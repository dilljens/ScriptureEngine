import React, { useState, useEffect, useRef } from 'react'

/**
 * VersePreviewCard — shows a scrollable chapter preview with highlighted verse(s).
 *
 * Props:
 *   refs: string | string[] — verse reference(s) like "isa.55.6" or ["isa.55.6", "isa.55.7"]
 *   onNavigate: (book, chapter) => void — called when user clicks to open full chapter
 *   maxHeight?: string — CSS max-height for the scrollable container (default "12rem")
 */
export default function VersePreviewCard({ refs, onNavigate, maxHeight = '12rem', compact }) {
  const [chapterData, setChapterData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

  // Normalize refs to array
  const verseRefs = Array.isArray(refs) ? refs : [refs]
  // Extract unique (book, chapter) pairs
  const locations = {}
  for (const ref of verseRefs) {
    const parts = ref.split('.')
    if (parts.length >= 3) {
      const key = `${parts[0]}.${parts[1]}`
      if (!locations[key]) {
        locations[key] = { book: parts[0], chapter: parseInt(parts[1]), verses: [] }
      }
      locations[key].verses.push(parseInt(parts[2]))
    }
  }

  const locKeys = Object.keys(locations)
  // For now: only handle the first location
  const primary = locKeys.length > 0 ? locations[locKeys[0]] : null
  const highlightVerses = primary ? new Set(primary.verses) : new Set()

  useEffect(() => {
    if (!primary) return
    setLoading(true)
    setError(null)

    fetch(`/api/v1/chapter/${primary.book}.${primary.chapter}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          setChapterData(d.data)
        } else {
          setError(d.detail || 'Failed to load chapter')
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [primary?.book, primary?.chapter])

  // Auto-scroll to first highlighted verse
  useEffect(() => {
    if (!scrollRef.current || !chapterData?.verses || highlightVerses.size === 0) return
    const firstHighlight = chapterData.verses.find(v => highlightVerses.has(v.verse))
    if (!firstHighlight) return
    // Find the DOM element for the highlighted verse
    const el = scrollRef.current.querySelector(`[data-verse="${firstHighlight.verse}"]`)
    if (el) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    }
  }, [chapterData, highlightVerses])

  if (loading) {
    return (
      <div className="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
        <div className="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500">
          <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading {primary?.book}.{primary?.chapter}…
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800 p-3">
        <p className="text-[11px] text-red-600 dark:text-red-400">{error}</p>
      </div>
    )
  }

  if (!chapterData?.verses?.length) return null

  const bookTitle = primary ? `${primary.book} ${primary.chapter}` : ''

  // Build the reference string
  const refSummary = verseRefs.length === 1
    ? verseRefs[0]
    : `${verseRefs[0]}…+${verseRefs.length - 1}`

  return (
    <div className={`bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden shadow-sm ${compact ? 'inline-block' : ''}`}>
      {/* Header */}
      <button onClick={() => onNavigate && primary && onNavigate(primary.book, primary.chapter)}
        className={`w-full flex items-center gap-2 ${compact ? 'px-2 py-1' : 'px-3 py-2'} bg-neutral-50 dark:bg-neutral-800/50
          hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors cursor-pointer text-left border-b border-neutral-200 dark:border-neutral-700`}>
        <span className="text-[11px] font-semibold text-neutral-700 dark:text-neutral-300">📖 {bookTitle}</span>
        <span className="text-[9px] font-mono text-neutral-400 dark:text-neutral-500 ml-auto">
          {refSummary}
        </span>
        <span className="text-[9px] text-blue-600 dark:text-blue-400 shrink-0">↗</span>
      </button>

      {/* Scrollable verses */}
      <div className="overflow-y-auto" style={{ maxHeight }} ref={scrollRef}>
        <div className="px-3 py-1.5 space-y-0.5">
          {chapterData.verses.map(v => {
            const isHighlighted = highlightVerses.has(v.verse)
            return (
              <div key={v.verse} data-verse={v.verse}
                className={`flex items-start gap-2 px-2 py-1 rounded text-[11px] leading-relaxed transition-colors
                  ${isHighlighted
                    ? 'bg-amber-50 dark:bg-amber-900/20 ring-1 ring-amber-300 dark:ring-amber-700'
                    : 'text-neutral-500 dark:text-neutral-500'
                  }`}>
                <span className={`text-[9px] font-mono mt-0.5 shrink-0 w-5 text-right
                  ${isHighlighted
                    ? 'text-amber-700 dark:text-amber-400 font-bold'
                    : 'text-neutral-400 dark:text-neutral-600'
                  }`}>
                  {isHighlighted ? '★' : ''}{v.verse}
                </span>
                <span className={isHighlighted
                  ? 'text-neutral-800 dark:text-neutral-200'
                  : 'text-neutral-500 dark:text-neutral-500'
                }>
                  {v.text_english}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 bg-neutral-50 dark:bg-neutral-800/30 border-t border-neutral-100 dark:border-neutral-700">
        <button onClick={() => onNavigate && primary && onNavigate(primary.book, primary.chapter)}
          className="text-[9px] text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">
          Open full chapter →
        </button>
      </div>
    </div>
  )
}
