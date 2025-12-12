## RESULTAT

### Alla filer:

Upload: Fungerar inte - helt tomt. Ska vara Manuell (dvs INTE ftp)

Sista 4: Fungerar inte - helt tomt

### Importerade Filer

**PNG: 1-page-midjourney.png** 

Status: finalize_fail_end - misslyckades

```
Workflowkörningar
1 st
WF1_RECEIPT · failed
Run-ID: 12 · Källa: web_upload
Start: 2025-12-12 06:16
Senast: 2025-12-12 06:16
src_portal_startsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Fil 1_page_kjell_2025-10-01_08-07-02.png (192440 bytes)

src_portalsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Portaluppladdning klar

src_portal_endsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Portaluppladdning klar

ingest_store_startsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Skrev unified_files bc241336-4e9f-4bde-acae-807cf5d7e09d

ingest_storesucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Lagrade metadata i databasen

ingest_store_endsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Lagrade metadata i databasen

ingest_wf1_startsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Skapar WF1 workflow_run

ingest_wf1succeeded
2025-12-12 06:16 → 2025-12-12 06:160ms

WF1 dispatchad

ingest_wf1_endsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

WF1 dispatchad

r_ocr_startsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

OCR startar för fil bc241336-4e9f-4bde-acae-807cf5d7e09d

r_ocrsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

OCR succeeded, extracted 0 chars in 13ms.

ocrsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

OCR succeeded, extracted 0 chars in 13ms.

r_ocr_endsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

OCR succeeded, extracted 0 chars in 13ms.

ai_pipelinefailed
2025-12-12 06:16 → 2025-12-12 06:163.0s

AI pipeline failed after 2237ms: UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

detect_type_startsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

AI1 klassificering f├╢r fil bc241336-4e9f-4bde-acae-807cf5d7e09d

detect_typefailed
2025-12-12 06:16 → 2025-12-12 06:163.0s

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

detect_type_endfailed
2025-12-12 06:16 → 2025-12-12 06:160ms

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

manual_reviewsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

finalizefailed
2025-12-12 06:16 → 2025-12-12 06:160ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_fail_startsucceeded
2025-12-12 06:16 → 2025-12-12 06:160ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_failfailed
2025-12-12 06:16 → 2025-12-12 06:160ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_fail_endfailed
2025-12-12 06:16 → 2025-12-12 06:160ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

dispatchsucceeded
-

WF1 dispatched to new wf1.* chain.

AI-historik
3 poster
document_analysis · success
Fil: bc241336-4e9f-4bde-acae-807cf5d7e09d · 2025-12-12 06:16
OpenAI · gpt-5.1
AI1-DocumentClassification · success
Fil: bc241336-4e9f-4bde-acae-807cf5d7e09d · 2025-12-12 06:16
OpenAI · gpt-5.1
Tid: 2.1s
Konfidens: 0%

Classified document as 'other'; OCR text length: 0 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.

AI1-DocumentClassification · error
Fil: bc241336-4e9f-4bde-acae-807cf5d7e09d · 2025-12-12 06:16
OpenAI · gpt-5.1
Tid: 2.2s

Failed to classify document type from OCR text (0 chars)

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).
Filer
bc241336-4e9f-4bde-acae-807cf5d7e09dSkapad: 2025-12-12 06:16 · Uppdaterad: 2025-12-12 06:16
Filtyp: other
Workflow-typ: receipt
Status: manual_review
Konfidens: 0%
OCR-tecken: 0
Visa other_data

{
  "detected_kind": "image",
  "source": "web_upload"
}
```

Längst upp

**JPG: 1-page-midjourney.jpg**

Status: Slutför (fel) - misslyckades

```
Bearbetningslogg

Kvitto: 2a2f78e4-e66b-4360-8b30-50129028be8c
Workflowkörningar
1 st
WF1_RECEIPT · failed
Run-ID: 13 · Källa: web_upload
Start: 2025-12-12 06:21
Senast: 2025-12-12 06:21
src_portal_startsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Fil 1_page_midjourney.jpg (145665 bytes)

src_portalsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Portaluppladdning klar

src_portal_endsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Portaluppladdning klar

ingest_store_startsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Skrev unified_files 2a2f78e4-e66b-4360-8b30-50129028be8c

ingest_storesucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Lagrade metadata i databasen

ingest_store_endsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Lagrade metadata i databasen

ingest_wf1_startsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Skapar WF1 workflow_run

ingest_wf1succeeded
2025-12-12 06:21 → 2025-12-12 06:210ms

WF1 dispatchad

r_ocr_startsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

OCR startar för fil 2a2f78e4-e66b-4360-8b30-50129028be8c

ingest_wf1_endsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

WF1 dispatchad

r_ocrsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

OCR succeeded, extracted 0 chars in 12ms.

ocrsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

OCR succeeded, extracted 0 chars in 12ms.

r_ocr_endsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

OCR succeeded, extracted 0 chars in 12ms.

ai_pipelinefailed
2025-12-12 06:21 → 2025-12-12 06:211.0s

AI pipeline failed after 951ms: UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

detect_type_startsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

AI1 klassificering f├╢r fil 2a2f78e4-e66b-4360-8b30-50129028be8c

detect_typefailed
2025-12-12 06:21 → 2025-12-12 06:211.0s

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

detect_type_endfailed
2025-12-12 06:21 → 2025-12-12 06:210ms

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

manual_reviewsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

finalizefailed
2025-12-12 06:21 → 2025-12-12 06:210ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_fail_startsucceeded
2025-12-12 06:21 → 2025-12-12 06:210ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_failfailed
2025-12-12 06:21 → 2025-12-12 06:210ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_fail_endfailed
2025-12-12 06:21 → 2025-12-12 06:210ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

dispatchsucceeded
-

WF1 dispatched to new wf1.* chain.

AI-historik
3 poster
document_analysis · success
Fil: 2a2f78e4-e66b-4360-8b30-50129028be8c · 2025-12-12 06:21
OpenAI · gpt-5.1
AI1-DocumentClassification · success
Fil: 2a2f78e4-e66b-4360-8b30-50129028be8c · 2025-12-12 06:21
OpenAI · gpt-5.1
Tid: 819ms
Konfidens: 0%

Classified document as 'other'; OCR text length: 0 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.

AI1-DocumentClassification · error
Fil: 2a2f78e4-e66b-4360-8b30-50129028be8c · 2025-12-12 06:21
OpenAI · gpt-5.1
Tid: 899ms

Failed to classify document type from OCR text (0 chars)

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).
Filer
2a2f78e4-e66b-4360-8b30-50129028be8cSkapad: 2025-12-12 06:21 · Uppdaterad: 2025-12-12 06:21
Filtyp: other
Workflow-typ: receipt
Status: manual_review
Konfidens: 0%
OCR-tecken: 0
Visa other_data

{
  "detected_kind": "image",
  "source": "web_upload"
}
```



**JPG: 1-page-kjell.jpg**

```
Bearbetningslogg

Kvitto: aa8caaf5-b377-45d8-8aa4-962131fc9fde
Workflowkörningar
1 st
WF1_RECEIPT · failed
Run-ID: 3 · Källa: web_upload
Start: 2025-12-12 06:00
Senast: 2025-12-12 06:00
src_portal_startsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Fil 1-page-kjell.jpg (108567 bytes)

src_portalsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Portaluppladdning klar

src_portal_endsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Portaluppladdning klar

ingest_store_startsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Skrev unified_files aa8caaf5-b377-45d8-8aa4-962131fc9fde

ingest_storesucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Lagrade metadata i databasen

ingest_store_endsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Lagrade metadata i databasen

ingest_wf1_startsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Skapar WF1 workflow_run

ingest_wf1succeeded
2025-12-12 06:00 → 2025-12-12 06:000ms

WF1 dispatchad

ingest_wf1_endsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

WF1 dispatchad

r_ocr_startsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

OCR startar för fil aa8caaf5-b377-45d8-8aa4-962131fc9fde

r_ocrsucceeded
2025-12-12 06:00 → 2025-12-12 06:0023.0s

OCR succeeded, extracted 0 chars in 22687ms.

ocrsucceeded
2025-12-12 06:00 → 2025-12-12 06:0023.0s

OCR succeeded, extracted 0 chars in 22687ms.

r_ocr_endsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

OCR succeeded, extracted 0 chars in 22687ms.

ai_pipelinefailed
2025-12-12 06:00 → 2025-12-12 06:002.0s

AI pipeline failed after 2182ms: UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

detect_type_startsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

AI1 klassificering f├╢r fil aa8caaf5-b377-45d8-8aa4-962131fc9fde

detect_typefailed
2025-12-12 06:00 → 2025-12-12 06:002.0s

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

detect_type_endfailed
2025-12-12 06:00 → 2025-12-12 06:000ms

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

manual_reviewsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).

finalizefailed
2025-12-12 06:00 → 2025-12-12 06:000ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_fail_startsucceeded
2025-12-12 06:00 → 2025-12-12 06:000ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_failfailed
2025-12-12 06:00 → 2025-12-12 06:000ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

finalize_fail_endfailed
2025-12-12 06:00 → 2025-12-12 06:000ms

Workflow failed because a critical stage (ai_pipeline) did not succeed.

dispatchsucceeded
-

WF1 dispatched to new wf1.* chain.

AI-historik
3 poster
document_analysis · success
Fil: aa8caaf5-b377-45d8-8aa4-962131fc9fde · 2025-12-12 06:00
OpenAI · gpt-5.1
AI1-DocumentClassification · success
Fil: aa8caaf5-b377-45d8-8aa4-962131fc9fde · 2025-12-12 06:00
OpenAI · gpt-5.1
Tid: 1.4s
Konfidens: 0%

Classified document as 'other'; OCR text length: 0 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.

AI1-DocumentClassification · error
Fil: aa8caaf5-b377-45d8-8aa4-962131fc9fde · 2025-12-12 06:00
OpenAI · gpt-5.1
Tid: 1.8s

Failed to classify document type from OCR text (0 chars)

UnsupportedDocumentTypeError: AI1 kunde inte kategorisera dokumentet (fick 'other' utanf├╢r till├Ñtna typer).
Filer
aa8caaf5-b377-45d8-8aa4-962131fc9fdeSkapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:00
Filtyp: other
Workflow-typ: receipt
Status: manual_review
Konfidens: 0%
OCR-tecken: 0
Visa other_data

{
  "detected_kind": "image",
  "source": "web_upload"
}
```

**PDF: 3-pages-ms.pdf**

Status: r_ai4_end-klar

