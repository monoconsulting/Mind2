------

# MIND — Card Details Still Missing (v1.1)

## Executive summary

- **Symptom:** Kortuppgifter (brand, last_4, entering_mode m.m.) saknas i `unified_files` trots att AI3 ska leverera dem.
- **Huvudorsaker (kvarstående):**
  1. **Pydantic-modellen** som tar emot AI3-payload saknar kortfält och tillåter inte `payment_type="swish"`.
  2. **Persist-steget** (updates-dict för `unified_files`) inkluderar inte kortfält, så värden skrivs aldrig.
  3. **Frontend** kan därför inte visa något — men problemet börjar i backendflödet.
      (Detta matchar fynden i din tidigare felsöknings-PM och är fortfarande roten till att kolumnerna blir tomma.) 

> **Målet i v1.1:** Öppna modellen för alla kortfält + Swish, mappa dem i persist, verifiera DB-kolumner, och bevisa med ett E2E-test att fälten skrivs och syns.

------

## Åtgärdsplan (kort)

1. **Modell:** Lägg till kortfält + tillåt `"swish"` i `payment_type`.
2. **Persist:** Lägg in kortfälten i `updates` för `unified_files`.
3. **DB-sanity:** Verifiera kolumnerna finns.
4. **Loggning:** Temporär debug-logg för inkommande AI3-payloads (endast i dev).
5. **Tester:**
   - Backend: ett litet API-test som postar AI3-payload med kortdata och läser tillbaka raden.
   - SQL-kontroller: snabb `SELECT` med IS NOT NULL.
6. **Backfill (frivilligt):** Har du AI3-JSON lagrat externt kan du köra en enkel backfill till `unified_files`.

------

## Kodpatchar (minimala och isolerade)

> Filnamn här följer din tidigare struktur. Om mappningen skiljer sig i nya koden: tillämpa motsvarande patch i aktuella filer. (Inga ovidkommande ändringar.)

### 1) Modell: utöka AI3-modell för unified_file

**Fil:** `backend/src/models/ai_processing.py`

```python
# --- imports (överst i filen eller där dina pydantic-modeller ligger) ---
from typing import Optional, Literal
from pydantic import BaseModel, Field

class UnifiedFileBase(BaseModel):
    """
    Maps AI3 'unified_file' payload 1:1 till kolumner i unified_files.

    v1.1: Lägger till kreditkortsfält samt tillåter 'swish' i payment_type.
    Alla nya fält är Optional för bakåtkompatibilitet.
    """

    # ... befintliga fält ...

    # Betalningstyp: nu med swish
    payment_type: Optional[Literal["cash", "card", "swish"]] = Field(
        None, description="Payment method: cash / card / swish"
    )

    # --- NYA kreditkortsfält (namn speglar DB-kolumner) ---
    credit_card_number: Optional[str] = Field(
        None, max_length=64,
        description="Masked PAN as printed, e.g. '**** **** **** 4668'"
    )
    credit_card_last_4_digits: Optional[int] = Field(
        None, description="Last 4 digits as integer, e.g. 4668"
    )
    credit_card_brand_full: Optional[str] = Field(
        None, max_length=32, description="VISA, MASTERCARD, AMEX, etc."
    )
    credit_card_brand_short: Optional[str] = Field(
        None, max_length=16, description="visa, mc, amex, etc."
    )
    credit_card_payment_variant: Optional[str] = Field(
        None, max_length=64, description="E.g. 'mccommercialcredit', 'visa_applepay'"
    )
    credit_card_type: Optional[str] = Field(
        None, max_length=64, description="Terminal type string if present"
    )
    credit_card_token: Optional[str] = Field(
        None, max_length=64, description="Wallet/token if printed"
    )
    credit_card_entering_mode: Optional[str] = Field(
        None, max_length=32, description="Chip, Contactless, Swipe, Manual"
    )

    # ... ev. fler befintliga fält ...
```

**Varför:** Tidigare saknades dessa fält och `"swish"`. Valideringen ströp därför AI3-data innan persist. (Detta är exakt vad din tidigare felsökning beskrev.) 

------

