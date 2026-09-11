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

/**
 * Total Ohr/sec.
 * mastery: {letterIndex: 0..1} from curriculum; unstudied = 0.5x, never 0.
 * letterUpgrades: {`u${i}:${k}`: true} — ×2 tiers.
 * perm: {upgradeId: true} — permanent Kavod upgrades.
 */
export function perSecond(owned, mastery = {}, tracks = {}, words = 0, roots = 0, letterUpgrades = {}, perm = {}) {
  const readingMult = 1 + (tracks.reading || 0) * 0.10
  const global = globalMultiplier(roots, words, tracks) * (1 + permEffect(perm, 'globalMult'))
  let sum = 0
  for (let i = 0; i < LETTERS.length; i++) {
    const n = owned[i] || 0
    if (!n) continue
    const m = mastery[i] ?? 0
    sum += baseRate(i) * n * (0.5 + m) * letterMultiplier(letterUpgrades, i)
  }
  return sum * readingMult * global
}

/** Compose perSecond straight from game state (keeps call sites honest). */
export function statePerSecond(state, mastery = {}) {
  return perSecond(
    state.owned || {}, mastery, state.tracks || {}, state.words || 0, state.roots || 0,
    state.letterUpgrades || {}, state.perm || {},
  )
}

export function globalMultiplier(roots = 0, words = 0, tracks = {}) {
  // Roots +10% each (Realm RE), words +2% each (AdCap Angels).
  // Reading track intentionally excluded here (applied in perSecond) to avoid double-count.
  void tracks
  return (1 + roots * 0.10) * (1 + words * 0.02)
}

/** Tap value for one correct answer (× difficulty, × permanent upgrades). */
export function tapValue(perSec, streak = 0, tracks = {}, diff = null, perm = {}) {
  const { tapMult } = difficultyScalars(diff || {})
  const dikdukMult = 1 + (tracks.dikduk || 0) * 0.15
  const streakBonus = 1 + Math.min(streak, 100) * 0.01
  return (1 + 0.05 * perSec) * streakBonus * dikdukMult * tapMult * (1 + permEffect(perm, 'tapMult'))
}

/** Crit chance: 2% base + Niqqud + permanents, cap 20%. Crit = x7. */
export function critChance(tracks = {}, perm = {}) {
  return Math.min(0.02 + (tracks.niqqud || 0) * 0.02 + permEffect(perm, 'critAdd'), 0.2)
}

export function rollTap(perSec, streak, tracks = {}, rng = Math.random, diff = null, perm = {}) {
  const crit = rng() < critChance(tracks, perm)
  return { value: tapValue(perSec, streak, tracks, diff, perm) * (crit ? 7 : 1), crit }
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
    taps: 0,
    crits: 0,
    prestiges: 0,
    lastSeen: Date.now(),
    muted: false,
    difficulty: defaultDifficulty(),
    correct: 0,        // lifetime correct answers (quest + loop stats)
    kavod: 0,          // 🌟 learning currency: earned ONLY by correct answers, buys speed
    warps: 0,          // time warps purchased (escalates cost)
    buffs: { frenzyEndsAt: 0 },
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
  const { value, crit } = rollTap(perSec, streak, state.tracks, rng, state.difficulty, state.perm)
  // Kavod — the learning currency: 1 base, +1 per 5 streak, +3 on crit.
  // This is the ONLY way to buy speed. No money, no waiting shortcut.
  const kavod = 1 + Math.floor(streak / 5) + (crit ? 3 : 0)
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

export function applyWrongAnswer(state) {
  state.streak = 0
}

/** Prestige: reset Ohr + generators, keep roots/words/tracks. Returns roots gained. */
export function applyPrestige(state) {
  const target = rootsEarned(state.lifetimeOhr || 0)
  const gained = Math.max(0, target - (state.roots || 0))
  if (gained <= 0) return 0
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

/** Current buff multiplier (1 or FRENZY_MULT). Buffs expire on their own. */
export function buffMultiplier(state, now = Date.now()) {
  return (state.buffs?.frenzyEndsAt || 0) > now ? FRENZY_MULT : 1
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

/** Sum a numeric effect key across owned permanents. */
export function permEffect(perm = {}, key) {
  let total = 0
  for (const u of KAVOD_UPGRADES) {
    if (perm[u.id] && u.effect[key] !== undefined) total += u.effect[key]
  }
  return total
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
}
