## PHASE B — Ultra-tight implementation plan for the dev-agent (English only)

**Date context:** 2025-12-21
**FUNCTION_X scope:** the entire import flow (Upload + FTP → workflow dispatch → OCR → AI1–AI4 → persistence → status + accounting).
**Mojibake:** explicitly out of scope.

This plan is **evidence-driven** and limited to the approved problem list:

- **PX-001** Foreign currency receipts missing `exchange_rate` + SEK amounts
- **PX-002** `manual_review` overwritten by `completed` on `finalize_ok`
- **PX-003** AI4 validation failures recorded as stage “succeeded”
- **PX-004** Missing card last4 even when `payment_type='card'`
- **PX-005** Missing receipt items for many receipts

All evidence references below use repo-relative paths and known line intervals from the approved Phase A.

------

# 1) Objective & scope

## Objective

1. Make import results **trustworthy**: if required data is missing (currency conversion, card last4, AI4 validation), the system must land in **manual_review** and **stay there**.
2. Make AI4 outcomes **truthful** in workflow telemetry: AI4 validation failures must not be marked as “succeeded”.
3. Improve data completeness deterministically where possible (card last4 extraction from OCR text as a safe fallback).
4. Provide deterministic verification using the existing “missing per receipt” report.

## What will be changed

Only code paths directly involved in:

- Workflow finalization / ai_status transitions
  Evidence: `backend/src/services/tasks/workflow_base.py:290–296`
- AI4 stage error handling / stage success flag
  Evidence: `backend/src/services/tasks/ai_pipeline_tasks.py:498–524`
- Missing-field rules / view semantics used by reports
  Evidence: `database/migrations/0047_create_view_v_receipt_missing_status.sql:92–104`, `135–137`
- AI3→DB persistence for payment card last4
  Evidence: `backend/src/api/ai_processing.py:548–551`, normalization helper `backend/src/models/ai_processing.py:137–147`
- Manual review setter
  Evidence: `backend/src/services/tasks/file_management_tasks.py:131–141`

## What will NOT be changed

- No unrelated refactors.
- No changes to models/providers unless required by proven failures.
- No PR workflow instructions.

## Definition of done

- A receipt that hits any of these conditions:

  - currency != SEK and `exchange_rate` missing or SEK amounts missing
  - `payment_type='card'` and last4 missing after fallback extraction attempt
  - AI4 proposals fail validation (e.g., not balanced)

  …must end in **ai_status = manual_review**, must **not** be overwritten to `completed`, and workflow stages must reflect failure/review truthfully.

- Running `missing_per_receipt_2025-12-21_215153.csv` generator on the updated DB shows **no false “completed” statuses** for receipts with missing-critical fields.

------

# 2) Preconditions / setup (Windows 11 + Docker)

## 2.1 Extract ZIP (Windows-safe)

```powershell
$zip  = "C:\path\to\codebase_251221_21-43.zip"
$dest = "C:\temp\codebase_251221_21-43"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -Path $zip -DestinationPath $dest -Force
Set-Location $dest
```

## 2.2 Start stack

```powershell
docker compose up -d --build
docker compose ps
```

## 2.3 Identify DB name/user/password from repo (do not invent)

Read from `.env` and `docker-compose.yml` in the extracted repo. (Do not paste secrets into logs.)

## 2.4 Baseline: generate missing report (current state)

Use the existing report script:

- Evidence: report script reads the missing-status view: `scripts/missing_per_receipt_report.py:51–74`
- Missing rules come from: `database/migrations/0047_create_view_v_receipt_missing_status.sql`

Run (adjust to repo’s actual command entrypoint if different):

```powershell
docker compose exec backend python scripts/missing_per_receipt_report.py --out /tmp/missing_per_receipt.csv
$cid = docker compose ps -q backend
docker cp ${cid}:/tmp/missing_per_receipt.csv .\missing_per_receipt_after.csv
```

Acceptance baseline: file exists and is readable.

------

# 3) Task breakdown (detailed)

## T-001 — Stop overwriting `manual_review` on `finalize_ok` (PX-002)

### Goal

