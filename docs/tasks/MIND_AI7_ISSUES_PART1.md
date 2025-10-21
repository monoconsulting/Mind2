# AI7 Box Enrichment — Verifieringsrapport

## 0) Översikt

- **Kodbas granskad:** `codebase_251019_13-16.zip` (570 filer).
- **Bedömningsmål:** Stämmer implementationen mot planen: rå-OCR → `ocr_boxes.json`, AI7 efter AI4/AI6 → `boxes.json`, rätt API/endpoints, inga breaking UI-ändringar, fungerande tester.
- **Sammanfattning:**
  - **Saknas:** Själva AI7-tjänsten (`backend/src/services/box_enrichment.py`) och dess anrop efter AI4/AI6.
  - **Fel:** OCR skriver fortfarande till `boxes.json` i stället för `ocr_boxes.json`.
  - **OK men förvirrande:** Läsningen av `boxes.json` i endpointen använder en “parent-trick” som fungerar, men är svårbegriplig.
  - **Tester:** Inga AI7-tester finns ännu.

------

## 1) Detaljerade fynd (rad-/filhänvisningar)

### F1. `_load_boxes()` – sökväg

- **Fil:** `backend/src/api/receipts.py`, rader **853–861**.

  ```
  def _load_boxes(rid: str) -> list[dict[str, Any]]:
      try:
          root = _storage_dir().parent / rid
          p = root / "boxes.json"
          ...
  ```

- **Analys:** `_storage_dir()` (r. 29–31) returnerar `Path(base)/"line_items"`. `.parent` blir alltså `Path(base)` ⇒ `root = /data/storage/<rid>`.
   **Slutsats:** Sökvägen **landar rätt** trots att det är otydligt. Det här var flaggat som “fel” i en tidigare rapport, men i denna kodbas är det **funktionellt korrekt**.

- **Rekommendation:** För tydlighet: inför en separat hjälpare, t.ex. `_storage_root()` → `Path(os.getenv("STORAGE_DIR", "/data/storage"))` och använd `root = _storage_root() / rid`. (Valfri förbättring; ej blockerare.)

### F2. **AI7 saknas helt**

- **Sökning:** Ingen fil `backend/src/services/box_enrichment.py`. Ingen referens till `run_box_enrichment` i koden.
- **Konsekvens:** `boxes.json` skapas aldrig semantiskt efter AI4/AI6. Overlay blir osäker/tom även om OCR genererar rutor.

### F3. **AI7 anropas inte efter AI4**

- **Fil:** `backend/src/api/ai_processing.py`, r. **744–821** (AI4-grenen i batchflödet).
  - Ingen anrop/logik för AI7 efter `file_result["steps_completed"].append("AI4")`.

### F4. **AI7 anropas inte i kreditkortsflödet**

- **Fil:** `backend/src/api/ai_processing.py`, funktionen **`match_credit_card_internal`** (r. **592–607**).
  - Efter lyckad match/persist körs aldrig AI7.
  - (Det finns heller inget begrepp “AI6” uttryckligen i denna fil; kreditkortsmatchningen hanteras via dedikerade metoder. Poängen kvarstår: efter att kortmatchningen fyllt strukturdata ska enrichment ske.)

### F5. **OCR skriver fortfarande till `boxes.json` (måste vara `ocr_boxes.json`)**

- **Fil:** `backend/src/services/ocr.py`, r. **28–33**:

  ```
  def _write_boxes(base, receipt_id, boxes):
      root = _receipt_dir(base, receipt_id)
      root.mkdir(parents=True, exist_ok=True)
      (root / "boxes.json").write_text(json.dumps(...))
  ```

- **Konsekvens:** AI7 får inget rå-underlag (`ocr_boxes.json`). I bästa fall övertrampas semantiska `boxes.json`; i sämsta fall uteblir overlay helt.

### F6. **Batch-modellens steps**

- **Fil:** `backend/src/models/ai_processing.py`, r. **319–323**.

  ```
  processing_steps: List[Literal["AI1","AI2","AI3","AI4","AI5"]]
  ```

- **Status:** **AI7 är INTE möjlig att begära** i modellen — vilket ligger i linje med kravet “AI7 ska köras automatiskt”. (Den tidigare externa rapporten som sade att AI7 redan fanns med i `Literal[...]` gäller inte denna kodbas.)

- **Åtgärd:** Ingen nödvändig.

### F7. **Endpoint för att hämta boxes**

- **Fil:** `backend/src/api/receipts.py`, r. **1317–1322**:

  ```
  @receipts_bp.get("/receipts/<rid>/ocr/boxes")
  def get_ocr_boxes(rid: str) -> Any:
      try:
          return jsonify(_load_boxes(rid)), 200
  ```

- **Status:** Endpoint finns och svarar med `boxes.json`-innehållet via `_load_boxes()` — **OK** när väl `boxes.json` skapas korrekt av AI7.

