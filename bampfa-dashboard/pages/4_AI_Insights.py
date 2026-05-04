"""
pages/4_AI_Insights.py
BAMPFA Audience Analytics — AI-powered insights chat interface.
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
    page_title="AI Insights | BAMPFA Analytics",
    page_icon="🤖",
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
      .suggested-btn { margin-bottom: 0.5rem; }
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
# Built once per render for the sidebar "view data context" expander.
data_summary = agent.get_data_summary_for_ai()

# ---------------------------------------------------------------------------
# Session state for conversation history
# ---------------------------------------------------------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of {"role": str, "content": str}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="page-header">
        <h2>AI Audience Insights</h2>
        <p>Ask Claude anything about BAMPFA's audience data. Powered by Anthropic claude-sonnet-4-5.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# API key status banner
if not insights_agent.has_api_key:
    st.warning(
        "**AI insights are in demo mode.** Add `ANTHROPIC_API_KEY` to your `.env` file to enable "
        "live Claude-powered analysis. The chat interface below is fully functional once connected.",
        icon="⚠️",
    )
else:
    st.success("Connected to Claude claude-sonnet-4-5", icon="✓")

# ---------------------------------------------------------------------------
# Sidebar: data context preview
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### AI Context")
    st.markdown("---")
    st.caption(
        "Claude receives a structured data summary on every query. "
        "You can expand the preview below to see exactly what context is sent."
    )
    with st.expander("View data context sent to Claude"):
        st.code(data_summary, language="text")
    st.markdown("---")
    if st.button("Clear Conversation", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ---------------------------------------------------------------------------
# Suggested questions
# ---------------------------------------------------------------------------

SUGGESTED_QUESTIONS = [
    "Which zip codes should we target for a membership acquisition campaign?",
    "What's driving our peak attendance in October and November?",
    "How do we reduce our 30% membership lapse rate?",
    "Which film titles are underperforming relative to marketing spend?",
]

st.markdown('<div class="section-header">Suggested Questions</div>', unsafe_allow_html=True)

sq_cols = st.columns(2)
for i, q in enumerate(SUGGESTED_QUESTIONS):
    with sq_cols[i % 2]:
        if st.button(f"💬 {q}", key=f"sq_{i}", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": q})
            with st.spinner("Thinking..."):
                response = insights_agent.ask_with_history(
                    q,
                    st.session_state.chat_history[:-1],
                )
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()

# ---------------------------------------------------------------------------
# Chat history display
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Conversation</div>', unsafe_allow_html=True)

if not st.session_state.chat_history:
    st.caption("No conversation yet. Type a question below or click a suggested question above.")

for message in st.session_state.chat_history:
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

# ---------------------------------------------------------------------------
# Input box
# ---------------------------------------------------------------------------

st.markdown('<div class="section-header">Ask a Question</div>', unsafe_allow_html=True)

with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_area(
        "Your question",
        placeholder=(
            "e.g., 'Which membership tier has the highest retention rate?' or "
            "'What events should we prioritize for fall 2026 based on historical patterns?'"
        ),
        height=90,
        label_visibility="collapsed",
    )
    submit_col, _ = st.columns([1, 4])
    with submit_col:
        submitted = st.form_submit_button("Send", use_container_width=True, type="primary")

if submitted and user_input.strip():
    st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
    with st.spinner("Claude is analyzing your data..."):
        history_for_context = st.session_state.chat_history[:-1]
        response = insights_agent.ask_with_history(
            user_input.strip(),
            history_for_context,
        )
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    st.rerun()

# ---------------------------------------------------------------------------
# Data context stats (footer)
# ---------------------------------------------------------------------------

st.markdown("---")
kpis = agent.get_ytd_kpis()
foot_col1, foot_col2, foot_col3 = st.columns(3)
with foot_col1:
    st.caption(f"**Transactions in context:** {len(agent.transactions):,}")
with foot_col2:
    st.caption(f"**Members in context:** {len(agent.members):,}")
with foot_col3:
    st.caption(f"**Reviews in context:** {len(agent.reviews):,}")
