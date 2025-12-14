Below is a **very explicit agent instruction** (English), with **hard boundaries**, **step-by-step tasks**, and **copy/paste prompts** you can give your agent. It is written to eliminate the class of mistakes we just found (migrations replay + prompt overwrites) and to restore the missing credit-card extraction reliably.

---

# Agent Instruction: Fix Migration Replay + Prompt Persistence + Restore Credit-Card Extraction

## Objective

1. **Stop destructive “replay” effects** from `database/migrations/*.sql` when migrations are applied multiple times.
2. Ensure **AI prompts edited in the UI** (stored in `ai_system_prompts`) **persist across restarts** and are **not overwritten** by migrations.
3. Restore **credit-card metadata extraction** in AI3 results (brand/last4/etc) by ensuring the active AI3 prompt includes those fields and rules, aligned with SoT.

## Non-negotiable Boundaries

* Do **not** change unrelated code. If a change is not required to achieve the objective, do not touch it.
* Do **not** delete existing SQL logic; if something must be removed, it must be **commented out** with a clear reason.
* Each task must be done in its **own branch**, committed, merged to `dev`, and pushed.
* Any migration change must be **safe**, **idempotent**, and **explainable** in SoT.
* No “seed” step may overwrite user-edited prompt content unless there is an explicit “force reset” action.

## Known Risk Areas (You Must Verify)

These have been observed in the codebase and must be treated as critical:

* `backend/src/services/db/migrations.py` currently **replays** migrations (no applied tracking).
* `database/migrations/0020_insert_ai_prompts.sql` and `0030_insert_ai6_credit_card_invoice_prompt.sql` contain `DELETE FROM ai_system_prompts...`
* `database/migrations/0027_receipt_preview_modal_enhancements.sql` contains `UPDATE ai_system_prompts SET prompt_content=...`
* `database/migrations/0036_reset_fc_processing.sql` and `0035_cleanup_fc_receipt_items.sql` contain `DELETE` operations that should not run repeatedly in production.

---

# Phase 0 — Safety and Repro

## Task 0.1: Create a DB backup and a reproducible test case

**Deliverable:** one short markdown note in the PR description: backup created + how to reproduce.

* Take a DB dump before changes.
* Reproduce the issue:

  * Change AI3 prompt in UI (or via API)
  * Run “apply migrations” / restart service
  * Confirm prompt reverted and credit-card fields missing again

**Acceptance:** You can show before/after evidence that prompt content was overwritten by migrations.

---

# Phase 1 — Implement Proper Migration Tracking (Stop Replay)

## Task 1.1: Add a migrations ledger table and apply-once logic

**Goal:** Each migration file runs **only once** per database.

### Requirements

* Add a table such as `schema_migrations` with:

  * `filename` (primary key)
  * `checksum` (optional but recommended)
  * `applied_at`
* In `backend/src/services/db/migrations.py`:

  * Read already-applied migrations from `schema_migrations`
  * Apply only those missing
  * Record each successfully applied file
* If there is an endpoint `/system/apply-migrations`, it must use the same safe logic.

### Important

* If checksum is implemented: if a file changed after applied, do **not** auto-reapply destructively. Instead log a warning and require a *new migration file* for changes.

**Acceptance Criteria**

* Running migrations twice results in **zero changes** on the second run.
* No prompt is overwritten by a second run.

**Branch name:** `fix/migrations-ledger`

---

# Phase 2 — Convert Prompt Seeding to Non-Destructive Behavior

## Task 2.1: Stop migrations from overwriting `ai_system_prompts`

**Goal:** Migrations may **seed** prompt rows if missing, but must **never** wipe/overwrite user content.

### Actions

* Identify all migrations that touch `ai_system_prompts`.
* Replace destructive patterns:

  * Remove or comment out `DELETE FROM ai_system_prompts ...`
  * Remove or comment out `UPDATE ai_system_prompts SET prompt_content=...`
* Replace with safe patterns:

  * Insert **only if missing**.
  * If an upsert is used, do **not** overwrite `prompt_content`.

### Notes

* If the schema does not enforce uniqueness by `prompt_key`, add it (or add a safe alternative). Use a new migration file if required.

**Acceptance Criteria**

* Edit AI3 prompt content in UI → run migrations → prompt stays unchanged.
* Edit AI6 prompt content in UI → run migrations → prompt stays unchanged.

**Branch name:** `fix/prompt-seeding-non-destructive`

---

# Phase 3 — Move One-Off Cleanup SQL Into One-Off Migrations (No Repeat Deletes)

## Task 3.1: Make FC cleanup/history reset one-time only

**Goal:** Anything that deletes real history/items must be one-time and never run again automatically.

### Actions

