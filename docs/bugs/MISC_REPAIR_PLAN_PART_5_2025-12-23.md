## Phase B — Agent-ready implementation plan (English only)

### 1) Objective & scope

**Objective:** Eliminate silent/partial failures in the FirstCard (FC) invoice pipeline so that:

* FC invoice lines are **actually persisted** into `invoice_lines`.
* The workflow **never** transitions to `READY_FOR_MATCHING` when **0** (or mismatched) lines were persisted.
* DB migration failures can no longer be silently ignored (they currently are), because that leads directly to “imported but no lines/matching UI empty”.
* AI4 accounting proposals stop failing silently when schema is missing `ai_accounting_proposals.item_id`.

**In scope (only):**

* WF3 FirstCard invoice stage (persist + status transitions) in `backend/src/services/tasks/workflow_tasks.py` (current behavior shown at `items_inserted ... inserted_invoice_lines ... metadata["line_counts"]=len(extraction.lines) ... READY_FOR_MATCHING` in `backend/src/services/tasks/workflow_tasks.py:789-858`).
* Invoice line persistence + observability in `backend/src/services/tasks/invoice_tasks.py` (silent swallow currently at `_persist_invoice_lines` in `backend/src/services/tasks/invoice_tasks.py:175-213`).
* Migration correctness & baseline detection in `backend/src/services/db/migrations.py` (baseline check currently does **not** validate critical columns; see `backend/src/services/db/migrations.py:227-257`).
* Fail-fast on migration failure in `backend/entrypoint.sh` (currently continues even if migrations fail at `backend/entrypoint.sh:5-11`).
* AI4 accounting proposal persistence logging in `backend/src/services/tasks/file_management_tasks.py` (silent swallow in two places at `backend/src/services/tasks/file_management_tasks.py:655-656` and `backend/src/services/tasks/file_management_tasks.py:683-684`).
* Add an idempotent schema repair migration for MySQL to ensure required columns exist even if baseline previously skipped broken migrations (migrations with `ADD COLUMN IF NOT EXISTS` are present at `database/migrations/0010_2025_10_10_ai_system_prompts_schema_update.sql:1-8` and `database/migrations/0026_2025_12_20_invoice_matching_enhancements.sql:26-33`, and `ai_accounting_proposals.item_id` is added at `database/migrations/0027_2025_12_21_receipt_preview_modal_enhancements.sql:39-42`).

**Out of scope:**

* Any changes to AI6 prompt content (per your instruction).
* Any unrelated refactors.

**Definition of done:**

1. After importing an FC PDF, `invoice_lines` contains rows for that invoice and the API returns them via `GET /reconciliation/firstcard/lines/<invoice_id>` (route defined in `backend/src/api/reconciliation_firstcard/routes/lines.py:40-63`).
2. WF3 **does not** set `READY_FOR_MATCHING` when persisted line count is 0 or mismatched.
3. If migrations fail, the backend container **fails fast** (unless explicitly overridden).
4. If AI4 cannot persist accounting proposals, the system logs the exception instead of silently returning false.

---

### 2) Preconditions / setup (Windows 11 + Docker)

Run everything from PowerShell in the repo root (where `docker-compose.yml` exists):

```powershell
docker compose --profile main up -d --build
docker compose --profile main ps
```

Backend auto-migrations are controlled in `backend/entrypoint.sh` via `DB_AUTO_MIGRATE` (defaults to enabled) at `backend/entrypoint.sh:5-12`.

**Pre-flight DB verification (inside MySQL container):**

```powershell
docker compose --profile main exec mysql mysql -u root -p -e "USE mind2; SHOW COLUMNS FROM invoice_lines LIKE 'extraction_confidence';"
docker compose --profile main exec mysql mysql -u root -p -e "USE mind2; SHOW COLUMNS FROM invoice_lines LIKE 'ocr_source_text';"
docker compose --profile main exec mysql mysql -u root -p -e "USE mind2; SHOW COLUMNS FROM ai_accounting_proposals LIKE 'item_id';"
```

If any are missing, the plan below ensures they will be created deterministically.

---

### 3) Task breakdown

---

#### T-001 — Stop WF3 from continuing when invoice lines were not persisted

**Goal:** Prevent the current silent transition to `READY_FOR_MATCHING` regardless of DB persistence, and stop using `len(extraction.lines)` as the source of truth for persisted line counts.

**Why:** WF3 currently:

