## FAS B — Agent-ready implementation plan (English only)

### Objective & scope

**IMPORTANT**

This must be implemented in the following order:

If**Phase 1 → Phase 2 → DB-REPAIR MIGRATIONS -> Phase 3 → Phase 4 → Phase 5**

**Primary objective:** Make accounting (“AI4”) and FirstCard matching **correct and complete**, with deterministic rules for corporate vs personal (including the `LAST4==9995` rule), and fix the UI so manual items are clearly visible.

**In scope (must be implemented):**

1. Fix **wrong / missing accounting proposals** (AI4 coverage and gating).
2. Fix **AI2 expense_type classification** so it matches the intended rule set (incl. `9995 => personal`, `6779/4668 => corporate`, Visa => personal).
3. Fix **FirstCard auto + manual matching** candidate logic so it matches **only relevant corporate receipts** and uses the same “match datetime/amount” logic everywhere.
4. Add **Process → MANUAL** column with an exclamation mark for manual items.
5. Add **repair steps** for existing already-imported wrong data (wrong expense_type and wrong matches).

**Out of scope (do not touch):**

- Any unrelated UI/UX changes outside the Process MANUAL column and the matching views needed to fix candidate visibility.
- Any refactors not directly required to fix the listed issues.
- Any PR workflow / CI/CD changes.

**Definition of done:**

- `LAST4==9995` receipts end up **expense_type=personal** deterministically.
- FirstCard auto matching never links invoice lines to **personal** receipts.
- Manual matching screens show the expected candidate receipts (including those missing `purchase_datetime` but having `created_at`).
- AI4 proposals are generated for all receipts that have sufficient totals (including legacy totals where appropriate).
- Process list shows a **MANUAL** column with `!` when the item is manual review.

------

## Preconditions / setup (Windows 11 + Docker)

### Run the stack

The compose file uses profiles (e.g. `profiles: [main]` in `docker-compose.yml`). *(local repo evidence: `docker-compose.yml` has `profiles: [main]` for services, e.g. `ai-api` and `mysql`)*

Run from repo root (PowerShell):

```powershell
docker compose --profile main up -d --build
docker compose ps
```

### DB access

MySQL root credentials are explicitly configured in `docker-compose.yml` (`MYSQL_ROOT_PASSWORD=root`).

Use:

```powershell
docker compose exec mysql mysql -uroot -proot -e "SELECT 1;"
```

### Canonical prompt source (DB)

Prompts are stored in `ai_system_prompts` in the DB dump (`mind_db_dump.sql`).
(We will **update DB prompts via migration** to keep runtime canonical and reproducible.)

------

## Phase 1 — Fix AI2 classification (stop wrong corporate tagging)

### T-001 — Implement deterministic AI2 rule set (including LAST4 rules)

**Goal:** Replace the current AI2 heuristic that marks *any* “visa/mastercard” text as corporate.

**Evidence of current bug:** `run_ai2_expense_classification()` sets corporate if any of `["visa","mastercard", ...]` appears. This makes Visa receipts corporate and can cascade into wrong matching. (`backend/src/services/ai_service.py:807–845`).

**Files touched**

- `backend/src/services/ai_service.py`

**Step-by-step changes**

1. In `AIService.run_ai2_expense_classification()`:
   - Remove the current `card_patterns` loop that flips to corporate on `"visa"` / `"mastercard"`.
   - Add a deterministic extractor:
     - Detect **payment method**: swish/cash → personal.
     - Detect **card brand** (Visa vs MasterCard).
     - Extract **last4** with regex patterns that cover common OCR formats (e.g. `**** 9995`, `XXXX9995`, `Kortnr ... 9995`).
2. Apply rule precedence deterministically:
   - If **Swish** or **cash/kontant** indicators → `expense_type="personal"`.
   - If **Visa** indicators → `expense_type="personal"`.
   - If **MasterCard** and last4 is:
     - `9995` → personal
     - `6779` or `4668` → corporate
   - If MasterCard but last4 is missing/unknown → do **not** default to corporate; set `expense_type="personal"` with lower confidence *or* set `expense_type="personal"` and `card_identifier=None` (so it won’t be matched as corporate).
3. Set `card_identifier` deterministically when last4 is extracted (e.g. `"MC-9995"` / `"MC-6779"` / `"VISA"`).

**Patch example (minimal, unified diff style)**

