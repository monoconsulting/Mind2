import React from 'react'
import { FiRefreshCw, FiCheckCircle, FiAlertTriangle, FiFileText } from 'react-icons/fi'
import { api } from '../api'

const STATUS_MAP = [
  { ids: ['matched', 'matchad', 'completed', 'done', 'success'], label: 'Matchad', tone: 'success' },
  { ids: ['processing', 'matching', 'running'], label: 'Bearbetas', tone: 'processing' },
  { ids: ['queued', 'pending', 'created', 'uploaded'], label: 'I kö', tone: 'pending' },
  { ids: ['failed', 'error'], label: 'Fel', tone: 'failed' },
  { ids: ['ready', 'ready_for_matching', 'new'], label: 'Redo för matchning', tone: 'processing' }
]

const toneClass = {
  success: 'status-passed',
  processing: 'status-processing',
  pending: 'status-pending',
  failed: 'status-failed'
}

function normalizeStatus(status) {
  return String(status ?? '').toLowerCase()
}

function describeStatus(status) {
  const normalized = normalizeStatus(status)
  const match = STATUS_MAP.find(({ ids }) => ids.includes(normalized))
  if (match) {
    return match
  }
  return { label: status || 'Okänd', tone: 'pending' }
}

function formatDateTime(value) {
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
    return parsed.toLocaleString('sv-SE', {
      dateStyle: 'short',
      timeStyle: 'short'
    })
  } catch (error) {
    return typeof value === 'string' ? value : '-'
  }
}

export default function CompanyCard() {
  const [items, setItems] = React.useState([])
  const [loading, setLoading] = React.useState(false)
  const [matchingId, setMatchingId] = React.useState(null)
  const [feedback, setFeedback] = React.useState(null)

  const load = React.useCallback(async () => {
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
        setFeedback({ type: 'info', text: 'Inga kontoutdrag hittades. Ladda upp ett utdrag för att börja matcha kvitton.' })
      } else {
        setFeedback(null)
      }
    } catch (error) {
      setItems([])
      setFeedback({
        type: 'error',
        text: `Fel vid hämtning av kontoutdrag: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => { load() }, [load])

  const onMatch = async (statementId) => {
    setMatchingId(statementId)
    try {
      const response = await api.fetch('/ai/api/reconciliation/firstcard/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: statementId })
      })

      if (!response.ok) {
        throw new Error(`Status ${response.status}`)
      }

      setFeedback({ type: 'success', text: 'Matchning klar. Uppdaterar listan...' })
      await load()
    } catch (error) {
      setFeedback({
        type: 'error',
        text: `Matchning misslyckades: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setMatchingId(null)
    }
  }

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

  const renderFeedback = () => {
    if (!feedback) {
      return null
    }
    const toneClassName = feedback.type === 'error'
      ? 'bg-red-900 text-red-200 border border-red-700'
      : feedback.type === 'success'
        ? 'bg-green-900 text-green-200 border border-green-700'
        : 'bg-blue-900 text-blue-200 border border-blue-700'

    return (
      <div className={`p-4 rounded-lg text-sm ${toneClassName}`}>
        {feedback.text}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="stats-grid">
        <div className="stat-card red">
          <div className="flex items-center justify-between mb-2">
            <FiFileText className="text-2xl opacity-80" />
            <div className="stat-number">{summary.total}</div>
          </div>
          <div className="stat-label">Kontoutdrag</div>
          <div className="stat-subtitle">Alla importerade kortutdrag</div>
        </div>

        <div className="stat-card green">
          <div className="flex items-center justify-between mb-2">
            <FiCheckCircle className="text-2xl opacity-80" />
            <div className="stat-number">{summary.matched}</div>
          </div>
          <div className="stat-label">Matchade</div>
          <div className="stat-subtitle">Utdrag där kvitton hittades</div>
        </div>

        <div className="stat-card yellow">
          <div className="flex items-center justify-between mb-2">
            <FiAlertTriangle className="text-2xl opacity-80" />
            <div className="stat-number">{summary.pending + summary.failed}</div>
          </div>
          <div className="stat-label">Åtgärd krävs</div>
          <div className="stat-subtitle">Kontrollera status eller kör om matchning</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Företagskort</h3>
            <p className="card-subtitle">Hantera kontoutdrag och matcha dem mot kvitton.</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={load}
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
        </div>

        {renderFeedback()}

        <div className="mt-4 overflow-hidden border border-gray-700 rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
              <div className="loading-spinner"></div>
              <span>Laddar kontoutdrag...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-12 text-gray-300">
              <FiFileText className="text-3xl" />
              <div className="text-base font-medium">Inga kontoutdrag hittades</div>
              <div className="text-sm text-gray-400">Ladda upp ett nytt utdrag för att starta matchning.</div>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Uppladdad</th>
                  <th className="px-4 py-3">Senaste uppdatering</th>
                  <th className="px-4 py-3 text-right">Åtgärd</th>
                </tr>
              </thead>
              <tbody>
                {items.map((statement) => {
                  const statusDetails = describeStatus(statement.status)
                  const badgeClass = toneClass[statusDetails.tone] ?? 'status-processing'
                  return (
                    <tr key={statement.id} className="border-t border-gray-700">
                      <td className="px-4 py-4 font-medium text-gray-100">{statement.id}</td>
                      <td className="px-4 py-4">
                        <span className={`status-badge ${badgeClass}`}>
                          {statusDetails.label}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-gray-300">{formatDateTime(statement.created_at || statement.uploaded_at)}</td>
                      <td className="px-4 py-4 text-gray-300">{formatDateTime(statement.updated_at)}</td>
                      <td className="px-4 py-4 text-right">
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={() => onMatch(statement.id)}
                          disabled={matchingId === statement.id}
                        >
                          {matchingId === statement.id ? (
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
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Så fungerar matchningen</h3>
            <p className="card-subtitle">Få en snabb överblick över processen för korttransaktioner.</p>
          </div>
        </div>
        <ul className="space-y-3 text-sm text-gray-300">
          <li><span className="text-white font-medium">1.</span> Ladda upp kontoutdrag från First Card eller annat kortinstitut via integrationssidan.</li>
          <li><span className="text-white font-medium">2.</span> Kör <em>Auto-matcha</em> för att koppla transaktioner till kvitton baserat på belopp, datum och referenser.</li>
          <li><span className="text-white font-medium">3.</span> Kontrollera statusen. Markera utdrag som misslyckats och kör matchningen på nytt vid behov.</li>
        </ul>
      </div>
    </div>
  )
}

