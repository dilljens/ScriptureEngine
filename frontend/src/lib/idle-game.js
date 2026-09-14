/**
 * idle-game.js — Aleph to Revelation balance formulas (trial).
 *
 * Pure functions, no React, no fetch. Tuned from:
 * Cookie Clicker (1.15 cost law), AdCap Angels (sqrt prestige, +2%),
 * Realm Grinder RE (+10%), Revolution Idle (promotion table), Melvor (offline cap).
 *
 * All state persists to localStorage under 'hebrew-idle-v1' for the trial.
 * Backend migration (hebrew_idle table) comes after balance is proven.
 */

export const LETTERS = [
  'א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י',
  'כ', 'ל', 'מ', 'נ', 'ס', 'ע', 'פ', 'צ', 'ק', 'ר', 'ש', 'ת',
]

/** Seed Ohr so a brand-new or freshly-prestiged workshop can always buy a first letter. */
export const STARTING_OHR = 50

export const PROMOTION_TRACKS = [  { id: 'dikduk', name: 'Dikduk Gain', desc: '+15% tap value / level', perLevel: 0.15 },
  { id: 'reading', name: 'Reading Speed', desc: '+10% Ohr/sec / level', perLevel: 0.10 },
  { id: 'niqqud', name: 'Niqqud Power', desc: '+2% crit chance / level (cap +10%)', perLevel: 0.02 },
  { id: 'chochmah', name: 'Chochmah Power', desc: '+25% offline earnings / level', perLevel: 0.25 },
]

/** Revolution-style promotion exp table: 1,3,7,15,31… */
export function promotionExpCost(level) {
  return Math.pow(2, level + 1) - 1
}

/** Base cost for letter generator i (0=Aleph). Aleph 10 … Tav ~230k. */
export function baseCost(i) {
  return Math.floor(10 * Math.pow(4.2, i / 3))
}

/** Cost of next generator given owned count. Cookie 1.15 law × difficulty. */
export function generatorCost(i, owned, diff = null) {
  const { costMult } = difficultyScalars(diff || {})
  return Math.max(1, Math.ceil(baseCost(i) * Math.pow(1.15, owned) * costMult))
}

/** Base Ohr/sec per generator. Aleph 0.2/s … Tav ~80/s. */
export function baseRate(i) {
  return 0.2 * Math.pow(1.35, i)
}

// ── Letter synergy: breadth beats spam ───────────────────────────────
// DESIGN.md: "leaders must shift over time (no permanently dominant letter) —
// use mastery multipliers and synergy so studying a *new* letter beats spamming
// a maxed one." Every letter you own lifts the others; every letter you MASTER
// lifts them more. Capped so depth (×2 tiers) still matters.

export const SYNERGY_OWNED = 0.02     // +2% per other letter owned
export const SYNERGY_MASTERED = 0.04  // +4% more per other letter mastered
export const SYNERGY_CAP = 1.0        // ceiling: +100%, workshop-wide
export const MASTERY_THRESHOLD = 0.8  // curriculum's own mastery/unlock bar

/** Workshop-wide synergy multiplier for letter i (counts every letter but i). */
export function synergyMultiplier(owned = {}, mastery = {}, i = 0) {
  let others = 0
  let mastered = 0
  for (let j = 0; j < LETTERS.length; j++) {
    if (j === i || !(owned[j] > 0)) continue
    others++
    if ((mastery[j] ?? 0) >= MASTERY_THRESHOLD) mastered++
  }
  return 1 + Math.min(others * SYNERGY_OWNED + mastered * SYNERGY_MASTERED, SYNERGY_CAP)
}

/**
 * Breadth bonus for the whole workshop, counting every owned letter — the single
 * number the HUD shows. Within one letter's worth of any individual letter's
 * multiplier (which excludes itself), so it reads as the honest "breadth" stat.
 */
export function workshopSynergy(owned = {}, mastery = {}) {
  return synergyMultiplier(owned, mastery, -1)
}

/**
 * Total Ohr/sec.
 * mastery: {letterIndex: 0..1} from curriculum; unstudied = 0.5x, never 0.
 * letterUpgrades: {`u${i}:${k}`: true} — ×2 tiers.
 * perm: {upgradeId: true} — permanent Kavod + heavenly upgrades.
 * sparks: unspent Aliyah sparks — +1% global each.
 */
export function perSecond(owned, mastery = {}, tracks = {}, words = 0, roots = 0, letterUpgrades = {}, perm = {}, sparks = 0) {
  const readingMult = 1 + (tracks.reading || 0) * 0.10
  const global = globalMultiplier(roots, words, tracks) * (1 + permEffect(perm, 'globalMult'))
  let sum = 0
  for (let i = 0; i < LETTERS.length; i++) {
    const n = owned[i] || 0
    if (!n) continue
    const m = mastery[i] ?? 0
    sum += baseRate(i) * n * (0.5 + m) * letterMultiplier(letterUpgrades, i) * synergyMultiplier(owned, mastery, i)
  }
  return sum * readingMult * global * sparkBonus(sparks)
}

/** Compose perSecond straight from game state (keeps call sites honest). */
export function statePerSecond(state, mastery = {}) {
  return perSecond(
    state.owned || {}, mastery, state.tracks || {}, state.words || 0, state.roots || 0,
    state.letterUpgrades || {}, state.perm || {}, availableSparks(state),
  ) * figMultiplier(state.figs) * vineyardMultiplier(state.vineyard) * shemenMultiplier(state)
}

export function globalMultiplier(roots = 0, words = 0, tracks = {}) {
  // Roots +10% each (Realm RE), words +2% each (AdCap Angels).
  // Reading track intentionally excluded here (applied in perSecond) to avoid double-count.
  void tracks
  return (1 + roots * 0.10) * (1 + words * 0.02)
}

/** Tap value for one correct answer (× difficulty, × permanent upgrades, × tap buff). */
export function tapValue(perSec, streak = 0, tracks = {}, diff = null, perm = {}, tapBuff = 1) {
  const { tapMult } = difficultyScalars(diff || {})
  const dikdukMult = 1 + (tracks.dikduk || 0) * 0.15
  const streakBonus = 1 + Math.min(streak, 100) * 0.01
  return (1 + 0.05 * perSec) * streakBonus * dikdukMult * tapMult * (1 + permEffect(perm, 'tapMult')) * tapBuff
}

/** Crit chance: 2% base + Niqqud + permanents, cap 20%. Crit = x7. */
export function critChance(tracks = {}, perm = {}) {
  return Math.min(0.02 + (tracks.niqqud || 0) * 0.02 + permEffect(perm, 'critAdd'), 0.2)
}

export function rollTap(perSec, streak, tracks = {}, rng = Math.random, diff = null, perm = {}, tapBuff = 1) {
  const crit = rng() < critChance(tracks, perm)
  return { value: tapValue(perSec, streak, tracks, diff, perm, tapBuff) * (crit ? 7 : 1), crit }
}

/** Roots earned from lifetime Ohr. First root ≈ 111k. */
export function rootsEarned(lifetimeOhr) {
  return Math.floor(3 * Math.sqrt(lifetimeOhr / 1e6))
}

/** Offline earnings. cap 12h → 24h after 10 roots. */
export function offlineEarnings(perSecAtDisconnect, elapsedSec, tracks = {}, roots = 0, perm = {}) {
  const cap = roots >= 10 ? 24 * 3600 : 12 * 3600
  const eff = Math.min(0.5 * (1 + (tracks.chochmah || 0) * 0.25) + permEffect(perm, 'offlineAdd'), 1)
  return perSecAtDisconnect * Math.min(elapsedSec, cap) * eff
}

/** Should-prestige hint: true when roots would at least double. */
export function shouldPrestige(lifetimeOhr, currentRoots) {
  return rootsEarned(lifetimeOhr) >= Math.max(2, currentRoots * 2)
}

// ── Adaptive difficulty ──────────────────────────────────────────────
// Two inputs, one knob:
//   1. Explicit feedback: player taps Too easy / Just right / Too hard.
//   2. Implicit signal: rolling accuracy + response time auto-drift.
// The knob (bias ∈ [-1, 1], + = harder) scales ONLY economy pacing
// (costs, taps, timers) — never mastery thresholds. Learning stays honest.

export function defaultDifficulty() {
  return { bias: 0, recent: [] } // recent: [{correct: bool, ms: number}]
}

function clampBias(b) {
  return Math.max(-1, Math.min(1, b))
}

/** Explicit feedback: 'easier' | 'harder' | 'just-right'. */
export function applyFeedback(diff, kind) {
  const d = { bias: diff.bias || 0, recent: diff.recent || [] }
  if (kind === 'easier') d.bias = clampBias(d.bias - 0.25)
  else if (kind === 'harder') d.bias = clampBias(d.bias + 0.25)
  else d.bias = clampBias(d.bias * 0.5) // just-right: decay toward neutral
  return d
}

/**
 * Implicit adaptation: call on every graded answer.
 * Target band 70–90% accuracy over last 20. Above → harden slowly,
 * below → ease faster (frustration costs more than boredom).
 * Very fast correct (<2s) hardens a touch; very slow wrong (>20s) eases.
 */
export function recordAttempt(diff, correct, responseMs) {
  const recent = [...(diff.recent || []), { correct: !!correct, ms: responseMs || 0 }].slice(-50)
  let bias = diff.bias || 0
  const window = recent.slice(-20)
  if (window.length >= 10) {
    const acc = window.filter(r => r.correct).length / window.length
    if (acc > 0.9) bias = clampBias(bias + 0.05)
    else if (acc < 0.6) bias = clampBias(bias - 0.1)
    else if (acc >= 0.7 && acc <= 0.9) bias = clampBias(bias * 0.95)
  }
  if (correct && (responseMs || 0) < 2000) bias = clampBias(bias + 0.01)
  if (!correct && (responseMs || 0) > 20000) bias = clampBias(bias - 0.02)
  return { bias, recent }
}

/** Economy scalars from bias. Mastery thresholds untouched. */
export function difficultyScalars(diff) {
  const b = clampBias(diff?.bias || 0)
  return {
    bias: b,
    costMult: 1 + 0.3 * b,   // harder → pricier generators
    tapMult: 1 - 0.25 * b,   // harder → smaller taps
    timeMult: 1 - 0.3 * b,   // harder → tighter quiz timers
    label: b <= -0.5 ? 'Gentle' : b <= -0.15 ? 'Eased' : b < 0.15 ? 'Standard' : b < 0.5 ? 'Spicy' : 'Fierce',
  }
}

/** Recent accuracy over last 20 attempts (null when too few). */
export function recentAccuracy(diff) {
  const w = (diff?.recent || []).slice(-20)
  if (w.length < 5) return null
  return w.filter(r => r.correct).length / w.length
}

const STORAGE_KEY = 'hebrew-idle-v1'

