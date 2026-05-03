"""
pages/6_Public_Sentiment.py
BAMPFA Audience Analytics — Public Sentiment & Earned Media page.

Sections:
  1. Data Source Status
  2. Press Coverage Timeline
  3. Press → Attendance Correlation (key analysis)
  4. Reddit & Social Chatter
  5. Google Reviews
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats  # for Pearson r; scipy is a plotly transitive dep

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent
from agents.public_data_agent import PublicDataAgent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Public Sentiment | BAMPFA Analytics",
    page_icon="🌐",
    layout="wide",
)

# ---------------------------------------------------------------------------
# CSS — dark museum theme (matches all other pages)
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: 'Inter', 'Helvetica Neue', sans-serif; }
      [data-testid="stSidebar"] { background-color: #0f0f1a; }
      [data-testid="stSidebar"] * { color: #e0e0e0 !important; }

      .page-header {
          background: linear-gradient(135deg, #1a1a2e, #0f3460);
          padding: 1.5rem 2rem; border-radius: 10px; margin-bottom: 1.5rem;
      }
      .page-header h2 { color: #e8c99a; margin: 0; font-size: 1.6rem; }
      .page-header p  { color: #a0b4c8; margin: 0.3rem 0 0 0; font-size: 0.9rem; }

      .section-header {
          color: #c8a96e; font-size: 0.75rem; font-weight: 600;
          letter-spacing: 0.12em; text-transform: uppercase;
          border-bottom: 1px solid #2d2d4a; padding-bottom: 0.4rem;
          margin: 1.5rem 0 1rem 0;
      }

      .insight-box {
          background: #141424; border: 1px solid #2d2d4a;
          border-left: 4px solid #c8a96e; border-radius: 8px; padding: 1rem 1.25rem;
          margin-bottom: 1rem;
      }
      .insight-box p { color: #d0d0e0; margin: 0; font-size: 0.9rem; }

      .review-card {
          background: #1e1e30; border: 1px solid #2d2d4a;
          border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem;
      }
      .review-card .stars { color: #c8a96e; font-size: 1.1rem; }
      .review-card .author { color: #a0b4c8; font-size: 0.78rem; margin-top: 0.3rem; }
      .review-card .text { color: #d0d0e0; font-size: 0.88rem; margin-top: 0.4rem; }

      #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Chart theme constants
# ---------------------------------------------------------------------------

CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#1e1e30",
    plot_bgcolor="#141424",
    margin=dict(l=0, r=0, t=40, b=0),
)
SENTIMENT_COLORS = {
    "positive": "#98c379",
    "neutral":  "#e5c07b",
    "negative": "#e06c75",
}
GOLD    = "#c8a96e"
BLUE    = "#5b8cdb"
RED     = "#e06c75"
GREEN   = "#98c379"

# ---------------------------------------------------------------------------
# Load data (cached)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_data_agent() -> DataAgent:
    return DataAgent()

@st.cache_resource
def get_public_agent() -> PublicDataAgent:
    return PublicDataAgent()

@st.cache_data(ttl=3600, show_spinner="Fetching press coverage…")
def load_press_coverage() -> pd.DataFrame:
    return get_public_agent().get_all_press_coverage()

@st.cache_data(ttl=3600, show_spinner="Fetching Reddit mentions…")
def load_reddit() -> pd.DataFrame:
    return get_public_agent().get_reddit_mentions()

@st.cache_data(ttl=3600, show_spinner="Fetching Google reviews…")
def load_reviews() -> pd.DataFrame:
    return get_public_agent().get_google_reviews()

@st.cache_data(ttl=3600)
def load_press_timeline() -> pd.DataFrame:
    return get_public_agent().get_press_timeline()

@st.cache_data(ttl=3600)
def load_source_status() -> dict:
    return get_public_agent().get_source_status()

data_agent   = get_data_agent()
public_agent = get_public_agent()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>Public Sentiment &amp; Earned Media</h2>
        <p>Press coverage, Reddit chatter, Google reviews, and attendance correlation analysis.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# SECTION 1: Data Source Status
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Data Source Status</div>', unsafe_allow_html=True)

status = load_source_status()
label_map = {
    "reddit":          "Reddit (PRAW)",
    "google_news_rss": "Google News RSS",
    "newsapi":         "NewsAPI.org",
    "google_reviews":  "Google Reviews (Places API)",
}

status_cols = st.columns(len(status))
for col, (key, val) in zip(status_cols, status.items()):
    with col:
        label = label_map.get(key, key)
        if val == "live":
            st.success(f"**{label}**\n\nLive data", icon="🟢")
        else:
            st.warning(f"**{label}**\n\nDemo mode", icon="🟡")

st.caption(
    "Demo mode uses realistic synthetic data. "
    "Add credentials to `.env` to activate live feeds. "
    "Google News RSS is always live (no key required)."
)

# ---------------------------------------------------------------------------
# SECTION 2: Press Coverage Timeline
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Press Coverage Timeline</div>', unsafe_allow_html=True)

press_df = load_press_coverage()
timeline_df = load_press_timeline()

if press_df.empty:
    st.info("No press data available.")
else:
    # --- Line chart: monthly article count ---
    if not timeline_df.empty:
        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Scatter(
            x=timeline_df["year_month_str"],
            y=timeline_df["article_count"],
            mode="lines+markers",
            name="Articles / month",
            line=dict(color=BLUE, width=2),
            marker=dict(size=5, color=BLUE),
            fill="tozeroy",
            fillcolor="rgba(91,140,219,0.12)",
        ))
        fig_timeline.update_layout(
            title="Monthly Press Article Count",
            xaxis_title="Month",
            yaxis_title="Articles",
            xaxis=dict(tickangle=45, tickfont=dict(size=10)),
            **CHART_LAYOUT,
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

    # --- Bar chart: articles by publication ---
    source_counts = (
        press_df.groupby("source")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(15)
    )
    fig_sources = px.bar(
        source_counts,
        x="count",
        y="source",
        orientation="h",
        title="Articles by Publication (Top 15)",
        color="count",
        color_continuous_scale=[[0, "#1e2a3a"], [1, BLUE]],
        labels={"count": "Articles", "source": "Publication"},
    )
    fig_sources.update_layout(
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False,
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig_sources, use_container_width=True)

    # --- Table: 20 most recent articles ---
    st.markdown("**Most Recent 20 Articles**")
    recent_press = press_df.head(20).copy()
    recent_press["date"] = pd.to_datetime(recent_press["date"]).dt.strftime("%Y-%m-%d")
    recent_press["sentiment_badge"] = recent_press["sentiment"].map({
        "positive": "✅ positive",
        "neutral":  "➖ neutral",
        "negative": "🔴 negative",
    }).fillna("➖ neutral")

    st.dataframe(
        recent_press[["date", "title", "source", "sentiment_badge", "url"]].rename(columns={
            "date":           "Date",
            "title":          "Title",
            "source":         "Publication",
            "sentiment_badge": "Sentiment",
            "url":            "Link",
        }),
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="Open ↗"),
        },
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# SECTION 3: Press → Attendance Correlation (KEY SECTION)
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Press Coverage → Attendance Correlation</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="insight-box"><p>'
    "This section examines whether months with higher press article counts are followed "
    "by higher attendance. The analysis shows both same-month and 1-month-lagged "
    "correlations. <strong>Note: correlation is not causation</strong> — other factors "
    "(exhibitions, seasonality, events) also influence attendance."
    "</p></div>",
    unsafe_allow_html=True,
)

# --- Build attendance time series ---
attendance_monthly = (
    data_agent.transactions
    .groupby("year_month")["quantity"]
    .sum()
    .reset_index()
)
attendance_monthly["year_month_str"] = attendance_monthly["year_month"].astype(str)
attendance_monthly = attendance_monthly.sort_values("year_month_str")

# --- Merge with press timeline ---
if timeline_df.empty:
    st.info("Not enough press data for correlation analysis.")
else:
    merged = attendance_monthly.merge(timeline_df, on="year_month_str", how="inner")

    # 1-month lagged press count: articles from previous month
    merged_sorted = merged.sort_values("year_month_str").reset_index(drop=True)
    merged_sorted["article_count_lag1"] = merged_sorted["article_count"].shift(1)

    merged_valid    = merged_sorted.dropna(subset=["article_count"])
    merged_lag_valid = merged_sorted.dropna(subset=["article_count_lag1"])

    # Pearson correlations
    r_same, p_same = (np.nan, np.nan)
    r_lag,  p_lag  = (np.nan, np.nan)
    if len(merged_valid) >= 3:
        r_same, p_same = stats.pearsonr(
            merged_valid["article_count"],
            merged_valid["quantity"],
        )
    if len(merged_lag_valid) >= 3:
        r_lag, p_lag = stats.pearsonr(
            merged_lag_valid["article_count_lag1"],
            merged_lag_valid["quantity"],
        )

    # Correlation metrics display
    corr_col1, corr_col2, corr_col3 = st.columns(3)
    with corr_col1:
        st.metric(
            "Same-Month Pearson r",
            f"{r_same:.3f}" if not np.isnan(r_same) else "n/a",
            help="Correlation between article count and attendance in the same month",
        )
    with corr_col2:
        st.metric(
            "1-Month Lag Pearson r",
            f"{r_lag:.3f}" if not np.isnan(r_lag) else "n/a",
            help="Correlation between last month's article count and this month's attendance",
        )
    with corr_col3:
        n_months = len(merged_valid)
        st.metric("Months of Overlap", f"{n_months}", help="Data points used in correlation")

    # --- Dual-axis chart: bars = attendance, lines = press count ---
    fig_dual = go.Figure()

    # Attendance bars
    fig_dual.add_trace(go.Bar(
        x=merged_sorted["year_month_str"],
        y=merged_sorted["quantity"],
        name="Attendance",
        marker_color="rgba(200,169,110,0.5)",
        yaxis="y1",
    ))
    # Same-month press line
    fig_dual.add_trace(go.Scatter(
        x=merged_sorted["year_month_str"],
        y=merged_sorted["article_count"],
        name="Press Articles (same month)",
        mode="lines+markers",
        line=dict(color=BLUE, width=2),
        marker=dict(size=5),
        yaxis="y2",
    ))
    # 1-month lag press line
    fig_dual.add_trace(go.Scatter(
        x=merged_sorted["year_month_str"],
        y=merged_sorted["article_count_lag1"],
        name="Press Articles (prior month)",
        mode="lines",
        line=dict(color=GREEN, width=1.5, dash="dot"),
        yaxis="y2",
    ))

    fig_dual.update_layout(
        title="Attendance vs. Press Coverage (dual axis)",
        xaxis=dict(title="Month", tickangle=45, tickfont=dict(size=9)),
        yaxis=dict(title="Attendance (visitors)", titlefont=dict(color=GOLD)),
        yaxis2=dict(
            title="Article Count",
            titlefont=dict(color=BLUE),
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", y=1.08, x=0),
        hovermode="x unified",
        **CHART_LAYOUT,
    )
    st.plotly_chart(fig_dual, use_container_width=True)

    # --- Scatter: x = article count, y = attendance (same month) ---
    if len(merged_valid) >= 3:
        fig_scatter = px.scatter(
            merged_valid,
            x="article_count",
            y="quantity",
            trendline="ols",
            title="Press Coverage vs. Attendance (scatter + trend line)",
            labels={"article_count": "Articles Published (month)", "quantity": "Visitors"},
            hover_data=["year_month_str"],
            color_discrete_sequence=[BLUE],
        )
        fig_scatter.update_traces(
            selector=dict(mode="markers"),
            marker=dict(size=8, opacity=0.75),
        )
        # Trendline color
        fig_scatter.update_traces(
            selector=dict(mode="lines"),
            line=dict(color=GOLD, width=2, dash="dash"),
        )
        fig_scatter.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Correlation interpretation callout
    if not np.isnan(r_same):
        strength = "strong" if abs(r_same) > 0.6 else ("moderate" if abs(r_same) > 0.3 else "weak")
        direction = "positive" if r_same > 0 else "negative"
        st.markdown(
            f'<div class="insight-box"><p>'
            f"The same-month Pearson r = {r_same:.3f} indicates a <strong>{strength} {direction}</strong> "
            f"correlation between press article counts and attendance. "
            f"The 1-month lagged r = {r_lag:.3f} tests whether last month's press "
            f"coverage predicts this month's attendance — potentially more useful for planning. "
            f"<em>Reminder: this is observational. Confounders include major exhibitions, "
            f"seasonality, and UC Berkeley academic calendar.</em>"
            f"</p></div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# SECTION 4: Reddit & Social Chatter
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Reddit &amp; Social Chatter</div>', unsafe_allow_html=True)

# TODO: Add Twitter/X mentions section once Academic Research API credentials
#       are available. Use snscrape or the v2 search endpoint.
# TODO: Add Instagram mentions via Meta Graph API basic display / hashtag search.

reddit_df = load_reddit()

if reddit_df.empty:
    st.info("No Reddit data available.")
else:
    # Top-line metrics
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    with r_col1:
        st.metric("Total Mentions", f"{len(reddit_df):,}")
    with r_col2:
        st.metric("Avg Upvote Score", f"{reddit_df['score'].mean():.1f}")
    with r_col3:
        top_sub = reddit_df["subreddit"].value_counts().idxmax()
        st.metric("Top Subreddit", f"r/{top_sub}")
    with r_col4:
        pct_positive = (reddit_df["sentiment"] == "positive").mean() * 100
        st.metric("% Positive", f"{pct_positive:.0f}%")

    reddit_chart_col1, reddit_chart_col2 = st.columns(2)

    with reddit_chart_col1:
        # Bar chart: mentions by subreddit
        sub_counts = (
            reddit_df.groupby("subreddit")
            .size()
            .reset_index(name="mentions")
            .sort_values("mentions", ascending=False)
        )
        fig_sub = px.bar(
            sub_counts,
            x="subreddit",
            y="mentions",
            title="Mentions by Subreddit",
            color="mentions",
            color_continuous_scale=[[0, "#1e2a3a"], [1, BLUE]],
            labels={"subreddit": "Subreddit", "mentions": "Posts"},
        )
        fig_sub.update_layout(coloraxis_showscale=False, **CHART_LAYOUT)
        st.plotly_chart(fig_sub, use_container_width=True)

    with reddit_chart_col2:
        # Sentiment donut
        sent_counts = reddit_df["sentiment"].value_counts().reset_index()
        sent_counts.columns = ["sentiment", "count"]
        fig_donut = px.pie(
            sent_counts,
            names="sentiment",
            values="count",
            title="Sentiment Distribution",
            hole=0.52,
            color="sentiment",
            color_discrete_map=SENTIMENT_COLORS,
        )
        fig_donut.update_traces(textposition="outside", textinfo="percent+label")
        fig_donut.update_layout(showlegend=False, **CHART_LAYOUT)
        st.plotly_chart(fig_donut, use_container_width=True)

    # Table: top 20 posts by score
    st.markdown("**Top 20 Reddit Posts by Upvote Score**")
    top_posts = reddit_df.nlargest(20, "score").copy()
    top_posts["date"] = pd.to_datetime(top_posts["date"]).dt.strftime("%Y-%m-%d")
    top_posts["sentiment_badge"] = top_posts["sentiment"].map({
        "positive": "✅ positive",
        "neutral":  "➖ neutral",
        "negative": "🔴 negative",
    }).fillna("➖ neutral")

    st.dataframe(
        top_posts[["subreddit", "date", "title", "score", "num_comments", "sentiment_badge", "url"]].rename(columns={
            "subreddit":       "Subreddit",
            "date":            "Date",
            "title":           "Title",
            "score":           "Score",
            "num_comments":    "Comments",
            "sentiment_badge": "Sentiment",
            "url":             "Link",
        }),
        column_config={
            "Link": st.column_config.LinkColumn("Link", display_text="Open ↗"),
        },
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# SECTION 5: Google Reviews
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Google Reviews</div>', unsafe_allow_html=True)

review_source_status = status.get("google_reviews", "demo")
if review_source_status == "demo":
    st.info(
        "Google Reviews are in **demo mode** (no Places API key). "
        "The Places API returns at most **5 reviews** per query — a platform limitation. "
        "For comprehensive review data, consider a third-party aggregator or direct "
        "Google Business Profile export.",
        icon="ℹ️",
    )

reviews_df = load_reviews()

if reviews_df.empty:
    st.info("No review data available.")
else:
    # Metrics
    rev_col1, rev_col2, rev_col3 = st.columns(3)
    with rev_col1:
        avg_r = reviews_df["rating"].mean()
        stars_display = "★" * round(avg_r) + "☆" * (5 - round(avg_r))
        st.metric("Average Rating", f"{avg_r:.2f} / 5.0", help="Based on available reviews")
    with rev_col2:
        five_star_pct = (reviews_df["rating"] == 5).mean() * 100
        st.metric("5-Star Reviews", f"{five_star_pct:.0f}%")
    with rev_col3:
        st.metric("Total Reviews", f"{len(reviews_df):,}")

    # Rating distribution
    rating_counts = (
        reviews_df["rating"]
        .value_counts()
        .reindex([5, 4, 3, 2, 1], fill_value=0)
        .reset_index()
    )
    rating_counts.columns = ["rating", "count"]
    rating_counts["stars"] = rating_counts["rating"].apply(lambda r: "★" * r + "☆" * (5 - r))

    star_colors = {5: GREEN, 4: "#7ec8a0", 3: "#e5c07b", 2: "#e09c68", 1: RED}
    rating_counts["color"] = rating_counts["rating"].map(star_colors)

    fig_ratings = px.bar(
        rating_counts,
        x="rating",
        y="count",
        title="Rating Distribution",
        labels={"rating": "Stars", "count": "Reviews"},
        color="rating",
        color_discrete_map={r: c for r, c in star_colors.items()},
        category_orders={"rating": [5, 4, 3, 2, 1]},
    )
    fig_ratings.update_layout(showlegend=False, **CHART_LAYOUT)
    st.plotly_chart(fig_ratings, use_container_width=True)

    # Recent reviews as styled cards
    st.markdown("**Recent Reviews**")
    recent_reviews = reviews_df.sort_values("date", ascending=False).head(10)

    for _, row in recent_reviews.iterrows():
        rating_val = int(row.get("rating", 3))
        stars_str = "★" * rating_val + "☆" * (5 - rating_val)
        date_str = pd.Timestamp(row["date"]).strftime("%b %d, %Y") if pd.notna(row["date"]) else ""
        text = row.get("text", "")
        author = row.get("author", "Anonymous")
        st.markdown(
            f"""
            <div class="review-card">
                <div class="stars">{stars_str} &nbsp;<small style="color:#a0b4c8;font-size:0.8rem;">{date_str}</small></div>
                <div class="text">{text}</div>
                <div class="author">— {author}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
