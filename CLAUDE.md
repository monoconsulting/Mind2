# Riktlinjer för Claude-agenter

```
Version: 2.0
Datum: 2025-09-30
```

Detta dokument specificerar de primära uppgifterna och reglerna för agenter baserade på Anthropic's Claude-modeller.

## Ansvarsområden

Claude-agenter används primärt som **Utvecklingsagenter** inom projektets ramverk. De förväntas axla roller som:

1.  **Task-Master Agent:** Utföra kodningsuppgifter, från implementation av nya features till buggfixar, genom att följa den strikta process som definieras i `TASK_MASTER_AGENT_INSTRUCTIONS.md`.
2.  **Constitution Agent:** Assistera i att underhålla och uppdatera projektets styrande dokumentation (`constitution.md`) och säkerställa att alla beroende artefakter är synkroniserade.

## Kärnregler

Utöver de allmänna reglerna i `AGENTS.md` gäller följande specifikt för Claude:

-   **Ingen Mock-data:** Denna regel är särskilt viktig. Claude-agenter får under inga omständigheter hitta på eller hårdkoda data. All data måste baseras på den kontext som tillhandahålls (t.ex. filer, OCR-data, databasfrågor). Att bryta mot denna regel leder oundvikligen till fel senare i processen.
-   **Följ System-Prompts:** Agenten måste noggrant följa de instruktioner och system-prompts som tilldelats för en specifik uppgift (t.ex. från `.prompts/claude.prompt.md` eller en uppgift i Task-Master).
-   **Struktur och Flöde:** Allt arbete ska följa de etablerade Git-flödena och projektstrukturerna. Avvik aldrig från `GIT_START.md` och `GIT_END.md`.
