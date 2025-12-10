🔧 AGENT INSTRUCTION — DO NOT DEVIATE

You must follow every instruction in this document with 100% accuracy.
You are not allowed to alter, reinterpret, soften, modify, or skip any part.
This is an execution order, not a suggestion.

SECTION 1 — OBJECTIVE

You must correct the workflow implementation so that:

WF3 (FirstCard Invoice Workflow) correctly updates
workflow_runs.status to "succeeded" when the workflow finishes successfully.

Queue diagnostics (Queue API + Queue page) must become aligned with the Source of Truth (SoT), including:

Consistent definition of orphan file

Correct filtering of ai_status

Clear separation of active workflows vs historical completed workflows

SoT-aligned representation of stalled

Batch resume functionality must be implemented exactly as specified, including:

New API endpoint for batch resume

Updated Queue UI with checkboxes

Backend logic that performs standard per-file resume for each selected ID

You may only modify code that directly implements these requirements.
No other part of the codebase may be touched.

SECTION 2 — MANDATORY FIXES FOR WF3
WF3 must update workflow_runs.status to “succeeded”

At the end of the workflow (after KLAR/finalize_ok), you must:

Set:

UPDATE workflow_runs
SET status = 'succeeded',
    current_stage = 'KLAR'
WHERE id = :workflow_run_id;


Ensure unified_files.ai_status reflects "completed" exactly as defined in SoT.

Ensure that the status transition is executed after the final stage is completed and logged.

You may not add new status values.
You may not introduce new workflow states.

SECTION 3 — QUEUE / ORPHAN ALIGNMENT
Correct orphan detection

Modify Queue API logic so that an “orphan file” is defined as:

A row in unified_files that has no corresponding entry in workflow_runs
AND whose ai_status is one of the allowed SoT starting statuses.

The allowed ai_status values for orphan detection are:

uploaded
processing
ocr_done
ocr_failed
manual_review


Remove the legacy values:

queued
running


They do not exist in SoT and must never be used for filtering again.

Clarify workflow visibility

Queue API must return:

ACTIVE workflows only:

status = running

status = queued

ORPHANS

as defined above

STALLED workflows

running for longer than stall_threshold

The Queue API must NOT include completed workflows (succeeded) or permanently failed workflows (failed).
These belong in the workflow history, not in the queue.

Stalled flag

Stalled = a workflow where:

workflow_runs.status = 'running'
AND idle_seconds > stall_threshold


No new state value may be created in the database.

SECTION 4 — BATCH RESUME IMPLEMENTATION

You must add:

Backend

Create a new endpoint:

POST /queue/resume-batch
Body: { "file_ids": [<int>, <int>, ...] }


For each file_id:

Call the existing resume handler:

POST /ai/api/ingest/process/<file_id>/resume


Collect results and return in a structured JSON array.

No new workflow logic may be introduced.
Only reuse the existing resume logic.

Frontend

Modify Queue.jsx:

Add a checkbox in each row:

Only for rows where canResume === true

Add a “Select all orphan” checkbox

Add a “Resume selected” button

When clicked, POST the list of selected file_ids to /queue/resume-batch

No other UI elements may be altered.

SECTION 5 — SECURITY AND SAFETY RULES

You must not:

Change any other workflows (WF1, WF2)

Add new workflow stages

Introduce new enum values

Modify database schemas

Change unrelated endpoints

Change unrelated UI pages

Change any SoT documents not listed below

SECTION 6 — MANDATORY TESTS BEFORE COMPLETION

You must self-execute all tests below before declaring success:

WF3 tests

Create a controlled FC invoice test file.

Run WF3.

Confirm:

workflow_runs.status = succeeded

workflow_runs.current_stage = KLAR

unified_files.ai_status = completed

Queue tests

Verify:

No completed workflows appear in queue.

Orphan files with valid ai_status appear.

Orphan files with invalid legacy ai_status do NOT appear.

Stalled logic works.

Batch resume tests

Select multiple orphans

Resume all

Confirm:

Correct workflows created

No duplicate workflows generated

No unexpected workflow types created

Only after all conditions above are fulfilled may you finalize your task.

SECTION 7 — ABSOLUTE COMPLIANCE

These orders override:

previous instructions

inferred intentions

agent judgment

agent optimization attempts

You must follow the instructions exactly.

END OF AGENT INSTRUCTION
✅ 2. SoT Updates (Authoritative, Versioned)

Below are the required additions/updates to the Source of Truth.
Each block can be inserted directly into the relevant SoT files.

Update 1 — 30_STATUS_MODEL.md
Add under “workflow_runs.status”:
The following rule is mandatory:

Every workflow MUST set workflow_runs.status to "succeeded" after the final
stage ("finalize_ok" or "KLAR") completes successfully.

No workflow is allowed to remain in status "running" after successful completion.

Update 2 — Add new section: "Orphan Files"

Add to 30_STATUS_MODEL.md:

### Definition: Orphan File

An orphan file is a row in unified_files that has no matching row in workflow_runs
AND whose ai_status is one of the valid starting statuses:

- uploaded
- processing
- ocr_done
- ocr_failed
- manual_review

Legacy values such as "queued" or "running" are invalid and must be migrated or ignored.

Update 3 — Add new section: "Queue Behavior"

Add to 50_PIPELINES_AND_JOBS.md:

### Queue View (Diagnostics)

The queue view must show only:
1. Active workflows (status = running or queued)
2. Orphan files (as defined in STATUS_MODEL)
3. Stalled workflows (running AND idle_seconds > stall_threshold)

Completed (succeeded) and permanently failed workflows must NOT appear in the queue.
They belong in the workflow history view.

Update 4 — Add new section: "Batch Resume"

Add to 80_OPERATIONS_RUNBOOK.md:

### Batch Resume Operation

The system must provide an endpoint to resume multiple workflow items:

POST /queue/resume-batch

Payload:
{
    "file_ids": [int, int, ...]
}

Each file_id must be resumed using the standard single-file resume API:
POST /ai/api/ingest/process/<file_id>/resume

No new workflow mechanics are allowed.
Only existing logic must be reused.

Update 5 — Document “Stalled”

Add to 30_STATUS_MODEL.md:

### Stalled Condition (UI only)

A workflow is considered stalled if:
- workflow_runs.status = "running", AND
- idle_seconds > stall_threshold

Stalled is NOT a database status.
It is a UI diagnostic flag only.