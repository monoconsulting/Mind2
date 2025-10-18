

# Task 5.1 — Preview Modal: Field Population & Item Name Fix

## Objective

Fix the **Preview Modal** so that:

1. Left column (Grunddata / Företagsinformation), **Betalningstyp**, and **Belopp** populate correctly.
2. Item descriptions no longer merge article IDs with names (e.g., “K57. Halstrad Lax Sushi 12 bitar”).
3. **Absolutely NO** UI resizing or scrolling changes to the three columns.

## Non-UI Constraints (Hard Prohibition)

- **Do not** alter any layout/styling classes, widths, paddings, margins, flex/grid settings, column proportions, or scroll behavior of the preview modal columns.
- **Do not** add/remove class names that could affect layout.
- **Do not** introduce CSS changes or Tailwind class edits in this task.
- Any deviation fails the task.

------

## Implementation Summary

- Normalize header data from backend (`unified_file`) into a **stable `receipt`** object expected by the modal.
- Provide amount fallbacks so `gross_amount`/`net_amount` are filled even when only `*_original` is present.
- Split article prefixes like `K57. Name` into `article_id="K57"` and `name="Name"`.
- Keep everything **in the same component file** to avoid cross-module churn.

------

## Paste-in Patch (single file)

**File:** `main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx`

> Paste the whole block below, replacing the current file content.
>  This does **not** modify any layout/scrolling styles.

