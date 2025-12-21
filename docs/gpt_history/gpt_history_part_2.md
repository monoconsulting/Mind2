gpt_history_part_2.md
Vi har mycket problem med konverteringen och det feltolkas på en mängd olika sätt. Konteringen fungerar också väldigt dåligt. 

Jag har sammaställt loggar och skämdumpar till dig på ett antal olika kvitton - dessa finns i @temp\result och ligger i en mapp per kvitto och även kvittologgen finns där. De ai-prompter som används ligger i samma folder som md-filer. 

Jag kör docker på windowsdator, och vill nu att du granskar de exempel som finns sparade i denna folder. Gå igenom alla kvitton och gör en sammanställning över alla de olika felen du hittar. 

Använd python, analysera fel, analysera kodbas, leverera en sammantällning över vad som inte fungerar och förslag på hur vi reder ut samtliga registrerade fel. Kodbas bifogad. 
Jag tror du har fångat den problematik som finns. Skapa nu en checklista/införandelista till agenten som exakt instruerar honom i alla de ändringar du föreslagit, så provar vi igen.
Ja lägg till et också
Vilka AI-prompter behövde uppdateras?
Skapa två nya prompter som tydligt eliminerar de problem du identifierat. Skriv dem på engelska - här är AI3:
- # AI3 – data_extraction (UI-prompt)
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


Och här följer AI4:
1. ### AI4 — Accounting Proposals (Swedish Bookkeeping, BAS 2025)

  ROLE
  You are a deterministic bookkeeping engine. You receive structured receipt data (header + items + VAT info) and must produce accounting proposals that follow Swedish accounting practice using the BAS 2025 chart of accounts.

  OUTPUT MUST BE JSON ONLY.
  All human-readable text fields (e.g., notes) MUST be written in Swedish.
  Do not output explanations outside JSON.

  PURPOSE
  Create accounting entries that can be stored directly in the database table ai_accounting_proposals.

  INPUT (STRUCTURED DATA)
  You receive a receipt object containing at minimum:
  - receipt_id (refers to unified_files.id)
  - receipt_items: one or more item rows with amounts and VAT details
  - receipt totals (gross, VAT breakdown if available)
  - payment information if available (e.g., paid by company card, cash, reimbursement)

  You may also have access to:
  - chart_of_accounts table (BAS 2025) for validating account codes and names.

  DATABASE TARGET: ai_accounting_proposals
  You MUST output an array of objects. Each object maps 1:1 to one row in ai_accounting_proposals:

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
  - If the correct account cannot be determined from input + available accounts, use a predefined fallback account code IF AND ONLY IF that fallback exists in chart_of_accounts. Otherwise, output null for account_code and explain in notes (Swedish) why it could not be determined.

  2) Double-entry bookkeeping
  - The sum of debits MUST equal the sum of credits per receipt (within rounding tolerance).
  - Rounding tolerance: max absolute imbalance 0.01 SEK. If larger, mark notes with "Obalans" and do not “force” amounts.

  3) VAT handling
  - VAT must be posted to input VAT accounts when VAT is deductible and explicitly present.
  - Default input VAT account: 2641 (Ingående moms) if it exists in chart_of_accounts.
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
    Common settlement accounts (use only if present in chart_of_accounts and clearly indicated by payment method):
  - Company card (e.g., FirstCard): 2440 (Leverantörsskulder) or a dedicated corporate card liability account if your chart defines one.
  - Cash: 1910 (Kassa)
  - Bank: 1930 (Företagskonto/bank)
  - Employee reimbursement: 2890 (Övriga kortfristiga skulder) or a dedicated “Skuld till anställd” account if defined.

  If payment method is unknown: use 2440 ONLY if it exists and is the system’s defined default settlement account. Otherwise set account_code=null and explain in Swedish notes.

  ACCOUNT SELECTION (BAS 2025)
  - Use chart_of_accounts as the source of truth for valid accounts.
  - Prefer accounts based on the item’s category/expense type provided in structured data.
  - If category is missing:
    - Use the most generic appropriate expense account available in chart_of_accounts (e.g., “Övriga externa kostnader”) ONLY if it is explicitly defined as the system default.
    - Otherwise, output account_code=null and add a Swedish note that classification is missing.

  VAT RATE FIELD (vat_rate)
  - For expense and VAT lines: set vat_rate to the VAT rate that applies to that item (e.g., 25.0).
  - For settlement/payment line: set vat_rate to 0.0.

  NOTES (SWEDISH)
  - Notes must be short, factual, and explain why the account was chosen.

  CONSISTENCY CHECKS
  Before output:
  - Validate that each account_code exists in chart_of_accounts if that table is available.
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
kan du skriva en ny version av denna där man inte behöver ändra prmpt för ai3 och ai4 - detta har jag fixat redan:
Här är en **införande-checklista** som agenten kan följa punkt för punkt. Den är skriven för att ge **exakt** de ändringar jag föreslog (backend-gates + AI3/AI4-regler + company fallback + duplicate-hantering + UI-fixar).

