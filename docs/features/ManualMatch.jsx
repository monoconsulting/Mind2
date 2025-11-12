jsx
/**
 * @file ManualMatch.jsx
 * @description Manual matching view for linking a single FirstCard line to a single receipt
 *              when automatic reconciliation has failed. The page provides:
 *              - A slim header to pick year/month (default = latest imported FC statement month)
 *              - Left column: FC invoice lines for the selected month (single-select via checkbox)
 *              - Right column: Receipts for the selected month (single-select via checkbox)
 *              - A centered MATCH button in the header that becomes enabled only when exactly
 *                one FC line and one receipt are selected
 *              - A button on each receipt row to open the existing ReceiptPreviewModal for view/edit
 *
 *              All functionality is strictly additive; no existing logic or endpoints are changed.
 *              Endpoints are aligned with the patterns already used elsewhere in the codebase.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import api from "../api"; // Reuses the existing authenticated fetch wrapper
import ReceiptPreviewModal from "../components/ReceiptPreviewModal"; // Existing modal component

/**
 * @typedef {Object} FcStatement
 * @property {number} id - Internal statement/invoice identifier.
 * @property {string} uploaded_at - ISO timestamp when the statement was uploaded.
 * @property {string} period_start - Inclusive ISO date for statement coverage (YYYY-MM-DD).
 * @property {string} period_end - Inclusive ISO date for statement coverage (YYYY-MM-DD).
 */

/**
 * @typedef {Object} FcLine
 * @property {number} id - Internal line identifier.
 * @property {string} transaction_date - ISO date of the card transaction (YYYY-MM-DD).
 * @property {number} amount - Amount in minor or major units depending on backend contract.
 * @property {string} currency - Currency code (e.g., "SEK", "EUR").
 * @property {string=} card_mask - Masked card number or short card reference.
 * @property {string=} holder_name - Cardholder's name if available.
 * @property {string=} merchant - Merchant string as parsed from statement.
 * @property {string=} description - Free-text transaction description.
 * @property {string=} match_status - Matching status (e.g., "pending", "matched", "failed").
 * @property {string=} processing_status - Internal processing status string.
 * @property {number=} invoice_id - Parent invoice/statement id if required for match call.
 */

/**
 * @typedef {Object} Receipt
 * @property {string} id - UUID of the receipt.
 * @property {string} purchase_date - ISO date of the purchase (YYYY-MM-DD).
 * @property {number} total_gross - Total gross amount in major currency units.
 * @property {string} currency - Currency code (e.g., "SEK").
 * @property {string=} merchant - Merchant name if available.
 * @property {string=} orgnr - Swedish org number if available.
 * @property {string=} status - Receipt workflow/business status.
 * @property {string=} tags - Comma-separated tags or array depending on backend.
 */

/**
 * Returns a numeric month length for the given year and month.
 *
 * @param {number} year - Four digit year.
 * @param {number} month1to12 - Month number, 1-12.
 * @returns {number} Last day in the given month.
 */
function daysInMonth(year, month1to12) {
  return new Date(year, month1to12, 0).getDate();
}

/**
 * Produces an ISO date range [from, to] for a given year and month.
 *
 * @param {number} year - Four digit year.
 * @param {number} month1to12 - Month number, 1-12.
 * @returns {{from: string, to: string}} Inclusive start (YYYY-MM-01) and end (YYYY-MM-DD).
 */
function monthRange(year, month1to12) {
  const last = daysInMonth(year, month1to12);
  const mm = String(month1to12).padStart(2, "0");
  return { from: `${year}-${mm}-01`, to: `${year}-${mm}-${last}` };
}

/**
 * Attempts to determine the latest statement month from a list of statements.
 * It prefers the statement with the newest `uploaded_at` that has valid period_start/period_end.
 *
 * @param {FcStatement[]} statements - List of statements returned by the API.
 * @returns {{year: number, month: number}|null} Latest statement year/month or null if none.
 */
