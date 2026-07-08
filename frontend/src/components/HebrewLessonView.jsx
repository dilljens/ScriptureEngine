import React, { useState, useEffect, useCallback } from 'react'
import HebrewKeyboard from './HebrewKeyboard'

/**
 * HebrewLessonView — lesson content with interactive quiz.
 * Supports:
 * - Lesson explanation display
 * - Multiple choice questions (click to answer)  
 * - Typing practice with on-screen Hebrew keyboard
 * - Transliteration input (type "bereshit" instead of typing Hebrew)
 * - Mastery tracking
 */

const QUESTION_COLORS = {
  multiple_choice: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800',
  true_false: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
  transliteration: 'bg-cyan-50 dark:bg-cyan-900/20 border-cyan-200 dark:border-cyan-800',
  recall: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
  typing: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
}

export default function HebrewLessonView({ nodeId, onBack }) {
  const [node, setNode] = useState(null)
  const [practice, setPractice] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [typedValue, setTypedValue] = useState('')
  const [showKeyboard, setShowKeyboard] = useState(false)
  const [results, setResults] = useState({ correct: 0, total: 0 })
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`/api/v1/hebrew/lesson/${nodeId}`).then(r => r.json()),
      fetch(`/api/v1/hebrew/practice/${nodeId}`).then(r => r.json()),
    ])
      .then(([nodeData, practiceData]) => {
        if (!nodeData.ok) throw new Error(nodeData.detail)
        setNode(nodeData.data)
        setPractice(practiceData.data?.items || [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [nodeId])

  const submitAnswer = useCallback(async (correct) => {
    try {
      await fetch('/api/v1/hebrew/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, correct, user_id: 'default' }),
      })
    } catch {}
  }, [nodeId])

  const handleNext = () => {
    if (currentQuestion < practice.length - 1) {
      setCurrentQuestion(prev => prev + 1)
      setSelectedAnswer(null)
      setSubmitted(false)
      setTypedValue('')
    } else {
      setCompleted(true)
    }
  }

  const handleSubmitAnswer = async () => {
    const q = practice[currentQuestion]
    if (!q) return

    let correct = false
    if (q.question_type === 'typing') {
      // Check typed answer matches correct (case-insensitive, trimmed)
      correct = typedValue.trim().toLowerCase() === q.correct_answer.trim().toLowerCase()
    } else {
      correct = selectedAnswer === q.correct_answer
    }

    setSubmitted(true)
    setResults(prev => ({ correct: prev.correct + (correct ? 1 : 0), total: prev.total + 1 }))
    await submitAnswer(correct)
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2" />
          <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
          <div className="h-48 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">← Back to curriculum</button>
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">{error}</div>
      </div>
    )
  }

  if (!node) return null

  // Extract lesson content
  const content = typeof node.lesson === 'string' ? node.lesson
    : node.content || node.lesson?.content || ''

  const q = practice[currentQuestion]

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      {/* Back button */}
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">
        ← Back to curriculum
      </button>

      {/* Lesson header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500">Level {node.level}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">
            {node.category}
          </span>
        </div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{node.title}</h2>
        {node.description && <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{node.description}</p>}
      </div>

      {/* Progress bar */}
      {practice.length > 0 && (
        <div className="mb-6">
          <div className="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-400 mb-1">
            <span>Progress: {results.correct}/{results.total} correct</span>
            <span>{Math.round((currentQuestion / practice.length) * 100)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${((submitted ? currentQuestion + 1 : currentQuestion) / practice.length) * 100}%` }} />
          </div>
        </div>
      )}

      {/* Lesson content (shown before questions) */}
      {content && !submitted && currentQuestion === 0 && (
        <div className="mb-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
          {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
        </div>
      )}

      {/* Completed state */}
      {completed ? (
        <div className="p-6 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-center">
          <span className="text-3xl block mb-2">🎉</span>
          <h3 className="text-base font-semibold text-green-800 dark:text-green-200 mb-1">Lesson Complete!</h3>
          <p className="text-sm text-green-600 dark:text-green-400 mb-4">
            {results.correct}/{results.total} correct ({Math.round((results.correct / Math.max(results.total, 1)) * 100)}%)
          </p>
          <div className="flex gap-2 justify-center">
            <button onClick={onBack} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
              Back to curriculum
            </button>
            <button onClick={() => { setCurrentQuestion(0); setSelectedAnswer(null); setSubmitted(false); setCompleted(false); setResults({ correct: 0, total: 0 }) }}
              className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-sm font-medium cursor-pointer transition-colors">
              Retry
            </button>
          </div>
        </div>
      ) : q ? (
        <div className={`p-4 rounded-xl border ${QUESTION_COLORS[q.question_type] || 'bg-neutral-50 dark:bg-neutral-900/50 border-neutral-200 dark:border-neutral-700'}`}>
          {/* Question type badge */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
              {q.question_type?.replace('_', ' ') || 'Question'} {currentQuestion + 1}/{practice.length}
            </span>
            {q.correct_answer && submitted && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">
                Answer: {q.correct_answer}
              </span>
            )}
          </div>

          {/* Question text */}
          <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-4 font-medium">{q.question_text}</p>

          {/* Answer input based on type */}
          {q.question_type === 'typing' || q.question_type === 'transliteration' ? (
            <div>
              {/* Typing input with optional keyboard */}
              <div className="flex items-center gap-2 mb-3">
                <input
                  type="text"
                  value={typedValue}
                  onChange={(e) => setTypedValue(e.target.value)}
                  disabled={submitted}
                  placeholder={q.question_type === 'transliteration' ? 'Type transliteration (e.g., bereshit)' : 'Type your answer'}
                  className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 text-sm font-mono outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 disabled:opacity-60"
                  dir={q.question_type === 'typing' ? 'rtl' : 'ltr'}
                />
                <button onClick={() => setShowKeyboard(!showKeyboard)}
                  className="px-3 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-xs font-medium cursor-pointer transition-colors shrink-0">
                  {showKeyboard ? 'Hide' : 'Keyboard'} ⌨
                </button>
              </div>
              {showKeyboard && (
                <HebrewKeyboard
                  value={typedValue}
                  onCharClick={(c) => setTypedValue(prev => prev + c)}
                  onBackspace={() => setTypedValue(prev => prev.slice(0, -1))}
                  onClear={() => setTypedValue('')}
                  onDone={() => setShowKeyboard(false)}
                />
              )}
            </div>
          ) : (
            /* Multiple choice buttons */
            <div className="space-y-1.5">
              {(q.options_json ? JSON.parse(q.options_json) : []).map((opt, i) => {
                const isCorrect = opt === q.correct_answer || i === parseInt(q.correct_answer)
                const isSelected = selectedAnswer === opt || selectedAnswer === i
                let cls = 'w-full text-left px-3 py-2.5 rounded-lg text-sm border transition-all cursor-pointer '

                if (!submitted) {
                  cls += isSelected
                    ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                } else {
                  cls += isCorrect
                    ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                    : isSelected && !isCorrect
                      ? 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                      : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
                }

                const isHebrew = /[\u0590-\u05FF]/.test(opt)
                return (
                  <button key={i} onClick={() => setSelectedAnswer(opt)} className={cls}>
                    <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + i)}.</span>
                    {isHebrew ? (
                      <span className="text-lg font-serif" dir="rtl" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>{opt}</span>
                    ) : (
                      <span>{opt}</span>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Submit / Next buttons */}
          <div className="flex gap-2 mt-4">
            {!submitted ? (
              <button onClick={handleSubmitAnswer}
                disabled={q.question_type?.includes('typing') ? !typedValue.trim() : selectedAnswer === null}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium cursor-pointer transition-colors">
                Check Answer
              </button>
            ) : (
              <button onClick={handleNext}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
                {currentQuestion < practice.length - 1 ? 'Next Question →' : 'See Results'}
              </button>
            )}
          </div>

          {/* Explanation */}
          {submitted && q.explanation && (
            <div className="mt-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">
              {q.explanation}
            </div>
          )}
        </div>
      ) : (
        <div className="p-6 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-center text-sm text-neutral-500 dark:text-neutral-400">
          No practice questions for this lesson yet.
          <button onClick={onBack} className="block mt-3 mx-auto px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
            Back to curriculum
          </button>
        </div>
      )}

      {/* Keyboard shortcut hint */}
      {!submitted && q?.question_type !== 'typing' && (
        <p className="mt-3 text-[10px] text-neutral-400 dark:text-neutral-500 text-center">
          Click an answer · No Hebrew typing needed
        </p>
      )}
    </div>
  )
}
