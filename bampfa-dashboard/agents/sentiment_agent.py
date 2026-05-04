"""
agents/sentiment_agent.py
SentimentAgent: monitors press, Reddit, and Google reviews; correlates earned-media
coverage spikes with attendance lift.

Wraps PublicDataAgent (the raw external-data fetcher) and adds the analysis layer
on top — primarily the Pearson correlation between monthly press coverage and
attendance, including a 1-month lag test.
"""

import numpy as np
import pandas as pd
from scipy import stats

from .data_agent import DataAgent
from .public_data_agent import PublicDataAgent


class SentimentAgent:
    def __init__(self, data_agent: DataAgent):
        self.data_agent = data_agent
        self._public = PublicDataAgent()

    # ------------------------------------------------------------------
    # Source status + raw data passthroughs
    # ------------------------------------------------------------------

    def get_source_status(self) -> dict:
        return self._public.get_source_status()

    def get_press_coverage(self) -> pd.DataFrame:
        return self._public.get_all_press_coverage()

    def get_press_timeline(self) -> pd.DataFrame:
        return self._public.get_press_timeline()

    def get_reddit_mentions(self) -> pd.DataFrame:
        return self._public.get_reddit_mentions()

    def get_google_reviews(self) -> pd.DataFrame:
        return self._public.get_google_reviews()

    # ------------------------------------------------------------------
    # Analysis: press → attendance correlation
    # ------------------------------------------------------------------

    def press_attendance_correlation(self) -> dict:
        """
        Pearson r between monthly press article counts and BAMPFA attendance,
        both same-month and 1-month-lagged (does last month's press predict
        this month's attendance?).

        Returns:
            {
                "merged": pd.DataFrame,        # year_month_str, quantity, article_count, article_count_lag1
                "r_same": float,               # same-month Pearson r (NaN if insufficient data)
                "p_same": float,
                "r_lag":  float,               # 1-month-lagged Pearson r
                "p_lag":  float,
                "n_months": int,               # months of overlap
                "interpretation_md": str,      # human-readable summary
            }
        """
        timeline_df = self.get_press_timeline()

        attendance_monthly = (
            self.data_agent.transactions
            .groupby("year_month")["quantity"]
            .sum()
            .reset_index()
        )
        attendance_monthly["year_month_str"] = attendance_monthly["year_month"].astype(str)
        attendance_monthly = attendance_monthly.sort_values("year_month_str")

        if timeline_df.empty:
            return {
                "merged": pd.DataFrame(),
                "r_same": np.nan, "p_same": np.nan,
                "r_lag":  np.nan, "p_lag":  np.nan,
                "n_months": 0,
                "interpretation_md": "Not enough press data for correlation analysis.",
            }

        merged = (
            attendance_monthly
            .merge(timeline_df, on="year_month_str", how="inner")
            .sort_values("year_month_str")
            .reset_index(drop=True)
        )
        merged["article_count_lag1"] = merged["article_count"].shift(1)

        merged_valid = merged.dropna(subset=["article_count"])
        merged_lag   = merged.dropna(subset=["article_count_lag1"])

        r_same, p_same = (np.nan, np.nan)
        r_lag,  p_lag  = (np.nan, np.nan)
        if len(merged_valid) >= 3:
            r_same, p_same = stats.pearsonr(
                merged_valid["article_count"],
                merged_valid["quantity"],
            )
        if len(merged_lag) >= 3:
            r_lag, p_lag = stats.pearsonr(
                merged_lag["article_count_lag1"],
                merged_lag["quantity"],
            )

        if not np.isnan(r_same):
            strength = "strong" if abs(r_same) > 0.6 else ("moderate" if abs(r_same) > 0.3 else "weak")
            direction = "positive" if r_same > 0 else "negative"
            interpretation = (
                f"The same-month Pearson r = {r_same:.3f} indicates a **{strength} {direction}** "
                f"correlation between press article counts and attendance. "
                f"The 1-month lagged r = {r_lag:.3f} tests whether last month's press "
                f"coverage predicts this month's attendance — potentially more useful for planning. "
                f"_Reminder: this is observational. Confounders include major exhibitions, "
                f"seasonality, and UC Berkeley academic calendar._"
            )
        else:
            interpretation = "Not enough overlap between press and attendance data."

        return {
            "merged": merged,
            "r_same": r_same, "p_same": p_same,
            "r_lag":  r_lag,  "p_lag":  p_lag,
            "n_months": len(merged_valid),
            "interpretation_md": interpretation,
        }
