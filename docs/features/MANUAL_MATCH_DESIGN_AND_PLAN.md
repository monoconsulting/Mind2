# Systemdesign: “Manuell matchning”

## Syfte

Ge operatören en dedikerad vy för att manuellt koppla **en** FirstCard-rad (vänster) till **ett** kvitto (höger) när den automatiska matchningen inte träffar korrekt. Skärmen stödjer:

* Val av **månad/år** i en smal header (default = **senast importerade FC-fakturan**).
* Vänster kolumn: alla **FC-rader** för vald period.
* Höger kolumn: alla **kvitton** i vald period.
* **Checkbox** per rad i respektive kolumn (exakt **en** åt gången per sida).
* **MATCHA**-knapp i headern som blir synlig/aktiv **endast när exakt en rad** är vald på båda sidor.
* Snabb åtkomst till din befintliga **kvittoportal/ReceiptPreviewModal** för att visa/redigera kvittodetaljer.

## Relevanta befintliga delar i kodbasen (återanvänds)

* **Frontend**

  * `main-system/app-frontend/src/ui/App.jsx` – navigering och rutter.
  * `main-system/app-frontend/src/ui/api.js` – token-aware fetch wrapper.
  * `main-system/app-frontend/src/ui/pages/CompanyCard.jsx` – befintlig FirstCard UI (logik, statusflöden, listor, kandidat-hämtning).
  * `main-system/app-frontend/src/ui/pages/Receipts.jsx` – kvittolista & filtermönster.
  * `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx` – kvittoportal (visa/redigera + OCR-overlay).
* **Backend (Flask) – FirstCard**

  * `backend/src/api/reconciliation_firstcard/routes/statements.py` – lista statements (period_start/period_end mm).
  * `backend/src/api/reconciliation_firstcard/routes/lines.py` – lista rader och kandidat-API.
  * `backend/src/api/reconciliation_firstcard/routes/matching.py` – **manuell/automatisk matchning** (`POST /reconciliation/firstcard/match`) samt `PUT /reconciliation/firstcard/lines/<id>`.
* **Backend – Kvitton**

  * `backend/src/api/receipts.py`

    * `GET /receipts` med `from`/`to` filters – används för månadsvy.
    * `GET/PUT /receipts/<id>/modal` – samma data som i kvittoportalen.

> Poängen: All kärnlogik (lista FC-rader, lista kvitton, matcha) finns redan. Den nya sidan är primärt **UI-komposition** + **tunn limlogik**.

## Navigering & Route

* **Nytt menyalternativ:** “Manuell matchning”
* **Ny route:** `/manual-match`
* Placeras i vänstermenyn intill “Kortmatchning” (CompanyCard). Ingen ändring av befintliga rutter eller globala states.

## Header (smal toppremsa)

* **Selectors:** `år` + `månad`.
* **Defaultval:** hämta senaste FC-statement via `GET /ai/api/reconciliation/firstcard/statements` och välj dess **period_end** (eller `period_start`) som startmånad. Om inga statements: fallback till nyaste kvitto-månad (via `/ai/api/receipts?to=...&from=...` med rimlig default, t.ex. innevarande månad).
* **Primär CTA:** **MATCHA** (centrerad). **Synlig och enabled endast om** exakt en vänster-rad och exakt ett höger-kvitto är selekterade. I övrigt dold/disabled.

## Vänster kolumn: FC-rader (för vald period)

* Källa:

  * Använd **senaste statement/invoice** för vald månad: lista via `GET /ai/api/reconciliation/firstcard/statements` → välj statement som överlappar vald månad → hämta dess detaljer/rader via motsvarande `lines`-endpoint (i CompanyCard används `/lines` och `/invoices/{id}`—återanvänd samma mönster).
* Tabellkolumner (för att kunna avgöra rätt rad):

  * Datum (transaction_date), Belopp (amount), Kortinnehavare/kortmask, Merchant, Beskrivning, Status (match_status/processing_status), ev. intern line_id.
* Första kolumnen: **checkbox** (single-select). Om ny selektion görs, avmarkera tidigare.

## Höger kolumn: Kvitton (för vald period)

* Källa: `GET /ai/api/receipts?from=YYYY-MM-01&to=YYYY-MM-<end>`
  (Redan stöds `from`/`to` i `receipts.py`.)
* Tabellkolumner:

  * Inköpsdatum, Belopp (total_gross), Valuta, Merchant, Orgnr, Taggar/status, Interna id, m.m.
* Första kolumnen: **checkbox** (single-select).
* **Visa/Redigera kvitto:** ikonknapp som öppnar **ReceiptPreviewModal** (återanvänd befintlig komponent rakt av).

## MATCHA-flöde

1. Användaren väljer **en** FC-rad + **ett** kvitto.
2. Klick på **MATCHA** → `POST /ai/api/reconciliation/firstcard/match`
   Payload: `{ line_id: <int>, receipt_id: <uuid>, invoice_id?: <int> }`
   (Befintliga endpoints i `matching.py` hanterar manuell länkning och uppdaterar status + loggar event via `observability.events.log_event`.)