* Persists lines, but then sets `metadata["line_counts"]` from `len(extraction.lines)` and transitions to `READY_FOR_MATCHING` without any guard (shown in `backend/src/services/tasks/workflow_tasks.py:789-858`).
* This can produce “imported but no lines” while still moving forward.

**Files touched:**

* `backend/src/services/tasks/workflow_tasks.py`
* `backend/src/services/tasks/invoice_tasks.py` (for `_count_invoice_lines`, see T-002)

**Patch (unified diff):**

```diff
--- a/backend/src/services/tasks/workflow_tasks.py
+++ b/backend/src/services/tasks/workflow_tasks.py
@@ -32,6 +32,7 @@
 from .invoice_tasks import (
     _ensure_invoice_document,
     _persist_invoice_lines,
+    _count_invoice_lines,
     _persist_creditcard_invoice_items,
     _update_invoice_metadata,
     _load_invoice_metadata,
@@ -820,18 +821,73 @@
     inserted_invoice_lines = _persist_invoice_lines(file_id, invoice_line_payloads)
 
     metadata = _load_invoice_metadata(file_id) or {}
-    metadata["line_counts"] = {
-        "total": len(extraction.lines),
-        "matched": 0,
-        "unmatched": len(extraction.lines),
-    }
-    metadata["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
-    _update_invoice_metadata(file_id, metadata)
+ 
+    extracted_total = len(extraction.lines)
+    persisted_total = _count_invoice_lines(file_id)
+
+    metadata["line_counts"] = {
+        "total": persisted_total,
+        "matched": 0,
+        "unmatched": persisted_total,
+        "extracted_total": extracted_total,
+        "persisted_total": persisted_total,
+        "persist_attempted": inserted_invoice_lines,
+    }
+
+    if extracted_total == 0 or persisted_total == 0 or persisted_total != extracted_total:
+        if extracted_total == 0:
+            reason = "AI6 produced 0 invoice lines; cannot proceed to matching."
+        elif persisted_total == 0:
+            reason = (
+                "Persisted 0 invoice lines although AI6 returned lines. "
+                "This strongly indicates a DB schema mismatch (migrations not applied) or a SQL error."
+            )
+        else:
+            reason = (
+                f"Persisted invoice line count mismatch: extracted={extracted_total}, persisted={persisted_total}. "
+                "Stop-the-line to avoid silent matching on incomplete data."
+            )
+
+        metadata["processing_status"] = InvoiceProcessingStatus.FAILED.value
+        metadata["last_error"] = {
+            "code": "invoice_lines_persist_failed",
+            "message": reason,
+            "extracted_total": extracted_total,
+            "persisted_total": persisted_total,
+        }
+        _update_invoice_metadata(file_id, metadata)
+
+        fc_coordinator.begin_fc_import_stage(
+            workflow_run_id,
+            "fc_ready",
+            message="Förbereder fakturan för matchning",
+        )
+        fc_coordinator.complete_fc_import_stage(
+            workflow_run_id,
+            "fc_ready",
+            success=False,
+            message=reason,
+        )
+        transition_processing_status(
+            file_id,
+            InvoiceProcessingStatus.FAILED,
+            (
+                InvoiceProcessingStatus.AI_PROCESSING,
+                InvoiceProcessingStatus.OCR_DONE,
+                InvoiceProcessingStatus.OCR_PENDING,
+                InvoiceProcessingStatus.READY_FOR_MATCHING,
+            ),
+        )
+        transition_document_status(
+            file_id,
+            InvoiceDocumentStatus.FAILED,
+            (
+                InvoiceDocumentStatus.IMPORTED,
+                InvoiceDocumentStatus.MATCHING,
+            ),
+        )
+        log_finalize_failure(workflow_run_id, reason)
+        return workflow_run_id
+
+    metadata["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
+    _update_invoice_metadata(file_id, metadata)
```

**Edge cases handled:**

* AI6 extracts 0 lines → explicit failure (no silent match stage).
* DB persists 0 lines (schema mismatch / SQL error) → explicit failure + metadata error.
* Partial mismatch → explicit failure.

**Acceptance criteria:**

* Import an FC PDF; if `invoice_lines` is empty, the invoice ends in `FAILED` (not `READY_FOR_MATCHING`) and `metadata.last_error` is populated.

---

#### T-002 — Make invoice line persistence observable and add DB-count source of truth

