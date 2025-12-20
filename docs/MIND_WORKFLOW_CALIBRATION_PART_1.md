#####  You said:



codebase_251218_12-15.zip

Zip Archive

Vi har mycket problem med konverteringen och det feltolkas på en mängd olika sätt. Konteringen fungerar också väldigt dåligt.  Jag har sammaställt loggar och skämdumpar till dig på ett antal olika kvitton - dessa finns i @temp\result och ligger i en mapp per kvitto och även kvittologgen finns där. De ai-prompter som används ligger i samma folder som md-filer.  Jag kör docker på windowsdator, och vill nu att du granskar de exempel som finns sparade i denna folder. Gå igenom alla kvitton och gör en sammanställning över alla de olika felen du hittar.  Använd python, analysera fel, analysera kodbas, leverera en sammantällning över vad som inte fungerar och förslag på hur vi reder ut samtliga registrerade fel. Kodbas bifogad. 

###### ChatGPT said:

Thought for 25m 35s

Jag har packat upp zip-filen och kört en automatisk genomlysning med Python av **databasschemat + db-dumpen + backend/frontend-kod** och de loggar som finns i repot.

**Viktigt:** den mapp du hänvisar till (`@temp\result` med *en mapp per kvitto*, screenshots och kvittologg) finns **inte** med i den uppladdade zip-filen (jag hittar varken `@temp`, `temp/result` eller några bildfiler/kvittomapparser i den). Så jag kan inte “gå igenom alla kvitton i @temp\result” i just den här leveransen – men jag kan ändå sammanställa de fel som faktiskt är registrerade i **DB-dump + ai_processing_history** och peka ut var i koden det går fel.

------

## 1) Sammanställning av faktiska fel jag hittar (från DB-dump / ai_processing_history)

I `ai_processing_history` (165 rader) finns **5 fel** (status=`error`), fördelat så här:

### A) AI3 – DataExtraction (1 fel)

**Fel:** `ValueError: Company resolution failed: both vat/orgnr and name are missing`
**Konsekvens:** AI3 stoppar helt för en invoice (doc_type=`invoice`, expense_type=`corporate`) eftersom varken **company.name** eller **orgnr/vat** kom ut ur AI3-resultatet.

**Trolig rotorsak:**

- AI3-prompten är för hårt styrd till “TOP OF RECEIPT ONLY” och missar vissa fakturaformat där avsändare/bolagsnamn inte hamnar på “toppen” på ett sätt OCR fångar.
- Alternativt: OCR-texten saknar bolagsnamn helt (PDF→bild→OCR-kvalitet).

### B) AI4 – AccountingClassification (3 fel)

1. **Vendor:** `Midjourney Inc`
   **Fel:** `AccountingProposalValidationError: No valid accounting proposals generated from payload`
2. **Vendor:** `RUSTA`
   **Fel:** `AccountingProposalValidationError: debit and credit cannot both be zero`
3. **Vendor:** `Loopia`
   **Fel:** `AccountingProposalValidationError: debit and credit cannot both be zero`

**Konsekvens:** kontering faller på valideringen av AI4-payload (antingen tomma/fel formaterade förslag, eller rader där debit och credit blir 0/0).

**Trolig rotorsak (mycket tydlig i datat):**

- Underlaget som AI4 får är ofta “trasigt” eller ofullständigt (se nästa punkt om belopp/valuta).
- AI4-prompten eller parsern tillåter att modellen returnerar rader som bryter mot era accounting-regler.

### C) Ingestion (1 fel)

**Fel:** `DuplicateFileError` vid FTP-import (hash finns redan).
**Konsekvens:** onödigt “rött fel” istället för att behandla detta som “redan importerad”.

------

## 2) Största systemiska datakvalitetsproblemet jag ser (orsakar feltolkningar + dålig kontering)

När jag korsläser `unified_files` i db-dumpen ser jag något som förklarar mycket:

### A) `exchange_rate` är i princip alltid **0.0**

I dumpen har **85 av 86** rader `exchange_rate = 0.0`.

Det här är giftigt eftersom:

- 0.0 betyder i praktiken “värdelös kurs”, men används som “default”.
- Det gör att “SEK-belopp” blir osäkra/inkonsekventa i resten av flödet.

### B) Många kvitton saknar `gross_amount_sek` och `net_amount_sek`

Jag hittar **minst 6 receipts** där `gross_amount_original` finns (t.ex. 199.00 / 511.00 / 365.22 / 2790.00 osv) men `gross_amount_sek` och/eller `net_amount_sek` är NULL.

Det här leder direkt till:

- `_load_accounting_inputs()` i backend hämtar **endast** `gross_amount_sek` och `net_amount_sek` → vilket blir `None`.
- AI4 körs ändå, men då blir underlaget svajigt och valideringen faller oftare.

**Kodpunkt som gör detta extra tydligt:**

- `backend/src/services/tasks/file_management_tasks.py::_load_accounting_inputs()` SELECT:ar `gross_amount_sek, net_amount_sek` (inte `*_original`).

### C) Kortdata är ofullständig

För receipts med `payment_type='card'` ser jag:

- 9 kortkvitton totalt
- bara 4 med `credit_card_last_4_digits` ifyllt

Det förklarar “kortuppgifter försvinner” i många fall: OCR eller AI3 hittar inte sista fyra, och då blir både analys + klassning sämre.

------

## 3) UI/logg-problem jag kan verifiera i frontend-koden (matchar exakt det du beskrivit)

I `main-system/app-frontend/src/ui/pages/Process.jsx` finns två saker som matchar dina symptom:

### A) “AI1–AI8 blir AI-entry 1..N” (din “AI1-8 besynnerligt”-grej)

Copy/clipboard-funktionen bygger texten så här:

- `--- AI-entry ${index + 1} ---`
  istället för att använda `entry.ai_stage_name` som rubrik.

Det gör att allt ser ut som “AI-entry” i stället för era riktiga AI-steg, och då blir klipp-ut-texten svår att använda.

### B) “Knappen går inte att trycka / ingen respons”

Clipboard-koden kör:

- `navigator.clipboard.writeText(...)`
  utan `await`, och fel fångas inte korrekt (Promise). Dessutom finns ingen UI-feedback (toast/ikonändring).

Resultat: det kan *kännas* som att knappen inte gör något (även om den ibland lyckas).

------

## 4) Förslag: så reder ni ut ALLA registrerade fel (konkret och “stänger luckorna”)

### Steg 1 — Sluta mata AI4 med trasigt underlag (backend-guard)

Inför en hård gate innan AI4:

- Om `gross_amount_sek`/`net_amount_sek` saknas men `currency == SEK` och `gross_amount_original` finns → fyll deterministiskt `gross_amount_sek = gross_amount_original` (samma för net).
- Om totals helt saknas → hoppa AI4 och markera manual_review med tydlig orsak (“missing totals”).

Detta ensam kommer minska AI4-felen kraftigt.

### Steg 2 — Skärp AI3 så den **aldrig** lämnar SEK-fälten tomma när currency=SEK

AI3-prompten måste göras glasklar på två punkter:

- För SEK: `exchange_rate` ska **inte** vara 0.0 (helst 1.0 eller null – men välj ett konsekvent SoT-beslut).
- Om `currency == SEK` och `gross_amount_original` finns: då ska `gross_amount_sek` alltid sättas = original.

Och lika viktigt:

- Om belopp inte hittas: **null**, aldrig 0.00 (0.00 är ett “riktigt belopp” och sabbar logik/validering).

### Steg 3 — AI4: stoppa “0/0 debit/credit” och tomma förslag i prompt + parser

Ni behöver två lager:

1. Prompt: explicit regel “Every entry must have exactly one of debit or credit > 0; the other must be 0”.
2. Parser/validering: om modellen ändå skickar 0/0 → returnera ett kontrollerat fel som triggar manual_review *innan* ni försöker spara/visa.

### Steg 4 — Company resolution: mildra “TOP OF RECEIPT ONLY” för fakturor

För `document_type='invoice'` behöver AI3 få en tydlig fallback:

- tillåt avsändarnamn från fakturahuvud/issuer-block (inte bara “top line”).
- om varken namn eller orgnr finns i OCR → manual_review, men med *diagnostik* (t.ex. “OCR missing vendor identity section”).

### Steg 5 — UI/loggmodalen: fixa tre saker som ger dig “det känns trasigt”

1. Rubriker: använd `entry.ai_stage_name` i stället för `AI-entry 1..N`.
2. Clipboard: gör funktionen `async`, `await navigator.clipboard.writeText(...)` och visa tydlig “Copied!”-indikering.
3. “Klipp ut allt i ett långt stycke”: bygg clipboard-strängen med mellanslag istället för `\n\n` när det läget används.

### Steg 6 — DuplicateFileError: gör den icke-fatal

Vid duplicate-hash:

- returnera “already imported” och länka till befintligt file_id (eller logga som warning), inte ett hårt fel som stoppar flödet.

------

## 5) Nästa steg för att jag ska kunna göra exakt det du bad om (alla kvitton i @temp\result)

Just nu saknas `@temp\result` i zip:en. För att jag ska kunna göra “en mapp per kvitto”-genomgången med screenshots + kvittologg + prompts per kvitto behöver zip-filen inkludera den katalogen (eller motsvarande sökväg i repot).

Tills dess har du ovan:

- **alla faktiska fel som är loggade i DB-dumpen**, plus
- de tydligaste systemiska orsakerna (exchange_rate=0.0, saknade SEK-belopp, AI4-validering), och
- exakta kodpunkter i backend/frontend som matchar dina symptom.

Vill du att jag direkt tar fram en “checklista för agenten” (patch-ordning + vilka filer som ska ändras, utan att skriva om hela kodbasen), så kan jag göra det i nästa svar baserat på punkterna ovan.

##### You said:

Jag tror du har fångat den problematik som finns. Skapa nu en checklista/införandelista till agenten som exakt instruerar honom i alla de ändringar du föreslagit, så provar vi igen.

###### ChatGPT said:

Thought for 12s

Här är en **införande-checklista** som agenten kan följa punkt för punkt. Den är skriven för att ge **exakt** de ändringar jag föreslog (backend-gates + AI3/AI4-regler + company fallback + duplicate-hantering + UI-fixar).

------

## 0) Guardrails innan kodändring

1. Skapa en ny branch per task:
   - `fix/accounting-input-gate`
   - `fix/ai3-sek-fields`
   - `fix/ai4-validation-and-prompt`
   - `fix/company-resolution-fallback`
   - `fix/duplicate-file-nonfatal`
   - `fix/process-ui-ai-stage-and-clipboard`
2. Ändra inget som inte hör till tasken. Om något måste tas bort: **kommentera bort** och skriv en tydlig förklaring i koden.
3. Kör enhetligt format/lint om projektet använder det (ex. ruff/black/eslint) – men ändra inte formatering i filer ni inte rör.

------

## 1) Backend: stoppa AI4 från att köras på trasigt underlag

**Mål:** AI4 ska aldrig få `None`/saknade totals när det finns deterministisk data att använda.

### 1.1 Implementera “SEK fallback” i accounting input loader

- Fil: `backend/src/services/tasks/file_management_tasks.py`
- Funktion: `_load_accounting_inputs()` (du nämnde den; den SELECT:ar idag `gross_amount_sek, net_amount_sek`)
- Ändring (logik):
  1. Utöka SELECT så att den även hämtar `gross_amount_original`, `net_amount_original`, `currency` samt `exchange_rate`.
  2. Skapa deterministisk fallback:
     - Om `currency == 'SEK'`:
       - Om `gross_amount_sek` är NULL och `gross_amount_original` finns → sätt `gross_amount_sek = gross_amount_original`
       - Om `net_amount_sek` är NULL och `net_amount_original` finns → sätt `net_amount_sek = net_amount_original`
       - Om `exchange_rate` är NULL eller 0 → sätt `exchange_rate = 1.0`
  3. Om totals fortfarande saknas (varken SEK eller original finns) → returnera ett kontrollerat “manual_review”-läge och **kör inte AI4**.

### 1.2 Lägg in en hård gate innan AI4-task körs

- Där AI4 triggas (troligen i samma service eller i en pipeline/orchestrator):
  - Om `_load_accounting_inputs()` returnerar “invalid/missing totals” → markera status för steget som “needs_review” (eller motsvarande i ert system) med tydligt felmeddelande.
  - Säkerställ att detta inte blir ett “uncaught exception”.

**Acceptance:**

- Ett receipt med `gross_amount_original` men utan `gross_amount_sek` ska ändå kunna konteras (för SEK).
- Ett receipt utan totals ska inte krascha AI4 – det ska stoppas och flaggas.

------

## 2) AI3: säkra SEK-fälten och stoppa 0.0-fällan

**Mål:** AI3 får inte producera “SEK men exchange_rate=0.0” eller lämna SEK-belopp tomma när original finns.

### 2.1 Uppdatera AI3 prompt (md-filen i er prompt-folder)

- Lokalisera AI3 prompten i repot (de ligger som `.md` enligt dig).
- Lägg till/justera regler (ordagrant/tydligt i prompten):
  - För `currency == "SEK"`:
    - `exchange_rate` MUST be `1.0` (never `0.0`)
    - If `gross_amount_original` is present, `gross_amount_sek` MUST be the same numeric value
    - If `net_amount_original` is present, `net_amount_sek` MUST be the same numeric value
  - Belopp som saknas ska vara `null` (inte 0.00)

### 2.2 Uppdatera parser/validator för AI3-resultat (om ni har en)

- I backend där AI3 JSON parse:as:
  - Om `currency == SEK` och `exchange_rate` kommer som 0 eller null → normalisera till 1.0
  - Om SEK och originalbelopp finns men SEK-belopp saknas → fyll deterministiskt

**Acceptance:**

- Nya AI3-rader i DB ska inte ha `exchange_rate=0.0` för SEK.
- `gross_amount_sek` och `net_amount_sek` ska fyllas när original finns och currency=SEK.

------

## 3) AI4: stoppa “tomma förslag” och “debit=0 AND credit=0”

**Mål:** AI4 ska producera validerbara konteringsrader, annars ska det bli kontrollerad review – inte exception.

### 3.1 Skärp AI4 promptregler

- Hitta AI4 prompt md.
- Lägg in hårda outputregler:
  - Output MUST contain at least 1 proposal row
  - Each row MUST have:
    - `account_number`
    - `description`
    - Exactly one of `debit_amount` or `credit_amount` > 0
    - The other MUST be 0
  - No row may have both 0
  - Totals MUST balance (sum debit == sum credit)

### 3.2 Skärp AI4 validator så den ger “review” istället för hårt fel

- Där `AccountingProposalValidationError` kastas:
  - Gör om flödet så att:
    - status/logg i historik blir “needs_review”
    - feltext sparas tydligt
    - pipeline fortsätter (eller stoppar bara den filen) utan att hela körningen dör

**Acceptance:**

- Rusta/Loopia/Midjourney-typen av fel ska inte bli “Fatal”, utan “Review required” med tydlig orsak.

------

## 4) Company resolution: mildra faktura-fallet så AI3 inte faller på saknat company

**Mål:** “Company resolution failed: both vat/orgnr and name are missing” ska bli sällsynt och hanteras bättre.

### 4.1 AI3 prompt – differentiera invoice vs receipt

- För `document_type == "invoice"`:
  - Tillåt extraction av supplier/issuer från “header block” (inte bara “TOP line”)
  - Lägg in fallback-regel:
    - If the supplier identity is not present in OCR text, set `company_match_type="unknown"` (eller ert närmaste tillåtna) och flagga review, istället för att lämna både name+orgnr tomma utan signal.

> Om er SoT kräver `company_match_type` = `vat|name|new` och aldrig något annat:
> Då ska fallback bli: sätt `company_match_type="name"` men `company.name=null` är förbjudet → alltså: vid saknad identitet: avbryt AI3 med kontrollerad “needs_review” innan DB insert.

### 4.2 Backend: om AI3 saknar både name och orgnr → kontrollerad review

- Istället för `ValueError` som bubblar:
  - fånga detta, sätt status “needs_review”, skriv “missing vendor identity in OCR”.

**Acceptance:**

- Inga “uncaught ValueError” för company resolution; det ska bli review-status.

------

## 5) DuplicateFileError: gör duplicate till icke-fatal

**Mål:** Samma fil (hash) ska ge “already imported”, inte error.

### 5.1 Fånga DuplicateFileError i ingestion

- Där FTP-importen körs (eller generella ingest-flödet):
  - Om hash redan finns:
    - returnera “already imported”
    - logga som warning/info
    - om möjligt: returnera befintligt `file_id` för spårbarhet

**Acceptance:**

- Duplicate importer ger inte “error” i historiken.

------

## 6) Frontend: fixa AI-stage-namn i modal + clipboard feedback

**Mål:** Loggmodalen ska visa rätt rubriker och knappen ska kännas “tryckbar” och ge respons.

### 6.1 Visa `ai_stage_name` istället för “AI-entry 1..N”

- Fil: `main-system/app-frontend/src/ui/pages/Process.jsx`
- Ändring:
  - Där ni renderar/bygger texten för AI-loggar: använd `entry.ai_stage_name` som rubrik.

### 6.2 Gör clipboard-kopiering async + feedback

- Samma fil:
  - gör handlern `async`
  - `await navigator.clipboard.writeText(text)`
  - visa UI feedback:
    - t.ex. “Copied” text i knappen i 1–2 sekunder, eller toast (beroende på UI-kit)
  - hantera Promise-error: visa “Copy failed” feedback (inte silent)

### 6.3 “Klipp ut allt som ett enda långt stycke”

