# Mind - Workflow update

This guide defines a lightweight, production-safe pattern to hard-separate multiple ingest workflows in our backend (e.g., classic receipt flow vs. portal PDF-split flow). The current problem is cross-pollination: tasks from one workflow sometimes run inside another, causing mixed states and brittle debugging. We keep changes minimal and compatible with the existing stack (Celery workers/queues, MySQL, current tables), adding only two small tracking tables plus strict Celery routing and a one-line guard in every task. Each file upload now creates an explicit `workflow_run`, and a dispatcher builds the correct Celery chain based on a clear `workflow_key` (e.g., `WF1_RECEIPT`, `WF2_PDF_SPLIT`). Stages are recorded in a per-run log so we can see progress, timings, and failures at a glance in Adminer/SQL views. The result: clean isolation between workflows, easy observability, and simple recovery—without refactoring the whole codebase.

# AGENT RULES

SYSTEM PROMPT — Workflow-Safe Agent (Strict Scope)

Purpose
You are a backend orchestration agent that executes EXACTLY ONE workflow run at a time in our ingestion system.

Immutable Inputs (MUST be provided by caller)
- workflow_run_id: integer
- expected_workflow_prefix: string (e.g., "WF1_", "WF2_")

Authoritative Sources (read/write)
- READ/WRITE: workflow_runs, workflow_stage_runs
- READ/WRITE as needed: unified_files (+ allowed receipt/invoice tables)
- READ-ONLY: v_workflow_overview, v_workflow_stages
No other tables, files, services, or APIs are in scope.

Hard Rules (Fail Closed)
1) Scope Lock: Operate ONLY on the provided workflow_run_id. Never touch or reference any other run.
2) Workflow Guard: Before any action, fetch workflow_runs.workflow_key and VERIFY it starts with expected_workflow_prefix. If mismatch → STOP immediately, mark stage “skipped” with message “workflow/task mismatch”, and return error.
3) Task Namespace: Invoke only tasks whose names begin with the queue namespace that corresponds to expected_workflow_prefix (e.g., WF1_* → wf1.*, WF2_* → wf2.*). Never call tasks from other namespaces.
4) Stage Logging: For each step, write to workflow_stage_runs:
   - status transitions: queued → running → succeeded/failed/skipped
   - timestamps: started_at / finished_at
   - concise message (≤ 200 chars) with key metrics (e.g., page_count, ocr_ok, match_score).
   Always keep workflow_runs.current_stage/status consistent.
5) Idempotence: Use content_hash + workflow_run_id to avoid duplicate processing. If a step appears already completed, mark “skipped” and continue.
6) Input Sanity: 
   - WF2_* requires mime_type='application/pdf'; otherwise fail with clear message.
   - WF1_* accepts images or PDF (PDF→PNG).
7) Minimal Write Surface: Only update fields required by the current step. Do NOT alter schema, indexes, unrelated rows, or other workflows’ data.
8) No Speculation: If information is missing/ambiguous, STOP and mark the stage “failed” with a clear message requesting the exact missing field. Do not guess.
9) No External Actions: Do not access the internet, external APIs, file systems outside approved storage, or spawn new services.
10) Privacy & Safety: Do not log OCR or full document contents; log only counts, hashes, and short summaries. Never include PII beyond what already exists in the row being processed.

Operational Constraints
- Timeouts: Prefer small, bounded operations; if a step risks long execution, chunk the work (e.g., per-page OCR loops).
- Retries: Only retry idempotent steps and record each retry attempt in the message.
- Concurrency: Assume multiple runs may execute in parallel; never take locks longer than necessary.

Outputs
- On success: Return { "workflow_run_id": <int>, "status": "succeeded", "stage": "<stage_key>" }.
- On controlled stop/failure: Return { "workflow_run_id": <int>, "status": "failed"|"skipped", "stage": "<stage_key>", "reason": "<short_message>" }.

Examples of Out-of-Scope (Must Refuse)
- Modifying other workflow runs or unrelated tables.
- Running tasks with the wrong namespace (e.g., wf2.* inside WF1_*).
- Changing Celery config, creating new queues, altering DB schema.
- Free-form data extraction or accounting beyond the defined stages for this run.

Compliance Reminder
If any rule above cannot be satisfied for the current step, do NOT proceed. Fail closed with a concise, actionable message and leave a proper audit trail in workflow_stage_runs.

## 1) Database: add two tables (plus two optional columns)

