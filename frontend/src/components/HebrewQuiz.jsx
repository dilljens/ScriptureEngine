import React, { useState, useEffect, useCallback, useRef } from 'react'
import HebrewKeyboard from './HebrewKeyboard'

/**
 * HebrewQuiz — cumulative interleaved quiz from recently studied material.
 *
 * Fetches mixed-category questions from /api/v1/hebrew/quiz,
 * presents them one at a time with timers, shows results at the end.
 */
const TYPE_COLORS = {
  multiple_choice: 'border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20',
  cloze: 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20',
  transliteration: 'border-cyan-200 dark:border-cyan-800 bg-cyan-50 dark:bg-cyan-900/20',
  true_false: 'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20',
}

const CATEGORY_BADGES = {
  word: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300', label: 'Vocab' },
  grammar: { bg: 'bg-rose-100 dark:bg-rose-900/30', text: 'text-rose-700 dark:text-rose-300', label: 'Grammar' },
  verb: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300', label: 'Verb' },
  phrase: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', text: 'text-yellow-700 dark:text-yellow-300', label: 'Phrase' },
}

function getTimeLimit(q) {
  if (!q) return 15
  const wordCount = (q.question || '').split(/\s+/).filter(Boolean).length
  let base = { multiple_choice: 8, true_false: 6, transliteration: 15, cloze: 20 }[q.type] || 12
  const wordBonus = Math.max(0, Math.floor((wordCount - 10) / 5)) * 2
  return Math.round(base + wordBonus)
}

