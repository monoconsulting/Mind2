# MIND Process Review - Kvittoanalys
**Datum:** 2025-10-11
**Analysör:** Claude Code
**Syfte:** Djupanalys av kvittohantering och identifiering av problem i AI-pipeline

---

## Sammanfattning

Analys av totalt **40 aktiva kvitton** i systemet visar flera kritiska problem som påverkar databehandling och kontering. Huvudproblemen är:

1. **Ofullständig grunddata** - 60% av kvitton saknar företagsinformation
2. **Saknad varulista** - Många kvitton saknar artikelrad (receipt_items)
3. **AI4-fel i kontering** - Ogiltiga item_id-värden blockerar kontering
4. **Schema-inkonsekvens** - merchant_name används felaktigt i frontend/backend
5. **AI3-valideringsfel** - Decimalhantering och datatyper brister

---

## 1. Grunddata-analys

### Statistik
- **Totalt antal kvitton:** 40
- **Kvitton med företag (company_id > 0):** 16 (40%)
- **Kvitton utan företag (company_id = 0):** 24 (60%)

### Status-fördelning
| Status | Antal | Beskrivning |
|--------|-------|-------------|
| `manual_review` | 18 | Kräver manuell granskning |
| `uploaded` | 13 | Bara uppladdade, ej processade |
| `ai4_completed` | 9 | Fullständigt processade med konteringsförslag |

### Kritiska fynd
- **60% av kvitton saknar företagsinformation** - Detta beror på:
  - Saknade orgnr i OCR-data
  - AI kan inte matcha företagsnamn utan organisationsnummer
  - Varning i loggar: `Cannot create company 'BURGER KING': orgnr is required but missing`

### Exempel på kvitton med bra grunddata
**Kvitto ID:** `63a665f3-9982-438c-97bb-7fe081d542c7` (BAUHAUS)
```
- company_id: 6 (BAUHAUS)
- purchase_datetime: 2025-07-07 07:41:00
- gross_amount_original: 464.26 SEK
- net_amount_original: 371.41 SEK
- receipt_number: 395505 854120 KF1
- payment_type: card
- ai_status: ai4_completed
- ai_confidence: 0.93
```

### Exempel på kvitton med saknad grunddata
**Kvitto ID:** `c31657f3-e2e6-499f-b6fd-322939843995`
```
- company_id: 0 (SAKNAS)
- purchase_datetime: NULL
- gross_amount: NULL
- net_amount: NULL
- ai_status: manual_review
```

---

## 2. Varulista (receipt_items) - Analys

### Statistik
Av de 20 senaste kvittona:
- **Kvitton med artiklar:** 4 (20%)
- **Kvitton utan artiklar:** 16 (80%)

### Exempel på korrekt varulista
**Kvitto:** `63a665f3-9982-438c-97bb-7fe081d542c7` (BAUHAUS)
| ID | Artikel | Antal | Pris exkl moms | Pris inkl moms | Moms % |
|----|---------|-------|----------------|----------------|--------|
| 32 | EXXACT RAM 3-FACK AV | 1 | 87.20 | 109.00 | 25% |
| 33 | EXXACT STRÖMST. TRA | 1 | 79.16 | 98.95 | 25% |
| 34 | EXXACT STRÖMST. TRA | 1 | 79.16 | 98.95 | 25% |
| 35 | EXXACT RAM 1-FACK | 1 | 23.96 | 29.95 | 25% |
| 36 | EXXACT VÄGGUTTAG 1- | 1 | 143.20 | 179.00 | 25% |
| 37 | RABATT | 1 | -41.27 | -51.59 | 25% |

### Problem
1. **AI3 returnerar NO receipt_items för många dokument**
   - Varning: `AI3 LLM returned NO receipt_items for file_id=e1df5ab5-8d4d-443e-985b-9ceb8c3e00b8`
   - Detta kan vara legitimt för vissa dokument, men händer för ofta

2. **Valideringsfel vid parsning av artiklar**
   - Exempel från logg:
   ```
   AI3 failed to parse receipt_items[1] for file_id=97fafb82-9102-424b-b2ba-1377c0dbdfa6:
   - number: Input should be a valid integer, got a number with a fractional part (25.35)
   - item_price_ex_vat: Decimal input should have no more than 2 decimal places (12.392)
   ```

