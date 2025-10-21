# AGENT BRIEF — AI7 Box Enrichment (Overlay Stability)

**Objective:** Fix preview overlay mismatch by deferring semantic box mapping to a new **AI7 – Box Enrichment** step that runs **after AI4** (or **after AI6** for card statements).
 **Key principle:** OCR writes **only raw OCR boxes** to `ocr_boxes.json`. AI7 reads `ocr_boxes.json` + AI3/AI4 outputs and writes **semantic** `boxes.json` with canonical field keys used by the UI.

------

## 0) Hard Non-Negotiable Rules

1. **DO NOT** alter frontend layout, scrolling, sizes, CSS, or column structure in the Preview modal. Zero visual changes.
2. **DO NOT** write or modify `boxes.json` in the OCR step. OCR must write **only** `ocr_boxes.json`.
3. **DO NOT** run AI7 before AI3/AI4 (or AI6).
4. **DO NOT** invent fields or change key names. Use **exact** canonical keys below.
5. **DO NOT** “auto-improve” unrelated files, prompts, or services. Scope is limited to files listed in §1.

------

## 1) Files to Create / Update (exact paths)

> All paths are relative to the repo root. Keep filenames and locations **exact**.

### Create

- `backend/src/services/box_enrichment.py`
   New service that:
  - Loads `/data/storage/<receipt_id>/ocr_boxes.json`
  - Loads structured values from DB (as produced by AI3/AI4)
  - Produces `/data/storage/<receipt_id>/boxes.json` with **semantic** fields.
- `backend/tests/test_box_enrichment.py`
   Pure unit tests for `box_enrichment.py` (no DB dependency; mock DB loader functions).

### Update

- `backend/src/services/ocr.py`
   Ensure the OCR box writer function writes to **`ocr_boxes.json`** (not `boxes.json`). If it already writes `ocr_boxes.json`, leave it unchanged.
- `backend/src/api/ai_processing.py` (or equivalent pipeline coordinator)
   Immediately after a successful **AI4** completion (and **AI6** if applicable), **invoke AI7** (`run_box_enrichment(receipt_id)`). Do **not** change API response schemas or frontend endpoints.
- (Optional, only if you have type guards) `backend/src/models/ai_processing.py`
   Extend allowed `processing_steps` to include `"AI7"`. You **must not** require the client to request AI7; it is run automatically after AI4/AI6 by the backend.

------

## 2) Canonical Field Keys (must match frontend & DB)

Use **exactly** these keys in `boxes.json` → `field` values:

**Company:**

- `company.name`
- `company.orgnr`
- `company.address`
- `company.zip`
- `company.city`
- `company.country`
- `company.phone`
- `company.www`
- `company.email`

**Receipt:**

- `receipt.gross_amount`
- `receipt.net_amount`
- `receipt.currency`
- `receipt.purchase_datetime` (ISO-8601)
- `receipt.payment_type` ∈ {`cash`,`card`,`swish`}
- `receipt.expense_type` ∈ {`personal`,`corporate`}
- `receipt.receipt_number`
- `receipt.total_vat_25`
- `receipt.total_vat_12`
- `receipt.total_vat_6`

**Notes:**

- Amounts are decimals with `.` decimal separator.
- If a value is unknown, leave it empty/`null`. **Do not invent values.**
- For now, **do not** include line-items (`items[i].*`) in AI7 mapping.

------

## 3) `box_enrichment.py` — Required Behavior (no extra features)

Implement a single public function:

```
def run_box_enrichment(receipt_id: str, storage_dir: str | Path | None = None) -> dict:
    """
    Reads <storage_dir or /data/storage>/<receipt_id>/ocr_boxes.json (list of OCR boxes),
    enriches them using structured fields from DB, and writes boxes.json (list).

    Returns a dict with:
      {
        "success": bool,
        "total_boxes": int,
        "matched_boxes": int,
        "unmatched_boxes": int,
        "match_rate": float,   # 0.0..1.0
        # Optional: "error": "<code>"
      }
    }
```

**Input file:**
 `/data/storage/<receipt_id>/ocr_boxes.json` — list of dicts with at least:

```
[
  {"x": <float/int>, "y": <float/int>, "w": <float/int>, "h": <float/int>, "field": "<ocr_text>", "confidence": <0..1>},
  ...
]
```

**Output file:**
 `/data/storage/<receipt_id>/boxes.json` — list of dicts:

```
[
  {
    "x": ...,
    "y": ...,
    "w": ...,
    "h": ...,
    "ocr_text": "<original>",
    "confidence": <0..1>,
    "field": "company.name" | "receipt.gross_amount" | "<unchanged OCR text if no match>",
    "match_confidence": <0..1>
  },
  ...
]
```

**Matching logic (strict minimal):**

