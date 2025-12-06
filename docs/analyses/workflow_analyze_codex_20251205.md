# Kö-återuppta felsökning – 2025-12-05 (Codex)

## Vad knappen gör idag
- Frontend (`main-system/app-frontend/src/ui/pages/Queue.jsx`) anropar `POST /ai/api/ingest/process/<file_id>/resume` och laddar om kön var 5:e sekund.
- API-svaret kommer från `resume_processing` i `backend/src/api/ingest.py`.
- `GET /ai/api/queue/` (`backend/src/api/queue.py`) bygger listan och märker ett objekt som `stalled` när `status ∈ {queued, running}` och `updated_at` är äldre än 300 s.

## SoT-krav som berör flödet
- AI-status får endast vara `{uploaded, processing, ocr_done, ocr_failed, manual_review, completed, failed}` enligt `docs/source_of_truth/30_STATUS_MODEL.md` (AI Status-tabellen).
- Workflow-run/status ska följa state diagrammen i samma SoT-fil: `queued → running → succeeded|failed|canceled`. Stage-statusar ska uppdateras löpande.

## Huvudorsaker till att filer fastnar som “Stalled running”
1) **Resume dispatchar aldrig workflow**  
   - `resume_processing` loggar ett stage (`log_import_event("resume_dispatch", status="running")`) men det finns inget efterföljande anrop till `dispatch_workflow(...)` (slutar vid return, `backend/src/api/ingest.py:323-352`).  
   - Därmed skapas ingen Celery-kedja, `workflow_stage_runs` uppdateras inte vidare och `workflow_runs.updated_at` står still efter några minuter → flaggas som stalled i `/queue`.

2) **AI-status bryter mot SoT och uppdateras inte vid återuppta**  
   - När en ny workflow_run skapas vid resume sätts `ai_status` till `"queued"` (`backend/src/api/ingest.py:305`), vilket inte är en tillåten AI-status i SoT.  
   - Om en befintlig run återanvänds uppdateras inte `ai_status` alls, så UI-fältet “AI-status” kan ligga kvar på t.ex. `failed` eller `manual_review` även efter att användaren tryckt “Lås upp/Återuppta”.

3) **Stalled-flaggan mäts mot `workflow_runs.updated_at` men inga nya heartbeat‑uppdateringar sker**  
   - Efter resume sätts `workflow_runs.status='queued'` och `current_stage='resume_dispatch'` (`backend/src/api/ingest.py:307-318`), men utan dispatch körs inga `mark_stage(...)` anrop som normalt skulle uppdatera `workflow_runs.updated_at` (se `mark_stage` i `backend/src/services/tasks/workflow_base.py:157-219`).  
   - Efter 300 s passerar `idle_seconds`‑gränsen i `/queue` och raden markeras som `stalled` trots att användaren försökt återuppta.

## Konsekvens
- “Lås upp/Återuppta” ger ingen faktisk fortsättning av processen; statusfältet för steg stannar på `resume_dispatch running` eller tidigare steg, AI-status förblir felaktig och kön fortsätter visa “Stalled running/queued”.
- Statusmodellen i SoT bryts (otillåten AI-status `queued`), vilket riskerar fel i andra vyer som använder `ai_status` som fallback.

## Rekommenderade åtgärder (måste följa SoT)
1) Lägg till ett omedelbart anrop till `dispatch_workflow(workflow_run_id)` i `resume_processing` efter att `resume_dispatch`-steget loggats, så att pipeline återstartas och statusar uppdateras vidare.  
2) Byt AI-status vid återuppta till den SoT-giltiga övergången `processing` (både när befintlig run återanvänds och när ny skapas) istället för `queued`.  
3) Säkerställ att `workflow_runs.status` sätts till `running` när dispatchen triggas, så att UI:s färgkodning följer SoT och idle-mätningen reflekterar verklig aktivitet.

## Spårbarhet
- Frontend-anrop och UI-beteende: `main-system/app-frontend/src/ui/pages/Queue.jsx`.
- Resume-endpoint och felande dispatch: `backend/src/api/ingest.py:220-352`.
- Stalled-beräkning i kön: `backend/src/api/queue.py:15-120`.
- SoT-statusdefinitioner: `docs/source_of_truth/30_STATUS_MODEL.md` (AI-status och Workflow Run/Stage Status).
