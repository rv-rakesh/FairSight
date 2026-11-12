# FairSight — AI-Based Malpractice Detection & Behavioral Integrity Platform

FairSight turns recorded exam videos or live candidate feeds into timestamped, explainable behavioral telemetry for human evaluators. It flags observable evidence using a transparent, time-normalized 3-layer scoring engine (`scoring_config.py`).

---

## Repository Structure

```text
fairsight_src/
├── .github/
│   └── workflows/
│       └── build_apps.yml      # Root GitHub Actions CI/CD workflow (Android APK & Windows EXE)
├── .gitignore                  # Python, Flutter, Android, Windows, secrets & media ignore rules
├── CHANGELOG.md                # Full audit trail (WP0, WP1, WP4)
├── exam_proctor_app/           # Flutter cross-platform client (Android & Windows Desktop)
└── malpractice_detector/       # Python AI detection core, FastAPI backend, Streamlit dashboard & tests
```

---

## Work Packages Included

- **WP0 (Baseline & Hygiene):** Single-source configuration (`malpractice_detector/scoring_config.py`), cleaned root assets, fixed Docker/Compose entrypoints, and `tests/test_config.py`.
- **WP1 (Scoring Improvements & Time Normalisation):** 10-minute windowed per-type capped severity model ($W=600\text{s}$, $\alpha=0.10$), timestamp-gap-guarded `multiple_faces` consecutive frame check, persistence factor calibration (`scripts/evaluate_persistence_alpha.py`), and `tests/test_time_normalisation.py`.
- **WP4 (Buildable Cross-Platform App):** Complete Android Gradle (`org.fairsight.exam_proctor`) and Windows Win32 C++ runner (`FairSight.exe`) scaffolding, modernized Material 3 UI, Dart unit tests (`exam_proctor_app/test/telemetry_model_test.dart`), project validator (`scripts/validate_flutter_project.py`), and GitHub Actions release pipeline.

---

## Quick Start

### 1. Backend & Tests (`malpractice_detector/`)
```bash
cd malpractice_detector
pip install -r requirements.txt
python -m pytest tests/ -v
python scripts/validate_flutter_project.py
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 2. Cross-Platform App (`exam_proctor_app/`)
Push this repository root (`fairsight_src/`) to your GitHub account and open the **Actions** tab to trigger **Build FairSight Cross-Platform Apps (Windows EXE & Android APK)**, or build locally with Flutter SDK:
```bash
cd exam_proctor_app
flutter pub get
flutter test
flutter build apk --release
flutter build windows --release
```

See [malpractice_detector/README.md](malpractice_detector/README.md) and [exam_proctor_app/README.md](exam_proctor_app/README.md) for detailed component instructions.
