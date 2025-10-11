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
  FiMapPin,
  FiUpload,
  FiClock,
  FiFile,
  FiCpu,
  FiTrash2
} from 'react-icons/fi'
import { api } from '../api'
import ReceiptPreviewModal from '../components/ReceiptPreviewModal'

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
  tag: '',
  fileType: 'receipt'
}

const statusClassMap = {
  // Legacy statuses
  processing: 'status-processing',
  queued: 'status-queued',
  failed: 'status-failed',
  passed: 'status-passed',
  completed: 'status-passed',
  manual_review: 'status-manual_review',
  needs_review: 'status-manual_review',

  // AI Pipeline stages - progressive colors (blue -> green)
  ftp_fetched: 'status-processing',
  ocr_done: 'status-processing',
  ai1_completed: 'status-processing',
  ai2_completed: 'status-processing',
  ai3_completed: 'status-processing',
  ai4_completed: 'status-queued',
  proc_completed: 'status-passed'
}

const initialPreviewState = {
  receipt: null,
  previewImage: null
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
    // Legacy statuses
    processing: 'Bearbetas',
    queued: 'I kö',
    failed: 'Fel',
    passed: 'Godkänd',
    completed: 'Klar',
    manual_review: 'Manuell kontroll',
    needs_review: 'Behöver kontroll',

    // AI Pipeline stages
    ftp_fetched: 'FTP - Fil hämtad',
    ocr_done: 'OCR - Text extraherad',
    ai1_completed: 'AI1 - Dokumentklassificering klar',
    ai2_completed: 'AI2 - Utgiftsklassificering klar',
    ai3_completed: 'AI3 - Dataextraktion klar',
    ai4_completed: 'AI4 - Bokföringsförslag klart',
    proc_completed: 'Bearbetning klar'
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
          <label className="filter-field">
            <span>Filtyp</span>
            <select
              value={draft.fileType}
              onChange={(event) => update('fileType', event.target.value)}
              className="dm-input"
              disabled={disabled}
            >
              <option value="">Alla</option>
              <option value="receipt">Kvitton</option>
              <option value="invoice">Fakturor</option>
              <option value="other">Övriga</option>
            </select>
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


function usePreviewImage({ previewUrl, receiptId, cachedSrc }) {
  const [state, setState] = React.useState({ src: cachedSrc || null, loading: false, error: null });
  const hasLoaded = React.useRef(!!cachedSrc);

  React.useEffect(() => {
    // Om vi redan har en cachad bild, använd den och ladda inte om
    if (cachedSrc && hasLoaded.current) {
      setState({ src: cachedSrc, loading: false, error: null });
      return () => {};
    }

    // Om vi redan har laddat denna bild tidigare, skippa
    if (hasLoaded.current && state.src) {
      return () => {};
    }

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

    setState((prev) => ({ ...prev, loading: true }));

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
          hasLoaded.current = true;
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
      if (objectUrl && !hasLoaded.current) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [receiptId, cachedSrc]);

  return state;
}

function ReceiptPreview({ receipt, onPreview, onCache, cachedImageMap }) {
  // Hämta cachad bild om den finns
  const cachedSrc = cachedImageMap ? cachedImageMap.get(receipt.id) : null;

  // Only use original image, no preview_url
  const { src, loading, error } = usePreviewImage({
    receiptId: receipt.id,
    cachedSrc: cachedSrc
  });

  React.useEffect(() => {
    if (typeof onCache === 'function' && src && src !== cachedSrc) {
      onCache(receipt.id, src);
    }
    return () => {};
  }, [receipt.id, src, onCache, cachedSrc]);

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

function UploadModal({ open, onClose, onUploadComplete }) {
  const [uploading, setUploading] = React.useState(false)
  const [selectedFiles, setSelectedFiles] = React.useState([])
  const [error, setError] = React.useState(null)
  const [success, setSuccess] = React.useState(null)
  const fileInputRef = React.useRef(null)

  React.useEffect(() => {
    if (open) {
      setSelectedFiles([])
      setError(null)
      setSuccess(null)
    }
  }, [open])

  if (!open) {
    return null
  }

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files || [])
    setSelectedFiles(files)
    setError(null)
    setSuccess(null)
  }

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Välj minst en fil att ladda upp')
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(null)

    const formData = new FormData()
    selectedFiles.forEach((file) => {
      formData.append('files', file)
    })

    try {
      const res = await api.fetch('/ai/api/ingest/upload', {
        method: 'POST',
        body: formData
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.error || `HTTP ${res.status}`)
      }

      const result = await res.json()
      if (result.errors && result.errors.length > 0) {
        throw new Error(result.errors.join(', '));
      }

      setSuccess(`${result.uploaded || selectedFiles.length} fil(er) uppladdade`)
      setSelectedFiles([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      if (typeof onUploadComplete === 'function') {
        setTimeout(() => {
          onUploadComplete()
        }, 1500)
      }
    } catch (err) {
      setError(err.message || 'Uppladdning misslyckades')
    } finally {
      setUploading(false)
    }
  }

  const handleBackdrop = (event) => {
    if (event.target === event.currentTarget && !uploading) {
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-label="Ladda upp filer" onClick={handleBackdrop}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Ladda upp kvitton</h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng" disabled={uploading}>
            <FiX />
          </button>
        </div>
        <div className="modal-body space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Välj filer att ladda upp</label>
            <div className="flex gap-2">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf"
                onChange={handleFileSelect}
                className="dm-input flex-1"
                disabled={uploading}
              />
            </div>
            {selectedFiles.length > 0 && (
              <div className="mt-2 text-sm text-gray-300">
                {selectedFiles.length} fil(er) valda
              </div>
            )}
          </div>
          {error && (
            <div className="alert alert-error">
              <FiAlertCircle />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="alert alert-success">
              <FiCheckCircle />
              <span>{success}</span>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-text" onClick={onClose} disabled={uploading}>
            Avbryt
          </button>
          <button type="button" className="btn btn-primary" onClick={handleUpload} disabled={uploading || selectedFiles.length === 0}>
            {uploading ? (
              <>
                <div className="loading-spinner mr-2" />
                Laddar upp...
              </>
            ) : (
              <>
                <FiUpload className="mr-2" />
                Ladda upp
              </>
            )}
          </button>
        </div>
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


function AIStageModal({ open, stageData, onClose }) {
  if (!open || !stageData) {
    return null;
  }

  const handleBackdrop = (event) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  const getStatusBadgeClass = (status) => {
    const normalized = String(status || '').toLowerCase();
    if (normalized === 'success' || normalized === 'completed') return 'status-passed';
    if (normalized === 'error' || normalized === 'failed') return 'status-failed';
    if (normalized === 'pending') return 'status-queued';
    return 'status-processing';
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-label="AI Stage Details" onClick={handleBackdrop}>
      <div className="modal modal-lg" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>{stageData.title || 'AI Processing Details'}</h3>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Stäng">
            <FiX />
          </button>
        </div>
        <div className="modal-body space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="filter-field">
              <span className="text-sm font-medium text-gray-300">Status</span>
              <div>
                <span className={`status-badge ${getStatusBadgeClass(stageData.status)}`}>
                  {stageData.status || 'N/A'}
                </span>
              </div>
            </div>
            {stageData.ai_stage_name && (
              <div className="filter-field">
                <span className="text-sm font-medium text-gray-300">Stage Name</span>
                <div className="text-gray-200">{stageData.ai_stage_name}</div>
              </div>
            )}
            {stageData.created_at && (
              <div className="filter-field">
                <span className="text-sm font-medium text-gray-300">Created At</span>
                <div className="text-gray-200">{stageData.created_at}</div>
              </div>
            )}
            {stageData.processing_time_ms !== null && stageData.processing_time_ms !== undefined && (
              <div className="filter-field">
                <span className="text-sm font-medium text-gray-300">Processing Time</span>
                <div className="text-gray-200">{stageData.processing_time_ms} ms</div>
              </div>
            )}
            {stageData.confidence !== null && stageData.confidence !== undefined && (
              <div className="filter-field">
                <span className="text-sm font-medium text-gray-300">Confidence</span>
                <div className="text-gray-200">{(stageData.confidence * 100).toFixed(1)}%</div>
              </div>
            )}
            {stageData.provider && (
              <div className="filter-field">
                <span className="text-sm font-medium text-gray-300">Provider</span>
                <div className="text-gray-200">{stageData.provider}</div>
              </div>
            )}
            {stageData.model && (
              <div className="filter-field">
                <span className="text-sm font-medium text-gray-300">Model</span>
                <div className="text-gray-200">{stageData.model}</div>
              </div>
            )}
          </div>

          {stageData.log_text && (
            <div className="filter-field">
              <span className="text-sm font-medium text-gray-300">Log Text</span>
              <div className="bg-gray-800 p-4 rounded-lg mt-2" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                <pre className="text-sm text-gray-200 whitespace-pre-wrap font-mono">{stageData.log_text}</pre>
              </div>
            </div>
          )}

          {stageData.ocr_raw && (
            <div className="filter-field">
              <span className="text-sm font-medium text-gray-300">OCR Raw Text</span>
              <div className="bg-gray-800 p-4 rounded-lg mt-2" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                <pre className="text-sm text-gray-200 whitespace-pre-wrap font-mono">{stageData.ocr_raw}</pre>
              </div>
            </div>
          )}

          {stageData.error_message && (
            <div className="alert alert-error">
              <FiAlertCircle className="text-xl" />
              <div>
                <div className="font-medium">Error Message</div>
                <div className="text-sm">{stageData.error_message}</div>
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


function WorkflowBadges({ receipt, onStageClick }) {
  const [workflow, setWorkflow] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;

    const fetchWorkflow = async () => {
      try {
        setLoading(true);
        const res = await api.fetch(`/ai/api/receipts/${receipt.id}/workflow-status`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          setWorkflow(data);
        }
      } catch (error) {
        console.error('Failed to fetch workflow status:', error);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchWorkflow();

    return () => {
      cancelled = true;
    };
  }, [receipt.id]);

  const getBadgeClass = (status) => {
    if (typeof status === 'object' && status !== null) {
      status = status.status;
    }
    const normalized = String(status || '').toLowerCase();
    if (normalized === 'success' || normalized === 'completed') return 'bg-green-600 text-white';
    if (normalized === 'error' || normalized === 'failed') return 'bg-red-600 text-white';
    if (normalized === 'pending') return 'bg-gray-500 text-white';
    if (normalized === 'n/a') return 'bg-gray-400 text-white';
    return 'bg-blue-500 text-white';
  };

  const renderBadge = (label, value, onClick = null) => {
    const displayValue = typeof value === 'object' && value !== null ? value.status || 'N/A' : value || 'N/A';
    const isClickable = onClick !== null;

    return (
      <div
        className={`flex flex-col items-center ${isClickable ? 'cursor-pointer hover:opacity-80 transition-opacity' : ''}`}
        onClick={isClickable ? onClick : undefined}
        role={isClickable ? 'button' : undefined}
        tabIndex={isClickable ? 0 : undefined}
      >
        <div className="text-xs text-gray-400 mb-1">{label}</div>
        <span className={`status-badge ${getBadgeClass(value)} text-xs px-2 py-1`}>
          {displayValue}
        </span>
      </div>
    );
  };

  if (loading || !workflow) {
    return (
      <div className="flex items-center gap-2 text-gray-400 text-sm">
        <div className="loading-spinner" style={{ width: '16px', height: '16px' }} />
        <span>Loading...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-3 items-start" style={{ minWidth: '800px' }}>
      {renderBadge('Title', workflow.title || `ID: ${workflow.file_id}`)}
      {renderBadge('Datum', workflow.datetime || '-')}
      {renderBadge('Upload', workflow.upload)}
      {renderBadge('FileName', workflow.filename || '-')}
      {renderBadge('PDFConvert', workflow.pdf_convert)}
      {renderBadge('OCR', workflow.ocr, workflow.ocr && workflow.ocr.status !== 'pending' ? () => onStageClick({ ...workflow.ocr, title: 'OCR Processing', ocr_raw: workflow.ocr_raw }) : null)}
      {renderBadge('AI1', workflow.ai1, workflow.ai1 && workflow.ai1.status !== 'pending' ? () => onStageClick({ ...workflow.ai1, title: 'AI1 - Document Classification' }) : null)}
      {renderBadge('AI2', workflow.ai2, workflow.ai2 && workflow.ai2.status !== 'pending' ? () => onStageClick({ ...workflow.ai2, title: 'AI2 - Expense Classification' }) : null)}
      {renderBadge('AI3', workflow.ai3, workflow.ai3 && workflow.ai3.status !== 'pending' ? () => onStageClick({ ...workflow.ai3, title: 'AI3 - Data Extraction' }) : null)}
      {renderBadge('AI4', workflow.ai4, workflow.ai4 && workflow.ai4.status !== 'pending' ? () => onStageClick({ ...workflow.ai4, title: 'AI4 - Accounting Proposal' }) : null)}
      {renderBadge('Match', workflow.match, workflow.match && workflow.match.status !== 'pending' ? () => onStageClick({ ...workflow.match, title: 'Match Status' }) : null)}
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
  const [isUploadOpen, setUploadOpen] = React.useState(false)
  const [isMapOpen, setMapOpen] = React.useState(false)
  const [selectedReceiptForMap, setSelectedReceiptForMap] = React.useState(null)
  const [isAIStageOpen, setAIStageOpen] = React.useState(false)
  const [selectedAIStage, setSelectedAIStage] = React.useState(null)
  const [previewState, setPreviewState] = React.useState(initialPreviewState)
  const previewCache = React.useRef(new Map())

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
    if (filters.status) params.set('status', filters.status)
    if (filters.orgnr) params.set('orgnr', filters.orgnr)
    if (filters.from) params.set('from', filters.from)
    if (filters.to) params.set('to', filters.to)
    if (filters.tag) params.set('tags', filters.tag)
    if (filters.fileType) params.set('file_type', filters.fileType)

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
      if (!silent) {
        setBanner({
          type: 'info',
          message: `Visar ${list.length} av ${fetchedMeta.total ?? list.length} kvitton`
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
  }, [page, pageSize, searchTerm, filters])

  React.useEffect(() => {
    loadReceipts()
  }, [loadReceipts])

  // Polling för automatisk uppdatering av status (var 5:e sekund)
  React.useEffect(() => {
    const intervalId = setInterval(() => {
      // Ladda om data tyst utan att visa loading-spinner eller uppdatera banner
      loadReceipts(true)
    }, 5000) // 5 sekunder

    return () => clearInterval(intervalId)
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
    setPreviewState({
      receipt,
      previewImage: cachedSrc
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
    setPreviewState({
      receipt: null,
      previewImage: null
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

  const handleShowAIStage = (stageData) => {
    setSelectedAIStage(stageData);
    setAIStageOpen(true);
  };

  const closeAIStage = () => {
    setAIStageOpen(false);
    setSelectedAIStage(null);
  };

  const handleResume = async (fileId) => {
    try {
      const res = await api.fetch(`/ai/api/ingest/process/${fileId}/resume`, {
        method: 'POST',
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();

      if (data.queued) {
        setBanner({
          type: 'success',
          message: `Bearbetning återupptagen: ${data.action || 'processing resumed'}`,
        });
        // Reload receipts after a short delay to show updated status
        setTimeout(() => {
          loadReceipts(true);
        }, 2000);
      } else {
        setBanner({
          type: 'error',
          message: data.error || 'Kunde inte återuppta bearbetning',
        });
      }
    } catch (error) {
      console.error('Error resuming processing:', error);
      setBanner({
        type: 'error',
        message: 'Fel vid återupptagning av bearbetning',
      });
    }
  };

  const handleResumeAll = async () => {
    if (displayedItems.length === 0) {
      setBanner({
        type: 'error',
        message: 'Inga kvitton att återuppta',
      });
      return;
    }

    setBanner({
      type: 'info',
      message: `Återupptar ${displayedItems.length} kvitton...`,
    });

    let successCount = 0;
    let errorCount = 0;

    for (const receipt of displayedItems) {
      try {
        const res = await api.fetch(`/ai/api/ingest/process/${receipt.id}/resume`, {
          method: 'POST',
        });

        if (res.ok) {
          successCount++;
        } else {
          errorCount++;
        }
      } catch (error) {
        console.error(`Error resuming ${receipt.id}:`, error);
        errorCount++;
      }
    }

    setBanner({
      type: successCount > 0 ? 'success' : 'error',
      message: `Återupptagning klar: ${successCount} lyckades, ${errorCount} misslyckades`,
    });

    setTimeout(() => {
      loadReceipts(true);
    }, 2000);
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

  return (
    <div className="space-y-6">
      <div className="card hero-card">
        <div className="flex items-center justify-between flex-col lg:flex-row gap-4">
          <div>
            <h1 className="text-2xl font-bold mb-2">Process</h1>
            <p className="text-sm text-gray-300">Hantera, filtrera och exportera filer från systemet</p>
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
            <button className="btn btn-primary" onClick={() => setUploadOpen(true)}>
              <FiUpload />
              Ladda upp
            </button>
            <button className="btn btn-secondary" onClick={() => setExportOpen(true)}>
              <FiDownload />
              Exportera
            </button>
            <button className="btn btn-secondary" onClick={() => setFilterOpen((prev) => !prev)}>
              <FiFilter />
              Filter
            </button>
            <button className="btn btn-primary" onClick={handleResumeAll} disabled={loading}>
              <FiRefreshCw />
              Återuppta alla
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

        <div className="table-wrapper" style={{ overflowX: 'auto' }}>
          <table className="table-dark">
            <thead>
              <tr>
                <th>Förhandsgranskning</th>
                <th>Process</th>
                <th>Datum</th>
                <th>Företag</th>
                <th className="text-right">Exkl. moms</th>
                <th className="text-right">Inkl. moms</th>
                <th className="text-center">Status</th>
                <th>Filtyp</th>
                <th className="text-center">Åtgärder</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="table-loading">
                    <div className="loading-inline">
                      <div className="loading-spinner" />
                      <span>Laddar kvitton...</span>
                    </div>
                  </td>
                </tr>
              ) : displayedItems.length === 0 ? (
                <tr>
                  <td colSpan={9} className="table-empty">
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
                        cachedImageMap={previewCache.current}
                      />
                    </td>
                    <td>
                      <WorkflowBadges receipt={receipt} onStageClick={handleShowAIStage} />
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
                      <div className="font-medium text-sm">
                        {receipt.file_type === 'receipt' ? 'Kvitto' :
                         receipt.file_type === 'invoice' ? 'Faktura' :
                         receipt.file_type || 'Okänd'}
                      </div>
                    </td>
                    <td className="text-center">
                      <div className="flex gap-2 justify-center flex-wrap">
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
                        <button
                          type="button"
                          className="btn btn-sm"
                          style={{
                            backgroundColor: '#dc2626',
                            color: 'white',
                            fontSize: '0.75rem',
                            padding: '0.375rem 0.625rem'
                          }}
                          onClick={() => handleResume(receipt.id)}
                          title="Återuppta bearbetning från där den stannade">
                          <FiRefreshCw style={{ fontSize: '0.875rem' }} />
                          Återuppta
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(receipt)}
                          title="Radera kvitto">
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

      <UploadModal
        open={isUploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploadComplete={() => {
          setUploadOpen(false)
          loadReceipts()
        }}
      />
      <ExportModal open={isExportOpen} filters={filters} onClose={() => setExportOpen(false)} />
      <MapModal open={isMapOpen} receipt={selectedReceiptForMap} onClose={closeMap} />
      <AIStageModal open={isAIStageOpen} stageData={selectedAIStage} onClose={closeAIStage} />
      <ReceiptPreviewModal
        open={Boolean(previewState.receipt)}
        receipt={previewState.receipt}
        previewImage={previewState.previewImage}
        onClose={closePreview}
        onReceiptUpdate={(updatedReceipt) => {
          loadReceipts(true);
          closePreview();
        }}
      />
    </div>
  )
}
