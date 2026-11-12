"""
app.py
------
AI-Based Interview & Online Examination Malpractice Detection System
Institutional Assessment Integrity Platform (Wide Layout)
"""

import os
import time
import tempfile
import numpy as np
import cv2
import pandas as pd
import streamlit as st

from pipeline import process_video
from demo_data import SCENARIOS, run_scenario_session
from scoring_config import (
    EVENT_WEIGHTS,
    FREQUENCY_WEIGHTS,
    YAW_THRESHOLD,
    PITCH_DOWN_THRESHOLD,
    MIN_EVENT_DURATION_SEC,
    FREQUENCY_MIN_COUNT,
    FREQUENCY_WINDOW_SEC,
)
from modules.scoring import RiskScorer, rescore_telemetry
from modules.face_utils import FaceMeshDetector, draw_face_annotations
from modules.eye_tracking import estimate_gaze
from modules.head_pose import estimate_head_pose
from modules.report import (
    build_summary_text,
    build_events_dataframe,
    build_activity_log_dataframe,
    build_html_printable_report,
    format_timestamp,
    _pretty_type,
)
from modules.visualizations import (
    render_risk_gauge,
    render_timeline_chart,
    render_flag_density_chart,
    render_pose_scatter,
    render_violation_breakdown,
    render_gaze_distribution,
)

