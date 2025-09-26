# MIND System Review - 2025-09-23

Detta dokument är en automatisk granskning av Mind2-systemet, genererad 2025-09-23. Syftet är att ge en aktuell överblick över systemets arkitektur, konfiguration och beroenden baserat på en analys av källkoden.

## 1. Systemarkitektur

Systemet följer en microservices-liknande arkitektur som orkestreras med `docker-compose`.

**Huvudkomponenter:**

| Service                  | Image                  | Intern Port | Exponerad Port (Host) | Beskrivning                                                              |
| ------------------------ | ---------------------- | ----------- | --------------------- | ------------------------------------------------------------------------ |
| `nginx`                  | `nginx:1.25`           | 80          | `8008`                | Reverse proxy, serverar frontends och vidarebefordrar API-anrop.         |
| `ai-api`                 | `mind2-ai-api:dev`     | 5000        | -                     | Backend-applikation (Python/Flask) som hanterar affärslogik.               |
| `celery-worker`          | `mind2-ai-api:dev`     | -           | -                     | Asynkron task-hanterare för `ai-api`.                                    |
| `mind-web-main-frontend` | `mind2-admin-frontend:dev` | 80          | -                     | Huvud-frontend (React/Vite) för administration.                          |
| `mysql`                  | `mysql:8`              | 3306        | `3310`                | SQL-databas för persistent lagring.                                      |
| `redis`                  | `redis:7`              | 6379        | `6380`                | Meddelandekö för Celery och potentiell cache.                            |
| `prometheus`             | `prom/prometheus:latest` | 9090        | `9091`                | Insamling av metrics.                                                    |
| `grafana`                | `grafana/latest`       | 3000        | `3003`                | Visualisering av metrics.                                                |

**Kommunikationsflöde:**

1.  Användare ansluter till Nginx på port `8008`.
2.  Nginx serverar antingen `mind-web-main-frontend` (React-appen) eller `mobile-capture-frontend` (statisk HTML/JS).
3.  Frontend-applikationerna gör API-anrop till `/ai/api/`, som Nginx proxyar till `ai-api`-tjänsten på port 5000.
4.  `ai-api` använder `mysql` för datalagring och `redis`/`celery-worker` för att hantera tunga eller tidskrävande operationer asynkront (t.ex. OCR-processning).

## 2. Backend (`ai-api`)

*   **Ramverk:** Flask (Python)
*   **Applikationsserver:** Gunicorn
*   **Beroenden:** `flask`, `celery`, `redis`, `mysql-connector-python`, `prometheus-client`. (Se `requirements.txt` för fullständig lista).
*   **Databas:** Använder `mysql-connector-python`. Migreringar hanteras via `.sql`-filer i `database/migrations/`.
*   **API-struktur:** API:et är modulärt och använder Flask Blueprints för att separera olika domäner som `receipts`, `auth`, `export`, etc.
*   **Autentisering:** JWT-baserad autentisering implementerad i `api/auth.py`.
*   **Konfiguration:** Laddas från miljövariabler, enligt definition i `.env.example`.

## 3. Frontend (`mind-web-main-frontend`)

*   **Ramverk:** React 18.3.1
*   **Byggverktyg:** Vite 5.4.0
*   **Styling:** TailwindCSS
*   **Beroenden:** `react`, `react-router-dom`, `chart.js`. (Se `main-system/app-frontend/package.json` för fullständig lista).
*   **Testning:** End-to-end-tester med Playwright.

## 4. Databasschema

Databasschemat är definierat i `database/migrations/`. Några av de centrala tabellerna är:

*   `unified_files`: Huvudtabell för alla typer av filer (kvitton, etc.).
*   `file_tags`: Taggar kopplade till filer.
*   `ai_processing_queue`: Kö för AI-bearbetning.
*   `invoice_documents` & `invoice_lines`: Tabeller för att hantera fakturor och deras rader.
*   `ai_accounting_proposals`: Förslag från AI för bokföring.

## 5. Nätverk & Konfiguration

*   **Nginx (`nginx.conf`):**
    *   Proxy-pass för `/ai/api/` till `http://ai-api:5000/`.
    *   Proxy-pass för `/` till `http://mind-web-main-frontend:80/`.
    *   Serverar en statisk applikation under `/capture/`.
*   **Miljövariabler (`.env.example`):**
    *   `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS` för databasanslutning.
    *   `REDIS_HOST`, `REDIS_PORT` för Redis-anslutning.
    *   `JWT_SECRET_KEY` för att signera JWT-tokens.
    *   `ALLOWED_ORIGINS` för CORS-policy.

## Sammanfattning av granskning

Systemet är välstrukturerat med en tydlig separation mellan backend, frontend och databastjänster. Användningen av Docker och Docker Compose förenklar utveckling och driftsättning. Koden är modulär, särskilt i backend där Flask Blueprints används effektivt.

Denna granskning ligger till grund för uppdateringen av den övriga systemdokumentationen.
