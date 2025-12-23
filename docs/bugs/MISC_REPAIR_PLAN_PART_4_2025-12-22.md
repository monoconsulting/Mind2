1. Objective & scope

* Objective: Restore reliable AI4 accounting classification coverage and ensure FirstCard “Kortmatchning” shows invoice lines by guaranteeing `invoice_lines` are not blocked by upstream gating and by verifying the WF3 pipeline persists parsed lines.
* In scope:

  * Remove AI4 “hard block” when `receipt_item_count == 0`, so AI4 runs on header totals even when line items are missing.
  * Improve deterministic accounting inputs for AI4:

    * Use a deterministic vendor name fallback (`unified_files.merchant_name`) when `companies.name` is missing.
    * Normalize common Swedish currency shorthand (`KR`) to `SEK`.
    * Deterministically compute missing SEK totals for non-SEK currencies when `gross/net_original` + `exchange_rate` exist.
* Out of scope (explicit):

  * Any changes to AI6 prompt content (user stated it is already updated; skip).
  * Any unrelated refactors or UI changes.

Definition of done

* AI4 no longer gets skipped solely due to `receipt_item_count == 0`.
* AI4 runs when deterministic totals exist (SEK totals present or can be computed deterministically), and moves to manual review only for validated reasons (missing totals, missing exchange rate for non-SEK, missing vendor_name after fallback, gross < net).
* FirstCard invoice uploads produce rows in `invoice_lines` so `/reconciliation/firstcard/invoices/<invoice_id>` and `/reconciliation/firstcard/invoices/<invoice_id>/lines` return non-empty `items` for invoices that contain transaction rows in OCR/AI6 output.
* Verification is repeatable on Windows 11 + Docker with concrete commands.

---

2. Preconditions / setup (Windows 11 + Docker)

Repository evidence

* Nginx reverse proxy exposes the API under `/ai/api/` (nginx/nginx.conf: lines 23–41, `location /ai/api/`) and forwards to `ai-api:5000`.
* Docker Compose exposes:

  * Nginx on `8008` (docker-compose.yml: lines 168–174)
  * MySQL on `3310` (docker-compose.yml: lines 138–152)
  * Redis on `6380` (docker-compose.yml: lines 131–136)
* Backend auto-runs migrations by default (`DB_AUTO_MIGRATE` default `1`) (backend/entrypoint.sh: lines 3–12).

PowerShell commands (run from repo root)

```powershell
docker compose --profile main up -d --build
docker compose ps
```

Sanity checks

```powershell
# API via nginx
curl.exe -s http://localhost:8008/ai/api/health | Out-String

# MySQL port reachable (host)
Test-NetConnection -ComputerName localhost -Port 3310
```

---

3. Task breakdown (detailed)

TASK T-001 — Remove AI4 hard-block on missing receipt items (receipt_item_count=0)
Goal

* AI4 must not be skipped just because there are zero `receipt_items`.
* This directly addresses the observed symptom “kontering fungerar inte” when receipts do not have parsed item rows, but totals exist.

Evidence (current blocking logic)

* `backend/src/services/tasks/ai_pipeline_tasks.py`:

  * Adds block reason `missing_receipt_items` when `receipt_item_count == 0` (around lines 418–419)
  * Then skips AI4 and moves file to manual review (lines 421–437)
  * Source: `ai_pipeline_tasks._run_ai_pipeline` (file range: 59–622)

Files touched

* `backend/src/services/tasks/ai_pipeline_tasks.py`

Step-by-step changes

1. Replace the `receipt_item_count == 0` block that currently appends `missing_receipt_items` to `ai4_block_reasons`.
2. Replace it with a non-blocking log line that explicitly states AI4 will proceed header-only.

Patch (unified diff)

