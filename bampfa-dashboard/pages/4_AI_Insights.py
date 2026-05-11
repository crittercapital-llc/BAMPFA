"""
pages/4_AI_Insights.py
BAMPFA Audience Analytics — "Ask" AI: Dexibit-style conversational insight tool.

Modeled on Dexibit's "Ask" feature: GPT intelligence tuned to visitor-attraction
data, organized suggested questions by topic area, and connected to all BAMPFA
data sources so any team member can get instant analytical answers.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.data_agent import DataAgent
from agents.insights_agent import InsightsAgent

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Ask | BAMPFA Analytics",
    page_icon="💬",
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
      .chat-message-user { background: #1e1e30; border: 1px solid #2d2d4a;
          border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.5rem; color: #e0e0e0; }
      .chat-message-assistant { background: #141424; border: 1px solid #2d2d4a;
          border-left: 4px solid #c8a96e; border-radius: 8px;
          padding: 0.8rem 1rem; margin-bottom: 1rem; color: #d0d0d0; }
      .topic-label { color: #a0b4c8; font-size: 0.72rem; font-weight: 600;
          text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.4rem; }
      #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Load data & agents
# ---------------------------------------------------------------------------

@st.cache_resource
def get_agent():
    return DataAgent()

agent = get_agent()
insights_agent = InsightsAgent(agent)
data_summary = agent.get_data_summary_for_ai()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>💬 Ask — AI Audience Intelligence</h2>
        <p>Ask anything about BAMPFA's visitors, programs, membership, and revenue.
           GPT-grade intelligence connected directly to your data — no dashboards or
           data requests required. Powered by Anthropic Claude.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# API key status
if not insights_agent.has_api_key:
    st.warning(
        "**Ask is in demo mode.** Add `ANTHROPIC_API_KEY` to your `.env` file to enable "
        "live Claude-powered answers. The interface is fully functional once connected.",
        icon="⚠️",
    )
else:
    st.success("Ask is connected to Claude — ready to answer questions about your data.", icon="✓")

# ---------------------------------------------------------------------------
# Sidebar: data context & controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Ask Controls")
    st.markdown("---")

    focus_area = st.selectbox(
        "Focus Area",
        options=[
            "All Data",
            "Attendance & Programs",
            "Membership & Conversion",
            "Revenue & Spend",
            "Visitor Flow & Experience",
            "Planning & Forecasting",
        ],
        index=0,
        help="Narrows the data context sent to Claude for more targeted answers.",
    )

    st.markdown("---")
    st.caption(
        "Claude receives a structured data summary on every query. "
        "Expand below to see what context is sent."
    )
    with st.expander("View data context"):
        st.code(data_summary, language="text")

    st.markdown("---")
    if st.button("Clear Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ---------------------------------------------------------------------------
# Suggested questions — organized by topic (Dexibit "Ask" style)
# ---------------------------------------------------------------------------

QUESTION_TOPICS = {
    "📊 Attendance & Programs": [
        "Why did attendance peak in October and November?",
        "Which exhibitions drove the highest per-visitor revenue?",
        "How does film attendance compare to gallery attendance seasonally?",
        "What's the impact of school breaks on our monthly visitor count?",
    ],
    "👥 Membership & Conversion": [
        "Which zip codes should we target for a membership acquisition campaign?",
        "How do we reduce our 30% membership lapse rate?",
        "Which non-members are our warmest conversion targets right now?",
        "What acquisition channel produces the most loyal members?",
    ],
    "💰 Revenue & Spend": [
        "What's driving the gap between our per-capita spend and the $20 industry benchmark?",
        "How can we increase F&B and retail revenue per visitor?",
        "Which ticket types generate the highest revenue per transaction?",
        "Compare member vs. non-member revenue contribution this year.",
    ],
    "🗺️ Visitor Experience": [
        "Which galleries have the lowest engagement — and what can we do about it?",
        "When should we schedule docent tours to maximize visitor contact?",
        "What's the optimal staffing level for a peak Saturday in summer?",
        "How do our Google review ratings correlate with attendance?",
    ],
    "🔮 Planning & Strategy": [
        "What events should we prioritize for fall 2026 based on historical patterns?",
        "Which months are historically weakest — and what programming could lift them?",
        "How should we adjust our marketing calendar around school breaks?",
        "What would it take to grow annual visitation by 15%?",
    ],
}

st.markdown('<div class="section-header">Ask a Question</div>', unsafe_allow_html=True)

# Compact question picker using tabs
topic_tabs = st.tabs(list(QUESTION_TOPICS.keys()))

for tab, (topic, questions) in zip(topic_tabs, QUESTION_TOPICS.items()):
    with tab:
        q_cols = st.columns(2)
        for i, q in enumerate(questions):
            with q_cols[i % 2]:
                if st.button(q, key=f"sq_{topic}_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": q})
                    with st.spinner("Ask is thinking..."):
                        response = insights_agent.ask_with_history(
                            q,
                            st.session_state.chat_history[:-1],
                        )
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    st.rerun()

# ---------------------------------------------------------------------------
# Free-text input
# ---------------------------------------------------------------------------

with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_area(
        "Or type your own question",
        placeholder=(
            "e.g. 'What's a creative campaign to capture tourist visitors in August?' or "
            "'Compare this year's membership cohort retention to 2024.'"
        ),
        height=80,
        label_visibility="visible",
    )
    sub_col, _ = st.columns([1, 4])
    with sub_col:
        submitted = st.form_submit_button("Ask →", use_container_width=True, type="primary")

if submitted and user_input.strip():
    # Prepend focus area to question if not "All Data"
    enriched = user_input.strip()
    if focus_area != "All Data":
        enriched = f"[Focus: {focus_area}] {enriched}"
    st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
    with st.spinner("Ask is analyzing your data..."):
        response = insights_agent.ask_with_history(
            enriched,
            st.session_state.chat_history[:-1],
        )
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()

# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------

if st.session_state.chat_history:
    st.markdown('<div class="section-header">Conversation</div>', unsafe_allow_html=True)

    for message in reversed(st.session_state.chat_history):
        if message["role"] == "user":
            st.markdown(
                f'<div class="chat-message-user"><strong>You</strong><br>{message["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.container():
                st.markdown("**Claude's Analysis**")
                st.markdown(message["content"])
                st.markdown("---")
else:
    st.caption(
        "No conversation yet. Click a suggested question above or type your own below."
    )

# ---------------------------------------------------------------------------
# Data context footer
# ---------------------------------------------------------------------------

st.markdown("---")
foot_col1, foot_col2, foot_col3, foot_col4 = st.columns(4)
with foot_col1:
    st.caption(f"**Transactions:** {len(agent.transactions):,}")
with foot_col2:
    st.caption(f"**Members:** {len(agent.members):,}")
with foot_col3:
    st.caption(f"**Reviews:** {len(agent.reviews):,}")
with foot_col4:
    st.caption(f"**Web traffic rows:** {len(agent.web_traffic):,}")