function inferLatestStatementMonth(statements) {
  if (!Array.isArray(statements) || statements.length === 0) return null;
  /** @type {FcStatement[]} */
  const filtered = statements.filter(
    (s) => !!s.period_start && !!s.period_end && !!s.uploaded_at
  );
  if (filtered.length === 0) return null;
  const sorted = filtered.sort(
    (a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at)
  );
  const pick = sorted[0];
  try {
    const d = new Date(pick.period_end);
    return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1 };
  } catch {
    return null;
  }
}

/**
 * Formats a number as a localized currency-like string without setting a fixed currency.
 * This avoids styling assumptions and preserves readability.
 *
 * @param {number} value - Numeric value in major units.
 * @returns {string} Human-friendly formatted string (e.g., "1 234,56").
 */
function formatAmount(value) {
  if (typeof value !== "number" || Number.isNaN(value)) return "";
  try {
    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  } catch {
    return String(value);
  }
}

/**
 * Formats a YYYY-MM-DD string into a readable local date.
 *
 * @param {string} isoDate - A date string in YYYY-MM-DD or ISO format.
 * @returns {string} Localized short date.
 */
function formatDate(isoDate) {
  if (!isoDate) return "";
  const d = new Date(isoDate);
  if (Number.isNaN(+d)) return isoDate;
  try {
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(d);
  } catch {
    return isoDate;
  }
}

/**
 * ManualMatch page component: shows FC lines vs receipts for a chosen month/year,
 * allowing the operator to manually link exactly one item from each side.
 *
 * @component
 * @returns {JSX.Element} Rendered manual matching page.
 */
