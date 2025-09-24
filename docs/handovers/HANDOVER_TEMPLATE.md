# AGENT HANDOVER TEMPLATE (ENGLISH)

> **How to use this template**
>  **Copy this file** to your repository as:
>  `/docs/handovers/HANDOVER_TM<task-id>-<short-desc>_<YYYY-MM-DD>.md`
>  Example: `/docs/handovers/HANDOVER_TM167-QueueRefactor_2025-09-07.md`
>  Keep this document updated during the task. At handover time, ensure all checkboxes below are ✅.

## 1) Handover Metadata

- **Project**:
- **Repository URL**:
- **Task / Ticket**: TM — 
- **Scope Status**: Green / Yellow / Red (pick one)
- **Branch**: `TM<id>-<short-desc>`
- **Base Branch**: `dev`
- **Latest Commit SHA on feature**:
- **Merged PR → dev**: 
- **Safety Tag on dev**: <`TM<id>-handover` link>
- **Handover Date/Time (UTC+1/UTC+2)**:
- **Agent (Name/Model/Version)**:
- **Contact / next-responsible**:

------

## 2) Executive Summary

- **Goal / objective**: One‑paragraph purpose of the task.
- **Current outcome**: What works, what is partial, what is pending.
- **Top risks & blockers**: bullets with severity (High/Med/Low).
- **Immediate next steps** (first 3 things successor should do):
   1.
   2.
   3.

------

## 3) Scope & Acceptance

- **In scope**: bullet list of functions, files, services touched.
- **Out of scope / Non‑goals**: explicit list.
- **Acceptance criteria**: list the exact pass conditions used for testing.

------

## 4) Changes Introduced (High‑Level)

- Feature(s) added:
- Behavior changes:
- Feature flags / toggles:
- Config changes (env vars / ports / files):

------

## 5) Code Diff Summary

> Provide a concise map of changed artifacts. Do not delete unrelated code.

| Path        | Change Type                            | Reason                       | Notes                       |
| ----------- | -------------------------------------- | ---------------------------- | --------------------------- |
| `src/...`   | Modified                               | Bug fix / Refactor / Feature |                             |
| `src/...`   | **Commented‑out (instead of deleted)** | Replaced by X                | Rationale documented inline |
| `tests/...` | Added/Updated                          | Coverage for X               |                             |

**Breaking changes**: Yes/No (if Yes, detail)

------

## 6) Database & Migrations

- **DB engine(s)**: MySQL / PostgreSQL / SQLite (choose)
- **Migrations applied**: id → description
- **Pending migrations**: id → description
- **Schema changes**: tables/columns/indexes
- **Seed/Test data**: how to load
- **Rollback plan**: commands and verification steps

------

## 7) Environment & Configuration

- **OS & Runtimes**: Windows/Linux; Python X.Y / PHP X.Y / Node X.Y
- **Containers**: Docker Compose services impacted
- **Ports**: service → port; confirm against **ATLAS port registry** if applicable
- **Env vars** (added/changed): `NAME` → purpose (do not include secrets)
- **Secrets handling**: where/how stored (vault/.env.local), rotation plan
- **Volumes / paths**: host ↔ container mappings

------

## 8) Build, Run, and Reproduce

- **Clean setup** (from fresh clone):
  1. `git checkout dev && git pull`
  2. `git checkout TM<id>-<short-desc>`
  3. Install deps: commands for Python/PHP/Node
  4. Start services: `docker compose up -d` (or equivalent)
  5. Initialize DB/migrations
  6. Load dev data (if any)
- **One‑line repro** (if applicable): command to reproduce key behavior/bug

------

## 9) Testing & Quality Gates

- **Test commands executed**:
- **Results summary**: pass/fail counts
- **Coverage**: overall %, critical modules %
- **Linters/Formatters**: results (flake8/black, eslint/prettier, phpstan/phpcs)
- **Static analysis**: SonarQube project key, last analysis time, critical issues
- **Security**: `pip-audit` / `npm audit` / `composer audit` highlights
- **Artifacts**: paths to HTML/JUnit reports

------

## 10) API & Contracts

- **Endpoints added/changed/deprecated** (method, path, auth, summary)
- **Request/response examples**: link or inline minimal JSON
- **Backward compatibility notes**

------

## 11) Data Flow & Integration Notes

- **Upstream dependencies** (who calls us)
- **Downstream dependents** (we call whom)
- **Queues/cron/webhooks** in play
- **Known cross‑service impacts**

