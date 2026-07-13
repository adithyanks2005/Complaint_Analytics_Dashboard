# Bugfix Requirements Document

## Introduction

After a user submits a complaint on the Complaint Analytics Dashboard and provides their phone number
in the contact field, no SMS confirmation is sent to their number. The complaint is saved to the
database successfully, but the user receives no real-world notification. This affects user trust and
prevents timely confirmation that a complaint was registered.

Investigation revealed three contributing defects:

1. **Silent notifier fallback** — if `notifier.py` fails to import (e.g., due to a missing
   dependency), `_NOTIFIER_AVAILABLE` is set to `False` and `notify_user()` silently stores an
   in-app banner (`"info"` level) instead of dispatching a real SMS. The user never receives an
   actual message and is not clearly informed that delivery failed.

2. **Exception swallowed without surfacing to the user** — when `_NOTIFIER_AVAILABLE` is `True`
   but the Twilio API call raises an exception (e.g., unverified recipient on a trial account,
   invalid credentials, network error), the exception is caught and stored as a `"warning"` in
   `st.session_state`. However, `st.rerun()` is called immediately after `notify_user()` returns,
   so by the time the page re-renders the warning is displayed only as a dismissible Streamlit
   `st.warning()` box — not as a blocking error — and users may miss it entirely.

3. **`TWILIO_FROM_NUMBER` placeholder in `.env.example`** — the example configuration ships with
   `TWILIO_FROM_NUMBER=+91` (an incomplete number), making it easy for operators to start the
   service with a non-functional sender number while `credentials_configured()` returns `True`
   because the field is non-empty.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user submits a complaint with a valid phone number AND the `notifier` module cannot be
imported at startup THEN the system stores an in-app info banner in `st.session_state["notify_msg"]`
and sets `_NOTIFIER_AVAILABLE = False`, dispatching no real SMS to the user's phone.

1.2 WHEN a user submits a complaint with a valid phone number AND `_NOTIFIER_AVAILABLE` is `True`
AND the Twilio API call fails (e.g., unverified recipient, bad credentials, network error) THEN the
system catches the exception silently, stores a `"warning"` message in `st.session_state`, and
immediately calls `st.rerun()`, causing the warning to render as a non-blocking dismissible banner
that the user may not notice.

1.3 WHEN an operator configures `TWILIO_FROM_NUMBER=+91` (the placeholder from `.env.example`) AND
`credentials_configured()` is called THEN the system returns `{"sms": True}` even though `+91` is
not a valid Twilio sender number, allowing the application to attempt SMS dispatch with a broken
sender address.

1.4 WHEN the `notify_user()` fallback path executes (`_NOTIFIER_AVAILABLE = False`) THEN the system
displays the full notification message body inline in the in-app banner (e.g., `"📢 Notification for
+91XXXXXXXXXX: Your complaint CMP-001 has been registered…"`), leaking internal message content in
the UI while still delivering nothing to the user's phone.

### Expected Behavior (Correct)

2.1 WHEN a user submits a complaint with a valid phone number AND the `notifier` module cannot be
imported at startup THEN the system SHALL surface a clear error to the operator at startup (log
message + visible warning) and SHALL inform the user on the dashboard that SMS delivery is
unavailable, rather than silently falling back to an in-app info banner.

2.2 WHEN a user submits a complaint with a valid phone number AND the Twilio API call raises an
exception THEN the system SHALL display a clearly visible, prominent error message (not a dismissible
info banner) that explains the SMS could not be sent, so the user is unambiguously aware the
notification was not delivered.

2.3 WHEN `credentials_configured()` evaluates the `TWILIO_FROM_NUMBER` value THEN the system SHALL
validate that the value is a syntactically valid E.164 phone number (starts with `+` followed by
7–15 digits) before returning `{"sms": True}`, returning `{"sms": False}` for placeholder or
malformed values.

2.4 WHEN the `notify_user()` fallback path executes THEN the system SHALL NOT display the raw
notification message body in the UI banner; it SHALL display only a brief status message indicating
the delivery channel is unavailable.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user submits a complaint with a valid phone number AND all Twilio credentials are
correctly configured AND the API call succeeds THEN the system SHALL CONTINUE TO send an SMS to the
user's normalised phone number and display a success confirmation on the dashboard.

3.2 WHEN a user submits a complaint with a valid email address THEN the system SHALL CONTINUE TO
send a confirmation email via Gmail SMTP and display a success confirmation on the dashboard,
unaffected by any SMS-related changes.

3.3 WHEN a user submits a complaint without providing any contact information THEN the system SHALL
CONTINUE TO save the complaint successfully without attempting to send any notification.

3.4 WHEN a user provides a 10-digit bare Indian phone number (e.g., `9876543210`) THEN the system
SHALL CONTINUE TO normalise it to E.164 format (`+919876543210`) before passing it to the Twilio
API.

3.5 WHEN the admin panel updates a complaint status to "Closed" and the complainant has a contact on
file THEN the system SHALL CONTINUE TO attempt to send a closure notification to that contact via
the same `notify_user()` path.

3.6 WHEN `credentials_configured()` is called with all three Twilio fields correctly set to valid
values THEN the system SHALL CONTINUE TO return `{"sms": True}`.
