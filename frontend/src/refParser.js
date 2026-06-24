/**
 * Parse scripture references and paths.
 *
 * Formats:
 *   "isa 55:6"      → navigate
 *   "/ot/isa/55"    → path-style
 *   "/chat ..."     → chat
 *   "/help"         → help
 */

const COLLECTION_MAP = {
  'ot': 'ot', 'old_testament': 'ot', 'oldtestament': 'ot', 'old testament': 'ot',
  'nt': 'nt', 'new_testament': 'nt', 'newtestament': 'nt', 'new testament': 'nt',
  'bom': 'bom', 'book_of_mormon': 'bom', 'bookofmormon': 'bom', 'book of mormon': 'bom',
  'dc': 'dc', 'd&c': 'dc', 'doctrine_and_covenants': 'dc',
  'pgp': 'pgp', 'pearl_of_great_price': 'pgp',
}

const BOOK_ALIASES = {
  'gen': 'gen', 'genesis': 'gen',
  'exo': 'exo', 'exodus': 'exo',
  'lev': 'lev', 'leviticus': 'lev',
  'num': 'num', 'numbers': 'num',
  'deu': 'deu', 'deuteronomy': 'deu',
  'josh': 'josh', 'joshua': 'josh',
  'judg': 'judg', 'judges': 'judg',
  'ruth': 'ruth',
  '1sam': '1sam', '1samuel': '1sam',
  '2sam': '2sam', '2samuel': '2sam',
  '1kgs': '1kgs', '1kings': '1kgs',
  '2kgs': '2kgs', '2kings': '2kgs',
  '1chr': '1chr', '1chronicles': '1chr',
  '2chr': '2chr', '2chronicles': '2chr',
  'ezra': 'ezra',
  'neh': 'neh', 'nehemiah': 'neh',
  'esth': 'esth', 'esther': 'esth',
  'job': 'job',
  'psa': 'psa', 'psalm': 'psa', 'psalms': 'psa',
  'prov': 'prov', 'proverbs': 'prov',
  'eccl': 'eccl', 'ecclesiastes': 'eccl',
  'song': 'song', 'song of solomon': 'song',
  'isa': 'isa', 'isaiah': 'isa',
  'jer': 'jer', 'jeremiah': 'jer',
  'lam': 'lam', 'lamentations': 'lam',
  'ezek': 'ezek', 'ezekiel': 'ezek',
  'dan': 'dan', 'daniel': 'dan',
  'hos': 'hos', 'hosea': 'hos',
  'joel': 'joel',
  'amos': 'amos',
  'obad': 'obad', 'obadiah': 'obad',
  'jonah': 'jonah',
  'mic': 'mic', 'micah': 'mic',
  'nah': 'nah', 'nahum': 'nah',
  'hab': 'hab', 'habakkuk': 'hab',
  'zeph': 'zeph', 'zephaniah': 'zeph',
  'hag': 'hag', 'haggai': 'hag',
  'zech': 'zech', 'zechariah': 'zech',
  'mal': 'mal', 'malachi': 'mal',
  'matt': 'matt', 'matthew': 'matt',
  'mark': 'mark',
  'luke': 'luke',
  'john': 'john',
  'acts': 'acts',
  'rom': 'rom', 'romans': 'rom',
  '1cor': '1cor', '1corinthians': '1cor',
  '2cor': '2cor', '2corinthians': '2cor',
  'gal': 'gal', 'galatians': 'gal',
  'eph': 'eph', 'ephesians': 'eph',
  'phil': 'phil', 'philippians': 'phil',
  'col': 'col', 'colossians': 'col',
  '1thes': '1thes', '1thessalonians': '1thes',
  '2thes': '2thes', '2thessalonians': '2thes',
  '1tim': '1tim', '1timothy': '1tim',
  '2tim': '2tim', '2timothy': '2tim',
  'titus': 'titus',
  'philem': 'philem', 'philemon': 'philem',
  'heb': 'heb', 'hebrews': 'heb',
  'james': 'james',
  '1pet': '1pet', '1peter': '1pet',
  '2pet': '2pet', '2peter': '2pet',
  '1john': '1john',
  '2john': '2john',
  '3john': '3john',
  'jude': 'jude',
  'rev': 'rev', 'revelation': 'rev',
  '1ne': '1ne', '1nephi': '1ne',
  '2ne': '2ne', '2nephi': '2ne',
  'jacob': 'jacob',
  'enos': 'enos',
  'jarom': 'jarom',
  'omni': 'omni',
  'wom': 'wom', 'words of mormon': 'wom',
  'mosiah': 'mosiah',
  'alma': 'alma',
  'hel': 'hel', 'helaman': 'hel',
  '3ne': '3ne', '3nephi': '3ne',
  '4ne': '4ne', '4nephi': '4ne',
  'morm': 'morm', 'mormon': 'morm',
  'ether': 'ether',
  'moro': 'moro', 'moroni': 'moro',
  'moses': 'moses',
  'abraham': 'abraham', 'abr': 'abraham',
  'jsm': 'jsm', 'joseph smith—matthew': 'jsm',
  'jsh': 'jsh', 'joseph smith—history': 'jsh',
  'aoff': 'aoff', 'articles of faith': 'aoff',
}

