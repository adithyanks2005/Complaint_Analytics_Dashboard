# Implementation Plan

## Overview

Fix three defects in the SMS notification pipeline:
- **Bug A**: Silent notifier fallback stores `"info"` banner with message body leaked — upgrade to `"error"`, strip body, log import failure (`streamlit_app.py`)
- **Bug B**: Twilio exception stored as `"warning"` and rendering blocks ignore `"error"` level — upgrade level and fix both rendering blocks (`streamlit_app.py`)
- **Bug C**: Placeholder `TWILIO_FROM_NUMBER=+91` passes credentials check — add E.164 regex validation in `credentials_configured()` (`notifier.py`)

Follows the exploratory bugfix workflow: write tests on unfixed code first, then implement fixes, then verify.

## Task Dependency Graph

```json
{
  "waves": [
    { "tasks": ["1", "2"] },
    { "tasks": ["3", "4", "5"] },
    { "tasks": ["6"] },
    { "tasks": ["7"] }
  ]
}
```

## Tasks

<!-- Three bugs are fixed in this plan:
     Bug A — silent notifier fallback stores info banner with message body leaked (streamlit_app.py)
     Bug B — Twilio exception stored as warning + broken rendering blocks (streamlit_app.py)
     Bug C — placeholder TWILIO_FROM_NUMBER=+91 passes credentials check (notifier.py)
-->

- [x] 1. Write bug condition exploration tests (all three bugs)
  - **Property 1: Bug Condition** - Silent Fallback Info Banner / Warning Level / Placeholder Credential
  - **CRITICAL**: Write these tests BEFORE implementing any fix
  - **DO NOT attempt to fix the test or the code when the tests fail**
  - **GOAL**: Surface counterexamples that demonstrate all three bugs exist
  - **Scoped PBT Approach**: Scope each property to the concrete failing case to ensure reproducibility
  - Create `tests/test_bugfix_sms_exploration.py` using `pytest` and `hypothesis`
  - **Bug A exploration** (isBugCondition: `_NOTIFIER_AVAILABLE == False` AND `contact != ""`):
    - Mock `_NOTIFIER_AVAILABLE = False` in `streamlit_app` module
    - Call `notify_user("+919876543210", "secret body text")` with a non-empty contact
    - Assert stored banner level is `"error"` (NOT `"info"`)
    - Assert `"secret body text"` is NOT present in the stored banner text
    - Run on UNFIXED code — **EXPECTED OUTCOME: FAILS** (level is `"info"`, body leaks)
    - Document counterexample: `notify_msg = ("info", "📢 Notification for **+919876543210**: secret body text")`
  - **Bug B exploration** (isBugCondition: `_NOTIFIER_AVAILABLE == True` AND `_notify_real` raises):
    - Mock `_NOTIFIER_AVAILABLE = True`, make `_notify_real` raise `Exception("Unverified number")`
    - Call `notify_user("+919876543210", "msg")`
    - Assert stored banner level is `"error"` (NOT `"warning"`)
    - Run on UNFIXED code — **EXPECTED OUTCOME: FAILS** (level is `"warning"`)
    - Document counterexample: `notify_msg = ("warning", "Could not send notification (Unverified number)…")`
  - **Bug C exploration** (isBugCondition: `TWILIO_FROM_NUMBER` non-empty but not valid E.164):
    - Set env `TWILIO_FROM_NUMBER=+91`, `TWILIO_ACCOUNT_SID=ACxxx`, `TWILIO_AUTH_TOKEN=token`
    - Call `credentials_configured()` from `notifier.py`
    - Assert `result["sms"] == False`
    - Run on UNFIXED code — **EXPECTED OUTCOME: FAILS** (`credentials_configured()` returns `{"sms": True}`)
    - Document counterexample: `credentials_configured()` returns `{"sms": True}` for `+91`
    - Also test `TWILIO_FROM_NUMBER=+1` → assert `result["sms"] == False`
  - Mark task complete when all three tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [-] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Successful SMS / Valid Credentials / Email Path / No-Contact Path
  - **IMPORTANT**: Follow observation-first methodology — observe UNFIXED code behaviour first
  - Create `tests/test_bugfix_sms_preservation.py` using `pytest` and `hypothesis`
  - **Observe on unfixed code** (non-bug-condition inputs where isBugCondition returns False):
    - Observe: `notify_user("+919876543210", "msg")` with `_NOTIFIER_AVAILABLE=True` and no exception → stores `("success", …)`
    - Observe: `notify_user("user@example.com", "msg")` → routes to email path, session state unchanged for SMS key
    - Observe: `notify_user("", "msg")` → returns immediately, no session state written
    - Observe: `credentials_configured()` with valid `TWILIO_FROM_NUMBER=+14155551234` → `{"sms": True}`
  - **Write property-based tests capturing observed behaviour**:
    - **Hypothesis — valid E.164 always accepted**: generate strings matching `^\+[1-9]\d{6,14}$`
      (e.g., `+14155551234`, `+447700900123`, `+919876543210`) with valid SID/token also set;
      assert `credentials_configured()["sms"] == True` for all generated values
    - **Hypothesis — successful SMS banner unchanged**: mock `_NOTIFIER_AVAILABLE=True` and `_notify_real` to succeed;
      for arbitrary non-empty phone contact strings, assert stored level is `"success"`
    - **Hypothesis — fallback preserves no-contact early return**: for empty contact strings (`contact=""`),
      assert `notify_user` returns without writing any key to `st.session_state`
    - **Unit — email path unaffected**: mock `_notify_real` and `send_email`; assert email contacts route to
      `send_email` and SMS session-state key is untouched
  - Verify all preservation tests **PASS on UNFIXED code** (confirms baseline to preserve)
  - **EXPECTED OUTCOME**: All tests PASS on unfixed code
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Fix Bug C — add E.164 validation to `credentials_configured()` in `notifier.py`

  - [x] 3.1 Add `_E164_RE` compiled regex at module level in `notifier.py`
    - Add `_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")` alongside the existing `_EMAIL_RE` and `_MOBILE_RE`
    - Place it in the `# ── Regex helpers ──` block (after `_MOBILE_RE`)
    - _Bug_Condition: `os.environ["TWILIO_FROM_NUMBER"]` matches `^\+\d{1,2}$` (non-empty but invalid E.164)_
    - _Expected_Behavior: `credentials_configured()` returns `{"sms": False}` for any non-E.164 value_
    - _Preservation: `credentials_configured()["sms"] == True` when all fields are valid_
    - _Requirements: 2.3, 3.6_

  - [x] 3.2 Replace presence-only `sms_ok` check with E.164-validated check
    - In `credentials_configured()`, change the `sms_ok` assignment from:
      ```python
      sms_ok = bool(
          os.environ.get("TWILIO_ACCOUNT_SID", "").strip() and
          os.environ.get("TWILIO_AUTH_TOKEN", "").strip() and
          os.environ.get("TWILIO_FROM_NUMBER", "").strip()
      )
      ```
      to:
      ```python
      from_num = os.environ.get("TWILIO_FROM_NUMBER", "").strip()
      sms_ok = bool(
          os.environ.get("TWILIO_ACCOUNT_SID", "").strip() and
          os.environ.get("TWILIO_AUTH_TOKEN", "").strip() and
          _E164_RE.match(from_num)
      )
      ```
    - _Bug_Condition: `TWILIO_FROM_NUMBER` is `+91` (or any string with no valid subscriber digits)_
    - _Expected_Behavior: `_E164_RE.match(from_num)` returns `None`, `sms_ok` evaluates to `False`_
    - _Preservation: valid numbers like `+14155551234` still match, `sms_ok` stays `True`_
    - _Requirements: 2.3, 3.6_