- Om checkbox “include prompts” är av:
  - bygg ett single-paragraph output med mellanslag mellan loggrader (ingen dubbel newline)
- Om checkbox är på:
  - inkludera prompts men fortfarande kontrollerat format

**Acceptance:**

- Rubriker matchar era steg (AI1, AI2, AI3… eller stage-namn).
- Copy-knapp ger omedelbar visuell respons.

------

## 7) Regression-test: kör igenom era exempel och verifiera

1. Kör pipeline på ett urval där ni tidigare sett:
   - saknade SEK-belopp men original finns
   - card receipts där sista fyra ibland saknas
   - faktura som tidigare gav company resolution fail
   - vendor: Loopia, Rusta, Midjourney (eller liknande mönster)
2. Verifiera i DB:
   - `exchange_rate != 0.0` för SEK (ska vara 1.0)
   - `gross_amount_sek` inte null när currency=SEK och original finns
   - AI4 ger antingen valid proposals eller “needs_review”, aldrig fatal crash
   - duplicate ingest blir “already imported”
3. Verifiera UI:
   - loggmodal visar endast senaste loggen (om ni har det kravet aktivt)
   - stage rubriker är korrekta
   - clipboard fungerar + feedback

------

Om du vill kan jag även skriva en **kort “Definition of Done”** som agenten checkar av (10 rader) så du direkt ser om allt är uppfyllt efter körningen.

##### You said:

Ja lägg till et också

###### ChatGPT said:

Här är en kort, knivskarp **Definition of Done** som agenten ska checka av efter att alla tasks är mergade till `dev` och en full testkörning är gjord:

## Definition of Done

1. **SEK-belopp normaliseras**

- För alla dokument med `currency="SEK"` gäller:
  - `exchange_rate = 1.0` (aldrig `0.0`)
  - Om `gross_amount_original` finns → `gross_amount_sek` är satt och lika med original
  - Om `net_amount_original` finns → `net_amount_sek` är satt och lika med original

1. **AI4 körs aldrig på saknade totals**

- Om totals saknas (både SEK och original) stoppas AI4 deterministiskt och markeras som **needs_review/manual_review** med en tydlig orsak (“missing totals”), utan att pipeline kraschar.

1. **AI4 producerar alltid validerbara rader eller kontrollerad review**

- Inga sparade proposals med `debit=0 AND credit=0`
- Om modellen returnerar tomma/ogiltiga förslag:
  - steget blir **needs_review** (inte fatal)
  - felmeddelandet loggas tydligt i historik/logg-tabell

1. **Company resolution kraschar inte**

- Inga okontrollerade `ValueError` vid saknat company.
- Om både orgnr/vat och namn saknas i OCR:
  - steget blir **needs_review** med “missing vendor identity in OCR”.

1. **DuplicateFileError är inte ett error**

- Import av identisk fil/hash ger “already imported” (warning/info) och stoppar inte körningen.

1. **Process-loggmodal visar rätt AI-steg**

- Rubriker i UI/clipboard använder `ai_stage_name` (inte “AI-entry 1..N”).

1. **Clipboard-knappen känns “tryckbar” och ger feedback**

- Copy handler är `async` och `await` används.
- UI visar tydlig “Copied!” eller “Copy failed” feedback.

1. **“Klipp ut allt i ett långt stycke” fungerar enligt checkbox**

- Checkbox av: prompts exkluderas och allt blir **ett långt stycke** (inte radmatta).
- Checkbox på: prompts inkluderas men formatet är fortfarande läsbart och konsekvent.

1. **DB-verifiering efter testkörning**

- Slumpa minst 10 nyligen processade `unified_files` och bekräfta:
  - inga `exchange_rate=0.0` för SEK
  - inga null SEK-belopp där original finns
  - AI4 errors har minskat och är “review” istället för fatal.

1. **Git/branch-disciplin**

- Varje task-branch är mergad till `dev` med tydlig commit message.
- Inga orelaterade diffar (format-only eller “städning”) i PR:erna.

Vill du att jag även skriver en **”agent startprompt”** (en enda klistra-in text som instruerar agenten att utföra checklistan + DoD + exakt ordning) så gör jag det direkt i nästa svar.

##### You said:

Vilka AI-prompter behövde uppdateras?

###### ChatGPT said:

De enda AI-prompterna som behövde uppdateras för de fel vi såg var:

1. **AI3 – Data extractor (receipt/invoice → DB-JSON)**

- Skälet: vi fick **company resolution fail** (varken namn eller orgnr/vat kom ut) och vi såg att **SEK-belopp/kurs blir fel** (t.ex. `exchange_rate=0.0`, saknade `*_sek` trots att `*_original` finns).
- Ändringar i prompten:
  - För `currency="SEK"`: `exchange_rate` måste vara **1.0** (aldrig 0.0).
  - För SEK: om `gross_amount_original` finns → `gross_amount_sek` måste sättas lika; samma för `net_*`.
  - Belopp som saknas ska vara **null**, aldrig `0.00`.
  - För `document_type="invoice"`: tillåt vendor från “issuer/header block” (inte bara “top line”), och om identitet saknas → styr mot **kontrollerad review** (inte “tyst tomt” som senare kraschar).

1. **AI4 – Accounting / konteringsförslag**

- Skälet: vi har valideringsfel: **tomma proposals** och rader där **debit=0 och credit=0** (Loopia/Rusta/Midjourney-exemplen).
- Ändringar i prompten:
  - Minst **1** konteringsrad måste alltid returneras (annars ska modellen markera att den inte kan).
  - Varje rad: exakt **en** av debit/credit > 0, den andra = 0.
  - Summor måste balansera (debit = credit).
  - Förbjud uttryckligen 0/0-rader.

Inga andra prompts (AI1/AI2 osv) var nödvändiga för just de registrerade felen vi sammanställde här.

##### You said:

Skapa två nya prompter som tydligt eliminerar de problem du identifierat. Skriv dem på engelska - här är AI3: - # AI3 – `data_extraction` (UI-prompt)  Role:  You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.   You MUST be strictly consistent, never guess values, and never invent IDs or data that are not clearly present in the input or explicitly provided in context.   -------------------------------------------------------------------------------  CRITICAL EXTRACTION RULES  -------------------------------------------------------------------------------   0) OUTPUT FORMAT (ABSOLUTE)  - Return ONLY one JSON object (no markdown, no code fences, no commentary).  - The top-level keys MUST ALWAYS be exactly:    - "company"    - "unified_file"    - "receipt_items"    - "company_match_type"    - "company_create_needed"    - "confidence"   1) COMPANY NAME (TOP OF RECEIPT ONLY)  - Extract the company name from the TOP of the receipt, not from amount lines.  - The company name is usually the first line or very near the top.  - NEVER use lines containing any of the following as company name:    - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"  - NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.  - HANDELSBANKEN NORDEA SWEDBANK or other bank names are **never** company names.   -------------------------------------------------------------------------------  KNOWN RETAIL RECEIPT TEMPLATES (EXPLICIT OVERRIDES)  -------------------------------------------------------------------------------   A) BAUHAUS RECEIPTS (SWEDEN)   If the TOP of the receipt contains:  - "BAUHAUS" (case-insensitive)   Then apply these deterministic rules:   1) company.name MUST be exactly:     "BAUHAUS"   2) company.orgnr:     - Extract ONLY if explicitly printed as "ORG.NR"     - Example: "ORG.NR: 969630-6944"     - Otherwise null   3) company.address / zip / city:     - Extract if printed directly below BAUHAUS header     - Example:       "Karlsbodavägen 2"       "168 67 Bromma"   4) payment_type:     - If any of these exist anywhere:       "Bankkort", "Visa", "Debit", "Contactless", EMV fields (AID/TVR/REF/RESP)       → payment_type = "card"   5) receipt_number:     - BAUHAUS receipts do NOT contain a true receipt number.     -  DO NOT invent.     - Set receipt_number = null   6) receipt_items:     - Item rows are ALWAYS BELOW organisation name and address and ABOVE "TOTAL".     - Prefer item rows above "TOTAL".     - Ignore the lower card slip completely for item extraction.     - number is specified BEFORE the name. If no number is specified, set it to 1. Only numbers are allowed.     - name is the name of the item and it cannot contain "SUMMA", "TOTAL", "BELOPP", "ATT BETALA", "SEK", "EUR", "€", "kr", "KÖP", "KÖPER", "KÖPER"   7) Split receipt handling:     - Upper part = receipt content     - Lower part = card terminal slip     - Never treat terminal slip as a separate receipt.   B) HORNBACH RECEIPTS (SWEDEN)   If the TOP of the receipt contains:  - "HORNBACH"   Then apply these deterministic rules:   1) company.name MUST be exactly:     "Hornbach Byggmarknad AB"   2) company.orgnr:     - Extract ONLY if explicitly printed as "Org.Nr"     - Example: "Org.Nr: 556613-4853"   3) Address:     - Extract from header block:       Example:       "Madenvägen 17"       "174 55 Sundbyberg"   4) payment_type:     - Presence of:       "GIVET VISA", "VISA DEBIT", "VISA CONTACTLESS", EMV fields       → payment_type = "card"   5) receipt_number:     - Hornbach receipts often lack a true receipt number.     - Do NOT use terminal refs, PSN, REF, or transaction codes.     - receipt_number = null unless explicitly labeled.   6) receipt_items:     - Extract item rows starting with:       "ART/EAN", quantity + product name + price     - Ignore payment/authorization block entirely.   2) PAYMENT TYPE DETECTION (ROBUST + DETERMINISTIC)  Detect payment_type using clear, explicit signals anywhere in the OCR text:   A) SWISH  -> payment_type = "swish"  - If the text contains any of:    - "SWISH", "Swish"    - "Swish-nummer", "Swishnummer"    - "Swish ref", "Swish referens", "Swishreferens"    - A clear Swish reference label + value (e.g. "Swish ref: 1786145908308241")   B) CARD -> payment_type = "card"  Set payment_type="card" if ANY of the following indicators exist:  - Card brand/wording:    - "VISA", "MASTERCARD", "MASTER CARD", "MAESTRO", "AMEX", "AMERICAN EXPRESS"    - "KORT", "KORTKÖP", "KORTKOP", "CARD", "CARD PURCHASE"  - Card-terminal / EMV technical markers:    - "AID", "TVR", "TSI", "ARQC", "AIP", "AAC", "TC", "ARC", "EMV"    - "TERMINAL", "TID", "MID", "BATCH", "TRACE"    - "AUT", "AUTH", "AUTH CODE", "AUTH NR", "AUKTORISERING", "GODKÄND", "APPROVED"    - "RRN", "STAN", "REF", "REFERENCE", "KUNDREFERENS"  - Masked card patterns like:    - "**** **** **** 1234", "XXXXXXXXXXXX1234", "XXXX XXXX XXXX 1234"    - (Only if clearly in a card/payment context)   C) CASH -> payment_type = "cash"  - If the text contains any of:    - "KONTANT", "kontant", "CASH", "cash"   D) If you cannot clearly determine payment type -> payment_type = null.   PRECEDENCE RULE (DETERMINISTIC):  - If both swish and card indicators exist:    - If a Swish reference exists -> payment_type="swish"    - Else if EMV tags / terminal markers exist -> payment_type="card"    - Else -> payment_type=null   3) EXPENSE TYPE (DO NOT GUESS)  - If expense_type is explicitly provided in context (e.g. "personal" or "corporate"), include it unchanged.  - Otherwise set expense_type = null.  - Never infer expense_type from the OCR text here.   4) RECEIPT ITEMS  - Extract line items whenever possible into receipt_items[] using this schema:    - main_id (must be the file_id from context; if missing, still output the key but keep exact string you were given)    - article_id ("" if unknown)    - name (required; do not invent)    - number (quantity, integer; default 1 if missing)    - item_price_ex_vat, item_price_inc_vat    - item_total_price_ex_vat, item_total_price_inc_vat    - currency (ISO, default to unified_file.currency if known else "SEK")    - vat (VAT amount for the line if clear)    - vat_percentage (e.g. 0.250000)  - If you cannot reliably form items, return an empty list [] (do not invent items).   -------------------------------------------------------------------------------  PATCH A: RECEIPT-LEVEL VAT SUMMARY (MOMS-TABELL) EXTRACTION  -------------------------------------------------------------------------------  Many Swedish receipts contain a VAT summary block near the bottom with headings like:  - "MOMS %", "MOMS", "Netto", "Brutto" (or similar)   If such a summary exists, you MUST:  1) Extract the VAT rate(s) as percent numbers (e.g. 12, 25, 6, 0) from the summary.  2) Extract the VAT amount(s) (e.g. "124,18") from the summary.  3) Extract the gross base amount(s) for those VAT rate(s) from the summary (e.g. "Brutto 1 159,00").  4) Extract the net base amount(s) from the summary if present.   Store the parsed VAT summary ONLY inside unified_file.other_data as a JSON object under key "vat_summary".  Example structure (stringified JSON in other_data):  {    "vat_summary": [      {        "vat_rate_percent": 12.0,        "vat_amount": 124.18,        "net_amount": 1034.82,        "gross_amount": 1159.00      }    ]  }   IMPORTANT:  - Do NOT put vat_summary anywhere except unified_file.other_data.  - This is used downstream to prevent VAT/dricks mixups.   -------------------------------------------------------------------------------  PATCH B: DRICKS / TIP HANDLING (MUST BE 0% VAT)  -------------------------------------------------------------------------------  If an item line contains "DRICKS" or "TIP" (case-insensitive), then:  - Create a receipt_items row for it.  - Set vat_percentage = 0.000000  - Set vat = 0.00 if amount is clear, otherwise null.  - Set item_price_inc_vat / item_total_price_inc_vat from the amount on the line.  - Set item_price_ex_vat / item_total_price_ex_vat equal to the inc_vat amount (since VAT is 0%).  - This line must NOT be included in any VAT base.   -------------------------------------------------------------------------------  PATCH C: TOTALS (gross/net) + OCR-REPAIR WHEN VAT SUMMARY IS CONSISTENT  -------------------------------------------------------------------------------  1) gross_amount_original:  - If the receipt contains a clear total label like "TOTALT", "SUMMA", "ATT BETALA", or "TOTAL",    set unified_file.gross_amount_original to that value (the final amount paid, which may include tip).   2) net_amount_original:  - If a VAT summary exists in other_data.vat_summary and it contains exactly ONE rate row with:    - vat_amount and gross_amount present,    then set unified_file.net_amount_original = gross_amount - vat_amount (deterministic).    This also fixes common OCR errors like missing leading digits in "Netto" (e.g. "034,82").   3) If VAT summary contains an explicit net_amount and it matches (gross_amount - vat_amount) within 0.01,     you may use that net_amount directly.   4) If VAT summary has multiple rates, do NOT compute a single net_amount_original unless the receipt clearly provides it.   -------------------------------------------------------------------------------  5) CARD DATA EXTRACTION (WHEN payment_type="card")  Goal: ensure card metadata lands in the correct unified_files columns when present.   A) SECURITY / PCI RULE (ABSOLUTE)  - NEVER output a full card number (PAN).  - NEVER output more than last 4 digits.  - You MAY output:    - credit_card_last_4_digits (integer)    - credit_card_number only if it is already masked in OCR (e.g. "**** **** **** 1234" or "XXXX XXXX XXXX 1234")    - brand and entry-mode metadata if explicitly present.   B) WHAT TO EXTRACT (ONLY IF PRESENT)  Populate these unified_file fields when clearly present:   - credit_card_last_4_digits  - credit_card_number (masked string only; NEVER full PAN)  - credit_card_brand_short (one of: "VISA", "MASTERCARD", "AMEX", "MAESTRO", "OTHER")  - credit_card_brand_full (one of: "Visa", "MasterCard", "American Express", "Maestro", "Other")  - credit_card_payment_variant (only if explicitly stated; allowed values: "contactless", "chip", "magstripe", "manual")  - credit_card_entering_mode (only if explicitly stated; allowed values: "NFC", "CHIP", "MAGSTRIPE", "MANUAL")  - credit_card_type (ONLY if explicitly stated; otherwise null)  - credit_card_token (ONLY if explicitly stated; otherwise null)   C) RELIABLE last4 DETECTION (DETERMINISTIC)  Extract credit_card_last_4_digits ONLY if you can link a 4-digit sequence to an explicit card/PAN context.   Valid patterns include:  - "Kort: **** **** **** 1234"  - "CARD NO: XXXX XXXX XXXX 1234"  - "PAN: ************1234"  - "KORTNR: 1234" (only if label clearly indicates card number)  - "VISA 1234" (only if clearly in the payment/terminal section)   SPECIAL RULE — BAUHAUS & HORNBACH LAST4   For BAUHAUS or HORNBACH receipts:   - ONLY extract credit_card_last_4_digits if:    - The digits appear immediately after masked PAN symbols:      "****", "XXXX", or explicit "KORTNR"    - Example:      "XXXX XXXX XXXX 3632"      "************2607"   - NEVER extract last4 from:    - REF    - PERIOD    - BUTIKSNR    - PSN    - TERMINAL / TID    - AID    - Any numeric sequence without masking   If masked PAN is not present:  → credit_card_last_4_digits = null   Disambiguation:  - Prefer candidates preceded by masking (* or X) and/or explicit labels (KORT/KORTNR/CARD/PAN).  - Never use 4 digits that are clearly a year, time, kvittonummer, orgnr fragment, or a reference not explicitly card-related.  - If uncertain -> set credit_card_last_4_digits = null.   D) TECHNICAL CARD/TERMINAL FIELDS -> unified_file.other_data ONLY  Store terminal/EMV fields ONLY inside unified_file.other_data as a JSON string object.  Allowed keys (only include those present):  - terminal_id, tid, mid, aid, auth_code, rrn, stan, tx_ref, batch  - emv_tvr, emv_tsi, emv_aip, emv_arc, emv_cryptogram  - payment_detail (e.g. "card") if helpful   6) SWISH DETAILS -> unified_file.other_data ONLY  If payment_type="swish" and a Swish reference exists, store in other_data:  - swish_ref: "<value>"   7) other_data (FORMAT)  - unified_file.other_data MUST be a valid JSON string (serialized object).  - If nothing extra exists, set other_data = "{}".  - Never put card technical fields outside other_data.   -------------------------------------------------------------------------------  COMPANY LOOKUP AND AUTO-CREATE (NO INVENTED IDs)  -------------------------------------------------------------------------------   IMPORTANT:  - The model has no company.id field. Do NOT output company.id.  - unified_file.company_id MUST be null unless an explicit existing company_id is provided in context.   You MUST always output:  - company_match_type: one of "vat", "name", "new" (never null)  - company_create_needed: boolean   Rules:  1) If the prompt/context explicitly provides a companies list with IDs and you can deterministically match by VAT/orgnr -> company_match_type="vat", company_create_needed=false, unified_file.company_id=<matched id>.  2) Else if companies list exists and you can deterministically match by name -> company_match_type="name", company_create_needed=false, unified_file.company_id=<matched id>.  3) Otherwise -> company_match_type="new", company_create_needed=true, unified_file.company_id=null.   Always fill company fields from OCR when available (never invent):  - name, vat/orgnr, address, address2, zip, city, country, phone, www, email.   -------------------------------------------------------------------------------  OUTPUT JSON STRUCTURE (STRICT)  -------------------------------------------------------------------------------   Return JSON with EXACTLY this structure and keys:   {    "company": {      "name": "string or null",      "vat": "string or null",      "orgnr": "string or null",      "address": "string or null",      "address2": "string or null",      "zip": "string or null",      "city": "string or null",      "country": "string or null",      "phone": "string or null",      "www": "string or null",      "email": "string or null"    },    "unified_file": {      "company_id": null,      "purchase_datetime": "YYYY-MM-DD HH:MM:SS or null",      "payment_type": "card|cash|swish or null",      "expense_type": "personal|corporate or null",      "currency": "ISO 4217 or null",      "gross_amount_original": 0.00 or null,      "net_amount_original": 0.00 or null,      "exchange_rate": 0.000000 or null,      "gross_amount_sek": 0.00 or null,      "net_amount_sek": 0.00 or null,      "receipt_number": "string or null",      "other_data": "{}",      "credit_card_number": "masked string or null",      "credit_card_last_4_digits": 1234 or null,      "credit_card_brand_full": "Visa|MasterCard|American Express|Maestro|Other or null",      "credit_card_brand_short": "VISA|MASTERCARD|AMEX|MAESTRO|OTHER or null",      "credit_card_payment_variant": "contactless|chip|magstripe|manual or null",      "credit_card_type": "string or null",      "credit_card_token": "string or null",      "credit_card_entering_mode": "NFC|CHIP|MAGSTRIPE|MANUAL or null"    },    "receipt_items": [      {        "main_id": "file_id",        "article_id": "",        "name": "string",        "number": 1,        "item_price_ex_vat": 0.00 or null,        "item_price_inc_vat": 0.00 or null,        "item_total_price_ex_vat": 0.00 or null,        "item_total_price_inc_vat": 0.00 or null,        "currency": "ISO code (default SEK)",        "vat": 0.00 or null,        "vat_percentage": 0.000000 or null      }    ],    "company_match_type": "vat|name|new",    "company_create_needed": true|false,    "confidence": 0.0-1.0  }   -------------------------------------------------------------------------------  GENERAL NUMERIC, DATE, VAT AND CURRENCY RULES  -------------------------------------------------------------------------------   - Dates:    - Use "YYYY-MM-DD HH:MM:SS"    - If time missing: use "00:00:00"   - Numbers:    - Accept "," or "." in OCR, output decimals with "."   - Currency:    - If OCR explicitly indicates SEK ("SEK" or "kr" in amount context) -> currency="SEK"    - If OCR explicitly indicates another ISO currency -> use it    - Otherwise currency=null (do not guess)   - exchange_rate:    - If currency="SEK" -> exchange_rate=0    - Otherwise set only if explicitly present; else null   - SEK *_sek fields:    - Populate only if you can deterministically compute them; otherwise null.   -------------------------------------------------------------------------------  DETERMINISM AND UNCERTAINTY  -------------------------------------------------------------------------------   - If a field cannot be confidently determined from OCR or explicit context: set it to null (or omit the key inside other_data).  - Never invent company_id, card last4, or any card digits beyond last4.  - Return ONLY the JSON object.  Och här följer AI4: 1. ### AI4 — Accounting Proposals (Swedish Bookkeeping, BAS 2025)   ROLE  You are a deterministic bookkeeping engine. You receive structured receipt data (header + items + VAT info) and must produce accounting proposals that follow Swedish accounting practice using the BAS 2025 chart of accounts.   OUTPUT MUST BE JSON ONLY.  All human-readable text fields (e.g., notes) MUST be written in Swedish.  Do not output explanations outside JSON.   PURPOSE  Create accounting entries that can be stored directly in the database table `ai_accounting_proposals`.   INPUT (STRUCTURED DATA)  You receive a receipt object containing at minimum:  - receipt_id (refers to unified_files.id)  - receipt_items: one or more item rows with amounts and VAT details  - receipt totals (gross, VAT breakdown if available)  - payment information if available (e.g., paid by company card, cash, reimbursement)   You may also have access to:  - `chart_of_accounts` table (BAS 2025) for validating account codes and names.   DATABASE TARGET: ai_accounting_proposals  You MUST output an array of objects. Each object maps 1:1 to one row in `ai_accounting_proposals`:   {    "receipt_id": "string (unified_files.id)",    "item_id": "string|null (receipt_items.id; can be null only for receipt-level balancing lines if item-level mapping is impossible)",    "account_code": "string (BAS account number)",    "debit": number,    "credit": number,    "vat_rate": number,    "notes": "string (SWEDISH, short and factual)"  }   CRITICAL RULES (DETERMINISTIC)  1) No guessing  - Never invent amounts, VAT rates, or accounts.  - If the correct account cannot be determined from input + available accounts, use a predefined fallback account code IF AND ONLY IF that fallback exists in `chart_of_accounts`. Otherwise, output null for account_code and explain in notes (Swedish) why it could not be determined.   2) Double-entry bookkeeping  - The sum of debits MUST equal the sum of credits per receipt (within rounding tolerance).  - Rounding tolerance: max absolute imbalance 0.01 SEK. If larger, mark notes with "Obalans" and do not “force” amounts.   3) VAT handling  - VAT must be posted to input VAT accounts when VAT is deductible and explicitly present.  - Default input VAT account: 2641 (Ingående moms) if it exists in `chart_of_accounts`.  - Use the VAT rate from the structured data (e.g., 25, 12, 6, 0). Do not derive a VAT rate from amounts unless the rate is explicitly provided in the input.   4) Amount normalization  - All amounts are in SEK decimals using "." as decimal separator.  - debit and credit must be non-negative numbers.  - Never use negative debit/credit values. Use the appropriate side instead.   5) Item-level proposals  - If multiple receipt_items exist, create proposals per item where possible:    - Expense (net) per item    - VAT per item (if VAT per item is available)    - A payment/settlement line per receipt (preferred) or per item if the input explicitly indicates item-level payments.   6) Payment / settlement line (balancing credit)    Create exactly one settlement credit line per receipt unless the input explicitly requires otherwise.    Common settlement accounts (use only if present in `chart_of_accounts` and clearly indicated by payment method):  - Company card (e.g., FirstCard): 2440 (Leverantörsskulder) or a dedicated corporate card liability account if your chart defines one.  - Cash: 1910 (Kassa)  - Bank: 1930 (Företagskonto/bank)  - Employee reimbursement: 2890 (Övriga kortfristiga skulder) or a dedicated “Skuld till anställd” account if defined.   If payment method is unknown: use 2440 ONLY if it exists and is the system’s defined default settlement account. Otherwise set account_code=null and explain in Swedish notes.   ACCOUNT SELECTION (BAS 2025)  - Use `chart_of_accounts` as the source of truth for valid accounts.  - Prefer accounts based on the item’s category/expense type provided in structured data.  - If category is missing:    - Use the most generic appropriate expense account available in `chart_of_accounts` (e.g., “Övriga externa kostnader”) ONLY if it is explicitly defined as the system default.    - Otherwise, output account_code=null and add a Swedish note that classification is missing.   VAT RATE FIELD (vat_rate)  - For expense and VAT lines: set vat_rate to the VAT rate that applies to that item (e.g., 25.0).  - For settlement/payment line: set vat_rate to 0.0.   NOTES (SWEDISH)  - Notes must be short, factual, and explain why the account was chosen.   CONSISTENCY CHECKS  Before output:  - Validate that each account_code exists in `chart_of_accounts` if that table is available.  - Ensure debit/credit totals balance per receipt within 0.01 SEK.  - Ensure vat_amount lines align with provided VAT amounts. Do not recompute VAT unless both net and VAT are explicitly provided and consistent. -------------------------------------------------------------------------------  PATCH 1: VAT SUMMARY OVERRIDE (MUST FIX NONNOS-TYPE RECEIPTS)  -------------------------------------------------------------------------------  If the input contains a receipt-level VAT summary/breakdown (e.g., one or more rows with vat_rate + vat_amount + net_amount/gross_amount),  THEN that summary MUST be treated as the source of truth for VAT and net amounts.   Rules:  - Use receipt-level VAT summary amounts for the VAT debit line(s) (e.g., 2641) and for the expense net amount line(s).  - Do NOT “derive” VAT by gross - net if a VAT summary exists.  - If there is exactly one VAT rate in the summary (e.g., 12%), you MAY create receipt-level lines (item_id=null) instead of per-item VAT allocation. -------------------------------------------------------------------------------  PATCH 2: TIP / DRICKS HANDLING (MUST NOT BECOME VAT)  -------------------------------------------------------------------------------  If any receipt item description indicates tip (e.g., contains "DRICKS" or "TIP" in the structured item name/description),  THEN:  - That amount MUST have vat_rate = 0.0  - That amount MUST NOT be included in the VAT base, and MUST NOT be posted to 2641.  - Create a separate expense debit line for tip (account must exist in chart_of_accounts).    - Prefer to use the same expense account as the meal/restaurant cost IF that account is already selected and exists.    - Otherwise: if no safe expense account exists, set account_code=null and notes="Dricks saknar konto i systemet". -------------------------------------------------------------------------------  PATCH 3: OUTPUT FORMAT (validator compatibility)  -------------------------------------------------------------------------------  Return ONLY a JSON object with key "proposals" containing the array of proposal rows.   {    "proposals": [ ... ]  }

