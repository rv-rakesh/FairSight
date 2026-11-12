"""
demo_data.py
-------------
Simulates realistic exam sessions as timelines of per-frame telemetry and conditions,
so the scoring and reporting pipeline (modules/scoring.py, modules/report.py)
and behavioral analytics (modules/visualizations.py) can be demonstrated
end-to-end WITHOUT needing a video file or webcam.

Every scenario generates full per-frame numeric telemetry:
  - time_sec: float
  - faces: int (0, 1, 2)
  - yaw: float (degrees, negative=right, positive=left)
  - pitch: float (degrees, positive=down, negative=up)
  - gaze_h_ratio: float (0=left, 0.5=center, 1=right)
  - gaze_v_ratio: float (0=up, 0.5=center, 1=down)

Boolean conditions (gaze_away, head_turned, no_face, multiple_faces) are
DERIVED from these numeric values using real thresholds (not hand-set).
"""

from scoring_config import (
    YAW_THRESHOLD,
    PITCH_DOWN_THRESHOLD,
    HORIZONTAL_CENTER_RANGE,
    VERTICAL_DOWN_THRESHOLD,
    VERTICAL_UP_THRESHOLD,
    DEMO_STEP_SEC,
)
from modules.scoring import RiskScorer

STEP_SEC = DEMO_STEP_SEC  # matching scoring_config.py


def derive_telemetry_conditions(frame, yaw_thresh=YAW_THRESHOLD, pitch_thresh=PITCH_DOWN_THRESHOLD,
                                h_range=HORIZONTAL_CENTER_RANGE, v_down=VERTICAL_DOWN_THRESHOLD,
                                v_up=VERTICAL_UP_THRESHOLD):
    """
    Derives condition booleans and human-readable details from raw numeric telemetry.
    Matches the exact logic used in pipeline.py and modules/scoring.py.
    """
    faces = frame.get("faces", 1)
    yaw = frame.get("yaw")
    pitch = frame.get("pitch")
    gh = frame.get("gaze_h_ratio")
    gv = frame.get("gaze_v_ratio")

    conditions = {
        "no_face": faces == 0,
        "multiple_faces": faces > 1,
        "gaze_away": False,
        "head_turned": False,
    }
    details = {}
    direction = "center"

    if faces == 1:
        if gv is not None and gh is not None:
            if gh < h_range[0]:
                direction = "left"
            elif gh > h_range[1]:
                direction = "right"
            elif gv > v_down:
                direction = "down"
            elif gv < v_up:
                direction = "up"
            else:
                direction = "center"

        if yaw is not None and pitch is not None:
            conditions["head_turned"] = abs(yaw) > yaw_thresh or pitch > pitch_thresh
            if conditions["head_turned"]:
                turn_dir = "right" if yaw < 0 else "left"
                tilt_dir = "down" if pitch > 0 else "up"
                if abs(yaw) >= abs(pitch):
                    details["head_turned"] = f"turned {turn_dir} (yaw {yaw:.1f}\u00b0)"
                else:
                    details["head_turned"] = f"tilted {tilt_dir} (pitch {pitch:.1f}\u00b0)"

        conditions["gaze_away"] = (direction != "center") and (not conditions["head_turned"])
        if conditions["gaze_away"]:
            details["gaze_away"] = f"looking {direction}"

    if conditions["multiple_faces"]:
        details["multiple_faces"] = f"{faces} faces in frame"
    if conditions["no_face"]:
        details["no_face"] = "no face detected"

    return conditions, details, direction


def _generate_telemetry_block(start_time, duration_sec, yaw_fn, pitch_fn, gh_fn, gv_fn, faces=1):
    """Generates a list of frame telemetry dicts over duration_sec."""
    frames = []
    num_steps = max(1, int(round(duration_sec / STEP_SEC)))
    t = start_time
    for i in range(num_steps):
        frac = i / max(1, num_steps - 1)
        y = yaw_fn(frac) if callable(yaw_fn) else yaw_fn
        p = pitch_fn(frac) if callable(pitch_fn) else pitch_fn
        gh = gh_fn(frac) if callable(gh_fn) else gh_fn
        gv = gv_fn(frac) if callable(gv_fn) else gv_fn

        frame = {
            "time_sec": round(t, 2),
            "faces": faces,
            "yaw": round(y, 1) if y is not None else None,
            "pitch": round(p, 1) if p is not None else None,
            "gaze_h_ratio": round(gh, 3) if gh is not None else None,
            "gaze_v_ratio": round(gv, 3) if gv is not None else None,
        }
        conds, details, direction = derive_telemetry_conditions(frame)
        frame["conditions"] = conds
        frame["details"] = details
        frame["gaze_direction"] = direction
        frame["flags"] = ",".join([k for k, v in conds.items() if v]) or "-"
        frames.append(frame)
        t += STEP_SEC
    return frames, t


