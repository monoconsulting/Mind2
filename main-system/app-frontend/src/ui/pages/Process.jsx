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
  FiCopy,
  FiFile,
  FiCpu,
  FiTrash2
} from 'react-icons/fi'
import { api } from '../api'
import ReceiptPreviewModal from '../components/ReceiptPreviewModal'
import statusDefinitions from '../../../../../shared/status_definitions.json'

const INITIAL_LOG_STATE = {
  open: false,
  loading: false,
  error: null,
  data: null,
  receiptId: null,
}


const statusClassMap = {
  // AI Status (source of truth: docs/source_of_truth/30_STATUS_MODEL.md)
  uploaded: 'status-queued',
  processing: 'status-processing',
  ocr_done: 'status-processing',
  ocr_failed: 'status-failed',
  manual_review: 'status-manual_review',
  completed: 'status-passed',
  failed: 'status-failed',

  // Legacy / pipeline aliases
  queued: 'status-queued',
  passed: 'status-passed',
  needs_review: 'status-manual_review',
  ftp_fetched: 'status-processing',
  ai1_completed: 'status-processing',
  ai2_completed: 'status-processing',
  ai3_completed: 'status-processing',
  ai4_completed: 'status-queued',
  proc_completed: 'status-passed',

  // Workflow stage status (queued/running/succeeded/failed/skipped)
  running: 'status-processing',
  succeeded: 'status-passed',
  skipped: 'status-queued',
  canceled: 'status-failed'
}

const CATEGORY_ORDER = ['upload', 'workflow', 'matching', 'resume', 'outcome']
const STAGE_DEFINITIONS = statusDefinitions?.stageKeys || {}
const CATEGORY_LABELS = statusDefinitions?.categories || {}
const LEGACY_STATUS_DEFINITIONS = statusDefinitions?.legacyStatuses || {}
const STATUS_LABEL_MAP = statusDefinitions?.statusLabels || {}

const stageOptions = (() => {
  const entries = Object.entries(STAGE_DEFINITIONS)
  const unusedKeys = new Set(entries.map(([key]) => key))
  /** @type {Array<{ value: string, label: string }>} */
  const ordered = []

  CATEGORY_ORDER.forEach((category) => {
    const categoryEntries = entries.filter(([, meta]) => (meta?.category || 'workflow') === category)
    if (!categoryEntries.length) {
      return
    }
    categoryEntries
      .sort((a, b) => (a[1]?.label || a[0]).localeCompare(b[1]?.label || b[0], 'sv'))
      .forEach(([key, meta]) => {
        unusedKeys.delete(key)
        ordered.push({
          value: `stage:${key}`,
          label: `${CATEGORY_LABELS?.[category]?.label || 'Workflow'} · ${meta?.label || key}`
        })
      })
  })

  if (unusedKeys.size > 0) {
    Array.from(unusedKeys)
      .sort((a, b) => a.localeCompare(b, 'sv'))
      .forEach((key) => {
        const meta = STAGE_DEFINITIONS[key]
        ordered.push({
          value: `stage:${key}`,
          label: `${CATEGORY_LABELS?.[meta?.category]?.label || 'Workflow'} · ${meta?.label || key}`
        })
      })
  }
  return ordered
})()

const legacyStatusOptions = Object.entries(LEGACY_STATUS_DEFINITIONS)
  .map(([key, meta]) => ({
    value: `legacy:${key}`,
    label: `Legacy · ${meta?.label || key}`
  }))
  .sort((a, b) => a.label.localeCompare(b.label, 'sv'))

// Build statusOptions dynamically from STAGE_DEFINITIONS and LEGACY_STATUS_DEFINITIONS
const statusOptions = [
  { value: '', label: 'Alla statusar' },
  // Meta filters (these are special filters, not status values)
  { value: 'status:completed', label: 'Slutförda (KLAR)' },
  { value: 'status:!completed', label: 'Ej slutförda' },
  { value: 'match_status:unmatched', label: 'Ej matchade' },
  { value: 'status:manual_review', label: 'Manuell hantering' },
  // Stage options generated from status_definitions.json
  ...stageOptions
]

const uploadStageOptions = [
  { value: '', label: 'Alla källor' },
  { value: 'src_portal', label: 'Manuellt' },
  { value: 'src_ftp', label: 'FTP' }
]

const initialPreviewState = {
  receipt: null,
  previewImage: null
}

const initialFilters = {
  status: '',
  orgnr: '',
  tag: '',
  from: '',
  to: '',
  fileType: '',
  uploadStage: '',
  expenseType: '',
  paymentType: '',
  uploadYear: '',
  uploadMonth: ''
}