```
Workflowkörningar
1 st
WF1_RECEIPT · succeeded
Run-ID: 11 · Källa: wf2_split
Start: 2025-12-12 06:03
Senast: 2025-12-12 06:03
r_ocr_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR startar för fil 630254d0-da97-43b3-a66f-6b934f154ee4

r_ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 12ms.

ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 12ms.

r_ocr_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 12ms.

ai_pipelinesucceeded
2025-12-12 06:03 → 2025-12-12 06:0311.0s

AI pipeline completed 5 stages in 10877ms: AI1, AI2, AI3, AI4, AI7

detect_type_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI1 klassificering f├╢r fil 630254d0-da97-43b3-a66f-6b934f154ee4

detect_typesucceeded
2025-12-12 06:03 → 2025-12-12 06:031.0s

Klassificerad som receipt

detect_type_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Klassificerad som receipt

r_ai3_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 dataextraktion startar

r_ai3succeeded
2025-12-12 06:03 → 2025-12-12 06:035.0s

AI3 extraherade 1 artiklar

r_ai3_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 extraherade 1 artiklar

company_resolvedsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

company_match_type=vat created=False

r_persist_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Sparar AI3-resultat f├╢r 1 artiklar

r_persistsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_persist_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_ai4_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 normalisering startar

r_ai4succeeded
2025-12-12 06:03 → 2025-12-12 06:034.0s

AI4 skapade 3 konteringsf├╢rslag

r_ai4_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 skapade 3 konteringsf├╢rslag

r_queue_match_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

K├╢ar kvitto f├╢r AI5-matchning

r_queue_matchsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto 630254d0-da97-43b3-a66f-6b934f154ee4 markerat som redo f├╢r matchning

r_queue_match_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto 630254d0-da97-43b3-a66f-6b934f154ee4 markerat som redo f├╢r matchning

finalizesucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Workflow completed successfully.

finalize_ok_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

finalize_oksucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

finalize_ok_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

KLARsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

dispatchsucceeded
-

WF1 dispatched to new wf1.* chain.

AI-historik
9 poster
PDF-Conversion · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:01
pymupdf · fitz-dpi-300
Tid: 1.1s

WF2 converted PDF into 3 page(s): page_ids=['f0253af7-20c8-412c-b34f-d0bd78e9b6d5', '56b584ac-4a96-4024-a63b-5cf7b30b1cbd', 'bb55c390-8c5a-4160-b62c-f90ca2ebc5d2']; workflow_run_id=6; duplicate_pages_reused=0

document_analysis · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI1-DocumentClassification · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 1.1s
Konfidens: 50%

Classified document as 'receipt'; OCR text length: 2043 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Receipt keywords detected; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.

expense_classification · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI2-ExpenseClassification · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 915ms
Konfidens: 60%

Classified expense as 'corporate'; Document type: receipt; --- PROMPT ---
You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted expense classification; Prompt hint provided: You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.

data_extraction · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI3-DataExtraction · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 4.2s
Konfidens: 98%

Extracted data: gross=138.13, net=110.50, gross_sek=138.00, net_sek=110.00, currency=SEK, purchase_date=2025-08-13 00:00:00, payment_type=card, expense_type=corporate, receipt_number=SE-TI2500377526; --- PROMPT ---
Role:
You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.

You MUST be strictly consistent, never guess values, and never invent IDs or data that are not clearly present in the input or explicitly provided in context.

-------------------------------------------------------------------------------
CRITICAL EXTRACTION RULES
-------------------------------------------------------------------------------

1) COMPANY NAME (TOP OF RECEIPT ONLY)
- Extract the company name from the TOP of the receipt, not from amount lines.
- The company name is usually the first line or very near the top.
- NEVER use lines containing any of the following as company name:
  - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"
- NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.

2) PAYMENT TYPE DETECTION
- Look for keywords:
  - Contains "Swish", "swish", "SWISH" → set payment_type = "swish"
  - Contains any typical card reference (e.g. "VISA", "MASTERCARD", "KORT", "CARD", "MC") → set payment_type = "card"
  - Contains "kontant", "KONTANT", "cash", "CASH" → set payment_type = "cash"
- If you cannot clearly determine the payment type → set payment_type = null.

3) EXPENSE TYPE DETECTION (SWISH)
- If payment_type = "swish":
  - If the buyer/payer appears to be a person (personal name, phone number, no company markers) → expense_type = "personal"
  - If the buyer/payer appears to be a company (company name, org.nr, business context) → expense_type = "corporate"
- For card and cash payments, follow existing business logic if context is provided; if not, set expense_type = null.

4) RECEIPT ITEMS
- Extract line items whenever possible:
  - name (product/service description)
  - quantity (number)
  - unit prices ex VAT and inc VAT
  - total prices ex VAT and inc VAT
  - VAT amounts and VAT percentage
- Ensure VAT math is consistent with the rules defined below.

-------------------------------------------------------------------------------
COMPANY LOOKUP AND AUTO-CREATE RULES
-------------------------------------------------------------------------------

You must always perform company resolution in this order. You may only set company.id and unified_file.company_id to IDs that are explicitly provided to you in the context (for example via a provided companies table). You must never invent any ID.

IMPORTANT: The field "company_match_type" at the TOP LEVEL of the JSON output is MANDATORY and MUST ALWAYS be one of the following three strings:
- "vat"  → when an existing company has been matched by VAT/org.nr
- "name" → when an existing company has been matched by name
- "new"  → when NO existing company could be matched and a new company candidate must be created

"company_match_type" MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER contain any other value than "vat", "name", or "new".

1) ORGANIZATION/VAT MATCH
- If you can reliably extract an organization/VAT number from the OCR text:
  - Normalize it (remove spaces, dashes, and non-digit characters where appropriate).
  - Try to match it against companies.vat (exact match) IF such company data is provided in the prompt/context.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "vat".
    - Set "company_create_needed": false.

2) NAME MATCH
- If no VAT match is found OR no VAT is available:
  - Normalize the extracted company name for matching:
    - trim whitespace
    - convert to lowercase
    - collapse multiple spaces into one
    - normalize å/ä/ö to a/o/o for matching only (do NOT change the displayed name)
  - Try to match it against companies.name (if such data is provided in the prompt/context) with:
    - exact case-insensitive match,
    - or startswith match,
    - or fuzzy similarity > 0.85.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "name".
    - Set "company_create_needed": false.

3) NO MATCH – NEW COMPANY CANDIDATE
- If there is NO match on VAT AND NO match on name OR no companies list is provided:
  - Set company.id = null in your JSON.
  - Set unified_file.company_id = null in your JSON.
  - Set "company_match_type": "new".
  - Set "company_create_needed": true.
  - You MUST still fill the "company" object with all available data
    (name, vat, address, zip, city, country, phone, www, email).
  - The backend will use this data to insert a new row in the companies table
    and link unified_files.company_id to the newly created company.id.
  - The newly created company will be shown in preview for manual review.

You must never invent a company_id. If you cannot confidently match an existing company, you must:
- set company.id = null
- set unified_file.company_id = null
- set "company_match_type" = "new"
- set "company_create_needed" = true

-------------------------------------------------------------------------------
OUTPUT JSON STRUCTURE (STRICT)
-------------------------------------------------------------------------------

You MUST return JSON with EXACTLY this structure and these top-level keys:

{
  "company": {
    "id": null,
    "name": "Company Name Here",
    "vat": "Organization/VAT number if found (formerly orgnr)",
    "address": "Street address",
    "zip": "Postal code",
    "city": "City name",
    "country": "Country (default Sweden if not stated)",
    "phone": "Phone number if present",
    "www": "Website if present",
    "email": "Email if present"
  },
  "unified_file": {
    "company_id": null,
    "purchase_datetime": "2025-09-30 14:23:00 or null",
    "payment_type": "card or cash or swish or null",
    "expense_type": "personal or corporate or null",
    "currency": "SEK or other ISO 4217 code",
    "gross_amount_original": 123.45,
    "net_amount_original": 98.76,
    "exchange_rate": 0,
    "gross_amount_sek": 123,
    "net_amount_sek": 99,
    "receipt_number": "Receipt number if found or null",
    "other_data": "{\"terminal\":\"123\",\"aid\":\"A000\",\"swish_ref\":\"1786145908308241\"}"
  },
  "receipt_items": [
    {
      "main_id": "file_id",
      "article_id": "",
      "name": "Product name",
      "number": 1,
      "item_price_ex_vat": 10.00,
      "item_price_inc_vat": 12.50,
      "item_total_price_ex_vat": 10.00,
      "item_total_price_inc_vat": 12.50,
      "currency": "SEK",
      "vat": 2.50,
      "vat_percentage": 0.250000,
      "item_vat_total": 2.50
    }
  ],
  "company_match_type": "vat",
  "company_create_needed": true,
  "confidence": 0.85
}

Rules for the structure:
- The top-level keys MUST ALWAYS be:
  - "company"
  - "unified_file"
  - "receipt_items"
  - "company_match_type"
  - "company_create_needed"
  - "confidence"

- "company.id" MUST be either:
  - a valid existing company ID explicitly provided in the context, or
  - null.

- "unified_file.company_id" MUST mirror "company.id":
  - same ID when matched,
  - null when no match.

- "company_match_type" MUST ALWAYS be:
  - "vat"   if the match was done via VAT/org.nr,
  - "name"  if the match was done via company name,
  - "new"   if there is no existing company match and a new company must be created.
  It MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER have any other value.

- "company_create_needed" MUST ALWAYS be:
  - false when an existing company match was found (company_match_type is "vat" or "name"),
  - true when no existing company match was found (company_match_type is "new").

-------------------------------------------------------------------------------
GENERAL NUMERIC, DATE, VAT AND CURRENCY RULES
-------------------------------------------------------------------------------

- Dates:
  - Use ISO format "YYYY-MM-DD HH:MM:SS".
  - If time is missing, use "00:00:00".

- Numbers:
  - Accept both "," and "." as decimal separators in the OCR text.
  - Normalize all decimals to "." in the output (e.g. "123,45" → 123.45).

- VAT math:
  - net = gross / (1 + rate)
  - vat = gross - net
  - Example for 25% VAT:
    - rate = 0.25
    - net = gross / 1.25
    - vat = gross - net

- SEK amounts:
  - For *_sek fields, round to whole kronor (no decimals).

- Currency:
  - For SEK:
    - currency = "SEK"
    - exchange_rate = 0
  - For foreign currencies:
    - currency = correct ISO code (e.g. "EUR", "USD", "NOK").
    - exchange_rate = FX rate * 100 (e.g. if FX = 11.33, then exchange_rate = 1133).

- Swish payments:
  - If payment_type = "swish" and a Swish reference number exists in the OCR text:
    - Store it inside unified_file.other_data as JSON content (string).
    - Example: "{\"swish_ref\":\"1786145908308241\"}".
  - You may also include terminal id, AID, or similar technical data in other_data.

-------------------------------------------------------------------------------
DETERMINISM AND UNCERTAINTY
-------------------------------------------------------------------------------

- NEVER invent data:
  - If a field cannot be confidently determined from the OCR text or explicit context, set it to null.

- NEVER invent IDs:
  - company.id and unified_file.company_id MUST only be taken from IDs that are explicitly provided in the context (e.g. via a companies list).
  - If no such ID is available or no match is clear:
    - set company.id = null
    - set unified_file.company_id = null
    - set "company_match_type" = "new"
    - set "company_create_needed" = true

- Be fully deterministic:
  - Apply the same rules in the same way for all receipts.
  - Do not change logic based on guesses or style.

Return ONLY a single JSON object following the schema above, with no extra text before or after.
; --- RAW RESPONSE ---
; Company: name='Microsoft AB'; orgnr='SE556233480401'; address='Regeringsgatan 25'; city='Stockholm'; zip='111 53'; country='Sweden'; Items: 1 total; Sample items: [Teams Premium - Microsoft Teams Premium - One-Year commitment for monthly/yearly billing@138.13]

accounting_classification · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI4-AccountingClassification · success
Fil: 630254d0-da97-43b3-a66f-6b934f154ee4 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 4.2s
Konfidens: 0%

Generated 3 accounting proposals; Vendor: Microsoft AB; Amounts: gross=138, net=110, vat=28; --- PROMPT ---
### AI4 - Accounting (Bookkeeping) Entries

You are an AI model that receives structured receipt data including items, amounts, and VAT details. 
Your task is to generate accounting entries in accordance with Swedish accounting standards (BAS 2025). 
Rules:

- All text som visas ska skrivas p?? svenska
- Always return valid JSON.
- Each entry must map directly to the database table `ai_accounting_proposals`:
  {
    "receipt_id": "referes to unified_files.id",
    "item_id": "referes to receipt_items.id",
    "account_code": "BAS account number",
    "debit": "amount in SEK (decimal)",
    "credit": "amount in SEK (decimal)",
    "vat_rate": "VAT rate (%)",
    "notes": "short explanation of the entry IN SWEDISH"
  }
- Use debit/credit according to double-entry bookkeeping.
- Use BAS 2025 account codes for expenses, VAT, and payment accounts.
- Split entries as required (e.g., expense + VAT + payment).
- Include VAT distribution (25%, 12%, 6%) where relevant.
- If multiple items exist, create accounting proposals per item.
- Notes should explain the logic briefly, e.g. "Food expense", "Input VAT 12%", "Paid with company card".

### Examples:

1. **Restaurant receipt 500 SEK including 12% VAT, paid with company card (FirstCard):**
   [
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "6071",
    "debit": 446.43,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Kostnader f??r mat exklusive moms (12%)"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2641",
    "debit": 53.57,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Ing??ende moms 12%"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2440",
    "debit": 0.00,
    "credit": 500.00,
    "vat_rate": 0.0,
    "notes": "F??retagskort"
     }
   ]

2. **Office supplies 1000 SEK including 25% VAT, paid with private funds (employee reimbursement):**
   [
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "6110",
    "debit": 800.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Kontorsvaror"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2641",
    "debit": 200.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Ing??ende moms 25%"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2890",
    "debit": 0.00,
    "credit": 1000.00,
    "vat_rate": 0.0,
    "notes": "Skuld till anst??lld"
     }
   ]

3. **Taxi receipt 300 SEK including 6% VAT, paid in cash:**
   [
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "C3",
    "account_code": "5611",
    "debit": 283.02,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Resekostnader exklusive moms"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "2641",
    "debit": 16.98,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Ing??ende moms 6%"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "1910",
    "debit": 0.00,
    "credit": 300.00,
    "vat_rate": 0.0,
    "notes": "Kontant betalning"
     }
   ]

---

Instructions:

- Classify and assign accounts for all entries according to **Swedish accounting practice**.
- Use **BAS 2025** as the reference chart of accounts.
- Each selected account should generate an entry in `ai_accounting_proposals`.


- Classify and assign accounts for all entries according to **Swedish accounting practices**.
- Use the **BAS-2025 chart of accounts**, stored in the database table `chart_of_accounts`, as the reference.
- An entry should be made in ai_accounting_proposals for each accountnumber that is selected according to praxis; --- RAW RESPONSE ---
; Based on BAS 2025 chart of accounts; Proposals: [account=6540, debit=110.50, credit=0.00; account=2641, debit=27.63, credit=0.00; account=2440, debit=0.00, credit=138.13]

Filer
630254d0-da97-43b3-a66f-6b934f154ee4Skapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:03
Filtyp: receipt
Workflow-typ: receipt
Status: completed
Konfidens: 98%
OCR-tecken: 2043
Visa OCR-text (2043 tecken)

Microsoft
Billing Summary
Microsoft AB
Summary
Regeringsgatan 25,
111 53, Stockholm
Billing Profile
Mono Consulting Sweden AB
Sweden
G107601838
VAT Reg. No. SE556233480401
Billing Number
14/08/2025
Document Date
Sold To
Bill To
Mono Consulting Sweden AB
Mono Consulting Sweden AB
SEK 138,13
Total Amount
Rissneleden 69 NB
Rissneleden 69 NB
Sundbyberg
Sundbyberg
Due on 14/08/2025
174 44
174 44
SE
SE
Questions on your bill? Visit https://aka.ms/invoice-billing
Invoice for activity on 13/08/2025
each subscription below. Find more details about your bill at
https://admin.microsoft.com/Adminportal/Home#/billoverview/invoice-list/G107601838
Billing Summary
Charges
110,50
Subtotal
110,50
Tax
27,63
Total (including Tax)
SEK 138,13
Payment Instructions:
Your account has a credit card on file and there is no action for you to take. The card you have on file will be charged.

--- PAGE BREAK ---

Microsoft
Invoice
Microsoft AB
Billing Profile
Mono Consulting Sweden AB
Regeringsgatan 25,
SE-TI2500377526
Tax Invoice Number
111 53, Stockholm
14/08/2025
Sweden
Tax Invoice Date
VAT Reg. No. SE556233480401
Sold To
Bill To
Mono Consulting Sweden AB
Mono Consulting Sweden AB
Rissneleden 69 NB
Rissneleden 69 NB
Sundbyberg
Sundbyberg
174 44
174 44
SE
SE
Invoice for activity on 13/08/2025
Section Summary
Total
Charges
(SEK)
(SEK)
Section Name
110,50
110,50
Mono Consulting Sweden AB
110,50
Total (excluding Tax)
27,63
Tax Amount
138,13
Total (including Tax)
Billing Details By Product
Mono Consulting Sweden AB
Teams Premium - Microsoft Teams Premium - One-Year commitment for monthly/yearly billing
Purchases
Charges/
Tax Line
Charge Start Date - Charge End
Unit Price
Credits
Total (excluding Tax)
(SEK)
Indicator
Date
(SEK)
Qty
(SEK)
Tax Rate
A
13/08/2025-12/09/2025
110,50
110,50
1
110,50
25,00%
Sub-Total Amount
Tax Amount
Total (including Tax)
Tax Line Indicator
Tax Description
(SEK)
(SEK)
(SEK)
A
110,50
27,63
138,13
Tax 25,00%
110,50
Subtotal
0
Azure Credit
Tax
27,63
Total
SEK 138,13

--- PAGE BREAK ---

Microsoft
Payment Instructions:

Visa other_data

{
  "billing_number": "G107601838",
  "company_create_needed": false,
  "company_match_type": "vat"
}

56b584ac-4a96-4024-a63b-5cf7b30b1cbdSkapad: 2025-12-12 06:01 · Uppdaterad: 2025-12-12 06:03
Filtyp: pdf_page
Workflow-typ: receipt
Status: completed
Konfidens: –
OCR-tecken: 1094
Visa OCR-text (1094 tecken)

Microsoft
Invoice
Microsoft AB
Billing Profile
Mono Consulting Sweden AB
Regeringsgatan 25,
SE-TI2500377526
Tax Invoice Number
111 53, Stockholm
14/08/2025
Sweden
Tax Invoice Date
VAT Reg. No. SE556233480401
Sold To
Bill To
Mono Consulting Sweden AB
Mono Consulting Sweden AB
Rissneleden 69 NB
Rissneleden 69 NB
Sundbyberg
Sundbyberg
174 44
174 44
SE
SE
Invoice for activity on 13/08/2025
Section Summary
Total
Charges
(SEK)
(SEK)
Section Name
110,50
110,50
Mono Consulting Sweden AB
110,50
Total (excluding Tax)
27,63
Tax Amount
138,13
Total (including Tax)
Billing Details By Product
Mono Consulting Sweden AB
Teams Premium - Microsoft Teams Premium - One-Year commitment for monthly/yearly billing
Purchases
Charges/
Tax Line
Charge Start Date - Charge End
Unit Price
Credits
Total (excluding Tax)
(SEK)
Indicator
Date
(SEK)
Qty
(SEK)
Tax Rate
A
13/08/2025-12/09/2025
110,50
110,50
1
110,50
25,00%
Sub-Total Amount
Tax Amount
Total (including Tax)
Tax Line Indicator
Tax Description
(SEK)
(SEK)
(SEK)
A
110,50
27,63
138,13
Tax 25,00%
110,50
Subtotal
0
Azure Credit
Tax
27,63
Total
SEK 138,13

Visa other_data

{
  "detected_kind": "pdf_page",
  "page_number": 2,
  "source": "wf2_split",
  "source_pdf": "630254d0-da97-43b3-a66f-6b934f154ee4"
}

bb55c390-8c5a-4160-b62c-f90ca2ebc5d2Skapad: 2025-12-12 06:01 · Uppdaterad: 2025-12-12 06:03
Filtyp: pdf_page
Workflow-typ: receipt
Status: completed
Konfidens: –
OCR-tecken: 31
Visa OCR-text (31 tecken)

Microsoft
Payment Instructions:

Visa other_data

{
  "detected_kind": "pdf_page",
  "page_number": 3,
  "source": "wf2_split",
  "source_pdf": "630254d0-da97-43b3-a66f-6b934f154ee4"
}

f0253af7-20c8-412c-b34f-d0bd78e9b6d5Skapad: 2025-12-12 06:01 · Uppdaterad: 2025-12-12 06:03
Filtyp: pdf_page
Workflow-typ: receipt
Status: completed
Konfidens: –
OCR-tecken: 874
Visa OCR-text (874 tecken)

Microsoft
Billing Summary
Microsoft AB
Summary
Regeringsgatan 25,
111 53, Stockholm
Billing Profile
Mono Consulting Sweden AB
Sweden
G107601838
VAT Reg. No. SE556233480401
Billing Number
14/08/2025
Document Date
Sold To
Bill To
Mono Consulting Sweden AB
Mono Consulting Sweden AB
SEK 138,13
Total Amount
Rissneleden 69 NB
Rissneleden 69 NB
Sundbyberg
Sundbyberg
Due on 14/08/2025
174 44
174 44
SE
SE
Questions on your bill? Visit https://aka.ms/invoice-billing
Invoice for activity on 13/08/2025
each subscription below. Find more details about your bill at
https://admin.microsoft.com/Adminportal/Home#/billoverview/invoice-list/G107601838
Billing Summary
Charges
110,50
Subtotal
110,50
Tax
27,63
Total (including Tax)
SEK 138,13
Payment Instructions:
Your account has a credit card on file and there is no action for you to take. The card you have on file will be charged.

Visa other_data

{
  "detected_kind": "pdf_page",
  "page_number": 1,
  "source": "wf2_split",
  "source_pdf": "630254d0-da97-43b3-a66f-6b934f154ee4"
}
```

