# Saknade komponenter i reconciliation_firstcard.py

## Problem Summary
Filen reconciliation_firstcard.py har refaktorerats och utökats kraftigt men flera kritiska komponenter saknas:

### 1. Saknade imports
- `_as_decimal` från services.validation
- `FileStorage` instansiering behöver `_storage()` helper

### 2. Saknade helper-funktioner
Dessa funktioner används men är inte definierade:

```python
def _storage() -> FileStorage:
    """Return FileStorage instance"""
    
def _count_invoice_lines(invoice_id: str) -> tuple[int, int]:
    """Return (total_lines, matched_lines) for an invoice"""
    
def _load_invoice_document(invoice_id: str) -> Optional[tuple[str, dict[str, Any]]]:
    """Load invoice document status and metadata"""
    
def _list_invoice_files(source_file_id: str) -> list[dict[str, Any]]:
    """List all files related to an invoice"""
    
def _create_invoice_document(invoice_id: str, invoice_type: str, status: str, metadata: dict) -> bool:
    """Create or update invoice document record"""
    
def _create_workflow_run(workflow_key: str, source_channel: str, file_id: str, content_hash: str) -> Optional[int]:
    """Create workflow run and return ID"""
    
def _find_file_id_by_hash(file_hash: str) -> Optional[str]:
    """Find existing file by content hash"""
    
def _write_invoice_metadata(invoice_id: str, metadata: dict) -> bool:
    """Write metadata to invoice document"""
    
def _find_invoice_id_for_main(main_id: int) -> Optional[str]:
    """Find invoice_document.id from creditcard_invoices_main.id"""
    
def _as_date(val: Any) -> Optional[date]:
    """Convert value to date"""
```

### 3. Saknade konstanter
```python
_OCR_COMPLETE_STATUSES = {"ocr_done", "completed", "processed", "ready"}
```

### 4. Saknade endpoints
```python
@recon_bp.get("/reconciliation/firstcard/statements")
def list_statements() -> Any:
    """List all company card statements"""
```

## Lösning
1. Importera saknade funktioner från befintliga moduler
2. Skapa de helper-funktioner som inte finns någon annanstans
3. Återställa list_statements endpoint
4. Lägga till saknade konstanter
