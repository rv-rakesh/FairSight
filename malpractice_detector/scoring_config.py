"""
scoring_config.py
=================
Single source of truth for every tunable parameter in the FairSight
detection and scoring system.

Every weight, gate, frequency setting, head and gaze threshold, sampling
rate and risk band is defined here and ONLY here. All other modules
(scoring.py, head_pose.py, eye_tracking.py, pipeline.py, api.py, app.py,
demo_data.py) import from this file.

If you need to change a threshold, change it here. If a test fails after
a change, the system is telling you the change has consequences.

Created as part of WP0 (Baseline and Hygiene). See handoff document
Section 9, WP0 acceptance criteria.
"""

# ─────────────────────────────────────────────────────────────────────
# 1. SAMPLING
# ─────────────────────────────────────────────────────────────────────

SAMPLE_FPS = 4  # frames per second; temporal resolution = 0.25 s

# ─────────────────────────────────────────────────────────────────────
# 2. HEAD POSE THRESHOLDS (degrees)
#    Calibrated against real footage: natural pitch median ~12°,
#    90th percentile ~17°. Yaw calibrated for natural screen scanning.
# ─────────────────────────────────────────────────────────────────────

YAW_THRESHOLD = 26.0         # |yaw| beyond this = looking away sideways
PITCH_DOWN_THRESHOLD = 26.0  # pitch above this = head tilted down significantly
PITCH_UP_THRESHOLD = 20.0    # pitch below -this = head tilted up significantly

# ─────────────────────────────────────────────────────────────────────
# 3. EYE GAZE THRESHOLDS (iris-ratio, 0.0–1.0)
#    0.5 = centred; lower = more left; higher = more right
# ─────────────────────────────────────────────────────────────────────

HORIZONTAL_CENTER_RANGE = (0.35, 0.65)  # inside this = "center"
VERTICAL_DOWN_THRESHOLD = 0.65          # above this = looking down
VERTICAL_UP_THRESHOLD = 0.22            # below this = looking up

# ─────────────────────────────────────────────────────────────────────
# 4. SCORING WEIGHTS
#    Points added per confirmed event. These are policy parameters:
#    weight ≈ escalation_threshold / tolerated_incidents.
#    They are NOT probabilities and NOT proven optima.
# ─────────────────────────────────────────────────────────────────────

EVENT_WEIGHTS = {
    "no_face": 6,             # candidate left the frame
    "multiple_faces": 30,     # extra person — highest severity
    "gaze_away": 12,          # sustained off-center gaze
    "head_turned": 15,        # sustained yaw/pitch beyond threshold
}

FREQUENCY_WEIGHTS = {
    "gaze_away": 18,          # repeated brief gaze events in window
    "head_turned": 18,        # repeated brief head-turn events in window
}

# ─────────────────────────────────────────────────────────────────────
# 5. DURATION GATES (seconds)
#    A condition must hold continuously for at least this long before
#    becoming a confirmed sustained event. Protects honest candidates
#    from being flagged for natural brief glances.
# ─────────────────────────────────────────────────────────────────────

MIN_EVENT_DURATION_SEC = 1.0  # global fallback (used if per-type not set)

DEFAULT_MIN_EVENT_DURATIONS = {
    "head_turned": 0.4,       # deliberate turn is significant even when brief
    "multiple_faces": 0.0,    # immediate — any occurrence counts
    "no_face": 1.0,           # candidate must be absent for 1 s
    "gaze_away": 0.7,         # avoids flagging natural reading saccades
}

# ─────────────────────────────────────────────────────────────────────
# 6. FREQUENCY DETECTION
#    Layer 2: catches repeated brief events that individually don't
#    reach the sustained-duration gate but form a suspicious pattern.
# ─────────────────────────────────────────────────────────────────────

FREQUENCY_WINDOW_SEC = 10.0       # rolling window size
FREQUENCY_MIN_COUNT = 2           # minimum brief events to trigger
FREQUENCY_TRACKED_TYPES = {"gaze_away", "head_turned"}

# ─────────────────────────────────────────────────────────────────────
# 7. IMMEDIATE EVENT TYPES
#    Layer 3: flagged on ANY occurrence regardless of duration.
#    There is no innocent reason for a second face to appear.
# ─────────────────────────────────────────────────────────────────────

IMMEDIATE_EVENT_TYPES = {"multiple_faces"}

# ─────────────────────────────────────────────────────────────────────
# 8. RISK BANDS
#    Score is 0–100 (capped). Bands determine the report verdict.
#    The score is a penalty index, not a probability.
# ─────────────────────────────────────────────────────────────────────

RISK_BAND_MEDIUM = 25   # score >= this = Medium
RISK_BAND_HIGH = 60     # score >= this = High
RISK_SCORE_CAP = 100    # maximum score

# ─────────────────────────────────────────────────────────────────────
# 9. DETECTION CONFIDENCE THRESHOLDS
#    Minimum confidence for each detector stage in the cascade.
# ─────────────────────────────────────────────────────────────────────

FACE_LANDMARKER_MIN_CONFIDENCE = 0.35
BLAZE_FACE_MIN_CONFIDENCE = 0.55
OBJECT_DETECTOR_MIN_CONFIDENCE = 0.18
HAND_LANDMARKER_MIN_CONFIDENCE = 0.35

# ─────────────────────────────────────────────────────────────────────
# 10. DEMO DATA
# ─────────────────────────────────────────────────────────────────────

DEMO_STEP_SEC = 0.5  # time step for simulated scenario telemetry

# ─────────────────────────────────────────────────────────────────────
# 11. TIME NORMALISATION (Decision D5 & Fix L16)
#     Partitions exam duration into 10-minute windows (600s).
#     Applies per-type caps per window to protect honest candidates in
#     long exams (e.g. 3 hours) from accumulating false High scores.
# ─────────────────────────────────────────────────────────────────────

TIME_WINDOW_SEC = 600.0            # 10 minutes per normalization block
TIME_NORM_PERSISTENCE_ALPHA = 0.10  # cross-window accumulation factor

WINDOW_PER_TYPE_CAPS = {
    "gaze_away": 24,               # max 2 sustained gaze events per 10m
    "head_turned": 30,             # max 2 sustained head turns per 10m
    "no_face": 18,                 # max 3 short absences per 10m
    "frequent_gaze_away": 18,      # max 1 frequency cluster per 10m
    "frequent_head_turned": 18,    # max 1 frequency cluster per 10m
    "multiple_faces": 60,          # max 2 immediate flags per 10m
}

# ─────────────────────────────────────────────────────────────────────
# 12. MULTI-FACE DETECTION RIGOR (Fix L19)
#     When True, requires at least 2 consecutive frames with multiple
#     faces before confirming an immediate multiple_faces event,
#     filtering single-frame motion blur or hand-near-face artifacts.
# ─────────────────────────────────────────────────────────────────────

REQUIRE_CONSECUTIVE_FRAMES_MULTI_FACE = False