---

## 0) Guardrails innan kodändring

1. Skapa en ny branch per task:

   * fix/accounting-input-gate
   * fix/ai3-sek-fields
   * fix/ai4-validation-and-prompt
   * fix/company-resolution-fallback
   * fix/duplicate-file-nonfatal
   * fix/process-ui-ai-stage-and-clipboard

2. Ändra inget som inte hör till tasken. Om något måste tas bort: **kommentera bort** och skriv en tydlig förklaring i koden.

3. Kör enhetligt format/lint om projektet använder det (ex. ruff/black/eslint) – men ändra inte formatering i filer ni inte rör.

---

## 1) Backend: stoppa AI4 från att köras på trasigt underlag

**Mål:** AI4 ska aldrig få None/saknade totals när det finns deterministisk data att använda.

### 1.1 Implementera “SEK fallback” i accounting input loader

* Fil: backend/src/services/tasks/file_management_tasks.py
* Funktion: _load_accounting_inputs() (du nämnde den; den SELECT:ar idag gross_amount_sek, net_amount_sek)
* Ändring (logik):

  1. Utöka SELECT så att den även hämtar gross_amount_original, net_amount_original, currency samt exchange_rate.
  2. Skapa deterministisk fallback:

     * Om currency == 'SEK':

       * Om gross_amount_sek är NULL och gross_amount_original finns → sätt gross_amount_sek = gross_amount_original
       * Om net_amount_sek är NULL och net_amount_original finns → sätt net_amount_sek = net_amount_original
       * Om exchange_rate är NULL eller 0 → sätt exchange_rate = 1.0
  3. Om totals fortfarande saknas (varken SEK eller original finns) → returnera ett kontrollerat “manual_review”-läge och **kör inte AI4**.

### 1.2 Lägg in en hård gate innan AI4-task körs

* Där AI4 triggas (troligen i samma service eller i en pipeline/orchestrator):

  * Om _load_accounting_inputs() returnerar “invalid/missing totals” → markera status för steget som “needs_review” (eller motsvarande i ert system) med tydligt felmeddelande.
  * Säkerställ att detta inte blir ett “uncaught exception”.

**Acceptance:**

* Ett receipt med gross_amount_original men utan gross_amount_sek ska ändå kunna konteras (för SEK).
* Ett receipt utan totals ska inte krascha AI4 – det ska stoppas och flaggas.

---

## 2) AI3: säkra SEK-fälten och stoppa 0.0-fällan

**Mål:** AI3 får inte producera “SEK men exchange_rate=0.0” eller lämna SEK-belopp tomma när original finns.

### 2.1 Uppdatera AI3 prompt (md-filen i er prompt-folder)

* Lokalisera AI3 prompten i repot (de ligger som .md enligt dig).
* Lägg till/justera regler (ordagrant/tydligt i prompten):

  * För currency == "SEK":

    * exchange_rate MUST be 1.0 (never 0.0)
    * If gross_amount_original is present, gross_amount_sek MUST be the same numeric value
    * If net_amount_original is present, net_amount_sek MUST be the same numeric value
  * Belopp som saknas ska vara null (inte 0.00)

### 2.2 Uppdatera parser/validator för AI3-resultat (om ni har en)

* I backend där AI3 JSON parse:as:

  * Om currency == SEK och exchange_rate kommer som 0 eller null → normalisera till 1.0
  * Om SEK och originalbelopp finns men SEK-belopp saknas → fyll deterministiskt

**Acceptance:**

* Nya AI3-rader i DB ska inte ha exchange_rate=0.0 för SEK.
* gross_amount_sek och net_amount_sek ska fyllas när original finns och currency=SEK.

---

## 3) AI4: stoppa “tomma förslag” och “debit=0 AND credit=0”

**Mål:** AI4 ska producera validerbara konteringsrader, annars ska det bli kontrollerad review – inte exception.

### 3.1 Skärp AI4 promptregler

* Hitta AI4 prompt md.
* Lägg in hårda outputregler:

  * Output MUST contain at least 1 proposal row
  * Each row MUST have:

    * account_number
    * description
    * Exactly one of debit_amount or credit_amount > 0
    * The other MUST be 0
  * No row may have both 0
  * Totals MUST balance (sum debit == sum credit)

### 3.2 Skärp AI4 validator så den ger “review” istället för hårt fel