// Look up a book alias -> internal ID
export function resolveBook(input) {
  if (!input) return null
  const key = input.toLowerCase().trim()
  if (Object.values(BOOK_ALIASES).includes(key)) return key
  if (BOOK_ALIASES[key]) return BOOK_ALIASES[key]
  if (/^dc\d+$/.test(key)) return key
  return null
}

// fzf-style scored fuzzy match
// Returns { score, matchIdxs } if match, or null if no match
// Scoring: consecutive bonus (+4), word boundary bonus (+8/+16), gap penalty (-3/-1)
// matchIdxs: positions in the original text that matched the query
export function scoreFuzzy(text, query) {
  if (!query) return { score: Infinity, matchIdxs: [] }
  const t = text.toLowerCase()
  const q = query.toLowerCase()
  let score = 0
  let prevIdx = -1
  let consecutive = 0
  let firstChar = true
  const matchIdxs = []

  for (let i = 0; i < q.length; i++) {
    const idx = t.indexOf(q[i], prevIdx + 1)
    if (idx === -1) return null  // no match

    matchIdxs.push(idx)

    // Base match score
    score += 16

    // Consecutive bonus
    if (prevIdx >= 0 && idx === prevIdx + 1) {
      consecutive++
      score += 4  // bonusConsecutive
    } else {
      // Gap penalty
      if (prevIdx >= 0) {
        const gap = idx - prevIdx - 1
        score += gap > 1 ? -3 : -1  // scoreGapStart or scoreGapExtension
      }
      consecutive = 0
    }

    // Word boundary bonus
    if (idx === 0 || /[\s\/._:\-]/.test(t[idx - 1])) {
      score += firstChar ? 16 : 8  // double for first character (bonusFirstCharMultiplier)
    }

    firstChar = false
    prevIdx = idx
  }

  // Small bonus for matching early in the string
  if (prevIdx !== undefined && prevIdx < text.length * 0.4) {
    score += 3
  }

  return { score, matchIdxs }
}

// Simple boolean fuzzy match (kept for backward compat)
export function fuzzyMatch(text, query) {
  return scoreFuzzy(text, query) !== null
}

