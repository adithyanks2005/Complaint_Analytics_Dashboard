# QA Test and Fix — Bugfix Design

## Overview

This document formalizes the fix approach for five confirmed bugs in the Complaint Analytics
Dashboard. Each bug has a precisely scoped condition, a root cause hypothesis, a minimal
implementation change, and a two-phase testing strategy (exploratory on unfixed code, then
fix + preservation checking on fixed code).

The five bugs are:

| # | Bug | File | Symptom |
|---|-----|------|---------|
| 1 | `_supabase_failed` state leaks between tests | `backend/database.py` + `tests/test_database.py` | `generate_next_id_supabase` returns `CMP-101` instead of `CMP-121` |
| 2 | `SettingWithCopyWarning` / silent `None` discard | `backend/analytics.py` | Non-closed complaints retain incorrect `closure_days` values |
| 3 | `NameError: ref_df` in backfill functions | `scripts/backfill_locations.py` | Calling `backfill_sqlite()` or `backfill_supabase()` programmatically crashes |
| 4 | Missing area length validation in admin update | `frontend/streamlit_app.py` | Admin can persist an empty or single-character area value |

---

## Glossary

- **Bug_Condition (C)**: A predicate that returns `True` when a given input will trigger the
  defective code path.
- **Property (P)**: The desired observable behavior when the bug condition holds — i.e., what
  the fixed code must produce.
- **Preservation**: The guarantee that for all inputs where the bug condition does NOT hold,
  the fixed code produces exactly the same result as the original code.
- **`_supabase_failed`**: Module-level boolean in `backend/database.py`; set to `True` when
  any Supabase operation fails. Controls whether `using_supabase()` returns `True` or `False`.
- **`using_supabase()`**: Returns `True` only when both `SUPABASE_URL`/`SUPABASE_KEY` are set
  and `_supabase_failed` is `False`.
- **`generate_next_id_supabase()`**: ID generation function that delegates to
  `generate_next_id()` (SQLite) when `using_supabase()` is `False`.
- **`closure_days`**: Computed Series — `(closed_date - created_date).dt.days`. Only meaningful
  for complaints with `status == "Closed"`.
- **`SettingWithCopyWarning`**: Pandas warning raised when a write is attempted on a view
  rather than the underlying DataFrame; the write is silently discarded.
- **`ref_df`**: Reference DataFrame loaded from `data/sample_complaints.csv` in
  `backfill_locations.py`; needed by `backfill_sqlite()` and `backfill_supabase()` to look up
  location fields.
- **`upd_area`**: The area string entered in the admin update form
  (`frontend/streamlit_app.py`, key `"adm_area_text"`).

---

## Bug Details

### Bug 1 — `_supabase_failed` State Leaks Between Tests

The test `test_generate_next_id_supabase_reads_remote_ids` monkeypatches `SUPABASE_URL`,
`SUPABASE_KEY`, and `get_supabase_client` to simulate a working Supabase connection. However,
if a prior test in the session caused `_supabase_failed` to be set to `True` (e.g., a test
that attempted a real Supabase connection and encountered an import error or connection
failure), `using_supabase()` returns `False` despite the monkeypatches, and
`generate_next_id_supabase()` falls through to `generate_next_id()` which reads the local
SQLite database and returns `CMP-101`.

The `_use_temp_db` autouse fixture resets `DB_PATH` and `_db_initialised` but does **not**
reset `_supabase_failed`, so the leaked state persists across tests.

**Formal Specification:**

```
FUNCTION isBugCondition_SupabaseId(test_context)
  INPUT: test_context — the state of the test process at the point
         test_generate_next_id_supabase_reads_remote_ids executes
  OUTPUT: boolean

  RETURN db._supabase_failed = True
         AND db.SUPABASE_URL is monkeypatched to a non-empty string
         AND db.SUPABASE_KEY is monkeypatched to a non-empty string
         AND db.get_supabase_client is monkeypatched to a fake client
END FUNCTION
```

**Examples:**

- A previous test calls `init_db()` which calls `get_supabase_client()`, which fails because
  the `supabase` package is not installed → `_supabase_failed` becomes `True` →
  `test_generate_next_id_supabase_reads_remote_ids` runs → `using_supabase()` returns `False`
  → `generate_next_id_supabase()` reads SQLite → returns `CMP-101` ❌ (expected `CMP-121`)
