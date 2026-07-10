import React, { useState, useEffect } from 'react'

/**
 * MemorizeQueue — manage a queue of verses to memorize.
 * Users can search verses, add them to the queue, and start reviews.
 */
export default function MemorizeQueue({ onStartReview }) {
  const [verses, setVerses] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [activeView, setActiveView] = useState('queue') // queue | search 

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

  // Search for verses to add
  useEffect(() => {
    if (!searchQuery || searchQuery.length < 2) {
      setSearchResults([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const r = await fetch(`/api/v1/search?q=${encodeURIComponent(searchQuery)}&limit=10`)
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

  const addChapter = async () => {
    const parts = searchQuery.split('.')
    if (parts.length >= 2) {
      try {
        await fetch('/api/v1/memorize/queue/batch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ book: parts[0], chapter: parseInt(parts[1]) }),
        })
        loadQueue()
      } catch {}
    }
  }

  const removeVerse = async (id) => {
    try {
      await fetch(`/api/v1/memorize/queue/${id}`, { method: 'DELETE' })
      loadQueue()
    } catch {}
  }

  const dueCount = verses.filter(v => v.attempts === 0 || (v.mastery || 0) < 0.8).length

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
          placeholder="Search by reference (e.g., gen.1.1 or psa.23)"
          className="flex-1 px-3 py-2 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 focus:border-indigo-400 outline-none transition-all"
        />
        {searchQuery.includes('.') && (
          <button onClick={addChapter}
            className="px-3 py-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-xs font-medium cursor-pointer hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors">
            Add Chapter
          </button>
        )}
      </div>

      {/* Search results */}
      {activeView === 'search' && searchResults.length > 0 && (
        <div className="mb-4 p-3 rounded-xl bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Search Results</p>
          {searchResults.slice(0, 8).map(r => (
            <div key={r.id} className="flex items-center justify-between py-1.5 border-b border-neutral-100 dark:border-neutral-700 last:border-0">
              <div>
                <span className="text-sm text-neutral-700 dark:text-neutral-300">{r.title}</span>
                <span className="text-[10px] text-neutral-400 ml-2">{r.subtitle}</span>
              </div>
              <button onClick={() => addVerse(r.id)}
                className="px-2 py-1 rounded text-[10px] font-medium bg-indigo-600 text-white hover:bg-indigo-700 cursor-pointer transition-colors">
                + Add
              </button>
            </div>
          ))}
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
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
              {verses.length} verses · {dueCount} due for review
            </span>
            {dueCount > 0 && (
              <button onClick={onStartReview}
                className="px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-medium cursor-pointer transition-colors">
                Start Review ({dueCount})
              </button>
            )}
          </div>
          {verses.map(v => (
            <div key={v.id} className="p-3 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <span className="text-xs font-mono font-medium text-indigo-600 dark:text-indigo-400">{v.verse_id}</span>
                  <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-0.5 line-clamp-2">{v.text}</p>
                </div>
                <button onClick={() => removeVerse(v.id)}
                  className="ml-2 text-neutral-300 hover:text-red-500 cursor-pointer text-sm shrink-0">✕</button>
              </div>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-neutral-400">
                <span>Mastery: {Math.round((v.mastery || 0) * 100)}%</span>
                <span>Attempts: {v.attempts || 0}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
