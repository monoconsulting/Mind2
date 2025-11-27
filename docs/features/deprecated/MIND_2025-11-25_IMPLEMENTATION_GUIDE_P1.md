# P1 – Ingestion & File Lifecycle Refactor (Detailed Agent Implementation Guide)

## High-level goal

1. **Unify FTP ingestion** so there is **one canonical code path** for:

   * connecting to FTP,
   * discovering files,
   * downloading them,
   * routing them to storage and DB (unified_files),
   * scheduling further processing.

2. **Centralize file creation** so all new files (FTP imports + uploads) are created via a single `create_unified_file(...)`-style function in `services/db/files.py` that:

   * handles `unified_files` inserts,
   * handles deduplication via `content_hash`,
   * sets consistent initial statuses and metadata,
   * optionally triggers workflow creation.

3. **Optionally (within P1)**: ensure that, when a file is created, a corresponding `workflow_runs` entry is created (if your current workflow design requires it) via a small helper, without changing external behaviour.

Everything below must follow the same strict rules as P0:
**no new features, no deletions, no behaviour change, no fake data.**

---

## 0. Global rules (P1-specific restatement)

The agent MUST obey these rules during P1:

1. **No new user-visible features.**
2. **No deleted code.**

   * If a function/module is retired:

     * Comment it out (do not remove).
     * Add a clear English comment explaining:

       * Why it is deprecated.
       * Which new function/module replaces it.
3. **No invented behaviour or configuration.**

   * All behaviour must be inferred from existing:

     * FTP modules (`services/fetch_ftp*.py`),
     * storage & DB modules,
     * API endpoints.
4. **Preserve all existing behaviour.**

   * Same files imported,
   * same statuses set,
   * same side effects (AI queueing, tasks scheduling, etc).
5. **Minimal, scoped changes.**

   * Do not modify unrelated modules.
   * Any touched file must have a comment at the top saying why it was changed.
6. **All tests must pass after P1.**

   * Update/add tests if necessary to keep coverage and verify behaviour.

---

## 1. Repository elements involved in P1

### FTP ingestion modules

You must inspect and work with:

* `backend/src/services/fetch_ftp.py`
* `backend/src/services/fetch_ftp_enhanced.py`
* `backend/src/services/fetch_ftp_updated.py`
* `backend/src/services/fetch_ftp_backup.py`

(Exact names may differ slightly; use the existing ones in the repo.)

### File & storage modules

You must inspect and work with:

* `backend/src/services/storage.py`
* `backend/src/services/file_detection.py` (if present)
* `backend/src/services/ocr.py` (for how files are passed along)
* `backend/src/services/db/files.py` (DB layer for unified_files and related tables)

### Tasks & API (FTP usage)

You must inspect where FTP ingestion and file creation are triggered:

* `backend/src/services/tasks/file_management_tasks.py`
* `backend/src/services/tasks/workflow_tasks.py`
* `backend/src/api/fetcher.py` (or equivalent)
* `backend/src/api/ingest.py`
* Any scripts that call FTP-related functions (e.g. CLI helpers under `backend/`)

### Database tables

Relevant tables (from migrations + code):

* `unified_files`

  * `id`
  * `company_id`
  * `file_type`
  * `ai_status`
  * `process_status`
  * `content_hash`
  * `file_location`
  * `original_filename`
  * `source_channel` (FTP, upload, etc)
  * soft-delete flags / timestamps
* `file_locations`, `file_suffix`, `file_categories` (if used for classification)
* `workflow_runs` / `workflow_stage_runs` (integration in P1.3)

---

## 2. P1.1 – **Unify FTP Ingestion**

### 2.1.1 – Inventory current FTP behaviour

You must start by **understanding all current FTP paths**.

1. Open and read:

   * `backend/src/services/fetch_ftp.py`
   * `backend/src/services/fetch_ftp_enhanced.py`
   * `backend/src/services/fetch_ftp_updated.py`
   * `backend/src/services/fetch_ftp_backup.py`

2. For each module, document (in comments or your own notes):

   * How it:

     * Gets FTP credentials (env vars, config, etc).
     * Connects (plain FTP, FTPS, TLS options, ports, timeouts).
     * Enumerates remote files and directories.
     * Filters files (by extension, patterns, date).
     * Downloads files to local storage (which path?).
     * Hands off to DB/storage (how does it create entries in `unified_files`?).
     * Handles errors (exceptions, logging, partial failures).

3. Identify **behaviour differences** between the modules:

   * Do they use different directory structures?
   * Different file filters or company mappings?
   * Different logging or error handling?

You must NOT change anything yet – just understand.

---

### 2.1.2 – Define a unified FTP ingestion interface

