import React, { useState, useCallback, useEffect } from 'react'
import CardQueue from './CardQueue'
import { assessmentToCards, interleaveCards } from '../lib/card-factory'

/**
 * AssessmentView — flashcard-style scripture knowledge assessment.
 *
 * Uses CardQueue for retrieval-practice (click-to-reveal + FSRS 4-point rating).
 * Follows The Math Academy Way Ch 20: testing effect / retrieval practice.
 *
 * Adaptive MC: if user has struggled with a question before, show MC options.
 * If they've answered correctly, hide options for pure recall.
 */
const TIER_OPTIONS = [
  { id: '', label: 'All Tiers', icon: '📚' },
  { id: 'text', label: 'Text', icon: '🔬' },
  { id: 'analysis', label: 'Analysis', icon: '🔍' },
  { id: 'consistency', label: 'Consistency', icon: '🤝' },
]

export default function AssessmentView({ user_id = 'default', onBack }) {
  const [mode, setMode] = useState('intro')   // intro | quiz | complete
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tier, setTier] = useState('')
  const [stats, setStats] = useState(null)

  // Fetch quiz questions and convert to flashcards
  // Mixed review: interleave assessment + verse review + Hebrew vocab
  const startMixed = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      // Fetch from 3 sources in parallel
      const [quizRes, verseRes, hebRes] = await Promise.all([
        fetch(`/api/v1/quiz?tier=&count=5&user_id=${user_id}`),
        fetch(`/api/v1/memorize/review?limit=5&user_id=${user_id}`).catch(() => ({ json: () => Promise.resolve({ ok: false }) })),
        fetch(`/api/v1/hebrew/review-queue?limit=5&user_id=${user_id}`).catch(() => ({ json: () => Promise.resolve({ ok: false }) })),
      ])
      const quizData = await quizRes.json()
      const verseData = await verseRes.json()
      const hebData = await hebRes.json()

      const assessmentCards = quizData.ok ? assessmentToCards(quizData.data?.questions || []) : []
      const verseCards = (verseData.ok ? (verseData.data?.results || verseData.data?.cards || []) : []).map(v => ({
        id: `verse-${v.verse_id || v.id}`,
        type: 'verse',
        data: { reference: v.verse_id || v.id, text: v.text_english || v.text || '' },
      }))
      const hebCards = (hebData.ok ? (hebData.data?.cards || hebData.data?.results || []) : []).map(h => ({
        id: `heb-${h.node_id || h.id}`,
        type: 'vocab',
        data: { word: h.hebrew || h.word || '', definition: h.gloss || h.definition || '', transliteration: h.transliteration || '' },
      }))

      const allCards = interleaveCards([assessmentCards, verseCards, hebCards], 2)
      if (allCards.length === 0) throw new Error('No cards available for mixed review')
      setCards(allCards)
      setMode('quiz')
    } catch (e) { setError(e.message) }
    setLoading(false)
  }, [user_id])

  const startQuiz = useCallback(async (t = '') => {
    setLoading(true); setError(null)
    try {
      const r = await fetch(`/api/v1/quiz?tier=${t}&count=10&user_id=${user_id}`)
      const d = await r.json()
      if (!d.ok) throw new Error(d.detail || d.error || 'Failed to load')
      if (!d.data?.questions?.length) throw new Error('No questions available for this tier')
      setCards(assessmentToCards(d.data.questions))
      setMode('quiz')
    } catch (e) { setError(e.message); setLoading(false) }
    setLoading(false)
  }, [user_id])

  // Handle FSRS rating — route to correct endpoint based on card type
  const handleRate = useCallback(async (card, rating) => {
    try {
      if (card.type === 'assessment_question') {
        const qid = parseInt(card.id?.replace('assessment-', '') || '0')
        if (qid) await fetch('/api/v1/quiz/answer', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id, question_id: qid, rating }),
        })
      } else if (card.type === 'verse') {
        // POST to memorize review endpoint
        await fetch('/api/v1/memorize/review/0', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id, verse_id: card.data?.reference, rating }),
        }).catch(() => {})
      }
    } catch {}
  }, [user_id])

  const handleComplete = useCallback((results) => {
    const correct = results.filter(r => r.rating >= 3).length
    setStats({ correct, total: results.length })
    setMode('complete')
  }, [])

  // Intro screen
  if (mode === 'intro') {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📝 Scripture Knowledge Assessment</h2>
          {onBack && <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>}
        </div>

        <div className="max-w-lg mx-auto space-y-6">
          <div className="p-5 rounded-xl bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 border border-indigo-200 dark:border-indigo-700">
            <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
              Test your scripture knowledge with adaptive flashcards.
              Each card shows a passage and question — <strong>recall the answer</strong> before flipping.
              Rate your recall (Again/Hard/Good/Easy) to schedule reviews at optimal intervals.
            </p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-2">
              Based on the <strong>testing effect</strong> — retrieval practice is the most effective way to build long-term memory.
            </p>
          </div>

          {/* Tier selector */}
          <div>
            <p className="text-xs font-medium text-neutral-600 dark:text-neutral-400 mb-2">Filter by tier:</p>
            <div className="flex flex-wrap gap-2">
              {TIER_OPTIONS.map(t => (
                <button key={t.id} onClick={() => setTier(t.id)}
                  className={`px-4 py-2 rounded-lg text-xs font-medium cursor-pointer transition-all border ${
                    tier === t.id
                      ? 'bg-indigo-600 text-white border-indigo-600'
                      : 'bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700 hover:border-indigo-300'
                  }`}>
                  {t.icon} {t.label}
                </button>
              ))}
            </div>
          </div>

          {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

          <div className="flex gap-3">
            <button onClick={() => startQuiz(tier)} disabled={loading}
              className="flex-1 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 text-white text-sm font-semibold cursor-pointer disabled:cursor-not-allowed transition-colors">
              {loading ? 'Loading...' : '🎯 Start Assessment'}
            </button>
            <button onClick={startMixed} disabled={loading}
              className="flex-1 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-sm font-semibold cursor-pointer disabled:cursor-not-allowed transition-colors">
              {loading ? 'Loading...' : '🔀 Mixed Review'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Quiz mode — CardQueue with assessment_question cards
  if (mode === 'quiz') {
    if (loading || cards.length === 0) {
      return (
        <div className="p-8 text-center">
          <p className="text-sm text-neutral-400 animate-pulse">Loading questions...</p>
        </div>
      )
    }
    return (
      <CardQueue
        cards={cards}
        onRate={handleRate}
        onComplete={handleComplete}
        title="Scripture Assessment"
        emptyMessage="No assessment questions available."
        onAnswer={(card, answer) => {
          // When user selects an MC option (assessment_question card calls onAnswer)
          // The rating will happen after flipping and rating
        }}
      />
    )
  }

  // Complete screen
  if (mode === 'complete') {
    return (
      <div className="p-8 max-w-lg mx-auto text-center">
        <div className="text-5xl mb-4">🎉</div>
        <h2 className="text-xl font-bold text-neutral-800 dark:text-neutral-200 mb-2">Session Complete!</h2>
        {stats && (
          <div className="mb-6">
            <p className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">
              {stats.correct}/{stats.total}
            </p>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              {Math.round((stats.correct / Math.max(stats.total, 1)) * 100)}% correct
            </p>
          </div>
        )}
        <div className="flex gap-3 justify-center">
          <button onClick={() => startQuiz(tier)}
            className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
            🔄 Try Again
          </button>
          <button onClick={() => setMode('intro')}
            className="px-6 py-2.5 rounded-xl bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 text-sm font-medium cursor-pointer transition-colors">
            ← Back to Intro
          </button>
        </div>
      </div>
    )
  }

  return null
}
