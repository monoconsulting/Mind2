# Workflow for processing files

This is the current workflow for file processing

## Step 1 – Import

- Import file from FTP.

## Step 2 – OCR

- Configure OCR settings under the menu **“Settings/OCR”**.
- Raw, unprocessed text must be inserted into `unified_files.ocr_raw` **without positional information**.
- JSON-files should be created in the storage area

## Step 3 – AI Analysis

### AI1 – Document Type Classification

- Configure this under the menu **“AI”**.
- Create a system prompt named **“Document Analysis”**.
- Allow model selection depending on available models defined in `.env`.
- Task: analyze the OCR text/image and determine the **document type**:
  - **receipt**, **invoice**, or **other**.
- Insert result into `unified_files.file_type`.
- If text exists but cannot be classified as a receipt, set the value to **“Manual Review”**.
  - This means the process stops and waits for user input.

### AI2 – Expense Type Classification

- Task: determine whether the document is an **employee personal expense** or a **corporate card expense**.
- Store result in `unified_files.expense_type`:
  - **personal** → employee paid the expense themselves.
  - **corporate** → expense belongs to a corporate card (e.g., First Card, MasterCard).

### AI3 – Data Extraction to Database

- Extract all structured data from the receipt/invoice and insert into three main tables:

1. **unified_files**
   - Master record for the receipt.
   - Stores high-level data such as vendor, total amount excluding VAT, etc.
2. **receipt_items**
   - Line items of each receipt.
   - Each record links back to its parent record in `unified_files.id`.
3. **companies**
   - Company details.
   - Must be synchronized with the official company registry via the Bolagsverket API.

### AI4 – Accounting (Bookkeeping) Entries

- Classify and assign accounts for all entries according to **Swedish accounting practices**.
- Use the **BAS-2025 chart of accounts**, stored in the database table `chart_of_accounts`, as the reference.
- An entry should be made in ai_accounting_proposals for each accountnumber that is selected according to praxis

### AI5 – Credit Card Invoice Matching

- Import invoices into:
  - `creditcard_invoices_main`
  - `creditcard_invoice_items`
- Match each invoice line item with receipts having the same `purchase_date` and amount
- If there is a check set true in unified_files_credit_card_match
