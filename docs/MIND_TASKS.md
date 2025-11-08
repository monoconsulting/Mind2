# MIND - TASKS

## BÖRJA HÄR

# REFACTORING PART 1: Tasks.py

Då ett större antal filer blivit alldeles för stora så behöver vi göra en omfattande refactoring för att få detta att amamma Single Responsibility Principle.

En genomgång har gjorts och denna ska du nu läsa igenom - /docs/REFACTORING_ANALYSIS_LARGE_FILES.md

Den största filen heter backend/src/services/tasks.py. Codex Cloud har tagit fram tre olika förslag på hur refactoring ska genomföras av den.

#PR 

Ditt uppdrag är att granska var och en av dessa 3 PR och efter analys ge en genomtänkt rekommendation på vilken av dessa tre - eller ingen alls - vi ska välja för merge.

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

##### Steg 1. 

* Filen E:\projects\Mind2\web\tests\codegen\mind_full_walkthrough.codegen.spec.ts innehåller en genomgång av alla funktioner i siten. 
* Hämta det du behöver härifrån och skapa ett NYTT test som du använder för att logga in och kontrollera funktionalitet.
* Du **MÅSTE HÄMTA INFORMATION UR MIN CODEGEN**. Du får korrigera funktioner men inloggningar menyer och annat SKA du hämta för attt vi ska spara tid.

##### Steg 2. 

* Kör testet på Kortmatchningsmenyn. 
  * Kontrollera statusmenyn. Kontrollera vad som händer om du trycker återuppta statusrapport - får du NY STATUS MOMENTANT?
  * Tryck på visa logg. Ser du fortfarande encodingfe

##### Steg 3. 

1. Lös problemen definierade ovan (Statusfel, encodingfel)

2. Kör testet och utvärdera resultat
3. Iterera över detta tills allt fungerar som föräntat och alla statusar visas snabbt och exakt.













**Ditt uppdrag är följande:**

**Menyval kortmatchning fungerar fortfarande inte tillfredsställande.**

* Status ändras ej oavsett hur många gånger jag trycker på "Återuppta fakturaimport"
* VIKTIGT! Om inkommande objekt för konvertering EJ klassificeras som faktura eller kvitto så ska det OMGÅENDE sättas i status manuell hantering och därefter hanteras manuellt. Det ska EJ processas vidare. 
* Skärmen hoppar fortfarande ca var 10.e sekund

**Felaktig encoding i "Visa logg"**

* #### Workflowk�rning

* Run-ID: 189 - K�lla: kortmatchning_restart

  







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

