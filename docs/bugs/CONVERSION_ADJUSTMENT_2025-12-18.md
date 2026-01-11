Här kommer checklistan igen, nu med en **Definition of Done** längst ner (utan något om att ändra AI3/AI4-prompter).

---

## 0) Guardrails innan kodändring

1. Skapa en ny branch per task:

* `fix/accounting-input-gate`
* `fix/company-resolution-fallback`
* `fix/duplicate-file-nonfatal`
* `fix/process-ui-ai-stage-and-clipboard`

2. Ändra inget som inte hör till tasken. Om något måste tas bort: **kommentera bort** och skriv en tydlig förklaring i koden.

3. Kör enhetligt format/lint om projektet använder det (ruff/black/eslint) – men undvik formateringsdiffar i filer som inte berörs.

---

## 1) Backend: stoppa AI4 från att köras på trasigt underlag

**Mål:** AI4 ska aldrig få `None`/saknade totals när deterministisk data finns.

### 1.1 Implementera “SEK fallback” i accounting input loader

* Fil: `backend/src/services/tasks/file_management_tasks.py`
* Funktion: `_load_accounting_inputs()`

**Ändring (logik):**

1. Utöka SELECT så att den även hämtar:

* `gross_amount_original`
* `net_amount_original`
* `currency`
* `exchange_rate`

2. Deterministisk normalisering innan AI4 byggs:

* Om `currency == 'SEK'`:

  * om `gross_amount_sek` är NULL och `gross_amount_original` finns → `gross_amount_sek = gross_amount_original`
  * om `net_amount_sek` är NULL och `net_amount_original` finns → `net_amount_sek = net_amount_original`
  * om `exchange_rate` är NULL eller 0 → `exchange_rate = 1.0`

3. Om totals fortfarande saknas (varken SEK eller original finns):

* returnera ett kontrollerat “missing totals”-läge som gör att AI4 **inte körs**.

### 1.2 Hård gate innan AI4-task körs

* Där AI4 triggas (pipeline/task runner):

**Ändring:**

* Om `_load_accounting_inputs()` indikerar “missing totals / invalid accounting input”:

  * markera steget som **needs_review**
  * logga tydlig orsak: `"missing totals for accounting"`
  * avbryt endast AI4 för filen (inte hela batchen)
* Säkerställ att inget okontrollerat exception bubblar ut.

---

## 2) Backend: AI4 validator ska aldrig ge fatal pipeline-crash

**Mål:** validator-problem ska bli review, inte fatal.

### 2.1 Fånga `AccountingProposalValidationError` och degradéra till review

* Där `AccountingProposalValidationError` kastas idag:

**Ändring:**

* fånga exception
* skriv status `needs_review` + feltext till historik/loggtabell
* stoppa bara AI4-steget för filen
* låt resten av batchen fortsätta

---

## 3) Company resolution: inga okontrollerade “company missing”-krascher

**Mål:** saknad vendor-identitet ska bli kontrollerad review.

### 3.1 Fånga “company resolution failed” och markera review

* Där ni idag får:

  * `ValueError: Company resolution failed: both vat/orgnr and name are missing`

**Ändring:**

* fånga detta
* markera fil/steg som `needs_review`
* logga orsak: `"missing_vendor_identity_in_ocr"`
* säkerställ att filen kan visas i UI som “Requires manual review” (inte “Error”).

---

## 4) DuplicateFileError: gör duplicate till icke-fatal

**Mål:** duplicate ska ge “already imported” och inte error.

### 4.1 Fånga DuplicateFileError i ingestion/import

* Där importen (FTP/ingest) sker:

**Ändring:**

* vid duplicate/hash-collision:

  * returnera “already imported”
  * logga som warning/info
  * om möjligt returnera befintligt `file_id` (för UI-spårbarhet)

---

## 5) Frontend: fixa AI-stage-namn + clipboard

**Mål:** loggmodalen ska bli begriplig och clipboard-knapp ska ge direkt respons.

### 5.1 Visa `ai_stage_name` istället för “AI-entry 1..N”

* Fil: `main-system/app-frontend/src/ui/pages/Process.jsx`

**Ändring:**

* använd `entry.ai_stage_name` som rubrik (fallback endast om saknas).

### 5.2 Clipboard: async + feedback + felhantering

* Samma fil

**Ändring:**

* gör handler `async`
* `await navigator.clipboard.writeText(text)`
* visa “Copied!” feedback (knapptext/ikon eller toast)
* catch: visa “Copy failed” feedback (inte silent)

### 5.3 “Klipp ut allt i ett långt stycke”

**Ändring:**

* include prompts AV: normalisera whitespace och join:a med **mellanslag** (ett stycke)
* include prompts PÅ: inkludera prompts men håll konsekvent struktur och rubriker via `ai_stage_name`

---

## 6) Regression-test (utan prompt-ändringar)

1. Kör batch på exempel där ni tidigare sett:

* saknade `*_sek` men original finns
* faktura som gav company resolution fail
* Loopia/Rusta/Midjourney-typ av AI4-valideringsfel
* duplicate-file scenario

2. Verifiera i DB:

* `exchange_rate` för SEK är aldrig 0.0 i nya rader
* `gross_amount_sek`/`net_amount_sek` fylls när original finns och currency=SEK
* AI4 fel blir `needs_review` och stoppar inte batch
* duplicate ger “already imported” utan error

3. Verifiera i UI:

* `ai_stage_name` visas korrekt
* clipboard funkar + feedback
* “långt stycke” blir faktiskt ett enda stycke

---

# Definition of Done

1. **SEK-normalisering fungerar i praktiken**

* För nya processade filer med `currency="SEK"`:

  * `exchange_rate = 1.0` (aldrig 0.0)
  * `gross_amount_sek`/`net_amount_sek` är inte null när motsvarande `*_original` finns.

2. **AI4 körs inte på saknade totals**

* Filer utan totals får AI4-steget markerat som `needs_review` med tydlig orsak.
* Batchen fortsätter utan fatal crash.

3. **AI4-valideringsfel stoppar inte batchen**

* `AccountingProposalValidationError` resulterar i `needs_review` + loggad feltext.
* Ingen “Fatal error” som stoppar hela körningen.

4. **Company resolution kraschar inte**

* “missing vendor identity” blir `needs_review` med orsak `"missing_vendor_identity_in_ocr"`.
* Inga okontrollerade `ValueError` bubblar ut.

5. **Duplicate import är icke-fatal**

* DuplicateFileError blir “already imported” (warning/info), inte error.

6. **Process UI är läsbart och responsivt**

* Loggmodal använder `ai_stage_name` (inte “AI-entry 1..N”).
* Clipboard-knapp ger “Copied!” eller “Copy failed”.
* “Klipp ut allt som ett enda långt stycke” ger ett enda stycke enligt checkbox-regeln.

7. **Branch/PR hygiene**

* Varje task är mergad till `dev` via separat branch med tydlig commit message.
* Inga orelaterade diffar (format/städning) utanför berörda filer.
