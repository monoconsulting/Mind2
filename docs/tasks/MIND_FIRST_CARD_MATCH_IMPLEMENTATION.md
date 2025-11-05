Here’s a complete, agent-ready implementation plan—based on a deep read of your attached codebase—showing exactly what to change to deliver **card-invoice↔receipt matching** the way you described.

---

# First-Class (FirstCard) ↔ Receipt Matching — Implementation Guide

## Goal

When the user clicks **Match** in **Kortmatchning**:

1. Each **invoice line** is matched against existing **receipts** by:

   * **Primary**: purchase date
   * **Secondary** (need one of): amount OR company/vendor
2. On a successful match, persist a row in:

   * `creditcard_receipt_matches (receipt_id, invoice_item_id, matched_amount, matched_at)`
3. Reflect the matched state in both domains:

   * `creditcard_invoice_items.matched = 1`
   * `unified_files.matched = 1` and `unified_files.credit_card_match = 1`
4. Update UI:

   * In **Kortmatchning** list, show **checkmark** instead of a cross for matched rows.
   * Add a new **“Kvitto”** column that opens the **preview modal** for the matched receipt.

This must work for **manual line matching** and **bulk/auto match**.

---

## What already exists (in your code)

### Database (✅ present)

* `creditcard_invoices_main`, `creditcard_invoice_items` (source items from FirstCard statement).
* `invoice_documents`, `invoice_lines` (normalized, app-level document & lines).
* `creditcard_receipt_matches` (target table we want to populate): created in `database/migrations/0010_expand_ai_schema.sql`.
* “matched flags” backfill: `database/migrations/0032_add_matched_flags.sql` adds `matched` to `creditcard_invoice_items` and `unified_files` and syncs with existing matches.

### Backend (Flask)

* **Blueprint**: `backend/src/api/reconciliation_firstcard.py` (`recon_bp`)
  Routes include:

  * `POST /reconciliation/firstcard/match`  → bulk/auto match **invoice_lines** (currently only updates `invoice_lines`, not `creditcard_receipt_matches`)
  * `PUT  /reconciliation/firstcard/lines/<int:line_id>` → manual match **invoice_lines** (same gap)
  * `GET  /reconciliation/firstcard/invoices/<invoice_id>` → returns `{ invoice, lines, items }`

    * `items` are **FirstCard** `creditcard_invoice_items` pulled via `creditcard_main_id` found in `invoice.metadata`
    * Already LEFT JOINs `creditcard_receipt_matches` to compute a **matched flag**, but does **not** return the matched `receipt_id`.

* `backend/src/api/ai_processing.py` already has safe helpers that **upsert** into `creditcard_receipt_matches` and flip flags in `unified_files` and `creditcard_invoice_items`. You can reuse this logic or mirror it.

### Frontend (React / Vite)

* File: `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`

  * Shows the **statement list**, **document lines** (from `invoice_lines`), and a compact **items** table (from `creditcard_invoice_items`).
  * **Document lines** table already shows a “Matchat kvitto” column with a **Preview** button that opens the receipt modal when `line.matched_receipt` exists (backend sends this).
  * The **items** table currently shows a “Matchad” checkbox but **no “Kvitto” column** and **no preview link** (backend doesn’t deliver the receipt ID for the item yet).

---

## Gaps to close

1. **Persistence gap**: Manual/auto matching endpoints update `invoice_lines`, but **don’t upsert** into `creditcard_receipt_matches`.
2. **Mapping gap**: Endpoints operate on `invoice_lines`. We also need to find the **corresponding** `creditcard_invoice_items.id` to write into `creditcard_receipt_matches.invoice_item_id`.
3. **Read gap (UI)**: `GET /reconciliation/firstcard/invoices/<id>` returns `items[]` with only a boolean `matched_flag`. It must also return the matched **receipt ID** so the frontend can show a **“Kvitto”** link.

---

## Design & Boundaries

* **Do not** touch modal layout/scrolling or column resizing of the **preview modal** (explicit requirement).
* **Do not** change existing route paths, payload shapes, or menu structure. Only **extend** responses where needed.
* **Idempotent matching**: Use `INSERT … ON DUPLICATE KEY UPDATE` for `creditcard_receipt_matches`.
* **Tie-break rule** for mapping an `invoice_line` to `creditcard_invoice_items`:

  1. Same `creditcard_main_id` (from the invoice metadata).
  2. **Date** must equal (`purchase_date` = `invoice_lines.transaction_date`).
  3. If multiple:

     * Prefer exact **amount** match (`amount_original` or `gross_amount`) within `±0.01`.
     * If still multiple, prefer **merchant_name** similarity (case-insensitive contains or Levenshtein fallback).
     * Last resort: lowest `line_no`.