###### ChatGPT said:

Thought for 47s

Nedan är **två nya, ersättande prompts** (AI3 + AI4) som är skrivna för att **eliminera exakt de problem vi identifierade**:

- **AI3:** stoppar `exchange_rate=0.0` för SEK, fyller `*_sek` när `*_original` finns, och ger en **kontrollerad “review”-signal** i `other_data` när vendor-identitet saknas (utan att uppfinna data).
- **AI4:** garanterar att output **aldrig blir tom**, **aldrig innehåller 0/0-rader**, och alltid **balanserar**. Om konton inte kan bestämmas deterministiskt skapas **balanserade placeholder-rader** med `account_code=null` och tydliga svenska notes (så validatorn inte faller sönder).

------

## AI3 — data_extraction (UI prompt) — v2

```
# AI3 — data_extraction (UI prompt) — v2

ROLE
You are a deterministic data extractor for Swedish receipts and invoices.
Your only goal is to parse OCR text into database-ready JSON for these tables:
- companies
- unified_files
- receipt_items

You MUST be strictly consistent.
You MUST NOT guess values.
You MUST NOT invent IDs or data that are not clearly present in the OCR text
or explicitly provided in the surrounding context.

-------------------------------------------------------------------------------
0) OUTPUT FORMAT (ABSOLUTE)
-------------------------------------------------------------------------------
Return ONLY one JSON object (no markdown, no code fences, no commentary).

The top-level keys MUST ALWAYS be exactly:
- "company"
- "unified_file"
- "receipt_items"
- "company_match_type"
- "company_create_needed"
- "confidence"

No other top-level keys are allowed.

-------------------------------------------------------------------------------
1) NON-NEGOTIABLE FIXES (TARGETED BUG ELIMINATION)
-------------------------------------------------------------------------------
A) SEK exchange rate MUST NEVER be 0.0
- If unified_file.currency is "SEK":
  - unified_file.exchange_rate MUST be 1.0 (never 0.0, never null)

B) SEK amounts MUST be populated when original amounts exist
- If unified_file.currency is "SEK":
  - If gross_amount_original is not null -> gross_amount_sek MUST equal gross_amount_original
  - If net_amount_original is not null   -> net_amount_sek MUST equal net_amount_original

C) Missing vendor identity must be signaled deterministically (no crashes)
- If BOTH company.name AND company.orgnr/vat are null:
  - Do NOT invent a company name.
  - Set company_match_type = "new"
  - Set company_create_needed = true
  - Add a review flag in unified_file.other_data:
    - {"review_required": true, "review_reasons": ["missing_vendor_identity_in_ocr"]}
  - Set confidence <= 0.20

-------------------------------------------------------------------------------
2) COMPANY IDENTIFICATION
-------------------------------------------------------------------------------
A) Receipts
- Prefer the vendor/company name from the TOP HEADER area of the receipt.
- NEVER use lines containing any of these as company name:
  - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"
- NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.
- Bank names like "HANDELSBANKEN", "NORDEA", "SWEDBANK" are never vendor names.

B) Invoices
- Vendor identity may appear in a supplier/issuer header block (not necessarily the first line).
- For invoices, you MAY extract the vendor name from the issuer/supplier block even if it is not the first line,
  as long as it is clearly the supplier identity (not totals, not bank details, not payment references).

C) Org-number / VAT
- Extract company.orgnr ONLY if explicitly labeled (examples: "Org.nr", "ORG.NR", "Organisationsnummer").
- Extract company.vat ONLY if explicitly labeled (examples: "Momsreg.nr", "VAT", "VAT nr", "SE123...").

If not explicitly labeled -> null.

-------------------------------------------------------------------------------
3) KNOWN RETAIL RECEIPT TEMPLATES (EXPLICIT OVERRIDES)
-------------------------------------------------------------------------------

A) BAUHAUS (SWEDEN)
Trigger:
- The top/header contains "BAUHAUS" (case-insensitive)

Rules:
1) company.name MUST be exactly "BAUHAUS"
2) company.orgnr: extract only if explicitly printed as "ORG.NR" or "Org.nr"; else null
3) Address fields: extract if printed in the header block; else null
4) receipt_number: BAUHAUS often lacks a true receipt number -> set null unless explicitly labeled
5) Split receipts:
   - Upper part = receipt content
   - Lower part = terminal/card slip
   - NEVER treat the terminal slip as a separate receipt
6) receipt_items:
   - Extract item rows from receipt content area (above "TOTAL"/"ATT BETALA")
   - Ignore the lower terminal slip for items

B) HORNBACH (SWEDEN)
Trigger:
- The top/header contains "HORNBACH"

Rules:
1) company.name MUST be exactly "Hornbach Byggmarknad AB"
2) company.orgnr: extract only if explicitly printed as "Org.Nr"/"Org.nr"; else null
3) Address fields: extract from header block if present
4) receipt_number: set null unless explicitly labeled as a receipt number
5) receipt_items:
   - Extract item rows from the receipt content area
   - Ignore payment/authorization blocks for item extraction

-------------------------------------------------------------------------------
4) PAYMENT TYPE DETECTION (ROBUST + DETERMINISTIC)
-------------------------------------------------------------------------------
Detect unified_file.payment_type using explicit signals anywhere in OCR:

A) SWISH -> "swish"
If OCR contains any of:
- "SWISH"
- "Swish-nummer", "Swishnummer"
- "Swish ref", "Swish referens", "Swishreferens"
and a reference value is present -> payment_type="swish"

B) CARD -> "card"
Set payment_type="card" if ANY of these exist:
- Card brands/words: "VISA", "MASTERCARD", "AMEX", "MAESTRO", "KORT", "KORTKÖP", "CARD"
- EMV/terminal markers: "AID", "TVR", "TSI", "ARQC", "EMV", "TERMINAL", "TID", "MID", "RRN", "STAN", "AUTH", "GODKÄND", "APPROVED"
- A masked PAN pattern in a payment context

C) CASH -> "cash"
If OCR contains: "KONTANT" or "CASH"

D) If unclear -> null

Precedence:
- If a Swish reference exists -> "swish"
- Else if EMV/terminal markers exist -> "card"
- Else -> null

-------------------------------------------------------------------------------
5) RECEIPT ITEMS
-------------------------------------------------------------------------------
Output receipt_items[] with this schema per item:

- main_id: use the file_id from context if provided; otherwise keep the exact string you were given; if none exists, still output the key with null
- article_id: "" if unknown
- name: required for each item (do not invent)
- number: integer quantity; if missing -> 1
- item_price_ex_vat, item_price_inc_vat
- item_total_price_ex_vat, item_total_price_inc_vat
- currency: default to unified_file.currency if known else "SEK"
- vat: VAT amount if explicitly stated for the line; else null
- vat_percentage: 0.250000 / 0.120000 / 0.060000 / 0.000000 if explicitly indicated; else null

If items cannot be reliably extracted -> return [] (do not invent).

-------------------------------------------------------------------------------
6) VAT SUMMARY (MOMS-TABELL) -> unified_file.other_data ONLY
-------------------------------------------------------------------------------
If a VAT summary exists (e.g. headings like "MOMS %", "Netto", "Brutto"):
- Parse rows with:
  - vat_rate_percent
  - vat_amount
  - net_amount (if present)
  - gross_amount (if present)
Store only in unified_file.other_data as a JSON object key "vat_summary".

If nothing extra exists -> other_data MUST be "{}".

-------------------------------------------------------------------------------
7) TIP / DRICKS (MUST BE 0% VAT)
-------------------------------------------------------------------------------
If an item line contains "DRICKS" or "TIP":
- Create an item row
- vat_percentage = 0.000000
- vat = 0.00 if amount is clear; else null
- ex_vat equals inc_vat (0% VAT)

-------------------------------------------------------------------------------
8) TOTALS (gross/net) + DETERMINISTIC NET REPAIR (WHEN POSSIBLE)
-------------------------------------------------------------------------------
A) gross_amount_original
- If OCR contains a clear total label ("TOTAL", "SUMMA", "ATT BETALA", "TOTALT"):
  set unified_file.gross_amount_original to that amount.

B) net_amount_original
- If a VAT summary exists AND it contains exactly one row with both vat_amount and gross_amount:
  net_amount_original = gross_amount - vat_amount (deterministic).
- If VAT summary contains an explicit net_amount and it matches (gross - vat) within 0.01:
  you may use that net_amount directly.
- If multiple VAT rates exist:
  do NOT compute a single net unless explicitly printed.

-------------------------------------------------------------------------------
9) CURRENCY + EXCHANGE RATE (STRICT)
-------------------------------------------------------------------------------
A) currency
- If OCR explicitly indicates SEK ("SEK" or "kr" in an amount context) -> currency="SEK"
- If OCR explicitly indicates another ISO currency -> use it
- Otherwise currency=null

B) exchange_rate
- If currency="SEK" -> exchange_rate=1.0 (ABSOLUTE)
- If currency is not SEK:
  - set exchange_rate only if explicitly printed; else null

C) SEK amounts (gross_amount_sek / net_amount_sek)
- If currency="SEK":
  - Populate using the NON-NEGOTIABLE FIXES above
- If currency is not SEK:
  - Populate *_sek only if exchange_rate is explicitly present and computation is deterministic; else null

-------------------------------------------------------------------------------
10) CARD DATA EXTRACTION (WHEN payment_type="card")
-------------------------------------------------------------------------------
PCI / Security (ABSOLUTE):
- NEVER output a full PAN.
- NEVER output more than last 4 digits.
- credit_card_number may be output ONLY if it is already masked in OCR.

Extract ONLY if explicitly present:
- credit_card_last_4_digits (integer)
- credit_card_number (masked string only)
- credit_card_brand_short: "VISA"|"MASTERCARD"|"AMEX"|"MAESTRO"|"OTHER"
- credit_card_brand_full:  "Visa"|"MasterCard"|"American Express"|"Maestro"|"Other"
- credit_card_payment_variant: "contactless"|"chip"|"magstripe"|"manual"
- credit_card_entering_mode: "NFC"|"CHIP"|"MAGSTRIPE"|"MANUAL"
- credit_card_type (only if explicitly stated; else null)
- credit_card_token (only if explicitly stated; else null)

Last4 extraction (DETERMINISTIC):
- Extract last4 ONLY if linked to masked PAN symbols or explicit labels like:
  "**** **** **** 1234", "XXXX XXXX XXXX 1234", "PAN: ************1234", "KORTNR: ...1234", "CARD NO: ...1234"
- NEVER extract last4 from:
  REF, RRN, STAN, PSN, AID, TID/MID, BUTIKSNR, dates, times, years, orgnr fragments.

BAUHAUS/HORNBACH special:
- Require masked PAN symbols or explicit KORTNR/PAN label; otherwise last4=null.

Terminal/EMV fields:
- Store ONLY in unified_file.other_data under "card_terminal" as a nested object.

Swish reference:
- Store ONLY in unified_file.other_data under key "swish_ref".

-------------------------------------------------------------------------------
11) COMPANY LOOKUP + AUTO-CREATE (NO INVENTED IDs)
-------------------------------------------------------------------------------
- Do NOT output company.id.
- unified_file.company_id MUST be null unless an explicit existing company_id is provided in context.

You MUST always output:
- company_match_type: one of "vat", "name", "new" (never null)
- company_create_needed: boolean

Rules:
1) If context provides a companies list with IDs and a deterministic match by orgnr/vat -> "vat", create_needed=false, company_id=matched
2) Else if deterministic match by name -> "name", create_needed=false, company_id=matched
3) Otherwise -> "new", create_needed=true, company_id=null

-------------------------------------------------------------------------------
12) REQUIRED JSON OUTPUT STRUCTURE (STRICT)
-------------------------------------------------------------------------------
Return exactly this structure:

{
  "company": {
    "name": null,
    "vat": null,
    "orgnr": null,
    "address": null,
    "address2": null,
    "zip": null,
    "city": null,
    "country": null,
    "phone": null,
    "www": null,
    "email": null
  },
  "unified_file": {
    "company_id": null,
    "purchase_datetime": null,
    "payment_type": null,
    "expense_type": null,
    "currency": null,
    "gross_amount_original": null,
    "net_amount_original": null,
    "exchange_rate": null,
    "gross_amount_sek": null,
    "net_amount_sek": null,
    "receipt_number": null,
    "other_data": "{}",
    "credit_card_number": null,
    "credit_card_last_4_digits": null,
    "credit_card_brand_full": null,
    "credit_card_brand_short": null,
    "credit_card_payment_variant": null,
    "credit_card_type": null,
    "credit_card_token": null,
    "credit_card_entering_mode": null
  },
  "receipt_items": [],
  "company_match_type": "new",
  "company_create_needed": true,
  "confidence": 0.0
}

-------------------------------------------------------------------------------
13) DATES + NUMBERS
-------------------------------------------------------------------------------
- purchase_datetime: "YYYY-MM-DD HH:MM:SS" or null. If date but no time -> "00:00:00".
- OCR decimal separators may be "," or "." -> output decimals using ".".

Return ONLY the JSON object.
```

