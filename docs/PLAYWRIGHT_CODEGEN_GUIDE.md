# Playwright Codegen - Guide

## Vad är Playwright Codegen?

Playwright Codegen är ett verktyg som **spelar in dina klick och interaktioner** i webbläsaren och genererar automatiskt testkod. Du klickar runt som en vanlig användare och får färdig kod som du kan använda för att skapa automatiserade tester.

---

## Snabbstart

### 1. Kör bat-filen

```bash
playwright_codegen.bat
```

Detta startar Codegen mot `http://localhost:8008` (din lokala miljö).

**Alternativt, för annan URL:**
```bash
playwright_codegen.bat http://localhost:5169
playwright_codegen.bat https://example.com
```

---

## Så här fungerar det

### När du kör bat-filen händer detta:

1. **Två fönster öppnas:**
   - **Webbläsare** - Där du klickar runt
   - **Playwright Inspector** - Där koden genereras i realtid

2. **Interagera med webbläsaren:**
   - Klicka på knappar
   - Fyll i formulär
   - Navigera mellan sidor
   - Allt du gör spelas in!

3. **Koden genereras automatiskt:**
   - Varje klick blir en `click()`
   - Varje textinmatning blir en `fill()`
   - Navigering blir `goto()`
   - Assertions kan läggas till manuellt

4. **Kopiera koden:**
   - När du är klar: Markera all kod i Inspector (Ctrl+A)
   - Kopiera (Ctrl+C)
   - Stäng webbläsaren

---

## Exempel på arbetsflöde

### Scenario: Testa kvittohantering

**Steg 1: Kör Codegen**
```bash
playwright_codegen.bat http://localhost:8008
```

**Steg 2: Klicka runt**
1. Logga in (om nödvändigt)
2. Gå till "Receipts"
3. Klicka på "Upload"
4. Välj en fil
5. Klicka "Submit"
6. Verifiera att kvittot visas

**Steg 3: Kopiera genererad kod**

Inspector visar något liknande:
```javascript
await page.goto('http://localhost:8008/');
await page.getByRole('link', { name: 'Receipts' }).click();
await page.getByRole('button', { name: 'Upload' }).click();
await page.setInputFiles('input[type="file"]', 'path/to/receipt.jpg');
await page.getByRole('button', { name: 'Submit' }).click();
```

**Steg 4: Ge koden till Claude**

Berätta för Claude:
> "Jag har spelat in ett test för kvittouppladding. Här är koden från Codegen:
> [klistra in koden]
>
> Gör ett komplett test i `web/tests/` som:
> - Använder korrekta viewport settings från playwright.config.ts
> - Lägger till assertions
> - Hanterar fel
> - Har bra struktur"

---

## Tips & Tricks

### 1. Använd rätt viewport
Bat-filen sätter automatiskt din ultrawide viewport: `--viewport-size=3440,1440`

### 2. Generera specifika selectors
I Playwright Inspector kan du:
- Klicka på "Explore" för att testa selectors
- Använda "Pick locator" för att välja element

### 3. Lägg till assertions efteråt
Codegen genererar bara interaktioner, inte assertions. Claude kan hjälpa till att lägga till:
```javascript
// Du kan be Claude lägga till:
await expect(page.getByText('Receipt uploaded')).toBeVisible();
await expect(page.getByRole('heading')).toContainText('Success');
```

### 4. Olika målmiljöer

**Produktion (port 8008):**
```bash
playwright_codegen.bat http://localhost:8008
```

**Dev med hot-reload (port 5169):**
```bash
playwright_codegen.bat http://localhost:5169
```

---

## Vad gör Claude efter att du klistrat in koden?

1. **Analyserar flödet** - Förstår vad testet gör
2. **Lägger till struktur:**
   - Test description
   - Proper test blocks
   - Setup/teardown om nödvändigt

3. **Förbättrar selectors:**
   - Använder `data-testid` om tillgängliga
   - Fallbacks för robusthet

4. **Lägger till assertions:**
   - Verifierar att element är synliga
   - Kontrollerar textvärden
   - Validerar navigering

5. **Error handling:**
   - Timeout-hantering
   - Retry-logik där nödvändigt

6. **Anpassar till din config:**
   - Använder rätt viewport från `playwright.config.ts`
   - Placerar i rätt testmapp (`web/tests/`)
   - Följer namnkonventioner

---

## Felsökning

### Problem: Codegen hittar inte npx
**Lösning:** Kör från Mind2-mappen där `node_modules` finns

### Problem: Fel viewport i genererad kod
**Lösning:** Bat-filen sätter redan rätt viewport (3440x1440)

### Problem: Koden fungerar inte när jag kör testet
**Lösning:**
1. Ge koden till Claude
2. Berätta vilket beteende du förväntar dig
3. Claude kommer fixa selectors och timing

---

## Nästa steg

Efter att du kört Codegen och kopierat koden:

1. **Starta en konversation med Claude:**
   ```
   Jag har spelat in ett test med Playwright Codegen.
   Här är koden: [klistra in]

   Skapa ett komplett test som:
   - Testar [beskriv vad testet ska göra]
   - Verifierar [beskriv förväntade resultat]
   - Sparas som web/tests/[filnamn].spec.ts
   ```

2. **Claude skapar testet**
3. **Kör testet:**
   ```bash
   npx playwright test web/tests/ditt-test.spec.ts --headed
   ```

---

## Sammanfattning

| Steg | Action | Resultat |
|------|--------|----------|
| 1 | Kör `playwright_codegen.bat` | Öppnar browser + Inspector |
| 2 | Klicka runt i browsern | Kod genereras live |
| 3 | Kopiera kod från Inspector | Färdig grundkod |
| 4 | Ge kod + instruktioner till Claude | Komplett, robust test |
| 5 | Kör testet | Automatiserad testning! |

**Fördel:** Du behöver inte känna till Playwright-syntax - klicka bara runt och Claude fixar resten!
