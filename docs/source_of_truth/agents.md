# ✅ 1. SYSTEM INSTRUCTIONS (GLOBALT BASELINE-DOKUMENT)

> Version: 2025-12-14.1

Denna fil gäller alla agenter och behövs i rotmappen. Namnförslag:

### **`/agents/SYSTEM_GOVERNANCE.md`**

Innehåll:

------

## **Global System Governance – Source of Truth Documentation**

Alla agenter (1, 2 och 3) ska följa dessa regler:

### **A. Principer**

1. Source of Truth (SoT) är den enda sanningen.
2. Alla förändringar i arkitektur, schema, pipelines eller statusar måste dokumenteras i SoT innan eller samtidigt som kodändringar görs.
3. Migreringar, kod och SoT får aldrig vara i konflikt – i konflikt fall ska SoT uppdateras först.
4. Migrations får aldrig skriva över eller radera användardata (t.ex. prompt-innehåll i `ai_system_prompts`) vid omkörning.

### **B. Strukturkrav**

Alla system ska följa strukturen:

```
docs/source_of_truth/
  00_INDEX.md
  10_SYSTEM_OVERVIEW.md
  20_DOMAIN_MODEL_AND_GLOSSARY.md
  30_STATUS_MODEL.md
  40_DATA_MODEL.md
  50_PIPELINES_AND_JOBS.md
  55_API_AND_ENDPOINTS.md
  60_INTEGRATIONS.md
  70_AI_PROMPTS_AND_ROLES.md   (systemspecifikt innehåll)
  80_OPERATIONS_RUNBOOK.md
  90_TEST_AND_QUALITY_STRATEGY.md

docs/wip/
docs/archive/
```

### **C. Konsolideringsprinciper**

1. Inget gammalt dokument får raderas – bara flyttas till `archive/` och märkas som `LEGACY`.
2. Ingen del av SoT får vara tom – allt ska fyllas med verkligt innehåll, inte placeholders.
3. Kod, migrations och databas ska alltid stämma exakt med `40_DATA_MODEL.md`.
4. Statusfält i kod/DB måste existera i `30_STATUS_MODEL.md`, annars är de ogiltiga.
5. Alla pipelines ska ha input/output-kontrakt och felhanteringsregler i `50_PIPELINES_AND_JOBS.md`.

------

# ✅ 2. PROJEKTPLAN FÖR INFÖRANDE AV SOURCE OF TRUTH

Läggs som:

### `/agents/PROJECT_PLAN_SOURCE_OF_TRUTH.md`

------

## **Projektplan – Införande av Source of Truth (SoT) för systemet Mind**

### **Fas 1 – Inventering**

- AI ska lista **alla befintliga dokument**: md, docx, pdf, kodkommentarer, migrations, databasdump.
- För varje dokument:
  - klassificera typ: Översikt, Datamodell, Status, Pipeline, AI, API, Legacy, Övrigt
  - bedöm kvalitet: hög/medium/låg
  - ange vilka SoT-filer dokumentet ska bidra till
- Resultatet sparas i `docs/wip/DOCUMENT_INVENTORY.md`

### **Fas 2 – Konfliktidentifiering**

- Identifiera:
  - dubbla definitioner (status, pipeline, tabeller)
  - motstridiga beskrivningar
  - ej dokumenterad funktionalitet
- Sammanställ i `docs/wip/CONFLICTS_AND_DECISIONS.md`

### **Fas 3 – Konsolidering**

För varje SoT-fil:

| Fil  | Källa                       | Aktivitet                           |
| ---- | --------------------------- | ----------------------------------- |
| 10   | Gamla översikter            | Sammanställ + förenkla              |
| 20   | Domänbegrepp i kod/dokument | Harmoniera begrepp                  |
| 30   | DB, kod, logs               | Matcha samtliga statusar            |
| 40   | Migrations + schema         | Skapa exakt och komplett datamodell |
| 50   | pipeline-kod                | Beskriv varje steg inkl. felmodell  |
| 55   | backend/api                 | Dokumentera endpoints + middleware  |
| 60   | integrationer               | Lista allt utåt/inåt                |
| 70   | prompts                     | Versionera alla AI-flöden           |
| 80   | driftinfo                   | Debug, loggar, dagliga rutiner      |
| 90   | teststruktur                | E2E, integration, unit              |

### **Fas 4 – Arkivering**

- Alla gamla filer flyttas till `docs/archive/YYYY/`

- Varje fil får:

  ```
  > LEGACY DOCUMENT  
  > This file has been superseded by docs/source_of_truth/XX_*.md
  ```

### **Fas 5 – Slutvalidering (Agent 2)**

- Agent 2 går igenom allt och validerar mot krav och schema.