* Där AccountingProposalValidationError kastas:

  * Gör om flödet så att:

    * status/logg i historik blir “needs_review”
    * feltext sparas tydligt
    * pipeline fortsätter (eller stoppar bara den filen) utan att hela körningen dör

**Acceptance:**

* Rusta/Loopia/Midjourney-typen av fel ska inte bli “Fatal”, utan “Review required” med tydlig orsak.

---

## 4) Company resolution: mildra faktura-fallet så AI3 inte faller på saknat company

**Mål:** “Company resolution failed: both vat/orgnr and name are missing” ska bli sällsynt och hanteras bättre.

### 4.1 AI3 prompt – differentiera invoice vs receipt

* För document_type == "invoice":

  * Tillåt extraction av supplier/issuer från “header block” (inte bara “TOP line”)
  * Lägg in fallback-regel:

    * If the supplier identity is not present in OCR text, set company_match_type="unknown" (eller ert närmaste tillåtna) och flagga review, istället för att lämna både name+orgnr tomma utan signal.

> Om er SoT kräver company_match_type = vat|name|new och aldrig något annat:
> Då ska fallback bli: sätt company_match_type="name" men company.name=null är förbjudet → alltså: vid saknad identitet: avbryt AI3 med kontrollerad “needs_review” innan DB insert.

### 4.2 Backend: om AI3 saknar både name och orgnr → kontrollerad review

* Istället för ValueError som bubblar:

  * fånga detta, sätt status “needs_review”, skriv “missing vendor identity in OCR”.

**Acceptance:**

* Inga “uncaught ValueError” för company resolution; det ska bli review-status.

---

## 5) DuplicateFileError: gör duplicate till icke-fatal

**Mål:** Samma fil (hash) ska ge “already imported”, inte error.

### 5.1 Fånga DuplicateFileError i ingestion

* Där FTP-importen körs (eller generella ingest-flödet):

  * Om hash redan finns:

    * returnera “already imported”
    * logga som warning/info
    * om möjligt: returnera befintligt file_id för spårbarhet

**Acceptance:**

* Duplicate importer ger inte “error” i historiken.

---

## 6) Frontend: fixa AI-stage-namn i modal + clipboard feedback

**Mål:** Loggmodalen ska visa rätt rubriker och knappen ska kännas “tryckbar” och ge respons.

### 6.1 Visa ai_stage_name istället för “AI-entry 1..N”

* Fil: main-system/app-frontend/src/ui/pages/Process.jsx
* Ändring:

  * Där ni renderar/bygger texten för AI-loggar: använd entry.ai_stage_name som rubrik.

### 6.2 Gör clipboard-kopiering async + feedback

* Samma fil:

  * gör handlern async
  * await navigator.clipboard.writeText(text)
  * visa UI feedback:

    * t.ex. “Copied” text i knappen i 1–2 sekunder, eller toast (beroende på UI-kit)
  * hantera Promise-error: visa “Copy failed” feedback (inte silent)

### 6.3 “Klipp ut allt som ett enda långt stycke”

* Om checkbox “include prompts” är av:

  * bygg ett single-paragraph output med mellanslag mellan loggrader (ingen dubbel newline)
* Om checkbox är på:

  * inkludera prompts men fortfarande kontrollerat format

**Acceptance:**

* Rubriker matchar era steg (AI1, AI2, AI3… eller stage-namn).
* Copy-knapp ger omedelbar visuell respons.

---

## 7) Regression-test: kör igenom era exempel och verifiera

1. Kör pipeline på ett urval där ni tidigare sett:

   * saknade SEK-belopp men original finns
   * card receipts där sista fyra ibland saknas
   * faktura som tidigare gav company resolution fail
   * vendor: Loopia, Rusta, Midjourney (eller liknande mönster)

2. Verifiera i DB:

   * exchange_rate != 0.0 för SEK (ska vara 1.0)
   * gross_amount_sek inte null när currency=SEK och original finns
   * AI4 ger antingen valid proposals eller “needs_review”, aldrig fatal crash
   * duplicate ingest blir “already imported”

3. Verifiera UI:

   * loggmodal visar endast senaste loggen (om ni har det kravet aktivt)
   * stage rubriker är korrekta
   * clipboard fungerar + feedback

---

