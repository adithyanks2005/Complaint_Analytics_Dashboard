"""
notifier.py – Notification helper for Complaint Analytics Dashboard
Sends email via Gmail SMTP  –or–  SMS via Twilio
depending on whether `contact` looks like an email or a phone number.

Required environment variables (set in .env or Streamlit secrets):
  GMAIL_SENDER_EMAIL   – your Gmail address (e.g. yourapp@gmail.com)
  GMAIL_APP_PASSWORD   – 16-char Gmail App Password (NOT your real password)
                         Generate at: https://myaccount.google.com/apppasswords
  TWILIO_ACCOUNT_SID   – Twilio Account SID
  TWILIO_AUTH_TOKEN    – Twilio Auth Token
  TWILIO_FROM_NUMBER   – Twilio phone number in E.164 format (e.g. +14155551234)
                         Note: Trial accounts can only message verified numbers.
"""
from __future__ import annotations

import os
import re
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Load .env from repo root if present
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ── Regex helpers ──────────────────────────────────────────────────────────────
_EMAIL_RE  = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MOBILE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{7,14}[0-9]$")
_E164_RE   = re.compile(r"^\+[1-9]\d{6,14}$")


def _is_email(contact: str) -> bool:
    return bool(_EMAIL_RE.match(contact.strip()))


def _is_phone(contact: str) -> bool:
    return bool(_MOBILE_RE.match(contact.strip()))


def _normalise_phone(phone: str) -> str:
    """Strip spaces/dashes and prepend +91 for bare 10-digit Indian numbers."""
    cleaned = re.sub(r"[\s\-]", "", phone.strip())
    if cleaned.startswith("+"):
        return cleaned
    if len(cleaned) == 10 and cleaned.isdigit():
        return f"+91{cleaned}"
    return cleaned


def credentials_configured() -> dict[str, bool]:
    """Return which notification channels have credentials configured."""
    email_ok = bool(
        os.environ.get("GMAIL_SENDER_EMAIL", "").strip() and
        os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    )
    from_num = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
    sms_ok = bool(
        os.environ.get("TWILIO_ACCOUNT_SID", "").strip() and
        os.environ.get("TWILIO_AUTH_TOKEN", "").strip() and
        _E164_RE.match(from_num)
    )
    return {"email": email_ok, "sms": sms_ok}


# ── Email via Gmail SMTP ───────────────────────────────────────────────────────
def send_email(to_address: str, subject: str, body: str) -> None:
    """Send an HTML email through Gmail SMTP (TLS on port 587)."""
    sender   = os.environ.get("GMAIL_SENDER_EMAIL", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD",  "").strip()

    if not sender or not password:
        raise RuntimeError(
            "Gmail credentials not configured. Set GMAIL_SENDER_EMAIL and "
            "GMAIL_APP_PASSWORD in your .env file."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to_address

    plain = re.sub(r"<[^>]+>", "", body)
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(body,  "html"))

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, to_address, msg.as_string())
    logger.info("Email sent to %s", to_address)


# ── SMS via Twilio ─────────────────────────────────────────────────────────────
def send_sms(to_phone: str, body: str) -> None:
    """Send an SMS through Twilio."""
    sid      = os.environ.get("TWILIO_ACCOUNT_SID",  "").strip()
    token    = os.environ.get("TWILIO_AUTH_TOKEN",   "").strip()
    from_num = os.environ.get("TWILIO_FROM_NUMBER",  "").strip()

    if not (sid and token and from_num):
        raise RuntimeError(
            "Twilio credentials not configured. Set TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER in your .env file."
        )

    try:
        from twilio.rest import Client  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "twilio package not installed. Run: pip install twilio"
        ) from exc

    client     = Client(sid, token)
    normalised = _normalise_phone(to_phone)
    client.messages.create(body=body, from_=from_num, to=normalised)
    logger.info("SMS sent to %s", normalised)


# ── Public API ─────────────────────────────────────────────────────────────────
def notify(contact: str, subject: str, message: str) -> None:
    """
    Route a notification to the right channel based on contact type.
    Raises an exception if sending fails so the caller can handle it.

    Args:
        contact: Email address OR phone number of the recipient.
        subject: Subject line (used for email; prepended to SMS body).
        message: Notification body (plain text or simple HTML for email).
    """
    contact = (contact or "").strip()
    if not contact:
        logger.debug("notify() called with empty contact — skipping.")
        return

    if _is_email(contact):
        html_body = f"""
        <html>
        <body style="font-family:Arial,sans-serif;color:#333;padding:24px;max-width:600px;margin:0 auto;">
          <div style="background:#6366f1;padding:16px 24px;border-radius:8px 8px 0 0;">
            <h2 style="color:white;margin:0;font-size:1.2rem;">Complaint Analytics Dashboard</h2>
          </div>
          <div style="background:#f8fafc;padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;">
            <p style="color:#374151;line-height:1.6;">{message}</p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
            <small style="color:#9ca3af;">This is an automated message from the Complaint Analytics Dashboard. Please do not reply.</small>
          </div>
        </body>
        </html>
        """
        send_email(contact, subject, html_body)

    elif _is_phone(contact):
        plain = re.sub(r"<[^>]+>", "", message).strip()
        send_sms(contact, f"{subject}\n\n{plain}")

    else:
        raise ValueError(
            f"Contact '{contact}' is not a valid email address or mobile number."
        )
