0) Scoperegler (för agenten)

✅ Gör endast detta:

Lägg till DB-kolumner för prompt/response (se 1)

Uppdatera log-insert (ai_logging) + wrapper (_history) (se 2)

Sluta skriva prompt/response in i log_text i pipeline-tasker (se 3)

Utöka GET /receipts/<rid>/log med latest=1 + returnera prompt/response (se 4)

UI: Visa endast senaste, checkbox för prompt, copy-button, ingen truncation (se 5)

Uppdatera SoT med de nya kolumnerna + endpoint-param (se 6)

🚫 Rör INTE:

affärslogik i AI-stegen

matchning/kontering/validering

workflow-engine, statusmodeller, övriga endpoints

tabeller som inte berör loggning

1) Databas: schemaförslag + migration (krav #1 och #5)
1.1 Nya kolumner i ai_processing_history

Minsta som löser krav:

prompt_text LONGTEXT NULL

response_text LONGTEXT NULL

Varför LONGTEXT: prompts och svar kan överskrida TEXT (64KB). Detta löser kravet “aldrig kapa”.

Migration (ny fil)

Skapa ny migration:
database/migrations/0045_add_prompt_and_response_to_ai_processing_history.sql
(0044 finns redan; nästa är 0045)

-- 0045_add_prompt_and_response_to_ai_processing_history.sql
-- Purpose: Store full AI prompt and raw response separately (improves UI readability and prompt calibration).
-- Notes:
-- - LONGTEXT is used because prompts/responses can exceed TEXT (64KB).
-- - Existing log_text remains as a short human-readable summary (no prompts embedded).

ALTER TABLE ai_processing_history
  ADD COLUMN prompt_text LONGTEXT NULL COMMENT 'Full prompt text used for this AI call (snapshot)';

ALTER TABLE ai_processing_history
  ADD COLUMN response_text LONGTEXT NULL COMMENT 'Full raw AI response text returned by provider (snapshot)';


Scopad: inga nya index krävs.

2) Backend: central loggning (krav #1)
2.1 Uppdatera central insert: backend/src/services/ai_logging.py
Problem idag

INSERT_HISTORY_SQL har bara log_text. Allt pressas in där.

Mål

Behåll log_text som kort summary (läsbart i UI)

Lägg prompt och respons i egna fält

Kodförslag (princip)

Ändra:

INSERT_HISTORY_SQL så den även skriver prompt_text, response_text

log_ai_call(...) får två nya optional-parametrar och skickar dem i tuple

Viktigt: Gör det bakåtkompatibelt (alla gamla callsites ska fungera).

Pseudo-exakt struktur:

INSERT_HISTORY_SQL = """
    INSERT INTO ai_processing_history
    (file_id, job_type, status, ai_stage_name, log_text, error_message,
     confidence, processing_time_ms, provider, model_name,
     prompt_text, response_text)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


och i log_ai_call(...):

def log_ai_call(..., model_name=None, prompt_text=None, response_text=None, *, cursor=None) -> bool:
    ...
    cur.execute(INSERT_HISTORY_SQL, (..., model_name, prompt_text, response_text))

2.2 Uppdatera wrappern: backend/src/services/tasks/history.py

Den här filen är en tunn wrapper _history(...) som forwardar till log_ai_call(...). Lägg till prompt_text och response_text här också, så hela kedjan stödjer separationen.

3) Backend: stoppa “prompt+response i log_text” (krav #1, #3, #5)
3.1 Var sker blandningen idag?

AI1–AI4: backend/src/services/tasks/ai_pipeline_tasks.py
Bygger log_parts som:

"--- PROMPT ---\n{aiX_prompt}"

"--- RAW RESPONSE ---\n{raw_response}"

joinas med "; " → oläsligt

AI6: backend/src/services/tasks/workflow_tasks.py
Samma mönster.

Dessutom finns “... +N more” i pipeline-linjer (krav #5).

3.2 Vad ska göras istället?

log_text ska endast innehålla kort summary (t.ex. klassificering, antal rader, varningar)

prompt och respons ska aldrig skrivas in i log_text

all truncation tas bort (ingen slicing [:4000])

inga “... +N more” som låtsas visa data

Konkreta ändringar i ai_pipeline_tasks.py

I AI1/AI2/AI3/AI4:

ta bort prompt/råresponsraderna ur log_parts

behåll summary som är kort och skannbar

ersätt “... +N more” med explicit “Sample (first N)” utan att signalera att texten “kapats mitt i”

Exempel på AI3:

idag: items_summary.append(f"... +{...} more")

ändra till:

Sample items (first 3): [...]

Items: {item_count} total

Exempel på AI4 proposals:

idag: proposal_details.append(f"... +{...} more")

ändra till:

Sample proposals (first 5): [...]

Proposals: {proposal_count} total

Konkreta ändringar i workflow_tasks.py (AI6)

ta bort prompt/raw response ur _history(... log_text=...)

log_text: “Successfully parsed ...”, “Lines: N”, ev confidence

4) Backend: endast senaste loggen till modalen (krav #2)
4.1 Var ligger endpointen?

backend/src/api/receipts.py
@receipts_bp.get("/receipts/<rid>/log") → get_receipt_log(...)

Den returnerar idag:

workflow_runs: alla körningar (desc)

ai_history: allt för relaterade file_ids (asc)

files: unified_files info

4.2 Implementera latest=1

Behåll endpointen, men lägg till query-param:

GET /ai/api/receipts/<rid>/log?latest=1

När latest=1:

returnera endast senaste workflow_run (+ dess stage_runs)

filtrera ai_processing_history så det bara innehåller poster som hör till senaste körningen

Robust men ändå hårt scoppat sätt (utan ny FK)

Eftersom ai_processing_history saknar workflow_run_id, gör så här:

Hämta senaste workflow_runs.created_at (körningens starttid)

Filtrera ai_processing_history.created_at >= latest_run_created_at

Detta är scoppat och kräver ingen omdragning i pipeline.

4.3 Returnera prompt/response i payload

Utöka SQL SELECT för ai_history:

Lägg till:

prompt_text

response_text

och returnera dem som fält i ai_history entries.

5) Frontend: modal UX (krav #2, #3, #4, #5)
5.1 Var finns log-modal?

main-system/app-frontend/src/ui/pages/Process.jsx

Den gör:

api.fetch(/ai/api/receipts/${receiptId}/log)

Renderar workflow_runs + ai_history + files

AI-history visar entry.log_text och entry.error_message

5.2 Ändringar i fetch

Ändra fetch så den alltid använder latest:

const res = await api.fetch(`/ai/api/receipts/${receiptId}/log?latest=1`)

5.3 Checkbox “Visa prompts” (default OFF)

Lägg till state i komponenten:

const [showPrompts, setShowPrompts] = React.useState(false)

I modalen topp:

checkbox med label Visa prompts

Beteende:

om OFF: promptfält renderas inte alls

om ON: visa entry.prompt_text i egen sektion

5.4 Knapp “Kopiera allt”

I modal-toppen:

knapp “Kopiera allt”

bygger en lång text sträng:

inkluderar alltid summary (log_text + error_message)

inkluderar response_text alltid (rekommenderat) eller enligt era preferenser

inkluderar prompt_text endast om checkbox är ON

navigator.clipboard.writeText(...)

OBS: kopian ska inte truncas. Använd hela strängen.

5.5 Ingen truncation i UI

Rendera prompt/response som <pre> med scroll (maxhöjd).
Undvik komponenter som “foldar” arrays/objekt med “... more”. Ni gör redan enkel text, så det är okej – bara visa hela prompt_text/response_text som sträng.

6) SoT-uppdateringar (måste göras i samma PR)
6.1 docs/source_of_truth/40_DATA_MODEL.md

Uppdatera tabellen ai_processing_history och lägg till två rader:

prompt_text | longtext | YES | NULL | Full prompt text used for this AI call

response_text | longtext | YES | NULL | Full raw response returned by provider

Behåll log_text men ändra kommentar (om ni vill) till “Short human readable summary”.

6.2 docs/source_of_truth/55_API_AND_ENDPOINTS.md

Receipts log endpoint dokumenteras (den saknas idag):

GET /ai/api/receipts/{rid}/log?latest=1

nämn att latest=1 returnerar endast senaste workflow_run + ai_history efter run start

nämn att ai_history inkluderar prompt_text, response_text

7) Verifiering (agentens checklista)
7.1 DB

Migrering körd

DESCRIBE ai_processing_history visar prompt_text, response_text

7.2 Backend logging

Kör en pipeline på ett kvitto

Verifiera att:

log_text är kort och inte innehåller prompt eller raw response

prompt_text innehåller full prompt

response_text innehåller full raw response

inga slices [:4000] kvar

7.3 Endpoint

GET /ai/api/receipts/<rid>/log?latest=1 returnerar:

workflow_runs.length === 1

ai_history begränsad till senaste körningen

entries har prompt_text och response_text

7.4 UI

Öppna log-modalen i Process

Default: prompts syns inte

Checkbox ON: prompts syns

Copy: klistrar in allt i ett stycke; respekterar checkbox

Inga “... +N more” i texten som presenteras
8) Extra: Ett litet men viktigt “anti-dumhet”-skydd

För att agenten inte ska råka “lösa” detta genom att gömma texten istället för att separera den:

Förbjud att prompt/response hamnar i log_text (kodreview-regel)

log_text ska alltid vara ≤ några rader i normalfall

prompt/response ska alltid vara i egna fält