You must design a **single, canonical Python interface** for FTP ingestion.

Create or choose a module, for example:

* `backend/src/services/fetch_ftp_unified.py` (new)
* or pick `fetch_ftp_enhanced.py` as canonical and refactor into it.

**Recommended approach:** create a new `fetch_ftp_unified.py` and gradually rewire others to it.

In `fetch_ftp_unified.py`, define:

```python
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class FTPSourceConfig:
    """Configuration for an FTP source."""
    host: str
    port: int
    username: str
    password: str
    remote_base_dir: str
    use_tls: bool
    timeout: int
    # Optional: company_id, source_channel, etc, if this is per-company


@dataclass
class FetchedFile:
    """Result of a single FTP file fetch operation."""
    local_path: str
    original_path: str
    original_filename: str
    company_id: Optional[int]
    source_channel: str
    category_key: Optional[str]  # e.g. "receipt", "invoice", etc
    metadata: dict
```

Then define a high-level function such as:

```python
def fetch_all_from_source(config: FTPSourceConfig) -> List[FetchedFile]:
    """Connect to the FTP source and download all eligible files.

    This function MUST preserve the behaviour of the existing FTP modules:
    - Same selection logic
    - Same directory traversal
    - Same naming
    - Same company mapping
    """
    ...
```

You MUST copy the existing behaviour from current modules – no new logic.

---

### 2.1.3 – Implement unified FTP logic using existing behaviour

You must:

1. Move **shared logic** (connect, list files, download) into helper functions inside `fetch_ftp_unified.py`.

   Example:

   ```python
   def _connect(config: FTPSourceConfig):
       ...
   ```

2. For each existing FTP module (`fetch_ftp.py`, `fetch_ftp_enhanced.py`, etc):

   * Replace their inner logic with thin wrappers that call the new unified functions.
   * Example:

   ```python
   # In fetch_ftp.py

   # Previous implementation is commented out and kept for history:
   # def old_fetch_files(...):
   #     ...

   from services.fetch_ftp_unified import FTPSourceConfig, fetch_all_from_source

   def fetch_files_for_company_x():
       """Thin wrapper: preserves previous entry-point API but delegates to unified service."""
       config = FTPSourceConfig(
           host=...,
           port=...,
           username=...,
           password=...,
           remote_base_dir=...,
           use_tls=...,
           timeout=...,
       )
       fetched = fetch_all_from_source(config)
       # Possibly call downstream ingestion functions (see P1.2) if that used to happen here.
       return fetched
   ```

   * You MUST comment out the old implementation and add a doc block explaining:

     ```python
     # NOTE:
     # This previous implementation has been replaced by the unified FTP logic
     # in services.fetch_ftp_unified.fetch_all_from_source(...).
     # The old code is preserved here for historical reference only.
     ```

3. You MUST ensure:

   * All existing public functions used by tasks/scripts still exist and have the same signature.
   * They now internally use the unified implementation.

---

### 2.1.4 – Integrate with logging and error handling

In `fetch_ftp_unified.py`, you must:

1. Use the project’s logging conventions (likely standard `logging` or `observability/logging.py`):

   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```

2. Log at key points:

   * Connection established.
   * Number of discovered candidate files.
   * Successful downloads.
   * Errors per file.

   Example:

   ```python
   logger.info("Connecting to FTP host=%s port=%s", config.host, config.port)
   ```

3. Error handling rules:

   * If an individual file fails to download:

     * Log at `ERROR` level.
     * Continue with remaining files.
   * If connection fails:

     * Log at `ERROR`.
     * Raise or return an empty list, depending on existing behaviour.
   * You MUST copy semantics from existing modules; do not change whether they raise or swallow exceptions at entry points.

---

### 2.1.5 – Tests for FTP ingestion

You must create or extend tests under:

* `backend/tests/unit/test_fetch_ftp_unified.py` (new)
* Possibly adjust existing tests for `fetch_ftp.py` / `fetch_ftp_enhanced.py`.

Test cases:

1. Configuration-based paths:

   * Validate that `FTPSourceConfig` can be built from environment/config exactly as existing modules did.

2. Happy path (mocked FTP client):

   * Using mocks for `ftplib.FTP` or whichever client is used.
   * Ensure `fetch_all_from_source`:

     * connects with same parameters,
     * enumerates same files,
     * returns list of `FetchedFile` with correct metadata.

3. Failure path:

   * Simulate connection errors.
   * Ensure behaviour matches previous modules:

     * either raising an exception or returning no files; follow existing semantics.

You must NOT introduce live network I/O in tests.
Use mocking/fakes only, consistent with current project test style.

---

## 3. P1.2 – **File storage and unified_files alignment**

Goal: all file creation should go through a single DB-layer function, making lifecycle consistent and deduplication central.

### 3.1.1 – Inspect DB file functions

You must open:

* `backend/src/services/db/files.py`
* `backend/src/services/storage.py`
* any functions that insert rows into `unified_files` (grep for `"INSERT INTO unified_files"` / `.insert_unified_file` etc).

Document:

* How `unified_files` rows are currently created:

  * which columns are set,
  * which defaults are used,
  * when `content_hash` is calculated,
  * how `file_type`, `company_id`, `source_channel` are determined.

---

### 3.1.2 – Define a centralized create_unified_file API

In `backend/src/services/db/files.py`, you must introduce a **single** public function (if not already existing), such as:

```python
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class NewUnifiedFile:
    """Incoming data required to create a new unified_files row."""
    company_id: Optional[int]
    file_type: str
    source_channel: str       # e.g. 'ftp', 'upload'
    original_filename: str
    storage_path: str         # path in storage backend
    content_hash: Optional[str]  # hash of file contents if available early
    metadata: Dict[str, str]  # json metadata, optional