---

## Backend changes (step-by-step, code-level)

### 1) Add a resolver to map invoice line → creditcard item

**File:** `backend/src/api/reconciliation_firstcard.py`
**Add near other helpers:**

```python
# --- NEW: helper to resolve cc item for an invoice line ---
def _resolve_creditcard_item_for_line(invoice_id: str, line_id: int) -> Optional[int]:
    """
    Given invoice_documents.id and invoice_lines.id, return the matching
    creditcard_invoice_items.id for the same credit card statement.
    Rules:
      - Same creditcard_main_id (from invoice_documents.metadata_json)
      - Same date (ci.purchase_date == il.transaction_date)
      - Prefer amount match within ±0.01 on (ci.amount_original or ci.gross_amount)
      - Prefer merchant similarity if needed
      - Finally, lowest ci.line_no
    """
    if db_cursor is None:
        return None

    creditcard_main_id: Optional[int] = None
    tx_date: Optional[str] = None
    amount: Optional[Decimal] = None
    merchant: Optional[str] = None

    try:
        with db_cursor() as cur:
            # 1) Pull creditcard_main_id from invoice metadata + line basics
            cur.execute("""
                SELECT d.metadata_json, l.transaction_date, l.amount, COALESCE(l.merchant_name, l.description)
                  FROM invoice_documents AS d
                  JOIN invoice_lines AS l ON l.invoice_id = d.id
                 WHERE d.id = %s AND l.id = %s
            """, (invoice_id, line_id))
            row = cur.fetchone()
            if not row:
                return None
            meta_json, tx_date, amount, merchant = row
            if isinstance(meta_json, str):
                try:
                    meta = json.loads(meta_json) if meta_json else {}
                except Exception:
                    meta = {}
            else:
                meta = meta_json or {}
            creditcard_main_id = meta.get("creditcard_main_id")

            if not creditcard_main_id or not tx_date:
                return None

            # 2) Candidate items on same statement and same date
            cur.execute("""
                SELECT ci.id, ci.line_no, ci.purchase_date,
                       COALESCE(ci.amount_original, ci.gross_amount) AS amt,
                       COALESCE(ci.merchant_name, '') AS merch
                  FROM creditcard_invoice_items AS ci
                 WHERE ci.main_id = %s AND ci.purchase_date = %s
            """, (creditcard_main_id, tx_date))
            candidates = cur.fetchall() or []
    except Exception:
        return None

    if not candidates:
        return None

    def _dec(x):
        try:
            return Decimal(str(x)) if x is not None else None
        except Exception:
            return None

    amount = _dec(amount)
    m = (merchant or "").strip().lower()

    # 3) Score candidates
    scored = []
    for cid, line_no, pdate, amt, merch in candidates:
        amt = _dec(amt)
        merch_l = (merch or "").strip().lower()
        amount_ok = (amount is not None and amt is not None and abs(amt - amount) <= Decimal("0.01"))
        merchant_ok = bool(m and merch_l and (m in merch_l or merch_l in m))
        score = 0
        if amount_ok:
            score += 10
        if merchant_ok:
            score += 5
        # Date equals by query condition
        score += 3
        scored.append((score, line_no or 999999, cid))

    scored.sort(key=lambda t: (-t[0], t[1]))
    best = scored[0] if scored else None
    return int(best[2]) if best and best[0] >= 3 else None  # require at least date+one more
```

### 2) Manual match should upsert `creditcard_receipt_matches`

**File:** `backend/src/api/reconciliation_firstcard.py`
**Patch inside** `update_line_match(line_id: int)`

Find the success branch after `transition_line_status_and_link(...)` and **before** returning `{"ok": True}`. Insert:

```python
# --- NEW: also persist match in creditcard_receipt_matches ---
try:
    with db_cursor() as cur2:
        # Resolve cc item id for this invoice line
        cur2.execute("SELECT invoice_id FROM invoice_lines WHERE id=%s", (line_id,))
        row = cur2.fetchone()
        invoice_id = row[0] if row else None

        cc_item_id = _resolve_creditcard_item_for_line(invoice_id, line_id) if invoice_id else None
        if cc_item_id is not None:
            # Write/refresh match row (idempotent)
            cur2.execute(
                """
                INSERT INTO creditcard_receipt_matches (receipt_id, invoice_item_id, matched_amount)
                VALUES (%s, %s, (
                    SELECT COALESCE(gross_amount, gross_amount_sek, net_amount_sek, net_amount_original, gross_amount_original)
                      FROM unified_files WHERE id=%s
                ))
                ON DUPLICATE KEY UPDATE matched_amount = VALUES(matched_amount), matched_at = NOW()
                """,
                (new_file_id, cc_item_id, new_file_id),
            )
            # Flip flags
            cur2.execute("UPDATE creditcard_invoice_items SET matched=1, updated_at=NOW() WHERE id=%s", (cc_item_id,))
            cur2.execute(
                "UPDATE unified_files SET matched=1, credit_card_match=1, updated_at=NOW() WHERE id=%s",
                (new_file_id,),
            )
except Exception:
    # non-fatal for manual match; history and line link already done
    pass
```

> **Why here?**
> `PUT /lines/<id>` is what the UI uses when you click **Matcha** on a candidate; this is the right place to also persist into `creditcard_receipt_matches` and update flags.

### 3) Bulk/auto match must also upsert matches

**File:** `backend/src/api/reconciliation_firstcard.py`
**Patch inside** `firstcard_match()` inside the loop where a line is successfully matched (right after `transition_line_status_and_link(...)` and history insert). Insert:

```python
# --- NEW: also persist match in creditcard_receipt_matches for bulk ---
try:
    with db_cursor() as cur2:
        # Resolve creditcard item for this invoice line
        cc_item_id = _resolve_creditcard_item_for_line(document_id, line_id)
        if cc_item_id is not None:
            cur2.execute(
                """
                INSERT INTO creditcard_receipt_matches (receipt_id, invoice_item_id, matched_amount)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE matched_amount = VALUES(matched_amount), matched_at = NOW()
                """,
                (file_id, cc_item_id, target_amount),
            )
            cur2.execute("UPDATE creditcard_invoice_items SET matched=1, updated_at=NOW() WHERE id=%s", (cc_item_id,))
            cur2.execute(
                "UPDATE unified_files SET matched=1, credit_card_match=1, updated_at=NOW() WHERE id=%s",
                (file_id,),
            )
except Exception:
    pass
```

Notes:

* `document_id` is the `invoice_documents.id` you already have in `firstcard_match`.
* `file_id` and `target_amount` are already computed in that loop.

### 4) Return the matched receipt for **items[]** (so the UI can show the “Kvitto” column)

**File:** `backend/src/api/reconciliation_firstcard.py`
**Inside** `invoice_detail(invoice_id)`, you already select the item rows:

```sql
SELECT ci.id, ci.line_no, ci.purchase_date, ci.merchant_name, ci.merchant_city,
       ci.amount_original, ci.net_amount, ci.vat_rate, ci.currency_original,
       CASE WHEN crm.invoice_item_id IS NOT NULL THEN 1 ELSE COALESCE(ci.matched, 0) END AS matched_flag
  FROM creditcard_invoice_items AS ci
 LEFT JOIN creditcard_receipt_matches AS crm ON crm.invoice_item_id = ci.id
 WHERE ci.main_id = %s
```

**Extend the SELECT** to include `crm.receipt_id`:

```sql
       , crm.receipt_id
```

**And in the Python loop**, build a `matched_receipt` object when `receipt_id` exists:

```python
# after fetching item_rows
for (
    item_id, line_no, purchase_date, merchant_name, merchant_city,
    amount_original, net_amount, vat_rate, currency_original,
    matched_flag, matched_receipt_id  # <-- NEW
) in item_rows:
    item_payload = {
        "id": int(item_id),
        "line_no": int(line_no) if line_no is not None else None,
        "purchase_date": purchase_date.isoformat() if hasattr(purchase_date, "isoformat") else purchase_date,
        "merchant_name": merchant_name,
        "merchant_city": merchant_city,
        "amount_original": float(amount_original) if amount_original is not None else None,
        "net_amount": float(net_amount) if net_amount is not None else None,
        "vat_rate": float(vat_rate) if vat_rate is not None else None,
        "currency_original": currency_original,
        "matched": bool(matched_flag),
    }
    if matched_receipt_id:
        item_payload["matched_receipt"] = {
            "file_id": matched_receipt_id
        }
    items.append(item_payload)
```

