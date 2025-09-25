import React from 'react'
import { FiSearch, FiFilter, FiDownload, FiRefreshCw, FiEye, FiEdit, FiCheckCircle, FiDollarSign, FiFileText } from 'react-icons/fi'
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

function StatusBadge({ status }) {
  const translated = translateStatus(status)
  const normalized = String(status || '').toLowerCase()

  const getStatusClass = (status) => {
    switch (status) {
      case 'processing': return 'status-processing'
      case 'queued': return 'status-queued'
      case 'failed': return 'status-failed'
      case 'passed':
      case 'completed': return 'status-passed'
      case 'manual_review':
      case 'needs_review': return 'status-manual_review'
      default: return 'status-pending'
    }
  }

  return (
    <span className={`status-badge ${getStatusClass(normalized)}`}>
      {translated || 'Okänd'}
    </span>
  )
}

function SearchAndFilters({ onSearch, onPageSizeChange, pageSize, loading }) {
  const [searchTerm, setSearchTerm] = React.useState('')

  const handleSearch = (e) => {
    e.preventDefault()
    onSearch(searchTerm)
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">Sök och filtrera</h3>
          <p className="card-subtitle">Hitta kvitton snabbt</p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Sök efter företag, belopp eller filnamn..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="dm-input pl-10"
            />
          </div>
          <button type="submit" className="btn btn-primary">
            <FiSearch />
          </button>
        </form>

        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-600 whitespace-nowrap" htmlFor="page-size">
            Visa per sida:
          </label>
          <select
            id="page-size"
            className="dm-input w-24"
            value={pageSize}
            onChange={onPageSizeChange}
            disabled={loading}
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>
    </div>
  )
}

function ReceiptPreview({ receipt }) {
  if (!receipt.preview_url) {
    return (
      <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center">
        <span className="text-gray-400 text-xs">Ingen bild</span>
      </div>
    )
  }

  return (
    <div className="group relative">
      <img
        src={receipt.preview_url}
        alt={`Förhandsgranskning av kvitto ${receipt.id}`}
        className="w-16 h-16 object-cover rounded-lg border-2 border-gray-200 hover:border-blue-300 transition-all duration-200 cursor-pointer"
        loading="lazy"
      />
      <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 rounded-lg transition-all duration-200 flex items-center justify-center">
        <FiEye className="text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
      </div>
    </div>
  )
}

