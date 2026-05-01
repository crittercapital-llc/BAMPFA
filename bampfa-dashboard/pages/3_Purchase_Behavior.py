"""
pages/3_Purchase_Behavior.py
BAMPFA Audience Analytics — Purchase Behavior deep-dive page.
"""

import sys
from pathlib import Path

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Purchase Behavior | BAMPFA Analytics",
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

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>Purchase Behavior</h2>
        <p>Lead times, channel mix, ticket types, revenue patterns, and member vs. non-member purchasing analysis.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI Row
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Purchase Overview</div>', unsafe_allow_html=True)

tx = agent.transactions
total_revenue = tx["revenue"].sum()
online_pct = (tx["channel"] == "Online").mean() * 100
avg_lead = tx["purchase_lead_days"].mean()
avg_qty = tx["quantity"].mean()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Total Revenue (All Time)", f"${total_revenue:,.0f}")
with k2:
    st.metric("Online Purchase Rate", f"{online_pct:.1f}%")
with k3:
    st.metric("Avg Purchase Lead Time", f"{avg_lead:.1f} days")
with k4:
    st.metric("Avg Tickets per Transaction", f"{avg_qty:.2f}")

# ---------------------------------------------------------------------------
# Section 1: Purchase Lead Time Distribution
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Purchase Lead Time Distribution</div>', unsafe_allow_html=True)
st.caption("How many days in advance do patrons buy tickets? Members and online buyers plan ahead more.")

lead_data = agent.get_purchase_lead_distribution()

lead_col1, lead_col2 = st.columns([3, 2])

with lead_col1:
    # Histogram: all patrons
    fig_lead = px.histogram(
        lead_data,
        x="purchase_lead_days",
        color="is_member",
        nbins=40,
        barmode="overlay",
        opacity=0.75,
        labels={"purchase_lead_days": "Days Before Event", "is_member": "Member"},
        title="Days Before Event: Ticket Purchase Timing",
        color_discrete_map={True: "#c8a96e", False: "#5b8cdb"},
        template="plotly_dark",
    )
    fig_lead.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        legend=dict(
            title="Member",
            itemsizing="constant",
        ),
        height=360,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis_title="Days Before Event",
        yaxis_title="Transactions",
    )
    # Rename legend labels
    fig_lead.for_each_trace(lambda t: t.update(name="Member" if t.name == "True" else "Non-Member"))
    st.plotly_chart(fig_lead, use_container_width=True)

with lead_col2:
    # Box plot by channel
    fig_box = px.box(
        lead_data,
        x="channel",
        y="purchase_lead_days",
        color="channel",
        title="Lead Time by Channel",
        labels={"purchase_lead_days": "Days Before Event", "channel": "Channel"},
        color_discrete_map={"Online": "#5b8cdb", "Onsite": "#c8a96e"},
        template="plotly_dark",
    )
    fig_box.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        showlegend=False,
        height=360,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_box, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 2: Online vs Onsite Over Time
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Online vs. Onsite Channel Mix Over Time</div>', unsafe_allow_html=True)

channel_data = agent.get_channel_over_time()

fig_channel = px.area(
    channel_data,
    x="year_month_str",
    y="quantity",
    color="channel",
    title="Monthly Ticket Sales: Online vs. Onsite",
    labels={"year_month_str": "Month", "quantity": "Tickets Sold", "channel": "Channel"},
    color_discrete_map={"Online": "#5b8cdb", "Onsite": "#c8a96e"},
    template="plotly_dark",
)
fig_channel.update_layout(
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    legend_title_text="",
    hovermode="x unified",
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    height=340,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_channel, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Ticket Type + Revenue by Category
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Ticket Types &amp; Revenue by Event Category</div>', unsafe_allow_html=True)

tt_col, rev_col = st.columns(2)

with tt_col:
    ticket_breakdown = agent.get_ticket_type_breakdown()
    fig_tt = px.bar(
        ticket_breakdown,
        x="ticket_type",
        y="total_visitors",
        color="ticket_type",
        title="Visitors by Ticket Type",
        labels={"ticket_type": "Ticket Type", "total_visitors": "Total Visitors"},
        template="plotly_dark",
        color_discrete_sequence=["#c8a96e", "#5b8cdb", "#98c379", "#e06c75", "#d19a66"],
        text="total_visitors",
    )
    fig_tt.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig_tt.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        showlegend=False,
        yaxis=dict(range=[0, ticket_breakdown["total_visitors"].max() * 1.15]),
        height=340,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_tt, use_container_width=True)

