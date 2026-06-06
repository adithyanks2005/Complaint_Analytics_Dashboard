# SMS Notification Not Sent — Bugfix Design

## Overview

Three distinct defects in the notification pipeline prevent users from receiving SMS confirmations
after submitting complaints, and prevent operators from detecting delivery failures early.

1. **Silent notifier fallback** (`Bug A`): when `notifier.py` fails to import at startup,
   `_NOTIFIER_AVAILABLE` is set to `False` and `notify_user()` stores an in-app `"info"` banner
   in `st.session_state` that leaks the full message body, while the user's phone receives nothing.

2. **Twilio exception swallowed as dismissible warning** (`Bug B`): when `_NOTIFIER_AVAILABLE` is
   `True` but the Twilio API call raises an exception, the failure is stored as a `"warning"` in
   `st.session_state` and `st.rerun()` is called immediately — causing the warning to render as a
   non-blocking, easily dismissed banner rather than a clearly visible error.

3. **Placeholder phone number accepted as valid** (`Bug C`): `credentials_configured()` in
   `notifier.py` returns `{"sms": True}` for `TWILIO_FROM_NUMBER=+91` (the `.env.example`
   default) because it only checks that the variable is non-empty, not that the value is a
   syntactically valid E.164 number.

The fix strategy is:
- **Bug A** — replace the silent in-app banner with a logged warning at startup and a clear
  `"error"`-level session-state message; strip the message body from the UI text.
- **Bug B** — upgrade the stored level from `"warning"` to `"error"` and stop calling
  `st.rerun()` immediately after `notify_user()` in the failure path (or render the error before
  the rerun).
- **Bug C** — add an E.164 format check (regex `^\+[1-9]\d{6,14}$`) inside
  `credentials_configured()` before setting `sms_ok = True`.

---

## Glossary

- **Bug_Condition (C)**: The set of runtime conditions that trigger one of the three defects.
- **Property (P)**: The desired, observable correct behaviour for each bug condition.
- **Preservation (¬C)**: All inputs / execution paths NOT in C — their behaviour must be
  unchanged after the fix is applied.
- **`notify_user()`**: The wrapper function in `frontend/streamlit_app.py` (line 1176) that
  calls `_notify_real()` when available and stores a session-state banner regardless.
- **`_NOTIFIER_AVAILABLE`**: Module-level boolean in `streamlit_app.py` set to `False` when
  both import attempts for `notifier.py` fail at startup.
- **`credentials_configured()`**: Function in `frontend/notifier.py` that returns a dict
  indicating which notification channels have credentials present in the environment.
- **E.164**: International phone number format — a `+` followed by 7–15 digits, no spaces or
  dashes (e.g. `+14155551234`).
- **`msg_key`**: Either `"notify_msg"` (public complaint form) or `"admin_notify_msg"` (admin
  panel) — the session-state key under which the notification banner tuple is stored.

---

## Bug Details

### Bug Condition

The bug manifests across three distinct code paths in the notification pipeline.

**Formal Specification:**

```
FUNCTION isBugCondition(scenario)
  INPUT: scenario — one of {IMPORT_FAIL, TWILIO_EXCEPTION, PLACEHOLDER_CRED}
  OUTPUT: boolean

  CASE IMPORT_FAIL:
    RETURN _NOTIFIER_AVAILABLE == False
           AND contact IS non-empty
           -- notify_user() stores info banner with full message body

  CASE TWILIO_EXCEPTION:
    RETURN _NOTIFIER_AVAILABLE == True
           AND _notify_real() raises any Exception
           AND stored level == "warning"           -- not "error"
           AND st.rerun() called immediately after
           -- user sees dismissible warning, not blocking error

  CASE PLACEHOLDER_CRED:
    RETURN os.environ["TWILIO_FROM_NUMBER"] matches regex "^\+\d{1,2}$"
           -- value is non-empty but not a valid E.164 number
           AND credentials_configured() returns {"sms": True}

  RETURN scenario IN {IMPORT_FAIL, TWILIO_EXCEPTION, PLACEHOLDER_CRED}
END FUNCTION
```

