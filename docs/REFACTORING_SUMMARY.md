# Refactoring-sammanfattning - Stora Filer

**TL;DR:** 8 kritiska filer kräver omedelbar refactoring. Totalt ~16,000 rader kod i dessa filer.

## 🚨 Kritiska Filer (Akut Åtgärd Krävs)

| Fil | Rader | Problem | Prioritet |
|-----|-------|---------|-----------|
| `backend/src/api/reconciliation_firstcard.py` | 2,418 | **WORKFLOW STANNAR!** Spridd state management, 15 endpoints, ingen central coordinator | 🔥 AKUT |
| `backend/src/services/tasks.py` | 3,950 | 59 funktioner, alla Celery tasks i en fil | 🔴 KRITISK |
| `main-system/app-frontend/src/ui/pages/Process.jsx` | 2,112 | 17 komponenter i en fil, monolitisk | 🔴 KRITISK |
| `main-system/app-frontend/src/ui/pages/CompanyCard.jsx` | 2,080 | Komplex state, många sub-komponenter | 🔴 KRITISK |

### ⚠️ VARFÖR FIRSTCARD ÄR HÖGST PRIORITET:
- **Produktion-problem:** Workflow stannar, invoices fastnar, status rapporteras fel
- **Rot-orsak:** Status-transitions spridda på 15 platser, ingen state machine
- **Snabb lösning:** Skapa Workflow Coordinator = 80% av problemen försvinner

## 🟡 Viktiga Filer (Hög Prioritet)

| Fil | Rader | Problem |
|-----|-------|---------|
| `backend/src/api/receipts.py` | 1,862 | 45 funktioner, blandad API/DB-logik |
| `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx` | 1,401 | För många features i en modal |
| `main-system/app-frontend/src/ui/pages/Receipts.jsx` | 1,293 | Stor listvy med embedded komponenter |
| `backend/src/services/ai_service.py` | 1,191 | Alla AI-providers i en fil |

## Snabb Åtgärdsplan

### 🔥 Vecka 1-2: `reconciliation_firstcard.py` (FÖRST!)
```
Skapa Workflow Coordinator:
- workflow_coordinator.py med central state machine
- Migrera alla transition_* anrop
- Implementera locking för concurrent updates
- Tester för state transitions

Extrahera endpoints:
- log.py (245 rader)
- upload.py + import.py
- status.py + detail.py
- lines.py + matching.py
- statements.py
```

### Vecka 3-4: `tasks.py`
```
Dela upp i:
- ocr_tasks.py
- ai_pipeline_tasks.py  
- invoice_tasks.py
- creditcard_tasks.py
- file_management_tasks.py
```

### Vecka 5-6: `Process.jsx`
```
Extrahera komponenter:
- StatusBadge, FilterPanel, ExportModal
- UploadModal, MapModal, AIStageModal
- Pagination, WorkflowBadges
```

## Nästa Steg

1. ✅ Läs full rapport: `REFACTORING_ANALYSIS_LARGE_FILES.md`
2. 🔥 **BÖRJA MED:** `reconciliation_firstcard.py` - Workflow Coordinator
   - Detta löser de akuta produktionsproblemen med stuck workflows
3. Skapa feature branch: `refactor/firstcard-workflow-coordinator`
4. Implementera Workflow Coordinator först (lösning på state-problem)
5. Sedan bryt ned endpoints i separata filer
6. Comprehensive testing efter varje steg

## 🎯 Workflow-problemen som kommer lösas:

✅ **Status transitions centraliserade** (inte spridda på 15 platser)  
✅ **Inga race conditions** (locking i coordinator)  
✅ **Konsistent state** (validation vid varje transition)  
✅ **Tydlig workflow lifecycle** (lätt att debugga)  
✅ **Färre stuck invoices** (robust state machine)
## Nästa Steg

1. ✅ Läs full rapport: `REFACTORING_ANALYSIS_LARGE_FILES.md`
2. Prioritera vilken fil att börja med
3. Skapa feature branch för refactoring
4. Följ gradvis nedbrytning-strategi
5. Comprehensive testing efter varje steg

---
**Se fullständig rapport:** [REFACTORING_ANALYSIS_LARGE_FILES.md](./REFACTORING_ANALYSIS_LARGE_FILES.md)
