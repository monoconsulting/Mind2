# FirstCard Refactor - Task List Fas 3

**Datum:** 2025-11-09  
**Branch:** TM000-firstcard-refactor  
**Status:** FAS 1 & 2 SLUTFÖRDA - FAS 3 KRÄVS FÖR PRODUCTION

---

## PRIORITERING

### 🔴 P0 - BLOCKERANDE (Måste göras innan deploy)
Dessa problem förhindrar systemet från att fungera korrekt.

### 🟠 P1 - KRITISKT (Bör göras innan deploy)
Dessa problem skapar instabilitet och inkonsistens.

### 🟡 P2 - VIKTIGT (Kan göras efter deploy)
Dessa förbättringar ökar robusthet men är inte blockerande.

### 🟢 P3 - FÖRBÄTTRING (Teknisk skuld)
Dessa optimeringar kan göras löpande.

---

## FAS 3 - AKUTA ÅTGÄRDER

### 🔴 TASK 3.1: Komplettera WorkflowCoordinator

**Prioritet:** P0 - BLOCKERANDE  
**Estimat:** 4 timmar  
**Ansvarig:** Backend team

#### Problem:
`WorkflowCoordinator` saknar metoder som anropas från `upload.py` och `statements.py`:
- `create_workflow_run()`
- `begin_import_stage()`
- `complete_import_stage()`
- `dispatch_workflow()`

#### Åtgärd:
Flytta dessa metoder från `services.tasks.workflow_tasks` till `WorkflowCoordinator`.

#### Implementation:

**Fil:** `backend/src/api/reconciliation_firstcard/services/workflow_coordinator.py`

```python
class WorkflowCoordinator:
    # ... existing methods ...
    
    def create_workflow_run(
        self,
        workflow_key: str,
        source_channel: str,
        file_id: str,
        content_hash: str,
    ) -> Optional[int]:
        """Create a new workflow run in the database.
        
        Args:
            workflow_key: Workflow identifier (e.g., "WF3_FIRSTCARD_INVOICE")
            source_channel: Source of the upload (e.g., "kortmatchning_upload")
            file_id: Invoice document ID
            content_hash: SHA256 hash of the uploaded file
            
        Returns:
            workflow_run_id if successful, None otherwise
        """
        if db_cursor is None:
            return None
            
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflow_runs (
                        workflow_key,
                        entity_type,
                        entity_id,
                        file_id,
                        content_hash,
                        source_channel,
                        status,
                        current_stage,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        workflow_key,
                        "invoice_document",
                        file_id,
                        file_id,
                        content_hash,
                        source_channel,
                        "pending",
                        "created",
                    ),
                )
                workflow_run_id = cur.lastrowid
                logger.info(
                    f"Created workflow run {workflow_run_id} for {workflow_key} (file_id={file_id})"
                )
                return workflow_run_id
        except Exception as e:
            logger.error(f"Failed to create workflow run: {e}")
            return None
    
    def begin_import_stage(
        self,
        workflow_run_id: int,
        stage_key: str,
        message: str = "",
    ) -> bool:
        """Log the start of an import stage.
        
        Args:
            workflow_run_id: The workflow run ID
            stage_key: Stage identifier (e.g., "src_fc", "fc_ocr")
            message: Optional descriptive message
            
        Returns:
            True if logged successfully
        """
        if db_cursor is None:
            return False
            
        try:
            with db_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO workflow_stage_runs (
                        workflow_run_id,
                        stage_key,
                        status,
                        message,
                        started_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                    """,
                    (workflow_run_id, stage_key, "running", message),
                )
                
                # Update current_stage_key in workflow_runs
                cur.execute(
                    """
                    UPDATE workflow_runs
                    SET current_stage_key = %s,
                        current_stage = %s
                    WHERE id = %s
                    """,
                    (stage_key, stage_key, workflow_run_id),
                )
            logger.info(
                f"Started stage {stage_key} for workflow run {workflow_run_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log stage start: {e}")
            return False
    
    def complete_import_stage(
        self,
        workflow_run_id: int,
        stage_key: str,
        success: bool,
        message: str = "",
    ) -> bool:
        """Log the completion of an import stage.
        
        Args:
            workflow_run_id: The workflow run ID
            stage_key: Stage identifier
            success: Whether the stage succeeded
            message: Optional result message
            
        Returns:
            True if logged successfully
        """
        if db_cursor is None:
            return False
            
        status = "succeeded" if success else "failed"
        
        try:
            with db_cursor() as cur:
                # Update the most recent stage run for this stage_key
                cur.execute(
                    """
                    UPDATE workflow_stage_runs
                    SET status = %s,
                        message = %s,
                        completed_at = NOW()
                    WHERE workflow_run_id = %s
                      AND stage_key = %s
                      AND completed_at IS NULL
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    (status, message, workflow_run_id, stage_key),
                )
            logger.info(
                f"Completed stage {stage_key} for workflow run {workflow_run_id}: {status}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log stage completion: {e}")
            return False
    
    def dispatch_workflow(self, workflow_run_id: int) -> bool:
        """Dispatch a Celery task to process the workflow.
        
        Args:
            workflow_run_id: The workflow run ID
            
        Returns:
            True if dispatched successfully
        """
        try:
            from services.tasks import wf3_firstcard_invoice
            
            # Queue the task
            task = wf3_firstcard_invoice.apply_async(
                args=[workflow_run_id],
                queue="workflow",
            )
            
            logger.info(
                f"Dispatched workflow run {workflow_run_id} (task_id={task.id})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch workflow: {e}")
            return False
```

