import sys
"""Streamlit Cloud entrypoint.

The maintained UI lives in frontend/streamlit_app.py. This wrapper normalizes
common Streamlit secret formatting mistakes before the backend is imported.
"""

import os

import streamlit as st

try:
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
    if os.getenv("SUPABASE_URL", "").endswith(".supabase.com"):
        os.environ["SUPABASE_URL"] = os.environ["SUPABASE_URL"].replace(
            ".supabase.com", ".supabase.co"
        )
except Exception:
    pass

from frontend.streamlit_app import *  # noqa: F401,F403,E402
