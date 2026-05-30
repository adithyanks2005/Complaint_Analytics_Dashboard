"""
notifier.py – Notification helper for Complaint Analytics Dashboard
Sends email via Gmail SMTP  –or–  SMS via Twilio
depending on whether `contact` looks like an email or a phone number.

Required environment variables (set in .env or Streamlit secrets):
  GMAIL_SENDER_EMAIL   – your Gmail address (e.g. yourapp@gmail.com)
  GMAIL_APP_PASSWORD   – 16-char Gmail App Password (NOT your real password)
  TWILIO_ACCOUNT_SID   – Twilio Account SID
  TWILIO_AUTH_TOKEN    – Twilio Auth Token
  TWILIO_FROM_NUMBER   – Twilio phone number in E.164 format (e.g. +14155551234)
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


# ── Email via Gmail SMTP ───────────────────────────────────────────────────────
def send_email(to_address: str, subject: str, body: str) -> None:
    """Send an HTML email through Gmail SMTP (TLS on port 587)."""
    sender    = os.environ.get("GMAIL_SENDER_EMAIL", "").strip()
    password  = os.environ.get("GMAIL_APP_PASSWORD",  "").strip()

    if not sender or not password:
        logger.warning("Gmail credentials not set – email not sent to %s", to_address)
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to_address

    # Plain-text fallback + HTML version
    plain = re.sub(r"<[^>]+>", "", body)
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(body,  "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_address, msg.as_string())
        logger.info("Email sent to %s", to_address)
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_address, exc)
        raise


# ── SMS via Twilio ─────────────────────────────────────────────────────────────
def send_sms(to_phone: str, body: str) -> None:
    """Send an SMS through Twilio."""
    sid       = os.environ.get("TWILIO_ACCOUNT_SID",  "").strip()
    token     = os.environ.get("TWILIO_AUTH_TOKEN",   "").strip()
    from_num  = os.environ.get("TWILIO_FROM_NUMBER",  "").strip()

    if not (sid and token and from_num):
        logger.warning("Twilio credentials not set – SMS not sent to %s", to_phone)
        return

    try:
        from twilio.rest import Client  # type: ignore
        client = Client(sid, token)
        normalised = _normalise_phone(to_phone)
        client.messages.create(body=body, from_=from_num, to=normalised)
        logger.info("SMS sent to %s", normalised)
    except ImportError:
        logger.error("twilio package not installed. Run: pip install twilio")
        raise
    except Exception as exc:
        logger.error("Failed to send SMS to %s: %s", to_phone, exc)
        raise


# ── Public API ─────────────────────────────────────────────────────────────────
def notify(contact: str, subject: str, message: str) -> None:
    """
    Route a notification to the right channel based on contact type.

    Args:
        contact: Email address OR phone number of the recipient.
        subject: Subject line (used for email; SMS body is `message`).
        message: Notification body (plain text or simple HTML for email).
    """
    contact = (contact or "").strip()
    if not contact:
        logger.debug("notify() called with empty contact – skipping.")
        return

    if _is_email(contact):
        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;color:#333;padding:20px;">
          <h2 style="color:#1a73e8;">Complaint Analytics Dashboard</h2>
          <p>{message}</p>
          <hr style="border:none;border-top:1px solid #eee;margin:24px 0;">
          <small style="color:#888;">This is an automated message. Please do not reply.</small>
        </body></html>
        """
        send_email(contact, subject, html_body)
    elif _is_phone(contact):
        send_sms(contact, f"{subject}\n{message}")
    else:
        logger.warning("Unknown contact format '%s' – notification skipped.", contact)