* Locate migrations like:

  * `0036_reset_fc_processing.sql` (deletes processing history)
  * `0035_cleanup_fc_receipt_items.sql` (deletes receipt items)
* Ensure they run **only once** by virtue of Phase 1 ledger.
* Additionally, review whether these belong as **manual admin actions** rather than migrations:

  * If the intent is operational cleanup, consider creating an **admin endpoint / CLI command** guarded by explicit confirmation, rather than a migration that can surprise you later.

**Acceptance Criteria**

* After ledger is added, verify these deletes are not repeated.
* Document in SoT runbook what the cleanup does and how to run it safely.

**Branch name:** `fix/one-off-cleanups`

---

# Phase 4 — Restore Credit Card Metadata Extraction (AI3)

## Task 4.1: Ensure the *active* AI3 prompt includes credit-card fields and extraction rules

**Goal:** `llm_result["unified_file"]` includes:

* `credit_card_number` (masked ok)
* `credit_card_last_4_digits`
* `credit_card_brand_full`
* `credit_card_brand_short`
* `credit_card_payment_variant`
* `credit_card_type`
* `credit_card_token`
* `credit_card_entering_mode`

### Actions

* Update the AI3 prompt content so it explicitly:

  * Defines those output keys under `unified_file`
  * Defines extraction rules for masked PAN, last4, and brand keywords (VISA/MC/AMEX etc)
  * States: **never invent card data**; only extract if present in OCR
* Apply the prompt change **without** relying on destructive migrations:

  * Prefer updating through your UI/API once
  * Or add a new *non-destructive* migration that inserts the prompt if missing, but does not overwrite.

### Validation

* Pick 2–3 receipts known to contain masked card number/brand text.
* Confirm the pipeline produces those fields again and that UI displays them.

**Acceptance Criteria**

* After processing, `unified_files` row has the credit-card fields populated when OCR contains them.
* Restart/apply-migrations does **not** remove them or revert prompt.

**Branch name:** `fix/ai3-credit-card-fields`

---

# Phase 5 — Tests & Guardrails (Prevent Regression)

## Task 5.1: Add regression tests for prompt persistence + migration idempotency

**Required tests**

1. Migration idempotency:

   * run apply-migrations twice
   * assert second run applies 0 migrations
2. Prompt persistence:

   * set `ai_system_prompts.prompt_content` to a custom value
   * run apply-migrations
   * assert it remains unchanged
3. AI3 mapping:

   * unit test that if LLM returns credit-card fields, they map into DB columns

**Acceptance Criteria**

* CI/local tests pass.
* You can demonstrate that the earlier failure mode cannot happen again.

**Branch name:** `test/migration-and-prompt-regression`

---

# Deliverables Checklist

* [ ] Ledger table + apply-once logic merged
* [ ] No destructive prompt resets in migrations
* [ ] One-off cleanup behavior documented and safe
* [ ] AI3 prompt updated to include credit-card output contract
* [ ] Regression tests added
* [ ] SoT updated (already provided in the updated SoT zip; ensure any additional changes are reflected)

---

# Copy/Paste Prompts for the Agent

## Prompt 1 — Repo scan & proof of overwrite

“Scan the repository for any SQL migrations that contain `DELETE FROM ai_system_prompts`, `UPDATE ai_system_prompts`, `DELETE FROM ai_processing_history`, or any destructive deletes against receipt items. List each file and the exact statements found. Then reproduce the prompt-overwrite issue end-to-end and provide evidence.”

## Prompt 2 — Implement migration ledger

“Implement migration tracking so that each SQL file is applied only once per DB. Add a `schema_migrations` table and update `backend/src/services/db/migrations.py` accordingly. Ensure `/system/apply-migrations` uses the safe logic. Provide a short test or proof showing the second run applies zero migrations.”

## Prompt 3 — Make prompt seeding non-destructive

“Modify the prompt-related migrations so they never delete or overwrite `ai_system_prompts.prompt_content`. Convert them to insert-only-if-missing logic. Ensure user-edited prompts persist across restarts and migration runs. Provide proof.”

## Prompt 4 — Restore AI3 credit-card extraction

“Update the AI3 ‘data_extraction’ prompt content to include the credit-card fields in `unified_file` and strict extraction rules. Apply the change in a way that does not rely on destructive migrations. Validate with real sample receipts that last4/brand returns again and persists after restart.”

## Prompt 5 — Regression tests

“Add tests for migration idempotency and prompt persistence. Ensure tests fail on old behavior and pass on new behavior. Provide test run output.”

---

If you want, I can also write a **single “master start prompt”** that your agent can run from and that includes the exact branch names + exact commit messages + merge sequence, but the above is already structured so the agent can execute without improvising.