export function defaultIdleState() {
  return {
    ohr: 0,
    lifetimeOhr: 0,
    owned: {},       // letterIndex -> count
    roots: 0,
    words: 0,        // mastered word count (synced from curriculum)
    tracks: {},      // trackId -> level
    streak: 0,
    bestStreak: 0,
    streakGraceDay: '', // last day grace halved (not reset) a 10+ streak
    taps: 0,
    crits: 0,
    prestiges: 0,
    exilesCompleted: 0, // finished vow runs (exile or shemittah)
    lastVowPrestige: 0, // prestige count when the current/past vow started (sim pacing)
    exile: null,        // active vow {letters:[i,j,k], startedAt} or null
    lastSeen: Date.now(),
    muted: false,
    difficulty: defaultDifficulty(),
    correct: 0,        // lifetime correct answers (quest + loop stats)
    kavod: 0,          // 🌟 learning currency: earned ONLY by correct answers, buys speed
    warps: 0,          // time warps purchased (escalates cost)
    buffs: { frenzyEndsAt: 0, galeEndsAt: 0, tapEndsAt: 0 },
    golden: null,        // active Golden Prompt {id, expiresAt}, null when none
    nextGoldenAt: 0,     // timestamp the next prompt may spawn
    figs: { level: 0, readyAt: 0 }, // 20h retention timer (sugar-lump analogue)
    vineyard: { level: 0, vines: [0, 0, 0] }, // 3 parallel 4h tending timers (garden analogue)
    daily: { day: '', correct: 0, claimed: false }, // 10-correct daily lesson
    letterUpgrades: {}, // `u${letter}:${tier}` -> true (×2 tiers)
    perm: {},           // permanent Kavod upgrades -> true
    quests: {},        // questId -> true when claimed
    milestones: {},    // streak milestone -> true when awarded
    pendingOffline: 0, // unclaimed offline Ohr (tap-to-claim)
  }
}

export function loadIdleState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      const s = defaultIdleState()
      s.ohr = STARTING_OHR
      s.lifetimeOhr = STARTING_OHR
      return s
    }
    const s = { ...defaultIdleState(), ...JSON.parse(raw) }
    // Onboarding rescue: a player with no golems and no Ohr can never start
    // (every letter is unaffordable). Top them up instead of dead-ending them.
    if (totalOwned(s) === 0 && (s.ohr || 0) < 10) {
      s.ohr = STARTING_OHR
      s.lifetimeOhr = Math.max(s.lifetimeOhr || 0, STARTING_OHR)
    }
    // Vow backfill: saves from before vows carried expiry get one from load.
    if (s.exile && !s.exile.endsAt) s.exile = { ...s.exile, endsAt: Date.now() + VOW_MAX_HOURS * 3600 * 1000 }
    return s
  } catch {
    return defaultIdleState()
  }
}

export function saveIdleState(s) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...s, lastSeen: Date.now() }))
  } catch {}
}

/** Apply one correct answer: tap + streak + Kavod. Returns {gained, crit, kavod}. */
export function applyCorrectAnswer(state, perSec, rng = Math.random) {
  const streak = (state.streak || 0) + 1
  const { value: raw, crit } = rollTap(perSec, streak, state.tracks, rng, state.difficulty, state.perm, tapBuffMultiplier(state))
  // Shemittah sprint: every tap counts double. Exile: Kavod doubles instead.
  const value = raw * shemittahTapMult(state)
  // Kavod — the learning currency: 1 base, +1 per 5 streak, +3 on crit.
  // This is the ONLY way to buy speed. No money, no waiting shortcut.
  // Exile runs pay double: fewer letters to study, faster Kavod, harder breadth.
  let kavod = 1 + Math.floor(streak / 5) + (crit ? 3 : 0)
  if (state.exile?.kind === 'exile') kavod = Math.round(kavod * EXILE_KAVOD_MULT)
  state.kavod = (state.kavod || 0) + kavod
  state.streak = streak
  state.bestStreak = Math.max(state.bestStreak || 0, streak)
  state.taps = (state.taps || 0) + 1
  state.correct = (state.correct || 0) + 1
  if (crit) state.crits = (state.crits || 0) + 1
  state.ohr += value
  state.lifetimeOhr = (state.lifetimeOhr || 0) + value
  return { gained: value, crit, streak, kavod }
}

/**
 * Apply a wrong answer. Streaks break — but once a day, a streak of 10+
 * bends instead: grace keeps half (Duolingo-freeze analogue). Milestones are
 * one-time bursts, so nothing earned is ever lost; only the live streak dips.
 * Returns {graced} so the HUD can say what happened.
 */
export function applyWrongAnswer(state, now = Date.now()) {
  const streak = state.streak || 0
  if (streak >= 10 && (state.streakGraceDay || '') !== dayKey(now)) {
    state.streak = Math.floor(streak / 2)
    state.streakGraceDay = dayKey(now)
    return { graced: true }
  }
  state.streak = 0
  return { graced: false }
}

/** Prestige: reset Ohr + generators, keep roots/words/tracks. Returns roots gained. */
export function applyPrestige(state) {
  const target = rootsEarned(state.lifetimeOhr || 0)
  const gained = Math.max(0, target - (state.roots || 0))
  if (gained <= 0) return 0
  // Coming home from exile counts: the run is complete, the vow released.
  if (state.exile) {
    state.exilesCompleted = (state.exilesCompleted || 0) + 1
    state.exile = null
  }
  state.roots = target
  state.ohr = STARTING_OHR
  state.owned = {}
  // 'Remembered Words' permanent: keep a head-start on your first letter.
  const seed = permEffect(state.perm || {}, 'seedLetter')
  if (seed > 0) state.owned = { 0: seed }
  state.streak = 0
  state.prestiges = (state.prestiges || 0) + 1
  return gained
}

// ── Vow runs: the prestige variants (challenge, not punishment) ───
// Realm Grinder's lesson: prestige must change HOW you play, not just the
// numbers. Two covenants, same seam (state.exile = {kind, ...}):
//   exile:     vowed any time once the meta layer opens — lock NEW study to
//              Aleph + 2 random letters until the next root (production keeps
//              running), and earn double Kavod while the vow holds.
//   shemittah: vowed any time once the meta layer opens — the rest HOUR.
//              Inscribe nothing for one hour (production keeps running), every
//              tap counts double, then the run completes. A sprint, never a
//              freeze: a buying freeze during compounding costs 20x (measured),
//              so shemittah is fixed-duration by design.
// Ending early is always allowed (prestige out); completing one counts toward
// the Covenant Keeper achievement. Vows open with the first heavenly upgrade —
// endgame spice for committed students, not early detours.

export const EXILE_KAVOD_MULT = 2.0
export const EXILE_LETTERS = 3
export const SHEMITTAH_TAP_MULT = 2.0
export const SHEMITTAH_HOURS = 1
export const VOW_MAX_HOURS = 24 // backstop: a vow that cannot complete in a day releases uncounted (fizzle, not trap)

/** Take the vow of exile: lock to `letters` until the next prestige. Returns true if vowed. */
export function startExile(state, letters, now = Date.now()) {
  const set = [...new Set(letters)].filter(i => i >= 0 && i < LETTERS.length)
  if (set.length !== EXILE_LETTERS || state.exile) return false
  state.exile = { kind: 'exile', letters: set.sort((a, b) => a - b), startedAt: now, endsAt: now + VOW_MAX_HOURS * 3600 * 1000 }
  state.lastVowPrestige = state.prestiges || 0
  return true
}

/** Take the shemittah vow any time: inscribe nothing for one hour. Returns true if vowed. */
export function startShemittah(state, now = Date.now()) {
  if (state.exile) return false
  state.exile = { kind: 'shemittah', startedAt: now, endsAt: now + SHEMITTAH_HOURS * 3600 * 1000 }
  state.lastVowPrestige = state.prestiges || 0
  return true
}

/**
 * Complete a rested shemittah: the hour elapsed, so the run counts.
 * (Prestiging out mid-hour also counts, via applyPrestige.) Returns true on completion.
 */
export function checkShemittah(state, now = Date.now()) {
  if (state.exile?.kind !== 'shemittah') return false
  if (now < (state.exile.endsAt || 0)) return false
  state.exile = null
  state.exilesCompleted = (state.exilesCompleted || 0) + 1
  return true
}

/**
 * Release an expired vow. A vow that cannot complete within 24h releases
 * UNCOUNTED — the fizzle rule applied to vows. Returns true if released.
 */
export function vowReleased(state, now = Date.now()) {
  if (!state.exile) return false
  if (now <= (state.exile.endsAt || Infinity)) return false
  state.exile = null
  return true
}

/** Sample the vow: Aleph (so the run is never dead) + 2 random others. */
export function rollExileLetters(rng = Math.random) {
  const pool = LETTERS.map((_, i) => i).slice(1)
  const out = [0]
  while (out.length < EXILE_LETTERS && pool.length) {
    out.push(pool.splice(Math.floor(rng() * pool.length), 1)[0])
  }
  return out.sort((a, b) => a - b)
}

/** A letter is buyable when no vow holds; exile allows its three; shemittah allows none. */
export function exileAllows(state, i) {
  if (!state.exile) return true
  if (state.exile.kind === 'shemittah') return false
  return (state.exile.letters || []).includes(i)
}

/** Tap multiplier while the shemittah vow holds (the sprint payoff). */
export function shemittahTapMult(state) {
  return state.exile?.kind === 'shemittah' ? SHEMITTAH_TAP_MULT : 1
}

// ── Gameplay loop: bulk-buy, quests, streak milestones, next goals ────

/** Total generators owned across all letters. */
export function totalOwned(state) {
  return Object.values(state.owned || {}).reduce((a, b) => a + (b || 0), 0)
}

/** Cost to buy n generators at once (loop; n is small). */
export function bulkCost(i, owned, n, diff = null) {
  let t = 0
  for (let k = 0; k < n; k++) t += generatorCost(i, owned + k, diff)
  return t
}

/** Max affordable count + total spend (cap 1000 iterations). */
export function maxBuyable(i, owned, ohr, diff = null) {
  let n = 0
  let spend = 0
  while (n < 1000) {
    const c = generatorCost(i, owned + n, diff)
    if (spend + c > ohr) break
    spend += c
    n++
  }
  return { n, spend }
}

/** Lifetime Ohr needed to reach r roots (inverse of rootsEarned). */
export function lifetimeForRoots(r) {
  return Math.pow(r / 3, 2) * 1e6
}

/**
 * Quests: short-term goals answering "what do I do next?".
 * progress(state) -> current value; goal -> target; complete when >= goal.
 */