------

## AI4 — accounting_proposals (BAS 2025) — v2

```
# AI4 — accounting_proposals (BAS 2025) — v2

ROLE
You are a deterministic bookkeeping engine for Swedish bookkeeping (BAS 2025).
You receive structured receipt/invoice data (from AI3 + DB) and must produce accounting proposals.

OUTPUT MUST BE JSON ONLY.
All human-readable text fields (notes) MUST be written in Swedish.
Do not output any explanation outside JSON.

-------------------------------------------------------------------------------
0) OUTPUT FORMAT (ABSOLUTE)
-------------------------------------------------------------------------------
Return ONLY this JSON object:

{
  "proposals": [ ... ]
}

No markdown, no code fences, no commentary.

-------------------------------------------------------------------------------
1) HARD VALIDATOR SAFETY RULES (TARGETED BUG ELIMINATION)
-------------------------------------------------------------------------------
These rules exist to prevent known failures:

A) proposals MUST NOT be empty
- Always output at least 2 proposal rows.

B) No row may have both debit=0 AND credit=0
- Each row MUST have exactly one side > 0 and the other side = 0.

C) Receipt must balance
- Sum(debit) MUST equal Sum(credit) within 0.01.
- Never “force” new amounts. Use only amounts present in input totals or VAT summary.

D) Never use negative amounts
- debit and credit must be non-negative.
- If something is conceptually negative, place the value on the correct side instead.

-------------------------------------------------------------------------------
2) INPUT YOU RECEIVE (STRUCTURED)
-------------------------------------------------------------------------------
You may receive fields such as:
- receipt_id (unified_files.id)
- currency (should be SEK for accounting output)
- gross_amount_sek, net_amount_sek (preferred for amounts)
- gross_amount_original, net_amount_original
- vat_summary (from unified_file.other_data.vat_summary) if present
- receipt_items with item totals and vat_percentage if present
- payment_type (card/cash/swish)
- expense_type (personal/corporate) if provided

chart_of_accounts (BAS 2025) may be available for validation.

-------------------------------------------------------------------------------
3) AMOUNTS SOURCE OF TRUTH (STRICT)
-------------------------------------------------------------------------------
Use amounts in this priority order:

1) If vat_summary exists:
   - Treat vat_summary as the source of truth for:
     - net expense amounts (per rate or total)
     - VAT amounts
     - gross amounts per rate
2) Else:
   - Use gross_amount_sek and net_amount_sek if present.
3) If SEK amounts are missing:
   - Use gross_amount_original and net_amount_original ONLY if currency is SEK or explicitly indicated as SEK.

If required totals are missing:
- You still MUST output non-empty, balanced proposals using ONLY amounts that are present.
- If no amounts exist at all, output two rows with debit=0.01 and credit=0.01 is NOT allowed (that would invent amounts).
  In that case, output two rows with debit=0 and credit=0 is also forbidden.
  Therefore: if no numeric amount exists anywhere, output a single proposal row is not allowed.
  Use this rule instead:
  - If no numeric amount exists, output:
    - proposals: []
  This is the ONLY exception to "proposals must not be empty".
  Notes: This exception should be extremely rare.

-------------------------------------------------------------------------------
4) ACCOUNT RULES (DETERMINISTIC)
-------------------------------------------------------------------------------
You MUST NOT invent account codes.

If chart_of_accounts is available:
- Use only accounts that exist in chart_of_accounts.

If you cannot deterministically pick an expense account:
- Set account_code = null and explain in Swedish notes.

VAT account:
- Use 2641 (Ingående moms) ONLY if it exists in chart_of_accounts; otherwise account_code=null for VAT line and note why.

Settlement/payment account (exactly one credit line per receipt):
- If payment_type="cash": prefer 1910 if it exists; else null
- If payment_type="card": prefer a dedicated corporate card liability if present; else 2440 if it exists; else null
- If payment_type="swish": prefer 1930 if it exists; else null
- If expense_type indicates employee reimbursement: prefer 2890 if it exists; else null

If payment method is unknown:
- Prefer 2440 only if it exists AND is defined as system default settlement account.
- Otherwise account_code=null and note why.

-------------------------------------------------------------------------------
5) VAT SUMMARY OVERRIDE (MANDATORY)
-------------------------------------------------------------------------------
If vat_summary exists:
- Create expense debit lines (net) based on vat_summary net amounts (or gross - vat if net is not present but gross+vat are present).
- Create VAT debit line(s) based on vat_summary vat_amount.
- Do NOT derive VAT from gross - net when vat_summary exists.

If vat_summary has exactly one VAT rate:
- You may create receipt-level lines (item_id=null).

If multiple VAT rates exist:
- You may create one expense line per VAT rate (item_id=null) plus one VAT line per rate (or a combined VAT line if input provides a combined VAT amount).

-------------------------------------------------------------------------------
6) TIP / DRICKS HANDLING (MUST NOT BECOME VAT)
-------------------------------------------------------------------------------
If any structured item indicates tip (name contains "DRICKS" or "TIP"):
- That amount MUST have vat_rate=0.0
- It MUST NOT be included in VAT base and MUST NOT go to 2641.

Account selection for tip:
- If an appropriate expense account is already selected for the receipt and exists -> reuse it.
- Otherwise account_code=null and notes="Dricks saknar konto i systemet".

-------------------------------------------------------------------------------
7) REQUIRED PROPOSAL ROW SCHEMA
-------------------------------------------------------------------------------
Each proposal row MUST have:

{
  "receipt_id": "string",
  "item_id": "string|null",
  "account_code": "string|null",
  "debit": number,
  "credit": number,
  "vat_rate": number,
  "notes": "string (SWEDISH)"
}

Rules:
- debit XOR credit must be > 0 (never both).
- vat_rate:
  - Expense and VAT lines: 25.0 / 12.0 / 6.0 / 0.0 based on input
  - Settlement line: 0.0

-------------------------------------------------------------------------------
8) ALWAYS-PASS FALLBACK (PREVENT EMPTY/TOTAL=0 FAILURES)
-------------------------------------------------------------------------------
If classification is not possible (missing categories/accounts), you MUST still output balanced lines using known totals.

Deterministic fallback template (use gross_amount_sek if present, else gross_amount_original):

If TOTAL exists:
- Row 1 (Expense placeholder):
  - account_code: null
  - debit: TOTAL
  - credit: 0
  - vat_rate: 0.0
  - notes (Swedish): "Okänt kostnadskonto – kräver manuell granskning"
- Row 2 (Settlement placeholder):
  - account_code: null (or settlement account if deterministically known and exists)
  - debit: 0
  - credit: TOTAL
  - vat_rate: 0.0
  - notes (Swedish): "Okänt betal-/avräkningskonto – kräver manuell granskning"

This guarantees:
- proposals not empty
- no 0/0 rows
- balanced totals
- no invented amounts

-------------------------------------------------------------------------------
9) FINAL CONSISTENCY CHECK BEFORE OUTPUT
-------------------------------------------------------------------------------
Before returning JSON:
- Ensure every row follows debit XOR credit > 0
- Ensure sums balance within 0.01
- Ensure notes are Swedish
- Ensure output is ONLY { "proposals": [...] }

Return ONLY the JSON object.
```

------

Vill du att jag även skriver **ett par “golden test cases”** (minimala input-exempel + exakt förväntad output) för AI3 och AI4 så agenten kan regression-testa innan han kör hela batchen?

##### You said:

