# **📌 MIND – RECEIPT PIPELINE REPAIR PLAN (FOR AGENT EXECUTION)**

### **Objective:**

Fix the broken receipt conversion flow (AI3 → company resolution → DB persistence → preview DTO) and update the codebase to fully align with the corrected SoT.

---

# **1. Scope of Work**

You must update **backend, AI pipeline, company lookup logic, persistence layer, and DTO mapping** to guarantee:

1. AI3 extraction runs correctly and returns required fields.
2. Company auto-matching and auto-creation work 100% reliably.
3. unified_files and receipt_items fields are persisted correctly.
4. Preview API returns correct data for UI.
5. All flows match the new SoT definitions.

**No other parts of the system may be changed.**

---

# **2. Files You MUST Review and Modify**

You must locate and update the following files:

### **Backend – AI3 and pipeline**

* `backend/src/api/ai_processing.py`
* `backend/src/services/ai_service.py`
* `backend/src/services/tasks/ai_pipeline_tasks.py`

### **Company resolution**

* `backend/src/services/company_service.py`
* `backend/src/repositories/company_repository.py`

### **Receipt persistence**

* `backend/src/services/unified_file_service.py`
* `backend/src/services/receipt_service.py`
* `backend/src/repositories/receipt_repository.py`

### **Receipt preview DTO**

* `backend/src/api/receipts.py`
* `backend/src/serializers/receipt_dto.py` (or equivalent serializer)

### **Database migrations (only IF required)**

* `database/migrations/` → validate schema alignment

### **Frontend (read-only; verify DTO mapping)**

* `main-system/app-frontend/src/ui/pages/Receipt.jsx`
* `main-system/app-frontend/src/components/ReceiptPreview.jsx`

---

# **3. Required Functional Fixes (MANDATORY)**

## **3.1 Fix AI3 JSON contract handling**

Implement the following validations:

1. **AI3 output must include:**

   * `company`
   * `unified_file`
   * `receipt_items`
   * `company_match_type`
   * `company_create_needed`

2. If fields are missing:

   * Log AI error
   * Move file to manual review
   * Do NOT continue pipeline

3. Normalize:

   * decimals (`,` → `.`)
   * date format → `"YYYY-MM-DD HH:MM:SS"`

---

## **3.2 Implement deterministic company resolution (MATCH OR CREATE)**

You MUST implement EXACTLY this resolution order:

### **(1) VAT MATCH**

If AI3 returned `company.vat`:

* Clean format (remove spaces/“-”/non-digits)
* Query: `SELECT * FROM companies WHERE vat = ? LIMIT 1`
* If found:

  * `company_id = id`
  * `company_match_type = "vat"`

### **(2) NAME MATCH**

If VAT match did not succeed:

* Normalize name:

  * lowercase
  * trim
  * collapse whitespace
  * normalize å/ä/ö → a/o/o (for matching only)
* Query companies table:

  * Exact match
  * Starts-with match
  * Fuzzy > 0.85

If found:

* `company_id = id`
* `company_match_type = "name"`

### **(3) NO MATCH → AUTO-CREATE (MANDATORY)**

If no match on VAT or name:

* Create new row in `companies` using AI3 company fields
* Set `company_id` to newly created ID
* Set `company_match_type = "new"`

**This logic is NOT optional.
It must always run and never silently fail.**

---

## **3.3 Persist unified_files fields EXACTLY as defined in SoT**

You must update the existing unified_files row with:

* company_id
* purchase_datetime
* payment_type
* expense_type
* currency
* gross_amount_original
* net_amount_original
* exchange_rate
* gross_amount_sek
* net_amount_sek
* receipt_number
* other_data (ensure JSON string)

If a value is missing in AI3 output:

* store NULL
* NEVER guess or auto-fill

---

## **3.4 Persist receipt_items**

For each item in AI3 output:

* Delete old items for this file
* Insert new items
* Ensure VAT math is consistent with SoT rules
* Currency = unified_file.currency

---

## **3.5 Ensure status transitions are correct**

You MUST verify:

* OCR → `ocr_done`
* AI3 success → AI stage succeeds
* Company resolution → new internal stage `company_resolved`
* Persistence → `ai_status = completed`
* Any error → `ai_status = manual_review`

**Illegal transitions must be prevented.**

---

## **3.6 Fix the receipt preview DTO**

The preview endpoint MUST return:

### **company block**

Always populated from `companies` table via `unified_files.company_id`.

If `company_id` is NULL at this point:

* This is a pipeline error and must raise an exception
* UI may NOT show empty company block

### **receipt block**

Values come from `unified_files` columns.

### **items block**

Values come from `receipt_items`.

### **ai block**

Retrieve AI confidence from AI history table or stored JSON.

---

# **4. Required SoT Alignment**

You MUST update code to fully align with the new SoT documents:

* `MIND2_RECEIPTS_DATA_MODEL_v2.md`
* `MIND2_RECEIPTS_PIPELINE_AI3_v2.md`
* `MIND2_RECEIPTS_PREVIEW_UI_v2.md`

This means:

* Naming must match.
* Required fields must exist.
* Mandatory auto-create company must be implemented.
* Preview DTO must match SoT exactly.

---

# **5. Test Scenarios (Agent MUST confirm manually)**

### **Test 1 – Existing company, VAT match**

* VAT present
* Matches existing company
* `company_id` is set
* Preview shows company data

### **Test 2 – Existing company, name match**

* VAT absent
* Name matches existing
* `company_id` is set
* Preview shows company data

### **Test 3 – No match → auto-create**

* No VAT
* Name does not match
* New company created
* unified_files.company_id set to new value
* Preview shows newly created company

### **Test 4 – Missing AI3 fields**

* AI3 returns incomplete JSON
* File must end in `manual_review`
* No partial writes allowed

### **Test 5 – Full preview validation**

* Preview shows:

  * company
  * receipt info
  * items
  * other_data

---

# **6. Deliverables**

The agent MUST deliver:

### ✔ Updated code for ALL required files

(backend + persistence + DTO)

### ✔ Validation notes for each test scenario

### ✔ Confirmation that:

* AI3 works
* company resolution works
* company auto-create works
* persistence works
* preview DTO matches SoT
* UI shows correct values

### ✔ Updated SoT documents (already provided)

---

# **7. Hard constraints**

* No unrelated changes allowed.
* No refactoring outside the described areas.
* No silent failures.
* No mocked data or invented values.
* ALL steps above MUST be implemented.

---

If you want, I can now also generate:

✅ A **diff-style patch plan**
or
✅ A **commit message template** for the agent

…bara säg till.
