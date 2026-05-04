"""
agents/conversion_agent.py
ConversionAgent: surfaces the warmest membership leads (non-members with
multiple visits) and drafts personalized outreach emails.
"""

import pandas as pd

from .data_agent import DataAgent
from ._anthropic import MODEL, get_client

_SYSTEM_PROMPT = """You are a membership marketing specialist for BAMPFA. You write warm, \
personalized invitation emails to non-member patrons who have visited multiple times. \
Keep emails brief, specific to each patron's history, and authentic — collegial and \
museum-appropriate, never salesy.
"""

# Member tier assumed for revenue projections — Individual is the entry tier.
_INDIVIDUAL_TIER_PRICE = 75
_PROJECTED_CONVERSION_RATE = 0.10


class ConversionAgent:
    """
    Wraps repeat-visitor analytics with a lead-scoring model and an outreach
    drafter. Shares the DataAgent so it sees the same transactions the rest of
    the dashboard does.
    """

    def __init__(self, data_agent: DataAgent):
        self.data_agent = data_agent
        self._client = get_client()

    @property
    def has_api_key(self) -> bool:
        return self._client is not None

    def get_warmest_leads(self, min_visits: int = 3) -> pd.DataFrame:
        """
        Repeat non-member patrons with a recency-weighted lead score.

        Lead score = visits × sqrt(spend) × recency_factor, where recency_factor
        decays roughly by half every 90 days since the patron's last visit.
        """
        leads = self.data_agent.get_repeat_visitors_not_members(min_visits=min_visits).copy()
        if leads.empty:
            leads["lead_score"] = []
            return leads

        max_event_date = leads["last_event"].max()
        days_since = (max_event_date - leads["last_event"]).dt.days.clip(lower=0)
        recency_factor = 1.0 / (1.0 + days_since / 90.0)

        spend_component = leads["total_spend"].clip(lower=1) ** 0.5
        leads["lead_score"] = (leads["visits"] * spend_component * recency_factor).round(1)

        return leads.sort_values("lead_score", ascending=False).reset_index(drop=True)

    def conversion_summary(self, min_visits: int = 3) -> dict:
        """High-level summary used by the Membership page and the BriefingAgent."""
        leads = self.get_warmest_leads(min_visits=min_visits)
        if leads.empty:
            return {
                "n_targets": 0,
                "avg_spend": 0.0,
                "projected_revenue_if_10pct_convert": 0,
            }
        return {
            "n_targets": len(leads),
            "avg_spend": float(leads["total_spend"].mean()),
            "projected_revenue_if_10pct_convert": int(round(
                len(leads) * _PROJECTED_CONVERSION_RATE * _INDIVIDUAL_TIER_PRICE
            )),
        }

    def draft_outreach_email(self, patron_row) -> str:
        """
        Draft a personalized membership invitation for one patron.

        Args:
            patron_row: a pandas Series or dict with at least the fields
                from get_warmest_leads (patron_id, visits, total_spend,
                last_event, zip_code).
        Returns:
            Markdown email body. Falls back to a templated message if no API key.
        """
        if isinstance(patron_row, dict):
            row = patron_row
        else:
            row = patron_row.to_dict()

        if self._client is None:
            return (
                "**Outreach drafting requires an Anthropic API key.**\n\n"
                f"Suggested template: invite patron {row.get('patron_id', '')} — "
                f"{row.get('visits', 0)} visits, ${row.get('total_spend', 0):,.0f} lifetime spend — "
                f"to join at the Individual tier (${_INDIVIDUAL_TIER_PRICE}/yr)."
            )

        last_event_str = "unknown"
        if pd.notna(row.get("last_event")):
            last_event_str = pd.to_datetime(row["last_event"]).strftime("%B %Y")

        prompt = f"""
Draft a brief personalized email (under 180 words) inviting this patron to become a BAMPFA member.

## Patron details
- Patron ID: {row.get('patron_id', '')}
- Visits in the last few years: {row.get('visits', 0)}
- Total spend to date: ${row.get('total_spend', 0):,.0f}
- Last event attended: {last_event_str}
- Zip code: {row.get('zip_code', '')}

## Style
- Friendly and specific — reference their multiple visits.
- Mention member benefits: free admission, member previews, 10% bookstore discount.
- Soft call to action: "Would you like to join at the Individual tier (${_INDIVIDUAL_TIER_PRICE}/yr)?"
- Sign off as "The BAMPFA Membership Team".
- Return only the email body in markdown — no subject line, no preamble.
"""

        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=400,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            return f"**Email drafting error:** {str(e)}"
