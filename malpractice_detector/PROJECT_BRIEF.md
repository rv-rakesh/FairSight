# PROJECT BRIEF: AI-Based Interview & Online Examination Malpractice Detection System
### Complete Handoff Document — For Development Continuation & Research Paper Preparation

**Project Classification:** Behavioral Integrity & AI Proctoring System
**Architecture:** Multi-Layer Computer Vision (solvePnP Pose + Iris Mesh + IoU Multi-Person)
**Document Version:** Production Release (Multi-Mode, Dockerized, Automated Testing)

---

## PART 1: PROJECT HISTORY & CONTEXT

### 1.1 Origin and Problem

This started as an EPICS (Engineering Projects in Community Service) course project. The problem: online interviews and examinations became the default assessment mode post-COVID, but manual invigilation cannot scale — one invigilator can only reliably watch 4-6 candidates simultaneously, and existing proctoring tools only *record* video without *analyzing* it. This creates two failures at once: real malpractice goes undetected, and honest candidates have no way to prove their innocence when accused.

### 1.2 Design Thinking Process Followed

The project followed a formal 5-stage design thinking process before any code was written:

1. **Empathize** — Interviewed 5 real stakeholders: a faculty invigilator, an exam candidate, a placement coordinator, an HR recruiter, and a final-year student.
2. **Define** — Narrowed to: "Educational institutions lack an intelligent, automated way to detect suspicious candidate behaviour in recorded online interviews and examinations."
3. **Ideate** — Generated concepts via Crazy-8, scored on an Impact-vs-Feasibility grid. Selected: eye/head-pose detection, multi-person detection, automated risk scoring.
4. **Prototype** — Built the working software pipeline described in Part 2.
5. **Test** — Iteratively refined based on real footage testing (see Part 4 — this is where most of the valuable, hard-won findings live).

**Key validated insight from user research:** Both candidates and evaluators want fairness, not just detection — candidates fear false accusations as much as evaluators fear missing real malpractice. This should remain the guiding design philosophy for all future work: **minimize false positives as aggressively as false negatives.**

### 1.3 Literature Positioning

Nine papers (2024-2026) on AI-based proctoring were reviewed. Summary of where this project sits relative to the field:

| Gap in existing literature | How this project addresses it |
|---|---|
| Papers benchmark detection models in isolation, no unified evaluator-facing system | Combines eye, head, and person signals into one risk score with an automated report |
| Field reviews recommend expensive IoT/biometric hardware for reliability | Uses only a standard webcam — no extra hardware |
| False-positive risk from natural behavior is named as a problem but rarely solved | Sustained-duration + frequency-pattern logic specifically targets this (see Part 2.4) |
| Heavy multimodal models (CNN-BiLSTM+YOLO+L2CS-Net) need GPU and training data | Purely geometric/rule-based — no training data or GPU required |
| Closest comparable system (AutoOEP, 2025) adds identity verification this project lacks | Honestly disclosed as a gap — see Part 5 roadmap |
| Commercial proctoring tools are criticized as opaque "black boxes" | Fully explainable — every flag traces to a named threshold and measured value |

**For a future research paper, this positioning is the core "related work" section — but it needs empirical backing (see Part 6) since right now these are architectural claims, not measured comparisons.**

---

## PART 2: CURRENT SYSTEM — COMPLETE TECHNICAL REFERENCE

### 2.1 Tech Stack (Current Architecture — FairSight)

