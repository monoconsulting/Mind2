# Mind - VAT Corrections

## Purpose

This step runs **after the file import is fully completed** and all records exist in the database.
 Its purpose is to **fill in missing numeric fields** in the `receipt_items` table, based on values that can be calculated from the same row or its parent record in `unified_files`.
 The process must be **fully deterministic** — no guessing, no overwriting existing values.

------

## Scope

- Operate only on table **`receipt_items`**
- Read complementary information from **`unified_files`**
- Update only fields that are currently **NULL**
- Never modify filled or header-level values

------

## Target fields (in `receipt_items`)

```
item_price_ex_vat
item_price_inc_vat
item_total_price_ex_vat
item_total_price_inc_vat
vat
vat_percentage
currency
```

------

## Source fields

From the same row or its parent in `unified_files`:

```
number
unified_files.total_vat_25
unified_files.total_vat_12
unified_files.total_vat_6
unified_files.currency
unified_files.exchange_rate
```

------

## VAT rates

Allowed values: **0.25**, **0.12**, **0.06**, **0.00**
 When calculating a rate, snap to the nearest valid value (tolerance ±0.005).

------

## Calculation logic

### 1. Basic formulas

```
item_total_price_ex_vat = number * item_price_ex_vat
item_total_price_inc_vat = number * item_price_inc_vat
vat = item_total_price_inc_vat - item_total_price_ex_vat
```

### 2. VAT rate detection

If missing (`vat_percentage` is NULL):

1. If both `item_price_inc_vat` and `item_price_ex_vat` exist:
    → `(inc/ex) - 1 = raw_rate`, snap to nearest allowed rate
2. Else if parent file (`unified_files`) has only one non-null total_vat_* field:
    → use its corresponding VAT rate
3. Else if both `item_total_price_ex_vat` and `item_total_price_inc_vat` exist:
    → derive `(inc/ex) - 1` and snap
4. Otherwise → leave NULL (no safe deduction)

### 3. Fill missing unit prices

If one price is missing and `vat_percentage` is known:

- `item_price_ex_vat = item_price_inc_vat / (1 + vat_percentage)`
- `item_price_inc_vat = item_price_ex_vat * (1 + vat_percentage)`

### 4. Fill totals

If `number` and both prices exist:

- `item_total_price_ex_vat = number * item_price_ex_vat`
- `item_total_price_inc_vat = number * item_price_inc_vat`
- `vat = item_total_price_inc_vat - item_total_price_ex_vat`

### 5. Currency

If `currency` is NULL → use `unified_files.currency`

------

## Update rules

- Only update NULL fields
- Round monetary values to **2 decimals**
- Never overwrite existing data
- Do not change `unified_files` totals
- Log all updated rows (table, id, fields changed, formulas used)

------

## Example decision chain

| Case                                | Available fields                   | Derived fields |
| ----------------------------------- | ---------------------------------- | -------------- |
| Only `item_price_inc_vat` + VAT 25% | ex_vat, totals, vat                |                |
| Both unit prices exist              | vat_percentage, totals, vat        |                |
| Only totals + quantity              | unit prices, vat                   |                |
| Missing everything                  | no update (flag for manual review) |                |

------

## Safe update criteria

A row can be updated only if:

1. Target field is NULL
2. All required source values are present
3. Derived VAT rate ∈ {0.25, 0.12, 0.06, 0.00}
4. Arithmetic result is internally consistent (inc = ex + vat ±0.01)

------

## Post-check (optional)

After all corrections:

- Compare total VAT per rate (25%, 12%, 6%) in `receipt_items` vs. `unified_files`
- If difference < 1.00 SEK → OK
- If larger → log warning but **do not modify headers**

------

## Logging example

Each update should be logged, e.g.:

```
{
  "table": "receipt_items",
  "row_id": 87,
  "action": "UPDATE_NULLS_ONLY",
  "fields_written": ["item_price_ex_vat", "item_total_price_ex_vat", "vat", "vat_percentage"],
  "source_fields": ["item_price_inc_vat", "number"],
  "notes": "Rate snapped 0.247→0.25; total difference <0.05 SEK"
}
```

------

## What the agent must **never** do

- Guess or assume values
- Overwrite non-null fields
- Modify totals in `unified_files`
- Create or delete records
- Use any VAT rate outside {0.00, 0.06, 0.12, 0.25}

------

## Summary

This step ensures all rows in `receipt_items` are **mathematically complete** and **VAT-consistent**.
 It provides a clean and verified dataset for later stages such as accounting proposals or analytics.

------

Would you like me to g