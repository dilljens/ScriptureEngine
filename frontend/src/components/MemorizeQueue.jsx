import React, { useState, useEffect } from 'react'
import { parseStandardRef, resolveBook } from '../refParser'
import { parseRef, resolveBookTitle, canonicalBookId } from '../bookNames'
import CardQueue from './CardQueue'
import { currentSessionToken } from '../api'

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
  const [masteryGroups, setMasteryGroups] = useState(null) // {group: count} for the LDS 100
  const [masteryMsg, setMasteryMsg] = useState('')
  const [masteryBusy, setMasteryBusy] = useState(false)
  // Bulk select + delete (e.g. undo an accidental whole-chapter add)
  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState([]) // queue row ids
  const [bulkBusy, setBulkBusy] = useState(false)
  const [bulkMsg, setBulkMsg] = useState('')

  const sessionToken = () => currentSessionToken()
  const sessionHeaders = () => {
    const token = sessionToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // Display verse ids in normal format ("D&C 19:16", "1 Nephi 3:7").
  const fmtRef = (verseId) => {
    try {
      const info = parseRef(verseId)
      if (info?.label) return info.label
    } catch {}
    return verseId
  }

  // Resolve a typed book name via parser aliases first, then library titles
  // (covers DSS/descriptive names the alias table lacks: "Community Rule").
  const resolveMemorizeBook = (text) => resolveBook(text) || resolveBookTitle(text)

  const loadQueue = async () => {
    setLoading(true)
    try {
      const r = await fetch('/api/v1/memorize/queue', { headers: sessionHeaders() })
      const d = await r.json()
      if (d.ok) setVerses(d.data.verses)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { loadQueue() }, [])

  // Scripture Mastery (LDS 100) group counts
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/v1/memorize/mastery', { headers: sessionHeaders() })
        const d = await r.json()
        if (d.ok) setMasteryGroups(d.data.by_group)
      } catch {}
    })()
  }, [])

  const addMastery = async (group) => {
    setMasteryBusy(true)
    setMasteryMsg('')
    try {
      const r = await fetch('/api/v1/memorize/queue/mastery', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify(group ? { group, session_token: sessionToken() } : { session_token: sessionToken() }),
      })
      const d = await r.json()
      if (d.ok) {
        const skipped = (d.data.skipped || []).length
        setMasteryMsg(`Added ${d.data.verses_added} verses${skipped ? ` (${skipped} already queued or unavailable)` : ''}`)
        loadQueue()
      } else {
        setMasteryMsg('Could not add mastery set.')
      }
    } catch {
      setMasteryMsg('Could not add mastery set.')
    }
    setMasteryBusy(false)
  }

  // Search: parse refs + FTS5 fallback
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([])
      setRefResults([])
      return
    }
    const trimmed = searchQuery.trim()

    // D&C forms the generic parsers miss ("D&C 19:16", "D&C 19").
    const dcMatch = trimmed.match(/^D&C\s+(\d+)(?::(\d+(?:[-,]\d+)*))?$/i)
    if (dcMatch) {
      const sec = parseInt(dcMatch[1])
      const vs = dcMatch[2]
      const firstV = vs ? parseInt(vs.split(/[-,]/)[0]) : null
      const lastV = vs ? (vs.includes('-') ? parseInt(vs.split('-')[1]) : firstV) : null
      const verseId = firstV ? `dc${sec}.${sec}.${firstV}` : `dc${sec}.${sec}.1`
      setRefResults([{
        verseId, label: firstV ? `D&C ${sec}:${firstV}${lastV && lastV !== firstV ? `-${lastV}` : ''}` : `D&C ${sec}`,
        book: `dc${sec}`, chapter: sec,
        verseStart: firstV, verseEnd: lastV && lastV !== firstV ? lastV : null,
      }])
    } else {
    // Dot form with any-case book id ("gen.1.1", "1QS.1.1", "dc76.76.22").
    const dotMatch = trimmed.match(/^([A-Za-z0-9_]{1,8})\.(\d+)(?:\.(\d+(?:-\d+)?))?$/)
    const dotBook = dotMatch ? canonicalBookId(dotMatch[1]) : null
    if (dotMatch && (resolveBookTitle(dotBook) || /^dc\d+$/i.test(dotMatch[1]))) {
      const ch = parseInt(dotMatch[2])
      const vsPart = dotMatch[3]
      const firstV = vsPart ? parseInt(vsPart.split('-')[0]) : null
      const lastV = vsPart && vsPart.includes('-') ? parseInt(vsPart.split('-')[1]) : null
      const verseId = firstV ? `${dotBook}.${ch}.${firstV}` : `${dotBook}.${ch}.1`
      const rangeSuffix = lastV && lastV !== firstV ? `-${lastV}` : ''
      setRefResults([{
        verseId,
        label: firstV ? fmtRef(verseId) + rangeSuffix : (parseRef(`${dotBook}.${ch}`)?.label || `${dotBook} ${ch}`),
        book: dotBook, chapter: ch,
        verseStart: firstV, verseEnd: lastV && lastV !== firstV ? lastV : null,
      }])
    } else {
    // Parse as a verse reference first
    const parsed = parseStandardRef(trimmed)
    if (parsed) {
      const firstVerse = parsed.verse || 1
      const isRange = parsed.verses && parsed.verses.length > 1
      const lastVerse = isRange ? parsed.verses[parsed.verses.length - 1] : firstVerse
      const verseId = `${parsed.book}.${parsed.chapter}.${firstVerse}`
      let label = fmtRef(verseId)
      if (isRange) label += `-${lastVerse}`
      else if (!parsed.verse) label = parseRef(`${parsed.book}.${parsed.chapter}`)?.label || label
      setRefResults([{
        verseId, label,
        book: parsed.book, chapter: parsed.chapter,
        verseStart: firstVerse, verseEnd: isRange ? lastVerse : null,
      }])
    } else {
      // Try natural language: "Genesis 1" or "Genesis 1:1-5"
      const bookMatch = trimmed.match(/^([\w\s]+?)\s*(\d+)(?::(\d+(?:[-,]\d+)*))?$/)
      if (bookMatch) {
        const bookId = resolveMemorizeBook(bookMatch[1].trim())
        if (bookId) {
          const ch = parseInt(bookMatch[2])
          const vs = bookMatch[3]
          const firstV = vs ? parseInt(vs.split(/[-,]/)[0]) : null
          const lastV = vs ? (vs.includes('-') ? parseInt(vs.split('-')[1]) : firstV) : null
          const verseId = firstV ? `${bookId}.${ch}.${firstV}` : `${bookId}.${ch}`
          setRefResults([{
            verseId,
            label: firstV
              ? fmtRef(verseId) + (lastV && lastV !== firstV ? `-${lastV}` : '')
              : (parseRef(`${bookId}.${ch}`)?.label || trimmed),
            book: bookId, chapter: ch,
            verseStart: firstV, verseEnd: lastV || null,
          }])
        } else {
          setRefResults([])
        }
      } else {
        setRefResults([])
      }
    } // end parseStandardRef else
    } // end dot-form else
    } // end D&C else

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
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify({ verse_id: verseId, session_token: sessionToken() }),
      })
      loadQueue()
    } catch {}
  }

  const addRange = async (ref) => {
    if (!ref) return
    try {
      await fetch('/api/v1/memorize/queue/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify({
          book: ref.book,
          chapter: ref.chapter,
          verse_start: ref.verseStart,
          verse_end: ref.verseEnd,
          session_token: sessionToken(),
        }),
      })
      loadQueue()
    } catch {}
  }

  const removeVerse = async (id) => {
    try {
      await fetch(`/api/v1/memorize/queue/${id}?session_token=${encodeURIComponent(sessionToken())}`, {
        method: 'DELETE', headers: sessionHeaders(),
      })
      loadQueue()
    } catch {}
  }

  const toggleSelect = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const deleteSelected = async () => {
    if (selected.length === 0 || bulkBusy) return
    setBulkBusy(true)
    setBulkMsg('')
    try {
      const r = await fetch('/api/v1/memorize/queue/delete-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify({ ids: selected, session_token: sessionToken() }),
      })
      const d = await r.json()
      if (d.ok) {
        setBulkMsg(`Removed ${d.data.removed} verse${d.data.removed === 1 ? '' : 's'}.`)
        setSelected([])
        loadQueue()
      } else {
        setBulkMsg('Could not remove verses.')
      }
    } catch {
      setBulkMsg('Could not remove verses.')
    }
    setBulkBusy(false)
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
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify({
          rating,
          session_token: sessionToken(),
          preview_mode: card.data?.preview_mode || 'none',
          preview_level: card.data?.preview_level || 0,
        }),
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

      {/* Scripture Mastery (LDS 100) bulk import */}
      <details className="mb-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800">
        <summary className="text-xs font-medium text-amber-800 dark:text-amber-300 cursor-pointer">
          📜 Scripture Mastery — add the LDS 100 to your queue
        </summary>
        <p className="text-[11px] text-amber-700 dark:text-amber-400 mt-2 mb-2">
          25 Old Testament · 25 New Testament · 25 Book of Mormon · 25 Doctrine &amp; Covenants.
          Multi-verse passages are added verse by verse.
        </p>
        <div className="flex flex-wrap gap-1.5">
          {(masteryGroups ? Object.keys(masteryGroups) : ['Old Testament', 'New Testament', 'Book of Mormon', 'Doctrine and Covenants']).map(g => (
            <button key={g} onClick={() => addMastery(g)} disabled={masteryBusy}
              className="px-2 py-1 rounded text-[10px] font-medium bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50 cursor-pointer transition-colors">
              + {g.replace(' Testament', 'T').replace('Book of Mormon', 'BoM').replace('Doctrine and Covenants', 'D&C')}
            </button>
          ))}
          <button onClick={() => addMastery(null)} disabled={masteryBusy}
            className="px-2 py-1 rounded text-[10px] font-medium bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 cursor-pointer transition-colors">
            + All 100
          </button>
        </div>
        {masteryMsg && <p className="text-[11px] text-amber-700 dark:text-amber-300 mt-2">{masteryMsg}</p>}
      </details>

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
                {r.verseStart && !r.verseEnd ? (
                  <button onClick={() => addVerse(r.verseId)}
                    className="px-2 py-1 rounded text-[10px] font-medium bg-indigo-600 text-white hover:bg-indigo-700 cursor-pointer transition-colors">
                    + Verse
                  </button>
                ) : null}
                <button onClick={() => addRange(r)}
                  className="px-2 py-1 rounded text-[10px] font-medium bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer transition-colors">
                  {r.verseEnd && r.verseStart
                    ? `+ Range (${r.verseEnd - r.verseStart + 1}v)`
                    : String(r.book || '').startsWith('dc') ? '+ Section' : '+ Chapter'}
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
                    <button onClick={() => { const p = (r.verse || r.verse_id || '').split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: canonicalBookId(p[0]), chapter: parseInt(p[1])}})) }}
                      className="text-[11px] font-mono text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-200 cursor-pointer transition-colors">{fmtRef(r.verse || r.verse_id)}</button>
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
              <button onClick={() => { setSelectMode(m => !m); setSelected([]); setBulkMsg('') }}
                aria-label={selectMode ? 'Done selecting' : 'Select verses to delete'}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                  selectMode
                    ? 'bg-neutral-600 hover:bg-neutral-700 text-white'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                }`}>
                {selectMode ? 'Done' : 'Select'}
              </button>
              {dueCount > 0 && !selectMode && (
                <button onClick={onStartReview}
                  className="px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-medium cursor-pointer transition-colors">
                  Start Review ({dueCount})
                </button>
              )}
            </div>
          </div>
          {/* Bulk action bar */}
          {selectMode && (
            <div className="flex items-center gap-2 mb-2 p-2 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <span className="text-[11px] font-medium text-neutral-600 dark:text-neutral-300 mr-auto">
                {selected.length === 0 ? 'Tap verses to select' : `${selected.length} selected`}
              </span>
              <button onClick={() => setSelected(verses.map(v => v.id))}
                className="px-2.5 py-1.5 rounded-lg text-[11px] font-medium text-neutral-600 dark:text-neutral-300 hover:bg-black/5 dark:hover:bg-white/10 cursor-pointer transition-colors min-h-[36px]">
                Select all
              </button>
              <button onClick={deleteSelected} disabled={selected.length === 0 || bulkBusy}
                className="pressable px-3 py-1.5 rounded-lg bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white text-[11px] font-medium cursor-pointer transition-colors min-h-[36px]">
                {bulkBusy ? 'Removing…' : `Delete${selected.length ? ` (${selected.length})` : ''}`}
              </button>
            </div>
          )}
          {bulkMsg && <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mb-2">{bulkMsg}</p>}
          {verses.map(v => (
            <div key={v.id}
              onClick={() => selectMode ? toggleSelect(v.id) : startVerseReview(v)}
              className={`p-3 rounded-xl bg-white dark:bg-neutral-800 border cursor-pointer transition-all flex items-start gap-2.5 ${
                selectMode && selected.includes(v.id)
                  ? 'border-red-400 dark:border-red-600 ring-1 ring-red-300 dark:ring-red-800'
                  : 'border-neutral-200 dark:border-neutral-700 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-sm'
              }`}>
              {selectMode && (
                <span aria-hidden="true"
                  className={`mt-0.5 w-6 h-6 rounded-md border-2 flex items-center justify-center text-sm shrink-0 transition-colors ${
                    selected.includes(v.id)
                      ? 'bg-red-600 border-red-600 text-white'
                      : 'border-neutral-300 dark:border-neutral-600 text-transparent'
                  }`}>
                  ✓
                </span>
              )}
              <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <span className="text-xs font-mono font-medium text-indigo-600 dark:text-indigo-400">{fmtRef(v.verse_id)}</span>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5 line-clamp-2" dir={displayLang === 'hebrew' ? 'rtl' : 'ltr'}>
                    {verseText(v)}
                  </p>
                </div>
                {!selectMode && (
                <button onClick={(e) => { e.stopPropagation(); removeVerse(v.id) }}
                  aria-label={`Remove ${fmtRef(v.verse_id)} from queue`}
                  className="ml-2 text-neutral-300 hover:text-red-500 cursor-pointer text-sm shrink-0">✕</button>
                )}
              </div>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-neutral-400">
                <span>Mastery: {Math.round((v.mastery || 0) * 100)}%</span>
                <span>Attempts: {v.attempts || 0}</span>
                {!selectMode && <span className="ml-auto text-[9px] text-indigo-400 hover:text-indigo-600">Click to review →</span>}
              </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