- The same test runs in isolation (no prior contaminating test) → `_supabase_failed` is `False`
  → `using_supabase()` returns `True` → fake client is used → returns `CMP-121` ✅

---

### Bug 2 — `SettingWithCopyWarning` / Silent `None` Discard in `analytics.py`

In `load_complaints()`, `closure_days` is derived as:

```python
closure_days = (closed_date - created_date).dt.days
```

This produces a **new Series** that is not yet part of `df`. The subsequent line:

```python
closure_days[mask_not_closed] = None
```

attempts a chained assignment on a standalone Series object. Pandas treats this as a
potential view-of-copy write and emits `SettingWithCopyWarning`. More critically, the
assignment may be silently discarded, meaning non-closed complaints can retain a computed
numeric `closure_days` value that is arithmetically meaningless (days since creation, not
days to close).

**Formal Specification:**

```
FUNCTION isBugCondition_ClosureDays(df)
  INPUT: df — a DataFrame as returned by read_complaints_df()
  OUTPUT: boolean

  RETURN EXISTS row IN df WHERE row["status"] != "Closed"
END FUNCTION
```

**Examples:**

- `df` has 3 rows: `status = ["Closed", "Pending", "In Progress"]` →
  `isBugCondition_ClosureDays(df)` is `True` → `closure_days[mask_not_closed] = None` may be
  silently discarded → `closure_days` for `"Pending"` and `"In Progress"` rows may still hold
  numeric day values → downstream `summary_metrics()` and `area_summary()` may receive
  incorrect non-`NaN` values for open complaints ❌
- `df` has 2 rows: both `status = "Closed"` → `isBugCondition_ClosureDays(df)` is `False` →
  no `None` assignment attempted → behavior unchanged ✅

---

### Bug 3 — `NameError: ref_df` in `backfill_locations.py`

`backfill_sqlite()` and `backfill_supabase()` both reference `ref_df` as if it were a global
variable. `ref_df` is only assigned inside the `if __name__ == "__main__"` block:

```python
if __name__ == "__main__":
    ref_df = pd.read_csv(CSV_PATH) if CSV_PATH.exists() else pd.DataFrame()
    ...
    backfill_sqlite()
```

When either function is called programmatically (imported by another module, invoked in a
test, or called via `runpy`), `ref_df` is not in scope, causing:

```
NameError: name 'ref_df' is not defined
```

**Formal Specification:**

```
FUNCTION isBugCondition_RefDf(call_context)
  INPUT: call_context — describes how the function was invoked
  OUTPUT: boolean

  RETURN (backfill_sqlite() OR backfill_supabase() called)
         AND __name__ != "__main__"
         AND ref_df NOT defined at module scope
END FUNCTION
```

**Examples:**

- A test imports `backfill_locations` and calls `backfill_sqlite(ref_df=...)` — if the
  function signature does not accept `ref_df` as a parameter, it raises `NameError` ❌
- Running `python scripts/backfill_locations.py` from the command line → `__name__` is
  `"__main__"` → `ref_df` is assigned before the call → no error ✅

---

### Bug 4 — Missing Area Length Validation in Admin Update Form

The admin update form in `frontend/streamlit_app.py` reads:

```python
upd_area = loc5.text_input("Area", value=str(row.get("area") or ""), key="adm_area_text")
```

When "Save Changes" is pressed, the code validates the `closed_date` ordering but does **not**
validate `upd_area`. The update is dispatched with `"area": upd_area.strip() or None`, which
means an empty string becomes `None` — violating the `NOT NULL` constraint on the `area`
column — or a single-character value is persisted without complaint, violating the business
rule that area must be at least 2 characters.

(Compare the complaint **submission** form, which correctly validates:
`if len(final_area) < 2: st.error("Area must be at least 2 characters")`.)

**Formal Specification:**

```
FUNCTION isBugCondition_AdminArea(upd_area)
  INPUT: upd_area — the string value from the "Area" text_input in the admin update form
  OUTPUT: boolean

  RETURN len(upd_area.strip()) < 2
END FUNCTION
```

**Examples:**

- Admin clears the Area field and presses "Save Changes" → `upd_area = ""` →
  `isBugCondition_AdminArea("")` is `True` → update is dispatched with `area=None` →
  database rejects with `NOT NULL` constraint error or silently stores `None` ❌
