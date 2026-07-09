import React, { useState, useCallback, useRef, useEffect } from 'react'

/**
 * AssessmentView — dedicated knowledge assessment UI (no LLM needed).
 *
 * Works directly with API endpoints, not through chat.
 * Shows questions with multiple choice, tracks score, shows progress.
 */

const LAYER_LABELS = {
  pshat: "P'shat (Literal)",
  remez: "Remez (Hint)",
  drash: "Drash (Comparative)",
  sod: "Sod (Hidden)",
}

export default function AssessmentView({ user_id = 'default', onBack }) {
  const [phase, setPhase] = useState('intro')  // intro | active | complete
  const [layers, setLayers] = useState([])
  const [question, setQuestion] = useState(null)
  const [selected, setSelected] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState({ correct: 0, total: 0 })
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionInfo, setSessionInfo] = useState(null)
  const targetLayerRef = useRef('')

  const startAssessment = useCallback(async (targetLayer = '') => {
    setLoading(true)
    setError(null)
    setPhase('active')
    targetLayerRef.current = targetLayer
    try {
      const r = await fetch('/api/v1/assessment/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, target_layer: targetLayer, max_items: 10 }),
      })
      const d = await r.json()
      if (!d.ok) throw new Error(d.detail || 'Failed to start')
      const data = d.data
      setSessionInfo(data)
      if (data.question) {
        setQuestion(data.question)
      } else {
        setPhase('complete')
      }
    } catch (e) {
      setError(e.message)
      setPhase('intro')
    }
    setLoading(false)
  }, [user_id])

  const submitAnswer = useCallback(async () => {
    if (selected === null || !question) return
    setSubmitted(true)
    const isCorrect = selected === question.correct_answer || 
      (typeof question.correct_answer === 'number' && selected === question.correct_answer)
    
    try {
      const r = await fetch('/api/v1/assessment/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, correct: isCorrect }),
      })
      const d = await r.json()
      if (d.ok) {
        setResults(prev => ({ correct: prev.correct + (isCorrect ? 1 : 0), total: prev.total + 1 }))
        setHistory(prev => [...prev, { question: question.question, correct: isCorrect, yourAnswer: selected }])
        
        if (d.data?.question) {
          // More questions available
          setTimeout(() => {
            setQuestion(d.data.question)
            setSelected(null)
            setSubmitted(false)
          }, 1000)
        } else {
          // Assessment complete
          setTimeout(() => {
            setPhase('complete')
            setQuestion(null)
          }, 1500)
        }
      }
    } catch (e) {
      setError(e.message)
    }
  }, [selected, question, user_id])

  if (phase === 'intro') return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-6 cursor-pointer">← Back</button>
      <div className="text-center">
        <span className="text-4xl block mb-4">✍️</span>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Knowledge Assessment</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6 max-w-md mx-auto">
          Test your understanding of scripture connections across all 8 works.
          Choose a layer or start with all layers.
        </p>
        <div className="space-y-2 max-w-xs mx-auto mb-6">
          <button onClick={() => startAssessment('')}
            className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium cursor-pointer transition-colors">
            All Layers (Diagnostic)
          </button>
          {Object.entries(LAYER_LABELS).map(([key, label]) => (
            <button key={key} onClick={() => startAssessment(key)}
              className="w-full py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-sm font-medium cursor-pointer transition-colors">
              {label}
            </button>
          ))}
        </div>
        {error && <p className="text-sm text-red-500 dark:text-red-400">{error}</p>}
      </div>
    </div>
  )

  if (loading) return (
    <div className="max-w-2xl mx-auto px-6 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
      <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
    </div>
  )

  if (phase === 'complete') return (
    <div className="max-w-2xl mx-auto px-6 py-8 text-center">
      <span className="text-4xl block mb-4">🎉</span>
      <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Assessment Complete</h2>
      <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mb-4">
        {results.correct}/{results.total} correct
      </p>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
        {results.correct === results.total ? 'Perfect score!' :
         results.correct >= results.total * 0.7 ? 'Good understanding!' :
         results.correct >= results.total * 0.5 ? 'Room for improvement.' :
         'Keep studying — you\'ll get there.'}
      </p>
      <div className="space-y-2 max-w-xs mx-auto mb-6">
        {history.map((h, i) => (
          <div key={i} className={`p-2 rounded-lg text-xs text-left ${h.correct ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300' : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300'}`}>
            <span className="font-medium">{h.correct ? '✓' : '✗'}</span>{' '}
            {h.question?.slice(0, 80)}...
          </div>
        ))}
      </div>
      <div className="flex gap-2 justify-center">
        <button onClick={onBack} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Done</button>
        <button onClick={() => { setPhase('intro'); setResults({ correct: 0, total: 0 }); setHistory([]); setQuestion(null) }}
          className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-sm font-medium cursor-pointer transition-colors">Try Again</button>
      </div>
    </div>
  )

  if (!question) return (
    <div className="max-w-2xl mx-auto px-6 py-8 text-center text-sm text-neutral-500">
      No questions available for this layer.
      <button onClick={onBack} className="block mt-3 mx-auto px-4 py-2 rounded-lg bg-indigo-600 text-white cursor-pointer">Back</button>
    </div>
  )

  const showExplanation = submitted

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">← Back</button>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">Knowledge Assessment</h2>
          {sessionInfo && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
              Layer: {LAYER_LABELS[sessionInfo.target_layer] || 'All'} · Item {sessionInfo.item_number}/{sessionInfo.total_items_planned}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono text-neutral-500">{results.correct}/{results.total}</span>
          {results.total > 0 && (
            <div className="w-16 h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
              <div className="h-full rounded-full bg-green-500" style={{ width: `${(results.correct / results.total) * 100}%` }} />
            </div>
          )}
        </div>
      </div>

      {/* Question */}
      <div className="p-5 rounded-xl border-2 border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20">
        {/* Question type */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
            {question.type?.replace('_', ' ') || 'Question'} · {question.layer || ''}
          </span>
          {question.bloom_level && (
            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-indigo-200 dark:bg-indigo-800 text-indigo-700 dark:text-indigo-300">
              {question.bloom_level}
            </span>
          )}
        </div>

        {/* Question text */}
        <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-4 font-medium">
          {question.question}
        </p>

        {/* Options */}
        {(question.options || []).length > 0 ? (
          <div className="space-y-1.5">
            {question.options.map((opt, i) => {
              const isCorrect = opt === question.correct_answer || i === question.correct_answer
              const isSelected = selected === opt || selected === i
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

              return (
                <button key={i} onClick={() => { if (!submitted) setSelected(opt) }} className={cls}>
                  <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + i)}.</span>
                  {opt}
                </button>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-neutral-500 italic">True or False question — select your answer above.</p>
        )}

        {/* Submit / Next */}
        {!submitted ? (
          <button onClick={submitAnswer}
            disabled={selected === null}
            className="mt-4 w-full py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-700 text-white">
            Submit Answer
          </button>
        ) : (
          <p className="mt-3 text-xs text-neutral-500 dark:text-neutral-400 text-center italic">
            {selected === question.correct_answer || selected === question.correct_answer 
              ? '✓ Correct!'
              : `✗ The answer was: ${question.correct_answer}`}
          </p>
        )}
      </div>
    </div>
  )
}
