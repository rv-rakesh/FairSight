"""
visualizations.py
-----------------
Interactive Plotly charts for the AI Malpractice Detection Dashboard:
- render_risk_gauge: Semicircular cheating-risk speedometer with explicit zone bands
- render_timeline_chart: Gantt-style horizontal violation timeline with session track
- render_flag_density_chart: Discrete bar chart of temporal violation clustering
- render_pose_scatter: Head pose geometry scatter (Yaw vs Pitch with safety boundary)
- render_violation_breakdown: Horizontal bar breakdown of confirmed violation categories
- render_gaze_distribution: Gaze ratio distribution with shaded normal boundaries
"""

import plotly.graph_objects as go
import pandas as pd
import numpy as np


def render_risk_gauge(score, level):
    """Renders a clean semi-circular risk gauge with clear zone bands (zero text collisions)."""
    color_map = {
        'Low': '#2E8B57',
        'Medium': '#E0A100',
        'High': '#C0392B',
    }
    bar_color = color_map.get(level, '#0F7C8A')

    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=score,
        number={'suffix': ' / 100', 'font': {'size': 32, 'color': bar_color, 'family': 'Inter, sans-serif'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1.5, 'tickcolor': '#CBD5E1', 'nticks': 6},
            'bar': {'color': bar_color, 'thickness': 0.35},
            'bgcolor': 'white',
            'borderwidth': 1,
            'bordercolor': '#E2E8F0',
            'steps': [
                {'range': [0, 25], 'color': 'rgba(46, 139, 87, 0.20)'},
                {'range': [25, 60], 'color': 'rgba(224, 161, 0, 0.22)'},
                {'range': [60, 100], 'color': 'rgba(192, 57, 43, 0.25)'},
            ],
            'threshold': {
                'line': {'color': '#C0392B', 'width': 3},
                'thickness': 0.8,
                'value': 60,
            },
        },
        domain={'x': [0.02, 0.98], 'y': [0.12, 1.0]}
    ))

    fig.update_layout(
        height=195,
        margin=dict(l=20, r=20, t=15, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif'),
    )
    return fig


def render_timeline_chart(events, video_duration):
    """Renders a horizontal Gantt-style timeline of confirmed events with full session track."""
    fig = go.Figure()

    max_x = max(video_duration, max((e['start_sec'] + e.get('duration_sec', 0)) for e in events) + 2) if events else max(video_duration, 10)

    if not events:
        fig.add_annotation(
            text='<b>✓ No confirmed suspicious events across session timeline</b>',
            xref='paper', yref='paper',
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color='#2E8B57'),
        )
        fig.update_layout(
            height=140,
            xaxis=dict(range=[0, max_x], title=dict(text='Session time (seconds)', font=dict(size=12, color='#64748B')), showgrid=True),
            yaxis=dict(showticklabels=False, showgrid=False),
            margin=dict(l=140, r=25, t=15, b=35),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(244, 250, 249, 0.5)',
        )
        return fig

    color_palette = {
        'multiple_faces': '#C0392B',
        'head_turned': '#E67E22',
        'gaze_away': '#F39C12',
        'frequent_gaze_away': '#8E44AD',
        'frequent_head_turned': '#9B59B6',
        'no_face': '#2980B9',
    }

    y_categories = sorted(list({e['type'].replace('_', ' ').title() for e in events}))

    # Light grey background track for each category
    for cat in y_categories:
        fig.add_trace(go.Bar(
            y=[cat],
            x=[max_x],
            base=[0],
            orientation='h',
            marker=dict(color='#F1F5F9', line=dict(width=0)),
            hoverinfo='skip',
            showlegend=False,
        ))

    # Actual event bars
    for e in events:
        e_type = e['type']
        pretty_type = e_type.replace('_', ' ').title()
        color = color_palette.get(e_type, '#0F7C8A')
        start = e['start_sec']
        duration = max(0.4, e.get('duration_sec', 0.5))
        note = e.get('note', 'sustained')

        hover_info = (
            f"<b>{pretty_type}</b><br>"
            f"Interval: {start:.1f}s – {start+duration:.1f}s ({duration:.1f}s)<br>"
            f"Severity Weight: +{e.get('weight', 0)} pts<br>"
            f"Note: {note}"
        )

        fig.add_trace(go.Bar(
            y=[pretty_type],
            x=[duration],
            base=[start],
            orientation='h',
            marker=dict(color=color, opacity=0.9, line=dict(color='#FFFFFF', width=1.5)),
            name=pretty_type,
            hovertemplate=hover_info + '<extra></extra>',
            showlegend=False,
        ))

    fig.update_layout(
        height=max(160, len(y_categories) * 45 + 60),
        xaxis=dict(range=[0, max_x], title=dict(text='Session time (seconds)', font=dict(size=12, color='#64748B')), showgrid=True, gridcolor='#E2E8F0', dtick=5),
        yaxis=dict(categoryorder='array', categoryarray=y_categories, title='', tickfont=dict(size=12, color='#12203A')),
        margin=dict(l=140, r=25, t=15, b=35),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
        barmode='overlay',
    )
    return fig


