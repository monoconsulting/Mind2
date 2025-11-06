# MIND - TASKS

Ditt uppdrag är att lösa uppgifterna nedan. Kom ihåg att du måste verifiera detta på valfritt sätt och säkerställa att rätt data visas! Du ska endast göra uppgifter fram till SLUTA HÄR.

- [ ] Flytta samtliga kolumner nedan så att de ej ligger inuti raden utan har egna kolumner med kolumnnamn i header

  - [ ] Gör om tabellen enligt följande:
    Ta bort "Title" och skriv i övre table header "Företag".

  - [ ] Gör om datum till "Fakturadatum/Inköpsdatum"

  - [ ] Upload: Denna visar fel. Den ska visa "Manuellt" eller "FTP". Nu visar det ftp på manuellt. 

  - [ ] Ta bort "FileName"

  - [ ] Ta bort PDF-convert, OCR, AI1, AI2, AI3, AI4, AI5, MATCH

  - [ ] Ta bort nästa datumkolumn

  - [ ] Ta bort företag

  - [ ] Status ska nu visa den status som förut visades i de färgade boxarna - dvs PDF, OCR, AI1, AI2, AI3, AI4 - Klar för kvitton, För first card ska den visa PDF, OCR, AI5, Match Done (AI6)

  - [ ] Behåll exkl moms, inkl moms, status, dokumenttyp

  - [ ] Lägg knapparna under åtgärder under varsin kolumn. Plats,  Ladda ned, Återuppta, Radera. 

    

### Meny - kvitton

- [ ] Preview - byt namn till Förhandsvisning
- [ ] Företag - hämta från databasen unified_files.company_id -> companies.name
- [ ] Köpdatum: ändra till inköpsdatum
- [ ] Belopp ex moms:
- [ ] Belopp ink moms:
- [ ] Match first card - byt namn till Matchning och kontrollera funktionaliteten så at tdet blir en grön bock vid math
- [ ] Utgiftstyp: unified_files.expense_type
- [ ] Kort sista 4: unified_files.credit_card_last_4_digits
- [ ] Korttyp: unified_files.credit_card_type
- [ ] Betalningssätt: unified_files.payment_type
- [ ] Låt övriga vara kvar just nu

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