Ensure a receipt marked `manual_review` stays `manual_review` after finalization.

### Files touched

- `backend/src/services/tasks/workflow_base.py`

### Evidence (current bug)

- Finalization overwrites status unconditionally:
  - `backend/src/services/tasks/workflow_base.py:290–296`
    `if stage_base == "finalize_ok" and success: set_ai_status(... completed)`
- Manual review setter exists:
  - `backend/src/services/tasks/file_management_tasks.py:131–141` (`_move_to_manual_review`)

### Step-by-step changes

1. Locate the function in `workflow_base.py` that performs the `finalize_ok` ai_status write (same block as evidence above).
2. Before setting `completed`, **read current ai_status** for the file.
3. Only set `completed` if current status is not already a “stop-the-line” status:
   - keep `manual_review` intact
   - keep failure states intact (if used)

### Patch (unified diff)

```diff
diff --git a/backend/src/services/tasks/workflow_base.py b/backend/src/services/tasks/workflow_base.py
index 0000000..0000000 100644
--- a/backend/src/services/tasks/workflow_base.py
+++ b/backend/src/services/tasks/workflow_base.py
@@ -287,10 +287,26 @@ def complete_import_stage(workflow_run_id: int, stage_key: str, success: bool, message: str = ""):
     # ... existing code above ...
 
     if stage_base == "finalize_ok" and success:
-        set_ai_status(workflow_run_id, "completed")
+        # Do not overwrite stop-the-line statuses (e.g., manual_review).
+        # Evidence for current overwrite bug: workflow_base.py:290–296 (Phase A).
+        current_status = get_ai_status(workflow_run_id)
+        if current_status in ("manual_review", "failed"):
+            # Preserve existing status. Finalize stage may still be marked succeeded,
+            # but ai_status must remain actionable.
+            pass
+        else:
+            set_ai_status(workflow_run_id, "completed")
```

### Notes (determinism)

- `get_ai_status` must already exist somewhere in the repo. If not, you must locate the existing DB accessor used elsewhere for ai_status and reuse it (do not invent new DB utilities).
- Cite its path + line interval in your implementation notes.

### Acceptance criteria

- A receipt set to manual_review remains manual_review after pipeline finalization.
- Verified by DB query:
  - `SELECT ai_status FROM unified_files WHERE id = <receipt_id>;`

### Rollback plan

- Revert this commit.

------

## T-002 — Make AI4 validation failure reflect failure/review, not “succeeded” (PX-003)

### Goal

If AI4 validation fails, the AI4 stage must not be recorded as succeeded, and the receipt must be set to manual_review.

### Files touched

- `backend/src/services/tasks/ai_pipeline_tasks.py`
- (possibly) reuse `backend/src/services/tasks/file_management_tasks.py:_move_to_manual_review` (no change required unless missing context)

### Evidence (current bug)

- AI4 validation error is caught but stage is completed with `success=True`:
  - `backend/src/services/tasks/ai_pipeline_tasks.py:498–524`
- Validation error type imported:
  - `backend/src/services/tasks/ai_pipeline_tasks.py:426`

### Step-by-step changes

1. In the `except AccountingProposalValidationError` handler:
   - call `_move_to_manual_review(file_id, reason=<explicit>)` before finalizing that stage
     Evidence for manual review helper: `backend/src/services/tasks/file_management_tasks.py:131–141`
2. Call `complete_import_stage(... success=False, message=error_msg)` for the AI4 stage.
3. Ensure no subsequent stage sets ai_status to completed (T-001 prevents override).

### Patch (unified diff)

```diff
diff --git a/backend/src/services/tasks/ai_pipeline_tasks.py b/backend/src/services/tasks/ai_pipeline_tasks.py
index 0000000..0000000 100644
--- a/backend/src/services/tasks/ai_pipeline_tasks.py
+++ b/backend/src/services/tasks/ai_pipeline_tasks.py
@@ -498,27 +498,35 @@ def _run_ai_pipeline(file_id: str, workflow_run_id: int, user_id: int) -> list[str]:
     try:
         # ... AI4 run ...
         pass
     except AccountingProposalValidationError as e:
         error_msg = f"{type(e).__name__}: {e}"
+        # Stop-the-line: proposals are not usable. Mark manual_review and reflect failure in stage telemetry.
+        _move_to_manual_review(file_id, reason=error_msg)
         complete_import_stage(
             workflow_run_id,
             "r_ai4",
-            success=True,
+            success=False,
             message=error_msg,
         )
         # Ensure downstream steps do not treat AI4 as succeeded.
         return []
```

