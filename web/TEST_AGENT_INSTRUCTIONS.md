# TEST_AGENT_INSTRUCTIONS.md

## Instruktioner för Test-Agenter: Hur man lägger till dokumentation och testresultat

Detta dokument beskriver exakt hur test-agenter ska lägga till testresultat och dokumentation i Mind2-systemet.

## Översikt

Mind2-dokumentationssystemet (mind-docs) tillhandahåller en webbbaserad plattform för att visa testresultat och systemdokumentation. Alla test-agenter måste följa dessa instruktioner för att säkerställa korrekt dokumentation.

## Katalogstruktur för Test-Agenter

### Grundläggande struktur:
```
/web/
├── test/                     # SPARA ALLA TESTFILER HÄR
├── test-results/             # SPARA ALLA TESTRAPPORTER HÄR
└── data/test-results.json    # JSON-data för testresultat (hanteras automatiskt)
```

## Steg-för-Steg Process för Test-Agenter

### 1. Förbered Testfiler

**Spara testfilen i:** `/web/test/`

**Namnkonvention:**
- Format: `YYYY-MM-DD_HH-MM-SS_testnamn.ext`
- Exempel: `2025-01-15_14-30-00_login_test.py`

### 2. Kör Testet

Kör testet enligt normal procedur och dokumentera:
- Startdatum och tid
- Testresultat i procent (0-100%)
- Poäng (X/Y format)
- Eventuella screenshots/videor

### 3. Skapa Testrapport

**Spara testrapporten i:** `/web/test-results/`

**Namnkonvention för rapport:**
- Format: `YYYY-MM-DD_HH-MM-SS_testnamn_report.html`
- Exempel: `2025-01-15_14-30-00_login_test_report.html`

**HTML-mall för testrapport:**
```html
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Testrapport - [TESTNAMN]</title>
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <div class="container">
        <h1>Testrapport: [TESTNAMN]</h1>
        <div class="card">
            <h2>Testinformation</h2>
            <p><strong>Testfil:</strong> [TESTFIL]</p>
            <p><strong>Datum:</strong> [DATUM OCH TID]</p>
            <p><strong>Resultat:</strong> [X]%</p>
            <p><strong>Poäng:</strong> [X]/[Y]</p>
        </div>

        <div class="card">
            <h2>Testbeskrivning</h2>
            <p>[BESKRIVNING AV VAD TESTET GJORDE]</p>
        </div>

        <div class="card">
            <h2>Testresultat</h2>
            <p>[DETALJERADE RESULTAT]</p>
        </div>

        <div class="card">
            <h2>Screenshots/Media</h2>
            <!-- Lägg till länkar till mediafiler här -->
        </div>
    </div>
</body>
</html>
```

### 4. Lägg till Media (screenshots/videor)

**Spara media i:** `/web/test-results/media/`

**Namnkonvention:**
- Format: `YYYY-MM-DD_HH-MM-SS_testnamn_screenshot_N.png`
- Format: `YYYY-MM-DD_HH-MM-SS_testnamn_video.mp4`

### 5. Registrera Testresultat i Systemet

#### Metod 1: API Call (Rekommenderad)

Gör en POST-förfrågan till `http://localhost:9091/api/test-results` med följande JSON-struktur:

```json
{
    "testFile": "2025-01-15_14-30-00_login_test.py",
    "description": "Testar inloggningsfunktionalitet med olika användartyper",
    "successPercentage": 85,
    "score": 17,
    "maxScore": 20,
    "reportLink": "test-results/2025-01-15_14-30-00_login_test_report.html",
    "mediaLinks": [
        "test-results/media/2025-01-15_14-30-00_login_test_screenshot_1.png",
        "test-results/media/2025-01-15_14-30-00_login_test_video.mp4"
    ],
    "testFileLink": "test/2025-01-15_14-30-00_login_test.py"
}
```

#### Exempel med curl:
```bash
curl -X POST http://localhost:9091/api/test-results \
  -H "Content-Type: application/json" \
  -d '{
    "testFile": "login_test.py",
    "description": "Testar inloggning",
    "successPercentage": 85,
    "score": 17,
    "maxScore": 20,
    "reportLink": "test-results/login_test_report.html"
  }'
```

#### Metod 2: JavaScript (om du arbetar i webbläsare)

