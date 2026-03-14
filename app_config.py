"""Application configuration helpers.
Reads settings from Streamlit secrets first, then environment variables.
"""

from __future__ import annotations

import os
from typing import Any


def _read_streamlit_secret(key: str) -> Any:
    try:
        import streamlit as st
    except Exception:
        return None

    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        return None
    return None


def get_setting(key: str, default: Any = None) -> Any:
    """Return configuration value from `st.secrets` or environment.

    Priority:
    1. `st.secrets[key]`
    2. `os.environ[key]`
    3. `default`
    """
    val = _read_streamlit_secret(key)
    if val is not None and str(val).strip() != "":
        return val

    env_val = os.getenv(key)
    if env_val is not None and str(env_val).strip() != "":
        return env_val

    return default


def get_bool_setting(key: str, default: bool = False) -> bool:
    raw = get_setting(key, default)
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}
