import React from 'react';
import { FiX, FiSave, FiEdit2, FiTrash2 } from 'react-icons/fi';
import { api } from '../api';

// Helper functions
function normaliseFieldId(value) {
  if (!value || typeof value !== 'string') {
    return '';
  }
  const lower = value.toLowerCase().trim();
  const withoutPrefix = lower.replace(/^(receipt|unified_files|receipt_items|accounting_proposals|items|line_items|proposals)./i, '');
  const withoutBrackets = withoutPrefix.replace(/[\d+]/g, '');
  return withoutBrackets;
}

function resolveBoxField(boxes, candidates) {
  if (!Array.isArray(boxes) || !Array.isArray(candidates)) {
    return candidates[0];
  }
  const normalised = candidates.map((c) => normaliseFieldId(c));
  const match = boxes.find((box) => normalised.includes(normaliseFieldId(box.field)));
  return match?.field || candidates[0];
}

function firstNonEmptyArray(source, keys) {
  if (!source || typeof source !== 'object') {
    return [];
  }
  for (const key of keys) {
    const value = source[key];
    if (Array.isArray(value) && value.length > 0) {
      return value;
    }
  }
  const fallbackKey = keys.find((key) => Array.isArray(source[key]));
  if (fallbackKey) {
    return source[fallbackKey];
  }
  return [];
}

async function attachLineItemsFallback(payload, receiptId) {
  if (!receiptId || !payload || typeof payload !== 'object') {
    return payload;
  }
  const existing = firstNonEmptyArray(payload, ['items', 'receipt_items', 'line_items', 'unified_file_items']);
  if (Array.isArray(existing) && existing.length > 0) {
    return payload;
  }
  try {
    const res = await api.fetch(`/ai/api/receipts/${receiptId}/line-items`);
    if (!res.ok) {
      return payload;
    }
    const data = await res.json();
    const fallback = Array.isArray(data?.line_items)
      ? data.line_items
      : Array.isArray(data)
        ? data
        : [];
    if (!fallback.length) {
      return payload;
    }
    console.debug('[ReceiptPreviewModal] Fetched fallback line items', fallback.length);
    const meta = {
      ...(payload.meta || {}),
      items_source: payload.meta?.items_source || 'file_store',
      items_count: fallback.length,
    };
    return {
      ...payload,
      line_items: fallback,
      meta,
    };
  } catch (err) {
    console.error('Failed to load fallback line items', err);
    return payload;
  }
}

function toNullableNumber(value) {
  if (value === '' || value === null || value === undefined) {
    return null;
  }
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function toOptionalString(value) {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value);
}

function normaliseItems(payload) {
  const receiptCurrency = payload?.receipt?.currency || 'SEK';
  const rawItems = firstNonEmptyArray(payload, ['items', 'receipt_items', 'line_items', 'unified_file_items']);
  return rawItems.map((item) => {
    const quantity = toNullableNumber(item.number ?? item.quantity ?? item.qty) ?? 1;
    const unitNet =
      toNullableNumber(
        item.item_price_ex_vat ??
          item.unit_price_ex_vat ??
          item.price_ex_vat ??
          item.unit_amount_ex_vat ??
          item.net_price ??
          item.unit_net
      ) ?? null;
    const unitGross =
      toNullableNumber(
        item.item_price_inc_vat ??
          item.unit_price_inc_vat ??
          item.price_inc_vat ??
          item.unit_amount_inc_vat ??
          item.gross_price ??
          item.unit_gross
      ) ?? null;
    const totalNet =
      toNullableNumber(
        item.item_total_price_ex_vat ??
          item.total_price_ex_vat ??
          item.total_net ??
          item.net_amount ??
          item.amount_ex_vat ??
          item.total_ex_vat
      ) ?? (unitNet != null ? unitNet * quantity : null);
    const totalGross =
      toNullableNumber(
        item.item_total_price_inc_vat ??
          item.total_price_inc_vat ??
          item.total_gross ??
          item.gross_amount ??
          item.total_amount ??
          item.total_inc_vat
      ) ?? (unitGross != null ? unitGross * quantity : null);
    const vatAmount =
      toNullableNumber(item.vat ?? item.item_vat ?? item.vat_amount ?? item.item_vat_total ?? item.total_vat) ??
      (totalGross != null && totalNet != null ? totalGross - totalNet : null);
    const vatRate =
      toNullableNumber(item.vat_percentage ?? item.vat_rate ?? item.vat_percent ?? item.vat) ??
      (vatAmount != null && totalNet ? (vatAmount / totalNet) * 100 : null);
    const idCandidate = item.id ?? item.item_id ?? item.receipt_item_id ?? item.main_id ?? item.uuid ?? null;

    return {
      id: idCandidate,
      item_id: item.item_id ?? item.receipt_item_id ?? null,
      article_id: toOptionalString(
        item.article_id ?? item.articleNumber ?? item.item_code ?? item.sku ?? item.product_code ?? ''
      ),
      name: toOptionalString(item.name ?? item.description ?? item.item_name ?? ''),
      number: quantity != null ? quantity : '',
      item_price_ex_vat: unitNet,
      item_price_inc_vat: unitGross,
      item_total_price_ex_vat: totalNet,
      item_total_price_inc_vat: totalGross,
      vat: vatAmount,
      vat_percentage: vatRate,
      currency: toOptionalString(item.currency ?? receiptCurrency ?? 'SEK'),
    };
  });
}

