/**
 * @file ManualMatch.jsx
 * @description Manual matching view for linking FirstCard transaction items to receipts.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FiCheckCircle, FiAlertTriangle, FiChevronLeft, FiChevronRight, FiEye } from 'react-icons/fi'
import { api } from '../api'
import ReceiptPreviewModal from '../components/ReceiptPreviewModal'

function PaginationControls({ page, totalPages, onPrev, onNext, label }) {
  if (!totalPages || totalPages <= 1) return null
  return (
    <div className="flex items-center gap-2 text-sm text-gray-300 flex-wrap">
      <button type="button" className="btn btn-secondary btn-sm" onClick={onPrev} disabled={page <= 1}>
        <FiChevronLeft />
        Föregående
      </button>
      <div className="px-2 py-1 rounded bg-gray-800/70 border border-gray-700">
        {label || `Sida ${page} av ${totalPages}`}
      </div>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onNext} disabled={page >= totalPages}>
        Nästa
        <FiChevronRight />
      </button>
    </div>
  )
}

function PageSizeSelector({ label, value, onChange, options = [10, 15, 25, 50] }) {
  return (
    <label className="flex items-center gap-2 text-sm text-gray-300">
      <span>{label}</span>
      <select
        className="dm-input w-24"
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || value)}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </label>
  )
}

function formatAmount(value, currency = 'SEK') {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  try {
    return new Intl.NumberFormat('sv-SE', {
      style: 'currency',
      currency: currency || 'SEK',
      minimumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${value.toFixed(2)} ${currency || 'SEK'}`
  }
}

function resolveFcCurrency(item) {
  return item?.currency_original || item?.currency || null
}

function resolveFcSek(item) {
  const candidate = item?.amount_sek ?? item?.gross_amount_sek ?? item?.amount ?? item?.gross_amount
  const value = Number(candidate)
  return Number.isFinite(value) ? value : null
}

function resolveFcOriginal(item) {
  const candidate = item?.amount_original ?? item?.gross_amount ?? item?.amount
  const value = Number(candidate)
  return Number.isFinite(value) ? value : null
}

function resolveReceiptCurrency(item) {
  return item?.currency || null
}

function resolveReceiptSek(item) {
  const candidate = item?.gross_amount_sek ?? item?.gross_amount ?? item?.total_gross
  const value = Number(candidate)
  return Number.isFinite(value) ? value : null
}

function resolveReceiptOriginal(item) {
  const candidate = item?.gross_amount_original ?? item?.gross_amount ?? item?.total_gross
  const value = Number(candidate)
  return Number.isFinite(value) ? value : null
}

function formatDate(isoDate) {
  if (!isoDate) return '-'
  try {
    const d = new Date(isoDate)
    if (Number.isNaN(+d)) return isoDate
    return d.toLocaleDateString('sv-SE')
  } catch {
    return isoDate
  }
}

function daysInMonth(year, month1to12) {
  return new Date(year, month1to12, 0).getDate()
}

function monthRange(year, month1to12) {
  const last = daysInMonth(year, month1to12)
  const mm = String(month1to12).padStart(2, '0')
  return { from: `${year}-${mm}-01`, to: `${year}-${mm}-${last}` }
}

function normalizeDateOnly(value) {
  if (!value) return null
  const trimmed = String(value).trim()
  if (!trimmed) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed
  try {
    const d = new Date(trimmed)
    if (Number.isNaN(+d)) return null
    return d.toISOString().slice(0, 10)
  } catch {
    return null
  }
}

function parseStatementsPayload(payload) {
  if (!payload) return []
  if (Array.isArray(payload?.statements)) return payload.statements
  if (Array.isArray(payload)) return payload
  return []
}

function collectStatementsForMonth(statements, year, month) {
  if (!Array.isArray(statements) || !year || !month) return []
  const { from, to } = monthRange(year, month)
  const windowStart = new Date(`${from}T00:00:00Z`)
  const windowEnd = new Date(`${to}T23:59:59Z`)

  return statements
    .filter((s) => {
      const start = normalizeDateOnly(s.period_start)
      const end = normalizeDateOnly(s.period_end)
      // Include statements without period dates - use invoice_date as fallback
      if (!start || !end) {
        const invoiceDate = normalizeDateOnly(s.invoice_date)
        if (!invoiceDate) return true // Include if no dates at all
        const invDate = new Date(`${invoiceDate}T00:00:00Z`)
        return invDate >= windowStart && invDate <= windowEnd
      }
      const rangeStart = new Date(`${start}T00:00:00Z`)
      const rangeEnd = new Date(`${end}T23:59:59Z`)
      return !(rangeEnd < windowStart || rangeStart > windowEnd)
    })
    .sort((a, b) => new Date(b.uploaded_at || b.created_at || 0) - new Date(a.uploaded_at || a.created_at || 0))
}

function isWithinSelectedMonth(dateInput, year, month) {
  const normalized = normalizeDateOnly(dateInput)
  // Include items without dates - they will show "–" in the UI
  if (!normalized) return true
  const d = new Date(`${normalized}T00:00:00Z`)
  if (Number.isNaN(+d)) return true
  return d.getUTCFullYear() === year && d.getUTCMonth() + 1 === month
}

function inferLatestStatementMonth(statements) {
  if (!Array.isArray(statements) || statements.length === 0) return null
  const filtered = statements.filter((s) => !!s.period_start && !!s.period_end && !!s.uploaded_at)
  if (filtered.length === 0) return null
  const sorted = filtered.sort((a, b) => new Date(b.uploaded_at) - new Date(a.uploaded_at))
  const pick = sorted[0]
  try {
    const d = new Date(pick.period_end)
    return { year: d.getUTCFullYear(), month: d.getUTCMonth() + 1 }
  } catch {
    return null
  }
}

export default function ManualMatch() {
  const [year, setYear] = useState(null)
  const [month, setMonth] = useState(null)
  const [statements, setStatements] = useState([])
  const [fcItems, setFcItems] = useState([])
  const [receipts, setReceipts] = useState([])

  const [selectedItemId, setSelectedItemId] = useState(null)
  const [selectedReceiptId, setSelectedReceiptId] = useState(null)

  const [loadingStatements, setLoadingStatements] = useState(false)
  const [loadingLeft, setLoadingLeft] = useState(false)
  const [loadingRight, setLoadingRight] = useState(false)
  const [matching, setMatching] = useState(false)
  const [banner, setBanner] = useState(null)
  const [filterStatus, setFilterStatus] = useState('all') // 'all', 'matched', 'unmatched'
  const [linesPage, setLinesPage] = useState(1)
  const [receiptsPage, setReceiptsPage] = useState(1)
  const [linesPerPage, setLinesPerPage] = useState(15)
  const [receiptsPerPage, setReceiptsPerPage] = useState(15)

  const [fcSortColumn, setFcSortColumn] = useState('purchase_date')
  const [fcSortDirection, setFcSortDirection] = useState('asc')
  const [receiptSortColumn, setReceiptSortColumn] = useState('purchase_datetime')
  const [receiptSortDirection, setReceiptSortDirection] = useState('asc')

  const [isReceiptModalOpen, setReceiptModalOpen] = useState(false)
  const [previewReceipt, setPreviewReceipt] = useState(null)
  const [confirmModalOpen, setConfirmModalOpen] = useState(false)

  const lastFetchKeyRef = useRef(null)
  const dismissBanner = useCallback(() => setBanner(null), [])
  const showError = useCallback((message) => setBanner({ type: 'error', message }), [])
  const showSuccess = useCallback((message) => setBanner({ type: 'success', message }), [])

  const monthKey = useMemo(() => {
    if (!year || !month) return null
    return `${year}-${String(month).padStart(2, '0')}`
  }, [year, month])

  const canMatch = Boolean(selectedItemId && selectedReceiptId && !matching)

  // Selected item and receipt for confirmation modal
  const selectedItem = useMemo(() => {
    if (!selectedItemId) return null
    return fcItems.find((i) => i.id === selectedItemId) || null
  }, [fcItems, selectedItemId])

  const selectedReceipt = useMemo(() => {
    if (!selectedReceiptId) return null
    return receipts.find((r) => r.id === selectedReceiptId) || null
  }, [receipts, selectedReceiptId])

  const matchedReceiptIds = useMemo(() => {
    const ids = new Set()
    fcItems.forEach((item) => {
      if (item.matched_receipt_id) {
        ids.add(item.matched_receipt_id)
      }
    })
    return ids
  }, [fcItems])

  // Sort handlers
  const handleFcSort = useCallback((column) => {
    if (fcSortColumn === column) {
      setFcSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setFcSortColumn(column)
      setFcSortDirection('asc')
    }
  }, [fcSortColumn])

  const handleReceiptSort = useCallback((column) => {
    if (receiptSortColumn === column) {
      setReceiptSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setReceiptSortColumn(column)
      setReceiptSortDirection('asc')
    }
  }, [receiptSortColumn])

  // Sorted and Filtered FC items
  const sortedFcItems = useMemo(() => {
    let items = [...fcItems]

    // Filter
    if (filterStatus === 'matched') {
      items = items.filter(i => i.matched !== 0)
    } else if (filterStatus === 'unmatched') {
      items = items.filter(i => i.matched === 0)
    }

    if (!fcSortColumn) return items

    return items.sort((a, b) => {
      let aVal, bVal

      switch (fcSortColumn) {
        case 'purchase_date':
          aVal = normalizeDateOnly(a.purchase_date) || ''
          bVal = normalizeDateOnly(b.purchase_date) || ''
          break
        case 'merchant_name':
          aVal = (a.merchant_name || '').toLowerCase()
          bVal = (b.merchant_name || '').toLowerCase()
          break
        case 'amount_sek':
          aVal = resolveFcSek(a) ?? 0
          bVal = resolveFcSek(b) ?? 0
          break
        case 'currency':
          aVal = (resolveFcCurrency(a) || '').toLowerCase()
          bVal = (resolveFcCurrency(b) || '').toLowerCase()
          break
        case 'amount_original':
          aVal = resolveFcOriginal(a) ?? 0
          bVal = resolveFcOriginal(b) ?? 0
          break
        case 'status':
          aVal = a.matched !== 0 ? 1 : 0
          bVal = b.matched !== 0 ? 1 : 0
          break
        default:
          return 0
      }

      if (aVal < bVal) return fcSortDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return fcSortDirection === 'asc' ? 1 : -1
      return 0
    })
  }, [fcItems, fcSortColumn, fcSortDirection, filterStatus])

  // Sorted and Filtered Receipts
  const sortedReceipts = useMemo(() => {
    let items = [...receipts]

    // Filter
    if (filterStatus === 'matched') {
      items = items.filter(r => matchedReceiptIds.has(r.id))
    } else if (filterStatus === 'unmatched') {
      items = items.filter(r => !matchedReceiptIds.has(r.id))
    }

    if (!receiptSortColumn) return items

    return items.sort((a, b) => {
      let aVal, bVal

      switch (receiptSortColumn) {
        case 'purchase_datetime':
          aVal = a.purchase_datetime || a.purchase_date || ''
          bVal = b.purchase_datetime || b.purchase_date || ''
          break
        case 'company':
          aVal = (a.merchant || a.company || '').toLowerCase()
          bVal = (b.merchant || b.company || '').toLowerCase()
          break
        case 'gross_amount':
          aVal = resolveReceiptSek(a) ?? 0
          bVal = resolveReceiptSek(b) ?? 0
          break
        case 'currency':
          aVal = (resolveReceiptCurrency(a) || '').toLowerCase()
          bVal = (resolveReceiptCurrency(b) || '').toLowerCase()
          break
        case 'gross_amount_original':
          aVal = resolveReceiptOriginal(a) ?? 0
          bVal = resolveReceiptOriginal(b) ?? 0
          break
        case 'status':
          aVal = matchedReceiptIds.has(a.id) ? 1 : 0
          bVal = matchedReceiptIds.has(b.id) ? 1 : 0
          break
        default:
          return 0
      }

      if (aVal < bVal) return receiptSortDirection === 'asc' ? -1 : 1
      if (aVal > bVal) return receiptSortDirection === 'asc' ? 1 : -1
      return 0
    })
  }, [receipts, receiptSortColumn, receiptSortDirection, filterStatus, matchedReceiptIds])

  const totalLinePages = useMemo(
    () => Math.max(1, Math.ceil(sortedFcItems.length / linesPerPage)),
    [sortedFcItems.length, linesPerPage]
  )
  const totalReceiptPages = useMemo(
    () => Math.max(1, Math.ceil(sortedReceipts.length / receiptsPerPage)),
    [sortedReceipts.length, receiptsPerPage]
  )

  const visibleFcItems = useMemo(() => {
    const start = (linesPage - 1) * linesPerPage
    return sortedFcItems.slice(start, start + linesPerPage)
  }, [sortedFcItems, linesPage, linesPerPage])

  const visibleReceipts = useMemo(() => {
    const start = (receiptsPage - 1) * receiptsPerPage
    return sortedReceipts.slice(start, start + receiptsPerPage)
  }, [sortedReceipts, receiptsPage, receiptsPerPage])

  const fcRangeLabel = useMemo(() => {
    if (!sortedFcItems.length) return '0 av 0'
    const start = (linesPage - 1) * linesPerPage + 1
    const end = Math.min(sortedFcItems.length, start + linesPerPage - 1)
    return `${start}-${end} av ${sortedFcItems.length}`
  }, [sortedFcItems.length, linesPage, linesPerPage])

  const receiptRangeLabel = useMemo(() => {
    if (!sortedReceipts.length) return '0 av 0'
    const start = (receiptsPage - 1) * receiptsPerPage + 1
    const end = Math.min(sortedReceipts.length, start + receiptsPerPage - 1)
    return `${start}-${end} av ${sortedReceipts.length}`
  }, [sortedReceipts.length, receiptsPage, receiptsPerPage])

  const goToPrevLinesPage = useCallback(() => setLinesPage((prev) => Math.max(1, prev - 1)), [])
  const goToNextLinesPage = useCallback(
    () => setLinesPage((prev) => Math.min(totalLinePages, prev + 1)),
    [totalLinePages]
  )
  const goToPrevReceiptsPage = useCallback(() => setReceiptsPage((prev) => Math.max(1, prev - 1)), [])
  const goToNextReceiptsPage = useCallback(
    () => setReceiptsPage((prev) => Math.min(totalReceiptPages, prev + 1)),
    [totalReceiptPages]
  )

  useEffect(() => {
    setLinesPage((prev) => Math.min(prev, totalLinePages) || 1)
  }, [totalLinePages])

  useEffect(() => {
    setReceiptsPage((prev) => Math.min(prev, totalReceiptPages) || 1)
  }, [totalReceiptPages])

  useEffect(() => {
    setLinesPage(1)
  }, [monthKey, filterStatus, fcSortColumn, fcSortDirection, linesPerPage, fcItems.length])

  useEffect(() => {
    setReceiptsPage(1)
  }, [monthKey, filterStatus, receiptSortColumn, receiptSortDirection, receiptsPerPage, receipts.length])

  useEffect(() => {
    if (selectedItemId && !fcItems.some((item) => item.id === selectedItemId)) {
      setSelectedItemId(null)
    }
  }, [fcItems, selectedItemId])

  useEffect(() => {
    if (selectedReceiptId && !receipts.some((r) => r.id === selectedReceiptId)) {
      setSelectedReceiptId(null)
    }
  }, [receipts, selectedReceiptId])

  // Fetch statements
  const fetchStatements = useCallback(async () => {
    setLoadingStatements(true)
    try {
      const res = await api.fetch('/ai/api/reconciliation/firstcard/statements')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      const list = parseStatementsPayload(data)
      setStatements(list)

      if (year == null || month == null) {
        const inferred = inferLatestStatementMonth(list)
        if (inferred) {
          setYear(inferred.year)
          setMonth(inferred.month)
        } else {
          const now = new Date()
          setYear(now.getUTCFullYear())
          setMonth(now.getUTCMonth() + 1)
        }
      }
    } catch (err) {
      console.error('Failed to fetch statements', err)
      showError('Kunde inte hämta FC-statements.')
    } finally {
      setLoadingStatements(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const resolveStatementsForMonth = useCallback(() => {
    return collectStatementsForMonth(statements, year, month)
  }, [statements, year, month])

  // Load FC items (invoice items/transactions)
  // Fetches from ALL statements, then filters by transaction_date within selected month
  const loadFcItems = useCallback(async (options = {}) => {
    if (!year || !month) return
    const { force = false } = options

    // Use ALL statements, not filtered by period
    const allStatements = Array.isArray(statements) ? statements : []
    const statementKey = allStatements.map((s) => s.id).join(',')
    const fetchKey = `items-${year}-${month}-${statementKey || 'none'}`
    if (!force && lastFetchKeyRef.current === fetchKey) return

    if (allStatements.length === 0) {
      setFcItems([])
      lastFetchKeyRef.current = fetchKey
      return
    }

    setLoadingLeft(true)
    setSelectedItemId(null)
    try {
      const responses = await Promise.all(
        allStatements.map(async (statement) => {
          const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${statement.id}`)
          if (!res.ok) throw new Error(`HTTP ${res.status}`)
          const data = await res.json()
          const items = Array.isArray(data?.items)
            ? data.items
            : Array.isArray(data?.lines)
              ? data.lines
              : []
          return items.map((item) => (item.invoice_id ? item : { ...item, invoice_id: statement.id }))
        })
      )

      // Filter transactions by their actual transaction_date within selected month
      const { from, to } = monthRange(year, month)
      const rangeStart = new Date(`${from}T00:00:00Z`)
      const rangeEnd = new Date(`${to}T23:59:59Z`)

      const filteredItems = responses
        .flat()
        .filter((item) => {
          const dateCandidate = item.transaction_date || item.purchase_date || item.purchase_datetime
          const normalized = normalizeDateOnly(dateCandidate)
          if (!normalized) return true // Include items without date
          const d = new Date(`${normalized}T00:00:00Z`)
          return d >= rangeStart && d <= rangeEnd
        })
        .sort((a, b) => {
          const da = normalizeDateOnly(a.transaction_date || a.purchase_date || a.purchase_datetime) || ''
          const db = normalizeDateOnly(b.transaction_date || b.purchase_date || b.purchase_datetime) || ''
          if (da !== db) return da.localeCompare(db)
          return String(a.id).localeCompare(String(b.id))
        })

      setFcItems(filteredItems)
      lastFetchKeyRef.current = fetchKey
    } catch (err) {
      console.error('Failed to load FC items', err)
      showError('Kunde inte hämta FC-transaktioner.')
      setFcItems([])
    } finally {
      setLoadingLeft(false)
    }
  }, [year, month, statements])

  // Load receipts
  const loadReceipts = useCallback(async () => {
    if (!year || !month) return
    setLoadingRight(true)
    setSelectedReceiptId(null)
    try {
      const { from, to } = monthRange(year, month)
      const pageSize = 100
      const aggregated = []
      let page = 1
      let total = Infinity

      while ((page - 1) * pageSize < total) {
        const params = new URLSearchParams({
          from,
          to: `${to} 23:59:59`,
          page: String(page),
          page_size: String(pageSize),
        })
        const apiSortBy = ['purchase_datetime', 'company', 'gross_amount'].includes(receiptSortColumn)
          ? receiptSortColumn
          : null
        if (apiSortBy) params.set('sort_by', apiSortBy)
        if (receiptSortDirection) params.set('sort_order', receiptSortDirection)
        // Use backend filter for unmatched receipts (more efficient than client-side)
        if (filterStatus === 'unmatched') {
          params.set('match_status', 'unmatched')
        }
        const res = await api.fetch(`/ai/api/receipts?${params.toString()}`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()

        let chunk = []
        if (Array.isArray(data?.items)) {
          chunk = data.items
        } else if (Array.isArray(data)) {
          chunk = data
        }
        aggregated.push(...chunk)

        const metaTotal = Number(data?.meta?.total)
        if (Number.isFinite(metaTotal)) {
          total = metaTotal
        } else if (chunk.length < pageSize) {
          break
        }

        if (chunk.length < pageSize) {
          break
        }
        page += 1
      }

      const filtered = aggregated.filter(item => {
        const wf = (item.workflow_type || '').toLowerCase()
        const ft = (item.file_type || '').toLowerCase()
        if (wf === 'creditcard_invoice') return false
        if (ft.startsWith('cc_') || ft === 'credit_card') return false
        const purchaseDate = item.purchase_datetime || item.purchase_date
        return isWithinSelectedMonth(purchaseDate, year, month)
      })

      setReceipts(filtered)
    } catch (err) {
      console.error('Failed to load receipts', err)
      showError('Kunde inte hämta kvitton.')
      setReceipts([])
    } finally {
      setLoadingRight(false)
    }
  }, [year, month, receiptSortColumn, receiptSortDirection, filterStatus])

  // Handle match - uses PUT endpoint for manual matching
  const handleMatch = useCallback(async () => {
    if (!canMatch) return
    setMatching(true)
    setConfirmModalOpen(false)
    try {
      const item = fcItems.find((i) => i.id === selectedItemId)
      if (!item) {
        showError('Kunde inte hitta vald transaktion.')
        return
      }

      // Correct endpoint: PUT /lines/<line_id>
      // Correct payload: { matched_file_id, invoice_id }
      const res = await api.fetch(`/ai/api/reconciliation/firstcard/lines/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          matched_file_id: selectedReceiptId,
          invoice_id: item.invoice_id || null,
        }),
      })

      if (res.ok) {
        showSuccess('Matchning genomförd!')
        await Promise.all([loadFcItems({ force: true }), loadReceipts()])
        setSelectedItemId(null)
        setSelectedReceiptId(null)
      } else {
        const errorData = await res.json().catch(() => ({}))
        // Handle specific error codes
        if (errorData.reason === 'receipt_in_use') {
          showError('Detta kvitto/faktura är redan matchat mot en annan rad.')
        } else if (errorData.reason === 'line_state_conflict') {
          showError('Raden kan inte matchas i nuvarande status.')
        } else {
          showError(errorData.error || errorData.reason || 'Matchning misslyckades.')
        }
      }
    } catch (err) {
      console.error('Match error', err)
      showError('Matchning misslyckades.')
    } finally {
      setMatching(false)
    }
  }, [canMatch, fcItems, selectedItemId, selectedReceiptId, loadFcItems, loadReceipts])

  const handleDeleteReceipt = useCallback(async (id) => {
    if (!window.confirm('Är du säker på att du vill radera detta kvitto?')) return
    try {
      const res = await api.fetch(`/ai/api/receipts/${id}`, { method: 'DELETE' })
      if (res.ok) {
        showSuccess('Kvitto raderat')
        // Remove locally
        setReceipts(prev => prev.filter(r => r.id !== id))
        if (selectedReceiptId === id) setSelectedReceiptId(null)
      } else {
        showError('Kunde inte radera kvitto')
      }
    } catch (err) {
      console.error('Delete error', err)
      showError('Ett fel inträffade vid radering')
    }
  }, [selectedReceiptId])

  // Modal handlers
  const openReceiptModal = useCallback((receiptId) => {
    const target = receipts.find((r) => r.id === receiptId)
    if (!target) {
      showError('Kunde inte hitta kvittot.')
      return
    }
    setPreviewReceipt(target)
    setReceiptModalOpen(true)
  }, [receipts])

  const closeReceiptModal = useCallback(() => {
    setReceiptModalOpen(false)
    setPreviewReceipt(null)
  }, [])

  const handleReceiptUpdate = useCallback((updated) => {
    if (!updated || !updated.id) return

    if (updated.deleted) {
      // Find current index before removing
      const currentIndex = receipts.findIndex(item => item.id === updated.id)

      // Remove from receipts list
      setReceipts((prev) => prev.filter((item) => item.id !== updated.id))

      // Clear selection if this receipt was selected for matching
      if (selectedReceiptId === updated.id) {
        setSelectedReceiptId(null)
      }

      // Handle navigation after deletion
      if (updated.shouldNavigateNext && currentIndex >= 0) {
        // Get the new list after deletion (simulated)
        const newList = receipts.filter(item => item.id !== updated.id)

        // The next receipt will now be at the same index as the deleted one
        if (currentIndex < newList.length) {
          const nextReceipt = newList[currentIndex]
          setPreviewReceipt(nextReceipt)
        } else {
          // No more receipts, close modal
          closeReceiptModal()
        }
      } else {
        // No navigation needed, just close modal
        closeReceiptModal()
      }
    } else {
      setReceipts((prev) => prev.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)))
    }
  }, [selectedReceiptId, receipts, closeReceiptModal])

  // Modal navigation
  const currentReceiptIndex = useMemo(() => {
    if (!previewReceipt) return -1
    return receipts.findIndex(item => item.id === previewReceipt.id)
  }, [receipts, previewReceipt])

  const handleNavigateNext = useCallback(() => {
    if (currentReceiptIndex >= 0 && currentReceiptIndex < receipts.length - 1) {
      const nextReceipt = receipts[currentReceiptIndex + 1]
      setPreviewReceipt(nextReceipt)
    }
  }, [currentReceiptIndex, receipts])

  const handleNavigatePrevious = useCallback(() => {
    if (currentReceiptIndex > 0) {
      const prevReceipt = receipts[currentReceiptIndex - 1]
      setPreviewReceipt(prevReceipt)
    }
  }, [currentReceiptIndex, receipts])

  const hasNext = currentReceiptIndex >= 0 && currentReceiptIndex < receipts.length - 1
  const hasPrevious = currentReceiptIndex > 0

  // Effects
  useEffect(() => {
    fetchStatements()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (monthKey) {
      loadFcItems()
      loadReceipts()
    }
  }, [monthKey, loadFcItems, loadReceipts])

  // Options
  const monthOptions = useMemo(() => {
    const base = []
    for (let m = 1; m <= 12; m += 1) {
      const date = new Date(2024, m - 1, 1)
      const label = new Intl.DateTimeFormat('sv-SE', { month: 'long' }).format(date)
      base.push({ value: m, label: label.charAt(0).toUpperCase() + label.slice(1) })
    }
    return base
  }, [])

  const yearOptions = useMemo(() => {
    const ys = new Set()
    const nowY = new Date().getFullYear()
    for (let d = -2; d <= 2; d += 1) ys.add(nowY + d)
    statements.forEach((s) => {
      try {
        ys.add(new Date(s.period_end).getUTCFullYear())
      } catch {
        /* ignore */
      }
    })
    return Array.from(ys).sort((a, b) => b - a)
  }, [statements])

  return (
    <div className="page-container">
      {banner && (
        <div className={`alert alert-${banner.type}`}>
          <div className="alert-icon">
            {banner.type === 'error' ? <FiAlertTriangle /> : <FiCheckCircle />}
          </div>
          <div className="alert-message">{banner.message}</div>
          <button type="button" className="alert-dismiss" onClick={dismissBanner}>×</button>
        </div>
      )}

      {/* Period Selection */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Välj period</h3>
            <p className="card-subtitle">Välj månad för att se FirstCard-transaktioner och kvitton</p>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-300">År</label>
              <select
                className="dm-input w-32"
                value={year ?? ''}
                onChange={(e) => setYear(Number(e.target.value))}
                disabled={loadingStatements}
              >
                <option value="" disabled>Välj år</option>
                {yearOptions.map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-300">Månad</label>
              <select
                className="dm-input w-40"
                value={month ?? ''}
                onChange={(e) => setMonth(Number(e.target.value))}
                disabled={loadingStatements}
              >
                <option value="" disabled>Välj månad</option>
                {monthOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {monthKey && (
              <div className="text-sm text-gray-400 ml-2">
                Period: {monthKey}
              </div>
            )}
          </div>

          <div className="flex-1 flex justify-center lg:justify-end items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-300">Visa</label>
              <select
                className="dm-input w-40"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="all">Alla</option>
                <option value="matched">Matchade</option>
                <option value="unmatched">Ej matchade</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Two columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: FC Items */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">FirstCard-transaktioner</h3>
              <p className="card-subtitle">
                {loadingLeft ? 'Laddar...' : `${fcItems.length} transaktioner`}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 px-4 pb-3 text-sm text-gray-300">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-gray-400">Visar {fcRangeLabel}</span>
              <PageSizeSelector label="Per sida" value={linesPerPage} onChange={setLinesPerPage} />
            </div>
            <PaginationControls
              page={linesPage}
              totalPages={totalLinePages}
              onPrev={goToPrevLinesPage}
              onNext={goToNextLinesPage}
              label={`Sida ${linesPage} av ${totalLinePages}`}
            />
          </div>

          <div className="overflow-hidden border border-gray-700 rounded-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
                  <tr>
                    <th className="px-4 py-3 w-12">Välj</th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleFcSort('purchase_date')}>
                      <div className="flex items-center gap-1">
                        Datum
                        {fcSortColumn === 'purchase_date' && (
                          <span>{fcSortDirection === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleFcSort('merchant_name')}>
                      <div className="flex items-center gap-1">
                        Företag
                        {fcSortColumn === 'merchant_name' && (
                          <span>{fcSortDirection === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleFcSort('amount_sek')}>
                      <div className="flex items-center gap-1">
                        SEK
                        {fcSortColumn === 'amount_sek' && (
                          <span>{fcSortDirection === 'asc' ? '' : ''}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleFcSort('currency')}>
                      <div className="flex items-center gap-1">
                        Valuta
                        {fcSortColumn === 'currency' && (
                          <span>{fcSortDirection === 'asc' ? '' : ''}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleFcSort('amount_original')}>
                      <div className="flex items-center gap-1">
                        Belopp
                        {fcSortColumn === 'amount_original' && (
                          <span>{fcSortDirection === 'asc' ? '' : ''}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleFcSort('status')}>
                      <div className="flex items-center gap-1">
                        Status
                        {fcSortColumn === 'status' && (
                          <span>{fcSortDirection === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {sortedFcItems.length === 0 && !loadingLeft ? (
                    <tr className="border-t border-gray-700">
                      <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                        Inga transaktioner för vald period.
                      </td>
                    </tr>
                  ) : (
                    visibleFcItems.map((item) => {
                      const isMatched = item.matched !== 0
                      const checked = selectedItemId === item.id
                      const canSelect = !isMatched
                      const fcCurrency = resolveFcCurrency(item)
                      const fcSek = resolveFcSek(item)
                      const fcOriginal = resolveFcOriginal(item)

                      return (
                        <tr key={item.id} className={`border-t border-gray-700 ${canSelect ? 'hover:bg-gray-800/30' : 'opacity-60'}`}>
                          <td className="px-4 py-3 align-top">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => canSelect && setSelectedItemId(checked ? null : item.id)}
                              disabled={!canSelect}
                              className={canSelect ? 'cursor-pointer' : 'cursor-not-allowed'}
                            />
                          </td>
                          <td className="px-4 py-3 text-gray-200 whitespace-nowrap align-top">
                            {formatDate(item.purchase_date)}
                          </td>
                          <td className="px-4 py-3 text-gray-100 align-top">
                            <div className="font-medium">{item.merchant_name || '-'}</div>
                            <div className="text-xs text-gray-400">ID: {item.id}</div>
                          </td>
                          <td className="px-4 py-3 text-gray-100 whitespace-nowrap align-top">
                            {fcSek != null ? formatAmount(fcSek, 'SEK') : '-'}
                          </td>
                          <td className="px-4 py-3 text-gray-100 whitespace-nowrap align-top">
                            {fcCurrency || '-'}
                          </td>
                          <td className="px-4 py-3 text-gray-100 whitespace-nowrap align-top">
                            {fcOriginal != null && fcCurrency
                              ? formatAmount(fcOriginal, fcCurrency)
                              : fcOriginal != null
                                ? formatAmount(fcOriginal, 'SEK')
                                : '-'}
                          </td>
                          <td className="px-4 py-3 align-top">
                            <span className={`status-badge ${isMatched ? 'status-passed' : 'status-pending'}`}>
                              {isMatched ? 'Matchad' : 'Ej matchad'}
                            </span>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right: Receipts */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Kvitton</h3>
              <p className="card-subtitle">
                {loadingRight ? 'Laddar...' : `${receipts.length} kvitton`}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 px-4 pb-3 text-sm text-gray-300">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-gray-400">Visar {receiptRangeLabel}</span>
              <PageSizeSelector label="Per sida" value={receiptsPerPage} onChange={setReceiptsPerPage} />
            </div>
            <PaginationControls
              page={receiptsPage}
              totalPages={totalReceiptPages}
              onPrev={goToPrevReceiptsPage}
              onNext={goToNextReceiptsPage}
              label={`Sida ${receiptsPage} av ${totalReceiptPages}`}
            />
          </div>

          <div className="overflow-hidden border border-gray-700 rounded-lg">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800 text-left text-gray-300 uppercase text-xs tracking-wide">
                  <tr>
                    <th className="px-4 py-3 w-12">Välj</th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleReceiptSort('purchase_datetime')}>
                      <div className="flex items-center gap-1">
                        Datum
                        {receiptSortColumn === 'purchase_datetime' && (
                          <span>{receiptSortDirection === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleReceiptSort('company')}>
                      <div className="flex items-center gap-1">
                        Företag
                        {receiptSortColumn === 'company' && (
                          <span>{receiptSortDirection === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleReceiptSort('gross_amount')}>
                      <div className="flex items-center gap-1">
                        SEK
                        {receiptSortColumn === 'gross_amount' && (
                          <span>{receiptSortDirection === 'asc' ? '' : ''}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleReceiptSort('currency')}>
                      <div className="flex items-center gap-1">
                        Valuta
                        {receiptSortColumn === 'currency' && (
                          <span>{receiptSortDirection === 'asc' ? '' : ''}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleReceiptSort('gross_amount_original')}>
                      <div className="flex items-center gap-1">
                        Belopp
                        {receiptSortColumn === 'gross_amount_original' && (
                          <span>{receiptSortDirection === 'asc' ? '' : ''}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 cursor-pointer hover:bg-gray-700" onClick={() => handleReceiptSort('status')}>
                      <div className="flex items-center gap-1">
                        Status
                        {receiptSortColumn === 'status' && (
                          <span>{receiptSortDirection === 'asc' ? '↑' : '↓'}</span>
                        )}
                      </div>
                    </th>
                    <th className="px-4 py-3 text-center">Åtgärd</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedReceipts.length === 0 && !loadingRight ? (
                    <tr className="border-t border-gray-700">
                      <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                        Inga kvitton för vald period.
                      </td>
                    </tr>
                  ) : (
                    visibleReceipts.map((r) => {
                      const checked = selectedReceiptId === r.id
                      const isMatched = matchedReceiptIds.has(r.id)
                      const selectable = !isMatched
                      const showMatchButton = checked && canMatch
                      const receiptCurrency = resolveReceiptCurrency(r)
                      const receiptSek = resolveReceiptSek(r)
                      const receiptOriginal = resolveReceiptOriginal(r)

                      return (
                        <tr key={r.id} className="border-t border-gray-700 hover:bg-gray-800/30">
                          <td className="px-4 py-3 align-top">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => selectable && setSelectedReceiptId(checked ? null : r.id)}
                              className={selectable ? 'cursor-pointer' : 'cursor-not-allowed'}
                              disabled={!selectable}
                            />
                          </td>
                          <td className="px-4 py-3 text-gray-200 whitespace-nowrap align-top">
                            {formatDate(r.purchase_datetime || r.purchase_date)}
                          </td>
                          <td className="px-4 py-3 text-gray-100 align-top">
                            <div className="font-medium">{r.merchant || r.company || '-'}</div>
                            <div className="text-xs text-gray-400">{r.orgnr || ''}</div>
                          </td>
                          <td className="px-4 py-3 text-gray-100 whitespace-nowrap align-top">
                            {receiptSek != null ? formatAmount(receiptSek, 'SEK') : '-'}
                          </td>
                          <td className="px-4 py-3 text-gray-100 whitespace-nowrap align-top">
                            {receiptCurrency || '-'}
                          </td>
                          <td className="px-4 py-3 text-gray-100 whitespace-nowrap align-top">
                            {receiptOriginal != null && receiptCurrency
                              ? formatAmount(receiptOriginal, receiptCurrency)
                              : receiptOriginal != null
                                ? formatAmount(receiptOriginal, 'SEK')
                                : '-'}
                          </td>
                          <td className="px-4 py-3 align-top">
                            <span className={`status-badge ${isMatched ? 'status-passed' : 'status-pending'}`}>
                              {isMatched ? 'Matchad' : 'Ej matchad'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center align-top">
                            <div className="flex items-center justify-end gap-2">
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={() => openReceiptModal(r.id)}
                                title="Visa"
                              >
                                <FiEye />
                              </button>
                              <button
                                type="button"
                                className={`btn btn-sm ${showMatchButton ? 'btn-primary' : 'btn-secondary opacity-50 cursor-not-allowed'}`}
                                onClick={() => setConfirmModalOpen(true)}
                                disabled={!showMatchButton}
                                title="Matcha"
                              >
                                Matcha
                              </button>
                              <button
                                type="button"
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDeleteReceipt(r.id)}
                                title="Radera"
                              >
                                Radera
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <ReceiptPreviewModal
        open={isReceiptModalOpen}
        receipt={previewReceipt}
        previewImage={null}
        onClose={closeReceiptModal}
        onReceiptUpdate={handleReceiptUpdate}
        onNavigateNext={handleNavigateNext}
        onNavigatePrevious={handleNavigatePrevious}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
      />

      {/* Confirmation Modal */}
      {confirmModalOpen && selectedItem && selectedReceipt && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-lg shadow-xl max-w-lg w-full mx-4">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Vill du matcha dessa?</h3>

              <div className="grid grid-cols-2 gap-4 mb-6">
                {/* Left: FC Transaction */}
                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="text-xs uppercase tracking-wide text-gray-400 mb-2">Korttransaktion</div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Datum:</span>
                      <span className="text-gray-100">{formatDate(selectedItem.purchase_date) || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Belopp:</span>
                      <span className="text-gray-100">{formatAmount(selectedItem.amount_original || selectedItem.gross_amount, selectedItem.currency_original)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Beskrivning:</span>
                      <span className="text-gray-100 truncate max-w-32">{selectedItem.merchant_name || selectedItem.description || '-'}</span>
                    </div>
                  </div>
                </div>

                {/* Right: Receipt/Invoice */}
                <div className="bg-gray-800 rounded-lg p-4">
                  <div className="text-xs uppercase tracking-wide text-gray-400 mb-2">
                    {selectedReceipt.file_type === 'invoice' ? 'Faktura' : 'Kvitto'}
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Datum:</span>
                      <span className="text-gray-100">{formatDate(selectedReceipt.purchase_datetime || selectedReceipt.purchase_date) || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Belopp:</span>
                      <span className="text-gray-100">{formatAmount(Number(selectedReceipt.gross_amount || selectedReceipt.total_gross || 0))}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Leverantor:</span>
                      <span className="text-gray-100 truncate max-w-32">{selectedReceipt.merchant || selectedReceipt.company || selectedReceipt.filename || '-'}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setConfirmModalOpen(false)}
                  disabled={matching}
                >
                  Avbryt
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleMatch}
                  disabled={matching}
                >
                  {matching ? 'Matchar...' : 'Matcha'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
