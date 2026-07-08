import React, { useState } from 'react'

/**
 * QuizCard — displays 1-5 questions at once in the chat.
 * User answers all, submits batch, gets results.
 */

export default function QuizCard({ questions, onAnswer }) {
  // Normalize: accept single question or array
  const qs = Array.isArray(questions) ? questions : (questions ? [questions] : [])
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState({})
  const [batchDone, setBatchDone] = useState(false)

  if (qs.length === 0) return null

  const handleSelect = (qIdx, optIdx) => {
    if (batchDone) return
    setAnswers(prev => ({ ...prev, [qIdx]: optIdx }))
  }

  const handleSubmit = () => {
    const newSubmitted = {}
    qs.forEach((q, i) => {
      const ans = answers[i]
      if (ans === undefined) return
      newSubmitted[i] = ans === (q.correctAnswer !== undefined ? q.correctAnswer : (q.correct || 0))
    })
    setSubmitted(newSubmitted)
    setBatchDone(true)
    if (onAnswer) onAnswer(Object.values(newSubmitted))
  }

  const allAnswered = qs.every((_, i) => answers[i] !== undefined)

  return (
    <div className="my-3 space-y-3">
      <div className="flex items-center gap-2 text-[10px] text-neutral-400 dark:text-neutral-500 font-medium">
        <span>📝 Knowledge Check</span>
        <span className="text-neutral-300 dark:text-neutral-600">·</span>
        <span>{qs.length} question{qs.length > 1 ? 's' : ''}</span>
      </div>

      {qs.map((q, qi) => {
        const isCorrect = submitted[qi]
        const options = q.options || []

        return (
          <div key={qi} className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20">
            <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-3 font-medium">
              {qi + 1}. {q.question || q.question_text}
            </p>
            <div className="space-y-1.5">
              {options.map((opt, oi) => {
                const isSelected = answers[qi] === oi
                let cls = 'w-full text-left px-3 py-2 rounded-lg text-sm border transition-all cursor-pointer '
                if (batchDone) {
                  const isOptCorrect = oi === (q.correctAnswer !== undefined ? q.correctAnswer : (q.correct || 0))
                  cls += isOptCorrect
                    ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                    : isSelected && !isOptCorrect
                      ? 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                      : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
                } else {
                  cls += isSelected
                    ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                }
                return (
                  <button key={oi} onClick={() => handleSelect(qi, oi)} className={cls}>
                    <span className="font-medium mr-2">{String.fromCharCode(65 + oi)}.</span>
                    {opt}
                  </button>
                )
              })}
            </div>
            {batchDone && isCorrect !== undefined && (
              <p className={`mt-2 text-xs ${isCorrect ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                {isCorrect ? '✓ Correct' : '✗ Incorrect'}
              </p>
            )}
          </div>
        )
      })}

      {!batchDone && (
        <button onClick={handleSubmit} disabled={!allAnswered}
          className="w-full py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-700 text-white">
          Submit All ({qs.length} question{qs.length > 1 ? 's' : ''})
        </button>
      )}
      {batchDone && (
        <p className="text-xs text-neutral-500 dark:text-neutral-400 text-center italic">
          {Object.values(submitted).filter(Boolean).length}/{qs.length} correct · Tell the LLM how you did!
        </p>
      )}
    </div>
  )
}
