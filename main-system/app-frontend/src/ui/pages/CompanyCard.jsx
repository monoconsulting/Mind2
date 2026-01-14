import React from 'react'
import {
  FiRefreshCw,
  FiCheckCircle,
  FiAlertTriangle,
  FiFileText,
  FiUpload,
  FiEye,
  FiLink,
  FiX,
  FiChevronRight,
  FiAlertCircle,
  FiTrash2,
  FiPercent,
} from 'react-icons/fi'
import ReceiptPreviewModal from '../components/ReceiptPreviewModal'
import DocumentPreviewModal from '../components/DocumentPreviewModal'
import { api } from '../api'

const MOJIBAKE_PATTERN = /\u00c3[\x80-\xBF]/;
let cachedUtf8Decoder = null;

function ensureUtf8Decoder() {
  if (cachedUtf8Decoder) {
    return cachedUtf8Decoder;
  }
  if (typeof TextDecoder === 'function') {
    try {
      cachedUtf8Decoder = new TextDecoder('utf-8', { fatal: false });
    } catch (err) {
      cachedUtf8Decoder = null;
    }
  }
  return cachedUtf8Decoder;
}

function fixMojibakeString(value) {
  if (typeof value !== 'string' || value.length === 0) {
    return value;
  }
  if (!MOJIBAKE_PATTERN.test(value)) {
    return value;
  }
  try {
    const decoder = ensureUtf8Decoder();
    if (decoder) {
      const bytes = new Uint8Array(value.length);
      for (let index = 0; index < value.length; index += 1) {
        bytes[index] = value.charCodeAt(index) & 0xff;
      }
      const decoded = decoder.decode(bytes);
      if (decoded && decoded !== value) {
        return decoded;
      }
    }
  } catch (err) {
    // Swallow and fall back
  }
  if (typeof Buffer !== 'undefined') {
    try {
      const decoded = Buffer.from(value, 'latin1').toString('utf8');
      if (decoded && decoded !== value) {
        return decoded;
      }
    } catch (err) {
      // Ignore buffer fallback failure
    }
  }
  if (typeof decodeURIComponent === 'function' && typeof escape === 'function') {
    try {
      const decoded = decodeURIComponent(escape(value));
      if (decoded && decoded !== value) {
        return decoded;
      }
    } catch (err) {
      // ignore
    }
  }
  return value;
}

function fixEncodingDeep(value) {
  if (typeof value === 'string') {
    return fixMojibakeString(value);
  }
  if (Array.isArray(value)) {
    return value.map((entry) => fixEncodingDeep(entry));
  }
  if (value && typeof value === 'object') {
    const next = {};
    for (const [key, nested] of Object.entries(value)) {
      next[key] = fixEncodingDeep(nested);
    }
    return next;
  }
  return value;
}

const DOCUMENT_STATUS_MAP = [
  { ids: ['matched', 'matchad', 'completed', 'done', 'success'], label: 'Matchad', tone: 'success' },
  { ids: ['partially_matched', 'ready_for_matching', 'processed'], label: 'Bearbetad', tone: 'success' },
  { ids: ['processing', 'matching', 'running', 'ai_processing', 'ocr_done'], label: 'Under bearbetning', tone: 'processing' },
  { ids: ['queued', 'pending', 'created', 'uploaded', 'imported', 'ocr_pending'], label: 'Ej bearbetad', tone: 'pending' },
  { ids: ['failed', 'error'], label: 'Fel', tone: 'failed' },
]

const LINE_STATUS_MAP = {
  auto: { label: 'Auto', tone: 'success' },
  manual: { label: 'Manuell', tone: 'processing' },
  confirmed: { label: 'Bekräftad', tone: 'success' },
  unmatched: { label: 'Obearbetad', tone: 'pending' },
  ignored: { label: 'Ignorerad', tone: 'pending' },
  pending: { label: 'I kö', tone: 'pending' },
}

const IMPORT_STAGE_LABELS = {
  src_portal: 'Portaluppladdning',
  src_ftp: 'FTP-import',
  src_fc: 'FirstCard-uppladdning',
  ingest_store: 'Lagra filmetadata',
  ingest_wf1: 'Skapa WF1',
  fc_create: 'Skapa FC-dokument',
  fc_ocr: 'OCR FirstCard',
  fc_parse: 'AI6 – FC-parsning',
  fc_ready: 'FC redo för matchning',
  fc_is_fc: 'FC-verifiering',
  detect_type: 'AI1 – Dokumentklassning',
  r_ocr: 'OCR kvitto',
  r_ai3: 'AI3 – Dataextraktion',
  r_ai4: 'AI4 – Normalisering',
  r_persist: 'Spara extraherad data',
  r_queue_match: 'Köa för matchning',
  ai5: 'AI5 – Matchning',
  m_found: 'Match hittad?',
  m_link: 'Länka kvitto',
  m_unmatched: 'Omatchade rader',
  finalize_ok: 'Slutförd',
  finalize_fail: 'Avslutad med fel',
  manual_review: 'Manuell granskning',
  resume_dispatch: 'Återupptar',
  restart_dispatch: 'Omstartar',
  KLAR: 'KLAR',
}

const toneClass = {
  success: 'status-passed',
  processing: 'status-processing',
  pending: 'status-pending',
  failed: 'status-failed',
}

const INITIAL_SYSTEM_SUMMARY = {
  receipts: { matched: 0, total: 0 },
  purchases: { unmatched: 0, total: 0 },
  invoices: { incomplete: 0, total: 0 },
}

// Map stage keys to tone colors
function getStageResultTone(stageKey) {
  if (!stageKey) return 'pending'

  // Completed/success stages
  if (['finalize_ok', 'KLAR', 'm_link', 'fc_ready'].includes(stageKey)) {
    return 'success'
  }

  // Failed stages
  if (['finalize_fail'].includes(stageKey) || stageKey.includes('fail')) {
    return 'failed'
  }

  // Processing stages (everything else is in progress)
  return 'processing'
}

function normalizeStatus(status) {
  return String(status ?? '').toLowerCase()
}

function describeDocumentStatus(status) {
  const normalized = normalizeStatus(status)
  const match = DOCUMENT_STATUS_MAP.find(({ ids }) => ids.includes(normalized))
  if (match) {
    return match
  }
  return { label: status || 'Okänd', tone: 'pending' }
}

function describeLineStatus(status) {
  if (!status) {
    return LINE_STATUS_MAP.pending
  }
  return LINE_STATUS_MAP[normalizeStatus(status)] ?? { label: status, tone: 'pending' }
}

function formatDate(value, withTime = true) {
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
    return parsed.toLocaleString('sv-SE', withTime
      ? { dateStyle: 'short', timeStyle: 'short' }
      : { dateStyle: 'short' })
  } catch (error) {
    return typeof value === 'string' ? value : '-'
  }
}

function formatNumber(value) {
  const numeric = Number(value ?? 0)
  if (Number.isNaN(numeric)) {
    return '0'
  }
  return numeric.toLocaleString('sv-SE')
}

function describeProcessingStatus(status) {
  const normalized = normalizeStatus(status)
  switch (normalized) {
    case 'ocr_pending':
      return { label: 'OCR pågår', tone: 'processing' }
    case 'ocr_done':
      return { label: 'OCR klar', tone: 'processing' }
    case 'ai_processing':
      return { label: 'AI6 bearbetar', tone: 'processing' }
    case 'ready_for_matching':
      return { label: 'Redo för matchning', tone: 'success' }
    case 'matching_completed':
      return { label: 'Matchning klar', tone: 'success' }
    case 'failed':
      return { label: 'Misslyckades', tone: 'failed' }
    default:
      return { label: status || 'Okänd', tone: 'processing' }
  }
}

