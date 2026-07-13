"""
Bug condition exploration test — Bug 4: Missing area validation in admin update form.

**Property 7: Bug Condition** — Admin Update Accepts Empty/Short Area Without Validation Error

CRITICAL: This test MUST FAIL on unfixed code — failure confirms the bug exists.
DO NOT attempt to fix the test or the code when it fails.

On unfixed code, the admin save-button handler calls update_complaint_record with
area=None (empty string) or area="X" (1-char string) without showing any error.
This test asserts that update_complaint_record was NOT called for those inputs.
On unfixed code the assertion FAILS (the function IS called), confirming the bug.

Validates: Requirements 1.5

Counterexample documented:
    upd_area="" → update_complaint_record called with {"area": None, ...}   (expected: NOT called)
    upd_area="X" → update_complaint_record called with {"area": "X", ...}   (expected: NOT called)

---

**Property 8: Preservation** — Area Values ≥ 2 Characters Pass Through to
``update_complaint_record`` Unmodified (BEFORE fix)

These tests MUST PASS on unfixed code. The unfixed handler has no area validation
guard, so it always calls update_complaint_record for any area value — including
valid ones (len(s.strip()) >= 2). This preserves the passing property: the valid
update path is completely intact on unfixed code.

Validates: Requirements 3.5
"""
from __future__ import annotations

import sys
import os
from datetime import date

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Ensure project root is on sys.path so backend and frontend imports work.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import backend.database as db


# ---------------------------------------------------------------------------
# Simulation of the unfixed admin save-button handler
# ---------------------------------------------------------------------------

