Below is your **full, strict, machine-readable P1 Agent Prompt**, written in the exact same style and format as the P0 prompt.
This is ready to paste directly into VS Code, Cursor, GitHub Copilot Agents, or your automation environment.

It references the attached repository archive:

```
/mnt/data/codebase_251125_12-35.zip
```

---

# ✅ **AGENT PROMPT – P1 INGESTION & FILE LIFECYCLE REFACTOR**

**Repository archive:** `/mnt/data/codebase_251125_12-35.zip`
**Scope:** *Unify FTP ingestion + centralize unified_files creation. Zero behavioural changes.*

---

# 0. GLOBAL RULES – YOU MUST OBEY THESE

1. **You MUST NOT change user-visible behaviour.**

   * All FTP ingestion must behave the same.
   * All created `unified_files` rows must be identical to before the refactoring.
   * All schedules, tasks, and workflow triggers must remain identical.

2. **You MUST NOT delete any code.**

   * If you replace something, **comment it out** and add a clear explanatory block (English).
   * You MUST clearly mark old code as *Deprecated – Replaced by unified implementation*.

3. **You MUST NOT invent new logic, values, defaults, or interpretations.**

   * FTP directory paths must stay the same.
   * Filtering rules must stay the same.
   * Company assignments must stay the same.
   * file_type and source_channel detection must stay the same.

4. **You MUST preserve every existing public function signature.**

   * All functions called by tasks or API endpoints must remain callable in the same way.

5. **You MUST isolate P1 changes to:**

   * FTP ingestion modules
   * File creation & storage modules
   * Optional workflow hook
     Nothing else.

6. **If you touch a file, you MUST add a comment at the top:**
   `# MODIFIED IN P1: <short explanation>`

   * You MUST keep this minimal and factual.

7. **All tests MUST pass after your modifications.**

8. **No mock data, no dummy files, no made-up examples.**

   * Everything MUST use real behaviour extracted from the codebase.

---

# 1. RELEVANT DIRECTORIES IN THIS REPO

You MUST work with the following modules inside the uploaded codebase:

### FTP-related ingestion modules:

```
backend/src/services/fetch_ftp.py
backend/src/services/fetch_ftp_enhanced.py
backend/src/services/fetch_ftp_updated.py
backend/src/services/fetch_ftp_backup.py
```

### File DB & storage modules:

```
backend/src/services/db/files.py
backend/src/services/storage.py
backend/src/services/file_detection.py
backend/src/services/ocr.py
```

### API ingestion modules:

```
backend/src/api/ingest.py
backend/src/api/fetcher.py
backend/src/api/receipts.py
```

### Task modules relying on FTP ingestion:

```
backend/src/services/tasks/file_management_tasks.py
backend/src/services/tasks/workflow_tasks.py
backend/src/services/tasks/invoice_tasks.py
backend/src/services/tasks/ocr_tasks.py
```

### Database tables implicated in P1:

```
unified_files
file_locations
file_categories
file_suffix
workflow_runs (optional)
workflow_stage_runs (optional)
```

You MUST NOT modify unrelated files.

---

# 2. YOUR OBJECTIVE FOR P1

Implement the following **without changing external behaviour**:

1. **Unify all FTP ingestion logic into one canonical implementation**
2. **Centralize unified_files creation into a single DB-layer function**, including deduplication logic
3. **Ensure all ingestion paths (FTP + uploads) go through this single function**
4. *(Optional P1 step)* If existing behaviour expects workflow_runs creation when a file is created, centralize this into a small helper

---

# 3. DETAILED STEPS YOU MUST FOLLOW

---

## **P1.1 — UNIFY FTP INGESTION**

### **P1.1.1 – Analyze and inventory all existing FTP ingestion behaviour**

You MUST read and document internally:

* How each FTP module connects to remote hosts
* How files/directories are enumerated
* How filtering, extensions, and company routing are done
* How metadata is extracted
* How downloaded files are passed to DB/storage
* How errors are handled (critical vs non-critical)

You MUST NOT change behaviour here. Only analyze.

---

### **P1.1.2 – Create unified FTP ingestion module**

You MUST create:

```
backend/src/services/fetch_ftp_unified.py
```

At the top include comment:

```python
# CREATED IN P1: Unified FTP ingestion module consolidating logic from fetch_ftp*, replacing multiple old implementations.
```

Inside, you MUST define:

```python
@dataclass
class FTPSourceConfig:
    host: str
    port: int
    username: str
    password: str
    remote_base_dir: str
    use_tls: bool
    timeout: int
```

And:

```python
@dataclass
class FetchedFile:
    local_path: str
    original_path: str
    original_filename: str
    company_id: Optional[int]
    source_channel: str
    category_key: Optional[str]
    metadata: dict
```

And a main ingestion function:

```python
def fetch_all_from_source(config: FTPSourceConfig) -> List[FetchedFile]:
    """Unified FTP ingestion. Must match behaviour of all legacy modules."""
```

**You MUST port existing logic directly**, preserving:

* file filtering
* directory traversal
* filename logic
* metadata interpretation
* error-handling semantics
* TLS behaviour

---

### **P1.1.3 – Replace old FTP modules with “thin wrappers”**

For each module:

```
fetch_ftp.py
fetch_ftp_enhanced.py
fetch_ftp_updated.py
fetch_ftp_backup.py
```

You MUST:

1. Add at top:

```python
# MODIFIED IN P1: Delegates to unified FTP ingestion module.
```

2. Comment out old implementation:

```python
# DEPRECATED IN P1:
# def old_ftp_logic(...):
#     <entire old code kept as-is in comments>
```

