"""
Preservation property tests for SMS notification not sent bugfix.

These tests encode CORRECT/UNCHANGED behaviour that must survive the fix.
All tests are expected to PASS on UNFIXED code — they confirm the baseline
that the fix must not regress.

Task 2 — Write preservation property tests (BEFORE implementing fix)
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Paths — load the REAL frontend modules by filesystem path
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

for p in [str(REPO_ROOT), str(FRONTEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def _load_frontend_streamlit_app():
    """Load frontend/streamlit_app.py as module 'frontend_streamlit_app'."""
    mod_name = "frontend_streamlit_app"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(
        mod_name,
        FRONTEND_DIR / "streamlit_app.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _call_notify_user(
    contact: str,
    message: str,
    session_state: dict,
    *,
    notifier_available: bool,
    notify_real_side_effect=None,
) -> dict:
    """
    Call the real notify_user() in a fully mocked Streamlit environment.
    Returns the session_state dict after the call.
    """
    app = _load_frontend_streamlit_app()
    mock_notify_real = MagicMock(side_effect=notify_real_side_effect)

    with (
        patch.object(app, "_NOTIFIER_AVAILABLE", notifier_available),
        patch.object(app, "_notify_real", mock_notify_real),
        patch("frontend_streamlit_app.st") as mock_st,
    ):
        mock_st.session_state = session_state
        app.notify_user(contact, message)

    return session_state


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Valid E.164: +[1-9][digits], total length 8–15 chars (+ sign + 7–14 digits)
_E164_STRATEGY = st.from_regex(r"^\+[1-9]\d{6,14}$", fullmatch=True)

# Non-E.164 strings: non-empty strings that do NOT match ^\+[1-9]\d{6,14}$
_NON_E164_STRATEGY = st.text(min_size=1).filter(
    lambda s: not __import__("re").match(r"^\+[1-9]\d{6,14}$", s)
)

# ---------------------------------------------------------------------------
# Property 1 (Hypothesis) — valid E.164 always accepted by credentials_configured
# Validates: Requirement 3.6
# ---------------------------------------------------------------------------

class TestValidE164AlwaysAccepted:
    """
    **Validates: Requirements 3.6**

    For any valid E.164 number (matching ^\\+[1-9]\\d{6,14}$) with valid SID
    and token set, credentials_configured()["sms"] must be True.

    EXPECTED TO PASS on unfixed code (and after the fix).
    """

    @given(phone=_E164_STRATEGY)
    @settings(max_examples=50)
    def test_valid_e164_sms_credentials_true(self, phone: str):
        """
        **Validates: Requirements 3.6**

        Generate valid E.164 phone numbers and assert credentials_configured()
        returns {"sms": True} for each when SID/token are also present.

        EXPECTED TO PASS on unfixed code.
        """
        import notifier as notifier_mod

        env_patch = {
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "TWILIO_AUTH_TOKEN": "authtoken1234567890abcdef12345678",
            "TWILIO_FROM_NUMBER": phone,
            "GMAIL_SENDER_EMAIL": "",
            "GMAIL_APP_PASSWORD": "",
        }
        # Force the module to re-read env on each call (no module-level caching)
        with patch.dict(os.environ, env_patch, clear=False):
            result = notifier_mod.credentials_configured()

        # On UNFIXED code this passes because unfixed code only checks non-empty.
        # Valid E.164 numbers are non-empty, so the unfixed code returns True.
        # After the fix, the regex also accepts valid E.164, so it still passes.
        assert result["sms"] is True, (
            f"Expected credentials_configured()['sms'] == True for valid E.164 "
            f"number {phone!r}, but got {result!r}"
        )


# ---------------------------------------------------------------------------
# Property 2 (Hypothesis) — non-E.164 strings rejected
# Validates: Requirement 2.3 (confirmed current baseline; checked explicitly)
#
# NOTE: This test exercises the UNFIXED code baseline for non-E.164 inputs.
# On UNFIXED code, the check is presence-only, so non-E.164 non-empty strings
# return sms=True. We therefore test a specific known behaviour from the UNFIXED
# code — that invalid E.164 placeholders like "+91" return sms=False AFTER the fix.
# For the preservation test file (tests on unfixed code), we instead verify:
#   - empty TWILIO_FROM_NUMBER → sms=False   (both before and after fix)
# ---------------------------------------------------------------------------

class TestEmptyFromNumberRejected:
    """
    **Validates: Requirements 3.6**

    When TWILIO_FROM_NUMBER is empty (or missing), credentials_configured()
    must return {"sms": False} regardless of whether SID/token are present.

    EXPECTED TO PASS on both unfixed and fixed code.
    """

    def test_empty_from_number_returns_sms_false(self):
        """
        An empty TWILIO_FROM_NUMBER with valid SID/token → sms=False.
        EXPECTED TO PASS on unfixed code.
        """
        import notifier as notifier_mod

        env_patch = {
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "TWILIO_AUTH_TOKEN": "authtoken1234567890abcdef12345678",
            "TWILIO_FROM_NUMBER": "",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            result = notifier_mod.credentials_configured()

        assert result["sms"] is False, (
            f"Expected credentials_configured()['sms'] == False for empty "
            f"TWILIO_FROM_NUMBER, but got {result!r}"
        )

    def test_missing_sid_returns_sms_false(self):
        """
        Missing TWILIO_ACCOUNT_SID → sms=False even with valid number.
        EXPECTED TO PASS on unfixed code.
        """
        import notifier as notifier_mod

        env_patch = {
            "TWILIO_ACCOUNT_SID": "",
            "TWILIO_AUTH_TOKEN": "authtoken1234567890abcdef12345678",
            "TWILIO_FROM_NUMBER": "+14155551234",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            result = notifier_mod.credentials_configured()

        assert result["sms"] is False, (
            f"Expected sms=False when TWILIO_ACCOUNT_SID is empty, got {result!r}"
        )

    def test_missing_token_returns_sms_false(self):
        """
        Missing TWILIO_AUTH_TOKEN → sms=False even with valid number.
        EXPECTED TO PASS on unfixed code.
        """
        import notifier as notifier_mod

        env_patch = {
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "TWILIO_AUTH_TOKEN": "",
            "TWILIO_FROM_NUMBER": "+14155551234",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            result = notifier_mod.credentials_configured()

        assert result["sms"] is False, (
            f"Expected sms=False when TWILIO_AUTH_TOKEN is empty, got {result!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Successful SMS path stores ("success", ...) banner
# Validates: Requirement 3.1
# ---------------------------------------------------------------------------

class TestSuccessfulSMSBannerPreserved:
    """
    **Validates: Requirements 3.1**

    When _NOTIFIER_AVAILABLE=True and _notify_real succeeds (no exception),
    notify_user() must store ("success", ...) in session_state["notify_msg"].

    EXPECTED TO PASS on unfixed code (success path is not broken).
    """

    def test_successful_notify_stores_success_banner(self):
        """
        Mock _NOTIFIER_AVAILABLE=True, _notify_real succeeds →
        session_state["notify_msg"] == ("success", ...)

        EXPECTED TO PASS on unfixed code.
        """
        session_state: dict = {}
        _call_notify_user(
            "+919876543210",
            "Your complaint has been registered.",
            session_state,
            notifier_available=True,
            notify_real_side_effect=None,  # no exception → success
        )

        stored = session_state.get("notify_msg")
        assert stored is not None, "notify_msg was not written to session_state"
        level, text = stored

        assert level == "success", (
            f"Expected level 'success' on successful notify, got {level!r}. "
            f"Stored: {stored!r}"
        )

    def test_successful_notify_banner_contains_contact(self):
        """
        The success banner should reference the contact so the operator
        knows who was notified.

        EXPECTED TO PASS on unfixed code.
        """
        session_state: dict = {}
        contact = "+14155551234"
        _call_notify_user(
            contact,
            "Your complaint has been registered.",
            session_state,
            notifier_available=True,
            notify_real_side_effect=None,
        )

        stored = session_state.get("notify_msg")
        assert stored is not None
        _, text = stored
        assert contact in text, (
            f"Expected contact {contact!r} to appear in success banner text, "
            f"but got {text!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — Email contacts route to email path, not SMS
# Validates: Requirement 3.2
# ---------------------------------------------------------------------------

class TestEmailPathUnaffected:
    """
    **Validates: Requirements 3.2**

    When notify_user() is called with an email address as the contact,
    it must route to the email (notify_real) path, not the SMS path.
    The session state SMS key is not written by email routing logic alone.

    EXPECTED TO PASS on unfixed code.
    """

    def test_email_contact_calls_notify_real(self):
        """
        An email address as contact should invoke _notify_real (which in the
        real notifier routes to send_email internally).

        We verify _notify_real is called with the email contact.

        EXPECTED TO PASS on unfixed code.
        """
        session_state: dict = {}
        app = _load_frontend_streamlit_app()

        mock_notify_real = MagicMock(return_value=None)

        with (
            patch.object(app, "_NOTIFIER_AVAILABLE", True),
            patch.object(app, "_notify_real", mock_notify_real),
            patch("frontend_streamlit_app.st") as mock_st,
        ):
            mock_st.session_state = session_state
            app.notify_user("user@example.com", "test message")

        # _notify_real must have been called once with the email contact
        mock_notify_real.assert_called_once()
        call_args = mock_notify_real.call_args
        # First positional argument should be the contact
        assert call_args[0][0] == "user@example.com", (
            f"Expected _notify_real to be called with email contact, "
            f"got {call_args!r}"
        )

    def test_email_contact_stores_success_banner(self):
        """
        Successful email notification stores ("success", ...) in session_state,
        confirming the email code path goes through the same success branch.

        EXPECTED TO PASS on unfixed code.
        """
        session_state: dict = {}
        _call_notify_user(
            "user@example.com",
            "Test email message",
            session_state,
            notifier_available=True,
            notify_real_side_effect=None,
        )

        stored = session_state.get("notify_msg")
        assert stored is not None, "notify_msg not written for email contact"
        level, _ = stored
        assert level == "success", (
            f"Expected 'success' banner for email contact, got {level!r}. "
            f"Stored: {stored!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Empty contact: notify_user returns without touching session_state
# Validates: Requirement 3.3
# ---------------------------------------------------------------------------

class TestNoContactEarlyReturn:
    """
    **Validates: Requirements 3.3**

    notify_user("", "msg") must return immediately without writing any key
    to st.session_state.

    EXPECTED TO PASS on unfixed code.
    """

    def test_empty_contact_no_session_state_written(self):
        """
        notify_user("", "msg") → no keys written to session_state.

        EXPECTED TO PASS on unfixed code.
        """
        session_state: dict = {}
        _call_notify_user(
            "",
            "This message should never appear",
            session_state,
            notifier_available=True,
        )

        assert len(session_state) == 0, (
            f"Expected empty session_state after empty contact, "
            f"but got keys: {list(session_state.keys())}"
        )

    def test_whitespace_only_contact_no_session_state_written(self):
        """
        notify_user("   ", "msg") → no keys written (whitespace stripped to empty).

        EXPECTED TO PASS on unfixed code.
        """
        session_state: dict = {}
        _call_notify_user(
            "   ",
            "This message should never appear",
            session_state,
            notifier_available=True,
        )

        assert len(session_state) == 0, (
            f"Expected empty session_state after whitespace-only contact, "
            f"but got keys: {list(session_state.keys())}"
        )
