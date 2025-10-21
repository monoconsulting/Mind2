# Overlay Solution Plan - Complete Fix

**Datum:** 2025-10-19
**Problem:** Boxes har OCR text som "field" istället av semantic identifiers
**Root Cause:** OCR-stadiet (mycket tidigt) skapar boxes med extraherad text

---

## PROBLEMANALYS

### När Skapas Boxes?

**Workflow:**
1. **Upload** → Fil sparas
2. **OCR** → PaddleOCR extraherar text + bounding boxes
   - `ocr.py:_extract_text_from_images()` rad 74-239
   - Skapar `boxes.json` med `"field": <extraherad_text>`
   - **Detta är MYCKET tidigt** - före AI-analys
3. **AI1** (document_analysis) → Klassificerar dokument
4. **AI2** (expense_classification) → Klassificerar utgiftstyp
5. **AI3** (data_extraction) → Extraherar strukturerad data
6. **AI4** (accounting) → Genererar bokföringsförslag

**Boxes skapas i steg 2 (OCR) - före AI har analyserat vad fälten betyder!**

### Current OCR Code (src/services/ocr.py rad 158-167):

```python
boxes.append({
    "field": text_str,  # ← PROBLEM: "BAUHAUS" istället för "company.name"
    "confidence": float(confidence),
    "x": x_norm,
    "y": y_norm,
    "w": w_norm,
    "h": h_norm,
})
```

### Rotation Code (ocr.py rad 145-150):

```python
if width > height:  # Landscape detection
    rotated_x = y_norm
    rotated_y = 1.0 - x_norm - w_norm
    rotated_w = h_norm
    rotated_h = w_norm
    x_norm, y_norm, w_norm, h_norm = rotated_x, rotated_y, rotated_w, rotated_h
```

**Problem:** Detta roterar koordinater om width > height, men:
- Logiken är unclear
- Fungerar inte med EXIF-rotation
- Frontend får redan roterade koordinater som inte matchar rendered image

---

## LÖSNINGSALTERNATIV

### ALTERNATIV A: AI3 Enriches Boxes (REKOMMENDERAD)

**Koncept:** AI3 (data_extraction) känner igen vilka fält som är vilka. Låt AI3 uppdatera boxes med semantic field names.

**Workflow:**
1. OCR skapar boxes med `"field": <text>` (behåller detta för backwards compatibility)
2. AI3 analyserar data och **matchar OCR boxes mot extracted fields**
3. AI3 uppdaterar boxes.json med semantic identifiers:

```json
{
  "field": "company.name",           // ← NY: Semantic identifier
  "ocr_text": "BAUHAUS",             // ← NY: Original text
  "confidence": 0.99,
  "x": 0.7,
  "y": 0.55,
  "w": 0.18,
  "h": 0.06
}
```

**Fördelar:**
- ✅ Boxes har semantic meaning
- ✅ OCR phase behålls enkel (bara text detection)
- ✅ AI3 har all context för matching
- ✅ Backwards compatible (behåller ocr_text)

**Implementation:**

**Steg 1:** AI3 ska få boxes som input:

```python
# I AI3 service
def extract_receipt_data(receipt_id: str, ocr_text: str) -> dict:
    # ... existing code ...

    # Load existing boxes from OCR
    boxes = _load_boxes(receipt_id)

    # ... AI extracts structured data ...
    extracted = {
        "merchant_name": "BAUHAUS",
        "gross_amount": 359.00,
        "purchase_datetime": "2025-09-08",
        # ...
    }

    # Match boxes to extracted fields
    enriched_boxes = _match_boxes_to_fields(boxes, extracted)

    # Save updated boxes
    _save_boxes(receipt_id, enriched_boxes)

    return extracted
```

**Steg 2:** Implement fuzzy matching logic:

```python
def _match_boxes_to_fields(
    boxes: List[Dict],
    extracted_data: Dict[str, Any]
) -> List[Dict]:
    """Match OCR boxes to semantic field names based on extracted data."""

    enriched = []

    for box in boxes:
        ocr_text = box.get("field", "").strip().lower()
        matched_field = None

        # Try to match against extracted values
        for field_name, field_value in extracted_data.items():
            if field_value is None:
                continue

            value_str = str(field_value).strip().lower()

            # Exact match
            if ocr_text == value_str:
                matched_field = f"receipt.{field_name}"
                break

            # Partial match (for long values)
            if len(ocr_text) >= 4 and (
                ocr_text in value_str or value_str in ocr_text
            ):
                matched_field = f"receipt.{field_name}"
                break

            # Fuzzy match for truncated text (e.g., "Handelsban" vs "Handelsbanken")
            if len(ocr_text) >= 6 and value_str.startswith(ocr_text):
                matched_field = f"receipt.{field_name}"
                break

        # Keep original box data
        enriched_box = {
            **box,
            "ocr_text": box.get("field"),  # Preserve original
        }

        # Add semantic field if matched
        if matched_field:
            enriched_box["field"] = matched_field
        # else: keep original text as field (unmatched)

        enriched.append(enriched_box)

    return enriched
```

