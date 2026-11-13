# FairSight — Cross-Platform Flutter Client (`exam_proctor_app/`)

Unified Flutter client compiling into:
- **Windows Desktop Application (`FairSight.exe`)**
- **Android Mobile Application (`app-release.apk`, package `org.fairsight.exam_proctor`)**

---

## 1. Architecture & Backend Connectivity

The Flutter client (`lib/services/api_service.dart`) communicates over HTTP with the Python FastAPI backend (`malpractice_detector/api.py`) listening on port `8000`:

| Target Environment | Recommended Backend URL | How to Configure |
|---|---|---|
| **Windows Desktop EXE** | `http://127.0.0.1:8000` *(default)* | Start backend locally via `malpractice_detector\start_backend.bat` or `python -m uvicorn api:app --host 0.0.0.0 --port 8000`. |
| **Android Emulator** | `http://10.0.2.2:8000` | Tap the top-right Settings icon (`tune`) on Home Screen -> enter `http://10.0.2.2:8000`. |
| **Physical Android Phone** | `http://<PC-LAN-IP>:8000` | Find PC IPv4 with `ipconfig` (e.g. `http://192.168.1.25:8000`), enter in Server Settings, and allow TCP Port `8000` in Windows Firewall. |

---

## 2. Key Screens & Implemented Features

1. **Home Dashboard (`lib/screens/home_screen.dart`)**:
   - Live backend connection status indicator (`GET /health`) + manual `Refresh` and `Engine Connection` URL editor.
   - Mode selection cards: Upload Examination Video, Live Camera Proctoring Studio, and Academic Scenarios Benchmark.
2. **Recorded Video File Audit (`lib/screens/video_audit_screen.dart`)**:
   - Pick from Gallery, Files (`FilePicker`), or Mobile Camera (`ImagePicker`).
   - Streams multipart upload to `POST /api/analyze-video` and surfaces descriptive backend error messages (e.g. empty file, unsupported extension, corrupt video) via floating `SnackBar`.
3. **Live Camera Proctoring Studio (`lib/screens/live_proctor_screen.dart`)**:
   - Creates a stateful backend session (`POST /api/session/start`), streams periodic frames (`POST /api/session/{id}/frame`), renders real-time Risk Score, Gaze direction, Head Pose yaw, person count, and active warning banners.
   - Shows explicit connection/camera error recovery UI if backend or camera is unavailable.
4. **Integrity Audit Certificate (`lib/screens/report_screen.dart`)**:
   - Displays both **Raw Risk Score (0–100)** and **10-Min Normalized Score**, risk band pill, duration, violation count, analyzed frames / flagged moments, and timestamped event timeline.

---

## 3. Running & Building Locally

Prerequisites: Flutter SDK `3.50.0` (Dart `>=3.13.0 <4.0.0`), Android SDK / Java `21` (for Android APK), or Visual Studio C++ Desktop Workload (for Windows EXE).

```bash
cd exam_proctor_app
flutter pub get
flutter analyze
flutter test
flutter build apk --release
flutter build windows --release
```

Build outputs:
- **Android APK:** `build/app/outputs/flutter-apk/app-release.apk`
- **Windows Bundle:** `build/windows/x64/runner/Release/FairSight.exe` (and adjacent `.dll` / `data/` folder)

---

## 4. Automated GitHub Actions Builds

Pushes to `main` automatically run `.github/workflows/build_apps.yml` and upload:
- **`FairSight-Android-APK`** (`app-release.apk`)
- **`FairSight-Windows-Desktop`** (zipped Windows release directory containing `FairSight.exe`)