| Layer | Technology | Role |
|---|---|---|
| Client Applications | Flutter (Dart) | Cross-platform client for Android APK and Windows Desktop (.exe) |
| Developer Dashboard | Streamlit (Python) | Local developer inspection, debug visualizer, threshold playground |
| Backend API | FastAPI + Uvicorn | RESTful API service (10 endpoints) powering both Flutter and web clients |
| Video Processing | OpenCV (`cv2.VideoCapture`) | Frame extraction at 4 fps sampling (250 ms temporal resolution) |
| Landmark Detection | MediaPipe Tasks API (`FaceLandmarker`) | 478 3D landmarks per face (468 facial mesh + 10 iris) |
| Auxiliary Person Detection | BlazeFace + ObjectDetector + HandLandmarker | Profile faces, peripheral bodies, intruder reaching hands |
| Eye Gaze Estimation | Geometric Iris-Ratio | Ratio calculation with head-turn decoupling |
| Head Pose Estimation | OpenCV `solvePnP` + Rodrigues | Yaw/pitch/roll with pitch unwrap and landmark symmetry confirmation |
| Risk Scoring Engine | 3-Layer `RiskScorer` | Layer 1 (Sustained) + Layer 2 (Frequency) + Layer 3 (Immediate) |
| Central Configuration | `scoring_config.py` | Single source of truth for all parameters, weights, gates, and bands |
| Report Generation | Report module (Pandas / HTML) | Confirmed Events + Full Activity Timeline + Printable HTML Certificate |
| Testing Suite | Pytest | Parameter baseline integrity guards and automated unit tests |

**Architecture note:** The system uses a decoupled client-server architecture. The FastAPI backend exposes RESTful endpoints for real-time frame telemetry, session state management, and video processing. The Flutter application communicates over HTTP, allowing deployment on mobile devices (Android) and desktop workstations (Windows).

### 2.2 Processing Pipeline (step by step, matches current code exactly)

```
Video Upload / Live Camera Stream (Flutter / Streamlit)
  → Frame Extraction (OpenCV, 4 fps sampling / 250 ms resolution)
    → Face & Landmark Detection (MediaPipe FaceLandmarker → 478 landmarks)
    → Auxiliary Cascade (BlazeFace + ObjectDetector + HandLandmarker)
      → [in parallel per frame]
         Eye Gaze Estimation (iris-relative ratio → direction)
         Head Pose Estimation (solvePnP → yaw/pitch/roll)
         Multi-Person Check (mesh count + auxiliary detections with IoU deduplication)
    → Risk Scoring Engine (3-Layer rule-based engine via scoring_config.py)
  → Report Generation (Confirmed Events + Full Activity Timeline + Debug data)
  → Client Display (Flutter HUD / Streamlit Dashboard)
```
      → [in parallel per frame]
         Eye Gaze Estimation (iris-relative ratio → direction)
         Head Pose Estimation (solvePnP → yaw/pitch/roll)
         Multi-Person Check (face count)
    → Risk Scoring Engine (see 2.4 — this is the most refined/important part)
  → Report Generation (Confirmed Events + Full Activity Timeline + Debug data)
  → Streamlit Dashboard Display