### F8. **Tester saknas**

- Ingen fil `backend/tests/test_box_enrichment.py` finns.

------

## 2) Prioriterad åtgärdslista (koncis)

> **P0 – Blockerande: måste fixas för funktion**

1. **Ändra OCR-skrivning → `ocr_boxes.json`**
   - Fil: `backend/src/services/ocr.py`
   - Ändra endast rad som skriver filnamnet (ofarlig, isolerad fix).
2. **Skapa AI7-tjänst**
   - Fil: `backend/src/services/box_enrichment.py` (ny)
   - Läser `<storage_root>/<rid>/ocr_boxes.json` + DB-värden och skriver `<storage_root>/<rid>/boxes.json`.
3. **Kör AI7 automatiskt efter AI4**
   - Fil: `backend/src/api/ai_processing.py`
   - Direkt efter “AI4 klar” i batchflödet: anropa AI7.
4. **Kör AI7 efter kreditkorts-match (post-match)**
   - Fil: `backend/src/api/ai_processing.py`
   - I `match_credit_card_internal(...)`: när matchning/lagring lyckats, anropa AI7.

> **P1 – Viktigt (kvalitet/säkerhet)**

1. **Lägg in guard i AI7**: kör inte om AI3/AI4-data saknas. Returnera `success=True` med `total_boxes=0` eller `success=False` med `error="no_data"`, utan att krascha.
2. **Förtydliga lagringsväg (frivilligt)**
   - Inför `_storage_root()` för läsbarhet så att path-logiken inte beror på `.parent`.

> **P2 – Rekommenderat**

1. **Migration för gamla kvitton**
   - Om det finns historiska `boxes.json` utan `ocr_boxes.json`: kopiera dessa till `ocr_boxes.json` och kör AI7 en gång för att få semantiska fält.
2. **Tester**
   - Lägg till `backend/tests/test_box_enrichment.py` med tre tests (enrichment happy path, missing OCR, invalid JSON).

------

## 3) Minimala kodpatchar (punktinsatser)

> Nedan är **små, precisa** patchar du kan applicera. De ändrar inga API-kontrakt eller UI.

### 3.1 OCR → skriv råboxar

**Fil:** `backend/src/services/ocr.py`

```
 def _write_boxes(base: str | Path, receipt_id: str, boxes: List[Dict[str, Any]]) -> None:
     root = _receipt_dir(base, receipt_id)
     root.mkdir(parents=True, exist_ok=True)
-    (root / "boxes.json").write_text(json.dumps(boxes, ensure_ascii=False, indent=2), encoding="utf-8")
+    # AI7 kräver RAW OCR-boxar här, inte semantiska.
+    (root / "ocr_boxes.json").write_text(json.dumps(boxes, ensure_ascii=False, indent=2), encoding="utf-8")
```

> **Obs:** Detta måste ut i drift innan ni förväntar er att nya körningar får overlay.

------

### 3.2 AI7 – ny tjänst

**Fil (ny):** `backend/src/services/box_enrichment.py`
 *(sammanfattad version enligt din specifikation; inga externa beroenden krävs)*