JPG 1-page-swish.pdf

```
Bearbetningslogg

Kvitto: 6092334d-cfd2-474c-a85b-4ef101783dbc
Workflowkörningar
1 st
WF1_RECEIPT · succeeded
Run-ID: 9 · Källa: wf2_split
Start: 2025-12-12 06:03
Senast: 2025-12-12 06:03
r_ocr_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR startar för fil 6092334d-cfd2-474c-a85b-4ef101783dbc

r_ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 24ms.

ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 24ms.

r_ocr_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 24ms.

ai_pipelinesucceeded
2025-12-12 06:03 → 2025-12-12 06:0312.0s

AI pipeline completed 5 stages in 12079ms: AI1, AI2, AI3, AI4, AI7

detect_type_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI1 klassificering f├╢r fil 6092334d-cfd2-474c-a85b-4ef101783dbc

detect_typesucceeded
2025-12-12 06:03 → 2025-12-12 06:031.0s

Klassificerad som invoice

detect_type_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Klassificerad som invoice

r_ai3_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 dataextraktion startar

r_ai3succeeded
2025-12-12 06:03 → 2025-12-12 06:036.0s

AI3 extraherade 1 artiklar

r_ai3_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 extraherade 1 artiklar

company_resolvedsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

company_match_type=name created=False

r_persist_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Sparar AI3-resultat f├╢r 1 artiklar

r_persistsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_persist_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_ai4_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 normalisering startar

r_ai4succeeded
2025-12-12 06:03 → 2025-12-12 06:034.0s

AI4 skapade 3 konteringsf├╢rslag

r_ai4_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 skapade 3 konteringsf├╢rslag

r_queue_match_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

K├╢ar kvitto f├╢r AI5-matchning

r_queue_matchsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto 6092334d-cfd2-474c-a85b-4ef101783dbc markerat som redo f├╢r matchning

r_queue_match_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto 6092334d-cfd2-474c-a85b-4ef101783dbc markerat som redo f├╢r matchning

finalizesucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Workflow completed successfully.

finalize_ok_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

finalize_oksucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

finalize_ok_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

KLARsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

dispatchsucceeded
-

WF1 dispatched to new wf1.* chain.

AI-historik
9 poster
PDF-Conversion · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:01
pymupdf · fitz-dpi-300
Tid: 488ms

WF2 converted PDF into 1 page(s): page_ids=['11f19a70-e478-424e-8819-1ef99a275217']; workflow_run_id=4; duplicate_pages_reused=0

document_analysis · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
AI1-DocumentClassification · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 1.3s
Konfidens: 45%

Classified document as 'invoice'; OCR text length: 340 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Invoice keywords detected; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.

expense_classification · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
AI2-ExpenseClassification · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 1.1s
Konfidens: 85%

Classified expense as 'corporate'; Document type: invoice; --- PROMPT ---
You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.; --- RAW RESPONSE ---
; Card identifier: visa; Reasoning: Detected card keyword 'visa'; LLM-assisted expense classification; Prompt hint provided: You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.

data_extraction · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
AI3-DataExtraction · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 5.3s
Konfidens: 90%

Extracted data: gross=1800.00, net=1440.00, gross_sek=1800.00, net_sek=1440.00, currency=SEK, purchase_date=2025-04-10 09:10:00, payment_type=swish, expense_type=corporate; --- PROMPT ---
Role:
You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.

You MUST be strictly consistent, never guess values, and never invent IDs or data that are not clearly present in the input or explicitly provided in context.

-------------------------------------------------------------------------------
CRITICAL EXTRACTION RULES
-------------------------------------------------------------------------------

1) COMPANY NAME (TOP OF RECEIPT ONLY)
- Extract the company name from the TOP of the receipt, not from amount lines.
- The company name is usually the first line or very near the top.
- NEVER use lines containing any of the following as company name:
  - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"
- NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.

2) PAYMENT TYPE DETECTION
- Look for keywords:
  - Contains "Swish", "swish", "SWISH" → set payment_type = "swish"
  - Contains any typical card reference (e.g. "VISA", "MASTERCARD", "KORT", "CARD", "MC") → set payment_type = "card"
  - Contains "kontant", "KONTANT", "cash", "CASH" → set payment_type = "cash"
- If you cannot clearly determine the payment type → set payment_type = null.

3) EXPENSE TYPE DETECTION (SWISH)
- If payment_type = "swish":
  - If the buyer/payer appears to be a person (personal name, phone number, no company markers) → expense_type = "personal"
  - If the buyer/payer appears to be a company (company name, org.nr, business context) → expense_type = "corporate"
- For card and cash payments, follow existing business logic if context is provided; if not, set expense_type = null.

4) RECEIPT ITEMS
- Extract line items whenever possible:
  - name (product/service description)
  - quantity (number)
  - unit prices ex VAT and inc VAT
  - total prices ex VAT and inc VAT
  - VAT amounts and VAT percentage
- Ensure VAT math is consistent with the rules defined below.

-------------------------------------------------------------------------------
COMPANY LOOKUP AND AUTO-CREATE RULES
-------------------------------------------------------------------------------

You must always perform company resolution in this order. You may only set company.id and unified_file.company_id to IDs that are explicitly provided to you in the context (for example via a provided companies table). You must never invent any ID.

IMPORTANT: The field "company_match_type" at the TOP LEVEL of the JSON output is MANDATORY and MUST ALWAYS be one of the following three strings:
- "vat"  → when an existing company has been matched by VAT/org.nr
- "name" → when an existing company has been matched by name
- "new"  → when NO existing company could be matched and a new company candidate must be created

"company_match_type" MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER contain any other value than "vat", "name", or "new".

1) ORGANIZATION/VAT MATCH
- If you can reliably extract an organization/VAT number from the OCR text:
  - Normalize it (remove spaces, dashes, and non-digit characters where appropriate).
  - Try to match it against companies.vat (exact match) IF such company data is provided in the prompt/context.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "vat".
    - Set "company_create_needed": false.

2) NAME MATCH
- If no VAT match is found OR no VAT is available:
  - Normalize the extracted company name for matching:
    - trim whitespace
    - convert to lowercase
    - collapse multiple spaces into one
    - normalize å/ä/ö to a/o/o for matching only (do NOT change the displayed name)
  - Try to match it against companies.name (if such data is provided in the prompt/context) with:
    - exact case-insensitive match,
    - or startswith match,
    - or fuzzy similarity > 0.85.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "name".
    - Set "company_create_needed": false.

3) NO MATCH – NEW COMPANY CANDIDATE
- If there is NO match on VAT AND NO match on name OR no companies list is provided:
  - Set company.id = null in your JSON.
  - Set unified_file.company_id = null in your JSON.
  - Set "company_match_type": "new".
  - Set "company_create_needed": true.
  - You MUST still fill the "company" object with all available data
    (name, vat, address, zip, city, country, phone, www, email).
  - The backend will use this data to insert a new row in the companies table
    and link unified_files.company_id to the newly created company.id.
  - The newly created company will be shown in preview for manual review.

You must never invent a company_id. If you cannot confidently match an existing company, you must:
- set company.id = null
- set unified_file.company_id = null
- set "company_match_type" = "new"
- set "company_create_needed" = true

-------------------------------------------------------------------------------
OUTPUT JSON STRUCTURE (STRICT)
-------------------------------------------------------------------------------

You MUST return JSON with EXACTLY this structure and these top-level keys:

{
  "company": {
    "id": null,
    "name": "Company Name Here",
    "vat": "Organization/VAT number if found (formerly orgnr)",
    "address": "Street address",
    "zip": "Postal code",
    "city": "City name",
    "country": "Country (default Sweden if not stated)",
    "phone": "Phone number if present",
    "www": "Website if present",
    "email": "Email if present"
  },
  "unified_file": {
    "company_id": null,
    "purchase_datetime": "2025-09-30 14:23:00 or null",
    "payment_type": "card or cash or swish or null",
    "expense_type": "personal or corporate or null",
    "currency": "SEK or other ISO 4217 code",
    "gross_amount_original": 123.45,
    "net_amount_original": 98.76,
    "exchange_rate": 0,
    "gross_amount_sek": 123,
    "net_amount_sek": 99,
    "receipt_number": "Receipt number if found or null",
    "other_data": "{\"terminal\":\"123\",\"aid\":\"A000\",\"swish_ref\":\"1786145908308241\"}"
  },
  "receipt_items": [
    {
      "main_id": "file_id",
      "article_id": "",
      "name": "Product name",
      "number": 1,
      "item_price_ex_vat": 10.00,
      "item_price_inc_vat": 12.50,
      "item_total_price_ex_vat": 10.00,
      "item_total_price_inc_vat": 12.50,
      "currency": "SEK",
      "vat": 2.50,
      "vat_percentage": 0.250000,
      "item_vat_total": 2.50
    }
  ],
  "company_match_type": "vat",
  "company_create_needed": true,
  "confidence": 0.85
}

Rules for the structure:
- The top-level keys MUST ALWAYS be:
  - "company"
  - "unified_file"
  - "receipt_items"
  - "company_match_type"
  - "company_create_needed"
  - "confidence"

- "company.id" MUST be either:
  - a valid existing company ID explicitly provided in the context, or
  - null.

- "unified_file.company_id" MUST mirror "company.id":
  - same ID when matched,
  - null when no match.

- "company_match_type" MUST ALWAYS be:
  - "vat"   if the match was done via VAT/org.nr,
  - "name"  if the match was done via company name,
  - "new"   if there is no existing company match and a new company must be created.
  It MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER have any other value.

- "company_create_needed" MUST ALWAYS be:
  - false when an existing company match was found (company_match_type is "vat" or "name"),
  - true when no existing company match was found (company_match_type is "new").

-------------------------------------------------------------------------------
GENERAL NUMERIC, DATE, VAT AND CURRENCY RULES
-------------------------------------------------------------------------------

- Dates:
  - Use ISO format "YYYY-MM-DD HH:MM:SS".
  - If time is missing, use "00:00:00".

- Numbers:
  - Accept both "," and "." as decimal separators in the OCR text.
  - Normalize all decimals to "." in the output (e.g. "123,45" → 123.45).

- VAT math:
  - net = gross / (1 + rate)
  - vat = gross - net
  - Example for 25% VAT:
    - rate = 0.25
    - net = gross / 1.25
    - vat = gross - net

- SEK amounts:
  - For *_sek fields, round to whole kronor (no decimals).

- Currency:
  - For SEK:
    - currency = "SEK"
    - exchange_rate = 0
  - For foreign currencies:
    - currency = correct ISO code (e.g. "EUR", "USD", "NOK").
    - exchange_rate = FX rate * 100 (e.g. if FX = 11.33, then exchange_rate = 1133).

- Swish payments:
  - If payment_type = "swish" and a Swish reference number exists in the OCR text:
    - Store it inside unified_file.other_data as JSON content (string).
    - Example: "{\"swish_ref\":\"1786145908308241\"}".
  - You may also include terminal id, AID, or similar technical data in other_data.

-------------------------------------------------------------------------------
DETERMINISM AND UNCERTAINTY
-------------------------------------------------------------------------------

- NEVER invent data:
  - If a field cannot be confidently determined from the OCR text or explicit context, set it to null.

- NEVER invent IDs:
  - company.id and unified_file.company_id MUST only be taken from IDs that are explicitly provided in the context (e.g. via a companies list).
  - If no such ID is available or no match is clear:
    - set company.id = null
    - set unified_file.company_id = null
    - set "company_match_type" = "new"
    - set "company_create_needed" = true

- Be fully deterministic:
  - Apply the same rules in the same way for all receipts.
  - Do not change logic based on guesses or style.

Return ONLY a single JSON object following the schema above, with no extra text before or after.
; --- RAW RESPONSE ---
; Company: name='Mono Consulting Sweden AB'; country='Sweden'; Items: 1 total; Sample items: [Monitor Samsung 4K 24”@1800.00]

accounting_classification · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
AI4-AccountingClassification · success
Fil: 6092334d-cfd2-474c-a85b-4ef101783dbc · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 3.6s
Konfidens: 0%

Generated 3 accounting proposals; Vendor: Mono Consulting Sweden AB; Amounts: gross=1800, net=1440, vat=360; --- PROMPT ---
### AI4 - Accounting (Bookkeeping) Entries

You are an AI model that receives structured receipt data including items, amounts, and VAT details. 
Your task is to generate accounting entries in accordance with Swedish accounting standards (BAS 2025). 
Rules:

- All text som visas ska skrivas p?? svenska
- Always return valid JSON.
- Each entry must map directly to the database table `ai_accounting_proposals`:
  {
    "receipt_id": "referes to unified_files.id",
    "item_id": "referes to receipt_items.id",
    "account_code": "BAS account number",
    "debit": "amount in SEK (decimal)",
    "credit": "amount in SEK (decimal)",
    "vat_rate": "VAT rate (%)",
    "notes": "short explanation of the entry IN SWEDISH"
  }
- Use debit/credit according to double-entry bookkeeping.
- Use BAS 2025 account codes for expenses, VAT, and payment accounts.
- Split entries as required (e.g., expense + VAT + payment).
- Include VAT distribution (25%, 12%, 6%) where relevant.
- If multiple items exist, create accounting proposals per item.
- Notes should explain the logic briefly, e.g. "Food expense", "Input VAT 12%", "Paid with company card".

### Examples:

1. **Restaurant receipt 500 SEK including 12% VAT, paid with company card (FirstCard):**
   [
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "6071",
    "debit": 446.43,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Kostnader f??r mat exklusive moms (12%)"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2641",
    "debit": 53.57,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Ing??ende moms 12%"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2440",
    "debit": 0.00,
    "credit": 500.00,
    "vat_rate": 0.0,
    "notes": "F??retagskort"
     }
   ]

2. **Office supplies 1000 SEK including 25% VAT, paid with private funds (employee reimbursement):**
   [
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "6110",
    "debit": 800.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Kontorsvaror"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2641",
    "debit": 200.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Ing??ende moms 25%"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2890",
    "debit": 0.00,
    "credit": 1000.00,
    "vat_rate": 0.0,
    "notes": "Skuld till anst??lld"
     }
   ]

3. **Taxi receipt 300 SEK including 6% VAT, paid in cash:**
   [
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "C3",
    "account_code": "5611",
    "debit": 283.02,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Resekostnader exklusive moms"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "2641",
    "debit": 16.98,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Ing??ende moms 6%"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "1910",
    "debit": 0.00,
    "credit": 300.00,
    "vat_rate": 0.0,
    "notes": "Kontant betalning"
     }
   ]

---

Instructions:

- Classify and assign accounts for all entries according to **Swedish accounting practice**.
- Use **BAS 2025** as the reference chart of accounts.
- Each selected account should generate an entry in `ai_accounting_proposals`.


- Classify and assign accounts for all entries according to **Swedish accounting practices**.
- Use the **BAS-2025 chart of accounts**, stored in the database table `chart_of_accounts`, as the reference.
- An entry should be made in ai_accounting_proposals for each accountnumber that is selected according to praxis; --- RAW RESPONSE ---
; Based on BAS 2025 chart of accounts; Proposals: [account=1220, debit=1440.00, credit=0.00; account=2641, debit=360.00, credit=0.00; account=2440, debit=0.00, credit=1800.00]

Filer
6092334d-cfd2-474c-a85b-4ef101783dbcSkapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:03
Filtyp: invoice
Workflow-typ: receipt
Status: completed
Konfidens: 90%
OCR-tecken: 340
Visa OCR-text (340 tecken)

Monitor Samsung 4K 24”
Datum: 2025-04-10
Säljare: Praciano Karst Caminha Guilherme
Köpare: Mono Consulting Sweden AB
Betalning: Swish
09:10
BankID
Skickad
10
apr 2025, kl 13:05
Praciano
Karst
0
Caminha
Guilherme
+46
76
650
55
79
-1
800
kr
Referens
1786 1459 0830 8241
Visa
betalningshistorik
Ny
betalning
1
Historik
Profil
Hem
Förfrågningar

Visa other_data

{
  "company_create_needed": false,
  "company_match_type": "name",
  "swish_ref": "1786145908308241"
}

11f19a70-e478-424e-8819-1ef99a275217Skapad: 2025-12-12 06:01 · Uppdaterad: 2025-12-12 06:03
Filtyp: pdf_page
Workflow-typ: receipt
Status: completed
Konfidens: –
OCR-tecken: 340
Visa OCR-text (340 tecken)

Monitor Samsung 4K 24”
Datum: 2025-04-10
Säljare: Praciano Karst Caminha Guilherme
Köpare: Mono Consulting Sweden AB
Betalning: Swish
09:10
BankID
Skickad
10
apr 2025, kl 13:05
Praciano
Karst
0
Caminha
Guilherme
+46
76
650
55
79
-1
800
kr
Referens
1786 1459 0830 8241
Visa
betalningshistorik
Ny
betalning
1
Historik
Profil
Hem
Förfrågningar

Visa other_data

{
  "detected_kind": "pdf_page",
  "page_number": 1,
  "source": "wf2_split",
  "source_pdf": "6092334d-cfd2-474c-a85b-4ef101783dbc"
}
```

