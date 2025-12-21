## PHASE B — Agent-ready implementation plan (English only)

You approved Phase A. This is an implementation plan for a dev-agent to **eliminate mojibake end-to-end** (DB + backend + frontend) and to **tighten AI4 accounting reliability** by ensuring deterministic, UTF-8-correct inputs and logs.

---

# 1) Objective & scope

## Objective

1. **Stop further mojibake from being written** (especially via prompt admin UI and pipeline log messages).
2. **Repair existing mojibake already stored** in MySQL (prompt tables + other known affected text fields).
3. **Fix mojibake inside backend business logic** so keyword matching works with correct Swedish tokens and amount normalization is Unicode-correct.
4. **Add deterministic verification** so we can prove that **å/ä/ö survive**:

   * file → OCR text → API → DB → UI

## In scope (explicit)

* Backend: fix mojibake literals and add write-time validation/guard rails.
* Frontend: remove/neutralize unsafe automatic “mojibake fixing” on save; move correctness to server-side validation + explicit repair tooling.
* DB: add a **new migration** that corrects known seeded prompt strings; provide a deterministic repair script for existing DB content.

## Out of scope (explicit)

* Changing AI model behavior beyond encoding correctness and input sanitation.
* Any refactors unrelated to mojibake / AI4 accounting determinism.
* PR workflow instructions.

**Definition of done**

* No mojibake signatures remain in:

  * `ai_system_prompts.title/description/prompt_content`
  * AI pipeline log messages written after the patch
  * backend keyword lists for AI1/AI2
* Repair tooling is deterministic, repeatable, and safe (idempotent).
* Verification commands produce pass/fail results and prove å/ä/ö roundtrip.

---

# 2) Preconditions / setup (Windows 11 + Docker)

## Repo configuration evidence

* MySQL container uses:

  * `MYSQL_ROOT_PASSWORD: root`
  * `MYSQL_DATABASE: ${DB_NAME}`
  * `MYSQL_USER: ${DB_USER}`
  * `MYSQL_PASSWORD: ${DB_PASS}`
    Evidence: `docker-compose.yml:146-149`

## PowerShell commands (run from repo root)

```powershell
# Ensure environment is loaded from .env used by docker compose
Get-Content .\.env | Select-String -Pattern "DB_NAME|DB_USER|DB_PASS"

# Start stack
docker compose up -d --build

# Confirm MySQL is healthy
docker compose ps
docker compose logs mysql --tail 50
```

## MySQL connectivity (inside container)

```powershell
# Interactive MySQL shell (root)
docker compose exec mysql mysql -uroot -proot -e "SELECT 1;"
```

---

# 3) Task breakdown (detailed)

## T-001 — Add “stop-the-line” server-side validation for prompt updates (reject mojibake on write)

### Goal

Prevent **any future mojibake** from being persisted to `ai_system_prompts` via the admin UI.

### Files touched

* `backend/src/api/ai_config.py`

### Evidence (current behavior)

* Backend update endpoint normalizes text but does **not** detect mojibake:

  * `_normalise_text(...)` returns strings unchanged when already `str`
    Evidence: `backend/src/api/ai_config.py:20-45`
  * `update_prompt(...)` uses `_normalise_text` and writes directly to DB
    Evidence: `backend/src/api/ai_config.py:328-359`

### Step-by-step changes

1. Add a strict mojibake detector:

   * Detect classic UTF-8→latin1 artifacts: `Ã`, `Â`, `â`
     (front-end currently uses a similar heuristic)
     Evidence: `main-system/app-frontend/src/ui/pages/Ai.jsx:5`
   * Detect CP437/CP850 artifacts seen in logs: `ΓÇ`, `├`, `╢`
     Evidence of CP850-like mojibake already present in pipeline log messages:
     `backend/src/services/tasks/ai_pipeline_tasks.py:564-572`
2. In `update_prompt(...)`, before executing UPDATE:

   * If mojibake signatures exist in `clean_title`, `clean_description`, or `clean_content`, return `400` with a deterministic error payload that includes:

     * which field failed
     * which signature matched
     * an instruction to run the DB repair script (T-003)