export const QUESTS = [
  { id: 'buy1', name: 'Light the first lamp', desc: 'Own 1 letter generator', goal: 1, reward: 25, progress: s => totalOwned(s) },
  { id: 'correct3', name: 'Warming up', desc: 'Answer 3 correctly', goal: 3, reward: 50, progress: s => s.correct || 0 },
  { id: 'streak5', name: 'On a roll', desc: 'Reach a 5 streak', goal: 5, reward: 75, progress: s => s.bestStreak || 0 },
  { id: 'earn1k', name: 'Kindling', desc: 'Earn 1,000 lifetime Ohr', goal: 1000, reward: 150, progress: s => s.lifetimeOhr || 0 },
  { id: 'own10', name: 'Choir', desc: 'Own 10 generators', goal: 10, reward: 300, progress: s => totalOwned(s) },
  { id: 'streak25', name: 'Unstoppable', desc: 'Reach a 25 streak', goal: 25, reward: 500, progress: s => s.bestStreak || 0 },
  { id: 'root1', name: 'First fruits', desc: 'Forge your first root', goal: 1, reward: 1000, progress: s => s.roots || 0 },
  { id: 'earn100k', name: 'Blaze', desc: 'Earn 100,000 lifetime Ohr', goal: 100000, reward: 2000, progress: s => s.lifetimeOhr || 0 },
]

export function questComplete(state, q) {
  return q.progress(state) >= q.goal
}

/** Claim a completed quest. Returns reward (0 if not claimable). */
export function claimQuest(state, id) {
  const q = QUESTS.find(x => x.id === id)
  if (!q || (state.quests || {})[id] || !questComplete(state, q)) return 0
  state.quests = { ...(state.quests || {}), [id]: true }
  state.ohr += q.reward
  state.lifetimeOhr = (state.lifetimeOhr || 0) + q.reward
  return q.reward
}

/** Streak milestones: one-time Ohr bursts. Returns bonus (0 if already awarded). */
export const STREAK_MILESTONES = [5, 10, 25, 50, 100]

export function checkStreakMilestone(state) {
  for (const m of STREAK_MILESTONES) {
    if ((state.streak || 0) >= m && !(state.milestones || {})[m]) {
      state.milestones = { ...(state.milestones || {}), [m]: true }
      const bonus = 25 * m
      state.ohr += bonus
      state.lifetimeOhr = (state.lifetimeOhr || 0) + bonus
      return { milestone: m, bonus }
    }
  }
  return null
}

/**
 * Next goals: cheapest generator + next root, each with % progress.
 * The HUD always answers "what am I working toward right now?".
 */
export function nextGoals(state, diff = null) {
  let gen = null
  for (let i = 0; i < LETTERS.length; i++) {
    if (!exileAllows(state, i)) continue // never point at a locked letter
    const cost = generatorCost(i, (state.owned || {})[i] || 0, diff)
    if (!gen || cost < gen.cost) gen = { letter: LETTERS[i], index: i, cost }
  }
  const roots = state.roots || 0
  const need = lifetimeForRoots(roots + 1)
  const have = state.lifetimeOhr || 0
  return {
    gen: gen ? { ...gen, pct: Math.min(1, (state.ohr || 0) / gen.cost) } : null,
    root: { next: roots + 1, need, pct: Math.min(1, have / need) },
  }
}

// ── Learning-as-currency: boosts bought with Kavod, never money ─────
// Everything idle games usually sell (frenzy multipliers, time warps) is
// bought with 🌟 Kavod, which is earned ONLY by correct answers.

export const FRENZY_COST = 20
export const FRENZY_MULT = 3
export const FRENZY_SECONDS = 60

/** Time Warp cost escalates per purchase: 30, 90, 270, … */
export function warpCost(state) {
  return 30 * Math.pow(3, state.warps || 0)
}

/** Current buff multiplier. Same-kind buffs don't stack — take the strongest. */
export function buffMultiplier(state, now = Date.now()) {
  const frenzy = (state.buffs?.frenzyEndsAt || 0) > now ? FRENZY_MULT : 1
  return Math.max(frenzy, galeMultiplier(state, now))
}

// ── Golden Prompts: quiz-gated buffs, accuracy windows, never reflex ──
// Cookie's golden cookie, but claimed by answering correctly within a window
// instead of clicking fast (DESIGN.md: no reflex gates). Wrong or late FIZZLES —
// nothing is ever drained (punishment ban).

export const GOLDEN_WINDOW_SEC = 20
export const GOLDEN_INTERVAL_SEC = [60, 180]

export const GOLDEN_PROMPTS = [
  { id: 'gale', name: 'Ruach Gale', icon: '🌪️', kind: 'mult', mult: 7, seconds: 77, weight: 3, desc: 'x7 Ohr for 77s' },
  { id: 'dew', name: 'Dew of Light', icon: '💧', kind: 'hours', hours: 2, weight: 2, desc: '2h of production, instantly' },
  { id: 'rush', name: 'Dikduk Rush', icon: '📖', kind: 'tap', tapMult: 3, seconds: 60, weight: 2, desc: 'x3 tap power for 60s' },
]

function goldenByKind(kind) {
  return GOLDEN_PROMPTS.find(p => p.kind === kind)
}

// ── Prophet's Choice: the rare pick-1-of-3 visitation ──────────────
// Golden Prompts are always-take surprises; the Prophet adds the one thing
// surprises lack — a decision. Three blessings, one choice, same 20s window,
// same fizzle rules (wrong/expired = nothing lost).

export const PROPHET_CHANCE = 0.12   // share of spawns that arrive as the Prophet
export const PROPHET_OPTIONS = 3
export const MANNA_KAVOD = 30        // Manna blessing: instant learning currency
export const EARLY_FIG_HOURS = 6     // Early Harvest: fig timer cut
export const EARLY_VINE_HOURS = 2    // Early Harvest: each vine timer cut

export const PROPHET_BLESSINGS = [
  { id: 'gale', name: 'Ruach Gale', icon: '🌪️', desc: 'x7 Ohr for 77s' },
  { id: 'dew', name: 'Dew of Light', icon: '💧', desc: '2h of production, instantly' },
  { id: 'rush', name: 'Dikduk Rush', icon: '📖', desc: 'x3 tap power for 60s' },
  { id: 'manna', name: 'Manna', icon: '🍞', desc: `+${MANNA_KAVOD} 🌟 Kavod, instantly` },
  { id: 'early', name: 'Early Harvest', icon: '⏰', desc: `Fig −${EARLY_FIG_HOURS}h, every vine −${EARLY_VINE_HOURS}h` },
]

/** Sample PROPHET_OPTIONS distinct blessing ids (exported for tests/determinism). */
export function sampleBlessings(rng = Math.random) {
  const pool = PROPHET_BLESSINGS.map(b => b.id)
  const out = []
  while (out.length < PROPHET_OPTIONS && pool.length) {
    out.push(pool.splice(Math.floor(rng() * pool.length), 1)[0])
  }
  return out
}

/**
 * Apply the player's chosen blessing. gale/dew/rush reuse the Golden Prompt
 * effects; manna grants Kavod; early cuts the grow timers. Returns the same
 * {claimed, granted} shape as resolveGoldenPrompt.
 */
export function applyProphetChoice(state, id, perSec = 0, now = Date.now()) {
  const def = id => PROPHET_BLESSINGS.find(b => b.id === id) || { name: id, desc: '' }
  if (id === 'gale' || id === 'rush') {
    const p = goldenByKind(id === 'gale' ? 'mult' : 'tap')
    const key = id === 'gale' ? 'galeEndsAt' : 'tapEndsAt'
    state.buffs = { ...(state.buffs || {}), [key]: now + p.seconds * 1000 }
    return { claimed: def(id), granted: 0 }
  }
  if (id === 'dew') {
    const p = goldenByKind('hours')
    const granted = perSec * 3600 * (p.hours || 0)
    state.ohr += granted
    state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
    return { claimed: def(id), granted }
  }
  if (id === 'manna') {
    state.kavod = (state.kavod || 0) + MANNA_KAVOD
    return { claimed: def(id), granted: MANNA_KAVOD }
  }
  if (id === 'early') {
    if (state.figs?.readyAt) state.figs = { ...state.figs, readyAt: state.figs.readyAt - EARLY_FIG_HOURS * 3600 * 1000 }
    const vines = [...(state.vineyard?.vines || [])]
    for (let i = 0; i < vines.length; i++) {
      if (vines[i]) vines[i] -= EARLY_VINE_HOURS * 3600 * 1000
    }
    state.vineyard = { level: state.vineyard?.level || 0, vines }
    return { claimed: def(id), granted: 0 }
  }
  return { fizzled: true, reason: 'unknown' }
}

export function galeMultiplier(state, now = Date.now()) {
  if ((state.buffs?.galeEndsAt || 0) <= now) return 1
  return goldenByKind('mult')?.mult || 1
}

export function tapBuffMultiplier(state, now = Date.now()) {
  if ((state.buffs?.tapEndsAt || 0) <= now) return 1
  return goldenByKind('tap')?.tapMult || 1
}

/** Weighted pick (exported for tests/determinism). */
export function pickGoldenPrompt(rng = Math.random) {
  const total = GOLDEN_PROMPTS.reduce((a, p) => a + p.weight, 0)
  let r = rng() * total
  for (const p of GOLDEN_PROMPTS) { r -= p.weight; if (r < 0) return p }
  return GOLDEN_PROMPTS[0]
}

/** Spawn a prompt when none is pending, the interval elapsed, and production exists. */
export function spawnGoldenPrompt(state, now = Date.now(), rng = Math.random, perSec = 1) {
  if (state.golden) return null
  if (perSec <= 0) return null // nothing to multiply yet — never hand out a value-less prompt
  if (now < (state.nextGoldenAt || 0)) return null
  // Rare visitation: the Prophet offers a CHOICE of three blessings instead
  // of one fixed prompt — the surprise system with an actual decision in it.
  if (rng() < PROPHET_CHANCE) {
    const options = sampleBlessings(rng)
    state.golden = { id: 'prophet', expiresAt: now + GOLDEN_WINDOW_SEC * 1000, options }
    const [lo, hi] = GOLDEN_INTERVAL_SEC
    state.nextGoldenAt = now + (lo + rng() * (hi - lo)) * 1000
    return state.golden
  }
  const p = pickGoldenPrompt(rng)
  state.golden = { id: p.id, expiresAt: now + GOLDEN_WINDOW_SEC * 1000 }
  const [lo, hi] = GOLDEN_INTERVAL_SEC
  state.nextGoldenAt = now + (lo + rng() * (hi - lo)) * 1000
  return state.golden
}

/** Clear a prompt whose claim window elapsed (fizzle — nothing lost). */
export function expireGoldenPrompt(state, now = Date.now()) {
  if (state.golden && now > state.golden.expiresAt) { state.golden = null; return true }
  return false
}

export function goldenRemainingSec(state, now = Date.now()) {
  return state.golden ? Math.max(0, Math.ceil((state.golden.expiresAt - now) / 1000)) : 0
}

/**
 * Resolve a pending prompt with the player's answer.
 * Correct inside the window → buff. Wrong or expired → fizzle (nothing lost).
 */