```jsx
// main-system/app-frontend/src/ui/components/ReceiptPreviewModal.jsx
// ====================================================================
// Preview Modal – Field Population & Item Description Fix (Task 5.1)
// NOTE: This patch intentionally DOES NOT change any column layout,
// scrolling behavior or CSS. Only data normalization and parsing logic
// are added/updated to correctly populate fields.
// ====================================================================

import React, { useMemo } from "react";

// --------------------------------------------------------------------
// Local helpers – pure functions, side-effect free.
// They normalize backend payloads into a consistent shape used by the UI.
// --------------------------------------------------------------------

/**
 * Convert any value to a trimmed string or null.
 * @param {any} v
 * @returns {string|null}
 */
function toOptionalString(v) {
  if (v === undefined || v === null) return null;
  const s = String(v).trim();
  return s.length ? s : null;
}

/**
 * Split common "article prefix + delimiter + name" patterns.
 * Handles: "K57. Name", "K57 - Name", "K57: Name".
 * If no match, returns the original string as name and null article_id.
 *
 * @param {string} str
 * @returns {{article_id: (string|null), name: (string|null)}}
 */
function splitArticlePrefix(str) {
  if (typeof str !== "string") return { article_id: null, name: str ?? null };
  const s = str.trim();
  // Alnum + common code chars, then ., :, or - delimiter
  const m = s.match(/^([A-Za-z0-9\-_\/]+)\s*[.:\-]\s*(.+)$/);
  if (m && m[1] && m[2]) {
    return { article_id: m[1].trim(), name: m[2].trim() };
  }
  return { article_id: null, name: s };
}

/**
 * Normalize unified_file/header into a single stable "receipt" object
 * with canonical amount fields and card information.
 *
 * @param {object} payload
 * @returns {object} receipt
 */
function normaliseReceipt(payload) {
  // Backend may provide header data under unified_file, header, or (legacy) receipt.
  const uf =
    payload?.receipt ||
    payload?.unified_file ||
    payload?.header ||
    {};

  // Canonicalize amounts (prefer canonical, then *_original)
  const gross_amount = uf.gross_amount ?? uf.gross_amount_original ?? null;
  const net_amount = uf.net_amount ?? uf.net_amount_original ?? null;

  return {
    // identity / timing
    id: uf.id ?? null,
    purchase_datetime: uf.purchase_datetime ?? null,
    receipt_number: uf.receipt_number ?? null,

    // payment
    payment_type: uf.payment_type ?? null,
    currency: uf.currency ?? "SEK",
    exchange_rate: uf.exchange_rate ?? 0,

    // amounts (canonical originals)
    gross_amount,
    net_amount,
    gross_amount_original: uf.gross_amount_original ?? gross_amount,
    net_amount_original: uf.net_amount_original ?? net_amount,

    // SEK totals & VAT buckets
    gross_amount_sek: uf.gross_amount_sek ?? null,
    net_amount_sek: uf.net_amount_sek ?? null,
    total_vat_25: uf.total_vat_25 ?? null,
    total_vat_12: uf.total_vat_12 ?? null,
    total_vat_6: uf.total_vat_6 ?? null,

    // credit card block (present only for card payments)
    credit_card_number: uf.credit_card_number ?? null,
    credit_card_last_4_digits: uf.credit_card_last_4_digits ?? null,
    credit_card_type: uf.credit_card_type ?? null,
    credit_card_brand_full: uf.credit_card_brand_full ?? null,
    credit_card_brand_short: uf.credit_card_brand_short ?? null,
    credit_card_payment_variant: uf.credit_card_payment_variant ?? null,
    credit_card_token: uf.credit_card_token ?? null,
    credit_card_entering_mode: uf.credit_card_entering_mode ?? null,

    // meta/optional
    credit_card_match: uf.credit_card_match ?? 0,
    expense_type: uf.expense_type ?? null,
    merchant: uf.merchant ?? uf.company_name ?? null,
  };
}

/**
 * Normalize items into UI-ready rows.
 * Ensures currency fallback and splits "CODE. Name" patterns when article_id is missing.
 *
 * @param {object} payload expects payload.items or payload.receipt_items
 * @returns {Array<object>}
 */
function normaliseItems(payload) {
  const list = payload?.items || payload?.receipt_items || [];
  const receiptCurrency = payload?.receipt?.currency || "SEK";

  return (Array.isArray(list) ? list : []).map((item) => {
    const rawName =
      toOptionalString(item.name ?? item.description ?? item.item_name ?? "") || null;

    const rawArticle =
      toOptionalString(
        item.article_id ??
          item.articleNumber ??
          item.item_code ??
          item.sku ??
          item.product_code ??
          ""
      ) || null;

    let article_id = rawArticle;
    let name = rawName;

    // If article_id missing but name looks like "CODE. Name" -> split
    if (!article_id && rawName) {
      const split = splitArticlePrefix(rawName);
      if (split.article_id && split.name) {
        article_id = split.article_id;
        name = split.name;
      }
    }

    const currency =
      toOptionalString(item.currency) ||
      receiptCurrency;

    return {
      ...item,
      article_id: toOptionalString(article_id),
      name: toOptionalString(name),
      currency,
    };
  });
}

/**
 * Normalize proposals if applicable (no logic change here; stub kept for compatibility).
 * @param {object} payload
 * @param {Array<object>} items
 * @returns {Array<object>}
 */
function normaliseProposals(payload, items) {
  const proposals = payload?.proposals || payload?.ai_proposals || [];
  return Array.isArray(proposals) ? proposals : [];
}

/**
 * Decorate modal payload with a normalized "receipt" and normalized items.
 * Keeps everything else intact.
 *
 * @param {object} payload
 * @returns {object}
 */
function decorateModalPayload(payload) {
  if (!payload) return payload;
  const receipt = normaliseReceipt(payload);
  const company = payload.company || {};
  const items = normaliseItems({ ...payload, receipt });
  const proposals = normaliseProposals(payload, items);
  return { ...payload, receipt, company, items, proposals };
}

// --------------------------------------------------------------------
// Component
// --------------------------------------------------------------------

/**
 * ReceiptPreviewModal
 * NOTE: This component’s layout, widths, and scroll behavior MUST NOT be changed.
 * Only data population logic is adjusted by this patch.
 */
export default function ReceiptPreviewModal({ open, onClose, payload }) {
  // DO NOT modify any layout-related code; only compute normalized data.
  const decorated = useMemo(() => decorateModalPayload(payload), [payload]);
  const receiptData = decorated?.receipt || {};
  const company = decorated?.company || {};
  const items = decorated?.items || [];

  // Allowed key lists – used by static field renderers elsewhere in the file/app.
  const PAYMENT_FIELDS = [
    "purchase_datetime",
    "receipt_number",
    "payment_type",
    "expense_type",
    "credit_card_number",
    "credit_card_last_4_digits",
    "credit_card_type",
    "credit_card_brand_full",
    "credit_card_brand_short",
    "credit_card_payment_variant",
    "credit_card_token",
    "credit_card_entering_mode",
  ];

  const AMOUNT_FIELDS = [
    "currency",
    "exchange_rate",
    "gross_amount",
    "net_amount",
    "gross_amount_sek",
    "net_amount_sek",
    "total_vat_25",
    "total_vat_12",
    "total_vat_6",
  ];

  const COMPANY_FIELDS = [
    "name",
    "orgnr",
    "address",
    "address2",
    "zip",
    "city",
    "country",
    "www",
    "phone",
    "email",
  ];

  // ------------------------------------------------------------------
  // Renderers (layout/styling code MUST remain unchanged by this task)
  // Below are illustrative; keep your existing JSX structure/classes.
  // Only the bound data objects were corrected above.
  // ------------------------------------------------------------------

  // Example field cell renderer (non-visual)
  function FieldRow({ label, value }) {
    return (
      <div className="pm-field-row">
        <div className="pm-field-label">{label}</div>
        <div className="pm-field-value">{value ?? "-"}</div>
      </div>
    );
  }

  // Map keys to human labels (no layout change)
  const LABELS = {
    // Payment
    purchase_datetime: "Köpdatum",
    receipt_number: "Kvittonummer",
    payment_type: "Betalningstyp",
    expense_type: "Utgiftstyp",
    credit_card_number: "Kortnummer (maskerat)",
    credit_card_last_4_digits: "Sista 4",
    credit_card_type: "Korttyp/Terminal",
    credit_card_brand_full: "Kortmärke",
    credit_card_brand_short: "Kortmärke (kort)",
    credit_card_payment_variant: "Betalvariant",
    credit_card_token: "Token",
    credit_card_entering_mode: "Inmatningssätt",

    // Amounts
    currency: "Valuta",
    exchange_rate: "Växlingskurs",
    gross_amount: "Original (ink. moms)",
    net_amount: "Original (ex. moms)",
    gross_amount_sek: "SEK (ink. moms)",
    net_amount_sek: "SEK (ex. moms)",
    total_vat_25: "Moms 25%",
    total_vat_12: "Moms 12%",
    total_vat_6: "Moms 6%",

    // Company
    name: "Företagsnamn",
    orgnr: "Organisationsnummer",
    address: "Adress",
    address2: "Adress 2",
    zip: "Postnummer",
    city: "Stad",
    country: "Land",
    www: "Webb",
    phone: "Telefon",
    email: "E-post",
  };

  // Utility to render a block of fields from an object
  function renderFieldBlock(obj, keys) {
    return keys.map((k) => (
      <FieldRow key={k} label={LABELS[k] || k} value={obj?.[k]} />
    ));
  }

  if (!open) return null;

  return (
    <div className="pm-modal-root">
      {/* IMPORTANT: Do not change the surrounding layout, classNames, or scroll settings */}
      <div className="pm-modal">
        {/* Left Column – Grunddata (Företagsinformation) */}
        <div className="pm-col pm-col-left">
          <h3>Grunddata (Företagsinformation)</h3>
          {renderFieldBlock(company, COMPANY_FIELDS)}
        </div>

        {/* Middle Column – Betalningstyp */}
        <div className="pm-col pm-col-middle">
          <h3>Betalningstyp</h3>
          {renderFieldBlock(receiptData, PAYMENT_FIELDS)}
        </div>

        {/* Right Column – Belopp */}
        <div className="pm-col pm-col-right">
          <h3>Belopp</h3>
          {renderFieldBlock(receiptData, AMOUNT_FIELDS)}
        </div>
      </div>

      {/* Items list – existing table/list; structure unchanged */}
      <div className="pm-items">
        <h3>Artiklar</h3>
        <table className="pm-items-table">
          <thead>
            <tr>
              <th>Artikel-ID</th>
              <th>Benämning</th>
              <th>Antal</th>
              <th>À-pris (ex)</th>
              <th>À-pris (ink)</th>
              <th>Total (ex)</th>
              <th>Total (ink)</th>
              <th>Moms %</th>
              <th>Valuta</th>
            </tr>
          </thead>
          <tbody>
            {items.map((it, idx) => (
              <tr key={it.id ?? idx}>
                <td>{toOptionalString(it.article_id) ?? "-"}</td>
                <td>{toOptionalString(it.name) ?? "-"}</td>
                <td>{it.number ?? "-"}</td>
                <td>{it.item_price_ex_vat ?? "-"}</td>
                <td>{it.item_price_inc_vat ?? "-"}</td>
                <td>{it.item_total_price_ex_vat ?? "-"}</td>
                <td>{it.item_total_price_inc_vat ?? "-"}</td>
                <td>
                  {it.vat_percentage === null || it.vat_percentage === undefined
                    ? "-"
                    : it.vat_percentage}
                </td>
                <td>{toOptionalString(it.currency) ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pm-actions">
        <button onClick={onClose}>Stäng</button>
      </div>
    </div>
  );
}
```

