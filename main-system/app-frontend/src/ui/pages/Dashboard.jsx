import React from 'react'
import { api } from '../api'

export default function Dashboard() {
  const [out, setOut] = React.useState('')

  const ping = async () => {
    try {
      const res = await api.fetch('/ai/api/admin/ping')
      const txt = await res.text()
      setOut(`${res.status}: ${txt}`)
    } catch (e) {
      setOut(`Fel: ${e}`)
    }
  }

  return (
    <section className="dm-card p-4">
      <h2 className="text-xl font-semibold mb-2">Välkommen till Mind Admin</h2>
      <p className="text-sm text-[#9aa3c7] mb-4">Använd knappen nedan för att verifiera att API:et svarar.</p>
      <button className="dm-btn" onClick={ping}>Testa API</button>
      <pre id="out" className="mt-3 text-sm text-[#9aa3c7]">{out}</pre>
    </section>
  )
}
