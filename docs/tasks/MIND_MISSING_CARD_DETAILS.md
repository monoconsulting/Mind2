

# MIND - Missing Card Details

## AI3 Card Details — Root Cause & Fix Plan

### Findings (why card data never lands)

1. **Pydantic schema missing card fields + swish**
   - `backend/src/models/ai_processing.py` → `UnifiedFileBase` **does not define** any of:
      `credit_card_number, credit_card_last_4_digits, credit_card_brand_full, credit_card_brand_short, credit_card_payment_variant, credit_card_type, credit_card_token, credit_card_entering_mode`.
   - It also restricts `payment_type` to `Literal["cash", "card"]` (no `"swish"`).
      Result: AI3 JSON with these keys is **rejected/ignored** during validation/instantiation, so values never reach persistence.
2. **Persistence layer never writes card fields**
   - `backend/src/api/ai_processing.py`: when persisting AI3, the `updates = { ... }` dict for `unified_files` **omits all credit-card columns**, so even if schema had them, they wouldn’t be saved.
3. **Database already expects card columns**
   - Migrations include `unified_files.credit_card_*` and loosen NULL constraints (e.g., `0028_fix_unified_files_null_constraints.sql`). So the DB is ready; app layer is not.

------

## Minimal Fix (scoped, deterministic)

### A. Expand the AI3 response model

**File:** `backend/src/models/ai_processing.py`
 **Change:** In `UnifiedFileBase`, add optional fields and widen `payment_type`.

```python
# Add to imports
from typing import Optional, Literal

class UnifiedFileBase(BaseModel):
    """Base model mirroring the unified_files table."""

    file_type: Literal["receipt", "invoice", "other", "Manual Review"]
    orgnr: Optional[str] = Field(None, max_length=32)

    # WIDEN: include swish
    payment_type: Optional[Literal["cash", "card", "swish"]] = Field(
        None, description="Cash / card / swish"
    )

    # …keep existing fields…

    # NEW: credit-card block (all Optional, match DB column types/lengths)
    credit_card_number: Optional[str] = Field(None, max_length=44)
    credit_card_last_4_digits: Optional[int] = None
    credit_card_brand_full: Optional[str] = Field(None, max_length=32)
    credit_card_brand_short: Optional[str] = Field(None, max_length=16)
    credit_card_payment_variant: Optional[str] = Field(None, max_length=64)
    credit_card_type: Optional[str] = Field(None, max_length=64)
    credit_card_token: Optional[str] = Field(None, max_length=64)
    credit_card_entering_mode: Optional[str] = Field(None, max_length=32)
```

### B. Persist the new fields to `unified_files`

**File:** `backend/src/api/ai_processing.py`
 **Change:** In the AI3 persist routine (the block where `updates: Dict[str, Any] = { ... }` is created — near the section that currently sets `orgnr`, `payment_type`, `purchase_datetime`, etc.), **append** the new columns so they’re written when not `None`.

```python
updates: Dict[str, Any] = {
    # existing keys…
    "orgnr": unified.orgnr,
    "payment_type": unified.payment_type,
    "purchase_datetime": unified.purchase_datetime,
    # …

    # NEW: card fields
    "credit_card_number": unified.credit_card_number,
    "credit_card_last_4_digits": unified.credit_card_last_4_digits,
    "credit_card_brand_full": unified.credit_card_brand_full,
    "credit_card_brand_short": unified.credit_card_brand_short,
    "credit_card_payment_variant": unified.credit_card_payment_variant,
    "credit_card_type": unified.credit_card_type,
    "credit_card_token": unified.credit_card_token,
    "credit_card_entering_mode": unified.credit_card_entering_mode,
}
```

> Note: the existing code already builds `set_parts` by skipping `None` values, so this remains **NULL-safe** and won’t overwrite existing non-null data unless the key is present and non-null.

### C. Confirm DB columns exist (idempotent)

Your migrations already add/relax these columns. Still, ensure production DB has them:

