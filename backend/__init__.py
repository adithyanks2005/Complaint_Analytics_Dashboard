"""Backend package compatibility helpers."""

from datetime import date as _date
import builtins as _builtins

# The legacy Streamlit entrypoint references ``date`` without importing it.
# The backend package is imported before the sidebar is rendered, so provide
# the missing builtin until the entrypoint is updated with a direct import.
if not hasattr(_builtins, "date"):
    _builtins.date = _date
