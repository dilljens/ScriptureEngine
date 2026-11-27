import React, { useState, useEffect, useMemo, useRef, useCallback, memo } from 'react'
import HebrewVerbDrill from './HebrewVerbDrill'
import HebrewQuiz from './HebrewQuiz'
import HebrewRoom from './HebrewRoom'
import HebrewModePicker, { getGame, loadLearnMode, loadGameId } from './HebrewModePicker'
import GameReviewModal from './GameReviewModal'
import { reportIdleAnswer } from './HebrewIdleBar'
import { markSessionStart, startAutoFlush } from '../lib/analytics'
import AnkiReview from './AnkiReview'
import PassageReader from './PassageReader'
import DailyVerse from './DailyVerse'
import AudioReviewSession from './AudioReviewSession'
import WordTilesView from './WordTilesView'
import GuidedLessonView from './GuidedLessonView'
import { hebrewToCards, drillsToCards, interleaveCards } from '../lib/card-factory'
import { grammarTrackBonus } from '../lib/idle-game'
import { currentSessionToken, hebrewSessionUser } from '../api'
import { retentionPct, forecastMax, heatmapMax, forecastTotal } from '../lib/hebrewStats'

/* ── Dropdown components for compact action menus ── */

function DropdownMenu({ label, color, children }) {
  const [open, setOpen] = useState(false)
  const [alignLeft, setAlignLeft] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // P0: menus opened right-aligned under left-edge buttons (e.g. Tools on
  // 390px) rendered off-viewport. Align toward the viewport instead.
  const toggle = () => {
    if (!open && ref.current) {
      const r = ref.current.getBoundingClientRect()
      setAlignLeft(r.left < 200)
    }
    setOpen(!open)
  }

  const colorMap = {
    amber: 'bg-amber-500 hover:bg-amber-600 text-white',
    teal: 'bg-teal-600 hover:bg-teal-700 text-white',
    neutral: 'bg-neutral-500 hover:bg-neutral-600 text-white',
  }

  return (
    <div className="relative shrink-0" ref={ref}>
      <button onClick={toggle}
        aria-haspopup="menu" aria-expanded={open} aria-label={`${label} menu`}
        className={`touch-target px-2.5 py-1.5 min-h-[36px] rounded-lg text-[10px] font-medium cursor-pointer transition-colors ${colorMap[color] || colorMap.neutral}`}>
        {label} {open ? '▲' : '▼'}
      </button>
      {open && (
        <div className={`absolute top-full mt-1 z-50 min-w-[180px] max-w-[calc(100vw-2rem)] bg-white dark:bg-neutral-900 rounded-xl shadow-xl border border-neutral-200 dark:border-neutral-700 py-1 overflow-hidden ${alignLeft ? 'left-0' : 'right-0'}`}
          onClick={() => setOpen(false)}>
          {children}
        </div>
      )}
    </div>
  )
}

function DropdownItem({ onClick, icon, label, desc }) {
  return (
    <button onClick={onClick}
      className="w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer transition-colors">
      <span className="text-sm shrink-0 w-5 text-center">{icon}</span>
      <div className="min-w-0">
        <div className="text-xs font-medium text-neutral-800 dark:text-neutral-200 truncate">{label}</div>
        {desc && <div className="text-[9px] text-neutral-400 dark:text-neutral-500 truncate">{desc}</div>}
      </div>
    </button>
  )
}

/**
 * HebrewLearnView — curriculum dashboard with gamification.
 * - Server-provided curriculum across Biblical Hebrew learning categories
 * - Server-side streak + XP + badges
 * - 5-minute quick session mode
 * - Category filter tabs
 * - Mastery Map visualization
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

/**
 * LessonRow — one curriculum row. Memoized so parent re-renders (toasts,
 * prefs, queue counts) skip all 696 rows: a row re-renders only when its
 * own node object changes.
 */
