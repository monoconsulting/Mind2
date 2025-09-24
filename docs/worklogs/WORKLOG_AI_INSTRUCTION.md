# AI_INSTRUCTION_Worklog.md

> **Audience:** An AI developer-assistant writing and maintaining a daily rolling worklog.
> **Objective:** Produce accurate, append-only entries with traceability (commit ↔ files ↔ tests ↔ docs), minimal friction for humans.

## Golden Rules
1. **Newest-first:** Insert the latest entry at the **top** of section `## 4) Rolling Log (Newest First)`.
2. **Central parameters mandatory:** Each entry must include: time, title, change type, scope, taskmaster id, branch, commit(s), commands, result summary, exact files changed with line ranges and functions/classes, diffs (minimal), tests executed, system documentation updated, artifacts, and next action.
3. **Exactness over brevity:** Prefer precise file paths, SHAs, and line ranges. If you remove code, it **must** be commented and justified in the log.
4. **Traceability:** Keep `## 13) Stats & Traceability` consistent with entries. Maintain Ticket ↔ Commit ↔ Test mapping.
5. **No secrets:** Redact secrets from env/outputs. Never paste tokens or credentials.
6. **Idempotent behavior:** Do not reformat unrelated parts of the file. Only insert the new entry and update the “Daily Index” line.

## Where to Log
- The worklog file is named `YY-MM-DD_Worklog.md` for the local date (Europe/Stockholm).
- If the file does not exist, create it from the template shipped in this package.

## Required Entry Schema
Represent mentally like this (do **not** add YAML to the worklog):
```yaml
entry:
  time: "HH:MM"  # 24h local time
  title: "Short Title"
  change_type: [feat|fix|chore|docs|perf|refactor|test|ops]
  scope: "<component/module>"
  tickets: ["ABC-123", "PR#45"]
  branch: "feature/x"
  commits: ["a1b2c3d", "e4f5g6h"]
  environment: "docker:compose-profileX" # optional
  commands: ["pytest -q", "playwright test --reporter=list"]
  result_summary: "1–3 lines outcome"
  files_changed:
    - path: "src/x.py"
      lines: "L42–L67"
      symbols: ["func_a", "ClassB.method_c"]
    - path: "docs/arch/overview.md"
      lines: "L10–L25"
      symbols: []
  diff: | # minimal unified or per-file blocks
    --- a/src/x.py
    +++ b/src/x.py
    @@ -42,6 +42,8 @@
  tests_executed: "pytest ... / playwright ... results"
  perf_note: "p95 220ms → 180ms"
  docs_updated: ["docs/arch/overview.md: updated sequence diagram"]
  artifacts: ["artifacts/pytest.html", "screenshots/2025-08-19/test.png"]
  next_action: "Open PR and request review"
```

## How to Collect Data (Commands)
Use only local tooling; do **not** fetch remote secrets.

### Git & Files
- **Branch:** `git rev-parse --abbrev-ref HEAD`
- **Latest commit short SHA:** `git rev-parse --short HEAD`
- **Changed files (working tree):** `git diff --name-only`
- **Changed files (staged):** `git diff --cached --name-only`
- **Last commit files:** `git diff --name-only HEAD~1..HEAD`
- **Minimal diff (whole working tree):** `git diff -U3`
- **Per-file diff:** `git diff -U3 -- <relative/path>`
- **Line ranges & symbols:** When you edit, record the approx. line spans and the function/class names touched. If uncertain, open the file and derive line numbers directly.

### Documentation Files
Treat files under `docs/`, `documentation/`, `doc/`, and root `README.md` as **system documentation**. If any are changed, list them under **System documentation updated** with a short note.

### Tests & Evidence
- Run unit tests: `pytest -q` (or with coverage: `pytest --maxfail=1 -q --cov=...`)  
- Run e2e: `playwright test --reporter=list`  
- Save artifacts: HTML reports, screenshots, and logs into a predictable folder (e.g., `artifacts/` or `screenshots/`). Reference paths in the entry.

### Performance
If you changed performance-sensitive code, gather before/after metrics with the smallest representative benchmark you have. Include p95, CPU, and memory deltas in the entry or section **9) Performance & Benchmarks**.

### Database & Migrations
If schema changes occurred, reference the migration files and provide **forward** and **rollback** SQL snippets in sections 6 and 14.

## Update the Daily Index
Add or update a single row at the top of the index table:
```
| HH:MM | <Short Title> | <change_type> | `<scope>` | ABC-123 | `a1b2c3d` | path1, path2 |
```
Keep the table header intact. Only insert one new row per entry at the top.

## Insertion Algorithm (High-level)
1. Read `YY-MM-DD_Worklog.md` into memory.
2. Find the marker line: `## 4) Rolling Log (Newest First)`.
3. Find the first blank line after the **Entry Template** block that says: "Place your first real entry here". Insert your new entry **immediately below** that marker (or above the previous newest entry if one exists).
4. Update the **Daily Index** table by inserting a single row directly below its header.
5. Do **not** modify any other sections.

## Example Entry (Compact)
```markdown
#### [14:05] Fix: null check for transcript parser
- **Change type:** fix
- **Scope (component/module):** `transcripts/parser`
- **Tickets/PRs:** ABC-123
- **Branch:** `bugfix/null-guard`
- **Commit(s):** `9f3a7c1`
- **Environment:** docker:compose=dev
- **Commands run:**
  ```bash
  pytest -q
```
- **Result summary:** All unit tests pass (56 total). Parser no longer crashes on empty segments.
- **Files changed (exact):**
  - `src/transcripts/parser.py` — L88–L104 — functions/classes: `parse_chunk`
- **Unified diff (minimal, per file or consolidated):**
  ```diff
  --- a/src/transcripts/parser.py
  +++ b/src/transcripts/parser.py
  @@ -88,6 +88,10 @@ def parse_chunk(chunk):
  +    if chunk is None:
  +        return []  # guard: handle empty chunk safely
  ```
- **Tests executed:** `pytest -q` → 56 passed
- **Performance note (if any):** N/A
- **System documentation updated:**
  - `docs/arch/transcript-flow.md` — clarified empty-chunk handling
- **Artifacts:** `artifacts/pytest_2025-08-19.html`
- **Next action:** Open PR for review
```

## Included Helper Scripts
- `tools/add_worklog_entry.ps1` — PowerShell helper that **generates an entry block** (to console and `.worklog_generated/`) using Git data.
- `tools/add_worklog_entry.sh` — Bash helper that does the same on Linux/macOS/WSL.

> These scripts **do not edit files automatically**; they produce an entry block for you to paste at the top of the Rolling Log and add a row to the Daily Index. This keeps edits deliberate and avoids unintended formatting changes.

## Failure Handling
- If Git commands fail, state that explicitly in the entry (e.g., "Git unavailable"), and proceed with manual details.
- If tests are flaky, mark them as flaky and provide a link/ID. Do not delete or suppress failures silently.

---
**End of AI instruction.**
