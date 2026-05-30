# Complaint Analytics Dashboard 📊
![CI](https://github.com/adithyanks2005/Complaint_Analytics_Dashboard/actions/workflows/ci.yml/badge.svg) ![Docker](https://ghcr-badge.egpl.io/adithyanks2005/complaint-dashboard)

![Dashboard UI Mockup](file:///C:/Users/adith/.gemini/antigravity-ide/brain/a3f07fd0-16a1-4c6b-85c3-d5c843a4a95f/dashboard_ui_mockup_1780164687369.png)

A **premium, production‑ready** complaint‑analytics dashboard built with **Streamlit** (frontend) and a lightweight **SQLite** backend (optionally Supabase). The repository includes:

- **Dockerfile** – containerised runtime
- **GitHub Actions CI** – lint, test, and Docker image build on every push
- **Comprehensive pytest suite** in `tests/`
- **Flake8 configuration** (`setup.cfg`)
- **Environment template** (`.env.example`)
- **Full documentation** (this README)
- **Beautiful dark‑mode UI** (see mockup above)

---

## ✨ Features
- Interactive charts & tables powered by **Plotly** and **Pandas**
- Sidebar filters for date range, area, category, status
- Optional Supabase sync for cloud persistence
- SMS/email notifications via **Twilio** / **Gmail** (configurable)
- Automatic Docker image generation (`ghcr.io/...` can be added later)
- CI pipeline that runs lint, unit tests and builds the Docker image

---

## 📦 Quick start (local)
```bash
# Clone the repo (already done)
cd Complaint-Analytics-Dashboard

# Create a virtual env and install deps
python -m venv .venv
# Windows: .venv\Scripts\activate   Linux/macOS: source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# (Optional) copy the env template and fill values
cp .env.example .env
# edit .env with your Supabase/Twilio/Gmail credentials if needed

# Run the dashboard
streamlit run frontend/streamlit_app.py --server.port 8501
```
Open `http://localhost:8501` in a browser.

---

## 🐳 Run with Docker
```bash
# Build the image (the CI does this automatically)
docker build -t complaint-dashboard .

# Run the container, exposing Streamlit's port
docker run -d -p 8501:8501 \
  -v $(pwd)/.env:/app/.env \
  --name complaint-dashboard \
  complaint-dashboard
```
Visit `http://localhost:8501` (or replace `localhost` with your host IP).

---

## ✅ Testing
```bash
pytest tests -q   # 7 passed
```
The test suite covers CRUD operations, ID generation, duplicate handling, and more.

---

## 🚀 CI / CD (GitHub Actions)
The workflow lives at `.github/workflows/ci.yml` and runs on every push & PR:
1. **Checkout** the repo
2. **Set up Python 3.12**
3. **Install dependencies** (including optional Supabase/Twilio)
4. **Lint** `backend/` with **flake8**
5. **Run tests** in `tests/`
6. **Build Docker image** (available as `complaint-dashboard` locally – you can push to a registry by extending the workflow).

---

## 🛠️ Customisation
- Modify `frontend/streamlit_app.py` to add new visualisations or filters.
- Extend the `backend/database.py` module for extra tables or Supabase features.
- Update `requirements.txt` for new Python packages; CI will pick them up automatically.

---

## 📄 License
This project is licensed under the **MIT License** – feel free to fork, modify, and deploy.