---

## 3. Kontering (ai_accounting_proposals) - Analys

### Statistik för konteringar
| Kvitto-ID | Företag | Antal artiklar | Antal konteringar |
|-----------|---------|----------------|-------------------|
| 63a665f3-... | BAUHAUS | 6 | 18 (3 per artikel) |
| 835ef425-... | Neko Sushi | 2 | 6 (3 per artikel) |
| 8eb032b6-... | Burger King Akalla | 5 | 15 (3 per artikel) |
| a919436a-... | Ruccola Bromma AB | 1 | 3 (3 per artikel) |

### Korrekt konteringsmönster
För varje artikel skapas 3 konteringar:
1. **Debet:** Konto 4010 (Inköp av varor) - nettopris
2. **Debet:** Konto 2641 (Ingående moms 25%) - moms
3. **Kredit:** Konto 2440 (Leverantörsskuld) - bruttopris

### Exempel på korrekt kontering (BAUHAUS, artikel 32)
```sql
id: 49  | receipt_id: 63a6... | item_id: 32 | account: 4010 | debit: 87.20  | credit: 0.00
id: 50  | receipt_id: 63a6... | item_id: 32 | account: 2641 | debit: 21.80  | credit: 0.00
id: 51  | receipt_id: 63a6... | item_id: 32 | account: 2440 | debit: 0.00   | credit: 109.00
```

### 🔴 KRITISKT FEL: AI4 payload validation error

**Problem:** AI4 försöker skapa konteringar utan giltigt item_id
```
ERROR: Invalid AI4 payload for 76438654-009c-4f0b-b220-fa565070c5ae:
entries[1].item_id must be an integer.
Full payload: {
  "entries": [
    {
      "receipt_id": "76438654-009c-4f0b-b220-fa565070c5ae",
      "item_id": "",  <-- TOM STRÄNG ISTÄLLET FÖR INTEGER!
      "account_code": "6210",
      "debit": 264.0,
      "credit": 0.0
    }
  ]
}
```

**Konsekvens:** Kontering blockeras helt för kvitton utan receipt_items

---

## 4. Title-fält och företagsnamn i Process-menyn

### 🔴 KRITISKT: Schema-inkonsekvens med merchant_name

**Problem identifierat i `backend/src/api/receipts.py`:**

#### Rad 787: SQL-query använder FELAKTIGT alias
```python
"SELECT u.id, u.original_filename, c.name as merchant_name, ..."  # FELAKTIGT!
```
- Kolumnen `merchant_name` finns INTE i `unified_files`
- Rätt: Företagsnamn ska alltid hämtas via `companies.name` genom JOIN

#### Rad 626: Kommentar bekräftar problemet
```python
# NOTE: merchant_name does NOT exist in unified_files
# Merchant name is stored in companies table via company_id
```

#### Frontend-kod (Process.jsx) använder felaktiga fält
**Rad 1019:** WorkflowBadges använder `workflow.title`
```javascript
{renderBadge('Title', workflow.title || `ID: ${workflow.file_id}`)}
```

**Rad 1540:** Tabell visar `receipt.merchant`
```javascript
<div className="font-medium">{receipt.merchant || 'Okänt bolag'}</div>
```

### Aktuellt schema
```
unified_files:
  ✅ id (varchar 36)
  ✅ company_id (int, FK till companies.id)
  ❌ merchant_name (FINNS INTE!)
  ❌ Title (FINNS INTE!)
  ✅ original_filename
  ✅ purchase_datetime
  ...

companies:
  ✅ id (int, PK)
  ✅ name (varchar) <-- DETTA är företagsnamnet!
  ✅ orgnr
```

---

## 5. Felmeddelanden från AI4 och Docker-loggar

### Sammanfattning av kritiska fel

#### A. SoftTimeLimitExceeded (Celery timeout)
```
billiard.exceptions.SoftTimeLimitExceeded: SoftTimeLimitExceeded()
```
- **Orsak:** AI-anrop tar över 240 sekunder (soft limit)
- **Påverkan:** Processning avbryts mitt i körning
- **Loggplats:** Celery worker logs

