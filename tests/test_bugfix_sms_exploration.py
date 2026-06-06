"""
Bug condition exploration tests for SMS notification not sent.

These tests encode the EXPECTED (correct) behaviour. They are run FIRST
against the UNFIXED code, so they are expected to FAIL. Failures are
documented as counterexamples that confirm each bug exists.

Task 1 — Write bug condition exploration tests (all three bugs)
Validates: Requirements 1.1, 1.2, 1.3, 1.4
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Paths — load the REAL frontend module by filesystem path to avoid
# picking up the root-level runpy wrapper (streamlit_app.py at repo root).
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

# Ensure repo root is on sys.path so backend/ imports inside streamlit_app work
for p in [str(REPO_ROOT), str(FRONTEND_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def _load_frontend_streamlit_app():
    """
    Load frontend/streamlit_app.py as module 'frontend_streamlit_app',
    bypassing the root-level wrapper so we get _NOTIFIER_AVAILABLE etc.
    """
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_streamlit_session_mock():
    """Return a plain dict that acts as st.session_state."""
    return {}


def _call_notify_user(contact: str, message: str, session_state: dict, *, notifier_available: bool, notify_real_side_effect=None):
    """
    Load the REAL frontend/streamlit_app.py and call notify_user() in a
    fully mocked Streamlit environment.

    We patch:
      - frontend_streamlit_app._NOTIFIER_AVAILABLE
      - frontend_streamlit_app._notify_real  (optionally raise)
      - st.session_state                      (replaced by a plain dict)
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
# Bug A — Silent notifier fallback: info banner with message body leaked
# ---------------------------------------------------------------------------

class TestBugAExploration:
    """
    **Bug A — Validates: Requirements 1.1, 1.4**

    Bug condition: _NOTIFIER_AVAILABLE == False AND contact is non-empty.

    Unfixed code sets:
        st.session_state["notify_msg"] = ("info", f"📢 Notification for **{contact}**: {message}")

    Correct / expected behaviour (what fix must produce):
        - level == "error"  (not "info")
        - message body NOT present in the stored text
    """

    def test_bug_a_level_should_be_error_not_info(self):
        """
        EXPECTED TO FAIL on unfixed code.

        Counterexample on unfixed code:
            notify_msg == ("info", "📢 Notification for **+919876543210**: secret body text")
            → level is "info", not "error"
        """
        session_state: dict = {}
        _call_notify_user(
            "+919876543210",
            "secret body text",
            session_state,
            notifier_available=False,
        )

        stored = session_state.get("notify_msg")
        assert stored is not None, "notify_msg was not written to session_state"
        level, text = stored

        # On unfixed code this assertion FAILS: level is "info", not "error"
        assert level == "error", (
            f"Bug A counterexample: level is {level!r} but should be 'error'. "
            f"Stored banner: {stored!r}"
        )

    def test_bug_a_body_should_not_be_in_banner(self):
        """
        EXPECTED TO FAIL on unfixed code.

        Counterexample on unfixed code:
            banner text contains "secret body text" → leaks message body in UI
        """
        session_state: dict = {}
        secret_body = "secret body text"
        _call_notify_user(
            "+919876543210",
            secret_body,
            session_state,
            notifier_available=False,
        )

        stored = session_state.get("notify_msg")
        assert stored is not None, "notify_msg was not written to session_state"
        _, text = stored

        # On unfixed code this assertion FAILS: secret_body is present in text
        assert secret_body not in text, (
            f"Bug A counterexample: message body leaked into UI banner. "
            f"Stored banner text: {text!r}"
        )


# ---------------------------------------------------------------------------
# Bug B — Twilio exception stored as "warning" instead of "error"
# ---------------------------------------------------------------------------

class TestBugBExploration:
    """
    **Bug B — Validates: Requirements 1.2**

    Bug condition: _NOTIFIER_AVAILABLE == True AND _notify_real() raises an Exception.

    Unfixed code sets:
        st.session_state["notify_msg"] = ("warning", f"Could not send notification ({exc}). …")

    Correct / expected behaviour (what fix must produce):
        - level == "error"  (not "warning")
    """

    def test_bug_b_exception_level_should_be_error_not_warning(self):
        """
        EXPECTED TO FAIL on unfixed code.

        Counterexample on unfixed code:
            notify_msg == ("warning", "Could not send notification (Unverified number)…")
            → level is "warning", not "error"
        """
        session_state: dict = {}
        _call_notify_user(
            "+919876543210",
            "msg",
            session_state,
            notifier_available=True,
            notify_real_side_effect=Exception("Unverified number"),
        )

        stored = session_state.get("notify_msg")
        assert stored is not None, "notify_msg was not written to session_state"
        level, text = stored

        # On unfixed code this assertion FAILS: level is "warning", not "error"
        assert level == "error", (
            f"Bug B counterexample: level is {level!r} but should be 'error'. "
            f"Stored banner: {stored!r}"
        )


# ---------------------------------------------------------------------------
# Bug C — Placeholder TWILIO_FROM_NUMBER=+91 passes credentials check
# ---------------------------------------------------------------------------

class TestBugCExploration:
    """
    **Bug C — Validates: Requirements 1.3**

    Bug condition: TWILIO_FROM_NUMBER is non-empty but NOT a valid E.164 number
    (e.g. "+91" — just a country code, no subscriber digits).

    Unfixed code returns {"sms": True} for any non-empty TWILIO_FROM_NUMBER.

    Correct / expected behaviour (what fix must produce):
        credentials_configured()["sms"] == False  for placeholder numbers
    """

    def _credentials_configured_with_env(self, from_num: str) -> dict:
        """Call credentials_configured() with controlled env vars."""
        import importlib
        import notifier as notifier_mod

        env_patch = {
            "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "TWILIO_AUTH_TOKEN": "authtoken1234567890abcdef12345678",
            "TWILIO_FROM_NUMBER": from_num,
            "GMAIL_SENDER_EMAIL": "",
            "GMAIL_APP_PASSWORD": "",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            # Re-evaluate so env changes are picked up
            return notifier_mod.credentials_configured()

    def test_bug_c_placeholder_plus91_should_return_sms_false(self):
        """
        EXPECTED TO FAIL on unfixed code.

        Counterexample on unfixed code:
            credentials_configured() returns {"sms": True} for TWILIO_FROM_NUMBER="+91"
            → +91 is just a country code prefix, not a valid E.164 number
        """
        result = self._credentials_configured_with_env("+91")

        # On unfixed code this assertion FAILS: result["sms"] is True
        assert result["sms"] is False, (
            f"Bug C counterexample: credentials_configured() returned {result!r} "
            f"for TWILIO_FROM_NUMBER='+91' — placeholder accepted as valid."
        )

    def test_bug_c_placeholder_plus1_should_return_sms_false(self):
        """
        EXPECTED TO FAIL on unfixed code.

        Counterexample on unfixed code:
            credentials_configured() returns {"sms": True} for TWILIO_FROM_NUMBER="+1"
            → +1 is just the US country code prefix, not a valid E.164 number
        """
        result = self._credentials_configured_with_env("+1")

        # On unfixed code this assertion FAILS: result["sms"] is True
        assert result["sms"] is False, (
            f"Bug C counterexample: credentials_configured() returned {result!r} "
            f"for TWILIO_FROM_NUMBER='+1' — country-code-only prefix accepted as valid."
        )
