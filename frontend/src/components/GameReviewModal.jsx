import React from 'react'
import HebrewQuiz from './HebrewQuiz'

/**
 * GameReviewModal — run a review session WITHOUT leaving the game.
 *
 * The game's whole premise is that recall is the click. Navigating away to a
 * lesson page broke that loop (and the flow state with it), so the review runs
 * in an overlay: answer → tap Ohr + mint Kavod → back to the golems.
 *
 * nodeId: when set, runs that lesson's quiz (guaranteed questions). When null,
 * runs the cumulative interleaved review (spaced-repetition due items) — only
 * useful once the learner has history.
 */
export default function GameReviewModal({ nodeId = null, title, onClose, onFinished }) {
  return (
    <div
      className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm flex items-start sm:items-center justify-center p-2 sm:p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-label="Practice review"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl my-2 sm:my-6 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 sticky top-0 bg-white dark:bg-neutral-900 z-10">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">
              ⚡ Practice — earn Ohr &amp; Kavod
            </div>
            <div className="text-[11px] text-neutral-500 dark:text-neutral-400 truncate">
              {title || 'Every correct answer taps Ohr and mints 🌟'}
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-3 min-h-[44px] min-w-[44px] rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 cursor-pointer shrink-0"
            aria-label="Close practice"
          >
            ✕
          </button>
        </div>

        <HebrewQuiz
          count={6}
          nodeId={nodeId || undefined}
          onBack={onClose}
          onComplete={() => { onFinished?.(); onClose() }}
          onOpenLesson={() => { onFinished?.(); onClose() }}
        />
      </div>
    </div>
  )
}
