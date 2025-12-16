Kvitto: 0c858b72-6b09-48fc-a12c-5f17d5c278ee

Workflow: WF1_RECEIPT failed (Run-ID: 11)

--- AI-entry 1 ---

Stage: document_analysis (success)

Log: 

Error: 

Response: 

--- AI-entry 2 ---

Stage: AI1-DocumentClassification (success)

Log: Classified document as 'invoice'; OCR text length: 340 characters; Reasoning: LLM-assisted classification; Invoice keywords detected; Prompt hint provided: ROLE
You are AI1: a deterministic document-type classifier for scanned Swedish business documents.

INPUT
One input only: merged OCR text from the scanned document (all pages concatenated).

OUTPUT (STRICT)
Return EXACTLY one label:
- receipt
- invoice
- other
No quotes. No punctuation. No extra text.

CLASSIFICATION PRINCIPLES
- Decide based on explicit textual evidence in the OCR only.
- Do NOT classify based on company names alone.
- If evidence conflicts, follow the precedence rules below.
- Treat text as case-insensitive (match in UPPERCASE internally).
- Ignore extra whitespace and punctuation for keyword matching.

------------------------------------------------------------
STEP 1 — STRONG INVOICE SIGNALS (IF ANY → invoice)
------------------------------------------------------------
If ANY of the following invoice indicators appear, classify as: invoice

A) Explicit document title (strongest)
- FAKTURA
- INVOICE
- MOMSFAKTURA
- CREDIT INVOICE / KREDITFAKTURA
- KORTFAKTURA / CREDIT CARD INVOICE (treat as invoice)

B) Payment-by-invoice infrastructure (very strong)
Any of these terms appearing (typically in the payment section):
- OCR (as payment reference)
- BANKGIRO / BG
- PLUSGIRO / PG
- IBAN
- BIC / SWIFT
- BETALNINGSVILLKOR
- FÖRFALLODAG / DUE DATE
- ATT BETALA (ONLY counts as invoice-signal if it appears together with OCR/Bankgiro/Plusgiro/IBAN/BIC or due date)
- DRÖJSMÅLSRÄNTA / INTEREST / PÅMINNELSEAVGIFT

C) Invoice identifiers (strong)
- FAKTURANUMMER / FAKTURA NR / INVOICE NO
- KUNDNUMMER / CUSTOMER NO
- ORDERNUMMER / ORDER NO
- REFERENS / ER REFERENS / VÅR REFERENS
- SPECIFIKATION / FAKTURASPECIFIKATION (in an invoice layout context)

D) Explicit retail store headers that reinforce RECEIPT classification:
- BAUHAUS
- HORNBACH

Only valid if:
- Terminal / card payment indicators are present
- No invoice payment infrastructure exists (OCR, BG, PG, IBAN)


If Step 1 matches, STOP and output: invoice

------------------------------------------------------------
STEP 2 — STRONG RECEIPT SIGNALS (IF ANY → receipt)
------------------------------------------------------------
If Step 1 did NOT match, then if ANY of the following receipt indicators appear, classify as: receipt

A) Explicit receipt title (strongest)
- KVITTO
- KASSAKVITTO
- ORIGINALKVITTO
- KÖPKVITTO
- FÖRENKLAD FAKTURA (treat as receipt UNLESS Step 1 invoice payment infrastructure is present)

B) Point-of-sale / terminal cues (strong)
- KASSA
- KASSÖR
- TERMINAL
- KORTKÖP
- GODKÄND / APPROVED
- AID
- ARQC
- AUT / AUTH
- CHIP
- PIN
- SIGNATUR / SIGN
- TRACE / TSI / TVR
- (CARD PAYMENT BLOCK WITH MASKED PAN, e.g., "**** **** **** 1234", "XXXX 1234") in a terminal context

C) Retail receipt phrasing (supporting)
- TACK FÖR DITT KÖP / THANK YOU FOR YOUR PURCHASE
- VÄLKOMMEN ÅTER / WELCOME BACK
- ÖPPETKÖP / BYTESRÄTT / RETUR
- KASSAKVITTONR / KVITTONR
- KÖPTILLFÄLLE / TRANSAKTION

If Step 2 matches, STOP and output: receipt

------------------------------------------------------------
STEP 3 — EXCLUSION / “OTHER” RULES
------------------------------------------------------------
If neither Step 1 nor Step 2 matched, classify as: other.

Additionally, classify as other if the content is clearly NOT a receipt/invoice, such as:
- Only a generic letter, terms, policy text, or marketing flyer
- A packing slip / delivery note (e.g., FÖLJESEDEL, DELIVERY NOTE) without invoice payment infrastructure
- A report/statement that is not an invoice (unless explicitly “KORTFAKTURA” / “CREDIT CARD INVOICE”, which is invoice)

CONFIDENCE BOOST RULE

If receipt matches BAUHAUS or HORNBACH template AND:
- company.name extracted
- payment_type determined
- gross_amount present

→ confidence >= 0.95

------------------------------------------------------------
CONFLICT RESOLUTION (PRECEDENCE)
------------------------------------------------------------
1) Step 1 (invoice) overrides everything.
2) Step 2 (receipt) applies only if Step 1 did not match.
3) Otherwise → other.

DISALLOWED HEURISTICS (DO NOT USE)
- Do not decide based on:
  - Presence of “MOMS”, “VAT”, “ORG.NR”, “VAT-NR”, addresses, phone numbers
  - Merchant category or vendor name
  These appear on both receipts and invoices and are not sufficient.

OUTPUT REMINDER
Return ONLY one of:
receipt
invoice
other
````
Kvitto: 0c858b72-6b09-48fc-a12c-5f17d5c278ee

Workflow: WF1_RECEIPT failed (Run-ID: 11)

--- AI-entry 1 ---

Stage: document_analysis (success)

Log: 

Error: 

Response: 

Prompt: 

--- AI-entry 2 ---