# ---------------------------------------------------------------------------
# Streamlit Configuration & Custom Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FairSight — AI Malpractice Detection System",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Apple / Minimalist Enterprise Light Palette */
    :root {
        --primary: #2563EB;
        --primary-hover: #1D4ED8;
        --navy: #0F172A;
        --text-main: #0F172A;
        --text-sub: #64748B;
        --bg-main: #F8FAFC;
        --card-bg: #FFFFFF;
        --border-color: #E2E8F0;
        --risk-low: #059669;
        --risk-med: #D97706;
        --risk-high: #DC2626;
    }

    /* Hide Deploy Button, Toolbar Actions, and Footer */
    [data-testid="stAppDeployButton"],
    [data-testid="stToolbarActions"],
    #MainMenu,
    footer,
    [data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Minimalist Header & Sidebar Toggle */
    header[data-testid="stHeader"] {
        background: transparent !important;
        color: #0F172A !important;
        height: 2.4rem !important;
    }
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 999999 !important;
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        padding: 5px !important;
    }

    .stApp {
        background-color: #F8FAFC;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #0F172A;
    }

    h1, h2, h3, h4 {
        color: #0F172A;
        font-weight: 700;
        letter-spacing: -0.4px;
    }

    /* Apple-Style Minimalist Banner */
    .app-header {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03), 0 1px 2px rgba(0, 0, 0, 0.02);
        display: flex;
        align-items: center;
        gap: 1.2rem;
    }
    .header-icon {
        width: 48px;
        height: 48px;
        background: #EFF6FF;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        border: 1px solid #DBEAFE;
    }
    .header-text {
        flex: 1;
    }
    .app-header h1 {
        color: #0F172A !important;
        font-size: 1.55rem;
        font-weight: 700;
        margin: 0 0 0.2rem 0;
        letter-spacing: -0.5px;
    }
    .app-header p {
        color: #64748B !important;
        font-size: 0.90rem;
        margin: 0;
        line-height: 1.4;
    }

    /* Apple-Style Status Strip */
    .status-strip-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 0.85rem 1.2rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
    }
    .strip-col {
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding: 0 0.5rem;
    }
    .strip-label {
        font-size: 0.70rem;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin-bottom: 2px;
    }
    .strip-val {
        font-size: 0.94rem;
        font-weight: 700;
        color: #0F172A;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Refined Light Verdict Banners */
    .verdict-low {
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        color: #065F46;
    }
    .verdict-med {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        color: #92400E;
    }
    .verdict-high {
        background: #FEF2F2;
        border: 1px solid #FECACA;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        color: #991B1B;
    }

    /* Event Cue Card */
    .cue-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.6rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
        transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .cue-card:hover {
        border-color: #2563EB;
        background: #F8FAFC;
        box-shadow: 0 3px 8px rgba(37, 99, 235, 0.08);
    }
    .cue-card-selected {
        border: 2px solid #2563EB !important;
        background: #EFF6FF !important;
    }

    /* Minimalist Apple Buttons */
    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.90rem;
        letter-spacing: -0.2px;
        padding: 0.5rem 1.1rem;
        transition: all 0.15s ease;
    }
    div.stButton > button[kind="primary"] {
        background: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 2px 6px rgba(37, 99, 235, 0.25) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #1D4ED8 !important;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.35) !important;
    }
    div.stButton > button[kind="secondary"] {
        background: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #E2E8F0 !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background: #F8FAFC !important;
        border-color: #CBD5E1 !important;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session State Initialization (Per-Mode Storage to Prevent State Leaks)
# ---------------------------------------------------------------------------
if "active_mode" not in st.session_state:
    st.session_state["active_mode"] = "video"

if "mode_results" not in st.session_state:
    st.session_state["mode_results"] = {
        "scenario": {
            "result": run_scenario_session("composite_session"),
            "source_name": "Comprehensive (Mixed)",
            "scenario_key": "composite_session",
            "duration": 90.0,
        },
        "video": {
            "result": None,
            "source_name": None,
            "uploaded_path": None,
            "duration": 0.0,
        },
        "webcam": {
            "result": None,
            "source_name": None,
            "live_frames": [],
            "uploaded_path": None,
            "duration": 0.0,
        },
    }

if "selected_event_idx" not in st.session_state:
    st.session_state["selected_event_idx"] = None

if "jump_timestamp" not in st.session_state:
    st.session_state["jump_timestamp"] = 0.0

if "candidate_meta" not in st.session_state:
    st.session_state["candidate_meta"] = {
        "candidate_name": "Standard Candidate",
        "candidate_id": "CAND-89412",
        "exam_title": "Online Proctored Examination",
        "department": "Assessment & Integrity Division",
        "institution": "Autonomous Examination Authority",
        "evaluator_name": "Chief Proctor / Auditor",
    }


@st.cache_resource
def get_face_detector():
    """Loads and caches the multi-stage face and person detector."""
    return FaceMeshDetector()


# ---------------------------------------------------------------------------
# Header (Apple / Minimalist Enterprise Light)
# ---------------------------------------------------------------------------
st.markdown("""
<div class="app-header">
    <div class="header-icon">🛡️</div>
    <div class="header-text">
        <h1>AI-Based Malpractice Detection Platform</h1>
        <p>Explainable, transparent, evidence-based behavioral integrity analysis for exams and interviews.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Global Navigation Bar: 3 Modes (Always accessible on main workspace)
# ---------------------------------------------------------------------------
nav_c1, nav_c2, nav_c3 = st.columns(3)
cur_m = st.session_state["active_mode"]

with nav_c1:
    if st.button("🎬 Scenario Simulation", type="primary" if cur_m == "scenario" else "secondary", use_container_width=True, key="main_nav_btn_scenario"):
        if cur_m != "scenario":
            st.session_state["active_mode"] = "scenario"
            st.rerun()

with nav_c2:
    if st.button("📤 Upload Examination Video", type="primary" if cur_m == "video" else "secondary", use_container_width=True, key="main_nav_btn_video"):
        if cur_m != "video":
            st.session_state["active_mode"] = "video"
            st.rerun()

with nav_c3:
    if st.button("📹 Live Webcam Proctoring", type="primary" if cur_m == "webcam" else "secondary", use_container_width=True, key="main_nav_btn_webcam"):
        if cur_m != "webcam":
            st.session_state["active_mode"] = "webcam"
            st.rerun()

current_mode = st.session_state["active_mode"]


# ---------------------------------------------------------------------------
# Sidebar Navigation & Mode Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 1. Analysis Source")
    mode_options = [
        "Scenario Simulation",
        "Uploaded Video",
        "Live Webcam",
    ]
    mode_map = {
        "Scenario Simulation": "scenario",
        "Uploaded Video": "video",
        "Live Webcam": "webcam",
    }
    inv_mode_map = {v: k for k, v in mode_map.items()}

    chosen_label = st.radio(
        "Select Source",
        mode_options,
        index=mode_options.index(inv_mode_map[st.session_state["active_mode"]]),
        label_visibility="collapsed",
        key="sidebar_mode_radio_select",
    )
    if mode_map[chosen_label] != st.session_state["active_mode"]:
        st.session_state["active_mode"] = mode_map[chosen_label]
        st.rerun()

    st.markdown("---")
    st.markdown("### 2. Mode Controls")

    # Mode 1: Scenario Simulation Controls
    if current_mode == "scenario":
        preset_names = {
            "composite_session": "Comprehensive (Mixed)",
            "honest_candidate": "Honest Candidate (Clean)",
            "occasional_distraction": "Occasional Distraction",
            "screen_peeking": "Screen Peeking (Notes)",
            "unauthorized_person": "Unauthorized Person",
        }
        active_key = st.session_state["mode_results"]["scenario"].get("scenario_key", "composite_session")
        if active_key not in preset_names:
            active_key = "composite_session"

        selected_key = st.selectbox(
            "Select Scenario Preset",
            list(preset_names.keys()),
            index=list(preset_names.keys()).index(active_key),
            format_func=lambda k: preset_names[k],
        )
        info = SCENARIOS[selected_key]
        st.caption(f"**Expected**: {info['expected_score']} ({info['expected_level']} Risk)\n\n{info['description']}")

        if st.button("Load & Evaluate Scenario", type="primary", use_container_width=True):
            with st.spinner("Simulating telemetry & scoring..."):
                res = run_scenario_session(selected_key)
                st.session_state["mode_results"]["scenario"] = {
                    "result": res,
                    "source_name": preset_names[selected_key],
                    "scenario_key": selected_key,
                    "duration": res["video_duration_sec"],
                }
                st.session_state["selected_event_idx"] = None
                st.session_state["jump_timestamp"] = 0.0
            st.rerun()

    # Mode 2: Video Upload Controls in Sidebar
    elif current_mode == "video":
        vid_store = st.session_state["mode_results"]["video"]
        if vid_store.get("source_name"):
            st.markdown(f"**Current File:** `{vid_store['source_name']}`")
            if vid_store.get("result"):
                st.caption(f"Status: Analyzed ({vid_store['duration']:.1f}s)")
                if st.button("Re-Analyze Video", use_container_width=True, key="sidebar_reanalyze_btn"):
                    with st.spinner("Re-analyzing frames..."):
                        res = process_video(vid_store["uploaded_path"], debug=True)
                        vid_store["result"] = res
                        vid_store["duration"] = res["video_duration_sec"]
                        st.session_state["selected_event_idx"] = None
                        st.session_state["jump_timestamp"] = 0.0
                    st.rerun()
        else:
            st.info("Upload your exam video file using the dedicated dropzone in the main workspace.")

    # Mode 3: Live Webcam Controls
    else:
        st.caption("Live Proctoring Mode active. Use the controls in the main workspace.")
        if st.button("Reset Live Session", use_container_width=True):
            st.session_state["mode_results"]["webcam"] = {
                "result": None,
                "source_name": None,
                "live_frames": [],
                "uploaded_path": None,
                "duration": 0.0,
            }
            st.rerun()

    # Advanced Settings (Threshold Playground relocated here per Audit Item 3.3)
    st.markdown("---")
    with st.expander("⚙️ Advanced Settings / Sensitivity", expanded=False):
        st.caption("Adjust detection rigor. Updates take effect immediately.")
        p_yaw = st.slider("Yaw Threshold (°)", 15.0, 40.0, float(YAW_THRESHOLD), 1.0)
        p_pitch = st.slider("Pitch Threshold (°)", 15.0, 35.0, float(PITCH_DOWN_THRESHOLD), 1.0)
        p_dur = st.slider("Sustained Duration (s)", 0.2, 4.0, float(MIN_EVENT_DURATION_SEC), 0.1)

        if st.button("Apply Custom Rigor", use_container_width=True):
            active_data = st.session_state["mode_results"][current_mode]
            if active_data.get("result") and active_data["result"].get("debug_frames"):
                cfg = {
                    "yaw_threshold": p_yaw,
                    "pitch_down_threshold": p_pitch,
                    "min_event_duration_sec": p_dur,
                }
                active_data["result"] = rescore_telemetry(active_data["result"]["debug_frames"], config=cfg)
                st.success("Rescored in <50ms!")
                st.rerun()

    with st.expander("ℹ️ About & System Telemetry", expanded=False):
        st.caption("MediaPipe 478 3D Mesh · OpenCV solvePnP · BlazeFace 2D · EfficientDet Person Detector · 3-Layer Rule Engine")


# ---------------------------------------------------------------------------
# Resolve Current Active Data
# ---------------------------------------------------------------------------
active_store = st.session_state["mode_results"][current_mode]
active_result = active_store.get("result")
has_data = active_result is not None


# ---------------------------------------------------------------------------
# Fixed 5-Column Status Strip (Audit Item 3.1)
# ---------------------------------------------------------------------------
c_src, c_mode, c_risk, c_time, c_viols = st.columns(5)

with c_src:
    src_val = active_store.get("source_name") or "—"
    st.markdown(f'<div class="strip-col"><div class="strip-label">Source</div><div class="strip-val" title="{src_val}">{src_val}</div></div>', unsafe_allow_html=True)

with c_mode:
    mode_label = "Preset Simulation" if current_mode == "scenario" else ("Uploaded Video" if current_mode == "video" else "Live Webcam")
    st.markdown(f'<div class="strip-col"><div class="strip-label">Mode</div><div class="strip-val">{mode_label}</div></div>', unsafe_allow_html=True)

with c_risk:
    if has_data:
        lvl = active_result["risk_level"]
        sc = active_result["risk_score"]
        color = "#2E8B57" if lvl == "Low" else ("#E0A100" if lvl == "Medium" else "#C0392B")
        st.markdown(f'<div class="strip-col"><div class="strip-label">Risk Verdict</div><div class="strip-val" style="color:{color};">{lvl.upper()} ({sc}/100)</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="strip-col"><div class="strip-label">Risk Verdict</div><div class="strip-val">—</div></div>', unsafe_allow_html=True)

with c_time:
    time_str = f"{active_result['video_duration_sec']:.1f} s" if has_data else "—"
    st.markdown(f'<div class="strip-col"><div class="strip-label">Analyzed Time</div><div class="strip-val">{time_str}</div></div>', unsafe_allow_html=True)

with c_viols:
    viols_str = f"{len(active_result.get('events', []))} events" if has_data else "—"
    st.markdown(f'<div class="strip-col"><div class="strip-label">Confirmed Events</div><div class="strip-val">{viols_str}</div></div>', unsafe_allow_html=True)

st.markdown('<hr style="margin: 0.6rem 0 1.2rem 0; border: none; border-top: 1px solid #E2E8F0;">', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Scenario Mode Information Callout
# ---------------------------------------------------------------------------
if current_mode == "scenario":
    st.markdown("""
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.55rem 0.9rem; margin-bottom: 0.8rem; display: flex; align-items: center; justify-content: space-between;">
        <div style="font-size: 0.84rem; color: #475569;">
            💡 Currently viewing <strong>Scenario Simulation</strong> presets. To upload and analyze your own examination video, click <strong>📤 Upload Examination Video</strong> in the top navigation bar.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Video Mode Workspace (Hero Upload Dropzone on Main Page)
# ---------------------------------------------------------------------------
if current_mode == "video":
    vid_store = st.session_state["mode_results"]["video"]
    with st.container(border=True):
        if vid_store.get("result") is not None:
            # Video is already analyzed: show a clean summary bar with option to upload a different video
            c_sum1, c_sum2 = st.columns([3, 1])
            with c_sum1:
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 0.8rem; padding: 0.2rem 0;">
                    <div style="font-size: 1.6rem;">📹</div>
                    <div>
                        <div style="font-weight: 700; font-size: 1rem; color: #0F172A;">{vid_store.get('source_name', 'Uploaded Video')}</div>
                        <div style="font-size: 0.82rem; color: #64748B;">Duration: {vid_store.get('duration', 0.0):.1f}s · Multi-Stage AI Analysis Complete · Full Integrity Report Below</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_sum2:
                if st.button("🔄 Upload Another Video", use_container_width=True, key="btn_upload_another_vid"):
                    vid_store["result"] = None
                    vid_store["source_name"] = None
                    vid_store["uploaded_path"] = None
                    vid_store["duration"] = 0.0
                    st.rerun()
        else:
            # Video not analyzed yet: show full upload dropzone and Run button
            st.markdown("""
            <div style="margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.22rem; font-weight: 700; color: #0F172A;">
                    📤 Upload Examination Video File
                </h3>
                <p style="margin: 0.25rem 0 0.8rem 0; color: #64748B; font-size: 0.88rem;">
                    Select or drag-and-drop your candidate recording (MP4, MOV, AVI, MKV). AI analyzes face mesh (478 points), 3D head pose (yaw/pitch), gaze direction, and secondary persons with candidate body suppression at 2 FPS.
                </p>
            </div>
            """, unsafe_allow_html=True)

            uploaded_vid = st.file_uploader(
                "Select examination video file",
                type=["mp4", "mov", "avi", "mkv"],
                label_visibility="collapsed",
                key="main_page_video_uploader",
                help="Recommended: candidate face clearly in frame at standard webcam resolution.",
            )

            if uploaded_vid is not None:
                if vid_store.get("source_name") != uploaded_vid.name:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_vid.name)[1]) as tmp:
                        tmp.write(uploaded_vid.read())
                        vid_store["uploaded_path"] = tmp.name
                        vid_store["source_name"] = uploaded_vid.name
                        vid_store["result"] = None
                        vid_store["duration"] = 0.0

                file_size_mb = os.path.getsize(vid_store["uploaded_path"]) / (1024 * 1024)
                st.markdown(f"""
                <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 4px solid #2563EB; border-radius: 12px; padding: 0.9rem 1.1rem; margin-top: 0.6rem; margin-bottom: 0.9rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <div style="font-weight: 700; font-size: 0.95rem; color: #0F172A;">📁 {uploaded_vid.name}</div>
                    <div style="font-size: 0.82rem; color: #64748B; margin-top: 3px;">Size: {file_size_mb:.2f} MB · Status: Ready for AI Forensic Analysis</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("🚀 Run Video AI Analysis", type="primary", use_container_width=True, key="btn_run_main_video"):
                    p_bar = st.progress(0.0, text="Initializing detection pipeline...")

                    def update_progress(frac):
                        p_bar.progress(min(1.0, frac), text=f"Analyzing frames & detecting features... {int(frac * 100)}%")

                    with st.spinner("Extracting frames & running 3D head pose, gaze, and person detection..."):
                        res = process_video(
                            vid_store["uploaded_path"],
                            progress_callback=update_progress,
                            debug=True,
                        )
                        vid_store["result"] = res
                        vid_store["duration"] = res["video_duration_sec"]
                        st.session_state["selected_event_idx"] = None
                        st.session_state["jump_timestamp"] = 0.0
                    p_bar.empty()
                    st.rerun()


# ---------------------------------------------------------------------------
# Webcam Workspace (If Active Mode is Webcam)
# ---------------------------------------------------------------------------
if current_mode == "webcam":
    with st.container(border=True):
        st.subheader("Live Webcam Proctoring Studio")
        st.caption("Verify candidate identity, test live tracking, or record a timed trial session.")

        cam_tab1, cam_tab2 = st.tabs(["Snapshot Check", "Timed Session"])

        with cam_tab1:
            col_shot1, col_shot2 = st.columns([1.2, 1.8])
            with col_shot1:
                cam_shot = st.camera_input("Capture Proctoring Photo")
                st.caption("Allow camera access in your browser to proceed.")

            with col_shot2:
                if cam_shot is not None:
                    bytes_data = cam_shot.getvalue()
                    np_arr = np.frombuffer(bytes_data, np.uint8)
                    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                    detector = get_face_detector()
                    det_res = detector.process(img_bgr)

                    face_count = det_res["face_count"]
                    gaze, pose = None, None
                    conds = {
                        "no_face": face_count == 0,
                        "multiple_faces": face_count > 1,
                        "gaze_away": False,
                        "head_turned": False,
                    }
                    details = {}

                    if face_count == 1 and len(det_res["landmarks_list"]) > 0:
                        landmarks = det_res["landmarks_list"][0]
                        gaze = estimate_gaze(landmarks)
                        pose = estimate_head_pose(landmarks, det_res["frame_shape"])

                        conds["head_turned"] = pose["flag"]
                        conds["gaze_away"] = (gaze["direction"] != "center") and (not pose["flag"])

                        if conds["gaze_away"]:
                            details["gaze_away"] = f"looking {gaze['direction']}"
                        if conds["head_turned"]:
                            yaw_v = pose["yaw"] if pose["yaw"] is not None else 0.0
                            pitch_v = pose["pitch"] if pose["pitch"] is not None else 0.0
                            turn_dir = "right" if yaw_v < 0 else "left"
                            tilt_dir = "down" if pitch_v > 0 else "up"
                            details["head_turned"] = f"turned {turn_dir} ({yaw_v:.1f}°)" if abs(yaw_v) >= abs(pitch_v) else f"tilted {tilt_dir} ({pitch_v:.1f}°)"

                    annotated = draw_face_annotations(
                        img_bgr,
                        det_res["landmarks_list"],
                        gaze_info=gaze,
                        pose_info=pose,
                        auxiliary_persons=det_res.get("auxiliary_persons", []),
                    )
                    st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), use_container_width=True)

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Persons", f"{face_count}")
                    m2.metric("Gaze", gaze["direction"].upper() if gaze else "N/A")
                    m3.metric("Head Pose", f"Y: {pose['yaw']:+.1f}° | P: {pose['pitch']:+.1f}°" if pose and pose.get("yaw") is not None else "N/A")

                    # Record frame
                    st.session_state["mode_results"]["webcam"]["live_frames"].append({
                        "time_sec": round(len(st.session_state["mode_results"]["webcam"]["live_frames"]) * 1.0, 1),
                        "faces": face_count,
                        "yaw": pose["yaw"] if pose else None,
                        "pitch": pose["pitch"] if pose else None,
                        "gaze_h_ratio": gaze["horizontal_ratio"] if gaze else None,
                        "gaze_v_ratio": gaze["vertical_ratio"] if gaze else None,
                        "gaze_direction": gaze["direction"] if gaze else "n/a",
                        "conditions": conds,
                        "details": details,
                        "flags": ",".join([k for k, v in conds.items() if v]) or "-",
                    })
                    st.session_state["mode_results"]["webcam"]["result"] = rescore_telemetry(st.session_state["mode_results"]["webcam"]["live_frames"])
                    st.session_state["mode_results"]["webcam"]["source_name"] = "Live Webcam Snapshot"
                    st.session_state["mode_results"]["webcam"]["duration"] = round(len(st.session_state["mode_results"]["webcam"]["live_frames"]) * 1.0, 1)

        with cam_tab2:
            st.markdown("##### Timed Session Recording")
            rec_sec = st.select_slider("Session Duration", options=[10, 15, 20, 30], value=10, format_func=lambda s: f"{s} s")
            if st.button("Start Timed Recording", type="primary"):
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(0)

                if not cap.isOpened():
                    st.error("Unable to access local camera device.")
                else:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    for _ in range(5):
                        cap.read()

                    stream_box = st.empty()
                    p_bar = st.progress(0.0)
                    rec_frames = []
                    start_t = time.time()
                    last_ui = 0.0

                    while (time.time() - start_t) < rec_sec:
                        now = time.time()
                        ret, frame = cap.read()
                        if not ret:
                            break
                        rec_frames.append(frame)

                        if now - last_ui >= 0.15:
                            last_ui = now
                            disp = cv2.resize(frame, (320, 240))
                            cv2.putText(disp, f"REC {int(rec_sec - (now - start_t))}s", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            stream_box.image(cv2.cvtColor(disp, cv2.COLOR_BGR2RGB), use_container_width=True)
                            p_bar.progress(min(1.0, (now - start_t) / rec_sec))

                    cap.release()
                    total_dur = time.time() - start_t
                    exact_fps = max(10.0, len(rec_frames) / max(0.1, total_dur))

                    tmp_vid = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                    tmp_vid_path = tmp_vid.name
                    tmp_vid.close()

                    writer = cv2.VideoWriter(tmp_vid_path, cv2.VideoWriter_fourcc(*"mp4v"), round(exact_fps), (640, 480))
                    for f in rec_frames:
                        writer.write(cv2.resize(f, (640, 480)))
                    writer.release()

                    with st.spinner("Analyzing recorded frames..."):
                        res = process_video(tmp_vid_path, debug=True)
                        st.session_state["mode_results"]["webcam"]["result"] = res
                        st.session_state["mode_results"]["webcam"]["uploaded_path"] = tmp_vid_path
                        st.session_state["mode_results"]["webcam"]["source_name"] = f"Live Proctoring ({rec_sec}s).mp4"
                        st.session_state["mode_results"]["webcam"]["duration"] = res["video_duration_sec"]
                    st.rerun()


# ---------------------------------------------------------------------------
# Empty State Guard (Audit Section 5)
# ---------------------------------------------------------------------------
if not has_data:
    with st.container(border=True):
        st.markdown(f"""
        <div style="text-align: center; padding: 2.5rem 1rem;">
            <div style="font-size: 2.8rem; margin-bottom: 0.5rem;">📂</div>
            <h3 style="margin-bottom: 0.3rem;">No Analysis Data Available</h3>
            <p style="color: #64748B; font-size: 0.95rem; max-width: 480px; margin: 0 auto 1.2rem auto;">
                {"Select or drop your exam video file in the upload card above and click 'Run Video AI Analysis' to begin." if current_mode == "video" else "Capture a live snapshot or start a timed recording session above."}
            </p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()


# ---------------------------------------------------------------------------
# Main Tabs (5 Functional Tabs per Audit Item 3.3)
# ---------------------------------------------------------------------------
tab_overview, tab_inspector, tab_analytics, tab_audit, tab_certificate = st.tabs([
    "Executive Overview",
    "Video & Event Inspector",
    "Behavioral Analytics",
    "Activity Audit Log",
    "Official Audit Certificate",
])

score = active_result["risk_score"]
level = active_result["risk_level"]
events = active_result.get("events", [])
activity_log = active_result.get("activity_log", [])
debug_frames = active_result.get("debug_frames", [])
duration_sec = active_result.get("video_duration_sec", 0.0)


# ===========================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ===========================================================================
with tab_overview:
    col_gauge, col_verdict = st.columns([1.1, 1.9])

    with col_gauge:
        with st.container(border=True):
            st.plotly_chart(render_risk_gauge(score, level), use_container_width=True, config={"displayModeBar": False})
            st.markdown("""
            <div style="display: flex; justify-content: space-around; align-items: center; margin-top: -14px; margin-bottom: 6px; font-size: 0.78rem; font-weight: 600;">
                <span style="color: #2E8B57;">● Low (0–25)</span>
                <span style="color: #E0A100;">● Medium (25–60)</span>
                <span style="color: #C0392B;">● High (60–100)</span>
            </div>
            """, unsafe_allow_html=True)
            st.caption("Score of 60 and above indicates High Risk.")

    with col_verdict:
        with st.container(border=True):
            l1_events = [e for e in events if not e['type'].startswith('frequent_') and e['type'] != 'multiple_faces']
            l2_events = [e for e in events if e['type'].startswith('frequent_')]
            l3_events = [e for e in events if e['type'] == 'multiple_faces']

            l1_pts = sum(e.get("weight", 0) for e in l1_events)
            l2_pts = sum(e.get("weight", 0) for e in l2_events)
            l3_pts = sum(e.get("weight", 0) for e in l3_events)

            # Generate evidence-grounded verdict text (Audit Item B4)
            if not events:
                verdict_title = f"Low Risk · {score} / 100"
                verdict_desc = "Candidate demonstrated normal exam focus. No infractions confirmed."
                banner_class = "verdict-low"
            else:
                phrases = []
                if l3_pts > 0:
                    phrases.append(f"{len(l3_events)} multi-person event(s)")
                if l1_pts > 0:
                    phrases.append(f"{len(l1_events)} sustained movement event(s)")
                if l2_pts > 0:
                    phrases.append(f"{len(l2_events)} repeated cluster(s)")
                summary_phrase = ", ".join(phrases)

                if level == "High":
                    verdict_title = f"High Risk · {score} / 100"
                    verdict_desc = f"Critical infractions flagged: {summary_phrase}. Proctor review required."
                    banner_class = "verdict-high"
                elif level == "Medium":
                    verdict_title = f"Moderate Risk · {score} / 100"
                    verdict_desc = f"Advisory infractions flagged: {summary_phrase}. Timestamps should be audited."
                    banner_class = "verdict-med"
                else:
                    verdict_title = f"Low Risk · {score} / 100"
                    verdict_desc = f"Minor movement flagged ({summary_phrase}), within tolerance."
                    banner_class = "verdict-low"

            st.markdown(f"""
            <div class="{banner_class}">
                <h3 style="margin: 0 0 4px 0; font-size: 1.15rem;">{verdict_title}</h3>
                <p style="margin: 0; font-size: 0.92rem; line-height: 1.4;">{verdict_desc}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Session Time", f"{duration_sec:.1f} s", help="Total analyzed video session length.")
            kpi2.metric("Confirmed Events", f"{len(events)}", help="Confirmed = verified violations meeting duration or recurrence rules.")
            kpi3.metric("Flagged Moments", f"{len(activity_log)}", help="Flagged = candidate frames flagged for review by the engine.")

    # 3-Layer Scoring Breakdown + Categories Breakdown
    col_breakdown, col_cat = st.columns([1.6, 1.4])

    with col_breakdown:
        with st.container(border=True):
            st.markdown("#### Scoring Breakdown")
            st.caption("Score traces directly to rule weights: Layer 1 + Layer 2 + Layer 3.")

            b1, b2, b3 = st.columns(3)
            # Neutral formatting for 0 (Audit Item B5)
            b1.metric("Layer 1: Sustained", f"+{l1_pts} pts", f"{len(l1_events)} events (sustained)" if l1_events else "0 events", delta_color="inverse" if l1_pts > 0 else "off")
            b2.metric("Layer 2: Frequency", f"+{l2_pts} pts", f"{len(l2_events)} clusters (≥{FREQUENCY_MIN_COUNT} in {int(FREQUENCY_WINDOW_SEC)}s)" if l2_events else f"0 clusters (≥{FREQUENCY_MIN_COUNT} in {int(FREQUENCY_WINDOW_SEC)}s)", delta_color="inverse" if l2_pts > 0 else "off")
            b3.metric("Layer 3: Immediate", f"+{l3_pts} pts", f"{len(l3_events)} flags" if l3_events else "0 flags", delta_color="inverse" if l3_pts > 0 else "off")

            if events:
                ev_df = build_events_dataframe(active_result)
                ev_df = ev_df.rename(columns={
                    "type": "Type",
                    "start_time": "Start",
                    "end_time": "End",
                    "duration_sec": "Duration (s)",
                    "weight": "Weight",
                    "note": "Note",
                })
                try:
                    st.dataframe(ev_df, hide_index=True, use_container_width=True, height=170)
                except Exception:
                    st.table(ev_df)
            else:
                st.info("No infractions confirmed in this session.")

    with col_cat:
        with st.container(border=True):
            st.markdown("#### Violation Categories")
            st.caption("Distribution of confirmed events across behavioral domains.")
            st.plotly_chart(render_violation_breakdown(events), use_container_width=True, config={"displayModeBar": False})


# ===========================================================================
# TAB 2: VIDEO & EVENT INSPECTOR
# ===========================================================================
with tab_inspector:
    with st.container(border=True):
        st.markdown("#### Event Timeline")
        st.caption("Gantt timeline relative to total session duration.")
        st.plotly_chart(render_timeline_chart(events, duration_sec), use_container_width=True, config={"displayModeBar": False})

    # Filter by violation type (Audit Item B7 - hidden if <= 1 type)
    unique_types = sorted(list({e['type'] for e in events})) if events else []
    selected_filter = "ALL"
    if len(unique_types) > 1:
        filter_opts = ["ALL"] + unique_types
        selected_filter = st.radio(
            "Filter Events by Type:",
            filter_opts,
            horizontal=True,
            format_func=lambda x: "All Types" if x == "ALL" else _pretty_type(x),
        )

    filtered_events = events if selected_filter == "ALL" else [e for e in events if e['type'] == selected_filter]

    # Two-Column Layout: Video Left (60%), Event Cards Right (40%) (Audit Item 4.2)
    col_media, col_cards = st.columns([1.5, 1.0])

    jump_time = st.session_state.get("jump_timestamp", 0.0)

    with col_media:
        with st.container(border=True):
            st.markdown("##### Synchronized Playback & Telemetry")
            media_path = active_store.get("uploaded_path")

            if media_path and os.path.exists(media_path):
                st.video(media_path, start_time=int(jump_time))
                st.caption(f"Playback positioned at {format_timestamp(jump_time)} ({jump_time:.1f} s)")
            else:
                # Telemetry Inspector for Scenarios / Snapshots
                matching_frame = None
                if debug_frames:
                    for f in debug_frames:
                        if abs(f["time_sec"] - jump_time) <= 0.6:
                            matching_frame = f
                            break
                    if not matching_frame:
                        matching_frame = debug_frames[0]

                if matching_frame:
                    t_time = matching_frame.get('time_sec', 0.0)
                    t_faces = matching_frame.get('faces', 1)
                    t_gaze = matching_frame.get('gaze_direction', 'center').upper()
                    t_yaw = matching_frame.get('yaw', 0.0) or 0.0
                    t_pitch = matching_frame.get('pitch', 0.0) or 0.0

                    st.markdown(f"""
                    <div style="background:#F8FAFC; border:1px solid #CBD5E1; border-radius:8px; padding:1.2rem; text-align:center;">
                        <div style="font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;">
                            Telemetry Snapshot at {t_time:.1f} s
                        </div>
                        <div style="font-size:1.8rem; margin:0.3rem 0; font-weight:800; color:#12203A;">
                            {'👤 1 Person' if t_faces == 1 else (f'👥 {t_faces} Persons' if t_faces > 1 else '❓ No Face')}
                        </div>
                        <div style="display:flex; justify-content:center; gap:16px; margin-top:0.8rem;">
                            <div><span style="font-size:0.75rem; color:#64748B;">Gaze</span><br><strong>{t_gaze}</strong></div>
                            <div><span style="font-size:0.75rem; color:#64748B;">Yaw</span><br><strong>{t_yaw:.1f}°</strong></div>
                            <div><span style="font-size:0.75rem; color:#64748B;">Pitch</span><br><strong>{t_pitch:.1f}°</strong></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("No video or telemetry frames available to seek.")

    with col_cards:
        with st.container(border=True):
            st.markdown("##### Flagged Event Cues")
            if not filtered_events:
                st.caption("No confirmed events matching selection.")
            else:
                for idx, e in enumerate(filtered_events):
                    orig_idx = events.index(e)
                    is_selected = (st.session_state.get("selected_event_idx") == orig_idx)
                    card_class = "cue-card-selected" if is_selected else ""

                    st.markdown(f"""
                    <div class="cue-card {card_class}">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>#{orig_idx+1} {_pretty_type(e['type'])}</strong>
                            <span style="color:#C0392B; font-weight:700; font-size:0.82rem;">+{e.get('weight', 0)} pts</span>
                        </div>
                        <div style="font-size:0.82rem; color:#64748B; margin:3px 0;">
                            {format_timestamp(e['start_sec'])} – {format_timestamp(e['end_sec'])} ({e['duration_sec']:.1f} s)
                        </div>
                        <div style="font-size:0.8rem; color:#4A5568;"><em>{e.get('note', 'sustained')}</em></div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"Jump to {format_timestamp(e['start_sec'])}", key=f"btn_jump_{orig_idx}", use_container_width=True):
                        st.session_state["selected_event_idx"] = orig_idx
                        st.session_state["jump_timestamp"] = e["start_sec"]
                        st.rerun()


# ===========================================================================
# TAB 3: BEHAVIORAL ANALYTICS
# ===========================================================================
with tab_analytics:
    with st.container(border=True):
        st.markdown("#### Temporal Flag Density")
        st.caption("Discrete counts of suspicious candidate frames per 2-second window.")
        st.plotly_chart(render_flag_density_chart(activity_log, duration_sec), use_container_width=True, config={"displayModeBar": False})

    col_geo, col_gaze = st.columns(2)

    with col_geo:
        with st.container(border=True):
            st.markdown("#### Head Pose Geometry")
            st.caption(f"Distribution of yaw vs. pitch. Permissible boundary at ±{YAW_THRESHOLD:.0f}° yaw and +{PITCH_DOWN_THRESHOLD:.0f}° pitch.")
            st.plotly_chart(render_pose_scatter(debug_frames, yaw_thresh=YAW_THRESHOLD, pitch_thresh=PITCH_DOWN_THRESHOLD), use_container_width=True, config={"displayModeBar": False})

    with col_gaze:
        with st.container(border=True):
            st.markdown("#### Gaze Ratio Distribution")
            st.caption("Horizontal and vertical iris position ratios. 0.5 indicates centered gaze.")
            st.plotly_chart(render_gaze_distribution(debug_frames), use_container_width=True, config={"displayModeBar": False})


# ===========================================================================
# TAB 4: ACTIVITY AUDIT LOG
# ===========================================================================
with tab_audit:
    with st.container(border=True):
        st.markdown("#### Complete Activity Stream")
        st.caption("Frame-by-frame log of all suspicious movements, including brief sub-threshold glances.")

        activity_df = build_activity_log_dataframe(active_result)
        if not activity_df.empty:
            f_col1, f_col2 = st.columns([1.2, 1.8])
            with f_col1:
                types_in_log = ["All"] + sorted(list(activity_df["type"].unique()))
                chosen_log_type = st.selectbox("Filter by Category", types_in_log)
            with f_col2:
                q = st.text_input("Search Detail (e.g. 'turned', 'faces')", "")

            f_df = activity_df.copy()
            if chosen_log_type != "All":
                f_df = f_df[f_df["type"] == chosen_log_type]
            if q:
                f_df = f_df[f_df["detail"].str.contains(q, case=False, na=False)]

            f_df = f_df.rename(columns={"time": "Timestamp", "type": "Violation Type", "detail": "Detail"})
            try:
                st.dataframe(f_df, hide_index=True, use_container_width=True, height=300)
            except Exception:
                st.table(f_df)
            st.caption(f"Showing {len(f_df)} of {len(activity_df)} logged moments.")

            st.markdown("---")
            d1, d2 = st.columns(2)
            summary_txt = build_summary_text(active_result, active_store.get("source_name", "session"))
            d1.download_button("Download Summary Report (.txt)", data=summary_txt, file_name="audit_summary.txt", mime="text/plain", use_container_width=True)
            d2.download_button("Download Activity Log (.csv)", data=activity_df.to_csv(index=False), file_name="activity_stream.csv", mime="text/csv", use_container_width=True)
        else:
            st.success("No suspicious moments logged in this session.")


# ===========================================================================
# TAB 5: OFFICIAL AUDIT CERTIFICATE
# ===========================================================================
with tab_certificate:
    with st.container(border=True):
        st.markdown("#### Institutional Audit Certificate")
        st.caption("Printable formal verification report for examination records.")

        with st.expander("Edit Candidate Details", expanded=False):
            e1, e2 = st.columns(2)
            st.session_state["candidate_meta"]["candidate_name"] = e1.text_input("Candidate Name", st.session_state["candidate_meta"]["candidate_name"])
            st.session_state["candidate_meta"]["candidate_id"] = e1.text_input("Registration ID", st.session_state["candidate_meta"]["candidate_id"])
            st.session_state["candidate_meta"]["exam_title"] = e1.text_input("Exam Title", st.session_state["candidate_meta"]["exam_title"])
            st.session_state["candidate_meta"]["evaluator_name"] = e2.text_input("Evaluator Name", st.session_state["candidate_meta"]["evaluator_name"])
            st.session_state["candidate_meta"]["institution"] = e2.text_input("Institution", st.session_state["candidate_meta"]["institution"])

        html_cert = build_html_printable_report(
            active_result,
            session_meta={
                **st.session_state["candidate_meta"],
                "source_name": active_store.get("source_name", "session"),
            }
        )

        st.download_button(
            "Download Printable Certificate (.html)",
            data=html_cert,
            file_name=f"Certificate_{st.session_state['candidate_meta']['candidate_id']}.html",
            mime="text/html",
            use_container_width=True,
            type="primary",
        )
        st.caption("Open the downloaded file in your browser and press Ctrl+P to save as PDF.")
        st.markdown("---")
        st.components.v1.html(html_cert, height=700, scrolling=True)
