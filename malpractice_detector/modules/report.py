"""
report.py
Turns a pipeline result dict into a human-readable report (text + CSV export)
for evaluators, per Phase 5 of the project plan.

Two levels of detail, matching the two layers in scoring.py:
  - "events": confirmed events (sustained + frequency-pattern) that
    contributed to the risk score.
  - "activity_log": EVERY suspicious moment detected, regardless of
    whether it was long/frequent enough to be a confirmed event — full
    transparency, exact timestamp for every flagged frame.
"""

import os
import html
import pandas as pd
from datetime import datetime


def format_timestamp(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _pretty_type(type_name):
    if type_name.startswith("frequent_"):
        return "Frequent " + type_name[len("frequent_"):].replace("_", " ").title()
    return type_name.replace("_", " ").title()


def build_summary_text(result, video_name="video"):
    lines = []
    lines.append("Cheating-Risk Analysis Report")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Source video: {video_name}")
    lines.append(f"Video duration analysed: {format_timestamp(result.get('video_duration_sec', result.get('duration_sec', 0)))}")
    lines.append(f"Frames analysed: {result.get('frames_analysed', 0)}")
    lines.append("")
    lines.append(f"RISK SCORE: {result['risk_score']} / 100  ({result['risk_level']})")
    lines.append("")

    if not result["events"]:
        lines.append("No confirmed suspicious events (sustained or repeated pattern) detected.")
    else:
        lines.append(f"Confirmed events ({len(result['events'])}) — these drove the risk score:")
        for e in result["events"]:
            note = f", {e['note']}" if e.get("note") and e["note"] != "sustained" else ""
            lines.append(
                f"  [{format_timestamp(e['start_sec'])} - {format_timestamp(e['end_sec'])}] "
                f"{_pretty_type(e['type'])} "
                f"(duration {e['duration_sec']}s, weight +{e['weight']}{note})"
            )

    activity_log = result.get("activity_log", [])
    lines.append("")
    if activity_log:
        lines.append(f"Full activity timeline ({len(activity_log)} flagged moments, every instance regardless of duration):")
        for a in activity_log:
            detail = f" — {a['detail']}" if a.get("detail") else ""
            lines.append(f"  [{format_timestamp(a['time_sec'])}] {_pretty_type(a['type'])}{detail}")
    else:
        lines.append("No suspicious moments detected at any point in the video.")

    return "\n".join(lines)


def build_events_dataframe(result):
    """Returns a pandas DataFrame of CONFIRMED events (sustained + frequency-pattern),
    suitable for CSV export / display."""
    if not result["events"]:
        return pd.DataFrame(columns=["type", "start_time", "end_time", "duration_sec", "weight", "note"])
    df = pd.DataFrame(result["events"])
    df["type"] = df["type"].apply(_pretty_type)
    df["start_time"] = df["start_sec"].apply(format_timestamp)
    df["end_time"] = df["end_sec"].apply(format_timestamp)
    if "note" not in df.columns:
        df["note"] = ""
    return df[["type", "start_time", "end_time", "duration_sec", "weight", "note"]]


def build_activity_log_dataframe(result):
    """Returns a pandas DataFrame of EVERY flagged moment (not just confirmed
    events), with exact timestamp and detail — for full transparency."""
    activity_log = result.get("activity_log", [])
    if not activity_log:
        return pd.DataFrame(columns=["time", "type", "detail"])
    df = pd.DataFrame(activity_log)
    df["type"] = df["type"].apply(_pretty_type)
    df["time"] = df["time_sec"].apply(format_timestamp)
    return df[["time", "type", "detail"]]


def save_report(result, video_name, output_dir="outputs"):
    """Saves a .txt summary, a confirmed-events .csv, and a full activity-log
    .csv. Returns (txt_path, events_csv_path, activity_csv_path)."""
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_name))[0]

    txt_path = os.path.join(output_dir, f"{base}_report.txt")
    events_csv_path = os.path.join(output_dir, f"{base}_events.csv")
    activity_csv_path = os.path.join(output_dir, f"{base}_activity_log.csv")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(build_summary_text(result, video_name))

    build_events_dataframe(result).to_csv(events_csv_path, index=False)
    build_activity_log_dataframe(result).to_csv(activity_csv_path, index=False)

    return txt_path, events_csv_path, activity_csv_path


