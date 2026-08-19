"""Backend package compatibility helpers."""

from datetime import date as _date
import builtins as _builtins

# Keep legacy Streamlit entrypoints compatible while all pages migrate to
# explicit datetime imports. The backend package is imported before widgets
# render, so exposing ``date`` here prevents a stale entrypoint from crashing.
if not hasattr(_builtins, "date"):
    _builtins.date = _date
