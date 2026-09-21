import React, { useState, useCallback, useEffect, useRef } from 'react'
import CardRenderer from './CardRenderer'
import { previewCapNote } from '../lib/previewMask'
import { currentSessionToken } from '../api'

// Objectively-graded card types: the server decides correctness, so the learner
// must never be asked to self-assess recall.
const GRADED_CARD_TYPES = new Set(['drill', 'learn_question', 'assessment_question'])
const isGradedCard = (card) => !!card && GRADED_CARD_TYPES.has(card.type)
const gradeKnown = (card, answerState) => {
  if (!card) return false
  const st = answerState?.[card.id]
  return !!st && typeof (st.correct ?? st.result?.correct) === 'boolean'
}
const gradeValue = (card, answerState) => {
  const st = answerState?.[card.id]
  const correct = st ? (st.correct ?? st.result?.correct) : undefined
  return correct === true ? 3 : 1
}

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
  const [rateError, setRateError] = useState(false)
  // Verse preview help (first-letter hints / full text), reset per card.
  // Initialized from the backend's automated suggestion when present.
  const [preview, setPreview] = useState({ mode: 'none', level: 100 })
  // Anki-style interval preview: next-review wait behind each rating,
  // computed with the exact scheduling math (incl. preview weighting).
  const [intervals, setIntervals] = useState(null) // {1:{label},…} for current card
  const intervalsCard = useRef(null)

  // Reset only when the deck identity actually changes (not on parent re-render
  // with a new array reference). Prevents wiping typed answers mid-card.
  const cardsKey = (cards || []).map(c => c.id ?? c.queue_id ?? '').join('|') + `:${(cards || []).length}`
  const prevCardsKey = React.useRef(cardsKey)
  useEffect(() => {
    if (prevCardsKey.current === cardsKey) return
    prevCardsKey.current = cardsKey
    setIdx(0)
    setRating(null)
    setShowAnswer(false)
    setResults([])
    setDone(false)
    setRateError(false)
  }, [cardsKey])

  const current = cards?.[idx]

  // Per-card preview: pick up the automated level suggestion.
  useEffect(() => {
    setPreview({
      mode: 'none',
      level: current?.data?.suggested_preview ?? 100,
    })
  }, [idx, cards])

  // Interval preview for verse cards with a queue row: refetch when the
  // card or the preview help changes (intervals are help-aware).
  useEffect(() => {
    const qid = current?.type === 'verse' ? current?.queue_id : null
    if (!qid) { setIntervals(null); intervalsCard.current = null; return }
    intervalsCard.current = qid
    const token = currentSessionToken()
    const params = new URLSearchParams({
      preview_mode: preview.mode || 'none',
      preview_level: String(preview.level ?? 0),
    })
    fetch(`/api/v1/memorize/review/${qid}/intervals?${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.json())
      .then(d => {
        if (intervalsCard.current !== qid) return
        setIntervals(d.ok ? d.data?.intervals || null : null)
      })
      .catch(() => { if (intervalsCard.current === qid) setIntervals(null) })
  }, [current?.type, current?.queue_id, idx, preview.mode, preview.level])

  const handleReveal = useCallback(() => {
    if (current?.type === 'drill' && !answerState?.[current.id]?.submitted) return
    if (!showAnswer) setShowAnswer(true)
  }, [current, answerState, showAnswer])

  const handleRate = useCallback(async (val) => {
    if (rating !== null) return
    setRateError(false)
    setRating(val)

    // Attach the preview help used so the backend can weight confidence.
    if (current?.type === 'verse' && current?.data) {
      current.data.preview_mode = preview.mode
      current.data.preview_level = preview.level
    }

    // Submit rating if callback provided
    let authoritativeCorrect
    let authoritativeAttempted = false
    if (onRate && current) {
      authoritativeAttempted = true
      try {
        authoritativeCorrect = await onRate(current, val)
      } catch {}
    }
    if (authoritativeAttempted && authoritativeCorrect === null) {
      setRating(null)
      setRateError(true)
      return
    }
    const result = {
      card: current,
      rating: val,
      authoritative: authoritativeAttempted && authoritativeCorrect !== undefined,
      correct: typeof authoritativeCorrect === 'boolean'
        ? authoritativeCorrect
        : authoritativeAttempted && authoritativeCorrect !== undefined
          ? null
          : answerState?.[current?.id]?.correct,
    }
    const nextResults = [...results, result]
    setResults(nextResults)

    // Advance after brief delay
    setTimeout(() => {
      if (idx + 1 < cards.length) {
        setIdx(p => p + 1)
        setRating(null)
        setShowAnswer(false)
      } else {
        setDone(true)
        if (onComplete) onComplete(nextResults)
      }
    }, 800)
  }, [rating, current, idx, cards.length, onRate, onComplete, answerState, results, preview])

  // Flip on Enter/Space, rate with 1-4 after reveal (Anki-style)
  const handleKey = useCallback((e) => {
    if (e.target?.tagName === 'INPUT' || e.target?.tagName === 'TEXTAREA') return
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      if (!showAnswer && current?.type !== 'drill') { handleReveal(); return }
    }
    if (showAnswer && rating === null && ['1', '2', '3', '4'].includes(e.key)) {
      handleRate(parseInt(e.key))
    }
  }, [showAnswer, handleReveal, current, rating, handleRate])

  useEffect(() => {
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [handleKey])

  // ── Completion screen ──
  if (done) {
    const correct = results.filter(r => r.authoritative ? r.correct === true : (r.correct ?? r.rating >= 3)).length
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
        className={`p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-indigo-200 dark:border-indigo-800 shadow-sm transition-colors min-h-[200px] flex items-center justify-center ${current.type === 'drill' ? '' : 'cursor-pointer hover:border-indigo-300 dark:hover:border-indigo-600'}`}
      >
        <CardRenderer card={current} showAnswer={showAnswer} onAnswer={(ans) => {
          if (onAnswer) onAnswer(current, ans)
          if (current.type === 'drill') setShowAnswer(true)
        }} answerState={answerState} hebrewOnly={hebrewOnly} preview={preview} onPreviewChange={setPreview} />
      </div>

      {/* Hint to flip */}
      {!showAnswer && current.type !== 'drill' && (
        <p className="text-center text-[10px] text-neutral-400 mt-2">Click card or press Space/Enter to reveal answer</p>
      )}

      {/* Rating buttons — shown after answer revealed.
          Objectively-graded cards (quiz/drill) never ask you to self-assess
          recall: the server already knows. Asking "how well did you recall?"
          while the grade still read "Pending" was backwards — you were rating
          yourself before being told whether you were right. Those cards get a
          single Continue, and the rating is derived from the grade. */}
      {showAnswer && rating === null && isGradedCard(current) && (
        <div className="mt-4">
          {gradeKnown(current, answerState) ? (
            <button onClick={() => handleRate(gradeValue(current, answerState))}
              className="w-full min-h-[48px] rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer">
              Continue →
            </button>
          ) : (
            <p className="text-center text-xs text-neutral-400">Grading…</p>
          )}
        </div>
      )}

      {showAnswer && rating === null && !isGradedCard(current) && (
        <div className="mt-4">
          <p className="text-center text-[10px] text-neutral-400 mb-2">How well did you recall this?</p>
          {current?.type === 'verse' && previewCapNote(preview.mode, preview.level) && (
            <p className="text-center text-[10px] text-amber-600 dark:text-amber-400 mb-2">
              ⚠️ {previewCapNote(preview.mode, preview.level)}
            </p>
          )}
          <div className="flex gap-2 justify-center">
            {[
              { val: 1, label: 'Again', desc: 'Forgot', color: 'bg-red-500 hover:bg-red-600' },
              { val: 2, label: 'Hard', desc: 'Struggled', color: 'bg-amber-500 hover:bg-amber-600' },
              { val: 3, label: 'Good', desc: 'Recalled', color: 'bg-green-500 hover:bg-green-600' },
              { val: 4, label: 'Easy', desc: 'Instant', color: 'bg-blue-500 hover:bg-blue-600' },
            ].map(b => (
              <button key={b.val} onClick={() => handleRate(b.val)}
                className={`pressable flex flex-col items-center px-4 py-2 rounded-lg text-white text-sm font-medium cursor-pointer transition-colors ${b.color} min-w-[70px]`}>
                <span>{b.label}</span>
                {intervals?.[b.val]?.label && (
                  <span className="text-[11px] font-semibold opacity-95 leading-tight">{intervals[b.val].label}</span>
                )}
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
      {rateError && (
        <p className="text-center text-sm text-red-600 dark:text-red-400 font-medium mt-4">
          Could not record this answer. Try the rating again.
        </p>
      )}
    </div>
  )
}
