import React, { useState, useMemo, useRef, useEffect } from 'react'

/**
 * HebrewQuizCard — interactive Hebrew knowledge quiz.
 * Renders in chat via %%%HEBREW_QUIZ:...%%% markers.
 *
 * Question types:
 *   letter_name: "What letter is this? → א"  (multiple choice with letter names)
 *   letter_recognition: "What does this letter sound like? → Aleph" (shows name, pick letter)
 *   multiple_choice: general knowledge questions
 *   true_false: true/false questions
 *   typing: "Type the letter: Aleph" — text input, expects Hebrew character
 *   transliteration: "How is א transliterated?" — text input, expects Latin
 *   recall: "What is X in Hebrew?" — text input
 *   cloze: "Complete the verse: ___" — text input, fill in blank
 *   contrast: discrimination between similar items
 */
export default function HebrewQuizCard({ quizData, onComplete }) {
  const [selected, setSelected] = useState(null)
  const [textInput, setTextInput] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [showExplanation, setShowExplanation] = useState(false)
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [selfAssessed, setSelfAssessed] = useState(null) // null | true | false
  const inputRef = useRef(null)

  const { question, options, correctAnswer, explanation, category, nodeTitle, questionType, hebrewGlyph } = quizData || {}

  const isProductionType = ['typing', 'transliteration', 'recall', 'cloze', 'contrast'].includes(questionType)
  const isChoiceType = ['multiple_choice', 'true_false', 'letter_name', 'letter_recognition', 'classification'].includes(questionType)
  const isAudioType = questionType === 'recitation'
  const hasHebrewText = hebrewGlyph || (question && /[\u0590-\u05FF]/.test(question))

  // Focus input on mount for production types
  useEffect(() => {
    if (isProductionType && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isProductionType])

  const handleSelect = (idx) => {
    if (submitted) return
    setSelected(idx)
  }

  const handleTextSubmit = () => {
    if (!textInput.trim()) return
    setSubmitted(true)
    setShowExplanation(true)
    if (onComplete) {
      // Normalize both inputs for comparison
      const normalize = (s) => s.trim().replace(/\s+/g, ' ').replace(/[\u0591-\u05AF]/g, '').toLowerCase()
      const userAns = normalize(textInput)
      const correctAns = normalize(String(correctAnswer || ''))
      // Also check if correct answer is one of multiple acceptable answers (separated by | or /)
      const acceptable = correctAns.split(/[|/]/).map(s => s.trim())
      const isCorrect = acceptable.some(a => userAns === a) || userAns === correctAns
      onComplete(isCorrect)
    }
  }

  const handleChoiceSubmit = () => {
    if (selected === null) return
    setSubmitted(true)
    setShowExplanation(true)
    if (onComplete) onComplete(selected === correctAnswer)
  }

  const handleRecitationAssessment = (correct) => {
    setSelfAssessed(correct)
    setSubmitted(true)
    if (onComplete) onComplete(correct)
  }

  const isCorrect = submitted && !isProductionType && !isAudioType
    ? selected === correctAnswer
    : submitted && isProductionType
    ? (() => {
        const normalize = (s) => s.trim().replace(/\s+/g, ' ').replace(/[\u0591-\u05AF]/g, '').toLowerCase()
        const userAns = normalize(textInput)
        const correctAns = normalize(String(correctAnswer || ''))
        const acceptable = correctAns.split(/[|/]/).map(s => s.trim())
        return acceptable.some(a => userAns === a) || userAns === correctAns
      })()
    : submitted && isAudioType
    ? selfAssessed === true
    : false

  // Render Hebrew letter large
  const renderLetter = () => {
    if (!hebrewGlyph) return null
    return (
      <div className="text-center mb-4">
        <span className="text-5xl font-serif leading-relaxed"
          style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
          dir="rtl">
          {hebrewGlyph}
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
          {questionType && (
            <span className="ml-1.5 px-1.5 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700 text-[9px]">
              {questionType}
            </span>
          )}
        </span>
      </div>

      {/* Hebrew letter display (large) */}
      {renderLetter()}

      {/* Question */}
      <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-3 font-medium">
        {question}
      </p>

      {/* Render by question type */}
      {isChoiceType && (
        /* Multiple choice / True-False / Letter name — options as buttons */
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
      )}

      {isProductionType && !submitted && (
        /* Production types — text input */
        <div>
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleTextSubmit() }}
              placeholder={questionType === 'typing' ? 'Type the Hebrew character...' : 
                          questionType === 'transliteration' ? 'Type the transliteration...' :
                          questionType === 'cloze' ? 'Type the missing word...' :
                          'Type your answer...'}
              className="flex-1 px-3 py-2.5 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 focus:border-indigo-400 dark:focus:border-indigo-500 focus:ring-1 focus:ring-indigo-400 dark:focus:ring-indigo-500 outline-none transition-all"
              dir={questionType === 'typing' || (hebrewGlyph) ? 'rtl' : 'ltr'}
              style={questionType === 'typing' ? { fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif", fontSize: '1.25rem' } : {}}
              autoComplete="off"
              spellCheck={false}
            />
          </div>
          <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">
            {questionType === 'typing' ? 'Type the Hebrew character and press Enter' :
             questionType === 'transliteration' ? 'Type the Latin transliteration' :
             questionType === 'cloze' ? 'Fill in the missing word(s)' :
             'Type your answer and press Enter'}
          </p>
        </div>
      )}

      {isAudioType && !submitted && (
        /* Audio recitation mode */
        <div className="space-y-3">
          {hebrewGlyph && (
            <div className="text-center py-4">
              <span className="text-4xl font-serif" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }} dir="rtl">
                {hebrewGlyph}
              </span>
            </div>
          )}
          <div className="flex gap-2 justify-center">
            <button
              onClick={() => {
                setAudioPlaying(true)
                // Try to play audio via the API
                if (hebrewGlyph) {
                  fetch(`/api/v1/hebrew/audio/${encodeURIComponent(hebrewGlyph)}`)
                    .then(r => r.json())
                    .then(data => {
                      if (data.ok && data.data?.audio_url) {
                        const audio = new Audio(data.data.audio_url)
                        audio.play().catch(() => {}) 
                      }
                    })
                    .catch(() => {})
                }
                setTimeout(() => setAudioPlaying(false), 1000)
              }}
              disabled={audioPlaying}
              className="px-4 py-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-sm font-medium cursor-pointer transition-colors disabled:opacity-50"
            >
              🔈 {audioPlaying ? 'Playing...' : 'Play pronunciation'}
            </button>
          </div>
          <p className="text-xs text-center text-neutral-500 dark:text-neutral-400 font-medium">
            Read this aloud in Hebrew
          </p>
          <div className="flex gap-2 justify-center">
            <button onClick={() => handleRecitationAssessment(true)}
              className="px-4 py-2 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-sm font-medium cursor-pointer transition-colors hover:bg-green-200 dark:hover:bg-green-900/50">
              ✓ I said it correctly
            </button>
            <button onClick={() => handleRecitationAssessment(false)}
              className="px-4 py-2 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm font-medium cursor-pointer transition-colors hover:bg-red-200 dark:hover:bg-red-900/50">
              ✗ I need more practice
            </button>
          </div>
        </div>
      )}

      {/* Submit button for choice types */}
      {isChoiceType && !submitted && (
        <button
          onClick={handleChoiceSubmit}
          disabled={selected === null}
          className="mt-3 w-full py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
            bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          Check Answer
        </button>
      )}

      {/* Submit button for production types */}
      {isProductionType && !submitted && (
        <button
          onClick={handleTextSubmit}
          disabled={!textInput.trim()}
          className="mt-3 w-full py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
            bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          Check Answer
        </button>
      )}

      {/* Result feedback */}
      {submitted && (
        <div className={`mt-3 p-3 rounded-lg text-sm ${
          isCorrect
            ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200'
            : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'
        }`}>
          <p className="font-medium">{isCorrect ? '✓ Correct!' : '✗ Not quite'}</p>
          {isProductionType && !isCorrect && (
            <p className="mt-1 text-xs opacity-80">
              Correct answer: <span className="font-medium" dir={/[\u0590-\u05FF]/.test(correctAnswer) ? 'rtl' : 'ltr'}
                style={/[\u0590-\u05FF]/.test(correctAnswer) ? { fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif", fontSize: '1.1rem' } : {}}>
                {correctAnswer}
              </span>
            </p>
          )}
          {showExplanation && explanation && explanation !== correctAnswer && (
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