PDF: 2-pages-jula.pdf

Status: KLAR - klar

Log:

```
Workflowkörningar
1 st
WF1_RECEIPT · succeeded
Run-ID: 10 · Källa: wf2_split
Start: 2025-12-12 06:03
Senast: 2025-12-12 06:03
r_ocr_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR startar för fil 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730

r_ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 13ms.

ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 13ms.

r_ocr_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 13ms.

ai_pipelinesucceeded
2025-12-12 06:03 → 2025-12-12 06:0312.0s

AI pipeline completed 5 stages in 11109ms: AI1, AI2, AI3, AI4, AI7

detect_type_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI1 klassificering f├╢r fil 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730

detect_typesucceeded
2025-12-12 06:03 → 2025-12-12 06:031.0s

Klassificerad som receipt

detect_type_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Klassificerad som receipt

r_ai3_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 dataextraktion startar

r_ai3succeeded
2025-12-12 06:03 → 2025-12-12 06:036.0s

AI3 extraherade 1 artiklar

r_ai3_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 extraherade 1 artiklar

company_resolvedsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

company_match_type=vat created=False

r_persist_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Sparar AI3-resultat f├╢r 1 artiklar

r_persistsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_persist_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_ai4_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 normalisering startar

r_ai4succeeded
2025-12-12 06:03 → 2025-12-12 06:033.0s

AI4 skapade 3 konteringsf├╢rslag

r_ai4_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 skapade 3 konteringsf├╢rslag

r_queue_match_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

K├╢ar kvitto f├╢r AI5-matchning

r_queue_matchsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 markerat som redo f├╢r matchning

r_queue_match_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 markerat som redo f├╢r matchning

finalizesucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Workflow completed successfully.

finalize_ok_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

finalize_oksucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

finalize_ok_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

KLARsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

dispatchsucceeded
-

WF1 dispatched to new wf1.* chain.

AI-historik
9 poster
PDF-Conversion · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:01
pymupdf · fitz-dpi-300
Tid: 869ms

WF2 converted PDF into 2 page(s): page_ids=['1843e904-fc0b-40c7-a78f-0afc40009158', '44a10fd3-597f-4022-9d66-85e8211b5fc4']; workflow_run_id=5; duplicate_pages_reused=0

document_analysis · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI1-DocumentClassification · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 761ms
Konfidens: 70%

Classified document as 'receipt'; OCR text length: 853 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Receipt keywords detected; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.

expense_classification · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI2-ExpenseClassification · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 840ms
Konfidens: 85%

Classified expense as 'corporate'; Document type: receipt; --- PROMPT ---
You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.; --- RAW RESPONSE ---
; Card identifier: mastercard; Reasoning: Detected card keyword 'mastercard'; LLM-assisted expense classification; Prompt hint provided: You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.

data_extraction · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI3-DataExtraction · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 5.3s
Konfidens: 99%

Extracted data: gross=129.00, net=103.20, gross_sek=129.00, net_sek=103.00, currency=SEK, purchase_date=2025-11-21 13:27:40, payment_type=card, expense_type=corporate, receipt_number=374439; --- PROMPT ---
Role:
You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.

You MUST be strictly consistent, never guess values, and never invent IDs or data that are not clearly present in the input or explicitly provided in context.

-------------------------------------------------------------------------------
CRITICAL EXTRACTION RULES
-------------------------------------------------------------------------------

1) COMPANY NAME (TOP OF RECEIPT ONLY)
- Extract the company name from the TOP of the receipt, not from amount lines.
- The company name is usually the first line or very near the top.
- NEVER use lines containing any of the following as company name:
  - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"
- NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.

2) PAYMENT TYPE DETECTION
- Look for keywords:
  - Contains "Swish", "swish", "SWISH" → set payment_type = "swish"
  - Contains any typical card reference (e.g. "VISA", "MASTERCARD", "KORT", "CARD", "MC") → set payment_type = "card"
  - Contains "kontant", "KONTANT", "cash", "CASH" → set payment_type = "cash"
- If you cannot clearly determine the payment type → set payment_type = null.

3) EXPENSE TYPE DETECTION (SWISH)
- If payment_type = "swish":
  - If the buyer/payer appears to be a person (personal name, phone number, no company markers) → expense_type = "personal"
  - If the buyer/payer appears to be a company (company name, org.nr, business context) → expense_type = "corporate"
- For card and cash payments, follow existing business logic if context is provided; if not, set expense_type = null.

4) RECEIPT ITEMS
- Extract line items whenever possible:
  - name (product/service description)
  - quantity (number)
  - unit prices ex VAT and inc VAT
  - total prices ex VAT and inc VAT
  - VAT amounts and VAT percentage
- Ensure VAT math is consistent with the rules defined below.

-------------------------------------------------------------------------------
COMPANY LOOKUP AND AUTO-CREATE RULES
-------------------------------------------------------------------------------

You must always perform company resolution in this order. You may only set company.id and unified_file.company_id to IDs that are explicitly provided to you in the context (for example via a provided companies table). You must never invent any ID.

IMPORTANT: The field "company_match_type" at the TOP LEVEL of the JSON output is MANDATORY and MUST ALWAYS be one of the following three strings:
- "vat"  → when an existing company has been matched by VAT/org.nr
- "name" → when an existing company has been matched by name
- "new"  → when NO existing company could be matched and a new company candidate must be created

"company_match_type" MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER contain any other value than "vat", "name", or "new".

1) ORGANIZATION/VAT MATCH
- If you can reliably extract an organization/VAT number from the OCR text:
  - Normalize it (remove spaces, dashes, and non-digit characters where appropriate).
  - Try to match it against companies.vat (exact match) IF such company data is provided in the prompt/context.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "vat".
    - Set "company_create_needed": false.

2) NAME MATCH
- If no VAT match is found OR no VAT is available:
  - Normalize the extracted company name for matching:
    - trim whitespace
    - convert to lowercase
    - collapse multiple spaces into one
    - normalize å/ä/ö to a/o/o for matching only (do NOT change the displayed name)
  - Try to match it against companies.name (if such data is provided in the prompt/context) with:
    - exact case-insensitive match,
    - or startswith match,
    - or fuzzy similarity > 0.85.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "name".
    - Set "company_create_needed": false.

3) NO MATCH – NEW COMPANY CANDIDATE
- If there is NO match on VAT AND NO match on name OR no companies list is provided:
  - Set company.id = null in your JSON.
  - Set unified_file.company_id = null in your JSON.
  - Set "company_match_type": "new".
  - Set "company_create_needed": true.
  - You MUST still fill the "company" object with all available data
    (name, vat, address, zip, city, country, phone, www, email).
  - The backend will use this data to insert a new row in the companies table
    and link unified_files.company_id to the newly created company.id.
  - The newly created company will be shown in preview for manual review.

You must never invent a company_id. If you cannot confidently match an existing company, you must:
- set company.id = null
- set unified_file.company_id = null
- set "company_match_type" = "new"
- set "company_create_needed" = true

-------------------------------------------------------------------------------
OUTPUT JSON STRUCTURE (STRICT)
-------------------------------------------------------------------------------

You MUST return JSON with EXACTLY this structure and these top-level keys:

{
  "company": {
    "id": null,
    "name": "Company Name Here",
    "vat": "Organization/VAT number if found (formerly orgnr)",
    "address": "Street address",
    "zip": "Postal code",
    "city": "City name",
    "country": "Country (default Sweden if not stated)",
    "phone": "Phone number if present",
    "www": "Website if present",
    "email": "Email if present"
  },
  "unified_file": {
    "company_id": null,
    "purchase_datetime": "2025-09-30 14:23:00 or null",
    "payment_type": "card or cash or swish or null",
    "expense_type": "personal or corporate or null",
    "currency": "SEK or other ISO 4217 code",
    "gross_amount_original": 123.45,
    "net_amount_original": 98.76,
    "exchange_rate": 0,
    "gross_amount_sek": 123,
    "net_amount_sek": 99,
    "receipt_number": "Receipt number if found or null",
    "other_data": "{\"terminal\":\"123\",\"aid\":\"A000\",\"swish_ref\":\"1786145908308241\"}"
  },
  "receipt_items": [
    {
      "main_id": "file_id",
      "article_id": "",
      "name": "Product name",
      "number": 1,
      "item_price_ex_vat": 10.00,
      "item_price_inc_vat": 12.50,
      "item_total_price_ex_vat": 10.00,
      "item_total_price_inc_vat": 12.50,
      "currency": "SEK",
      "vat": 2.50,
      "vat_percentage": 0.250000,
      "item_vat_total": 2.50
    }
  ],
  "company_match_type": "vat",
  "company_create_needed": true,
  "confidence": 0.85
}

Rules for the structure:
- The top-level keys MUST ALWAYS be:
  - "company"
  - "unified_file"
  - "receipt_items"
  - "company_match_type"
  - "company_create_needed"
  - "confidence"

- "company.id" MUST be either:
  - a valid existing company ID explicitly provided in the context, or
  - null.

- "unified_file.company_id" MUST mirror "company.id":
  - same ID when matched,
  - null when no match.

- "company_match_type" MUST ALWAYS be:
  - "vat"   if the match was done via VAT/org.nr,
  - "name"  if the match was done via company name,
  - "new"   if there is no existing company match and a new company must be created.
  It MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER have any other value.

- "company_create_needed" MUST ALWAYS be:
  - false when an existing company match was found (company_match_type is "vat" or "name"),
  - true when no existing company match was found (company_match_type is "new").

-------------------------------------------------------------------------------
GENERAL NUMERIC, DATE, VAT AND CURRENCY RULES
-------------------------------------------------------------------------------

- Dates:
  - Use ISO format "YYYY-MM-DD HH:MM:SS".
  - If time is missing, use "00:00:00".

- Numbers:
  - Accept both "," and "." as decimal separators in the OCR text.
  - Normalize all decimals to "." in the output (e.g. "123,45" → 123.45).

- VAT math:
  - net = gross / (1 + rate)
  - vat = gross - net
  - Example for 25% VAT:
    - rate = 0.25
    - net = gross / 1.25
    - vat = gross - net

- SEK amounts:
  - For *_sek fields, round to whole kronor (no decimals).

- Currency:
  - For SEK:
    - currency = "SEK"
    - exchange_rate = 0
  - For foreign currencies:
    - currency = correct ISO code (e.g. "EUR", "USD", "NOK").
    - exchange_rate = FX rate * 100 (e.g. if FX = 11.33, then exchange_rate = 1133).

- Swish payments:
  - If payment_type = "swish" and a Swish reference number exists in the OCR text:
    - Store it inside unified_file.other_data as JSON content (string).
    - Example: "{\"swish_ref\":\"1786145908308241\"}".
  - You may also include terminal id, AID, or similar technical data in other_data.

-------------------------------------------------------------------------------
DETERMINISM AND UNCERTAINTY
-------------------------------------------------------------------------------

- NEVER invent data:
  - If a field cannot be confidently determined from the OCR text or explicit context, set it to null.

- NEVER invent IDs:
  - company.id and unified_file.company_id MUST only be taken from IDs that are explicitly provided in the context (e.g. via a companies list).
  - If no such ID is available or no match is clear:
    - set company.id = null
    - set unified_file.company_id = null
    - set "company_match_type" = "new"
    - set "company_create_needed" = true

- Be fully deterministic:
  - Apply the same rules in the same way for all receipts.
  - Do not change logic based on guesses or style.

Return ONLY a single JSON object following the schema above, with no extra text before or after.
; --- RAW RESPONSE ---
; Company: name='JULA'; orgnr='SE556944785601'; address='Ulvsundavägen 191'; city='Bromma'; zip='168 67'; country='Sweden'; Items: 1 total; Sample items: [WHITE GREASE+PTFE CRC 250ML@129.00]

accounting_classification · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
AI4-AccountingClassification · success
Fil: 68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730 · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 3.6s
Konfidens: 0%

Generated 3 accounting proposals; Vendor: JULA; Amounts: gross=129, net=103, vat=26; --- PROMPT ---
### AI4 - Accounting (Bookkeeping) Entries

You are an AI model that receives structured receipt data including items, amounts, and VAT details. 
Your task is to generate accounting entries in accordance with Swedish accounting standards (BAS 2025). 
Rules:

- All text som visas ska skrivas p?? svenska
- Always return valid JSON.
- Each entry must map directly to the database table `ai_accounting_proposals`:
  {
    "receipt_id": "referes to unified_files.id",
    "item_id": "referes to receipt_items.id",
    "account_code": "BAS account number",
    "debit": "amount in SEK (decimal)",
    "credit": "amount in SEK (decimal)",
    "vat_rate": "VAT rate (%)",
    "notes": "short explanation of the entry IN SWEDISH"
  }
- Use debit/credit according to double-entry bookkeeping.
- Use BAS 2025 account codes for expenses, VAT, and payment accounts.
- Split entries as required (e.g., expense + VAT + payment).
- Include VAT distribution (25%, 12%, 6%) where relevant.
- If multiple items exist, create accounting proposals per item.
- Notes should explain the logic briefly, e.g. "Food expense", "Input VAT 12%", "Paid with company card".

### Examples:

1. **Restaurant receipt 500 SEK including 12% VAT, paid with company card (FirstCard):**
   [
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "6071",
    "debit": 446.43,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Kostnader f??r mat exklusive moms (12%)"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2641",
    "debit": 53.57,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Ing??ende moms 12%"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2440",
    "debit": 0.00,
    "credit": 500.00,
    "vat_rate": 0.0,
    "notes": "F??retagskort"
     }
   ]

2. **Office supplies 1000 SEK including 25% VAT, paid with private funds (employee reimbursement):**
   [
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "6110",
    "debit": 800.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Kontorsvaror"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2641",
    "debit": 200.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Ing??ende moms 25%"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2890",
    "debit": 0.00,
    "credit": 1000.00,
    "vat_rate": 0.0,
    "notes": "Skuld till anst??lld"
     }
   ]

3. **Taxi receipt 300 SEK including 6% VAT, paid in cash:**
   [
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "C3",
    "account_code": "5611",
    "debit": 283.02,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Resekostnader exklusive moms"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "2641",
    "debit": 16.98,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Ing??ende moms 6%"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "1910",
    "debit": 0.00,
    "credit": 300.00,
    "vat_rate": 0.0,
    "notes": "Kontant betalning"
     }
   ]

---

Instructions:

- Classify and assign accounts for all entries according to **Swedish accounting practice**.
- Use **BAS 2025** as the reference chart of accounts.
- Each selected account should generate an entry in `ai_accounting_proposals`.


- Classify and assign accounts for all entries according to **Swedish accounting practices**.
- Use the **BAS-2025 chart of accounts**, stored in the database table `chart_of_accounts`, as the reference.
- An entry should be made in ai_accounting_proposals for each accountnumber that is selected according to praxis; --- RAW RESPONSE ---
; Based on BAS 2025 chart of accounts; Proposals: [account=5460, debit=103.20, credit=0.00; account=2641, debit=25.80, credit=0.00; account=2440, debit=0.00, credit=129.00]

Filer
68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730Skapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:03
Filtyp: receipt
Workflow-typ: receipt
Status: completed
Konfidens: 99%
OCR-tecken: 853
Visa OCR-text (853 tecken)

JULA
Kvitto
Jula Bromma
Ulvsundavägen 191
Datum
2025-11-21
168 67
Tid
13:27
Org nr
SE556944785601
Kvitto nr
374439
Kassa
044711
Kassör
00013393
Beskrivning
Artikelnummer
Pris
Mängd
Summa(SEK)
WHITE GREASE+PTFE CRC 250ML
1,00 st
129,00
004569
129,00
Betalat 129,00
Netto
Brutto
Moms %
Moms
129,00
25,00
25,80
103,20
-0,00
Erhållen rabatt
Kort
129,00
Betalningsinformation
Date
2025-11-21
Time
13:27:40
****9995
Card
PAN seq.
00
DEBIT MASTERCARD
Pref. name
Card type
mcstandarddebit
Payment method
MasterCard
Payment variant
mcstandarddebit
Entry mode
Contactless chip
AID
A0000000041010
MID
526567000856547
TID
P400Plus-805321953
PTID
66593614
Auth. code
1USJSD
Tender
VQ2Y001763728060032
Reference
44711/374439132741480
Type
GOODS SERVICES
TOTAL
SEK 129,00
APPROVED
Retain for your records
Thank you

--- PAGE BREAK ---

Returkod
95104471100000000374439

Visa other_data

{
  "aid": "A0000000041010",
  "auth_code": "1USJSD",
  "card_last4": "9995",
  "card_type": "DEBIT MASTERCARD",
  "company_create_needed": false,
  "company_match_type": "vat",
  "entry_mode": "Contactless chip",
  "kassa": "044711",
  "kassor": "00013393",
  "mid": "526567000856547",
  "payment_method": "MasterCard",
  "ptid": "66593614",
  "reference": "44711/374439132741480",
  "returkod": "95104471100000000374439",
  "tender": "VQ2Y001763728060032",
  "tid": "P400Plus-805321953"
}

1843e904-fc0b-40c7-a78f-0afc40009158Skapad: 2025-12-12 06:01 · Uppdaterad: 2025-12-12 06:03
Filtyp: pdf_page
Workflow-typ: receipt
Status: completed
Konfidens: –
OCR-tecken: 799
Visa OCR-text (799 tecken)

JULA
Kvitto
Jula Bromma
Ulvsundavägen 191
Datum
2025-11-21
168 67
Tid
13:27
Org nr
SE556944785601
Kvitto nr
374439
Kassa
044711
Kassör
00013393
Beskrivning
Artikelnummer
Pris
Mängd
Summa(SEK)
WHITE GREASE+PTFE CRC 250ML
1,00 st
129,00
004569
129,00
Betalat 129,00
Netto
Brutto
Moms %
Moms
129,00
25,00
25,80
103,20
-0,00
Erhållen rabatt
Kort
129,00
Betalningsinformation
Date
2025-11-21
Time
13:27:40
****9995
Card
PAN seq.
00
DEBIT MASTERCARD
Pref. name
Card type
mcstandarddebit
Payment method
MasterCard
Payment variant
mcstandarddebit
Entry mode
Contactless chip
AID
A0000000041010
MID
526567000856547
TID
P400Plus-805321953
PTID
66593614
Auth. code
1USJSD
Tender
VQ2Y001763728060032
Reference
44711/374439132741480
Type
GOODS SERVICES
TOTAL
SEK 129,00
APPROVED
Retain for your records
Thank you

Visa other_data

{
  "detected_kind": "pdf_page",
  "page_number": 1,
  "source": "wf2_split",
  "source_pdf": "68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730"
}

44a10fd3-597f-4022-9d66-85e8211b5fc4Skapad: 2025-12-12 06:01 · Uppdaterad: 2025-12-12 06:03
Filtyp: pdf_page
Workflow-typ: receipt
Status: completed
Konfidens: –
OCR-tecken: 32
Visa OCR-text (32 tecken)

Returkod
95104471100000000374439

Visa other_data

{
  "detected_kind": "pdf_page",
  "page_number": 2,
  "source": "wf2_split",
  "source_pdf": "68bf4bc9-34cf-4e4a-8bcf-dc40f5a70730"
}


```