```
from __future__ import annotations
import json, os, re, unicodedata, logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

def _storage_root() -> Path:
    return Path(os.getenv("STORAGE_DIR", "/data/storage"))

def _norm(x: Any) -> str:
    if x is None: return ""
    s = str(x).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)

def _nums(x: Any) -> List[str]:
    if x is None: return []
    return [p.replace(",", ".") for p in re.findall(r"\d+[.,\-]?\d*", str(x))]

def _fuzzy(ocr_text: str, value: Any) -> Tuple[bool, float]:
    a, b = _norm(ocr_text), _norm(value)
    if not a or not b: return (False, 0.0)
    if a == b: return (True, 0.95)
    if len(a) >= 4 and a in b: return (True, 0.80 if len(a)/len(b) > .5 else 0.70)
    na, nb = _nums(ocr_text), _nums(value)
    if na and nb and all(x in nb for x in na): return (True, 0.85 if len(na)>1 else 0.75)
    return (False, 0.0)

def _best_field(ocr_text: str, receipt: Dict[str,Any], company: Dict[str,Any], thr=0.60) -> Tuple[Optional[str], float]:
    best: Tuple[Optional[str], float] = (None, 0.0)
    for k,v in (receipt or {}).items():
        ok,c = _fuzzy(ocr_text,v)
        if ok and c>best[1]: best = (f"receipt.{k}", c)
    for k,v in (company or {}).items():
        ok,c = _fuzzy(ocr_text,v)
        if ok and c>best[1]: best = (f"company.{k}", c)
    return best if best[1] >= thr else (None, 0.0)

def _db_cursor():
    try:
        from services.db.connection import db_cursor
        return db_cursor
    except Exception:
        return None

def _load_receipt(rid: str) -> Dict[str,Any]:
    dbc = _db_cursor()
    if not dbc: return {}
    with dbc() as cur:
        cur.execute("""
            SELECT gross_amount, net_amount, gross_amount_sek, net_amount_sek,
                   purchase_datetime, purchase_date, receipt_number,
                   payment_type, expense_type, currency, exchange_rate,
                   total_vat_25, total_vat_12, total_vat_6
              FROM unified_files WHERE id=%s
        """,(rid,))
        row = cur.fetchone()
        if not row: return {}
        cols = [d[0] for d in cur.description]
        return {k:v for k,v in dict(zip(cols,row)).items() if v is not None}

def _load_company(rid: str) -> Dict[str,Any]:
    dbc = _db_cursor()
    if not dbc: return {}
    with dbc() as cur:
        cur.execute("""
           SELECT c.name, c.orgnr, c.address, c.address2, c.zip, c.city, c.country,
                  c.phone, c.www, c.email
             FROM companies c JOIN unified_files u ON u.company_id=c.id
            WHERE u.id=%s
        """,(rid,))
        row = cur.fetchone()
        if not row: return {}
        cols = [d[0] for d in cur.description]
        return {k:v for k,v in dict(zip(cols,row)).items() if v is not None}

def run_box_enrichment(receipt_id: str, storage_dir: str | Path | None = None) -> Dict[str,Any]:
    base = Path(storage_dir or _storage_root())
    rdir = base / receipt_id
    raw_path = rdir / "ocr_boxes.json"
    if not raw_path.exists():
        logger.info("AI7: no ocr_boxes.json for %s", receipt_id)
        return {"success": True, "total_boxes": 0, "matched_boxes": 0, "unmatched_boxes": 0, "match_rate": 0.0}

    try:
        ocr_boxes = json.loads(raw_path.read_text(encoding="utf-8"))
        if not isinstance(ocr_boxes, list): ocr_boxes = []
    except Exception:
        return {"success": False, "error": "read_error", "total_boxes": 0, "matched_boxes": 0, "unmatched_boxes": 0, "match_rate": 0.0}

    receipt = _load_receipt(receipt_id)
    company = _load_company(receipt_id)

    enriched, matched = [], 0
    for b in ocr_boxes:
        txt = b.get("field") or ""
        mfield, mconf = _best_field(txt, receipt, company, thr=0.60)
        out = {
            "x": b.get("x"), "y": b.get("y"), "w": b.get("w"), "h": b.get("h"),
            "ocr_text": txt, "confidence": b.get("confidence"),
            "field": mfield or txt, "match_confidence": mconf if mfield else 0.0,
        }
        if mfield: matched += 1
        enriched.append(out)

    (rdir / "boxes.json").write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    total = len(enriched)
    return {
        "success": True, "total_boxes": total,
        "matched_boxes": matched, "unmatched_boxes": total-matched,
        "match_rate": (matched/total) if total else 0.0
    }
```

------

### 3.3 Kör AI7 efter AI4 (batch)

**Fil:** `backend/src/api/ai_processing.py` (AI4-grenen)

Leta upp efter `file_result["steps_completed"].append("AI4")` (runt **809**). Lägg till AI7-anropet **precis efter**:

```
@@
                             )
                             file_result["steps_completed"].append("AI4")
+                            # AI7: Enrichment efter AI4
+                            try:
+                                from services.box_enrichment import run_box_enrichment
+                                stats = run_box_enrichment(file_id)
+                                if stats.get("success"):
+                                    file_result["steps_completed"].append("AI7")
+                                    file_result["ai7"] = stats
+                                else:
+                                    file_result["ai7_error"] = stats.get("error", "unknown")
+                            except Exception as _e:
+                                logger.exception("AI7 error on %s", file_id)
```

------

### 3.4 Kör AI7 efter kreditkortsmatch

**Fil:** `backend/src/api/ai_processing.py`, funktion `match_credit_card_internal(...)` (runt **592–607**). Lägg till i slutet, efter att matchning/`_persist_credit_card_match(...)` lyckats:

```
@@ def match_credit_card_internal(req: CreditCardMatchRequest) -> CreditCardMatchResponse:
-    _persist_credit_card_match(
+    _persist_credit_card_match(
         req.file_id,
         result.credit_card_invoice_item_id,
         result.match_details,
         matched_amount,
     )
+    # AI7: Enrichment efter credit card-match
+    try:
+        from services.box_enrichment import run_box_enrichment
+        run_box_enrichment(req.file_id)
+    except Exception:
+        logger.exception("AI7 error after credit card match on %s", req.file_id)
     return result
```

> Detta täcker ditt “AI6”-behov i praktiken (kör enrichment efter kortflödet).

------

