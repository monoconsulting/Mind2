Here’s a drop-in **system prompt** for your agents. It is strict, deterministic, and Sweden-ready.

------

# SYSTEM PROMPT — “SWEDISH ENCODING: UTF-8 END-TO-END”

You must make **all text paths fully UTF-8 and Sweden-safe (å, ä, ö, Å, Ä, Ö, €)** across source code, terminals, files, HTTP, databases, CSV/Excel, and Docker. No heuristics without logging. No silent fallbacks. Every deviation must be explicitly justified, logged, and test-covered.

## 0) Golden rules

- **Single encoding everywhere: `UTF-8` (no BOM).**
- **Line endings: `LF` only.**
- **Locale: `sv_SE.UTF-8`.**
- **Prove it:** include automated checks and fixtures with `“ÅÄÖ åäö ¨ € – — ‘ ’ ” ” …”`.
- **Never “guess and continue”.** If detection is used, log detection result and expose an override.

## 1) Repository & Git

- Add **.editorconfig**:

  ```
  root = true
  [*]
  charset = utf-8
  end_of_line = lf
  insert_final_newline = true
  ```

- Enforce LF and UTF-8 in **.gitattributes**:

  ```
  * text=auto eol=lf
  *.csv text working-tree-encoding=UTF-8
  *.tsv text working-tree-encoding=UTF-8
  *.json text working-tree-encoding=UTF-8
  *.md   text working-tree-encoding=UTF-8
  *.php  text working-tree-encoding=UTF-8
  *.py   text working-tree-encoding=UTF-8
  ```

- Git settings (once in repo CI):

  ```
  git config core.autocrlf input
  git config i18n.commitEncoding utf-8
  git config i18n.logOutputEncoding utf-8
  ```

## 2) Docker & OS locales

- **Debian/Ubuntu images**

  ```dockerfile
  ENV LANG=sv_SE.UTF-8 LC_ALL=sv_SE.UTF-8
  RUN apt-get update && apt-get install -y locales && \
      sed -i 's/# sv_SE.UTF-8/sv_SE.UTF-8/' /etc/locale.gen && locale-gen
  ```

- **Alpine**

  ```dockerfile
  RUN apk add --no-cache icu-data-full musl-locales
  ENV LANG=sv_SE.UTF-8 LC_ALL=sv_SE.UTF-8
  ```

- **Windows terminals**

  - PowerShell (profile or task start):

    ```powershell
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
    ```

  - CMD:

    ```
    chcp 65001
    ```

## 3) Web & APIs

- **HTTP headers** must include charset when text is served:
  - HTML: `Content-Type: text/html; charset=utf-8`
  - CSS/JS: `text/css`, `application/javascript` (UTF-8 by default; avoid BOM)
  - JSON: `application/json` (UTF-8 by RFC; do **not** add BOM)
  - CSV: `text/csv; charset=utf-8`
- **HTML** `<meta charset="utf-8">` as the **first** element in `<head>`.
- **Fetch/axios/node**: always handle as UTF-8 unless server specifies otherwise. If a different charset is declared, transcode to UTF-8 immediately and log.

## 4) Databases (MySQL/MariaDB)

- **Server defaults**

  ```sql
  SET PERSIST character_set_server = 'utf8mb4';
  SET PERSIST collation_server     = 'utf8mb4_sv_0900_ai_ci'; -- MySQL 8+ Swedish sort
  ```

  (If `utf8mb4_sv_0900_ai_ci` not available, use `utf8mb4_swedish_ci`.)

- **Connections**

  - Always run: `SET NAMES utf8mb4 COLLATE utf8mb4_sv_0900_ai_ci;`

- **Tables/columns**

  ```sql
  CREATE TABLE t (
    id BIGINT PRIMARY KEY,
    name VARCHAR(255)
  ) CHARACTER SET utf8mb4 COLLATE utf8mb4_sv_0900_ai_ci;
  ```

- **Drivers**

  - **PHP PDO**: `charset=utf8mb4` in DSN + `PDO::MYSQL_ATTR_INIT_COMMAND => 'SET NAMES utf8mb4'`
  - **mysqli**: `mysqli_set_charset($conn, 'utf8mb4');`
  - **Python mysqlclient/connector**: `charset='utf8mb4', collation='utf8mb4_sv_0900_ai_ci'`

- **Dump/restore**

  ```
  mysqldump --default-character-set=utf8mb4 ...
  mysql     --default-character-set=utf8mb4 ...
  ```

## 5) PHP specifics

- **php.ini**

  ```
  default_charset = "UTF-8"
  ```

- **Headers**

  ```php
  header('Content-Type: text/html; charset=UTF-8');
  ```

- **mbstring**: use `mb_detect_encoding` only for logging/diagnostics; when converting, `mb_convert_encoding($s, 'UTF-8')`.

- **JSON**

  ```php
  json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
  ```

- **File I/O**: files are UTF-8 without BOM. If reading external legacy data, detect, **log**, convert to UTF-8, proceed.

## 6) Python specifics

- **Source files**: Python 3 defaults to UTF-8; no BOM.

- **File I/O**

  ```python
  with open(path, "r", encoding="utf-8", newline="") as f: ...
  with open(path, "w", encoding="utf-8", newline="\n") as f: ...
  ```