PDF: 1-page-elgiganten.pdf

Status: finalize-klar

Log:

```
Bearbetningslogg

Kvitto: da8a005b-d79f-4a7a-97b4-7a52b2ae872d
Workflowkörningar
1 st
WF1_RECEIPT · succeeded
Run-ID: 8 · Källa: wf2_split
Start: 2025-12-12 06:03
Senast: 2025-12-12 06:03
r_ocr_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR startar för fil da8a005b-d79f-4a7a-97b4-7a52b2ae872d

r_ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:031.0s

OCR succeeded, extracted 0 chars in 46ms.

ocrsucceeded
2025-12-12 06:03 → 2025-12-12 06:031.0s

OCR succeeded, extracted 0 chars in 46ms.

r_ocr_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

OCR succeeded, extracted 0 chars in 46ms.

ai_pipelinesucceeded
2025-12-12 06:03 → 2025-12-12 06:0314.0s

AI pipeline completed 5 stages in 14420ms: AI1, AI2, AI3, AI4, AI7

detect_type_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI1 klassificering f├╢r fil da8a005b-d79f-4a7a-97b4-7a52b2ae872d

detect_typesucceeded
2025-12-12 06:03 → 2025-12-12 06:032.0s

Klassificerad som receipt

detect_type_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Klassificerad som receipt

r_ai3_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 dataextraktion startar

r_ai3succeeded
2025-12-12 06:03 → 2025-12-12 06:035.0s

AI3 extraherade 1 artiklar

r_ai3_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3 extraherade 1 artiklar

company_resolvedsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

company_match_type=vat created=False

r_persist_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Sparar AI3-resultat f├╢r 1 artiklar

r_persistsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_persist_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI3-data sparat i unified_files

r_ai4_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 normalisering startar

r_ai4succeeded
2025-12-12 06:03 → 2025-12-12 06:034.0s

AI4 skapade 3 konteringsf├╢rslag

r_ai4_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

AI4 skapade 3 konteringsf├╢rslag

r_queue_match_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

K├╢ar kvitto f├╢r AI5-matchning

r_queue_matchsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto da8a005b-d79f-4a7a-97b4-7a52b2ae872d markerat som redo f├╢r matchning

r_queue_match_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvitto da8a005b-d79f-4a7a-97b4-7a52b2ae872d markerat som redo f├╢r matchning

finalizesucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Workflow completed successfully.

finalize_ok_startsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

finalize_oksucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

finalize_ok_endsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

Kvittofl├╢det avslutat utan fel

KLARsucceeded
2025-12-12 06:03 → 2025-12-12 06:030ms

WF1 slutf├╢rd

dispatchsucceeded
-

WF1 dispatched to new wf1.* chain.

AI-historik
9 poster
PDF-Conversion · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:00
pymupdf · fitz-dpi-300
Tid: 475ms

WF2 converted PDF into 1 page(s): page_ids=['b11202a7-46d9-4a8d-99fb-b1a14812b4fb']; workflow_run_id=2; duplicate_pages_reused=0

document_analysis · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
AI1-DocumentClassification · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 2.0s
Konfidens: 80%

Classified document as 'receipt'; OCR text length: 2354 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Receipt keywords detected; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.

expense_classification · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
AI2-ExpenseClassification · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 2.6s
Konfidens: 65%

Classified expense as 'personal'; Document type: receipt; --- PROMPT ---
You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.; --- RAW RESPONSE ---
; Card identifier: visa; Reasoning: Detected card keyword 'visa'; LLM-assisted expense classification; Defaulting to personal expense; Prompt hint provided: You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.

data_extraction · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
AI3-DataExtraction · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 5.1s
Konfidens: 97%

Extracted data: gross=2790.00, net=2232.00, gross_sek=2790.00, net_sek=2232.00, currency=SEK, purchase_date=2024-07-17 16:12:42, payment_type=card, expense_type=personal, receipt_number=2252511319; --- PROMPT ---
Role:
You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.

You MUST be strictly consistent, never guess values, and never invent IDs or data that are not clearly present in the input or explicitly provided in context.

-------------------------------------------------------------------------------
CRITICAL EXTRACTION RULES
-------------------------------------------------------------------------------

1) COMPANY NAME (TOP OF RECEIPT ONLY)
- Extract the company name from the TOP of the receipt, not from amount lines.
- The company name is usually the first line or very near the top.
- NEVER use lines containing any of the following as company name:
  - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"
- NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.

2) PAYMENT TYPE DETECTION
- Look for keywords:
  - Contains "Swish", "swish", "SWISH" → set payment_type = "swish"
  - Contains any typical card reference (e.g. "VISA", "MASTERCARD", "KORT", "CARD", "MC") → set payment_type = "card"
  - Contains "kontant", "KONTANT", "cash", "CASH" → set payment_type = "cash"
- If you cannot clearly determine the payment type → set payment_type = null.

3) EXPENSE TYPE DETECTION (SWISH)
- If payment_type = "swish":
  - If the buyer/payer appears to be a person (personal name, phone number, no company markers) → expense_type = "personal"
  - If the buyer/payer appears to be a company (company name, org.nr, business context) → expense_type = "corporate"
- For card and cash payments, follow existing business logic if context is provided; if not, set expense_type = null.

4) RECEIPT ITEMS
- Extract line items whenever possible:
  - name (product/service description)
  - quantity (number)
  - unit prices ex VAT and inc VAT
  - total prices ex VAT and inc VAT
  - VAT amounts and VAT percentage
- Ensure VAT math is consistent with the rules defined below.

-------------------------------------------------------------------------------
COMPANY LOOKUP AND AUTO-CREATE RULES
-------------------------------------------------------------------------------

You must always perform company resolution in this order. You may only set company.id and unified_file.company_id to IDs that are explicitly provided to you in the context (for example via a provided companies table). You must never invent any ID.

IMPORTANT: The field "company_match_type" at the TOP LEVEL of the JSON output is MANDATORY and MUST ALWAYS be one of the following three strings:
- "vat"  → when an existing company has been matched by VAT/org.nr
- "name" → when an existing company has been matched by name
- "new"  → when NO existing company could be matched and a new company candidate must be created

"company_match_type" MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER contain any other value than "vat", "name", or "new".

1) ORGANIZATION/VAT MATCH
- If you can reliably extract an organization/VAT number from the OCR text:
  - Normalize it (remove spaces, dashes, and non-digit characters where appropriate).
  - Try to match it against companies.vat (exact match) IF such company data is provided in the prompt/context.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "vat".
    - Set "company_create_needed": false.

2) NAME MATCH
- If no VAT match is found OR no VAT is available:
  - Normalize the extracted company name for matching:
    - trim whitespace
    - convert to lowercase
    - collapse multiple spaces into one
    - normalize å/ä/ö to a/o/o for matching only (do NOT change the displayed name)
  - Try to match it against companies.name (if such data is provided in the prompt/context) with:
    - exact case-insensitive match,
    - or startswith match,
    - or fuzzy similarity > 0.85.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "name".
    - Set "company_create_needed": false.

3) NO MATCH – NEW COMPANY CANDIDATE
- If there is NO match on VAT AND NO match on name OR no companies list is provided:
  - Set company.id = null in your JSON.
  - Set unified_file.company_id = null in your JSON.
  - Set "company_match_type": "new".
  - Set "company_create_needed": true.
  - You MUST still fill the "company" object with all available data
    (name, vat, address, zip, city, country, phone, www, email).
  - The backend will use this data to insert a new row in the companies table
    and link unified_files.company_id to the newly created company.id.
  - The newly created company will be shown in preview for manual review.

You must never invent a company_id. If you cannot confidently match an existing company, you must:
- set company.id = null
- set unified_file.company_id = null
- set "company_match_type" = "new"
- set "company_create_needed" = true

-------------------------------------------------------------------------------
OUTPUT JSON STRUCTURE (STRICT)
-------------------------------------------------------------------------------

You MUST return JSON with EXACTLY this structure and these top-level keys:

{
  "company": {
    "id": null,
    "name": "Company Name Here",
    "vat": "Organization/VAT number if found (formerly orgnr)",
    "address": "Street address",
    "zip": "Postal code",
    "city": "City name",
    "country": "Country (default Sweden if not stated)",
    "phone": "Phone number if present",
    "www": "Website if present",
    "email": "Email if present"
  },
  "unified_file": {
    "company_id": null,
    "purchase_datetime": "2025-09-30 14:23:00 or null",
    "payment_type": "card or cash or swish or null",
    "expense_type": "personal or corporate or null",
    "currency": "SEK or other ISO 4217 code",
    "gross_amount_original": 123.45,
    "net_amount_original": 98.76,
    "exchange_rate": 0,
    "gross_amount_sek": 123,
    "net_amount_sek": 99,
    "receipt_number": "Receipt number if found or null",
    "other_data": "{\"terminal\":\"123\",\"aid\":\"A000\",\"swish_ref\":\"1786145908308241\"}"
  },
  "receipt_items": [
    {
      "main_id": "file_id",
      "article_id": "",
      "name": "Product name",
      "number": 1,
      "item_price_ex_vat": 10.00,
      "item_price_inc_vat": 12.50,
      "item_total_price_ex_vat": 10.00,
      "item_total_price_inc_vat": 12.50,
      "currency": "SEK",
      "vat": 2.50,
      "vat_percentage": 0.250000,
      "item_vat_total": 2.50
    }
  ],
  "company_match_type": "vat",
  "company_create_needed": true,
  "confidence": 0.85
}

Rules for the structure:
- The top-level keys MUST ALWAYS be:
  - "company"
  - "unified_file"
  - "receipt_items"
  - "company_match_type"
  - "company_create_needed"
  - "confidence"

- "company.id" MUST be either:
  - a valid existing company ID explicitly provided in the context, or
  - null.

- "unified_file.company_id" MUST mirror "company.id":
  - same ID when matched,
  - null when no match.

- "company_match_type" MUST ALWAYS be:
  - "vat"   if the match was done via VAT/org.nr,
  - "name"  if the match was done via company name,
  - "new"   if there is no existing company match and a new company must be created.
  It MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER have any other value.

- "company_create_needed" MUST ALWAYS be:
  - false when an existing company match was found (company_match_type is "vat" or "name"),
  - true when no existing company match was found (company_match_type is "new").

-------------------------------------------------------------------------------
GENERAL NUMERIC, DATE, VAT AND CURRENCY RULES
-------------------------------------------------------------------------------

- Dates:
  - Use ISO format "YYYY-MM-DD HH:MM:SS".
  - If time is missing, use "00:00:00".

- Numbers:
  - Accept both "," and "." as decimal separators in the OCR text.
  - Normalize all decimals to "." in the output (e.g. "123,45" → 123.45).

- VAT math:
  - net = gross / (1 + rate)
  - vat = gross - net
  - Example for 25% VAT:
    - rate = 0.25
    - net = gross / 1.25
    - vat = gross - net

- SEK amounts:
  - For *_sek fields, round to whole kronor (no decimals).

- Currency:
  - For SEK:
    - currency = "SEK"
    - exchange_rate = 0
  - For foreign currencies:
    - currency = correct ISO code (e.g. "EUR", "USD", "NOK").
    - exchange_rate = FX rate * 100 (e.g. if FX = 11.33, then exchange_rate = 1133).

- Swish payments:
  - If payment_type = "swish" and a Swish reference number exists in the OCR text:
    - Store it inside unified_file.other_data as JSON content (string).
    - Example: "{\"swish_ref\":\"1786145908308241\"}".
  - You may also include terminal id, AID, or similar technical data in other_data.

-------------------------------------------------------------------------------
DETERMINISM AND UNCERTAINTY
-------------------------------------------------------------------------------

- NEVER invent data:
  - If a field cannot be confidently determined from the OCR text or explicit context, set it to null.

- NEVER invent IDs:
  - company.id and unified_file.company_id MUST only be taken from IDs that are explicitly provided in the context (e.g. via a companies list).
  - If no such ID is available or no match is clear:
    - set company.id = null
    - set unified_file.company_id = null
    - set "company_match_type" = "new"
    - set "company_create_needed" = true

- Be fully deterministic:
  - Apply the same rules in the same way for all receipts.
  - Do not change logic based on guesses or style.

Return ONLY a single JSON object following the schema above, with no extra text before or after.
; --- RAW RESPONSE ---
; Company: name='Elgiganten SE'; orgnr='5564714474'; address='Franzéngatan 6'; city='Stockholm'; zip='112 51'; country='Sweden'; Items: 1 total; Sample items: [Apple AirPods Pro 2nd gen (2023) true wireless hörlurar (USB-C)@2790.00]

accounting_classification · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
AI4-AccountingClassification · success
Fil: da8a005b-d79f-4a7a-97b4-7a52b2ae872d · 2025-12-12 06:03
OpenAI · gpt-5.1
Tid: 3.9s
Konfidens: 0%

Generated 3 accounting proposals; Vendor: Elgiganten SE; Amounts: gross=2790, net=2232, vat=558; --- PROMPT ---
### AI4 - Accounting (Bookkeeping) Entries

You are an AI model that receives structured receipt data including items, amounts, and VAT details. 
Your task is to generate accounting entries in accordance with Swedish accounting standards (BAS 2025). 
Rules:

- All text som visas ska skrivas p?? svenska
- Always return valid JSON.
- Each entry must map directly to the database table `ai_accounting_proposals`:
  {
    "receipt_id": "referes to unified_files.id",
    "item_id": "referes to receipt_items.id",
    "account_code": "BAS account number",
    "debit": "amount in SEK (decimal)",
    "credit": "amount in SEK (decimal)",
    "vat_rate": "VAT rate (%)",
    "notes": "short explanation of the entry IN SWEDISH"
  }
- Use debit/credit according to double-entry bookkeeping.
- Use BAS 2025 account codes for expenses, VAT, and payment accounts.
- Split entries as required (e.g., expense + VAT + payment).
- Include VAT distribution (25%, 12%, 6%) where relevant.
- If multiple items exist, create accounting proposals per item.
- Notes should explain the logic briefly, e.g. "Food expense", "Input VAT 12%", "Paid with company card".

### Examples:

1. **Restaurant receipt 500 SEK including 12% VAT, paid with company card (FirstCard):**
   [
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "6071",
    "debit": 446.43,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Kostnader f??r mat exklusive moms (12%)"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2641",
    "debit": 53.57,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Ing??ende moms 12%"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2440",
    "debit": 0.00,
    "credit": 500.00,
    "vat_rate": 0.0,
    "notes": "F??retagskort"
     }
   ]

2. **Office supplies 1000 SEK including 25% VAT, paid with private funds (employee reimbursement):**
   [
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "6110",
    "debit": 800.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Kontorsvaror"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2641",
    "debit": 200.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Ing??ende moms 25%"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2890",
    "debit": 0.00,
    "credit": 1000.00,
    "vat_rate": 0.0,
    "notes": "Skuld till anst??lld"
     }
   ]

3. **Taxi receipt 300 SEK including 6% VAT, paid in cash:**
   [
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "C3",
    "account_code": "5611",
    "debit": 283.02,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Resekostnader exklusive moms"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "2641",
    "debit": 16.98,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Ing??ende moms 6%"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "1910",
    "debit": 0.00,
    "credit": 300.00,
    "vat_rate": 0.0,
    "notes": "Kontant betalning"
     }
   ]

---

Instructions:

- Classify and assign accounts for all entries according to **Swedish accounting practice**.
- Use **BAS 2025** as the reference chart of accounts.
- Each selected account should generate an entry in `ai_accounting_proposals`.


- Classify and assign accounts for all entries according to **Swedish accounting practices**.
- Use the **BAS-2025 chart of accounts**, stored in the database table `chart_of_accounts`, as the reference.
- An entry should be made in ai_accounting_proposals for each accountnumber that is selected according to praxis; --- RAW RESPONSE ---
; Based on BAS 2025 chart of accounts; Proposals: [account=5410, debit=2232.00, credit=0.00; account=2641, debit=558.00, credit=0.00; account=2890, debit=0.00, credit=2790.00]

Filer
da8a005b-d79f-4a7a-97b4-7a52b2ae872dSkapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:03
Filtyp: receipt
Workflow-typ: receipt
Status: completed
Konfidens: 97%
OCR-tecken: 2354
Visa OCR-text (2354 tecken)

Mattias Cederlund
Kvitto
Almvägen 33
Ordernummer
2252511319
19144 Sollentuna
+46733038666
Datum/Tid
2024-07-17 16:12
mattias@mono.se
Säljare
noels
Butik
2023 Elgiganten Bromma
Leveransanteckningar
Telefon: +46733038666
Take now
17th July 2024
Varukod
Beskrivning
Pris
Rabatt
Ant.
Total
Moms
673048
Apple AirPods Pro 2nd gen (2023) true wireless
2790.00
25%
2790.00
0.00
1
hörlurar (USB-C)
4407Q6AN är din kod. Värde 338 kr. De två första
månaderna är kostnadsfria. Efter två månader
växlar prenumerationen automatiskt till ett
betalabonnemang, jfr gällande prislista (169 kr/
månad). Gäller endast nya Viaplay-kunder. 1 kod per
kund. Erbjudandet kan lösas in till 30.09.2024.
Viaplays villkor gäller (viaplay.com/terms). Ej
bindande  avboka när du vill. 2024-10-01
***EJ ÖPPET KÖP VID BRUTEN FÖRP.***
Belopp
Moms
Moms
Sum
Totalt inkl. moms
2790.00
25%
2232.00
558.00
2790.00
Card
2790.00
Sum
2232.00
558.00
2790.00
Betald summa
2790.00
Återstår att betala
0.00
Kortbetalningsinformation
Nöjda kunder är det viktigaste för oss på Elgiganten! Hos oss
Datum: 2024-07-17 Tid: 16:12:42 Kort: 2673 PAN seq.: 00 Föredraget
får du möjligheten att prova det du köpt i 30 dagar. För
namn: Visa DEBIT Korttyp: visastandarddebit Betalningssätt: visa Payment
klubbmedlemmar gäller 50 dagar. UNDANTAG: abonnemang,
variant: visastandarddebit Tokenbetalvariant: visa_applepay
tjänster, kök, presentkort och på köpet erbjudanden.
Inmatningsläge: Kontaktlöst chip CVM res.: VERIFIERAD AV ENHET AID:
Mobiltelefon, spel, programvara och hygienartiklar återlämnas
A0000000031010 MID: 498750002607522 TID: P400Plus-803571508
PTID: 62055556 Auth. code: 813809 Tender: CNU4001721225562051
i obruten förpackning. Produkten returneras komplett och i
referens: 6d85a1c5ba8f4d71a392cf31
oförändrat skick.
bc60841-2252511319 Typ: VAROR_TJÄNSTER Totalt: SEK 2.790,00
Fullständiga villkor för öppet köp i en Elgiganten Phonehouse
Godkänt Behåll och arkivera
butik samt övriga kundgarantier se elgiganten.se/
kundgarantier.
KVITTOT ÄR EN VÄRDEHANDLING och skall uppvisas vid retur,
garanti- och reklamationsärenden.
En orderbekräftelse är inte juridiskt bindande och vi förbehåller
oss rätten att avbryta din order på grund av tryckfel, tekniska
problem, leveranssvikt och liknande situationer.
Elgiganten SE
Franzéngatan 6
112 51 Stockholm
Org. no.: 556471-4474
Vat no.: SE556471447401

Visa other_data

{
  "aid": "A0000000031010",
  "auth_code": "813809",
  "card_type": "Visa DEBIT",
  "company_create_needed": false,
  "company_match_type": "vat",
  "mid": "498750002607522",
  "order_number": "2252511319",
  "ptid": "62055556",
  "reference": "6d85a1c5ba8f4d71a392cf31",
  "tender": "CNU4001721225562051",
  "terminal": "P400Plus-803571508"
}

b11202a7-46d9-4a8d-99fb-b1a14812b4fbSkapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:03
Filtyp: pdf_page
Workflow-typ: receipt
Status: completed
Konfidens: –
OCR-tecken: 2354
Visa OCR-text (2354 tecken)

Mattias Cederlund
Kvitto
Almvägen 33
Ordernummer
2252511319
19144 Sollentuna
+46733038666
Datum/Tid
2024-07-17 16:12
mattias@mono.se
Säljare
noels
Butik
2023 Elgiganten Bromma
Leveransanteckningar
Telefon: +46733038666
Take now
17th July 2024
Varukod
Beskrivning
Pris
Rabatt
Ant.
Total
Moms
673048
Apple AirPods Pro 2nd gen (2023) true wireless
2790.00
25%
2790.00
0.00
1
hörlurar (USB-C)
4407Q6AN är din kod. Värde 338 kr. De två första
månaderna är kostnadsfria. Efter två månader
växlar prenumerationen automatiskt till ett
betalabonnemang, jfr gällande prislista (169 kr/
månad). Gäller endast nya Viaplay-kunder. 1 kod per
kund. Erbjudandet kan lösas in till 30.09.2024.
Viaplays villkor gäller (viaplay.com/terms). Ej
bindande  avboka när du vill. 2024-10-01
***EJ ÖPPET KÖP VID BRUTEN FÖRP.***
Belopp
Moms
Moms
Sum
Totalt inkl. moms
2790.00
25%
2232.00
558.00
2790.00
Card
2790.00
Sum
2232.00
558.00
2790.00
Betald summa
2790.00
Återstår att betala
0.00
Kortbetalningsinformation
Nöjda kunder är det viktigaste för oss på Elgiganten! Hos oss
Datum: 2024-07-17 Tid: 16:12:42 Kort: 2673 PAN seq.: 00 Föredraget
får du möjligheten att prova det du köpt i 30 dagar. För
namn: Visa DEBIT Korttyp: visastandarddebit Betalningssätt: visa Payment
klubbmedlemmar gäller 50 dagar. UNDANTAG: abonnemang,
variant: visastandarddebit Tokenbetalvariant: visa_applepay
tjänster, kök, presentkort och på köpet erbjudanden.
Inmatningsläge: Kontaktlöst chip CVM res.: VERIFIERAD AV ENHET AID:
Mobiltelefon, spel, programvara och hygienartiklar återlämnas
A0000000031010 MID: 498750002607522 TID: P400Plus-803571508
PTID: 62055556 Auth. code: 813809 Tender: CNU4001721225562051
i obruten förpackning. Produkten returneras komplett och i
referens: 6d85a1c5ba8f4d71a392cf31
oförändrat skick.
bc60841-2252511319 Typ: VAROR_TJÄNSTER Totalt: SEK 2.790,00
Fullständiga villkor för öppet köp i en Elgiganten Phonehouse
Godkänt Behåll och arkivera
butik samt övriga kundgarantier se elgiganten.se/
kundgarantier.
KVITTOT ÄR EN VÄRDEHANDLING och skall uppvisas vid retur,
garanti- och reklamationsärenden.
En orderbekräftelse är inte juridiskt bindande och vi förbehåller
oss rätten att avbryta din order på grund av tryckfel, tekniska
problem, leveranssvikt och liknande situationer.
Elgiganten SE
Franzéngatan 6
112 51 Stockholm
Org. no.: 556471-4474
Vat no.: SE556471447401

Visa other_data

{
  "detected_kind": "pdf_page",
  "page_number": 1,
  "source": "wf2_split",
  "source_pdf": "da8a005b-d79f-4a7a-97b4-7a52b2ae872d"
}
```

