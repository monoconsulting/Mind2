### Importlogg

Kontoutdrag: 96429ebe-4a31-47d4-abeb-6966242b1a46

#### Workflowkörningar

1 st

WF3_FIRSTCARD_INVOICE  –  failed

Run-ID: 94  –  Source: kortmatchning_upload

Start: 2025-12-12 16:52

Senast: 2025-12-12 16:52

FirstCard-uppladdning – startsucceeded

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
Fil FC_2504.pdf (107007 bytes)
```

FirstCard-uppladdningsucceeded

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
Fil uppladdad
```

Skapa FC-dokument – startsucceeded

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
Skapar invoice_document-post
```

Skapa FC-dokumentsucceeded

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
Invoice_document registrerat
```

firstcard_invoicefailed

2025-12-12 16:52 → 2025-12-12 16:5217 s

```
OCR preparation failed: create_unified_file() missing 1 required keyword-only argument: 'source'
```

OCR FirstCardfailed

2025-12-12 16:52 → 2025-12-12 16:5217 s

```
create_unified_file() missing 1 required keyword-only argument: 'source'
```

Skapa FC-dokument – klartsucceeded

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
Invoice_document registrerat
```

FirstCard-uppladdning – klartsucceeded

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
Fil uppladdad
```

Avslutad med fel – startsucceeded

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
OCR-misslyckande: create_unified_file() missing 1 required keyword-only argument: 'source'
```

Avslutad med felfailed

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
OCR-misslyckande: create_unified_file() missing 1 required keyword-only argument: 'source'
```

Avslutad med fel – klartfailed

2025-12-12 16:52 → 2025-12-12 16:520 ms

```
OCR-misslyckande: create_unified_file() missing 1 required keyword-only argument: 'source'
```

dispatchsucceeded

\-

```
WF3 dispatched to new wf3.* chain.
```

#### AI-historik

1 poster

PDF-Conversion  –  error

Fil: 96429ebe-4a31-47d4-abeb-6966242b1a46  –  2025-12-12 16:52

pymupdf  –  fitz-dpi-300

Tid: 2.30 s

```
Failed to convert credit card PDF to page images.
```

TypeError: create_unified_file() missing 1 required keyword-only argument: 'source'

#### Filer

96429ebe-4a31-47d4-abeb-6966242b1a46Skapad: 2025-12-12 16:52  –  Uppdaterad: 2025-12-12 16:52

Filtyp: cc_pdf

Workflow-typ: creditcard_invoice

Status: uploaded

Konfidens: –

OCR-tecken: 0

<details class="bg-gray-800/50 border border-gray-700/60 rounded-md p-2" open=""><summary class="text-xs text-gray-300 cursor-pointer">Visa other_data</summary><pre class="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono overflow-x-auto">{
  "detected_kind": "pdf",
  "original_filename": "FC_2504.pdf",
  "source": "kortmatchning_upload",
  "workflow_type": "creditcard_invoice"
}</pre></details>

#### Metadata (invoice_documents)

```
{
  "detected_kind": "pdf",
  "last_progress_at": "2025-12-12T16:52:13Z",
  "mime_type": "application/pdf",
  "original_filename": "FC_2504.pdf",
  "processing_status": "uploaded",
  "source_file_id": "96429ebe-4a31-47d4-abeb-6966242b1a46",
  "submitted_by": "invoice_upload",
  "workflow_run_id": 94
}
```