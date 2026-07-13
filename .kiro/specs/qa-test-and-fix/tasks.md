# Implementation Plan

## Overview

This task list implements the exploratory bugfix workflow for four confirmed bugs in the Complaint Analytics Dashboard:

1. **Bug 1** — `_supabase_failed` state leaks between tests (`tests/test_database.py`)
2. **Bug 2** — `SettingWithCopyWarning` / silent `None` discard (`backend/analytics.py`)
3. **Bug 3** — `NameError: ref_df` when backfill functions called programmatically (`scripts/backfill_locations.py`)
4. **Bug 4** — Missing area length validation in the admin update form (`frontend/streamlit_app.py`)

Tasks follow the bug condition methodology: exploration tests (run BEFORE any fix, expected to FAIL) → preservation tests (run BEFORE any fix, expected to PASS) → fix implementations → checkpoint.

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": ["1", "2", "3", "4", "5", "6", "7", "8"],
      "description": "Write all exploration and preservation property tests BEFORE any fix"
    },
    {
      "wave": 2,
      "tasks": ["9.1", "10.1", "11.1", "12.1"],
      "description": "Implement all four fixes (can be done in parallel)"
    },
    {
      "wave": 3,
      "tasks": ["9.2", "9.3", "10.2", "10.3", "11.2", "11.3", "12.2", "12.3"],
      "description": "Verify all exploration tests now pass and preservation tests still pass"
    },
    {
      "wave": 4,
      "tasks": ["13"],
      "description": "Full test suite checkpoint"
    }
  ]
}
```

## Tasks

---

## Bug 1 — `_supabase_failed` state leaks between tests (`test_database.py`)

- [x] 1. Write bug condition exploration test — Supabase ID state leak
  - **Property 1: Bug Condition** - Supabase ID Returns Wrong Value When `_supabase_failed` Is Leaked
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface the counterexample `generate_next_id_supabase()` returning `CMP-101` instead of `CMP-121`
  - **Scoped PBT Approach**: This is a deterministic state-pollution bug; scope the property to the concrete failing case (a contaminating test sets `_supabase_failed = True` immediately before the target test)
  - Add a new test (or parametrize with `hypothesis`) in `tests/test_database.py` named `test_bug1_supabase_id_state_leak`
  - Step 1 — Contaminate state: `monkeypatch.setattr(db, "_supabase_failed", True)`
  - Step 2 — Apply the same patches as the original test: `SUPABASE_URL`, `SUPABASE_KEY`, `get_supabase_client → _FakeClient()`
  - Step 3 — Call `db.generate_next_id_supabase()` and assert the result equals `"CMP-121"`
  - Run this test on UNFIXED code (no `_supabase_failed = False` patch added yet)
  - **EXPECTED OUTCOME**: Test FAILS with `AssertionError: assert 'CMP-101' == 'CMP-121'` — this proves the bug exists
  - Document the counterexample: `_supabase_failed=True` → `using_supabase()` returns `False` → SQLite fallback → `CMP-101`
  - Mark task complete when test is written, run on unfixed code, and FAILURE is documented
  - _Requirements: 1.1, 1.2_

- [x] 2. Write preservation property test — Supabase fallback unaffected (BEFORE fix)
  - **Property 2: Preservation** - Supabase Fallback Still Reads SQLite When Credentials Are Absent
  - **IMPORTANT**: Follow observation-first methodology — run on UNFIXED code first
  - Use `hypothesis` `@given(st.booleans())` or a parameterised test to cover all states where `using_supabase()` legitimately returns `False`
  - Observe on UNFIXED code: when both `SUPABASE_URL` and `SUPABASE_KEY` are empty strings and `_supabase_failed` is `False`, `generate_next_id_supabase()` delegates to `generate_next_id()` and returns a `"CMP-NNN"` string from SQLite
  - Write property: for all contexts where `SUPABASE_URL=""` and `SUPABASE_KEY=""`, `generate_next_id_supabase()` returns a string matching `r"CMP-\d{3,}"` and does NOT call `get_supabase_client`
  - Verify this property test PASSES on UNFIXED code (confirms baseline)
  - **EXPECTED OUTCOME**: Test PASSES (confirms the fallback path is intact and unaffected)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2_

---

## Bug 2 — `SettingWithCopyWarning` / silent `None` discard (`analytics.py`)

- [x] 3. Write bug condition exploration test — non-closed `closure_days` not nulled
  - **Property 3: Bug Condition** - Non-Closed Rows Retain Numeric `closure_days` on Unfixed Code
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexample — `closure_days` for a `"Pending"` row is a numeric value, not `NaN`
  - **Scoped PBT Approach**: Scope to concrete failing case — a 2-row DataFrame: one `"Closed"` row, one `"Pending"` row with known dates
  - Create a new test file `tests/test_analytics_bug.py` (or add to an existing analytics test file)
  - Build a minimal DataFrame: `status=["Closed","Pending"]`, `created_date=["2024-01-01","2024-01-01"]`, `closed_date=["2024-01-06","2024-01-06"]`
  - Monkeypatch `backend.analytics.read_complaints_df` to return this DataFrame
  - Call `load_complaints()` on unfixed code
  - Assert that the `"Pending"` row's `closure_days` is `pd.isna()` — on unfixed code this will NOT be `NaN`
  - Also use `pytest.warns(pd.errors.SettingWithCopyWarning)` to confirm the warning fires
  - Run on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with `AssertionError: Expected NaN for non-closed row, got 5.0` — proves bug exists
  - Document counterexample: `Pending` row retains `closure_days=5` after the silent discard
  - Mark task complete when test written, run, and FAILURE documented
  - _Requirements: 1.3_

- [x] 4. Write preservation property test — closed `closure_days` values unchanged (BEFORE fix)
  - **Property 4: Preservation** - All-Closed DataFrames Produce Numerically Identical `closure_days`
  - **IMPORTANT**: Follow observation-first methodology — observe on UNFIXED code
  - Use `hypothesis` with `@given(...)` to generate DataFrames where every row has `status="Closed"` and valid `created_date` / `closed_date` pairs (closed_date ≥ created_date)
  - Use `hypothesis` strategies: `st.dates()` for date fields, constrain so `closed_date >= created_date`
  - Observe on UNFIXED code: `closure_days` for all-Closed DataFrames is `(closed_date - created_date).dt.days` — numerically correct, no nulling attempted
  - Write property: for all DataFrames where every row has `status="Closed"`, `load_complaints()["closure_days"]` equals `(pd.to_datetime(closed_date) - pd.to_datetime(created_date)).dt.days` element-wise
  - Verify this property test PASSES on UNFIXED code
  - **EXPECTED OUTCOME**: Test PASSES (confirms all-Closed path produces correct values)
  - Mark task complete when tests written, run, and passing on unfixed code
  - _Requirements: 3.3, 3.7_

---

## Bug 3 — `NameError: ref_df` in `backfill_locations.py`

- [x] 5. Write bug condition exploration test — `backfill_sqlite` raises `NameError` when called programmatically
  - **Property 5: Bug Condition** - `backfill_sqlite()` / `backfill_supabase()` Raise `NameError` Outside `__main__`
  - **CRITICAL**: This test MUST FAIL (raise `NameError`) on unfixed code — the exception confirms the bug
  - **DO NOT fix the code when the error appears**
  - **GOAL**: Surface `NameError: name 'ref_df' is not defined`
  - **Scoped PBT Approach**: Deterministic — call `backfill_sqlite()` (no args) from test context (outside `__main__`)
  - Add test in a new file `tests/test_backfill_bug.py` or alongside existing tests
  - Import `scripts.backfill_locations` (add `scripts/` to `sys.path` as needed)
  - Call `backfill_locations.backfill_sqlite()` with no arguments on unfixed code
  - Wrap in `pytest.raises(NameError)` to assert the error is raised — this assertion PASSES on unfixed code confirming the bug
  - Note: this is the only exploration test where `pytest.raises(NameError)` is the "expected failure" pattern — the bug IS the exception
  - Run on UNFIXED code
  - **EXPECTED OUTCOME**: `NameError: name 'ref_df' is not defined` is raised — confirms bug exists
  - Document counterexample: importing and calling `backfill_sqlite()` programmatically raises `NameError`
  - Mark task complete when test written and `NameError` confirmed on unfixed code
  - _Requirements: 1.4_

- [x] 6. Write preservation property test — script execution behavior unchanged (BEFORE fix)
  - **Property 6: Preservation** - `backfill_sqlite(ref_df=...)` Produces Same DB Updates as Script Execution
  - **IMPORTANT**: Observe on UNFIXED code — specifically the `__main__` path (run as script)
  - Use `hypothesis` `@given(st.data_frames(...))` or hand-written parametrised cases with `pytest.mark.parametrize`
  - Observe: when `ref_df` contains rows with matching IDs and non-null location columns, the function updates exactly those rows in SQLite
  - Observe: when `ref_df` contains no matching IDs, zero rows are updated (no crash, no error)
  - Write property: for all DataFrames `ref_df` (empty or non-empty), once the fix is applied, `backfill_sqlite(ref_df=ref_df)` raises no exception, updates exactly the rows with matching IDs that have missing location columns, and leaves all other rows unchanged
  - Verify this property test can be written and reasoned about on UNFIXED code (the `__main__` path still works) — test PASSES via `__main__` invocation
  - **EXPECTED OUTCOME**: Tests PASS (confirms that the observable update logic is identical between old and new calling conventions)
  - Mark task complete when tests written and passing
  - _Requirements: 3.4_

---

## Bug 4 — Missing area validation in admin update form (`streamlit_app.py`)

- [x] 7. Write bug condition exploration test — short area accepted without error
  - **Property 7: Bug Condition** - Admin Update Accepts Empty/Short Area Without Validation Error
  - **CRITICAL**: This test MUST confirm the absence of validation on unfixed code
  - **DO NOT fix the code when the assertion fails**
  - **GOAL**: Demonstrate that `update_complaint_record` IS called with `area=None` or a 1-char value on unfixed code
  - **Scoped PBT Approach**: Scope to concrete failing cases — `upd_area=""` and `upd_area="X"` (len < 2)
  - Extract the admin update save-button handler logic into a testable helper or test it by monkeypatching `update_complaint_record`
  - In `tests/test_admin_validation_bug.py`:
    - Monkeypatch `update_complaint_record` to record whether it was called
    - Simulate the save-button handler with `upd_area=""` on unfixed code
    - Assert that `update_complaint_record` was NOT called (on unfixed code it IS called — assertion fails, confirming bug)
  - Also test with `upd_area="X"` — same pattern
  - Run on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS because `update_complaint_record` IS called with `area=None` — proves bug exists
  - Document counterexample: empty area → `update_complaint_record(id, {"area": None, ...})` called without error
  - Mark task complete when test written, run, and FAILURE documented
  - _Requirements: 1.5_

- [x] 8. Write preservation property test — valid area updates proceed unchanged (BEFORE fix)
  - **Property 8: Preservation** - Area Values ≥ 2 Characters Pass Through to `update_complaint_record` Unmodified
  - **IMPORTANT**: Follow observation-first methodology — observe on UNFIXED code
  - Use `hypothesis` `@given(st.text(min_size=2))` filtered to `len(s.strip()) >= 2`
  - Observe on UNFIXED code: for `upd_area="MG Road"`, the handler calls `update_complaint_record` with `area="MG Road"` (stripped, not `None`)
  - Write property: for all strings `s` where `len(s.strip()) >= 2`, the admin update handler calls `update_complaint_record` with `area=s.strip()` and does NOT show the area error
  - Also write property: for any `s` where `len(s.strip()) < 2`, the fixed handler shows error `"Area must be at least 2 characters"` and does NOT call `update_complaint_record`
  - Verify both properties PASS on UNFIXED code for the `len >= 2` case (unfixed code always calls through, so the preservation property holds trivially on unfixed code)
  - **EXPECTED OUTCOME**: Preservation tests PASS on unfixed code (the valid-area path is unbroken)
  - Mark task complete when tests written and passing on unfixed code
  - _Requirements: 3.5_

---

## Fix Implementations

- [ ] 9. Fix Bug 1 — Reset `_supabase_failed` in test fixture

  - [x] 9.1 Add `_supabase_failed` monkeypatch to `test_generate_next_id_supabase_reads_remote_ids`
    - File: `tests/test_database.py`
    - Add `monkeypatch.setattr(db, "_supabase_failed", False)` immediately after the existing `SUPABASE_KEY` patch
    - No changes needed in `backend/database.py` — the production logic is correct
    - _Bug_Condition: `db._supabase_failed = True` AND `SUPABASE_URL`/`SUPABASE_KEY` are monkeypatched to valid values_
    - _Expected_Behavior: `generate_next_id_supabase()` returns `"CMP-121"` (highest suffix 120 + 1) when `using_supabase()` returns `True`_
    - _Preservation: All 11 currently passing tests must continue to pass; fallback to SQLite when credentials are absent is unchanged_
    - _Requirements: 2.1, 2.2, 3.1, 3.2_

  - [ ] 9.2 Verify bug condition exploration test (Property 1) now passes
    - **Property 1: Expected Behavior** - Supabase ID Is `CMP-121` After Resetting `_supabase_failed`
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 (`test_bug1_supabase_id_state_leak`) encodes the expected behavior
    - Run `pytest tests/test_database.py::test_bug1_supabase_id_state_leak`
    - **EXPECTED OUTCOME**: Test PASSES — confirms the `_supabase_failed` leak is resolved
    - _Requirements: 2.1, 2.2_

  - [ ] 9.3 Verify preservation test (Property 2) still passes
    - **Property 2: Preservation** - Supabase Fallback Unaffected
    - **IMPORTANT**: Re-run the SAME test from task 2 — do NOT write a new test
    - Run the preservation property test from task 2
    - **EXPECTED OUTCOME**: Test PASSES — confirms no regressions in the SQLite fallback path
    - _Requirements: 3.1, 3.2_

- [ ] 10. Fix Bug 2 — Use `.where()` for `closure_days` in `analytics.py`

  - [ ] 10.1 Replace chained assignment with `Series.where()` in `load_complaints`
    - File: `backend/analytics.py`
    - Replace the two lines:
      ```python
      mask_not_closed = df["status"] != "Closed"
      closure_days[mask_not_closed] = None
      ```
      with:
      ```python
      mask_not_closed = df["status"] != "Closed"
      closure_days = closure_days.where(~mask_not_closed, other=pd.NA)
      ```
    - The `Series.where(cond, other)` call returns a new Series — no mutation of a view, no `SettingWithCopyWarning`
    - `pd.NA` is used instead of `None` for consistent nullable-integer dtype
    - _Bug_Condition: `EXISTS row IN df WHERE row["status"] != "Closed"` — any DataFrame with at least one non-Closed row_
    - _Expected_Behavior: every row with `status != "Closed"` has `closure_days` equal to `pd.NA` / `NaN`; no `SettingWithCopyWarning` emitted_
    - _Preservation: all-Closed DataFrames produce numerically identical `closure_days` values; `summary_metrics()` and `area_summary()` receive correct data_
    - _Requirements: 2.3, 3.3, 3.7_

  - [ ] 10.2 Verify bug condition exploration test (Property 3) now passes
    - **Property 3: Expected Behavior** - Non-Closed `closure_days` Are `pd.NA` After Fix
    - **IMPORTANT**: Re-run the SAME test from task 3 — do NOT write a new test
    - Run `pytest tests/test_analytics_bug.py` (or equivalent)
    - **EXPECTED OUTCOME**: Test PASSES — non-Closed rows have `pd.NA`; no `SettingWithCopyWarning`
    - _Requirements: 2.3_

  - [ ] 10.3 Verify preservation test (Property 4) still passes
    - **Property 4: Preservation** - Closed `closure_days` Unchanged
    - **IMPORTANT**: Re-run the SAME test from task 4 — do NOT write a new test
    - Run property-based preservation test from task 4
    - **EXPECTED OUTCOME**: Test PASSES — all-Closed DataFrames produce identical `closure_days` values
    - _Requirements: 3.3, 3.7_

- [ ] 11. Fix Bug 3 — Add `ref_df` parameter to backfill functions

  - [ ] 11.1 Add `ref_df: pd.DataFrame` parameter to `backfill_sqlite` and `backfill_supabase`
    - File: `scripts/backfill_locations.py`
    - Change function signatures:
      - `def backfill_sqlite() -> None:` → `def backfill_sqlite(ref_df: pd.DataFrame) -> None:`
      - `def backfill_supabase() -> None:` → `def backfill_supabase(ref_df: pd.DataFrame) -> None:`
    - Remove any reliance on `ref_df` as a global/free variable inside both functions (no other change to function bodies — `ref_df` is already used by name, only the source of binding changes)
    - Update the `__main__` block to pass `ref_df` explicitly:
      ```python
      if using_supabase():
          backfill_supabase(ref_df)
      else:
          backfill_sqlite(ref_df)
      ```
    - _Bug_Condition: `backfill_sqlite()` or `backfill_supabase()` called outside `__main__` with `ref_df` not defined in module scope_
    - _Expected_Behavior: both functions accept `ref_df` as an explicit parameter and execute without `NameError` for any caller context_
    - _Preservation: `python scripts/backfill_locations.py` command-line execution unchanged; same rows updated, same values written_
    - _Requirements: 2.4, 3.4_

  - [ ] 11.2 Verify bug condition exploration test (Property 5) now passes
    - **Property 5: Expected Behavior** - `backfill_sqlite(ref_df=...)` No Longer Raises `NameError`
    - **IMPORTANT**: Re-run the SAME test from task 5 — do NOT write a new test
    - The test from task 5 now expects no `NameError` — update the assertion if it used `pytest.raises(NameError)` to instead assert no exception is raised and the function completes successfully with an empty DataFrame
    - Run `pytest tests/test_backfill_bug.py`
    - **EXPECTED OUTCOME**: Test PASSES — no `NameError`; function executes cleanly with `ref_df=pd.DataFrame()`
    - _Requirements: 2.4_

  - [ ] 11.3 Verify preservation test (Property 6) still passes
    - **Property 6: Preservation** - Script Execution Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 6 — do NOT write new tests
    - Run preservation property tests from task 6
    - **EXPECTED OUTCOME**: Tests PASS — same update logic, same affected rows, no regressions
    - _Requirements: 3.4_

- [ ] 12. Fix Bug 4 — Add area length validation to admin update form

  - [ ] 12.1 Add area validation guard before `update_complaint_record` dispatch in `streamlit_app.py`
    - File: `frontend/streamlit_app.py`
    - Inside the `with tab_update:` block, under `if st.button("Save Changes", ...)`:
    - Add the following block BEFORE the `closed_date` ordering check:
      ```python
      if len(upd_area.strip()) < 2:
          st.error("Area must be at least 2 characters")
          st.stop()
      ```
    - In the `update_complaint_record` call, change `"area": upd_area.strip() or None` to `"area": upd_area.strip()` — the guard above guarantees a non-empty value
    - This mirrors the identical check in `handle_complaint_submission` (`if len(final_area) < 2`)
    - _Bug_Condition: `len(upd_area.strip()) < 2` — empty string or single character in the Area field_
    - _Expected_Behavior: error message `"Area must be at least 2 characters"` displayed; `update_complaint_record` NOT called_
    - _Preservation: area values ≥ 2 characters proceed to `update_complaint_record` unmodified; closed-date ordering validation and all other form behavior unchanged_
    - _Requirements: 2.5, 3.5_

  - [ ] 12.2 Verify bug condition exploration test (Property 7) now passes
    - **Property 7: Expected Behavior** - Short Area Shows Error, Does Not Update
    - **IMPORTANT**: Re-run the SAME test from task 7 — do NOT write a new test
    - Run test from task 7 against fixed code
    - **EXPECTED OUTCOME**: Test PASSES — `update_complaint_record` is NOT called; error message is shown for `upd_area=""` and `upd_area="X"`
    - _Requirements: 2.5_

  - [ ] 12.3 Verify preservation test (Property 8) still passes
    - **Property 8: Preservation** - Valid Area Updates Pass Through Unmodified
    - **IMPORTANT**: Re-run the SAME tests from task 8 — do NOT write new tests
    - Run property-based preservation test from task 8 (`@given(st.text(min_size=2))`)
    - **EXPECTED OUTCOME**: Tests PASS — all valid-area updates reach `update_complaint_record` with `area=s.strip()`
    - _Requirements: 3.5_

---

## Checkpoint

- [ ] 13. Checkpoint — all tests pass, no regressions
  - Run the full test suite: `pytest tests/ -v`
  - Confirm all 12+ tests pass (11 original + regression tests added in this workflow)
  - Confirm no `SettingWithCopyWarning` appears in the output
  - Run `python scripts/backfill_locations.py` against a local SQLite DB and confirm it completes without errors
  - Verify API endpoints (`/health`, `/options`, `/complaints`, `/`) return `200 OK`
  - Ask the user if any questions arise before marking done
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

## Notes

- All property-based tests use the `hypothesis` library (`pip install hypothesis`). If `hypothesis` is not already in `requirements.txt`, add it before running the tests.
- Exploration tests (tasks 1, 3, 5, 7) are intentionally written to **FAIL** on unfixed code. Do not try to fix them when they fail — failure is the expected outcome and confirms the bug exists.
- Preservation tests (tasks 2, 4, 6, 8) must **PASS** on unfixed code before any fix is applied. This establishes the baseline behavior that must be preserved.
- The sub-tasks in tasks 9–12 (`.2` and `.3`) re-run the exact same tests written in tasks 1–8 — they do not create new tests.
- Bug 3 exploration test (task 5) uses `pytest.raises(NameError)` as its "failure" pattern — the `NameError` itself IS the bug confirmation. After the fix (task 11), this assertion must be inverted to confirm no exception is raised.
- `hypothesis` strategies for DataFrame generation: use `hypothesis.extra.pandas` (`st.data_frames`, `st.column`) for Bugs 2 and 4 where tabular data generation is required.
