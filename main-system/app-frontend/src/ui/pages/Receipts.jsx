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
  FiChevronRight,
  FiTrash2,
  FiFileText,
  FiAlertCircle
} from 'react-icons/fi'
import { api } from '../api'
import ReceiptPreviewModal from '../components/ReceiptPreviewModal'

const INITIAL_LOG_STATE = {
  open: false,
  loading: false,
  error: null,
  data: null,
  receiptId: null,
}
// Force Vite reload

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

function formatDate(value, includeTime = false) {
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
    if (includeTime) {
      return `${parsed.toLocaleDateString('sv-SE')} ${parsed.toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' })}`
    }
    return parsed.toLocaleDateString('sv-SE')
  } catch (error) {
    return typeof value === 'string' ? value : '-'
  }
}

function formatDurationMs(ms) {
  if (ms == null || ms === 0) return '0ms'
  if (ms < 1000) return `${ms}ms`
  const sec = (ms / 1000).toFixed(1)
  return `${sec}s`
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
  const [sortColumn, setSortColumn] = React.useState('purchase_datetime')
  const [sortDirection, setSortDirection] = React.useState('desc')
  const [logState, setLogState] = React.useState(INITIAL_LOG_STATE)

  const fetchReceiptLog = React.useCallback(async (receiptId) => {
    if (!receiptId) {
      return
    }
    setLogState((prev) => ({
      open: true,
      loading: true,
      error: null,
      data: prev.receiptId === receiptId ? prev.data : null,
      receiptId,
    }))
    try {
      const res = await api.fetch(`/ai/api/receipts/${receiptId}/log`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const payload = await res.json()
      setLogState({
        open: true,
        loading: false,
        error: null,
        data: payload,
        receiptId,
      })
    } catch (error) {
      console.error('Failed to fetch receipt log', error)
      setLogState({
        open: true,
        loading: false,
        error: error instanceof Error ? error.message : String(error),
        data: null,
        receiptId,
      })
    }
  }, [])

  const closeLogViewer = React.useCallback(() => {
    setLogState(INITIAL_LOG_STATE)
  }, [])

  const updateReceiptInList = React.useCallback((updated) => {
    if (!updated || !updated.id) {
      return
    }

    if (updated.deleted) {
      // Handle navigation after deletion using state updater
      if (updated.shouldNavigateNext) {
        setItems((prevItems) => {
          const currentIndex = prevItems.findIndex(item => item.id === updated.id)
          const newList = prevItems.filter(item => item.id !== updated.id)

          // The next receipt will now be at the same index as the deleted one
          if (currentIndex >= 0 && currentIndex < newList.length) {
            const nextReceipt = newList[currentIndex]
            setSelectedReceipt(nextReceipt)
            setPreviewImage(null)
          } else {
            // No more receipts, close modal
            setSelectedReceipt(null)
            setIsPreviewOpen(false)
          }

          return newList
        })
      } else {
        // Remove from items list and close modal
        setItems((prev) => prev.filter((item) => item.id !== updated.id))
        setSelectedReceipt(null)
        setIsPreviewOpen(false)
      }
    } else {
      setItems((prev) => prev.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)))
      setSelectedReceipt((prev) => (prev && prev.id === updated.id ? { ...prev, ...updated } : prev))
    }
  }, [])

  const loadReceipts = React.useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true)
    }
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
    if (sortColumn) params.set('sort_by', sortColumn)
    if (sortDirection) params.set('sort_order', sortDirection)

    try {
      const res = await api.fetch(`/ai/api/receipts?${params.toString()}`)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = await res.json()
      const list = Array.isArray(payload?.items) ? payload.items : []
      const filteredList = list.filter((item) => {
        const workflowType = String(item?.workflow_type || '').toLowerCase()
        if (workflowType && workflowType !== 'receipt') {
          return false
        }
        const fileType = String(item?.file_type || '').toLowerCase()
        if (workflowType === 'creditcard_invoice') {
          return false
        }
        if (fileType.startsWith('cc_') || fileType === 'credit_card') {
          return false
        }
        return true
      })
      const fetchedMeta = payload?.meta || {}

      // Only update state if data has actually changed (prevents flickering during silent refresh)
      setItems(prevItems => {
        if (silent && JSON.stringify(prevItems) === JSON.stringify(filteredList)) {
          return prevItems
        }
        return filteredList
      })

      setMeta({
        page: fetchedMeta.page ?? page,
        page_size: fetchedMeta.page_size ?? pageSize,
        total: fetchedMeta.total ?? filteredList.length
      })
      if (!silent) {
        setBanner({
          type: 'info',
          message: `Visar ${filteredList.length} kvitton`
        })
      }
    } catch (error) {
      console.error('Receipts fetch failed', error)
      if (!silent) {
        setItems([])
        setMeta((prev) => ({ ...prev, total: 0 }))
        setBanner({
          type: 'error',
          message: `Kunde inte hämta kvitton: ${error instanceof Error ? error.message : error}`
        })
      }
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }, [page, pageSize, searchTerm, filters, sortColumn, sortDirection])

  React.useEffect(() => {
    loadReceipts()
  }, [loadReceipts])

  // Polling för automatisk uppdatering av status (konfigurerbart intervall från .env)
  React.useEffect(() => {
    const refreshInterval = (import.meta.env.VITE_REFRESH_INTERVAL_SECONDS || 10) * 1000
    const intervalId = setInterval(() => {
      // Ladda om data tyst utan att visa loading-spinner eller uppdatera banner
      loadReceipts(true)
    }, refreshInterval)

    return () => clearInterval(intervalId)
  }, [loadReceipts])

  const handleSort = React.useCallback((column) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }, [sortColumn])

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

  // Modal navigation
  const currentReceiptIndex = React.useMemo(() => {
    if (!selectedReceipt) return -1
    return displayedItems.findIndex(item => item.id === selectedReceipt.id)
  }, [displayedItems, selectedReceipt])

  const handleNavigateNext = React.useCallback(() => {
    if (currentReceiptIndex >= 0 && currentReceiptIndex < displayedItems.length - 1) {
      const nextReceipt = displayedItems[currentReceiptIndex + 1]
      setSelectedReceipt(nextReceipt)
      setPreviewImage(null)
    }
  }, [currentReceiptIndex, displayedItems])

  const handleNavigatePrevious = React.useCallback(() => {
    if (currentReceiptIndex > 0) {
      const prevReceipt = displayedItems[currentReceiptIndex - 1]
      setSelectedReceipt(prevReceipt)
      setPreviewImage(null)
    }
  }, [currentReceiptIndex, displayedItems])

  const hasNext = currentReceiptIndex >= 0 && currentReceiptIndex < displayedItems.length - 1
  const hasPrevious = currentReceiptIndex > 0

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

  const handleDelete = async (receipt) => {
    try {
      const res = await api.fetch(`/ai/api/receipts/${receipt.id}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      setItems((prev) => prev.filter((item) => item.id !== receipt.id));
      setMeta((prev) => ({ ...prev, total: Math.max(0, prev.total - 1) }));
    } catch (error) {
      console.error('Delete failed', error);
      setBanner({
        type: 'error',
        message: `Kunde inte radera kvitto: ${error instanceof Error ? error.message : error}`
      });
    }
  };

  const dismissBanner = () => setBanner(null)

  const renderLogModal = () => {
    if (!logState.open) {
      return null
    }

    const logData = logState.data ?? {}
    const workflowRuns = Array.isArray(logData?.workflow_runs) ? logData.workflow_runs : []
    const aiHistory = Array.isArray(logData?.ai_history) ? logData.ai_history : []
    const files = Array.isArray(logData?.files) ? logData.files : []
    const receiptIdForModal = logData?.receipt_id || logState.receiptId

    const handleBackdrop = (event) => {
      if (event.target === event.currentTarget) {
        closeLogViewer()
      }
    }

    return (
      <div className="modal-backdrop" role="dialog" aria-label="Bearbetningslogg" onClick={handleBackdrop}>
        <div
          className="modal"
          onClick={(event) => event.stopPropagation()}
          style={{ maxWidth: '960px' }}
        >
          <div className="modal-header">
            <div>
              <h3>Bearbetningslogg</h3>
              <p className="text-xs text-gray-400 mt-1">
                Kvitto: {receiptIdForModal || 'okänt'}
              </p>
            </div>
            <button type="button" className="icon-button" onClick={closeLogViewer} aria-label="Stäng logg">
              <FiX />
            </button>
          </div>

          <div className="modal-body space-y-6 max-h-[70vh] overflow-y-auto">
            {logState.loading ? (
              <div className="flex items-center justify-center gap-3 py-10 text-gray-200">
                <div className="loading-spinner" />
                <span>Hämtar logg...</span>
              </div>
            ) : logState.error ? (
              <div className="alert alert-error">
                <FiAlertCircle className="mr-2" />
                <span>{`Misslyckades att hämta logg: ${logState.error}`}</span>
              </div>
            ) : (
              <>
                <section>
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                      Workflowkörningar
                    </h4>
                    <span className="text-xs text-gray-500">
                      {workflowRuns.length ? `${workflowRuns.length} st` : 'Inga loggar'}
                    </span>
                  </div>
                  {workflowRuns.length === 0 ? (
                    <p className="text-xs text-gray-400 mt-2">Inga workflow-loggar hittades för detta kvitto.</p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {workflowRuns.map((run) => (
                        <div key={run.id} className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-gray-100">
                                {run.workflow_key} · {run.status}
                              </div>
                              <div className="text-xs text-gray-400">
                                Run-ID: {run.id} · Källa: {run.source_channel || 'okänd'}
                              </div>
                            </div>
                            <div className="text-xs text-gray-400 text-right">
                              <div>Start: {formatDate(run.created_at, true)}</div>
                              <div>Senast: {formatDate(run.updated_at, true)}</div>
                            </div>
                          </div>
                          {Array.isArray(run.stages) && run.stages.length > 0 ? (
                            <div className="space-y-2">
                              {run.stages.map((stage, index) => (
                                <div
                                  key={`${run.id}-${stage.stage_key}-${stage.started_at || stage.finished_at || index}`}
                                  className="bg-gray-800/70 border border-gray-700/70 rounded-md px-3 py-2 space-y-1"
                                >
                                  <div className="flex flex-wrap items-center justify-between text-sm font-medium text-gray-100">
                                    <span>{stage.stage_key}</span>
                                    <span>{stage.status}</span>
                                  </div>
                                  <div className="flex flex-wrap items-center justify-between text-xs text-gray-400">
                                    <span>
                                      {formatDate(stage.started_at, true)}{stage.finished_at ? ` → ${formatDate(stage.finished_at, true)}` : ''}
                                    </span>
                                    {stage.duration_ms != null && (
                                      <span>{formatDurationMs(stage.duration_ms)}</span>
                                    )}
                                  </div>
                                  {stage.message && (
                                    <pre className="mt-2 text-xs text-gray-300 whitespace-pre-wrap font-mono">
                                      {stage.message}
                                    </pre>
                                  )}
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-gray-500">Inga steg registrerade.</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section>
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                      AI-historik
                    </h4>
                    <span className="text-xs text-gray-500">
                      {aiHistory.length ? `${aiHistory.length} poster` : 'Inga AI-loggar'}
                    </span>
                  </div>
                  {aiHistory.length === 0 ? (
                    <p className="text-xs text-gray-400 mt-2">
                      Ingen AI-historik registrerad för detta kvitto.
                    </p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {aiHistory.map((entry) => (
                        <div key={entry.id} className="bg-gray-900 border border-gray-700 rounded-lg p-3 space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-gray-100">
                                {(entry.ai_stage_name || entry.job_type || 'Okänt steg')} · {entry.status}
                              </div>
                              <div className="text-xs text-gray-400">
                                Fil: {entry.file_id} · {formatDate(entry.created_at, true)}
                              </div>
                            </div>
                            <div className="text-xs text-gray-400 text-right space-y-1">
                              {(entry.provider || entry.model) && (
                                <div>
                                  {entry.provider || 'okänd'}{entry.model ? ` · ${entry.model}` : ''}
                                </div>
                              )}
                              {entry.processing_time_ms != null && (
                                <div>Tid: {formatDurationMs(entry.processing_time_ms)}</div>
                              )}
                              {entry.confidence != null && (
                                <div>Konfidens: {Math.round(entry.confidence * 100)}%</div>
                              )}
                            </div>
                          </div>
                          {entry.log_text && (
                            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono bg-gray-800/70 border border-gray-700/70 rounded-md p-2">
                              {entry.log_text}
                            </pre>
                          )}
                          {entry.error_message && (
                            <div className="text-xs text-red-300 bg-red-900/30 border border-red-800/40 rounded-md p-2 whitespace-pre-wrap font-mono">
                              {entry.error_message}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section>
                  <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                    Filer
                  </h4>
                  {files.length === 0 ? (
                    <p className="text-xs text-gray-400 mt-2">
                      Inga relaterade filer hittades i unified_files.
                    </p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {files.map((file) => (
                        <div key={file.id} className="bg-gray-900 border border-gray-700 rounded-lg p-3 space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-100">
                            <span className="font-semibold">{file.id}</span>
                            <span className="text-xs text-gray-400">
                              Skapad: {formatDate(file.created_at, true)}
                              {file.updated_at ? ` · Uppdaterad: ${formatDate(file.updated_at, true)}` : ''}
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-300">
                            <div>Filtyp: {file.file_type || '–'}</div>
                            <div>Workflow-typ: {file.workflow_type || '–'}</div>
                            <div>Status: {file.ai_status || '–'}</div>
                            <div>
                              Konfidens: {file.ai_confidence != null ? `${Math.round(file.ai_confidence * 100)}%` : '–'}
                            </div>
                            <div>OCR-tecken: {file.ocr_raw_length ?? 0}</div>
                          </div>
                          {file.ocr_raw_length > 0 && (
                            <details className="bg-gray-800/60 border border-gray-700/60 rounded-md p-2">
                              <summary className="text-xs text-gray-300 cursor-pointer">
                                Visa OCR-text ({file.ocr_raw_length} tecken)
                              </summary>
                              <pre className="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                                {file.ocr_raw}
                              </pre>
                            </details>
                          )}
                          {file.other_data && Object.keys(file.other_data).length > 0 && (
                            <details className="bg-gray-800/50 border border-gray-700/60 rounded-md p-2">
                              <summary className="text-xs text-gray-300 cursor-pointer">
                                Visa other_data
                              </summary>
                              <pre className="mt-2 text-xs text-gray-200 whitespace-pre-wrap font-mono overflow-x-auto">
                                {JSON.stringify(file.other_data, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              </>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-text" onClick={closeLogViewer}>
              Stäng
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => logState.receiptId && fetchReceiptLog(logState.receiptId)}
              disabled={logState.loading || !logState.receiptId}
            >
              {logState.loading ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Hämtar...
                </>
              ) : (
                <>
                  <FiRefreshCw className="mr-2" />
                  Ladda om
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    )
  }

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
                <th>Förhandsvisning</th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('company')}>
                  Företag {sortColumn === 'company' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('purchase_datetime')}>
                  Inköpsdatum {sortColumn === 'purchase_datetime' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="text-right cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('net_amount')}>
                  Belopp ex moms {sortColumn === 'net_amount' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="text-right cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('gross_amount')}>
                  Belopp ink moms {sortColumn === 'gross_amount' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="text-center cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('firstcard_matched')}>
                  Matchning {sortColumn === 'firstcard_matched' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('expense_type')}>
                  Utgiftstyp {sortColumn === 'expense_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('credit_card_last_4')}>
                  Kort sista 4 {sortColumn === 'credit_card_last_4' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('credit_card_type')}>
                  Korttyp {sortColumn === 'credit_card_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('payment_type')}>
                  Betalningssätt {sortColumn === 'payment_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
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
                    <td className="font-mono">{receipt.credit_card_last_4 || '-'}</td>
                    <td>{receipt.credit_card_type || '-'}</td>
                    <td>{receipt.payment_type || '-'}</td>
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
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => fetchReceiptLog(receipt.id)}
                          title="Visa logg"
                        >
                          <FiFileText />
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(receipt)}
                          title="Radera kvitto"
                        >
                          <FiTrash2 />
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
        onNavigateNext={handleNavigateNext}
        onNavigatePrevious={handleNavigatePrevious}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
      />
      <MapModal open={isMapOpen} receipt={selectedReceipt} onClose={closeMap} />
      <ItemsModal open={isItemsOpen} receipt={selectedReceipt} onClose={closeItems} />
      {renderLogModal()}
    </div>
  )
}
