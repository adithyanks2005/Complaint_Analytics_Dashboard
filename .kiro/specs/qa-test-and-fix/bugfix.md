# Bugfix Requirements Document

## Introduction

The Complaint Analytics Dashboard has several bugs discovered through QA testing and direct test execution. The confirmed test failure is in `test_generate_next_id_supabase_reads_remote_ids`, which returns `CMP-101` instead of the expected `CMP-121`. Additional bugs include a `SettingWithCopyWarning` in `analytics.py` that silently discards data modifications for non-closed complaints' closure days, a `NameError` in `scripts/backfill_locations.py` where `ref_df` is used inside functions before it is defined, and missing area length validation in the admin panel update flow. Together these bugs cause one automated test failure, silent data corruption in the analytics layer, and a crash when `backfill_locations.py` functions are called programmatically.

---

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `test_generate_next_id_supabase_reads_remote_ids` runs after any prior test that set `_supabase_failed = True` THEN the system calls `generate_next_id()` against the local SQLite database instead of the mocked Supabase client, returning `CMP-101` instead of `CMP-121`

1.2 WHEN `generate_next_id_supabase()` is called with a mocked Supabase client that returns `[{"id": "CMP-002"}, {"id": "CMP-120"}, {"id": "legacy"}]` and `_supabase_failed` is `True` from a prior test THEN the system bypasses the mock entirely and reads the local database, producing an incorrect next ID

1.3 WHEN `load_complaints()` is called and there are non-closed complaints THEN the system attempts `closure_days[mask_not_closed] = None` on a derived Series, producing a `SettingWithCopyWarning` and silently discarding the `None` assignments so that non-closed complaints may retain incorrect closure-day values

1.4 WHEN `backfill_sqlite()` or `backfill_supabase()` is called as an imported function (not from the `__main__` block) THEN the system raises `NameError: name 'ref_df' is not defined` because `ref_df` is only assigned inside the `if __name__ == "__main__"` guard and is not in function scope

1.5 WHEN an admin updates a complaint record in the admin panel and sets the Area field to an empty string or fewer than 2 characters THEN the system accepts the update without validation and persists an empty or too-short area value to the database, violating the business rule that area must be at least 2 characters

### Expected Behavior (Correct)

2.1 WHEN `test_generate_next_id_supabase_reads_remote_ids` runs THEN the system SHALL reset `_supabase_failed` to `False` before the assertion so that `using_supabase()` returns `True` and the mocked Supabase client is used, returning `CMP-121`

2.2 WHEN `generate_next_id_supabase()` is called with valid `SUPABASE_URL`, `SUPABASE_KEY`, a working (or mocked) Supabase client, and `_supabase_failed` is `False` THEN the system SHALL compute the highest numeric suffix from the remote IDs and return `CMP-{highest + 1:03d}`

2.3 WHEN `load_complaints()` is called THEN the system SHALL use `.loc` indexing to assign `pd.NA` to closure days for non-closed complaints so that modifications are applied on the actual Series data without triggering a `SettingWithCopyWarning`

2.4 WHEN `backfill_sqlite()` or `backfill_supabase()` is called from any context THEN the system SHALL accept `ref_df` as an explicit function parameter so the reference DataFrame is always available without relying on a global variable defined only in the `__main__` block

2.5 WHEN an admin submits an update to a complaint record with the Area field containing fewer than 2 characters THEN the system SHALL display an error message "Area must be at least 2 characters" and SHALL NOT persist the invalid value to the database

### Unchanged Behavior (Regression Prevention)

3.1 WHEN all 11 currently passing tests run THEN the system SHALL CONTINUE TO pass all 11 tests without regression

3.2 WHEN `generate_next_id_supabase()` is called in an environment where `using_supabase()` returns `False` (no credentials) THEN the system SHALL CONTINUE TO fall back to `generate_next_id()` which reads the local SQLite database

3.3 WHEN `load_complaints()` is called and all complaints have `status == "Closed"` THEN the system SHALL CONTINUE TO return correct closure-day values for all records

