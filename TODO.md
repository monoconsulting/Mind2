## Översikt/Dashboard

### Översta raden

- [ ] Rött fält "Totalt antal kvitton" - stämmer ej. Troligen mockup
- [ ] Grönt fält "Träffsäkerhet" - stämmer ej. Troligen mockup
- [ ] Orange fält "Bearbetningskö" stämmer ej. Troligen mockup
- [ ] Blått fält "Systemhälsa"- stämmer ej. Troligen mockup
- [ ] Rött fält "Totalt antal kvitton" - stämmer ej. Troligen mockup

#### Tabell senaste händelser

- [ ] I varje rad - lägg till datum och tid för när detta inträffade
- [ ] Mockup?

#### Lagring:

- [ ] Lagringsanvändning - mockup - ändra



## Process 1 

#### Filter

- [x] Status: Ta bort alla legacy-poster. Lägg endast så man kan välja slutförda aktiviteter. Dessutom så är dessa statusflaggor inte alls synkade mot statuskolumnen under.
- [ ] Lägg till en status för "Ej slutförda" och 
- [ ] en status för "Ej matchade". - ger 0 vid riltrering.

- [ ] Lägg till kolumn "Manuell hantering"

- [x] Lägg också till status "Manuell hantering" - jag vet inte riktigt var det lagras men jag behöver kunna filtrera på det.
- [ ] Filter: Status: Statusar är definierade i @MIND_STATUS_DEFINITIONS.md.  Dessa ska användas. Alla andra statusar ska tas bort. Det är en stor diskrepans mellan filtreringen för status - och kolumnen status i tabellen. Båda kolumnerna måste använda statusar från filen ovan.
- [x] Filter: Upload: Här ska endast "Manuellt" eller "FTP" presenteras.
- [ ] Visa per sida: Oavsett vad jag väljer så visas 178 poster.
- [ ] Lägg till kolumn "Matchad"  med alternativ "Matchad/Ej matchad"
- [x] Om jag återupptar en post så ska statusen omedelbart förändras till det stället den återupptar arbetet ifrån - vilket jag antar är r_ocr. Nu händer ingenting.
- [x] Om man väljer ett företag så ska man även kunna ändra eller fylla på information i fält som saknas. Det valda företaget ska då uppdateras när man trycker spara. Nu kan man inte ändra något. 
- [ ]  
- [ ] 

## Kvitton

- [ ] 



## Kortmatchning

- [ ] Preview för kortmatchning behöver skapas. Som start gör vi en enkel version som visar samtliga scannade sidor av dokumentet. Man ska kunna växla mellan de inbördes sidorna med höger och vänsterpil. Pilarna ska se ut som i ReceiptPreviewModal - men endast gälla de sidor som tillhör dokumentet. 
- [ ] Dubbla listor visas när sidan laddas - se över varför det renderas två kompletta listor först innan det slutligen blir en. 
- [ ] Ta bort funktionen Visa kandidater
- [ ] Sortering under kontoutdrag - alltså överst på sidan - ska visa **senaste fakturan överst**
- [ ] Uppdatering körs hela tiden på sidan vilket leder till att det fladdrar hela tiden Ta bort fladdret vid uppdatering
- [ ] 





## Manuell matchning

Under menyval "Manuell matchning" E:\projects\Mind2\main-system\app-frontend\src\ui\pages\ManualMatch.jsx så ska funktionen se ut som följande:

### Kontext

Syftet är att matcha kvitton som finns i systemet mot företagskortets faktura som kommer månadsvis. Detta lagras sedan som en matchning i databasen. Man kan under menyval "Kortmatchning" automatiskt matcha, vilket sker i många fall - men inte alltid, och då behöver man in och själv korrigera.

### **Funktion**

#### Välj period

Här väljer du den period som du vill göra matchning på genom att välja år och månad. Här är det viktigt att komma ihåg följande:
**Om september 2025 väljs som period - så innebär det att alla items för semptember ska visas för FC-card och Kvitton**

Det innebär - att **fakturadatumet** för FC-card är med största sannolikhet oktober, eftersom fakturan kommer efter månadsbrytet.

### Filtrering

Filtrering ska finnas och som start endast en dropdown som visar Matchade, Ej matchade, Alla

#### Kvitto/FC-tabeller

**Vänster kolumn**

På vänster sida finns transaktionerna för First Card listade. Dessa ska sorteras i datumordning med äldsta datumet först. 

Man ska kunna klicka på varje header - och sortering ska då ske efter den headern

Följande kolumner är listade just nu: Välj - Datum - Företag - Beolopp (ink moms) - Status (Matchad/Ej matchad)

**Höger kolumn**