function formatCurrency(value, currency = 'SEK') {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-'
  }
  const code = typeof currency === 'string' && currency.trim() ? currency.trim().toUpperCase() : 'SEK'
  try {
    const formatter = new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: code,
      minimumFractionDigits: 2
    })
    return formatter.format(value)
  } catch (error) {
    const formatter = new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: 'SEK',
      minimumFractionDigits: 2
    })
    return `${formatter.format(value)}${code && code !== 'SEK' ? ` ${code}` : ''}`
  }
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

function formatStageLabel(stageKey) {
  if (!stageKey) {
    return ''
  }
  return STAGE_DEFINITIONS?.[stageKey]?.label || stageKey
}

function formatStageStatusLabel(stageStatus) {
  if (!stageStatus) {
    return ''
  }
  const normalized = stageStatus.toLowerCase()
  return STATUS_LABEL_MAP?.[normalized] || stageStatus
}

function translateStatus(status, stageKey = null, stageStatus = null) {
  if (stageKey || stageStatus) {
    // Use STAGE_DEFINITIONS from status_definitions.json for stage labels
    const stageLabel = STAGE_DEFINITIONS?.[stageKey]?.label || stageKey || ''

    // Use STATUS_LABEL_MAP from status_definitions.json for status labels
    const statusLabelTranslated = stageStatus
      ? (STATUS_LABEL_MAP?.[stageStatus.toLowerCase()] || stageStatus)
      : ''

    if (stageLabel && statusLabelTranslated) {
      return `${stageLabel} - ${statusLabelTranslated}`
    }
    return stageLabel || statusLabelTranslated || ''
  }

  if (!status) {
    return ''
  }

  const statusStr = String(status)
  const parts = statusStr.split(' ')
  if (parts.length >= 2) {
    const keyCandidate = parts[0]
    const stageCandidate = parts[1]
    return translateStatus(null, keyCandidate, stageCandidate)
  }

  const normalized = statusStr.toLowerCase()

  // First check LEGACY_STATUS_DEFINITIONS from status_definitions.json
  const legacyLabel = LEGACY_STATUS_DEFINITIONS?.[normalized]?.label
  if (legacyLabel) {
    return legacyLabel
  }

  // Then check if it's a stage key in STAGE_DEFINITIONS
  const stageDefLabel = STAGE_DEFINITIONS?.[normalized]?.label
  if (stageDefLabel) {
    return stageDefLabel
  }

  // Fallback to original status string
  return status
}

