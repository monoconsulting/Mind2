# Receipt Preview Modal 

Actions: 

Paymenttype=swish

Make all fields editable

Make it possible to scroll all 3 columns indiviually

Previous column: unified_files.orgnr CHANGED TO unified_files.vat

Added columns in unified_files - **ADD THESE TO SCHEMA**

|      | 10   | credit_card_number          | varchar(44)  | utf8mb4_0900_ai_ci |      | Nej  | *Inget* |                                     |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=credit_card_number&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
| ---- | ---- | --------------------------- | ------------ | ------------------ | ---- | ---- | ------- | ----------------------------------- | ---- | ------------------------------------------------------------ | ------------------------------------------------------------ | ---- |
|      | 11   | credit_card_last_4_digits   | int          |                    |      | Nej  | *Inget* | Example: 4668                       |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=credit_card_last_4_digits&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
|      | 12   | credit_card_type            | varchar(44)  | utf8mb4_0900_ai_ci |      | Nej  | *Inget* | Example: mccommercialcredit         |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=credit_card_type&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
|      | 13   | credit_card_brand_full      | varchar(22)  | utf8mb4_0900_ai_ci |      | Nej  | *Inget* | Example: MASTERCARD, VISA           |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=credit_card_brand_full&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
|      | 14   | credit_card_brand_short     | varchar(22)  | utf8mb4_0900_ai_ci |      | Nej  | *Inget* | Example: mc, visa                   |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=credit_card_brand_short&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
|      | 15   | credit_card_payment_variant | varchar(222) | utf8mb4_0900_ai_ci |      | Nej  | *Inget* | Example: mccommercialcredit         |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=credit_card_payment_variant&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
|      | 16   | credit_card_token           | varchar(222) | utf8mb4_0900_ai_ci |      | Nej  | *Inget* | Example: mc_applepay, visa_applepay |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=credit_card_token&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
|      | 17   | credit_card_entering_mode   | varchar(222) | utf8mb4_0900_ai_ci |      | Nej  | *Inget* | Example: Kontaktlöst chip           |      |                                                              |                                                              |      |

