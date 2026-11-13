# FairSight — AI-Based Malpractice Detection & Behavioral Integrity Platform

FairSight turns recorded exam videos or live candidate feeds into timestamped, explainable behavioral telemetry for human evaluators. It flags observable evidence using a transparent, time-normalized 3-layer scoring engine (`malpractice_detector/scoring_config.py`).

---

## Repository Structure

```text
FairSight/
├── .github/
│   └── workflows/
│       └── build_apps.yml                  # Root GitHub Actions CI/CD workflow (Backend tests, Android APK & Windows EXE)
├── .gitignore                              # Python, Flutter, Android, Windows, secrets & media ignore rules
├── CHANGELOG.md                            # Complete chronological audit trail (C-001 to C-016)
├── docs/
│   └── ARCHITECTURE_AND_DIAGRAMS.md        # System architecture, DFD, API sequence, ML pipeline & PPT notes
├── exam_proctor_app/                       # Flutter cross-platform client (Android APK & Windows Desktop EXE)
└── malpractice_detector/                   # Python AI detection core, FastAPI backend, Streamlit dashboard & tests
    ├── api.py                              # FastAPI REST service (10 endpoints)
    ├── pipeline.py                         # 4 FPS OpenCV + MediaPipe video processing pipeline
    ├── scoring_config.py                   # Single source of truth for thresholds, weights & windows
    ├── modules/                            # face_utils, head_pose, eye_tracking, scoring, report, visualizations
    ├── models/                             # Bundled MediaPipe / TFLite model files
    ├── scripts/                            # run_wp2_evaluation.py, validate_flutter_project.py, evaluate_persistence_alpha.py
    ├── tests/                              # Unit, scenario, multi-person, time-norm & API edge-case tests
    ├── results/                            # Reproducible pytest & WP2 evaluation reports
    └── start_backend.bat                   # Windows one-click backend launcher + LAN IP helper
```

---

## System Requirements

- **Backend:** Python `3.10+` (verified on Python `3.11.9`), OpenCV, MediaPipe Tasks API, FastAPI, Uvicorn, Pydantic, Pandas, Streamlit, Plotly, Pytest.
- **Mobile & Desktop Builds (CI or Local):** Flutter SDK `3.50.0`, Java `21` + Android SDK / Gradle `9.5.0` (Android APK), Visual Studio C++ Desktop Workload (Windows EXE).

---

## Quick Start (Windows & Cross-Platform)

### 1. Start the FastAPI Backend (`malpractice_detector/`)

On Windows, either double-click `malpractice_detector\start_backend.bat` or run:
```powershell
cd malpractice_detector
python -m pip install -r requirements.txt
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

- **Swagger API Docs:** `http://127.0.0.1:8000/docs`
- **Health Endpoint:** `http://127.0.0.1:8000/health`

> **Environment Tip (NumPy / OpenCV):** If your global Python/Anaconda environment reports NumPy `1.26.4` vs OpenCV/ContourPy version warnings, create an isolated project virtual environment (`python -m venv venv`) rather than modifying your global base environment.

### 2. Run Tests & Reproducible Evaluation

```powershell
cd malpractice_detector
python -B -m pytest tests/ -v -p no:cacheprovider
python -B scripts/validate_flutter_project.py
python -B scripts/run_wp2_evaluation.py
```

### 3. Connect Windows Desktop (`FairSight.exe`) or Android APK (`app-release.apk`)

| Client Target | Backend URL Setting | Network Notes |
|---|---|---|
| **Windows Desktop EXE** | `http://127.0.0.1:8000` (default) | Start backend first with `start_backend.bat` or `uvicorn api:app --host 0.0.0.0 --port 8000`. |
| **Android Emulator** | `http://10.0.2.2:8000` | Change URL via the top-right Settings (`tune`) icon in `FairSight`. |
| **Physical Android Phone (Wi-Fi)** | `http://<PC-LAN-IP>:8000` | Run `ipconfig` on PC, connect both devices to the same Wi-Fi, and allow inbound TCP port `8000` in Windows Defender Firewall. |

> **Why Backend Does Not Auto-Spawn Inside `FairSight.exe`:** The CI-built Windows release ZIP (`FairSight-Windows-Desktop`) packages only the Flutter desktop binary and runtime DLLs (~12 MB) without bundling a Python interpreter or ~19 MB MediaPipe models. Keeping the backend as an independent FastAPI server allows both local desktop use (`127.0.0.1:8000`) and shared LAN mobile proctoring (`<PC-LAN-IP>:8000`).

### 4. GitHub Actions CI/CD Artifacts

Pushes to `main` trigger `.github/workflows/build_apps.yml`, building and publishing:
- **`FairSight-Android-APK`** (`app-release.apk`)
- **`FairSight-Windows-Desktop`** (zipped Windows release directory containing `FairSight.exe`)

---

## Known Limitations

1. **Rule-Based Policy Weights:** Risk points (`30` multiple faces, `15` head turned, `12` gaze away, `6` absent) are policy-calibrated severity weights (`scoring_config.py`), not calibrated probabilities.
2. **Dataset Scope:** Repository evaluation uses simulated scenarios (`demo_data.py`) and local reference frames (`docs/images/`); external multi-subject field exam datasets are not bundled.
3. **Environmental Sensitivity:** Extreme backlight, severe motion blur, or very low illumination can reduce MediaPipe landmark confidence.
4. **In-Memory Session Store:** Active live sessions in `api.py` (`_active_sessions`) are stored in memory and reset if the backend restarts.

See [docs/ARCHITECTURE_AND_DIAGRAMS.md](docs/ARCHITECTURE_AND_DIAGRAMS.md), [malpractice_detector/README.md](malpractice_detector/README.md), and [exam_proctor_app/README.md](exam_proctor_app/README.md) for full details.