#### Test:
```python
def test_workflow_coordinator_complete():
    coordinator = WorkflowCoordinator()
    
    # Test create workflow run
    run_id = coordinator.create_workflow_run(
        workflow_key="WF3_FIRSTCARD_INVOICE",
        source_channel="test",
        file_id="test-123",
        content_hash="abc123",
    )
    assert run_id is not None
    
    # Test begin stage
    assert coordinator.begin_import_stage(run_id, "test_stage", "Testing")
    
    # Test complete stage
    assert coordinator.complete_import_stage(run_id, "test_stage", True, "Done")
    
    # Test dispatch
    assert coordinator.dispatch_workflow(run_id)
```

#### Acceptanskriterier:
- [ ] `create_workflow_run()` skapar rad i `workflow_runs`
- [ ] `begin_import_stage()` skapar rad i `workflow_stage_runs`
- [ ] `complete_import_stage()` uppdaterar `workflow_stage_runs`
- [ ] `dispatch_workflow()` kör Celery task
- [ ] Upload flow fungerar end-to-end
- [ ] Resume flow fungerar
- [ ] Restart flow fungerar

---

### 🔴 TASK 3.2: Ta bort manuella SQL status-updates

**Prioritet:** P0 - BLOCKERANDE  
**Estimat:** 2 timmar  
**Ansvarig:** Backend team

#### Problem:
Flera endpoints uppdaterar `processing_status` direkt med SQL istället för via `transition_processing_status()`:
- `upload.py` - `_ensure_processing_state()` (rad 67-80)
- `matching.py` - `_ensure_processing_state()` (rad 39-52)

#### Åtgärd:
Ta bort alla `_ensure_processing_state()` funktioner och använd coordinator istället.

#### Implementation:

**Fil:** `backend/src/api/reconciliation_firstcard/routes/upload.py`

```python
# TA BORT denna funktion:
def _ensure_processing_state(invoice_id: str) -> None:
    # ... DELETE ...

# I import_invoice() rad 195-217, ERSÄTT med:
coordinator = WorkflowCoordinator()
coordinator.start_processing(invoice_id)
```

**Fil:** `backend/src/api/reconciliation_firstcard/routes/matching.py`

```python
# TA BORT denna funktion:
def _ensure_processing_state(invoice_id: str) -> None:
    # ... DELETE ...

# I match_invoice_lines() rad 59, ERSÄTT med:
# Inget behövs - status hanteras av workflow
```

#### Acceptanskriterier:
- [ ] Inga direkta SQL-updates av status kvar
- [ ] Alla status-ändringar går via `transition_*` funktioner
- [ ] Import flow fungerar
- [ ] Match flow fungerar

---

### 🟠 TASK 3.3: Dokumentera legacy-tabeller och planera migration