def build_html_printable_report(result, session_meta=None):
    """
    Generates a formal, printable HTML Assessment Integrity Audit Report
    complete with institutional branding, candidate metadata, executive verdict,
    flagged event tables, explainability traces, and an invigilator sign-off block.
    Optimized for browser display and direct 1-click 'Save to PDF' / print (@media print).
    """
    meta = {
        "candidate_name": "Candidate / Examinee",
        "candidate_id": "CAND-89412",
        "exam_title": "Standardized Online Examination",
        "department": "Integrity & Assessment Division",
        "institution": "Autonomous Examination Authority",
        "evaluator_name": "Lead Proctor / Behavioral Auditor",
        "session_date": datetime.now().strftime("%B %d, %Y %H:%M:%S"),
        "source_name": "Recorded Session Video",
    }
    if session_meta:
        meta.update({k: html.escape(str(v)) for k, v in session_meta.items() if v is not None})
    meta = {k: html.escape(str(v)) if not (session_meta and k in session_meta) else v for k, v in meta.items()}

    score = int(result.get("risk_score", 0))
    level = html.escape(str(result.get("risk_level", "Low")))
    norm_score = int(result.get("normalized_score", score))
    norm_level = html.escape(str(result.get("normalized_risk_level", level)))
    duration_sec = result.get("video_duration_sec", result.get("duration_sec", 0)) or 0
    duration_str = format_timestamp(duration_sec)
    events = result.get("events", [])
    activity_log = result.get("activity_log", [])

    if level == "Low":
        verdict_badge = "VERIFIED · NO MALPRACTICE DETECTED"
        verdict_color = "#1E8E5A"
        verdict_bg = "#E8F5E9"
        verdict_desc = "Behavioral telemetry aligns with honest examination protocols. No sustained or systematic infractions detected."
    elif level == "Medium":
        verdict_badge = "ATTENTION · MODERATE SUSPICION · MANUAL REVIEW REQUIRED"
        verdict_color = "#B7791F"
        verdict_bg = "#FFF8E1"
        verdict_desc = "Noticeable behavioral anomalies or repeated glancing patterns were detected. Evaluator inspection recommended."
    else:
        verdict_badge = "CRITICAL · HIGH CHEATING RISK · FORMAL AUDIT REQUIRED"
        verdict_color = "#C0392B"
        verdict_bg = "#FFEBEE"
        verdict_desc = "Substantial evidence of exam infractions (sustained glances away, unauthorized head turns, or multiple persons) was captured."

    # Build Events Table Rows
    events_rows = []
    if events:
        for idx, e in enumerate(events, 1):
            note = html.escape(str(e.get("note", "sustained")))
            ev_type = html.escape(_pretty_type(str(e.get("type", "unknown"))))
            start_s = float(e.get("start_sec", 0.0))
            end_s = float(e.get("end_sec", 0.0))
            dur_s = float(e.get("duration_sec", 0.0))
            wt = int(e.get("weight", 0))
            b64_img = e.get("evidence_frame_b64")
            img_cell = f'<img src="data:image/jpeg;base64,{b64_img}" style="max-width:100px; max-height:65px; border-radius:4px; border:1px solid #CBD5E1;" alt="Evidence"/>' if b64_img else '<span style="color:#94A3B8; font-size:11px;">Telemetry Trace</span>'
            events_rows.append(f"""
            <tr>
                <td style="text-align:center; font-weight:600;">{idx}</td>
                <td style="font-weight:600; color:#1E2761;">{ev_type}</td>
                <td style="font-family:monospace;">{format_timestamp(start_s)} – {format_timestamp(end_s)}</td>
                <td style="text-align:right;">{dur_s:.1f}s</td>
                <td style="text-align:right; font-weight:600; color:#C0392B;">+{wt}</td>
                <td style="color:#555;">{note}</td>
                <td style="text-align:center;">{img_cell}</td>
            </tr>
            """)
    else:
        events_rows.append("""
        <tr>
            <td colspan="7" style="text-align:center; padding:18px; color:#1E8E5A; font-weight:500;">
                ✓ No sustained or repeated suspicious events recorded during this session.
            </td>
        </tr>
        """)
    events_html = "".join(events_rows)

    # Build Activity Timeline Sample Rows (up to 25 for print brevity)
    activity_rows = []
    if activity_log:
        sample_log = activity_log[:25]
        for a in sample_log:
            act_time = format_timestamp(float(a.get("time_sec", 0.0)))
            act_type = html.escape(_pretty_type(str(a.get("type", "unknown"))))
            act_det = html.escape(str(a.get("detail", "-")))
            activity_rows.append(f"""
            <tr>
                <td style="font-family:monospace; color:#028090;">{act_time}</td>
                <td style="font-weight:600;">{act_type}</td>
                <td style="color:#444;">{act_det}</td>
            </tr>
            """)
        if len(activity_log) > 25:
            activity_rows.append(f"""
            <tr>
                <td colspan="3" style="text-align:center; color:#777; font-style:italic; padding:8px;">
                    ... and {len(activity_log) - 25} additional frame moments recorded in digital audit log.
                </td>
            </tr>
            """)
    else:
        activity_rows.append("""
        <tr>
            <td colspan="3" style="text-align:center; padding:12px; color:#777;">
                No infractions logged in activity stream.
            </td>
        </tr>
        """)
    activity_html = "".join(activity_rows)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Integrity Audit Report - {meta['candidate_id']}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #1E2761;
            background: #F8FAFC;
            margin: 0;
            padding: 30px;
            line-height: 1.45;
        }}
        .report-page {{
            max-width: 900px;
            margin: 0 auto;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #028090;
            padding-bottom: 18px;
            margin-bottom: 24px;
        }}
        .logo-area h1 {{
            font-size: 20px;
            margin: 0 0 4px 0;
            color: #1E2761;
            letter-spacing: -0.3px;
        }}
        .logo-area p {{
            font-size: 12px;
            color: #64748B;
            margin: 0;
        }}
        .report-badge {{
            text-align: right;
        }}
        .report-badge span {{
            background: #028090;
            color: white;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .report-badge p {{
            font-size: 11px;
            color: #64748B;
            margin: 6px 0 0 0;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px 24px;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 24px;
            font-size: 13px;
        }}
        .meta-item strong {{
            color: #475569;
            display: inline-block;
            width: 130px;
        }}
        .verdict-box {{
            background: {verdict_bg};
            border-left: 5px solid {verdict_color};
            border-radius: 6px;
            padding: 16px 20px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .verdict-info h2 {{
            margin: 0 0 4px 0;
            font-size: 16px;
            color: {verdict_color};
        }}
        .verdict-info p {{
            margin: 0;
            font-size: 13px;
            color: #334155;
        }}
        .score-pill {{
            text-align: center;
            background: #FFFFFF;
            border: 2px solid {verdict_color};
            border-radius: 10px;
            padding: 10px 18px;
            min-width: 140px;
        }}
        .score-pill .num {{
            font-size: 26px;
            font-weight: 800;
            color: {verdict_color};
            line-height: 1;
        }}
        .score-pill .lbl {{
            font-size: 10px;
            font-weight: 700;
            color: #64748B;
            text-transform: uppercase;
            margin-top: 4px;
        }}
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 28px;
        }}
        .stat-card {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px 14px;
            text-align: center;
        }}
        .stat-card .val {{
            font-size: 18px;
            font-weight: 700;
            color: #1E2761;
        }}
        .stat-card .tit {{
            font-size: 11px;
            color: #64748B;
            margin-top: 2px;
        }}
        h3.section-title {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: #1E2761;
            border-bottom: 1px solid #CBD5E1;
            padding-bottom: 6px;
            margin: 28px 0 12px 0;
        }}
        table.audit-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12.5px;
            margin-bottom: 20px;
        }}
        table.audit-table th {{
            background: #F1F5F9;
            color: #334155;
            font-weight: 600;
            text-align: left;
            padding: 8px 10px;
            border-bottom: 2px solid #CBD5E1;
        }}
        table.audit-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #E2E8F0;
        }}
        .sign-off-box {{
            margin-top: 36px;
            border: 1px dashed #94A3B8;
            border-radius: 8px;
            padding: 20px;
            background: #F8FAFC;
        }}
        .sign-options {{
            display: flex;
            gap: 20px;
            font-size: 12.5px;
            margin-bottom: 16px;
        }}
        .sign-options label {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .sig-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 40px;
            margin-top: 30px;
        }}
        .sig-line {{
            border-top: 1px solid #1E2761;
            padding-top: 6px;
            font-size: 11.5px;
            color: #475569;
            text-align: center;
        }}
        .print-toolbar {{
            max-width: 900px;
            margin: 0 auto 16px auto;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }}
        .btn {{
            background: #028090;
            color: #FFFFFF;
            border: none;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
        }}
        .btn:hover {{ background: #026572; }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .report-page {{ border: none; box-shadow: none; padding: 15px; width: 100%; max-width: 100%; }}
            .print-toolbar {{ display: none; }}
            .sign-off-box {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="print-toolbar">
        <button class="btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
    </div>
    <div class="report-page">
        <div class="header">
            <div class="logo-area">
                <h1>🛡️ AI MALPRACTICE AUDIT CERTIFICATE</h1>
                <p>{meta['institution']} · {meta['department']}</p>
            </div>
            <div class="report-badge">
                <span>Official Record</span>
                <p>{meta['session_date']}</p>
            </div>
        </div>

        <div class="meta-grid">
            <div class="meta-item"><strong>Candidate Name:</strong> {meta['candidate_name']}</div>
            <div class="meta-item"><strong>Registration No:</strong> {meta['candidate_id']}</div>
            <div class="meta-item"><strong>Examination:</strong> {meta['exam_title']}</div>
            <div class="meta-item"><strong>Evaluator/Invigilator:</strong> {meta['evaluator_name']}</div>
            <div class="meta-item"><strong>Source Media:</strong> {meta['source_name']}</div>
            <div class="meta-item"><strong>Duration Analysed:</strong> {duration_str} ({result.get('frames_analysed', 0)} frames)</div>
        </div>

        <div class="verdict-box">
            <div class="verdict-info">
                <h2>{verdict_badge}</h2>
                <p>{verdict_desc}</p>
            </div>
            <div class="score-pill">
                <div class="num">{score}</div>
                <div class="lbl">Raw Risk ({level})</div>
                <div class="lbl" style="margin-top:6px; color:#028090;">10m Norm: {norm_score} ({norm_level})</div>
            </div>
        </div>

        <div class="stats-row">
            <div class="stat-card">
                <div class="val">{duration_str}</div>
                <div class="tit">Analyzed Time</div>
            </div>
            <div class="stat-card">
                <div class="val">{len(events)}</div>
                <div class="tit">Confirmed Events</div>
            </div>
            <div class="stat-card">
                <div class="val">{len(activity_log)}</div>
                <div class="tit">Activity Flags</div>
            </div>
            <div class="stat-card">
                <div class="val">{result.get('frames_analysed', 0)}</div>
                <div class="tit">Sampled Frames</div>
            </div>
        </div>

        <h3 class="section-title">I. Confirmed Suspicious Events (Evidence Trace)</h3>
        <table class="audit-table">
            <thead>
                <tr>
                    <th style="width:36px; text-align:center;">#</th>
                    <th>Violation Category</th>
                    <th>Time Interval</th>
                    <th style="text-align:right;">Duration</th>
                    <th style="text-align:right;">Weight</th>
                    <th>Algorithmic Trace / Detection Layer</th>
                    <th style="text-align:center; width:110px;">Evidence Snapshot</th>
                </tr>
            </thead>
            <tbody>
                {events_html}
            </tbody>
        </table>

        <h3 class="section-title">II. High-Frequency Activity Stream (Sample)</h3>
        <table class="audit-table">
            <thead>
                <tr>
                    <th style="width:90px;">Timestamp</th>
                    <th style="width:180px;">Sensor Flag</th>
                    <th>Telemetry Measurement Detail</th>
                </tr>
            </thead>
            <tbody>
                {activity_html}
            </tbody>
        </table>

        <div class="sign-off-box">
            <h3 style="margin:0 0 12px 0; font-size:13px; text-transform:uppercase; color:#1E2761;">
                III. Human-in-the-Loop Evaluator Sign-Off & Recommendation
            </h3>
            <div class="sign-options">
                <label><input type="checkbox"> Exonerated (False Positive / Justified Physical Glance)</label>
                <label><input type="checkbox"> Retest Under Physical Supervision</label>
                <label><input type="checkbox"> Disciplinary Malpractice Action Confirmed</label>
            </div>
            <div style="font-size:12px; color:#64748B; margin-bottom:20px;">
                Evaluator Notes: __________________________________________________________________________________________
            </div>
            <div class="sig-grid">
                <div class="sig-line">Invigilator / Evaluator Signature</div>
                <div class="sig-line">Dean of Academic Examinations / Seal</div>
            </div>
        </div>
    </div>
</body>
</html>"""
    return html_content