**Goal:** Stop returning a misleading “partial inserted” count when the DB transaction rolled back, and provide a deterministic “persisted count” function.

**Why:**

* `_persist_invoice_lines` catches exceptions and returns `inserted`, but the DB cursor context rolls back on exception, making `inserted` potentially misleading (function shown at `backend/src/services/tasks/invoice_tasks.py:175-213`).
* WF3 needs a DB count, not an attempted counter.

**Files touched:**

* `backend/src/services/tasks/invoice_tasks.py`

**Patch (unified diff):**

```diff
--- a/backend/src/services/tasks/invoice_tasks.py
+++ b/backend/src/services/tasks/invoice_tasks.py
@@ -204,8 +204,29 @@
-    except Exception:
-        return inserted
+    except Exception as exc:
+        logger.exception("Failed to persist invoice_lines for invoice_id=%s; transaction rolled back: %s", invoice_id, exc)
+        return 0
     return inserted
 
+def _count_invoice_lines(invoice_id: str) -> int:
+    """Count persisted invoice lines for a credit-card invoice.
+
+    Args:
+        invoice_id: The ``invoice_documents.id`` / ``invoice_lines.invoice_id`` to count.
+
+    Returns:
+        Number of rows in ``invoice_lines`` for this invoice, or 0 if DB is unavailable.
+    """
+    if db_cursor is None:
+        return 0
+    try:
+        with db_cursor() as cur:
+            cur.execute('SELECT COUNT(1) FROM invoice_lines WHERE invoice_id=%s', (invoice_id,))
+            row = cur.fetchone()
+            return int(row[0] or 0) if row else 0
+    except Exception as exc:
+        logger.exception("Failed to count invoice_lines for invoice_id=%s: %s", invoice_id, exc)
+        return 0
```

**Acceptance criteria:**

* If schema is wrong and INSERT fails, logs contain the exception and WF3 fails (T-001).
* If schema is correct, `_count_invoice_lines(invoice_id)` equals extracted line count.

---

#### T-003 — Fail fast when DB migrations fail (stop silent bad schema)

**Goal:** Prevent the backend from starting when migrations fail (unless explicitly overridden).

**Why:** `backend/entrypoint.sh` currently runs migrations and then continues even on failure (`|| echo ...`) at `backend/entrypoint.sh:5-11`. This directly enables the “imported but empty lines / AI4 fails silently” class of errors.

**Files touched:**

* `backend/entrypoint.sh`

**Patch (unified diff):**

```diff
--- a/backend/entrypoint.sh
+++ b/backend/entrypoint.sh
@@ -3,9 +3,18 @@
 if [ "${DB_AUTO_MIGRATE:-1}" = "1" ]; then
     echo "Running database migrations..."
-    python -c "from services.db.migrations import apply_migrations; apply_migrations()" || echo "Migration step failed (continuing anyway)."
+    python -c "from services.db.migrations import apply_migrations; apply_migrations()" || {
+        if [ "${DB_MIGRATIONS_ALLOW_FAILURE:-0}" = "1" ]; then
+            echo "Warning: Database migrations failed, but continuing (DB_MIGRATIONS_ALLOW_FAILURE=1)."
+            echo "System behavior may be incorrect until schema is fixed."
+        else
+            echo "ERROR: Database migrations failed. Refusing to start server."
+            echo "Set DB_MIGRATIONS_ALLOW_FAILURE=1 to override (not recommended for production)."
+            exit 1
+        fi
+    }
 fi
```

**Acceptance criteria:**

* Introduce a deliberate migration syntax error → container exits (unless `DB_MIGRATIONS_ALLOW_FAILURE=1`).

---

#### T-004 — Make migration execution compatible and baseline detection stricter

**Goal:** Ensure migrations execute deterministically on MySQL even if migration files contain MySQL-incompatible `ADD COLUMN IF NOT EXISTS`, and prevent baseline mode from silently skipping required columns.

**Why:**

* Baseline “provisioned” check currently validates only a handful of tables/columns and does not validate `invoice_lines` and `ai_accounting_proposals.item_id` (`backend/src/services/db/migrations.py:227-257`).
* Migrations containing `ADD COLUMN IF NOT EXISTS` exist (`database/migrations/0026...:26-33`, `database/migrations/0010...:1-8`), which can fail depending on MySQL syntax support—leading to missing columns and downstream silent failures.

**Files touched:**

* `backend/src/services/db/migrations.py`

