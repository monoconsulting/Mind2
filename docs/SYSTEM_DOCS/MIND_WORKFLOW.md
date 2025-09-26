# Workflow for processing files

This is the current workflow for file processing

### 1. File import 
File is imported from the ftp and inserted into the database together with the metadata from the JSON-file
### 2. OCR 
After the file is imported - the OCR should start using Paddle OCR 3.0. The data for the import should be stored in the database (what tables?)
### 3. AI - document type
AI will take a look at the ocr-text and decide the following:
- Is this a receipt ("kvitto")
- Is this an invoice ("faktura")
- Is this something else ("misc")
The database should then be updated and if it is not "kvitto", it should be removed for now, but saved in the database so we can handle it later

The system prompt for this should be handled from menu option "AI Systemprompter" and a text box with the name "Klassning av dokumenttyper"

### 4. AI - expense type
AI will investigate if this expense_type is private (egna utlägg) or company_card (företagskort). The system prompt for this will be defined in menu AI Systemprompter "Klassning av utgiftstyp"


### 5. AI - classification
All information on the receipt should now be analyzed and classified. The data should be stored in the following tables:
receipt_main: contains the general information on the receipt which is:
company_name
document_type
company_id
receipt_number
total_ex_vat
total_vat
total_incl_vat
buyer_type
buyer_name
buyer_phone
buyer_email
expense_type
cash
payment_card_name
payment_card_last4
payment_card_identifier
payment_card_variant
payment_token
payment_details
purchase_date
reference_number
customer_number
customer_name
customer_address
contact_person
phone_number
email
item_list
item_list_string
items_price
approved_by
currency
exchange_rate
ver_number
ver_date
description
original_filename
mimeType
fileExtension
file_prefix_expense_type

receipt_items:
This contains every single item that is bought:
id (referes to receipt_main)
row_id (row on the receipt - 1=first item, 2 is second and so on)
vat_percentage
vat_amount
item_price_ex_vat_each
item_price_inc_vat_each
item_price_ex_vat_total
item_price_inc_vat_total
item_description
item_number (how many items of this sort?)