**Steg 3:** Handle company vs receipt fields:

```python
def _match_boxes_to_fields(
    boxes: List[Dict],
    extracted_receipt: Dict[str, Any],
    extracted_company: Dict[str, Any] = None
) -> List[Dict]:
    """Match boxes to both receipt and company fields."""

    enriched = []

    for box in boxes:
        ocr_text = box.get("field", "").strip().lower()
        matched_field = None

        # Try receipt fields first
        for field_name, field_value in extracted_receipt.items():
            if _is_match(ocr_text, field_value):
                matched_field = f"receipt.{field_name}"
                break

        # Try company fields if no receipt match
        if not matched_field and extracted_company:
            for field_name, field_value in extracted_company.items():
                if _is_match(ocr_text, field_value):
                    matched_field = f"company.{field_name}"
                    break

        enriched_box = {
            **box,
            "ocr_text": box.get("field"),
            "field": matched_field or box.get("field")  # fallback to original
        }

        enriched.append(enriched_box)

    return enriched

def _is_match(ocr_text: str, field_value: Any) -> bool:
    """Check if OCR text matches a field value."""
    if field_value is None:
        return False

    value_str = str(field_value).strip().lower()

    # Exact match
    if ocr_text == value_str:
        return True

    # Partial match (both ways)
    if len(ocr_text) >= 4 and (ocr_text in value_str or value_str in ocr_text):
        return True

    # Prefix match for truncated names
    if len(ocr_text) >= 6 and value_str.startswith(ocr_text):
        return True

    return False
```

---

### ALTERNATIV B: Frontend Fuzzy Matching (WORKAROUND)

Om backend-fix tar för lång tid, temporary workaround i frontend:

```javascript
// ReceiptPreviewModal.jsx
function findMatchingBox(fieldKey, fieldValue, boxes) {
  // 1. Try exact semantic match
  const semanticMatch = boxes.find(box =>
    normaliseFieldId(box.field) === normaliseFieldId(fieldKey)
  );
  if (semanticMatch) return semanticMatch;

  // 2. Try fuzzy match on value
  if (!fieldValue) return null;

  const valueStr = String(fieldValue).toLowerCase();
  const fuzzyMatch = boxes.find(box => {
    const boxField = String(box.field || box.ocr_text || '').toLowerCase();

    // Exact match
    if (boxField === valueStr) return true;

    // Partial match (min 4 chars)
    if (valueStr.length >= 4 && boxField.includes(valueStr)) return true;
    if (boxField.length >= 4 && valueStr.includes(boxField)) return true;

    // Prefix match (min 6 chars)
    if (valueStr.length >= 6 && boxField.startsWith(valueStr)) return true;
    if (boxField.length >= 6 && valueStr.startsWith(boxField)) return true;

    return false;
  });

  return fuzzyMatch;
}

// Usage in field rendering:
const hoverKey = (() => {
  const fieldValue = sourceData[field.key];
  const matchedBox = findMatchingBox(field.key, fieldValue, boxes);
  return matchedBox?.field || field.key;
})();
```

---

## ROTATION FIX

### Problem Med Nuvarande Kod:

```python
# ocr.py rad 145-150
if width > height:  # Landscape detection
    rotated_x = y_norm
    rotated_y = 1.0 - x_norm - w_norm
    rotated_w = h_norm
    rotated_h = w_norm
```

**Issues:**
1. Roterar baserat på aspect ratio, inte EXIF orientation
2. Antar 90° rotation vilket kanske inte stämmer
3. Frontend kan ha redan roterat bilden via EXIF → dubbel rotation

### Lösning: Ta Bort Auto-Rotation i OCR

**RÄTT approach:**
1. OCR ska returnera koordinater för bilden **som den är** (innan rotation)
2. Frontend ska hantera rotation baserat på EXIF

**Fix i ocr.py:**

```python
# TA BORT rad 145-150 (auto-rotation logic)

# Eller gör det optional med en flag
def append_detection(text_value, polygon, confidence, apply_rotation=False):
    # ... existing code until normalization ...

    x_norm = min_x / width
    y_norm = min_y / height
    w_norm = (max_x - min_x) / width
    h_norm = (max_y - min_y) / height

    # REMOVE eller gör conditional:
    # if apply_rotation and width > height:
    #     ... rotation logic ...

    # Clamp values
    x_norm = max(min(x_norm, 1.0), 0.0)
    y_norm = max(min(y_norm, 1.0), 0.0)
    # ...
```

**Frontend ska då:**
1. Läsa EXIF orientation från img
2. Applicera transformation på boxes vid render

