# Complaint Analytics Dashboard

A production-oriented complaint intake and analytics system for public-service teams.
It combines a Streamlit dashboard, a FastAPI REST API, SQLite for local persistence,
and optional Supabase cloud storage.

## Product Features

- Public complaint submission with validation, photo attachments, and GPS-assisted location
- Automatic Low, Medium, or High priority classification
- Dashboard KPIs, monthly trends, category charts, area analytics, and CSV export
- Filters for date, location, category, and status
- Protected Streamlit admin workflow for updating and deleting complaints
- Optional email notifications through Gmail SMTP
- Optional SMS notifications through Twilio
- FastAPI endpoints for complaint CRUD, exports, options, and analytics
- SQLite by default with automatic schema migration and sample data
- Optional Supabase persistence for hosted environments

## Run Locally

Requirements: Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run streamlit_app.py
```

Open `http://localhost:8501`.

To run the API separately:

```powershell
uvicorn backend.main:app --reload
```

API documentation is available at `http://localhost:8000/docs`.

## Configuration

All integrations are optional. Without cloud credentials, the app uses
`data/complaints.db`.

| Variable | Purpose |
|---|---|
| `DASHBOARD_ADMIN_USERNAME` | Enables the Streamlit admin login |
| `DASHBOARD_ADMIN_PASSWORD` | Admin password; use a long random value |
| `SUPABASE_URL` | Optional Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Preferred server-side Supabase credential |
| `SUPABASE_KEY` | Supabase key fallback |
| `SUPABASE_TABLE` | Table name; defaults to `complaints` |
| `GOOGLE_MAPS_API_KEY` | Optional reverse geocoding for GPS location |
| `GMAIL_SENDER_EMAIL` | Gmail sender for email notifications |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_FROM_NUMBER` | Twilio sender in E.164 format |

Never commit `.env` or production secrets.

## Test and Quality Checks

```powershell
pytest -q
python -m flake8 backend
```

The suite covers database CRUD and migrations, API reads, analytics behavior,
notification routing, validation, and regression cases.

## Deployment

### Streamlit Community Cloud

Use `streamlit_app.py` as the entry point and add environment values through
the platform's secret management.

### Docker

```powershell
docker build -t complaint-dashboard .
docker run --env-file .env -p 8501:8501 complaint-dashboard
```

### Vercel API

`vercel.json` deploys the FastAPI application from `api/index.py`. This hosts
the API only; deploy the Streamlit interface separately.

### Supabase

Run `supabase/migrations/20240101_init.sql`, then configure the Supabase
environment variables. Use a service-role key only in trusted server-side
environments.

## Main Entry Points

- Dashboard: `streamlit_app.py`
- Streamlit implementation: `frontend/streamlit_app.py`
- API: `backend/main.py`
- Database layer: `backend/database.py`
- Analytics: `backend/analytics.py`
- Notifications: `frontend/notifier.py`

## License

MIT
