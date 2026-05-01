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
# Section 5: Geographic Distribution
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Geographic Visitor Distribution</div>', unsafe_allow_html=True)
st.caption("Visitor counts by zip code — weighted toward Berkeley/Oakland core, with reach into SF and beyond.")

zip_data = agent.get_zip_distribution()

geo_col1, geo_col2 = st.columns([3, 2])

with geo_col1:
    fig_zip = px.bar(
        zip_data.head(20),
        x="visitors",
        y="zip_code",
        orientation="h",
        color="region",
        labels={"visitors": "Total Visitors", "zip_code": "Zip Code", "region": "Region"},
        title="Top 20 Zip Codes by Visitor Count",
        color_discrete_sequence=px.colors.qualitative.Pastel,
        template="plotly_dark",
    )
    fig_zip.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        yaxis=dict(autorange="reversed"),
        height=480,
        margin=dict(l=0, r=0, t=40, b=0),
        legend_title_text="Region",
    )
    st.plotly_chart(fig_zip, use_container_width=True)

with geo_col2:
    region_summary = (
        zip_data.groupby("region")["visitors"]
        .sum()
        .reset_index()
        .sort_values("visitors", ascending=False)
    )
    fig_region = px.pie(
        region_summary,
        values="visitors",
        names="region",
        title="Visitors by Region",
        template="plotly_dark",
        hole=0.35,
        color_discrete_sequence=px.colors.qualitative.Pastel,
    )
    fig_region.update_layout(
        paper_bgcolor="#1e1e30",
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_region, use_container_width=True)

    # Summary table
    region_summary["visitors"] = region_summary["visitors"].map("{:,}".format)
    region_summary.columns = ["Region", "Visitors"]
    st.dataframe(region_summary, use_container_width=True, hide_index=True)