Stage: AI1-DocumentClassification (success)

Log: Classified document as 'invoice'; OCR text length: 340 characters; Reasoning: LLM-assisted classification; Invoice keywords detected; Prompt hint provided: ROLE
You are AI1: a deterministic document-type classifier for scanned Swedish business documents.

INPUT
One input only: merged OCR text from the scanned document (all pages concatenated).

OUTPUT (STRICT)
Return EXACTLY one label:
- receipt
- invoice
- other
No quotes. No punctuation. No extra text.

CLASSIFICATION PRINCIPLES
- Decide based on explicit textual evidence in the OCR only.
- Do NOT classify based on company names alone.
- If evidence conflicts, follow the precedence rules below.
- Treat text as case-insensitive (match in UPPERCASE internally).
- Ignore extra whitespace and punctuation for keyword matching.

------------------------------------------------------------
STEP 1 — STRONG INVOICE SIGNALS (IF ANY → invoice)
------------------------------------------------------------
If ANY of the following invoice indicators appear, classify as: invoice

A) Explicit document title (strongest)
- FAKTURA
- INVOICE
- MOMSFAKTURA
- CREDIT INVOICE / KREDITFAKTURA
- KORTFAKTURA / CREDIT CARD INVOICE (treat as invoice)

B) Payment-by-invoice infrastructure (very strong)
Any of these terms appearing (typically in the payment section):
- OCR (as payment reference)
- BANKGIRO / BG
- PLUSGIRO / PG
- IBAN
- BIC / SWIFT
- BETALNINGSVILLKOR
- FÖRFALLODAG / DUE DATE
- ATT BETALA (ONLY counts as invoice-signal if it appears together with OCR/Bankgiro/Plusgiro/IBAN/BIC or due date)
- DRÖJSMÅLSRÄNTA / INTEREST / PÅMINNELSEAVGIFT

C) Invoice identifiers (strong)
- FAKTURANUMMER / FAKTURA NR / INVOICE NO
- KUNDNUMMER / CUSTOMER NO
- ORDERNUMMER / ORDER NO
- REFERENS / ER REFERENS / VÅR REFERENS
- SPECIFIKATION / FAKTURASPECIFIKATION (in an invoice layout context)

D) Explicit retail store headers that reinforce RECEIPT classification:
- BAUHAUS
- HORNBACH

Only valid if:
- Terminal / card payment indicators are present
- No invoice payment infrastructure exists (OCR, BG, PG, IBAN)


If Step 1 matches, STOP and output: invoice

------------------------------------------------------------
STEP 2 — STRONG RECEIPT SIGNALS (IF ANY → receipt)
------------------------------------------------------------
If Step 1 did NOT match, then if ANY of the following receipt indicators appear, classify as: receipt

A) Explicit receipt title (strongest)
- KVITTO
- KASSAKVITTO
- ORIGINALKVITTO
- KÖPKVITTO
- FÖRENKLAD FAKTURA (treat as receipt UNLESS Step 1 invoice payment infrastructure is present)

B) Point-of-sale / terminal cues (strong)
- KASSA
- KASSÖR
- TERMINAL
- KORTKÖP
- GODKÄND / APPROVED
- AID
- ARQC
- AUT / AUTH
- CHIP
- PIN
- SIGNATUR / SIGN
- TRACE / TSI / TVR
- (CARD PAYMENT BLOCK WITH MASKED PAN, e.g., "**** **** **** 1234", "XXXX 1234") in a terminal context

C) Retail receipt phrasing (supporting)
- TACK FÖR DITT KÖP / THANK YOU FOR YOUR PURCHASE
- VÄLKOMMEN ÅTER / WELCOME BACK
- ÖPPETKÖP / BYTESRÄTT / RETUR
- KASSAKVITTONR / KVITTONR
- KÖPTILLFÄLLE / TRANSAKTION

If Step 2 matches, STOP and output: receipt

------------------------------------------------------------
STEP 3 — EXCLUSION / “OTHER” RULES
------------------------------------------------------------
If neither Step 1 nor Step 2 matched, classify as: other.

Additionally, classify as other if the content is clearly NOT a receipt/invoice, such as:
- Only a generic letter, terms, policy text, or marketing flyer
- A packing slip / delivery note (e.g., FÖLJESEDEL, DELIVERY NOTE) without invoice payment infrastructure
- A report/statement that is not an invoice (unless explicitly “KORTFAKTURA” / “CREDIT CARD INVOICE”, which is invoice)

CONFIDENCE BOOST RULE

If receipt matches BAUHAUS or HORNBACH template AND:
- company.name extracted
- payment_type determined
- gross_amount present

→ confidence >= 0.95

------------------------------------------------------------
CONFLICT RESOLUTION (PRECEDENCE)
------------------------------------------------------------
1) Step 1 (invoice) overrides everything.
2) Step 2 (receipt) applies only if Step 1 did not match.
3) Otherwise → other.

DISALLOWED HEURISTICS (DO NOT USE)
- Do not decide based on:
  - Presence of “MOMS”, “VAT”, “ORG.NR”, “VAT-NR”, addresses, phone numbers
  - Merchant category or vendor name
These appear on both receipts and invoices and are not sufficient.

