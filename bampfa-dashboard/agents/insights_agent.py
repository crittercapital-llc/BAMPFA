"""
agents/insights_agent.py
InsightsAgent: natural-language Q&A over BAMPFA audience data.

Conversational interface for non-technical staff. Takes the shared DataAgent
via constructor injection and asks Claude to ground its answers in the
data summary.
"""

from .data_agent import DataAgent
from ._anthropic import MODEL, get_client

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
    Wraps the Anthropic API to answer marketing questions using BAMPFA data.
    The data context is rebuilt from the shared DataAgent on each call.
    """

    def __init__(self, data_agent: DataAgent):
        self.data_agent = data_agent
        self._client = get_client()

    @property
    def has_api_key(self) -> bool:
        return self._client is not None

    def _build_context_message(self) -> str:
        return (
            "Here is the current BAMPFA audience analytics data summary:\n\n"
            f"```\n{self.data_agent.get_data_summary_for_ai()}\n```\n\n"
        )

    def ask(self, question: str) -> str:
        """Single-turn Q&A. Returns markdown."""
        if self._client is None:
            return _FALLBACK_MESSAGE

        user_message = self._build_context_message() + f"**Marketing team question:** {question}"

        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except Exception as e:
            return f"**Error calling AI service:** {str(e)}\n\nPlease check your API key and try again."

    def ask_with_history(self, question: str, history: list[dict]) -> str:
        """
        Multi-turn conversation. history is a list of {"role": "user"|"assistant", "content": str}.
        Data context is injected only into the first user turn.
        """
        if self._client is None:
            return _FALLBACK_MESSAGE

        messages = []
        if history:
            first = history[0].copy()
            if first["role"] == "user":
                first["content"] = self._build_context_message() + first["content"]
            messages = [first] + history[1:]

        if not messages:
            messages = [{"role": "user", "content": self._build_context_message() + question}]
        else:
            messages.append({"role": "user", "content": question})

        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=_SYSTEM_PROMPT,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            return f"**Error calling AI service:** {str(e)}\n\nPlease check your API key and try again."