- Normalize both OCR text and candidate values (lowercase, strip, remove diacritics, collapse whitespace).
- Consider:
  - Exact normalized equality → high score.
  - Substring on sufficiently long tokens.
  - Numeric token overlap (e.g., amounts, dates, orgnr).
- Choose the **single best** semantic key if score ≥ `0.60`. Otherwise keep `field` as original OCR text and set `match_confidence = 0.0`.

**Data sources (read-only):**

- A function that returns a dict of current **receipt** values for the `receipt_id`.
- A function that returns a dict of current **company** values for the `receipt_id`.

If your project provides a DB cursor helper (e.g., `services.db.connection.db_cursor`), use it. If not available at import time, handle gracefully (empty dicts). Do not crash on missing data.

------

## 4) Pipeline Hook (when to run AI7)

- **After AI4 success** for receipts: immediately call `run_box_enrichment(receipt_id)`.
- **After AI6 success** for card statement workflows: same.

Append `"AI7"` to any in-memory `steps_completed` list if `run_box_enrichment(...)["success"]` is `True`.
 Do **not** change existing API response schema to clients.

------

## 5) Verification Procedure (must pass 100%)

1. **OCR stage output**
   - Process a receipt through OCR only.
   - Verify directory: `/data/storage/<receipt_id>/` contains `ocr_boxes.json`.
   - Verify that `boxes.json` **does not exist** yet.
2. **Run through AI1–AI4** (or AI6)
   - After AI4 (or AI6) completes, verify `boxes.json` now exists.
   - Open `boxes.json` and confirm every object contains:
     - `ocr_text`, `x`, `y`, `w`, `h`, `confidence`
     - `field` (semantic key **or** unchanged OCR text if no match)
     - `match_confidence` (≥ 0.60 for mapped fields, 0.0 for unmapped)
3. **Preview modal behavior**
   - Open the Preview modal for that `receipt_id`.
   - Hover any populated field in the left/right tables; the corresponding overlay box must highlight **exactly** and in **the same yellow**.
   - Hover a box on the image; the corresponding table row must highlight **exactly**.
4. **No layout changes**
   - Confirm no visual changes to widths, scrolling, or columns in the modal.
5. **Regression on failure paths**
   - Temporarily remove `ocr_boxes.json` and re-run AI7 → should return success with 0 boxes and **must not** crash the API.
   - Corrupt JSON in `ocr_boxes.json` → AI7 should return `{"success": False, "error": "read_error", ...}` and **must not** crash upstream.

------

## 6) Tests to Add (pytest)

> Place in `backend/tests/test_box_enrichment.py`. Tests are **self-contained** and **do not** require DB connectivity or the full web app. They monkeypatch the data-loading functions in `box_enrichment.py`.

