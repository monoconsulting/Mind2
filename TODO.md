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



## Process

#### Filter

- [ ] Status: Ta bort alla legacy-poster. Lägg endast så man kan välja slutförda aktiviteter. Dessutom så är dessa statusflaggor inte alls synkade mot statuskolumnen under. Lägg till en status för "Ej slutförda" och en status för "Ej matchade". Lägg också till status "Manuell hantering" - jag vet inte riktigt var det lagras men jag behö
- [ ] Upload: Här ska det vara "Manuellt" om flödet är triggat från knappen "Ladda upp" i systemet, eller "FTP" om filen är hämtad från ftp
- [ ] Dokumenttyp: 
- [ ] År och månad: Detta stämmer inte. Detta ska sorteras på fakturadatum/inköpsdatum och korrekt månad. Om jag väljer 2025 November så får jag 2025 oktober, okänt fakturadatum, 2024 december, 2025 juli, 2025 augusti.

## Kvitton

- [ ] 



## Kortmatchning

- [ ] Först visas dubbla listor vilket är förvirrande. Sen tar det en väldigt tid att ladda på sidan.
- [ ] Visa kandidater fungerar inte - den visar inte något ens när det är matchat
- [ ] Sortering under kontoutdrag ska visa senaste fakturan överst
- [ ] Uppdatering körs hela tiden på sidan
- [ ] 

## Manuell matchning

- [ ] Välj period: Här ska default vara sista inkomna fc-fakturans period
- [ ] Det är för få kvitton med. Tittar jag på augusti 2025 så har jag 6 kvitton i manuell matchning. Det är 17 i process.
- [ ] Lägg till knapp för "Radera kvitto" - gör då soft delete av kvittot
- [ ]  Lägg till knapp på varje rad som aktiveras då ett fält är valt på varje sida: "Matcha". Då ska dessa två rader kopplas ihop.

- [ ] Ta bort knappen längst uppe till höger "MATCHA"

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





- [ ] I preview modal - skapa knapp för att rensa logger
- [ ] I kortmatchning logg - knapp för att rensa loggar

