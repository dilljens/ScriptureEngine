import React, { useState, useEffect, useCallback, useRef } from 'react'
import HebrewKeyboard from './HebrewKeyboard'

/**
 * HebrewLessonView — enhanced lesson player with:
 * - Audio playback for every Hebrew word
 * - Cloze deletion from verse text
 * - Recognition→Recall→Production ladder
 * - English→Hebrew and Hebrew→English sentence forming
 * - Mastery tracking with dynamic difficulty
 */

const TYPE_COLORS = {
  multiple_choice: 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800',
  cloze: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800',
  recall: 'bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800',
  typing: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
  transliteration: 'bg-cyan-50 dark:bg-cyan-900/20 border-cyan-200 dark:border-cyan-800',
}

const STAGE_ICONS = { recognition: '👁', recall: '🧠', production: '✍️' }
const STAGE_LABELS = { recognition: 'Recognition', recall: 'Recall', production: 'Production' }

export default function HebrewLessonView({ nodeId, onBack }) {
  const [node, setNode] = useState(null)
  const [practice, setPractice] = useState([])
  const [lessonContent, setLessonContent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [typedValue, setTypedValue] = useState('')
  const [showKeyboard, setShowKeyboard] = useState(false)
  const [results, setResults] = useState({ correct: 0, total: 0, streak: 0, bestStreak: 0 })
  const [completed, setCompleted] = useState(false)
  const [stage, setStage] = useState('recognition')
  const [hebrewText, setHebrewText] = useState('')
  const [audioPlaying, setAudioPlaying] = useState(null)
  const audioRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`/api/v1/hebrew/lesson/${nodeId}`).then(r => r.json()),
      fetch(`/api/v1/hebrew/practice/${nodeId}`).then(r => r.json()),
      fetch(`/api/v1/hebrew/curriculum`).then(r => r.json()),
    ])
      .then(([nodeRes, practiceRes, curriculumRes]) => {
        if (!nodeRes.ok) throw new Error(nodeRes.detail || 'Failed to load lesson')
        const nd = nodeRes.data
        setNode(nd)
        
        // Extract lesson content
        let content = nd.lesson || nd.content || ''
        if (typeof content === 'object') content = JSON.stringify(content, null, 2)
        setLessonContent(content)
        
        // Get practice items
        const items = practiceRes.data?.items || []
        setPractice(items)
        
        // Set Hebrew text for the lesson
        const heb = nd.hebrew || nd.title?.split('—')[0]?.trim() || ''
        setHebrewText(heb)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [nodeId])

  // Play audio for a Hebrew word
  const playAudio = useCallback(async (word) => {
    if (!word) return
    try {
      const r = await fetch(`/api/v1/hebrew/audio/${encodeURIComponent(word)}`)
      const d = await r.json()
      if (d.ok && d.data?.audio_url) {
        if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
        const audio = new Audio(d.data.audio_url)
        audioRef.current = audio
        audio.onended = () => setAudioPlaying(null)
        audio.onerror = () => setAudioPlaying(null)
        audio.play().then(() => setAudioPlaying(word)).catch(() => setAudioPlaying(null))
      }
    } catch {}
  }, [])

  // Submit answer and record progress
  const submitAnswer = useCallback(async (correct) => {
    try {
      await fetch('/api/v1/hebrew/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, correct, user_id: 'default' }),
      })
    } catch {}
    setResults(prev => ({
      correct: prev.correct + (correct ? 1 : 0),
      total: prev.total + 1,
      streak: correct ? prev.streak + 1 : 0,
      bestStreak: Math.max(prev.bestStreak, correct ? prev.streak + 1 : 0),
    }))
  }, [nodeId])

  const handleCheck = () => {
    const q = practice[currentIdx]
    if (!q) return

    let correct = false
    if (q.question_type === 'typing' || q.question_type === 'recall' || q.question_type === 'cloze' || q.question_type === 'transliteration') {
      const answer = q.correct_answer?.toLowerCase().trim() || ''
      const typed = typedValue?.toLowerCase().trim() || ''
      correct = typed === answer || typed.includes(answer) || answer.includes(typed)
    } else {
      correct = selected === q.correct_answer
    }

    setSubmitted(true)
    submitAnswer(correct)

    // Advance stage
    if (correct) {
      if (stage === 'recognition') setStage('recall')
      else if (stage === 'recall') setStage('production')
    }
  }

  const handleNext = () => {
    if (currentIdx < practice.length - 1) {
      setCurrentIdx(prev => prev + 1)
      setSelected(null)
      setSubmitted(false)
      setTypedValue('')
      // Move back one stage for variety
      if (stage === 'production') setStage('recall')
    } else {
      setCompleted(true)
    }
  }

  // Cleanup audio on unmount
  useEffect(() => () => { if (audioRef.current) audioRef.current.pause() }, [])

  // ── Render States ──
  if (loading) return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2" />
        <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
        <div className="h-48 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
      </div>
    </div>
  )

  if (error) return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">← Back</button>
      <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">{error}</div>
    </div>
  )

  if (!node) return null

  const q = practice[currentIdx]
  const progressPct = practice.length > 0 ? ((submitted ? currentIdx + 1 : currentIdx) / practice.length) * 100 : 0

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      {/* Back + Audio button */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        {hebrewText && (
          <button onClick={() => playAudio(hebrewText)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-xs font-medium hover:bg-amber-200 dark:hover:bg-amber-900/50 cursor-pointer transition-colors"
            title="Play pronunciation">
            <span>{audioPlaying === hebrewText ? '🔊' : '🔈'}</span>
            <span>{audioPlaying === hebrewText ? 'Playing...' : 'Play word'}</span>
          </button>
        )}
      </div>

      {/* Lesson header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500">Level {node.level}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">{node.category}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">{STAGE_ICONS[stage]} {STAGE_LABELS[stage]}</span>
        </div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{node.title}</h2>
        {node.description && <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{node.description}</p>}
      </div>

      {/* Progress + stats bar */}
      <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <div className="flex-1">
          <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${progressPct}%` }} />
          </div>
        </div>
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">{results.correct}/{results.total}</span>
        {results.streak > 1 && <span className="text-[10px] text-amber-600 dark:text-amber-400 font-mono">🔥{results.streak}</span>}
      </div>

      {/* Completed state */}
      {completed ? (
        <div className="p-6 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-center">
          <span className="text-3xl block mb-2">🎉</span>
          <h3 className="text-base font-semibold text-green-800 dark:text-green-200 mb-1">Lesson Complete!</h3>
          <p className="text-sm text-green-600 dark:text-green-400 mb-1">
            {results.correct}/{results.total} correct ({Math.round((results.correct / Math.max(results.total, 1)) * 100)}%)
          </p>
          {results.bestStreak > 2 && (
            <p className="text-xs text-green-500 dark:text-green-400 mb-4">Best streak: {results.bestStreak} 🔥</p>
          )}
          <div className="flex gap-2 justify-center">
            <button onClick={onBack} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Back to curriculum</button>
            <button onClick={() => { setCurrentIdx(0); setSelected(null); setSubmitted(false); setCompleted(false); setResults({ correct: 0, total: 0, streak: 0, bestStreak: 0 }); setStage('recognition') }}
              className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-sm font-medium cursor-pointer transition-colors">Retry</button>
          </div>
        </div>
      ) : q ? (
        <div className={`p-4 rounded-xl border ${TYPE_COLORS[q.question_type] || 'bg-neutral-50 dark:bg-neutral-900/50 border-neutral-200 dark:border-neutral-700'}`}>
          {/* Header bar */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">{q.question_type?.replace(/_/g, ' ')} {currentIdx + 1}/{practice.length}</span>
              {hebrewText && (
                <button onClick={() => {
                  // Find the Hebrew word in this question
                  const words = [hebrewText, node.hebrew, node.title?.split('—')[0]?.trim()].filter(Boolean)
                  playAudio(words[0])
                }}
                  className="text-xs text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 cursor-pointer"
                  title="Play audio for this word">
                  🔊
                </button>
              )}
            </div>
            {submitted && q.correct_answer && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300">Answer: {q.correct_answer}</span>
            )}
          </div>

          {/* Question text with any Hebrew in large font */}
          <div className="mb-4">
            {(q.question_text || '').split('\n').map((line, i) => {
              const hasHebrew = /[\u0590-\u05FF]/.test(line)
              return hasHebrew ? (
                <p key={i} className="text-xl font-serif leading-relaxed text-neutral-800 dark:text-neutral-200 mb-1" dir="rtl"
                  style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>{line}</p>
              ) : (
                <p key={i} className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-1">{line}</p>
              )
            })}
          </div>

          {/* Answer input */}
          {['typing', 'recall', 'cloze', 'transliteration'].includes(q.question_type) ? (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <input type="text" value={typedValue} onChange={e => setTypedValue(e.target.value)}
                  disabled={submitted}
                  placeholder={q.question_type === 'transliteration' ? 'Type transliteration (e.g., bereshit)' : 'Type your answer'}
                  className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 disabled:opacity-60"
                  dir={q.question_type === 'typing' || q.question_type === 'cloze' ? 'rtl' : 'ltr'}
                  onKeyDown={e => { if (e.key === 'Enter' && !submitted && typedValue.trim()) handleCheck() }} />
                {q.question_type !== 'transliteration' && (
                  <button onClick={() => setShowKeyboard(!showKeyboard)}
                    className="px-2.5 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-xs font-medium cursor-pointer transition-colors shrink-0">
                    ⌨
                  </button>
                )}
              </div>
              {showKeyboard && (
                <HebrewKeyboard value={typedValue} onCharClick={c => setTypedValue(prev => prev + c)}
                  onBackspace={() => setTypedValue(prev => prev.slice(0, -1))}
                  onClear={() => setTypedValue('')}
                  onDone={() => setShowKeyboard(false)} />
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              {(q.options_json ? (() => { try { return JSON.parse(q.options_json) } catch { return [] } })() : []).map((opt, i) => {
                const isCorrect = opt === q.correct_answer || String(i) === String(q.correct_answer)
                const isSelected = selected === opt || selected === i || selected === String(i)
                let cls = 'w-full text-left px-3 py-2.5 rounded-lg text-sm border transition-all cursor-pointer '
                if (!submitted) {
                  cls += isSelected ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                } else {
                  cls += isCorrect ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                    : isSelected && !isCorrect ? 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                    : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
                }
                const isHeb = /[\u0590-\u05FF]/.test(opt)
                return (
                  <button key={i} onClick={() => setSelected(opt)} className={cls}>
                    <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + i)}.</span>
                    {isHeb ? <span className="text-lg font-serif" dir="rtl" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>{opt}</span>
                    : <span>{opt}</span>}
                  </button>
                )
              })}
            </div>
          )}

          {/* Submit/Next */}
          <div className="flex gap-2 mt-4">
            {!submitted ? (
              <button onClick={handleCheck}
                disabled={['typing','recall','cloze','transliteration'].includes(q.question_type) ? !typedValue.trim() : selected === null}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium cursor-pointer transition-colors">
                Check
              </button>
            ) : (
              <button onClick={handleNext}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
                {currentIdx < practice.length - 1 ? 'Next →' : 'See Results'}
              </button>
            )}
          </div>

          {/* Explanation */}
          {submitted && q.explanation && (
            <div className="mt-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed">{q.explanation}</div>
          )}
        </div>
      ) : (
        <div className="p-6 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-center text-sm text-neutral-500 dark:text-neutral-400">
          No practice questions for this lesson.
          <button onClick={onBack} className="block mt-3 mx-auto px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Back</button>
        </div>
      )}

      {/* Stage progress indicator */}
      <div className="flex items-center justify-center gap-4 mt-4 text-[10px] text-neutral-400 dark:text-neutral-500">
        <span className={`flex items-center gap-1 ${stage === 'recognition' ? 'text-indigo-600 dark:text-indigo-400 font-medium' : ''}`}>
          <span>👁</span> Recognition
        </span>
        <span className="text-neutral-300 dark:text-neutral-600">→</span>
        <span className={`flex items-center gap-1 ${stage === 'recall' ? 'text-indigo-600 dark:text-indigo-400 font-medium' : ''}`}>
          <span>🧠</span> Recall
        </span>
        <span className="text-neutral-300 dark:text-neutral-600">→</span>
        <span className={`flex items-center gap-1 ${stage === 'production' ? 'text-indigo-600 dark:text-indigo-400 font-medium' : ''}`}>
          <span>✍️</span> Production
        </span>
      </div>
    </div>
  )
}
