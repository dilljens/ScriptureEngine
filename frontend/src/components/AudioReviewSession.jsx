import React, { useState, useEffect, useCallback } from 'react'

/**
 * AudioReviewSession — eyes-free audio review for walking/driving/exercising.
 *
 * Speaks Hebrew word → pause → speaks English meaning → user rates recall.
 * Uses Web Speech Synthesis API (no external dependencies).
 *
 * Props:
 *   words: array of {hebrew, english, transliteration}
 *   onComplete: () => void
 */
export default function AudioReviewSession({ words, onComplete }) {
  const [idx, setIdx] = useState(0)
  const [phase, setPhase] = useState('listening') // listening | answering | rated
  const [rating, setRating] = useState(null)
  const [paused, setPaused] = useState(false)

  const current = words?.[idx]

  const speak = useCallback((text, lang = 'he-IL', rate = 0.8) => {
    return new Promise((resolve) => {
      if (!window.speechSynthesis) { resolve(); return }
      const u = new SpeechSynthesisUtterance(text.replace(/[/\u0591-\u05bd\u05bf\u05c1-\u05c7]/g, ''))
      u.lang = lang
      u.rate = rate
      u.onend = resolve
      window.speechSynthesis.speak(u)
    })
  }, [])

  // Speak the Hebrew word
  useEffect(() => {
    if (!current || paused) return
    setPhase('listening')

    const run = async () => {
      if (current.hebrew) {
        await speak(current.hebrew, 'he-IL', 0.7)
      }
      // Pause for user to think
      await new Promise(r => setTimeout(r, 2000))
      // Speak the English answer
      if (current.english) {
        await speak(current.english, 'en-US', 0.9)
      }
      setPhase('answering')
    }
    run()
  }, [current, paused, speak])

  const handleRate = (val) => {
    setRating(val)
    setPhase('rated')
    setTimeout(() => {
      if (idx + 1 < words.length) {
        setIdx(p => p + 1)
        setRating(null)
        setPhase('listening')
      } else {
        if (onComplete) onComplete()
      }
    }, 1000)
  }

  if (!current) {
    return (
      <div className="max-w-lg mx-auto px-4 py-8 text-center">
        <span className="text-4xl block mb-4">🎉</span>
        <p className="text-sm text-neutral-500">Audio review complete!</p>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-neutral-500">Audio Review</span>
        <span className="text-[10px] font-mono text-neutral-400">{idx + 1}/{words.length}</span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mb-8">
        <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${(idx / words.length) * 100}%` }} />
      </div>

      {/* Visual indicator (for when user glances at phone) */}
      <div className="text-center py-8">
        <div className={`text-5xl mb-4 transition-all ${phase === 'listening' ? 'opacity-100 scale-100' : 'opacity-30 scale-90'}`}>
          {phase === 'listening' ? '🔊' : phase === 'answering' ? '💭' : '✓'}
        </div>
        <p className="text-sm text-neutral-400">
          {phase === 'listening' ? 'Listen…' : phase === 'answering' ? 'How did you do?' : 'Recorded'}
        </p>
      </div>

      {/* Rating buttons — only phase after hearing answer */}
      {phase === 'answering' && rating === null && (
        <div className="flex gap-2 justify-center">
          {[
            { val: 1, label: 'Again', color: 'bg-red-500 hover:bg-red-600' },
            { val: 2, label: 'Hard', color: 'bg-amber-500 hover:bg-amber-600' },
            { val: 3, label: 'Good', color: 'bg-green-500 hover:bg-green-600' },
            { val: 4, label: 'Easy', color: 'bg-blue-500 hover:bg-blue-600' },
          ].map(b => (
            <button key={b.val} onClick={() => handleRate(b.val)}
              className={`px-4 py-2 rounded-lg text-white text-sm font-medium cursor-pointer transition-colors ${b.color}`}>
              {b.label}
            </button>
          ))}
        </div>
      )}

      {/* Pause/Resume */}
      <div className="text-center mt-4">
        <button onClick={() => setPaused(!paused)}
          className="text-xs text-neutral-400 hover:text-neutral-600 cursor-pointer">
          {paused ? '▶ Resume' : '⏸ Pause'}
        </button>
      </div>

      {/* Only show text if user glances at screen */}
      <div className="mt-6 text-center text-xs text-neutral-400">
        <p className="font-serif text-lg text-neutral-600 dark:text-neutral-400"
          style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
          {current.hebrew}
        </p>
        <p className="mt-1">{current.transliteration || current.english}</p>
      </div>
    </div>
  )
}
