---
date created: 2025-09-07 11:34:43
date modified: 2025-09-07 16:00:12
aliases: [Guide för Taggning i Git]
title: Guide för Taggning i Git
linter-yaml-title-alias: Guide för Taggning i Git
version: 1.1
---

# Guide för Taggning i Git


Denna guide beskriver standarden för hur och när vi använder Git-taggar i våra projekt. Korrekt taggning är en kritisk del av en säker och spårbar utvecklingsprocess.

### Varför ska man använda taggar?

En Git-tagg är som ett permanent bokmärke för en specifik commit. Till skillnad från en branch, som flyttar sig framåt med nya commits, pekar en tagg alltid på exakt samma punkt i historiken. Vi använder dem för tre huvudsakliga anledningar:

1.  **Säkerhet:** En tagg fungerar som en garanterad "ångra-knapp" eller återställningspunkt. Om en merge mot förmodan skulle orsaka problem, kan vi alltid med 100% säkerhet backa till exakt det tillstånd koden hade vid taggningstillfället.
2.  **Spårbarhet:** Genom att inkludera ärendenumret (`TMXXX`) i taggen kopplar vi koden direkt till uppgiften i vårt ärendehanteringssystem. Det blir extremt enkelt att se vilken kod som implementerade en viss funktion eller fix.
3.  **Överskådlighet:** Taggar gör det lätt att navigera i Git-historiken och snabbt hitta viktiga händelser, som till exempel när en specifik feature blev klar för merge.

### När ska taggen skapas?

Det absolut viktigaste tillfället att skapa en tagg i vår workflow är:

**Precis INNAN du mergar din feature-branch till `dev`-branchen.**

Taggen ska skapas på den sista committen i din feature-branch efter att den är helt färdigtestad och redo att integreras. Detta är en del av vår `GIT_END`-procedur.

### Format för taggar

Vi använder ett standardiserat format för att hålla våra taggar konsekventa och sökbara:

`TMXXX-kort-beskrivning`

* **`TMXXX`**: ID från ditt ärendehanteringssystem (Task Master). Exempel: `TM133`, `TM148`.
* **`kort-beskrivning`**: En eller två ord som beskriver uppgiften, med bindestreck mellan orden. Oftast samma som i ditt branch-namn. Exempel: `update-headers`, `fix-login-error`.

**Fullständiga exempel:**
* `TM133-update-headers`
* `TM148-fix-login-error`
* `TM151-add-user-avatar`

### Hur man skapar och pushar en tagg

Processen består av två enkla steg.

#### Steg 1: Skapa taggen lokalt

Se till att du står på din feature-branch och har committat ditt sista arbete. Kör sedan kommandot:

```bash
# Exempel
git tag TM133-update-headers
```

Detta skapar taggen `TM133-update-headers` och fäster den vid den senaste committen på din nuvarande branch.



#### Steg 2: Pusha taggen till GitHub (Viktigt!)



En `git push` skickar **inte** med taggar automatiskt. Du måste explicit pusha taggen till fjärr-repot (origin/GitHub) med följande kommando:

Bash

```
# Exempel
git push origin TM133-update-headers
```



### Hur man ser sina taggar



- **För att lista alla lokala taggar:**

  Bash

  ```
  git tag
  ```

- **För att se taggar på GitHub:** Gå till startsidan för ditt repo och klicka på länken "Tags" eller "Releases".

tability of the `dev` branch.