export default function ManualMatch() {
  // -----------------------------
  // State
  // -----------------------------
  /** @type {[number|null, Function]} */
  const [year, setYear] = useState(null);
  /** @type {[number|null, Function]} */
  const [month, setMonth] = useState(null);
  /** @type {[FcStatement[], Function]} */
  const [statements, setStatements] = useState([]);
  /** @type {[FcLine[], Function]} */
  const [fcLines, setFcLines] = useState([]);
  /** @type {[Receipt[], Function]} */
  const [receipts, setReceipts] = useState([]);

  /** @type {[number|null, Function]} */
  const [selectedLineId, setSelectedLineId] = useState(null);
  /** @type {[string|null, Function]} */
  const [selectedReceiptId, setSelectedReceiptId] = useState(null);

  /** @type {[boolean, Function]} */
  const [loadingStatements, setLoadingStatements] = useState(false);
  /** @type {[boolean, Function]} */
  const [loadingLeft, setLoadingLeft] = useState(false);
  /** @type {[boolean, Function]} */
  const [loadingRight, setLoadingRight] = useState(false);
  /** @type {[boolean, Function]} */
  const [matching, setMatching] = useState(false);

  /** @type {[boolean, Function]} */
  const [showReceiptModal, setShowReceiptModal] = useState(false);
  /** @type {[string|null, Function]} */
  const [activeReceiptId, setActiveReceiptId] = useState(null);

  // -----------------------------
  // Constants (endpoints mirror existing patterns used in the codebase)
  // -----------------------------
  // NOTE: We purposely do not remove or alter any existing API contracts elsewhere.
  // These paths follow the same scheme referenced by existing FirstCard and Receipts pages.
  const EP_STATEMENTS = "/ai/api/reconciliation/firstcard/statements";
  // Lines are typically fetched either by statement/invoice id or by a lines endpoint used in CompanyCard.
  // This view will resolve the correct statement for the chosen month, then fetch its lines.
  const EP_LINES_BY_INVOICE = (invoiceId) =>
    `/ai/api/reconciliation/firstcard/invoices/${invoiceId}/lines`;
  const EP_RECEIPTS = "/ai/api/receipts";
  const EP_MATCH = "/ai/api/reconciliation/firstcard/match";

  // -----------------------------
  // Derived values
  // -----------------------------
  const monthKey = useMemo(() => {
    if (!year || !month) return null;
    return `${year}-${String(month).padStart(2, "0")}`;
  }, [year, month]);

  const canMatch = Boolean(selectedLineId && selectedReceiptId && !matching);

  // -----------------------------
  // Data Loaders
  // -----------------------------

  /**
   * Fetches the list of FirstCard statements and sets default period
   * to the latest imported statement month if year/month are not set yet.
   *
   * @returns {Promise<void>}
   */
  const fetchStatements = useCallback(async () => {
    setLoadingStatements(true);
    try {
      const res = await api.get(EP_STATEMENTS);
      const list = Array.isArray(res?.data) ? res.data : [];
      setStatements(list);

      if (year == null || month == null) {
        const inferred = inferLatestStatementMonth(list);
        if (inferred) {
          setYear(inferred.year);
          setMonth(inferred.month);
        } else {
          // If there are no statements at all, default to current month without mutating any other logic.
          const now = new Date();
          setYear(now.getUTCFullYear());
          setMonth(now.getUTCMonth() + 1);
        }
      }
    } catch (err) {
      console.error("Failed to fetch statements", err);
      // Minimal, non-intrusive UX message without altering shared components
      window.alert("Kunde inte hämta FC-statements. Se konsolen för detaljer.");
    } finally {
      setLoadingStatements(false);
    }
  }, [EP_STATEMENTS, month, year]);

  /**
   * Finds a statement that overlaps the current selected month.
   * Preference: the newest uploaded statement overlapping the period.
   *
   * @returns {FcStatement|null} Matching statement or null.
   */
  const resolveStatementForMonth = useCallback(() => {
    if (!Array.isArray(statements) || !year || !month) return null;
    const { from, to } = monthRange(year, month);
    const start = new Date(from);
    const end = new Date(to);

    const overlapping = statements.filter((s) => {
      const ps = new Date(s.period_start);
      const pe = new Date(s.period_end);
      return !(pe < start || ps > end);
    });

    if (overlapping.length === 0) return null;
    const sorted = overlapping.sort(
      (a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at)
    );
    return sorted[0];
  }, [statements, year, month]);

  /**
   * Loads FirstCard lines for the selected period by resolving a statement
   * and asking for its invoice lines.
   *
   * @returns {Promise<void>}
   */
  const loadFcLinesForPeriod = useCallback(async () => {
    setLoadingLeft(true);
    setSelectedLineId(null); // Reset selection when period changes
    try {
      const st = resolveStatementForMonth();
      if (!st) {
        setFcLines([]);
        return;
      }
      // Reuse the known pattern to fetch lines by parent invoice/statement id
      const linesResp = await api.get(EP_LINES_BY_INVOICE(st.id));
      const rows = Array.isArray(linesResp?.data) ? linesResp.data : [];

      // Ensure each line surface its parent invoice id if backend does not include it in each item
      const rowsWithInvoice = rows.map((r) =>
        typeof r.invoice_id === "number" ? r : { ...r, invoice_id: st.id }
      );

      setFcLines(rowsWithInvoice);
    } catch (err) {
      console.error("Failed to load FC lines", err);
      window.alert("Kunde inte hämta FC-rader för vald period. Se konsolen för detaljer.");
      setFcLines([]);
    } finally {
      setLoadingLeft(false);
    }
  }, [EP_LINES_BY_INVOICE, resolveStatementForMonth, year, month]);

  /**
   * Loads receipts for the selected month using the existing receipts endpoint with from/to filters.
   *
   * @returns {Promise<void>}
   */
  const loadReceiptsForPeriod = useCallback(async () => {
    if (!year || !month) return;
    setLoadingRight(true);
    setSelectedReceiptId(null); // Reset selection when period changes
    try {
      const { from, to } = monthRange(year, month);
      const resp = await api.get(EP_RECEIPTS, { params: { from, to } });
      const list = Array.isArray(resp?.data) ? resp.data : [];
      setReceipts(list);
    } catch (err) {
      console.error("Failed to load receipts", err);
      window.alert("Kunde inte hämta kvitton för vald period. Se konsolen för detaljer.");
      setReceipts([]);
    } finally {
      setLoadingRight(false);
    }
  }, [EP_RECEIPTS, year, month]);

  // -----------------------------
  // Event Handlers
  // -----------------------------

  /**
   * Handles the selection of one FC line (single-select). Selecting a new line clears previous.
   *
   * @param {number} lineId - FC line id to select.
   */
  const handleSelectLine = useCallback((lineId) => {
    setSelectedLineId((prev) => (prev === lineId ? null : lineId));
  }, []);

  /**
   * Handles the selection of one receipt (single-select). Selecting a new receipt clears previous.
   *
   * @param {string} receiptId - Receipt id to select.
   */
  const handleSelectReceipt = useCallback((receiptId) => {
    setSelectedReceiptId((prev) => (prev === receiptId ? null : receiptId));
  }, []);

  /**
   * Invokes the manual match endpoint to link the selected FC line to the selected receipt.
   * After success, it refreshes both lists to surface the updated statuses.
   *
   * @returns {Promise<void>}
   */
  const handleMatch = useCallback(async () => {
    if (!canMatch) return;
    setMatching(true);
    try {
      const line = fcLines.find((l) => l.id === selectedLineId);
      if (!line) {
        window.alert("Kunde inte hitta vald FC-rad.");
        return;
      }

      const payload = {
        line_id: line.id,
        receipt_id: selectedReceiptId,
      };

      // Only include invoice_id if the line exposes it (we do not invent values).
      if (typeof line.invoice_id === "number") {
        payload.invoice_id = line.invoice_id;
      }

      const res = await api.post(EP_MATCH, payload);

      if (res?.status >= 200 && res?.status < 300) {
        // Refresh lists so statuses & visibility reflect the match
        await Promise.all([loadFcLinesForPeriod(), loadReceiptsForPeriod()]);
        // Clear selections to avoid accidental double-match
        setSelectedLineId(null);
        setSelectedReceiptId(null);
        window.alert("Matchning genomförd.");
      } else {
        window.alert("Matchning misslyckades. Se konsolen för detaljer.");
        console.error("Match API non-2xx response", res);
      }
    } catch (err) {
      console.error("Match API error", err);
      window.alert("Matchning misslyckades. Se konsolen för detaljer.");
    } finally {
      setMatching(false);
    }
  }, [
    canMatch,
    fcLines,
    selectedLineId,
    selectedReceiptId,
    EP_MATCH,
    loadFcLinesForPeriod,
    loadReceiptsForPeriod,
  ]);

  /**
   * Opens the ReceiptPreviewModal for a given receipt id.
   *
   * @param {string} receiptId - Target receipt id to open in modal.
   */
  const openReceiptModal = useCallback((receiptId) => {
    setActiveReceiptId(receiptId);
    setShowReceiptModal(true);
  }, []);

  /**
   * Closes the ReceiptPreviewModal and optionally refreshes the receipts list
   * if changes were made inside the modal (the modal can trigger this via callback).
   *
   * @param {boolean} shouldReload - Whether to reload the receipts after closing.
   */
  const closeReceiptModal = useCallback(
    async (shouldReload = false) => {
      setShowReceiptModal(false);
      setActiveReceiptId(null);
      if (shouldReload) {
        await loadReceiptsForPeriod();
      }
    },
    [loadReceiptsForPeriod]
  );

  // -----------------------------
  // Effects
  // -----------------------------

  // Initial load of statements + default period inference
  useEffect(() => {
    // We do not remove statements if already present; calling once on mount is safe.
    fetchStatements();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When period changes OR statements change (for resolution), load both lists
  useEffect(() => {
    if (!year || !month) return;
    loadFcLinesForPeriod();
    loadReceiptsForPeriod();
  }, [year, month, statements, loadFcLinesForPeriod, loadReceiptsForPeriod]);

  // -----------------------------
  // Render Helpers
  // -----------------------------

  /**
   * Returns a list of month options (1..12) with localized labels.
   *
   * @returns {{value:number,label:string}[]} Month options.
   */
  const monthOptions = useMemo(() => {
    const base = [];
    for (let m = 1; m <= 12; m += 1) {
      const date = new Date(2024, m - 1, 1); // Year is irrelevant for label localization
      const label = new Intl.DateTimeFormat(undefined, { month: "long" }).format(date);
      base.push({ value: m, label: label.charAt(0).toUpperCase() + label.slice(1) });
    }
    return base;
  }, []);

  /**
   * Creates a small rolling window of years around current year,
   * ensuring the latest statement year is selectable as well.
   *
   * @returns {number[]} Array of year numbers.
   */
  const yearOptions = useMemo(() => {
    const ys = new Set();
    const nowY = new Date().getFullYear();
    for (let d = -2; d <= 2; d += 1) ys.add(nowY + d);
    // Include any statement years explicitly (period_end year)
    statements.forEach((s) => {
      try {
        ys.add(new Date(s.period_end).getUTCFullYear());
      } catch {
        /* ignore parse issues */
      }
    });
    return Array.from(ys).sort((a, b) => b - a);
  }, [statements]);

  // -----------------------------
  // UI
  // -----------------------------
  return (
    <div className="flex flex-col h-full">
      {/* Slim header */}
      <div className="w-full border-b border-gray-200 bg-white px-4 py-2 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">År</span>
          <select
            className="border rounded-md px-2 py-1 text-sm"
            value={year ?? ""}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            <option value="" disabled>Välj år</option>
            {yearOptions.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>

          <span className="text-sm font-medium text-gray-700">Månad</span>
          <select
            className="border rounded-md px-2 py-1 text-sm"
            value={month ?? ""}
            onChange={(e) => setMonth(Number(e.target.value))}
          >
            <option value="" disabled>Välj månad</option>
            {monthOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Centered MATCH button */}
        <div className="flex-1 flex justify-center">
          <button
            className={`px-4 py-1.5 rounded-md text-sm font-semibold ${
              canMatch
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-200 text-gray-500 cursor-not-allowed"
            }`}
            disabled={!canMatch}
            onClick={handleMatch}
            title="Koppla vald FC-rad mot valt kvitto"
          >
            {matching ? "MATCHAR..." : "MATCHA"}
          </button>
        </div>

        {/* Period indicator (right side) */}
        <div className="text-xs text-gray-500">
          {loadingStatements ? "Laddar statements..." : monthKey ? `Period: ${monthKey}` : "Välj period"}
        </div>
      </div>

      {/* Main content: two columns */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 overflow-hidden">
        {/* Left column: FC lines */}
        <div className="flex flex-col min-h-0 border border-gray-200 rounded-xl bg-white">
          <div className="px-4 py-2 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold">FirstCard-rader</h2>
            <div className="text-xs text-gray-500">
              {loadingLeft ? "Laddar..." : `${fcLines.length} rader`}
            </div>
          </div>
          <div className="flex-1 overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-3 py-2 text-left w-10">Val</th>
                  <th className="px-3 py-2 text-left">Datum</th>
                  <th className="px-3 py-2 text-left">Belopp</th>
                  <th className="px-3 py-2 text-left">Valuta</th>
                  <th className="px-3 py-2 text-left">Kort</th>
                  <th className="px-3 py-2 text-left">Innehavare</th>
                  <th className="px-3 py-2 text-left">Merchant</th>
                  <th className="px-3 py-2 text-left">Beskrivning</th>
                  <th className="px-3 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {fcLines.length === 0 && !loadingLeft ? (
                  <tr>
                    <td colSpan={9} className="px-3 py-6 text-center text-gray-400">
                      Inga rader för vald period.
                    </td>
                  </tr>
                ) : (
                  fcLines.map((l) => {
                    const checked = selectedLineId === l.id;
                    const amount = typeof l.amount === "number" ? l.amount : Number(l.amount);
                    return (
                      <tr key={l.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="px-3 py-2 align-top">
                          <input
                            type="checkbox"
                            checked={!!checked}
                            onChange={() => handleSelectLine(l.id)}
                            aria-label={`Välj rad ${l.id}`}
                          />
                        </td>
                        <td className="px-3 py-2 align-top">{formatDate(l.transaction_date)}</td>
                        <td className="px-3 py-2 align-top whitespace-nowrap">{formatAmount(amount)}</td>
                        <td className="px-3 py-2 align-top">{l.currency || ""}</td>
                        <td className="px-3 py-2 align-top">{l.card_mask || ""}</td>
                        <td className="px-3 py-2 align-top">{l.holder_name || ""}</td>
                        <td className="px-3 py-2 align-top">{l.merchant || ""}</td>
                        <td className="px-3 py-2 align-top">{l.description || ""}</td>
                        <td className="px-3 py-2 align-top">
                          <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-700">
                            {l.match_status || l.processing_status || "okänd"}
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right column: Receipts */}
        <div className="flex flex-col min-h-0 border border-gray-200 rounded-xl bg-white">
          <div className="px-4 py-2 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Kvitton</h2>
            <div className="text-xs text-gray-500">
              {loadingRight ? "Laddar..." : `${receipts.length} kvitton`}
            </div>
          </div>
          <div className="flex-1 overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-3 py-2 text-left w-10">Val</th>
                  <th className="px-3 py-2 text-left">Datum</th>
                  <th className="px-3 py-2 text-left">Belopp</th>
                  <th className="px-3 py-2 text-left">Valuta</th>
                  <th className="px-3 py-2 text-left">Merchant</th>
                  <th className="px-3 py-2 text-left">Org.nr</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left w-24">Portal</th>
                </tr>
              </thead>
              <tbody>
                {receipts.length === 0 && !loadingRight ? (
                  <tr>
                    <td colSpan={8} className="px-3 py-6 text-center text-gray-400">
                      Inga kvitton för vald period.
                    </td>
                  </tr>
                ) : (
                  receipts.map((r) => {
                    const checked = selectedReceiptId === r.id;
                    return (
                      <tr key={r.id} className="border-b last:border-0 hover:bg-gray-50">
                        <td className="px-3 py-2 align-top">
                          <input
                            type="checkbox"
                            checked={!!checked}
                            onChange={() => handleSelectReceipt(r.id)}
                            aria-label={`Välj kvitto ${r.id}`}
                          />
                        </td>
                        <td className="px-3 py-2 align-top">{formatDate(r.purchase_date)}</td>
                        <td className="px-3 py-2 align-top whitespace-nowrap">{formatAmount(Number(r.total_gross))}</td>
                        <td className="px-3 py-2 align-top">{r.currency || ""}</td>
                        <td className="px-3 py-2 align-top">{r.merchant || ""}</td>
                        <td className="px-3 py-2 align-top">{r.orgnr || ""}</td>
                        <td className="px-3 py-2 align-top">
                          <span className="inline-block px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-700">
                            {r.status || "okänd"}
                          </span>
                        </td>
                        <td className="px-3 py-2 align-top">
                          <button
                            className="px-2 py-1 text-xs rounded-md border border-gray-300 hover:bg-gray-100"
                            onClick={() => openReceiptModal(r.id)}
                            title="Öppna kvittoportalen"
                          >
                            Öppna
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Receipt modal */}
      {showReceiptModal && activeReceiptId && (
        <ReceiptPreviewModal
          receiptId={activeReceiptId}
          onClose={(reload) => closeReceiptModal(Boolean(reload))}
        />
      )}
    </div>
  );
}