3. UI:

   * Disable CTA under call, visa spinner/toast.
   * Vid svar `{ ok: true }`: uppdatera vänster lista (radens status blir “matched/…”) och höger lista (kvittot kan markeras “linked/matched” om du vill gråa ut).
   * Vid fel: visa tydligt fel (HTTP-kod + reason), lämna selection intakt så operatören kan försöka en annan kvittorad.

## State & återladdning

* Lokal page-state: `selectedPeriod`, `selectedLineId`, `selectedReceiptId`, `fcLines[]`, `receipts[]`, `loadingFlags`.
* Vid periodbyte:

  * Ladda **statement** för månaden (om flera – ta senast `uploaded_at` som överlappar månaden).
  * Ladda rader för valt statement.
  * Ladda kvitton med `from`/`to`.
* Spara senast använda period i `sessionStorage` (valfritt) för bättre UX.

## Rättigheter & logg

* Återanvänd befintlig auth (JWT i `api.js`).
* Inga nya roller krävs om nuvarande endpoints redan är skyddade.
* Logg sker i backend (redan implementerat—`log_event`, `record_invoice_decision`). Ingen förändring.

## Prestanda

* Paginera om listor är stora (både `lines` och `receipts` stödjer pagination/filter i backenden).
* Minimera extrahämtningar—debounce/avoid duplicate fetch på periodbyte.

## Felhantering (typfall)

* Inga statements i vald period → visa tomt till vänster + info-banner.
* Inga kvitton i vald period → tomt till höger + länk/knapp för att öppna kvittosidan (valfritt).
* Matchningsfel (409/422) → förklara konflikt (kvittot redan länkat, avvikande belopp/datum) och lämna användaren kvar på sidan.

---

# Genomförandeplan (strikt scope, agentvänlig)

**Scope:** Endast ny frontend-vy + minimal navigationstillägg. **Ingen** ändring i befintlig backendlogik. Endast anropa redan existerande endpoints. **Ingen** refaktor av befintliga sidor. **Inget** tas bort – allt nytt läggs till isolerat.

## Fas 0 – Förberedelser (½ sprint)

**Mål:** Säkra beroenden och skapa grundfil för sidan.

* **Task F0.1**: Läs in befintliga mönster

  * Studera hur `CompanyCard.jsx` hämtar statements, rader, kandidater och hur den anropar `/reconciliation/firstcard/*`.
  * Studera `Receipts.jsx` för datumfilter och tabellrendering.
* **Task F0.2**: Skapa ny sida

  * Skapa `main-system/app-frontend/src/ui/pages/ManualMatch.jsx` (ren ny fil).
  * **Ingen** påverkan på andra sidor i detta steg.
* **Task F0.3**: UI-skal

  * Lägg en enkel layout: Header (månad/år + disabled MATCHA), två kolumner med tomma placeholders.

## Fas 1 – Datakoppling (1 sprint)

**Mål:** Få listsidorna att ladda korrekt data för vald period.

* **Task F1.1**: Defaultperiod (senaste statement)

  * Vid mount: `GET /ai/api/reconciliation/firstcard/statements` → plocka senaste som överlappar någon månad → sätt `selectedYear`/`selectedMonth`.
  * Fallback: om tomt, sätt `selectedYear/Month` till nuvarande månad (eller nyaste kvittomånad via `/receipts`).
* **Task F1.2**: Ladda FC-rader

  * Hitta rätt statement/invoice för vald månad (samma logik som i CompanyCard). Ladda rader via `lines`/`invoices/{id}`-mönstret.
* **Task F1.3**: Ladda kvitton

  * Anropa `GET /ai/api/receipts?from=YYYY-MM-01&to=YYYY-MM-<end>` och rendera tabell.
* **Task F1.4**: Checkbox-logik

  * Implementera **single-select** per kolumn (deselect tidigare vid nytt val).
  * MATCHA-knappen blir synlig/aktiv endast när båda sidor har **exakt 1** vald.

## Fas 2 – Kvittoportal, detaljer & UX (½–1 sprint)

**Mål:** Integrera kvittoportal och förbättra tabellernas användbarhet.

* **Task F2.1**: Öppna kvittoportal

  * Återanvänd `ReceiptPreviewModal.jsx` (samma props-/api-användning som i `Receipts.jsx`). Lägg en “Visa”-ikon i kvittotabellen.
* **Task F2.2**: Kolumnformattering

  * Datumformat SV, beloppsformat SEK/EUR etc (återanvänd formatterare från `Receipts.jsx` där möjligt).
* **Task F2.3**: Statusbadges

  * Visa enkel statusindikator på FC-rad (matched/pending/failed) och kvitton (approved/needs_review) genom att mappa fält du redan visar i CompanyCard/Receipts.

## Fas 3 – Matchnings-call & uppfräschning (½ sprint)

