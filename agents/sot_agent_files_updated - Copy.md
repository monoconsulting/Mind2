# Updated SoT Agent Files

This document contains the revised versions of SYSTEM_GOVERNANCE.md and AGENT_SOT_CONSOLIDATOR.md including:
- Separation between archive‑eligible system/docs folders
- Permanent working directories
- Rules for graphic/UI design

You can use this file to overwrite your existing SoT Agent Files in the repo.

---

# /agents/SYSTEM_GOVERNANCE.md

## Global System Governance – Source of Truth Documentation

All agents must comply with these rules.

### A. Principles
1. The Source of Truth (SoT) directory is the *only authoritative documentation*.
2. All changes to architecture, schema, pipelines or statuses must be documented in SoT before or together with code changes.
3. Migrations, code and SoT must never conflict.

### B. Required Structure
```
docs/source_of_truth/
  00_INDEX.md
  10_SYSTEM_OVERVIEW.md
  20_DOMAIN_MODEL_AND_GLOSSARY.md
  30_STATUS_MODEL.md
  40_DATA_MODEL.md
  50_PIPELINES_AND_JOBS.md
  55_API_AND_ENDPOINTS.md
  60_INTEGRATIONS.md
  70_AI_PROMPTS_AND_ROLES.md
  80_OPERATIONS_RUNBOOK.md
  90_TEST_AND_QUALITY_STRATEGY.md

docs/wip/
docs/archive/
```

### C. Consolidation Rules
1. No document may be deleted, only moved to `archive/` and marked as `LEGACY`.
2. No SoT file may contain placeholders.
3. Database schema must fully match `40_DATA_MODEL.md`.
4. All status fields in DB/code must appear in `30_STATUS_MODEL.md`.
5. All pipelines must define input/output and error models.

### D. Documentation Areas and Archiving Policy
There are two categories of documentation:

#### 1. System & Architecture Docs (archive‑eligible once merged into SoT)
These folders contain system‑level design and structure. They may be archived *only after* all relevant content is merged into SoT:
- `docs/ARCHITECTURE/`
- `docs/SYSTEM_DOCS/`
- `docs/DIAGRAMS/`
- `docs/OPS/`
- `docs/WORKFLOWS/`

Rules:
- Once consolidated into SoT, files must be moved to `docs/archive/<YEAR>/`.
- Every archived file must begin with:
  > LEGACY DOCUMENT  
  > This file has been superseded by the Source of Truth documentation in `docs/source_of_truth/`.
- These folders must not contain updated system‑truth once SoT exists.

#### 2. Working & Activity Logs (MUST remain active)
These represent day‑to‑day work and must never be bulk‑archived:
- `docs/features/`
- `docs/handovers/`
- `docs/logs/`
- `docs/tasks/`
- `docs/worklogs/`

Rules:
- Files remain active.
- They may only become LEGACY if they are 1:1 duplicates of SoT content.
- Exceptional archiving requires justification in `CONFLICTS_AND_DECISIONS.md`.

### E. Graphic and UI Design
Graphic/UI design artifacts (Figma, mockups, screenshots) are **not authoritative** for system behaviour or data.

Rules:
- Graphics may be stored in `design/` or `docs/design/`.
- SoT may reference design, but must not copy pixel‑level design.
- Design is *never* authoritative for:
  - database schema
  - statuses
  - workflows
  - APIs
  - behavioural logic
- If design and SoT disagree, SoT overrides design. Design must be updated to match SoT.

---

# /agents/AGENT_SOT_CONSOLIDATOR.md

## Agent 1 – Source of Truth Consolidator

Your mission:
- Follow `SYSTEM_GOVERNANCE.md` exactly with no deviation.
- Inventory all documentation and generate:
  - `docs/wip/DOCUMENT_INVENTORY.md`
- Identify conflicts and generate:
  - `docs/wip/CONFLICTS_AND_DECISIONS.md`
- Build and populate every SoT file:
  - 00, 10, 20, 30, 40, 50, 55, 60, 70, 80, 90
- Ensure:
  - 100% completeness
  - 0% assumptions
  - Traceability to code/migrations
  - All SoT files are complete, validated markdown

### Archiving Rules for Agent 1
You may archive files from the following directories *only after* their content is fully represented in the Source of Truth:
- `docs/ARCHITECTURE/`
- `docs/SYSTEM_DOCS/`
- `docs/DIAGRAMS/`
- `docs/OPS/`
- `docs/WORKFLOWS/`

You must **NOT** archive, rename or relocate files in these active working areas:
- `docs/features/`
- `docs/handovers/`
- `docs/logs/`
- `docs/tasks/`
- `docs/worklogs/`

All archived files:
- Must be placed into `docs/archive/<YEAR>/`
- Must begin with a LEGACY header

### Additional Rules
- You may not add new architecture or design outside SoT.
- You may not re‑interpret or guess missing information.

Output: A complete, correct and fully compliant Source of Truth with protected working documentation preserved.

---

# Other Agent Files (Validator, Monitor, Orchestration)
These remain unchanged from the previous version.

Agent 2 and Agent 3 automatically respect `SYSTEM_GOVERNANCE.md`, and therefore inherit the new archiving and design rules.

---

_End of Updated SoT Agent Files_