export function resolveGoldenPrompt(state, correct, now = Date.now(), perSec = 0) {
  const g = state.golden
  if (!g) return null
  const expired = now > g.expiresAt
  state.golden = null
  if (!correct || expired) return { fizzled: true, reason: expired ? 'expired' : 'wrong' }
  // The Prophet doesn't grant — he offers. The HUD presents g.options and
  // calls applyProphetChoice with the player's pick.
  if (g.id === 'prophet') return { choice: [...(g.options || [])] }
  const p = GOLDEN_PROMPTS.find(x => x.id === g.id)
  if (!p) return { fizzled: true, reason: 'unknown' }
  if (p.kind === 'mult') {
    state.buffs = { ...(state.buffs || {}), galeEndsAt: now + p.seconds * 1000 }
    return { claimed: p, granted: 0 }
  }
  if (p.kind === 'tap') {
    state.buffs = { ...(state.buffs || {}), tapEndsAt: now + p.seconds * 1000 }
    return { claimed: p, granted: 0 }
  }
  const granted = perSec * 3600 * (p.hours || 0)
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  return { claimed: p, granted }
}

export function frenzyRemainingSec(state, now = Date.now()) {
  return Math.max(0, Math.ceil(((state.buffs?.frenzyEndsAt || 0) - now) / 1000))
}

/**
 * Buy Ruach Frenzy: x3 Ohr/sec for 60s. Returns true on success.
 * Refuses while a frenzy is already active (no stacking, no waste).
 */
export function buyFrenzy(state, now = Date.now()) {
  if ((state.kavod || 0) < FRENZY_COST) return false
  if ((state.buffs?.frenzyEndsAt || 0) > now) return false
  state.kavod -= FRENZY_COST
  const secs = FRENZY_SECONDS + permEffect(state.perm || {}, 'frenzyBonusSec')
  state.buffs = { ...(state.buffs || {}), frenzyEndsAt: now + secs * 1000 }
  return true
}

/**
 * Buy Time Warp: instantly grant `hours` of production at the given rate.
 * Returns granted Ohr (0 if unaffordable).
 */
export function buyTimeWarp(state, perSec, hours = 1) {
  const cost = warpCost(state)
  if ((state.kavod || 0) < cost) return 0
  state.kavod -= cost
  state.warps = (state.warps || 0) + 1
  const granted = perSec * 3600 * hours
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  return granted
}

// ── Letter upgrades (×2 tiers, bought with Ohr) ──────────────────────
// The choice axis: doubling a letter you have 10 of beats a new letter you
// can barely afford. Thresholds are Cookie's own (1/5/25/50/100 shortened).

export const LETTER_UPGRADE_TIERS = [
  { at: 10, mult: 2, costMult: 10 },
  { at: 25, mult: 2, costMult: 60 },
  { at: 50, mult: 2, costMult: 400 },
  { at: 100, mult: 2, costMult: 3000 },
]

export function letterUpgradeId(i, k) { return `u${i}:${k}` }

export function letterUpgradeCost(i, k) {
  return Math.ceil(baseCost(i) * (LETTER_UPGRADE_TIERS[k]?.costMult || 1))
}

/** Product of every purchased ×2 tier for letter i. */
export function letterMultiplier(upgrades = {}, i) {
  let m = 1
  for (let k = 0; k < LETTER_UPGRADE_TIERS.length; k++) {
    if (upgrades[letterUpgradeId(i, k)]) m *= LETTER_UPGRADE_TIERS[k].mult
  }
  return m
}

/** Tiers that are unlocked (owned threshold met) and not yet bought. */
export function availableLetterUpgrades(state, i) {
  if (!exileAllows(state, i)) return []
  const owned = (state.owned || {})[i] || 0
  const ups = state.letterUpgrades || {}
  const out = []
  for (let k = 0; k < LETTER_UPGRADE_TIERS.length; k++) {
    const t = LETTER_UPGRADE_TIERS[k]
    if (owned >= t.at && !ups[letterUpgradeId(i, k)]) {
      out.push({ k, id: letterUpgradeId(i, k), cost: letterUpgradeCost(i, k), mult: t.mult, at: t.at })
    }
  }
  return out
}

/** Buy one letter upgrade. Returns true on success. */
export function buyLetterUpgrade(state, i, k) {
  if (!exileAllows(state, i)) return false
  const owned = (state.owned || {})[i] || 0
  const t = LETTER_UPGRADE_TIERS[k]
  if (!t || owned < t.at) return false
  const id = letterUpgradeId(i, k)
  if ((state.letterUpgrades || {})[id]) return false
  const cost = letterUpgradeCost(i, k)
  if ((state.ohr || 0) < cost) return false
  state.ohr -= cost
  state.letterUpgrades = { ...(state.letterUpgrades || {}), [id]: true }
  return true
}

// ── Kavod permanents: learning buys permanent power (one-time) ───────
export const KAVOD_UPGRADES = [
  { id: 'tap2', name: 'Steady Hand', icon: '✋', desc: 'Tap power ×2', cost: 15, effect: { tapMult: 1 } },
  { id: 'crit5', name: 'Sharp Eye', icon: '👁️', desc: '+5% crit chance', cost: 25, effect: { critAdd: 0.05 } },
  { id: 'frenzy30', name: 'Deep Breath', icon: '🌬️', desc: 'Frenzy lasts +30s', cost: 40, effect: { frenzyBonusSec: 30 } },
  { id: 'offline25', name: 'Faithful Watch', icon: '🕯️', desc: 'Offline earnings +25%', cost: 60, effect: { offlineAdd: 0.25 } },
  { id: 'global25', name: 'Kavanah', icon: '🎯', desc: 'All Ohr +25%', cost: 100, effect: { globalMult: 0.25 } },
  { id: 'seed', name: 'Remembered Words', icon: '📜', desc: 'Every prestige starts with +1 of your first letter', cost: 150, effect: { seedLetter: 1 } },
]

export function hasPerm(state, id) { return !!(state.perm || {})[id] }

/** Sum a numeric effect key across owned permanents (Kavod + heavenly). */
export function permEffect(perm = {}, key) {
  let total = 0
  for (const u of KAVOD_UPGRADES) {
    if (perm[u.id] && u.effect[key] !== undefined) total += u.effect[key]
  }
  for (const u of HEAVENLY_UPGRADES) {
    if (perm[u.id] && u.effect[key] !== undefined) total += u.effect[key]
  }
  return total
}

// ── Aliyah: cube-root ascension sparks + heavenly unlock chain ───────
// Cookie's heavenly-chips shape. Sparks are earned from LIFETIME Ohr by cube
// root, give +1% Ohr each while UNSPENT, and are spent on an ordered heavenly
// chain — so holding sparks and buying upgrades compete for the same resource
// (Cookie's actual tradeoff). Not a wipe: roots already supply the reset loop,
// and DESIGN.md bans punishing resets.
//
// Tuned by headless sim (scripts/balance-sim.mjs): at 1e8 the first spark lands
// at ~40m of engaged play and the whole chain finishes in ~1.8h — too early for
// a meta layer. 1e12 puts the first spark at ~2.8h of *optimal* play, which is
// roughly 1-4 days for a real learner (the sim is a 5-answers/min upper bound).

export const ALIYAH_BASE = 1e12
export const SPARK_BONUS = 0.01
// The Ascent: six stations, two ways up each. Enoch walked with God and was
// taken (Gen 5.24); his tour runs treasuries of winds (1 En 18.1), portals
// and luminaries (1 En 34, 72), the crystal throne (1 En 14.18) — with
// Genesis anchors where they already live (primordial light, Shabbat rest,
// first fruits, David's key). Each tier offers a genuine tradeoff (head-start
// vs scaling, taps vs idle, burst vs steady, active vs offline), and each
// choice is EXCLUSIVE: your heaven looks different from mine (64 heavens).
// Costs stay Fibonacci; effects reuse the existing perm keys so every
// consumer (permEffect and below) works unchanged.
export const HEAVENLY_UPGRADES = [
  { id: 'h_legacy', tier: 0, cost: 1, name: 'Legacy of the Fathers', icon: '📜', desc: 'Every prestige starts with +1 of your first letter', effect: { seedLetter: 1 } },
  { id: 'h_firstfruits', tier: 0, cost: 1, name: 'First Fruits', icon: '🌾', desc: 'All Ohr +10%, Abel’s offering first', effect: { globalMult: 0.10 } },
  { id: 'h_light', tier: 1, cost: 2, name: 'Primordial Light', icon: '💡', desc: 'All Ohr +25%', effect: { globalMult: 0.25 } },
  { id: 'h_luminary', tier: 1, cost: 2, name: 'Luminary Courses', icon: '🌙', desc: 'Offline earnings +50% — the moon keeps its courses while you sleep', effect: { offlineAdd: 0.50 } },
  { id: 'h_wisdom', tier: 2, cost: 3, name: 'Chochmah', icon: '🧠', desc: 'Tap power +50%', effect: { tapMult: 0.5 } },
  { id: 'h_watcher', tier: 2, cost: 3, name: 'Watcher', icon: '👁️', desc: '+10% crit chance — the holy ones strike suddenly', effect: { critAdd: 0.10 } },
  { id: 'h_rest', tier: 3, cost: 5, name: 'Shabbat Rest', icon: '🕯️', desc: 'Offline earnings +25%', effect: { offlineAdd: 0.25 } },
  { id: 'h_vigil', tier: 3, cost: 5, name: 'Night Watch', icon: '🦉', desc: 'Frenzy lasts +60s — for those who stay awake', effect: { frenzyBonusSec: 60 } },
  { id: 'h_breath', tier: 4, cost: 8, name: 'Long Breath', icon: '🌬️', desc: 'Frenzy lasts +30s', effect: { frenzyBonusSec: 30 } },
  { id: 'h_winds', tier: 4, cost: 8, name: 'Treasuries of Winds', icon: '🌪️', desc: 'All Ohr +50%, from the storehouses Enoch saw', effect: { globalMult: 0.50 } },
  { id: 'h_key', tier: 5, cost: 13, name: 'Key of David', icon: '🗝️', desc: 'All Ohr +100%', effect: { globalMult: 1.0 } },
  { id: 'h_throne', tier: 5, cost: 13, name: 'Throne Vision', icon: '🔥', desc: 'Tap power +100% and +5% crit — the crystal throne', effect: { tapMult: 1.0, critAdd: 0.05 } },
]

export const HEAVENLY_TIERS = [0, 1, 2, 3, 4, 5]

export function heavenlyTier(id) {
  return HEAVENLY_UPGRADES.find(u => u.id === id)?.tier ?? -1
}

/** A tier is complete once either of its two ways is owned. */
export function heavenlyTierOwned(state, t) {
  return HEAVENLY_UPGRADES.some(u => u.tier === t && heavenlyOwned(state, u.id))
}

/** Total sparks ever earned (cube root of lifetime Ohr). */
export function sparksEarned(lifetimeOhr) {
  return Math.floor(Math.cbrt(Math.max(0, lifetimeOhr) / ALIYAH_BASE))
}

/** Lifetime Ohr needed to reach `n` earned sparks (inverse of sparksEarned). */
export function lifetimeForSpark(n) {
  return Math.pow(n, 3) * ALIYAH_BASE
}

