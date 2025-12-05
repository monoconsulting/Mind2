# docs/source_of_truth/90_TEST_AND_QUALITY_STRATEGY.md

# Mind – Test and Quality Strategy (Source of Truth)

> This file describes how we ensure that Mind remains reliable as it evolves.
>
> Version: 2025-12-04
> Source: `docs/TEST_RULES.md`, `playwright.config.ts`, `playwright.dev.config.ts`

## 1. Test Types

Mind uses a combination of test types:

| Test Type | Purpose | Location | Framework |
|-----------|---------|----------|-----------|
| Unit Tests | Isolated business logic | `backend/tests/` | pytest |
| Integration Tests | API endpoints, DB interactions | `backend/tests/` | pytest |
| E2E Tests | Full user flows | `web/tests/` | Playwright |
| Data Validation | Schema and status invariants | Migrations, code | SQL, Python |

## 2. E2E Testing with Playwright

### 2.1 Configuration Files

| Config | Port | Purpose |
|--------|------|---------|
| `playwright.config.ts` | 8008 | Production testing (DO NOT EDIT) |
| `playwright.dev.config.ts` | 5169 | Development testing (may edit) |

### 2.2 Running Tests

**Production Testing (Port 8008):**
```bash
# Full test suite
npx playwright test --headed

# Single test file
npx playwright test web/tests/[filename].spec.ts --headed

# Tagged tests
npx playwright test -g @receipts --headed
```

**Development Testing (Port 5169):**
```bash
npx playwright test --config=playwright.dev.config.ts --headed
```

### 2.3 Test Output

| Output | Location |
|--------|----------|
| HTML Report | `web/test-results/html/index.html` |
| Videos | `web/test-results/media/video/` |
| Screenshots | `web/test-results/media/snapshots/` |
| Traces | `web/test-results/_artifacts/` |

### 2.4 Video and Snapshot Settings

- Video resolution: 3440x1440
- Snapshot resolution: 3440x1440
- Video format: WebM

## 3. Test Rules (From TEST_RULES.md)

### 3.1 Before Starting

1. Check if test exists in `/web/tests`
2. Report: "Test available" or "Test not available"
3. If test exists, fix the responsible layer
4. Never modify test to make it pass

### 3.2 Test Execution Workflow

1. **Prove Problem:** Run one failing test
2. **Fix:** Fix only the responsible layer
3. **Prove Fix:** Same test now passes
4. **Verify:** Check database updates
5. **Report:** Document each step

### 3.3 Success Criteria

- 100% pass rate required
- Tests must verify actual functionality
- Must confirm database changes
- Report must include test HTML link

### 3.4 Prohibited Actions

- DO NOT change `playwright.config.ts`
- DO NOT create new spec files if area exists (expand existing)
- DO NOT skip reporting steps
- DO NOT modify tests to make them pass

## 4. Critical Paths to Test

### 4.1 Receipt Workflow (WF1)

1. Upload receipt via portal
2. OCR extraction completes
3. AI classification succeeds
4. Data extraction produces valid data
5. Accounting proposal generated
6. Status reaches `completed`/`KLAR`

### 4.2 FirstCard Workflow (WF3)

1. Upload credit card statement
2. OCR extraction completes
3. AI parsing extracts header and lines
4. Auto-matching runs
5. Manual match UI functional
6. Status reaches `completed`/`KLAR`

### 4.3 Manual Match Flow

1. List statements
2. View statement details
3. View transaction lines
4. Match receipt to line
5. Confirm match
6. Verify database update

### 4.4 Export Flow

1. Select receipts/invoices
2. Generate SIE export
3. Verify export file content

## 5. Pre-Release Requirements

### 5.1 Mandatory Tests

- [ ] All existing E2E tests pass
- [ ] Critical paths covered
- [ ] No open P0 defects
- [ ] Database migrations tested

### 5.2 Test Coverage

| Area | Required Coverage |
|------|-------------------|
| Receipt upload | 100% |
| Receipt processing | 100% |
| FirstCard upload | 100% |
| FirstCard processing | 100% |
| Manual matching | 100% |
| Export | 100% |

## 6. Data Validation

### 6.1 Status Consistency

All status fields must follow `30_STATUS_MODEL.md`:
- `unified_files.ai_status` values must be valid
- `workflow_runs.status` values must be valid
- `workflow_stage_runs.status` values must be valid

### 6.2 Schema Validation

- Migrations must be tested on realistic data
- Foreign key constraints must be satisfied
- Data types must match schema

### 6.3 Validation Queries

```sql
-- Check for invalid ai_status values
SELECT DISTINCT ai_status FROM unified_files
WHERE ai_status NOT IN ('uploaded', 'processing', 'ocr_done', 'ocr_failed', 'manual_review', 'completed', 'failed');

-- Check for orphaned workflow_stage_runs
SELECT wsr.* FROM workflow_stage_runs wsr
LEFT JOIN workflow_runs wr ON wr.id = wsr.workflow_run_id
WHERE wr.id IS NULL;
```

## 7. AI Testing

### 7.1 AI Behavior Stability

- Prompts must be versioned
- Model changes must be tested
- Confidence thresholds must be validated

### 7.2 AI Test Cases

| AI Role | Test Cases |
|---------|------------|
| AI1 | Receipt classification, invoice classification, unknown document |
| AI3 | Amount extraction, date extraction, merchant extraction |
| AI4 | Account code assignment, VAT calculation |
| AI5 | Exact match, fuzzy match, no match |
| AI6 | Header parsing, line parsing, multi-page |

## 8. Test Data Guidelines

### 8.1 Prohibited

- **NO MOCK DATA** - All data must come from real sources
- **NO HARDCODED VALUES** - Use database or API data

### 8.2 Test Data Sources

- Real receipts (anonymized if needed)
- Real credit card statements (anonymized)
- Database fixtures from migrations

## 9. Continuous Integration

### 9.1 CI Pipeline

1. Run linting
2. Run unit tests
3. Run integration tests
4. Build containers
5. Run E2E tests
6. Generate reports

### 9.2 CI Requirements

- All tests must pass before merge
- Test reports must be attached to PR
- Coverage must not decrease

## 10. Regression Testing

### 10.1 When Required

- Before any release
- After major refactoring
- After database migrations
- After AI prompt changes

### 10.2 Regression Test Suite

Full E2E test suite covering all critical paths.

## 11. Performance Testing

### 11.1 Benchmarks

| Operation | Target |
|-----------|--------|
| File upload | < 2s |
| OCR processing | < 30s |
| AI classification | < 10s |
| Page load | < 2s |

### 11.2 Load Testing

- Concurrent uploads: 10 files
- Concurrent users: 5

## 12. Quality Gates

### 12.1 Before Merge

- [ ] All tests pass
- [ ] No linting errors
- [ ] Code review approved
- [ ] SoT docs updated (if applicable)

### 12.2 Before Release

- [ ] Full regression suite passes
- [ ] No P0/P1 defects
- [ ] Documentation updated
- [ ] Release notes prepared

## 13. Governance

- New features must include appropriate tests
- When changing core flows, update SoT docs
- Test changes must be reviewed
- Breaking changes require migration plan
