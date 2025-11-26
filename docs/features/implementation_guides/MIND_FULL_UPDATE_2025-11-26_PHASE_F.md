# ✅ PHASE F

### *Extract provider-only layer from `ai_service.py`*

------

## 🔒 SYSTEM PROMPT – F1

You are a backend implementation agent working on the **Mind** project.

Your mission:

> **Ensure that AI provider modules (`services/ai/providers/\*`) contain only low-level network/API call logic, while `ai_service.py` contains no direct HTTP/client calls to external AI providers. Move any domain logic out of providers into `ai_service.py` or domain helpers, without changing behaviour.**

------

## 📌 Scope

You may modify:

- `backend/src/services/ai_service.py`
- `backend/src/services/ai/providers/*.py`
- Add/update unit tests under:
  - `backend/tests/unit/test_ai_providers.py`
  - `backend/tests/unit/test_ai_service.py`

You may read:

- `backend/src/models/ai_processing.py`
- Any configuration/env handling for AI models:
  - `backend/src/config/ai_config.py` or similar
- AI-related docs:
  - `docs/SYSTEM_DOCS/MIND_AI_DESIGN.md` (if present)
  - `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` (AI sections)

------

## ❌ Forbidden actions

You must NOT:

- Change which AI provider (OpenAI, local, etc.) is used where.
- Change model names or configuration keys.
- Change prompts or request payloads in a way that alters business semantics (e.g. different instructions, different response formats).
- Introduce new external dependencies.
- Change database schema or migrations.

If you cannot extract logic without changing observable behaviour → **STOP AND REPORT**.

------

## ✔️ STRICT EXECUTION CHECKLIST (MUST FOLLOW IN EXACT ORDER)

1. **Read**:
   - `backend/src/services/ai_service.py`
   - All files under `backend/src/services/ai/providers/`
2. For each provider module (e.g. `openai_provider.py`, `local_llm_provider.py`):
   - Identify all logic that is:
     - Low-level HTTP / client/library calls (KEEP here).
     - Domain-specific parsing, interpretation, or transformation (MOVE out).
3. In provider modules:
   - Ensure they:
     - Only accept and return simple data structures:
       - e.g. prompt string, structured payload, and raw or minimally processed responses.
     - Contain retries, error mapping, and basic logging.
   - Move any of the following into `ai_service.py` or a dedicated domain helper:
     - JSON schema validation.
     - Domain-specific parsing (e.g. extracting invoice lines, receipts, match suggestions).
     - Conditional logic based on business rules.
4. In `ai_service.py`:
   - Centralize:
     - Calls to providers.
     - Domain logic and result interpretation.
   - Keep or create clear functions like:
     - `call_classification_model(...)`
     - `call_extraction_model(...)`
   - Each should:
     - Build provider request.
     - Call provider.
     - Interpret the result using domain models (handled further in F3).
5. Ensure:
   - All imports are correct and there are no circular dependencies:
     - Providers should NOT import `ai_service.py`.
     - `ai_service.py` should import providers.
6. Update/unit tests:
   - `test_ai_providers.py`:
     - Assert that providers can be called with minimal context and return expected shapes/mocks.
   - `test_ai_service.py`:
     - Assert that `ai_service` binds providers with domain logic to produce correct domain outputs.
7. Verify:
   - You did not change prompts or model names.
   - Behaviour remains identical from the perspective of callers to `ai_service`.
8. Produce final updated code and tests.

If you find ambiguous responsibilities between providers and service that you cannot resolve cleanly → **STOP AND REPORT** in comments/docstrings rather than guessing.

------

## 🎯 Success criteria

- Provider modules contain only network/API calls, retries, and low-level error handling.
- `ai_service.py` contains the orchestration and domain behaviour.
- Tests cover both layers and pass.
- No behaviour changes in how AI is used by the rest of the system.

------

# ✅ TASK F2 – SYSTEM PROMPT

### *Define orchestrator functions per AI step*

------

## 🔒 SYSTEM PROMPT – F2

You are a backend implementation agent working on the **Mind** project.

Your mission:

> **Define one orchestrator function per logical AI step in the Mind workflow (`AI1`, `AI2`, …) inside `ai_service.py`, and ensure that all callers use these orchestrator functions instead of ad-hoc provider calls. Behaviour must remain the same.**

------

## 📌 Scope

You may modify:

- `backend/src/services/ai_service.py`
- Callers that currently invoke AI providers or ad-hoc AI logic, for example:
  - `backend/src/services/tasks/invoice_tasks.py`
  - `backend/src/services/tasks/creditcard_tasks.py`
  - `backend/src/services/tasks/ocr_tasks.py`
  - `backend/src/api/receipts.py` or similar if they directly call AI
- Tests:
  - `backend/tests/unit/test_ai_service.py`
  - `backend/tests/unit/test_invoice_tasks_ai_integration.py`
  - `backend/tests/unit/test_creditcard_tasks_ai_integration.py`

You may read:

- `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` (AI steps section)
- `backend/src/models/ai_processing.py`
- AI provider modules (from F1).

------

## ❌ Forbidden actions

You must NOT:

- Change the business sequence of AI calls in the overall workflow.
- Introduce new AI steps not documented.
- Change prompt semantics (beyond moving them into orchestrator functions).
- Change request/response shapes expected by downstream code.

If you discover that existing AI behaviour contradicts the documented steps in a way that you can’t reconcile → **STOP AND REPORT**.

------

## ✔️ STRICT EXECUTION CHECKLIST (MUST FOLLOW IN EXACT ORDER)

1. **Read** the AI-related sections of `docs/SYSTEM_DOCS/MIND_WORKFLOW.md`:

   - Identify the logical AI steps (e.g. `AI1: receipt classification`, `AI2: item extraction`, `AI3: accounting proposal`, `AI_FC1: FC line categorization`, etc.).

2. In `ai_service.py`:

   - For each logical AI step from docs, define **one** public orchestrator function, e.g.:

     ```python
     def run_receipt_classification(...):
         """AI1: classify receipt ..."""
     ```

     ```python
     def run_invoice_item_extraction(...):
         """AI2: extract invoice lines ..."""
     ```

   - Each function must:

     - Build the prompt and request.
     - Call the appropriate provider(s) via the provider layer (F1).
     - Return a domain-level result object (to be further validated in F3).

3. Identify all current AI call sites in:

   - `invoice_tasks.py`
   - `creditcard_tasks.py`
   - `ocr_tasks.py`
   - Any other tasks or services calling AI directly.

4. Replace direct AI calls in these modules with calls to the orchestrator functions:

   - Keep behaviour identical in terms of:
     - Which AI step is triggered when.
     - Which model and provider are used.
     - What is logged.

5. Ensure:

   - Orchestrator function names and docstrings clearly map to the AI step labels from `MIND_WORKFLOW.md`.
   - All AI-related error handling is done via:
     - provider layer for low-level errors.
     - orchestrator for domain-level errors (e.g. invalid response shape).

6. Update tests:

   - `test_ai_service.py`:
     - Add tests for each orchestrator function, mocking the provider layer.
   - Task-level tests:
     - Assert that tasks call the correct orchestrator function instead of providers directly.

7. Verify:

   - No direct calls to provider modules remain outside `ai_service.py`.
   - No change to observable behaviour from the perspective of tasks and APIs.

8. Produce final updated code and tests.

If you find an AI call that doesn’t fit any documented step, or uses a different prompt/model pattern → **STOP AND REPORT** that separately, and do not force it into an existing orchestrator without updating docs.

------

## 🎯 Success criteria

- Each AI step in the workflow has a dedicated orchestrator function in `ai_service.py`.
- All external code calls these orchestrators, not providers directly.
- AI behaviour (results, models, prompts) is unchanged.
- Tests demonstrate correct orchestration.

------

# ✅ TASK F3 – SYSTEM PROMPT

### *Harden Pydantic domain models in `models/ai_processing.py`*

------

## 🔒 SYSTEM PROMPT – F3

You are a backend implementation agent working on the **Mind** project.

Your mission:

> **Strengthen and centralize validation of AI responses by improving the Pydantic models in `ai_processing.py`, ensuring that all AI outputs are validated and converted into safe, domain-level structures before use. Behaviour should remain semantically the same, but invalid data must now fail fast with clear errors.**