- [x] 4. Fix Bug A — upgrade silent fallback banner in `notify_user()` in `streamlit_app.py`

  - [x] 4.1 Replace info-level fallback with error-level generic message (strip message body)
    - In `notify_user()`, find the fallback assignment (executed when `_NOTIFIER_AVAILABLE` is `False`):
      ```python
      st.session_state[msg_key] = ("info", f"📢 Notification for **{contact}**: {message}")
      ```
      Replace with:
      ```python
      st.session_state[msg_key] = (
          "error",
          "SMS delivery is currently unavailable. No notification was sent to the user."
      )
      ```
    - This removes the `message` body from the UI and upgrades severity from `"info"` to `"error"`
    - _Bug_Condition: `_NOTIFIER_AVAILABLE == False` AND `contact` is non-empty_
    - _Expected_Behavior: stored tuple is `("error", <generic message>)` with no message body_
    - _Preservation: when `_NOTIFIER_AVAILABLE == True` and no exception, success path is unchanged_
    - _Requirements: 2.1, 2.4_

  - [x] 4.2 Log the import failure at module startup in `streamlit_app.py`
    - In the outer `except Exception as exc:` block (lines ~49–60) that sets `_NOTIFIER_AVAILABLE = False`,
      add a warning log immediately before or after the assignment:
      ```python
      import logging as _logging
      _logging.getLogger(__name__).warning(
          "notifier.py could not be loaded — SMS/email notifications disabled: %s", exc
      )
      ```
    - Ensure `logging` is imported at the top of `streamlit_app.py` if not already present
    - _Bug_Condition: import of `notifier.py` raises any `Exception` at startup_
    - _Expected_Behavior: operator sees a structured log line identifying the import failure_
    - _Preservation: normal startup (successful import) path is completely unaffected_
    - _Requirements: 2.1_