/** Sparks already spent on the heavenly chain. */
export function heavenlySpent(perm = {}) {
  let total = 0
  for (const u of HEAVENLY_UPGRADES) if (perm[u.id]) total += u.cost
  return total
}

/** Sparks not yet spent — these are the ones granting +1% each. */
export function availableSparks(state) {
  return Math.max(0, sparksEarned(state.lifetimeOhr || 0) - heavenlySpent(state.perm || {}))
}

/** Global multiplier from unspent sparks. */
export function sparkBonus(sparks) {
  return 1 + Math.max(0, sparks) * SPARK_BONUS
}

export function heavenlyOwned(state, id) {
  return !!(state.perm || {})[id]
}

/** Tier gate: tier 0 is open; a tier unlocks once the previous tier has EITHER way owned. */
export function heavenlyUnlocked(state, id) {
  const t = heavenlyTier(id)
  if (t < 0) return false
  return t === 0 || heavenlyTierOwned(state, t - 1)
}

/**
 * Buy a heavenly upgrade with sparks. One way per tier — choosing locks the
 * rival out (build identity: 64 possible heavens). Returns true on success.
 */
export function buyHeavenly(state, id) {
  const u = HEAVENLY_UPGRADES.find(x => x.id === id)
  if (!u || heavenlyOwned(state, id)) return false
  if (!heavenlyUnlocked(state, id)) return false
  if (heavenlyTierOwned(state, u.tier)) return false
  if (availableSparks(state) < u.cost) return false
  state.perm = { ...(state.perm || {}), [id]: true }
  return true
}

/** Progress toward the next earned spark — the "first ascension" target. */
export function sparkProgress(lifetimeOhr) {
  const earned = sparksEarned(lifetimeOhr)
  const next = earned + 1
  const need = lifetimeForSpark(next)
  return { earned, next, need, pct: need > 0 ? Math.min(1, (lifetimeOhr || 0) / need) : 0 }
}

// ── Figs: the 20h retention timer (sugar-lump analogue) ──────────────
// One fig grows over 20h; harvesting grants hours of production, levels the
// grove (up to 10, +10% Ohr each forever), and plants the next one. Deliberately
// NOT quiz-gated: losing a 20h timer to a misclick would punish, which DESIGN.md
// bans. The timer IS the retention hook; harvesting is one deliberate tap.

export const FIG_RIPEN_HOURS = 20
export const FIG_MAX_LEVEL = 10
export const FIG_REWARD_HOURS = 4
export const FIG_LEVEL_BONUS = 0.10

export function figReady(state, now = Date.now()) {
  return (state.figs?.readyAt || 0) > 0 && now >= state.figs.readyAt
}

export function figRemainingSec(state, now = Date.now()) {
  return Math.max(0, Math.ceil(((state.figs?.readyAt || 0) - now) / 1000))
}

export function figMultiplier(figs) {
  return 1 + Math.min(FIG_MAX_LEVEL, figs?.level || 0) * FIG_LEVEL_BONUS
}

/** Plant a fig if none is growing. Returns true if planted. */
export function plantFig(state, now = Date.now()) {
  if (state.figs?.readyAt) return false
  state.figs = { level: state.figs?.level || 0, readyAt: now + FIG_RIPEN_HOURS * 3600 * 1000 }
  return true
}

/** Harvest a ripe fig: grants hours of production, levels up, replants. */
export function harvestFig(state, perSec, now = Date.now()) {
  if (!figReady(state, now)) return 0
  const level = Math.min(FIG_MAX_LEVEL, (state.figs?.level || 0) + 1)
  const granted = perSec * FIG_REWARD_HOURS * 3600 * (1 + level * FIG_LEVEL_BONUS)
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  state.figs = { level, readyAt: now + FIG_RIPEN_HOURS * 3600 * 1000 }
  return granted
}

// ── Vineyard: the 4h tending loop (garden analogue) ────────────────
// Figs are the day-scale retention timer (one 20h tree, 4h reward, +10%/lvl
// to 2.0x). The vineyard is the session-scale tending loop: 3 vines ripening
// in parallel on a 4h cycle, each harvest granting 15min of production and
// levelling the whole vineyard (+5%/lvl to 1.5x). Same income shape as figs
// (3×0.25h/4h ≈ +19% vs 4h/20h = +20% when perfectly tended), smaller
// permanent — the quick small win beside the fig's slow big one. Same rules:
// never quiz-gated (punishment ban), rewards on the effective buffed rate.

export const VINE_COUNT = 3
export const VINE_RIPEN_HOURS = 4
export const VINE_REWARD_HOURS = 0.25
export const VINE_MAX_LEVEL = 10
export const VINE_LEVEL_BONUS = 0.05

export function vineReady(state, i, now = Date.now()) {
  const readyAt = state.vineyard?.vines?.[i] || 0
  return readyAt > 0 && now >= readyAt
}

export function vineRemainingSec(state, i, now = Date.now()) {
  return Math.max(0, Math.ceil(((state.vineyard?.vines?.[i] || 0) - now) / 1000))
}

export function vineyardMultiplier(vineyard) {
  return 1 + Math.min(VINE_MAX_LEVEL, vineyard?.level || 0) * VINE_LEVEL_BONUS
}

/** Plant every empty vine slot. Returns the number of vines planted. */
export function plantVineyard(state, now = Date.now()) {
  const vines = [...(state.vineyard?.vines || [])]
  while (vines.length < VINE_COUNT) vines.push(0)
  let planted = 0
  for (let i = 0; i < VINE_COUNT; i++) {
    if (!vines[i]) { vines[i] = now + VINE_RIPEN_HOURS * 3600 * 1000; planted++ }
  }
  state.vineyard = { level: state.vineyard?.level || 0, vines }
  return planted
}

/** Harvest one ripe vine: grants production, levels the vineyard, replants the slot. */
export function harvestVine(state, i, perSec, now = Date.now()) {
  if (!vineReady(state, i, now)) return 0
  const level = Math.min(VINE_MAX_LEVEL, (state.vineyard?.level || 0) + 1)
  const granted = perSec * VINE_REWARD_HOURS * 3600 * (1 + level * VINE_LEVEL_BONUS)
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  const vines = [...(state.vineyard?.vines || [])]
  while (vines.length < VINE_COUNT) vines.push(0)
  vines[i] = now + VINE_RIPEN_HOURS * 3600 * 1000
  state.vineyard = { level, vines }
  return granted
}

// ── Achievements → Shemen (oil): +4% Ohr each ────────────────────────
// Derived from state — no extra bookkeeping, no way to lose one.
// ("Talmidim multipliers read Shemen" from the plan is moot: there is no
//  building ladder — letters are the generators — so Shemen is a global.)

export const SHEMEN_PER_ACHIEVEMENT = 0.04

export const ACHIEVEMENTS = [
  { id: 'first_letter', name: 'First Light', icon: '🕯️', desc: 'Inscribe your first golem', check: s => totalOwned(s) >= 1 },
  { id: 'own10', name: 'Choir', icon: '🗿', desc: 'Own 10 golems', check: s => totalOwned(s) >= 10 },
  { id: 'own100', name: 'Legion', icon: '🏛️', desc: 'Own 100 golems', check: s => totalOwned(s) >= 100 },
  { id: 'own1000', name: 'Multitude', icon: '👥', desc: 'Own 1,000 golems', check: s => totalOwned(s) >= 1000 },
  { id: 'streak25', name: 'Unstoppable', icon: '🔥', desc: 'Reach a 25 streak', check: s => (s.bestStreak || 0) >= 25 },
  { id: 'streak50', name: 'Steadfast', icon: '🏔️', desc: 'Reach a 50 streak', check: s => (s.bestStreak || 0) >= 50 },
  { id: 'correct100', name: 'Diligent', icon: '📖', desc: 'Answer 100 correctly', check: s => (s.correct || 0) >= 100 },
  { id: 'correct1000', name: 'Scribe', icon: '✍️', desc: 'Answer 1,000 correctly', check: s => (s.correct || 0) >= 1000 },
  { id: 'root1', name: 'First Fruits', icon: '🌿', desc: 'Forge your first root', check: s => (s.roots || 0) >= 1 },
  { id: 'prestige5', name: 'Reformed', icon: '🔄', desc: 'Prestige 5 times', check: s => (s.prestiges || 0) >= 5 },
  { id: 'fig1', name: 'Gardener', icon: '🍯', desc: 'Harvest your first fig', check: s => (s.figs?.level || 0) >= 1 },
  { id: 'vine1', name: 'Vinedresser', icon: '🍇', desc: 'Harvest your first vine', check: s => (s.vineyard?.level || 0) >= 1 },
  { id: 'spark1', name: 'Ascendant', icon: '💫', desc: 'Earn your first Aliyah spark', check: s => sparksEarned(s.lifetimeOhr || 0) >= 1 },
  { id: 'vow1', name: 'Covenant Keeper', icon: '⛓️', desc: 'Complete a vow run (exile or shemittah)', check: s => (s.exilesCompleted || 0) >= 1 },
  { id: 'own22', name: 'Full Aleph-Bet', icon: '🔠', desc: 'Own every letter', check: s => LETTERS.every((_, i) => (s.owned?.[i] || 0) > 0) },
  // Hidden deeds: concealed (❓) until earned — discovery is the reward.
  { id: 'breadth10', name: 'Well-Rounded', icon: '🍲', desc: 'Study 10 different letters', hidden: true, check: s => Object.values(s.owned || {}).filter(n => (n || 0) > 0).length >= 10 },
  { id: 'crit50', name: 'Sharpshooter', icon: '🎯', desc: 'Land 50 crits', hidden: true, check: s => (s.crits || 0) >= 50 },
  { id: 'hoarder10', name: 'Patient', icon: '🏦', desc: 'Hold 10 unspent sparks at once', hidden: true, check: s => availableSparks(s) >= 10 },
]

export function achievementsEarned(state) {
  return ACHIEVEMENTS.filter(a => { try { return a.check(state) } catch { return false } })
}

export function shemenMultiplier(state) {
  return 1 + achievementsEarned(state).length * SHEMEN_PER_ACHIEVEMENT
}

/**
 * Share card: a plain-text snapshot of the workshop for pasting into a
 * message (study group, family chat). No backend, no accounts — the social
 * layer without multiplayer. Pure and deterministic (no dates), so it is
 * trivially testable.
 */
export function shareCard(state) {
  const fmt = n => Math.floor(n || 0).toLocaleString('en-US')
  const earned = achievementsEarned(state)
  const lines = [
    '🕯️ My EMET workshop — Aleph to Revelation',
    `✨ ${fmt(state.lifetimeOhr)} lifetime Ohr · 🌿 ${state.roots || 0} roots · 🗿 ${totalOwned(state)} golems`,
    `🔥 best streak ${state.bestStreak || 0} · 🌟 ${fmt(state.kavod)} Kavod`,
    `🍯 grove lvl ${state.figs?.level || 0} · 🍇 vineyard lvl ${state.vineyard?.level || 0} · 💫 ${availableSparks(state)} sparks`,
    `🏆 ${earned.length}/${ACHIEVEMENTS.length} achievements · 🫒 +${Math.round((shemenMultiplier(state) - 1) * 100)}% Shemen`,
  ]
  if (state.exile) lines.push(`⛓️ under vow (${state.exile.kind}) — study with me`)
  const ascended = HEAVENLY_UPGRADES.filter(u => (state.perm || {})[u.id])
  if (ascended.length) lines.push(`🌌 ascended: ${ascended.map(u => u.name).join(' · ')}`)
  return lines.join('\n')
}