## 4) Tester att lägga till

**Fil (ny):** `backend/tests/test_box_enrichment.py`
 *(100% självgående; ingen DB krävs — vi monkeypatchar laddarna.)*

```
import json
from pathlib import Path
import pytest
import importlib

# Module under test
import backend.src.services.box_enrichment as be


@pytest.fixture
def temp_storage(tmp_path: Path):
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
    assert stats["matched_boxes"] >= 3
    assert 0.0 <= stats["match_rate"] <= 1.0

    out = (tmp_root / rid / "boxes.json").read_text(encoding="utf-8")
    boxes = json.loads(out)
    assert isinstance(boxes, list) and len(boxes) == 5

    fields = {b["field"] for b in boxes}
    assert "company.name" in fields
    assert "company.orgnr" in fields
    assert any(f.startswith("receipt.") for f in fields)

    random_box = next(b for b in boxes if b["ocr_text"] == "Random note")
    assert random_box["field"] == "Random note"
    assert random_box["match_confidence"] == 0.0


def test_handles_missing_ocr_file_gracefully(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    rid = "R-NO-OCR"

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

**Körning:**

```
pytest -q backend/tests/test_box_enrichment.py
```

------

## 5) Databas / schema / API / endpoints

- **DB-ändringar:** **Inga** krävs för AI7. AI7 läser strukturfält som redan finns i `unified_files` (+ join mot `companies`).
- **Prompter i AI-menyn:** Enligt din spec räcker det att **uppdatera AI3/AI4 systemprompt** (overlay-klara nycklar). **AI7 behöver ingen prompt.** 
- **API/Endpoints:**
  - `GET /receipts/<rid>/ocr/boxes` finns och blir korrekt när `boxes.json` börjar produceras.
  - **Lägg till** AI7-anrop i `ai_processing.py` (batch efter AI4 samt efter kreditkorts-match). Inga ändringar i response-schema krävs — men du kan (frivilligt) inkludera `ai7`-stats i batchsvaret som internt fält för enklare felsökning.
- **Path-tydlighet:** Se F1 — fungerar i praktiken, men överväg `_storage_root()` för läsbarhet.

------

## 6) Migrering av historiska kvitton (utan `ocr_boxes.json`)

**Mål:** overlay ska fungera även för gamla kvitton.

**Praktisk väg framåt (låg risk):**

1. Kör ett litet engångsskript (CLI eller admin-task) som för varje `<rid>`:
   - Om `ocr_boxes.json` **saknas** men `boxes.json` **finns** → kopiera `boxes.json` → `ocr_boxes.json`.
   - Kör `run_box_enrichment(<rid>)` för att skapa nya semantiska `boxes.json`.
2. Logga antal migrerade poster och ev. fel.

*(Vill du att jag skriver en minimal “management-kommandofil” för detta så kan jag leverera en version som anropar AI7 i batch över en lista med `rid`.)*

------

## 7) Slutlig checklista (ska vara grön)

-  `backend/src/services/ocr.py` skriver **`ocr_boxes.json`** (inte `boxes.json`).
-  `backend/src/services/box_enrichment.py` finns och fungerar.
-  `ai_processing.py` anropar AI7 **efter AI4** och **efter kreditkorts-match**.
-  `GET /receipts/<rid>/ocr/boxes` returnerar faktisk overlay (dvs. semantiskt `boxes.json`).
-  `pytest -q backend/tests/test_box_enrichment.py` passerar.
-  Smoke: Nytt kvitto → OCR endast `ocr_boxes.json`; efter AI4 → `boxes.json` finns, hover fungerar åt båda håll i preview-modalen.
-  Migration körd för historiska kvitton där `ocr_boxes.json` saknas.

------

## 8) Avvikelser mot den tidigare externa rapporten

- Påståendet att `_load_boxes()` “letar i fel katalog” **stämmer inte** i denna kodbas — den når `/data/storage/<rid>/boxes.json` via `.parent`-tricket. Det är dock **svårläst** och jag rekommenderar (`P1/P2`) att införa `_storage_root()` för tydlighet.
- Påståendet att “AI7 finns som explicit step i modellen” **stämmer inte** här; modellen listar `["AI1".."AI5"]`. Det är i linje med kravbilden (AI7 ska vara automatisk).

------

## 9) Referens till din AI7-spec

Denna rapport följer och verifierar mot din *AGENT BRIEF — AI7 Box Enrichment (Overlay Stability)*, bl.a. om **filnamn**, **körordning**, **kanoniska nycklar**, **verifiering** och **tester**. 

------

Vill du att jag paketera ovan patchar som **ren diff** (`.patch`/`git apply`-redo) och lägga till ett litet **migrationsskript** (`backend/ops/migrate_ocr_boxes.py`) som du kan köra med en lista av `rid`? Jag kan leverera båda direkt.