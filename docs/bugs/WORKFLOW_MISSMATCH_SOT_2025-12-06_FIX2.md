🔧 AGENT INSTRUCTION – FIX AI ERROR HANDLING TO USE invoice_id (NOT file_id)

You must follow these instructions exactly.
You are not allowed to modify anything outside the scope defined here.

1. Scope and allowed files

You may only modify:

backend/src/services/tasks/workflow_tasks.py

No other file is allowed to be edited.

Your task is to correct the AiProviderError handling in the WF3 FirstCard workflow so that:

All invoice state transitions (transition_processing_status, transition_document_status, _fail_invoice_processing) operate on invoice_id, not file_id.

No state transition is ever invoked with a file_id as the identifier for the invoice state machine.

2. Target function

In backend/src/services/tasks/workflow_tasks.py, locate the WF3 FirstCard task function.

It is named:

wf3_firstcard_invoice


Inside this function there is a try/except AiProviderError block around the AI parsing step (AI6 / fc_parse).

The problematic code is inside the except AiProviderError branch, where:

transition_processing_status(...)

transition_document_status(...)

_fail_invoice_processing(...)

are called with file_id as the identifier argument.

You must correct this.

3. Step-by-step changes
3.1 Identify the correct invoice_id in this function

In wf3_firstcard_invoice, find the variable that represents the credit card invoice id for this workflow.

It is typically:

passed into the function as a parameter, or

retrieved near the beginning from the workflow metadata / FirstCard coordinator, or

stored in a clearly named variable such as invoice_id, creditcard_invoice_id or similar.

You must use this invoice id as the canonical identifier for:

transition_processing_status

transition_document_status

_fail_invoice_processing

Do not derive the invoice id from the file_id.
Do not introduce any new mapping logic (no extra queries or helper functions).
Use the same invoice_id that the rest of WF3 uses for state transitions.

If the function currently does not keep an invoice_id variable in scope through the AI step and into the except AiProviderError block, you must:

Thread the existing invoice_id variable down into that block (e.g. by keeping it in the outer function scope).

Do not introduce any new parameters to the Celery task signature.

3.2 Replace all file_id-based transitions with invoice_id

Inside the except AiProviderError as exc: block in wf3_firstcard_invoice:

Find this code (or equivalent):

transition_processing_status(
    file_id,
    InvoiceProcessingStatus.FAILED,
    (
        InvoiceProcessingStatus.AI_PROCESSING,
        InvoiceProcessingStatus.OCR_DONE,
        InvoiceProcessingStatus.OCR_PENDING,
    ),
)

transition_document_status(
    file_id,
    InvoiceDocumentStatus.FAILED,
    (
        InvoiceDocumentStatus.IMPORTED,
        InvoiceDocumentStatus.MATCHING,
    ),
)

_fail_invoice_processing(file_id, f"AI6 provider failed: {exc}")


Replace the identifier argument file_id in all three calls with the correct invoice_id variable you identified in step 3.1.

After your change, it must look conceptually like this:

transition_processing_status(
    invoice_id,
    InvoiceProcessingStatus.FAILED,
    (
        InvoiceProcessingStatus.AI_PROCESSING,
        InvoiceProcessingStatus.OCR_DONE,
        InvoiceProcessingStatus.OCR_PENDING,
    ),
)

transition_document_status(
    invoice_id,
    InvoiceDocumentStatus.FAILED,
    (
        InvoiceDocumentStatus.IMPORTED,
        InvoiceDocumentStatus.MATCHING,
    ),
)

_fail_invoice_processing(invoice_id, f"AI6 provider failed: {exc}")


The only change is the identifier: invoice_id instead of file_id.
Do not modify the allowed state tuples, enums, or message text.

Keep the surrounding calls to:

fc_coordinator.complete_fc_import_stage(..., success=False, ...)

log_finalize_failure(...)

return workflow_run_id

exactly as they are.
You must not change the workflow stage behavior.

4. No new logic, no new enums, no new queries

You must NOT:

Add new enums or status values.

Add new database queries to map file_id → invoice_id.

Change _fail_invoice_processing implementation.

Change any other parts of wf3_firstcard_invoice that are unrelated to this identifier swap.

Touch any other workflows (WF1, WF2) or tasks.

You must ONLY:

Ensure that all invoice state transitions in the AiProviderError branch of wf3_firstcard_invoice use the correct invoice_id.

5. Mandatory verification

Before you consider your work done, you must self-verify:

Static check

Search in workflow_tasks.py for:

transition_processing_status( inside wf3_firstcard_invoice.

transition_document_status( inside wf3_firstcard_invoice.

_fail_invoice_processing( inside wf3_firstcard_invoice.

Confirm that none of these calls use file_id as the identifier argument.

All must use invoice_id.

Runtime sanity check (manual reasoning)

With a failing AI provider (e.g. simulated AiProviderError), the expected behavior is:

invoice_documents row for this invoice id has:

processing_status = FAILED

status = FAILED or MANUAL_REVIEW (according to SoT and _fail_invoice_processing).

No “Illegal transition … current=missing … target=ai_processing/failed” log lines appear for any file_id.

You must not mark this task as complete until these conditions are satisfied.

End of agent instruction.