import React, { useState, useCallback, useEffect } from 'react'
import CardRenderer from './CardRenderer'

/**
 * CardQueue — generic spaced-repetition card queue.
 *
 * Takes any array of cards (verse, knowledge, connection, gematria, etc.)
 * and presents them one at a time with FSRS-style rating.
 *
 * Props:
 *   cards: array of { id, type, data, queue_id }
 *   onRate: async (card, rating) => {} — called when user rates a card
 *   onComplete: () => {} — called when all cards reviewed
 *   title: string — optional heading
 *   emptyMessage: string — shown when cards is empty
 *   onAnswer: (card, answer) => {} — called when user answers a learn_question (before rating)
 *   answerState: object — extra state to pass to CardRenderer (e.g. LLM grade)
 *   hebrewOnly: boolean — hide English transliteration on vocab cards
 */
export default function CardQueue({ cards, onRate, onComplete, title, emptyMessage, onAnswer, answerState, hebrewOnly: hebrewOnlyProp }) {
  // Read hebrewOnly from settings context, fall back to prop
  let hebrewOnly = hebrewOnlyProp
  try {
    const settings = JSON.parse(localStorage.getItem('settings') || '{}')
    if (settings.hebrewOnly !== undefined) hebrewOnly = settings.hebrewOnly
  } catch {}
  const [idx, setIdx] = useState(0)
  const [rating, setRating] = useState(null)
  const [showAnswer, setShowAnswer] = useState(false)
  const [results, setResults] = useState([])
  const [done, setDone] = useState(false)

  // Reset when cards change
  useEffect(() => {
    setIdx(0)
    setRating(null)
    setShowAnswer(false)
    setResults([])
    setDone(false)
  }, [cards])

  const current = cards?.[idx]

  const handleReveal = useCallback(() => {
    if (!showAnswer) setShowAnswer(true)
  }, [showAnswer])

  const handleRate = useCallback(async (val) => {
    if (rating !== null) return
    setRating(val)
    setResults(prev => [...prev, { card: current, rating: val }])

    // Submit rating if callback provided
    if (onRate && current) {
      try {
        await onRate(current, val)
      } catch {}
    }

    // Advance after brief delay
    setTimeout(() => {
      if (idx + 1 < cards.length) {
        setIdx(p => p + 1)
        setRating(null)
        setShowAnswer(false)
      } else {
        setDone(true)
        if (onComplete) onComplete()
      }
    }, 800)
  }, [rating, current, idx, cards.length, onRate, onComplete])

  // Flip on Enter/Space
  const handleKey = useCallback((e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      if (!showAnswer) { handleReveal(); return }
    }
  }, [showAnswer, handleReveal])

  useEffect(() => {
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [handleKey])

  // ── Completion screen ──
  if (done) {
    const correct = results.filter(r => r.rating >= 3).length
    const total = results.length
    const pct = total > 0 ? Math.round((correct / total) * 100) : 0
    return (
      <div className="max-w-lg mx-auto px-4 py-8 text-center">
        <span className="text-4xl block mb-4">{pct >= 80 ? '🎉' : pct >= 50 ? '👍' : '📚'}</span>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Session Complete</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-2">{title || 'Review'} · {total} cards</p>
        <div className="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-2">{correct}/{total}</div>
        <div className="w-48 h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 mx-auto overflow-hidden mb-6">
          <div className="h-full rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex gap-2 justify-center text-xs text-neutral-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500" /> Again: {results.filter(r => r.rating === 1).length}
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> Hard: {results.filter(r => r.rating === 2).length}
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500" /> Good: {results.filter(r => r.rating === 3).length}
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500" /> Easy: {results.filter(r => r.rating === 4).length}
          </span>
        </div>
      </div>
    )
  }

  // ── Empty state ──
  if (!current) {
    return (
      <div className="max-w-lg mx-auto px-4 py-8 text-center">
        <p className="text-sm text-neutral-400">{emptyMessage || 'No cards to review.'}</p>
      </div>
    )
  }

  // ── Card display ──
  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {title || 'Review'}
        </span>
        <span className="text-[10px] font-mono text-neutral-400">{idx + 1}/{cards.length}</span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mb-4">
        <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${(idx / cards.length) * 100}%` }} />
      </div>

      {/* Card type badge */}
      {current.type && (
        <div className="text-center mb-2">
          <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium uppercase tracking-wider
            bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">
            {current.type.replace(/_/g, ' ')}
          </span>
        </div>
      )}

      {/* Card content */}
      <div
        onClick={handleReveal}
        className="p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-indigo-200 dark:border-indigo-800 shadow-sm cursor-pointer hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors min-h-[200px] flex items-center justify-center"
      >
        <CardRenderer card={current} showAnswer={showAnswer} onAnswer={(ans) => { if (onAnswer) onAnswer(current, ans) }} answerState={answerState} hebrewOnly={hebrewOnly} />
      </div>

      {/* Hint to flip */}
      {!showAnswer && (
        <p className="text-center text-[10px] text-neutral-400 mt-2">Click card or press Space/Enter to reveal answer</p>
      )}

      {/* Rating buttons — shown after answer revealed */}
      {showAnswer && rating === null && (
        <div className="mt-4">
          <p className="text-center text-[10px] text-neutral-400 mb-2">How well did you recall this?</p>
          <div className="flex gap-2 justify-center">
            {[
              { val: 1, label: 'Again', desc: 'Forgot', color: 'bg-red-500 hover:bg-red-600' },
              { val: 2, label: 'Hard', desc: 'Struggled', color: 'bg-amber-500 hover:bg-amber-600' },
              { val: 3, label: 'Good', desc: 'Recalled', color: 'bg-green-500 hover:bg-green-600' },
              { val: 4, label: 'Easy', desc: 'Instant', color: 'bg-blue-500 hover:bg-blue-600' },
            ].map(b => (
              <button key={b.val} onClick={() => handleRate(b.val)}
                className={`flex flex-col items-center px-4 py-2 rounded-lg text-white text-sm font-medium cursor-pointer transition-colors ${b.color} min-w-[70px]`}>
                <span>{b.label}</span>
                <span className="text-[9px] opacity-80">{b.desc}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Rating feedback */}
      {rating !== null && (
        <p className="text-center text-sm text-green-600 font-medium mt-4">✓ Recorded</p>
      )}
    </div>
  )
}