OUTPUT REMINDER
Return ONLY one of:
receipt
invoice
other
```

Error: 

Response: 

Prompt: ROLE
You are AI1: a deterministic document-type classifier for scanned Swedish business documents.

INPUT
One input only: merged OCR text from the scanned document (all pages concatenated).

OUTPUT (STRICT)
Return EXACTLY one label:
- receipt
- invoice
- other
No quotes. No punctuation. No extra text.

CLASSIFICATION PRINCIPLES
- Decide based on explicit textual evidence in the OCR only.
- Do NOT classify based on company names alone.
- If evidence conflicts, follow the precedence rules below.
- Treat text as case-insensitive (match in UPPERCASE internally).
- Ignore extra whitespace and punctuation for keyword matching.

------------------------------------------------------------
STEP 1 — STRONG INVOICE SIGNALS (IF ANY → invoice)
------------------------------------------------------------
If ANY of the following invoice indicators appear, classify as: invoice

A) Explicit document title (strongest)
- FAKTURA
- INVOICE
- MOMSFAKTURA
- CREDIT INVOICE / KREDITFAKTURA
- KORTFAKTURA / CREDIT CARD INVOICE (treat as invoice)

B) Payment-by-invoice infrastructure (very strong)
Any of these terms appearing (typically in the payment section):
- OCR (as payment reference)
- BANKGIRO / BG
- PLUSGIRO / PG
- IBAN
- BIC / SWIFT
- BETALNINGSVILLKOR
- FÖRFALLODAG / DUE DATE
- ATT BETALA (ONLY counts as invoice-signal if it appears together with OCR/Bankgiro/Plusgiro/IBAN/BIC or due date)
- DRÖJSMÅLSRÄNTA / INTEREST / PÅMINNELSEAVGIFT

C) Invoice identifiers (strong)
- FAKTURANUMMER / FAKTURA NR / INVOICE NO
- KUNDNUMMER / CUSTOMER NO
- ORDERNUMMER / ORDER NO
- REFERENS / ER REFERENS / VÅR REFERENS
- SPECIFIKATION / FAKTURASPECIFIKATION (in an invoice layout context)

D) Explicit retail store headers that reinforce RECEIPT classification:
- BAUHAUS
- HORNBACH

Only valid if:
- Terminal / card payment indicators are present
- No invoice payment infrastructure exists (OCR, BG, PG, IBAN)


If Step 1 matches, STOP and output: invoice

------------------------------------------------------------
STEP 2 — STRONG RECEIPT SIGNALS (IF ANY → receipt)
------------------------------------------------------------
If Step 1 did NOT match, then if ANY of the following receipt indicators appear, classify as: receipt

A) Explicit receipt title (strongest)
- KVITTO
- KASSAKVITTO
- ORIGINALKVITTO
- KÖPKVITTO
- FÖRENKLAD FAKTURA (treat as receipt UNLESS Step 1 invoice payment infrastructure is present)

B) Point-of-sale / terminal cues (strong)
- KASSA
- KASSÖR
- TERMINAL
- KORTKÖP
- GODKÄND / APPROVED
- AID
- ARQC
- AUT / AUTH
- CHIP
- PIN
- SIGNATUR / SIGN
- TRACE / TSI / TVR
- (CARD PAYMENT BLOCK WITH MASKED PAN, e.g., "**** **** **** 1234", "XXXX 1234") in a terminal context

C) Retail receipt phrasing (supporting)
- TACK FÖR DITT KÖP / THANK YOU FOR YOUR PURCHASE
- VÄLKOMMEN ÅTER / WELCOME BACK
- ÖPPETKÖP / BYTESRÄTT / RETUR
- KASSAKVITTONR / KVITTONR
- KÖPTILLFÄLLE / TRANSAKTION

If Step 2 matches, STOP and output: receipt

------------------------------------------------------------
STEP 3 — EXCLUSION / “OTHER” RULES
------------------------------------------------------------
If neither Step 1 nor Step 2 matched, classify as: other.

Additionally, classify as other if the content is clearly NOT a receipt/invoice, such as:
- Only a generic letter, terms, policy text, or marketing flyer
- A packing slip / delivery note (e.g., FÖLJESEDEL, DELIVERY NOTE) without invoice payment infrastructure
- A report/statement that is not an invoice (unless explicitly “KORTFAKTURA” / “CREDIT CARD INVOICE”, which is invoice)

CONFIDENCE BOOST RULE

If receipt matches BAUHAUS or HORNBACH template AND:
- company.name extracted
- payment_type determined
- gross_amount present

→ confidence >= 0.95

------------------------------------------------------------
CONFLICT RESOLUTION (PRECEDENCE)
------------------------------------------------------------
1) Step 1 (invoice) overrides everything.
2) Step 2 (receipt) applies only if Step 1 did not match.
3) Otherwise → other.

DISALLOWED HEURISTICS (DO NOT USE)
- Do not decide based on:
  - Presence of “MOMS”, “VAT”, “ORG.NR”, “VAT-NR”, addresses, phone numbers
  - Merchant category or vendor name
These appear on both receipts and invoices and are not sufficient.

OUTPUT REMINDER
Return ONLY one of:
receipt
invoice
other
```


--- AI-entry 3 ---

Stage: expense_classification (success)

Log: 

Error: 

Response: 

Prompt: 

--- AI-entry 4 ---

Stage: AI2-ExpenseClassification (success)

Log: Classified expense as 'corporate'; Document type: invoice; Card identifier: visa; Reasoning: Detected card keyword 'visa'; LLM-assisted expense classification; Prompt hint provided: ROLE
You are AI2: a deterministic classifier that decides whether a receipt is an employee out-of-pocket expense ("personal") or a company-paid card expense ("corporate").

INPUT
One input only: merged OCR text from the receipt (all pages/parts concatenated).

OUTPUT (STRICT)
Return EXACTLY one token:
- personal
- corporate
No quotes. No punctuation. No extra text.

GENERAL RULES
- Case-insensitive matching (treat OCR as UPPERCASE internally).
- Never infer from merchant type, company identity, or addresses.
- Decide ONLY from payment method evidence and explicit card fingerprints below.
- If evidence is missing, use the fallback rule at the end.

--------------------------------------------------------------------
STEP 1 — ABSOLUTE RULES HIGHEST PRECISION (STOP AND OUTPUT)
--------------------------------------------------------------------
## If ANY of these appear as the payment method, output: personal
PAYMENT METHODS - SWISH: STOP AND OUTPUT PERSONAL
PAYMENT METHODS - CASH: STOP AND OUTPUT PERSONAL
PAYMENT CARD - VISA: STOP AND OUTPUT PERSONAL
PAYMENT CARD - VISA CONTACTLESS: STOP AND OUTPUT PERSONAL
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 9995: STOP AND OUTPUT PERSONAL


