import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import {
  LETTERS, LETTER_NAMES, LETTER_SYMBOLS, GEMATRIA, baseCost, generatorCost, bulkCost, maxBuyable, statePerSecond, tapValue,
  rootsEarned, shouldPrestige, offlineEarnings, totalOwned,
  QUESTS, questComplete, claimQuest, checkStreakMilestone, nextGoals,
  FRENZY_COST, FRENZY_MULT, buffMultiplier, frenzyRemainingSec, buyFrenzy, buyTimeWarp, warpCost,
  LETTER_UPGRADE_TIERS, availableLetterUpgrades, buyLetterUpgrade, letterMultiplier,
  KAVOD_UPGRADES, buyPerm, hasPerm, synergyMultiplier, workshopSynergy, letterRate,
  loadIdleState, saveIdleState, applyPrestige, applyCorrectAnswer, applyWrongAnswer, applyTap,
  applyFeedback, recordAttempt, difficultyScalars, recentAccuracy,
  sparksEarned, availableSparks, sparkBonus, sparkProgress,
  HEAVENLY_UPGRADES, heavenlyOwned, heavenlyUnlocked, buyHeavenly, heavenlyTierOwned, HEAVENLY_TIERS,
  GOLDEN_PROMPTS, spawnGoldenPrompt, answerGoldenQuiz, goldenRemainingSec, tapBuffMultiplier, galeMultiplier, shofarMultiplier, activeBuffCount, expireGoldenPrompt, goldenWindowSec,
  PROPHET_BLESSINGS, applyProphetChoice, startExile, rollExileLetters, exileAllows, dayKey,
  startShemittah, shemittahTapMult, shareCard, checkShemittah, SHEMITTAH_HOURS,
  figReady, figRemainingSec, plantFig, harvestFig, FIG_MAX_LEVEL, FIG_RIPEN_HOURS,
  plantVineyard, harvestVine, vineReady, vineRemainingSec, vineyardMultiplier,
  VINE_COUNT, VINE_MAX_LEVEL, VINE_RIPEN_HOURS, vowReleased, VOW_MAX_HOURS,
  ACHIEVEMENTS, achievementsEarned, shemenMultiplier, dailyReady, claimDaily, recordDailyCorrect, DAILY_GOAL,
  defaultIdleState,
} from '../lib/idle-game'
import { pullIdleState, pushIdleState, beaconIdleState, serverIsNewer } from '../lib/idle-sync'
import { logEvent, exportLog } from '../lib/analytics'
import { grammarTrackBonus, gardenPlots, gardenReady, watchEffects, isFeastDay, activeFeasts, nextFeast, scribeUnlocked, scribeCost, hireScribe, autoBuyTick, scribeCount, fmtBig } from '../lib/idle-game'
import FeastModal from './FeastModal'
import GardenPanel from './GardenPanel'
import WatchmenPanel from './WatchmenPanel'
import ShukPanel from './ShukPanel'
import { fetchAudioUrl, playUrl, playHebrewAudio } from '../lib/audio-pool'
import GolemCanvas from './GolemCanvas'

/**
 * HebrewIdleBar — trial idle-game HUD for Aleph to Revelation.
 *
 * The gameplay loop, all visible at a glance:
 *   answer correctly → tap Ohr (+streak, crits) → buy letters (x1/x10/Max)
 *   → chase quests + next goals → forge roots → repeat, faster.
 *
 * Mobile-first: stacks on small screens, 44px+ touch targets, 6-col
 * letter grid on phones → 11-col on sm+.
 *
 * Difficulty: explicit feedback buttons (too easy / just right / too hard)
 * plus implicit auto-adaptation. Any graded answer anywhere in the app can
 * call `reportIdleAnswer(correct, responseMs)` — this bar picks it up via
 * window event and adapts. Economy pacing only; mastery never touched.
 *
 * localStorage only ('hebrew-idle-v1'). Reads curriculum mastery for
 * generator rates, never writes SRS state. Ticker is 1s.
 */

/** Call from any quiz/review grader: feeds taps + adaptive difficulty + analytics.
 *  meta: {source: 'quiz'|'audio'|'review', qtype, nodeId} — powers balance queries. */
export function reportIdleAnswer(correct, responseMs, meta = {}) {
  try {
    logEvent('answer', { correct: !!correct, ms: responseMs || 0, ...meta })
  } catch {}
  try {
    window.dispatchEvent(new CustomEvent('hebrew-idle-answer', {
      detail: { correct: !!correct, ms: responseMs || 0 },
    }))
  } catch {}
}

const BULK_MODES = ['1', '10', 'max']

const UI_KEY = 'hebrew-idle-ui-v1'
const IDLE_TABS = ['letters', 'garden', 'watch', 'shuk', 'boosts', 'quests', 'upgrades']
const TAB_META = {
  letters: { icon: 'א', label: 'Letters' },
  garden: { icon: '🌱', label: 'Garden' },
  watch: { icon: '👁️', label: 'Watch' },
  shuk: { icon: '🧺', label: 'Shuk' },
  boosts: { icon: '🌬️', label: 'Boosts' },
  quests: { icon: '📜', label: 'Quests' },
  upgrades: { icon: '⬆️', label: 'Upgrades' },
}
// Progressive unlocks — breadth gates, never time gates. A new system opens
// when the player has mastered the previous one; locked tabs stay visible
// but greyed with the unlock condition (aspiration, not surprise).
const GARDEN_UNLOCK_OWNED = 10 // matches the Watchmen gate: a bench of letters first
function gardenUnlockedFor(s) { return totalOwned(s) >= GARDEN_UNLOCK_OWNED || (s.roots || 0) > 0 }
function shukUnlockedFor(s) { return (s.roots || 0) > 0 } // the market is the second-act reveal
// Locked-tab teaser — shows WHAT the system is and HOW CLOSE the unlock is,
// with one tap back to the core loop. Tapping a locked tab is never a dead end.
function LockedTeaser({ icon, name, blurb, progress, onGo }) {
  return (
    <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
      <div className="p-4 rounded-xl bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700 text-center">
        <div className="text-3xl" aria-hidden="true">{icon}</div>
        <div className="mt-1 text-sm font-bold text-neutral-700 dark:text-neutral-200">🔒 {name} — not yet planted</div>
        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">{blurb}</p>
        <div className="mt-2 text-xs font-semibold text-amber-600 dark:text-amber-400 tabular-nums">{progress}</div>
        <button onClick={onGo}
          className="mt-3 min-h-[48px] px-5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-bold cursor-pointer active:scale-95">
          א Back to Letters
        </button>
      </div>
    </div>
  )
}
function loadUiPrefs() {
  try {
    const raw = localStorage.getItem(UI_KEY)
    if (raw) return { showGolems: true, bulk: '1', activeTab: 'letters', ...JSON.parse(raw) }
  } catch {}
  return { showGolems: true, bulk: '1', activeTab: 'letters' }
}

