/**
 * Scroll memory — remembers the first-visible verse per tab so returning to
 * a reading tab (or reloading) lands where you left off, not at the top.
 *
 * Stored OUTSIDE the tab reducer on purpose: writing on every scroll would
 * re-render the whole tab context each time. Keyed by tab id (stable across
 * reloads via scripture_tabs), LRU-capped so closed tabs age out.
 */

const KEY = 'scripture_scroll'
const MAX_ENTRIES = 50

function loadAll() {
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? JSON.parse(raw) : null
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

function writeAll(map) {
  try {
    // LRU eviction: keep the freshest entries only
    const entries = Object.entries(map).sort((a, b) => (b[1]?.ts || 0) - (a[1]?.ts || 0))
    const trimmed = Object.fromEntries(entries.slice(0, MAX_ENTRIES))
    localStorage.setItem(KEY, JSON.stringify(trimmed))
  } catch {}
}

export function saveScrollPos(tabId, book, chapter, verse) {
  if (!tabId || !book || !chapter || !verse) return
  const map = loadAll()
  const prev = map[tabId]
  if (prev && prev.book === book && prev.chapter === chapter && prev.verse === verse) return
  map[tabId] = { book, chapter, verse, ts: Date.now() }
  writeAll(map)
}

export function readScrollPos(tabId) {
  if (!tabId) return null
  const entry = loadAll()[tabId]
  return entry && entry.book && entry.chapter && entry.verse ? entry : null
}

export function clearScrollPos(tabId) {
  if (!tabId) return
  const map = loadAll()
  if (map[tabId]) {
    delete map[tabId]
    writeAll(map)
  }
}

/** Parse a ChapterView verse anchor id ("verse-gen.1.1") → {book, chapter, verse}. */
export function parseVerseAnchor(id) {
  if (typeof id !== 'string' || !id.startsWith('verse-')) return null
  const parts = id.slice('verse-'.length).split('.')
  if (parts.length !== 3) return null
  const [book, chStr, vsStr] = parts
  const chapter = parseInt(chStr)
  const verse = parseInt(vsStr)
  if (!book || isNaN(chapter) || isNaN(verse)) return null
  return { book, chapter, verse }
}
