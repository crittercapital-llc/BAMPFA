"""
agents/forecasting_agent.py
ForecastingAgent: predicts attendance, revenue, and VX staffing for new BAMPFA
films and exhibitions by combining historical comps + seasonality with Claude's
knowledge of directors, genres, artists, and mediums.
"""

import pandas as pd

from .data_agent import DataAgent
from ._anthropic import MODEL, get_client

_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_SYSTEM_PROMPT = """You are a forecasting analyst for BAMPFA (Berkeley Art Museum and Pacific \
Film Archive). You forecast attendance, revenue, and staffing for new film screenings and art \
exhibitions using BAMPFA's own historical performance data plus your knowledge of the film \
and art world. Be specific with numbers and avoid hedging excessively.
"""


class ForecastingAgent:
    """
    Forecasts a new event by:
      1) Pulling historical comps from DataAgent (same category, same calendar month).
      2) Computing a seasonality factor and a base-case attendance / revenue / staffing.
      3) Asking Claude to write a three-scenario narrative using the comps as anchor.
    """

    def __init__(self, data_agent: DataAgent):
        self.data_agent = data_agent
        self._client = get_client()

    @property
    def has_api_key(self) -> bool:
        return self._client is not None

    def forecast_event(self, spec: dict) -> dict:
        """
        Generate a forecast for a new event.

        Args:
            spec: {
                "category": "Film" | "Art",
                "title": str,
                "opening_date": datetime.date,
                "ticket_price": float,
                "marketing_tier": str,
                "run_length_days": int,
                "notes": str,
                # Film-only:
                "director": str,
                "genre": str,
                "day_of_week": list[str],
                "time_slot": str,
                # Art-only:
                "artist_name": str,
                "medium": str,
                "gallery": str,
            }

        Returns:
            {
                "comps": pd.DataFrame,         # historical comps for the same category/month
                "seasonality_factor": float,   # 1.0 = annual avg; 1.2 = +20%
                "base_visitors": int,          # comp-average × seasonality
                "base_revenue": float,         # base_visitors × ticket_price × 0.85
                "base_staff": int,             # 1 staff per 80 visitors/day, min 2
                "narrative_md": str,           # Claude-generated three-scenario forecast
            }
        """
        category = spec["category"]
        opening_date = spec["opening_date"]
        month = opening_date.month
        ticket_price = float(spec.get("ticket_price", 15.0))

        comps = self.data_agent.get_historical_comps(category, month)
        seasonality = self.data_agent.get_seasonality_factor(month)

        top_comps = comps.head(8)
        avg_visitors = int(top_comps["total_visitors"].mean()) if len(top_comps) else 500
        avg_revenue = float(top_comps["total_revenue"].mean()) if len(top_comps) else 5000.0

        base_visitors = int(avg_visitors * seasonality)
        # 0.85 = blended factor accounting for member discounts
        base_revenue = round(base_visitors * ticket_price * 0.85)
        # 22 open days/month, 1 staff per 80 visitors/day, floor of 2
        base_staff = max(2, round(base_visitors / 22 / 80))

        narrative_md = self._generate_narrative(
            spec, comps, seasonality, avg_visitors, avg_revenue
        )

        return {
            "comps": comps,
            "seasonality_factor": seasonality,
            "base_visitors": base_visitors,
            "base_revenue": base_revenue,
            "base_staff": base_staff,
            "narrative_md": narrative_md,
        }

    # ------------------------------------------------------------------
    # Internal: Claude prompt
    # ------------------------------------------------------------------

    def _generate_narrative(
        self,
        spec: dict,
        comps: pd.DataFrame,
        seasonality: float,
        avg_visitors: int,
        avg_revenue: float,
    ) -> str:
        if self._client is None:
            return (
                "**Forecast narrative requires an Anthropic API key.** "
                "The base-case numbers above are computed directly from BAMPFA historical comps."
            )

        category = spec["category"]
        is_film = category == "Film"
        month = spec["opening_date"].month
        season_label = f"{round((seasonality - 1) * 100):+}% vs annual average"

        if is_film:
            event_details = f"""
Event Type: Film Screening
Title: {spec.get('title', '')}
Director: {spec.get('director', '')}
Genre: {spec.get('genre', '')}
Screening Days: {', '.join(spec.get('day_of_week') or []) or 'TBD'}
Time Slot: {spec.get('time_slot', '')}
Number of Screenings: {spec.get('run_length_days', '')}
Ticket Price: ${spec.get('ticket_price', '')}
Marketing Support: {spec.get('marketing_tier', '')}
Opening Month: {_MONTH_NAMES[month-1]} (Seasonality factor: {season_label})
Additional Notes: {spec.get('notes') or 'None'}
"""
        else:
            event_details = f"""
Event Type: Art Exhibition
Title: {spec.get('title', '')}
Artist / Curator: {spec.get('artist_name', '')}
Medium: {spec.get('medium', '')}
Gallery: {spec.get('gallery', '')}
Run Length: {spec.get('run_length_days', '')} days
Ticket Price: ${spec.get('ticket_price', '')}
Marketing Support: {spec.get('marketing_tier', '')}
Opening Month: {_MONTH_NAMES[month-1]} (Seasonality factor: {season_label})
Additional Notes: {spec.get('notes') or 'None'}
"""

        top_comps = comps.head(8)
        comp_text = "\n".join([
            f"  - {row['event_name']}: {row['total_visitors']:,} visitors, "
            f"${row['total_revenue']:,.0f} revenue, {row['online_pct']}% online, {row['member_pct']}% members"
            for _, row in top_comps.iterrows()
        ])

        prompt = f"""
You are forecasting attendance for a new BAMPFA event. Use your knowledge of the film/art world
AND the historical BAMPFA data provided to generate a realistic, specific forecast.

## New Event
{event_details}

## Historical BAMPFA Comps ({category} events in {_MONTH_NAMES[month-1]})
{comp_text}

Historical average for this category/month: {avg_visitors:,} visitors, ${avg_revenue:,.0f} revenue

## Your Task
Generate a detailed attendance and staffing forecast with these exact sections:

### Attendance Forecast
Provide three scenarios (Conservative / Base Case / Optimistic) with specific visitor numbers.
Factor in: director/artist reputation and draw, genre/medium appeal for BAMPFA's audience,
day-of-week and time slot effects, marketing support level, seasonality, and any co-presenter
or touring exhibition multipliers mentioned in notes.

For films specifically: assess whether this director has crossover appeal beyond hardcore cinephiles,
whether the genre aligns with BAMPFA's historically strong film categories, and whether the
screening format (number of screenings, time slots) maximizes or limits attendance.

For exhibitions specifically: assess artist national vs. local recognition, medium appeal,
gallery placement (G1 vs. secondary), and run length relative to typical BAMPFA engagement.

### Revenue Estimate
Based on your attendance forecast, ticket price, and typical member discount rates.

### Week-by-Week Pattern
Brief description of expected attendance curve (opening weekend, mid-run, closing).

### VX Staffing Recommendation
Using 1 staff per 80 visitors/day. Specify peak days and minimum staffing floor.

### Key Risk Factors
2-3 things that could push attendance above or below forecast.

### Comparable Past Events at BAMPFA
Identify 2-3 of the historical comps above that are most similar and explain why.

Be specific with numbers. Avoid hedging excessively — give a clear base case recommendation.
"""

        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=1500,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            return f"**Forecast narrative error:** {str(e)}"