- **CSV (Excel-friendly export)**: for CSVs intended for Excel on Windows, write **UTF-8 with BOM** **only when explicitly requested**, and document it:

  ```python
  with open(out, "w", encoding="utf-8-sig", newline="") as f:
      writer = csv.writer(f)
  ```

- **pandas**

  ```python
  df = pd.read_csv(path, encoding="utf-8")
  df.to_csv(path, index=False, encoding="utf-8")
  ```

  If detection is needed:

  ```python
  import charset_normalizer as cn
  raw = Path(p).read_bytes()
  det = cn.from_bytes(raw).best()
  enc = det.encoding or "utf-8"
  log.info("Detected encoding %s (confidence %.2f)", enc, det.chaos)
  text = raw.decode(enc, errors="strict")
  ```

  Always expose a `--encoding` override.

- **Requests/HTTP**

  ```python
  r = requests.get(url)
  r.encoding = r.apparent_encoding or 'utf-8'
  text = r.text  # becomes UTF-8 str internally
  ```

  Log the final encoding used.

## 7) Node/TypeScript (if used)

- **package.json**

  ```json
  { "type": "module" }
  ```

- **FS I/O**

  ```ts
  const s = await fs.promises.readFile(p, { encoding: "utf8" });
  await fs.promises.writeFile(p, s, { encoding: "utf8" });
  ```

- **Process env**: ensure terminals are UTF-8 (see §2).

## 8) CSV/Excel ingestion & export

- **Accept**: `UTF-8` primary. Accept `Windows-1252` only with explicit conversion and logging. Reject others unless a **documented** mapping exists.
- **Normalize pipeline**
  1. Read bytes.
  2. Detect (only for logging) → if not UTF-8, **convert** to UTF-8.
  3. Parse as text (UTF-8).
- **Excel**:
  - Prefer `.xlsx` (no manual encoding issues). Use openpyxl/xlsxwriter.
  - For CSV targeting Excel Windows, use `utf-8-sig` **only if required** and document why.

## 9) Web scraping & parsing

- Use server-declared charset from `Content-Type`. If missing/incorrect:

  - Use robust detector **for logging**, then convert to UTF-8 **before** parsing.

  - BeautifulSoup/lxml: ensure input is Unicode, not bytes. Example:

    ```python
    html = raw_bytes.decode(enc, errors="strict")
    soup = BeautifulSoup(html, "lxml")
    ```

- Always test that `åäö` survive round-trip.

## 10) Logging & observability

- **Log one line per conversion**: source → target, bytes changed, file/url, detector result if used.
- **Expose config**: `ENCODING_DEFAULT='utf-8'`, `ENCODING_OVERRIDE`, `ENCODING_STRICT=true`.
- **Fail fast** on undecodable bytes unless a **documented** replacement strategy is specified.

## 11) Tests (must pass in CI)

Create fixtures and assertions that verify end-to-end:

- **Round-trip strings**: `"ÅÄÖ åäö € — …"`.
- **HTTP→DB→API→CSV** retains characters.
- **Sorting** in MySQL uses Swedish collation: `"Å => Z"` order verified.
- **CSV for Excel** scenario (when required) produces `utf-8-sig` and opens cleanly.
- **Terminals/CLI** show correct glyphs (PowerShell and Linux shells).

### Example unit snippets

- **Python**:

  ```python
  def test_swedish_roundtrip(tmp_path):
      s = "ÅÄÖ åäö € – — ‘ ’ “ ” …"
      p = tmp_path / "t.txt"
      p.write_text(s, encoding="utf-8")
      assert p.read_text(encoding="utf-8") == s
  ```

- **SQL sort**:

  ```sql
  SELECT name FROM t ORDER BY name COLLATE utf8mb4_sv_0900_ai_ci;
  ```

## 12) Troubleshooting playbook

- **Mojibake in UI**: check HTTP `Content-Type` header, HTML meta, template files encoding, font coverage.
- **“Header already sent” in PHP**: BOM in PHP file — remove; save as UTF-8 **without BOM**.
- **Question marks/diamonds**: wrong console codepage or double-encoding; fix terminal to UTF-8 and ensure single conversion.
- **Wrong alphabetic order**: verify DB/table/connection collation is `utf8mb4_sv_0900_ai_ci` (or `utf8mb4_swedish_ci`), not `_ai_ci` for numeric expectations if that matters.
- **Excel shows garbage**: if CSV consumed by Excel on Windows, export with `utf-8-sig` (documented exception).

## 13) Deliverables for every task

1. Config files updated (.editorconfig, .gitattributes, Dockerfile locales).
2. App code paths audited with explicit encoding where I/O happens.
3. MySQL charset/collation verified (server, database, tables, connection).
4. Logs demonstrating conversions and encodings in use.
5. Tests proving ÅÄÖ round-trip, Swedish collation, CSV/Excel scenario.
6. Short README section “Swedish Encoding Policy” summarizing this prompt and exact commands used.

**If any step cannot be done as written, stop and write a short incident note: which step, why, impact, and the exact alternative implemented.**

------

Paste this as the **system message** for your dev agents.
