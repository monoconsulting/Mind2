import React from 'react';
import { FiX, FiSave, FiEdit2 } from 'react-icons/fi';
import { api } from '../api';

// Helper functions
function normaliseFieldId(value) {
  if (!value || typeof value !== 'string') {
    return '';
  }
  const lower = value.toLowerCase().trim();
  const withoutPrefix = lower.replace(/^(receipt|unified_files|receipt_items|accounting_proposals|items|line_items|proposals)\./i, '');
  const withoutBrackets = withoutPrefix.replace(/\[\d+\]/g, '');
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

function decorateModalPayload(payload) {
  if (!payload) {
    return payload;
  }
  const items = Array.isArray(payload.items) ? payload.items : [];
  const proposals = Array.isArray(payload.proposals) ? payload.proposals : [];
  const company = payload.company || {};
  const itemCount = items.length || 1;
  const decoratedProposals = proposals.map((entry, index) => {
    const itemIndex = typeof entry.item_index === 'number' ? entry.item_index : Math.min(index, Math.max(itemCount - 1, 0));
    return { ...entry, item_index: itemIndex };
  });
  return { ...payload, company, items, proposals: decoratedProposals };
}

function prepareDraft(payload) {
  if (!payload) {
    return { receipt: {}, company: {}, items: [], proposals: [] };
  }
  const receipt = payload.receipt || {};
  const company = payload.company || {};
  const items = (payload.items || []).map((item) => ({
    id: item.id ?? null,
    article_id: item.article_id || '',
    name: item.name || item.description || '',
    number: item.number != null ? String(item.number) : '',
    item_price_ex_vat: item.item_price_ex_vat != null ? String(item.item_price_ex_vat) : '',
    item_price_inc_vat: item.item_price_inc_vat != null ? String(item.item_price_inc_vat) : '',
    item_total_price_ex_vat: item.item_total_price_ex_vat != null ? String(item.item_total_price_ex_vat) : '',
    item_total_price_inc_vat: item.item_total_price_inc_vat != null ? String(item.item_total_price_inc_vat) : '',
    vat: item.vat != null ? String(item.vat) : '',
    vat_percentage: item.vat_percentage != null ? String(item.vat_percentage) : '',
    currency: item.currency || 'SEK',
  }));
  const itemCount = Math.max(items.length, 1);
  const proposals = (payload.proposals || []).map((entry, index) => ({
    id: entry.id ?? null,
    account: entry.account || entry.account_code || '',
    debit: entry.debit != null ? String(entry.debit) : '',
    credit: entry.credit != null ? String(entry.credit) : '',
    vat_rate: entry.vat_rate != null ? String(entry.vat_rate) : '',
    notes: entry.notes || '',
    item_index: typeof entry.item_index === 'number' ? entry.item_index : Math.min(index, itemCount - 1),
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
      credit_card_last_4: receipt.credit_card_last_4 || '',
      credit_card_brand_full: receipt.credit_card_brand_full || '',
      credit_card_brand_short: receipt.credit_card_brand_short || '',
      credit_card_token: receipt.credit_card_token || '',
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
        const json = decorateModalPayload(await res.json());
        if (cancelled) {
          return;
        }
        setPayload(json);
        setDraft(prepareDraft(json));
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
  const resolveCandidates = React.useCallback(
    (candidates) => resolveBoxField(boxes, (candidates || []).filter(Boolean)),
    [boxes]
  );

  const matchHighlight = React.useCallback(
    (key) => {
      if (!hoverField || !key) {
        return '';
      }
      return normaliseFieldId(hoverField) === normaliseFieldId(key) ? 'highlighted' : 'muted';
    },
    [hoverField]
  );

  const highlightReceiptField = React.useCallback(
    (field, extras = []) => resolveCandidates([field, `receipt.${field}`, `unified_files.${field}`, ...extras]),
    [resolveCandidates]
  );

  const highlightItemField = React.useCallback(
    (index, field, extras = []) =>
      resolveCandidates([
        `items[${index}].${field}`,
        `line_items[${index}].${field}`,
        `receipt_items[${index}].${field}`,
        ...extras,
      ]),
    [resolveCandidates]
  );

  const highlightProposalField = React.useCallback(
    (index, field, extras = []) =>
      resolveCandidates([
        `accounting_proposals[${index}].${field}`,
        `proposals[${index}].${field}`,
        ...extras,
      ]),
    [resolveCandidates]
  );

  const receiptData = payload?.receipt || {};
  const receiptDraft = draft?.receipt || {};
  const companyData = payload?.company || {};
  const companyDraft = draft?.company || {};

  const itemsSource = React.useMemo(
    () => (editing && draft ? draft.items : payload?.items || []),
    [editing, draft, payload]
  );

  const proposalsSource = React.useMemo(
    () => (editing && draft ? draft.proposals : payload?.proposals || []),
    [editing, draft, payload]
  );

  const proposalsByItem = React.useMemo(() => {
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
  }, [itemsSource, proposalsSource]);

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
      const refreshed = decorateModalPayload(json.data || {});
      const nextPayload = {
        ...(payload || {}),
        receipt: refreshed.receipt || payload?.receipt || {},
        company: refreshed.company || payload?.company || {},
        items: refreshed.items || [],
        proposals: refreshed.proposals || [],
      };
      setPayload(nextPayload);
      setDraft(prepareDraft(nextPayload));
      setEditing(false);
      setHoverField(null);
      if (refreshed.receipt && typeof onReceiptUpdate === 'function') {
        onReceiptUpdate(refreshed.receipt);
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

  const baseImageSrc = previewImage || `/ai/api/receipts/${receipt.id}/image?size=preview&rotate=portrait`;

  return (
    <div className="modal-backdrop" role="dialog" aria-label={`Förhandsgranskning kvitto ${receipt.id}`} onClick={handleBackdrop}>
      <div className="modal modal-xxl receipt-preview-modal" onClick={(event) => event.stopPropagation()}>
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
            <div className="receipt-modal-content" style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 250px)' }}>
              {/* Left Column - Company & Receipt Data */}
              <div className="receipt-modal-column receipt-modal-left" style={{ flex: '1', overflowY: 'auto', paddingRight: '0.5rem' }}>
                {/* RP5: Grunddata (Box 1) - Company Information */}
                <div className="receipt-modal-section">
                  <h4>Grunddata (Företagsinformation)</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
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
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                    {[
                      { key: 'purchase_datetime', label: 'Inköpsdatum' },
                      { key: 'receipt_number', label: 'Kvittonnummer' },
                      { key: 'payment_type', label: 'Betalningstyp' },
                      { key: 'expense_type', label: 'Utgiftstyp' },
                      { key: 'credit_card_number', label: 'Kortnummer' },
                      { key: 'credit_card_last_4', label: 'Kortnummer 4 sista' },
                      { key: 'credit_card_brand_full', label: 'Korttyp' },
                      { key: 'credit_card_brand_short', label: 'Korttyp kort' },
                      { key: 'credit_card_token', label: 'Korttyp token' },
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
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
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
                <div className="receipt-modal-section ocr-section">
                  <h4>OCR-text</h4>
                  <div className="ocr-content" style={{ whiteSpace: 'pre-wrap', maxHeight: '200px', overflowY: 'auto' }}>
                    {receiptDraft.ocr_raw || 'Ingen OCR-data tillgänglig'}
                  </div>
                </div>
              </div>

              {/* Center Column - Image */}
              <div className="receipt-modal-center" style={{ flex: '1', overflowY: 'auto', paddingRight: '0.5rem' }}>
                <div className="receipt-modal-image-wrapper" style={{ position: 'relative' }}>
                  {baseImageSrc ? (
                    <img src={baseImageSrc} alt={`Kvitto ${receipt.id}`} className="receipt-modal-image" style={{ width: '100%', height: 'auto' }} />
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
              <div className="receipt-modal-column receipt-modal-right" style={{ flex: '1.5', overflowY: 'auto' }}>
                <div className="receipt-modal-section">
                  <h4>Varor och kontering</h4>
                  {itemsSource.length === 0 ? (
                    <div className="field-value muted">Inga varor registrerade</div>
                  ) : (
                    itemsSource.map((item, itemIndex) => {
                      const itemProposals = proposalsByItem[itemIndex] || [];
                      return (
                        <div key={`item-${itemIndex}`} className="receipt-item-card" style={{ marginBottom: '1.5rem', border: '1px solid #374151', borderRadius: '8px', padding: '1rem' }}>
                          {/* Row Number Header */}
                          <div style={{ background: '#1f2937', padding: '0.5rem', marginBottom: '1rem', borderRadius: '4px', fontWeight: 'bold' }}>
                            RAD {itemIndex + 1}
                          </div>

                          {/* Item Details Grid (4 columns) */}
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', marginBottom: '1rem' }}>
                            {[
                              { key: 'article_id', label: 'Artikelnummer' },
                              { key: 'name', label: 'Artikel' },
                              { key: 'number', label: 'Antal' },
                              { key: '', label: '' },
                              { key: 'item_price_ex_vat', label: 'Belopp ex. moms' },
                              { key: 'item_price_inc_vat', label: 'Belopp ink. moms' },
                              { key: 'vat', label: 'Belopp moms' },
                              { key: 'vat_percentage', label: 'Moms %' },
                              { key: 'item_total_price_ex_vat', label: 'Belopp totalt ex. moms' },
                              { key: 'item_total_price_inc_vat', label: 'Belopp totalt ink. moms' },
                              { key: 'item_vat_total', label: 'Belopp moms totalt', computed: true },
                              { key: 'vat_percentage', label: 'Moms %' },
                            ].map((field, idx) => {
                              if (!field.key && !field.label) {
                                return <div key={idx}></div>;
                              }
                              const value = editing && draft ? draft.items[itemIndex][field.key] : item[field.key];
                              const displayValue = field.computed && field.key === 'item_vat_total'
                                ? (Number(item.vat || 0) * Number(item.number || 1)).toFixed(2)
                                : value;
                              return (
                                <div key={`${field.key}-${idx}`} style={{ fontSize: '0.875rem' }}>
                                  <div style={{ color: '#9ca3af', marginBottom: '0.25rem' }}>{field.label}</div>
                                  {editing && !field.computed ? (
                                    <input
                                      className="dm-input"
                                      style={{ fontSize: '0.875rem', padding: '0.25rem' }}
                                      value={displayValue ?? ''}
                                      onChange={(event) => updateItemDraft(itemIndex, field.key, event.target.value)}
                                      disabled={saving}
                                    />
                                  ) : (
                                    <div style={{ color: '#e5e7eb', fontWeight: '500' }}>{displayValue || '-'}</div>
                                  )}
                                </div>
                              );
                            })}
                          </div>

                          {/* Accounting Proposals */}
                          <div style={{ borderTop: '1px solid #374151', paddingTop: '1rem' }}>
                            <div style={{ fontWeight: 'bold', marginBottom: '0.75rem', color: '#9ca3af' }}>Kontering:</div>
                            {itemProposals.length === 0 ? (
                              <div className="field-value muted">Inga konteringsförslag</div>
                            ) : (
                              itemProposals.map((proposal) => {
                                const globalIndex = proposal._globalIndex;
                                const debitValue = editing && draft ? draft.proposals[globalIndex].debit : proposal.debit;
                                const creditValue = editing && draft ? draft.proposals[globalIndex].credit : proposal.credit;
                                const accountValue = editing && draft ? draft.proposals[globalIndex].account : proposal.account;
                                const vatRateValue = editing && draft ? draft.proposals[globalIndex].vat_rate : proposal.vat_rate;
                                const notesValue = editing && draft ? draft.proposals[globalIndex].notes : proposal.notes;

                                const isDebit = Number(debitValue || 0) > 0;
                                const amount = isDebit ? debitValue : creditValue;
                                const prefix = isDebit ? 'Debet:' : 'Kredit:';

                                return (
                                  <div key={`proposal-${globalIndex}`} style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem', marginBottom: '0.5rem', padding: '0.5rem', background: '#111827', borderRadius: '4px' }}>
                                    <div style={{ fontSize: '0.875rem' }}>
                                      <div style={{ color: '#9ca3af' }}>{prefix} {accountValue || '-'}</div>
                                      {editing && (
                                        <input
                                          className="dm-input"
                                          style={{ fontSize: '0.875rem', padding: '0.25rem', marginTop: '0.25rem' }}
                                          value={accountValue ?? ''}
                                          onChange={(event) => updateProposalDraft(globalIndex, 'account', event.target.value)}
                                          disabled={saving}
                                          placeholder="Konto"
                                        />
                                      )}
                                    </div>
                                    <div style={{ fontSize: '0.875rem' }}>
                                      <div style={{ color: '#9ca3af' }}>Belopp: {amount || '0.00'}</div>
                                      {editing && (
                                        <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.25rem' }}>
                                          <input
                                            className="dm-input"
                                            style={{ fontSize: '0.875rem', padding: '0.25rem', flex: 1 }}
                                            value={debitValue ?? ''}
                                            onChange={(event) => updateProposalDraft(globalIndex, 'debit', event.target.value)}
                                            disabled={saving}
                                            placeholder="Debet"
                                          />
                                          <input
                                            className="dm-input"
                                            style={{ fontSize: '0.875rem', padding: '0.25rem', flex: 1 }}
                                            value={creditValue ?? ''}
                                            onChange={(event) => updateProposalDraft(globalIndex, 'credit', event.target.value)}
                                            disabled={saving}
                                            placeholder="Kredit"
                                          />
                                        </div>
                                      )}
                                    </div>
                                    <div style={{ fontSize: '0.875rem' }}>
                                      <div style={{ color: '#9ca3af' }}>Momssats: {vatRateValue || '0'}%</div>
                                      {editing && (
                                        <input
                                          className="dm-input"
                                          style={{ fontSize: '0.875rem', padding: '0.25rem', marginTop: '0.25rem' }}
                                          value={vatRateValue ?? ''}
                                          onChange={(event) => updateProposalDraft(globalIndex, 'vat_rate', event.target.value)}
                                          disabled={saving}
                                          placeholder="Moms %"
                                        />
                                      )}
                                    </div>
                                    <div style={{ fontSize: '0.875rem' }}>
                                      <div style={{ color: '#9ca3af' }}>{notesValue || 'Ingen notering'}</div>
                                      {editing && (
                                        <input
                                          className="dm-input"
                                          style={{ fontSize: '0.875rem', padding: '0.25rem', marginTop: '0.25rem' }}
                                          value={notesValue ?? ''}
                                          onChange={(event) => updateProposalDraft(globalIndex, 'notes', event.target.value)}
                                          disabled={saving}
                                          placeholder="Notering"
                                        />
                                      )}
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
              <button type="button" className="btn btn-secondary" onClick={handleToggleEdit} disabled={saving || loading || !payload}>
                <FiEdit2 />
                Redigera
              </button>
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
