import React, { useMemo, useState, useEffect, useCallback } from 'react'
import { getChapterEntities } from '../api'

/**
 * WikiLayout — Wikipedia-style two-column chapter view.
 *
 * Takes the same chapter data as ChapterView but renders it with:
 * - Two-column grid: verse text (left) + connection sidebar (right)
 * - Breadcrumb: Work → Book → Chapter
 * - Book infobox at top
 * - Connection sidebar grouped by layer with expand/collapse
 * - Quality stars on connections
 * - Layer badges (colored pills)
 * - Responsive: sidebar collapses below lg breakpoint
 */
const LAYER_COLORS = {
  linguistic: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800', dot: 'bg-blue-500' },
  numerical: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800', dot: 'bg-purple-500' },
  structural: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-300', border: 'border-green-200 dark:border-green-800', dot: 'bg-green-500' },
  intertextual: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200 dark:border-amber-800', dot: 'bg-amber-500' },
  textual: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-700 dark:text-red-300', border: 'border-red-200 dark:border-red-800', dot: 'bg-red-500' },
  geographic: { bg: 'bg-teal-100 dark:bg-teal-900/30', text: 'text-teal-700 dark:text-teal-300', border: 'border-teal-200 dark:border-teal-800', dot: 'bg-teal-500' },
  chronological: { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-700 dark:text-orange-300', border: 'border-orange-200 dark:border-orange-800', dot: 'bg-orange-500' },
  interpretive: { bg: 'bg-pink-100 dark:bg-pink-900/30', text: 'text-pink-700 dark:text-pink-300', border: 'border-pink-200 dark:border-pink-800', dot: 'bg-pink-500' },
  frequency: { bg: 'bg-cyan-100 dark:bg-cyan-900/30', text: 'text-cyan-700 dark:text-cyan-300', border: 'border-cyan-200 dark:border-cyan-800', dot: 'bg-cyan-500' },
  symbolic: { bg: 'bg-violet-100 dark:bg-violet-900/30', text: 'text-violet-700 dark:text-violet-300', border: 'border-violet-200 dark:border-violet-800', dot: 'bg-violet-500' },
  sod: { bg: 'bg-indigo-100 dark:bg-indigo-900/30', text: 'text-indigo-700 dark:text-indigo-300', border: 'border-indigo-200 dark:border-indigo-800', dot: 'bg-indigo-500' },
}

const LAYER_LABELS = {
  linguistic: 'Linguistic', numerical: 'Numerical', structural: 'Structural',
  intertextual: 'Intertextual', textual: 'Textual', geographic: 'Geographic',
  chronological: 'Chronological', interpretive: 'Interpretive',
  frequency: 'Frequency', symbolic: 'Symbolic', sod: 'Sod',
}

/** Render quality score (0-100) with color coding */
function QualityStars({ quality_score }) {
  const score = typeof quality_score === 'number' ? Math.round(quality_score) : 0
  const clamped = Math.max(0, Math.min(100, score))
  const color = clamped >= 80 ? '#2E7D32' : clamped >= 60 ? '#F57C00' : clamped >= 35 ? '#757575' : '#9E9E9E'
  return (
    <span className="text-[11px] font-mono whitespace-nowrap" style={{ color }} title={`Quality: ${clamped}/100`}>
      {clamped}
    </span>
  )
}

/** Render a colored layer badge pill */
function LayerBadge({ layer }) {
  const colors = LAYER_COLORS[layer] || LAYER_COLORS.linguistic
  const label = LAYER_LABELS[layer] || layer
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium ${colors.bg} ${colors.text} ${colors.border} border`}>
      <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
      {label}
    </span>
  )
}

/** Parse verse reference into (book, chapter, verse) */
function parseRef(ref) {
  if (!ref) return null
  const parts = ref.split('.')
  if (parts.length >= 3) return { book: parts[0], chapter: parts[1], verse: parts.slice(2).join('.') }
  if (parts.length === 2) return { book: parts[0], chapter: parts[1], verse: '' }
  return { book: parts[0], chapter: '', verse: '' }
}

/** Collapse a connection sidebar section */
function ConnectionSection({ layer, connections, defaultOpen }) {
  const [open, setOpen] = React.useState(defaultOpen)
  const colors = LAYER_COLORS[layer] || LAYER_COLORS.linguistic
  const label = LAYER_LABELS[layer] || layer

  return (
    <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium ${colors.bg} ${colors.text} cursor-pointer hover:opacity-80 transition-opacity`}
      >
        <span className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${colors.dot}`} />
          {label}
          <span className="text-[10px] opacity-60">({connections.length})</span>
        </span>
        <span className="text-[10px] opacity-60">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
          {connections.map((conn, i) => (
            <div key={i} className="px-3 py-2 text-[11px] text-neutral-700 dark:text-neutral-300 space-y-1">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="font-medium">{conn.type}</span>
                {conn.quality_score != null && <QualityStars quality_score={conn.quality_score} />}
              </div>
              {conn.subtype && <span className="text-[10px] text-neutral-400 dark:text-neutral-500">{conn.subtype}</span>}
              {conn.target_verse && (() => {
                const pr = parseRef(conn.target_verse)
                return (
                  <button onClick={(e) => { e.stopPropagation(); const p = conn.target_verse.split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}})) }}
                    className="text-[10px] text-blue-600 dark:text-blue-400 truncate hover:text-indigo-600 dark:hover:text-indigo-300 cursor-pointer transition-colors">
                    → {pr?.book}.{pr?.chapter}:{pr?.verse}
                  </button>
                )
              })()}
              {conn.strength != null && (
                <div className="text-[9px] text-neutral-400 dark:text-neutral-500">
                  strength: {typeof conn.strength === 'number' ? conn.strength.toFixed(2) : conn.strength}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** Simple SVG force-directed graph — renders nodes as circles and edges as colored lines */
function ConnectionGraphSVG({ nodes, edges, width = 500, height = 250 }) {
  const cx = width / 2
  const cy = height / 2
  const radius = Math.min(cx, cy) - 30

  // Circular layout positions
  const positions = {}
  nodes.forEach((n, i) => {
    const angle = (i / nodes.length) * Math.PI * 2 - Math.PI / 2
    positions[n.id] = {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  })

  // Layer colors (matches ConnectionGraph)
  const EDGE_COLORS = {
    linguistic: '#10b981', numerical: '#f59e0b', structural: '#8b5cf6',
    intertextual: '#3b82f6', textual: '#ec4899', geographic: '#14b8a6',
    chronological: '#f97316', interpretive: '#a855f7', frequency: '#06b6d4',
    symbolic: '#eab308', sod: '#ef4444',
  }

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto max-h-64 bg-neutral-50 dark:bg-neutral-900/20 rounded">
      {/* Edges */}
      {edges.map((e, i) => {
        const p1 = positions[e.source]
        const p2 = positions[e.target]
        if (!p1 || !p2) return null
        return (
          <line key={i}
            x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y}
            stroke={EDGE_COLORS[e.layer] || '#6b7280'}
            strokeWidth={1} opacity={0.5}
          />
        )
      })}
      {/* Nodes */}
      {nodes.map((n) => {
        const p = positions[n.id]
        if (!p) return null
        return (
          <g key={n.id}>
            <circle cx={p.x} cy={p.y} r={14}
              className="fill-blue-100 dark:fill-blue-900/40 stroke-blue-500 dark:stroke-blue-400"
              strokeWidth={2}
            />
            <text x={p.x} y={p.y + 0.5} textAnchor="middle" dominantBaseline="central"
              className="fill-blue-700 dark:fill-blue-300 text-[9px] font-medium"
              fontSize={9}>
              {n.label}
            </text>
          </g>
        )
      })}
    </svg>
  )
}


export default function WikiLayout({ data, book, chapter, toggles, chapterConnections, onOpenWiki }) {
  const [graphOpen, setGraphOpen] = React.useState(false)
  const [browseLayer, setBrowseLayer] = React.useState(null)
  const [entities, setEntities] = React.useState([])
  const [entitiesLoading, setEntitiesLoading] = React.useState(false)

  // Fetch real entities from the API
  useEffect(() => {
    const ref = `${book}.${chapter}`
    setEntitiesLoading(true)
    getChapterEntities(ref)
      .then(res => {
        if (res.ok && res.data?.entities) {
          setEntities(res.data.entities)
        }
      })
      .catch(() => {}) // ponytail: fail silently, entities stay empty
      .finally(() => setEntitiesLoading(false))
  }, [book, chapter])

  // Group connections by layer from chapterConnections data
  const connectionsByLayer = useMemo(() => {
    if (!chapterConnections) return {} // ponytail: no connection data falls back gracefully
    const grouped = {}
    for (const [vnum, conns] of Object.entries(chapterConnections)) {
      for (const c of conns) {
        const layer = c.layer || 'intertextual'
        if (!grouped[layer]) grouped[layer] = []
        grouped[layer].push({ ...c, verse_num: vnum })
      }
    }
    return Object.fromEntries(
      Object.entries(grouped)
        .map(([k, v]) => [k, v.slice(0, 50)])
        .sort((a, b) => b[1].length - a[1].length)
    )
  }, [chapterConnections])

  // Group connections by type within a layer for Browse-by-Layer view
  const connectionsByType = useMemo(() => {
    if (!browseLayer || !connectionsByLayer[browseLayer]) return {}
    const grouped = {}
    for (const c of connectionsByLayer[browseLayer]) {
      const type = c.type || 'unknown'
      if (!grouped[type]) grouped[type] = []
      grouped[type].push(c)
    }
    return Object.fromEntries(
      Object.entries(grouped).sort((a, b) => b[1].length - a[1].length)
    )
  }, [browseLayer, connectionsByLayer])

  // Build graph elements for the simple chapter graph
  const graphElements = useMemo(() => {
    if (!chapterConnections || !verses.length) return { nodes: [], edges: [] }
    const nodes = verses.map(v => ({ id: String(v.verse), label: String(v.verse) }))
    const edges = []
    const seen = new Set()
    for (const [vnum, conns] of Object.entries(chapterConnections)) {
      for (const c of conns) {
        const target = c.target_verse?.split('.').pop() || ''
        if (target && target !== vnum) {
          const key = [vnum, target, c.type].sort().join('|')
          if (!seen.has(key)) {
            seen.add(key)
            edges.push({ source: vnum, target, type: c.type, layer: c.layer })
          }
        }
      }
    }
    return { nodes, edges: edges.slice(0, 100) }
  }, [chapterConnections, verses])

  const verses = data?.verses || []
  const bookInfo = data?.book || {}

  if (!data) return null

  return (
    <div className="max-w-7xl mx-auto px-4 py-4">
      {/* ── Breadcrumb ── */}
      <nav className="text-[11px] text-neutral-400 dark:text-neutral-500 mb-3 flex items-center gap-1.5 flex-wrap">
        <a href={`/work/${bookInfo.work_id || ''}`} className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
          {bookInfo.work_title || 'Scripture'}
        </a>
        <span className="opacity-50">›</span>
        <span className="font-medium text-neutral-600 dark:text-neutral-300">{bookInfo.title || book}</span>
        <span className="opacity-50">›</span>
        <span>Chapter {chapter}</span>
        <span className="ml-auto text-[10px] text-neutral-300 dark:text-neutral-600">{verses.length} verses</span>
      </nav>

      {/* ── Two-column grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        {/* ── Left: Verse Text ── */}
        <div className="min-w-0">
          {/* Infobox */}
          <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 px-4 py-3 mb-6 text-xs text-neutral-600 dark:text-neutral-400">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-semibold text-neutral-800 dark:text-neutral-200">{bookInfo.title || book} {chapter}</span>
              {bookInfo.work_title && <span className="text-[10px] text-neutral-400">({bookInfo.work_title})</span>}
              <span className="text-[10px]">{verses.length} verses</span>
              {entities.length > 0 && <span className="text-[10px]">{entities.length} entities</span>}
              {Object.keys(connectionsByLayer).length > 0 && (
                <span className="text-[10px]">
                  {Object.values(connectionsByLayer).reduce((a, b) => a + b.length, 0)} connections
                </span>
              )}
            </div>
          </div>

          {/* ── Graph Panel — interactive SVG force graph ── */}
          {graphElements.nodes.length > 1 && (
            <div className="mb-6 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
              <button
                onClick={() => setGraphOpen(!graphOpen)}
                className="w-full flex items-center justify-between px-4 py-2 text-xs font-medium text-neutral-600 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-800/30 hover:bg-neutral-100 dark:hover:bg-neutral-800/50 cursor-pointer transition-colors"
              >
                <span className="flex items-center gap-2">
                  <span className="text-blue-500">◉</span>
                  Chapter Connection Graph
                  <span className="text-[10px] opacity-60">({graphElements.nodes.length} nodes, {graphElements.edges.length} edges)</span>
                </span>
                <span className="text-[10px] opacity-60">{graphOpen ? '▾' : '▸'}</span>
              </button>
              {graphOpen && (
                <div className="p-3 bg-white dark:bg-neutral-800/10">
                  <ConnectionGraphSVG nodes={graphElements.nodes} edges={graphElements.edges} />
                  {/* Edge list below graph */}
                  <details className="mt-2">
                    <summary className="text-[10px] text-neutral-400 cursor-pointer hover:text-neutral-600 dark:hover:text-neutral-300">
                      Show edge list ({graphElements.edges.length} edges)
                    </summary>
                    <div className="text-[10px] text-neutral-400 max-h-24 overflow-y-auto space-y-0.5 mt-1">
                      {graphElements.edges.slice(0, 50).map((e, i) => (
                        <div key={i} className="truncate">
                          <button onClick={() => window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book, chapter: parseInt(chapter), verse: parseInt(e.source)}}))}
                            className="font-mono text-blue-500 hover:text-indigo-600 cursor-pointer transition-colors">{e.source}</button>
                          <span className="mx-1">—{e.layer?.slice(0, 4)}→</span>
                          <button onClick={() => window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book, chapter: parseInt(chapter), verse: parseInt(e.target)}}))}
                            className="font-mono text-blue-500 hover:text-indigo-600 cursor-pointer transition-colors">{e.target}</button>
                          <span className="ml-1 text-neutral-400">({e.type})</span>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}

          {/* Verse blocks */}
          <div className="space-y-4">
            {verses.map((v) => {
              const vnum = String(v.verse)
              return (
                <div key={vnum} id={`wiki-verse-${book}.${chapter}.${vnum}`} className="group scroll-mt-16">
                  {/* Verse number */}
                  <a href={`#wiki-verse-${book}.${chapter}.${vnum}`}
                    className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-[10px] font-bold mr-2 float-left -ml-8 mt-0.5 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors no-underline">
                    {vnum}
                  </a>

                  {/* Verse text */}
                  <div className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
                    {toggles?.displayLang === 'hebrew' && v.text_hebrew && (
                      <span className="text-lg text-right block" dir="rtl">{v.text_hebrew}</span>
                    )}
                    {toggles?.displayLang === 'greek' && v.text_greek && (
                      <span className="block">{v.text_greek}</span>
                    )}
                    {(toggles?.displayLang === 'english' || !toggles?.displayLang) && (
                      <span>{v.text_english}</span>
                    )}
                  </div>

                  {/* Inline connection badges */}
                  {chapterConnections?.[vnum]?.length > 0 && (
                    <div className="mt-1.5 flex items-center gap-1 flex-wrap opacity-0 group-hover:opacity-100 transition-opacity">
                      {chapterConnections[vnum].slice(0, 3).map((c, i) => (
                        <LayerBadge key={i} layer={c.layer || 'intertextual'} />
                      ))}
                      {chapterConnections[vnum].length > 3 && (
                        <span className="text-[9px] text-neutral-400">+{chapterConnections[vnum].length - 3} more</span>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Right: Connection Sidebar ── */}
        <aside className="space-y-4">
          {/* Chapter stats card */}
          <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 bg-white dark:bg-neutral-800/30">
            <h3 className="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">Chapter Info</h3>
            <div className="space-y-1 text-[11px] text-neutral-600 dark:text-neutral-400">
              <div className="flex justify-between"><span>Verses</span><span className="font-medium">{verses.length}</span></div>
              <div className="flex justify-between"><span>Connections</span><span className="font-medium">{Object.values(connectionsByLayer).reduce((a, b) => a + b.length, 0)}</span></div>
              <div className="flex justify-between"><span>Layers</span><span className="font-medium">{Object.keys(connectionsByLayer).length}</span></div>
              <div className="flex justify-between"><span>Entities</span><span className="font-medium">{entities.length}</span></div>
            </div>
          </div>

          {/* ── Browse by Layer (B4) ── */}
          {Object.keys(connectionsByLayer).length > 0 && (
            <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 bg-white dark:bg-neutral-800/30">
              <h3 className="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">Browse by Layer</h3>
              {/* Layer tabs */}
              <div className="flex flex-wrap gap-1 mb-2">
                {Object.keys(connectionsByLayer).map(layer => (
                  <button key={layer} onClick={() => setBrowseLayer(browseLayer === layer ? null : layer)}
                    className={`px-1.5 py-0.5 rounded text-[9px] font-medium cursor-pointer transition-colors ${
                      browseLayer === layer
                        ? (LAYER_COLORS[layer]?.bg || 'bg-blue-100') + ' ' + (LAYER_COLORS[layer]?.text || 'text-blue-700') + ' border ' + (LAYER_COLORS[layer]?.border || 'border-blue-200')
                        : 'text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700/50 border border-transparent'
                    }`}>
                    {LAYER_LABELS[layer] || layer}
                  </button>
                ))}
              </div>
              {/* Connections grouped by type for selected layer */}
              {browseLayer && (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {Object.entries(connectionsByType).map(([type, conns]) => (
                    <div key={type}>
                      <div className="flex items-center gap-1 text-[10px] font-medium text-neutral-600 dark:text-neutral-400 mb-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-neutral-400" />
                        {type}
                        <span className="text-[9px] opacity-60">({conns.length})</span>
                      </div>
                      <div className="pl-3 space-y-0.5">
                        {conns.slice(0, 5).map((c, i) => (
                          <div key={i} className="text-[10px] text-neutral-500 dark:text-neutral-400 truncate">
                            <button onClick={() => { const p = (c.target_verse || '').split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}})) }}
                              className="hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer transition-colors">v{c.verse_num}</button>
                            <span className="mx-0.5">→</span>
                            <button onClick={() => { const p = (c.target_verse || '').split('.'); if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}})) }}
                              className="hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer transition-colors">{c.target_verse?.split('.').pop()}</button>
                            {c.quality_score != null && <QualityStars quality_score={c.quality_score} />}
                          </div>
                        ))}
                        {conns.length > 5 && (
                          <div className="text-[9px] text-neutral-300 pl-3">+{conns.length - 5} more</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Connections by layer */}
          {Object.keys(connectionsByLayer).length > 0 && (
            <div>
              <h3 className="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">All Connections</h3>
              <div className="space-y-2">
                {Object.entries(connectionsByLayer).map(([layer, conns]) => (
                  <ConnectionSection key={layer} layer={layer} connections={conns} defaultOpen={conns.length <= 5} />
                ))}
              </div>
            </div>
          )}

          {/* Entities sidebar — real data from DB */}
          {entities.length > 0 && (
            <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 bg-white dark:bg-neutral-800/30">
              <h3 className="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">
                Entities
                <span className="ml-1 text-[9px] font-normal opacity-60">({entities.length})</span>
                {entitiesLoading && <span className="ml-1 text-[9px] animate-pulse">…</span>}
              </h3>
              <div className="space-y-1.5 max-h-60 overflow-y-auto">
                {entities.map((entity, i) => (
                  <div key={i} className="group">
                    <button onClick={() => onOpenWiki?.(entity.entity_id, entity.english_name)}
                      className="w-full flex items-center gap-1.5 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded px-1 py-0.5 transition-colors text-left">
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                        entity.entity_type === 'person' ? 'bg-blue-400' :
                        entity.entity_type === 'place' ? 'bg-green-400' :
                        entity.entity_type === 'concept' ? 'bg-purple-400' :
                        'bg-neutral-400'
                      }`} />
                      <span className="text-[11px] font-medium text-neutral-700 dark:text-neutral-300 hover:text-blue-600 dark:hover:text-blue-400">
                        {entity.english_name}
                      </span>
                      <span className="text-[8px] text-neutral-400 dark:text-neutral-500 uppercase ml-auto">
                        {entity.entity_type}
                      </span>
                    </button>
                    {(entity.hebrew_name || entity.greek_name) && (
                      <div className="text-[9px] text-neutral-400 dark:text-neutral-500 ml-3">
                        {entity.hebrew_name && <span className="font-mono" dir="rtl">{entity.hebrew_name}</span>}
                        {entity.hebrew_name && entity.greek_name && <span className="mx-1">·</span>}
                        {entity.greek_name && <span className="font-mono">{entity.greek_name}</span>}
                      </div>
                    )}
                    <div className="text-[9px] text-neutral-400 dark:text-neutral-500 ml-3 flex items-center gap-1">
                      <span>{entity.total_mentions} mention{entity.total_mentions !== 1 ? 's' : ''}</span>
                      <span className="opacity-50">·</span>
                      <span className="truncate">
                        v{entity.verses?.map(v => v.verse).filter(Boolean).join(', v')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {entities.length === 0 && !entitiesLoading && data?.verses && (
            <div className="border border-dashed border-neutral-200 dark:border-neutral-700 rounded-lg p-3 bg-white dark:bg-neutral-800/30">
              <h3 className="text-[11px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1">Entities</h3>
              <p className="text-[10px] text-neutral-400 dark:text-neutral-500">No entity data indexed for this chapter</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