```diff
--- a/backend/src/services/tasks/ai_pipeline_tasks.py
+++ b/backend/src/services/tasks/ai_pipeline_tasks.py
@@ -415,9 +415,13 @@
         if currency and currency != "SEK":
             if missing_exchange_rate or gross_amount_sek is None or net_amount_sek is None:
                 ai4_block_reasons.append("foreign_currency_missing_exchange_rate_or_sek_amounts")
 
         if receipt_item_count == 0:
-            ai4_block_reasons.append("missing_receipt_items")
+            logger.info(
+                "AI4 proceeding with receipt_item_count=0 (header-only accounting); file_id=%s",
+                file_id,
+            )
 
     if ai4_block_reasons:
         reason = "; ".join(ai4_block_reasons)
         _history(
```

Edge cases

* If totals are missing, AI4 still must not run (existing logic remains).
* If currency is non-SEK and `exchange_rate` or SEK totals are missing, AI4 still must not run (existing `foreign_currency_missing_exchange_rate_or_sek_amounts` remains).

Rollback plan

* Revert this diff hunk; AI4 will again be hard-blocked when `receipt_item_count == 0`.

Acceptance criteria

* For a receipt with valid SEK totals but no `receipt_items`, the pipeline reaches AI4 execution branch (`elif accounting_inputs and accounting_inputs.get("ai4_ready")`), and `_history` records AI4 success/error rather than “skipped: missing_receipt_items”.

---

TASK T-002 — Improve deterministic AI4 input readiness: vendor fallback, currency normalization, FX SEK-total computation
Goal

* Ensure `_load_accounting_inputs` produces `ai4_ready=True` whenever deterministic totals exist or can be deterministically derived.
* Ensure vendor name is present even when `company_id`/`companies.name` is missing by falling back to `unified_files.merchant_name`.
* Normalize “KR” → “SEK” deterministically.
* Compute missing SEK totals for foreign currencies when `gross/net_original` and `exchange_rate` exist.

Evidence (current behavior)

* `_load_accounting_inputs` pulls vendor only from `companies.name` (no fallback) and normalizes currency by `.upper()` only:

  * `backend/src/services/tasks/file_management_tasks.py`:

    * SQL selects `c.name AS vendor_name` (lines 412–427)
    * Currency normalization is `currency_norm = str(currency or "").strip().upper()` (line ~449)
    * SEK totals are only filled automatically when `currency_norm == "SEK"` (line ~453)
  * Function: `_load_accounting_inputs` (range 395–585)

Files touched

* `backend/src/services/tasks/file_management_tasks.py`

Step-by-step changes

1. SQL: Select vendor name as `COALESCE(c.name, uf.merchant_name)` so a deterministic OCR vendor string can be used even without a resolved company.
2. Normalize currency:

   * If currency is `KR`, `KR.`, `SEK.`, or `SEK`, set to `SEK`.
3. FX computation (non-SEK):

   * If `exchange_rate` is present and is a `Decimal`, and `*_sek` is NULL while `*_original` exists, compute:

     * `gross_amount_sek = gross_amount_original * exchange_rate` (quantize 0.01)
     * `net_amount_sek = net_amount_original * exchange_rate` (quantize 0.01)
   * Only fill when NULL to avoid overwriting validated SEK totals.

Patch (unified diff)

