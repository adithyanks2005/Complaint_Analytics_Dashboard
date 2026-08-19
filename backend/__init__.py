"""Backend package initialization and Streamlit Cloud secret bridge."""

import os
from datetime import date as _date
import builtins as _builtins

# Streamlit Cloud secrets are exposed through ``st.secrets`` rather than
# automatically becoming environment variables. The database layer reads its
# configuration from ``os.environ``, so bridge the supported production secret
# names before importing backend.database.
try:  # pragma: no cover - depends on Streamlit runtime
    import streamlit as _st

    if hasattr(_st, "secrets"):
        for _key, _value in _st.secrets.items():
            if isinstance(_value, str) and _value.strip() and _key not in os.environ:
                os.environ[_key] = _value.strip().strip('"').strip("'")
except Exception:
    # Backend imports must also work outside Streamlit (FastAPI/pytest/CLI).
    pass

# Keep legacy Streamlit entrypoints compatible while all pages migrate to
# explicit datetime imports. The backend package is imported before widgets
# render, so exposing ``date`` here prevents a stale entrypoint from crashing.
if not hasattr(_builtins, "date"):
    _builtins.date = _date
