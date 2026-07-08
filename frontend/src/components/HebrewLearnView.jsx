import React, { useState, useEffect, useMemo } from 'react'

/**
 * HebrewLearnView — curriculum dashboard with gamification.
 * - 602 lessons across 9 categories with mastery tracking
 * - Streak counter + XP
 * - 5-minute quick session mode
 * - Category filter tabs
 * - Progress bar showing mastered/total
 */

const CATEGORY_STYLES = {
  consonant: { bg: 'bg-amber-100 dark:bg-amber-900/30', border: 'border-amber-300 dark:border-amber-700', text: 'text-amber-800 dark:text-amber-200', label: 'Letters', icon: 'א' },
  vowel: { bg: 'bg-blue-100 dark:bg-blue-900/30', border: 'border-blue-300 dark:border-blue-700', text: 'text-blue-800 dark:text-blue-200', label: 'Vowels', icon: 'ַ' },
  syllable: { bg: 'bg-cyan-100 dark:bg-cyan-900/30', border: 'border-cyan-300 dark:border-cyan-700', text: 'text-cyan-800 dark:text-cyan-200', label: 'Syllables', icon: '◌' },
  word: { bg: 'bg-green-100 dark:bg-green-900/30', border: 'border-green-300 dark:border-green-700', text: 'text-green-800 dark:text-green-200', label: 'Vocabulary', icon: 'מ' },
  verb: { bg: 'bg-purple-100 dark:bg-purple-900/30', border: 'border-purple-300 dark:border-purple-700', text: 'text-purple-800 dark:text-purple-200', label: 'Verbs', icon: 'ע' },
  noun: { bg: 'bg-pink-100 dark:bg-pink-900/30', border: 'border-pink-300 dark:border-pink-700', text: 'text-pink-800 dark:text-pink-200', label: 'Nouns', icon: 'ד' },
  syntax: { bg: 'bg-orange-100 dark:bg-orange-900/30', border: 'border-orange-300 dark:border-orange-700', text: 'text-orange-800 dark:text-orange-200', label: 'Syntax', icon: '⇄' },
  reading: { bg: 'bg-indigo-100 dark:bg-indigo-900/30', border: 'border-indigo-300 dark:border-indigo-700', text: 'text-indigo-800 dark:text-indigo-200', label: 'Reading', icon: 'ק' },
  grammar: { bg: 'bg-rose-100 dark:bg-rose-900/30', border: 'border-rose-300 dark:border-rose-700', text: 'text-rose-800 dark:text-rose-200', label: 'Grammar', icon: 'דק' },
  root: { bg: 'bg-teal-100 dark:bg-teal-900/30', border: 'border-teal-300 dark:border-teal-700', text: 'text-teal-800 dark:text-teal-200', label: 'Roots', icon: 'ש' },
  root_concept: { bg: 'bg-teal-100 dark:bg-teal-900/30', border: 'border-teal-300 dark:border-teal-700', text: 'text-teal-800 dark:text-teal-200', label: 'Roots', icon: 'ש' },
  phrase: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', border: 'border-yellow-300 dark:border-yellow-700', text: 'text-yellow-800 dark:text-yellow-200', label: 'Phrases', icon: 'כ' },
}

