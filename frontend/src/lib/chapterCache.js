/**
 * chapterCache — tiny shared read-through cache for chapter JSON.
 *
 * VersePopup and VersePreviewCard both fetch `/api/v1/chapter/:book.:ch`.
 * This module lets ChatPanel *prefetch* chapters for refs visible in the
 * conversation (hover intent + idle sweep), so tapping a reference opens
 * the drawer instantly instead of showing a loading spinner.
 *
 * Plain fetch cache (not HTTP cache) so prefetches survive across
 * components within the session. Entries live for the session only.
 */

const cache = new Map() // key "book.chapter" -> chapter data (d.data)
const inflight = new Map() // key -> Promise

export function chapterKey(book, chapter) {
  return `${String(book).toLowerCase()}.${parseInt(chapter) || 1}`
}

export function getCachedChapter(book, chapter) {
  return cache.get(chapterKey(book, chapter)) || null
}

export function setCachedChapter(book, chapter, data) {
  cache.set(chapterKey(book, chapter), data)
}

/** Fetch chapter JSON once; concurrent callers share the promise. */
export function prefetchChapter(book, chapter) {
  if (!book || chapter == null) return Promise.resolve(null)
  const key = chapterKey(book, chapter)
  if (cache.has(key)) return Promise.resolve(cache.get(key))
  if (inflight.has(key)) return inflight.get(key)
  const p = fetch(`/api/v1/chapter/${book}.${parseInt(chapter) || 1}`)
    .then((r) => r.json())
    .then((d) => {
      if (d?.ok && d?.data) {
        cache.set(key, d.data)
        return d.data
      }
      return null
    })
    .catch(() => null)
    .finally(() => inflight.delete(key))
  inflight.set(key, p)
  return p
}

/** Split a verse id like "isa.55.6-8" into { book, chapter } for prefetch. */
export function bookChapterOf(ref) {
  const parts = String(ref || '').split('.')
  if (parts.length < 2) return null
  // D&C sections ("dc76.76.22", "dc76") carry the chapter in the book part.
  const dc = parts[0].match(/^dc(\d+)$/i)
  if (dc) return { book: parts[0].toLowerCase(), chapter: parseInt(parts[1]) || parseInt(dc[1]) }
  return { book: parts[0], chapter: parseInt(parts[1]) || 1 }
}
