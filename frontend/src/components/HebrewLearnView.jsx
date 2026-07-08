import React, { useState, useEffect } from 'react'

/**
 * HebrewLearnView — structured curriculum dashboard.
 * Shows all Hebrew lessons organized by level/category.
 * Tracks mastery, shows prerequisites, enables progression.
 */

const CATEGORY_COLORS = {
  consonant: { bg: 'bg-amber-100 dark:bg-amber-900/30', border: 'border-amber-300 dark:border-amber-700', text: 'text-amber-800 dark:text-amber-200', label: 'Letters' },
  vowel: { bg: 'bg-blue-100 dark:bg-blue-900/30', border: 'border-blue-300 dark:border-blue-700', text: 'text-blue-800 dark:text-blue-200', label: 'Vowels' },
  syllable: { bg: 'bg-cyan-100 dark:bg-cyan-900/30', border: 'border-cyan-300 dark:border-cyan-700', text: 'text-cyan-800 dark:text-cyan-200', label: 'Syllables' },
  word: { bg: 'bg-green-100 dark:bg-green-900/30', border: 'border-green-300 dark:border-green-700', text: 'text-green-800 dark:text-green-200', label: 'Words' },
  verb: { bg: 'bg-purple-100 dark:bg-purple-900/30', border: 'border-purple-300 dark:border-purple-700', text: 'text-purple-800 dark:text-purple-200', label: 'Verbs' },
  noun: { bg: 'bg-pink-100 dark:bg-pink-900/30', border: 'border-pink-300 dark:border-pink-700', text: 'text-pink-800 dark:text-pink-200', label: 'Nouns' },
  syntax: { bg: 'bg-orange-100 dark:bg-orange-900/30', border: 'border-orange-300 dark:border-orange-700', text: 'text-orange-800 dark:text-orange-200', label: 'Syntax' },
  reading: { bg: 'bg-indigo-100 dark:bg-indigo-900/30', border: 'border-indigo-300 dark:border-indigo-700', text: 'text-indigo-800 dark:text-indigo-200', label: 'Reading' },
}

export default function HebrewLearnView({ onOpenLesson }) {
  const [curriculum, setCurriculum] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetch('/api/v1/hebrew/curriculum')
      .then(r => r.json())
      .then(d => {
        if (d.ok) setCurriculum(d.data)
        else setError(d.detail || 'Failed to load')
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
          <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4" />
          {[1,2,3,4].map(i => <div key={i} className="h-16 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
          Failed to load Hebrew curriculum: {error}
        </div>
      </div>
    )
  }

  if (!curriculum) return null

  const { nodes, total, mastered, in_progress, locked, categories } = curriculum

  // Filter nodes
  const filtered = filter === 'all' ? nodes : nodes.filter(n => n.category === filter)

  // Group by level
  const byLevel = {}
  for (const n of filtered) {
    if (!byLevel[n.level]) byLevel[n.level] = []
    byLevel[n.level].push(n)
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Biblical Hebrew</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {total} lessons · {mastered} mastered · {in_progress} in progress · {locked} locked
        </p>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-4 mb-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <div className="flex-1">
          <div className="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-green-500" style={{ width: `${(mastered / Math.max(total, 1)) * 100}%` }} />
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs text-neutral-500 dark:text-neutral-400">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> {mastered} mastered</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> {in_progress} learning</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-neutral-300 dark:bg-neutral-600" /> {locked} locked</span>
        </div>
      </div>

      {/* Category filter tabs */}
      <div className="flex flex-wrap gap-1.5 mb-6">
        <button onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
            filter === 'all' ? 'bg-indigo-600 text-white' : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
          }`}>
          All ({total})
        </button>
        {categories.map(cat => {
          const cc = CATEGORY_COLORS[cat]
          const count = nodes.filter(n => n.category === cat).length
          return (
            <button key={cat} onClick={() => setFilter(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
                filter === cat
                  ? `${cc.bg} ${cc.text} ${cc.border} border`
                  : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
              }`}>
              {cc?.label || cat} ({count})
            </button>
          )
        })}
      </div>

      {/* Curriculum tree by level */}
      <div className="space-y-6">
        {Object.entries(byLevel).map(([level, levelNodes]) => (
          <div key={level}>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3">
              Level {level}
            </h3>
            <div className="space-y-2">
              {levelNodes.map(node => {
                const cc = CATEGORY_COLORS[node.category] || {}
                const mastered = node.mastery >= 0.8
                const learning = node.mastery > 0 && node.mastery < 0.8
                const locked = !node.unlocked

                return (
                  <button
                    key={node.id}
                    onClick={() => {
                      if (!locked) onOpenLesson?.(node.id)
                    }}
                    disabled={locked}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left cursor-pointer
                      ${locked
                        ? 'opacity-40 cursor-not-allowed border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/30'
                        : mastered
                          ? `${cc.bg} ${cc.border} hover:shadow-sm`
                          : learning
                            ? 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 hover:shadow-sm'
                            : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm'
                      }`}
                  >
                    {/* Status indicator */}
                    <div className={`w-3 h-3 rounded-full shrink-0 ${
                      locked ? 'bg-neutral-300 dark:bg-neutral-600'
                        : mastered ? 'bg-green-500'
                        : learning ? 'bg-amber-500'
                        : 'bg-neutral-200 dark:bg-neutral-700'
                    }`} />

                    {/* Level badge */}
                    <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500 w-8 shrink-0">
                      L{node.level}
                    </span>

                    {/* Title and description */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${
                          locked ? 'text-neutral-400 dark:text-neutral-500' : 'text-neutral-800 dark:text-neutral-200'
                        }`}>
                          {node.title}
                        </span>
                        {cc?.label && (
                          <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${cc.bg} ${cc.text} ${cc.border} border`}>
                            {cc.label}
                          </span>
                        )}
                      </div>
                      {node.description && (
                        <p className={`text-xs mt-0.5 truncate ${locked ? 'text-neutral-400 dark:text-neutral-500' : 'text-neutral-500 dark:text-neutral-400'}`}>
                          {node.description}
                        </p>
                      )}
                    </div>

                    {/* Mastery bar */}
                    <div className="w-16 shrink-0">
                      <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                        <div className={`h-full rounded-full ${
                          mastered ? 'bg-green-500' : learning ? 'bg-amber-500' : 'bg-neutral-300 dark:bg-neutral-600'
                        }`} style={{ width: `${node.mastery * 100}%` }} />
                      </div>
                      <span className="text-[9px] text-neutral-400 dark:text-neutral-500 mt-0.5 block text-right">
                        {Math.round(node.mastery * 100)}%
                      </span>
                    </div>

                    {/* Prerequisites indicator */}
                    {locked && node.prerequisites?.length > 0 && (
                      <span className="text-[9px] text-neutral-400 dark:text-neutral-500 shrink-0" title={node.prerequisites.map(p => p.title).join(', ')}>
                        🔒
                      </span>
                    )}
                    {!locked && !mastered && (
                      <span className="text-xs text-indigo-500 dark:text-indigo-400 shrink-0">→</span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
