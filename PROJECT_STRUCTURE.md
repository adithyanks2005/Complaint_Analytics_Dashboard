# Project Structure

```
Complaint-Analytics-Dashboard/
├─ .git/                     # Git repository metadata
├─ backend/                  # Core application logic & database helpers
│   ├─ __init__.py
│   ├─ database.py           # SQLite / Supabase DB layer
│   ├─ pincode_lookup.py    # Helper to resolve Indian pincodes
│   └─ ...
├─ frontend/                 # Streamlit UI entry point
│   └─ streamlit_app.py      # Main Streamlit application
├─ data/                     # Sample data files (CSV, SQLite DB)
│   ├─ complaints.db
│   └─ sample_complaints.csv
├─ tests/                    # Automated tests
│   ├─ __init__.py
│   ├─ conftest.py
│   └─ test_api.py
└─ schema/                   # Database schema definitions (if any)
```

The above tree provides a clean, hierarchical view of all important files and directories in the project. Feel free to adjust or expand it as the project evolves.