### Patch (unified diff)

```diff
diff --git a/backend/src/api/ai_config.py b/backend/src/api/ai_config.py
index 0000000..0000000 100644
--- a/backend/src/api/ai_config.py
+++ b/backend/src/api/ai_config.py
@@ -1,6 +1,7 @@
 """API endpoints for AI LLM configuration."""
 
 import logging
+import re
 
 import requests
 from flask import Blueprint, jsonify, request
@@ -17,6 +18,22 @@ logger = logging.getLogger(__name__)
 
 ai_config_bp = Blueprint("ai_config", __name__, url_prefix="/ai-config")
 
+_MOJIBAKE_SIGNATURES = [
+    # Common UTF-8 bytes mis-decoded as latin-1 / Windows-1252
+    ("utf8_as_latin1", re.compile(r"[ÃÂâ][\u0080-\u00FF]")),
+    # UTF-8 bytes mis-decoded as CP437 (e.g., "–" -> "ΓÇô")
+    ("utf8_as_cp437", re.compile(r"ΓÇ")),
+    # UTF-8 bytes mis-decoded as CP850 (e.g., "ö" -> "├╢")
+    ("utf8_as_cp850", re.compile(r"[├╢]")),
+]
+
+def _contains_mojibake(value: str) -> tuple[bool, str]:
+    for name, rx in _MOJIBAKE_SIGNATURES:
+        if rx.search(value or ""):
+            return True, name
+    return False, ""
+
@@ -337,6 +354,22 @@ def update_prompt(prompt_id):
         with db_cursor() as cursor:
             clean_title = _normalise_text(data.get("title"))
             clean_description = _normalise_text(data.get("description"))
             clean_content = _normalise_text(data.get("prompt_content"))
+
+            for field_name, field_value in (
+                ("title", clean_title),
+                ("description", clean_description),
+                ("prompt_content", clean_content),
+            ):
+                bad, sig = _contains_mojibake(field_value)
+                if bad:
+                    return jsonify(
+                        {
+                            "error": "mojibake_detected",
+                            "field": field_name,
+                            "signature": sig,
+                            "action": "Run the DB mojibake repair tool before editing prompts.",
+                        }
+                    ), 400
+
             cursor.execute(
                 """
                 UPDATE ai_system_prompts
```

### Edge cases

* Prompts that intentionally include those glyphs (rare): this will block saving. That is a feature: the system is Swedish-text-first; mojibake glyphs are treated as data corruption.

### Rollback plan

* Revert this single patch commit; behavior returns to current permissive writes.

---

## T-002 — Fix mojibake literals in backend AI keyword logic and amount normalization

### Goal

Make keyword matching and parsing align with correct Swedish UTF-8 text.

### Files touched

* `backend/src/services/ai_service.py`

### Evidence (current mojibake in business logic)

* AI1 keyword list includes `fÃ¶rfallodatum` (should be `förfallodatum`)
  Evidence: `backend/src/services/ai_service.py:696-701`
* AI2 card patterns include `fÃ¶retagskort` (should be `företagskort`)
  Evidence: `backend/src/services/ai_service.py:746-761`
* Amount normalization removes the literal `"â€¯"` instead of handling the real Unicode `\u202F`
  Evidence: `_normalize_amount` uses `cleaned.replace("â€¯", "")`
  `backend/src/services/ai_service.py:395-406`

### Step-by-step changes

1. Replace mojibake tokens with correct Swedish Unicode tokens.
2. Update `_normalize_amount(...)` to remove real Unicode whitespace variants:

   * `\u00A0` (NBSP)
   * `\u202F` (Narrow NBSP)
   * and optionally any general whitespace via regex, but keep it deterministic.

### Patch (unified diff)

