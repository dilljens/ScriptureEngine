import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { getChapter } from '../api'
import { parseAndFuzzy, getChapters } from '../refParser'

const TYPE_ICONS = {
  navigate: '📖', search: '🔍', chat: '💬', command: '🎯',
  toggle: '🔘', history: '🕐', help: '❓', structure: '⟷',
  dark: '🌙', font: '🔤', error: '⚠️', autocomplete: '?',
  collection: '🗂️', library: '🗂️',
}

const TYPE_COLORS = {
  navigate: 'text-blue-600 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/40',
  search: 'text-green-600 dark:text-green-300 bg-green-100 dark:bg-green-900/40',
  chat: 'text-purple-600 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/40',
  command: 'text-amber-600 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40',
  toggle: 'text-teal-600 dark:text-teal-300 bg-teal-100 dark:bg-teal-900/40',
  history: 'text-neutral-600 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-700/50',
  help: 'text-indigo-600 dark:text-indigo-300 bg-indigo-100 dark:bg-indigo-900/40',
  autocomplete: 'text-neutral-500 bg-neutral-100 dark:bg-neutral-700/50',
  collection: 'text-amber-600 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40',
  library: 'text-blue-600 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/40',
}

const WORK_LABEL = {
  ot: 'Old Testament', nt: 'New Testament', bom: 'Book of Mormon',
  dc: 'Doctrine & Covenants', pgp: 'Pearl of Great Price',
  dss: 'Dead Sea Scrolls', apoc: 'Apocrypha', pseu: 'Pseudepigrapha',
  expanded: 'Expanded Canon',
}

/**
 * CommandInput — slash-command palette ([/dark /font /toggle /history
 * /structure /search /cfm /conference /collections /library ...]).
 *
 * Extracted from App.jsx (god-file decomposition, sentrux no_god_files).
 */