- Admin enters `"X"` → `isBugCondition_AdminArea("X")` is `True` → single-character area
  persisted → violates minimum-length business rule ❌
- Admin enters `"MG Road"` → `isBugCondition_AdminArea("MG Road")` is `False` →
  update proceeds normally ✅

---

## Expected Behavior

### Preservation Requirements

The following behaviors must remain entirely unchanged by all four fixes:

**Bug 1 fix — must not affect:**
- All 11 currently passing tests (no regressions from the `_supabase_failed` reset)
- `generate_next_id_supabase()` falling back to `generate_next_id()` when credentials are
  absent and `using_supabase()` returns `False` in a real (non-test) context

**Bug 2 fix — must not affect:**
- `load_complaints()` output for DataFrames where every row has `status == "Closed"` —
  `closure_days` values must remain numerically identical
- `summary_metrics()`, `area_summary()`, and `records()` receiving a correctly computed
  `closure_days` column

**Bug 3 fix — must not affect:**
- Running `python scripts/backfill_locations.py` from the command line — the script must
  still load `ref_df` from the CSV and pass it correctly to the backfill functions
- The observable update behavior of `backfill_sqlite()` and `backfill_supabase()` (same rows
  updated, same values written)

**Bug 4 fix — must not affect:**
- Valid area values (≥ 2 characters) — the update must proceed without any error or
  additional friction
- The `closed_date` ordering validation already present in the admin form
- The complaint submission form validation (already correct, must remain untouched)

**Scope:** All inputs where the respective bug condition does NOT hold must be completely
unaffected. This includes normal CRUD operations, API endpoints (`/options`, `/complaints`,
`/health`, `/`), and all dashboard analytics computations.

---

## Hypothesized Root Cause

### Bug 1

**Missing monkeypatch of `_supabase_failed` in the test fixture.** The `_use_temp_db`
autouse fixture resets database path and init flag but leaves `_supabase_failed` at whatever
value it accumulated during the test session. Because `using_supabase()` checks
`_supabase_failed` first and short-circuits to `False`, the credential monkeypatches in the
specific test have no effect. The fix belongs in the test — not in `database.py` — because
the production code behavior is correct; it is the test isolation that is broken.

### Bug 2

**Chained assignment on a derived Series.** `closure_days` is created by
`(closed_date - created_date).dt.days`, producing a Series that is not a column of `df`.
Writing to a slice of this detached Series via `closure_days[mask_not_closed] = None` is the
classic pandas chained-indexing pattern that triggers `SettingWithCopyWarning` and may have
no effect. The correct fix is to use `.loc` on a column that is part of `df` — achieved by
assigning `closure_days` into `df` first and then masking with `.loc`, or by computing the
nulled series before calling `df.assign()`.

### Bug 3

**Global variable used inside functions defined before the global is assigned.** `ref_df` is
assigned in the `__main__` block, but `backfill_sqlite()` and `backfill_supabase()` are
defined before it at module scope and reference it as a free variable. In Python, free
variables in functions are resolved at call time from the enclosing or global scope; since
`ref_df` is not a module-level variable (it is only bound inside the `if __name__` block),
calling these functions from any other context raises `NameError`. The fix is to add `ref_df`
as an explicit parameter to both functions.

### Bug 4

**Validation gap between the submission form and the admin update form.** The submission form
(`handle_complaint_submission`) applies `len(final_area) < 2` validation before calling
`insert_complaint`. The admin update form was built separately and replicates most validation
logic (closed-date ordering, category lookup) but omits the area length guard. The fix is to
add the identical area validation check before dispatching `update_complaint_record`.

---

## Correctness Properties

Property 1: Bug Condition — Supabase ID Generation Ignores Leaked Failure State

_For any_ test execution context where `_supabase_failed` is `True` at the start of
`test_generate_next_id_supabase_reads_remote_ids`, yet `SUPABASE_URL`, `SUPABASE_KEY`, and
`get_supabase_client` are monkeypatched to valid values, the fixed test SHALL reset
`_supabase_failed` to `False` so that `using_supabase()` returns `True` and
`generate_next_id_supabase()` returns `"CMP-121"` (the highest remote ID suffix 120, plus 1).