```diff
diff --git a/backend/src/services/ai_service.py b/backend/src/services/ai_service.py
index 0000000..0000000 100644
--- a/backend/src/services/ai_service.py
+++ b/backend/src/services/ai_service.py
@@ -693,7 +693,7 @@ class AIService:
 
         receipt_tokens = ["kvitto", "receipt", "summa", "moms", "butik", "kundens kvitto"]
-        invoice_tokens = ["invoice", "faktura", "fÃ¶rfallodatum", "ocr", "betalning"]
+        invoice_tokens = ["invoice", "faktura", "förfallodatum", "ocr", "betalning"]
         fc_tokens = ["firstcard", "first card", "kortmatchning", "kontoutdrag", "firstcard company", "kortfaktura"]
 
@@ -747,7 +747,7 @@ class AIService:
         text = (request.ocr_text or "").lower()
         logger.info("Classifying expense for %s", request.file_id)
 
-        card_patterns = ["visa", "mastercard", "first card", "corporate", "fÃ¶retagskort", "card number"]
+        card_patterns = ["visa", "mastercard", "first card", "corporate", "företagskort", "card number"]
         cash_patterns = ["kontant", "cash"]
 
@@ -394,8 +394,12 @@ def _normalize_amount(token: str) -> Optional[Decimal]:
-    cleaned = token.strip().replace(" ", "")
-    cleaned = cleaned.replace("â€¯", "").replace("'", "")
+    cleaned = token.strip()
+    # Remove common OCR/PDF spacing variants deterministically (UTF-8 correct).
+    cleaned = cleaned.replace(" ", "")
+    cleaned = cleaned.replace("\u00A0", "")  # NBSP
+    cleaned = cleaned.replace("\u202F", "")  # Narrow NBSP
+    cleaned = cleaned.replace("'", "")
     cleaned = cleaned.replace(",", ".")
```

### Edge cases

* If OCR produces other Unicode spaces, they won’t be removed. That is acceptable unless verified problematic; add only with evidence.

### Rollback plan

* Revert this commit; behavior returns to existing logic.

---

## T-003 — Fix mojibake in pipeline log messages (so new DB writes are clean)

### Goal

Ensure all **new log messages written to DB** are correct UTF-8 Swedish.

### Files touched

* `backend/src/services/tasks/ai_pipeline_tasks.py`

### Evidence (current mojibake in log messages)

* `message="AI4 hoppades ├╢ver ΓÇô saknar konteringsunderlag"`
  Evidence: `backend/src/services/tasks/ai_pipeline_tasks.py:564-565`
* `begin_import_stage(..., message="K├╢ar kvitto f├╢r AI5-matchning")`
  Evidence: `backend/src/services/tasks/ai_pipeline_tasks.py:567`
* `"markerat som redo f├╢r matchning"`
  Evidence: `backend/src/services/tasks/ai_pipeline_tasks.py:571-572`

### Step-by-step changes

1. Replace those literal strings with correct Swedish:

   * `hoppades över – saknar konteringsunderlag`
   * `Köar kvitto för AI5-matchning`
   * `redo för matchning`

### Patch (unified diff)

```diff
diff --git a/backend/src/services/tasks/ai_pipeline_tasks.py b/backend/src/services/tasks/ai_pipeline_tasks.py
index 0000000..0000000 100644
--- a/backend/src/services/tasks/ai_pipeline_tasks.py
+++ b/backend/src/services/tasks/ai_pipeline_tasks.py
@@ -561,12 +561,12 @@ def _run_ai_pipeline(file_id: str, workflow_run_id: int) -> list[str]:
             workflow_run_id,
             "r_ai4",
             success=True,
-            message="AI4 hoppades ├╢ver ΓÇô saknar konteringsunderlag",
+            message="AI4 hoppades över – saknar konteringsunderlag",
         )
 
-    begin_import_stage(workflow_run_id, "r_queue_match", message="K├╢ar kvitto f├╢r AI5-matchning")
+    begin_import_stage(workflow_run_id, "r_queue_match", message="Köar kvitto för AI5-matchning")
     complete_import_stage(
         workflow_run_id,
         "r_queue_match",
         success=True,
-        message=f"Kvitto {file_id} markerat som redo f├╢r matchning",
+        message=f"Kvitto {file_id} markerat som redo för matchning",
     )
```