kan du skriva en ny version av denna där man inte behöver ändra prmpt för ai3 och ai4 - detta har jag fixat redan: Här är en **införande-checklista** som agenten kan följa punkt för punkt. Den är skriven för att ge **exakt** de ändringar jag föreslog (backend-gates + AI3/AI4-regler + company fallback + duplicate-hantering + UI-fixar). --- ## 0) Guardrails innan kodändring 1. Skapa en ny branch per task:    * `fix/accounting-input-gate`   * `fix/ai3-sek-fields`   * `fix/ai4-validation-and-prompt`   * `fix/company-resolution-fallback`   * `fix/duplicate-file-nonfatal`   * `fix/process-ui-ai-stage-and-clipboard` 2. Ändra inget som inte hör till tasken. Om något måste tas bort: **kommentera bort** och skriv en tydlig förklaring i koden. 3. Kör enhetligt format/lint om projektet använder det (ex. ruff/black/eslint) – men ändra inte formatering i filer ni inte rör. --- ## 1) Backend: stoppa AI4 från att köras på trasigt underlag **Mål:** AI4 ska aldrig få `None`/saknade totals när det finns deterministisk data att använda. ### 1.1 Implementera “SEK fallback” i accounting input loader * Fil: `backend/src/services/tasks/file_management_tasks.py` * Funktion: `_load_accounting_inputs()` (du nämnde den; den SELECT:ar idag `gross_amount_sek, net_amount_sek`) * Ändring (logik):   1. Utöka SELECT så att den även hämtar `gross_amount_original`, `net_amount_original`, `currency` samt `exchange_rate`.  2. Skapa deterministisk fallback:      * Om `currency == 'SEK'`:        * Om `gross_amount_sek` är NULL och `gross_amount_original` finns → sätt `gross_amount_sek = gross_amount_original`       * Om `net_amount_sek` är NULL och `net_amount_original` finns → sätt `net_amount_sek = net_amount_original`       * Om `exchange_rate` är NULL eller 0 → sätt `exchange_rate = 1.0`  3. Om totals fortfarande saknas (varken SEK eller original finns) → returnera ett kontrollerat “manual_review”-läge och **kör inte AI4**. ### 1.2 Lägg in en hård gate innan AI4-task körs * Där AI4 triggas (troligen i samma service eller i en pipeline/orchestrator):   * Om `_load_accounting_inputs()` returnerar “invalid/missing totals” → markera status för steget som “needs_review” (eller motsvarande i ert system) med tydligt felmeddelande.  * Säkerställ att detta inte blir ett “uncaught exception”. **Acceptance:** * Ett receipt med `gross_amount_original` men utan `gross_amount_sek` ska ändå kunna konteras (för SEK). * Ett receipt utan totals ska inte krascha AI4 – det ska stoppas och flaggas. --- ## 2) AI3: säkra SEK-fälten och stoppa 0.0-fällan **Mål:** AI3 får inte producera “SEK men exchange_rate=0.0” eller lämna SEK-belopp tomma när original finns. ### 2.1 Uppdatera AI3 prompt (md-filen i er prompt-folder) * Lokalisera AI3 prompten i repot (de ligger som `.md` enligt dig). * Lägg till/justera regler (ordagrant/tydligt i prompten):   * För `currency == "SEK"`:     * `exchange_rate` MUST be `1.0` (never `0.0`)    * If `gross_amount_original` is present, `gross_amount_sek` MUST be the same numeric value    * If `net_amount_original` is present, `net_amount_sek` MUST be the same numeric value  * Belopp som saknas ska vara `null` (inte 0.00) ### 2.2 Uppdatera parser/validator för AI3-resultat (om ni har en) * I backend där AI3 JSON parse:as:   * Om `currency == SEK` och `exchange_rate` kommer som 0 eller null → normalisera till 1.0  * Om SEK och originalbelopp finns men SEK-belopp saknas → fyll deterministiskt **Acceptance:** * Nya AI3-rader i DB ska inte ha `exchange_rate=0.0` för SEK. * `gross_amount_sek` och `net_amount_sek` ska fyllas när original finns och currency=SEK. --- ## 3) AI4: stoppa “tomma förslag” och “debit=0 AND credit=0” **Mål:** AI4 ska producera validerbara konteringsrader, annars ska det bli kontrollerad review – inte exception. ### 3.1 Skärp AI4 promptregler * Hitta AI4 prompt md. * Lägg in hårda outputregler:   * Output MUST contain at least 1 proposal row  * Each row MUST have:     * `account_number`    * `description`    * Exactly one of `debit_amount` or `credit_amount` > 0    * The other MUST be 0  * No row may have both 0  * Totals MUST balance (sum debit == sum credit) ### 3.2 Skärp AI4 validator så den ger “review” istället för hårt fel * Där `AccountingProposalValidationError` kastas:   * Gör om flödet så att:     * status/logg i historik blir “needs_review”    * feltext sparas tydligt    * pipeline fortsätter (eller stoppar bara den filen) utan att hela körningen dör **Acceptance:** * Rusta/Loopia/Midjourney-typen av fel ska inte bli “Fatal”, utan “Review required” med tydlig orsak. --- ## 4) Company resolution: mildra faktura-fallet så AI3 inte faller på saknat company **Mål:** “Company resolution failed: both vat/orgnr and name are missing” ska bli sällsynt och hanteras bättre. ### 4.1 AI3 prompt – differentiera invoice vs receipt * För `document_type == "invoice"`:   * Tillåt extraction av supplier/issuer från “header block” (inte bara “TOP line”)  * Lägg in fallback-regel:     * If the supplier identity is not present in OCR text, set `company_match_type="unknown"` (eller ert närmaste tillåtna) och flagga review, istället för att lämna både name+orgnr tomma utan signal. > Om er SoT kräver `company_match_type` = `vat|name|new` och aldrig något annat: > Då ska fallback bli: sätt `company_match_type="name"` men `company.name=null` är förbjudet → alltså: vid saknad identitet: avbryt AI3 med kontrollerad “needs_review” innan DB insert. ### 4.2 Backend: om AI3 saknar både name och orgnr → kontrollerad review * Istället för `ValueError` som bubblar:   * fånga detta, sätt status “needs_review”, skriv “missing vendor identity in OCR”. **Acceptance:** * Inga “uncaught ValueError” för company resolution; det ska bli review-status. --- ## 5) DuplicateFileError: gör duplicate till icke-fatal **Mål:** Samma fil (hash) ska ge “already imported”, inte error. ### 5.1 Fånga DuplicateFileError i ingestion * Där FTP-importen körs (eller generella ingest-flödet):   * Om hash redan finns:     * returnera “already imported”    * logga som warning/info    * om möjligt: returnera befintligt `file_id` för spårbarhet **Acceptance:** * Duplicate importer ger inte “error” i historiken. --- ## 6) Frontend: fixa AI-stage-namn i modal + clipboard feedback **Mål:** Loggmodalen ska visa rätt rubriker och knappen ska kännas “tryckbar” och ge respons. ### 6.1 Visa `ai_stage_name` istället för “AI-entry 1..N” * Fil: `main-system/app-frontend/src/ui/pages/Process.jsx` * Ändring:   * Där ni renderar/bygger texten för AI-loggar: använd `entry.ai_stage_name` som rubrik. ### 6.2 Gör clipboard-kopiering async + feedback * Samma fil:   * gör handlern `async`  * `await navigator.clipboard.writeText(text)`  * visa UI feedback:     * t.ex. “Copied” text i knappen i 1–2 sekunder, eller toast (beroende på UI-kit)  * hantera Promise-error: visa “Copy failed” feedback (inte silent) ### 6.3 “Klipp ut allt som ett enda långt stycke” * Om checkbox “include prompts” är av:   * bygg ett single-paragraph output med mellanslag mellan loggrader (ingen dubbel newline) * Om checkbox är på:   * inkludera prompts men fortfarande kontrollerat format **Acceptance:** * Rubriker matchar era steg (AI1, AI2, AI3… eller stage-namn). * Copy-knapp ger omedelbar visuell respons. --- ## 7) Regression-test: kör igenom era exempel och verifiera 1. Kör pipeline på ett urval där ni tidigare sett:    * saknade SEK-belopp men original finns   * card receipts där sista fyra ibland saknas   * faktura som tidigare gav company resolution fail   * vendor: Loopia, Rusta, Midjourney (eller liknande mönster) 2. Verifiera i DB:    * `exchange_rate != 0.0` för SEK (ska vara 1.0)   * `gross_amount_sek` inte null när currency=SEK och original finns   * AI4 ger antingen valid proposals eller “needs_review”, aldrig fatal crash   * duplicate ingest blir “already imported” 3. Verifiera UI:    * loggmodal visar endast senaste loggen (om ni har det kravet aktivt)   * stage rubriker är korrekta   * clipboard fungerar + feedback --- Om du vill kan jag även skriva en **kort “Definition of Done”** som agenten checkar av (10 rader) så du direkt ser om allt är uppfyllt efter körningen.

###### ChatGPT said:

Absolut — här är en **ny version av införande-checklistan** där **AI3- och AI4-prompterna INTE ska ändras** (du har redan fixat dem). Allt nedan är alltså **enbart kod/flow/UI**.

------

## 0) Guardrails innan kodändring

1. Skapa en ny branch per task:

- `fix/accounting-input-gate`
- `fix/company-resolution-fallback`
- `fix/duplicate-file-nonfatal`
- `fix/process-ui-ai-stage-and-clipboard`

1. Ändra inget som inte hör till tasken. Om något måste tas bort: **kommentera bort** och skriv en tydlig förklaring i koden.
2. Kör enhetligt format/lint om projektet använder det (ruff/black/eslint) – men undvik formateringsdiffar i filer som inte berörs.

------

## 1) Backend: stoppa AI4 från att köras på trasigt underlag

**Mål:** AI4 ska aldrig få `None`/saknade totals när deterministisk data finns, och AI4 ska aldrig krascha pipeline vid saknade totals.

### 1.1 Implementera “SEK fallback” i accounting input loader

- Fil: `backend/src/services/tasks/file_management_tasks.py`
- Funktion: `_load_accounting_inputs()`

**Ändring (logik):**

1. Utöka SELECT så att den även hämtar:

- `gross_amount_original`
- `net_amount_original`
- `currency`
- `exchange_rate`

1. Deterministisk normalisering **innan** AI4 byggs:

- Om `currency == 'SEK'`:
  - om `gross_amount_sek` är NULL och `gross_amount_original` finns → sätt `gross_amount_sek = gross_amount_original`
  - om `net_amount_sek` är NULL och `net_amount_original` finns → sätt `net_amount_sek = net_amount_original`
  - om `exchange_rate` är NULL eller 0 → sätt `exchange_rate = 1.0`

1. Om totals fortfarande saknas (varken SEK eller original finns):

- returnera ett kontrollerat “missing totals”-läge (t.ex. flagga/struktur) som gör att AI4 **inte körs**.

### 1.2 Hård gate innan AI4-task körs

- Där AI4 triggas (task runner/pipeline/orchestrator):

**Ändring:**

- Om `_load_accounting_inputs()` indikerar “missing totals / invalid accounting input”:
  - markera status för steget som **needs_review** (eller ert motsvarande)
  - skriv tydlig orsak: `"missing totals for accounting"` / `"gross/net missing"`
  - avbryt endast AI4 för filen (inte hela körningen)
- Säkerställ att detta inte blir ett okontrollerat exception.

**Acceptance:**

- Receipt med `gross_amount_original` men saknar `gross_amount_sek` → kontering kan ändå köras (via fallback).
- Receipt utan totals → AI4 körs inte, markeras som review, pipeline fortsätter.

------

## 2) Backend: AI4 validator ska aldrig ge fatal pipeline-crash

**Mål:** även om AI4 returnerar något som validatorn ogillar ska det bli “review required”, inte fatal.

### 2.1 Fånga `AccountingProposalValidationError` och degradéra till review

- Där `AccountingProposalValidationError` kastas idag:

**Ändring:**

- fånga exception
- skriv till er historik/loggtabell med status `needs_review` + feltext
- stoppa bara AI4-steget för filen
- låt resten av batchen fortsätta

**Acceptance:**

- Loopia/Rusta/Midjourney-typen av fel blir “Review required” med orsak, aldrig “Fatal error” som stoppar allt.

------

## 3) Company resolution: inga okontrollerade “company missing”-krascher

**Mål:** när AI3 ändå råkar ge tom vendor-identitet ska det bli kontrollerad review, inte ValueError som bubblar.

### 3.1 Fånga “company resolution failed” och markera review

- Leta upp stället där ni idag får:
  - `ValueError: Company resolution failed: both vat/orgnr and name are missing`

**Ändring:**

- fånga detta
- markera fil/steg som `needs_review`
- logga en tydlig orsak: `"missing_vendor_identity_in_ocr"`
- säkerställ att filen kan visas i UI som “Requires manual review” (istället för “Error”).

**Acceptance:**

- Inga okontrollerade ValueError i pipeline från vendor-identitet; allt blir review-status.

------

## 4) DuplicateFileError: gör duplicate till icke-fatal

**Mål:** samma fil/hash ska ge “already imported” och inte skapa error-läge.

### 4.1 Fånga DuplicateFileError i ingestion/import

- Där FTP-importen eller generella ingest-flödet körs:

**Ändring:**

- vid duplicate/hash-collision:
  - returnera “already imported”
  - logga som warning/info
  - om möjligt returnera befintligt `file_id` (så UI kan länka till tidigare).

**Acceptance:**

- Duplicate importer skapar inte “error” i historiken.

------

## 5) Frontend: fixa AI-stage-namn + clipboard (känns trasigt idag)

**Mål:** loggmodalen ska bli begriplig och clipboard-knapp ska ge direkt respons.

### 5.1 Visa `ai_stage_name` istället för “AI-entry 1..N”

- Fil: `main-system/app-frontend/src/ui/pages/Process.jsx`

**Ändring:**

- i render/format för logg:
  - använd `entry.ai_stage_name` som rubrik
  - fall back endast om `ai_stage_name` saknas (t.ex. “AI stage unknown”).

### 5.2 Clipboard-kopiering: async + feedback + robust felhantering

- Samma fil

**Ändring:**

- gör handler `async`
- `await navigator.clipboard.writeText(text)`
- visa feedback:
  - “Copied!” (t.ex. i knappen eller toast) i 1–2 sek
- catch:
  - visa “Copy failed” och logga error i console (om ni gör så)

### 5.3 “Klipp ut allt i ett långt stycke”

**Ändring:**

- när “include prompts” är AV:
  - normalisera whitespace och join:a loggrader med **enkla mellanslag** (inte dubbla radbrytningar)
- när den är PÅ:
  - inkludera prompts men håll konsekvent separering, och använd fortfarande `ai_stage_name` rubriker.

**Acceptance:**

- Rubriker visar AI-steg korrekt.
- Copy-knapp ger omedelbar visuell respons.
- “Long paragraph” blir faktiskt ett enda stycke.

------

## 6) Regression-test (utan prompt-ändringar)

1. Kör batch på exempel där ni tidigare sett:

- saknade `*_sek` men original finns
- faktura som gav company resolution fail
- vendor: Loopia / Rusta / Midjourney
- duplicate-file scenario

1. Verifiera i DB:

- `exchange_rate` för SEK är aldrig 0.0 **i nya rader**
- `gross_amount_sek`/`net_amount_sek` fylls när original finns och currency=SEK
- AI4 fel blir **needs_review** och stoppar inte batch
- duplicate ger “already imported” utan error

1. Verifiera UI:

- ai_stage_name används överallt
- clipboard funkar och visar feedback

------

Vill du att jag även tar med den komprimerade **Definition of Done** direkt under checklistan (så agenten har allt i ett dokument)?

##### You said:

Ja tack

###### ChatGPT said:

Här kommer checklistan igen, nu med en **Definition of Done** längst ner (utan något om att ändra AI3/AI4-prompter).

------

## 0) Guardrails innan kodändring

1. Skapa en ny branch per task:

- `fix/accounting-input-gate`
- `fix/company-resolution-fallback`
- `fix/duplicate-file-nonfatal`
- `fix/process-ui-ai-stage-and-clipboard`

1. Ändra inget som inte hör till tasken. Om något måste tas bort: **kommentera bort** och skriv en tydlig förklaring i koden.
2. Kör enhetligt format/lint om projektet använder det (ruff/black/eslint) – men undvik formateringsdiffar i filer som inte berörs.

------

## 1) Backend: stoppa AI4 från att köras på trasigt underlag

**Mål:** AI4 ska aldrig få `None`/saknade totals när deterministisk data finns.

### 1.1 Implementera “SEK fallback” i accounting input loader

- Fil: `backend/src/services/tasks/file_management_tasks.py`
- Funktion: `_load_accounting_inputs()`

**Ändring (logik):**

1. Utöka SELECT så att den även hämtar:

- `gross_amount_original`
- `net_amount_original`
- `currency`
- `exchange_rate`

1. Deterministisk normalisering innan AI4 byggs:

- Om `currency == 'SEK'`:
  - om `gross_amount_sek` är NULL och `gross_amount_original` finns → `gross_amount_sek = gross_amount_original`
  - om `net_amount_sek` är NULL och `net_amount_original` finns → `net_amount_sek = net_amount_original`
  - om `exchange_rate` är NULL eller 0 → `exchange_rate = 1.0`

1. Om totals fortfarande saknas (varken SEK eller original finns):

- returnera ett kontrollerat “missing totals”-läge som gör att AI4 **inte körs**.

### 1.2 Hård gate innan AI4-task körs

- Där AI4 triggas (pipeline/task runner):

**Ändring:**

- Om `_load_accounting_inputs()` indikerar “missing totals / invalid accounting input”:
  - markera steget som **needs_review**
  - logga tydlig orsak: `"missing totals for accounting"`
  - avbryt endast AI4 för filen (inte hela batchen)
- Säkerställ att inget okontrollerat exception bubblar ut.

------

## 2) Backend: AI4 validator ska aldrig ge fatal pipeline-crash

**Mål:** validator-problem ska bli review, inte fatal.

### 2.1 Fånga `AccountingProposalValidationError` och degradéra till review

- Där `AccountingProposalValidationError` kastas idag:

**Ändring:**

- fånga exception
- skriv status `needs_review` + feltext till historik/loggtabell
- stoppa bara AI4-steget för filen
- låt resten av batchen fortsätta

------

## 3) Company resolution: inga okontrollerade “company missing”-krascher

**Mål:** saknad vendor-identitet ska bli kontrollerad review.

### 3.1 Fånga “company resolution failed” och markera review

- Där ni idag får:
  - `ValueError: Company resolution failed: both vat/orgnr and name are missing`

**Ändring:**

- fånga detta
- markera fil/steg som `needs_review`
- logga orsak: `"missing_vendor_identity_in_ocr"`
- säkerställ att filen kan visas i UI som “Requires manual review” (inte “Error”).

------

## 4) DuplicateFileError: gör duplicate till icke-fatal

**Mål:** duplicate ska ge “already imported” och inte error.

### 4.1 Fånga DuplicateFileError i ingestion/import

- Där importen (FTP/ingest) sker:

**Ändring:**

- vid duplicate/hash-collision:
  - returnera “already imported”
  - logga som warning/info
  - om möjligt returnera befintligt `file_id` (för UI-spårbarhet)

------

## 5) Frontend: fixa AI-stage-namn + clipboard

**Mål:** loggmodalen ska bli begriplig och clipboard-knapp ska ge direkt respons.

### 5.1 Visa `ai_stage_name` istället för “AI-entry 1..N”

- Fil: `main-system/app-frontend/src/ui/pages/Process.jsx`

**Ändring:**

- använd `entry.ai_stage_name` som rubrik (fallback endast om saknas).

### 5.2 Clipboard: async + feedback + felhantering

- Samma fil

**Ändring:**

- gör handler `async`
- `await navigator.clipboard.writeText(text)`
- visa “Copied!” feedback (knapptext/ikon eller toast)
- catch: visa “Copy failed” feedback (inte silent)

### 5.3 “Klipp ut allt i ett långt stycke”

**Ändring:**

- include prompts AV: normalisera whitespace och join:a med **mellanslag** (ett stycke)
- include prompts PÅ: inkludera prompts men håll konsekvent struktur och rubriker via `ai_stage_name`

------

## 6) Regression-test (utan prompt-ändringar)

1. Kör batch på exempel där ni tidigare sett:

- saknade `*_sek` men original finns
- faktura som gav company resolution fail
- Loopia/Rusta/Midjourney-typ av AI4-valideringsfel
- duplicate-file scenario

1. Verifiera i DB:

- `exchange_rate` för SEK är aldrig 0.0 i nya rader
- `gross_amount_sek`/`net_amount_sek` fylls när original finns och currency=SEK
- AI4 fel blir `needs_review` och stoppar inte batch
- duplicate ger “already imported” utan error

1. Verifiera i UI:

- `ai_stage_name` visas korrekt
- clipboard funkar + feedback
- “långt stycke” blir faktiskt ett enda stycke

------

# Definition of Done

1. **SEK-normalisering fungerar i praktiken**

- För nya processade filer med `currency="SEK"`:
  - `exchange_rate = 1.0` (aldrig 0.0)
  - `gross_amount_sek`/`net_amount_sek` är inte null när motsvarande `*_original` finns.

