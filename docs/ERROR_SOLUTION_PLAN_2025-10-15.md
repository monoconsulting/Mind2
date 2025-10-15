# Error Solution Plan 2025-10-15

**Created**: 2025-10-15
**Related Report**: ERROR_REPORT_2025-10-15.md
**Priority**: 🔴 CRITICAL - Production Blocking

---

## Solution Overview

The root cause is a **provider routing conflict** where:
1. Environment variable `AI_PROVIDER=ollama` forces all calls through Ollama
2. Database configuration specifies OpenAI models (gpt-5, gpt-5-mini)
3. Code prioritizes env var over database config, causing mismatch

**Primary Solution**: Fix provider selection logic in `ai_service.py` to respect database model configuration.

---

## Solution Options

### Option A: Fix Provider Selection Logic (RECOMMENDED)

**Approach**: Make code respect database `llm_id` when selecting provider, ignore `AI_PROVIDER` env var for model-specific calls.

**Pros**:
- Preserves existing database configuration
- Allows per-prompt provider selection
- Most flexible long-term solution
- No data migration needed

**Cons**:
- Requires code changes
- Needs rebuild and restart

**Implementation**:
1. Modify `ai_service.py` provider selection logic
2. Priority order: DB model llm_id → model name pattern → AI_PROVIDER env var
3. Add logging to track provider selection decisions

---

### Option B: Update Database to Use Ollama Models

**Approach**: Change all AI prompts to use Ollama models (llm_id=2, gpt-oss-20b).

**Pros**:
- Quick database fix
- No code changes needed
- Uses local Ollama instance (no API costs)

**Cons**:
- Requires Ollama container to be healthy
- gpt-oss-20b may have lower quality than gpt-5
- Loses OpenAI API benefits
- Need to test model quality

**Implementation**:
1. Fix Ollama container health (port 11434 vs 11435)
2. Update ai_system_prompts: set all selected_model_id to 2 (gpt-oss-20b)
3. Restart celery workers

---

### Option C: Set AI_PROVIDER=openai

**Approach**: Change `.env` to `AI_PROVIDER=openai`.

**Pros**:
- Single line change
- Quick fix
- Aligns with database config

**Cons**:
- Relies on global env var instead of per-model config
- Less flexible for mixed provider scenarios
- Band-aid solution if code logic is flawed

**Implementation**:
1. Edit `.env`: Change `AI_PROVIDER=ollama` to `AI_PROVIDER=openai`
2. Rebuild containers
3. Restart services

---

## Recommended Approach

**Use Option A + Option C hybrid**:

1. **Immediate fix**: Change `AI_PROVIDER=openai` in `.env` (gets system working NOW)
2. **Proper fix**: Improve provider selection logic in code (prevents future issues)
3. **Secondary fix**: Fix Ollama health for when local models are needed

---

## Implementation Task List

### Phase 1: Emergency Fix (Immediate - 5 minutes)

**Goal**: Get AI processing working immediately

- [ ] **Task 1.1**: Update `.env` file
  - File: `E:\projects\Mind2\.env`
  - Change: Line 72: `AI_PROVIDER=ollama` → `AI_PROVIDER=openai`
  - Priority: 🔴 CRITICAL
  - Estimated time: 1 minute

- [ ] **Task 1.2**: Rebuild Docker containers
  - Command: `mind_docker_build_nocache.bat`
  - Priority: 🔴 CRITICAL
  - Estimated time: 3-5 minutes

- [ ] **Task 1.3**: Restart services
  - Command: `mind_docker_compose_up.bat`
  - Priority: 🔴 CRITICAL
  - Estimated time: 1 minute

- [ ] **Task 1.4**: Verify AI processing works
  - Test: Upload a receipt and check if AI1-AI4 pipeline completes
  - Check: Celery logs for successful OpenAI API calls
  - Priority: 🔴 CRITICAL
  - Estimated time: 2 minutes

**Phase 1 Expected Result**: AI processing pipeline working again

---

### Phase 2: Code Fix (Within 24 hours)

**Goal**: Implement robust provider selection logic

- [ ] **Task 2.1**: Analyze current provider selection code
  - File: `backend/src/services/ai_service.py`
  - Focus: Find where provider is selected based on model name
  - Identify: Lines that check AI_PROVIDER env var
  - Priority: ⚠️ HIGH
  - Estimated time: 15 minutes

