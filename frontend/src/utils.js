/**
 * Shared utility functions for the Scripture frontend.
 */

// Hebrew Unicode ranges
const HEBREW_BLOCK = /[\u0590-\u05FF]/;

/**
 * Strip niqqud (vowel points) and cantillation marks from Hebrew text,
 * keeping only the consonant letters.
 */
export function cleanHebrew(text) {
  if (!text) return ''
  // Remove niqqud (U+05B0–U+05BF, U+05C1–U+05C2, U+05C4–U+05C7)
  // and cantillation marks (U+0591–U+05AF)
  return text.replace(/[\u0591-\u05AF\u05B0-\u05BF\u05C1-\u05C2\u05C4-\u05C7]/g, '')
}

/**
 * Check if a verse number has a chiastic role in any of the given chiasms.
 * Returns the label (letter) of the role, or null.
 */
export function lineHasChiasmRole(verseNum, chiasms) {
  if (!chiasms || !verseNum) return null
  for (const chiasm of chiasms) {
    if (!chiasm.elements) continue
    for (const el of chiasm.elements) {
      if (el.verse === verseNum) {
        return el.label || null
      }
    }
  }
  return null
}