### Acceptance criteria

- For a receipt where AI4 proposals are not balanced:
  - workflow stage `r_ai4` is not “succeeded” (status depends on your schema, but `success=False` must produce the “failed” status used by your stage system).
  - `unified_files.ai_status` is `manual_review` and remains so even after `finalize_ok` (T-001).

### Rollback plan

- Revert this commit.

------

## T-003 — Enforce foreign currency prerequisites before AI4 (PX-001)

### Goal

If `currency != 'SEK'` and either `exchange_rate` is missing or SEK amounts are missing, AI4 must not run; receipt must move to manual_review with an explicit reason.

### Files touched

- `backend/src/services/tasks/ai_pipeline_tasks.py` (gate before AI4 call)
- potentially `backend/src/api/ai_processing.py` (only if the prerequisite fields are assembled there; prefer gating at pipeline level)

### Evidence (missing rules)

- Missing view requires `exchange_rate` and SEK amounts when currency != SEK:
  - `database/migrations/0047_create_view_v_receipt_missing_status.sql:92–104`

### Step-by-step changes

1. Locate where AI4 decides whether it has sufficient inputs (near AI4 call site).
2. Read from DB the fields needed to decide:
   - `currency`
   - `exchange_rate`
   - `gross_amount_sek`, `net_amount_sek`, (and/or `vat_amount_sek` if present)
3. If foreign currency prerequisites are missing:
   - `_move_to_manual_review(file_id, reason="foreign_currency_missing_exchange_rate_or_sek_amounts")`
   - mark stage `r_ai4` as skipped **with failure/review semantics** (use your existing stage naming conventions; do not invent a new stage key)
   - do not call AI4 provider

### Patch direction (pseudo-diff; must be made concrete in code)

Insert immediately before AI4 call:

```python
if currency and currency != "SEK":
    missing_fx = (exchange_rate is None)
    missing_sek = (gross_amount_sek is None or net_amount_sek is None)
    if missing_fx or missing_sek:
        _move_to_manual_review(file_id, reason="foreign_currency_missing_exchange_rate_or_sek_amounts")
        complete_import_stage(workflow_run_id, "r_ai4", success=False,
                              message="AI4 blocked: foreign currency requires exchange_rate and SEK amounts.")
        return []
```

### Acceptance criteria

- Any foreign-currency receipt missing fx prerequisites ends in manual_review.
- AI4 is not called (verify via AI history logs: `ai_processing_history` entries for AI4 should not be created for that receipt when blocked).

### Rollback plan

- Revert this commit.

------

## T-004 — Deterministic fallback extraction of card last4 from OCR text (PX-004)

### Goal

When `payment_type='card'` and AI3 did not provide last4, attempt a deterministic extraction from OCR text. If it cannot be extracted safely, force manual_review (and preserve it via T-001).

### Files touched

- `backend/src/api/ai_processing.py` (persistence hook)
- `backend/src/models/ai_processing.py` (reuse normalization helper)
- optionally a new helper module under existing `backend/src/services/` or `backend/src/utils/` if repo already has that pattern (do not invent a new folder structure)

### Evidence (where last4 is persisted)

- Direct mapping without repair:
  - `backend/src/api/ai_processing.py:548–551`
- Normalization exists:
  - `backend/src/models/ai_processing.py:137–147` (`_normalize_last4`)

### Step-by-step changes

1. Locate `_persist_extraction_result(...)`:
   - Evidence: `backend/src/api/ai_processing.py:379–602`
2. Identify where OCR text is available in that function (it must be read from DB or passed in request context—use what exists; do not invent).
3. Add deterministic regex extraction:
   - Extract only when you find an unambiguous last4:
     - patterns like `**** 1234`, `xxxx 1234`, `• • • • 1234`
     - or `Card number ... 1234`
   - If multiple competing last4 matches exist, do not choose; push manual_review.
