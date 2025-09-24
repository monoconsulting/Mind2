import React from 'react'
import { api } from '../api'

export default function ExportPage() {
  const [msg, setMsg] = React.useState('')

  const gen = async (e) => {
    e.preventDefault()
    setMsg('Genererar SIE-fil...')
    const form = e.currentTarget
    const from = form.querySelector('#exp-from').value
    const to = form.querySelector('#exp-to').value
    const qs = new URLSearchParams()
    if (from) qs.set('from', from)
    if (to) qs.set('to', to)
    try {
      const res = await api.fetch(`/ai/api/export/sie?${qs.toString()}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `export_${from || 'start'}_${to || 'slut'}.sie`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setMsg(`${res.status}: SIE-fil nerladdad`)
    } catch (error) {
      setMsg(`Fel vid export: ${error instanceof Error ? error.message : error}`)
    }
  }

  return (
    <section>
      <h2 className="text-xl font-semibold">Exportera SIE</h2>
      <form onSubmit={gen} className="dm-card p-4 flex gap-2 items-end mt-3">
        <label>Från
          <input id="exp-from" type="date" className="dm-input" />
        </label>
        <label>Till
          <input id="exp-to" type="date" className="dm-input" />
        </label>
        <button className="dm-btn">Generera</button>
        <div className="ml-auto text-[#9aa3c7] text-sm">{msg}</div>
      </form>
    </section>
  )
}
