# docs/source_of_truth/70_AI_PROMPTS_AND_ROLES.md

# Mind – AI Prompts and Roles (Source of Truth)

> This file defines the AI roles used in Mind (AI1–AI7 and similar), their responsibilities, and references to the prompts and contracts they follow. If AI behavior in code or agents differs from what is written here, this file must be updated.

## 1. Overview

Mind uses a chain of AI steps to process documents. Typical roles include:

- **AI1 – Document Type Classification**
- **AI2 – Field Extraction**
- **AI3 – Normalisation / Enrichment**
- **AI4 – Accounting Proposal Generation**
- **AI5 – Matching Support**
- **AI6 / AI7 – Additional enrichment, summaries or QA**

> NOTE: Exact naming and responsibilities must be aligned with the current implementation in the codebase and any external agent orchestration tools.

## 2. Role Definitions

For each AI role, document:

- **Name/Identifier** – How it is referred to in code/config (e.g. `AI1_DOCUMENT_TYPE`).
- **Responsibility** – Short description of what the step does.
- **Input Contract** – Required fields, optional fields, context (e.g. previous AI outputs, company settings, Swedish BAS rules).
- **Output Contract** – Expected JSON structure, mandatory fields, error model.
- **Model / Provider** – Which model(s) are typically used (e.g. GPT-5.1, local LLM), including any fallbacks.
- **Prompt Reference** – Where the actual prompt is stored (file path, config key) and how it is versioned.

A simple template section for each AI role should look like this:

\## AIx – <Role Name>

\- Identifier: `AIx_<SOME_NAME>`

\- Responsibility: ...

\- Input Contract:

  \- `field1` (type, required/optional)

  \- `field2` ...

\- Output Contract:

  \- `field1` ...

  \- `field2` ...

\- Model / Provider:

  \- Primary: ...

  \- Fallback: ...

\- Prompt Reference:

  \- Prompt file: `docs/prompts/AIx_<name>.md`

  \- Version: semantic version or Git hash reference

## 3. Prompt Storage and Versioning

- Prompts should live in a predictable location (e.g. `docs/prompts/` or `backend/prompts/`).
- File names must map clearly to AI roles.
- Changes to prompts that may affect behavior must be tracked via Git and, ideally, a simple version field stored together with AI outputs (for traceability).

## 4. Error Handling and Guardrails

For each AI role, specify:

- How invalid or partial responses are detected.
- How retries are handled.
- Any guardrails or schema validation applied before persisting results.

## 5. Governance

- New AI roles must be added here before or together with implementation.
- Deprecated roles should be marked with a clear note and migration path.

*End of initial Mind Source of Truth document set (draft).*