import React, { useState, useCallback, useEffect } from 'react'

/**
 * AssessmentView — serves the new deep questions from assessment_items.
 * Three modes:
 *   quiz   — multiple choice from /api/v1/quiz with tier filtering
 *   open   — open-ended short answer, graded by LLM via /api/v1/assess/grade
 *
 * Tiers: text (verifiable from passage), analysis (patterns), consistency (multi-witness)
 */
const TIER_META = {
  text:        { label: 'Text',        color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',        icon: '🔬', desc: 'Verifiable from the passage text' },
  analysis:    { label: 'Analysis',    color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300', icon: '🔍', desc: 'Patterns, comparisons, cross-references' },
  consistency: { label: 'Consistency', color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',   icon: '🤝', desc: 'Taught across multiple witnesses' },
}

const TIER_OPTIONS = [
  { id: '', label: 'All Tiers', icon: '📚' },
  { id: 'text', label: 'Text', icon: '🔬' },
  { id: 'analysis', label: 'Analysis', icon: '🔍' },
  { id: 'consistency', label: 'Consistency', icon: '🤝' },
]

const OPEN_RUBRIC = `Your answer will be evaluated on:
1. TEXT ENGAGEMENT — Do you reference specific words or phrases?
2. REASONING QUALITY — Is your argument logical and consistent?
3. DEPTH — Do you go beyond surface observation to insight?
4. CONTEXT — Do you show awareness of the passage's context?`

export default function AssessmentView({ user_id = 'default', onBack }) {
  const [mode, setMode] = useState('intro')   // intro | quiz | open | complete
  const [questions, setQuestions] = useState([])
  const [qIdx, setQIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [openInput, setOpenInput] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [results, setResults] = useState({ correct: 0, total: 0 })
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [tier, setTier] = useState('')
  const [llmGrade, setLlmGrade] = useState(null)
  const [showRubric, setShowRubric] = useState(false)

  const question = questions[qIdx] || null
  const isOpen = question?.type === 'open' || mode === 'open'

  // Fetch quiz questions (adaptive — prioritizes unseen/low-accuracy questions)
  const fetchQuiz = useCallback(async (t = '') => {
    setLoading(true); setError(null); setMode('quiz')
    try {
      const r = await fetch(`/api/v1/quiz?tier=${t}&count=10&user_id=${user_id}`)
      const d = await r.json()
      if (!d.ok) throw new Error(d.detail || 'Failed to load')
      if (d.data.questions.length === 0) throw new Error('No questions for this tier')
      setQuestions(d.data.questions)
      setQIdx(0); setSelected(null); setSubmitted(false)
    } catch (e) { setError(e.message); setMode('intro') }
    setLoading(false)
  }, [user_id])

  const submitMC = async () => {
    if (selected === null || !question) return
    setSubmitted(true)
    const correct = selected === question.correct_answer || String(selected) === String(question.correct_answer)
    setResults(p => ({ correct: p.correct + (correct ? 1 : 0), total: p.total + 1 }))
    setHistory(p => [...p, {
      q: question.question.slice(0, 100),
      correct,
      tier: question.tier,
      bloom: question.bloom_level,
    }])
    // Record answer for adaptive progress tracking
    try {
      await fetch('/api/v1/quiz/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id,
          question_id: question.question_id,
          correct,
        }),
      })
    } catch {}
    setTimeout(() => nextQuestion(), 1500)
  }

  const submitOpen = async () => {
    if (!openInput.trim() || !question) return
    setSubmitted(true); setLlmGrade(null)
    setResults(p => ({ ...p, total: p.total + 1 }))

    try {
      const r = await fetch('/api/v1/assess/grade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question.question,
          user_answer: openInput,
          tier: question.tier || 'text',
        }),
      })
      const d = await r.json()
      if (d.ok) setLlmGrade(d.data?.grading)
    } catch {}
  }

  const nextQuestion = () => {
    if (qIdx + 1 < questions.length) {
      setQIdx(p => p + 1); setSelected(null); setSubmitted(false); setOpenInput(''); setLlmGrade(null)
    } else {
      setMode('complete')
    }
  }

  const renderQuestion = () => {
    if (!question) return null
    const tierMeta = TIER_META[question.tier] || TIER_META.text

    return (
      <div className="p-5 rounded-xl border-2 border-indigo-200 dark:border-indigo-800 bg-white dark:bg-neutral-800">
        {/* Header */}
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
            {question.type?.replace('_', ' ') || 'Question'}
          </span>
          {question.tier && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${tierMeta.color}`}>
              {tierMeta.icon} {tierMeta.label}
            </span>
          )}
          {question.bloom_level && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-500">
              {question.bloom_level}
            </span>
          )}
        </div>

        {/* Question text */}
        <div className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-4 whitespace-pre-wrap font-medium">
          {question.question}
        </div>

        {isOpen ? (
          /* Open-ended mode */
          <div>
            {!submitted && (
              <button onClick={() => setShowRubric(!showRubric)}
                className="text-[10px] text-indigo-500 hover:underline mb-2 cursor-pointer">
                {showRubric ? 'Hide' : 'Show'} grading rubric
              </button>
            )}
            {showRubric && !submitted && (
              <div className="mb-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/30 text-[10px] text-neutral-500 dark:text-neutral-400 whitespace-pre-wrap border border-neutral-200 dark:border-neutral-700">
                {OPEN_RUBRIC}
              </div>
            )}
            <textarea
              value={openInput}
              onChange={e => setOpenInput(e.target.value)}
              disabled={submitted}
              rows={5}
              placeholder="Write your analysis here… Reference specific words, phrases, and connections."
              className="w-full px-3 py-2.5 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900 text-neutral-800 dark:text-neutral-200 focus:border-indigo-400 outline-none transition-all resize-y disabled:opacity-50"
            />
            {llmGrade && (
              <div className="mt-3 p-4 rounded-lg bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">LLM Evaluation</p>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {['text_engagement', 'reasoning', 'depth', 'context'].map(k => {
                    const score = llmGrade?.scores?.[k] || llmGrade?.[k]
                    if (score === undefined) return null
                    const pct = (score / 10) * 100
                    return (
                      <div key={k}>
                        <div className="text-[9px] text-neutral-400 capitalize mb-0.5">{k.replace('_', ' ')}</div>
                        <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                          <div className="h-full rounded-full bg-indigo-500" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="text-[10px] font-mono text-neutral-500">{score}/10</span>
                      </div>
                    )
                  })}
                </div>
                {llmGrade.feedback && (
                  <p className="text-xs text-neutral-600 dark:text-neutral-400">{llmGrade.feedback}</p>
                )}
                {llmGrade.strengths && llmGrade.strengths.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[9px] font-medium text-green-600 dark:text-green-400">Strengths:</p>
                    {llmGrade.strengths.map((s, i) => <p key={i} className="text-[10px] text-green-600 dark:text-green-400">✅ {s}</p>)}
                  </div>
                )}
                {llmGrade.areas_for_growth && llmGrade.areas_for_growth.length > 0 && (
                  <div className="mt-1">
                    <p className="text-[9px] font-medium text-amber-600 dark:text-amber-400">Growth areas:</p>
                    {llmGrade.areas_for_growth.map((s, i) => <p key={i} className="text-[10px] text-amber-600 dark:text-amber-400">💡 {s}</p>)}
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          /* Multiple choice options */
          <div className="space-y-1.5">
            {(question.options || []).map((opt, i) => {
              const isCorrect = String(opt) === String(question.correct_answer)
              const isSelected = selected === opt || selected === i
              let cls = 'w-full text-left px-3 py-2.5 rounded-lg text-sm border transition-all cursor-pointer '
              if (!submitted) {
                cls += isSelected
                  ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                  : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
              } else {
                cls += isCorrect
                  ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                  : isSelected
                    ? 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                    : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
              }
              return (
                <button key={i} onClick={() => { if (!submitted) setSelected(opt) }} className={cls}>
                  <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + i)}.</span>
                  <span>{opt}</span>
                </button>
              )
            })}
          </div>
        )}

        {/* Submit/Next */}
        {!submitted ? (
          isOpen ? (
            <button onClick={submitOpen} disabled={!openInput.trim()}
              className="mt-4 w-full py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-700 text-white">
              Submit for Evaluation
            </button>
          ) : (
            <button onClick={submitMC} disabled={selected === null}
              className="mt-4 w-full py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-700 text-white">
              Submit Answer
            </button>
          )
        ) : (
          <div className="mt-3 text-center">
            {!isOpen && (
              <p className={`text-xs font-medium mb-2 ${selected === question.correct_answer || String(selected) === String(question.correct_answer) ? 'text-green-600' : 'text-red-500'}`}>
                {selected === question.correct_answer || String(selected) === String(question.correct_answer) ? '✓ Correct!' : `✗ The answer was: ${question.correct_answer}`}
              </p>
            )}
            <button onClick={nextQuestion}
              className="px-4 py-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 text-sm font-medium cursor-pointer transition-colors hover:bg-indigo-200 dark:hover:bg-indigo-900/50">
              {qIdx + 1 < questions.length ? 'Next Question →' : 'See Results →'}
            </button>
          </div>
        )}
      </div>
    )
  }

  if (mode === 'intro') return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-6 cursor-pointer">← Back</button>
      <div className="text-center">
        <span className="text-4xl block mb-4">✍️</span>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Scripture Knowledge</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6 max-w-md mx-auto">
          Questions that show passage text and test understanding — not memorization.
        </p>

        {/* Tier selector */}
        <div className="space-y-2 max-w-xs mx-auto mb-4">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Choose question type:</p>
          {TIER_OPTIONS.map(t => (
            <button key={t.id} onClick={() => { setTier(t.id); fetchQuiz(t.id) }}
              className="w-full py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-sm font-medium cursor-pointer transition-colors flex items-center justify-center gap-2">
              <span>{t.icon}</span> {t.label}
            </button>
          ))}
        </div>

        <button onClick={() => {
          setMode('open')
          setQuestions([{
            type: 'open', tier: 'analysis', bloom_level: 'analyze',
            question: `**Exodus 12:1-13** describes the Passover — the blood of a lamb saves Israel from death.\n\n**Isaiah 53:4-7** describes a suffering servant who is "led as a lamb to the slaughter."\n\n**John 1:29** calls Jesus "the Lamb of God who takes away the sin of the world."\n\n**1 Corinthians 5:7** says "Christ our Passover is sacrificed for us."\n\nWhat do these passages reveal together? How does the lamb metaphor develop across the Old and New Testaments?`,
            options: [],
            correct_answer: '',
          }])
        }}
          className="mt-4 w-full py-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-sm font-medium cursor-pointer transition-colors">
          🖊️ Try Open Response (LLM Graded)
        </button>

        {error && <p className="text-sm text-red-500 mt-4">{error}</p>}
      </div>
    </div>
  )

  if (loading) return (
    <div className="max-w-2xl mx-auto px-6 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
      <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
    </div>
  )

  if (mode === 'complete') return (
    <div className="max-w-2xl mx-auto px-6 py-8 text-center">
      <span className="text-4xl block mb-4">🎉</span>
      <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Session Complete</h2>
      <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mb-4">{results.correct}/{results.total} correct</p>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">{results.correct === results.total ? 'Great work!' : results.correct >= results.total * 0.7 ? 'Good understanding!' : 'Keep studying!'}</p>
      {history.length > 0 && (
        <div className="space-y-1 max-w-xs mx-auto mb-6">
          {history.map((h, i) => (
            <div key={i} className={`p-2 rounded-lg text-xs text-left ${h.correct ? 'bg-green-50 dark:bg-green-900/20 text-green-700' : 'bg-red-50 dark:bg-red-900/20 text-red-700'}`}>
              <span>{h.correct ? '✓' : '✗'}</span> {h.tier && <span className="text-[9px] opacity-60">[{h.tier}]</span>} {h.q}...
            </div>
          ))}
        </div>
      )}
      <div className="flex gap-2 justify-center">
        <button onClick={onBack} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium cursor-pointer">Done</button>
        <button onClick={() => { setMode('intro'); setResults({ correct: 0, total: 0 }); setHistory([]) }}
          className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 text-sm font-medium cursor-pointer">Try Again</button>
      </div>
    </div>
  )

  if (!question) return (
    <div className="max-w-2xl mx-auto px-6 py-8 text-center text-sm text-neutral-500">
      No questions available. <button onClick={() => setMode('intro')} className="text-indigo-500 underline cursor-pointer">Back</button>
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <button onClick={() => setMode('intro')} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">← Back</button>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">
            {mode === 'open' ? 'Open Response' : 'Scripture Quiz'}
          </h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Question {qIdx + 1}/{questions.length}
          </p>
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

      {renderQuestion()}
    </div>
  )
}
