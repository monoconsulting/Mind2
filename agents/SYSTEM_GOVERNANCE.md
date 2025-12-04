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

There are two classes of documentation:

1. **System & Architecture Docs (archive-eligible once merged into SoT)**  
   These directories contain system-level descriptions, architecture and design that SHOULD be consolidated into SoT and then archived when fully superseded:
   - `docs/ARCHITECTURE/`
   - `docs/SYSTEM_DOCS/`
   - `docs/DIAGRAMS/`
   - `docs/OPS/`
   - `docs/WORKFLOWS/`

   Rules:
   - When their content has been merged into `docs/source_of_truth/`, the original files must be moved to `docs/archive/<YEAR>/` and marked with a LEGACY header.
   - New system-level instructions must live in SoT, not in these folders.

2. **Working & Activity Logs (must remain active)**  
   These directories are ongoing work surfaces and must NOT be bulk-archived or removed:
   - `docs/features/`
   - `docs/handovers/`
   - `docs/logs/`
   - `docs/tasks/`
   - `docs/worklogs/`

   Rules:
   - Files in these directories are not to be archived automatically.
   - They may only be marked LEGACY in exceptional cases (e.g. a direct duplicate of a SoT file), and such decisions must be documented in `CONFLICTS_AND_DECISIONS.md`.

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