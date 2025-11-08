# Mind2 Status Definitions - Komplett Lista

**Version:** 1.0
**Datum:** 2025-11-08

Detta dokument listar ALLA statusar (stage_keys) som skrivs till `workflow_stage_runs` tabellen, organiserade per workflow-typ.

---

## 📋 Innehållsförteckning

1. [Gemensamma Källor-statusar](#gemensamma-källor-statusar)
2. [WF1_RECEIPT - Kvittoflöde](#wf1_receipt---kvittoflöde)
3. [WF3_FIRSTCARD_INVOICE - FirstCard-fakturor](#wf3_firstcard_invoice---firstcard-fakturor)
4. [Återuppta/Omstart-statusar](#återupptaomstart-statusar)
5. [Gemensamma Utfall-statusar](#gemensamma-utfall-statusar)
6. [Svenska översättningar i frontend](#svenska-översättningar-i-frontend)

---

## Gemensamma Källor-statusar

Dessa statusar loggas vid filuppladdning, oavsett workflow-typ:

### src_portal (Upload Portal)
- **Källa:** `backend/src/api/ingest.py` rad 161-171
- **Trigger:** Process.jsx "Ladda upp"-knapp → `/ai/api/ingest/upload`
- **Loggas vid:** Portaluppladdning av filer
- **Statusar:**
  - `src_portal_start` - startad ⏳
  - `src_portal running` - pågående
  - `src_portal_end` / `src_portal succeeded` - avslutad ✅

### src_ftp (FTP-hämtning)
- **Källa:** `backend/src/services/fetch_ftp.py` rad 225-267
- **Trigger:** Process.jsx "Hämta från FTP"-knapp → `/ai/api/ingest/fetch-ftp`
- **Loggas vid:** FTP-hämtning av filer från leverantör
- **Statusar:**
  - `src_ftp_start` - startad ⏳
  - `src_ftp running` - pågående
  - `src_ftp_end` / `src_ftp succeeded` - avslutad ✅

### src_fc (FirstCard-uppladdning)
- **Källa:** `backend/src/api/reconciliation_firstcard.py` rad 634-679
- **Trigger:** CompanyCard.jsx "Ladda upp faktura" → `/reconciliation/firstcard/upload-invoice`
- **Loggas vid:** Upload av FirstCard-fakturaexcel
- **Statusar:**
  - `src_fc_start` - startad ⏳
  - `src_fc running` - pågående
  - `src_fc_end` / `src_fc succeeded` - avslutad ✅

### ingest_store (Lagra fil)
- **Källa:** `backend/src/api/ingest.py` rad 172-182
- **Trigger:** Automatiskt efter upload
- **Loggas vid:** Lagring av fil + metadata i unified_files
- **Statusar:**
  - `ingest_store_start` - startad ⏳
  - `ingest_store running` - pågående
  - `ingest_store_end` / `ingest_store succeeded` - avslutad ✅

### ingest_wf1 (Skapa kvitto-workflow)
- **Källa:** `backend/src/api/ingest.py` rad 184-198
- **Trigger:** Automatiskt för WF1_RECEIPT workflows
- **Loggas vid:** Skapande av workflow_run för kvitton
- **Statusar:**
  - `ingest_wf1_start` - startad ⏳
  - `ingest_wf1 running` - pågående
  - `ingest_wf1_end` / `ingest_wf1 succeeded` - avslutad ✅

---

## WF1_RECEIPT - Kvittoflöde

### detect_type (Dokumentklassning - AI1)
- **Källa:** `backend/src/services/tasks.py` rad 3832-3904
- **Trigger:** Celery task `classify_and_route_receipt_v3()`
- **AI-modell:** AI1 (dokumentklassificering)
- **Loggas vid:** Klassificering av dokumenttyp (kvitto/faktura/annat)
- **Statusar:**
  - `detect_type_start` - startad ⏳
  - `detect_type running` - pågående
  - `detect_type_end` / `detect_type succeeded` - avslutad ✅

### r_ocr (OCR för kvitton)
- **Källa:** `backend/src/services/tasks.py` rad 2689-2713
- **Trigger:** Celery task `perform_ocr_on_receipt()`
- **OCR-motor:** PaddleOCR
- **Loggas vid:** OCR-textextraktion från kvittobild
- **Statusar:**
  - `r_ocr_start` - startad ⏳
  - `r_ocr running` - pågående
  - `r_ocr_end` / `r_ocr succeeded` - avslutad ✅

### r_ai3 (Dataextraktion - AI3)
- **Källa:** `backend/src/services/tasks.py` rad 3979-4110
- **Trigger:** Celery task `extract_receipt_data_ai3()`
- **AI-modell:** AI3 (dataextraktion)
- **Loggas vid:** Extrahering av belopp, datum, merchant från OCR-text
- **Statusar:**
  - `r_ai3_start` - startad ⏳
  - `r_ai3 running` - pågående
  - `r_ai3_end` / `r_ai3 succeeded` - avslutad ✅

### r_ai4 (Normalisering/validering - AI4)
- **Källa:** `backend/src/services/tasks.py` rad 4120-4226
- **Trigger:** Celery task `normalize_receipt_data_ai4()`
- **AI-modell:** AI4 (normalisering)
- **Loggas vid:** Normalisering och validering av extraherad data
- **Statusar:**
  - `r_ai4_start` - startad ⏳
  - `r_ai4 running` - pågående
  - `r_ai4_end` / `r_ai4 succeeded` - avslutad ✅

### r_persist (Spara data)
- **Källa:** `backend/src/services/tasks.py` (implicit via AI4)
- **Trigger:** Efter AI4-normalisering
- **Loggas vid:** Sparande av strukturerad data till unified_files + derivattabeller
- **Statusar:**
  - `r_persist_start` - startad ⏳
  - `r_persist running` - pågående
  - `r_persist_end` / `r_persist succeeded` - avslutad ✅

### r_queue_match (Köa matchning)
- **Källa:** `backend/src/services/tasks.py` rad 4233-4234
- **Trigger:** Efter r_persist
- **Loggas vid:** Köande av kvitto för AI5 kortmatchning
- **Statusar:**
  - `r_queue_match_start` - startad ⏳
  - `r_queue_match running` - pågående
  - `r_queue_match_end` / `r_queue_match succeeded` - avslutad ✅

---

## WF3_FIRSTCARD_INVOICE - FirstCard-fakturor

### fc_create (Skapa invoice_document)
- **Källa:** `backend/src/api/reconciliation_firstcard.py` rad 656-673
- **Trigger:** Efter src_fc upload
- **Loggas vid:** Skapande av credit_card_invoice-post
- **Statusar:**
  - `fc_create_start` - startad ⏳
  - `fc_create running` - pågående
  - `fc_create_end` / `fc_create succeeded` - avslutad ✅

### fc_ocr (OCR + sidextraktion)
- **Källa:** `backend/src/services/tasks.py` (process_credit_card_statement)
- **Trigger:** Celery task WF3
- **OCR-motor:** PaddleOCR
- **Loggas vid:** OCR på FirstCard PDF-faktura
- **Statusar:**
  - `fc_ocr_start` - startad ⏳
  - `fc_ocr running` - pågående
  - `fc_ocr_end` / `fc_ocr succeeded` - avslutad ✅

### fc_parse (Parsing av faktura - AI6)
- **Källa:** `backend/src/services/tasks.py` rad 3491-3543
- **Trigger:** Celery task `parse_credit_card_invoice_ai6()`
- **AI-modell:** AI6 (fakturatolkning)
- **Loggas vid:** Parsing av fakturahuvud + rader från OCR-text
- **Tabeller:** creditcard_invoices_main, creditcard_invoice_items
- **Statusar:**
  - `fc_parse_start` - startad ⏳
  - `fc_parse running` - pågående
  - `fc_parse_end` / `fc_parse succeeded` - avslutad ✅

### fc_is_fc (Beslut: FC-faktura?)
- **Källa:** Implicit decision node i workflow
- **Trigger:** Efter fc_parse
- **Loggas vid:** Beslut om dokumentet är en giltig FC-faktura
- **Statusar:**
  - `fc_is_fc running` - kontrollerar
  - `fc_is_fc succeeded` - JA, det är FC-faktura
  - `fc_is_fc failed` - NEJ → manual_review

### fc_ready (Redo för matchning)
- **Källa:** `backend/src/services/tasks.py` rad 3660-3692
- **Trigger:** Efter fc_parse (om fc_is_fc=ja)
- **Loggas vid:** Markering som 'ready_for_matching'
- **Statusar:**
  - `fc_ready_start` - startad ⏳
  - `fc_ready running` - pågående
  - `fc_ready_end` / `fc_ready succeeded` - avslutad ✅

---

## Gemensam Matchning (AI5)

### ai5 (Kortmatchning - AI5)
- **Källa:** `backend/src/services/tasks.py` rad 3702-3722
- **Trigger:** Efter r_queue_match (WF1) eller fc_ready (WF3)
- **AI-modell:** AI5 (matching-logik)
- **Loggas vid:** Automatisk matchning av kvitton ↔ FC-fakturarad
- **Statusar:**
  - `ai5_start` - startad ⏳
  - `ai5 running` - pågående
  - `ai5_end` / `ai5 succeeded` - avslutad ✅

### m_found (Beslut: Match hittad?)
- **Källa:** `backend/src/services/tasks.py` rad 3724-3729
- **Trigger:** Efter ai5
- **Loggas vid:** Beslut om automatisk match hittades
- **Statusar:**
  - `m_found succeeded` - JA, match hittad
  - `m_found failed` - NEJ, ingen match

### m_link (Länka kvitto)
- **Källa:** `backend/src/services/tasks.py` rad 3731-3741
- **Trigger:** Om m_found=ja
- **Loggas vid:** Länkning av kvitto till fakturarad (unified_files.credit_card_match=1)
- **Statusar:**
  - `m_link_start` - startad ⏳
  - `m_link running` - pågående
  - `m_link_end` / `m_link succeeded` - avslutad ✅

### m_unmatched (Omatchad)
- **Källa:** `backend/src/services/tasks.py` rad 3744-3754
- **Trigger:** Om m_found=nej eller partial match
- **Loggas vid:** Flaggning av omatchade rader för manuell hantering
- **Statusar:**
  - `m_unmatched_start` - startad ⏳
  - `m_unmatched running` - pågående
  - `m_unmatched_end` / `m_unmatched succeeded` - avslutad ✅

---

## Återuppta/Omstart-statusar

### resume_dispatch (Återupptar bearbetning) 🔄
- **Källa:**
  - `backend/src/api/ingest.py` rad 348-354 (Process.jsx)
  - `backend/src/api/reconciliation_firstcard.py` rad 2179-2185 (CompanyCard.jsx)
- **Trigger:**
  - Process.jsx "Återuppta"-knapp → `/ai/api/ingest/process/{id}/resume`
  - CompanyCard.jsx "Återuppta"-knapp → `/ai/api/reconciliation/firstcard/statements/{id}/resume`
- **Loggas vid:** Användare trycker "Återuppta" på en fil (fortsätter från där workflow stannade)
- **Statusar:**
  - `resume_dispatch_start` - startad ⏳
  - `resume_dispatch running` - pågående
  - `resume_dispatch_end` / `resume_dispatch succeeded` - avslutad ✅

### restart_dispatch (Omstartar från början) 🔄
- **Källa:** `backend/src/api/reconciliation_firstcard.py` rad 2248-2255
- **Trigger:** CompanyCard.jsx "Återuppta" (på completed status) → `/ai/api/reconciliation/firstcard/statements/{id}/restart`
- **Loggas vid:** Användare startar om HELA WF3-flödet från början (bara FC-fakturor)
- **Statusar:**
  - `restart_dispatch_start` - startad ⏳
  - `restart_dispatch running` - pågående
  - `restart_dispatch_end` / `restart_dispatch succeeded` - avslutad ✅

---

## Gemensamma Utfall-statusar

### finalize_ok (Slutför: lyckades)
- **Källa:** `backend/src/services/tasks.py` rad 3779-3789
- **Trigger:** Vid framgångsrikt slutförande av workflow
- **Loggas vid:** Workflow slutförd utan kritiska fel
- **Statusar:**
  - `finalize_ok_start` - startad ⏳
  - `finalize_ok running` - pågående
  - `finalize_ok_end` / `finalize_ok succeeded` - avslutad ✅

### finalize_fail (Slutför: misslyckades)
- **Källa:** `backend/src/services/tasks.py` rad 2556-2557
- **Trigger:** Vid misslyckande eller kritiska fel i workflow
- **Loggas vid:** Workflow kräver manuell åtgärd
- **Statusar:**
  - `finalize_fail_start` - startad ⏳
  - `finalize_fail running` - pågående
  - `finalize_fail_end` / `finalize_fail succeeded` - avslutad ✅

### manual_review (Manuell granskning) 🚩
- **Källa:** `backend/src/services/tasks.py` rad 3448, 3881
- **Trigger:** När dokument inte kan klassificeras eller processas automatiskt
- **Loggas vid:** Stopppunkt för manuell granskning
- **Statusar:**
  - `manual_review running` - väntar på manuell åtgärd
  - `manual_review succeeded` - granskad och godkänd

### KLAR (Workflow helt slutförd) ✅
- **Källa:** `backend/src/services/tasks.py` rad 3790-3794
- **Trigger:** Efter finalize_ok
- **Loggas vid:** Workflow helt avslutad, inga fler steg
- **Statusar:**
  - `KLAR succeeded` - helt klar

---

## Svenska översättningar i frontend

**Fil:** `main-system/app-frontend/src/ui/pages/Process.jsx` rad 145-177

### Stage Keys → Svenska

| Backend stage_key | Svenska (frontend) |
|------------------|-------------------|
| `src_portal` | Portal |
| `src_portal_start` | Portal start |
| `src_portal_end` | Portal klar |
| `src_ftp` | FTP |
| `src_ftp_start` | FTP start |
| `src_ftp_end` | FTP klar |
| `src_fc` | FC-uppladdning |
| `src_fc_start` | FC start |
| `src_fc_end` | FC klar |
| `ingest_store` | Lagrar fil |
| `ingest_store_start` | Lagrar fil start |
| `ingest_store_end` | Lagrar fil klar |
| `ingest_wf1` | Startar kvittoflöde |
| `fc_create` | Skapar FC-faktura |
| `fc_ocr` | FC OCR |
| `fc_parse` | FC-parsing |
| `fc_ready` | FC redo för matchning |
| `detect_type` | Dokumentklassning |
| `r_ocr` | OCR |
| `r_ai3` | Dataextraktion |
| `r_ai4` | Normalisering |
| `r_persist` | Sparar data |
| `r_queue_match` | Köar matchning |
| `ai5` | Kortmatchning |
| `m_link` | Länka kvitto |
| `m_unmatched` | Omatchad |
| `finalize_ok` | Slutför |
| `finalize_fail` | Slutför (fel) |
| `manual_review` | Manuell granskning |
| `resume_dispatch` | **Återupptar** ⭐ |
| `restart_dispatch` | **Omstartar** ⭐ |
| `KLAR` | KLAR |

### Status → Svenska

| Backend status | Svenska (frontend) |
|---------------|-------------------|
| `running` | pågående |
| `succeeded` | klar |
| `failed` | misslyckades |
| `queued` | i kö |
| `skipped` | hoppades över |

---

## Format i workflow_stage_runs

**Tabell:** `workflow_stage_runs`

**Kolumner:**
- `workflow_run_id` - FK till workflow_runs
- `stage_key` - Unik nyckel för steget (t.ex. "fc_parse", "resume_dispatch")
- `status` - Status för steget ("running", "succeeded", "failed", "queued")
- `message` - Beskrivande meddelande
- `started_at` - Timestamp när steget började
- `finished_at` - Timestamp när steget slutfördes

**Exempel på rader:**

```
stage_key         | status    | message                              | started_at
-----------------|-----------|--------------------------------------|------------------
src_fc_start     | running   | FC start                             | 2025-11-08 10:00:00
src_fc           | running   | Fil faktura.xlsx (45892 bytes)       | 2025-11-08 10:00:01
src_fc_end       | succeeded | Fil uppladdad                        | 2025-11-08 10:00:02
fc_ocr_start     | running   | FC OCR start                         | 2025-11-08 10:00:03
fc_ocr           | running   | OCR + sidextraktion                  | 2025-11-08 10:00:05
fc_ocr_end       | succeeded | OCR slutförd                         | 2025-11-08 10:00:15
fc_parse_start   | running   | FC-parsing start                     | 2025-11-08 10:00:16
fc_parse         | running   | AI6 tolkning av faktura              | 2025-11-08 10:00:17
fc_parse_end     | succeeded | Parsed 24 rader                      | 2025-11-08 10:00:25
ai5_start        | running   | Kortmatchning start                  | 2025-11-08 10:00:26
ai5              | running   | AI5 kortmatchning startar            | 2025-11-08 10:00:27
ai5_end          | succeeded | AI5 matchade 18/24 rader             | 2025-11-08 10:01:05
finalize_ok_start| running   | Slutför start                        | 2025-11-08 10:01:06
finalize_ok      | running   | FirstCard-flödet klart               | 2025-11-08 10:01:07
finalize_ok_end  | succeeded | Fakturaflödet avslutades utan fel    | 2025-11-08 10:01:08
KLAR             | succeeded | WF3 slutförd                         | 2025-11-08 10:01:09
```

---

## Frontend Status-visning

**Hämtas från:** `GET /ai/api/receipts`

**SQL-query** (backend/src/api/receipts.py rad 953-957):
```sql
SELECT
  ...
  (SELECT CONCAT(wsr.stage_key, ' ', wsr.status)
   FROM workflow_runs wr
   JOIN workflow_stage_runs wsr ON wsr.workflow_run_id = wr.id
   WHERE wr.file_id = u.id
   ORDER BY wsr.started_at DESC LIMIT 1) as workflow_stage_status
FROM unified_files u
```

**JSON-svar:**
```json
{
  "id": "file-123",
  "status": "processing",
  "ai_status": "processing",
  "workflow_stage_status": "fc_parse running"  ← DETTA VISAS I UI!
}
```

**Frontend (Process.jsx) visar:**
```javascript
<StatusBadge status={receipt.workflow_stage_status || receipt.status || receipt.ai_status} />
```

**Prioritet:**
1. **workflow_stage_status** (senaste stage från workflow_stage_runs) ⭐ **FÖRST**
2. `status` (unified_files.ai_status) - fallback
3. `ai_status` (samma som status) - fallback

**Exempel på UI-visning:**

| Backend returnerar | Frontend visar |
|-------------------|----------------|
| `src_fc running` | **FC-uppladdning - pågående** (blå) |
| `fc_parse succeeded` | **FC-parsing - klar** (grön) |
| `resume_dispatch running` | **Återupptar - pågående** (blå) ⭐ |
| `restart_dispatch running` | **Omstartar - pågående** (blå) ⭐ |
| `ai5 running` | **Kortmatchning - pågående** (blå) |
| `finalize_ok succeeded` | **Slutför - klar** (grön) |
| `KLAR succeeded` | **KLAR - klar** (grön) |

---

## Debugging och verifiering

### SQL-queries för debugging

**Visa senaste stages för en fil:**
```sql
SELECT wsr.stage_key, wsr.status, wsr.message, wsr.started_at, wsr.finished_at
FROM workflow_runs wr
JOIN workflow_stage_runs wsr ON wsr.workflow_run_id = wr.id
WHERE wr.file_id = 'DIN_FILE_ID'
ORDER BY wsr.started_at DESC
LIMIT 20;
```

**Visa alla unika stage_keys som använts:**
```sql
SELECT DISTINCT stage_key, COUNT(*) as count
FROM workflow_stage_runs
GROUP BY stage_key
ORDER BY stage_key;
```

**Kolla om resume_dispatch loggas:**
```sql
SELECT stage_key, status, message, started_at
FROM workflow_stage_runs
WHERE stage_key IN ('resume_dispatch', 'restart_dispatch')
ORDER BY started_at DESC
LIMIT 10;
```

---

**Dokumentation skapad:** 2025-11-08
**Av:** Claude Code (Anthropic)
**Version:** 1.0
