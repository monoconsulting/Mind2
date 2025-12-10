Bra, då kör vi “operation fixa state-maskinen” 😊

Jag gör två saker nu:

1. Förklarar **exakt vad som ska implementeras** för att bli av med `current=missing`–varningarna och göra AI-felen hanterbara.
2. Ger dig en **stenhård agent-instruktion på engelska** + SoT-uppdateringar och några SQL-snuttar för datastädning.

---

## 1. Vad loggen betyder – fokus för fixen

Vi har redan sett:

* `Illegal transition for processing_status … current=missing target=ocr_done/ai_processing/ready_for_matching`
* `Illegal transition for status … current=missing target=matching`
* `matching.invoice_state.refresh_failed … reason="line_count_query_failed"`
* OpenAI 500 → pipeline försöker ändå vidare till `ai_processing`.

Det här kommer från:

```python
# services/invoice_status.py
def _record_illegal(entity: str, object_id: str, target: str) -> None:
    current_value = "missing"
    ...
        query = f"SELECT {column} FROM invoice_documents WHERE id=%s"
        ...
        row = cur.fetchone()
        if row:
            current_value = row[0] or "null"
    ...
    logger.warning(
        "Illegal transition for %s id=%s: current=%s target=%s", entity, object_id, current_value, target
    )
```

`current=missing` betyder: **det finns ingen rad i `invoice_documents` med det här id:t**.
Ändå kör någon:

```python
transition_processing_status(invoice_id, InvoiceProcessingStatus.OCR_DONE, ...)
transition_processing_status(invoice_id, InvoiceProcessingStatus.AI_PROCESSING, ...)
...
```

Den logik som triggar detta är bl.a.:

```python
# services/tasks/file_management_tasks.py
def _maybe_advance_invoice_from_file(file_id: str, success: bool) -> None:
    invoice_id = _get_invoice_parent_id(file_id)
    ...
    transition_processing_status(invoice_id, next_state, allowed_states)
    if should_schedule and _enqueue_invoice_document(invoice_id):
        ...
```

och FirstCard-koordinatorn:

```python
# api/reconciliation_firstcard/services/workflow_coordinator.py
def start_processing(self, invoice_id: str) -> bool:
    success = transition_processing_status(
        invoice_id,
        InvoiceProcessingStatus.OCR_PENDING,
        (InvoiceProcessingStatus.UPLOADED,),
    )
```

→ **Om `invoice_documents`-raden aldrig skapats (eller raderats) för just det `invoice_id` → `current=missing`.**

Dessutom: när OpenAI ger 500 fortsätter pipeline ändå försöka sätta `ai_processing` → då blir det dubbelt fel: provider-fel + illegal transition.

---

## 2. Nästa steg: vad vi vill uppnå

Vi vill:

1. **Aldrig ha “nakna” invoice_ids utan rad i `invoice_documents`.**
   Antingen:

   * skapa raden tidigt (upload/JSON-import), eller
   * ha en definierad “self-healing”/fail-fast när den saknas.

2. **Hantering av OpenAI 500**:

   * markera dokumentet som ett definierat fel–läge (`FAILED`/`ai_failed`) enligt SoT,
   * inte försöka hoppa vidare i state-maskinen till `ai_processing` om provider-svaret är 500.

3. **Dokumentera detta i SoT** så agenten får ett tydligt facit.

Nedan är en **agent-instruktion** som du kan mata direkt till din kod-agent.

---

## 3. Agent instruction (English, no deviation allowed)

> 🔧 **SYSTEM / AGENT PROMPT – DO NOT DEVIATE**

You must follow every instruction below exactly.
You are not allowed to skip, modify, or reinterpret any step.

### 3.1 Goal

Eliminate `current=missing` illegal transitions and make AI provider failures (e.g. OpenAI 500) safe and SoT-compliant by:

1. Guaranteeing that every invoice id used in the invoice state machine has a corresponding row in `invoice_documents`.
2. Handling missing `invoice_documents` rows in a deterministic way (either self-healing or fail-fast).
3. Ensuring AI provider 500 errors result in a controlled failure state and do not attempt illegal invoice state transitions.
4. Updating the Source of Truth (SoT) sections to document these rules.

You may **only** change the files listed below:

* `backend/src/api/reconciliation_firstcard/utils/db_helpers.py`
* `backend/src/api/reconciliation_firstcard/routes/upload.py`
* `backend/src/api/reconciliation_firstcard/services/workflow_coordinator.py`
* `backend/src/services/tasks/file_management_tasks.py`
* `backend/src/services/invoice_status.py`
* `backend/src/services/ai_service.py` (or the equivalent central AI orchestration module)
* SoT files:

  * `docs/source_of_truth/30_STATUS_MODEL.md`
  * `docs/source_of_truth/50_PIPELINES_AND_JOBS.md`
  * `docs/source_of_truth/80_OPERATIONS_RUNBOOK.md`

No other files may be modified.

---

### 3.2 Step 1 – Add a safe “ensure invoice document” helper

**File:** `backend/src/api/reconciliation_firstcard/utils/db_helpers.py`

1. Implement a function:

```python
def ensure_invoice_document(
    invoice_id: str,
    invoice_type: str = "credit_card_invoice",
) -> bool:
    """
    Ensure that an invoice_documents row exists for the given invoice_id.

    Behaviour:
    - If a row exists (including soft-deleted), return True.
    - If no row exists, create a minimal, SoT-compliant document row:
        * id = invoice_id
        * invoice_type = invoice_type
        * status = InvoiceDocumentStatus.IMPORTED.value
        * processing_status = InvoiceProcessingStatus.UPLOADED.value
        * metadata_json contains at least:
            - {"recovered_from_missing_invoice_document": true}
    - If creation fails, log an error and return False.
    """
```

2. Use the existing helper `_create_invoice_document` internally.
   You must not duplicate insert SQL.

3. If `invoice_documents_supports_updated_at()` is false, ensure `metadata_json` still gets a proper `last_progress_at` field (reusing the existing logic from `_create_invoice_document`).

4. The function must be idempotent:

   * If `invoice_documents` already contains the row (even with `deleted_at` set), do **not** create a duplicate.
   * Only insert when no row exists at all.

---

### 3.3 Step 2 – Call `ensure_invoice_document` before state transitions

You must guarantee that any use of `transition_processing_status` or `transition_document_status` for credit-card invoices is preceded by `ensure_invoice_document`.

#### 3.3.1 FirstCard upload path

**File:** `backend/src/api/reconciliation_firstcard/routes/upload.py`

In the upload handler where you currently do:

```python
create_invoice_document(
    invoice_id=invoice_id,
    invoice_type="credit_card_invoice",
    status=InvoiceDocumentStatus.IMPORTED.value,
    metadata=metadata,
    processing_status=metadata.get("processing_status"),
)
```

You must:

1. Keep this call as is (it is the primary, SoT-correct path).
2. Immediately after it, call:

```python
ensure_invoice_document(invoice_id=invoice_id, invoice_type="credit_card_invoice")
```

This guarantees that even if `create_invoice_document` is changed or fails partially in the future, the invariants are enforced.

#### 3.3.2 FirstCard workflow coordinator

**File:** `backend/src/api/reconciliation_firstcard/services/workflow_coordinator.py`

For the methods that call `transition_processing_status`, you must ensure they call `ensure_invoice_document` first:

* `start_processing(self, invoice_id: str) -> bool`
* Any method that transitions to:

  * `OCR_PENDING`
  * `OCR_DONE`
  * `AI_PROCESSING`
  * `READY_FOR_MATCHING`
  * `MATCHING_COMPLETED`
  * `COMPLETED` / `FAILED`

**For each such method:**

1. At the very start of the method, before the first `transition_processing_status(...)` call, insert:

```python
from api.reconciliation_firstcard.utils.db_helpers import ensure_invoice_document

if not ensure_invoice_document(invoice_id, invoice_type="credit_card_invoice"):
    logger.error("Cannot start or advance workflow for %s: invoice_documents row missing and cannot be created", invoice_id)
    return False
```

2. Do not introduce new invoice types. Always use `"credit_card_invoice"` for FirstCard.

#### 3.3.3 File->invoice pipeline (`_maybe_advance_invoice_from_file`)

**File:** `backend/src/services/tasks/file_management_tasks.py`

In:

```python
def _maybe_advance_invoice_from_file(file_id: str, success: bool) -> None:
    invoice_id = _get_invoice_parent_id(file_id)
    ...
    _update_invoice_metadata(invoice_id, metadata)
    transition_processing_status(invoice_id, next_state, allowed_states)
    if should_schedule and _enqueue_invoice_document(invoice_id):
        ...
```

