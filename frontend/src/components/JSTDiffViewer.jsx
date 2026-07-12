import React, { useState, useEffect } from 'react'

/**
 * JSTDiffViewer — shows JST (Joseph Smith Translation) changes for a verse.
 *
 * Fetches verse data including text_jst and jst_diff fields.
 * Shows KJV ↔ JST side by side with color-coded differences.
 *
 * Props:
 *   verse: string (e.g., "gen.1.1")
 *   onNavigate: (book, chapter) => void
 */
export default function JSTDiffViewer({ verse, onNavigate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!verse) return
    setLoading(true)
    fetch(`/api/v1/verses/${encodeURIComponent(verse)}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) setData(d.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [verse])

  if (!verse) return null
  if (loading) return <div className="text-xs text-neutral-400 animate-pulse p-3">Loading JST…</div>

  const jstText = data?.text_jst
  const kjvText = data?.text_english
  const diff = data?.jst_diff || 'identical'

  if (!jstText) return null // No JST for this verse

  // Determine if there's a meaningful difference
  const isChanged = diff !== 'identical'
  // Check actual text difference
  const normKjv = (kjvText || '').replace(/\s+/g, ' ').trim().toLowerCase()
  const normJst = (jstText || '').replace(/\s+/g, ' ').trim().toLowerCase()
  const textuallyDifferent = normKjv !== normJst

  if (!textuallyDifferent && diff === 'identical') return null

  const diffLabel = diff === 'jst_addition' ? 'Expanded' : diff === 'jst_change' ? 'Modified' : 'Minor Change'

  return (
    <div className="mt-4 rounded-xl border-2 overflow-hidden
      ${diff === 'jst_addition' ? 'border-green-300 dark:border-green-700' :
        diff === 'jst_change' ? 'border-amber-300 dark:border-amber-700' :
        'border-blue-200 dark:border-blue-800'}">
      
      {/* Header */}
      <div className={`px-3 py-1.5 flex items-center gap-2 text-[10px] font-medium ${
        diff === 'jst_addition' ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' :
        diff === 'jst_change' ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300' :
        'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
      }`}>
        <span className="font-semibold">JST</span>
        <span className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider
          ${diff === 'jst_addition' ? 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200' :
            diff === 'jst_change' ? 'bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200' :
            'bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200'}">
          {diffLabel}
        </span>
        <span className="ml-auto opacity-60">{verse}</span>
      </div>

      {/* Side-by-side comparison */}
      <div className="grid grid-cols-2 divide-x divide-neutral-200 dark:divide-neutral-700">
        {/* KJV */}
        <div className="p-3 bg-white dark:bg-neutral-900">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">KJV</p>
          <p className="text-xs leading-relaxed text-neutral-700 dark:text-neutral-300">{kjvText}</p>
        </div>
        {/* JST */}
        <div className="p-3 bg-white dark:bg-neutral-900">
          <p className="text-[9px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">JST</p>
          <p className="text-xs leading-relaxed text-neutral-800 dark:text-neutral-200 font-medium">
            {jstText}
          </p>
        </div>
      </div>

      {/* Footer with link to navigate */}
      <div className="px-3 py-1 border-t border-neutral-100 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-right">
        <span className="text-[9px] text-neutral-400">
          Joseph Smith Translation · {jstText.length} chars
        </span>
      </div>
    </div>
  )
}
