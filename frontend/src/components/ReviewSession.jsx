import React, { useEffect, useState, useCallback, useRef } from 'react'
import { memorizeApi } from '../memorizeApi'

const RATINGS = [
  { key: 'again', value: 1, label: 'Again', shortcut: '1', color: 'bg-red-500 hover:bg-red-600' },
  { key: 'hard',  value: 2, label: 'Hard',  shortcut: '2', color: 'bg-amber-500 hover:bg-amber-600' },
  { key: 'good',  value: 3, label: 'Good',  shortcut: '3', color: 'bg-green-500 hover:bg-green-600' },
  { key: 'easy',  value: 4, label: 'Easy',  shortcut: '4', color: 'bg-blue-500 hover:bg-blue-600' },
]

const HINT_LABELS = [
  'Full text',
  'First letters',
  'Image cue',
  'Reference only',
  'Connection hint',
  'Blank recall',
]

function firstLetters(text) {
  return text.split(' ').map(w => w[0]).join(' ')
}

export default function ReviewSession({ onDone }) {
  const [queue, setQueue] = useState([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)
  const [stats, setStats] = useState({ dueCards: 0, totalCards: 0, mastered: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [conceptImage, setConceptImage] = useState(null)
  const [remediation, setRemediation] = useState([])
  const [connectionHint, setConnectionHint] = useState(null)
  const imageFetched = useRef({})
  const connectionFetched = useRef({})

  const loadQueue = useCallback(async () => {
    try {
      const [queueData, statsData] = await Promise.all([
        memorizeApi.get('/queue?limit=20'),
        memorizeApi.get('/stats'),
      ])
      setQueue(queueData.cards || [])
      setStats(statsData.stats || {})
      setCurrentIdx(0)
      setShowAnswer(false)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadQueue() }, [loadQueue])

  // Load hint resources when answer shown
  useEffect(() => {
    const card = queue[currentIdx]
    if (!card || !showAnswer) return
    const hl = card.HintLevel || 0

    // Level 2: load concept image
    if (hl >= 2 && !imageFetched.current[card.CardID]) {
      imageFetched.current[card.CardID] = true
      const img = new Image()
      img.onload = () => setConceptImage(`/api/memorize/images/${card.VerseID}?t=${Date.now()}`)
      img.onerror = () => setConceptImage(null)
      img.src = `/api/memorize/images/${card.VerseID}`
    }

    // Level 4: fetch connection hint from API
    if (hl >= 4 && !connectionFetched.current[card.CardID]) {
      connectionFetched.current[card.CardID] = true
      fetch(`/api/v1/search?q=${encodeURIComponent(card.VerseText.split(' ').slice(0, 3).join(' '))}&limit=1`)
        .then(r => r.json())
        .then(d => {
          if (d.results?.length > 0 && d.results[0].id !== card.VerseID) {
            setConnectionHint(d.results[0])
          }
        })
        .catch(() => {})
    }
  }, [showAnswer, currentIdx, queue])

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key === ' ' || e.key === 'Space') {
        e.preventDefault()
        if (!showAnswer) setShowAnswer(true)
        return
      }
      if (showAnswer && !submitting) {
        const rating = RATINGS.find(r => r.shortcut === e.key)
        if (rating) handleRate(rating.value)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [showAnswer, submitting, currentIdx])

  const handleRate = async (rating) => {
    const card = queue[currentIdx]
    if (!card) return
    setSubmitting(true)
    try {
      const result = await memorizeApi.post(`/review/${card.CardID}`, { rating })
      setRemediation(result.remediation || [])
      if (currentIdx + 1 < queue.length) {
        setCurrentIdx(i => i + 1)
        setShowAnswer(false)
        setConceptImage(null)
        setConnectionHint(null)
        setRemediation([])
      } else {
        await loadQueue()
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Render ──

  if (loading) {
    return <div className="flex items-center justify-center py-20 text-neutral-400"><div className="animate-pulse">Loading review queue...</div></div>
  }

  if (error) {
    return (
      <div className="max-w-lg mx-auto p-4">
        <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30 p-4 text-sm text-red-700 dark:text-red-400">
          <p className="font-medium">Error</p>
          <p className="mt-1 text-xs">{error}</p>
          <button onClick={loadQueue} className="mt-2 text-xs underline">Retry</button>
        </div>
      </div>
    )
  }

  if (queue.length === 0) {
    return (
      <div className="max-w-lg mx-auto p-4 text-center">
        <div className="py-12">
          <div className="text-4xl mb-3">🎉</div>
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-1">All caught up!</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
            {stats.mastered > 0 ? `${stats.mastered} verses mastered. Great work!` : 'Add verses to memorize from any chapter view.'}
          </p>
          <button onClick={onDone} className="text-sm text-indigo-500 hover:text-indigo-600 underline">Back to dashboard</button>
        </div>
      </div>
    )
  }

  const card = queue[currentIdx]
  const hintLevel = card.HintLevel || 0

  // Render hint based on level
  const renderHint = () => {
    if (showAnswer) {
      // Reveal answer — show full text regardless of level
      return card.VerseText
    }
    switch (hintLevel) {
      case 0: return card.VerseText
      case 1: return firstLetters(card.VerseText)
      case 2: return '' // image only, no text
      case 3: return '[Reference only]'
      case 4: return connectionHint ? `Hint: ${connectionHint.id} — ${connectionHint.text?.slice(0, 60)}...` : firstLetters(card.VerseText)
      case 5: return ''
      default: return firstLetters(card.VerseText)
    }
  }

  return (
    <div className="max-w-lg mx-auto p-4">
      {/* Progress bar */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-800 rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500 rounded-full transition-all duration-300" style={{ width: `${((currentIdx) / queue.length) * 100}%` }} />
        </div>
        <span className="text-[10px] text-neutral-400 font-medium tabular-nums">{queue.length - currentIdx} left</span>
      </div>

      {/* Reference + Hint Level */}
      <div className="flex items-center justify-center gap-2 mb-4">
        <span className="text-xs font-medium text-indigo-500 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950/40 px-2 py-0.5 rounded-full">
          {card.Reference}
        </span>
        <span className="text-[10px] text-neutral-400 bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded">
          L{hintLevel}: {HINT_LABELS[hintLevel] || 'Unknown'}
        </span>
      </div>

      {/* Verse card */}
      <div className="bg-white dark:bg-neutral-900 rounded-xl border border-neutral-200 dark:border-neutral-800 overflow-hidden mb-6 shadow-sm">
        {/* Concept image for level 2+ */}
        {showAnswer && hintLevel >= 2 && conceptImage && (
          <div className="w-full h-48 overflow-hidden bg-neutral-100 dark:bg-neutral-800">
            <img src={conceptImage} alt="Concept illustration" className="w-full h-full object-cover" />
          </div>
        )}
        <div className="p-6 min-h-[100px] flex items-center justify-center">
          <p className="text-lg leading-relaxed text-neutral-800 dark:text-neutral-200 text-center font-serif">
            {renderHint() || (showAnswer ? card.VerseText : '—')}
          </p>
        </div>
      </div>

      {/* Hint level dots */}
      <div className="flex justify-center gap-1 mb-4">
        {[0, 1, 2, 3, 4, 5].map(level => (
          <div key={level} className={`w-2 h-2 rounded-full ${level <= hintLevel ? 'bg-indigo-400' : 'bg-neutral-200 dark:bg-neutral-700'}`} />
        ))}
      </div>

      {/* Remediation suggestions (shown after failed review) */}
      {remediation.length > 0 && (
        <div className="mb-4 p-3 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 mb-2">You might want to review these connected verses:</p>
          {remediation.map((r, i) => (
            <div key={i} className="text-xs text-amber-600 dark:text-amber-300 mb-1">
              <button onClick={() => { const p = (r.verse_id || '').split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}})) }}
                className="font-medium hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer transition-colors">{r.verse_id}</button>
              <span className="opacity-60"> ({r.conn_type})</span>
              <p className="text-[11px] text-amber-500 dark:text-amber-400 mt-0.5">{r.text}</p>
            </div>
          ))}
        </div>
      )}

      {/* Show answer button */}
      {!showAnswer && (
        <button onClick={() => setShowAnswer(true)} className="w-full py-3 px-4 rounded-lg border-2 border-dashed border-neutral-300 dark:border-neutral-700 text-sm text-neutral-500 dark:text-neutral-400 hover:border-indigo-400 hover:text-indigo-500 transition-colors mb-4">
          Show Answer <span className="text-[10px] opacity-50">(Space)</span>
        </button>
      )}

      {/* Rating buttons */}
      {showAnswer && (
        <div className="grid grid-cols-4 gap-2">
          {RATINGS.map(r => (
            <button key={r.key} onClick={() => handleRate(r.value)} disabled={submitting}
              className={`${r.color} text-white text-sm font-medium py-3 px-2 rounded-lg transition-all disabled:opacity-50`}>
              <div>{r.label}</div>
              <div className="text-[10px] opacity-70 mt-0.5">{r.shortcut}</div>
            </button>
          ))}
        </div>
      )}

      {/* Stats footer */}
      <div className="flex justify-center gap-4 mt-6 text-[10px] text-neutral-400">
        <span>{stats.totalCards || '-'} cards</span>
        <span>{queue.length} due</span>
        <span>{stats.mastered || 0} mastered</span>
      </div>
    </div>
  )
}
