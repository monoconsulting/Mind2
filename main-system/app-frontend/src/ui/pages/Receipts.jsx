import React from 'react'
import {
  FiSearch,
  FiFilter,
  FiDownload,
  FiRefreshCw,
  FiEye,
  FiX,
  FiCheckCircle,
  FiDollarSign,
  FiFileText,
  FiInfo,
  FiAlertCircle,
  FiCalendar,
  FiTag,
  FiChevronLeft,
  FiChevronRight,
  FiMapPin
} from 'react-icons/fi'
import { api } from '../api'

const statusOptions = [
  { value: '', label: 'Alla statusar' },
  { value: 'processing', label: 'Bearbetas' },
  { value: 'queued', label: 'I kö' },
  { value: 'failed', label: 'Fel' },
  { value: 'passed', label: 'Godkänd' },
  { value: 'completed', label: 'Klar' },
  { value: 'manual_review', label: 'Manuell kontroll' },
  { value: 'needs_review', label: 'Behöver kontroll' }
]

const initialFilters = {
  status: '',
  from: '',
  to: '',
  orgnr: '',
  tag: ''
}

const statusClassMap = {
  processing: 'status-processing',
  queued: 'status-queued',
  failed: 'status-failed',
  passed: 'status-passed',
  completed: 'status-passed',
  manual_review: 'status-manual_review',
  needs_review: 'status-manual_review'
}