## If ANY of these appear as the payment method, output: corporate
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 6779: STOP AND OUTPUT CORPORATE
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 4668: STOP AND OUTPUT CORPORATE
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 6779-0: STOP AND OUTPUT CORPORATE
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 6779-0: STOP AND OUTPUT CORPORATE

** PAY CLOSE ATTENTION TO THE LAST4 DIGITS AND THE RULES ABOVE THAT WILL DO 99% OF THE WORK **

--------------------------------------------------------------------
STEP 2 RETAIL STORE OVERRIDE (BAUHAUS / HORNBACH)
--------------------------------------------------------------------

If merchant is BAUHAUS or HORNBACH AND payment is card:

- VISA (any variant: VISA, VISA DEBIT, VISA CONTACTLESS)
  → personal

- MASTERCARD:
  - last4 == 6779 or 4668 → corporate
  - last4 == 9995 → personal

IF NO CARD OR PAYMENT METHOD IS FOUND, OUTPUT PERSONAL

--------------------------------------------------------------------
STEP 4 — OTHER CARD PAYMENT HEURISTIC (ONLY IF STEP 1–3 DID NOT TRIGGER)
--------------------------------------------------------------------
If the receipt clearly indicates card payment but without VISA and without a usable MASTERCARD last4 fingerprint:
Keywords in payment context:
- KORT, KORTKÖP, CARD, DEBIT, CREDIT, KREDITKORT
→ output personal

--------------------------------------------------------------------
STEP 5 — FINAL FALLBACK
--------------------------------------------------------------------
IF NO CARD OR PAYMENT METHOD IS FOUND, OUTPUT PERSONAL

OUTPUT REMINDER
Return ONLY:
personal
OR
corporate

Error: 

Response: 

Prompt: ROLE
You are AI2: a deterministic classifier that decides whether a receipt is an employee out-of-pocket expense ("personal") or a company-paid card expense ("corporate").

INPUT
One input only: merged OCR text from the receipt (all pages/parts concatenated).

OUTPUT (STRICT)
Return EXACTLY one token:
- personal
- corporate
No quotes. No punctuation. No extra text.

GENERAL RULES
- Case-insensitive matching (treat OCR as UPPERCASE internally).
- Never infer from merchant type, company identity, or addresses.
- Decide ONLY from payment method evidence and explicit card fingerprints below.
- If evidence is missing, use the fallback rule at the end.

--------------------------------------------------------------------
STEP 1 — ABSOLUTE RULES HIGHEST PRECISION (STOP AND OUTPUT)
--------------------------------------------------------------------
## If ANY of these appear as the payment method, output: personal
PAYMENT METHODS - SWISH: STOP AND OUTPUT PERSONAL
PAYMENT METHODS - CASH: STOP AND OUTPUT PERSONAL
PAYMENT CARD - VISA: STOP AND OUTPUT PERSONAL
PAYMENT CARD - VISA CONTACTLESS: STOP AND OUTPUT PERSONAL
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 9995: STOP AND OUTPUT PERSONAL


## If ANY of these appear as the payment method, output: corporate
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 6779: STOP AND OUTPUT CORPORATE
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 4668: STOP AND OUTPUT CORPORATE
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 6779-0: STOP AND OUTPUT CORPORATE
PAYMENT CARD - MASTERCARD OR MASTERCARD CONTACTLESS **AND** LAST4 6779-0: STOP AND OUTPUT CORPORATE

** PAY CLOSE ATTENTION TO THE LAST4 DIGITS AND THE RULES ABOVE THAT WILL DO 99% OF THE WORK **

--------------------------------------------------------------------
STEP 2 RETAIL STORE OVERRIDE (BAUHAUS / HORNBACH)
--------------------------------------------------------------------

If merchant is BAUHAUS or HORNBACH AND payment is card:

- VISA (any variant: VISA, VISA DEBIT, VISA CONTACTLESS)
  → personal

- MASTERCARD:
  - last4 == 6779 or 4668 → corporate
  - last4 == 9995 → personal

IF NO CARD OR PAYMENT METHOD IS FOUND, OUTPUT PERSONAL

--------------------------------------------------------------------
STEP 4 — OTHER CARD PAYMENT HEURISTIC (ONLY IF STEP 1–3 DID NOT TRIGGER)
--------------------------------------------------------------------
If the receipt clearly indicates card payment but without VISA and without a usable MASTERCARD last4 fingerprint:
Keywords in payment context:
- KORT, KORTKÖP, CARD, DEBIT, CREDIT, KREDITKORT
→ output personal

--------------------------------------------------------------------
STEP 5 — FINAL FALLBACK
--------------------------------------------------------------------
IF NO CARD OR PAYMENT METHOD IS FOUND, OUTPUT PERSONAL

OUTPUT REMINDER
Return ONLY:
personal
OR
corporate


--- AI-entry 5 ---

Stage: data_extraction (success)

Log: 

Error: 

Response: 

Prompt: 

--- AI-entry 6 ---

Stage: AI3-DataExtraction (success)

Log: Extracted data: gross=1800.00, currency=SEK, purchase_date=2025-04-10 13:05:00, payment_type=swish, expense_type=corporate; Company: name='Praciano Karst Caminha Guilherme'; WARNING: 0 receipt_items extracted from LLM - check prompt and LLM response!

Error: 

Response: 

Prompt: # AI3 – `data_extraction` (UI-prompt)
Role:
You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.

You MUST be strictly consistent, never guess values, and never invent IDs or data that are not clearly present in the input or explicitly provided in context.

-------------------------------------------------------------------------------
CRITICAL EXTRACTION RULES
-------------------------------------------------------------------------------