export default function HebrewQuiz({ count = 8, onComplete, onBack, onOpenLesson }) {
  const [questions, setQuestions] = useState([])
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState({})
  const [results, setResults] = useState({ correct: 0, total: 0 })
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showKeyboard, setShowKeyboard] = useState(false)
  const [timeLeft, setTimeLeft] = useState(null)
  const [missedItems, setMissedItems] = useState([])
  const timerRef = useRef(null)
  const startRef = useRef(null)

  useEffect(() => {
    fetch(`/api/v1/hebrew/quiz?count=${count}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok && d.data?.questions?.length > 0) {
          setQuestions(d.data.questions)
          startRef.current = Date.now()
        } else {
          setError('No questions available. Study some lessons first!')
        }
      })
      .catch(() => setError('Failed to load quiz'))
      .finally(() => setLoading(false))
  }, [count])

  const current = questions[idx]

  // Per-question timer
  useEffect(() => {
    if (!current || done) return
    const limit = getTimeLimit(current)
    setTimeLeft(limit)
    if (timerRef.current) clearInterval(timerRef.current)
    const start = Date.now()
    timerRef.current = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000
      const remaining = Math.max(0, limit - elapsed)
      setTimeLeft(remaining)
      if (remaining <= 0) {
        clearInterval(timerRef.current)
        setSubmitted(prev => ({ ...prev, [idx]: false }))
      }
    }, 200)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idx, done, current])

  const submitAnswer = useCallback(() => {
    if (submitted[idx] !== undefined) return
    const ans = answers[idx]
    const correct = ans !== undefined && ans !== null && ans !== ''
      && (ans === current.correct || ans.toLowerCase().trim() === current.correct.toLowerCase().trim())
    setSubmitted(prev => ({ ...prev, [idx]: correct }))
    setResults(prev => ({ correct: prev.correct + (correct ? 1 : 0), total: prev.total + 1 }))
    if (!correct) {
      setMissedItems(prev => [...prev, { ...current, yourAnswer: ans || '(timed out)' }])
    }
    // Report progress
    try {
      fetch('/api/v1/hebrew/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: current.node_id, correct, user_id: 'default' }),
      })
    } catch {}
  }, [idx, answers, submitted, current])

  const nextQuestion = () => {
    if (idx < questions.length - 1) {
      setIdx(prev => prev + 1)
      setTimeLeft(null)
    } else {
      setDone(true)
      onComplete?.({ correct: results.correct + (submitted[idx] ? 0 : 1), total: results.total + 1 })
    }
  }

  const setAnswer = (value) => {
    setAnswers(prev => ({ ...prev, [idx]: value }))
  }

  if (loading) return (
    <div className="max-w-2xl mx-auto px-6 py-12 text-center">
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3 mx-auto" />
        <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
      </div>
    </div>
  )

  if (error) return (
    <div className="max-w-2xl mx-auto px-6 py-12 text-center">
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">{error}</p>
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
    </div>
  )

  if (done) {
    const pct = Math.round((results.correct / Math.max(results.total, 1)) * 100)
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="p-8 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-center">
          <div className="text-4xl mb-4">{pct >= 80 ? '🎉' : pct >= 50 ? '💪' : '📚'}</div>
          <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Quiz Complete!</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
            {results.correct} / {results.total} correct ({pct}%)
          </p>
          <div className="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mb-6 max-w-xs mx-auto">
            <div className={`h-full rounded-full transition-all ${pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
              style={{ width: `${pct}%` }} />
          </div>

          {missedItems.length > 0 && (
            <div className="mb-6 text-left">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-3">
                Review Missed Items ({missedItems.length})
              </h3>
              <div className="space-y-2">
                {missedItems.map((m, i) => (
                  <div key={i} className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-neutral-700 dark:text-neutral-300">{m.question}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-500">
                          {CATEGORY_BADGES[m.category]?.label || m.category}
                        </span>
                        {m.node_id && (
                          <button onClick={() => onOpenLesson?.(m.node_id)}
                            className="text-[10px] text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
                            Study
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-1">
                      Correct answer: <span className="text-green-600 dark:text-green-400 font-medium">{m.correct}</span>
                      {m.yourAnswer && <span> · Your answer: <span className="text-red-500">{m.yourAnswer}</span></span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 justify-center">
            <button onClick={onBack}
              className="px-6 py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-sm font-medium cursor-pointer hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors">
              ← Back to Lessons
            </button>
            <button onClick={() => { setDone(false); setIdx(0); setAnswers({}); setSubmitted({}); setResults({ correct: 0, total: 0 }); setMissedItems([]); setLoading(true); setError(null); fetch(`/api/v1/hebrew/quiz?count=${count}`).then(r => r.json()).then(d => { if (d.ok) setQuestions(d.data.questions); setLoading(false) }).catch(() => setError('Failed')) }}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
              🔄 New Quiz
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!current) return null

  const answered = answers[idx] !== undefined && answers[idx] !== null && answers[idx] !== ''
  const showResult = submitted[idx] !== undefined

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-neutral-400">{idx + 1}/{questions.length}</span>
          {CATEGORY_BADGES[current.category] && (
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${CATEGORY_BADGES[current.category].bg} ${CATEGORY_BADGES[current.category].text}`}>
              {CATEGORY_BADGES[current.category].label}
            </span>
          )}
          <span className={`text-[10px] font-mono ${timeLeft <= 3 ? 'text-red-500' : 'text-neutral-400'}`}>
            ⏱ {Math.ceil(timeLeft || 0)}s
          </span>
          <span className="text-[10px] text-neutral-400">{results.correct}/{results.total}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mb-6">
        <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${((idx + 1) / questions.length) * 100}%` }} />
      </div>

      {/* Question card */}
      <div className={`p-6 rounded-xl border-2 ${TYPE_COLORS[current.type] || 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800'}`}>
        {/* Type badge */}
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-white dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
          {current.type.replace(/_/g, ' ')}
        </span>

        {/* Question text */}
        <p className="text-sm text-neutral-800 dark:text-neutral-200 mt-3 mb-4 leading-relaxed">{current.question}</p>

        {/* Answer area */}
        {!showResult ? (
          <>
            {current.type === 'multiple_choice' && current.options?.length > 0 && (
              <div className="space-y-2">
                {current.options.map((opt, i) => (
                  <button key={i} onClick={() => setAnswer(opt)}
                    className={`w-full text-left px-4 py-3 rounded-lg text-sm border transition-all cursor-pointer ${
                      answers[idx] === opt
                        ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                        : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                    }`}>
                    {opt}
                  </button>
                ))}
              </div>
            )}
            {current.type === 'true_false' && current.options?.length > 0 && (
              <div className="flex gap-3">
                {current.options.map((opt, i) => (
                  <button key={i} onClick={() => setAnswer(opt)}
                    className={`flex-1 px-4 py-3 rounded-lg text-sm font-medium border transition-all cursor-pointer ${
                      answers[idx] === opt
                        ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700'
                        : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300'
                    }`}>
                    {opt}
                  </button>
                ))}
              </div>
            )}
            {['transliteration', 'cloze'].includes(current.type) && (
              <div>
                <input type="text" value={answers[idx] || ''}
                  onChange={e => setAnswer(e.target.value)}
                  onFocus={() => setShowKeyboard(true)}
                  placeholder="Type your answer..."
                  className="w-full px-4 py-3 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 text-sm outline-none focus:border-indigo-400 dark:focus:border-indigo-500 font-hebrew-biblical"
                  dir="auto"
                  autoFocus
                />
              </div>
            )}
          </>
        ) : (
          /* Result display */
          <div className={`p-4 rounded-lg ${showResult ? (submitted[idx] ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800') : ''}`}>
            <p className="text-sm font-medium mb-1">
              {submitted[idx] ? '✓ Correct!' : '✗ Incorrect'}
            </p>
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              Correct answer: <span className="text-green-600 dark:text-green-400 font-medium">{current.correct}</span>
            </p>
            {!submitted[idx] && answers[idx] && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                Your answer: <span className="text-red-500">{answers[idx]}</span>
              </p>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 mt-4">
        {!showResult ? (
          <button onClick={submitAnswer} disabled={!answered}
            className={`flex-1 py-3 rounded-xl text-sm font-medium cursor-pointer transition-colors ${
              answered
                ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 cursor-not-allowed'
            }`}>
            Submit Answer
          </button>
        ) : (
          <button onClick={nextQuestion}
            className="flex-1 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
            {idx < questions.length - 1 ? 'Next Question →' : 'See Results'}
          </button>
        )}
      </div>

      {/* Hebrew keyboard */}
      {showKeyboard && ['transliteration', 'cloze'].includes(current.type) && (
        <div className="mt-4">
          <HebrewKeyboard onChar={(c) => setAnswer((answers[idx] || '') + c)} />
          <button onClick={() => setShowKeyboard(false)}
            className="mt-2 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">
            Hide keyboard
          </button>
        </div>
      )}
    </div>
  )
}