**Create a new migration** (or run directly in MySQL/Adminer).

### 1.1 `workflow_runs`

```
CREATE TABLE IF NOT EXISTS workflow_runs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  workflow_key VARCHAR(40) NOT NULL COMMENT 'e.g., WF1_RECEIPT, WF2_PDF_SPLIT',
  source_channel VARCHAR(40) NULL COMMENT 'upload_portal, ftp, api, …',
  file_id VARCHAR(36) NULL COMMENT 'FK to unified_files.id (root file)',
  content_hash VARCHAR(64) NULL,
  current_stage VARCHAR(40) NOT NULL DEFAULT 'queued',
  status ENUM('queued','running','succeeded','failed','canceled') NOT NULL DEFAULT 'queued',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_wfr_workflow (workflow_key),
  KEY idx_wfr_file (file_id),
  KEY idx_wfr_hash (content_hash)
);
```

### 1.2 `workflow_stage_runs`

```
CREATE TABLE IF NOT EXISTS workflow_stage_runs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  workflow_run_id BIGINT NOT NULL,
  stage_key VARCHAR(40) NOT NULL, -- 'pdf_to_png', 'ocr', 'ai1', 'merge_ocr', etc.
  status ENUM('queued','running','succeeded','failed','skipped') NOT NULL DEFAULT 'queued',
  started_at TIMESTAMP NULL,
  finished_at TIMESTAMP NULL,
  message TEXT NULL,
  INDEX idx_wfs_workflow_run (workflow_run_id),
  CONSTRAINT fk_wfs_wfr FOREIGN KEY (workflow_run_id)
    REFERENCES workflow_runs(id) ON DELETE CASCADE
);
```

### 1.3 (Optional but recommended) mirror fields on `unified_files`

```
ALTER TABLE unified_files
  ADD COLUMN ingest_workflow_key VARCHAR(40) NULL AFTER file_type,
  ADD COLUMN ingest_source_channel VARCHAR(40) NULL AFTER ingest_workflow_key;
```

### 1.4 Helpful read-only views

```
CREATE OR REPLACE VIEW v_workflow_overview AS
SELECT
  wfr.id AS workflow_run_id,
  wfr.workflow_key,
  wfr.source_channel,
  wfr.file_id,
  wfr.content_hash,
  wfr.current_stage,
  wfr.status,
  wfr.created_at,
  wfr.updated_at,
  uf.original_filename,
  uf.mime_type,
  uf.file_suffix
FROM workflow_runs wfr
LEFT JOIN unified_files uf ON uf.id = wfr.file_id;

CREATE OR REPLACE VIEW v_workflow_stages AS
SELECT
  wfr.id AS workflow_run_id,
  wfr.workflow_key,
  wfs.stage_key,
  wfs.status,
  wfs.started_at,
  wfs.finished_at,
  TIMESTAMPDIFF(SECOND, wfs.started_at, wfs.finished_at) AS duration_s,
  LEFT(wfs.message, 200) AS message_snippet
FROM workflow_stage_runs wfs
JOIN workflow_runs wfr ON wfr.id = wfs.workflow_run_id
ORDER BY wfr.id DESC, wfs.id ASC;
```

------

## 2) Celery: define queues and routes

### 2.1 Celery config (e.g., `celery_app.py`)

```
from celery import Celery
from kombu import Queue

app = Celery('mind')
app.config_from_object('django.conf:settings', namespace='CELERY')  # or your settings loader

app.conf.task_queues = (
    Queue('wf1', routing_key='wf1.#'),
    Queue('wf2', routing_key='wf2.#'),
)

app.conf.task_routes = {
    'wf1.*': {'queue': 'wf1', 'routing_key': 'wf1.default'},
    'wf2.*': {'queue': 'wf2', 'routing_key': 'wf2.default'},
}
```

> Naming rule: **All** WF1 tasks must be named `wf1.*` (e.g., `wf1.pdf_to_png`), and WF2 tasks `wf2.*`. This alone prevents cross-execution.

### 2.2 Start workers

```
celery -A celery_app worker -Q wf1 -n wf1@%h
celery -A celery_app worker -Q wf2 -n wf2@%h
```

------

## 3) A tiny dispatcher that builds the right chain

### 3.1 Minimal DB helpers (pseudo)

```
def get_workflow_run(db, workflow_run_id):
    # return dict: {id, workflow_key, status, current_stage, file_id, content_hash, ...}
    ...

def mark_stage(db, workflow_run_id, stage_key, status, message=None, start=False, end=False):
    # insert/update workflow_stage_runs and bump workflow_runs.current_stage/status
    ...
```

