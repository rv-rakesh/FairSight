"""
validate_flutter_project.py
===========================
Automated verification tool for FairSight WP4 + CI/CD (Buildable App).
Checks that all Android, Windows, Dart, and root-level CI/CD assets conform
to Flutter stable build requirements and repository standards.
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FLUTTER_ROOT = os.path.join(REPO_ROOT, "exam_proctor_app")


def check_file(base_dir, rel_path, required_strings=None):
    full_path = os.path.join(base_dir, rel_path)
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
    print("FAIRSIGHT: FLUTTER APP STRUCTURE, PLATFORM & CI/CD INTEGRITY AUDIT")
    print("=" * 70)
    print(f"Auditing Flutter root: {FLUTTER_ROOT}\n")

    checks = [
        # Android Platform Scaffolding
        (FLUTTER_ROOT, "android/build.gradle", ["allprojects", "layout.buildDirectory", "tasks.register(\"clean\""]),
        (FLUTTER_ROOT, "android/settings.gradle", ["pluginManagement", "dev.flutter.flutter-plugin-loader", "9.3.1", "2.4.20", "include \":app\""]),
        (FLUTTER_ROOT, "android/gradle.properties", ["org.gradle.vfs.watch=false", "android.useAndroidX=true", "android.newDsl=false", "android.builtInKotlin=false"]),
        (FLUTTER_ROOT, "android/gradle/wrapper/gradle-wrapper.properties", ["gradle-9.5.0-all.zip"]),
        (FLUTTER_ROOT, "android/app/build.gradle", ["namespace \"org.fairsight.exam_proctor\"", "compileSdk flutter.compileSdkVersion", "minSdkVersion flutter.minSdkVersion", "applicationId \"org.fairsight.exam_proctor\""]),
        (FLUTTER_ROOT, "android/app/src/main/AndroidManifest.xml", ["package=\"org.fairsight.exam_proctor\"", "android:label=\"FairSight\""]),
        (FLUTTER_ROOT, "android/app/src/main/kotlin/org/fairsight/exam_proctor/MainActivity.kt", ["package org.fairsight.exam_proctor", "class MainActivity"]),
        (FLUTTER_ROOT, "android/app/src/main/res/values/styles.xml", ["LaunchTheme", "NormalTheme"]),
        (FLUTTER_ROOT, "android/app/src/main/res/drawable/launch_background.xml", ["layer-list"]),
        (FLUTTER_ROOT, "android/app/src/main/res/mipmap-mdpi/ic_launcher.png", None),
        (FLUTTER_ROOT, "android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png", None),

        # Windows Platform Scaffolding
        (FLUTTER_ROOT, "windows/CMakeLists.txt", ["APPLY_STANDARD_SETTINGS", "FLUTTER_MANAGED_DIR", "set(BINARY_NAME \"FairSight\")", "INSTALL_BUNDLE_DATA_DIR"]),
        (FLUTTER_ROOT, "windows/flutter/CMakeLists.txt", ["generated_config.cmake", "flutter_wrapper_app", "flutter_assemble"]),
        (FLUTTER_ROOT, "windows/runner/CMakeLists.txt", ["apply_standard_settings(${BINARY_NAME})", "generated_plugin_registrant.cc", "runner.exe.manifest"]),
        (FLUTTER_ROOT, "windows/runner/main.cpp", ["wWinMain", "FairSight - AI-Based Behavioral Integrity Platform"]),
        (FLUTTER_ROOT, "windows/runner/flutter_window.h", ["class FlutterWindow : public Win32Window"]),
        (FLUTTER_ROOT, "windows/runner/flutter_window.cpp", ["generated_plugin_registrant.h", "RegisterPlugins", "SetChildContent", "SetNextFrameCallback"]),
        (FLUTTER_ROOT, "windows/runner/win32_window.h", ["class Win32Window", "SetChildContent", "bool Show()"]),
        (FLUTTER_ROOT, "windows/runner/win32_window.cpp", ["WindowClassRegistrar", "SetChildContent", "UpdateTheme"]),
        (FLUTTER_ROOT, "windows/runner/utils.h", ["CreateAndAttachConsole", "GetCommandLineArguments"]),
        (FLUTTER_ROOT, "windows/runner/utils.cpp", ["CreateAndAttachConsole", "Utf8FromUtf16"]),
        (FLUTTER_ROOT, "windows/runner/resource.h", ["IDI_APP_ICON"]),
        (FLUTTER_ROOT, "windows/runner/Runner.rc", ["FairSight.exe", "FairSight Organization", "app_icon.ico"]),
        (FLUTTER_ROOT, "windows/runner/resources/app_icon.ico", None),
        (FLUTTER_ROOT, "windows/runner/runner.exe.manifest", ["PerMonitorV2"]),

        # Dart Application Logic, Theme & Tests
        (FLUTTER_ROOT, "pubspec.yaml", ["name: exam_proctor_app", "material_ui:", "flutter:", "sdk: flutter"]),
        (FLUTTER_ROOT, "lib/main.dart", ["package:material_ui/material_ui.dart", "title: 'FairSight'", "CardThemeData(", "fontFamilyFallback", "useMaterial3: true"]),
        (FLUTTER_ROOT, "lib/models/telemetry_model.dart", ["class TelemetryResult", "class ExamAuditReport", "normalizedScore", "normalizedRiskLevel"]),
        (FLUTTER_ROOT, "lib/services/api_service.dart", ["class ApiService", "defaultLocalhost", "defaultEmulator"]),
        (FLUTTER_ROOT, "test/telemetry_model_test.dart", ["Telemetry Model Unit Tests", "ExamAuditReport parses dual score"]),
        (FLUTTER_ROOT, "test/widget_test.dart", ["ExamProctorApp", "Exam Proctor AI"]),

        # Root-Level Repository Hygiene & CI/CD Workflow
        (REPO_ROOT, ".gitignore", ["__pycache__/", "**/windows/flutter/ephemeral/"]),
        (REPO_ROOT, ".github/workflows/build_apps.yml", ["libegl1", "libgles2", "java-version: '21'", "flutter config --jdk-dir", "flutter-version: '3.50.0'", "flutter analyze", "flutter test", "flutter build apk --release", "flutter build windows --release", "FairSight-Android-APK", "FairSight-Windows-Desktop"]),
    ]

    passed = 0
    failed = 0

    for base_dir, path, req_strings in checks:
        ok, msg = check_file(base_dir, path, req_strings)
        if ok:
            print(f"  [PASS] {path}")
            passed += 1
        else:
            print(f"  [FAIL] {msg}")
            failed += 1

    # Ensure duplicate nested workflow does NOT exist
    nested_wf = os.path.join(FLUTTER_ROOT, ".github", "workflows", "build_apps.yml")
    if os.path.exists(nested_wf):
        print(f"  [FAIL] Duplicate nested workflow still exists: exam_proctor_app/.github/workflows/build_apps.yml")
        failed += 1
    else:
        print("  [PASS] No duplicate nested workflow in exam_proctor_app/.github")
        passed += 1

    # Verify runner.exe.manifest is NOT blocked by .gitignore
    with open(os.path.join(REPO_ROOT, ".gitignore"), "r", encoding="utf-8") as f:
        gi_lines = [line.strip() for line in f.read().splitlines()]
    if "*.manifest" in gi_lines:
        print("  [FAIL] .gitignore still blocks *.manifest (breaks runner.exe.manifest tracking)")
        failed += 1
    else:
        print("  [PASS] .gitignore allows runner.exe.manifest tracking")
        passed += 1

    print("\n" + "-" * 70)
    print(f"Audit Summary: {passed} PASSED, {failed} FAILED.")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
