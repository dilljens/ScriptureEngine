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
    taps: 0,
    crits: 0,
    prestiges: 0,
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
  const { value, crit } = rollTap(perSec, streak, state.tracks, rng, state.difficulty, state.perm, tapBuffMultiplier(state))
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
export const HEAVENLY_UPGRADES = [
  { id: 'h_legacy', name: 'Legacy of the Fathers', icon: '📜', cost: 1, desc: 'Every prestige starts with +1 of your first letter', effect: { seedLetter: 1 } },
  { id: 'h_light', name: 'Primordial Light', icon: '💡', cost: 2, desc: 'All Ohr +25%', effect: { globalMult: 0.25 } },
  { id: 'h_wisdom', name: 'Chochmah', icon: '🧠', cost: 3, desc: 'Tap power +50%', effect: { tapMult: 0.5 } },
  { id: 'h_rest', name: 'Shabbat Rest', icon: '🕯️', cost: 5, desc: 'Offline earnings +25%', effect: { offlineAdd: 0.25 } },
  { id: 'h_breath', name: 'Long Breath', icon: '🌬️', cost: 8, desc: 'Frenzy lasts +30s', effect: { frenzyBonusSec: 30 } },
  { id: 'h_key', name: 'Key of David', icon: '🗝️', cost: 13, desc: 'All Ohr +100%', effect: { globalMult: 1.0 } },
]

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

/** Chain gate: an upgrade unlocks only once the previous one is owned. */
export function heavenlyUnlocked(state, id) {
  const idx = HEAVENLY_UPGRADES.findIndex(u => u.id === id)
  if (idx < 0) return false
  return idx === 0 || heavenlyOwned(state, HEAVENLY_UPGRADES[idx - 1].id)
}

/** Buy a heavenly upgrade with sparks. Returns true on success. */
export function buyHeavenly(state, id) {
  const u = HEAVENLY_UPGRADES.find(x => x.id === id)
  if (!u || heavenlyOwned(state, id)) return false
  if (!heavenlyUnlocked(state, id)) return false
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
  { id: 'streak25', name: 'Unstoppable', icon: '🔥', desc: 'Reach a 25 streak', check: s => (s.bestStreak || 0) >= 25 },
  { id: 'correct100', name: 'Diligent', icon: '📖', desc: 'Answer 100 correctly', check: s => (s.correct || 0) >= 100 },
  { id: 'root1', name: 'First Fruits', icon: '🌿', desc: 'Forge your first root', check: s => (s.roots || 0) >= 1 },
  { id: 'prestige5', name: 'Reformed', icon: '🔄', desc: 'Prestige 5 times', check: s => (s.prestiges || 0) >= 5 },
  { id: 'fig1', name: 'Gardener', icon: '🍯', desc: 'Harvest your first fig', check: s => (s.figs?.level || 0) >= 1 },
  { id: 'vine1', name: 'Vinedresser', icon: '🍇', desc: 'Harvest your first vine', check: s => (s.vineyard?.level || 0) >= 1 },
  { id: 'spark1', name: 'Ascendant', icon: '💫', desc: 'Earn your first Aliyah spark', check: s => sparksEarned(s.lifetimeOhr || 0) >= 1 },
  { id: 'own22', name: 'Full Aleph-Bet', icon: '🔠', desc: 'Own every letter', check: s => LETTERS.every((_, i) => (s.owned?.[i] || 0) > 0) },
]

export function achievementsEarned(state) {
  return ACHIEVEMENTS.filter(a => { try { return a.check(state) } catch { return false } })
}

export function shemenMultiplier(state) {
  return 1 + achievementsEarned(state).length * SHEMEN_PER_ACHIEVEMENT
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
  a(heavenlyUnlocked(hs, 'h_legacy') && !heavenlyUnlocked(hs, 'h_light'), 'chain locked until previous owned')
  a(buyHeavenly(hs, 'h_light') === false, 'cannot skip the chain')
  a(buyHeavenly(hs, 'h_legacy') === true && heavenlyOwned(hs, 'h_legacy'), 'buy the first heavenly upgrade')
  a(availableSparks(hs) === 1, 'spending a spark reduces the live bonus')
  a(heavenlyUnlocked(hs, 'h_light'), 'chain unlocks after the previous is owned')
  hs.lifetimeOhr = 27 * ALIYAH_BASE // 3 earned, 3 spent → 0 available
  a(buyHeavenly(hs, 'h_light') === true && availableSparks(hs) === 0, 'buy the second once funded')
  a(permEffect(hs.perm, 'globalMult') === 0.25, 'heavenly effect feeds permEffect (no dropped modifier)')
  a(sparkBonus(0) === 1, 'no sparks = no bonus')
  a(sparkProgress(0).next === 1 && sparkProgress(0).pct === 0, 'spark progress starts at 1, 0%')
  a(sparkProgress(ALIYAH_BASE).earned === 1 && sparkProgress(ALIYAH_BASE).next === 2, 'spark progress advances')
  const sparkState = { ...defaultIdleState(), lifetimeOhr: 27 * ALIYAH_BASE, owned: { 0: 10 } }
  a(statePerSecond(sparkState, { 0: 1 }) > perSecond({ 0: 10 }, { 0: 1 }), 'statePerSecond includes the spark bonus')
  a(Math.abs(statePerSecond(sparkState, { 0: 1 }) - perSecond({ 0: 10 }, { 0: 1 }, {}, 0, 0, {}, {}, 3) * shemenMultiplier(sparkState)) < 1e-9, 'spark bonus is exactly +1% each')
  // Golden Prompts
  const gp = defaultIdleState()
  a(gp.golden === null && gp.nextGoldenAt === 0, 'no golden prompt at start')
  a(spawnGoldenPrompt(gp, 1000) !== null && !!gp.golden, 'first prompt spawns when due')
  a(goldenRemainingSec(gp, 1000) === GOLDEN_WINDOW_SEC, 'claim window is 20s')
  const gRes = resolveGoldenPrompt(gp, true, 2000, 0)
  a(gRes.claimed && !gRes.fizzled, 'correct answer claims the prompt')
  a(gp.golden === null && gp.nextGoldenAt > 2000, 'prompt cleared + next one scheduled')
  const gp2 = defaultIdleState()
  spawnGoldenPrompt(gp2, 1000)
  a(resolveGoldenPrompt(gp2, false, 2000, 0).fizzled === true, 'wrong answer fizzles')
  a(gp2.buffs.galeEndsAt === 0 && gp2.buffs.tapEndsAt === 0, 'fizzle grants nothing (no punishment)')
  const gp3 = defaultIdleState()
  spawnGoldenPrompt(gp3, 1000)
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
  spawnGoldenPrompt(gp7, 1000)
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
}
