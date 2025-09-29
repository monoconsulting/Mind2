# Mind2 Documentation Server (mind-docs)

Detta är dokumentationsservern för Mind2-systemet som hanterar testresultat och systemdokumentation.

## Överblick

Systemet består av:
- **Web Interface**: HTML-baserat gränssnitt för att visa testresultat och systemdokumentation
- **API Server**: Python-baserad server som hanterar data och API-anrop
- **Auto-start Scripts**: Skript för att starta servern automatiskt

## Katalogstruktur

```
/web/
├── index.html                 # Huvudsida med systemöversikt
├── test-results.html          # Sida för testresultat
├── css/
│   └── style.css             # Stilmallar för alla sidor
├── js/
│   ├── main.js               # JavaScript för huvudsida
│   └── test-results.js       # JavaScript för testresultat
├── test/                     # Katalog för testfiler
├── test-results/             # Katalog för testrapporter
├── data/                     # JSON-data för testresultat
├── server.py                 # Python web server
├── start_mind_docs.bat       # Windows startup script
├── start_mind_docs.sh        # Linux/Mac startup script
├── README.md                 # Denna fil
└── TEST_AGENT_INSTRUCTIONS.md # Instruktioner för agenter
```

## Installation och Start

### Automatisk Start

#### Windows:
```bash
start_mind_docs.bat
```

#### Linux/Mac:
```bash
./start_mind_docs.sh
```

### Manuell Start:
```bash
python server.py
```

Servern startar på `http://localhost:9091`

## API Endpoints

Servern tillhandahåller följande API-endpoints:

### GET /api/test-results
Hämtar alla testresultat som JSON.

### POST /api/test-results
Lägger till ett nytt testresultat. Kräver JSON-data med följande fält:
- `testFile` (string): Namnet på testfilen
- `description` (string): Beskrivning av testet
- `successPercentage` (number): Framgångsprocent (0-100)
- `score` (number): Poäng som uppnåtts
- `maxScore` (number): Maximal möjlig poäng
- `reportLink` (string, valfritt): Länk till testrapport
- `mediaLinks` (array, valfritt): Array med länkar till mediafiler
- `testFileLink` (string, valfritt): Länk till testfilen

### GET /api/health
Hälsokontroll för servern.

## Auto-start med System

### Windows (Task Scheduler):
1. Öppna Task Scheduler
2. Skapa ny uppgift
3. Ställ in att köra vid systemstart
4. Sätt action till att köra `start_mind_docs.bat`
5. Ställ in working directory till `/web`

### Linux (systemd):
Skapa filen `/etc/systemd/system/mind-docs.service`:

```ini
[Unit]
Description=Mind2 Documentation Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Mind2/web
ExecStart=/usr/bin/python3 /path/to/Mind2/web/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Aktivera tjänsten:
```bash
sudo systemctl enable mind-docs.service
sudo systemctl start mind-docs.service
```

### macOS (launchd):
Skapa filen `~/Library/LaunchAgents/com.mind2.docs.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mind2.docs</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/Mind2/web/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/Mind2/web</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Aktivera:
```bash
launchctl load ~/Library/LaunchAgents/com.mind2.docs.plist
```

## Konfiguration

Du kan ändra följande inställningar i `config.py`:
- `PORT`: Portnummer (standard: 9091)
- `HOST`: Host-adress (standard: '0.0.0.0')
- `AUTO_OPEN_BROWSER`: Öppna webbläsaren automatiskt (standard: True)
- `LOG_REQUESTS`: Logga HTTP-förfrågningar (standard: True)
- `ENABLE_CORS`: Aktivera CORS för utveckling (standard: True)

## Felsökning

### Servern startar inte:
- Kontrollera att Python 3.7+ är installerat
- Kontrollera att porten inte redan används
- Kör `python server.py` för att se felmeddelanden

### Testresultat visas inte:
- Kontrollera att `data/test-results.json` finns
- Kontrollera att API-endpoints svarar på `/api/test-results`
- Kontrollera att servern körs på rätt port (9091)

### Automatisk start fungerar inte:
- Kontrollera sökvägar i startup-skripten
- Kontrollera behörigheter på skriptfilerna
- Kontrollera systemloggar för felmeddelanden

## Support

För frågor och support, se systemdokumentationen eller kontakta systemadministratören.