"""
agents/_anthropic.py
Shared helper for Claude API access. Loads the API key from .env (local) or
Streamlit secrets (Cloud), and constructs a configured Anthropic client.

All AI-powered agents (Insights, Forecasting, Conversion, Briefing) use this
so the .env + secrets fallback isn't duplicated five times.
"""

import os

from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-5"


def _api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


def get_client():
    """Returns a configured Anthropic client, or None if no key / SDK is available."""
    key = _api_key()
    if not key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=key)
    except ImportError:
        return None


def has_api_key() -> bool:
    return bool(_api_key())
