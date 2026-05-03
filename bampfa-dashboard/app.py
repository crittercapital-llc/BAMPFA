"""
app.py — BAMPFA Audience Analytics Dashboard
Home / Overview page

Run with: streamlit run app.py
"""

import datetime
import os

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="BAMPFA Audience Analytics",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — dark museum feel
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
      /* Global font and background */
      html, body, [class*="css"] {
          font-family: 'Inter', 'Helvetica Neue', sans-serif;
      }

      /* Sidebar */
      [data-testid="stSidebar"] {
          background-color: #0f0f1a;
      }
      [data-testid="stSidebar"] * {
          color: #e0e0e0 !important;
      }

      /* Main header banner */
      .bampfa-header {
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
          padding: 2rem 2.5rem 1.5rem 2.5rem;
          border-radius: 12px;
          margin-bottom: 1.5rem;
      }
      .bampfa-header h1 {
          color: #e8c99a;
          font-size: 2.1rem;
          font-weight: 700;
          margin: 0;
          letter-spacing: 0.02em;
      }
      .bampfa-header p {
          color: #a0b4c8;
          font-size: 0.95rem;
          margin: 0.4rem 0 0 0;
      }
      .bampfa-header .subtitle {
          color: #c8a96e;
          font-size: 0.78rem;
          font-weight: 600;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          margin-bottom: 0.4rem;
      }

      /* Metric cards */
      [data-testid="metric-container"] {
          background: #1e1e30;
          border: 1px solid #2d2d4a;
          border-radius: 10px;
          padding: 1rem;
      }
      [data-testid="metric-container"] label {
          color: #a0b4c8 !important;
          font-size: 0.78rem !important;
          text-transform: uppercase;
          letter-spacing: 0.08em;
      }
      [data-testid="metric-container"] [data-testid="stMetricValue"] {
          color: #e8c99a !important;
          font-size: 1.9rem !important;
          font-weight: 700 !important;
      }

      /* Section headers */
      .section-header {
          color: #c8a96e;
          font-size: 0.75rem;
          font-weight: 600;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          border-bottom: 1px solid #2d2d4a;
          padding-bottom: 0.4rem;
          margin: 1.5rem 0 1rem 0;
      }

      /* AI Briefing box */
      .ai-briefing {
          background: #141424;
          border: 1px solid #2d2d4a;
          border-left: 4px solid #c8a96e;
          border-radius: 8px;
          padding: 1.5rem;
      }
      .ai-briefing h2, .ai-briefing h3 {
          color: #e8c99a !important;
      }
      .ai-briefing p, .ai-briefing li {
          color: #d0d0e0 !important;
      }

      /* Chat messages */
      .chat-message-user {
          background: #1e1e30;
          border: 1px solid #2d2d4a;
          border-radius: 8px;
          padding: 0.8rem 1rem;
          margin-bottom: 0.5rem;
          color: #e0e0e0;
      }
      .chat-message-assistant {
          background: #141424;
          border: 1px solid #2d2d4a;
          border-left: 4px solid #c8a96e;
          border-radius: 8px;
          padding: 0.8rem 1rem;
          margin-bottom: 1rem;
          color: #d0d0d0;
      }

      /* Hide Streamlit default header */
      #MainMenu {visibility: hidden;}
      footer {visibility: hidden;}
      header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Imports (after page config)
# ---------------------------------------------------------------------------

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.data_agent import DataAgent
from agents.insights_agent import InsightsAgent

# ---------------------------------------------------------------------------
# Sidebar — global date filter
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### BAMPFA Analytics")
    st.markdown("---")
    st.markdown("**Date Range Filter**")

    min_date = datetime.date(2022, 1, 1)
    max_date = datetime.date(2026, 4, 30)

    date_start = st.date_input(
        "From",
        value=datetime.date(2025, 1, 1),
        min_value=min_date,
        max_value=max_date,
        key="global_start",
    )
    date_end = st.date_input(
        "To",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
        key="global_end",
    )

    st.markdown("---")
    st.caption("Data: Jan 2022 – Apr 2026")
    st.caption("Refresh: Daily batch")
    # TODO: Add live data source status indicators here

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

@st.cache_resource
def get_agent():
    return DataAgent()

agent = get_agent()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="bampfa-header">
        <div class="subtitle">Audience Analytics Dashboard</div>
        <h1>Berkeley Art Museum &amp; Pacific Film Archive</h1>
        <p>Marketing Intelligence Platform &mdash; Updated daily &mdash; Internal use only</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI Cards
# ---------------------------------------------------------------------------

kpis = agent.get_ytd_kpis()

st.markdown('<div class="section-header">2026 Year-to-Date Highlights</div>', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Visitors YTD",
        value=f"{kpis['ytd_visitors']:,}",
        delta="+8% vs 2025",
    )
with col2:
    st.metric(
        label="Active Members",
        value=f"{kpis['active_members']:,}",
        delta="-3% lapse rate",
    )
with col3:
    st.metric(
        label="Avg Review Rating",
        value=f"{kpis['avg_rating']} / 5",
        delta=f"{kpis['avg_rating_delta']:+.2f} vs 2025",
    )
with col4:
    st.metric(
        label="YTD Revenue",
        value=f"${kpis['ytd_revenue']:,.0f}",
        delta="+12% vs 2025",
    )

# ---------------------------------------------------------------------------
# Two-column charts: Attendance + Membership
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Attendance &amp; Membership Trends</div>', unsafe_allow_html=True)

