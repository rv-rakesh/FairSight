import pytest
from modules.scoring import RiskScorer, rescore_telemetry, EVENT_WEIGHTS

def test_sustained_duration_guard():
    scorer = RiskScorer(min_event_duration_sec=2.0)
    # 0.4s glance away (should NOT be confirmed)
    scorer.update(1.0, {'no_face': False, 'multiple_faces': False, 'gaze_away': True, 'head_turned': False})
    scorer.update(1.4, {'no_face': False, 'multiple_faces': False, 'gaze_away': False, 'head_turned': False})
    scorer.finalize(2.0)
    assert len(scorer.events) == 0
    assert scorer.compute_risk_score() == 0

def test_sustained_duration_confirmed():
    scorer = RiskScorer(min_event_duration_sec=2.0)
    # 3.0s sustained glance away (SHOULD be confirmed)
    scorer.update(1.0, {'no_face': False, 'multiple_faces': False, 'gaze_away': True, 'head_turned': False})
    scorer.update(4.0, {'no_face': False, 'multiple_faces': False, 'gaze_away': False, 'head_turned': False})
    scorer.finalize(5.0)
    assert len(scorer.events) == 1
    assert scorer.events[0]['type'] == 'gaze_away'
    assert scorer.compute_risk_score() == EVENT_WEIGHTS['gaze_away']

def test_frequency_pattern_layer():
    scorer = RiskScorer(min_event_duration_sec=2.0)
    # 3 brief glances within 6 seconds (each 0.4s)
    # Glance 1
    scorer.update(1.0, {'no_face': False, 'multiple_faces': False, 'gaze_away': True, 'head_turned': False})
    scorer.update(1.4, {'no_face': False, 'multiple_faces': False, 'gaze_away': False, 'head_turned': False})
    # Glance 2
    scorer.update(3.0, {'no_face': False, 'multiple_faces': False, 'gaze_away': True, 'head_turned': False})
    scorer.update(3.4, {'no_face': False, 'multiple_faces': False, 'gaze_away': False, 'head_turned': False})
    # Glance 3
    scorer.update(5.0, {'no_face': False, 'multiple_faces': False, 'gaze_away': True, 'head_turned': False})
    scorer.update(5.4, {'no_face': False, 'multiple_faces': False, 'gaze_away': False, 'head_turned': False})
    scorer.finalize(6.0)

    frequent_events = [e for e in scorer.events if e['type'] == 'frequent_gaze_away']
    assert len(frequent_events) == 1
    assert frequent_events[0]['weight'] == 18

def test_immediate_multiple_faces():
    scorer = RiskScorer(min_event_duration_sec=2.0)
    # Brief 0.5s second face appearance
    scorer.update(2.0, {'no_face': False, 'multiple_faces': True, 'gaze_away': False, 'head_turned': False})
    scorer.update(2.5, {'no_face': False, 'multiple_faces': False, 'gaze_away': False, 'head_turned': False})
    scorer.finalize(3.0)
    assert len(scorer.events) == 1
    assert scorer.events[0]['type'] == 'multiple_faces'
    assert scorer.events[0]['weight'] == 30

def test_rescore_telemetry():
    debug_frames = [
        {'time_sec': 1.0, 'faces': 1, 'yaw': 0.0, 'pitch': 10.0, 'gaze_h_ratio': 0.5, 'gaze_v_ratio': 0.5},
        {'time_sec': 2.0, 'faces': 1, 'yaw': -30.0, 'pitch': 10.0, 'gaze_h_ratio': 0.5, 'gaze_v_ratio': 0.5},
        {'time_sec': 3.0, 'faces': 1, 'yaw': -30.0, 'pitch': 10.0, 'gaze_h_ratio': 0.5, 'gaze_v_ratio': 0.5},
        {'time_sec': 5.0, 'faces': 1, 'yaw': -30.0, 'pitch': 10.0, 'gaze_h_ratio': 0.5, 'gaze_v_ratio': 0.5},
        {'time_sec': 6.0, 'faces': 1, 'yaw': 0.0, 'pitch': 10.0, 'gaze_h_ratio': 0.5, 'gaze_v_ratio': 0.5},
    ]
    # Calibrated yaw threshold is 26.0 -> yaw -30.0 triggers head_turned for 4.0s (sustained)
    res_default = rescore_telemetry(debug_frames)
    assert res_default['risk_score'] > 0

    # Strict yaw threshold (40.0) -> yaw -30.0 is now below threshold!
    res_relaxed = rescore_telemetry(debug_frames, config={'yaw_threshold': 40.0})
    assert res_relaxed['risk_score'] == 0


def test_gaze_head_decoupling_prevents_double_counting():
    """Turning head sideways displaces 2D iris position; ensure gaze_away is decoupled so it doesn't double-count."""
    debug_frames = [
        {'time_sec': 1.0, 'faces': 1, 'yaw': 0.0, 'pitch': 10.0, 'gaze_h_ratio': 0.5, 'gaze_v_ratio': 0.5},
        # Candidate turns head sideways (yaw 30°) and iris also shifts (gaze_h 0.8)
        {'time_sec': 2.0, 'faces': 1, 'yaw': 30.0, 'pitch': 10.0, 'gaze_h_ratio': 0.8, 'gaze_v_ratio': 0.5},
        {'time_sec': 5.0, 'faces': 1, 'yaw': 30.0, 'pitch': 10.0, 'gaze_h_ratio': 0.8, 'gaze_v_ratio': 0.5},
        {'time_sec': 6.0, 'faces': 1, 'yaw': 0.0, 'pitch': 10.0, 'gaze_h_ratio': 0.5, 'gaze_v_ratio': 0.5},
    ]
    res = rescore_telemetry(debug_frames)
    event_types = [e['type'] for e in res['events']]
    assert 'head_turned' in event_types
    # gaze_away MUST NOT be flagged for the same movement
    assert 'gaze_away' not in event_types
    # Only head_turned weight (15), not double-counted (15+12=27)
    assert res['risk_score'] == EVENT_WEIGHTS['head_turned']


def test_risk_level_calibration():
    scorer = RiskScorer()
    assert scorer.risk_level(0) == "Low"
    assert scorer.risk_level(24) == "Low"
    assert scorer.risk_level(25) == "Medium"
    assert scorer.risk_level(59) == "Medium"
    assert scorer.risk_level(60) == "High"
    assert scorer.risk_level(100) == "High"

