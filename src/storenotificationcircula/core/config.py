from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def secret(key: str, default: str = "") -> str:
    value = os.getenv(key, default)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(key, default)
    except Exception:
        return default
