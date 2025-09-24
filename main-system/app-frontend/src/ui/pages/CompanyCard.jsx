import React from 'react'
import { api } from '../api'

export default function CompanyCard() {
  const [items, setItems] = React.useState([])
  const [msg, setMsg] = React.useState('')

  const load = React.useCallback(async () => {
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
      const data = res.ok ? await res.json() : { items: [] }
      setItems(data.items || [])
      setMsg('')
    } catch (error) {
      setMsg(`Fel vid hämtning: ${error instanceof Error ? error.message : error}`)
    }
  }, [])

  React.useEffect(() => { load() }, [load])

  const onMatch = async (statementId) => {
    try {
      const response = await api.fetch('/ai/api/reconciliation/firstcard/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: statementId }),
      })
      setMsg(response.ok ? 'Matchning klar' : `Matchning misslyckades (${response.status})`)
    } catch (error) {
      setMsg(`Matchning misslyckades: ${error instanceof Error ? error.message : error}`)
    } finally {
      load()
    }
  }

  return (
    <section>
      <h2 className="text-xl font-semibold">Företagskort</h2>
      <p className="text-[#9aa3c7] text-sm">Hantera kontoutdrag och matcha dem mot kvitton.</p>
      <div className="text-[#9aa3c7] mt-2 h-5">{msg}</div>
      <div className="dm-card overflow-hidden mt-3">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-left p-2">ID</th>
              <th className="text-left p-2">Status</th>
              <th className="text-left p-2">Uppladdad</th>
              <th className="text-right p-2">Åtgärder</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={4} className="border-t border-[var(--dm-border)] p-4 text-center text-[#9aa3c7]">
                  Inga kontoutdrag hittades
                </td>
              </tr>
            ) : (
              items.map((s) => (
                <tr key={s.id}>
                  <td className="border-t border-[var(--dm-border)] p-2">{s.id}</td>
                  <td className="border-t border-[var(--dm-border)] p-2">{s.status ?? ''}</td>
                  <td className="border-t border-[var(--dm-border)] p-2">{s.created_at ?? s.uploaded_at ?? ''}</td>
                  <td className="border-t border-[var(--dm-border)] p-2 text-right">
                    <button className="dm-btn" onClick={() => onMatch(s.id)}>Auto-matcha</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
