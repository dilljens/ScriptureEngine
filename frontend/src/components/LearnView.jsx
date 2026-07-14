import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { preprocess, createComponents } from '../lib/scripture-markdown'
import CardQueue from './CardQueue'
import { lessonToCards } from '../lib/card-factory'

/**
 * LearnView — structured learning modules following The Math Academy Way.
 *
 * Shows modules as a curriculum grid with subject picker. Each module has:
 *  1. Direct instruction (lesson content + wiki articles)
 *  2. Worked examples (real verse connections)
 *  3. Practice questions (adaptive — weakest first)
 *  4. Mastery tracking (FSRS-based review scheduling)
 */

const SUBJECTS = [
  { id: 'all', label: 'All Subjects', icon: '📚' },
  { id: 'covenant', label: 'Covenants', icon: '🤝' },
  { id: 'temple', label: 'Temple', icon: '🏛️' },
  { id: 'atonement', label: 'Atonement', icon: '🕊️' },
  { id: 'exodus', label: 'Exodus', icon: '🌊' },
  { id: 'wisdom', label: 'Wisdom', icon: '📜' },
  { id: 'zion', label: 'Zion', icon: '🏔️' },
  { id: 'faith', label: 'Faith', icon: '🔥' },
  { id: 'prayer', label: 'Prayer', icon: '🙏' },
  { id: 'grace', label: 'Grace', icon: '✨' },
]

