"""
scoring.py
Rule-based cheating-risk scoring engine.

Two complementary detection layers, both explainable (every point traces
to a named rule, never a black-box model decision):

1. SUSTAINED EVENTS (original design, from user research):
   don't flag a single brief glance — only flag behaviour that holds
   continuously for at least MIN_EVENT_DURATION_SEC. This is what
   protects honest candidates from being flagged for a momentary
   glance down to think.

2. FREQUENCY-PATTERN EVENTS (added after real-footage testing showed a
   real gap: someone repeatedly glancing away many times, each glance
   too brief to be "sustained," is itself a suspicious pattern that
   layer 1 alone completely misses). If a condition recurs
   FREQUENCY_MIN_COUNT+ times within a rolling FREQUENCY_WINDOW_SEC
   window, that cluster is flagged as its own event — explainable as
   "N brief occurrences within W seconds," not a mystery score bump.

Every single raw flagged frame (sustained or not) is also recorded in
activity_log, so the report can show a candidate/evaluator "here is
every suspicious moment, at its exact timestamp" — not just the
confirmed events that made it into the final score.
"""

from scoring_config import (
    YAW_THRESHOLD,
    PITCH_DOWN_THRESHOLD,
    PITCH_UP_THRESHOLD,
    EVENT_WEIGHTS,
    FREQUENCY_WEIGHTS,
    MIN_EVENT_DURATION_SEC,
    DEFAULT_MIN_EVENT_DURATIONS,
    FREQUENCY_WINDOW_SEC,
    FREQUENCY_MIN_COUNT,
    FREQUENCY_TRACKED_TYPES,
    IMMEDIATE_EVENT_TYPES,
    RISK_BAND_MEDIUM,
    RISK_BAND_HIGH,
    RISK_SCORE_CAP,
    HORIZONTAL_CENTER_RANGE,
    VERTICAL_DOWN_THRESHOLD,
    VERTICAL_UP_THRESHOLD,
    TIME_WINDOW_SEC,
    TIME_NORM_PERSISTENCE_ALPHA,
    WINDOW_PER_TYPE_CAPS,
    REQUIRE_CONSECUTIVE_FRAMES_MULTI_FACE,
    SAMPLE_FPS,
)


