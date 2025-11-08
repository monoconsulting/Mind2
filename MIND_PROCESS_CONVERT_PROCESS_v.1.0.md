# MIND Process Convert – Processbeskrivning v1.0

## Översikt

Konverteringsprocessen hanterar alla inkommande PDF-dokument som måste brytas ned till bildsidor innan vidare OCR- och AI-behandling. Två huvudsakliga inträden finns i backend:

1. `services.tasks._ensure_creditcard_pages_and_ocr` – används av WF3-flödet för First Card-fakturor.
2. `services.tasks.wf2_prepare_pdf_pages` – generellt WF2-flöde för övriga PDF:er.

I båda fallen används `services.pdf_conversion.pdf_to_png_pages` (PyMuPDF/`fitz`) för att skapa 300 dpi PNG-sidor i katalogen `storage/converted/<file_id>/`. Resultatet persisteras i tabellen `unified_files` och nedströms OCR triggas omgående.

## Detaljerade steg (WF3 – kreditkortsfakturor)

1. **Initiering & cachekontroll**  
   - Funktion: `_ensure_creditcard_pages_and_ocr`  
   - Logg: `convert.creditcard.cached_result` (vid återanvändning av sparad text) samt `_history(.., status="skipped")`.

2. **Metadata-synk**  
   - Säkerställer att föräldrafilen har `file_type=cc_pdf` och barn `file_type=cc_image`.  
   - Logg: `convert.creditcard.ensure_state` med nuvarande sidantal.

3. **Beslut: konvertera eller återanvänd**  
   - Om sidor saknas och källan är PDF fortsätter flödet, annars:
     - icke-PDF → logg `convert.creditcard.single_image_source` + `_history(..., status="skipped")`.
     - befintliga sidor → logg `convert.creditcard.pages_reused` + `_history(..., status="skipped")`.

4. **Läs originalfil**  
   - Bygger sökväg i `storage/originals`.  
   - Logg: `convert.creditcard.conversion_start` med filnamn och lagringssökväg.

5. **Konvertering till PNG**  
   - Tidstagning med `time.perf_counter`.  
   - Vid duplicerade sidor loggas `convert.creditcard.page_duplicate` innan befintlig sida hämtas.  
   - Vid fel loggas `convert.creditcard.conversion_failed` och `_history(..., status="error")` med felmeddelande.

6. **Persistens av nya sidor**  
   - Varje sida får ny `file_id`, `insert_unified_file` och `FileStorage.adopt`.  
   - Vid lyckad körning loggas `convert.creditcard.conversion_succeeded` + `_history(..., status="success")` inklusive lista över `page_ids` och arbetstid.

7. **OCR per sida**  
   - För varje sida körs `services.ocr.run_ocr`.  
   - Loggar:  
     - `convert.creditcard.page_ocr_completed` (innehåller antal tecken), eller  
     - `convert.creditcard.page_ocr_empty` om OCR saknar text.  
   - För icke-PDF fallback används `convert.creditcard.single_ocr_completed` respektive `single_ocr_empty`.

8. **Sammanställning av OCR-text**  
   - Texten sparas i `other_data["combined_ocr_text"]`.  
   - Loggar:  
     - `convert.creditcard.ocr_completed` med totalt tecken.  
     - `convert.creditcard.ocr_empty` om ingen text extraherades.  
   - Filstatus uppdateras till `ocr_done`.

## Detaljerade steg (WF2 – generella PDF:er)

1. **Initiering**  
   - Funktion: `wf2_prepare_pdf_pages`.  
   - Logg: `convert.wf2.prepare_start` med fil-id, mime och filtyp.  
   - Ogiltiga typer loggas som `convert.wf2.prepare_failed` innan tidig avbrytning.

2. **Läs originalfil**  
   - Som i WF3 men utan sidcaching.  
   - Logg: `convert.wf2.read_original` med källfil och sökväg.

3. **Konvertering**  
   - Starttid sparas i `conversion_started`.  
   - Efter `pdf_to_png_pages` skapas per-sida-objekt i `unified_files`.  
   - Lyckad konvertering loggas via `convert.wf2.conversion_succeeded` och `_history(..., status="success")`.  
   - Fel (inklusive `DuplicateFileError`) loggas genom `convert.wf2.conversion_failed` och `_history(..., status="error")` med varaktighet.

