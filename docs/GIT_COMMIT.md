---
date created: 2025-09-07 11:33:37
date modified: 2025-09-07 15:55:27
title: GIT_COMMIT
version: 1.1
---

# GIT_COMMIT
## GIT_COMMIT: Spara och Pusha Ditt Arbete

Detta skript är ett "allt-i-ett"-kommando för att spara ditt pågående arbete. Använd detta flera gånger om dagen från din feature-branch för att committa och pusha dina ändringar.

**OBS:** Den automatiska säkerhetskontrollen för 'main' och 'dev' är borttagen. **Det är ditt ansvar att säkerställa att du är på rätt branch innan du kör skriptet.**

---

## Steg 1: Skriv ett commit-meddelande

Tänk ut ett kort och tydligt meddelande som beskriver ändringarna du har gjort.

## Steg 2: Kör commit-skriptet

Kopiera hela kodblocket nedan och klistra in det i din terminal. Du kommer att bli ombedd att skriva in ditt commit-meddelande.

```bash
# === COMMIT & PUSH-SKRIPT (Kopiera allt nedan) ===

# Hämta och visa nuvarande branch-namn som en påminnelse
CURRENT_BRANCH=$(git branch --show-current)
echo -e "\033[0;33m>>> Committar på branch: '$CURRENT_BRANCH' <<< \033[0m" # Gul färg för uppmärksamhet
echo "---"

# Lägg till alla filer (förutsätter en bra .gitignore-fil)
git add .

# Fråga efter commit-meddelande
read -p "Skriv ditt commit-meddelande: " COMMIT_MESSAGE

# Genomför commit
git commit -m "$COMMIT_MESSAGE"

# Pusha till GitHub (använder -u för att sätta upp spårning första gången)
echo "---"
echo "Pushar ändringar till GitHub..."
git push -u origin HEAD

echo -e "\033[0;32mKLART! Dina ändringar är sparade på branchen '$CURRENT_BRANCH' och pushade till GitHub.\033[0m"

# === SLUT PÅ SKRIPT ===