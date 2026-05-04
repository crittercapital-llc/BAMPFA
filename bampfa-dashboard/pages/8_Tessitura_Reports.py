"""
pages/8_Tessitura_Reports.py
BAMPFA Audience Analytics — Live Tessitura data exports.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.real_data_agent import RealDataAgent

st.set_page_config(
    page_title="Tessitura Reports | BAMPFA Analytics",
    page_icon="🎟️",
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
    return RealDataAgent()

agent = get_agent()
ticketholders = agent.ticketholders
revenue = agent.revenue

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
      <h2>🎟️ Tessitura Reports</h2>
      <p>Live exports from Tessitura — ticketholder list, performance revenue, and will-call batch report</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<span style="background:#2d7a2d;color:white;padding:3px 10px;border-radius:4px;'
    'font-size:0.75rem;font-weight:600;">✓ REAL DATA</span>',
    unsafe_allow_html=True,
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Section 1 — Performance Revenue Breakdown
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Performance Revenue Breakdown</div>', unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="highlight-box">
      <strong style="color:#e8c99a;">{revenue["performance"]}</strong><br/>
      <span style="color:#a0b4c8;">{revenue["date"]}</span><br/>
      <span style="color:#7a8fa6;font-size:0.85rem;">{revenue["season"]}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

ticket_rows = revenue["ticket_rows"]
if ticket_rows:
    df_rev = pd.DataFrame(ticket_rows)
    total_tickets = df_rev["count"].sum()
    total_revenue = df_rev["total"].sum()
    avg_price = total_revenue / total_tickets if total_tickets else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Tickets Sold", f"{total_tickets:,}")
    c2.metric("Total Revenue", f"${total_revenue:,.2f}")
    c3.metric("Average Ticket Price", f"${avg_price:.2f}")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown('<div class="section-header">Revenue by Ticket Type</div>', unsafe_allow_html=True)
        fig_rev = px.bar(
            df_rev.sort_values("total", ascending=True),
            x="total",
            y="price_type",
            orientation="h",
            text="total",
            color="total",
            color_continuous_scale=[[0, "#1e3a5f"], [1, "#c8a96e"]],
            labels={"total": "Revenue ($)", "price_type": "Ticket Type"},
        )
        fig_rev.update_traces(
            texttemplate="$%{text:,.0f}",
            textposition="outside",
        )
        fig_rev.update_layout(
            plot_bgcolor="#0f0f1a",
            paper_bgcolor="#0f0f1a",
            font_color="#e0e0e0",
            coloraxis_showscale=False,
            margin=dict(l=10, r=60, t=10, b=10),
            xaxis=dict(gridcolor="#2d2d4a", tickprefix="$"),
            yaxis=dict(gridcolor="#2d2d4a"),
            height=320,
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-header">Tickets by Type</div>', unsafe_allow_html=True)
        fig_pie = px.pie(
            df_rev,
            names="price_type",
            values="count",
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig_pie.update_traces(textinfo="label+value", textfont_color="#e0e0e0")
        fig_pie.update_layout(
            plot_bgcolor="#0f0f1a",
            paper_bgcolor="#0f0f1a",
            font_color="#e0e0e0",
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown('<div class="section-header">Full Ticket Breakdown</div>', unsafe_allow_html=True)
    df_display = df_rev.copy()
    df_display.columns = ["Ticket Type", "Unit Price ($)", "Count", "Total Revenue ($)"]
    df_display["Unit Price ($)"] = df_display["Unit Price ($)"].map("${:.2f}".format)
    df_display["Total Revenue ($)"] = df_display["Total Revenue ($)"].map("${:.2f}".format)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    with st.expander("View Raw PDF Text"):
        st.code(revenue["raw_text"], language=None)

# ---------------------------------------------------------------------------
# Section 2 — Shanghai Drama Ticketholder List
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown('<div class="section-header">Shanghai Drama — Ticketholder List</div>', unsafe_allow_html=True)

cities = ticketholders["city"].nunique()
states = ticketholders["state"].nunique()
c1, c2, c3 = st.columns(3)
c1.metric("Total Patrons", len(ticketholders))
c2.metric("Cities Represented", cities)
c3.metric("States / Regions", states)

col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown('<div class="section-header">Patrons by City</div>', unsafe_allow_html=True)
    city_counts = ticketholders["city"].value_counts().reset_index()
    city_counts.columns = ["City", "Count"]
    fig_city = px.bar(
        city_counts,
        x="Count",
        y="City",
        orientation="h",
        color="Count",
        color_continuous_scale=[[0, "#1e3a5f"], [1, "#c8a96e"]],
        text="Count",
    )
    fig_city.update_traces(textposition="outside")
    fig_city.update_layout(
        plot_bgcolor="#0f0f1a",
        paper_bgcolor="#0f0f1a",
        font_color="#e0e0e0",
        coloraxis_showscale=False,
        margin=dict(l=10, r=40, t=10, b=10),
        xaxis=dict(gridcolor="#2d2d4a"),
        yaxis=dict(gridcolor="#2d2d4a"),
        height=300,
    )
    st.plotly_chart(fig_city, use_container_width=True)

with col_right:
    st.markdown('<div class="section-header">Patron Locations</div>', unsafe_allow_html=True)
    map_df = ticketholders.dropna(subset=["zip_code"]).copy()
    zip_counts = map_df["zip_code"].value_counts().reset_index()
    zip_counts.columns = ["zip_code", "count"]
    merged = map_df.merge(zip_counts, on="zip_code", how="left")
    merged_agg = (
        merged.groupby("zip_code")
        .agg(count=("count", "first"), city=("city", "first"))
        .reset_index()
    )
    fig_zip = px.scatter(
        merged_agg,
        x="zip_code",
        y="count",
        size="count",
        color="city",
        text="city",
        labels={"zip_code": "ZIP Code", "count": "Patrons"},
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig_zip.update_traces(textposition="top center")
    fig_zip.update_layout(
        plot_bgcolor="#0f0f1a",
        paper_bgcolor="#0f0f1a",
        font_color="#e0e0e0",
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(gridcolor="#2d2d4a", tickangle=-45),
        yaxis=dict(gridcolor="#2d2d4a", title="Patrons"),
        height=300,
    )
    st.plotly_chart(fig_zip, use_container_width=True)

st.markdown('<div class="section-header">Patron Directory</div>', unsafe_allow_html=True)
st.caption("Email addresses omitted for privacy.")
display_cols = ["patron_id", "display_name", "city", "state", "zip_code", "event_name"]
st.dataframe(
    ticketholders[display_cols].rename(columns={
        "patron_id": "Patron ID",
        "display_name": "Name",
        "city": "City",
        "state": "State",
        "zip_code": "ZIP",
        "event_name": "Event",
    }),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------------------------
# Section 3 — Will Call Batch Report
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown('<div class="section-header">Batch Ticket Report — Will Call</div>', unsafe_allow_html=True)

willcall_path = RealDataAgent.get_willcall_image_path()
try:
    st.image(willcall_path, caption="Source: Tessitura batch ticket export — Will Call list", use_container_width=True)
except Exception as e:
    st.warning(f"Could not load will-call image: {e}")