**Result**: `GET /reconciliation/firstcard/invoices/<id>` will now return, for each `items[]`, an optional `matched_receipt.file_id` that the frontend can use to open the preview modal.

> You already return a similar `matched_receipt` for **document lines**—this mirrors that structure for **items**.

---

## Frontend changes (precise edits)

**File:** `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`

### 5) Add a **“Kvitto”** column to the **items** table

Find the **items** table header around the “Matchad” column (≈ lines 800–830 in your current file). **Add one column** before “Matchad”:

```jsx
// header
<th className="px-4 py-3">Kvitto</th>
<th className="px-4 py-3 text-center">Matchad</th>
```

And in the corresponding **row** cells (≈ lines 834–860), **insert a new `<td>`** right before the “Matchad” `<td>`:

```jsx
<td className="px-4 py-3">
  {item.matched && item.matched_receipt?.file_id ? (
    <button
      type="button"
      className="btn btn-text btn-sm"
      onClick={() => openReceiptPreview(item.matched_receipt.file_id)}
    >
      Förhandsgranska
    </button>
  ) : (
    <span className="text-gray-500">-</span>
  )}
</td>
```

> **No layout changes** to the preview modal. We only add a link that calls your existing `openReceiptPreview(fileId)`.

### 6) No other UI changes needed

* The **checkmark** in the items table is already driven by the `matched` flag; back-end updates will flip it automatically after refresh.
* The **document lines** table already supports “Matchat kvitto → Förhandsgranska”. It will continue to work.

---

## Testing checklist

### Database quick checks (MySQL)

```sql
-- 1) An item matched manually should create or update a row here:
SELECT * FROM creditcard_receipt_matches ORDER BY matched_at DESC LIMIT 10;

-- 2) Flags should flip:
SELECT id, matched FROM creditcard_invoice_items WHERE id = <the-resolved-item-id>;
SELECT id, matched, credit_card_match FROM unified_files WHERE id = '<receipt_uuid>';

-- 3) Items endpoint should now include matched_receipt:
--    Call: GET /ai/api/reconciliation/firstcard/invoices/<invoice_id>
--    Verify: items[].matched_receipt.file_id exists on matched rows
```

### API flow

1. Upload a FirstCard invoice (PDF): `/ai/api/reconciliation/firstcard/upload-invoice`
2. Open **Kortmatchning**, pick the statement, look at **document lines**.
3. Click **Visa kandidater → Matcha** on a line.

   * Verify:

     * Row flips to matched.
     * `creditcard_receipt_matches` contains a row with `(receipt_id, invoice_item_id)` for the mapped item.
     * Items table shows **Kvitto → Förhandsgranska**.
4. Use **Matcha (auto)** (POST `/reconciliation/firstcard/match`) and verify same DB/UI outcomes.

---

## Edge cases & decisions

* **Multiple candidates on same day**: the resolver favors **amount** match, then **merchant** similarity, then lowest `line_no`.
* **Amounts with FX**: we compare invoice line amount to `amount_original/gross_amount` on the CC item (both are in statement currency).
* **Partial data**: If date is missing, we **do not** write a `creditcard_receipt_matches` row (line remains matched to file for `invoice_lines`, but items table won’t show a “Kvitto”).
* **Idempotency**: Re-matching the same line updates the existing `creditcard_receipt_matches` row (`ON DUPLICATE KEY UPDATE`).
* **No changes** to preview modal layout, scroll, or column sizing.

---

## Summary of exact files to touch

* **Backend**

  * `backend/src/api/reconciliation_firstcard.py`

    * Add `_resolve_creditcard_item_for_line(...)`
    * Extend `update_line_match(...)` to upsert into `creditcard_receipt_matches` and flip flags
    * Extend `firstcard_match(...)` similarly
    * Extend `invoice_detail(...)` items query & payload to include `matched_receipt.file_id`
* **Frontend**

  * `main-system/app-frontend/src/ui/pages/CompanyCard.jsx`

    * Add “Kvitto” column to the **items** table and a **Förhandsgranska** button when `item.matched_receipt.file_id` exists

That’s it—follow the patches above line-by-line and you’ll have the full matching flow persisting to `creditcard_receipt_matches`, updating the flags, flipping the checkmarks, and opening previews from the new **Kvitto** column without touching the modal layout.
