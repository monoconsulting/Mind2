# Riktlinjer för Gemini-agenter

```
Version: 1.0
Datum: 2025-09-30
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