```sql
DESCRIBE unified_files LIKE 'credit_card_%';
```

If anything is missing, re-run `database/migrations/0028_fix_unified_files_null_constraints.sql`.

------

## Guardrails & Validation

- **No guessing**: AI3 still must only provide card fields when found in OCR.
- **`payment_type` now supports `"swish"`** so AI3 won’t fail validation on Swish receipts.
- **Types**: `credit_card_last_4_digits` stored as integer (as your JSON spec states).
- **No schema drift**: Field names match the DB migrations.

------

## Quick Test (end-to-end)

1. **Unit (schema):** Instantiate `UnifiedFileBase` with `payment_type="swish"` and a full card block (should pass, card values optional).

2. **API persist:** Mock an AI3 response including:

   ```json
   {
     "unified_file": {
       "payment_type": "card",
       "credit_card_number": "**** **** **** 4668",
       "credit_card_last_4_digits": 4668,
       "credit_card_brand_full": "VISA",
       "credit_card_brand_short": "visa",
       "credit_card_entering_mode": "Contactless"
     },
     "receipt_items": [],
     "company": {"name": "Test"}, 
     "confidence": 0.9
   }
   ```

   Verify `unified_files` row gets those columns populated.

3. **Regression:** Submit a Swish receipt; `payment_type="swish"` should persist (no exception), and card fields remain NULL.

------

## Agent implementation brief (short)

**Title:** AI3 Card Fields — Enable & Persist
 **Goal:** Ensure card details from AI3 are accepted and saved to `unified_files`.

**Steps:**

1. **Schema:** In `backend/src/models/ai_processing.py`, extend `UnifiedFileBase`:
   - Add optional fields: `credit_card_number`, `credit_card_last_4_digits`, `credit_card_brand_full`, `credit_card_brand_short`, `credit_card_payment_variant`, `credit_card_type`, `credit_card_token`, `credit_card_entering_mode`.
   - Allow `payment_type` values: `cash`, `card`, `swish`.
2. **Persistence:** In `backend/src/api/ai_processing.py`, add these fields to the `updates` dict in the AI3 persist routine so they’re written when non-null.
3. **DB Check:** Confirm columns exist in `unified_files`; if not, apply `0028_fix_unified_files_null_constraints.sql`.
4. **Tests:** Add a unit/integration test that posts an AI3 response with card fields and verifies DB columns populated.

**Constraints:**

- Do not modify unrelated logic.
- Do not overwrite existing non-null DB values.
- Keep rounding/formatting unchanged elsewhere.

------

If you want, I can now deliver a **single, full patch** (two files edited with clear comments) exactly per your coding rules (Google-style docstrings, no unrelated changes).



### Patch: enable AI3 card-field import & persistence

