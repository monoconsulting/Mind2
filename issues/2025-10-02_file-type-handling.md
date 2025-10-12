# File Type Handling After Upload (Image, Audio, PDF, Other)

## Context

**Current behavior:**
- Systemet hanterar primärt bildfilformat (jpg, jpeg, png, tiff) för kvittobearbetning
- PDF-filer och ljudfiler saknar automatisk hantering
- Ingen systematisk filtypsdetektering finns implementerad

**Expected behavior:**
- Systemet ska automatiskt detektera filtyp vid uppladdning
- Olika filtyper ska ledas till rätt bearbetningsflöde:
  - Bilder → direkt till kvittoflödet (OCR → AI-pipeline)
  - PDF → konvertering till PNG → kvittoflödet
  - Audio → transkriptionsflöde
  - Övriga → manuell granskning

**Business value:**
- Möjliggör hantering av fler filformat (särskilt PDF som är vanligt för fakturor)
- Förbättrad användarupplevelse genom automatisk hantering
- Bättre OCR-kvalitet genom optimerad konvertering (300 DPI PNG från PDF)

## Definition of Done

### Functional acceptance criteria
- [ ] Systemet detekterar korrekt filtyp för: image, audio, PDF, other
- [ ] Bilduppladdning fortsätter direkt i befintligt kvittoflöde (OCR → AI1-AI4)
- [ ] PDF-uppladdning resulterar i:
  - [ ] Original-PDF sparas oförändrad i storage
  - [ ] Varje sida konverteras till PNG (300 DPI, lossless)
  - [ ] PNG-filer processas i kvittoflödet
  - [ ] Sidnumrering: `<filename>_page_0001.png`, `<filename>_page_0002.png`, etc.
- [ ] Ljuduppladdning dirigeras till transkriptionspipeline
- [ ] Okända filtyper markeras för manuell granskning
- [ ] All konvertering och routing loggas med full spårbarhet

### Tests
- [ ] Unit tests för filtypsdetektering
- [ ] Integration tests för PDF → PNG konvertering (kontrollera DPI, format)
- [ ] E2E test: ladda upp PDF → verifiera PNG-skapande → verifiera OCR körs
- [ ] E2E test: ladda upp ljud → verifiera transkription triggas
- [ ] E2E test: ladda upp okänd filtyp → verifiera manual review-status

### Docs/Changelog
- [ ] Uppdatera `MIND_WORKFLOW.md` med nya filtypsflöden
- [ ] Dokumentera PDF-konverteringsparametrar (DPI, format)
- [ ] API-dokumentation för nya endpoints (om några)

### Performance/Security
- [ ] PDF-konvertering ska hantera sidvis för att undvika minnesöverbelastning
- [ ] Validera filstorlek och antal sidor innan konvertering
- [ ] Säker filtypsvalidering (inte bara extension-baserad)
- [ ] Temporära filer (PNG från PDF) rensas korrekt efter bearbetning

## Scope & Constraints

### In scope:
1. **Filtypsdetektering vid uppladdning:**
   - Implementera i `backend/src/api/ingest.py` (upload endpoint)
   - Använd både extension och MIME-type för säker detektering
   - Detektera: image (jpg, jpeg, png, tiff), audio (mp3, wav, m4a), PDF, other

2. **PDF-hantering:**
   - Konvertera PDF → PNG med PyMuPDF (fitz) eller pdf2image/Poppler
   - Parametrar: 300 DPI, PNG-format (lossless), grayscale om möjligt
   - Spara original-PDF i storage (`/data/storage/originals/<file_id>.pdf`)
   - Generera PNG per sida: `/data/storage/converted/<file_id>_page_0001.png`
   - Skapa post i `unified_files` för varje PNG-sida med länk till original-PDF

3. **Routing till rätt pipeline:**
   - Image → befintligt OCR-flöde (`process_ocr` task)
   - PDF → konvertering → OCR-flöde för varje PNG
   - Audio → ny transkriptionspipeline (skapas om den inte finns)
   - Other → status `manual_review`