const LessonRow = memo(function LessonRow({ node, onOpenLesson, onOpenPassage }) {
  const cs = CATEGORY_STYLES[node.category] || {}
  // Placement (diagnostic) credit unlocks but is NOT practiced
  // mastery — shown distinctly so it never masquerades as mastered.
  const isTestedOut = node.mastery >= 0.8 && node.source === 'placement'
  const isMastered = node.mastery >= 0.8 && !isTestedOut
  const isLearning = node.mastery > 0 && node.mastery < 0.8
  const isLocked = !node.unlocked

  return (
    <button onClick={() => {
      if (isLocked) return
      // Reading lessons open the PassageReader instead of the lesson view
      if (node.category === 'reading' && node.description) {
        const refMatch = node.description.match(/Read\s+([\w]+)\.(\d+)/)
        if (refMatch) {
          onOpenPassage?.(`${refMatch[1]}.${refMatch[2]}.1`, node.id)
          return
        }
      }
      onOpenLesson?.(node.id)
    }} disabled={isLocked}
      className={`lesson-row w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left cursor-pointer group
        ${isLocked ? 'opacity-40 cursor-not-allowed border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/30'
          : isMastered ? `${cs.bg} ${cs.border} hover:shadow-sm`
          : isLearning ? 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 hover:shadow-sm'
          : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm'
        }`}>
      {/* Status dot */}
      <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${
        isLocked ? 'bg-neutral-300 dark:bg-neutral-600'
          : isMastered ? 'bg-green-500'
          : isTestedOut ? 'bg-sky-400'
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
          {isTestedOut && (
            <span className="text-[9px] px-1.5 py-0.5 rounded-full font-medium shrink-0 bg-sky-50 dark:bg-sky-900/20 text-sky-600 dark:text-sky-400 border border-sky-200 dark:border-sky-800"
              title="Diagnostic credit — demonstrated in the placement quiz, not yet practiced">
              ✓ tested out
            </span>
          )}
        </div>
        {node.description && (
          <p className={`text-xs mt-0.5 truncate ${isLocked ? 'text-neutral-400' : 'text-neutral-500 dark:text-neutral-400'}`}>{node.description}</p>
        )}
        {/* Why is this locked? Never leave a dead end unexplained. */}
        {isLocked && (
          <p className="text-[10px] text-amber-600 dark:text-amber-400 mt-0.5 truncate" title="Master the prerequisites (80%+) to unlock">
            🔒 Requires {(node.prerequisites && node.prerequisites.length > 0)
              ? node.prerequisites.map(p => `${p.title} (${Math.round((p.mastery || 0) * 100)}%)`).join(', ')
              : 'an earlier lesson'}
          </p>
        )}
      </div>

      {/* Mastery bar */}
      <div className="w-14 shrink-0">
        <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
          <div className={`h-full rounded-full transition-all ${isMastered ? 'bg-green-500' : isTestedOut ? 'bg-sky-400' : isLearning ? 'bg-amber-500' : 'bg-neutral-300 dark:bg-neutral-600'}`}
            style={{ width: `${node.mastery * 100}%` }} />
        </div>
        <span className="text-[8px] text-neutral-400 dark:text-neutral-500 mt-0.5 block text-right">{Math.round(node.mastery * 100)}%</span>
      </div>

      {/* Learning speed indicator */}
      {!isLocked && node.learning_speed !== undefined && (
        <div className="w-6 shrink-0 flex items-center justify-center" title={
          node.learning_speed > 1.5 ? 'Fast learner on this topic' :
          node.learning_speed >= 0.8 ? 'Normal pace' :
          node.learning_speed >= 0.4 ? 'Needs extra practice' :
          'Struggling — review prerequisites'
        }>
          <span className={`text-xs ${
            node.learning_speed > 1.5 ? 'text-green-500' :
            node.learning_speed >= 0.8 ? 'text-blue-400' :
            node.learning_speed >= 0.4 ? 'text-amber-500' :
            'text-red-500'
          }`}>
            {node.learning_speed > 1.5 ? '⚡' :
             node.learning_speed >= 0.8 ? '→' :
             node.learning_speed >= 0.4 ? '～' :
             '⚠'}
          </span>
        </div>
      )}

      {isLocked && <span className="text-xs text-neutral-400 shrink-0">🔒</span>}
      {!isLocked && !isMastered && <span className="text-xs text-indigo-500 dark:text-indigo-400 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">→</span>}
    </button>
  )
})

export default function HebrewLearnView({ onOpenLesson, onOpenPassage }) {
  const [curriculum, setCurriculum] = useState(null)
  const [gamification, setGamification] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [showMasteryMap, setShowMasteryMap] = useState(false)
  const [showVerbDrill, setShowVerbDrill] = useState(false)
  const [showHebrewReview, setShowHebrewReview] = useState(false)
  const [hebrewReviewCards, setHebrewReviewCards] = useState([])
  const [showPassageReader, setShowPassageReader] = useState(false)
  const [passageInput, setPassageInput] = useState('gen.1.1')
  const [quickMode, setQuickMode] = useState(false)
  const [quickQuestions, setQuickQuestions] = useState([])
  const [quickIdx, setQuickIdx] = useState(0)
  const [timeLeft, setTimeLeft] = useState(300)
  const [quickScore, setQuickScore] = useState(0)
  const [toast, setToast] = useState(null) // {message, type}
  const [showDailyVerse, setShowDailyVerse] = useState(false)
  const [showAudioReview, setShowAudioReview] = useState(false)
  const [audioWords, setAudioWords] = useState([])
  const [showWordTiles, setShowWordTiles] = useState(false)
  const [wordTilesInitial, setWordTilesInitial] = useState([])
  const [wordTilesKind, setWordTilesKind] = useState('words')
  const [showQuiz, setShowQuiz] = useState(false)
  const [showRoom, setShowRoom] = useState(false)
  const [guidedNode, setGuidedNode] = useState(undefined)
  const [showGrammarFocus, setShowGrammarFocus] = useState(false)
  const [focusTopics, setFocusTopics] = useState([])
  const [showStats, setShowStats] = useState(false)
  const [statsData, setStatsData] = useState(null)
  // Anki-style daily pacing: deck options + live queue counts
  const [prefs, setPrefs] = useState({ new_cards_per_day: 10, max_reviews_per_day: 100, desired_retention: 0.9 })
  // Classic Study vs Games — persisted, defaults to classic so existing
  // learners see zero change until they opt into a game.
  const [learnMode, setLearnMode] = useState(loadLearnMode)
  const [activeGameId, setActiveGameId] = useState(loadGameId)
  const [showBrowseInGame, setShowBrowseInGame] = useState(false)
  // In-game practice: a bare node id (lesson quiz) or 'due' (interleaved review).
  const [reviewTarget, setReviewTarget] = useState(null)
  const [queueStats, setQueueStats] = useState(null)
  const [prefsEditing, setPrefsEditing] = useState(false)
  const [prefsDraft, setPrefsDraft] = useState({ new_cards_per_day: 10, max_reviews_per_day: 100, desired_retention: 0.9, goal: '' })
  const [profile, setProfile] = useState(null)

  // Resolve the session-bound user (falls back to 'default' for anonymous
  // learners, so a missing/expired token is never a hard failure). Curriculum,
  // gamification and the review queue are all per-user, so a logged-in session
  // lands review/progress data on the real account instead of the shared
  // 'default' user. Returns '' when anonymous so the API keeps its default.
  const sessionQuery = async () => {
    const uid = await hebrewSessionUser()
    return uid && uid !== 'default' ? `?user_id=${encodeURIComponent(uid)}` : ''
  }

  const sessionHeaders = () => {
    const token = currentSessionToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  // Load everything in ONE round trip (bootstrap: curriculum + gamification
  // + prefs + queue). Falls back to the old 3-fetch path if bootstrap is
  // unavailable (older backend).
  const loadAll = () => {
    setLoading(true)
    sessionQuery().then(async (q) => {
      const amp = q ? '&' + q.slice(1) : ''
      try {
        const r = await fetch(`/api/v1/hebrew/bootstrap?queue_limit=1${amp}`, { headers: sessionHeaders() })
        const d = await r.json()
        if (d.ok && d.data?.curriculum) {
          setCurriculum(d.data.curriculum)
          if (d.data.gamification) setGamification(d.data.gamification)
          if (d.data.prefs) { setPrefs(d.data.prefs); setPrefsDraft(d.data.prefs) }
          if (d.data.queue) setQueueStats(d.data.queue)
          return
        }
      } catch {}
      const [curData, gamData] = await Promise.all([
        fetch(`/api/v1/hebrew/curriculum${q}`, { headers: sessionHeaders() }).then(r => r.json()),
        fetch(`/api/v1/hebrew/gamification${q}`, { headers: sessionHeaders() }).then(r => r.json()),
      ])
      if (curData.ok) setCurriculum(curData.data)
      else setError(curData.detail || 'Failed to load')
      if (gamData.ok) setGamification(gamData.data)
      loadPacing() // fallback path skips bootstrap: fetch pacing separately
    })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(loadAll, [])
  useEffect(() => {
    try { markSessionStart() } catch {}
    const stop = startAutoFlush()
    return stop
  }, [])

  // Learner profile (P1): per-skill mass, production ratio, goal.
  const loadProfile = useCallback(async () => {
    try {
      const uq = await sessionQuery()
      const r = await fetch(`/api/v1/hebrew/profile${uq}`, { headers: sessionHeaders() })
      const d = await r.json()
      if (d.ok) setProfile(d.data)
    } catch {}
  }, [])
  useEffect(() => { loadProfile() }, [loadProfile])

  // Daily pacing refresh (prefs + queue counts). Mount is covered by the
  // bootstrap in loadAll; this stays for post-save refreshes.
  const loadPacing = useCallback(async () => {
    try {
      const uq = await sessionQuery()
      const amp = uq ? '&' + uq.slice(1) : ''
      const [p, q] = await Promise.all([
        fetch(`/api/v1/hebrew/prefs${uq}`, { headers: sessionHeaders() }).then(r => r.json()),
        fetch(`/api/v1/hebrew/review-queue?limit=1${amp}`, { headers: sessionHeaders() }).then(r => r.json()),
      ])
      if (p.ok) { setPrefs(p.data); setPrefsDraft(p.data) }
      if (q.ok) setQueueStats(q.data)
      loadProfile()
    } catch {}
  }, [loadProfile])

  const savePrefs = async () => {
    try {
      const r = await fetch('/api/v1/hebrew/prefs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify({
          ...prefsDraft,
          new_cards_per_day: Math.max(0, parseInt(prefsDraft.new_cards_per_day) || 0),
          max_reviews_per_day: Math.max(0, parseInt(prefsDraft.max_reviews_per_day) || 0),
          desired_retention: Math.min(0.99, Math.max(0.7, parseFloat(prefsDraft.desired_retention) || 0.9)),
          session_token: currentSessionToken(),
        }),
      })
      const d = await r.json()
      if (d.ok) { setPrefs(d.data); setPrefsEditing(false); loadPacing() }
    } catch {}
  }

  // Quick-session + audio ratings earn FSRS credit. Know it = Good (3),
  // Skip = Again (1) on the same schedule everything else uses — a review
  // that schedules nothing is a trap. Node ids resolve server-side from
  // Hebrew text when missing.
  const rateKnownSkip = async (hebrew, nodeId, known) => {
    const t0 = Date.now()
    try {
      await fetch('/api/v1/hebrew/fsrs/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify({ hebrew, node_id: nodeId || undefined, rating: known ? 3 : 1, session_token: currentSessionToken() }),
      })
    } catch {}
    reportIdleAnswer(known, Date.now() - t0, { source: 'quick', hebrew })
  }

  // Audio-review ratings earn FSRS credit via Hebrew-text node resolution
  const handleAudioRate = async (word, rating) => {
    const t0 = Date.now()
    try {
      await fetch('/api/v1/hebrew/fsrs/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...sessionHeaders() },
        body: JSON.stringify({ hebrew: word.hebrew, rating, session_token: currentSessionToken() }),
      })
    } catch {}
    reportIdleAnswer(rating >= 3, Date.now() - t0, { source: 'audio', hebrew: word.hebrew })
  }

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  // Start quick session
  const startQuickSession = () => {
    if (!curriculum?.nodes) return
    const unlocked = curriculum.nodes.filter(n => n.unlocked && n.mastery < 0.8)
    if (unlocked.length === 0) {
      unlocked.push(...curriculum.nodes.filter(n => n.mastery >= 0.8))
    }
    const shuffled = [...unlocked].sort(() => Math.random() - 0.5).slice(0, 10)
    setQuickQuestions(shuffled)
    setQuickIdx(0)
    setQuickScore(0)
    setTimeLeft(300)
    setQuickMode(true)
  }

  // Frequency-vocab bands → 3-way AnkiReview (hebrew-card-rules.md).
  // schedulable=1 keeps only words that resolve to a lesson node, so every
  // rating persists into the FSRS schedule. Offset slices the filtered list.
  const startVocabBand = async (top, cutoff, offset) => {
    try {
      const r = await fetch(`/api/v1/vocabulary?top=${top}&cutoff=${cutoff}&schedulable=1`)
      const d = await r.json()
      const words = (d.data?.words || []).filter(w => w.hebrew && w.gloss).slice(offset)
      setHebrewReviewCards(words.map((w, i) => ({
        id: `vocab-${offset}-${i}`, node_id: '', hebrew: w.hebrew, gloss: w.gloss,
        transliteration: w.transliteration || '', lemma: w.lemma || '',
      })))
    } catch {}
    setShowHebrewReview(true)
  }

  // Quick session timer
  useEffect(() => {
    if (!quickMode) return
    if (timeLeft <= 0) { setQuickMode(false); return }
    const timer = setInterval(() => setTimeLeft(t => t - 1), 1000)
    return () => clearInterval(timer)
  }, [quickMode, timeLeft])

  // Perf (Track D2): grouping rebuilt only when nodes/filter change — toast,
  // prefs and queue updates re-render without touching 696 rows (memo below).
  // The 'tracks' pseudo-filter shows the grammar grid, not the lesson list.
  // NOTE: these hooks must stay ABOVE every early return (rules of hooks) —
  // they run on `nodes ?? []` while the curriculum is still loading.
  const nodes = curriculum?.nodes ?? []
  const filtered = useMemo(
    () => (filter === 'all' ? nodes : filter === 'tracks' ? [] : nodes.filter(n => n.category === filter)),
    [nodes, filter])
  const byLevel = useMemo(() => {
    const groups = {}
    for (const n of filtered) {
      if (!groups[n.level]) groups[n.level] = []
      groups[n.level].push(n)
    }
    return groups
  }, [filtered])
  // Grammar tracks grid (Scale Track C): derived from node category+level,
  // no migration. +5% Ohr per complete tier (see IdleBar 📜 chip).
  const trackInfo = useMemo(() => grammarTrackBonus(nodes), [nodes])
  const TRACK_META = [
    { id: 'binyanim', label: 'Binyanim', desc: 'verb stems', icon: 'ע' },
    { id: 'clauses', label: 'Clauses', desc: 'syntax', icon: '⇄' },
    { id: 'nominals', label: 'Nominals', desc: 'nouns + grammar', icon: 'ד' },
  ]

  // One screen on phones: land exactly on the game at open (the sticky
  // workshop then locks to the viewport — no hunting, no page scroll).
  // NOTE: hooks must stay ABOVE every early return (rules of hooks).
  const gameTopRef = useRef(null)
  useEffect(() => {
    if (learnMode === 'game' && !showBrowseInGame && typeof window !== 'undefined' && window.innerWidth < 640) {
      gameTopRef.current?.scrollIntoView({ block: 'start' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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

  const { total, mastered, tested_out, in_progress, locked } = curriculum

  // Passage reader mode
  if (showPassageReader) {
    return (
      <div>
        <div className="max-w-4xl mx-auto px-6 pt-4">
          <div className="flex items-center gap-3 mb-4">
            <button onClick={() => setShowPassageReader(false)}
              className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer shrink-0">
              ← Back to Curriculum
            </button>
            <input type="text" value={passageInput}
              onChange={e => setPassageInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') setShowPassageReader(true) }}
              placeholder="e.g. gen.22.1-19 or isa.55"
              className="flex-1 max-w-xs px-2 py-1 rounded text-xs border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400" />
            <button onClick={() => {
              // Force re-render by toggling key
              setShowPassageReader(false)
              setTimeout(() => setShowPassageReader(true), 50)
            }}
              className="px-2 py-1 rounded text-xs bg-blue-600 text-white hover:bg-blue-700 cursor-pointer font-medium transition-colors">
              Load
            </button>
          </div>
        </div>
        <PassageReader key="passage-reader" passageId={passageInput} />
      </div>
    )
  }

  // Verb drill mode
  if (showVerbDrill) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">Verb Conjugation Drills</h2>
          <button onClick={() => setShowVerbDrill(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
        <HebrewVerbDrill />
      </div>
    )
  }

  // Hebrew review mode — Anki-style flashcard review
  if (showHebrewReview) {
    // Convert curriculum nodes to AnkiReview-compatible cards
    const ankiCards = hebrewReviewCards
      .filter(c => c.data?.hebrew)
      .map(c => ({
        node_id: c.data?.node_id || c.id?.replace(/heb-/, '') || '',
        hebrew: c.data?.hebrew || '',
        gloss: c.data?.gloss || c.data?.definition?.split(' — ')[1] || c.data?.definition || '',
        transliteration: c.data?.transliteration || '',
        modes: c.modes,
      }))

    if (ankiCards.length === 0) {
      return (
        <div className="max-w-lg mx-auto px-6 py-12 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">No words to review right now.</p>
          <button onClick={() => setShowHebrewReview(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
      )
    }

    return (
      <AnkiReview
        cards={ankiCards}
        onComplete={() => {
          setShowHebrewReview(false); setHebrewReviewCards([])
          try {
            const t = currentSessionToken()
            fetch('/api/v1/hebrew/session-summary', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', ...(t ? { Authorization: `Bearer ${t}` } : {}) },
              body: JSON.stringify({ user_id: 'default', session_token: t }),
            }).catch(() => {})
          } catch {}
        }}
        onBack={() => { setShowHebrewReview(false); setHebrewReviewCards([]) }}
        title="Hebrew Review"
      />
    )
  }

  // Daily Verse mode
  if (showDailyVerse) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📆 Verse of the Day</h2>
          <button onClick={() => setShowDailyVerse(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
        <DailyVerse onOpenLesson={(nid) => { setShowDailyVerse(false); onOpenLesson?.(nid) }} />
      </div>
    )
  }

  // Audio review mode
  if (showAudioReview) {
    if (audioWords.length === 0) {
      return (
        <div className="max-w-lg mx-auto px-6 py-12 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">No audio words loaded.</p>
          <button onClick={() => setShowAudioReview(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
      )
    }
    return (
      <div className="max-w-lg mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">🎧 Audio Review</h2>
          <button onClick={() => setShowAudioReview(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back
          </button>
        </div>
        <AudioReviewSession words={audioWords} onComplete={() => setShowAudioReview(false)} onRate={handleAudioRate} />
      </div>
    )
  }

  // Word Tiles: 50 words at once, Anki-style (mastered = 21+ day interval)
  if (showWordTiles) {
    return (
      <WordTilesView initialWords={wordTilesKind === 'words' ? wordTilesInitial : []} kind={wordTilesKind} onClose={() => { setShowWordTiles(false); loadAll() }} />
    )
  }

  // Guided lesson (weakest-topic, knowledge-grounded)
  if (guidedNode !== undefined) {
    return (
      <GuidedLessonView
        nodeId={guidedNode}
        onBack={() => { setGuidedNode(undefined); setShowGrammarFocus(true) }}
        onOpenLesson={(nid) => { setGuidedNode(undefined); setShowGrammarFocus(false); onOpenLesson?.(nid) }}
      />
    )
  }

  // Quiz mode
  if (showGrammarFocus) {
    const blocked = focusTopics.blocked_by || []
    const topics = focusTopics.topics || focusTopics
    const list = Array.isArray(topics) ? topics : []
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">🎯 Grammar Focus</h2>
          <button onClick={() => setShowGrammarFocus(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-4">
          Weakest grammar first — prerequisites already met. Study a topic, then drill it.
        </p>
        {list.length > 0 && (
          <button onClick={() => setGuidedNode(list[0].node_id)}
            className="mb-4 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium cursor-pointer transition-colors">
            ✨ Start guided lesson — {list[0].title.length > 32 ? list[0].title.slice(0, 32) + '…' : list[0].title}
          </button>
        )}
        {list.length === 0 && blocked.length > 0 && (
          <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 mb-3">
            <div className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-2">
              🔒 Grammar unlocks as you master the basics. Closest first:
            </div>
            {blocked.map(b => (
              <div key={b.node_id} className="flex items-center gap-2 py-1">
                <span className="text-sm text-neutral-700 dark:text-neutral-300 flex-1">
                  {b.title} <span className="text-[11px] text-neutral-400">{Math.round((b.mastery || 0) * 100)}%</span>
                </span>
                <button onClick={() => { setShowGrammarFocus(false); onOpenLesson?.(b.node_id) }}
                  className="px-3 py-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium cursor-pointer transition-colors">
                  Study →
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="space-y-3">
          {list.length === 0 && blocked.length === 0 && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">No grammar topics found.</p>
          )}
          {list.map(t => (
            <div key={t.node_id}
              className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
                  {t.category} · L{t.level}
                </span>
                {t.is_new
                  ? <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">NEW</span>
                  : <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">{Math.round((t.mastery || 0) * 100)}%</span>}
                {t.is_leech && <span className="text-[10px] px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300" title="8+ lapses — Anki leech threshold. Consider a mnemonic or breaking this topic down.">🪲 leech</span>}
                <span className="flex-1" />
                <button onClick={() => setGuidedNode(t.node_id)}
                  className="px-4 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium cursor-pointer transition-colors">
                  Guided →
                </button>
                <button onClick={() => { setShowGrammarFocus(false); onOpenLesson?.(t.node_id) }}
                  className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors">
                  Study →
                </button>
              </div>
              <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{t.title}</div>
              <div className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full mt-2 overflow-hidden">
                <div className="h-full bg-purple-500 rounded-full transition-all"
                  style={{ width: `${Math.round((t.mastery || 0) * 100)}%` }} />
              </div>
              <div className="text-[11px] text-neutral-400 mt-1">
                {t.attempts || 0} attempts · {t.lapses || 0} lapses · {t.drill_count || 0} drills available
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Stats panel (B3: retention + forecast + heatmap)
  if (showStats) {
    const ret = statsData?.retention || {}
    const modes30 = ret.by_mode_30d || {}
    const fsrs = ret.fsrs_lifetime_by_mode || {}
    const forecast = statsData?.forecast || []
    const heatmap = statsData?.heatmap || []
    const fmax = forecastMax(forecast)
    const hmax = heatmapMax(heatmap)
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📈 Learning Stats</h2>
          <button onClick={() => setShowStats(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-4">
          True retention (last 30d, graded answers) + FSRS lifetime accuracy per direction + scheduled workload for the next 30 days.
        </p>
        {!statsData && (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">Couldn&rsquo;t load stats — try again.</p>
        )}
        {statsData && (
          <>
            <div className="grid md:grid-cols-2 gap-3 mb-4">
              <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
                <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">Retention · last 30 days</div>
                <div className="text-2xl font-bold text-neutral-800 dark:text-neutral-100">{retentionPct(ret.overall_30d?.rate)}</div>
                <div className="text-[11px] text-neutral-400 mb-2">{ret.overall_30d?.correct ?? 0}/{ret.overall_30d?.attempts ?? 0} correct</div>
                {Object.entries(modes30).map(([m, v]) => (
                  <div key={m} className="flex items-center gap-2 text-xs py-0.5">
                    <span className="w-20 text-neutral-500 dark:text-neutral-400">{m}</span>
                    <div className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                      <div className="h-full bg-green-500 rounded-full" style={{ width: `${Math.round((v.rate ?? 0) * 100)}%` }} />
                    </div>
                    <span className="w-10 text-right font-mono text-neutral-600 dark:text-neutral-300">{retentionPct(v.rate)}</span>
                  </div>
                ))}
                {Object.keys(modes30).length === 0 && (
                  <p className="text-[11px] text-neutral-400">No graded answers yet — quizzes and lessons feed this.</p>
                )}
              </div>
              <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
                <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">FSRS accuracy · lifetime by direction</div>
                {Object.entries(fsrs).map(([m, v]) => (
                  <div key={m} className="flex items-center gap-2 text-xs py-0.5">
                    <span className="w-20 text-neutral-500 dark:text-neutral-400">{m}</span>
                    <div className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.round((v.rate ?? 0) * 100)}%` }} />
                    </div>
                    <span className="w-10 text-right font-mono text-neutral-600 dark:text-neutral-300">{retentionPct(v.rate)}</span>
                  </div>
                ))}
                {Object.keys(fsrs).length === 0 && (
                  <p className="text-[11px] text-neutral-400">No reviews yet — rate some cards.</p>
                )}
                {statsData.suspended_count > 0 && (
                  <p className="text-[11px] text-neutral-400 mt-2">🚫 {statsData.suspended_count} suspended (excluded from forecast)</p>
                )}
              </div>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 mb-3">
              <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-1">
                Due forecast · next 30 days ({forecastTotal(forecast)} scheduled)
              </div>
              <div className="flex items-end gap-[2px] h-20 mt-2">
                {forecast.map(f => (
                  <div key={f.date} title={`${f.date}: ${f.due} due`} className="flex-1 rounded-t bg-indigo-400 dark:bg-indigo-600 min-h-[2px]"
                    style={{ height: `${Math.max(2, Math.round((f.due / fmax) * 100))}%` }} />
                ))}
              </div>
              <div className="flex justify-between text-[10px] text-neutral-400 mt-1">
                <span>today · {forecast[0]?.due ?? 0} due</span>
                <span>+30d</span>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
              <div className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">Activity · last 30 days</div>
              <div className="flex gap-[3px] flex-wrap">
                {heatmap.map(h => (
                  <div key={h.date} title={`${h.date}: ${h.reviews} reviews`}
                    className={`w-4 h-4 rounded ${h.reviews === 0 ? 'bg-neutral-200 dark:bg-neutral-700' : h.reviews < hmax / 3 ? 'bg-green-200 dark:bg-green-900' : h.reviews < (2 * hmax) / 3 ? 'bg-green-400 dark:bg-green-700' : 'bg-green-600 dark:bg-green-500'}`} />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    )
  }

  // Room mode (R4b: one composed session)
  if (showRoom) {
    return (
      <div className="max-w-4xl mx-auto px-2 py-4">
        <HebrewRoom
          onBack={() => { setShowRoom(false); loadAll() }}
          onOpenLesson={onOpenLesson}
        />
      </div>
    )
  }

  // Quiz mode
  if (showQuiz) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <HebrewQuiz
          count={8}
          onBack={() => { setShowQuiz(false); loadAll() }}
          onOpenLesson={(nid) => { setShowQuiz(false); onOpenLesson?.(nid) }}
        />
      </div>
    )
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
          <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">Know it schedules further out · Skip brings it back soon</p>
          <div className="flex gap-2 justify-center mt-3">
            <button onClick={() => { const q = quickQuestions[quickIdx]; rateKnownSkip(q?.hebrew || q?.title, q?.id, true); setQuickIdx(prev => Math.min(prev + 1, quickQuestions.length - 1)); setQuickScore(s => s + 1) }}
              className="px-3 py-1.5 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs font-medium cursor-pointer transition-colors">Know it ✓</button>
            <button onClick={() => { const q = quickQuestions[quickIdx]; rateKnownSkip(q?.hebrew || q?.title, q?.id, false); setQuickIdx(prev => Math.min(prev + 1, quickQuestions.length - 1)) }}
              className="px-3 py-1.5 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-medium cursor-pointer transition-colors">Skip →</button>
          </div>
        </div>
        <button onClick={() => setQuickMode(false)} className="mt-4 w-full py-2 rounded-lg text-sm text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 cursor-pointer transition-colors">
          End session
        </button>
      </div>
    )
  }

  const gam = gamification || {}

  // ── Games mode: focused game screen (progressive disclosure — the full
  // curriculum browse is one tap away, not dumped on top of the game) ──
  if (learnMode === 'game' && !showBrowseInGame) {
    const game = getGame(activeGameId)
    const ActiveGame = game?.Component
    const nextLesson = (nodes || [])
      .filter(n => n.unlocked && n.mastery < 0.8)
      .sort((a, b) => a.level - b.level || a.mastery - b.mastery)[0]
    return (
      <div ref={gameTopRef} className="max-w-4xl mx-auto px-4 sm:px-6 py-6 scroll-mt-12">
        {toast && (
          <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium transition-all animate-slide-down ${
            toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-amber-600 text-white'
          }`}>
            {toast.message}
          </div>
        )}
        <HebrewModePicker mode={learnMode} onMode={setLearnMode} activeGameId={activeGameId} onGame={setActiveGameId} />
        {/* Practice + review live inside the game shell (Letters tab) — the
            earn-loop card below used to slide under the sticky workshop. */}
        {ActiveGame ? <ActiveGame curriculum={curriculum} dueCount={queueStats?.due_count || 0} onOpenReview={setReviewTarget} onBrowseLessons={() => setShowBrowseInGame(true)} /> : null}

        {reviewTarget && (
          <GameReviewModal
            nodeId={reviewTarget === 'due' ? null : reviewTarget}
            title={reviewTarget === 'due'
              ? 'Spaced-repetition review (interleaved)'
              : nextLesson?.title}
            onClose={() => setReviewTarget(null)}
            onFinished={() => { loadAll(); loadPacing() }}
            onOpenLesson={(nid) => { setReviewTarget(null); onOpenLesson?.(nid) }}
          />
        )}
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium transition-all animate-slide-down ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-amber-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-1">Biblical Hebrew</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">{total} lessons · {mastered} mastered{tested_out > 0 ? ` · ${tested_out} tested out` : ''} · {locked} locked</p>
        </div>
        <div className="flex items-center gap-3">
          {gam.streak > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
              <span className="text-sm">🔥</span>
              <span className="text-sm font-bold text-amber-700 dark:text-amber-300">{gam.streak}</span>
              <span className="text-[9px] text-amber-500 dark:text-amber-400">day streak</span>
            </div>
          )}
          {gam.badge_count > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700">
              <span className="text-sm">🏅</span>
              <span className="text-sm font-bold text-purple-700 dark:text-purple-300">{gam.badge_count}</span>
            </div>
          )}
          {gam.xp > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700">
              <span className="text-sm">✨</span>
              <span className="text-sm font-bold text-indigo-700 dark:text-indigo-300">{gam.xp}</span>
              <span className="text-[9px] text-indigo-500 dark:text-indigo-400">XP</span>
            </div>
          )}
        </div>
      </div>

      {/* Classic vs Games picker (registry in HebrewModePicker) */}
      <HebrewModePicker mode={learnMode} onMode={setLearnMode} activeGameId={activeGameId} onGame={setActiveGameId} />
      {learnMode === 'game' && (
        <button onClick={() => setShowBrowseInGame(false)}
          className="mb-4 min-h-[44px] px-4 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium cursor-pointer">
          ← Back to the game
        </button>
      )}

      {/* Stats + quick action dropdowns */}
      <div className="flex flex-wrap items-center gap-2 mb-6 p-3 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <div className="flex-1 min-w-0">
          <div className="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${(mastered / Math.max(total, 1)) * 100}%` }} />
          </div>
        </div>

        {/* Mastery stats inline */}
        <div className="hidden sm:flex items-center gap-2 text-[10px] text-neutral-500 dark:text-neutral-400 shrink-0">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> {mastered}</span>
          {tested_out > 0 && (
            <span className="flex items-center gap-1" title="Diagnostic credit — demonstrated, not yet practiced">
              <span className="w-2 h-2 rounded-full bg-sky-400" /> {tested_out} tested out
            </span>
          )}
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> {in_progress}</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-neutral-300 dark:bg-neutral-600" /> {locked}</span>
        </div>

        {/* Map/List toggle */}
        <button onClick={() => setShowMasteryMap(!showMasteryMap)}
          className="px-2.5 py-1.5 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 text-[10px] font-medium cursor-pointer transition-colors shrink-0">
          {showMasteryMap ? '📋 List' : '🗺️ Map'}
        </button>

        {/* Practice dropdown */}
        <DropdownMenu label="⏱ Practice" color="amber">
          <DropdownItem onClick={startQuickSession} icon="⏱" label="5-min Quick" desc="Timed review session" />
          <DropdownItem onClick={() => setShowRoom(true)} icon="🏠" label="Room" desc="Today's session: verse + due + new" />
          <DropdownItem onClick={() => setShowQuiz(true)} icon="📝" label="Quiz" desc="Test your knowledge" />
          <DropdownItem onClick={async () => {
            // Prefer the persisted scheduler's due items; fall back to unlocked nodes.
            let dueCards = []
            try {
              const uq = await sessionQuery()
              const r = await fetch(`/api/v1/hebrew/review-queue?limit=30${uq}`, { headers: sessionHeaders() })
              const d = await r.json()
              if (d.ok && d.data?.reviews?.length) {
                // P1: the Review deck is letter/vocab flashcards. Grammar,
                // syntax, reading and verb nodes have no Hebrew stimulus —
                // reverse-mode would show their description as a fake gloss
                // (seen live: "English → Hebrew: Read maqqef-bound words…").
                // Those skills are covered by Grammar Focus, Verb Drills,
                // PassageReader; filter them here rather than misrender.
                const flattenReviews = (rs) => rs.flatMap(r =>
                  r.type === 'compressed' && Array.isArray(r.items) ? r.items : [r])
                // Queue rows carry only title/description; the curriculum
                // (already loaded) carries the node's hebrew/gloss fields.
                const byId = Object.fromEntries((curriculum?.nodes || []).map(n => [n.id, n]))
                dueCards = flattenReviews(d.data.reviews)
                  .filter(item => ['consonant', 'vowel', 'word'].includes(item.category))
                  .map((item, i) => {
                    const node = byId[item.node_id] || {}
                    // Prefer node fields; fall back to title parsing for
                    // nodes missing from the curriculum payload.
                    const hebrew = node.hebrew || (() => {
                      const title = item.title || ''
                      if (title.includes('—')) {
                        const parts = title.split('—').map(s => (s || '').trim())
                        if (parts.length > 1 && parts[1]) return parts[0]
                      }
                      const parens = [...title.matchAll(/\(([^)]+)\)/g)].map(m => m[1])
                      const hebParen = parens.length ? [...parens].reverse().find(p => /[\u0590-\u05FF]/.test(p)) : ''
                      return hebParen || title
                    })()
                    const gloss = node.gloss || item.title?.split('—')?.[1]?.trim() || item.description || ''
                    return { id: `due-${i}`, type: item.category === 'consonant' ? 'hebrew_letter' : 'vocab', modes: item.due_modes, data: {
                      node_id: item.node_id, hebrew, gloss,
                      transliteration: node.transliteration || '',
                      definition: gloss || item.description || '',
                      language: item.language || node.language || 'hebrew',
                    } }
                  })
              }
            } catch {}
            const unlocked = curriculum?.nodes?.filter(n => n.unlocked) || []
            const nodeCards = dueCards.length ? dueCards : hebrewToCards(unlocked)
            let drillCards = []
            try {
              const uq = await sessionQuery()
              const r = await fetch(`/api/v1/hebrew/verb-drill?limit=8${uq}`, { headers: sessionHeaders() })
              const d = await r.json()
              if (d.ok) drillCards = drillsToCards(d.data.drills || [])
            } catch {}
            setHebrewReviewCards(interleaveCards([nodeCards, drillCards]))
            setShowHebrewReview(true)
          }} icon="🔄" label="Review 🔀" desc="Letters, vowels & vocab due" />
        </DropdownMenu>

        {/* Reading dropdown */}
        <DropdownMenu label="📖 Reading" color="teal">
          <DropdownItem onClick={() => setShowDailyVerse(true)} icon="📆" label="Verse of Day" desc="Daily featured verse" />
          <DropdownItem onClick={() => setShowPassageReader(true)} icon="📖" label="Read Passage" desc="Full chapter reader" />
        </DropdownMenu>

        {/* Tools dropdown */}
        <DropdownMenu label="🔧 Tools" color="neutral">
          <DropdownItem onClick={() => setShowVerbDrill(true)} icon="ע" label="Verb Drills" desc="Conjugation practice" />
          <DropdownItem onClick={() => startVocabBand(100, 10, 0)} icon="📊" label="Top Vocab" desc="Top 100 words · 3-way" />
          <DropdownItem onClick={() => startVocabBand(300, 10, 100)} icon="📚" label="More Vocab" desc="Next ~200 words · 3-way" />
          <DropdownItem onClick={() => startVocabBand(700, 5, 300)} icon="📖" label="Long Tail" desc="Remaining words · 3-way" />
          <DropdownItem onClick={async () => {
            try {
              const uq = await sessionQuery()
              const r = await fetch(`/api/v1/hebrew/grammar-focus?limit=8${uq}`, { headers: sessionHeaders() })
              const d = await r.json()
              setFocusTopics(d.ok ? (d.data || { topics: [] }) : { topics: [] })
            } catch { setFocusTopics({ topics: [] }) }
            setShowGrammarFocus(true)
          }} icon="🎯" label="Grammar Focus" desc="Weakest grammar first" />
          <DropdownItem onClick={async () => {
            try { const r = await fetch('/api/v1/vocabulary?top=50&cutoff=10'); const d = await r.json(); setAudioWords((d.data?.words || []).filter(w => w.hebrew && w.gloss).map(w => ({ hebrew: w.hebrew, english: w.gloss, transliteration: w.transliteration }))) } catch {}
            setShowAudioReview(true)
          }} icon="🎧" label="Audio Review" desc="Listen & repeat" />
          <DropdownItem onClick={async () => {
            try {
              const uq = await sessionQuery()
              const amp = uq ? '&' + uq.slice(1) : ''
              const r = await fetch(`/api/v1/hebrew/top-words?limit=50&with_status=1${amp}`, { headers: sessionHeaders() })
              const d = await r.json()
              setWordTilesInitial(d.ok ? (d.data?.words || []) : [])
            } catch { setWordTilesInitial([]) }
            setWordTilesKind('words')
            setShowWordTiles(true)
          }} icon="🔠" label="Word Tiles" desc="50 words at once · Anki intervals" />
          <DropdownItem onClick={() => { setWordTilesKind('roots'); setShowWordTiles(true) }} icon="🌱" label="Root Tiles" desc="50 roots · 25 mastered words to enter" />
          <DropdownItem onClick={async () => {
            try {
              const uq = await sessionQuery()
              const r = await fetch(`/api/v1/hebrew/stats${uq}`, { headers: sessionHeaders() })
              const d = await r.json()
              setStatsData(d.ok ? d.data : null)
            } catch { setStatsData(null) }
            setShowStats(true)
          }} icon="📈" label="Stats" desc="Retention · forecast · activity" />
        </DropdownMenu>
      </div>

      {/* What-do-what guide (native disclosure: no state, persists nothing).
          First-time orientation for Map / Practice / Reading / Tools. */}
      <details className="mb-4 px-3 text-[11px] text-neutral-500 dark:text-neutral-400">
        <summary className="cursor-pointer hover:text-neutral-700 dark:hover:text-neutral-300 select-none">
          What do Map · Practice · Reading · Tools do?
        </summary>
        <ul className="mt-1.5 space-y-1 leading-relaxed list-none">
          <li><span className="font-medium text-neutral-600 dark:text-neutral-300">🗺️ Map</span> — the whole curriculum: what's mastered, learning, or locked, and your frontier. Tap any lesson to study it.</li>
          <li><span className="font-medium text-neutral-600 dark:text-neutral-300">⏱ Practice</span> — train: 5-min Quick sessions, Quizzes that test you, Reviews due today, dictation, and the Room (verse + due + new).</li>
          <li><span className="font-medium text-neutral-600 dark:text-neutral-300">📖 Reading</span> — read real text: Verse of the Day and the full-chapter Passage Reader with tap-a-word help.</li>
          <li><span className="font-medium text-neutral-600 dark:text-neutral-300">🔧 Tools</span> — drills and lists: verb conjugation drills, Top-100 vocab bands, listen-and-repeat audio, word/root tiles, and your stats.</li>
        </ul>
      </details>

      {/* Daily pacing (Anki-style deck options) */}
      <div className="flex flex-wrap items-center gap-2 mb-4 px-3 py-2 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <span className="text-[11px] text-neutral-600 dark:text-neutral-400">
          📊 {queueStats ? (
            <>{queueStats.due_count} due · {queueStats.new_cards} new · ✅ {queueStats.reviews_done_today ?? 0} done{queueStats.learning_count > 0 ? ` · 🔴 ${queueStats.learning_count} learning` : ''}{queueStats.reviews_capped ? ` · capped (${queueStats.reviews_remaining} waiting)` : ''}{queueStats.leech_due > 0 ? ` · 🪲 ${queueStats.leech_due} leech${queueStats.leech_due === 1 ? '' : 'es'}` : ''}</>
          ) : 'Loading queue…'}
        </span>
        <span className="flex-1" />
        {!prefsEditing ? (
          <button onClick={() => { setPrefsDraft(prefs); setPrefsEditing(true) }}
            className="text-[10px] text-neutral-500 dark:text-neutral-400 hover:text-indigo-500 cursor-pointer"
            title="Deck options: daily new cards, max reviews, and desired retention">
            ⚙️ {prefs.new_cards_per_day} new · {prefs.max_reviews_per_day === 0 ? '∞' : prefs.max_reviews_per_day} rev/day · {Math.round((prefs.desired_retention ?? 0.9) * 100)}% retention
          </button>
        ) : (
          <span className="flex items-center gap-1.5 text-[10px] text-neutral-500 dark:text-neutral-400">
            <label>New <input type="number" min="0" max="100" value={prefsDraft.new_cards_per_day}
              onChange={e => setPrefsDraft(d => ({ ...d, new_cards_per_day: e.target.value }))}
              className="w-12 px-1 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none" />/day</label>
            <label>Max <input type="number" min="0" max="1000" value={prefsDraft.max_reviews_per_day}
              onChange={e => setPrefsDraft(d => ({ ...d, max_reviews_per_day: e.target.value }))}
              className="w-14 px-1 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none" /> rev/day</label>
            <label title="Desired retention (Anki deck option, 70–99%). Higher = shorter intervals, more reviews.">Ret <input type="number" min="70" max="99" step="1" value={Math.round((prefsDraft.desired_retention ?? 0.9) * 100)}
              onChange={e => setPrefsDraft(d => ({ ...d, desired_retention: (parseInt(e.target.value) || 90) / 100 }))}
              className="w-12 px-1 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none" />%</label>
            <label title="Your goal — shapes what the Room serves first.">Goal <select value={prefsDraft.goal || ''}
              onChange={e => setPrefsDraft(d => ({ ...d, goal: e.target.value }))}
              className="px-1 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none">
              <option value="">—</option>
              <option value="read">📖 Read</option>
              <option value="vocab">📚 Vocab</option>
              <option value="parse">ע Parse</option>
              <option value="fluency">⚡ Fluency</option>
            </select></label>
            <button onClick={savePrefs} className="px-2 py-0.5 rounded bg-indigo-600 text-white font-medium cursor-pointer">Save</button>
            <button onClick={() => setPrefsEditing(false)} className="hover:text-neutral-700 cursor-pointer">✕</button>
          </span>
        )}
      </div>

      {/* Learner profile (P1): one glance at the whole learner */}
      {profile && profile.skills?.length > 0 && (
        <div className="px-4 py-3 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] font-semibold text-neutral-600 dark:text-neutral-300">👤 Your Hebrew</span>
            <span className="text-[10px] text-neutral-400">L{profile.frontier_level} frontier</span>
            {profile.production_ratio_30d?.rate != null && (
              <span className="text-[10px] text-neutral-400" title="Share of graded answers that were production (typed/named), last 30 days. Target ≥40%.">
                · ⚙️ {Math.round(profile.production_ratio_30d.rate * 100)}% production
              </span>
            )}
            <span className="flex-1" />
            {profile.goal ? (
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300">
                🎯 {{ read: 'Read the Bible', vocab: 'Master vocab', parse: 'Parse fluently', fluency: 'Build fluency' }[profile.goal] || profile.goal}
              </span>
            ) : (
              <button onClick={() => setPrefsEditing(true)} className="text-[10px] text-indigo-500 hover:underline cursor-pointer">set a goal →</button>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1">
            {profile.skills.slice(0, 6).map(s => (
              <div key={s.category} className="flex items-center gap-2 text-[11px]" title={`${s.practiced} practiced · ${s.mastered} mastered · ${s.due} due`}>
                <span className="w-16 truncate text-neutral-500 dark:text-neutral-400 capitalize">{s.category}</span>
                <div className="flex-1 h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${Math.round((s.avg_mastery || 0) * 100)}%` }} />
                </div>
                <span className="w-8 text-right font-mono text-neutral-500 dark:text-neutral-400">{Math.round((s.avg_mastery || 0) * 100)}%</span>
              </div>
            ))}
          </div>
          {Array.isArray(profile.milestones) && profile.milestones.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {profile.milestones.map(m => (
                <span key={m.id} title={`${m.desc} — ${m.count}/${m.total}`}
                  className={`text-[10px] px-2 py-0.5 rounded-full border cursor-default ${m.done
                    ? 'bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700 text-green-700 dark:text-green-300'
                    : 'bg-neutral-100 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-500 dark:text-neutral-400'}`}>
                  {m.done ? '✓ ' : ''}{m.title} {m.done ? '' : `${m.count}/${m.total}`}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Badges row */}
      {gam.badge_catalog && gam.badge_catalog.filter(b => b.earned).length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4 px-4 py-3 rounded-xl bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
          <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mr-1">Badges</span>
          {gam.badge_catalog.filter(b => b.earned).map(b => (
            <span key={b.id} className="flex items-center gap-1 px-2 py-1 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 text-xs" title={b.desc}>
              <span>{b.icon}</span>
              <span className="text-[10px] font-medium text-purple-700 dark:text-purple-300">{b.name}</span>
            </span>
          ))}
          {gam.next_badges && gam.next_badges.length > 0 && (
            <span className="text-[9px] text-neutral-400 ml-2">
              Next: {gam.next_badges.map(b => b.name).join(', ')}
            </span>
          )}
        </div>
      )}

      {/* Placement CTA for brand-new learners — then "Continue Learning" */}
      {profile && (profile?.frontier_level ?? 1) <= 1 && (profile?.skills || []).reduce((s, k) => s + (k.practiced || 0), 0) < 10 && (
        <div className="mb-4 p-3 rounded-xl bg-gradient-to-r from-sky-50 to-indigo-50 dark:from-sky-900/20 dark:to-indigo-900/20 border border-sky-200 dark:border-sky-800 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-sky-100 dark:bg-sky-900/40 flex items-center justify-center text-sm shrink-0">📝</div>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-wider text-sky-600 dark:text-sky-400 mb-0.5">New here? Find your level</div>
            <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">5-minute placement quiz — skip what you already know</div>
          </div>
          <button onClick={() => onOpenLesson?.('diagnostic')}
            className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
            Start →
          </button>
        </div>
      )}
      {/* Suggested next lesson — "Continue Learning" */}
      {(() => {
        // Find best next lesson: unlocked, not mastered, lowest level first, then lowest mastery
        const candidates = (nodes || []).filter(n => n.unlocked && n.mastery < 0.8)
          .sort((a, b) => a.level - b.level || a.mastery - b.mastery)
        const next = candidates[0]
        if (!next) return null
        const cs = CATEGORY_STYLES[next.category] || {}
        return (
          <div className="mb-4 p-3 rounded-xl bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-900/20 dark:to-blue-900/20 border border-indigo-200 dark:border-indigo-800 flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-sm shrink-0">
              {cs.icon || '📖'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-500 dark:text-indigo-400 mb-0.5">Continue Learning</div>
              <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">{next.title}</div>
              <div className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-0.5">
                Level {next.level} · {cs.label || next.category} · {Math.round((1 - next.mastery) * 100)}% to go
              </div>
            </div>
            <button onClick={() => onOpenLesson?.(next.id)}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
              Continue →
            </button>
          </div>
        )
      })()}

      {/* Category filter — horizontal scroll on mobile */}
      <div className="flex gap-1.5 mb-6 overflow-x-auto pb-1 scrollbar-thin -mx-2 px-2 snap-x snap-mandatory md:mx-0 md:px-0 md:flex-wrap md:overflow-visible">
        {[{id:'all',count:total,label:'All'}].concat(
          Object.entries(CATEGORY_STYLES).map(([cat, cs]) => ({
            id: cat, count: nodes.filter(n => n.category === cat).length, ...cs
          })).filter(c => c.count > 0)
        ).concat([{ id: 'tracks', count: trackInfo.complete, label: 'Tracks', icon: '🧭',
          bg: 'bg-sky-100 dark:bg-sky-900/30', text: 'text-sky-800 dark:text-sky-200' }]).map(c => (
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

      {/* Mastery Map grid (toggle) */}
      {showMasteryMap && (
        <div className="mb-6 p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3">
            Mastery Map · {mastered}/{total} nodes mastered ({Math.round(mastered / Math.max(total, 1) * 100)}%)
          </h3>
          <div className="grid grid-cols-8 sm:grid-cols-10 md:grid-cols-12 gap-1.5">
            {nodes.map(node => {
              const locked = !node.unlocked
              const masteryPct = node.mastery || 0
              let color = ''
              if (locked) color = 'bg-neutral-200 dark:bg-neutral-700'
              else if (masteryPct >= 1.0) color = 'bg-yellow-400 dark:bg-yellow-500'
              else if (masteryPct >= 0.8) color = 'bg-green-500'
              else if (masteryPct >= 0.6) color = 'bg-blue-400'
              else if (masteryPct >= 0.3) color = 'bg-amber-400'
              else if (masteryPct > 0) color = 'bg-red-300 dark:bg-red-700'
              else color = 'bg-neutral-100 dark:bg-neutral-600'
              
              return (
                <button key={node.id}
                  onClick={() => { if (!locked) onOpenLesson?.(node.id) }}
                  disabled={locked}
                  className={`w-full aspect-square rounded-md ${color} transition-all hover:ring-2 hover:ring-indigo-400 cursor-pointer disabled:cursor-not-allowed relative group`}
                  title={`${node.title} (${Math.round(masteryPct * 100)}%)`}>
                  {/* Tooltip on hover */}
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 rounded bg-neutral-800 text-white text-[9px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    {node.title} — {Math.round(masteryPct * 100)}%
                  </span>
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-3 mt-3 text-[9px] text-neutral-400">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-400" /> Mastered</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500" /> 80%+</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-blue-400" /> Learning</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-400" /> Started</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-300" /> Needs work</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-neutral-200 dark:bg-neutral-700" /> Locked</span>
          </div>
        </div>
      )}

      {/* Grammar tracks grid (Scale Track C): 3 tracks × 5 tiers. Click a
          cell to open its first unmastered lesson. Empty cells are the
          content backlog — visible, not hidden. */}
      {filter === 'tracks' && (
        <div className="mb-6 p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1">
            Grammar Tracks · {trackInfo.complete} tiers complete (+{Math.round(trackInfo.bonus * 100)}% Ohr)
          </h3>
          <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mb-3">Each complete tier pays +5% Ohr/sec (cap +50%). Tiers follow lesson level (L3→1 … L7→5).</p>
          <div className="space-y-2">
            {TRACK_META.map(t => (
              <div key={t.id} className="flex items-center gap-2">
                <div className="w-24 shrink-0 text-[11px] font-medium text-neutral-600 dark:text-neutral-300">
                  <span className="mr-1">{t.icon}</span>{t.label}
                </div>
                <div className="flex gap-1.5 flex-1">
                  {[1, 2, 3, 4, 5].map(tier => {
                    const cell = trackInfo.grid[t.id]?.[tier]
                    const done = cell && cell.mastered >= cell.total
                    const color = !cell ? 'bg-neutral-100 dark:bg-neutral-800 border-dashed'
                      : done ? 'bg-green-500 border-green-500'
                      : cell.mastered > 0 ? 'bg-amber-400 border-amber-400'
                      : 'bg-neutral-200 dark:bg-neutral-700 border-transparent'
                    const nextId = cell?.ids.map(id => nodes.find(n => n.id === id)).find(n => n && (n.mastery || 0) < 0.8)?.id
                      || cell?.ids[0]
                    return (
                      <button key={tier} disabled={!nextId} onClick={() => nextId && onOpenLesson?.(nextId)}
                        title={!cell ? `Tier ${tier}: no lessons yet — content backlog`
                          : `${t.label} tier ${tier}: ${cell.mastered}/${cell.total} mastered${done ? ' (+5% Ohr)' : ''}`}
                        className={`flex-1 h-9 rounded-lg border text-[10px] font-medium transition-all cursor-pointer disabled:cursor-default hover:ring-2 hover:ring-indigo-400 disabled:hover:ring-0 ${color} ${done || !cell ? 'text-white dark:text-white' : 'text-neutral-600 dark:text-neutral-300'}`}>
                        T{tier}{cell ? ` ${cell.mastered}/${cell.total}` : ' ···'}
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lessons by level */}
      {!showMasteryMap && filtered.length > 0 && (
        <p className="text-[11px] text-neutral-400 dark:text-neutral-500 mb-3" role="status">
          {filtered.length} lesson{filtered.length === 1 ? '' : 's'}{filter !== 'all' ? ` in ${(CATEGORY_STYLES[filter]?.label || filter)}` : ''} · grouped by level
        </p>
      )}
      {!showMasteryMap && (
        <div className="space-y-6">
          {Object.entries(byLevel).map(([level, levelNodes]) => (
            <div key={level}>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3">Level {level}</h3>
              <div className="space-y-1.5">
                {levelNodes.map(node => (
                  <LessonRow key={node.id} node={node} onOpenLesson={onOpenLesson} onOpenPassage={onOpenPassage} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {filtered.length === 0 && filter !== 'tracks' && (
        <div className="p-8 text-center" role="status">
          <div className="text-3xl mb-2" aria-hidden="true">🔍</div>
          <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">No lessons in this category</p>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 mb-4">Try another filter, or start with Letters (L1).</p>
          <button onClick={() => setFilter('all')}
            className="px-4 py-2 min-h-[44px] rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors">
            Show all lessons
          </button>
        </div>
      )}
    </div>
  )
}