### Examples

**Bug A — Silent fallback:**
- Input: user submits complaint with `contact = "+919876543210"`, `twilio` package missing.
- Actual: `st.session_state["notify_msg"] = ("info", "📢 Notification for **+919876543210**: Your complaint CMP-042 has been registered…")` — no SMS sent, full body shown in UI.
- Expected: error-level banner "SMS delivery is currently unavailable. No notification was sent." — body not exposed.

**Bug B — Swallowed exception:**
- Input: `contact = "+919876543210"`, `TWILIO_ACCOUNT_SID` is valid but recipient is unverified on a trial account; `_NOTIFIER_AVAILABLE = True`.
- Actual: exception caught, `("warning", "Could not send notification (…)")` stored, `st.rerun()` fires — warning banner appears and user may dismiss it without noticing.
- Expected: `("error", "…")` stored and displayed prominently before any rerun, so the user is unambiguously aware delivery failed.

**Bug C — Placeholder credential:**
- Input: `.env` contains `TWILIO_FROM_NUMBER=+91`.
- Actual: `credentials_configured()` returns `{"sms": True}`.
- Expected: `credentials_configured()` returns `{"sms": False}` because `+91` is only 3 characters (country code with no subscriber number) and fails E.164 validation.

---

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviours:**
- When all Twilio credentials are correctly configured and the API call succeeds, the system must
  continue to send the SMS and store a `("success", …)` banner.
- Gmail SMTP notification flow must be completely unaffected by all three fixes.
- Complaint submission with no contact field must continue to silently skip notification.
- 10-digit bare Indian phone numbers (e.g. `9876543210`) must continue to be normalised to
  E.164 (`+919876543210`) before being passed to Twilio.
- Admin panel closure notifications must continue to follow the same `notify_user()` path.
- `credentials_configured()` must continue to return `{"sms": True}` when all three Twilio
  fields are set to syntactically valid values.

**Scope:**
All inputs that do NOT match any of the three bug conditions are unaffected. Specifically:
- Successful Twilio API calls (no exception raised).
- Email-address contacts routed through Gmail SMTP.
- Complaints submitted without any contact information.
- Operator environments where `notifier.py` imports correctly.

---

## Hypothesized Root Cause

**Bug A — Silent notifier fallback:**
1. **Missing failure surfacing at startup**: the outer `except Exception: _NOTIFIER_AVAILABLE = False` in `streamlit_app.py` (lines 49–60) silently discards the import error. No log message or visible warning is emitted to the operator.
2. **Fallback leaks message body**: the fallback line `("info", f"📢 Notification for **{contact}**: {message}")` (line 1196) embeds the full notification body — which may include complaint IDs and user details — into the in-app UI.

**Bug B — Twilio exception swallowed as dismissible warning:**
1. **Wrong severity level**: the `except Exception` branch in `notify_user()` stores level `"warning"` (line 1192) instead of `"error"`, so the rendering code at lines 1760–1765 falls through to `st.info()` rather than `st.error()`.
2. **Rerun before render**: `st.rerun()` is called at line 1746 immediately after `notify_user()` returns. The warning is stored in session state and rendered only after the rerun — as a dismissible, non-blocking banner at the top of the form. A blocking `st.error()` before the rerun would be more prominent.

**Bug C — Placeholder credential accepted:**
1. **Presence-only check**: `credentials_configured()` uses `bool(…strip())` to test each credential (line 63 of `notifier.py`). For `TWILIO_FROM_NUMBER`, this accepts any non-empty string — including the two-character placeholder `+91`.
2. **No format validation**: there is no regex or length check against the E.164 standard, so partial country codes pass silently.

---

## Correctness Properties

Property 1: Bug Condition A — Notifier Unavailable Surfaces Error, Not Info Banner