**Validates: Requirements 2.1, 2.2**

---

Property 2: Preservation — Supabase Fallback Unaffected

_For any_ execution context where `using_supabase()` legitimately returns `False` (no
credentials or genuine failure), the fixed code SHALL produce the same result as the original
code — `generate_next_id_supabase()` delegating to `generate_next_id()` and reading from
SQLite.

**Validates: Requirements 3.1, 3.2**

---

Property 3: Bug Condition — Non-Closed `closure_days` Are Null After Fix

_For any_ DataFrame `df` returned by `read_complaints_df()` that contains at least one row
where `status != "Closed"`, the fixed `load_complaints()` function SHALL ensure that every
such row has `closure_days` equal to `pd.NA` (or `NaN`), and SHALL NOT raise or log a
`SettingWithCopyWarning`.

**Validates: Requirements 2.3**

---

Property 4: Preservation — Closed `closure_days` Unchanged

_For any_ DataFrame `df` where all rows have `status == "Closed"`, the fixed
`load_complaints()` function SHALL produce a `closure_days` column with values numerically
identical to those produced by the original function, preserving correct analytics for
fully-closed datasets.

**Validates: Requirements 3.3, 3.7**

---

Property 5: Bug Condition — `backfill_sqlite` / `backfill_supabase` Accept `ref_df` Parameter

_For any_ call to `backfill_sqlite(ref_df=any_dataframe)` or
`backfill_supabase(ref_df=any_dataframe)` made outside the `__main__` block (i.e., when
`ref_df` is not a global), the fixed functions SHALL execute without raising `NameError` and
SHALL use the supplied `ref_df` to look up location values.

**Validates: Requirements 2.4**

---

Property 6: Preservation — Script Execution Behavior Unchanged

_For any_ invocation of `python scripts/backfill_locations.py` from the command line, the
fixed script SHALL produce the same database updates as before — same rows identified as
missing, same values written — because the `__main__` block will pass `ref_df` as an
explicit argument to both functions.

**Validates: Requirements 3.4**

---

Property 7: Bug Condition — Admin Update Rejects Short Area Values

_For any_ admin update submission where `upd_area.strip()` has fewer than 2 characters, the
fixed admin panel SHALL display the error message `"Area must be at least 2 characters"` and
SHALL NOT call `update_complaint_record`, ensuring no invalid value is persisted.

**Validates: Requirements 2.5**

---

Property 8: Preservation — Admin Update Accepts Valid Area Values

_For any_ admin update submission where `upd_area.strip()` has 2 or more characters, the
fixed admin panel SHALL call `update_complaint_record` with the same arguments as the
original code and SHALL display the same success message, preserving all valid update
behavior.

**Validates: Requirements 3.5**

---

## Fix Implementation

### Bug 1 — Reset `_supabase_failed` in Test

**File:** `tests/test_database.py`

**Function:** `test_generate_next_id_supabase_reads_remote_ids`

**Specific Changes:**

1. Add `monkeypatch.setattr(db, "_supabase_failed", False)` alongside the existing
   `SUPABASE_URL` and `SUPABASE_KEY` patches so that `using_supabase()` returns `True`
   regardless of what prior tests set.

```python
# Before fix — _supabase_failed may be True from a prior test
monkeypatch.setattr(db, "SUPABASE_URL", "https://example.supabase.co")
monkeypatch.setattr(db, "SUPABASE_KEY", "test-key")
monkeypatch.setattr(db, "get_supabase_client", lambda: _FakeClient())

# After fix — explicitly reset failure flag
monkeypatch.setattr(db, "SUPABASE_URL", "https://example.supabase.co")
monkeypatch.setattr(db, "SUPABASE_KEY", "test-key")
monkeypatch.setattr(db, "_supabase_failed", False)          # <-- ADD THIS
monkeypatch.setattr(db, "get_supabase_client", lambda: _FakeClient())
```

No changes required to `backend/database.py` — the production logic is correct.

---

### Bug 2 — Use `.loc` for `closure_days` Assignment

**File:** `backend/analytics.py`

**Function:** `load_complaints`

**Specific Changes:**

Replace the detached-Series chained assignment with a `df.assign()` call that builds the
correct Series before assigning, using `numpy`/`pandas` masking without chained indexing:

```python
# Before fix
closure_days = (closed_date - created_date).dt.days
mask_not_closed = df["status"] != "Closed"
closure_days[mask_not_closed] = None          # SettingWithCopyWarning, may be discarded
return df.assign(
    created_date=created_date,
    closed_date=closed_date,
    closure_days=closure_days,
)

# After fix
closure_days = (closed_date - created_date).dt.days
mask_not_closed = df["status"] != "Closed"
closure_days = closure_days.where(~mask_not_closed, other=pd.NA)  # safe, no copy warning
return df.assign(
    created_date=created_date,
    closed_date=closed_date,
    closure_days=closure_days,
)
```

The `Series.where(cond, other)` method returns a new Series (no mutation of a view),
completely avoiding the `SettingWithCopyWarning`. `pd.NA` is used instead of `None` for
consistency with nullable integer dtype.

---

### Bug 3 — Add `ref_df` as an Explicit Parameter

**File:** `scripts/backfill_locations.py`

**Functions:** `backfill_sqlite`, `backfill_supabase`

**Specific Changes:**

1. Add `ref_df: pd.DataFrame` as a required parameter to both functions.
2. Update the `__main__` block to pass `ref_df` explicitly when calling the functions.

```python
# Before fix
def backfill_sqlite() -> None:
    ...
    csv_match = ref_df[ref_df["id"] == row_dict["id"]]   # NameError if not in __main__

def backfill_supabase() -> None:
    ...
    csv_match = ref_df[ref_df["id"] == row["id"]]        # NameError if not in __main__

if __name__ == "__main__":
    ref_df = pd.read_csv(CSV_PATH) if CSV_PATH.exists() else pd.DataFrame()
    backfill_sqlite()
    backfill_supabase()

# After fix
def backfill_sqlite(ref_df: pd.DataFrame) -> None:
    ...
    csv_match = ref_df[ref_df["id"] == row_dict["id"]]   # always defined

def backfill_supabase(ref_df: pd.DataFrame) -> None:
    ...
    csv_match = ref_df[ref_df["id"] == row["id"]]        # always defined

if __name__ == "__main__":
    ref_df = pd.read_csv(CSV_PATH) if CSV_PATH.exists() else pd.DataFrame()
    if using_supabase():
        backfill_supabase(ref_df)
    else:
        backfill_sqlite(ref_df)
```

---

### Bug 4 — Add Area Validation to Admin Update Form

**File:** `frontend/streamlit_app.py`

**Location:** Inside the `with tab_update:` block, under the `if st.button("Save Changes", ...)` handler

**Specific Changes:**

Add an area length guard before dispatching `update_complaint_record`, mirroring the
validation already present in `handle_complaint_submission`:

```python
# Before fix — no area validation
if st.button("Save Changes", use_container_width=True, key="adm_save"):
    closed_val = upd_closed.isoformat() if upd_closed else None
    created_for_check = row["created_date"].date() if pd.notna(row["created_date"]) else date.today()
    if upd_closed and upd_closed < created_for_check:
        st.error("Closed date cannot be before created date")
        st.stop()
    try:
        update_complaint_record(sel_id, { ... "area": upd_area.strip() or None, ... })

# After fix — area validated before dispatch
if st.button("Save Changes", use_container_width=True, key="adm_save"):
    closed_val = upd_closed.isoformat() if upd_closed else None
    created_for_check = row["created_date"].date() if pd.notna(row["created_date"]) else date.today()
    if len(upd_area.strip()) < 2:                                    # <-- ADD THIS BLOCK
        st.error("Area must be at least 2 characters")
        st.stop()
    if upd_closed and upd_closed < created_for_check:
        st.error("Closed date cannot be before created date")
        st.stop()
    try:
        update_complaint_record(sel_id, { ... "area": upd_area.strip(), ... })
        # Note: remove "or None" — validation above guarantees a non-empty value
```

---

## Testing Strategy

### Validation Approach

Testing follows a two-phase approach:

1. **Exploratory phase** — run tests against the unfixed code to observe the bug, confirm the
   root cause, and collect a concrete counterexample.
2. **Fix + Preservation phase** — apply the fix, re-run all tests to verify the bug is gone,
   and run property-based and integration tests to confirm no regressions.

---

### Exploratory Bug Condition Checking

