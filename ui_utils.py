"""Reusable UI safety helpers."""

from __future__ import annotations

import streamlit as st
from app_logging import log_exception


def show_friendly_error(user_message: str, context: str, exc: Exception | None = None) -> None:
    """Show safe message to users while logging technical details internally."""
    if exc is not None:
        log_exception(context, exc)
    st.error(user_message)


def show_info_card(title: str, description: str) -> None:
    st.markdown(f"**{title}**")
    st.caption(description)
