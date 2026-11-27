import React from 'react'

/**
 * HebrewPrompt — question/prompt text with Hebrew-script runs promoted.
 *
 * A bare vowel point or letter at 14px body size is near-invisible, and
 * "Name this vowel: Patah" tests the English label rather than the script.
 * So every Hebrew-script run renders large + RTL + biblical font on a chip
 * while the Latin remainder keeps body styling. Pure presentational.
 *
 * Props: text (string), className (optional override for the wrapper).
 */
export default function HebrewPrompt({ text, className }) {
  const parts = String(text ?? '').split(/([\u0590-\u05FF\u05B0-\u05C7]+)/g)
  if (parts.length <= 1) {
    return (
      <p className={className || 'text-sm text-neutral-800 dark:text-neutral-200 mt-3 mb-4 leading-relaxed'} dir="auto">
        {String(text ?? '')}
      </p>
    )
  }
  return (
    <p className={className || 'text-sm text-neutral-800 dark:text-neutral-200 mt-3 mb-4 leading-relaxed'} dir="auto">
      {parts.map((part, i) =>
        /[\u0590-\u05FF]/.test(part) ? (
          <span key={i} dir="rtl" lang="he"
            className="font-hebrew-biblical text-3xl leading-relaxed align-middle mx-1 inline-block min-w-[1.5em] text-center rounded-lg bg-neutral-100 dark:bg-neutral-700/60 px-2 py-0.5">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </p>
  )
}
