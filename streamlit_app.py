from pathlib import Path
import sys
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if not (PROJECT_ROOT / "backend").exists():
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import (
    DuplicateComplaintError,
    delete_complaint_record,
    insert_complaint,
    init_db,
    read_complaints_df,
    update_complaint_record,
)

# Keep the rest of the application unchanged; this commit fixes the runtime
# dependency explicitly: both date and datetime are required by the form/admin UI.