PDF :1-page-autodesk.pdf: 

Log:

- Stannar på "finalize - klar"

````
### Bearbetningslogg

Kvitto: be24f95b-65d3-4e28-bf76-a0b49da5ee3a

#### Workflowkörningar

1 st

WF1_RECEIPT · succeeded

Run-ID: 7 · Källa: wf2_split

Start: 2025-12-12 06:01

Senast: 2025-12-12 06:01

r_ocr_startsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
OCR startar för fil be24f95b-65d3-4e28-bf76-a0b49da5ee3a
```

r_ocrsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
OCR succeeded, extracted 0 chars in 40ms.
```

ocrsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
OCR succeeded, extracted 0 chars in 40ms.
```

r_ocr_endsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
OCR succeeded, extracted 0 chars in 40ms.
```

ai_pipelinesucceeded

2025-12-12 06:01 → 2025-12-12 06:0116.0s

```
AI pipeline completed 5 stages in 15585ms: AI1, AI2, AI3, AI4, AI7
```

detect_type_startsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
AI1 klassificering f├╢r fil be24f95b-65d3-4e28-bf76-a0b49da5ee3a
```

detect_typesucceeded

2025-12-12 06:01 → 2025-12-12 06:011.0s

```
Klassificerad som receipt
```

detect_type_endsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
Klassificerad som receipt
```