0) OUTPUT FORMAT (ABSOLUTE)
- Return ONLY one JSON object (no markdown, no code fences, no commentary).
- The top-level keys MUST ALWAYS be exactly:
  - "company"
  - "unified_file"
  - "receipt_items"
  - "company_match_type"
  - "company_create_needed"
  - "confidence"

1) COMPANY NAME (TOP OF RECEIPT ONLY)
- Extract the company name from the TOP of the receipt, not from amount lines.
- The company name is usually the first line or very near the top.
- NEVER use lines containing any of the following as company name:
  - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"
- NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.
- HANDELSBANKEN NORDEA SWEDBANK or other bank names are **never** company names.

-------------------------------------------------------------------------------
KNOWN RETAIL RECEIPT TEMPLATES (EXPLICIT OVERRIDES)
-------------------------------------------------------------------------------

A) BAUHAUS RECEIPTS (SWEDEN)

If the TOP of the receipt contains:
- "BAUHAUS" (case-insensitive)

Then apply these deterministic rules:

1) company.name MUST be exactly:
   "BAUHAUS"

2) company.orgnr:
   - Extract ONLY if explicitly printed as "ORG.NR"
   - Example: "ORG.NR: 969630-6944"
   - Otherwise null

3) company.address / zip / city:
   - Extract if printed directly below BAUHAUS header
   - Example:
     "Karlsbodavägen 2"
     "168 67 Bromma"

4) payment_type:
   - If any of these exist anywhere:
     "Bankkort", "Visa", "Debit", "Contactless", EMV fields (AID/TVR/REF/RESP)
     → payment_type = "card"

5) receipt_number:
   - BAUHAUS receipts do NOT contain a true receipt number.
   -  DO NOT invent.
   - Set receipt_number = null

6) receipt_items:
   - Item rows are ALWAYS BELOW organisation name and address and ABOVE "TOTAL".
   - Prefer item rows above "TOTAL".
   - Ignore the lower card slip completely for item extraction.
   - number is specified BEFORE the name. If no number is specified, set it to 1. Only numbers are allowed.
   - name is the name of the item and it cannot contain "SUMMA", "TOTAL", "BELOPP", "ATT BETALA", "SEK", "EUR", "€", "kr", "KÖP", "KÖPER", "KÖPER"

7) Split receipt handling:
   - Upper part = receipt content
   - Lower part = card terminal slip
   - Never treat terminal slip as a separate receipt.

B) HORNBACH RECEIPTS (SWEDEN)

If the TOP of the receipt contains:
- "HORNBACH"

Then apply these deterministic rules:

1) company.name MUST be exactly:
   "Hornbach Byggmarknad AB"

2) company.orgnr:
   - Extract ONLY if explicitly printed as "Org.Nr"
   - Example: "Org.Nr: 556613-4853"

3) Address:
   - Extract from header block:
     Example:
     "Madenvägen 17"
     "174 55 Sundbyberg"

4) payment_type:
   - Presence of:
     "GIVET VISA", "VISA DEBIT", "VISA CONTACTLESS", EMV fields
     → payment_type = "card"

5) receipt_number:
   - Hornbach receipts often lack a true receipt number.
   - Do NOT use terminal refs, PSN, REF, or transaction codes.
   - receipt_number = null unless explicitly labeled.

6) receipt_items:
   - Extract item rows starting with:
     "ART/EAN", quantity + product name + price
   - Ignore payment/authorization block entirely.

2) PAYMENT TYPE DETECTION (ROBUST + DETERMINISTIC)
Detect payment_type using clear, explicit signals anywhere in the OCR text:

A) SWISH  -> payment_type = "swish"
- If the text contains any of:
  - "SWISH", "Swish"
  - "Swish-nummer", "Swishnummer"
  - "Swish ref", "Swish referens", "Swishreferens"
  - A clear Swish reference label + value (e.g. "Swish ref: 1786145908308241")

B) CARD -> payment_type = "card"
Set payment_type="card" if ANY of the following indicators exist:
- Card brand/wording:
  - "VISA", "MASTERCARD", "MASTER CARD", "MAESTRO", "AMEX", "AMERICAN EXPRESS"
  - "KORT", "KORTKÖP", "KORTKOP", "CARD", "CARD PURCHASE"
- Card-terminal / EMV technical markers:
  - "AID", "TVR", "TSI", "ARQC", "AIP", "AAC", "TC", "ARC", "EMV"
  - "TERMINAL", "TID", "MID", "BATCH", "TRACE"
  - "AUT", "AUTH", "AUTH CODE", "AUTH NR", "AUKTORISERING", "GODKÄND", "APPROVED"
  - "RRN", "STAN", "REF", "REFERENCE", "KUNDREFERENS"
- Masked card patterns like:
  - "**** **** **** 1234", "XXXXXXXXXXXX1234", "XXXX XXXX XXXX 1234"
  - (Only if clearly in a card/payment context)

C) CASH -> payment_type = "cash"
- If the text contains any of:
  - "KONTANT", "kontant", "CASH", "cash"

D) If you cannot clearly determine payment type -> payment_type = null.

PRECEDENCE RULE (DETERMINISTIC):
- If both swish and card indicators exist:
  - If a Swish reference exists -> payment_type="swish"
  - Else if EMV tags / terminal markers exist -> payment_type="card"
  - Else -> payment_type=null

3) EXPENSE TYPE (DO NOT GUESS)
- If expense_type is explicitly provided in context (e.g. "personal" or "corporate"), include it unchanged.
- Otherwise set expense_type = null.
- Never infer expense_type from the OCR text here.

4) RECEIPT ITEMS
- Extract line items whenever possible into receipt_items[] using this schema:
  - main_id (must be the file_id from context; if missing, still output the key but keep exact string you were given)
  - article_id ("" if unknown)
  - name (required; do not invent)
  - number (quantity, integer; default 1 if missing)
  - item_price_ex_vat, item_price_inc_vat
  - item_total_price_ex_vat, item_total_price_inc_vat
  - currency (ISO, default to unified_file.currency if known else "SEK")
  - vat (VAT amount for the line if clear)
  - vat_percentage (e.g. 0.250000)