// ── Daily lesson: 10 correct answers, once per day ───────────────────

export const DAILY_GOAL = 10
export const DAILY_REWARD_HOURS = 1

export function dayKey(now = Date.now()) {
  return new Date(now).toDateString()
}

/** Record a correct answer toward today's goal (resets on a new day). */
export function recordDailyCorrect(state, now = Date.now()) {
  const key = dayKey(now)
  const d = state.daily || {}
  if (d.day !== key) state.daily = { day: key, correct: 1, claimed: false }
  else state.daily = { ...d, correct: (d.correct || 0) + 1 }
  return state.daily
}

export function dailyReady(state, now = Date.now()) {
  const d = state.daily || {}
  return d.day === dayKey(now) && (d.correct || 0) >= DAILY_GOAL && !d.claimed
}

/** Claim today's reward: DAILY_REWARD_HOURS of production, once per day. */
export function claimDaily(state, perSec, now = Date.now()) {
  if (!dailyReady(state, now)) return 0
  const granted = perSec * DAILY_REWARD_HOURS * 3600
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  state.daily = { ...state.daily, claimed: true }
  return granted
}

/** Buy a permanent with Kavod. Returns true on success. */
export function buyPerm(state, id) {
  const u = KAVOD_UPGRADES.find(x => x.id === id)
  if (!u || (state.perm || {})[id]) return false
  if ((state.kavod || 0) < u.cost) return false
  state.kavod -= u.cost
  state.perm = { ...(state.perm || {}), [id]: true }
  return true
}

