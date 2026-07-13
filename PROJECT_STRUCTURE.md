# Project Structure

```
Complaint-Analytics-Dashboard/
│
├── backend/                        # Core application logic
│   ├── __init__.py
│   ├── ai_prioritizer.py           # AI-based complaint priority classifier
│   ├── analytics.py                # Data aggregation & analytics functions
│   ├── database.py                 # SQLite / Supabase DB layer (CRUD + migrations)
│   ├── main.py                     # FastAPI REST API entry point
│   └── pincode_lookup.py           # Indian pincode → location resolver
│
├── frontend/                       # Streamlit UI
│   ├── notifier.py                 # Email (Gmail SMTP) & SMS (Twilio) notifications
│   └── streamlit_app.py            # Main dashboard application
│
├── data/                           # Data files
│   ├── sample_complaints.csv       # Seed data (100 complaints across 12 states)
│   └── complaints.db               # SQLite database (auto-created, gitignored)
│
├── tests/                          # Automated test suite
│   ├── __init__.py
│   ├── test_api.py                 # FastAPI endpoint tests
│   └── test_database.py            # Database CRUD tests
│
├── scripts/                        # Utility & maintenance scripts
│   ├── backfill_locations.py       # Backfill missing state/district/municipality
│   └── test_backend.py             # Manual DB smoke test
│
├── api/                            # Vercel serverless entry point
│   ├── index.py                    # Mounts FastAPI app for Vercel deployment
│   └── requirements.txt            # Vercel-specific dependencies
│
├── supabase/                       # Supabase cloud DB config
│   └── migrations/
│       └── 20240101_init.sql       # Initial schema migration
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
│
├── .streamlit/
│   └── config.toml                 # Streamlit theme & server config
│
├── .env.example                    # Environment variable template
├── .gitignore
├── conftest.py                     # Pytest root config
├── Dockerfile                      # Container build definition
├── LICENSE
├── README.md
├── requirements.txt                # Python dependencies
├── setup.cfg                       # Flake8 / tool config
├── streamlit_app.py                # Root entry point (delegates to frontend/)
└── vercel.json                     # Vercel deployment config
```

## Key Entry Points

| Purpose | File |
|---|---|
| Run dashboard | `streamlit run streamlit_app.py` |
| Run API server | `uvicorn backend.main:app --reload` |
| Run tests | `pytest tests/` |
| Backfill DB locations | `python scripts/backfill_locations.py` |

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL (optional, falls back to SQLite) |
| `SUPABASE_KEY` | Supabase API key |
| `GMAIL_SENDER_EMAIL` | Gmail address for email notifications |
| `GMAIL_APP_PASSWORD` | Gmail App Password (16-char) |
| `TWILIO_ACCOUNT_SID` | Twilio SID for SMS notifications |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_FROM_NUMBER` | Twilio phone number (E.164 format) |
| `GOOGLE_MAPS_API_KEY` | Google Maps Geocoding API key (for GPS autofill) |