export default function HebrewIdleBar({ curriculum, onEarn, dueCount = 0, onOpenReview = null, onBrowseLessons = null }) {
  const [state, setState] = useState(loadIdleState)
  // UI prefs persist separately from game state — the active tab stays as you left it.
  const [uiPrefs] = useState(loadUiPrefs)
  const [activeTab, setActiveTab] = useState(() => IDLE_TABS.includes(uiPrefs.activeTab) ? uiPrefs.activeTab : 'letters')
  const [bulk, setBulk] = useState(() => BULK_MODES.includes(uiPrefs.bulk) ? uiPrefs.bulk : '1')
  const [offlinePopup, setOfflinePopup] = useState(null)
  const [prestigeFlash, setPrestigeFlash] = useState(null)
  const [feedbackFlash, setFeedbackFlash] = useState(null)
  const [milestoneFlash, setMilestoneFlash] = useState(null)
  const [questFlash, setQuestFlash] = useState(null)
  const [boostFlash, setBoostFlash] = useState(null)
  const [goldenFlash, setGoldenFlash] = useState(null)
  const [prophetPick, setProphetPick] = useState(null)
  const [prophetSnoozed, setProphetSnoozed] = useState(false) // "decide later" — the choice never expires
  const [showFeast, setShowFeast] = useState(null) // {feast, daysUntil} — moed info modal
  const [quizAudio, setQuizAudio] = useState(null) // {url} | {failed:true} — listening-question audio
  const [prestigeTick, setPrestigeTick] = useState(0)
  const [showGolems, setShowGolems] = useState(() => uiPrefs.showGolems)
  const [lastGain, setLastGain] = useState(null) // {value, crit, kavod, n} tap floater (stacked)
  const [gains, setGains] = useState([]) // stacked tap floaters — rapid answers each pop, none dropped
  const [buyHint, setBuyHint] = useState(null) // {i, need} — unaffordable click feedback
  const [answerPulse, setAnswerPulse] = useState(null) // {n, correct} — golem reaction
  const [tapFloats, setTapFloats] = useState([]) // manual golem taps — {id, x, y, value, crit}
  const lastBuzzRef = useRef(0) // haptic throttle — max ~1 buzz per 80ms in tap bursts
  // Persist UI prefs — the tab stays exactly as you left it.
  useEffect(() => {
    try {
      localStorage.setItem(UI_KEY, JSON.stringify({ showGolems, bulk, activeTab }))
    } catch {}
  }, [activeTab, showGolems, bulk])

  // Top-500 words/roots for the translation tier. Perf (Track D2): fetched
  // lazily — word quizzes need 100+ readable words (mid-game), so new
  // players never download 1000 rows on mount. Retry-safe via the flag.
  const topWordsRef = useRef(null)
  const topRootsRef = useRef(null)
  const topListsLoading = useRef(false)
  const ensureTopLists = () => {
    if (topWordsRef.current || topListsLoading.current) return
    topListsLoading.current = true
    fetch('/api/v1/hebrew/top-words?limit=500')
      .then(r => r.json())
      .then(d => { if (d.ok) topWordsRef.current = d.data.words || [] })
      .catch(() => { topListsLoading.current = false })
    fetch('/api/v1/hebrew/top-roots?limit=500')
      .then(r => r.json())
      .then(d => { if (d.ok) topRootsRef.current = d.data.roots || [] })
      .catch(() => { topListsLoading.current = false })
  }

  // Grammar studied (for the translation gate): mastered grammar/syntax/verb nodes.
  const gramInfo = useMemo(() => {
    const m = {}, c = {}
    try {
      for (const n of curriculum?.nodes || []) {
        if (n.category === 'grammar' || n.category === 'syntax' || n.category === 'verb') {
          m[n.id] = n.mastery || 0
          c[n.id] = n.category
        }
      }
    } catch {}
    return { m, c }
  }, [curriculum])

  // Map curriculum mastery onto letter indices. Consonant nodes in level
  // order map 1:1 onto the 22-letter roster; unknown letters = 0 mastery.
  const mastery = useMemo(() => {
    const m = {}
    try {
      const consonants = (curriculum?.nodes || [])
        .filter(n => n.category === 'consonant')
        .sort((a, b) => (a.level || 0) - (b.level || 0))
      consonants.slice(0, 22).forEach((n, i) => { m[i] = n.mastery || 0 })
    } catch {}
    return m
  }, [curriculum])

  // Authoritative state mirror. React StrictMode double-invokes setState
  // updaters in dev, so updaters must be PURE. Anything with a side effect
  // (random crit roll, localStorage save, parent callback) is computed here
  // from the mirror and applied once, outside the updater.
  // Listening questions: fetch the letter audio when the popup opens. If it
  // fails, the popup falls back to showing the transliterated name.
  useEffect(() => {
    const q = state.golden?.quiz
    if (!q || q.qtype !== 'audio') { setQuizAudio(null); return }
    let cancelled = false
    setQuizAudio(null)
    fetchAudioUrl(LETTERS[q.letter]).then(url => {
      if (cancelled) return
      setQuizAudio(url ? { url } : { failed: true })
      if (url) playUrl(url)
    })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.golden])
  // updaters in dev, so updaters must be PURE. Anything with a side effect
  // (random crit roll, localStorage save, parent callback) is computed here
  // from the mirror and applied once, outside the updater.
  const stateRef = useRef(state)
  const commit = useCallback((next) => {
    stateRef.current = next
    setState(next)
    return next
  }, [])
  useEffect(() => { stateRef.current = state }, [state])

  // Perf (Track D1): graded answers arrive in bursts — trail the localStorage
  // write by 2s and flush on hide/unmount. Purchases/prestige still save
  // immediately (money movements must persist).
  const saveTimer = useRef(null)
  const saveSoon = useCallback((s) => {
    stateRef.current = s
    if (saveTimer.current) return
    saveTimer.current = setTimeout(() => {
      saveTimer.current = null
      try { saveIdleState(stateRef.current) } catch {}
    }, 2000)
  }, [])
  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current) }, [])
  useEffect(() => {
    const flush = () => {
      if (saveTimer.current) { clearTimeout(saveTimer.current); saveTimer.current = null }
      try { saveIdleState(stateRef.current) } catch {}
      try { beaconIdleState(stateRef.current) } catch {}
    }
    window.addEventListener('pagehide', flush)
    return () => window.removeEventListener('pagehide', flush)
  }, [])

  // Cross-device sync: pull on mount (server wins only when strictly newer),
  // push every 30s when logged in. Logged-out play stays local-only.
  const [sync, setSync] = useState('off')
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      const remote = await pullIdleState()
      if (cancelled) return
      if (!currentSessionToken()) { setSync('off'); return }
      if (remote && serverIsNewer(remote.updated_at, (loadIdleState().lastSeen || 0))) {
        const merged = { ...defaultIdleState(), ...remote.state }
        commit(merged)
        try { saveIdleState(merged) } catch {}
      }
      setSync('ok')
    })()
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  useEffect(() => {
    const t = setInterval(async () => {
      if (!currentSessionToken()) { setSync('off'); return }
      const res = await pushIdleState(stateRef.current)
      setSync(res ? 'ok' : 'err')
    }, 30000)
    return () => clearInterval(t)
  }, [])

  const diff = state.difficulty || { bias: 0, recent: [] }
  const scalars = difficultyScalars(diff)
  const acc = recentAccuracy(diff)
  // Grammar tracks income: +5% per complete track-tier (cap +50%), derived
  // from curriculum mastery — recomputed only when curriculum changes.
  // Shavuot doubles it (Torah given); the day key refreshes across midnight.
  const todayKey = dayKey(Date.now())
  const gramMult = useMemo(() => (1 + grammarTrackBonus(curriculum?.nodes || []).bonus) * (isFeastDay('shavuot') ? 2 : 1), [curriculum, todayKey])
  // Practice entry: the next unmastered lesson (same pick as the dashboard).
  // Lives in the Letters tab — answers are the core loop, not a card below the game.
  const nextLesson = useMemo(() => (curriculum?.nodes || [])
    .filter(n => n.unlocked && n.mastery < 0.8)
    .sort((a, b) => a.level - b.level || a.mastery - b.mastery)[0] || null, [curriculum])
  const gramPct = Math.round((gramMult - 1) * 100)
  const perSec = statePerSecond(state, mastery, gramMult)
  const workshopSyn = workshopSynergy(state.owned, mastery)
  const synPct = Math.round((workshopSyn - 1) * 100)
  const sparks = availableSparks(state)
  const sparksTotal = sparksEarned(state.lifetimeOhr || 0)
  const sparkProg = sparkProgress(state.lifetimeOhr || 0)
  const goals = nextGoals(state, diff)
  const unclaimedQuests = QUESTS.filter(q => !state.quests?.[q.id] && questComplete(state, q)).length
  // Tab badges (cheap, derived): quests to claim, upgrades affordable, garden ripe.
  const upgradeBadge = (() => {
    const afford = LETTERS.map((_, i) => availableLetterUpgrades(state, i).filter(u => u.cost <= state.ohr).length).reduce((a, b) => a + b, 0)
    const permAfford = KAVOD_UPGRADES.filter(u => !hasPerm(state, u.id) && (state.kavod || 0) >= u.cost).length
    const avail = LETTERS.map((_, i) => availableLetterUpgrades(state, i).length).reduce((a, b) => a + b, 0)
    return { n: afford + permAfford, avail }
  })()
  const gardenRipe = gardenPlots(state).filter((p, i) => gardenReady(state, i)).length
  // Progressive unlocks (breadth gates): garden opens on a bench of letters,
  // shuk opens at the first forged root. Locked tabs stay visible as teasers.
  const gardenOpen = gardenUnlockedFor(state)
  const shukOpen = shukUnlockedFor(state)

  // 1s ticker — accrues Ohr (× frenzy buff), persists throttled.
  useEffect(() => {
    let n = 0
    const t = setInterval(() => {
      // Perf (Track D1): background tabs do nothing — golden windows fizzle
      // via expireGoldenPrompt on return, offline earnings settle on mount.
      if (typeof document !== 'undefined' && document.hidden) return
      const s = stateRef.current
      const rate = statePerSecond(s, mastery, gramMult)
      const gain = rate * buffMultiplier(s)
      const next = {
        ...s,
        ohr: s.ohr + gain,
        lifetimeOhr: (s.lifetimeOhr || 0) + gain,
      }
      // Scribes: mastered letters drip one unit per tick when affordable.
      // Runs before the skip check — a buy is movement worth rendering.
      const bought = autoBuyTick(next, next.difficulty, watchEffects(next).cost)
      // Word quizzes unlock mid-game (100+ readable words) — start the
      // 1000-row download only once the workshop is broad enough to use it.
      if (totalOwned(s) >= 5 || (s.roots || 0) > 0) ensureTopLists()
      spawnGoldenPrompt(next, Date.now(), Math.random, rate, { mastery, bias: s.difficulty?.bias || 0, topWords: topWordsRef.current || [], topRoots: topRootsRef.current || [], gramMastery: gramInfo.m, gramCategories: gramInfo.c }) // only when due + production exists
      const hadGolden = !!s.golden
      expireGoldenPrompt(next) // a missed window fizzles so the next one can spawn
      if (hadGolden && !next.golden) {
        // Watchers saw the banner vanish with no explanation — say it faded, no harm.
        setGoldenFlash({ name: '', desc: '', fizzled: true })
        setTimeout(() => setGoldenFlash(null), 4000)
        try { logEvent('golden_expired', {}) } catch {}
      }
      // Shemittah completes on its hour; an uncompletable vow releases uncounted (24h cap).
      if (checkShemittah(next, Date.now())) {
        commit(next); saveIdleState(next)
        try { logEvent('vow_complete', { kind: 'shemittah' }) } catch {}
        setBoostFlash({ text: '🌾 Shemittah complete — the land woke up. Covenant kept.' })
        setTimeout(() => setBoostFlash(null), 4500)
      } else if (vowReleased(next, Date.now())) {
        commit(next); saveIdleState(next)
        setBoostFlash({ text: '🕊️ Your vow released unfulfilled — no harm done. Vow again whenever you like.' })
        setTimeout(() => setBoostFlash(null), 4500)
      }
      // Perf: skip the render when nothing moved — zero production, no
      // golden change, no scribe buys. New players idle at ~0 renders/s.
      const goldenChanged = (hadGolden !== !!next.golden) || !!next.golden
      if (gain === 0 && !goldenChanged && bought === 0) return
      if (bought > 0) saveSoon(next)
      else if (++n % 5 === 0) saveIdleState(next)
      commit(next)
    }, 1000)
    return () => { clearInterval(t); saveIdleState(stateRef.current) }
  }, [mastery, commit, gramMult])

  // Adaptive loop: graded answers from anywhere in the app.
  // Correct answers tap Ohr (streak + crit) — studying IS the clicker.
  useEffect(() => {
    const handler = (e) => {
      const { correct, ms } = e.detail || {}
      const s = stateRef.current
      const next = { ...s, difficulty: recordAttempt(s.difficulty || { bias: 0, recent: [] }, correct, ms) }
      const rate = statePerSecond(next, mastery, gramMult)
      let gainInfo = null
      let milestoneInfo = null
      if (correct) {
        const r = applyCorrectAnswer(next, rate)
        gainInfo = { value: r.gained, crit: r.crit, kavod: r.kavod, n: next.taps }
        milestoneInfo = checkStreakMilestone(next)
        recordDailyCorrect(next)
        if (r.crit && onEarn) onEarn(r.gained)
      } else {
        const wres = applyWrongAnswer(next)
        if (wres?.graced) {
          setBoostFlash({ text: `🛡️ Streak grace — a wrong answer halved your streak to ${next.streak} instead of resetting it. Once per day.` })
          setTimeout(() => setBoostFlash(null), 4500)
        }
      }
      // Golden Prompts are answered in their own popup quiz now, not here:
      // study answers tap Ohr, tune difficulty, and keep streaks — they never
      // claim or fizzle prompts.
      saveSoon(next)
      commit(next)
      if (gainInfo) {
        setLastGain(gainInfo)
        const id = Date.now() + Math.random()
        setGains(g => [...g.slice(-4), { ...gainInfo, id }])
        setTimeout(() => setGains(g => g.filter(x => x.id !== id)), 1500)
      }
      setAnswerPulse({ n: Date.now(), correct: !!correct })
      if (milestoneInfo) {
        try { logEvent('milestone', milestoneInfo) } catch {}
        setMilestoneFlash(milestoneInfo)
        setTimeout(() => setMilestoneFlash(null), 4000)
      }
    }
    window.addEventListener('hebrew-idle-answer', handler)
    return () => window.removeEventListener('hebrew-idle-answer', handler)
  }, [mastery, onEarn, saveSoon, gramMult])

  // Manual golem tap: small Ohr (no Kavod/streak) + floater exactly at the tap point.
  // Feel: light haptic per tap (throttled in bursts), a double-buzz + big
  // floater every 100th tap. Haptics default on, toggleable under the ⚙️ gear.
  const doCanvasTap = useCallback((x, y) => {
    const s = stateRef.current
    const next = { ...s }
    const rate = statePerSecond(next, mastery, gramMult)
    const r = applyTap(next, rate)
    saveSoon(next)
    commit(next)
    const id = Date.now() + Math.random()
    const taps = next.taps || 0
    const milestone = taps > 0 && taps % 100 === 0
    setTapFloats(f => [...f.slice(-9), { id, x, y, value: r.gained, crit: r.crit || milestone }])
    setTimeout(() => setTapFloats(f => f.filter(t => t.id !== id)), 1100)
    setAnswerPulse({ n: Date.now(), correct: true })
    try {
      if (s.haptics !== false && typeof navigator !== 'undefined' && navigator.vibrate) {
        const now = Date.now()
        if (milestone) { navigator.vibrate([30, 50, 30]); lastBuzzRef.current = now }
        else if (now - lastBuzzRef.current > 80) { navigator.vibrate(10); lastBuzzRef.current = now }
      }
    } catch {}
  }, [mastery, gramMult, saveSoon, commit])

  // Mount: plant the first fig AND settle offline earnings in ONE commit.
  // (Two separate commits here would let the later value-update clobber the
  // offline pendingOffline queued by an earlier functional update.)
  useEffect(() => {
    try {
      const s = loadIdleState()
      const next = { ...s }
      if (!next.figs?.readyAt) {
        next.figs = { level: next.figs?.level || 0, readyAt: 0 }
        plantFig(next)
      }
      plantVineyard(next)
      vowReleased(next) // an offline-expired vow releases on return, uncounted
      if (s.pendingOffline >= 1) {
        setOfflinePopup({ earned: Math.floor(s.pendingOffline), claim: true })
        commit(next); saveIdleState(next)
        return
      }
      const elapsed = (Date.now() - (s.lastSeen || Date.now())) / 1000
      if (elapsed > 60) {
        const atDisconnect = statePerSecond(next, mastery, gramMult)
        const earned = offlineEarnings(atDisconnect, elapsed, next.tracks, next.roots, next.perm) * watchEffects(next).offline
        if (earned >= 1) {
          const capHrs = (next.roots || 0) >= 10 ? 24 : 12
          const hrs = (Math.min(elapsed, capHrs * 3600) / 3600).toFixed(1)
          next.pendingOffline = (next.pendingOffline || 0) + earned
          setOfflinePopup({ earned: Math.floor(earned), hrs, claim: true })
          try { logEvent('offline_earned', { earned: Math.floor(earned), elapsed_h: Math.round((elapsed / 3600) * 10) / 10 }) } catch {}
        }
      }
      commit(next); saveIdleState(next)
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const claimOffline = () => {
    setState(s => {
      const amt = s.pendingOffline || 0
      const next = { ...s, pendingOffline: 0, ohr: s.ohr + amt, lifetimeOhr: (s.lifetimeOhr || 0) + amt }
      saveIdleState(next)
      return next
    })
    try { logEvent('offline_claim', { earned: Math.floor(state.pendingOffline || 0) }) } catch {}
    setOfflinePopup(null)
  }

  const buyAmount = (i) => {
    const owned = state.owned[i] || 0
    const watchCost = watchEffects(state).cost
    if (bulk === 'max') {
      const { n, spend } = maxBuyable(i, owned, state.ohr, diff, watchCost)
      return { n, spend }
    }
    const n = parseInt(bulk, 10)
    return { n, spend: bulkCost(i, owned, n, diff, watchCost) }
  }

  const buy = (i) => {
    if (!exileAllows(state, i)) {
      // Vow-bound: explain instead of silently ignoring.
      setBuyHint({ i, need: 0, locked: true })
      setTimeout(() => setBuyHint(null), 3500)
      return
    }
    const owned = state.owned[i] || 0
    const { n, spend } = buyAmount(i)
    if (n <= 0 || state.ohr < spend) {
      // Never silently ignore a click — tell them exactly what's missing.
      setBuyHint({ i, need: Math.max(1, Math.ceil(spend - state.ohr)) })
      setTimeout(() => setBuyHint(null), 3500)
      return
    }
    const next = { ...state, ohr: state.ohr - spend, owned: { ...state.owned, [i]: owned + n } }
    setState(next); saveIdleState(next)
    try { logEvent('purchase', { letter: i, n, spend, bulk, ohr_left: Math.floor(next.ohr) }) } catch {}
    if (!next.muted) playLetterAudio(i)
  }

  const playLetterAudio = async (i) => {
    // Perf (Track D2): pooled URL cache + shared element (see audio-pool).
    try { await playHebrewAudio(LETTERS[i]) } catch {}
  }

  // Scribes: hire a self-buyer for a MASTERED letter (learning stays manual —
  // the quill only appears at 0.8+ and after the first root).
  const hire = (i) => {
    const next = { ...state }
    if (!hireScribe(next, i)) {
      setBoostFlash({ text: `Need ${scribeCost(state)} 🌟 Kavod for a ${LETTERS[i]} scribe — Kavod comes only from correct answers.` })
      setTimeout(() => setBoostFlash(null), 4000)
      return
    }
    setState(next); saveIdleState(next)
    try { logEvent('scribe', { letter: i, cost: scribeCost(state) }) } catch {}
  }

  const doPrestige = () => {
    const target = rootsEarned(state.lifetimeOhr || 0)
    const gained = Math.max(0, target - (state.roots || 0))
    if (gained <= 0) {
      // The button only shows when nextRoots > roots, but a stale render can
      // still land here — never swallow the click silently.
      const need = Math.floor((goals?.root?.need || 0))
      setBoostFlash({ text: need > 0 ? `🌿 Not yet — ${fmtBig(need)} lifetime Ohr for root #${goals?.root?.next}. Keep studying.` : '🌿 Not yet — keep studying and the next root will come.' })
      setTimeout(() => setBoostFlash(null), 4000)
      return
    }
    const next = { ...state }
    applyPrestige(next)
    setState({ ...next }); saveIdleState(next)
    try { logEvent('prestige', { gained, roots: next.roots, lifetime: Math.floor(next.lifetimeOhr || 0), prestiges: next.prestiges }) } catch {}
    setPrestigeFlash({ gained })
    setTimeout(() => setPrestigeFlash(null), 5000)
    setPrestigeTick(t => t + 1)
    if (onEarn) onEarn(0)
  }

  // Vow exile mid-run (no reset — production intact, growth constrained).
  const takeExile = () => {
    const next = { ...stateRef.current }
    const letters = rollExileLetters()
    if (!startExile(next, letters)) return
    commit(next); saveIdleState(next)
    try { logEvent('vow', { kind: 'exile', letters }) } catch {}
    setBoostFlash({ text: `⛓️ Exile vowed — new study is ${letters.map(i => LETTERS[i]).join(' · ')} only, until your next root. Double 🌟 meanwhile.` })
    setTimeout(() => setBoostFlash(null), 4500)
  }

  // Copy a plain-text workshop card for pasting anywhere (no backend, no accounts).
  const shareWorkshop = () => {
    const text = shareCard(stateRef.current)
    const done = () => {
      setBoostFlash({ text: '📣 Workshop card copied — paste it to your study group.' })
      setTimeout(() => setBoostFlash(null), 4000)
    }
    try { logEvent('share', {}) } catch {}
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done))
    } else fallbackCopy(text, done)
  }

  const fallbackCopy = (text, done) => {
    try {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      done()
    } catch {}
  }

  // Vow shemittah for its hour (no reset — production intact, taps double).
  const takeRest = () => {
    const next = { ...stateRef.current }
    if (!startShemittah(next)) return
    commit(next); saveIdleState(next)
    try { logEvent('vow', { kind: 'shemittah' }) } catch {}
    setBoostFlash({ text: '🌾 Shemittah vowed — the land rests for one hour. No inscribing; every tap counts double.' })
    setTimeout(() => setBoostFlash(null), 4500)
  }

  // Answer the Golden Prompt's own popup quiz (the prompt asks; no study needed).
  const answerQuiz = (choiceIdx) => {
    const next = { ...stateRef.current }
    const rate = statePerSecond(next, mastery, gramMult) * buffMultiplier(next)
    const res = answerGoldenQuiz(next, choiceIdx, Date.now(), rate)
    if (!res) return
    commit(next); saveIdleState(next)
    if (res.choice) {
      // The Prophet offers — the quiz is passed, so the choice never expires.
      setProphetPick({ options: res.choice })
      try { logEvent('prophet', { options: res.choice }) } catch {}
    } else if (res.claimed) {
      setGoldenFlash({ name: res.claimed.name, desc: res.claimed.desc, fizzled: false })
      setTimeout(() => setGoldenFlash(null), 4000)
      try { logEvent('golden', { id: res.claimed.id, granted: Math.floor(res.granted || 0) }) } catch {}
    } else if (res.fizzled) {
      setGoldenFlash({ name: '', desc: '', fizzled: true })
      setTimeout(() => setGoldenFlash(null), 4000)
      try { logEvent('golden', { fizzled: true, reason: res.reason }) } catch {}
    }
    if (onEarn && res.granted > 0) onEarn(res.granted)
  }

  // Take one of the Prophet's three blessings (the choice itself never expires).
  const takeBlessing = (id) => {
    const next = { ...stateRef.current }
    const rate = statePerSecond(next, mastery, gramMult) * buffMultiplier(next)
    const res = applyProphetChoice(next, id, rate)
    if (res.fizzled) { setProphetPick(null); return }
    commit(next); saveIdleState(next)
    setProphetPick(null)
    try { logEvent('prophet_choice', { id, granted: Math.floor(res.granted || 0) }) } catch {}
    setGoldenFlash({ name: res.claimed.name, desc: res.claimed.desc, fizzled: false })
    setTimeout(() => setGoldenFlash(null), 4000)
  }

  const buyBoostFrenzy = () => {
    let ok = false
    setState(s => {
      const next = { ...s }
      ok = buyFrenzy(next)
      if (ok) saveIdleState(next)
      return next
    })
    if (ok) {
      try { logEvent('boost', { kind: 'frenzy', cost: FRENZY_COST }) } catch {}
      setBoostFlash({ text: `🌬️ Ruach Frenzy! x${FRENZY_MULT} Ohr for 60s — keep answering to chain it.` })
      setTimeout(() => setBoostFlash(null), 4000)
    }
  }

  const buyBoostWarp = () => {
    let granted = 0
    let cost = 0
    let warps = 0
    setState(s => {
      const next = { ...s }
      cost = warpCost(next)
      const rate = statePerSecond(next, mastery, gramMult) * buffMultiplier(next)
      granted = buyTimeWarp(next, rate, 1)
      warps = next.warps || 0
      if (granted > 0) saveIdleState(next)
      return next
    })
    if (granted > 0) {
      try { logEvent('boost', { kind: 'warp', cost, granted: Math.floor(granted), warps }) } catch {}
      setBoostFlash({ text: `⏳ Time Warp! +${fmtBig(granted)} Ohr (1h, cost ${cost} 🌟).` })
      setTimeout(() => setBoostFlash(null), 4000)
    }
  }

  const claimQuestReward = (id) => {    let reward = 0
    setState(s => {
      const next = { ...s }
      reward = claimQuest(next, id)
      if (reward > 0) saveIdleState(next)
      return next
    })
    if (reward > 0) {
      try { logEvent('quest', { id, reward }) } catch {}
      const q = QUESTS.find(x => x.id === id)
      setQuestFlash({ name: q?.name, reward })
      setTimeout(() => setQuestFlash(null), 4000)
    }
  }

  // Heavenly chain: spend Aliyah sparks (pure — computed from the mirror, applied once).
  const buyHeaven = (id) => {
    const next = { ...stateRef.current }
    if (!buyHeavenly(next, id)) {
      const u = HEAVENLY_UPGRADES.find(x => x.id === id)
      const tier = u?.tier ?? 0
      const open = tier === 0 || heavenlyTierOwned(next, tier - 1)
      setBoostFlash({ text: !open ? `💫 Station ${tier + 1} is sealed — ascend the station before it first.` : `💫 Need ${(u?.cost || 0) - availableSparks(next)} more spark${(u?.cost || 0) - availableSparks(next) === 1 ? '' : 's'} for ${u?.name || 'this'}. Unspent sparks still earn +1% Ohr each.` })
      setTimeout(() => setBoostFlash(null), 4000)
      return
    }
    commit(next); saveIdleState(next)
    try { logEvent('upgrade', { kind: 'heavenly', id }) } catch {}
    const u = HEAVENLY_UPGRADES.find(x => x.id === id)
    const left = availableSparks(next)
    setBoostFlash({ text: `💫 ${u.icon} ${u.name} — ${u.desc}. ${left} unspent spark${left === 1 ? '' : 's'} still giving +${left}% Ohr.` })
    setTimeout(() => setBoostFlash(null), 4500)
  }

  // Fig harvest + daily claim (pure — from the mirror, applied once).
  const harvest = () => {
    const next = { ...stateRef.current }
    const granted = harvestFig(next, statePerSecond(next, mastery, gramMult) * buffMultiplier(next))
    if (granted <= 0) return
    commit(next); saveIdleState(next)
    try { logEvent('fig', { granted: Math.floor(granted), level: next.figs.level }) } catch {}
    setBoostFlash({ text: `🍯 Fig harvested! +${fmtBig(granted)} Ohr · grove level ${next.figs.level} (+${next.figs.level * 10}% Ohr forever).` })
    setTimeout(() => setBoostFlash(null), 4500)
  }

  const claimDailyReward = () => {
    const next = { ...stateRef.current }
    const granted = claimDaily(next, statePerSecond(next, mastery, gramMult) * buffMultiplier(next))
    if (granted <= 0) return
    commit(next); saveIdleState(next)
    try { logEvent('daily', { granted: Math.floor(granted) }) } catch {}
    setBoostFlash({ text: `📅 Daily lesson complete! +${fmtBig(granted)} Ohr. Come back tomorrow.` })
    setTimeout(() => setBoostFlash(null), 4500)
  }

  // Vine harvest (pure — from the mirror, applied once). One vine at a time,
  // tap-to-harvest like figs: never quiz-gated, rewards the buffed rate.
  const harvestVineAt = (i) => {
    const next = { ...stateRef.current }
    const granted = harvestVine(next, i, statePerSecond(next, mastery, gramMult) * buffMultiplier(next))
    if (granted <= 0) return
    commit(next); saveIdleState(next)
    try { logEvent('vineyard', { granted: Math.floor(granted), level: next.vineyard.level, vine: i }) } catch {}
    setBoostFlash({ text: `🍇 Vine harvested! +${fmtBig(granted)} Ohr · vineyard level ${next.vineyard.level} (+${next.vineyard.level * 5}% Ohr forever).` })
    setTimeout(() => setBoostFlash(null), 4500)
  }

  const giveFeedback = (kind) => {
    setState(s => {
      const next = { ...s, difficulty: applyFeedback(s.difficulty || { bias: 0, recent: [] }, kind) }
      saveIdleState(next)
      try { logEvent('feedback', { kind, bias: next.difficulty.bias }) } catch {}
      return next
    })
    setFeedbackFlash(kind)
    setTimeout(() => setFeedbackFlash(null), 3000)
  }

  const prestigeReady = shouldPrestige(state.lifetimeOhr || 0, state.roots || 0)
  const nextRoots = rootsEarned(state.lifetimeOhr || 0)
  const frenzySecs = frenzyRemainingSec(state)
  const frenzyActive = frenzySecs > 0
  const effPerSec = perSec * buffMultiplier(state)
  const warpPrice = warpCost(state)
  const goldenSecs = goldenRemainingSec(state)
  const goldenPrompt = state.golden ? GOLDEN_PROMPTS.find(p => p.id === state.golden.id) : null
  const shemenPct = Math.round((shemenMultiplier(state) - 1) * 100)
  const earnedAch = achievementsEarned(state)
  const figIsReady = figReady(state)
  // Coarse "20h left" sat static for an hour — show h+m so the timer visibly moves.
  const fmtWait = (sec) => {
    const s = Math.max(0, Math.ceil(sec))
    if (s < 60) return `${s}s`
    const m = Math.floor(s / 60)
    if (m < 60) return `${m}m ${s % 60}s`
    const h = Math.floor(m / 60)
    if (h < 48) return `${h}h ${m % 60}m`
    return `${Math.floor(h / 24)}d ${h % 24}h`
  }
  const figWait = fmtWait(figRemainingSec(state))
  const fmtRate = (v) => {
    if (!(v > 0)) return '0'
    if (v < 10) return v.toFixed(1)
    if (v < 1000) return Math.floor(v).toLocaleString()
    if (v < 1e8) return `${(v / 1000).toFixed(1)}k`
    return fmtBig(v) // 9+ digits go scientific, never "100000.0k"
  }
  const figLevel = state.figs?.level || 0
  const figPct = figIsReady ? 1 : figLevel >= 0 && state.figs?.readyAt
    ? Math.max(0, Math.min(1, 1 - figRemainingSec(state) / (FIG_RIPEN_HOURS * 3600)))
    : 0
  const vineLevel = state.vineyard?.level || 0
  const vines = Array.from({ length: VINE_COUNT }, (_, i) => {
    const ready = vineReady(state, i)
    const remaining = vineRemainingSec(state, i)
    return {
      i, ready, remaining,
      hoursLeft: Math.ceil(remaining / 3600),
      wait: fmtWait(remaining),
      pct: ready ? 1 : state.vineyard?.vines?.[i]
        ? Math.max(0, Math.min(1, 1 - remaining / (VINE_RIPEN_HOURS * 3600)))
        : 0,
    }
  })
  const dailyOk = dailyReady(state)
  // Toasts float top-center as an overlay stack — transient flashes must
  // never push the shop or HUD around (no layout shift, ever).
  const toasts = [
    boostFlash && { id: 'boost', cls: 'bg-orange-500', text: boostFlash.text },
    goldenFlash && {
      id: 'golden', cls: goldenFlash.fizzled ? 'bg-neutral-500' : 'bg-yellow-500',
      text: goldenFlash.fizzled ? '🌫️ The prompt faded — no harm done. Another will come.' : `✨ ${goldenFlash.name} — ${goldenFlash.desc}!`,
    },
    prestigeFlash && {
      id: 'prestige', cls: 'bg-teal-600',
      text: `🌿 You erase the א — +${prestigeFlash.gained} root${prestigeFlash.gained > 1 ? 's' : ''} (+${prestigeFlash.gained * 10}% Ohr forever).`,
    },
    milestoneFlash && {
      id: 'milestone', cls: 'bg-orange-500',
      text: `🔥 ${milestoneFlash.milestone} streak! +${fmtBig(milestoneFlash.bonus)} Ohr burst.`,
    },
    questFlash && {
      id: 'quest', cls: 'bg-green-600',
      text: `✅ Quest complete: ${questFlash.name} (+${fmtBig(questFlash.reward)} Ohr)`,
    },
    buyHint && {
      id: 'buyhint', cls: 'bg-red-500',
      text: buyHint.locked
        ? (exileKind === 'shemittah'
          ? '🌾 The land rests — no inscribing until the next root. Study on: every tap counts double.'
          : `⛓️ ${LETTERS[buyHint.i]} is beyond your vow — exile study is ${exileLetters.map(i => LETTERS[i]).join(' · ')} until the next root.`)
        : `Need ${fmtBig(buyHint.need)} more ✨ Ohr for ${LETTERS[buyHint.i]} — answer a question (tap bonus) or let your golems mine.`,
    },
    feedbackFlash && {
      id: 'feedback', cls: 'bg-neutral-600',
      text: feedbackFlash === 'easier' ? '✓ Eased — letters cheaper, taps bigger, timers longer.'
        : feedbackFlash === 'harder' ? '✓ Spicier — letters pricier, taps smaller, timers tighter.'
        : '✓ Locked in — auto-tuning continues in the background.',
    },
  ].filter(Boolean)
  const dailyCount = Math.min(DAILY_GOAL, state.daily?.correct || 0)
  const dailyClaimed = !!state.daily?.claimed
  const graceAvailable = (state.streakGraceDay || '') !== dayKey()
  const prophetPending = state.golden?.id === 'prophet'
  const exileLetters = state.exile?.kind === 'exile' ? state.exile.letters : null
  const exileKind = state.exile?.kind || null
  const vowHoursLeft = state.exile?.endsAt ? Math.max(0, Math.ceil((state.exile.endsAt - Date.now()) / 3600000)) : VOW_MAX_HOURS

  return (
    <div className="mb-4 p-3 rounded-xl bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/20 border border-amber-200 dark:border-amber-800 relative flex flex-col overflow-hidden max-h-[calc(100vh-6.5rem)] max-h-[calc(100dvh-6.5rem)] sm:max-h-[100dvh] sticky top-10 z-10 sm:static">
      <style>{`
        @keyframes idle-rise { 0% { opacity: 0; transform: translateY(6px) scale(0.9); } 15% { opacity: 1; transform: translateY(0) scale(1.05); } 100% { opacity: 0; transform: translateY(-22px) scale(1); } }
        .idle-gain { animation: idle-rise 1.4s ease-out forwards; }
        @keyframes idle-pop { 0% { transform: scale(0.8); } 40% { transform: scale(1.1); } 100% { transform: scale(1); } }
        .idle-pop { animation: idle-pop 0.35s ease-out; }
        @keyframes tap-ring-good { 0% { box-shadow: inset 0 0 0 3px rgba(34,197,94,.8); } 100% { box-shadow: inset 0 0 0 0 rgba(34,197,94,0); } }
        @keyframes tap-ring-bad { 0% { box-shadow: inset 0 0 0 3px rgba(239,68,68,.8); } 100% { box-shadow: inset 0 0 0 0 rgba(239,68,68,0); } }
        .tap-flash-good { animation: tap-ring-good .5s ease-out; }
        .tap-flash-bad { animation: tap-ring-bad .5s ease-out; }
        @media (prefers-reduced-motion: reduce) {
          .idle-gain, .idle-pop, .tap-flash-good, .tap-flash-bad { animation: none; }
        }
      `}</style>
      {/* Tap feedback: graded answers AND golem taps flash this panel (green =
          tap landed, red = missed) and pop the counters — the tap must be
          visible exactly where the numbers live. */}
      {answerPulse && (
        <div key={answerPulse.n}
          className={`absolute inset-0 rounded-xl pointer-events-none ${answerPulse.correct ? 'tap-flash-good' : 'tap-flash-bad'}`}
          aria-hidden="true" />
      )}

      {/* HUD row — stacks on mobile */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
        <div className="flex items-center gap-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-amber-600 dark:text-amber-400 font-semibold">✨ Ohr</div>
            <div key={state.taps || 0} className="idle-pop text-2xl sm:text-xl font-bold text-neutral-800 dark:text-neutral-100 tabular-nums">
              {fmtBig(state.ohr)}
            </div>
          </div>
          {/* HUD strip — permanent space is earned by frequency: Ohr, rate,
              tap, streak, the two currencies. Buffs collapse to one combo
              pill, passive bonuses to one ✦ popover, both tap-for-detail. */}
          <div className="text-xs text-neutral-500 dark:text-neutral-400">
            {effPerSec.toFixed(1)}/s · tap {(tapValue(perSec, state.streak, state.tracks, diff, state.perm, tapBuffMultiplier(state)) * shemittahTapMult(state) * watchEffects(state).tap).toFixed(1)}{exileKind === 'shemittah' ? ' ×2🌾' : ''} · 🔥{state.bestStreak || 0} best{state.streak > 0 && ` · ${state.streak} now`}{graceAvailable && <span title="Streak grace: once a day, a wrong answer halves a 10+ streak instead of resetting it."> · 🛡️</span>}
            {state.roots > 0 && <span> · 🌿 {state.roots}</span>}
            <span title="Kavod — earned only by correct answers, buys speed"> · 🌟 <span key={Math.floor(state.kavod || 0)} className="idle-pop inline-block">{fmtBig(state.kavod || 0)}</span></span>
            {(frenzyActive || galeMultiplier(state) > 1 || shofarMultiplier(state) > 1) && (
              <details className="relative inline-block">
                <summary className="cursor-pointer font-bold text-orange-500 hover:underline" title="Active buffs multiply together — tap for detail">
                  {' '}· ⚡COMBO x{activeBuffCount(state)} ▾
                </summary>
                <div className="absolute left-0 z-30 mt-1 p-2 rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-xl text-[11px] whitespace-nowrap">
                  {frenzyActive && <div>🌬️ Frenzy x{FRENZY_MULT} · {frenzySecs}s left</div>}
                  {galeMultiplier(state) > 1 && <div>🌪️ Gale x{galeMultiplier(state)}</div>}
                  {shofarMultiplier(state) > 1 && <div>📯 Shofar x{shofarMultiplier(state).toFixed(1)}</div>}
                </div>
              </details>
            )}
            {(synPct > 0 || gramPct > 0 || sparksTotal > 0 || sparkProg.pct > 0 || shemenPct > 0) && (
              <details className="relative inline-block">
                <summary className="cursor-pointer hover:underline" title="Passive bonuses — tap for detail">
                  {' '}· ✦ ▾
                </summary>
                <div className="absolute left-0 z-30 mt-1 p-2 rounded-lg bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-xl text-[11px] whitespace-nowrap space-y-0.5">
                  {synPct > 0 && (
                    <div className="text-amber-600 dark:text-amber-400"
                      title={`Breadth bonus: every letter you own boosts the others (+2% each, +4% more per mastered). Currently +${synPct}%, cap +100%.`}>
                      ⚡ Synergy +{synPct}%
                    </div>
                  )}
                  {gramPct > 0 && (
                    <div className="text-sky-600 dark:text-sky-400"
                      title={`Grammar tracks: +5% Ohr for each complete track-tier (binyanim/clauses/nominals × levels). Currently +${gramPct}%, cap +50%.`}>
                      📜 Grammar +{gramPct}%
                    </div>
                  )}
                  {(sparksTotal > 0 || sparkProg.pct > 0) && (
                    <div className="text-teal-600 dark:text-teal-400"
                      title="Aliyah sparks — cube root of lifetime Ohr. Each UNSPENT spark is +1% Ohr; spend them on the heavenly chain (⬆️ Upgrades).">
                      💫 Sparks {sparks}{sparks > 0 ? ` +${Math.round((sparkBonus(sparks) - 1) * 100)}%` : ''}
                    </div>
                  )}
                  {shemenPct > 0 && (
                    <div className="text-lime-600 dark:text-lime-500"
                      title={`Shemen (oil): +4% Ohr for each achievement — ${earnedAch.length}/${ACHIEVEMENTS.length} earned.`}>
                      🫒 Shemen +{shemenPct}%
                    </div>
                  )}
                </div>
              </details>
            )}
            {(() => {
              const live = activeFeasts()
              if (live.length) {
                const f = live[0]
                return (
                  <button onClick={() => setShowFeast({ feast: f, daysUntil: 0 })}
                    title={`${f.name} is live — tap for meaning, scriptures, vocab. ${f.effect}`}
                    className="text-amber-600 dark:text-amber-400 font-semibold cursor-pointer hover:underline">
                    {' '}· {f.icon} {f.name}{f.len > 1 ? ` d${f.dayIndex + 1}` : ''}
                  </button>
                )
              }
              const nx = nextFeast()
              if (!nx) return null
              return (
                <button onClick={() => setShowFeast({ feast: nx.feast, daysUntil: nx.daysUntil })}
                  title={`Next moed: ${nx.feast.name} — tap for meaning, scriptures, vocab. ${nx.feast.effect}`}
                  className="cursor-pointer hover:underline">
                  {' '}· → {nx.feast.icon} {nx.daysUntil}d
                </button>
              )
            })()}
          </div>
          {/* Tap floaters: every correct answer pops its reward — stacked, none dropped */}
          {gains.length > 0 ? (
            <span className="pointer-events-none inline-flex flex-col items-end" aria-live="polite">
              {gains.map(g => (
                <span key={g.id}
                  className={`idle-gain text-sm font-bold tabular-nums whitespace-nowrap ${g.crit ? 'text-orange-500 text-base' : 'text-green-600 dark:text-green-400'}`}>
                  +{g.value.toFixed(1)} +{g.kavod}🌟{g.crit ? ' CRIT! ⚡' : ''}
                </span>
              ))}
            </span>
          ) : lastGain ? (
            <span
              className={`idle-gain pointer-events-none text-sm font-bold tabular-nums whitespace-nowrap ${lastGain.crit ? 'text-orange-500 text-base' : 'text-green-600 dark:text-green-400'}`}>
              +{lastGain.value.toFixed(1)} +{lastGain.kavod}🌟{lastGain.crit ? ' CRIT! ⚡' : ''}
            </span>
          ) : null}
        </div>
        <span className="hidden sm:flex flex-1" />
        <div className="flex flex-wrap gap-2">
          {/* Settings live behind a gear — mute + golem visibility, not permanent buttons. */}
          <details className="relative">
            <summary className="min-h-[44px] min-w-[44px] px-2 rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-500 cursor-pointer flex items-center justify-center list-none [&::-webkit-details-marker]:hidden"
              title="Workshop settings">
              ⚙️
            </summary>
            <div className="absolute left-0 z-30 mt-1 p-1.5 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-xl flex flex-col gap-1 w-44">
              <button onClick={() => setState(s => { const n = { ...s, muted: !s.muted }; saveIdleState(n); return n })}
                className="min-h-[44px] px-3 rounded-lg text-xs text-left text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer"
                title="Toggle letter audio">
                {state.muted ? '🔇 Muted' : '🔊 Audio on'}
              </button>
              <button onClick={() => setShowGolems(s => !s)}
                className="min-h-[44px] px-3 rounded-lg text-xs text-left text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer"
                title="Show or hide the golem workshop (tapping still earns via answers)">
                {showGolems ? '🫥 Hide golems' : '🗿 Show golems'}
              </button>
              <button onClick={() => setState(s => { const n = { ...s, haptics: s.haptics === false }; saveIdleState(n); return n })}
                className="min-h-[44px] px-3 rounded-lg text-xs text-left text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer"
                title="Tap vibration (light buzz per tap, double-buzz every 100th)">
                {state.haptics === false ? '📳 Haptics off' : '📳 Haptics on'}
              </button>
            </div>
          </details>
          {sync !== 'off' && (
            <span title={sync === 'ok' ? 'Workshop syncs to your account — same progress on phone & computer' : sync === 'busy' ? 'Syncing…' : 'Sync failed — playing local (progress stays on this device)'}
              className={`min-h-[44px] min-w-[44px] px-2 rounded-lg border flex items-center justify-center text-sm ${sync === 'err' ? 'border-red-300 text-red-500' : 'border-neutral-200 dark:border-neutral-700 text-neutral-500'}`}
              aria-live="polite">
              {sync === 'busy' ? '☁️···' : sync === 'err' ? '☁️!' : '☁️'}
            </span>
          )}
          <button onClick={() => setActiveTab('letters')} data-testid="shop-toggle" aria-label="Letter shop"
            className={`flex-1 sm:flex-none min-h-[44px] text-sm px-4 rounded-lg font-medium cursor-pointer ${totalOwned(state) === 0 ? 'bg-amber-500 hover:bg-amber-600 text-white animate-pulse' : 'bg-amber-500 hover:bg-amber-600 text-white'}`}>
            Letters ▼
          </button>
          {nextRoots > (state.roots || 0) && (
            <button onClick={doPrestige}
              title={exileKind ? 'Complete your vow run: forge roots, release the vow' : 'Forge roots: reset Ohr + generators, keep roots, +10% each forever'}
              className={`flex-1 sm:flex-none min-h-[44px] text-sm px-4 rounded-lg font-medium cursor-pointer ${prestigeReady ? 'bg-teal-600 hover:bg-teal-700 text-white animate-pulse' : 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300'}`}>
              🌿 Root (+{nextRoots - (state.roots || 0)})
            </button>
          )}
          {!exileKind && heavenlyOwned(state, 'h_legacy') && totalOwned(state) > 0 && (
            <button onClick={takeExile}
              title="Vow exile, any time: lock new study to Aleph + 2 letters until your next root, for double 🌟 Kavod (your workshop keeps running)"
              className="flex-1 sm:flex-none min-h-[44px] text-sm px-4 rounded-lg font-medium cursor-pointer bg-neutral-700 hover:bg-neutral-800 text-white active:scale-[0.99]">
              ⛓️ Exile
            </button>
          )}
          {!exileKind && heavenlyOwned(state, 'h_legacy') && totalOwned(state) > 0 && (
            <button onClick={takeRest}
              title="Vow shemittah (rest hour), any time: inscribe nothing for one hour — every tap counts double"
              className="flex-1 sm:flex-none min-h-[44px] text-sm px-4 rounded-lg font-medium cursor-pointer bg-lime-700 hover:bg-lime-800 text-white active:scale-[0.99]">
              🌾 Rest
            </button>
          )}
        </div>
      </div>

      {/* The horde — letters become visible golems that work for you.
          Tap them for a little Ohr; correct answers earn the big taps + Kavod. */}
      {showGolems && (
        <div className="relative">
          <GolemCanvas owned={state.owned} mastery={mastery} prestigeTick={prestigeTick} answerPulse={answerPulse} onTap={doCanvasTap} />
          {/* First-tap cue: a tappable-looking chip floating over the workshop
              until the first tap lands — teaches the clicker without words. */}
          {(state.taps || 0) === 0 && totalOwned(state) > 0 && (
            <span className="absolute bottom-1.5 left-1/2 -translate-x-1/2 pointer-events-none px-2.5 py-1 rounded-full bg-amber-500 text-white text-[11px] font-bold shadow-lg animate-pulse" aria-hidden="true">
              👆 tap the golems!
            </span>
          )}
          {tapFloats.map(t => (
            <span key={t.id}
              className={`idle-gain pointer-events-none absolute text-sm font-bold tabular-nums whitespace-nowrap ${t.crit ? 'text-orange-500 text-base' : 'text-green-600 dark:text-green-400'}`}
              style={{ left: t.x, top: t.y, transform: 'translate(-50%, -100%)' }}
              aria-hidden="true">
              +{t.value.toFixed(1)}{t.crit ? ' ⚡' : ''}
            </span>
          ))}
        </div>
      )}

      {/* The active vow */}
      {exileKind === 'exile' && exileLetters && (
        <div className="mt-2 p-2 rounded-lg bg-neutral-700 text-neutral-100 text-xs text-center font-medium">
          ⛓️ In exile: new study is {exileLetters.map(i => LETTERS[i]).join(' · ')} only (the workshop keeps running) · double 🌟 Kavod · prestige out any time, or release in {vowHoursLeft}h
        </div>
      )}
      {exileKind === 'shemittah' && (
        <div className="mt-2 p-2 rounded-lg bg-lime-700 text-white text-xs text-center font-medium">
          🌾 Shemittah — the land rests for {fmtWait(((state.exile?.endsAt || 0) - Date.now()) / 1000)} more: no inscribing · every tap counts double
        </div>
      )}
      {/* Golden result flashes live in the overlay toast stack. */}

      {/* Next goals live in the Quests tab — "what am I working toward" has its own spot. */}
      {/* Prestige/milestone/quest flashes live in the overlay toast stack. */}

      {/* Offline: tap-to-claim, never silent */}
      {(offlinePopup || (state.pendingOffline || 0) >= 1) && (
        <button onClick={claimOffline}
          className="mt-2 w-full min-h-[48px] p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer active:scale-[0.99]">
          🌙 While you were away{offlinePopup?.hrs ? ` (${offlinePopup.hrs}h)` : ''}: +{fmtBig(state.pendingOffline || offlinePopup?.earned || 0)} Ohr — tap to claim
        </button>
      )}

      {/* First-run call to action — the buy button must be unmissable. */}
      {totalOwned(state) === 0 && (
        <div className="mt-2 p-2.5 rounded-lg bg-amber-100 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-700 text-xs text-amber-800 dark:text-amber-200">
          <b>👋 Start here:</b> tap any letter below to inscribe your <b>first golem</b>. You have {fmtBig(state.ohr)} ✨ Ohr — the first letters cost 10–40. Golems then mine Ohr for you while you study.
        </div>
      )}
      {/* Tap affordance: until the first tap lands, say where taps come from. */}
      {(state.taps || 0) === 0 && totalOwned(state) > 0 && (
        <div className="mt-2 p-2.5 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 text-xs text-green-800 dark:text-green-200">
          <b>👆 Two ways to earn:</b> tap your golems above for a little Ohr any time — each correct answer below pops <b>big +Ohr</b> up top and flashes this panel green. Wrong answers flash red (streak only, nothing lost).
        </div>
      )}


      {/* Boosts tab — learning buys the speed that idle games sell for money.
          Pace controls live here too, beside the buffs they tune. */}
      {activeTab === 'boosts' && (
      <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
      <div className="mt-2 flex gap-2">
        <button onClick={buyBoostFrenzy} disabled={(state.kavod || 0) < FRENZY_COST || frenzyActive}
          title={frenzyActive ? `Frenzy active — ${frenzySecs}s left` : `x${FRENZY_MULT} Ohr/sec for 60s — costs ${FRENZY_COST} 🌟`}
          className={`flex-1 min-h-[48px] px-3 rounded-lg text-xs font-semibold cursor-pointer active:scale-[0.99] ${frenzyActive ? 'bg-orange-500 text-white' : (state.kavod || 0) >= FRENZY_COST ? 'bg-white dark:bg-neutral-800 border-2 border-orange-400 dark:border-orange-600 text-orange-600 dark:text-orange-300' : 'bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300'}`}>
          {frenzyActive ? `🌬️ Frenzy x${FRENZY_MULT} · ${frenzySecs}s` : `🌬️ Frenzy x${FRENZY_MULT} · ${FRENZY_COST} 🌟`}
        </button>
        <button onClick={buyBoostWarp} disabled={(state.kavod || 0) < warpPrice}
          title={`Instantly grant 1h of production — costs ${warpPrice} 🌟 (earned only by studying)`}
          className={`flex-1 min-h-[48px] px-3 rounded-lg text-xs font-semibold cursor-pointer active:scale-[0.99] ${(state.kavod || 0) >= warpPrice ? 'bg-white dark:bg-neutral-800 border-2 border-indigo-400 dark:border-indigo-600 text-indigo-600 dark:text-indigo-300' : 'bg-neutral-100 dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300'}`}>
          ⏳ +1h now · {warpPrice} 🌟
        </button>
      </div>
      {/* Difficulty feedback — the player tunes the algorithm */}
      <div className="mt-2 flex items-center gap-2 flex-wrap">
        <span className="text-[10px] text-neutral-500 dark:text-neutral-400">
          Pace: <b>{scalars.label}</b>
          {acc !== null && <span> · recent {Math.round(acc * 100)}%</span>}
        </span>
        <span className="flex-1" />
        <div className="flex gap-1.5" role="group" aria-label="Difficulty feedback">
          <button onClick={() => { try { exportLog() } catch {} }}
            className="min-h-[44px] px-2.5 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 cursor-pointer active:scale-95"
            title="Download the full event log (JSON) for balancing">
            📊 Log
          </button>
          <button onClick={shareWorkshop}
            className="min-h-[44px] px-2.5 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 cursor-pointer active:scale-95"
            title="Copy a text snapshot of your workshop for your study group (no account, nothing uploaded)">
            📣 Share
          </button>
          <button onClick={() => setShowGolems(s => !s)}
            className="min-h-[44px] px-2.5 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 cursor-pointer active:scale-95"
            title="Show or hide the golem workshop">
            {showGolems ? '🫥 Hide golems' : '🗿 Show golems'}
          </button>
          <button onClick={() => giveFeedback('easier')}
            className="min-h-[44px] px-2.5 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 cursor-pointer active:scale-95"
            title="Make it easier (cheaper letters, bigger taps, more time)">
            😅 Too hard
          </button>
          <button onClick={() => giveFeedback('just-right')}
            className="min-h-[44px] px-2.5 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 cursor-pointer active:scale-95"
            title="Feels right">
            🙂 OK
          </button>
          <button onClick={() => giveFeedback('harder')}
            className="min-h-[44px] px-2.5 rounded-lg text-xs border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 cursor-pointer active:scale-95"
            title="Make it harder (pricier letters, smaller taps, tighter timers)">
            😌 Too easy
          </button>
        </div>
      </div>
      {/* Difficulty feedback confirmations live in the overlay toast stack. */}
      <div className="mt-1 text-[11px] text-neutral-500 dark:text-neutral-400">
        Answer → tap Ohr → buy letters → quests → roots. Green dot = mastered (0.8+). ⚡ = breadth bonus (each letter you own lifts all the others). The game watches your accuracy and adjusts — the pace buttons steer it.
      </div>
      </div>
      )}


      {/* Toasts live in the overlay stack at the end — nothing flashes in-flow. */}

      {/* Golden Prompt — the prompt asks its own letter question, right here.
          Three modes, never mixed scripts: name (see glyph → pick name),
          glyph (see name → pick glyph), audio (hear it → pick glyph).
          Correct in 30s wins the buff (or the Prophet's choice); wrong or
          late fizzles, never drains. */}
      {state.golden && (goldenPrompt || prophetPending) && state.golden.quiz && (
        <div role="dialog" aria-label={prophetPending ? 'The Prophet visits — answer to choose your blessing' : `Golden Prompt — answer to win ${goldenPrompt?.desc || 'a blessing'}`}
          className="idle-pop fixed bottom-3 left-1/2 -translate-x-1/2 z-40 w-[min(94vw,32rem)] p-3 rounded-xl shadow-[0_0_36px_rgba(250,204,21,0.65)] ring-4 ring-yellow-200 dark:ring-yellow-700 bg-gradient-to-r from-yellow-400 to-amber-500 text-white text-base font-medium">
          {goldenSecs <= 10 && (
            <div className="animate-pulse mb-1.5 text-center text-sm font-bold" aria-live="polite">
              ⏳ Hurry — {goldenSecs}s left!
            </div>
          )}
          <div className="flex items-center gap-2">
            {state.golden.quiz.kind === 'word' && (
              <span className="flex-1">
                {state.golden.quiz.direction === 'en-he'
                  ? <span><b>📖 Translate!</b> "{state.golden.quiz.gloss}" in Hebrew? Pick it within {goldenSecs}s → {goldenPrompt?.desc}</span>
                  : <span><b>📖 Translate!</b> What does <b className="text-lg">{state.golden.quiz.hebrew}</b> mean? Pick it within {goldenSecs}s → {goldenPrompt?.desc}</span>}
              </span>
            )}
            {state.golden.quiz.kind === 'root' && (
              <span className="flex-1">
                {state.golden.quiz.direction === 'en-he'
                  ? <span><b>🌱 Root!</b> Which root means "{state.golden.quiz.gloss}"? Pick it within {goldenSecs}s → {goldenPrompt?.desc}</span>
                  : <span><b>🌱 Root!</b> What does the root <b className="text-lg">{state.golden.quiz.root}</b> mean? Pick it within {goldenSecs}s → {goldenPrompt?.desc}</span>}
              </span>
            )}
            {state.golden.quiz.kind !== 'word' && state.golden.quiz.kind !== 'root' && (state.golden.quiz.qtype || 'name') === 'name' && (
              <><span className="text-2xl" aria-hidden="true">{LETTERS[state.golden.quiz.letter]}</span>
              <span className="flex-1">
                {prophetPending
                  ? <span><b>🔮 The Prophet visits!</b> Name this letter within {goldenSecs}s → choose 1 of 3 blessings</span>
                  : <span><b>✨ Golden Prompt!</b> Name this letter within {goldenSecs}s → {goldenPrompt?.desc}</span>}
              </span></>
            )}
            {state.golden.quiz.qtype === 'glyph' && (
              <span className="flex-1">
                {prophetPending
                  ? <span><b>🔮 The Prophet visits!</b> Which letter is <b>{LETTER_NAMES[state.golden.quiz.letter]}</b>? Pick it within {goldenSecs}s → choose 1 of 3 blessings</span>
                  : <span><b>✨ Golden Prompt!</b> Which letter is <b>{LETTER_NAMES[state.golden.quiz.letter]}</b>? Pick it within {goldenSecs}s → {goldenPrompt?.desc}</span>}
              </span>
            )}
            {state.golden.quiz.qtype === 'audio' && (
              <><button onClick={() => { if (quizAudio?.url) playUrl(quizAudio.url) }}
                  disabled={!quizAudio?.url}
                  aria-label="Replay the letter sound"
                  className="shrink-0 min-h-[44px] min-w-[44px] rounded-lg bg-white/20 hover:bg-white/30 disabled:opacity-50 text-xl cursor-pointer">
                  🔊
                </button>
              <span className="flex-1">
                {quizAudio?.failed
                  ? <span><b>✨ Golden Prompt!</b> Which letter is <b>{LETTER_NAMES[state.golden.quiz.letter]}</b>? Pick it within {goldenSecs}s → {prophetPending ? 'choose 1 of 3 blessings' : goldenPrompt?.desc}</span>
                  : <span><b>🔊 Listen!</b> Which letter did you hear? Pick it within {goldenSecs}s → {prophetPending ? 'choose 1 of 3 blessings' : goldenPrompt?.desc}</span>}
              </span></>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-1.5 mt-1.5">
            {(state.golden.quiz.kind === 'word' || state.golden.quiz.kind === 'root')
              ? state.golden.quiz.options.map((opt, oi) => (
                <button key={oi} onClick={() => answerQuiz(oi)}
                  aria-label={`Answer: ${opt}`}
                  data-testid={`golden-word-${oi}`}
                  className={`min-h-[44px] px-2 rounded-lg bg-white/20 hover:bg-white/30 active:scale-95 cursor-pointer ${state.golden.quiz.direction === 'en-he' ? 'text-xl' : 'text-sm font-bold'}`}>
                  <span dir="auto">{opt}</span>
                </button>
              ))
              : null}
            {state.golden.quiz.kind !== 'word' && state.golden.quiz.kind !== 'root' && (state.golden.quiz.qtype || 'name') === 'name'
              ? state.golden.quiz.options.map((opt, oi) => (
                <button key={opt} onClick={() => answerQuiz(oi)}
                  aria-label={`Answer: ${LETTER_NAMES[opt]}`}
                  data-testid={`golden-opt-${opt}`}
                  className="min-h-[44px] px-2 rounded-lg bg-white/20 hover:bg-white/30 active:scale-95 text-sm font-bold cursor-pointer">
                  {LETTER_NAMES[opt]}
                </button>
              ))
              : state.golden.quiz.kind !== 'word' && state.golden.quiz.kind !== 'root'
              ? state.golden.quiz.options.map((opt, oi) => (
                <button key={opt} onClick={() => answerQuiz(oi)}
                  disabled={state.golden.quiz.qtype === 'audio' && !quizAudio?.url && !quizAudio?.failed}
                  aria-label={`Answer: letter option ${oi + 1}`}
                  data-testid={`golden-opt-${opt}`}
                  className="min-h-[52px] px-2 rounded-lg bg-white/20 hover:bg-white/30 active:scale-95 disabled:opacity-50 text-2xl cursor-pointer">
                  {LETTERS[opt]}
                </button>
              ))
              : null}
          </div>
          {state.quizDeck && (
            <div className="mt-1 text-[11px] text-white/90">
              Today's set: {(state.quizDeck.newLetters || []).length} new · {Object.keys(state.quizDeck.due || {}).length} in rotation · {state.quizDeck.reviewedToday || 0} reviewed
            </div>
          )}
          <div className="h-1 rounded-full bg-white/30 overflow-hidden mt-1.5" aria-hidden="true">
            <div className="h-full rounded-full bg-white transition-all" style={{ width: `${Math.max(0, Math.min(1, goldenSecs / goldenWindowSec())) * 100}%` }} />
          </div>
        </div>
      )}
      {/* Prophet's Choice — the decision after the claim */}
      {prophetPick && !prophetSnoozed && (
        <div role="dialog" aria-label="The Prophet offers — choose one blessing, or decide later"
          onKeyDown={(e) => { if (e.key === 'Escape') setProphetSnoozed(true) }}
          className="idle-pop fixed bottom-3 left-1/2 -translate-x-1/2 z-40 w-[min(94vw,32rem)] p-3 rounded-xl shadow-[0_0_36px_rgba(167,139,250,0.65)] ring-4 ring-violet-200 dark:ring-violet-700 bg-gradient-to-r from-violet-500 to-purple-600 text-white text-sm font-medium">
          <div className="mb-1.5 text-center"><b>🔮 The Prophet offers — take one blessing:</b></div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
            {prophetPick.options.map(id => {
              const b = PROPHET_BLESSINGS.find(x => x.id === id) || { name: id, desc: '', icon: '✨' }
              return (
                <button key={id} onClick={() => takeBlessing(id)}
                  aria-label={`Take blessing: ${b.name} — ${b.desc}`}
                  className="min-h-[52px] p-1.5 rounded-lg bg-white/15 hover:bg-white/25 active:scale-95 cursor-pointer text-center">
                  <div className="text-lg leading-none">{b.icon}</div>
                  <div className="text-xs font-bold">{b.name}</div>
                  <div className="text-[10px] opacity-90 leading-tight">{b.desc}</div>
                </button>
              )
            })}
          </div>
          <button onClick={() => setProphetSnoozed(true)}
            className="mt-1.5 w-full min-h-[44px] rounded-lg bg-white/15 hover:bg-white/25 text-xs font-medium cursor-pointer">
            Decide later — the Prophet waits
          </button>
        </div>
      )}
      {prophetPick && prophetSnoozed && (
        <button onClick={() => setProphetSnoozed(false)}
          className="fixed bottom-3 left-1/2 -translate-x-1/2 z-40 w-[min(94vw,32rem)] min-h-[44px] rounded-xl shadow-xl bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium cursor-pointer active:scale-[0.99]">
          🔮 The Prophet waits — choose your blessing
        </button>
      )}
      {/* Buy hints live in the overlay toast stack. */}



      {/* Garden tab — Root Garden minigame + grove timers, single scroll region */}
      {activeTab === 'garden' && (gardenOpen ? (
        <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
          <GardenPanel state={state} perSec={perSec} onUpdate={(next) => { commit(next); saveIdleState(next) }} />
          {/* Grove timers: fig + vineyard live in the Garden tab */}
          <div className="mt-2 rounded-xl bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700 px-2.5 py-2 space-y-2">
          {/* Fig — 20h timer */}
          <div className="flex items-center gap-2">
            <span className="text-lg">{figIsReady ? '🍯' : '🌱'}</span>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between text-[11px] text-neutral-500 dark:text-neutral-400">
                <span>Fig <b>lvl {figLevel}</b>{figLevel > 0 && <span> · +{figLevel * 10}% Ohr</span>}{figLevel >= FIG_MAX_LEVEL && <span> · max</span>}</span>
                <span className="tabular-nums">{figIsReady ? 'ripe!' : state.figs?.readyAt ? `${figWait} left` : 'planting…'}</span>
              </div>
              <div className="h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mt-0.5">
                <div className={`h-full rounded-full ${figIsReady ? 'bg-amber-500' : 'bg-lime-500'}`} style={{ width: `${figPct * 100}%` }} />
              </div>
            </div>
            <button onClick={harvest} disabled={!figIsReady} data-testid="fig-harvest"
              title={figIsReady ? 'Fig is ripe — harvest now' : `Fig ripening — ${figWait} left`}
              aria-label={figIsReady ? `Harvest ripe fig, grove level ${figLevel}` : `Fig not ready, ${figWait} remaining`}
              className={`shrink-0 min-h-[44px] px-3 rounded-lg text-xs font-semibold ${figIsReady ? 'idle-pop bg-amber-500 hover:bg-amber-600 text-white cursor-pointer active:scale-95' : 'border border-neutral-200 dark:border-neutral-700 text-neutral-400 opacity-60'}`}>
              Harvest
            </button>
          </div>
          {/* Vineyard — 4h tending loop, 3 parallel vines */}
          <div className="flex items-center gap-2">
            <span className="text-lg">🍇</span>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between text-[11px] text-neutral-500 dark:text-neutral-400">
                <span>Vineyard <b>lvl {vineLevel}</b>{vineLevel > 0 && <span> · +{vineLevel * 5}% Ohr</span>}{vineLevel >= VINE_MAX_LEVEL && <span> · max</span>}</span>
                <span className="tabular-nums">{vines.filter(v => v.ready).length}/{VINE_COUNT} ripe</span>
              </div>
              <div className="space-y-0.5 mt-0.5">
                {vines.map(v => (
                  <div key={v.i} className="flex items-center gap-1.5">
                    <div className="flex-1 h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                      <div className={`h-full rounded-full ${v.ready ? 'bg-purple-500' : 'bg-lime-500'}`} style={{ width: `${v.pct * 100}%` }} />
                    </div>
                    <button onClick={() => harvestVineAt(v.i)} disabled={!v.ready} data-testid={`vine-tend-${v.i}`}
                      title={v.ready ? `Vine ${v.i + 1} ripe — tend now` : state.vineyard?.vines?.[v.i] ? `Vine ${v.i + 1} ripening — ${v.wait} left` : `Vine ${v.i + 1} sowing…`}
                      aria-label={v.ready ? `Tend ripe vine ${v.i + 1}` : `Vine ${v.i + 1} not ready, ${v.wait} remaining`}
                      className={`shrink-0 min-h-[44px] px-2 rounded-md text-[11px] font-semibold ${v.ready ? 'idle-pop bg-purple-500 hover:bg-purple-600 text-white cursor-pointer active:scale-95' : 'border border-neutral-200 dark:border-neutral-700 text-neutral-400 opacity-60'}`}>
                      {v.ready ? 'Tend' : (state.vineyard?.vines?.[v.i] ? v.wait : 'sowing…')}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
          </div>
        </div>
      ) : (
        <LockedTeaser icon="🌱" name="Root Garden"
          blurb="Plant readable roots and cross-breed them for Kavod — your garden grows while you study."
          progress={`${totalOwned(state)}/${GARDEN_UNLOCK_OWNED} letters inscribed`}
          onGo={() => setActiveTab('letters')} />
      ))}

      {/* Watch tab — watchmen loadout minigame */}
      {activeTab === 'watch' && (
        <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
          <WatchmenPanel state={state} onUpdate={(next) => { commit(next); saveIdleState(next) }} />
        </div>
      )}

      {/* Shuk tab — market stalls minigame, gated to the first root (second-act reveal) */}
      {activeTab === 'shuk' && (shukOpen ? (
        <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
          <ShukPanel state={state} perSec={perSec} onUpdate={(next) => { commit(next); saveIdleState(next) }} />
        </div>
      ) : (
        <LockedTeaser icon="🧺" name="Shuk market"
          blurb="Trade oil, wine, and grain for production — and borrow light against tomorrow's earnings. The market opens its stalls to proven builders."
          progress="Unlocks at your first forged root 🌿"
          onGo={() => setActiveTab('letters')} />
      ))}

      {/* Letter shop — one tab of the single screen (6 cols on phones) */}
      {activeTab === 'letters' && (
        <div className="min-h-0 flex-1 overflow-y-auto">
          {/* Answer to earn — the core loop lives here, inside the game shell,
              never as a card sliding under the sticky workshop. */}
          {(nextLesson || dueCount > 0 || onBrowseLessons) && (
            <div className="mt-2 flex flex-wrap gap-2">
              {nextLesson && onOpenReview && (
                <button onClick={() => onOpenReview(nextLesson.id)} data-testid="practice-now"
                  className="flex-1 sm:flex-none min-h-[48px] px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer active:scale-[0.99]">
                  ⚡ Practice: {nextLesson.title}
                </button>
              )}
              {dueCount > 0 && onOpenReview && (
                <button onClick={() => onOpenReview('due')} data-testid="review-due"
                  className="flex-1 sm:flex-none min-h-[48px] px-4 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium cursor-pointer active:scale-[0.99]">
                  🔁 Review ({dueCount})
                </button>
              )}
              {onBrowseLessons && (
                <button onClick={onBrowseLessons}
                  className="min-h-[48px] px-4 rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 text-sm cursor-pointer active:scale-[0.99]">
                  📚 Lessons
                </button>
              )}
            </div>
          )}
          <div className="mt-2 flex items-center gap-1.5">
            <span className="text-[11px] text-neutral-500 dark:text-neutral-400">Buy:</span>
            {BULK_MODES.map(m => (
              <button key={m} onClick={() => setBulk(m)} aria-pressed={bulk === m} aria-label={`Buy amount: ${m === 'max' ? 'maximum affordable' : `${m} at a time`}`}
                className={`min-h-[44px] px-3 rounded-lg text-xs font-medium cursor-pointer ${bulk === m ? 'bg-amber-500 text-white' : 'border border-neutral-200 dark:border-neutral-700 text-neutral-500'}`}>
                {m === 'max' ? 'Max' : `x${m}`}
              </button>
            ))}
            <span className="flex-1" />
            <span className="text-[11px] text-neutral-500 tabular-nums">{totalOwned(state)} owned</span>
            {scribeCount(state) > 0 && (
              <button onClick={() => { const next = { ...state, autobuy: !state.autobuy }; setState(next); saveIdleState(next) }}
                aria-pressed={state.autobuy !== false} title="Scribes auto-buy one unit per tick for mastered letters"
                className={`min-h-[44px] px-3 rounded-lg text-xs font-medium cursor-pointer ${state.autobuy !== false ? 'bg-indigo-500 text-white' : 'border border-neutral-200 dark:border-neutral-700 text-neutral-500'}`}>
                📜 {state.autobuy !== false ? 'ON' : 'OFF'}
              </button>
            )}
          </div>
          {!scribeUnlocked(state) && (
            <div className="mt-1.5 text-[10px] text-neutral-400 dark:text-neutral-500">
              📜 Scribes unlock at your first forged root — mastered letters will inscribe themselves (learning itself is never automated).
            </div>
          )}
          <div className="mt-1.5 grid grid-cols-6 sm:grid-cols-11 gap-1.5">
            {LETTERS.map((L, i) => {
              const owned = state.owned[i] || 0
              const { n, spend } = buyAmount(i)
              const afford = n > 0 && state.ohr >= spend
              const m = mastery[i] || 0
              const locked = !exileAllows(state, i)
              const lockIcon = exileKind === 'shemittah' ? '🌾' : '⛓️'
              const scribed = !!state.scribes?.[i]
              const canHire = !scribed && scribeUnlocked(state) && m >= 0.8
              return (
                <div key={i} className="relative">
                <button onClick={() => buy(i)}
                  aria-label={`${locked ? 'Locked' : afford ? 'Buy' : 'Cannot afford'} ${L} (${LETTER_NAMES[i]}, "${LETTER_SYMBOLS[i]}", gematria ${GEMATRIA[i]}), owned ${owned}, costs ${spend} Ohr${owned > 0 ? `, earns ${fmtRate(letterRate(state, mastery, i, gramMult))}/s` : ''}`}
                  title={locked ? (exileKind === 'shemittah' ? '🌾 The land rests — no inscribing until the next root' : `⛓️ Beyond your vow — exile study is ${exileLetters.map(j => LETTERS[j]).join(' · ')}`) : `${L} ${LETTER_NAMES[i]} · "${LETTER_SYMBOLS[i]}" · gematria ${GEMATRIA[i]} · owned ${owned} · base ${baseCost(i)} · mastery ${Math.round(m * 100)}% · synergy ×${synergyMultiplier(state.owned, mastery, i).toFixed(2)}${owned > 0 ? ` · +${fmtRate(letterRate(state, mastery, i, gramMult))}/s` : ''}`}
                  className={`min-h-[64px] p-1.5 rounded-lg border text-center transition-colors cursor-pointer focus-visible:outline-2 focus-visible:outline-amber-500 ${locked ? 'bg-neutral-800 dark:bg-black border-neutral-700 opacity-50' : afford ? 'bg-white dark:bg-neutral-800 border-amber-300 dark:border-amber-700 shadow-[0_0_10px_rgba(245,158,11,0.35)] active:scale-95' : buyHint?.i === i ? 'bg-red-50 dark:bg-red-900/20 border-red-400 dark:border-red-600' : 'bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 opacity-70'}`}>
                  <div className="text-xl leading-none">{locked ? lockIcon : L}</div>
                  <div className="text-[10px] font-mono text-neutral-500 tabular-nums">
                    {owned > 0 && bulk === '1' ? `x${owned}` : spend >= 1e8 ? fmtBig(spend) : spend >= 1000 ? `${(spend / 1000).toFixed(1)}k${bulk !== '1' ? ` ×${bulk === 'max' ? n : bulk}` : ''}` : `${spend}${bulk !== '1' ? ` ×${bulk === 'max' ? n : bulk}` : ''}`}
                  </div>
                  <div className="text-[10px] font-mono text-amber-600 dark:text-amber-400 tabular-nums">
                    {owned > 0 ? `+${fmtRate(letterRate(state, mastery, i, gramMult))}/s` : `=${GEMATRIA[i]}`}
                  </div>
                  {m >= 0.8 && <div className="text-[10px] text-green-600" aria-hidden="true">●<span className="sr-only">mastered</span></div>}
                </button>
                {scribed && (
                  <span title="Scribed — buys itself when affordable" className="absolute top-0.5 right-0.5 text-[10px] pointer-events-none" aria-hidden="true">📜</span>
                )}
                {canHire && (
                  <button onClick={() => hire(i)}
                    aria-label={`Hire a scribe for ${L} — ${scribeCost(state)} Kavod. Mastered letters buy themselves.`}
                    title={`Hire scribe (${scribeCost(state)} 🌟): ${L} buys itself when affordable`}
                    className="absolute top-0 right-0 min-w-[28px] min-h-[28px] rounded-bl-lg rounded-tr-lg bg-indigo-500 hover:bg-indigo-600 text-white text-xs cursor-pointer active:scale-95">
                    📜
                  </button>
                )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Quests tab — the short-term loop + daily + achievements */}
      {activeTab === 'quests' && (
        <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
      {/* Next up — "what am I working toward" lives here, not on the main screen. */}
      <div className="grid gap-1.5 grid-cols-2">
        {goals.gen && (
          <div className="px-2.5 py-1.5 rounded-lg bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700">
            <div className="flex justify-between text-[10px] text-neutral-500 dark:text-neutral-400 mb-1">
              <span>Next: <b>{goals.gen.letter}</b> generator · {fmtBig(goals.gen.cost)} Ohr</span>
              <span className="tabular-nums">{Math.round(goals.gen.pct * 100)}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
              <div className="h-full rounded-full bg-amber-500 transition-all" style={{ width: `${goals.gen.pct * 100}%` }} />
            </div>
          </div>
        )}
        <div className="px-2.5 py-1.5 rounded-lg bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700">
          <div className="flex justify-between text-[10px] text-neutral-500 dark:text-neutral-400 mb-1">
            <span>Next: root <b>#{goals.root.next}</b> · {fmtBig(goals.root.need)} lifetime</span>
            <span className="tabular-nums">{Math.round(goals.root.pct * 100)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-teal-500 transition-all" style={{ width: `${goals.root.pct * 100}%` }} />
          </div>
        </div>
        {((state.roots || 0) > 0 || sparksTotal > 0) && (
          <div className="px-2.5 py-1.5 rounded-lg bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700 col-span-2">
            <div className="flex justify-between text-[10px] text-neutral-500 dark:text-neutral-400 mb-1">
              <span>Next: 💫 spark <b>#{sparkProg.next}</b> · {fmtBig(sparkProg.need)} lifetime Ohr</span>
              <span className="tabular-nums">{Math.round(sparkProg.pct * 100)}%{sparksTotal > 0 ? ` · ${sparksTotal} earned` : ''}</span>
            </div>
            <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
              <div className="h-full rounded-full bg-sky-400 transition-all" style={{ width: `${sparkProg.pct * 100}%` }} />
            </div>
          </div>
        )}
      </div>
      <div className="mt-2 rounded-lg bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700 overflow-hidden">
        <div
          className="w-full min-h-[44px] px-2.5 flex items-center gap-2 text-xs font-semibold text-neutral-600 dark:text-neutral-300">
          <span>📜 Quests</span>
          {unclaimedQuests > 0 && (
            <span className="idle-pop px-1.5 py-0.5 rounded-full bg-green-500 text-white text-[10px] font-bold">{unclaimedQuests} to claim!</span>
          )}
          <span className="flex-1" />
        </div>
          <div className="px-2.5 pb-2 space-y-1.5">
            {QUESTS.map(q => {
              const val = q.progress(state)
              const done = questComplete(state, q)
              const claimed = !!state.quests?.[q.id]
              const pct = Math.min(1, val / q.goal)
              return (
                <div key={q.id} className="flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex justify-between text-[11px] text-neutral-500 dark:text-neutral-400">
                      <span className={claimed ? 'line-through opacity-60' : ''}>{q.name} · {q.desc}</span>
                      <span className="tabular-nums shrink-0 ml-2">
                        {fmtBig(val)}/{fmtBig(q.goal)}
                      </span>
                    </div>
                    <div className="h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mt-0.5">
                      <div className={`h-full rounded-full transition-all ${claimed ? 'bg-green-500' : done ? 'bg-green-400' : 'bg-indigo-400'}`} style={{ width: `${pct * 100}%` }} />
                    </div>
                  </div>
                  {claimed ? (
                    <span className="text-green-600 text-sm shrink-0" aria-label={`Quest complete: ${q.name}`}>✓</span>
                  ) : done ? (
                    <button onClick={() => claimQuestReward(q.id)} aria-label={`Claim quest reward: ${q.name}, +${fmtBig(q.reward)} Ohr`}
                      className="idle-pop shrink-0 min-h-[44px] px-3 rounded-lg bg-green-500 hover:bg-green-600 text-white text-xs font-bold cursor-pointer">
                      +{fmtBig(q.reward)}
                    </button>
                  ) : null}
                </div>
              )
              })}
            </div>
      </div>
      {/* Daily + achievements join the Quests tab, same scroll region */}
      <div className="mt-2 rounded-xl bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700 px-2.5 py-2 space-y-2">
          {/* Daily lesson */}
          <div className="flex items-center gap-2">
            <span className="text-lg">📅</span>
            <div className="flex-1 min-w-0">
              <div className="flex justify-between text-[11px] text-neutral-500 dark:text-neutral-400">
                <span>Daily lesson · answer {DAILY_GOAL} correctly</span>
                <span className="tabular-nums">{dailyCount}/{DAILY_GOAL}{dailyClaimed ? ' · done ✓' : ''}</span>
              </div>
              <div className="h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden mt-0.5">
                <div className={`h-full rounded-full ${dailyClaimed ? 'bg-green-500' : 'bg-indigo-400'}`} style={{ width: `${(dailyCount / DAILY_GOAL) * 100}%` }} />
              </div>
            </div>
            <button onClick={claimDailyReward} disabled={!dailyOk} data-testid="daily-claim"
              title={dailyClaimed ? 'Daily claimed — come back tomorrow' : dailyOk ? 'Daily complete — claim your hour of Ohr' : `Daily lesson — ${DAILY_GOAL - dailyCount} correct answers to go`}
              aria-label={dailyClaimed ? 'Daily reward already claimed' : dailyOk ? 'Claim daily reward' : `Daily reward not ready, ${DAILY_GOAL - dailyCount} answers remaining`}
              className={`shrink-0 min-h-[44px] px-3 rounded-lg text-xs font-semibold ${dailyOk ? 'idle-pop bg-green-500 hover:bg-green-600 text-white cursor-pointer active:scale-95' : 'border border-neutral-200 dark:border-neutral-700 text-neutral-400 opacity-60'}`}>
              {dailyClaimed ? '✓' : 'Claim'}
            </button>
          </div>
          {/* Achievements → Shemen */}
          <div>
            <div className="flex justify-between text-[10px] text-neutral-500 dark:text-neutral-400 mb-0.5">
              <span>🏆 Achievements · each +4% Ohr (🫒 Shemen)</span>
              <span className="tabular-nums">{earnedAch.length}/{ACHIEVEMENTS.length}</span>
            </div>
            <div className="flex flex-wrap gap-1">
              {ACHIEVEMENTS.map(a => {
                const has = earnedAch.some(x => x.id === a.id)
                const concealed = !has && a.hidden
                return (
                  <span key={a.id} title={concealed ? 'A hidden deed — its terms are secret' : `${a.name} — ${a.desc}${has ? '' : ' (locked)'}`}
                    className={`text-sm ${has ? '' : 'opacity-30 grayscale'}`}>{concealed ? '❓' : a.icon}</span>
                )
              })}
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Grove + daily blocks now live inside their tab scrollers (single scroll region). */}

      {/* Upgrades tab — the choice axis. Letter ×2s (Ohr) + permanents (Kavod). */}
      {activeTab === 'upgrades' && (
      <div className="mt-2 min-h-0 flex-1 overflow-y-auto">
      <div className="rounded-lg bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700 overflow-hidden">
        <div
          className="w-full min-h-[44px] px-2.5 flex items-center gap-2 text-xs font-semibold text-neutral-600 dark:text-neutral-300">
          <span>⬆️ Upgrades</span>
          {(upgradeBadge.n > 0 || upgradeBadge.avail > 0) && (
            <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${upgradeBadge.n > 0 ? 'bg-green-500 text-white idle-pop' : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-500'}`}>
              {upgradeBadge.n > 0 ? `${upgradeBadge.n} to buy` : `${upgradeBadge.avail} locked`}
            </span>
          )}
          <span className="flex-1" />
        </div>
          <div className="px-2.5 pb-2.5 space-y-2.5">
            {/* Letter ×2 upgrades — appear only when a letter reaches its tier */}
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Letters · pay ✨ Ohr</div>
              {(() => {
                const rows = []
                LETTERS.forEach((L, i) => {
                  const owned = state.owned[i] || 0
                  availableLetterUpgrades(state, i).forEach(u => rows.push({ L, i, owned, ...u }))
                })
                if (rows.length === 0) {
                  return <p className="text-[11px] text-neutral-500 dark:text-neutral-400">
                    No letter upgrades yet — own <b>10</b> of a letter to unlock its first ×2.
                  </p>
                }
                return rows.map(r => {
                  const afford = state.ohr >= r.cost
                  const nowRate = letterRate(state, mastery, r.i, gramMult)
                  return (
                    <button key={r.id} onClick={() => {
                      const next = { ...state }
                      if (!buyLetterUpgrade(next, r.i, r.k)) {
                        setBoostFlash({ text: `Need ${fmtBig(r.cost - state.ohr)} more ✨ Ohr for ${r.L} ×2 — answer a question or let your golems mine.` })
                        setTimeout(() => setBoostFlash(null), 4000)
                        return
                      }
                      setState(next); saveIdleState(next)
                      try { logEvent('upgrade', { kind: 'letter', letter: r.i, tier: r.k, cost: r.cost }) } catch {}
                    }}
                      className={`w-full min-h-[44px] mb-1 px-2.5 rounded-lg border text-left cursor-pointer active:scale-[0.99] ${afford ? 'border-amber-400 dark:border-amber-600 bg-white dark:bg-neutral-800' : 'border-neutral-200 dark:border-neutral-700 opacity-60'}`}>
                      <div className="flex justify-between text-[11px]">
                        <span className="font-medium text-neutral-700 dark:text-neutral-200">
                          {r.L} ×2 output <span className="text-neutral-400">· owns {r.owned}</span>
                        </span>
                        <span className="tabular-nums text-neutral-500">{fmtBig(r.cost)} ✨</span>
                      </div>
                      <div className="text-[10px] tabular-nums text-amber-600 dark:text-amber-400">
                        Effect: +{fmtRate(nowRate)}/s → +{fmtRate(nowRate * 2)}/s
                      </div>
                    </button>
                  )
                })
              })()}
            </div>

            {/* Kavod permanents — learning buys permanent power */}
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">
                Permanents · pay 🌟 Kavod (you have {Math.floor(state.kavod || 0)})
              </div>
              {KAVOD_UPGRADES.map(u => {
                const ownedP = hasPerm(state, u.id)
                const afford = (state.kavod || 0) >= u.cost
                return (
                  <button key={u.id} disabled={ownedP} onClick={() => {
                    const next = { ...state }
                    if (!buyPerm(next, u.id)) {
                      setBoostFlash({ text: `Need ${fmtBig(u.cost - (state.kavod || 0))} more 🌟 Kavod for ${u.name} — Kavod comes only from correct answers.` })
                      setTimeout(() => setBoostFlash(null), 4000)
                      return
                    }
                    setState(next); saveIdleState(next)
                    try { logEvent('upgrade', { kind: 'perm', id: u.id, cost: u.cost }) } catch {}
                  }}
                    className={`w-full min-h-[48px] mb-1 px-2.5 rounded-lg border text-left ${ownedP ? 'border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-900/20 cursor-default' : afford ? 'border-indigo-300 dark:border-indigo-700 bg-white dark:bg-neutral-800 cursor-pointer active:scale-[0.99]' : 'border-neutral-200 dark:border-neutral-700 opacity-60 cursor-pointer'}`}>
                    <div className="flex justify-between items-center text-[11px]">
                      <span className="font-medium text-neutral-700 dark:text-neutral-200">
                        {u.icon} {u.name} {ownedP && <span className="text-green-600">✓</span>}
                      </span>
                      <span className={`tabular-nums ${ownedP ? 'text-green-600' : 'text-indigo-500'}`}>
                        {ownedP ? 'owned' : `${u.cost} 🌟`}
                      </span>
                    </div>
                    <div className="text-[10px] text-neutral-500 dark:text-neutral-400">{u.desc}</div>
                  </button>
                )
              })}
            </div>

            {/* Heavenly chain — Aliyah sparks, one way per tier */}
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">
                The Ascent · pay 💫 sparks ({sparks} available{sparksTotal > 0 ? ` · ${sparksTotal} earned` : ''})
              </div>
              <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mb-1">
                Six stations, two ways up each — choosing one seals the other, forever. Unspent sparks give +1% Ohr each, so buying trades bonus for permanence.
              </p>
              {HEAVENLY_TIERS.map(t => {
                const pair = HEAVENLY_UPGRADES.filter(u => u.tier === t)
                const done = heavenlyTierOwned(state, t)
                const open = t === 0 || heavenlyTierOwned(state, t - 1)
                return (
                  <div key={t} className="mb-1">
                    <div className="text-[10px] uppercase tracking-wider text-neutral-500 mb-0.5">Station {t + 1}</div>
                    <div className="grid grid-cols-2 gap-1">
                      {pair.map(u => {
                        const ownedH = heavenlyOwned(state, u.id)
                        const foregone = done && !ownedH
                        const afford = open && !done && sparks >= u.cost
                        return (
                          <button key={u.id} disabled={ownedH || foregone} onClick={() => buyHeaven(u.id)}
                            title={foregone ? `${u.name} — foregone: you ascended the other way` : u.desc}
                            className={`min-h-[48px] px-2 rounded-lg border text-left ${ownedH ? 'border-green-300 dark:border-green-800 bg-green-50 dark:bg-green-900/20 cursor-default' : foregone ? 'border-neutral-200 dark:border-neutral-700 opacity-40 cursor-default' : afford ? 'border-sky-300 dark:border-sky-700 bg-white dark:bg-neutral-800 cursor-pointer active:scale-[0.99]' : 'border-neutral-200 dark:border-neutral-700 opacity-60 cursor-pointer'}`}>
                            <div className="flex justify-between items-center text-[11px]">
                              <span className="font-medium text-neutral-700 dark:text-neutral-200">
                                {foregone ? '✕' : u.icon} {u.name} {ownedH ? <span className="text-green-600">✓</span> : (!open && <span className="text-neutral-400">🔒</span>)}
                              </span>
                              <span className={`tabular-nums ${ownedH ? 'text-green-600' : 'text-sky-500'}`}>
                                {ownedH ? 'owned' : `${u.cost} 💫`}
                              </span>
                            </div>
                            <div className="text-[10px] text-neutral-500 dark:text-neutral-400">{foregone ? 'Foregone — the other way was chosen' : u.desc}</div>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
      </div>
      </div>
      )}
      {/* Bottom tab bar — thumb-first section switching (iPhone pattern).
          Sticky within the one-screen shell; safe-area padded. */}
      <div className="mt-2 -mx-1 px-1 pt-1.5 shrink-0 border-t border-amber-200 dark:border-amber-800 bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/20" style={{ paddingBottom: 'max(0.25rem, env(safe-area-inset-bottom))' }}>
      <div className="grid grid-cols-7 gap-1" role="tablist" aria-label="Workshop sections">
        {IDLE_TABS.map(t => {
          const badge = t === 'quests' && unclaimedQuests > 0 ? unclaimedQuests
            : t === 'upgrades' && upgradeBadge.n > 0 ? upgradeBadge.n
            : null
          const dot = t === 'garden' && gardenOpen && gardenRipe > 0
          // Locked tabs stay visible but greyed with the unlock condition —
          // tapping one shows its teaser, never a dead end.
          const locked = (t === 'garden' && !gardenOpen) || (t === 'shuk' && !shukOpen)
          const lockHint = t === 'garden' && locked ? `Root Garden unlocks at ${GARDEN_UNLOCK_OWNED} letters or your first root (${totalOwned(state)}/${GARDEN_UNLOCK_OWNED})`
            : t === 'shuk' && locked ? 'Shuk market unlocks at your first forged root'
            : null
          return (
            <button key={t} role="tab" aria-selected={activeTab === t} onClick={() => setActiveTab(t)}
              title={lockHint || TAB_META[t].label}
              className={`relative min-h-[48px] rounded-lg text-[10px] font-semibold cursor-pointer transition-colors ${activeTab === t ? 'bg-amber-500 text-white' : locked ? 'bg-neutral-100 dark:bg-neutral-900 border border-dashed border-neutral-300 dark:border-neutral-700 text-neutral-400 dark:text-neutral-500' : 'bg-white/70 dark:bg-neutral-800/70 border border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300'}`}>
              <div className="text-base leading-none">{TAB_META[t].icon}</div>
              <div className="text-[9px] leading-tight truncate">{TAB_META[t].label}</div>
              {locked && <span className="absolute top-0.5 left-0.5 text-[9px]" aria-hidden="true">🔒</span>}
              {badge != null && (
                <span className="absolute top-0.5 right-0.5 px-1.5 py-px rounded-full bg-green-500 text-white text-[9px] font-bold">{badge}</span>
              )}
              {dot && <span className="absolute top-1 right-1 w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />}
            </button>
          )
        })}
      </div>
      </div>
      {/* Feast info modal — meaning, scriptures, vocab, live effect. */}
      {showFeast && (
        <FeastModal feast={showFeast.feast} daysUntil={showFeast.daysUntil} onClose={() => setShowFeast(null)} />
      )}
      {/* Overlay toast stack — transient flashes float top-center, never in-flow. */}
      {toasts.length > 0 && (
        <div className="fixed top-3 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-1.5 items-center pointer-events-none w-[min(94vw,32rem)]" aria-live="polite">
          {toasts.map(t => (
            <div key={t.id} className={`idle-pop w-full p-2 rounded-xl shadow-xl text-white text-sm text-center font-medium ${t.cls}`}>
              {t.text}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