const initialPreviewState = {
  receipt: null,
  imageUrl: null,
  loading: false,
  error: null,
  revokeOnClose: false,
  cachedImageUrl: null
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

function translateStatus(status) {
  if (!status) {
    return ''
  }
  const normalized = String(status).toLowerCase()
  const map = {
    processing: 'Bearbetas',
    queued: 'I kö',
    failed: 'Fel',
    passed: 'Godkänd',
    completed: 'Klar',
    manual_review: 'Manuell kontroll',
    needs_review: 'Behöver kontroll'
  }
  return map[normalized] || status
}

function StatusBadge({ status }) {
  const normalized = String(status || '').toLowerCase()
  const translated = translateStatus(status)
  const badgeClass = statusClassMap[normalized] || 'status-pending'
  return <span className={`status-badge ${badgeClass}`}>{translated || 'Okänd'}</span>
}

function Banner({ banner, onDismiss }) {
  if (!banner) {
    return null
  }
  const iconMap = {
    info: <FiInfo className="text-xl" />,
    success: <FiCheckCircle className="text-xl" />,
    error: <FiAlertCircle className="text-xl" />
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
            <span>Status</span>
            <select
              value={draft.status}
              onChange={(event) => update('status', event.target.value)}
              className="dm-input"
              disabled={disabled}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
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


function usePreviewImage({ previewUrl, receiptId }) {
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
  }, [previewUrl, receiptId]);

  return state;
}

function ReceiptPreview({ receipt, onPreview, onCache }) {
  // Only use original image, no preview_url
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

function ExportModal({ open, filters, onClose }) {
  const [fromDate, setFromDate] = React.useState(filters.from || '')
  const [toDate, setToDate] = React.useState(filters.to || '')
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState('')

  React.useEffect(() => {
    if (open) {
      setFromDate(filters.from || '')
      setToDate(filters.to || '')
      setError('')
    }
  }, [filters, open])

  if (!open) {
    return null
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    const params = new URLSearchParams()
    if (fromDate) params.set('from', fromDate)
    if (toDate) params.set('to', toDate)
    try {
      const res = await api.fetch(`/ai/api/export/sie?${params.toString()}`)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const filename = `mind_export_${fromDate || 'start'}_${toDate || 'slut'}.sie`
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = filename
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-label="Exportera SIE">
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Exportera SIE</h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng">
            <FiX />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="modal-body space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="filter-field">
              <span>Från datum</span>
              <input
                type="date"
                className="dm-input"
                value={fromDate}
                onChange={(event) => setFromDate(event.target.value)}
                disabled={loading}
              />
            </label>
            <label className="filter-field">
              <span>Till datum</span>
              <input
                type="date"
                className="dm-input"
                value={toDate}
                onChange={(event) => setToDate(event.target.value)}
                disabled={loading}
              />
            </label>
          </div>
          {error && <div className="alert alert-error">{error}</div>}
          <div className="modal-footer">
            <button type="button" className="btn btn-text" onClick={onClose}>
              Avbryt
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Genererar...
                </>
              ) : (
                <>
                  <FiDownload className="mr-2" />
                  Generera SIE-fil
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
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

  // Google Maps URL for embedding
  const mapUrl = hasCoordinates
    ? `https://www.google.com/maps/embed/v1/place?key=YOUR_API_KEY&q=${lat},${lon}&zoom=15`
    : null;

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
              {/* OpenStreetMap iframe */}
              <iframe
                width="100%"
                height="100%"
                style={{ border: 0, borderRadius: '8px' }}
                src={`https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.01},${lat-0.01},${lon+0.01},${lat+0.01}&layer=mapnik&marker=${lat},${lon}`}
                title={`Karta för kvitto ${receipt.id}`}
              />
              {/* Coordinate overlay */}
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
              {/* External link button */}
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


function PreviewModal({ previewState, onClose, onDownload }) {
  const [ocrBoxes, setOcrBoxes] = React.useState([]);
  const [imageLoaded, setImageLoaded] = React.useState(false);

  // Reset image loaded state when receipt changes
  React.useEffect(() => {
    setImageLoaded(false);
  }, [previewState.receipt?.id]);

  // Fetch OCR box data when modal opens and image is ready
  React.useEffect(() => {
    if (!previewState.receipt || !previewState.imageUrl) {
      setOcrBoxes([]);
      return;
    }

    let cancelled = false;

    const fetchOcrBoxes = async () => {
      try {
        const res = await api.fetch(`/ai/api/receipts/${previewState.receipt.id}/ocr/boxes`);
        if (!res.ok) {
          console.warn(`Could not fetch OCR boxes: HTTP ${res.status}`);
          return;
        }
        const data = await res.json();
        if (!cancelled) {
          if (Array.isArray(data)) {
            setOcrBoxes(data);
          } else {
            console.warn('OCR boxes response is not an array:', data);
            setOcrBoxes([]);
          }
        }
      } catch (error) {
        console.error('Failed to fetch OCR boxes:', error);
        setOcrBoxes([]);
      }
    };

    fetchOcrBoxes();

    return () => {
      cancelled = true;
    };
  }, [previewState.receipt?.id, previewState.imageUrl]);

  if (!previewState.receipt) {
    return null;
  }

  const handleBackdrop = () => {
    if (!previewState.loading) {
      onClose();
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-label={`Förhandsgranska kvitto ${previewState.receipt.id}`} onClick={handleBackdrop}>
      <div className="modal modal-lg" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Förhandsgranskning</h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng förhandsgranskning">
            <FiX />
          </button>
        </div>
        <div className="modal-body preview-body">
          {previewState.loading ? (
            <div className="loading-inline">
              <div className="loading-spinner" />
              <span>Laddar bild...</span>
            </div>
          ) : previewState.imageUrl ? (
            <div className="preview-image-wrapper">
                <div
                  className="preview-image-container"
                  style={{
                    width: '100%',
                    height: '100%',
                    backgroundImage: `url(${previewState.imageUrl})`,
                    backgroundSize: 'contain',
                    backgroundRepeat: 'no-repeat',
                    backgroundPosition: 'center'
                  }}
                  onLoad={() => {
                    setImageLoaded(true);
                  }}
                >
                  <img
                    src={previewState.imageUrl}
                    alt={'Förhandsgranskning av kvitto ' + previewState.receipt.id}
                    style={{ display: 'none' }}
                    onLoad={() => {
                      setImageLoaded(true);
                    }}
                  />
                </div>
                <div
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    pointerEvents: 'none'
                  }}
                >
                  {imageLoaded && ocrBoxes && ocrBoxes.length > 0 && (
                    <>
                      {ocrBoxes.map((box, index) => {
                        if (!box || typeof box.x !== 'number' || typeof box.y !== 'number' ||
                            typeof box.w !== 'number' || typeof box.h !== 'number') {
                          console.warn('Invalid OCR box data at index', index, ':', box);
                          return null;
                        }
                        return (
                          <div
                            key={index}
                            style={{
                              position: 'absolute',
                              left: (box.x * 100) + '%',
                              top: (box.y * 100) + '%',
                              width: (box.w * 100) + '%',
                              height: (box.h * 100) + '%',
                              backgroundColor: 'rgba(0, 123, 255, 0.2)',
                              border: '2px solid rgba(0, 123, 255, 0.8)',
                              borderRadius: '2px',
                              boxShadow: '0 0 4px rgba(0, 123, 255, 0.5)',
                              zIndex: 10
                            }}
                            title={box.field || ''}
                          />
                        );
                      })}
                    </>
                  )}
                </div>
            </div>
          ) : (
            <div className="preview-missing">{previewState.error || 'Ingen bild tillgänglig'}</div>
          )}
        </div>
        <div className="modal-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onDownload(previewState.receipt)}
            disabled={previewState.loading}
          >
            <FiDownload className="mr-2" />
            Ladda ned original
          </button>
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

export default function Receipts() {
  const [items, setItems] = React.useState([])
  const [meta, setMeta] = React.useState({ page: 1, page_size: 25, total: 0 })
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(25)
  const [loading, setLoading] = React.useState(false)
  const [ftpLoading, setFtpLoading] = React.useState(false)
  const [banner, setBanner] = React.useState(null)
  const [searchTerm, setSearchTerm] = React.useState('')
  const [filters, setFilters] = React.useState(initialFilters)
  const [isFilterOpen, setFilterOpen] = React.useState(false)
  const [isExportOpen, setExportOpen] = React.useState(false)
  const [isMapOpen, setMapOpen] = React.useState(false)
  const [selectedReceiptForMap, setSelectedReceiptForMap] = React.useState(null)
  const [previewState, setPreviewState] = React.useState(initialPreviewState)
  const previewCache = React.useRef(new Map())

  const loadReceipts = React.useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    if (searchTerm) {
      params.set('merchant', searchTerm)
    }
    if (filters.status) params.set('status', filters.status)
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

  const totals = React.useMemo(() => {
    const gross = displayedItems.reduce((sum, receipt) => sum + (receipt.gross_amount || 0), 0)
    const completed = displayedItems.filter((receipt) => ['passed', 'completed'].includes(String(receipt.status).toLowerCase())).length
    return {
      totalGross: gross,
      completed
    }
  }, [displayedItems])

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

  const handleFetchFtp = React.useCallback(async () => {
    setFtpLoading(true)
    setBanner({ type: 'info', message: 'Hämtar filer från FTP...' })
    try {
      const res = await api.fetch('/ai/api/ingest/fetch-ftp', { method: 'POST' })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      let message = 'FTP-hämtning klar'
      try {
        const payload = await res.json()
        if (payload?.message) {
          message = payload.message
        } else if (typeof payload?.downloaded === 'number') {
          message = `FTP-hämtning klar – ${payload.downloaded} filer hämtade`
        }
      } catch (jsonError) {
        // Ignore JSON parse errors and use default message
      }
      setBanner({ type: 'success', message })
      await loadReceipts()
    } catch (error) {
      console.error('FTP fetch failed', error)
      setBanner({
        type: 'error',
        message: `FTP-fel: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setFtpLoading(false)
    }
  }, [loadReceipts])

  const handlePreview = (receipt, previewData = null) => {
    if (!receipt) {
      return;
    }
    const cachedSrc = previewData?.src || previewCache.current.get(receipt.id) || null;
    const hadError = Boolean(previewData?.error);
    setPreviewState((prev) => {
      if (prev.imageUrl && prev.revokeOnClose) {
        URL.revokeObjectURL(prev.imageUrl);
      }
      return {
        receipt,
        imageUrl: null, // Start with null to ensure loading effect triggers
        loading: !cachedSrc, // Only load if we don't have a cached image
        error: hadError ? 'Kunde inte ladda förhandsgranskning' : null,
        revokeOnClose: false,
        cachedImageUrl: cachedSrc // Store cached image separately
      };
    });
  };

  const handleDownload = async (receipt) => {
    if (!receipt) {
      return;
    }
    try {
      const res = await api.fetch('/ai/api/receipts/' + receipt.id + '/image');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const filename = receipt.original_filename || `${receipt.id}.jpg`;
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);
      setBanner({ type: 'success', message: `Kvitto ${filename} nedladdat` });
    } catch (error) {
      setBanner({
        type: 'error',
        message: `Kunde inte ladda ned kvitto: ${error instanceof Error ? error.message : error}`
      });
    }
  };

  const closePreview = () => {
    setPreviewState((prev) => {
      if (prev.imageUrl && prev.revokeOnClose) {
        URL.revokeObjectURL(prev.imageUrl);
      }
      return {
        receipt: null,
        imageUrl: null,
        loading: false,
        error: null,
        revokeOnClose: false,
        cachedImageUrl: null
      };
    });
  };

  const handleShowMap = (receipt) => {
    setSelectedReceiptForMap(receipt);
    setMapOpen(true);
  };

  const closeMap = () => {
    setMapOpen(false);
    setSelectedReceiptForMap(null);
  };

  React.useEffect(() => {
    if (!previewState.receipt) {
      return;
    }

    if (previewState.cachedImageUrl) {
      setPreviewState((prev) => ({
        ...prev,
        imageUrl: prev.cachedImageUrl,
        loading: false,
        error: null,
        revokeOnClose: false
      }));
      return;
    }

    if (!previewState.loading) {
      return;
    }

    let cancelled = false;
    let objectUrl = null;
    const { receipt } = previewState;
    const cacheBuster = Date.now();
    const base = '/ai/api/receipts/' + receipt.id + '/image';
    const endpoints = [
      base + '?cb=' + cacheBuster,
      base + '?size=raw&cb=' + cacheBuster
    ];

    const loadImage = async () => {
      for (const endpoint of endpoints) {
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
          setPreviewState((prev) => ({
            ...prev,
            imageUrl: objectUrl,
            loading: false,
            error: null,
            revokeOnClose: true
          }));
          return;
        } catch (error) {
          if (cancelled) {
            return;
          }
        }
      }
      if (!cancelled) {
        setPreviewState((prev) => ({
          ...prev,
          loading: false,
          error: 'Kunde inte ladda bild',
          revokeOnClose: false
        }));
      }
    };

    loadImage();

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [previewState.receipt, previewState.loading, previewState.cachedImageUrl]);

  const dismissBanner = () => setBanner(null)

  return (
    <div className="space-y-6">
      <div className="card hero-card">
        <div className="flex items-center justify-between flex-col lg:flex-row gap-4">
          <div>
            <h1 className="text-2xl font-bold mb-2">Kvitton</h1>
            <p className="text-sm text-gray-300">Hantera, filtrera och exportera kvitton från kvittolistan</p>
          </div>
          <div className="flex gap-2">
            <button
              className={`btn btn-primary ${ftpLoading ? 'opacity-70' : ''}`}
              onClick={handleFetchFtp}
              disabled={ftpLoading}
            >
              <FiRefreshCw className={ftpLoading ? 'animate-spin' : ''} />
              {ftpLoading ? 'Hämtar…' : 'Hämta från FTP'}
            </button>
            <button className="btn btn-secondary" onClick={() => setExportOpen(true)}>
              <FiDownload />
              Exportera
            </button>
            <button className="btn btn-secondary" onClick={() => setFilterOpen((prev) => !prev)}>
              <FiFilter />
              Filter
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
                <th>Förhandsgranskning</th>
                <th>Datum</th>
                <th>Företag</th>
                <th className="text-right">Exkl. moms</th>
                <th className="text-right">Inkl. moms</th>
                <th className="text-center">Status</th>
                <th>Filnamn</th>
                <th className="text-center">Åtgärder</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="table-loading">
                    <div className="loading-inline">
                      <div className="loading-spinner" />
                      <span>Laddar kvitton...</span>
                    </div>
                  </td>
                </tr>
              ) : displayedItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="table-empty">
                    <div className="space-y-2">
                      <div>Inga kvitton hittades</div>
                      <div className="text-sm text-gray-400">Justera filter eller hämta nya filer från FTP</div>
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
                      <div className="font-medium">{formatDate(receipt.file_creation_timestamp)}</div>
                      {receipt.file_creation_timestamp && (
                        <div className="text-xs text-gray-400">{receipt.file_creation_timestamp}</div>
                      )}
                    </td>
                    <td>
                      <div className="font-medium">{receipt.merchant || 'Okänt bolag'}</div>
                      {receipt.line_item_count ? (
                        <div className="text-xs text-gray-400">{receipt.line_item_count} artiklar</div>
                      ) : null}
                    </td>
                    <td className="text-right">{formatCurrency(receipt.net_amount)}</td>
                    <td className="text-right text-lg font-semibold">{formatCurrency(receipt.gross_amount)}</td>
                    <td className="text-center">
                      <StatusBadge status={receipt.status || receipt.ai_status} />
                    </td>
                    <td>
                      <div className="font-mono text-sm truncate" title={receipt.original_filename || ''}>
                        {receipt.original_filename || '-'}
                      </div>
                      {receipt.tags?.length ? (
                        <div className="text-xs text-gray-400 truncate">Taggar: {receipt.tags.join(', ')}</div>
                      ) : null}
                    </td>
                    <td className="text-center">
                      <div className="flex gap-2 justify-center">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleShowMap(receipt)}>
                          <FiMapPin />
                          Plats
                        </button>
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleDownload(receipt)}>
                          <FiDownload />
                          Ladda ned
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

      {displayedItems.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="stat-card red">
            <div className="flex items-center justify-between">
              <div>
                <div className="stat-number">{meta.total}</div>
                <div className="stat-label">Totalt antal kvitton</div>
              </div>
              <FiFileText className="text-2xl opacity-80" />
            </div>
          </div>
          <div className="stat-card green">
            <div className="flex items-center justify-between">
              <div>
                <div className="stat-number">{totals.completed}</div>
                <div className="stat-label">Godkända kvitton</div>
              </div>
              <FiCheckCircle className="text-2xl opacity-80" />
            </div>
          </div>
          <div className="stat-card blue">
            <div className="flex items-center justify-between">
              <div>
                <div className="stat-number">{formatCurrency(totals.totalGross)}</div>
                <div className="stat-label">Total summa</div>
              </div>
              <FiDollarSign className="text-2xl opacity-80" />
            </div>
          </div>
        </div>
      )}

      <ExportModal open={isExportOpen} filters={filters} onClose={() => setExportOpen(false)} />
      <MapModal open={isMapOpen} receipt={selectedReceiptForMap} onClose={closeMap} />
      <PreviewModal previewState={previewState} onClose={closePreview} onDownload={handleDownload} />
    </div>
  )
}
