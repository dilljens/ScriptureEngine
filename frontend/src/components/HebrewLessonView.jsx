import React, { useState, useEffect, useCallback, useRef } from 'react'
import HebrewKeyboard from './HebrewKeyboard'

/**
 * HebrewLessonView — shows questions in batches (1-5 at a time).
 * User answers all, submits once, gets batch feedback.
 * Supports: MC, cloze, recall, typing, transliteration.
 */

const TYPE_COLORS = {
  multiple_choice: 'border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20',
  cloze: 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20',
  recall: 'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20',
  typing: 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20',
  transliteration: 'border-cyan-200 dark:border-cyan-800 bg-cyan-50 dark:bg-cyan-900/20',
}

export default function HebrewLessonView({ nodeId, onBack, batchSize = 5 }) {
  const [node, setNode] = useState(null)
  const [practice, setPractice] = useState([])
  const [lessonContent, setLessonContent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [batch, setBatch] = useState(0)         // which batch of batchSize
  const [answers, setAnswers] = useState({})    // { questionIdx: selectedValue }
  const [submitted, setSubmitted] = useState({}) // { questionIdx: true/false } — true=correct false=wrong
  const [showKeyboard, setShowKeyboard] = useState(false)
  const [keyboardTarget, setKeyboardTarget] = useState(null)
  const [results, setResults] = useState({ correct: 0, total: 0, streak: 0, bestStreak: 0 })
  const [completed, setCompleted] = useState(false)
  const [audioPlaying, setAudioPlaying] = useState(null)
  const audioRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`/api/v1/hebrew/lesson/${nodeId}`).then(r => r.json()),
      fetch(`/api/v1/hebrew/practice/${nodeId}`).then(r => r.json()),
    ])
      .then(([nodeRes, practiceRes]) => {
        if (!nodeRes.ok) throw new Error(nodeRes.detail || 'Failed to load')
        const nd = nodeRes.data
        setNode(nd)
        let content = nd.lesson || nd.content || ''
        if (typeof content === 'object') content = JSON.stringify(content, null, 2)
        setLessonContent(content)
        setPractice(practiceRes.data?.items || [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [nodeId])

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

  useEffect(() => () => { if (audioRef.current) audioRef.current.pause() }, [])

  // Current batch questions
  const startIdx = batch * batchSize
  const batchQuestions = practice.slice(startIdx, startIdx + batchSize)
  const totalBatches = Math.ceil(practice.length / batchSize)

  // Submit current batch
  const handleSubmitBatch = async () => {
    const newSubmitted = {}
    let batchCorrect = 0
    let batchTotal = 0

    batchQuestions.forEach((q, i) => {
      const idx = startIdx + i
      const ans = answers[idx]
      if (ans === undefined || ans === null || ans === '') return

      let correct = false
      if (['typing', 'recall', 'cloze', 'transliteration'].includes(q.question_type)) {
        const expected = (q.correct_answer || '').toLowerCase().trim()
        const given = (ans || '').toLowerCase().trim()
        correct = given === expected || given.includes(expected) || expected.includes(given)
      } else {
        correct = ans === q.correct_answer
      }
      newSubmitted[idx] = correct
      if (correct) batchCorrect++
      batchTotal++
    })

    setSubmitted(prev => ({ ...prev, ...newSubmitted }))

    // Report each answer to progress
    for (const [idx, correct] of Object.entries(newSubmitted)) {
      try {
        await fetch('/api/v1/hebrew/progress', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ node_id: nodeId, correct, user_id: 'default' }),
        })
      } catch {}
    }

    setResults(prev => ({
      correct: prev.correct + batchCorrect,
      total: prev.total + batchTotal,
      streak: batchCorrect === batchTotal ? prev.streak + 1 : 0,
      bestStreak: Math.max(prev.bestStreak, batchCorrect === batchTotal ? prev.streak + 1 : 0),
    }))
  }

  // Go to next batch
  const handleNextBatch = () => {
    if (batch < totalBatches - 1) {
      setBatch(prev => prev + 1)
      setAnswers({})
      setSubmitted({})
    } else {
      setCompleted(true)
    }
  }

  // Set answer for a question
  const setAnswer = (idx, value) => {
    setAnswers(prev => ({ ...prev, [idx]: value }))
  }

  const hebrewWord = node?.hebrew || node?.title?.split('—')[0]?.trim() || ''

  if (loading) return (
    <div className="max-w-3xl mx-auto px-6 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2" />
      <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
    </div>
  )

  if (error) return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">← Back</button>
      <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">{error}</div>
    </div>
  )

  if (!node) return null

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        <div className="flex items-center gap-2">
          {hebrewWord && (
            <button onClick={() => playAudio(hebrewWord)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-xs font-medium hover:bg-amber-200 dark:hover:bg-amber-900/50 cursor-pointer transition-colors">
              <span>{audioPlaying === hebrewWord ? '🔊' : '🔈'}</span>
              <span>{audioPlaying === hebrewWord ? 'Playing...' : 'Play'}</span>
            </button>
          )}
          <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500">
            Batch {batch + 1}/{totalBatches}
          </span>
        </div>
      </div>

      {/* Title */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500">Level {node.level}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">{node.category}</span>
        </div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{node.title}</h2>
        {node.description && <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{node.description}</p>}
      </div>

      {/* Lesson content (shown once) */}
      {batch === 0 && lessonContent && Object.keys(submitted).length === 0 && (
        <div className="mb-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap max-h-60 overflow-y-auto">
          {lessonContent}
        </div>
      )}

      {/* Progress */}
      <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <div className="flex-1">
          <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${(results.total / Math.max(practice.length, 1)) * 100}%` }} />
          </div>
        </div>
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">{results.correct}/{results.total}</span>
        {results.streak > 1 && <span className="text-[10px] text-amber-600 dark:text-amber-400 font-mono">🔥{results.streak}</span>}
      </div>

      {/* Completed */}
      {completed ? (
        <div className="p-6 rounded-xl bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-center">
          <span className="text-3xl block mb-2">🎉</span>
          <h3 className="text-base font-semibold text-green-800 dark:text-green-200 mb-1">Complete!</h3>
          <p className="text-sm text-green-600 dark:text-green-400 mb-1">{results.correct}/{results.total} ({Math.round(results.correct / Math.max(results.total, 1) * 100)}%)</p>
          {results.bestStreak > 2 && <p className="text-xs text-green-500 dark:text-green-400 mb-4">Best streak: {results.bestStreak} 🔥</p>}
          <div className="flex gap-2 justify-center">
            <button onClick={onBack} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Back</button>
            <button onClick={() => { setBatch(0); setAnswers({}); setSubmitted({}); setCompleted(false); setResults({ correct: 0, total: 0, streak: 0, bestStreak: 0 }) }}
              className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-sm font-medium cursor-pointer transition-colors">Retry</button>
          </div>
        </div>
      ) : batchQuestions.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[10px] text-neutral-400 dark:text-neutral-500">
            Answer all {batchQuestions.length} questions below, then click Submit.
          </p>

          {batchQuestions.map((q, qi) => {
            const idx = startIdx + qi
            const isSubmitted = idx in submitted
            const isCorrect = submitted[idx]
            const answer = answers[idx]
            const hasHebrew = /[\u0590-\u05FF]/.test(q.question_text)

            return (
              <div key={idx} className={`p-4 rounded-xl border ${TYPE_COLORS[q.question_type] || 'bg-neutral-50 dark:bg-neutral-900/50 border-neutral-200 dark:border-neutral-700'}`}>
                {/* Question header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                      Q{idx + 1} · {q.question_type?.replace(/_/g, ' ')}
                    </span>
                  </div>
                  {isSubmitted && (
                    <span className={`text-[10px] font-medium ${isCorrect ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {isCorrect ? '✓ Correct' : '✗ Incorrect'}
                    </span>
                  )}
                </div>

                {/* Question text */}
                <div className="mb-3">
                  {q.question_text.split('\n').map((line, li) => {
                    const isHb = /[\u0590-\u05FF]/.test(line)
                    return isHb
                      ? <p key={li} className="text-xl font-serif leading-relaxed text-neutral-800 dark:text-neutral-200 mb-1" dir="rtl" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>{line}</p>
                      : <p key={li} className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-1">{line}</p>
                  })}
                </div>

                {/* Answer area */}
                {['typing', 'recall', 'cloze', 'transliteration'].includes(q.question_type) ? (
                  <div className="flex items-center gap-2">
                    <input type="text" value={answer || ''} onChange={e => setAnswer(idx, e.target.value)}
                      disabled={isSubmitted}
                      placeholder={q.question_type === 'transliteration' ? 'Type transliteration...' : 'Type answer...'}
                      className={`flex-1 px-3 py-2 rounded-lg border text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 disabled:opacity-60
                        ${isSubmitted ? (isCorrect ? 'border-green-400 bg-green-50 dark:bg-green-900/20' : 'border-red-400 bg-red-50 dark:bg-red-900/20') : 'border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200'}`}
                      dir={q.question_type === 'typing' || q.question_type === 'cloze' ? 'rtl' : 'ltr'} />
                    {q.question_type !== 'transliteration' && (
                      <button onClick={() => { setShowKeyboard(true); setKeyboardTarget(idx) }}
                        className="px-2.5 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-xs font-medium cursor-pointer transition-colors shrink-0">⌨</button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {(q.options_json ? (() => { try { return JSON.parse(q.options_json) } catch { return [] } })() : []).map((opt, oi) => {
                      const isSelected = answer === opt || answer === String(oi)
                      let cls = 'w-full text-left px-3 py-2 rounded-lg text-sm border transition-all cursor-pointer '
                      if (isSubmitted) {
                        const isOptCorrect = opt === q.correct_answer || String(oi) === String(q.correct_answer)
                        cls += isOptCorrect ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                          : isSelected && !isOptCorrect ? 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                          : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
                      } else {
                        cls += isSelected
                          ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                          : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                      }
                      const isHeb = /[\u0590-\u05FF]/.test(opt)
                      return (
                        <button key={oi} onClick={() => { if (!isSubmitted) setAnswer(idx, opt) }} className={cls}>
                          <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + oi)}.</span>
                          {isHeb ? <span className="text-lg font-serif" dir="rtl" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>{opt}</span> : <span>{opt}</span>}
                        </button>
                      )
                    })}
                  </div>
                )}

                {/* Explanation on submit */}
                {isSubmitted && q.explanation && (
                  <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">{q.explanation}</div>
                )}
              </div>
            )
          })}

          {/* Submit / Next Batch buttons */}
          <div className="flex gap-2">
            {!batchQuestions.some((_, i) => (startIdx + i) in submitted) ? (
              <button onClick={handleSubmitBatch}
                disabled={batchQuestions.every((_, i) => answers[startIdx + i] === undefined || answers[startIdx + i] === null || answers[startIdx + i] === '')}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium cursor-pointer transition-colors">
                Submit All Answers
              </button>
            ) : (
              <button onClick={handleNextBatch}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
                {batch < totalBatches - 1 ? `Next Batch (${batch + 2}/${totalBatches}) →` : 'See Results'}
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="p-6 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border-neutral-200 dark:border-neutral-700 text-center text-sm text-neutral-500 dark:text-neutral-400">
          No questions for this lesson.
          <button onClick={onBack} className="block mt-3 mx-auto px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Back</button>
        </div>
      )}

      {/* Keyboard overlay */}
      {showKeyboard && (
        <div className="fixed inset-0 z-50 bg-black/30 flex items-end justify-center" onClick={() => setShowKeyboard(false)}>
          <div className="bg-white dark:bg-neutral-900 rounded-t-2xl p-4 w-full max-w-lg" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-neutral-500 dark:text-neutral-400">Hebrew Keyboard</span>
              <button onClick={() => setShowKeyboard(false)} className="text-xs text-neutral-400 hover:text-neutral-600 cursor-pointer">✕</button>
            </div>
            <HebrewKeyboard
              value={answers[keyboardTarget] || ''}
              onCharClick={c => { if (keyboardTarget !== null) setAnswer(keyboardTarget, (answers[keyboardTarget] || '') + c) }}
              onBackspace={() => { if (keyboardTarget !== null) setAnswer(keyboardTarget, (answers[keyboardTarget] || '').slice(0, -1)) }}
              onClear={() => { if (keyboardTarget !== null) setAnswer(keyboardTarget, '') }}
              onDone={() => setShowKeyboard(false)} />
          </div>
        </div>
      )}

      {/* Audio el */}
      <audio ref={audioRef} />
    </div>
  )
}