```

And the function:

```python
def create_unified_file(new_file: NewUnifiedFile) -> int:
    """Create a new unified_files row.

    - Sets ai_status and process_status to the correct initial values.
    - Handles deduplication via content_hash if required.
    - Returns the new unified_files.id.
    """
    ...
```

Rules:

* You MUST use existing conventions for:

  * initial `ai_status` (e.g. "new"),
  * initial `process_status`,
  * any soft-delete flags.
* You MUST enforce any constraints already implemented elsewhere (e.g. not inserting duplicates).

---

### 3.1.3 – Implement deduplication semantics

You must inspect existing deduplication logic:

* Search for `content_hash` usage.
* Look for any queries like:

  ```sql
  SELECT id FROM unified_files WHERE content_hash = ... AND company_id = ...
  ```

You must centralize this logic inside `create_unified_file()`:

1. If no deduplication exists currently:

   * You must **NOT invent new behaviour**.
   * You may only prepare the structure for future dedup (e.g. keep parameter but don’t enforce uniqueness).

2. If deduplication exists:

   * Copy the exact conditions:

     * same columns used,
     * same exceptions/flags set on duplicates.
   * For example:

   ```python
   existing_id = _find_existing_unified_file(new_file)
   if existing_id is not None:
       # either return existing_id, or raise a DuplicateFileError, depending on current behaviour
       ...
   ```

3. You must ensure that all code paths use this function to create `unified_files` records, so dedup logic isn’t reimplemented ad-hoc.

---

### 3.1.4 – Wire FTP ingestion into create_unified_file

In your unified FTP module `fetch_ftp_unified.py` (and its wrappers), you must:

1. After downloading each file, construct a `NewUnifiedFile` instance:

   ```python
   from services.db.files import NewUnifiedFile, create_unified_file

   new_file = NewUnifiedFile(
       company_id=company_id,
       file_type=file_type,               # how this is determined is based on existing logic
       source_channel="ftp",
       original_filename=fetched.original_filename,
       storage_path=fetched.local_path,
       content_hash=calculated_hash,      # if your current flow calculates this; otherwise None
       metadata=fetched.metadata,
   )
   unified_id = create_unified_file(new_file)
   ```

2. Remove (by commenting out) any direct SQL inserts into `unified_files` from FTP modules and replace them with calls to `create_unified_file()`. Keep old SQL as comments and add explanation:

   ```python
   # Old inline insertion into unified_files has been replaced by
   # services.db.files.create_unified_file(NewUnifiedFile(...)).
   # The SQL is preserved below for historical reference.
   # INSERT INTO unified_files (...)
   # VALUES (...);
   ```

3. Ensure that any follow-up behaviour (e.g. scheduling OCR/AI tasks) that used to rely on the old insertion path still happens:

   * If the previous function returned `unified_files.id`, your new wrapper must also return it.

---

### 3.1.5 – Wire upload endpoints into create_unified_file

You must also adjust any **upload-based** ingestion paths:

1. Inspect:

   * `backend/src/api/ingest.py`
   * `backend/src/api/receipts.py` (if it accepts direct upload)
   * any other endpoints or scripts that create `unified_files` records.

2. For each such path:

   * Replace direct DB insertions into `unified_files` with `create_unified_file()` calls.
   * Preserve:

     * `source_channel` (e.g. `"upload"`),
     * company determination logic,
     * file type classification logic.

3. **Important:** you must not change API response formats. If an endpoint used to return `{"file_id": ...}`, it must still do so.

---

### 3.1.6 – Tests for file creation

You must create or extend tests under:

* `backend/tests/unit/test_db_files_create_unified_file.py` (new)
* and integration tests for ingestion.

Test cases:

1. Creating a new file:

   * Use a real test DB (with migrations applied).
   * Call `create_unified_file()` with a `NewUnifiedFile` instance.
   * Verify:

     * A row is inserted into `unified_files`.
     * Fields are set as expected (ai_status, process_status, content_hash, etc).

2. Duplicate handling:

   * If dedup logic is active:

     * Call `create_unified_file()` twice with identical `content_hash` & `company_id`.
     * Verify the same behaviour as before refactor:

       * either same id is returned,
       * or a defined exception is raised,
       * or a duplicate flag is set.

3. FTP integration test:

   * Using mocks for FTP, simulate one or more downloaded files.
   * Ensure that calling the FTP wrapper results in:

     * `create_unified_file` being called once per file,
     * correct arguments mapping.

---

## 4. P1.3 – **Workflow integration at file creation (optional but recommended in P1)**

If current design expects each file to have a `workflow_runs` entry, P1 should include a thin integration.

### 4.1.1 – Inspect workflow tables and code

You must examine:

* `database/migrations/0031_create_workflow_tracking.sql` (or equivalent)

* Any code that writes to:

  * `workflow_runs`
  * `workflow_stage_runs`

* `backend/src/api/receipts.py`

* `backend/src/services/tasks/workflow_tasks.py`

* `backend/src/services/db/workflow.py` (if exists)

You must understand:

* When a workflow is created today:

  * On upload only?
  * On AI-handling?
  * On manual actions?

---

### 4.1.2 – Introduce a small helper for workflow start

If there is not already a central helper, you should add one in a suitable DB layer, e.g.:

* `backend/src/services/db/workflow.py`

Define:

```python
from typing import Optional