```diff
--- a/backend/src/services/tasks/file_management_tasks.py
+++ b/backend/src/services/tasks/file_management_tasks.py
@@ -416,7 +416,7 @@
                     uf.gross_amount_original,
                     uf.net_amount_original,
                     uf.currency,
                     uf.exchange_rate,
-                    c.name AS vendor_name,
+                    COALESCE(c.name, uf.merchant_name) AS vendor_name,
                     (
                         SELECT COUNT(*)
                           FROM receipt_items ri
                          WHERE ri.main_id = uf.id
@@ -446,7 +446,9 @@
             vendor_name_norm = (vendor_name or "").strip()
             item_count = int(receipt_item_count or 0)
 
             currency_norm = str(currency or "").strip().upper()
+            if currency_norm in {"KR", "KR.", "SEK.", "SEK"}:
+                currency_norm = "SEK"
             updates: list[str] = []
             params: list[Any] = []
 
             if currency_norm == "SEK":
@@ -474,6 +476,24 @@
                     updates.append("exchange_rate=%s")
                     params.append(exchange_rate)
 
+            elif currency_norm:
+                # Deterministic FX conversion when SEK totals are missing but original totals + exchange_rate exist.
+                # Only fill *_sek fields when they are NULL in DB to avoid overwriting validated SEK totals.
+                if exchange_rate not in (None, 0) and isinstance(exchange_rate, Decimal):
+                    if gross_amount_sek is None and gross_amount_original is not None:
+                        gross_amount_sek = (gross_amount_original * exchange_rate).quantize(Decimal("0.01"))
+                        updates.append("gross_amount_sek=%s")
+                        params.append(gross_amount_sek)
+                    if net_amount_sek is None and net_amount_original is not None:
+                        net_amount_sek = (net_amount_original * exchange_rate).quantize(Decimal("0.01"))
+                        updates.append("net_amount_sek=%s")
+                        params.append(net_amount_sek)
+                else:
+                    # exchange_rate is missing or not a Decimal; leave SEK totals unset.
+                    pass
+
             if updates:
                 updates.append("updated_at=NOW()")
                 params.append(file_id)
                 cur.execute(
```

Edge cases

* Non-SEK currency with missing `exchange_rate`: still returns `ai4_ready=False` with reason “missing exchange_rate for non-SEK currency” (existing branch retained).
* If `exchange_rate` is present but not a Decimal type, the function does not compute SEK totals; it leaves them unset and downstream gating continues to behave deterministically (manual review).
* If OCR/AI3 provides currency “kr” in non-currency context, normalization does not force a currency unless the stored `currency` field contains that token (no new inference added).

Rollback plan

* Revert this diff; vendor fallback, currency normalization, and FX SEK total computation are removed.

Acceptance criteria

* Receipts with:

  * currency = “KR” or “kr” stored → `currency_norm` becomes “SEK”, enabling SEK-fill logic.
  * currency != “SEK”, `gross/net_original` present, `exchange_rate` present → SEK totals computed, enabling `ai4_ready=True`.
  * missing `companies.name` but `unified_files.merchant_name` present → `vendor_name` is non-null.

---

TASK T-003 — Verify FirstCard “Kortmatchning” line visibility end-to-end (no AI6 prompt changes)
Goal

* Confirm that invoice upload triggers WF3 and produces `invoice_lines` such that UI endpoints return line items.

Evidence (WF3 persists invoice_lines and then attempts auto-match)

* `backend/src/services/tasks/workflow_tasks.py` (`wf3_firstcard_invoice`, range 394–1014):

  * Runs AI6 parsing: `run_ai6_credit_card_invoice_parsing` (lines 625–656)
  * Persists credit card items: `_persist_creditcard_invoice_items` (line 780)
  * Persists `invoice_lines`: `_persist_invoice_lines(file_id, invoice_line_payloads)` (line 802)
  * Runs auto matching: `matched_auto, evaluated = auto_match_invoice_lines(file_id)` (line 879)
* UI uses these endpoints (CompanyCard.jsx):

  * Statements list: `/ai/api/reconciliation/firstcard/statements` (CompanyCard.jsx line ~481)
  * Invoice detail: `/ai/api/reconciliation/firstcard/invoices/${invoiceId}` (CompanyCard.jsx line ~533)
  * Lines for matching: `/ai/api/reconciliation/firstcard/invoices/${invoiceId}/lines` (CompanyCard.jsx implied via lines route usage; backend route exists)

Concrete verification commands (Windows 11 + Docker)

1. Upload a FirstCard invoice PDF (example: the user-provided `FC_2503.pdf` / `FC_2505.pdf`) via nginx:

```powershell
# Replace the path with your local file path
$FilePath = "C:\path\to\FC_2503.pdf"

curl.exe -s -X POST `
  -F "invoice=@$FilePath" `
  http://localhost:8008/ai/api/reconciliation/firstcard/upload-invoice
```

Expected: JSON containing `"id"` (invoice_id).
Evidence: route `upload_invoice` at `backend/src/api/reconciliation_firstcard/routes/upload.py` lines 55–75.