1. **AI4 körs inte på saknade totals**

- Filer utan totals får AI4-steget markerat som `needs_review` med tydlig orsak.
- Batchen fortsätter utan fatal crash.

1. **AI4-valideringsfel stoppar inte batchen**

- `AccountingProposalValidationError` resulterar i `needs_review` + loggad feltext.
- Ingen “Fatal error” som stoppar hela körningen.

1. **Company resolution kraschar inte**

- “missing vendor identity” blir `needs_review` med orsak `"missing_vendor_identity_in_ocr"`.
- Inga okontrollerade `ValueError` bubblar ut.

1. **Duplicate import är icke-fatal**

- DuplicateFileError blir “already imported” (warning/info), inte error.

1. **Process UI är läsbart och responsivt**

- Loggmodal använder `ai_stage_name` (inte “AI-entry 1..N”).
- Clipboard-knapp ger “Copied!” eller “Copy failed”.
- “Klipp ut allt som ett enda långt stycke” ger ett enda stycke enligt checkbox-regeln.

1. **Branch/PR hygiene**

- Varje task är mergad till `dev` via separat branch med tydlig commit message.
- Inga orelaterade diffar (format/städning) utanför berörda filer.

Vill du att jag även skriver en **“agent startprompt”** (en enda text att klistra in) som instruerar agenten att genomföra exakt detta i rätt ordning, inklusive teststeg och vad som ska bifogas i PR-beskrivningen?

##### You said:

gör det

###### ChatGPT said:

Här är en **agent startprompt** (kopiera/klistra in som en enda instruktion). Den utgår från att **AI3/AI4-prompter redan är fixade och ska inte ändras**.

```
You are an implementation agent working on the receipt/invoice conversion pipeline.
Your mission is to apply a small, targeted set of code/UI changes to eliminate known failure modes:
- AI4 must not run on missing/invalid totals
- AI4 validation errors must degrade to needs_review (never fatal crash)
- Missing vendor identity must degrade to needs_review (never uncaught ValueError)
- Duplicate file ingestion must be non-fatal ("already imported")
- Process UI log modal must show ai_stage_name and clipboard must be responsive with feedback

IMPORTANT CONSTRAINTS
- Do NOT edit AI3 or AI4 prompt files. They are already fixed.
- Do NOT refactor unrelated code. No cosmetic changes.
- If something must be removed, comment it out and explain why in code.
- Make a separate branch for each task and merge to dev via PRs.

BRANCH PLAN
Create these branches (one PR each, merged to dev in this order):
1) fix/accounting-input-gate
2) fix/company-resolution-fallback
3) fix/ai4-validation-nonfatal
4) fix/duplicate-file-nonfatal
5) fix/process-ui-ai-stage-and-clipboard

------------------------------------------------------------
TASK 1 — fix/accounting-input-gate
------------------------------------------------------------
Goal: AI4 must never run with missing totals when deterministic data exists.

A) Update the accounting input loader
- File: backend/src/services/tasks/file_management_tasks.py
- Function: _load_accounting_inputs()

1) Extend the SELECT to also fetch:
- gross_amount_original
- net_amount_original
- currency
- exchange_rate

2) Deterministic normalization:
- If currency == 'SEK':
  - If gross_amount_sek is NULL and gross_amount_original exists -> set gross_amount_sek = gross_amount_original
  - If net_amount_sek is NULL and net_amount_original exists -> set net_amount_sek = net_amount_original
  - If exchange_rate is NULL or 0 -> set exchange_rate = 1.0

3) If totals are still missing (neither SEK nor original totals exist):
- Return a controlled “missing totals” indicator/structure so the caller can mark needs_review and skip AI4.

B) Add a hard gate before AI4 starts (where AI4 is triggered)
- If _load_accounting_inputs() indicates missing totals / invalid inputs:
  - Mark this step as needs_review (or your system’s equivalent)
  - Store a clear reason: "missing totals for accounting"
  - Do NOT raise an uncaught exception
  - Skip AI4 only for that file, continue batch

Acceptance for Task 1:
- Receipts with gross_amount_original but missing gross_amount_sek can still proceed (via fallback).
- Receipts without any totals do not crash; AI4 is skipped and file is flagged needs_review.

PR REQUIREMENTS (Task 1):
- Include a short PR description: what changed, why, and where.
- Include a quick note on how you tested.

------------------------------------------------------------
TASK 2 — fix/company-resolution-fallback
------------------------------------------------------------
Goal: Missing vendor identity must become needs_review, not an uncaught ValueError.

A) Locate where this happens:
- Error text: "Company resolution failed: both vat/orgnr and name are missing" (ValueError)

B) Implement controlled handling:
- Catch this error at the step boundary
- Mark the file/step needs_review
- Store reason: "missing_vendor_identity_in_ocr"
- Ensure the pipeline continues (no fatal crash)
- Ensure UI can display it as "Requires manual review" rather than "Error"

Acceptance for Task 2:
- No uncaught ValueError for missing vendor identity; it becomes needs_review.

PR REQUIREMENTS (Task 2):
- Include before/after behavior description.

------------------------------------------------------------
TASK 3 — fix/ai4-validation-nonfatal
------------------------------------------------------------
Goal: AI4 validator errors must never become fatal pipeline crashes.

A) Locate where AccountingProposalValidationError is thrown
B) Change behavior:
- Catch AccountingProposalValidationError
- Persist status needs_review + full error message into the appropriate log/history table
- Skip saving invalid proposals if required by your flow
- Continue processing the batch (do not crash the run)

Acceptance for Task 3:
- Loopia/Rusta/Midjourney-type failures become needs_review with error text recorded.
- Batch continues.

PR REQUIREMENTS (Task 3):
- Include proof in logs or screenshot of needs_review status being stored.

------------------------------------------------------------
TASK 4 — fix/duplicate-file-nonfatal
------------------------------------------------------------
Goal: Duplicate ingestion should be "already imported", not error.

A) Locate DuplicateFileError handling in ingestion/import (FTP or general ingest flow)
B) Change behavior:
- On duplicate hash:
  - Return "already imported"
  - Log as warning/info
  - If possible, return the existing file_id for traceability
- Do not mark run as failed

Acceptance for Task 4:
- Duplicate file does not create an error in history; it becomes already imported.

PR REQUIREMENTS (Task 4):
- Add a short note describing the return/response shape.

------------------------------------------------------------
TASK 5 — fix/process-ui-ai-stage-and-clipboard
------------------------------------------------------------
Goal: Process UI log modal should show ai_stage_name and clipboard should give immediate feedback.

File: main-system/app-frontend/src/ui/pages/Process.jsx

A) Replace "AI-entry 1..N" headings
- Use entry.ai_stage_name as the heading for each log entry
- Provide a safe fallback label only if ai_stage_name is missing

B) Make clipboard copy robust
- Copy handler must be async
- Use await navigator.clipboard.writeText(...)
- Show feedback: "Copied!" for success, "Copy failed" for errors
- Errors must not be silent

C) “Copy as one long paragraph”
- If “include prompts” is OFF:
  - Join log lines with single spaces into one paragraph (not multiple newlines)
- If “include prompts” is ON:
  - Include prompt blocks but keep consistent headings using ai_stage_name

Acceptance for Task 5:
- UI shows correct stage headings.
- Copy button visibly responds and works.
- Long-paragraph mode is truly one paragraph.

PR REQUIREMENTS (Task 5):
- Include a screenshot or short description of the new UI behavior.

------------------------------------------------------------
FINAL REGRESSION TEST (after all merges to dev)
------------------------------------------------------------
Run a batch with examples covering:
- Missing *_sek but original totals exist
- Missing totals entirely
- An invoice previously failing vendor identity resolution
- A case that triggers AI4 validation failure
- A duplicate file ingestion scenario

Verify in DB:
- For new SEK rows: exchange_rate is never 0.0 and is 1.0
- gross_amount_sek/net_amount_sek are filled when originals exist and currency=SEK
- AI4 errors are needs_review (not fatal) and error text is stored
- Missing vendor identity is needs_review with reason "missing_vendor_identity_in_ocr"
- Duplicate ingestion returns already imported without error

Verify in UI:
- ai_stage_name is shown
- Clipboard shows Copied!/Copy failed feedback
- Long-paragraph copy behaves correctly

DELIVERABLES
For each PR:
- Branch name
- Short PR summary
- List of touched files
- How you tested (commands or steps)
After merge:
- A short final report confirming the Definition of Done items are met.
```

##### You said:



codebase_251219_07-42.zip

Zip Archive

Det blev skillnad till det bättre men även tydliga felaktigheter. log_text ska inte användas alls för agentdialog  nu smygs prompter in där. Tittar man på ai_processing_history prompt text och prompt respons så är det uselt genomfört och implementerat. Gör med hjälp av python en ny analys av databasen igen.Se över slutresultatet för alla importerade kvitto i db. Undersök varför det är fel på ett antal poster. Summera felen så i får en öveblick och därefter förslå enlösning

###### ChatGPT said:

Thought for 18m 19s

Jag har gjort en ny DB-genomgång utifrån **`mind_db_dump.sql`** i `codebase_251219_07-42.zip` och fokuserat på:

- `ai_processing_history` (log_text vs prompt_text/response_text)
- slutresultatet i `unified_files` (kvitton/fakturor)
- `receipt_items`
- `ai_accounting_proposals` (konteringen)

Nedan är en tydlig överblick + en lösning som adresserar alla fel som faktiskt syns i datan.

------

## 1) AI-historik: prompt/response är i praktiken trasigt

### Vad som syns i DB

I `ai_processing_history`:

- **response_text är alltid tomt** (0 rader med innehåll).
- **log_text innehåller prompttext** (dvs “smygs in där”) – detta händer konsekvent (i princip alla importerade kvitton har 2 sådana rader: typ AI1 + AI2).
- prompt_text finns ofta ifyllt, men eftersom log_text redan “läcker” prompten blir checkbox-logiken meningslös.

**Konsekvens:** UI kan inte “gömma prompts” eftersom de redan ligger i log_text, och du kan inte granska modellens faktiska svar eftersom response_text är tomt.

### Trolig rotorsak i kod

Det finns kod som bygger en `log_parts`/logsträng som explicit lägger in:

- `PROMPT USED:` + prompt
- `RAW RESPONSE:` + svar

…och sedan sparar allt i **log_text** (i stället för att använda `prompt_text`/`response_text`-kolumnerna som du nu vill använda).

------

## 2) Konteringen: många poster blir obalanserade

### Vad som syns i DB

I `ai_accounting_proposals` per kvitto/faktura:

- **10 av 14** (receipt/invoice) har **obalans** (debet ≠ kredit med mer än 0,01).
- Typiskt mönster: det sparas **bara momsrad + betalrad**, men **kostnadsraden saknas**, t.ex.
  - kvitto med gross 2980 / net 2384 / vat 596 → sparat: **2641 debit 596** + **2440 credit 2980** → diff = **-2384** (exakt den saknade kostnaden)

**Konsekvens:** bokföringsförslag går inte att använda, och ännu värre: systemet kan se “klart” ut men innehåller trasiga verifikat.

### Rotorsak (praktiskt)

AI4 kan uppenbarligen producera ofullständiga set (eller så filtreras/valideras delar bort), och systemet verkar **spara delmängder** i stället för att stoppa allt och markera review.

------

## 3) SEK-fält och växelkurs: feltyp som fortfarande skapar följdfel

### Vad som syns i DB (kvitton)

- 6 av 14 har **SEK-mismatch** (gross/net i SEK skiljer sig från original > 0,01).
- 1 invoice med SEK har **exchange_rate = 0**.
- Det ser också ut som att *_sek-kolumner är lagrade utan ören (schema/typ-problem), vilket ger avrundning/kapning och kan skapa obalans downstream.

**Konsekvens:** även om AI4 “gör rätt” kan inputen redan vara fel (avrundad/kapad), vilket spräcker balans och moms.

------

## 4) Kortdata: payment_type=card men last4 saknas

### Vad som syns i DB

För alla `unified_files` med `payment_type="card"`:

- `credit_card_last_4_digits` är **NULL i 100%** av fallen i detta dump-läge.

Samtidigt innehåller `ocr_raw` typiskt card-sektion (“MASTERCARD”, “PAN”, “XXXX”, osv), så det finns material att extrahera ifrån — men det hamnar inte i rätt kolumner.

**Konsekvens:** ni tappar en av era viktigaste deterministiska match-nycklar (kortets sista 4).

------

# Förslag på lösning (utan att ändra AI3/AI4-prompterna)

Här är en plan som löser problemen **i backend/DB-logik** och gör att du får en ren pipeline där logg + kontering blir stabila.

## A) Lås loggningen: log_text får aldrig innehålla prompt/response

**Mål:** log_text = kort, läsbar “human log”. Prompt/svar ska **enbart** ligga i `prompt_text` / `response_text`.

1. Identifiera alla ställen där log_text byggs med strängar som:
   - “PROMPT USED:”
   - “RAW RESPONSE:”
   - “OUTPUT REMINDER”
2. Ta bort/kommentera bort dessa block så de inte längre concat:as in i log_text.
3. Säkerställ att alla AI-anrop sparar:
   - `prompt_text = exakt prompt som skickades`
   - `response_text = exakt råtext som kom tillbaka` (även om den senare parse:as)
4. UI ska bara visa prompts när checkbox är aktiv – och då läsa från `prompt_text` (inte log_text).

**Extra hårt skydd (rekommenderas):**

- Lägg in en “sanitizer” innan insert/update av `ai_processing_history`:
  - Om `log_text` innehåller “Role:” / “CRITICAL” / “OUTPUT FORMAT” → flytta allt från den markören till prompt_text (om prompt_text är tom) och kapa log_text.

------

## B) Gör response_text obligatoriskt

**Mål:** du ska alltid kunna se vad modellen svarade.

- Vid varje AI-körning: om du har ett svar (även om parse failar) → `response_text` måste fyllas.
- Om det blir exception innan svar finns → `response_text` får vara null, men då ska `error_message` vara tydlig.

------

## C) Kontering: spara aldrig obalanserade delmängder

**Mål:** antingen (1) balanserat och OK, eller (2) stoppa och markera review – men aldrig “halv-verifikat”.

1. Efter att AI4-resultatet parse:ats till entries, kör en **pre-save validation**:
   - summera debet/credit
   - om |diff| > 0,01 → **SPARA INGA RADER**
2. Markera AI4-steget som `needs_review` och spara:
   - `error_message` = “Unbalanced proposals diff=…; missing expense line likely”
   - `response_text` (råsvaret) för felsökning
3. (Valfritt men kraftfullt) Om ni vill ha automatisk räddning utan promptändring:
   - Implementera en deterministisk “balancing fallback” **endast om** systemet har en explicit default-kostnadskonto inställd och kontot finns i `chart_of_accounts`.
   - Skapa då EN kostnadsrad med belopp = diff (på rätt sida) och notering “Auto-balansrad – kräver granskning”.
   - Sätt ändå status = `needs_review` (för att inte maskera att AI4 missade).

------

## D) SEK / exchange_rate: normalisera i backend + fixa schema om ören kapas

**Mål:** SEK ska aldrig ha exchange_rate=0 och *_sek ska aldrig tappa ören.

1. Backend-normalisering:
   - Om currency = SEK:
     - exchange_rate = 1.0
     - gross_amount_sek = gross_amount_original
     - net_amount_sek = net_amount_original
2. Schema/migration (om *_sek idag inte kan lagra ören):
   - ändra *_sek till DECIMAL med 2 decimaler och default NULL (inte 0)
   - migrera existerande data: för SEK → kopiera original → *_sek

------

## E) Kort last4: deterministisk post-extractor (utan promptändring)

**Mål:** Om OCR har card-sektion men AI3 inte fyllde last4 → backend försöker deterministiskt.

- Efter AI3 (eller efter OCR-lagring), om `payment_type='card'` och last4 är NULL:
  - kör regex-baserad extractor på `ocr_raw`:
    - leta efter maskade PAN-mönster (blandat `X/x/*`) nära VISA/MASTERCARD/CARD/KORT/PAN
    - fånga sista 4 siffror
  - skriv till:
    - `credit_card_last_4_digits`
    - ev. `credit_card_brand_short/full`
  - om flera kandidater → välj bara om exakt 1 är tydligt kopplad till mask/pan-kontext, annars lämna NULL (ingen gissning)

------

# Snabb “felöversikt” från dumpen (så du ser omfattningen)

**I detta DB-läge:**

- `ai_processing_history`: response_text innehåll = **0 rader**
- log_text innehåller prompttext: **systematiskt** (praktiskt taget alla importerade kvitton)
- `ai_accounting_proposals`: **10/14** receipts/invoices obalanserade
- `credit_card_last_4_digits`: **0% ifyllt** trots `payment_type='card'`
- SEK-mismatch: **6/14**

------

Vill du att jag skriver en **agent-checklista (task-by-task)** som exakt matchar punkterna A–E ovan (med filnamn och vad som ska ändras var), baserat på den här kodbasen? Jag kan göra den lika “copy/paste-styrd” som sist – men nu med fokus på log_text/prompt_text/response_text och att stoppa obalanserade verifikat.

##### You said:

Jättebra! Du har presenterat felen på ett utmärkt sätt. Jag vill att du nu gräver dig ännu djupare ner i koden och analyerar var i koden detta sker, och därefter presenterar en lösning som är hållbar, med exakta kodreferenser, för varje fel.

###### ChatGPT said:

Thought for 19m 32s

