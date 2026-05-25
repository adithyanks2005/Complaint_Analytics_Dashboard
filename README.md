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

### Email OTP delivery
Citizen login can send OTPs to email when SMTP settings are configured in Streamlit secrets:

```toml
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = "587"
SMTP_USERNAME = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
SMTP_FROM = "your-email@gmail.com"
SMTP_USE_TLS = "true"
```

If SMTP is not configured, the app runs in demo mode and shows the OTP on screen.

### SMS OTP delivery
Mobile OTPs are sent with Twilio when these Streamlit secrets are configured:

```toml
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your-twilio-auth-token"
TWILIO_FROM_NUMBER = "+1234567890"
TWILIO_DEFAULT_COUNTRY_CODE = "+91"
```

Mobile numbers entered without a country code use `TWILIO_DEFAULT_COUNTRY_CODE`. If Twilio is not configured or the SMS API rejects the number, the app shows the demo OTP on screen.

---
Feel free to open issues or submit pull requests for enhancements!
