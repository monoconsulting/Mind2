# 🧭 **FULL UTFÖRANDEPLAN – I RÄTT ORDNING**

## 🟦 **PHASE A – MUST BE FIRST**

### *Establish migration correctness & DB foundation*

Kör i denna ordning:

1. **A1** – Migrations directory centralization
2. **A2** – Migration consistency audit
3. **A3** – Generate missing migrations
4. **A4** – Migrations test hardening

➡️ Efter fas A är DB stabil, migreringssystemet robust och agenten kan jobba tryggt vidare.

------

## 🟩 **PHASE B – Stabilize status model**

Kör i denna ordning:

1. **B1** – Status inventory
2. **B2** – Reconcile constants
3. **B3** – Replace loose strings
4. **B4** – Full status transition tests

➡️ Detta låser statusmodellen för hela systemet och minimerar buggar i C–F.

------

## 🟨 **PHASE C – Normalize Receipts & Invoices**

Måste köras **före FirstCard och AI** eftersom hela FC och AI är beroende av normaliserade dokumentfält.

Ordning:

1. **C1** – Model unification
2. **C2** – FK integrity pass
3. **C3** – Date/time normalization
4. **C4** – Amount/currency normalization
5. **C5** – End-to-end normalization tests

➡️ Efter fas C är systemets datamodeller stabila och alla workflows kan lita på dokumentstrukturer.

------

## 🟥 **PHASE D – FirstCard workflow refactor**

Den viktigaste fasen efter A–C.
 Task-ordningen:

1. **D1** – FC WorkflowCoordinator
2. **D2** – Route import/resume via coordinator
3. **D3** – Replace manual status updates
4. **D4** – Canonical detail views (invoice_documents + lines)
5. **D5** – FC full workflow integration test
6. **D6** – Resume/restart workflow tests

➡️ Efter fas D är FirstCard stabil, konsekvent och testad end-to-end.

------

## 🟧 **PHASE E – ManualMatch polish**

Måste köras **efter D**, annars bygger den mot gamla FC-flöden.

Ordning:

1. **E1** – Pagination improvements
2. **E2** – Toasts/error handling
3. **E3** – ManualMatch API-level tests

➡️ Efter fas E är ManualMatch robust, användarvänlig och korrekt testad.

------

## 🟪 **PHASE F – AI Pipeline refactor**

Måste köras **efter A–E**, annars måste AI stegen byggas om i efterhand för att matcha workflows.

Ordning:

1. **F1** – Provider-only extraction
2. **F2** – Orchestrator per AI step
3. **F3** – Hardened Pydantic domain models
4. **F4** – Unified AI logging

➡️ Efter fas F är AI-lagret superstabilt, isolerat och perfekt spårbart.

------

## ⬛ **PHASE G – Task quality & observability**

Måste köra **efter alla kodfaser (A–F)** så att det finns en stabil struktur att analysera.

Ordning:

1. **G1** – Classify tasks (active/legacy/unused)
2. **G2** – Logging improvements
3. **G3** – Retire unused tasks (comment only)
4. **G4** – Fix silent failures

➡️ Efter fas G är task-systemet renare, säkrare och lättare att felsöka.

------

## 🟫 **PHASE H – Documentation**

ALLTID sista fasen.

Ordning:

1. **H1** – System-level documentation
2. **H2** – Workflow diagrams
3. **H3** – QuickStart onboarding
4. **H4** – Monitoring & debugging docs

➡️ Detta är ren finish och förbereder systemet för långsiktig drift & vidareutveckling.

------

# 🎯 **Sammanfattad exekveringsordning (kondensformat)**

```
A1 → A2 → A3 → A4
B1 → B2 → B3 → B4
C1 → C2 → C3 → C4 → C5
D1 → D2 → D3 → D4 → D5 → D6
E1 → E2 → E3
F1 → F2 → F3 → F4
G1 → G2 → G3 → G4
H1 → H2 → H3 → H4
```

**Ja – faserna körs från A → H i ordning.
 Och ja – tasks körs i exakt ordningsföljd inom sin fas.**