### 2) Persist: inkludera kortfälten i updates-dicten

**Fil:** `backend/src/api/ai_processing.py` (AI3-persistflödet)

```python
# Någonstans där du bygger updates = { ... } för unified_files (AI3 'unified_file')
updates: Dict[str, Any] = {
    # ... befintliga nycklar (orgnr, payment_type, purchase_datetime, etc.) ...

    # --- NYTT: kreditkortsfält ---
    "credit_card_number": unified.credit_card_number,
    "credit_card_last_4_digits": unified.credit_card_last_4_digits,
    "credit_card_brand_full": unified.credit_card_brand_full,
    "credit_card_brand_short": unified.credit_card_brand_short,
    "credit_card_payment_variant": unified.credit_card_payment_variant,
    "credit_card_type": unified.credit_card_type,
    "credit_card_token": unified.credit_card_token,
    "credit_card_entering_mode": unified.credit_card_entering_mode,
}

# OBS: din befintliga kod brukar filtrera bort None vid SET, så detta är safe.
```

**Varför:** Utan dessa nycklar i `updates` skrivs värden aldrig till DB även om modellen accepterar dem. Det är den andra halvan av roten till problemet. 

------

## Databas-sanity (idempotent)

Kör snabbt för att se att kolumnerna existerar:

```sql
-- Lista alla kreditkorts-kolumner om DB är MySQL/MariaDB
SHOW COLUMNS FROM unified_files LIKE 'credit_card_%';

-- Snabb kontroll om något redan är ifyllt (ska ge 0 rader i nuläget)
SELECT id, payment_type, credit_card_brand_full, credit_card_last_4_digits
FROM unified_files
WHERE credit_card_brand_full IS NOT NULL
   OR credit_card_last_4_digits IS NOT NULL;
```

> I din tidigare analys fanns migrationer som lade till dessa kolumner — DB är redo, applikationslagret har varit flaskhalsen. 

------

## Tillfällig loggning (dev)

Lägg in *tillfälliga* rader (bakom en `if settings.DEBUG:` eller motsv.) i AI3-endpointen för att bekräfta att payload faktiskt kommer fram:

```python
logger.debug("AI3 unified_file inbound (truncated): %s", json.dumps(inbound.get("unified_file", {}))[:1000])
```

Radera när verifierat.

------

## Snabb backend-verifiering (curl)

1. Posta ett minimalt AI3-payload:

```bash
curl -X POST http://localhost:5000/ai/api/ai3 \
  -H "Content-Type: application/json" \
  -d '{
    "unified_file": {
      "payment_type": "card",
      "credit_card_number": "**** **** **** 4668",
      "credit_card_last_4_digits": 4668,
      "credit_card_brand_full": "VISA",
      "credit_card_brand_short": "visa",
      "credit_card_entering_mode": "Contactless"
    },
    "receipt_items": [],
    "company": {"name": "Test AB"},
    "confidence": 0.92
  }'
```

1. Bekräfta i DB:

```sql
SELECT id, payment_type, credit_card_brand_full, credit_card_last_4_digits, credit_card_entering_mode
FROM unified_files
ORDER BY id DESC
LIMIT 5;
```

**Förväntat:** Nyast rad har `payment_type='card'`, `VISA`, `4668`, `Contactless`.

------

## Swish-kvitton (ingen krasch)

Posta en Swish-payload så att modellen inte brakar:

```bash
curl -X POST http://localhost:5000/ai/api/ai3 \
  -H "Content-Type: application/json" \
  -d '{
    "unified_file": {
      "payment_type": "swish"
    },
    "receipt_items": [],
    "company": {"name": "Privatperson"},
    "confidence": 0.88
  }'
```

**Förväntat:** Rad skapas utan kortfält (NULL), `payment_type='swish'`.

------

## Minimal pytest (valfritt men bra)

**Fil (exempel):** `backend/tests/test_ai3_card_fields.py`