**Mål:** Göra kopplingen och uppdatera vyerna korrekt.

* **Task F3.1**: MATCHA-anrop

  * `POST /ai/api/reconciliation/firstcard/match` med `{ line_id, receipt_id, invoice_id? }`.
  * Under call: disable CTA, visa spinner.
* **Task F3.2**: Uppdatera listor efter lyckad match

  * Hämta om raden (eller hela listan för enkelhet) så status ändras.
  * Option: markera kvittot som använt/länkat (gråa ut).
* **Task F3.3**: Felhantering

  * Visa tydlig toast/banner på 4xx/5xx. Lämna selection intakt.

## Fas 4 – Paginering & filter (valfritt, ½ sprint)

**Mål:** Robusthet vid stora datamängder.

* **Task F4.1**: Paginering

  * Lägg enkla “visa fler”/”nästa sida” för både FC-rader och kvitton, matchande backends parametrar.
* **Task F4.2**: Enkla filter

  * Sökfält på merchant/amount-spann för snabbare urval lokalt, alternativt lägg query-parametrar om backend redan stödjer.

## Fas 5 – Test & Go-Live (½ sprint)

**Mål:** Verifiera att inget annat påverkas och att flödet är stabilt.

* **Task F5.1**: E2E smoke (Playwright tests ligger redan i repo)

  * Minimal e2e: ladda sidan, välj period, select vänster+höger, öppna modal, gör match, verifiera uppdaterad status.
* **Task F5.2**: Regression

  * Bekräfta att `CompanyCard.jsx`, `Receipts.jsx` och `/process` fungerar som tidigare (ingen påverkan).
* **Task F5.3**: Dokumentation

  * Lägg kort README-sektion i `main-system/app-frontend/README.md` som beskriver var sidan finns, vilka endpoints den nyttjar och hur defaultperiod fastställs.

---

# Tekniska detaljer (för utvecklingsagenten)

## Filändringar (endast tillägg + minimal navigationsdiff)

* **Skapa:**
  `main-system/app-frontend/src/ui/pages/ManualMatch.jsx`
* **Uppdatera (små diffar, inget tas bort):**
  `main-system/app-frontend/src/ui/App.jsx`

  * Lägg till en ny `NavButton` “Manuell matchning” och en `<Route path="/manual-match" element={<Shell><ManualMatch /></Shell>} />`
  * All befintlig meny och sidor orörda.
* **Återanvänd:**
  `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx` (oförändrad)

## Datahämtning (mönster)

* **Senaste statement → defaultperiod**

  * GET `/ai/api/reconciliation/firstcard/statements` → sortera på `uploaded_at`/`updated_at`, filtrera som överlappar vald månad.
* **FC-rader**

  * Via samma endpoints/mönster som i `CompanyCard.jsx` (`/lines`, `/invoices/{id}`, `/lines/{id}/candidates` finns redan).
* **Kvitton**

  * GET `/ai/api/receipts?from=YYYY-MM-01&to=YYYY-MM-<end>`

## Matcha

* **POST** `/ai/api/reconciliation/firstcard/match`
  Body: `{ line_id: number, receipt_id: string, invoice_id?: number }`
  Hanteras i `matching.py` (loggar, status transitions, persist).

## UI-regler

* Exakt **en** checkbox åt gången i varje lista (vänster/höger).
* MATCHA: disabled tills båda val finns.
* Efter lyckad match:

  * Uppdatera raden (status) och/eller ladda om listan.
  * Valfritt: auto-avmarkera båda val för att undvika dubbelmatch på samma kvitto.

## Testfall (korta)

1. **Defaultperiod** sätts till senaste statement.
2. **Periodbyte** laddar om båda listor korrekt.
3. **Öppna kvittoportal** från höger tabell och spara en redigering.
4. **Lyckad match** ger `{ ok: true }` och uppdaterar UI-status.
5. **Felmatch** (kvittot redan länkat) visar fel utan att krascha.

---

# Risker & Mitigation

* **Ingen statement i vald månad:** Visa info-banner och låt användaren välja annan månad.
* **Stora listor:** Lägg pagination i Fas 4 om nödvändigt.
* **API-avvikelser:** Håll dig strikt till redan använda kontrakt i `CompanyCard.jsx` och `receipts.py`. Undvik nya endpoints i denna leverans.

---

# Leveranschecklista (snabb)

* [ ] Ny sida `ManualMatch.jsx` incheckad, isolerad.
* [ ] Meny + route tillagd i `App.jsx` utan att röra andra sidor.
* [ ] Defaultperiod = senaste statement.
* [ ] Vänster = FC-rader, Höger = kvitton, båda filtrerade på period.
* [ ] Single-select checkbox per kolumn.
* [ ] MATCHA-knapp → POST `/reconciliation/firstcard/match`.
* [ ] ReceiptPreviewModal öppnas från kvittolistan.
* [ ] README-notis med kort bruksanvisning.

