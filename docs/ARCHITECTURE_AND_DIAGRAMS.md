# FairSight — Architecture, System Diagrams & Presentation Reference

> Every component, endpoint, threshold, and file path below reflects the verified implementation in `fairsight_src/`.

---

## 1. Overall System Architecture

```mermaid
flowchart TB
    subgraph Clients["Client Applications (exam_proctor_app/)"]
        WIN["Windows Desktop App<br/>(FairSight.exe — Flutter Win32)"]
        AND["Android Mobile App<br/>(org.fairsight.exam_proctor — APK)"]
        DEV["Streamlit Analytics UI<br/>(malpractice_detector/app.py)"]
    end

    subgraph Backend["FastAPI Service (malpractice_detector/api.py :8000)"]
        ROUTES["10 REST Endpoints<br/>/health, /api/scenarios, /api/detect-frame,<br/>/api/session/*, /api/analyze-video,<br/>/api/rescore, /api/report/html"]
        SESS["In-Memory Session Store<br/>(_active_sessions)"]
        PIPE["Video Pipeline (pipeline.py)<br/>4 FPS sampling + cleanup"]
    end

    subgraph AI["AI / Computer Vision Core (modules/)"]
        CASCADE["FaceMeshDetector (face_utils.py)<br/>FaceLandmarker 478pts + BlazeFace +<br/>EfficientDet-Lite0 + HandLandmarker"]
        POSE["Head Pose (head_pose.py)<br/>solvePnP SQPNP + 2D symmetry"]
        GAZE["Eye Gaze (eye_tracking.py)<br/>Iris-corner & eyelid ratios"]
        SCORER["3-Layer RiskScorer (scoring.py)<br/>Raw (0-100) & 10-Min Normalized Score"]
        REPORT["Report Builder (report.py)<br/>TXT, CSV, Printable HTML"]
    end

    WIN -->|HTTP REST :8000| ROUTES
    AND -->|HTTP REST over LAN / 10.0.2.2:8000| ROUTES
    DEV -->|Direct Python Calls| PIPE
    DEV -->|Direct Python Calls| SCORER
    ROUTES --> SESS
    ROUTES --> PIPE
    SESS --> CASCADE
    SESS --> SCORER
    PIPE --> CASCADE
    CASCADE --> POSE
    CASCADE --> GAZE
    POSE --> SCORER
    GAZE --> SCORER
    SCORER --> REPORT
```

---

## 2. Data Flow Diagram (DFD)

```mermaid
flowchart LR
    U["Invigilator / Candidate"] -->|"Video (.mp4/.avi/.mov/.mkv/.webm)<br/>or Live Base64 Camera Frame"| API["FastAPI Ingress<br/>(api.py validation)"]
    API -->|"Valid Decoded BGR Frame(s)"| CV["OpenCV Frame Sampler<br/>(4 FPS / 250 ms step)"]
    CV -->|"RGB Image + Timestamp"| MP["MediaPipe Cascade<br/>(face_utils.py)"]
    MP -->|"478 Landmarks (if face_count == 1)"| GEOM["head_pose.py + eye_tracking.py<br/>(yaw, pitch, roll, gaze_h, gaze_v)"]
    MP -->|"face_count == 0 or > 1"| COND["Condition Evaluator<br/>no_face | multiple_faces"]
    GEOM -->|"Thresholds from scoring_config.py"| COND
    COND -->|"Per-frame conditions + details"| RS["RiskScorer<br/>(scoring.py)"]
    RS -->|"Events + Activity Log +<br/>Raw & 10m Normalized Score"| JSONOUT["JSON Audit Response /<br/>Printable HTML Certificate"]
    JSONOUT --> U
```

---

## 3. Detection & 3-Layer Scoring Workflow

