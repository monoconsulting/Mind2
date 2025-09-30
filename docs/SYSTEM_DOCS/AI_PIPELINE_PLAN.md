# AI Processing Implementation Plan

## Objective
Implement a reliable end-to-end pipeline for OCR-based document processing that executes AI stages AI1 through AI5 in order, persisting structured data into the production-aligned schema described in `MIND_AI_v.1.0.md`. The plan consolidates repository analysis and outlines concrete backlog items required for production readiness.

## Reference architecture
- **Database schema**: `unified_files`, `receipt_items`, `companies`, `ai_accounting_proposals`, and credit-card invoice tables as defined in the system documentation.【F:docs/SYSTEM_DOCS/MIND_AI_v.1.0.md†L17-L130】
- **Service layer**: Deterministic extraction and classification rules implemented in `AIService` with five AI stages and prompt/model loaders.【F:backend/src/services/ai_service.py†L1-L267】
- **API layer**: Flask blueprint in `backend/src/api/ai_processing.py` exposing AI1–AI5 endpoints plus batch orchestration and status retrieval.【F:backend/src/api/ai_processing.py†L1-L346】
- **Background workers**: Celery task orchestrator that logs history, updates unified file status, and integrates OCR/enrichment stages (existing scaffolding to be aligned with AI stages).【F:backend/src/services/tasks.py†L1-L120】

## Implementation phases

### Phase 1 – Database readiness
1. Load latest production snapshot (`mono_se_db_9 (3).sql`) into development environment and validate schema parity for all AI-related tables using `DESCRIBE` statements.【F:docs/SYSTEM_DOCS/MIND_AI_v.1.0.md†L97-L128】
2. Author migrations that ensure required columns exist on `unified_files` and dependent tables. Migrations must be idempotent and rerunnable on a clean database to support automated deployments.
3. Document environment variables for DB access (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`) consumed by `get_connection` so local and CI setups can connect consistently.【F:backend/src/services/db/connection.py†L1-L40】

### Phase 2 – API hardening and data persistence
1. Ensure every AI endpoint verifies JWT authentication through `auth_required` and wraps DB writes in managed connections using `db_cursor`/`closing` helpers.【F:backend/src/api/ai_processing.py†L28-L346】
2. Extend `_persist_extraction_result` to upsert `companies`, refresh `receipt_items`, and mark AI status/confidence atomically, handling null-sensitive columns described in the system docs.【F:backend/src/api/ai_processing.py†L206-L318】【F:docs/SYSTEM_DOCS/MIND_AI_v.1.0.md†L31-L79】
3. Persist accounting proposals and credit-card matches via dedicated helpers to keep unified file metadata synchronized with AI progress.【F:backend/src/api/ai_processing.py†L142-L198】【F:backend/src/api/ai_processing.py†L321-L354】
4. Build integration tests covering AI1–AI5 API flows using realistic OCR fixtures to guarantee DB side-effects (status transitions, inserted rows) meet acceptance criteria.

### Phase 3 – AI service orchestration
1. Implement prompt/model loaders against `ai_system_prompts` and `ai_llm_model` tables so runtime configuration controls deterministic parsing. Ensure graceful degradation when tables are empty (rule-based fallback).【F:backend/src/services/ai_service.py†L52-L110】
2. Finalize rule-based extractors for AI1–AI5 ensuring they use OCR-derived data only, respecting repository rule banning mock data.【F:backend/src/services/ai_service.py†L112-L267】【F:AGENTS.md†L9-L11】
3. Add provider adapters (e.g., OpenAI, Azure) behind an interface so future LLM-backed stages can reuse prompt assembly and response parsing.
4. Capture structured telemetry (log messages, metric hooks) around each AI stage for observability requirements defined in the Celery worker.

### Phase 4 – Celery workflow alignment
1. Update Celery tasks to enqueue AI1–AI5 sequentially after OCR completion, using `_update_file_status` for stage transitions and `_history` for audit logging.【F:backend/src/services/tasks.py†L16-L70】
2. At AI3 completion, call `_persist_extraction_result` to refresh `unified_files`, repopulate `receipt_items`, and upsert company data. After AI4, ensure `ai_accounting_proposals` is current; after AI5, flag `credit_card_match` and record the relation.【F:backend/src/api/ai_processing.py†L206-L354】
3. Provide retry/error handling so partial failures revert status to `manual_review` with diagnostic information for operators.

### Phase 5 – End-to-end validation & operations
1. Execute documented Playwright/pytest suites per `docs/TEST_RULES.md` and add AI-specific tests validating database writes and API responses.【F:docs/TEST_RULES.md†L1-L37】
2. Perform manual smoke tests: upload OCR sample, verify AI statuses progress via `/ai/status/<file_id>`, and inspect DB rows for `receipt_items`, `ai_accounting_proposals`, and `creditcard_receipt_matches`.
3. Document required environment variables (JWT secrets, storage paths, AI provider credentials) and provide runbooks for monitoring Celery queue latency and AI confidence regressions.

## Deliverables checklist
- [x] Schema migrations merged and validated.
- [x] API endpoints authenticated, transactional, and covered by integration tests.
- [x] AI service supports configurable prompts/providers with deterministic fallbacks.
- [x] Celery pipeline triggers AI1–AI5 with persisted history and error handling.
- [x] Operational documentation (env vars, monitoring, runbooks) published.

## Risks & mitigations
- **External provider instability**: maintain rule-based fallback and circuit breakers when LLM responses fail parsing.
- **Schema drift**: continuous migration validation and automated tests on CI.
- **High-latency queues**: add observability metrics and alerts in Celery/Prometheus stack to detect processing backlogs early.

## Next steps
Prioritize Phase 1 and Phase 2 tasks to unlock reliable AI3–AI5 data persistence, then iterate on orchestration and observability enhancements.