// Self-check: node --test or plain node run prints assertions.
if (typeof process !== 'undefined' && process.argv?.[1]?.endsWith('idle-game.js')) {
  const a = (cond, msg) => { if (!cond) { console.error('FAIL:', msg); process.exit(1) } else console.log('ok:', msg) }
  a(baseCost(0) === 10, 'Aleph costs 10')
  a(baseCost(21) > 100000, `Tav costs ${baseCost(21)} (>100k)`)
  a(generatorCost(0, 0) === 10, 'first Aleph = 10')
  a(generatorCost(0, 10) > 30, '10th Aleph scales 1.15^10')
  a(rootsEarned(0) === 0, 'no roots at 0')
  a(rootsEarned(111112) === 1, 'first root ≈111k')
  a(rootsEarned(1e6) === 3, '3 roots at 1M')
  a(Math.abs(perSecond({ 0: 1 }, { 0: 1 }) - 0.3) < 1e-9, '1 mastered Aleph = 0.3/s')
  a(tapValue(0, 0) === 1, 'base tap = 1')
  a(offlineEarnings(10, 3600, {}, 0) === 10 * 3600 * 0.5, 'offline 50% eff')
  a(offlineEarnings(10, 99 * 3600, {}, 0) === 10 * 12 * 3600 * 0.5, 'offline capped 12h')
  a(promotionExpCost(0) === 1 && promotionExpCost(3) === 15, 'promotion exp doubles')
  a(applyFeedback({ bias: 0, recent: [] }, 'easier').bias === -0.25, 'feedback easier eases')
  a(applyFeedback({ bias: 0, recent: [] }, 'harder').bias === 0.25, 'feedback harder hardens')
  a(difficultyScalars({ bias: -1 }).costMult < 1, 'gentle = cheaper generators')
  a(difficultyScalars({ bias: 1 }).tapMult < 1, 'fierce = smaller taps')
  let dd = defaultDifficulty()
  for (let k = 0; k < 20; k++) dd = recordAttempt(dd, false, 25000)
  a(dd.bias < 0, 'struggling auto-eases')
  dd = defaultDifficulty()
  for (let k = 0; k < 20; k++) dd = recordAttempt(dd, true, 1000)
  a(dd.bias > 0, 'crushing auto-hardens')
  a(bulkCost(0, 0, 1) === generatorCost(0, 0), 'bulk x1 = single cost')
  a(bulkCost(0, 0, 10) > 10 * generatorCost(0, 0), 'bulk x10 scales 1.15')
  const mb = maxBuyable(0, 0, 100)
  a(mb.n >= 3 && mb.spend <= 100, `max buy with 100 Ohr: ${mb.n} for ${mb.spend}`)
  a(Math.abs(lifetimeForRoots(1) - 111111) < 1, 'inverse: 1 root needs ~111k')
  const qs = defaultIdleState()
  a(!questComplete(qs, QUESTS[0]), 'buy1 incomplete at start')
  qs.owned = { 0: 1 }
  a(questComplete(qs, QUESTS[0]), 'buy1 complete after purchase')
  a(claimQuest(qs, 'buy1') === 25 && qs.quests.buy1, 'claim pays +25 once')
  a(claimQuest(qs, 'buy1') === 0, 'no double-claim')
  qs.streak = 5
  const ms = checkStreakMilestone(qs)
  a(ms && ms.milestone === 5 && ms.bonus === 125, 'streak-5 milestone +125')
  a(checkStreakMilestone(qs) === null, 'milestone fires once')
  const ng = nextGoals(defaultIdleState())
  a(ng.gen && ng.gen.letter === 'א' && ng.root.next === 1, 'next goals: Aleph + root 1')
  const ks = defaultIdleState()
  const cr = applyCorrectAnswer(ks, 0, () => 0.99)
  a(cr.kavod === 1 && ks.kavod === 1, 'correct earns 1 Kavod')
  ks.streak = 9
  const cr2 = applyCorrectAnswer(ks, 0, () => 0.99)
  a(cr2.kavod === 3, 'streak 10 earns 1 + 2 = 3 Kavod')
  const critR = applyCorrectAnswer(defaultIdleState(), 0, () => 0.0)
  a(critR.crit && critR.kavod === 4, 'crit earns 1 + 3 = 4 Kavod')
  const fs = defaultIdleState()
  a(buyFrenzy(fs) === false, 'frenzy refused when broke')
  fs.kavod = 50
  a(buyFrenzy(fs) === true && fs.kavod === 30, 'frenzy costs 20 Kavod')
  a(buffMultiplier(fs) === 3, 'frenzy active x3')
  a(buyFrenzy(fs) === false, 'no stacking frenzy')
  a(warpCost(defaultIdleState()) === 30, 'first warp 30 Kavod')
  const ws = defaultIdleState()
  ws.kavod = 100
  const granted = buyTimeWarp(ws, 10, 1)
  a(granted === 36000 && ws.warps === 1 && ws.kavod === 70, 'warp grants 1h production, escalates')
  a(warpCost(ws) === 90, 'second warp 90 Kavod')
  a(STARTING_OHR >= generatorCost(0, 0), 'starting Ohr affords the first letter')
  const ps = defaultIdleState()
  ps.lifetimeOhr = 1e6
  ps.ohr = 5
  ps.owned = { 0: 3 }
  applyPrestige(ps)
  a(ps.ohr === STARTING_OHR && Object.keys(ps.owned).length === 0, 'prestige reseeds starting Ohr + clears golems')
  // Letter upgrades
  a(letterMultiplier({}, 0) === 1, 'no letter upgrades = x1')
  let us = defaultIdleState()
  a(availableLetterUpgrades(us, 0).length === 0, 'no upgrades available at 0 owned')
  us.owned = { 0: 10 }
  const au = availableLetterUpgrades(us, 0)
  a(au.length === 1 && au[0].cost === letterUpgradeCost(0, 0), 'x2 tier unlocks at 10 owned')
  us.ohr = au[0].cost
  a(buyLetterUpgrade(us, 0, 0) === true && us.letterUpgrades['u0:0'], 'buy letter upgrade')
  a(buyLetterUpgrade(us, 0, 0) === false, 'letter upgrade is one-time')
  a(letterMultiplier(us.letterUpgrades, 0) === 2, 'letter upgrade doubles')
  const base = perSecond({ 0: 10 }, { 0: 1 })
  const upgraded = perSecond({ 0: 10 }, { 0: 1 }, {}, 0, 0, us.letterUpgrades)
  a(Math.abs(upgraded - base * 2) < 1e-9, 'perSecond reflects letter upgrade x2')
  a(statePerSecond(us, { 0: 1 }) > 0, 'statePerSecond composes state')
  // Kavod permanents
  const kp = defaultIdleState()
  a(buyPerm(kp, 'tap2') === false, 'perm refused when broke')
  kp.kavod = 200
  a(buyPerm(kp, 'tap2') === true && kp.kavod === 185, 'perm costs Kavod')
  a(buyPerm(kp, 'tap2') === false, 'perm is one-time')
  a(permEffect(kp.perm, 'tapMult') === 1, 'tap2 = +100% (x2)')
  a(Math.abs(tapValue(0, 0, {}, null, kp.perm) - 2) < 1e-9, 'tap perm doubles tap value')
  kp.kavod = 200
  buyPerm(kp, 'crit5')
  a(critChance({}, kp.perm) > critChance({}), 'crit perm raises crit chance')
  a(offlineEarnings(10, 3600, {}, 0, { offline25: true }) > offlineEarnings(10, 3600, {}, 0),
    'offline perm raises offline earnings')
  a(buffMultiplier({ buffs: { frenzyEndsAt: Date.now() + 1000 } }) === FRENZY_MULT, 'frenzy buff applies')
  kp.kavod = 200
  buyPerm(kp, 'seed')
  const pp = { ...kp, lifetimeOhr: 1e6, owned: { 0: 5 }, ohr: 0 }
  applyPrestige(pp)
  a(pp.owned[0] === 1, 'seed perm grants 1 starting letter after prestige')
  // Letter synergy (breadth + mastery, capped)
  a(synergyMultiplier({ 0: 5 }, {}, 0) === 1, 'lone letter has no synergy')
  a(synergyMultiplier({ 0: 5, 1: 5 }, {}, 0) > 1, 'owning another letter lifts output')
  const synOwn = synergyMultiplier({ 0: 5, 1: 5 }, {}, 0)
  const synMastered = synergyMultiplier({ 0: 5, 1: 5 }, { 1: 1 }, 0)
  a(synMastered > synOwn, 'mastering a neighbour lifts output more than owning it')
  a(synergyMultiplier({ 0: 5, 1: 5 }, { 1: MASTERY_THRESHOLD }, 0) === synMastered, 'mastery bar is the curriculum threshold')
  const allOwned = Object.fromEntries(LETTERS.map((_, k) => [k, 1]))
  const allMastered = Object.fromEntries(LETTERS.map((_, k) => [k, 1]))
  a(synergyMultiplier(allOwned, allMastered, 0) === 1 + SYNERGY_CAP, 'synergy is capped')
  a(synergyMultiplier({ 0: 5, 1: 5 }, {}, 0) === synergyMultiplier({ 0: 5, 1: 5 }, {}, 1), 'synergy is symmetric between letters')
  a(workshopSynergy({ 0: 5 }, {}) === 1 + SYNERGY_OWNED, 'workshop synergy counts every letter')
  a(Math.abs(workshopSynergy({ 0: 5, 1: 5 }, { 1: 1 }) - (1 + 2 * SYNERGY_OWNED + SYNERGY_MASTERED)) < 1e-9, 'workshop synergy adds mastery on top')
  const rawPair = (baseRate(0) * 10 * 1.5 + baseRate(1) * 10 * 1.5) * synergyMultiplier({ 0: 10, 1: 10 }, { 0: 1, 1: 1 }, 0)
  a(Math.abs(perSecond({ 0: 10, 1: 10 }, { 0: 1, 1: 1 }) - rawPair) < 1e-9, 'perSecond applies synergy to every letter')
  // Aliyah sparks + heavenly unlock chain
  a(sparksEarned(0) === 0, 'no sparks at 0 lifetime')
  a(sparksEarned(ALIYAH_BASE) === 1, 'first spark at ALIYAH_BASE')
  a(sparksEarned(8 * ALIYAH_BASE) === 2 && sparksEarned(27 * ALIYAH_BASE) === 3, 'sparks are cube-root')
  a(Math.abs(lifetimeForSpark(2) - 8 * ALIYAH_BASE) < 1, 'lifetimeForSpark inverts sparksEarned')
  a(Math.abs(sparkBonus(5) - 1.05) < 1e-9, 'each unspent spark = +1%')
  const hs = defaultIdleState()
  hs.lifetimeOhr = 8 * ALIYAH_BASE
  a(availableSparks(hs) === 2, 'available sparks = earned - spent')
  a(heavenlyUnlocked(hs, 'h_legacy') && heavenlyUnlocked(hs, 'h_firstfruits') && !heavenlyUnlocked(hs, 'h_light'), 'tier 0 open, tier 1 locked until either way is owned')
  a(buyHeavenly(hs, 'h_light') === false, 'cannot skip the chain')
  a(buyHeavenly(hs, 'h_legacy') === true && heavenlyOwned(hs, 'h_legacy'), 'buy the first heavenly upgrade')
  a(buyHeavenly(hs, 'h_firstfruits') === false, 'choosing locks the rival out (one way per tier)')
  a(availableSparks(hs) === 1, 'spending a spark reduces the live bonus')
  a(heavenlyUnlocked(hs, 'h_light') && heavenlyUnlocked(hs, 'h_luminary'), 'tier unlocks BOTH next-tier ways')
  hs.lifetimeOhr = 27 * ALIYAH_BASE // 3 earned, 3 spent → 0 available
  a(buyHeavenly(hs, 'h_luminary') === true && heavenlyTierOwned(hs, 1), 'the rival way completes the tier too')
  a(buyHeavenly(hs, 'h_light') === false, 'tier complete means the other way is closed')
  a(permEffect(hs.perm, 'offlineAdd') === 0.50, 'rival effect feeds permEffect (no dropped modifier)')
  a(heavenlyTier('bogus') === -1 && !heavenlyUnlocked(hs, 'bogus'), 'unknown ids stay locked')
  a(permEffect(hs.perm, 'globalMult') === 0, 'unbought branches grant nothing')
  a(sparkBonus(0) === 1, 'no sparks = no bonus')
  a(sparkProgress(0).next === 1 && sparkProgress(0).pct === 0, 'spark progress starts at 1, 0%')
  a(sparkProgress(ALIYAH_BASE).earned === 1 && sparkProgress(ALIYAH_BASE).next === 2, 'spark progress advances')
  const sparkState = { ...defaultIdleState(), lifetimeOhr: 27 * ALIYAH_BASE, owned: { 0: 10 } }
  a(statePerSecond(sparkState, { 0: 1 }) > perSecond({ 0: 10 }, { 0: 1 }), 'statePerSecond includes the spark bonus')
  a(Math.abs(statePerSecond(sparkState, { 0: 1 }) - perSecond({ 0: 10 }, { 0: 1 }, {}, 0, 0, {}, {}, 3) * shemenMultiplier(sparkState)) < 1e-9, 'spark bonus is exactly +1% each')
  // Golden Prompts (deterministic rng: () => 0.5 never rolls the Prophet)
  const gp = defaultIdleState()
  a(gp.golden === null && gp.nextGoldenAt === 0, 'no golden prompt at start')
  a(spawnGoldenPrompt(gp, 1000, () => 0.5) !== null && !!gp.golden, 'first prompt spawns when due')
  a(goldenRemainingSec(gp, 1000) === GOLDEN_WINDOW_SEC, 'claim window is 20s')
  const gRes = resolveGoldenPrompt(gp, true, 2000, 0)
  a(gRes.claimed && !gRes.fizzled, 'correct answer claims the prompt')
  a(gp.golden === null && gp.nextGoldenAt > 2000, 'prompt cleared + next one scheduled')
  const gp2 = defaultIdleState()
  spawnGoldenPrompt(gp2, 1000, () => 0.5)
  a(resolveGoldenPrompt(gp2, false, 2000, 0).fizzled === true, 'wrong answer fizzles')
  a(gp2.buffs.galeEndsAt === 0 && gp2.buffs.tapEndsAt === 0, 'fizzle grants nothing (no punishment)')
  const gp3 = defaultIdleState()
  spawnGoldenPrompt(gp3, 1000, () => 0.5)
  const gExp = resolveGoldenPrompt(gp3, true, 1000 + (GOLDEN_WINDOW_SEC + 1) * 1000, 0)
  a(gExp.fizzled === true && gExp.reason === 'expired', 'late answer fizzles (window enforced)')
  const gp4 = defaultIdleState()
  gp4.buffs = { ...gp4.buffs, galeEndsAt: 5000 }
  a(galeMultiplier(gp4, 1000) === 7 && buffMultiplier(gp4, 1000) === 7, 'gale = x7 and feeds buffMultiplier')
  gp4.buffs = { ...gp4.buffs, frenzyEndsAt: 5000 }
  a(buffMultiplier(gp4, 1000) === 7, 'same-kind buffs take the max, not the product')
  a(galeMultiplier(gp4, 6000) === 1, 'gale expires')
  const gp5 = defaultIdleState()
  gp5.buffs = { ...gp5.buffs, tapEndsAt: 5000 }
  a(tapBuffMultiplier(gp5, 1000) === 3, 'rush = x3 tap')
  a(tapValue(0, 0, {}, null, {}, tapBuffMultiplier(gp5, 1000)) === 3, 'tap value reflects the rush buff')
  const gp6 = defaultIdleState()
  gp6.golden = { id: 'dew', expiresAt: 99999 }
  const dew = resolveGoldenPrompt(gp6, true, 1000, 10)
  a(dew.granted === 10 * 3600 * 2, 'dew grants 2h of production instantly')
  a(pickGoldenPrompt(() => 0).id === 'gale' && pickGoldenPrompt(() => 0.99).id === 'rush', 'weighted pick is ordered')
  a(GOLDEN_PROMPTS.every(p => p.weight > 0), 'every prompt has weight')
  a(spawnGoldenPrompt(defaultIdleState(), 1000, Math.random, 0) === null, 'no golden prompt with zero production')
  const gp7 = defaultIdleState()
  spawnGoldenPrompt(gp7, 1000, () => 0.5)
  a(expireGoldenPrompt(gp7, 1000 + (GOLDEN_WINDOW_SEC + 1) * 1000) === true && gp7.golden === null, 'expired prompt auto-clears')
  a(expireGoldenPrompt(defaultIdleState(), 1000) === false, 'nothing to expire when none pending')
  // Figs
  const fg = defaultIdleState()
  a(!figReady(fg, 1000), 'no fig ready at start')
  a(plantFig(fg, 1000) === true && plantFig(fg, 2000) === false, 'plant once, not twice')
  const fgRipe = 1000 + FIG_RIPEN_HOURS * 3600 * 1000
  a(!figReady(fg, fgRipe - 1) && figReady(fg, fgRipe), 'fig ripens exactly at 20h')
  a(harvestFig(defaultIdleState(), 10, 1000) === 0, 'cannot harvest an unripe fig')
  const hres = harvestFig(fg, 10, fgRipe)
  a(hres === 10 * FIG_REWARD_HOURS * 3600 * (1 + FIG_LEVEL_BONUS), 'harvest grants hours x (1 + level bonus)')
  a(fg.figs.level === 1 && fg.figs.readyAt > fgRipe, 'harvest levels up and replants')
  a(Math.abs(figMultiplier({ level: 1 }) - 1.1) < 1e-9, 'fig level = +10%')
  a(figMultiplier({ level: 99 }) === 1 + FIG_MAX_LEVEL * FIG_LEVEL_BONUS, 'fig level caps at 10')
  const fgs = { ...defaultIdleState(), owned: { 0: 10 }, figs: { level: 5, readyAt: 0 } }
  a(statePerSecond(fgs, { 0: 1 }) > statePerSecond({ ...fgs, figs: { level: 0, readyAt: 0 } }, { 0: 1 }), 'statePerSecond includes the fig bonus')
  // Achievements → Shemen
  a(achievementsEarned(defaultIdleState()).length === 0, 'no achievements at start')
  const ach = defaultIdleState(); ach.owned = { 0: 1 }
  a(achievementsEarned(ach).some(x => x.id === 'first_letter'), 'first-letter achievement unlocks')
  a(Math.abs(shemenMultiplier(ach) - (1 + SHEMEN_PER_ACHIEVEMENT)) < 1e-9, 'one achievement = +4% Shemen')
  a(statePerSecond({ ...ach, owned: { 0: 10 } }, { 0: 1 }) === perSecond({ 0: 10 }, { 0: 1 }) * shemenMultiplier({ ...ach, owned: { 0: 10 } }), 'Shemen feeds statePerSecond')
  // Daily lesson
  const dl = defaultIdleState()
  a(!dailyReady(dl), 'daily not ready at start')
  for (let k = 0; k < DAILY_GOAL; k++) recordDailyCorrect(dl, 1000)
  a(dl.daily.correct === DAILY_GOAL, 'daily counts correct answers')
  a(dailyReady(dl, 1000), 'daily ready after 10 correct')
  a(claimDaily(dl, 10, 1000) === 10 * DAILY_REWARD_HOURS * 3600, 'daily grants 1h of production')
  a(claimDaily(dl, 10, 1000) === 0, 'daily claims once')
  recordDailyCorrect(dl, 1000 + 86400000)
  a(dl.daily.correct === 1 && !dl.daily.claimed, 'daily resets the next day')
  // Vineyard
  const vy = defaultIdleState()
  a(!vineReady(vy, 0, 1000), 'no vine ready at start')
  a(plantVineyard(vy, 1000) === VINE_COUNT && plantVineyard(vy, 2000) === 0, 'plant fills every empty slot once')
  const vyRipe = 1000 + VINE_RIPEN_HOURS * 3600 * 1000
  a(!vineReady(vy, 1, vyRipe - 1) && vineReady(vy, 1, vyRipe), 'vines ripen exactly at 4h, independently')
  a(harvestVine(defaultIdleState(), 0, 10, 1000) === 0, 'cannot harvest an unripe vine')
  const vres = harvestVine(vy, 0, 10, vyRipe)
  a(vres === 10 * VINE_REWARD_HOURS * 3600 * (1 + VINE_LEVEL_BONUS), 'harvest grants 15min x (1 + level bonus)')
  a(vy.vineyard.level === 1 && vy.vineyard.vines[0] > vyRipe && vineReady(vy, 1, vyRipe), 'harvest levels up, replants only that slot')
  a(Math.abs(vineyardMultiplier({ level: 2 }) - 1.1) < 1e-9, 'vineyard level = +5% each')
  a(vineyardMultiplier({ level: 99 }) === 1 + VINE_MAX_LEVEL * VINE_LEVEL_BONUS, 'vineyard level caps at 10 (1.5x)')
  const vys = { ...defaultIdleState(), owned: { 0: 10 }, vineyard: { level: 4, vines: [0, 0, 0] } }
  a(statePerSecond(vys, { 0: 1 }) > statePerSecond({ ...vys, vineyard: { level: 0, vines: [0, 0, 0] } }, { 0: 1 }), 'statePerSecond includes the vineyard bonus')
  const vyach = defaultIdleState(); vyach.vineyard = { level: 1, vines: [0, 0, 0] }
  a(achievementsEarned(vyach).some(x => x.id === 'vine1'), 'first-vine achievement unlocks')
  // Prophet's Choice
  const ph = defaultIdleState()
  a(spawnGoldenPrompt(ph, 1000, () => 0.05)?.id === 'prophet', 'low roll summons the Prophet')
  a(Array.isArray(ph.golden.options) && ph.golden.options.length === PROPHET_OPTIONS, 'prophet offers three blessings')
  a(new Set(ph.golden.options).size === PROPHET_OPTIONS, 'prophet blessings are distinct')
  const phRes = resolveGoldenPrompt(ph, true, 2000, 0)
  a(phRes.choice && phRes.choice.length === PROPHET_OPTIONS && ph.golden === null, 'correct answer opens the choice, prompt clears')
  const ph2 = defaultIdleState()
  spawnGoldenPrompt(ph2, 1000, () => 0.05)
  a(resolveGoldenPrompt(ph2, false, 2000, 0).fizzled === true, 'wrong answer fizzles the Prophet too')
  const manna = applyProphetChoice(defaultIdleState(), 'manna', 0)
  a(manna.granted === MANNA_KAVOD, 'manna grants instant Kavod')
  const dewChoice = applyProphetChoice(defaultIdleState(), 'dew', 10)
  a(dewChoice.granted === 10 * 3600 * 2, 'dew choice matches the dew prompt')
  const galeChoice = applyProphetChoice(defaultIdleState(), 'gale', 0, 1000)
  a(galeChoice.granted === 0, 'gale choice buffs instead of granting')
  const early = { ...defaultIdleState(), figs: { level: 0, readyAt: 100000 }, vineyard: { level: 0, vines: [100000, 0, 0] } }
  applyProphetChoice(early, 'early', 0)
  a(early.figs.readyAt === 100000 - EARLY_FIG_HOURS * 3600 * 1000 && early.vineyard.vines[0] === 100000 - EARLY_VINE_HOURS * 3600 * 1000, 'early harvest cuts both timers')
  a(applyProphetChoice(defaultIdleState(), 'bogus', 0).fizzled === true, 'unknown blessing fizzles')
  // Exile runs
  const ex = defaultIdleState()
  a(startExile(ex, [0, 1]) === false && !ex.exile, 'exile needs exactly three letters')
  a(startExile(ex, [0, 5, 21]) === true && ex.exile.letters.length === 3, 'vow locks three letters')
  a(startExile(ex, [2, 3, 4]) === false, 'cannot re-vow mid-exile')
  a(exileAllows(ex, 5) && !exileAllows(ex, 6), 'only the exiled three are buyable')
  a(exileAllows(defaultIdleState(), 20), 'no vow means every letter')
  const exRoll = rollExileLetters(() => 0)
  a(exRoll.length === 3 && new Set(exRoll).size === 3, 'rolled exile letters are distinct')
  a(exRoll[0] === 0, 'exile always carries Aleph (never a dead run)')
  const exK = defaultIdleState()
  startExile(exK, [0, 1, 2])
  const exCr = applyCorrectAnswer(exK, 0, () => 0.99)
  a(exCr.kavod === 2 && exK.kavod === 2, 'exile doubles Kavod (1 -> 2)')
  a(nextGoals(exK).gen.index !== undefined && exileAllows(exK, nextGoals(exK).gen.index), 'next goal never points at a locked letter')
  const exU = defaultIdleState()
  exU.owned = { 0: 10 }
  startExile(exU, [0, 1, 2])
  a(availableLetterUpgrades(exU, 0).length === 1 && availableLetterUpgrades(exU, 3).length === 0, 'upgrades respect the vow')
  exU.ohr = 1e9
  a(buyLetterUpgrade(exU, 3, 0) === false, 'cannot buy upgrades for locked letters')
  const exP = { ...defaultIdleState(), lifetimeOhr: 1e6, exile: { letters: [0, 1, 2], startedAt: 0 } }
  exP.ohr = 0
  applyPrestige(exP)
  a(!exP.exile && exP.exilesCompleted === 1, 'prestiging out completes the exile')
  const exAch = defaultIdleState(); exAch.exilesCompleted = 1
  a(achievementsEarned(exAch).some(x => x.id === 'vow1'), 'completed vow unlocks Covenant Keeper')
  // Shemittah
  const sh = defaultIdleState()
  a(startShemittah(sh, 1000) === true && sh.exile.kind === 'shemittah', 'shemittah vow takes hold')
  a(sh.lastVowPrestige === 0, 'vow records the prestige count')
  a(startShemittah(sh, 2000) === false && startExile(sh, [0, 1, 2]) === false, 'no second vow mid-vow')
  a(!exileAllows(sh, 0) && !exileAllows(sh, 21), 'shemittah locks every letter')
  a(shemittahTapMult(sh) === 2 && shemittahTapMult(defaultIdleState()) === 1, 'shemittah doubles taps, otherwise x1')
  const shTap = applyCorrectAnswer(sh, 0, () => 0.99)
  a(Math.abs(shTap.gained - 2.02) < 1e-9 && shTap.kavod === 1, 'shemittah doubles the tap but not the Kavod')
  const shP = { ...defaultIdleState(), lifetimeOhr: 1e6, exile: { kind: 'shemittah', startedAt: 0 } }
  shP.ohr = 0
  applyPrestige(shP)
  a(!shP.exile && shP.exilesCompleted === 1, 'prestiging out completes shemittah too')
  const shDone = defaultIdleState()
  startShemittah(shDone, 1000)
  a(checkShemittah(shDone, 1000 + SHEMITTAH_HOURS * 3600 * 1000 - 1) === false && !!shDone.exile, 'shemittah holds for its hour')
  a(checkShemittah(shDone, 1000 + SHEMITTAH_HOURS * 3600 * 1000) === true && !shDone.exile && shDone.exilesCompleted === 1, 'the rested hour completes the run')
  // Tiered + hidden achievements
  const tier = defaultIdleState(); tier.owned = { 0: 1000 }; tier.correct = 1000; tier.bestStreak = 50
  a(achievementsEarned(tier).some(x => x.id === 'own1000'), 'own-1000 tier unlocks')
  a(achievementsEarned(tier).some(x => x.id === 'correct1000'), 'correct-1000 tier unlocks')
  a(achievementsEarned(tier).some(x => x.id === 'streak50'), 'streak-50 tier unlocks')
  const soup = defaultIdleState(); soup.owned = Object.fromEntries(Array.from({ length: 10 }, (_, i) => [i, 1]))
  a(achievementsEarned(soup).some(x => x.id === 'breadth10'), 'ten studied letters unlocks the hidden breadth deed')
  const sharp = defaultIdleState(); sharp.crits = 50
  a(achievementsEarned(sharp).some(x => x.id === 'crit50'), 'fifty crits unlocks the hidden sharpshooter deed')
  const hoard = defaultIdleState(); hoard.lifetimeOhr = lifetimeForSpark(10)
  a(achievementsEarned(hoard).some(x => x.id === 'hoarder10'), 'ten held sparks unlocks the hidden patience deed')
  const hoard9 = defaultIdleState(); hoard9.lifetimeOhr = lifetimeForSpark(10) - 1
  a(!achievementsEarned(hoard9).some(x => x.id === 'hoarder10'), 'nine sparks is not patience')
  a(ACHIEVEMENTS.filter(x => x.hidden).length === 3 && ACHIEVEMENTS.length === 18, 'three hidden deeds among eighteen achievements')
  // Share card
  const sc = defaultIdleState(); sc.lifetimeOhr = 1234567; sc.roots = 3; sc.owned = { 0: 5 }; sc.bestStreak = 48
  const card = shareCard(sc)
  a(card.includes('EMET') && card.includes('3 roots') && card.includes('48'), 'share card carries the headline numbers')
  a(!shareCard(defaultIdleState()).includes('under vow'), 'no vow line when free')
  a(shareCard({ ...defaultIdleState(), exile: { kind: 'exile', letters: [0, 1, 2], startedAt: 0 } }).includes('under vow'), 'vow line invites others in')
  // Streak grace
  const gr = defaultIdleState()
  gr.streak = 4
  a(applyWrongAnswer(gr, 1000).graced === false && gr.streak === 0, 'short streaks still reset')
  gr.streak = 20
  const grRes = applyWrongAnswer(gr, 1000)
  a(grRes.graced === true && gr.streak === 10, 'grace halves a 10+ streak instead of resetting')
  a(applyWrongAnswer(gr, 2000).graced === false && gr.streak === 0, 'grace is once per day')
  const grNext = { ...gr, streak: 20 }
  applyWrongAnswer(grNext, 1000 + 86400000)
  a(grNext.streak === 10, 'grace renews the next day')
  // Vow expiry: no trap states
  const vx = defaultIdleState()
  startExile(vx, [0, 1, 2], 1000)
  a(vowReleased(vx, 1000 + VOW_MAX_HOURS * 3600 * 1000 - 1) === false && !!vx.exile, 'vow holds within 24h')
  a(vowReleased(vx, 1000 + VOW_MAX_HOURS * 3600 * 1000 + 1) === true && !vx.exile, 'vow releases after 24h')
  a(vx.exilesCompleted === 0, 'expiry releases uncounted (fizzle, not completion)')
  a(vowReleased(defaultIdleState(), 99999) === false, 'nothing to release when free')
}