2. Poll invoice detail until it contains lines:

```powershell
$InvoiceId = "<id from previous step>"

curl.exe -s http://localhost:8008/ai/api/reconciliation/firstcard/invoices/$InvoiceId | Out-String
```

Evidence: invoice detail endpoint in `backend/src/api/reconciliation_firstcard/routes/status.py` (decorator at line ~208, function `invoice_detail` range 209–471) reads from `invoice_lines` (comment at line ~338).

3. Verify invoice lines pagination endpoint:

```powershell
curl.exe -s "http://localhost:8008/ai/api/reconciliation/firstcard/invoices/$InvoiceId/lines?limit=200&offset=0" | Out-String
```

Evidence: `invoice_lines` handler in `backend/src/api/reconciliation_firstcard/routes/lines.py` (def at lines 36–128) reads `invoice_lines` table and returns `{items,total,matched,...}`.

Database verification (via phpMyAdmin or direct)

* phpMyAdmin exposed on `http://localhost:8087` (docker-compose.yml: lines 155–166).
* Minimal SQL checks:

```sql
-- Confirm persisted invoice lines
SELECT COUNT(*) AS line_count
FROM invoice_lines
WHERE invoice_id = '<invoice_id>';

-- Confirm credit card items were stored (if metadata links main_id)
SELECT uf.id, uf.other_data
FROM unified_files uf
WHERE uf.id = '<invoice_id>';
```

Acceptance criteria

* `invoice_lines` count > 0 for invoices that contain transaction rows in OCR/AI6 output.
* UI “Kortmatchning” shows items after selecting the statement/invoice.

Rollback plan

* No code changes in this task; only verification.

---

4. Test & verification plan

A) Unit/integration tests (Dockerized)

* Run backend test suite:

```powershell
docker compose exec ai-api pytest -q
```

Evidence: `pytest` is included in `requirements.txt` (repo root, lines 1–15).

B) AI4 functional verification (deterministic)

1. Upload/import a receipt that has totals but no receipt line items.
2. Confirm AI4 runs and stores proposals:

```sql
SELECT COUNT(*) AS proposals
FROM ai_accounting_proposals
WHERE receipt_id = '<file_id>';
```

Evidence: proposals stored in `ai_accounting_proposals` (database/migrations/0007_add_ai_accounting_proposals.sql: lines 2–11).

3. Confirm pipeline history shows AI4 executed (not skipped due to missing items):

* Check `ai_processing_history` / `_history` entries (tables exist per migrations; exact table name depends on your schema version).

C) Encoding verification (å/ä/ö)

* Ensure API logs and DB entries preserve Swedish characters end-to-end:

  * Upload an invoice/receipt where merchant contains å/ä/ö.
  * Confirm `invoice_lines.merchant_name` and UI rendering preserves characters.

D) Acceptance criteria per task

* T-001: No occurrences of skip reason `missing_receipt_items` in AI4 gating; AI4 proceeds with `receipt_item_count=0`.
* T-002: `_load_accounting_inputs` returns `ai4_ready=True` for:

  * SEK totals present, vendor present
  * KR currency normalized to SEK
  * FX totals computable (original totals + exchange_rate)
* T-003: FirstCard invoice lines appear via `/reconciliation/firstcard/invoices/<id>/lines`.

---

5. Final validation checklist

* [ ] `docker compose --profile main up -d --build` succeeds and API reachable at `http://localhost:8008/ai/api/`.
* [ ] Upload FirstCard invoice via `/reconciliation/firstcard/upload-invoice` returns an invoice id.
* [ ] `/reconciliation/firstcard/invoices/<id>` returns non-empty lines for invoices with transaction rows.
* [ ] AI4 runs for receipts with totals even when `receipt_items` is empty; proposals saved to `ai_accounting_proposals`.
* [ ] Non-SEK receipts with `exchange_rate` + original totals produce computed SEK totals and run AI4.
* [ ] Swedish characters render correctly in UI and persist in DB.

---