**Prioritet:** P1 - KRITISKT  
**Estimat:** 3 timmar  
**Ansvarig:** Backend team + Arkitekt

#### Problem:
Systemet använder två parallella tabellstrukturer:
- Nya: `invoice_documents` + `invoice_lines`
- Legacy: `creditcard_invoices_main` + `creditcard_invoice_items`

Detta skapar synkroniseringsproblem och risk för inkonsistens.

#### Åtgärd:
1. Dokumentera exakt vilka fält som används från varje tabell
2. Bestäm migration-strategi
3. Implementera enligt vald strategi

#### Implementation Plan:

**Steg 1: Dokumentation (1 timme)**

Skapa fil: `docs/CREDITCARD_LEGACY_TABLES_MAPPING.md`

```markdown
# Legacy Tabeller - Mapping och Migration Plan

## Nuvarande användning

### creditcard_invoices_main
**Används av:**
- status.py invoice_detail() - rad 141-190
- statements.py list_statements() - rad 125-138

**Fält som läses:**
- id (länkas via metadata.creditcard_main_id)
- card_type
- card_name
- card_number_masked
- card_holder
- due_date
- amount_to_pay
- invoice_date

**Fält som skrivs:**
- Alla fält (via _persist_creditcard_invoice_main i workflow_tasks)

### creditcard_invoice_items
**Används av:**
- lines.py line_candidates() - rad 91-127
- creditcard_tasks.py _load_credit_items_for_invoice() - rad 370-427
- matching.py update_line_match() - rad 69-82

**Fält som läses:**
- id
- main_id
- line_no
- purchase_date
- amount_original
- amount_sek
- gross_amount
- net_amount
- merchant_name
- description
- matched

**Fält som skrivs:**
- matched (via _persist_credit_card_match)

## Migration Strategier

### Strategi A: Soft Migration (Rekommenderad för Fas 3)
1. Fortsätt skriva till BÅDA systemen
2. Läs först från invoice_lines, fallback till legacy
3. Lägg till "migrated" flag i metadata
4. Migrera backend endpoint för endpoint
5. När alla endpoints migrerade: ta bort legacy writes

**Fördelar:**
- Låg risk
- Gradvis övergång
- Rollback möjlig

**Nackdelar:**
- Dubbelskrivning kvar tillfälligt
- Mer kod att underhålla

### Strategi B: Hard Migration
1. Migrera all historisk data från legacy → nya tabeller
2. Ta bort all legacy-kod på en gång
3. Deploy med downtime

**Fördelar:**
- Rent system direkt
- Mindre kod

**Nackdelar:**
- Hög risk
- Kräver downtime
- Svår att rolla tillbaka
```

**Steg 2: Bestäm strategi (30 min)**

Rekommendation: **Strategi A (Soft Migration)**

**Steg 3: Implementera fas 1 av soft migration (1.5 timme)**

Lägg till helper-funktion:

**Fil:** `backend/src/api/reconciliation_firstcard/utils/db_helpers.py`

