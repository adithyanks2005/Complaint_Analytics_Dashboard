"""
Bug condition exploration test for Bug 2 — SettingWithCopyWarning / silent None discard.

Task 3: Write bug condition exploration test — non-closed closure_days not nulled.

Property 3: Bug Condition — Non-Closed Rows Retain Numeric closure_days on Unfixed Code.

CRITICAL: This test is EXPECTED TO FAIL on unfixed code — failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

Validates: Requirements 1.3
"""
from __future__ import annotations

import pandas as pd
import pytest
import warnings

import sys
import os

# Ensure repo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import backend.analytics as analytics


def _make_minimal_df() -> pd.DataFrame:
    """
    Build a minimal 2-row DataFrame:
      - Row 0: status="Closed",  created_date="2024-01-01", closed_date="2024-01-06"
      - Row 1: status="Pending", created_date="2024-01-01", closed_date="2024-01-06"
    """
    return pd.DataFrame(
        {
            "id":           ["CMP-001", "CMP-002"],
            "status":       ["Closed",  "Pending"],
            "created_date": ["2024-01-01", "2024-01-01"],
            "closed_date":  ["2024-01-06", "2024-01-06"],
            # Minimal extra columns load_complaints() may reference
            "area":         ["Area A",  "Area B"],
            "category":     ["Water",   "Water"],
            "description":  ["desc1",   "desc2"],
            "state":        ["State1",  "State1"],
            "district":     ["Dist1",   "Dist1"],
            "pincode":      ["123456",  "123456"],
        }
    )


class TestBug2ClosureDaysNotNulled:
    """
    **Property 3: Bug Condition**

    Validates: Requirements 1.3

    Goal: Surface the counterexample where the "Pending" row retains a
    numeric closure_days value (5.0) instead of NaN/pd.NA after
    load_complaints() processes the DataFrame.

    EXPECTED TO FAIL on unfixed code with:
        AssertionError: Expected NaN for non-closed row, got 5.0

    Counterexample:
        Pending row retains closure_days=5 after the silent discard caused by
        chained assignment: closure_days[mask_not_closed] = None on a derived
        Series does NOT modify the underlying data (SettingWithCopyWarning).
    """

    def test_bug2_non_closed_closure_days_is_nan(self, monkeypatch):
        """
        Bug condition exploration test — non-closed closure_days not nulled.

        EXPECTED TO FAIL on unfixed code:
            The "Pending" row's closure_days retains value 5.0 instead of NaN.

        Counterexample documented:
            Pending row: closure_days=5.0  (should be NaN/pd.NA)
        """
        minimal_df = _make_minimal_df()

        # Monkeypatch backend.analytics.read_complaints_df to return our minimal DataFrame
        monkeypatch.setattr(analytics, "read_complaints_df", lambda: minimal_df)

        result = analytics.load_complaints()

        pending_rows = result[result["status"] == "Pending"]
        assert len(pending_rows) == 1, "Expected exactly one Pending row"

        pending_closure_days = pending_rows["closure_days"].iloc[0]

        # On unfixed code this assertion FAILS:
        #   pending_closure_days == 5.0 (numeric), NOT NaN
        assert pd.isna(pending_closure_days), (
            f"Expected NaN for non-closed row, got {pending_closure_days!r}. "
            f"Bug 2 counterexample: Pending row retains closure_days={pending_closure_days} "
            f"after the silent discard from chained assignment."
        )

    def test_bug2_setting_with_copy_warning_is_not_raised(self, monkeypatch):
        """
        Verify that the unfixed code emits a SettingWithCopyWarning.

        EXPECTED TO PASS on unfixed code (confirms the warning IS raised).
        On fixed code, this test should be updated to assert no warning is raised.

        Note: pytest.warns checks that the warning is raised during load_complaints().
        """
        minimal_df = _make_minimal_df()
        monkeypatch.setattr(analytics, "read_complaints_df", lambda: minimal_df)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            analytics.load_complaints()
        assert not [
            warning
            for warning in caught
            if issubclass(warning.category, pd.errors.SettingWithCopyWarning)
        ]


# ---------------------------------------------------------------------------
# Task 4 — Preservation property test: closed closure_days unchanged (BEFORE fix)
# ---------------------------------------------------------------------------
"""
Preservation property test for Bug 2 — All-Closed DataFrames Produce Correct closure_days.

Task 4: Write preservation property test — closed closure_days values unchanged (BEFORE fix)

Property 4: Preservation — All-Closed DataFrames Produce Numerically Identical closure_days

IMPORTANT: This test is EXPECTED TO PASS on unfixed code. It establishes the baseline
that must be preserved after the fix is applied.

Rationale: The bug (chained assignment on a derived Series) only fires when there are
rows where status != "Closed". For all-Closed DataFrames, no None assignment is
attempted, so the unfixed code produces correct values — this preservation test
verifies that the all-Closed path is not broken by any fix.

Validates: Requirements 3.3, 3.7
"""
from hypothesis import given, settings, assume
from hypothesis import strategies as st
import datetime


def _make_all_closed_df(
    created_dates: list[datetime.date],
    closed_dates: list[datetime.date],
) -> pd.DataFrame:
    """
    Build a DataFrame where every row has status='Closed' and the given date pairs.
    Includes all columns expected by load_complaints().
    """
    n = len(created_dates)
    return pd.DataFrame(
        {
            "id":           [f"CMP-{i:03d}" for i in range(1, n + 1)],
            "status":       ["Closed"] * n,
            "created_date": [d.isoformat() for d in created_dates],
            "closed_date":  [d.isoformat() for d in closed_dates],
            "area":         [f"Area{i}" for i in range(n)],
            "category":     ["Water"] * n,
            "description":  [f"desc{i}" for i in range(n)],
            "state":        ["State1"] * n,
            "district":     ["Dist1"] * n,
            "pincode":      ["123456"] * n,
        }
    )


