import { useEffect, useState } from 'react'
import { currentSessionToken } from '../api'
import { submitHebrewProgressDetailed } from './HebrewQuiz'

/**
 * GuidedLessonView — weakest-topic lesson grounded in the learner's knowledge
 * state. Explanation + examples render first; drills grade through the
 * existing /hebrew/progress FSRS path (curriculum drills) or client-side
 * (LLM checks, practice-only, no schedule mutation).
 */
export default function GuidedLessonView({ nodeId, onBack, onOpenLesson }) {
  const [lesson, setLesson] = useState(null)
  const [error, setError] = useState('')
  const [picked, setPicked] = useState({})
  const [results, setResults] = useState({})

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const token = currentSessionToken()
        const r = await fetch('/api/v1/hebrew/guided-lesson', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ user_id: 'default', session_token: token, node_id: nodeId || '' }),
        })
        const d = await r.json()
        if (!cancelled) {
          if (d.ok) setLesson(d.data)
          else setError('Could not build a lesson right now.')
        }
      } catch {
        if (!cancelled) setError('Could not build a lesson right now.')
      }
    }
    load()
    return () => { cancelled = true }
  }, [nodeId])

  const answerDrill = async (idx, drill, optIdx) => {
    if (results[idx] !== undefined) return
    setPicked(prev => ({ ...prev, [idx]: optIdx }))
    if (drill.id == null) {
      // LLM check — client-side only, no schedule mutation.
      setResults(prev => ({ ...prev, [idx]: optIdx === drill.answer_index }))
      return
    }
    const res = await submitHebrewProgressDetailed({
      node_id: drill.node_id,
      user_id: 'default',
      session_token: currentSessionToken(),
      question_id: drill.id,
      answer: drill.options?.[optIdx] ?? '',
    })
    setResults(prev => ({ ...prev, [idx]: res ? !!res.correct : null }))
    if (res) {
      setResults(prev => ({ ...prev, [idx]: !!res.correct }))
      drill._feedback = res
    }
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        <p className="text-sm text-neutral-500 mt-4">{error}</p>
      </div>
    )
  }
  if (!lesson) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        <p className="text-sm text-neutral-500 mt-4">Building your lesson…</p>
      </div>
    )
  }
  if (!lesson.topic) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        <p className="text-sm text-neutral-600 dark:text-neutral-300 mt-4">
          🔒 Grammar unlocks as you master the basics — keep reviewing and this lesson builds itself.
        </p>
      </div>
    )
  }
  const t = lesson.topic
  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📖 {t.title}</h2>
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
      </div>
      <div className="text-[11px] text-neutral-400 mb-3">
        {t.category} · Level {t.level} · {lesson.source === 'llm' ? 'personalized' : 'curriculum'}
        {lesson.knowledge_used?.known_words > 0 && ` · uses ${lesson.knowledge_used.known_words} words you know`}
      </div>
      <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed mb-4">{lesson.explanation}</p>
      {(lesson.key_points || []).length > 0 && (
        <ul className="list-disc ml-5 mb-4 text-sm text-neutral-700 dark:text-neutral-300 space-y-1">
          {lesson.key_points.map((k, i) => <li key={i}>{k}</li>)}
        </ul>
      )}
      {(lesson.examples || []).length > 0 && (
        <div className="space-y-2 mb-5">
          {lesson.examples.map((e, i) => (
            <div key={i} className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-800/60 border border-neutral-200 dark:border-neutral-700">
              <span className="font-serif text-lg" dir="rtl" lang="he">{e.hebrew}</span>
              <span className="text-sm text-neutral-500 ml-2">— {e.gloss}</span>
              {e.note && <div className="text-xs text-neutral-400 mt-1">{e.note}</div>}
            </div>
          ))}
        </div>
      )}
      {(lesson.drills || []).length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">Check yourself</h3>
          {lesson.drills.map((d, di) => (
            <div key={d.id ?? `llm-${di}`} className="p-3 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
              <div className="text-sm mb-2">{d.question_text}</div>
              <div className="grid gap-1.5">
                {(d.options || []).map((opt, oi) => {
                  const isPicked = picked[di] === oi
                  const done = results[di] !== undefined && results[di] !== null
                  const isRight = d.id == null ? oi === d.answer_index : (done && isPicked && results[di])
                  return (
                    <button key={oi} disabled={done} onClick={() => answerDrill(di, d, oi)}
                      className={`text-left px-3 py-1.5 rounded-lg text-sm border transition-colors cursor-pointer disabled:cursor-default ${
                        done && isRight
                          ? 'bg-green-100 dark:bg-green-900/30 border-green-400'
                          : done && isPicked
                            ? 'bg-red-100 dark:bg-red-900/30 border-red-400'
                            : 'border-neutral-200 dark:border-neutral-700 hover:border-indigo-400'}`}>
                      {opt}
                    </button>
                  )
                })}
              </div>
              {results[di] !== undefined && results[di] !== null && (
                <div className="text-xs mt-2 text-neutral-500">
                  {results[di] ? '✓ Correct' : '✗ Not quite'}
                  {d.id == null && d.why ? ` — ${d.why}` : ''}
                  {d._feedback?.explanation ? ` — ${d._feedback.explanation}` : ''}
                  {d.id == null ? ' (practice only)' : ''}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      <button onClick={() => onOpenLesson?.(t.node_id)}
        className="mt-5 text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
        Full lesson →
      </button>
    </div>
  )
}
