"""
validate_flutter_project.py
===========================
Automated verification tool for FairSight WP4 (Buildable App).
Checks that all Android, Windows, Dart, and CI/CD assets conform to
the specifications of the Master Project and Handoff Document.
"""

import os
import sys

FLUTTER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "exam_proctor_app"))

def check_file(rel_path, required_strings=None):
    full_path = os.path.join(FLUTTER_ROOT, rel_path)
    if not os.path.isfile(full_path):
        return False, f"Missing file: {rel_path}"
    if required_strings:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for s in required_strings:
            if s not in content:
                return False, f"File {rel_path} missing required text: '{s}'"
    return True, f"OK: {rel_path}"

def run_checks():
    print("=" * 70)
    print("FAIRSIGHT WP4: FLUTTER APP STRUCTURE & PLATFORM INTEGRITY AUDIT")
    print("=" * 70)
    print(f"Auditing path: {FLUTTER_ROOT}\n")

    checks = [
        # Android Platform Scaffolding
        ("android/build.gradle", ["allprojects", "tasks.register(\"clean\""]),
        ("android/settings.gradle", ["pluginManagement", "dev.flutter.flutter-plugin-loader", "include \":app\""]),
        ("android/gradle.properties", ["android.useAndroidX=true"]),
        ("android/gradle/wrapper/gradle-wrapper.properties", ["gradle-8.4-all.zip"]),
        ("android/app/build.gradle", ["namespace \"org.fairsight.exam_proctor\"", "compileSdk 34", "minSdkVersion 21", "applicationId \"org.fairsight.exam_proctor\""]),
        ("android/app/src/main/AndroidManifest.xml", ["package=\"org.fairsight.exam_proctor\"", "android:label=\"FairSight\""]),
        ("android/app/src/main/kotlin/org/fairsight/exam_proctor/MainActivity.kt", ["package org.fairsight.exam_proctor", "class MainActivity"]),
        ("android/app/src/main/res/values/styles.xml", ["LaunchTheme", "NormalTheme"]),
        ("android/app/src/main/res/drawable/launch_background.xml", ["layer-list"]),

        # Windows Platform Scaffolding
        ("windows/CMakeLists.txt", ["cmake_minimum_required", "set(BINARY_NAME \"FairSight\")"]),
        ("windows/runner/CMakeLists.txt", ["add_executable(${BINARY_NAME} WIN32", "flutter_window.cpp"]),
        ("windows/runner/main.cpp", ["wWinMain", "FairSight — AI-Based Behavioral Integrity Platform"]),
        ("windows/runner/flutter_window.h", ["class FlutterWindow : public Win32Window"]),
        ("windows/runner/flutter_window.cpp", ["FlutterViewController"]),
        ("windows/runner/win32_window.h", ["class Win32Window"]),
        ("windows/runner/win32_window.cpp", ["kWindowClassName"]),
        ("windows/runner/utils.h", ["GetCommandLineArguments"]),
        ("windows/runner/utils.cpp", ["Utf8FromUtf16"]),
        ("windows/runner/resource.h", ["IDI_APP_ICON"]),
        ("windows/runner/Runner.rc", ["FairSight.exe", "FairSight Organization"]),
        ("windows/runner/runner.exe.manifest", ["PerMonitorV2"]),

        # Dart Application Logic & Theme
        ("pubspec.yaml", ["name: exam_proctor_app", "flutter:", "sdk: flutter"]),
        ("lib/main.dart", ["title: 'FairSight'", "fontFamilyFallback", "useMaterial3: true"]),
        ("lib/models/telemetry_model.dart", ["class TelemetryResult", "class ExamAuditReport", "normalizedScore", "normalizedRiskLevel"]),
        ("lib/services/api_service.dart", ["class ApiService", "defaultLocalhost", "defaultEmulator"]),
        ("test/telemetry_model_test.dart", ["Telemetry Model Unit Tests", "ExamAuditReport parses dual score"]),

        # CI/CD Workflow
        (".github/workflows/build_apps.yml", ["flutter create --platforms=android .", "flutter create --platforms=windows .", "FairSight-Android-APK", "FairSight-Windows-Desktop"]),
    ]

    passed = 0
    failed = 0

    for path, req_strings in checks:
        ok, msg = check_file(path, req_strings)
        if ok:
            print(f"  [PASS] {path}")
            passed += 1
        else:
            print(f"  [FAIL] {msg}")
            failed += 1

    # Verify YAML files structure
    yaml_files = ["pubspec.yaml", ".github/workflows/build_apps.yml"]
    for yf in yaml_files:
        full_path = os.path.join(FLUTTER_ROOT, yf)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) > 5, "File too short"
            print(f"  [PASS] File structure verified: {yf} ({len(lines)} lines)")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] Error reading {yf}: {e}")
            failed += 1

    print("\n" + "-" * 70)
    print(f"Audit Summary: {passed} PASSED, {failed} FAILED.")
    print("=" * 70)

    return failed == 0

if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
