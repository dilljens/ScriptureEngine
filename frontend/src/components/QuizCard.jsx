import React, { useState } from 'react'

/**
 * Interactive quiz card rendered from %%QUIZ:...%% markers in LLM responses.
 * Supports multiple-choice questions with clickable options.
 */
export default function QuizCard({ question, options, onAnswer }) {
  const [selected, setSelected] = useState(null)
  const [submitted, setSubmitted] = useState(false)

  const handleSelect = (idx) => {
    if (submitted) return
    setSelected(idx)
  }

  const handleSubmit = () => {
    if (selected === null) return
    setSubmitted(true)
    if (onAnswer) onAnswer(selected)
  }

  return (
    <div className="my-3 p-4 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm">📝</span>
        <span className="text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Knowledge Check</span>
      </div>
      <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-3">
        {question}
      </p>
      <div className="space-y-1.5">
        {options.map((opt, i) => {
          let cls = 'w-full text-left px-3 py-2 rounded-lg text-sm border transition-all cursor-pointer '
          if (!submitted) {
            cls += selected === i
              ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200'
              : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
          } else {
            // Show correct/incorrect after submit
            cls += selected === i
              ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200'
              : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
          }
          return (
            <button key={i} onClick={() => handleSelect(i)} className={cls}>
              <span className="font-medium mr-2">{String.fromCharCode(65 + i)}.</span>
              {opt}
            </button>
          )
        })}
      </div>
      {!submitted && (
        <button
          onClick={handleSubmit}
          disabled={selected === null}
          className="mt-3 w-full py-2 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
            bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          Submit Answer
        </button>
      )}
      {submitted && (
        <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400 text-center italic">
          Tell the LLM your answer to get feedback and the next question
        </p>
      )}
    </div>
  )
}