```diff
--- a/backend/src/services/ai_service.py
+++ b/backend/src/services/ai_service.py
@@ -807,25 +807,120 @@
     def run_ai2_expense_classification(self, request: ExpenseClassificationRequest) -> ExpenseClassificationResponse:
         text = (request.ocr_text or "").lower()
         logger.info("Classifying expense for %s", request.file_id)
 
-        card_patterns = ["visa", "mastercard", "first card", "corporate", "företagskort", "card number"]
-        cash_patterns = ["kontant", "cash"]
-
-        expense_type = "personal"
-        confidence = 0.6
-        reasoning_parts: List[str] = []
-        card_identifier: Optional[str] = None
-
-        for pattern in card_patterns:
-            if pattern in text:
-                expense_type = "corporate"
-                confidence = 0.85
-                reasoning_parts.append(f"Detected corporate indicator: {pattern}")
-                break
-
-        for pattern in cash_patterns:
-            if pattern in text:
-                expense_type = "personal"
-                confidence = 0.9
-                reasoning_parts.append(f"Detected cash indicator: {pattern}")
-                break
+        # Deterministic AI2 rules:
+        # - Swish/cash -> personal
+        # - Visa -> personal
+        # - MasterCard with last4:
+        #     9995 -> personal
+        #     6779/4668 -> corporate
+        expense_type = "personal"
+        confidence = 0.60
+        reasoning_parts: List[str] = []
+        card_identifier: Optional[str] = None
+
+        def _extract_last4(ocr: str) -> Optional[str]:
+            # Common OCR patterns for last4 digits
+            patterns = [
+                r"(?:\*{2,}|x{2,}|#){2,}\s*([0-9]{4})",
+                r"(?:kort|card)\s*(?:nr|no|number)?\s*[:\-]?\s*.*?([0-9]{4})\b",
+                r"\b([0-9]{4})\b\s*(?:contactless|blipp|tap)?\b",
+            ]
+            for pat in patterns:
+                m = re.search(pat, ocr, flags=re.IGNORECASE | re.DOTALL)
+                if m:
+                    return m.group(1)
+            return None
+
+        is_cash = any(k in text for k in ["kontant", "cash"])
+        is_swish = "swish" in text
+        is_visa = "visa" in text
+        is_mc = "mastercard" in text or "master card" in text
+
+        if is_cash or is_swish:
+            expense_type = "personal"
+            confidence = 0.95
+            reasoning_parts.append("Detected swish/cash indicator")
+        elif is_visa:
+            expense_type = "personal"
+            confidence = 0.90
+            card_identifier = "VISA"
+            reasoning_parts.append("Detected VISA indicator")
+        elif is_mc:
+            last4 = _extract_last4(text)
+            if last4:
+                card_identifier = f"MC-{last4}"
+                if last4 == "9995":
+                    expense_type = "personal"
+                    confidence = 0.95
+                    reasoning_parts.append("MasterCard last4=9995 => personal")
+                elif last4 in ("6779", "4668"):
+                    expense_type = "corporate"
+                    confidence = 0.95
+                    reasoning_parts.append(f"MasterCard last4={last4} => corporate")
+                else:
+                    expense_type = "personal"
+                    confidence = 0.70
+                    reasoning_parts.append(f"MasterCard last4={last4} not in corporate set => personal")
+            else:
+                expense_type = "personal"
+                confidence = 0.65
+                reasoning_parts.append("MasterCard indicator but last4 not extracted => personal (non-corporate-safe default)")
 
         prompt_hint = self.prompts.get("expense_classification")
         if prompt_hint:
             reasoning_parts.append(f"Prompt hint provided: {prompt_hint}")
```

**Edge cases**

- OCR often contains many 4-digit numbers (e.g. time, amounts). The extractor must prefer masked patterns (`**** 1234`) before generic 4-digit hits.
- If both Visa and MasterCard appear (bad OCR), keep precedence: Visa → personal unless a corporate MasterCard last4 is clearly extracted.

**Rollback**

- Revert commit that changes `run_ai2_expense_classification()`.

------

### T-002 — Repair existing DB rows for LAST4 rules

**Goal:** Fix already-imported `unified_files.expense_type` where last4 implies a different expense_type.

**Files touched**

- New migration SQL: `database/migrations/00XX_repair_expense_type_last4.sql`

**SQL actions**

