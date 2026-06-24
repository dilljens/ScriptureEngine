import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { getInfo, getBooks } from './api'
import { TabProvider, useTabs } from './tabContext.jsx'
import { SettingsProvider, useSettings, useHistory } from './settings.jsx'
import { ProgressProvider, useProgress } from './progress.jsx'
import { parseAndFuzzy, getChapters } from './refParser'
import ChatPanel from './components/ChatPanel'
import ConversationHistory from './components/ConversationHistory'
import VerseBlock from './components/VerseBlock'
import StudyViewer from './components/StudyViewer'
import SearchBar from './components/SearchBar'
import { ToggleProvider, ToggleBar, PoetryToggle, useToggles, TOGGLE_DEFS } from './components/ToggleProvider'
import ChiasmPanel from './components/ChiasmPanel'
import StructureModal from './components/StructureModal'
import BookView from './components/BookView'
import WorkView from './components/WorkView'
import LibraryView from './components/LibraryView'
import SettingsPanel from './components/SettingsPanel'
import HotkeyCheatsheet from './components/HotkeyCheatsheet'
import ErrorBoundary from './components/ErrorBoundary'
import useAgentControl from './useAgentControl'

import { getChapterParallelism, getFootnotes, getTskCrossrefs, getChapterGrammar, getChapterConnections, searchVerses } from './api'
import { getCached, setCached } from './cache'

function useChapterData(book, chapter) {
  const key = `${book}.${chapter}`
  const [d, sd] = useState(() => getCached(key))
  const [l, sl] = useState(!d)
  const [e, se] = useState(null)
  useEffect(() => {
    const c = getCached(key)
    if (c) { sd(c); sl(false); se(null); return }
    let cancel = false; let att = 0
    const tf = () => {
      if (cancel) return; sl(true); se(null)
      getChapterParallelism(book, chapter)
        .then(r => { if (!cancel) { setCached(key, r.data); sd(r.data); sl(false) } })
        .catch(err => { if (cancel) return; att++; if (att < 5) setTimeout(tf, Math.min(1000 * 2 ** att, 8000)); else { se(err.message); sl(false) } })
    }
    tf()
    return () => { cancel = true }
  }, [book, chapter])
  return { data: d, loading: l, error: e }
}

// ── Chapter View ──