**Patch (unified diff):**

```diff
--- a/backend/src/services/db/migrations.py
+++ b/backend/src/services/db/migrations.py
@@ -252,6 +252,15 @@
         if not _column_exists(cur, "unified_files", "merchant_name"):
             missing.append("unified_files.merchant_name")
 
+    # Critical columns required by current conversion + matching flows
+    if not _column_exists(cur, "invoice_lines", "extraction_confidence"):
+        missing.append("column:invoice_lines.extraction_confidence")
+    if not _column_exists(cur, "invoice_lines", "ocr_source_text"):
+        missing.append("column:invoice_lines.ocr_source_text")
+
+    if not _column_exists(cur, "ai_accounting_proposals", "item_id"):
+        missing.append("column:ai_accounting_proposals.item_id")
+
     return (len(missing) == 0, missing)
 
+def _normalize_mysql_statement(stmt: str) -> str:
+    """Normalize migration SQL for MySQL compatibility.
+
+    This codebase historically shipped migrations using DDL like:
+    ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...``.
+
+    MySQL 8 does not support the ``IF NOT EXISTS`` modifier for ``ADD COLUMN``. To keep the
+    existing migration files stable while remaining deterministic, we rewrite the statement
+    at execution time.
+
+    Args:
+        stmt: Single SQL statement (no trailing semicolon).
+
+    Returns:
+        Normalized SQL statement safe to execute on MySQL.
+    """
+    upper = stmt.upper()
+    if upper.startswith("ALTER TABLE") and "ADD COLUMN IF NOT EXISTS" in upper:
+        # Replace case-insensitively while preserving the rest of the statement.
+        return re.sub(r"\bADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\b", "ADD COLUMN", stmt, flags=re.IGNORECASE)
+    return stmt
+
@@ -559,6 +568,7 @@
                     safe_stmt = _transform_prompt_statement(
                         safe_stmt, meta.get("applied_at"), meta.get("original_checksum")
                     )
                     if safe_stmt is None:
                         continue
+                    safe_stmt = _normalize_mysql_statement(safe_stmt)
                     cur.execute(safe_stmt)
```

**Acceptance criteria:**

* New DB: migrations apply fully; columns exist afterward.
* Existing DB with baseline drift: the baseline check now reports missing columns instead of incorrectly saying “provisioned”.

---

#### T-005 — Add an idempotent schema repair migration for existing drifted DBs

**Goal:** Guarantee required columns exist even if old baseline logic already marked broken migrations as applied.

**Why:** You can have a DB where `schema_migrations` says applied, but `invoice_lines.extraction_confidence` or `ai_accounting_proposals.item_id` is missing → WF3 and AI4 break.

**Files touched:**

* `database/migrations/0049_2025_12_23_repair_fc_and_ai4_schema.sql` (new file)

**Add this file (full content):**

```sql
-- Repair missing columns required by:
-- - FirstCard invoice matching (invoice_lines.extraction_confidence, invoice_lines.ocr_source_text)
-- - AI4 accounting proposals (ai_accounting_proposals.item_id)
--
-- This migration is idempotent on MySQL by using information_schema checks + dynamic DDL.

SET @schema := DATABASE();

-- -------------------------------------------------------------------
-- invoice_lines.extraction_confidence
-- -------------------------------------------------------------------
SET @exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema
    AND table_name   = 'invoice_lines'
    AND column_name  = 'extraction_confidence'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE invoice_lines ADD COLUMN extraction_confidence FLOAT NULL COMMENT ''AI extraction confidence for this line'' AFTER match_score',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------------
-- invoice_lines.ocr_source_text
-- -------------------------------------------------------------------
SET @exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema
    AND table_name   = 'invoice_lines'
    AND column_name  = 'ocr_source_text'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE invoice_lines ADD COLUMN ocr_source_text TEXT NULL COMMENT ''Excerpt of OCR text around this transaction'' AFTER extraction_confidence',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- -------------------------------------------------------------------
-- ai_accounting_proposals.item_id
-- -------------------------------------------------------------------
SET @exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @schema
    AND table_name   = 'ai_accounting_proposals'
    AND column_name  = 'item_id'
);
SET @sql := IF(
  @exists = 0,
  'ALTER TABLE ai_accounting_proposals ADD COLUMN item_id VARCHAR(36) NULL AFTER unified_file_id',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
```

**Acceptance criteria:**