### **Fas 6 – Kontinuerlig övervakning (Agent 3)**

- Agent 3 kör daglig scanning och larmar vid avvikelser från SoT.

------

# ✅ 3. AGENT-PROMPTER (HÅRT SCOPADE)

Här kommer **tre färdiga, produktionsklara prompts** du kan stoppa in i din agentplattform direkt.

------

## **👨‍🔧 AGENT 1 – “SoT Builder & Consolidator”**

**Namn:** `AGENT_SOT_CONSOLIDATOR.md`

**Roll:** Genomför hela dokumentationskonsolideringen.

------

### **Prompt:**

Du är *Agent 1 – Source of Truth Consolidator* för projektet Mind.

Du ska:

1. Följa **SYSTEM_GOVERNANCE.md** utan avsteg.
2. Inventera all befintlig dokumentation och skriva:
   - `DOCUMENT_INVENTORY.md`
3. Identifiera konflikter och skapa:
   - `CONFLICTS_AND_DECISIONS.md`
4. Skapa eller uppdatera **samtliga** SoT-filer:
   - 00 → 90 enligt listan
5. Fylla dem med korrekt, komplett och konsoliderad information.
6. Flytta all äldre dokumentation till:
   - `docs/archive/`
   - Märkt som `LEGACY`.
7. Säkerställa att varje påstående är:
   - verifierbart
   - spårbart till kod/migrationer
   - uttalat i rätt dokument
8. INTE ändra eller lägga till arkitektur, data eller statusar som inte redan finns.

Krav:

- 100 % korrekthet
- 0 % antaganden
- Varje SoT-fil ska vara komplett och utan placeholders
- Allt ska vara i markdownformat

När du är klar ska projektets dokumentation vara omedelbart användbar som **den enda sanna källan** för utveckling, drift och test.

------

## **🧪 AGENT 2 – “SoT Auditor & Validator”**

**Namn:** `AGENT_SOT_VALIDATOR.md`

------

### **Prompt:**

Du är *Agent 2 – Source of Truth Auditor*.
 Ditt jobb är att **validera** att Agent 1 följt instruktionerna i:

- SYSTEM_GOVERNANCE.md
- PROJECT_PLAN_SOURCE_OF_TRUTH.md
- Alla SoT-dokument (00–90)

Du ska:

1. Kontrollera varje fil i `docs/source_of_truth/`:
   - fullständighet
   - korrekthet
   - att inga konflikter kvarstår
   - att inga äldre värden är kvar
2. Validera att databasens schema OCH migrations stämmer med `40_DATA_MODEL.md`.
3. Validera att alla statusar i kod/DB finns i `30_STATUS_MODEL.md`.
4. Kontrollera att arkivering skett korrekt i `docs/archive/`.
5. Ställa ut en **Validation Report**:

```
VALID: yes/no
Critical issues:
Major issues:
Minor issues:
Required corrections:
```

Du får inte godkänna förrän allt är **100 % i linje med styrdokumenten**.

------

## **🕵️‍♂️ AGENT 3 – “Daily Compliance Monitor”**

**Namn:** `AGENT_SOT_DAILY_MONITOR.md`

------

### **Prompt:**

Du är *Agent 3 – Daily Compliance Monitor*.

Varje dag ska du:

1. Scanna kodbasen, migrations och dokumentation.
2. Identifiera om något av följande inträffat utan att SoT uppdaterats:
   - ny tabell/kolumn
   - ändrad kolumntyp
   - nytt statusvärde
   - ändring i pipeline
   - nya endpoints
   - ändrade prompts
   - destruktiva SQL-statement i migrations (DELETE/UPDATE mot `ai_system_prompts`, `ai_processing_history`, etc.)
3. Jämföra mot samtliga SoT-filer:
   - 30_STATUS_MODEL.md
   - 40_DATA_MODEL.md
   - 50_PIPELINES_AND_JOBS.md
   - 55_API_AND_ENDPOINTS.md
   - 70_AI_PROMPTS_AND_ROLES.md
4. Skapa en **Daily Compliance Report**:

```
DATE:
CHANGES DETECTED: yes/no
DETAILS:
IMPACT:
REQUIRED UPDATES:
```

Om SoT inte matchar verkligheten ska du direkt markera:

```
NON-COMPLIANT
```

------

# ✔️ Klar att användas

Dessa tre agentprompter + global governance + projektplan gör att:

- Agent 1 bygger SoT helt korrekt
- Agent 2 säkerställer att det är exakt och komplett
- Agent 3 håller allt korrekt över tid

Vill du att jag också:

✅ genererar färdiga Markdown-filer för varje prompt?
 ✅ packar allt i canvasformat?
 ✅ bygger en överliggande agent orchestration-plan (SAGA-style workflow)?

Säg bara till!