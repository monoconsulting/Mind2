# Mind2 Documentation Server Configuration
# Ändra dessa inställningar för att anpassa servern

# Server inställningar
PORT = 9091
HOST = '0.0.0.0'  # '0.0.0.0' för alla interfaces, 'localhost' för endast lokal åtkomst

# Katalog inställningar
DOCS_DIR = None  # None = automatisk detection av web-katalogen
DATA_DIR = None  # None = använder 'data' under DOCS_DIR

# Server beteende
AUTO_OPEN_BROWSER = True  # Öppna webbläsaren automatiskt vid start
LOG_REQUESTS = True  # Logga HTTP-förfrågningar

# API inställningar
ENABLE_CORS = True  # Aktivera CORS för utveckling