### 3.2 The dispatcher

```
from celery import chain
from app.celery_app import app
from app import db

def dispatch_workflow(workflow_run_id: int):
    wfr = get_workflow_run(db, workflow_run_id)
    if wfr['workflow_key'] == 'WF1_RECEIPT':
        chain(
            wf1_pdf_to_png.s(workflow_run_id) |
            wf1_ocr.s() |
            wf1_store_db.s() |
            wf1_ai_chain.s() |
            wf1_finalize.s()
        ).apply_async()
    elif wfr['workflow_key'] == 'WF2_PDF_SPLIT':
        chain(
            wf2_pdf_to_png.s(workflow_run_id) |
            wf2_split_pages.s() |
            wf2_ocr_each_png.s() |
            wf2_merge_ocr_text.s() |
            wf2_store_db.s() |
            wf2_ai_analysis.s() |
            wf2_match_existing_receipts.s() |
            wf2_finalize.s()
        ).apply_async()
    else:
        raise ValueError(f"Unknown workflow_key: {wfr['workflow_key']}")
```

> Each task **must** accept `workflow_run_id` as first arg and return the same (plus any needed payload) to the next task.

------

## 4) One-line guard in every task (critical)

### 4.1 Guard helper

```
def ensure_workflow(db, workflow_run_id, expected_prefix: str):
    wfr = get_workflow_run(db, workflow_run_id)
    if not wfr['workflow_key'].startswith(expected_prefix):
        # soft-fail with a clear log + stage mark
        mark_stage(db, workflow_run_id, stage_key='guard', status='skipped',
                   message=f"Task belongs to {expected_prefix} but workflow_key is {wfr['workflow_key']}")
        raise RuntimeError("Workflow/task mismatch")
    return wfr
```

### 4.2 Use guard at the top of each task

```
@app.task(name='wf2.pdf_to_png')
def wf2_pdf_to_png(workflow_run_id: int, *args, **kwargs):
    ensure_workflow(db, workflow_run_id, expected_prefix='WF2_')
    mark_stage(db, workflow_run_id, 'pdf_to_png', 'running', start=True)

    # ... do the work ...

    mark_stage(db, workflow_run_id, 'pdf_to_png', 'succeeded', end=True)
    return workflow_run_id  # keep passing it forward
```

> Do this for *all* `wf1.*` and `wf2.*` tasks.
>  Effect: even if something is misrouted, it will refuse to run and leave an audit trail.

------

## 5) Upload endpoints: create a workflow_run first

### 5.1 Intake (simplified)

- When a file arrives, **before** enqueuing any tasks:
  1. Create `unified_files` row as you already do (with `content_hash`).
  2. Insert a row in `workflow_runs`:
     - `workflow_key`:
       - Classic flow: `WF1_RECEIPT`
       - Portal PDF split: `WF2_PDF_SPLIT`
     - `source_channel`: `upload_portal`, `ftp`, or `api`
     - `file_id`: the `unified_files.id`
     - `content_hash`: the same hash as the file
  3. (Optional) Mirror `ingest_workflow_key` and `ingest_source_channel` into `unified_files`.
  4. Call `dispatch_workflow(workflow_run_id)`.

**Example SQL (insert):**

```
INSERT INTO workflow_runs (workflow_key, source_channel, file_id, content_hash, current_stage, status)
VALUES ('WF2_PDF_SPLIT', 'upload_portal', '<unified_files.id>', '<hash>', 'queued', 'queued');
```

------

## 6) Lightweight idempotence

- If desired, add a UNIQUE index to `workflow_runs(workflow_key, content_hash)` to avoid duplicate runs for the same workflow and file content:

```
ALTER TABLE workflow_runs
  ADD UNIQUE KEY uniq_wfkey_contenthash (workflow_key, content_hash);
```

------

## 7) Pre-checks (nice and tiny)

- At the first task per workflow:
  - **WF2_PDF_SPLIT**: verify `mime_type='application/pdf'`. If not, fail the stage with a helpful message and stop.
  - **WF1_RECEIPT**: allow images or pdf; if pdf, proceed with pdf→png.

------

## 8) Logging & observability (minimal)

- On each task transition, call `mark_stage(...)`.
- Keep messages short and actionable (e.g., “OCR count=7 pages; 0 failed”).