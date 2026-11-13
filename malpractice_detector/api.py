"""
api.py
------
FastAPI Backend Service for AI Malpractice Detection System.
Powers both the Web, Desktop (.exe), and Mobile (.apk) Flutter clients.

Endpoints:
  - GET  /health
  - GET  /api/scenarios
  - POST /api/scenarios/{key}/run
  - POST /api/detect-frame          (Real-time single frame telemetry)
  - POST /api/session/start         (Start a stateful proctoring session)
  - POST /api/session/{id}/frame    (Feed frame into session state scorer)
  - POST /api/session/{id}/finalize (Finalize session and calculate 0-100 score)
  - POST /api/analyze-video         (Full video upload processing)
  - POST /api/rescore               (Re-run telemetry against custom thresholds)
  - POST /api/report/html           (Generate printable HTML/PDF audit certificate)
"""

import os
import math
import uuid
import time
import base64
import tempfile
from typing import Dict, Any, List, Optional
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from demo_data import SCENARIOS, run_scenario_session
from modules.scoring import RiskScorer, rescore_telemetry
from scoring_config import EVENT_WEIGHTS, FREQUENCY_WEIGHTS
from modules.face_utils import FaceMeshDetector, draw_face_annotations
from modules.eye_tracking import estimate_gaze
from modules.head_pose import estimate_head_pose
from modules.report import build_html_printable_report
from pipeline import process_video

app = FastAPI(
    title="FairSight Malpractice Detection Platform API",
    description="Cross-platform proctoring engine for Windows Desktop and Mobile clients.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v", ".wmv"}
MAX_VIDEO_UPLOAD_BYTES = 250 * 1024 * 1024  # 250 MB safety cap

# Persistent singleton detector for instant inference (<15ms)
_detector: Optional[FaceMeshDetector] = None

def get_detector() -> FaceMeshDetector:
    global _detector
    if _detector is None:
        _detector = FaceMeshDetector(max_num_faces=4)
    return _detector

def close_detector():
    global _detector
    if _detector is not None:
        try:
            _detector.close()
        except Exception:
            pass
        _detector = None

# In-memory store for live proctoring sessions
_active_sessions: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
def health_check():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_exists = os.path.exists(os.path.join(base_dir, "models", "face_landmarker.task"))
    hand_exists = os.path.exists(os.path.join(base_dir, "models", "hand_landmarker.task"))
    return {
        "status": "healthy",
        "version": "2.1.0",
        "models_loaded": {
            "face_landmarker": model_exists,
            "hand_landmarker": hand_exists,
        },
        "active_sessions": len(_active_sessions),
    }


@app.get("/api/scenarios")
def list_scenarios():
    return {
        key: {
            "title": val["title"],
            "subtitle": val["subtitle"],
            "description": val["description"],
            "expected_score": val["expected_score"],
            "expected_level": val["expected_level"],
        }
        for key, val in SCENARIOS.items()
    }


@app.post("/api/scenarios/{scenario_key}/run")
def execute_scenario(scenario_key: str):
    if scenario_key not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_key}' not found.")
    return run_scenario_session(scenario_key)


class DetectFramePayload(BaseModel):
    image_base64: str = Field(..., min_length=1)
    timestamp_ms: Optional[int] = Field(default=None, ge=0)


@app.post("/api/detect-frame")
def detect_single_frame(payload: DetectFramePayload):
    """
    Analyzes a single frame sent as base64 string from Flutter Mobile/Desktop camera.
    Returns real-time facial telemetry, eye gaze, head pose, and detected intruder limbs.
    """
    try:
        raw_b64 = payload.image_base64.strip()
        if not raw_b64:
            raise ValueError("Empty base64 image string")
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64, validate=True)
        if not img_bytes:
            raise ValueError("Decoded image payload is empty")
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame_bgr is None or frame_bgr.size == 0:
            raise ValueError("Failed to decode image from base64")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")

    detector = get_detector()
    res = detector.process(frame_bgr, timestamp_ms=payload.timestamp_ms)

    face_count = res["face_count"]
    conditions = {
        "no_face": face_count == 0,
        "multiple_faces": face_count > 1,
        "gaze_away": False,
        "head_turned": False,
    }
    details = {}
    gaze_data = None
    pose_data = None

    if face_count == 1 and len(res["landmarks_list"]) > 0:
        landmarks = res["landmarks_list"][0]
        gaze = estimate_gaze(landmarks)
        pose = estimate_head_pose(landmarks, res["frame_shape"])

        conditions["head_turned"] = bool(pose["flag"])
        conditions["gaze_away"] = bool((gaze["direction"] != "center") and (not pose["flag"]))

        gaze_data = gaze
        pose_data = pose

        if conditions["gaze_away"]:
            details["gaze_away"] = f"looking {gaze['direction']}"
        if conditions["head_turned"]:
            yaw_v = pose["yaw"] if pose["yaw"] is not None else 0.0
            turn_dir = "right" if yaw_v < 0 else "left"
            details["head_turned"] = f"turned {turn_dir} (yaw {yaw_v:.1f}\u00b0)"

    if conditions["multiple_faces"]:
        details["multiple_faces"] = f"{face_count} persons/limbs detected"
    if conditions["no_face"]:
        details["no_face"] = "no face detected"

    return {
        "face_count": face_count,
        "person_count": res["person_count"],
        "mesh_face_count": res["mesh_face_count"],
        "conditions": conditions,
        "details": details,
        "gaze": gaze_data,
        "head_pose": pose_data,
        "auxiliary_persons": res.get("auxiliary_persons", []),
    }


