import React, { useState, useEffect, useCallback, useRef } from 'react'
import HebrewKeyboard from './HebrewKeyboard'
import {
  ANSWER_MODES,
  answerModeForQuestion,
} from '../lib/quiz-grading'
import { currentSessionToken, hebrewSessionUser } from '../api'

/**
 * HebrewQuiz — cumulative interleaved quiz from recently studied material.
 *
 * Fetches mixed-category questions from /api/v1/hebrew/quiz (or a per-lesson
 * quiz from /api/v1/hebrew/lesson/{nodeId}/quiz when nodeId is provided),
 * presents them one at a time with timers, shows results at the end.
 */
const TYPE_COLORS = {
  multiple_choice: 'border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20',
  cloze: 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20',
  transliteration: 'border-cyan-200 dark:border-cyan-800 bg-cyan-50 dark:bg-cyan-900/20',
  true_false: 'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20',
  recall: 'border-teal-200 dark:border-teal-800 bg-teal-50 dark:bg-teal-900/20',
  typing: 'border-rose-200 dark:border-rose-800 bg-rose-50 dark:bg-rose-900/20',
  contrast: 'border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/20',
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

/**
 * Read only a per-answer boolean from the progress response. The progress
 * endpoint also returns cumulative counters, so numeric `correct` values are
 * deliberately ignored here.
 */
export function getAuthoritativeCorrect(payload) {
  const envelope = payload && typeof payload === 'object' ? payload : {}
  const data = envelope.data && typeof envelope.data === 'object' ? envelope.data : envelope
  const candidates = [
    data.is_correct,
    data.isCorrect,
    data.correct,
    data.grading,
    data.grading?.is_correct,
    data.grading?.isCorrect,
    data.grading?.correct,
    data.grading?.result?.is_correct,
    data.grading?.result?.isCorrect,
    data.grading?.result?.correct,
    data.result?.is_correct,
    data.result?.isCorrect,
    data.result?.correct,
    envelope.is_correct,
    envelope.isCorrect,
    envelope.grading?.is_correct,
    envelope.grading?.isCorrect,
    envelope.grading?.correct,
  ]
  return candidates.find(value => typeof value === 'boolean') ?? null
}

/** Submit an issued answer and return a server result when one is provided. */
export async function submitHebrewProgress(progress) {
  try {
    const response = await fetch('/api/v1/hebrew/progress', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(currentSessionToken() ? { Authorization: `Bearer ${currentSessionToken()}` } : {}),
      },
      body: JSON.stringify(progress),
    })
    if (response?.ok === false) return null
    return getAuthoritativeCorrect(await response.json())
  } catch {
    return null
  }
}

