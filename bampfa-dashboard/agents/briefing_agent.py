"""
agents/briefing_agent.py
BriefingAgent: orchestrator that synthesizes overnight findings from the other
agents into a daily marketing standup memo.

Pulls KPIs from DataAgent, a top membership lead from ConversionAgent, and the
press↔attendance correlation from SentimentAgent, then asks Claude to weave
them into a prioritized briefing.
"""

import numpy as np

from .conversion_agent import ConversionAgent
from .data_agent import DataAgent
from .sentiment_agent import SentimentAgent
from ._anthropic import MODEL, get_client

_SYSTEM_PROMPT = """You are the lead marketing analyst for BAMPFA, writing a concise daily \
standup memo for the marketing team. You synthesize findings from the museum's analytics, \
membership conversion targets, and earned-media monitoring into prioritized actions. \
Be specific with numbers from the data and confident in your recommendations.
"""

_FALLBACK = """**AI briefing requires an Anthropic API key.**

Set `ANTHROPIC_API_KEY` in `.env` (local) or Streamlit secrets (Cloud) to enable
Claude-powered daily briefings. The other dashboard pages remain fully functional.
"""


class BriefingAgent:
    """
    Calls into ConversionAgent and SentimentAgent for headline findings, then
    asks Claude to assemble a daily memo grounded in the DataAgent summary.
    """

    def __init__(self, data_agent: DataAgent):
        self.data_agent = data_agent
        self.conversion = ConversionAgent(data_agent)
        self.sentiment = SentimentAgent(data_agent)
        self._client = get_client()

    @property
    def has_api_key(self) -> bool:
        return self._client is not None

    def generate_daily_briefing(self) -> str:
        """Returns a markdown standup memo for the home page."""
        if self._client is None:
            return _FALLBACK

        data_summary = self.data_agent.get_data_summary_for_ai()

        # Conversion Agent headline
        conv = self.conversion.conversion_summary()
        conv_line = (
            f"Conversion Agent: {conv['n_targets']:,} non-member repeat visitors flagged; "
            f"projected ${conv['projected_revenue_if_10pct_convert']:,} in new membership "
            f"revenue at a 10% conversion rate."
        )

        # Sentiment Agent headline
        try:
            corr = self.sentiment.press_attendance_correlation()
            r_same = corr["r_same"]
            r_lag = corr["r_lag"]
            if not np.isnan(r_same):
                sentiment_line = (
                    f"Sentiment Agent: same-month press↔attendance r = {r_same:.2f}, "
                    f"1-month lag r = {r_lag:.2f} (n={corr['n_months']} months)."
                )
            else:
                sentiment_line = "Sentiment Agent: insufficient press data for correlation."
        except Exception as e:
            sentiment_line = f"Sentiment Agent: unavailable ({e})."

        prompt = f"""
Here is the current BAMPFA audience analytics data summary:

```
{data_summary}
```

Findings from sibling agents this morning:
- {conv_line}
- {sentiment_line}

Please generate a concise **daily marketing briefing** for the BAMPFA team. Structure it as:

## Today's Audience Intelligence Briefing

### Key Trends (2-3 bullets)
### Membership Alert (1-2 bullets — incorporate the Conversion Agent finding)
### Earned Media Signal (1-2 bullets — incorporate the Sentiment Agent finding)
### Recommended Actions This Week (3 prioritized action items)
### One Data Question to Investigate

Keep the whole briefing under 350 words. Be specific with numbers from the data.
"""

        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=700,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            return f"**Could not generate briefing:** {str(e)}"
