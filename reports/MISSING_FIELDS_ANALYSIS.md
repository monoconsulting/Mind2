# MISSING_FIELDS_ANALYSIS (from missing_per_receipt_2025-12-21_165628.csv)
Date: 2025-12-21

## CSV summary (top missing categories)
Source: `reports/missing_per_receipt_2025-12-21_165628.csv`.

| Missing field category | Count in CSV | Example file_ids |
|---|---:|---|
| credit_card_last_4_digits | 6 | 4395f85a-81ae-4c64-bfaa-2aa7ce8672df, 3f3ec231-11ca-478a-9d61-80b619394afa, 2fc66e35-585a-42a3-8749-665eacc36126, 1a2dd79a-0e92-436c-8f6a-fb251f3efb80, 0bf9ef71-1380-45fb-ac46-17a1ecd4101f, 0bda6c99-c456-407d-8925-f660c73663b1 |
| payment_type | 2 | e4669830-1b66-4d7c-b9c5-e349722e6a58, d374ea63-2bbe-49c6-aef9-666b0b2bb7dd |
| credit_card_brand_short | 2 | 2fc66e35-585a-42a3-8749-665eacc36126, 0bda6c99-c456-407d-8925-f660c73663b1 |
| vat_breakdown(total_vat_25/12/6) | 1 | d374ea63-2bbe-49c6-aef9-666b0b2bb7dd |
| receipt_items | 1 | 2fc66e35-585a-42a3-8749-665eacc36126 |

**Note on the “13 examples” requirement:** the top-5 categories above cover **8 unique** receipts in this CSV, so there are not 13 distinct IDs available without repeating; this is constrained by the input data.

## DB evidence for the 8 receipts
Unified_files snapshot:
```
SELECT id, file_type, workflow_type, payment_type, currency,
       gross_amount_original, net_amount_original,
       gross_amount_sek, net_amount_sek, exchange_rate,
       total_vat_25, total_vat_12, total_vat_6,
       credit_card_brand_short, credit_card_last_4_digits,
       company_id, ai_status
FROM unified_files
WHERE id IN (
  '0bda6c99-c456-407d-8925-f660c73663b1',
  '0bf9ef71-1380-45fb-ac46-17a1ecd4101f',
  '1a2dd79a-0e92-436c-8f6a-fb251f3efb80',
  '2fc66e35-585a-42a3-8749-665eacc36126',
  '3f3ec231-11ca-478a-9d61-80b619394afa',
  '4395f85a-81ae-4c64-bfaa-2aa7ce8672df',
  'd374ea63-2bbe-49c6-aef9-666b0b2bb7dd',
  'e4669830-1b66-4d7c-b9c5-e349722e6a58'
);

id                                   file_type  workflow_type  payment_type  currency  gross_amount_original  net_amount_original  gross_amount_sek  net_amount_sek  exchange_rate  total_vat_25  total_vat_12  total_vat_6  credit_card_brand_short  credit_card_last_4_digits  company_id  ai_status
0bda6c99-c456-407d-8925-f660c73663b1  receipt    receipt        card          SEK       1947.00                1557.60             1947.00           1557.60         1.000000      389.40         NULL          NULL         NULL                     NULL                        46          completed
0bf9ef71-1380-45fb-ac46-17a1ecd4101f  receipt    receipt        card          SEK       2980.00                2384.00             2980.00           2384.00         1.000000      596.00         NULL          NULL         MASTERCARD               NULL                        5           completed
1a2dd79a-0e92-436c-8f6a-fb251f3efb80  receipt    receipt        card          SEK       2980.00                2384.00             2980.00           2384.00         1.000000      596.00         NULL          NULL         MASTERCARD               NULL                        5           completed
2fc66e35-585a-42a3-8749-665eacc36126  receipt    receipt        card          SEK       138.13                110.50              138.13            110.50          1.000000      27.63          NULL          NULL         NULL                     NULL                        104         completed
3f3ec231-11ca-478a-9d61-80b619394afa  receipt    receipt        card          SEK       558.30                446.64              558.30            446.64          1.000000      111.66         NULL          NULL         MASTERCARD               NULL                        17          completed
4395f85a-81ae-4c64-bfaa-2aa7ce8672df  receipt    receipt        card          SEK       2790.00               2232.00             2790.00           2232.00         1.000000      558.00         NULL          NULL         VISA                     NULL                        62          completed
d374ea63-2bbe-49c6-aef9-666b0b2bb7dd  receipt    receipt        NULL          SEK       680.00                680.00              680.00            680.00          1.000000      NULL           NULL          NULL         NULL                     NULL                        57          completed
e4669830-1b66-4d7c-b9c5-e349722e6a58  receipt    receipt        NULL          USD       12.50                 10.00               NULL              NULL             NULL          2.50           NULL          NULL         NULL                     NULL                        51          completed
```

Receipt items counts:
```
SELECT main_id, COUNT(*) AS item_count
FROM receipt_items
WHERE main_id IN (
  '0bda6c99-c456-407d-8925-f660c73663b1',
  '0bf9ef71-1380-45fb-ac46-17a1ecd4101f',
  '1a2dd79a-0e92-436c-8f6a-fb251f3efb80',
  '2fc66e35-585a-42a3-8749-665eacc36126',
  '3f3ec231-11ca-478a-9d61-80b619394afa',
  '4395f85a-81ae-4c64-bfaa-2aa7ce8672df',
  'd374ea63-2bbe-49c6-aef9-666b0b2bb7dd',
  'e4669830-1b66-4d7c-b9c5-e349722e6a58'
)
GROUP BY main_id;

main_id                              item_count
0bda6c99-c456-407d-8925-f660c73663b1  1
0bf9ef71-1380-45fb-ac46-17a1ecd4101f  1
1a2dd79a-0e92-436c-8f6a-fb251f3efb80  1
3f3ec231-11ca-478a-9d61-80b619394afa  4
4395f85a-81ae-4c64-bfaa-2aa7ce8672df  1
d374ea63-2bbe-49c6-aef9-666b0b2bb7dd  1
e4669830-1b66-4d7c-b9c5-e349722e6a58  1
```

