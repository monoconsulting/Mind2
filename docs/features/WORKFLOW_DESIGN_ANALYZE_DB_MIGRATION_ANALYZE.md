# THIS IS DONE!

- 

- Bra, då börjar vi “på riktigt tekniskt” här. 🙂

  Jag har:

  - Packat upp hela zip:en
  - Läst alla migrations i `database/migrations/*.sql`
  - Läst strukturen i dina db-backuper:
    - `.dbbackup/Mind2_mono_se_db_9_2025-11-11_08-59.sql`
    - `.dbbackup/Mind2_mono_se_db_9_2025-11-11_09-03.sql`
  - Jämfört **varje migration** (0001–0033) mot den faktiska databasschemat i dumpen.

  ------

  ## 1. Vad finns i databasen idag?

  Från dumpen:

  - Totalt **27 tabeller**:
    - Bl.a. `unified_files`, `receipt_items`,
       `creditcard_invoices_main`, `creditcard_invoice_items`, `creditcard_receipt_matches`,
       `invoice_documents`, `invoice_lines`, `invoice_line_history`,
       `ai_processing_history`, `ai_system_prompts`, `ai_accounting_proposals`,
       `file_tags`, `file_suffix`, `file_locations`,
       `workflow_runs`, `workflow_stage_runs`, `chart_of_accounts`, `tags`, `tag_categories`, `companies` m.fl.

  Tabellerna som skapas i migrationsfilerna **0001–0033** finns alla i dumpen.
   Det betyder att alla **”tabellskapande”** delar av migrationskedjan är körda.

  Exempel (några kritiska saker):

  - `workflow_runs` + `workflow_stage_runs` finns med exakt den struktur som i `0031_create_workflow_tracking.sql`.
  - `invoice_documents` har:
    - `processing_status` (från `0026_invoice_matching_enhancements.sql`)
    - `deleted_at` + index (från `0033_add_invoice_document_soft_delete.sql`)
  - `creditcard_invoices_main` har:
    - `ocr_raw` och index `idx_creditcard_invoices_number` (från `0031_add_ocr_raw_to_creditcard_invoices.sql`)
  - `unified_files` har:
    - alla AI-relaterade kolumner (`ai_status`, `ai_confidence`)
    - alla kreditkorts-fält (last_4, brand, entering_mode osv)
    - `content_hash` (`0016`)
    - `deleted_at` + index (`0029`)
    - `workflow_type` (`0032`)
    - `matched` (`0032`)

  Så de stora, viktiga migrationsstegen **är genomförda i dumpen**.

  ------

  ## 2. Vad saknas / är inte helt synkat med migrationsfilerna?

  När jag matchar migrationsfilerna mot dumpen hittar jag **några kolumner** som migrationsfilerna vill skapa, men som **inte finns** i dumpen.

  ### 2.1 `unified_files.invoice_match_status` (0026)

  I `0026_invoice_matching_enhancements.sql`:

  - `ALTER TABLE unified_files ADD COLUMN IF NOT EXISTS invoice_match_status VARCHAR(32) ...`
  - `ALTER TABLE unified_files ADD COLUMN IF NOT EXISTS matched_invoice_id VARCHAR(36) ...`

  I dumpen:

  - `unified_files` **saknar** kolumnen `invoice_match_status`.
  - `matched_invoice_id` finns inte heller.

  Kodgenomgång:

  - Sökningar i hela kodbasen visar att
     `invoice_match_status` och `matched_invoice_id` **bara finns i**:
    - migrationsfilen 0026
    - ett par design-dokument (`MIND_INVOICE_MATCH_IMPLEMENTATION_PLAN*.md`)

  Det finns **ingen Python/JS/SQL-kod** som i runtime läser/uppdaterar dessa kolumner.

  ➡️ **Konsekvens nu:**
   Databasen saknar de här kolumnerna, men ingen aktiv kod använder dem.
   Det är mer ett “doc/design drift”, inget som stoppar systemet.

  ------

  ### 2.2 `receipt_items.item_vat_total` (0027)

  I `0027_receipt_preview_modal_enhancements.sql` finns en dynamisk bit:

  - Den försöker, via `information_schema`, lägga till:
    - `ALTER TABLE receipt_items ADD COLUMN item_vat_total ...`

  I dumpen:

  - `receipt_items` har:
    - `item_price_ex_vat`, `item_price_inc_vat`
    - `item_total_price_ex_vat`, `item_total_price_inc_vat`
    - `vat`, `vat_percentage`
  - **Men ingen** kolumn `item_vat_total`.

  Kodgenomgång:

  - Backend (`backend/src/api/receipts.py`) använder **bara** `item_vat_total` när den läser ut JSON från AI-extraktionen:

    ```python
    vat_amount = _coerce_float(raw.get("vat") or raw.get("vat_amount") or raw.get("item_vat_total"))
    ```

    Det är **inte** kopplat till databaskolumnen, utan till JSON-fält i AI3-responsen.

  - Frontend (`ReceiptPreviewModal.jsx`) använder `item.item_vat_total` i den generiska kolumnlistan, men alltid ihop med fallback:

    ```js
    toNullableNumber(
      item.vat ??
      item.item_vat ??
      item.vat_amount ??
      item.item_vat_total ??
      item.total_vat
    )
    ```

    Dvs – om fältet saknas kommer den ta något annat fält.

  ➡️ **Konsekvens nu:**
   Databasen saknar kolumnen `item_vat_total`, men ingen kod förväntar sig att den *måste finnas i tabellen*.
   Den används mer som ett potentiellt AI-fält i JSON.

  ------

  ### 2.3 `invoice_documents.source_file_id` (0026)

  I samma `0026_invoice_matching_enhancements.sql`:

  - `ALTER TABLE invoice_documents ADD COLUMN IF NOT EXISTS source_file_id VARCHAR(36) ...`

  I dumpen för `invoice_documents`:

  - Kolumner:
    - `id`, `invoice_type`, `period_start`, `period_end`,
       `uploaded_at`, `status`, `processing_status`, `metadata_json`, `deleted_at`.
  - **Ingen** kolumn `source_file_id`.

  Kodgenomgång:

  - Backend-logik (status- och upload-ändpunkter) jobbar idag med `source_file_id` **i metadata-json**, inte i tabellkolumnen:

    - `routes/status.py`:

      ```python
      source_file_id = metadata.get("source_file_id") or invoice_id
      files = list_invoice_files(source_file_id)
      ```

    - `utils/db_helpers.py`:

      ```python
      SELECT id, file_type, ai_status, ocr_raw, other_data, created_at
      FROM unified_files
      WHERE id = %s OR original_file_id = %s
      ```

  - Ingenstans ser jag en SQL mot `invoice_documents.source_file_id` i runtime-kod.

  ➡️ **Konsekvens nu:**
   Kolumnen finns inte, men den används inte.
   Allt går via `metadata_json["source_file_id"]` + `unified_files.original_file_id`.

  ------

  ## 3. Slutsats: Har databasen “alla migrations”?

  **På tabellnivå:**
   Ja. Alla tabeller som ska finnas efter `0033_add_invoice_document_soft_delete.sql` finns i dumpen.

  **På kolumnnivå:**
   Alla väsentliga kolumner för kvittoflödet, FC-flödet och manuell matchning finns.

  Några “nice to have”/framtidsfält enligt migrationsfilerna saknas i dumpen:

  1. `unified_files.invoice_match_status` (+ `matched_invoice_id`)
  2. `invoice_documents.source_file_id`
  3. `receipt_items.item_vat_total`

  Men:

  - Ingen aktiv kod använder `invoice_match_status` / `matched_invoice_id`.
  - `item_vat_total` används som JSON-fält, inte databaskolumn.
  - `source_file_id` används i metadata-json, inte i tabellkolumnen.

  Rent praktiskt betyder det att:

  - **Systemet kan köras utan att dessa kolumner finns**.
  - Men om du vill ha databasen 100 % i synk med migrationsplanen och docs är det bra att låta migrationsrutinen lägga till dem.

  ------

  ## 4. Rekommendation – hur du faktiskt “säkerställer” migrations

  För att se till att databasen verkligen motsvarar din migrationsmapp:

  ### 4.1 Sätt på auto-migration (en gång)

  I din backend-konfiguration (env):

  - Sätt `DB_AUTO_MIGRATE=1` för `ai-api`-containern.

  Då kommer:

  - `backend/src/api/app.py` under uppstart att köra igenom `database/migrations` i ordning.
  - `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` är idempotent:
    - kolumner/index som redan finns lämnas ifred,
    - saknade kolumner (`invoice_match_status`, `item_vat_total`, `source_file_id`) skapas.

  Efter en lyckad körning kan du sätta tillbaka `DB_AUTO_MIGRATE=0` om du vill ha strikt kontroll.

  ### 4.2 Alternativ: manuellt lägga till de tre kolumnerna

  Om du föredrar att göra det manuellt i t.ex. Adminer eller CLI kan du köra motsvarande delar ur migrationsfilerna:

  - `unified_files`:

    ```sql
    ALTER TABLE unified_files
      ADD COLUMN invoice_match_status VARCHAR(32) NULL
        COMMENT 'Status for invoice matching: pending, matched, unmatched, reviewed' AFTER credit_card_match,
      ADD COLUMN matched_invoice_id VARCHAR(36) NULL
        COMMENT 'FK to invoice_documents.id if matched to invoice line' AFTER invoice_match_status;
    ```

  - `invoice_documents`:

    ```sql
    ALTER TABLE invoice_documents
      ADD COLUMN source_file_id VARCHAR(36) NULL
        COMMENT 'FK to unified_files.id for uploaded PDF/image' AFTER invoice_type;
    ```

  - `receipt_items`:

    ```sql
    ALTER TABLE receipt_items
      ADD COLUMN item_vat_total DECIMAL(10,2) NULL
        COMMENT 'Total VAT amount for the item (number * vat_amount)' AFTER item_total_price_inc_vat;
    ```

  (Ingen av dem krockar med befintlig kod – de blir bara tillgängliga för framtida/loggad användning.)

  ------

  ## 5. Vad betyder detta för nästa steg?

  Du bad specifikt om **steg 1: analysera kod + databas och säkerställa migrations** – det är gjort:

  - Databasdumpen är i praktiken **i fas med migrations 0001–0033**.
  - Några planerade fält för framtida invoice-matching/preview finns inte i dumpen, men de används inte i kritisk logik.

  Nästa naturliga steg, när du vill, är:

  1. Antingen:
     - slå på `DB_AUTO_MIGRATE` och starta backend mot den här dumpen,
  2. eller:
     - köra de tre små ALTER TABLE-stegen manuellt.

  När vi gjort det kan vi ta nästa del:
   ”Hur vi får igång systemet och anpassar så att det följer kraven i dokumentationen / dina nya krav”.