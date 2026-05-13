"""
pages/10_Visitor_Flow.py
BAMPFA Audience Analytics — Cross-Visitation & Venue Traffic.

Answers the stated BAMPFA need: which patrons cross between films and
exhibitions, how engaged are they, and what does venue-level traffic
(Cinema vs galleries) look like by month and day of week.

All data is derived from real ticket transaction records — no simulation.
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
    page_title="Cross-Visitation | BAMPFA Analytics",
    page_icon="🔀",
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
    st.markdown("### Cross-Visitation Filters")
    st.markdown("---")
    year_options = list(range(2022, 2027))
    selected_year = st.selectbox("Year for venue traffic", options=year_options, index=3)
    st.markdown("---")
    st.caption("All data derived from ticket transaction records.")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>🔀 Cross-Visitation &amp; Venue Traffic</h2>
        <p>Which patrons attend both films and exhibitions? How loyal are they vs. single-program
           visitors? And how does Cinema traffic compare to gallery traffic month by month?</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

summary_df = agent.get_cross_visitation_summary()
monthly_df = agent.get_cross_visitation_by_month()
gallery_df = agent.get_gallery_traffic_by_month()
dow_df = agent.get_day_of_week_attendance()

SEGMENT_COLORS = {
    "Cross-Visitor (Art + Film)": "#c8a96e",
    "Art / Gallery Only":         "#5b8cdb",
    "Film Only":                   "#8fd36e",
}

# ---------------------------------------------------------------------------
# Section 1: Segment KPIs
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Visitor Segment Overview</div>', unsafe_allow_html=True)

total_patrons = summary_df["patrons"].sum()
seg_cols = st.columns(len(summary_df))

for i, (_, row) in enumerate(summary_df.iterrows()):
    share = row["patrons"] / total_patrons * 100
    with seg_cols[i]:
        st.metric(
            label=row["segment"],
            value=f"{row['patrons']:,}",
            delta=f"{share:.0f}% of all patrons",
        )

# ---------------------------------------------------------------------------
# Section 2: Engagement comparison
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Engagement by Segment</div>', unsafe_allow_html=True)
st.caption(
    "Cross-visitors — those who attend both gallery exhibitions and film programs — "
    "are BAMPFA's most engaged audience. Understanding this group shapes programming, "
    "marketing, and membership conversion strategy."
)

eng_col1, eng_col2 = st.columns(2)

with eng_col1:
    fig_visits = px.bar(
        summary_df,
        x="segment",
        y="avg_visits",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        text="avg_visits",
        labels={"segment": "", "avg_visits": "Avg visits per patron"},
        title="Average Visits per Patron",
        template="plotly_dark",
    )
    fig_visits.update_traces(texttemplate="%{text:.1f}×", textposition="outside")
    fig_visits.update_layout(
        paper_bgcolor="#1e1e30", plot_bgcolor="#141424",
        height=320, margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        xaxis=dict(tickfont=dict(size=10)),
    )
    st.plotly_chart(fig_visits, use_container_width=True)

with eng_col2:
    fig_spend = px.bar(
        summary_df,
        x="segment",
        y="avg_spend_per_visit",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        text="avg_spend_per_visit",
        labels={"segment": "", "avg_spend_per_visit": "Avg ticket spend per visit ($)"},
        title="Average Ticket Spend per Visit",
        template="plotly_dark",
    )
    fig_spend.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
    fig_spend.update_layout(
        paper_bgcolor="#1e1e30", plot_bgcolor="#141424",
        height=320, margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        xaxis=dict(tickfont=dict(size=10)),
    )
    st.plotly_chart(fig_spend, use_container_width=True)

# Summary table
display_summary = summary_df.copy()
display_summary["avg_ticket_price"] = display_summary["avg_ticket_price"].map("${:.2f}".format)
display_summary["avg_spend_per_visit"] = display_summary["avg_spend_per_visit"].map("${:.2f}".format)
display_summary["member_rate"] = display_summary["member_rate"].map("{:.1f}%".format)
display_summary["online_pct"] = display_summary["online_pct"].map("{:.1f}%".format)
display_summary["avg_visits"] = display_summary["avg_visits"].map("{:.1f}×".format)
display_summary.columns = [
    "Segment", "Patrons", "Avg Visits", "Avg Spend/Visit",
    "Member Rate", "Online %", "Avg Ticket Price",
]
st.dataframe(display_summary, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Section 3: Cross-visitation trend over time
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Monthly Visitor Count by Segment</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Track whether cross-visitation is growing relative to single-program attendance. "
    "A rising cross-visitor share indicates successful programming synergy."
)

fig_trend = px.area(
    monthly_df.sort_values(["year_month_str", "segment"]),
    x="year_month_str",
    y="quantity",
    color="segment",
    color_discrete_map=SEGMENT_COLORS,
    labels={"year_month_str": "Month", "quantity": "Visitors", "segment": "Segment"},
    title="Monthly Visitors by Segment (2022–2026)",
    template="plotly_dark",
)
fig_trend.update_layout(
    paper_bgcolor="#1e1e30", plot_bgcolor="#141424",
    hovermode="x unified",
    height=340, margin=dict(l=0, r=0, t=40, b=0),
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
)
st.plotly_chart(fig_trend, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 4: Venue (gallery) traffic — real data
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Venue Traffic — Cinema vs Galleries</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Visitor volume by venue from ticket transaction records. "
    "Cinema dominates by volume; G1 and G2 reflect gallery attendance."
)

year_gallery = gallery_df[gallery_df["year_month_str"].str.startswith(str(selected_year))]

GALLERY_COLORS = {
    "Cinema": "#5b8cdb",
    "G1": "#c8a96e",
    "G2": "#8fd36e",
    "Outdoor": "#e06c75",
}

gal_col1, gal_col2 = st.columns([3, 2])

with gal_col1:
    fig_gal = px.bar(
        year_gallery.sort_values("year_month_str"),
        x="year_month_str",
        y="quantity",
        color="gallery",
        barmode="stack",
        color_discrete_map=GALLERY_COLORS,
        labels={"year_month_str": "Month", "quantity": "Visitors", "gallery": "Venue"},
        title=f"Monthly Visitors by Venue ({selected_year})",
        template="plotly_dark",
    )
    fig_gal.update_layout(
        paper_bgcolor="#1e1e30", plot_bgcolor="#141424",
        hovermode="x unified",
        height=340, margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(tickangle=30, tickfont=dict(size=10)),
    )
    st.plotly_chart(fig_gal, use_container_width=True)

with gal_col2:
    all_gallery_totals = (
        gallery_df.groupby("gallery")["quantity"]
        .sum()
        .reset_index()
        .sort_values("quantity", ascending=False)
    )
    fig_pie = px.pie(
        all_gallery_totals,
        values="quantity",
        names="gallery",
        hole=0.45,
        color="gallery",
        color_discrete_map=GALLERY_COLORS,
        title="All-Time Visitor Split by Venue",
        template="plotly_dark",
    )
    fig_pie.update_layout(
        paper_bgcolor="#1e1e30",
        height=340, margin=dict(l=0, r=0, t=40, b=10),
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 5: Day-of-week attendance (real)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Average Visitors by Day of Week</div>',
    unsafe_allow_html=True,
)
st.caption("Derived from transaction event dates. Use for staffing and programming decisions.")

fig_dow = px.bar(
    dow_df,
    x="day_of_week",
    y="avg_visitors",
    color="avg_visitors",
    color_continuous_scale="YlOrBr",
    text="avg_visitors",
    labels={"day_of_week": "Day", "avg_visitors": "Avg visitors per day"},
    title="Average Daily Visitors by Day of Week",
    template="plotly_dark",
)
fig_dow.update_traces(texttemplate="%{text:.1f}", textposition="outside")
fig_dow.update_layout(
    paper_bgcolor="#1e1e30", plot_bgcolor="#141424",
    height=300, margin=dict(l=0, r=0, t=40, b=0),
    coloraxis_showscale=False, showlegend=False,
)
st.plotly_chart(fig_dow, use_container_width=True)

# ---------------------------------------------------------------------------
# Section 6: Programming implications
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Programming &amp; Marketing Implications</div>', unsafe_allow_html=True)

cross_row = summary_df[summary_df["segment"] == "Cross-Visitor (Art + Film)"].iloc[0]
art_row = summary_df[summary_df["segment"] == "Art / Gallery Only"].iloc[0]
film_row = summary_df[summary_df["segment"] == "Film Only"].iloc[0]

visit_lift = round(cross_row["avg_visits"] / film_row["avg_visits"], 1)
cross_share = round(cross_row["patrons"] / total_patrons * 100)

i1, i2, i3 = st.columns(3)

with i1:
    st.markdown(
        f"""
        <div class="insight-card">
            <div style="color:#c8a96e;font-size:0.72rem;font-weight:600;
                        text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.4rem;">
                Cross-Visitor Visit Lift</div>
            <div style="color:#e8c99a;font-size:1.8rem;font-weight:700;">{visit_lift}×</div>
            <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                more visits than film-only patrons. Programming film series that
                connect to current exhibitions is a proven loyalty driver.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with i2:
    st.markdown(
        f"""
        <div class="insight-card">
            <div style="color:#5b8cdb;font-size:0.72rem;font-weight:600;
                        text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.4rem;">
                Cross-Visitors as Share of Audience</div>
            <div style="color:#e8c99a;font-size:1.8rem;font-weight:700;">{cross_share}%</div>
            <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                of all patrons already attend both programs. Marketing that
                surfaces the film–exhibition connection can deepen this further.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with i3:
    film_only_count = int(film_row["patrons"])
    st.markdown(
        f"""
        <div class="insight-card">
            <div style="color:#8fd36e;font-size:0.72rem;font-weight:600;
                        text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.4rem;">
                Film-Only Conversion Opportunity</div>
            <div style="color:#e8c99a;font-size:1.8rem;font-weight:700;">{film_only_count:,}</div>
            <div style="color:#a0b4c8;font-size:0.82rem;margin-top:0.3rem;">
                film-only patrons have never visited the galleries. Targeted
                post-screening prompts and exhibition preview nights could
                convert them into cross-visitors.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
