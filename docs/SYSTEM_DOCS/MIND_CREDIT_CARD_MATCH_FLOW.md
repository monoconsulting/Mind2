# Mind Credit Card Match Flow (2025-10)

This runbook captures the complete FirstCard receipt matching pipeline across backend, database, and frontend layers. Use it to debug reconciliation gaps, trace logging, and rerun matching safely.

---

## 1. End-to-end flow

1. **Workflow dispatch**  
   When a FirstCard statement is imported, `dispatch_workflow` schedules the WF3 chain (`backend/src/services/tasks.py:2134`). The `wf3_firstcard_invoice` task parses the statement, persists invoice lines, and immediately calls `auto_match_invoice_lines` followed by `refresh_invoice_match_state` (`backend/src/services/tasks.py:2980`).

2. **AI receipt-level match**  
   A standalone receipt can be matched against credit-card items via `POST /ai/api/match/creditcard`. This hits `match_credit_card_internal`, which delegates to `AIService.match_credit_card` and persists the outcome (`backend/src/api/ai_processing.py:624` and `backend/src/services/ai_service.py:1206`).

3. **Manual retry from UI**  
   The reconciliation page triggers `POST /ai/api/reconciliation/firstcard/match` to re-run the matcher for a specific invoice (`backend/src/api/reconciliation_firstcard.py:1641`). The endpoint ensures the processing state, reuses `auto_match_invoice_lines`, and refreshes counters.

4. **Manual per-line match**  
   Reassigning a receipt happens through `PUT /ai/api/reconciliation/firstcard/lines/<line_id>` (`backend/src/api/reconciliation_firstcard.py:1699`). It validates the mapping, updates line status, calls `_persist_credit_card_match`, and refreshes invoice totals.

---

## 2. How to rerun matching

- **Invoice level:** `POST /ai/api/reconciliation/firstcard/match` with `{"document_id": "<invoice_id>"}` replays the auto-matcher and updates counts. Programmatically call `auto_match_invoice_lines("<invoice_id>")` followed by `refresh_invoice_match_state("<invoice_id>")`.
- **Single line:** `PUT /ai/api/reconciliation/firstcard/lines/<line_id>` with `{"matched_file_id": "<receipt_id>"}` (and optionally `invoice_id`) links or re-links a receipt.
- **Single receipt vs. card item:** `POST /ai/api/match/creditcard` with receipt metadata to let AI5 suggest and persist a match.

Always verify the resulting database state (see §4) before confirming with users.

---

## 3. Data sources & comparison logic

`auto_match_invoice_lines` (`backend/src/services/tasks.py:1260`) performs these steps:

- Fetches **pending invoice lines** from `invoice_lines` (`match_status` in `NULL/pending/unmatched`) with transaction date, amount, and merchant hint.
- Loads `invoice_documents.metadata_json` via `_load_invoice_metadata` for supplementary context (`backend/src/services/tasks.py:280`).
- Retrieves the related **credit-card statement items** from `creditcard_invoice_items` using `_load_credit_items_for_invoice`, filtering out already matched entries (`backend/src/services/tasks.py:1099`).
- For each pending line, queries candidate receipts in `unified_files`, left-joining `creditcard_receipt_matches` to exclude receipts already in use and `companies` for vendor names (`backend/src/services/tasks.py:1320`). The lookup now falls back to `created_at` when `purchase_datetime` is missing, so day-matching still works for older receipts without enriched timestamps.
- Calculates comparison metrics:
  - `amount_diff` / ratio with ±5 SEK tolerance.
  - `date_diff` in days.
  - Merchant name containment check.
  - Confidence heuristic mixing amount ratio and date difference (`backend/src/services/tasks.py:1356`).
- Selects the best card item via `_select_credit_item_for_line`, which weighs amount distance, date proximity, merchant similarity, and line order (`backend/src/services/tasks.py:1173`).

---

## 4. Persistence & database side-effects

When a match locks in:

| Table | Update | Source |
| --- | --- | --- |
| `invoice_lines` | `matched_file_id`, `match_status` transitions (auto/manual), history entry in `invoice_line_history` | `transition_line_status_and_link` & history insert (`backend/src/services/tasks.py:1459`) |
| `creditcard_receipt_matches` | Upsert of (`receipt_id`, `invoice_item_id`, `matched_amount`) or deletion when unmatched | `_persist_credit_card_match` (`backend/src/api/ai_processing.py:384`) |
| `creditcard_invoice_items` | `matched` flag (0=no match, 1=auto, 2=manual, 3=confirmed) | `_persist_credit_card_match` |
| `unified_files` | `credit_card_match` + `matched` boolean | `_persist_credit_card_match` |
| `invoice_documents.metadata_json` | `line_counts.total/matched/unmatched`, processing status tokens | `refresh_invoice_match_state` (`backend/src/services/tasks.py:1563`) |

Always confirm `invoice_line_history` entries to audit changes and rely on metadata counters for UI tallies.

---

## 5. Frontend update path

`main-system/app-frontend/src/ui/pages/CompanyCard.jsx` orchestrates UI refresh:

- `onMatchDocument` posts to `/reconciliation/firstcard/match`, then reloads statement and detail panes (`CompanyCard.jsx:447`).
- `assignCandidate` posts `PUT /reconciliation/firstcard/lines/<id>`, closes the candidate modal, and refetches lines and statements (`CompanyCard.jsx:552`).
- Line candidate drawer invokes `/reconciliation/firstcard/lines/<id>/candidates` to display current options (`CompanyCard.jsx:526`).

The UI reflects database changes after these refetches; no optimistic updates are performed.

---

## 6. Logging map

Structured logging now emits JSON payloads (see `backend/src/observability/events.py`) with keys prefixed by pipeline stage:

- **Auto matcher:** `matching.auto.lines_fetched`, `matching.auto.candidates_collected`, `matching.auto.matched`, `matching.auto.marked_unmatched`, `matching.auto.completed`, plus error variants like `matching.auto.persist_failed`.
- **Invoice state:** `matching.invoice_state.refreshed`, `matching.invoice_state.refresh_failed`.
- **API triggers:** `matching.api.invoice.requested/completed/failed`, `matching.api.line.requested/completed/failed`.
- **AI5 service:** `matching.ai.requested/result/persisted`, with failures for persistence and AI7 enrichment.

All events carry contextual fields (`invoice_id`, `line_id`, `receipt_id`, diffs, confidence, etc.) to reconstruct the flow in log aggregators.

---

## 7. Operational checklist

1. Trigger the desired endpoint or task (`auto_match_invoice_lines` or manual API).
2. Watch the corresponding `matching.*` log events to confirm each stage executed.
3. Validate database updates:
   - `SELECT match_status, matched_file_id FROM invoice_lines WHERE invoice_id = ...`
   - `SELECT * FROM creditcard_receipt_matches WHERE invoice_item_id = ...`
   - `SELECT metadata_json FROM invoice_documents WHERE id = ...`
4. Reload the reconciliation UI (statements + detail) to ensure new counts surface.

This documentation should give full control over the FirstCard matching lifecycle from ingestion through frontend confirmation.
