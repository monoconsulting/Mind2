
# Implementation Plan: Mind Receipt System

**Branch**: `001-mind-system-receipt` | **Date**: 2025-09-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-mind-system-receipt/spec.md`

## Summary
Receipt capture system with mobile web interface for public capture, AI processing pipeline for OCR/classification, admin interface for review/approval, and SIE export for accounting. Implements pure Python architecture per MIND v2.0 with Flask API + Celery workers + Redis + MySQL.

## Technical Context
**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask, Celery, Redis, MySQL, Gunicorn, Nginx  
**Storage**: MySQL for metadata, filesystem for images, Redis for task queue  
**Testing**: pytest, Playwright for E2E  
**Target Platform**: Docker containers on Linux  
**Project Type**: MIND v2.0 pure Python stack (NOT web app with backend/frontend folders)  
**Performance Goals**: API p95 < 200ms, real-time OCR processing, concurrent uploads  
**Constraints**: Mobile-optimized capture, GDPR compliance, Swedish accounting standards (SIE)  
**Scale/Scope**: Multi-user receipt processing, 1000s receipts/month, admin workflow

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Architecture Compliance**: Follows MIND v2.0 pure Python stack:
- AI/API: `ai-api` container (`app/main.py`, `app/admin/admin_api_server.py`)  
- Frontend: `mind-web-main-frontend` container (`main-system/app-frontend`)
- Workers: `celery-worker` container (`app/services/queue_manager.py`)
- NO backend/frontend folder structure (deprecated)

✅ **Database Schema**: Canonical migration order unified_files → ai_* → invoice_*
✅ **API Endpoints**: All via `/ai/api/*` base as per MIND_ENDPOINTS.md  
✅ **Separation**: Mobile capture (public) vs Admin SPA (internal) properly separated

## Project Structure

### MIND v2.0 Architecture (Pure Python Stack)
```
# AI/API Container (ai-api)
app/
├── main.py                    # Flask application entry
├── admin/
│   └── admin_api_server.py    # Admin API Blueprint
├── services/
│   ├── queue_manager.py       # Celery configuration
│   ├── tasks.py              # Background workers
│   ├── validation.py         # Receipt validation
│   ├── enrichment.py         # Company data enrichment
│   └── accounting.py         # BAS accounting proposals
├── api/
│   ├── receipts.py           # Receipt CRUD endpoints
│   ├── reconciliation_firstcard.py # Company card matching
│   ├── export.py            # SIE export generation
│   ├── ingest.py            # Public capture endpoint
│   ├── auth.py              # JWT authentication
│   └── middleware.py        # CORS, auth decorators
└── observability/
    ├── logging.py           # Structured JSON logging  
    └── metrics.py           # Prometheus metrics

# Admin Frontend Container (mind-web-main-frontend)
main-system/app-frontend/
├── src/
│   ├── main.js              # Admin SPA entry
│   ├── wireframe.js         # Auth, routing, API client
│   └── views/
│       ├── receipts.js      # Receipt management
│       ├── receipt_detail.js # Review & approval
│       ├── company_card.js  # FirstCard reconciliation
│       ├── export.js        # SIE export generation
│       └── settings_rules.js # Accounting rules config
├── dist/                    # Built files for nginx
├── Dockerfile              # Container definition
└── nginx.conf             # Frontend + API proxy config

# Mobile Capture (separate deployment)
mobile-capture-frontend/
├── index.html              # Public receipt capture
├── app.js                 # Camera, gallery, tags, location
├── styles.css             # Mobile-optimized UI
└── README.md              # Deployment to web hotel

# Database Migrations (canonical order per MIND v2.0)
database/migrations/
├── 0001_unified_migration_fixed.sql    # unified_files, file_tags
├── 0002_ai_schema_extension.sql        # ai_*, processing_queue
└── 0003_2025_09_18_invoice_schema.sql  # invoice_*, FirstCard
```

**Structure Decision**: MIND v2.0 Pure Python Architecture (NOT web app Option 2)

## Implementation Status

**STATUS**: ✅ COMPLETED with architectural corrections applied.

### Phase 0: Research ✅ COMPLETE
- Technology decisions: Flask + Celery + Redis + MySQL + Nginx
- Mobile capture flow per MIND_FUNCTION_DESCRIPTION.md
- MIND v2.0 pure Python architecture validated

### Phase 1: Design & Contracts ✅ COMPLETE  
- **data-model.md**: Entities align with canonical migration order
- **contracts/**: API contracts for `/ai/api/*` endpoints
- **quickstart.md**: End-to-end validation scenarios
- **Copilot instructions**: Updated for correct architecture

### Phase 2-5: Implementation ✅ COMPLETE + CORRECTED
- **All tasks executed**: 52 tasks completed (T001-T052)
- **Architecture corrected**: Added separation for mobile vs admin frontends
- **MIND v2.0 compliance**: Pure Python stack with proper containers
- **Containers deployed**: 
  - `ai-api`: Flask API + endpoints
  - `celery-worker`: Background processing
  - `mind-web-main-frontend`: Admin SPA (port 8008)
  - `mobile-capture-frontend`: Public capture (separate deployment)

### Architectural Corrections Applied
- ✅ Separated mobile capture from admin SPA
- ✅ Added `mind-web-main-frontend` container per MIND v2.0
- ✅ Removed deprecated backend/frontend folder structure  
- ✅ Implemented canonical migration order: unified → ai → invoice
- ✅ All endpoints use `/ai/api/*` base as specified

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [ ] Phase 0: Research complete (/plan command)
- [ ] Phase 1: Design complete (/plan command)
- [ ] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [ ] Initial Constitution Check: PASS
- [ ] Post-Design Constitution Check: PASS
- [ ] All NEEDS CLARIFICATION resolved
- [ ] Complexity deviations documented

---
*Based on Constitution v1.0.0 - See `/memory/constitution.md`*