1. Set personal for 9995:

```sql
UPDATE unified_files
SET expense_type='personal', updated_at=NOW()
WHERE credit_card_last_4_digits=9995
  AND (expense_type IS NULL OR expense_type<>'personal');
```

1. Set corporate for 6779/4668:

```sql
UPDATE unified_files
SET expense_type='corporate', updated_at=NOW()
WHERE credit_card_last_4_digits IN (6779,4668)
  AND (expense_type IS NULL OR expense_type<>'corporate');
```

**Acceptance criteria**

- Query returns 0 for corporate+9995:

```sql
SELECT COUNT(*) AS wrong
FROM unified_files
WHERE credit_card_last_4_digits=9995 AND expense_type='corporate';
```

------

## Phase 2 — Fix FirstCard matching (auto + manual)

### T-010 — Restrict candidate receipts to corporate receipts only (auto matching)

**Goal:** Stop auto-matching invoice lines to personal receipts.

**Evidence:** `_fetch_receipt_candidates()` currently does not filter by `expense_type` and will consider any receipt, ordered by amount/date. (`backend/src/services/tasks/creditcard_tasks.py:648–677`).

**Files touched**

- `backend/src/services/tasks/creditcard_tasks.py`

**Step-by-step changes**

1. In `_fetch_receipt_candidates()` SQL WHERE clause, add:
   - `AND uf.file_type = 'receipt'`
   - `AND uf.expense_type = 'corporate'`
2. Keep the existing `COALESCE(purchase_datetime, created_at)` and match_amount expression unchanged.

**Patch example**

```diff
--- a/backend/src/services/tasks/creditcard_tasks.py
+++ b/backend/src/services/tasks/creditcard_tasks.py
@@ -674,6 +674,8 @@
                             )
                         AND (uf.credit_card_match IS NULL OR uf.credit_card_match = 0)
                         AND il.id IS NULL
+                        AND uf.file_type = 'receipt'
+                        AND uf.expense_type = 'corporate'
```

**Acceptance criteria**

- Auto matching produces **zero** matches where matched receipt is personal:

```sql
SELECT COUNT(*) AS wrong
FROM invoice_lines il
JOIN unified_files uf ON uf.id = il.matched_file_id
WHERE il.match_status='auto'
  AND uf.expense_type='personal';
```

------

### T-011 — Align manual candidates endpoint with auto logic (and corporate-only)

**Goal:** Fix “manual match shows nothing/few items” and stop irrelevant candidates.

**Evidence:** Candidates endpoint requires `purchase_datetime IS NOT NULL` and uses only `gross_amount`, which drops valid receipts and diverges from auto matching. (`backend/src/api/reconciliation_firstcard/routes/lines.py:69–137`).

**Files touched**

- `backend/src/api/reconciliation_firstcard/routes/lines.py`

**Step-by-step changes**

1. Replace:
   - `purchase_datetime IS NOT NULL` with `COALESCE(purchase_datetime, created_at) IS NOT NULL`
2. Replace amount selection with the same `COALESCE(NULLIF(...))` match_amount expression used in auto matching.
3. Add:
   - `AND u.file_type='receipt'`
   - `AND u.expense_type='corporate'`
4. Keep tolerance and date window consistent with auto matching constants.

**Acceptance criteria**

- The manual candidates endpoint returns candidates for receipts with null `purchase_datetime` but recent `created_at`.
- No personal receipts appear as candidates.

------

### T-012 — Add “uniqueness guard” for auto matching

**Goal:** Avoid “it matched, but completely wrong” when multiple candidates exist.

**Evidence:** Auto matching picks the first candidate not used based on sorting, without checking if a near-tie exists. (`backend/src/services/tasks/creditcard_tasks.py:810–860`).

**Files touched**

- `backend/src/services/tasks/creditcard_tasks.py`

**Step-by-step changes**

1. Before linking, inspect the sorted candidate list:
   - If there are ≥2 candidates and candidate #2 is “too close” to candidate #1 (amount_diff within a small delta and date_diff within a small delta), **do not auto link** → keep status pending/unmatched.
2. Log an explicit event `matching.auto.ambiguous_candidates`.

**Acceptance criteria**

- Ambiguous lines remain pending (not auto matched).
- Clear single-candidate lines still auto match.

------

### T-013 — Repair already-wrong matches

