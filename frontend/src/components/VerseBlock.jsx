import React, { useState, useMemo, useRef, useCallback, useEffect } from 'react'
import { cleanHebrew, lineHasChiasmRole } from '../utils'

const CHIASMUS_COLORS = {
  'A':  { border: 'border-red-400 dark:border-red-600',  bg: 'bg-red-50 dark:bg-red-900/20',   text: 'text-red-700 dark:text-red-300', bar: 'bg-red-300 dark:bg-red-600' },
  "A'": { border: 'border-red-400 dark:border-red-600',  bg: 'bg-red-50 dark:bg-red-900/20',   text: 'text-red-700 dark:text-red-300', bar: 'bg-red-300 dark:bg-red-600' },
  'B':  { border: 'border-blue-400 dark:border-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300', bar: 'bg-blue-300 dark:bg-blue-600' },
  "B'": { border: 'border-blue-400 dark:border-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300', bar: 'bg-blue-300 dark:bg-blue-600' },
  'C':  { border: 'border-green-400 dark:border-green-600',bg: 'bg-green-50 dark:bg-green-900/20',text: 'text-green-700 dark:text-green-300', bar: 'bg-green-300 dark:bg-green-600' },
  "C'": { border: 'border-green-400 dark:border-green-600',bg: 'bg-green-50 dark:bg-green-900/20',text: 'text-green-700 dark:text-green-300', bar: 'bg-green-300 dark:bg-green-600' },
}

const HEBREW_FONT = "font-['SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif]"

const CATEGORY_ICONS = {
  'cross-ref': '📖', 'tg': '🏷', 'heb': 'א', 'gr': 'α',
  'trn': '🔄', 'jst': '📜', 'ie': 'ℹ', 'or': '📝', 'gs': '📋', 'bd': '📚',
}
const CATEGORY_LABELS = {
  'cross-ref': 'Cross-reference', 'tg': 'Topical Guide', 'heb': 'Hebrew', 'gr': 'Greek',
  'trn': 'Translation', 'jst': 'JST', 'ie': 'Explanation', 'or': 'Other',
  'gs': 'Guide to Scriptures', 'bd': 'Bible Dictionary',
}

// ── Connection group display config ──