3.4 WHEN `backfill_locations.py` is run as a script (`python scripts/backfill_locations.py`) THEN the system SHALL CONTINUE TO load `ref_df` from the CSV and pass it to the backfill functions correctly

3.5 WHEN a valid area value (2 or more characters) is submitted in the admin update form THEN the system SHALL CONTINUE TO persist the update successfully without any error

3.6 WHEN the `/options`, `/complaints`, `/health`, and root `/` API endpoints are called THEN the system SHALL CONTINUE TO return `200 OK` responses with the expected JSON structure

3.7 WHEN `analytics.summary_metrics()` is called on a DataFrame containing mixed open and closed complaints THEN the system SHALL CONTINUE TO calculate `average_closure_days` and `closure_rate_percent` correctly

---

## Bug Condition Pseudocode

### Bug 1 & 2 — Supabase ID Generation Test Failure

```pascal
FUNCTION isBugCondition_SupabaseId(test_run)
  INPUT: test_run context
  OUTPUT: boolean

  RETURN db._supabase_failed = True
         AND db.SUPABASE_URL is patched to a valid value
         AND db.get_supabase_client is patched to a mock
END FUNCTION

// Property: Fix Checking
FOR ALL test_run WHERE isBugCondition_SupabaseId(test_run) DO
  monkeypatch db._supabase_failed = False
  result ← generate_next_id_supabase'()
  ASSERT result = "CMP-121"
END FOR

// Property: Preservation Checking
FOR ALL test_run WHERE NOT isBugCondition_SupabaseId(test_run) DO
  ASSERT generate_next_id_supabase(test_run) = generate_next_id_supabase'(test_run)
END FOR
```

### Bug 3 — SettingWithCopyWarning / Silent Data Loss in analytics.py

```pascal
FUNCTION isBugCondition_ClosureDays(df)
  INPUT: df DataFrame
  OUTPUT: boolean

  RETURN EXISTS row IN df WHERE row["status"] != "Closed"
END FUNCTION

// Property: Fix Checking
FOR ALL df WHERE isBugCondition_ClosureDays(df) DO
  result ← load_complaints'(df)
  FOR ALL row IN result WHERE row["status"] != "Closed" DO
    ASSERT row["closure_days"] IS NULL OR row["closure_days"] IS pd.NA
  END FOR
  ASSERT no SettingWithCopyWarning raised
END FOR

// Property: Preservation Checking
FOR ALL df WHERE NOT isBugCondition_ClosureDays(df) DO
  ASSERT load_complaints(df)["closure_days"] = load_complaints'(df)["closure_days"]
END FOR
```

### Bug 4 — ref_df NameError in backfill_locations.py

```pascal
FUNCTION isBugCondition_RefDf(call_context)
  INPUT: call_context
  OUTPUT: boolean

  RETURN backfill_sqlite OR backfill_supabase called outside __main__ block
         AND ref_df not defined in module scope
END FUNCTION

// Property: Fix Checking
FOR ALL call_context WHERE isBugCondition_RefDf(call_context) DO
  result ← backfill_sqlite'(ref_df=any_dataframe)
  ASSERT no NameError raised
END FOR

// Property: Preservation Checking
FOR ALL call_context WHERE NOT isBugCondition_RefDf(call_context) DO
  ASSERT backfill_sqlite(ref_df) = backfill_sqlite'(ref_df)
END FOR
```

### Bug 5 — Missing Area Validation in Admin Update

```pascal
FUNCTION isBugCondition_AdminArea(upd_area)
  INPUT: upd_area string
  OUTPUT: boolean

  RETURN len(upd_area.strip()) < 2
END FUNCTION

// Property: Fix Checking
FOR ALL upd_area WHERE isBugCondition_AdminArea(upd_area) DO
  result ← admin_update_submit'(upd_area)
  ASSERT error_displayed = "Area must be at least 2 characters"
  ASSERT database NOT updated
END FOR

// Property: Preservation Checking
FOR ALL upd_area WHERE NOT isBugCondition_AdminArea(upd_area) DO
  ASSERT admin_update_submit(upd_area) = admin_update_submit'(upd_area)
END FOR
```
