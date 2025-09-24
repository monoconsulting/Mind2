# YY-MM-DD_Worklog.md — Daily Engineering Worklog Template

> **Usage:** Save this file as `YY-MM-DD_Worklog.md` (e.g., `25-08-19_Worklog.md`). This template is **rolling/blog-style**: add small entries **as you work**, placing the **newest entry at the top** of the Rolling Log. **Also read and follow `AI_INSTRUCTION_Worklog.md` included in this package.** Fill every placeholder. Keep exact identifiers (commit SHAs, line ranges, file paths, command outputs). Never delete sections—if not applicable, write `N/A`.

---

## 0) TL;DR (3–5 lines)

- **What changed:** 
- **Why:** <primary reason / ticket>
- **Risk level:** <Low/Medium/High>
- **Deploy status:** <Not started / In progress / Done>

---

## 1) Metadata

- **Date (local):** <YYYY-MM-DD, Europe/Stockholm>
- **Author:** 
- **Project/Repo:** <org/repo>
- **Branch:** 
- **Commit range:** <BASE_SHA>..<HEAD_SHA>
- **Related tickets/PRs:** 
- **Template version:** 1.1

---

## 2) Goals for the Day

- 

**Definition of done today:** 

---

## 3) Environment & Reproducibility

- **OS / Kernel:** <e.g., Windows 11 24H2, WSL2 Ubuntu 22.04>
- **Runtime versions:** <Python X, PHP Y, Node Z, MySQL X>
- **Containers:** <image:tag, compose profile>
- **Data seeds/fixtures:** 
- **Feature flags:** <enabled/disabled flags>
- **Env vars touched:** `NAME=...` (values redacted if sensitive)

**Exact repro steps:**

1. `git checkout <branch>`
2. `git pull --rebase`
3. 

**Expected vs. actual:**

- *Expected:* <...>
- *Actual:* <...>

---

## 4) Rolling Log (Newest First)

> Add each work item as a compact **entry** while you work. **Insert new entries at the top** of this section. Each entry must include the central parameters below and explicitly list any **system documentation files** updated.

### Daily Index (auto-maintained by you)

| Time | Title | Change Type | Scope | Tickets | Commits | Files Touched |
|---|---|---|---|---|---|---|
| [HH:MM](HH:MM) |  | <feat/fix/chore/docs/perf/refactor/test/ops> | `<component/module>` | ABC-123 | `a1b2c3d` | `src/x.py, docs/arch/...` |

### Entry Template (copy & paste below; newest entry goes **above** older ones)
```markdown
#### [<HH:MM>] <Short Title>
- **Change type:** <feat/fix/chore/docs/perf/refactor/test/ops>
- **Scope (component/module):** `<component>`
- **Tickets/PRs:** <IDs with links>
- **Branch:** `<branch>`
- **Commit(s):** `<short SHA(s)>`
- **Environment:** <runtime/container/profile if relevant>
- **Commands run:**
  ```bash
  <command one>
  <command two>
  ```
- **Result summary:** <1–3 lines outcome>
- **Files changed (exact):**
  - `<relative/path.ext>` — L<start>–L<end> — functions/classes: `<names>`
  - …
- **Unified diff (minimal, per file or consolidated):**
  ```diff
  --- a/<path>
  +++ b/<path>
  @@ -<start>,<len> +<start>,<len> @@
  -<removed>
  +<added>
  ```
- **Tests executed:** <pytest/playwright commands + brief pass/fail>
- **Performance note (if any):** <metric before → after>
- **System documentation updated:**
  - `<docs/.../file.md>` — <what changed>
- **Artifacts:** <screenshots/logs/report paths>
- **Next action:** <what to do next>
```

> Place your first real entry **here** ⬇️ (and keep placing new ones above the previous):

---

## 5) Changes by File (Exact Edits)
> For each file edited today, fill **all** fields. Include line ranges and unified diffs. If lines were removed, include rationale and reference to backup/commit.

### 5.<n>) `<relative/path/to/file.ext>`
- **Purpose of change:** <why>
- **Functions/Classes touched:** <names>
- **Exact lines changed:** <e.g., L42–L67, L120>
- **Linked commit(s):** <short SHA(s)>
- **Before/After diff (unified):**
```diff
--- a/<path>
+++ b/<path>
@@ -<start>,<len> +<start>,<len> @@
-<removed line>
+<added line>
```
- **Removals commented & justification:** 
- **Side-effects / dependencies:** <e.g., API, DB, config>

