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
  const MAX_ITEMS = 200
  const [items, setItems] = React.useState([])
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState('')
  const [resuming, setResuming] = React.useState(new Set())
  const [selected, setSelected] = React.useState(new Set())

  const loadQueue = React.useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true)
      setError('')
    }
    try {
      const res = await api.fetch('/ai/api/queue/')
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = await res.json()
      const list = Array.isArray(data.items) ? data.items : []
      const trimmed = list.slice(0, MAX_ITEMS)
      setItems(trimmed)
      // Drop selections that are no longer visible
      const visibleIds = new Set(trimmed.map((r) => r.file_id))
      setSelected((prev) => new Set([...prev].filter((id) => visibleIds.has(id))))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setItems([])
    } finally {
      if (!silent) {
        setLoading(false)
      }
    }
  }, [])

  React.useEffect(() => {
    loadQueue(false)
    const intervalMs = 30000
    const interval = setInterval(() => loadQueue(true), intervalMs)
    return () => clearInterval(interval)
  }, [loadQueue])

  const toggleSelected = (fileId) => {
    if (!fileId) return
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(fileId)) {
        next.delete(fileId)
      } else {
        next.add(fileId)
      }
      return next
    })
  }

  const selectAllOrphans = () => {
    const orphanIds = items.filter((r) => r.is_orphan && r.can_resume && r.file_id).map((r) => r.file_id)
    setSelected(new Set(orphanIds))
  }

  const clearSelection = () => setSelected(new Set())

  const handleResumeSelected = async () => {
    const ids = Array.from(selected)
    if (ids.length === 0) return
    setResuming(new Set(ids))
    try {
      const res = await api.fetch('/ai/api/queue/resume-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_ids: ids }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.error || `HTTP ${res.status}`)
      }
      await loadQueue()
      clearSelection()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setResuming(new Set())
    }
  }

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
    const isOrphan = row.is_orphan || (!row.id && row.file_id)
    const canResumeApi = row.can_resume === true
    // Fallback logic if API does not provide can_resume
    const canResumeLocal = (stalled && (row.status === 'running' || row.status === 'queued') && row.file_id) || isOrphan
    const canResume = canResumeApi || canResumeLocal

    const isResuming = resuming.has(row.file_id)
    const isSelected = selected.has(row.file_id)

    return (
      <div key={row.id || row.file_id} className={`card ${isFirst ? 'border-red-600 border' : ''}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-gray-800 text-red-200">
              {isFirst ? <FiPlay /> : <FiPause />}
            </div>
            <div>
              <div className="text-sm text-gray-400">Workflow</div>
              <div className="text-lg font-semibold text-white">{row.workflow_key || 'Okänd'}</div>
              <div className="text-xs text-gray-500">Källa: {row.source_channel || 'okänd'}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {stalled && <Badge label="Stalled" tone="status-failed" />}
            {isOrphan && <Badge label="Orphan" tone="status-failed" />}
            <Badge label={row.status || 'okänd'} tone={tone} />
            {canResume && (
              <input
                type="checkbox"
                className="form-checkbox h-4 w-4 text-blue-500"
                checked={isSelected}
                onChange={() => toggleSelected(row.file_id)}
              />
            )}
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
            <div>{row.derived_ai_status || row.ai_status || '-'}</div>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500 mt-3">
          <div><FiClock className="inline mr-1" />Start: {row.created_at || '-'}</div>
          <div><FiClock className="inline mr-1" />Senast: {row.updated_at || '-'}</div>
          {stalled && <div className="text-red-400 font-semibold">Ingen uppdatering på {row.idle_seconds}s</div>}
          <div className="ml-auto">Run-ID: {row.id || 'Saknas'}</div>
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
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              className="form-checkbox h-4 w-4"
              onChange={(e) => (e.target.checked ? selectAllOrphans() : clearSelection())}
            />
            Markera alla Orphan
          </label>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleResumeSelected}
            disabled={selected.size === 0 || resuming.size > 0}
          >
            Återuppta markerade
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => loadQueue(false)} disabled={loading}>
            Uppdatera
          </button>
        </div>
      </div>

      {/* Silent refresh: no visible spinner to avoid layout jump */}

      {error && (
        <div className="card border border-red-700 text-red-200 flex items-center gap-2">
          <FiAlertCircle /> {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="card text-gray-300">Ingen kö just nu.</div>
      )}

      {items.map((row, idx) => renderRow(row, idx === 0))}

      {!loading && !error && items.length === MAX_ITEMS && (
        <div className="text-xs text-gray-500">
          Visar de första {MAX_ITEMS} posterna av köresultatet för att undvika att sidan blir tung. Använd manuellt
          Uppdatera vid behov.
        </div>
      )}
    </div>
  )
}

export default QueuePage
