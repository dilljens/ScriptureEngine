import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import VersePreviewCard from './VersePreviewCard'
import StudyEditor from './StudyEditor'

const LAYER_COLORS = {
  linguistic:     { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-700 dark:text-emerald-300', dot: 'bg-emerald-500' },
  numerical:      { bg: 'bg-violet-50 dark:bg-violet-900/20',  text: 'text-violet-700 dark:text-violet-300',  dot: 'bg-violet-500' },
  structural:     { bg: 'bg-indigo-50 dark:bg-indigo-900/20',  text: 'text-indigo-700 dark:text-indigo-300',  dot: 'bg-indigo-500' },
  intertextual:   { bg: 'bg-blue-50 dark:bg-blue-900/20',      text: 'text-blue-700 dark:text-blue-300',      dot: 'bg-blue-500' },
  textual:        { bg: 'bg-gray-50 dark:bg-gray-800/50',      text: 'text-gray-600 dark:text-gray-400',      dot: 'bg-gray-400' },
  geographic:     { bg: 'bg-emerald-50 dark:bg-emerald-900/20', text: 'text-emerald-600 dark:text-emerald-400',dot: 'bg-emerald-500' },
  chronological:  { bg: 'bg-orange-50 dark:bg-orange-900/20',  text: 'text-orange-600 dark:text-orange-400',  dot: 'bg-orange-500' },
  interpretive:   { bg: 'bg-amber-50 dark:bg-amber-900/20',    text: 'text-amber-700 dark:text-amber-300',    dot: 'bg-amber-500' },
  frequency:      { bg: 'bg-pink-50 dark:bg-pink-900/20',      text: 'text-pink-600 dark:text-pink-400',      dot: 'bg-pink-500' },
  symbolic:       { bg: 'bg-purple-50 dark:bg-purple-900/20',  text: 'text-purple-700 dark:text-purple-300',  dot: 'bg-purple-500' },
  sod:            { bg: 'bg-rose-50 dark:bg-rose-900/20',      text: 'text-rose-700 dark:text-rose-300',      dot: 'bg-rose-500' },
}

function typeLabel(type) {
  return (type || '').replace(/_/g, ' ')
}

/**
 * StudyViewer — interactive tab that renders a scripture study with
 * clickable verse refs, connection graph paths, expand/collapse steps,
 * layer filtering, and an inline LLM Quick Ask bar.
 */
export default function StudyViewer({ study: initialStudy, onFetch, onNavigate, onOpenTab, showQuickAsk, onChatOpen, guideId }) {
  const [study, setStudy] = useState(initialStudy || null)
  const [loading, setLoading] = useState(!initialStudy)
  const [error, setError] = useState(null)
  const [collapsed, setCollapsed] = useState({})
  const [enabledLayers, setEnabledLayers] = useState(() => {
    // Enable all by default
    const all = {}
    for (const k of Object.keys(LAYER_COLORS)) all[k] = true
    return all
  })
  const [qaInput, setQaInput] = useState('')
  const [qaAnswer, setQaAnswer] = useState('')
  const [qaWaiting, setQaWaiting] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const qaRef = useRef(null)

  // Load study if slug/ID provided
  useEffect(() => {
    if (initialStudy) {
      setStudy(initialStudy)
      setLoading(false)
      return
    }
    if (onFetch) {
      setLoading(true)
      setError(null)
      onFetch()
        .then(data => { setStudy(data); setLoading(false) })
        .catch(err => { setError(err.message || String(err)); setLoading(false) })
    }
  }, [initialStudy, onFetch])

  // Auto-collapse all except first step on load
  useEffect(() => {
    if (study?.steps?.length > 0) {
      const c = { 0: false } // first step expanded
      for (let i = 1; i < study.steps.length; i++) c[i] = true
      setCollapsed(c)
    }
  }, [study?.steps?.length])

  // Toggle step collapse
  const toggleStep = useCallback((idx) => {
    setCollapsed(prev => ({ ...prev, [idx]: !prev[idx] }))
  }, [])

  // Toggle layer filter
  const toggleLayer = useCallback((layer) => {
    setEnabledLayers(prev => ({ ...prev, [layer]: !prev[layer] }))
  }, [])

  // Collect all unique layers across all steps
  const allLayers = useMemo(() => {
    const s = new Set()
    if (!study?.steps) return []
    for (const step of study.steps) {
      for (const c of (step.connections || [])) {
        if (c.layer) s.add(c.layer)
      }
    }
    return Array.from(s).sort()
  }, [study])

  // Quick Ask handler
  const handleQuickAsk = useCallback(async () => {
    const q = qaInput.trim()
    if (!q || qaWaiting) return
    setQaWaiting(true)
    setQaAnswer('')
    try {
      // Build context from the study
      const context = {
        title: study?.title || 'Study',
        steps: study?.steps?.map(s => ({
          step: s.step, verse: s.verse, title: s.title,
          explanation: s.explanation,
          connections: (s.connections || []).slice(0, 5),
        })) || [],
      }
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            { role: 'system', content: `You are a scripture study assistant. The user is studying: "${study?.title || 'a scripture study'}". Here is the study context:\n${JSON.stringify(context, null, 2)}\n\nAnswer based on the scriptures. Cite verse references when possible. Be concise.` },
            { role: 'user', content: q },
          ],
          model: 'deepseek-chat',
          max_tokens: 1000,
          temperature: 0.5,
        }),
      })
      const data = await res.json()
      const answer = data?.choices?.[0]?.message?.content || data?.message?.content || data?.content || 'No answer received.'
      setQaAnswer(answer)
    } catch (err) {
      setQaAnswer(`Error: ${err.message}`)
    } finally {
      setQaWaiting(false)
    }
  }, [qaInput, qaWaiting, study])

  // Open full chat
  const openFullChat = useCallback(() => {
    if (onChatOpen && study) {
      onChatOpen(`Continuing study: "${study.title}". Context loaded.`)
    }
  }, [onChatOpen, study])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500 text-sm">
        <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Loading study…
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-4 mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
        {error}
      </div>
    )
  }

  if (!study) {
    return (
      <div className="mx-4 mt-4 p-4 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-700 dark:text-amber-300 text-sm">
        Study not found.
      </div>
    )
  }

  const { title, description, author, steps, graph_summary, seed_verse } = study
  const totalSteps = steps?.length || 0
  const expandedCount = Object.values(collapsed).filter(v => !v).length

  return (
    <div className="max-w-4xl mx-auto px-6 py-6">
      {/* Header */}
      <div className="mb-6 pb-4 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">{title}</h1>
            {description && <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{description}</p>}
            <div className="flex items-center gap-3 mt-2 text-[11px] text-neutral-400 dark:text-neutral-500">
              {author?.name && <span>by {author.name}</span>}
              <span>{totalSteps} steps · {expandedCount}/{totalSteps} expanded</span>
              {graph_summary?.total_connections > 0 && <span>{graph_summary.total_connections} graph connections</span>}
              {seed_verse && <button onClick={() => { const p = seed_verse.split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}})) }}
  className="hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer transition-colors">seed: {seed_verse}</button>}
            </div>
          </div>
          <button onClick={() => setEditMode(!editMode)}
            className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all cursor-pointer ml-4
              ${editMode
                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-700'
              }`}>
            {editMode ? '← View' : 'Edit'}
          </button>
        </div>
      </div>

      {/* Editor Mode */}
      {editMode && guideId && (
        <StudyEditor
          study={{ title, description, author, steps, graph_summary, seed_verse }}
          guideId={guideId}
          onSave={() => {
            // Reload study after save
            setEditMode(false)
            if (onFetch) onFetch().then(setStudy)
          }}
          onNavigate={onNavigate}
          onOpenTab={onOpenTab}
          showQuickAsk={showQuickAsk}
        />
      )}
      {editMode && !guideId && (
        <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-sm text-amber-700 dark:text-amber-300 mb-4">
          Editing is only available for draft studies (not published snapshots). Fork this study first.
        </div>
      )}

      {/* Layer filters */}
      {allLayers.length > 1 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          <span className="text-[10px] font-medium text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mr-1 self-center">Layers:</span>
          {allLayers.map(layer => (
            <button key={layer} onClick={() => toggleLayer(layer)}
              className={`text-[10px] px-2 py-0.5 rounded-full border transition-all cursor-pointer
                ${enabledLayers[layer] !== false
                  ? `${LAYER_COLORS[layer]?.bg || 'bg-blue-50 dark:bg-blue-900/20'} ${LAYER_COLORS[layer]?.text || 'text-blue-700 dark:text-blue-300'} border-transparent font-medium`
                  : 'bg-transparent text-neutral-400 dark:text-neutral-600 border-neutral-200 dark:border-neutral-700'
                }`}>
              {typeLabel(layer)}
            </button>
          ))}
        </div>
      )}

      {/* Steps */}
      <div className="space-y-3">
        {steps?.map((step, idx) => {
          const isCollapsed = collapsed[idx] !== false
          const conns = (step.connections || []).filter(c => enabledLayers[c.layer] !== false)
          const parts = step.verse?.split('.') || []
          const bookChapter = parts.length >= 2 ? `${parts[0]}.${parts[1]}` : ''

          return (
            <div key={idx} className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden shadow-sm">
              {/* Step header */}
              <button onClick={() => toggleStep(idx)}
                className="w-full flex items-center gap-3 px-4 py-3 bg-neutral-50 dark:bg-neutral-800/50 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 transition-colors cursor-pointer text-left border-b border-neutral-100 dark:border-neutral-700">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500 text-white text-[11px] font-bold shrink-0">
                  {step.step || idx + 1}
                </span>
                <span className="flex-1 text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">
                  {step.title || `${step.verse}`}
                </span>
                <button onClick={() => { const p = (step.verse || '').split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}})) }}
                  className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500 hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer transition-colors">{step.verse}</button>
                {conns.length > 0 && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-medium">
                    {conns.length}
                  </span>
                )}
                <span className="text-neutral-300 dark:text-neutral-600 text-sm transition-transform" style={{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
                  ▼
                </span>
              </button>

              {/* Step body */}
              {!isCollapsed && (
                <div className="px-4 py-3 space-y-3">
                  {/* Verse reference — clickable */}
                  <div className="flex items-center gap-2">
                    <button onClick={() => onNavigate && onNavigate(parts[0], parseInt(parts[1]) || 1)}
                      className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">
                      {step.verse}
                    </button>
                    {step.book_title && <span className="text-[10px] text-neutral-400 dark:text-neutral-500">{step.book_title}</span>}
                    <button onClick={() => onOpenTab && onOpenTab(parts[0], parseInt(parts[1]) || 1, { label: bookChapter })}
                      className="text-[9px] text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 ml-auto cursor-pointer"
                      title="Open chapter in new tab">⧉</button>
                  </div>

                  {/* VersePreviewCard as popover */}
                  <VersePreviewCard refs={step.verse} onNavigate={onNavigate} maxHeight="10rem" />

                  {/* Explanation */}
                  {step.explanation && (
                    <div className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
                      {step.explanation}
                    </div>
                  )}

                  {/* Connections */}
                  {conns.length > 0 && (
                    <div className="pt-2 border-t border-neutral-100 dark:border-neutral-700">
                      <h4 className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1.5">
                        Graph Paths
                      </h4>
                      <div className="space-y-1">
                        {conns.map((c, ci) => {
                          const lc = LAYER_COLORS[c.layer] || { bg: 'bg-neutral-50 dark:bg-neutral-800', text: 'text-neutral-600 dark:text-neutral-400', dot: 'bg-neutral-400' }
                          return (
                            <div key={ci} className={`flex items-start gap-2 px-2.5 py-1.5 rounded text-[11px] ${lc.bg}`}>
                              <span className={`w-1.5 h-1.5 rounded-full mt-1 shrink-0 ${lc.dot}`} />
                              <div className="flex-1 min-w-0">
                                <span className={`font-medium ${lc.text}`}>{typeLabel(c.type)}</span>
                                <span className="text-neutral-400 dark:text-neutral-500 ml-1">— {c.layer}</span>
                                <span className="text-neutral-300 dark:text-neutral-600 ml-1">({c.strength?.toFixed(2)})</span>
                                <button onClick={() => {
                                  const tp = (c.to || '').split('.')
                                  if (tp.length >= 2 && onNavigate) onNavigate(tp[0], parseInt(tp[1]) || 1)
                                }}
                                  className="block text-blue-600 dark:text-blue-400 hover:underline mt-0.5 cursor-pointer">
                                  → {c.to || ''}
                                </button>
                              </div>
                              {c.to_text && <span className="text-neutral-500 dark:text-neutral-400 truncate max-w-[200px] text-right">{c.to_text.slice(0, 60)}…</span>}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* Choices (branching) */}
                  {step.choices?.length > 0 && (
                    <div className="pt-1">
                      <h4 className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1">Continue exploring</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {step.choices.map((ch, ci) => (
                          <button key={ci} onClick={() => {
                            const cp = (ch.verse || '').split('.')
                            if (cp.length >= 2 && onNavigate) onNavigate(cp[0], parseInt(cp[1]) || 1)
                          }}
                            className="text-[11px] px-2.5 py-1 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-700 dark:hover:text-blue-300 border border-neutral-200 dark:border-neutral-600 transition-all cursor-pointer">
                            {ch.label || ch.verse} →
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Graph summary */}
      {graph_summary?.total_connections > 0 && (
        <div className="mt-6 p-4 bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700 rounded-lg">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-1">Graph Summary</h3>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-600 dark:text-neutral-400">
            <span>Connections: <strong>{graph_summary.total_connections}</strong></span>
            {graph_summary.unique_layers?.length > 0 && <span>Layers: <strong>{graph_summary.unique_layers.join(', ')}</strong></span>}
            {graph_summary.hub_verses?.length > 0 && <span>Hub verses: <strong>{graph_summary.hub_verses.length}</strong></span>}
          </div>
        </div>
      )}

      {/* Inline Quick Ask */}
      {showQuickAsk && (
        <div className="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Quick Ask</span>
            <button onClick={openFullChat}
              className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline ml-auto cursor-pointer">
              Open full chat →
            </button>
          </div>
          <div className="flex gap-2">
            <input ref={qaRef} type="text" value={qaInput}
              onChange={e => setQaInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleQuickAsk() }}
              placeholder="Ask about this study…"
              className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 placeholder-neutral-400 dark:placeholder-neutral-500" />
            <button onClick={handleQuickAsk} disabled={qaWaiting || !qaInput.trim()}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer
                ${qaWaiting ? 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 cursor-not-allowed'
                  : 'bg-blue-500 text-white hover:bg-blue-600 active:bg-blue-700'}`}>
              {qaWaiting ? '…' : 'Ask'}
            </button>
          </div>
          {qaAnswer && (
            <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-lg text-sm text-neutral-700 dark:text-neutral-300">
              {qaAnswer}
              <button onClick={openFullChat}
                className="block mt-1 text-[10px] text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">
                Continue in full chat →
              </button>
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 text-center text-[10px] text-neutral-300 dark:text-neutral-600">
        Study format: scripture-study-v1 · {totalSteps} steps · {graph_summary?.total_connections || 0} graph paths
      </div>
    </div>
  )
}