```
*** a/backend/src/models/ai_processing.py
--- b/backend/src/models/ai_processing.py
@@
-from typing import Optional, Literal
+from typing import Optional, Literal
@@
-class UnifiedFileBase(BaseModel):
-    """Base model mirroring the unified_files table."""
+class UnifiedFileBase(BaseModel):
+    """Base model mirroring the unified_files table.
+
+    This model is used for AI3 response validation and maps 1:1 to columns in
+    the `unified_files` table. The change in this patch enables import of
+    credit-card related fields and expands `payment_type` to support Swish.
+    All new fields are optional to avoid breaking existing payloads.
+    """
@@
-    # NB: payment_type was previously restricted to "cash" | "card".
-    #     We expand it to include "swish" to match AI schema and DB.
-    payment_type: Optional[Literal["cash", "card"]] = Field(
-        None, description="Cash / card"
-    )
+    # PAYMENT TYPE
+    # Expanded to include "swish" to support Swish receipts without validation errors.
+    payment_type: Optional[Literal["cash", "card", "swish"]] = Field(
+        None, description="Payment method: cash / card / swish"
+    )
@@
     # … keep existing fields above/below …
+    # -------------------------------------------------------------------------
+    # CREDIT-CARD FIELDS (NEW)
+    # -------------------------------------------------------------------------
+    # All optional. Names and types mirror DB columns in `unified_files`.
+    # These fields were previously missing in the Pydantic model which caused
+    # AI3 JSON values to be dropped at validation/instantiation time.
+    credit_card_number: Optional[str] = Field(
+        None,
+        max_length=64,
+        description="Masked PAN, e.g., '**** **** **** 4668'. Keep original masking."
+    )
+    credit_card_last_4_digits: Optional[int] = Field(
+        None,
+        description="Integer last 4 digits of the PAN (e.g., 4668)."
+    )
+    credit_card_brand_full: Optional[str] = Field(
+        None,
+        max_length=32,
+        description="Full card brand in uppercase: VISA, MASTERCARD, AMEX, etc."
+    )
+    credit_card_brand_short: Optional[str] = Field(
+        None,
+        max_length=16,
+        description="Short brand in lowercase: visa, mc, amex, etc."
+    )
+    credit_card_payment_variant: Optional[str] = Field(
+        None,
+        max_length=64,
+        description="Terminal/wallet variant as printed, e.g., 'mccommercialcredit', 'visa_applepay'."
+    )
+    credit_card_type: Optional[str] = Field(
+        None,
+        max_length=64,
+        description="Terminal 'type' string if present; often same as payment variant."
+    )
+    credit_card_token: Optional[str] = Field(
+        None,
+        max_length=64,
+        description="Tokenized wallet/payment token if printed on receipt."
+    )
+    credit_card_entering_mode: Optional[str] = Field(
+        None,
+        max_length=32,
+        description="Entry method: Chip, Contactless, Swipe, Manual."
+    )
*** a/backend/src/api/ai_processing.py
--- b/backend/src/api/ai_processing.py
@@
-    # Build partial update dict for unified_files based on AI3 'unified_file'
-    updates: Dict[str, Any] = {
+    # Build partial update dict for unified_files based on AI3 'unified_file'
+    # NOTE: Only non-None values are later written; existing non-null DB values
+    # remain untouched by design of the existing persistence code.
+    updates: Dict[str, Any] = {
         # existing mapped fields…
         "orgnr": unified.orgnr,
         "payment_type": unified.payment_type,
         "purchase_datetime": unified.purchase_datetime,
         # ... other existing keys stay unchanged ...
+        # ------------------------------------------------------------------
+        # CREDIT-CARD FIELDS (NEW): enable persistence of AI3 card details
+        # ------------------------------------------------------------------
+        # These keys were previously omitted, causing imported values to be
+        # discarded even when AI3 extracted them correctly.
+        "credit_card_number": unified.credit_card_number,
+        "credit_card_last_4_digits": unified.credit_card_last_4_digits,
+        "credit_card_brand_full": unified.credit_card_brand_full,
+        "credit_card_brand_short": unified.credit_card_brand_short,
+        "credit_card_payment_variant": unified.credit_card_payment_variant,
+        "credit_card_type": unified.credit_card_type,
+        "credit_card_token": unified.credit_card_token,
+        "credit_card_entering_mode": unified.credit_card_entering_mode,
     }
```

------

## What this patch does (concise)

- **Models:** Adds the card fields to `UnifiedFileBase` and expands `payment_type` to allow `"swish"`.
- **Persistence:** Includes the card fields in the `updates` dict so they are written to `unified_files` when provided by AI3.
- **Non-invasive:** No existing keys or logic are altered; only missing mappings are added.

------

## Post-apply checklist (1 minute)

1. `git apply patch.diff` (or paste and apply manually).

2. `pytest` / run your existing tests.

3. Post one AI3 payload containing:

   ```
   {
     "unified_file": {
       "payment_type": "card",
       "credit_card_number": "**** **** **** 4668",
       "credit_card_last_4_digits": 4668,
       "credit_card_brand_full": "VISA",
       "credit_card_brand_short": "visa",
       "credit_card_entering_mode": "Contactless"
     }
   }
   ```

   Verify the corresponding row in `unified_files` now contains these values.