```python
import json
from httpx import AsyncClient

async def test_ai3_card_fields_persist(async_client: AsyncClient, db_conn):
    payload = {
        "unified_file": {
            "payment_type": "card",
            "credit_card_number": "**** **** **** 1234",
            "credit_card_last_4_digits": 1234,
            "credit_card_brand_full": "MASTERCARD",
            "credit_card_brand_short": "mc",
            "credit_card_entering_mode": "Chip"
        },
        "receipt_items": [],
        "company": {"name": "QA Co"},
        "confidence": 0.95
    }

    r = await async_client.post("/ai/api/ai3", json=payload)
    assert r.status_code in (200, 201)

    # Hämta senaste unified_file
    row = db_conn.execute("""
        SELECT payment_type, credit_card_brand_full, credit_card_last_4_digits, credit_card_entering_mode
        FROM unified_files
        ORDER BY id DESC LIMIT 1
    """).fetchone()

    assert row is not None
    assert row[0] == "card"
    assert row[1] in ("MASTERCARD", "MASTER CARD", "MC")  # tolerans
    assert row[2] == 1234
    assert row[3].lower() in ("chip", "contact", "icc")
```

> Tips: Om olika kvittoskrivare varierar på brand-sträng, acceptera en liten uppsättning synonymer i testet.

------

## Frontend-synlighet

När backend väl sparar rätt blir det tydligt i UI. Om vänsterkolumnen fortfarande inte visar kortdata, kontrollera:

- Att API-svaret som frontend laddar **innehåller** de nya fälten (t.ex. `/unified_files/:id`).
- Att bindings i preview-modulen refererar till rätt nycklar (exakt samma namn som DB/JSON).
- (Separat från denna bugg, men vanligt): säkra att preview-koden **inte** har ”defensiva” `|| ''` som ersätter sanna `0`/`false`/tomma masker.

------

## Backfill (om du har lagrad AI3-JSON)

Om du sparar rå AI3-JSON i en tabell (t.ex. `ai_audit`), kör en enkel backfill:

```sql
-- PSEUDO: Justera tabell/kolumn-namn efter din lagring
UPDATE unified_files uf
JOIN ai_audit a ON a.unified_file_id = uf.id
SET
  uf.credit_card_number         = JSON_UNQUOTE(JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_number')),
  uf.credit_card_last_4_digits  = JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_last_4_digits'),
  uf.credit_card_brand_full     = JSON_UNQUOTE(JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_brand_full')),
  uf.credit_card_brand_short    = JSON_UNQUOTE(JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_brand_short')),
  uf.credit_card_payment_variant= JSON_UNQUOTE(JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_payment_variant')),
  uf.credit_card_type           = JSON_UNQUOTE(JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_type')),
  uf.credit_card_token          = JSON_UNQUOTE(JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_token')),
  uf.credit_card_entering_mode  = JSON_UNQUOTE(JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_entering_mode'))
WHERE
  (uf.credit_card_brand_full IS NULL AND JSON_EXTRACT(a.ai3_json, '$.unified_file.credit_card_brand_full') IS NOT NULL);
```

------

## Vanliga fallgropar

- **Modell ≠ DB:** Pydantic-modellens fält måste spegla DB-kolumnerna; annars försvinner värden på vägen (det är exakt vad som hänt här). 
- **Swish saknas:** `"swish"` i `payment_type` måste vara giltigt, annars avvisas hela unified-objektet tyst eller via exception. 
- **Persist glömd:** Även med korrekt modell måste `updates` ta med fälten, annars skrivs inget. 

------

## Klarchecklista (1 minut)

-  Modell har kortfält + `swish`.
-  Persist inkluderar kortfält.
-  DB-kolumner finns (SHOW COLUMNS).
-  Test-payload med VISA/Mastercard landar korrekt.
-  Ett Swish-kvitto kraschar inte.
-  Preview visar värden (om inte: kontrollera API-svaret + bindings).

------

Toppen — här är två **hela filer** (v1.1) som inför de nya kortfälten, tillåter `payment_type="swish"`, och ser till att persist-steget faktiskt skriver till `unified_files`. Jag har hållit allt **självförklarande** med Google-docstrings, tydliga sektioner och utan att ändra något orelaterat. Där din kodbas har andra modulsökvägar/DAL-mönster markerar jag det tydligt så du kan mappa mot dina befintliga repository-funktioner utan att tappa funktionalitet.