@app.post("/api/session/start")
def start_session():
    """Starts a stateful live exam proctoring session for a candidate."""
    session_id = str(uuid.uuid4())
    _active_sessions[session_id] = {
        "session_id": session_id,
        "start_time": time.time(),
        "scorer": RiskScorer(),
        "frames": [],
        "last_timestamp_sec": 0.0,
    }
    return {"session_id": session_id, "status": "active"}


class SessionFramePayload(BaseModel):
    image_base64: str = Field(..., min_length=1)
    timestamp_sec: float = Field(..., ge=0.0)


@app.post("/api/session/{session_id}/frame")
def ingest_session_frame(session_id: str, payload: SessionFramePayload):
    """Feeds a real-time frame into an active proctoring session."""
    session = _active_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    if not math.isfinite(payload.timestamp_sec):
        raise HTTPException(status_code=400, detail="timestamp_sec must be finite")

    # Reuse detect logic
    det_out = detect_single_frame(DetectFramePayload(
        image_base64=payload.image_base64,
        timestamp_ms=int(payload.timestamp_sec * 1000)
    ))

    t = payload.timestamp_sec
    session["last_timestamp_sec"] = t
    scorer: RiskScorer = session["scorer"]
    scorer.update(t, det_out["conditions"], details=det_out["details"])

    current_score = scorer.compute_risk_score()
    return {
        "status": "recorded",
        "frame_time_sec": t,
        "telemetry": det_out,
        "current_risk_score": current_score,
        "current_risk_level": scorer.risk_level(current_score),
    }


@app.post("/api/session/{session_id}/finalize")
def finalize_session(session_id: str):
    """Finalizes an active proctoring session, closing conditions and returning the final audit report."""
    session = _active_sessions.pop(session_id, None)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already finalized")

    scorer: RiskScorer = session["scorer"]
    scorer.finalize(session["last_timestamp_sec"])
    final_score = scorer.compute_risk_score()
    norm_res = scorer.compute_normalized_score(session_duration_sec=session["last_timestamp_sec"])

    return {
        "session_id": session_id,
        "duration_sec": round(session["last_timestamp_sec"], 2),
        "risk_score": final_score,
        "risk_level": scorer.risk_level(final_score),
        "normalized_score": norm_res["normalized_score"],
        "normalized_risk_level": norm_res["normalized_risk_level"],
        "window_analysis": norm_res["window_analysis"],
        "events": scorer.events,
        "activity_log": scorer.activity_log,
        "frames_analysed": len(scorer.activity_log),
    }


@app.post("/api/analyze-video")
def analyze_video_file(file: UploadFile = File(...)):
    """Processes an uploaded exam video file (.mp4, .avi, .mov, .mkv, .webm) using the 4 FPS pipeline."""
    filename = file.filename or "upload.mp4"
    suffix = os.path.splitext(filename)[1].lower() or ".mp4"
    if suffix not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{suffix}'. Allowed formats: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}",
        )

    file.file.seek(0)
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded video file is empty.")
    if len(content) > MAX_VIDEO_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded video exceeds maximum allowed size ({MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024)} MB).",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = process_video(tmp_path, debug=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid or unreadable video file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return result


class RescorePayload(BaseModel):
    debug_frames: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = None


@app.post("/api/rescore")
def rescore_session(payload: RescorePayload):
    try:
        return rescore_telemetry(payload.debug_frames, config=payload.config)
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid rescore payload: {str(e)}")


class ReportPayload(BaseModel):
    result: Dict[str, Any]
    session_meta: Optional[Dict[str, str]] = None


@app.post("/api/report/html", response_class=HTMLResponse)
def generate_html_report(payload: ReportPayload):
    try:
        return build_html_printable_report(payload.result, session_meta=payload.session_meta)
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid report payload: {str(e)}")
