# MIND - TASKS

## BÖRJA HÄR



## Refactoring fas 1 och 2 - korrigeringar

Context:



Vi har nu gjort refactoring av stora filer fas ett och två och har ett antal rättningar som behöver göras i koden. 

Denna fil innehåller all information och planen för refactoring: `docs/REFACTORING_ANALYSIS_LARGE_FILES.md` 

Dessa filer har refactoriserats i fas 1 och 2.

* `backend/src/api/reconciliation_firstcard.py`.
* `backend/src/services/tasks.py` 



Granskning har gjort och ett antal rättelser behöver nu göras

DITT UPPDRAG

## Ditt uppdrag

Läs igenom denna filen noggrant: 

Gå igenom punkt för punkt och rätta de uppgifter som finns.

Då allt är klart - gör en ny genomgång och se till att din kod fungerar, har kopplingar mot databasen och att varje uppgift i instruktionen är till 100% täckt.

Success=Allt genomfört exakt som det står i beskrivningen med 100% täckning `docs\FIRSTCARD_REFACTOR_FAS1_FAS2_ANALYS.md`

**Har du några frågor du vill ställa innan du börjar ditt arbete?**



#### 1. Resume endpoint (rad 298-307):

# MANUELL UPDATE - sätter både status OCH processing_status direkt

Nu:

```
set_clause = "status='matching', processing_status=%s"
if invoice_documents_supports_updated_at():
    set_clause += ", updated_at=NOW()"
cur.execute(
    f"UPDATE invoice_documents SET {set_clause} WHERE id=%s",
    (InvoiceProcessingStatus.OCR_PENDING.value, sid),
)
```

Ändra till:

*# Använd WorkflowCoordinator eller transition_\* funktioner*

```
coordinator = WorkflowCoordinator()

coordinator.start_processing(sid)  *# Transition till ocr_pending*

transition_document_status(

  sid, 

  InvoiceDocumentStatus.MATCHING,

  (InvoiceDocumentStatus.IMPORTED, InvoiceDocumentStatus.MATCHING, InvoiceDocumentStatus.FAILED)

)
```

#### 2. Restart endpoint (rad 420-424):

*# MANUELL UPDATE - sätter flera fält samtidigt*

```
set_clause = "metadata_json=%s, processing_status='ocr_pending', status='imported'"

*if* invoice_documents_supports_updated_at():

  set_clause += ", updated_at=NOW()"

cur.execute(

  f"UPDATE invoice_documents SET {set_clause} WHERE id=%s",

  (json.dumps(metadata), sid),

)


```

Ändra till*# Uppdatera metadata separat*

```
write_invoice_metadata(sid, metadata)

*# Använd transitions för status*

transition_processing_status(

  sid,

  InvoiceProcessingStatus.OCR_PENDING,

  (InvoiceProcessingStatus.UPLOADED, InvoiceProcessingStatus.FAILED, InvoiceProcessingStatus.COMPLETED)

)

transition_document_status(

  sid,

  InvoiceDocumentStatus.IMPORTED,

  (InvoiceDocumentStatus.FAILED, InvoiceDocumentStatus.COMPLETED, InvoiceDocumentStatus.MATCHED)

)


```













###REFACTORING PART 2 : backend/src/api/reconciliation_firstcard.py

Ditt uppdrag:

Du ska genomföra en omfattande re-factoring av filen backend/src/api/reconciliation_firstcard.py

1. Läs först .prompts/start.prompt.md

    2. Läs därefter \docs\REFACTORING_ANALYSIS_LARGE_FILES.md4 och E:\projects\Mind2\docs\FIRSTCARD_STATUS_FLOW.md
    3. Du ska följa instruktionerna i dessa filer exakt, och hjälpa till att försöka nå single responsible principle
    4. Starta från början och följ principerna exakt. 



Har du några frågor till mig innan du kör igång?



    2. PR 62 and PR 64 both introduce a deterministic NameError in
  ould regress critical workflows and the 
    3. core sizing goal has not been met, I recommend rejecting all four PRs
    for now. The next iteration should (a) retain or shim the legacy
    Celery entry points until every caller is migrated, (b) fix the
    _move_to_manual_review implementation, and (c) continue splitting the        
    massive credit-card/AI modules into the specific files outlined in
    REFACTORING_ANALYSIS_LARGE_FILES.md.

  1. PR 61/62/63 remove process_ocr/process_ai_pipeline/
     process_invoice_ai_extraction, breaking every existing script, test, and
     operational tool that still imports those symbols.
    until responsibilities are isolated.

  4. **Maintain Behavior & Tests**
     - Do not drop or rename helpers currently patched in tests (e.g., `_get_file_type`,
    `_load_unified_file_info`, `_maybe_advance_invoice_from_file`). If you relocate them, re-export through  
    `services.tasks` so all existing tests pass without changes.
     - No mock/placeholder data. Follow the real DB/storage interactions already in the codebase.

  5. **Workflow Logging & Status**
     - Ensure workflow helpers (`begin_import_stage`, `complete_import_stage`, `mark_stage`, etc.) stay    
    functional. When you move code, keep their side effects identical.
     - Credit-card processing must continue to update invoice metadata, line counts, and statuses exactly  
    as before.

  6. **Before Opening a PR**
     - Verify `python -m pytest backend/tests/unit/test_tasks_invoice_pipeline.py` passes.
     - Spot-check `flake8 backend/src/services/tasks` (or the new package) for obvious issues.

  Deliverable: a clean `services/tasks/` package that honors the legacy API, fixes manual-review errors,   
  and matches the structure/size goals from the refactor plan.



