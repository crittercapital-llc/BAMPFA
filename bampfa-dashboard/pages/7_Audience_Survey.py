"""
pages/7_Audience_Survey.py
2025 Audience Survey — full breakdown sourced from Individual responses sheet.
Organized to mirror BAMPFA's own Summary tab structure.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.real_data_agent import RealDataAgent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Audience Survey | BAMPFA Analytics",
    page_icon="📋",
    layout="wide",
)

_CSS = """
<style>
  html, body, [class*="css"] { font-family: 'Inter', 'Helvetica Neue', sans-serif; }
  [data-testid="stSidebar"] { background-color: #0f0f1a; }
  [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
  .page-header { background: linear-gradient(135deg, #1a1a2e, #0f3460);
      padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1rem; }
  .page-header h2 { color: #e8c99a; margin: 0; font-size: 1.6rem; }
  .page-header p  { color: #a0b4c8; margin: 0.3rem 0 0 0; font-size: 0.9rem; }
  .section-header { color: #c8a96e; font-size: 0.75rem; font-weight: 600;
      letter-spacing: 0.12em; text-transform: uppercase;
      border-bottom: 1px solid #2d2d4a; padding-bottom: 0.4rem;
      margin: 1.2rem 0 0.8rem 0; }
  [data-testid="metric-container"] { background: #1e1e30; border: 1px solid #2d2d4a;
      border-radius: 10px; padding: 1rem; }
  [data-testid="metric-container"] label { color: #a0b4c8 !important;
      font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
      color: #e8c99a !important; font-size: 1.9rem !important; font-weight: 700 !important; }
  #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

@st.cache_resource
def get_agent():
    return RealDataAgent()

s = get_agent().survey

GOLD  = "#c8a96e"
BLUE  = "#5b8cdb"
SCALE = [[0, "#1e3a5f"], [1, "#c8a96e"]]

def _hbar(df, x, y, height=None, text_col=None):
    """Horizontal bar chart with consistent dark styling."""
    fig = px.bar(
        df, x=x, y=y, orientation="h",
        text=text_col or x,
        color=x,
        color_continuous_scale=SCALE,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
        font_color="#e0e0e0", coloraxis_showscale=False,
        margin=dict(l=10, r=80, t=8, b=8),
        xaxis=dict(gridcolor="#2d2d4a"),
        yaxis=dict(gridcolor="#2d2d4a", autorange="reversed"),
        height=height or max(260, len(df) * 38),
    )
    return fig

def _vbar(df, x, y, height=300):
    fig = px.bar(
        df, x=x, y=y, text=y,
        color=y, color_continuous_scale=SCALE,
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
        font_color="#e0e0e0", coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=8, b=60),
        xaxis=dict(gridcolor="#2d2d4a", tickangle=-30),
        yaxis=dict(gridcolor="#2d2d4a"),
        height=height,
    )
    return fig

def _pie(df, names, values):
    fig = px.pie(df, names=names, values=values,
                 color_discrete_sequence=["#c8a96e","#0f3460","#2d7a2d",
                                          "#7a3d2d","#4a3d7a","#2d5a7a"])
    fig.update_traces(textinfo="label+percent", textfont_color="#e0e0e0")
    fig.update_layout(
        plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
        font_color="#e0e0e0", showlegend=False,
        margin=dict(l=10, r=10, t=8, b=8), height=300,
    )
    return fig

def _dict_to_df(d, label_col="label", count_col="count", sort=True):
    df = pd.DataFrame(list(d.items()), columns=[label_col, count_col])
    if sort:
        df = df.sort_values(count_col, ascending=True)
    return df

def _shorten(text, n=55):
    return text if len(text) <= n else text[:n] + "…"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """<div class="page-header">
      <h2>📋 2025 Audience Survey</h2>
      <p>1,147 respondents · April – May 2025 · Source: Individual responses tab</p>
    </div>""",
    unsafe_allow_html=True,
)
st.markdown(
    '<span style="background:#2d7a2d;color:white;padding:3px 10px;border-radius:4px;'
    'font-size:0.75rem;font-weight:600;">✓ REAL DATA — 1,147 respondents</span>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------

total = s.get("total_respondents", 0)
q4    = s.get("q4", {})
member_yes = sum(v for k, v in q4.items() if str(k).lower().startswith("yes"))
q14   = s.get("q14", {})
# NPS-style: treat 4-5 as promoters
promoters = sum(v for k, v in q14.items() if k in (4, 5))
nps_pct   = round(promoters / sum(q14.values()) * 100, 1) if q14 else 0
q27_avg   = s.get("q27_avg_precomputed", 0)

st.markdown("")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Respondents", f"{total:,}")
c2.metric("Current BAMPFA Members", f"{member_yes:,}")
c3.metric("Member Rate", f"{round(member_yes/total*100,1)}%")
c4.metric("Would Recommend (4–5 ★)", f"{nps_pct}%")
c5.metric("Family Film Interest", f"{q27_avg} / 10")

st.markdown("---")

# ---------------------------------------------------------------------------
# Tabs  (match BAMPFA Summary structure: Q1→Q31 in thematic groups)
# ---------------------------------------------------------------------------

tabs = st.tabs([
    "🏛️ Visitation",
    "👥 Membership",
    "📣 Discovery",
    "⭐ Experience",
    "🌆 Bay Area Scene",
    "👤 Demographics",
    "🌱 Community & Access",
    "👨‍👩‍👧 Families",
])

# ===========================  TAB 1: VISITATION  ===========================
with tabs[0]:
    st.markdown("### How audiences visit BAMPFA")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q1 — Gallery Visit Frequency</div>', unsafe_allow_html=True)
        order_q1 = [
            "4 or more times", "2 or 3 times", "Once",
            "It has been more than a year since I visited the galleries",
            "I have never visited BAMPFA’s art galleries",
        ]
        labels_q1 = ["4+ times", "2–3 times", "Once", "Over a year ago", "Never visited"]
        q1 = s.get("q1", {})
        df_q1 = pd.DataFrame({
            "label": labels_q1,
            "count": [q1.get(k, 0) for k in order_q1],
        }).query("count > 0").sort_values("count")
        st.plotly_chart(_hbar(df_q1, "count", "label"), use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Q2 — Film Screening Frequency</div>', unsafe_allow_html=True)
        order_q2 = [
            "10 or more times", "4–9 times", "2 or 3 times",
            "Once",
            "It has been more than a year since I attended a film screening",
            "I have never attended a film screening at BAMPFA",
        ]
        labels_q2 = ["10+ times", "4–9 times", "2–3 times", "Once", "Over a year ago", "Never"]
        q2 = s.get("q2", {})
        df_q2 = pd.DataFrame({
            "label": labels_q2,
            "count": [q2.get(k, 0) for k in order_q2],
        }).query("count > 0").sort_values("count")
        st.plotly_chart(_hbar(df_q2, "count", "label"), use_container_width=True)

    st.markdown('<div class="section-header">Q3 — Main Reasons for Visiting (select all that apply)</div>', unsafe_allow_html=True)
    q3 = s.get("q3", {})
    df_q3 = _dict_to_df(q3)
    df_q3["label"] = df_q3["label"].apply(_shorten)
    st.plotly_chart(_hbar(df_q3, "count", "label", height=300), use_container_width=True)
    st.caption("Respondents could select all that apply — totals exceed 1,147.")

# ===========================  TAB 2: MEMBERSHIP  ===========================
with tabs[1]:
    st.markdown("### BAMPFA membership status and tenure")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q4 — Current BAMPFA Member?</div>', unsafe_allow_html=True)
        def _q4_label(k):
            k = str(k).lower()
            if k.startswith("yes"):               return "Current member"
            if "used to be" in k:                 return "Lapsed member"
            if "thinking about" in k:             return "Considering joining"
            return "Not interested"
        q4_clean = {}
        for k, v in q4.items():
            lbl = _q4_label(k)
            q4_clean[lbl] = q4_clean.get(lbl, 0) + v
        df_q4 = pd.DataFrame(list(q4_clean.items()), columns=["status", "count"]).sort_values("count", ascending=False)
        st.plotly_chart(_pie(df_q4, "status", "count"), use_container_width=True)
        for _, row in df_q4.iterrows():
            pct = round(row["count"] / total * 100, 1)
            st.markdown(f"- **{row['status']}**: {row['count']:,} ({pct}%)")

    with col_r:
        st.markdown('<div class="section-header">Q5 — How Long as a Member? (current members only)</div>', unsafe_allow_html=True)
        order_q5 = ["Less than 1 year", "1-3 years", "3-5 years", "6-9 years", "10+ years"]
        q5 = s.get("q5", {})
        df_q5 = pd.DataFrame({
            "duration": [o for o in order_q5 if q5.get(o, 0) > 0],
            "count":    [q5.get(o, 0) for o in order_q5 if q5.get(o, 0) > 0],
        })
        st.plotly_chart(_vbar(df_q5, "duration", "count"), use_container_width=True)
        st.caption(f"n = {sum(q5.values()):,} current members answered")

# ===========================  TAB 3: DISCOVERY  ===========================
with tabs[2]:
    st.markdown("### How audiences discover BAMPFA")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q7 — How Did You First Hear About BAMPFA?</div>', unsafe_allow_html=True)
        q7 = s.get("q7", {})
        df_q7 = _dict_to_df(q7)
        df_q7["label"] = df_q7["label"].apply(lambda x: _shorten(x, 50))
        st.plotly_chart(_hbar(df_q7, "count", "label"), use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Q8 — How Do You Find Out About Programs? (select all)</div>', unsafe_allow_html=True)
        q8 = s.get("q8", {})
        df_q8 = _dict_to_df(q8)
        df_q8["label"] = df_q8["label"].str.replace("BAMPFA’s ", "", regex=False).apply(lambda x: _shorten(x, 40))
        st.plotly_chart(_hbar(df_q8, "count", "label"), use_container_width=True)
        st.caption("Select all that apply.")

    st.markdown('<div class="section-header">Q6 — UC Berkeley Affiliation</div>', unsafe_allow_html=True)
    q6 = s.get("q6", {})
    df_q6 = _dict_to_df(q6)
    df_q6["label"] = df_q6["label"].apply(lambda x: _shorten(x, 55))
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.plotly_chart(_hbar(df_q6, "count", "label", height=280), use_container_width=True)
    with col_b:
        st.markdown("&nbsp;")
        for _, row in df_q6.sort_values("count", ascending=False).iterrows():
            pct = round(row["count"] / total * 100, 1)
            st.markdown(f"**{pct}%** {row['label']}")

# ===========================  TAB 4: EXPERIENCE  ===========================
with tabs[3]:
    st.markdown("### What makes BAMPFA tick — strengths, gaps, and ideal visits")

    # Q9 and Q11 side by side
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q9 — What Does BAMPFA Do Well? (select all)</div>', unsafe_allow_html=True)
        q9 = s.get("q9", {})
        df_q9 = _dict_to_df(q9)
        df_q9["label"] = df_q9["label"].apply(lambda x: _shorten(x, 45))
        st.plotly_chart(_hbar(df_q9, "count", "label"), use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Q11 — What Could BAMPFA Improve? (select all)</div>', unsafe_allow_html=True)
        q11 = s.get("q11", {})
        df_q11 = _dict_to_df(q11)
        df_q11["label"] = df_q11["label"].apply(lambda x: _shorten(x, 45))
        st.plotly_chart(_hbar(df_q11, "count", "label"), use_container_width=True)

    st.markdown("---")

    # Q12 and Q14 side by side
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q12 — Barriers to Visiting More Often (select all)</div>', unsafe_allow_html=True)
        q12 = s.get("q12", {})
        df_q12 = _dict_to_df(q12)
        df_q12["label"] = df_q12["label"].apply(lambda x: _shorten(x, 50))
        st.plotly_chart(_hbar(df_q12, "count", "label"), use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Q14 — Likelihood to Recommend (1–5 scale)</div>', unsafe_allow_html=True)
        q14_data = s.get("q14", {})
        df_q14 = pd.DataFrame(
            [(f"{'★' * int(k)} ({int(k)})", v) for k, v in sorted(q14_data.items(), reverse=True)],
            columns=["rating", "count"],
        ).sort_values("count")
        fig_q14 = px.bar(
            df_q14, x="count", y="rating", orientation="h", text="count",
            color="count", color_continuous_scale=SCALE,
        )
        fig_q14.update_traces(textposition="outside", cliponaxis=False)
        fig_q14.update_layout(
            plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
            font_color="#e0e0e0", coloraxis_showscale=False,
            margin=dict(l=10, r=80, t=8, b=8),
            xaxis=dict(gridcolor="#2d2d4a"),
            yaxis=dict(gridcolor="#2d2d4a", autorange="reversed"),
            height=260,
        )
        st.plotly_chart(fig_q14, use_container_width=True)
        avg_rec = sum(int(k) * v for k, v in q14_data.items()) / sum(q14_data.values()) if q14_data else 0
        st.metric("Average Rating", f"{avg_rec:.2f} / 5")

    st.markdown("---")
    st.markdown('<div class="section-header">Q18 — Ideal BAMPFA Visit: What Matters Most? (select all)</div>', unsafe_allow_html=True)
    q18 = s.get("q18", {})
    df_q18 = _dict_to_df(q18)
    df_q18["label"] = df_q18["label"].apply(lambda x: _shorten(x, 70))
    st.plotly_chart(_hbar(df_q18, "count", "label", height=400), use_container_width=True)

# ===========================  TAB 5: BAY AREA SCENE  =======================
with tabs[4]:
    st.markdown("### Where else does BAMPFA's audience go in the Bay Area?")
    st.markdown('<div class="section-header">Q17 — Other Bay Area Cultural Institutions Visited (select all)</div>', unsafe_allow_html=True)

    q17 = s.get("q17", {})
    df_q17 = _dict_to_df(q17).sort_values("count", ascending=False)
    # Top 20 for readability; show rest in expander
    df_top20 = df_q17.head(20).sort_values("count")

    st.plotly_chart(_hbar(df_top20, "count", "label", height=580), use_container_width=True)
    st.caption(f"Showing top 20 of {len(df_q17)} institutions. Select all that apply.")

    with st.expander("View all institutions"):
        df_all = df_q17.copy().sort_values("count", ascending=False)
        df_all.columns = ["Institution", "Respondents"]
        df_all["% of Respondents"] = (df_all["Respondents"] / total * 100).round(1).astype(str) + "%"
        st.dataframe(df_all, use_container_width=True, hide_index=True)

# ===========================  TAB 6: DEMOGRAPHICS  ========================
with tabs[5]:
    st.markdown("### Who responds: age, gender, race/ethnicity, income, and politics")

    # Row 1: Age + Gender
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q21 — Age</div>', unsafe_allow_html=True)
        age_order = [
            "17 or younger", "18 to 21", "22 to 29", "30 to 39",
            "40 to 49", "50 to 54", "55 to 59", "60 to 64",
            "65 to 69", "70 or older",
        ]
        q21 = s.get("q21", {})
        df_age = pd.DataFrame({
            "age": [a for a in age_order if q21.get(a, 0) > 0],
            "count": [q21.get(a, 0) for a in age_order if q21.get(a, 0) > 0],
        })
        st.plotly_chart(_vbar(df_age, "age", "count", height=320), use_container_width=True)
        median_bracket = df_age.loc[df_age["count"].idxmax(), "age"] if len(df_age) else "—"
        st.caption(f"Most common bracket: **{median_bracket}** ({df_age['count'].max():,} respondents)")

    with col_r:
        st.markdown('<div class="section-header">Q22 — Gender Identity</div>', unsafe_allow_html=True)
        q22 = s.get("q22", {})
        df_q22 = pd.DataFrame(list(q22.items()), columns=["gender", "count"]).sort_values("count", ascending=False)
        st.plotly_chart(_pie(df_q22, "gender", "count"), use_container_width=True)
        for _, row in df_q22.iterrows():
            pct = round(row["count"] / total * 100, 1)
            st.markdown(f"- **{row['gender']}**: {row['count']:,} ({pct}%)")

    st.markdown("---")

    # Row 2: Race/ethnicity + LGBTQ
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q28 — Race / Ethnicity (select all)</div>', unsafe_allow_html=True)
        q28 = s.get("q28", {})
        df_q28 = _dict_to_df(q28)
        df_q28["pct"] = (df_q28["count"] / total * 100).round(1).astype(str) + "%"
        fig_q28 = px.bar(
            df_q28, x="count", y="label", orientation="h",
            text="pct", color="count", color_continuous_scale=SCALE,
        )
        fig_q28.update_traces(textposition="outside", cliponaxis=False)
        fig_q28.update_layout(
            plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
            font_color="#e0e0e0", coloraxis_showscale=False,
            margin=dict(l=10, r=80, t=8, b=8),
            xaxis=dict(gridcolor="#2d2d4a"),
            yaxis=dict(gridcolor="#2d2d4a", autorange="reversed"),
            height=340,
        )
        st.plotly_chart(fig_q28, use_container_width=True)
        st.caption("Respondents could select all that apply.")

    with col_r:
        st.markdown('<div class="section-header">Q29 — LGBTQ+ Community Member</div>', unsafe_allow_html=True)
        q29 = s.get("q29", {})
        df_q29 = pd.DataFrame(list(q29.items()), columns=["response", "count"])
        st.plotly_chart(_pie(df_q29, "response", "count"), use_container_width=True)
        lgbtq_count = q29.get("Yes", 0)
        st.metric("LGBTQ+ respondents", f"{lgbtq_count:,} ({round(lgbtq_count/total*100,1)}%)")

    st.markdown("---")

    # Row 3: Political views + Income
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q30 — Political Views</div>', unsafe_allow_html=True)
        pol_order = ["Very conservative", "Somewhat conservative", "Moderate",
                     "I don’t care about politics", "Somewhat liberal", "Very liberal"]
        q30 = s.get("q30", {})
        df_pol = pd.DataFrame({
            "view": [p for p in pol_order if q30.get(p, 0) > 0],
            "count": [q30.get(p, 0) for p in pol_order if q30.get(p, 0) > 0],
        })
        colors = ["#e06c75", "#e88c6a", "#c8a96e", "#888", "#5b8cdb", "#2d7a2d"]
        fig_pol = px.bar(
            df_pol, x="view", y="count", text="count",
            color="view",
            color_discrete_sequence=colors[:len(df_pol)],
        )
        fig_pol.update_traces(textposition="outside", cliponaxis=False)
        fig_pol.update_layout(
            plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
            font_color="#e0e0e0", showlegend=False,
            margin=dict(l=10, r=10, t=8, b=60),
            xaxis=dict(gridcolor="#2d2d4a", tickangle=-25),
            yaxis=dict(gridcolor="#2d2d4a"),
            height=320,
        )
        st.plotly_chart(fig_pol, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Q31 — Annual Household Income</div>', unsafe_allow_html=True)
        inc_order = [
            "Less than $35,000", "$35,000 to $49,000", "$50,000 to $74,999",
            "$75,000 to $99,999", "$100,000 to $149,000", "$150,000 to $199,999",
            "$200,000 or more", "I’m a full-time student", "I’m retired",
        ]
        q31 = s.get("q31", {})
        df_inc = pd.DataFrame({
            "bracket": [i for i in inc_order if q31.get(i, 0) > 0],
            "count":   [q31.get(i, 0) for i in inc_order if q31.get(i, 0) > 0],
        })
        st.plotly_chart(_vbar(df_inc, "bracket", "count", height=320), use_container_width=True)

# ===========================  TAB 7: COMMUNITY & ACCESS  ===================
with tabs[6]:
    st.markdown("### Equity, representation, and accessibility")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q19 — Importance of BAMPFA Leading on Race, Ethnicity & Equity</div>', unsafe_allow_html=True)
        imp_order = ["Very important", "Somewhat important", "Not very important",
                     "Not at all important", "Other (please specify)"]
        q19 = s.get("q19", {})
        df_q19 = pd.DataFrame({
            "importance": [i for i in imp_order if q19.get(i, 0) > 0],
            "count":      [q19.get(i, 0) for i in imp_order if q19.get(i, 0) > 0],
        })
        imp_colors = ["#2d7a2d", "#5b8cdb", "#c8a96e", "#e06c75", "#888"]
        fig_q19 = px.bar(
            df_q19, x="importance", y="count", text="count",
            color="importance",
            color_discrete_sequence=imp_colors[:len(df_q19)],
        )
        fig_q19.update_traces(textposition="outside", cliponaxis=False)
        fig_q19.update_layout(
            plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
            font_color="#e0e0e0", showlegend=False,
            margin=dict(l=10, r=10, t=8, b=80),
            xaxis=dict(gridcolor="#2d2d4a", tickangle=-20),
            yaxis=dict(gridcolor="#2d2d4a"),
            height=340,
        )
        st.plotly_chart(fig_q19, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Q15 — Accommodations Needed to Visit (select all)</div>', unsafe_allow_html=True)
        q15 = s.get("q15", {})
        df_q15 = _dict_to_df(q15)
        df_q15["label"] = df_q15["label"].apply(lambda x: _shorten(x, 50))
        st.plotly_chart(_hbar(df_q15, "count", "label", height=300), use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-header">Q23 — Where Do Respondents Live?</div>', unsafe_allow_html=True)

    cities = s.get("q23_cities", {})
    if cities:
        df_cities = pd.DataFrame(
            [(k, v) for k, v in cities.items()],
            columns=["City", "Count"],
        ).sort_values("Count", ascending=False).head(20).sort_values("Count")
        st.plotly_chart(_hbar(df_cities, "Count", "City", height=540), use_container_width=True)
        st.caption(f"Showing top 20 cities. {sum(cities.values()):,} total location responses.")

# ===========================  TAB 8: FAMILIES  ============================
with tabs[7]:
    st.markdown("### Family programs and children")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">Q25 — Parenting / Guardian Status (select all)</div>', unsafe_allow_html=True)
        q25 = s.get("q25", {})
        df_q25 = _dict_to_df(q25)
        df_q25["label"] = df_q25["label"].apply(lambda x: _shorten(x, 40))
        st.plotly_chart(_hbar(df_q25, "count", "label", height=260), use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">Q26 — Children\'s Age Ranges (select all)</div>', unsafe_allow_html=True)
        q26 = s.get("q26", {})
        df_q26 = _dict_to_df(q26)
        df_q26["label"] = df_q26["label"].apply(lambda x: _shorten(x, 40))
        st.plotly_chart(_hbar(df_q26, "count", "label", height=260), use_container_width=True)

    st.markdown('<div class="section-header">Q27 — Interest in Family Film Programs (0–10 scale)</div>', unsafe_allow_html=True)
    q27d = s.get("q27_dist", {})
    q27_avg = s.get("q27_avg_precomputed", 0)

    col_l, col_r = st.columns([3, 1])
    with col_l:
        if q27d:
            df_q27 = pd.DataFrame(
                [(k, v) for k, v in sorted(q27d.items())],
                columns=["Score", "Count"],
            )
            fig_q27 = px.bar(
                df_q27, x="Score", y="Count", text="Count",
                color="Score", color_continuous_scale=SCALE,
            )
            fig_q27.update_traces(textposition="outside", cliponaxis=False)
            fig_q27.update_layout(
                plot_bgcolor="#0f0f1a", paper_bgcolor="#0f0f1a",
                font_color="#e0e0e0", coloraxis_showscale=False,
                margin=dict(l=10, r=10, t=8, b=10),
                xaxis=dict(gridcolor="#2d2d4a", dtick=1, title="Score (0 = not interested, 10 = very interested)"),
                yaxis=dict(gridcolor="#2d2d4a"),
                height=300,
            )
            st.plotly_chart(fig_q27, use_container_width=True)
    with col_r:
        st.markdown("&nbsp;")
        st.metric("Average Interest", f"{q27_avg} / 10")
        n_answered = sum(q27d.values())
        st.metric("Answered", f"{n_answered:,}")
        st.caption(f"{round(n_answered/total*100,1)}% of respondents")