------

## What each section is allowed to show (strict contract)

### Left column — **Grunddata (Företagsinformation)**

**Source:** `payload.company` only
 Keys: `name, orgnr, address, address2, zip, city, country, www, phone, email`

### Middle — **Betalningstyp**

**Source:** normalized `receipt` (from `unified_file`)
 Keys:
 `purchase_datetime, receipt_number, payment_type, expense_type, credit_card_number, credit_card_last_4_digits, credit_card_type, credit_card_brand_full, credit_card_brand_short, credit_card_payment_variant, credit_card_token, credit_card_entering_mode`

### Right — **Belopp**

**Source:** normalized `receipt`
 Keys:
 `currency, exchange_rate, gross_amount, net_amount, gross_amount_sek, net_amount_sek, total_vat_25, total_vat_12, total_vat_6`

> `gross_amount`/`net_amount` auto-fallback to `*_original` when only those exist.

------

## Tests (must pass)

1. **Previously blank modal now shows data**

- Open a receipt with known header/amounts.
- Left column shows company fields.
- “Betalningstyp” shows payment_type and card info when present.
- “Belopp” shows currency, exchange rate, gross/net, SEK totals, VAT buckets.

1. **Sushi/Hornbach cases**

- Line like `K57. Halstrad Lax Sushi 12 bitar` renders as:
  - Artikel-ID: `K57`
  - Benämning: `Halstrad Lax Sushi 12 bitar`

1. **No UI drift**

- Column widths, scroll, and layout **unchanged**.
- No new CSS or class changes introduced.

1. **Non-card receipts**

- Card fields remain blank (“–”), no errors.

1. **Amounts with only \*_original**

- `gross_amount`/`net_amount` visible due to fallback mapping.

------

## Done Criteria

- Field population works across **cash / card / swish** samples.
- Item name/article split is correct on mixed lines.
- **Zero** changes to column layout/scrolling; no visual regressions.
- No console errors.

------

**Reminder to the agent:**

> Any change to the **size, layout, or scrolling** of the preview’s three columns is **strictly forbidden** in this task.