export default function HebrewLearnView({ onOpenLesson }) {
  const [curriculum, setCurriculum] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [streak, setStreak] = useState(0)
  const [xp, setXp] = useState(0)
  const [quickMode, setQuickMode] = useState(false)
  const [quickQuestions, setQuickQuestions] = useState([])
  const [quickIdx, setQuickIdx] = useState(0)
  const [timeLeft, setTimeLeft] = useState(300)
  const [quickScore, setQuickScore] = useState(0)

  // Load curriculum
  const loadCurriculum = () => {
    setLoading(true)
    fetch('/api/v1/hebrew/curriculum')
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          setCurriculum(d.data)
          computeStreak(d.data.nodes)
        } else setError(d.detail || 'Failed to load')
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(loadCurriculum, [])

  // Compute streak from progress data (stored in localStorage for persistence)
  const computeStreak = (nodes) => {
    // Simple: count consecutive days from localStorage
    const last = localStorage.getItem('hebrew_last_practice')
    const today = new Date().toDateString()
    if (last === today) {
      // Already practiced today, keep streak
    } else if (last && new Date(last).getTime() >= Date.now() - 2 * 86400000) {
      // Practiced yesterday, increment
    } else {
      // Streak broken
      localStorage.setItem('hebrew_streak', '0')
    }
    const saved = parseInt(localStorage.getItem('hebrew_streak') || '0')
    setStreak(saved)
    const savedXp = parseInt(localStorage.getItem('hebrew_xp') || '0')
    setXp(savedXp)
  }

  // Start quick session
  const startQuickSession = () => {
    if (!curriculum?.nodes) return
    // Pick from unlocked nodes
    const unlocked = curriculum.nodes.filter(n => n.unlocked && n.mastery < 0.8)
    if (unlocked.length === 0) {
      // Pick from mastered for review
      unlocked.push(...curriculum.nodes.filter(n => n.mastery >= 0.8))
    }
    const shuffled = [...unlocked].sort(() => Math.random() - 0.5).slice(0, 10)
    setQuickQuestions(shuffled)
    setQuickIdx(0)
    setQuickScore(0)
    setTimeLeft(300)
    setQuickMode(true)
  }

  // Quick session timer
  useEffect(() => {
    if (!quickMode) return
    if (timeLeft <= 0) { setQuickMode(false); return }
    const timer = setInterval(() => setTimeLeft(t => t - 1), 1000)
    return () => clearInterval(timer)
  }, [quickMode, timeLeft])

  const recordPractice = () => {
    // Update streak
    const today = new Date().toDateString()
    localStorage.setItem('hebrew_last_practice', today)
    const curStreak = parseInt(localStorage.getItem('hebrew_streak') || '0')
    const newStreak = curStreak + 1
    localStorage.setItem('hebrew_streak', String(newStreak))
    setStreak(newStreak)
    // Add XP
    const newXp = parseInt(localStorage.getItem('hebrew_xp') || '0') + 10
    localStorage.setItem('hebrew_xp', String(newXp))
    setXp(newXp)
    // Reload curriculum (to update mastery)
    setTimeout(loadCurriculum, 500)
  }

  if (loading) return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
        <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4" />
        {[1,2,3,4].map(i => <div key={i} className="h-16 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
      </div>
    </div>
  )

  if (error) return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">Failed to load: {error}</div>
    </div>
  )

  if (!curriculum) return null

  const { nodes, total, mastered, in_progress, locked } = curriculum
  const filtered = filter === 'all' ? nodes : nodes.filter(n => n.category === filter)
  const byLevel = {}
  for (const n of filtered) {
    if (!byLevel[n.level]) byLevel[n.level] = []
    byLevel[n.level].push(n)
  }

  // Quick mode rendering
  if (quickMode) {
    const q = quickQuestions[quickIdx]
    if (!q) {
      setQuickMode(false)
      return null
    }
    const mins = Math.floor(timeLeft / 60)
    const secs = timeLeft % 60
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="text-center mb-6">
          <span className={`text-2xl font-mono font-bold ${timeLeft < 30 ? 'text-red-500' : 'text-indigo-600 dark:text-indigo-400'}`}>
            {mins}:{String(secs).padStart(2, '0')}
          </span>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">Quick Session · {quickScore}/{quickQuestions.length}</p>
        </div>
        <div className="p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-indigo-200 dark:border-indigo-800 text-center">
          <p className="text-lg font-serif leading-relaxed mb-2" dir="rtl" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
            {q.title?.split('—')[0]?.trim() || q.title}
          </p>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-1">{q.title?.split('—')[1]?.trim() || q.description}</p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 mb-6">Level {q.level} · {q.category}</p>
          <button onClick={() => { onOpenLesson(q.id); setQuickMode(false) }}
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium cursor-pointer transition-colors">
            Practice this word
          </button>
          <div className="flex gap-2 justify-center mt-3">
            <button onClick={() => { setQuickIdx(prev => Math.min(prev + 1, quickQuestions.length - 1)); setQuickScore(s => s + 1) }}
              className="px-3 py-1.5 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs font-medium cursor-pointer transition-colors">Know it ✓</button>
            <button onClick={() => setQuickIdx(prev => Math.min(prev + 1, quickQuestions.length - 1))}
              className="px-3 py-1.5 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-medium cursor-pointer transition-colors">Skip →</button>
          </div>
        </div>
        <button onClick={() => setQuickMode(false)} className="mt-4 w-full py-2 rounded-lg text-sm text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 cursor-pointer transition-colors">
          End session
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-1">Biblical Hebrew</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">{total} lessons · {mastered} mastered · {locked} locked</p>
        </div>
        <div className="flex items-center gap-3">
          {streak > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
              <span className="text-sm">🔥</span>
              <span className="text-sm font-bold text-amber-700 dark:text-amber-300">{streak}</span>
              <span className="text-[9px] text-amber-500 dark:text-amber-400">day streak</span>
            </div>
          )}
          {xp > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700">
              <span className="text-sm">✨</span>
              <span className="text-sm font-bold text-indigo-700 dark:text-indigo-300">{xp}</span>
              <span className="text-[9px] text-indigo-500 dark:text-indigo-400">XP</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats + Quick mode button */}
      <div className="flex items-center gap-3 mb-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <div className="flex-1">
          <div className="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${(mastered / Math.max(total, 1)) * 100}%` }} />
          </div>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-neutral-500 dark:text-neutral-400">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> {mastered} mastered</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> {in_progress}</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-neutral-300 dark:bg-neutral-600" /> {locked} locked</span>
        </div>
        <button onClick={startQuickSession}
          className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          ⏱ 5-min quick
        </button>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-1.5 mb-6">
        {[{id:'all',count:total,label:'All'}].concat(
          Object.entries(CATEGORY_STYLES).map(([cat, cs]) => ({
            id: cat, count: nodes.filter(n => n.category === cat).length, ...cs
          })).filter(c => c.count > 0)
        ).map(c => (
          <button key={c.id} onClick={() => setFilter(c.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === c.id
                ? 'bg-indigo-600 text-white'
                : `${c.bg || 'bg-neutral-100 dark:bg-neutral-800'} ${c.text || 'text-neutral-600 dark:text-neutral-400'} hover:bg-neutral-200 dark:hover:bg-neutral-700`
            }`}>
            {c.icon && <span className="mr-1">{c.icon}</span>}
            {c.label || c.id} ({c.count})
          </button>
        ))}
      </div>

      {/* Lessons by level */}
      <div className="space-y-6">
        {Object.entries(byLevel).map(([level, levelNodes]) => (
          <div key={level}>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3">Level {level}</h3>
            <div className="space-y-1.5">
              {levelNodes.map(node => {
                const cs = CATEGORY_STYLES[node.category] || {}
                const isMastered = node.mastery >= 0.8
                const isLearning = node.mastery > 0 && node.mastery < 0.8
                const isLocked = !node.unlocked

                return (
                  <button key={node.id} onClick={() => { if (!isLocked) onOpenLesson?.(node.id) }} disabled={isLocked}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left cursor-pointer group
                      ${isLocked ? 'opacity-40 cursor-not-allowed border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/30'
                        : isMastered ? `${cs.bg} ${cs.border} hover:shadow-sm`
                        : isLearning ? 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 hover:shadow-sm'
                        : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm'
                      }`}>
                    {/* Status dot */}
                    <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                      isLocked ? 'bg-neutral-300 dark:bg-neutral-600'
                        : isMastered ? 'bg-green-500'
                        : isLearning ? 'bg-amber-500'
                        : 'bg-neutral-200 dark:bg-neutral-700'
                    }`} />

                    {/* Level */}
                    <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500 w-6 shrink-0">L{node.level}</span>

                    {/* Title + category */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium truncate ${isLocked ? 'text-neutral-400 dark:text-neutral-500' : 'text-neutral-800 dark:text-neutral-200'}`}>
                          {node.title}
                        </span>
                        {cs?.label && (
                          <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium shrink-0 ${cs.bg} ${cs.text} ${cs.border} border`}>
                            {cs.icon} {cs.label}
                          </span>
                        )}
                      </div>
                      {node.description && (
                        <p className={`text-xs mt-0.5 truncate ${isLocked ? 'text-neutral-400' : 'text-neutral-500 dark:text-neutral-400'}`}>{node.description}</p>
                      )}
                    </div>

                    {/* Mastery bar */}
                    <div className="w-14 shrink-0">
                      <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${isMastered ? 'bg-green-500' : isLearning ? 'bg-amber-500' : 'bg-neutral-300 dark:bg-neutral-600'}`}
                          style={{ width: `${node.mastery * 100}%` }} />
                      </div>
                      <span className="text-[8px] text-neutral-400 dark:text-neutral-500 mt-0.5 block text-right">{Math.round(node.mastery * 100)}%</span>
                    </div>

                    {isLocked && <span className="text-xs text-neutral-400 shrink-0">🔒</span>}
                    {!isLocked && !isMastered && <span className="text-xs text-indigo-500 dark:text-indigo-400 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">→</span>}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="p-8 text-center text-sm text-neutral-500 dark:text-neutral-400">
          No lessons in this category. Try another filter.
        </div>
      )}
    </div>
  )
}
