import React, { useState, useEffect, useRef } from 'react'
import HebrewKeyboard from './HebrewKeyboard'

/**
 * HebrewDiagnostic — adaptive placement test (1-up-3-down staircase).
 *
 * Drives the per-skill adaptive endpoint: one question at a time per skill
 * (alphabet → vocab → grammar → reading), each answer adapts the next
 * question's difficulty. Tests-out skills you already know and seeds the
 * spaced-repetition state so known words aren't reviewed heavily.
 */
const TEXT_INPUT_TYPES = new Set(['transliteration', 'cloze', 'recall', 'typing', 'letter_name'])

export default function HebrewDiagnostic({ onComplete, user_id = 'default' }) {
  const [sessionId, setSessionId] = useState(null)
  const [skill, setSkill] = useState('')
  const [skillIndex, setSkillIndex] = useState(0)
  const [totalSkills, setTotalSkills] = useState(4)
  const [question, setQuestion] = useState(null)
  const [answer, setAnswer] = useState('')
  const [submitted, setSubmitted] = useState(null) // null | {correct}
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showKeyboard, setShowKeyboard] = useState(false)
  const answersLog = useRef([])

  // Start the placement test
  useEffect(() => {
    fetch('/api/v1/hebrew/diagnostic/adaptive/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          setSessionId(d.data.session_id)
          setSkill(d.data.skill)
          setSkillIndex(d.data.skill_index)
          setTotalSkills(d.data.total_skills)
          setQuestion(d.data.question)
        } else {
          setError(d.detail || 'Failed to start assessment')
        }
      })
      .catch(() => setError('Failed to connect'))
      .finally(() => setLoading(false))
  }, [user_id])

  const submitAnswer = () => {
    if (!question || submitted) return
    fetch('/api/v1/hebrew/diagnostic/adaptive/answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        question_id: question.question_id,
        node_id: question.node_id,
        answer,
      }),
    })
      .then(r => r.json())
      .then(d => {
        if (!d.ok) { setError(d.detail || 'Failed to submit'); return }
        const data = d.data
        setSubmitted(data.last_correct !== undefined ? { correct: data.last_correct } : null)
        answersLog.current.push({ skill, correct: data.last_correct })

        // Short reveal of correctness before the next question
        setTimeout(() => {
          setAnswer('')
          setSubmitted(null)
          setShowKeyboard(false)
          if (data.done) {
            setResults(data.results)
          } else {
            setSkill(data.skill)
            setSkillIndex(data.skill_index)
            setTotalSkills(data.total_skills)
            setQuestion(data.question)
          }
        }, 900)
      })
      .catch(() => setError('Failed to submit'))
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && question && !submitted) submitAnswer()
  }
  useEffect(() => {
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  })

  const isTextInput = question && TEXT_INPUT_TYPES.has(question.type)

  if (loading) return (
    <div className="max-w-2xl mx-auto px-6 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
      {[1,2,3,4].map(i => <div key={i} className="h-20 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
    </div>
  )

  if (error) return (
    <div className="max-w-2xl mx-auto px-6 py-8 text-center">
      <p className="text-sm text-red-600 dark:text-red-400 mb-4">{error}</p>
      <button onClick={onComplete} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium cursor-pointer">Skip diagnostic →</button>
    </div>
  )

  // ── Results ──
  if (results) {
    const skillLabels = {
      alphabet: 'Alphabet & Vowels',
      vocab: 'Vocabulary',
      grammar: 'Grammar',
      reading: 'Reading',
    }
    const levels = Object.entries(results.skills || {})
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="text-center mb-6">
          <span className="text-4xl block mb-4">📊</span>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Your Placement</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-2 max-w-md mx-auto">
            We adaptively tested 4 skill areas. You've demonstrated mastery in some areas —
            they're unlocked without heavy review. Everything else stays in your curriculum.
          </p>
        </div>

        <div className="space-y-2 mb-4">
          {levels.map(([key, stats]) => (
            <div key={key} className="flex items-center justify-between p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
              <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 capitalize">
                {skillLabels[key] || key}
              </span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-neutral-400">
                  {stats.correct}/{stats.items_asked} · {Math.round((stats.confidence || 0) * 100)}% conf
                </span>
                <span className="text-sm font-bold text-indigo-600 dark:text-indigo-400">
                  Level {stats.estimated_level}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center text-xs text-neutral-400 mb-6">
          {results.nodes_tested_out} skills tested out · {results.srs_seeded} words scheduled for review
        </div>

        <button onClick={onComplete}
          className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium cursor-pointer transition-colors">
          Start Learning
        </button>
      </div>
    )
  }

  // ── Question ──
  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">Placement Test</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Skill {skillIndex + 1}/{totalSkills}: <span className="capitalize">{skill}</span>
          </p>
        </div>
        <div className="flex gap-1">
          {Array.from({ length: totalSkills }).map((_, i) => (
            <div key={i} className={`w-8 h-1.5 rounded-full ${i < skillIndex ? 'bg-green-500' : i === skillIndex ? 'bg-indigo-500' : 'bg-neutral-200 dark:bg-neutral-700'}`} />
          ))}
        </div>
      </div>

      {!question ? (
        <div className="p-6 text-center text-sm text-neutral-500 dark:text-neutral-400">Loading question...</div>
      ) : (
        <div className="p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-indigo-200 dark:border-indigo-800">
          <span className="text-[9px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
            {question.type.replace(/_/g, ' ')} · Level {question.level}
          </span>
          <p className="text-sm text-neutral-800 dark:text-neutral-200 mt-3 mb-4 leading-relaxed">{question.question}</p>

          {isTextInput ? (
            <input type="text" value={answer} autoFocus
              onChange={e => setAnswer(e.target.value)}
              onFocus={() => setShowKeyboard(true)}
              placeholder="Type your answer..."
              className="w-full px-4 py-3 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 text-sm outline-none focus:border-indigo-400 dark:focus:border-indigo-500 font-hebrew-biblical"
              dir="auto"
              disabled={!!submitted}
            />
          ) : (
            <div className="space-y-2">
              {(question.options || []).map((opt, i) => (
                <button key={i} onClick={() => !submitted && setAnswer(opt)}
                  className={`w-full text-left px-4 py-3 rounded-lg text-sm border transition-all cursor-pointer ${
                    answer === opt
                      ? 'border-indigo-400 dark:border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                      : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                  }`}>
                  {opt}
                </button>
              ))}
            </div>
          )}

          {showKeyboard && isTextInput && (
            <div className="mt-4">
              <HebrewKeyboard onCharClick={(c) => setAnswer(a => a + c)} />
              <button onClick={() => setShowKeyboard(false)}
                className="mt-2 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">
                Hide keyboard
              </button>
            </div>
          )}

          <div className="mt-4 flex items-center gap-3">
            <button onClick={submitAnswer} disabled={!answer || !!submitted}
              className={`flex-1 py-3 rounded-xl text-sm font-medium cursor-pointer transition-colors ${
                answer && !submitted
                  ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                  : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 cursor-not-allowed'
              }`}>
              Submit Answer
            </button>
            {submitted && (
              <span className={`text-sm font-medium ${submitted.correct ? 'text-green-600 dark:text-green-400' : 'text-red-500'}`}>
                {submitted.correct ? '✓' : '✗'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