#### B. OpenAI API Timeout
```
ERROR: OpenAI API error: HTTPSConnectionPool(host='api.openai.com', port=443):
Read timed out. (read timeout=180)
```
- **Orsak:** OpenAI API svarar inte inom 180 sekunder
- **Påverkan:** AI2 (expense_classification) failar
- **Frekvens:** Regelbundet

#### C. AI3 Valideringsfel
```
ERROR: AI3 failed to parse receipt_items[1]:
- number: Input should be a valid integer, got a number with a fractional part (25.35)
- item_price_ex_vat: Decimal input should have no more than 2 decimal places (12.392)
```
- **Orsak:** AI3 returnerar flyttal där heltal förväntas
- **Påverkan:** Receipt items kan inte sparas korrekt
- **Exempel data:** `{'number': 25.35, 'item_price_ex_vat': 12.392, ...}`

#### D. Saknade organisationsnummer
```
WARNING: Cannot create company 'OKQ8': orgnr is required but missing
WARNING: Cannot create company 'BURGER KING': orgnr is required but missing
WARNING: Cannot ensure company: both name and orgnr are empty
```
- **Orsak:** OCR hittar inte orgnr på kvitton
- **Påverkan:** Företag kan inte skapas → company_id = 0

#### E. AI4 item_id validation error
```
ERROR: Invalid AI4 payload: entries[1].item_id must be an integer.
Full payload: {"item_id": "", ...}
```
- **Orsak:** AI4 försöker skapa kontering när receipt_items saknas
- **Påverkan:** Kontering blockeras helt

---

## 6. Rekommendationer

### 🔴 Kritiska åtgärder (MÅSTE fixas omedelbart)

#### 6.1 Fixa AI4 item_id validation error
**Problem:** AI4 skickar tom sträng istället för integer
**Lösning:**
```python
# I backend/src/services/accounting.py eller liknande
def create_accounting_proposal(receipt_id, items):
    if not items or len(items) == 0:
        # Skapa en "fallback" kontering direkt på kvittot utan item_id
        return create_receipt_level_accounting(receipt_id)

    # Annars, skapa kontering per artikel som vanligt
    for item in items:
        if item.id is None:
            logger.error(f"Item missing id for receipt {receipt_id}")
            continue
        create_item_accounting(receipt_id, item.id, ...)
```

#### 6.2 Ta bort merchant_name från SQL-queries
**Filer att uppdatera:**
- `backend/src/api/receipts.py:787` - Ändra alias till `c.name as company_name`
- Alla andra ställen som använder `merchant_name` från unified_files

**Före:**
```python
"SELECT u.id, c.name as merchant_name FROM unified_files u ..."
```

**Efter:**
```python
"SELECT u.id, c.name as company_name FROM unified_files u ..."
```

#### 6.3 Fixa AI3 valideringsfel för decimaler
**Problem:** AI3 returnerar 12.392 (3 decimaler) där 2 förväntas
**Lösning:**
```python
# I backend/src/services/ai_service.py eller parsing-logik
def parse_receipt_item(raw_data):
    # Avrunda alla priser till 2 decimaler
    if 'item_price_ex_vat' in raw_data:
        raw_data['item_price_ex_vat'] = round(float(raw_data['item_price_ex_vat']), 2)

    # Konvertera 'number' till heltal
    if 'number' in raw_data:
        raw_data['number'] = int(round(float(raw_data['number'])))

    return raw_data
```

### 🟡 Viktiga åtgärder (Bör fixas snart)

#### 6.4 Förbättra företagsidentifiering
**Problem:** 60% av kvitton saknar företag (company_id = 0)
**Lösningar:**
1. **Förbättra OCR-extrahering av orgnr**
   - Lägg till regex-patterns för svenska orgnr (XXXXXX-XXXX)
   - Träna AI att känna igen "Org.nr:", "Orgnr:", "VAT:", etc.

2. **Implementera fuzzy matching på företagsnamn**
   ```python
   def find_company_by_name(name):
       # Om orgnr saknas, försök hitta företag baserat på namn
       # Använd Levenshtein distance eller liknande
       companies = get_all_companies()
       best_match = find_closest_match(name, [c.name for c in companies])
       if similarity > 0.85:  # 85% match
           return best_match
   ```