**Goal:** Undo incorrect links created earlier.

**Files touched**

- New migration SQL: `database/migrations/00XY_unmatch_personal_receipts_from_fc.sql`

**SQL actions**

1. Unlink any invoice line matched to a personal receipt:

```sql
UPDATE invoice_lines il
JOIN unified_files uf ON uf.id = il.matched_file_id
SET il.matched_file_id=NULL,
    il.match_status='pending',
    il.match_confidence=NULL,
    il.updated_at=NOW()
WHERE uf.expense_type='personal'
  AND il.matched_file_id IS NOT NULL;
```

1. Reset receipt side match marker if your system uses `credit_card_match` (only for receipts that were unlinked):

```sql
UPDATE unified_files
SET credit_card_match=0, updated_at=NOW()
WHERE expense_type='personal' AND credit_card_match=1;
```

**Acceptance criteria**

- No invoice line remains matched to a personal receipt.

------

## Phase 3 — Fix missing accounting proposals (AI4 completeness)

### T-020 — Accept legacy totals when originals are missing (SEK receipts)

**Goal:** Make AI4 runnable when `gross_amount_original/net_amount_original` are null but legacy totals exist.

**Evidence:** `_load_accounting_inputs()` gates AI4 on SEK/original fields and reports missing totals. (`backend/src/services/tasks/file_management_tasks.py:420–640`, esp. `ai4_ready` logic).
Also, list/pipeline currently stores legacy columns `gross_amount`/`net_amount` (see update in `backend/src/api/ai_processing.py:560–590` where legacy is preserved).

**Files touched**

- `backend/src/services/tasks/file_management_tasks.py`

**Step-by-step changes**

1. Extend SELECT in `_load_accounting_inputs()` to also read `uf.gross_amount` and `uf.net_amount` (legacy).
2. If `currency` is SEK and `gross_amount_original` is null but legacy `gross_amount` exists:
   - Set `gross_amount_original = gross_amount`
   - Set `net_amount_original = net_amount` if present
   - Persist those back to `unified_files` (single UPDATE, same transaction).
3. Continue using the existing SEK invariant logic already present in the function.

**Acceptance criteria**

- AI4 runs for SEK receipts that previously failed only due to missing `*_original` while legacy totals were present.
- `unified_files.gross_amount_original` becomes populated for those receipts.

------

### T-021 — Ensure DB prompts are correct and reproducible (AI2/AI3/AI4)

**Goal:** Make prompt content stable across environments.

**Evidence:** Prompts are stored in DB (`ai_system_prompts` insert in `mind_db_dump.sql`, line containing all keys including `expense_classification`, `data_extraction`, `accounting_classification`).
SoT also defines the prompt table structure. (`docs/source_of_truth/70_AI_PROMPTS_AND_ROLES.md:~350–370`).

**Files touched**

- Add “upsert prompts” migration:
  - `database/migrations/00XZ_upsert_ai_prompts_from_files.sql`
- Add canonical prompt files:
  - `docs/ai_prompts/AI2_expense_classification.md`
  - `docs/ai_prompts/AI3_data_extraction.md`
  - `docs/ai_prompts/AI4_accounting_classification.md`

**Step-by-step changes**

1. Export current prompt texts from DB into those files (one-time).
2. Migration should upsert by `prompt_key` and replace `prompt_content` with file content.
   - Use a deterministic approach compatible with your migration runner (if migrations can’t read files directly, embed the content in the SQL migration explicitly).

**Acceptance criteria**

- The DB prompt content equals the canonical file content after migration.
- The UI “AI” prompt editor shows the same content.

------

### T-022 — Backfill AI4 for already-imported receipts lacking proposals

**Goal:** Generate proposals where AI4 never ran or produced none.

**Files touched**

- Add a one-off script:
  - `backend/tools/backfill_ai4.py` (or similar)

**Step-by-step changes**

1. Query for receipts:
   - file_type='receipt'
   - ai_status in ('completed','manual_review') as appropriate
   - no rows in `ai_accounting_proposals` for that file_id
   - has totals (post T-020)
2. Call the existing pipeline entry for AI4 (the same one used in normal processing), not an ad-hoc reimplementation.
3. Write progress logs with file_id counts.

**Acceptance criteria**

- After running the script, the count of receipts without proposals drops as expected:

```sql
SELECT COUNT(*) AS missing_ai4
FROM unified_files uf
LEFT JOIN ai_accounting_proposals ap ON ap.file_id = uf.id
WHERE uf.file_type='receipt'
  AND uf.ai_status IN ('completed','manual_review')
  AND ap.id IS NULL;
```

------

## Phase 4 — UI: add MANUAL indicator in Process list

### T-030 — Add “MANUAL” column with `!`

**Goal:** In Process list, show a MANUAL column where manual-review items display `!`.

**Evidence:** Manual state is represented by `unified_files.ai_status='manual_review'`. (`backend/src/api/receipts.py` comment lists valid values, and `_mark_manual_review()` updates `ai_status` to `'manual_review'`).

**Files touched**

- `main-system/app-frontend/src/ui/pages/Process.jsx`

**Step-by-step changes**

1. Add a table column header: **MANUAL**
2. In each row render:
   - `!` if `receipt.ai_status === 'manual_review'`
   - empty otherwise
3. Do not change sorting/filtering behavior unless required.

**Acceptance criteria**

- Any receipt with `ai_status=manual_review` shows `!` in the MANUAL column.

------

## Phase 5 — Make date filters and manual match list not drop receipts with null purchase_datetime

### T-040 — Use COALESCE(purchase_datetime, created_at) in list endpoint date filters

**Goal:** Fix cases where lists show “nothing/few” because `purchase_datetime` is null.

**Evidence:** `list_receipts()` uses `purchase_datetime >= %s` / `<= %s` directly. (`backend/src/api/receipts.py:~940–1010`).

**Files touched**

- `backend/src/api/receipts.py`

**Step-by-step changes**

1. Replace date filters:
   - `purchase_datetime >= %s` → `COALESCE(purchase_datetime, created_at) >= %s`
   - `purchase_datetime <= %s` → `COALESCE(purchase_datetime, created_at) <= %s`

**Acceptance criteria**

- Filtering by date shows receipts even if purchase_datetime is null, based on created_at fallback.

------

## Test & verification plan (mandatory)

### Unit-level smoke checks (fast)

1. **AI2 classification**
   Feed OCR snippets (or real OCR text from DB) into `run_ai2_expense_classification()`:
   - Contains “MasterCard **** 9995” → personal
   - Contains “MasterCard **** 6779” → corporate
   - Contains “VISA” → personal
   - Contains “Swish” → personal
2. **FirstCard candidates**
   Call the manual candidates endpoint and verify:
   - No personal receipts returned
   - Receipts with null purchase_datetime still appear via created_at

### Integration (Dockerized)

1. Bring stack up:

```powershell
docker compose --profile main up -d --build
```

1. Run:

- Upload a small set of receipts + a FirstCard invoice and execute:
  - auto match endpoint (the route in `reconciliation_firstcard/routes/matching.py` calls `auto_match_invoice_lines()`)
  - manual candidates view

### DB validation queries

1. No corporate+9995:

```sql
SELECT COUNT(*) FROM unified_files
WHERE credit_card_last_4_digits=9995 AND expense_type='corporate';
```

1. No FC line matched to personal:

```sql
SELECT COUNT(*) 
FROM invoice_lines il
JOIN unified_files uf ON uf.id=il.matched_file_id
WHERE uf.expense_type='personal' AND il.matched_file_id IS NOT NULL;
```

1. AI4 proposals coverage:

```sql
SELECT COUNT(*) AS receipts_without_ai4
FROM unified_files uf
LEFT JOIN ai_accounting_proposals ap ON ap.file_id=uf.id
WHERE uf.file_type='receipt'
  AND uf.ai_status IN ('completed','manual_review')
  AND ap.id IS NULL;
```

### Encoding verification (å/ä/ö end-to-end)

- Pick a receipt with Swedish characters in merchant/name/text.
- Confirm:
  1. OCR text in DB contains correct characters
  2. API response preserves them
  3. UI renders them without mojibake

------

## Final validation checklist

-  AI2: Visa never yields corporate.
-  AI2: MC-9995 yields personal.
-  FC matching: only corporate receipts are considered candidates.
-  FC auto matching: ambiguous candidate sets do not auto-link.
-  Manual match screens show expected candidates (created_at fallback works).
-  AI4 proposals exist for eligible receipts; backlog backfill reduces missing count.
-  Process list displays MANUAL column with `!` for `ai_status='manual_review'`.

------