```mermaid
flowchart TD
    F["Sampled Frame at timestamp t"] --> D["FaceMeshDetector.process()"]
    D -->|face_count == 0| NF["condition: no_face = True"]
    D -->|face_count > 1| MF["condition: multiple_faces = True"]
    D -->|face_count == 1| HP["estimate_head_pose() via solvePnP"]
    HP -->|"|yaw| > 26° OR pitch > 26° OR pitch < -20°"| HT["condition: head_turned = True<br/>(Decoupled: gaze_away suppressed)"]
    HP -->|Head frontal| EG["estimate_gaze()<br/>h_ratio outside (0.35, 0.65)<br/>or v_ratio > 0.65 / < 0.22"]
    EG -->|Off-center| GA["condition: gaze_away = True"]
    EG -->|Centered| OK["Compliant Frame"]

    NF --> L1["Layer 1: Sustained Gate<br/>head_turned>=0.4s (+15)<br/>gaze_away>=0.7s (+12)<br/>no_face>=1.0s (+6)"]
    HT --> L1
    GA --> L1
    L1 -->|Duration too brief| L2["Layer 2: Frequency Rule<br/>&ge;2 brief events in 10s window<br/>frequent_gaze_away (+18)<br/>frequent_head_turned (+18)"]
    MF --> L3["Layer 3: Immediate Flag<br/>multiple_faces (+30)<br/>Optional gap-guarded 2-frame check"]

    L1 --> AGG["Dual Score Aggregation"]
    L2 --> AGG
    L3 --> AGG
    AGG --> RAW["Raw Risk Score (0-100 cap)"]
    AGG --> NORM["Time-Normalized Score<br/>W=600s, per-type caps, alpha=0.10"]
```

---

## 4. Backend / Frontend Communication Sequence

```mermaid
sequenceDiagram
    participant App as Flutter Client (ApiService)
    participant API as FastAPI Server (api.py :8000)
    participant AI as Pipeline & FaceMeshDetector

    App->>API: GET /health
    API-->>App: 200 {status: "healthy", models_loaded}

    alt Mode A: Recorded Video Audit
        App->>API: POST /api/analyze-video (multipart file)
        API->>API: Validate extension, non-empty, <=250 MB
        API->>AI: process_video(tmp_path, debug=True)
        AI-->>API: {risk_score, normalized_score, events, activity_log, frames_analysed}
        API->>API: Delete temporary video in finally block
        API-->>App: 200 ExamAuditReport JSON (or 400 with detail)
    else Mode B: Live Camera Proctoring
        App->>API: POST /api/session/start
        API-->>App: 200 {session_id}
        loop Every ~700ms while camera active
            App->>API: POST /api/session/{id}/frame {image_base64, timestamp_sec}
            API->>AI: detect_single_frame + scorer.update()
            API-->>App: 200 {telemetry, current_risk_score, current_risk_level}
        end
        App->>API: POST /api/session/{id}/finalize
        API-->>App: 200 ExamAuditReport JSON
    end
```

---

## 5. API Endpoint Map

| Method | Endpoint | Purpose | Error Handling Verified |
|---|---|---|---|
| `GET` | `/health` | Service status, model asset checks, active session count | — |
| `GET` | `/api/scenarios` | Lists the 5 simulated calibration scenarios | — |
| `POST` | `/api/scenarios/{key}/run` | Runs `RiskScorer` on a benchmark scenario timeline | `404` on unknown key |
| `POST` | `/api/detect-frame` | Stateless single base64 frame telemetry | `400` bad base64/image, `422` negative timestamp |
| `POST` | `/api/session/start` | Creates a stateful session with `RiskScorer` | — |
| `POST` | `/api/session/{id}/frame` | Decodes frame, updates session scorer, returns live risk | `404` unknown session, `400`/`422` invalid timestamp |
| `POST` | `/api/session/{id}/finalize` | Finalizes session & returns raw + normalized report | `404` missing or already finalized |
| `POST` | `/api/analyze-video` | Saves upload to temp, runs 4 FPS `process_video`, cleans up | `400` empty/corrupt/unsupported, `413` >250 MB |
| `POST` | `/api/rescore` | Re-evaluates `debug_frames` with custom config in memory | `400` malformed payload |
| `POST` | `/api/report/html` | Builds HTML-escaped printable audit certificate | `400` malformed payload |