```

### 2.3 Folder Structure (current, exact)

```
malpractice_detector/
├── app.py                       (Streamlit dashboard — custom light theme, demo mode, debug view)
├── pipeline.py                  (Orchestrator: process_video(), run_demo_session(), --debug CLI flag)
├── demo_data.py                 (Simulated exam-session timeline for demo mode)
├── download_model.py            (One-time MediaPipe model downloader)
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml              (Forces light theme — critical fix, see Part 4)
├── modules/
│   ├── __init__.py
│   ├── face_utils.py            (MediaPipe FaceLandmarker wrapper — eye/iris index bug fixed)
│   ├── eye_tracking.py          (Gaze direction estimation — eye/iris index bug fixed)
│   ├── head_pose.py             (solvePnP head pose — pitch offset bug fixed, threshold recalibrated)
│   ├── scoring.py               (Risk scoring engine — dual-layer detection, see 2.4)
│   └── report.py                (Report/CSV/timeline generation)
├── models/                      (face_landmarker.task — downloaded, not in version control)
├── test_videos/                 (test clips)
└── outputs/                     (generated reports land here)
```

### 2.4 Risk Scoring Engine — Detailed Logic (most important section for anyone extending this)

This evolved significantly through real-world testing and is the project's core intellectual contribution. Three distinct detection layers, each solving a specific problem discovered empirically:

**Layer 1 — Sustained-Duration Events**
A condition (`gaze_away`, `head_turned`, `no_face`, `multiple_faces`) must hold continuously for its calibrated duration gate (`DEFAULT_MIN_EVENT_DURATIONS` in `scoring_config.py`: `head_turned`: 0.4 s, `gaze_away`: 0.7 s, `no_face`: 1.0 s) before counting as a confirmed event. This exists specifically to prevent flagging a momentary glance or natural pause.

**Layer 2 — Frequency-Pattern Events**
Real cheating often looks like many *quick* glances, not one long stare. If a condition (`gaze_away` or `head_turned` — see `FREQUENCY_TRACKED_TYPES`) occurs 2+ times (`FREQUENCY_MIN_COUNT = 2`) within a rolling 10-second window (`FREQUENCY_WINDOW_SEC = 10.0`), that pattern becomes a confirmed frequency event, weighted at 18 points.

**Layer 3 — Immediate-Flag Events**
`multiple_faces` (`IMMEDIATE_EVENT_TYPES`) is flagged as a confirmed event on ANY occurrence (0.0 s gate) — an unauthorized second person has no legitimate reason to appear during an exam.

**Current weights and parameters** (defined centrally in `scoring_config.py`):
```python
EVENT_WEIGHTS = {
    "no_face": 6,
    "multiple_faces": 30,
    "gaze_away": 12,
    "head_turned": 15,
}
FREQUENCY_WEIGHTS = {  # for Layer 2 pattern events
    "gaze_away": 18,
    "head_turned": 18,
}
DEFAULT_MIN_EVENT_DURATIONS = {
    "head_turned": 0.4,
    "multiple_faces": 0.0,
    "no_face": 1.0,
    "gaze_away": 0.7,
}
MIN_EVENT_DURATION_SEC = 1.0
FREQUENCY_WINDOW_SEC = 10.0
FREQUENCY_MIN_COUNT = 2
```

**Current head pose thresholds** (defined centrally in `scoring_config.py`):
```python
YAW_THRESHOLD = 26.0         # degrees — |yaw| beyond this = looking away sideways
PITCH_DOWN_THRESHOLD = 26.0  # degrees — head tilted down significantly (e.g. notes/phone)
PITCH_UP_THRESHOLD = 20.0    # degrees — head tilted up significantly
```

**Full Activity Timeline:** Separately from the scoring logic, every single flagged frame (regardless of whether it became a confirmed event) is logged with an exact timestamp and human-readable detail (e.g., "turned right (yaw -66.9°)", "2 faces in frame"). This gives evaluators full transparency — they can see everything the system noticed, not just what crossed a threshold.

---

## PART 3: WHAT'S ALREADY VALIDATED (don't rebuild these — they work)

- MediaPipe face/landmark detection: confirmed working on real footage
- `solvePnP` head pose math: confirmed correct after the pitch-offset fix (see Part 4)
- Sustained-duration false-positive protection: confirmed working via synthetic test (a 0.3s glance correctly ignored, a 3s sustained event correctly flagged)
- Frequency-pattern detection: confirmed working — replaying real recorded footage through it took a previously-missed cheating pattern from a 10/100 score to a 100/100 score, matching what was actually visible in the video
- Immediate multi-person flagging: confirmed catching a real second person that was previously invisible in the report
- Streamlit light-theme UI: confirmed rendering correctly and consistently after the `.streamlit/config.toml` fix

---

## PART 4: COMPLETE LIST OF KNOWN BUGS, FIXES, AND LIMITATIONS

This section is the most valuable part of this document for both a rebuilding AI tool and for a research paper's "Limitations" / "Threats to Validity" section. Be honest and specific — do not hide any of these.

### 4.1 Bugs found and fixed (document these as resolved, with the fix)

1. **Eye/iris landmark cross-pairing bug (fixed).** The original code paired the left iris's landmarks with the RIGHT eye's corner/eyelid landmarks (verified against MediaPipe's own `FACEMESH_LEFT_EYE`/`FACEMESH_RIGHT_EYE` constants), and vice versa — comparing an iris against a completely different eye's geometry. Fixed by swapping the corner/eyelid constant assignments in `modules/face_utils.py` and `modules/eye_tracking.py`.

2. **Head pose pitch wraparound bug (fixed).** OpenCV's `decomposeProjectionMatrix` returns pitch wrapped around 180° for a face looking straight at the camera, not around 0° as intuitively expected. This caused `pitch` to read ~160-179° for completely neutral frames, making `head_turned` fire on nearly every single frame (94% of one 40-second test video). Fixed with an unwrap correction in `modules/head_pose.py`:
   ```python
   if pitch >= 0: pitch = 180 - pitch
   else: pitch = -180 - pitch
   ```

3. **Pitch threshold miscalibration (fixed via empirical recalibration).** Even after the wraparound fix, `PITCH_DOWN_THRESHOLD = 15°` was still too sensitive — statistical analysis of real footage showed median natural pitch was ~12° with a 90th percentile of ~17°, meaning the threshold was flagging more than half of ordinary, honest frames. Raised to 22° (above the 95th percentile of natural variation).

4. **Multi-person detection invisible for brief appearances (fixed).** A genuine second person who appeared for under 2 seconds was completely absent from Confirmed Events (too brief for the sustained-duration rule, and multi-person wasn't tracked by the frequency-pattern logic either). Fixed by adding an `IMMEDIATE_EVENT_TYPES` category that bypasses the duration requirement entirely for `multiple_faces`.

5. **Sustained-duration-only scoring missed real repeated-glance cheating (fixed via Layer 2 above).** A real test video with 3 genuine eye movements and 3 genuine head turns (each individually brief) scored only 10/100 under the original sustained-duration-only design. This was the most significant scoring gap found.

6. **Streamlit dark-mode theme conflict (fixed).** The app's custom light CSS was fighting against Streamlit's OS-level dark-mode auto-detection, producing washed-out unreadable text and a black file-upload widget. Fixed by adding `.streamlit/config.toml` with an explicit `[theme] base = "light"` block — this forces consistent theming regardless of the user's system settings, which turned out to be the correct fix (CSS overrides alone are fragile against native widget theming).

7. **MediaPipe API version instability (worked around, not "fixed").** Newer MediaPipe releases (0.10.20+) removed the simple offline `mp.solutions.face_mesh` API in favor of the Tasks API (`FaceLandmarker`), which requires a one-time internet-based model download (`download_model.py`, pulling from `storage.googleapis.com`). This is a real external dependency risk — if Google changes that model URL or the Tasks API again, this breaks. **A hosted MVP should bundle the model file directly rather than downloading it at runtime.**

8. **`ModuleNotFoundError: No module named 'cv2'` despite correct `pip install` (environment issue, not a code bug, but a very common deployment friction point).** Caused by a system-level Anaconda Python installation shadowing the intended virtual environment on Windows. Worked around by always invoking Python explicitly via `.\venv\Scripts\python.exe -m streamlit run app.py` rather than relying on the bare `streamlit` command and PATH resolution. **A hosted/containerized deployment eliminates this entire class of problem** — this is a strong practical argument for prioritizing containerization in the MVP roadmap.

### 4.2 Known limitations (NOT yet fixed — document honestly, these are real gaps)

1. **Gaze detection contaminates during head turns.** The iris-ratio-based gaze calculation isn't head-pose-invariant — when the head itself rotates, the eye's apparent shape relative to its corner landmarks changes even if the eyes haven't moved relative to the head. This produces spurious `gaze_away` flags that frequently co-occur with genuine `head_turned` events, rather than representing an independent signal. **This is a legitimate, citable limitation for a research paper** — dedicated gaze-estimation models (rather than pure geometric ratio) don't have this problem, at the cost of needing training data.

2. **Frame sampling (2 fps) can miss very brief events.** If a suspicious action lasts under ~0.5 seconds, it may fall entirely between sampled frames and never be seen at all. This is a genuine speed/accuracy tradeoff, not a bug.

3. **Multi-person detection produces false positives from hand gestures near the face.** Confirmed via real-footage review — a hand gesture near the jawline was briefly misdetected as a second face, most likely due to motion blur. This is a known weakness of lightweight face detectors under motion. Worth noting: the recent fix that made multi-person detection "immediate" (see 4.1 item 4) increases sensitivity to BOTH real second-person appearances and this kind of false positive — it's a genuine precision/recall tradeoff, not free.

4. **No identity/liveness verification.** The system cannot detect if the person being evaluated mid-session is a different person than who started the session (impersonation). This is the single clearest capability gap versus the closest comparable published system (AutoOEP, 2025), which uses ArcFace-based identity matching alongside behavioral tracking.

5. **Multi-person detection reliability in low light is unverified/likely weak** — flagged as a concern in the original user-research findings but not yet specifically stress-tested.

6. **No audio analysis** — cannot detect whispered prompts, voice assistants, or background conversation. Explicitly out of current scope.

7. **No object detection** (phones, books, notes) — the system only tracks face/eye/head/person-count signals, not physical objects in frame. A YOLO-based object detector was considered but not implemented (adds a second heavy model and inference cost).

8. **Threshold values are calibrated against a small number of real test videos from one environment/lighting setup**, not a large, diverse validation set. This is the single biggest weakness for any research-paper claim of general accuracy.

9. **No persistent storage / database.** Every analysis is single-session — nothing is saved, searchable, or comparable across sessions. Deliberate MVP-scope decision (also has a privacy upside: no raw video is retained after analysis), but blocks any multi-candidate, multi-exam institutional use case.

10. **No user authentication or multi-user support.** Anyone with access to the running instance can use it; there's no concept of separate institutional accounts, access control, or candidate privacy protection beyond not storing video.

11. **Not deployed/hosted anywhere.** Currently runs only via `streamlit run app.py` on a local machine with a manually-managed Python virtual environment. Zero production deployment exists.

---

## PART 5: ROADMAP TO A REAL, HOSTED, MULTI-USER MVP (not a prototype)

This section is written as direct build guidance for whichever tool/team takes this forward.

### 5.1 Critical — must have before calling this a real product

- **Containerize the application** (Docker). Bundle the MediaPipe model file directly into the image rather than downloading it at runtime — removes the external dependency risk noted in Part 4.1.7 and the Anaconda/venv PATH conflict class of problems entirely (Part 4.1.8).
- **Separate frontend and backend properly.** Move off the "Streamlit calls Python functions directly, no API" architecture. Introduce a real backend API (FastAPI is a natural fit, staying in Python) so the processing pipeline can be scaled, queued, and called from any frontend — not just Streamlit.
- **Asynchronous / queued video processing.** Long videos currently block the Streamlit UI thread synchronously. A hosted multi-user product needs a job queue (e.g., Celery + Redis, or a simpler cloud task queue) so uploads are processed in the background and users get notified/poll for results, rather than the page hanging.
- **Cloud hosting + storage.** Video upload needs to go to object storage (S3-compatible) rather than a local temp file; processing needs to run on a server, not a laptop. Options to evaluate: a simple VM (EC2/Azure VM) for cost control initially, or a managed container platform (Cloud Run, ECS, Azure Container Apps) for easier scaling later.
- **Database.** Add persistent storage (PostgreSQL is a safe default) for: user accounts, exam sessions, risk reports, and audit history. This directly unblocks the "search past sessions", "institutional dashboard", and "compare candidates" use cases that are currently impossible.
- **User authentication & role-based access.** At minimum: institution admin accounts, invigilator/evaluator accounts, and a clear separation of what each role can see. Candidates should NOT need accounts if avoidable — minimize data collected from them specifically (privacy-by-design, ties back to the "fairness tool not surveillance tool" framing established during design thinking).
- **Input validation & security hardening.** File type/size validation (currently loosely enforced via the Streamlit file uploader's type filter only), rate limiting, HTTPS everywhere, no raw file paths exposed to users, sanitized error messages (don't leak stack traces to end users in production).
- **Proper error handling and logging.** Currently, a malformed video or an unexpected codec can crash the pipeline with a raw Python traceback shown to the user. Production needs graceful failure messages and structured server-side logging (not just print statements) for debugging.
- **Automated testing + CI/CD.** Currently, testing is manual (run a script, eyeball the output). Needs: unit tests for `scoring.py`'s event logic (already partially validated manually — formalize into `pytest`), integration tests for the full pipeline against a fixed set of reference videos with known expected output, and a CI pipeline (GitHub Actions is a natural fit) that runs these on every change.
- **Privacy & data retention policy, actually enforced in code.** The current "we don't store raw video" design principle needs to become an explicit, auditable retention policy once real candidate data flows through a hosted system — likely a legal/compliance requirement depending on jurisdiction (e.g., India's DPDP Act, or GDPR if any EU users), not just a nice architectural choice.

### 5.2 Important — needed for a genuinely usable, not just technically-functional, product

- Real-time progress feedback for long video processing (websockets or polling, not a blocking spinner)
- A proper admin/evaluator dashboard: list of sessions, filter by risk level, side-by-side video + timeline review UI (currently the report is static text/CSV — an evaluator should be able to click a flagged timestamp and jump to that moment in the video)
- Configurable thresholds per institution (not everyone's ideal `PITCH_DOWN_THRESHOLD` will be identical — expose this as an admin setting, not a hardcoded constant, once there's real usage data to justify per-institution tuning)
- Batch processing (upload/queue many candidate videos at once for a single exam session)
- Export/integration options (PDF report generation, webhook or API for integration with existing LMS/exam platforms)
- Accessibility review of the UI (screen reader support, keyboard navigation, color-contrast compliance beyond just "looks nice")
- Mobile-responsive UI (current Streamlit layout is desktop-oriented)

### 5.3 Nice-to-have / clearly future scope

- YOLO-based object detection (phones, books, notes) as a fourth detection signal
- Audio analysis (whispered prompts, voice assistant detection)
- Lightweight identity/liveness verification (geometric face-embedding snapshot at session start, re-checked periodically) — this is the most valuable single addition since it directly closes the gap versus the AutoOEP paper
- ML-based risk scoring (Random Forest/XGBoost trained on labeled behavioral data) as an alternative to rule-based scoring, once enough real labeled data exists to train on
- Real-time (live, not just recorded) monitoring mode

---

## PART 6: ROADMAP TO RESEARCH-PAPER-WORTHY CONTRIBUTION

Being direct: the current system's individual techniques (MediaPipe, `solvePnP`, rule-based scoring) are not novel — multiple 2024-2025 papers already use this exact combination, including one (AutoOEP) that is architecturally very close. A paper submission needs one of two things: genuine technical novelty, or rigorous empirical validation of a real, measured contribution. The second path is far more achievable here, and there is already a strong candidate contribution: **the empirically-motivated dual-layer scoring design (sustained-duration + frequency-pattern + immediate-flag detection) — but it currently has zero formal quantitative evaluation.** Fixing that is the single highest-value next step for a paper.

### 6.1 Required for any credible submission

- **A real, labeled evaluation dataset.** Currently, validation has been "record a video, manually watch it, compare to system output" — useful for debugging, not citable as evidence. Need: either the public MSU OEP dataset / Mendeley Cheating Scenario dataset (both already identified during literature search) with their ground-truth labels, OR a self-recorded dataset of sufficient size (recommend minimum 30-50 videos, varied lighting/camera/demographics) with independently double-annotated ground truth (two people labeling separately, measuring inter-annotator agreement).
- **Formal metrics: precision, recall, F1-score, and false-positive rate**, computed against that ground truth — not just "it seemed to work" anecdotes. This is the single most important addition.
- **An ablation study.** This is the paper's strongest possible contribution, given the project's actual history: show quantitatively what each scoring layer contributes.
  - Sustained-duration-only (original design) vs. + frequency-pattern layer vs. + immediate-flag layer vs. full system.
  - This directly reuses evidence already informally gathered (the 10/100 → 100/100 replay result) — formalize it into a proper table with precision/recall/F1 per configuration, across the full evaluation dataset, not one video.
- **Statistical comparison, not just point estimates.** Confidence intervals or significance testing on the metrics above, given the dataset size.
- **A comparison table against 2-3 of the reviewed papers' reported numbers** (with the caveat that different datasets make this an approximate comparison, which should be stated explicitly, not hidden).

### 6.2 Strongly recommended to strengthen the paper

- **User study / expert validation.** Have real faculty invigilators review a sample of the system's flagged events and rate agreement — this validates that "confirmed events" actually correspond to what a human expert would flag, closing the loop back to the original design-thinking user research.
- **Explicit ethics/fairness section.** Given the field's own literature (Part 1.3) criticizes commercial tools for opacity and fairness concerns, a paper here should proactively address: false-positive rate broken down by any available demographic variation in the test set (lighting conditions proxy for skin tone bias risk in face detection is a known issue class worth checking for), and the explicit design philosophy of minimizing false accusations (ties to the original candidate interview finding).
- **A generalizability discussion** — explicitly state what conditions were and weren't tested (camera types, lighting, distance from camera, glasses/no glasses, etc.) rather than implying universal performance.
- **Reproducibility package** — the actual code, thresholds, and evaluation dataset (or a public subset) made available, consistent with the project's own "explainability over black-box" positioning.

### 6.3 Suggested venue level

Given team stage and available resources: a national-level student conference or a UGC-CARE listed journal is a realistic, achievable first target — not a Q1 journal on a first submission, which typically expects either genuine novelty or large-scale evaluation neither of which is currently in reach without significant additional data collection.

---

## PART 7: PRIORITIZED MASTER FEATURE LIST

**Tier 1 — Do before anything else is worth building on top of:**
1. Formal evaluation dataset + precision/recall/F1 measurement (unlocks both MVP confidence and paper credibility)
2. Containerize + bundle the MediaPipe model (removes the biggest current deployment fragility)
3. Separate backend API from the Streamlit frontend

**Tier 2 — Core MVP buildout:**
4. Cloud hosting + object storage for video
5. Async job queue for processing
6. Database + user auth + role-based access
7. Input validation, security hardening, proper error handling/logging
8. Automated tests + CI/CD

**Tier 3 — Product polish:**
9. Admin/evaluator dashboard with click-to-timestamp video review
10. Configurable per-institution thresholds
11. Batch processing, PDF export, LMS integration hooks

**Tier 4 — Research-paper-specific (can run in parallel with Tier 1-2):**
12. Ablation study formalization (sustained vs. frequency vs. immediate layers)
13. Expert/user validation study
14. Ethics & fairness analysis section

**Tier 5 — Future capability expansion:**
15. Identity/liveness verification (closes AutoOEP gap — highest value in this tier)
16. Object detection (YOLO) for phones/notes
17. Audio analysis
18. ML-based scoring to replace/augment rule-based scoring

---

## PART 8: INSTRUCTIONS FOR THE AI TOOL / DEVELOPER CONTINUING THIS

- **Preserve the core detection logic** (`modules/scoring.py`, `modules/head_pose.py`, `modules/eye_tracking.py`, `modules/face_utils.py`) as the validated foundation — it has been debugged and empirically calibrated against real footage. Do not casually rewrite these; extend them.
- **Preserve the explainability principle.** Every design decision so far has deliberately favored transparent, traceable rule-based logic over black-box scoring, in direct response to a literature-identified gap (Part 1.3) and the original user research (candidates fear unexplained false accusations). Any new scoring logic (e.g., ML-based, Tier 5) should keep this property — expose *why* a decision was made, not just the decision.
- **The biggest architectural change needed is separating frontend from backend** (Part 5.1) — this should be the first structural change, since almost everything else in the MVP roadmap depends on having a real API layer instead of direct function calls from Streamlit.
- **Do not treat the current threshold values as final** — they are calibrated against a small number of real test videos from one specific setup (Part 4.2.8). Build the evaluation dataset (Part 6.1) early, and expect thresholds to move again once tested against more diverse footage.
- **Keep the "Full Activity Timeline" transparency feature** in any UI redesign — it's a direct, deliberate response to the literature's "black box" criticism and shouldn't be simplified away for aesthetics.