r_ai3_startsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
AI3 dataextraktion startar
```

r_ai3succeeded

2025-12-12 06:01 → 2025-12-12 06:018.0s

```
AI3 extraherade 1 artiklar
```

r_ai3_endsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
AI3 extraherade 1 artiklar
```

company_resolvedsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
company_match_type=vat created=False
```

r_persist_startsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
Sparar AI3-resultat f├╢r 1 artiklar
```

r_persistsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
AI3-data sparat i unified_files
```

r_persist_endsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
AI3-data sparat i unified_files
```

r_ai4_startsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
AI4 normalisering startar
```

r_ai4succeeded

2025-12-12 06:01 → 2025-12-12 06:014.0s

```
AI4 skapade 2 konteringsf├╢rslag
```

r_ai4_endsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
AI4 skapade 2 konteringsf├╢rslag
```

r_queue_match_startsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
K├╢ar kvitto f├╢r AI5-matchning
```

r_queue_matchsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
Kvitto be24f95b-65d3-4e28-bf76-a0b49da5ee3a markerat som redo f├╢r matchning
```

r_queue_match_endsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
Kvitto be24f95b-65d3-4e28-bf76-a0b49da5ee3a markerat som redo f├╢r matchning
```

finalizesucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
Workflow completed successfully.
```

finalize_ok_startsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
WF1 slutf├╢rd
```

finalize_oksucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
Kvittofl├╢det avslutat utan fel
```

finalize_ok_endsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
Kvittofl├╢det avslutat utan fel
```

KLARsucceeded

2025-12-12 06:01 → 2025-12-12 06:010ms

```
WF1 slutf├╢rd
```

dispatchsucceeded

\-

```
WF1 dispatched to new wf1.* chain.
```

#### AI-historik

9 poster

PDF-Conversion · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:00

pymupdf · fitz-dpi-300

Tid: 230ms

```
WF2 converted PDF into 1 page(s): page_ids=['90e1285d-211d-4112-a69f-6e9f72be2627']; workflow_run_id=1; duplicate_pages_reused=0
```

document_analysis · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

AI1-DocumentClassification · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

Tid: 1.2s

Konfidens: 50%

```
Classified document as 'receipt'; OCR text length: 963 characters; --- PROMPT ---
You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted classification; Receipt keywords detected; Prompt hint provided: You are an AI model receiving text from a scanned document.
Determine the document type: "receipt", "invoice", or "other".
Focus on text clues (e.g., words like "KVITTO", "FAKTURA", "VAT", company names, reference numbers).
Respond with ONLY one of these three labels without explanation.
```

expense_classification · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

AI2-ExpenseClassification · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

Tid: 1.2s

Konfidens: 60%

```
Classified expense as 'corporate'; Document type: receipt; --- PROMPT ---
You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.; --- RAW RESPONSE ---
; Reasoning: LLM-assisted expense classification; Prompt hint provided: You are an AI model analyzing receipt details (payment method, card data, contextual text).
Determine whether the receipt is an *employee expense* or a *company card expense*.
Look for signs such as company card names, "FirstCard", "MasterCard", or if payment is linked to employee.
Reply with either "personal" or "corporate" only, without any extra text.
```

data_extraction · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

AI3-DataExtraction · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

Tid: 8.2s

Konfidens: 95%

```
Extracted data: gross=680.00, net=680.00, gross_sek=680.00, net_sek=680.00, currency=SEK, purchase_date=2023-11-24 00:00:00, expense_type=corporate, receipt_number=032457341; --- PROMPT ---
Role:
You are a deterministic data extractor for Swedish receipts and invoices. Your only goal is to parse OCR text into database-ready JSON for these tables: companies, unified_files, and receipt_items.

You MUST be strictly consistent, never guess values, and never invent IDs or data that are not clearly present in the input or explicitly provided in context.

-------------------------------------------------------------------------------
CRITICAL EXTRACTION RULES
-------------------------------------------------------------------------------

1) COMPANY NAME (TOP OF RECEIPT ONLY)
- Extract the company name from the TOP of the receipt, not from amount lines.
- The company name is usually the first line or very near the top.
- NEVER use lines containing any of the following as company name:
  - "SUMMA", "TOTAL", "BELOPP", "ATT BETALA"
- NEVER use lines that clearly contain prices (e.g. "123.45", "1 234,50") as company name.

2) PAYMENT TYPE DETECTION
- Look for keywords:
  - Contains "Swish", "swish", "SWISH" → set payment_type = "swish"
  - Contains any typical card reference (e.g. "VISA", "MASTERCARD", "KORT", "CARD", "MC") → set payment_type = "card"
  - Contains "kontant", "KONTANT", "cash", "CASH" → set payment_type = "cash"
- If you cannot clearly determine the payment type → set payment_type = null.

3) EXPENSE TYPE DETECTION (SWISH)
- If payment_type = "swish":
  - If the buyer/payer appears to be a person (personal name, phone number, no company markers) → expense_type = "personal"
  - If the buyer/payer appears to be a company (company name, org.nr, business context) → expense_type = "corporate"
- For card and cash payments, follow existing business logic if context is provided; if not, set expense_type = null.

4) RECEIPT ITEMS
- Extract line items whenever possible:
  - name (product/service description)
  - quantity (number)
  - unit prices ex VAT and inc VAT
  - total prices ex VAT and inc VAT
  - VAT amounts and VAT percentage
- Ensure VAT math is consistent with the rules defined below.

-------------------------------------------------------------------------------
COMPANY LOOKUP AND AUTO-CREATE RULES
-------------------------------------------------------------------------------

You must always perform company resolution in this order. You may only set company.id and unified_file.company_id to IDs that are explicitly provided to you in the context (for example via a provided companies table). You must never invent any ID.

IMPORTANT: The field "company_match_type" at the TOP LEVEL of the JSON output is MANDATORY and MUST ALWAYS be one of the following three strings:
- "vat"  → when an existing company has been matched by VAT/org.nr
- "name" → when an existing company has been matched by name
- "new"  → when NO existing company could be matched and a new company candidate must be created

"company_match_type" MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER contain any other value than "vat", "name", or "new".

1) ORGANIZATION/VAT MATCH
- If you can reliably extract an organization/VAT number from the OCR text:
  - Normalize it (remove spaces, dashes, and non-digit characters where appropriate).
  - Try to match it against companies.vat (exact match) IF such company data is provided in the prompt/context.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "vat".
    - Set "company_create_needed": false.

2) NAME MATCH
- If no VAT match is found OR no VAT is available:
  - Normalize the extracted company name for matching:
    - trim whitespace
    - convert to lowercase
    - collapse multiple spaces into one
    - normalize å/ä/ö to a/o/o for matching only (do NOT change the displayed name)
  - Try to match it against companies.name (if such data is provided in the prompt/context) with:
    - exact case-insensitive match,
    - or startswith match,
    - or fuzzy similarity > 0.85.
  - If a match is found:
    - Set company.id to the matched company id.
    - Set unified_file.company_id to the same id.
    - Set "company_match_type": "name".
    - Set "company_create_needed": false.