function normaliseProposals(payload, items) {
  const rawProposals = firstNonEmptyArray(payload, [
    'proposals',
    'accounting',
    'accounting_entries',
    'accounting_proposals',
    'ai_accounting_proposals',
  ]);
  if (!rawProposals.length) {
    return [];
  }

  const itemIndexById = new Map();
  items.forEach((item, index) => {
    const candidates = [
      item.id,
      item.item_id,
      item.receipt_item_id,
      item.article_id,
      item.sku,
      item.articleNumber,
    ]
      .filter((key) => key !== null && key !== undefined)
      .map((key) => String(key));
    candidates.forEach((candidate) => {
      if (!itemIndexById.has(candidate)) {
        itemIndexById.set(candidate, index);
      }
    });
  });

  return rawProposals.map((entry, index) => {
    const debit = toNullableNumber(entry.debit ?? entry.debet ?? entry.amount_debet ?? entry.amount_debit);
    const credit = toNullableNumber(entry.credit ?? entry.kredit ?? entry.amount_credit);
    const vatRate = toNullableNumber(entry.vat_rate ?? entry.vat ?? entry.vat_percentage);
    let itemIndex =
      typeof entry.item_index === 'number' && Number.isInteger(entry.item_index)
        ? entry.item_index
        : null;
    const candidateKeys = [
      entry.item_id,
      entry.receipt_item_id,
      entry.item,
      entry.item_key,
      entry.article_id,
    ]
      .filter((key) => key !== null && key !== undefined)
      .map((key) => String(key));
    if ((itemIndex === null || itemIndex < 0 || itemIndex >= items.length) && candidateKeys.length) {
      for (const candidate of candidateKeys) {
        if (itemIndexById.has(candidate)) {
          itemIndex = itemIndexById.get(candidate);
          break;
        }
      }
    }
    if (itemIndex === null || itemIndex < 0 || itemIndex >= items.length) {
      itemIndex = items.length > 0 ? Math.min(index, items.length - 1) : 0;
    }

    return {
      id: entry.id ?? entry.proposal_id ?? null,
      item_index: itemIndex,
      account: toOptionalString(entry.account ?? entry.account_code ?? entry.konto ?? ''),
      debit,
      credit,
      vat_rate: vatRate,
      notes: toOptionalString(entry.notes ?? entry.description ?? entry.memo ?? ''),
    };
  });
}

function decorateModalPayload(payload) {
  if (!payload) {
    return payload;
  }
  const company = payload.company || {};
  const items = normaliseItems(payload);
  const proposals = normaliseProposals(payload, items);
  return { ...payload, company, items, proposals };
}

const ITEM_DETAIL_FIELDS = [
  { key: 'article_id', label: 'Artikelnummer' },
  { key: 'name', label: 'Artikel' },
  { key: 'number', label: 'Antal' },
  { key: 'currency', label: 'Valuta' },
  { key: 'item_price_ex_vat', label: 'Belopp ex. moms' },
  { key: 'item_price_inc_vat', label: 'Belopp ink. moms' },
  { key: 'vat', label: 'Belopp moms' },
  { key: 'vat_percentage', label: 'Moms %' },
  { key: 'item_total_price_ex_vat', label: 'Belopp totalt ex. moms' },
  { key: 'item_total_price_inc_vat', label: 'Belopp totalt ink. moms' },
  { key: 'item_vat_total', label: 'Belopp moms totalt', computed: true },
];

