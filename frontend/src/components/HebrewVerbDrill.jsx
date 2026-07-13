import React, { useState, useEffect, useCallback } from 'react'
import { preprocess, createComponents } from '../lib/scripture-markdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

/**
 * HebrewVerbDrill — interactive verb conjugation drills.
 *
 * Fetches drill questions from /api/v1/hebrew/verb-drill and presents
 * them as multiple-choice. Tracks correct/incorrect and shows explanations.
 */
const CATEGORIES = [
  { id: 'qal', label: 'Qal', icon: 'ק' },
  { id: 'niphal', label: 'Niphal', icon: 'נ' },
  { id: 'piel', label: 'Piel', icon: 'פ' },
  { id: 'hiphil', label: 'Hiphil', icon: 'ה' },
  { id: 'weak_verbs', label: 'Weak Verbs', icon: 'ח' },
  { id: 'all', label: 'All Binyanim', icon: 'כ' },
]

export default function HebrewVerbDrill({ onNavigate }) {
  const [drills, setDrills] = useState([])
  const [qIdx, setQIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [score, setScore] = useState({ correct: 0, total: 0 })
  const [category, setCategory] = useState('all')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  const loadDrills = useCallback(async (cat) => {
    setLoading(true)
    setQIdx(0)
    setSelected(null)
    setSubmitted(false)
    setDone(false)
    setScore({ correct: 0, total: 0 })
    try {
      const r = await fetch(`/api/v1/hebrew/verb-drill?category=${cat}&limit=8`)
      const d = await r.json()
      if (d.ok) setDrills(d.data.drills || [])
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { loadDrills(category) }, [category, loadDrills])

  const current = drills[qIdx]

  const handleSelect = (opt) => {
    if (submitted) return
    setSelected(opt)
  }

  const handleSubmit = () => {
    if (selected === null) return
    setSubmitted(true)
    const isCorrect = String(selected) === String(current?.correct)
    setScore(prev => ({ correct: prev.correct + (isCorrect ? 1 : 0), total: prev.total + 1 }))
  }

  const handleNext = () => {
    if (qIdx + 1 < drills.length) {
      setQIdx(p => p + 1)
      setSelected(null)
      setSubmitted(false)
    } else {
      setDone(true)
    }
  }

  const isOpen = current?.type === 'open' || !current?.options

  // Score display
  if (done) {
    const pct = score.total > 0 ? Math.round((score.correct / score.total) * 100) : 0
    return (
      <div className="max-w-2xl mx-auto px-4 py-8 text-center">
        <span className="text-4xl block mb-4">{pct >= 80 ? '🎉' : pct >= 50 ? '👍' : '📚'}</span>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Drill Complete</h2>
        <div className="text-3xl font-bold text-blue-600 dark:text-blue-400 mb-2">{score.correct}/{score.total}</div>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">{pct}% correct</p>
        <div className="w-48 h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 mx-auto overflow-hidden mb-6">
          <div className="h-full rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex gap-2 justify-center">
          <button onClick={() => { loadDrills(category) }}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium cursor-pointer hover:bg-blue-700 transition-colors">
            Try Again
          </button>
          <button onClick={() => setCategory(category === 'all' ? 'qal' : 'all')}
            className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 text-sm font-medium cursor-pointer hover:bg-neutral-300 dark:hover:bg-neutral-600 transition-colors">
            Switch Category
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-1">Hebrew Verb Drills</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">Practice binyan recognition and conjugation</p>

      {/* Category selector */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {CATEGORIES.map(c => (
          <button key={c.id} onClick={() => setCategory(c.id)}
            className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors cursor-pointer ${
              category === c.id
                ? 'bg-indigo-600 text-white'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
            }`}>
            {c.icon} {c.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="animate-pulse p-8 text-center text-sm text-neutral-400">Loading drills…</div>
      ) : !current ? (
        <div className="p-8 text-center text-sm text-neutral-400">No drills available for this category.</div>
      ) : (
        <div className="p-5 rounded-xl border-2 border-indigo-200 dark:border-indigo-800 bg-white dark:bg-neutral-800">
          {/* Progress */}
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] text-neutral-400 font-mono">
              {score.correct}/{score.total} correct
            </span>
            <span className="text-[10px] text-neutral-400 font-mono">{qIdx + 1}/{drills.length}</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mb-4">
            <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(qIdx / drills.length) * 100}%` }} />
          </div>

          {/* Verb badge */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-base font-bold text-indigo-600 dark:text-indigo-400 font-hebrew">
              {current.node_id}
            </span>
            {current.type && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 font-medium uppercase">
                {current.type.replace('_', ' ')}
              </span>
            )}
          </div>

          {/* Question */}
          <div className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-4">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={createComponents()}>
              {preprocess(current.question || '')}
            </ReactMarkdown>
          </div>

          {/* Options */}
          {!isOpen && (
            <div className="space-y-1.5">
              {(JSON.parse(current.options || '[]')).map((opt, i) => {
                const isCorrect = String(opt) === String(current.correct)
                const isSelected = selected === opt || selected === i
                let cls = 'w-full text-left px-3 py-2.5 rounded-lg text-sm border transition-all cursor-pointer '
                if (!submitted) {
                  cls += isSelected
                    ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300'
                } else {
                  cls += isCorrect
                    ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                    : isSelected
                      ? 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                      : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500'
                }
                return (
                  <button key={i} onClick={() => handleSelect(opt)} className={cls}>
                    <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + i)}.</span>
                    {opt}
                  </button>
                )
              })}
            </div>
          )}

          {/* Submit button */}
          {!submitted && !isOpen && (
            <button onClick={handleSubmit} disabled={selected === null}
              className="mt-4 w-full py-2.5 rounded-lg text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
              Submit
            </button>
          )}

          {/* After submission */}
          {submitted && (
            <div className="mt-3">
              <p className={`text-xs text-center font-medium mb-2 ${String(selected) === String(current?.correct) ? 'text-green-600' : 'text-red-600'}`}>
                {String(selected) === String(current?.correct) ? '✓ Correct!' : `✗ Incorrect — ${current.correct}`}
              </p>
              {current.explanation && (
                <div className="p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 text-xs text-neutral-700 dark:text-neutral-300 leading-relaxed">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={createComponents()}>
                    {preprocess(current.explanation)}
                  </ReactMarkdown>
                </div>
              )}
              <button onClick={handleNext}
                className="mt-3 w-full py-2.5 rounded-lg text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer transition-colors">
                {qIdx + 1 < drills.length ? 'Next Question →' : 'See Results'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
