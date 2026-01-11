from __future__ import annotations

import json
from typing import Any, Sequence
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from api.receipts import receipts_bp
from api.reconciliation_firstcard import recon_bp


class FakeCursor:
    """Minimal cursor stub that returns canned rows for fetchone/fetchall."""

    def __init__(self, fetchone_sequence: Sequence[Any] | None = None, fetchall_sequence: Sequence[Any] | None = None):
        self.fetchone_sequence = list(fetchone_sequence or [])
        self.fetchall_sequence = list(fetchall_sequence or [])
        self._fetchone_calls = 0
        self._fetchall_calls = 0

    def execute(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def fetchone(self) -> Any:
        if not self.fetchone_sequence:
            self._fetchone_calls += 1
            return None
        idx = min(self._fetchone_calls, len(self.fetchone_sequence) - 1)
        self._fetchone_calls += 1
        return self.fetchone_sequence[idx]

    def fetchall(self) -> Any:
        if not self.fetchall_sequence:
            self._fetchall_calls += 1
            return []
        idx = min(self._fetchall_calls, len(self.fetchall_sequence) - 1)
        self._fetchall_calls += 1
        return self.fetchall_sequence[idx]


class CursorContext:
    def __init__(self, cursor: FakeCursor):
        self.cursor = cursor

    def __enter__(self) -> FakeCursor:
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False


def make_db_cursor(cursors: Sequence[FakeCursor]):
    """Return a db_cursor stub that yields FakeCursor objects in order."""
    call_state = {"i": 0}

    def _factory():
        idx = min(call_state["i"], len(cursors) - 1)
        call_state["i"] = min(call_state["i"] + 1, len(cursors))
        return CursorContext(cursors[idx])

    return _factory


@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(recon_bp)
    app.register_blueprint(receipts_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_list_statements_and_invoice_detail(client):
    statement_cursor = FakeCursor(
        fetchone_sequence=[(1,)],
        fetchall_sequence=[
            [
                (
                    "inv-1",
                    "2025-11-02T10:00:00",
                    "2025-11-03T12:00:00",
                    "matching",
                    "ready_for_matching",
                    "2025-10-01",
                    "2025-10-31",
                    json.dumps(
                        {
                            "invoice_summary": {"invoice_number": "INV-1", "card_name": "FirstCard"},
                            "line_counts": {"total": 2, "matched": 1},
                        }
                    ),
                    "stage_import",
                )
            ]
        ],
    )

    invoice_row = (
        "company_card",
        "matching",
        "ready_for_matching",
        "2025-10-01",
        "2025-10-31",
        "2025-11-02T10:00:00",
        json.dumps({"invoice_summary": {"invoice_number": "INV-1"}}),
    )
    invoice_lines = [
        (
            101,
            "2025-10-05",
            "ACME",
            "Lunch",
            125.0,
            "SEK",
            0.95,
            "manual",
            0.9,
            "rec-1",
            "2025-10-05T12:00:00",
            125.0,
            True,
            "2025-10-06T08:00:00",
            "ACME AB",
        )
    ]

    status_cursors = [
        FakeCursor(fetchone_sequence=[invoice_row], fetchall_sequence=[[]]),
        FakeCursor(fetchone_sequence=[], fetchall_sequence=[invoice_lines]),
    ]

    with patch("api.reconciliation_firstcard.routes.statements.db_cursor", make_db_cursor([statement_cursor])), patch(
        "api.reconciliation_firstcard.routes.statements.count_invoice_lines", return_value=(2, 1)
    ):
        resp = client.get("/reconciliation/firstcard/statements")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["statements"][0]["id"] == "inv-1"
        assert payload["statements"][0]["line_counts"]["total"] == 2

    with patch("api.reconciliation_firstcard.routes.status.db_cursor", make_db_cursor(status_cursors)), patch(
        "api.reconciliation_firstcard.routes.status.count_invoice_lines", return_value=(2, 1)
    ):
        resp_detail = client.get("/reconciliation/firstcard/invoices/inv-1")
        assert resp_detail.status_code == 200
        detail = resp_detail.get_json()
        assert detail["invoice"]["id"] == "inv-1"
        assert detail["invoice"]["line_counts"]["matched"] == 1
        assert detail["items"][0]["matched_receipt_id"] == "rec-1"

    line_cursor = FakeCursor(fetchone_sequence=[(2, 1)], fetchall_sequence=[[(101, "2025-10-05", 125.0, "ACME", "Lunch", "manual", 0.9, "rec-1")]])
    with patch("api.reconciliation_firstcard.routes.lines.db_cursor", make_db_cursor([line_cursor])), patch(
        "api.reconciliation_firstcard.routes.lines.load_invoice_document", return_value=True
    ):
        resp_lines = client.get("/reconciliation/firstcard/invoices/inv-1/lines")
        assert resp_lines.status_code == 200
        lines_payload = resp_lines.get_json()
        assert lines_payload["total"] == 2
        assert lines_payload["items"][0]["id"] == 101


def test_receipts_listing_and_match_and_confirm(client):
    receipt_count_cursor = FakeCursor(fetchone_sequence=[(1,)])
    receipt_data_cursor = FakeCursor(
        fetchall_sequence=[
            [
                (
                    "rec-1",
                    "receipt.pdf",
                    "ACME",
                    "2025-10-05T10:00:00",
                    100.0,
                    125.0,
                    "ocr_done",
                    "receipt",
                    "receipt",
                    "user1",
                    "2025-10-05T08:00:00",
                    None,
                    None,
                    None,
                    "travel",
                    None,
                    None,
                    None,
                    "",
                    None,
                )
            ]
        ]
    )

    with patch("api.receipts.db_cursor", make_db_cursor([receipt_count_cursor, receipt_data_cursor])):
        receipts_resp = client.get("/receipts")
        assert receipts_resp.status_code == 200
        receipts_payload = receipts_resp.get_json()
        assert receipts_payload["items"][0]["id"] == "rec-1"

    with patch("api.reconciliation_firstcard.routes.matching.load_invoice_document", return_value=True), patch(
        "api.reconciliation_firstcard.routes.matching.auto_match_invoice_lines", return_value=(1, 1)
    ), patch("api.reconciliation_firstcard.routes.matching.refresh_invoice_match_state", return_value=(2, 1)):
        match_resp = client.post("/reconciliation/firstcard/match", json={"invoice_id": "inv-1"})
        assert match_resp.status_code == 200
        match_payload = match_resp.get_json()
        assert match_payload["matched"] == 1
        assert match_payload["total"] == 2

    transition_proc = MagicMock()
    transition_doc = MagicMock()
    with patch("api.reconciliation_firstcard.routes.statements.db_cursor", lambda: CursorContext(FakeCursor())), patch(
        "api.reconciliation_firstcard.routes.statements.load_invoice_document", return_value=True
    ), patch("api.reconciliation_firstcard.routes.statements.refresh_invoice_match_state", return_value=(2, 2)), patch(
        "api.reconciliation_firstcard.routes.statements.transition_processing_status", transition_proc
    ), patch("api.reconciliation_firstcard.routes.statements.transition_document_status", transition_doc):
        confirm_resp = client.post("/reconciliation/firstcard/statements/inv-1/confirm")
        assert confirm_resp.status_code == 200
        transition_proc.assert_called_once()
        transition_doc.assert_called_once()


# =============================================================================
# NEW TESTS: Manual Matching (PUT /reconciliation/firstcard/lines/<line_id>)
# =============================================================================


def test_manual_match_line_success(client):
    """Verify PUT /lines/<id> updates matched_file_id correctly."""
    # Setup cursors: Line lookup, conflict check, old match value
    line_cursor = FakeCursor(
        fetchone_sequence=[
            ("inv-1", "2025-10-05", 125.0),  # Line data (invoice_id, transaction_date, amount)
            None,  # No conflict - no other line has this receipt
            (None,),  # Old match is NULL
        ]
    )

    with patch(
        "api.reconciliation_firstcard.routes.matching.db_cursor",
        make_db_cursor([line_cursor]),
    ), patch(
        "api.reconciliation_firstcard.routes.matching.transition_line_status_and_link",
        return_value=True,
    ), patch(
        "api.reconciliation_firstcard.routes.matching.log_line_history"
    ), patch(
        "api.reconciliation_firstcard.routes.matching.refresh_invoice_match_state",
        return_value=(2, 1),
    ), patch(
        "api.reconciliation_firstcard.routes.matching._backfill_receipt_card_from_fc"
    ):
        resp = client.put(
            "/reconciliation/firstcard/lines/101",
            json={"matched_file_id": "rec-1", "invoice_id": "inv-1"},
        )

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["ok"] is True


def test_manual_match_line_conflict_receipt_in_use(client):
    """Verify PUT /lines/<id> returns 409 when receipt already matched to another line."""
    # Setup cursors: Line exists, but receipt is already matched to another line (999)
    line_cursor = FakeCursor(
        fetchone_sequence=[
            ("inv-1", "2025-10-05", 125.0),  # Line data
            (999,),  # Conflict: another line (ID 999) already has this receipt
        ]
    )

    with patch(
        "api.reconciliation_firstcard.routes.matching.db_cursor",
        make_db_cursor([line_cursor]),
    ):
        resp = client.put(
            "/reconciliation/firstcard/lines/101",
            json={"matched_file_id": "rec-1", "invoice_id": "inv-1"},
        )

        assert resp.status_code == 409
        payload = resp.get_json()
        assert payload["ok"] is False
        assert payload["reason"] == "receipt_in_use"


def test_manual_match_line_not_found(client):
    """Verify PUT /lines/<id> returns 404 when line does not exist."""
    # Line lookup returns None
    line_cursor = FakeCursor(fetchone_sequence=[None])

    with patch(
        "api.reconciliation_firstcard.routes.matching.db_cursor",
        make_db_cursor([line_cursor]),
    ):
        resp = client.put(
            "/reconciliation/firstcard/lines/999",
            json={"matched_file_id": "rec-1", "invoice_id": "inv-1"},
        )

        assert resp.status_code == 404
        payload = resp.get_json()
        assert payload["ok"] is False
        assert payload["reason"] == "not_found"


def test_manual_match_line_state_conflict(client):
    """Verify PUT /lines/<id> returns 409 when line status transition fails."""
    # Line exists, no receipt conflict, but status transition fails
    line_cursor = FakeCursor(
        fetchone_sequence=[
            ("inv-1", "2025-10-05", 125.0),  # Line data
            None,  # No conflict
            (None,),  # Old match is NULL
        ]
    )

    with patch(
        "api.reconciliation_firstcard.routes.matching.db_cursor",
        make_db_cursor([line_cursor]),
    ), patch(
        "api.reconciliation_firstcard.routes.matching.transition_line_status_and_link",
        return_value=False,  # Transition fails (e.g., line already confirmed)
    ):
        resp = client.put(
            "/reconciliation/firstcard/lines/101",
            json={"matched_file_id": "rec-1", "invoice_id": "inv-1"},
        )

        assert resp.status_code == 409
        payload = resp.get_json()
        assert payload["ok"] is False
        assert payload["reason"] == "line_state_conflict"


def test_manual_match_missing_file_id(client):
    """Verify PUT /lines/<id> returns 400 when matched_file_id is missing."""
    with patch(
        "api.reconciliation_firstcard.routes.matching.db_cursor",
        make_db_cursor([FakeCursor()]),
    ):
        resp = client.put(
            "/reconciliation/firstcard/lines/101",
            json={"invoice_id": "inv-1"},  # Missing matched_file_id
        )

        assert resp.status_code == 400
        payload = resp.get_json()
        assert payload["ok"] is False
        assert payload["reason"] == "invalid_request"
