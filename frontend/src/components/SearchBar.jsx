/**
 * SearchBar — full-text search of all scripture text.
 * Always visible in the header. Uses FTS5 + optional semantic search.
 * Results dropdown with click-to-navigate.
 *
 * Features:
 * - Keyword highlighting (from API highlights or client-side regex)
 * - Work badges on each result
 * - Pagination with "Load more"
 * - Work filter dropdown
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { searchVerses, semanticSearch } from '../api'
import { parseAndFuzzy } from '../refParser'
import VersePreviewCard from './VersePreviewCard'

// Map book IDs to their parent work ID
function bookToWork(bookId, bookData) {
  if (!bookData?.works) return null
  for (const w of bookData.works) {
    if (w.books?.some(b => b.id === bookId)) return w.id
  }
  return null
}

const WORK_COLORS = {
  'ot': 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  'nt': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  'bom': 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
  'dc': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  'pgp': 'bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-300',
  'dss': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300',
  'apoc': 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300',
  'pseu': 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
  'expanded': 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300',
}

function highlightText(text, query) {
  if (!query?.trim() || !text) return text
  const terms = query.trim().split(/\s+/).filter(t => t.length > 1 && !t.startsWith('-') && !t.startsWith('"'))
  if (terms.length === 0) return text
  let result = text.slice(0, 200)
  for (const term of terms) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    result = result.replace(new RegExp(`(${escaped})`, 'gi'), '¬¬$1¬¬')
  }
  return result.split('¬¬').map((part, i) =>
    i % 2 === 1 ? `<mark class="bg-amber-200 dark:bg-amber-600/50 rounded-sm font-semibold">${part}</mark>` : part
  ).join('')
}

// Highlight using API offsets array
function applyHighlights(text, highlights) {
  if (!highlights?.length || !text) return text
  const chars = [...text.slice(0, 200)]
  const marks = new Array(chars.length).fill(false)
  for (const h of highlights) {
    for (let i = h.pos; i < h.pos + h.len && i < chars.length; i++) {
      marks[i] = true
    }
  }
  let result = ''
  let inMark = false
  for (let i = 0; i < chars.length; i++) {
    if (marks[i] && !inMark) { result += '<mark class="bg-amber-200 dark:bg-amber-600/50 rounded-sm font-semibold">'; inMark = true }
    if (!marks[i] && inMark) { result += '</mark>'; inMark = false }
    result += chars[i]
  }
  if (inMark) result += '</mark>'
  return result
}

export default function SearchBar({ onNavigate, onOpenTab, bookData, onCommand }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [semanticResults, setSemanticResults] = useState([])
  const [refResult, setRefResult] = useState(null) // { book, chapter, verse, label }
  const [cmdResult, setCmdResult] = useState(null) // { type, label, action } for /commands
  const [loading, setLoading] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [showSemantic, setShowSemantic] = useState(false)
  const [sel, setSel] = useState(0)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [workFilter, setWorkFilter] = useState('')
  const inputRef = useRef(null)
  const debounceRef = useRef(null)
  const dropdownRef = useRef(null)

  const doSearch = useCallback(async (q, append = false) => {
    if (!q.trim()) { setResults([]); setSemanticResults([]); setLoading(false); return }
    setLoading(true)
    const currentOffset = append ? offset : 0
    try {
      const res = await searchVerses(q.trim(), { limit: 10, offset: currentOffset, book: workFilter })
      const list = res?.data?.results || []
      setResults(prev => append ? [...prev, ...list] : list)
      setHasMore(res?.data?.has_more ?? false)
      setTotalCount(res?.data?.total ?? list.length)
      setOffset(currentOffset + list.length)

      // Semantic search (if toggle is on or as supplement)
      if (showSemantic || list.length < 3) {
        try {
          const sres = await semanticSearch(q.trim(), { limit: 5 })
          setSemanticResults(sres?.data?.results || [])
        } catch { setSemanticResults([]) }
      } else {
        setSemanticResults([])
      }
    } catch { setResults([]) }
    setLoading(false)
  }, [showSemantic, offset, workFilter])

  const handleQueryChange = (v) => {
    setQuery(v)
    setOffset(0)
    setSel(0)
    const trimmed = v.trim()
    if (trimmed) {
      const books = bookData?.works?.flatMap?.(w => w.books?.map?.(b => ({ bookId: b.id, bookTitle: b.title, workId: w.id, workLabel: w.title, searchText: `${b.title} ${b.id} ${w.title}` }))) || []
      const parsed = parseAndFuzzy(trimmed, books)
      // Check for navigate (ref) results — show ALL matches as a dropdown
      if (parsed.type === 'navigate' && parsed.results?.length > 0) {
        setRefResult(parsed.results.map(r => ({
          book: r.book, chapter: r.chapter, label: r.label || `${r.book} ${r.chapter}`,
          newTab: r.newTab || false, verses: r.verses || null, score: r.score || 0,
        })))
      } else {
        setRefResult(null)
      }
      // Check for command results (/chat, /dark, etc.)
      if (parsed.type === 'chat' || parsed.type === 'dark' || parsed.type === 'font' ||
          parsed.type === 'toggle' || parsed.type === 'history' || parsed.type === 'structure' ||
          parsed.type === 'help' || parsed.type === 'search') {
        setCmdResult(parsed)
      } else {
        setCmdResult(null)
      }
    } else {
      setRefResult(null)
      setCmdResult(null)
    }
  }

  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (!query.trim()) { setResults([]); setSemanticResults([]); setRefResult(null); setShowDropdown(false); return }
    debounceRef.current = setTimeout(() => doSearch(query, false), 300)
    setShowDropdown(true)
    return () => clearTimeout(debounceRef.current)
  }, [query, doSearch])

  // Reset search when work filter changes
  useEffect(() => {
    if (query.trim()) {
      clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => doSearch(query, false), 100)
    }
  }, [workFilter])

  // Close dropdown on click outside
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target) &&
          inputRef.current && !inputRef.current.contains(e.target)) {
        setShowDropdown(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const navigate = (verseId, e) => {
    const parts = verseId?.split('.')
    if (parts?.length >= 2) {
      const book = parts[0]; const chapter = parseInt(parts[1]); const verse = parts[2] ? parseInt(parts[2]) : null
      const label = `${book} ${chapter}${verse ? `:${verse}` : ''}`
      if (e.ctrlKey || e.metaKey) { onOpenTab?.(book, chapter, { label, highlights: verse ? [verse] : [] }) }
      else { onNavigate?.(book, chapter) }
    }
    setShowDropdown(false)
    setQuery('')
  }

  const loadMore = () => {
    if (!loading && hasMore) doSearch(query, true)
  }

  const works = bookData?.works || []
  const refItems = Array.isArray(refResult) && refResult.length > 0
    ? [{ _type: 'ref_header' }, ...refResult.map((r, i) => ({ _type: 'ref', ref: r.label, book: r.book, chapter: r.chapter, verses: r.verses, newTab: r.newTab, _refIdx: i }))]
    : []
  const cmdItem = cmdResult ? cmdResult.results?.map((r, i) => ({ ...r, _type: 'cmd', _cmdIdx: i })) || [] : []
  const allResults = [
    ...refItems,
    ...cmdItem,
    ...(results.length > 0 && refItems.length > 0 ? [{ _type: 'search_header' }] : []),
    ...results.map(r => ({ ...r, _type: 'fts' })),
    ...(showSemantic && semanticResults.length > 0 ? [{ _type: 'semantic_header' }, ...semanticResults.map(r => ({ ...r, _type: 'semantic' }))] : []),
  ]

  return (
    <div className="relative">
      {/* Search input */}
      <div className="flex items-center gap-1 px-2 py-1 rounded-lg border border-neutral-300 dark:border-neutral-700
        bg-white dark:bg-neutral-800 focus-within:border-blue-400 dark:focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-400 transition-all w-52 sm:w-64">
        <svg className="w-3.5 h-3.5 text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input ref={inputRef}
          type="text" value={query} onChange={e => handleQueryChange(e.target.value)}
          onFocus={() => { if (query.trim()) setShowDropdown(true) }}
          onKeyDown={e => {
            if (e.key === 'Escape') { setShowDropdown(false); inputRef.current?.blur() }
            if (e.key === 'ArrowDown') { e.preventDefault(); setSel(i => Math.min(i + 1, allResults.length - 1)) }
            if (e.key === 'ArrowUp') { e.preventDefault(); setSel(i => Math.max(i - 1, 0)) }
            if (e.key === 'Enter' && allResults[sel]) {
              const item = allResults[sel]
              if (item._type === 'semantic_header' || item._type === 'ref_header' || item._type === 'search_header') return
              if (item._type === 'ref') {
                onNavigate?.(item.book, item.chapter, item.verses)
                setShowDropdown(false)
                setQuery('')
              } else if (item._type === 'cmd') {
                onCommand?.(item)
                setShowDropdown(false)
                setQuery('')
              } else {
                navigate(item.verse || item.verse_id, e)
              }
            }
          }}
          placeholder="Search, navigate, /commands..."
          className="flex-1 text-xs outline-none bg-transparent text-neutral-800 dark:text-neutral-200 placeholder-neutral-400 dark:placeholder-neutral-500" />
        {loading && <svg className="w-3 h-3 text-neutral-400 animate-spin" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>}
        {/* Semantic toggle */}
        <button onClick={() => setShowSemantic(!showSemantic)}
          className={`text-[9px] px-1 rounded cursor-pointer shrink-0 ${showSemantic ? 'text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30' : 'text-neutral-300 dark:text-neutral-600 hover:text-neutral-400'}`}
          title="Toggle semantic search concept matching">✦</button>
        {/* Work filter */}
        {works.length > 0 && (
          <select value={workFilter} onChange={e => { setWorkFilter(e.target.value); setOffset(0); setSel(0) }}
            className="text-[8px] font-mono bg-transparent border-l border-neutral-200 dark:border-neutral-700 pl-1 outline-none text-neutral-400 dark:text-neutral-500 cursor-pointer max-w-[60px]"
            title="Filter by work">
            <option value="">All</option>
            {works.map(w => <option key={w.id} value={w.id}>{w.id.toUpperCase()}</option>)}
          </select>
        )}
      </div>

      {/* Results dropdown */}
      {showDropdown && (allResults.length > 0 || loading) && (
        <div ref={dropdownRef}
          className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 max-h-96 overflow-y-auto z-50">
          {loading && results.length === 0 && (
            <div className="px-4 py-6 text-xs text-neutral-400 text-center">Searching...</div>
          )}
          {/* Result count */}
          {results.length > 0 && !loading && (
            <div className="sticky top-0 bg-white dark:bg-neutral-800 border-b border-neutral-100 dark:border-neutral-700 px-4 py-1.5 text-[9px] text-neutral-400 dark:text-neutral-500 flex items-center gap-2 z-10">
              <span>{totalCount} result{totalCount !== 1 ? 's' : ''}</span>
              {workFilter && <span className="text-blue-500 dark:text-blue-400">· filtered: {workFilter.toUpperCase()}</span>}
            </div>
          )}
          {/* Divider after ref result */}
          {Array.isArray(refResult) && refResult.length > 0 && results.length > 0 && (
            <div className="border-t border-neutral-100 dark:border-neutral-700 mx-2" />
          )}
          {allResults.map((r, i) => {
            if (r._type === 'ref_header') {
              return <div key="ref-header" className="px-4 py-1.5 text-[9px] text-neutral-400 dark:text-neutral-500 font-mono">📍 Navigate</div>
            }
            if (r._type === 'search_header') {
              return <div key="search-header" className="border-t border-neutral-100 dark:border-neutral-700 mx-2" />
            }
            if (r._type === 'semantic_header') {
              return <div key="semantic-h" className="px-4 py-2 text-[9px] text-neutral-400 dark:text-neutral-500 font-mono border-t border-neutral-100 dark:border-neutral-700">✦ Semantic matches</div>
            }
            if (r._type === 'ref') {
              return (
                <div key={`ref-${r._refIdx}`} className="border-b border-neutral-100 dark:border-neutral-700 last:border-b-0">
                  <button
                    onClick={() => { onNavigate?.(r.book, r.chapter, r.verses); setShowDropdown(false); setQuery('') }}
                    onMouseEnter={() => setSel(i)}
                    className={`w-full text-left px-4 py-2.5 flex items-center gap-2 cursor-pointer transition-colors ${
                      i === sel ? 'bg-blue-100 dark:bg-blue-900/30 border-l-2 border-blue-500' : 'hover:bg-neutral-50 dark:hover:bg-neutral-700/50 border-l-2 border-transparent'
                    }`}>
                    <span className="text-xs shrink-0">📖</span>
                    <span className="text-sm font-medium text-blue-700 dark:text-blue-300">{r.ref}</span>
                    {r.verses?.length > 0 && <span className="text-[9px] text-amber-600 dark:text-amber-400 font-mono">✦{r.verses.length}</span>}
                    <span className="ml-auto text-[9px] text-neutral-400 dark:text-neutral-500">↵ jump</span>
                  </button>
                  {/* Inline verse preview */}
                  {r.book && r.chapter && (
                    <div className="px-4 pb-2">
                      <VersePreviewCard
                        refs={r.verses?.length > 0 ? r.verses.map(v => `${r.book}.${r.chapter}.${v}`) : `${r.book}.${r.chapter}`}
                        onNavigate={(b, c) => { onNavigate?.(b, c); setShowDropdown(false); setQuery('') }}
                        maxHeight="8rem"
                        compact
                      />
                    </div>
                  )}
                </div>
              )
            }
            if (r._type === 'cmd') {
              const icons = { chat: '💬', search: '🔍', dark: '🌙', font: '🔤', toggle: '🔘', history: '🕐', structure: '⟷', help: 'ℹ️' }
              return (
                <button key={`cmd-${r._cmdIdx}`}
                  onClick={() => { onCommand?.(r); setShowDropdown(false); setQuery('') }}
                  onMouseEnter={() => setSel(i)}
                  className={`w-full text-left px-4 py-2.5 flex items-center gap-2 cursor-pointer transition-colors ${
                    i === sel ? 'bg-blue-100 dark:bg-blue-900/30 border-l-2 border-blue-500' : 'hover:bg-neutral-50 dark:hover:bg-neutral-700/50 border-l-2 border-transparent'
                  }`}>
                  <span className="text-xs shrink-0">{icons[r.type] || '⚡'}</span>
                  <span className="text-sm text-neutral-700 dark:text-neutral-300">{r.label}</span>
                  {r.text && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 ml-1 truncate">{r.text}</span>}
                  <span className="ml-auto text-[9px] text-neutral-400 dark:text-neutral-500">↵ run</span>
                </button>
              )
            }
            const verseId = r.verse || r.verse_id
            const ref = r.reference || verseId
            const text = r.text || r.text_english || ''
            const similarity = r.similarity
            const isSelected = i === sel
            const workId = bookToWork(verseId?.split('.')[0], bookData)
            // Use API highlights if available, otherwise client-side regex
            const highlighted = r.highlights?.length
              ? applyHighlights(text, r.highlights)
              : highlightText(text, query)
            return (
              <button key={verseId || i}
                onClick={(e) => navigate(verseId, e)}
                onMouseEnter={() => setSel(i)}
                className={`w-full text-left px-4 py-2.5 flex flex-col gap-0.5 cursor-pointer transition-colors
                  ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-neutral-50 dark:hover:bg-neutral-700/50'}`}>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-blue-600 dark:text-blue-400 font-medium">{ref}</span>
                  {workId && (
                    <span className={`text-[8px] px-1 rounded ${WORK_COLORS[workId] || 'bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400'}`}>
                      {workId.toUpperCase()}
                    </span>
                  )}
                  {similarity !== undefined && (
                    <span className="text-[8px] text-neutral-400 dark:text-neutral-500 font-mono">({similarity.toFixed(3)})</span>
                  )}
                  <span className="text-[8px] text-neutral-300 dark:text-neutral-600 ml-auto">
                    {r._type === 'semantic' ? '✦' : '📖'}
                  </span>
                </div>
                <span className="text-xs text-neutral-600 dark:text-neutral-300 line-clamp-2"
                  dangerouslySetInnerHTML={{ __html: highlighted }} />
              </button>
            )
          })}
          {/* Load more */}
          {hasMore && !loading && (
            <button onClick={loadMore}
              className="w-full text-center px-4 py-2 text-[11px] text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-colors border-t border-neutral-100 dark:border-neutral-700 font-medium">
              Load more results...
            </button>
          )}
          {loading && results.length > 0 && (
            <div className="px-4 py-2 text-[10px] text-neutral-400 text-center border-t border-neutral-100 dark:border-neutral-700">
              Loading...
            </div>
          )}
        </div>
      )}
    </div>
  )
}