* After applying migrations, `SHOW COLUMNS ...` confirms all three columns exist even on previously drifted DBs.

---

#### T-006 — Stop AI4 accounting proposal persistence from failing silently

**Goal:** Ensure schema problems (like missing `item_id`) are visible in logs.

**Why:** `_save_accounting_entries` currently catches `Exception` and returns `False` without logging, hiding the root cause (`backend/src/services/tasks/file_management_tasks.py:683-684`), and another helper does the same (`...:655-656`).

**Files touched:**

* `backend/src/services/tasks/file_management_tasks.py`

**Patch (unified diff):**

```diff
--- a/backend/src/services/tasks/file_management_tasks.py
+++ b/backend/src/services/tasks/file_management_tasks.py
@@ -652,7 +652,9 @@
-    except Exception:
-        return []
+    except Exception as exc:
+        logger.exception("Failed to save ai_accounting_proposals for unified_file_id=%s: %s", unified_file_id, exc)
+        return []
 
@@ -681,7 +683,9 @@
-    except Exception:
-        return False
+    except Exception as exc:
+        logger.exception("Failed to persist ai_accounting_proposals for file_id=%s: %s", file_id, exc)
+        return False
```

**Acceptance criteria:**

* If `ai_accounting_proposals.item_id` is missing, logs clearly show the SQL error instead of silent `False`.

---

### 4) Test & verification plan

#### 4.1 Migration verification

1. Rebuild + restart backend to force migrations:

```powershell
docker compose --profile main up -d --build
docker compose --profile main logs -f ai-api
```

2. Verify columns exist:

```powershell
docker compose --profile main exec mysql mysql -u root -p -e "USE mind2; SHOW COLUMNS FROM invoice_lines LIKE 'extraction_confidence';"
docker compose --profile main exec mysql mysql -u root -p -e "USE mind2; SHOW COLUMNS FROM invoice_lines LIKE 'ocr_source_text';"
docker compose --profile main exec mysql mysql -u root -p -e "USE mind2; SHOW COLUMNS FROM ai_accounting_proposals LIKE 'item_id';"
```

Pass criteria: each query returns exactly one row.

---

#### 4.2 FC import + persistence verification

1. Import an FC PDF via UI (or the upload route), observe returned `invoice_id` (upload response includes `processing_status` at `backend/src/api/reconciliation_firstcard/routes/upload.py:191-202`).

2. Check status endpoint:

* `GET /reconciliation/firstcard/status/<invoice_id>` (route: `backend/src/api/reconciliation_firstcard/routes/status.py:97-118`)

3. Check lines endpoint:

* `GET /reconciliation/firstcard/lines/<invoice_id>` (route: `backend/src/api/reconciliation_firstcard/routes/lines.py:40-63`)

4. Verify DB rows exist:

```powershell
docker compose --profile main exec mysql mysql -u root -p -e "USE mind2; SELECT COUNT(*) AS cnt FROM invoice_lines WHERE invoice_id='<invoice_id>';"
```

**Pass criteria:**

* `cnt > 0`
* Workflow does not end in `READY_FOR_MATCHING` with `cnt = 0`.
* If `cnt = 0`, status is `FAILED` and `metadata.last_error` exists (T-001).

---

#### 4.3 Encoding verification (å/ä/ö end-to-end)

* Confirm new Swedish strings in WF3 stage messages display correctly in the UI log modal (the mojibake strings existed in `workflow_tasks.py` and were corrected by T-001).

---

### 5) Final validation checklist (tick-off)

* [ ] Backend refuses to start if migrations fail (unless `DB_MIGRATIONS_ALLOW_FAILURE=1`).
* [ ] DB has `invoice_lines.extraction_confidence`, `invoice_lines.ocr_source_text`, `ai_accounting_proposals.item_id`.
* [ ] Import FC invoice → `invoice_lines` row count > 0.
* [ ] `metadata.line_counts.total` reflects persisted rows, not AI-extracted count.
* [ ] If persisted rows are 0/mismatched → status becomes `FAILED`, not `READY_FOR_MATCHING`.
* [ ] AI4 proposal persistence failures produce explicit logs (no silent swallow).

---

Patch below:
Save this as e.g. `fix_fc_ai4_fc-lines.patch` (UTF-8) in repo root and apply with:

```powershell
git apply .\fix_fc_ai4_fc-lines.patch
```