You must:

1. Import `ensure_invoice_document` at the top of the file (via the same module as above).
2. Before `transition_processing_status(...)`, insert:

```python
if not ensure_invoice_document(invoice_id, invoice_type="credit_card_invoice"):
    logger.error(
        "Skipping invoice state advance for %s (file %s): missing invoice_documents row",
        invoice_id,
        file_id,
    )
    return
```

3. Do not change the logic that computes `next_state`, `allowed_states`, or `should_schedule`.

This ensures that if a file refers to an invoice that does not exist in `invoice_documents`, the pipeline fails fast and does not spam illegal transitions.

---

### 3.4 Step 3 – Improve `_record_illegal` observability (no logic change)

**File:** `backend/src/services/invoice_status.py`

In `_record_illegal(...)`:

1. Extend the logging payload to include whether the invoice document exists or not.

   Example:

```python
exists_flag = False
...
    if db_cursor is not None:
        ...
            cur.execute(query, params)
            row = cur.fetchone()
        if row:
            current_value = row[0] or "null"
            exists_flag = True
...
logger.warning(
    "Illegal transition for %s id=%s: current=%s target=%s exists=%s",
    entity,
    object_id,
    current_value,
    target,
    exists_flag,
)
```

2. You must not change the semantics of the function.
   It still logs, records metrics, and returns nothing.
   This is purely to help operations distinguish “missing row” from “invalid state”.

---

### 3.5 Step 4 – Handle AI provider 500 errors safely

**File:** `backend/src/services/ai_service.py` (already referenced in logs: `_provider_generate`)

You must:

1. In `_provider_generate(...)`, when catching provider exceptions like:

```python
except RuntimeError as exc:
    # currently logs "Provider call for document_analysis failed ..."
```

add a clear signal back to the caller that the AI step has **hard-failed** for this document, e.g.:

```python
raise AiProviderError("provider_failed", str(exc))
```

where `AiProviderError` is a small, typed exception you define in this module.

2. In any workflow / task that drives invoice AI steps and calls `_provider_generate` (e.g. in `wf3_firstcard_invoice` or `creditcard_tasks`):

   * Catch `AiProviderError`.
   * When caught:

     * Call `_fail_invoice_processing(invoice_id, error_message=...)` (the helper in `file_management_tasks.py`) or an equivalent existing helper that:

       * transitions `processing_status` to `FAILED` using `transition_processing_status`,
       * transitions `status` to a failure state (`FAILED` or `MANUAL_REVIEW` according to SoT),
       * logs error in history.
     * Do **not** call `transition_processing_status` to `AI_PROCESSING` or beyond after a provider failure.
     * Exit the task cleanly.

3. Do not introduce any new `processing_status` or `status` values. Use existing SoT enums only.

Result:

* A 500 from OpenAI turns till a clean “AI failed” state in your DB.
* You no longer see illegal transitions like `missing → ai_processing` for those invoices.

---

### 3.6 Step 5 – Data repair query (one-off, not in app code)

You must prepare a SQL repair script (not executed by the application, only by an operator) that identifies existing “naked” invoices and either:

* creates `invoice_documents` rows via `_create_invoice_document`, or
* marks them for manual review.

Design the script as follows (to be documented in SoT):

1. Find invoice ids that appear in `invoice_lines` but not in `invoice_documents`:

```sql
SELECT il.invoice_id
FROM invoice_lines il
LEFT JOIN invoice_documents d ON d.id = il.invoice_id
WHERE d.id IS NULL
GROUP BY il.invoice_id;
```

2. For each such id, call `ensure_invoice_document(invoice_id, 'credit_card_invoice')` via a small admin script (Python management command) that uses the same helper you just wrote.

3. Do not delete any data in this script.

You must document this in `80_OPERATIONS_RUNBOOK.md` as an “Invoice State Repair Procedure”.

---

### 3.7 Step 6 – SoT updates

You must update the SoT with the following content.

#### 3.7.1 30_STATUS_MODEL.md – Invoice Document Invariants

Add:

