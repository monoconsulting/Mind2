import React from 'react'
import { api } from '../api'

const currencyFormatter = new Intl.NumberFormat('sv-SE', {
  style: 'currency',
  currency: 'SEK',
  minimumFractionDigits: 2,
})

function formatCurrency(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '-'
  }
  return currencyFormatter.format(value)
}

function formatDate(value) {
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
    return parsed.toLocaleDateString('sv-SE')
  } catch (error) {
    return typeof value === 'string' ? value : '-'
  }
}

function translateStatus(status) {
  if (!status) {
    return ''
  }
  const normalized = String(status).toLowerCase()
  const map = {
    processing: 'Bearbetas',
    queued: 'I kö',
    failed: 'Fel',
    passed: 'Godkänd',
    completed: 'Klar',
    manual_review: 'Manuell kontroll',
    needs_review: 'Behöver kontroll',
  }
  return map[normalized] || status
}

export default function Kvitton() {
  const [items, setItems] = React.useState([])
  const [status, setStatus] = React.useState('')
  const [pageSize, setPageSize] = React.useState(50)
  const [loading, setLoading] = React.useState(false)
  const [ftpLoading, setFtpLoading] = React.useState(false)

  const loadReceipts = React.useCallback(async () => {
    setLoading(true)
    setStatus('Laddar kvitton...')
    try {
      const res = await api.fetch(`/ai/api/receipts?page_size=${pageSize}`)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = await res.json()
      const arr = Array.isArray(data?.items) ? data.items : (Array.isArray(data) ? data : [])
      setItems(arr)
      setStatus(`Hämtade ${arr.length} kvitton`)
    } catch (error) {
      setStatus(`Fel vid hämtning: ${error instanceof Error ? error.message : error}`)
    } finally {
      setLoading(false)
    }
  }, [pageSize])

  React.useEffect(() => {
    loadReceipts()
  }, [loadReceipts])

  const onPageSizeChange = (event) => {
    const value = Number(event.target.value)
    if (!Number.isNaN(value)) {
      setPageSize(value)
    }
  }

  const onFetchFtp = async () => {
    setFtpLoading(true)
    let resultMessage = 'Hämtar filer från FTP...'
    setStatus(resultMessage)
    try {
      const res = await api.fetch('/ai/api/ingest/fetch-ftp', { method: 'POST' })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      resultMessage = 'FTP-hämtning klar'
      try {
        const payload = await res.json()
        if (payload?.message) {
          resultMessage = payload.message
        } else if (payload?.downloaded !== undefined) {
          resultMessage = `FTP-hämtning klar – ${payload.downloaded} filer hämtade`
        }
      } catch (jsonError) {
        // Behåll standardmeddelandet om svaret inte är JSON
      }
    } catch (error) {
      resultMessage = `FTP-fel: ${error instanceof Error ? error.message : error}`
    } finally {
      setFtpLoading(false)
      await loadReceipts()
      setStatus(resultMessage)
    }
  }

  return (
    <section>
      <div className="flex items-start justify-between flex-wrap gap-3 mb-3">
        <div>
          <h2 className="text-xl font-semibold">Kvitton</h2>
          <div id="status" className="text-[#9aa3c7] text-sm mt-1">{status}</div>
        </div>
        <div className="flex items-center gap-3 ml-auto">
          <label className="text-sm text-[#9aa3c7]" htmlFor="page-size">Antal per sida</label>
          <select
            id="page-size"
            className="dm-input"
            value={pageSize}
            onChange={onPageSizeChange}
            disabled={loading}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <button
            type="button"
            className="dm-btn-danger"
            onClick={onFetchFtp}
            disabled={ftpLoading}
          >
            {ftpLoading ? 'Hämtar…' : 'Hämta från FTP'}
          </button>
        </div>
      </div>
      <div className="dm-card overflow-hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="text-left p-2">Datum (från kvitto)</th>
              <th className="text-left p-2">Företag</th>
              <th className="text-right p-2">Total summa ex. moms</th>
              <th className="text-right p-2">Total summa inkl. moms</th>
              <th className="text-right p-2">Antal varor</th>
              <th className="text-left p-2">Filnamn</th>
              <th className="text-left p-2">Förhandsgranskning</th>
            </tr>
          </thead>
          <tbody id="tbl">
            {items.length === 0 ? (
              <tr>
                <td colSpan={7} className="border-t border-[var(--dm-border)] p-4 text-center text-[#9aa3c7]">
                  {loading ? 'Laddar...' : 'Inga kvitton hittades'}
                </td>
              </tr>
            ) : (
              items.map((receipt) => {
                const preview = receipt.preview_url
                const statusLabel = translateStatus(receipt.status || receipt.ai_status)
                return (
                  <tr key={receipt.id}>
                    <td className="border-t border-[var(--dm-border)] p-2">{formatDate(receipt.purchase_date || receipt.purchase_datetime)}</td>
                    <td className="border-t border-[var(--dm-border)] p-2">
                      <div>{receipt.merchant || '-'}</div>
                      {statusLabel && <div className="text-xs text-[#9aa3c7] mt-1">{statusLabel}</div>}
                    </td>
                    <td className="border-t border-[var(--dm-border)] p-2 text-right">{formatCurrency(receipt.net_amount)}</td>
                    <td className="border-t border-[var(--dm-border)] p-2 text-right">{formatCurrency(receipt.gross_amount)}</td>
                    <td className="border-t border-[var(--dm-border)] p-2 text-right">{typeof receipt.line_item_count === 'number' ? receipt.line_item_count : '-'}</td>
                    <td className="border-t border-[var(--dm-border)] p-2">{receipt.original_filename || '-'}</td>
                    <td className="border-t border-[var(--dm-border)] p-2">
                      {preview ? (
                        <img
                          src={preview}
                          alt={`Förhandsgranskning av kvitto ${receipt.id}`}
                          className="h-16 w-16 object-cover rounded-md border border-[var(--dm-border)]"
                          loading="lazy"
                        />
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