# Strategy: generate a list of (created_date, closed_date) pairs where closed >= created
_date_pair_strategy = st.lists(
    st.tuples(
        st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31)),
        st.dates(min_value=datetime.date(2020, 1, 1), max_value=datetime.date(2030, 12, 31)),
    ).filter(lambda pair: pair[1] >= pair[0]),  # closed_date >= created_date
    min_size=1,
    max_size=10,
)


class TestBug2PreservationAllClosedClosureDays:
    """
    **Property 4: Preservation**

    **Validates: Requirements 3.3, 3.7**

    For all DataFrames where every row has status='Closed' and
    closed_date >= created_date, load_complaints() must produce
    closure_days values numerically identical to:
        (pd.to_datetime(closed_date) - pd.to_datetime(created_date)).dt.days

    EXPECTED TO PASS on unfixed code — the bug only affects non-Closed rows.
    This confirms the all-Closed path is correct and must remain so after the fix.
    """

    @given(date_pairs=_date_pair_strategy)
    @settings(max_examples=100)
    def test_all_closed_closure_days_equal_date_diff(self, date_pairs):
        """
        **Validates: Requirements 3.3, 3.7**

        Property: For any all-Closed DataFrame with valid date pairs (closed >= created),
        load_complaints()['closure_days'] equals
        (pd.to_datetime(closed_date) - pd.to_datetime(created_date)).dt.days
        element-wise.

        EXPECTED TO PASS on unfixed code.
        """
        from unittest.mock import patch as mock_patch

        created_dates = [pair[0] for pair in date_pairs]
        closed_dates  = [pair[1] for pair in date_pairs]

        input_df = _make_all_closed_df(created_dates, closed_dates)

        # Patch read_complaints_df to return our all-Closed DataFrame
        with mock_patch.object(analytics, "read_complaints_df", return_value=input_df):
            result = analytics.load_complaints()

        # Compute the expected closure_days independently
        expected_closure_days = (
            pd.to_datetime(pd.Series([d.isoformat() for d in closed_dates]))
            - pd.to_datetime(pd.Series([d.isoformat() for d in created_dates]))
        ).dt.days

        actual_closure_days = result["closure_days"].reset_index(drop=True)

        # Every row must be Closed — confirm no row was accidentally nulled
        assert result["status"].eq("Closed").all(), (
            "All rows must have status='Closed' in the output"
        )

        # closure_days values must equal the expected day differences
        for i, (actual, expected) in enumerate(
            zip(actual_closure_days, expected_closure_days)
        ):
            assert not pd.isna(actual), (
                f"Row {i}: closure_days is NaN for a Closed row — "
                f"expected {expected} days "
                f"(created={created_dates[i]}, closed={closed_dates[i]})"
            )
            assert int(actual) == int(expected), (
                f"Row {i}: closure_days mismatch — "
                f"got {actual}, expected {expected} "
                f"(created={created_dates[i]}, closed={closed_dates[i]})"
            )

    def test_single_row_known_dates(self, monkeypatch):
        """
        Spot-check with a concrete known date pair: 2024-01-01 → 2024-01-06 = 5 days.

        EXPECTED TO PASS on unfixed code.
        **Validates: Requirements 3.3**
        """
        input_df = _make_all_closed_df(
            created_dates=[datetime.date(2024, 1, 1)],
            closed_dates=[datetime.date(2024, 1, 6)],
        )
        monkeypatch.setattr(analytics, "read_complaints_df", lambda: input_df)

        result = analytics.load_complaints()

        assert result.iloc[0]["status"] == "Closed"
        assert int(result.iloc[0]["closure_days"]) == 5, (
            f"Expected 5 days closure for 2024-01-01 → 2024-01-06, "
            f"got {result.iloc[0]['closure_days']}"
        )

    def test_same_day_closure(self, monkeypatch):
        """
        Edge case: created_date == closed_date → closure_days == 0.

        EXPECTED TO PASS on unfixed code.
        **Validates: Requirements 3.3**
        """
        d = datetime.date(2024, 6, 15)
        input_df = _make_all_closed_df(
            created_dates=[d],
            closed_dates=[d],
        )
        monkeypatch.setattr(analytics, "read_complaints_df", lambda: input_df)

        result = analytics.load_complaints()

        assert int(result.iloc[0]["closure_days"]) == 0, (
            f"Expected 0 days when created and closed on the same day, "
            f"got {result.iloc[0]['closure_days']}"
        )

    def test_multiple_rows_varied_durations(self, monkeypatch):
        """
        Multiple rows with different durations — all Closed.

        EXPECTED TO PASS on unfixed code.
        **Validates: Requirements 3.3, 3.7**
        """
        created_dates = [
            datetime.date(2024, 1, 1),
            datetime.date(2024, 3, 1),
            datetime.date(2024, 6, 1),
        ]
        closed_dates = [
            datetime.date(2024, 1, 11),  # 10 days
            datetime.date(2024, 3, 16),  # 15 days
            datetime.date(2024, 6, 1),   # 0 days
        ]
        expected_days = [10, 15, 0]

        input_df = _make_all_closed_df(created_dates, closed_dates)
        monkeypatch.setattr(analytics, "read_complaints_df", lambda: input_df)

        result = analytics.load_complaints()

        for i, expected in enumerate(expected_days):
            actual = int(result.iloc[i]["closure_days"])
            assert actual == expected, (
                f"Row {i}: expected {expected} days, got {actual} "
                f"(created={created_dates[i]}, closed={closed_dates[i]})"
            )
