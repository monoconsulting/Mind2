import React from 'react'
import { FiDownload, FiInfo } from 'react-icons/fi'
import { api } from '../api'

function FeedbackMessage({ feedback }) {
  if (!feedback) {
    return null
  }

  const toneClass = feedback.type === 'error'
    ? 'bg-red-900 text-red-200 border border-red-700'
    : 'bg-green-900 text-green-200 border border-green-700'

  return (
    <div className={`p-4 rounded-lg text-sm mt-4 ${toneClass}`}>
      {feedback.text}
    </div>
  )
}

export default function ExportPage() {
  const [feedback, setFeedback] = React.useState(null)
  const [loading, setLoading] = React.useState(false)

  const gen = async (e) => {
    e.preventDefault()
    setFeedback(null)
    setLoading(true)

    const form = e.currentTarget
    const from = form.querySelector('#export-from').value
    const to = form.querySelector('#export-to').value

    const qs = new URLSearchParams()
    if (from) qs.set('from', from)
    if (to) qs.set('to', to)

    try {
      const res = await api.fetch(`/ai/api/export/sie?${qs.toString()}`)
      if (!res.ok) {
        throw new Error(`Status ${res.status}`)
      }

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mind_export_${from || 'start'}_${to || 'slut'}.sie`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)

      setFeedback({ type: 'success', text: 'Exportfilen skapades och laddades ner.' })
    } catch (error) {
      setFeedback({
        type: 'error',
        text: `Fel vid export: ${error instanceof Error ? error.message : error}`
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Exportera SIE</h3>
            <p className="card-subtitle">Skapa bokföringsunderlag för valfri period.</p>
          </div>
        </div>

        <form onSubmit={gen} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <label className="text-sm text-gray-300">
            Från datum
            <input id="export-from" type="date" className="mt-2" placeholder="ÅÅÅÅ-MM-DD" />
          </label>
          <label className="text-sm text-gray-300">
            Till datum
            <input id="export-to" type="date" className="mt-2" placeholder="ÅÅÅÅ-MM-DD" />
          </label>
          <div className="flex items-end">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? (
                <>
                  <div className="loading-spinner mr-2"></div>
                  Genererar...
                </>
              ) : (
                <>
                  <FiDownload className="mr-2" />
                  Generera SIE-fil
                </>
              )}
            </button>
          </div>
        </form>

        <FeedbackMessage feedback={feedback} />
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">När ska export användas?</h3>
            <p className="card-subtitle">Bra att känna till inför bokföringen.</p>
          </div>
          <FiInfo className="text-xl text-blue-300" />
        </div>
        <ul className="space-y-3 text-sm text-gray-300">
          <li><span className="text-white font-medium">•</span> Kör exporten efter att kvitton och kontoutdrag är matchade.</li>
          <li><span className="text-white font-medium">•</span> Välj en tidsperiod som matchar din bokföringsmånad.</li>
          <li><span className="text-white font-medium">•</span> Kontrollera filen i ekonomisystemet och åtgärda eventuella varningar.</li>
        </ul>
      </div>
    </div>
  )
}
