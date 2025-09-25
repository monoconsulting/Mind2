import React from 'react'
import { FiLayers, FiPlusCircle } from 'react-icons/fi'
import { api } from '../api'

function Feedback({ feedback }) {
  if (!feedback) {
    return null
  }

  const tone = feedback.type === 'error'
    ? 'bg-red-900 text-red-200 border border-red-700'
    : 'bg-green-900 text-green-200 border border-green-700'

  return (
    <div className={`p-4 rounded-lg text-sm mt-4 ${tone}`}>
      {feedback.text}
    </div>
  )
}

export default function Settings() {
  const [items, setItems] = React.useState([])
  const [matcher, setMatcher] = React.useState('')
  const [account, setAccount] = React.useState('')
  const [note, setNote] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const [feedback, setFeedback] = React.useState(null)

  const load = React.useCallback(async () => {
    setLoading(true)
    setFeedback(null)
    try {
      const res = await api.fetch('/ai/api/rules')
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }
      const data = await res.json()
      setItems(Array.isArray(data) ? data : data?.items ?? [])
    } catch (error) {
      setItems([])
      setFeedback({
        type: 'error',
        text: `Fel vid hämtning av regler: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => { load() }, [load])

  const add = async (e) => {
    e.preventDefault()
    setSaving(true)
    setFeedback(null)
    try {
      await api.fetch('/ai/api/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ matcher, account, note })
      })
      setMatcher('')
      setAccount('')
      setNote('')
      setFeedback({ type: 'success', text: 'Regeln sparades.' })
      await load()
    } catch (error) {
      setFeedback({
        type: 'error',
        text: `Kunde inte spara regeln: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setSaving(false)
    }
  }

  const statistics = React.useMemo(() => {
    const withNotes = items.filter((rule) => rule.note && rule.note.trim().length > 0).length
    return {
      total: items.length,
      withNotes,
      withoutNotes: items.length - withNotes
    }
  }, [items])

  return (
    <div className="space-y-6">
      <div className="stats-grid">
        <div className="stat-card red">
          <div className="flex items-center justify-between mb-2">
            <FiLayers className="text-2xl opacity-80" />
            <div className="stat-number">{statistics.total}</div>
          </div>
          <div className="stat-label">Regler totalt</div>
          <div className="stat-subtitle">Aktiva konteringsregler i systemet</div>
        </div>
        <div className="stat-card green">
          <div className="flex items-center justify-between mb-2">
            <FiPlusCircle className="text-2xl opacity-80" />
            <div className="stat-number">{statistics.withNotes}</div>
          </div>
          <div className="stat-label">Med notering</div>
          <div className="stat-subtitle">Regler med extra instruktioner</div>
        </div>
        <div className="stat-card yellow">
          <div className="flex items-center justify-between mb-2">
            <FiLayers className="text-2xl opacity-80" />
            <div className="stat-number">{statistics.withoutNotes}</div>
          </div>
          <div className="stat-label">Saknar notering</div>
          <div className="stat-subtitle">Bra att komplettera för tydlighet</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Regler för kontering</h3>
            <p className="card-subtitle">Automatisera hur kvitton kopplas till konton.</p>
          </div>
        </div>

        <form onSubmit={add} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <label className="text-sm text-gray-300">
            Villkor
            <input
              className="mt-2"
              value={matcher}
              onChange={(e) => setMatcher(e.target.value)}
              placeholder="Exempel: merchant innehåller..."
              required
            />
          </label>
          <label className="text-sm text-gray-300">
            Konto
            <input
              className="mt-2"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              placeholder="Exempel: 5610"
              required
            />
          </label>
          <label className="text-sm text-gray-300">
            Notering
            <input
              className="mt-2"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Valfritt meddelande"
            />
          </label>
          <div className="flex items-end">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? (
                <>
                  <div className="loading-spinner mr-2"></div>
                  Sparar...
                </>
              ) : (
                <>
                  <FiPlusCircle className="mr-2" />
                  Lägg till regel
                </>
              )}
            </button>
          </div>
        </form>

        <Feedback feedback={feedback} />
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Aktiva regler</h3>
            <p className="card-subtitle">Översikt av villkor och konton.</p>
          </div>
        </div>

        <div className="overflow-hidden border border-gray-700 rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center gap-3 py-12 text-gray-400">
              <div className="loading-spinner"></div>
              <span>Laddar regler...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-12 text-gray-300">
              <FiLayers className="text-3xl" />
              <div className="text-base font-medium">Inga regler registrerade ännu</div>
              <div className="text-sm text-gray-400">Lägg till en regel via formuläret ovan.</div>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
                <tr>
                  <th className="px-4 py-3">Villkor</th>
                  <th className="px-4 py-3">Konto</th>
                  <th className="px-4 py-3">Notering</th>
                </tr>
              </thead>
              <tbody>
                {items.map((rule) => (
                  <tr key={rule.id} className="border-t border-gray-700">
                    <td className="px-4 py-4 text-gray-100">{rule.matcher}</td>
                    <td className="px-4 py-4 text-gray-100">{rule.account}</td>
                    <td className="px-4 py-4 text-gray-300">{rule.note ?? ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