3) NO MATCH – NEW COMPANY CANDIDATE
- If there is NO match on VAT AND NO match on name OR no companies list is provided:
  - Set company.id = null in your JSON.
  - Set unified_file.company_id = null in your JSON.
  - Set "company_match_type": "new".
  - Set "company_create_needed": true.
  - You MUST still fill the "company" object with all available data
    (name, vat, address, zip, city, country, phone, www, email).
  - The backend will use this data to insert a new row in the companies table
    and link unified_files.company_id to the newly created company.id.
  - The newly created company will be shown in preview for manual review.

You must never invent a company_id. If you cannot confidently match an existing company, you must:
- set company.id = null
- set unified_file.company_id = null
- set "company_match_type" = "new"
- set "company_create_needed" = true

-------------------------------------------------------------------------------
OUTPUT JSON STRUCTURE (STRICT)
-------------------------------------------------------------------------------

You MUST return JSON with EXACTLY this structure and these top-level keys:

{
  "company": {
    "id": null,
    "name": "Company Name Here",
    "vat": "Organization/VAT number if found (formerly orgnr)",
    "address": "Street address",
    "zip": "Postal code",
    "city": "City name",
    "country": "Country (default Sweden if not stated)",
    "phone": "Phone number if present",
    "www": "Website if present",
    "email": "Email if present"
  },
  "unified_file": {
    "company_id": null,
    "purchase_datetime": "2025-09-30 14:23:00 or null",
    "payment_type": "card or cash or swish or null",
    "expense_type": "personal or corporate or null",
    "currency": "SEK or other ISO 4217 code",
    "gross_amount_original": 123.45,
    "net_amount_original": 98.76,
    "exchange_rate": 0,
    "gross_amount_sek": 123,
    "net_amount_sek": 99,
    "receipt_number": "Receipt number if found or null",
    "other_data": "{\"terminal\":\"123\",\"aid\":\"A000\",\"swish_ref\":\"1786145908308241\"}"
  },
  "receipt_items": [
    {
      "main_id": "file_id",
      "article_id": "",
      "name": "Product name",
      "number": 1,
      "item_price_ex_vat": 10.00,
      "item_price_inc_vat": 12.50,
      "item_total_price_ex_vat": 10.00,
      "item_total_price_inc_vat": 12.50,
      "currency": "SEK",
      "vat": 2.50,
      "vat_percentage": 0.250000,
      "item_vat_total": 2.50
    }
  ],
  "company_match_type": "vat",
  "company_create_needed": true,
  "confidence": 0.85
}

Rules for the structure:
- The top-level keys MUST ALWAYS be:
  - "company"
  - "unified_file"
  - "receipt_items"
  - "company_match_type"
  - "company_create_needed"
  - "confidence"

- "company.id" MUST be either:
  - a valid existing company ID explicitly provided in the context, or
  - null.

- "unified_file.company_id" MUST mirror "company.id":
  - same ID when matched,
  - null when no match.

- "company_match_type" MUST ALWAYS be:
  - "vat"   if the match was done via VAT/org.nr,
  - "name"  if the match was done via company name,
  - "new"   if there is no existing company match and a new company must be created.
  It MUST NEVER be null, MUST NEVER be omitted, and MUST NEVER have any other value.

- "company_create_needed" MUST ALWAYS be:
  - false when an existing company match was found (company_match_type is "vat" or "name"),
  - true when no existing company match was found (company_match_type is "new").

-------------------------------------------------------------------------------
GENERAL NUMERIC, DATE, VAT AND CURRENCY RULES
-------------------------------------------------------------------------------

- Dates:
  - Use ISO format "YYYY-MM-DD HH:MM:SS".
  - If time is missing, use "00:00:00".

- Numbers:
  - Accept both "," and "." as decimal separators in the OCR text.
  - Normalize all decimals to "." in the output (e.g. "123,45" → 123.45).

- VAT math:
  - net = gross / (1 + rate)
  - vat = gross - net
  - Example for 25% VAT:
    - rate = 0.25
    - net = gross / 1.25
    - vat = gross - net

- SEK amounts:
  - For *_sek fields, round to whole kronor (no decimals).

- Currency:
  - For SEK:
    - currency = "SEK"
    - exchange_rate = 0
  - For foreign currencies:
    - currency = correct ISO code (e.g. "EUR", "USD", "NOK").
    - exchange_rate = FX rate * 100 (e.g. if FX = 11.33, then exchange_rate = 1133).

- Swish payments:
  - If payment_type = "swish" and a Swish reference number exists in the OCR text:
    - Store it inside unified_file.other_data as JSON content (string).
    - Example: "{\"swish_ref\":\"1786145908308241\"}".
  - You may also include terminal id, AID, or similar technical data in other_data.

-------------------------------------------------------------------------------
DETERMINISM AND UNCERTAINTY
-------------------------------------------------------------------------------

- NEVER invent data:
  - If a field cannot be confidently determined from the OCR text or explicit context, set it to null.

- NEVER invent IDs:
  - company.id and unified_file.company_id MUST only be taken from IDs that are explicitly provided in the context (e.g. via a companies list).
  - If no such ID is available or no match is clear:
    - set company.id = null
    - set unified_file.company_id = null
    - set "company_match_type" = "new"
    - set "company_create_needed" = true

- Be fully deterministic:
  - Apply the same rules in the same way for all receipts.
  - Do not change logic based on guesses or style.

Return ONLY a single JSON object following the schema above, with no extra text before or after.
; --- RAW RESPONSE ---
; Company: name='Autodesk Ireland Operations UC'; orgnr='IE3515583EH'; address='Windmill Lane'; city='Dublin 2'; country='Ireland'; Items: 1 total; Sample items: [Fusion 360 (Period: 1-Månad)@680.00]
```

accounting_classification · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

AI4-AccountingClassification · success

Fil: be24f95b-65d3-4e28-bf76-a0b49da5ee3a · 2025-12-12 06:01

OpenAI · gpt-5.1

Tid: 3.8s

Konfidens: 0%

```
Generated 2 accounting proposals; Vendor: Autodesk Ireland Operations UC; Amounts: gross=680, net=680, vat=0; --- PROMPT ---
### AI4 - Accounting (Bookkeeping) Entries

You are an AI model that receives structured receipt data including items, amounts, and VAT details. 
Your task is to generate accounting entries in accordance with Swedish accounting standards (BAS 2025). 
Rules:

- All text som visas ska skrivas p?? svenska
- Always return valid JSON.
- Each entry must map directly to the database table `ai_accounting_proposals`:
  {
    "receipt_id": "referes to unified_files.id",
    "item_id": "referes to receipt_items.id",
    "account_code": "BAS account number",
    "debit": "amount in SEK (decimal)",
    "credit": "amount in SEK (decimal)",
    "vat_rate": "VAT rate (%)",
    "notes": "short explanation of the entry IN SWEDISH"
  }
- Use debit/credit according to double-entry bookkeeping.
- Use BAS 2025 account codes for expenses, VAT, and payment accounts.
- Split entries as required (e.g., expense + VAT + payment).
- Include VAT distribution (25%, 12%, 6%) where relevant.
- If multiple items exist, create accounting proposals per item.
- Notes should explain the logic briefly, e.g. "Food expense", "Input VAT 12%", "Paid with company card".

### Examples:

1. **Restaurant receipt 500 SEK including 12% VAT, paid with company card (FirstCard):**
   [
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "6071",
    "debit": 446.43,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Kostnader f??r mat exklusive moms (12%)"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2641",
    "debit": 53.57,
    "credit": 0.00,
    "vat_rate": 12.0,
    "notes": "Ing??ende moms 12%"
     },
     {
    "receipt_id": "914003da-5688-458b-9f44-c44fe39c9daa",
    "item_id": "3",
    "account_code": "2440",
    "debit": 0.00,
    "credit": 500.00,
    "vat_rate": 0.0,
    "notes": "F??retagskort"
     }
   ]

2. **Office supplies 1000 SEK including 25% VAT, paid with private funds (employee reimbursement):**
   [
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "6110",
    "debit": 800.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Kontorsvaror"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2641",
    "debit": 200.00,
    "credit": 0.00,
    "vat_rate": 25.0,
    "notes": "Ing??ende moms 25%"
     },
     {
    "receipt_id": "d34ba425-db67-4056-a0ce-cf9989b5671e",
    "item_id": "27",
    "account_code": "2890",
    "debit": 0.00,
    "credit": 1000.00,
    "vat_rate": 0.0,
    "notes": "Skuld till anst??lld"
     }
   ]

3. **Taxi receipt 300 SEK including 6% VAT, paid in cash:**
   [
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "C3",
    "account_code": "5611",
    "debit": 283.02,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Resekostnader exklusive moms"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "2641",
    "debit": 16.98,
    "credit": 0.00,
    "vat_rate": 6.0,
    "notes": "Ing??ende moms 6%"
     },
     {
    "receipt_id": "595466b8-ed50-4a98-a248-8760aa14abb1",
    "item_id": "48",
    "account_code": "1910",
    "debit": 0.00,
    "credit": 300.00,
    "vat_rate": 0.0,
    "notes": "Kontant betalning"
     }
   ]

---

Instructions:

- Classify and assign accounts for all entries according to **Swedish accounting practice**.
- Use **BAS 2025** as the reference chart of accounts.
- Each selected account should generate an entry in `ai_accounting_proposals`.


- Classify and assign accounts for all entries according to **Swedish accounting practices**.
- Use the **BAS-2025 chart of accounts**, stored in the database table `chart_of_accounts`, as the reference.
- An entry should be made in ai_accounting_proposals for each accountnumber that is selected according to praxis; --- RAW RESPONSE ---
; Based on BAS 2025 chart of accounts; Proposals: [account=5420, debit=680.00, credit=0.00; account=2440, debit=0.00, credit=680.00]
```

#### Filer

be24f95b-65d3-4e28-bf76-a0b49da5ee3aSkapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:01

Filtyp: receipt

Workflow-typ: receipt

Status: completed

Konfidens: 95%

OCR-tecken: 963

<details class="bg-gray-800/60 border border-gray-700/60 rounded-md p-2" open=""><summary class="text-xs text-gray-300 cursor-pointer">Visa OCR-text (963 tecken)</summary><pre class="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">Autodesk Ireland Operations UC
Windmill Lane
Dublin 2
002 F206
reland
www.autodesk.com
V.A.T. No.:IE3515583EH
Sida: 1 av 1
Fakturaadress:
Mono Consulting Sweden AB
Almvägen 33
Helenelund
191 41 Sollentuna
Sweden
Denna faktura betalas. Tack för din beställning.
Fakturanummer:
Såld till:
032457341
Mono Consulting Sweden AB
Mattias Cederlund
Fakturadatum:
Almvägen 33
Helenelund
24.11.2023
191 41 Sollentuna
Sweden
nternt ordernr.:
Inköpsordernr.:
Inköpsordernr datum:
069651998
51038519
24.11.2023
Kundnummer:
Momsregistreringsnummer:
Datum för beställning:
5501457519
SE556675539201
24.11.2023
Nr.
Prenumerationer id
Beskrivning
Belopp
Antal
Antal användare
Enhetspris
1
68502386527944
Fusion 360
1
680,00
680,00
Period: 1-Månad
Reverse charge VAT
Totalt nettobelopp
680,00
Slutanvändare:
VAT (0%)
0,00
Mono Consulting Sweden AB
Almvägen 33
Totala beloppet (SEK)
680,00
Helenelund
191 41 Sollentuna
Totalt betalat belopp (SEK)
680,00
Sweden
Förfallna belopp
0,00</pre></details>

<details class="bg-gray-800/50 border border-gray-700/60 rounded-md p-2" open=""><summary class="text-xs text-gray-300 cursor-pointer">Visa other_data</summary><pre class="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono overflow-x-auto">{
  "company_create_needed": false,
  "company_match_type": "vat",
  "customer_number": "5501457519",
  "internal_order_number": "069651998",
  "purchase_order_date": "2023-11-24",
  "purchase_order_number": "51038519"
}</pre></details>

90e1285d-211d-4112-a69f-6e9f72be2627Skapad: 2025-12-12 06:00 · Uppdaterad: 2025-12-12 06:01

Filtyp: pdf_page

Workflow-typ: receipt

Status: completed

Konfidens: –

OCR-tecken: 963

<details class="bg-gray-800/60 border border-gray-700/60 rounded-md p-2" open=""><summary class="text-xs text-gray-300 cursor-pointer">Visa OCR-text (963 tecken)</summary><pre class="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">Autodesk Ireland Operations UC
Windmill Lane
Dublin 2
002 F206
reland
www.autodesk.com
V.A.T. No.:IE3515583EH
Sida: 1 av 1
Fakturaadress:
Mono Consulting Sweden AB
Almvägen 33
Helenelund
191 41 Sollentuna
Sweden
Denna faktura betalas. Tack för din beställning.
Fakturanummer:
Såld till:
032457341
Mono Consulting Sweden AB
Mattias Cederlund
Fakturadatum:
Almvägen 33
Helenelund
24.11.2023
191 41 Sollentuna
Sweden
nternt ordernr.:
Inköpsordernr.:
Inköpsordernr datum:
069651998
51038519
24.11.2023
Kundnummer:
Momsregistreringsnummer:
Datum för beställning:
5501457519
SE556675539201
24.11.2023
Nr.
Prenumerationer id
Beskrivning
Belopp
Antal
Antal användare
Enhetspris
1
68502386527944
Fusion 360
1
680,00
680,00
Period: 1-Månad
Reverse charge VAT
Totalt nettobelopp
680,00
Slutanvändare:
VAT (0%)
0,00
Mono Consulting Sweden AB
Almvägen 33
Totala beloppet (SEK)
680,00
Helenelund
191 41 Sollentuna
Totalt betalat belopp (SEK)
680,00
Sweden
Förfallna belopp
0,00</pre></details>

<details class="bg-gray-800/50 border border-gray-700/60 rounded-md p-2" open=""><slot name="internal-main-summary"><summary class="text-xs text-gray-300 cursor-pointer">Visa other_data</summary></slot><slot><pre class="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono overflow-x-auto">{
  "detected_kind": "pdf_page",
  "page_number": 1,
  "source": "wf2_split",
  "source_pdf": "be24f95b-65d3-4e28-bf76-a0b49da5ee3a"
}</pre></slot></details>


````

