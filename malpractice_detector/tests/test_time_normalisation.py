"""
test_time_normalisation.py
==========================
WP1 Test Suite: Time Normalisation, Frequency Rule, and Consecutive-Frame Rigor.

Covers:
1. Short (30s) vs 3-Hour (10,800s) session behavior: proves that an honest candidate
   with sparse natural glances never reaches High under time normalisation (Fix L16 & D5).
2. Acute cheating in a single window correctly escalates to High.
3. Per-type window caps are strictly enforced per 10-minute window.
4. Frequency rule evaluation: frequency_min_count 2 vs 3 (Fix L17).
5. Consecutive-frame guard for multi-face detection (Fix L19).
6. rescore_telemetry returns complete dual-score telemetry.
"""

import pytest
from modules.scoring import RiskScorer, rescore_telemetry
import scoring_config as cfg


def test_short_clip_vs_3hour_honest_session():
    """
    Acceptance Test for WP1 / Fix L16 / Decision D5:
    A 30s clip and a 3-hour session with identical sparse natural glancing (1 glance per 10 min).
    - Under raw score: 3-hour exam reaches 100/100 (HIGH RISK - false accusation!).
    - Under time normalisation: 3-hour exam stays at ~32 (MEDIUM - advisory), NEVER reaches HIGH.
    """
    # 1. Short 30s session: 1 natural sustained glance away (1.0s at t=10s)
    scorer_short = RiskScorer()
    scorer_short.update(0.0, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_short.update(10.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_short.update(11.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_short.update(11.5, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_short.finalize(30.0)

    norm_short = scorer_short.compute_normalized_score(30.0)
    assert norm_short["raw_score"] == 12
    assert norm_short["raw_risk_level"] == "Low"
    assert norm_short["normalized_score"] == 12
    assert norm_short["normalized_risk_level"] == "Low"
    assert len(norm_short["window_analysis"]) == 1

    # 2. Long 3-hour session (180 min = 10,800s):
    # Candidate looks away once every 10 minutes (18 total windows, 1 glance each)
    scorer_3h = RiskScorer()
    for w in range(18):
        t_base = w * 600.0 + 300.0  # middle of each 10-minute window
        scorer_3h.update(t_base, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
        scorer_3h.update(t_base + 1.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
        scorer_3h.update(t_base + 1.5, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_3h.finalize(10800.0)

    norm_3h = scorer_3h.compute_normalized_score(10800.0)

    # Raw score blows up to cap (18 * 12 = 216 -> 100 High)
    assert norm_3h["raw_score"] == 100
    assert norm_3h["raw_risk_level"] == "High"

    # Normalized score stays controlled: ~32 (Medium advisory, NOT High)
    assert norm_3h["normalized_score"] < 40
    assert norm_3h["normalized_score"] >= 25
    assert norm_3h["normalized_risk_level"] == "Medium"
    assert norm_3h["normalized_risk_level"] != "High"
    assert len(norm_3h["window_analysis"]) == 18


def test_cheating_in_single_window_escalates():
    """
    Verifies that if a candidate cheats heavily in even ONE 10-minute window
    during a 3-hour exam, the normalized score immediately escalates to High (>=60).
    """
    scorer = RiskScorer()
    # Quiet exam for 2 hours, then acute malpractice in Window 2 (minute 20 to 30)
    # 1 second person (30 pts) + 2 sustained head turns (15+15=30 pts) = 60 pts
    w2_base = 2 * 600.0 + 60.0  # t = 1260s
    scorer.update(w2_base, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer.update(w2_base + 0.5, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})

    # Head turn 1 (0.6s)
    scorer.update(w2_base + 10.0, {"head_turned": True, "multiple_faces": False, "gaze_away": False, "no_face": False})
    scorer.update(w2_base + 10.6, {"head_turned": False, "multiple_faces": False, "gaze_away": False, "no_face": False})

    # Head turn 2 (0.6s)
    scorer.update(w2_base + 30.0, {"head_turned": True, "multiple_faces": False, "gaze_away": False, "no_face": False})
    scorer.update(w2_base + 30.6, {"head_turned": False, "multiple_faces": False, "gaze_away": False, "no_face": False})

    scorer.finalize(10800.0)
    norm = scorer.compute_normalized_score(10800.0)

    # In window 2, total = 30 + 15 + 15 = 60
    assert norm["window_analysis"][2]["window_score"] == 60
    assert norm["normalized_score"] >= 60
    assert norm["normalized_risk_level"] == "High"


def test_per_type_window_caps_enforced():
    """
    Verifies that within any single 10-minute window, excessive events of the same
    type are capped at WINDOW_PER_TYPE_CAPS (e.g. gaze_away capped at 24 pts).
    """
    scorer = RiskScorer()
    # 5 sustained glances away in the first 10 minutes (raw = 5 * 12 = 60 pts)
    for i in range(5):
        t = 50.0 + i * 20.0
        scorer.update(t, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
        scorer.update(t + 1.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
        scorer.update(t + 1.2, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer.finalize(600.0)

    norm = scorer.compute_normalized_score(600.0)
    assert norm["raw_score"] == 60  # raw sum is 60

    # Capped at WINDOW_PER_TYPE_CAPS["gaze_away"] (24)
    w0 = norm["window_analysis"][0]
    assert w0["points_by_type"]["gaze_away"] == 60
    assert w0["capped_points_by_type"]["gaze_away"] == 24
    assert w0["window_score"] == 24
    assert norm["normalized_score"] == 24
    assert norm["normalized_risk_level"] == "Low"


def test_frequency_rule_2_vs_3_behavior():
    """
    Fix L17 evaluation: Compares detection under frequency_min_count = 2 vs 3.
    Two brief glances in an 8-second window:
    - count=2: triggers frequent_gaze_away (+18 pts)
    - count=3: does not trigger (0 pts)
    """
    # 1. With frequency_min_count = 2 (FairSight default)
    scorer_cnt2 = RiskScorer(frequency_min_count=2, frequency_window_sec=10.0)
    # Glance 1 (0.2s duration < 0.7s gate -> brief)
    scorer_cnt2.update(2.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt2.update(2.2, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    # Glance 2 (0.2s duration at t=6.0s -> inside 10s window)
    scorer_cnt2.update(6.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt2.update(6.2, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt2.finalize(15.0)

    assert any(e["type"] == "frequent_gaze_away" for e in scorer_cnt2.events)
    assert scorer_cnt2.compute_risk_score() == 18

    # 2. With frequency_min_count = 3 (older guideline)
    scorer_cnt3 = RiskScorer(frequency_min_count=3, frequency_window_sec=10.0)
    scorer_cnt3.update(2.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt3.update(2.2, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt3.update(6.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt3.update(6.2, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt3.finalize(15.0)

    # With only 2 glances, count=3 does NOT trigger
    assert not any(e["type"] == "frequent_gaze_away" for e in scorer_cnt3.events)
    assert scorer_cnt3.compute_risk_score() == 0

    # Adding the 3rd glance makes count=3 trigger
    scorer_cnt3.update(8.0, {"gaze_away": True, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt3.update(8.2, {"gaze_away": False, "head_turned": False, "no_face": False, "multiple_faces": False})
    scorer_cnt3.finalize(15.0)
    assert any(e["type"] == "frequent_gaze_away" for e in scorer_cnt3.events)
    assert scorer_cnt3.compute_risk_score() == 18


def test_multi_face_consecutive_frames_guard():
    """
    Fix L19: When require_consecutive_multi_face is True, a single 1-frame
    artifact is suppressed, while 2 consecutive frames confirm the violation.
    When False (default), single frame triggers immediately.
    """
    # 1. Default (require_consecutive_multi_face = False): single frame triggers immediately
    scorer_default = RiskScorer(require_consecutive_multi_face=False)
    scorer_default.update(5.0, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_default.update(5.25, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_default.finalize(10.0)
    assert len(scorer_default.events) == 1
    assert scorer_default.events[0]["type"] == "multiple_faces"

    # 2. With guard enabled (require_consecutive_multi_face = True):
    # Single frame proposal is suppressed
    scorer_guarded = RiskScorer(require_consecutive_multi_face=True)
    scorer_guarded.update(5.0, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_guarded.update(5.25, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_guarded.finalize(10.0)
    assert len(scorer_guarded.events) == 0  # suppressed!

    # 2 consecutive frames proposal is confirmed
    scorer_guarded2 = RiskScorer(require_consecutive_multi_face=True)
    scorer_guarded2.update(5.0, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_guarded2.update(5.25, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_guarded2.update(5.5, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_guarded2.finalize(10.0)
    assert len(scorer_guarded2.events) == 1
    assert scorer_guarded2.events[0]["type"] == "multiple_faces"


def test_multi_face_timestamp_gap_and_consecutive_integrity():
    """
    Task 1 Verification (Fix L19 Rigor):
    Tests max timestamp gap check for consecutive multi-face detections:
      1. Two genuinely consecutive frames (delta_t = 0.25s <= 1.5 * (1/4) = 0.375s) -> confirmed.
      2. Two detections separated by large time gap (delta_t = 8.0s > 0.375s) -> suppressed.
      3. A True -> False -> True sequence (both single frames separated by False) -> suppressed.
      4. Irregular frame timestamps:
         - Within tolerance (delta_t = 0.30s <= 0.375s) -> confirmed.
         - Exceeding tolerance (delta_t = 0.45s > 0.375s) -> resets counter, suppressed.
      5. Default behavior: require_consecutive_multi_face=False allows immediate flagging.
    """
    # 1. Two genuinely consecutive frames at 4 FPS (interval 0.25s)
    scorer_consec = RiskScorer(require_consecutive_multi_face=True, sample_fps=4)
    scorer_consec.update(2.00, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_consec.update(2.25, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_consec.update(2.50, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_consec.finalize(5.0)
    assert len(scorer_consec.events) == 1, "Two genuinely consecutive frames must confirm multiple_faces"
    assert scorer_consec.events[0]["type"] == "multiple_faces"

    # 2. Two detections separated by a large time gap (8.0s gap > 0.375s)
    # Neither occurrence had 2 consecutive frames; large gap must reset counter
    scorer_gap = RiskScorer(require_consecutive_multi_face=True, sample_fps=4)
    scorer_gap.update(2.00, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_gap.update(10.00, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_gap.update(10.50, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_gap.finalize(12.0)
    assert len(scorer_gap.events) == 0, "Detections separated by large gap must NOT bridge to form consecutive frames"

    # 3. True -> False -> True sequence (both single frames separated by False)
    scorer_tft = RiskScorer(require_consecutive_multi_face=True, sample_fps=4)
    scorer_tft.update(1.00, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_tft.update(1.25, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_tft.update(1.50, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_tft.update(1.75, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_tft.finalize(3.0)
    assert len(scorer_tft.events) == 0, "True -> False -> True single-frame blips must both be suppressed"

    # 4. Irregular frame timestamps:
    # 4a. Jittered timestamps within 1.5x tolerance (0.30s <= 0.375s)
    scorer_jitter_ok = RiskScorer(require_consecutive_multi_face=True, sample_fps=4)
    scorer_jitter_ok.update(2.00, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_jitter_ok.update(2.30, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})  # 0.30s gap <= 0.375s
    scorer_jitter_ok.update(2.55, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_jitter_ok.finalize(4.0)
    assert len(scorer_jitter_ok.events) == 1, "Frames within 1.5x tolerance must be accepted as consecutive"

    # 4b. Jittered timestamps exceeding 1.5x tolerance (0.45s > 0.375s) -> resets counter
    scorer_jitter_exceed = RiskScorer(require_consecutive_multi_face=True, sample_fps=4)
    scorer_jitter_exceed.update(2.00, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_jitter_exceed.update(2.45, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})  # 0.45s gap > 0.375s
    scorer_jitter_exceed.update(2.70, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_jitter_exceed.finalize(4.0)
    assert len(scorer_jitter_exceed.events) == 0, "Frame interval exceeding 1.5x tolerance must reset counter and suppress"

    # 5. Default behavior verification (require_consecutive_multi_face=False)
    scorer_default = RiskScorer(require_consecutive_multi_face=False, sample_fps=4)
    scorer_default.update(1.00, {"multiple_faces": True, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_default.update(1.25, {"multiple_faces": False, "head_turned": False, "gaze_away": False, "no_face": False})
    scorer_default.finalize(2.0)
    assert len(scorer_default.events) == 1, "Default config must preserve immediate flagging without consecutive requirement"


def test_rescore_telemetry_returns_normalized_fields():
    """
    Verifies that rescore_telemetry() returns normalized_score,
    normalized_risk_level, and window_analysis in its output dict.
    """
    debug_frames = [
        {"time_sec": 0.0, "faces": 1, "yaw": 0.0, "pitch": 0.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
        {"time_sec": 5.0, "faces": 1, "yaw": 35.0, "pitch": 0.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
        {"time_sec": 5.5, "faces": 1, "yaw": 35.0, "pitch": 0.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
        {"time_sec": 6.0, "faces": 1, "yaw": 0.0, "pitch": 0.0, "gaze_h_ratio": 0.5, "gaze_v_ratio": 0.5},
    ]
    res = rescore_telemetry(debug_frames)

    assert "risk_score" in res
    assert "risk_level" in res
    assert "normalized_score" in res
    assert "normalized_risk_level" in res
    assert "window_analysis" in res
    assert res["risk_score"] == 15
    assert res["normalized_score"] == 15
    assert res["normalized_risk_level"] == "Low"
    assert len(res["window_analysis"]) == 1
