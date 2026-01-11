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
```

Error: 

Response: 

--- AI-entry 3 ---

Stage: expense_classification (success)

Log: 

Error: 

Response: 

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

--- AI-entry 5 ---

Stage: data_extraction (success)

Log: 

Error: 

Response: 

--- AI-entry 6 ---

Stage: AI3-DataExtraction (success)

Log: Extracted data: gross=1800.00, currency=SEK, purchase_date=2025-04-10 13:05:00, payment_type=swish, expense_type=corporate; Company: name='Praciano Karst Caminha Guilherme'; WARNING: 0 receipt_items extracted from LLM - check prompt and LLM response!

Error: 

Response: 

--- AI-entry 7 ---

Stage: accounting_classification (success)

Log: 

Error: 

Response: 

--- AI-entry 8 ---

Stage: AI4-AccountingClassification (error)

Log: Failed to classify accounting for vendor='Praciano Karst Caminha Guilherme', gross=None, net=None, vat=None

Error: AccountingProposalValidationError: No valid accounting proposals generated from payload

Response: 