function describeFirstCardStatus(statement) {
  if (!statement) {
    return { label: 'Okänd', tone: 'pending' }
  }

  // Use current_stage_key from workflow if available
  const stageKey = statement.current_stage_key
  if (stageKey && IMPORT_STAGE_LABELS[stageKey]) {
    return {
      label: IMPORT_STAGE_LABELS[stageKey],
      tone: getStageResultTone(stageKey),
    }
  }

  // Fallback to processing_status if no stage key
  const processing = normalizeStatus(statement.processing_status || statement.status)
  switch (processing) {
    case 'uploaded':
    case 'imported':
    case 'ocr_pending':
      return { label: 'PDF', tone: 'pending' }
    case 'ocr_done':
    case 'ai_processing':
      return { label: 'OCR', tone: 'processing' }
    case 'ready_for_matching':
      return { label: 'AI5', tone: 'processing' }
    case 'matching_completed':
    case 'completed':
      return { label: 'Match Done (AI6)', tone: 'success' }
    case 'failed':
      return { label: 'Fel', tone: 'failed' }
    default:
      return describeDocumentStatus(statement.status)
  }
}

function formatStageLabel(key) {
  if (!key) {
    return 'Okänd'
  }
  if (IMPORT_STAGE_LABELS[key]) {
    return IMPORT_STAGE_LABELS[key]
  }
  if (key.endsWith('_start')) {
    const base = key.replace(/_start$/, '')
    const label = IMPORT_STAGE_LABELS[base] || base
    return `${label} – start`
  }
  if (key.endsWith('_end')) {
    const base = key.replace(/_end$/, '')
    const label = IMPORT_STAGE_LABELS[base] || base
    return `${label} – klart`
  }
  return key
}


const currencyFormatter = new Intl.NumberFormat('sv-SE', {
  style: 'currency',
  currency: 'SEK',
  minimumFractionDigits: 2,
})

function formatAmount(value) {
  if (value === null || value === undefined) {
    return '-'
  }
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return String(value)
  }
  return currencyFormatter.format(num)
}

function formatCurrency(value, currency = 'SEK') {
  if (value === null || value === undefined) {
    return '-'
  }
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return String(value)
  }
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
    }).format(num)
  } catch (error) {
    return currencyFormatter.format(num)
  }
}