4. Normalize using existing `_normalize_last4`.
5. If extraction succeeds, persist `credit_card_last_4_digits` and (if possible) infer brand only if already present; do not invent brand.

### Patch (example unified diff; adjust OCR source variable based on evidence)

```diff
diff --git a/backend/src/api/ai_processing.py b/backend/src/api/ai_processing.py
index 0000000..0000000 100644
--- a/backend/src/api/ai_processing.py
+++ b/backend/src/api/ai_processing.py
@@ -1,6 +1,7 @@
 import json
+import re
 from decimal import Decimal
 
 from flask import Blueprint, jsonify, request
@@ -540,12 +541,46 @@ def _persist_extraction_result(file_id: str, extraction_result: dict, user_id: int):
     payment_type = extraction_result.get("payment_type")
     credit_card_last4 = extraction_result.get("credit_card_last_4_digits")
 
+    # Deterministic fallback: if payment_type=card but last4 missing, try extracting from OCR text.
+    # Evidence:
+    # - last4 persisted directly: ai_processing.py:548–551 (Phase A)
+    # - normalization helper exists: models/ai_processing.py:137–147 (Phase A)
+    if payment_type == "card" and not credit_card_last4:
+        ocr_text = extraction_result.get("ocr_text")  # replace with actual OCR source proven in code
+        if ocr_text:
+            candidates = []
+            patterns = [
+                r"(?:\*{2,}|x{2,}|•{2,})\s*([0-9]{4})",
+                r"(?:kortnr|kort nr|card number|card no)\s*[:#]?\s*.*?([0-9]{4})\b",
+                r"\b([0-9]{4})\b\s*(?:contactless|chip|debit|credit)\b",
+            ]
+            lower = ocr_text.lower()
+            for pat in patterns:
+                for m in re.finditer(pat, lower, flags=re.IGNORECASE | re.DOTALL):
+                    candidates.append(m.group(1))
+            candidates = list(dict.fromkeys(candidates))  # stable de-dup
+            if len(candidates) == 1:
+                credit_card_last4 = _normalize_last4(candidates[0])  # reuse existing helper
+                extraction_result["credit_card_last_4_digits"] = credit_card_last4
+            else:
+                # ambiguous or not found -> force manual review upstream (pipeline gate),
+                # do not invent a last4.
+                pass
+
     # existing persistence logic continues...
```

**Important:** You must replace `extraction_result.get("ocr_text")` with the real OCR text source proven by code in this repo (DB column / request context). Cite the exact line interval when you do.

### Acceptance criteria

- For receipts flagged by the missing view as:
  - payment_type=card AND last4 is NULL
    After rerun:
  - If OCR contains an unambiguous last4 → DB stores it.
  - If OCR does not contain a safe last4 → receipt ends in manual_review and stays there.

### Rollback plan

- Revert this commit.

------

## T-005 — Receipt items missing: enforce a deterministic review gate and add traceability (PX-005)

### Goal

If `receipt_items` are missing (item_count=0), the system must either:

- (A) still proceed safely only when AI4 prerequisites and totals are sufficient **and** your SoT/requirements allow it, or
- (B) route to manual_review deterministically.

Given your requirement “tight and trustworthy”, default is **B** unless you can prove A is safe.

### Files touched

- `backend/src/services/tasks/ai_pipeline_tasks.py` (gate before AI4)
- optionally `backend/src/api/ai_processing.py` (ensure items persistence is not silently failing)

### Evidence

- Missing view flags item_count=0:
  - `database/migrations/0047_create_view_v_receipt_missing_status.sql:136–137`
- `_persist_extraction_result` inserts items:
  - `backend/src/api/ai_processing.py:569–577`

### Step-by-step changes

1. Add a gate before AI4:
   - If item_count == 0 → `_move_to_manual_review(file_id, reason="missing_receipt_items")`
   - mark AI4 stage as not successful (success=False) with explicit message