## Root-cause mapping (top 5 categories)
### 1) credit_card_last_4_digits
- **Where it should be populated:** AI3 LLM output → `UnifiedFileBase.credit_card_last_4_digits` in `run_ai3_data_extraction` (`backend/src/services/ai_service.py:961-992`), persisted to `unified_files` in `_persist_extraction_result` (`backend/src/api/ai_processing.py:527-555`).
- **Evidence it is missing in DB:** see unified_files query above (six receipts with NULL last_4). 
- **Exact reason (code-level):** There is no deterministic fallback for last-4 in persistence; `_persist_extraction_result` writes whatever AI3 provided, and AI3 only assigns `card_last_4` from `unified_data` (`backend/src/services/ai_service.py:961-992`). If AI3 payload omits last-4, the DB field stays NULL. (`backend/src/services/ai_service.py:961-992`; `backend/src/api/ai_processing.py:527-555`).

### 2) payment_type
- **Where it should be populated:** AI3 LLM output → `UnifiedFileBase.payment_type` in `run_ai3_data_extraction` (`backend/src/services/ai_service.py:969-975`), persisted to `unified_files.payment_type` in `_persist_extraction_result` (`backend/src/api/ai_processing.py:527-533`).
- **Evidence it is missing in DB:** `payment_type` is NULL for `d374ea63-2bbe-49c6-aef9-666b0b2bb7dd` and `e4669830-1b66-4d7c-b9c5-e349722e6a58` (see query above).
- **Exact reason (code-level):** Persistence does not synthesize payment_type; the field is written as-is from AI3's `unified_file` payload (`backend/src/services/ai_service.py:969-975`; `backend/src/api/ai_processing.py:527-533`). Missing values therefore originate in AI3 output.

### 3) credit_card_brand_short
- **Where it should be populated:** AI3 LLM output → `UnifiedFileBase.credit_card_brand_short` (`backend/src/services/ai_service.py:985-989`), persisted to `unified_files.credit_card_brand_short` (`backend/src/api/ai_processing.py:549-551`).
- **Evidence it is missing in DB:** NULL for `2fc66e35-585a-42a3-8749-665eacc36126` and `0bda6c99-c456-407d-8925-f660c73663b1` (see query above).
- **Exact reason (code-level):** No deterministic fallback exists; AI3 payload must provide brand_short and persistence writes it directly (`backend/src/services/ai_service.py:985-989`; `backend/src/api/ai_processing.py:549-551`).

### 4) vat_breakdown(total_vat_25/12/6)
- **Where it should be populated:** `_persist_extraction_result` computes VAT totals from `vat_summary` (AI3 `other_data`) or from gross-net when a VAT rate is detected (`backend/src/api/ai_processing.py:479-523`).
- **Evidence it is missing in DB:** `total_vat_25/12/6` are NULL for `d374ea63-2bbe-49c6-aef9-666b0b2bb7dd` (see query above).
- **Exact reason (code-level):** VAT totals are only derived if `vat_summary` is present or if a VAT rate is detected (`vat_rates_detected`) alongside gross/net (`backend/src/api/ai_processing.py:479-523`). When AI3 output does not include VAT summary/rates, the totals remain NULL.

### 5) receipt_items
- **Where it should be populated:** AI3 LLM output must include `receipt_items` (`backend/src/services/ai_service.py:1013-1040`), which are persisted with `_replace_receipt_items` (`backend/src/api/ai_processing.py:317-377`).
- **Evidence it is missing in DB:** No `receipt_items` rows exist for `2fc66e35-585a-42a3-8749-665eacc36126` (no row in the receipt_items query above).
- **Exact reason (code-level):** If AI3 returns an empty list, `_replace_receipt_items` deletes old items and inserts none; `_run_ai_pipeline` explicitly logs when item_count=0 but does not block persistence (`backend/src/services/tasks/ai_pipeline_tasks.py:287-368`, `_replace_receipt_items` `backend/src/api/ai_processing.py:317-377`).

## Additional missing categories (tied count = 1)
### sek_amounts(gross_amount_sek/net_amount_sek) + exchange_rate
- **Where they should be populated:** AI3 output can provide `gross_amount_sek`/`net_amount_sek` and `exchange_rate` (`backend/src/services/ai_service.py:976-979`), persisted in `_persist_extraction_result` (`backend/src/api/ai_processing.py:527-543`). `_load_accounting_inputs` only auto-fills SEK totals and exchange_rate when currency == SEK (`backend/src/services/tasks/file_management_tasks.py:453-466`).
- **Evidence it is missing in DB:** `e4669830-1b66-4d7c-b9c5-e349722e6a58` is USD with NULL SEK totals and exchange_rate (see query above).
- **Exact reason (code-level):** For non-SEK currency, no deterministic conversion is applied; missing SEK totals and exchange_rate must originate from AI3 payload (no fallback in `_load_accounting_inputs`) (`backend/src/services/tasks/file_management_tasks.py:453-466`).