_For any_ call to `notify_user(contact, message)` where `_NOTIFIER_AVAILABLE` is `False` and
`contact` is non-empty, the fixed `notify_user()` SHALL store an `"error"`-level session-state
banner containing only a generic "SMS delivery unavailable" message and SHALL NOT include the raw
`message` body in the stored banner text.

**Validates: Requirements 2.1, 2.4**

Property 2: Bug Condition B — Twilio Exception Surfaces as Error

_For any_ call to `notify_user(contact, message)` where `_NOTIFIER_AVAILABLE` is `True` and
`_notify_real()` raises an exception, the fixed `notify_user()` SHALL store an `"error"`-level
(not `"warning"`-level) session-state banner, ensuring the notification rendering code calls
`st.error()` rather than `st.warning()` or `st.info()`.

**Validates: Requirements 2.2**

Property 3: Bug Condition C — Placeholder FROM Number Rejected

_For any_ value of `TWILIO_FROM_NUMBER` that is non-empty but does NOT match the regex
`^\+[1-9]\d{6,14}$` (i.e. is not a valid E.164 number), the fixed `credentials_configured()`
SHALL return `{"sms": False}`, preventing the application from attempting SMS dispatch with an
invalid sender number.

**Validates: Requirements 2.3**

Property 4: Preservation — Successful Notification Path Unchanged

_For any_ call to `notify_user(contact, message)` where `_NOTIFIER_AVAILABLE` is `True` and
`_notify_real()` completes without raising an exception, the fixed code SHALL produce exactly
the same result as the original code: storing `("success", …)` in session state and returning.

**Validates: Requirements 3.1, 3.2, 3.3**

Property 5: Preservation — Valid Credentials Still Accepted

_For any_ environment where `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`
are all set to syntactically valid values (non-empty, and `TWILIO_FROM_NUMBER` matches E.164),
the fixed `credentials_configured()` SHALL continue to return `{"sms": True}`.

**Validates: Requirements 3.6**

---

## Fix Implementation

### Changes Required

**File 1**: `frontend/notifier.py`

**Function**: `credentials_configured()`

**Specific Changes:**

1. **Add E.164 validation for `TWILIO_FROM_NUMBER`**: introduce a compiled regex
   `_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")` at module level (alongside the existing
   `_EMAIL_RE` and `_MOBILE_RE`).
2. **Replace presence-only check**: change the `sms_ok` assignment from
   `bool(…TWILIO_FROM_NUMBER…strip())` to additionally require that `_E164_RE.match(from_num)`
   is truthy:
   ```python
   from_num = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
   sms_ok = bool(
       os.environ.get("TWILIO_ACCOUNT_SID", "").strip() and
       os.environ.get("TWILIO_AUTH_TOKEN", "").strip() and
       _E164_RE.match(from_num)
   )
   ```

---

**File 2**: `frontend/streamlit_app.py`

**Function / Block 1**: module-level import block (lines 46–60)

**Specific Changes:**

3. **Log the import failure**: inside the final `except Exception as exc:` block that sets
   `_NOTIFIER_AVAILABLE = False`, add:
   ```python
   import logging as _logging
   _logging.getLogger(__name__).warning(
       "notifier.py could not be loaded — SMS/email notifications disabled: %s", exc
   )
   ```
   (The `logging` import can be done once at the top of the file if not already present.)

---

**Function / Block 2**: `notify_user()` (line 1176)

**Specific Changes:**

4. **Upgrade exception level from `"warning"` to `"error"`**: in the `except Exception as exc:`
   branch, change:
   ```python
   st.session_state[msg_key] = ("warning", f"Could not send notification ({exc}). …")
   ```
   to:
   ```python
   st.session_state[msg_key] = ("error", f"SMS/email notification could not be sent: {exc}")
   ```

5. **Fix fallback banner — remove message body and upgrade level**: replace:
   ```python
   st.session_state[msg_key] = ("info", f"📢 Notification for **{contact}**: {message}")
   ```
   with:
   ```python
   st.session_state[msg_key] = (
       "error",
       "SMS delivery is currently unavailable. No notification was sent to the user."
   )
   ```