function prepareDraft(payload) {
  if (!payload) {
    return { receipt: {}, company: {}, items: [], proposals: [] };
  }
  const receipt = payload.receipt || {};
  const company = payload.company || {};
  const items = (payload.items || []).map((item) => ({
    id: item.id ?? null,
    item_id: item.item_id ?? null,
    article_id: toOptionalString(item.article_id || item.articleNumber || ''),
    name: toOptionalString(item.name || item.description || ''),
    number: item.number != null ? String(item.number) : '',
    item_price_ex_vat: item.item_price_ex_vat != null ? String(item.item_price_ex_vat) : '',
    item_price_inc_vat: item.item_price_inc_vat != null ? String(item.item_price_inc_vat) : '',
    item_total_price_ex_vat: item.item_total_price_ex_vat != null ? String(item.item_total_price_ex_vat) : '',
    item_total_price_inc_vat: item.item_total_price_inc_vat != null ? String(item.item_total_price_inc_vat) : '',
    vat: item.vat != null ? String(item.vat) : '',
    vat_percentage: item.vat_percentage != null ? String(item.vat_percentage) : '',
    currency: toOptionalString(item.currency || payload?.receipt?.currency || 'SEK'),
  }));
  const itemCount = Math.max(items.length, 1);
  const proposals = (payload.proposals || []).map((entry, index) => ({
    id: entry.id ?? null,
    account: toOptionalString(entry.account || entry.account_code || ''),
    debit: entry.debit != null ? String(entry.debit) : '',
    credit: entry.credit != null ? String(entry.credit) : '',
    vat_rate: entry.vat_rate != null ? String(entry.vat_rate) : '',
    notes: toOptionalString(entry.notes || ''),
    item_index:
      typeof entry.item_index === 'number' && entry.item_index >= 0
        ? entry.item_index
        : Math.min(index, itemCount - 1),
  }));
  return {
    receipt: {
      merchant: receipt.merchant || receipt.merchant_name || '',
      vat: receipt.vat || '',
      purchase_datetime: receipt.purchase_datetime || receipt.purchase_date || '',
      receipt_number: receipt.receipt_number || '',
      payment_type: receipt.payment_type || '',
      expense_type: receipt.expense_type || '',
      credit_card_number: receipt.credit_card_number || '',
      credit_card_last_4_digits: receipt.credit_card_last_4_digits || '',
      credit_card_type: receipt.credit_card_type || '',
      credit_card_brand_full: receipt.credit_card_brand_full || '',
      credit_card_brand_short: receipt.credit_card_brand_short || '',
      credit_card_payment_variant: receipt.credit_card_payment_variant || '',
      credit_card_token: receipt.credit_card_token || '',
      credit_card_entering_mode: receipt.credit_card_entering_mode || '',
      currency: receipt.currency || 'SEK',
      exchange_rate: receipt.exchange_rate != null ? String(receipt.exchange_rate) : '',
      gross_amount: receipt.gross_amount != null ? String(receipt.gross_amount) : '',
      net_amount: receipt.net_amount != null ? String(receipt.net_amount) : '',
      gross_amount_sek: receipt.gross_amount_sek != null ? String(receipt.gross_amount_sek) : '',
      net_amount_sek: receipt.net_amount_sek != null ? String(receipt.net_amount_sek) : '',
      total_vat_25: receipt.total_vat_25 != null ? String(receipt.total_vat_25) : '',
      total_vat_12: receipt.total_vat_12 != null ? String(receipt.total_vat_12) : '',
      total_vat_6: receipt.total_vat_6 != null ? String(receipt.total_vat_6) : '',
      ai_status: receipt.ai_status || receipt.status || '',
      ai_confidence: receipt.ai_confidence != null ? String(receipt.ai_confidence) : '',
      tags: Array.isArray(receipt.tags) ? receipt.tags.join(', ') : receipt.tags || '',
      ocr_raw: receipt.ocr_raw || '',
      other_data: receipt.other_data || '',
    },
    company: {
      name: company.name || '',
      orgnr: company.orgnr || '',
      address: company.address || '',
      address2: company.address2 || '',
      zip: company.zip || '',
      city: company.city || '',
      country: company.country || '',
      phone: company.phone || '',
      www: company.www || '',
      email: company.email || '',
    },
    items,
    proposals,
  };
}

