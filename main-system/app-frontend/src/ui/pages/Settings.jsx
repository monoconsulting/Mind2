import React from 'react'
import { api } from '../api'

export default function Settings() {
  const [items, setItems] = React.useState([])
  const [matcher, setMatcher] = React.useState('')
  const [account, setAccount] = React.useState('')
  const [note, setNote] = React.useState('')

  const load = React.useCallback(async () => {
    try {
      const res = await api.fetch('/ai/api/rules')
      setItems(res.ok ? await res.json() : [])
    } catch (error) {
      setItems([])
    }
  }, [])

  React.useEffect(() => { load() }, [load])

  const add = async (e) => {
    e.preventDefault()
    try {
      await api.fetch('/ai/api/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ matcher, account, note }),
      })
      setMatcher('')
      setAccount('')
      setNote('')
      load()
    } catch (error) {
      // TODO: surface validation errors
    }
  }

  return (
    <section>
      <h2 className="text-xl font-semibold">Regler för kontering</h2>
      <form onSubmit={add} className="dm-card p-4 flex gap-2 items-end mt-3">
        <label className="text-sm">Villkor
          <input className="dm-input" value={matcher} onChange={(e) => setMatcher(e.target.value)} placeholder="t.ex. merchant innehåller..." />
        </label>
        <label className="text-sm">Konto
          <input className="dm-input" value={account} onChange={(e) => setAccount(e.target.value)} placeholder="t.ex. 5610" />
        </label>
        <label className="text-sm">Notering
          <input className="dm-input" value={note} onChange={(e) => setNote(e.target.value)} placeholder="valfritt" />
        </label>
        <button className="dm-btn">Lägg till regel</button>
      </form>
      <div className="dm-card overflow-hidden mt-3">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-left p-2">Villkor</th>
              <th className="text-left p-2">Konto</th>
              <th className="text-left p-2">Notering</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={3} className="border-t border-[var(--dm-border)] p-4 text-center text-[#9aa3c7]">
                  Inga regler registrerade ännu
                </td>
              </tr>
            ) : (
              items.map((r) => (
                <tr key={r.id}>
                  <td className="border-t border-[var(--dm-border)] p-2">{r.matcher}</td>
                  <td className="border-t border-[var(--dm-border)] p-2">{r.account}</td>
                  <td className="border-t border-[var(--dm-border)] p-2">{r.note ?? ''}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