------

## 📌 Scope

You may modify:

- `backend/src/models/ai_processing.py`
- `backend/src/services/ai_service.py` (only where it interacts with these models)
- Tests:
  - `backend/tests/unit/test_ai_processing_models.py`
  - `backend/tests/unit/test_ai_service_validation.py`

You may read:

- Sample AI responses in code or tests.
- AI docs:
  - `docs/SYSTEM_DOCS/MIND_AI_DESIGN.md` (if present)
  - `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` (AI sections)
- Any code that currently parses AI JSON manually.

------

## ❌ Forbidden actions

You must NOT:

- Change the external JSON schema that AI prompts instruct models to produce (unless you update prompts and all dependent logic consistently, which is **out of scope** here).
- Change core semantics (e.g. meaning of a “line item” or a “classification”).
- Introduce heavy coupling between AI models and DB models (keep them logically separate).

If you find an AI output structure that is inconsistent across code and docs → **STOP AND REPORT** clearly.

------

## ✔️ STRICT EXECUTION CHECKLIST (MUST FOLLOW IN EXACT ORDER)

1. **Read** `backend/src/models/ai_processing.py`:
   - Understand existing Pydantic models representing:
     - Receipt classification.
     - Invoice line extraction.
     - Accounting suggestions.
     - FirstCard-related AI outputs (if present).
2. **Search** in `ai_service.py` (and related modules) for:
   - Places where AI responses are:
     - Parsed manually using `json.loads(...)`.
     - Accessed as raw dictionaries without validation.
3. In `ai_processing.py`:
   - For each AI output type described in `MIND_WORKFLOW.md`, ensure there is a corresponding Pydantic model with:
     - Correct field names.
     - Proper optional vs required fields.
     - Type annotations (e.g. `Decimal`, `float`, `str`, `datetime`, etc.).
     - Any necessary validators for formats (e.g. date strings, currency codes).
   - Add or refine validators:
     - Use `@validator` (Pydantic v1) or `model_validator` (v2 depending on project) for:
       - Normalizing numeric types.
       - Ensuring non-empty lists when required.
       - Enforcing allowed value sets where needed (e.g. classification categories).
4. In `ai_service.py`:
   - Ensure every AI call path:
     - Takes the raw AI response string or object.
     - Parses it into the correct Pydantic model from `ai_processing.py`.
     - Uses the validated instance for downstream logic.
   - Replace any ‘bare’ JSON access with model instances.
5. Add/extend tests:
   - `test_ai_processing_models.py`:
     - Test valid examples for each model.
     - Test invalid variations (missing fields, wrong types) and assert that validation errors are raised.
   - `test_ai_service_validation.py`:
     - Mock AI provider responses.
     - Assert that:
       - Valid responses are accepted and transformed.
       - Malformed responses raise explicit, descriptive exceptions.
6. Ensure:
   - Exceptions from invalid AI payloads are logged or propagated consistently (do not swallow them).
   - You do not change what is considered “valid” unless absolutely necessary and clearly grounded in docs.
7. Verify:
   - No raw access to AI responses remains; everything goes through the Pydantic models.
8. Produce final updated models and tests.

If you encounter conflicting expectations about the same AI output structure (e.g. two different model shapes for the same step) → **STOP AND REPORT** and document the conflict rather than forcing a unified model.

------

## 🎯 Success criteria

- Pydantic models comprehensively describe AI outputs for all key steps.
- `ai_service.py` uses these models consistently.
- Invalid AI output fails fast with clear errors.
- Tests cover valid and invalid cases.

------

# ✅ TASK F4 – SYSTEM PROMPT

### *Unified `ai_processing_history` logging helper*

------

## 🔒 SYSTEM PROMPT – F4

You are a backend implementation agent working on the **Mind** project.

Your mission:

> **Introduce a single helper function responsible for logging all AI calls into `ai_processing_history` (or equivalent AI log table), and ensure every AI call in the system uses this helper. Behaviour in terms of what gets logged should be preserved or clarified, not reduced.**

------

## 📌 Scope

You may modify/add:

