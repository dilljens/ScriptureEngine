import { useState, useRef, useEffect } from 'react'

/** In-memory cache of fetched verse preview texts, keyed by start-verse id. */
const previewCache = new Map()

/**
 * VerseRef — a scripture reference chip with hover preview.
 *
 * Hover (desktop) fetches the verse text once and shows it in a popover;
 * click calls onOpen(refId) so the host can navigate (existing behavior).
 * On touch devices there is no hover — tap navigates as before.
 *
 * Props:
 *   refId   — verse id like "isa.1.18", "2ne.31.17", "dc93.93.1", ranges like "isa.33.14-17"
 *   label   — display text (defaults to refId)
 *   onOpen  — called with (refId) on click
 */
export default function VerseRef({ refId, label, onOpen }) {
  const [open, setOpen] = useState(false)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const openTimer = useRef(null)
  const closeTimer = useRef(null)
  const startRef = String(refId).split('-')[0]

  useEffect(() => () => {
    clearTimeout(openTimer.current)
    clearTimeout(closeTimer.current)
  }, [])

  const handleEnter = () => {
    clearTimeout(closeTimer.current)
    if (previewCache.has(startRef)) {
      setPreview(previewCache.get(startRef))
      setOpen(true)
      return
    }
    openTimer.current = setTimeout(() => {
      setOpen(true)
      setLoading(true)
      fetch(`/api/v1/verses/${startRef}`)
        .then((r) => r.json())
        .then((d) => {
          const entry = {
            text: d?.data?.text_english || null,
            reference: d?.data?.reference || null,
          }
          previewCache.set(startRef, entry)
          setPreview(entry)
        })
        .catch(() => setPreview({ text: null, reference: null }))
        .finally(() => setLoading(false))
    }, 220)
  }

  const handleLeave = () => {
    clearTimeout(openTimer.current)
    closeTimer.current = setTimeout(() => setOpen(false), 180)
  }

  const handleClick = (e) => {
    e.stopPropagation()
    setOpen(false)
    if (onOpen) onOpen(refId)
  }

  return (
    <span className="relative inline" onMouseEnter={handleEnter} onMouseLeave={handleLeave}>
      <span
        onClick={handleClick}
        className="inline align-baseline font-medium cursor-pointer transition-colors
          text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline"
        title={`Click to view ${label || refId}`}
      >
        {label || refId}
      </span>
      {open && (
        <span
          onClick={handleClick}
          className="absolute z-50 bottom-full left-0 mb-1.5 w-72 max-w-[80vw] cursor-pointer
            rounded-lg border border-neutral-200 dark:border-neutral-700
            bg-white dark:bg-neutral-900 shadow-xl p-2.5 text-left font-normal no-underline"
        >
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-1">
            {preview?.reference || label || refId}
          </span>
          {loading ? (
            <span className="block text-xs text-neutral-400">Loading…</span>
          ) : preview?.text ? (
            <span className="block text-xs leading-relaxed text-neutral-700 dark:text-neutral-300">
              {preview.text.length > 320 ? `${preview.text.slice(0, 320)}…` : preview.text}
            </span>
          ) : (
            <span className="block text-xs text-neutral-400">Verse text unavailable — click to open.</span>
          )}
          <span className="block mt-1.5 text-[10px] text-neutral-400 dark:text-neutral-500">
            Click to open in context
          </span>
        </span>
      )}
    </span>
  )
}
