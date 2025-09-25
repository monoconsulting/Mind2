<!--
AI INSTRUCTIONS (DO NOT REMOVE)
Syfte: Detta dokument är redigerbart av AI/människor. Följ reglerna:

1) Håll detta dokument som källsanning för hur MIND ska vara uppbyggt (MÅLBILD v2.1) – referera till övriga docs för detaljer.
2) Inga hemligheter: använd plats‑hållare (<set via secrets>), hänvisa till .env.example/sekretshantering.
3) Uppdatera ändringsloggen varje gång du justerar innehållet.
4) Håll docs i synk: PORTS, API-baser, Endpoints, Env vars, Security, Migrations.
5) Om något avviker i koden: uppdatera planen eller flagga blocker i handover.
-->

# Technical Implementation Plan – MIND + AI (v2.1, 2025-09-23)

## Changelog

| Version | Datum      | Förändring |
|---------|------------|------------|
| 2.1.1   | 2025-09-24 | Korrigerade frontend-sökväg från `frontend/` till `main-system/app-frontend/` för att matcha den faktiska kodstrukturen. Uppdaterade design till mörkt tema med röd Mind-branding. |
| 2.1     | 2025-09-23 | Korrigerade sökvägar för backend- och frontend-kod för att matcha den faktiska kodbasen. Flyttade changelog till toppen. |
| 2.0     | 2025-09-19 | MÅLBILD utan PHP: ren Python‑stack, kanoniska migrationer (unified→ai→invoice), endpoints och portar uppdaterade; deprecations tydliggjorda |
| 1.0     | 2025-09-18 | Python‑admin/AI beskrivet; kvar fanns PHP‑delar i överblicken |

---

Status: MÅLBILD v2.1 är en ren Python-baserad admin/AI‑stack. Alla administrativa endpoints och processflöden körs i Flask + Celery mot MySQL. Legacy PHP (UI + API + phpMyAdmin) ingår inte i MÅLBILDEN och ska inte användas i nya flöden.

Se även referensdokumenten i `docs/SYSTEMDOCS/`:
- MIND_PORTS.md (portledger; markera PHP som deprecated i nästa uppdatering)
- MIND_API_BASES.md (service-URL:er för /ai/api)
- MIND_ENDPOINTS.md (kanonisk endpoint‑inventering för Python‑backend)
- MIND_ENV_VARS.md (miljövariabler för ai-api/celery)
- MIND_MIGRATIONS.md (kanonisk migrationskedja: unified → ai → invoice)
- MIND_OBSERVABILITY.md (övervakning/metrics) och VERIFICATION_CHECKLIST.md (slutkontroll)

## 1. Systemöversikt

| Lager | Komponenter | Syfte |
|-------|-------------|-------|
| Presentation | Admin SPA (Nginx, port 8008), Vite dev (5176) | Intern admin/analys‑GUI kopplad mot `/ai/api` |
| API & Logik | Flask `ai-api` (intern 5000, proxas via `/ai/api`) | Systemstatus, kö, kvitton, FirstCard, analytics |
| Asynkron | Celery worker(s) + Redis | OCR, klassificering, faktura‑OCR, matchning, historik |
| Data | MySQL (`mono_se_db_9`), filvolymer (`docker/receipts_raw`) | `unified_files`, `ai_*`, `invoice_*`, `tags/file_tags` |
| Observability | Prometheus, Grafana, exporters | Hälsa, KPI, ködjup/latens, DB/Redis‑metrics |

Ej i MÅLBILD v2.1: PHP UI/API, phpMyAdmin. Dessa är utfasade/legacy och ska inte refereras i nya flöden eller dokumentation (förutom som deprecation‑notiser).

## 2. Nätverk & portar (sammanfattning)

Detaljerad tabell finns i `MIND_PORTS.md`. För v2.1 gäller:
- Admin SPA: `127.0.0.1:8008` (Nginx, endast frontend). 
- AI‑API (Flask): internt `ai-api:5000`, nås via proxy på `/ai/api`.
- MySQL: `127.0.0.1:3310` → container 3306.
- Redis: `127.0.0.1:6379` (endast vid behov i dev).
- Monitoring: Prometheus `9091`, Grafana `3003`, övriga exporters enligt profil `monitoring`.

Deprecated i v2.1: `8004` (PHP UI), `8009` (PHP API), `8087` (phpMyAdmin). Dessa ska vara avstängda i huvudprofilen och markerade som deprecated i portledgern.

## 3. Tjänsteöversikt

| Tjänst | Container | Kod | Notis |
|--------|-----------|-----|-------|
| AI/API | `ai-api` | `backend/src/api/` | Servar alla administrativa/AI‑endpoints via `/ai/api/*` |
| Worker | `celery-worker` | `backend/src/services/` | Kör `process_ocr`, `process_classification`, `process_invoice_document` m.fl. |
| Redis | `mind-redis` | – | Broker/result backend för Celery |
| MySQL | `mind-mysql` | `database/migrations/*` | Kanonisk schemaordning, se §5 |
| Frontend | `mind-web-main-frontend` | `main-system/app-frontend/` build | Talar endast med `/ai/api` - MÖRKT TEMA med röd Mind-branding |
| Monitoring | `prometheus`, `grafana`, `*-exporter` | `monitoring/*` | Paneler för AI‑pipeline, DB/Redis |