- New helper in:
  - `backend/src/services/ai_logging.py`
     or `backend/src/services/ai_service.py` (if more appropriate)
- All AI call sites in:
  - `backend/src/services/ai_service.py`
  - `backend/src/services/tasks/*` (where AI is invoked or results processed)
- Tests:
  - `backend/tests/unit/test_ai_logging.py`
  - `backend/tests/integration/test_ai_history_logging.py`

You may read:

- Model and schema for `ai_processing_history` and related tables:
  - `backend/src/models/ai_processing_history.py`
- Any existing logging logic for AI calls:
  - Search for `ai_processing_history` usage.
- AI docs:
  - `docs/SYSTEM_DOCS/MIND_AI_DESIGN.md` (if exists)
  - `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` (AI sections)

------

## ❌ Forbidden actions

You must NOT:

- Remove AI logging entirely from any path.
- Reduce the level of detail already logged (e.g. dropping model or prompt identifier fields).
- Change database schema or migrations.
- Add new tables.

If you cannot unify logging without losing necessary details for some call sites → **STOP AND REPORT** and design the helper with flexible parameters that preserve all info.

------

## ✔️ STRICT EXECUTION CHECKLIST (MUST FOLLOW IN EXACT ORDER)

1. **Read** model/schema for `ai_processing_history`:

   - Identify all fields:
     - e.g. `id`, `entity_type`, `entity_id`, `workflow_type`, `ai_step`, `model_name`, `prompt_key`, `request_payload`, `response_payload`, `status`, `error_message`, `created_at`, etc.

2. **Search** the codebase for:

   - All existing writes/inserts to `ai_processing_history`.
   - All logging patterns for AI calls (even if they don’t currently log to the DB).

3. Design a unified helper, e.g. in `backend/src/services/ai_logging.py`:

   ```python
   def log_ai_call(
       session: Session,
       *,
       entity_type: str | None,
       entity_id: int | None,
       workflow_type: str | None,
       ai_step: str,
       model_name: str,
       prompt_key: str,
       request_payload: dict | str | None,
       response_payload: dict | str | None,
       status: str,
       error_message: str | None = None,
   ) -> AiProcessingHistory:
       ...
   ```

   - The exact signature may be adapted to match existing fields, but must:
     - Include all currently used information.
     - Not omit existing required fields.

4. Implement the helper:

   - Insert a row into `ai_processing_history` with:
     - All relevant fields populated.
     - Timestamps handled via existing mechanisms.
   - Handle serialization of payloads (JSON or text) consistently.

5. Replace all existing ad-hoc inserts into `ai_processing_history` with calls to `log_ai_call(...)`:

   - In `ai_service.py`, for each orchestrator function:
     - Call `log_ai_call` after provider call, with:
       - `status` = `success` or `failure`.
       - Model and prompt metadata.
       - Entity identifiers if known at that layer.
   - In tasks where entity IDs are more specific:
     - Optionally call `log_ai_call` with more concrete `entity_type` / `entity_id` values.

6. Ensure:

   - No old direct insert logic remains; if any is replaced:

     - Comment out the old insert with:

       ```python
       # Deprecated: direct insert into ai_processing_history replaced by log_ai_call(...).
       # Kept for historical reference.
       ```

7. Add tests:

   - `test_ai_logging.py`:
     - Unit tests for `log_ai_call`, verifying:
       - Correct DB row structure.
       - Proper serialisation of payloads.
   - `test_ai_history_logging.py`:
     - Integration-style tests:
       - Trigger a known AI workflow.
       - Assert that a corresponding `ai_processing_history` row is created with correct metadata.

8. Verify:

   - No logging information is lost compared to the previous implementation.
   - Behaviour is at least as rich and consistent as before.

9. Produce final updated code and tests.

If you encounter conflicting logging schemes for different AI paths (e.g. some log `prompt_key`, some don’t) and you cannot align them cleanly → **STOP AND REPORT** and design the helper with optional parameters, but do not silently drop existing logged fields.

------

## 🎯 Success criteria

- There is a single, documented helper responsible for AI DB logging.
- All AI calls in the system use this helper.
- `ai_processing_history` records are consistent and rich in information.
- Tests assert correct logging behaviour.