- [ ] **Task 2.2**: Implement improved provider selection
  - File: `backend/src/services/ai_service.py`
  - Logic:
    ```python
    # Priority order:
    # 1. Check DB: ai_llm_model.llm_id → ai_llm.provider_name
    # 2. Check model name pattern (gpt-* → OpenAI, claude-* → Anthropic)
    # 3. Fallback to AI_PROVIDER env var
    ```
  - Add: Detailed logging of provider selection decisions
  - Priority: ⚠️ HIGH
  - Estimated time: 30 minutes

- [ ] **Task 2.3**: Add validation checks
  - Validate: Model exists in database before using
  - Validate: Provider API key is configured
  - Error handling: Clear error messages when provider misconfigured
  - Priority: ⚠️ HIGH
  - Estimated time: 15 minutes

- [ ] **Task 2.4**: Test provider selection
  - Test scenario 1: OpenAI model → should use OpenAI API
  - Test scenario 2: Ollama model → should use Ollama API
  - Test scenario 3: Mixed models in pipeline → should switch correctly
  - Priority: ⚠️ HIGH
  - Estimated time: 20 minutes

- [ ] **Task 2.5**: Rebuild and deploy
  - Rebuild: `mind_docker_build_nocache.bat`
  - Restart: `mind_docker_compose_up.bat`
  - Verify: Run full AI pipeline on test receipt
  - Priority: ⚠️ HIGH
  - Estimated time: 10 minutes

**Phase 2 Expected Result**: Provider selection based on database config, not just env var

---

### Phase 3: Ollama Fix (Within 48 hours)

**Goal**: Fix Ollama container for local model support

- [ ] **Task 3.1**: Diagnose Ollama health check failure
  - Container: ollama-gpu
  - Check: Port configuration (11434 vs 11435)
  - Review: docker-compose.yml health check settings
  - Priority: 🟡 MEDIUM
  - Estimated time: 10 minutes

- [ ] **Task 3.2**: Fix Ollama port configuration
  - Check `.env`: OLLAMA_HOST should point to correct port
  - Check `docker-compose.yml`: Port mappings and health checks
  - Expected: Internal 11434, external 11435, or standardize
  - Priority: 🟡 MEDIUM
  - Estimated time: 5 minutes

- [ ] **Task 3.3**: Verify Ollama health
  - Test: `curl http://host.docker.internal:11435/api/tags`
  - Expected: 200 OK with model list
  - Check: Docker health status turns to "healthy"
  - Priority: 🟡 MEDIUM
  - Estimated time: 5 minutes

- [ ] **Task 3.4**: Test Ollama model inference
  - Test: Run AI1 with model_id=2 (gpt-oss-20b)
  - Verify: Successful completion
  - Compare: Quality vs OpenAI gpt-5-mini
  - Priority: 🟡 MEDIUM
  - Estimated time: 15 minutes

**Phase 3 Expected Result**: Ollama container healthy and usable for local models

---

### Phase 4: Monitoring & Documentation (Within 1 week)

**Goal**: Prevent similar issues and improve observability

- [ ] **Task 4.1**: Add provider selection logging
  - Log: Which provider selected for each AI prompt
  - Log: Reason for selection (DB config, pattern match, env var)
  - Log: API endpoint being used
  - Priority: 🟢 LOW
  - Estimated time: 15 minutes

- [ ] **Task 4.2**: Create provider configuration documentation
  - Document: How to configure providers in database
  - Document: Environment variables and their priority
  - Document: How to add new providers/models
  - Location: `docs/SYSTEM_DOCS/AI_PROVIDER_CONFIGURATION.md`
  - Priority: 🟢 LOW
  - Estimated time: 30 minutes

- [ ] **Task 4.3**: Add automated tests
  - Test: Provider selection logic
  - Test: Fallback behavior when API keys missing
  - Test: Mixed provider scenarios
  - Priority: 🟢 LOW
  - Estimated time: 1 hour

- [ ] **Task 4.4**: Add health checks for AI providers
  - Check: OpenAI API key valid on startup
  - Check: Ollama responding on configured port
  - Alert: Log warnings when providers unavailable
  - Priority: 🟢 LOW
  - Estimated time: 30 minutes

**Phase 4 Expected Result**: Better monitoring and documentation to prevent recurrence

---

## Validation Checklist

After completing Phase 1 (Emergency Fix), verify:

✅ **Celery Worker Logs**:
```
# Should see:
[INFO] Provider call for document_analysis (provider=OpenAI, model=gpt-5-mini): Success
[INFO] Provider call for expense_classification (provider=OpenAI, model=gpt-5-mini): Success
[INFO] Provider call for data_extraction (provider=OpenAI, model=gpt-5): Success

# Should NOT see:
[ERROR] Ollama API call failed: 404 Client Error
```

✅ **Receipt Processing**:
- Upload test receipt
- Verify OCR completes (status: ocr_complete)
- Verify AI1 completes (status: classified)
- Verify AI2 completes (status: expense_classified)
- Verify AI3 completes (status: data_extracted)
- Verify AI4 completes (status: accounting_ready)

✅ **Database**:
```sql
-- Check that receipts are progressing through AI stages
SELECT id, ai_status, ai_confidence, created_at
FROM unified_files
WHERE created_at > NOW() - INTERVAL 1 HOUR
ORDER BY created_at DESC;

-- Should see ai_status progressing: ocr_complete → classified → data_extracted → accounting_ready
```

✅ **API Endpoints**:
```bash
# Test classification endpoint
curl -X POST http://localhost:8008/ai/api/ai-processing/classify/document_analysis \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{"text": "KVITTO\nICA Supermarket\nSumma: 123.45 kr"}'

# Should return: {"document_type": "receipt"}
```

---

## Rollback Plan

If Phase 1 fix causes issues:

1. **Revert `.env` change**:
   ```
   AI_PROVIDER=ollama  # Back to original
   ```

2. **Rebuild and restart**:
   ```
   mind_docker_build_nocache.bat
   mind_docker_compose_up.bat
   ```

3. **Alternative**: Use Option B (switch to Ollama models in database)
   ```sql
   UPDATE ai_system_prompts SET selected_model_id = 2 WHERE id IN (4,5,6,7,8,9);
   ```

---

## Risk Assessment

### Phase 1 Risks:

**Risk**: OpenAI API rate limits
- **Likelihood**: Medium
- **Impact**: High
- **Mitigation**: Monitor API usage, implement rate limiting in code

**Risk**: OpenAI API costs
- **Likelihood**: High
- **Impact**: Medium
- **Mitigation**: Track costs, consider Ollama for high-volume tasks

**Risk**: API key invalid/expired
- **Likelihood**: Low
- **Impact**: High
- **Mitigation**: Test API call before deploying

### Phase 2 Risks:

**Risk**: Code changes introduce bugs
- **Likelihood**: Medium
- **Impact**: High
- **Mitigation**: Thorough testing, code review

**Risk**: Performance degradation
- **Likelihood**: Low
- **Impact**: Medium
- **Mitigation**: Performance testing before deployment

---

## Success Criteria

### Phase 1 Success:
- [ ] Zero "Ollama API call failed" errors in logs
- [ ] AI processing pipeline completing successfully
- [ ] Receipts reaching "accounting_ready" status within 2 minutes
- [ ] No errors in celery worker logs for 30 minutes

### Phase 2 Success:
- [ ] Provider selection respects database configuration
- [ ] Clear logging of provider selection decisions
- [ ] Successful tests with both OpenAI and Ollama models
- [ ] Code review approved

### Phase 3 Success:
- [ ] Ollama container health: "healthy"
- [ ] Successful inference with gpt-oss-20b model
- [ ] Quality assessment completed and documented

### Overall Success:
- [ ] All AI pipelines (AI1-AI6) working correctly
- [ ] No provider-related errors for 7 days
- [ ] Documentation complete and reviewed
- [ ] Automated tests passing

---

## Timeline Summary

| Phase | Duration | Priority | Status |
|-------|----------|----------|--------|
| Phase 1: Emergency Fix | 5-10 min | 🔴 CRITICAL | Pending |
| Phase 2: Code Fix | 1-2 hours | ⚠️ HIGH | Pending |
| Phase 3: Ollama Fix | 30-45 min | 🟡 MEDIUM | Pending |
| Phase 4: Monitoring & Docs | 2-3 hours | 🟢 LOW | Pending |

**Total Estimated Time**: 4-6 hours across 1 week

---

## Contact & Escalation

If issues persist after Phase 1:
1. Check OpenAI API status: https://status.openai.com
2. Verify API key validity in OpenAI dashboard
3. Review `backend/src/services/ai_service.py` for recent changes
4. Check container logs for additional errors: `docker logs mind2-ai-api-1`

---

**Document Status**: Ready for implementation
**Next Action**: Begin Phase 1 - Task 1.1
