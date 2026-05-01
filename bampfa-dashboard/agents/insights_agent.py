"""
agents/insights_agent.py
InsightsAgent: Uses the Anthropic API (claude-sonnet-4-5) to generate
AI-powered audience insights and answer marketing team questions.

Falls back gracefully if ANTHROPIC_API_KEY is not set.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# Read API key from .env locally, or from Streamlit Cloud secrets in production
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    try:
        import streamlit as st
        ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        pass

_SYSTEM_PROMPT = """You are an expert arts and culture marketing analyst assistant for BAMPFA \
(Berkeley Art Museum and Pacific Film Archive). You have deep knowledge of museum audience \
development, membership programs, and film/arts programming. \

You are given a summary of BAMPFA's real audience analytics data and are asked to provide \
specific, actionable insights and recommendations for the marketing team. \

Always:
- Ground your analysis in the specific numbers provided in the data context
- Make concrete, prioritized recommendations
- Format your response in clear markdown with headers and bullet points
- Keep responses focused and practical — this is an operational dashboard, not an academic report
- Mention specific zip codes, tiers, or segments when relevant
- Use a confident, collegial tone appropriate for an internal marketing tool
"""

_FALLBACK_MESSAGE = """**AI Insights are not configured.**

To enable AI-powered insights, add your Anthropic API key to the `.env` file:

```
ANTHROPIC_API_KEY=your_key_here
```

In the meantime, here are some manual analysis directions based on the data visible in the other dashboard pages:

- **Membership conversion**: Check the repeat visitors table on the Membership page for warm leads
- **Seasonal planning**: October–November and February–March are peak months — plan campaigns accordingly
- **Geographic targeting**: Berkeley and Oakland zip codes drive the majority of attendance
- **Channel mix**: Online channels account for ~65% of ticket sales — digital campaigns have high reach
"""


class InsightsAgent:
    """
    Wraps the Anthropic API to answer marketing questions using BAMPFA analytics data.
    """

    def __init__(self, data_summary: str):
        """
        Args:
            data_summary: Pre-computed text from DataAgent.get_data_summary_for_ai()
        """
        self.data_summary = data_summary
        self.has_api_key = bool(ANTHROPIC_API_KEY)
        self._client = None

        if self.has_api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except ImportError:
                self.has_api_key = False

    def _build_context_message(self) -> str:
        return (
            "Here is the current BAMPFA audience analytics data summary:\n\n"
            f"```\n{self.data_summary}\n```\n\n"
        )

    def ask(self, question: str) -> str:
        """
        Sends a user question to Claude with the data summary as context.
        Returns markdown-formatted response string.
        """
        if not self.has_api_key or self._client is None:
            return _FALLBACK_MESSAGE

        user_message = self._build_context_message() + f"**Marketing team question:** {question}"

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message}
                ],
            )
            return response.content[0].text
        except Exception as e:
            return f"**Error calling AI service:** {str(e)}\n\nPlease check your API key and try again."

    def ask_with_history(self, question: str, history: list[dict]) -> str:
        """
        Multi-turn conversation. history is a list of {"role": "user"|"assistant", "content": str}.
        The data context is injected only in the first user turn.
        """
        if not self.has_api_key or self._client is None:
            return _FALLBACK_MESSAGE

        # Inject data context into the first user message
        messages = []
        if history:
            first = history[0].copy()
            if first["role"] == "user":
                first["content"] = self._build_context_message() + first["content"]
            messages = [first] + history[1:]

        # Add current question
        if not messages:
            messages = [{"role": "user", "content": self._build_context_message() + question}]
        else:
            messages.append({"role": "user", "content": question})

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            return f"**Error calling AI service:** {str(e)}\n\nPlease check your API key and try again."

    def generate_dashboard_summary(self) -> str:
        """
        Auto-generates a daily briefing for the home page overview.
        Called once per session and cached by the caller.
        """
        if not self.has_api_key or self._client is None:
            return _FALLBACK_MESSAGE

        prompt = (
            self._build_context_message()
            + """Please generate a concise **daily marketing briefing** for the BAMPFA team. \
Structure it as:

## Today's Audience Intelligence Briefing

### Key Trends (2-3 bullets)
### Membership Alert (1-2 bullets on retention/conversion opportunities)
### Recommended Actions This Week (3 prioritized action items)
### One Data Question to Investigate

Keep the whole briefing under 300 words. Be specific with numbers from the data."""
        )

        try:
            response = self._client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=600,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            return f"**Could not generate briefing:** {str(e)}"
