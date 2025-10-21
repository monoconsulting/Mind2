# Overlay Solution - Box Generation Som Sista Steg

**Datum:** 2025-10-19
**Princip:** Boxes ska genereras ABSOLUT SIST när all data är färdig
**Rätt plats:** Efter AI4 (eller AI5 för receipts, AI6 för creditcard_invoice)

---

## KORREKT WORKFLOW-FÖRSTÅELSE

### Receipt Workflow:
1. **Upload** → Fil sparas
2. **OCR** → Text extraheras (RAW, ingen semantisk analys)
3. **AI1** → Document classification
4. **AI2** → Expense classification
5. **AI3** → Data extraction (structured fields)
6. **AI4** → Accounting proposals
7. **AI5** → Credit card matching (om applicable)
8. **✨ NYA STEGET: Box Generation** ← HÄR SKA DET SKE

### Credit Card Invoice Workflow:
1. **Upload** → Fil sparas
2. **OCR** → Text extraheras
3. **AI6** → Credit card invoice parsing
4. **✨ NYA STEGET: Box Generation** ← HÄR SKA DET SKE

---

## VARFÖR SIST?

### Efter AI4/AI6 Har Vi:
- ✅ **Alla extraherade värden** med hög confidence
- ✅ **Normalized data** (formaterade datum, belopp, etc.)
- ✅ **Company matching** genomförd (vet vilket företag det är)
- ✅ **Item-level data** extraherad och sparad
- ✅ **Accounting proposals** genererade (för receipts)

### Med Denna Data Kan Vi:
1. **Matcha OCR boxes mot extracted values**
2. **Assigna semantic field names** (company.name, receipt.gross_amount)
3. **Validera matches** (confidence check)
4. **Gruppera boxes** per field (t.ex. flera boxes för samma value)

---

## NY DESIGN: AI7 - BOX ENRICHMENT STEP

### Koncept:
Skapa ett nytt AI-steg (AI7) som **ENBART** ansvarar för box enrichment.

**Input:**
- OCR raw boxes (från OCR-steget, sparade som `ocr_boxes.json`)
- Extracted data från AI3/AI4/AI6
- Company data (från matching)

**Process:**
- Matchar OCR text mot extracted values
- Assignar semantic field names
- Beräknar confidence för matchning
- Grupperar multi-box fields

**Output:**
- `boxes.json` med enriched data (semantic field names)

### Fördelar:
- ✅ Separerar concerns (OCR = text detection, AI7 = semantic mapping)
- ✅ Kan köras om separat vid behov
- ✅ Enkel att testa isolerat
- ✅ Fungerar för både receipts och creditcard_invoice

---

## IMPLEMENTATION PLAN

### STEG 1: Modifiera OCR för att Spara Raw Boxes

**Fil:** `backend/src/services/ocr.py`

**Nuvarande (rad 334):**
```python
boxes = ocr_result.get("boxes", [])
_write_boxes(base_path, receipt_id, boxes)
```

**Ändra till:**
```python
boxes = ocr_result.get("boxes", [])
# Save raw OCR boxes (NOT enriched yet)
_write_raw_boxes(base_path, receipt_id, boxes)
```

**Ny function:**
```python
def _write_raw_boxes(base: str | Path, receipt_id: str, boxes: List[Dict[str, Any]]) -> None:
    """Save raw OCR boxes before semantic enrichment."""
    root = _receipt_dir(base, receipt_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "ocr_boxes.json").write_text(
        json.dumps(boxes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
```

---

### STEG 2: Skapa AI7 Box Enrichment Service

**Ny fil:** `backend/src/services/box_enrichment.py`

