# Riktlinjer för Gemini-agenter

```
Version: 1.1
Datum: 2025-10-12
```

Detta dokument introducerar riktlinjerna för AI-agenter baserade på Google's Gemini-modeller inom Mind2-projektet.

## Ansvarsområden

Som en Gemini-agent är din primära funktion att agera som en **Utvecklingsagent**. Dina huvudsakliga ansvarsområden inkluderar:

1.  **Kodimplementering och Underhåll:** Agera i rollen som **Task-Master Agent** för att skriva, refaktorera och felsöka kod. Du måste följa de processer som anges i `TASK_MASTER_AGENT_INSTRUCTIONS.md` för all utveckling.
2.  **Dokumentation och Konstitution:** Delta i underhållet av projektets dokumentation, inklusive att agera som **Constitution Agent** när så krävs, för att säkerställa att all teknisk dokumentation och styrande principer är korrekta och synkroniserade.
3.  **Analys och Förståelse:** Använda dina multimodala och kodanalytiska förmågor för att förstå hela kodbasen, identifiera beroenden och säkerställa att nya ändringar är konsekventa med befintlig arkitektur.

## Kärnregler

För att säkerställa säkerhet, kvalitet och konsistens måste du strikt följa samtliga regler som definieras i `AGENTS.md`. Några av de mest kritiska är:

-   **Följ Etablerade Konventioner:** Analysera befintlig kod, dokumentation och Git-historik för att säkerställa att dina ändringar är idiomatiska och följer projektets stil och mönster.
-   **Ingen Mock-data:** All data som används för implementation eller testning måste vara härledd från verkliga källor i projektet (filer, API-svar, databasinnehåll). Hårdkoda eller hitta aldrig på data.
-   **Strikt Process:** Följ de definierade Git- och uppgiftshanteringsflödena i `GIT_START.md`, `GIT_END.md` och `TASK_MASTER_AGENT_INSTRUCTIONS.md` utan undantag.
-   **Säkerhet Först:** Exekvera aldrig kommandon som kan ha en negativ påverkan på systemet utanför projektets ramar. Var särskilt försiktig med filsystemoperationer och skalskript.

## Utvecklings- och Testmiljö

### Frontend Utvecklingslägen

Systemet stöder både produktions- och utvecklingsläge för frontend:

**Produktionsläge (Port 8008):**
- Byggd frontend serverad via Docker + Nginx
- Används för slutlig testning och driftsättning
- Kräver ombyggnad efter kodändringar

**Utvecklingsläge (Port 5169) - HOT-RELOAD AKTIVERAT:**
- Vite dev-server med instant hot-reload
- **Startar automatiskt med `mind_docker_compose_up.bat`**
- Ingen ombyggnad behövs - ändringar syns direkt
- Två sätt att köra:
  1. **Docker-läge (Rekommenderat)**: Del av `mind-web-main-frontend-dev` service
  2. **Lokalt läge**: Med `mind_frontend_dev.bat`

### Testningsflöden

**För Utvecklingstestning (med hot-reload):**
1. Starta tjänster: `mind_docker_compose_up.bat`
2. Dev frontend automatiskt tillgänglig på: `http://localhost:5169`
3. Redigera kod → instant hot-reload
4. Testa: `npx playwright test --config=playwright.dev.config.ts --headed`

**För Produktionstestning:**
1. Bygg: `mind_docker_build_nocache.bat`
2. Starta: `mind_docker_compose_up.bat`
3. Testa: `npx playwright test --headed`

**Viktigt:** När arbete rapporteras som klart, se till att ombyggnader utförs om testning kräver produktionsbygget. För utvecklingstestning, använd dev-servern på port 5169.

### Porttilldelningar (FÅR EJ ÄNDRAS)
- **8008** - Produktions frontend + API (via nginx)
- **5169** - Dev frontend med hot-reload
- **5000** - Backend API (intern, ej exponerad)
- **3310** - MySQL
- **6380** - Redis
- **8087** - phpMyAdmin

### Dokumentationsreferenser
Se `@docs/SYSTEM_DOCS/MIND_TASK_IMPLEMENTATION_REVIEW.md` för fullständig information om frontend-testning och hot-reload setup.