export default function LearnView({ userId = 'default', onBack }) {
  const [modules, setModules] = useState([])
  const [currentModule, setCurrentModule] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [qIdx, setQIdx] = useState(0)
  const [selected, setSelected] = useState(null)
  const [openInput, setOpenInput] = useState('')
  const [llmGrade, setLlmGrade] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [showNext, setShowNext] = useState(false)
  const [showLesson, setShowLesson] = useState(true)
  const [phase, setPhase] = useState('list')
  const [subjectFilter, setSubjectFilter] = useState('all')
  const [practiceCards, setPracticeCards] = useState([])
  const [answerState, setAnswerState] = useState({})

  const loadModules = async () => {
    setLoading(true)
    try {
      const r = await fetch(`/api/v1/learn/modules?user_id=${userId}`)
      const d = await r.json()
      if (d.ok) setModules(d.data.modules)
      else setError(d.detail)
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  const loadModule = async (id) => {
    setLoading(true); setQIdx(0); setSelected(null); setSubmitted(false); setShowNext(false); setShowLesson(true); setOpenInput(''); setLlmGrade(null)
    try {
      const r = await fetch(`/api/v1/learn/modules/${id}?user_id=${userId}`)
      const d = await r.json()
      if (d.ok) { setCurrentModule(d.data); setPhase('lesson') }
      else setError(d.detail)
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  const advanceToNext = () => {
    if (qIdx + 1 < currentModule.questions.length) {
      setQIdx(p => p + 1); setSelected(null); setSubmitted(false); setShowNext(false); setOpenInput(''); setLlmGrade(null)
    } else {
      setPhase('complete')
    }
  }

  const submitAnswer = async (correct) => {
    if (!currentModule) return
    const q = currentModule.questions[qIdx]
    setSubmitted(true)
    // Record answer
    await fetch(`/api/v1/learn/modules/${currentModule.id}/practice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, question_id: q.id, correct }),
    })
    setShowNext(true)
  }

  const submitOpenAnswer = async () => {
    if (!openInput.trim() || !currentModule) return
    const q = currentModule.questions[qIdx]
    setSubmitted(true); setLlmGrade(null)
    // Record as neutral for now (LLM will evaluate)
    await fetch(`/api/v1/learn/modules/${currentModule.id}/practice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, question_id: q.id, correct: true }),
    })
    // Call LLM grading
    try {
      const r = await fetch('/api/v1/assess/grade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q.question,
          user_answer: openInput,
          tier: q.tier || 'analysis',
          user_id: userId,
        }),
      })
      const d = await r.json()
      if (d.ok) setLlmGrade(d.data?.grading)
    } catch {}
    setShowNext(true)
  }

  useEffect(() => { loadModules() }, [userId])

  // ── Module list view ──
  if (phase === 'list') {
    const filtered = subjectFilter === 'all' 
      ? modules 
      : modules.filter(m => m.id.includes(subjectFilter) || m.title.toLowerCase().includes(subjectFilter))

    return (
      <div className="max-w-4xl mx-auto px-4 py-6">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Learn Scripture</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
          Choose a subject or let the AI pick for you.
        </p>

        {/* Subject filter chips + Surprise Me */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {SUBJECTS.map(s => (
            <button key={s.id} onClick={() => setSubjectFilter(s.id)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors cursor-pointer ${
                subjectFilter === s.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
              }`}>
              {s.icon} {s.label}
            </button>
          ))}
          <button onClick={() => {
            const available = modules.filter(m => m.status !== 'mastered')
            if (available.length > 0) {
              const pick = available[Math.floor(Math.random() * available.length)]
              loadModule(pick.id)
            }
          }}
            className="px-3 py-1 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-[10px] font-medium cursor-pointer hover:bg-amber-200 dark:hover:bg-amber-900/50 transition-colors">
            🎲 Surprise Me
          </button>
        </div>

        {loading ? (
          <div className="animate-pulse space-y-3">
            {[1,2,3,4].map(i => <div key={i} className="h-20 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-sm text-neutral-400">No modules match this filter.</div>
        ) : (
          <div className="space-y-2">
            {filtered.map(m => (
              <button key={m.id} onClick={() => loadModule(m.id)}
                className={`w-full text-left p-4 rounded-xl border transition-all cursor-pointer ${
                  m.status === 'mastered'
                    ? 'border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/10'
                    : m.status === 'learning'
                    ? 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/10'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-600'
                }`}>
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{m.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{m.title}</span>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-500">Lv.{m.difficulty}</span>
                      {m.status === 'mastered' && <span className="text-[10px] text-green-600">✓ Mastered</span>}
                    </div>
                    <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-1">{m.description}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono text-neutral-400">{m.question_count} questions</span>
                    <div className="w-14 h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 mt-1 overflow-hidden">
                      <div className={`h-full rounded-full ${m.mastery >= 0.8 ? 'bg-green-500' : 'bg-amber-500'}`}
                        style={{ width: `${Math.round(m.mastery * 100)}%` }} />
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Lesson view ──
  if (phase === 'lesson' && currentModule) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-6">
        <button onClick={() => setPhase('list')} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">
          ← All Modules
        </button>

        {/* Lesson content */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">{currentModule.icon}</span>
            <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{currentModule.title}</h2>
          </div>
          <div className="prose prose-sm dark:prose-invert max-w-none
            prose-headings:text-neutral-800 dark:prose-headings:text-neutral-200
            prose-a:text-blue-600 dark:prose-a:text-blue-400
            prose-strong:text-neutral-800 dark:prose-strong:text-neutral-200
            prose-code:text-[11px] prose-code:bg-neutral-100 dark:prose-code:bg-neutral-800 prose-code:px-1 prose-code:rounded
            p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700 max-h-80 overflow-y-auto">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={createComponents()}>
              {preprocess(currentModule.lesson_content || '')}
            </ReactMarkdown>
          </div>
        </div>

        {/* Worked examples */}
        {currentModule.worked_examples?.length > 0 && (
          <div className="mb-6">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-3">Examples in Scripture</h3>
            <div className="space-y-2">
              {currentModule.worked_examples.map((ex, i) => (
                <div key={i} className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-200 dark:border-indigo-800">
                  <p className="text-[10px] font-medium text-indigo-600 dark:text-indigo-400 mb-1">{ex.title}</p>
                  {ex.verse && <button onClick={() => { const p = ex.verse.split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}})) }}
  className="text-[10px] font-mono text-indigo-400 mb-1 hover:text-indigo-600 dark:hover:text-indigo-200 cursor-pointer transition-colors">{ex.verse}</button>}
                  {ex.text && <p className="text-xs text-neutral-600 dark:text-neutral-400 italic">"{ex.text}"</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Related wiki articles */}
        {currentModule.related_wiki && (
          <div className="mb-6 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-2">📖 Related Wiki Articles</h3>
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={createComponents()}>
                {preprocess(currentModule.related_wiki || '')}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Start practice — flashcard mode */}
        {currentModule.questions?.length > 0 && (
          <button onClick={() => {
            setPracticeCards(lessonToCards(currentModule))
            setAnswerState({})
            setPhase('practice')
          }}
            className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
            Start Practice ({currentModule.questions.length} questions)
          </button>
        )}
      </div>
    )
  }

  // ── Practice mode — flashcard via CardQueue ──
  if (phase === 'practice' && currentModule) {
    const handleRate = async (card, rating) => {
      // For MC questions, the correct/incorrect is based on the stored answer
      const isCorrect = rating >= 3
      await fetch(`/api/v1/learn/modules/${currentModule.id}/practice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          question_id: card.data?.question_id || card.id,
          correct: isCorrect,
        }),
      })
    }

    const handleAnswer = async (card, answer) => {
      const q = currentModule.questions.find(q => q.id === card.data?.question_id)
      if (!q?.is_open || !answer?.openInput?.trim()) return

      // For open-ended: record + call LLM grading
      await fetch(`/api/v1/learn/modules/${currentModule.id}/practice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, question_id: q.id, correct: true }),
      })

      try {
        const r = await fetch('/api/v1/assess/grade', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: q.question,
            user_answer: answer.openInput,
            tier: q.tier || 'analysis',
            user_id: userId,
          }),
        })
        const d = await r.json()
        if (d.ok) setAnswerState(prev => ({ ...prev, [card.id]: { llmGrade: d.data?.grading } }))
      } catch {}
    }

    // After CardQueue completes, show the completion screen
    if (practiceCards.length === 0) {
      return (
        <div className="max-w-3xl mx-auto px-4 py-8 text-center">
          <span className="text-4xl block mb-4">🎉</span>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Module Complete!</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
            You've completed the practice for this module. Keep reviewing to strengthen your understanding.
          </p>
          <div className="flex gap-2 justify-center">
            <button onClick={() => { setPhase('list'); setCurrentModule(null); setPracticeCards([]) }}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium cursor-pointer hover:bg-indigo-700 transition-colors">
              Back to Modules
            </button>
            <button onClick={() => {
              setPracticeCards(lessonToCards(currentModule))
              setAnswerState({})
            }}
              className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 text-sm font-medium cursor-pointer hover:bg-neutral-300 dark:hover:bg-neutral-600 transition-colors">
              Review Again
            </button>
          </div>
        </div>
      )
    }

    return (
      <div>
        <div className="max-w-3xl mx-auto px-4 pt-2">
          <button onClick={() => setPhase('lesson')}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Lesson
          </button>
        </div>
        <CardQueue
          cards={practiceCards}
          onRate={handleRate}
          onAnswer={handleAnswer}
          answerState={answerState}
          onComplete={() => setPracticeCards([])}
          title={currentModule.title}
          emptyMessage="No questions to review."
        />
      </div>
    )
  }

  // ── Module complete ──
  if (phase === 'complete') {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 text-center">
        <span className="text-4xl block mb-4">🎉</span>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Module Complete!</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
          You've completed the practice for this module. Keep reviewing to strengthen your understanding.
        </p>
        <div className="flex gap-2 justify-center">
          <button onClick={() => { setPhase('list'); setCurrentModule(null) }}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium cursor-pointer hover:bg-indigo-700 transition-colors">
            Back to Modules
          </button>
          <button onClick={() => loadModule(currentModule?.id)}
            className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 text-sm font-medium cursor-pointer hover:bg-neutral-300 dark:hover:bg-neutral-600 transition-colors">
            Review Lesson Again
          </button>
        </div>
      </div>
    )
  }

  return null
}