3. Replace with wrapper:

```python
from services.fetch_ftp_unified import FTPSourceConfig, fetch_all_from_source

def fetch_files_for_<purpose>():
    """P1: Legacy wrapper preserved for API/task compatibility."""
    config = FTPSourceConfig(
        host=...,
        port=...,
        username=...,
        password=...,
        remote_base_dir=...,
        use_tls=...,
        timeout=...,
    )
    return fetch_all_from_source(config)
```

4. Wrap any follow-up logic (file classification, DB insertion, task scheduling) exactly as it was before.

**You MUST ensure ALL old entry points still behave identically to external callers.**

---

## **P1.2 — CENTRALIZE FILE CREATION IN unified_files**

### **P1.2.1 – Add a canonical data class**

In:

```
backend/src/services/db/files.py
```

Add:

```python
@dataclass
class NewUnifiedFile:
    company_id: Optional[int]
    file_type: str
    source_channel: str
    original_filename: str
    storage_path: str
    content_hash: Optional[str]
    metadata: Dict[str, Any]
```

---

### **P1.2.2 – Add a single public function create_unified_file()**

Inside `files.py`, create:

```python
def create_unified_file(new_file: NewUnifiedFile) -> int:
    """
    MODIFIED IN P1:
    Canonical file creation path for unified_files.

    MUST preserve:
    - identical initial ai_status
    - identical process_status
    - identical source_channel behaviour
    - identical deduplication logic (if present)
    - identical handling of file_type / metadata
    """
```

You MUST:

* Implement deduplication exactly as in legacy code
* Preserve old behaviour for duplicates (return existing id OR raise DuplicateFileError)
* Preserve ai_status default values (e.g. “new”)
* Preserve process_status default values
* Preserve metadata formatting if JSON is stored
* Preserve file_location logic

You MUST copy old SQL logic into comments above the new implementation.

---

### **P1.2.3 – Replace all direct unified_files insertions**

You MUST:

1. Search for any SQL like:

   ```
   INSERT INTO unified_files
   ```
2. Replace those with calls to:

   ```
   create_unified_file(...)
   ```
3. Add comment above each replaced section:

```python
# P1: Legacy inline unified_files insert replaced by create_unified_file().
# Old SQL preserved below:
# INSERT INTO unified_files (...)
# VALUES (...);
```

4. Ensure functions still return exactly what they returned before.

---

### **P1.2.4 – Make FTP ingestion use create_unified_file()**

In `fetch_ftp_unified.py`:

After downloading each file:

```python
from services.db.files import NewUnifiedFile, create_unified_file

nu = NewUnifiedFile(
    company_id=detected_company_id,
    file_type=detected_file_type,
    source_channel="ftp",
    original_filename=fetched.original_filename,
    storage_path=fetched.local_path,
    content_hash=maybe_hash,
    metadata=fetched.metadata,
)
file_id = create_unified_file(nu)
```

You MUST copy company identification / file_type detection logic exactly as today.

---

### **P1.2.5 – Make upload endpoints use create_unified_file()**

Modify:

```
backend/src/api/ingest.py
backend/src/api/receipts.py
backend/src/api/fetcher.py
```

You MUST replace all direct inserts with:

```python
new_file = NewUnifiedFile(...)
file_id = create_unified_file(new_file)
```

Retain all return values and API schemas exactly as before.

---

## **P1.3 — OPTIONAL WORKFLOW HOOK (ONLY IF ALREADY USED)**

If and only if existing behaviour already creates entries in:

```
workflow_runs
workflow_stage_runs
```

when files are created, then:

### **P1.3.1 – Create helper module**

```
backend/src/services/db/workflow.py
```

Add:

```python
def start_workflow_for_file(file_id: int, workflow_key: str, source_channel: str) -> int:
    """
    P1: Centralized workflow creation.
    MUST mirror exactly the old inline SQL insert.
    """
```

Comment old SQL inside.

### **P1.3.2 – Trigger this helper**

Only in paths which *already* created workflow entries before.

You MUST NOT introduce workflow creation where none existed.

---

## **P1.4 — TESTING REQUIREMENTS**

You MUST implement/extend tests in:

```
backend/tests/unit/test_fetch_ftp_unified.py
backend/tests/unit/test_create_unified_file.py
backend/tests/integration/test_ingestion_pipeline.py
```

Tests MUST verify:

1. Unified FTP ingestion:

   * Connects same way as legacy modules
   * Returns same discovered files list
   * Logs same behaviours
2. create_unified_file:

   * Inserts identical unified_files rows
   * Deduplication matches legacy semantics
3. FTP ingestion end-to-end:

   * Produces same unified_files entries
   * Preserves metadata, ai_status, process_status
4. Upload ingestion:

   * Same API behaviour
   * Same unified_files rows

Tests MUST NOT introduce dummy or fake schema.

Mock FTP clients are permitted if the repository already uses mocking.

---

# 4. FINAL REQUIREMENTS (MANDATORY)

* You MUST complete all P1 tasks above.
* You MUST NOT change public API behaviour.
* You MUST NOT remove any code—only comment it out.
* You MUST NOT invent configuration, values, or logic.
* You MUST keep wrappers and compatibility layers intact.
* You MUST add top-of-file “MODIFIED IN P1” comments wherever needed.
* You MUST ensure all migrations from P0 still function.
* All tests MUST pass.

---

If you want, I can now also produce:

✅ **P2 Agent Prompt** – AI pipeline restructuring
or
✅ **P3 Agent Prompt** – task/workflow cleanup & observability

Just say: **“Make P2 prompt”** or **“Make P3 prompt.”**