```
# backend/tests/test_box_enrichment.py
import json
import os
from pathlib import Path
import types

import pytest

# Import the module under test
import backend.src.services.box_enrichment as be


@pytest.fixture
def temp_storage(tmp_path: Path):
    # Create a fake receipt directory with minimal OCR boxes
    rid = "R-TEST-001"
    rdir = tmp_path / rid
    rdir.mkdir(parents=True)
    ocr_boxes = [
        {"x": 10, "y": 20, "w": 100, "h": 24, "field": "Acme AB", "confidence": 0.91},
        {"x": 12, "y": 56, "w": 90,  "h": 22, "field": "Org.nr 556677-8899", "confidence": 0.88},
        {"x": 15, "y": 98, "w": 80,  "h": 22, "field": "Total: 123,45 SEK", "confidence": 0.93},
        {"x": 16, "y": 140,"w": 70,  "h": 22, "field": "2025-10-01 12:34", "confidence": 0.85},
        {"x": 18, "y": 170,"w": 75,  "h": 22, "field": "Random note", "confidence": 0.50},
    ]
    (rdir / "ocr_boxes.json").write_text(json.dumps(ocr_boxes, ensure_ascii=False, indent=2), encoding="utf-8")
    return rid, tmp_path


def test_enrichment_maps_semantic_fields(monkeypatch: pytest.MonkeyPatch, temp_storage):
    rid, tmp_root = temp_storage

    # Monkeypatch data loaders to avoid DB
    def fake_load_receipt(_rid: str):
        assert _rid == rid
        return {
            "gross_amount": 123.45,
            "net_amount": 98.76,
            "currency": "SEK",
            "purchase_datetime": "2025-10-01T12:34:00",
            "payment_type": "card",
            "expense_type": "corporate",
            "receipt_number": "A-42",
            "total_vat_25": 24.69,
            "total_vat_12": None,
            "total_vat_6": None,
        }

    def fake_load_company(_rid: str):
        assert _rid == rid
        return {
            "name": "Acme AB",
            "orgnr": "556677-8899",
            "address": "Storgatan 1",
            "zip": "11122",
            "city": "Stockholm",
            "country": "SE",
            "phone": None,
            "www": None,
            "email": None,
        }

    monkeypatch.setattr(be, "_load_receipt", fake_load_receipt)
    monkeypatch.setattr(be, "_load_company", fake_load_company)

    stats = be.run_box_enrichment(receipt_id=rid, storage_dir=tmp_root)
    assert stats["success"] is True
    assert stats["total_boxes"] == 5
    assert stats["matched_boxes"] >= 3  # company name, orgnr, total/amount should match
    assert 0.0 <= stats["match_rate"] <= 1.0

    # Validate output file
    out = (tmp_root / rid / "boxes.json").read_text(encoding="utf-8")
    boxes = json.loads(out)
    assert isinstance(boxes, list) and len(boxes) == 5

    # Check some specific mappings
    fields = {b["field"] for b in boxes}
    assert "company.name" in fields
    assert "company.orgnr" in fields
    # Allow amount text to map to either gross or net depending on OCR text, but must be semantic if numeric overlap
    assert any(f.startswith("receipt.") for f in fields)

    # Ensure unmapped text remains unmapped with 0.0 confidence
    random_box = next(b for b in boxes if b["ocr_text"] == "Random note")
    assert random_box["field"] == "Random note"
    assert random_box["match_confidence"] == 0.0


def test_handles_missing_ocr_file_gracefully(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    rid = "R-NO-OCR"
    # No ocr_boxes.json written

    # Return some data (they should be ignored due to no OCR boxes)
    monkeypatch.setattr(be, "_load_receipt", lambda _rid: {"gross_amount": 10})
    monkeypatch.setattr(be, "_load_company", lambda _rid: {"name": "X"})

    stats = be.run_box_enrichment(receipt_id=rid, storage_dir=tmp_path)
    assert stats["success"] is True
    assert stats["total_boxes"] == 0
    assert stats["matched_boxes"] == 0
    assert stats["unmatched_boxes"] == 0
    assert stats["match_rate"] == 0.0


def test_invalid_ocr_json_is_reported(tmp_path: Path):
    rid = "R-BAD-JSON"
    rdir = tmp_path / rid
    rdir.mkdir(parents=True)
    (rdir / "ocr_boxes.json").write_text("{invalid json", encoding="utf-8")

    stats = be.run_box_enrichment(receipt_id=rid, storage_dir=tmp_path)
    assert stats["success"] is False
    assert stats["error"] == "read_error"
    assert stats["total_boxes"] == 0
```

**How to run:**

```
# from repo root
pytest -q backend/tests/test_box_enrichment.py
```

**Passing criteria:**

- All tests above must pass without modifying anything outside §1 scope.
- No additional network/DB/file dependencies may be introduced into these tests.

------

## 7) Minimal Edits Required (exact)

1. **`backend/src/services/ocr.py`**

   - Confirm that OCR box writer writes **`ocr_boxes.json`** (and not `boxes.json`).
   - If a helper `_write_boxes()` exists and points to `boxes.json`, change it to `ocr_boxes.json`.
   - No other logic changes.

2. **`backend/src/api/ai_processing.py`** (or equivalent)

   - After finishing **AI4** (and **AI6** if present), call:

     ```
     from services.box_enrichment import run_box_enrichment
     stats = run_box_enrichment(file_id)
     if stats.get("success"):
         steps_completed.append("AI7")
         result["ai7"] = stats
     else:
         result["ai7_error"] = stats.get("error", "unknown")
     ```

   - Do **not** modify request/response schema visible to frontend clients.

3. **`backend/src/services/box_enrichment.py`**

   - Implement **exactly** the behavior in §3 (no extra endpoints, no CLI, no side effects).

4. **`backend/tests/test_box_enrichment.py`**

   - Add the tests from §6 verbatim. Do not rename the file.

------

## 8) Post-Deployment Smoke Checklist

-  New OCR runs produce **only** `ocr_boxes.json`.
-  After AI4 (or AI6), directory contains **both** `ocr_boxes.json` and `boxes.json`.
-  Preview modal highlighting is correct both image→table and table→image.
-  No UI regressions (sizes/scroll/columns).
-  Tests in `backend/tests/test_box_enrichment.py` pass locally and in CI.
-  Error handling validated for missing/corrupt OCR JSON.

------

## 9) Out-of-Scope (forbidden)

- Changing any frontend code, styling, or behavior in the Preview modal.
- Changing API endpoints, shapes, or auth.
- Renaming fields or adding new ones beyond §2.
- Re-ordering pipeline steps other than adding the **automatic** AI7 call post-AI4/AI6.
- Any schema migrations or DB writes. AI7 is **read-only** (input), **write boxes.json only** (output).