Om du vill kan jag även skriva en **kort “Definition of Done”** som agenten checkar av (10 rader) så du direkt ser om allt är uppfyllt efter körningen.
Ja tack
gör det
codebase_251219_07-42.zip
Zip Archive
Det blev skillnad till det bättre men även tydliga felaktigheter. log_text ska inte användas alls för agentdialog  nu smygs prompter in där. Tittar man på ai_processing_history prompt text och prompt respons så är det uselt genomfört och implementerat. Gör med hjälp av python en ny analys av databasen igen.Se över slutresultatet för alla importerade kvitto i db. Undersök varför det är fel på ett antal poster. Summera felen så i får en öveblick och därefter förslå enlösning
Jättebra! Du har presenterat felen på ett utmärkt sätt. Jag vill att du nu gräver dig ännu djupare ner i koden och analyerar var i koden detta sker, och därefter presenterar en lösning som är hållbar, med exakta kodreferenser, för varje fel.
Ja tack. 
skapa en startprompt för agenten som hänvisar till din plan som finns i /docs/bugs/CONVERSION_ADJUSTMENTS_2025-12-19_part_2.md
codebase_251219_21-31.zip
Zip Archive
Då är dessa ändringar implementerade. Använd python och gå igenom hela kodbasen och gör följande: 
1. Kontrollera att de ändringar du specificerade är genomförda på rätt sätt, att kodbas och databas är konfigurerade rätt
2. Gå igenom den nya importen som är gjord och granska resultatet. Kontrollera att samtliga tabeller är ifyllda på rätt sätt enligt SoT och att det inte sker sammanblandning av loggar, att konteringen går igenom 100% korrekt och att funktionaliteten är fullständig. 
3. Skapa en rapport och presentera det du kommit fram till. 

Kodbasen med inkluderad db bifogad.
kör patchDå är de senaste ändringarna implementerade för att höja kvaliten på konverteringen. Hela kodbasen och databas finns bifogad i zip-filen. All historik på de tidigare chattar vi haft runt detta ligger som en md-fil. Jag ser att det fortfarande inte fungerar bra. Använd python och gå igenom hela kodbasen och gör följande: 1. Kontrollera att de ändringar du specificerade är genomförda på rätt sätt, att kodbas och databas är konfigurerade rätt 2. Gå igenom den nya importen som är gjord och granska resultatet. Kontrollera att samtliga tabeller är ifyllda på rätt sätt enligt SoT och att det inte sker sammanblandning av loggar, att konteringen går igenom 100% korrekt och att funktionaliteten är fullständig. 3. Skapa en rapport och presentera det du kommit fram till. Kodbasen med inkluderad db bifogad.
Då vill jag ha följande:
1. Ett tillägg i både SoT och implementation: Om ett pris finns - med moms eller utan moms - så ska övriga parametrar räknas ut så inga fält lämnas tomma. 
2. Samma sak för främmande valutor om detta är möjligt. Via riksbankens API så kan man hämta växlingskurser om det skulle hjälpa till. Detta syns annars i FC-Cardfakturan - så är det en dålig ide kan man lämna det tomt. 
3. Belopp som syns i tabeller i process, kvitton och kö ska visas i originalvaluta.
4. Gör ytterligare en djup granskning av konverteringsflödet och sök efter andra problem i konverteringen. Gå igenom alla AI-prompter. De ligger i databasen, gå också igenom unified_files och undersök exakt vad som saknas för varje kvitto. 
5. Leverera en revidering av de AI-prompter du anser behöver justeras. Gör detta på engelska.
6. Leverera uppdaterad SoT-dokumentation på de ändringar du avser att göra
7. Leverera en extremt detaljerad instruktion på engelska till agenten som steg för steg går igenom allting som behöver åtgärdas. Denna ska vara komplett inklusive startprmpt, tasks med subtasks, testförfarande, tydliga instrutktioner om exakt vilken kod som ska ändras. 

All information finns i zip-filen inklusive SoT, och även det nyua dokumentet docs/SWEA_API_FAQ.md

Har du några frågor innan du sätter igång?

Ja skapa båda dessa
codebase_251221_08-01.zip
Zip Archive
Då har körningen gått igenom, och vi kan se vissa framsteg. Men mycket saknas fortfarade främst när det kommer till AI4 - kontering. Gör en ny analys där du som tidigare går igenom resultatet. Använd python för analys av av kodbasen och databasen. Läs igenom AIprompterna - främst AI4 (du måste läsa från db) - och gå igenom samtliga poster i databasen. Redovisa ditt resultat och föreslå de ändringar vi behöver göra för att komma i mål. Kom ihåg att det är ifrån en windowsmiljö, att jag kör docker och att du ska använda python för din analys. 
gällande mojibakes. Jag lägger ju in detta under menyval AI i systemet. Något är det som konverterar helt fel där då. Varför gör det det?
Jag vill inte göra massa fix - jag vill skapa en helt fungerande version vi kan lita på och ta bort allt skräp. Jag sitter på svenskt windows, mitt huvudspråk är svenska. Hela databasen innehåller svensk data. Således måste vi göra de anpassningar som krävs. Men jag vill inte LAGA saker jag vill konstruera om detta så det verkligen fungerar. I hela databasen. Detta är ju en central funktion - om inte frontend skriver in rätt data i db är det ju kört från början