```python
"""
AI7 - Box Enrichment Service

Matches OCR bounding boxes to semantic field identifiers.
Runs AFTER all data extraction is complete (AI3/AI4/AI6).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _normalize_text(text: Any) -> str:
    """Normalize text for comparison."""
    if text is None:
        return ""
    return str(text).strip().lower()


def _is_fuzzy_match(ocr_text: str, field_value: Any, min_length: int = 4) -> bool:
    """
    Check if OCR text fuzzy matches a field value.

    Strategies:
    1. Exact match
    2. Partial match (substring)
    3. Prefix match (for truncated text)
    """
    ocr_normalized = _normalize_text(ocr_text)
    value_normalized = _normalize_text(field_value)

    if not ocr_normalized or not value_normalized:
        return False

    # Exact match
    if ocr_normalized == value_normalized:
        return True

    # Partial match (both ways, min length check)
    if len(ocr_normalized) >= min_length:
        if ocr_normalized in value_normalized:
            return True
        if value_normalized in ocr_normalized:
            return True

    # Prefix match for truncated names (min 6 chars)
    if len(ocr_normalized) >= 6:
        if value_normalized.startswith(ocr_normalized):
            return True

    return False


def _find_matching_field(
    ocr_text: str,
    receipt_data: Dict[str, Any],
    company_data: Dict[str, Any],
) -> Tuple[Optional[str], float]:
    """
    Find which field (if any) matches the OCR text.

    Returns:
        (field_name, confidence) where field_name is like "receipt.gross_amount" or "company.name"
    """
    # Try receipt fields first
    for field_name, field_value in receipt_data.items():
        if _is_fuzzy_match(ocr_text, field_value):
            # Higher confidence for exact matches
            confidence = 0.95 if _normalize_text(ocr_text) == _normalize_text(field_value) else 0.75
            return (f"receipt.{field_name}", confidence)

    # Try company fields
    for field_name, field_value in company_data.items():
        if _is_fuzzy_match(ocr_text, field_value):
            confidence = 0.95 if _normalize_text(ocr_text) == _normalize_text(field_value) else 0.75
            return (f"company.{field_name}", confidence)

    # No match found
    return (None, 0.0)


def enrich_boxes(
    receipt_id: str,
    receipt_data: Dict[str, Any],
    company_data: Dict[str, Any],
    items_data: List[Dict[str, Any]],
    storage_dir: str | Path,
) -> List[Dict[str, Any]]:
    """
    Enrich OCR boxes with semantic field names.

    Args:
        receipt_id: Receipt identifier
        receipt_data: Extracted receipt fields (from AI3)
        company_data: Company/merchant data (from AI3 + matching)
        items_data: Line items (from AI3)
        storage_dir: Base storage directory

    Returns:
        List of enriched boxes with semantic "field" identifiers
    """
    base_path = Path(storage_dir)
    receipt_dir = base_path / receipt_id

    # Load raw OCR boxes
    ocr_boxes_path = receipt_dir / "ocr_boxes.json"
    if not ocr_boxes_path.exists():
        logger.warning(f"No OCR boxes found for {receipt_id}")
        return []

    try:
        ocr_boxes = json.loads(ocr_boxes_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Failed to load OCR boxes for {receipt_id}: {e}")
        return []

    if not isinstance(ocr_boxes, list):
        logger.warning(f"OCR boxes not a list for {receipt_id}")
        return []

    enriched_boxes = []

    for box in ocr_boxes:
        ocr_text = box.get("field", "")  # Original OCR text

        # Find matching semantic field
        matched_field, match_confidence = _find_matching_field(
            ocr_text,
            receipt_data,
            company_data,
        )

        enriched_box = {
            "ocr_text": ocr_text,  # Preserve original
            "confidence": box.get("confidence"),  # OCR confidence
            "x": box.get("x"),
            "y": box.get("y"),
            "w": box.get("w"),
            "h": box.get("h"),
        }

        if matched_field:
            enriched_box["field"] = matched_field
            enriched_box["match_confidence"] = match_confidence
        else:
            # Keep original OCR text if no match
            enriched_box["field"] = ocr_text
            enriched_box["match_confidence"] = 0.0

        enriched_boxes.append(enriched_box)

    # TODO: Handle item-level boxes (items[0].name, items[1].amount, etc.)
    # This requires more sophisticated matching logic

    return enriched_boxes


def save_enriched_boxes(
    receipt_id: str,
    enriched_boxes: List[Dict[str, Any]],
    storage_dir: str | Path,
) -> bool:
    """Save enriched boxes to boxes.json."""
    base_path = Path(storage_dir)
    receipt_dir = base_path / receipt_id
    receipt_dir.mkdir(parents=True, exist_ok=True)

    boxes_path = receipt_dir / "boxes.json"
    try:
        boxes_path.write_text(
            json.dumps(enriched_boxes, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(enriched_boxes)} enriched boxes for {receipt_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save enriched boxes for {receipt_id}: {e}")
        return False


def run_box_enrichment(receipt_id: str, storage_dir: str | Path | None = None) -> Dict[str, Any]:
    """
    Main entry point for AI7 box enrichment.

    Should be called AFTER AI4 (for receipts) or AI6 (for creditcard_invoice).

    Returns:
        Stats about enrichment process
    """
    import os

    base = storage_dir or os.getenv("STORAGE_DIR", "/data/storage")

    # Load extracted data (from AI3/AI4)
    # TODO: Implement data loading from database or file storage
    receipt_data = _load_receipt_data(receipt_id)
    company_data = _load_company_data(receipt_id)
    items_data = _load_items_data(receipt_id)

    # Enrich boxes
    enriched_boxes = enrich_boxes(
        receipt_id,
        receipt_data,
        company_data,
        items_data,
        base,
    )

    # Save enriched boxes
    success = save_enriched_boxes(receipt_id, enriched_boxes, base)

    # Calculate stats
    matched_count = sum(1 for box in enriched_boxes if box.get("match_confidence", 0) > 0.5)
    unmatched_count = len(enriched_boxes) - matched_count

    return {
        "success": success,
        "total_boxes": len(enriched_boxes),
        "matched_boxes": matched_count,
        "unmatched_boxes": unmatched_count,
        "match_rate": matched_count / len(enriched_boxes) if enriched_boxes else 0.0,
    }


def _load_receipt_data(receipt_id: str) -> Dict[str, Any]:
    """Load receipt data from database."""
    # TODO: Implement
    # Query unified_files WHERE id = receipt_id
    # Return fields: gross_amount, net_amount, purchase_datetime, etc.
    return {}


def _load_company_data(receipt_id: str) -> Dict[str, Any]:
    """Load company data from database."""
    # TODO: Implement
    # Query companies JOIN unified_files WHERE unified_files.id = receipt_id
    # Return fields: name, orgnr, address, etc.
    return {}


def _load_items_data(receipt_id: str) -> List[Dict[str, Any]]:
    """Load line items from database."""
    # TODO: Implement
    # Query receipt_items WHERE main_id = receipt_id
    # Return list of items with name, amount, etc.
    return []
```

