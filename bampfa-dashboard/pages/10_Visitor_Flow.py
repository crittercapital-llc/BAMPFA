"""
pages/10_Visitor_Flow.py
BAMPFA Audience Analytics — Visitor Flow & Dwell Time.

Inspired by Dexibit's guest-flow feature: heatmaps, dwell time, and path
analysis show how visitors move through the building, which galleries capture
the most time, and when peak traffic flows occur throughout the day.

⚠ Gallery visitor counts and dwell times are simulated using transaction totals
  as a base. Replace with sensor/WiFi/indoor-positioning data when available.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Visitor Flow | BAMPFA Analytics",
    page_icon="🗺️",
    layout="wide",
)

st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: 'Inter', 'Helvetica Neue', sans-serif; }
      [data-testid="stSidebar"] { background-color: #0f0f1a; }
      [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
      .page-header { background: linear-gradient(135deg, #1a1a2e, #0f3460);
          padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem; }
      .page-header h2 { color: #e8c99a; margin: 0; font-size: 1.6rem; }
      .page-header p { color: #a0b4c8; margin: 0.3rem 0 0 0; font-size: 0.9rem; }
      .section-header { color: #c8a96e; font-size: 0.75rem; font-weight: 600;
          letter-spacing: 0.12em; text-transform: uppercase;
          border-bottom: 1px solid #2d2d4a; padding-bottom: 0.4rem; margin: 1.5rem 0 1rem 0; }
      .insight-card { background: #1e1e30; border: 1px solid #2d2d4a; border-radius: 8px;
          padding: 1rem; margin-bottom: 0.5rem; }
      #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

@st.cache_resource
def get_agent():
    return DataAgent()

agent = get_agent()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Visitor Flow Filters")
    st.markdown("---")

    year_options = list(range(2022, 2027))
    selected_year = st.selectbox("Year", options=year_options, index=3)

    gallery_options = [
        "G1 (Main Gallery)", "G2 (Modern/Contemporary)", "G3 (Works on Paper)",
        "G4 (Rotating)", "Cinema", "Film Study Center",
    ]
    selected_galleries = st.multiselect(
        "Galleries to Display",
        options=gallery_options,
        default=gallery_options,
    )

    st.markdown("---")
    st.caption(
        "⚠ Gallery-level data is simulated using ticket transaction volumes as a baseline. "
        "Connect indoor-positioning or door-counter feeds for live accuracy."
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>🗺️ Visitor Flow &amp; Dwell Time</h2>
        <p>Understand how visitors move through BAMPFA — which galleries attract the most
           traffic, how long people linger, and when the building is busiest throughout the day.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "⚠️ **Demo Mode:** Gallery traffic and dwell times are modelled from ticket transaction "
    "volume proportions. Connect WiFi, door-counter, or indoor-positioning hardware for "
    "real-time accuracy.",
    icon="📡",
)

# ---------------------------------------------------------------------------
# Load gallery flow data
# ---------------------------------------------------------------------------

flow_df = agent.get_gallery_flow_data()
hourly_df = agent.get_hourly_flow()
dwell_summary = agent.get_dwell_time_summary()

# Filter year and galleries
year_flow = flow_df[
    flow_df["year_month_str"].str.startswith(str(selected_year))
    & flow_df["gallery"].isin(selected_galleries)
].copy()

# ---------------------------------------------------------------------------
# Section 1: Gallery Traffic KPIs
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Gallery Traffic — Year Overview</div>', unsafe_allow_html=True)

if not year_flow.empty:
    gallery_totals = (
        year_flow.groupby("gallery")
        .agg(total_visitors=("visitors", "sum"), avg_dwell=("avg_dwell_minutes", "mean"))
        .reset_index()
        .sort_values("total_visitors", ascending=False)
    )
    total_all = gallery_totals["total_visitors"].sum()
    gallery_totals["share_pct"] = (gallery_totals["total_visitors"] / total_all * 100).round(1)

    kpi_cols = st.columns(min(len(gallery_totals), 6))
    for i, (_, row) in enumerate(gallery_totals.iterrows()):
        if i < 6:
            with kpi_cols[i]:
                st.metric(
                    label=row["gallery"],
                    value=f"{row['total_visitors']:,}",
                    delta=f"{row['share_pct']}% of traffic",
                )

# ---------------------------------------------------------------------------
# Section 2: Gallery Traffic Heatmap (month × gallery)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Gallery Traffic Heatmap — Month × Gallery</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Which galleries are busiest each month? Use this to plan programming, "
    "staffing rotations, and maintenance windows."
)

if not year_flow.empty:
    pivot = year_flow.pivot_table(
        index="gallery",
        columns="year_month_str",
        values="visitors",
        aggfunc="sum",
    ).fillna(0)

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale="YlOrBr",
        labels=dict(x="Month", y="Gallery", color="Visitors"),
        title=f"Visitors by Gallery and Month ({selected_year})",
        template="plotly_dark",
        aspect="auto",
    )
    fig_heat.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(title="Visitors"),
        xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Monthly Gallery Traffic Trend (stacked area)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Gallery Traffic Over Time</div>',
    unsafe_allow_html=True,
)

if not year_flow.empty:
    fig_area = px.area(
        year_flow.sort_values(["year_month_str", "gallery"]),
        x="year_month_str",
        y="visitors",
        color="gallery",
        title=f"Monthly Visitors by Gallery ({selected_year})",
        labels={"year_month_str": "Month", "visitors": "Visitors", "gallery": "Gallery"},
        template="plotly_dark",
    )
    fig_area.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        hovermode="x unified",
        height=360,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(tickangle=30, tickfont=dict(size=10)),
    )
    st.plotly_chart(fig_area, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 4: Dwell Time Analysis
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Dwell Time by Gallery</div>', unsafe_allow_html=True)
st.caption(
    "Average time visitors spend in each gallery. Longer dwell in permanent collection "
    "spaces indicates deeper engagement; short dwell in Cinema reflects scheduled screenings."
)

dwell_filtered = dwell_summary[dwell_summary["gallery"].isin(selected_galleries)]

dwell_col1, dwell_col2 = st.columns([2, 1])

with dwell_col1:
    fig_dwell = go.Figure()
    fig_dwell.add_trace(go.Bar(
        x=dwell_filtered["gallery"],
        y=dwell_filtered["avg_dwell"],
        marker_color=[
            "#c8a96e" if v > dwell_filtered["avg_dwell"].mean() else "#5b8cdb"
            for v in dwell_filtered["avg_dwell"]
        ],
        text=[f"{v:.0f} min" for v in dwell_filtered["avg_dwell"]],
        textposition="outside",
        textfont=dict(color="#e0e0e0", size=11),
    ))
    fig_dwell.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        title="Average Dwell Time per Gallery (minutes)",
        xaxis=dict(tickangle=15, tickfont=dict(size=10)),
        yaxis_title="Minutes",
        height=360,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig_dwell, use_container_width=True)

with dwell_col2:
    st.markdown("**Dwell Time Summary**")
    display_dwell = dwell_filtered[["gallery", "avg_dwell", "total_visitors"]].copy()
    display_dwell.columns = ["Gallery", "Avg Dwell (min)", "Total Visitors"]
    display_dwell["Avg Dwell (min)"] = display_dwell["Avg Dwell (min)"].round(1)
    st.dataframe(display_dwell, use_container_width=True, hide_index=True)

    avg_all = dwell_filtered["avg_dwell"].mean()
    st.metric(
        "Overall Avg Dwell",
        f"{avg_all:.0f} min",
        delta=None,
    )
    best = dwell_filtered.loc[dwell_filtered["avg_dwell"].idxmax(), "gallery"]
    st.metric("Highest Engagement", best, delta=None)

# ---------------------------------------------------------------------------
# Section 5: Hourly Flow Heatmap (day × hour)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Hourly Visitor Flow — Day of Week × Hour</div>',
    unsafe_allow_html=True,
)
st.caption(
    "When does the building peak during the day? Use for scheduling floor staff, "
    "planning docent tours, and optimizing café prep."
)

hourly_pivot = hourly_df.pivot_table(
    index="day",
    columns="hour_label",
    values="avg_visitors",
    aggfunc="sum",
)

day_order = ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
hourly_pivot = hourly_pivot.reindex(
    [d for d in day_order if d in hourly_pivot.index]
)

fig_hourly = px.imshow(
    hourly_pivot,
    color_continuous_scale="Plasma",
    labels=dict(x="Hour of Day", y="Day", color="Avg Visitors"),
    title="Average Visitors by Day of Week and Hour (BAMPFA Open Hours: 11am–7pm)",
    template="plotly_dark",
    aspect="auto",
)
fig_hourly.update_layout(
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    height=280,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_hourly, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 6: Peak hour bar chart
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Peak Hour Distribution</div>', unsafe_allow_html=True)

hourly_totals = (
    hourly_df.groupby("hour_label")["avg_visitors"]
    .mean()
    .reset_index()
    .sort_values("hour_label")
)

fig_peak = px.bar(
    hourly_totals,
    x="hour_label",
    y="avg_visitors",
    labels={"hour_label": "Hour of Day", "avg_visitors": "Avg Visitors"},
    title="Average Visitors per Hour (across all open days)",
    color="avg_visitors",
    color_continuous_scale="YlOrBr",
    template="plotly_dark",
)
fig_peak.update_layout(
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    height=280,
    margin=dict(l=0, r=0, t=40, b=0),
    showlegend=False,
    coloraxis_showscale=False,
)
st.plotly_chart(fig_peak, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 7: Gallery Flow Insights
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Flow Insights &amp; Recommendations</div>', unsafe_allow_html=True)

if not year_flow.empty and not dwell_filtered.empty:
    busiest = gallery_totals.iloc[0]["gallery"]
    quietest = gallery_totals.iloc[-1]["gallery"]
    longest_dwell = dwell_filtered.loc[dwell_filtered["avg_dwell"].idxmax(), "gallery"]
    shortest_dwell = dwell_filtered.loc[dwell_filtered["avg_dwell"].idxmin(), "gallery"]

    peak_day = hourly_df.groupby("day")["avg_visitors"].sum().idxmax()
    peak_hour_row = hourly_df.loc[hourly_df["avg_visitors"].idxmax()]

    ins_col1, ins_col2, ins_col3 = st.columns(3)

    with ins_col1:
        st.markdown(
            f"""
            <div class="insight-card">
                <div style="color:#c8a96e;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.1em;margin-bottom:0.4rem;">Highest Traffic</div>
                <div style="color:#e8c99a;font-size:1.2rem;font-weight:700;">{busiest}</div>
                <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                    Ensure adequate staffing and seating. Consider placing membership
                    desk or café promotions near this space.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with ins_col2:
        st.markdown(
            f"""
            <div class="insight-card">
                <div style="color:#5b8cdb;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.1em;margin-bottom:0.4rem;">Deepest Engagement</div>
                <div style="color:#e8c99a;font-size:1.2rem;font-weight:700;">{longest_dwell}</div>
                <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                    Highest dwell time. Consider programming docent talks, interactive
                    elements, and membership conversion touchpoints here.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with ins_col3:
        st.markdown(
            f"""
            <div class="insight-card">
                <div style="color:#8fd36e;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.1em;margin-bottom:0.4rem;">Daily Peak</div>
                <div style="color:#e8c99a;font-size:1.2rem;font-weight:700;">
                    {peak_day}s at {peak_hour_row['hour_label']}
                </div>
                <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                    Schedule maximum floor staff, café prep, and security coverage
                    around this daily peak window.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Underperforming gallery callout
    st.markdown(
        f"""
        <div style="background:#1e1e30;border:1px solid #2d2d4a;border-left:4px solid #e06c75;
                    border-radius:8px;padding:1rem;margin-top:0.5rem;">
            <strong style="color:#e06c75;">Low-Traffic Alert: {quietest}</strong><br>
            <span style="color:#a0b4c8;font-size:0.88rem;">
                This gallery receives the lowest visitor share. Consider rotating a
                special display, improving wayfinding signage, or scheduling a docent
                activation to increase discovery and dwell time.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
