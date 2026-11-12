# FairSight — AI-Based Malpractice Detection & Behavioral Integrity Platform

FairSight turns recorded exam videos or live candidate feeds into timestamped, explainable behavioral telemetry for human evaluators. It flags observable evidence using a transparent, time-normalized 3-layer scoring engine (`malpractice_detector/scoring_config.py`).

---

## Repository Structure

```text
FairSight/
├── .github/
│   └── workflows/
│       └── build_apps.yml      # Root GitHub Actions CI/CD workflow (Backend tests, Android APK & Windows EXE)
├── .gitignore                  # Python, Flutter, Android, Windows, secrets & media ignore rules
├── CHANGELOG.md                # Full audit trail (WP0, WP1, WP4)
├── exam_proctor_app/           # Flutter cross-platform client (Android & Windows Desktop)
└── malpractice_detector/       # Python AI detection core, FastAPI backend, Streamlit dashboard & tests
```

---

## Work Packages Included

- **WP0 (Baseline & Hygiene):** Single-source configuration (`malpractice_detector/scoring_config.py`), cleaned root assets, fixed Docker/Compose entrypoints, and `tests/test_config.py`.
- **WP1 (Scoring Improvements & Time Normalisation):** 10-minute windowed per-type capped severity model ($W=600\text{s}$, $\alpha=0.10$), timestamp-gap-guarded `multiple_faces` consecutive frame check, persistence factor calibration (`scripts/evaluate_persistence_alpha.py`), and `tests/test_time_normalisation.py`.
- **WP4 (Buildable Cross-Platform App & CI/CD):** Complete Android Gradle (`org.fairsight.exam_proctor`) and Windows Win32 C++ runner (`FairSight.exe`) scaffolding, modernized Material 3 UI (`CardThemeData`), Flutter unit & widget tests, project validator (`scripts/validate_flutter_project.py`), and root GitHub Actions build pipeline.

---

## Quick Start

### 1. Backend & Tests (`malpractice_detector/`)
```bash
cd malpractice_detector
pip install -r requirements.txt
python -B -m pytest tests/ -v -p no:cacheprovider
python -B scripts/validate_flutter_project.py
uvicorn api:app --host 0.0.0.0 --port 8000
```

> **Note on Client-Backend Architecture:** The Android APK and Windows EXE communicate with the FastAPI backend (`malpractice_detector/api.py`) over HTTP (`http://127.0.0.1:8000` on local PC, `http://10.0.2.2:8000` on Android emulator, or `http://<PC-LAN-IP>:8000` over Wi-Fi). Start `uvicorn api:app --host 0.0.0.0 --port 8000` before running live proctoring or video audit sessions.

### 2. Cross-Platform App (`exam_proctor_app/`)
Push to `main` on GitHub and open the **Actions** tab to download **FairSight-Android-APK** and **FairSight-Windows-Desktop**, or build locally with Flutter SDK:
```bash
cd exam_proctor_app
flutter pub get
flutter analyze
flutter test
flutter build apk --release
flutter build windows --release
```

See [malpractice_detector/README.md](malpractice_detector/README.md) and [exam_proctor_app/README.md](exam_proctor_app/README.md) for detailed component instructions.