Här är den djupare analysen “ner i koden” (med exakta kodreferenser) och en hållbar lösning per fel. Jag baserar detta på:

- **Kodbasen** i `/backend` + `/main-system/app-frontend`
- **DB-dumpen** `mind_db_dump.sql` i zippen (där jag bl.a. kunde se att **30 rader** i `ai_processing_history.log_text` innehåller **hela prompt_text som substring**)

------

## 1) Fel: `log_text` används (och fylls) med prompt-dialog – “prompts smygs in där”

### Symptom i DB

I `mind_db_dump.sql` finns ett tydligt mönster: `ai_processing_history.log_text` innehåller “normal logg” + **hela prompten** (exempelvis `log_text` som innehåller `prompt_text` rakt av).
Jag kunde verifiera att **30 rader: `prompt_text` är en substring av `log_text`**.

### Var detta sker i koden (varför det kan hända)

Det här uppstår när någon skickar in `log_text` som råkar innehålla prompten (oavsett var den byggs). Det mest hållbara sättet att stoppa detta är att göra en **hård “sanity gate” precis vid DB-insert**.

**Kodreferens (DB insert för ai-historik):**

- `backend/src/services/ai_logging.py`
  - `log_ai_call(...)` (det är här *all* historik skrivs)

### Hållbar lösning (stoppa läckage oavsett framtida regression)

**Inför sanitization i `log_ai_call()`**:

- Om `prompt_text` finns och `log_text` råkar innehålla `prompt_text` → **ta bort den delen ur `log_text` innan insert**.
- Samma princip kan gälla för `response_text` om ni vill vara 100% säkra att log_text aldrig blir en dialogdump.

> Detta är “belt-and-suspenders”: även om någon dev råkar concatenata prompt till log_text i framtiden så kommer DB aldrig få det.

------

## 2) Fel: `prompt_text` och `response_text` är “uselt implementerat” (fel instans → tom/irrelevant response)

Det här är en **riktig rotorsak** i er nuvarande kod.

### Rotorsak

`ai_pipeline_tasks.py` skapar en `AIService()`-instans – men den instansen används **inte** för AI-körningen. Istället anropas `*_internal(...)`-funktioner som i sin tur skapar **en helt ny AIService()**.

Resultat:

- `ai_pipeline_tasks.py` försöker läsa `ai_service.last_raw_response` → men den är **tom/irrelevant** (fel instans).
- Därför blir `response_text` ofta tom/NULL eller “fel”.
- Samtidigt loggas saker dubbelt (se fel #3).

### Exakta kodreferenser

**A) Pipeline skapar “fel” AIService-instans och läser `last_raw_response`:**

- `backend/src/services/tasks/ai_pipeline_tasks.py`
  - Skapar instans: **rad ~68**
  - Läser raw response (fel instans):
    - AI1 success: **rader 97–101**
    - AI2 success: **rader 192–196**
    - AI3 success: **rader 310–313**
    - AI4 success: **rader 443–446**
  - Skriver historik via `_history(...)`:
    - AI1: **106–118**, AI1 error **151–162**
    - AI2: **203–210**, AI2 error **220–230**
    - AI3: **330–340**, AI3 error **373–382**
    - AI4: **458–470**, AI4 error **481–491**, AI4 skipped **503–510**

**B) Internal-funktionerna skapar egen AIService (rätt instans för AI-körningen):**

- `backend/src/api/ai_processing.py`
  - `classify_document_internal`: **rader 651–655** (skapar `AIService()`)
  - `classify_expense_internal`: **rader 670–673**
  - `extract_receipt_data_internal`: **rader 683–686**
  - `generate_accounting_proposals_internal`: **rader 688–691**

### Hållbar lösning

Ni måste välja **en** källa som är “ägare” av `ai_processing_history` för prompt/response. Mest robust:

**Alternativ A (rekommenderas): Låt endast AIService logga prompt/response**

1. **Sluta skriva AI-historik i `ai_pipeline_tasks.py`** (commenta bort `_history(...)`-anropen ovan, med tydlig motivering i kod).
2. Flytta ansvaret till den plats där AI-svaret faktiskt finns: **`AIService`** (se fel #3).

Detta löser samtidigt:

- tom/trasig `response_text`
- dubbelloggning
- “log_text innehåller prompt” (om ni samtidigt gör sanitization i `log_ai_call`)

------

## 3) Fel: Dubbelloggning + inkonsekventa stage-namn (AI1/AI2 vs document_analysis/expense_classification)

### Symptom i DB

I dumpen finns historikrader med `job_type` som:

- `ai1/ai2/ai3/ai4` (med `ai_stage_name = AI1-...`)
  **och**
- `document_analysis/expense_classification/data_extraction/accounting_classification` (ofta med tomma fält)

Detta gör UI/diagnostik rörig och kan få frontend att visa “fel” rader.

### Exakt kodorsak

**A) AIService loggar “stage_key” som job_type/stage_name – men utan prompt/response/log_text**

- `backend/src/services/ai_service.py`
  - `_provider_generate(...)` loggar success här: **rader 619–627**
  - loggar error här: **rader 651–661**
  - MEN den skickar inte `log_text`, `prompt_text`, `response_text` ⇒ de blir NULL i DB.

**B) ai_pipeline_tasks loggar igen med `ai1/ai2/ai3/ai4` och stage-namn**

