import React from 'react'

/**
 * FeastModal — what/why/when of a Hebrew feast (moed).
 *
 * Every feast teaches (meaning, scriptures, vocab) and pays (one mechanic).
 * Opened from the HUD feast chip. Pure display — dates come precomputed.
 */
export default function FeastModal({ feast, daysUntil, onClose }) {
  if (!feast) return null
  const live = daysUntil === 0
  return (
    <div role="dialog" aria-label={`${feast.name} — Hebrew feast`} onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 cursor-pointer">
      <div onClick={e => e.stopPropagation()}
        className="w-[min(94vw,26rem)] max-h-[85dvh] overflow-y-auto p-4 rounded-2xl bg-white dark:bg-neutral-900 shadow-2xl border border-amber-200 dark:border-amber-800 cursor-default">
        <div className="text-center mb-2">
          <div className="text-3xl">{feast.icon}</div>
          <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">
            {feast.name} <span className="font-serif" dir="rtl">{feast.hebrew}</span>
          </h2>
          <div className="text-[11px] text-neutral-500 dark:text-neutral-400">
            {feast.month} {feast.start}{feast.len > 1 ? `–${feast.start + feast.len - 1}` : ''}
            {live ? ` · day ${feast.dayIndex + 1} of ${feast.len} — LIVE now` : ` · begins in ${daysUntil}d`}
          </div>
        </div>
        <p className="text-xs text-neutral-600 dark:text-neutral-300 leading-relaxed mb-2">{feast.meaning}</p>
        <div className="mb-2 px-2.5 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-[11px] text-amber-800 dark:text-amber-200 text-center">
          ⚡ In game: {feast.effect}
        </div>
        <div className="flex flex-wrap gap-1.5 justify-center mb-2">
          {(feast.scriptures || []).map(s => (
            <span key={s} className="px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-[10px] font-medium text-neutral-600 dark:text-neutral-300">{s}</span>
          ))}
        </div>
        <div className="space-y-1 mb-3">
          {(feast.vocab || []).map(([he, tr, en]) => (
            <div key={he} className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-neutral-50 dark:bg-neutral-800/60 text-[11px]">
              <span className="font-serif text-sm" dir="rtl">{he}</span>
              <span className="text-neutral-400 italic">{tr}</span>
              <span className="flex-1" />
              <span className="text-neutral-600 dark:text-neutral-300">{en}</span>
            </div>
          ))}
        </div>
        <button onClick={onClose}
          className="w-full min-h-[44px] rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold cursor-pointer">
          {live ? 'Back to the feast 🎉' : 'Close'}
        </button>
      </div>
    </div>
  )
}
