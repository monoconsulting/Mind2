# AI Workflow Failure Report (MIND_REPORT_AI_ERRORS3.md)
_Prepared: 17 October 2025_

## 1. Scope & Context
- Requested deep dive into the current AI workflow outages affecting both receipt (WF1) and FirstCard (WF3) pipelines.
- Environment time reference: 17 Oct 2025.
- Investigation limited to repository contents available in `e:\projects\Mind2`. No direct access to running containers, Docker logs, live databases, or external network resources.

## 2. Summary of Findings
1. **OpenAI Responses API migration partially complete.**  
   - `backend/src/services/ai_service.py` now targets `https://api.openai.com/v1/responses`.  
   - Initial change used the deprecated `response_format` payload property, triggering 400 errors; patched to use `text: { format: "json_object" }`.  
   - Need confirmation from runtime logs that OpenAI accepts the final payload (not verifiable offline).
2. **No fallback when providers fail.**  
   - `_provider_generate` logs an error and aborts if the configured provider instance is `None` or raises. No guards for retry/backoff or alternate providers. Failures cascade quickly to workflow aborts (`wf3_firstcard_invoice` raising `Failed to persist credit card invoice header`).
3. **Dependency on DB configuration (ai_system_prompts / ai_llm / ai_llm_model).**  
   - Providers/models are injected entirely from DB. If records are stale (e.g., still pointing at chat-completions models) workflows fail before reaching business logic. Unable to audit actual DB rows offline; high-risk configuration point.
4. **Downstream persistence assumptions.**  
   - WF3 calls `_persist_creditcard_invoice_main` only after a successful AI6 parse. Any AI failure still pushes the workflow to a hard error; there is no degraded mode to store combined OCR or partial metadata beyond what we recently added.
5. **Test endpoints & scripts still reference legacy APIs.**  
   - `backend/src/api/ai_config.py` provider test for OpenAI checks `/v1/models`, which is still valid but does not guarantee Responses API readiness. Consider adding a targeted Responses API smoke test.

## 3. Detailed Observations
### 3.1 Provider Loading Logic
- `AIService._load_prompts_and_providers` reads the AI config tables and instantiates providers per prompt. All prompts without valid provider/model remain detached (`prompt_providers[key] = None`), causing immediate runtime errors when invoked.
- There is no repository default or sample data to validate these configurations. Recommend extracting the current DB dump to confirm that:  
  - Each critical prompt (`credit_card_invoice_parsing`, `data_extraction`, etc.) points to a provider that supports the Responses API (`gpt-5`, `json_object` output).  
  - API keys stored in `ai_llm` are current and not revoked.

### 3.2 Error Surfacing
- When a provider raises, `_provider_generate` re-raises a `RuntimeError`.  
- Workflows log the provider/model pair (`provider=OpenAI, model=gpt-5`) but the root-cause (HTTP 400) halts the Celery task and never re-queues. There is no automatic mitigation (e.g., marking the stage as `failed` and letting an operator retry from the UI).

### 3.3 Receipts vs FirstCard
- WF1 (receipts) and WF3 (FirstCard) share the same `AIService`. A mis-configuration in shared prompts or provider tables concurrently breaks both workflows.
- WF3 specifically depends on AI6 (`credit_card_invoice_parsing`) for header/line extraction. Without a successful call, `_persist_creditcard_invoice_main` is not reached; the workflow raises `RuntimeError("Failed to persist credit card invoice header")`.

### 3.4 Recent Code Changes
- The repository currently includes the Responses API change (`text.format`). Anyone running older containers without rebuilding may still execute the pre-patch code, so ensure services are redeployed after updating.

## 4. Gaps Due to Offline Analysis
- **Docker logs:** Not accessible from this environment. Please capture current Celery worker logs after redeploy/restart to confirm request/response flows.  
- **Database inspection:** No visibility into `ai_system_prompts`, `ai_llm`, `ai_llm_model`, or `ai_processing_history` tables. Recommend exporting current rows for auditing.  
- **Network connectivity:** Cannot validate outbound reachability, DNS, or TLS issues from within the containers. Ensure firewalls/proxies permit POSTs to `api.openai.com`.  
- **Access tokens:** Unable to verify that `OPENAI_API_KEY` and DB-stored API keys remain valid/active.

## 5. Recommended Next Steps
1. **Redeploy / Restart AI services** after pulling the latest code so the patched Responses payload is live.  
2. **Run a live FirstCard import** and monitor Celery logs to confirm the HTTP 400 is resolved.  
3. **Audit AI configuration tables**:  
   - Verify provider names (`OpenAI`), models (`gpt-5`), and that Response-format capable prompts are selected.  
   - Confirm `ai_llm.enabled = 1` and API keys are correct.  
4. **Enhance monitoring**:  
   - Record request/response metadata (status codes, latency) into `ai_processing_history` for faster triage.  
   - Optionally implement retry/backoff in `_provider_generate` for transient errors (timeouts, 429).  
5. **Add health checks**: extend `/ai/api/ai_config.py`’s provider test endpoint to hit `/v1/responses` with a tiny `text.format` payload to catch regressions early.

## 6. Open Questions / Operator Actions
- Are containers rebuilt/restarted following recent AI code updates?  
- Do current DB prompt configurations still reference deprecated chat-completion models?  
- Is there evidence of networking issues (timeouts, SSL errors) beyond payload validation failures?  
- Would a temporary feature flag to bypass AI calls (logging & manual fallback) be acceptable to restore partial functionality while investigating?

---
_Prepared without live log or database access. Please supplement with runtime evidence from the operational environment for a complete root-cause analysis._