```python
def get_invoice_lines_unified(invoice_id: str) -> list[dict[str, Any]]:
    """Get invoice lines from new OR legacy tables.
    
    Priority:
    1. Read from invoice_lines if available
    2. Fallback to creditcard_invoice_items if legacy invoice
    
    Returns unified structure.
    """
    if db_cursor is None:
        return []
    
    lines = []
    
    # Try new table first
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT id, transaction_date, amount, merchant_name, 
                       description, match_status, matched_file_id, match_score
                FROM invoice_lines
                WHERE invoice_id = %s
                ORDER BY transaction_date ASC, id ASC
                """,
                (invoice_id,),
            )
            rows = cur.fetchall() or []
            
            if rows:
                # Found data in new table
                for row in rows:
                    lines.append({
                        "id": row[0],
                        "transaction_date": row[1],
                        "amount": row[2],
                        "merchant_name": row[3],
                        "description": row[4],
                        "match_status": row[5],
                        "matched_file_id": row[6],
                        "match_score": row[7],
                        "source": "invoice_lines",
                    })
                return lines
    except Exception as e:
        logger.warning(f"Failed to read from invoice_lines: {e}")
    
    # Fallback to legacy table
    metadata = _load_invoice_metadata(invoice_id) or {}
    main_id = metadata.get("creditcard_main_id")
    
    if not main_id:
        return []
    
    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT ci.id, ci.purchase_date, ci.amount_sek, ci.merchant_name,
                       ci.description, ci.matched,
                       crm.receipt_id, NULL as match_score
                FROM creditcard_invoice_items ci
                LEFT JOIN creditcard_receipt_matches crm ON crm.invoice_item_id = ci.id
                WHERE ci.main_id = %s
                ORDER BY ci.line_no ASC, ci.id ASC
                """,
                (main_id,),
            )
            rows = cur.fetchall() or []
            
            for row in rows:
                match_status = "pending"
                if row[5] == 2:
                    match_status = "manual"
                elif row[5] == 1:
                    match_status = "auto"
                
                lines.append({
                    "id": row[0],
                    "transaction_date": row[1],
                    "amount": row[2],
                    "merchant_name": row[3],
                    "description": row[4],
                    "match_status": match_status,
                    "matched_file_id": row[6],
                    "match_score": row[7],
                    "source": "creditcard_invoice_items",  # Mark as legacy
                })
    except Exception as e:
        logger.error(f"Failed to read from legacy tables: {e}")
    
    return lines
```

#### Acceptanskriterier:
- [ ] Dokumentation skapad
- [ ] Migration-strategi beslutad
- [ ] Helper-funktion implementerad
- [ ] Endpoints uppdaterade att använda helper
- [ ] Tester visar att både nya och legacy-data fungerar

---

### 🟠 TASK 3.4: Centralisera workflow stage hantering

**Prioritet:** P1 - KRITISKT  
**Estimat:** 2 timmar  
**Ansvarig:** Backend team

#### Problem:
Workflow stages loggas på två ställen:
1. `upload.py` försöker logga `src_fc`, `fc_create` (anropar coordinator-metoder som nu finns)
2. `workflow_tasks.py` loggar `fc_ocr`, `ocr_merge`, etc.

Detta skapar dubbla ansvarsområden.

#### Åtgärd:
Beslut: **ALL stage-loggning ska ske i workflow_tasks.py**

Endpoints (upload.py, statements.py) ska ENDAST:
1. Validera input
2. Skapa workflow run
3. Dispatcha workflow
4. Returnera response

#### Implementation:

**Fil:** `backend/src/api/reconciliation_firstcard/routes/upload.py`

```python
@recon_bp.post("/reconciliation/firstcard/upload-invoice")
def upload_invoice() -> Any:
    """Upload a FirstCard invoice (PDF or image) and dispatch a workflow."""
    
    # ... existing file processing code ...
    
    # Simplified workflow creation - NO STAGE LOGGING HERE
    coordinator = WorkflowCoordinator()
    workflow_run_id = coordinator.create_workflow_run(
        workflow_key="WF3_FIRSTCARD_INVOICE",
        source_channel="kortmatchning_upload",
        file_id=invoice_id,
        content_hash=file_hash,
    )
    
    if not workflow_run_id:
        return jsonify({"error": "workflow_creation_failed"}), 500
    
    # Create invoice document
    metadata["workflow_run_id"] = workflow_run_id
    create_invoice_document(
        invoice_id=invoice_id,
        invoice_type="credit_card_invoice",
        status=InvoiceDocumentStatus.IMPORTED.value,
        metadata=metadata,
        processing_status=InvoiceProcessingStatus.UPLOADED.value,
    )
    
    # Dispatch workflow - stages will be logged by workflow task
    if not coordinator.dispatch_workflow(workflow_run_id):
        return jsonify({"error": "workflow_dispatch_failed"}), 500
    
    response = {
        "invoice_id": invoice_id,
        "status": "processing",
        "workflow_run_id": workflow_run_id,
    }
    return jsonify(response), 201
```

**Fil:** `backend/src/services/tasks/workflow_tasks.py`

Lägg till stage-loggning i början av workflow:

