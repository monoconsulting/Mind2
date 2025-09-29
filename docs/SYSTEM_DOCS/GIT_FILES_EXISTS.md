---
date created: 2025-09-07 11:33:37
date modified: 2025-09-07 15:55:59
aliases: ["GIT_FILES_EXISTS: Hantera ocommittade filer på ett säkert sätt"]
version: 1.1
title: "GIT_FILES_EXISTS: Hantera ocommittade filer på ett säkert sätt"
linter-yaml-title-alias: "GIT_FILES_EXISTS: Hantera ocommittade filer på ett säkert sätt"
---

# GIT_FILES_EXISTS: Hantera ocommittade filer på ett säkert sätt

Denna guide hjälper dig när `git status` visar att du har ändringar i ditt "working tree" eller om du har en bortglömd "stash". Målet är att spara ditt arbete korrekt så att du kan byta branch eller starta en ny uppgift.

**Grundregel:** Innan du gör något annat, se vad Git säger.
`git status`

---

## Scenario 1: `git status` visar ändringar eller ospårade filer

Detta betyder att du har ändrat eller skapat filer som inte har sparats i en commit.

### Alternativ A: Du vill spara ändringarna i en ny, egen branch (REKOMMENDERAS)

Detta är den säkraste metoden. Du skapar en tillfällig branch bara för dessa ändringar.

1.  **Skapa en temporär branch:** Ge den ett logiskt namn.

    ```bash
    git checkout -b temp-fix-2025-09-07
    ```

2.  **Lägg till och committa ALLA filer:** Här använder vi `git add .` för att garantera att allt (nya, ändrade, raderade filer) inkluderas.

    ```bash
    # Steg 1: Granska ändringarna du är på väg att lägga till
    git status

    # Steg 2: Lägg till allt i "staging area"
    git add .

    # Steg 3: Committa
    git commit -m "WIP: Sparar ocommittat arbete"
    ```

3.  **Nu är din arbetsyta ren!** Du kan nu byta tillbaka till `dev` och köra `GIT_START.md` igen.

### Alternativ B: Du vill spara ändringarna temporärt (Stashing)

En stash är perfekt för att snabbt "gömma" ändringarna. Vi lägger till flaggan `-u` för att säkerställa att även helt nya (untracked) filer följer med i din stash.

1.  **Spara allt i en stash:**

    ```bash
    # Använd -u för att inkludera "untracked" (nya) filer
    git stash push -u -m "Beskrivning av vad du höll på med"
    ```

2.  **Verifiera att arbetsytan är ren:**

    ```bash
    git status 
    ```
    Svaret ska nu vara `working tree clean`.

3.  **För att senare återställa ändringarna:** Gå till den branch där ändringarna hör hemma och kör:

    ```bash
    git stash pop
    ```
    När ändringarna är återställda, committa dem med `git add .` för att säkerställa att allt kommer med.
    ```bash
    git add .
    git commit -m "Återställt och committat arbete från stash"
    ```

### Alternativ C: Du vill kasta bort alla ändringar (VAR FÖRSIKTIG!)

**DETTA FÅR DU ALDRIG GÖRA UTAN MIN ORDER**

```bash
# KASTAR BORT ALLA LOKALA ÄNDRINGAR
git reset --hard
git clean -fdxxxxxxxxxxx # Deletes the latest stashgit stash drop stash@{0}# Deletes ALL stashes (BE CAREFUL!)git stash clear
```