## 4. Dataflöden

1) Ingest: Mobilapp/FTP lämnar filer + metadata. FTP‑importer skriver till `unified_files` (`file_type='receipt'`), sätter statusflaggor och filhash. JSON‑metadata parsas till avsedda fält/`manual_tags` enligt backlog.
2) Kö: API/worker lägger jobb i `ai_processing_queue`. Celery hämtar, kör OCR/klassificering/moderation/objekt/faces och uppdaterar `unified_files` + `ai_processing_history`.
3) Dashboards: `GET /ai/api/system/status`, `/ai/api/system/stats`, `/ai/api/processing/jobs`, `/ai/api/receipts/monthly-summary` läser MySQL/Redis och returnerar verkliga värden.
4) FirstCard: `POST /ai/api/reconciliation/firstcard/import` fyller `invoice_documents` + `invoice_lines`; `.../match` scorer mot kvitton; manuella `confirm/reject` uppdaterar matchstatus och historik.

## 5. Datamodell & migrationer

Kanonisk ordning (se `MIND_MIGRATIONS.md`):
1. `unified-migration-fixed.sql` → `unified_files`, `file_tags` (+ ev. vyer/kompat)
2. `ai_schema_extension.sql` → AI‑kolumner på `unified_files` + `ai_processing_queue`, `ai_models`, `ai_processing_history`
3. `2025_09_18_invoice_schema.sql` → `invoice_documents`, `invoice_lines`, `invoice_line_history`

Principer: Idempotent DDL (`IF NOT EXISTS`), additiv utveckling, rollback via kompensationsskript. Legacy `images`‑spåret är arkiverat och ska inte användas.

## 6. API‑kontrakt (Python)

Bas: internt `http://ai-api:5000/api`, via proxy `/ai/api`.

- Auth: JWT Bearer. CORS via `ALLOWED_ORIGINS`.
- System: `GET /system/status`, `GET /system/stats`, `GET /system/config`, `PUT /system/config`, triggers för `fetcher/ocr`.
- Kö: `GET /processing/jobs`, `GET /processing/jobs/{id}`, `POST /processing/jobs/{id}/{action}`, `DELETE /processing/queue`, `POST /processing/retry-failed`.
- Kvitton: `GET /receipts`, `GET /receipts/{id}`, `PUT /receipts/{id}`, `GET /receipts/monthly-summary`, `GET /receipts/{id}/thumbnail`, `GET /receipts/{id}/image`.
- FirstCard: `POST /reconciliation/firstcard/import`, `POST /reconciliation/firstcard/match`, `POST /reconciliation/firstcard/statements/{id}/confirm`, `.../reject`, `GET /reconciliation/firstcard/statements`.

Källa: `MIND_ENDPOINTS.md` (hålls i synk med `backend/src/api/`). Inga PHP‑endpoints ska dokumenteras i v2.1.

## 7. Miljövariabler (urval)

Se `MIND_ENV_VARS.md` för komplett lista. Centrala värden:
- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
- REDIS_HOST, REDIS_PORT, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- JWT_SECRET_KEY, ALLOWED_ORIGINS, LOG_LEVEL
- AI‑flaggor: `AI_PROCESSING_ENABLED`, `ENABLE_REAL_OCR`

## 8. Säkerhet

- Auth: JWT Bearer i Python‑lagret. Delad nyckel hanteras via secrets.
- CORS: Styrs via `ALLOWED_ORIGINS`; endast admin‑domäner.
- Nätverk: AI‑API exponeras inte på host‑port; nås via proxy.
- Least privilege: Applikationsanvändare i MySQL; `READ ONLY` där det är rimligt.
- Sekretess: Inga verkliga nycklar i kod/dokument – använd `<set via secrets>`.

## 9. Observability

- Prometheus scrapar exporter + AI‑stats via `/ai/api/system/stats`.
- Grafana paneler för: ködjup/latens, OCR‑framgång, felkvoter, DB/Redis.
- Loggning: Strukturerad JSON i Flask/Celery; centralisering möjlig via log‑driver/Loki.

## 10. Dev & release‑workflow

1. Kör migrationskedjan i staging (se §5) före deploy.
2. Starta kärnprofil: `docker compose up --profile main` (+ `--profile monitoring` vid behov).
3. Efter kodändringar: `python -m py_compile backend/src/api/app.py backend/src/services/queue_manager.py`.
4. Uppdatera handover med eventuella blockers och `docs/SYSTEMDOCS` vid schema/endpoint‑ändringar.

## 11. Deprecation (v2.1)

- PHP UI/API och phpMyAdmin är utfasade och ingår inte i MÅLBILD. 
- Frontend ska endast anropa `/ai/api/*`.
- Portar 8004/8009/8087 markeras som deprecated i portledgern och ska inte startas i huvudprofilen.

## 12. Verifiering

Använd `VERIFICATION_CHECKLIST.md` för helhetskontroll. Minimikrav för godkänd v2.1:
- System‑ och köendpoints läser riktiga data från MySQL/Redis.
- Kvittoflöden (lista, detalj, update, monthly‑summary) fungerar mot `unified_files`.
- FirstCard import/match/confirm/reject fungerar mot `invoice_*`.
- Grafana visar AI‑pipeline och systemstatus baserat på Prometheus‑data.