|      | 20   | total_vat_25 | decimal(12,2) |      |      | Ja   | *NULL*  | total vat amount 25% |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=total_vat_25&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
| ---- | ---- | ------------ | ------------- | ---- | ---- | ---- | ------- | -------------------- | ---- | ------------------------------------------------------------ | ------------------------------------------------------------ | ---- |
|      | 21   | total_vat_12 | decimal(12,2) |      |      | Nej  | *Inget* | total vat amount 12% |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=total_vat_12&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |
|      | 22   | total_vat_6  | decimal(12,2) |      |      | Nej  | *Inget* | total vat amount 6%  |      | [![Ändra](http://localhost:8087/themes/dot.gif) Ändra](http://localhost:8087/index.php?route=/table/structure/change&db=mono_se_db_9&table=unified_files&field=total_vat_6&change_column=1) | [![Radera](http://localhost:8087/themes/dot.gif) Radera](http://localhost:8087/index.php?route=/sql) |      |



## Left side (2 columns)

#### Grunddata (box 1)

| Företag - companies.name       | Organisationsnummer - companies.orgnr |
| ------------------------------ | ------------------------------------- |
| **Adress** - companies.address | Adress 2 - companies.address2         |
| Postnummer - companies.zip     | Ort - companies.city                  |
| Land - companies.country       | www - companies.www                   |
| Telefonnummer: companies.phone | Email: companies.email                |



#### Betalningstyp (box 2)

| Inköpsdatum - unified_files.purchase_datetime   | Kvittonnummer - unified_files.receipt_number          |
| ----------------------------------------------- | ----------------------------------------------------- |
| Betalningstyp - unified_files.payment_type      | Utgiftstyp - unified_files.expense_type               |
| Kortnummer - unified_files.credit_card_number   | Kortnummer 4 sista - unified_files.credit_card_last_4 |
| Korttyp - unified_files.credit_card_brand_full  | Korttyp kort - unified_files.credit_card_brand_short  |
| Korttyp token - unified_files.credit_card_token |                                                       |

#### Belopp (box 3)

| Valuta - unified_files.currency                              | Växlingskurs - unified_files. exchange_rate                  |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| Originalbelopp ink. moms - unified_files.gross_amount        | Originalbelopp ex. moms - unified_files.net_amount           |
| Svenskt totalbelopp ink moms SEK - unified_files.gross_amount_sek | Svenskt totalbelopp ex. moms SEK - unified_files.net_amount_SEK |
| Moms 25% - unified_files.total_vat_25                        | Moms 12% - unified_files.total_vat_12                        |
| Moms 6% - unified_files.total_vat_6                          |                                                              |

#### Övrigt (box 4 - 1 kolumn längst ner lika bred som de andra två tillsammans)

| Övrig data - unified_files.other_data |
| ------------------------------------- |



## Right side

This table should consist of two tables in one. 

The first one should only tell the row number. The second one should contain all the data for the specific item including accounting.

One row for each accounting is the standard so this means that this has to be filled in correct from the db. Today it looks like this 

### ai_accounting_proposals

| id   | receipt_id                           | item_id | account_code | debit  | credit | vat_rate | notes               | created_at          |
| ---- | ------------------------------------ | ------- | ------------ | ------ | ------ | -------- | ------------------- | ------------------- |
| 1    | 4abf6968-05f3-4593-88f1-9e475496fba2 | 94      | 6110         | 209.44 | 0.00   | 25.00    | Kontorsvaror        | 2025-10-03 20:21:53 |
| 2    | 4abf6968-05f3-4593-88f1-9e475496fba2 | 94      | 2641         | 52.36  | 0.00   | 25.00    | Ingående moms 25%   | 2025-10-03 20:21:53 |
| 3    | 4abf6968-05f3-4593-88f1-9e475496fba2 | 94      | 2890         | 0.00   | 262.00 | 0.00     | Skuld till anställd | 2025-10-03 20:21:53 |

This would result in a table like this (only accounting specified):

**IMPORTANT!! ALL THE ACCOUNTING POSTS MUST BE LISTED. IF THE AMOUNT HAS DATA IN DEBIT COLUMN THEN IT IS DEBET:XXXX IF IT IS IN CREDIT COLUMN IT IS KREDIT XXXX**

Table 1: RAD 1

Table 2 (inside 1) below

| Artikelnummer - receipt_items.article_id                     | Artikel - receipt_items.name                                 | Antal - receipt_items.number                      |                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------- | ------------------------------------- |
| Belopp ex. moms - receipt_items.item_price_ex_vat            | Belopp ink. moms - receipt_items.item_price_inc_vat          | Belopp moms - receipt_items.vat                   | Moms % - receipt_items.vat_percentage |
| Belopp totalt ex. moms - receipt_items.item_total_price_ex_vat | Belopp totalt ink. moms - receipt_items.item_total_price_ink_vat | Belopp moms totalt - receipt_items.item_vat_total | Moms % - receipt_items.vat_percentage |
| Debet: 6110                                                  | Belopp: 209.44                                               | Momssats: 25%                                     | Kontorsvaror                          |
| Debet: 2641                                                  | Belopp: 52.36                                                | Momssats: 25%                                     | Ingående moms 25%                     |
| Kredit: 2890                                                 | Belopp: 262.00                                               | Momssats: 0%                                      | Skuld till anställd                   |

Here is the complete template

**IMPORTANT!! ALL THE ACCOUNTING POSTS MUST BE LISTED. IF THE AMOUNT HAS DATA IN DEBIT COLUMN THEN IT IS DEBET:XXXX IF IT IS IN CREDIT COLUMN IT IS KREDIT XXXX**

| Artikelnummer - receipt_items.article_id                     | Artikel - receipt_items.name                                 | Antal - receipt_items.number                      |                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------- | ------------------------------------- |
| Belopp ex. moms - receipt_items.item_price_ex_vat            | Belopp ink. moms - receipt_items.item_price_inc_vat          | Belopp moms - receipt_items.vat                   | Moms % - receipt_items.vat_percentage |
| Belopp totalt ex. moms - receipt_items.item_total_price_ex_vat | Belopp totalt ink. moms - receipt_items.item_total_price_ink_vat | Belopp moms totalt - receipt_items.item_vat_total | Moms % - receipt_items.vat_percentage |
| Debet ELLER Kredit konto - ai_accounting_proposals.account_code | Debet eller kredit belopp - ai_accounting_proposals.debit OR ai_accounting_proposals.kredit | ai_accounting_proposals.vat_rate                  | ai_accounting_proposals.notes         |











- Systemprompt

- Role:
  You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.
  Do not set expense_type or document_type here (handled elsewhere).

  Merchant name rule (critical):
  Extract the COMPANY NAME from the TOP of the receipt — never from amount lines.

  The company name is usually the first line or near the top.

  NEVER use lines containing SUMMA, TOTAL, BELOPP, ATT BETALA as company name.

  NEVER use amount lines (e.g., 123.45) as company name.

  Banks (Handelsbanken, Nordea, Swedbank, etc.) are not merchants/shops.

  Normalization rules:

  Dates: YYYY-MM-DD HH:MM:SS. If time missing ⇒ use 00:00:00.

  Numbers: Accept , or . as decimal separator; normalize to ..

  VAT math: net = gross / (1 + rate), vat = gross - net.

  Currencies:

  currency is ISO-4217 (e.g., SEK, USD, EUR).

  If currency == "SEK" ⇒ exchange_rate = 0 (no FX conversion).

  If foreign currency ⇒ exchange_rate = SEK per 1 unit foreign, in basis points (bps).

  Example: 11.33 SEK per 1 USD ⇒ exchange_rate = 1133.

  Conversion: amount_sek = round(amount_foreign * (exchange_rate / 100)).

  SEK rounding: gross_amount_sek and net_amount_sek are integers (round to whole kronor).

  Unknowns: If not found with high confidence ⇒ use null.

  Do not invent data.

  Swedish org. number: May appear as Org.nr, Organisationsnummer, etc.; format typically NNNNNN-XXXX.

  Return one JSON object exactly in this structure

  All empty/unknown fields must be null (not invented).
  Arrays may be empty if no items can be parsed confidently.
  other_data is a JSON string with key–value pairs for extra parsed metadata.

  {
    "company": {
      "name": null,
      "orgnr": null,
      "address": null,
      "zip": null,
      "city": null,
      "country": "Sweden",
      "phone": null,
      "www": null
    },
    "unified_file": {
      "id": null,
      "company_id": null,
      "file_type": null,
      "created_at": null,
      "updated_at": null,

      "purchase_datetime": null,
      "receipt_number": null,
      
      "payment_type": null,
      "credit_card_number": null,
      "credit_card_last_4_digits": null,
      "credit_card_type": null,
      "credit_card_brand_full": null,
      "credit_card_brand_short": null,
      "credit_card_payment_variant": null,
      "credit_card_token": null,
      "credit_card_entering_mode": null,
      
      "currency": "SEK",
      "exchange_rate": 0,
      
      "gross_amount_original": null,
      "net_amount_original": null,
      
      "total_vat_25": null,
      "total_vat_12": null,
      "total_vat_6": null,
      
      "gross_amount_sek": 0,
      "net_amount_sek": 0,
      
      "gross_amount": null,
      "net_amount": null,
      
      "ai_status": null,
      "ai_confidence": null,
      
      "submitted_by": null,
      
      "original_filename": null,
      "original_file_id": null,
      "original_file_name": null,
      "file_creation_timestamp": null,
      "original_file_size": null,
      "mime_type": null,
      
      "ocr_raw": null,
      
      "file_suffix": null,
      "file_category": null,
      
      "approved_by": 0,
      
      "other_data": null,
      "credit_card_match": 0,
      "content_hash": null
        },
        "receipt_items": [
          {
            "main_id": null,
            "article_id": null,
            "name": null,
            "number": null,  
            "item_price_ex_vat": null,
            "item_price_inc_vat": null,
            "item_total_price_ex_vat": null,
            "item_total_price_inc_vat": null,
            "currency": "SEK",
            "vat": null,
            "vat_percentage": null
      }
            
  ```
  
  ```

  

      
    ],
    "confidence": null
  }

  Field-by-field extraction guidance (high level)

  company: Parse from header block; prefer legal name near top; cross-check with orgnr pattern.

  purchase_datetime: Look for explicit date/time; support Swedish formats; normalize to ISO; if time missing ⇒ 00:00:00.

  payment_type: One of card, cash, swish (if clearly stated).

  credit_card*: Populate only if present (PAN masked, last4, brand MASTERCARD/VISA, token *_applepay etc.).

  currency: If currency symbol/code detected, set accordingly; else SEK.

  exchange_rate:

  If currency == "SEK" ⇒ 0.

  Else compute SEK/foreign in bps (multiply by 100 and round to integer).

  gross/net (original currency):

  Parse line items and totals; infer VAT distribution across 25/12/6 when possible.

  Set both gross_amount_original & gross_amount (same value).

  Set both net_amount_original & net_amount (same value).

  SEK amounts:

  If currency == "SEK":

  gross_amount_sek = round(gross_amount)

  net_amount_sek = round(net_amount)

  If foreign:

  gross_amount_sek = round(gross_amount * (exchange_rate/100))

  net_amount_sek = round(net_amount * (exchange_rate/100))

  VAT totals: Fill total_vat_25, total_vat_12, total_vat_6 when identifiable; otherwise null.

  other_data: JSON-stringify terminal/AID/trace/reference IDs or any non-mapped metadata.

  receipt_items:

  number is quantity (integer).

  item_price_* are per-unit; item_total_* are per line (quantity × price).

  currency mirrors header currency; vat = item_total_price_inc_vat - item_total_price_ex_vat; vat_percentage in decimal (e.g., 0.25).

  confidence: 0.0–1.0 overall extraction confidence.
  # JSON Contract (Deterministic Extractor for Swedish receipts/invoices)

  ## General rules

  * **Dates:** `YYYY-MM-DD HH:MM:SS`. If time missing → use `00:00:00`.
  * **Numbers:** Accept `,` or `.`; **normalize to `.`**.
  * **VAT math:** `net = gross / (1 + rate)`; `vat = gross - net`.
  * **Currency:**

    * `currency` is ISO-4217 (e.g., `SEK`, `USD`, `EUR`).
    * If `currency == "SEK"` → `exchange_rate = 0`.
    * If foreign currency → `exchange_rate` is **SEK per 1 foreign unit, in basis points (bps)**.
      Example: `1 USD = 11.33 SEK` → `exchange_rate = 1133`.
    * Conversion to SEK (integer kronor):
      `amount_sek = round(amount_foreign * (exchange_rate / 100))`.
  * **SEK rounding:** `gross_amount_sek`, `net_amount_sek` are **integers** (whole kronor).
  * **Unknowns:** If not confidently found → `null`. Do **not** invent values.
  * **Merchant name:** take from the **top** header; never from amount/total lines.
  * **Banks ≠ merchants:** Handelsbanken, Nordea, Swedbank etc. are not shops.

  ---

  ## `company` (object)

  * **`name`**
    **Meaning:** Legal/trading name at the top of the receipt/invoice (header area).
    **How to fill:** Take the first plausible header line; exclude lines containing totals (`SUMMA`, `TOTAL`, `ATT BETALA`, etc.) and numeric price lines.
    **Example:** `"IKEA Barkarby"`

  * **`orgnr`**
    **Meaning:** Swedish organization number, if present.
    **How to fill:** Look for patterns like `Org.nr`, `Organisationsnummer`.
    **Example:** `"556074-7569"`

  * **`address`**
    **Meaning:** Street address.
    **Example:** `"Ekgatan 12"`

  * **`zip`**
    **Meaning:** Postal code.
    **Example:** `"169 67"`

  * **`city`**
    **Meaning:** City/town.
    **Example:** `"Solna"`

  * **`country`**
    **Meaning:** Country name; default `"Sweden"` if not stated.
    **Example:** `"Sweden"`

  * **`phone`**
    **Meaning:** Merchant phone number, if printed.
    **Example:** `"+46 8 123 45 67"`

  * **`www`**
    **Meaning:** Merchant website, if printed.
    **Example:** `"www.ikea.se"`

  ---

  ## `unified_file` (object)

  > Only the fields you listed are included. Fields not confidently found → `null`.
  > **Do not** set `expense_type` or `document_type` here (handled elsewhere).

  * **`id`** (`varchar(36)`)
    **Meaning:** Primary key UUID for this file/record. Often assigned by your system.
    **How to fill:** If the AI does not know it at extraction time, return `null`.
    **Example:** `null` or `"2f8a8d7c-3f6f-4a9a-8b0a-1a2b3c4d5e6f"`

  * **`company_id`** (`int`, default `0`)
    **Meaning:** FK to `companies.id` (seller).
    **How to fill:** If unknown at extraction time, return `null` (or your pipeline may later map it).
    **Example:** `null`

  * **`file_type`** (`varchar(32)`)
    **Meaning:** Classified file type.
    **How to fill:** Use the value from your upstream classifier (e.g., `"receipt"`, `"invoice"`, `"other"`).
    **Example:** `"receipt"`

  * **`created_at`** (`timestamp`, default `CURRENT_TIMESTAMP`)
    **Meaning:** Record creation time in DB.
    **How to fill:** Usually set by DB; AI can return `null`.
    **Example:** `null`

  * **`updated_at`** (`timestamp`)
    **Meaning:** Record update time in DB.
    **How to fill:** Usually set by DB; AI can return `null`.
    **Example:** `null`

  * **`purchase_datetime`** (`datetime`)
    **Meaning:** Purchase date/time on the receipt/invoice.
    **How to fill:** Parse printed date/time; if only date exists, set time to `00:00:00`.
    **Example:** `"2025-09-30 14:23:00"`

  * **`receipt_number`** (`varchar(255)`)
    **Meaning:** Receipt/invoice reference (e.g., `Ordernummer`, `Kvittonummer`).
    **How to fill:** Extract exact printed value.
    **Example:** `"KV-938475"`

  * **`payment_type`** (`varchar(255)`)
    **Meaning:** Payment method.
    **How to fill:** One of `"card"`, `"cash"`, `"swish"` when clearly stated.
    **Example:** `"card"`

  * **`credit_card_number`** (`varchar(44)`)
    **Meaning:** Masked PAN as printed (never full PAN).
    **How to fill:** Use exactly as printed (e.g., `**** **** **** 4668`).
    **Example:** `"**** **** **** 4668"`

  * **`credit_card_last_4_digits`** (`int`)
    **Meaning:** Last 4 digits of the card.
    **How to fill:** Derive from printed masked card if available.
    **Example:** `4668`

  * **`credit_card_type`** (`varchar(44)`)
    **Meaning:** Processor/terminal product type string, if printed.
    **Example:** `"mccommercialcredit"`

  * **`credit_card_brand_full`** (`varchar(22)`)
    **Meaning:** Full brand name.
    **Example:** `"MASTERCARD"` or `"VISA"`

  * **`credit_card_brand_short`** (`varchar(22)`)
    **Meaning:** Short brand code.
    **Example:** `"mc"` or `"visa"`

  * **`credit_card_payment_variant`** (`varchar(222)`)
    **Meaning:** Variant string printed by terminal/acquirer.
    **Example:** `"mccommercialcredit"`

  * **`credit_card_token`** (`varchar(222)`)
    **Meaning:** Tokenized network or wallet marker.
    **Example:** `"mc_applepay"`, `"visa_applepay"`

  * **`credit_card_entering_mode`** (`varchar(222)`)
    **Meaning:** Entry mode as printed.
    **Example:** `"Kontaktlöst chip"`, `"Chip"`, `"Magstripe"`

  * **`gross_amount_original`** (`decimal(12,2)`)
    **Meaning:** Total **incl. VAT** in the **original transaction currency**.
    **How to fill:** The printed grand total including VAT.
    **Example:** `123.45`

  * **`net_amount_original`** (`decimal(12,2)`)
    **Meaning:** Total **excl. VAT** in the **original transaction currency**.
    **How to fill:** Compute if not printed: `gross / (1 + weighted_vat_rate)`; otherwise use printed net.
    **Example:** `98.76`

  * **`total_vat_25`** (`decimal(12,2)`)
    **Meaning:** Total VAT amount at 25% in the original currency.
    **How to fill:** From VAT breakdown or compute per lines.
    **Example:** `24.69` (or `null` if not identifiable)

  * **`total_vat_12`** (`decimal(12,2)`)
    **Meaning:** Total VAT amount at 12% in the original currency.
    **Example:** `0.00` (or `null` if not identifiable)

  * **`total_vat_6`** (`decimal(12,2)`)
    **Meaning:** Total VAT amount at 6% in the original currency.
    **Example:** `0.00` (or `null` if not identifiable)

  * **`exchange_rate`** (`decimal(12,0)`, default `0`)
    **Meaning:** **SEK per 1 foreign unit, in basis points**.
    **How to fill:**

    * If `currency == "SEK"` → `0`.
    * If foreign: multiply SEK rate by `100`, round to integer.
      **Example:** `1133` (for `1 USD = 11.33 SEK`)

  * **`currency`** (`varchar(222)`, default `SEK`)
    **Meaning:** Transaction currency (ISO-4217).
    **Example:** `"SEK"`, `"USD"`, `"EUR"`

  * **`gross_amount_sek`** (`decimal(10,0)`, default `0`)
    **Meaning:** Total incl. VAT in **SEK**, rounded to whole kronor.
    **How to fill:**

    * If `currency == "SEK"`: `round(gross_amount_original)`
    * Else: `round(gross_amount_original * (exchange_rate/100))`
      **Example:** `139`

  * **`net_amount_sek`** (`decimal(10,0)`, default `0`)
    **Meaning:** Total excl. VAT in **SEK**, rounded to whole kronor.
    **How to fill:**

    * If `currency == "SEK"`: `round(net_amount_original)`
    * Else: `round(net_amount_original * (exchange_rate/100))`
      **Example:** `111`

  * **`gross_amount`** (`decimal(12,2)`)
    **Meaning:** Duplicate of “gross incl. VAT in original currency” (kept for compatibility).
    **How to fill:** Same as `gross_amount_original`.
    **Example:** `123.45`

  * **`net_amount`** (`decimal(12,2)`)
    **Meaning:** Duplicate of “net excl. VAT in original currency” (kept for compatibility).
    **How to fill:** Same as `net_amount_original`.
    **Example:** `98.76`

  ---

  ## `receipt_items` (array of objects)

  Each element represents one line item parsed from the receipt/invoice.

  * **`main_id`**
    **Meaning:** FK to the parent file/record (your `unified_file.id`).
    **How to fill:** If unknown at extraction time, set `null`.
    **Example:** `null`

  * **`article_id`**
    **Meaning:** SKU/article code if printed.
    **Example:** `"SKU-12345"` (or `null`)

  * **`name`**
    **Meaning:** Item name/description as printed.
    **Example:** `"Cappuccino 33cl"`

  * **`number`**
    **Meaning:** Quantity (integer).
    **Example:** `2`

  * **`item_price_ex_vat`**
    **Meaning:** Unit price excluding VAT, in the header `currency`.
    **Example:** `10.00`

  * **`item_price_inc_vat`**
    **Meaning:** Unit price including VAT, in the header `currency`.
    **Example:** `12.50`

  * **`item_total_price_ex_vat`**
    **Meaning:** Line total excluding VAT = `number × item_price_ex_vat`.
    **Example:** `20.00`

  * **`item_total_price_inc_vat`**
    **Meaning:** Line total including VAT = `number × item_price_inc_vat`.
    **Example:** `25.00`

  * **`currency`**
    **Meaning:** Currency for item amounts; mirror the header `currency`.
    **Example:** `"SEK"`

  * **`vat`**
    **Meaning:** VAT amount for the line = `item_total_price_inc_vat - item_total_price_ex_vat`.
    **Example:** `5.00`

  * **`vat_percentage`**
    **Meaning:** VAT rate as a decimal.
    **Example:** `0.25` (for 25%), `0.12`, `0.06`

  ---

  ## `confidence` (number)

  * **Meaning:** Overall extraction confidence (0.0–1.0).
  * **How to fill:** Calibrated model score or heuristic confidence.
  * **Example:** `0.87`

  ---

  ## Worked mini-examples

  ### A) Purchase in SEK

  ```json
  {
    "company": { "name": "Pressbyrån T-Centralen", "orgnr": "556000-0000", "address": "Centralplan 1", "zip": "111 20", "city": "Stockholm", "country": "Sweden", "phone": null, "www": null },
    "unified_file": {
      "id": null,
      "company_id": null,
      "file_type": "receipt",
      "created_at": null,
      "updated_at": null,
      "purchase_datetime": "2025-09-30 14:23:00",
      "receipt_number": "KV-938475",
      "payment_type": "card",
      "credit_card_number": "**** **** **** 4668",
      "credit_card_last_4_digits": 4668,
      "credit_card_type": "mccommercialcredit",
      "credit_card_brand_full": "MASTERCARD",
      "credit_card_brand_short": "mc",
      "credit_card_payment_variant": "mccommercialcredit",
      "credit_card_token": "mc_applepay",
      "credit_card_entering_mode": "Kontaktlöst chip",
      "gross_amount_original": 123.45,
      "net_amount_original": 98.76,
      "total_vat_25": 24.69,
      "total_vat_12": null,
      "total_vat_6": null,
      "exchange_rate": 0,
      "currency": "SEK",
      "gross_amount_sek": 123,
      "net_amount_sek": 99,
      "gross_amount": 123.45,
      "net_amount": 98.76
    },
    "receipt_items": [
      {
        "main_id": null,
        "article_id": "SKU-CAF33",
        "name": "Cappuccino 33cl",
        "number": 1,
        "item_price_ex_vat": 27.20,
        "item_price_inc_vat": 34.00,
        "item_total_price_ex_vat": 27.20,
        "item_total_price_inc_vat": 34.00,
        "currency": "SEK",
        "vat": 6.80,
        "vat_percentage": 0.25
      }
    ],
    "confidence": 0.92
  }
  ```

  ### B) Purchase in USD (with SEK conversion)

  ```json
  {
    "company": { "name": "Coffee NYC", "orgnr": null, "address": "123 5th Ave", "zip": "10003", "city": "New York", "country": "USA", "phone": null, "www": null },
    "unified_file": {
      "id": null,
      "company_id": null,
      "file_type": "receipt",
      "created_at": null,
      "updated_at": null,
      "purchase_datetime": "2025-09-15 09:10:00",
      "receipt_number": "R-10293",
      "payment_type": "card",
      "credit_card_number": "**** **** **** 4668",
      "credit_card_last_4_digits": 4668,
      "credit_card_type": null,
      "credit_card_brand_full": "VISA",
      "credit_card_brand_short": "visa",
      "credit_card_payment_variant": null,
      "credit_card_token": null,
      "credit_card_entering_mode": "Chip",
      "gross_amount_original": 10.50,
      "net_amount_original": 8.40,
      "total_vat_25": null,
      "total_vat_12": null,
      "total_vat_6": null,
      "exchange_rate": 1133,
      "currency": "USD",
      "gross_amount_sek": 12,
      "net_amount_sek": 10,
      "gross_amount": 10.50,
      "net_amount": 8.40
    },
    "receipt_items": [],
    "confidence": 0.85
  }
  ```

  ---

  ## Quick answers to your earlier points

  * Use **`gross_amount` / `net_amount`** (and the `_original` twins) for values in the **original transaction currency** (decimals).
  * Use **`gross_amount_sek` / `net_amount_sek`** for **SEK**, **rounded to integers**.
  * **`exchange_rate`**:

    * **SEK purchase:** `0` (not `1`).
    * **Foreign purchase:** SEK per 1 foreign unit, in **bps** (e.g., `11.33 SEK/USD` → `1133`).
    * Conversion: `amount_sek = round(amount_foreign * (exchange_rate/100))`.