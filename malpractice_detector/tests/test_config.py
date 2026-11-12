"""
test_config.py
==============
WP0 Acceptance Test: Parameter Baseline Integrity Guard.

Verifies that:
1. Every tunable threshold in scoring_config.py matches the documented baseline.
2. All modules (scoring, head_pose, eye_tracking, pipeline, demo_data) import
   consistently from scoring_config.
3. Risk band definitions, event weights, duration gates, and frequency rules
   remain strictly consistent with the project specification.

If any parameter is accidentally altered or drifts between modules,
this test suite will fail.
"""

import pytest
import scoring_config as cfg
import modules.scoring as scoring
import modules.head_pose as head_pose
import modules.eye_tracking as eye_tracking
import pipeline
import demo_data


def test_sampling_rate():
    assert cfg.SAMPLE_FPS == 4
    assert pipeline.SAMPLE_FPS == cfg.SAMPLE_FPS


def test_head_pose_thresholds():
    assert cfg.YAW_THRESHOLD == 26.0
    assert cfg.PITCH_DOWN_THRESHOLD == 26.0
    assert cfg.PITCH_UP_THRESHOLD == 20.0
    assert head_pose.YAW_THRESHOLD == cfg.YAW_THRESHOLD
    assert head_pose.PITCH_DOWN_THRESHOLD == cfg.PITCH_DOWN_THRESHOLD
    assert head_pose.PITCH_UP_THRESHOLD == cfg.PITCH_UP_THRESHOLD


def test_eye_gaze_thresholds():
    assert cfg.HORIZONTAL_CENTER_RANGE == (0.35, 0.65)
    assert cfg.VERTICAL_DOWN_THRESHOLD == 0.65
    assert cfg.VERTICAL_UP_THRESHOLD == 0.22
    assert eye_tracking.HORIZONTAL_CENTER_RANGE == cfg.HORIZONTAL_CENTER_RANGE
    assert eye_tracking.VERTICAL_DOWN_THRESHOLD == cfg.VERTICAL_DOWN_THRESHOLD
    assert eye_tracking.VERTICAL_UP_THRESHOLD == cfg.VERTICAL_UP_THRESHOLD


def test_event_weights():
    expected_weights = {
        "no_face": 6,
        "multiple_faces": 30,
        "gaze_away": 12,
        "head_turned": 15,
    }
    assert cfg.EVENT_WEIGHTS == expected_weights
    assert scoring.EVENT_WEIGHTS == expected_weights

    expected_freq_weights = {
        "gaze_away": 18,
        "head_turned": 18,
    }
    assert cfg.FREQUENCY_WEIGHTS == expected_freq_weights
    assert scoring.FREQUENCY_WEIGHTS == expected_freq_weights


def test_duration_gates():
    assert cfg.MIN_EVENT_DURATION_SEC == 1.0
    assert scoring.MIN_EVENT_DURATION_SEC == cfg.MIN_EVENT_DURATION_SEC

    expected_gates = {
        "head_turned": 0.4,
        "multiple_faces": 0.0,
        "no_face": 1.0,
        "gaze_away": 0.7,
    }
    assert cfg.DEFAULT_MIN_EVENT_DURATIONS == expected_gates
    assert scoring.DEFAULT_MIN_EVENT_DURATIONS == expected_gates


def test_frequency_rule():
    assert cfg.FREQUENCY_WINDOW_SEC == 10.0
    assert cfg.FREQUENCY_MIN_COUNT == 2
    assert cfg.FREQUENCY_TRACKED_TYPES == {"gaze_away", "head_turned"}
    assert scoring.FREQUENCY_WINDOW_SEC == cfg.FREQUENCY_WINDOW_SEC
    assert scoring.FREQUENCY_MIN_COUNT == cfg.FREQUENCY_MIN_COUNT
    assert scoring.FREQUENCY_TRACKED_TYPES == cfg.FREQUENCY_TRACKED_TYPES


def test_immediate_event_types():
    assert cfg.IMMEDIATE_EVENT_TYPES == {"multiple_faces"}
    assert scoring.IMMEDIATE_EVENT_TYPES == cfg.IMMEDIATE_EVENT_TYPES


def test_risk_bands():
    assert cfg.RISK_BAND_MEDIUM == 25
    assert cfg.RISK_BAND_HIGH == 60
    assert cfg.RISK_SCORE_CAP == 100

    scorer = scoring.RiskScorer()
    assert scorer.risk_level(0) == "Low"
    assert scorer.risk_level(24) == "Low"
    assert scorer.risk_level(25) == "Medium"
    assert scorer.risk_level(59) == "Medium"
    assert scorer.risk_level(60) == "High"
    assert scorer.risk_level(100) == "High"
    assert scorer.risk_level(150) == "High"


def test_time_normalization_config():
    assert cfg.TIME_WINDOW_SEC == 600.0
    assert cfg.TIME_NORM_PERSISTENCE_ALPHA == 0.10
    assert cfg.WINDOW_PER_TYPE_CAPS["gaze_away"] == 24
    assert cfg.WINDOW_PER_TYPE_CAPS["head_turned"] == 30
    assert cfg.WINDOW_PER_TYPE_CAPS["no_face"] == 18
    assert cfg.WINDOW_PER_TYPE_CAPS["multiple_faces"] == 60
    assert cfg.REQUIRE_CONSECUTIVE_FRAMES_MULTI_FACE is False
