import React, { useState, useEffect, useMemo, useCallback, useRef, Suspense } from 'react'
import { getInfo, getBooks } from './api'
import { TabProvider, useTabs } from './tabContext.jsx'
import { SettingsProvider, useSettings, useHistory } from './settings.jsx'
import { ProgressProvider, useProgress } from './progress.jsx'
import { parseAndFuzzy, getChapters } from './refParser'
const ChatPanel = React.lazy(() => import('./components/ChatPanel'))
import ConversationHistory from './components/ConversationHistory'
import VerseBlock from './components/VerseBlock'
const StudyViewer = React.lazy(() => import('./components/StudyViewer'))
import SearchBar from './components/SearchBar'
import './fonts.css'
import { ToggleProvider, LayersPopover, useToggles, TOGGLE_DEFS } from './components/ToggleProvider'
import {
  ChevronLeft, ChevronRight, ChevronUp, ChevronDown,
  ChatIcon, GridIcon, SunIcon, MoonIcon,
  GearIcon, CommandIcon, ClockIcon,
  TextSmallIcon, TextLargeIcon,
  BookIcon, MenuIcon, PlusIcon,
} from './icons'
import MobileBottomNav from './components/MobileBottomNav'
import MobileMenuDrawer from './components/MobileMenuDrawer'
import ChiasmPanel from './components/ChiasmPanel'
import StructureModal from './components/StructureModal'
import BookView from './components/BookView'
import WorkView from './components/WorkView'
import LibraryView, { WORK_LABEL } from './components/LibraryView'
import SettingsPanel from './components/SettingsPanel'
import HotkeyCheatsheet from './components/HotkeyCheatsheet'
import ErrorBoundary from './components/ErrorBoundary'
import ChapterView from './components/ChapterView'
import AuthButton from './components/AuthButton'
const HubNoteView = React.lazy(() => import('./components/HubNoteView'))
const MemorizeView = React.lazy(() => import('./components/MemorizeView'))
const HebrewDiagnostic = React.lazy(() => import('./components/HebrewDiagnostic'))
const HebrewLessonView = React.lazy(() => import('./components/HebrewLessonView'))
const HebrewLearnView = React.lazy(() => import('./components/HebrewLearnView'))
const WikiArticleViewer = React.lazy(() => import('./components/WikiArticleViewer'))
const HebrewPassageReader = React.lazy(() => import('./components/HebrewPassageReader'))
const LearnView = React.lazy(() => import('./components/LearnView'))
import TileDashboard from './components/TileDashboard'
import SubjectTabBar from './components/SubjectTabBar'
import useAgentControl from './useAgentControl'

import { getFootnotes, getTskCrossrefs, getChapterGrammar, getChapterConnections, searchVerses } from './api'

// ── Chapter View ──



// ── Book View (real input for filter) ──



// ── Chiasm Panel ──



// ── Command Input (unified: refs, paths, /chat, /help) ──