with rev_col:
    rev_data = agent.get_revenue_by_category()
    fig_rev = px.area(
        rev_data,
        x="year_month_str",
        y="revenue",
        color="event_category",
        title="Monthly Revenue: Art vs Film",
        labels={"year_month_str": "Month", "revenue": "Revenue ($)", "event_category": "Category"},
        color_discrete_map={"Art": "#c8a96e", "Film": "#5b8cdb"},
        template="plotly_dark",
    )
    fig_rev.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        legend_title_text="",
        hovermode="x unified",
        xaxis=dict(tickangle=45, tickfont=dict(size=9)),
        height=340,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_rev, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 4: Day-of-Week Purchase Patterns
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Purchase Timing — Day of Week</div>', unsafe_allow_html=True)
st.caption(
    "Based on transaction_date. Shows when patrons are actually making purchases, "
    "useful for scheduling email campaigns and social posts."
)

tx = agent.transactions.copy()
tx["purchase_dow"] = tx["transaction_date"].dt.day_name()

dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow_counts = (
    tx.groupby(["purchase_dow", "channel"])["transaction_id"]
    .count()
    .reset_index(name="transactions")
)
dow_counts["purchase_dow"] = pd.Categorical(dow_counts["purchase_dow"], categories=dow_order, ordered=True)
dow_counts = dow_counts.sort_values("purchase_dow")

fig_dow = px.bar(
    dow_counts,
    x="purchase_dow",
    y="transactions",
    color="channel",
    barmode="group",
    title="Transactions by Day of Week",
    labels={"purchase_dow": "Day", "transactions": "Transactions", "channel": "Channel"},
    color_discrete_map={"Online": "#5b8cdb", "Onsite": "#c8a96e"},
    template="plotly_dark",
)
fig_dow.update_layout(
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    legend_title_text="",
    height=320,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_dow, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 5: Member vs Non-Member Purchasing Patterns
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Member vs. Non-Member Purchasing Patterns</div>', unsafe_allow_html=True)

comparison = agent.get_member_vs_nonmember()

# Radar / comparison table
comp_table = comparison[["is_member", "avg_ticket_price", "avg_quantity", "avg_lead_days", "online_pct", "transactions"]].copy()
comp_table["avg_ticket_price"] = comp_table["avg_ticket_price"].map("${:.2f}".format)
comp_table["avg_quantity"] = comp_table["avg_quantity"].map("{:.2f}".format)
comp_table["avg_lead_days"] = comp_table["avg_lead_days"].map("{:.1f} days".format)
comp_table["online_pct"] = comp_table["online_pct"].map("{:.1f}%".format)
comp_table["transactions"] = comp_table["transactions"].map("{:,}".format)
comp_table.columns = ["Segment", "Avg Ticket Price", "Avg Qty", "Avg Lead Time", "Online %", "Total Transactions"]
st.dataframe(comp_table, use_container_width=True, hide_index=True)

# Lead time density comparison
fig_density = go.Figure()
for is_mem, label, color in [(True, "Members", "#c8a96e"), (False, "Non-Members", "#5b8cdb")]:
    subset = lead_data[lead_data["is_member"] == is_mem]["purchase_lead_days"]
    fig_density.add_trace(go.Histogram(
        x=subset,
        name=label,
        nbinsx=30,
        opacity=0.65,
        marker_color=color,
        histnorm="probability density",
    ))
fig_density.update_layout(
    title="Lead Time Distribution: Members vs. Non-Members (Density)",
    barmode="overlay",
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    xaxis_title="Days Before Event",
    yaxis_title="Density",
    legend_title_text="",
    height=320,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_density, use_container_width=True)