---

**Function / Block 3**: notification rendering (lines 1757–1765 and 2091–2099)

**Specific Changes:**

6. **Handle `"error"` level in both rendering blocks**: the current rendering code has:
   ```python
   if level == "success":
       st.success(msg)
   else:
       st.info(msg)   # ← also covers "warning" and "error"
   ```
   Update both the public form block and the admin panel block to:
   ```python
   if level == "success":
       st.success(msg)
   elif level == "warning":
       st.warning(msg)
   elif level == "error":
       st.error(msg)
   else:
       st.info(msg)
   ```

---

## Testing Strategy

### Validation Approach

Testing follows a two-phase approach: first surface counterexamples on the **unfixed** code to
confirm the root cause analysis, then verify that the fix makes all properties hold and that no
preserved behaviour regresses.

---

### Exploratory Bug Condition Checking

**Goal**: run tests against the unfixed code to observe failures and confirm the three root causes.
If a test passes unexpectedly on unfixed code, the root cause hypothesis must be revised.

**Test Plan**: use `pytest` with `unittest.mock` to patch `_NOTIFIER_AVAILABLE`,
`_notify_real`, and environment variables; assert on the stored session-state tuple and on what
`credentials_configured()` returns.

**Test Cases:**

1. **Bug A — Info banner with body on fallback** *(will fail / show wrong value on unfixed code)*:
   Mock `_NOTIFIER_AVAILABLE = False`, call `notify_user("+919876543210", "secret body")`,
   assert the stored tuple level is NOT `"info"` and does NOT contain `"secret body"`.

2. **Bug B — Warning instead of error on Twilio exception** *(will fail on unfixed code)*:
   Mock `_NOTIFIER_AVAILABLE = True`, make `_notify_real` raise `Exception("Unverified number")`,
   call `notify_user("+919876543210", "msg")`, assert stored level is `"error"` not `"warning"`.

3. **Bug C — Placeholder `+91` accepted** *(will fail on unfixed code)*:
   Set `TWILIO_FROM_NUMBER=+91`, `TWILIO_ACCOUNT_SID=ACxxx`, `TWILIO_AUTH_TOKEN=token`,
   call `credentials_configured()`, assert `result["sms"] == False`.

4. **Bug C edge — `+1` also rejected** *(may fail on unfixed code)*:
   Set `TWILIO_FROM_NUMBER=+1`, assert `credentials_configured()["sms"] == False`.

**Expected Counterexamples:**

- On unfixed code, `st.session_state["notify_msg"]` level is `"info"` and value contains the
  raw message body (Bug A).
- On unfixed code, the stored level is `"warning"` when an exception fires (Bug B).
- On unfixed code, `credentials_configured()` returns `{"sms": True}` for `TWILIO_FROM_NUMBER=+91` (Bug C).

---

### Fix Checking

**Goal**: after applying the fix, verify that for all inputs where any bug condition holds, the
fixed functions produce the expected (correct) behaviour.

**Pseudocode:**

```
-- Bug A
FOR ALL contact WHERE contact != "" AND _NOTIFIER_AVAILABLE == False DO
  result := notify_user_fixed(contact, ANY_MESSAGE)
  stored := session_state[msg_key]
  ASSERT stored.level == "error"
  ASSERT ANY_MESSAGE NOT IN stored.text
END FOR

-- Bug B
FOR ALL contact WHERE _NOTIFIER_AVAILABLE == True AND _notify_real RAISES DO
  result := notify_user_fixed(contact, ANY_MESSAGE)
  stored := session_state[msg_key]
  ASSERT stored.level == "error"
END FOR

-- Bug C
FOR ALL from_num WHERE NOT matches(from_num, E164_REGEX) AND from_num != "" DO
  env["TWILIO_FROM_NUMBER"] = from_num
  result := credentials_configured_fixed()
  ASSERT result["sms"] == False
END FOR
```

---