**Goal:** Surface concrete counterexamples that demonstrate each bug on unfixed code.

#### Bug 1 — Supabase state leak

**Test Plan:** Introduce a "contaminating" test that sets `_supabase_failed = True` before
the Supabase ID test runs. Observe the assertion failure.

**Test Cases:**
1. **Contamination test** (runs first): patch `get_supabase_client` to raise an exception,
   call `using_supabase()` or `init_db()`, confirm `_supabase_failed` is now `True`.
2. **ID generation test** (runs second, unfixed): call `generate_next_id_supabase()` with
   URL/key patched — observe it returns `CMP-101` instead of `CMP-121`. (Will fail.)
3. **Isolation test**: run test 2 in isolation (fresh process) — observe it passes —
   confirming the bug is purely a cross-test state leak.

**Expected Counterexample:**
```
AssertionError: assert 'CMP-101' == 'CMP-121'
```

#### Bug 2 — `SettingWithCopyWarning`

**Test Plan:** Call the unfixed `load_complaints()` with a DataFrame containing a mix of
`"Closed"` and `"Pending"` rows. Capture warnings and inspect `closure_days`.

**Test Cases:**
1. **Warning check**: use `pytest.warns(pd.errors.SettingWithCopyWarning)` — confirm the
   warning fires (will pass on unfixed code, i.e., confirms the warning exists).
2. **Value check**: assert that `closure_days` for `"Pending"` rows is `NaN`/`pd.NA` on
   unfixed code — observe that it is NOT `NaN`, it is a numeric value. (Will fail.)

**Expected Counterexample:**
```
AssertionError: Expected NaN for non-closed row, got 5.0
```

#### Bug 3 — `NameError: ref_df`

**Test Plan:** Import `backfill_locations` and call `backfill_sqlite()` directly (no args).

**Test Cases:**
1. **Direct call test** (unfixed): `from scripts import backfill_locations;
   backfill_locations.backfill_sqlite()` — observe `NameError: name 'ref_df' is not defined`.

**Expected Counterexample:**
```
NameError: name 'ref_df' is not defined
```

#### Bug 4 — Missing area validation

**Test Plan:** Simulate the admin update form submission with an empty area string. This is a
UI test; exploratory checking is done via code review and manual testing in the Streamlit app.

**Test Cases:**
1. **Unit test** (unfixed): call the validation logic extracted from the button handler with
   `upd_area = ""` — assert that `update_complaint_record` is NOT called. On unfixed code,
   it IS called. (Will fail.)
2. **Manual test**: load the admin panel, select a complaint, clear the Area field, press
   "Save Changes" — observe no error is shown and the update proceeds.

**Expected Counterexample:**
```
update_complaint_record called with area=None (expected: not called, error shown instead)
```

---

### Fix Checking

**Goal:** Verify that for all inputs where each bug condition holds, the fixed code produces
the expected behavior (Properties 1, 3, 5, 7).

```
// Bug 1
FOR ALL test_context WHERE isBugCondition_SupabaseId(test_context) DO
  result := generate_next_id_supabase_fixed(test_context)
  ASSERT result = "CMP-121"
END FOR

// Bug 2
FOR ALL df WHERE isBugCondition_ClosureDays(df) DO
  result := load_complaints_fixed(df)
  FOR ALL row IN result WHERE row["status"] != "Closed" DO
    ASSERT row["closure_days"] IS pd.NA OR pd.isna(row["closure_days"])
  END FOR
  ASSERT no SettingWithCopyWarning emitted
END FOR

// Bug 3
FOR ALL call_context WHERE isBugCondition_RefDf(call_context) DO
  result := backfill_sqlite_fixed(ref_df=sample_dataframe)
  ASSERT no NameError raised
END FOR

// Bug 4
FOR ALL upd_area WHERE isBugCondition_AdminArea(upd_area) DO
  result := admin_update_handler_fixed(upd_area)
  ASSERT error_shown = "Area must be at least 2 characters"
  ASSERT update_complaint_record NOT called
END FOR
```

---

### Preservation Checking

**Goal:** Verify that for all inputs where the bug condition does NOT hold, the fixed code
produces the same result as the original code (Properties 2, 4, 6, 8).