// Full parse + fuzzy results
export function parseAndFuzzy(input, allBooks) {
  if (!input?.trim()) return { type: 'empty', results: [] }
  const text = input.trim()
  const isNewTab = text.endsWith('+')
  const clean = text.replace(/\+$/, '').trim()

  // ── / commands (universal command palette) ──
  if (clean.startsWith('/') && clean !== '/?') {
    const parts = clean.slice(1).split(/\s+/)
    const cmd = parts[0].toLowerCase()
    const args = parts.slice(1).join(' ').trim()
    switch (cmd) {
      case 'chat':
        return { type: 'chat', message: args, results: [{ type: 'chat', message: args, matchIdxs: [], label: args ? `💬 Chat: ${args}` : '💬 New chat' }] }
      case 'search':
      case 'find':
        return { type: 'search', query: args, results: [{ type: 'search', query: args, label: args ? `🔍 Search: ${args}` : '🔍 Search scriptures' }] }
      case 'dark':
      case 'theme':
        return { type: 'dark', results: [{ type: 'dark', label: '🌙 Toggle dark mode' }] }
      case 'font':
        if (args === 'up' || args === '+') return { type: 'font', direction: 'up', results: [{ type: 'font', label: '🔤 Increase font size' }] }
        if (args === 'down' || args === '-') return { type: 'font', direction: 'down', results: [{ type: 'font', label: '🔤 Decrease font size' }] }
        if (/^\d+$/.test(args)) return { type: 'font', size: parseInt(args), results: [{ type: 'font', label: `🔤 Set font size to ${args}%` }] }
        return { type: 'navigate', results: [{ type: 'navigate', label: 'Font: use /font up, /font down, or /font 120' }] }
      case 'toggle':
        return { type: 'toggle', toggle: args, results: [{ type: 'toggle', toggle: args, label: args ? `🔘 Toggle: ${args}` : '🔘 Toggle a feature (footnotes, gematria, lemma, chiasmus, etc.)' }] }
      case 'history':
        return { type: 'history', results: [{ type: 'history', label: '🕐 Open conversation history' }] }
      case 'structure':
        return { type: 'structure', results: [{ type: 'structure', label: '⟷ Open Isaiah structure' }] }
      case 'help':
      case '?':
        return {
          type: 'help',
          results: [{ type: 'help', label: 'Commands', text: `References: type a book or ref like "isa 55:6", "isa:34", "isa/34", or fuzzy like "isah"\nPaths: "/ot/isa/55", "/dc/76"\n\n/chat [message] — Open chat\n/search [query] — Search verses\n/dark — Toggle dark mode\n/font (up|down|120) — Font size\n/toggle [feature] — Toggle footnotes, gematria, lemma, etc.\n/history — Conversation history\n/structure — Isaiah structure\n/help — This help\n\nAdd + for new tab: "isa 55:6 +"` }],
        }
      default:
        // Not a known / command — fall through to path/fuzzy parsing below
        break
    }
  }

  // ── /? as standalone (special case since `/?` is a valid path or help trigger) ──
  if (clean === '/?' || clean === 'help') {
    return {
      type: 'help',
      results: [{ type: 'help', label: 'Commands', text: `References: type a book or ref like "isa 55:6", "isa:34", "isa/34", or fuzzy like "isah"\nPaths: "/ot/isa/55", "/dc/76"\n\n/chat [message] — Open chat\n/search [query] — Search verses\n/dark — Toggle dark mode\n/font (up|down|120) — Font size\n/toggle [feature] — Toggle footnotes, gematria, lemma, etc.\n/history — Conversation history\n/structure — Isaiah structure\n/help — This help\n\nAdd + for new tab: "isa 55:6 +"` }],
    }
  }

  // ── D&C path: /dc/76 or dc76 (must be before simple path to avoid misinterpretation) ──
  const dcMatch = clean.match(/^\/?dc\/(\d+)$/i)
  if (dcMatch) {
      return {
        type: 'navigate',
        results: [{ type: 'navigate', matchIdxs: [], book: `dc${dcMatch[1]}`, chapter: 1, label: `D&C Section ${dcMatch[1]}`, newTab: isNewTab }],
      }
  }

  // ── Simple path: isa/34 or isaiah/34 (book/chapter without collection) ──
  const simplePath = clean.match(/^\/?([a-z0-9_]+)\/(\d+)$/i)
  if (simplePath) {
    const book = resolveBook(simplePath[1])
    if (book) {
      return {
        type: 'navigate',
        results: [{ type: 'navigate', matchIdxs: [], book, chapter: parseInt(simplePath[2]), label: `${book} ${simplePath[2]}`, newTab: isNewTab }],
      }
    }
  }

  // ── Path-style: /ot/isa/55 or /ot/isa ──
  const pathMatch = clean.match(/^\/?([\w\s-&]+)\/([\w\s-]+)(?:\/(\d+))?$/)
  if (pathMatch) {
    const collectionInput = pathMatch[1].toLowerCase().replace(/_/g, ' ')
    const bookInput = pathMatch[2].toLowerCase().replace(/_/g, ' ')
    const chapterStr = pathMatch[3]
    const collectionId = COLLECTION_MAP[collectionInput]

    if (!collectionId) {
      return { type: 'error', results: [{ type: 'error', label: `Unknown collection: ${collectionInput}` }] }
    }

    // Find matching books in this collection (scored and sorted)
    const scored = allBooks
      .map(b => {
        const s = scoreFuzzy(b.searchText, bookInput)
        return s ? { ...b, score: s.score } : null
      })
      .filter(Boolean)
      .sort((a, b) => b.score - a.score)
      .slice(0, 20)
      .map(b => {
        const label = `${b.workLabel} → ${b.bookTitle}${chapterStr ? ` ch.${chapterStr}` : ''}`
        const hl = scoreFuzzy(label, bookInput)
        return {
          type: 'navigate',
          score: b.score,
          matchIdxs: hl?.matchIdxs || [],
          workId: b.workId,
          book: b.bookId,
          chapter: chapterStr ? parseInt(chapterStr) : 1,
          label,
          newTab: isNewTab,
        }
      })

    if (scored.length === 0) {
      return { type: 'error', results: [{ type: 'error', label: `No books in ${collectionInput} matching "${bookInput}"` }] }
    }

    return { type: 'navigate', results: scored }
  }

  // ── Standard ref: "isa 55:6" ──
  // Try exact match first
  const exact = parseStandardRef(clean)
  if (exact) {
    // Look up the full book title from allBooks for a nicer label
    const bookInfo = allBooks.find(b => b.bookId === exact.book)
    const title = bookInfo?.bookTitle || exact.book.toUpperCase()
    // Build label with verse info
    let label = `${title} ${exact.chapter}`
    if (exact.verses?.length === 1) {
      label += `:${exact.verses[0]}`
    } else if (exact.verses?.length > 1) {
      // Show a compact range: first-last, or first,second,...
      const compact = exact.verses.length <= 3
        ? exact.verses.join(',')
        : `${exact.verses[0]}-${exact.verses[exact.verses.length-1]}`
      label += `:${compact}`
    }
    return { type: 'navigate', results: [{ ...exact, matchIdxs: [], label, newTab: isNewTab }] }
  }

  // ── Fuzzy search across all books (scored, sorted, top 20) ──
  // Extract trailing number from query to use as chapter (so "isaah 34" fuzzy-matches "Isaiah")
  const chapterMatch = clean.match(/^(.*\S)\s+(\d+)$/)
  const fuzzyQuery = chapterMatch ? chapterMatch[1].trim() : clean
  const chapterNum = chapterMatch ? parseInt(chapterMatch[2]) : 1

  const scored = allBooks
    .map(b => {
      const s1 = scoreFuzzy(b.searchText, fuzzyQuery)
      const s2 = scoreFuzzy(b.bookId, fuzzyQuery)
      const best = [s1, s2].filter(Boolean).sort((a, b) => b.score - a.score)[0]
      return best ? { ...b, score: best.score } : null
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score)
    .slice(0, 20)
    .map(b => {
      const label = `${b.workLabel} → ${b.bookTitle}`
      const hl = scoreFuzzy(label, fuzzyQuery)
      return {
        type: 'navigate',
        score: b.score,
        matchIdxs: hl?.matchIdxs || [],
        workId: b.workId,
        book: b.bookId,
        chapter: chapterNum,
        label: chapterNum > 1 ? `${label} ch.${chapterNum}` : label,
        newTab: isNewTab,
      }
    })

  if (scored.length > 0) {
    return { type: 'navigate', results: scored }
  }

  return { type: 'error', results: [{ type: 'error', label: `No match for "${input}"` }] }
}

// Parse a verse spec into an array of verse numbers.
// "6" → [6], "6-12" → [6,7,8,9,10,11,12], "6,8,10" → [6,8,10], "6-8,10" → [6,7,8,10]
function parseVerses(spec) {
  if (!spec) return []
  const verses = new Set()
  const parts = spec.split(',')
  for (const part of parts) {
    const range = part.match(/^(\d+)-(\d+)$/)
    if (range) {
      const start = parseInt(range[1]), end = parseInt(range[2])
      for (let v = start; v <= end; v++) verses.add(v)
    } else {
      const n = parseInt(part)
      if (!isNaN(n)) verses.add(n)
    }
  }
  return [...verses].sort((a, b) => a - b)
}

function parseStandardRef(text) {
  // "book chapter:verse-range" or "book chapter:verse1,verse2" or "book chapter:verse-verse"
  const mRange = text.match(/^([a-z0-9_]+)\s+(\d+):([\d,\-]+)$/i)
  if (mRange) {
    const book = resolveBook(mRange[1])
    if (book) {
      const verses = parseVerses(mRange[3])
      return { book, chapter: parseInt(mRange[2]), verse: verses[0] || null, verses: verses.length > 0 ? verses : null }
    }
  }
  // "book chapter:verse" (single verse)
  const m1 = text.match(/^([a-z0-9_]+)\s+(\d+):(\d+)$/i)
  if (m1) {
    const book = resolveBook(m1[1])
    if (book) return { book, chapter: parseInt(m1[2]), verse: parseInt(m1[3]), verses: [parseInt(m1[3])] }
  }
  // "book chapter"
  const m2 = text.match(/^([a-z0-9_]+)\s+(\d+)$/i)
  if (m2) {
    const book = resolveBook(m2[1])
    if (book) return { book, chapter: parseInt(m2[2]), verse: null, verses: null }
  }
  // "book:chapter" (colon between book and chapter)
  const m3 = text.match(/^([a-z0-9_]+):(\d+)$/i)
  if (m3) {
    const book = resolveBook(m3[1])
    if (book) return { book, chapter: parseInt(m3[2]), verse: null, verses: null }
  }
  // "bookN" no-space ref: "isa3", "isaiah3", "gen1" etc.
  const m4 = text.match(/^([a-zA-Z]+)(\d+)$/)
  if (m4) {
    const combined = (m4[1] + m4[2]).toLowerCase()
    // Check for D&C sections like "dc76"
    if (/^dc\d+$/.test(combined)) {
      return { book: combined, chapter: 1, verse: null, verses: null }
    }
    // Check for book:chapter like "isa3" (resolve "isa" + "3")
    const book = resolveBook(m4[1])
    if (book) return { book, chapter: parseInt(m4[2]), verse: null, verses: null }
    // Try the full string as a book alias: "gen1" might resolve
    const book2 = resolveBook(combined)
    if (book2) return { book: book2, chapter: 1, verse: null, verses: null }
  }
  const book = resolveBook(text)
  if (book) return { book, chapter: 1, verse: null, verses: null }
  return null
}

// Chapter counts for every book — used by the chapter preview in the command bar
const CHAPTER_MAP = {
  gen:50, exo:40, lev:27, num:36, deu:34, josh:24, judg:21, ruth:4,
  '1sam':31, '2sam':24, '1kgs':22, '2kgs':25, '1chr':29, '2chr':36,
  ezra:10, neh:13, esth:10, job:42, psa:150, prov:31, eccl:12, song:8,
  isa:66, jer:52, lam:5, ezek:48, dan:12, hos:14, joel:3, amos:9,
  obad:1, jonah:4, mic:7, nah:3, hab:3, zeph:3, hag:2, zech:14, mal:4,
  matt:28, mark:16, luke:24, john:21, acts:28, rom:16, '1cor':16,
  '2cor':13, gal:6, eph:6, phil:4, col:4, '1thes':5, '2thes':3,
  '1tim':6, '2tim':4, titus:3, philem:1, heb:13, james:5, '1pet':5,
  '2pet':3, '1john':5, '2john':1, '3john':1, jude:1, rev:22,
  '1ne':22, '2ne':33, jacob:7, enos:1, jarom:1, omni:1, wom:1,
  mosiah:29, alma:63, hel:16, '3ne':30, '4ne':1, morm:9, ether:15, moro:10,
  moses:8, abraham:5, jsm:1, jsh:1, aoff:1,
}

export function getChapters(bookId) {
  if (bookId?.startsWith('dc')) return [parseInt(bookId.replace('dc', ''))]
  const count = CHAPTER_MAP[bookId]
  if (!count) return [1]
  return Array.from({ length: count }, (_, i) => i + 1)
}
