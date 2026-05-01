"""
pages/2_Membership.py
BAMPFA Audience Analytics — Membership deep-dive page.
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
    page_title="Membership | BAMPFA Analytics",
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
      .highlight-box { background: #1a1a2e; border: 1px solid #2d2d4a;
          border-left: 4px solid #c8a96e; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
      [data-testid="metric-container"] { background: #1e1e30; border: 1px solid #2d2d4a;
          border-radius: 10px; padding: 1rem; }
      [data-testid="metric-container"] label { color: #a0b4c8 !important;
          font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
      [data-testid="metric-container"] [data-testid="stMetricValue"] {
          color: #e8c99a !important; font-size: 1.9rem !important; font-weight: 700 !important; }
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
metrics = agent.get_member_metrics()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>Membership Analytics</h2>
        <p>Active vs. lapsed trends, tier mix, acquisition channels, cohort retention, and conversion opportunities.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI Row
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Membership Snapshot</div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Active Members", f"{metrics['active_members']:,}")
with k2:
    st.metric("Lapsed Members", f"{metrics['lapsed_members']:,}")
with k3:
    st.metric("Lapse Rate", f"{metrics['lapse_rate']}%")
with k4:
    st.metric("Avg Visits / Member", f"{metrics['avg_visits']}")

# ---------------------------------------------------------------------------
# Section 1: Active vs Lapsed Over Time
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Active vs. Lapsed Members Over Time</div>', unsafe_allow_html=True)

mem_time = agent.get_membership_over_time()

fig_time = go.Figure()
fig_time.add_trace(go.Scatter(
    x=mem_time["year_month"],
    y=mem_time["active"],
    name="Active Members",
    line=dict(color="#5b8cdb", width=2.5),
    fill="tozeroy",
    fillcolor="rgba(91,140,219,0.15)",
))
fig_time.add_trace(go.Scatter(
    x=mem_time["year_month"],
    y=mem_time["lapsed"],
    name="Lapsed Members",
    line=dict(color="#e06c75", width=2, dash="dot"),
))
fig_time.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    hovermode="x unified",
    legend_title_text="",
    yaxis_title="Members",
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    height=350,
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig_time, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 2: Tier + Acquisition breakdown
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Tier Mix &amp; Acquisition Channels</div>', unsafe_allow_html=True)

donut_col, acq_col = st.columns(2)

with donut_col:
    tier_df = (
        agent.members[agent.members["is_active"]]
        .groupby("membership_tier")
        .size()
        .reset_index(name="count")
    )
    tier_order = ["Individual", "Dual", "Family", "Patron", "Benefactor"]
    fig_tier = px.pie(
        tier_df,
        values="count",
        names="membership_tier",
        title="Active Members by Tier",
        template="plotly_dark",
        hole=0.42,
        category_orders={"membership_tier": tier_order},
        color_discrete_sequence=["#c8a96e", "#5b8cdb", "#98c379", "#e06c75", "#d19a66"],
    )
    fig_tier.update_traces(textposition="inside", textinfo="percent+label")
    fig_tier.update_layout(
        paper_bgcolor="#1e1e30",
        showlegend=False,
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_tier, use_container_width=True)

with acq_col:
    acq_df = (
        agent.members[agent.members["is_active"]]
        .groupby("acquisition_channel")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=True)
    )
    fig_acq = px.bar(
        acq_df,
        x="count",
        y="acquisition_channel",
        orientation="h",
        title="New Members by Acquisition Channel",
        labels={"count": "Members", "acquisition_channel": "Channel"},
        color="count",
        color_continuous_scale="Blues",
        template="plotly_dark",
    )
    fig_acq.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        coloraxis_showscale=False,
        yaxis_title="",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_acq, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Cohort Retention
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Cohort Retention by Join Quarter</div>', unsafe_allow_html=True)
st.caption("Measures the % of members from each join cohort who have not lapsed.")

cohort = agent.get_member_cohort_retention()

fig_cohort = px.bar(
    cohort,
    x="join_quarter",
    y="retention_rate",
    color="retention_rate",
    color_continuous_scale="RdYlGn",
    range_color=[50, 100],
    labels={"join_quarter": "Join Quarter", "retention_rate": "Retention Rate (%)"},
    title="Retention Rate by Cohort Quarter",
    text="retention_rate",
    template="plotly_dark",
)
fig_cohort.update_traces(texttemplate="%{text:.0f}%", textposition="outside")
fig_cohort.update_layout(
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    coloraxis_showscale=False,
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    yaxis=dict(range=[0, 110]),
    height=350,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_cohort, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 4: Conversion Opportunity Table
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Membership Conversion Opportunities</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="highlight-box">'
    'These patrons have visited <strong>3 or more times</strong> but have never joined as members. '
    'They represent high-intent prospects for direct outreach or targeted email campaigns.'
    '</div>',
    unsafe_allow_html=True,
)

convert_col1, convert_col2 = st.columns([3, 2])

with convert_col1:
    min_visits = st.slider("Minimum visits threshold", min_value=2, max_value=8, value=3)
    targets = agent.get_repeat_visitors_not_members(min_visits=min_visits)

    st.metric("Conversion Targets", f"{len(targets):,} patrons")

    display = targets.head(30).copy()
    display["total_spend"] = display["total_spend"].map("${:,.0f}".format)
    display["last_event"] = display["last_event"].dt.strftime("%b %d, %Y")
    display.columns = ["Patron ID", "Visits", "Total Spend", "Last Event", "Zip Code"]
    st.dataframe(display, use_container_width=True, hide_index=True)

with convert_col2:
    visits_dist = targets["visits"].value_counts().sort_index().reset_index()
    visits_dist.columns = ["Visits", "Patrons"]
    fig_visits = px.bar(
        visits_dist,
        x="Visits",
        y="Patrons",
        title="Visit Count Distribution (Non-Members)",
        template="plotly_dark",
        color="Patrons",
        color_continuous_scale="YlOrBr",
    )
    fig_visits.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        coloraxis_showscale=False,
        height=300,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_visits, use_container_width=True)

    avg_spend = targets["total_spend"].mean()
    st.metric("Avg Spend (Target Patrons)", f"${avg_spend:,.0f}")
    st.caption(
        f"If even 10% of {len(targets):,} targets convert at Individual tier (~$75/yr), "
        f"that's **${len(targets) * 0.10 * 75:,.0f}** in new membership revenue."
    )

# ---------------------------------------------------------------------------
# Section 5: Member vs Non-Member Purchase Behavior
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Member vs. Non-Member Purchase Patterns</div>', unsafe_allow_html=True)

comparison = agent.get_member_vs_nonmember()

comp_col1, comp_col2, comp_col3 = st.columns(3)
for col, metric_key, label, fmt in [
    (comp_col1, "avg_ticket_price", "Avg Ticket Price", "${:.2f}"),
    (comp_col2, "avg_lead_days", "Avg Purchase Lead (Days)", "{:.1f}"),
    (comp_col3, "online_pct", "Online Purchase %", "{:.1f}%"),
]:
    member_val = comparison[comparison["is_member"] == "Member"][metric_key].values[0]
    nonmember_val = comparison[comparison["is_member"] == "Non-Member"][metric_key].values[0]
    with col:
        fig = px.bar(
            comparison,
            x="is_member",
            y=metric_key,
            title=label,
            color="is_member",
            color_discrete_map={"Member": "#c8a96e", "Non-Member": "#5b8cdb"},
            template="plotly_dark",
            text=metric_key,
        )
        fig.update_traces(
            texttemplate=fmt.replace("{", "{text").replace("}", "}"),
            textposition="outside"
        )
        fig.update_layout(
            paper_bgcolor="#1e1e30",
            plot_bgcolor="#141424",
            showlegend=False,
            xaxis_title="",
            yaxis_title="",
            height=260,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