3. **Manuell review-workflow**
   - För kvitton med company_id = 0, flagga för manuell företagslänkning
   - Lägg till UI i ReceiptPreviewModal för att välja företag

#### 6.5 Hantera saknade receipt_items
**Problem:** 80% av kvitton saknar artikelrad
**Lösningar:**
1. **Skapa fallback-kontering**
   ```python
   def create_fallback_accounting(receipt):
       # Om inga items finns, skapa en enkel kontering på totalnivå
       entries = [
           {'account': '4010', 'debit': receipt.net_amount, 'credit': 0},
           {'account': '2641', 'debit': receipt.vat_amount, 'credit': 0},
           {'account': '2440', 'debit': 0, 'credit': receipt.gross_amount}
       ]
       return entries
   ```

2. **Förbättra AI3 prompt**
   - Tydliggör att varje rad på kvittot ska bli en article
   - Ge exempel på struktur

#### 6.6 Öka timeouts för AI-anrop
**Problem:** SoftTimeLimitExceeded och API timeouts
**Lösning:**
```python
# I docker-compose.yml eller celery config
celery ... --soft-time-limit=480 --time-limit=600  # Öka från 240 till 480 sek

# I backend/src/services/ai_service.py
response = requests.post(url, ..., timeout=300)  # Öka från 180 till 300 sek
```

### 🟢 Förbättringar (Nice to have)

#### 6.7 Lägg till monitoring för AI-stadier
- Dashboard som visar success rate per AI-stage
- Alert när fel överstiger 10% för någon stage
- Grafana-dashboard med metrics från Prometheus

#### 6.8 Implementera retry-logik
```python
@retry(max_attempts=3, backoff=exponential)
def call_ai_service(prompt, payload):
    # Försök igen automatiskt vid timeout eller fel
    ...
```

#### 6.9 Cachning av AI-resultat
- För identiska kvitton (content_hash), återanvänd tidigare AI-resultat
- Spara tokens och processingstid

---

## 7. Sammanfattande åtgärdslista

### Prioritet 1 (Akut - Blockerar produktion)
- [ ] Fixa AI4 item_id validation error (empty string → integer)
- [ ] Ta bort alla referenser till `merchant_name` från unified_files
- [ ] Implementera fallback-kontering för kvitton utan receipt_items

### Prioritet 2 (Hög - Påverkar datakvalitet)
- [ ] Fixa AI3 decimal-avrundning (2 decimaler max)
- [ ] Fixa AI3 'number' field (måste vara integer)
- [ ] Förbättra OCR-extrahering av organisationsnummer
- [ ] Öka timeouts för AI-anrop (240s → 480s)

### Prioritet 3 (Medel - Förbättrar användbarhet)
- [ ] Implementera fuzzy matching för företagsnamn
- [ ] Lägg till manuell företagslänkning i UI
- [ ] Förbättra AI3 prompt för bättre item-extrahering
- [ ] Lägg till retry-logik för AI-anrop

### Prioritet 4 (Låg - Optimering)
- [ ] Monitoring dashboard för AI-stages
- [ ] Cachning av AI-resultat baserat på content_hash
- [ ] Alerting för höga felfrekvenser

---

## 8. Teknisk skuld

### Schema-inkonsekvenser
- `merchant_name` används i kod men finns inte i databas
- `Title` refereras i frontend men finns inte i schema
- Inkonsekvent användning av `status` vs `ai_status`

### AI Pipeline-brister
- Ingen hantering av kvitton utan artiklar
- Ingen retry-mekanism vid timeout
- Ingen validering av AI-output innan databas-insert

### Frontend-backend mismatch
- Frontend förväntar `merchant` från API
- API returnerar `merchant_name` via alias
- Ingen av dessa matchar faktiskt schema (ska vara `companies.name`)

---

**Analysens slutsats:**
Systemet har en fungerande grundstruktur men lider av kritiska schema-inkonsekvenser och bristande felhantering i AI-pipelinen. De viktigaste åtgärderna är att:
1. Fixa item_id-valideringen i AI4
2. Rätta till merchant_name-förvirringen
3. Implementera fallback-kontering för kvitton utan artiklar

Med dessa fixar bör systemet kunna processa kvitton mer tillförlitligt.
