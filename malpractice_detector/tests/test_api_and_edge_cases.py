"""
test_api_and_edge_cases.py
--------------------------
Comprehensive WP2 & WP3 verification suite exercising the FastAPI application
(`api.py`), Pydantic validation models, all 10 routes, CORS middleware configuration,
multipart UploadFile handling, and edge-case/error paths reliably on Windows & Linux.
"""

import io
import os
import base64
import tempfile
import cv2
import numpy as np
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.datastructures import UploadFile

import api

DETECTOR_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(DETECTOR_DIR, "docs", "images")


@pytest.fixture(autouse=True)
def cleanup_api_detector():
    yield
    api.close_detector()


def _create_video_bytes(frames, fps=12.0, ext=".mp4"):
    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*("MJPG" if ext == ".avi" else "mp4v"))
        writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
        assert writer.isOpened(), f"Could not open VideoWriter for {ext}"
        for frm in frames:
            writer.write(frm)
        writer.release()
        with open(path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_fastapi_routes_and_cors_registered():
    route_paths = {getattr(r, "path", None) for r in api.app.routes}
    expected_routes = {
        "/health",
        "/api/scenarios",
        "/api/scenarios/{scenario_key}/run",
        "/api/detect-frame",
        "/api/session/start",
        "/api/session/{session_id}/frame",
        "/api/session/{session_id}/finalize",
        "/api/analyze-video",
        "/api/rescore",
        "/api/report/html",
    }
    assert expected_routes.issubset(route_paths)
    assert len(api.app.user_middleware) >= 1


def test_health_and_scenarios_endpoints():
    health = api.health_check()
    assert health["status"] == "healthy"
    assert health["models_loaded"]["face_landmarker"] is True
    assert health["models_loaded"]["hand_landmarker"] is True

    scenarios = api.list_scenarios()
    assert "honest_candidate" in scenarios
    assert "screen_peeking" in scenarios
    assert "unauthorized_person" in scenarios

    res = api.execute_scenario("honest_candidate")
    assert res["risk_score"] == 0

    with pytest.raises(HTTPException) as exc:
        api.execute_scenario("does_not_exist")
    assert exc.value.status_code == 404


def test_detect_frame_valid_and_invalid():
    frame_path = os.path.join(IMAGES_DIR, "frame_230.png")
    img = cv2.imread(frame_path)
    assert img is not None
    ok, buf = cv2.imencode(".png", img)
    assert ok
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    try:
        res = api.detect_single_frame(api.DetectFramePayload(image_base64=b64, timestamp_ms=100))
    except OSError as e:
        if "4551" in str(e) or "Application Control" in str(e):
            pytest.skip(f"Windows Smart App Control blocked MediaPipe: {e}")
        raise

    assert res["face_count"] == 1
    assert res["conditions"]["no_face"] is False

    # Blank frame -> no face
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    _, bbuf = cv2.imencode(".png", blank)
    res_blank = api.detect_single_frame(
        api.DetectFramePayload(
            image_base64=base64.b64encode(bbuf.tobytes()).decode("ascii"),
            timestamp_ms=200,
        )
    )
    assert res_blank["conditions"]["no_face"] is True

    # Invalid base64 -> 400
    with pytest.raises(HTTPException) as exc:
        api.detect_single_frame(api.DetectFramePayload(image_base64="not-valid-base64!!!"))
    assert exc.value.status_code == 400

    # Negative timestamp rejected by Pydantic validation
    with pytest.raises(ValidationError):
        api.DetectFramePayload(image_base64=b64, timestamp_ms=-5)


def test_session_lifecycle_and_error_cases():
    started = api.start_session()
    sid = started["session_id"]
    assert started["status"] == "active"

    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    _, bbuf = cv2.imencode(".png", blank)
    b64_blank = base64.b64encode(bbuf.tobytes()).decode("ascii")

    try:
        for t in (0.0, 0.5, 1.0, 1.5):
            out = api.ingest_session_frame(
                sid,
                api.SessionFramePayload(image_base64=b64_blank, timestamp_sec=t),
            )
            assert out["status"] == "recorded"
    except OSError as e:
        if "4551" in str(e) or "Application Control" in str(e):
            pytest.skip(f"Windows Smart App Control blocked MediaPipe: {e}")
        raise

    # Negative timestamp rejected by Pydantic validation
    with pytest.raises(ValidationError):
        api.SessionFramePayload(image_base64=b64_blank, timestamp_sec=-1.0)

    # Unknown session -> 404
    with pytest.raises(HTTPException) as exc_nf:
        api.ingest_session_frame(
            "nonexistent-session-id",
            api.SessionFramePayload(image_base64=b64_blank, timestamp_sec=0.0),
        )
    assert exc_nf.value.status_code == 404

    # Finalize succeeds once
    rep = api.finalize_session(sid)
    assert rep["risk_score"] >= 6
    assert "normalized_score" in rep

    # Second finalize returns 404
    with pytest.raises(HTTPException) as exc2:
        api.finalize_session(sid)
    assert exc2.value.status_code == 404


def test_analyze_video_valid_short_empty_invalid_unsupported():
    # 1. Empty file upload -> 400
    with pytest.raises(HTTPException) as exc_empty:
        api.analyze_video_file(UploadFile(filename="empty.mp4", file=io.BytesIO(b"")))
    assert exc_empty.value.status_code == 400
    assert "empty" in exc_empty.value.detail.lower()

    # 2. Unsupported extension -> 400
    with pytest.raises(HTTPException) as exc_unsup:
        api.analyze_video_file(UploadFile(filename="notes.txt", file=io.BytesIO(b"hello")))
    assert exc_unsup.value.status_code == 400
    assert "unsupported" in exc_unsup.value.detail.lower()

    # 3. Corrupt video bytes -> 400 (not 500)
    with pytest.raises(HTTPException) as exc_bad:
        api.analyze_video_file(UploadFile(filename="corrupt.mp4", file=io.BytesIO(b"NOT_A_REAL_MP4")))
    assert exc_bad.value.status_code == 400

    # 4. Very short blank video -> valid result
    blank_frames = [np.zeros((160, 200, 3), dtype=np.uint8) for _ in range(3)]
    short_mp4 = _create_video_bytes(blank_frames, fps=12.0, ext=".mp4")
    try:
        res_short = api.analyze_video_file(UploadFile(filename="short.mp4", file=io.BytesIO(short_mp4)))
    except OSError as e:
        if "4551" in str(e) or "Application Control" in str(e):
            pytest.skip(f"Windows Smart App Control blocked MediaPipe: {e}")
        raise
    assert res_short["frames_analysed"] >= 1

    # 5. Normal candidate MP4 built from reference frame -> Low risk
    img_normal = cv2.imread(os.path.join(IMAGES_DIR, "frame_230.png"))
    normal_mp4 = _create_video_bytes([img_normal for _ in range(24)], fps=12.0, ext=".mp4")
    res_normal = api.analyze_video_file(UploadFile(filename="normal.mp4", file=io.BytesIO(normal_mp4)))
    assert res_normal["risk_score"] == 0
    assert res_normal["risk_level"] == "Low"


def test_rescore_and_html_report_endpoints():
    debug_frames = [
        {"time_sec": 0.0, "faces": 1, "yaw": 0.0, "pitch": 5.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
        {"time_sec": 0.5, "faces": 1, "yaw": 0.0, "pitch": -25.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
        {"time_sec": 1.5, "faces": 1, "yaw": 0.0, "pitch": -25.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
        {"time_sec": 2.0, "faces": 1, "yaw": 0.0, "pitch": 5.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
    ]
    rescored = api.rescore_session(api.RescorePayload(debug_frames=debug_frames))
    assert any(e["type"] == "head_turned" for e in rescored["events"])

    # Empty debug_frames returns clean zero report
    empty_res = api.rescore_session(api.RescorePayload(debug_frames=[]))
    assert empty_res["risk_score"] == 0

    # HTML Report accepts rescore/session output and escapes XSS in metadata
    html_text = api.generate_html_report(
        api.ReportPayload(
            result=rescored,
            session_meta={"candidate_name": "<script>alert(1)</script>Alice"},
        )
    )
    assert "10m Norm:" in html_text
    assert "<script>alert(1)</script>" not in html_text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;Alice" in html_text
