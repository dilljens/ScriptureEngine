import React, { useState, useEffect } from 'react'

/**
 * HebrewDiagnostic — pre-assessment before entering the Hebrew curriculum.
 * Shows questions from all categories and applies placement credit only to
 * the specific skills the learner demonstrates.
 */

export default function HebrewDiagnostic({ onComplete, user_id = 'default' }) {
  const [questions, setQuestions] = useState([])
  const [categories, setCategories] = useState([])
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [phase, setPhase] = useState('intro') // intro | quiz | results
  const [diagnosticResults, setDiagnosticResults] = useState(null)
  const [batchId, setBatchId] = useState(null)

  useEffect(() => {
    fetch(`/api/v1/hebrew/diagnostic?user_id=${user_id}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          setQuestions(d.data?.questions || [])
          setCategories(d.data?.categories || [])
          setBatchId(d.data?.batch_id || null)
        } else setError(d.detail || 'Failed to load')
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [user_id])

  // Build a mapping of node_id → category from the categories response
  const nodeToCategory = {}
  categories.forEach(cat => {
    ;(cat.node_ids || []).forEach(nid => {
      nodeToCategory[nid] = cat.category
    })
  })

  const handleSubmitAll = async () => {
    try {
      const response = await fetch('/api/v1/hebrew/diagnostic/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id,
          batch_id: batchId,
          answers: questions.map((question, index) => ({
            question_id: question.question_id,
            node_id: question.node_id,
            answer: answers[index],
          })),
        }),
      })
      const data = await response.json()
      if (!data.ok) throw new Error(data.detail || 'Failed to grade diagnostic')
      setDiagnosticResults(data.data)
      setPhase('results')
    } catch (e) {
      setError(e.message)
    }
  }

  if (loading) return (
    <div className="max-w-2xl mx-auto px-6 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
      {[1,2,3,4,5].map(i => <div key={i} className="h-20 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
    </div>
  )

  if (error) return (
    <div className="max-w-2xl mx-auto px-6 py-8 text-center">
      <p className="text-sm text-red-600 dark:text-red-400 mb-4">{error}</p>
      <button onClick={onComplete} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium cursor-pointer">Skip diagnostic →</button>
    </div>
  )

  if (phase === 'intro') return (
    <div className="max-w-2xl mx-auto px-6 py-8 text-center">
      <span className="text-4xl block mb-4">📋</span>
      <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Hebrew Knowledge Check</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6 max-w-md mx-auto">
        Let's see what you already know. Answer {questions.length} quick questions across all topics.
        Placement credit is limited to the exact skills you demonstrate, so untested material stays available.
      </p>
      <button onClick={() => setPhase('quiz')}
        className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium cursor-pointer transition-colors">
        Start ({questions.length} questions)
      </button>
      <button onClick={onComplete}
        className="block mx-auto mt-3 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">
        Skip diagnostic
      </button>
    </div>
  )

  if (phase === 'results') {
    const catResults = diagnosticResults?.results || {}
    const totalCorrect = diagnosticResults?.correct || 0
    const total = diagnosticResults?.total || questions.length

    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="text-center mb-6">
          <span className="text-4xl block mb-4">{totalCorrect === total ? '🎉' : '📊'}</span>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Results</h2>
          <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400 mb-2">{totalCorrect}/{total} correct</p>
          {totalCorrect === total ? (
            <p className="text-sm text-green-600 dark:text-green-400 mb-2">Perfect score! You know this material well.</p>
          ) : totalCorrect >= total * 0.6 ? (
            <p className="text-sm text-amber-600 dark:text-amber-400 mb-2">Good foundation! You'll review the areas you missed.</p>
          ) : (
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-2">You'll start from the beginning to build a strong foundation.</p>
          )}
        </div>

        {/* Per-category breakdown */}
        <div className="space-y-2 mb-6">
          {Object.entries(catResults).map(([cat, stats]) => (
            <div key={cat} className="flex items-center justify-between p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
              <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300 capitalize">{cat}</span>
              <span className={`text-sm font-bold ${
                stats.correct === stats.total ? 'text-green-600 dark:text-green-400' :
                stats.correct >= stats.total * 0.6 ? 'text-amber-600 dark:text-amber-400' :
                'text-neutral-500 dark:text-neutral-400'
              }`}>
                {stats.correct}/{stats.total}
                {stats.correct === stats.total ? ' ✅ Demonstrated' : stats.correct > 0 ? ' ⚡ Developing' : ' 📚 Review'}
              </span>
            </div>
          ))}
        </div>

        <button onClick={onComplete}
          className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium cursor-pointer transition-colors">
          Start Learning
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">Knowledge Check</h2>
        <span className="text-xs text-neutral-400 dark:text-neutral-500">
          {Object.keys(answers).length}/{questions.length} answered
        </span>
      </div>

      <div className="space-y-4">
        {questions.map((q, i) => {
          const isAnswered = answers[i] !== undefined && answers[i] !== null
          const opts = q.options || []
          const isProduction = q.question_type === 'typing' || q.question_type === 'transliteration' || q.question_type === 'recall' || q.question_type === 'cloze'

          return (
            <div key={i} className="p-4 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[9px] font-mono text-neutral-400 w-6">Q{i+1}</span>
                {q.question_type && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-500">
                    {q.question_type.replace('_', ' ')}
                  </span>
                )}
                {q.node_id && nodeToCategory[q.node_id] && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">
                    {nodeToCategory[q.node_id]}
                  </span>
                )}
              </div>
              <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-3">{q.question}</p>

              {isProduction ? (
                /* Production type — text input for diagnostic */
                <input
                  type="text"
                  value={answers[i] || ''}
                  onChange={(e) => setAnswers(prev => ({ ...prev, [i]: e.target.value }))}
                  placeholder={q.question_type === 'typing' ? 'Type Hebrew character...' :
                              q.question_type === 'transliteration' ? 'Type transliteration...' :
                              'Type your answer...'}
                  className="w-full px-3 py-2 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 focus:border-indigo-400 outline-none transition-all"
                  dir={q.question_type === 'typing' ? 'rtl' : 'ltr'}
                  style={q.question_type === 'typing' ? { fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif", fontSize: '1.25rem' } : {}}
                />
              ) : (
                /* Choice type — options as buttons */
                <div className="space-y-1">
                  {opts.map((opt, oi) => {
                    const sel = answers[i] === opt || answers[i] === oi
                    return (
                      <button key={oi} onClick={() => setAnswers(prev => ({ ...prev, [i]: opt }))}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition-all cursor-pointer
                          ${sel
                            ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                            : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/30 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'}`}>
                        <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + oi)}.</span>
                        {opt}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button onClick={handleSubmitAll}
        disabled={Object.keys(answers).length < questions.length}
        className="mt-6 w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium cursor-pointer transition-colors">
        See Results ({Object.keys(answers).length}/{questions.length} answered)
      </button>
    </div>
  )
}
