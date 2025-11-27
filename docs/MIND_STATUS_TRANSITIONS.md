# Mind2 Status Transitions

**Version:** 1.0
**Date:** 2025-11-27
**Source:** `backend/src/services/invoice_status.py` & `backend/src/services/status_constants.py`

This document defines the allowed state transitions for invoice processing entities. These transitions are enforced by the backend state machine helpers.

## 1. Invoice Processing Status (`invoice_documents.processing_status`)

Tracks the technical processing pipeline.

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> UPLOADED
    UPLOADED --> OCR_PENDING
    UPLOADED --> READY_FOR_MATCHING : Manual/JSON Import
    UPLOADED --> FAILED

    OCR_PENDING --> OCR_DONE
    OCR_PENDING --> FAILED

    OCR_DONE --> AI_PROCESSING
    OCR_DONE --> READY_FOR_MATCHING : Skip AI
    OCR_DONE --> FAILED

    AI_PROCESSING --> READY_FOR_MATCHING
    AI_PROCESSING --> FAILED

    READY_FOR_MATCHING --> MATCHING_COMPLETED
    READY_FOR_MATCHING --> FAILED

    MATCHING_COMPLETED --> COMPLETED

    COMPLETED --> [*]
    FAILED --> [*]
```

### Allowed Transitions

| Current State | Allowed Next States |
| :--- | :--- |
| `uploaded` | `ocr_pending`, `ready_for_matching`, `failed` |
| `ocr_pending` | `ocr_done`, `failed` |
| `ocr_done` | `ai_processing`, `ready_for_matching`, `failed` |
| `ai_processing` | `ready_for_matching`, `failed` |
| `ready_for_matching` | `matching_completed`, `failed` |
| `matching_completed` | `completed` |
| `completed` | *(none)* |
| `failed` | *(none)* |

---

## 2. Invoice Document Status (`invoice_documents.status`)

Tracks the business-facing lifecycle state.

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> IMPORTED
    IMPORTED --> MATCHING
    IMPORTED --> MATCHED
    IMPORTED --> PARTIALLY_MATCHED
    IMPORTED --> FAILED

    MATCHING --> MATCHED
    MATCHING --> PARTIALLY_MATCHED
    MATCHING --> FAILED

    MATCHED --> COMPLETED
    MATCHED --> PARTIALLY_MATCHED

    PARTIALLY_MATCHED --> MATCHED
    PARTIALLY_MATCHED --> COMPLETED
    PARTIALLY_MATCHED --> FAILED

    PROCESSING --> MATCHING
    PROCESSING --> FAILED

    COMPLETED --> [*]
    FAILED --> [*]
```

### Allowed Transitions

| Current State | Allowed Next States |
| :--- | :--- |
| `imported` | `matching`, `matched`, `partially_matched`, `failed` |
| `matching` | `matched`, `partially_matched`, `failed` |
| `matched` | `completed`, `partially_matched` |
| `partially_matched` | `matched`, `completed`, `failed` |
| `processing` | `matching`, `failed` |
| `completed` | *(none)* |
| `failed` | *(none)* |

---

## 3. Invoice Line Match Status (`invoice_lines.match_status`)

Tracks the reconciliation status of individual invoice lines.

### State Diagram

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> AUTO
    PENDING --> MANUAL
    PENDING --> UNMATCHED
    PENDING --> IGNORED

    AUTO --> MANUAL
    AUTO --> CONFIRMED
    AUTO --> UNMATCHED

    MANUAL --> CONFIRMED
    MANUAL --> UNMATCHED

    UNMATCHED --> MANUAL
    IGNORED --> MANUAL

    CONFIRMED --> [*]
```

### Allowed Transitions

| Current State | Allowed Next States |
| :--- | :--- |
| `pending` | `auto`, `manual`, `unmatched`, `ignored` |
| `auto` | `manual`, `confirmed`, `unmatched` |
| `manual` | `confirmed`, `unmatched` |
| `confirmed` | *(none)* |
| `unmatched` | `manual` |
| `ignored` | `manual` |