```diff
--- a/backend/src/services/tasks/invoice_tasks.py
+++ b/backend/src/services/tasks/invoice_tasks.py
@@ -207,8 +207,13 @@
                     ),
                 )
                 inserted += 1
-    except Exception:
-        return inserted
+    except Exception as exc:
+        logger.exception(
+            "Failed to persist invoice_lines for invoice_id=%s; transaction rolled back: %s",
+            invoice_id,
+            exc,
+        )
+        return 0
     return inserted
 
+def _count_invoice_lines(invoice_id: str) -> int:
+    """Count persisted invoice lines for a credit-card invoice.
+
+    Args:
+        invoice_id: The ``invoice_documents.id`` / ``invoice_lines.invoice_id`` to count.
+
+    Returns:
+        Number of rows in ``invoice_lines`` for this invoice, or 0 if the database is unavailable.
+    """
+    if db_cursor is None:
+        return 0
+    try:
+        with db_cursor() as cur:
+            cur.execute("SELECT COUNT(1) FROM invoice_lines WHERE invoice_id=%s", (invoice_id,))
+            row = cur.fetchone()
+            return int(row[0] or 0) if row else 0
+    except Exception as exc:
+        logger.exception("Failed to count invoice_lines for invoice_id=%s: %s", invoice_id, exc)
+        return 0
+
 
 __all__ = [
     "process_invoice_document",
     "_persist_invoice_lines",
+    "_count_invoice_lines",
     "_to_decimal",
     "_format_date_for_db",
     "_persist_creditcard_invoice_ocr",
     "_persist_creditcard_invoice_main",
     "_persist_creditcard_invoice_items",
 ]
--- a/backend/src/services/tasks/workflow_tasks.py
+++ b/backend/src/services/tasks/workflow_tasks.py
@@ -13,6 +13,7 @@
 from .invoice_tasks import (
     _persist_creditcard_invoice_items,
     _persist_creditcard_invoice_main,
     _persist_creditcard_invoice_ocr,
     _persist_invoice_lines,
+    _count_invoice_lines,
     process_invoice_document,
 )
@@ -860,14 +861,70 @@
     if extraction.header.period_start:
         metadata["period_start"] = extraction.header.period_start.isoformat()
     if extraction.header.period_end:
         metadata["period_end"] = extraction.header.period_end.isoformat()
-    metadata["line_counts"] = {
-        "total": len(extraction.lines),
-        "matched": 0,
-        "unmatched": len(extraction.lines),
-    }
-    metadata["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
-    _update_invoice_metadata(file_id, metadata)
+    extracted_total = len(extraction.lines)
+    persisted_total = _count_invoice_lines(file_id)
+
+    metadata["line_counts"] = {
+        "total": persisted_total,
+        "matched": 0,
+        "unmatched": persisted_total,
+        "extracted_total": extracted_total,
+        "persisted_total": persisted_total,
+        "persist_attempted": inserted_invoice_lines,
+    }
+
+    if extracted_total == 0 or persisted_total == 0 or persisted_total != extracted_total:
+        if extracted_total == 0:
+            reason = "AI6 produced 0 invoice lines; cannot proceed to matching."
+        elif persisted_total == 0:
+            reason = (
+                "Persisted 0 invoice lines although AI6 returned lines. "
+                "This strongly indicates a DB schema mismatch (migrations not applied) or a SQL error."
+            )
+        else:
+            reason = (
+                f"Persisted invoice line count mismatch: extracted={extracted_total}, persisted={persisted_total}. "
+                "Stop-the-line to avoid matching on incomplete data."
+            )
+
+        metadata["processing_status"] = InvoiceProcessingStatus.FAILED.value
+        metadata["last_error"] = {
+            "code": "invoice_lines_persist_failed",
+            "message": reason,
+            "extracted_total": extracted_total,
+            "persisted_total": persisted_total,
+        }
+        _update_invoice_metadata(file_id, metadata)
+
+        fc_coordinator.begin_fc_import_stage(
+            workflow_run_id,
+            "fc_ready",
+            message="Förbereder fakturan för matchning",
+        )
+        fc_coordinator.complete_fc_import_stage(
+            workflow_run_id,
+            "fc_ready",
+            success=False,
+            message=reason,
+        )
+
+        transition_processing_status(
+            file_id,
+            InvoiceProcessingStatus.FAILED,
+            (
+                InvoiceProcessingStatus.AI_PROCESSING,
+                InvoiceProcessingStatus.OCR_PENDING,
+                InvoiceProcessingStatus.OCR_DONE,
+                InvoiceProcessingStatus.READY_FOR_MATCHING,
+                InvoiceProcessingStatus.MATCHING_COMPLETED,
+                InvoiceProcessingStatus.COMPLETED,
+                InvoiceProcessingStatus.FAILED,
+            ),
+        )
+        transition_document_status(
+            file_id,
+            InvoiceDocumentStatus.FAILED,
+            (
+                InvoiceDocumentStatus.IMPORTED,
+                InvoiceDocumentStatus.MATCHING,
+                InvoiceDocumentStatus.MATCHED,
+                InvoiceDocumentStatus.PARTIALLY_MATCHED,
+                InvoiceDocumentStatus.PROCESSING,
+                InvoiceDocumentStatus.COMPLETED,
+                InvoiceDocumentStatus.FAILED,
+            ),
+        )
+        logger.error(
+            "wf3_fc_invoice_lines_persist_failed invoice_id=%s extracted_total=%s persisted_total=%s",
+            file_id,
+            extracted_total,
+            persisted_total,
+        )
+        return workflow_run_id
+
+    metadata["processing_status"] = InvoiceProcessingStatus.READY_FOR_MATCHING.value
+    _update_invoice_metadata(file_id, metadata)
 
     fc_coordinator.begin_fc_import_stage(
         workflow_run_id,
         "fc_ready",
-        message="Förbereder fakturan för matchning",
+        message="Förbereder fakturan för matchning",
     )
     transition_processing_status(
         file_id,
         InvoiceProcessingStatus.READY_FOR_MATCHING,
@@ -894,7 +951,7 @@
     fc_coordinator.complete_fc_import_stage(
         workflow_run_id,
         "fc_ready",
         success=True,
-        message="Fakturan redo för AI5",
+        message="Fakturan redo för AI5",
     )
--- a/backend/src/services/db/migrations.py
+++ b/backend/src/services/db/migrations.py
@@ -116,6 +116,16 @@
     prompt_type = _column_type(cur, "ai_system_prompts", "prompt_content")
     if prompt_type != "mediumtext":
         missing.append("column:ai_system_prompts.prompt_content (expected mediumtext)")
 
+    # Critical columns required by current conversion + matching flows
+    if not _column_exists(cur, "invoice_lines", "extraction_confidence"):
+        missing.append("column:invoice_lines.extraction_confidence")
+    if not _column_exists(cur, "invoice_lines", "ocr_source_text"):
+        missing.append("column:invoice_lines.ocr_source_text")
+
+    if not _column_exists(cur, "ai_accounting_proposals", "item_id"):
+        missing.append("column:ai_accounting_proposals.item_id")
+
     return (len(missing) == 0, missing)
 
+def _normalize_mysql_statement(statement: str) -> str:
+    """Normalize migration SQL for MySQL compatibility.
+
+    The migrations directory historically contains statements like::
+
+        ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...
+
+    MySQL 8 does not support the ``IF NOT EXISTS`` modifier for ``ADD COLUMN``.
+    To keep migration files stable while executing deterministically, the migration
+    runner rewrites this pattern at execution time.
+
+    Args:
+        statement: A single SQL statement (without the trailing semicolon).
+
+    Returns:
+        A statement safe to execute on MySQL.
+    """
+    upper = statement.upper()
+    if upper.startswith("ALTER TABLE") and "ADD COLUMN IF NOT EXISTS" in upper:
+        return re.sub(
+            r"\bADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\b",
+            "ADD COLUMN",
+            statement,
+            flags=re.IGNORECASE,
+        )
+    return statement
+
 def apply_migrations() -> None:
@@ -420,7 +462,8 @@
                 for statement in _iter_sql_statements(sql_text):
                     safe_stmt = _transform_prompt_statement(statement) if prompt_safe_mode else statement
                     if safe_stmt is None:
                         continue
+                    safe_stmt = _normalize_mysql_statement(safe_stmt)
                     cur.execute(safe_stmt)
                     try:
                         cur.fetchall()
                     except Exception:
                         pass
--- a/backend/entrypoint.sh
+++ b/backend/entrypoint.sh
@@ -3,11 +3,17 @@
 # Run database migrations if enabled
 if [ "${DB_AUTO_MIGRATE:-1}" = "1" ]; then
     echo "Running database migrations..."
-    python -c "from services.db.migrations import apply_migrations; apply_migrations()" || {
-        echo "Warning: Database migrations failed, but continuing to start server..."
-        echo "This is expected if migrations have already been applied."
-    }
+    python -c "from services.db.migrations import apply_migrations; apply_migrations()" || {
+        if [ "${DB_MIGRATIONS_ALLOW_FAILURE:-0}" = "1" ]; then
+            echo "Warning: Database migrations failed, but continuing (DB_MIGRATIONS_ALLOW_FAILURE=1)."
+            echo "System behavior may be incorrect until schema is fixed."
+        else
+            echo "ERROR: Database migrations failed. Refusing to start server."
+            echo "Set DB_MIGRATIONS_ALLOW_FAILURE=1 to override (not recommended for production)."
+            exit 1
+        fi
+    }
 else
     echo "Skipping database migrations (DB_AUTO_MIGRATE=0)"
 fi
--- a/backend/src/services/tasks/file_management_tasks.py
+++ b/backend/src/services/tasks/file_management_tasks.py
@@ -707,8 +707,10 @@
                 ))
             return items
-    except Exception:
-        return []
+    except Exception as exc:
+        logger.exception("Failed to load receipt items for file_id=%s: %s", file_id, exc)
+        return []
 
 
 def _save_accounting_en
@@ -807,8 +809,10 @@
                 )
         return True
-    except Exception:
-        return False
+    except Exception as exc:
+        logger.exception("Failed to persist ai_accounting_proposals for file_id=%s: %s", file_id, exc)
+        return False
--- a/database/migrations/0049_2025_12_23_repair_fc_and_ai4_schema.sql
+++ b/database/migrations/0049_2025_12_23_repair_fc_and_ai4_schema.sql
@@ -0,0 +1,76 @@
+-- Repair missing columns required by:
+-- - FirstCard invoice matching (invoice_lines.extraction_confidence, invoice_lines.ocr_source_text)
+-- - AI4 accounting proposals (ai_accounting_proposals.item_id)
+--
+-- This migration is idempotent on MySQL by using information_schema checks + dynamic DDL.
+
+SET @schema := DATABASE();
+
+-- -------------------------------------------------------------------
+-- invoice_lines.extraction_confidence
+-- -------------------------------------------------------------------
+SET @exists := (
+  SELECT COUNT(*)
+  FROM information_schema.columns
+  WHERE table_schema = @schema
+    AND table_name   = 'invoice_lines'
+    AND column_name  = 'extraction_confidence'
+);
+SET @sql := IF(
+  @exists = 0,
+  'ALTER TABLE invoice_lines ADD COLUMN extraction_confidence FLOAT NULL COMMENT ''AI extraction confidence for this line'' AFTER match_score',
+  'SELECT 1'
+);
+PREPARE stmt FROM @sql;
+EXECUTE stmt;
+DEALLOCATE PREPARE stmt;
+
+-- -------------------------------------------------------------------
+-- invoice_lines.ocr_source_text
+-- -------------------------------------------------------------------
+SET @exists := (
+  SELECT COUNT(*)
+  FROM information_schema.columns
+  WHERE table_schema = @schema
+    AND table_name   = 'invoice_lines'
+    AND column_name  = 'ocr_source_text'
+);
+SET @sql := IF(
+  @exists = 0,
+  'ALTER TABLE invoice_lines ADD COLUMN ocr_source_text TEXT NULL COMMENT ''Excerpt of OCR text around this transaction'' AFTER extraction_confidence',
+  'SELECT 1'
+);
+PREPARE stmt FROM @sql;
+EXECUTE stmt;
+DEALLOCATE PREPARE stmt;
+
+-- -------------------------------------------------------------------
+-- ai_accounting_proposals.item_id
+-- -------------------------------------------------------------------
+SET @exists := (
+  SELECT COUNT(*)
+  FROM information_schema.columns
+  WHERE table_schema = @schema
+    AND table_name   = 'ai_accounting_proposals'
+    AND column_name  = 'item_id'
+);
+SET @sql := IF(
+  @exists = 0,
+  'ALTER TABLE ai_accounting_proposals ADD COLUMN item_id VARCHAR(36) NULL AFTER unified_file_id',
+  'SELECT 1'
+);
+PREPARE stmt FROM @sql;
+EXECUTE stmt;
+DEALLOCATE PREPARE stmt;
```
