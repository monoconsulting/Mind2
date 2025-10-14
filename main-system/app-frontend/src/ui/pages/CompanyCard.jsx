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
} from 'react-icons/fi'
import ReceiptPreviewModal from '../components/ReceiptPreviewModal'
import { api } from '../api'

const DOCUMENT_STATUS_MAP = [
  { ids: ['matched', 'matchad', 'completed', 'done', 'success'], label: 'Matchat', tone: 'success' },
  { ids: ['processing', 'matching', 'running', 'ready_for_matching'], label: 'Bearbetas', tone: 'processing' },
  { ids: ['queued', 'pending', 'created', 'uploaded', 'imported'], label: 'I kö', tone: 'pending' },
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

const toneClass = {
  success: 'status-passed',
  processing: 'status-processing',
  pending: 'status-pending',
  failed: 'status-failed',
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

const currencyFormatter = new Intl.NumberFormat('sv-SE', {
  style: 'currency',
  currency: 'SEK',
  minimumFractionDigits: 2,
})

function formatAmount(value) {
  if (value === null || value === undefined) {
    return '–'
  }
  const num = Number(value)
  if (!Number.isFinite(num)) {
    return String(value)
  }
  return currencyFormatter.format(num)
}

const initialCandidatesState = {
  open: false,
  line: null,
  candidates: [],
  loading: false,
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
  const selectedDocumentIdRef = React.useRef(null)
  const [selectedDocument, setSelectedDocument] = React.useState(null)
  const [documentLines, setDocumentLines] = React.useState([])
  const [detailLoading, setDetailLoading] = React.useState(false)

  const [candidateState, setCandidateState] = React.useState(initialCandidatesState)
  const [assigningLineId, setAssigningLineId] = React.useState(null)
  const [candidateFeedback, setCandidateFeedback] = React.useState(null)

  const [previewReceipt, setPreviewReceipt] = React.useState(null)
  const [previewImage, setPreviewImage] = React.useState(null)
  const [uploadModalOpen, setUploadModalOpen] = React.useState(false)

  React.useEffect(() => {
    selectedDocumentIdRef.current = selectedDocumentId
  }, [selectedDocumentId])

  const loadStatements = React.useCallback(async (preferredId = selectedDocumentIdRef.current) => {
    setLoading(true)
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const data = await res.json()
      const nextItems = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
      setItems(nextItems)
      if (!nextItems.length) {
        setSelectedDocumentId(null)
        setSelectedDocument(null)
        setDocumentLines([])
        setDocumentFeedback({
          type: 'info',
          text: 'Inga kontoutdrag hittades. Ladda upp ett utdrag för att börja matcha kvitton.',
        })
      } else {
        const targetId = preferredId && nextItems.some((item) => item.id === preferredId)
          ? preferredId
          : nextItems[0].id
        setSelectedDocumentId(targetId)
        setDocumentFeedback(null)
      }
    } catch (error) {
      console.error('Failed to load statements', error)
      setItems([])
      setSelectedDocumentId(null)
      setSelectedDocument(null)
      setDocumentLines([])
      setDocumentFeedback({
        type: 'error',
        text: `Fel vid hämtning av kontoutdrag: ${error instanceof Error ? error.message : error}`,
      })
    } finally {
      setLoading(false)
    }
  }, [])

  const loadDocumentDetail = React.useCallback(async (invoiceId) => {
    if (!invoiceId) {
      setSelectedDocument(null)
      setDocumentLines([])
      return
    }
    setDetailLoading(true)
    try {
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${invoiceId}`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const data = await res.json()
      const invoice = data?.invoice ?? null
      const lines = Array.isArray(data?.lines) ? data.lines : []
      setSelectedDocument(invoice)
      setDocumentLines(lines)
    } catch (error) {
      console.error('Failed to load invoice detail', error)
      setSelectedDocument(null)
      setDocumentLines([])
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
  }, [loadStatements])

  React.useEffect(() => {
    if (selectedDocumentId) {
      loadDocumentDetail(selectedDocumentId)
    }
  }, [selectedDocumentId, loadDocumentDetail])

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

  const summary = React.useMemo(() => {
    const base = { matched: 0, pending: 0, failed: 0 }
    for (const item of items) {
      const status = normalizeStatus(item?.status)
      if (['matched', 'matchad', 'completed', 'done', 'success'].includes(status)) {
        base.matched += 1
      } else if (['failed', 'error'].includes(status)) {
        base.failed += 1
      } else {
        base.pending += 1
      }
    }
    return { ...base, total: items.length }
  }, [items])

  const lineCounts = selectedDocument?.line_counts ?? {
    total: documentLines.length,
    matched: documentLines.filter((line) => line.match_status && line.match_status !== 'unmatched').length,
    unmatched: documentLines.filter((line) => !line.match_status || line.match_status === 'unmatched').length,
  }

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

  const renderStatementList = () => (
    <div className="space-y-3">
      {items.map((statement) => {
        const statusDetails = describeDocumentStatus(statement.status)
        const badgeClass = toneClass[statusDetails.tone] ?? 'status-processing'
        const lineSummary = statement.line_counts ?? {}
        const isSelected = statement.id === selectedDocumentId
        return (
          <button
            type="button"
            key={statement.id}
            onClick={() => setSelectedDocumentId(statement.id)}
            className={`w-full text-left rounded-lg border transition-all duration-150 ${
              isSelected ? 'border-red-500 bg-red-600 bg-opacity-10 shadow-lg' : 'border-gray-700 bg-gray-900 hover:border-red-500'
            }`}
          >
            <div className="p-4 flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-gray-100">
                  <FiChevronRight className={`transition-transform ${isSelected ? 'rotate-90 text-red-400' : 'text-gray-500'}`} />
                  {statement.period_start && statement.period_end
                    ? `${formatDate(statement.period_start, false)} – ${formatDate(statement.period_end, false)}`
                    : `Utdrag ${statement.id}`}
                </div>
                <div className="mt-2 text-xs text-gray-400">
                  Uppladdad {formatDate(statement.created_at || statement.uploaded_at)}
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-gray-400 uppercase tracking-wide">
                  <span>Total: {lineSummary.total ?? '–'}</span>
                  <span>Matchade: {lineSummary.matched ?? '–'}</span>
                  <span>Obearbetade: {lineSummary.unmatched ?? '–'}</span>
                </div>
              </div>
              <span className={`status-badge ${badgeClass}`}>
                {statusDetails.label}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )

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
          <div className="loading-spinner"></div>
          <span>Laddar detaljer...</span>
        </div>
      )
    }

    if (!documentLines.length) {
      return (
        <div className="flex flex-col items-center justify-center gap-2 py-12 text-gray-400">
          <FiFileText className="text-3xl" />
          <div>Inga rader hittades i detta utdrag.</div>
        </div>
      )
    }

    return (
      <div className="overflow-hidden border border-gray-700 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
            <tr>
              <th className="px-4 py-3">Datum</th>
              <th className="px-4 py-3">Beskrivning</th>
              <th className="px-4 py-3">Belopp</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Matchat kvitto</th>
              <th className="px-4 py-3 text-right">Åtgärder</th>
            </tr>
          </thead>
          <tbody>
            {documentLines.map((line) => {
              const statusDetails = describeLineStatus(line.match_status)
              const badgeClass = toneClass[statusDetails.tone] ?? 'status-processing'
              const matchedReceipt = line.matched_receipt
              return (
                <tr key={line.id} className="border-t border-gray-700">
                  <td className="px-4 py-3 text-gray-200 whitespace-nowrap">{formatDate(line.transaction_date, false)}</td>
                  <td className="px-4 py-3 text-gray-200">
                    <div className="font-medium text-gray-100">{line.description || '—'}</div>
                    <div className="text-xs text-gray-400">Rad-ID: {line.id}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-100 whitespace-nowrap">{formatAmount(line.amount)}</td>
                  <td className="px-4 py-3 text-gray-200">
                    <span className={`status-badge ${badgeClass}`}>
                      {statusDetails.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-200">
                    {matchedReceipt ? (
                      <div className="flex flex-col gap-1">
                        <span className="font-medium text-gray-100">{matchedReceipt.vendor_name || 'Okänd leverantör'}</span>
                        <span className="text-xs text-gray-400">{formatAmount(matchedReceipt.gross_amount)}</span>
                      </div>
                    ) : (
                      <span className="text-sm text-gray-500">Ej matchat</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {matchedReceipt && (
                        <button
                          type="button"
                          className="btn btn-secondary btn-xs"
                          onClick={() => openReceiptPreview(matchedReceipt.file_id, { credit_card_match: matchedReceipt.credit_card_match })}
                        >
                          <FiEye className="mr-2" />
                          Visa kvitto
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn btn-primary btn-xs"
                        onClick={() => onOpenCandidates(line)}
                      >
                        <FiLink className="mr-2" />
                        Visa kandidater
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    )
  }

  const candidatesContent = candidateState.open && (
    <div className="fixed inset-0 z-40 flex">
      <div
        className="flex-1 bg-black bg-opacity-50"
        onClick={candidateState.loading ? undefined : closeCandidates}
      />
      <div className="w-full sm:w-[420px] h-full bg-gray-900 border-l border-gray-700 shadow-2xl overflow-y-auto">
        <div className="flex items-start justify-between p-5 border-b border-gray-800">
          <div>
            <div className="text-lg font-semibold text-white">Kandidater</div>
            {candidateState.line && (
              <div className="text-xs text-gray-400 mt-1">
                Rad {candidateState.line.id} &middot; {formatAmount(candidateState.line.amount)} &middot; {candidateState.line.description}
              </div>
            )}
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-xs text-gray-400 hover:text-white"
            onClick={closeCandidates}
          >
            <FiX className="text-lg" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {candidateState.loading ? (
            <div className="flex items-center justify-center gap-3 py-10 text-gray-400">
              <div className="loading-spinner"></div>
              <span>Söker efter kandidater...</span>
            </div>
          ) : candidateState.candidates.length === 0 ? (
            <div className="text-sm text-gray-400">
              Inga kandidater hittades ännu. Kontrollera att kvittot är registrerat eller försök igen efter matchning.
            </div>
          ) : (
            <div className="space-y-3">
              {candidateState.candidates.map((candidate) => {
                const isCurrentMatch = candidate.is_current_match
                return (
                  <div
                    key={candidate.file_id}
                    className={`rounded-lg border p-4 transition-all ${
                      isCurrentMatch ? 'border-green-500 bg-green-600 bg-opacity-5' : 'border-gray-700 bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-sm font-semibold text-gray-100">
                          {candidate.vendor_name || 'Okänd leverantör'}
                        </div>
                        <div className="text-xs text-gray-400 mt-1">
                          {formatDate(candidate.purchase_datetime)} &middot; {formatAmount(candidate.gross_amount)}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          Beloppsdiff: {candidate.amount_difference != null ? formatAmount(candidate.amount_difference) : '–'} &middot; Datumsdiff: {candidate.date_difference_days ?? '–'} dagar
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <button
                          type="button"
                          className="btn btn-secondary btn-xxs"
                          onClick={() => openReceiptPreview(candidate.file_id, { credit_card_match: candidate.credit_card_match })}
                        >
                          <FiEye className="mr-1" />
                          Visa
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary btn-xxs"
                          disabled={assigningLineId === candidateState.line?.id || isCurrentMatch}
                          onClick={() => assignCandidate(candidateState.line?.id, candidate.file_id)}
                        >
                          {assigningLineId === candidateState.line?.id ? (
                            <>
                              <div className="loading-spinner mr-1"></div>
                              Matchar...
                            </>
                          ) : isCurrentMatch ? (
                            'Redan matchad'
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
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="stat-card green">
          <div className="flex items-center justify-between mb-2">
            <FiCheckCircle className="text-2xl opacity-80" />
            <div className="stat-number">{summary.matched}</div>
          </div>
          <div className="stat-label">Matchade utdrag</div>
          <div className="stat-subtitle">Utdrag som är helt matchade</div>
        </div>

        <div className="stat-card blue">
          <div className="flex items-center justify-between mb-2">
            <FiRefreshCw className="text-2xl opacity-80" />
            <div className="stat-number">{summary.pending}</div>
          </div>
          <div className="stat-label">Pågående matchningar</div>
          <div className="stat-subtitle">Utdrag som bearbetas</div>
        </div>

        <div className="stat-card yellow">
          <div className="flex items-center justify-between mb-2">
            <FiAlertTriangle className="text-2xl opacity-80" />
            <div className="stat-number">{summary.failed}</div>
          </div>
          <div className="stat-label">Kräver åtgärd</div>
          <div className="stat-subtitle">Kontrollera status eller kör om matchning</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px,1fr] gap-6">
        <aside className="space-y-4">
          <div className="card">
            <div className="card-header">
              <div>
                <h3 className="card-title">Kontoutdrag</h3>
                <p className="card-subtitle">Välj ett utdrag för att se detaljerad information.</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => loadStatements()}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <div className="loading-spinner mr-2"></div>
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
                  className="btn btn-primary btn-sm"
                  onClick={() => setUploadModalOpen(true)}
                >
                  <FiUpload className="mr-2" />
                  Ladda upp utdrag
                </button>
              </div>
            </div>
            {renderFeedback()}
            {loading ? (
              <div className="flex items-center justify-center gap-3 py-8 text-gray-400">
                <div className="loading-spinner"></div>
                <span>Laddar kontoutdrag...</span>
              </div>
            ) : items.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 py-10 text-gray-300">
                <FiFileText className="text-3xl" />
                <div className="text-base font-medium">Inga kontoutdrag hittades</div>
              </div>
            ) : (
              renderStatementList()
            )}
          </div>
        </aside>

        <section className="space-y-4">
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
              {selectedDocumentId && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => loadDocumentDetail(selectedDocumentId)}
                    disabled={detailLoading}
                  >
                    {detailLoading ? (
                      <>
                        <div className="loading-spinner mr-2"></div>
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
                    className="btn btn-primary btn-sm"
                    onClick={() => onMatchDocument(selectedDocumentId)}
                    disabled={matchingDocumentId === selectedDocumentId}
                  >
                    {matchingDocumentId === selectedDocumentId ? (
                      <>
                        <div className="loading-spinner mr-2"></div>
                        Matchar...
                      </>
                    ) : (
                      <>
                        <FiCheckCircle className="mr-2" />
                        Auto-matcha
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>

            {selectedDocument && (
              <div className="px-6 pb-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                    <div className="text-xs text-gray-400 uppercase tracking-wide">Status</div>
                    <div className="mt-2 flex items-center gap-2">
                      <span className={`status-badge ${toneClass[describeDocumentStatus(selectedDocument.status).tone] || 'status-processing'}`}>
                        {describeDocumentStatus(selectedDocument.status).label}
                      </span>
                    </div>
                  </div>
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                    <div className="text-xs text-gray-400 uppercase tracking-wide">Linjer</div>
                    <div className="mt-2 text-gray-100 text-lg font-semibold">{lineCounts.total}</div>
                    <div className="text-xs text-gray-400 mt-1">Matchade: {lineCounts.matched} &middot; Obearbetade: {lineCounts.unmatched}</div>
                  </div>
                  <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                    <div className="text-xs text-gray-400 uppercase tracking-wide">Senast uppdaterad</div>
                    <div className="mt-2 text-gray-100 text-lg font-semibold">
                      {formatDate(selectedDocument.updated_at || selectedDocument.uploaded_at)}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="px-6 pb-6">
              {renderLineTable()}
            </div>
          </div>
        </section>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Så fungerar matchningen</h3>
            <p className="card-subtitle">Få en snabb överblick över processen för korttransaktioner.</p>
          </div>
        </div>
        <ul className="space-y-3 text-sm text-gray-300 px-6 pb-6">
          <li><span className="text-white font-medium">1.</span> Ladda upp kontoutdrag från First Card eller annat kortinstitut via integrationssidan.</li>
          <li><span className="text-white font-medium">2.</span> Kör <em>Auto-matcha</em> för att koppla transaktioner till kvitton baserat på belopp, datum och referenser.</li>
          <li><span className="text-white font-medium">3.</span> Vid behov kan du manuellt koppla kvitton via kandidatlistan för varje rad.</li>
        </ul>
      </div>

      {candidatesContent}

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