export default function HebrewQuiz({ count = 8, onComplete, onBack, onOpenLesson, nodeId }) {
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
  const [submissionError, setSubmissionError] = useState('')
  const timerRef = useRef(null)
  const startRef = useRef(null)
  const answersRef = useRef(answers)
  const submittedRef = useRef(submitted)

  useEffect(() => { answersRef.current = answers }, [answers])
  useEffect(() => { submittedRef.current = submitted }, [submitted])

  const quizUrl = nodeId
    ? `/api/v1/hebrew/lesson/${encodeURIComponent(nodeId)}/quiz?count=${count}`
    : `/api/v1/hebrew/quiz?count=${count}`

  useEffect(() => {
    let cancelled = false
    const loadQuiz = async () => {
      await hebrewSessionUser()
      if (cancelled) return
      try {
        const token = currentSessionToken()
        const response = await fetch(quizUrl, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        })
        const d = await response.json()
        if (cancelled) return
        if (d.ok && d.data?.questions?.length > 0) {
          setQuestions(d.data.questions)
          startRef.current = Date.now()
        } else {
          setError('No questions available. Study some lessons first!')
        }
      } catch {
        if (!cancelled) setError('Failed to load quiz')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadQuiz()
    return () => { cancelled = true }
  }, [quizUrl])

  const current = questions[idx]

  const submitAnswer = useCallback(async (timedOut = false) => {
    if (submittedRef.current[idx] !== undefined) return
    const questionIndex = idx
    const question = current
    const ans = answersRef.current[questionIndex]
    const answerMode = answerModeForQuestion(question || {})
    setSubmissionError('')
    submittedRef.current = { ...submittedRef.current, [questionIndex]: null }
    // Report progress — /hebrew/progress feeds the FSRS review state, so every
    // quiz answer is retrieval practice that schedules the next review.
    let authoritativeCorrect = null
    if (question?.node_id && question.question_id !== undefined && question.question_id !== null) {
      const token = currentSessionToken()
      const progress = {
        node_id: question.node_id,
        user_id: 'default',
        session_token: token,
        question_id: question.question_id,
        answer: ans ?? '',
        answer_mode: answerMode,
      }
      authoritativeCorrect = await submitHebrewProgress(progress)
    }
    if (authoritativeCorrect === null) {
      const pending = { ...submittedRef.current }
      delete pending[questionIndex]
      submittedRef.current = pending
      setSubmitted(previous => {
        const next = { ...previous }
        delete next[questionIndex]
        return next
      })
      setSubmissionError('Could not verify this answer. Please try again.')
      return
    }
    const correct = typeof authoritativeCorrect === 'boolean' ? authoritativeCorrect : null
    submittedRef.current = { ...submittedRef.current, [questionIndex]: correct }
    setSubmitted(prev => ({ ...prev, [questionIndex]: correct }))
    setResults(prev => ({ correct: prev.correct + (correct ? 1 : 0), total: prev.total + 1 }))
    if (correct !== true) {
      setMissedItems(prev => [...prev, { ...question, quizIndex: questionIndex, yourAnswer: ans || '(timed out)' }])
    }
  }, [idx, current])

  // Per-question timer. A timeout is an assessed retrieval attempt, not just a UI state.
  useEffect(() => {
    if (!current || done || submitted[idx] !== undefined) return
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
        submitAnswer(true)
      }
    }, 200)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [idx, done, current, submitted, submitAnswer])

  const nextQuestion = () => {
    if (submitted[idx] === null) return
    if (idx < questions.length - 1) {
      setIdx(prev => prev + 1)
      setTimeLeft(null)
    } else {
      setDone(true)
      onComplete?.(results)
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
                       Server grading marked this answer incorrect.
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
              {nodeId ? '← Back to Lesson' : '← Back to Lessons'}
            </button>
             <button onClick={() => { setDone(false); setIdx(0); setAnswers({}); answersRef.current = {}; setSubmitted({}); submittedRef.current = {}; setResults({ correct: 0, total: 0 }); setMissedItems([]); setSubmissionError(''); setLoading(true); setError(null); fetch(quizUrl, { headers: currentSessionToken() ? { Authorization: `Bearer ${currentSessionToken()}` } : {} }).then(r => r.json()).then(d => { if (d.ok) setQuestions(d.data.questions); setLoading(false) }).catch(() => setError('Failed')) }}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
              🔄 New Quiz
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!current) return null

  const currentAnswerMode = answerModeForQuestion(current)
  const currentIsTextInput = currentAnswerMode === ANSWER_MODES.FREE_TEXT
  const answered = typeof answers[idx] === 'string'
    ? answers[idx].trim().length > 0
    : answers[idx] !== undefined && answers[idx] !== null
  const showResult = submitted[idx] !== undefined
  const displayedAnswer = currentAnswerMode === ANSWER_MODES.CHOICE_INDEX
    ? current.options?.[answers[idx]]
    : answers[idx]

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
            {currentAnswerMode === ANSWER_MODES.CHOICE_INDEX && current.options?.length > 0 && (
              <div className={current.type === 'true_false' ? 'flex gap-3' : 'space-y-2'}>
                {current.options.map((opt, i) => (
                  <button key={i} onClick={() => setAnswer(i)}
                    className={`${current.type === 'true_false' ? 'flex-1' : 'w-full text-left'} px-4 py-3 rounded-lg text-sm border transition-all cursor-pointer ${
                      answers[idx] === i
                        ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                        : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                    }`}>
                    {opt}
                  </button>
                ))}
              </div>
            )}
            {currentIsTextInput && (
              <div>
                <input type="text" value={answers[idx] || ''}
                  onChange={e => setAnswer(e.target.value)}
                  onFocus={() => setShowKeyboard(true)}
                  placeholder={current.type === 'typing' || current.type === 'letter_name'
                    ? 'Type Hebrew characters...'
                    : 'Type your answer...'}
                  className="w-full px-4 py-3 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 text-sm outline-none focus:border-indigo-400 dark:focus:border-indigo-500 font-hebrew-biblical"
                  dir="auto"
                  autoFocus
                />
              </div>
            )}
          </>
        ) : (
          /* Result display */
           <div className={`p-4 rounded-lg ${submitted[idx] === true
             ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
             : submitted[idx] === false
               ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
               : 'bg-neutral-50 dark:bg-neutral-900/20 border border-neutral-200 dark:border-neutral-800'}`}>
             <p className="text-sm font-medium mb-1">
               {submitted[idx] === true ? '✓ Correct!' : submitted[idx] === false ? '✗ Incorrect' : 'Unable to verify'}
             </p>
             {submitted[idx] === false && displayedAnswer && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
                Your answer: <span className="text-red-500">{displayedAnswer}</span>
              </p>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      {submissionError && <p className="text-center text-sm text-red-600 dark:text-red-400 mt-4">{submissionError}</p>}
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
          <button onClick={nextQuestion} disabled={submitted[idx] === null}
            className="flex-1 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-wait text-white text-sm font-medium cursor-pointer transition-colors">
            {submitted[idx] === null ? 'Checking…' : idx < questions.length - 1 ? 'Next Question →' : 'See Results'}
          </button>
        )}
      </div>

      {/* Hebrew keyboard */}
      {showKeyboard && currentIsTextInput && (
        <div className="mt-4">
          <HebrewKeyboard onCharClick={(c) => setAnswer((answers[idx] || '') + c)} />
          <button onClick={() => setShowKeyboard(false)}
            className="mt-2 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">
            Hide keyboard
          </button>
        </div>
      )}
    </div>
  )
}