def render_flag_density_chart(activity_log, video_duration, bin_size=2.0):
    """Renders discrete bar chart of temporal violation clustering (replaces smoothed spline)."""
    fig = go.Figure()

    if not activity_log:
        fig.add_annotation(
            text='<b>✓ Zero suspicious moments logged in activity stream</b>',
            xref='paper', yref='paper',
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color='#2E8B57'),
        )
        fig.update_layout(
            height=190,
            xaxis=dict(range=[0, max(video_duration, 10)], title=dict(text='Session time (seconds)', font=dict(size=12, color='#64748B'))),
            yaxis=dict(title=dict(text='Flags per 2s window', font=dict(size=12, color='#64748B')), showgrid=True),
            margin=dict(l=45, r=20, t=15, b=35),
            paper_bgcolor='rgba(0,0,0,0)',
        )
        return fig

    max_time = max(video_duration, max(a['time_sec'] for a in activity_log) + 1.0)
    bins = np.arange(0, max_time + bin_size, bin_size)
    times = [a['time_sec'] for a in activity_log]
    counts, bin_edges = np.histogram(times, bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    fig.add_trace(go.Bar(
        x=bin_centers,
        y=counts,
        marker=dict(color='#0F7C8A', opacity=0.85, line=dict(color='#026572', width=1)),
        name='Flags',
        hovertemplate='Time: %{x:.1f}s<br>Flags: %{y}<extra></extra>',
    ))

    fig.update_layout(
        height=190,
        xaxis=dict(title=dict(text='Session time (seconds)', font=dict(size=12, color='#64748B')), showgrid=True, gridcolor='#E2E8F0', range=[0, max_time]),
        yaxis=dict(title=dict(text='Flags per 2s window', font=dict(size=12, color='#64748B')), showgrid=True, gridcolor='#E2E8F0', dtick=1),
        margin=dict(l=45, r=20, t=15, b=35),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
    )
    return fig


def render_pose_scatter(debug_frames, yaw_thresh=26.0, pitch_thresh=26.0):
    """Renders 2D scatter of Yaw vs Pitch angles with permissible boundary box and clean layout."""
    fig = go.Figure()

    valid_frames = [f for f in (debug_frames or []) if f.get('yaw') is not None and f.get('pitch') is not None]

    if not valid_frames:
        fig.add_annotation(
            text='<b>No head pose telemetry available for this session</b>',
            xref='paper', yref='paper',
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color='#64748B'),
        )
        fig.update_layout(height=280, margin=dict(l=30, r=30, t=30, b=30), paper_bgcolor='rgba(0,0,0,0)')
        return fig

    yaws = [f['yaw'] for f in valid_frames]
    pitches = [f['pitch'] for f in valid_frames]
    times = [f['time_sec'] for f in valid_frames]

    is_flagged = [abs(y) > yaw_thresh or p > pitch_thresh for y, p in zip(yaws, pitches)]

    normal_x = [y for y, flag in zip(yaws, is_flagged) if not flag]
    normal_y = [p for p, flag in zip(pitches, is_flagged) if not flag]
    normal_t = [t for t, flag in zip(times, is_flagged) if not flag]

    flag_x = [y for y, flag in zip(yaws, is_flagged) if flag]
    flag_y = [p for p, flag in zip(pitches, is_flagged) if flag]
    flag_t = [t for t, flag in zip(times, is_flagged) if flag]

    # Permissible safe zone rectangle (±26° yaw, -14° to +26° pitch)
    fig.add_shape(
        type='rect',
        x0=-yaw_thresh, x1=yaw_thresh,
        y0=-14, y1=pitch_thresh,
        fillcolor='rgba(46, 139, 87, 0.08)',
        line=dict(color='#2E8B57', width=1.5, dash='dash'),
    )
    # Zone label positioned above box to prevent data point overlap
    fig.add_annotation(
        x=0, y=pitch_thresh + 4,
        text='Normal Head Motion Zone (±26° Yaw, +26° Pitch)',
        showarrow=False,
        font=dict(size=10.5, color='#2E8B57', family='Inter, sans-serif'),
    )

    if normal_x:
        fig.add_trace(go.Scatter(
            x=normal_x, y=normal_y,
            mode='markers',
            marker=dict(color='#0F7C8A', size=6, opacity=0.65),
            name='Normal Pose',
            customdata=normal_t,
            hovertemplate='Time: %{customdata:.1f}s<br>Yaw: %{x:.1f}°<br>Pitch: %{y:.1f}°<extra>Normal</extra>',
        ))

    if flag_x:
        fig.add_trace(go.Scatter(
            x=flag_x, y=flag_y,
            mode='markers',
            marker=dict(color='#C0392B', size=8, symbol='diamond', opacity=0.9),
            name='Turn/Tilt Flag',
            customdata=flag_t,
            hovertemplate='Time: %{customdata:.1f}s<br>Yaw: %{x:.1f}°<br>Pitch: %{y:.1f}°<extra>FLAGGED</extra>',
        ))

    fig.update_layout(
        height=280,
        xaxis=dict(title=dict(text='Yaw (°)', font=dict(size=12, color='#64748B')), range=[-60, 60], zeroline=True, zerolinecolor='#CBD5E1', gridcolor='#F1F5F9'),
        yaxis=dict(title=dict(text='Pitch (°)', font=dict(size=12, color='#64748B')), range=[-30, 60], zeroline=True, zerolinecolor='#CBD5E1', gridcolor='#F1F5F9'),
        margin=dict(l=40, r=20, t=25, b=45),
        legend=dict(orientation='h', yanchor='top', y=-0.22, xanchor='center', x=0.5, font=dict(size=11)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
    )
    return fig


def render_violation_breakdown(events):
    """Renders clean horizontal bar chart of violation categories (replaces single-slice donut)."""
    fig = go.Figure()

    if not events:
        fig.add_annotation(
            text='<b>✓ Zero Confirmed Infractions</b>',
            xref='paper', yref='paper',
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color='#2E8B57'),
        )
        fig.update_layout(height=180, margin=dict(l=15, r=15, t=15, b=15), paper_bgcolor='rgba(0,0,0,0)')
        return fig

    types = [e['type'].replace('_', ' ').title() for e in events]
    counts = pd.Series(types).value_counts().reset_index()
    counts.columns = ['Category', 'Count']

    color_map = {
        'Multiple Faces': '#C0392B',
        'Head Turned': '#E67E22',
        'Gaze Away': '#F39C12',
        'Frequent Gaze Away': '#8E44AD',
        'Frequent Head Turned': '#9B59B6',
        'No Face': '#2980B9',
    }
    bar_colors = [color_map.get(c, '#0F7C8A') for c in counts['Category']]

    fig.add_trace(go.Bar(
        y=counts['Category'],
        x=counts['Count'],
        orientation='h',
        marker=dict(color=bar_colors, opacity=0.9),
        text=counts['Count'],
        textposition='auto',
        hovertemplate='<b>%{y}</b>: %{x} events<extra></extra>',
    ))

    fig.update_layout(
        height=max(140, len(counts) * 38 + 45),
        xaxis=dict(title=dict(text='Count', font=dict(size=11, color='#64748B')), showgrid=True, gridcolor='#E2E8F0', dtick=1),
        yaxis=dict(title='', tickfont=dict(size=12, color='#12203A')),
        margin=dict(l=110, r=20, t=15, b=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
    )
    return fig


def render_gaze_distribution(debug_frames):
    """Renders two clean histograms for Horizontal and Vertical gaze ratios with normal zones."""
    fig = go.Figure()
    valid_gaze = [f for f in (debug_frames or []) if f.get("gaze_h_ratio") is not None and f.get("gaze_v_ratio") is not None]

    if not valid_gaze:
        fig.add_annotation(
            text='<b>No numeric gaze telemetry recorded</b>',
            xref='paper', yref='paper',
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color='#64748B'),
        )
        fig.update_layout(height=280, margin=dict(l=30, r=30, t=30, b=30), paper_bgcolor='rgba(0,0,0,0)')
        return fig

    gh_vals = [f["gaze_h_ratio"] for f in valid_gaze]
    gv_vals = [f["gaze_v_ratio"] for f in valid_gaze]

    # Shaded normal boundary bars
    fig.add_trace(go.Histogram(
        x=gh_vals,
        name='Horizontal Ratio',
        marker=dict(color='#0F7C8A', opacity=0.7),
        xbins=dict(start=0.0, end=1.0, size=0.05),
        hovertemplate='Horiz Ratio: %{x:.2f}<br>Frames: %{y}<extra></extra>',
    ))
    fig.add_trace(go.Histogram(
        x=gv_vals,
        name='Vertical Ratio',
        marker=dict(color='#E0A100', opacity=0.7),
        xbins=dict(start=0.0, end=1.0, size=0.05),
        hovertemplate='Vert Ratio: %{x:.2f}<br>Frames: %{y}<extra></extra>',
    ))

    # Reference lines for normal zone
    fig.add_vline(x=0.35, line_dash="dash", line_color="#2E8B57", annotation_text="Center Min (0.35)", annotation_font_size=9)
    fig.add_vline(x=0.65, line_dash="dash", line_color="#2E8B57", annotation_text="Center Max (0.65)", annotation_font_size=9)

    fig.update_layout(
        height=280,
        barmode='overlay',
        xaxis=dict(title=dict(text='Iris Position Ratio (0.5 = Centered)', font=dict(size=12, color='#64748B')), range=[0.0, 1.0], showgrid=True),
        yaxis=dict(title=dict(text='Sampled Frames', font=dict(size=12, color='#64748B')), showgrid=True, gridcolor='#E2E8F0'),
        margin=dict(l=45, r=20, t=25, b=45),
        legend=dict(orientation='h', yanchor='top', y=-0.22, xanchor='center', x=0.5, font=dict(size=11)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#FFFFFF',
    )
    return fig


# Backward-compatible alias
render_violation_donut = render_violation_breakdown