4. **Loggning:**
   - Logga filtypsdetektering i `ai_processing_history`
   - Logga PDF-konvertering (antal sidor, framgång/fel)
   - Spåra relation mellan original-PDF och genererade PNG-filer

### Out of scope:
- Transkriptionspipeline-implementation (endast routing till den, om den finns)
- Batch-uppladdning av flera filer samtidigt
- Avancerad bildoptimering utöver 300 DPI PNG-konvertering
- Automatisk textigenkänning i ljudfiler (endast transkription)

## Links

### Code files
- Upload endpoint: [backend/src/api/ingest.py](backend/src/api/ingest.py)
- OCR service: [backend/src/services/ocr.py](backend/src/services/ocr.py)
- Task processing: [backend/src/services/tasks.py](backend/src/services/tasks.py)

### Related documentation
- Workflow: [docs/SYSTEM_DOCS/MIND_WORKFLOW.md](docs/SYSTEM_DOCS/MIND_WORKFLOW.md)
- OCR settings: Settings/OCR in application

### Technical references
- PyMuPDF docs: https://pymupdf.readthedocs.io/
- pdf2image docs: https://github.com/Belval/pdf2image
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR

## Technical Implementation Notes

### PDF → PNG Conversion:
```python
# Recommended: PyMuPDF (fitz)
import fitz  # PyMuPDF

def pdf_to_png(pdf_path, output_dir, dpi=300):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi/72, dpi/72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat, alpha=False)
        output_path = f"{output_dir}/{file_id}_page_{page_num+1:04d}.png"
        pix.save(output_path)
    doc.close()
```

### File Type Detection:
```python
import mimetypes
from pathlib import Path

def detect_file_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type:
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type == 'application/pdf':
            return 'pdf'

    # Fallback to extension
    ext = Path(file_path).suffix.lower()
    if ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
        return 'image'
    elif ext in ['.mp3', '.wav', '.m4a', '.ogg']:
        return 'audio'
    elif ext == '.pdf':
        return 'pdf'

    return 'other'
```

### Database Schema Updates (if needed):
- Add `original_file_id` column to `unified_files` (foreign key to original PDF if converted from PDF)
- Add `page_number` column to `unified_files` (for PDF pages)
- Add `file_format` column to track: 'native_image', 'pdf_converted', 'audio_transcribed', 'other'

## Git Branching Strategy

**Branch name:** `feature/file-type-handling`

**Branching from:** `dev`

**Commands:**
```bash
git checkout dev
git pull --ff-only
git checkout -b feature/file-type-handling
```

**Commit Policy:**
- Use Conventional Commits format
- Reference this issue in commits: `feat: add PDF detection (refs #XX)`
- Final commit/PR must include: `Fixes #XX`

**Example commits:**
```bash
git commit -m "feat: add file type detection utility (refs #XX)"
git commit -m "feat: implement PDF to PNG conversion (refs #XX)"
git commit -m "feat: route file types to appropriate pipelines (refs #XX)"
git commit -m "test: add PDF conversion integration tests (refs #XX)"
git commit -m "docs: update MIND_WORKFLOW.md with file type handling (refs #XX)"
```

## Pull Request Checklist

When creating PR to `dev`:

- [ ] All acceptance criteria met
- [ ] Tests pass (unit + integration + E2E)
- [ ] Code reviewed by at least one team member
- [ ] Documentation updated (MIND_WORKFLOW.md, API docs)
- [ ] No breaking changes to existing image upload flow
- [ ] Performance tested with multi-page PDFs (10+ pages)
- [ ] Error handling verified (corrupted PDFs, unsupported formats)
- [ ] PR description includes `Fixes #XX`

## Labels

enhancement, backend, high-priority, pdf-support

## Assignees

(To be assigned)

## Milestone

v1.2 - Multi-format Support