2. Add trace logging (using existing workflow stage message field) indicating whether items were present and how many.

### Acceptance criteria

- Receipts with zero receipt_items do not end as completed without review.
- The reason “missing_receipt_items” is visible in:
  - ai_status (manual_review)
  - workflow stage message

### Rollback plan

- Revert this commit.

------

## T-006 — Re-run pipeline consistency check against “missing_per_receipt” report

### Goal

Ensure the changes improve correctness and make status/telemetry truthful.

### Files touched

- None (verification only)

### Steps

1. Rebuild and restart:

```powershell
docker compose up -d --build
```

1. Generate the report again:

```powershell
docker compose exec backend python scripts/missing_per_receipt_report.py --out /tmp/missing_per_receipt.csv
$cid = docker compose ps -q backend
docker cp ${cid}:/tmp/missing_per_receipt.csv .\missing_per_receipt_after.csv
```

1. Compare to baseline:

- Count receipts with missing critical fields and check ai_status/stage truthfulness.

### Acceptance criteria

- Any receipt still missing:
  - foreign currency fx/SEK amounts OR card last4 OR receipt items OR AI4 validation
    must be in manual_review (not completed) and must not have AI4 stage marked succeeded.

------

# 4) Test & verification plan (mandatory)

## 4.1 DB validation queries (read-only)

Use the missing-status semantics and verify the three critical issues:

### A) Foreign currency prerequisites

```sql
SELECT id, currency, exchange_rate, gross_amount_sek, net_amount_sek, ai_status
FROM unified_files
WHERE currency IS NOT NULL AND currency <> 'SEK';
```

**Pass/fail:**

- If exchange_rate or SEK amounts are NULL → ai_status must be manual_review.

### B) Card payments missing last4

```sql
SELECT id, payment_type, credit_card_last_4_digits, ai_status
FROM unified_files
WHERE payment_type='card';
```

**Pass/fail:**

- If last4 NULL → ai_status must be manual_review.

### C) AI4 stage truthfulness

```sql
SELECT workflow_run_id, stage_key, status, message
FROM workflow_stage_runs
WHERE stage_key='r_ai4'
ORDER BY workflow_run_id DESC;
```

**Pass/fail:**

- Any message containing validation error must not have “succeeded” status (or equivalent).

> Adjust `status` values to your schema’s exact vocabulary, but they must align with `success=False` behavior.

## 4.2 Encoding verification (å/ä/ö)

Even though mojibake is out of scope, you still must prove UTF-8 survives:

- Pick one receipt item containing `å/ä/ö` (known-good per your statement).
- Verify:
  - DB select returns correct text
  - API returns correct text
  - UI renders correct text

Do not “assume”; show evidence via query outputs and an API call.

------

# 5) Final validation checklist

-  `manual_review` is never overwritten by `finalize_ok` (`workflow_base.py` fix applied and tested).
  Evidence anchor: `backend/src/services/tasks/workflow_base.py:290–296`
-  AI4 validation failures are recorded as failure/review, not succeeded.
  Evidence anchor: `backend/src/services/tasks/ai_pipeline_tasks.py:498–524`
-  Foreign currency receipts without fx prerequisites are blocked from AI4 and routed to manual_review.
  Evidence anchor: `database/migrations/0047_create_view_v_receipt_missing_status.sql:92–104`
-  Card last4 fallback extraction exists, is deterministic, and never invents data.
  Evidence anchors: `backend/src/api/ai_processing.py:548–551`, `backend/src/models/ai_processing.py:137–147`
-  Missing receipt_items (item_count=0) routes to manual_review (tight correctness).
  Evidence anchor: `database/migrations/0047_create_view_v_receipt_missing_status.sql:136–137`
-  `missing_per_receipt` report after changes matches the truth: missing-critical receipts are in manual_review, not completed.
  Evidence anchor: `scripts/missing_per_receipt_report.py:51–74`

------

## One critical instruction to the dev-agent (non-negotiable)

For every task above, before committing:

1. Add a short “Evidence” section in your dev notes with **path + line interval** and symbol name.
2. Demonstrate the behavioral change with **exact commands and queries** shown above.

