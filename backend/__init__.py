"""Backend package compatibility helpers."""

from datetime import date as _date
import builtins as _builtins

# The deployed legacy Streamlit entrypoint references ``date`` without a local
# import. backend is imported before the sidebar is rendered, so make the name
# available process-wide while the entrypoint is being migrated.
if not hasattr(_builtins, "date"):
    _builtins.date = _date
