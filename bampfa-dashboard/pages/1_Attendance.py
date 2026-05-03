"""
pages/1_Attendance.py
BAMPFA Audience Analytics — Attendance deep-dive page.
"""

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Attendance | BAMPFA Analytics",
    page_icon="🎨",
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
# Sidebar filters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Attendance Filters")
    st.markdown("---")
    view_mode = st.radio("View Mode", ["Monthly", "Weekly"], index=0)
    category_filter = st.multiselect(
        "Event Category",
        options=["Art", "Film"],
        default=["Art", "Film"],
    )
    st.markdown("---")
    st.caption("Data: Jan 2022 – Apr 2026")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>Attendance Analytics</h2>
        <p>Event performance, seasonality patterns, geographic reach, and web traffic correlation.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Section 1: Monthly / Weekly Attendance Bar Chart
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Attendance Over Time</div>', unsafe_allow_html=True)

if view_mode == "Monthly":
    att_data = agent.get_attendance_by_month()
    x_col = "year_month_str"
    x_label = "Month"
else:
    att_data = agent.get_attendance_by_week()
    x_col = "year_week"
    x_label = "Year-Week"

if category_filter:
    att_data = att_data[att_data["event_category"].isin(category_filter)]

fig_bar = px.bar(
    att_data,
    x=x_col,
    y="quantity",
    color="event_category",
    barmode="group",
    labels={x_col: x_label, "quantity": "Visitors", "event_category": "Category"},
    color_discrete_map={"Art": "#c8a96e", "Film": "#5b8cdb"},
    template="plotly_dark",
    title=f"{view_mode} Attendance by Category",
)
fig_bar.update_layout(
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    legend_title_text="",
    hovermode="x unified",
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    height=360,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 2: Seasonality Heatmap
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Seasonality Heatmap — Avg Visitors by Month &amp; Day</div>', unsafe_allow_html=True)

heatmap_data = agent.get_seasonality_heatmap()

fig_heat = px.imshow(
    heatmap_data,
    color_continuous_scale="YlOrBr",
    labels=dict(x="Day of Week", y="Month", color="Avg Visitors"),
    title="Average Daily Visitors: Month × Day of Week",
    template="plotly_dark",
    aspect="auto",
)
fig_heat.update_layout(
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    coloraxis_colorbar=dict(title="Visitors"),
    height=360,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_heat, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Event Performance Table
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Event Performance — All Exhibitions &amp; Films</div>', unsafe_allow_html=True)

event_perf = agent.get_event_performance()

col1, col2 = st.columns([2, 1])

with col1:
    # Top 10 by visitors
    top10 = event_perf.head(10).copy()
    top10["total_revenue"] = top10["total_revenue"].map("${:,.0f}".format)
    top10["avg_ticket_price"] = top10["avg_ticket_price"].map("${:.2f}".format)
    top10 = top10.rename(columns={
        "event_name": "Event",
        "event_category": "Category",
        "total_visitors": "Visitors",
        "total_revenue": "Revenue",
        "avg_ticket_price": "Avg Ticket",
        "transactions": "Transactions",
    })
    st.dataframe(top10, use_container_width=True, hide_index=True)

with col2:
    fig_cat = px.pie(
        event_perf.groupby("event_category")["total_visitors"].sum().reset_index(),
        values="total_visitors",
        names="event_category",
        title="Visitors: Art vs Film Split",
        color_discrete_map={"Art": "#c8a96e", "Film": "#5b8cdb"},
        template="plotly_dark",
        hole=0.4,
    )
    fig_cat.update_layout(
        paper_bgcolor="#1e1e30",
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 4: Attendance vs Web Traffic Overlay
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Attendance vs. Web Traffic Correlation</div>', unsafe_allow_html=True)
st.caption("Higher web sessions often precede or accompany attendance spikes — useful for campaign timing.")

overlay = agent.get_attendance_vs_traffic()

fig_overlay = go.Figure()
fig_overlay.add_trace(go.Scatter(
    x=overlay["year_month_str"],
    y=overlay["quantity"],
    name="Visitors",
    line=dict(color="#c8a96e", width=2),
    yaxis="y1",
))
fig_overlay.add_trace(go.Scatter(
    x=overlay["year_month_str"],
    y=overlay["sessions"],
    name="Web Sessions",
    line=dict(color="#5b8cdb", width=2, dash="dot"),
    yaxis="y2",
))
fig_overlay.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    hovermode="x unified",
    title="Monthly Attendance vs Web Sessions",
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    yaxis=dict(title="Visitors", titlefont=dict(color="#c8a96e")),
    yaxis2=dict(
        title="Web Sessions",
        titlefont=dict(color="#5b8cdb"),
        overlaying="y",
        side="right",
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=380,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_overlay, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 5: Geographic Distribution — Distance Traveled
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">How Far Are Visitors Traveling?</div>', unsafe_allow_html=True)
st.caption("Approximate distance from BAMPFA (2155 Center St, Berkeley) based on visitor zip codes.")

dist_data = agent.get_distance_distribution()

geo_col1, geo_col2 = st.columns([2, 3])

with geo_col1:
    bucket_summary = (
        dist_data.groupby("distance_bucket")["visitors"]
        .sum()
        .reset_index()
        .sort_values("visitors", ascending=False)
    )
    bucket_order = ["0–3 mi (Walking)", "3–10 mi (Local)", "10–25 mi (Regional)", "25–50 mi (Day Trip)", "50+ mi (Destination)", "Unknown"]
    bucket_summary["distance_bucket"] = pd.Categorical(bucket_summary["distance_bucket"], categories=bucket_order, ordered=True)
    bucket_summary = bucket_summary.sort_values("distance_bucket")

    fig_bucket = px.bar(
        bucket_summary,
        x="distance_bucket",
        y="visitors",
        color="distance_bucket",
        labels={"distance_bucket": "Distance from BAMPFA", "visitors": "Total Visitors"},
        title="Visitors by Distance Traveled",
        template="plotly_dark",
        color_discrete_sequence=["#5b8cdb", "#c8a96e", "#e06c75", "#98c379", "#c678dd", "#888888"],
    )
    fig_bucket.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        showlegend=False,
        height=360,
        margin=dict(l=0, r=0, t=40, b=80),
        xaxis=dict(tickangle=30, tickfont=dict(size=10)),
    )
    st.plotly_chart(fig_bucket, use_container_width=True)

with geo_col2:
    # Top 20 zips with distance
    top_zips = dist_data.dropna(subset=["distance_miles"]).head(20).copy()
    fig_zip = px.bar(
        top_zips,
        x="visitors",
        y="zip_code",
        orientation="h",
        color="distance_miles",
        color_continuous_scale="Blues",
        labels={"visitors": "Total Visitors", "zip_code": "Zip Code", "distance_miles": "Miles"},
        title="Top 20 Zip Codes — Colored by Distance",
        template="plotly_dark",
    )
    fig_zip.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        yaxis=dict(autorange="reversed"),
        height=480,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_zip, use_container_width=True)

# Distance insight callouts
d_cols = st.columns(4)
for i, bucket in enumerate(["0–3 mi (Walking)", "3–10 mi (Local)", "10–25 mi (Regional)", "25–50 mi (Day Trip)"]):
    row = bucket_summary[bucket_summary["distance_bucket"] == bucket]
    count = int(row["visitors"].values[0]) if len(row) else 0
    total = bucket_summary["visitors"].sum()
    pct = round(count / total * 100, 1) if total else 0
    with d_cols[i]:
        st.metric(bucket.split("(")[0].strip(), f"{count:,}", f"{pct}% of visitors")

# ---------------------------------------------------------------------------
# Section 6: Press Coverage Correlation
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Web Traffic Spikes vs. Attendance — Press Correlation Proxy</div>', unsafe_allow_html=True)
st.caption(
    "Months with above-average web traffic (potential press coverage or campaigns) highlighted in orange. "
    "Compare with attendance to spot lift. Not causal — correlational only. "
    "⚠️ Replace with actual press mention data when available."
)

spike_data = agent.get_press_spike_correlation()

fig_spike = go.Figure()

# Shade spike months
for _, row in spike_data[spike_data["is_spike"]].iterrows():
    fig_spike.add_vrect(
        x0=row["year_month_str"], x1=row["year_month_str"],
        fillcolor="rgba(200,169,110,0.15)", line_width=0,
    )

fig_spike.add_trace(go.Bar(
    x=spike_data["year_month_str"],
    y=spike_data["quantity"],
    name="Visitors",
    marker_color=[
        "#c8a96e" if s else "#2d2d4a" for s in spike_data["is_spike"]
    ],
    yaxis="y1",
))
fig_spike.add_trace(go.Scatter(
    x=spike_data["year_month_str"],
    y=spike_data["sessions"],
    name="Web Sessions",
    line=dict(color="#5b8cdb", width=2),
    yaxis="y2",
))
fig_spike.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    hovermode="x unified",
    title="Attendance (bars) vs Web Sessions (line) — Orange = Traffic Spike Month",
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    yaxis=dict(title="Visitors", titlefont=dict(color="#c8a96e")),
    yaxis2=dict(
        title="Web Sessions",
        titlefont=dict(color="#5b8cdb"),
        overlaying="y",
        side="right",
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=400,
    margin=dict(l=0, r=0, t=50, b=0),
)
st.plotly_chart(fig_spike, use_container_width=True)

# Spike summary table
spike_summary = spike_data[spike_data["is_spike"]][
    ["year_month_str", "sessions", "sessions_vs_avg", "quantity", "visitors_vs_avg"]
].copy()
spike_summary.columns = ["Month", "Web Sessions", "Sessions vs Avg (%)", "Visitors", "Attendance vs Avg (%)"]
st.caption("**Spike months** — web traffic significantly above average:")
st.dataframe(spike_summary, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 7: VX Staff Scheduling Forecast
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">VX Staff Scheduling Forecast</div>', unsafe_allow_html=True)
st.caption(
    "Recommended floor staff based on historical attendance patterns. "
    "Model assumes 1 staff per 80 visitors/day, 22 open days/month. "
    "Peak months (top 25% attendance) include a 20% buffer for G1 opening weekends. "
    "⚠️ Calibrate ratios with your operations team before using for actual scheduling."
)

staffing = agent.get_vx_staffing_forecast()
recent_staffing = staffing[staffing["year"] >= 2025].copy()

staff_col1, staff_col2 = st.columns([3, 2])

with staff_col1:
    fig_staff = go.Figure()
    fig_staff.add_trace(go.Bar(
        x=recent_staffing["label"],
        y=recent_staffing["total_visitors"],
        name="Total Visitors",
        marker_color=[
            "#c8a96e" if p else "#2d4a6e" for p in recent_staffing["is_peak"]
        ],
        yaxis="y1",
    ))
    fig_staff.add_trace(go.Scatter(
        x=recent_staffing["label"],
        y=recent_staffing["recommended_staff"],
        name="Recommended VX Staff",
        line=dict(color="#e06c75", width=3),
        mode="lines+markers",
        marker=dict(size=8),
        yaxis="y2",
    ))
    fig_staff.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        title="Attendance vs Recommended VX Staff (2025–2026) — Gold = Peak/G1 Month",
        hovermode="x unified",
        xaxis=dict(tickangle=45, tickfont=dict(size=9)),
        yaxis=dict(title="Total Visitors", titlefont=dict(color="#c8a96e")),
        yaxis2=dict(
            title="Staff Needed",
            titlefont=dict(color="#e06c75"),
            overlaying="y",
            side="right",
            rangemode="tozero",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=400,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    st.plotly_chart(fig_staff, use_container_width=True)

with staff_col2:
    st.markdown("**Staffing Schedule — 2026 YTD**")
    display_staff = recent_staffing[recent_staffing["year"] == 2026][
        ["label", "total_visitors", "avg_daily_visitors", "recommended_staff", "is_peak"]
    ].copy()
    display_staff["is_peak"] = display_staff["is_peak"].apply(lambda x: "🟠 Peak" if x else "")
    display_staff.columns = ["Month", "Total Visitors", "Avg Daily", "VX Staff Rec.", "Notes"]
    st.dataframe(display_staff, use_container_width=True, hide_index=True)
    st.caption("🟠 Peak = top-quartile attendance month, includes G1 opening buffer.")