### Preservation Checking

**Goal**: verify that for all inputs where NO bug condition holds, the fixed code produces
identical results to the original code.

**Pseudocode:**

```
-- Preservation: successful SMS
FOR ALL (contact, message) WHERE _NOTIFIER_AVAILABLE == True AND _notify_real SUCCEEDS DO
  ASSERT notify_user_fixed(contact, message).session_state == notify_user_original(contact, message).session_state
END FOR

-- Preservation: valid credentials still accepted
FOR ALL from_num WHERE matches(from_num, "^\+[1-9]\d{6,14}$") DO
  env["TWILIO_FROM_NUMBER"] = from_num
  ASSERT credentials_configured_fixed()["sms"] == credentials_configured_original()["sms"]
END FOR

-- Preservation: email path completely unchanged
FOR ALL email_contact DO
  ASSERT notify_user_fixed(email_contact, message) == notify_user_original(email_contact, message)
END FOR
```

**Testing Approach**: property-based testing (Hypothesis) is used for preservation checking
because:
- It generates many E.164 phone numbers and valid credential combinations automatically.
- It catches edge cases (numbers at the boundary of 7 and 15 digits) that manual tests miss.
- It provides strong guarantees across the full valid-input domain.

**Test Cases:**

1. **Successful SMS preservation**: mock `_NOTIFIER_AVAILABLE = True` and `_notify_real` to
   succeed; verify stored banner is `("success", …)` on both original and fixed code.
2. **Email path preservation**: patch `_is_email` to return `True`; verify `send_email` is
   called and session state matches before and after fix.
3. **No-contact preservation**: call `notify_user("", "msg")`; verify function returns
   immediately with no session-state change.
4. **Valid E.164 credentials still accepted** (PBT): Hypothesis generates valid E.164 numbers
   (`+` + 7–15 digits, first digit 1–9); `credentials_configured()` must return `{"sms": True}`.

---

### Unit Tests

- Test `credentials_configured()` with exactly `TWILIO_FROM_NUMBER=+91` → `{"sms": False}`.
- Test `credentials_configured()` with `TWILIO_FROM_NUMBER=+14155551234` → `{"sms": True}`.
- Test `credentials_configured()` with `TWILIO_FROM_NUMBER=` (empty) → `{"sms": False}`.
- Test `credentials_configured()` with `TWILIO_FROM_NUMBER=+1` (too short) → `{"sms": False}`.
- Test `notify_user()` with `_NOTIFIER_AVAILABLE=False`: stored level is `"error"`, body not in text.
- Test `notify_user()` with exception: stored level is `"error"`, not `"warning"` or `"info"`.
- Test rendering block: `("error", msg)` routes to `st.error()`, not `st.info()`.

### Property-Based Tests

- **Hypothesis — valid E.164 always accepted**: generate strings matching `^\+[1-9]\d{6,14}$`;
  assert `credentials_configured()["sms"] == True` for all (with valid SID/token also set).
- **Hypothesis — invalid FROM numbers always rejected**: generate strings that are non-empty but
  do NOT match E.164 (e.g., country-code-only, plain digits, letters included); assert
  `credentials_configured()["sms"] == False`.
- **Hypothesis — fallback banner never contains message body**: generate arbitrary `message`
  strings; when `_NOTIFIER_AVAILABLE=False`, assert `message not in stored_banner_text`.
- **Hypothesis — exception path always stores error level**: generate arbitrary exception
  messages; assert stored level is always `"error"` when `_notify_real` raises.

### Integration Tests

- Submit a complaint end-to-end with a mocked `notify` that raises; verify `st.error()` is
  ultimately rendered on the dashboard, not `st.warning()` or `st.info()`.
- Start the app with `TWILIO_FROM_NUMBER=+91` and verify the credentials check shows SMS as
  unavailable in any credential-status UI element.
- Submit a complaint with a valid phone number and a fully configured mock Twilio client; verify
  the success banner is shown and the SMS body is not leaked into the UI.