def build_honest_candidate_telemetry():
    """
    Scenario 1: Honest Candidate (Clean)
    40 seconds of normal exam behavior with 1 brief natural glance down (0.3s)
    to reflect on a question. Correctly filtered out by duration guard.
    Expected: 0 confirmed events, Risk Score: 0/100 (Low).
    """
    frames = []
    t = 0.0

    # 0s - 18s: Attentive focus on screen (yaw ~1.5°, pitch ~9°, gaze centered)
    f, t = _generate_telemetry_block(t, 18.0, yaw_fn=1.5, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 18.0s - 18.3s: Momentary natural glance down (~0.3s, pitch 14°, gaze down 0.70)
    f, t = _generate_telemetry_block(t, 0.4, yaw_fn=1.0, pitch_fn=14.0, gh_fn=0.50, gv_fn=0.70)
    frames.extend(f)

    # 18.5s - 40s: Return to centered focus, slight posture shift (yaw -3.0°)
    f, t = _generate_telemetry_block(t, 21.5, yaw_fn=-3.0, pitch_fn=10.0, gh_fn=0.51, gv_fn=0.49)
    frames.extend(f)

    return frames


def build_occasional_distraction_telemetry():
    """
    Scenario 2: Occasional Distraction (Low Risk)
    45 seconds with natural room glance (1.0s) and slight head tilt (1.0s).
    None exceed the 2.0s sustained threshold or cluster into frequency patterns.
    Expected: 0 confirmed events, Risk Score: 0/100 (Low).
    """
    frames = []
    t = 0.0

    # 0s - 14s: Normal focus
    f, t = _generate_telemetry_block(t, 14.0, yaw_fn=0.5, pitch_fn=8.5, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 14s - 15s: Brief 1.0s gaze shift to the right (window/door sound)
    f, t = _generate_telemetry_block(t, 1.0, yaw_fn=2.0, pitch_fn=8.0, gh_fn=0.75, gv_fn=0.50)
    frames.extend(f)

    # 15s - 28s: Normal focus
    f, t = _generate_telemetry_block(t, 13.0, yaw_fn=-1.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.51)
    frames.extend(f)

    # 28s - 29s: Brief 1.0s head turn left (yaw +28°, above 26° threshold but under 2.0s guard)
    f, t = _generate_telemetry_block(t, 1.0, yaw_fn=28.0, pitch_fn=10.0, gh_fn=0.55, gv_fn=0.50)
    frames.extend(f)

    # 29s - 45s: Resumes exam focus
    f, t = _generate_telemetry_block(t, 16.0, yaw_fn=0.0, pitch_fn=9.5, gh_fn=0.49, gv_fn=0.50)
    frames.extend(f)

    return frames


def build_screen_peeking_telemetry():
    """
    Scenario 3: Screen Peeking & Notes Cheating (Medium-High Risk)
    Demonstrates Layer 2 Frequency-Pattern detection.
    Candidate repeatedly glances down-left at notes/phone every ~2s.
    Each glance is only 0.5s (under 2.0s sustained guard), but 4 glances
    in 7 seconds trigger a confirmed frequent_gaze_away pattern event (+18 pts).
    A second cluster triggers at 30s. Total: 36 / 100 (Medium).
    """
    frames = []
    t = 0.0

    # 0s - 10s: Normal focus
    f, t = _generate_telemetry_block(t, 10.0, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # Cluster 1: 4 rapid glances down-left within 7 seconds
    for _ in range(4):
        # 0.5s glance down-left (gaze_h=0.20, gaze_v=0.72)
        f, t = _generate_telemetry_block(t, 0.5, yaw_fn=-2.0, pitch_fn=12.0, gh_fn=0.20, gv_fn=0.72)
        frames.extend(f)
        # 1.5s center
        f, t = _generate_telemetry_block(t, 1.5, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
        frames.extend(f)

    # 18s - 30s: Normal pause
    f, t = _generate_telemetry_block(t, 12.0, yaw_fn=1.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # Cluster 2: 3 rapid glances down-left within 5 seconds
    for _ in range(3):
        f, t = _generate_telemetry_block(t, 0.5, yaw_fn=-3.0, pitch_fn=13.0, gh_fn=0.18, gv_fn=0.74)
        frames.extend(f)
        f, t = _generate_telemetry_block(t, 1.5, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
        frames.extend(f)

    # 38s - 50s: Return to center
    f, t = _generate_telemetry_block(t, 12.0, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    return frames


def build_unauthorized_person_telemetry():
    """
    Scenario 4: Unauthorized Second Person (Severe / Critical)
    Demonstrates Layer 3 Immediate Flagging.
    A second face appears in camera view at 15s (3.5s) and 32s (1.0s).
    Both trigger confirmed multiple_faces events (+30 pts each). Total: 60 / 100 (High).
    """
    frames = []
    t = 0.0

    # 0s - 15s: Normal focus, 1 person
    f, t = _generate_telemetry_block(t, 15.0, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50, faces=1)
    frames.extend(f)

    # 15s - 18.5s: Second person enters frame (faces=2)
    f, t = _generate_telemetry_block(t, 3.5, yaw_fn=4.0, pitch_fn=10.0, gh_fn=0.52, gv_fn=0.50, faces=2)
    frames.extend(f)

    # 18.5s - 32s: Normal focus, 1 person
    f, t = _generate_telemetry_block(t, 13.5, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50, faces=1)
    frames.extend(f)

    # 32s - 33s: Brief 1.0s second person reappearance (faces=2) -> Immediate flag!
    f, t = _generate_telemetry_block(t, 1.0, yaw_fn=2.0, pitch_fn=9.5, gh_fn=0.50, gv_fn=0.50, faces=2)
    frames.extend(f)

    # 33s - 45s: Resumes solo exam
    f, t = _generate_telemetry_block(t, 12.0, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50, faces=1)
    frames.extend(f)

    return frames


def build_composite_telemetry():
    """
    Scenario 5: Comprehensive Evaluation (Mixed Malpractice)
    Preserves the exact sequence and timestamps of the original build_demo_timeline(),
    now fully enriched with real numeric yaw/pitch/gaze telemetry.
      - 0s - 15s: Normal (15s)
      - 15.5s - 15.9s: Brief glance down (~0.4s) -> below threshold
      - 20s - 24s: Sustained gaze-away (4.0s) -> confirmed event (+12)
      - 30s - 38s: Repeated glances (4 in 8s) -> frequent pattern (+18)
      - 45s - 50.5s: Sustained head turn right (5.5s, yaw -32°) -> confirmed event (+15)
      - 65s - 70s: Second person enters (5.0s, faces=2) -> confirmed event (+30)
      - Total Score: 75 / 100 (High)
    """
    frames = []
    t = 0.0

    # 0s - 15s: Normal focus
    f, t = _generate_telemetry_block(t, 15.0, yaw_fn=0.5, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 15s - 15.5s: Normal transition
    f, t = _generate_telemetry_block(t, 0.5, yaw_fn=0.0, pitch_fn=9.5, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 15.5s - 15.9s: Brief glance down (~0.4s)
    f, t = _generate_telemetry_block(t, 0.4, yaw_fn=0.0, pitch_fn=13.0, gh_fn=0.50, gv_fn=0.72)
    frames.extend(f)

    # 15.9s - 20s: Normal center focus (4.1s)
    f, t = _generate_telemetry_block(t, 4.1, yaw_fn=1.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 20s - 24s: Sustained gaze away left (4.0s, gh=0.20)
    f, t = _generate_telemetry_block(t, 4.0, yaw_fn=-2.0, pitch_fn=10.0, gh_fn=0.20, gv_fn=0.50)
    frames.extend(f)

    # 24s - 30s: Normal focus (6.0s)
    f, t = _generate_telemetry_block(t, 6.0, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 30s - 38s: Repeated brief glances down-left (4 occurrences within ~8s)
    for _ in range(4):
        f, t = _generate_telemetry_block(t, 0.5, yaw_fn=-1.0, pitch_fn=12.0, gh_fn=0.19, gv_fn=0.70)
        frames.extend(f)
        f, t = _generate_telemetry_block(t, 1.5, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
        frames.extend(f)

    # 38s - 45s: Normal transition (7.0s)
    f, t = _generate_telemetry_block(t, 7.0, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 45s - 50.5s: Sustained head turn right (5.5s, yaw -32.0°)
    f, t = _generate_telemetry_block(t, 5.5, yaw_fn=-32.0, pitch_fn=11.0, gh_fn=0.48, gv_fn=0.50)
    frames.extend(f)

    # 50.5s - 65s: Normal focus (14.5s)
    f, t = _generate_telemetry_block(t, 14.5, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    # 65s - 70s: Extra person enters frame (5.0s, faces=2)
    f, t = _generate_telemetry_block(t, 5.0, yaw_fn=3.0, pitch_fn=9.5, gh_fn=0.50, gv_fn=0.50, faces=2)
    frames.extend(f)

    # 70s - 90s: Final normal segment (20.0s)
    f, t = _generate_telemetry_block(t, 20.0, yaw_fn=0.0, pitch_fn=9.0, gh_fn=0.50, gv_fn=0.50)
    frames.extend(f)

    return frames


# ---------------------------------------------------------------------------
# Canonical Scenarios Registry
# ---------------------------------------------------------------------------
SCENARIOS = {
    "honest_candidate": {
        "title": "Honest Candidate (Clean)",
        "subtitle": "Natural behavior · False-positive duration protection",
        "description": "Candidate demonstrates attentive examination focus. An accidental micro-glance (0.3s) is safely ignored by the 2.0s duration guard.",
        "expected_score": "0 / 100",
        "expected_level": "Low",
        "badge_color": "#1E8E5A",
        "generator": build_honest_candidate_telemetry,
    },
    "occasional_distraction": {
        "title": "Occasional Distraction (Low Risk)",
        "subtitle": "Brief room adjustments · No sustained cheating",
        "description": "Candidate briefly glances at room noises (1.0s) and tilts head (1.0s). Both remain below the sustained threshold without clustering.",
        "expected_score": "0 / 100",
        "expected_level": "Low",
        "badge_color": "#1E8E5A",
        "generator": build_occasional_distraction_telemetry,
    },
    "screen_peeking": {
        "title": "Screen Peeking & Notes Cheating (Medium-High)",
        "subtitle": "Repeated micro-glances · Layer 2 Frequency-Pattern trigger",
        "description": "Candidate glances off-screen at notes in rapid succession. Although individual glances last under 2s, the repeated pattern is flagged as suspicious clusters.",
        "expected_score": "36 / 100",
        "expected_level": "Medium",
        "badge_color": "#B7791F",
        "generator": build_screen_peeking_telemetry,
    },
    "unauthorized_person": {
        "title": "Unauthorized Second Person (Severe / Critical)",
        "subtitle": "Multiple faces detected · Layer 3 Immediate Flag",
        "description": "A second person enters the webcam frame. Triggered immediately regardless of duration, escalating risk to critical status.",
        "expected_score": "60 / 100",
        "expected_level": "High",
        "badge_color": "#C0392B",
        "generator": build_unauthorized_person_telemetry,
    },
    "composite_session": {
        "title": "Comprehensive Evaluation (Mixed Malpractice)",
        "subtitle": "Multi-layer demonstration · Sustained + Frequency + Immediate",
        "description": "Full 90-second exam evaluation showing sustained off-center gaze, repeated peeking clusters, sustained head turn, and second person presence.",
        "expected_score": "75 / 100",
        "expected_level": "High",
        "badge_color": "#C0392B",
        "generator": build_composite_telemetry,
    },
}


def run_scenario_session(scenario_key="composite_session", progress_callback=None, config=None):
    """
    Executes the real RiskScorer against a canonical scenario's telemetry frames.
    Derives condition flags dynamically from numeric measurements.
    """
    scenario_info = SCENARIOS.get(scenario_key, SCENARIOS["composite_session"])
    telemetry_frames = scenario_info["generator"]()

    scorer = RiskScorer(sample_fps=1.0 / STEP_SEC)
    debug_frames = []
    last_timestamp = 0.0

    for i, frame in enumerate(telemetry_frames):
        t = frame["time_sec"]
        last_timestamp = t
        conds, details, direction = derive_telemetry_conditions(frame)

        scorer.update(t, conds, details=details)

        f_copy = dict(frame)
        f_copy["conditions"] = conds
        f_copy["details"] = details
        f_copy["gaze_direction"] = direction
        f_copy["flags"] = ",".join([k for k, v in conds.items() if v]) or "-"
        debug_frames.append(f_copy)

        if progress_callback:
            progress_callback((i + 1) / len(telemetry_frames))

    scorer.finalize(last_timestamp)
    score = scorer.compute_risk_score()

    return {
        "risk_score": score,
        "risk_level": scorer.risk_level(score),
        "events": scorer.events,
        "activity_log": scorer.activity_log,
        "frames_analysed": len(telemetry_frames),
        "video_duration_sec": round(last_timestamp, 2),
        "debug_frames": debug_frames,
        "scenario_key": scenario_key,
        "scenario_title": scenario_info["title"],
    }


def build_demo_timeline():
    """Backward-compatible helper returning (timestamp, conditions) tuples."""
    frames = build_composite_telemetry()
    return [(f["time_sec"], f["conditions"]) for f in frames]


DEMO_VIDEO_NAME = "demo_session_simulated.mp4"