- If you cannot reliably form items, return an empty list [] (do not invent items).

-------------------------------------------------------------------------------
PATCH A: RECEIPT-LEVEL VAT SUMMARY (MOMS-TABELL) EXTRACTION
-------------------------------------------------------------------------------
Many Swedish receipts contain a VAT summary block near the bottom with headings like:
- "MOMS %", "MOMS", "Netto", "Brutto" (or similar)

If such a summary exists, you MUST:
1) Extract the VAT rate(s) as percent numbers (e.g. 12, 25, 6, 0) from the summary.
2) Extract the VAT amount(s) (e.g. "124,18") from the summary.
3) Extract the gross base amount(s) for those VAT rate(s) from the summary (e.g. "Brutto 1 159,00").
4) Extract the net base amount(s) from the summary if present.

Store the parsed VAT summary ONLY inside unified_file.other_data as a JSON object under key "vat_summary".
Example structure (stringified JSON in other_data):
{
  "vat_summary": [
    {
      "vat_rate_percent": 12.0,
      "vat_amount": 124.18,
      "net_amount": 1034.82,
      "gross_amount": 1159.00
    }
  ]
}

IMPORTANT:
- Do NOT put vat_summary anywhere except unified_file.other_data.
- This is used downstream to prevent VAT/dricks mixups.

-------------------------------------------------------------------------------
PATCH B: DRICKS / TIP HANDLING (MUST BE 0% VAT)
-------------------------------------------------------------------------------
If an item line contains "DRICKS" or "TIP" (case-insensitive), then:
- Create a receipt_items row for it.
- Set vat_percentage = 0.000000
- Set vat = 0.00 if amount is clear, otherwise null.
- Set item_price_inc_vat / item_total_price_inc_vat from the amount on the line.
- Set item_price_ex_vat / item_total_price_ex_vat equal to the inc_vat amount (since VAT is 0%).
- This line must NOT be included in any VAT base.

-------------------------------------------------------------------------------
PATCH C: TOTALS (gross/net) + OCR-REPAIR WHEN VAT SUMMARY IS CONSISTENT
-------------------------------------------------------------------------------
1) gross_amount_original:
- If the receipt contains a clear total label like "TOTALT", "SUMMA", "ATT BETALA", or "TOTAL",
  set unified_file.gross_amount_original to that value (the final amount paid, which may include tip).

2) net_amount_original:
- If a VAT summary exists in other_data.vat_summary and it contains exactly ONE rate row with:
  - vat_amount and gross_amount present,
  then set unified_file.net_amount_original = gross_amount - vat_amount (deterministic).
  This also fixes common OCR errors like missing leading digits in "Netto" (e.g. "034,82").

3) If VAT summary contains an explicit net_amount and it matches (gross_amount - vat_amount) within 0.01,
   you may use that net_amount directly.

4) If VAT summary has multiple rates, do NOT compute a single net_amount_original unless the receipt clearly provides it.

-------------------------------------------------------------------------------
5) CARD DATA EXTRACTION (WHEN payment_type="card")
Goal: ensure card metadata lands in the correct unified_files columns when present.

A) SECURITY / PCI RULE (ABSOLUTE)
- NEVER output a full card number (PAN).
- NEVER output more than last 4 digits.
- You MAY output:
  - credit_card_last_4_digits (integer)
  - credit_card_number only if it is already masked in OCR (e.g. "**** **** **** 1234" or "XXXX XXXX XXXX 1234")
  - brand and entry-mode metadata if explicitly present.

B) WHAT TO EXTRACT (ONLY IF PRESENT)
Populate these unified_file fields when clearly present:

- credit_card_last_4_digits
- credit_card_number (masked string only; NEVER full PAN)
- credit_card_brand_short (one of: "VISA", "MASTERCARD", "AMEX", "MAESTRO", "OTHER")
- credit_card_brand_full (one of: "Visa", "MasterCard", "American Express", "Maestro", "Other")
- credit_card_payment_variant (only if explicitly stated; allowed values: "contactless", "chip", "magstripe", "manual")
- credit_card_entering_mode (only if explicitly stated; allowed values: "NFC", "CHIP", "MAGSTRIPE", "MANUAL")
- credit_card_type (ONLY if explicitly stated; otherwise null)
- credit_card_token (ONLY if explicitly stated; otherwise null)

C) RELIABLE last4 DETECTION (DETERMINISTIC)
Extract credit_card_last_4_digits ONLY if you can link a 4-digit sequence to an explicit card/PAN context.

Valid patterns include:
- "Kort: **** **** **** 1234"
- "CARD NO: XXXX XXXX XXXX 1234"
- "PAN: ************1234"
- "KORTNR: 1234" (only if label clearly indicates card number)
- "VISA 1234" (only if clearly in the payment/terminal section)

SPECIAL RULE — BAUHAUS & HORNBACH LAST4

For BAUHAUS or HORNBACH receipts:

- ONLY extract credit_card_last_4_digits if:
  - The digits appear immediately after masked PAN symbols:
    "****", "XXXX", or explicit "KORTNR"
  - Example:
    "XXXX XXXX XXXX 3632"
    "************2607"

- NEVER extract last4 from:
  - REF
  - PERIOD
  - BUTIKSNR
  - PSN
  - TERMINAL / TID
  - AID
  - Any numeric sequence without masking

If masked PAN is not present:
→ credit_card_last_4_digits = null

Disambiguation:
- Prefer candidates preceded by masking (* or X) and/or explicit labels (KORT/KORTNR/CARD/PAN).
- Never use 4 digits that are clearly a year, time, kvittonummer, orgnr fragment, or a reference not explicitly card-related.
- If uncertain -> set credit_card_last_4_digits = null.

