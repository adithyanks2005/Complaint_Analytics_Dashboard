# Test Report: Complaint Analytics Dashboard

## Test Run Summary

| Item | Result |
| --- | --- |
| Test date | 2026-05-25 |
| Test suite | `tests/test_api.py` |
| Test runner | `pytest 9.0.3` on Python 3.14.3 |
| Total tests | 7 |
| Passed | 7 |
| Failed | 0 |
| Warnings | 8 |
| Overall status | PASS |

## Execution Command

The API tests were run against the local SQLite fallback rather than any
configured shared Supabase project:

```bash
VERCEL=1 SUPABASE_URL= SUPABASE_KEY= SUPABASE_ANON_KEY= SUPABASE_SERVICE_ROLE_KEY= .venv/bin/python -m pytest tests -v
```

Setting `VERCEL=1` sends the SQLite database used during testing to `/tmp`,
and clearing the Supabase variables prevents test CRUD actions from updating
shared data.

## Test Results

| Test Case | Status |
| --- | --- |
| Health endpoint returns an OK response | Passed |
| Analytics summary includes required KPI fields | Passed |
| Area filter returns only matching complaint records | Passed |
| Date-range filter returns matching complaint records | Passed |
| Complaint create, update, read, and delete flow succeeds | Passed |
| Invalid closed status without closure date is rejected | Passed |
| Administrator can close a resolved complaint | Passed |

## Test Information

| Test Function | API Route(s) | Scenario and Validation |
| --- | --- | --- |
| `test_health_endpoint` | `GET /health` | Verifies service availability by checking for HTTP `200` and the response `{"status": "ok"}`. |
| `test_summary_has_required_kpis` | `GET /analytics/summary` | Checks that seeded analytics data contains at least 30 complaints and exposes `average_closure_days` and `closure_rate_percent`. |
| `test_area_filter_limits_records` | `GET /complaints?area=North Zone` | Confirms the area filter produces records and that every returned complaint belongs to `North Zone`. |
| `test_date_range_filter_returns_matching_records` | `GET /complaints?start_date=2026-04-01&end_date=2026-04-30` | Confirms the date filter produces records and restricts every complaint creation date to April 2026. |
| `test_crud_flow_inserts_updates_reads_and_deletes_sample_record` | `POST /complaints`, `PUT /complaints/CMP-TEST-901`, `GET /complaints/CMP-TEST-901`, `DELETE /complaints/CMP-TEST-901` | Tests a complete record lifecycle. New records default to `Pending` with no priority or closure date, can be closed with high priority, can be read by ID, and can be deleted. |
| `test_admin_validation_rejects_closed_status_without_closure_date` | `POST /complaints`, `PUT /complaints/CMP-BAD-901`, `DELETE /complaints/CMP-BAD-901` | Attempts to close a complaint without a closure date and verifies that validation rejects it with HTTP `422`; the inserted test record is then cleaned up. |
| `test_admin_can_close_resolved_complaint` | `POST /complaints`, `PUT /complaints/CMP-ADMIN-901`, `DELETE /complaints/CMP-ADMIN-901` | Creates a complaint, submits a closure date and `Closed` status, verifies HTTP `200` and the stored closed state, then removes the test record. |

## Coverage Scope

The current automated suite covers API health, summary analytics fields,
complaint filtering, complaint CRUD operations, and administrator closure
validation. It does not currently cover the frontend dashboard, CSV export,
Supabase-backed persistence, authorization behavior, or error cases such as
missing complaint IDs.

## Observations

1. `pytest` is not declared in `requirements.txt` and was not installed in
   the existing virtual environment before this run. It was installed locally
   in `.venv` to execute the suite.
2. The passing run reports 8 `FutureWarning` messages from
   `backend/analytics.py` lines 118-119. Pandas warns that the current
   assignment pattern will change behavior when Copy-on-Write becomes the
   default in pandas 3.0.

## Conclusion

The existing API test suite passes in an isolated local test run. The test
setup should declare its runner dependency, and the pandas warnings should be
addressed before upgrading to pandas 3.0.
