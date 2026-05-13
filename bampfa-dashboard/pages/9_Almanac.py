"""
pages/9_Almanac.py
BAMPFA Audience Analytics — Almanac: unified planning calendar.

Inspired by Dexibit's Almanac feature: layers exhibitions, public holidays,
school terms, and historical attendance context into a single planning view
so the team can anticipate visitation, plan programming, and forecast impact.
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
    page_title="Almanac | BAMPFA Analytics",
    page_icon="📅",
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
      .context-card { background: #1e1e30; border: 1px solid #2d2d4a; border-radius: 8px;
          padding: 1rem; margin-bottom: 0.5rem; }
      .badge-break { background: #3a5c2a; color: #8fd36e; padding: 2px 8px;
          border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
      .badge-term { background: #1e3a5c; color: #6ea8e0; padding: 2px 8px;
          border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
      .badge-holiday { background: #5c3a1e; color: #e0a86e; padding: 2px 8px;
          border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
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
    st.markdown("### Almanac Filters")
    st.markdown("---")
    show_holidays = st.checkbox("Show Public Holidays", value=True)
    show_school = st.checkbox("Show School Terms / Breaks", value=True)
    show_exhibitions = st.checkbox("Show Exhibitions (Art)", value=True)
    show_films = st.checkbox("Show Film Programs", value=True)
    st.markdown("---")

    years = list(range(2022, 2027))
    selected_year = st.selectbox("Focus Year", options=years, index=3)

    st.markdown("---")
    st.caption("School terms: BUSD/OUSD schedule (approximate)")
    st.caption("Holidays: US federal calendar")
    st.caption("⚠ Demo data — attendance simulated")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>📅 Almanac — Planning Calendar</h2>
        <p>Layer exhibitions, school terms, public holidays, and attendance context
           into a unified planning view. Anticipate demand, optimize programming, and
           inform your marketing calendar.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load calendar data
# ---------------------------------------------------------------------------

terms = agent.get_bay_area_school_terms()
holidays = agent.get_public_holidays()
impact_df = agent.get_holiday_attendance_impact()
footprint_df = agent.get_program_monthly_footprint()

# ---------------------------------------------------------------------------
# Section 1: Program Activity Heatmap (month × program, based on ticket sales)
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Program Activity by Month — Ticket Sales Footprint</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Which programs had ticket sales in each month? This is what the transaction "
    "data can reliably tell us. Darker = more visitors that month."
)

cat_filter = []
if show_exhibitions:
    cat_filter.append("Art")
if show_films:
    cat_filter.append("Film")

year_footprint = footprint_df[
    footprint_df["year_month_str"].str.startswith(str(selected_year))
    & footprint_df["event_category"].isin(cat_filter if cat_filter else ["Art", "Film"])
].copy()

if not year_footprint.empty:
    pivot = year_footprint.pivot_table(
        index="event_name",
        columns="year_month_str",
        values="quantity",
        aggfunc="sum",
    ).fillna(0)

    # Sort programs by total visitors so the busiest are at the top
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    # Truncate long names for display
    pivot.index = [n[:38] + "…" if len(n) > 38 else n for n in pivot.index]

    fig_foot = px.imshow(
        pivot,
        color_continuous_scale="YlOrBr",
        labels=dict(x="Month", y="Program", color="Visitors"),
        title=f"Program Ticket Sales by Month ({selected_year})",
        template="plotly_dark",
        aspect="auto",
    )
    fig_foot.update_layout(
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        height=max(360, len(pivot) * 22 + 80),
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(tickangle=30, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
        coloraxis_colorbar=dict(title="Visitors"),
    )
    st.plotly_chart(fig_foot, use_container_width=True)
    st.caption(
        "Each cell = visitor count from ticket sales in that month. "
        "Empty = no ticket records for that program that month."
    )
else:
    st.info("Select at least one program type in the sidebar.")

# ---------------------------------------------------------------------------
# Section 2: Monthly Attendance with Context Overlay
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Monthly Attendance by School Calendar Context</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Attendance grouped by whether the month falls during a school break, "
    "school term, or mixed period. School breaks historically drive higher "
    "family / youth group attendance."
)

year_impact = impact_df[
    impact_df["year_month_str"].str.startswith(str(selected_year))
].copy()

if not year_impact.empty:
    context_colors = {
        "school_break": "#8fd36e",
        "school_term": "#5b8cdb",
        "mixed": "#c8a96e",
    }
    # Map labels
    context_labels = {
        "school_break": "School Break",
        "school_term": "School Term",
        "mixed": "Mixed",
    }
    year_impact["context_label"] = year_impact["context"].map(
        lambda c: context_labels.get(c, c)
    )
    year_impact["bar_color"] = year_impact["context"].map(
        lambda c: context_colors.get(c, "#888")
    )

    fig_ctx = go.Figure()
    for ctx, grp in year_impact.groupby("context"):
        fig_ctx.add_trace(go.Bar(
            x=grp["year_month_str"],
            y=grp["quantity"],
            name=context_labels.get(ctx, ctx),
            marker_color=context_colors.get(ctx, "#888"),
        ))

    fig_ctx.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1e1e30",
        plot_bgcolor="#141424",
        barmode="stack",
        hovermode="x unified",
        height=320,
        margin=dict(l=0, r=0, t=30, b=0),
        xaxis=dict(tickangle=30, tickfont=dict(size=10)),
        yaxis_title="Visitors",
        legend_title_text="School Context",
    )
    st.plotly_chart(fig_ctx, use_container_width=True)

    # Context summary KPIs
    ctx_summary = year_impact.groupby("context")["quantity"].agg(["mean", "sum"]).round(0)
    if not ctx_summary.empty:
        k_cols = st.columns(len(ctx_summary))
        for i, (ctx, row) in enumerate(ctx_summary.iterrows()):
            label = context_labels.get(ctx, ctx)
            with k_cols[i]:
                st.metric(
                    label=f"Avg Monthly Visitors — {label}",
                    value=f"{int(row['mean']):,}",
                    delta=None,
                )

# ---------------------------------------------------------------------------
# Section 3: All-Year Attendance vs Holiday / Break Calendar
# ---------------------------------------------------------------------------

st.markdown(
    '<div class="section-header">Full-Range Attendance with Calendar Context Overlay</div>',
    unsafe_allow_html=True,
)

all_impact = impact_df.copy()
fig_all = go.Figure()

fig_all.add_trace(go.Bar(
    x=all_impact["year_month_str"],
    y=all_impact["quantity"],
    name="Monthly Visitors",
    marker_color=[
        "#8fd36e" if c == "school_break" else
        ("#5b8cdb" if c == "school_term" else "#c8a96e")
        for c in all_impact["context"]
    ],
))

fig_all.update_layout(
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    title="Monthly Attendance Jan 2022 – Apr 2026 (colored by school calendar context)",
    hovermode="x unified",
    height=340,
    margin=dict(l=0, r=0, t=50, b=0),
    xaxis=dict(tickangle=45, tickfont=dict(size=9)),
    yaxis_title="Visitors",
    showlegend=False,
)
st.plotly_chart(fig_all, use_container_width=True)
st.caption(
    "🟢 Green = school break month  |  🔵 Blue = school term month  |  🟡 Gold = mixed/transition"
)

# ---------------------------------------------------------------------------
# Section 4: Upcoming Events & Holiday Table
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Upcoming Context Events</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📚 School Calendar", "🏛️ Public Holidays", "🖼️ Active Programs"])

with tab1:
    term_rows = []
    for t in terms:
        s = pd.Timestamp(t["start"])
        e = pd.Timestamp(t["end"])
        if s.year >= selected_year or e.year >= selected_year:
            badge = "school_break" if t["type"] == "school_break" else "school_term"
            label = "🏖 Break" if t["type"] == "school_break" else "📖 Term"
            duration = (e - s).days + 1
            term_rows.append({
                "Period": f"{label} {t['name']}",
                "Start": s.strftime("%b %d, %Y"),
                "End": e.strftime("%b %d, %Y"),
                "Duration (days)": duration,
            })
    if term_rows:
        st.dataframe(pd.DataFrame(term_rows[:20]), use_container_width=True, hide_index=True)

with tab2:
    hol_year = [h for h in holidays if str(selected_year) in h["date"]]
    hol_df = pd.DataFrame([
        {"Holiday": h["name"], "Date": pd.Timestamp(h["date"]).strftime("%b %d, %Y")}
        for h in sorted(hol_year, key=lambda x: x["date"])
    ])
    if not hol_df.empty:
        st.dataframe(hol_df, use_container_width=True, hide_index=True)

with tab3:
    if not year_footprint.empty:
        prog_summary = (
            year_footprint.groupby(["event_name", "event_category"])
            .agg(
                active_months=("year_month_str", "nunique"),
                total_visitors=("quantity", "sum"),
            )
            .reset_index()
            .sort_values("total_visitors", ascending=False)
        )
        prog_summary.columns = ["Program", "Category", "Active Months", "Total Visitors"]
        st.dataframe(prog_summary, use_container_width=True, hide_index=True)
        st.caption(
            "Active Months = months with ticket sales in the selected year. "
            "Actual run dates require a direct programming calendar export."
        )
    else:
        st.info(f"No program data found for {selected_year}.")

# ---------------------------------------------------------------------------
# Section 5: Planning Insight Summary
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Almanac Planning Insights</div>', unsafe_allow_html=True)

break_avg = all_impact[all_impact["context"] == "school_break"]["quantity"].mean()
term_avg = all_impact[all_impact["context"] == "school_term"]["quantity"].mean()
lift_pct = round((break_avg - term_avg) / term_avg * 100, 1) if term_avg else 0

ins_col1, ins_col2, ins_col3 = st.columns(3)

with ins_col1:
    st.markdown(
        f"""
        <div class="context-card">
            <div style="color:#8fd36e;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.1em;margin-bottom:0.3rem;">School Break Uplift</div>
            <div style="color:#e8c99a;font-size:1.8rem;font-weight:700;">+{lift_pct}%</div>
            <div style="color:#a0b4c8;font-size:0.82rem;">average monthly attendance during
            school breaks vs. school term months</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with ins_col2:
    peak_month = all_impact.loc[all_impact["quantity"].idxmax(), "year_month_str"]
    peak_val = all_impact["quantity"].max()
    st.markdown(
        f"""
        <div class="context-card">
            <div style="color:#c8a96e;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.1em;margin-bottom:0.3rem;">All-Time Peak Month</div>
            <div style="color:#e8c99a;font-size:1.8rem;font-weight:700;">{peak_month}</div>
            <div style="color:#a0b4c8;font-size:0.82rem;">{int(peak_val):,} visitors — plan
            staffing, marketing, and operations accordingly</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with ins_col3:
    holiday_count = len([h for h in holidays if str(selected_year) in h["date"]])
    st.markdown(
        f"""
        <div class="context-card">
            <div style="color:#e0a86e;font-size:0.72rem;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.1em;margin-bottom:0.3rem;">Public Holidays in {selected_year}</div>
            <div style="color:#e8c99a;font-size:1.8rem;font-weight:700;">{holiday_count}</div>
            <div style="color:#a0b4c8;font-size:0.82rem;">federal holidays affecting operating
            hours, staffing, and expected walk-up traffic patterns</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
