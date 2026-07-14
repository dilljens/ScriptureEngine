/**
 * Hebrew text utilities for the frontend.
 */

/**
 * Navigate to a verse by dispatching a scripture-navigate event.
 * This is handled by App.jsx globally.
 */
export function navigateToVerse(verseRef) {
  if (!verseRef) return
  const parts = verseRef.split('.')
  if (parts.length >= 2) {
    const book = parts[0]
    const chapter = parseInt(parts[1]) || 1
    window.dispatchEvent(new CustomEvent('scripture-navigate', {
      detail: { book, chapter }
    }))
  } else if (verseRef.startsWith('wiki:')) {
    window.dispatchEvent(new CustomEvent('scripture-navigate', {
      detail: { ref: verseRef }
    }))
  }
}

/**
 * Navigate to a verse by book, chapter, and optional verse number.
 */
export function navigateToVerseBCV(book, chapter, verse) {
  if (!book || !chapter) return
  window.dispatchEvent(new CustomEvent('scripture-navigate', {
    detail: { book, chapter }
  }))
}

/**
 * Strip morphological separators (/) from Hebrew text.
 * The WLC database uses / to mark morpheme boundaries (prefixes, etc.),
 * which is useful for linguistic analysis but not for reading.
 */
/**
 * Strip morphological separators (/) from Hebrew text.
 * The WLC database uses / to mark morpheme boundaries — useful for
 * linguistic analysis but not for reading display.
 * Note: there is also cleanHebrew() in utils.js which strips vowels.
 */
export function stripMorphSeparators(text) {
  if (!text) return text
  return text.replace(/\//g, '')
}

/**
 * Hebrew font stack for biblical text with niqqud + te'amim.
 * Uses self-hosted fonts with system fallbacks.
 */
export const HEBREW_BIBLICAL_FONT = "font-['SBL_Hebrew','Ezra_SIL','Taamey_Frank_CLM','Noto_Sans_Hebrew','Tahoma','Arial_Hebrew',serif]"

/**
 * Hebrew font stack for modern/UI text (no niqqud needed).
 */
export const HEBREW_UI_FONT = "font-['Noto_Sans_Hebrew','Heebo','Tahoma','Arial_Hebrew',sans-serif]"

/**
 * Hebrew display modes.
 */
export const HEBREW_MODES = {
  READING: 'reading',
  SCHOLAR: 'scholar',
  INTERLINEAR: 'interlinear',
}

/**
 * Strip niqqud (vowel points) from Hebrew text, keeping consonants + dagesh.
 * Used for cantillation toggle.
 */
export function stripNiqqud(text) {
  if (!text) return text
  // Remove combining marks except shin/sin dot (U+05C1, U+05C2) and dagesh (U+05BC)
  return text.replace(/[\u0591-\u05AF\u05B0-\u05BB\u05BD-\u05BF\u05C3-\u05C7]/g, '')
}

/**
 * Strip cantillation marks (te'amim) from Hebrew text.
 */
export function stripCantillation(text) {
  if (!text) return text
  // Cantillation marks are in the range U+0591-U+05AF
  return text.replace(/[\u0591-\u05AF]/g, '')
}

/**
 * Format a verse reference with full book name.
 */
export function formatRef(book, ch, vs) {
  const BOOK_NAMES = {
    gen: 'Genesis', exo: 'Exodus', lev: 'Leviticus', num: 'Numbers', deu: 'Deuteronomy',
    josh: 'Joshua', judg: 'Judges', ruth: 'Ruth', '1sam': '1 Samuel', '2sam': '2 Samuel',
    '1kgs': '1 Kings', '2kgs': '2 Kings', '1chr': '1 Chronicles', '2chr': '2 Chronicles',
    ezra: 'Ezra', neh: 'Nehemiah', esth: 'Esther', job: 'Job', psa: 'Psalms',
    prov: 'Proverbs', eccl: 'Ecclesiastes', song: 'Song of Solomon',
    isa: 'Isaiah', jer: 'Jeremiah', lam: 'Lamentations', ezek: 'Ezekiel',
    dan: 'Daniel', hos: 'Hosea', joel: 'Joel', amos: 'Amos', obad: 'Obadiah',
    jonah: 'Jonah', mic: 'Micah', nah: 'Nahum', hab: 'Habakkuk',
    zeph: 'Zephaniah', hag: 'Haggai', zech: 'Zechariah', mal: 'Malachi',
    matt: 'Matthew', mark: 'Mark', luke: 'Luke', john: 'John',
    acts: 'Acts', rom: 'Romans', '1cor': '1 Corinthians', '2cor': '2 Corinthians',
    gal: 'Galatians', eph: 'Ephesians', phil: 'Philippians', col: 'Colossians',
    '1thes': '1 Thessalonians', '2thes': '2 Thessalonians',
    '1tim': '1 Timothy', '2tim': '2 Timothy', titus: 'Titus', philem: 'Philemon',
    heb: 'Hebrews', james: 'James', '1pet': '1 Peter', '2pet': '2 Peter',
    '1john': '1 John', '2john': '2 John', '3john': '3 John', jude: 'Jude', rev: 'Revelation',
    '1ne': '1 Nephi', '2ne': '2 Nephi', jacob: 'Jacob', enos: 'Enos',
    jarom: 'Jarom', omni: 'Omni', wom: 'Words of Mormon',
    mosiah: 'Mosiah', alma: 'Alma', hel: 'Helaman', '3ne': '3 Nephi',
    '4ne': '4 Nephi', morm: 'Mormon', ether: 'Ether', moro: 'Moroni',
    dc: 'D&C', moses: 'Moses', abraham: 'Abraham', jsm: 'Joseph Smith—Matthew',
    jsh: 'Joseph Smith—History', aoff: 'Articles of Faith',
  }
  const name = BOOK_NAMES[book.toLowerCase()] || book
  return vs ? `${name} ${ch}:${vs}` : `${name} ${ch}`
}