class RiskScorer:
    def __init__(
        self,
        min_event_duration_sec=MIN_EVENT_DURATION_SEC,
        min_event_durations=None,
        event_weights=None,
        frequency_weights=None,
        frequency_window_sec=FREQUENCY_WINDOW_SEC,
        frequency_min_count=FREQUENCY_MIN_COUNT,
        immediate_event_types=None,
        require_consecutive_multi_face=REQUIRE_CONSECUTIVE_FRAMES_MULTI_FACE,
        sample_fps=SAMPLE_FPS,
    ):
        self.min_event_duration_sec = min_event_duration_sec
        self.min_event_durations = dict(DEFAULT_MIN_EVENT_DURATIONS) if min_event_durations is None else dict(min_event_durations)
        if min_event_duration_sec != MIN_EVENT_DURATION_SEC and min_event_durations is None:
            for k in list(self.min_event_durations.keys()):
                if k != "multiple_faces":
                    self.min_event_durations[k] = min_event_duration_sec
        self.event_weights = dict(EVENT_WEIGHTS) if event_weights is None else dict(event_weights)
        self.frequency_weights = dict(FREQUENCY_WEIGHTS) if frequency_weights is None else dict(frequency_weights)
        self.frequency_window_sec = frequency_window_sec
        self.frequency_min_count = frequency_min_count
        self.immediate_event_types = set(IMMEDIATE_EVENT_TYPES) if immediate_event_types is None else set(immediate_event_types)
        self.require_consecutive_multi_face = require_consecutive_multi_face
        self.sample_fps = max(1e-3, float(sample_fps))
        self.max_consecutive_gap_sec = 1.5 / self.sample_fps

        self.events = []                # confirmed events (sustained + frequency-pattern)
        self.activity_log = []          # EVERY raw flagged frame, regardless of duration
        self._active_conditions = {}    # condition_name -> start_timestamp
        self._condition_frame_counts = {} # condition_name -> consecutive frame count
        self._last_condition_timestamp = {} # condition_name -> timestamp of most recent active frame
        self._recent_occurrences = {t: [] for t in FREQUENCY_TRACKED_TYPES}

    def update(self, timestamp_sec, conditions, details=None):
        """
        conditions: dict of {condition_name: bool} for the current frame,
        e.g. {"no_face": False, "multiple_faces": False,
              "gaze_away": True, "head_turned": False}
        details: optional dict of {condition_name: str} with a short
        human-readable detail for that condition this frame, e.g.
        {"gaze_away": "left", "head_turned": "yaw -24.8 deg"} — shown
        in the activity log so evaluators see WHY, not just WHAT.
        Call this once per analysed frame, in timestamp order.
        """
        details = details or {}

        for name, is_active in conditions.items():
            if is_active:
                self.activity_log.append({
                    "time_sec": round(timestamp_sec, 2),
                    "type": name,
                    "detail": details.get(name, ""),
                })

                if name == "multiple_faces":
                    # Fix L19: Check gap for consecutive frame integrity
                    if name in self._last_condition_timestamp:
                        gap = timestamp_sec - self._last_condition_timestamp[name]
                        if gap > self.max_consecutive_gap_sec:
                            # Gap exceeded permitted interval (1.5 / sample_fps) -> frames are NOT consecutive!
                            # Close prior condition at its last observed timestamp and reset counter
                            if name in self._active_conditions:
                                self._close_condition(name, self._last_condition_timestamp[name])
                            self._condition_frame_counts[name] = 1
                            self._active_conditions[name] = timestamp_sec
                        else:
                            self._condition_frame_counts[name] = self._condition_frame_counts.get(name, 0) + 1
                    else:
                        self._condition_frame_counts[name] = 1
                        self._active_conditions[name] = timestamp_sec
                    self._last_condition_timestamp[name] = timestamp_sec
                else:
                    if name not in self._active_conditions:
                        self._active_conditions[name] = timestamp_sec
                    self._condition_frame_counts[name] = self._condition_frame_counts.get(name, 0) + 1
                    self._last_condition_timestamp[name] = timestamp_sec
            else:
                self._last_condition_timestamp.pop(name, None)
                if name in self._active_conditions:
                    self._close_condition(name, timestamp_sec)

    def _close_condition(self, name, end_timestamp_sec):
        if name not in self._active_conditions:
            return
        start_timestamp_sec = self._active_conditions.pop(name)
        frames_count = self._condition_frame_counts.pop(name, 1)
        self._last_condition_timestamp.pop(name, None)
        duration = end_timestamp_sec - start_timestamp_sec
        is_immediate = name in self.immediate_event_types

        # Fix L19: filter single-frame transient multi-face proposals when guard is enabled
        if is_immediate and name == "multiple_faces" and self.require_consecutive_multi_face and frames_count < 2:
            return

        req_duration = self.min_event_durations.get(name, self.min_event_duration_sec)
        if duration >= req_duration or is_immediate:
            note = "sustained" if duration >= req_duration else "brief but flagged immediately"
            self.events.append({
                "type": name,
                "start_sec": round(start_timestamp_sec, 2),
                "end_sec": round(end_timestamp_sec, 2),
                "duration_sec": round(duration, 2),
                "weight": self.event_weights.get(name, 5),
                "note": note,
            })
            # A sustained event is confirmed and penalized; remove from recent brief occurrences
            # so the sustained event does not double-trigger a "brief occurrences" event
            if name in self._recent_occurrences:
                self._recent_occurrences[name] = [item for item in self._recent_occurrences[name] if item[1] < start_timestamp_sec]
        else:
            # Condition closed before reaching sustained duration: genuine brief occurrence!
            if name in FREQUENCY_TRACKED_TYPES:
                self._register_occurrence(name, start_timestamp_sec, end_timestamp_sec)

    def _register_occurrence(self, name, start_sec, end_sec):
        occurrences = self._recent_occurrences[name]
        occurrences.append((start_sec, end_sec))
        # keep only occurrences within the rolling window
        window_start = end_sec - self.frequency_window_sec
        occurrences[:] = [item for item in occurrences if item[1] >= window_start]

        if len(occurrences) >= self.frequency_min_count:
            first_start = occurrences[0][0]
            self.events.append({
                "type": f"frequent_{name}",
                "start_sec": round(first_start, 2),
                "end_sec": round(end_sec, 2),
                "duration_sec": round(end_sec - first_start, 2),
                "weight": self.frequency_weights.get(name, 18),
                "note": f"{len(occurrences)} brief occurrences within {self.frequency_window_sec:.0f}s",
            })
            occurrences.clear()

    def finalize(self, final_timestamp_sec):
        """Call once after the last frame to close any still-active conditions."""
        for name in list(self._active_conditions.keys()):
            self._close_condition(name, final_timestamp_sec)

    def compute_risk_score(self):
        """
        Returns an integer 0-100 risk score. Simple additive model, capped
        at RISK_SCORE_CAP (100). Multiple occurrences of the same event type — sustained or
        frequency-pattern — each contribute independently, so repeated
        lapses (even brief, repeated ones) accumulate risk instead of
        vanishing because no single glance was long enough alone.
        """
        raw_score = sum(e["weight"] for e in self.events)
        return min(RISK_SCORE_CAP, raw_score)

    def risk_level(self, score=None):
        if score is None:
            score = self.compute_risk_score()
        if score >= RISK_BAND_HIGH:
            return "High"
        elif score >= RISK_BAND_MEDIUM:
            return "Medium"
        else:
            return "Low"

    def compute_normalized_score(self, session_duration_sec=None, persistence_alpha=TIME_NORM_PERSISTENCE_ALPHA):
        """
        Computes time-normalized risk score using the Windowed Per-Type Capped
        Severity Model (Decision D5 & Fix L16).

        Partitions session into 10-minute windows (600s). Each window caps points
        per event type (WINDOW_PER_TYPE_CAPS). The session normalized score is:
            S_norm = min(100, S_peak + alpha * S_other_windows)

        Protects honest candidates during long examinations (e.g. 3 hours)
        from accumulating false High risk scores from sparse natural glances.

        Returns dict:
          {
            "normalized_score": int (0-100),
            "normalized_risk_level": str ("Low", "Medium", "High"),
            "raw_score": int,
            "raw_risk_level": str,
            "window_analysis": list of window dicts
          }
        """
        import math
        raw_score = self.compute_risk_score()
        raw_level = self.risk_level(raw_score)

        if not self.events and not self.activity_log:
            return {
                "normalized_score": 0,
                "normalized_risk_level": "Low",
                "raw_score": 0,
                "raw_risk_level": "Low",
                "window_analysis": [],
            }

        # Determine total session duration
        if session_duration_sec is None or session_duration_sec <= 0:
            max_ev = max((e.get("end_sec", e.get("start_sec", 0.0)) for e in self.events), default=0.0)
            max_act = max((a.get("time_sec", 0.0) for a in self.activity_log), default=0.0)
            session_duration_sec = max(max_ev, max_act, 1.0)

        window_size = TIME_WINDOW_SEC
        num_windows = max(1, math.ceil(session_duration_sec / window_size))

        # Initialize window structures
        windows = [
            {
                "window_index": k,
                "start_sec": round(k * window_size, 1),
                "end_sec": round(min(session_duration_sec, (k + 1) * window_size), 1),
                "events": [],
                "points_by_type": {},
                "capped_points_by_type": {},
                "window_score": 0,
            }
            for k in range(num_windows)
        ]

        # Assign each event to its starting window
        for ev in self.events:
            ev_start = ev.get("start_sec", 0.0)
            w_idx = min(num_windows - 1, max(0, int(ev_start // window_size)))
            windows[w_idx]["events"].append(ev)
            ev_type = ev.get("type", "unknown")
            ev_weight = ev.get("weight", 0)
            windows[w_idx]["points_by_type"][ev_type] = windows[w_idx]["points_by_type"].get(ev_type, 0) + ev_weight

        # Compute capped score per window
        for w in windows:
            total_capped = 0
            for ev_type, pts in w["points_by_type"].items():
                cap = WINDOW_PER_TYPE_CAPS.get(ev_type, 30)
                capped = min(cap, pts)
                w["capped_points_by_type"][ev_type] = capped
                total_capped += capped
            w["window_score"] = min(RISK_SCORE_CAP, total_capped)

        window_scores = [w["window_score"] for w in windows]
        peak_score = max(window_scores)
        peak_idx = window_scores.index(peak_score)

        other_scores_sum = sum(score for idx, score in enumerate(window_scores) if idx != peak_idx)
        alpha = float(persistence_alpha)
        normalized_score = min(RISK_SCORE_CAP, round(peak_score + alpha * other_scores_sum))
        normalized_level = self.risk_level(normalized_score)

        return {
            "normalized_score": int(normalized_score),
            "normalized_risk_level": normalized_level,
            "raw_score": int(raw_score),
            "raw_risk_level": raw_level,
            "window_analysis": windows,
        }


def rescore_telemetry(debug_frames, config=None):
    """
    Re-derives conditions from raw frame telemetry against custom thresholds
    and re-runs scoring in-memory (<50ms).

    debug_frames: list of dicts with:
      - time_sec: float
      - faces: int
      - yaw: float (optional)
      - pitch: float (optional)
      - gaze_h_ratio: float (optional)
      - gaze_v_ratio: float (optional)
      - gaze_direction: str (optional fallback)

    config: optional dict with custom threshold overrides:
      - yaw_threshold: float (default 26.0)
      - pitch_down_threshold: float (default 26.0)
      - min_event_duration_sec: float (default 1.0)
      - frequency_window_sec: float (default 10.0)
      - frequency_min_count: int (default 2)
      - event_weights: dict
      - frequency_weights: dict
      - horizontal_center_range: tuple (default (0.35, 0.65))
      - vertical_down_threshold: float (default 0.65)
      - vertical_up_threshold: float (default 0.22)
    """
    if not debug_frames:
        return {
            "risk_score": 0,
            "risk_level": "Low",
            "normalized_score": 0,
            "normalized_risk_level": "Low",
            "window_analysis": [],
            "events": [],
            "activity_log": [],
            "frames_analysed": 0,
            "video_duration_sec": 0.0,
            "debug_frames": [],
        }

    config = config or {}
    yaw_thresh = config.get("yaw_threshold", YAW_THRESHOLD)
    pitch_thresh = config.get("pitch_down_threshold", PITCH_DOWN_THRESHOLD)
    h_range = config.get("horizontal_center_range", HORIZONTAL_CENTER_RANGE)
    v_down = config.get("vertical_down_threshold", VERTICAL_DOWN_THRESHOLD)
    v_up = config.get("vertical_up_threshold", VERTICAL_UP_THRESHOLD)

    min_dur = config.get("min_event_duration_sec", MIN_EVENT_DURATION_SEC)
    min_durs = config.get("min_event_durations", DEFAULT_MIN_EVENT_DURATIONS)
    f_win = config.get("frequency_window_sec", FREQUENCY_WINDOW_SEC)
    f_cnt = config.get("frequency_min_count", FREQUENCY_MIN_COUNT)
    ev_w = config.get("event_weights", EVENT_WEIGHTS)
    fq_w = config.get("frequency_weights", FREQUENCY_WEIGHTS)
    imm_types = config.get("immediate_event_types", IMMEDIATE_EVENT_TYPES)

    scorer = RiskScorer(
        min_event_duration_sec=min_dur,
        min_event_durations=min_durs,
        event_weights=ev_w,
        frequency_weights=fq_w,
        frequency_window_sec=f_win,
        frequency_min_count=f_cnt,
        immediate_event_types=imm_types,
    )

    last_timestamp = 0.0
    rescored_debug_frames = []

    for frame in debug_frames:
        t = frame.get("time_sec", 0.0)
        last_timestamp = t
        faces = frame.get("faces", 1)
        yaw = frame.get("yaw")
        pitch = frame.get("pitch")
        gaze_h = frame.get("gaze_h_ratio")
        gaze_v = frame.get("gaze_v_ratio")

        conditions = {
            "no_face": faces == 0,
            "multiple_faces": faces > 1,
            "gaze_away": False,
            "head_turned": False,
        }
        details = {}
        direction = "center"

        if faces == 1:
            # Gaze direction calculation (prioritize horizontal away glances over vertical)
            if gaze_v is not None and gaze_h is not None:
                if gaze_h < h_range[0]:
                    direction = "left"
                elif gaze_h > h_range[1]:
                    direction = "right"
                elif gaze_v > v_down:
                    direction = "down"
                elif gaze_v < v_up:
                    direction = "up"
                else:
                    direction = "center"
            else:
                direction = frame.get("gaze_direction", "center")

            # Head pose check
            if yaw is not None and pitch is not None:
                conditions["head_turned"] = abs(yaw) > yaw_thresh or pitch > pitch_thresh
                if conditions["head_turned"]:
                    turn_dir = "right" if yaw < 0 else "left"
                    tilt_dir = "down" if pitch > 0 else "up"
                    if abs(yaw) >= abs(pitch):
                        details["head_turned"] = f"turned {turn_dir} (yaw {yaw:.1f}\u00b0)"
                    else:
                        details["head_turned"] = f"tilted {tilt_dir} (pitch {pitch:.1f}\u00b0)"
            elif "head_turned" in frame.get("flags", ""):
                conditions["head_turned"] = True
                details["head_turned"] = "head turned"

            # Decouple gaze from head turn: do not double-penalize gaze when head is turned
            conditions["gaze_away"] = (direction not in ("center", "n/a", "")) and (not conditions["head_turned"])
            if conditions["gaze_away"]:
                details["gaze_away"] = f"looking {direction}"

        if conditions["multiple_faces"]:
            details["multiple_faces"] = f"{faces} faces in frame"
        if conditions["no_face"]:
            details["no_face"] = "no face detected"

        scorer.update(t, conditions, details=details)

        # Record updated frame entry for debug visualization
        f_copy = dict(frame)
        f_copy["gaze_direction"] = direction
        f_copy["flags"] = ",".join([k for k, v in conditions.items() if v]) or "-"
        rescored_debug_frames.append(f_copy)

    scorer.finalize(last_timestamp)
    score = scorer.compute_risk_score()
    norm_res = scorer.compute_normalized_score(session_duration_sec=last_timestamp)

    return {
        "risk_score": score,
        "risk_level": scorer.risk_level(score),
        "normalized_score": norm_res["normalized_score"],
        "normalized_risk_level": norm_res["normalized_risk_level"],
        "window_analysis": norm_res["window_analysis"],
        "events": scorer.events,
        "activity_log": scorer.activity_log,
        "frames_analysed": len(debug_frames),
        "video_duration_sec": round(last_timestamp, 2),
        "debug_frames": rescored_debug_frames,
    }

