import React, { useState, useEffect } from 'react'
import { parseStandardRef, resolveBook } from '../refParser'
import CardQueue from './CardQueue'

const LANGUAGES = [
  { id: 'english', label: 'English', field: 'text_english' },
  { id: 'hebrew', label: 'עברית', field: 'text_hebrew' },
  { id: 'greek', label: 'Ελληνικά', field: 'text_greek' },
]

/**
 * MemorizeQueue — manage a queue of verses to memorize.
 * Users can search verses, add them to the queue, and start reviews.
 * Supports verse ranges and language selection.
 */
export default function MemorizeQueue({ onStartReview }) {
  const [verses, setVerses] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [refResults, setRefResults] = useState([])
  const [activeView, setActiveView] = useState('queue')
  const [displayLang, setDisplayLang] = useState('english')
  const [reviewVerse, setReviewVerse] = useState(null) // single-verse quick review
  const [reviewLang, setReviewLang] = useState('hebrew') // Anki-style: show target language first

  const loadQueue = async () => {
    setLoading(true)
    try {
      const r = await fetch('/api/v1/memorize/queue')
      const d = await r.json()
      if (d.ok) setVerses(d.data.verses)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { loadQueue() }, [])

  // Search: parse refs + FTS5 fallback
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([])
      setRefResults([])
      return
    }
    const trimmed = searchQuery.trim()

    // Parse as a verse reference first
    const parsed = parseStandardRef(trimmed)
    if (parsed) {
      const firstVerse = parsed.verse || 1
      const isRange = parsed.verses && parsed.verses.length > 1
      const lastVerse = isRange ? parsed.verses[parsed.verses.length - 1] : firstVerse
      const verseId = `${parsed.book}.${parsed.chapter}.${firstVerse}`
      let label = `${parsed.book} ${parsed.chapter}:${firstVerse}`
      if (isRange) label += `-${lastVerse}`
      else if (!parsed.verse) label = `${parsed.book} ${parsed.chapter}`
      setRefResults([{
        verseId, label,
        book: parsed.book, chapter: parsed.chapter,
        verseStart: firstVerse, verseEnd: isRange ? lastVerse : null,
      }])
    } else {
      // Try natural language: "Genesis 1" or "Genesis 1:1-5"
      const bookMatch = trimmed.match(/^([\w\s]+?)\s*(\d+)(?::(\d+(?:[-,]\d+)*))?$/)
      if (bookMatch) {
        const bookId = resolveBook(bookMatch[1].trim())
        if (bookId) {
          const ch = parseInt(bookMatch[2])
          const vs = bookMatch[3]
          const firstV = vs ? parseInt(vs.split(/[-,]/)[0]) : null
          const lastV = vs ? (vs.includes('-') ? parseInt(vs.split('-')[1]) : firstV) : null
          const verseId = firstV ? `${bookId}.${ch}.${firstV}` : `${bookId}.${ch}`
          setRefResults([{
            verseId, label: trimmed,
            book: bookId, chapter: ch,
            verseStart: firstV, verseEnd: lastV || null,
          }])
        } else {
          setRefResults([])
        }
      } else {
        setRefResults([])
      }
    }

    // FTS5 text search as supplement
    const timer = setTimeout(async () => {
      try {
        const r = await fetch(`/api/v1/search?q=${encodeURIComponent(trimmed)}&limit=10`)
        const d = await r.json()
        if (d.ok) setSearchResults(d.data.results || [])
      } catch {}
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  const addVerse = async (verseId) => {
    try {
      await fetch('/api/v1/memorize/queue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verse_id: verseId }),
      })
      loadQueue()
    } catch {}
  }

  const addRange = async (ref) => {
    if (!ref) return
    try {
      await fetch('/api/v1/memorize/queue/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          book: ref.book,
          chapter: ref.chapter,
          verse_start: ref.verseStart,
          verse_end: ref.verseEnd,
        }),
      })
      loadQueue()
    } catch {}
  }

  const removeVerse = async (id) => {
    try {
      await fetch(`/api/v1/memorize/queue/${id}`, { method: 'DELETE' })
      loadQueue()
    } catch {}
  }

  const dueCount = verses.filter(v => v.attempts === 0 || (v.mastery || 0) < 0.8).length

  // Get text for the current display language
  const verseText = (v) => {
    const lang = LANGUAGES.find(l => l.id === displayLang)
    return v[lang?.field || 'text_english'] || v.text_english || ''
  }

  // Quick review single verse
  const startVerseReview = (v) => {
    const card = {
      id: v.queue_id || v.id || v.verse_id,
      type: 'verse',
      queue_id: v.queue_id || v.id,
      data: {
        reference: v.verse_id,
        text: v[v.langField || 'text_hebrew'] || v.text_hebrew || v.text_english || '',
        book: v.verse_id?.split('.')[0],
        chapter: parseInt(v.verse_id?.split('.')[1]) || 1,
        verse: parseInt(v.verse_id?.split('.')[2]) || 1,
      },
    }
    setReviewLang('hebrew') // Start in target language (Anki-style)
    setReviewVerse(card)
  }

  const handleVerseReviewRate = async (card, rating) => {
    if (card.queue_id) {
      await fetch(`/api/v1/memorize/review/${card.queue_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating }),
      })
    }
    setReviewVerse(null)
    loadQueue()
  }

  // Single-verse review mode
  if (reviewVerse) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <button onClick={() => { setReviewVerse(null); loadQueue() }}
            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Queue
          </button>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-neutral-400">Display:</span>
            <select value={reviewLang} onChange={e => setReviewLang(e.target.value)}
              className="text-[10px] px-1.5 py-0.5 rounded border border-neutral-200 dark:border-neutral-700 bg-transparent text-neutral-500 dark:text-neutral-400 outline-none cursor-pointer">
              <option value="hebrew">עברית</option>
              <option value="english">English</option>
            </select>
            <span className="text-[9px] text-amber-500">(switching resets mastery)</span>
          </div>
        </div>
        {reviewLang === 'hebrew' ? (
          <CardQueue
            cards={[reviewVerse]}
            onRate={handleVerseReviewRate}
            onComplete={() => { setReviewVerse(null); loadQueue() }}
            title="Quick Review"
            emptyMessage=""
          />
        ) : (
          <CardQueue
            cards={[{
              ...reviewVerse,
              data: { ...reviewVerse.data, text: verses.find(v => v.verse_id === reviewVerse.data.reference)?.['text_english'] || '' }
            }]}
            onRate={handleVerseReviewRate}
            onComplete={() => { setReviewVerse(null); loadQueue() }}
            title="Quick Review (English)"
            emptyMessage=""
          />
        )}
      </div>
    )
  }

  // Check if input looks like a verse ref for "Add" button
  const isRef = (() => {
    const t = searchQuery.trim()
    if (!t) return false
    if (t.includes('.')) return true
    if (t.match(/^[\w\s]+\s+\d+/)) return true
    return false
  })()

  // Merge ref results + FTS5 results
  const allResults = [
    ...refResults.map(r => ({ ...r, _isRef: true })),
    ...(refResults.length > 0 && searchResults.length > 0 ? [{ _isDivider: true }] : []),
    ...searchResults.map(r => ({ ...r, _isRef: false })),
  ]

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Memorize</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
        Add verses to your queue for spaced repetition review.
      </p>

      {/* Search/add bar */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={searchQuery}
          onChange={e => { setSearchQuery(e.target.value); setActiveView('search') }}
          placeholder="e.g., Genesis 1:1-5, gen.1, isa 55:6, psa.23"
          className="flex-1 px-3 py-2 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 focus:border-indigo-400 outline-none transition-all"
        />
        {isRef && (
          <select value={displayLang} onChange={e => setDisplayLang(e.target.value)}
            className="px-2 py-2 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 outline-none cursor-pointer">
            {LANGUAGES.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}
          </select>
        )}
      </div>

      {/* Combined search results */}
      {activeView === 'search' && allResults.length > 0 && (
        <div className="mb-4 p-3 rounded-xl bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
          {refResults.length > 0 && (
            <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">📍 Reference</p>
          )}
          {refResults.map((r, i) => (
            <div key={r.verseId} className="flex items-center justify-between py-1.5">
              <div>
                <span className="text-sm text-indigo-700 dark:text-indigo-300 font-medium">{r.label}</span>
                {r.verseStart && !r.verseEnd && (
                  <span className="text-[10px] text-neutral-400 ml-2">1 verse</span>
                )}
                {r.verseEnd && (
                  <span className="text-[10px] text-amber-600 dark:text-amber-400 ml-2">
                    {r.verseEnd - r.verseStart + 1} verses
                  </span>
                )}
              </div>
              <div className="flex gap-1.5">
                {!r.verseEnd ? (
                  <button onClick={() => addVerse(r.verseId)}
                    className="px-2 py-1 rounded text-[10px] font-medium bg-indigo-600 text-white hover:bg-indigo-700 cursor-pointer transition-colors">
                    + Verse
                  </button>
                ) : null}
                <button onClick={() => addRange(r)}
                  className="px-2 py-1 rounded text-[10px] font-medium bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer transition-colors">
                  {r.verseEnd && r.verseStart
                    ? `+ Range (${r.verseEnd - r.verseStart + 1}v)`
                    : '+ Chapter'}
                </button>
              </div>
            </div>
          ))}
          {searchResults.length > 0 && (
            <>
              {refResults.length > 0 && <div className="border-t border-neutral-200 dark:border-neutral-600 my-1" />}
              <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mt-2 mb-2">🔍 Text Search</p>
              {searchResults.slice(0, 8).map(r => (
                <div key={r.verse || r.verse_id} className="flex items-center justify-between py-1.5 border-b border-neutral-100 dark:border-neutral-700 last:border-0">
                  <div className="min-w-0 flex-1 mr-2">
                    <span className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400">{r.verse || r.verse_id}</span>
                    <span className="text-[10px] text-neutral-500 dark:text-neutral-400 ml-1">{(r.book || '').toUpperCase()}</span>
                    <p className="text-[11px] text-neutral-600 dark:text-neutral-400 mt-0.5 truncate">{(r.text || r.text_english || '').slice(0, 80)}</p>
                  </div>
                  <button onClick={() => addVerse(r.verse || r.verse_id)}
                    className="px-2 py-1 rounded text-[10px] font-medium bg-indigo-600 text-white hover:bg-indigo-700 cursor-pointer transition-colors shrink-0">
                    + Add
                  </button>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* Queue */}
      {loading ? (
        <div className="animate-pulse space-y-3">
          {[1,2,3].map(i => <div key={i} className="h-16 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
        </div>
      ) : verses.length === 0 ? (
        <div className="p-8 text-center text-sm text-neutral-400">
          No verses in your queue. Search above to add some.
        </div>
      ) : (
        <div className="space-y-2">
          {/* Language selector for display */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
              {verses.length} verses · {dueCount} due for review
            </span>
            <div className="flex items-center gap-2">
              <select value={displayLang} onChange={e => setDisplayLang(e.target.value)}
                className="text-[10px] px-1.5 py-0.5 rounded border border-neutral-200 dark:border-neutral-700 bg-transparent text-neutral-500 dark:text-neutral-400 outline-none cursor-pointer">
                {LANGUAGES.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}
              </select>
              {dueCount > 0 && (
                <button onClick={onStartReview}
                  className="px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-medium cursor-pointer transition-colors">
                  Start Review ({dueCount})
                </button>
              )}
            </div>
          </div>
          {verses.map(v => (
            <div key={v.id}
              onClick={() => startVerseReview(v)}
              className="p-3 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-sm cursor-pointer transition-all">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <span className="text-xs font-mono font-medium text-indigo-600 dark:text-indigo-400">{v.verse_id}</span>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5 line-clamp-2" dir={displayLang === 'hebrew' ? 'rtl' : 'ltr'}>
                    {verseText(v)}
                  </p>
                </div>
                <button onClick={(e) => { e.stopPropagation(); removeVerse(v.id) }}
                  className="ml-2 text-neutral-300 hover:text-red-500 cursor-pointer text-sm shrink-0">✕</button>
              </div>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-neutral-400">
                <span>Mastery: {Math.round((v.mastery || 0) * 100)}%</span>
                <span>Attempts: {v.attempts || 0}</span>
                <span className="ml-auto text-[9px] text-indigo-400 hover:text-indigo-600">Click to review →</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