```python
def wf3_firstcard_invoice(workflow_run_id: int) -> int:
    """Workflow 3: FirstCard Invoice Processing."""
    wfr = ensure_workflow(workflow_run_id, expected_prefix="WF3_")
    mark_stage(workflow_run_id, "firstcard_invoice", "running", start=True)
    
    # ADD: Log source stage
    begin_import_stage(
        workflow_run_id,
        "src_fc",
        message="FirstCard invoice uploaded",
    )
    complete_import_stage(
        workflow_run_id,
        "src_fc",
        success=True,
        message="File received",
    )
    
    file_id = wfr.get("file_id")
    # ... rest of workflow ...
```

#### Acceptanskriterier:
- [ ] upload.py loggar INGA stages
- [ ] statements.py (resume/restart) loggar INGA stages
- [ ] workflow_tasks.py loggar ALLA stages
- [ ] Frontend ser korrekt stage-progression
- [ ] current_stage_key uppdateras korrekt

---

### 🟡 TASK 3.5: Lägg till integration tests

**Prioritet:** P2 - VIKTIGT  
**Estimat:** 4 timmar  
**Ansvarig:** QA + Backend team

#### Implementation:

**Fil:** `backend/tests/integration/test_firstcard_flow.py`

```python
import pytest
import time
from services.db.connection import db_cursor
from api.reconciliation_firstcard.services.workflow_coordinator import WorkflowCoordinator

@pytest.fixture
def test_invoice_file():
    """Load test PDF file."""
    with open("tests/fixtures/firstcard_test.pdf", "rb") as f:
        return f.read()

def test_complete_upload_to_match_flow(test_invoice_file, api_client):
    """Test complete flow: upload → OCR → AI → match → confirm."""
    
    # Step 1: Upload invoice
    response = api_client.post(
        "/ai/api/reconciliation/firstcard/upload-invoice",
        data={"invoice": (test_invoice_file, "test.pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    invoice_id = data["invoice_id"]
    workflow_run_id = data["workflow_run_id"]
    
    # Step 2: Wait for OCR to complete (max 30 seconds)
    for _ in range(30):
        response = api_client.get(
            f"/ai/api/reconciliation/firstcard/invoices/{invoice_id}/status"
        )
        assert response.status_code == 200
        status_data = response.json()
        
        if status_data["processing_status"] in ["ready_for_matching", "completed"]:
            break
        
        time.sleep(1)
    else:
        pytest.fail("OCR did not complete within 30 seconds")
    
    # Verify OCR progress
    assert status_data["ocr_progress"]["percentage"] == 100.0
    
    # Step 3: Check that lines were created
    assert status_data["line_counts"]["total"] > 0
    
    # Step 4: Trigger matching
    response = api_client.post(
        "/ai/api/reconciliation/firstcard/match",
        json={"invoice_id": invoice_id},
    )
    assert response.status_code == 200
    match_data = response.json()
    
    # Verify some lines matched
    assert match_data["matched"] >= 0
    
    # Step 5: Get detail to verify data structure
    response = api_client.get(
        f"/ai/api/reconciliation/firstcard/invoices/{invoice_id}"
    )
    assert response.status_code == 200
    detail = response.json()
    
    assert "invoice" in detail
    assert "lines" in detail
    assert detail["invoice"]["id"] == invoice_id
    
    # Step 6: Confirm if all matched
    if detail["invoice"]["line_counts"]["unmatched"] == 0:
        response = api_client.post(
            f"/ai/api/reconciliation/firstcard/statements/{invoice_id}/confirm"
        )
        assert response.status_code == 200
        
        # Verify status is completed
        response = api_client.get(
            f"/ai/api/reconciliation/firstcard/invoices/{invoice_id}"
        )
        data = response.json()
        assert data["invoice"]["status"] == "completed"

def test_resume_stuck_workflow(api_client, db_cursor):
    """Test resume functionality for stuck invoices."""
    
    # Create a stuck invoice (status = matching but workflow stopped)
    invoice_id = "test-stuck-123"
    
    with db_cursor() as cur:
        # Insert test invoice
        cur.execute(
            """
            INSERT INTO invoice_documents (id, invoice_type, status, processing_status)
            VALUES (%s, 'credit_card_invoice', 'matching', 'ocr_done')
            """,
            (invoice_id,),
        )
        
        # Insert stuck workflow
        cur.execute(
            """
            INSERT INTO workflow_runs (workflow_key, file_id, status, current_stage)
            VALUES ('WF3_FIRSTCARD_INVOICE', %s, 'running', 'fc_ocr')
            """,
            (invoice_id,),
        )
        workflow_run_id = cur.lastrowid
    
    # Resume workflow
    response = api_client.post(
        f"/ai/api/reconciliation/firstcard/statements/{invoice_id}/resume"
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["action"] == "resumed"
    
    # Verify workflow was re-dispatched
    # (In real test, check Celery task was created)

def test_restart_workflow(api_client, db_cursor):
    """Test restart functionality."""
    
    # Create a failed invoice
    invoice_id = "test-failed-456"
    content_hash = "abc123hash"
    
    with db_cursor() as cur:
        # Insert test invoice
        cur.execute(
            """
            INSERT INTO invoice_documents (id, invoice_type, status, processing_status)
            VALUES (%s, 'credit_card_invoice', 'failed', 'failed')
            """,
            (invoice_id,),
        )
        
        # Insert file record
        cur.execute(
            """
            INSERT INTO unified_files (id, file_type, content_hash)
            VALUES (%s, 'cc_pdf', %s)
            """,
            (invoice_id, content_hash),
        )
    
    # Restart workflow
    response = api_client.post(
        f"/ai/api/reconciliation/firstcard/statements/{invoice_id}/restart"
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["ok"] is True
    assert data["action"] == "restarted"
    assert "workflow_run_id" in data
    
    # Verify new workflow was created
    with db_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM workflow_runs WHERE file_id=%s",
            (invoice_id,),
        )
        count = cur.fetchone()[0]
    
    assert count >= 2  # Old workflow + new workflow
```

