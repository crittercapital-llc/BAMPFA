"""
pages/11_Spend_Analysis.py
BAMPFA Audience Analytics — Spend Analysis.

Inspired by Dexibit's spend analysis feature: breaks down revenue by stream
(tickets, F&B/café, retail/gift shop), calculates per-capita spend, and
compares member vs. non-member purchasing behavior to surface revenue
optimization opportunities.

⚠ F&B and retail revenue figures are simulated at typical cultural-institution
  per-capita rates. Replace with actual POS exports when available.
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
    page_title="Spend Analysis | BAMPFA Analytics",
    page_icon="💰",
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
      .spend-card { background: #1e1e30; border: 1px solid #2d2d4a; border-radius: 8px;
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
    st.markdown("### Spend Analysis Filters")
    st.markdown("---")
    year_options = list(range(2022, 2027))
    selected_year = st.selectbox("Focus Year", options=year_options, index=3)

    stream_options = ["Ticket Revenue", "F&B (Café)", "Retail (Gift Shop)"]
    selected_streams = st.multiselect(
        "Revenue Streams",
        options=stream_options,
        default=stream_options,
    )
    st.markdown("---")
    st.caption("⚠ F&B and retail revenue are simulated at industry-standard per-capita rates.")
    st.caption("Typical benchmarks: F&B ~$4.50/visitor · Retail ~$7.20/visitor")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>💰 Spend Analysis</h2>
        <p>Understand total revenue per visitor across all streams — tickets, café, and gift shop.
           Benchmark per-capita performance and identify opportunities to grow secondary revenue.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "⚠️ **Demo Mode:** Café (F&B) and gift shop (retail) revenue are modelled at "
    "typical cultural-institution per-capita rates ($3.80–$5.20 F&B · $5.50–$9.00 retail). "
    "Connect your POS system for real figures.",
    icon="🛒",
)

# ---------------------------------------------------------------------------
# Load spend data
# ---------------------------------------------------------------------------

spend_df = agent.get_spend_breakdown()
segment_df = agent.get_per_capita_spend_by_segment()
member_df = agent.get_member_vs_nonmember()

year_spend = spend_df[spend_df["year_month_str"].str.startswith(str(selected_year))].copy()

# ---------------------------------------------------------------------------
# Section 1: YTD Spend KPIs
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Revenue Snapshot — Selected Year</div>', unsafe_allow_html=True)

if not year_spend.empty:
    tot_ticket = year_spend["ticket_revenue"].sum()
    tot_fb = year_spend["fb_revenue"].sum()
    tot_retail = year_spend["retail_revenue"].sum()
    tot_total = year_spend["total_revenue"].sum()
    tot_visitors = year_spend["visitors"].sum()
    avg_per_cap = year_spend["per_capita_total"].mean()
    avg_ticket_per_cap = (tot_ticket / tot_visitors) if tot_visitors else 0
    avg_fb_per_cap = (tot_fb / tot_visitors) if tot_visitors else 0
    avg_retail_per_cap = (tot_retail / tot_visitors) if tot_visitors else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total Revenue", f"${tot_total:,.0f}", delta=None)
    with k2:
        st.metric("Ticket Revenue", f"${tot_ticket:,.0f}",
                  delta=f"{tot_ticket/tot_total*100:.0f}% of total")
    with k3:
        st.metric("F&B Revenue", f"${tot_fb:,.0f}",
                  delta=f"{tot_fb/tot_total*100:.0f}% of total")
    with k4:
        st.metric("Retail Revenue", f"${tot_retail:,.0f}",
                  delta=f"{tot_retail/tot_total*100:.0f}% of total")
    with k5:
        st.metric("Avg Per-Capita Spend", f"${avg_per_cap:.2f}", delta=None)

# ---------------------------------------------------------------------------
# Section 2: Revenue Mix — Stacked Bar by Month
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Monthly Revenue Mix by Stream</div>', unsafe_allow_html=True)

if not year_spend.empty:
    stream_map = {
        "Ticket Revenue": ("ticket_revenue", "#c8a96e"),
        "F&B (Café)": ("fb_revenue", "#5b8cdb"),
        "Retail (Gift Shop)": ("retail_revenue", "#8fd36e"),
    }

    fig_stack = go.Figure()
    for stream_label in selected_streams:
        col, color = stream_map[stream_label]
        fig_stack.add_trace(go.Bar(
            x=year_spend["year_month_str"],
            y=year_spend[col],
            name=stream_label,
            marker_color=color,
        ))

    fig_stack.update_layout(
        barmode="stack",
        template="plotly_dark",
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        title=f"Monthly Revenue by Stream ({selected_year})",
        hovermode="x unified",
        height=360,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(tickangle=30, tickfont=dict(size=10)),
        yaxis_title="Revenue ($)",
    )
    st.plotly_chart(fig_stack, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Per-Capita Spend Trend
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Per-Capita Total Spend Over Time</div>', unsafe_allow_html=True)
st.caption(
    "Total revenue (all streams) divided by visitor count. "
    "Rising per-capita indicates successful upselling; dips may signal "
    "price-sensitivity or reduced secondary purchases."
)

all_year_spend = spend_df.copy()

fig_percap = go.Figure()
fig_percap.add_trace(go.Scatter(
    x=all_year_spend["year_month_str"],
    y=all_year_spend["per_capita_total"],
    name="Per-Capita Spend",
    line=dict(color="#c8a96e", width=2),
    fill="tozeroy",
    fillcolor="rgba(200,169,110,0.1)",
))

# Add benchmark line (~$18 typical mid-size museum)
fig_percap.add_hline(
    y=18.0,
    line_color="#5b8cdb",
    line_dash="dot",
    annotation_text="Industry benchmark ~$18",
    annotation_font_color="#5b8cdb",
    annotation_position="bottom right",
)

fig_percap.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    hovermode="x unified",
    height=300,
    margin=dict(l=0, r=0, t=30, b=0),
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    yaxis_title="$ per Visitor",
)
st.plotly_chart(fig_percap, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 4: Revenue Stream Donut Charts
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Revenue Stream Mix — Full Period vs Selected Year</div>', unsafe_allow_html=True)

donut_col1, donut_col2 = st.columns(2)

def make_donut(ticket, fb, retail, title):
    fig = go.Figure(data=[go.Pie(
        labels=["Tickets", "F&B / Café", "Retail / Gift Shop"],
        values=[ticket, fb, retail],
        hole=0.45,
        marker_colors=["#c8a96e", "#5b8cdb", "#8fd36e"],
    )])
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor="#1e1e30",
        height=300,
        margin=dict(l=0, r=10, t=40, b=0),
        legend=dict(orientation="h", y=-0.1),
    )
    return fig

with donut_col1:
    full = spend_df[["ticket_revenue", "fb_revenue", "retail_revenue"]].sum()
    st.plotly_chart(
        make_donut(full["ticket_revenue"], full["fb_revenue"], full["retail_revenue"],
                   "All-Time Revenue Mix"),
        use_container_width=True,
    )

with donut_col2:
    if not year_spend.empty:
        yr = year_spend[["ticket_revenue", "fb_revenue", "retail_revenue"]].sum()
        st.plotly_chart(
            make_donut(yr["ticket_revenue"], yr["fb_revenue"], yr["retail_revenue"],
                       f"{selected_year} Revenue Mix"),
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Section 5: Member vs. Non-Member Spend Comparison
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Member vs. Non-Member Purchase Behavior</div>', unsafe_allow_html=True)
st.caption(
    "Members typically pay less per ticket (discounts) but buy earlier and in greater quantities. "
    "Non-members drive higher per-transaction revenue. Understanding this split "
    "informs pricing and membership value proposition."
)

if not member_df.empty:
    mem_col1, mem_col2 = st.columns(2)

    with mem_col1:
        fig_mem_price = go.Figure(go.Bar(
            x=member_df["is_member"],
            y=member_df["avg_ticket_price"].round(2),
            marker_color=["#5b8cdb", "#c8a96e"],
            text=[f"${v:.2f}" for v in member_df["avg_ticket_price"]],
            textposition="outside",
            textfont=dict(color="#e0e0e0"),
        ))
        fig_mem_price.update_layout(
            title="Average Ticket Price",
            template="plotly_dark",
            paper_bgcolor="#1e1e30",
            plot_bgcolor="#141424",
            height=300,
            margin=dict(l=0, r=0, t=40, b=0),
            yaxis_title="$ per ticket",
            showlegend=False,
        )
        st.plotly_chart(fig_mem_price, use_container_width=True)

    with mem_col2:
        fig_mem_lead = go.Figure(go.Bar(
            x=member_df["is_member"],
            y=member_df["avg_lead_days"].round(1),
            marker_color=["#5b8cdb", "#c8a96e"],
            text=[f"{v:.1f}d" for v in member_df["avg_lead_days"]],
            textposition="outside",
            textfont=dict(color="#e0e0e0"),
        ))
        fig_mem_lead.update_layout(
            title="Avg Purchase Lead Time (days before event)",
            template="plotly_dark",
            paper_bgcolor="#1e1e30",
            plot_bgcolor="#141424",
            height=300,
            margin=dict(l=0, r=0, t=40, b=0),
            yaxis_title="Days",
            showlegend=False,
        )
        st.plotly_chart(fig_mem_lead, use_container_width=True)

    # Comparison table
    display_mem = member_df[
        ["is_member", "avg_ticket_price", "avg_quantity", "avg_lead_days",
         "online_pct", "total_revenue", "transactions"]
    ].copy()
    display_mem["avg_ticket_price"] = display_mem["avg_ticket_price"].map("${:.2f}".format)
    display_mem["avg_quantity"] = display_mem["avg_quantity"].map("{:.2f}".format)
    display_mem["avg_lead_days"] = display_mem["avg_lead_days"].map("{:.1f} days".format)
    display_mem["online_pct"] = display_mem["online_pct"].map("{:.1f}%".format)
    display_mem["total_revenue"] = display_mem["total_revenue"].map("${:,.0f}".format)
    display_mem.columns = ["Segment", "Avg Ticket Price", "Avg Qty/Txn",
                            "Avg Lead Time", "Online %", "Total Revenue", "Transactions"]
    st.dataframe(display_mem, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 6: Per-Capita Spend by Segment
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Ticket Revenue Per-Capita by Visitor Segment</div>', unsafe_allow_html=True)

if not segment_df.empty:
    fig_seg = px.bar(
        segment_df.sort_values("avg_revenue_per_transaction", ascending=False),
        x="segment",
        y="avg_revenue_per_transaction",
        color="avg_ticket_price",
        color_continuous_scale="YlOrBr",
        labels={
            "segment": "Visitor Segment",
            "avg_revenue_per_transaction": "Avg Revenue / Transaction ($)",
            "avg_ticket_price": "Avg Ticket Price",
        },
        title="Average Revenue per Transaction by Visitor Segment",
        template="plotly_dark",
        text="avg_revenue_per_transaction",
    )
    fig_seg.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
    fig_seg.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        height=320,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(tickangle=10),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_seg, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 7: Spend Optimization Insights
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Revenue Optimization Opportunities</div>', unsafe_allow_html=True)

if not year_spend.empty and tot_visitors > 0:
    current_percap = tot_total / tot_visitors
    target_percap = 20.0
    gap = max(0, target_percap - current_percap)
    annual_uplift = gap * tot_visitors

    ins_col1, ins_col2, ins_col3 = st.columns(3)

    with ins_col1:
        st.markdown(
            f"""
            <div class="spend-card">
                <div style="color:#c8a96e;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.1em;margin-bottom:0.4rem;">Per-Capita vs Target</div>
                <div style="color:#e8c99a;font-size:1.6rem;font-weight:700;">${current_percap:.2f}</div>
                <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                    Current all-stream per-capita vs. $20 target.
                    <strong style="color:#8fd36e;">
                        ${gap:.2f} gap = ~${annual_uplift:,.0f} potential uplift
                    </strong> at current visitor volume.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with ins_col2:
        fb_share = (tot_fb / tot_total * 100) if tot_total else 0
        industry_fb = 15.0
        fb_status = "below" if fb_share < industry_fb else "at or above"
        st.markdown(
            f"""
            <div class="spend-card">
                <div style="color:#5b8cdb;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.1em;margin-bottom:0.4rem;">F&B Revenue Share</div>
                <div style="color:#e8c99a;font-size:1.6rem;font-weight:700;">{fb_share:.1f}%</div>
                <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                    F&B is {fb_status} the ~{industry_fb:.0f}% industry benchmark.
                    Consider café promotions during exhibition openings and
                    film-program intermissions.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with ins_col3:
        retail_per_cap = tot_retail / tot_visitors if tot_visitors else 0
        st.markdown(
            f"""
            <div class="spend-card">
                <div style="color:#8fd36e;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                            letter-spacing:0.1em;margin-bottom:0.4rem;">Retail Per-Capita</div>
                <div style="color:#e8c99a;font-size:1.6rem;font-weight:700;">${retail_per_cap:.2f}</div>
                <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                    Industry range: $5–$12. Place exhibition-tied merchandise near
                    G1 exit and offer member discounts to boost conversion.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
