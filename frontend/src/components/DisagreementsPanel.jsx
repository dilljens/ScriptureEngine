import React, { useState, useEffect } from 'react'

/**
 * DisagreementsPanel — shows interpretive disagreements for a verse.
 *
 * Disagreements are contradictory readings across traditions (Jewish vs
 * Christian, critical vs faith-based, etc.).
 *
 * Props:
 *   verse: string (e.g., "isa.7.14")
 *   onNavigate: (book, chapter) => void
 */
export default function DisagreementsPanel({ verse, onNavigate }) {
  const [disagreements, setDisagreements] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState({})

  useEffect(() => {
    if (!verse) return
    setLoading(true)
    setError(null)
    fetch(`/api/v1/tools/scripture_disagreements?verse=${encodeURIComponent(verse)}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) setDisagreements(d.data.disagreements || [])
        else setError(d.detail || 'Failed to load')
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [verse])

  if (!verse) return null
  if (loading) return <div className="text-xs text-neutral-400 animate-pulse p-3">Loading disagreements…</div>
  if (error) return null // silently fail — disagreements are enrichment, not core
  if (disagreements.length === 0) return null

  const toggle = (i) => setExpanded(prev => ({ ...prev, [i]: !prev[i] }))

  return (
    <div className="mt-4 p-3 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
      <h3 className="text-[10px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-2 flex items-center gap-1">
        <span>⚖️ Interpretive Disagreements</span>
        <span className="text-[9px] font-normal opacity-60">({disagreements.length})</span>
      </h3>
      <div className="space-y-1.5">
        {disagreements.map((d, i) => {
          const isExpanded = expanded[i]
          return (
            <div key={d.id || i} className="text-xs">
              <button onClick={() => toggle(i)}
                className="w-full text-left flex items-start gap-2 p-2 rounded-lg hover:bg-amber-100/50 dark:hover:bg-amber-900/20 transition-colors cursor-pointer">
                <span className="text-amber-500 mt-0.5 shrink-0">{isExpanded ? '▾' : '▸'}</span>
                <div className="flex-1 min-w-0">
                  {/* Tradition badges */}
                  <div className="flex flex-wrap items-center gap-1 mb-1">
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
                      {d.tradition_a || 'Tradition A'}
                    </span>
                    <span className="text-[9px] text-amber-400">vs</span>
                    <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                      {d.tradition_b || 'Tradition B'}
                    </span>
                  </div>
                  {/* Description */}
                  <p className="text-[11px] text-neutral-700 dark:text-neutral-300 leading-relaxed">
                    {d.description || 'No description available.'}
                  </p>
                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="mt-2 space-y-1.5 pl-1">
                      {d.verse_a && (
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-mono text-neutral-400">A:</span>
                          <button onClick={() => {
                            const p = d.verse_a.split('.')
                            if (p.length >= 2 && onNavigate) onNavigate(p[0], parseInt(p[1]) || 1)
                          }}
                            className="text-[10px] font-mono text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">
                            {d.verse_a}
                          </button>
                          {d.text_a && <span className="text-[9px] text-neutral-500 truncate">"{d.text_a.slice(0, 80)}…"</span>}
                        </div>
                      )}
                      {d.verse_b && (
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-mono text-neutral-400">B:</span>
                          <button onClick={() => {
                            const p = d.verse_b.split('.')
                            if (p.length >= 2 && onNavigate) onNavigate(p[0], parseInt(p[1]) || 1)
                          }}
                            className="text-[10px] font-mono text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">
                            {d.verse_b}
                          </button>
                          {d.text_b && <span className="text-[9px] text-neutral-500 truncate">"{d.text_b.slice(0, 80)}…"</span>}
                        </div>
                      )}
                      {d.resolved_by && (
                        <p className="text-[9px] text-green-600 dark:text-green-400">
                          ✓ Resolved by: {d.resolved_by}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