export default function Receipts() {
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
      setStatus(`✅ Hämtade ${arr.length} kvitton`)
    } catch (error) {
      // Fallback: Show component with error message but don't prevent rendering
      console.warn('Receipts API error:', error)
      setItems([])
      setStatus(`❌ Fel vid hämtning: ${error instanceof Error ? error.message : error}`)
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

  const onSearch = (searchTerm) => {
    setStatus(`🔍 Söker efter: "${searchTerm}"`)
    // Implement search logic here
    console.log('Search for:', searchTerm)
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
      resultMessage = '✅ FTP-hämtning klar'
      try {
        const payload = await res.json()
        if (payload?.message) {
          resultMessage = `✅ ${payload.message}`
        } else if (payload?.downloaded !== undefined) {
          resultMessage = `✅ FTP-hämtning klar – ${payload.downloaded} filer hämtade`
        }
      } catch (jsonError) {
        // Keep default message if response is not JSON
      }
    } catch (error) {
      resultMessage = `❌ FTP-fel: ${error instanceof Error ? error.message : error}`
    } finally {
      setFtpLoading(false)
      await loadReceipts()
      setStatus(resultMessage)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="card bg-gradient-to-r from-green-500 to-blue-500 text-white border-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">Kvitton</h1>
            <p className="opacity-90">Hantera och granska alla inkomna kvitton</p>
          </div>
          <div className="flex gap-2">
            <button
              className={`btn bg-white bg-opacity-20 hover:bg-opacity-30 border-0 ${ftpLoading ? 'loading-overlay' : ''}`}
              onClick={onFetchFtp}
              disabled={ftpLoading}
            >
              <FiRefreshCw className={ftpLoading ? 'animate-spin' : ''} />
              {ftpLoading ? 'Hämtar...' : 'Hämta från FTP'}
            </button>
            <button className="btn bg-white bg-opacity-20 hover:bg-opacity-30 border-0">
              <FiDownload />
              Exportera
            </button>
          </div>
        </div>
      </div>

      {/* Status Display */}
      {status && (
        <div className={`card border-l-4 ${
          status.includes('✅') ? 'border-l-green-500 bg-green-50' :
          status.includes('❌') ? 'border-l-red-500 bg-red-50' :
          status.includes('🔍') ? 'border-l-blue-500 bg-blue-50' :
          'border-l-gray-500 bg-gray-50'
        }`}>
          <div className="text-sm font-medium">{status}</div>
        </div>
      )}

      {/* Search and Filters */}
      <SearchAndFilters
        onSearch={onSearch}
        onPageSizeChange={onPageSizeChange}
        pageSize={pageSize}
        loading={loading}
      />

      {/* Receipts Table */}
      <div className="card overflow-hidden">
        <div className="card-header">
          <div>
            <h3 className="card-title">Alla kvitton ({items.length})</h3>
            <p className="card-subtitle">Sorterat efter senaste först</p>
          </div>
          <div className="flex gap-2">
            <button className="btn btn-secondary btn-sm">
              <FiFilter />
              Filter
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                <th className="text-left p-4">Förhandsgranskning</th>
                <th className="text-left p-4">Datum</th>
                <th className="text-left p-4">Företag</th>
                <th className="text-right p-4">Exkl. moms</th>
                <th className="text-right p-4">Inkl. moms</th>
                <th className="text-center p-4">Status</th>
                <th className="text-left p-4">Filnamn</th>
                <th className="text-center p-4">Åtgärder</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center">
                    <div className="flex items-center justify-center gap-3">
                      <div className="loading-spinner"></div>
                      <span className="text-gray-500">Laddar kvitton...</span>
                    </div>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-gray-500">
                    <div className="space-y-2">
                      <div>Inga kvitton hittades</div>
                      <div className="text-sm">Prova att hämta nya filer från FTP</div>
                    </div>
                  </td>
                </tr>
              ) : (
                items.map((receipt, index) => (
                  <tr
                    key={receipt.id}
                    className={`hover:bg-blue-50 transition-colors duration-200 ${
                      index % 2 === 0 ? 'bg-gray-50' : 'bg-white'
                    }`}
                  >
                    <td className="p-4">
                      <ReceiptPreview receipt={receipt} />
                    </td>
                    <td className="p-4">
                      <div className="font-medium">
                        {formatDate(receipt.purchase_date || receipt.purchase_datetime)}
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="font-medium">{receipt.merchant || '-'}</div>
                      {receipt.line_item_count && (
                        <div className="text-sm text-gray-500">
                          {receipt.line_item_count} artiklar
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-right font-medium">
                      {formatCurrency(receipt.net_amount)}
                    </td>
                    <td className="p-4 text-right font-bold text-lg">
                      {formatCurrency(receipt.gross_amount)}
                    </td>
                    <td className="p-4 text-center">
                      <StatusBadge status={receipt.status || receipt.ai_status} />
                    </td>
                    <td className="p-4">
                      <div className="text-sm font-mono text-gray-600 max-w-32 truncate">
                        {receipt.original_filename || '-'}
                      </div>
                    </td>
                    <td className="p-4 text-center">
                      <div className="flex gap-1 justify-center">
                        <button className="btn btn-sm border border-gray-200 hover:border-blue-300 bg-white hover:bg-blue-50 text-gray-600 hover:text-blue-600">
                          <FiEye />
                        </button>
                        <button className="btn btn-sm border border-gray-200 hover:border-green-300 bg-white hover:bg-green-50 text-gray-600 hover:text-green-600">
                          <FiEdit />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Summary Stats */}
      {items.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="stat-card bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <div className="stat-number text-2xl font-bold text-blue-600">
                  {items.length}
                </div>
                <div className="stat-label text-blue-800">Totalt kvitton</div>
              </div>
              <FiFileText className="text-blue-500 text-2xl" />
            </div>
          </div>

          <div className="stat-card bg-gradient-to-br from-green-50 to-green-100 border border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <div className="stat-number text-2xl font-bold text-green-600">
                  {items.filter(r => ['passed', 'completed'].includes(r.status || r.ai_status)).length}
                </div>
                <div className="stat-label text-green-800">Godkända</div>
              </div>
              <FiCheckCircle className="text-green-500 text-2xl" />
            </div>
          </div>

          <div className="stat-card bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200">
            <div className="flex items-center justify-between">
              <div>
                <div className="stat-number text-2xl font-bold text-purple-600">
                  {formatCurrency(
                    items.reduce((sum, r) => sum + (r.gross_amount || 0), 0)
                  )}
                </div>
                <div className="stat-label text-purple-800">Total summa</div>
              </div>
              <FiDollarSign className="text-purple-500 text-2xl" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}