# FairSight Backend — AI Malpractice Detection Engine (`malpractice_detector/`)

> **Evaluator-Assistance Proctoring Engine & FastAPI Backend**  
> FairSight converts recorded exam videos or live candidate camera frames into timestamped, explainable behavioral telemetry (`0–100` raw and time-normalized risk scores) for human invigilators. It flags observable behavioral cues; it never renders an automated disciplinary verdict.

---

## 1. System Architecture & Technology Stack

1. **Computer Vision & AI Pipeline (`pipeline.py`, `modules/face_utils.py`)**:
   - **OpenCV** video decoding & 4 FPS temporal sampling (`250 ms` resolution).
   - **MediaPipe FaceLandmarker (478 landmarks)** for primary candidate facial geometry & iris tracking.
   - **Multi-Stage Auxiliary Cascade** (`BlazeFace`, `EfficientDet-Lite0` person detector, and `HandLandmarker`) with IoU deduplication and candidate workspace filtering to detect secondary people and reaching limbs without flagging the candidate's own hands.
   - **Head Pose (`modules/head_pose.py`)**: OpenCV `solvePnP` (`SOLVEPNP_SQPNP` with `ITERATIVE` fallback), Euler pitch unwrap, and 2D nasal-ocular symmetry guard (`YAW_THRESHOLD=26.0°`, `PITCH_DOWN_THRESHOLD=26.0°`, `PITCH_UP_THRESHOLD=20.0°`).
   - **Eye Gaze (`modules/eye_tracking.py`)**: Normalized horizontal & vertical iris-ratio tracking (`HORIZONTAL_CENTER_RANGE=(0.35, 0.65)`, `VERTICAL_DOWN_THRESHOLD=0.65`, `VERTICAL_UP_THRESHOLD=0.22`), decoupled from head turns so a single head turn is never double-counted.
2. **3-Layer Time-Normalized Scoring Engine (`modules/scoring.py`, `scoring_config.py`)**:
   - **Layer 1 (Sustained Events):** `head_turned` >= `0.4s` (+15), `gaze_away` >= `0.7s` (+12), `no_face` >= `1.0s` (+6).
   - **Layer 2 (Frequency Patterns):** >= `2` brief occurrences within a rolling `10.0s` window (`frequent_gaze_away`: +18, `frequent_head_turned`: +18).
   - **Layer 3 (Immediate Flags):** `multiple_faces` flagged immediately (+30; optional gap-guarded consecutive-frame confirmation via `REQUIRE_CONSECUTIVE_FRAMES_MULTI_FACE`).
   - **Time Normalization:** 10-minute windows (`W=600s`), per-type caps (`WINDOW_PER_TYPE_CAPS`), and cross-window persistence `alpha=0.10` prevent long 3-hour honest sessions from drifting into false High risk.
3. **FastAPI REST Backend (`api.py`) & Report Engine (`modules/report.py`)**:
   - Exposes 10 REST endpoints powering Windows Desktop (`FairSight.exe`), Android (`FairSight` APK), and external integrations.
   - Generates `.txt`, `.csv`, and XSS-sanitized printable HTML/PDF audit certificates displaying both Raw and 10-Min Normalized scores.

---

## 2. API Endpoints (`api.py`)

| Method | Route | Description |
|---|---|---|
| `GET` | `/health` | Service health check, model asset presence, active session count |
| `GET` | `/api/scenarios` | Lists pre-calibrated benchmark scenarios (`honest_candidate`, `screen_peeking`, etc.) |
| `POST` | `/api/scenarios/{scenario_key}/run` | Runs a scenario timeline through `RiskScorer` (`404` if invalid key) |
| `POST` | `/api/detect-frame` | Stateless telemetry on a base64-encoded image (`400` invalid image, `422` bad timestamp) |
| `POST` | `/api/session/start` | Starts a stateful live proctoring session and returns `session_id` |
| `POST` | `/api/session/{session_id}/frame` | Scores a live session frame at `timestamp_sec` (`404` unknown session, `422` negative time) |
| `POST` | `/api/session/{session_id}/finalize` | Finalizes active session, closes open cues, returns full dual-score report (`404` if closed) |
| `POST` | `/api/analyze-video` | Analyses uploaded `.mp4`/`.avi`/`.mov`/`.mkv`/`.webm` at 4 FPS (`400` empty/corrupt/unsupported, `413` >250 MB) |
| `POST` | `/api/rescore` | Re-scores stored `debug_frames` in-memory with custom thresholds |
| `POST` | `/api/report/html` | Renders an HTML-escaped printable Audit Certificate (compatible with both video and live session outputs) |

---

## 3. Running & Testing Locally (Windows / Linux)

### Install Dependencies (Isolated venv Recommended on Anaconda Hosts)
```powershell
cd malpractice_detector
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Start FastAPI Server
```powershell
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```
Or double-click `start_backend.bat` on Windows to launch Uvicorn and print candidate LAN IPv4 addresses for mobile testing.
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### CLI Video Analysis & Developer Streamlit UI
```powershell
python pipeline.py path/to/video.mp4 --debug
streamlit run app.py
```

### Automated Test & Benchmark Commands
```powershell
python -B -m pytest tests/ -v -p no:cacheprovider
python -B scripts/validate_flutter_project.py
python -B scripts/run_wp2_evaluation.py
```

---

## 4. Troubleshooting

- **`numpy` / `opencv` / `contourpy` binary warning in global Anaconda**: Use a clean `venv` (`python -m venv venv`) with `numpy==1.26.4` (or compatible compiled wheels) without downgrading global Anaconda packages.
- **Physical Android phone cannot reach `http://<PC-IP>:8000`**:
  1. Ensure `uvicorn` was launched with `--host 0.0.0.0` (not `127.0.0.1`).
  2. Allow inbound TCP Port `8000` in Windows Defender Firewall (`Private` profile).
  3. Confirm phone and PC are on the same Wi-Fi subnet without AP client isolation.
- **`[WinError 4551]` Smart App Control on `libmediapipe.dll`**: Some hardened Windows machines block unsigned native wheels; run pytest inside CI Linux or disable Smart App Control if evaluating MediaPipe locally.

---

## 5. Privacy & Data Retention

- Uploaded videos in `/api/analyze-video` are written to a temporary file only during inference and deleted immediately in a `finally` block.
- Outputs contain timestamped telemetry (`yaw`, `pitch`, gaze ratios, event logs) rather than storing raw candidate video recordings.
