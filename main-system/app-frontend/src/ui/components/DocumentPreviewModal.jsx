import React from 'react'
import { FiX, FiChevronLeft, FiChevronRight, FiMaximize, FiMinimize } from 'react-icons/fi'
import { api } from '../api'

/**
 * DocumentPreviewModal
 *
 * A lightweight preview modal for FirstCard invoices. It focuses purely on rendering
 * the largest possible page image, with pagination and zoom controls.
 *
 * The backend is expected to return `invoice.pages` (or `invoice.metadata.pages`) where each page contains:
 *   - file_id: string
 *   - page_number: number
 *   - url: string (preferred)
 *
 * If `url` is missing, this component falls back to the receipt image endpoint using `file_id`.
 */
export default function DocumentPreviewModal({ open, documentId, onClose }) {
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState(null)
  const [pages, setPages] = React.useState([])
  const [currentPageIndex, setCurrentPageIndex] = React.useState(0)
  const [zoom, setZoom] = React.useState(1)

  const resolvePageUrl = React.useCallback((page) => {
    if (!page) return null
    if (page.url) return page.url
    const fileId = page.file_id || page.id
    if (!fileId) return null
    return `/ai/api/receipts/${fileId}/image?size=original&quality=high`
  }, [])

  React.useEffect(() => {
    if (!open || !documentId) {
      setPages([])
      setCurrentPageIndex(0)
      setZoom(1)
      setError(null)
      return
    }

    const fetchPages = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${documentId}`)
        if (!res.ok) throw new Error(`Status ${res.status}`)

        const data = await res.json()
        const invoicePages = data?.invoice?.pages || data?.invoice?.metadata?.pages || []
        const normalized = Array.isArray(invoicePages)
          ? invoicePages
              .map((p, idx) => ({
                ...p,
                page_number: p.page_number || idx + 1,
                url: resolvePageUrl(p),
              }))
              .filter((p) => !!p.url)
              .sort((a, b) => (a.page_number || 0) - (b.page_number || 0))
          : []

        if (!normalized.length) {
          setPages([])
          setError('Inga sidor hittades för detta dokument.')
        } else {
          setPages(normalized)
          setCurrentPageIndex(0)
          setZoom(1)
        }
      } catch (err) {
        console.error('Failed to load document pages', err)
        setPages([])
        setError('Kunde inte ladda dokumentet.')
      } finally {
        setLoading(false)
      }
    }

    fetchPages()
  }, [open, documentId, resolvePageUrl])

  if (!open) return null

  const hasMultiplePages = pages.length > 1
  const currentPage = pages[currentPageIndex]
  const currentUrl = resolvePageUrl(currentPage)

  const goPrev = () => setCurrentPageIndex((idx) => Math.max(0, idx - 1))
  const goNext = () => setCurrentPageIndex((idx) => Math.min(pages.length - 1, idx + 1))

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-label="Dokumentgranskning">
      <div
        className="w-full h-full max-w-6xl max-h-[90vh] flex flex-col p-0 overflow-hidden bg-gray-800 rounded-lg shadow-2xl border border-gray-700"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
          <div className="text-white font-medium">
            Dokumentgranskning {hasMultiplePages && `(${currentPageIndex + 1} / ${pages.length})`}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))}
              className="icon-button"
              aria-label="Zoom out"
            >
              <FiMinimize />
            </button>
            <span className="text-xs text-gray-400 w-12 text-center">{Math.round(zoom * 100)}%</span>
            <button
              type="button"
              onClick={() => setZoom((z) => Math.min(4, z + 0.25))}
              className="icon-button"
              aria-label="Zoom in"
            >
              <FiMaximize />
            </button>
            <div className="w-px h-6 bg-gray-700 mx-2" />
            <button type="button" onClick={onClose} className="icon-button" aria-label="Stäng">
              <FiX className="mr-1" />
              <span>Stäng</span>
            </button>
          </div>
        </div>

        <div className="flex-1 relative bg-gray-900 overflow-auto flex items-center justify-center p-4">
          {loading ? (
            <div className="loading-spinner" />
          ) : error ? (
            <div className="text-gray-300 p-6">{error}</div>
          ) : !currentUrl ? (
            <div className="text-gray-300 p-6">Kunde inte hitta någon bild att visa.</div>
          ) : (
            <div
              className="relative transition-transform duration-200 ease-out"
              style={{ transform: `scale(${zoom})` }}
            >
              <img
                src={currentUrl}
                alt={`Sida ${currentPageIndex + 1}`}
                className="max-w-full shadow-2xl"
                onError={() => setError('Kunde inte visa bild.')}
              />
            </div>
          )}

          {hasMultiplePages && !loading && !error && (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  goPrev()
                }}
                className="absolute left-4 top-1/2 -translate-y-1/2 icon-button bg-gray-800/80 hover:bg-gray-700/80"
                disabled={currentPageIndex === 0}
                aria-label="Previous page"
              >
                <FiChevronLeft />
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  goNext()
                }}
                className="absolute right-4 top-1/2 -translate-y-1/2 icon-button bg-gray-800/80 hover:bg-gray-700/80"
                disabled={currentPageIndex === pages.length - 1}
                aria-label="Next page"
              >
                <FiChevronRight />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
