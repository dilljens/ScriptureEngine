import React, { useState, useMemo } from 'react'

/**
 * HebrewQuizCard — interactive Hebrew knowledge quiz.
 * Renders in chat via %%%HEBREW_QUIZ:...%%% markers.
 *
 * Question types:
 *   letter_name: "What letter is this? → א"  (multiple choice with letter names)
 *   letter_recognition: "What does this letter sound like? → Aleph" (shows name, pick letter)
 *   multiple_choice: general knowledge questions
 *   transliteration: "How is this word pronounced?"
 */
export default function HebrewQuizCard({ quizData, onComplete }) {
  const [selected, setSelected] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [showExplanation, setShowExplanation] = useState(false)

  const { question, options, correctAnswer, explanation, category, nodeTitle } = quizData || {}

  const handleSelect = (idx) => {
    if (submitted) return
    setSelected(idx)
  }

  const handleSubmit = () => {
    if (selected === null) return
    setSubmitted(true)
    setShowExplanation(true)
    if (onComplete) onComplete(selected === correctAnswer)
  }

  const isCorrect = submitted && selected === correctAnswer

  // Render Hebrew letter large
  const renderLetter = () => {
    if (!quizData.hebrewGlyph) return null
    return (
      <div className="text-center mb-4">
        <span className="text-5xl font-serif leading-relaxed"
          style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
          dir="rtl">
          {quizData.hebrewGlyph}
        </span>
      </div>
    )
  }

  const categoryColors = {
    consonant: 'border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20',
    vowel: 'border-blue-300 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/20',
    word: 'border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/20',
    grammar: 'border-purple-300 dark:border-purple-700 bg-purple-50 dark:bg-purple-900/20',
    phrase: 'border-pink-300 dark:border-pink-700 bg-pink-50 dark:bg-pink-900/20',
    reading: 'border-indigo-300 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/20',
  }
  const borderColor = categoryColors[category] || 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/20'

  return (
    <div className={`my-3 p-4 rounded-xl border-2 ${borderColor}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-sm">📖</span>
        <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
          Hebrew Quiz{category ? ` — ${category}` : ''}
          {nodeTitle ? ` — ${nodeTitle}` : ''}
        </span>
      </div>

      {/* Hebrew letter display (large) */}
      {renderLetter()}

      {/* Question */}
      <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-3 font-medium">
        {question}
      </p>

      {/* Options as buttons */}
      <div className="space-y-1.5">
        {(options || []).map((opt, i) => {
          let cls = 'w-full text-left px-3 py-2.5 rounded-lg text-sm border transition-all cursor-pointer '
          
          if (!submitted) {
            cls += selected === i
              ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
              : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
          } else {
            if (i === correctAnswer) {
              cls += 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
            } else if (i === selected && selected !== correctAnswer) {
              cls += 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
            } else {
              cls += 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
            }
          }

          // Check if option looks like a Hebrew letter (has Hebrew chars)
          const isHebrewOption = /[\u0590-\u05FF]/.test(opt)

          return (
            <button key={i} onClick={() => handleSelect(i)} className={cls}>
              <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + i)}.</span>
              {isHebrewOption ? (
                <span className="text-xl font-serif" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }} dir="rtl">
                  {opt}
                </span>
              ) : (
                <span>{opt}</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Submit button */}
      {!submitted && (
        <button
          onClick={handleSubmit}
          disabled={selected === null}
          className="mt-3 w-full py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
            bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          Check Answer
        </button>
      )}

      {/* Result feedback */}
      {submitted && (
        <div className={`mt-3 p-3 rounded-lg text-sm ${isCorrect ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200' : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}`}>
          <p className="font-medium">{isCorrect ? '✓ Correct!' : '✗ Not quite'}</p>
          {showExplanation && explanation && (
            <p className="mt-1 text-xs opacity-80">{explanation}</p>
          )}
        </div>
      )}

      {/* Restart hint */}
      {submitted && (
        <p className="mt-2 text-[10px] text-neutral-400 dark:text-neutral-500 text-center italic">
          Ask for another question to keep going
        </p>
      )}
    </div>
  )
}