const TYPE_ICONS = {
  navigate: '📖', search: '🔍', chat: '💬', command: '🎯',
  toggle: '🔘', history: '🕐', help: '❓', structure: '⟷',
  dark: '🌙', font: '🔤', error: '⚠️', autocomplete: '?',
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
}

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
    selectWorkspace, newWorkspace, renameWorkspace, deleteWorkspace, deleteWorkspaces, reorderWorkspaces,
    openTab, closeTab, selectTab, updateTab, goToChapter, goToBook, goToWork, openChatTab,
    moveTab, openMemorizeTab, openWikiTab, openHebrewTab, openKnowledgeTab, openLearnTab, openHubNoteTab,
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
  const [apiConnected, setApiConnected] = useState(true)
  const [poetryMode, setPoetryMode] = useState(false) // default Narrative
  const [showLayers, setShowLayers] = useState(false)
  const [showMainMenu, setShowMainMenu] = useState(false)
  const layersBtnRef = useRef(null)
  const [showStructure, setShowStructure] = useState(false)
  const [showChat, setShowChat] = useState(false); const [chatInitialMsg, setChatInitialMsg] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const [showHebrewLearn, setShowHebrewLearn] = useState(false)
  const [passageStudyRef, setPassageStudyRef] = useState(null)
  const [hebrewLessonId, setHebrewLessonId] = useState(null)  // null = curriculum view, string = lesson view
  const [showHebrewDiagnostic, setShowHebrewDiagnostic] = useState(false)
  const [showHubNotes, setShowHubNotes] = useState(false)
  const [hubNoteId, setHubNoteId] = useState(null)
  const [showTabs, setShowTabs] = useState(true)
  
  // Stable anonymous user_id — persists across sessions via localStorage
  const [userId, setUserId] = useState(() => {
    let uid = localStorage.getItem('scripture_user_id')
    if (!uid) {
      uid = 'anon_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36)
      localStorage.setItem('scripture_user_id', uid)
    }
    return uid
  })
  const [userName, setUserName] = useState(localStorage.getItem('scripture_user_name') || '')
  const [userAvatar, setUserAvatar] = useState(localStorage.getItem('scripture_user_avatar') || '')
  const [showGlobalKeyboard, setShowGlobalKeyboard] = useState(false)
  const [showCommand, setShowCommand] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showCheatsheet, setShowCheatsheet] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const [renamingWs, setRenamingWs] = useState(null); const [renameValue, setRenameValue] = useState('')

  // Mobile nav search state
  const [mobileNavVal, setMobileNavVal] = useState('')
  const [mobileNavResults, setMobileNavResults] = useState([])
  const [mobileNavSel, setMobileNavSel] = useState(0)
  const [showMobileNav, setShowMobileNav] = useState(false)
  const mobileNavRef = useRef(null)
  const mobileNavDebounce = useRef(null)

  const [bookError, setBookError] = useState(null)
  useEffect(() => {
    let retries = 0
    const maxRetries = 2
    const doFetch = () => {
      getBooks()
        .then(r => { setBookData(r.data); window.__bookData = r.data; setBookError(null) })
        .catch(e => {
          if (retries < maxRetries) {
            retries++
            setTimeout(doFetch, 2000 * retries)
          } else {
            setBookError('Could not load library. Check your connection.')
          }
        })
    }
    doFetch()
  }, [])
  useEffect(() => {
    let cancelled = false
    const check = () => {
      getInfo()
        .then(r => { if (!cancelled) { setServerInfo(r.data); setApiConnected(true) } })
        .catch(() => { if (!cancelled) setApiConnected(false) })
    }
    check()
    const interval = setInterval(check, 30000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])
  // Close dropdown menus when clicking outside
  useEffect(() => {
    const handler = () => { setShowMainMenu(false) }
    window.addEventListener('click', handler)
    return () => window.removeEventListener('click', handler)
  }, [])

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
  const tabLabel = currentTab?.label || ''
  const mobileActiveTab = showMobileMenu ? 'menu' : showCommand ? 'command' : viewLevel === 'chapter' || viewLevel === 'book' || viewLevel === 'work' || viewLevel === 'library' ? 'read' : viewLevel === 'chat' ? 'chat' : viewLevel === 'tiles' ? 'tiles' : viewLevel === 'wiki' ? 'wiki' : 'read'
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
    // D&C books are stored as "dc{section}" in nav data — try matching prefix for plain "dc"
    if (bookId === 'dc') return nav?.flat.find(n => n.bookId?.startsWith('dc'))?.workTitle || 'Doctrine and Covenants'
    return nav?.flat.find(n => n.bookId === bookId)?.bookTitle || bookId
  }, [nav])

  // Listen for navigation events from VerseBlock, WikiArticleViewer, etc.
  useEffect(() => {
    const handleNav = (e) => {
      if (e.detail?.ref && typeof e.detail.ref === 'string' && e.detail.ref.startsWith('wiki:')) {
        const entityId = e.detail.ref.slice(5)
        openWikiTab(entityId, `Wiki: ${entityId}`)
        return
      }
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
  }, [currentTab?.id, goToChapter, openTab, resolveBookTitle, openWikiTab])

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
    // D&C: each section is its own book — use flat nav to go between sections
    if (book?.startsWith?.('dc')) {
      if (nav && nav.idx > 0) { const prev = nav.flat[nav.idx - 1]; goToChapter(currentTab.id, prev.bookId, prev.bookId.startsWith('dc') ? parseInt(prev.bookId.replace('dc', '')) : 1) }
      return
    }
    if (chapter > 1) updateTab(currentTab.id, { chapter: chapter - 1 })
    else if (nav && nav.idx > 0) { const prev = nav.flat[nav.idx - 1]; goToChapter(currentTab.id, prev.bookId, prev.bookId.startsWith('dc') ? parseInt(prev.bookId.replace('dc', '')) : 1) }
  }, [currentTab?.id, chapter, nav, book])
  const goNextChapter = useCallback(() => {
    if (!currentTab?.id) return
    // D&C: each section is its own book — use flat nav to go between sections
    if (book?.startsWith?.('dc')) {
      if (nav && nav.idx < nav.flat.length - 1) { const next = nav.flat[nav.idx + 1]; goToChapter(currentTab.id, next.bookId, next.bookId.startsWith('dc') ? parseInt(next.bookId.replace('dc', '')) : 1) }
      return
    }
    const maxCh = getChapters(book).length > 0 ? Math.max(...getChapters(book)) : 150
    if (chapter < maxCh) updateTab(currentTab.id, { chapter: chapter + 1 })
    else if (nav && nav.idx < nav.flat.length - 1) { const next = nav.flat[nav.idx + 1]; goToChapter(currentTab.id, next.bookId, next.bookId.startsWith('dc') ? parseInt(next.bookId.replace('dc', '')) : 1) }
  }, [currentTab?.id, chapter, nav, book])
  const goPrevBookStay = useCallback(() => {
    if (!nav || nav.idx < 0 || !currentTab?.id) return; const prev = nav.flat[nav.idx - 1]; if (prev) goToBook(currentTab.id, prev.bookId, prev.bookTitle)
  }, [nav, currentTab?.id])
  const goNextBookStay = useCallback(() => {
    if (!nav || nav.idx < 0 || !currentTab?.id) return; const next = nav.flat[nav.idx + 1]; if (next) goToBook(currentTab.id, next.bookId, next.bookTitle)
  }, [nav, currentTab?.id])
  const isDc = book?.startsWith?.('dc') || false
  // Work-specific division labels (section, psalm, chapter, etc.)
  const divisionLabel = isDc ? 'sec.' : book === 'psa' ? 'psalm' : book === 'prov' ? 'prov.' : 'ch.'

  const goUpLevel = useCallback(() => {
    if (!currentTab?.id) return
    if (viewLevel === 'chapter') {
      if (isDc) {
        // D&C: skip book level, go directly to work view
        updateTab(currentTab.id, { view: 'work', viewRef: 'dc', label: 'Doctrine & Covenants' })
      } else {
        updateTab(currentTab.id, { view: 'book', viewRef: book, label: nav?.flat[nav.idx]?.bookTitle || book })
      }
    } else if (viewLevel === 'book') {
      const wId = nav?.flat[nav.idx]?.workId || 'ot'
      const wT = bookData?.works?.find(w => w.id === wId)?.title || wId
      updateTab(currentTab.id, { view: 'work', viewRef: wId, label: wT })
    } else if (viewLevel === 'work') {
      // Preserve work ID in viewRef so LibraryView knows where you came from
      const wId = viewRef || nav?.flat[nav.idx]?.workId || 'ot'
      const wT = bookData?.works?.find(w => w.id === wId)?.title || wId
      const firstBook = bookData?.works?.find(w => w.id === wId)?.books?.[0]?.id
      updateTab(currentTab.id, {
        view: 'library', viewRef: wId, label: 'Library',
        ...(firstBook ? { book: firstBook } : {}),
      })
    } else if (viewLevel === 'library') {
      updateTab(currentTab.id, { view: 'tiles', viewRef: null, label: 'Subjects' })
    }
  }, [currentTab?.id, viewLevel, book, nav, bookData, updateTab, isDc])

  const goDownLevel = useCallback(() => {
    if (!currentTab?.id) return
    if (viewLevel === 'tiles') {
      updateTab(currentTab.id, { view: 'library', viewRef: null, label: 'Library' })
    } else if (viewLevel === 'library') {
      const targetWorkId = viewRef || bookData?.works?.find(w => w.books?.some(b => b.id === book))?.id || bookData?.works?.[0]?.id || 'ot'
      const wT = bookData?.works?.find(w => w.id === targetWorkId)?.title || targetWorkId
      const firstBook = bookData?.works?.find(w => w.id === targetWorkId)?.books?.[0]?.id
      updateTab(currentTab.id, {
        view: 'work', viewRef: targetWorkId, label: wT,
        ...(firstBook ? { book: firstBook } : {}),
      })
    } else if (viewLevel === 'work') {
      if (viewRef === 'dc') {
        // D&C: skip book level, go directly to chapter view
        goToChapter(currentTab.id, book, chapter, `${bookTitle} ${chapter}`)
      } else {
        const bTitle = nav?.flat.find(n => n.bookId === book)?.bookTitle || book
        updateTab(currentTab.id, { view: 'book', viewRef: book, label: bTitle })
      }
    } else if (viewLevel === 'book') {
      goToChapter(currentTab.id, book, chapter, `${bookTitle} ${chapter}`)
    }
  }, [currentTab?.id, viewLevel, viewRef, bookData, book, chapter, nav, updateTab, goToChapter, bookTitle, isDc])

  // Navigate between works (left/right in work or library view)
  const goPrevWork = useCallback(() => {
    if (!bookData?.works || !currentTab?.id) return
    const list = bookData.works
    const idx = list.findIndex(w => w.id === viewRef)
    if (idx > 0) {
      const target = list[idx - 1]
      const firstBook = target.books?.[0]
      // Keep label consistent: "Library" for library view, work title for work view
      const label = viewLevel === 'library' ? 'Library' : target.title
      updateTab(currentTab.id, {
        view: viewLevel === 'library' ? 'library' : 'work',
        viewRef: target.id,
        label,
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
      const label = viewLevel === 'library' ? 'Library' : target.title
      updateTab(currentTab.id, {
        view: viewLevel === 'library' ? 'library' : 'work',
        viewRef: target.id,
        label,
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
      if (e.ctrlKey && e.shiftKey && e.key === 'H') { e.preventDefault(); setShowGlobalKeyboard(p => !p); return }

      // Alt+Arrow for history (browser-like)
      if (e.altKey && e.key === 'ArrowLeft') { e.preventDefault(); doHistoryBack(); return }
      if (e.altKey && e.key === 'ArrowRight') { e.preventDefault(); doHistoryForward(); return }

      // ? opens chat
      if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault()
        if (viewLevel === 'chat') return // already on chat tab
        setChatInitialMsg('')
        openChatTab()
        return
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

  const handleChatNavigate = (b, ch, highlights) => {
    const bt = resolveBookTitle(b)
    if (currentTab?.id) {
      goToChapter(currentTab.id, b, ch, `${bt} ${ch}`)
      // Set highlights after navigation
      if (highlights) {
        setTimeout(() => updateTab(currentTab.id, { highlights }), 50)
      }
    } else {
      openTab(b, ch, { label: `${bt} ${ch}`, highlights: highlights || [] })
    }
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

  // Handle commands from the SearchBar (/chat, /dark, etc.)
  const handleSearchCommand = useCallback((cmd) => {
    if (!cmd) return
    switch (cmd.type) {
      case 'chat':
        if (cmd.message) { setChatInitialMsg(cmd.message); setShowChat(true) }
        else handleOpenChat()
        break
      case 'dark':
        toggleDarkMode()
        break
      case 'font':
        if (cmd.direction === 'up') changeFontSize(1)
        else if (cmd.direction === 'down') changeFontSize(-1)
        else if (cmd.size) changeFontSize(parseInt(cmd.size))
        break
      case 'toggle':
        if (cmd.toggle) toggleDispatch(cmd.toggle)
        break
      case 'history':
        setShowHistory(true)
        break
      case 'structure':
        setShowStructure(true)
        break
      case 'help':
        setShowCheatsheet(true)
        break
      case 'search':
        if (cmd.query) setShowCommand(true) // fallback to command palette
        break
    }
  }, [handleOpenChat, toggleDarkMode, changeFontSize, toggleDispatch])

  const openTilesView = useCallback(() => {
    updateTab(currentTab?.id, { view: 'tiles', viewRef: null, label: 'Subjects' })
  }, [currentTab?.id, updateTab])

  const openLibraryView = useCallback(() => {
    const wId = viewRef || bookData?.works?.find(w => w.books?.some(b => b.id === book))?.id || null
    updateTab(currentTab?.id, { view: 'library', viewRef: wId, label: 'Library' })
  }, [currentTab?.id, updateTab, viewRef, book, bookData])

  // ── Split-pane reading ──
  const [showSplitPicker, setShowSplitPicker] = useState(false)
  const [splitTarget, setSplitTarget] = useState({ book: '', chapter: '' })
  const handleOpenSplitPicker = useCallback(() => {
    setSplitTarget({ book: book || 'isa', chapter: chapter ? chapter + 1 : 1 })
    setShowSplitPicker(true)
  }, [book, chapter])
  const handleConfirmSplit = useCallback(() => {
    if (splitTarget.book && splitTarget.chapter && currentTab?.id) {
      updateTab(currentTab.id, {
        companion: { book: splitTarget.book, chapter: parseInt(splitTarget.chapter) || 1 }
      })
      setShowSplitPicker(false)
    }
  }, [splitTarget, currentTab?.id, updateTab])

  const handleCommandChat = useCallback((message) => {
    setChatInitialMsg(message || '')
    setShowChat(true)
    setShowCommand(false)
  }, [])

  // ── Mobile nav search handler ──
  const executeMobileNav = useCallback((result) => {
    if (!result) return
    setShowMobileNav(false)
    setMobileNavVal('')
    if (result.type === 'navigate' && result.book) {
      handleCommandNav(result.book, result.chapter, false)
    } else if (result.type === 'chat') {
      handleCommandChat(result.message || '')
    } else if (result.type === 'search' && result.query) {
      // Open command palette with a /search prefix
      setShowCommand(true)
    } else if (result.type === 'command') {
      handleSearchCommand(result)
    } else if (result.type === 'history') {
      setShowHistory(true)
    } else if (result.type === 'structure') {
      setShowStructure(true)
    }
  }, [handleCommandNav, handleCommandChat, handleSearchCommand])

  const handleMobileNavInput = useCallback((val) => {
    setMobileNavVal(val)
    setMobileNavSel(0)
    if (!val.trim()) { setMobileNavResults([]); setShowMobileNav(false); return }
    setShowMobileNav(true)

    clearTimeout(mobileNavDebounce.current)
    mobileNavDebounce.current = setTimeout(() => {
      // Try fuzzy navigation parsing first
      const parsed = parseAndFuzzy(val.trim(), allBooks || [])
      if (parsed.type === 'navigate' && parsed.results?.length > 0) {
        setMobileNavResults(parsed.results.map(r => ({
          ...r,
          icon: '📖',
          label: r.label || `${r.book} ${r.chapter}`,
        })))
        return
      }
      // Try /commands
      if (parsed.type === 'chat' || parsed.type === 'search' || parsed.type === 'command' ||
          parsed.type === 'toggle' || parsed.type === 'history' || parsed.type === 'structure') {
        setMobileNavResults(parsed.results || [parsed].map(r => ({
          ...r, icon: r.icon || '⚡',
          label: r.label || r.message || r.query || r.type,
        })))
        return
      }
      // Fallback: show full-text search option
      setMobileNavResults([{
        type: 'search', query: val.trim(), icon: '🔍',
        label: `Search: "${val.trim()}"`,
      }])
    }, 200)
  }, [allBooks])

  // Close mobile nav dropdown on click outside
  useEffect(() => {
    const handler = (e) => {
      if (mobileNavRef.current && !mobileNavRef.current.contains(e.target)) {
        setShowMobileNav(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // ── Touch / pinch handlers for mobile zoom ──
  const touchRef = useRef(null)
  const handleTouchStart = useCallback((e) => {
    if (e.touches.length === 2) {
      touchRef.current = {
        dist: Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY),
      }
    }
  }, [])
  const handleTouchEnd = useCallback(() => {
    touchRef.current = null
  }, [])
  const handleTouchMove = useCallback((e) => {
    // Two finger pinch: zoom control
    if (e.touches.length === 2 && touchRef.current) {
      e.preventDefault() // Prevent browser zoom
      touchRef.current.moved = true
      const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY)
      const threshold = 40
      if (Math.abs(dist - touchRef.current.dist) > threshold) {
        if (dist > touchRef.current.dist) {
          goDownLevel() // pinch out → zoom in
        } else {
          goUpLevel() // pinch in → zoom out
        }
        touchRef.current.dist = dist
      }
    }
  }, [goDownLevel, goUpLevel])

  // ── Mobile UI auto-hide on scroll ──
  const [uiVisible, setUiVisible] = useState(true)
  const lastScrollY = useRef(0)
  const mainRef = useRef(null)
  const lastTapRef = useRef(0)  // for double-tap detection
  const handleMainScroll = useCallback(() => {
    const el = mainRef.current
    if (!el) return
    const dy = el.scrollTop - lastScrollY.current
    if (dy > 15) setUiVisible(false)
    else if (dy < -10) setUiVisible(true)
    lastScrollY.current = el.scrollTop
  }, [])
  const handleMainClick = useCallback(() => {
    // Double-tap to toggle UI visibility (bars hide/show)
    const now = Date.now()
    if (now - lastTapRef.current < 300) {
      setUiVisible(v => !v)
      lastTapRef.current = 0
    } else {
      lastTapRef.current = now
    }
  }, [])

  // highlightVerse: from search results or tab highlights
  const highlightVerse = currentTab?.highlights?.[0] || null

  // Passage study overlay
  if (passageStudyRef) {
    return (
      <div className="fixed inset-0 z-50 bg-white dark:bg-neutral-950">
        <HebrewPassageReader verseRef={passageStudyRef} onClose={() => setPassageStudyRef(null)} />
      </div>
    )
  }

  const renderMainContent = () => {
    if (showHebrewDiagnostic) {
      return (
        <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading diagnostic...</div>}>
          <HebrewDiagnostic onComplete={() => { setShowHebrewDiagnostic(false); setShowHebrewLearn(true) }} />
        </Suspense>
      )
    }
    if (hebrewLessonId !== null) {
      return (
        <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading lesson...</div>}>
          <HebrewLessonView nodeId={hebrewLessonId} onBack={() => setHebrewLessonId(null)} />
        </Suspense>
      )
    }
    if (showHubNotes) {
      return (
        <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading paths...</div>}>
          <HubNoteView hubId={hubNoteId} onNavigate={(v) => { const p = v.split('.'); if (p.length >= 2) handleChatNavigate?.(p[0], parseInt(p[1])||1) }} onGraph={(v) => window.open(`/graph?verse=${v}`, '_blank')} />
        </Suspense>
      )
    }
    if (showHebrewLearn) {
      return (
        <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading curriculum...</div>}>
          <HebrewLearnView onOpenLesson={(nodeId) => setHebrewLessonId(nodeId)} />
        </Suspense>
      )
    }
    if (showHistory) return <ErrorBoundary><ConversationHistory onNavigate={handleChatNavigate} onClose={() => setShowHistory(false)} /></ErrorBoundary>
    if (viewLevel === 'library') return <LibraryView bookData={bookData} bookError={bookError} onRetry={() => { setBookError(null); getBooks().then(r => { setBookData(r.data); window.__bookData = r.data }).catch(() => { setBookError('Still could not load.') }) }} onNavigate={handleChatNavigate} />
    if (viewLevel === 'work' && viewRef) return <WorkView workId={viewRef} />
    if (viewLevel === 'book') return <BookView bookId={book} />
    // Chat view — render ChatPanel inline
    if (viewLevel === 'chat') {
      return (
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400">Loading chat...</div>}>
          <ChatPanel
          variant="tab"
          open={true}
          initialMessage={chatInitialMsg}
          onNavigate={handleChatNavigate}
          onOpenTab={handleChatOpenTab}
          onClose={() => {}}
        />
      </Suspense>
      )
    }
    // Memorize view
    if (viewLevel === 'memorize') {
      return (
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400">Loading memorize...</div>}>
          <MemorizeView />
        </Suspense>
      )
    }
    // Tiles view — subject/chapter dashboard
    if (viewLevel === 'tiles') {
      return (
        <TileDashboard
          workspaces={workspaces}
          activeWorkspace={activeWorkspace}
          activeTab={activeTab}
          onSelectWorkspace={selectWorkspace}
          onNewWorkspace={newWorkspace}
          onRenameWorkspace={renameWorkspace}
          onDeleteWorkspace={deleteWorkspace}
          onDeleteWorkspaces={deleteWorkspaces}
          onReorderWorkspaces={reorderWorkspaces}
          onSelectTab={selectTab}
          onCloseTab={closeTab}
          onMoveTab={moveTab}
          onOpenTab={openTab}
          book={book} chapter={chapter} bookTitle={bookTitle}
        />
      )
    }
    // Wiki view — render WikiArticleViewer
    if (viewLevel === 'wiki') {
      return (
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading wiki...</div>}>
          <WikiArticleViewer
            entityId={viewRef}
            onNavigate={(eid) => updateTab(currentTab?.id, { view: 'wiki', viewRef: eid, label: `Wiki: ${eid}` })}
            onOpenTab={(b, ch, opts) => openTab(b, ch, opts)}
          />
        </Suspense>
      )
    }

    // Passage study view — Hebrew word-by-word reader
    if (viewLevel === 'passage-study' && viewRef) {
      return (
        <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading passage reader...</div>}>
          <HebrewPassageReader verseRef={viewRef} onClose={() => dispatch({ type: 'CLOSE_TAB' })} />
        </Suspense>
      )
    }

    // HubNote tab view
    if (viewLevel === 'hubnote') {
      return (
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading study path...</div>}>
          <HubNoteView hubId={viewRef} onNavigate={(v) => { const p = v.split('.'); if (p.length >= 2) handleChatNavigate?.(p[0], parseInt(p[1])||1) }} onGraph={(v) => window.open(`/graph?verse=${v}`, '_blank')} />
        </Suspense>
      )
    }

    // Hebrew view — if viewRef is set, show lesson; otherwise show curriculum
    if (viewLevel === 'hebrew') {
      if (viewRef && typeof viewRef === 'string' && !viewRef.startsWith('heb-')) {
        const HebrewLessonView = React.lazy(() => import('./components/HebrewLessonView'))
        return (
          <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading lesson...</div>}>
            <HebrewLessonView
              nodeId={viewRef}
              onBack={(fallbackNodeId) => {
                if (currentTab?.id) {
                  if (fallbackNodeId) {
                    updateTab(currentTab.id, { viewRef: fallbackNodeId, label: `Hebrew: ${fallbackNodeId}` })
                  } else {
                    updateTab(currentTab.id, { viewRef: null, label: 'Biblical Hebrew' })
                  }
                }
              }}
              onNavigate={(verseId) => {
                const parts = verseId.split('.')
                if (parts.length >= 2) {
                  handleChatNavigate?.(parts[0], parseInt(parts[1]) || 1)
                }
              }}
            />
          </Suspense>
        )
      }
      return (
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading Hebrew...</div>}>
          <HebrewLearnView onOpenLesson={(nodeId) => {
            if (currentTab?.id) updateTab(currentTab.id, { viewRef: nodeId, label: `Hebrew: ${nodeId}` })
          }} />
        </Suspense>
      )
    }

    // Learn view
    if (viewLevel === 'learn') {
      return (
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading learn...</div>}>
          <LearnView userId={userId} onBack={() => {}} />
        </Suspense>
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
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400">Loading study...</div>}>
          <StudyViewer
            onFetch={fetchStudy}
            onNavigate={handleChatNavigate}
            onOpenTab={(b, ch, opts) => openTab(b, ch, opts)}
            showQuickAsk={showQuickAsk}
            onChatOpen={(msg) => { setChatInitialMsg(msg); setShowChat(true) }}
            guideId={null}
          />
        </Suspense>
      )
    }
    // Split-pane reading: if companion is set, render two ChapterViews side by side
    const companion = currentTab?.companion
    if (companion?.book && companion?.chapter) {
      return (
        <div className="flex h-full">
          <div className="flex-1 min-w-0 overflow-y-auto border-r border-neutral-200 dark:border-neutral-700">
            <ChapterView book={book} chapter={chapter} poetryMode={poetryMode} highlightVerse={highlightVerse}
              onSplit={null}
              companionLabel={null}
              onCloseCompanion={() => {
                if (currentTab?.id) updateTab(currentTab.id, { companion: null })
              }} />
          </div>
          <div className="flex-1 min-w-0 overflow-y-auto bg-neutral-50/50 dark:bg-neutral-900/50">
            <ChapterView book={companion.book} chapter={companion.chapter} poetryMode={poetryMode} highlightVerse={null}
              onSplit={null}
              companionLabel={`${companion.book} ${companion.chapter}`}
              onCloseCompanion={() => {
                if (currentTab?.id) updateTab(currentTab.id, { companion: null })
              }} />
          </div>
        </div>
      )
    }
    return <ChapterView book={book} chapter={chapter} poetryMode={poetryMode} highlightVerse={highlightVerse}
      onSplit={handleOpenSplitPicker}
      companionLabel={null}
      onCloseCompanion={null} />
  }

  return (
    <div className="min-h-screen bg-white dark:bg-neutral-950 text-neutral-900 dark:text-neutral-100 transition-colors" style={{ fontSize: `${fontSize}%` }}>
      {/* Toolbar — desktop only */}
      <header className={`hidden sm:flex sticky top-0 z-40 bg-white/80 dark:bg-neutral-950/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800 transition-transform duration-200 ${uiVisible ? 'translate-y-0' : '-translate-y-full sm:translate-y-0'}`}>
        <div className="max-w-6xl mx-auto flex items-center justify-between h-9 px-2">
          {/* Left: nav arrows + clickable breadcrumb */}
          <div className="flex items-center gap-0.5 text-sm min-w-0">
            {/* Up arrow — zoom out */}
            <button onClick={goUpLevel} className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer"
              title={`Zoom out (${getHotkey('goUp') || '↑'})`}>
              <ChevronUp />
            </button>
            {/* Down arrow — zoom in */}
            <button onClick={goDownLevel} className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer"
              title={`Zoom in (${getHotkey('goDown') || '↓'})`}>
              <ChevronDown />
            </button>

            {/* Clickable breadcrumb or tab label */}
            <h1 className="font-semibold text-neutral-900 dark:text-neutral-100 truncate px-1 select-none text-sm">
              {['chapter', 'book', 'work', 'library'].includes(viewLevel) ? (<>
                {workTitle ? (
                  <button onClick={() => {
                    if (viewLevel !== 'work') {
                      const wId = nav?.flat[nav.idx]?.workId
                      if (wId) goToWork(currentTab?.id, wId, workTitle)
                    }
                  }} className="text-neutral-400 dark:text-neutral-500 font-normal text-[10px] mr-0.5 whitespace-nowrap hover:text-blue-500 dark:hover:text-blue-400 cursor-pointer">
                    {workTitle}
                  </button>
                ) : isLibraryView ? (
                  <span className="text-neutral-400 dark:text-neutral-500 font-normal text-[10px] mr-0.5">Library</span>
                ) : null}
                {isChapterView ? (
                  <button onClick={() => {
                    if (viewLevel !== 'book') goToBook(currentTab?.id, book, bookTitle)
                  }} className="hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer">
                    {bookTitle}
                  </button>
                ) : (
                  <span>{bookTitle}</span>
                )}
                {isChapterView && <span className="font-normal text-neutral-500 dark:text-neutral-400 text-xs"> / {isDc ? 'sec.' : 'ch.'} {chapter}</span>}
              </>) : (
                <span className="text-neutral-800 dark:text-neutral-200">{tabLabel}</span>
              )}
            </h1>

            {/* Left arrow — previous at current level */}
            <button onClick={isChapterView ? goPrevChapter : viewLevel === 'book' ? goPrevBookStay : goPrevWork}
              className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer"
              title={`Previous ${viewLevel === 'library' ? 'work' : viewLevel === 'work' ? 'work' : viewLevel === 'book' ? 'book' : 'chapter'} (←)`}>
              <ChevronLeft />
            </button>
            {/* Right arrow — next at current level */}
            <button onClick={isChapterView ? goNextChapter : viewLevel === 'book' ? goNextBookStay : goNextWork}
              className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer"
              title={`Next ${viewLevel === 'library' ? 'work' : viewLevel === 'work' ? 'work' : viewLevel === 'book' ? 'book' : 'chapter'} (→)`}>
              <ChevronRight />
            </button>
          </div>

          {/* Right: Search + consolidated dropdown menus */}
          <div className="flex items-center gap-0.5 text-neutral-400 dark:text-neutral-500">
            <SearchBar onNavigate={handleChatNavigate} onOpenTab={handleChatOpenTab} bookData={bookData} onCommand={handleSearchCommand} />

            {/* Divider */}
            <span className="w-px h-4 bg-neutral-200 dark:border-neutral-700 mx-0.5 shrink-0" />

            {/* ── Unified Menu dropdown ── */}
            <div className="relative">
              <button onClick={(e) => { e.stopPropagation(); setShowMainMenu(p => !p); setShowStudyMenu(false); setShowToolsMenu(false) }}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer shrink-0 text-[10px] font-medium ${
                  showMainMenu ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600' : 'hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-500'
                }`} title="Menu">
                ☰ Menu ▾
              </button>
              {showMainMenu && (
                <div onClick={(e) => e.stopPropagation()} className="absolute right-0 top-full mt-1 bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg shadow-xl z-50 py-1 min-w-[180px]">
                  <p className="px-3 py-1 text-[9px] font-semibold uppercase tracking-wider text-neutral-400">Study</p>
                  <button onClick={() => { setShowMainMenu(false); openLearnTab() }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">📚 Learn</button>
                  <button onClick={() => { setShowMainMenu(false); openHebrewTab() }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">א Hebrew</button>
                  <button onClick={() => { setShowMainMenu(false); openMemorizeTab() }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">🧠 Memorize</button>
                  <button onClick={() => { setShowMainMenu(false); openHubNoteTab() }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">🗺️ Study Paths</button>
                  <button onClick={() => { setShowMainMenu(false); openWikiTab() }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">📖 Wiki</button>
                  <div className="border-t border-neutral-200 dark:border-neutral-700 my-1" />
                  <p className="px-3 py-1 text-[9px] font-semibold uppercase tracking-wider text-neutral-400">Tools</p>
                  <button onClick={() => { setShowMainMenu(false); handleOpenChat() }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">💬 Chat</button>
                  <button onClick={() => { setShowMainMenu(false); setShowHistory(p => !p) }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">🕐 History</button>
                  <button onClick={() => { setShowMainMenu(false); setShowStructure(true) }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">⊞ Structure</button>
                  <button onClick={() => { setShowMainMenu(false); setShowLayers(p => !p) }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">🎨 Layers</button>
                  <button onClick={() => { setShowMainMenu(false); setShowGlobalKeyboard(p => !p) }} className="w-full text-left px-3 py-2 text-xs hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300 flex items-center gap-2 cursor-pointer">א Keyboard</button>
                </div>
              )}
            </div>

            {/* ── Auth (Google sign-in) ── */}
            <AuthButton userId={userId} userName={userName} userAvatar={userAvatar} onLogin={(u) => {
              localStorage.setItem('scripture_user_name', u.name || '')
              localStorage.setItem('scripture_user_avatar', u.avatar_url || '')
              localStorage.setItem('scripture_auth_user_id', u.user_id || '')
              setUserName(u.name || '')
              setUserAvatar(u.avatar_url || '')
            }} />

            {/* ── Display controls (always visible) ── */}
            <div className="flex items-center gap-0">
              <button onClick={() => changeFontSize(-1)} className="p-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0" title={`Smaller (${getHotkey('fontDown')})`}><TextSmallIcon /></button>
              <span className="text-[9px] w-4 text-center shrink-0 font-mono">{fontSize}%</span>
              <button onClick={() => changeFontSize(1)} className="p-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0" title={`Larger (${getHotkey('fontUp')})`}><TextLargeIcon /></button>
            </div>
            <button onClick={toggleDarkMode} className="p-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0" title={`Dark mode (${getHotkey('darkMode')})`}>
              {darkMode ? <MoonIcon /> : <SunIcon />}
            </button>
            <button onClick={() => setShowSettings(true)} className="p-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0" title={`Settings (${getHotkey('settingsPanel')})`}><GearIcon /></button>
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${apiConnected ? 'bg-green-400' : 'bg-red-400'}`} title={apiConnected ? 'API connected' : 'API disconnected'} />
            <button onClick={() => openWikiTab()} className="p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0 text-xs" title="Wiki">📖</button>
            {viewLevel === 'chapter' && (
              <button onClick={() => setPassageStudyRef(passageStudyRef ? null : `${book}.${chapter}.${verse || 1}`)}
                className={`p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0 text-xs ${passageStudyRef ? 'bg-blue-100 dark:bg-blue-900/30' : ''}`}
                title="Passage Study (Hebrew word-by-word)">📝</button>
            )}
            <button onClick={() => setShowCommand(true)} className="p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0" title={`Go to (${getHotkey('command')})`}><CommandIcon /></button>
          </div>
        </div>
      </header>

      {/* Mobile top bar — location breadcrumb + history arrows */}
      <div className={`flex sm:hidden items-center justify-between h-10 px-2 bg-white/80 dark:bg-neutral-950/80 backdrop-blur-md border-b border-neutral-200 dark:border-neutral-800 sticky top-0 z-40 transition-transform duration-200 ${uiVisible ? 'translate-y-0' : '-translate-y-full'}`}>
        <div className="flex items-center gap-1 text-sm min-w-0 flex-1">
          {/* History back */}
          <button onClick={doHistoryBack} className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 cursor-pointer shrink-0" title="Back">
            <ChevronLeft />
          </button>
          {/* History forward */}
          <button onClick={doHistoryForward} className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 cursor-pointer shrink-0" title="Forward">
            <ChevronRight />
          </button>
          {/* Tappable breadcrumb or tab label */}
          <h1 className="font-semibold text-neutral-900 dark:text-neutral-100 truncate px-1 select-none text-xs min-w-0">
            {['chapter', 'book', 'work', 'library'].includes(viewLevel) ? (<>
              {workTitle ? (
                <button onClick={() => {
                  if (viewLevel !== 'work') {
                    const wId = nav?.flat[nav.idx]?.workId
                    if (wId) goToWork(currentTab?.id, wId, workTitle)
                  }
                }} className="text-neutral-400 dark:text-neutral-500 font-normal mr-0.5 hover:text-blue-500 dark:hover:text-blue-400 cursor-pointer">
                  {workTitle}{' '}
                </button>
              ) : isLibraryView ? (
                <span className="text-neutral-400 dark:text-neutral-500 font-normal mr-0.5">Library </span>
              ) : null}
              {isChapterView ? (
                <button onClick={() => {
                  if (viewLevel !== 'book') goToBook(currentTab?.id, book, bookTitle)
                }} className="hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer">
                  {bookTitle}
                </button>
              ) : (
                <span>{bookTitle}</span>
              )}
              {isChapterView && <span className="font-normal text-neutral-500 dark:text-neutral-400"> / {isDc ? 'sec.' : 'ch.'} {chapter}</span>}
            </>) : (
              <span className="text-neutral-800 dark:text-neutral-200">{tabLabel}</span>
            )}
          </h1>
        </div>
        {/* Right side: compact nav search + Tiles */}
        <div className="flex items-center gap-1 shrink-0">
          <div ref={mobileNavRef} className="relative">
            <input
              type="search" inputMode="search" enterKeyHint="go"
              value={mobileNavVal} onChange={e => handleMobileNavInput(e.target.value)}
              onFocus={() => { if (mobileNavVal.trim()) setShowMobileNav(true) }}
              onKeyDown={e => {
                if (e.key === 'Escape') { setShowMobileNav(false); e.target.blur() }
                if (e.key === 'ArrowDown') { e.preventDefault(); setMobileNavSel(i => Math.min(i + 1, mobileNavResults.length - 1)) }
                if (e.key === 'ArrowUp') { e.preventDefault(); setMobileNavSel(i => Math.max(i - 1, 0)) }
                if (e.key === 'Enter') { e.preventDefault(); executeMobileNav(mobileNavResults[mobileNavSel]) }
              }}
              placeholder="🔍 Go to…"
              className="w-20 sm:w-28 text-[10px] px-1.5 py-1 rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 placeholder-neutral-400 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-all" />
            {showMobileNav && mobileNavResults.length > 0 && (
              <div className="absolute right-0 top-full mt-1 bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 max-h-72 overflow-y-auto z-50 min-w-[220px]">
                {mobileNavResults.map((r, i) => (
                  <button key={i}
                    onClick={() => { executeMobileNav(r); setShowMobileNav(false) }}
                    onMouseEnter={() => setMobileNavSel(i)}
                    className={`w-full text-left px-3 py-2 flex items-center gap-2 cursor-pointer transition-colors text-[11px] ${
                      i === mobileNavSel ? 'bg-blue-100 dark:bg-blue-900/30' : 'hover:bg-neutral-50 dark:hover:bg-neutral-700/50'
                    }`}>
                    <span className="shrink-0">{r.icon || (r.book ? '📖' : r.type === 'chat' ? '💬' : r.type === 'search' ? '🔍' : '⚡')}</span>
                    <span className="truncate text-neutral-700 dark:text-neutral-300">{r.label}</span>
                    {r.book && <span className="ml-auto text-[9px] text-neutral-400 shrink-0">↵ go</span>}
                    {r.type === 'search' && <span className="ml-auto text-[9px] text-neutral-400 shrink-0">↵ search</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button onClick={openTilesView}
            className="px-2 py-1 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0 text-[10px] font-medium text-neutral-500 dark:text-neutral-400" title="Manage subjects and tabs">
            ▦
          </button>
        </div>
      </div>

      {/* Desktop subject tabs */}
      <div className={`transition-transform duration-200 ${uiVisible ? 'translate-y-0' : '-translate-y-full sm:translate-y-0'}`}>
        <SubjectTabBar
          workspaces={workspaces}
          activeWorkspace={activeWorkspace}
          onSelect={selectWorkspace}
          onNew={newWorkspace}
        />
      </div>

      {/* Tab strip — collapsible with ▲/▼ toggle */}
      <div className={`bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 transition-all duration-200 overflow-hidden ${showTabs ? 'max-h-12' : 'max-h-0'} ${uiVisible ? 'opacity-100' : 'opacity-0 sm:opacity-100'}`}>
        <div className="flex items-center min-h-[30px]">
          <button onClick={() => setShowTabs(!showTabs)}
            className="hidden sm:flex items-center justify-center w-5 h-full shrink-0 text-[9px] text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            title={showTabs ? 'Hide tabs' : 'Show tabs'}>
            {showTabs ? '▲' : '▼'}
          </button>
        {/* Workspace selector (desktop only) */}
        <div className="hidden sm:flex items-center gap-0.5 pl-2 pr-1 border-r border-neutral-200 dark:border-neutral-700 shrink-0">
          <span className="text-[10px] font-medium text-neutral-400 dark:text-neutral-500 mr-1">WS</span>
          <select value={activeWorkspace || ''} onChange={e => selectWorkspace(e.target.value)}
            className="text-xs bg-transparent border-none outline-none cursor-pointer text-neutral-600 dark:text-neutral-400 font-medium pr-4 appearance-none"
            style={{ backgroundImage: 'none' }}>
            {workspaces.map(ws => (
              <option key={ws.id} value={ws.id}>{ws.name}</option>
            ))}
          </select>
          <button onClick={() => newWorkspace()} className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-sm leading-none px-0.5" title="New workspace">+</button>
        </div>

        {/* Chapter tabs — always visible (hidden on mobile, use bottom nav) */}
        <div className="hidden sm:flex items-center gap-0.5 overflow-x-auto tab-scroll flex-1 px-1">
          {(currentWorkspace?.tabs || []).map(tab => (
              <div key={tab.id} onClick={() => selectTab(tab.id)}
                className={`flex items-center gap-1 px-2 py-0.5 cursor-pointer text-xs border-b-2 transition-colors shrink-0 ${
                  tab.id === activeTab
                    ? 'text-blue-700 dark:text-blue-400 border-blue-500 dark:border-blue-400 font-medium'
                    : 'text-neutral-500 dark:text-neutral-400 border-transparent hover:text-neutral-700 dark:hover:text-neutral-300 hover:border-neutral-300 dark:hover:border-neutral-600'
                }`}
                onMouseDown={e => { if (e.button === 1) { e.preventDefault(); closeTab(tab.id) } }}
                title={`${tab.label} (click, middle-click to close)`}>
                <span>{tab.label}</span>
                {tab.view !== 'chapter' && <span className="text-[9px] text-neutral-400 font-mono">[{tab.view}]</span>}
                <button onClick={e => { e.stopPropagation(); closeTab(tab.id) }}
                  className="text-neutral-300 dark:text-neutral-600 hover:text-neutral-500 dark:hover:text-neutral-400 ml-0.5 cursor-pointer leading-none"
                  title="Close tab">&times;</button>
              </div>
            ))}

          </div>
        </div>
      </div>

      {/* Main */}
      <ErrorBoundary>
        <main ref={mainRef} className="flex-1 min-h-0"
          onTouchStart={handleTouchStart} onTouchEnd={handleTouchEnd} onTouchMove={handleTouchMove}
          onScroll={handleMainScroll} onClick={handleMainClick}
          style={{ touchAction: 'pan-y', overscrollBehaviorX: 'none' }}>
          {renderMainContent()}
        </main>
      </ErrorBoundary>

      {/* Overlays */}
      <StructureModal open={showStructure} onClose={() => setShowStructure(false)}
        onNavigate={(ref) => { if (ref && currentTab?.id) { const p = ref.split('.'); if (p.length >= 2) goToChapter(currentTab.id, p[0], parseInt(p[1]) || 1) }; setShowStructure(false) }} />
      <Suspense fallback={null}>
        <ChatPanel open={showChat} onClose={() => { setShowChat(false); setChatInitialMsg('') }}
          initialMessage={chatInitialMsg}
          onNavigate={handleChatNavigate} onOpenTab={handleChatOpenTab} />
      </Suspense>
      <CommandInput open={showCommand} onClose={() => setShowCommand(false)}
        allBooks={allBooks}
        onNavigate={handleCommandNav} onChat={handleCommandChat} />

      {/* Split-pane chapter picker */}
      {showSplitPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowSplitPicker(false)}>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl border border-neutral-200 dark:border-neutral-700 p-4 w-72" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-3">Split with chapter</h3>
            <div className="flex items-center gap-2 mb-3">
              <input value={splitTarget.book} onChange={e => setSplitTarget({ ...splitTarget, book: e.target.value })}
                placeholder="Book (e.g. isa)"
                className="flex-1 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-xs bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 placeholder-neutral-400" />
              <input value={splitTarget.chapter} onChange={e => setSplitTarget({ ...splitTarget, chapter: e.target.value.replace(/[^0-9]/g, '') })}
                placeholder="Ch"
                className="w-16 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-xs bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 placeholder-neutral-400 text-center" />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowSplitPicker(false)}
                className="flex-1 px-3 py-1.5 rounded-lg text-xs font-medium text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
                Cancel
              </button>
              <button onClick={handleConfirmSplit}
                className="flex-1 px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 cursor-pointer transition-colors">
                Split
              </button>
            </div>
          </div>
        </div>
      )}

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

      {/* Global Hebrew keyboard (floating at bottom) */}
      {showGlobalKeyboard && (
        <div className="fixed bottom-0 inset-x-0 z-50 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700 p-2 shadow-2xl">
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="text-[10px] text-neutral-500 dark:text-neutral-400 font-medium">Hebrew Keyboard</span>
            <button onClick={() => setShowGlobalKeyboard(false)}
              className="text-[10px] text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">✕</button>
          </div>
          {React.createElement(React.lazy(() => import('./components/HebrewKeyboard')), {
            value: '',
            onCharClick: (c) => {
              // Dispatch keyboard input event for any focused Hebrew input
              const el = document.activeElement
              if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                const start = el.selectionStart || 0
                const end = el.selectionEnd || 0
                el.value = el.value.substring(0, start) + c + el.value.substring(end)
                el.selectionStart = el.selectionEnd = start + c.length
                el.dispatchEvent(new Event('input', { bubbles: true }))
                el.focus()
              }
            },
            onBackspace: () => {
              const el = document.activeElement
              if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                const start = el.selectionStart || 0
                if (start > 0) {
                  el.value = el.value.substring(0, start - 1) + el.value.substring(el.selectionEnd || start)
                  el.selectionStart = el.selectionEnd = start - 1
                  el.dispatchEvent(new Event('input', { bubbles: true }))
                  el.focus()
                }
              }
            },
            onClear: () => {
              const el = document.activeElement
              if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                el.value = ''
                el.dispatchEvent(new Event('input', { bubbles: true }))
                el.focus()
              }
            },
            onDone: () => setShowGlobalKeyboard(false),
          })}
        </div>
      )}

      {/* Mobile: Bottom Navigation — hidden when uiVisible is false (immersion mode) */}
      <MobileBottomNav activeTab={mobileActiveTab} visible={uiVisible} onTab={(tab) => {
        switch (tab) {
          case 'read': {
            setShowCommand(false); setShowMobileMenu(false)
            // Go to Library view if no read tabs exist
            const readTab = currentWorkspace?.tabs?.slice().reverse().find(t => t.view !== 'chat')
            if (readTab && readTab.id !== currentTab?.id) {
              selectTab(readTab.id)
            } else {
              openLibraryView()
            }
            break
          }
          case 'chat': {
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); setHebrewLessonId(null)
            const chatTab = currentWorkspace?.tabs?.find(t => t.view === 'chat')
            if (chatTab) {
              selectTab(chatTab.id)
            } else {
              openChatTab()
            }
            break
          }
          case 'hebrew':
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); setHebrewLessonId(null); openHebrewTab()
            break
          case 'learn':
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); openLearnTab()
            break
          case 'memorize':
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); openMemorizeTab()
            break
          case 'tiles':
            openTilesView(); setShowMobileMenu(false)
            break
          case 'command':
            setShowCommand(true); setShowMobileMenu(false)
            break
          case 'menu':
            setShowMobileMenu(p => !p)
            break
        }
      }} />

      {/* Mobile: Menu Drawer */}
      <MobileMenuDrawer
        open={showMobileMenu}
        onClose={() => setShowMobileMenu(false)}
        onWiki={() => { setShowMobileMenu(false); openWikiTab() }}
        onLayers={() => { setShowMobileMenu(false); setShowLayers(true) }}
        onHistory={() => { setShowMobileMenu(false); setShowHistory(true) }}
        onStructure={() => { setShowMobileMenu(false); setShowStructure(true) }}
        onHebrew={() => { setShowMobileMenu(false); setShowHebrewDiagnostic(true); setHebrewLessonId(null) }}
        onMemorize={() => { setShowMobileMenu(false); openMemorizeTab() }}
        onKnowledge={() => { setShowMobileMenu(false); openLearnTab() }}
        onHubNotes={() => { setShowMobileMenu(false); openHubNoteTab() }}
        darkMode={darkMode}
        onToggleDarkMode={toggleDarkMode}
        fontSize={fontSize}
        onChangeFontSize={changeFontSize}
        onSettings={() => { setShowMobileMenu(false); setShowSettings(true) }}
        authUser={userName || null}
        authAvatar={userAvatar || null}
        onSignIn={() => { setShowMobileMenu(false); document.querySelector('#google-signin-btn')?.click() }}
        onSignOut={() => { localStorage.removeItem('scripture_user_name'); localStorage.removeItem('scripture_user_avatar'); localStorage.removeItem('scripture_auth_user_id'); setUserName(''); setUserAvatar('') }}
      />

      {/* Spacer to prevent content from being hidden behind bottom nav — hidden when UI is hidden */}
      <div className={`sm:hidden transition-all duration-300 ${uiVisible ? 'h-14' : 'h-0'}`} />

    </div>
  )
}

// ── Mobile Bottom Tab Button ──

function TabButton({ icon, label, active, onClick }) {
  return (
    <button onClick={onClick}
      className={`flex flex-col items-center justify-center gap-0.5 px-3 py-1 rounded-lg transition-colors cursor-pointer ${
        active
          ? 'text-indigo-600 dark:text-indigo-400'
          : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-400'
      }`}
      title={label}>
      <span className={active ? '' : 'opacity-70'}>{icon}</span>
      <span className="text-[9px] font-medium leading-tight">{label}</span>
    </button>
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
