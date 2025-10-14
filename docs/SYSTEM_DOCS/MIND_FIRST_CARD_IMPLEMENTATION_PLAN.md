# MIND First Card Implementation Plan

```
Version: 0.1-draft
Date: 2025-10-13
Author: Codex (TM000-creditcard-matching-analysis)
```

> **Scope:** Deliver end-to-end credit card invoice ingestion, OCR, AI-assisted extraction, receipt matching, and UI surfacing for the "Kortmatchning" experience. All work must respect CLAUDE.md (no mock data, never use `merchant_name` in `unified_files`, no SQLite) and the production testing rules in `docs/TEST_RULES.md`.

---

## 1. Objectives

- Enable users to upload monthly credit card invoices via the existing `/reconciliation/firstcard/upload-invoice` endpoint and transition them through OCR, parsing, and AI matching using the standardized invoice state machine.
- Persist parsed invoice lines with confidence metadata, link matched receipts through `creditcard_receipt_matches`, and expose reconciliation status consistently in API and UI.
- Provide a rich frontend workflow where accountants can browse invoices by month, inspect individual line matches, preview linked receipts, and resolve unmatched lines.
- Supply automated test coverage (backend + Playwright) that proves the workflow without introducing mock fixtures.

---

## 2. Current Gaps Summary

| Area | Gap | Impact |
|------|-----|--------|
| State lifecycle | `upload-invoice` seeds `status='processing'` and never transitions `processing_status` beyond `uploaded`. | OCR jobs complete but the state machine never progresses; downstream tasks are starved. |
| Invoice parsing | `process_invoice_document` is a placeholder; invoice lines must be injected manually via JSON imports. | No automatic population of `invoice_lines`; match automation infeasible. |
| Matching | `/reconciliation/firstcard/match` inserts into `invoice_lines` only; it bypasses `creditcard_receipt_matches` and does not emit confidence metadata. | Manual review lacks traceability and AI5 history. |
| API surface | `/reconciliation/firstcard/statements` filters `invoice_type='company_card'` and omits processing metadata. | Uploaded invoices (type `credit_card_invoice`) remain invisible to the frontend. |
| Frontend UX | `CompanyCard.jsx` shows a coarse table and "Auto-match" button only; no invoice drill-down or modal integration. | Users cannot reconcile or inspect matches per requirement. |
| Tests | Integration tests stop at upload/status; there is no end-to-end UI coverage. | Regression risk remains high; no evidence the workflow works. |
| Sample data | Real First Card invoice files exist under the repository folder `fc/`. | Parsing logic must be validated against actual production-format PDFs rather than synthetic fixtures. |

---

## 3. High-Level Delivery Phases

1. **State Machine Alignment (Backend)**
   - Normalize initial states, persist metadata, and wire OCR completion to invoice processing tasks.
2. **Invoice Parsing Pipeline**
   - Implement deterministic parsing + AI fallback, populate `invoice_lines`, and record OCR source text/confidence.
3. **Matching Engine & Persistence**
   - Invoke AI5 for each invoice line, store results in `creditcard_receipt_matches`, update line statuses, and log history.
4. **API & DTO Enhancements**
   - Enrich statement listings, expose invoice detail endpoints, and provide receipt context for matched lines.
5. **Frontend Experience**
   - Build invoice navigation, line tables with match indicators, and augment receipt preview modal with match badges.
6. **Testing & Observability**
   - Expand pytest integration/unit suites; add Playwright specs and ensure metrics/logging support monitoring.

---

## 4. Detailed Task List

### Phase 1 – State Lifecycle Foundation

1. **Normalize Upload Status** *(DONE)*
   - Update `upload_invoice` to set `InvoiceDocumentStatus.IMPORTED` and `InvoiceProcessingStatus.OCR_PENDING` via `transition_*` helpers.
   - Persist `source_file_id`, `page_ids`, `processing_status`, and `submitted_by` metadata in `invoice_documents.metadata_json`.
2. **OCR Completion Orchestration** *(DONE)*
   - Extend `_maybe_advance_invoice_from_file` to detect when all pages hit `_OCR_COMPLETE_STATUSES`, transition to `AI_PROCESSING`, and enqueue `process_invoice_document`.
   - Record per-page status in metadata (`page_status`) ensuring idempotent transitions.
3. **Regression Tests** *(DONE)*
   - Update `backend/tests/integration/test_invoice_upload_status.py` to assert correct status transitions and Celery scheduling stubs.

### Phase 2 – Invoice Parsing

4. **Implement `process_invoice_document`** *(DONE)*
   - Fetch invoice metadata, retrieve OCR text for each page, run deterministic parser (regex-based) with AI fallback subject to existing prompt guidelines.
   - Insert/update `invoice_lines` (with `extraction_confidence`, `ocr_source_text`), set `processing_status` to `ready_for_matching`, and transition document status to `matching`.
5. **Shared Parser Utilities** *(DONE)*
   - Create a parsing helper module (e.g., `services/invoice_parser.py`) returning structured lines and header metadata; ensure no forbidden `merchant_name` usage.
6. **Unit Tests**
   - Add pytest coverage for parser success/failure paths and for `process_invoice_document` state transitions using fake DB cursor.
   - Include regression tests that load representative PDFs from the `fc/` directory to exercise realistic layouts (ensure no mock data is introduced).
   - Verify multi-page PDF handling mirrors the receipt ingestion workflow (PDF → PNG via `pdf_to_png_pages` → OCR text ingestion) so statement pages receive consistent processing.

### Phase 3 – Matching Engine