### Rollback plan

* Revert this commit.

---

## T-004 — Add a new migration to correct known seeded mojibake prompt metadata

### Goal

Ensure that even if earlier migrations inserted mojibake (e.g. 0041), **the final schema state is UTF-8 correct** after running the full migration sequence.

### Files touched

* Add: `database/migrations/00XX_fix_mojibake_seed_prompts.sql` (choose the next numeric migration id in your repo sequence)

### Evidence (seeded mojibake exists)

* `0041_add_ai_llm_tables.sql` inserts mojibake:

  * `'UtlÃ¤gg eller fÃ¶retag'`, `'... kvitto Ã¤r ...'`
    Evidence: `database/migrations/0041_add_ai_llm_tables.sql:41-47`

### Step-by-step changes

1. Add a migration that updates only the known affected rows by `prompt_key` (deterministic and low-risk).
2. Do **not** delete prompts; only update the corrupted fields.

### Migration content (example)

```sql
-- database/migrations/00XX_fix_mojibake_seed_prompts.sql
-- Fix known mojibake seeded prompt titles/descriptions inserted earlier.

UPDATE ai_system_prompts
SET
  title = 'Utlägg eller företag',
  description = '... kvitto är ett personligt utlägg eller företagskostnad'
WHERE prompt_key = 'expense_classification';
```

### Edge cases

* If the prompt is already correct (manually fixed), this UPDATE is still safe (idempotent).

### Rollback plan

* Revert by updating back (not recommended) or revert the migration application in a controlled DB restore.

---

## T-005 — Add deterministic DB repair tool for existing mojibake (safe, repeatable)

### Goal

Repair mojibake already stored in DB using deterministic, evidence-driven transforms:

* UTF-8 bytes mis-decoded as latin-1 (`Ã¶`)
* UTF-8 bytes mis-decoded as CP437 (`ΓÇô`)
* UTF-8 bytes mis-decoded as CP850 (`├╢`)

### Files touched

* Add: `backend/scripts/repair_mojibake_db.py` (or equivalent scripts folder used in your repo)

### Repair rules (deterministic)

1. For each candidate string:

   * If it contains `[ÃÂâ]` pattern → attempt `latin1_bytes -> utf8`
   * If it contains `ΓÇ` pattern → attempt `cp437_bytes -> utf8`
   * If it contains `├` or `╢` pattern → attempt `cp850_bytes -> utf8`
2. Only apply a conversion if:

   * The conversion succeeds without exceptions
   * The result differs from the original
   * The result does not contain Unicode replacement characters `�`

### Tables/columns to include first (minimum viable)

* `ai_system_prompts.title`
* `ai_system_prompts.description`
* `ai_system_prompts.prompt_content`

(You can extend later, but keep initial scope tight.)

### Execution (PowerShell + Docker)

Option A: run inside backend container (preferred if backend has Python runtime available):

```powershell
# Service is `ai-api` (not `backend`). Script defaults to dry-run; add `--apply` to write.
docker compose exec ai-api python -m scripts.repair_mojibake_db --tables ai_system_prompts
```

Option B: run from host if you have venv wired to same DB port (only if repo already supports it).

### Acceptance criteria

* Before repair, query finds mojibake signatures; after repair, it finds none.

---

## T-006 — Frontend: remove automatic on-save “encoding fix” and rely on server validation + explicit repair

### Goal

Stop the UI from silently mutating content and accidentally persisting partial “fixes”.

### Files touched

* `main-system/app-frontend/src/ui/pages/Ai.jsx`

### Evidence (current behavior)

* Frontend has a mojibake detector and performs fixes on prompt objects:

  * `MOJIBAKE_PATTERN = /[ÃÂâ][\u0080-\u00FF]/;`
    Evidence: `main-system/app-frontend/src/ui/pages/Ai.jsx:5`
  * `normalizePrompt(...)` calls `fixEncodingDeep(prompt)` and is used in edit flow
    Evidence: `main-system/app-frontend/src/ui/pages/Ai.jsx:490-518`

