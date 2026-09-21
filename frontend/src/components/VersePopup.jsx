import React, { useState, useEffect, useRef } from 'react'
import { parseRef } from '../bookNames'
import { groupVerses } from '../lib/verseGroups'

/**
 * VersePopup — Gospel-Library-style verse reference drawer.
 *
 * A panel anchored to the right covering most of the viewport, showing the
 * full chapter (scrollable) with the referenced verse highlighted.
 * Click the backdrop, press Escape, or hit ✕ to dismiss.
 */
export default function VersePopup({ verseRef, onClose, onNavigate }) {
  const info = parseRef(verseRef)
  // Verse ranges ("1john.4.7-8"): parseRef keeps only the first verse, so
  // expand the range here for highlighting, scrolling, and handoff.
  const targetVerses = (() => {
    const vpart = String(verseRef).split('.')[2] || ''
    const m = vpart.match(/^(\d+)(?:-(\d+))?$/)
    if (m) {
      const out = []
      for (let v = parseInt(m[1]); v <= (m[2] ? parseInt(m[2]) : parseInt(m[1])); v++) out.push(v)
      return out
    }
    return info?.verse != null ? [info.verse] : []
  })()
  // Show the full range in the header ("1 John 4:7-8", not "1 John 4:7").
  const label = (() => {
    if (!info) return verseRef
    const vpart = String(verseRef).split('.')[2] || ''
    const m = vpart.match(/^(\d+)-(\d+)$/)
    return m ? `${info.label}-${m[2]}` : info.label
  })()
  const [chapterData, setChapterData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [mounted, setMounted] = useState(false)
  const scrollRef = useRef(null)

  // Slide-in transition (no custom keyframes — plain Tailwind transition).
  useEffect(() => {
    const t = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(t)
  }, [])

  // Fetch chapter data
  useEffect(() => {
    if (!info) return
    setLoading(true)
    fetch(`/api/v1/chapter/${info.book}.${info.chapter}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) setChapterData(d.data)
        else setError(d.detail || 'Failed to load')
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [info?.book, info?.chapter])

  // Auto-scroll to the referenced verse
  useEffect(() => {
    if (!scrollRef.current || !chapterData?.verses) return
    const el = targetVerses.length > 0 ? scrollRef.current.querySelector(`[data-verse="${targetVerses[0]}"]`) : null
    if (el) {
      // Same containment as VersePreviewCard: scroll the popup's own
      // container only, never the page behind it.
      const container = scrollRef.current
      const cRect = container.getBoundingClientRect()
      const eRect = el.getBoundingClientRect()
      container.scrollTo({
        top: container.scrollTop + (eRect.top - cRect.top) - container.clientHeight / 2 + eRect.height / 2,
        behavior: 'smooth',
      })
    }
  }, [chapterData, info?.verse])

  // Close on Escape
  useEffect(() => {
    function handleKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  if (!info) {
    return (
      <div className="fixed inset-0 z-[70] bg-black/30" onClick={onClose}>
        <div className="absolute right-0 top-0 h-full w-[94vw] sm:w-[min(75vw,860px)] bg-white dark:bg-neutral-900 p-6 text-sm text-red-500">Invalid reference: {verseRef}</div>
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 z-[70] bg-black/30 dark:bg-black/60"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={label}
    >
      <div
        onClick={e => e.stopPropagation()}
        className={`
          absolute right-0 top-0 h-full w-[94vw] sm:w-[min(75vw,860px)]
          bg-white dark:bg-neutral-900
          border-l border-neutral-200 dark:border-neutral-700
          shadow-2xl
          flex flex-col
          overflow-hidden
          transition-transform duration-200 ease-out
          ${mounted ? 'translate-x-0' : 'translate-x-full'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
              📖 {label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onNavigate && onNavigate(info.book, info.chapter, targetVerses.length > 0 ? targetVerses : undefined)}
              className="text-[11px] text-blue-600 dark:text-blue-400 hover:underline cursor-pointer px-2 py-0.5 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
              title="Open full chapter"
            >
              ↗ Open
            </button>
            <button
              onClick={onClose}
              aria-label="Close"
              className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-sm px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-3" ref={scrollRef}>
          {loading && (
            <div className="flex items-center justify-center py-10 text-sm text-neutral-400">
              <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Loading {info.bookName} {info.chapter}…
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-600">{error}</div>
          )}

          {chapterData?.verses && (
            <div>
              {/* Verse context list — consecutive targets merge into one block */}
              <div className="space-y-1">
                {groupVerses(chapterData.verses, v => targetVerses.includes(v.verse)).map((seg, si) => (
                  seg.highlighted ? (
                    <div
                      key={`hl-${si}`}
                      className="rounded-lg bg-amber-50 dark:bg-amber-900/20 ring-1 ring-amber-300 dark:ring-amber-700 px-1 py-1"
                    >
                      {seg.verses.map(v => (
                        <div key={v.verse} data-verse={v.verse}
                          className="flex items-start gap-2 px-3 py-1.5 rounded-lg text-sm leading-relaxed">
                          <span className="text-[10px] font-mono mt-0.5 shrink-0 w-6 text-right text-amber-700 dark:text-amber-400 font-bold">
                            ★{v.verse}
                          </span>
                          <span className="text-neutral-800 dark:text-neutral-200 font-medium">
                            {v.text_english}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    seg.verses.map(v => (
                      <div key={v.verse} data-verse={v.verse}
                        className="flex items-start gap-2 px-3 py-1.5 rounded-lg text-sm leading-relaxed text-neutral-500 dark:text-neutral-500">
                        <span className="text-[10px] font-mono mt-0.5 shrink-0 w-6 text-right text-neutral-400 dark:text-neutral-600">
                          {v.verse}
                        </span>
                        <span>{v.text_english}</span>
                      </div>
                    ))
                  )
                ))}
              </div>

              {/* Connections section placeholder */}
              <div className="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-700">
                <button
                  onClick={() => onNavigate && onNavigate(info.book, info.chapter, targetVerses.length > 0 ? targetVerses : undefined)}
                  className="w-full text-center text-xs text-blue-600 dark:text-blue-400 hover:underline py-2 cursor-pointer"
                >
                  Open full {info.bookName} {info.chapter} →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