Här listas **samtliga kvitton som existerar för perioden**

Från vänster till höger ser tabellen ut så här: Välj (checkbox) - Datum - Företag - Belopp - Status - Åtgärd (Nu: Visa - när du är klar - Visa - Radera - Matcha)

Man ska kunna klicka på varje header - utom åtgärd - och sortering ska då ske efter den headern

Under åtgärd vinns idag "Visa" - och du ska nu också lägga till "Matcha" - denna ska tändas om två poster är valda - en på varje sida. Denna ska också visa "Radera" - vilket gör en soft delete av aktuellt kvitto. Kan vara användbart om dubletter finns.

**Matchning:**

Då en post är vald i varje kolumn ska knappen "Matcha" tändas längst till höger. Då den klickas markeras de båda posterna som matchade i databasen.



**Ditt uppdrag:**

1. Säkerställ att alla kvitton verkligen visas i kvittotabellen - ibland verkar det saknas kvitton

2. Skapa filtrering och lägg in för "Matchade"

3. Lägg till Radera och matcha i kvittokolumnen

4. ta bort knappen MATCHA som finns längst uppe på sidan

   
Utökad funktionalite:
Chatta med agenten och fyll i data från modal

Hantering av personliga kvitton

Belopp sparas inte när man ändrar i modalen







höger k

- [ ] 
- [ ] Välj period: Här ska default vara sista inkomna fc-fakturans period
- [ ] Det är för få kvitton med. Tittar jag på augusti 2025 så har jag 6 kvitton i manuell matchning. Det är 17 i process.
- [ ] Lägg till knapp för "Radera kvitto" - gör då soft delete av kvittot
- [ ]  Lägg till knapp på varje rad som aktiveras då ett fält är valt på varje sida: "Matcha". Då ska dessa två rader kopplas ihop.

- [ ] Ta bort knappen längst uppe till höger "MATCHA"

## AI

- [x] Under menyval AI: Det har tillkommit ett antal nya poster under "Systemprompter"  - och detta är inte bra. De enda systemprompter som får nyttjas är de som är listade ovan. Addera till AGENTS.md att agenter aldrig får lägga till systemprompter. Alla nya systemprompter har svensk text i rubriken. De som ska vara kvar har engelsk text i rubriken och börjar med AIX: Description.
  Undersök om dessa anropas någonstans i något workflow. Detta måste i sådana fall återställas så ordinarie prompts används
  Radera sedan de nya systempromptarna.

## Export

- [ ] 

## Användare

- [ ] 

## Inställningar

- [ ] 

## Import av filer

Fixa flow som körs i n8n för hämtning av alla kvitton

Betalningstyp "Swish står som corporate - helt fel."

Dubletthantering vid import

Kontrollera att samtliga sidor är improterade vid fc-import



Import functionality

Importfunktionaliteten som sker antingen via manuell uppladdning eller ftp - behöver ytterligare funktionalitet för att fungera:

1. Vi måste kontrollera om kvittot redan är inläst så snart det är möjligt att göra. Om kvittot är inläst ska det stanna kvar i systemet men markeras som dublett på något sätt och inte synas i listan över kvitton. 
2. Swish - tolkas av AI som "corporate" - vilket är helt fel. Det kan BARA vara personal
3. Vi behöver se över importen av FC-fakturor - det verkar som inte alla sidor följer med på alla fakturor. Vid importen så behöver systemet först se efter hur många sidor detta är som start. I sista steget i konverteringsskedjan då all OCR slås samman till en lång text - måste man se till att lika många sidor har bearbetats som det är sidor i PDF-filen. Dvs: En pdf med 6 sidor -> skapra 6 bilder - OCR:ar 6 bilder - slår ihop 6 texter. 
4. Systemet måste hantera kvitton som har fler än en sida på samma sätt som fc-fakturor. Nu genereras ett kvitto per sida i pdf:en vilket blir helt fel. Säkerställ att import av flersidiga kvitton i pdf-format genererar ett flersidigt kvitto. Skapa också möjlighet i ReceiptPreviewModal att hantera flersidiga kvitton. Gör detta genom att låta de översta pilarna höger-vänster gå till nästa kvitto i listan, och lägg till nedre pilar om det finns flera sidor - som växlar mellan sidorna i dokumentet. Lägg sidnumrering längst ner på sidan Sida 1 Sida 2 etc. 



- [ ] I preview modal - skapa knapp för att rensa logger
- [ ] I kortmatchning logg - knapp för att rensa loggar

## FEATURES TO COME
Skapa dedikerad yta för upp och nedladdning
Scannat: Mindupload
Inläst: mindupload/archived

Hur kan man tagga kvitton som icke-företagskvitton?