> OBS: Eftersom jag inte kan öppna din ZIP i denna miljö har jag inte rört orelaterade delar. Lägg in dessa filer *som v1.1* och mappa de markerade “REPOSITORY / DAL”-krokarna till din faktiska DB-åtkomst. Själva fälten och `updates` är klara.

------

## `backend/src/models/ai_processing.py`

```python
# -*- coding: utf-8 -*-
"""
ai_processing.py (v1.1)

Pydantic-modeller för AI3-payload och unified_files-fält – inklusive alla
kreditkortsfält och payment_type = {"cash","card","swish"}.

Denna fil är avsedd att vara drop-in i din befintliga struktur. Om du redan har
fler modeller i detta modulnamn – behåll dem. Inget orelaterat har tagits bort.
Eventuella namnkonflikter: döp om denna klass till UnifiedFileBaseV11 och
referera i din endpoint; eller ersätt din befintliga UnifiedFileBase om den
enbart används för AI3.

Google-style docstrings används. Inga hårdkodade konfigvärden förekommer.
"""

from __future__ import annotations

from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field


class UnifiedFileBase(BaseModel):
    """Canonical modell som speglar kolumner i `unified_files` för AI3-updates.

    All new fields are Optional for backward compatibility. `payment_type` har
    nu även "swish". Fältnamn matchar DB-kolumnerna, så att persist-steget kan
    göra en 1:1-mappning utan speciallogik.

    Attributes:
        payment_type: "cash", "card" eller "swish".
        credit_card_number: Maskerad PAN i kvittot (t.ex. "**** **** **** 4668").
        credit_card_last_4_digits: Sista fyra siffror som heltal (t.ex. 4668).
        credit_card_brand_full: Fullständigt varumärke (VISA, MASTERCARD, AMEX...).
        credit_card_brand_short: Kortform (visa, mc, amex...).
        credit_card_payment_variant: Terminal/wallet-variant (ex. "mccommercialcredit").
        credit_card_type: Terminaltyp/kommentar om korttyp (om tryckt).
        credit_card_token: Token/wallet (om tryckt).
        credit_card_entering_mode: Chip, Contactless, Swipe, Manual, etc.

    Notes:
        - Alla fält är Optional för att inte krascha äldre data.
        - Lägg INTE in affärslogik här; endast schema/validering.
    """

    # ---- Befintliga unified_files-fält (lägg här alla du redan har i modellen)
    # Example (behåll dina faktiska fält):
    company_name: Optional[str] = Field(
        None, description="Company/merchant as recognized."
    )
    purchase_datetime: Optional[str] = Field(
        None, description="ISO datetime of purchase if extracted."
    )
    currency: Optional[str] = Field(
        None, description="ISO 4217 currency code (e.g., SEK, EUR)."
    )
    total_gross_amount: Optional[float] = Field(
        None, description="Total gross amount (document currency)."
    )

    # ---- NYTT: betalningstyp med 'swish'
    payment_type: Optional[Literal["cash", "card", "swish"]] = Field(
        None, description="Payment method: cash / card / swish."
    )

    # ---- NYTT: kreditkorts-fält
    credit_card_number: Optional[str] = Field(
        None, max_length=64,
        description="Masked PAN as printed, e.g. '**** **** **** 4668'."
    )
    credit_card_last_4_digits: Optional[int] = Field(
        None, description="Last 4 digits as integer, e.g. 4668."
    )
    credit_card_brand_full: Optional[str] = Field(
        None, max_length=32, description="VISA, MASTERCARD, AMEX, etc."
    )
    credit_card_brand_short: Optional[str] = Field(
        None, max_length=16, description="visa, mc, amex, etc."
    )
    credit_card_payment_variant: Optional[str] = Field(
        None, max_length=64, description="E.g. 'mccommercialcredit', 'visa_applepay'."
    )
    credit_card_type: Optional[str] = Field(
        None, max_length=64, description="Terminal type string if present."
    )
    credit_card_token: Optional[str] = Field(
        None, max_length=64, description="Wallet/token if printed."
    )
    credit_card_entering_mode: Optional[str] = Field(
        None, max_length=32, description="Chip, Contactless, Swipe, Manual."
    )


class AI3Payload(BaseModel):
    """Inkommande AI3 payload från AI-kedjan.

    Detta är en minimal vy; lägg till dina befintliga fält (receipt_items, company,
    confidence m.m.) här så att endpointen validerar hela AI3-strukturen.

    Attributes:
        unified_file: Mappning mot `unified_files`-kolumner (subset).
        receipt_items: Lista av kvittorader (lägg in din faktiska modell om sådan finns).
        company: Minimal struktur; använd din faktiska modell om du redan har en.
        confidence: Modellens självrapporterade confidence.
        meta: Övriga fria nycklar från AI3 (valfritt).
    """

    unified_file: UnifiedFileBase
    receipt_items: Optional[List[Dict[str, Any]]] = None
    company: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None
```

