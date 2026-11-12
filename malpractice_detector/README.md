# FairSight — AI-Based Malpractice Detection System

> **Evaluator-Assistance Proctoring Engine & Behavioral Integrity Platform**  
> FairSight turns recorded exam videos or live candidate feeds into timestamped, explainable behavioral telemetry for human evaluators. It flags observable evidence; it never declares guilt.

---

## 1. System Architecture

FairSight consists of three integrated layers:

1. **Python AI Detection Core & FastAPI Service** (`api.py`, `pipeline.py`, `modules/`):
   - OpenCV frame extraction at 4 fps (250 ms temporal resolution).
   - MediaPipe Tasks API FaceLandmarker (478 3D landmarks).
   - Cascade auxiliary detectors: BlazeFace (profile/edge faces), ObjectDetector (unauthorized persons/bodies), and HandLandmarker (intruder reaching hands) with duplicate suppression.
   - Head pose estimation via `solvePnP` (yaw, pitch, roll) with pitch wraparound correction and landmark symmetry confirmation.
   - Geometric iris-ratio gaze classification (center, left, right, up, down) with head-turn decoupling to prevent double-penalization.
   - 3-Layer explainable scoring engine (`RiskScorer`).

2. **Cross-Platform Client** (`exam_proctor_app/`):
   - Flutter application targeting **Android APK** and **Windows Desktop (.exe)**.
   - Real-time live proctoring HUD, video file audit with staged progress, scenario simulations, and verifiable audit certificates.

3. **Developer & Analytics Dashboard** (`app.py`):
   - Streamlit wide-layout dashboard for scenario inspection, telemetry visualization (Plotly), and threshold sensitivity tuning.

---

## 2. Three-Layer Scoring Engine

Every point in the 0–100 risk score traces to a named rule, calibrated threshold, and exact timestamp:

| Layer | Rule | Gate / Window | Weight |
|---|---|---|---|
| **Layer 1: Sustained Events** | Condition holds continuously ≥ duration gate | `head_turned`: 0.4 s<br>`gaze_away`: 0.7 s<br>`no_face`: 1.0 s | `head_turned`: 15<br>`gaze_away`: 12<br>`no_face`: 6 |
| **Layer 2: Frequency Patterns** | Repeated brief glances/turns too short for Layer 1 | ≥ 2 brief events within a rolling 10.0 s window | `frequent_gaze_away`: 18<br>`frequent_head_turned`: 18 |
| **Layer 3: Immediate Flags** | High-severity cues flagged on any occurrence | 0.0 s (immediate, single frame) | `multiple_faces`: 30 |

### Risk Bands
- **Low**: 0 – 24 (normal natural behavior)
- **Medium**: 25 – 59 (advisory for evaluator review)
- **High**: 60 – 100 (escalation threshold for human invigilator investigation)

All parameters are centrally governed by `scoring_config.py`.

---

## 3. Data Retention & Privacy Policy

- **No Raw Video Storage**: Uploaded video files sent to `/api/analyze-video` are processed in temporary storage and deleted immediately upon analysis completion.
- **Explainability**: Video frames themselves are not stored; only timestamped event logs, measured angles, and telemetry ratios are output in the audit report.
- **Human-in-the-Loop**: The risk score is an assistance index for human invigilators, not an autonomous verdict.

---

## 4. Quick Start

### Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Bundled MediaPipe model files in `models/` (already included)

### Installation
```bash
pip install -r requirements.txt
```

### Running the FastAPI Backend
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
API documentation is available at `http://localhost:8000/docs`.

### Running the Streamlit Dashboard (Developer Tool)
```bash
streamlit run app.py
```

### Command-Line Video Analysis
```bash
python pipeline.py path/to/video.mp4 --debug
```

### Running Automated Tests
```bash
python -m pytest tests/ -v
```
All unit tests, scenario simulations, time-normalisation checks, and the configuration baseline integrity suite are executed. Results are logged to `results/pytest_output.txt`.

> **Test Suite Status**: 32 passed, 1 skipped (0 failed).  
> **Environment Note on Skipped Test**: `tests/test_multi_person_detection.py::test_detector_initialization_and_keys` is skipped on Windows environments where **Smart App Control (SAC)** is active (`VerifiedAndReputablePolicyState: 1`). Windows SAC blocks loading unsigned native binaries (`libmediapipe.dll`) via `ctypes.CDLL()` (`[WinError 4551] An Application Control policy has blocked this file`). All multi-person bounding-box heuristics, auxiliary annotation rendering, and hand suppression tests run and pass cleanly.

---

## 5. Work Package Tracking & Roadmap

| Work Package | Focus Area | Status | Scope & Deliverables |
|---|---|:---:|---|
| **WP0** | Baseline & Hygiene | **COMPLETED** | Single configuration (`scoring_config.py`), fixed imports, cleaned root assets, baseline test guards (C-009). |
| **WP1** | Scoring Improvements & Time Normalisation | **COMPLETED** | 10-minute windowed capped model ($W=600\text{s}$, $\alpha=0.10$), multi-face gap integrity guard ($1.5\times$ tolerance), calibration of scenarios, 32 unit tests passing (C-010, C-011). |
| **WP4** | Buildable Cross-Platform App | **COMPLETED** | Full Android Gradle & Windows C++ runner scaffolding, rebranded to `org.fairsight.exam_proctor`, Material 3 theme modernized, CI release pipeline for APK & Windows ZIP (C-012). |
| **WP2** | Evaluation Package | **NEXT RECOMMENDED** | Dataset description, ground-truth labels CSV, `evaluate.py`, `ablation.py`, `benchmark.py`, Wilson 95% intervals, Cohen's kappa. |
| **WP3** | Backend Hardening | Queued | API-key authentication, configurable CORS, upload limits, automatic temp video file deletion, `/version` endpoint. |
| **WP5** | App UI & UX Redesign | Queued | Professional proctor HUD, dual risk score display, audit certificate viewer. |
| **WP6** | App Identity & Packaging | Queued | Branding, app icons, installer generation. |
| **WP7** | Technical Documentation | Queued | Updating specification, literature verification, removing overclaims. |
| **WP8** | Final Presentation | Queued | Defense slide deck aligned with actual code and evaluation benchmarks. |
| **WP9** | Viva Readiness Pack | Queued | 15 examiner Q&A answers with real numbers, demo scripts, fallback contingency plans. |

---

## 6. Directory Structure

```
malpractice_detector/
├── scoring_config.py          # Single source of truth for all parameters
├── api.py                     # FastAPI backend (10 endpoints)
├── app.py                     # Streamlit dashboard
├── pipeline.py                # End-to-end video pipeline
├── demo_data.py               # 5 benchmark scenario timelines
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container specification
├── docker-compose.yml         # Compose configuration
├── models/                    # MediaPipe & TFLite model tasks
├── modules/
│   ├── face_utils.py          # Face mesh & cascade detection
│   ├── eye_tracking.py        # Iris-ratio gaze direction
│   ├── head_pose.py           # solvePnP pose estimation
│   ├── scoring.py             # 3-layer RiskScorer & rescore engine
│   ├── report.py              # Audit report & certificate builders
│   └── visualizations.py      # Plotly visualizers
├── tests/
│   ├── test_config.py         # WP0 baseline integrity guard
│   ├── test_scoring.py        # Scoring layer tests
│   ├── test_scenarios.py      # Scenario simulation tests
│   └── test_multi_person_detection.py  # Cascade detector tests
├── docs/
│   └── images/                # Reference test frames
└── results/
    └── pytest_output.txt      # Verified test execution log
```