```
// Bug 1 — Supabase fallback preserved
FOR ALL test_context WHERE NOT isBugCondition_SupabaseId(test_context) DO
  ASSERT generate_next_id_supabase(test_context) = generate_next_id_supabase_fixed(test_context)
END FOR

// Bug 2 — Closed complaint closure_days preserved
FOR ALL df WHERE NOT isBugCondition_ClosureDays(df) DO
  original := load_complaints(df)["closure_days"]
  fixed    := load_complaints_fixed(df)["closure_days"]
  ASSERT original.equals(fixed)
END FOR

// Bug 3 — Script execution behavior preserved
FOR ALL ref_df WHERE call_context = "__main__" DO
  ASSERT backfill_sqlite(ref_df) = backfill_sqlite_fixed(ref_df)
END FOR

// Bug 4 — Valid area updates preserved
FOR ALL upd_area WHERE NOT isBugCondition_AdminArea(upd_area) DO
  ASSERT admin_update_handler(upd_area) = admin_update_handler_fixed(upd_area)
END FOR
```

**Testing Approach for Preservation:** Property-based testing (Hypothesis) is recommended for
Bugs 2 and 4 because:
- It generates many diverse DataFrames / input strings automatically.
- It catches edge cases that hand-written examples miss (e.g., DataFrames with all-null dates,
  area strings at the boundary of 2 characters).
- It provides strong statistical guarantees that behavior is unchanged across the input domain.

---

### Unit Tests

**Bug 1:**
- Test that `_use_temp_db` fixture resets `_supabase_failed` (add explicit reset to fixture
  and verify the reset takes effect).
- Test `test_generate_next_id_supabase_reads_remote_ids` passes when run after a test that
  sets `_supabase_failed = True`.
- Test that `using_supabase()` returns `False` when `_supabase_failed = True` regardless of
  credential values.

**Bug 2:**
- Test `load_complaints()` with a mixed-status DataFrame: assert all non-Closed rows have
  `closure_days` as `NaN`/`pd.NA`.
- Test `load_complaints()` with an all-Closed DataFrame: assert `closure_days` values are
  numerically correct (spot-check known date pairs).
- Test that no `SettingWithCopyWarning` is raised by `load_complaints()`.

**Bug 3:**
- Test `backfill_sqlite(ref_df=pd.DataFrame(...))` does not raise `NameError`.
- Test `backfill_supabase(ref_df=pd.DataFrame(...))` does not raise `NameError`.
- Test that the `__main__` block correctly passes `ref_df` to both functions.
- Test that a DataFrame with no matching IDs results in zero updates (no crash).

**Bug 4:**
- Test that submitting an empty area string shows the error and does not call
  `update_complaint_record`.
- Test that submitting a 1-character area string shows the error.
- Test that submitting a 2-character area string proceeds without error.
- Test that submitting a valid area string calls `update_complaint_record` with the correct
  `area` value.

---

### Property-Based Tests

- **Bug 2 — Closure days nullity**: Generate random DataFrames with arbitrary `status` values
  and date pairs; assert that after `load_complaints()`, every row with `status != "Closed"`
  has `pd.isna(closure_days)`. Use `hypothesis` with `@given(st.dataframes(...))`.
- **Bug 2 — Closed days preservation**: Generate DataFrames where all rows have
  `status == "Closed"` and valid date pairs; assert `closure_days` equals
  `(closed_date - created_date).dt.days` exactly.
- **Bug 4 — Area boundary**: Generate random strings; assert that `len(s.strip()) < 2`
  triggers the error path and `len(s.strip()) >= 2` does not.
- **Bug 4 — Valid update passthrough**: Generate random area strings with length ≥ 2; assert
  that the validation gate passes and `update_complaint_record` receives the stripped value.

---

### Integration Tests

- Run the full pytest suite (`pytest tests/`) and confirm all 12 tests (11 original + 1
  regression test for Bug 1 cross-test contamination) pass.
- Run `python scripts/backfill_locations.py` against a local SQLite database and confirm it
  completes without errors and updates the expected rows.
- Start the Streamlit app locally, log in as admin, select a complaint with a valid area, and
  verify the update round-trips correctly.
- Start the Streamlit app locally, attempt to save an empty area via the admin form, and
  confirm the error banner appears with no database write.
- Call the `/complaints` and `/options` API endpoints and verify `200 OK` responses with
  correct JSON structure after all fixes are applied.