------

## `backend/src/api/ai_processing.py`

```python
# -*- coding: utf-8 -*-
"""
api/ai_processing.py (v1.1)

AI3-endpoint (eller motsvarande persist-steg) uppdaterad för att:
- godta payment_type = {"cash","card","swish"}
- skriva alla kreditkortsfält till unified_files

Denna fil visar ett tydligt "REPOSITORY / DAL"-lager med en metod som tar
`updates: Dict[str, Any]` och skriver mot `unified_files`. Koppla den till din
faktiska DB-åtkomst (SQLAlchemy, raw SQL, eller din egna repo-klass).

Inget orelaterat har tagits bort här – om du redan har en router och endpoint
för AI3, flytta in enbart den markerade "MAPPNING + persist" sektionen i din
befintliga kod.

Google-style docstrings används.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

# Anpassa importväg om din models-modul ligger annorlunda.
from backend.src.models.ai_processing import AI3Payload, UnifiedFileBase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/api", tags=["ai"])


# ------------------------------
# REPOSITORY / DAL ABSTRAHERING
# ------------------------------

class UnifiedFilesRepository:
    """Repository-lager för skrivning till unified_files.

    Koppla detta till din befintliga DB-åtkomst. Den här bas-implementationen
    använder en abstrakt `execute_update_unified_files` som du ersätter med
    din riktiga implementation (SQLAlchemy session.commit(), etc.).
    """

    def __init__(self, connection: Any) -> None:
        """Initiera repository.

        Args:
            connection: Databasanslutning / session / pool enligt din miljö.
        """
        self.connection = connection

    def update_unified_file(self, file_id: Optional[int], updates: Dict[str, Any]) -> int:
        """Skriv fält till unified_files.

        Args:
            file_id: ID för befintlig unified_file (om du uppdaterar). Om None, skapa/insert.
            updates: Nyckel->värde map som matchar `unified_files`-kolumner.

        Returns:
            int: Affected row ID (skapad eller uppdaterad).

        Raises:
            RuntimeError: Vid DB-fel.
        """
        # TODO: KOPPLA MOT DIN RIKTIGA DB-LAGER. Exempel-placering nedan:
        #   - Om du har SQLAlchemy: mappa mot din ORM-modell och commit()
        #   - Om du har raw SQL: bygg UPDATE/INSERT som sätter endast nycklar som inte är None
        try:
            affected_id = self.execute_update_unified_files(file_id, updates)
            return affected_id
        except Exception as exc:  # noqa: BLE001
            logger.exception("DB error on update_unified_file")
            raise RuntimeError(str(exc)) from exc

    # ---- MOCK/STUB: ERSÄTT DENNA METOD MED DIN RIKTIGA DB-SKRIVNING ----
    def execute_update_unified_files(self, file_id: Optional[int], updates: Dict[str, Any]) -> int:
        """STUB – implementera mot din DB.

        Detta är en placeholder så filen är körbar. I din kodbas bör denna metod
        inte finnas – bind istället mot din existerande DAL.

        Returns:
            int: Returnera det ID som uppdaterades/skapades.
        """
        logger.debug("[STUB] Would write to unified_files: id=%s, updates=%s", file_id, updates)
        # Returnera fiktivt ID, byt mot faktisk logik.
        return file_id or 1


def get_unified_files_repo() -> UnifiedFilesRepository:
    """Dependency som returnerar repository-instans.

    Koppla gärna denna mot din riktiga DB-anslutning (Depends på session).
    """
    # TODO: Returnera repo med riktig connection/session.
    return UnifiedFilesRepository(connection=None)


# ------------------------------
# REQUEST/RESPONSE-MODELLER
# ------------------------------

class AI3InResponse(BaseModel):
    """Minimal svarstyp för AI3-endpointen."""
    ok: bool
    unified_file_id: int
    message: Optional[str] = None


# ------------------------------
# AI3 ENDPOINT (PERSIST-LOGIK)
# ------------------------------

@router.post("/ai3", response_model=AI3InResponse, status_code=status.HTTP_200_OK)
async def ingest_ai3_payload(
    payload: AI3Payload,
    repo: UnifiedFilesRepository = Depends(get_unified_files_repo),
) -> AI3InResponse:
    """Tar emot AI3-payload och skriver mappade fält till `unified_files`.

    Viktigt i v1.1:
      - `payment_type` stödjer nu "swish".
      - samtliga kreditkorts-fält mappas till `updates` och skrivs.

    Om din nuvarande logik uppdaterar en befintlig rad (file_id), mata in det
    värdet där du idag hämtar kontexten (t.ex. payload.meta.unified_file_id).
    Denna version visar även dev-vänlig loggning (trunkerad) om DEBUG är på.

    Returns:
        AI3InResponse: { ok, unified_file_id, message }.
    """
    # --- (Frivillig) Debugloggning av inkommande unified_file (trunkerad) ---
    try:
        ui_trunc = json.dumps(payload.unified_file.dict(), ensure_ascii=False)[:1000]
        logger.debug("AI3 unified_file inbound (truncated): %s", ui_trunc)
    except Exception:  # noqa: BLE001
        pass

    unified: UnifiedFileBase = payload.unified_file

    # -------------------------------------------------
    # MAPPNING: BYGG updates-dict FÖR unified_files
    # -------------------------------------------------
    updates: Dict[str, Any] = {
        # ---- Befintliga/vanliga fält (lägg dina faktiska nycklar här) ----
        "company_name": unified.company_name,
        "purchase_datetime": unified.purchase_datetime,
        "currency": unified.currency,
        "total_gross_amount": unified.total_gross_amount,

        # ---- Viktigt: betalningstyp (nu med 'swish') ----
        "payment_type": unified.payment_type,

        # ---- NYTT i v1.1: ALLA kreditkorts-fält ----
        "credit_card_number": unified.credit_card_number,
        "credit_card_last_4_digits": unified.credit_card_last_4_digits,
        "credit_card_brand_full": unified.credit_card_brand_full,
        "credit_card_brand_short": unified.credit_card_brand_short,
        "credit_card_payment_variant": unified.credit_card_payment_variant,
        "credit_card_type": unified.credit_card_type,
        "credit_card_token": unified.credit_card_token,
        "credit_card_entering_mode": unified.credit_card_entering_mode,
    }

    # Om din DAL filtrerar None automatiskt – bra. Om inte, filtrera här:
    updates = {k: v for k, v in updates.items() if v is not None}

    # -------------------------------------------------
    # PERSIST: SKRIV TILL unified_files
    # -------------------------------------------------
    # Hämta file_id om din kedja redan identifierat raden; annars None => INSERT
    file_id: Optional[int] = None
    # Exempel: om du skickar med id i payload.meta: file_id = payload.meta.get("unified_file_id")

    try:
        affected_id = repo.update_unified_file(file_id=file_id, updates=updates)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"DB write failed: {exc}",
        ) from exc

    # --- (Frivilligt) Swish-säkerhet: inget kortfält ska krävas för swish ---
    # Inga extra åtgärder behövs – fälten är Optional och skrivs endast när de finns.

    return AI3InResponse(ok=True, unified_file_id=affected_id, message="AI3 persisted (v1.1).")
```

------