chart_col1, chart_col2 = st.columns(2)

# --- Monthly Attendance by Category ---
with chart_col1:
    attendance = agent.get_attendance_by_month()
    fig_att = px.line(
        attendance,
        x="year_month_str",
        y="quantity",
        color="event_category",
        title="Monthly Attendance: Art vs Film",
        labels={"year_month_str": "Month", "quantity": "Visitors", "event_category": "Category"},
        color_discrete_map={"Art": "#c8a96e", "Film": "#5b8cdb"},
        template="plotly_dark",
    )
    fig_att.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        legend_title_text="",
        hovermode="x unified",
        xaxis=dict(tickangle=45, tickfont=dict(size=10)),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    # Shade every other month for readability
    st.plotly_chart(fig_att, use_container_width=True)

# --- Membership Over Time ---
with chart_col2:
    mem_time = agent.get_membership_over_time()
    fig_mem = go.Figure()
    fig_mem.add_trace(go.Scatter(
        x=mem_time["year_month"],
        y=mem_time["active"],
        name="Active",
        line=dict(color="#5b8cdb", width=2),
        fill="tozeroy",
        fillcolor="rgba(91,140,219,0.15)",
    ))
    fig_mem.add_trace(go.Scatter(
        x=mem_time["year_month"],
        y=mem_time["lapsed"],
        name="Lapsed",
        line=dict(color="#e06c75", width=2, dash="dot"),
    ))
    fig_mem.update_layout(
        title="Membership: Active vs Lapsed",
        template="plotly_dark",
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        legend_title_text="",
        hovermode="x unified",
        xaxis=dict(tickangle=45, tickfont=dict(size=10)),
        margin=dict(l=0, r=0, t=40, b=0),
        yaxis_title="Members",
    )
    st.plotly_chart(fig_mem, use_container_width=True)

# ---------------------------------------------------------------------------
# AI Daily Briefing
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Today\'s AI Briefing</div>', unsafe_allow_html=True)

@st.cache_data(ttl=3600, show_spinner="Generating AI briefing...")
def get_briefing(data_summary: str) -> str:
    insights = InsightsAgent(data_summary)
    return insights.generate_dashboard_summary()

data_summary = agent.get_data_summary_for_ai()
briefing = get_briefing(data_summary)

# Render briefing in a styled container — use st.markdown so markdown renders properly
st.markdown('<div class="ai-briefing">', unsafe_allow_html=True)
st.markdown(briefing)
st.markdown('</div>', unsafe_allow_html=True)

# Check API key from both .env and Streamlit secrets
def _has_api_key() -> bool:
    if os.getenv("ANTHROPIC_API_KEY"):
        return True
    try:
        return bool(st.secrets.get("ANTHROPIC_API_KEY", ""))
    except Exception:
        return False

if not _has_api_key():
    st.info("Tip: Add ANTHROPIC_API_KEY to Streamlit secrets to enable live AI briefings powered by Claude.")

# ---------------------------------------------------------------------------
# Inline follow-up chat on briefing
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Ask a Follow-Up</div>', unsafe_allow_html=True)

if "home_chat" not in st.session_state:
    st.session_state.home_chat = []

# Display previous Q&A
for msg in st.session_state.home_chat:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="chat-message-user"><strong>You:</strong> {msg["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="chat-message-assistant"><strong>Claude:</strong></div>',
            unsafe_allow_html=True,
        )
        st.markdown(msg["content"])

# Input form
with st.form(key="home_chat_form", clear_on_submit=True):
    home_input = st.text_input(
        "Ask Claude about the briefing or any audience trend",
        placeholder="e.g. 'What should we do about the April web traffic dip?'",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Ask Claude →", type="primary")

if submitted and home_input.strip():
    st.session_state.home_chat.append({"role": "user", "content": home_input.strip()})
    insights_agent = InsightsAgent(data_summary)
    with st.spinner("Claude is thinking..."):
        response = insights_agent.ask_with_history(
            home_input.strip(),
            st.session_state.home_chat[:-1],
        )
    st.session_state.home_chat.append({"role": "assistant", "content": response})
    st.rerun()

if st.session_state.home_chat:
    if st.button("Clear", type="secondary"):
        st.session_state.home_chat = []
        st.rerun()

# ---------------------------------------------------------------------------
# Navigation — clickable page links
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Navigate the Dashboard</div>', unsafe_allow_html=True)

nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns(5)

with nav_col1:
    st.page_link("pages/1_Attendance.py", label="📊 Attendance", use_container_width=True)
    st.caption("Seasonality, G1 shows, distance traveled, press spikes, VX staffing")
with nav_col2:
    st.page_link("pages/2_Membership.py", label="👥 Membership", use_container_width=True)
    st.caption("Tiers, lapse risk, cohorts, conversion targets")
with nav_col3:
    st.page_link("pages/3_Purchase_Behavior.py", label="🎟️ Purchase Behavior", use_container_width=True)
    st.caption("Lead times, channels, ticket types, revenue")
with nav_col4:
    st.page_link("pages/4_AI_Insights.py", label="🤖 AI Insights", use_container_width=True)
    st.caption("Ask Claude anything about BAMPFA audience data")
with nav_col5:
    st.page_link("pages/5_Event_Forecast.py", label="🔮 Event Forecaster", use_container_width=True)
    st.caption("Forecast attendance & staffing for a new film or exhibit")