#### Acceptanskriterier:
- [ ] Test för complete flow (upload → match) passerar
- [ ] Test för resume fungerar
- [ ] Test för restart fungerar
- [ ] Tests kan köras i CI/CD pipeline

---

## FAS 4 - FÖRBÄTTRINGAR (Efter deployment)

### 🟡 TASK 4.1: Migrera detail endpoint till invoice_lines

**Prioritet:** P2 - VIKTIGT  
**Estimat:** 3 timmar

Se TASK 3.3 för implementation details.

---

### 🟡 TASK 4.2: Lägg till observability metrics

**Prioritet:** P2 - VIKTIGT  
**Estimat:** 2 timmar

```python
# Lägg till metrics för:
- workflow_created_total
- workflow_completed_total
- workflow_failed_total
- lines_matched_total
- lines_unmatched_total
- match_score_distribution
```

---

### 🟢 TASK 4.3: Optimera candidates query

**Prioritet:** P3 - FÖRBÄTTRING  
**Estimat:** 2 timmar

`lines.py` `line_candidates()` kan optimeras med bättre index.

---

### 🟢 TASK 4.4: Lägg till caching för statements list

**Prioritet:** P3 - FÖRBÄTTRING  
**Estimat:** 2 timmar

`statements.py` `list_statements()` kan cache:a resultat i 30 sekunder.

---

## SAMMANFATTNING

### Total Estimat för Fas 3 (P0 + P1):
- TASK 3.1: 4 timmar
- TASK 3.2: 2 timmar
- TASK 3.3: 3 timmar
- TASK 3.4: 2 timmar
- TASK 3.5: 4 timmar

**TOTALT: 15 timmar (cirka 2 arbetsdagar)**

### Kritisk Path:
```
TASK 3.1 (Komplettera coordinator)
    ↓
TASK 3.2 (Ta bort manuella SQL-updates)
    ↓
TASK 3.4 (Centralisera stage hantering)
    ↓
TASK 3.5 (Integration tests)
```

TASK 3.3 kan köras parallellt med övriga.

### Definition of Done för Fas 3:
- [ ] Alla P0 tasks slutförda
- [ ] Alla P1 tasks slutförda
- [ ] Integration tests passerar
- [ ] Manuell E2E test: upload → match → confirm fungerar
- [ ] Manuell test: resume fungerar
- [ ] Manuell test: restart fungerar
- [ ] Code review genomförd
- [ ] Documentation uppdaterad

---

**Skapad:** 2025-11-09  
**Nästa review:** Efter Fas 3 completion
