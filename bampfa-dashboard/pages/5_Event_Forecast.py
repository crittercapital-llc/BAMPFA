"""
pages/5_Event_Forecast.py
BAMPFA Event Attendance Forecaster

Interactive tool to forecast attendance and VX staffing for a new film
screening or art exhibition. Uses historical comps + Claude AI to factor in
director/artist reputation, genre, day of week, seasonality, and more.
"""

import sys
from pathlib import Path
from datetime import date

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent
from agents.forecasting_agent import ForecastingAgent
from agents.insights_agent import InsightsAgent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Event Forecaster | BAMPFA Analytics",
    page_icon="🔮",
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
      .forecast-box { background: #141424; border: 1px solid #2d2d4a;
          border-left: 4px solid #c8a96e; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem; }
      .forecast-box h3, .forecast-box h4 { color: #e8c99a !important; }
      .forecast-box p, .forecast-box li { color: #d0d0e0 !important; }
      [data-testid="metric-container"] { background: #1e1e30; border: 1px solid #2d2d4a;
          border-radius: 10px; padding: 1rem; }
      [data-testid="metric-container"] label { color: #a0b4c8 !important;
          font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
      [data-testid="metric-container"] [data-testid="stMetricValue"] {
          color: #e8c99a !important; font-size: 1.9rem !important; font-weight: 700 !important; }
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
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>🔮 Event Attendance Forecaster</h2>
        <p>Input a new film screening or art exhibition to get an AI-powered attendance forecast,
        revenue estimate, and VX staffing recommendation — benchmarked against historical BAMPFA data.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Input Form
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Event Details</div>', unsafe_allow_html=True)

event_type = st.radio(
    "Event Type",
    options=["🎬 Film Screening", "🎨 Art Exhibition"],
    horizontal=True,
)
is_film = event_type.startswith("🎬")

with st.form("forecast_form"):
    col_a, col_b = st.columns(2)

    with col_a:
        event_title = st.text_input(
            "Title *",
            placeholder="e.g. 'Mulholland Drive' or 'Kehinde Wiley: An Economy of Grace'",
        )
        opening_date = st.date_input(
            "Opening / Screening Date *",
            value=date.today(),
            min_value=date(2024, 1, 1),
        )
        ticket_price = st.number_input(
            "Planned Ticket Price ($)",
            min_value=0.0,
            max_value=100.0,
            value=15.0,
            step=1.0,
        )
        run_length_days = st.number_input(
            "Run Length (days)" if not is_film else "Number of Screenings",
            min_value=1,
            max_value=365,
            value=60 if not is_film else 4,
        )

    with col_b:
        if is_film:
            director = st.text_input(
                "Director *",
                placeholder="e.g. 'David Lynch', 'Agnès Varda', 'Bong Joon-ho'",
            )
            genre = st.selectbox(
                "Genre",
                ["Art House / Experimental", "International / Foreign Language",
                 "Documentary", "Classic / Repertory", "Contemporary Drama",
                 "Animation", "Horror / Thriller", "Comedy", "Other"],
            )
            day_of_week = st.multiselect(
                "Screening Day(s)",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                default=["Friday", "Saturday"],
            )
            time_slot = st.selectbox(
                "Primary Time Slot",
                ["Matinee (before 5pm)", "Evening (5–8pm)", "Late Night (after 8pm)"],
            )
            marketing_tier = st.select_slider(
                "Marketing Support",
                options=["Minimal", "Standard", "Featured", "Major Campaign"],
                value="Standard",
            )
        else:
            artist_name = st.text_input(
                "Artist / Curator *",
                placeholder="e.g. 'Kerry James Marshall', 'Judy Chicago'",
            )
            medium = st.selectbox(
                "Medium / Type",
                ["Painting", "Photography", "Sculpture", "Mixed Media",
                 "Video / New Media", "Drawing / Works on Paper",
                 "Textile / Fiber", "Installation", "Group Exhibition", "Other"],
            )
            gallery = st.selectbox(
                "Gallery",
                ["G1 (Main Gallery)", "G2 (Secondary)", "Project Space", "Outdoor"],
            )
            marketing_tier = st.select_slider(
                "Marketing Support",
                options=["Minimal", "Standard", "Featured", "Major Campaign"],
                value="Standard",
            )

        notes = st.text_area(
            "Additional Context (optional)",
            placeholder="e.g. 'Part of a retrospective series', 'Co-presented with SF Film Festival', 'National touring exhibition'",
            height=80,
        )

    submitted = st.form_submit_button("Generate Forecast →", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Forecast Logic
# ---------------------------------------------------------------------------

if submitted:
    if not event_title:
        st.error("Please enter an event title.")
        st.stop()

    month = opening_date.month
    category = "Film" if is_film else "Art"
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Build the spec the ForecastingAgent expects
    spec = {
        "category": category,
        "title": event_title,
        "opening_date": opening_date,
        "ticket_price": ticket_price,
        "marketing_tier": marketing_tier,
        "run_length_days": run_length_days,
        "notes": notes,
    }
    if is_film:
        spec.update({
            "director": director,
            "genre": genre,
            "day_of_week": day_of_week,
            "time_slot": time_slot,
        })
    else:
        spec.update({
            "artist_name": artist_name,
            "medium": medium,
            "gallery": gallery,
        })

    forecaster = ForecastingAgent(agent)
    with st.spinner("Forecasting Agent analyzing historical comps and generating forecast..."):
        result = forecaster.forecast_event(spec)

    comps = result["comps"]
    seasonality = result["seasonality_factor"]
    forecast_result = result["narrative_md"]
    season_label = f"{round((seasonality - 1) * 100):+}% vs annual average"

    # ---------------------------------------------------------------------------
    # Output
    # ---------------------------------------------------------------------------

    st.markdown('<div class="section-header">Forecast Results</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Comp Average (this month)", f"{result['base_visitors']:,}", f"Seasonality: {season_label}")
    with m2:
        st.metric("Est. Revenue (Base)", f"${result['base_revenue']:,.0f}", "At comp avg attendance")
    with m3:
        st.metric("Est. Daily VX Staff", str(result["base_staff"]), "Base case")
    with m4:
        st.metric("Seasonality Index", str(seasonality), f"{month_names[month-1]} vs annual avg")

    # Full AI forecast
    st.markdown('<div class="forecast-box">', unsafe_allow_html=True)
    st.markdown(forecast_result)
    st.markdown('</div>', unsafe_allow_html=True)

    # Historical comps table
    st.markdown('<div class="section-header">Historical Comps — Similar BAMPFA Events</div>', unsafe_allow_html=True)
    st.caption(f"All {category} events at BAMPFA in {month_names[month-1]}, ranked by attendance.")

    display_comps = comps.head(12).copy()
    display_comps["total_revenue"] = display_comps["total_revenue"].map("${:,.0f}".format)
    display_comps["avg_ticket"] = display_comps["avg_ticket"].map("${:.2f}".format)
    display_comps["online_pct"] = display_comps["online_pct"].map("{}%".format)
    display_comps["member_pct"] = display_comps["member_pct"].map("{}%".format)
    display_comps = display_comps.rename(columns={
        "event_name": "Event",
        "event_category": "Category",
        "total_visitors": "Visitors",
        "total_revenue": "Revenue",
        "avg_ticket": "Avg Ticket",
        "online_pct": "Online %",
        "member_pct": "Member %",
        "transactions": "Transactions",
    })
    st.dataframe(display_comps, use_container_width=True, hide_index=True)

    # Follow-up chat
    st.markdown('<div class="section-header">Ask a Follow-Up</div>', unsafe_allow_html=True)

    if "forecast_chat" not in st.session_state:
        st.session_state.forecast_chat = []

    for msg in st.session_state.forecast_chat:
        if msg["role"] == "user":
            st.markdown(
                f'<div style="background:#1e1e30;border:1px solid #2d2d4a;border-radius:8px;'
                f'padding:0.8rem 1rem;margin-bottom:0.5rem;color:#e0e0e0;">'
                f'<strong>You:</strong> {msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**Claude:** {msg['content']}")

    with st.form("followup_form", clear_on_submit=True):
        followup = st.text_input(
            "Ask a follow-up",
            placeholder="e.g. 'What if we added a Saturday matinee?' or 'How does this compare to our best-performing film last year?'",
            label_visibility="collapsed",
        )
        ask_btn = st.form_submit_button("Ask →", type="primary")

    if ask_btn and followup.strip():
        context = f"We just generated a forecast for: {event_title} ({category}). " \
                  f"The forecast was:\n\n{forecast_result}\n\nFollow-up question: {followup.strip()}"
        st.session_state.forecast_chat.append({"role": "user", "content": followup.strip()})
        insights = InsightsAgent(agent)
        with st.spinner("Thinking..."):
            reply = insights.ask(context)
        st.session_state.forecast_chat.append({"role": "assistant", "content": reply})
        st.rerun()

else:
    # Empty state
    st.markdown('<div class="section-header">How It Works</div>', unsafe_allow_html=True)

    hw_col1, hw_col2, hw_col3 = st.columns(3)
    with hw_col1:
        st.markdown("""
        **1. Fill in event details**

        Enter the title, opening date, and key attributes — director and genre for films,
        artist and medium for exhibitions.
        """)
    with hw_col2:
        st.markdown("""
        **2. Claude analyzes comps**

        The system pulls historical BAMPFA events from the same category and season,
        then uses Claude to assess the new event's draw relative to past performance.
        """)
    with hw_col3:
        st.markdown("""
        **3. Get a full forecast**

        Receive three attendance scenarios (conservative / base / optimistic), a revenue
        estimate, week-by-week pattern, VX staffing recommendation, and risk factors.
        """)

    st.info(
        "💡 **Film tip:** Directors like Agnès Varda, Wong Kar-wai, or Akira Kurosawa "
        "will be assessed differently than debut or unknown directors. The more detail you "
        "provide, the more accurate the forecast.\n\n"
        "💡 **Exhibition tip:** Specify G1 vs. secondary gallery — G1 shows historically "
        "drive 2–3× more attendance than secondary spaces."
    )