- [x] 5. Fix Bug B — upgrade Twilio exception level and fix rendering blocks in `streamlit_app.py`

  - [x] 5.1 Upgrade exception banner from `"warning"` to `"error"` in `notify_user()`
    - In the `except Exception as exc:` branch of `notify_user()`, change:
      ```python
      st.session_state[msg_key] = ("warning", f"Could not send notification ({exc}). …")
      ```
      to:
      ```python
      st.session_state[msg_key] = ("error", f"SMS/email notification could not be sent: {exc}")
      ```
    - _Bug_Condition: `_NOTIFIER_AVAILABLE == True` AND `_notify_real()` raises any `Exception`_
    - _Expected_Behavior: stored tuple level is `"error"`; rendering block calls `st.error()`_
    - _Preservation: success path (`_notify_real` does not raise) stores `("success", …)` unchanged_
    - _Requirements: 2.2_

  - [x] 5.2 Fix both notification rendering blocks to handle `"error"` level
    - Locate both rendering blocks in `streamlit_app.py`:
      - Public complaint form block (~lines 1757–1765)
      - Admin panel block (~lines 2091–2099)
    - In both blocks, replace the current binary `if/else`:
      ```python
      if level == "success":
          st.success(msg)
      else:
          st.info(msg)
      ```
      with a four-branch check:
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
    - This ensures `"error"` banners stored by bugs A and B are rendered with `st.error()`,
      not silently downgraded to `st.info()`
    - _Bug_Condition: rendering block receives `level == "error"` but falls through to `st.info()`_
    - _Expected_Behavior: `st.error(msg)` is called when level is `"error"`_
    - _Preservation: `"success"` level still calls `st.success()`; `"warning"` calls `st.warning()`_
    - _Requirements: 2.2_

  - [x] 5.3 Verify `st.rerun()` call order does not swallow the error banner
    - Locate the `st.rerun()` call at ~line 1746 immediately after `notify_user()` in the
      complaint submission path
    - Confirm the `"error"` banner stored in session state by task 5.1 persists through the rerun
      and is rendered visibly on the next page load (the session-state key is preserved across reruns)
    - If `st.rerun()` is called before the rendering block, the banner will appear on the re-rendered
      page — verify this is sufficient or add a direct `st.error()` call before `st.rerun()` if the
      UX requires it to be immediate
    - _Requirements: 2.2_

- [ ] 6. Verify bug condition exploration tests now pass (after all three fixes)

  - [-] 6.1 Re-run Bug A, B, C exploration tests from task 1
    - **Property 1: Expected Behavior** - Silent Fallback Error / Exception Error Level / E.164 Rejection
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - The tests from task 1 encode the expected (correct) behavior
    - Run `pytest tests/test_bugfix_sms_exploration.py -v`
    - **EXPECTED OUTCOME**: All three exploration tests PASS
    - Bug A test: level is `"error"`, `"secret body text"` not in banner text
    - Bug B test: level is `"error"`, not `"warning"`
    - Bug C test: `credentials_configured()["sms"] == False` for `+91` and `+1`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [~] 6.2 Re-run preservation tests from task 2
    - **Property 2: Preservation** - Successful SMS / Valid Credentials / Email Path / No-Contact
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run `pytest tests/test_bugfix_sms_preservation.py -v`
    - **EXPECTED OUTCOME**: All preservation tests still PASS (no regressions)
    - Valid E.164 numbers still accepted, success path unchanged, email path unaffected
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [~] 7. Checkpoint — ensure all tests pass
  - Run the full test suite: `pytest tests/ -v`
  - Confirm zero failures across both exploration and preservation test files
  - Confirm no existing tests regressed
  - Review the rendering fix in both UI blocks (public form + admin panel) manually if possible
  - Ensure all tests pass; ask the user if any questions arise

## Notes

- `hypothesis` must be installed: `pip install hypothesis` (already a dev-dependency via `requirements-dev.txt` if present, otherwise add it)
- All test files go in `tests/` at the project root
- The `notify_user()` function is in `frontend/streamlit_app.py`; mock via `unittest.mock.patch`
- The `credentials_configured()` function is in `frontend/notifier.py`
- Exploration tests (task 1) are expected to **fail** on unfixed code — this is correct and intentional
- Preservation tests (task 2) are expected to **pass** on unfixed code — this confirms the baseline
- Tasks 3, 4, and 5 are independent and can be implemented in any order

