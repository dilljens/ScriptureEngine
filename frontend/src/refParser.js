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
  'dss': 'dss', 'dead_sea_scrolls': 'dss', 'deadsea scrolls': 'dss',
  'apoc': 'apoc', 'apocrypha': 'apoc',
  'pseu': 'pseu', 'pseudepigrapha': 'pseu',
  'expanded': 'expanded', 'expanded_canon': 'expanded', 'expanded canon': 'expanded',
}

const BOOK_ALIASES = {
  'tob': 'tob', 'tobit': 'tob',
  'jdt': 'jdt', 'judith': 'jdt',
  'wis': 'wis', 'wisdom': 'wis', 'wisdom of solomon': 'wis',
  'sir': 'sir', 'sirach': 'sir', 'ecclesiasticus': 'sir',
  'bar': 'bar', 'baruch': 'bar',
  '1ma': '1ma', '1maccabees': '1ma',
  '2ma': '2ma', '2maccabees': '2ma',
  '1esd': '1esd', '1esdras': '1esd',
  '2esd': '2esd', '2esdras': '2esd',
  'man': 'man', 'manasses': 'man', 'prayer of manasses': 'man',
  'sus': 'sus', 'susanna': 'sus',
  'bel': 'bel', 'bel and the dragon': 'bel',
  's3y': 's3y', 'song of three': 's3y',
  'esga': 'esga', 'additions to esther': 'esga',
  'psa151': 'psa151', 'psalm 151': 'psa151',

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
  'dc': 'dc', 'd&c': 'dc', 'doctrine and covenants': 'dc',
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

  // Prefix bonus: query is a prefix of the entire text or a word within it
  if (t.startsWith(q)) {
    score += 50
  } else {
    // Check if query is a prefix of any word in the text
    const words = t.split(/[\s\/._:\-]+/)
    for (const word of words) {
      if (word.startsWith(q)) {
        score += 50
        break
      }
    }
  }

  // Word-prefix bonus: query starts at a word boundary
  const words = t.split(/[\s\/._:\-]+/)
  for (const word of words) {
    if (word.startsWith(q)) {
      score += 30
      break
    }
  }

  // Length normalization: prevent long strings from dominating short ones
  score = score / Math.sqrt(text.length)

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

  // ── COMMAND LIST for autocomplete ──
  const COMMANDS = [
    { cmd: 'chat', icon: '💬', label: 'Chat', desc: 'Open chat with a message', type: 'chat' },
    { cmd: 'search', icon: '🔍', label: 'Search', desc: 'Search scriptures', type: 'search' },
    { cmd: 'find', icon: '🔍', label: 'Find', desc: 'Search scriptures (alias)', type: 'search' },
    { cmd: 'dark', icon: '🌙', label: 'Dark mode', desc: 'Toggle dark mode', type: 'command' },
    { cmd: 'theme', icon: '🌙', label: 'Theme', desc: 'Toggle dark mode (alias)', type: 'command' },
    { cmd: 'font', icon: '🔤', label: 'Font size', desc: '/font up, /font down, /font 120', type: 'command' },
    { cmd: 'toggle', icon: '🔘', label: 'Toggle feature', desc: 'Toggle footnotes, gematria, etc.', type: 'toggle' },
    { cmd: 'history', icon: '🕐', label: 'History', desc: 'Conversation history', type: 'history' },
    { cmd: 'structure', icon: '⟷', label: 'Isaiah structure', desc: 'Open Isaiah structure viewer', type: 'structure' },
    { cmd: 'help', icon: '❓', label: 'Help', desc: 'Show this help', type: 'help' },
  ]

  // ── / commands (universal command palette) ──
  if (clean.startsWith('/') && clean !== '/?') {
    const parts = clean.slice(1).split(/\s+/)
    const cmd = parts[0].toLowerCase()
    const args = parts.slice(1).join(' ').trim()

    // If empty after / or only partial command, show autocomplete suggestions
    if (cmd === '' || COMMANDS.some(c => c.cmd.startsWith(cmd) && c.cmd !== cmd)) {
      const suggestions = COMMANDS
        .filter(c => c.cmd.startsWith(cmd))
        .map(c => ({
          type: c.type,
          label: `${c.icon} /${c.cmd} — ${c.desc}`,
          cmd: c.cmd,
          explanation: c.desc,
          matchIdxs: [],
        }))
      if (suggestions.length > 0) {
        // Add a "Type a book to navigate" option at the top
        const navHint = { type: 'navigate', label: '📖 Type a book name or reference to navigate', explanation: 'e.g., "isa 55:6" or "genesis"', matchIdxs: [] }
        return { type: 'autocomplete', results: [navHint, ...suggestions] }
      }
    }

    switch (cmd) {
      case '':
        return { type: 'autocomplete', results: [] }
      case 'chat':
        return { type: 'chat', message: args, results: [{ type: 'chat', icon: '💬', message: args, matchIdxs: [], label: args ? `💬 Chat: ${args}` : '💬 New chat' }] }
      case 'search':
      case 'find':
        return { type: 'search', query: args, results: [{ type: 'search', icon: '🔍', query: args, label: args ? `🔍 Search: ${args}` : '🔍 Search scriptures', explanation: 'Press Enter to search' }] }
      case 'dark':
      case 'theme':
        return { type: 'command', results: [{ type: 'command', icon: '🌙', label: '🌙 Toggle dark mode', explanation: 'Toggle between light and dark theme' }] }
      case 'font':
        if (args === 'up' || args === '+') return { type: 'command', results: [{ type: 'command', icon: '🔤', label: '🔤 Increase font size', explanation: 'Make text larger' }] }
        if (args === 'down' || args === '-') return { type: 'command', results: [{ type: 'command', icon: '🔤', label: '🔤 Decrease font size', explanation: 'Make text smaller' }] }
        if (/^\d+$/.test(args)) return { type: 'command', results: [{ type: 'command', icon: '🔤', label: `🔤 Set font size to ${args}%`, explanation: `Font will be ${args}%` }] }
        return { type: 'autocomplete', results: [
          { type: 'command', icon: '🔤', label: '🔤 /font up — Larger text', explanation: 'Increase font size', matchIdxs: [] },
          { type: 'command', icon: '🔤', label: '🔤 /font down — Smaller text', explanation: 'Decrease font size', matchIdxs: [] },
          { type: 'command', icon: '🔤', label: '🔤 /font 120 — Set to 120%', explanation: 'Specific percentage', matchIdxs: [] },
        ]}
      case 'toggle':
        return { type: 'toggle', toggle: args, results: [{ type: 'toggle', icon: '🔘', toggle: args, label: args ? `🔘 Toggle: ${args}` : '🔘 Toggle a feature', explanation: args ? `Toggle ${args} on/off` : 'footnotes, gematria, lemma, chiasmus, etc.' }] }
      case 'history':
        return { type: 'history', results: [{ type: 'history', icon: '🕐', label: '🕐 Open conversation history', explanation: 'View past conversations' }] }
      case 'structure':
        return { type: 'structure', results: [{ type: 'structure', icon: '⟷', label: '⟷ Open Isaiah structure', explanation: 'View Isaiah parallelism' }] }
      case 'help':
      case '?':
        return {
          type: 'help',
          results: [{ type: 'help', label: 'Commands', text: `References: type a book or ref like "isa 55:6", "isa:34", "isa/34"\nPaths: "/ot/isa/55", "/dc/76"\n\n${COMMANDS.map(c => `${c.icon} /${c.cmd} — ${c.desc}`).join('\n')}\n\nAdd + for new tab: "isa 55:6 +"` }],
        }
      default:
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
        const isDcResult = b.bookId?.startsWith?.('dc')
        const chLabel = isDcResult ? 'sec.' : 'ch.'
        const label = `${b.workLabel} → ${b.bookTitle}${chapterStr ? ` ${chLabel}${chapterStr}` : ''}`
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
        label: chapterNum > 1 ? `${label} ${b.bookId?.startsWith('dc') ? 'sec.' : 'ch.'}${chapterNum}` : label,
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

export function parseStandardRef(text) {
  // "bookN:verse-range" or "bookN:verse" no-space ref: "genesis1:1", "isa55:6-12", "gen1:1-2"
  const mNoSpace = text.match(/^([a-zA-Z]+)(\d+):([\d,\-]+)$/)
  if (mNoSpace) {
    const combined = (mNoSpace[1] + mNoSpace[2]).toLowerCase()
    // D&C sections like "dc76:22" → book=dc76, chapter=76, verses=[22]
    if (/^dc\d+$/.test(combined)) {
      const verses = parseVerses(mNoSpace[3])
      const sectionNum = parseInt(mNoSpace[2])
      return { book: combined, chapter: sectionNum, verse: verses[0] || null, verses: verses.length > 0 ? verses : null }
    }
    const book = resolveBook(mNoSpace[1])
    if (book) {
      const verses = parseVerses(mNoSpace[3])
      return { book, chapter: parseInt(mNoSpace[2]), verse: verses[0] || null, verses: verses.length > 0 ? verses : null }
    }
  }
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
  // "book.chapter" (dot between book and chapter — common in ref format)
  const mDot = text.match(/^([a-z0-9_]+)\.(\d+)$/i)
  if (mDot) {
    const book = resolveBook(mDot[1])
    if (book) return { book, chapter: parseInt(mDot[2]), verse: null, verses: null }
  }
  // "bookN" no-space ref: "isa3", "isaiah3", "gen1" etc.
  const m4 = text.match(/^([a-zA-Z]+)(\d+)$/)
  if (m4) {
    const combined = (m4[1] + m4[2]).toLowerCase()
    // Check for D&C sections like "dc76" → book=dc76, chapter=76
    if (/^dc\d+$/.test(combined)) {
      const sectionNum = parseInt(m4[2])
      return { book: combined, chapter: sectionNum, verse: null, verses: null }
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
  tob:14, jdt:16, wis:19, sir:51, bar:6, man:1,
  '1ma':16, '2ma':15, '1esd':9, '2esd':16, esga:16, s3y:1, sus:1, bel:1, psa151:1,

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
  // DSS
  '1QS':1, '1QSa':1, '1QSb':1, '1QM':1, '1QHa':1,
  '1QpHab':1, '11Q13':1, '11Q19':1, '11Q20':1, 'CD':1,
  '4Q400':20, '4Q401':1, '4Q402':1, '4Q403':1, '4Q404':1,
  '4Q405':1, '4Q406':1, '4Q407':1,
  '4Q174':1, '4Q246':1, '4Q521':1,
  '4Q266':1, '4Q267':1, '4Q268':1, '4Q269':1, '4Q270':1,
  '4Q271':1, '4Q272':1, '4Q273':1,
  '4Q394':1, '4Q395':1, '4Q396':1, '4Q397':1, '4Q398':1, '4Q399':1,
  '1Qisaa':1, '1Q20':1, bookgiants:1, visamram:1, tkohath:2,
  // Pseudepigrapha
  '1en':108, '2en':68, '3bar':17, '4bar':9,
  '1adae':79, '2adae':22, apabr:32, apelj:5,
  apsed:1, apjosh:24, ascis:11, asmos:12,
  azar:1, balin:2, jasher:91, jub:50,
  nathan:3, '5psdav':5, gad:23, grkest:16,
  rechab:22, janjam:1, josasen:29, ladjac:8,
  livprop:23, odessol:42, psssol:18,
  tabr:20, tisaac:13, tjacob:13, tjob:12,
  tsol:1, ahikar:7,
  treub:2, tsimeon:3, tlevi:5, tjudah:4,
  tdan:2, tnaph:2, tgad:2, tasher:1,
  tiss:2, tzeb:2, tjos:2, tbenj:2,
  // Expanded Canon
  '1her':4, '2her':12, '3her':9, apet:17, barn:21, gnic:23,
}

export function getChapters(bookId) {
  if (bookId?.startsWith('dc')) return [parseInt(bookId.replace('dc', ''))]
  const count = CHAPTER_MAP[bookId]
  if (!count) return [1]
  return Array.from({ length: count }, (_, i) => i + 1)
}
