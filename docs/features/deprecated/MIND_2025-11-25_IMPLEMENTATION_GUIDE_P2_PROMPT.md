Below is your **machine-tight, agent-ready P0 implementation prompt**, formatted exactly for use in VS Code, your automation framework, or GitHub Copilot Agents.

It references the uploaded codebase at:

```
/mnt/data/codebase_251125_12-35.zip
```

You can paste this prompt **as-is** into your agent.
It contains strict rules, scope enforcement, and step-by-step instructions.

---

# ✅ **AGENT PROMPT – P0 MIGRATIONS & WORKFLOW BASELINE**

**Repository archive:** `/mnt/data/codebase_251125_12-35.zip`
**Scope:** *Migrations, schema consistency, status centralization. Zero behavioural change.*

---

## 0. **GLOBAL RULES – YOU MUST OBEY THESE**

1. **You MUST NOT create new features.**
   Only refactor for consistency, structure, and correctness.

2. **You MUST NOT delete code.**
   If you retire code, you must:

   * Comment out the old code.
   * Add a clear explanation block above it.
   * Reference the new canonical file/module.

3. **You MUST NOT invent data, SQL, schema, or values.**
   All status values and schema elements must come from:

   * `/database/migrations/*.sql`
   * `/backend/migrations/*.sql`
   * Code in the repository.

4. **You MUST preserve ALL behaviour.**
   API output, status values, workflows, and side effects must remain identical.

5. **Zero mock data.**
   Never seed or fabricate sample rows.

6. **If your work touches a file, you MUST add an explanation comment at the top**
   describing why that file needs modification.

7. **All changes must be atomic, minimal, and precisely scoped to P0**
   (Migrations & Workflow Status Baseline).

8. **All tests must pass after your changes.**

---

## 1. **REPOSITORY STRUCTURE YOU MUST WORK WITH**

### Canonical migration directory:

```
database/migrations/
```

### Extra/backend migrations:

```
backend/migrations/
```

### Migration runner:

```
backend/src/services/db/migrations.py
```

### Workflow & status code:

```
backend/src/api/*
backend/src/services/tasks/*
backend/src/services/db/*
backend/src/models/*
```

---

# 2. **YOUR TASKS FOR P0**

## **P0.1 – MIGRATION CANONICALIZATION & VALIDATION**

### **P0.1.1 – Confirm canonical directory & runner**

You MUST ensure the canonical migrations directory is:

```
database/migrations
```

Steps:

1. Open `backend/src/services/db/migrations.py`.
2. Confirm `_resolve_migrations_dir()` resolves correctly in:

   * repo mode → `database/migrations`
   * container mode → `/app/database/migrations`
3. DO NOT alter this behaviour.
4. DO NOT add support for `backend/migrations`.

---

### **P0.1.2 – Add migration sequence validator**

You MUST implement a validator in `backend/src/services/db/migrations.py`:

* Validate:

  * Filenames match: `NNNN_name.sql`
  * No duplicated numbers
  * No invalid patterns

* Raise `ValueError` with a clear message if invalid.

**You MUST integrate the validator at the top of `apply_migrations()`.**

### Example (your implementation may differ but must match behaviour):

```python
MIGRATION_NAME_PATTERN = re.compile(r"^(\d{4})_(.+)\.sql$")

def validate_migration_sequence(files):
    numbers = {}
    invalid = []

    for path in files:
        m = MIGRATION_NAME_PATTERN.match(path.name)
        if not m:
            invalid.append(path.name)
            continue
        num = int(m.group(1))
        numbers.setdefault(num, []).append(path.name)

    if invalid:
        raise ValueError(f"Invalid migration filenames: {', '.join(invalid)}")

    duplicates = {k:v for k,v in numbers.items() if len(v) > 1}
    if duplicates:
        raise ValueError(
            "Duplicate migration numbers detected: " +
            "; ".join(f"{k}: {', '.join(v)}" for k,v in duplicates.items())
        )
```

You MUST call `validate_migration_sequence()` before running migrations.

---

### **P0.1.3 – Reconcile duplicated or backend migrations**

There are duplicate migration numbers, including:

```
database/migrations/0007_add_ai_accounting_proposals.sql
database/migrations/0007_add_ai_llm_tables.sql

database/migrations/0031_add_ocr_raw_to_creditcard_invoices.sql
database/migrations/0031_create_workflow_tracking.sql
```

You MUST:

1. Create **new** canonical migration files for any duplicates, renumbering **forward only**, e.g.:

```
0034_add_ai_llm_tables.sql
0035_add_ocr_raw_to_creditcard_invoices.sql
```

2. For each deprecated file:

   * Keep it in repo.
   * Comment out its contents.
   * Add a header:

```sql
-- DEPRECATED: Superseded by <new-file>.sql
-- This file is kept for historical reference only.
-- It MUST NOT be executed by the migration runner.
```

3. You MUST NOT remove any SQL content—it stays as commented historical code.

4. You MUST update nothing except naming and comments.

5. You MUST NOT alter behaviour of production DB when applying migrations.

> Note: Because migration system already handles idempotent operations, reordering/renumbering is safe.

---

### **P0.1.4 – Handle non-SQL file in migrations directory**

There is a documentation file:

```
database/migrations/0015_QUICKSTART.md
```

You MUST:

* Add a header to `0015_QUICKSTART.md`:

```markdown
> NOTE: Documentation only. Do NOT rename to .sql.
> Present here to preserve schema commentary. Not executed by migration runner.
```

You MUST NOT move or delete the file.

---

### **P0.1.5 – Keep seed_demo disabled**

Near bottom of `apply_migrations()`:

```python
if False and seed_demo:
    ...
```

You MUST NOT modify behaviour.
You MAY clarify the comment, but MUST NOT enable the block.

---

### **P0.1.6 – Migration regression alignment**

You MUST ensure:

* Running all migrations in canonical order produces a schema compatible with the production dump at:

```
.dbbackup/Mind2_mono_se_db_9_2025-11-25_12-34.sql
```

If a column/table exists in production but not in migrations:

* Create a new forward migration to add it.

DO NOT modify old migrations.

---

## **P0.2 – WORKFLOW STATUS CENTRALIZATION**

### **P0.2.1 – Status inventory**

You MUST extract ALL status values used across the codebase:

* unified_files.ai_status
* workflow_runs.status
* workflow_stage_runs.status
* creditcard_* tables
* ReceiptStatus enum
* Any custom per-task statuses

Sources include:

```
backend/src/api/*
backend/src/services/tasks/*
backend/src/services/db/*
backend/src/models/*
```

You MUST create a documentation block inside:

```
docs/SYSTEM_DOCS/MIND_WORKFLOW.md
```

Format:

```
### Canonical Status Inventory (Generated in P0)

<list all statuses and where they appear in code/schema>
```

No invented values allowed.

---

### **P0.2.2 – Create central enums module**

You MUST create:

```
backend/src/models/statuses.py
```

Containing enums:

* WorkflowRunStatus
* WorkflowStageStatus
* AIStatus
* CreditCardInvoiceStatus

You MUST use **only** values found in P0.2.1.

Example structure:

```python
class WorkflowRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
```

Repeat for all discovered statuses.

---

### **P0.2.3 – Replace hardcoded strings with enums (write operations only)**

You MUST replace all **write-side** uses of raw strings such as:

```python
status = "queued"
```

WITH:

```python
from models.statuses import WorkflowRunStatus

status = WorkflowRunStatus.QUEUED.value
```

You MUST NOT modify API output formatting.
You MUST NOT modify DB schema.

---

### **P0.2.4 – Connect AI and credit card statuses to enums**

Replace:

```python
ai_status="processing"
```

with:

```python
ai_status=AIStatus.PROCESSING.value
```

Repeat for all credit card flows.

---

### **P0.2.5 – Add regression tests**

You MUST update or add tests to:

```
backend/tests/unit
backend/tests/integration
```

Tests MUST verify:

* No API behavioural changes.
* Status strings returned to clients are unchanged.
* Workflow transitions still function.

You MUST NOT introduce new test data or mock structures.

---

# ❗ FINAL REQUIREMENTS

* You MUST complete the entire P0 plan.
* You MUST keep every change atomic and documented.
* You MUST NOT modify functionality.
* You MUST NOT introduce new behaviours.
* You MUST keep old files intact, commented, and documented.
* All tests MUST pass.