function ChapterView({ book, chapter, poetryMode, highlightVerse }) {
  const { toggles } = useToggles()
  const { data, loading, error } = useChapterData(book, chapter)
  const [footnotes, setFootnotes] = useState(null)
  const [tskRefs, setTskRefs] = useState(null)
  const [wordData, setWordData] = useState(null)
  const [chapterConnections, setChapterConnections] = useState(null)
  const { isReviewed, toggleReviewed, getChapterProgress, markReviewed } = useProgress()
  const [verseJump, setVerseJump] = useState('')
  const verseInputRef = useRef(null)

  // Intercept number keys to focus the verse-jump input
  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
      if (/^[0-9]$/.test(e.key)) {
        e.preventDefault()
        verseInputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const jumpToVerse = (vnum) => {
    if (!vnum) return
    const el = document.getElementById(`verse-${book}.${chapter}.${vnum}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('ring-2', 'ring-blue-400', 'rounded-lg')
      setTimeout(() => el.classList.remove('ring-2', 'ring-blue-400', 'rounded-lg'), 2000)
    }
    setVerseJump('')
    verseInputRef.current?.blur()
  }

  useEffect(() => {
    getFootnotes(`${book}.${chapter}`)
      .then(r => setFootnotes(r.data?.footnotes || []))
      .catch(() => setFootnotes([]))
  }, [book, chapter])

  useEffect(() => {
    getTskCrossrefs(`${book}.${chapter}`)
      .then(r => setTskRefs(r.data?.cross_references || []))
      .catch(() => setTskRefs([]))
  }, [book, chapter])

  // Fetch word-level grammar/gematria data
  useEffect(() => {
    getChapterGrammar(`${book}.${chapter}`)
      .then(r => setWordData(r.data?.verses || {}))
      .catch(() => setWordData({}))
  }, [book, chapter])

  // Fetch chapter connections (intertextual, geographic, chronological, etc.)
  useEffect(() => {
    getChapterConnections(`${book}.${chapter}`)
      .then(r => setChapterConnections(r.data?.verses || {}))
      .catch(() => setChapterConnections({}))
  }, [book, chapter])

  const verseRefs = useRef({})
  useEffect(() => {
    if (highlightVerse && verseRefs.current[highlightVerse]) {
      verseRefs.current[highlightVerse].scrollIntoView({ behavior: 'smooth', block: 'center' })
      markReviewed(`${book}.${chapter}.${highlightVerse}`)
    }
  }, [highlightVerse, book, chapter])

  // ── These must live before the early returns (hooks rule) ──
  const LAYER_MAP = {
    'intertextual': [
      { toggle: 'direct', types: ['direct_quotation', 'modified_quotation'] },
      { toggle: 'allusion', types: ['allusion'] },
      { toggle: 'echo', types: ['echo'] },
    ],
    'geographic': [
      { toggle: 'places', types: ['same_location', 'journey_path', 'wilderness_sojourn', 'exile_route', 'promised_land', 'mountain_of_god', 'temple_location', 'garden_presence'] },
    ],
    'chronological': [
      { toggle: 'times', types: ['same_time_period', 'feast_connection', 'chronological_marker', 'sabbatical_cycle', 'jubilee_cycle', 'dispensation', 'prophetic_timeline'] },
    ],
    'interpretive': [
      { toggle: 'isaiah', types: ['giliadi_pattern'] },
    ],
  }

  const connectionsByVerse = useMemo(() => {
    if (!chapterConnections) return {}
    const result = {}
    for (const [vnum, conns] of Object.entries(chapterConnections)) {
      const grouped = {}
      for (const c of conns) {
        for (const rules of Object.values(LAYER_MAP)) {
          for (const rule of rules) {
            if (rule.types.includes(c.type) && toggles[rule.toggle]) {
              if (!grouped[rule.toggle]) grouped[rule.toggle] = []
              grouped[rule.toggle].push(c)
              break
            }
          }
        }
      }
      if (Object.keys(grouped).length > 0) result[vnum] = grouped
    }
    return result
  }, [chapterConnections, toggles])

  if (loading) return <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500 text-sm"><svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Loading chapter…</div>
  if (error) return <div className="mx-4 mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">{error}<button onClick={() => window.location.reload()} className="ml-3 underline hover:text-red-800 cursor-pointer">Retry</button></div>
  if (!data) return null

  const totalVerses = data.verses?.length || 0
  const reviewedCount = data.verses?.filter(v => isReviewed(`${book}.${chapter}.${v.verse}`)).length || 0
  const progressPct = totalVerses > 0 ? Math.round(reviewedCount / totalVerses * 100) : 0

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      <div className="mb-3 flex items-center gap-3 text-[10px] text-neutral-400 dark:text-neutral-500">
        <div className="flex-1 h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
          <div className="h-full rounded-full bg-blue-500 dark:bg-blue-400 transition-all duration-300" style={{ width: `${progressPct}%` }} />
        </div>
        <span className="shrink-0">{reviewedCount}/{totalVerses} verses reviewed</span>
        {footnotes && <span className="shrink-0">· {footnotes.length} fn</span>}
        {tskRefs && <span className="shrink-0">· {tskRefs.length} tsk</span>}
        {/* Verse jump input */}
        <div className="shrink-0 flex items-center gap-1 ml-auto">
          <span className="text-neutral-300 dark:text-neutral-600">⏎</span>
          <input ref={verseInputRef} type="text" value={verseJump}
            onChange={e => setVerseJump(e.target.value.replace(/[^0-9]/g, ''))}
            onKeyDown={e => {
              if (e.key === 'Enter' && verseJump) { jumpToVerse(parseInt(verseJump)) }
              if (e.key === 'Escape') { setVerseJump(''); verseInputRef.current?.blur() }
            }}
            placeholder="v#"
            className="w-12 px-1.5 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 text-[10px] font-mono bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 placeholder-neutral-400 dark:placeholder-neutral-500" />
        </div>
      </div>

      {data.verses?.map(v => {
        const vs = String(v.verse)
        const verseFns = footnotes?.filter(f => { const vn = f.verse_id?.split('.').pop(); return vn === vs }) || []
        const verseTsk = tskRefs?.filter(r => { const vn = r.source_verse?.split('.').pop(); return vn === vs }) || []
        const verseWords = wordData?.[`${book}.${chapter}.${v.verse}`] || null
        const verseExtra = connectionsByVerse[vs] || null
        const reviewed = isReviewed(`${book}.${chapter}.${v.verse}`)
        return (
          <div key={v.verse} id={`verse-${book}.${chapter}.${v.verse}`} ref={el => verseRefs.current[v.verse] = el} className={highlightVerse === v.verse ? 'scroll-mt-20' : ''}>
            <VerseBlock verse={v} toggles={toggles} poetryMode={poetryMode}
              chiasms={data.chiasms} highlights={[]}
              footnotes={toggles.footnotes ? verseFns : []}
              tskRefs={toggles.tsk ? verseTsk : []}
              wordData={toggles.gematria || toggles.lemma ? verseWords : null}
              extraConnections={verseExtra}
              reviewed={reviewed}
              onToggleReview={() => toggleReviewed(`${book}.${chapter}.${v.verse}`)}
            />
          </div>
        )
      })}
      {toggles.chiasmus && data.chiasms?.length > 0 && (
        <div className="mt-10 space-y-3">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider px-1">Chiasmus Structures</h3>
          {data.chiasms.filter(ch => ch.elements?.length > 0 || ch.chapter_section).map(ch => <ChiasmPanel key={ch.chiasm_id} chiasm={ch} />)}
        </div>
      )}
    </div>
  )
}

// ── Book View (real input for filter) ──



// ── Chiasm Panel ──



// ── Command Input (unified: refs, paths, /chat, /help) ──

function CommandInput({ open, onClose, onNavigate, onChat, allBooks }) {
  const [val, setVal] = useState('')
  const [results, setResults] = useState([])
  const [resultType, setResultType] = useState('empty')
  const [sel, setSel] = useState(0)
  const [showChapters, setShowChapters] = useState(false)  // tab toggles chapter preview
  const inputRef = useRef(null)
  const resultsRef = useRef(null)

  useEffect(() => {
    if (open) { setVal(''); setResults([]); setResultType('empty'); setSel(0); setShowChapters(false); setTimeout(() => inputRef.current?.focus(), 50) }
  }, [open])

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
        score: Infinity,  // no relevance bar shown
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

  // /search execution — fetches and shows first matching verse
  const handleSearchResult = async (query) => {
    if (!query) return
    try {
      const res = await searchVerses(query, { limit: 5 })
      if (res.ok && res.data?.results?.length > 0) {
        const first = res.data.results[0]
        const ref = first.verse_id || first.ref || ''
        const parts = ref.split('.')
        if (parts.length >= 2) {
          onNavigate(parts[0], parseInt(parts[1]), false)
        }
      }
    } catch {}
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
        handleSearchResult(r.query)
        onClose(); break
      case 'dark':
        toggleDarkMode()
        onClose(); break
      case 'font':
        if (r.direction === 'up') changeFontSize(1)
        else if (r.direction === 'down') changeFontSize(-1)
        else if (r.size) changeFontSize(r.size)
        onClose(); break
      case 'toggle':
        if (r.toggle) {
          // Map display names to dispatch action names
          const toggleMap = {
            'footnotes': 'footnotes', 'fn': 'footnotes',
            'gematria': 'gematria', 'gem': 'gematria',
            'lemma': 'lemma', 'strongs': 'lemma',
            'synonymous': 'synonymous',
            'antithetic': 'antithetic',
            'synthetic': 'synthetic',
            'staircase': 'staircase',
            'chiasmus': 'chiasmus', 'chiastic': 'chiasmus',
            'tsk': 'tsk', 'crossref': 'tsk', 'cross-ref': 'tsk',
            'direct': 'direct', 'quotation': 'direct',
            'allusion': 'allusion',
            'echo': 'echo',
            'times': 'times', 'time': 'times', 'chronological': 'times',
            'places': 'places', 'geographic': 'places',
            'isaiah': 'isaiah', 'giliadi': 'isaiah',
          }
          const action = toggleMap[r.toggle.toLowerCase()] || r.toggle
          toggleDispatch(action)
        }
        onClose(); break
      case 'history':
        setShowHistory(true)
        onClose(); break
      case 'structure':
        setShowStructure(true)
        onClose(); break
    }
  }

  const executeCurrent = () => {
    const r = results[sel]
    if (r?.type === 'header') return  // can't execute headers
    if (r) executeResult(r)
  }

  // Tab toggles chapter preview for the selected book result
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
  }

  const workHeaderColors = {
    'ot': 'bg-amber-50/50 dark:bg-amber-900/10 text-amber-700 dark:text-amber-300',
    'nt': 'bg-blue-50/50 dark:bg-blue-900/10 text-blue-700 dark:text-blue-300',
    'bom': 'bg-green-50/50 dark:bg-green-900/10 text-green-700 dark:text-green-300',
    'dc': 'bg-purple-50/50 dark:bg-purple-900/10 text-purple-700 dark:text-purple-300',
    'pgp': 'bg-pink-50/50 dark:bg-pink-900/10 text-pink-700 dark:text-pink-300',
  }

  // Get the currently selected result (not a header)
  const selResult = results[sel]?.type === 'navigate' ? results[sel] : null

  // fzf-style match highlighting
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
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]" onClick={onClose}>
      <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-300 dark:border-neutral-700 w-full max-w-xl mx-4 flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}>

        {/* Results area (fzf: results above input) */}
        <div ref={resultsRef} className="overflow-y-auto max-h-[50vh] min-h-0" style={{ scrollBehavior: 'smooth' }}>
          {/* When query is empty, show all books with work headers */}
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

                  {/* Icon */}
                  <span className="text-xs shrink-0 w-4 text-center">
                    {r.type === 'navigate' ? '📖' : r.type === 'chat' ? '💬' : r.type === 'help' ? 'ℹ️' : '⚠️'}
                  </span>

                  {/* Work badge */}
                  {r.workId && (
                    <span className={`text-[9px] font-mono px-1 rounded shrink-0 ${workColors[r.workId] || 'text-neutral-500 bg-neutral-100'}`}>
                      {WORK_LABEL[r.workId] || r.workId.toUpperCase()}
                    </span>
                  )}

                  {/* Label with match highlighting */}
                  <span className="flex-1 truncate text-neutral-800 dark:text-neutral-200">
                    <HighlightedLabel label={r.label} matchIdxs={r.matchIdxs} />
                  </span>

                  {/* Score bar (right) */}
                  {r.score !== undefined && r.score !== Infinity && (
                    <span className="w-10 h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden shrink-0">
                      <span className="block h-full rounded-full transition-all"
                        style={{ width: `${rel * 100}%`, backgroundColor: rel > 0.7 ? '#22c55e' : rel > 0.4 ? '#eab308' : '#6b7280' }}
                      />
                    </span>
                  )}

                  {/* New tab indicator */}
                  {r.newTab && <span className="text-[9px] text-amber-600 dark:text-amber-400 font-mono">+tab</span>}

                  {/* Help text */}
                  {r.text && <span className="text-xs text-neutral-400 dark:text-neutral-500 whitespace-pre-line">{r.text}</span>}
                </button>

                {/* Chapter preview (fzf-preview style) — toggled via Tab when a book is selected */}
                {isSelected && showChapters && r.type === 'navigate' && r.book && (
                  <div className="px-4 py-2 pl-14 border-t border-b border-neutral-100 dark:border-neutral-700 bg-neutral-50/50 dark:bg-neutral-800/30">
                    <div className="flex flex-wrap gap-1">
                      {getChapters(r.book).map(ch => (
                        <button key={ch} onClick={() => { executeResult({ ...r, chapter: ch }); onClose() }}
                          className="px-1.5 py-0.5 text-[10px] font-mono rounded border border-neutral-200 dark:border-neutral-600
                            text-neutral-600 dark:text-neutral-400 bg-white dark:bg-neutral-800
                            hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-600
                            hover:text-blue-700 dark:hover:text-blue-300 cursor-pointer transition-colors">
                          {ch}
                        </button>
                      ))}
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
          <input ref={inputRef} type="text" value={val} onChange={e => handleChange(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') { e.preventDefault(); executeCurrent() }
              if (e.key === 'Escape') { onClose(); return }
              if (e.key === 'Tab') { e.preventDefault(); toggleChapterPreview(); return }
              if (e.key === 'ArrowDown' || (e.ctrlKey && e.key === 'n')) { e.preventDefault(); setShowChapters(false); setSel(i => Math.min(i + 1, results.length - 1)); return }
              if (e.key === 'ArrowUp' || (e.ctrlKey && e.key === 'p')) { e.preventDefault(); setShowChapters(false); setSel(i => Math.max(i - 1, 0)); return }
            }}
            placeholder="isa 55:6 · isa:34 · isa/34 · or fuzzy book name"
            className="flex-1 text-sm outline-none bg-transparent text-neutral-800 dark:text-neutral-200 placeholder-neutral-400 dark:placeholder-neutral-500" />
          <kbd className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono bg-neutral-100 dark:bg-neutral-700 px-1.5 py-0.5 rounded">↵</kbd>
          <span className="text-[9px] text-neutral-300 dark:text-neutral-600 font-mono hidden sm:inline">
            <kbd className="bg-neutral-100 dark:bg-neutral-700 px-1 rounded">Tab</kbd> chapters
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Settings Panel ──



// ═══════════════════════════════════════════════════════════════
// App Inner
// ═══════════════════════════════════════════════════════════════

function AppInner() {
  const {
    workspaces, activeWorkspace, activeTab, currentWorkspace, currentTab,
    viewLevel, viewUp, viewDown, isChapterView, isLibraryView,
    selectWorkspace, newWorkspace, renameWorkspace, deleteWorkspace,
    openTab, closeTab, selectTab, updateTab, goToChapter, goToBook, goToWork, openChatTab,
  } = useTabs()

  const { fontSize, changeFontSize, darkMode, toggleDarkMode, getHotkey, setHotkey, DEFAULT_HOTKEYS, resetHotkeys, hotkeys, showQuickAsk, persist } = useSettings()
  const { toggles, dispatch: toggleDispatch } = useToggles()

  // Agent control hook (testing, enabled via ?agent=true)
  useAgentControl({
    currentTab,
    toggles,
    navigate: (book, chapter) => goToChapter(currentTab?.id, book, chapter),
    openTab,
    toggleDispatch,
  })

  // Check if an event matches a hotkey combo
  const matchesHotkey = useCallback((e, action) => {
    const combo = getHotkey(action)
    if (!combo) return false
    const parts = combo.split('+')
    const hasCtrl = e.ctrlKey || e.metaKey
    const hasAlt = e.altKey
    const hasShift = e.shiftKey
    const needsCtrl = parts.includes('Ctrl') || parts.includes('Cmd')
    const needsAlt = parts.includes('Alt')
    const needsShift = parts.includes('Shift')
    const lastPart = parts[parts.length - 1]
    const keyMatches = lastPart === e.key || lastPart.toLowerCase() === e.key.toLowerCase()
    return hasCtrl === needsCtrl && hasAlt === needsAlt && hasShift === needsShift && keyMatches
  }, [getHotkey])
  const history = useHistory()

  const [bookData, setBookData] = useState(null); const [serverInfo, setServerInfo] = useState(null)
  const [poetryMode, setPoetryMode] = useState(true)
  const [showStructure, setShowStructure] = useState(false)
  const [showChat, setShowChat] = useState(false); const [chatInitialMsg, setChatInitialMsg] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const [showCommand, setShowCommand] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showCheatsheet, setShowCheatsheet] = useState(false)
  const [renamingWs, setRenamingWs] = useState(null); const [renameValue, setRenameValue] = useState('')

  useEffect(() => { getBooks().then(r => { setBookData(r.data); window.__bookData = r.data }).catch(() => {}) }, [])
  useEffect(() => { getInfo().then(r => setServerInfo(r.data)).catch(() => {}) }, [])

  // Open study from URL query param (e.g., ?study=torah-in-all-scripture)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const studySlug = params.get('study')
    if (studySlug) {
      // Wait a beat for tabs to initialize
      const timer = setTimeout(() => {
        openTab(studySlug, 1, {
          label: `Study: ${studySlug}`,
          view: 'study',
          viewRef: studySlug,
        })
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [openTab])

  const book = currentTab?.book || 'isa'; const chapter = currentTab?.chapter || 1; const viewRef = currentTab?.viewRef || null
  window.__bookData = bookData

  const nav = useMemo(() => {
    if (!bookData?.works) return null
    const flat = []
    for (const w of bookData.works) for (const b of w.books) flat.push({ workId: w.id, workTitle: w.title, bookId: b.id, bookTitle: b.title })
    return { flat, idx: flat.findIndex(n => n.bookId === book) }
  }, [bookData, book])
  const bookTitle = nav?.flat.find(n => n.bookId === book)?.bookTitle || book
  const workTitle = nav?.flat[nav.idx]?.workTitle || ''

  // Resolve a book ID to its display title using nav flat data
  const resolveBookTitle = useCallback((bookId) => {
    return nav?.flat.find(n => n.bookId === bookId)?.bookTitle || bookId
  }, [nav])

  // Listen for TSK navigation events from VerseBlock
  useEffect(() => {
    const handleNav = (e) => {
      if (currentTab?.id && e.detail?.book && e.detail?.chapter) {
        goToChapter(currentTab.id, e.detail.book, e.detail.chapter)
      }
    }
    const handleTab = (e) => {
      if (e.detail?.book && e.detail?.chapter) {
        const bt = resolveBookTitle(e.detail.book)
        openTab(e.detail.book, e.detail.chapter, { label: `${bt} ${e.detail.chapter}` })
      }
    }
    window.addEventListener('scripture-navigate', handleNav)
    window.addEventListener('scripture-open-tab', handleTab)
    return () => {
      window.removeEventListener('scripture-navigate', handleNav)
      window.removeEventListener('scripture-open-tab', handleTab)
    }
  }, [currentTab?.id, goToChapter, openTab, resolveBookTitle])

  // Flat book list for fuzzy finder
  const allBooks = useMemo(() => {
    if (!bookData?.works) return []
    const result = []
    for (const w of bookData.works) {
      for (const b of w.books) {
        result.push({
          workId: w.id,
          workLabel: w.title,
          bookId: b.id,
          bookTitle: b.title,
          searchText: `${b.title} ${b.id} ${w.title}`,
        })
      }
    }
    return result
  }, [bookData])

  const historyNavRef = useRef(false)
  const doHistoryBack = useCallback(() => {
    const entry = history.goBack()
    if (entry && currentTab?.id) { historyNavRef.current = true; updateTab(currentTab.id, { book: entry.book, chapter: entry.chapter, view: entry.view || 'chapter', viewRef: entry.viewRef || null, label: entry.label || `${entry.book} ${entry.chapter}` }) }
  }, [history, currentTab?.id])
  const doHistoryForward = useCallback(() => {
    const entry = history.goForward()
    if (entry && currentTab?.id) { historyNavRef.current = true; updateTab(currentTab.id, { book: entry.book, chapter: entry.chapter, view: entry.view || 'chapter', viewRef: entry.viewRef || null, label: entry.label || `${entry.book} ${entry.chapter}` }) }
  }, [history, currentTab?.id])

  const pushHistory = useCallback(() => { history.push({ book, chapter, view: viewLevel, viewRef, label: `${bookTitle} ${chapter}`, tabId: currentTab?.id }) }, [book, chapter, bookTitle, viewLevel, viewRef, currentTab?.id, history])
  useEffect(() => { if (historyNavRef.current) { historyNavRef.current = false; return }; if (currentTab?.id) pushHistory() }, [book, chapter, viewLevel])

  const goPrevChapter = useCallback(() => {
    if (!currentTab?.id) return
    if (chapter > 1) updateTab(currentTab.id, { chapter: chapter - 1 })
    else if (nav && nav.idx > 0) { const prev = nav.flat[nav.idx - 1]; goToChapter(currentTab.id, prev.bookId, 1) }
  }, [currentTab?.id, chapter, nav])
  const goNextChapter = useCallback(() => {
    if (!currentTab?.id) return
    if (chapter < 150) updateTab(currentTab.id, { chapter: chapter + 1 })
    else if (nav && nav.idx < nav.flat.length - 1) { const next = nav.flat[nav.idx + 1]; goToChapter(currentTab.id, next.bookId, 1) }
  }, [currentTab?.id, chapter, nav])
  const goPrevBookStay = useCallback(() => {
    if (!nav || nav.idx < 0 || !currentTab?.id) return; const prev = nav.flat[nav.idx - 1]; if (prev) goToBook(currentTab.id, prev.bookId, prev.bookTitle)
  }, [nav, currentTab?.id])
  const goNextBookStay = useCallback(() => {
    if (!nav || nav.idx < 0 || !currentTab?.id) return; const next = nav.flat[nav.idx + 1]; if (next) goToBook(currentTab.id, next.bookId, next.bookTitle)
  }, [nav, currentTab?.id])
  const goUpLevel = useCallback(() => {
    if (!currentTab?.id) return
    if (viewLevel === 'chapter') {
      // Keep chapter in memory, go to book view
      updateTab(currentTab.id, { view: 'book', viewRef: book, label: nav?.flat[nav.idx]?.bookTitle || book })
    } else if (viewLevel === 'book') {
      // Keep book in memory, go to work view
      const wId = nav?.flat[nav.idx]?.workId || 'ot'
      const wT = bookData?.works?.find(w => w.id === wId)?.title || wId
      updateTab(currentTab.id, { view: 'work', viewRef: wId, label: wT })
    } else if (viewLevel === 'work') {
      // Keep work in memory, go to library view
      updateTab(currentTab.id, { view: 'library', viewRef: null, label: 'Library' })
    }
  }, [currentTab?.id, viewLevel, book, nav, bookData, updateTab])

  const goDownLevel = useCallback(() => {
    if (!currentTab?.id) return
    if (viewLevel === 'library') {
      // Use viewRef if set (from arrow navigation), else find work containing current book
      const targetWorkId = viewRef || bookData?.works?.find(w => w.books?.some(b => b.id === book))?.id || bookData?.works?.[0]?.id || 'ot'
      const wT = bookData?.works?.find(w => w.id === targetWorkId)?.title || targetWorkId
      updateTab(currentTab.id, { view: 'work', viewRef: targetWorkId, label: wT })
    } else if (viewLevel === 'work') {
      // Return to the book we were in (book field still holds the last book)
      const bTitle = nav?.flat.find(n => n.bookId === book)?.bookTitle || book
      updateTab(currentTab.id, { view: 'book', viewRef: book, label: bTitle })
    } else if (viewLevel === 'book') {
      // Return to the chapter we were in (chapter field still holds the last chapter)
      goToChapter(currentTab.id, book, chapter, `${bookTitle} ${chapter}`)
    }
  }, [currentTab?.id, viewLevel, viewRef, bookData, book, chapter, nav, updateTab, goToChapter])

  // Navigate between works (left/right in work or library view)
  const goPrevWork = useCallback(() => {
    if (!bookData?.works || !currentTab?.id) return
    const list = bookData.works
    const idx = list.findIndex(w => w.id === viewRef)
    if (idx > 0) {
      const target = list[idx - 1]
      // Also update book to the first book of the target work (for goDown navigation)
      const firstBook = target.books?.[0]
      updateTab(currentTab.id, {
        view: viewLevel === 'library' ? 'library' : 'work',
        viewRef: target.id,
        label: target.title,
        ...(firstBook ? { book: firstBook.id } : {}),
      })
    }
  }, [bookData, currentTab?.id, viewRef, viewLevel, updateTab])

  const goNextWork = useCallback(() => {
    if (!bookData?.works || !currentTab?.id) return
    const list = bookData.works
    const idx = list.findIndex(w => w.id === viewRef)
    if (idx < list.length - 1) {
      const target = list[idx + 1]
      const firstBook = target.books?.[0]
      updateTab(currentTab.id, {
        view: viewLevel === 'library' ? 'library' : 'work',
        viewRef: target.id,
        label: target.title,
        ...(firstBook ? { book: firstBook.id } : {}),
      })
    }
  }, [bookData, currentTab?.id, viewRef, viewLevel, updateTab])

  // ── Keyboard handler ──
  useEffect(() => {
    function handleKey(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
        // Allow arrow keys through for navigation even when in an input
        if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
          // Let them through to the navigation logic below
        } else if (e.key === 'Escape') { e.target.blur(); return }
        else { return }
      }
      // Check configurable hotkeys
      if (matchesHotkey(e, 'chat')) { e.preventDefault(); handleOpenChat(); return }
      if (matchesHotkey(e, 'command') || matchesHotkey(e, 'commandAlt')) { e.preventDefault(); setShowCommand(true); return }
      if (matchesHotkey(e, 'historyBack')) { e.preventDefault(); doHistoryBack(); return }
      if (matchesHotkey(e, 'historyForward')) { e.preventDefault(); doHistoryForward(); return }
      if (matchesHotkey(e, 'darkMode')) { e.preventDefault(); toggleDarkMode(); return }
      if (matchesHotkey(e, 'fontUp')) { e.preventDefault(); changeFontSize(1); return }
      if (matchesHotkey(e, 'fontDown')) { e.preventDefault(); changeFontSize(-1); return }
      if (matchesHotkey(e, 'newTab')) { e.preventDefault(); openTab(book, chapter, { label: `${bookTitle} ${chapter}` }); return }
      if (matchesHotkey(e, 'structureModal')) { e.preventDefault(); setShowStructure(true); return }
      if (matchesHotkey(e, 'settingsPanel')) { e.preventDefault(); setShowSettings(p => !p); return }
      if (matchesHotkey(e, 'toggleFootnotes')) { e.preventDefault(); toggleDispatch('footnotes'); return }
      if (matchesHotkey(e, 'toggleGematria')) { e.preventDefault(); toggleDispatch('gematria'); return }
      if (matchesHotkey(e, 'toggleLemma')) { e.preventDefault(); toggleDispatch('lemma'); return }
      if (matchesHotkey(e, 'toggleSynonymous')) { e.preventDefault(); toggleDispatch('synonymous'); return }
      if (matchesHotkey(e, 'toggleAntithetic')) { e.preventDefault(); toggleDispatch('antithetic'); return }
      if (matchesHotkey(e, 'toggleSynthetic')) { e.preventDefault(); toggleDispatch('synthetic'); return }
      if (matchesHotkey(e, 'toggleStaircase')) { e.preventDefault(); toggleDispatch('staircase'); return }
      if (matchesHotkey(e, 'toggleChiasmus')) { e.preventDefault(); toggleDispatch('chiasmus'); return }
      if (matchesHotkey(e, 'toggleTsk')) { e.preventDefault(); toggleDispatch('tsk'); return }
      if (matchesHotkey(e, 'toggleDirect')) { e.preventDefault(); toggleDispatch('direct'); return }
      if (matchesHotkey(e, 'toggleAllusion')) { e.preventDefault(); toggleDispatch('allusion'); return }
      if (matchesHotkey(e, 'toggleEcho')) { e.preventDefault(); toggleDispatch('echo'); return }
      if (matchesHotkey(e, 'toggleTimes')) { e.preventDefault(); toggleDispatch('times'); return }
      if (matchesHotkey(e, 'togglePlaces')) { e.preventDefault(); toggleDispatch('places'); return }
      if (matchesHotkey(e, 'toggleIsaiah')) { e.preventDefault(); toggleDispatch('isaiah'); return }

      // Alt+Arrow for history (browser-like)
      if (e.altKey && e.key === 'ArrowLeft') { e.preventDefault(); doHistoryBack(); return }
      if (e.altKey && e.key === 'ArrowRight') { e.preventDefault(); doHistoryForward(); return }

      // ? opens hotkey cheat sheet (Shift+/)
      if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault(); setShowCheatsheet(p => !p); return
      }
      // / always opens command
      if (e.key === '/') { e.preventDefault(); setShowCommand(true); return }
      if (e.key === 'Escape') { setShowChat(false); setShowHistory(false); setShowCommand(false); setShowSettings(false); setShowCheatsheet(false); setRenamingWs(null); return }

      // Arrow navigation — these are hardcoded since they map to physical arrow keys
      if (isChapterView) { if (e.key === 'ArrowLeft') { e.preventDefault(); goPrevChapter() }; if (e.key === 'ArrowRight') { e.preventDefault(); goNextChapter() } }
      else if (viewLevel === 'book') { if (e.key === 'ArrowLeft') { e.preventDefault(); goPrevBookStay() }; if (e.key === 'ArrowRight') { e.preventDefault(); goNextBookStay() } }
      else if (viewLevel === 'work') { if (e.key === 'ArrowLeft') { e.preventDefault(); goPrevWork() }; if (e.key === 'ArrowRight') { e.preventDefault(); goNextWork() } }
      else if (viewLevel === 'library') { if (e.key === 'ArrowLeft') { e.preventDefault(); goPrevWork() }; if (e.key === 'ArrowRight') { e.preventDefault(); goNextWork() }; if (e.key === 'Enter') { e.preventDefault(); goDownLevel() } }
      else if (viewLevel === 'work') { if (e.key === 'Enter') { e.preventDefault(); goDownLevel() } }
      if (matchesHotkey(e, 'goUp')) { e.preventDefault(); goUpLevel() }
      if (matchesHotkey(e, 'goDown')) { e.preventDefault(); goDownLevel() }
    }
    window.addEventListener('keydown', handleKey); return () => window.removeEventListener('keydown', handleKey)
  }, [chapter, isChapterView, viewLevel, goPrevChapter, goNextChapter, goPrevBookStay, goNextBookStay, goUpLevel, goDownLevel, goPrevWork, goNextWork, doHistoryBack, doHistoryForward, toggleDarkMode, changeFontSize, openTab, book, matchesHotkey, toggleDispatch])

  const currentWorkTitle = nav?.flat[nav.idx]?.workTitle || ''; const currentBookTitle = nav?.flat[nav.idx]?.bookTitle || book

  const handleChatNavigate = (b, ch) => {
    const bt = resolveBookTitle(b)
    if (currentTab?.id) goToChapter(currentTab.id, b, ch, `${bt} ${ch}`)
    else openTab(b, ch, { label: `${bt} ${ch}` })
  }
  const handleChatOpenTab = (b, ch, opts = {}) => { openTab(b, ch, { ...opts, label: `${resolveBookTitle(b)} ${ch}` }) }
  const handleCommandNav = useCallback((bookId, chapter, isNewTab) => {
    const bt = resolveBookTitle(bookId)
    if (isNewTab) openTab(bookId, chapter, { label: `${bt} ${chapter}` })
    else if (currentTab?.id) goToChapter(currentTab.id, bookId, chapter)
    setShowCommand(false)
  }, [currentTab?.id, openTab, resolveBookTitle])

  // Open a chat tab (clears any stale initialMessage)
  const handleOpenChat = useCallback(() => {
    setChatInitialMsg('')
    openChatTab()
  }, [openChatTab])

  const handleCommandChat = useCallback((message) => {
    setChatInitialMsg(message || '')
    setShowChat(true)
    setShowCommand(false)
  }, [])

  // highlightVerse: from search results or tab highlights
  const highlightVerse = currentTab?.highlights?.[0] || null

  const renderMainContent = () => {
    if (showHistory) return <ConversationHistory onNavigate={handleChatNavigate} onClose={() => setShowHistory(false)} />
    if (viewLevel === 'library') return <LibraryView bookData={bookData} onNavigate={handleChatNavigate} />
    if (viewLevel === 'work' && viewRef) return <WorkView workId={viewRef} />
    if (viewLevel === 'book') return <BookView bookId={book} />
    // Chat view — render ChatPanel inline
    if (viewLevel === 'chat') {
      return (
        <ChatPanel
          variant="tab"
          open={true}
          initialMessage={chatInitialMsg}
          onNavigate={handleChatNavigate}
          onOpenTab={handleChatOpenTab}
          onClose={() => {}}
        />
      )
    }
    // Study view — render StudyViewer
    if (viewLevel === 'study' && viewRef) {
      // Load study from API using the slug
      const fetchStudy = async () => {
        const res = await fetch(`/api/v1/studies/published/${viewRef}`)
        const data = await res.json()
        if (!data.ok) throw new Error(data.error || 'Failed to load study')
        return data.data
      }
      return (
        <StudyViewer
          onFetch={fetchStudy}
          onNavigate={handleChatNavigate}
          onOpenTab={(b, ch, opts) => openTab(b, ch, opts)}
          showQuickAsk={showQuickAsk}
          onChatOpen={(msg) => { setChatInitialMsg(msg); setShowChat(true) }}
          guideId={null}
        />
      )
    }
    return <ChapterView book={book} chapter={chapter} poetryMode={poetryMode} highlightVerse={highlightVerse} />
  }

  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors" style={{ fontSize: `${fontSize}%` }}>
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/80 dark:bg-neutral-950/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800 px-4 py-2">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-neutral-900 dark:text-neutral-100">
              {currentWorkTitle && <span className="text-neutral-400 dark:text-neutral-500 font-normal text-sm mr-2">{currentWorkTitle}</span>}
              {currentBookTitle}
            </h1>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-neutral-400 dark:text-neutral-500">
            {/* Search bar — always visible */}
            <SearchBar onNavigate={handleChatNavigate} onOpenTab={handleChatOpenTab} bookData={bookData} />

            {/* Command palette */}
            <button onClick={() => setShowCommand(true)} className="px-2 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0"
              title={`Go to (${getHotkey('command')})`}>:</button>

            {/* History (browser-style) */}
            <span className="flex items-center gap-0.5 px-1 py-0.5 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
              <button onClick={doHistoryBack} disabled={!history.canGoBack}
                className="px-1.5 py-0.5 rounded hover:bg-white dark:hover:bg-neutral-700 cursor-pointer disabled:opacity-25 disabled:cursor-not-allowed shrink-0 text-xs transition-colors"
                title={`Back (${getHotkey('historyBack')} or Alt+←)`}>←</button>
              <span className="w-px h-3 bg-neutral-200 dark:bg-neutral-600" />
              <button onClick={doHistoryForward} disabled={!history.canGoForward}
                className="px-1.5 py-0.5 rounded hover:bg-white dark:hover:bg-neutral-700 cursor-pointer disabled:opacity-25 disabled:cursor-not-allowed shrink-0 text-xs transition-colors"
                title={`Forward (${getHotkey('historyForward')} or Alt+→)`}>→</button>
            </span>

            {/* Font size */}
            <button onClick={() => changeFontSize(-1)} className="px-1.5 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0"
              title={`Smaller (${getHotkey('fontDown')})`}>A−</button>
            <span className="text-[9px] w-5 text-center shrink-0">{fontSize}%</span>
            <button onClick={() => changeFontSize(1)} className="px-1.5 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0"
              title={`Larger (${getHotkey('fontUp')})`}>A+</button>

            {/* Dark mode */}
            <button onClick={toggleDarkMode} className="px-2 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0"
              title={`Dark mode (${getHotkey('darkMode')})`}>{darkMode ? '☀' : '☾'}</button>

            {/* History */}
            <button onClick={() => setShowHistory(p => !p)} className="px-2 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0"
              title="Conversation History">🕐</button>

            {/* Chat (opens a chat tab) */}
            <button onClick={handleOpenChat} className="px-2 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0"
              title={`Chat (${getHotkey('chat')})`}>💬</button>

            {/* Isaiah structure */}
            <button onClick={() => setShowStructure(true)}
              className="px-2 py-1 rounded-full border border-indigo-300 dark:border-indigo-700 text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-all cursor-pointer font-medium shrink-0"
              title={`Isaiah Structure (${getHotkey('structureModal')})`}>⟷</button>

            {/* Settings */}
            <button onClick={() => setShowSettings(true)}
              className="px-2 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0"
              title={`Settings (${getHotkey('settingsPanel')})`}>⚙</button>
          </div>
        </div>
      </header>

      {/* Workspace tabs */}
      <div className="bg-neutral-100 dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 px-2 pt-1 flex items-center gap-0.5 overflow-x-auto tab-scroll">
        {workspaces.map(ws => (
          <div key={ws.id} className={`flex items-center gap-1 px-3 py-1.5 rounded-t cursor-pointer text-xs font-medium border-t border-l border-r transition-colors ${ws.id === activeWorkspace ? 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-800 dark:text-neutral-200' : 'bg-neutral-50 dark:bg-neutral-900 border-transparent text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300'}`}>
            {renamingWs === ws.id ? (
              <input value={renameValue} onChange={e => setRenameValue(e.target.value)}
                onBlur={() => { renameWorkspace(ws.id, renameValue); setRenamingWs(null) }}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === 'Escape') { renameWorkspace(ws.id, renameValue); setRenamingWs(null) } }}
                className="w-20 text-xs bg-transparent border-b border-blue-400 outline-none" autoFocus />
            ) : (
              <span onClick={() => selectWorkspace(ws.id)} onDoubleClick={() => { setRenamingWs(ws.id); setRenameValue(ws.name) }} className="cursor-pointer">{ws.name}</span>
            )}
            <button onClick={e => { e.stopPropagation(); deleteWorkspace(ws.id) }} className="text-neutral-300 dark:text-neutral-600 hover:text-neutral-500 dark:hover:text-neutral-400 ml-1 cursor-pointer">&times;</button>
          </div>
        ))}
        <button onClick={() => newWorkspace()} className="px-2 py-1.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-sm font-medium">+</button>
      </div>

      {/* Chapter tabs */}
      {currentWorkspace && (
        <div className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 px-2 flex items-center gap-0.5 overflow-x-auto tab-scroll min-h-[32px]">
          {currentWorkspace.tabs.map(tab => (
            <div key={tab.id} onClick={() => selectTab(tab.id)}
              className={`flex items-center gap-1 px-2.5 py-1 cursor-pointer text-xs border-b-2 transition-colors shrink-0 ${tab.id === activeTab ? 'text-blue-700 dark:text-blue-400 border-blue-500 dark:border-blue-400 font-medium' : 'text-neutral-500 dark:text-neutral-400 border-transparent hover:text-neutral-700 dark:hover:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600'}`}
              onMouseDown={e => { if (e.button === 1) { e.preventDefault(); closeTab(tab.id) } }}
              title={`${tab.label} (click to activate, middle-click to close)`}>
              <span>{tab.label}</span>
              {tab.view !== 'chapter' && <span className="text-[9px] text-neutral-400 font-mono">[{tab.view}]</span>}
              <button onClick={e => { e.stopPropagation(); closeTab(tab.id) }} className="text-neutral-300 dark:text-neutral-600 hover:text-neutral-500 dark:hover:text-neutral-400 ml-0.5 cursor-pointer"
                title="Close tab">&times;</button>
            </div>
          ))}
          <button onClick={() => openTab(book, chapter, { label: `${bookTitle} ${chapter}` })}
            className="px-2 py-1 rounded-md text-neutral-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer text-sm shrink-0 border border-dashed border-transparent hover:border-blue-200 dark:hover:border-blue-800 transition-colors"
            title="New tab (Ctrl+T)">+</button>
        </div>
      )}

      {/* Chapter controls */}
      {isChapterView && (
        <div className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
          <div className="max-w-6xl mx-auto flex items-center gap-2 px-4 py-1.5">
            <button onClick={goPrevBookStay} className="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5l-7 7 7 7" opacity="0.5" /></svg></button>
            {nav && (
              <select value={book} onChange={e => goToChapter(currentTab?.id, e.target.value, 1)}
                className="px-2 py-0.5 rounded-lg border border-neutral-300 dark:border-neutral-700 text-xs bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer max-w-[180px]">
                {nav.flat.map(n => (<option key={n.bookId} value={n.bookId}>{n.workTitle !== nav.flat[nav.idx]?.workTitle ? `${n.workTitle} — ` : ''}{n.bookTitle}</option>))}
              </select>
            )}
            <span className="text-neutral-300 dark:text-neutral-600 text-xs">ch.</span>
            <select value={chapter} onChange={e => updateTab(currentTab?.id, { chapter: Number(e.target.value) })}
              className="px-2 py-0.5 rounded-lg border border-neutral-300 dark:border-neutral-700 text-xs bg-white dark:bg-neutral-800 w-16 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer">
              {Array.from({ length: 150 }, (_, i) => (<option key={i+1} value={i+1}>{i+1}</option>))}
            </select>
            <button onClick={goNextBookStay} className="p-1 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19l7-7-7-7" opacity="0.5" /></svg></button>
          </div>
          <ToggleBar />
          <PoetryToggle poetryMode={poetryMode} setPoetryMode={setPoetryMode} />
        </div>
      )}

      {/* Main */}
      <ErrorBoundary>
        <main>{renderMainContent()}</main>
      </ErrorBoundary>

      {/* Overlays */}
      <StructureModal open={showStructure} onClose={() => setShowStructure(false)}
        onNavigate={(ref) => { if (ref && currentTab?.id) { const p = ref.split('.'); if (p.length >= 2) goToChapter(currentTab.id, p[0], parseInt(p[1]) || 1) }; setShowStructure(false) }} />
      <ChatPanel open={showChat} onClose={() => { setShowChat(false); setChatInitialMsg('') }}
        initialMessage={chatInitialMsg}
        onNavigate={handleChatNavigate} onOpenTab={handleChatOpenTab} />
      <CommandInput open={showCommand} onClose={() => setShowCommand(false)}
        allBooks={allBooks}
        onNavigate={handleCommandNav} onChat={handleCommandChat} />

      {/* Settings panel */}
      {/* Hotkey Cheatsheet */}
      {showCheatsheet && <HotkeyCheatsheet onClose={() => setShowCheatsheet(false)} getHotkey={getHotkey} DEFAULT_HOTKEYS={DEFAULT_HOTKEYS} />}

      {showSettings && (
        <SettingsPanel
          onClose={() => setShowSettings(false)}
          hotkeys={hotkeys}
          getHotkey={getHotkey}
          setHotkey={setHotkey}
          resetHotkeys={resetHotkeys}
          DEFAULT_HOTKEYS={DEFAULT_HOTKEYS}
          fontSize={fontSize}
          changeFontSize={changeFontSize}
          darkMode={darkMode}
          toggleDarkMode={toggleDarkMode}
          showQuickAsk={showQuickAsk}
          onToggleQuickAsk={() => persist({ showQuickAsk: !showQuickAsk })}
        />
      )}

      {/* Navigation hints */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40">
        <div className="bg-white/80 dark:bg-neutral-900/80 backdrop-blur border border-neutral-200 dark:border-neutral-700 rounded-full px-4 py-1.5 text-[10px] text-neutral-400 dark:text-neutral-500 flex items-center gap-2 flex-wrap">
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{getHotkey('historyBack')}</kbd>/<kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{getHotkey('historyForward')}</kbd> history</span>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">←</kbd>/<kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">→</kbd> chapter</span>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{getHotkey('goUp')}</kbd> out</span>
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{getHotkey('goDown')}</kbd> in</span>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{getHotkey('command')}</kbd> go</span>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{getHotkey('darkMode')}</kbd> theme</span>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">{getHotkey('settingsPanel')}</kbd> prefs</span>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          <span><kbd className="font-mono bg-neutral-100 dark:bg-neutral-800 px-1 rounded">?</kbd> help</span>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════
// App Root
// ═══════════════════════════════════════════════════════════════

export default function App() {
  return (
    <SettingsProvider>
      <ProgressProvider>
        <TabProvider>
          <ToggleProvider>
            <AppInner />
          </ToggleProvider>
        </TabProvider>
      </ProgressProvider>
    </SettingsProvider>
  )
}