export default function CommandInput({ open, onClose, onNavigate, onChat, allBooks, onCommand, onToggle, onToggleHistory, onToggleStructure }) {
const [val, setVal] = useState('')
const [results, setResults] = useState([])
const [resultType, setResultType] = useState('empty')
const [sel, setSel] = useState(0)
const [showChapters, setShowChapters] = useState(false)  // tab toggles chapter preview
const [previewCh, setPreviewCh] = useState(1)
const [previewVerses, setPreviewVerses] = useState([])
const [previewLoading, setPreviewLoading] = useState(false)
const previewCache = useRef({})
const inputRef = useRef(null)
const resultsRef = useRef(null)

// Live chapter preview (fzf --preview style): show the first verses of the
// selected book/chapter when the chapter preview is open.
const loadPreview = useCallback(async (book, ch) => {
  if (!book) return
  setPreviewCh(ch)
  const key = `${book}.${ch}`
  if (previewCache.current[key]) {
    setPreviewVerses(previewCache.current[key])
    return
  }
  setPreviewLoading(true)
  try {
    const r = await getChapter(key)
    const verses = r.data?.verses?.slice(0, 6) || []
    previewCache.current[key] = verses
    setPreviewVerses(verses)
  } catch {
    setPreviewVerses([])
  } finally {
    setPreviewLoading(false)
  }
}, [])

useEffect(() => {
  if (open) { setVal(''); setResults([]); setResultType('empty'); setSel(0); setShowChapters(false); setTimeout(() => inputRef.current?.focus(), 50) }
}, [open])

const selResult = results[sel]?.type === 'navigate' ? results[sel] : null
useEffect(() => {
  if (showChapters && selResult?.book) loadPreview(selResult.book, selResult.chapter || 1)
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [showChapters, sel])

// Show all books when query is empty (fzf default behavior)
const getAllBooksResults = useCallback(() => {
  if (!allBooks?.length) return []
  const out = []
  let lastWork = ''
  for (const b of allBooks) {
    if (b.workLabel !== lastWork) {
      out.push({ type: 'header', label: `▸ ${b.workLabel}`, workId: b.workId })
      lastWork = b.workLabel
    }
    out.push({
      type: 'navigate',
      matchIdxs: [],
      score: Infinity,
      workId: b.workId,
      workLabel: b.workLabel,
      book: b.bookId,
      chapter: 1,
      label: `${b.workLabel} → ${b.bookTitle}`,
      bookTitle: b.bookTitle,
    })
  }
  return out
}, [allBooks])

const handleChange = (v) => {
  setVal(v)
  setSel(0)
  setShowChapters(false)
  if (!v.trim()) {
    setResults(getAllBooksResults())
    setResultType('list')
    return
  }
  const parsed = parseAndFuzzy(v, allBooks || [])
  setResultType(parsed.type)
  setResults(parsed.results || [])
}

const executeResult = (r) => {
  if (!r) return
  switch (r.type) {
    case 'navigate':
      onNavigate(r.book, r.chapter, r.newTab || false)
      onClose(); break
    case 'chat':
      onChat(r.message || '')
      onClose(); break
    case 'search':
      onCommand?.({ type: 'search', query: r.query })
      onClose(); break
    case 'dark':
      onCommand?.({ type: 'dark' })
      onClose(); break
    case 'font':
      onCommand?.({ type: 'font', direction: r.direction, size: r.size })
      onClose(); break
    case 'toggle':
      if (r.toggle) onCommand?.({ type: 'toggle', toggle: r.toggle })
      onClose(); break
    case 'history':
      onCommand?.({ type: 'history' })
      onClose(); break
    case 'structure':
      onCommand?.({ type: 'structure' })
      onClose(); break
    case 'collection':
      onCommand?.({ type: 'collection', target: r.target })
      onClose(); break
    case 'library':
      onCommand?.({ type: 'library' })
      onClose(); break
  }
}

const executeCurrent = () => {
  const r = results[sel]
  if (r?.type === 'header') return
  if (r) executeResult(r)
}

const toggleChapterPreview = () => {
  const r = results[sel]
  if (r?.type === 'navigate' && r.book) {
    setShowChapters(p => !p)
  }
}

if (!open) return null

const workColors = {
  'ot': 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20',
  'nt': 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20',
  'bom': 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20',
  'dc': 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20',
  'pgp': 'text-pink-600 dark:text-pink-400 bg-pink-50 dark:bg-pink-900/20',
  'dss': 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20',
  'apoc': 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20',
  'pseu': 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20',
  'expanded': 'text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20',
}

const workHeaderColors = {
  'ot': 'bg-amber-50/50 dark:bg-amber-900/10 text-amber-700 dark:text-amber-300',
  'nt': 'bg-blue-50/50 dark:bg-blue-900/10 text-blue-700 dark:text-blue-300',
  'bom': 'bg-green-50/50 dark:bg-green-900/10 text-green-700 dark:text-green-300',
  'dc': 'bg-purple-50/50 dark:bg-purple-900/10 text-purple-700 dark:text-purple-300',
  'pgp': 'bg-pink-50/50 dark:bg-pink-900/10 text-pink-700 dark:text-pink-300',
  'dss': 'bg-yellow-50/50 dark:bg-yellow-900/10 text-yellow-700 dark:text-yellow-300',
  'apoc': 'bg-rose-50/50 dark:bg-rose-900/10 text-rose-700 dark:text-rose-300',
  'pseu': 'bg-indigo-50/50 dark:bg-indigo-900/10 text-indigo-700 dark:text-indigo-300',
  'expanded': 'bg-teal-50/50 dark:bg-teal-900/10 text-teal-700 dark:text-teal-300',
}

function HighlightedLabel({ label, matchIdxs }) {
  if (!matchIdxs || matchIdxs.length === 0) return <>{label}</>
  const chars = [...label]
  const sorted = [...new Set(matchIdxs)].filter(i => i < label.length).sort((a, b) => a - b)
  if (sorted.length === 0) return <>{label}</>
  const parts = []
  let last = 0
  for (const idx of sorted) {
    if (idx > last) parts.push(chars.slice(last, idx).join(''))
    parts.push(<mark key={idx} className="bg-amber-200 dark:bg-amber-600/60 text-inherit rounded-sm font-semibold">{chars[idx]}</mark>)
    last = idx + 1
  }
  if (last < chars.length) parts.push(chars.slice(last).join(''))
  return <>{parts}</>
}

return (
  <div role="dialog" aria-modal="true" aria-label="Command palette" className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]" onClick={onClose}>
    <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-300 dark:border-neutral-700 w-full max-w-xl mx-4 flex flex-col overflow-hidden"
      onClick={e => e.stopPropagation()}>

      {/* Results area (fzf: results above input) */}
      <div ref={resultsRef} className="overflow-y-auto max-h-[50vh] min-h-0" style={{ scrollBehavior: 'smooth' }}>
        {results.length === 0 && val.trim() === '' && (
          <div className="px-4 py-8 text-center text-sm text-neutral-400 dark:text-neutral-500">Loading books...</div>
        )}

        {results.length > 0 && results.map((r, i) => {
          // Section header for work groups
          if (r.type === 'header') {
            return (
              <div key={r.workId || i}
                className={`px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider ${workHeaderColors[r.workId] || 'text-neutral-400 bg-neutral-50 dark:bg-neutral-800/50'}`}>
                {r.label}
              </div>
            )
          }

          const isSelected = i === sel
          const rel = r.score !== undefined && r.score !== Infinity ? Math.min(r.score / 150, 1) : 0

          return (
            <div key={i}>
              <button
                onClick={() => executeResult(r)}
                onMouseEnter={() => { setSel(i); setShowChapters(false) }}
                className={`w-full text-left px-4 py-2 flex items-center gap-2.5 cursor-pointer text-sm transition-colors relative
                  ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-neutral-50 dark:hover:bg-neutral-700/50'}`}>

                {/* Relevance line (left edge) — only for fuzzy matches */}
                {r.score !== undefined && r.score !== Infinity && (
                  <span className="absolute left-0 top-1 bottom-1 w-0.5 rounded-r transition-all"
                    style={{
                      backgroundColor: rel > 0.7 ? '#22c55e' : rel > 0.4 ? '#eab308' : '#6b7280',
                      opacity: 0.3 + rel * 0.7,
                    }}
                  />
                )}

                {/* Icon + type badge */}
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-xs w-4 text-center">{r.icon || TYPE_ICONS[r.type] || '•'}</span>
                  <span className={`text-[8px] px-1 py-0.5 rounded font-medium ${TYPE_COLORS[r.type] || 'text-neutral-400 bg-neutral-100 dark:bg-neutral-700'}`}>
                    {r.type === 'navigate' ? 'go' : r.type === 'chat' ? 'chat' : r.type === 'search' ? 'find' : r.type === 'command' ? 'cmd' : r.type === 'toggle' ? 'toggle' : r.type === 'history' ? 'hist' : r.type === 'help' ? 'help' : r.type === 'autocomplete' ? '?' : r.type}
                  </span>
                </div>

                {/* Work badge */}
                {r.workId && (
                  <span className={`text-[9px] font-mono px-1 rounded shrink-0 ${workColors[r.workId] || 'text-neutral-500 bg-neutral-100'}`}>
                    {WORK_LABEL[r.workId] || r.workId.toUpperCase()}
                  </span>
                )}

                {/* Label with explanation */}
                <div className="flex-1 min-w-0">
                  <span className="text-sm truncate block text-neutral-800 dark:text-neutral-200">
                    {r.type === 'navigate' && r.book ? (
                      <span>
                        <span className="text-blue-600 dark:text-blue-400 font-medium">Go to </span>
                        <HighlightedLabel label={r.label} matchIdxs={r.matchIdxs} />
                      </span>
                    ) : (
                      <HighlightedLabel label={r.label} matchIdxs={r.matchIdxs} />
                    )}
                  </span>
                  {r.explanation && (
                    <span className="text-[9px] text-neutral-400 dark:text-neutral-500 truncate block">{r.explanation}</span>
                  )}
                </div>

                {/* Score bar (right) */}
                {r.score !== undefined && r.score !== Infinity && (
                  <span className="w-10 h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden shrink-0">
                    <span className="block h-full rounded-full transition-all"
                      style={{ width: `${rel * 100}%`, backgroundColor: rel > 0.7 ? '#22c55e' : rel > 0.4 ? '#eab308' : '#6b7280' }}
                    />
                  </span>
                )}

                {/* Navigate hint & new tab indicator */}
                {r.type === 'navigate' && r.book && !r.newTab && (
                  <span className="text-[9px] text-neutral-400 dark:text-neutral-500 font-mono shrink-0">↵ jump</span>
                )}
                {r.newTab && <span className="text-[9px] text-amber-600 dark:text-amber-400 font-mono shrink-0">+tab</span>}

                {/* Help text */}
                {r.text && <span className="text-xs text-neutral-400 dark:text-neutral-500 whitespace-pre-line">{r.text}</span>}
              </button>

              {/* Chapter preview (fzf-preview style) — toggled via Tab when a book is selected */}
              {isSelected && showChapters && r.type === 'navigate' && r.book && (
                <div className="px-4 py-2 pl-14 border-t border-b border-neutral-100 dark:border-neutral-700 bg-neutral-50/50 dark:bg-neutral-800/30">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[9px] text-neutral-400 dark:text-neutral-500">Chapters of {r.bookTitle} · hover to preview</span>
                    <span className="text-[9px] text-neutral-400 dark:text-neutral-500 font-mono">{getChapters(r.book).length} total</span>
                  </div>
                  <div className="flex flex-wrap gap-1 max-h-16 overflow-y-auto">
                    {getChapters(r.book).map(ch => (
                      <button key={ch} onClick={() => { executeResult({ ...r, chapter: ch }); onClose() }}
                        onMouseEnter={() => loadPreview(r.book, ch)}
                        className={`px-1.5 py-0.5 text-[10px] font-mono rounded border transition-colors cursor-pointer
                          ${ch === previewCh
                            ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-300 dark:border-blue-600 text-blue-700 dark:text-blue-300'
                            : 'border-neutral-200 dark:border-neutral-600 text-neutral-600 dark:text-neutral-400 bg-white dark:bg-neutral-800 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-600 hover:text-blue-700 dark:hover:text-blue-300'}`}>
                        {ch}
                      </button>
                    ))}
                  </div>
                  {/* Live verse preview for the hovered/selected chapter */}
                  <div className="mt-2 pt-2 border-t border-neutral-100 dark:border-neutral-700 max-h-36 overflow-y-auto">
                    <div className="text-[9px] text-neutral-400 uppercase tracking-wider mb-1">{r.bookTitle} {previewCh} — preview</div>
                    {previewLoading ? (
                      <div className="animate-pulse text-[11px] text-neutral-400 py-1">Loading chapter…</div>
                    ) : previewVerses.length > 0 ? (
                      previewVerses.map(v => (
                        <div key={v.verse} className="flex gap-1.5 text-[11px] leading-relaxed text-neutral-600 dark:text-neutral-300">
                          <span className="text-blue-500 dark:text-blue-400 text-[9px] font-mono shrink-0 w-5 text-right mt-0.5">{v.verse}</span>
                          <span>{v.text_english}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-[11px] text-neutral-400 py-1">No preview available.</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {/* Error state */}
        {resultType === 'error' && results.length > 0 && (
          <div className="px-4 py-3 text-xs text-red-500">{results[0].label}</div>
        )}
      </div>

      {/* Input bar (fzf: input at the bottom) */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-t border-neutral-100 dark:border-neutral-700 bg-white dark:bg-neutral-800 shrink-0">
        <span className="text-xs text-green-600 dark:text-green-400 font-mono shrink-0 font-bold">{'>'}</span>
        <input ref={inputRef} type="search" inputMode="search" enterKeyHint="go"
          value={val} onChange={e => handleChange(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') { e.preventDefault(); executeCurrent() }
            if (e.key === 'Escape') { onClose(); return }
            if (e.key === 'Tab') { e.preventDefault(); toggleChapterPreview(); return }
            if (e.key === 'ArrowDown' || (e.ctrlKey && e.key === 'n')) { e.preventDefault(); setShowChapters(false); setSel(i => Math.min(i + 1, results.length - 1)); return }
            if (e.key === 'ArrowUp' || (e.ctrlKey && e.key === 'p')) { e.preventDefault(); setShowChapters(false); setSel(i => Math.max(i - 1, 0)); return }
          }}
          placeholder="isa 55:6 · /search · /chat · /help"
          className="flex-1 text-base sm:text-sm outline-none bg-transparent text-neutral-800 dark:text-neutral-200 placeholder-neutral-400 dark:placeholder-neutral-500" />
        <kbd className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono bg-neutral-100 dark:bg-neutral-700 px-1.5 py-0.5 rounded">↵</kbd>
        <span className="text-[9px] text-neutral-300 dark:text-neutral-600 font-mono hidden sm:inline">
          <kbd className="bg-neutral-100 dark:bg-neutral-700 px-1 rounded">Tab</kbd> chapters
        </span>
      </div>
    </div>
  </div>
)
}
