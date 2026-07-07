/**
 * Book name resolution and reference formatting.
 *
 * Provides:
 *  - parseRef(ref) → { label, book, chapter, verse, bookName, workId } or null
 *  - formatRef(book, chapter, verse) → "book.chapter.verse"
 */

// Which work each book belongs to
const WORK_MAP = {
  // OT
  gen:'ot', exo:'ot', lev:'ot', num:'ot', deu:'ot',
  josh:'ot', judg:'ot', ruth:'ot',
  '1sam':'ot', '2sam':'ot', '1kgs':'ot', '2kgs':'ot',
  '1chr':'ot', '2chr':'ot', ezra:'ot', neh:'ot',
  esth:'ot', job:'ot', psa:'ot', prov:'ot', eccl:'ot', song:'ot',
  isa:'ot', jer:'ot', lam:'ot', ezek:'ot', dan:'ot',
  hos:'ot', joel:'ot', amos:'ot', obad:'ot', jonah:'ot',
  mic:'ot', nah:'ot', hab:'ot', zeph:'ot', hag:'ot', zech:'ot', mal:'ot',
  // Apocrypha
  tob:'apoc', jdt:'apoc', wis:'apoc', sir:'apoc', bar:'apoc',
  '1ma':'apoc', '2ma':'apoc', '1esd':'apoc', '2esd':'apoc',
  man:'apoc', sus:'apoc', bel:'apoc', s3y:'apoc', esga:'apoc', psa151:'apoc',
  // NT
  matt:'nt', mark:'nt', luke:'nt', john:'nt', acts:'nt',
  rom:'nt', '1cor':'nt', '2cor':'nt', gal:'nt', eph:'nt',
  phil:'nt', col:'nt', '1thes':'nt', '2thes':'nt',
  '1tim':'nt', '2tim':'nt', titus:'nt', philem:'nt',
  heb:'nt', james:'nt', '1pet':'nt', '2pet':'nt',
  '1john':'nt', '2john':'nt', '3john':'nt', jude:'nt', rev:'nt',
  // BoM
  '1ne':'bom', '2ne':'bom', jacob:'bom', enos:'bom', jarom:'bom',
  omni:'bom', wom:'bom', mosiah:'bom', alma:'bom', hel:'bom',
  '3ne':'bom', '4ne':'bom', morm:'bom', ether:'bom', moro:'bom',
  // D&C
  moses:'pgp', abraham:'pgp', jsm:'pgp', jsh:'pgp', aoff:'pgp',
}

// Full book titles
const BOOK_TITLES = {
  gen:'Genesis', exo:'Exodus', lev:'Leviticus', num:'Numbers', deu:'Deuteronomy',
  josh:'Joshua', judg:'Judges', ruth:'Ruth',
  '1sam':'1 Samuel', '2sam':'2 Samuel', '1kgs':'1 Kings', '2kgs':'2 Kings',
  '1chr':'1 Chronicles', '2chr':'2 Chronicles',
  ezra:'Ezra', neh:'Nehemiah', esth:'Esther', job:'Job',
  psa:'Psalms', prov:'Proverbs', eccl:'Ecclesiastes', song:'Song of Solomon',
  isa:'Isaiah', jer:'Jeremiah', lam:'Lamentations', ezek:'Ezekiel', dan:'Daniel',
  hos:'Hosea', joel:'Joel', amos:'Amos', obad:'Obadiah', jonah:'Jonah',
  mic:'Micah', nah:'Nahum', hab:'Habakkuk', zeph:'Zephaniah', hag:'Haggai',
  zech:'Zechariah', mal:'Malachi',
  tob:'Tobit', jdt:'Judith', wis:'Wisdom of Solomon', sir:'Sirach',
  bar:'Baruch', '1ma':'1 Maccabees', '2ma':'2 Maccabees',
  '1esd':'1 Esdras', '2esd':'2 Esdras',
  man:'Prayer of Manasses', sus:'Susanna', bel:'Bel and the Dragon',
  s3y:'Song of Three Children', esga:'Additions to Esther', psa151:'Psalm 151',
  matt:'Matthew', mark:'Mark', luke:'Luke', john:'John',
  acts:'Acts', rom:'Romans', '1cor':'1 Corinthians', '2cor':'2 Corinthians',
  gal:'Galatians', eph:'Ephesians', phil:'Philippians', col:'Colossians',
  '1thes':'1 Thessalonians', '2thes':'2 Thessalonians',
  '1tim':'1 Timothy', '2tim':'2 Timothy', titus:'Titus', philem:'Philemon',
  heb:'Hebrews', james:'James', '1pet':'1 Peter', '2pet':'2 Peter',
  '1john':'1 John', '2john':'2 John', '3john':'3 John', jude:'Jude', rev:'Revelation',
  '1ne':'1 Nephi', '2ne':'2 Nephi', jacob:'Jacob', enos:'Enos',
  jarom:'Jarom', omni:'Omni', wom:'Words of Mormon',
  mosiah:'Mosiah', alma:'Alma', hel:'Helaman',
  '3ne':'3 Nephi', '4ne':'4 Nephi', morm:'Mormon',
  ether:'Ether', moro:'Moroni',
  moses:'Moses', abraham:'Abraham', jsm:'Joseph Smith—Matthew',
  jsh:'Joseph Smith—History', aoff:'Articles of Faith',
}

/**
 * Parse a verse reference string like "gen.1.1" or "gen.1" into its components.
 * Returns { label, book, chapter, verse, bookName, workId } or null.
 */
export function parseRef(ref) {
  if (!ref) return null

  // Handle D&C sections: "dc76.1" or "dc76"
  const dcMatch = ref.match(/^(dc)(\d+)(?:\.(\d+))?$/)
  if (dcMatch) {
    const book = `dc${dcMatch[2]}`
    const chapter = 1
    const verse = dcMatch[3] ? parseInt(dcMatch[3]) : null
    const label = `D&C ${dcMatch[2]}${verse ? `:${verse}` : ''}`
    return { label, book, chapter, verse, bookName: `D&C ${dcMatch[2]}`, workId: 'dc' }
  }

  const parts = ref.split('.')
  if (parts.length < 2) return null

  const bookId = parts[0].toLowerCase()
  const chapter = parseInt(parts[1])
  const verse = parts[2] ? parseInt(parts[2]) : null

  if (isNaN(chapter)) return null

  const bookTitle = BOOK_TITLES[bookId]
  if (!bookTitle) return null

  // Determine workId (D&C books are stored as dcN)
  let workId = WORK_MAP[bookId]
  if (!workId && bookId.startsWith('dc')) workId = 'dc'

  let label = `${bookTitle} ${chapter}`
  if (verse != null) label += `:${verse}`

  return { label, book: bookId, chapter, verse, bookName: bookTitle, workId }
}

/**
 * Format a book/chapter/verse into a reference string.
 */
export function formatRef(book, chapter, verse) {
  if (verse != null) return `${book}.${chapter}.${verse}`
  return `${book}.${chapter}`
}