7. **AI5 Invocation Workflow** *(DONE)*
   - For each `invoice_lines` row in `pending/unmatched`, derive candidate receipts (date/amount) and call `match_credit_card_internal`.
   - Persist matches via `_persist_credit_card_match` ensuring `creditcard_receipt_matches` is updated and `unified_files.credit_card_match` toggled.
8. **Manual Review Hooks** *(DONE)*
   - Store results in `invoice_line_history`, set `match_status` to `auto` or `unmatched`, and expose unmatched receipts for remediation.
9. **Metrics & Logging** *(DONE)*
   - Emit observability metrics (`record_invoice_decision`, `record_invoice_state_assertion`) for match outcomes and illegal transitions.
10. **Unit/Integration Tests** *(DONE)*
    - Extend integration tests to simulate matching and verify DB effects (without mock data).

### Phase 4 – API Enhancements

11. **Statements Listing** *(DONE)*
    - Modify `/reconciliation/firstcard/statements` to include both `company_card` and `credit_card_invoice` types, returning `status`, `processing_status`, `line_counts`, `period_start/end`, and upload metadata.
12. **Invoice Detail Endpoint** *(DONE)*
    - Add `/reconciliation/firstcard/invoices/{id}` (GET) returning invoice header, lines with match summaries, and receipt metadata (vendor, amount, `credit_card_match` flag).
13. **Line Candidates Endpoint** *(DONE)*
    - Provide `/reconciliation/firstcard/lines/{id}/candidates` listing potential receipts for manual assignment (sorted by similarity).
14. **Schema/Contract Updates** *(DONE)*
    - Update OpenAPI contract (`specs/001-mind-system-receipt/contracts/reconciliation_firstcard.yaml`) and regenerate documentation if required.

### Phase 5 – Frontend Experience

15. **Company Card Page** *(DONE)*
    - Refactor `CompanyCard.jsx` to display monthly invoice selector, status chips, and detailed line table with match badges and manual action buttons.
16. **Receipt Preview Modal** *(DONE)*
    - Add a prominent “Matchad” indicator when `credit_card_match` is true; show linked invoice line info and provide quick navigation.
17. **Manual Match UI** *(DONE)*
    - Implement modal/drawer for assigning receipts to lines using the new candidates endpoint; ensure optimistic UI updates.
18. **State Polling**
    - Introduce polling or WebSocket stub (polling acceptable for MVP) to refresh invoice state until processing completes.
19. **UI Tests**
    - Add/extend Playwright specs under `web/tests/` verifying invoice listing, line display, match badges, and receipt preview indicators. Follow `docs/TEST_RULES.md` (video 1900×120, snapshot 1900×1200, reports in `web/test-reports/`).

### Phase 6 – Quality, Docs, and Ops

20. **Backend Test Matrix**
    - Run pytest suites covering new code paths; document results with references to DB tables affected (as required by TEST_RULES).
21. **Playwright Reports**
    - Capture reports per rule, store artifacts, and link them in future PR description.
22. **Documentation**
    - Update `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` and `docs/SYSTEM_DOCS/MIND_INVOICE_MATCH_IMPLEMENTATION_PLAN_v1.1.md` with any API/UX adjustments.
23. **Operational Readiness**
    - Add runbook notes (alerts, dashboards) for new metrics and state transitions; coordinate with DevOps if additional monitoring is required.

- **Sample Assets:** Real First Card statement files are stored under `fc/`; treat these as reference inputs for parser validation and ensure they remain untouched in git history (read-only usage).
- **PDF Handling:** Many `fc/` assets are multi-page PDFs; always run them through the established receipt pipeline (PDF → PNG conversion → OCR) before extraction to guarantee parity with production behavior.

---

## 5. Dependencies & Constraints

- **No Mock Data:** All tests must operate against deterministic fixtures created within the DB layer or via existing ingestion paths.
- **Database:** Use existing MySQL tables and migrations; do not introduce SQLite.
- **Ports:** Respect assigned ports (5169 dev frontend, 8008 production) — no changes without approval.
- **Testing Harness:** Playwright config is immutable (`playwright.config.ts` cannot be edited); rely on `playwright.dev.config.ts` for dev runs if needed.
- **AI Prompts:** Reuse existing AI5 prompt definitions; any prompt change must go through documentation review.

---

## 6. Milestones & Deliverables

| Milestone | Deliverable | Definition of Done |
|-----------|-------------|--------------------|
| M1 | State machine fixes | Upload → OCR transitions succeed; integration tests updated. |
| M2 | Invoice parsing | `process_invoice_document` populates lines; confidence logged. |
| M3 | Matching engine | AI5 matches stored; unmatched lines flagged; metrics emitted. |
| M4 | API surface | Enhanced endpoints documented and tested. |
| M5 | Frontend UX | Invoice selection, line table, receipt preview badges functional; Playwright coverage passing 100%. |
| M6 | Documentation & Ops | Workflow docs updated; test reports archived; monitoring guidance delivered. |

---

## 7. Open Questions / Follow-Ups

1. Confirm availability of invoice extraction AI prompt/model; if external service required, ensure credentials/config are documented.
2. Determine retention policy for `ocr_source_text` to balance traceability vs. storage cost.
3. Decide whether manual receipt assignment should lock matched receipts to prevent duplicates or allow split matches (not yet supported).
4. Validate if additional dashboard metrics are required by finance stakeholders (e.g., unmatched invoice lines aging).

---

## 8. Next Actions

1. Kick off Phase 1 tasks (#1–3) on branch `TM000-creditcard-matching-analysis`.
2. Align with stakeholders on open questions (Section 7).
3. Prepare development task tickets aligned with phases and milestones for parallel workstreams if multiple agents join.

--- 

**End of document.**
