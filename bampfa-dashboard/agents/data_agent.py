"""
agents/data_agent.py
DataAgent: loads and processes all BAMPFA CSV data, exposing clean DataFrames
for the Streamlit dashboard pages.

TODO: Replace CSV loads with Tesitura API calls or database queries when live
      data infrastructure is available.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# Resolve the data directory relative to this file so it works from any cwd.
_DATA_DIR = Path(__file__).parent.parent / "data"


class DataAgent:
    """
    Loads all CSV sources and exposes analysis methods.
    Uses st.cache_data so Streamlit only reads from disk once per session.
    """

    def __init__(self):
        self.transactions = self._load_transactions()
        self.members = self._load_members()
        self.web_traffic = self._load_web_traffic()
        self.reviews = self._load_reviews()

    # ------------------------------------------------------------------
    # Private loaders (cached)
    # ------------------------------------------------------------------

    @staticmethod
    @st.cache_data(show_spinner="Loading transactions...")
    def _load_transactions() -> pd.DataFrame:
        # TODO: Replace with Tesitura transaction export or ticketing API
        path = _DATA_DIR / "transactions.csv"
        df = pd.read_csv(path, parse_dates=["transaction_date", "event_date"])
        df["year_month"] = df["event_date"].dt.to_period("M")
        df["year"] = df["event_date"].dt.year
        df["month"] = df["event_date"].dt.month
        df["week"] = df["event_date"].dt.isocalendar().week.astype(int)
        df["day_of_week"] = df["event_date"].dt.day_name()
        df["revenue"] = df["ticket_price"] * df["quantity"]
        return df

    @staticmethod
    @st.cache_data(show_spinner="Loading members...")
    def _load_members() -> pd.DataFrame:
        # TODO: Replace with Tesitura membership roster export
        path = _DATA_DIR / "members.csv"
        df = pd.read_csv(path, parse_dates=["join_date", "lapse_date", "last_visit_date"])
        df["is_active"] = df["lapse_date"].isna()
        df["join_year_month"] = df["join_date"].dt.to_period("M")
        return df

    @staticmethod
    @st.cache_data(show_spinner="Loading web traffic...")
    def _load_web_traffic() -> pd.DataFrame:
        # TODO: Replace with Google Analytics 4 API export
        path = _DATA_DIR / "web_traffic.csv"
        df = pd.read_csv(path, parse_dates=["date"])
        df["year_month"] = df["date"].dt.to_period("M")
        return df

    @staticmethod
    @st.cache_data(show_spinner="Loading reviews...")
    def _load_reviews() -> pd.DataFrame:
        # TODO: Replace with Google Business / Yelp API pull
        path = _DATA_DIR / "reviews.csv"
        df = pd.read_csv(path, parse_dates=["date"])
        df["year_month"] = df["date"].dt.to_period("M")
        return df

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_attendance_by_month(self, category: str | None = None) -> pd.DataFrame:
        """
        Returns monthly visitor counts (sum of quantity) grouped by event_category.
        Pass category='Art' or 'Film' to filter; None returns both.
        """
        df = self.transactions.copy()
        if category:
            df = df[df["event_category"] == category]
        grouped = (
            df.groupby(["year_month", "event_category"])["quantity"]
            .sum()
            .reset_index()
        )
        grouped["year_month_str"] = grouped["year_month"].astype(str)
        return grouped.sort_values("year_month_str")

    def get_attendance_by_week(self) -> pd.DataFrame:
        """Weekly attendance aggregated by year-week."""
        df = self.transactions.copy()
        df["year_week"] = df["event_date"].dt.strftime("%Y-W%V")
        grouped = (
            df.groupby(["year_week", "event_category"])["quantity"]
            .sum()
            .reset_index()
        )
        return grouped.sort_values("year_week")

    def get_seasonality_heatmap(self) -> pd.DataFrame:
        """
        Returns a pivot of average daily visitors: rows=month, cols=day_of_week.
        """
        df = self.transactions.copy()
        daily = (
            df.groupby(["event_date", "month", "day_of_week"])["quantity"]
            .sum()
            .reset_index()
        )
        pivot = daily.pivot_table(
            index="month", columns="day_of_week", values="quantity", aggfunc="mean"
        )
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])
        month_names = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
        }
        pivot.index = pivot.index.map(month_names)
        return pivot

    def get_event_performance(self) -> pd.DataFrame:
        """Top events by total attendance and revenue."""
        df = self.transactions.copy()
        grouped = (
            df.groupby(["event_name", "event_category"])
            .agg(
                total_visitors=("quantity", "sum"),
                total_revenue=("revenue", "sum"),
                avg_ticket_price=("ticket_price", "mean"),
                transactions=("transaction_id", "count"),
            )
            .reset_index()
            .sort_values("total_visitors", ascending=False)
        )
        return grouped

    def get_member_metrics(self) -> dict:
        """High-level membership KPIs."""
        df = self.members
        active = df[df["is_active"]]
        lapsed = df[~df["is_active"]]
        return {
            "total_members": len(df),
            "active_members": len(active),
            "lapsed_members": len(lapsed),
            "lapse_rate": round(len(lapsed) / len(df) * 100, 1),
            "avg_visits": round(df["total_visits"].mean(), 1),
            "tier_breakdown": active.groupby("membership_tier").size().to_dict(),
            "acq_breakdown": active.groupby("acquisition_channel").size().to_dict(),
        }

    def get_membership_over_time(self) -> pd.DataFrame:
        """
        Monthly snapshot of cumulative active vs. lapsed members.
        Approximated from join_date and lapse_date.
        """
        df = self.members.copy()
        periods = pd.period_range("2022-01", "2026-04", freq="M")
        rows = []
        for p in periods:
            p_date = p.to_timestamp(how="end")
            active = df[
                (df["join_date"] <= p_date)
                & (df["lapse_date"].isna() | (df["lapse_date"] > p_date))
            ]
            lapsed = df[
                (df["join_date"] <= p_date)
                & df["lapse_date"].notna()
                & (df["lapse_date"] <= p_date)
            ]
            rows.append({
                "year_month": str(p),
                "active": len(active),
                "lapsed": len(lapsed),
            })
        return pd.DataFrame(rows)

    def get_member_cohort_retention(self) -> pd.DataFrame:
        """
        Simplified cohort view: join quarter vs. lapse rate.
        """
        df = self.members.copy()
        df["join_quarter"] = df["join_date"].dt.to_period("Q").astype(str)
        cohort = (
            df.groupby("join_quarter")
            .agg(
                total=("patron_id", "count"),
                lapsed=("is_active", lambda x: (~x).sum()),
            )
            .reset_index()
        )
        cohort["retention_rate"] = round(
            (cohort["total"] - cohort["lapsed"]) / cohort["total"] * 100, 1
        )
        return cohort

    def get_purchase_lead_distribution(self) -> pd.DataFrame:
        """Lead-time histogram data: how many days before event tickets are bought."""
        return self.transactions[["purchase_lead_days", "is_member", "channel"]].copy()

    def get_channel_over_time(self) -> pd.DataFrame:
        """Monthly online vs. onsite split."""
        df = self.transactions.copy()
        grouped = (
            df.groupby(["year_month", "channel"])["quantity"]
            .sum()
            .reset_index()
        )
        grouped["year_month_str"] = grouped["year_month"].astype(str)
        return grouped.sort_values("year_month_str")

    def get_ticket_type_breakdown(self) -> pd.DataFrame:
        """Revenue and visitor counts by ticket type."""
        return (
            self.transactions.groupby("ticket_type")
            .agg(
                total_visitors=("quantity", "sum"),
                total_revenue=("revenue", "sum"),
            )
            .reset_index()
        )

    def get_revenue_by_category(self) -> pd.DataFrame:
        """Monthly revenue split by event category."""
        df = self.transactions.copy()
        grouped = (
            df.groupby(["year_month", "event_category"])["revenue"]
            .sum()
            .reset_index()
        )
        grouped["year_month_str"] = grouped["year_month"].astype(str)
        return grouped.sort_values("year_month_str")

    def get_zip_distribution(self) -> pd.DataFrame:
        """Visitor counts by zip code with estimated distance category."""
        df = self.transactions.copy()
        zip_counts = (
            df.groupby("zip_code")
            .agg(visitors=("quantity", "sum"), transactions=("transaction_id", "count"))
            .reset_index()
            .sort_values("visitors", ascending=False)
        )

        # Rough distance classification
        berkeley_zips = {"94704", "94705", "94703", "94702", "94709", "94710", "94720"}
        oakland_zips = {"94601", "94602", "94609", "94611", "94618", "94619", "94606"}
        sf_zips = {"94107", "94110", "94117", "94103", "94118", "94122", "94114"}

        def classify(z):
            if z in berkeley_zips:
                return "Berkeley (Local)"
            elif z in oakland_zips:
                return "Oakland (Near)"
            elif z in sf_zips:
                return "San Francisco"
            else:
                return "Other Bay Area / Beyond"

        zip_counts["region"] = zip_counts["zip_code"].apply(classify)
        return zip_counts

    def get_repeat_visitors_not_members(self, min_visits: int = 3) -> pd.DataFrame:
        """
        Patrons with >= min_visits transactions who are NOT members.
        These are prime membership conversion targets.
        """
        df = self.transactions.copy()
        non_members = df[~df["is_member"]]
        visit_counts = (
            non_members.groupby("patron_id")
            .agg(
                visits=("transaction_id", "count"),
                total_spend=("revenue", "sum"),
                last_event=("event_date", "max"),
                zip_code=("zip_code", "first"),
            )
            .reset_index()
        )
        targets = visit_counts[visit_counts["visits"] >= min_visits].sort_values(
            "visits", ascending=False
        )
        return targets

    def get_member_vs_nonmember(self) -> pd.DataFrame:
        """Comparative purchase behavior for members vs. non-members."""
        df = self.transactions.copy()
        comparison = (
            df.groupby("is_member")
            .agg(
                avg_ticket_price=("ticket_price", "mean"),
                avg_quantity=("quantity", "mean"),
                avg_lead_days=("purchase_lead_days", "mean"),
                online_pct=("channel", lambda x: (x == "Online").mean() * 100),
                total_revenue=("revenue", "sum"),
                transactions=("transaction_id", "count"),
            )
            .reset_index()
        )
        comparison["is_member"] = comparison["is_member"].map(
            {True: "Member", False: "Non-Member"}
        )
        return comparison

    def get_web_traffic_summary(self) -> pd.DataFrame:
        """Monthly aggregated web traffic across all sources."""
        df = self.web_traffic.copy()
        grouped = (
            df.groupby("year_month")
            .agg(
                sessions=("sessions", "sum"),
                users=("users", "sum"),
                page_views=("page_views", "sum"),
                exhibition_page_views=("exhibition_page_views", "sum"),
                film_page_views=("film_page_views", "sum"),
                membership_page_views=("membership_page_views", "sum"),
                avg_session_duration=("avg_session_duration_seconds", "mean"),
            )
            .reset_index()
        )
        grouped["year_month_str"] = grouped["year_month"].astype(str)
        return grouped.sort_values("year_month_str")

    def get_traffic_by_source(self) -> pd.DataFrame:
        """Monthly sessions broken down by source channel."""
        df = self.web_traffic.copy()
        grouped = (
            df.groupby(["year_month", "source"])["sessions"]
            .sum()
            .reset_index()
        )
        grouped["year_month_str"] = grouped["year_month"].astype(str)
        return grouped.sort_values("year_month_str")

    def get_attendance_vs_traffic(self) -> pd.DataFrame:
        """
        Merges monthly attendance totals with web traffic for overlay chart.
        """
        attendance = (
            self.transactions.groupby("year_month")["quantity"]
            .sum()
            .reset_index()
        )
        attendance["year_month_str"] = attendance["year_month"].astype(str)

        traffic = self.get_web_traffic_summary()[["year_month_str", "sessions"]]

        merged = attendance.merge(traffic, on="year_month_str", how="inner")
        return merged.sort_values("year_month_str")

    def get_review_sentiment_over_time(self) -> pd.DataFrame:
        """Monthly review counts by sentiment and average rating."""
        df = self.reviews.copy()
        grouped = (
            df.groupby(["year_month", "sentiment"])
            .agg(count=("rating", "count"), avg_rating=("rating", "mean"))
            .reset_index()
        )
        grouped["year_month_str"] = grouped["year_month"].astype(str)
        return grouped.sort_values("year_month_str")

    def get_review_avg_rating_over_time(self) -> pd.DataFrame:
        """Monthly average rating across all sources."""
        df = self.reviews.copy()
        grouped = (
            df.groupby("year_month")
            .agg(avg_rating=("rating", "mean"), count=("rating", "count"))
            .reset_index()
        )
        grouped["year_month_str"] = grouped["year_month"].astype(str)
        return grouped.sort_values("year_month_str")

    def get_ytd_kpis(self) -> dict:
        """Top-level KPIs for the current year (2026 YTD)."""
        current_year = 2026
        tx = self.transactions[self.transactions["year"] == current_year]
        reviews_year = self.reviews[self.reviews["date"].dt.year == current_year]

        return {
            "ytd_visitors": int(tx["quantity"].sum()),
            "ytd_revenue": round(tx["revenue"].sum(), 2),
            "active_members": self.get_member_metrics()["active_members"],
            "avg_rating": round(reviews_year["rating"].mean(), 2) if len(reviews_year) else 0.0,
            "avg_rating_delta": round(
                reviews_year["rating"].mean()
                - self.reviews[self.reviews["date"].dt.year == 2025]["rating"].mean(),
                2,
            ) if len(reviews_year) else 0.0,
        }

    def get_data_summary_for_ai(self) -> str:
        """
        Returns a compact text summary of key metrics for the InsightsAgent context window.
        Keeps token usage low while giving Claude enough to generate real insights.
        """
        kpis = self.get_ytd_kpis()
        member_metrics = self.get_member_metrics()
        top_events = self.get_event_performance().head(5)
        zip_dist = self.get_zip_distribution().head(10)
        conversion = self.get_repeat_visitors_not_members()
        traffic = self.get_web_traffic_summary().tail(3)
        sentiment = self.get_review_sentiment_over_time().tail(6)

        lines = [
            "=== BAMPFA AUDIENCE ANALYTICS SUMMARY ===",
            f"Data range: Jan 2022 – Apr 2026",
            "",
            f"--- YTD 2026 KPIs ---",
            f"Visitors: {kpis['ytd_visitors']:,}",
            f"Revenue:  ${kpis['ytd_revenue']:,.0f}",
            f"Active Members: {kpis['active_members']}",
            f"Avg Review Rating: {kpis['avg_rating']}",
            "",
            f"--- Membership ---",
            f"Total members ever: {member_metrics['total_members']}",
            f"Lapse rate: {member_metrics['lapse_rate']}%",
            f"Avg visits per member: {member_metrics['avg_visits']}",
            f"Tier mix: {member_metrics['tier_breakdown']}",
            f"Acquisition channels: {member_metrics['acq_breakdown']}",
            "",
            f"--- Top 5 Events by Attendance ---",
        ]
        for _, row in top_events.iterrows():
            lines.append(
                f"  {row['event_name']} ({row['event_category']}): "
                f"{row['total_visitors']:,} visitors, ${row['total_revenue']:,.0f} revenue"
            )

        lines += [
            "",
            f"--- Top Visitor Zip Codes ---",
        ]
        for _, row in zip_dist.iterrows():
            lines.append(
                f"  {row['zip_code']} ({row['region']}): {row['visitors']:,} visitors"
            )

        lines += [
            "",
            f"--- Conversion Opportunity ---",
            f"Non-member patrons with 3+ visits: {len(conversion):,}",
            f"Avg spend per target patron: ${conversion['total_spend'].mean():,.0f}",
            "",
            f"--- Recent Web Traffic (last 3 months) ---",
        ]
        for _, row in traffic.iterrows():
            lines.append(
                f"  {row['year_month_str']}: {row['sessions']:,} sessions, "
                f"{row['users']:,} users"
            )

        lines += [
            "",
            f"--- Recent Review Sentiment ---",
        ]
        for _, row in sentiment.iterrows():
            lines.append(
                f"  {row['year_month_str']} {row['sentiment']}: "
                f"{row['count']} reviews, avg {row['avg_rating']:.2f}"
            )

        return "\n".join(lines)
