import React from 'react'
import { FiX, FiChevronLeft, FiChevronRight, FiMaximize, FiMinimize } from 'react-icons/fi'
import { api } from '../api'

export default function DocumentPreviewModal({
    open,
    documentId,
    onClose,
}) {
    const [loading, setLoading] = React.useState(false)
    const [error, setError] = React.useState(null)
    const [pages, setPages] = React.useState([])
    const [currentPageIndex, setCurrentPageIndex] = React.useState(0)
    const [zoom, setZoom] = React.useState(1)

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
                // Fetch document details to get pages
                // Assuming the endpoint returns a list of pages or we can construct image URLs
                // Adjust this endpoint based on actual API availability for document pages
                const res = await api.fetch(`/ai/api/reconciliation/firstcard/invoices/${documentId}`)
                if (!res.ok) throw new Error(`Status ${res.status}`)

                const data = await res.json()
                // Assuming data.invoice.pages contains the pages or we use a specific endpoint for images
                // If pages are not directly available, we might need to use a different strategy
                // For now, let's assume we can get a list of image URLs or IDs

                // Fallback: If no specific pages array, maybe we can just show the document itself if it's an image
                // or if it's a PDF, we might need a PDF viewer. 
                // Given the requirement "scanned pages", let's assume we have image URLs.

                // MOCKING for now based on typical structure, will need adjustment if API differs
                // If the API returns 'pages' array in the invoice object:
                const invoicePages = data.invoice?.pages || []

                if (invoicePages.length > 0) {
                    setPages(invoicePages)
                } else {
                    // If no pages array, maybe the document itself is the "page"
                    // We can try to construct a URL for the document file
                    setPages([{ id: 'main', url: `/ai/api/reconciliation/firstcard/invoices/${documentId}/file` }])
                }

            } catch (err) {
                console.error('Failed to load document pages', err)
                setError('Kunde inte ladda dokumentet.')
            } finally {
                setLoading(false)
            }
        }

        fetchPages()
    }, [open, documentId])

    const handlePrev = (e) => {
        e.stopPropagation()
        setCurrentPageIndex((prev) => Math.max(0, prev - 1))
    }

    const handleNext = (e) => {
        e.stopPropagation()
        setCurrentPageIndex((prev) => Math.min(pages.length - 1, prev + 1))
    }

    const handleKeyDown = React.useCallback((e) => {
        if (!open) return
        if (e.key === 'ArrowLeft') handlePrev(e)
        if (e.key === 'ArrowRight') handleNext(e)
        if (e.key === 'Escape') onClose()
    }, [open, pages.length])

    React.useEffect(() => {
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [handleKeyDown])

    if (!open) return null

    const currentPage = pages[currentPageIndex]
    const hasMultiplePages = pages.length > 1

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div
                className="modal w-full h-full max-w-6xl max-h-[90vh] flex flex-col p-0 overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
                    <div className="text-white font-medium">
                        Dokumentgranskning {hasMultiplePages && `(${currentPageIndex + 1} / ${pages.length})`}
                    </div>
                    <div className="flex items-center gap-2">
                        <button onClick={() => setZoom(z => Math.max(0.5, z - 0.25))} className="icon-button">
                            <FiMinimize />
                        </button>
                        <span className="text-xs text-gray-400 w-12 text-center">{Math.round(zoom * 100)}%</span>
                        <button onClick={() => setZoom(z => Math.min(3, z + 0.25))} className="icon-button">
                            <FiMaximize />
                        </button>
                        <div className="w-px h-6 bg-gray-700 mx-2" />
                        <button onClick={onClose} className="icon-button">
                            <FiX />
                        </button>
                    </div>
                </div>

                <div className="flex-1 relative bg-gray-900 overflow-auto flex items-center justify-center p-4">
                    {loading ? (
                        <div className="loading-spinner" />
                    ) : error ? (
                        <div className="text-red-400">{error}</div>
                    ) : currentPage ? (
                        <div
                            className="relative transition-transform duration-200 ease-out"
                            style={{ transform: `scale(${zoom})` }}
                        >
                            {/* Assuming page has a 'url' property or we construct it. 
                  If it's a PDF, we might need <embed> or <iframe, but user asked for "scanned pages" implying images.
                  Let's try <img> first. 
              */}
                            <img
                                src={currentPage.url || currentPage.image_url || `/ai/api/files/${currentPage.file_id || currentPage.id}/content`}
                                alt={`Sida ${currentPageIndex + 1}`}
                                className="max-w-full shadow-2xl"
                                onError={(e) => {
                                    // Fallback if image load fails, maybe show a message or try different URL
                                    e.target.style.display = 'none'
                                    e.target.parentNode.innerHTML = '<div class="text-gray-500 p-8">Kunde inte visa bild.</div>'
                                }}
                            />
                        </div>
                    ) : (
                        <div className="text-gray-500">Inga sidor att visa.</div>
                    )}

                    {/* Navigation Overlays */}
                    {hasMultiplePages && (
                        <>
                            <button
                                className={`absolute left-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors ${currentPageIndex === 0 ? 'opacity-30 cursor-not-allowed' : ''}`}
                                onClick={handlePrev}
                                disabled={currentPageIndex === 0}
                            >
                                <FiChevronLeft size={24} />
                            </button>
                            <button
                                className={`absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors ${currentPageIndex === pages.length - 1 ? 'opacity-30 cursor-not-allowed' : ''}`}
                                onClick={handleNext}
                                disabled={currentPageIndex === pages.length - 1}
                            >
                                <FiChevronRight size={24} />
                            </button>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}
