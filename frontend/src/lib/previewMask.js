/**
 * Preview masking for verse memorization review.
 *
 * Two preview options (mirrors web/routes/memorize.py):
 *   first_letters — first letter of N% of words (levels 25/50/75/100)
 *   full_text     — the whole verse
 *   none          — reference only, pure recall
 *
 * Hidden words render as ___ so positions are preserved.
 * Revealed words show just their first letter (classic first-letter drill).
 */

export const PREVIEW_LEVELS = [0, 25, 50, 75, 100]

export function autoPreviewLevel(mastery = 0, attempts = 0) {
  if (!attempts) return 100
  if (mastery < 0.3) return 100
  if (mastery < 0.5) return 75
  if (mastery < 0.7) return 50
  if (mastery < 0.9) return 25
  return 0
}

function firstLetterOf(word) {
  const m = (word || '').match(/[A-Za-z\u00C0-\u024F\u0370-\u03FF\u0590-\u05FF]/)
  return m ? m[0] : (word || '')[0] || ''
}

/** Evenly-spread deterministic reveal of pct% of words. */
export function firstLetterMask(text, pct) {
  if (!text) return ''
  const words = text.split(/\s+/).filter(Boolean)
  if (pct >= 100) return words.map(firstLetterOf).join(' ')
  if (pct <= 0) return ''
  return words.map((w, i) => {
    const reveal = Math.floor(((i + 1) * pct) / 100) > Math.floor((i * pct) / 100)
    return reveal ? firstLetterOf(w) : '___'
  }).join(' ')
}

/** Human-readable note about how the current preview caps the rating. */
export function previewCapNote(mode, level) {
  if (mode === 'full_text') return 'Full text shown — counts at most as Hard'
  if (mode === 'first_letters' && (level || 0) >= 75) return `Hints at ${level}% — Easy counts as Good`
  return null
}
