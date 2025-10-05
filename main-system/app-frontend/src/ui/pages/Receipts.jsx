import React from 'react'
import {
  FiSearch,
  FiFilter,
  FiRefreshCw,
  FiEye,
  FiX,
  FiEdit2,
  FiSave,
  FiCheckCircle,
  FiXCircle,
  FiMapPin,
  FiShoppingCart,
  FiCalendar,
  FiTag,
  FiChevronLeft,
  FiChevronRight
} from 'react-icons/fi'
import { api } from '../api'

const initialFilters = {
  from: '',
  to: '',
  orgnr: '',
  tag: ''
}

function formatCurrency(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-'
  }
  const formatter = new Intl.NumberFormat('sv-SE', {
    style: 'currency',
    currency: 'SEK',
    minimumFractionDigits: 2
  })
  return formatter.format(value)
}

function formatDate(value) {
  if (!value) {
    return '-'
  }
  try {
    const raw = typeof value === 'string' ? value : value?.toString?.()
    if (!raw) {
      return '-'
    }
    const parsed = raw.length === 10 ? new Date(`${raw}T00:00:00Z`) : new Date(raw)
    if (Number.isNaN(parsed.getTime())) {
      return raw
    }
    return parsed.toLocaleDateString('sv-SE')
  } catch (error) {
    return typeof value === 'string' ? value : '-'
  }
}

function normaliseFieldId(value) {
  if (!value) {
    return ''
  }
  return String(value)
    .toLowerCase()
    .replace(/receipt[_\.]/g, '')
    .replace(/unified_files[_\.]/g, '')
    .replace(/line_items/g, 'items')
    .replace(/accounting_proposals/g, 'proposals')
    .replace(/[^a-z0-9]/g, '')
}

function resolveBoxField(boxes, candidates) {
  if (!Array.isArray(candidates) || candidates.length === 0) {
    return ''
  }
  if (!Array.isArray(boxes) || boxes.length === 0) {
    return candidates[0]
  }
  const normalised = candidates.map((candidate) => normaliseFieldId(candidate))
  const match = boxes.find((box) => normalised.includes(normaliseFieldId(box.field)))
  return match?.field || candidates[0]
}

function decorateModalPayload(payload) {
  if (!payload) {
    return payload
  }
  const items = Array.isArray(payload.items) ? payload.items : []
  const proposals = Array.isArray(payload.proposals) ? payload.proposals : []
  const itemCount = items.length || 1
  const decoratedProposals = proposals.map((entry, index) => {
    const itemIndex = typeof entry.item_index === 'number' ? entry.item_index : Math.min(index, Math.max(itemCount - 1, 0))
    return { ...entry, item_index: itemIndex }
  })
  return { ...payload, items, proposals: decoratedProposals }
}

function prepareDraft(payload) {
  if (!payload) {
    return { receipt: {}, items: [], proposals: [] }
  }
  const receipt = payload.receipt || {}
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
  }))
  const itemCount = Math.max(items.length, 1)
  const proposals = (payload.proposals || []).map((entry, index) => ({
    id: entry.id ?? null,
    account: entry.account || entry.account_code || '',
    debit: entry.debit != null ? String(entry.debit) : '',
    credit: entry.credit != null ? String(entry.credit) : '',
    vat_rate: entry.vat_rate != null ? String(entry.vat_rate) : '',
    notes: entry.notes || '',
    item_index: typeof entry.item_index === 'number' ? entry.item_index : Math.min(index, itemCount - 1),
  }))
  return {
    receipt: {
      merchant: receipt.merchant || receipt.merchant_name || '',
      orgnr: receipt.orgnr || '',
      purchase_datetime: receipt.purchase_datetime || receipt.purchase_date || '',
      gross_amount: receipt.gross_amount != null ? String(receipt.gross_amount) : '',
      net_amount: receipt.net_amount != null ? String(receipt.net_amount) : '',
      expense_type: receipt.expense_type || '',
      ai_status: receipt.ai_status || receipt.status || '',
      ai_confidence: receipt.ai_confidence != null ? String(receipt.ai_confidence) : '',
      tags: Array.isArray(receipt.tags) ? receipt.tags.join(', ') : receipt.tags || '',
      ocr_raw: receipt.ocr_raw || '',
    },
    items,
    proposals,
  }
}