```jsx
const [exifOrientation, setExifOrientation] = React.useState(1);

React.useEffect(() => {
  if (!imgRef.current) return;

  // Read EXIF if available
  const img = imgRef.current;
  // EXIF reading logic eller via library

  // Eller detektera från CSS transform
  const style = window.getComputedStyle(img);
  const transform = style.transform;
  // Parse rotation från transform matrix
}, [baseImageSrc]);

function transformBox(box, orientation) {
  const {x, y, w, h} = box;

  switch(orientation) {
    case 6: // 90° CW
      return {
        x: 1 - y - h,
        y: x,
        w: h,
        h: w
      };
    case 3: // 180°
      return {
        x: 1 - x - w,
        y: 1 - y - h,
        w, h
      };
    case 8: // 270° CW
      return {
        x: y,
        y: 1 - x - w,
        w: h,
        h: w
      };
    default: // 1 = no rotation
      return {x, y, w, h};
  }
}
```

---

## IMPLEMENTATION PLAN

### Phase 1: Backend - AI3 Box Enrichment (2-3 hours)

**Priority:** HIGH

**Files:**
- `backend/src/services/ai_service.py` (AI3 logic)
- `backend/src/services/ocr.py` (helper functions)

**Steps:**
1. Create `_match_boxes_to_fields()` function
2. Integrate into AI3 data extraction
3. Load/save boxes.json
4. Test with sample receipts

**Testing:**
```bash
# Before fix
curl -s http://localhost:8008/ai/api/receipts/933b749c.../modal | grep -A5 boxes
# Shows: "field": "BAUHAUS"

# After fix
# Shows: "field": "company.name", "ocr_text": "BAUHAUS"
```

---

### Phase 2: Backend - Remove OCR Rotation (30 min)

**Priority:** MEDIUM

**Files:**
- `backend/src/services/ocr.py` rad 145-150

**Action:** Comment out or remove rotation logic

**Rationale:** Let frontend handle rotation based on actual EXIF

---

### Phase 3: Frontend - EXIF Rotation Support (1-2 hours)

**Priority:** MEDIUM (can be done later)

**Files:**
- `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Steps:**
1. Detect EXIF orientation
2. Transform box coordinates
3. Test with rotated images

---

### Phase 4: Frontend - Fuzzy Matching Fallback (1 hour)

**Priority:** LOW (only if backend fix insufficient)

**Files:**
- `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

**Purpose:** Handle any remaining unmatchable boxes

---

## SUCCESS CRITERIA

### After Phase 1 (AI3 Enrichment):

```bash
# API returns semantic field names
curl localhost:8008/ai/api/receipts/{id}/modal | jq '.boxes[0]'
{
  "field": "company.name",
  "ocr_text": "BAUHAUS",
  "confidence": 0.99,
  "x": 0.7,
  "y": 0.55,
  "w": 0.18,
  "h": 0.06
}
```

**Frontend:**
- ✅ Hover över "Företag: BAUHAUS" field → overlay över "BAUHAUS" text blir gul
- ✅ Hover över overlay → field "Företag" blir gul
- ✅ Matching fungerar för alla huvudfält

### After Phase 2 (Rotation Fix):

**Backend:**
- ✅ OCR returnerar koordinater för original image (inte roterade)

**Frontend:**
- ⏭️ Väntar på Phase 3 för full rotation support

### After Phase 3 (EXIF Support):

**Frontend:**
- ✅ Portrait images: overlays korrekt placerade
- ✅ Landscape images: overlays korrekt placerade
- ✅ Rotated images (EXIF 6/8): overlays transformerade korrekt
- ✅ Resize window: overlays följer bilden

---

## TIMELINE

**Day 1 (Today):**
- [x] Problem analysis ✅
- [x] Solution design ✅
- [ ] Phase 1 implementation (2-3h)
- [ ] Phase 1 testing (30min)

**Day 2:**
- [ ] Phase 2 implementation (30min)
- [ ] Phase 3 implementation (1-2h)
- [ ] Full E2E testing
- [ ] Documentation update

**Total:** ~5-7 hours work

---

## RISKS & MITIGATION

### Risk 1: AI3 Matching Fails for Some Fields

**Mitigation:**
- Start with high-confidence matches (exact, prefix)
- Log unmatched boxes for analysis
- Frontend fallback to ocr_text
- Iterative improvement based on logs

### Risk 2: Rotation Logic Breaks Existing Receipts

**Mitigation:**
- Make Phase 2 optional with feature flag
- Test thoroughly with sample set
- Rollback capability

### Risk 3: Performance Impact (Box Matching)

**Mitigation:**
- Matching is simple string comparison (fast)
- Runs once during AI3 (not on every request)
- Cache enriched boxes

---

## NEXT ACTIONS

**IMMEDIATE (Priority 1):**

1. **Start Phase 1 Implementation**
   ```bash
   cd E:\projects\Mind2\backend
   # Edit src/services/ai_service.py
   # Add box matching logic to AI3
   ```

2. **Test AI3 Enrichment**
   ```bash
   # Trigger AI3 for a test receipt
   # Check boxes.json before/after
   ```

3. **Verify Frontend Receives Semantic Names**
   ```bash
   # Open modal
   # Check console for box.field values
   ```

**Vill du att jag börjar med Phase 1 implementation nu?**

---

**Plan Created:** 2025-10-19
**Status:** READY TO IMPLEMENT
**Estimated Effort:** 5-7 hours total
**Phase 1 Effort:** 2-3 hours (highest priority)
