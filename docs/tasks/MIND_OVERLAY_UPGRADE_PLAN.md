# MIND Overlay Upgrade Plan - AI7 Box Enrichment Implementation

**Datum:** 2025-10-19
**Version:** 1.0
**Status:** 📋 PLANERING KLAR - READY FOR IMPLEMENTATION
**Estimerad Total Tid:** 12-16 timmar

---

## INNEHÅLLSFÖRTECKNING

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Architecture](#solution-architecture)
4. [Implementation Phases](#implementation-phases)
5. [Detailed Task Breakdown](#detailed-task-breakdown)
6. [Testing Strategy](#testing-strategy)
7. [Migration Plan](#migration-plan)
8. [Rollback Plan](#rollback-plan)
9. [Success Criteria](#success-criteria)
10. [Timeline](#timeline)

---

## EXECUTIVE SUMMARY

### Mål
Implementera AI7 Box Enrichment som ett nytt workflow-steg som körs **efter** all dataextraktion är klar (AI3/AI4 för receipts, AI6 för creditcard_invoice). Detta kommer ge overlays semantic field identifiers istället för OCR text, vilket gör hover-highlighting fullt funktionell.

### Omfattning
- **Backend:** Nytt AI7-steg i workflow
- **Backend:** Ny service `box_enrichment.py`
- **Backend:** Modifikation av OCR-service
- **Backend:** Integration i workflow engine
- **Database:** Nya kolumner för AI7 tracking (optional)
- **Frontend:** Ingen ändring behövs (API-compatible)
- **Migration:** Retroaktiv enrichment av existing receipts (optional)

### Business Value
- ✅ Hover highlighting mellan fields och overlays fungerar
- ✅ Bättre användarupplevelse i receipt preview
- ✅ Visuell validering av extracted data
- ✅ Lättare att spotta fel i AI-extraction

### Risk Level
🟢 **LÅG RISK**
- Påverkar inte existerande funktionalitet
- Bakåtkompatibel (gamla receipts fungerar fortfarande)
- Kan rullas tillbaka enkelt

---

## PROBLEM STATEMENT

### Nuvarande Situation

**OCR-steget (tidigt i workflow):**
```json
// boxes.json skapas direkt efter OCR
{
  "field": "BAUHAUS",  // ← OCR text, inte semantic identifier
  "confidence": 0.99,
  "x": 0.7,
  "y": 0.55,
  "w": 0.18,
  "h": 0.06
}
```

**Frontend field keys:**
```javascript
{key: 'name', label: 'Företag'}  // Värde: "BAUHAUS"
```

**Problem:**
- "BAUHAUS" matchar inte "name"
- Hover highlighting fungerar inte
- Ingen koppling mellan overlay och field

### Root Cause Analysis

**Varför skapas boxes så tidigt?**

OCR-steget (steg 2 av 8) har tillgång till:
- ✅ Bild pixels
- ✅ OCR text extraction
- ✅ Bounding box coordinates
- ❌ **SAKNAR:** Semantic understanding (vad är företagsnamn vs belopp vs datum)

**Semantic understanding finns först efter:**
- AI1: Document classification
- AI2: Expense classification
- AI3: **Data extraction** ← Här vet vi vad varje fält betyder
- AI4: Accounting proposals

**Därför måste boxes enrichas EFTER AI3 är klar.**

---

## SOLUTION ARCHITECTURE

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│ NUVARANDE WORKFLOW (RECEIPTS)                               │
├─────────────────────────────────────────────────────────────┤
│ Upload → OCR* → AI1 → AI2 → AI3 → AI4 → (AI5)              │
│          └─ boxes.json (OCR text)                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ NY WORKFLOW (RECEIPTS)                                      │
├─────────────────────────────────────────────────────────────┤
│ Upload → OCR* → AI1 → AI2 → AI3 → AI4 → AI7** → (AI5)      │
│          │                            │                      │
│          └─ ocr_boxes.json            └─ boxes.json         │
│             (raw OCR)                    (enriched)         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ NY WORKFLOW (CREDITCARD_INVOICE)                            │
├─────────────────────────────────────────────────────────────┤
│ Upload → OCR* → AI6 → AI7**                                 │
│          │              │                                    │
│          └─ ocr_boxes.json  └─ boxes.json                   │
└─────────────────────────────────────────────────────────────┘

* OCR sparar ocr_boxes.json istället för boxes.json
** AI7 läser ocr_boxes.json + extracted data → skapar boxes.json
```

### Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ AI7 BOX ENRICHMENT SERVICE                                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  INPUT:                                                      │
│  ├─ ocr_boxes.json (från OCR)                               │
│  ├─ Extracted receipt data (från AI3/AI4)                   │
│  ├─ Extracted company data (från AI3 + matching)            │
│  └─ Line items (från AI3)                                   │
│                                                              │
│  PROCESS:                                                    │
│  ├─ Load OCR boxes                                          │
│  ├─ Load extracted data from DB                             │
│  ├─ FOR EACH box:                                           │
│  │   ├─ Extract OCR text                                    │
│  │   ├─ Match against receipt fields (fuzzy matching)       │
│  │   ├─ Match against company fields (fuzzy matching)       │
│  │   ├─ Match against item fields (optional)                │
│  │   ├─ Assign semantic field name if match found          │
│  │   └─ Calculate match confidence                          │
│  └─ Group multi-box fields (optional)                       │
│                                                              │
│  OUTPUT:                                                     │
│  └─ boxes.json (enriched with semantic field names)         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────┐
│   OCR       │
│   (Step 2)  │
└──────┬──────┘
       │
       │ Creates
       ▼
┌─────────────────────────────┐
│  ocr_boxes.json             │
│  [                          │
│    {                        │
│      "field": "BAUHAUS",    │  ← OCR text (raw)
│      "confidence": 0.99,    │
│      "x": 0.7,              │
│      "y": 0.55,             │
│      "w": 0.18,             │
│      "h": 0.06              │
│    }                        │
│  ]                          │
└──────┬──────────────────────┘
       │
       │ Preserved as-is
       ▼
┌─────────────┐      ┌──────────────────┐
│   AI3       │      │  Database        │
│   AI4       │──────│  - unified_files │
│   (Steps    │      │  - companies     │
│    5-6)     │      │  - receipt_items │
└─────────────┘      └─────────┬────────┘
                               │
                               │ Extracted data
                               ▼
                     ┌─────────────────────┐
                     │  AI7                │
                     │  Box Enrichment     │
                     │  (Step 7)           │
                     └──────────┬──────────┘
                                │
                                │ Creates
                                ▼
                     ┌──────────────────────────────┐
                     │  boxes.json                  │
                     │  [                           │
                     │    {                         │
                     │      "field": "company.name",│  ← Semantic!
                     │      "ocr_text": "BAUHAUS",  │
                     │      "confidence": 0.99,     │  ← OCR conf
                     │      "match_confidence": 0.95│  ← Match conf
                     │      "x": 0.7,               │
                     │      "y": 0.55,              │
                     │      "w": 0.18,              │
                     │      "h": 0.06               │
                     │    }                         │
                     │  ]                           │
                     └──────────┬───────────────────┘
                                │
                                │ Served by API
                                ▼
                     ┌──────────────────────────────┐
                     │  /api/receipts/{id}/modal    │
                     │  Returns boxes to frontend   │
                     └──────────────────────────────┘
```

### Matching Algorithm

```python
def match_box_to_field(ocr_text: str, all_fields: dict) -> tuple[str, float]:
    """
    Match OCR text to semantic field.

    Returns: (field_name, confidence)
    """

    # 1. EXACT MATCH (highest confidence)
    for field_name, field_value in all_fields.items():
        if normalize(ocr_text) == normalize(field_value):
            return (field_name, 0.95)

    # 2. SUBSTRING MATCH (medium confidence)
    for field_name, field_value in all_fields.items():
        if len(ocr_text) >= 4:
            if normalize(ocr_text) in normalize(field_value):
                return (field_name, 0.80)
            if normalize(field_value) in normalize(ocr_text):
                return (field_name, 0.75)

    # 3. PREFIX MATCH (for truncated text, medium confidence)
    for field_name, field_value in all_fields.items():
        if len(ocr_text) >= 6:
            if normalize(field_value).startswith(normalize(ocr_text)):
                return (field_name, 0.70)

    # 4. NUMERIC MATCH (for amounts, dates)
    # Extract numbers from ocr_text and compare
    ocr_numbers = extract_numbers(ocr_text)
    for field_name, field_value in all_fields.items():
        field_numbers = extract_numbers(field_value)
        if ocr_numbers and ocr_numbers == field_numbers:
            return (field_name, 0.85)

    # 5. NO MATCH
    return (None, 0.0)
```

---

## IMPLEMENTATION PHASES

### PHASE 1: Backend - Core Service Implementation
**Tid:** 4-5 timmar
**Prioritet:** KRITISK

Implementera box enrichment service utan workflow integration.

**Deliverables:**
- ✅ `backend/src/services/box_enrichment.py`
- ✅ Unit tests för matching logic
- ✅ Standalone CLI tool för testing

---

### PHASE 2: Backend - OCR Modification
**Tid:** 1 timme
**Prioritet:** KRITISK

Modifiera OCR för att spara raw boxes separat.

**Deliverables:**
- ✅ OCR sparar `ocr_boxes.json` istället för `boxes.json`
- ✅ Backwards compatibility check
- ✅ Tests uppdaterade

---

### PHASE 3: Backend - Workflow Integration
**Tid:** 3-4 timmar
**Prioritet:** HÖG

Integrera AI7 i receipt och creditcard_invoice workflows.

**Deliverables:**
- ✅ AI7 triggas efter AI4 (receipts)
- ✅ AI7 triggas efter AI6 (creditcard_invoice)
- ✅ Error handling och logging
- ✅ Workflow tests

---

### PHASE 4: Database Schema & Tracking (OPTIONAL)
**Tid:** 1-2 timmar
**Prioritet:** LÅGGRADIENT

Lägg till AI7 tracking i database.

**Deliverables:**
- ✅ Database migration script
- ✅ ai7_status, ai7_confidence kolumner
- ✅ Rollback script

---

### PHASE 5: Testing & Validation
**Tid:** 2-3 timmar
**Prioritet:** HÖG

End-to-end testing av hela flödet.

**Deliverables:**
- ✅ Integration tests
- ✅ Test med sample receipts
- ✅ Frontend validation
- ✅ Performance testing

---

### PHASE 6: Migration (OPTIONAL)
**Tid:** 2-3 timmar
**Prioritet:** LÅGGRADIENT

Retroaktiv enrichment av existing receipts.

**Deliverables:**
- ✅ Migration script
- ✅ Batch processing logic
- ✅ Progress tracking
- ✅ Rollback capability

---

### PHASE 7: Documentation & Deployment
**Tid:** 1-2 timmar
**Prioritet:** MEDIUM

Documentation och deployment prep.

**Deliverables:**
- ✅ API documentation update
- ✅ README updates
- ✅ Deployment guide
- ✅ Monitoring setup

---

## DETAILED TASK BREAKDOWN

### PHASE 1: Core Service Implementation

#### Task 1.1: Create box_enrichment.py Base Structure
**Fil:** `backend/src/services/box_enrichment.py`
**Tid:** 30 min

```python
"""
AI7 - Box Enrichment Service

Matches OCR bounding boxes to semantic field identifiers.
Runs AFTER all data extraction is complete (AI3/AI4/AI6).
"""

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BoxEnricher:
    """Main class for box enrichment logic."""

    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)

    def enrich(
        self,
        receipt_id: str,
        receipt_data: Dict[str, Any],
        company_data: Dict[str, Any],
        items_data: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Main enrichment method."""
        pass


def run_box_enrichment(receipt_id: str, storage_dir: str | Path | None = None) -> Dict[str, Any]:
    """
    Main entry point for AI7 box enrichment.

    Args:
        receipt_id: Receipt identifier
        storage_dir: Base storage directory

    Returns:
        Stats about enrichment process
    """
    pass
```

**Verifiering:**
```bash
cd backend
python -c "from src.services.box_enrichment import BoxEnricher; print('OK')"
```

---

#### Task 1.2: Implement Text Normalization
**Fil:** `backend/src/services/box_enrichment.py`
**Tid:** 30 min

```python
import re
import unicodedata


def normalize_text(text: Any) -> str:
    """
    Normalize text for comparison.

    Steps:
    1. Convert to string
    2. Strip whitespace
    3. Lowercase
    4. Remove accents/diacritics
    5. Remove extra spaces
    6. Remove special characters (optional)
    """
    if text is None:
        return ""

    # Convert to string
    text_str = str(text).strip()

    # Lowercase
    text_str = text_str.lower()

    # Remove accents (å→a, ä→a, ö→o)
    text_str = unicodedata.normalize('NFKD', text_str)
    text_str = text_str.encode('ASCII', 'ignore').decode('ASCII')

    # Remove extra whitespace
    text_str = re.sub(r'\s+', ' ', text_str).strip()

    return text_str


def extract_numbers(text: Any) -> List[str]:
    """
    Extract all numbers from text.

    Handles:
    - Integers: 123, 456
    - Decimals: 123.45, 456,78 (both . and , as decimal separator)
    - Dates: 2025-09-08
    """
    if text is None:
        return []

    text_str = str(text)

    # Find all number patterns
    # Matches: 123, 123.45, 123,45, 2025-09-08
    pattern = r'\d+[.,\-]?\d*'
    matches = re.findall(pattern, text_str)

    # Normalize decimal separators
    normalized = []
    for match in matches:
        # Replace comma with dot for consistency
        normalized.append(match.replace(',', '.'))

    return normalized
```

**Unit Tests:**
```python
# tests/unit/test_box_enrichment.py
import pytest
from src.services.box_enrichment import normalize_text, extract_numbers


def test_normalize_text_basic():
    assert normalize_text("BAUHAUS") == "bauhaus"
    assert normalize_text("  Bauhaus  ") == "bauhaus"
    assert normalize_text("Köpa något") == "kopa nagot"


def test_normalize_text_empty():
    assert normalize_text(None) == ""
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""


def test_extract_numbers():
    assert extract_numbers("359.00") == ["359.00"]
    assert extract_numbers("359,00") == ["359.00"]
    assert extract_numbers("2025-09-08") == ["2025", "09", "08"]
    assert extract_numbers("No numbers") == []
```

**Verifiering:**
```bash
cd backend
pytest tests/unit/test_box_enrichment.py -v
```

---

#### Task 1.3: Implement Fuzzy Matching Logic
**Fil:** `backend/src/services/box_enrichment.py`
**Tid:** 1 timme

```python
def is_fuzzy_match(
    ocr_text: str,
    field_value: Any,
    min_length: int = 4,
    match_threshold: float = 0.0
) -> Tuple[bool, float]:
    """
    Check if OCR text fuzzy matches a field value.

    Returns:
        (is_match, confidence) where confidence is 0.0-1.0

    Matching strategies (in order of confidence):
    1. Exact match: confidence = 0.95
    2. Substring match: confidence = 0.80
    3. Prefix match: confidence = 0.70
    4. Numeric match: confidence = 0.85
    """
    ocr_norm = normalize_text(ocr_text)
    value_norm = normalize_text(field_value)

    if not ocr_norm or not value_norm:
        return (False, 0.0)

    # 1. EXACT MATCH
    if ocr_norm == value_norm:
        return (True, 0.95)

    # 2. SUBSTRING MATCH (both directions)
    if len(ocr_norm) >= min_length:
        if ocr_norm in value_norm:
            # OCR text is substring of field value
            # e.g., "Bauhaus" in "Bauhaus AB"
            ratio = len(ocr_norm) / len(value_norm)
            confidence = 0.80 if ratio > 0.5 else 0.70
            return (True, confidence)

        if value_norm in ocr_norm:
            # Field value is substring of OCR text (less common)
            # e.g., "SEK" in "359.00 SEK"
            ratio = len(value_norm) / len(ocr_norm)
            confidence = 0.75 if ratio > 0.5 else 0.65
            return (True, confidence)

    # 3. PREFIX MATCH (for truncated names)
    if len(ocr_norm) >= 6:
        if value_norm.startswith(ocr_norm):
            # e.g., "Handelsban" matches "Handelsbanken"
            ratio = len(ocr_norm) / len(value_norm)
            confidence = 0.70 if ratio > 0.7 else 0.60
            return (True, confidence)

    # 4. NUMERIC MATCH (for amounts, dates)
    ocr_numbers = extract_numbers(ocr_text)
    value_numbers = extract_numbers(field_value)

    if ocr_numbers and value_numbers:
        # Check if all OCR numbers are in field value numbers
        if all(num in value_numbers for num in ocr_numbers):
            confidence = 0.85 if len(ocr_numbers) >= 2 else 0.75
            return (True, confidence)

    # NO MATCH
    return (False, 0.0)


def find_matching_field(
    ocr_text: str,
    receipt_data: Dict[str, Any],
    company_data: Dict[str, Any],
    min_confidence: float = 0.60
) -> Tuple[Optional[str], float]:
    """
    Find which field (if any) matches the OCR text.

    Args:
        ocr_text: Text extracted from OCR
        receipt_data: Receipt fields (gross_amount, purchase_datetime, etc.)
        company_data: Company fields (name, orgnr, address, etc.)
        min_confidence: Minimum confidence threshold

    Returns:
        (field_name, confidence) where field_name is like "receipt.gross_amount"
        or "company.name", or (None, 0.0) if no match
    """
    best_match = (None, 0.0)

    # Try receipt fields first (usually more relevant)
    for field_name, field_value in receipt_data.items():
        if field_value is None:
            continue

        is_match, confidence = is_fuzzy_match(ocr_text, field_value)

        if is_match and confidence > best_match[1]:
            best_match = (f"receipt.{field_name}", confidence)

    # Try company fields if no good match yet
    for field_name, field_value in company_data.items():
        if field_value is None:
            continue

        is_match, confidence = is_fuzzy_match(ocr_text, field_value)

        if is_match and confidence > best_match[1]:
            best_match = (f"company.{field_name}", confidence)

    # Return only if above threshold
    if best_match[1] >= min_confidence:
        return best_match

    return (None, 0.0)
```

**Unit Tests:**
```python
def test_is_fuzzy_match_exact():
    is_match, conf = is_fuzzy_match("BAUHAUS", "Bauhaus")
    assert is_match is True
    assert conf == 0.95


def test_is_fuzzy_match_substring():
    is_match, conf = is_fuzzy_match("Bauhaus", "Bauhaus AB")
    assert is_match is True
    assert conf >= 0.70


def test_is_fuzzy_match_prefix():
    is_match, conf = is_fuzzy_match("Handelsban", "Handelsbanken")
    assert is_match is True
    assert conf >= 0.60


def test_is_fuzzy_match_numeric():
    is_match, conf = is_fuzzy_match("359.00", "359.00 kr")
    assert is_match is True
    assert conf >= 0.75


def test_find_matching_field():
    receipt_data = {
        "gross_amount": 359.00,
        "merchant_name": "BAUHAUS"
    }
    company_data = {
        "name": "Bauhaus AB",
        "orgnr": "969630-6944"
    }

    # Should match company.name (exact match on normalized text)
    field, conf = find_matching_field("BAUHAUS", receipt_data, company_data)
    assert field == "company.name" or field == "receipt.merchant_name"
    assert conf >= 0.75
```

---

#### Task 1.4: Implement Data Loading Helpers
**Fil:** `backend/src/services/box_enrichment.py`
**Tid:** 1 timme

```python
def _load_receipt_data(receipt_id: str) -> Dict[str, Any]:
    """
    Load receipt data from database.

    Returns dict with fields:
    - gross_amount, net_amount
    - gross_amount_sek, net_amount_sek
    - purchase_datetime, purchase_date
    - receipt_number
    - payment_type, expense_type
    - credit_card_* fields
    - currency, exchange_rate
    - total_vat_25, total_vat_12, total_vat_6
    """
    from services.db.connection import db_cursor

    if db_cursor is None:
        logger.warning("DB not available for receipt data loading")
        return {}

    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    gross_amount, net_amount,
                    gross_amount_sek, net_amount_sek,
                    purchase_datetime, purchase_date,
                    receipt_number,
                    payment_type, expense_type,
                    credit_card_number, credit_card_last_4_digits,
                    credit_card_type, credit_card_brand_full, credit_card_brand_short,
                    credit_card_payment_variant, credit_card_token, credit_card_entering_mode,
                    currency, exchange_rate,
                    total_vat_25, total_vat_12, total_vat_6
                FROM unified_files
                WHERE id = %s
            """, (receipt_id,))

            row = cur.fetchone()
            if not row:
                logger.warning(f"Receipt {receipt_id} not found in database")
                return {}

            # Build dict from row
            columns = [desc[0] for desc in cur.description]
            data = dict(zip(columns, row))

            # Remove None values to avoid unnecessary matching attempts
            return {k: v for k, v in data.items() if v is not None}

    except Exception as e:
        logger.error(f"Failed to load receipt data for {receipt_id}: {e}")
        return {}


def _load_company_data(receipt_id: str) -> Dict[str, Any]:
    """
    Load company data from database.

    Returns dict with fields:
    - name, orgnr
    - address, address2, zip, city, country
    - phone, www, email
    """
    from services.db.connection import db_cursor

    if db_cursor is None:
        return {}

    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    c.name, c.orgnr,
                    c.address, c.address2, c.zip, c.city, c.country,
                    c.phone, c.www, c.email
                FROM companies c
                JOIN unified_files u ON u.company_id = c.id
                WHERE u.id = %s
            """, (receipt_id,))

            row = cur.fetchone()
            if not row:
                logger.info(f"No company found for receipt {receipt_id}")
                return {}

            columns = [desc[0] for desc in cur.description]
            data = dict(zip(columns, row))

            return {k: v for k, v in data.items() if v is not None}

    except Exception as e:
        logger.error(f"Failed to load company data for {receipt_id}: {e}")
        return {}


def _load_items_data(receipt_id: str) -> List[Dict[str, Any]]:
    """
    Load line items from database.

    Returns list of dicts with fields:
    - article_id, name
    - number (quantity)
    - item_price_ex_vat, item_price_inc_vat
    - item_total_price_ex_vat, item_total_price_inc_vat
    - currency, vat, vat_percentage
    """
    from services.db.connection import db_cursor

    if db_cursor is None:
        return []

    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    article_id, name, number,
                    item_price_ex_vat, item_price_inc_vat,
                    item_total_price_ex_vat, item_total_price_inc_vat,
                    currency, vat, vat_percentage
                FROM receipt_items
                WHERE main_id = %s
                ORDER BY id
            """, (receipt_id,))

            rows = cur.fetchall()
            if not rows:
                return []

            columns = [desc[0] for desc in cur.description]
            items = []
            for row in rows:
                data = dict(zip(columns, row))
                # Remove None values
                items.append({k: v for k, v in data.items() if v is not None})

            return items

    except Exception as e:
        logger.error(f"Failed to load items data for {receipt_id}: {e}")
        return []
```

**Tests:**
```python
def test_load_receipt_data(sample_receipt_id):
    data = _load_receipt_data(sample_receipt_id)
    assert isinstance(data, dict)
    assert "gross_amount" in data or len(data) == 0  # Empty if not found


def test_load_company_data(sample_receipt_id):
    data = _load_company_data(sample_receipt_id)
    assert isinstance(data, dict)
    # May be empty if no company matched


def test_load_items_data(sample_receipt_id):
    items = _load_items_data(sample_receipt_id)
    assert isinstance(items, list)
```

---

#### Task 1.5: Implement Main Enrichment Logic
**Fil:** `backend/src/services/box_enrichment.py`
**Tid:** 1.5 timmar

```python
def enrich_boxes(
    receipt_id: str,
    receipt_data: Dict[str, Any],
    company_data: Dict[str, Any],
    items_data: List[Dict[str, Any]],
    storage_dir: str | Path,
    min_confidence: float = 0.60
) -> List[Dict[str, Any]]:
    """
    Enrich OCR boxes with semantic field names.

    Args:
        receipt_id: Receipt identifier
        receipt_data: Extracted receipt fields
        company_data: Company/merchant data
        items_data: Line items
        storage_dir: Base storage directory
        min_confidence: Minimum confidence for matching

    Returns:
        List of enriched boxes with semantic "field" identifiers
    """
    base_path = Path(storage_dir)
    receipt_dir = base_path / receipt_id

    # Load raw OCR boxes
    ocr_boxes_path = receipt_dir / "ocr_boxes.json"
    if not ocr_boxes_path.exists():
        logger.warning(f"No OCR boxes found for {receipt_id} at {ocr_boxes_path}")
        return []

    try:
        with open(ocr_boxes_path, 'r', encoding='utf-8') as f:
            ocr_boxes = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load OCR boxes for {receipt_id}: {e}")
        return []

    if not isinstance(ocr_boxes, list):
        logger.warning(f"OCR boxes not a list for {receipt_id}")
        return []

    enriched_boxes = []
    match_stats = {
        'total': len(ocr_boxes),
        'matched': 0,
        'unmatched': 0,
        'low_confidence': 0
    }

    for box in ocr_boxes:
        ocr_text = box.get("field", "")  # Original OCR text

        if not ocr_text:
            continue

        # Find matching semantic field
        matched_field, match_confidence = find_matching_field(
            ocr_text,
            receipt_data,
            company_data,
            min_confidence=min_confidence
        )

        # Build enriched box
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
            match_stats['matched'] += 1

            logger.debug(
                f"Matched '{ocr_text}' → {matched_field} "
                f"(confidence: {match_confidence:.2f})"
            )
        else:
            # Keep original OCR text if no match
            # Frontend can still use ocr_text for debugging
            enriched_box["field"] = ocr_text
            enriched_box["match_confidence"] = 0.0
            match_stats['unmatched'] += 1

            logger.debug(f"No match for '{ocr_text}'")

        enriched_boxes.append(enriched_box)

    # Log stats
    logger.info(
        f"Box enrichment for {receipt_id}: "
        f"{match_stats['matched']}/{match_stats['total']} matched "
        f"({match_stats['matched']/match_stats['total']*100:.1f}%)"
    )

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
        with open(boxes_path, 'w', encoding='utf-8') as f:
            json.dump(enriched_boxes, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(enriched_boxes)} enriched boxes to {boxes_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save enriched boxes for {receipt_id}: {e}")
        return False


def run_box_enrichment(
    receipt_id: str,
    storage_dir: str | Path | None = None
) -> Dict[str, Any]:
    """
    Main entry point for AI7 box enrichment.

    Should be called AFTER AI4 (for receipts) or AI6 (for creditcard_invoice).

    Returns:
        Stats about enrichment process:
        {
            "success": bool,
            "total_boxes": int,
            "matched_boxes": int,
            "unmatched_boxes": int,
            "match_rate": float (0.0-1.0)
        }
    """
    import os

    base = storage_dir or os.getenv("STORAGE_DIR", "/data/storage")

    logger.info(f"Starting box enrichment for receipt {receipt_id}")

    # Load extracted data
    receipt_data = _load_receipt_data(receipt_id)
    company_data = _load_company_data(receipt_id)
    items_data = _load_items_data(receipt_id)

    if not receipt_data and not company_data:
        logger.warning(
            f"No extracted data found for {receipt_id}. "
            "Cannot enrich boxes without data."
        )
        return {
            "success": False,
            "error": "no_extracted_data",
            "total_boxes": 0,
            "matched_boxes": 0,
            "unmatched_boxes": 0,
            "match_rate": 0.0,
        }

    # Enrich boxes
    try:
        enriched_boxes = enrich_boxes(
            receipt_id,
            receipt_data,
            company_data,
            items_data,
            base,
        )
    except Exception as e:
        logger.error(f"Box enrichment failed for {receipt_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "total_boxes": 0,
            "matched_boxes": 0,
            "unmatched_boxes": 0,
            "match_rate": 0.0,
        }

    if not enriched_boxes:
        logger.warning(f"No boxes to enrich for {receipt_id}")
        return {
            "success": True,
            "total_boxes": 0,
            "matched_boxes": 0,
            "unmatched_boxes": 0,
            "match_rate": 0.0,
        }

    # Save enriched boxes
    success = save_enriched_boxes(receipt_id, enriched_boxes, base)

    # Calculate stats
    matched_count = sum(
        1 for box in enriched_boxes
        if box.get("match_confidence", 0) >= 0.60
    )
    unmatched_count = len(enriched_boxes) - matched_count
    match_rate = matched_count / len(enriched_boxes) if enriched_boxes else 0.0

    return {
        "success": success,
        "total_boxes": len(enriched_boxes),
        "matched_boxes": matched_count,
        "unmatched_boxes": unmatched_count,
        "match_rate": match_rate,
    }
```

**Integration Test:**
```python
def test_run_box_enrichment_full_flow(sample_receipt_with_ocr_boxes):
    """Test complete enrichment flow with real receipt."""
    receipt_id = sample_receipt_with_ocr_boxes

    result = run_box_enrichment(receipt_id)

    assert result["success"] is True
    assert result["total_boxes"] > 0
    assert result["match_rate"] >= 0.0

    # Verify boxes.json was created
    boxes_path = Path(os.getenv("STORAGE_DIR")) / receipt_id / "boxes.json"
    assert boxes_path.exists()

    # Verify structure
    with open(boxes_path) as f:
        boxes = json.load(f)

    assert isinstance(boxes, list)
    assert len(boxes) == result["total_boxes"]

    # Check first box has required fields
    if boxes:
        box = boxes[0]
        assert "field" in box
        assert "ocr_text" in box
        assert "confidence" in box
        assert "match_confidence" in box
        assert "x" in box and "y" in box
        assert "w" in box and "h" in box
```

---

#### Task 1.6: Create CLI Tool for Testing
**Fil:** `backend/src/tools/enrich_boxes_cli.py`
**Tid:** 30 min

```python
#!/usr/bin/env python3
"""
CLI tool for testing box enrichment.

Usage:
    python -m src.tools.enrich_boxes_cli <receipt_id>
    python -m src.tools.enrich_boxes_cli --batch --all
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.box_enrichment import run_box_enrichment

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def enrich_single(receipt_id: str, storage_dir: str | None = None) -> None:
    """Enrich boxes for a single receipt."""
    print(f"\n{'='*60}")
    print(f"Enriching boxes for receipt: {receipt_id}")
    print(f"{'='*60}\n")

    result = run_box_enrichment(receipt_id, storage_dir)

    print("\nResults:")
    print(f"  Success: {result['success']}")
    print(f"  Total boxes: {result['total_boxes']}")
    print(f"  Matched boxes: {result['matched_boxes']}")
    print(f"  Unmatched boxes: {result['unmatched_boxes']}")
    print(f"  Match rate: {result['match_rate']:.1%}")

    if result['success'] and result['total_boxes'] > 0:
        # Show some examples
        import os
        boxes_path = Path(storage_dir or os.getenv("STORAGE_DIR", "/data/storage")) / receipt_id / "boxes.json"

        if boxes_path.exists():
            with open(boxes_path) as f:
                boxes = json.load(f)

            print("\nExample matches (first 5):")
            for i, box in enumerate(boxes[:5], 1):
                field = box.get("field", "")
                ocr_text = box.get("ocr_text", "")
                match_conf = box.get("match_confidence", 0)

                if match_conf > 0:
                    print(f"  {i}. '{ocr_text}' → {field} (confidence: {match_conf:.2f})")
                else:
                    print(f"  {i}. '{ocr_text}' → NO MATCH")


def enrich_batch(storage_dir: str | None = None, limit: int | None = None) -> None:
    """Enrich boxes for all receipts with AI4 completed."""
    from src.services.db.connection import db_cursor

    if db_cursor is None:
        print("ERROR: Database not available")
        return

    with db_cursor() as cur:
        cur.execute("""
            SELECT id FROM unified_files
            WHERE ai4_status = 'completed'
            AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit or 1000,))

        receipt_ids = [row[0] for row in cur.fetchall()]

    print(f"\nFound {len(receipt_ids)} receipts to enrich")

    success_count = 0
    error_count = 0

    for i, receipt_id in enumerate(receipt_ids, 1):
        print(f"\n[{i}/{len(receipt_ids)}] Processing {receipt_id}...")

        try:
            result = run_box_enrichment(receipt_id, storage_dir)
            if result['success']:
                success_count += 1
                print(f"  ✓ Success: {result['matched_boxes']}/{result['total_boxes']} matched")
            else:
                error_count += 1
                print(f"  ✗ Failed: {result.get('error', 'unknown error')}")
        except Exception as e:
            error_count += 1
            print(f"  ✗ Error: {e}")

    print(f"\n{'='*60}")
    print(f"Batch enrichment complete:")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Box enrichment CLI tool")
    parser.add_argument("receipt_id", nargs="?", help="Receipt ID to enrich")
    parser.add_argument("--batch", action="store_true", help="Batch mode")
    parser.add_argument("--all", action="store_true", help="Process all receipts (use with --batch)")
    parser.add_argument("--limit", type=int, default=100, help="Limit for batch mode (default: 100)")
    parser.add_argument("--storage-dir", help="Storage directory override")

    args = parser.parse_args()

    if args.batch:
        limit = None if args.all else args.limit
        enrich_batch(args.storage_dir, limit)
    elif args.receipt_id:
        enrich_single(args.receipt_id, args.storage_dir)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Test single receipt
cd backend
python -m src.tools.enrich_boxes_cli 933b749c-d31e-46f8-b58f-4dfdfcdd74b6

# Batch enrich (first 10)
python -m src.tools.enrich_boxes_cli --batch --limit 10

# Enrich all
python -m src.tools.enrich_boxes_cli --batch --all
```

---

### PHASE 2: OCR Modification

#### Task 2.1: Modify OCR to Save Raw Boxes
**Fil:** `backend/src/services/ocr.py`
**Tid:** 30 min

**Nuvarande kod (rad 28-31):**
```python
def _write_boxes(base: str | Path, receipt_id: str, boxes: List[Dict[str, Any]]) -> None:
    root = _receipt_dir(base, receipt_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "boxes.json").write_text(json.dumps(boxes, ensure_ascii=False, indent=2), encoding="utf-8")
```

**Ändra till:**
```python
def _write_boxes(base: str | Path, receipt_id: str, boxes: List[Dict[str, Any]]) -> None:
    """
    Save RAW OCR boxes (before enrichment).

    Saves to ocr_boxes.json instead of boxes.json.
    boxes.json will be created later by AI7 box enrichment.
    """
    root = _receipt_dir(base, receipt_id)
    root.mkdir(parents=True, exist_ok=True)

    # Save as ocr_boxes.json (raw OCR data)
    ocr_boxes_path = root / "ocr_boxes.json"
    ocr_boxes_path.write_text(
        json.dumps(boxes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    logger.info(f"Saved {len(boxes)} raw OCR boxes to {ocr_boxes_path}")
```

**Verifiering:**
```bash
# After OCR runs
ls /data/storage/<receipt_id>/
# Should see: ocr_boxes.json (NOT boxes.json)
```

---

#### Task 2.2: Update OCR Tests
**Fil:** `backend/tests/unit/test_ocr_service.py` och `backend/tests/integration/test_receipt_images_and_boxes.py`
**Tid:** 30 min

```python
# Update test expectations
def test_ocr_creates_ocr_boxes_file(sample_receipt_with_image):
    """Test that OCR creates ocr_boxes.json (not boxes.json)."""
    from src.services.ocr import run_ocr

    result = run_ocr(sample_receipt_with_image)

    # Check ocr_boxes.json exists
    ocr_boxes_path = Path(os.getenv("STORAGE_DIR")) / sample_receipt_with_image / "ocr_boxes.json"
    assert ocr_boxes_path.exists()

    # Check boxes.json does NOT exist yet (will be created by AI7)
    boxes_path = Path(os.getenv("STORAGE_DIR")) / sample_receipt_with_image / "boxes.json"
    assert not boxes_path.exists()
```

---

### PHASE 3: Workflow Integration

#### Task 3.1: Add AI7 Trigger After AI4 (Receipts)
**Fil:** `backend/src/api/ai_processing.py` eller `backend/src/tasks.py`
**Tid:** 1 timme

**Hitta var AI4 completion hanteras:**
```bash
cd backend
grep -r "ai4.*completed\|AI4.*success" src/
```

**Lägg till AI7 trigger:**
```python
# I funktionen som hanterar AI4 completion
def handle_ai4_completion(file_id: str, ai4_result: dict):
    """Handle AI4 completion and trigger AI7."""

    # ... existing AI4 logic ...

    # Update AI4 status
    _set_ai_stage(cursor, file_id, "AI4", ai4_confidence, success=ai4_success)

    # NEW: Trigger AI7 box enrichment after successful AI4
    if ai4_success:
        logger.info(f"Triggering AI7 box enrichment for {file_id} after AI4 success")

        try:
            from services.box_enrichment import run_box_enrichment

            box_stats = run_box_enrichment(file_id)

            if box_stats["success"]:
                logger.info(
                    f"AI7 box enrichment completed for {file_id}: "
                    f"{box_stats['matched_boxes']}/{box_stats['total_boxes']} matched "
                    f"({box_stats['match_rate']:.1%})"
                )

                # Update AI7 status (if DB schema updated)
                if 'ai7_status' in get_table_columns('unified_files'):
                    _set_ai_stage(
                        cursor,
                        file_id,
                        "AI7",
                        box_stats['match_rate'],
                        success=True
                    )
            else:
                logger.warning(f"AI7 box enrichment failed for {file_id}: {box_stats.get('error')}")

                # Still mark as attempted
                if 'ai7_status' in get_table_columns('unified_files'):
                    _set_ai_stage(cursor, file_id, "AI7", 0.0, success=False)

        except Exception as e:
            logger.error(f"AI7 box enrichment error for {file_id}: {e}", exc_info=True)

            # Don't fail the whole pipeline - box enrichment is optional
            # Mark as error but continue
            if 'ai7_status' in get_table_columns('unified_files'):
                _set_ai_stage(cursor, file_id, "AI7", 0.0, success=False)
```

---

#### Task 3.2: Add AI7 Trigger After AI6 (Creditcard Invoice)
**Fil:** `backend/src/api/ai_processing.py` eller task handler för AI6
**Tid:** 30 min

```python
def handle_ai6_completion(file_id: str, ai6_result: dict):
    """Handle AI6 completion and trigger AI7."""

    # ... existing AI6 logic ...

    # NEW: Trigger AI7 after successful AI6
    if ai6_success:
        logger.info(f"Triggering AI7 box enrichment for {file_id} after AI6 success")

        try:
            from services.box_enrichment import run_box_enrichment

            box_stats = run_box_enrichment(file_id)

            # Same logic as AI4 handler above
            # ...

        except Exception as e:
            logger.error(f"AI7 box enrichment error for {file_id}: {e}", exc_info=True)
```

---

#### Task 3.3: Add Error Handling & Logging
**Tid:** 30 min

```python
# Add retry logic for transient failures
from functools import wraps
import time


def retry_on_failure(max_attempts=3, delay=1.0):
    """Decorator for retrying failed operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
                        raise
            return None
        return wrapper
    return decorator


@retry_on_failure(max_attempts=2, delay=0.5)
def run_box_enrichment_with_retry(receipt_id: str, storage_dir: str | Path | None = None):
    """Box enrichment with retry logic."""
    return run_box_enrichment(receipt_id, storage_dir)
```

---

### PHASE 4: Database Schema (OPTIONAL)

#### Task 4.1: Create Migration Script
**Fil:** `backend/migrations/add_ai7_tracking.sql`
**Tid:** 30 min

```sql
-- Migration: Add AI7 box enrichment tracking
-- Date: 2025-10-19
-- Description: Adds columns to track AI7 (box enrichment) status and confidence

-- Add AI7 tracking columns
ALTER TABLE unified_files
ADD COLUMN IF NOT EXISTS ai7_status VARCHAR(32) DEFAULT NULL
    COMMENT 'AI7 box enrichment status: completed, error, pending',
ADD COLUMN IF NOT EXISTS ai7_confidence DECIMAL(5,4) DEFAULT NULL
    COMMENT 'AI7 match rate (0.0-1.0) indicating percentage of boxes matched',
ADD COLUMN IF NOT EXISTS ai7_timestamp TIMESTAMP DEFAULT NULL
    COMMENT 'When AI7 box enrichment completed';

-- Add index for querying AI7 status
CREATE INDEX IF NOT EXISTS idx_ai7_status ON unified_files(ai7_status);

-- Add comment to table
ALTER TABLE unified_files COMMENT = 'Updated with AI7 tracking columns for box enrichment (2025-10-19)';
```

**Apply migration:**
```bash
cd backend
mysql -u root -p mind < migrations/add_ai7_tracking.sql
```

---

#### Task 4.2: Create Rollback Script
**Fil:** `backend/migrations/rollback_ai7_tracking.sql`
**Tid:** 15 min

```sql
-- Rollback: Remove AI7 tracking columns
-- Date: 2025-10-19

-- Remove index
DROP INDEX IF EXISTS idx_ai7_status ON unified_files;

-- Remove columns
ALTER TABLE unified_files
DROP COLUMN IF EXISTS ai7_timestamp,
DROP COLUMN IF EXISTS ai7_confidence,
DROP COLUMN IF EXISTS ai7_status;
```

---

#### Task 4.3: Update _set_ai_stage Function
**Fil:** `backend/src/api/ai_processing.py` eller där _set_ai_stage finns
**Tid:** 30 min

```python
def _set_ai_stage(
    cursor,
    file_id: str,
    stage: str,  # "AI1", "AI2", ..., "AI7"
    confidence: float | None = None,
    success: bool = True,
    **kwargs
):
    """
    Update AI stage status in database.

    Now supports AI7 tracking.
    """
    if stage == "AI7":
        status = "completed" if success else "error"

        cursor.execute("""
            UPDATE unified_files
            SET ai7_status = %s,
                ai7_confidence = %s,
                ai7_timestamp = NOW()
            WHERE id = %s
        """, (status, confidence, file_id))

        logger.info(f"Set AI7 status for {file_id}: {status} (confidence: {confidence})")

    else:
        # Existing logic for AI1-AI6
        # ...
        pass
```

---

### PHASE 5: Testing & Validation

#### Task 5.1: Unit Tests
**Fil:** `backend/tests/unit/test_box_enrichment.py`
**Tid:** 1 timme

```python
import pytest
import json
from pathlib import Path
from src.services.box_enrichment import (
    normalize_text,
    extract_numbers,
    is_fuzzy_match,
    find_matching_field,
    enrich_boxes,
    run_box_enrichment
)


class TestTextNormalization:
    def test_basic_normalization(self):
        assert normalize_text("BAUHAUS") == "bauhaus"
        assert normalize_text("  Bauhaus  ") == "bauhaus"

    def test_accent_removal(self):
        assert normalize_text("Köpa något") == "kopa nagot"
        assert normalize_text("Fågelmörker") == "fagelmorker"

    def test_empty_input(self):
        assert normalize_text(None) == ""
        assert normalize_text("") == ""
        assert normalize_text("   ") == ""

    def test_numbers(self):
        assert normalize_text("123.45") == "123.45"
        assert normalize_text("2025-09-08") == "2025-09-08"


class TestNumberExtraction:
    def test_decimal_numbers(self):
        assert extract_numbers("359.00") == ["359.00"]
        assert extract_numbers("359,00") == ["359.00"]  # Comma converted

    def test_dates(self):
        numbers = extract_numbers("2025-09-08")
        assert "2025" in numbers
        assert "09" in numbers
        assert "08" in numbers

    def test_no_numbers(self):
        assert extract_numbers("BAUHAUS") == []
        assert extract_numbers("No numbers here") == []


class TestFuzzyMatching:
    def test_exact_match(self):
        is_match, conf = is_fuzzy_match("BAUHAUS", "Bauhaus")
        assert is_match is True
        assert conf == 0.95

    def test_substring_match(self):
        is_match, conf = is_fuzzy_match("Bauhaus", "Bauhaus AB")
        assert is_match is True
        assert conf >= 0.70

    def test_prefix_match(self):
        is_match, conf = is_fuzzy_match("Handelsban", "Handelsbanken")
        assert is_match is True
        assert conf >= 0.60

    def test_numeric_match(self):
        is_match, conf = is_fuzzy_match("359.00", "359.00 kr")
        assert is_match is True
        assert conf >= 0.75

    def test_no_match(self):
        is_match, conf = is_fuzzy_match("BAUHAUS", "HORNBACH")
        assert is_match is False
        assert conf == 0.0


class TestFieldMatching:
    def test_find_receipt_field(self):
        receipt_data = {
            "gross_amount": "359.00",
            "merchant_name": "BAUHAUS"
        }
        company_data = {}

        field, conf = find_matching_field("359.00", receipt_data, company_data)
        assert field == "receipt.gross_amount"
        assert conf >= 0.75

    def test_find_company_field(self):
        receipt_data = {}
        company_data = {
            "name": "Bauhaus AB",
            "orgnr": "969630-6944"
        }

        field, conf = find_matching_field("BAUHAUS", receipt_data, company_data)
        assert field == "company.name"
        assert conf >= 0.70

    def test_no_match(self):
        receipt_data = {"gross_amount": "359.00"}
        company_data = {"name": "BAUHAUS"}

        field, conf = find_matching_field("HORNBACH", receipt_data, company_data)
        assert field is None
        assert conf == 0.0


@pytest.fixture
def sample_ocr_boxes(tmp_path):
    """Create sample OCR boxes file."""
    receipt_id = "test-receipt-123"
    receipt_dir = tmp_path / receipt_id
    receipt_dir.mkdir()

    ocr_boxes = [
        {
            "field": "BAUHAUS",
            "confidence": 0.99,
            "x": 0.7,
            "y": 0.55,
            "w": 0.18,
            "h": 0.06
        },
        {
            "field": "359.00",
            "confidence": 0.98,
            "x": 0.75,
            "y": 0.85,
            "w": 0.15,
            "h": 0.05
        }
    ]

    with open(receipt_dir / "ocr_boxes.json", 'w') as f:
        json.dump(ocr_boxes, f)

    return receipt_id, tmp_path


class TestEnrichment:
    def test_enrich_boxes(self, sample_ocr_boxes):
        receipt_id, storage_dir = sample_ocr_boxes

        receipt_data = {"gross_amount": 359.00}
        company_data = {"name": "BAUHAUS AB"}
        items_data = []

        enriched = enrich_boxes(
            receipt_id,
            receipt_data,
            company_data,
            items_data,
            storage_dir
        )

        assert len(enriched) == 2

        # Check first box (BAUHAUS)
        box1 = enriched[0]
        assert box1["ocr_text"] == "BAUHAUS"
        assert box1["field"] == "company.name"
        assert box1["match_confidence"] >= 0.60

        # Check second box (359.00)
        box2 = enriched[1]
        assert box2["ocr_text"] == "359.00"
        assert box2["field"] == "receipt.gross_amount"
        assert box2["match_confidence"] >= 0.60
```

**Run tests:**
```bash
cd backend
pytest tests/unit/test_box_enrichment.py -v
```

---

#### Task 5.2: Integration Tests
**Fil:** `backend/tests/integration/test_ai7_workflow.py`
**Tid:** 1 timme

```python
import pytest
import json
from pathlib import Path
from src.services.ocr import run_ocr
from src.services.box_enrichment import run_box_enrichment


@pytest.mark.integration
class TestAI7Workflow:
    """Test complete workflow: OCR → AI3 → AI4 → AI7."""

    def test_ocr_creates_raw_boxes(self, sample_receipt_image):
        """Test that OCR creates ocr_boxes.json."""
        receipt_id = sample_receipt_image

        # Run OCR
        ocr_result = run_ocr(receipt_id)

        # Verify ocr_boxes.json exists
        storage_dir = Path(os.getenv("STORAGE_DIR"))
        ocr_boxes_path = storage_dir / receipt_id / "ocr_boxes.json"
        assert ocr_boxes_path.exists()

        # Verify boxes.json does NOT exist yet
        boxes_path = storage_dir / receipt_id / "boxes.json"
        assert not boxes_path.exists()

    def test_ai7_enriches_boxes_after_ai4(self, sample_receipt_with_ai4_completed):
        """Test that AI7 runs after AI4 and creates boxes.json."""
        receipt_id = sample_receipt_with_ai4_completed

        # Run AI7 enrichment
        result = run_box_enrichment(receipt_id)

        assert result["success"] is True
        assert result["total_boxes"] > 0

        # Verify boxes.json exists now
        storage_dir = Path(os.getenv("STORAGE_DIR"))
        boxes_path = storage_dir / receipt_id / "boxes.json"
        assert boxes_path.exists()

        # Verify structure
        with open(boxes_path) as f:
            boxes = json.load(f)

        assert isinstance(boxes, list)

        # Check first box has semantic field
        if boxes:
            box = boxes[0]
            assert "field" in box
            assert "ocr_text" in box
            assert "match_confidence" in box

            # Should have semantic name (not just OCR text)
            # Either "receipt.X" or "company.X" or unmatched OCR text
            field = box["field"]
            is_semantic = field.startswith("receipt.") or field.startswith("company.")
            is_unmatched = box["match_confidence"] == 0.0

            # At least some boxes should be matched
            assert is_semantic or is_unmatched

    def test_api_returns_enriched_boxes(self, sample_receipt_with_ai7_completed):
        """Test that /api/receipts/:id/modal returns enriched boxes."""
        from src.api.receipts import get_receipt_modal

        receipt_id = sample_receipt_with_ai7_completed

        response, status = get_receipt_modal(receipt_id)

        assert status == 200
        data = response.get_json()

        assert "boxes" in data
        boxes = data["boxes"]

        assert isinstance(boxes, list)

        if boxes:
            box = boxes[0]
            # Should have enriched structure
            assert "field" in box
            assert "ocr_text" in box or "field" in box
```

---

#### Task 5.3: Frontend Validation
**Tid:** 1 timme

**Manual test:**
1. Kör AI7 för ett test-kvitto
2. Öppna frontend (http://localhost:5169)
3. Gå till Process → Förhandsgranska kvitto
4. Verifiera:
   - Overlays visas
   - Hover över field → overlay blir gul
   - Hover över overlay → field blir gul

**Playwright test (optional):**
```typescript
// web/tests/overlay-matching.spec.ts
test('Field hover highlights matching overlay', async ({ page }) => {
  await page.goto('/process');

  // Open receipt modal
  await page.getByRole('button', { name: /Förhandsgranska kvitto/i }).first().click();

  // Wait for modal
  await page.waitForSelector('.receipt-modal-overlay');

  // Hover over a field (e.g., Företag)
  const companyField = page.locator('.receipt-modal-field').filter({ hasText: 'Företag' });
  await companyField.hover();

  // Check that corresponding overlay is highlighted
  const highlightedOverlay = page.locator('.receipt-modal-overlay.highlighted');
  await expect(highlightedOverlay).toBeVisible();

  // Leave hover
  await page.mouse.move(0, 0);

  // Check that highlight is removed
  await expect(highlightedOverlay).not.toBeVisible();
});
```

---

#### Task 5.4: Performance Testing
**Tid:** 30 min

```python
import time
from src.services.box_enrichment import run_box_enrichment


def test_enrichment_performance():
    """Test that enrichment completes in reasonable time."""
    receipt_id = "sample-receipt-with-many-boxes"

    start = time.time()
    result = run_box_enrichment(receipt_id)
    duration = time.time() - start

    assert result["success"] is True
    assert duration < 5.0  # Should complete in less than 5 seconds

    print(f"Enriched {result['total_boxes']} boxes in {duration:.2f}s")
    print(f"Match rate: {result['match_rate']:.1%}")


def test_batch_performance():
    """Test batch enrichment performance."""
    receipt_ids = get_sample_receipt_ids(count=50)

    start = time.time()
    results = []

    for receipt_id in receipt_ids:
        result = run_box_enrichment(receipt_id)
        results.append(result)

    duration = time.time() - start

    success_rate = sum(1 for r in results if r["success"]) / len(results)
    avg_match_rate = sum(r["match_rate"] for r in results) / len(results)

    print(f"\nBatch performance:")
    print(f"  Receipts: {len(receipt_ids)}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Avg per receipt: {duration/len(receipt_ids):.2f}s")
    print(f"  Success rate: {success_rate:.1%}")
    print(f"  Avg match rate: {avg_match_rate:.1%}")

    assert duration / len(receipt_ids) < 2.0  # Less than 2s per receipt
```

---

### PHASE 6: Migration (OPTIONAL)

#### Task 6.1: Create Migration Script
**Fil:** `backend/src/tools/migrate_existing_boxes.py`
**Tid:** 1 timme

```python
#!/usr/bin/env python3
"""
Migrate existing receipts to enriched boxes.

This script retroactively runs AI7 box enrichment for receipts that:
- Have AI4 completed (receipts) or AI6 completed (creditcard_invoice)
- Do NOT have AI7 completed yet
- Have ocr_boxes.json OR boxes.json (will rename boxes.json → ocr_boxes.json)

Usage:
    python -m src.tools.migrate_existing_boxes --dry-run
    python -m src.tools.migrate_existing_boxes --limit 100
    python -m src.tools.migrate_existing_boxes --all
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.box_enrichment import run_box_enrichment
from src.services.db.connection import db_cursor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_receipts_to_migrate(limit: int | None = None) -> list[str]:
    """Get list of receipts that need box enrichment."""
    if db_cursor is None:
        logger.error("Database not available")
        return []

    with db_cursor() as cur:
        # Check if ai7_status column exists
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'unified_files'
            AND COLUMN_NAME = 'ai7_status'
        """)
        has_ai7_column = cur.fetchone()[0] > 0

        if has_ai7_column:
            # Use AI7 status if available
            sql = """
                SELECT id FROM unified_files
                WHERE (ai4_status = 'completed' OR ai6_status = 'completed')
                AND (ai7_status IS NULL OR ai7_status = 'error')
                AND deleted_at IS NULL
                ORDER BY created_at DESC
            """
        else:
            # Fallback: just check AI4/AI6
            sql = """
                SELECT id FROM unified_files
                WHERE (ai4_status = 'completed' OR ai6_status = 'completed')
                AND deleted_at IS NULL
                ORDER BY created_at DESC
            """

        if limit:
            sql += f" LIMIT {limit}"

        cur.execute(sql)
        return [row[0] for row in cur.fetchall()]


def prepare_receipt(receipt_id: str, storage_dir: Path) -> bool:
    """
    Prepare receipt for enrichment.

    If boxes.json exists but ocr_boxes.json doesn't, rename it.
    """
    receipt_dir = storage_dir / receipt_id

    if not receipt_dir.exists():
        logger.warning(f"Receipt directory not found: {receipt_dir}")
        return False

    boxes_path = receipt_dir / "boxes.json"
    ocr_boxes_path = receipt_dir / "ocr_boxes.json"

    # If ocr_boxes.json exists, we're good
    if ocr_boxes_path.exists():
        return True

    # If boxes.json exists, rename it to ocr_boxes.json
    if boxes_path.exists():
        logger.info(f"Renaming boxes.json → ocr_boxes.json for {receipt_id}")
        boxes_path.rename(ocr_boxes_path)
        return True

    logger.warning(f"No boxes files found for {receipt_id}")
    return False


def migrate_receipt(receipt_id: str, dry_run: bool = False) -> dict:
    """Migrate a single receipt."""
    storage_dir = Path(os.getenv("STORAGE_DIR", "/data/storage"))

    # Prepare receipt
    if not prepare_receipt(receipt_id, storage_dir):
        return {
            "receipt_id": receipt_id,
            "success": False,
            "error": "no_boxes_file"
        }

    if dry_run:
        logger.info(f"[DRY RUN] Would enrich {receipt_id}")
        return {
            "receipt_id": receipt_id,
            "success": True,
            "dry_run": True
        }

    # Run enrichment
    try:
        result = run_box_enrichment(receipt_id)
        return {
            "receipt_id": receipt_id,
            **result
        }
    except Exception as e:
        logger.error(f"Failed to migrate {receipt_id}: {e}")
        return {
            "receipt_id": receipt_id,
            "success": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description="Migrate existing receipts to enriched boxes")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't actually enrich)")
    parser.add_argument("--limit", type=int, help="Limit number of receipts to process")
    parser.add_argument("--all", action="store_true", help="Process all receipts")
    parser.add_argument("--storage-dir", help="Storage directory override")

    args = parser.parse_args()

    if args.storage_dir:
        os.environ["STORAGE_DIR"] = args.storage_dir

    # Get receipts to migrate
    limit = None if args.all else (args.limit or 10)
    receipt_ids = get_receipts_to_migrate(limit)

    logger.info(f"Found {len(receipt_ids)} receipts to migrate")

    if args.dry_run:
        logger.info("DRY RUN MODE - no actual changes will be made")

    # Process receipts
    results = []
    for i, receipt_id in enumerate(receipt_ids, 1):
        logger.info(f"[{i}/{len(receipt_ids)}] Processing {receipt_id}")
        result = migrate_receipt(receipt_id, args.dry_run)
        results.append(result)

    # Summary
    success_count = sum(1 for r in results if r["success"])
    error_count = len(results) - success_count

    if not args.dry_run:
        total_boxes = sum(r.get("total_boxes", 0) for r in results if r["success"])
        matched_boxes = sum(r.get("matched_boxes", 0) for r in results if r["success"])
        avg_match_rate = sum(r.get("match_rate", 0) for r in results if r["success"]) / success_count if success_count > 0 else 0

    print(f"\n{'='*60}")
    print("Migration Summary:")
    print(f"  Total receipts: {len(results)}")
    print(f"  Success: {success_count}")
    print(f"  Errors: {error_count}")

    if not args.dry_run and success_count > 0:
        print(f"  Total boxes enriched: {total_boxes}")
        print(f"  Total matched: {matched_boxes}")
        print(f"  Average match rate: {avg_match_rate:.1%}")

    print(f"{'='*60}\n")

    # Save results to file
    if not args.dry_run:
        results_file = Path("migration_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Detailed results saved to: {results_file}")


if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Dry run (first 10)
python -m src.tools.migrate_existing_boxes --dry-run --limit 10

# Migrate first 100
python -m src.tools.migrate_existing_boxes --limit 100

# Migrate all (BE CAREFUL!)
python -m src.tools.migrate_existing_boxes --all
```

---

#### Task 6.2: Monitor Migration Progress
**Tid:** 30 min

```bash
# Check progress
mysql -u root -p mind -e "
SELECT
    COUNT(*) as total_receipts,
    SUM(CASE WHEN ai7_status = 'completed' THEN 1 ELSE 0 END) as enriched,
    SUM(CASE WHEN ai7_status IS NULL THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN ai7_status = 'error' THEN 1 ELSE 0 END) as errors,
    AVG(ai7_confidence) as avg_match_rate
FROM unified_files
WHERE ai4_status = 'completed'
AND deleted_at IS NULL
"
```

---

### PHASE 7: Documentation & Deployment

#### Task 7.1: Update API Documentation
**Fil:** `docs/API.md` eller `README.md`
**Tid:** 30 min

```markdown
## Box Enrichment (AI7)

AI7 is an automatic process that runs after data extraction (AI4 for receipts, AI6 for creditcard_invoice) to enrich OCR bounding boxes with semantic field identifiers.

### How It Works

1. **OCR** (early in workflow) detects text and creates `ocr_boxes.json`:
   ```json
   {
     "field": "BAUHAUS",  // OCR text
     "confidence": 0.99,
     "x": 0.7, "y": 0.55, "w": 0.18, "h": 0.06
   }
   ```

2. **AI3/AI4** extract structured data

3. **AI7** (after AI4) matches OCR boxes to extracted fields and creates `boxes.json`:
   ```json
   {
     "field": "company.name",      // Semantic identifier
     "ocr_text": "BAUHAUS",         // Original OCR text
     "confidence": 0.99,            // OCR confidence
     "match_confidence": 0.95,      // Match confidence
     "x": 0.7, "y": 0.55, "w": 0.18, "h": 0.06
   }
   ```

### API Response

`GET /api/receipts/:id/modal` returns enriched boxes:

```json
{
  "boxes": [
    {
      "field": "company.name",
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

### Field Names

Boxes use semantic field identifiers:

**Receipt fields:**
- `receipt.gross_amount`, `receipt.net_amount`
- `receipt.purchase_datetime`, `receipt.purchase_date`
- `receipt.payment_type`, `receipt.expense_type`
- `receipt.credit_card_*`

**Company fields:**
- `company.name`, `company.orgnr`
- `company.address`, `company.city`, `company.zip`
- `company.phone`, `company.www`, `company.email`

**Item fields (future):**
- `items[0].name`, `items[0].amount`
```

---

#### Task 7.2: Update README
**Fil:** `README.md`
**Tid:** 15 min

```markdown
## AI Pipeline

1. **Upload** - File uploaded to system
2. **OCR** - Text extraction with PaddleOCR
   - Creates `ocr_boxes.json` with raw bounding boxes
3. **AI1** - Document classification
4. **AI2** - Expense classification
5. **AI3** - Data extraction (structured fields)
6. **AI4** - Accounting proposals
7. **✨ AI7** - Box enrichment (NEW)
   - Matches OCR boxes to semantic field names
   - Creates `boxes.json` with enriched data
8. **AI5** - Credit card matching (optional)

### NEW: AI7 Box Enrichment

AI7 automatically runs after AI4 to match OCR bounding boxes to extracted data fields. This enables:
- Visual overlay highlighting in receipt preview
- Hover interaction between fields and image overlays
- Validation of extracted data accuracy

See [docs/AI7_BOX_ENRICHMENT.md](docs/AI7_BOX_ENRICHMENT.md) for details.
```

---

#### Task 7.3: Create Deployment Guide
**Fil:** `docs/DEPLOYMENT_AI7.md`
**Tid:** 30 min

```markdown
# AI7 Box Enrichment - Deployment Guide

## Pre-Deployment Checklist

- [ ] All tests passing (`pytest tests/`)
- [ ] Integration tests verified
- [ ] Frontend validation completed
- [ ] Performance acceptable (<2s per receipt)
- [ ] Migration script tested on staging
- [ ] Rollback plan ready

## Deployment Steps

### 1. Database Migration (Optional)

If tracking AI7 in database:

```bash
# Apply migration
cd backend
mysql -u root -p mind < migrations/add_ai7_tracking.sql

# Verify
mysql -u root -p mind -e "SHOW COLUMNS FROM unified_files LIKE 'ai7%'"
```

### 2. Deploy Code

```bash
# Pull latest code
git pull origin master

# Rebuild backend
docker-compose build backend

# Restart services
docker-compose restart backend
```

### 3. Verify Deployment

```bash
# Test AI7 with sample receipt
docker-compose exec backend python -m src.tools.enrich_boxes_cli <sample_receipt_id>

# Check API response
curl http://localhost:8008/ai/api/receipts/<sample_receipt_id>/modal | jq '.boxes[0]'
```

Should see:
```json
{
  "field": "company.name",  // Semantic name ✓
  "ocr_text": "BAUHAUS",
  "confidence": 0.99,
  "match_confidence": 0.95,
  ...
}
```

### 4. Migration (Optional)

Enrich existing receipts:

```bash
# Test with 10 receipts
docker-compose exec backend python -m src.tools.migrate_existing_boxes --limit 10

# If OK, migrate all (run in background)
nohup docker-compose exec backend python -m src.tools.migrate_existing_boxes --all > migration.log 2>&1 &

# Monitor progress
tail -f migration.log
```

### 5. Frontend Verification

1. Open http://localhost:5169 (dev) or http://localhost:8008 (prod)
2. Navigate to Process → Förhandsgranska kvitto
3. Verify hover highlighting works

## Rollback Plan

If issues occur:

### 1. Disable AI7 Triggering

Comment out AI7 trigger in workflow:

```python
# In src/api/ai_processing.py or tasks.py
# if ai4_success:
#     run_box_enrichment(file_id)  # DISABLED
```

Restart backend:
```bash
docker-compose restart backend
```

### 2. Rollback Database (if applied)

```bash
mysql -u root -p mind < migrations/rollback_ai7_tracking.sql
```

### 3. Restore Old Boxes (if needed)

If migration renamed boxes.json → ocr_boxes.json, restore:

```bash
# For specific receipt
cd /data/storage/<receipt_id>
cp ocr_boxes.json boxes.json

# Batch restore (if needed)
find /data/storage -name "ocr_boxes.json" -exec sh -c 'cp "$1" "${1%/*}/boxes.json"' _ {} \;
```

## Monitoring

### Check AI7 Status

```sql
SELECT
    ai7_status,
    COUNT(*) as count,
    AVG(ai7_confidence) as avg_match_rate
FROM unified_files
WHERE ai7_status IS NOT NULL
GROUP BY ai7_status;
```

### Check Errors

```sql
SELECT id, ai7_status, ai7_confidence
FROM unified_files
WHERE ai7_status = 'error'
ORDER BY ai7_timestamp DESC
LIMIT 10;
```

### Logs

```bash
# Backend logs
docker-compose logs -f backend | grep "AI7\|box_enrichment"

# Errors only
docker-compose logs backend | grep -i "error.*ai7"
```

## Troubleshooting

### AI7 Not Running

Check workflow integration:
```bash
# Verify AI7 is triggered after AI4
grep -A5 "ai4.*completed" backend/src/api/ai_processing.py
```

### Low Match Rate

Check extracted data quality:
```bash
# Inspect a receipt with low match rate
docker-compose exec backend python -m src.tools.enrich_boxes_cli <receipt_id>
```

### Performance Issues

Check enrichment time:
```bash
# Time enrichment
time docker-compose exec backend python -m src.tools.enrich_boxes_cli <receipt_id>
```

Should complete in <5s.

## Success Criteria

- [ ] AI7 runs automatically after AI4/AI6
- [ ] Match rate >70% on average
- [ ] Performance <2s per receipt
- [ ] Frontend hover highlighting works
- [ ] No increase in error rate
- [ ] Migration completed (if running)

## Support

For issues, check:
1. Backend logs
2. Database ai7_status
3. boxes.json structure
4. Match confidence values

Contact: [Your team/email]
```

---

## ROLLBACK PLAN

### Quick Rollback (< 5 minutes)

**If AI7 causes issues immediately after deployment:**

1. **Disable AI7 Triggering**
   ```python
   # Comment out in backend/src/api/ai_processing.py
   # if ai4_success:
   #     run_box_enrichment(file_id)  # DISABLED
   ```

2. **Restart Backend**
   ```bash
   docker-compose restart backend
   ```

3. **Verify Old Behavior**
   ```bash
   # Check that boxes.json still works (if old receipts)
   curl localhost:8008/api/receipts/<old_receipt_id>/modal | jq '.boxes'
   ```

**Impact:** New receipts won't get enriched boxes, but old receipts still work.

---

### Full Rollback (< 30 minutes)

**If migration was run and needs rollback:**

1. **Stop Backend**
   ```bash
   docker-compose stop backend
   ```

2. **Restore boxes.json Files**
   ```bash
   # Rename ocr_boxes.json back to boxes.json
   cd /data/storage
   find . -name "ocr_boxes.json" -exec sh -c 'cp "$1" "${1%/*}/boxes.json"' _ {} \;
   ```

3. **Rollback Database** (if AI7 columns added)
   ```bash
   mysql -u root -p mind < backend/migrations/rollback_ai7_tracking.sql
   ```

4. **Revert Code** (git)
   ```bash
   git revert <ai7_commit_hash>
   git push
   ```

5. **Rebuild & Restart**
   ```bash
   docker-compose build backend
   docker-compose up -d backend
   ```

6. **Verify**
   ```bash
   # Check API still works
   curl localhost:8008/api/receipts/<receipt_id>/modal | jq '.boxes'
   ```

**Impact:** System restored to pre-AI7 state. Frontend fuzzy matching required for hover.

---

## SUCCESS CRITERIA

### Must-Have (Before Production)
- ✅ All unit tests pass
- ✅ Integration tests pass
- ✅ Frontend hover works with enriched boxes
- ✅ Performance <2s per receipt
- ✅ No errors in workflow integration

### Should-Have (Within 1 Week)
- ✅ Match rate >70% on average
- ✅ Migration script tested
- ✅ Documentation complete
- ✅ Monitoring in place

### Nice-to-Have (Future)
- ⏭️ Item-level box matching
- ⏭️ Multi-box field grouping
- ⏭️ Confidence-based fallback strategies
- ⏭️ A/B testing of match algorithms

---

## TIMELINE

### Week 1 (Implementation)
**Day 1-2: Core Service**
- Mon: Phase 1 (Task 1.1-1.3) - 3h
- Tue: Phase 1 (Task 1.4-1.6) - 4h

**Day 3: OCR & Integration**
- Wed: Phase 2 + Phase 3 - 4h

**Day 4: Testing**
- Thu: Phase 5 (Task 5.1-5.3) - 3h

**Day 5: Documentation**
- Fri: Phase 7 + Buffer - 2h

**Total Week 1:** ~16 hours

### Week 2 (Optional: Migration + Deployment)
**Day 1: Database**
- Mon: Phase 4 (optional) - 2h

**Day 2-3: Migration**
- Tue-Wed: Phase 6 - 4h

**Day 4: Deployment**
- Thu: Deploy to staging, verify - 4h

**Day 5: Production**
- Fri: Production deployment, monitoring - 2h

**Total Week 2:** ~12 hours (optional)

---

## RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Low match rate (<50%) | Medium | Medium | Tune matching thresholds, add more patterns |
| Performance issues | Low | Medium | Add caching, optimize queries |
| Workflow integration breaks | Low | High | Comprehensive tests, error handling |
| Migration fails | Low | Medium | Dry run, batch processing, rollback plan |
| Frontend compatibility | Low | Low | API backwards compatible |
| Database migration fails | Low | Medium | Tested migration, rollback script ready |

**Overall Risk:** 🟢 LOW

---

## MONITORING & METRICS

### Key Metrics to Track

1. **Match Rate**
   ```sql
   SELECT AVG(ai7_confidence) as avg_match_rate
   FROM unified_files
   WHERE ai7_status = 'completed'
   ```

   **Target:** >70%

2. **Success Rate**
   ```sql
   SELECT
       COUNT(CASE WHEN ai7_status = 'completed' THEN 1 END) / COUNT(*) as success_rate
   FROM unified_files
   WHERE ai4_status = 'completed'
   ```

   **Target:** >95%

3. **Performance**
   - Log enrichment duration
   - **Target:** <2s per receipt

4. **Error Rate**
   ```sql
   SELECT COUNT(*) FROM unified_files WHERE ai7_status = 'error'
   ```

   **Target:** <5%

### Alerts

Set up alerts for:
- AI7 error rate >10%
- Match rate <50%
- Performance >5s

---

## CONTACT & SUPPORT

**Implementation Lead:** [Your Name]
**Code Reviewer:** [Reviewer Name]
**QA Lead:** [QA Name]

**Questions:** Contact via [Slack/Email]

---

**Plan Created:** 2025-10-19
**Version:** 1.0
**Status:** ✅ READY FOR IMPLEMENTATION
**Estimated Effort:** 12-16 hours (core) + 12 hours (optional migration)
**Target Completion:** Week 1-2

---

## NEXT STEPS

1. **Review this plan** with team
2. **Get approval** for Phase 1-3 (critical)
3. **Decide on Phase 4** (database tracking - optional)
4. **Decide on Phase 6** (migration - optional)
5. **Start implementation** following task breakdown

**Ready to begin? Start with Phase 1, Task 1.1!**
