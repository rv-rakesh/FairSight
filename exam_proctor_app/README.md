# Exam Proctor AI - Cross-Platform Client (Windows & Mobile)

This is the unified Flutter application for the **AI-Based Malpractice Detection System**. It provides a single codebase that compiles into:
- **Windows Desktop Application (`.exe`)**
- **Android Mobile Application (`.apk`)**

---

## 🏗️ Architecture Overview

The app connects to the high-performance Python FastAPI backend (`api.py`) running on `http://127.0.0.1:8000` (or your PC's Wi-Fi IP when testing on mobile).

### Key Features:
1. **Live Camera Proctoring Studio:**
   - Real-time front camera stream (webcam on PC, selfie camera on mobile).
   - In-app HUD overlay displaying:
     - Real-time 0–100 Risk Score.
     - Risk Level Badge (Low, Medium, High).
     - Head Pose Pitch & Yaw angles in degrees.
     - Eye Gaze Direction (Center, Left, Right, Down, Up).
     - Live multi-person and intruder hand warning banners.
2. **Recorded Video File Audit:**
   - Upload any `.mp4`, `.webm`, or `.mov` exam recording.
   - Generates a full forensic audit report.
3. **Forensic Audit Certificate:**
   - Color-coded circular risk gauge.
   - Second-by-second event timeline.
   - List of confirmed infractions with justification notes.

---

## 🚀 How to Run & Build Locally

### Prerequisites:
- Install the [Flutter SDK](https://docs.flutter.dev/get-started/install).

### 1. Run in Development Mode:
```bash
# Get dependencies
flutter pub get

# Run on Windows Desktop
flutter run -d windows

# Run on Android Phone (USB debugging enabled)
flutter run -d android
```

### 2. Build Release Windows App (.exe):
```bash
flutter build windows --release
```
The compiled output will be in `build/windows/x64/runner/Release/`.

### 3. Build Release Android App (.apk):
```bash
flutter build apk --release
```
The compiled `.apk` will be in `build/app/outputs/flutter-apk/app-release.apk`. Transfer this file to any Android phone to install!

---

## ☁️ Automated Cloud Build (Zero Installation Required)

If you don't want to download large 10GB Android Studio / Visual Studio C++ toolchains on your PC, this repository includes an automated **GitHub Actions Workflow** (`.github/workflows/build_apps.yml`):

1. Push this project to your GitHub repository.
2. Go to the **Actions** tab on GitHub.
3. GitHub's free cloud servers will automatically compile both:
   - **`ExamProctor-Android-APK`** (`app-release.apk`)
   - **`ExamProctor-Windows-Desktop`** (`.exe` bundle)
4. Download the ready-to-use apps directly to your phone and laptop!
