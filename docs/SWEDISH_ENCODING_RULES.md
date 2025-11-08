# SWEDISH_ENCODING_RULES

Version: 1.1  
Senast uppdaterad: 2025-11-07

## Varför dokumentet finns
- Alla agenter ska omedelbart förstå att svenska tecken (å, ä, ö, Å, Ä, Ö) **måste** fungera överallt.
- Flera buggar i kortmatchning/loggmodulen berodde på felaktig kodning (Ã¤ etc.). Vi accepterar inte fler sådana regressioner.
- Dokumentet fungerar som en mini-systemprompt: läs och följ innan du skriver kod eller dokumentation.

## Grundregler
1. **Endast UTF-8 utan BOM**  
   - VS Code: `File → Save with Encoding → UTF-8`.  
   - JetBrains: `File → File Properties → File Encoding → UTF-8`.  
   - Kontrollera `git config core.autocrlf false` och att `.editorconfig` gäller.
2. **Verifiera svenska tecken**  
   - Lägg till kontrollsträngen `ÅÄÖ åäö – Kontrollrad` i nya filer under utveckling (ta bort innan commit om den stör).  
   - Om filen inte klarar detta: stoppa, fixa encoding, testa igen.
3. **Terminal / shell**  
   - PowerShell: `chcp 65001`.  
   - Bash: `export LANG=sv_SE.UTF-8 LC_ALL=sv_SE.UTF-8`.
4. **JSON/CSV/XLSX**  
   - JSON/CSV: skriv alltid `ensure_ascii=False` (Python) eller motsvarande när du serialiserar.  
   - XLSX export: använd verktyg som genererar UTF-8/UTF-16; om kunden kräver ANSI, skapa ett separat steg som dokumenteras här innan leverans.
5. **Webb-UI**  
   - `<meta charset="utf-8">` måste ligga överst i `<head>`.  
   - Testa visuellt: öppna logg- och statusmoduler, verifiera å/ä/ö på Windows och macOS.

## Plan-påminnelse
Varje arbetsplan ska innehålla punkterna:
- “Bekräfta att filerna redigeras som UTF-8 och att svenska specialtecken visas korrekt.”
- “Kör encoding-kontroll (minst en teststräng med ÅÄÖ) innan leverans.”

## Testa att encoding inte bryts
1. **CLI-smoke**
   - `rg "å|ä|ö" -n <sökväg>` ska visa riktiga tecken, aldrig `Ã¥`.
   - `python - <<'PY'\nprint("ÅÄÖ åäö – Kontrollrad")\nPY` måste skriva ut korrekt i terminalen.
2. **Frontend**
   - Öppna modaler/tabeller med svensk text. Om du ser `Ã` eller `?` måste buggen fixas innan PR.
3. **Backend/API**
   - Returnera JSON med `Göteborg`, `Malmö`, `Åre` i integrationstester.
   - Lägg till pytest som validerar `response.text.encode('utf-8').decode('utf-8') == response.text`.

## När du hittar encodingproblem
- Stoppa allt arbete. Skapa issue eller kommentar med fil, rad och verktyg som orsakade felet.
- Beskriv miljö (OS, editor, terminalkodning) och lägg till minimal reproduktion.
- Lös aldrig genom att byta port eller starta om tjänster; fixa koden eller konfigurationen.

## Checklista före leverans
- [ ] Har du manuellt sett `ÅÄÖ åäö` i alla filer du rört?  
- [ ] Är `git diff` fritt från ersättningstecken `�`?  
- [ ] Nämner PR-beskrivningen att encoding kontrollerats?  
- [ ] Har du uppdaterat detta dokument om nya regler behövs?

Genom att följa planen finns inga ursäkter för “konsekvent fel encoding” längre.
