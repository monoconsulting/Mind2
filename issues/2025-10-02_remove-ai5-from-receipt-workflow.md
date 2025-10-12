# Ta bort AI5 från kvittoflödet

## Context

AI5 (Credit Card Matching) används idag som sista steg i det workflow som körs på varje kvitto. Detta steg matchar kvitton mot fakturor från FirstCard.

**Nuvarande beteende:**
- AI5 körs automatiskt på varje kvitto efter AI4
- AI5 visas i Process-menyn som en workflow-badge
- Systemet försöker matcha varje kvitto mot kreditkortsfakturor

**Problem:**
Vi kommer att göra matchningen i ett senare steg - och matchningen behöver inte göras per kvitto utan istället med fakturan som utgångspunkt (dvs. för varje faktura, matcha mot alla kvitton för perioden).

**Önskat beteende:**
- AI5-steget ska inte köras automatiskt längre
- AI5 ska inte visas i Process-menyn/workflow-badges
- Systemprompten för AI5 ska behållas i databasen för framtida användning
- Ingen kod eller databeroenden ska gå sönder

## Definition of Done

- [ ] AI5 körs inte längre automatiskt i tasks.py efter AI4
- [ ] AI5 visas inte längre i Process.jsx workflow-badges
- [ ] AI5-systemprompten finns kvar i databasen (ai_system_prompts)
- [ ] Inga andra delar av systemet är beroende av att AI5 körs
- [ ] Befintliga poster i ai_processing_history för AI5 påverkas inte
- [ ] Tester körs och passerar (om det finns några för AI5)
- [ ] Dokumentation uppdaterad (MIND_WORKFLOW.md)

## Scope & Constraints

**In scope:**
- Ta bort AI5 från workflow-pipeline i `backend/src/services/tasks.py` (_run_ai_pipeline)
- Ta bort AI5-badge från frontend i `main-system/app-frontend/src/ui/pages/Process.jsx`
- Uppdatera `docs/SYSTEM_DOCS/MIND_WORKFLOW.md` för att reflektera att AI5 inte längre är en del av kvittoflödet
- Verifiera att inga andra beroenden finns (databas, API-endpoints, etc.)

**Out of scope:**
- Ta bort AI5-funktionen helt (den ska finnas kvar för framtida användning)
- Ta bort AI5-systemprompten från databasen
- Ändra AI5-implementationen i ai_service.py eller ai_processing.py
- Ta bort historikdata för AI5

## Links

### Code files
- Backend workflow: [backend/src/services/tasks.py](backend/src/services/tasks.py#L679-L750)
- Frontend workflow display: [main-system/app-frontend/src/ui/pages/Process.jsx](main-system/app-frontend/src/ui/pages/Process.jsx#L1035)
- AI5 implementation: [backend/src/services/ai_service.py](backend/src/services/ai_service.py#L662-L724)
- Workflow documentation: [docs/SYSTEM_DOCS/MIND_WORKFLOW.md](docs/SYSTEM_DOCS/MIND_WORKFLOW.md)

### Related documentation
- [docs/SYSTEM_DOCS/MIND_WORKFLOW.md](docs/SYSTEM_DOCS/MIND_WORKFLOW.md) - Current workflow description

## Labels

backend, frontend, refactoring, medium-priority

## Assignees

@mattiasstjernstrom

## Milestone

v1.1
