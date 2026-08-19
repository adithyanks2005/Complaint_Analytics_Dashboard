# Complaint Analytics Dashboard

A production-oriented complaint intake and analytics system for public-service teams. It combines a Streamlit dashboard, a FastAPI REST API, complaint validation, analytics, notifications, and a database layer designed for safe local development and authoritative cloud persistence.

## Product Features

- Public complaint submission with validation, photo attachments, and GPS-assisted location
- Automatic Low, Medium, or High priority classification
- Dashboard KPIs, monthly trends, category charts, area analytics, and CSV export
- Filters for date, location, category, and status
- Protected Streamlit admin workflow for updating and deleting complaints
- Optional email notifications through Gmail SMTP
- Optional SMS notifications through Twilio
- FastAPI endpoints for complaint CRUD, exports, options, health, and analytics
- Atomic complaint IDs (`CMP-001`, `CMP-002`, ...)
- Backend and database complaint-state invariants
- Structured logging for database, API, and notification failures
- Concurrent-submission protection for local SQLite development
- Supabase production persistence with database-owned ID generation
- No silent Supabase-to-SQLite failover

## Data-store contract

**Local development:** if Supabase variables are completely absent, SQLite is used from `data/complaints.db`.

**Hosted/production:** when Supabase is configured, Supabase is the **only** authoritative datastore. A Supabase outage returns a clear database-unavailable error; the application never writes a second copy to SQLite.

For production, use `SUPABASE_SERVICE_ROLE_KEY` only in trusted server-side secrets. Do not expose it to browser code.

## Run Locally

Requirements: Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Set a real random DASHBOARD_ADMIN_PASSWORD in .env
streamlit run streamlit_app.py
```

Open `http://localhost:8501`.

To run the API separately:

```powershell
uvicorn backend.main:app --reload
```

API documentation is available at `http://localhost:8000/docs`.

## Configuration

| Variable | Purpose |
|---|---|
| `DASHBOARD_ADMIN_USERNAME` | Streamlit admin username |
| `DASHBOARD_ADMIN_PASSWORD` | Long random admin password |
| `SUPABASE_URL` | Supabase project URL; enables authoritative cloud mode |
| `SUPABASE_SERVICE_ROLE_KEY` | Preferred server-side Supabase credential |
| `SUPABASE_KEY` | Alternate server-side Supabase key |
| `SUPABASE_TABLE` | Table name; defaults to `complaints` |
| `GOOGLE_MAPS_API_KEY` | Optional reverse geocoding for GPS-assisted location |
| `GMAIL_SENDER_EMAIL` | Gmail sender for email notifications |
| `GMAIL_APP_PASSWORD` | Gmail App Password |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_FROM_NUMBER` | Twilio sender in E.164 format |

Never commit `.env`, Supabase service-role keys, Twilio tokens, or Gmail app passwords.

## Supabase setup

Apply `supabase/migrations/20240101_init.sql` to the project before enabling production mode. The migration creates the complaint table, state constraints, indexes, RLS service-role policy, and an atomic Postgres sequence/trigger for complaint IDs.

The API health endpoints expose database availability:

- `GET /health`
- `GET /health/database`

A Supabase outage produces HTTP 503 instead of silently switching datastores.

## Test and Quality Checks

```powershell
pytest -q
python -m flake8 backend --max-line-length=120
```

The regression suite covers CRUD workflows, duplicate IDs, concurrent submissions, state invariants, Supabase failure/recovery, notification ID correctness, exports, empty analytics, image validation, GPS validation, and startup health checks.

CI also performs Python compilation, backend linting, FastAPI startup/health smoke tests, and Streamlit startup smoke tests.

## Deployment

### Streamlit Community Cloud

Use `streamlit_app.py` as the entry point and configure all secrets through the platform's secret management. Set a strong admin password and configure Supabase service-role credentials for the hosted datastore.

### Docker

```powershell
docker build -t complaint-dashboard .
docker run --env-file .env -p 8501:8501 complaint-dashboard
```

### FastAPI

```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Supabase

Run the migration once, then configure `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in the trusted server environment. Do not use the service-role key in client-side JavaScript.

## Main Entry Points

- Dashboard: `streamlit_app.py`
- Streamlit implementation: `frontend/streamlit_app.py`
- API: `backend/main.py`
- Database layer: `backend/database.py`
- Shared validation: `backend/validation.py`
- Analytics: `backend/analytics.py`
- Notifications: `frontend/notifier.py`
- Supabase schema: `supabase/migrations/20240101_init.sql`

## License

MIT
