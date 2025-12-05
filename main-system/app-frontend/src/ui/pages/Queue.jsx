import React from 'react'
import { FiClock, FiPlay, FiPause, FiAlertCircle } from 'react-icons/fi'
import { api } from '../api'

const statusClass = {
  running: 'status-processing',
  queued: 'status-queued',
  succeeded: 'status-passed',
  failed: 'status-failed',
  canceled: 'status-failed',
  skipped: 'status-queued',
}

function Badge({ label, tone = 'status-queued' }) {
  return <span className={`status-badge ${tone}`}>{label}</span>
}

function QueuePage() {
  const [items, setItems] = React.useState([])
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState('')
  const [resuming, setResuming] = React.useState(new Set())

  const loadQueue = React.useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.fetch('/ai/api/queue/')
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = await res.json()
      setItems(Array.isArray(data.items) ? data.items : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    loadQueue()
    const interval = setInterval(loadQueue, 5000)
    return () => clearInterval(interval)
  }, [loadQueue])

  const handleResume = async (row) => {
    if (!row.file_id) return
    const key = row.file_id
    setResuming((prev) => new Set([...prev, key]))
    try {
      const res = await api.fetch(`/ai/api/ingest/process/${row.file_id}/resume`, { method: 'POST' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || data.queued === false) {
        throw new Error(data.error || `HTTP ${res.status}`)
      }
      await loadQueue()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setResuming((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  const renderRow = (row, isFirst) => {
    const tone = statusClass[row.status] || 'status-queued'
    const stage = row.latest_stage_key ? `${row.latest_stage_key} ${row.latest_stage_status || ''}`.trim() : row.current_stage
    const stalled = row.stalled
    const canResume = stalled && (row.status === 'running' || row.status === 'queued') && row.file_id
    const isResuming = resuming.has(row.file_id)
    return (
      <div key={row.id} className={`card ${isFirst ? 'border-red-600 border' : ''}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gray-800 text-red-200">
              {isFirst ? <FiPlay /> : <FiPause />}
            </div>
            <div>
              <div className="text-sm text-gray-400">Workflow</div>
              <div className="text-lg font-semibold text-white">{row.workflow_key}</div>
              <div className="text-xs text-gray-500">Källa: {row.source_channel || 'okänd'}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {stalled && <Badge label="Stalled" tone="status-failed" />}
            <Badge label={row.status || 'okänd'} tone={tone} />
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 text-sm text-gray-200">
          <div>
            <div className="text-gray-400 text-xs">Fil</div>
            <div>{row.file_name || row.file_id || '-'}</div>
          </div>
          <div>
            <div className="text-gray-400 text-xs">Steg</div>
            <div>{stage || '-'}</div>
          </div>
          <div>
            <div className="text-gray-400 text-xs">AI-status</div>
            <div>{row.ai_status || '-'}</div>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500 mt-3">
          <div><FiClock className="inline mr-1" />Start: {row.created_at || '-'}</div>
          <div><FiClock className="inline mr-1" />Senast: {row.updated_at || '-'}</div>
          {stalled && <div className="text-red-400 font-semibold">Ingen uppdatering på {row.idle_seconds}s</div>}
          <div className="ml-auto">Run-ID: {row.id}</div>
        </div>
        {canResume && (
          <div className="mt-3 flex justify-end">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => handleResume(row)}
              disabled={isResuming}
            >
              {isResuming ? 'Återupptar...' : 'Lås upp / Återuppta'}
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-white">Kö</h2>
          <p className="text-sm text-gray-400">Visar alla workflow_runs i ordning. Överst = pågående.</p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={loadQueue} disabled={loading}>
          Uppdatera
        </button>
      </div>

      {loading && (
        <div className="card flex items-center gap-2 text-gray-200">
          <div className="loading-spinner" /> Laddar kö...
        </div>
      )}

      {error && (
        <div className="card border border-red-700 text-red-200 flex items-center gap-2">
          <FiAlertCircle /> {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="card text-gray-300">Ingen kö just nu.</div>
      )}

      {items.map((row, idx) => renderRow(row, idx === 0))}
    </div>
  )
}

export default QueuePage