function Banner({ banner, onDismiss }) {
  if (!banner) {
    return null
  }
  const iconMap = {
    info: <FiCheckCircle className="text-xl" />,
    success: <FiCheckCircle className="text-xl" />,
    error: <FiXCircle className="text-xl" />
  }
  const tone = banner.type || 'info'
  return (
    <div className={`alert alert-${tone}`}>
      <div className="alert-icon">{iconMap[tone] || iconMap.info}</div>
      <div className="alert-message">{banner.message}</div>
      {onDismiss && (
        <button type="button" className="alert-dismiss" onClick={onDismiss} aria-label="Stäng meddelande">
          <FiX />
        </button>
      )}
    </div>
  )
}

function SearchAndFilters({ searchTerm, onSearch, onReset, loading, pageSize, onPageSizeChange }) {
  const [value, setValue] = React.useState(searchTerm)

  React.useEffect(() => {
    setValue(searchTerm)
  }, [searchTerm])

  const handleSubmit = (event) => {
    event.preventDefault()
    onSearch(value.trim())
  }

  const handleReset = () => {
    setValue('')
    onReset()
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Sök och filtrera</h3>
          <p className="card-subtitle">Hitta kvitton snabbt</p>
        </div>
      </div>
      <div className="flex flex-col lg:flex-row gap-4">
        <form onSubmit={handleSubmit} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <FiSearch className="input-icon" />
            <input
              type="text"
              placeholder="Sök efter företag, filnamn eller belopp"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              className="dm-input pl-10"
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            <FiSearch />
            Sök
          </button>
          <button type="button" className="btn btn-secondary" onClick={handleReset} disabled={loading && !value}>
            Rensa
          </button>
        </form>
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-300 whitespace-nowrap" htmlFor="page-size">
            Visa per sida:
          </label>
          <select
            id="page-size"
            className="dm-input w-28"
            value={pageSize}
            onChange={onPageSizeChange}
            disabled={loading}
          >
            {[10, 25, 50, 100].map((size) => (
              <option key={size} value={size}>{size}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}

function FilterPanel({ open, filters, onApply, onReset, onClose, disabled }) {
  const [draft, setDraft] = React.useState(filters)

  React.useEffect(() => {
    if (open) {
      setDraft(filters)
    }
  }, [filters, open])

  if (!open) {
    return null
  }

  const update = (field, value) => {
    setDraft((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    onApply(draft)
  }

  const handleReset = () => {
    setDraft(initialFilters)
    onReset()
  }

  return (
    <div className="filter-panel" role="dialog" aria-label="Filter för kvitton">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="filter-grid">
          <label className="filter-field">
            <span>Organisationsnummer</span>
            <input
              className="dm-input"
              value={draft.orgnr}
              onChange={(event) => update('orgnr', event.target.value)}
              placeholder="ÅÅÅÅÅÅ-XXXX"
              disabled={disabled}
            />
          </label>
          <label className="filter-field">
            <span>Taggar</span>
            <div className="filter-icon-input">
              <FiTag />
              <input
                className="dm-input"
                value={draft.tag}
                onChange={(event) => update('tag', event.target.value)}
                placeholder="Ex: moms, kort"
                disabled={disabled}
              />
            </div>
          </label>
          <label className="filter-field">
            <span>Från datum</span>
            <div className="filter-icon-input">
              <FiCalendar />
              <input
                type="date"
                className="dm-input"
                value={draft.from}
                onChange={(event) => update('from', event.target.value)}
                disabled={disabled}
              />
            </div>
          </label>
          <label className="filter-field">
            <span>Till datum</span>
            <div className="filter-icon-input">
              <FiCalendar />
              <input
                type="date"
                className="dm-input"
                value={draft.to}
                onChange={(event) => update('to', event.target.value)}
                disabled={disabled}
              />
            </div>
          </label>
        </div>
        <div className="filter-actions">
          <button type="button" className="btn btn-secondary" onClick={handleReset} disabled={disabled}>
            Rensa filter
          </button>
          <div className="spacer" />
          <button type="button" className="btn btn-text" onClick={onClose}>
            Avbryt
          </button>
          <button type="submit" className="btn btn-primary" disabled={disabled}>
            Använd filter
          </button>
        </div>
      </form>
    </div>
  )
}

function usePreviewImage({ receiptId }) {
  const [state, setState] = React.useState({ src: null, loading: false, error: null });

  React.useEffect(() => {
    let cancelled = false;
    let objectUrl = null;
    const sources = [];
    if (receiptId) {
      const base = '/ai/api/receipts/' + receiptId + '/image';
      sources.push(base);
      sources.push(base + '?size=raw');
    }

    if (!sources.length) {
      setState({ src: null, loading: false, error: null });
      return () => {};
    }

    setState({ src: null, loading: true, error: null });

    const load = async () => {
      for (const endpoint of sources) {
        try {
          const res = await api.fetch(endpoint);
          if (!res.ok) {
            continue;
          }
          const blob = await res.blob();
          objectUrl = URL.createObjectURL(blob);
          if (cancelled) {
            URL.revokeObjectURL(objectUrl);
            return;
          }
          setState({ src: objectUrl, loading: false, error: null });
          return;
        } catch (error) {
          if (cancelled) {
            return;
          }
        }
      }
      if (!cancelled) {
        setState({ src: null, loading: false, error: 'Ingen bild tillgänglig' });
      }
    };

    load();

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [receiptId]);

  return state;
}

function ReceiptPreview({ receipt, onPreview, onCache }) {
  const { src, loading, error } = usePreviewImage({ receiptId: receipt.id });

  React.useEffect(() => {
    if (typeof onCache === 'function') {
      onCache(receipt.id, src);
      return () => {
        onCache(receipt.id, null);
      };
    }
    return () => {};
  }, [receipt.id, src, onCache]);

  const label = error ? 'Kunde inte ladda' : 'Ingen bild';

  const handleClick = () => {
    onPreview(receipt, { src, error });
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleClick();
    }
  };

  return (
    <div
      className={`preview-thumb ${loading ? 'opacity-70' : ''}`}
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-label={`Förhandsgranska kvitto ${receipt.id}`}
    >
      {src ? (
        <img src={src} alt={`Förhandsgranskning av kvitto ${receipt.id}`} loading="lazy" />
      ) : (
        <span>{label}</span>
      )}
    </div>
  );
}

function ReceiptPreviewModal({ open, receipt, previewImage, onClose, onReceiptUpdate }) {
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
      resolveCandidates(
        [
          `accounting_proposals[${index}].${field}`,
          field === 'account' ? `accounting_proposals[${index}].account_code` : null,
          `proposals[${index}].${field}`,
          ...extras,
        ].filter(Boolean)
      ),
    [resolveCandidates]
  );

  const receiptData = payload?.receipt || {};
  const receiptDraft = draft?.receipt || {};

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
      const next = prev.proposals.map((proposal, idx) => {
        if (idx !== index) {
          return proposal;
        }
        if (field === 'item_index') {
          return { ...proposal, item_index: Number(value) };
        }
        return { ...proposal, [field]: value };
      });
      return { ...prev, proposals: next };
    });
  };

  const handleToggleEdit = () => {
    if (!payload) {
      return;
    }
    if (editing) {
      setDraft(prepareDraft(payload));
      setEditing(false);
    } else {
      setDraft(prepareDraft(payload));
      setEditing(true);
    }
    setHoverField(null);
    setError(null);
  };

  const handleSave = async () => {
    if (!receipt?.id || !draft) {
      return;
    }
    setSaving(true);
    setError(null);
    const serialisedItems = draft.items.map((item) => ({
      article_id: item.article_id || '',
      name: item.name || '',
      number: item.number === '' ? null : (isNaN(Number(item.number)) ? null : Number(item.number)),
      item_price_ex_vat: item.item_price_ex_vat,
      item_price_inc_vat: item.item_price_inc_vat,
      item_total_price_ex_vat: item.item_total_price_ex_vat,
      item_total_price_inc_vat: item.item_total_price_inc_vat,
      vat: item.vat,
      vat_percentage: item.vat_percentage,
      currency: item.currency || 'SEK',
    }));
    const serialisedProposals = draft.proposals.map((entry) => ({
      account: entry.account || '',
      debit: entry.debit,
      credit: entry.credit,
      vat_rate: entry.vat_rate,
      notes: entry.notes,
      item_index: entry.item_index,
    }));
    const body = {
      receipt: {
        merchant: receiptDraft.merchant,
        orgnr: receiptDraft.orgnr,
        purchase_datetime: receiptDraft.purchase_datetime,
        gross_amount: receiptDraft.gross_amount,
        net_amount: receiptDraft.net_amount,
        expense_type: receiptDraft.expense_type,
        ai_status: receiptDraft.ai_status,
      },
      items: serialisedItems,
      proposals: serialisedProposals,
    };

    try {
      const res = await api.fetch(`/ai/api/receipts/${receipt.id}/modal`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const json = await res.json();
      const refreshed = decorateModalPayload(json.data || {});
      const nextPayload = {
        ...(payload || {}),
        receipt: refreshed.receipt || payload?.receipt || {},
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

  const leftFields = [
    { key: 'merchant', label: 'Företag', highlight: highlightReceiptField('merchant', ['merchant_name']) },
    { key: 'orgnr', label: 'Organisationsnummer', highlight: highlightReceiptField('orgnr') },
    { key: 'purchase_datetime', label: 'Köpdatum', highlight: highlightReceiptField('purchase_datetime', ['purchase_date']) },
    { key: 'gross_amount', label: 'Belopp ink. moms', highlight: highlightReceiptField('gross_amount') },
    { key: 'net_amount', label: 'Belopp ex. moms', highlight: highlightReceiptField('net_amount') },
    { key: 'expense_type', label: 'Utgiftstyp', highlight: highlightReceiptField('expense_type') },
    { key: 'ai_status', label: 'AI-status', highlight: highlightReceiptField('ai_status', ['status']) },
  ];

  const additionalInfo = [
    {
      key: 'ai_confidence',
      label: 'AI-säkerhet',
      highlight: highlightReceiptField('ai_confidence'),
      value: receiptData.ai_confidence != null ? `${Number(receiptData.ai_confidence).toFixed(2)}` : '-',
    },
    {
      key: 'tags',
      label: 'Taggar',
      highlight: highlightReceiptField('tags'),
      value: Array.isArray(receiptData.tags) ? receiptData.tags.join(', ') : receiptDraft.tags || '-',
    },
  ];

  const ocrFieldKey = highlightReceiptField('ocr_raw', ['ocr']);

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
              <FiXCircle />
              <span>{error}</span>
            </div>
          ) : !payload ? (
            <div className="receipt-modal-loading">Ingen data tillgänglig</div>
          ) : (
            <div className="receipt-modal-content">
              <div className="receipt-modal-column receipt-modal-left">
                <div className="receipt-modal-section">
                  <h4>Grunddata</h4>
                  {leftFields.map((field) => {
                    const highlight = field.highlight;
                    return (
                      <div
                        key={field.key}
                        className={`receipt-modal-field ${matchHighlight(highlight)}`}
                        onMouseEnter={() => setHoverField(highlight)}
                        onMouseLeave={() => setHoverField(null)}
                      >
                        <label className="field-label" htmlFor={`receipt-${field.key}`}>{field.label}</label>
                        {editing ? (
                          <input
                            id={`receipt-${field.key}`}
                            className="dm-input"
                            value={receiptDraft[field.key] ?? ''}
                            onChange={(event) => updateReceiptDraft(field.key, event.target.value)}
                            disabled={saving}
                          />
                        ) : field.key === 'gross_amount' || field.key === 'net_amount' ? (
                          <div className="field-value">{formatCurrency(Number(receiptData[field.key] || 0))}</div>
                        ) : field.key === 'purchase_datetime' ? (
                          <div className="field-value">{formatDate(receiptData.purchase_datetime)}</div>
                        ) : (
                          <div className="field-value">{receiptData[field.key] || receiptDraft[field.key] || '-'}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="receipt-modal-section">
                  <h4>Status & metadata</h4>
                  {additionalInfo.map((info) => (
                    <div
                      key={info.key}
                      className={`receipt-modal-field ${matchHighlight(info.highlight)}`}
                      onMouseEnter={() => setHoverField(info.highlight)}
                      onMouseLeave={() => setHoverField(null)}
                    >
                      <div className="field-label">{info.label}</div>
                      <div className="field-value">{info.value}</div>
                    </div>
                  ))}
                </div>
                <div
                  className={`receipt-modal-section ocr-section ${matchHighlight(ocrFieldKey)}`}
                  onMouseEnter={() => setHoverField(ocrFieldKey)}
                  onMouseLeave={() => setHoverField(null)}
                >
                  <h4>OCR-text</h4>
                  <div className="ocr-content">{receiptDraft.ocr_raw || 'Ingen OCR-data tillgänglig'}</div>
                </div>
              </div>
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
              <div className="receipt-modal-column receipt-modal-right">
                <div className="receipt-modal-section">
                  <h4>Varor och kontering</h4>
                  {itemsSource.length === 0 ? (
                    <div className="field-value muted">Inga varor registrerade</div>
                  ) : (
                    itemsSource.map((item, itemIndex) => (
                      <div key={`item-${itemIndex}`} className="receipt-item-card">
                        <div className="receipt-item-header">Rad {itemIndex + 1}</div>
                        {['name', 'number', 'item_price_inc_vat', 'item_total_price_inc_vat', 'vat_percentage'].map((field) => {
                          const labels = {
                            name: 'Artikel',
                            number: 'Antal',
                            item_price_inc_vat: 'Pris (ink. moms)',
                            item_total_price_inc_vat: 'Totalt (ink. moms)',
                            vat_percentage: 'Moms %',
                          };
                          const highlight = highlightItemField(itemIndex, field);
                          const value = editing && draft ? draft.items[itemIndex][field] : item[field];
                          return (
                            <div
                              key={`${field}-${itemIndex}`}
                              className={`receipt-modal-field ${matchHighlight(highlight)}`}
                              onMouseEnter={() => setHoverField(highlight)}
                              onMouseLeave={() => setHoverField(null)}
                            >
                              <div className="field-label">{labels[field]}</div>
                              {editing ? (
                                <input
                                  className="dm-input"
                                  value={value ?? ''}
                                  onChange={(event) => updateItemDraft(itemIndex, field, event.target.value)}
                                />
                              ) : (
                                <div className="field-value">{value || '-'}</div>
                              )}
                            </div>
                          );
                        })}
                        <div className="proposal-group">
                          <div className="proposal-group-header">Konteringsrader</div>
                          {(proposalsByItem[itemIndex] || []).length === 0 ? (
                            <div className="field-value muted">Inga konteringsförslag</div>
                          ) : (
                            proposalsByItem[itemIndex].map((proposal) => {
                              const globalIndex = proposal._globalIndex;
                              return (
                                <div key={`proposal-${globalIndex}`} className="proposal-card">
                                  {['account', 'debit', 'credit', 'vat_rate', 'notes'].map((field) => {
                                    const labels = {
                                      account: 'Konto',
                                      debit: 'Debet',
                                      credit: 'Kredit',
                                      vat_rate: 'Moms %',
                                      notes: 'Notering',
                                    };
                                    const highlight = highlightProposalField(globalIndex, field);
                                    const value = editing && draft ? draft.proposals[globalIndex][field] : proposal[field];
                                    return (
                                      <div
                                        key={`${field}-${globalIndex}`}
                                        className={`receipt-modal-field proposal-field ${matchHighlight(highlight)}`}
                                        onMouseEnter={() => setHoverField(highlight)}
                                        onMouseLeave={() => setHoverField(null)}
                                      >
                                        <div className="field-label">{labels[field]}</div>
                                        {editing ? (
                                          <input
                                            className="dm-input"
                                            value={value ?? ''}
                                            onChange={(event) => updateProposalDraft(globalIndex, field, event.target.value)}
                                          />
                                        ) : (
                                          <div className="field-value">{value || '-'}</div>
                                        )}
                                      </div>
                                    );
                                  })}
                                  <div
                                    className={`receipt-modal-field proposal-field ${matchHighlight(highlightProposalField(globalIndex, 'item_index'))}`}
                                    onMouseEnter={() => setHoverField(highlightProposalField(globalIndex, 'item_index'))}
                                    onMouseLeave={() => setHoverField(null)}
                                  >
                                    <div className="field-label">Kopplad rad</div>
                                    {editing ? (
                                      <select
                                        className="dm-input"
                                        value={draft?.proposals?.[globalIndex]?.item_index ?? itemIndex}
                                        onChange={(event) => updateProposalDraft(globalIndex, 'item_index', Number(event.target.value))}
                                      >
                                        {itemsSource.map((_, idx) => (
                                          <option key={`proposal-link-${idx}`} value={idx}>
                                            Rad {idx + 1}
                                          </option>
                                        ))}
                                      </select>
                                    ) : (
                                      <div className="field-value">Rad {(proposal.item_index ?? itemIndex) + 1}</div>
                                    )}
                                  </div>
                                </div>
                              );
                            })
                          )}
                        </div>
                      </div>
                    ))
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

function MapModal({ open, receipt, onClose }) {
  if (!open || !receipt) {
    return null;
  }

  const handleBackdrop = (event) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  const location = receipt.location;
  const lat = location?.lat;
  const lon = location?.lon;
  const accuracy = location?.accuracy;
  const hasCoordinates = lat != null && lon != null && lat !== 0 && lon !== 0;

  return (
    <div className="modal-backdrop" role="dialog" aria-label={`Karta för kvitto ${receipt.id}`} onClick={handleBackdrop}>
      <div className="modal modal-lg" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Plats för kvitto</h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng karta">
            <FiX />
          </button>
        </div>
        <div className="modal-body" style={{ height: '500px', padding: 0 }}>
          {hasCoordinates ? (
            <div style={{ width: '100%', height: '100%', position: 'relative' }}>
              <iframe
                width="100%"
                height="100%"
                style={{ border: 0, borderRadius: '8px' }}
                src={`https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.01},${lat-0.01},${lon+0.01},${lat+0.01}&layer=mapnik&marker=${lat},${lon}`}
                title={`Karta för kvitto ${receipt.id}`}
              />
              <div style={{
                position: 'absolute',
                top: '10px',
                left: '10px',
                background: 'rgba(255, 255, 255, 0.9)',
                padding: '8px 12px',
                borderRadius: '6px',
                fontSize: '12px',
                fontFamily: 'monospace',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
              }}>
                <div>Lat: {lat.toFixed(6)}</div>
                <div>Lng: {lon.toFixed(6)}</div>
                {accuracy && <div>Noggrannhet: ±{accuracy}m</div>}
              </div>
              <div style={{
                position: 'absolute',
                bottom: '10px',
                right: '10px'
              }}>
                <a
                  href={`https://www.google.com/maps?q=${lat},${lon}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-primary btn-sm"
                  style={{ fontSize: '12px' }}
                >
                  Google Maps
                </a>
              </div>
            </div>
          ) : (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              background: '#f5f5f5',
              borderRadius: '8px'
            }}>
              <div style={{ textAlign: 'center' }}>
                <FiMapPin size={48} style={{ color: '#ccc', marginBottom: '16px' }} />
                <div style={{ fontSize: '16px', color: '#666' }}>
                  Ingen platsdata tillgänglig för detta kvitto
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Stäng
          </button>
        </div>
      </div>
    </div>
  );
}

function ItemsModal({ open, receipt, onClose }) {
  const [items, setItems] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (!open || !receipt) {
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const fetchItems = async () => {
      try {
        const res = await api.fetch(`/ai/api/receipts/${receipt.id}/line-items`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          const itemsList = Array.isArray(data) ? data : (data.line_items || data.items || []);
          setItems(itemsList);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      }
    };

    fetchItems();

    return () => {
      cancelled = true;
    };
  }, [open, receipt]);

  if (!open || !receipt) {
    return null;
  }

  const handleBackdrop = (event) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-label={`Varor för kvitto ${receipt.id}`} onClick={handleBackdrop}>
      <div className="modal modal-lg" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Varor - {receipt.merchant || 'Okänt företag'}</h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng varor">
            <FiX />
          </button>
        </div>
        <div className="modal-body">
          {loading ? (
            <div className="loading-inline">
              <div className="loading-spinner" />
              <span>Laddar varor...</span>
            </div>
          ) : error ? (
            <div className="alert alert-error">
              <FiXCircle />
              <span>{error}</span>
            </div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
              Inga varor registrerade för detta kvitto
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="table-dark">
                <thead>
                  <tr>
                    <th>Beskrivning</th>
                    <th className="text-right">Antal</th>
                    <th className="text-right">Pris</th>
                    <th className="text-right">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, index) => (
                    <tr key={index}>
                      <td>{item.description || item.item_name || '-'}</td>
                      <td className="text-right">{item.quantity || 1}</td>
                      <td className="text-right">{formatCurrency(item.unit_price || item.price || 0)}</td>
                      <td className="text-right font-semibold">
                        {formatCurrency((item.quantity || 1) * (item.unit_price || item.price || 0))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Stäng
          </button>
        </div>
      </div>
    </div>
  );
}

function Pagination({ page, totalPages, onPrev, onNext }) {
  if (totalPages <= 1) {
    return null
  }
  return (
    <div className="pagination">
      <button type="button" className="btn btn-secondary btn-sm" onClick={onPrev} disabled={page <= 1}>
        <FiChevronLeft />
        Föregående
      </button>
      <div className="pagination-status">
        Sida {page} av {totalPages}
      </div>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onNext} disabled={page >= totalPages}>
        Nästa
        <FiChevronRight />
      </button>
    </div>
  )
}

export default function ReceiptsList() {
  const [items, setItems] = React.useState([])
  const [meta, setMeta] = React.useState({ page: 1, page_size: 25, total: 0 })
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(25)
  const [loading, setLoading] = React.useState(false)
  const [banner, setBanner] = React.useState(null)
  const [searchTerm, setSearchTerm] = React.useState('')
  const [filters, setFilters] = React.useState(initialFilters)
  const [isFilterOpen, setFilterOpen] = React.useState(false)
  const [isPreviewOpen, setPreviewOpen] = React.useState(false)
  const [previewImage, setPreviewImage] = React.useState(null)
  const [isMapOpen, setMapOpen] = React.useState(false)
  const [isItemsOpen, setItemsOpen] = React.useState(false)
  const [selectedReceipt, setSelectedReceipt] = React.useState(null)
  const previewCache = React.useRef(new Map())

  const updateReceiptInList = React.useCallback((updated) => {
    if (!updated || !updated.id) {
      return
    }
    setItems((prev) => prev.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)))
    setSelectedReceipt((prev) => (prev && prev.id === updated.id ? { ...prev, ...updated } : prev))
  }, [])

  const loadReceipts = React.useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    if (searchTerm) {
      params.set('merchant', searchTerm)
    }
    if (filters.orgnr) params.set('orgnr', filters.orgnr)
    if (filters.from) params.set('from', filters.from)
    if (filters.to) params.set('to', filters.to)
    if (filters.tag) params.set('tags', filters.tag)

    try {
      const res = await api.fetch(`/ai/api/receipts?${params.toString()}`)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = await res.json()
      const list = Array.isArray(payload?.items) ? payload.items : []
      const fetchedMeta = payload?.meta || {}
      setItems(list)
      setMeta({
        page: fetchedMeta.page ?? page,
        page_size: fetchedMeta.page_size ?? pageSize,
        total: fetchedMeta.total ?? list.length
      })
      setBanner({
        type: 'info',
        message: `Visar ${list.length} av ${fetchedMeta.total ?? list.length} kvitton`
      })
    } catch (error) {
      console.error('Receipts fetch failed', error)
      setItems([])
      setMeta((prev) => ({ ...prev, total: 0 }))
      setBanner({
        type: 'error',
        message: `Kunde inte hämta kvitton: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchTerm, filters])

  React.useEffect(() => {
    loadReceipts()
  }, [loadReceipts])

  const displayedItems = React.useMemo(() => {
    const term = searchTerm.trim().toLowerCase()
    if (!term) {
      return items
    }
    const numericValue = Number(term.replace(',', '.'))
    const hasNumeric = !Number.isNaN(numericValue)
    return items.filter((item) => {
      const merchantMatch = item.merchant?.toLowerCase().includes(term)
      const fileMatch = item.original_filename?.toLowerCase().includes(term)
      const idMatch = String(item.id || '').toLowerCase().includes(term)
      const amountMatch = hasNumeric
        ? Number(item.net_amount || 0) === numericValue || Number(item.gross_amount || 0) === numericValue
        : false
      return merchantMatch || fileMatch || idMatch || amountMatch
    })
  }, [items, searchTerm])

  const totalPages = React.useMemo(() => {
    const perPage = meta.page_size || pageSize || 1
    const total = meta.total || displayedItems.length || 1
    return Math.max(1, Math.ceil(total / perPage))
  }, [meta, displayedItems.length, pageSize])

  const handleSearch = (term) => {
    setSearchTerm(term)
    setPage(1)
  }

  const handleResetSearch = () => {
    setSearchTerm('')
    setPage(1)
  }

  const handleFiltersApply = (nextFilters) => {
    setFilters(nextFilters)
    setFilterOpen(false)
    setPage(1)
  }

  const handleFiltersReset = () => {
    setFilters(initialFilters)
    setPage(1)
  }

  const handlePageSizeChange = (event) => {
    const size = Number(event.target.value)
    if (!Number.isNaN(size)) {
      setPageSize(size)
      setPage(1)
    }
  }

  const handlePrevPage = () => {
    setPage((prev) => Math.max(1, prev - 1))
  }

  const handleNextPage = () => {
    setPage((prev) => Math.min(totalPages, prev + 1))
  }

  const handlePreview = (receipt, previewData = null) => {
    if (!receipt) {
      return
    }
    const cachedSrc = previewData?.src || previewCache.current.get(receipt.id) || null
    setSelectedReceipt(receipt)
    setPreviewImage(cachedSrc)
    setPreviewOpen(true)
  };

  const handleShowMap = (receipt) => {
    setSelectedReceipt(receipt);
    setMapOpen(true);
  };

  const handleShowItems = (receipt) => {
    setSelectedReceipt(receipt);
    setItemsOpen(true);
  };

  const closePreview = () => {
    setPreviewOpen(false);
    setPreviewImage(null);
  };

  const closeMap = () => {
    setMapOpen(false);
    setSelectedReceipt(null);
  };

  const closeItems = () => {
    setItemsOpen(false);
    setSelectedReceipt(null);
  };

  const dismissBanner = () => setBanner(null)

  return (
    <div className="space-y-6">
      <div className="card hero-card">
        <div className="flex items-center justify-between flex-col lg:flex-row gap-4">
          <div>
            <h1 className="text-2xl font-bold mb-2">Kvitton</h1>
            <p className="text-sm text-gray-300">Hantera och filtrera kvitton (endast kvitton från unified_files)</p>
          </div>
          <div className="flex gap-2">
            <button className="btn btn-secondary" onClick={() => setFilterOpen((prev) => !prev)}>
              <FiFilter />
              Filter
            </button>
            <button className="btn btn-primary" onClick={loadReceipts} disabled={loading}>
              <FiRefreshCw className={loading ? 'animate-spin' : ''} />
              Uppdatera
            </button>
          </div>
        </div>
      </div>

      <Banner banner={banner} onDismiss={dismissBanner} />

      <FilterPanel
        open={isFilterOpen}
        filters={filters}
        onApply={handleFiltersApply}
        onReset={handleFiltersReset}
        onClose={() => setFilterOpen(false)}
        disabled={loading}
      />

      <SearchAndFilters
        searchTerm={searchTerm}
        onSearch={handleSearch}
        onReset={handleResetSearch}
        loading={loading}
        pageSize={pageSize}
        onPageSizeChange={handlePageSizeChange}
      />

      <div className="card overflow-hidden">
        <div className="card-header">
          <div>
            <h3 className="card-title">Alla kvitton ({meta.total})</h3>
            <p className="card-subtitle">Sorterat efter senaste först</p>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="table-dark">
            <thead>
              <tr>
                <th>Preview</th>
                <th>Företag</th>
                <th>Köpdatum</th>
                <th className="text-right">Belopp ex moms</th>
                <th className="text-right">Belopp ink moms</th>
                <th className="text-center">Match First Card</th>
                <th>Utgiftstyp</th>
                <th>Kort sista 4</th>
                <th>Korttyp</th>
                <th>Betalningssätt</th>
                <th className="text-center">Åtgärder</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={11} className="table-loading">
                    <div className="loading-inline">
                      <div className="loading-spinner" />
                      <span>Laddar kvitton...</span>
                    </div>
                  </td>
                </tr>
              ) : displayedItems.length === 0 ? (
                <tr>
                  <td colSpan={11} className="table-empty">
                    <div className="space-y-2">
                      <div>Inga kvitton hittades</div>
                      <div className="text-sm text-gray-400">Justera filter eller sök</div>
                    </div>
                  </td>
                </tr>
              ) : (
                displayedItems.map((receipt) => (
                  <tr key={receipt.id}>
                    <td>
                      <ReceiptPreview
                        receipt={receipt}
                        onPreview={(data) => handlePreview(receipt, data)}
                        onCache={(id, src) => {
                          if (src) {
                            previewCache.current.set(id, src)
                          } else {
                            previewCache.current.delete(id)
                          }
                        }}
                      />
                    </td>
                    <td>
                      <div className="font-medium">{receipt.merchant || 'Okänt bolag'}</div>
                    </td>
                    <td>
                      <div className="font-medium">{formatDate(receipt.purchase_date || receipt.purchase_datetime)}</div>
                    </td>
                    <td className="text-right">{formatCurrency(receipt.net_amount)}</td>
                    <td className="text-right text-lg font-semibold">{formatCurrency(receipt.gross_amount)}</td>
                    <td className="text-center">
                      {receipt.match_first_card ? (
                        <FiCheckCircle className="text-green-500 inline-block text-xl" />
                      ) : (
                        <FiXCircle className="text-red-500 inline-block text-xl" />
                      )}
                    </td>
                    <td>{receipt.expense_type || '-'}</td>
                    <td className="font-mono">{receipt.card_last_four || '-'}</td>
                    <td>{receipt.card_type || '-'}</td>
                    <td>{receipt.payment_method || '-'}</td>
                    <td className="text-center">
                      <div className="flex gap-2 justify-center">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleShowMap(receipt)}
                          title="Visa på karta"
                        >
                          <FiMapPin />
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleShowItems(receipt)}
                          title="Visa varor"
                        >
                          <FiShoppingCart />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Pagination page={page} totalPages={totalPages} onPrev={handlePrevPage} onNext={handleNextPage} />

      <ReceiptPreviewModal
        open={isPreviewOpen}
        receipt={selectedReceipt}
        previewImage={previewImage}
        onClose={closePreview}
        onReceiptUpdate={updateReceiptInList}
      />
      <MapModal open={isMapOpen} receipt={selectedReceipt} onClose={closeMap} />
      <ItemsModal open={isItemsOpen} receipt={selectedReceipt} onClose={closeItems} />
    </div>
  )
}