// Format helpers
const formatDate = (dateString) => {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('sv-SE');
  } catch {
    return dateString;
  }
};

const formatCurrency = (value) => {
  if (value == null || isNaN(value)) return '-';
  return new Intl.NumberFormat('sv-SE', {
    style: 'currency',
    currency: 'SEK',
  }).format(value);
};

// Main component
export default function ReceiptPreviewModal({ open, receipt, previewImage, onClose, onReceiptUpdate }) {
  const [loading, setLoading] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [payload, setPayload] = React.useState(null);
  const [draft, setDraft] = React.useState(null);
  const [editing, setEditing] = React.useState(false);
  const [hoverField, setHoverField] = React.useState(null);

  React.useEffect(() => {
    if (!open) {
      setPayload(null);
      setDraft(null);
      setEditing(false);
      setHoverField(null);
      setError(null);
      setLoading(false);
      setSaving(false);
    }
  }, [open]);

  React.useEffect(() => {
    if (!open || !receipt?.id) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setEditing(false);
    setHoverField(null);

    const fetchData = async () => {
      try {
        const res = await api.fetch(`/ai/api/receipts/${receipt.id}/modal`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        let rawPayload = await res.json();
        rawPayload = await attachLineItemsFallback(rawPayload, receipt.id);
        if (cancelled) {
          return;
        }
        const decorated = decorateModalPayload(rawPayload);
        const mergedPayload = { ...rawPayload, ...decorated };
        if (cancelled) {
          return;
        }
        setPayload(mergedPayload);
        setDraft(prepareDraft(mergedPayload));
        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      }
    };

    fetchData();

    return () => {
      cancelled = true;
    };
  }, [open, receipt?.id]);

  if (!open || !receipt) {
    return null;
  }

  const boxes = payload?.boxes || [];

  const matchHighlight = (key) => {
    if (!hoverField || !key) {
      return '';
    }
    return normaliseFieldId(hoverField) === normaliseFieldId(key) ? 'highlighted' : 'muted';
  };

  const receiptData = payload?.receipt || {};
  const receiptDraft = draft?.receipt || {};
  const companyData = payload?.company || {};
  const companyDraft = draft?.company || {};

  const itemsSource = editing && draft ? draft.items : payload?.items || [];
  const proposalsSource = editing && draft ? draft.proposals : payload?.proposals || [];

  const proposalsByItem = (() => {
    if (!itemsSource.length) {
      return [];
    }
    const groups = itemsSource.map(() => []);
    proposalsSource.forEach((entry, index) => {
      const targetIndex =
        typeof entry.item_index === 'number' && entry.item_index >= 0 && entry.item_index < groups.length
          ? entry.item_index
          : Math.min(groups.length - 1, Math.max(index, 0));
      groups[targetIndex].push({ ...entry, _globalIndex: index });
    });
    return groups;
  })();

  const updateReceiptDraft = (field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      return { ...prev, receipt: { ...prev.receipt, [field]: value } };
    });
  };

  const updateCompanyDraft = (field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      return { ...prev, company: { ...prev.company, [field]: value } };
    });
  };

  const updateItemDraft = (index, field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      const nextItems = prev.items.map((item, idx) => (idx === index ? { ...item, [field]: value } : item));
      return { ...prev, items: nextItems };
    });
  };

  const updateProposalDraft = (index, field, value) => {
    setDraft((prev) => {
      if (!prev) {
        return prev;
      }
      const nextProposals = prev.proposals.map((proposal, idx) =>
        idx === index ? { ...proposal, [field]: value } : proposal
      );
      return { ...prev, proposals: nextProposals };
    });
  };

  const handleToggleEdit = () => {
    if (editing) {
      setDraft(prepareDraft(payload));
    }
    setEditing((prev) => !prev);
  };

  const handleSave = async () => {
    if (!draft) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await api.fetch(`/ai/api/receipts/${receipt.id}/modal`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const json = await res.json();
      let refreshedPayload = json.data || {};
      refreshedPayload = await attachLineItemsFallback(refreshedPayload, receipt.id);
      const decorated = decorateModalPayload(refreshedPayload);
      const nextPayload = {
        ...(payload || {}),
        ...refreshedPayload,
        receipt: decorated.receipt || payload?.receipt || {},
        company: decorated.company || payload?.company || {},
        items: decorated.items || [],
        proposals: decorated.proposals || [],
      };
      setPayload(nextPayload);
      setDraft(prepareDraft(nextPayload));
      setEditing(false);
      setHoverField(null);
      if (decorated.receipt && typeof onReceiptUpdate === 'function') {
        onReceiptUpdate(decorated.receipt);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const handleBackdrop = (event) => {
    if (event.target === event.currentTarget && !saving) {
      onClose();
    }
  };

  const handleDelete = async () => {
    if (!receipt?.id) {
      return;
    }
    try {
      const res = await api.fetch(`/ai/api/receipts/${receipt.id}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      if (typeof onReceiptUpdate === 'function') {
        onReceiptUpdate({ id: receipt.id, deleted: true });
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const baseImageSrc = previewImage || `/ai/api/receipts/${receipt.id}/image?size=preview&rotate=portrait`;

  return (
    <div className="modal-backdrop receipt-preview-modal" role="dialog" aria-label={`Förhandsgranskning kvitto ${receipt.id}`} onClick={handleBackdrop}>
      <div className="modal modal-xxl" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>Förhandsgranska kvitto</h3>
            <p className="card-subtitle">
              {receiptData.merchant || receipt.merchant || 'Kvitto'} · {formatDate(receiptData.purchase_datetime)}
            </p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng förhandsgranskning" disabled={saving}>
            <FiX />
          </button>
        </div>
        <div className="modal-body receipt-modal-body">
          {loading ? (
            <div className="receipt-modal-loading">
              <div className="loading-inline">
                <div className="loading-spinner" />
                <span>Laddar kvitto...</span>
              </div>
            </div>
          ) : error ? (
            <div className="alert alert-error">
              <span>{error}</span>
            </div>
          ) : !payload ? (
            <div className="receipt-modal-loading">Ingen data tillgänglig</div>
          ) : (
            <div className="receipt-modal-content">
              {/* Left Column - Company & Receipt Data */}
              <div className="receipt-modal-column receipt-modal-left">
                {/* RP5: Grunddata (Box 1) - Company Information */}
                <div className="receipt-modal-section">
                  <h4>Grunddata (Företagsinformation)</h4>
                  <div className="receipt-modal-grid">
                    {[
                      { key: 'name', label: 'Företag', source: 'company' },
                      { key: 'orgnr', label: 'Organisationsnummer', source: 'company' },
                      { key: 'address', label: 'Adress', source: 'company' },
                      { key: 'address2', label: 'Adress 2', source: 'company' },
                      { key: 'zip', label: 'Postnummer', source: 'company' },
                      { key: 'city', label: 'Ort', source: 'company' },
                      { key: 'country', label: 'Land', source: 'company' },
                      { key: 'www', label: 'Hemsida', source: 'company' },
                      { key: 'phone', label: 'Telefonnummer', source: 'company' },
                      { key: 'email', label: 'Email', source: 'company' },
                    ].map((field) => {
                      const sourceData = field.source === 'company' ? companyData : receiptData;
                      const draftData = field.source === 'company' ? companyDraft : receiptDraft;
                      return (
                        <div key={field.key} className="receipt-modal-field">
                          <label className="field-label">{field.label}</label>
                          {editing ? (
                            <input
                              className="dm-input"
                              value={draftData[field.key] ?? ''}
                              onChange={(event) => field.source === 'company' ? updateCompanyDraft(field.key, event.target.value) : updateReceiptDraft(field.key, event.target.value)}
                              disabled={saving}
                            />
                          ) : (
                            <div className="field-value">{sourceData[field.key] || '-'}</div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* RP6: Betalningstyp (Box 2) - Payment Information */}
                <div className="receipt-modal-section">
                  <h4>Betalningstyp</h4>
                  <div className="receipt-modal-grid">
                    {[
                      { key: 'purchase_datetime', label: 'Inköpsdatum' },
                      { key: 'receipt_number', label: 'Kvittonnummer' },
                      { key: 'payment_type', label: 'Betalningstyp' },
                      { key: 'expense_type', label: 'Utgiftstyp' },
                      { key: 'credit_card_number', label: 'Kortnummer' },
                      { key: 'credit_card_last_4_digits', label: 'Kortnummer 4 sista' },
                      { key: 'credit_card_type', label: 'Korttyp' },
                      { key: 'credit_card_brand_full', label: 'Korttyp full' },
                      { key: 'credit_card_brand_short', label: 'Korttyp kort' },
                      { key: 'credit_card_payment_variant', label: 'Betalningsvariant' },
                      { key: 'credit_card_token', label: 'Korttyp token' },
                      { key: 'credit_card_entering_mode', label: 'Inmatningsläge' },
                    ].map((field) => (
                      <div key={field.key} className="receipt-modal-field">
                        <label className="field-label">{field.label}</label>
                        {editing ? (
                          <input
                            className="dm-input"
                            value={receiptDraft[field.key] ?? ''}
                            onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
                            disabled={saving}
                          />
                        ) : field.key === 'purchase_datetime' ? (
                          <div className="field-value">{formatDate(receiptData.purchase_datetime)}</div>
                        ) : (
                          <div className="field-value">{receiptData[field.key] || '-'}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* RP7: Belopp (Box 3) - Amounts and VAT */}
                <div className="receipt-modal-section">
                  <h4>Belopp</h4>
                  <div className="receipt-modal-grid">
                    {[
                      { key: 'currency', label: 'Valuta' },
                      { key: 'exchange_rate', label: 'Växlingskurs' },
                      { key: 'gross_amount', label: 'Originalbelopp ink. moms', format: 'currency' },
                      { key: 'net_amount', label: 'Originalbelopp ex. moms', format: 'currency' },
                      { key: 'gross_amount_sek', label: 'Svenskt totalbelopp ink moms SEK', format: 'currency' },
                      { key: 'net_amount_sek', label: 'Svenskt totalbelopp ex. moms SEK', format: 'currency' },
                      { key: 'total_vat_25', label: 'Moms 25%', format: 'currency' },
                      { key: 'total_vat_12', label: 'Moms 12%', format: 'currency' },
                      { key: 'total_vat_6', label: 'Moms 6%', format: 'currency' },
                    ].map((field) => (
                      <div key={field.key} className="receipt-modal-field">
                        <label className="field-label">{field.label}</label>
                        {editing ? (
                          <input
                            className="dm-input"
                            value={receiptDraft[field.key] ?? ''}
                            onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
                            disabled={saving}
                          />
                        ) : field.format === 'currency' ? (
                          <div className="field-value">{formatCurrency(Number(receiptData[field.key] || 0))}</div>
                        ) : (
                          <div className="field-value">{receiptData[field.key] || '-'}</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* RP8: Övrigt (Box 4) - Other Data (Full Width) */}
                <div className="receipt-modal-section">
                  <h4>Övrigt</h4>
                  <div className="receipt-modal-field">
                    <label className="field-label">Övrig data</label>
                    {editing ? (
                      <textarea
                        className="dm-input"
                        value={receiptDraft.other_data ?? ''}
                        onChange={(event) => updateReceiptDraft('other_data', event.target.value)}
                        disabled={saving}
                        rows={3}
                        style={{ width: '100%', resize: 'vertical' }}
                      />
                    ) : (
                      <div className="field-value" style={{ whiteSpace: 'pre-wrap' }}>{receiptData.other_data || '-'}</div>
                    )}
                  </div>
                </div>

                {/* OCR Text Section */}
                {editing && (
                <div className="receipt-modal-section ocr-section">
                  <h4>OCR-text</h4>
                  <div className="ocr-content" style={{ whiteSpace: 'pre-wrap', maxHeight: '200px', overflowY: 'auto' }}>
                    {receiptDraft.ocr_raw || 'Ingen OCR-data tillgänglig'}
                  </div>
                </div>
                )}
              </div>

              {/* Center Column - Image */}
              <div className="receipt-modal-center">
                <div className="receipt-modal-image-wrapper">
                  {baseImageSrc ? (
                    <img src={baseImageSrc} alt={`Kvitto ${receipt.id}`} className="receipt-modal-image" />
                  ) : (
                    <div className="receipt-modal-image-fallback">Ingen bild</div>
                  )}
                  {boxes.map((box, index) => {
                    const overlayKey = box.field || `box-${index}`;
                    const toCss = (val) => {
                      if (typeof val !== 'number') {
                        return '0%';
                      }
                      if (val > 1) {
                        return `${val}px`;
                      }
                      const clamped = Math.min(Math.max(val, 0), 1);
                      return `${clamped * 100}%`;
                    };
                    return (
                      <div
                        key={`${overlayKey}-${index}`}
                        className={`receipt-modal-overlay ${matchHighlight(overlayKey)}`}
                        style={{
                          position: 'absolute',
                          top: toCss(box.y ?? box.top ?? 0),
                          left: toCss(box.x ?? box.left ?? 0),
                          width: toCss(box.w ?? box.width ?? 0),
                          height: toCss(box.h ?? box.height ?? 0),
                        }}
                        onMouseEnter={() => setHoverField(overlayKey)}
                        onMouseLeave={() => setHoverField(null)}
                      />
                    );
                  })}
                </div>
              </div>

              {/* RP9: Items Table with Accounting (Right Column) */}
              <div className="receipt-modal-column receipt-modal-right">
                <div className="receipt-modal-section">
                  <div className="receipt-item-header-main">Varor och kontering</div>
                  {itemsSource.length === 0 ? (
                    <div className="field-value muted">Inga varor registrerade</div>
                  ) : (
                    itemsSource.map((item, itemIndex) => {
                      const itemProposals = proposalsByItem[itemIndex] || [];
                      const itemDraft = editing && draft ? draft.items[itemIndex] : null;
                      const getItemValue = (key) => {
                        if (editing && itemDraft && Object.prototype.hasOwnProperty.call(itemDraft, key)) {
                          return itemDraft[key];
                        }
                        return item[key];
                      };
                      return (
                        <div key={`item-${itemIndex}`} className="receipt-item-card-new">
                          <div className="receipt-item-header-new">RAD {itemIndex + 1}</div>
                          <div className="receipt-item-grid-new">
                            {ITEM_DETAIL_FIELDS.map((field) => {
                              const computedValue =
                                field.computed && field.key === 'item_vat_total'
                                  ? (() => {
                                      const grossTotal = Number(
                                        getItemValue('item_total_price_inc_vat') ?? getItemValue('item_price_inc_vat') ?? 0
                                      );
                                      const netTotal = Number(
                                        getItemValue('item_total_price_ex_vat') ?? getItemValue('item_price_ex_vat') ?? 0
                                      );
                                      const diff = grossTotal - netTotal;
                                      if (Number.isFinite(diff) && Math.abs(diff) > 0) {
                                        return diff.toFixed(2);
                                      }
                                      const fallback = Number(getItemValue('vat') || 0) * Number(getItemValue('number') || 1);
                                      return Number.isFinite(fallback) && Math.abs(fallback) > 0 ? fallback.toFixed(2) : '';
                                    })()
                                  : null;
                              const readOnlyValue = field.computed ? computedValue : getItemValue(field.key);
                              const draftValue = itemDraft ? itemDraft[field.key] ?? '' : '';
                              return (
                                <div key={`${field.key}-${itemIndex}`} className="receipt-item-cell-new">
                                  <span className="cell-label-new">{field.label}</span>
                                  {editing && !field.computed ? (
                                    <input
                                      className="dm-input-new"
                                      value={draftValue}
                                      onChange={(event) => updateItemDraft(itemIndex, field.key, event.target.value)}
                                      disabled={saving}
                                    />
                                  ) : (
                                    <div className="cell-value-new">{readOnlyValue !== null && readOnlyValue !== undefined && readOnlyValue !== '' ? readOnlyValue : '-'}</div>
                                  )}
                                </div>
                              );
                            })}
                          </div>

                          <div className="proposal-group-new">
                            <div className="proposal-group-header-new">Kontering</div>
                            {itemProposals.length === 0 ? (
                              <div className="proposal-empty-new">Inga konteringsförslag</div>
                            ) : (
                              itemProposals.map((proposal) => {
                                const globalIndex = proposal._globalIndex;
                                const proposalDraft = editing && draft ? draft.proposals[globalIndex] : null;
                                const debitValue = proposalDraft ? proposalDraft.debit : proposal.debit;
                                const creditValue = proposalDraft ? proposalDraft.credit : proposal.credit;
                                const accountValue = proposalDraft ? proposalDraft.account : proposal.account;
                                const vatRateValue = proposalDraft ? proposalDraft.vat_rate : proposal.vat_rate;
                                const notesValue = proposalDraft ? proposalDraft.notes : proposal.notes;

                                const isDebit = Number(debitValue || 0) > 0;
                                const amount = isDebit ? debitValue : creditValue;
                                const amountDisplay = editing
                                  ? amount ?? ''
                                  : amount != null && amount !== ''
                                  ? formatCurrency(Number(amount))
                                  : '-';
                                const vatRateDisplay = editing
                                  ? vatRateValue ?? ''
                                  : vatRateValue != null && vatRateValue !== ''
                                  ? `${Number(vatRateValue).toLocaleString('sv-SE', { maximumFractionDigits: 2 })}%`
                                  : '-';

                                return (
                                  <div key={`proposal-${globalIndex}`} className="proposal-card-new">
                                    <div className="proposal-line-new">
                                      <div className="proposal-cell-new">
                                        <span className="cell-label-new">{isDebit ? 'Debetkonto' : 'Kreditkonto'}</span>
                                        {editing ? (
                                          <input
                                            className="dm-input-new"
                                            value={accountValue ?? ''}
                                            onChange={(event) => updateProposalDraft(globalIndex, 'account', event.target.value)}
                                            disabled={saving}
                                            placeholder="Konto"
                                          />
                                        ) : (
                                          <div className="cell-value-new">{accountValue || '-'}</div>
                                        )}
                                      </div>
                                      <div className="proposal-cell-new">
                                        <span className="cell-label-new">Belopp {isDebit ? 'Debet' : 'Kredit'}</span>
                                        {editing ? (
                                          <div className="proposal-amount-inputs-new">
                                            <input
                                              className="dm-input-new"
                                              value={debitValue ?? ''}
                                              onChange={(event) => updateProposalDraft(globalIndex, 'debit', event.target.value)}
                                              disabled={saving}
                                              placeholder="Debet"
                                            />
                                            <input
                                              className="dm-input-new"
                                              value={creditValue ?? ''}
                                              onChange={(event) => updateProposalDraft(globalIndex, 'credit', event.target.value)}
                                              disabled={saving}
                                              placeholder="Kredit"
                                            />
                                          </div>
                                        ) : (
                                          <div className="cell-value-new">{amountDisplay}</div>
                                        )}
                                      </div>
                                      <div className="proposal-cell-new">
                                        <span className="cell-label-new">Momssats</span>
                                        {editing ? (
                                          <input
                                            className="dm-input-new"
                                            value={vatRateValue ?? ''}
                                            onChange={(event) => updateProposalDraft(globalIndex, 'vat_rate', event.target.value)}
                                            disabled={saving}
                                            placeholder="Moms %"
                                          />
                                        ) : (
                                          <div className="cell-value-new">{vatRateDisplay}</div>
                                        )}
                                      </div>
                                      <div className="proposal-cell-new">
                                        <span className="cell-label-new">Notering</span>
                                        {editing ? (
                                          <input
                                            className="dm-input-new"
                                            value={notesValue ?? ''}
                                            onChange={(event) => updateProposalDraft(globalIndex, 'notes', event.target.value)}
                                            disabled={saving}
                                            placeholder="Notering"
                                          />
                                        ) : (
                                          <div className="cell-value-new">{notesValue || 'Ingen notering'}</div>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                );
                              })
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer receipt-modal-footer">
          <div className="footer-hint">Hovra över fält eller bildmarkeringar för att se kopplingarna.</div>
          <div className="modal-footer-actions">
            {editing ? (
              <>
                <button type="button" className="btn btn-secondary" onClick={handleToggleEdit} disabled={saving}>
                  Avbryt
                </button>
                <button type="button" className="btn btn-primary" onClick={handleSave} disabled={saving}>
                  <FiSave />
                  {saving ? 'Sparar...' : 'Spara'}
                </button>
              </>
            ) : (
              <>
                <button type="button" className="btn btn-secondary" onClick={handleToggleEdit} disabled={saving || loading || !payload}>
                  <FiEdit2 />
                  Redigera
                </button>
                <button type="button" className="btn btn-danger" onClick={handleDelete} disabled={saving || loading} title="Radera kvitto">
                  <FiTrash2 />
                  Radera
                </button>
              </>
            )}
            <button type="button" className="btn btn-text" onClick={onClose} disabled={saving}>
              Stäng
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