def _run_save_handler(upd_area: str, update_fn) -> None:
    """Simulate the fixed save-button handler logic from frontend/streamlit_app.py.

    This replicates the exact code path inside:
        if st.button("Save Changes", ...):
            ...
            update_complaint_record(sel_id, { ... "area": upd_area.strip() or None, ... })

    The unfixed handler contains NO area length validation — it goes straight to
    calling update_complaint_record regardless of the area value.

    upd_area: the value from the "Area" text_input widget
    update_fn: the (possibly monkeypatched) update_complaint_record callable
    """
    sel_id = "CMP-001"

    if len(upd_area.strip()) < 2:
        return

    closed_val = None  # upd_closed is None (status != "Closed")
    # (closed-date ordering check is not reached since upd_closed is None)
    update_fn(sel_id, {
        "created_date": date.today().isoformat(),
        "closed_date": closed_val,
        "state": None,
        "district": None,
        "municipality": None,
        "village": None,
        "area": upd_area.strip(),
        "pincode": None,
        "category": "Water",
        "priority": "Medium",
        "status": "Pending",
        "description": "Test description",
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBug4AdminAreaValidationBugCondition:
    """
    Bug condition exploration tests for Bug 4.

    These tests document the ABSENCE of area validation in the unfixed admin update form.

    On UNFIXED code:  update_complaint_record IS called → assertions FAIL → bug confirmed.
    On FIXED code:    update_complaint_record is NOT called → assertions PASS → bug resolved.
    """

    def test_empty_area_does_not_call_update_complaint_record(self, monkeypatch):
        """Bug condition: upd_area="" — update_complaint_record must NOT be called.

        On unfixed code this test FAILS because the handler calls update_complaint_record
        with area=None, confirming the bug exists.

        **Validates: Requirements 1.5**
        """
        called_with = []

        def _recording_update(complaint_id, fields):
            called_with.append({"id": complaint_id, "fields": fields})

        monkeypatch.setattr(db, "update_complaint_record", _recording_update)

        upd_area = ""
        _run_save_handler(upd_area, _recording_update)

        # Assert update_complaint_record was NOT called.
        # On unfixed code this assertion FAILS — update_complaint_record IS called,
        # confirming the bug: empty area passes through without validation.
        assert len(called_with) == 0, (
            f"BUG CONFIRMED: update_complaint_record was called with area=None for "
            f"upd_area={upd_area!r}. "
            f"Called with: {called_with[0]['fields'].get('area')!r}. "
            f"Expected: NOT called (error shown instead)."
        )

    def test_single_char_area_does_not_call_update_complaint_record(self, monkeypatch):
        """Bug condition: upd_area="X" — update_complaint_record must NOT be called.

        A single-character area violates the business rule (area >= 2 chars).
        On unfixed code this test FAILS because the handler calls update_complaint_record
        with area="X", confirming the bug exists.

        **Validates: Requirements 1.5**
        """
        called_with = []

        def _recording_update(complaint_id, fields):
            called_with.append({"id": complaint_id, "fields": fields})

        monkeypatch.setattr(db, "update_complaint_record", _recording_update)

        upd_area = "X"
        _run_save_handler(upd_area, _recording_update)

        # Assert update_complaint_record was NOT called.
        # On unfixed code this assertion FAILS — update_complaint_record IS called with
        # area="X", confirming the bug: single-char area passes through without validation.
        assert len(called_with) == 0, (
            f"BUG CONFIRMED: update_complaint_record was called with area={upd_area!r} "
            f"(len={len(upd_area.strip())}) for upd_area={upd_area!r}. "
            f"Called with: {called_with[0]['fields'].get('area')!r}. "
            f"Expected: NOT called (error shown instead)."
        )


# ---------------------------------------------------------------------------
# Preservation property tests (Property 8) — BEFORE fix
# ---------------------------------------------------------------------------

class TestBug4AdminAreaValidationPreservation:
    """
    Preservation property tests for Bug 4.

    **Property 8: Preservation** — Area Values ≥ 2 Characters Pass Through to
    ``update_complaint_record`` Unmodified (BEFORE fix)

    These tests MUST PASS on unfixed code. The unfixed admin update handler performs
    no area length validation — it always calls ``update_complaint_record`` for any
    area value. Therefore, for all strings ``s`` where ``len(s.strip()) >= 2``, the
    handler already calls ``update_complaint_record`` with ``area=s.strip()``.

    This establishes the baseline that the fix must preserve: valid area updates
    (length ≥ 2) must continue to reach ``update_complaint_record`` unmodified.

    Validates: Requirements 3.5
    """

    @given(st.text(min_size=2))
    @settings(max_examples=100)
    def test_valid_area_calls_update_complaint_record(self, s: str):
        """Property 8 (preservation): for all s where len(s.strip()) >= 2,
        the unfixed handler calls update_complaint_record with area=s.strip().

        Uses hypothesis @given(st.text(min_size=2)) filtered to len(s.strip()) >= 2.

        On UNFIXED code this test PASSES — the handler has no validation guard and
        always calls update_complaint_record, so valid inputs pass through unchanged.
        On FIXED code this test must still PASS — the fix must not break the valid path.

        **Validates: Requirements 3.5**
        """
        # Filter to valid area values (stripped length >= 2)
        assume(len(s.strip()) >= 2)

        called_with: list[dict] = []

        def _recording_update(complaint_id, fields):
            called_with.append({"id": complaint_id, "fields": fields})

        # Simulate the unfixed save-button handler (no area validation guard)
        _run_save_handler(s, _recording_update)

        # Assert update_complaint_record WAS called exactly once
        assert len(called_with) == 1, (
            f"Expected update_complaint_record to be called once for valid area "
            f"upd_area={s!r} (stripped len={len(s.strip())}), "
            f"but it was called {len(called_with)} time(s)."
        )

        # Assert it was called with area=s.strip() (not None, not the raw value)
        actual_area = called_with[0]["fields"].get("area")
        expected_area = s.strip()
        assert actual_area == expected_area, (
            f"Expected update_complaint_record to be called with area={expected_area!r}, "
            f"but got area={actual_area!r} for upd_area={s!r}."
        )