```markdown
### Invoice Document Integrity

For every invoice that participates in the invoice state machine, the following
must always hold:

- There MUST be exactly one row in `invoice_documents` with `id = invoice_id`.
- All calls to `transition_processing_status` and `transition_document_status`
  MUST only be made for invoice ids that have a corresponding
  `invoice_documents` row.

To enforce this, application code MUST call a central helper
(e.g. `ensure_invoice_document(...)`) before performing any state transitions.
If the helper cannot create or confirm the `invoice_documents` row, the
pipeline MUST fail fast and record an error, instead of performing any
transitions.
```

And under `InvoiceProcessingStatus` rules:

```markdown
Illegal transitions from a missing document:

If the state machine receives a request to transition an invoice id that does
not exist in `invoice_documents`, this MUST be treated as a data integrity
issue. The implementation MUST:

- Log an "illegal transition" event with `current=missing`.
- NOT create any new invoice state rows implicitly (unless explicitly defined
  as a recovery operation).
- Provide a separate operator-level repair procedure in the runbook to fix or
  recreate the missing `invoice_documents` rows.
```

#### 3.7.2 50_PIPELINES_AND_JOBS.md – AI Failure Behaviour

Add:

```markdown
### AI Provider Failures (e.g. OpenAI 500)

When an external AI provider returns a 5xx error or equivalent hard failure
during invoice processing:

- The pipeline MUST NOT transition the invoice to `AI_PROCESSING` or any later
  processing status.
- Instead, the invoice MUST transition to a failure state using the standard
  helper (e.g. `_fail_invoice_processing(...)`), which sets:

  - `invoice_documents.processing_status = FAILED`
  - `invoice_documents.status = FAILED` or `MANUAL_REVIEW` (depending on
    product requirements)

- The failure MUST be logged in the invoice history with enough detail to
  support later reprocessing.

Reprocessing (via queue resume or batch resume) is allowed and MUST perform
a fresh AI call and a new state transition sequence.
```

#### 3.7.3 80_OPERATIONS_RUNBOOK.md – Invoice State Repair Procedure

Add:

````markdown
### Invoice State Repair Procedure (Missing invoice_documents)

Symptom:
- Logs contain repeated warnings of the form:
  "Illegal transition for processing_status id=<uuid>: current=missing target=<state>"

Cause:
- The application attempted to transition an invoice that has no corresponding
  row in `invoice_documents`.

Repair steps:

1. Identify affected invoices:

   ```sql
   SELECT il.invoice_id
   FROM invoice_lines il
   LEFT JOIN invoice_documents d ON d.id = il.invoice_id
   WHERE d.id IS NULL
   GROUP BY il.invoice_id;
````

2. For each invoice_id in the result set, run the admin script that calls
   `ensure_invoice_document(invoice_id, 'credit_card_invoice')`. This will
   create a minimal `invoice_documents` row with:

   * `status = IMPORTED`
   * `processing_status = UPLOADED`
   * `metadata_json.recovered_from_missing_invoice_document = true`

3. After recovery, re-run the relevant workflows using the existing
   resume/batch-resume mechanisms.

4. If recovery fails for any invoice (e.g. referential integrity issues),
   escalate as a data-quality incident and handle manually.

```

---

### 3.8 Step 7 – Tests you MUST run

Before you consider your work done, you must run these tests:

1. **New upload → no “missing” transitions**
   - Upload a new FirstCard invoice via the normal endpoint.
   - Confirm:
     - `invoice_documents` row exists.
     - `transition_processing_status` moves from `UPLOADED` → `OCR_PENDING` → `OCR_DONE` → `AI_PROCESSING` → `READY_FOR_MATCHING` etc. without any `current=missing` logs.

2. **Existing bad invoice → repaired**
   - Pick one of the problematic invoice ids from the logs (e.g. `15a314e7-82ce-49fd-8bae-af44bcc27ddb`).
   - Run the repair procedure (`ensure_invoice_document` via admin script).
   - Re-run workflow / resume from queue.
   - Confirm that `Illegal transition ... current=missing` no longer appears for that id.

3. **AI 500 handling**
   - Simulate a provider 500 (e.g. by forcing `_provider_generate` to raise `AiProviderError`).
   - Confirm:
     - `invoice_documents.processing_status = FAILED`
     - `invoice_documents.status` matches SoT (FAILED or MANUAL_REVIEW).
     - No `transition_processing_status(..., AI_PROCESSING, ...)` is called after the failure.
     - No `current=missing target=ai_processing` logs appear.

Only after all these tests pass, you may consider the task complete.

> **End of agent instruction.**

---