### Step-by-step changes

1. Change `normalizePrompt(...)` so it **does not** apply `fixEncodingDeep` during save/edit.
2. Keep display-time “fix” optional only if you must preserve UI readability, but do not write it back implicitly.
3. If server returns `400 mojibake_detected` (T-001), display an explicit banner:

   * “DB contains mojibake. Run repair tool before editing prompts.”

### Minimal patch direction (conceptual)

* Replace:

  * `const safePrompt = fixEncodingDeep(prompt)`
* With:

  * `const safePrompt = prompt`
* Do not remove the helper functions; just stop applying them automatically to write-path.

### Acceptance criteria

* If DB contains mojibake, the UI can display it, but saving is blocked by server until repaired (deterministic safety).
* If DB is clean, prompts roundtrip exactly without mutation.

---

# 4) Test & verification plan (mandatory)

## 4.1 DB mojibake detection queries (before and after)

Run inside MySQL container:

```powershell
docker compose exec mysql mysql -uroot -proot -e "
SELECT prompt_key, title
FROM ai_system_prompts
WHERE title LIKE '%Ã%' OR title LIKE '%ΓÇ%' OR title LIKE '%├%' OR title LIKE '%╢%';

SELECT prompt_key, description
FROM ai_system_prompts
WHERE description LIKE '%Ã%' OR description LIKE '%ΓÇ%' OR description LIKE '%├%' OR description LIKE '%╢%';

SELECT prompt_key
FROM ai_system_prompts
WHERE prompt_content LIKE '%Ã%' OR prompt_content LIKE '%ΓÇ%' OR prompt_content LIKE '%├%' OR prompt_content LIKE '%╢%';
" ${DB_NAME}
```

**Pass condition:** all three resultsets are empty after repair + migration.

## 4.2 End-to-end UTF-8 proof (å/ä/ö survive)

1. After T-001..T-006 applied, pick a prompt and set the content to include:

   * `å ä ö Å Ä Ö`
2. Save in UI.
3. Verify in DB:

```powershell
docker compose exec mysql mysql -uroot -proot -e "
SELECT prompt_key, prompt_content
FROM ai_system_prompts
WHERE prompt_content LIKE '%å%' OR prompt_content LIKE '%ä%' OR prompt_content LIKE '%ö%';
" ${DB_NAME}
```

**Pass condition:** the exact characters are present, not mojibake.

## 4.3 Verify AI keyword logic is UTF-8 correct

This is a deterministic static check:

* Confirm source contains correct tokens:

  * `förfallodatum`
  * `företagskort`

You can enforce via a simple grep (PowerShell):

```powershell
Select-String -Path .\backend\src\services\ai_service.py -Pattern "förfallodatum","företagskort"
```

**Pass condition:** both are found, and mojibake versions are not.

## 4.4 Verify new pipeline log messages are clean

Trigger a workflow run that reaches the log lines updated in T-003, then query the stored messages and confirm they do not contain mojibake signatures.

---

# 5) Final validation checklist

* [ ] `backend/src/api/ai_config.py` blocks prompt saves containing mojibake signatures (T-001).
* [ ] `backend/src/services/ai_service.py` no longer contains `fÃ¶rfallodatum` / `fÃ¶retagskort` (T-002).
* [ ] `_normalize_amount(...)` handles `\u00A0` and `\u202F` and does not rely on `"â€¯"` literal (T-002).
* [ ] `backend/src/services/tasks/ai_pipeline_tasks.py` no longer writes mojibake log messages (T-003).
* [ ] New migration updates known corrupted seeded prompt metadata (T-004).
* [ ] DB repair script runs idempotently and removes mojibake from prompt table (T-005).
* [ ] Frontend no longer mutates prompt content via automatic “fixEncodingDeep” on save (T-006).
* [ ] DB queries for mojibake signatures return **no rows**.
* [ ] A prompt containing `å ä ö Å Ä Ö` roundtrips UI → API → DB correctly.

---