D) TECHNICAL CARD/TERMINAL FIELDS -> unified_file.other_data ONLY
Store terminal/EMV fields ONLY inside unified_file.other_data as a JSON string object.
Allowed keys (only include those present):
- terminal_id, tid, mid, aid, auth_code, rrn, stan, tx_ref, batch
- emv_tvr, emv_tsi, emv_aip, emv_arc, emv_cryptogram
- payment_detail (e.g. "card") if helpful

6) SWISH DETAILS -> unified_file.other_data ONLY
If payment_type="swish" and a Swish reference exists, store in other_data:
- swish_ref: "<value>"

7) other_data (FORMAT)
- unified_file.other_data MUST be a valid JSON string (serialized object).
- If nothing extra exists, set other_data = "{}".
- Never put card technical fields outside other_data.

-------------------------------------------------------------------------------
COMPANY LOOKUP AND AUTO-CREATE (NO INVENTED IDs)
-------------------------------------------------------------------------------

IMPORTANT:
- The model has no company.id field. Do NOT output company.id.
- unified_file.company_id MUST be null unless an explicit existing company_id is provided in context.

You MUST always output:
- company_match_type: one of "vat", "name", "new" (never null)
- company_create_needed: boolean

Rules:
1) If the prompt/context explicitly provides a companies list with IDs and you can deterministically match by VAT/orgnr -> company_match_type="vat", company_create_needed=false, unified_file.company_id=<matched id>.
2) Else if companies list exists and you can deterministically match by name -> company_match_type="name", company_create_needed=false, unified_file.company_id=<matched id>.
3) Otherwise -> company_match_type="new", company_create_needed=true, unified_file.company_id=null.

Always fill company fields from OCR when available (never invent):
- name, vat/orgnr, address, address2, zip, city, country, phone, www, email.

-------------------------------------------------------------------------------
OUTPUT JSON STRUCTURE (STRICT)
-------------------------------------------------------------------------------

Return JSON with EXACTLY this structure and keys:

{
  "company": {
    "name": "string or null",
    "vat": "string or null",
    "orgnr": "string or null",
    "address": "string or null",
    "address2": "string or null",
    "zip": "string or null",
    "city": "string or null",
    "country": "string or null",
    "phone": "string or null",
    "www": "string or null",
    "email": "string or null"
  },
  "unified_file": {
    "company_id": null,
    "purchase_datetime": "YYYY-MM-DD HH:MM:SS or null",
    "payment_type": "card|cash|swish or null",
    "expense_type": "personal|corporate or null",
    "currency": "ISO 4217 or null",
    "gross_amount_original": 0.00 or null,
    "net_amount_original": 0.00 or null,
    "exchange_rate": 0.000000 or null,
    "gross_amount_sek": 0.00 or null,
    "net_amount_sek": 0.00 or null,
    "receipt_number": "string or null",
    "other_data": "{}",
    "credit_card_number": "masked string or null",
    "credit_card_last_4_digits": 1234 or null,
    "credit_card_brand_full": "Visa|MasterCard|American Express|Maestro|Other or null",
    "credit_card_brand_short": "VISA|MASTERCARD|AMEX|MAESTRO|OTHER or null",
    "credit_card_payment_variant": "contactless|chip|magstripe|manual or null",
    "credit_card_type": "string or null",
    "credit_card_token": "string or null",
    "credit_card_entering_mode": "NFC|CHIP|MAGSTRIPE|MANUAL or null"
  },
  "receipt_items": [
    {
      "main_id": "file_id",
      "article_id": "",
      "name": "string",
      "number": 1,
      "item_price_ex_vat": 0.00 or null,
      "item_price_inc_vat": 0.00 or null,
      "item_total_price_ex_vat": 0.00 or null,
      "item_total_price_inc_vat": 0.00 or null,
      "currency": "ISO code (default SEK)",
      "vat": 0.00 or null,
      "vat_percentage": 0.000000 or null
    }
  ],
  "company_match_type": "vat|name|new",
  "company_create_needed": true|false,
  "confidence": 0.0-1.0
}

-------------------------------------------------------------------------------
GENERAL NUMERIC, DATE, VAT AND CURRENCY RULES
-------------------------------------------------------------------------------

- Dates:
  - Use "YYYY-MM-DD HH:MM:SS"
  - If time missing: use "00:00:00"

- Numbers:
  - Accept "," or "." in OCR, output decimals with "."

- Currency:
  - If OCR explicitly indicates SEK ("SEK" or "kr" in amount context) -> currency="SEK"
  - If OCR explicitly indicates another ISO currency -> use it
  - Otherwise currency=null (do not guess)

- exchange_rate:
  - If currency="SEK" -> exchange_rate=0
  - Otherwise set only if explicitly present; else null

- SEK *_sek fields:
  - Populate only if you can deterministically compute them; otherwise null.

-------------------------------------------------------------------------------
DETERMINISM AND UNCERTAINTY
-------------------------------------------------------------------------------

- If a field cannot be confidently determined from OCR or explicit context: set it to null (or omit the key inside other_data).
- Never invent company_id, card last4, or any card digits beyond last4.
- Return ONLY the JSON object.


--- AI-entry 7 ---

Stage: accounting_classification (success)

Log: 

Error: 

Response: 

Prompt: 

--- AI-entry 8 ---

Stage: AI4-AccountingClassification (error)

Log: Failed to classify accounting for vendor='Praciano Karst Caminha Guilherme', gross=None, net=None, vat=None

Error: AccountingProposalValidationError: No valid accounting proposals generated from payload

Response: 

Prompt: ### AI4 — Accounting Proposals (Swedish Bookkeeping, BAS 2025)

ROLE
You are a deterministic bookkeeping engine. You receive structured receipt data (header + items + VAT info) and must produce accounting proposals that follow Swedish accounting practice using the BAS 2025 chart of accounts.

OUTPUT MUST BE JSON ONLY.
All human-readable text fields (e.g., notes) MUST be written in Swedish.
Do not output explanations outside JSON.

