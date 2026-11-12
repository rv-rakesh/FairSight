"""
pipeline.py
End-to-end video processing pipeline (Phase 3 + Phase 4 combined):
Video Upload -> Frame Extraction -> Face/Landmark Detection ->
Eye + Head Analysis -> Multi-Person Check -> Rule-Based Scoring -> Report

Usage (CLI, for testing without Streamlit):
    python pipeline.py path/to/video.mp4

This is the module the Streamlit app (app.py) will call into.
"""

import sys
import json
import cv2

from modules.face_utils import FaceMeshDetector
from modules.eye_tracking import estimate_gaze
from modules.head_pose import estimate_head_pose
from modules.scoring import RiskScorer
from scoring_config import SAMPLE_FPS


def process_video(video_path, sample_fps=SAMPLE_FPS, progress_callback=None, debug=False):
    """
    Runs the full pipeline on a video file.

    progress_callback: optional function(fraction_complete: float) for UI progress bars.
    debug: if True, records raw per-frame measurements (gaze ratio/direction,
           face count, head yaw/pitch) into result["debug_frames"], and also
           prints them to stdout when run from the command line. Use this to
           see exactly why an event was or wasn't flagged.

    Returns a dict:
      {
        "risk_score": int,
        "risk_level": str,
        "events": [ ... ],
        "frames_analysed": int,
        "video_duration_sec": float,
        "debug_frames": [ ... ]  (only present if debug=True)
      }
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_interval = max(1, round(native_fps / sample_fps))

    detector = FaceMeshDetector(max_num_faces=3)
    scorer = RiskScorer()
    debug_frames = [] if debug else None

    frame_idx = 0
    frames_analysed = 0
    last_timestamp = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            timestamp_sec = frame_idx / native_fps
            last_timestamp = timestamp_sec

            result = detector.process(frame, timestamp_ms=int(timestamp_sec * 1000))
            face_count = result["face_count"]

            conditions = {
                "no_face": face_count == 0,
                "multiple_faces": face_count > 1,
                "gaze_away": False,
                "head_turned": False,
            }

            gaze, pose = None, None
            details = {}
            if face_count == 1 and len(result["landmarks_list"]) > 0:
                landmarks = result["landmarks_list"][0]
                gaze = estimate_gaze(landmarks)
                pose = estimate_head_pose(landmarks, result["frame_shape"])

                conditions["head_turned"] = pose["flag"]
                # Decouple gaze from head turn: when candidate's head is turned (pose["flag"] is True),
                # flag head_turned. Only flag gaze_away when candidate's head is facing screen forward
                # but eyes look away (pure gaze deviation / screen peeking).
                conditions["gaze_away"] = (gaze["direction"] != "center") and (not pose["flag"])

                if conditions["gaze_away"]:
                    details["gaze_away"] = f"looking {gaze['direction']}"
                if conditions["head_turned"]:
                    yaw_v = pose["yaw"] if pose["yaw"] is not None else 0.0
                    pitch_v = pose["pitch"] if pose["pitch"] is not None else 0.0
                    turn_dir = "right" if yaw_v < 0 else "left"
                    tilt_dir = "down" if pitch_v > 0 else "up"
                    if abs(yaw_v) >= abs(pitch_v):
                        details["head_turned"] = f"turned {turn_dir} (yaw {yaw_v:.1f}\u00b0)"
                    else:
                        details["head_turned"] = f"tilted {tilt_dir} (pitch {pitch_v:.1f}\u00b0)"
            if conditions["multiple_faces"]:
                details["multiple_faces"] = f"{face_count} persons in frame"
            if conditions["no_face"]:
                details["no_face"] = "no candidate face/person detected"

            if debug:
                row = {
                    "time_sec": round(timestamp_sec, 2),
                    "faces": face_count,
                    "gaze_h_ratio": gaze["horizontal_ratio"] if gaze else None,
                    "gaze_v_ratio": gaze["vertical_ratio"] if gaze else None,
                    "gaze_direction": gaze["direction"] if gaze else "n/a",
                    "yaw": pose["yaw"] if pose else None,
                    "pitch": pose["pitch"] if pose else None,
                    "flags": ",".join([k for k, v in conditions.items() if v]) or "-",
                }
                debug_frames.append(row)
                print(f"{row['time_sec']:6.1f} | faces={row['faces']} | gaze={row['gaze_h_ratio']}/{row['gaze_v_ratio']} ({row['gaze_direction']}) | yaw={row['yaw']} pitch={row['pitch']} | {row['flags']}")

            scorer.update(timestamp_sec, conditions, details=details)
            frames_analysed += 1

            if progress_callback and total_frames > 0:
                progress_callback(frame_idx / total_frames)

        frame_idx += 1

    cap.release()
    detector.close()
    scorer.finalize(last_timestamp)

    score = scorer.compute_risk_score()
    norm_res = scorer.compute_normalized_score(session_duration_sec=last_timestamp)

    output = {
        "risk_score": score,
        "risk_level": scorer.risk_level(score),
        "normalized_score": norm_res["normalized_score"],
        "normalized_risk_level": norm_res["normalized_risk_level"],
        "window_analysis": norm_res["window_analysis"],
        "events": scorer.events,
        "activity_log": scorer.activity_log,
        "frames_analysed": frames_analysed,
        "video_duration_sec": round(last_timestamp, 2),
    }
    if debug:
        output["debug_frames"] = debug_frames
    return output


def run_demo_session(progress_callback=None):
    """
    Runs the REAL RiskScorer against a simulated exam-session timeline
    (see demo_data.py), instead of a real video. Useful for demonstrating
    the scoring/report pipeline works correctly without needing a webcam,
    internet access for the MediaPipe model, or a real test video on hand.

    Returns the exact same result dict shape as process_video(), so it
    can be displayed by the same Streamlit UI code / report.py functions.
    """
    from demo_data import run_scenario_session

    return run_scenario_session("composite_session", progress_callback=progress_callback)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <video_path> [--debug]")
        print("       python pipeline.py --demo   (runs simulated demo session, no video needed)")
        sys.exit(1)

    if sys.argv[1] == "--demo":
        print("Running simulated demo session (no video/webcam needed)...")
        report = run_demo_session()
        print(json.dumps(report, indent=2))
        sys.exit(0)

    video_path = sys.argv[1]
    debug_mode = "--debug" in sys.argv
    print(f"Processing: {video_path}" + (" (debug mode)" if debug_mode else ""))
    report = process_video(video_path, debug=debug_mode)
    print()
    print(json.dumps(report, indent=2))
