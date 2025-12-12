# Workflow: PDF receipt conversion stalls after WF2 split (2025-12-10)

## Bakgrund
- Två enkelsidiga kvitto-PDF:er (240820_Elgiganten_2282897372.pdf och 240717_Elgiganten_2252511319.pdf) laddades upp via portal.  
- WF2_PDF_SPLIT kördes och skapade varsin `pdf_page`-post med OCR.  
- Efter WF2 är sidorna kvar med `workflow_type=receipt`, `ai_status=uploaded`, **inga** workflow_runs och ingen AI-historik. En orphan-post (`...page-0001.png`) hänger kvar i kön.  
- Användaren förväntar sig att PDF (även fler-sidiga) ger **en** processlogg och att AI-stegen körs.

## Observationer i kod & data
- `backend/src/api/ingest.py`: alla PDF-er routas till `workflow_key = "WF2_PDF_SPLIT"` och passas vidare som `workflow_type="WF2_PDF_SPLIT"` till `create_unified_file`.  
- `create_unified_file` (db/files.py) skapar workflow_run endast när `create_workflow=True`. För WF2-sidor anges `create_workflow=False`.  
- `wf2_prepare_pdf_pages` (ocr_tasks.py) skapar `pdf_page`-rader med `workflow_type` default `receipt`, `ai_status=uploaded`, men **ingen** workflow_run.  
- `wf2_merge_ocr_results` + `wf2_run_invoice_analysis` avslutar WF2 utan att trigga WF1 eller någon annan pipeline för de skapade sidorna.  
- Databas: `workflow_runs` saknas för `c36772fb-b132-4bc3-b782-bd54483c19e3` och `37023b1e-7f58-46fe-a7f1-58f6151a332f`; `unified_files` visar `workflow_type=receipt`, `ai_status=uploaded`, `other_data.source="wf2_split"`.  
- SoT (`docs/source_of_truth/50_PIPELINES_AND_JOBS.md`) säger WF2_PDF_SPLIT ska splittra och OCR:a sidor; det står inget om att WF2 är slutpunkt. För kvittoflöden (WF1_RECEIPT) krävs AI1–AI4 och workflow_run (WF1).  
- SoT (`30_STATUS_MODEL.md`) kräver att workflow_run sätts till `succeeded`/`KLAR` vid färdigställande – här finns ingen run för sidorna, så de klassas som orphans och stannar i kön.

## Rotorsak
PDF-sidor skapas med `create_workflow=False`, och det finns ingen efterföljande dispatch till WF1. Därmed saknas workflow_runs och AI-steg, vilket lämnar sidorna i `uploaded` och i orphan-listan. WF2 kedjan betraktar sitt jobb som klart utan att koppla kvittosidorna till kvitto-pipelinen.

## Konsekvenser
- Kvitto-PDF:er (även enkelsidiga) fastnar efter OCR; inga AI1–AI4 körs, ingen AI-historik eller statusuppdatering.  
- Orphan-sidor skapar brus i kö/diagnostik och riskerar manuella felhanteringar.  
- SoT-kravet om en sammanhållen processlogg per dokument bryts (endast WF2-logg, ingen kvitto-process).

## Rekommenderad åtgärdsplan
1) **Routingbeslut efter split**  
   - När WF2 är klar och `page_count` > 0: skapa workflow_runs för sidorna (eller parent) och dispatcha till WF1 så att AI1–AI4 körs.  
   - Om kravet är “en loggpost per dokument”: överväg att köra WF1 på **parent-PDF** efter att `combined_ocr_text` satts (kopiera OCR till `ocr_raw` på parent, skapa WF1 workflow_run för parent).  
   - Säkerställ att `workflow_type` i `unified_files` följer SoT (`receipt` / `creditcard_invoice`) medan `workflow_runs.workflow_key` används för WF1/WF2/WF3.

2) **Skapa workflow_run vid sid-skapande (interim säkerhetsnät)**  
   - Sätt `create_workflow=True` för pdf_page när vi vill köra WF1 per sida, och dispatcha direkt till WF1-kedjan.  
   - Spara `pages[*].workflow_run_id` i `other_data` för spårbarhet och diagnos.

3) **Statusuppdateringar**  
   - När WF2 triggar WF1: sätt sidornas `ai_status` till `processing` och uppdatera parent `other_data` med referenser.  
   - Se till att WF1-finalize markerar workflow_run `succeeded`/`KLAR` (SoT 30_STATUS_MODEL).

4) **Orphan-repair script**  
   - Engångsreparation: hitta `unified_files` där `file_type='pdf_page'` AND `ai_status='uploaded'` AND ingen workflow_run; för varje, skapa WF1 workflow_run och dispatcha.  
   - Lägg till diagnostik i queue-view för att flagga pdf_page utan workflow_run och erbjuda batch-resume.

5) **Tests**  
   - Unit: wf2_prepare_pdf_pages should create workflow_runs/dispatch according to chosen strategy; assert `workflow_runs` exists for pages/parent.  
   - Integration/E2E: ladda upp enkelsidig kvitto-PDF -> se att WF1 AI1–AI4 körs och status blir `completed`; loggen visar en sammanhållen kedja.  
   - Regression: fler-sidigt kvitto-PDF -> säkerställ exakt en processlogg (parent) och att alla sidor OCR-resultat inkluderas i AI-steget.

6) **Dokumentation & SoT**  
   - Uppdatera SoT 50_PIPELINES_AND_JOBS.md för att uttryckligen beskriva hur WF2 överlämnar till WF1 för kvittodokument och hur loggningen ska se ut (en post per dokument).  
   - Uppdatera 40_DATA_MODEL.md om nya fält i `other_data` (t.ex. `pages[*].workflow_run_id`) och eventuella statusflöden.

## Data att åtgärda (nuvarande incident)
- Parent PDFs: `88fb3800-94d8-4590-8f9b-f81cb51d609d`, `5917dfea-b724-47d8-85a5-18addf5117be` (WF2 OK).  
- Sidor utan workflow_run: `c36772fb-b132-4bc3-b782-bd54483c19e3`, `37023b1e-7f58-46fe-a7f1-58f6151a332f`, samt orphan `240820_Elgiganten_2282897372.pdf-page-0001.png` (troligen samma ID).  
- Status: `ai_status=uploaded`, `workflow_type=receipt`, `other_data.source="wf2_split"`, inga rader i `workflow_runs`.

## Föreslagen genomförandeordning
1. Besluta modell: WF1 på parent eller per sida (rekommenderar parent för “en loggpost”).  
2. Implementera routing + workflow_run-skapande + dispatch; sätt rätt `workflow_key` / `workflow_type`.  
3. Lägg till migrationsscript/repair script för befintliga pdf_page-orphans.  
4. Uppdatera SoT (50, 40) och ev. runbook.  
5. Skriv/uppdatera tester och kör riktade integrationstester med kvitto-PDF (1p & fler sidor).  
6. Kör batch-resume/repair i miljön och verifiera att AI1–AI4 körs och loggar visas korrekt.