function StatusBadge({ status, stageKey = null, stageStatus = null }) {
  const statusStr = typeof status === 'string' ? status : ''
  const translated = translateStatus(statusStr, stageKey, stageStatus)

  let badgeClass = 'status-pending'
  if (stageStatus) {
    const normalizedStageStatus = stageStatus.toLowerCase()
    if (normalizedStageStatus === 'succeeded') {
      badgeClass = 'status-passed'
    } else if (normalizedStageStatus === 'running') {
      badgeClass = 'status-processing'
    } else if (normalizedStageStatus === 'failed') {
      badgeClass = 'status-failed'
    } else if (normalizedStageStatus === 'queued') {
      badgeClass = 'status-queued'
    }
  } else if (statusStr.includes(' ')) {
    const [, stageState] = statusStr.split(' ')
    if (stageState) {
      return (
        <StatusBadge
          status={statusStr}
          stageKey={stageKey || statusStr.split(' ')[0]}
          stageStatus={stageState}
        />
      )
    }
  } else if (statusStr) {
    badgeClass = statusClassMap[statusStr.toLowerCase()] || 'status-pending'
  }

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
            {[10, 25, 50, 100, 250, 500, 1000].map((size) => (
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
          <label className="filter-field">
            <span>Upload</span>
            <select
              value={draft.uploadStage}
              onChange={(event) => update('uploadStage', event.target.value)}
              className="dm-input"
              disabled={disabled}
            >
              {uploadStageOptions.map((option) => (
                <option key={option.value || option.label} value={option.value}>
                  {option.label}
                </option>
              ))}
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
      return () => { };
    }

    // Om vi redan har laddat denna bild tidigare, skippa
    if (hasLoaded.current && state.src) {
      return () => { };
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
      return () => { };
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
    return () => { };
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
                src={`https://www.openstreetmap.org/export/embed.html?bbox=${lon - 0.01},${lat - 0.01},${lon + 0.01},${lat + 0.01}&layer=mapnik&marker=${lat},${lon}`}
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


function WorkflowBadges({ receipt, refreshTick, onStageClick }) {
  const [workflow, setWorkflow] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let cancelled = false;

    const fetchWorkflow = async () => {
      try {
        setLoading(true);
        const cacheBuster = typeof refreshTick === 'number' ? refreshTick : Date.now();
        const res = await api.fetch(`/ai/api/receipts/${receipt.id}/workflow-status?tick=${cacheBuster}`);
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
  }, [receipt.id, receipt.status, receipt.ai_status, refreshTick]);

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

  // Detect if this is a FirstCard invoice workflow based on file properties
  const isFirstCardFile = () => {
    const fileType = (receipt.file_type || '').toLowerCase();
    const submittedBy = (receipt.submitted_by || '').toLowerCase();

    // FirstCard files have file_type that starts with 'cc_' or legacy 'invoice'/'invoice_page'
    // AND they're uploaded via 'invoice_upload' (from Kortmatchning menu)
    return (
      (fileType.startsWith('cc_') || fileType === 'invoice' || fileType === 'invoice_page') &&
      submittedBy.includes('invoice')
    );
  };

  const showFirstCard = isFirstCardFile();

  return (
    <div className="flex flex-wrap gap-3 items-start" style={{ minWidth: '800px' }}>
      {renderBadge('Title', workflow.title || `ID: ${workflow.file_id}`)}
      {renderBadge('Datum', workflow.datetime || '-')}
      {renderBadge('Upload', workflow.upload)}
      {renderBadge('FileName', workflow.filename || '-')}
      {renderBadge('PDFConvert', workflow.pdf_convert)}
      {renderBadge('OCR', workflow.ocr, workflow.ocr && workflow.ocr.status !== 'pending' ? () => onStageClick({ ...workflow.ocr, title: 'OCR Processing', ocr_raw: workflow.ocr_raw }) : null)}

      {/* FirstCard-specific stages */}
      {showFirstCard && renderBadge('OCR-Merge', workflow.ocr_merge, workflow.ocr_merge && workflow.ocr_merge.status !== 'pending' ? () => onStageClick({ ...workflow.ocr_merge, title: 'OCR Merge' }) : null)}
      {showFirstCard && renderBadge('OCR_RAW', workflow.ocr_raw_updated, workflow.ocr_raw_updated && workflow.ocr_raw_updated.status !== 'pending' ? () => onStageClick({ ...workflow.ocr_raw_updated, title: 'OCR RAW Updated' }) : null)}
      {showFirstCard && renderBadge('AI6', workflow.ai6, workflow.ai6 && workflow.ai6.status !== 'pending' ? () => onStageClick({ ...workflow.ai6, title: 'AI6 - Credit Card Invoice Parsing' }) : null)}

      {/* Regular receipt stages (hide for FirstCard) */}
      {!showFirstCard && renderBadge('AI1', workflow.ai1, workflow.ai1 && workflow.ai1.status !== 'pending' ? () => onStageClick({ ...workflow.ai1, title: 'AI1 - Document Classification' }) : null)}
      {!showFirstCard && renderBadge('AI2', workflow.ai2, workflow.ai2 && workflow.ai2.status !== 'pending' ? () => onStageClick({ ...workflow.ai2, title: 'AI2 - Expense Classification' }) : null)}
      {!showFirstCard && renderBadge('AI3', workflow.ai3, workflow.ai3 && workflow.ai3.status !== 'pending' ? () => onStageClick({ ...workflow.ai3, title: 'AI3 - Data Extraction' }) : null)}
      {!showFirstCard && renderBadge('AI4', workflow.ai4, workflow.ai4 && workflow.ai4.status !== 'pending' ? () => onStageClick({ ...workflow.ai4, title: 'AI4 - Accounting Proposal' }) : null)}

      {/* AI5 and Match shown for both workflows */}
      {renderBadge('AI5', workflow.ai5, workflow.ai5 && workflow.ai5.status !== 'pending' ? () => onStageClick({ ...workflow.ai5, title: 'AI5 - Credit Card Matching' }) : null)}
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
  const [refreshTick, setRefreshTick] = React.useState(0)
  const resumePending = React.useRef(new Set())
  const [sortColumn, setSortColumn] = React.useState('created_at')
  const [sortDirection, setSortDirection] = React.useState('desc')
  const [logState, setLogState] = React.useState(INITIAL_LOG_STATE)
  const [showPrompts, setShowPrompts] = React.useState(false)
  const [logActionState, setLogActionState] = React.useState({ clearing: false, error: '', success: '' })

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
      const res = await api.fetch(`/ai/api/receipts/${receiptId}/log?latest=1`)
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
    setLogActionState({ clearing: false, error: '', success: '' })
    setShowPrompts(false)
  }, [])

  const handleClearReceiptLog = React.useCallback(async (receiptId) => {
    if (!receiptId || logActionState.clearing) {
      return
    }
    if (!window.confirm('Vill du rensa alla loggar för detta kvitto? Detta går inte att ångra.')) {
      return
    }
    setLogActionState({ clearing: true, error: '', success: '' })
    try {
      const res = await api.fetch(`/ai/api/receipts/${receiptId}/log`, { method: 'DELETE' })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      await res.json().catch(() => ({}))
      setLogActionState({ clearing: false, error: '', success: 'Loggen rensades.' })
      await fetchReceiptLog(receiptId)
    } catch (error) {
      setLogActionState({
        clearing: false,
        error: error instanceof Error ? error.message : String(error),
        success: ''
      })
    }
  }, [fetchReceiptLog, logActionState.clearing])

  const handleCopyAll = React.useCallback(() => {
    const logData = logState.data ?? {}
    const historyEntries = Array.isArray(logData.ai_history) ? logData.ai_history : []
    const run = Array.isArray(logData.workflow_runs) ? logData.workflow_runs[0] : null
    const sections = []
    sections.push(`Kvitto: ${logData.receipt_id || logState.receiptId || 'okänt'}`)
    if (run) {
      sections.push(`Workflow: ${run.workflow_key} ${run.status} (Run-ID: ${run.id})`)
    }
    historyEntries.forEach((entry, index) => {
      sections.push(`--- AI-entry ${index + 1} ---`)
      sections.push(`Stage: ${entry.ai_stage_name || entry.job_type || 'Okänt'} (${entry.status})`)
      sections.push(`Log: ${entry.log_text ?? ''}`)
      sections.push(`Error: ${entry.error_message ?? ''}`)
      sections.push(`Response: ${entry.response_text ?? ''}`)
      if (showPrompts) {
        sections.push(`Prompt: ${entry.prompt_text ?? ''}`)
      }
    })
    try {
      navigator.clipboard.writeText(sections.join('\n\n'))
    } catch (error) {
      console.error('Failed to copy receipt log', error)
    }
  }, [logState.data, logState.receiptId, showPrompts])

  const resetReceiptForResume = React.useCallback((fileId) => {
    resumePending.current.add(fileId)
    setItems((prev) =>
      prev.map((item) => {
        if (item.id !== fileId) {
          return item
        }
        return {
          ...item,
          status: 'pending',
          ai_status: 'pending',
          purchase_datetime: null,
          purchase_date: null,
          file_creation_timestamp: null,
          merchant: '',
          net_amount: null,
          gross_amount: null,
          line_item_count: 0,
          file_type: 'unknown'
        }
      })
    )
    setRefreshTick((prev) => prev + 1)
  }, [])

  const loadReceipts = React.useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true)
    }
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(pageSize))
    // Add limit/offset as fallback for backend pagination
    params.set('limit', String(pageSize))
    params.set('offset', String((page - 1) * pageSize))
    if (searchTerm) {
      params.set('search', searchTerm)
    }
    if (filters.status) {
      if (filters.status.startsWith('stage:')) {
        // Workflow stage filtering - use workflow_stage_key param
        params.set('workflow_stage_key', filters.status.replace('stage:', ''))
      } else if (filters.status.startsWith('legacy:')) {
        // Legacy statuses map to ai_status
        params.set('ai_status', filters.status.replace('legacy:', ''))
      } else if (filters.status === 'status:completed') {
        // AiStatus value 'completed' (not 'passed')
        params.set('ai_status', 'completed')
      } else if (filters.status === 'status:!completed') {
        // Negation: ai_status != 'completed'
        params.set('ai_status', '!completed')
      } else if (filters.status === 'match_status:unmatched') {
        // Match status filter for unmatched receipts
        params.set('match_status', 'unmatched')
      } else if (filters.status === 'status:manual_review') {
        // AiStatus value 'manual_review'
        params.set('ai_status', 'manual_review')
      } else {
        // Default: treat as ai_status value
        params.set('ai_status', filters.status)
      }
    }
    if (filters.orgnr) params.set('orgnr', filters.orgnr)
    if (filters.from) params.set('from', filters.from)
    if (filters.to) params.set('to', filters.to)
    if (filters.tag) params.set('tags', filters.tag)
    if (filters.fileType) params.set('file_type', filters.fileType)

    // Nya filter
    if (filters.expenseType) params.set('expense_type', filters.expenseType)
    if (filters.paymentType) params.set('payment_type', filters.paymentType)
    if (filters.uploadStage) {
      params.set('upload_stage', filters.uploadStage)
    }

    // År/Månad filter (konvertera till from/to datum för purchase_date/created_at)
    // Används istället för upload_from/upload_to för att filtrera på fakturadatum
    if (filters.uploadYear) {
      let fromDate, toDate
      const year = parseInt(filters.uploadYear)

      if (filters.uploadMonth) {
        const month = parseInt(filters.uploadMonth)
        fromDate = new Date(year, month - 1, 1).toISOString().split('T')[0]
        const lastDay = new Date(year, month, 0).getDate()
        toDate = new Date(year, month - 1, lastDay).toISOString().split('T')[0]
      } else {
        fromDate = `${year}-01-01`
        toDate = `${year}-12-31`
      }

      // Om användaren inte manuellt valt datum, använd år/månad-filtret
      if (!filters.from) params.set('from', fromDate)
      if (!filters.to) params.set('to', toDate)
    }

    if (sortColumn) params.set('sort_by', sortColumn)
    if (sortDirection) params.set('sort_order', sortDirection)
    // Visa endast kvitton i Process-vyn: exkludera FirstCard/fakturaposter från API-svaret
    params.set('include_credit', '0')

    try {
      const res = await api.fetch(`/ai/api/receipts?${params.toString()}`)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = await res.json()
      const list = Array.isArray(payload?.items) ? payload.items : []
      const normalisedList = list.map((item) => {
        if (!item?.id || !resumePending.current.has(item.id)) {
          return item
        }
        const hasNewValues =
          !!(
            item.purchase_datetime ||
            item.purchase_date ||
            (typeof item.merchant === 'string' && item.merchant.trim()) ||
            (typeof item.net_amount === 'number' && !Number.isNaN(item.net_amount)) ||
            (typeof item.gross_amount === 'number' && !Number.isNaN(item.gross_amount)) ||
            (item.file_type && item.file_type !== 'unknown')
          )
        const aiStatus = typeof item.ai_status === 'string' ? item.ai_status.toLowerCase() : ''
        const shouldReleaseByStatus = aiStatus && !['pending', 'queued', 'processing', 'ftp_fetched'].includes(aiStatus)
        if (hasNewValues || shouldReleaseByStatus) {
          resumePending.current.delete(item.id)
          return item
        }
        return {
          ...item,
          status: 'pending',
          ai_status: 'pending',
          purchase_datetime: null,
          purchase_date: null,
          file_creation_timestamp: null,
          merchant: '',
          net_amount: null,
          gross_amount: null,
          line_item_count: 0,
          file_type: 'unknown'
        }
      })
      const fetchedMeta = payload?.meta || {}

      // Only update state if data has actually changed (prevents flickering during silent refresh)
      setItems(prevItems => {
        if (silent && JSON.stringify(prevItems) === JSON.stringify(normalisedList)) {
          return prevItems
        }
        return normalisedList
      })

      setMeta({
        page: fetchedMeta.page ?? page,
        page_size: fetchedMeta.page_size ?? pageSize,
        total: fetchedMeta.total ?? normalisedList.length
      })
      setRefreshTick((prev) => prev + 1)
      if (!silent) {
        setBanner({
          type: 'info',
          message: `Visar ${normalisedList.length} av ${fetchedMeta.total ?? normalisedList.length} kvitton`
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

  const displayedItems = items

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

  // Modal navigation
  const currentReceiptIndex = React.useMemo(() => {
    if (!previewState.receipt) return -1
    return displayedItems.findIndex(item => item.id === previewState.receipt.id)
  }, [displayedItems, previewState.receipt])

  const handleNavigateNext = React.useCallback(() => {
    if (currentReceiptIndex >= 0 && currentReceiptIndex < displayedItems.length - 1) {
      const nextReceipt = displayedItems[currentReceiptIndex + 1]
      setPreviewState({ receipt: nextReceipt, previewImage: null })
    }
  }, [currentReceiptIndex, displayedItems])

  const handleNavigatePrevious = React.useCallback(() => {
    if (currentReceiptIndex > 0) {
      const prevReceipt = displayedItems[currentReceiptIndex - 1]
      setPreviewState({ receipt: prevReceipt, previewImage: null })
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

      let data = {};
      try {
        data = await res.json();
      } catch (jsonError) {
        console.warn('Resume response JSON parse failed', jsonError);
      }

      if (res.ok && data.queued) {
        resetReceiptForResume(fileId);
        setBanner({
          type: 'success',
          message: data.message || `Bearbetning återupptagen: ${data.action || 'processing resumed'}`,
        });
        // Refresh immediately so the UI shows the pending state without waiting for polling
        try {
          await loadReceipts(true);
        } catch (reloadError) {
          console.error('Immediate receipts refresh failed after resume', reloadError);
        }
        // Schedule a follow-up refresh to capture pipeline progress updates
        setTimeout(() => {
          loadReceipts(true).catch((err) => console.error('Delayed receipts refresh failed after resume', err));
        }, 5000);
      } else {
        const errorMessage =
          (data && data.error) || `Kunde inte återuppta bearbetning (HTTP ${res.status})`;
        setBanner({
          type: 'error',
          message: errorMessage,
        });
      }
    } catch (error) {
      console.error('Error resuming processing:', error);
      setBanner({
        type: 'error',
        message: 'Fel vid återupptagning av bearbetning',
      });
      loadReceipts(true);
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
    const errorMessages = [];

    for (const receipt of displayedItems) {
      try {
        const res = await api.fetch(`/ai/api/ingest/process/${receipt.id}/resume`, {
          method: 'POST',
        });

        let data = {};
        try {
          data = await res.json();
        } catch (jsonError) {
          console.warn('Bulk resume JSON parse failed', jsonError);
        }

        if (res.ok && data.queued) {
          resetReceiptForResume(receipt.id);
          successCount++;
        } else {
          errorCount++;
          if (data && data.error) {
            errorMessages.push(`${receipt.original_filename || receipt.id}: ${data.error}`);
          } else {
            errorMessages.push(`${receipt.original_filename || receipt.id}: HTTP ${res.status}`);
          }
        }
      } catch (error) {
        console.error(`Error resuming ${receipt.id}:`, error);
        errorCount++;
        errorMessages.push(`${receipt.original_filename || receipt.id}: ${error instanceof Error ? error.message : error}`);
      }
    }

    if (successCount === 0) {
      const failureDetail = errorMessages.length > 0 ? `: ${errorMessages.join(', ')}` : '';
      setBanner({
        type: 'error',
        message: `Återupptagning misslyckades${failureDetail}`,
      });
    } else {
      const summary = `Återupptagning klar: ${successCount} lyckades, ${errorCount} misslyckades`;
      const detail = errorMessages.length > 0 ? ` - ${errorMessages[0]}` : '';
      setBanner({
        type: errorCount > 0 ? 'info' : 'success',
        message: `${summary}${detail}`,
      });
    }

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
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex items-center gap-1 text-xs text-gray-200">
                <input
                  type="checkbox"
                  className="form-checkbox rounded border-gray-600"
                  checked={showPrompts}
                  onChange={(event) => setShowPrompts(event.target.checked)}
                />
                <span>Visa prompts</span>
              </label>
              <button
                type="button"
                className="btn btn-secondary btn-sm flex items-center gap-1"
                onClick={handleCopyAll}
                disabled={logState.loading || !logState.data}
              >
                <FiCopy />
                Kopiera allt
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => handleClearReceiptLog(receiptIdForModal)}
                disabled={!receiptIdForModal || logState.loading || logActionState.clearing}
              >
                {logActionState.clearing ? (
                  <>
                    <div className="loading-spinner w-4 h-4 mr-2" />
                    Rensar...
                  </>
                ) : (
                  <>
                    <FiTrash2 className="mr-1" />
                    Rensa logg
                  </>
                )}
              </button>
              <button type="button" className="icon-button" onClick={closeLogViewer} aria-label="Stäng logg">
                <FiX />
              </button>
            </div>
          </div>

          <div className="modal-body space-y-6 max-h-[70vh] overflow-y-auto">
            {logActionState.error && (
              <div className="alert alert-error">
                <FiAlertCircle className="mr-2" />
                <span>{`Kunde inte rensa logg: ${logActionState.error}`}</span>
              </div>
            )}
            {logActionState.success && (
              <div className="alert alert-success">
                <FiCheckCircle className="mr-2" />
                <span>{logActionState.success}</span>
              </div>
            )}
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
                          {entry.response_text && (
                            <div className="text-xs text-gray-300 bg-gray-900/60 border border-gray-700/70 rounded-md p-2">
                              <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1">Response</div>
                              <pre className="whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                                {entry.response_text}
                              </pre>
                            </div>
                          )}
                          {showPrompts && entry.prompt_text && (
                            <div className="text-xs text-gray-100 bg-blue-900/30 border border-blue-800/40 rounded-md p-2">
                              <div className="text-[10px] uppercase tracking-wide text-blue-200 mb-1">Prompt</div>
                              <pre className="whitespace-pre-wrap font-mono max-h-48 overflow-y-auto text-blue-100">
                                {entry.prompt_text}
                              </pre>
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

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Filter</h3>
        </div>
        <div className="p-4 space-y-4">
          {/* Första raden */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <label className="filter-field">
              <span>Status</span>
              <select
                value={filters.status}
                onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                className="dm-input"
                disabled={loading}
              >
                {statusOptions.map((opt) => (
                  <option key={opt.value || opt.label} value={opt.value} disabled={opt.disabled}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="filter-field">
              <span>Upload</span>
              <select
                value={filters.uploadStage}
                onChange={(e) => setFilters(prev => ({ ...prev, uploadStage: e.target.value }))}
                className="dm-input"
                disabled={loading}
              >
                {uploadStageOptions.map((opt) => (
                  <option key={opt.value || opt.label} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="filter-field">
              <span>Dokumenttyp</span>
              <select
                value={filters.fileType}
                onChange={(e) => setFilters(prev => ({ ...prev, fileType: e.target.value }))}
                className="dm-input"
                disabled={loading}
              >
                <option value="">Alla</option>
                <option value="receipt">Kvitton</option>
                <option value="invoice">Fakturor</option>
                <option value="other">Övriga</option>
              </select>
            </label>

            <label className="filter-field">
              <span>Utgiftstyp</span>
              <select
                value={filters.expenseType}
                onChange={(e) => setFilters(prev => ({ ...prev, expenseType: e.target.value }))}
                className="dm-input"
                disabled={loading}
              >
                <option value="">Alla typer</option>
                <option value="personal">Personal</option>
                <option value="corporate">Corporate</option>
              </select>
            </label>

            <label className="filter-field">
              <span>Betalningstyp</span>
              <select
                value={filters.paymentType}
                onChange={(e) => setFilters(prev => ({ ...prev, paymentType: e.target.value }))}
                className="dm-input"
                disabled={loading}
              >
                <option value="">Alla</option>
                <option value="card">Kort</option>
                <option value="swish">Swish</option>
                <option value="cash">Kontant</option>
              </select>
            </label>
          </div>

          {/* Andra raden */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="filter-field">
              <span>År</span>
              <select
                value={filters.uploadYear}
                onChange={(e) => setFilters(prev => ({ ...prev, uploadYear: e.target.value }))}
                className="dm-input"
                disabled={loading}
              >
                <option value="">Alla år</option>
                {Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i).map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </label>

            <label className="filter-field">
              <span>Månad</span>
              <select
                value={filters.uploadMonth}
                onChange={(e) => setFilters(prev => ({ ...prev, uploadMonth: e.target.value }))}
                className="dm-input"
                disabled={loading}
              >
                <option value="">Alla månader</option>
                <option value="01">Januari</option>
                <option value="02">Februari</option>
                <option value="03">Mars</option>
                <option value="04">April</option>
                <option value="05">Maj</option>
                <option value="06">Juni</option>
                <option value="07">Juli</option>
                <option value="08">Augusti</option>
                <option value="09">September</option>
                <option value="10">Oktober</option>
                <option value="11">November</option>
                <option value="12">December</option>
              </select>
            </label>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setFilters(initialFilters)}
              disabled={loading}
            >
              Rensa filter
            </button>
          </div>
        </div>
      </div>

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
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('purchase_datetime')}>
                  Fakturadatum/Inköpsdatum {sortColumn === 'purchase_datetime' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('company')}>
                  Företag {sortColumn === 'company' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th>Upload</th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('expense_type')}>
                  Utgiftstyp {sortColumn === 'expense_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('payment_type')}>
                  Betalningstyp {sortColumn === 'payment_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('uploaded_at')}>
                  Uppladdningsdatum {sortColumn === 'uploaded_at' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th>Sista 4</th>
                <th className="text-right cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('net_amount')}>
                  Exkl. moms {sortColumn === 'net_amount' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="text-right cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('gross_amount')}>
                  Inkl. moms {sortColumn === 'gross_amount' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="text-center">Matchad</th>
                <th className="text-center">MANUAL</th>
                <th className="text-center cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('status')}>
                  Status {sortColumn === 'status' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="cursor-pointer hover:bg-gray-800/40 select-none" onClick={() => handleSort('file_type')}>
                  Dokumenttyp {sortColumn === 'file_type' && (sortDirection === 'asc' ? '▲' : '▼')}
                </th>
                <th className="text-center">Plats</th>
                <th className="text-center">Ladda ned</th>
                <th className="text-center">Logg</th>
                <th className="text-center">Återuppta</th>
                <th className="text-center">Radera</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={19} className="table-loading">
                    <div className="loading-inline">
                      <div className="loading-spinner" />
                      <span>Laddar kvitton...</span>
                    </div>
                  </td>
                </tr>
              ) : displayedItems.length === 0 ? (
                <tr>
                  <td colSpan={19} className="table-empty">
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
                      <div className="font-medium">{formatDate(receipt.purchase_datetime || receipt.purchase_date || receipt.file_creation_timestamp)}</div>
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
                    <td>
                      {(() => {
                        // 1) Explicit upload stage (src_*)
                        if (receipt.upload_stage) {
                          const key = (receipt.upload_stage.stage_key || '').toLowerCase()
                          if (key.startsWith('src_portal')) return <span className="text-sm">Manuellt</span>
                          if (key.startsWith('src_ftp')) return <span className="text-sm">FTP</span>
                          return (
                            <StatusBadge
                              status={`${receipt.upload_stage.stage_key || ''} ${receipt.upload_stage.status || ''}`.trim()}
                              stageKey={receipt.upload_stage.stage_key}
                              stageStatus={receipt.upload_stage.status}
                            />
                          )
                        }

                        // 2) Workflow source_channel from workflow_runs
                        const sourceChannel = (receipt.workflow_source_channel || '').toLowerCase()
                        if (sourceChannel.includes('ftp')) return <span className="text-sm">FTP</span>
                        if (sourceChannel.includes('portal') || sourceChannel.includes('manual')) return <span className="text-sm">Manuellt</span>

                        // 3) Fallback
                        return <div className="text-sm text-gray-400">-</div>
                      })()}
                    </td>
                    <td>
                      <div className="font-medium text-sm">
                        {receipt.expense_type || '-'}
                      </div>
                    </td>
                    <td>
                      <div className="font-medium text-sm">
                        {receipt.payment_type || '-'}
                      </div>
                    </td>
                    <td>
                      <div className="font-medium text-sm">
                        {formatDate(receipt.file_creation_timestamp || receipt.created_at, true)}
                      </div>
                    </td>
                    <td>
                      <div className="font-medium text-sm">
                        {receipt.credit_card_last_4 || '-'}
                      </div>
                    </td>
                    <td className="text-right">{formatCurrency(receipt.net_amount_display, receipt.currency)}</td>
                    <td className="text-right text-lg font-semibold">{formatCurrency(receipt.gross_amount_display, receipt.currency)}</td>
                    <td className="text-center">
                      {(() => {
                        const status = (receipt.ai_status || '').toLowerCase()
                        const stage = (receipt.workflow_stage_key || '').toLowerCase()
                        const matched =
                          status.includes('match') ||
                          ['m_link', 'm_found'].includes(stage) ||
                          stage.startsWith('m_link') ||
                          stage === 'ai5'
                        return matched ? 'Ja' : 'Nej'
                      })()}
                    </td>
                    <td className="text-center">
                      {(() => {
                        const status = (receipt.ai_status || '').toLowerCase()
                        return status === 'manual_review' ? '!' : ''
                      })()}
                    </td>
                    <td className="text-center">
                      <StatusBadge
                        status={receipt.workflow_stage_status || receipt.status || receipt.ai_status}
                        stageKey={receipt.workflow_stage_key}
                        stageStatus={receipt.workflow_stage_state}
                      />
                    </td>
                    <td>
                      <div className="font-medium text-sm">
                        {!receipt.file_type || receipt.file_type === 'unknown' || receipt.file_type === '' ? 'Okänd' :
                          receipt.file_type === 'receipt' ? 'Kvitto' :
                            receipt.file_type === 'invoice' ? 'Faktura' :
                              receipt.file_type === 'other' ? 'Övrigt' :
                                'Okänd'}
                      </div>
                    </td>
                    <td className="text-center">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleShowMap(receipt)}>
                        <FiMapPin />
                      </button>
                    </td>
                    <td className="text-center">
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => handleDownload(receipt)}>
                        <FiDownload />
                      </button>
                    </td>
                    <td className="text-center">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => fetchReceiptLog(receipt.id)}
                        title="Visa logg">
                        <FiFileText />
                      </button>
                    </td>
                    <td className="text-center">
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
                      </button>
                    </td>
                    <td className="text-center">
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(receipt)}
                        title="Radera kvitto">
                        <FiTrash2 />
                      </button>
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
        onReceiptUpdate={(updated) => {
          if (updated?.deleted) {
            // Handle navigation after deletion using state updater
            if (updated.shouldNavigateNext) {
              setItems((prevItems) => {
                const currentIndex = prevItems.findIndex(item => item.id === updated.id)
                const newList = prevItems.filter(item => item.id !== updated.id)

                // The next receipt will now be at the same index as the deleted one
                if (currentIndex >= 0 && currentIndex < newList.length) {
                  const nextReceipt = newList[currentIndex]
                  setPreviewState({ receipt: nextReceipt, previewImage: null })
                } else {
                  // No more receipts, close modal
                  closePreview()
                }

                return newList
              })
            } else {
              // Remove from items list and close modal
              setItems((prev) => prev.filter((item) => item.id !== updated.id))
              closePreview()
            }
          } else {
            loadReceipts(true)
            closePreview()
          }
        }}
        onNavigateNext={handleNavigateNext}
        onNavigatePrevious={handleNavigatePrevious}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
      />
      {renderLogModal()}
    </div>
  )
}