function formatDurationMs(durationMs) {
  if (durationMs === null || durationMs === undefined) {
    return null
  }
  const value = Number(durationMs)
  if (!Number.isFinite(value) || value < 0) {
    return null
  }
  if (value < 1000) {
    return `${Math.round(value)} ms`
  }
  const seconds = value / 1000
  if (seconds < 60) {
    const rounded = seconds < 10 ? seconds.toFixed(2) : seconds.toFixed(1)
    return `${rounded.replace(/\.0+$/, '')} s`
  }
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds - minutes * 60)
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`
  }
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return `${hours}h ${remainingMinutes}m`
}

const initialCandidatesState = {
  open: false,
  line: null,
  candidates: [],
  loading: false,
}

const INITIAL_LOG_STATE = {
  open: false,
  loading: false,
  error: null,
  data: null,
  invoiceId: null,
}

function buildUploadErrorMessage(status, payload) {
  const code = payload?.error
  switch (code) {
    case 'duplicate_file':
      return 'Filen har redan laddats upp tidigare.'
    case 'unsupported_file_type':
      return 'Filtypen stöds inte. Ladda upp en PDF eller bildfil.'
    case 'empty_file':
      return 'Filen var tom.'
    case 'missing_file':
      return 'Ingen fil skickades.'
    case 'upload_failed':
      return payload?.details
        ? `Serverfel: ${payload.details}`
        : 'Servern rapporterade ett fel under uppladdningen.'
    default:
      if (status === 413) {
        return 'Filen är för stor.'
      }
      if (status === 415) {
        return 'Filtypen stöds inte.'
      }
      if (status >= 500) {
        return 'Serverfel uppstod.'
      }
      if (status >= 400) {
        return `Fel ${status}.`
      }
      return 'Okänt fel.'
  }
}

export default function CompanyCard() {
  const [items, setItems] = React.useState([])
  const [loading, setLoading] = React.useState(false)
  const [documentFeedback, setDocumentFeedback] = React.useState(null)
  const [matchingDocumentId, setMatchingDocumentId] = React.useState(null)

  const [selectedDocumentId, setSelectedDocumentId] = React.useState(null)
  const [previewOpen, setPreviewOpen] = React.useState(false)
  const [previewInvoiceId, setPreviewInvoiceId] = React.useState(null)
  const selectedDocumentIdRef = React.useRef(null)
  const [selectedDocument, setSelectedDocument] = React.useState(null)
  const [documentLines, setDocumentLines] = React.useState([])
  const [documentItems, setDocumentItems] = React.useState([])
  const [systemSummary, setSystemSummary] = React.useState(INITIAL_SYSTEM_SUMMARY)
  const [systemSummaryLoading, setSystemSummaryLoading] = React.useState(false)
  const [detailLoading, setDetailLoading] = React.useState(false)

  const [candidateState, setCandidateState] = React.useState(initialCandidatesState)
  const [assigningLineId, setAssigningLineId] = React.useState(null)
  const [candidateFeedback, setCandidateFeedback] = React.useState(null)
  const [deletingDocumentId, setDeletingDocumentId] = React.useState(null)

  const [previewReceipt, setPreviewReceipt] = React.useState(null)
  const [previewImage, setPreviewImage] = React.useState(null)
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false)
  const [logState, setLogState] = React.useState(INITIAL_LOG_STATE)
  const [logActionState, setLogActionState] = React.useState({ clearing: false, error: '', success: '' })

  const [sortColumn, setSortColumn] = React.useState('updated_at')
  const [sortDirection, setSortDirection] = React.useState('desc')
  const [sortLineColumn, setSortLineColumn] = React.useState('transaction_date')
  const [sortLineDirection, setSortLineDirection] = React.useState('desc')

  React.useEffect(() => {
    selectedDocumentIdRef.current = selectedDocumentId
  }, [selectedDocumentId])

  const loadSystemSummary = React.useCallback(async () => {
    setSystemSummaryLoading(true)
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/summary')
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      let payload = await res.json()
      payload = fixEncodingDeep(payload)
      setSystemSummary({
        receipts: {
          matched: Number(payload?.receipts?.matched) || 0,
          total: Number(payload?.receipts?.total) || 0,
        },
        purchases: {
          unmatched: Number(payload?.purchases?.unmatched) || 0,
          total: Number(payload?.purchases?.total) || 0,
        },
        invoices: {
          incomplete: Number(payload?.invoices?.incomplete) || 0,
          total: Number(payload?.invoices?.total) || 0,
        },
      })
    } catch (error) {
      console.error('Failed to load FirstCard summary', error)
    } finally {
      setSystemSummaryLoading(false)
    }
  }, [])

  const loadStatements = React.useCallback(async (preferredId = selectedDocumentIdRef.current) => {
    setLoading(true)
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      let data = await res.json()
      data = fixEncodingDeep(data)
      const nextItems = Array.isArray(data?.statements) ? data.statements : []
      setItems(nextItems)
      if (!nextItems.length) {
        setSelectedDocumentId(null)
        setSelectedDocument(null)
        setDocumentLines([])
        setDocumentItems([])
        setDocumentFeedback({
          type: 'info',
          text: 'Inga kontoutdrag hittades. Ladda upp ett utdrag för att börja matcha kvitton.',
        })
      } else {
        const targetId = preferredId && nextItems.some((item) => item.id === preferredId)
          ? preferredId
          : nextItems[0].id
        setSelectedDocumentId(targetId)
        setDocumentItems([])
        setDocumentFeedback(null)
      }
      return nextItems
    } catch (error) {
      console.error('Failed to load statements', error)
      setItems([])
      setSelectedDocumentId(null)
      setSelectedDocument(null)
      setDocumentLines([])
      setDocumentItems([])
      setDocumentFeedback({
        type: 'error',
        text: `Fel vid hämtning av kontoutdrag: ${error instanceof Error ? error.message : error}`,
      })
      return []
    } finally {
      setLoading(false)
    }
  }, [])

  const loadDocumentDetail = React.useCallback(async (invoiceId) => {
    if (!invoiceId) {
      setSelectedDocument(null)
      setDocumentLines([])
      setDocumentItems([])
      return
    }
    setDetailLoading(true)
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      let data = await res.json()
      data = fixEncodingDeep(data)
      const invoice = data?.invoice ?? null
      const lines = Array.isArray(data?.lines) ? data.lines : []
      const items = Array.isArray(data?.items) ? data.items : []
      setSelectedDocument(invoice)
      setDocumentLines(lines)
      setDocumentItems(items)
    } catch (error) {
      console.error('Failed to load invoice detail', error)
      setSelectedDocument(null)
      setDocumentLines([])
      setDocumentItems([])
      setDocumentFeedback({
        type: 'error',
        text: `Kunde inte hämta detaljer för utdraget (${invoiceId}): ${error instanceof Error ? error.message : error}`,
      })
    } finally {
      setDetailLoading(false)
    }
  }, [])

  React.useEffect(() => {
    loadStatements()
    loadSystemSummary()

    const intervalId = setInterval(() => {
      loadStatements(selectedDocumentIdRef.current)
      loadSystemSummary()
    }, 15000) // Poll every 15 seconds

    return () => clearInterval(intervalId) // Cleanup on unmount
  }, [loadStatements, loadSystemSummary])

  React.useEffect(() => {
    if (selectedDocumentId) {
      loadDocumentDetail(selectedDocumentId)
    }
  }, [selectedDocumentId, loadDocumentDetail])

  const fetchInvoiceLog = React.useCallback(async (invoiceId) => {
    if (!invoiceId) {
      return
    }
    setLogState((prev) => ({
      open: true,
      loading: true,
      error: null,
      data: prev.invoiceId === invoiceId ? prev.data : null,
      invoiceId,
    }))
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}/log`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const payloadRaw = await res.json()
      const payload = fixEncodingDeep(payloadRaw)
      setLogState({
        open: true,
        loading: false,
        error: null,
        data: payload,
        invoiceId,
      })
    } catch (error) {
      console.error('Failed to fetch invoice log', error)
      setLogState({
        open: true,
        loading: false,
        error: error instanceof Error ? error.message : String(error),
        data: null,
        invoiceId,
      })
    }
  }, [])

  const closeLogViewer = React.useCallback(() => {
    setLogState(INITIAL_LOG_STATE)
    setLogActionState({ clearing: false, error: '', success: '' })
  }, [])

  const handleClearInvoiceLog = React.useCallback(async (invoiceId) => {
    if (!invoiceId || logActionState.clearing) {
      return
    }
    if (!window.confirm('Vill du rensa alla loggar för detta kontoutdrag? Detta går inte att ångra.')) {
      return
    }
    setLogActionState({ clearing: true, error: '', success: '' })
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}/log`, { method: 'DELETE' })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      await res.json().catch(() => ({}))
      setLogActionState({ clearing: false, error: '', success: 'Loggen rensades.' })
      await fetchInvoiceLog(invoiceId)
    } catch (error) {
      setLogActionState({
        clearing: false,
        error: error instanceof Error ? error.message : String(error),
        success: ''
      })
    }
  }, [fetchInvoiceLog, logActionState.clearing])

  const onMatchDocument = React.useCallback(async (statementId) => {
    if (!statementId) return
    setMatchingDocumentId(statementId)
    try {
      const response = await api.fetch('/ai/api/reconciliation/firstcard/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: statementId }),
      })

      if (!response.ok) {
        throw new Error(`Status ${response.status}`)
      }

      setDocumentFeedback({ type: 'success', text: 'Matchning klar. Uppdaterar listan...' })
      await loadStatements(statementId)
      await loadDocumentDetail(statementId)
    } catch (error) {
      setDocumentFeedback({
        type: 'error',
        text: `Matchningen misslyckades: ${error instanceof Error ? error.message : error}`,
      })
    } finally {
      setMatchingDocumentId(null)
    }
  }, [loadStatements, loadDocumentDetail])

  const handleDeleteStatement = React.useCallback(
    async (statementId) => {
      if (!statementId) return
      if (typeof window !== 'undefined') {
        const confirmed = window.confirm('Är du säker på att du vill ta bort utdraget?')
        if (!confirmed) {
          return
        }
      }
      setDeletingDocumentId(statementId)
      try {
        const res = await api.fetch(`/ai/api/reconciliation/firstcard/statements/${statementId}`, {
          method: 'DELETE',
        })
        if (!res.ok) {
          let message = `Status ${res.status}`
          try {
            const payload = await res.json()
            if (payload?.error) {
              message = payload.error
            }
          } catch (error) {
            // ignore json parse errors
          }
          throw new Error(message)
        }
        if (selectedDocumentId === statementId) {
          setSelectedDocumentId(null)
          setSelectedDocument(null)
          setDocumentLines([])
          setDocumentItems([])
        }
        const refreshed = await loadStatements()
        if (Array.isArray(refreshed) && refreshed.length > 0) {
          setDocumentFeedback({
            type: 'success',
            text: 'Utdraget har tagits bort.',
          })
        }
      } catch (error) {
        setDocumentFeedback({
          type: 'error',
          text: `Kunde inte ta bort utdraget: ${error instanceof Error ? error.message : error}`,
        })
      } finally {
        setDeletingDocumentId(null)
      }
    },
    [loadStatements, selectedDocumentId],
  )

  const [matchingAllUnmatched, setMatchingAllUnmatched] = React.useState(false)

  const handleMatchAllUnmatched = React.useCallback(async () => {
    const unmatchedStatements = items.filter((item) => (item.line_counts?.unmatched ?? 0) > 0)
    if (!unmatchedStatements.length) {
      setDocumentFeedback({
        type: 'info',
        text: 'Inga omatchade poster hittades.',
      })
      return
    }

    setMatchingAllUnmatched(true)
    let successCount = 0
    let failCount = 0

    for (const statement of unmatchedStatements) {
      try {
        const response = await api.fetch('/ai/api/reconciliation/firstcard/match', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ document_id: statement.id }),
        })

        if (response.ok) {
          successCount++
        } else {
          failCount++
        }
      } catch (error) {
        console.error(`Failed to match statement ${statement.id}`, error)
        failCount++
      }
    }

    setMatchingAllUnmatched(false)
    await loadStatements(selectedDocumentIdRef.current)
    if (selectedDocumentId) {
      await loadDocumentDetail(selectedDocumentId)
    }

    if (failCount === 0) {
      setDocumentFeedback({
        type: 'success',
        text: `Matchning klar. ${successCount} utdrag har bearbetats.`,
      })
    } else {
      setDocumentFeedback({
        type: 'warning',
        text: `Matchning delvis klar. ${successCount} lyckades, ${failCount} misslyckades.`,
      })
    }
  }, [items, loadStatements, loadDocumentDetail, selectedDocumentId])

  const [resumingDocumentId, setResumingDocumentId] = React.useState(null)
  const pollingIntervalRef = React.useRef(null)

  // Silent refresh - no loading state, no flickering
  const silentRefreshStatements = React.useCallback(async () => {
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
      if (!res.ok) {
        return null
      }
      let data = await res.json()
      data = fixEncodingDeep(data)
      return Array.isArray(data?.statements) ? data.statements : []
    } catch (error) {
      console.error('Silent refresh failed', error)
      return null
    }
  }, [])

  const startStatusPolling = React.useCallback((statementId) => {
    // Clear any existing polling
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }

    // Poll every 2 seconds
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const refreshedItems = await silentRefreshStatements()

        if (!refreshedItems) return

        // Find the statement we're polling for
        const statement = refreshedItems.find(item => item.id === statementId)

        if (statement) {
          const processingStatus = statement.processing_status
          const status = statement.status

          // Only update state if data has actually changed
          setItems(prevItems => {
            const oldStatement = prevItems.find(item => item.id === statementId)
            const hasChanged = !oldStatement ||
                              oldStatement.processing_status !== processingStatus ||
                              oldStatement.status !== status

            return hasChanged ? refreshedItems : prevItems
          })

          // Stop polling if we reach a terminal state
          if (processingStatus === 'matching_completed' ||
              status === 'matched' ||
              status === 'failed' ||
              processingStatus === 'ready_for_matching') {
            clearInterval(pollingIntervalRef.current)
            pollingIntervalRef.current = null
            setResumingDocumentId(null)
          }
        }
      } catch (error) {
        console.error('Polling error:', error)
      }
    }, 2000)
  }, [silentRefreshStatements])

  // Cleanup polling on unmount
  React.useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  const handleResumeOrRestartInvoice = React.useCallback(async (statementId, processingStatus) => {
    if (!statementId) return
    setResumingDocumentId(statementId)

    try {
      // Determine if we should resume or restart based on processing_status
      const isCompleted = processingStatus === 'matching_completed' || processingStatus === 'ready_for_matching'
      const action = isCompleted ? 'restart' : 'resume'

      const response = await api.fetch(`/ai/api/reconciliation/firstcard/statements/${statementId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })

      if (!response.ok) {
        throw new Error(`Status ${response.status}`)
      }

      const result = await response.json()

      setDocumentFeedback({
        type: 'success',
        text: `Fakturaimport ${action === 'restart' ? 'omstartas' : 'återupptas'}...`,
      })

      // Update the statement in state immediately with the new status
      if (result.processing_status || result.status || result.current_stage_key) {
        setStatements(prev => prev.map(stmt =>
          stmt.id === statementId
            ? {
                ...stmt,
                processing_status: result.processing_status || stmt.processing_status,
                status: result.status || stmt.status,
                current_stage_key: result.current_stage_key || stmt.current_stage_key,
              }
            : stmt
        ))
      }

      // Also reload from server to get full details
      await loadStatements(statementId)
      if (selectedDocumentId === statementId) {
        await loadDocumentDetail(statementId)
      }

      // Start polling for status updates
      startStatusPolling(statementId)

    } catch (error) {
      setDocumentFeedback({
        type: 'error',
        text: `Kunde inte återuppta fakturaimport: ${error instanceof Error ? error.message : error}`,
      })
      setResumingDocumentId(null)
    }
  }, [loadStatements, loadDocumentDetail, selectedDocumentId, startStatusPolling])

  const onOpenCandidates = React.useCallback(async (line) => {
    if (!line) return
    setCandidateState({ open: true, line, candidates: [], loading: true })
    setCandidateFeedback(null)
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/lines/${line.id}/candidates`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const data = await res.json()
      const candidates = Array.isArray(data?.candidates) ? data.candidates : []
      setCandidateState({ open: true, line: data?.line ?? line, candidates, loading: false })
    } catch (error) {
      console.error('Failed to load candidates', error)
      setCandidateState({ open: true, line, candidates: [], loading: false })
      setCandidateFeedback({
        type: 'error',
        text: `Kunde inte hämta kandidater: ${error instanceof Error ? error.message : error}`,
      })
    }
  }, [])

  const closeCandidates = React.useCallback(() => {
    setCandidateState(initialCandidatesState)
    setCandidateFeedback(null)
  }, [])

  const assignCandidate = React.useCallback(async (lineId, receiptId) => {
    if (!lineId || !receiptId) return
    setAssigningLineId(lineId)
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/lines/${lineId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ matched_file_id: receiptId }),
      })
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      setCandidateFeedback({ type: 'success', text: 'Kvitto matchat mot raden.' })
      await loadStatements(selectedDocumentIdRef.current)
      await loadDocumentDetail(selectedDocumentIdRef.current)
      closeCandidates()
    } catch (error) {
      console.error('Failed to assign candidate', error)
      setCandidateFeedback({
        type: 'error',
        text: `Kunde inte matcha kvittot: ${error instanceof Error ? error.message : error}`,
      })
    } finally {
      setAssigningLineId(null)
    }
  }, [closeCandidates, loadDocumentDetail, loadStatements])

  const openReceiptPreview = React.useCallback((receiptId, extra = {}) => {
    if (!receiptId) return
    setPreviewReceipt({ id: receiptId, ...extra })
    setPreviewImage(null)
  }, [])

  const closeReceiptPreview = React.useCallback(() => {
    setPreviewReceipt(null)
    setPreviewImage(null)
  }, [])

  const handleReceiptUpdate = React.useCallback((updated) => {
    if (updated?.id && candidateState.line && updated.id === candidateState.line.matched_file_id) {
      loadDocumentDetail(selectedDocumentIdRef.current)
    } else {
      loadDocumentDetail(selectedDocumentIdRef.current)
    }
  }, [candidateState.line, loadDocumentDetail])

  const handleUploadComplete = React.useCallback(async ({ lastInvoiceId, successMessage } = {}) => {
    await loadStatements(lastInvoiceId)
    if (successMessage) {
      setDocumentFeedback({ type: 'success', text: successMessage })
    }
  }, [loadStatements])

  const handleSort = React.useCallback((column) => {
    if (sortColumn === column) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('asc')
    }
  }, [sortColumn])

  const sortedItems = React.useMemo(() => {
    if (!sortColumn) return items

    const sorted = [...items].sort((a, b) => {
      let aVal, bVal

      switch (sortColumn) {
        case 'card_name':
          aVal = (a.card_name || '').toLowerCase()
          bVal = (b.card_name || '').toLowerCase()
          break
        case 'invoice_date':
          aVal = a.invoice_date || ''
          bVal = b.invoice_date || ''
          break
        case 'due_date':
          aVal = a.due_date || ''
          bVal = b.due_date || ''
          break
        case 'amount_to_pay':
          aVal = Number(a.amount_to_pay) || 0
          bVal = Number(b.amount_to_pay) || 0
          break
        case 'status':
          aVal = (a.status || '').toLowerCase()
          bVal = (b.status || '').toLowerCase()
          break
        case 'overall_confidence':
          aVal = Number(a.overall_confidence) || 0
          bVal = Number(b.overall_confidence) || 0
          break
        case 'total_lines':
          aVal = Number(a.line_counts?.total) || 0
          bVal = Number(b.line_counts?.total) || 0
          break
        case 'matched_lines':
          aVal = Number(a.line_counts?.matched) || 0
          bVal = Number(b.line_counts?.matched) || 0
          break
        case 'unmatched_lines':
          aVal = Number(a.line_counts?.unmatched) || 0
          bVal = Number(b.line_counts?.unmatched) || 0
          break
        case 'updated_at':
          aVal = a.updated_at || a.uploaded_at || ''
          bVal = b.updated_at || b.uploaded_at || ''
          break
        default:
          return 0
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1
      return 0
    })

    return sorted
  }, [items, sortColumn, sortDirection])

  const detailSummaryCards = React.useMemo(() => {
    if (!selectedDocument) {
      return []
    }
    const summary = selectedDocument.invoice_summary ?? {}
    const details = selectedDocument.creditcard_details ?? {}
    const currency = summary.currency || 'SEK'
    const amountToPay = summary.amount_to_pay ?? summary.invoice_total
    const cardHolder = summary.card_holder || details.card_holder || 'Okänd'
    const cardType = summary.card_type || details.card_type
    const cardName = summary.card_name || details.card_name
    const cardNumberMasked = summary.card_number_masked || details.card_number_masked
    const cardDescriptor = [cardType, cardName].filter(Boolean).join(' - ') || cardNumberMasked || 'Okänt'
    const rows = [
      { label: 'Fakturanummer', value: summary.invoice_number || 'Okänt' },
      { label: 'Kortinnehavare', value: cardHolder },
      { label: 'Kort', value: cardDescriptor },
      {
        label: 'Belopp att betala',
        value: amountToPay != null ? formatCurrency(amountToPay, currency) : '-',
      },
      {
        label: 'AI-konfidens',
        value:
          selectedDocument.overall_confidence != null
            ? `${Math.round(Number(selectedDocument.overall_confidence) * 100)}%`
            : '–',
      },
    ]
    if (selectedDocument.creditcard_main_id) {
      rows.push({ label: 'Invoice-ID', value: selectedDocument.creditcard_main_id })
    }
    return rows
  }, [selectedDocument])

  const lineCounts = selectedDocument?.line_counts ?? {
    total: documentLines.length,
    matched: documentLines.filter((line) => line.match_status && line.match_status !== 'unmatched').length,
    unmatched: documentLines.filter((line) => !line.match_status || line.match_status === 'unmatched').length,
  }

  const receiptStats = systemSummary.receipts ?? INITIAL_SYSTEM_SUMMARY.receipts
  const purchaseStats = systemSummary.purchases ?? INITIAL_SYSTEM_SUMMARY.purchases
  const invoiceStats = systemSummary.invoices ?? INITIAL_SYSTEM_SUMMARY.invoices
  const totalInvoices = Number(invoiceStats.total) || 0
  const totalItems = Number(purchaseStats.total) || 0
  const matchedItems = Math.max(totalItems - (Number(purchaseStats.unmatched) || 0), 0)
  const matchedItemsPercent = totalItems ? Math.round((matchedItems / totalItems) * 100) : 0

  const handleSortLines = React.useCallback((column) => {
    if (sortLineColumn === column) {
      setSortLineDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortLineColumn(column)
      setSortLineDirection('asc')
    }
  }, [sortLineColumn])

  const sortedDocumentLines = React.useMemo(() => {
    if (!sortLineColumn) return documentLines

    const sorted = [...documentLines].sort((a, b) => {
      let aVal, bVal

      switch (sortLineColumn) {
        case 'transaction_date':
          aVal = a.transaction_date || ''
          bVal = b.transaction_date || ''
          break
        case 'description':
          aVal = (a.description || '').toLowerCase()
          bVal = (b.description || '').toLowerCase()
          break
        case 'amount_sek':
          aVal = Number(a.amount_sek ?? a.amount) || 0
          bVal = Number(b.amount_sek ?? b.amount) || 0
          break
        case 'currency':
          aVal = String(a.currency_original || a.currency || '').toLowerCase()
          bVal = String(b.currency_original || b.currency || '').toLowerCase()
          break
        case 'amount_original':
          aVal = Number(a.amount_original ?? a.amount) || 0
          bVal = Number(b.amount_original ?? b.amount) || 0
          break
        case 'match_status':
          aVal = (a.match_status || '').toLowerCase()
          bVal = (b.match_status || '').toLowerCase()
          break
        default:
          return 0
      }

      if (aVal < bVal) return sortLineDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return sortLineDirection === 'asc' ? 1 : -1
      return 0
    })

    return sorted
  }, [documentLines, sortLineColumn, sortLineDirection])

  const renderFeedback = () => {
    const feedback = candidateFeedback ?? documentFeedback
    if (!feedback) return null
    const tone = feedback.type === 'success' ? 'alert-success' : feedback.type === 'info' ? 'alert-info' : 'alert-error'
    return (
      <div className={`alert ${tone} mb-4`}>
        {feedback.text}
      </div>
    )
  }

  const renderLineTable = () => {
    if (!selectedDocumentId) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 py-12 text-gray-400">
          <FiFileText className="text-3xl" />
          <div>Välj ett kontoutdrag för att se dess transaktioner.</div>
        </div>
      )
    }

    if (detailLoading) {
      return (
        <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
          <div className="loading-spinner" />
          <span>Laddar detaljer...</span>
        </div>
      )
    }

    return (
      <div className="overflow-hidden border border-gray-700 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
            <tr>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('transaction_date')}
              >
                Datum {sortLineColumn === 'transaction_date' && (sortLineDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('description')}
              >
                Beskrivning {sortLineColumn === 'description' && (sortLineDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('amount_sek')}
              >
                SEK {sortLineColumn === 'amount_sek' && (sortLineDirection === 'asc' ? '\x1e' : '\x1f')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('currency')}
              >
                Valuta {sortLineColumn === 'currency' && (sortLineDirection === 'asc' ? '\x1e' : '\x1f')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('amount_original')}
              >
                Belopp {sortLineColumn === 'amount_original' && (sortLineDirection === 'asc' ? '\x1e' : '\x1f')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSortLines('match_status')}
              >
                Status {sortLineColumn === 'match_status' && (sortLineDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th className="px-4 py-3">Matchat kvitto</th>
              <th className="px-4 py-3 text-right">Åtgärder</th>
            </tr>
          </thead>
          <tbody>
            {sortedDocumentLines.length > 0 ? sortedDocumentLines.map((line) => {
              const statusDetails = describeLineStatus(line.match_status)
              const badgeClass = toneClass[statusDetails.tone] ?? 'status-processing'
              const matchedReceipt = line.matched_receipt
              const isAssigning = assigningLineId === line.id
              const lineCurrency = line.currency_original || line.currency
              const lineSek = line.amount_sek ?? line.amount
              const lineOriginal = line.amount_original ?? line.amount

              return (
                <tr key={line.id} className="border-t border-gray-700">
                  <td className="px-4 py-3 text-gray-200 whitespace-nowrap">{formatDate(line.transaction_date, false)}</td>
                  <td className="px-4 py-3 text-gray-100">
                    <div className="font-medium">{line.description || '–'}</div>
                    <div className="text-xs text-gray-400">Rad-ID: {line.id}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{lineSek != null ? formatCurrency(lineSek, 'SEK') : '-'}</td>
                  <td className="px-4 py-3 text-gray-200 whitespace-nowrap">{lineCurrency || '-'}</td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{lineOriginal != null && lineCurrency
                    ? formatCurrency(lineOriginal, lineCurrency)
                    : lineOriginal != null
                      ? formatCurrency(lineOriginal, 'SEK')
                      : '-'}</td>
                  <td className="px-4 py-3 text-gray-200">
                    <span className={`status-badge ${badgeClass}`}>{statusDetails.label}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-200">
                    {matchedReceipt ? (
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-gray-100">{matchedReceipt.vendor_name || 'Okänd leverantör'}</span>
                        <span className="text-xs text-gray-400">{formatDate(matchedReceipt.purchase_datetime, false)}  –  {formatAmount(matchedReceipt.gross_amount)}</span>
                        <button
                          type="button"
                          className="btn btn-text btn-xxs self-start"
                          onClick={() => openReceiptPreview(matchedReceipt.file_id, { credit_card_match: matchedReceipt.credit_card_match })}
                        >
                          Förhandsgranska
                        </button>
                      </div>
                    ) : (
                      <span className="text-xs text-gray-400">Ingen</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={(event) => {
                          event.stopPropagation()
                          onOpenCandidates(line)
                        }}
                      >
                        {candidateState.open && candidateState.line?.id === line.id ? 'Stäng kandidater' : 'Visa kandidater'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={isAssigning || !matchedReceipt}
                        onClick={(event) => {
                          event.stopPropagation()
                          if (matchedReceipt) {
                            openReceiptPreview(matchedReceipt.file_id, { credit_card_match: matchedReceipt.credit_card_match })
                          }
                        }}
                      >
                        Förhandsgranska
                      </button>
                    </div>
                  </td>
                </tr>
              )
            }) : (
              <tr className="border-t border-gray-700">
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">-</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    )
  }

  const renderItemTable = () => {
    if (detailLoading && !documentItems.length) {
      return (
        <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
          <div className="loading-spinner" />
          <span>Laddar transaktioner...</span>
        </div>
      )
    }

    const rows = documentItems.length ? documentItems : []

    return (
      <div className="overflow-hidden border border-gray-700 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
            <tr>
              <th className="px-4 py-3">Köpdatum</th>
              <th className="px-4 py-3">Butik</th>
              <th className="px-4 py-3">Stad</th>
              <th className="px-4 py-3">Belopp</th>
              <th className="px-4 py-3">Nettobelopp</th>
              <th className="px-4 py-3">Moms %</th>
              <th className="px-4 py-3">Valuta</th>
              <th className="px-4 py-3 text-center">Matchad</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? rows.map((item, index) => {
              const matched = Number(item.matched) === 1
              const currency = item.currency_original || 'SEK'
              const amountOriginal = item.amount_original != null ? formatCurrency(item.amount_original, currency) : '-'
              const netAmount = item.net_amount != null ? formatCurrency(item.net_amount, currency) : '-'
              const vatDisplay = item.vat_rate != null ? `${Number(item.vat_rate).toFixed(2)}%` : '-'
              return (
                <tr key={item.id ?? `item-${index}`} className="border-t border-gray-700">
                  <td className="px-4 py-3 text-gray-200 whitespace-nowrap">{formatDate(item.purchase_date, false)}</td>
                  <td className="px-4 py-3 text-gray-100">{item.merchant_name || '-'}</td>
                  <td className="px-4 py-3 text-gray-200">{item.merchant_city || '-'}</td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{amountOriginal}</td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{netAmount}</td>
                  <td className="px-4 py-3 text-gray-200">{vatDisplay}</td>
                  <td className="px-4 py-3 text-gray-200">{item.currency_original || currency}</td>
                  <td className="px-4 py-3 text-center">
                    {matched ? (
                      <FiCheckCircle className="inline text-green-400" aria-label="Matchad" />
                    ) : (
                      <FiX className="inline text-red-400" aria-label="Ej matchad" />
                    )}
                  </td>
                </tr>
              )
            }) : (
              <tr className="border-t border-gray-700">
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">-</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    )
  }

  const candidatesContent = candidateState.open && candidateState.line ? (
    <div className="modal-backdrop" onClick={closeCandidates}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3>Matchningskandidater</h3>
            <p className="text-sm text-gray-400 mt-1">
              Rad {candidateState.line.id}: {candidateState.line.description} - {candidateState.line?.amount_sek != null
                ? formatCurrency(candidateState.line.amount_sek, 'SEK')
                : candidateState.line?.amount != null
                  ? formatCurrency(candidateState.line.amount, 'SEK')
                  : '-'}
            </p>
          </div>
          <button type="button" className="icon-button" onClick={closeCandidates} aria-label="Stäng">
            <FiX />
          </button>
        </div>
        <div className="modal-body">
          {candidateFeedback && (
            <div className={`alert ${candidateFeedback.type === 'success' ? 'alert-success' : 'alert-error'} mb-4`}>
              {candidateFeedback.text}
            </div>
          )}
          {candidateState.loading ? (
            <div className="flex items-center justify-center gap-3 py-8">
              <div className="loading-spinner" />
              <span>Laddar kandidater...</span>
            </div>
          ) : candidateState.candidates.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <FiFileText className="text-3xl mx-auto mb-2" />
              <p>Inga matchningskandidater hittades för denna rad.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {candidateState.candidates.map((candidate) => (
                <div key={candidate.file_id} className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="font-medium text-gray-100">{candidate.vendor_name || 'Okänd leverantör'}</div>
                      <div className="text-sm text-gray-400 space-y-1">
                        <div>Datum: {formatDate(candidate.purchase_datetime, false)}</div>
                        <div>Belopp: {formatAmount(candidate.gross_amount)}</div>
                        {candidate.match_score != null && (
                          <div>Match-poäng: {Math.round(candidate.match_score * 100)}%</div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="btn btn-text btn-sm"
                        onClick={() => openReceiptPreview(candidate.file_id)}
                      >
                        <FiEye className="mr-1" />
                        Visa
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() => assignCandidate(candidateState.line.id, candidate.file_id)}
                        disabled={assigningLineId === candidateState.line.id}
                      >
                        {assigningLineId === candidateState.line.id ? (
                          <>
                            <div className="loading-spinner mr-1" />
                            Matchar...
                          </>
                        ) : (
                          <>
                            <FiLink className="mr-1" />
                            Matcha
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={closeCandidates}>
            Stäng
          </button>
        </div>
      </div>
    </div>
  ) : null

  const renderLogModal = () => {
    if (!logState.open) {
      return null
    }

    const logData = logState.data ?? {}
    const workflowRuns = Array.isArray(logData?.workflow_runs) ? logData.workflow_runs : []
    const aiHistory = Array.isArray(logData?.ai_history) ? logData.ai_history : []
    const files = Array.isArray(logData?.files) ? logData.files : []
    const metadataPayload = logData?.metadata && typeof logData.metadata === 'object' ? logData.metadata : {}
    const invoiceIdForModal = logData?.invoice_id || logState.invoiceId

    const handleBackdrop = (event) => {
      if (event.target === event.currentTarget) {
        closeLogViewer()
      }
    }

    return (
      <div className="modal-backdrop" role="dialog" aria-label="Importlogg" onClick={handleBackdrop}>
        <div
          className="modal"
          onClick={(event) => event.stopPropagation()}
          style={{ maxWidth: '960px' }}
        >
          <div className="modal-header">
            <div>
              <h3>Importlogg</h3>
              <p className="text-xs text-gray-400 mt-1">
                Kontoutdrag: {invoiceIdForModal || 'okänd'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => handleClearInvoiceLog(invoiceIdForModal)}
                disabled={!invoiceIdForModal || logState.loading || logActionState.clearing}
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
                    <p className="text-xs text-gray-400 mt-2">Inga workflow-loggar hittades för detta utdrag.</p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {workflowRuns.map((run) => (
                        <div key={run.id} className="bg-gray-900 border border-gray-700 rounded-lg p-4 space-y-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-gray-100">
                                {run.workflow_key}  –  {run.status}
                              </div>
                              <div className="text-xs text-gray-400">
                                Run-ID: {run.id}  –  Source: {run.source_channel || 'okänd'}
                              </div>
                            </div>
                            <div className="text-xs text-gray-400 text-right">
                              <div>Start: {formatDate(run.created_at)}</div>
                              <div>Senast: {formatDate(run.updated_at)}</div>
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
                                  <span>{formatStageLabel(stage.stage_key)}</span>
                                    <span>{stage.status}</span>
                                  </div>
                                  <div className="flex flex-wrap items-center justify-between text-xs text-gray-400">
                                    <span>
                                      {formatDate(stage.started_at)}{stage.finished_at ? ` → ${formatDate(stage.finished_at)}` : ''}
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
                      Ingen AI-historik registrerad för detta utdrag eller dess sidor.
                    </p>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {aiHistory.map((entry) => (
                        <div key={entry.id} className="bg-gray-900 border border-gray-700 rounded-lg p-3 space-y-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <div className="text-sm font-semibold text-gray-100">
                                {(entry.ai_stage_name || entry.job_type || 'Okänt steg')}  –  {entry.status}
                              </div>
                              <div className="text-xs text-gray-400">
                                Fil: {entry.file_id}  –  {formatDate(entry.created_at)}
                              </div>
                            </div>
                            <div className="text-xs text-gray-400 text-right space-y-1">
                              {(entry.provider || entry.model) && (
                                <div>
                                  {entry.provider || 'okänd'}{entry.model ? `  –  ${entry.model}` : ''}
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
                              Skapad: {formatDate(file.created_at)}
                              {file.updated_at ? `  –  Uppdaterad: ${formatDate(file.updated_at)}` : ''}
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

                <section>
                  <h4 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
                    Metadata (invoice_documents)
                  </h4>
                  {metadataPayload && Object.keys(metadataPayload).length > 0 ? (
                    <div className="mt-3 bg-gray-900 border border-gray-700 rounded-lg p-3">
                      <pre className="text-xs text-gray-200 whitespace-pre-wrap font-mono overflow-x-auto">
                        {JSON.stringify(metadataPayload, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 mt-2">
                      Ingen metadata sparad för detta utdrag.
                    </p>
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
              onClick={() => logState.invoiceId && fetchInvoiceLog(logState.invoiceId)}
              disabled={logState.loading || !logState.invoiceId}
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


const renderStatementTable = () => {
    if (!items.length) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 py-10 text-gray-300">
          <FiFileText className="text-3xl" />
          <div>Inga kontoutdrag hittades.</div>
        </div>
      )
    }

    const rows = sortedItems.map((statement) => {
      const statusDetails = describeFirstCardStatus(statement)
      const badgeClass = toneClass[statusDetails.tone] ?? 'status-processing'
      const lineSummary = statement.line_counts ?? {}
      const isSelected = statement.id === selectedDocumentId
      const cardLabel = statement.card_name || `Utdrag ${statement.id}`
      const invoiceNumber = statement.invoice_summary?.invoice_number || statement.invoice_number || statement.id
      const periodRange = statement.period_start && statement.period_end
        ? `${formatDate(statement.period_start, false)} - ${formatDate(statement.period_end, false)}`
        : null
      const processingDetails = describeProcessingStatus(statement.processing_status || statement.status)
      const updatedAt = statement.updated_at || statement.uploaded_at
      const confidence = typeof statement.overall_confidence === 'number'
        ? `${Math.round(Number(statement.overall_confidence) * 100)}%`
        : '-'
      const invoiceDateLabel = statement.invoice_date ? formatDate(statement.invoice_date, false) : '-'
      const dueDateLabel = statement.due_date ? formatDate(statement.due_date, false) : '-'
      const amountToPayLabel = statement.amount_to_pay ? formatAmount(statement.amount_to_pay) : '-'

      return {
        statement,
        statusDetails,
        badgeClass,
        lineSummary,
        isSelected,
        cardLabel,
        invoiceNumber,
        periodRange,
        processingDetails,
        updatedAt,
        confidence,
        invoiceDateLabel,
        dueDateLabel,
        amountToPayLabel,
      }
    })

    return (
      <div className="overflow-hidden border border-gray-700 rounded-lg">
        <table className="min-w-full divide-y divide-gray-700 text-sm">
          <thead className="bg-gray-900/60 text-gray-300 uppercase tracking-wide text-xs">
            <tr>
              <th
                className="px-4 py-3 text-left cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('card_name')}
              >
                Kort {sortColumn === 'card_name' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('invoice_date')}
              >
                Fakturadatum {sortColumn === 'invoice_date' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('due_date')}
              >
                Betalningsdatum {sortColumn === 'due_date' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('amount_to_pay')}
              >
                Belopp {sortColumn === 'amount_to_pay' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('status')}
              >
                Status {sortColumn === 'status' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('overall_confidence')}
              >
                AI - Konfidens {sortColumn === 'overall_confidence' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('total_lines')}
              >
                RADER {sortColumn === 'total_lines' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('matched_lines')}
              >
                Matchade rader {sortColumn === 'matched_lines' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('unmatched_lines')}
              >
                Omatchade rader {sortColumn === 'unmatched_lines' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th
                className="px-4 py-3 text-center cursor-pointer hover:bg-gray-800/40 select-none"
                onClick={() => handleSort('updated_at')}
              >
                Senast uppdaterad {sortColumn === 'updated_at' && (sortDirection === 'asc' ? '▲' : '▼')}
              </th>
              <th className="px-4 py-3 text-center">Logg</th>
              <th className="px-4 py-3 text-center">Matcha omatchade rader</th>
              <th className="px-4 py-3 text-center">Återuppta fakturaimport</th>
              <th className="px-3 py-3 text-right">Ta bort</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {rows.map(({ statement, statusDetails, badgeClass, lineSummary, isSelected, cardLabel, invoiceNumber, periodRange, updatedAt, confidence, invoiceDateLabel, dueDateLabel, amountToPayLabel }) => {
              const rowClasses = isSelected ? 'bg-red-600/10 hover:bg-red-600/20' : 'hover:bg-gray-800/40'
              const hasUnmatchedRows = (lineSummary.unmatched ?? 0) > 0

              return (
                <tr
                  key={statement.id}
                  onClick={() => setSelectedDocumentId(statement.id)}
                  className={`cursor-pointer transition-colors ${rowClasses}`}
                >
                  <td className="px-4 py-3 text-sm font-medium text-gray-100">
                    <div className="flex items-center gap-2">
                      <FiChevronRight className={`transition-transform ${isSelected ? 'rotate-90 text-red-400' : 'text-gray-500'}`} />
                      {cardLabel}
                    </div>
                    <div className="mt-1 text-xs text-gray-400">Fakturanummer: {invoiceNumber}</div>
                    {periodRange && <div className="text-xs text-gray-400">Period: {periodRange}</div>}
                    <div className="mt-1 text-xs text-gray-400">
                      Uppladdad {formatDate(statement.created_at || statement.uploaded_at)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-200 text-center">{invoiceDateLabel}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{dueDateLabel}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{amountToPayLabel}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`status-badge ${badgeClass}`}>{statusDetails.label}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-200 text-center">{confidence}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{lineSummary.total ?? '–'}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{lineSummary.matched ?? '–'}</td>
                  <td className="px-4 py-3 text-gray-200 text-center">{lineSummary.unmatched ?? '–'}</td>
                  <td className="px-4 py-3 text-gray-200 text-center whitespace-nowrap">
                    {formatDate(updatedAt)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={(event) => {
                        event.stopPropagation()
                        setSelectedDocumentId(statement.id)
                        fetchInvoiceLog(statement.id)
                      }}
                    >
                      Visa logg
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm ml-2"
                      onMouseDown={(event) => {
                        event.stopPropagation()
                        setPreviewInvoiceId(statement.id)
                        setPreviewOpen(true)
                      }}
                      onClick={(event) => {
                        event.stopPropagation()
                        setPreviewInvoiceId(statement.id)
                        setPreviewOpen(true)
                      }}
                    >
                      <FiEye className="mr-1" />
                      Förhandsgranska
                    </button>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {hasUnmatchedRows && (
                      <button
                        type="button"
                        className="btn btn-sm"
                        style={{
                          backgroundColor: '#dc2626',
                          color: 'white',
                          border: 'none',
                        }}
                        onClick={(event) => {
                          event.stopPropagation()
                          onMatchDocument(statement.id)
                        }}
                        disabled={matchingDocumentId === statement.id}
                      >
                        {matchingDocumentId === statement.id ? (
                          <>
                            <div className="loading-spinner mr-1" />
                            Matchar...
                          </>
                        ) : (
                          <>
                            <FiLink className="mr-1" />
                            Matcha omatchade rader
                          </>
                        )}
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={(event) => {
                        event.stopPropagation()
                        handleResumeOrRestartInvoice(statement.id, statement.processing_status)
                      }}
                      disabled={resumingDocumentId === statement.id}
                    >
                      {resumingDocumentId === statement.id ? (
                        <>
                          <div className="loading-spinner mr-1" />
                          Bearbetar...
                        </>
                      ) : (
                        <>
                          <FiRefreshCw className="mr-1" />
                          Återuppta fakturaimport
                        </>
                      )}
                    </button>
                  </td>
                  <td className="px-3 py-3 text-right">
                    <button
                      type="button"
                      className={`icon-button ${deletingDocumentId === statement.id ? 'opacity-60 cursor-wait' : 'text-gray-500 hover:text-red-400'}`}
                      onClick={(event) => {
                        event.stopPropagation()
                        handleDeleteStatement(statement.id)
                      }}
                      disabled={deletingDocumentId === statement.id}
                      aria-label="Ta bort utdrag"
                    >
                      {deletingDocumentId === statement.id ? <div className="loading-spinner w-4 h-4" /> : <FiTrash2 />}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div className="stat-card blue">
          <div className="flex items-center justify-between mb-2">
            <FiCheckCircle className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{formatNumber(totalInvoices)}</div>
              </div>
            )}
          </div>
          <div className="stat-label">Inlästa utdrag</div>
          <div className="stat-subtitle">Totalt antal importerade fakturor</div>
        </div>

        <div className="stat-card green">
          <div className="flex items-center justify-between mb-2">
            <FiFileText className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{formatNumber(totalItems)}</div>
              </div>
            )}
          </div>
          <div className="stat-label">Totalt fakturaposter</div>
          <div className="stat-subtitle">Antal rader (items) i alla utdrag</div>
        </div>

        <div className="stat-card blue">
          <div className="flex items-center justify-between mb-2">
            <FiLink className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{formatNumber(matchedItems)}</div>
              </div>
            )}
          </div>
          <div className="stat-label">Matchade kvitton</div>
          <div className="stat-subtitle">Antal rader som fått kvitto-match</div>
        </div>

        <div className="stat-card yellow">
          <div className="flex items-center justify-between mb-2">
            <FiPercent className="text-2xl opacity-80" />
            {systemSummaryLoading ? (
              <div className="loading-spinner" />
            ) : (
              <div className="text-right">
                <div className="stat-number">{`${matchedItemsPercent}%`}</div>
                <div className="text-xs text-gray-400">av {formatNumber(totalItems)} rader</div>
              </div>
            )}
          </div>
          <div className="stat-label">Matchningsgrad</div>
          <div className="stat-subtitle">Andel item-rader som är matchade</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="card-title">Kontoutdrag</h3>
            <p className="card-subtitle">Överblick över importerade kontoutdrag.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => loadStatements(selectedDocumentIdRef.current)}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Uppdaterar...
                </>
              ) : (
                <>
                  <FiRefreshCw className="mr-2" />
                  Uppdatera
                </>
              )}
            </button>
            <button
              type="button"
              className="btn btn-sm"
              style={{
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
              }}
              onClick={handleMatchAllUnmatched}
              disabled={matchingAllUnmatched || loading}
            >
              {matchingAllUnmatched ? (
                <>
                  <div className="loading-spinner mr-2" />
                  Matchar...
                </>
              ) : (
                <>
                  <FiLink className="mr-2" />
                  Matcha omatchade poster
                </>
              )}
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setUploadModalOpen(true)}
            >
              <FiUpload className="mr-2" />
              Ladda upp utdrag
            </button>
          </div>
        </div>
        <div className="px-6 pb-6 space-y-4">
          {renderFeedback()}
          {loading ? (
            <div className="flex items-center justify-center gap-3 py-10 text-gray-400">
              <div className="loading-spinner" />
              <span>Laddar kontoutdrag...</span>
            </div>
          ) : (
            renderStatementTable()
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header flex-wrap gap-3">
          <div>
            <h3 className="card-title">Utdragsdetaljer</h3>
            {selectedDocument ? (
              <p className="card-subtitle">
                {selectedDocument.period_start && selectedDocument.period_end
                  ? `Period: ${formatDate(selectedDocument.period_start, false)} – ${formatDate(selectedDocument.period_end, false)}`
                  : 'Välj ett kontoutdrag för att se detaljer.'}
              </p>
            ) : (
              <p className="card-subtitle">Välj ett kontoutdrag för att se detaljer.</p>
            )}
          </div>
        </div>
        <div className="px-6 pb-6 space-y-6">
          {selectedDocument && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">Status</div>
                  <div className="mt-2 flex items-center gap-2">
                    <span className={`status-badge ${toneClass[describeFirstCardStatus(selectedDocument).tone] || 'status-processing'}`}>
                      {describeFirstCardStatus(selectedDocument).label}
                    </span>
                  </div>
                </div>
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">Linjer</div>
                  <div className="mt-2 text-gray-100 text-lg font-semibold">{lineCounts.total}</div>
                  <div className="text-xs text-gray-400 mt-1">Matchade: {lineCounts.matched}  –  Obearbetade: {lineCounts.unmatched}</div>
                </div>
                <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">Senast uppdaterad</div>
                  <div className="mt-2 text-gray-100 text-lg font-semibold">
                    {formatDate(selectedDocument.updated_at || selectedDocument.uploaded_at)}
                  </div>
                </div>
              </div>
              {detailSummaryCards.length > 0 && (
                <dl className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                  {detailSummaryCards.map((item) => (
                    <div key={item.label} className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3">
                      <dt className="text-xs uppercase tracking-wide text-gray-400">{item.label}</dt>
                      <dd className="text-sm font-semibold text-white mt-1 break-words">{item.value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </>
          )}

          {renderItemTable()}
          {renderLineTable()}
        </div>
      </div>

      {candidatesContent}
      {renderLogModal()}

      <DocumentPreviewModal
        open={previewOpen}
        documentId={previewInvoiceId}
        onClose={() => setPreviewOpen(false)}
      />

      <InvoiceUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploaded={handleUploadComplete}
      />

      <ReceiptPreviewModal
        open={Boolean(previewReceipt)}
        receipt={previewReceipt}
        previewImage={previewImage}
        onClose={closeReceiptPreview}
        onReceiptUpdate={handleReceiptUpdate}
      />
    </div>
  )
}


function InvoiceUploadModal({ open, onClose, onUploaded }) {
  const fileInputRef = React.useRef(null)
  const [selectedFiles, setSelectedFiles] = React.useState([])
  const [uploading, setUploading] = React.useState(false)
  const [feedback, setFeedback] = React.useState(null)

  React.useEffect(() => {
    if (!open) {
      setSelectedFiles([])
      setFeedback(null)
      setUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }, [open])

  if (!open) {
    return null
  }

  const handleBackdropClick = (event) => {
    if (event.target === event.currentTarget && !uploading && typeof onClose === 'function') {
      onClose()
    }
  }

  const handleFileSelect = (event) => {
    const files = Array.from(event.target.files ?? [])
    setSelectedFiles(files)
    setFeedback(null)
  }

  const handleUpload = async () => {
    if (!selectedFiles.length || uploading) {
      return
    }

    setUploading(true)
    setFeedback(null)

    const successes = []
    const failures = []

    for (const file of selectedFiles) {
      const formData = new FormData()
      formData.append('invoice', file)
      try {
        const response = await api.fetch('/ai/api/reconciliation/firstcard/upload-invoice', {
          method: 'POST',
          body: formData,
        })

        if (response.status === 201) {
          const data = await response.json().catch(() => null)
          successes.push({ file, invoiceId: data?.invoice_id ?? null })
        } else {
          const payload = await response.json().catch(() => null)
          failures.push({
            file,
            message: buildUploadErrorMessage(response.status, payload),
          })
        }
      } catch (error) {
        const message = error instanceof Error ? `Nätverksfel: ${error.message}` : 'Nätverksfel.'
        failures.push({ file, message })
      }
    }

    if (successes.length && typeof onUploaded === 'function') {
      const lastInvoiceId = successes[successes.length - 1]?.invoiceId ?? null
      const successSummary = `Uppladdning klar: ${successes.length} fil${successes.length === 1 ? '' : 'er'} skickades för bearbetning.`
      await onUploaded({
        lastInvoiceId,
        successMessage: failures.length ? null : successSummary,
      })
      if (!failures.length) {
        setFeedback({ type: 'success', text: successSummary })
      }
    }

    if (failures.length) {
      const detail = failures
        .map(({ file, message }) => `${file.name} (${message})`)
        .join('; ')
      const prefix = successes.length
        ? `Vissa filer laddades upp, men ${failures.length} misslyckades`
        : `Kunde inte ladda upp ${failures.length} fil${failures.length === 1 ? '' : 'er'}`
      setFeedback({
        type: 'error',
        text: `${prefix}: ${detail}.`,
      })
      setSelectedFiles(failures.map(({ file }) => file))
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } else if (successes.length) {
      setSelectedFiles([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      setTimeout(() => {
        setFeedback(null)
        if (typeof onClose === 'function') {
          onClose()
        }
      }, 1200)
    }

    setUploading(false)
  }

  const selectedSummary = selectedFiles.length
    ? `${selectedFiles.length} fil${selectedFiles.length === 1 ? ' vald' : 'er valda'}`
    : null

  const feedbackTone = feedback?.type === 'success'
    ? 'alert-success'
    : feedback?.type === 'error'
      ? 'alert-error'
      : 'alert-info'

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-label="Ladda upp kontoutdrag"
      onClick={handleBackdropClick}
    >
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Ladda upp kontoutdrag</h3>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Stäng"
            disabled={uploading}
          >
            <FiX />
          </button>
        </div>

        <div className="modal-body space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Välj filer att ladda upp</label>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,.pdf"
              className="dm-input w-full"
              disabled={uploading}
              onChange={handleFileSelect}
            />
            {selectedFiles.length > 0 && (
              <ul className="mt-2 text-sm text-gray-300 space-y-1 list-disc list-inside">
                {selectedFiles.map((file) => (
                  <li key={`${file.name}-${file.size}`}>{file.name}</li>
                ))}
              </ul>
            )}
            {selectedSummary && (
              <div className="mt-2 text-xs text-gray-400">{selectedSummary}</div>
            )}
            <p className="mt-2 text-xs text-gray-500">
              Filerna skickas till OCR och matchning direkt efter uppladdning.
            </p>
          </div>

          {feedback && (
            <div className={`alert ${feedbackTone}`}>
              {feedback.type === 'success' ? (
                <FiCheckCircle className="mr-2" />
              ) : (
                <FiAlertCircle className="mr-2" />
              )}
              <span>{feedback.text}</span>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-text" onClick={onClose} disabled={uploading}>
            Avbryt
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={uploading || selectedFiles.length === 0}
          >
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