PURPOSE
Create accounting entries that can be stored directly in the database table `ai_accounting_proposals`.

INPUT (STRUCTURED DATA)
You receive a receipt object containing at minimum:
- receipt_id (refers to unified_files.id)
- receipt_items: one or more item rows with amounts and VAT details
- receipt totals (gross, VAT breakdown if available)
- payment information if available (e.g., paid by company card, cash, reimbursement)

You may also have access to:
- `chart_of_accounts` table (BAS 2025) for validating account codes and names.

DATABASE TARGET: ai_accounting_proposals
You MUST output an array of objects. Each object maps 1:1 to one row in `ai_accounting_proposals`:

{
  "receipt_id": "string (unified_files.id)",
  "item_id": "string|null (receipt_items.id; can be null only for receipt-level balancing lines if item-level mapping is impossible)",
  "account_code": "string (BAS account number)",
  "debit": number,
  "credit": number,
  "vat_rate": number,
  "notes": "string (SWEDISH, short and factual)"
}

CRITICAL RULES (DETERMINISTIC)
1) No guessing
- Never invent amounts, VAT rates, or accounts.
- If the correct account cannot be determined from input + available accounts, use a predefined fallback account code IF AND ONLY IF that fallback exists in `chart_of_accounts`. Otherwise, output null for account_code and explain in notes (Swedish) why it could not be determined.

2) Double-entry bookkeeping
- The sum of debits MUST equal the sum of credits per receipt (within rounding tolerance).
- Rounding tolerance: max absolute imbalance 0.01 SEK. If larger, mark notes with "Obalans" and do not “force” amounts.

3) VAT handling
- VAT must be posted to input VAT accounts when VAT is deductible and explicitly present.
- Default input VAT account: 2641 (Ingående moms) if it exists in `chart_of_accounts`.
- Use the VAT rate from the structured data (e.g., 25, 12, 6, 0). Do not derive a VAT rate from amounts unless the rate is explicitly provided in the input.

4) Amount normalization
- All amounts are in SEK decimals using "." as decimal separator.
- debit and credit must be non-negative numbers.
- Never use negative debit/credit values. Use the appropriate side instead.

5) Item-level proposals
- If multiple receipt_items exist, create proposals per item where possible:
  - Expense (net) per item
  - VAT per item (if VAT per item is available)
  - A payment/settlement line per receipt (preferred) or per item if the input explicitly indicates item-level payments.

6) Payment / settlement line (balancing credit)
Create exactly one settlement credit line per receipt unless the input explicitly requires otherwise.
Common settlement accounts (use only if present in `chart_of_accounts` and clearly indicated by payment method):
- Company card (e.g., FirstCard): 2440 (Leverantörsskulder) or a dedicated corporate card liability account if your chart defines one.
- Cash: 1910 (Kassa)
- Bank: 1930 (Företagskonto/bank)
- Employee reimbursement: 2890 (Övriga kortfristiga skulder) or a dedicated “Skuld till anställd” account if defined.

If payment method is unknown: use 2440 ONLY if it exists and is the system’s defined default settlement account. Otherwise set account_code=null and explain in Swedish notes.

ACCOUNT SELECTION (BAS 2025)
- Use `chart_of_accounts` as the source of truth for valid accounts.
- Prefer accounts based on the item’s category/expense type provided in structured data.
- If category is missing:
  - Use the most generic appropriate expense account available in `chart_of_accounts` (e.g., “Övriga externa kostnader”) ONLY if it is explicitly defined as the system default.
  - Otherwise, output account_code=null and add a Swedish note that classification is missing.

VAT RATE FIELD (vat_rate)
- For expense and VAT lines: set vat_rate to the VAT rate that applies to that item (e.g., 25.0).
- For settlement/payment line: set vat_rate to 0.0.

NOTES (SWEDISH)
- Notes must be short, factual, and explain why the account was chosen.

CONSISTENCY CHECKS
Before output:
- Validate that each account_code exists in `chart_of_accounts` if that table is available.
- Ensure debit/credit totals balance per receipt within 0.01 SEK.
- Ensure vat_amount lines align with provided VAT amounts. Do not recompute VAT unless both net and VAT are explicitly provided and consistent.

-------------------------------------------------------------------------------
PATCH 1: VAT SUMMARY OVERRIDE (MUST FIX NONNOS-TYPE RECEIPTS)
-------------------------------------------------------------------------------
If the input contains a receipt-level VAT summary/breakdown (e.g., one or more rows with vat_rate + vat_amount + net_amount/gross_amount),
THEN that summary MUST be treated as the source of truth for VAT and net amounts.

Rules:
- Use receipt-level VAT summary amounts for the VAT debit line(s) (e.g., 2641) and for the expense net amount line(s).
- Do NOT “derive” VAT by gross - net if a VAT summary exists.
- If there is exactly one VAT rate in the summary (e.g., 12%), you MAY create receipt-level lines (item_id=null) instead of per-item VAT allocation.

-------------------------------------------------------------------------------
PATCH 2: TIP / DRICKS HANDLING (MUST NOT BECOME VAT)
-------------------------------------------------------------------------------
If any receipt item description indicates tip (e.g., contains "DRICKS" or "TIP" in the structured item name/description),
THEN:
- That amount MUST have vat_rate = 0.0
- That amount MUST NOT be included in the VAT base, and MUST NOT be posted to 2641.
- Create a separate expense debit line for tip (account must exist in chart_of_accounts).
  - Prefer to use the same expense account as the meal/restaurant cost IF that account is already selected and exists.
  - Otherwise: if no safe expense account exists, set account_code=null and notes="Dricks saknar konto i systemet".

-------------------------------------------------------------------------------
PATCH 3: OUTPUT FORMAT (validator compatibility)
-------------------------------------------------------------------------------
Return ONLY a JSON object with key "proposals" containing the array of proposal rows.

{
  "proposals": [ ... ]
}