Då ett större antal filer blivit alldeles för stora så behöver vi göra en omfattande refactoring för att få detta att amamma Single Responsibility Principle.

En genomgång har gjorts och denna ska du nu läsa igenom - /docs/REFACTORING_ANALYSIS_LARGE_FILES.md

Den största filen heter backend/src/services/tasks.py. Codex Cloud har tagit fram fyra olika förslag på hur refactoring ska genomföras av den.

#PR 61

#PR 62

#PR 63

#PR 64

Ditt uppdrag är att granska var och en av dessa 4 PR och efter analys ge en genomtänkt rekommendation på vilken av dessa - eller ingen alls - vi ska välja för merge.

Jämför med befintlig kodbas, och jämför med planen /docs/REFACTORING_ANALYSIS_LARGE_FILES.md

Redovisa därefter din slutsats med motivation. 



Vi har ett antal filer som blivit alldeles för stora i systemet och nu behöver delas upp för att få en effektivare struktur. En genomgång är gjord, och vi ska nu fortsätta med filen `backend/src/api/reconciliation_firstcard.py`. Börja läsa @docs/REFACTORING_ANALYSIS_LARGE_FILES.md och genomför denna omstrukturering på filen med flest rader - backend/src/services/tasks.py. Gör refactory på `backend/src/api/reconciliation_firstcard.py`enligt dokumentet.







Läs först /.prompts/start.prompt.md

Läs därefter /docs/MIND_PROCESS_IMPORT_STATUS_DIAGRAM.md. Denna fil innehåller den exakta processen för import och återupptag av konvertering. Detta är din bibel och ditt facit - EXAKT DETTA ska du lösa.

**Vi försöker få till följande två saker och har hållit på snart i två dygn utan framgång.**

1. Status skrivs ej ut rätt i kolumnen "STATUS" 

   1. Fungerar ej rätt i menyval kortmatchning (company-card). 
   2. SKA följa samma statusar som rapporteras i loggen - som nås via kolumn "Visa logg".  
   3. Statusuppdatering ska ske momentant efter att knappen "Återuppdata fakturaimport" trycks in. Momentant. 
   4. Den ska då gå till den status den startar ifrån och fortsätta till slutet. 
   5. VARJE GÅNG den byter status ska du skriva ut den svenska texten inom hakklammer:   r_ai3_start["r_ai3 startad ⏳"] - då ska du skriva ut r_ai3 startad ⏳

2. Felaktig encoding då man trycke knappen "Visa logg". 

   1. Det visar sig att alla mina agenter har varit kompetenta. De kan inte fixa dessa bokstäver. Visa mig gärna att du är smartare. Vill du ha ytterligare info läs denna /docs/[SWEDISH_ENCODING_RULES.md](SWEDISH_ENCODING_RULES.md) .
   2. Så här ser det ut: 
      1. Workflowk�rning
      2. Run-ID: 571 - K�lla: kortmatchning_restart
      3. Kan finnas fler. ALLA SKA BORT.

   

## **ACTIONLISTA**









**Ditt uppdrag är följande:**

**Menyval kortmatchning fungerar fortfarande inte tillfredsställande.**

* Status ändras ej oavsett hur många gånger jag trycker på "Återuppta fakturaimport"
* VIKTIGT! Om inkommande objekt för konvertering EJ klassificeras som faktura eller kvitto så ska det OMGÅENDE sättas i status manuell hantering och därefter hanteras manuellt. Det ska EJ processas vidare. 
* Skärmen hoppar fortfarande ca var 10.e sekund

**Felaktig encoding i "Visa logg"**

* #### Workflowk�rning

* Run-ID: 189 - K�lla: kortmatchning_restart

  



Stora uppgifter:

Uppdatering av modal - företag måste kunna väljas eller skapas





# SLUTA HÄR

_________

## KLART - IGNORERA NEDAN



## Meny - Kortmatchning



### Kontoutdrag

#### Header i fält "Kontoutdrag"

- [ ] Lägg till en knapp "Matcha omatchade poster" - denna ska köra igenom alla poster för samtliga fakturor som ej är matchade

#### Tabell

- [x] Kort (första kolumnmen): Ändra CEDERLUND MATTIAS till  (creditcard_invoices_main.card_name). 
- [x] Fakturadatum saknas på alla (creditcard_invoices_main.invoice_date)
- [x] LÄGG TILL KOLUMN: Betalningsdatum  (creditcard_invoices_main.due_date)
- [x] LÄGG TILL Kolumn: Belopp (creditcard_invoices_main.amount_to_pay) kr
- [x] LÄGG TILL Kolumn: Matchade rader
- [x] LÄGG TILL Kolumn: Omatchade rader
- [x] LÄGG TILL Kolumn: RÖD KNAPP - Matcha omatchade rader
- [x] Ändra AI6 till AI - Konfidens
- [x] Status: Alternativen ska vara Ej bearbetad (nyss uppladdad), Under bearbetning, Bearbetad (allt klar utom match), Matchad (allt klar, alla poster på fakturan har gåtts igenom för matchning)
- [x] Ta bort kolumn bearbetning
- [x] Ändra kolumn linjer till RADER
- [x] LÄGG TILL Kolumn: 
- [x] Ta bort knapp "Auto-matcha"





- [ ] Vid klick på post i första kolumnen ska previewmodalen öppnas med inställningar anpassade för FC
- [ ] 