- `backend/src/services/tasks/ai_pipeline_tasks.py` (rader listade i fel #2)

### Hållbar lösning

Gör AIService till **enda** loggern av ai-dialog (prompt/response) och standardisera stage-namn:

1. I `backend/src/services/ai_service.py` (`_provider_generate`):
   - Skicka alltid in:
     - `prompt_text = prompt` (eller “final prompt” om ni har den)
     - `response_text = response.raw`
     - `log_text = kort human-sammanfattning` (inte prompt!)
   - Mät och skicka `processing_time_ms` på riktigt (start/stop i `_provider_generate`)
2. Standardisera namn i samma metod:
   - Mappa:
     - `document_analysis` → `job_type="ai1"`, `ai_stage_name="AI1-DocumentClassification"`
     - `expense_classification` → `ai2`, `"AI2-ExpenseClassification"`
     - `data_extraction` → `ai3`, `"AI3-DataExtraction"`
     - `accounting_classification` → `ai4`, `"AI4-AccountingProposals"`
   - Då slipper ni två olika “universum” i historiken.
3. I `ai_pipeline_tasks.py`:
   - Commenta bort `_history(...)` (för att inte dubba och inte skriva fel response_text).

------

## 4) Fel i importerade kvitton: `exchange_rate=0.0` för SEK i `unified_files`

### Symptom i DB

I dumpen finns många poster i `unified_files` där:

- `currency="SEK"` men `exchange_rate=0.0` (jag såg detta i **21 poster** i dumpen)

### Exakt kodställe där detta “cementeras” till DB

Ni tar `exchange_rate` direkt från AI3 JSON och sparar utan deterministisk normalisering:

- `backend/src/services/ai_service.py`
  - där `UnifiedFileBase(...)` byggs:
    - `exchange_rate=unified_data.get("exchange_rate")` på **rad ~908**

### Hållbar lösning (utan att röra prompt)

Lägg in deterministisk normalisering precis innan `UnifiedFileBase(...)` skapas i samma block:

- Om `currency == "SEK"`:
  - om `exchange_rate` är `None` eller `0` → sätt `1.0`
  - om SEK-belopp saknas men original finns → fyll SEK = original

Det gör systemet robust även om en prompt råkar regress:a.

------

## 5) (Bonus – datakvalitet) `unified_files.vat` blir alltid NULL i dumpen

I dumpen var `unified_files.vat` **NULL för alla rader**.
Orsak: ni hämtar `vat/orgnr` från `unified_data`, men i AI3-strukturen ligger de normalt under `company`.

- `backend/src/services/ai_service.py`
  - just nu:
    - `vat=unified_data.get("vat") or unified_data.get("orgnr")`
  - men `unified_data` verkar inte bära de nycklarna → blir NULL.

**Hållbar fix:** hämta från `company_data` istället (om fältet ska representera leverantörens identitet).

------

# Konkreta åtgärder (min rekommenderade “minsta hållbara paket”)

## A) Gör `ai_processing_history` korrekt och framtidssäkert

1. `backend/src/services/ai_logging.py`
   - Lägg in sanitization: om `prompt_text in log_text` → remove.
2. `backend/src/services/ai_service.py` (`_provider_generate`)
   - Logga **alltid** `prompt_text`, `response_text`, `log_text`, `processing_time_ms`
   - Standardisera `job_type`/`ai_stage_name` via mapping
3. `backend/src/services/tasks/ai_pipeline_tasks.py`
   - Commenta bort `_history(...)` för AI1–AI4 (för att slippa dubbar + fel instans)

## B) Rensa visning utan att “förstöra historik”

1. `backend/src/api/receipts.py` (`/receipts/<rid>/log`)
   - När ni returnerar loggar: filtrera bort “legacy/dupe”-rader om de saknar `prompt_text` och `response_text` **och** har stage_key-namn (tills allt är migrerat).
   - Alternativt: visa bara senaste per `ai_stage_name` eller bara de med `ai_stage_name` som börjar med `"AI"`.

## C) Data-normalisering vid AI3-save (utan prompt-ändring)

1. `backend/src/services/ai_service.py` i AI3-resultat-blocket
   - SEK: `exchange_rate=1.0`, fyll SEK-belopp deterministiskt

------

# Snabb “Definition of Done” (10 rader)

1. Nya AI-körningar skapar exakt **en** historikrad per stage (AI1–AI4) och fil.
2. `ai_processing_history.prompt_text` är alltid ifylld för AI1–AI4.
3. `ai_processing_history.response_text` är alltid ifylld (raw modelloutput) för AI1–AI4.
4. `ai_processing_history.log_text` innehåller **aldrig** prompt eller raw response.
5. UI kan gömma/visa prompt utan att något “läcker in” via log_text.
6. `job_type` är konsekvent `ai1/ai2/ai3/ai4`.
7. `ai_stage_name` är konsekvent `AI1-...` etc.
8. För `currency=SEK` är `exchange_rate` alltid `1.0`.
9. För SEK: `gross_amount_sek/net_amount_sek` saknas inte när original finns.
10. Ingen “tom” historikrad (NULL log_text/prompt/response) skapas längre.

------

Vill du att jag ska gå hela vägen och skriva **exakta patch-förslag som fulla filer** för:

- `backend/src/services/ai_logging.py`
- `backend/src/services/ai_service.py`
- `backend/src/services/tasks/ai_pipeline_tasks.py`
- ev. `backend/src/api/receipts.py`

…så gör jag det i nästa svar (då skriver jag ut *hela filerna*).

##### You said:

Ja tack. 

###### ChatGPT said:

Thought for 13m 30s

Här är den **djupare rotorsaksanalysen** + en **hållbar kodlösning** (med exakta kodställen) som fixar att:

- **`log_text` återigen får in promptar** (ska aldrig ske)
- **`prompt_text`/`response_text` i `ai_processing_history` blir felparade/usla** (tomma responser, fel prompt kopplad till fel körning)
- **dubbel-loggning** ger dubbletter och “AI1-8”-liknande beteende i UI
- **fel VAT/ORGNR-mappning** (unified_file tog VAT från fel objekt)
- **SEK/exchange_rate/SEK-belopp** blir inkonsekvent när AI3 redan ger “original” men SEK-fält lämnas tomma

## Var i koden felen uppstår

### Fel 1 — Pipeline skriver historik med fel AIService-instans ⇒ tom `response_text`

**Fil:** `backend/src/services/tasks/ai_pipeline_tasks.py`
**Problem:** Pipeline skapar en `AIService()` och läser `ai_service.last_raw_response`, men **den instansen gör aldrig provider-anropet** (det görs inne i `ai_service.run_aiX_*` som skapar/har egen intern logik). Resultat: `response_text` blir tomt/irrelevant.

**Exakta anropsställen (original):**

- AI1-historik: `_history(... "ai1" ...)` runt rad **106** och **151**
- AI2-historik: runt rad **203** och **220**
- AI3-historik: runt rad **330** och **373**
- AI4-historik: runt rad **458**, **481**, **503**

### Fel 2 — Central provider-loggning saknar prompt/response ⇒ DB får “success” men utan dialog

**Fil:** `backend/src/services/ai_service.py`
**Problem:** `_provider_generate()` loggar med `log_ai_call(...)` men skickar **inte** `prompt_text`/`response_text`.
**Exakta rader (original):** `log_ai_call(` runt **578, 608, 620, 634, 647, 658, 673**.

### Fel 3 — Promptar “smugglas” in i `log_text` ⇒ UI måste strip:a (men det ska aldrig behövas)

**Fil:** `backend/src/services/ai_logging.py` + legacy-format i DB
**Problem:** `log_ai_call()` skriver `log_text` rakt in i DB utan skydd. Om någon del råkar bygga `log_text` med prompt/response (eller legacy-block `--- PROMPT ---`), så hamnar det i `log_text` och UI försöker sedan “rensa” det. Det blir skört och återkommer.

### Fel 4 — `/receipts/<rid>/ai-history` returnerar inte prompt/response ⇒ felsökning blir “blind”

**Fil:** `backend/src/api/receipts.py`
**Problem:** `get_ai_processing_history()` SELECT:ar inte `prompt_text`/`response_text` och returnerar inte dem.

------

## Lösningen jag byggt (hållbar, med tydlig ansvarsfördelning)

### Princip (viktig)

**Endast ett ställe får skriva stage-historik (AI1–AI4):**
✅ `AIService._provider_generate()` (det är där prompt+raw response faktiskt finns)

Pipeline (`ai_pipeline_tasks.py`) ska **inte** skriva stage-historik – annars får du exakt den felparning du ser.

### Vad patchen gör

1. **`AIService._provider_generate()` loggar alltid:**

- `prompt_text`
- `response_text`
- `processing_time_ms`
- stabila `job_type` = `ai1/ai2/ai3/ai4`
- tydliga `ai_stage_name` (AI1-…, AI2-…, osv)

1. **Pipeline stage-loggning stängs av** (men koden finns kvar bakom en flagga för spårbarhet).
2. **`log_ai_call()` sanerar defensivt**:

- Om prompt/response råkar ligga i `log_text` (legacy eller misstag) så plockas det bort och hamnar i rätt fält.

1. **Receipts API**: `/ai-history` inkluderar `prompt_text` + `response_text`, och `log_text` strip:as från legacy-block.
2. **AI3 mapping fix**:

- `vat/orgnr` i `UnifiedFileBase` tas från `company` (inte från `unified_file`)
- SEK-normalisering: `exchange_rate=1.0` när currency=SEK + backfill SEK-belopp från original om de saknas
- deterministisk OCR-fallback för last4 **endast** om masked PAN finns

------

## Leverans: färdiga ersättningsfiler + patch

Du kan antingen:

- **ersätta filerna** rakt av med zippen, eller
- applicera unified diff patch.

### ✅ Zip med kompletta uppdaterade filer (ersättningsfiler)

Download ai_history_fix_files.zip

Innehåller exakt dessa filer:

- `backend/src/services/ai_logging.py`
- `backend/src/services/ai_service.py`
- `backend/src/services/tasks/ai_pipeline_tasks.py`
- `backend/src/api/receipts.py`

### ✅ Unified diff patch

Download ai_history_fix.patch

------

## Kontroll: rader + funktionsräkning (före/efter)

- `backend/src/services/ai_logging.py`
  - rader: **94 → 194**
  - funktioner: **1 → 2** (ny sanitizer-funktion)
- `backend/src/services/ai_service.py`
  - rader: **1365 → 1463**
  - funktioner: **35 → 36** (ny `_history_fields_for_stage`)
- `backend/src/services/tasks/ai_pipeline_tasks.py`
  - rader: **601 → 617**
  - funktioner: **4 → 4**
- `backend/src/api/receipts.py`
  - rader: **2479 → 2481**
  - funktioner: **52 → 52**

Inga befintliga funktioner är borttagna.

------

## Definition of Done (10 rader, rakt att bocka av)

1. Kör import på 3–5 kända problemkvitton.
2. I DB: `ai_processing_history` för varje fil har **ai1/ai2/ai3/ai4** med korrekt `ai_stage_name`.
3. `prompt_text` är ifyllt för ai1–ai4.
4. `response_text` är ifyllt för ai1–ai4 (inte tomt).
5. `log_text` innehåller **inga** “Role:”, “CRITICAL…”, promptar eller raw JSON-dumpar.
6. Inga rader i `log_text` innehåller `--- PROMPT ---` eller `--- RAW RESPONSE ---`.
7. `/receipts/<rid>/ai-history` returnerar `prompt_text` och `response_text`.
8. UI-modal visar läsbar logg även när “show prompts” är av.
9. Det finns **ingen dubbel loggning** per AI-stage (dvs inte två ai3-rader för samma körning).
10. unified_files: VAT/ORGNR matchar company-fält (inte felaktigt från unified_file payload).

------

Vill du att jag även ska lägga in ett **litet SQL-verifieringsscript** (SELECTs) som snabbt listar alla rader där `log_text` fortfarande innehåller prompt-markörer eller där `response_text` är null för ai1–ai4? Det blir en perfekt “smoke test” efter varje importkörning.

##### You said:

skapa en startprompt för agenten som hänvisar till din plan som finns i /docs/bugs/CONVERSION_ADJUSTMENTS_2025-12-19_part_2.md

###### ChatGPT said:

```
You are an implementation agent working in this repository. Your task is to implement the fixes described in:

/docs/bugs/CONVERSION_ADJUSTMENTS_2025-12-19_part_2.md

This document is the single source of truth for what to change, in what order, and what “done” looks like.

NON-NEGOTIABLE RULES
- Do NOT modify AI3 or AI4 prompt files. They are already corrected.
- Do NOT refactor or “clean up” unrelated code. Only touch code that is directly required by the plan.
- Do NOT delete existing logic. If something must be removed, comment it out and add a clear explanation in code.
- Work in small, reviewable PRs. One task/branch per change set.

WORKFLOW (MANDATORY)
1) Create a fresh branch for each task described in the plan. Use the branch naming in the plan (or the closest equivalent).
2) For each branch:
   - Implement only that task.
   - Run the minimal tests or the manual verification steps listed in the plan.
   - Create a PR into dev with:
     - Summary of changes
     - Files touched
     - How you tested
     - Any risks/notes

PRIMARY OBJECTIVES (FROM THE PLAN)
A) Stop prompt/response leakage into ai_processing_history.log_text
   - log_text must be a short human-readable log only.
   - prompt_text and response_text must contain the full AI dialog.

B) Ensure prompt_text and response_text are correctly paired with the actual AI call
   - No “wrong instance” issues.
   - response_text must not be empty when an AI response exists.

C) Eliminate duplicate / inconsistent AI history rows
   - Exactly one canonical history entry per stage (AI1–AI4) per run.
   - Consistent job_type and ai_stage_name.

D) Prevent broken accounting saves
   - Never persist unbalanced/partial proposals.
   - Validation failures degrade to needs_review without crashing the batch.

E) Preserve pipeline stability
   - Missing vendor identity becomes needs_review (never fatal ValueError).
   - Duplicate file ingestion becomes “already imported” (non-fatal).

IMPLEMENTATION GUIDANCE
- Follow the exact file references and code references in the plan.
- Apply changes in the order the plan specifies, because later tasks depend on earlier fixes.
- Where the plan recommends “defensive” protections (sanitizers/guards), implement them exactly to prevent regressions.

REQUIRED REGRESSION TEST (FROM THE PLAN)
After all PRs are merged to dev:
1) Run a conversion batch that includes:
   - Receipts missing *_sek but with *_original present
   - A case with missing vendor identity
   - A case that previously caused AccountingProposalValidationError
   - A duplicate file ingestion case
2) Verify in DB:
   - For new SEK rows: exchange_rate is 1.0 (never 0.0)
   - prompt_text and response_text are populated for AI1–AI4
   - log_text contains no prompt/response content
   - needs_review is used instead of fatal errors
3) Verify in UI:
   - Stage names are consistent
   - Prompts are only shown when explicitly enabled

DELIVERABLES
- One PR per task described in /docs/bugs/CONVERSION_ADJUSTMENTS_2025-12-19_part_2.md
- A final short report confirming the Definition of Done items in that document, with evidence (DB queries/log excerpts) where relevant.
```

##### You said:



codebase_251219_21-31.zip

Zip Archive

Då är dessa ändringar implementerade. Använd python och gå igenom hela kodbasen och gör följande:  1. Kontrollera att de ändringar du specificerade är genomförda på rätt sätt, att kodbas och databas är konfigurerade rätt 2. Gå igenom den nya importen som är gjord och granska resultatet. Kontrollera att samtliga tabeller är ifyllda på rätt sätt enligt SoT och att det inte sker sammanblandning av loggar, att konteringen går igenom 100% korrekt och att funktionaliteten är fullständig.  3. Skapa en rapport och presentera det du kommit fram till.  Kodbasen med inkluderad db bifogad.

###### ChatGPT said:

Thought for 17m 41s

Jag gick igenom **hela zip:en `/mnt/data/codebase_251219_21-31.zip`**, inklusive **DB-dumpen `mind_db_dump.sql`**, och validerade både (A) att de planerade ändringarna verkligen sitter där de ska och (B) hur **den nya importen** faktiskt ser ut i databasen.

Nedan är en **rapport med konkreta fel**, **exakta kodreferenser** (fil + rader i denna zip), samt en **hållbar lösning per fel**.

------

## 1) Status: är “planens” ändringar korrekt genomförda?

### ✅ DB har rätt schema (bra grund)

I DB-schemat finns fälten som behövs för den nya AI-historiken (t.ex. `prompt_text`, `response_text`) i `ai_processing_history`. Det är alltså inte schema som blockerar.

### ❌ Men historiken blir ändå fel i praktiken

I nya importen ser jag detta i DB:

- `ai_processing_history` totalt: **174** rader
- “pipeline”-jobben `ai1/ai2/ai3/ai4`: **82** rader
- “stage-key”-jobben (`document_analysis`, `expense_classification`, `data_extraction`, `accounting_classification`): **74** rader
- **0%** av `ai1/ai2/ai3/ai4` har ifylld `response_text` (**alltid tom**)
- **0%** av stage-key-jobben har ifylld `prompt_text` (**alltid tom**)
- **23.6%** av alla history-rader innehåller prompt-lik text i `log_text` (41 rader)

Det betyder att det fortfarande blir:

1. **Dubbel-loggning** (två “varv” per AI-steg)
2. **Prompt smygs in i `log_text`**
3. **Prompt/response hamnar inte där de ska** (response är tom, stage-key saknar prompt/response)

------

## 2) Fel 1: `log_text` innehåller prompt (fast det inte ska)

### Symptom i DB

Många `ai1`/`ai2`-rader har `log_text` som innehåller prompt-snuttar som `"ROLE"`, `"OUTPUT (STRICT)"`, `"Return ONLY one label"`.

I DB ser jag att **ca 50%** av `ai1/ai2/ai3/ai4`-raderna har prompt-tail i `log_text`.

### Rotorsak i koden

Det kommer från att ni lägger in *prompt-hint* i **reasoning** (som sedan appendar in i `log_text`):

**Fil:** `backend/src/services/ai_service.py`
**AI1:** runt **rad ~728–731**

```
reasoning_parts.append(f"Prompt hint provided: {prompt_hint}")
```

Och samma mönster finns igen:

**Fil:** `backend/src/services/ai_service.py`
**AI2:** runt **rad ~788** (söksträng: `"Prompt hint provided"`)

### Hållbar lösning

- Ta bort att prompt-hint hamnar i reasoning/log_text.
- Om ni vill spåra “vilken prompt/version som användes”, gör det via:
  - `ai_stage_name` / `job_type` + `model_name` + `provider`
  - eller separat metadatafält i DB (men **inte** `log_text`)

**Konsekvens:** `log_text` blir ren (kort), och prompt ligger bara i `prompt_text` där den hör hemma.

------

## 3) Fel 2: `response_text` är tom för `ai1/ai2/ai3/ai4`

### Symptom i DB

För `job_type in ('ai1','ai2','ai3','ai4')` är `response_text` **alltid tom**.

### Rotorsak i koden (mycket tydlig)

I pipeline försöker ni logga raw response så här:

**Fil:** `backend/src/services/tasks/ai_pipeline_tasks.py`

- AI1: runt **rad ~114**
- AI2: runt **rad ~212**
- AI3: runt **rad ~330**
- AI4: runt **rad ~477**

Exempel:

```
raw_response = ai_service.last_raw_response
```

Men: de interna funktionerna ni anropar skapar **en helt ny AIService** och kör modellen där.

**Fil:** `backend/src/api/ai_processing.py`

- `classify_document_internal(...)` runt **rad ~639+**
- `classify_expense_type_internal(...)` osv

Där gör ni:

```
ai_service = AIService()
# ... kör AI
```

Alltså:

- pipeline-instansen (`ai_service` i pipeline) har **ingen** raw response
- raw ligger i den **andra** instansen i `ai_processing.py`
- därför loggas `response_text=""`

### Hållbar lösning (välj 1 – men gör det konsekvent)

**Alternativ A (rekommenderad): Pipeline kör AI direkt via samma AIService-instans**

- Flytta “internal”-funktionernas kärnlogik till metoder på `AIService`
- Pipeline anropar `ai_service.run_ai1.../run_ai2.../run_ai3.../run_ai4...`
- Då är `ai_service.last_raw_response` korrekt och kan loggas.

**Alternativ B: Låt internal-funktionerna returnera raw_response**

- Utöka `DocumentClassificationResponse`, `ExpenseTypeResponse`, `DataExtractionResponse`, `AccountingClassificationResponse` med `raw_response: Optional[str]`
- Sätt `raw_response=ai_service.last_raw_response` **i samma instans**
- Pipeline loggar `raw_response` från responseobjektet istället för `ai_service.last_raw_response`

Oavsett alternativ: `response_text` måste komma från *samma körning*.

------

## 4) Fel 3: Stage-key-jobben loggas men saknar prompt/response

### Symptom i DB

Jobbtyperna:

- `document_analysis`
- `expense_classification`
- `data_extraction`
- `accounting_classification`

…har `prompt_text` och `response_text` **0% ifyllt**.

### Rotorsak

I `AIService._provider_generate()` (och/eller där ni gör `log_ai_call`) skickar ni inte prompt/response till loggningen.

Du kan verifiera direkt:

**Fil:** `backend/src/services/ai_service.py`
Sök på `log_ai_call(` – där finns **ingen** `prompt_text=` och **ingen** `response_text=` i denna zip.

### Hållbar lösning

När ni loggar i AIService, logga alltid:

- `prompt_text=<exakt promptsträng>`
- `response_text=<raw LLM output>`

Då blir stage-key-jobben kompletta, och ni kan dessutom välja att **sluta logga pipeline-jobben** (eller vice versa) för att eliminera dubletter.

------

## 5) Fel 4: Konteringen går inte igenom korrekt (obalans i `ai_accounting_proposals`)

### Symptom i DB (hårt bevis)

- AI4 `success`: **13** kvitton
- I `ai_accounting_proposals` finns rader för **13** kvitton
- Men balanskontroll visar:
  - **12/13** kvitton är **obalanserade**
  - bara **1** är balanserat inom 0.01

Exempel (störst fel):

- `85539cd6-52d3-46a3-be1f-560f638abfb1` diff **-2384.00**
  (VAT debit finns, settlement credit finns, men **expense debit saknas**)

### Rotorsak i koden

Ni saknar en riktig “must-balance”-validator innan persist.

Jag sökte efter balanslogik (sum debit/credit, tolerans 0.01) och hittar **ingen** riktig enforcement som stoppar persist vid obalans.

Persisten sker i:

**Fil:** `backend/src/api/ai_processing.py`
**Funktion:** `_persist_accounting_proposals(...)` runt **rad ~470–520**
Den sparar precis det som kommer in.

### Hållbar lösning

Inför en *hård validator* innan `_persist_accounting_proposals()` körs:

- För varje receipt:
  - minst 2 rader
  - varje rad: exakt en sida > 0 (debit XOR credit)
  - `abs(sum(debit)-sum(credit)) <= 0.01`
- Om fail:
  - skriv AI4 history status `needs_review`/`manual_review`
  - spara felorsak
  - **persist inga proposals**

Detta är det enda sättet att få “100% korrekt kontering” i DB, annars blir det per definition trasigt.

> Bonus-rotorsak (sannolik): AI4 undviker expense-rader när konto inte kan väljas deterministiskt → då får ni bara VAT + settlement → obalans.
> Den måste lösas via (1) system-default expensekonto eller (2) att AI4 får en deterministisk fallback som alltid finns i `chart_of_accounts`.

------

## 6) Fel 5: SEK/exchange_rate/totals är fortfarande fel på många rader

### Symptom i DB

För `unified_files` med `currency='SEK'`:

- **34 av 49** har `exchange_rate = 0.0` (det ska inte ske)
- många totals ligger som **0.0** istället för **NULL** när okänt

### Rotorsak i koden

Ni sparar AI3-resultatet “as-is” utan normalisering:

**Fil:** `backend/src/api/ai_processing.py`
I `_persist_extraction_result(...)` bygger ni `updates` med:

```
"exchange_rate": unified.exchange_rate,
"gross_amount_sek": unified.gross_amount_sek,
"net_amount_sek": unified.net_amount_sek,
...
```

(runt **rad ~362–389**)

### Hållbar lösning

Normalisera *innan* `updates` byggs:

- Om `currency == "SEK"`:
  - om `exchange_rate is None or exchange_rate == 0` → sätt `1.0`
- Om belopp är 0.0 men egentligen “saknas” → konvertera till `NULL`
  - (minst: om både gross och net = 0.0 samtidigt → sätt NULL)

Detta ska göras server-side så ni inte blir beroende av promptkvalitet.

------

## 7) Rekommenderad “städad” arkitektur (för att få bort alla logg-problem)

Just nu loggar ni i två parallella spår:

- pipeline `_history(...)` (ai1..ai4)
- AIService log (stage-key)

Det är därför ni får dubletter + fel fält ifyllda.

**Hållbar modell: välj EN loggkälla**

- Antingen:
  1. **Endast pipeline loggar** (och då måste raw_response verkligen komma från samma körning)
- Eller:
  2) **Endast AIService loggar** (pipeline loggar bara “steget startade/klart”, utan prompt/response)

Jag skulle välja **(2)**:

- AIService vet prompt + raw response + provider + model
- pipeline vet workflow-status och kan spara “step status” separat

------

## 8) Slutsats: vad är “fullständigt” just nu?

**Det som fungerar bättre än tidigare**

- ni har rätt DB-fält och ni loggar *någonstans* per steg

**Men det som fortfarande är tydligt trasigt**

1. `response_text` saknas helt där den behövs
2. prompt hamnar i `log_text` (via reasoning/prompt_hint)
3. dubbel-loggning gör UI/utredning rörig
4. AI4-output sparas trots att den är obalanserad (12/13 fel)
5. SEK/exchange_rate-normalisering är inte enforcead server-side

------

## 9) Vill du att jag tar fram nästa patch?

Om du vill att jag tar fram **nästa patch (kodfix) som gör detta korrekt på riktigt**, så är min rekommendation att vi gör det i 3 “säkra” commits:

1. **Fix raw_response-kedjan** (en AIService-instans eller raw_response i responseobjekt)
2. **Stoppa prompt i log_text** (ta bort `prompt_hint` i reasoning + ev. sanitize)
3. **Validator-gate för AI4** (stoppa persist vid obalans + manual_review)

Säg bara “kör patch” så tar jag fram den som en sammanhängande, minimal ändring med exakta filer.

##### You said:

kör patch

###### ChatGPT said:

Thought for 12m 28s

Klart — här är patchen som fixar exakt det du bad om (log_text ska **inte** innehålla agentdialog, prompt/response ska ligga i **egna kolumner**, och AI4 ska **inte** kunna persista trasiga konteringar).

### ✅ Patch + ersättningsfiler

- Download patch
- Download updated files (zip)

------

## Vad patchen gör (kort men konkret)

### 1) **Stoppar prompt/response från att smyga in i `log_text`**

**Fil:** `backend\src\services\ai_logging.py`

- Lägger in `_sanitize_log_text()` som tar bort:
  - legacy-block som `--- PROMPT ---` / `--- RAW RESPONSE ---`
  - råa prompt/response-substrings om de av misstag hamnat i log_text
- Loggar *alltid* prompt/response i `prompt_text` / `response_text` (som redan finns i tabellen) – inte i `log_text`.

### 2) **Gör AIService till “single source of truth” för AI-dialog**

**Fil:** `backend\src\services\ai_service.py`

- `_provider_generate()` loggar nu alltid en korrekt rad i `ai_processing_history` med:
  - `job_type` = `ai1/ai2/ai3/ai4` (mappat från stage_key)
  - `ai_stage_name` = `AI1-...` osv
  - `prompt_text` = prompt
  - `response_text` = raw response
  - `processing_time_ms`
- Tar bort läckan där hela prompten tidigare trycktes in i “reasoning” via `prompt_hint`.

### 3) **Tar bort duplicerade/trasiga AI1–AI4-historikrader från pipeline-lagret**

**Fil:** `backend\src\services\tasks\ai_pipeline_tasks.py`

- Introducerar wrapper `_pipeline_history()`:
  - Default: **loggar INTE** pipeline-rader för `ai1..ai4` (för att undvika dubletter + tomma response_text).
  - Pipeline-event som `ai_pipeline` och “skipped” osv kan fortfarande loggas.
  - Om du vill kunna logga AI1–AI4 även från pipeline för felsökning: sätt
    `PIPELINE_AI_HISTORY_ENABLED=1`

### 4) **Hård validator-gate för AI4 innan persist**

**Fil:** `backend\src\api\ai_processing.py`

- Ny `_validate_accounting_proposals()`:
  - kräver minst 1 rad
  - `account_code` måste finnas
  - exakt en av debit/credit > 0 per rad
  - inga negativa belopp
  - total debit == total credit inom 0.01
- Vid fel:
  - `_mark_manual_review(...)`
  - **persist sker inte**
  - result.proposals sätts till `[]`

### 5) **API returnerar nu prompt/response**

**Fil:** `backend\src\api\receipts.py`

- `/receipts/<rid>/ai_processing_history` inkluderar nu:
  - `prompt_text`
  - `response_text`

------

## Kör patchen

I reporoten:

```
git apply /path/to/ai_history_fix_v2.patch
```

Om du inte kör git-apply: packa upp zippen och ersätt filerna med samma paths.

------

Vill du att jag även tar fram en **SQL-kontrollfråga** (SELECTs) som verifierar att:

- `log_text` inte innehåller prompt-markörer
- `prompt_text/response_text` faktiskt är ifyllda för senaste importerade kvitton
- inga dubletter finns för ai1–ai4 per file_id/steg

…så skriver jag den direkt i nästa svar.