---

## 6. AI/ML Multi-Stage Detection Cascade (`modules/face_utils.py`)

```mermaid
flowchart LR
    BGR["Input Frame (BGR)"] --> RGB["RGB Image"]
    RGB --> FL["1. FaceLandmarker (VIDEO mode)<br/>478 3D Landmarks, min_conf=0.35<br/>+ duplicate mesh IoU/center suppression"]
    RGB --> BF["2. BlazeFace Short Range<br/>Peripheral / profile faces, min_conf=0.55<br/>+ hand/chest FP suppression"]
    RGB --> OD["3. EfficientDet-Lite0 ('person')<br/>Unauthorized bodies/background students,<br/>score>=0.18 + candidate workspace filter"]
    RGB --> HL["4. HandLandmarker (IMAGE mode)<br/>Reaching intruder arms/hands,<br/>min_conf=0.35 vs candidate workspace"]
    FL --> DEDUP["IoU > 0.25 Box Deduplication"]
    BF --> DEDUP
    OD --> DEDUP
    HL --> DEDUP
    DEDUP --> OUT["total person_count + landmarks_list + auxiliary_persons"]
```

---

## 7. Deployment & CI/CD Architecture

```mermaid
flowchart LR
    DEV["Developer Push to GitHub<br/>(rv-rakesh/FairSight : main)"] --> GHA["GitHub Actions (.github/workflows/build_apps.yml)"]
    GHA --> J1["ubuntu-latest: Backend & Integrity<br/>pytest + validate_flutter_project.py"]
    GHA --> J2["ubuntu-latest: Android APK<br/>Java 21 + Flutter 3.50.0 + Gradle 9.5.0<br/>-> FairSight-Android-APK"]
    GHA --> J3["windows-latest: Windows Desktop<br/>Flutter 3.50.0 + MSVC Win32 Runner<br/>-> FairSight-Windows-Desktop (.zip)"]

    subgraph Runtime["Local / LAN Runtime Deployment"]
        PC["Windows Host PC<br/>uvicorn api:app --host 0.0.0.0 --port 8000<br/>Firewall TCP 8000 Allow (Private)"]
        PC ---|"127.0.0.1:8000"| DESK["FairSight.exe (Windows)"]
        PC ---|"10.0.2.2:8000"| EMU["Android Emulator"]
        PC ---|"PC_LAN_IP:8000 (Wi-Fi)"| PHN["Physical Android Phone"]
    end
```

---

## 8. Concise Presentation (PPT) Bullet Reference

1. **Problem Statement**: Manual proctoring does not scale cleanly, while opaque black-box classifiers and cumulative point counters punish honest candidates during long exams.
2. **FairSight Solution**: Explainable, rule-based behavioral telemetry engine pairing MediaPipe Tasks API (Face + BlazeFace + EfficientDet-Lite0 + HandLandmarker) with OpenCV `solvePnP` head pose and iris-ratio gaze tracking.
3. **3 Key Algorithmic Innovations**:
   - *Head-Gaze Decoupling*: Suppresses `gaze_away` when `head_turned` is active to prevent double counting (`head_turned` + `gaze_away`).
   - *3-Layer Scoring Engine*: Sustained duration gates (`0.4s`/`0.7s`/`1.0s`) + rolling frequency pattern detector (`>=2` in `10s`) + immediate multi-person flag (`+30`).
   - *Windowed Time Normalization*: 10-minute windows (`W=600s`) with per-type caps and persistence factor `alpha=0.10` prevent false High-risk escalation over 3-hour exams.
4. **Engineering & Privacy Safeguards**: Temporary uploaded video files are deleted in a `finally` block; HTML certificates sanitize metadata; single `scoring_config.py` governs all parameters.
5. **Honest Scope & Limitations**: Rule weights are policy-calibrated rather than learned probabilities; local CPU throughput operates at 4 FPS sampling; no external real-student annotated dataset is claimed.
