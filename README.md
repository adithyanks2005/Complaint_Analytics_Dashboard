# Complaint Analytics Dashboard

A Streamlit‑based dashboard that visualises public‑service complaint data.  
It uses a local SQLite fallback (or Supabase when configured) and features a premium glass‑morphic UI.

## Quick start (local)
```bash
# Create a virtual env (optional)
python -m venv .venv
\.venv\Scripts\activate.bat
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy to Streamlit Community Cloud
1. Fork or push this repository to GitHub (already done).
2. Visit **https://share.streamlit.io** and log in with GitHub.
3. Click **New app**, select this repo, branch `main`, and set the entry file to `streamlit_app.py`.
4. (Optional) Rename the app to **complaintanalyticsdashboard** – the public URL will become `https://complaintanalyticsdashboard.streamlit.app/`.
5. Click **Deploy** – Streamlit will install the packages from `requirements.txt` and launch the app.

## Configuration
- Place any secret keys (e.g. Supabase URL / Service key) in a `secrets.toml` file under the `.streamlit` folder, or add them via the **Secrets** tab on the Streamlit Cloud dashboard.
- The file `.streamlit/config.toml` already contains the minimal server configuration for the cloud.

---
Feel free to open issues or submit pull requests for enhancements!
