# MIND - AI Implementation

```
Filename: MIND_AI.1.0.md
Version: 1.0.
```

## Changelog

| Version | Date       | Changes  | Author            |
| ------- | ---------- | -------- | ----------------- |
| 1.0     | 2025-09-29 | Original | Mattias Cederlund |
|         |            |          |                   |
|         |            |          |                   |

_____________

### unified_files:

| Field                   | Type          | Null | Key  | Comment                                               |
| ----------------------- | ------------- | ---- | ---- | ----------------------------------------------------- |
| id                      | varchar(36)   | NO   | PRI  |                                                       |
| file_type               | varchar(32)   | NO   |      |                                                       |
| created_at              | timestamp     | YES  |      |                                                       |
| updated_at              | timestamp     | YES  |      |                                                       |
| orgnr                   | varchar(32)   | YES  |      | Company Organization Number                           |
| payment_type            | varchar(255)  | NO   |      | Enter "cash" or "card"                                |
| purchase_datetime       | datetime      | YES  |      | Date and time on the receipt                          |
| expense_type            | varchar(255)  | NO   |      | If this is bought using a private card or cash (pe... |
| gross_amount_original   | decimal(12,2) | YES  |      | amount inc vat                                        |
| net_amount_original     | decimal(12,2) | YES  |      | amount ex vat                                         |
| exchange_rate           | decimal(12,0) | NO   |      | exchange rate example: 1 USD=11.33 SEK                |
| currency                | varchar(222)  | NO   |      | currency that was bought in                           |
| gross_amount_sek        | decimal(10,0) | NO   |      | only used for foreign currency - shows the gross a... |
| net_amount_sek          | decimal(10,0) | NO   |      | The net amount in SEK after exchange conversion       |
| ai_status               | varchar(32)   | YES  |      |                                                       |
| ai_confidence           | float         | YES  |      |                                                       |
| mime_type               | varchar(222)  | YES  |      |                                                       |
| ocr_raw                 | text          | NO   |      | The raw ocr-text without coordinates from the pict... |
| company_id              | int           | NO   |      | companies.id - refering to the company that sold t... |
| receipt_number          | varchar(255)  | NO   |      | the unique receipt number                             |
| file_creation_timestamp | timestamp     | YES  |      | picked from the file when its fetched from ftp        |
| submitted_by            | varchar(64)   | YES  |      | the logged in user that submitted the file            |
| original_file_id        | varchar(36)   | YES  |      |                                                       |
| original_file_name      | varchar(222)  | YES  |      |                                                       |
| original_file_size      | int           | YES  |      |                                                       |
| file_suffix             | varchar(32)   | YES  |      | File extension without dot                            |
| file_category           | int           | YES  |      | Reference to file_categories.id                       |
| original_filename       | varchar(255)  | YES  |      |                                                       |
| approved_by             | int           | NO   |      | user id that approved the receipt                     |
| other_data              | text          | NO   |      | This is for all other data available on the receip... |
| credit_card_match       | tinyint(1)    | NO   |      | When matching receipt is available set 1              |

## receipt_items

| Field                    | Type          | Null | Key  | Default  | Comment                                               |
| ------------------------ | ------------- | ---- | ---- | -------- | ----------------------------------------------------- |
| id                       | int           | NO   | PRI  | *NULL*   |                                                       |
| main_id                  | int           | NO   |      | *NULL*   | Referes to the unified_files.id                       |
| article_id               | varchar(222)  | NO   |      | *NULL*   | The unique product or article number that comes fr... |
| name                     | varchar(222)  | NO   |      | *NULL*   | Product name                                          |
| number                   | int           | NO   |      | *NULL*   | The number of this item that was bought               |
| item_price_ex_vat        | decimal(10,2) | NO   |      | 0.00     |                                                       |
| item_price_inc_vat       | decimal(10,2) | NO   |      | 0.00     |                                                       |
| item_total_price_ex_vat  | decimal(10,2) | NO   |      | 0.00     |                                                       |
| item_total_price_inc_vat | decimal(10,2) | NO   |      | 0.00     |                                                       |
| currency                 | varchar(11)   | NO   |      | SEK      |                                                       |
| vat                      | decimal(10,2) | NO   |      | 0.00     |                                                       |
| vat_percentage           | decimal(7,6)  | NO   |      | 0.000000 |                                                       |



## companies

| Field    | Type         | Null | Key  | Comment                          |
| -------- | ------------ | ---- | ---- | -------------------------------- |
| id       | int          | NO   | PRI  |                                  |
| name     | varchar(234) | NO   |      | The name of the company          |
| orgnr    | varchar(22)  | NO   |      | The company organization number. |
| address  | int          | NO   |      | Street address                   |
| address2 | varchar(222) | NO   |      | Extra addres row                 |
| zip      | varchar(123) | NO   |      | Zip-code                         |
| city     | varchar(234) | NO   |      | City of the company              |
| country  | varchar(234) | NO   |      | Country of the company           |
| phone    | varchar(234) | NO   |      | Phone number to company          |
| www      | varchar(234) | NO   |      | Company homepage                 |





## credit_card_invoices_main

| Field                | Type            | Key  | Default | Comment                              |
| -------------------- | --------------- | ---- | ------- | ------------------------------------ |
| id                   | bigint unsigned | PRI  | *NULL*  | Primary key, internal unique ID      |
| main_id              | bigint unsigned | MUL  | *NULL*  | FK to creditcard_invoices_main.id    |
| line_no              | int             |      | *NULL*  | Line number within invoice (1..N)    |
| transaction_id       | varchar(64)     |      | *NULL*  | Transaction reference from issuer    |
| purchase_date        | date            | MUL  | *NULL*  | Date purchase occurred               |
| posting_date         | date            |      | *NULL*  | Date transaction was posted          |
| merchant_name        | varchar(200)    | MUL  | *NULL*  | Name of merchant/vendor              |
| merchant_city        | varchar(100)    |      | *NULL*  | City of merchant                     |
| merchant_country     | char(2)         |      | *NULL*  | ISO 3166-1 alpha-2 country code      |
| mcc                  | varchar(4)      |      | *NULL*  | Merchant Category Code               |
| description          | text            |      | *NULL*  | Free-text transaction description    |
| currency_original    | char(3)         |      | *NULL*  | Original currency code (ISO 4217)    |
| amount_original      | decimal(13,2)   |      | *NULL*  | Original amount in currency_original |
| exchange_rate        | decimal(18,6)   |      | *NULL*  | Exchange rate applied (orig → SEK)   |
| amount_sek           | decimal(13,2)   |      | *NULL*  | Amount converted to SEK              |
| vat_rate             | decimal(5,2)    |      | *NULL*  | Applicable VAT rate (%)              |
| vat_amount           | decimal(13,2)   |      | *NULL*  | VAT amount in SEK                    |
| net_amount           | decimal(13,2)   |      | *NULL*  | Net amount excluding VAT             |
| gross_amount         | decimal(13,2)   |      | *NULL*  | Gross amount incl. VAT               |
| cost_center_override | varchar(100)    |      | *NULL*  | Optional cost center override        |
| project_code         | varchar(100)    |      | *NULL*  | Optional project code for accounting |



## credit_card_invoice_items

| Field                | Type            | Key  | Comment                              |
| -------------------- | --------------- | ---- | ------------------------------------ |
| id                   | bigint unsigned | PRI  | Primary key, internal unique ID      |
| main_id              | bigint unsigned | MUL  | FK to creditcard_invoices_main.id    |
| line_no              | int             |      | Line number within invoice (1..N)    |
| transaction_id       | varchar(64)     |      | Transaction reference from issuer    |
| purchase_date        | date            | MUL  | Date purchase occurred               |
| posting_date         | date            |      | Date transaction was posted          |
| merchant_name        | varchar(200)    | MUL  | Name of merchant/vendor              |
| merchant_city        | varchar(100)    |      | City of merchant                     |
| merchant_country     | char(2)         |      | ISO 3166-1 alpha-2 country code      |
| mcc                  | varchar(4)      |      | Merchant Category Code               |
| description          | text            |      | Free-text transaction description    |
| currency_original    | char(3)         |      | Original currency code (ISO 4217)    |
| amount_original      | decimal(13,2)   |      | Original amount in currency_original |
| exchange_rate        | decimal(18,6)   |      | Exchange rate applied (orig → SEK)   |
| amount_sek           | decimal(13,2)   |      | Amount converted to SEK              |
| vat_rate             | decimal(5,2)    |      | Applicable VAT rate (%)              |
| vat_amount           | decimal(13,2)   |      | VAT amount in SEK                    |
| net_amount           | decimal(13,2)   |      | Net amount excluding VAT             |
| gross_amount         | decimal(13,2)   |      | Gross amount incl. VAT               |
| cost_center_override | varchar(100)    |      | Optional cost center override        |
| project_code         | varchar(100)    |      | Optional project code for accounting |