---

### STEG 3: Integrera AI7 i Workflow

**Fil:** `backend/src/api/ai_processing.py` eller `backend/src/tasks.py`

**För receipts (efter AI4):**
```python
# Efter AI4 completion
if ai4_success:
    # Run box enrichment
    from services.box_enrichment import run_box_enrichment

    box_stats = run_box_enrichment(file_id, storage_dir)
    logger.info(f"Box enrichment for {file_id}: {box_stats}")

    # Update AI status
    _set_ai_stage(cursor, file_id, "AI7", box_stats["match_rate"])
```

**För creditcard_invoice (efter AI6):**
```python
# Efter AI6 completion
if ai6_success:
    # Run box enrichment
    from services.box_enrichment import run_box_enrichment

    box_stats = run_box_enrichment(file_id, storage_dir)
    logger.info(f"Box enrichment for {file_id}: {box_stats}")

    _set_ai_stage(cursor, file_id, "AI7", box_stats["match_rate"])
```

---

### STEG 4: Database Schema Update (Optional)

Om vi vill tracka AI7:

```sql
ALTER TABLE unified_files
ADD COLUMN ai7_status VARCHAR(32) DEFAULT NULL,
ADD COLUMN ai7_confidence DECIMAL(5,4) DEFAULT NULL,
ADD COLUMN ai7_timestamp TIMESTAMP DEFAULT NULL;
```

