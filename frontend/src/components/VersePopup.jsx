import React, { useState, useEffect, useRef } from 'react'
import { parseRef, formatRef } from '../bookNames'
import VersePreviewCard from './VersePreviewCard'

/**
 * VersePopup — responsive verse reference popup.
 *
 * Mobile: bottom sheet that slides up
 * Desktop: centered modal
 *
 * Shows verse text, surrounding context, connections, and actions.
 */
export default function VersePopup({ verseRef, onClose, onNavigate }) {
  const info = parseRef(verseRef)
  const [chapterData, setChapterData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

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
    const el = scrollRef.current.querySelector(`[data-verse="${info?.verse}"]`)
    if (el) {
      el.scrollIntoView({ block: 'center', behavior: 'smooth' })
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
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
        <div className="bg-white dark:bg-neutral-900 rounded-xl p-6 text-sm text-red-500">Invalid reference: {verseRef}</div>
      </div>
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/30 dark:bg-black/60 flex items-end sm:items-center justify-center animate-fade-in"
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="
          w-full sm:max-w-lg
          sm:rounded-xl rounded-t-xl
          bg-white dark:bg-neutral-900
          border border-neutral-200 dark:border-neutral-700
          shadow-2xl
          max-h-[85vh] sm:max-h-[70vh]
          flex flex-col
          animate-slide-up sm:animate-scale-in
          overflow-hidden
        "
      >
        {/* Mobile drag handle */}
        <div className="sm:hidden flex justify-center pt-2 pb-1">
          <div className="w-10 h-1 rounded-full bg-neutral-300 dark:bg-neutral-600" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
              📖 {info.label}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => onNavigate && onNavigate(info.book, info.chapter)}
              className="text-[11px] text-blue-600 dark:text-blue-400 hover:underline cursor-pointer px-2 py-0.5 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
              title="Open full chapter"
            >
              ↗ Open
            </button>
            <button
              onClick={onClose}
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
              {/* Verse context list */}
              <div className="space-y-1">
                  {chapterData.verses.map(v => {
                  const isTarget = v.verse === info.verse

                  return (
                    <div
                      key={v.verse}
                      data-verse={v.verse}
                      className={`flex items-start gap-2 px-3 py-1.5 rounded-lg text-sm leading-relaxed transition-colors
                        ${isTarget
                          ? 'bg-amber-50 dark:bg-amber-900/20 ring-1 ring-amber-300 dark:ring-amber-700 -mx-1 px-4'
                          : 'text-neutral-500 dark:text-neutral-500'
                        }`}
                    >
                      <span className={`text-[10px] font-mono mt-0.5 shrink-0 w-6 text-right
                        ${isTarget
                          ? 'text-amber-700 dark:text-amber-400 font-bold'
                          : 'text-neutral-400 dark:text-neutral-600'
                        }`}>
                        {isTarget ? '★' : ''}{v.verse}
                      </span>
                      <span className={isTarget
                        ? 'text-neutral-800 dark:text-neutral-200 font-medium'
                        : 'text-neutral-500 dark:text-neutral-500'
                      }>
                        {v.text_english}
                      </span>
                    </div>
                  )
                })}
              </div>

              {/* Connections section placeholder */}
              <div className="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-700">
                <button
                  onClick={() => onNavigate && onNavigate(info.book, info.chapter)}
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