------

## 12) Logs, Evidence, and Screenshots

List paths/links to:

- Build logs
- Runtime logs
- Failing test output
- Screenshots/video of key flows

------

## 13) Open Issues & Risks

| ID   | Title | Severity | Owner | Status | Link |
| ---- | ----- | -------- | ----- | ------ | ---- |
|      |       |          |       |        |      |

------

## 14) Next‑Agent Playbook (First 24–48h)

1. Verify environment with commands X/Y/Z
2. Run test suite and confirm same results
3. Address blockers A/B/C
4. Implement next increment …

------

## 15) Backout / Recovery Plan

- Exact commands to revert to safety tag and redeploy
- Data migration rollback and verification

------

## 16) Artifacts Package (attach or link)

- `handover.json` (see schema below) populated with all fields
- PR link and `git diff` (against `dev`)
- Test/coverage reports
- SonarQube HTML or link
- Logs & screenshots

------

## 17) Policy Reminders (Do‑Not‑Break Rules)

- Do **not** delete, overwrite, or rename existing code/files unless explicitly approved; **comment out** and document rationale.
- No force‑push, no history rewrites, no destructive cleanups.
- Before risky edits: create a safety tag/branch; after changes, ensure the diff only adds or comments code.
- When stuck: **STOP and preserve** — code preservation outranks speed.

------

## 18) Changelog

| Version | Date       | Changes          |
| ------- | ---------- | ---------------- |
| 0.9     | 2025‑09‑07 | Initial template |

------

## Appendix A — `handover.json` Schema (machine‑readable)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AgentHandover",
  "type": "object",
  "required": ["project", "taskId", "branch", "commit", "prUrl", "status", "nextSteps"],
  "properties": {
    "project": {"type": "string"},
    "repositoryUrl": {"type": "string"},
    "taskId": {"type": "string", "pattern": "^TM[0-9]+$"},
    "title": {"type": "string"},
    "status": {"type": "string", "enum": ["green", "yellow", "red"]},
    "branch": {"type": "string"},
    "baseBranch": {"type": "string", "default": "dev"},
    "commit": {"type": "string"},
    "prUrl": {"type": "string", "format": "uri"},
    "safetyTag": {"type": "string"},
    "handoverAt": {"type": "string", "format": "date-time"},
    "agent": {"type": "object", "properties": {"name": {"type": "string"}, "model": {"type": "string"}, "version": {"type": "string"}}},
    "summary": {"type": "string"},
    "inScope": {"type": "array", "items": {"type": "string"}},
    "outOfScope": {"type": "array", "items": {"type": "string"}},
    "acceptanceCriteria": {"type": "array", "items": {"type": "string"}},
    "changes": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "changeType": {"type": "string"}, "reason": {"type": "string"}}}},
    "db": {"type": "object", "properties": {"engine": {"type": "string"}, "appliedMigrations": {"type": "array", "items": {"type": "string"}}, "pendingMigrations": {"type": "array", "items": {"type": "string"}}}},
    "env": {"type": "object", "properties": {"runtimes": {"type": "object"}, "ports": {"type": "array", "items": {"type": "string"}}, "envVars": {"type": "array", "items": {"type": "string"}}}},
    "buildRun": {"type": "array", "items": {"type": "string"}},
    "tests": {"type": "object", "properties": {"commands": {"type": "array", "items": {"type": "string"}}, "result": {"type": "string"}, "coverage": {"type": "number"}}},
    "api": {"type": "array", "items": {"type": "object", "properties": {"method": {"type": "string"}, "path": {"type": "string"}, "notes": {"type": "string"}}}},
    "logs": {"type": "array", "items": {"type": "string"}},
    "issues": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "severity": {"type": "string"}}}},
    "nextSteps": {"type": "array", "items": {"type": "string"}},
    "backoutPlan": {"type": "array", "items": {"type": "string"}}
  }
}
```

------

## Appendix B — Quick Handover Checklist (tick all)

-  Feature branch from `dev` with correct name `TM<id>-<short-desc>`
-  PR merged to `dev` (no unrelated changes, no deletions)
-  Safety tag `TM<id>-handover` pushed
-  All tests & linters executed; reports attached
-  Sonar/static analysis up to date
-  DB migrations documented (applied/pending/rollback)
-  Repro steps from clean clone verified
-  Logs/screenshots attached
-  `handover.json` produced and linked in Artifacts
-  Next‑Agent Playbook filled with first 3 steps