const CONNECTION_GROUPS = [
  { key: 'direct', icon: '📖', label: 'Direct', dot: 'bg-blue-500', light: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50' },
  { key: 'allusion', icon: '🔗', label: 'Allusion', dot: 'bg-sky-500', light: 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300 hover:bg-sky-200 dark:hover:bg-sky-900/50' },
  { key: 'echo', icon: '💬', label: 'Echo', dot: 'bg-gray-400', light: 'bg-gray-100 dark:bg-gray-800/50 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700/60' },
  { key: 'times', icon: '📅', label: 'Times', dot: 'bg-orange-500', light: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 hover:bg-orange-200 dark:hover:bg-orange-900/50' },
  { key: 'places', icon: '🌍', label: 'Places', dot: 'bg-emerald-500', light: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-200 dark:hover:bg-emerald-900/50' },
  { key: 'isaiah', icon: '🔍', label: 'Isaiah Pattern', dot: 'bg-violet-500', light: 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300 hover:bg-violet-200 dark:hover:bg-violet-900/50' },
]

function confidenceColor(c) {
  if (c == null) return 'bg-gray-300 dark:bg-gray-600'
  return c >= 0.8 ? 'bg-green-500' : c >= 0.5 ? 'bg-yellow-500' : 'bg-gray-400'
}

function confidenceTitle(c) {
  if (c == null) return 'confidence: unknown'
  return `confidence: ${Math.round(c * 100)}%`
}

// ── ConnectionPanel — unified collapsible panel per verse ──

function ConnectionPanel({ extraConnections, tskRefs, navigateToRef }) {
  const [panelOpen, setPanelOpen] = useState(false)
  const [filter, setFilter] = useState('')
  const [expandedSections, setExpandedSections] = useState({})

  // Compute total connection count
  const totalConns = useMemo(() => {
    let n = 0
    if (!extraConnections) return n
    for (const group of CONNECTION_GROUPS) {
      n += (extraConnections[group.key] || []).length
    }
    return n
  }, [extraConnections])

  // Toggle a section's expanded state
  const toggleSection = (key) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const filterLower = filter.toLowerCase()

  // Filter connections across all groups
  const filtered = useMemo(() => {
    if (!extraConnections) return []
    const result = []
    for (const group of CONNECTION_GROUPS) {
      const items = extraConnections[group.key] || []
      const matched = items.filter(c => {
        if (!filterLower) return true
        return (c.target || '').toLowerCase().includes(filterLower)
          || (c.type || '').toLowerCase().includes(filterLower)
      })
      if (matched.length > 0) {
        result.push({ ...group, items: matched, total: items.length })
      }
    }
    return result
  }, [extraConnections, filterLower])

  if (totalConns === 0 && (!tskRefs || tskRefs.length === 0)) return null

  // ── TSK summary ──
  const tskCount = tskRefs?.length || 0

  return (
    <div className="mt-1.5 px-1">
      {/* Header pill */}
      <button onClick={() => setPanelOpen(p => !p)}
        className="inline-flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full cursor-pointer
          bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300
          hover:bg-neutral-200 dark:hover:bg-neutral-700 border border-neutral-200 dark:border-neutral-700
          transition-all select-none">
        <span>📖 Connections</span>
        <span className="font-mono text-[9px] opacity-60">{totalConns}</span>
        {tskCount > 0 && <span className="font-mono text-[9px] text-purple-500">ᵗ{tskCount}</span>}
        <span className="ml-0.5">{panelOpen ? '▲' : '▼'}</span>
      </button>

      {/* Expanded panel */}
      {panelOpen && (
        <div className="mt-2 p-2.5 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-sm">
          {/* Filter */}
          <div className="relative mb-2">
            <input type="text" value={filter} onChange={e => setFilter(e.target.value)}
              placeholder="🔍 filter connections..."
              className="w-full text-[11px] px-2 py-1.5 rounded border border-neutral-200 dark:border-neutral-600
                bg-neutral-50 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200
                outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
            />
            {filter && (
              <button onClick={() => setFilter('')}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 cursor-pointer text-xs">
                ✕
              </button>
            )}
          </div>

          {/* Grouped sections */}
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {filtered.map(group => (
              <div key={group.key}>
                {/* Section header */}
                <button onClick={() => toggleSection(group.key)}
                  className="w-full flex items-center gap-1.5 text-[11px] px-2 py-1.5 rounded
                    hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer transition-colors text-left">
                  <span className="font-semibold text-neutral-600 dark:text-neutral-400">
                    {group.icon} {group.label}
                  </span>
                  <span className="text-[9px] font-mono text-neutral-400 dark:text-neutral-500 ml-auto">
                    {expandedSections[group.key] ? '▲' : '▼'} {group.items.length}/{group.total}
                  </span>
                </button>

                {/* Items */}
                {expandedSections[group.key] && (
                  <div className="ml-2 space-y-0.5 pb-1">
                    {group.items.map((c, i) => (
                      <button key={i} onClick={e => navigateToRef(c.target, e)}
                        onMouseDown={e => { if (e.button === 1) { e.preventDefault(); navigateToRef(c.target, e) } }}
                        className="w-full flex items-center gap-2 text-[10px] px-2 py-1.5 rounded cursor-pointer
                          hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors text-left"
                        title={`${c.target} · Click to navigate · Ctrl+click for new tab`}>
                        {/* Confidence dot */}
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${confidenceColor(c.confidence)}`}
                          title={confidenceTitle(c.confidence)} />
                        {/* Type label */}
                        <span className="text-neutral-500 dark:text-neutral-400 shrink-0 min-w-[3.5rem]">
                          {c.type.replace(/_/g, ' ')}
                        </span>
                        {/* Target */}
                        <span className="font-mono font-medium text-neutral-700 dark:text-neutral-300 truncate">
                          {c.target}
                        </span>
                        {/* Arrow */}
                        <span className="ml-auto text-neutral-300 dark:text-neutral-600 shrink-0">↪</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Empty state */}
          {filtered.length === 0 && filter && (
            <p className="text-[10px] text-neutral-400 text-center py-2">No connections match "{filter}"</p>
          )}

          {/* TSK summary */}
          {tskCount > 0 && (
            <div className="mt-1.5 pt-1.5 border-t border-neutral-100 dark:border-neutral-700">
              <span className="text-[10px] text-purple-600 dark:text-purple-400">
                ᵗ {tskCount} Treasury of Scripture Knowledge cross-references available
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function VerseBlock({ verse, toggles, poetryMode, chiasms, highlights, footnotes, tskRefs, reviewed, onToggleReview, wordData, extraConnections }) {
  const [expanded, setExpanded] = useState(false)
  const [openFn, setOpenFn] = useState(null)
  const [openTsk, setOpenTsk] = useState(false)
  const [tooltip, setTooltip] = useState(null) // { fn, x, y } | null
  const tooltipRef = useRef(null)
  const tooltipTimer = useRef(null)
  const lines = verse.lines || []
  const hasMultipleLines = lines.length >= 2
  const showLines = poetryMode && hasMultipleLines
  const chiasmRole = toggles.chiasmus ? lineHasChiasmRole(verse.verse, chiasms) : null
  const chColor = chiasmRole ? CHIASMUS_COLORS[chiasmRole.label] : null
  const intraPar = verse.intra_parallelisms || []
  const isHighlighted = highlights?.includes(verse.verse)

  // Navigate to a verse reference (left click = current tab, Ctrl+click = new tab)
  const navigateToRef = (targetVerse, e) => {
    const parts = targetVerse.split('.')
    if (parts.length < 2) return
    const book = parts[0]
    const chapter = parseInt(parts[1])
    if (e.ctrlKey || e.metaKey) {
      window.dispatchEvent(new CustomEvent('scripture-open-tab', { detail: { book, chapter } }))
    } else {
      window.dispatchEvent(new CustomEvent('scripture-navigate', { detail: { book, chapter } }))
    }
  }

  return (
    <div className={`mb-5 ${isHighlighted ? 'ring-2 ring-amber-400 dark:ring-amber-600 rounded-lg p-2 -m-2' : ''}`}>
      {/* Content — verse number inline with text */}
      <div className={`rounded-lg border transition-all relative ${showLines ? 'border-neutral-200 dark:border-neutral-700' : 'border-transparent'}`}>
        {showLines ? (
          <div className="flex">
            {chColor && toggles.chiasmus && <div className={`w-1 shrink-0 rounded-l ${chColor.bar}`} />}
            <div className="flex-1 min-w-0 py-1">
              {lines.map((line, i) => (
                <div key={i} className="flex items-start gap-2 px-3 py-1.5 border-b border-neutral-100 dark:border-neutral-800 last:border-b-0">
                  <span className="text-[10px] text-neutral-300 dark:text-neutral-600 font-mono w-4 shrink-0 mt-1">{lines.length > 1 ? i + 1 : ''}</span>
                  <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">{line.english}</p>
                </div>
              ))}
            </div>
            <div className="w-px bg-neutral-200 dark:border-neutral-700 shrink-0" />
            <div className="flex-1 min-w-0 py-1" dir="rtl">
              {lines.map((line, i) => (
                <div key={i} className="flex items-start gap-2 px-3 py-1.5 border-b border-neutral-100 dark:border-neutral-800 last:border-b-0">
                  <p className={`text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 ${HEBREW_FONT}`} style={{ fontSize: '1.05em' }} dir="rtl">{cleanHebrew(line.hebrew)}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex relative group">
            {chColor && toggles.chiasmus && <div className={`w-1 shrink-0 rounded-l ${chColor.bar}`} />}
            <div className="flex-1 min-w-0 px-3 py-2">
              <div className="flex items-start gap-1.5">
                {/* Verse number + chiasm label inline */}
                <span className="text-xs text-neutral-400 dark:text-neutral-500 font-mono select-none mt-0.5 shrink-0 flex items-center">
                  <span onClick={(e) => { e.stopPropagation(); onToggleReview?.() }}
                    className={`inline-block w-2.5 h-2.5 rounded-sm mr-1 cursor-pointer border transition-colors
                      ${reviewed ? 'bg-blue-500 dark:bg-blue-400 border-blue-500 dark:border-blue-400' : 'border-neutral-300 dark:border-neutral-600 hover:border-blue-400'}`}
                    title={reviewed ? 'Mark as unread' : 'Mark as read'} />
                  {verse.verse}
                  {isHighlighted && <span className="text-amber-500 dark:text-amber-400 ml-0.5">★</span>}
                  {chiasmRole && toggles.chiasmus && (
                    <span className={`ml-1 text-[9px] font-bold ${chColor?.text || 'text-indigo-600 dark:text-indigo-400'}`}>
                      {chiasmRole.label}
                    </span>
                  )}
                  {/* TSK badge */}
                  {tskRefs?.length > 0 && (
                    <button onClick={(e) => { e.stopPropagation(); setOpenTsk(!openTsk) }}
                      className="ml-1 text-[9px] font-mono px-1 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-300 cursor-pointer hover:bg-purple-200 dark:hover:bg-purple-900/60"
                      title="Treasury of Scripture Knowledge cross-references">
                      ᵗ{tskRefs.length}
                    </button>
                  )}
                </span>
                {/* Verse text with footnote markers */}
                <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 flex-1 min-w-0">
                  {renderWithFootnotes(verse.text_english, footnotes, openFn, setOpenFn, setTooltip, tooltip)}
                </p>
              </div>
            </div>
            {verse.text_hebrew && (
              <>
                <div className="w-px bg-neutral-200 dark:bg-neutral-700 shrink-0" />
                <div className="flex-1 min-w-0 px-3 py-2">
                  <p className={`text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 ${HEBREW_FONT}`} style={{ fontSize: '1.05em' }} dir="rtl">
                    {wordData ? renderHebrewWithAnnotations(verse.text_hebrew, wordData, toggles) : cleanHebrew(verse.text_hebrew)}
                  </p>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Footnote popup */}
      {openFn && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4 bg-black/20 dark:bg-black/50"
          onClick={() => setOpenFn(null)}>
          <div className="bg-white dark:bg-neutral-800 rounded-t-xl sm:rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700
            w-full sm:max-w-md mx-0 sm:mx-4 p-4 max-h-[60vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                {CATEGORY_ICONS[openFn.category]} {CATEGORY_LABELS[openFn.category]}
              </span>
              <button onClick={() => setOpenFn(null)}
                className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-lg leading-none">&times;</button>
            </div>
            {openFn.context_word && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-3">
                Annotated word: <span className="font-medium italic text-neutral-700 dark:text-neutral-300">{openFn.context_word}</span>
              </p>
            )}
            {openFn.references?.length > 0 ? (
              <div className="space-y-1.5">
                {openFn.references.map((ref, i) => (
                  <a key={i} href={ref.href} target="_blank" rel="noopener noreferrer"
                    className="block text-sm px-3 py-2.5 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300
                      hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors cursor-pointer border border-blue-100 dark:border-blue-900/30">
                    {ref.text || ref.href}
                  </a>
                ))}
              </div>
            ) : openFn.body_html ? (
              <div className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed" dangerouslySetInnerHTML={{ __html: openFn.body_html }} />
            ) : null}
            <div className="mt-3 pt-2 border-t border-neutral-100 dark:border-neutral-700 text-[10px] text-neutral-400 dark:text-neutral-500 flex gap-2 items-center">
              <span className="font-mono">{openFn.marker}</span>
              <span>·</span>
              <span>{openFn.verse_id || ''}</span>
              <span className="ml-auto">click outside to close</span>
            </div>
          </div>
        </div>
      )}

      {/* Rich tooltip on hover over footnote markers/words */}
      {tooltip && (
        <FootnoteTooltip fn={tooltip.fn} x={tooltip.x} y={tooltip.y} onClose={() => setTooltip(null)} />
      )}

      {/* TSK popup */}
      {openTsk && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4 bg-black/20 dark:bg-black/50"
          onClick={() => setOpenTsk(false)}>
          <div className="bg-white dark:bg-neutral-800 rounded-t-xl sm:rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700
            w-full sm:max-w-md mx-0 sm:mx-4 p-4 max-h-[60vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                ᵗ Treasury of Scripture Knowledge ({tskRefs.length} refs)
              </span>
              <button onClick={() => setOpenTsk(false)}
                className="text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-lg leading-none">&times;</button>
            </div>
            <div className="space-y-1">
              {tskRefs.map((ref, i) => (
                <div key={i} onClick={(e) => navigateToRef(ref.target_verse, e)}
                  onMouseDown={(e) => { if (e.button === 1) { e.preventDefault(); navigateToRef(ref.target_verse, e) } }}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer
                    bg-neutral-50 dark:bg-neutral-900/50 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-700
                    border border-neutral-200 dark:border-neutral-700 transition-all"
                  title="Click to navigate • Ctrl+click for new tab • Middle-click for new tab">
                  <span className="text-[11px] font-mono font-bold text-blue-600 dark:text-blue-400 shrink-0 min-w-[7rem]">{ref.target_verse}</span>
                  <span className="text-xs text-neutral-500 dark:text-neutral-400 shrink-0 mr-1">
                    {ref.type === 'direct_quotation' ? '📖 direct' : ref.type === 'allusion' ? '🔗 allusion' : '📝 echo'}
                  </span>
                  <span className="ml-auto text-[9px] text-neutral-400 dark:text-neutral-500 shrink-0">↪</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-2 border-t border-neutral-100 dark:border-neutral-700 flex justify-between text-[10px] text-neutral-400 dark:text-neutral-500">
              <span>Click to navigate · Ctrl+click for new tab</span>
              <span className="text-blue-600 dark:text-blue-400 cursor-pointer hover:underline" onClick={() => setOpenTsk(false)}>Close</span>
            </div>
          </div>
        </div>
      )}

      {/* Parallelism badges */}
      {toggles.synonymous && intraPar.filter(p => p.type === 'parallel_synonymous').length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1.5 px-1">
          {intraPar.filter(p => p.type === 'parallel_synonymous').map((p, i) => (
            <span key={i} className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">≡ synonymous L{p.line_a + 1}↔L{p.line_b + 1}</span>
          ))}
        </div>
      )}
      {toggles.antithetic && intraPar.filter(p => p.type === 'parallel_antithetic').length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1.5 px-1">
          {intraPar.filter(p => p.type === 'parallel_antithetic').map((p, i) => (
            <span key={i} className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300">⇄ antithetic L{p.line_a + 1}↔L{p.line_b + 1}</span>
          ))}
        </div>
      )}
      {verse.parallelisms?.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1 px-1">
          {toggles.antithetic && verse.parallelisms.filter(p => p.type === 'parallel_antithetic').map((p, i) => (
            <span key={i} className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300">⇄ antithetic w/ v{p.paired_verse}</span>
          ))}
          {toggles.synonymous && verse.parallelisms.filter(p => p.type === 'parallel_synonymous').map((p, i) => (
            <span key={i} className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">≡ synonymous w/ v{p.paired_verse}</span>
          ))}
          {toggles.synthetic && verse.parallelisms.filter(p => p.type === 'parallel_synthetic').map((p, i) => (
            <span key={i} className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300">→ synthetic w/ v{p.paired_verse}</span>
          ))}
        </div>
      )}

      {/* Unified connections panel — grouped, filterable, clickable */}
      <ConnectionPanel extraConnections={extraConnections} tskRefs={tskRefs} navigateToRef={navigateToRef} />

      {/* Expand */}
      {expanded && (
        <div className="mt-2 ml-1 p-3 bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 rounded-lg text-xs text-neutral-600 dark:text-neutral-400">
          <p className="font-medium text-neutral-700 dark:text-neutral-300 mb-1.5">Details</p>
          {footnotes?.map((fn, i) => (
            <div key={i} className="flex items-start gap-2 py-0.5">
              <span className={`text-[10px] px-1 rounded font-mono ${fn.category === 'cross-ref' ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20' : fn.category === 'tg' ? 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20' : 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20'}`}>
                {CATEGORY_ICONS[fn.category] || '•'}
              </span>
              <span className="text-neutral-500 dark:text-neutral-400">{fn.context_word}</span>
              <span className="text-neutral-300 dark:text-neutral-600">→</span>
              <span className="text-neutral-600 dark:text-neutral-300">{CATEGORY_LABELS[fn.category] || fn.category}</span>
            </div>
          ))}
        </div>
      )}

      <button onClick={() => setExpanded(!expanded)}
        className="mt-0.5 text-[10px] text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer px-1">
        {expanded ? '▲ less' : '▼ more'}
      </button>
    </div>
  )
}

// ── Rich footnote tooltip (hover) ──

function FootnoteTooltip({ fn, x, y, onClose }) {
  const [verseTexts, setVerseTexts] = useState({})
  const refs = fn.references || []

  // Fetch verse text for scripture references
  useEffect(() => {
    const scriptureRefs = refs.filter(r => r.type === 'scripture' && r.href)
    for (const ref of scriptureRefs) {
      const match = ref.href.match(/\/([^/]+)\.(\d+)\.(\d+)/)
      if (match) {
        const verseId = `${match[1]}.${match[2]}.${match[3]}`
        if (!verseTexts[verseId]) {
          fetch(`/api/v1/verses/${verseId}`)
            .then(r => r.json())
            .then(d => {
              if (d.ok) setVerseTexts(prev => ({ ...prev, [verseId]: d.data.text_english }))
            })
            .catch(() => {})
        }
      }
    }
  }, [fn])

  // Adjust position to stay within viewport
  const tooltipX = Math.min(x, window.innerWidth - 320)
  const tooltipY = Math.min(y, window.innerHeight - 250)

  return (
    <div className="fixed z-[60 pointer-events-none"
      style={{ left: tooltipX + 12, top: tooltipY - 10 }}>
      <div className="bg-white dark:bg-neutral-800 rounded-lg shadow-xl border border-neutral-200 dark:border-neutral-700
        p-3 max-w-xs text-xs leading-relaxed"
        onMouseEnter={() => {}}>
        {/* Header */}
        <div className="flex items-center gap-1.5 mb-1.5 font-medium text-neutral-800 dark:text-neutral-200">
          <span>{CATEGORY_ICONS[fn.category] || '📄'}</span>
          <span>{CATEGORY_LABELS[fn.category] || fn.category}</span>
        </div>
        {/* Context word */}
        {fn.context_word && (
          <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mb-1">
            Word: <span className="italic font-medium text-neutral-700 dark:text-neutral-300">{fn.context_word}</span>
          </p>
        )}
        {/* References */}
        {refs.length > 0 && (
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {refs.slice(0, 4).map((ref, i) => {
              const match = ref.href?.match(/\/([^/]+)\.(\d+)\.(\d+)/)
              const verseId = match ? `${match[1]}.${match[2]}.${match[3]}` : null
              const text = verseId ? verseTexts[verseId] : null
              return (
                <div key={i} className="text-[10px] text-neutral-600 dark:text-neutral-400">
                  <span className="font-medium text-neutral-700 dark:text-neutral-300">{ref.text || ref.href}</span>
                  {text && <p className="mt-0.5 text-neutral-500 dark:text-neutral-400 line-clamp-2">{text}</p>}
                </div>
              )
            })}
            {refs.length > 4 && (
              <p className="text-[9px] text-neutral-400 dark:text-neutral-500">+{refs.length - 4} more references</p>
            )}
          </div>
        )}
        {/* No references — show body HTML */}
        {refs.length === 0 && fn.body_html && (
          <div className="text-[10px] text-neutral-500 dark:text-neutral-400 line-clamp-3" dangerouslySetInnerHTML={{ __html: fn.body_html }} />
        )}
        <p className="mt-1.5 text-[8px] text-neutral-400 dark:text-neutral-500">Click to open full details</p>
      </div>
    </div>
  )
}

// ── Text renderer with LDS-style footnote markers + hover tooltips ──

function fnTooltip(fn) {
  const label = CATEGORY_LABELS[fn.category] || fn.category
  const icon = CATEGORY_ICONS[fn.category] || '📄'
  const refs = (fn.references || []).slice(0, 2)
  let tip = `${icon} ${label}`
  if (fn.context_word) tip += `\nWord: "${fn.context_word}"`
  if (refs.length > 0) tip += `\n→ ${refs.map(r => r.text || r.href).join(', ')}`
  if (refs.length < (fn.references || []).length) tip += `\n… +${(fn.references || []).length - refs.length} more`
  return tip
}

function renderWithFootnotes(text, footnotes, openFn, setOpenFn, setTooltip, activeTooltip) {
  if (!footnotes?.length) return text

  // ── Separate single-word vs multi-word footnotes ──
  const singleFns = []
  const multiFns = []
  const letterFns = []

  for (const fn of footnotes) {
    const raw = (fn.context_word || '').trim()
    if (!raw) continue
    if (raw.length === 1) {
      if (fn.word_index != null) letterFns.push({ ...fn, wordIdx: fn.word_index })
      continue
    }
    const words = raw.split(/\s+/)
    if (words.length === 1) {
      singleFns.push(fn)
    } else {
      const clean = raw.toLowerCase().replace(/[^a-z\u0590-\u05ff' ]/g, '').trim()
      if (clean) {
        let group = multiFns.find(g => g.clean === clean)
        if (!group) {
          group = { clean, words: clean.split(/\s+/), fns: [] }
          multiFns.push(group)
        }
        group.fns.push(fn)
      }
    }
  }

  const fnMap = {}
  for (const fn of singleFns) {
    const cleanWord = fn.context_word.toLowerCase().replace(/[^a-z\u0590-\u05ff']/g, '')
    const markerLetter = fn.marker?.split('_')[1] || '?'
    if (!fnMap[cleanWord]) fnMap[cleanWord] = []
    if (!fnMap[cleanWord].some(f => f.marker === markerLetter)) {
      fnMap[cleanWord].push({ ...fn, markerLetter, cleanWord })
    }
  }

  const hasSingle = Object.keys(fnMap).length > 0
  const hasMulti = multiFns.length > 0
  const hasLetter = letterFns.length > 0
  if (!hasSingle && !hasMulti && !hasLetter) return text

  multiFns.sort((a, b) => b.words.length - a.words.length)
  const tokens = text.split(/(\s+)/)

  const showTooltip = (fn, e) => {
    if (setTooltip) setTooltip({ fn, x: e.clientX, y: e.clientY })
  }
  const hideTooltip = () => { if (setTooltip) setTooltip(null) }

  const renderToken = (token, matches, key) => (
    <React.Fragment key={key}>
      {matches.map((m, j) => (
        <sup key={j}
          onClick={(e) => { e.stopPropagation(); setOpenFn(m) }}
          onMouseEnter={(e) => showTooltip(m, e)}
          onMouseLeave={hideTooltip}
          className="fn-marker"
        >{m.markerLetter}</sup>
      ))}
      <span onClick={(e) => { e.stopPropagation(); setOpenFn(matches[0]) }}
        onMouseEnter={(e) => showTooltip(matches[0], e)}
        onMouseLeave={hideTooltip}
        className="fn-word">
        {token}
      </span>
    </React.Fragment>
  )

  const renderMerged = (wordTokens, sepTokens, matches, key) => {
    const fullText = wordTokens.map((t, i) => (i > 0 ? sepTokens[i - 1] || '' : '') + t).join('')
    return (
      <React.Fragment key={key}>
        {matches.map((m, j) => (
          <sup key={j}
            onClick={(e) => { e.stopPropagation(); setOpenFn(m) }}
            onMouseEnter={(e) => showTooltip(m, e)}
            onMouseLeave={hideTooltip}
            className="fn-marker"
          >{m.markerLetter}</sup>
        ))}
        <span onClick={(e) => { e.stopPropagation(); setOpenFn(matches[0]) }}
          onMouseEnter={(e) => showTooltip(matches[0], e)}
          onMouseLeave={hideTooltip}
          className="fn-word">
          {fullText}
        </span>
      </React.Fragment>
    )
  }

  const result = []
  let i = 0
  let outputKey = 0
  let wordCursor = 0

  while (i < tokens.length) {
    const token = tokens[i]
    if (!token.trim()) {
      result.push(token)
      i++
      continue
    }

    let matched = false

    if (hasMulti && !matched) {
      for (const group of multiFns) {
        const n = group.words.length
        const wordPos = []
        const words = []
        let wi = i
        for (let w = 0; w < n; w++) {
          while (wi < tokens.length && !tokens[wi]?.trim()) wi++
          if (wi >= tokens.length) break
          wordPos.push(wi)
          words.push(tokens[wi])
          wi++
        }
        if (words.length !== n) continue

        const phrase = words.map(w =>
          w.toLowerCase().replace(/[^a-z\u0590-\u05ff']/g, '')
        ).join(' ')
        if (phrase !== group.clean) continue

        const seps = []
        for (let s = i + 1; s < wordPos[wordPos.length - 1]; s++) {
          if (!tokens[s].trim()) seps.push(tokens[s])
        }
        const matches = group.fns.map(fn => {
          const ml = fn.marker?.split('_')[1] || '?'
          return { ...fn, markerLetter: ml, cleanWord: group.clean }
        })
        result.push(renderMerged(words, seps, matches, outputKey++))
        i = wordPos[wordPos.length - 1] + 1
        wordCursor += n
        matched = true
        break
      }
    }

    if (matched) continue

    if (hasLetter) {
      const lf = letterFns.find(l => l.wordIdx === wordCursor)
      if (lf) {
        const ml = lf.marker?.split('_')[1] || '?'
        result.push(renderToken(token, [{ ...lf, markerLetter: ml, cleanWord: lf.context_word }], outputKey++))
        wordCursor++
        i++
        continue
      }
    }

    if (hasSingle) {
      const ct = token.toLowerCase().replace(/[^a-z\u0590-\u05ff']/g, '')
      const matches = fnMap[ct]
      if (matches?.length) {
        result.push(renderToken(token, matches, outputKey++))
        wordCursor++
        i++
        continue
      }
    }

    result.push(token)
    wordCursor++
    i++
  }

  return result
}

// ── Hebrew word-level annotation renderer (gematria, lemma) ──

const DIVINE_NAME_VALUES = [26, 86, 65, 136, 113, 300, 211, 395, 586, 277, 249, 371, 481, 430, 72, 199, 192, 201]

function renderHebrewWithAnnotations(hebrewText, wordData, toggles) {
  const cleaned = cleanHebrew(hebrewText)
  if (!wordData?.length) return cleaned

  const wordMap = {}
  for (const w of wordData) {
    if (w.word_index !== null && w.word_index !== undefined) {
      wordMap[w.word_index] = w
    }
  }

  const tokens = cleaned.split(/(\s+)/)
  let wordIdx = 0
  return tokens.map((token, i) => {
    if (!token.trim() || !/[\u0590-\u05FF]/.test(token)) return token
    const w = wordMap[wordIdx]
    wordIdx++
    if (!w) return token

    const isDivine = DIVINE_NAME_VALUES.includes(w.gematria?.standard)
    const showGematria = toggles?.gematria
    const showLemma = toggles?.lemma

    let tooltipParts = []
    if (showGematria && w.gematria?.standard) tooltipParts.push(`Gematria ${w.gematria.standard}`)
    if (isDivine) tooltipParts.push(`Divine Name (value ${w.gematria?.standard})`)
    if (showLemma && w.lemma) tooltipParts.push(`Strong's H${w.lemma}`)
    if (w.morph) tooltipParts.push(`Morph: ${w.morph}`)
    const tip = tooltipParts.join(' · ')

    return (
      <React.Fragment key={i}>
        {showLemma && w.lemma && (
          <sup className="text-[8px] text-purple-500 dark:text-purple-400 font-mono cursor-help select-none"
            title={`H${w.lemma} · ${w.morph || ''}`}>λ</sup>
        )}
        {isDivine && (
          <span className="inline-block px-0.5 rounded bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-200"
            title={tip}>
            {token}
          </span>
        )}
        {!isDivine && (
          <span className="cursor-help" title={tip}>
            {showGematria && w.gematria?.standard && (
              <sup className="text-[8px] text-blue-500 dark:text-blue-400 font-mono select-none">{w.gematria.standard}</sup>
            )}
            {token}
          </span>
        )}
      </React.Fragment>
    )
  })
}