---

## MIGRATION STRATEGY

### För Existing Receipts:

**Option A: Lazy Migration (Recommended)**
- Gamla receipts behåller nuvarande boxes.json (med OCR text)
- Frontend fallback fuzzy matching fungerar
- Nya receipts får enriched boxes från AI7

**Option B: Batch Re-enrichment**
- Kör AI7 retroaktivt för alla receipts som har AI4 completed
- Kan göras som background job

```python
# Migration script
def migrate_existing_receipts():
    """Run AI7 box enrichment for all completed receipts."""
    from services.db.connection import db_cursor

    with db_cursor() as cur:
        cur.execute("""
            SELECT id FROM unified_files
            WHERE ai4_status = 'completed'
            AND ai7_status IS NULL
            AND deleted_at IS NULL
        """)
        receipt_ids = [row[0] for row in cur.fetchall()]

    for receipt_id in receipt_ids:
        try:
            run_box_enrichment(receipt_id)
        except Exception as e:
            logger.error(f"Failed to enrich {receipt_id}: {e}")
```

---

## EXPECTED RESULTS

### Innan AI7:
```json
// ocr_boxes.json (efter OCR)
[
  {
    "field": "BAUHAUS",  // OCR text
    "confidence": 0.99,
    "x": 0.7,
    "y": 0.55,
    "w": 0.18,
    "h": 0.06
  }
]
```

### Efter AI7:
```json
// boxes.json (efter AI7 enrichment)
[
  {
    "field": "company.name",  // ← Semantic identifier
    "ocr_text": "BAUHAUS",     // ← Preserved OCR text
    "confidence": 0.99,         // ← OCR confidence
    "match_confidence": 0.95,   // ← Match confidence
    "x": 0.7,
    "y": 0.55,
    "w": 0.18,
    "h": 0.06
  }
]
```

### Frontend Receives:
```javascript
// From /api/receipts/{id}/modal endpoint
{
  "boxes": [
    {
      "field": "company.name",  // ← Matches field keys!
      "ocr_text": "BAUHAUS",
      "confidence": 0.99,
      "match_confidence": 0.95,
      "x": 0.7,
      "y": 0.55,
      "w": 0.18,
      "h": 0.06
    }
  ]
}
```

**Result:** Hover works perfectly without fuzzy matching!

---

## TIMELINE

**Day 1:**
- [ ] STEG 1: Modify OCR to save ocr_boxes.json (30min)
- [ ] STEG 2: Implement box_enrichment.py (2-3h)
- [ ] STEG 2b: Implement data loading helpers (1h)

**Day 2:**
- [ ] STEG 3: Integrate AI7 into workflow (1h)
- [ ] Test with sample receipts (1h)
- [ ] STEG 4: Database schema update (30min)

**Day 3:**
- [ ] Frontend testing (verify semantic matching works)
- [ ] Edge case handling
- [ ] Documentation

**Total Effort:** 6-8 hours

---

## ADVANTAGES OF THIS APPROACH

1. ✅ **Semantic names available** - Frontend gets proper field identifiers
2. ✅ **Separation of concerns** - OCR does OCR, AI7 does semantic mapping
3. ✅ **Testable** - Can test AI7 isolation from rest of pipeline
4. ✅ **Re-runnable** - Can re-run AI7 if matching logic improves
5. ✅ **Works for both workflows** - Receipts AND creditcard_invoice
6. ✅ **Backwards compatible** - Old receipts still work with fuzzy matching
7. ✅ **Confidence tracking** - Know which matches are reliable

---

## NEXT STEPS

1. **Du bestämmer:** Ska vi implementera AI7 som eget steg?
2. **Alternativ:** Eller integrera i AI4 som sista del (mindre clean men snabbare)?
3. **Migration:** Ska gamla receipts få nya boxes eller nöja oss med lazy migration?

**Vad tycker du - ska vi köra på AI7-approach?**

---

**Plan Created:** 2025-10-19
**Status:** READY FOR DECISION
**Recommended:** AI7 as separate step (cleaner architecture)
