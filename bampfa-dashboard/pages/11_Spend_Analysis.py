"""
pages/11_Spend_Analysis.py
BAMPFA Audience Analytics — Ticket Revenue & Spend Analysis.

Analyses ticket revenue and per-capita spend from real transaction data.
Member vs. non-member, channel mix, venue split, and monthly trends.

F&B and retail data are NOT included — connect your POS system and add
those columns to the data pipeline before drawing any conclusions there.
"""

import sys
from pathlib import Path

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
      .callout { background: #1e1e30; border: 1px solid #2d2d4a;
          border-left: 4px solid #c8a96e; border-radius: 8px; padding: 1rem; }
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
    st.markdown("---")
    st.caption("All figures are ticket revenue from transaction records.")
    st.markdown(
        """
        <div style="background:#2a1a1a;border:1px solid #5c2a2a;border-radius:6px;
                    padding:0.6rem;font-size:0.78rem;color:#e08080;margin-top:0.5rem;">
            <strong>Not shown:</strong> F&amp;B and retail revenue require a POS
            integration — adding simulated figures here would be misleading.
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>💰 Ticket Revenue &amp; Spend Analysis</h2>
        <p>Per-capita ticket spend, revenue by venue and channel, and member vs.
           non-member purchasing behaviour — all from real transaction data.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load revenue data
# ---------------------------------------------------------------------------

revenue_df = agent.get_ticket_revenue_by_month()
venue_df = agent.get_revenue_by_gallery()
member_df = agent.get_member_vs_nonmember()
channel_df = agent.get_channel_over_time()
segment_df = agent.get_per_capita_spend_by_segment()

year_rev = revenue_df[revenue_df["year_month_str"].str.startswith(str(selected_year))]
year_venue = venue_df[venue_df["year_month_str"].str.startswith(str(selected_year))]

# ---------------------------------------------------------------------------
# Section 1: KPI snapshot
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Revenue Snapshot — Selected Year</div>', unsafe_allow_html=True)

if not year_rev.empty:
    tot_rev = year_rev["ticket_revenue"].sum()
    tot_vis = year_rev["visitors"].sum()
    avg_ticket = year_rev["avg_ticket_price"].mean()
    avg_percap = year_rev["per_capita_ticket"].mean()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Ticket Revenue", f"${tot_rev:,.0f}")
    with k2:
        st.metric("Total Visitors", f"{tot_vis:,}")
    with k3:
        st.metric("Avg Ticket Price", f"${avg_ticket:.2f}")
    with k4:
        st.metric("Avg Per-Capita (tickets)", f"${avg_percap:.2f}")

# ---------------------------------------------------------------------------
# Section 2: Monthly revenue trend
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Monthly Ticket Revenue</div>', unsafe_allow_html=True)

fig_rev = go.Figure()
fig_rev.add_trace(go.Bar(
    x=revenue_df["year_month_str"],
    y=revenue_df["ticket_revenue"],
    name="Ticket Revenue",
    marker_color="#c8a96e",
))
fig_rev.add_trace(go.Scatter(
    x=revenue_df["year_month_str"],
    y=revenue_df["per_capita_ticket"],
    name="Per-Capita ($)",
    line=dict(color="#5b8cdb", width=2),
    mode="lines",
    yaxis="y2",
))
fig_rev.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    title="Monthly Ticket Revenue vs Per-Capita Spend",
    hovermode="x unified",
    height=340,
    margin=dict(l=0, r=0, t=40, b=0),
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    yaxis=dict(title="Revenue ($)", title_font=dict(color="#c8a96e")),
    yaxis2=dict(
        title="Per-Capita ($)",
        title_font=dict(color="#5b8cdb"),
        overlaying="y",
        side="right",
    ),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig_rev, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 3: Revenue by venue
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Revenue by Venue</div>', unsafe_allow_html=True)
st.caption("Cinema ticket revenue vs gallery ticket revenue from transaction records.")

GALLERY_COLORS = {
    "Cinema": "#5b8cdb", "G1": "#c8a96e", "G2": "#8fd36e", "Outdoor": "#e06c75",
}

ven_col1, ven_col2 = st.columns([3, 2])

with ven_col1:
    fig_venue = px.bar(
        year_venue.sort_values("year_month_str"),
        x="year_month_str",
        y="revenue",
        color="gallery",
        barmode="stack",
        color_discrete_map=GALLERY_COLORS,
        labels={"year_month_str": "Month", "revenue": "Revenue ($)", "gallery": "Venue"},
        title=f"Monthly Ticket Revenue by Venue ({selected_year})",
        template="plotly_dark",
    )
    fig_venue.update_layout(
        paper_bgcolor="#1e1e30", plot_bgcolor="#141424",
        hovermode="x unified",
        height=320, margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(tickangle=30, tickfont=dict(size=10)),
    )
    st.plotly_chart(fig_venue, use_container_width=True)

with ven_col2:
    all_venue = (
        venue_df.groupby("gallery")
        .agg(total_revenue=("revenue", "sum"), total_visitors=("visitors", "sum"))
        .reset_index()
    )
    all_venue["avg_ticket"] = (all_venue["total_revenue"] / all_venue["total_visitors"]).round(2)
    all_venue["revenue_share"] = (all_venue["total_revenue"] / all_venue["total_revenue"].sum() * 100).round(1)
    display_venue = all_venue.copy()
    display_venue["total_revenue"] = display_venue["total_revenue"].map("${:,.0f}".format)
    display_venue["avg_ticket"] = display_venue["avg_ticket"].map("${:.2f}".format)
    display_venue["revenue_share"] = display_venue["revenue_share"].map("{:.1f}%".format)
    display_venue.columns = ["Venue", "Total Revenue", "Total Visitors", "Avg Ticket", "Revenue Share"]
    st.dataframe(display_venue, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 4: Member vs Non-Member
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Member vs. Non-Member Purchasing</div>', unsafe_allow_html=True)
st.caption(
    "Members pay less per ticket (discounts) but buy earlier and more predictably. "
    "Non-members drive higher per-transaction revenue. Both matter for cash flow."
)

if not member_df.empty:
    mem_col1, mem_col2, mem_col3 = st.columns(3)

    mem_metrics = {
        "Avg Ticket Price": ("avg_ticket_price", "${:.2f}"),
        "Avg Lead Days": ("avg_lead_days", "{:.1f} days"),
        "Online %": ("online_pct", "{:.1f}%"),
    }

    for col, (metric, (field, fmt)) in zip([mem_col1, mem_col2, mem_col3], mem_metrics.items()):
        with col:
            vals = {row["is_member"]: row[field] for _, row in member_df.iterrows()}
            fig = go.Figure(go.Bar(
                x=list(vals.keys()),
                y=list(vals.values()),
                marker_color=["#5b8cdb", "#c8a96e"],
                text=[fmt.format(v) for v in vals.values()],
                textposition="outside",
                textfont=dict(color="#e0e0e0"),
            ))
            fig.update_layout(
                title=metric,
                template="plotly_dark",
                paper_bgcolor="#1e1e30",
                plot_bgcolor="#141424",
                height=260,
                margin=dict(l=0, r=0, t=40, b=0),
                showlegend=False,
                xaxis=dict(tickfont=dict(size=11)),
            )
            st.plotly_chart(fig, use_container_width=True)

    # Revenue split table
    rev_split = member_df[["is_member", "total_revenue", "transactions"]].copy()
    rev_split["revenue_share"] = (rev_split["total_revenue"] / rev_split["total_revenue"].sum() * 100).round(1)
    rev_split["total_revenue"] = rev_split["total_revenue"].map("${:,.0f}".format)
    rev_split["revenue_share"] = rev_split["revenue_share"].map("{:.1f}%".format)
    rev_split.columns = ["Segment", "Total Revenue", "Transactions", "Revenue Share"]
    st.dataframe(rev_split, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 5: Online vs onsite revenue channel
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Online vs Onsite Revenue Channel</div>', unsafe_allow_html=True)

fig_chan = px.area(
    channel_df.sort_values("year_month_str"),
    x="year_month_str",
    y="quantity",
    color="channel",
    color_discrete_map={"Online": "#5b8cdb", "Onsite": "#c8a96e"},
    labels={"year_month_str": "Month", "quantity": "Visitors", "channel": "Channel"},
    title="Monthly Visitors by Purchase Channel",
    template="plotly_dark",
)
fig_chan.update_layout(
    paper_bgcolor="#1e1e30", plot_bgcolor="#141424",
    hovermode="x unified",
    height=300, margin=dict(l=0, r=0, t=40, b=0),
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
)
st.plotly_chart(fig_chan, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 6: What's missing + next steps
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">To Complete This Picture</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="callout">
        <strong style="color:#e8c99a;">Data gaps to close with your operations team</strong>
        <ul style="color:#a0b4c8;margin-top:0.6rem;font-size:0.88rem;line-height:1.7;">
            <li><strong style="color:#e0e0e0;">Café / F&B POS export</strong> — even a monthly
                totals spreadsheet would let you calculate true per-capita spend and identify
                peak F&B periods vs. attendance peaks.</li>
            <li><strong style="color:#e0e0e0;">Gift shop / retail POS export</strong> — same
                format. Correlating retail peaks with specific exhibitions would inform
                merchandise planning.</li>
            <li><strong style="color:#e0e0e0;">Membership fee revenue</strong> — currently not
                in the transaction export; adding it gives a complete revenue-per-patron picture
                for members.</li>
        </ul>
        Once available, these can be added as additional columns in the data pipeline without
        requiring code changes to any existing page.
    </div>
    """,
    unsafe_allow_html=True,
)
