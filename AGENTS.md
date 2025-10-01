# Översikt över Agenter i Mind2-projektet

```
Version: 2.0
Datum: 2025-09-30
```

Detta dokument beskriver de olika typerna av AI-agenter som används i projektet och de grundläggande reglerna de måste följa.

## Huvudtyper av Agenter

Projektet använder huvudsakligen två kategorier av agenter:

1.  **Pipeline-agenter:** Automatiserade agenter som exekverar en specifik del av AI-pipelinen för dokumentanalys.
2.  **Utvecklingsagenter:** Agenter som utför uppgifter relaterade till kodning, dokumentation och projektstyrning (t.ex. "Task-Master").

### 1. AI-Pipeline Agenter

Dessa agenter hanterar kvitton och fakturor i en sekventiell process. Varje steg är ett anrop till en dedikerad AI-tjänst.

-   **AI1: Dokumentklassificering:** Identifierar om ett dokument är ett kvitto, en faktura eller "annat".
-   **AI2: Utläggsklassificering:** Avgör om ett utlägg är privat eller ett företagsutlägg (via kort).
-   **AI3: Dataextrahering:** Plockar ut strukturerad data såsom datum, belopp, moms, organisationsnummer och enskilda kvittorader.
-   **AI4: Konteringsförslag:** Föreslår bokföringskonton baserat på extraherad data och gällande BAS-kontoplan.
-   **AI5: Kreditkortsmatchning:** Matchar kvittot mot en korresponderande kreditkortstransaktion.

Resultatet från varje steg lagras i databasen och styr nästa steg i processen.

### 2. Utvecklingsagenter

Dessa agenter interagerar med kodbasen för att implementera nya funktioner, fixa buggar och underhålla projektet.

-   **Task-Master Agent:** Huvudagenten för utveckling som följer en strikt workflow för Git-hantering och uppgiftsindelning enligt `TASK_MASTER_AGENT_INSTRUCTIONS.md`.
-   **Constitution Agent:** En specialiserad agent ansvarig för att upprätthålla projektets "konstitution" (`.specify/memory/constitution.md`) och säkerställa att andra mallar och dokument är synkroniserade med denna.

## Allmänna Regler för Alla Agenter

Alla agenter, oavsett typ, måste strikt följa dessa regler:

-   **Ingen Mock-data:** Det är absolut förbjudet att introducera fejkad eller hårdkodad data. All data ska härledas från källan (t.ex. OCR-text) eller databasen.
-   **Ingen SQLite:** Användning av SQLite är inte tillåtet. Projektet använder en centraliserad databasserver.
-   **Testning:** Tester måste utföras exakt enligt instruktionerna i `@docs/TEST_RULES.md`.
-   **Porthantering:** Ändra aldrig en port eller tilldela en ny utan att först be om lov. Användning av `taskkill` för att stänga en upptagen port är strikt förbjudet.
-   **Konfiguration:** Redigera aldrig `playwright.config.ts` utan uttrycklig order.
-   **Workflow:** Följ alltid de specificerade Git-flödena som beskrivs i `GIT_START.md` och `GIT_END.md`.

## Teknisk Översikt

Denna sektion beskriver systemets arkitektur, API:er och arbetsflöden.

### Systemarkitektur och Start av Tjänster

Systemet är container-baserat och orkestreras med `docker-compose`. De centrala tjänsterna är:

-   `ai-api`: Flask-applikationen som exponerar REST API:et för all AI-logik.
-   `celery-worker`: Bakgrundarbetare som asynkront exekverar tunga uppgifter, framför allt OCR och AI-pipeline-stegen.
-   `nginx`: Fungerar som en reverse proxy och serverar de olika frontend-applikationerna.
-   `mysql`: Databasen för all persistent data.
-   `redis`: Används som meddelandekö (message broker) för Celery.

**Starta systemet:**

För att starta hela systemet, kör följande kommando från projektets rotmapp:

```bash
docker-compose --profile main up
```

Detta startar alla kärntjänster som krävs för applikationen. För monitorering kan profilen `monitoring` användas.

### AI API Endpoints

AI-funktionaliteten exponeras via ett REST API under prefixet `/ai`. Alla anrop kräver autentisering. De centrala endpoints som utgör AI-pipelinen är:

-   `POST /ai/classify/document`: **(AI1)** Klassificerar dokument (kvitto, faktura, etc.).
-   `POST /ai/classify/expense`: **(AI2)** Klassificerar typ av utlägg (privat/företag).
-   `POST /ai/extract`: **(AI3)** Extraherar strukturerad data från dokumentet.
-   `POST /ai/classify/accounting`: **(AI4)** Föreslår kontering.
-   `POST /ai/match/creditcard`: **(AI5)** Matchar kvittot mot kreditkortstransaktioner.

Utöver dessa finns även:

-   `POST /ai/process/batch`: För att manuellt trigga hela pipelinen för en lista med filer.
-   `GET /ai/status/<file_id>`: För att hämta aktuell AI-status för en specifik fil.

### Arbetsflöde och Triggers

AI-pipelinen kan triggas på två huvudsakliga sätt:

1.  **Automatiskt (via Celery):**
    -   När en ny fil laddas upp till systemet (t.ex. via FTP eller ett annat API), skapas en uppgift för OCR-bearbetning (`process_ocr`).
    -   När `process_ocr` är klar och lyckas, köar den automatiskt en ny uppgift, `process_ai_pipeline`, som exekverar stegen AI1-AI5 i sekvens.
    -   Denna asynkrona process hanteras av `celery-worker` och definieras i `backend/src/services/tasks.py`.

2.  **Manuellt:**
    -   Genom att köra skriptet `trigger_ocr.bat`. Detta skript anropar i sin tur `scripts/trigger_ocr_all.py`, som sannolikt initierar OCR-processen för alla relevanta filer i systemet, vilket i sin tur startar AI-pipelinen.
    -   Genom att göra ett direkt anrop till `POST /ai/process/batch` med en lista av fil-ID:n som ska bearbetas.