def start_workflow_for_file(
    file_id: int,
    workflow_key: str,
    source_channel: str,
) -> int:
    """Create a workflow_runs entry for the given file.

    Must preserve existing behaviour:
    - Same default status (e.g. queued)
    - Same field values for workflow_key and source_channel
    - Same handling for duplicates, if any.
    """
    ...
```

You must:

* Implement this using the existing SQL pattern seen in other code that creates workflow runs.
* Preserve the existing workflow design – no new workflow types.

---

### 4.1.3 – Call workflow helper from create_unified_file (if appropriate)

This part must be done **very carefully**.

1. Determine whether, today, every new file leads to a `workflow_runs` row:

   * If yes, and the creation currently happens in various scattered places, you can centralize it by calling `start_workflow_for_file()` inside `create_unified_file()` or immediately afterwards in the ingestion call path.
   * If no (only some flows start workflows), you must not change that behaviour in P1. Instead:

     * Add hooks only in the existing workflows where that already happens.

2. You must ensure behaviour parity:

   * Compare current state:

     * Before refactor: “After uploading via endpoint X, we see 1 row in unified_files and 1 row in workflow_runs”.
     * After refactor: same result.

3. If you adjust code to call `start_workflow_for_file`, you must comment out and preserve any old inline SQL that did the same, with a note:

   ```python
   # NOTE: Inline workflow_runs INSERT has been replaced by
   # services.db.workflow.start_workflow_for_file(...).
   # Old SQL preserved below for historical reference.
   ```

---

### 4.1.4 – Tests for workflow at file creation

Add / update tests:

* `backend/tests/integration/test_file_workflow_creation.py` (new)

Test cases:

1. FTP ingestion:

   * Mock FTP to download one file.
   * Run FTP ingestion entry point.
   * Assert:

     * One row in `unified_files` for that file.
     * One corresponding workflow_runs row, if this was already behaviour before.

2. Upload ingestion:

   * Call upload endpoint.
   * Assert same as above, if this matched existing behaviour.

If no such behaviour existed before, you may skip these tests, but you must NOT introduce new behaviour silently.

---

## 5. Cross-cutting aspects for P1

### 5.1 – Logging

* Use the logging patterns already present (e.g. JSON logging).
* Do not introduce new logging frameworks.
* For new modules/functions:

  * Add a module-level logger.
  * Log relevant events (connect, discovered files, created unified_files IDs, workflows).

### 5.2 – Error propagation

* Maintain the existing contract for errors:

  * If a given entry point used to raise an exception on critical FTP failure, keep that.
  * If it logged and continued, keep that behaviour.
* When you centralize file creation and workflow creation, do not add new exception types unless they already exist (e.g. `DuplicateFileError`).

### 5.3 – Encoding & filenames

* Do not alter filename handling logic regarding UTF-8 and Swedish characters.
* Ensure that filenames (with å, ä, ö, etc.) still pass through unchanged.
* If there is an existing place where encoding is normalised, reuse it; do not add additional transcoding.