```javascript
// Lägg till testresultat via JavaScript
const testResult = {
    testFile: "login_test.py",
    description: "Testar inloggningsfunktionalitet",
    successPercentage: 85,
    score: 17,
    maxScore: 20,
    reportLink: "test-results/login_test_report.html",
    mediaLinks: ["test-results/media/screenshot1.png"],
    testFileLink: "test/login_test.py"
};

fetch('/api/test-results', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(testResult)
})
.then(response => response.json())
.then(data => console.log('Test result added:', data));
```

## Obligatoriska Fält

Följande fält MÅSTE inkluderas när du lägger till ett testresultat:

- **testFile** (string): Namn på testfilen
- **description** (string): Kort beskrivning av vad testet gjorde
- **successPercentage** (number): Framgångsprocent (0-100)
- **score** (number): Poäng som uppnåtts
- **maxScore** (number): Maximal möjlig poäng

## Valfria Fält

- **reportLink** (string): Relativ länk till HTML-rapporten
- **mediaLinks** (array): Array med länkar till screenshot/videofiler
- **testFileLink** (string): Relativ länk till testfilen
- **timestamp** (string): ISO-format timestamp (läggs till automatiskt om den saknas)

## Filstruktur Exempel

Efter att ha slutfört ett test ska din filstruktur se ut så här:

```
/web/
├── test/
│   └── 2025-01-15_14-30-00_login_test.py
├── test-results/
│   ├── 2025-01-15_14-30-00_login_test_report.html
│   └── media/
│       ├── 2025-01-15_14-30-00_login_test_screenshot_1.png
│       └── 2025-01-15_14-30-00_login_test_video.mp4
└── data/
    └── test-results.json (uppdateras automatiskt)
```

## Felsökning för Test-Agenter

### Problem: API-anropet misslyckas
- Kontrollera att mind-docs servern körs på port 9091
- Verifiera att JSON-formatet är korrekt
- Kontrollera att alla obligatoriska fält är inkluderade

### Problem: Länkar fungerar inte
- Använd relativa sökvägar (t.ex. `test-results/report.html`, inte `/web/test-results/report.html`)
- Kontrollera att filerna finns på de angivna platserna
- Verifiera att filnamnen stämmer exakt

### Problem: Testresultatet visas inte
- Kontrollera att API-anropet returnerade framgång
- Uppdatera webbläsaren (Ctrl+F5)
- Kontrollera att `data/test-results.json` uppdaterades

## Testa Din Implementation

För att verifiera att allt fungerar:

1. Starta mind-docs servern: `python server.py`
2. Öppna webbläsaren på `http://localhost:9091`
3. Lägg till ett testresultat via API
4. Gå till "Testresultat"-sidan
5. Verifiera att ditt test visas korrekt
6. Klicka på länkarna för att kontrollera att de fungerar

## Python Exempel för Test-Agenter

```python
import requests
import json
from datetime import datetime

def add_test_result(test_data):
    """Lägg till testresultat i mind-docs systemet."""
    url = "http://localhost:9091/api/test-results"

    # Lägg till timestamp om den saknas
    if 'timestamp' not in test_data:
        test_data['timestamp'] = datetime.now().isoformat()

    try:
        response = requests.post(url, json=test_data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Fel vid tillägg av testresultat: {e}")
        return None

# Exempel på användning
test_result = {
    "testFile": "api_test.py",
    "description": "Testar API-endpoints för kvittohantering",
    "successPercentage": 92,
    "score": 23,
    "maxScore": 25,
    "reportLink": "test-results/api_test_report.html",
    "mediaLinks": ["test-results/media/api_test_log.txt"],
    "testFileLink": "test/api_test.py"
}

result = add_test_result(test_result)
if result:
    print("Testresultat tillagd framgångsrikt!")
else:
    print("Fel vid tillägg av testresultat")
```

## Viktiga Påminnelser för Test-Agenter

1. **ALLTID** använd relativa sökvägar i länkar
2. **ALLTID** spara testfiler i `/web/test/`
3. **ALLTID** spara rapporter i `/web/test-results/`
4. **ALLTID** inkludera alla obligatoriska fält
5. **ALLTID** testa att länkar fungerar innan du slutför
6. **ANVÄND** konsekvent namnkonvention
7. **DOKUMENTERA** tydligt vad testet gör
8. **VERIFIERA** att testresultatet visas korrekt i webbgränssnittet

## Support

Om du stöter på problem när du följer dessa instruktioner, kontrollera:
1. Att mind-docs servern körs
2. Att du har skrivbehörighet till `/web`-katalogen
3. Att din JSON-data är korrekt formaterad
4. Systemloggar för eventuella felmeddelanden

Vid fortsatta problem, kontakta systemadministratören med detaljerade felmeddelanden och loggar.