> Repeat subsection 5.<n> for every modified file.

---

## 6) Database & Migrations

- **Schema objects affected:** <tables, columns, indexes>
- **Migration script(s):** <file path(s)>
- **Forward SQL:**
```sql
-- migration up
```
- **Rollback SQL:**
```sql
-- migration down
```
- **Data backfill steps:** <commands/SQL>
- **Verification query/results:**
```sql
-- SELECT ... ;  -- paste minimal result sample
```

---

## 7) APIs & Contracts

- **New/Changed endpoints:** <method, path>
- **Request schema:** 
- **Response schema:** 
- **Backward compatibility:** <Yes/No — explain>
- **Clients impacted:** <services/UI>

---

## 8) Tests & Evidence

- **Unit tests added/updated:** 
- **Integration/E2E:** 
- **Coverage:** lines <x%>, branches <y%> (attach report path)
- **Artifacts:** <screenshots dir, HTML reports, logs>
- **Commands run:**
```bash
pytest -q
playwright test --reporter=list
```
- **Results summary:** <pass/fail counts>
- **Known flaky tests:** 

---

## 9) Performance & Benchmarks

- **Scenario:** 
- **Method:** <tool, dataset, iterations>
- **Before vs After:**
| Metric | Before | After | Δ | Notes |
|---|---:|---:|---:|---|
| p95 latency (ms) |  |  |  |  |
| CPU (%) |  |  |  |  |
| Memory (MB) |  |  |  |  |

---

## 10) Security, Privacy, Compliance

- **Secrets handling:** <none/updated .env.example>
- **Access control changes:** <roles, policies>
- **Data handling:** <PII/PHI touched?>
- **Threat/abuse considerations:** 

---

## 11) Issues, Bugs, Incidents

- **Symptom:** <error message / behavior>
- **Impact:** 
- **Root cause (if known):** 
- **Mitigation/Workaround:** 
- **Permanent fix plan:** <steps + owner>
- **Links:** <issue IDs, logs>

---

## 12) Communication & Reviews

- **PR(s):** 
- **Reviewers & outcomes:** <who, summary>
- **Follow-up actions requested:** 

---

## 13) Stats & Traceability

- **Files changed:** 
- **Lines added/removed:** + / -
- **Functions/classes count (before → after):** <n → m>  
  *(If functions removed, list each and reason; link to commit preserving prior code.)*
- **Ticket ↔ Commit ↔ Test mapping (RTM):**
| Ticket | Commit SHA | Files | Test(s) |
|---|---|---|---|
| ABC-123 | `abcdef1` | `src/x.py` | `tests/test_x.py::test_ok` |

---

## 14) Config & Ops

- **Config files touched:** 
- **Runtime toggles/flags:** 
- **Dev/Test/Prod parity:** 
- **Deploy steps executed:** <commands, target env>
- **Backout plan:** 
- **Monitoring/alerts:** <dashboards, thresholds>

---

## 15) Decisions & Rationale (ADR-style snippets)

- **Decision:** 
- **Context:** 
- **Options considered:** <A/B/C>
- **Chosen because:** 
- **Consequences:** 

---

## 16) TODO / Next Steps

- 

---

## 17) Time Log
| Start | End | Duration | Activity |
|---|---|---|---|
| 08:00 | 09:30 | 1h30 | Investigated failing tests |

---

## 18) Attachments & Artifacts

- **Screenshots:** `<path/to/screenshots/>`
- **Logs:** `<path/to/logs/>`
- **Reports:** `<path/to/report.html>`
- **Data samples (sanitized):** `<path>`

---

## 19) Appendix A — Raw Console Log (Optional)
```text
<paste trimmed console output>
```

## 20) Appendix B — Full Patches (Optional)
```diff
<if large diffs needed inline>
```

---

> **Checklist before closing the day:**
> - [ ] All edits captured with exact file paths, line ranges, and diffs.
> - [ ] Tests executed with evidence attached.
> - [ ] DB changes documented with rollback.
> - [ ] Config changes and feature flags recorded.
> - [ ] Traceability matrix updated.
> - [ ] Backout plan defined.
> - [ ] Next steps & owners set.