4. **Uppdatera metadata**  
   - `other_data.page_count` och `other_data.pages` uppdateras.  
   - Logg: `convert.wf2.prepare_succeeded`.

5. **Triggning av OCR**  
   - Celery `group` + `chord` startas för sidvisa OCR-jobb.  
   - Logg: `convert.wf2.ocr_dispatched` med sidantal.

6. **Efterföljande steg**  
   - `wf2_run_page_ocr` och `wf2_merge_ocr_results` hanterar OCR-utfall och sparar `combined_ocr_text`. Dessa har redan detaljerad logik via `mark_stage`, men kompletteras nu av historikposten från konverteringen.

## Historikloggning (`ai_processing_history`)

| Scenario | Funktion | Status | Loggtext (exempel) |
|----------|----------|--------|--------------------|
| Konvertering lyckas (WF3/WF2) | `_ensure_creditcard_pages_and_ocr` / `wf2_prepare_pdf_pages` | `success` | `Converted ... page_ids=['...']` |
| Konvertering skippas (icke-PDF, cache eller återanvändning) | `_ensure_creditcard_pages_and_ocr` | `skipped` | `Skipped PDF conversion ...` |
| Konvertering misslyckas | Båda | `error` | `Failed to convert ...` respektive `WF2 PDF conversion failed.` |
| Dubblettsidor (WF3) | `_ensure_creditcard_pages_and_ocr` | – | Loggas som event `convert.creditcard.page_duplicate` medan processen återanvänder befintlig sida (ingen historikpost skapas). |

Alla poster använder `job_type="pdf_convert"`, `ai_stage_name="PDF-Conversion"`, `provider="pymupdf"` och `model_name="fitz-dpi-300"`. `processing_time_ms` fylls automatiskt när varaktighet finns.

## Loggevent-översikt

| Event | Beskrivning |
|-------|-------------|
| `convert.creditcard.cached_result` | OCR-data fanns redan, ingen konvertering behövs. |
| `convert.creditcard.ensure_state` | Sammanfattning av initialt läge för kreditkortsfakturor. |
| `convert.creditcard.conversion_start` / `conversion_succeeded` / `conversion_failed` | Start, lyckad respektive misslyckad konvertering. |
| `convert.creditcard.page_duplicate` | Befintlig sidbild återanvänds efter `DuplicateFileError`. |
| `convert.creditcard.single_image_source` / `pages_reused` | Grenar där konvertering inte körs. |
| `convert.creditcard.page_ocr_completed` / `page_ocr_empty` | OCR-resultat per sida. |
| `convert.creditcard.single_ocr_completed` / `single_ocr_empty` | OCR-resultat för icke-PDF. |
| `convert.creditcard.ocr_completed` / `ocr_empty` | Sammanställd OCR-text för hela dokumentet. |
| `convert.wf2.prepare_start` / `prepare_failed` | Start respektive valideringsavbrott för WF2. |
| `convert.wf2.read_original` | Originalfil läses från lagring. |
| `convert.wf2.conversion_succeeded` / `conversion_failed` | Resultat av WF2-konvertering. |
| `convert.wf2.prepare_succeeded` | Metadata uppdaterad efter lyckad konvertering. |
| `convert.wf2.ocr_dispatched` | OCR-uppgifter köade. |

Samtliga event skrivs genom `observability.events.log_event` som producerar JSON-strukturerade loggar kompatibla med befintligt monitoreringsstack.

## Fil- och lagringsstruktur

| Mapp | Innehåll |
|------|----------|
| `storage/originals/<file_id>.pdf` | Ursprunglig uppladdad PDF. |
| `storage/converted/<file_id>/<file_id>_page_XXXX.png` | Renderade 300 dpi PNG-sidor. |
| `unified_files` | Metadata och referenser till både ursprungsfil och sidbilder. |
| `ai_processing_history` | Tidsstämplade historikrader för konverteringsutfall. |

## Felhantering

- Alla kritiska undantag vid konvertering bubblas upp efter att logg och historik skrivits. Workflow-steg (`mark_stage`) sätter status till `failed`.
- För WF3 hanteras redan existerande sidor genom återanvändning; processen fortsätter utan att kasta fel.
- För WF2 betraktas duplicerade sidor som irreparabla i denna fas och steget misslyckas (kräver manuell hantering).

---

Version 1.0 skapad 2025-11-06. Uppdatera denna fil när nya loggsteg eller flödesförändringar införs.
