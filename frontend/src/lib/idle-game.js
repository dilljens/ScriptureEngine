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

/** Spoken names for the Golden Prompt popup quiz (glyph → name, 3 options). */
export const LETTER_NAMES = [
  'Aleph', 'Bet', 'Gimel', 'Dalet', 'He', 'Vav', 'Zayin', 'Chet', 'Tet', 'Yod',
  'Kaf', 'Lamed', 'Mem', 'Nun', 'Samekh', 'Ayin', 'Pe', 'Tsade', 'Qof', 'Resh', 'Shin', 'Tav',
]

/** Traditional letter meanings (ox, house, camel…) for tooltips and teaching. */
export const LETTER_SYMBOLS = [
  'ox', 'house', 'camel', 'door', 'behold', 'hook', 'weapon', 'fence', 'serpent', 'hand',
  'palm', 'goad', 'water', 'fish', 'support', 'eye', 'mouth', 'fishhook', 'back of head', 'head', 'tooth', 'mark',
]

/** Standard gematria (mispar hechrechi): the numeric value of each letter. */
export const GEMATRIA = [
  1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400,
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

/** Cost of next generator given owned count. Cookie 1.15 law × difficulty × sages. */
export function generatorCost(i, owned, diff = null, costMult = 1) {
  const { costMult: diffMult } = difficultyScalars(diff || {})
  return Math.max(1, Math.ceil(baseCost(i) * Math.pow(1.15, owned) * diffMult * costMult))
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
 * masteredWords: mastered word objects ({bare}) for the word→letter bonus —
 *   each mastered word containing letter i lifts ONLY that letter's rate.
 * matureRoots: count of mature roots (word↔root synergy input).
 */
export function perSecond(owned, mastery = {}, tracks = {}, words = 0, roots = 0, letterUpgrades = {}, perm = {}, sparks = 0, masteredWords = [], matureRoots = 0) {
  const readingMult = 1 + (tracks.reading || 0) * 0.10
  const wordCount = Array.isArray(words) ? words.length : words
  const details = masteredWords.length ? masteredWords : (Array.isArray(words) ? words : [])
  const global = globalMultiplier(roots, wordCount, tracks, matureRoots) * (1 + permEffect(perm, 'globalMult'))
  let sum = 0
  for (let i = 0; i < LETTERS.length; i++) {
    const n = owned[i] || 0
    if (!n) continue
    const m = mastery[i] ?? 0
    sum += baseRate(i) * n * (0.5 + m) * letterMultiplier(letterUpgrades, i) * synergyMultiplier(owned, mastery, i) * letterWordMultiplier(i, details, mastery)
  }
  return sum * readingMult * global * sparkBonus(sparks)
}

/** Compose perSecond straight from game state (keeps call sites honest). */
export function statePerSecond(state, mastery = {}, gramMult = 1) {
  return perSecond(
    state.owned || {}, mastery, state.tracks || {}, state.words || 0, state.roots || 0,
    state.letterUpgrades || {}, state.perm || {}, availableSparks(state),
    state.masteredWords || [], matureRootCount(state),
  ) * figMultiplier(state.figs) * vineyardMultiplier(state.vineyard) * shemenMultiplier(state) * gramMult
    * sageEffects(state).global
}

/**
 * This letter's current Ohr/sec contribution — the exact term perSecond sums.
 * Powers the shop tile's "+X/s" effect preview (what buying more buys).
 */
export function letterRate(state = {}, mastery = {}, i = 0, gramMult = 1) {
  const n = (state.owned || {})[i] || 0
  if (!n) return 0
  const m = mastery[i] ?? 0
  const readingMult = 1 + ((state.tracks || {}).reading || 0) * 0.10
  const global = globalMultiplier(state.roots || 0, state.words || 0, state.tracks || {}, matureRootCount(state))
    * (1 + permEffect(state.perm || {}, 'globalMult'))
  const tail = figMultiplier(state.figs) * vineyardMultiplier(state.vineyard) * shemenMultiplier(state)
  return baseRate(i) * n * (0.5 + m) * letterMultiplier(state.letterUpgrades || {}, i)
    * synergyMultiplier(state.owned || {}, mastery, i)
    * letterWordMultiplier(i, state.masteredWords || [], mastery)
    * readingMult * global * sparkBonus(availableSparks(state)) * tail * gramMult
    * sageEffects(state).global
}

/** Per mature root: +5% to the word term (roots bootstrap vocabulary). */
export const WORD_ROOT_SYNERGY = 0.05
/** Per mastered word: +0.1% to the roots term (vocabulary feeds roots back). */
export const ROOT_WORD_SYNERGY = 0.001

export function globalMultiplier(roots = 0, words = 0, tracks = {}, matureRoots = 0) {
  // Roots +10% each (Realm RE), words +2% each (AdCap Angels).
  // Reading track intentionally excluded here (applied in perSecond) to avoid double-count.
  // Word↔root synergy (Cookie-Clicker Farm↔Time Machine pairs, linguistically
  // true both ways): each mature root lifts the WORD term +5%, and each
  // mastered word lifts the ROOTS term +0.1% — late game pulls early forward.
  void tracks
  const wordCount = Array.isArray(words) ? words.length : words
  return (1 + roots * 0.10) * (1 + wordCount * ROOT_WORD_SYNERGY)
    * (1 + wordCount * 0.02) * (1 + (matureRoots || 0) * WORD_ROOT_SYNERGY)
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
    masteredWords: [], // mastered word details [{bare, rank}] → per-letter bonus
    rootReps: {},    // root string -> {k: knows, s: skips} → mature roots
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
    quizDeck: null, // Anki-style daily quiz set {day, newLetters, due, seen, stats} — built on first quiz
    vineyard: { level: 0, vines: [0, 0, 0] }, // 3 parallel 4h tending timers (garden analogue)
    garden: { plots: [null, null, null, null, null, null] }, // Root Garden: 6 plots of growing roots
    sanhedrin: { seats: {}, cooldowns: {} }, // Seated sages (Honor/Wisdom/Learning) + swap cooldowns
    shuk: { holdings: {}, debtUntil: 0, loanCooldownUntil: 0 }, // market stalls + credit state
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
  const fx = sageEffects(state)
  const { value: raw, crit } = rollTap(perSec, streak, state.tracks, rng, state.difficulty, state.perm, tapBuffMultiplier(state))
  // Shemittah sprint: every tap counts double. Exile: Kavod doubles instead.
  // Seated sages tune both (Hillel/Shammai/Elijah taps, Akiva Kavod).
  const value = raw * shemittahTapMult(state) * fx.tap
  // Kavod — the learning currency: 1 base, +1 per 5 streak, +3 on crit.
  // This is the ONLY way to buy speed. No money, no waiting shortcut.
  // Exile runs pay double: fewer letters to study, faster Kavod, harder breadth.
  let kavod = 1 + Math.floor(streak / 5) + (crit ? 3 : 0)
  if (state.exile?.kind === 'exile') kavod = Math.round(kavod * EXILE_KAVOD_MULT)
  kavod = Math.max(1, Math.round(kavod * fx.kavod))
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
export function bulkCost(i, owned, n, diff = null, costMult = 1) {
  let t = 0
  for (let k = 0; k < n; k++) t += generatorCost(i, owned + k, diff, costMult)
  return t
}

/** Max affordable count + total spend (cap 1000 iterations). */
export function maxBuyable(i, owned, ohr, diff = null, costMult = 1) {
  let n = 0
  let spend = 0
  while (n < 1000) {
    const c = generatorCost(i, owned + n, diff, costMult)
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
  { id: 'own10', name: 'Minyan', desc: 'Own 10 generators — a prayer quorum of golems', goal: 10, reward: 300, progress: s => totalOwned(s) },
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

/** Current buff multiplier. Different KINDS multiply (the combo engine:
 * Frenzy × Gale × Shofar) — same kind refreshes, never double-counts.
 * Shuk debt (learning on credit) multiplies in as the one debuff. */
export function buffMultiplier(state, now = Date.now()) {
  const frenzy = (state.buffs?.frenzyEndsAt || 0) > now ? FRENZY_MULT : 1
  return frenzy * galeMultiplier(state, now) * shofarMultiplier(state, now) * shukDebt(state, now)
}

// ── Golden Prompts: quiz-gated buffs, accuracy windows, never reflex ──
// Cookie's golden cookie, but claimed by answering correctly within a window
// instead of clicking fast (DESIGN.md: no reflex gates). Wrong or late FIZZLES —
// nothing is ever drained (punishment ban).

export const GOLDEN_WINDOW_SEC = 30
export const GOLDEN_INTERVAL_SEC = [60, 180]

export const GOLDEN_PROMPTS = [
  { id: 'gale', name: 'Ruach Gale', icon: '🌪️', kind: 'mult', mult: 7, seconds: 77, weight: 3, desc: 'x7 Ohr for 77s' },
  { id: 'dew', name: 'Dew of Light', icon: '💧', kind: 'hours', hours: 2, weight: 2, desc: '2h of production, instantly' },
  { id: 'rush', name: 'Dikduk Rush', icon: '📖', kind: 'tap', tapMult: 3, seconds: 60, weight: 2, desc: 'x3 tap power for 60s' },
  { id: 'shofar', name: 'Shofar Blast', icon: '📯', kind: 'blast', seconds: 60, weight: 1, desc: 'workshop blast: production ×(1 + golems/20) for 60s' },
]

/** Bank rule (Cookie Lucky): Dew pays at most 2h, at least 15min, and scales
 * with the bank in between — hoarding Ohr pays. granted = min(2h·rate,
 * max(15min·rate, 15% of bank)). */
export const DEW_BANK_SHARE = 0.15
export const DEW_MIN_HOURS = 0.25
export function dewGrant(state, perSec) {
  const cap = (perSec || 0) * 3600 * ((GOLDEN_PROMPTS.find(p => p.id === 'dew') || {}).hours || 0)
  const floor = (perSec || 0) * 3600 * DEW_MIN_HOURS
  return Math.min(cap, Math.max(floor, (state.ohr || 0) * DEW_BANK_SHARE))
}

function goldenByKind(kind) {
  return GOLDEN_PROMPTS.find(p => p.kind === kind)
}

// ── Prophet's Choice: the rare pick-1-of-3 visitation ──────────────
// Golden Prompts are always-take surprises; the Prophet adds the one thing
// surprises lack — a decision. Three blessings, one choice, same 30s window,
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
  { id: 'shofar', name: 'Shofar Blast', icon: '📯', desc: 'workshop blast: production ×(1 + golems/20) for 60s' },
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
  if (id === 'gale' || id === 'rush' || id === 'shofar') {
    const p = goldenByKind(id === 'gale' ? 'mult' : id === 'rush' ? 'tap' : 'blast')
    const key = id === 'gale' ? 'galeEndsAt' : id === 'rush' ? 'tapEndsAt' : 'blastEndsAt'
    state.buffs = { ...(state.buffs || {}), [key]: now + p.seconds * 1000 }
    if (id === 'shofar') {
      const mult = 1 + totalOwned(state) / 20
      state.buffs.blastMult = mult
      return { claimed: { ...def(id), desc: `workshop blast: production ×${mult.toFixed(1)} for 60s` }, granted: 0 }
    }
    return { claimed: def(id), granted: 0 }
  }
  if (id === 'dew') {
    const granted = dewGrant(state, perSec)
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

/** Shofar Blast multiplier (1 when silent). */
export function shofarMultiplier(state, now = Date.now()) {
  if ((state.buffs?.blastEndsAt || 0) <= now) return 1
  return state.buffs?.blastMult || 1
}

/** How many production buffs are currently stacked (combo display). */
export function activeBuffCount(state, now = Date.now()) {
  return ((state.buffs?.frenzyEndsAt || 0) > now ? 1 : 0)
    + (galeMultiplier(state, now) > 1 ? 1 : 0)
    + (shofarMultiplier(state, now) > 1 ? 1 : 0)
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
export function spawnGoldenPrompt(state, now = Date.now(), rng = Math.random, perSec = 1, extra = {}) {
  if (state.golden) return null
  if (perSec <= 0) return null // nothing to multiply yet — never hand out a value-less prompt
  if (now < (state.nextGoldenAt || 0)) return null
  // Get Lucky (Cookie): while a production buff runs, the next visit comes
  // twice as fast — combos happen naturally to the prepared.
  const lucky = activeBuffCount(state, now) > 0 ? 0.5 : 1
  const scheduleNext = () => {
    const [lo, hi] = GOLDEN_INTERVAL_SEC
    state.nextGoldenAt = now + (lo + rng() * (hi - lo)) * 1000 * lucky
  }
  // Rare visitation: the Prophet offers a CHOICE of three blessings instead
  // of one fixed prompt — the surprise system with an actual decision in it.
  if (rng() < PROPHET_CHANCE) {
    const options = sampleBlessings(rng)
    state.golden = { id: 'prophet', expiresAt: now + GOLDEN_WINDOW_SEC * 1000, options, quiz: makeGoldenQuiz(state, rng, extra, now) }
    scheduleNext()
    return state.golden
  }
  const p = pickGoldenPrompt(rng)
  // Highest tier: word/root translation (EN↔HE) once 100 words + 100 roots
  // are known and grammar is studied. 90% reviews known words (due first),
  // 10% stretches into new ones; roots mix in at ROOT_QUIZ_SHARE.
  const topW = extra.topWords || []
  const topR = extra.topRoots || []
  const known = wordCandidates(state, topW, topR, extra.gramMastery || {}, extra.gramCategories || {})
  let quiz = null
  if (known.length && rng() < WORD_QUIZ_SHARE) {
    const kroots = knownRoots(state, topW, topR)
    if (kroots.length && rng() < ROOT_QUIZ_SHARE) {
      quiz = makeRootQuiz(kroots, topR, rng)
    } else {
      const deck = ensureQuizDeck(state, now)
      const stats = deck.wordStats || {}
      const freshW = known.filter(w => !stats[w.rank]?.seen)
      let pool = known
      if (freshW.length && rng() >= WORD_KNOWN_SHARE) pool = freshW
      else {
        const dueW = known.filter(w => stats[w.rank]?.seen && (stats[w.rank]?.due || 0) <= now)
        if (dueW.length) pool = dueW
      }
      quiz = makeWordQuiz(pool, rng, topW)
    }
  }
  if (!quiz) quiz = makeGoldenQuiz(state, rng, extra, now)
  state.golden = { id: p.id, expiresAt: now + GOLDEN_WINDOW_SEC * 1000, quiz }
  scheduleNext()
  return state.golden
}

/**
 * Build the popup quiz for a Golden Prompt: 6 options, three question types.
 * - name:  shown the GLYPH, pick its transliterated name (recognition, easiest)
 * - glyph: shown the NAME, pick the actual glyph (recall, harder)
 * - audio: hear the letter, pick the glyph (listening, hardest — no visual cue)
 * Anki-style daily deck: each day brings QUIZ_NEW_PER_DAY unseen letters plus
 * reviews due from spaced repetition; correct answers stretch the interval
 * (1d → 3d → 7d → 14d), wrong answers come back in 10 minutes.
 * Adaptive: struggling players (bias > 0) get name questions on high-mastery
 * letters; cruising players get glyph/audio on weak letters with confusable
 * foils. Never repeats the previous letter while alternatives exist.
 * Pure data — the HUD renders and answers it.
 */
export const QUIZ_OPTIONS = 6
export const QUIZ_NEW_PER_DAY = 3
export const QUIZ_REVIEW_DAYS = [1, 3, 7, 14]
export const QUIZ_WRONG_MIN = 10
// Mirrors the curriculum confusability seed (hebrew_confusability): pairs
// learners actually mix up. Hard-mode foils come from here first.
export const CONFUSABLES = {
  0: [15], 15: [0],   // aleph / ayin
  1: [5], 5: [1],     // bet / vav
  4: [7], 7: [4],     // he / chet
  8: [21], 21: [8],   // tet / tav
  14: [20], 20: [14], // samekh / shin
}

export function ensureQuizDeck(state, now = Date.now(), rng = Math.random) {
  const day = dayKey(now)
  if (state.quizDeck && state.quizDeck.day === day) return state.quizDeck
  // New day: carry reviews (due map + per-letter streaks), deal fresh letters.
  const prev = state.quizDeck
  const due = { ...(prev?.due || {}) }
  const stats = { ...(prev?.stats || {}) }
  const seen = new Set([...Object.keys(due).map(Number), ...Object.keys(stats).map(Number)]);
  const fresh = []
  for (let i = 0; i < LETTERS.length && fresh.length < QUIZ_NEW_PER_DAY; i++) {
    if (!seen.has(i)) fresh.push(i)
  }
  state.quizDeck = {
    day, newLetters: fresh, due, stats,
    wordStats: { ...(prev?.wordStats || {}) },
    rootStats: { ...(prev?.rootStats || {}) },
    reviewedToday: 0,
  }
  return state.quizDeck
}

/** File one quiz answer into the spaced-repetition deck. */
export function recordGoldenAnswer(state, letter, correct, now = Date.now()) {
  const d = ensureQuizDeck(state, now)
  d.reviewedToday = (d.reviewedToday || 0) + 1
  d.newLetters = (d.newLetters || []).filter(x => x !== letter)
  if (correct) {
    const streak = (d.stats[letter] || 0) + 1
    d.stats[letter] = streak
    const step = QUIZ_REVIEW_DAYS[Math.min(streak - 1, QUIZ_REVIEW_DAYS.length - 1)]
    d.due[letter] = now + step * 86400000
  } else {
    d.stats[letter] = 0
    d.due[letter] = now + QUIZ_WRONG_MIN * 60000
  }
  return d
}

/**
 * Word/root answers feed their own SRS tracks (per-rank / per-root streaks).
 * Correct stretches the interval, wrong returns in 10 minutes — partial
 * correctness is exactly what the deck records: every word and root carries
 * its own streak, so strong words graduate while weak ones keep coming back.
 */
export function recordWordAnswer(state, rank, correct, now = Date.now()) {
  const d = ensureQuizDeck(state, now)
  d.reviewedToday = (d.reviewedToday || 0) + 1
  d.wordStats = d.wordStats || {}
  const s = d.wordStats[rank] || { streak: 0, due: 0, seen: 0 }
  s.seen += 1
  if (correct) {
    s.streak += 1
    const step = QUIZ_REVIEW_DAYS[Math.min(s.streak - 1, QUIZ_REVIEW_DAYS.length - 1)]
    s.due = now + step * 86400000
  } else {
    s.streak = 0
    s.due = now + QUIZ_WRONG_MIN * 60000
  }
  d.wordStats[rank] = s
  return d
}

export function recordRootAnswer(state, root, correct, now = Date.now()) {
  const d = ensureQuizDeck(state, now)
  d.reviewedToday = (d.reviewedToday || 0) + 1
  d.rootStats = d.rootStats || {}
  const s = d.rootStats[root] || { streak: 0, due: 0, seen: 0 }
  s.seen += 1
  if (correct) {
    s.streak += 1
    const step = QUIZ_REVIEW_DAYS[Math.min(s.streak - 1, QUIZ_REVIEW_DAYS.length - 1)]
    s.due = now + step * 86400000
  } else {
    s.streak = 0
    s.due = now + QUIZ_WRONG_MIN * 60000
  }
  d.rootStats[root] = s
  return d
}

export function makeGoldenQuiz(state, rng = Math.random, extra = {}, now = Date.now()) {
  const d = ensureQuizDeck(state, now, rng)
  const { mastery = {}, bias = 0 } = extra
  const dueNow = Object.keys(d.due || {}).map(Number).filter(l => d.due[l] <= now)
  const fresh = [...(d.newLetters || [])]
  let pool = [...dueNow, ...fresh]
  // Never quiz the same letter twice in a row while alternatives exist.
  if (pool.length > 1 && pool.includes(state.lastQuizLetter)) {
    pool = pool.filter(l => l !== state.lastQuizLetter)
  }
  if (!pool.length) {
    for (let i = 0; i < LETTERS.length; i++) {
      if ((state?.owned?.[i] || 0) > 0) pool.push(i)
    }
  }
  if (!pool.length) for (let i = 0; i < LETTERS.length; i++) pool.push(i)
  const m = l => mastery[l] || 0
  let letter
  if (bias > 0.05) letter = pool.reduce((a, b) => (m(a) >= m(b) ? a : b))
  else if (bias < -0.05) letter = pool.reduce((a, b) => (m(a) <= m(b) ? a : b))
  else letter = pool[Math.floor(rng() * pool.length)]
  // Foils: hard mode leads with the target's confusables, then rng, then a
  // deterministic walk (a constant test seed must never spin forever).
  const hard = bias < -0.05
  const options = [letter]
  if (hard) {
    for (const cand of CONFUSABLES[letter] || []) {
      if (options.length >= QUIZ_OPTIONS) break
      if (!options.includes(cand)) options.push(cand)
    }
  }
  let guard = 0
  while (options.length < QUIZ_OPTIONS && guard++ < 200) {
    const cand = Math.floor(rng() * LETTERS.length)
    if (!options.includes(cand)) options.push(cand)
  }
  for (let k = 1; options.length < QUIZ_OPTIONS; k++) {
    const cand = (letter + k) % LETTERS.length
    if (!options.includes(cand)) options.push(cand)
  }
  // Fisher–Yates with the same rng (deterministic under test seeds).
  for (let i = options.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[options[i], options[j]] = [options[j], options[i]]
  }
  // Question type follows the same adaptivity: recognition when struggling,
  // recall or listening when cruising. The HUD upgrades glyph→audio only if
  // the letter audio actually loads; otherwise the name stays visible.
  let qtype
  const r = rng()
  if (bias > 0.05) qtype = 'name'
  else if (bias < -0.05) qtype = r < 0.5 ? 'glyph' : 'audio'
  else qtype = r < 0.4 ? 'name' : r < 0.7 ? 'glyph' : 'audio'
  state.lastQuizLetter = letter
  return { kind: 'letter', letter, options, qtype }
}

// ── Word/root tier: EN↔HE translation from the top-500 ───────────────────
// Unlock: 100 known words + 100 known roots + studied grammar. A word is
// known when every letter is owned (readable); a root is known when 2+ of
// its example words are known. Past the gate, 90% of questions review known
// words (due first) and 10% stretch into new ones. Judged by exact match —
// deterministic, offline, instant; no LLM judge.

export const WORD_KNOWN_TARGET = 100
export const ROOT_KNOWN_TARGET = 100
export const WORD_KNOWN_SHARE = 0.9
export const WORD_QUIZ_SHARE = 0.35
export const ROOT_QUIZ_SHARE = 0.15
const FINAL_TO_BASE = { 'ך': 11, 'ם': 12, 'ן': 13, 'ף': 16, 'ץ': 17 }

// ── Word→letter gains + Anki-style word mastery ──────────────────────────
// Compared against Anki 26.08.1 (/usr/bin/anki): Anki has no "mastered" flag —
// mastery IS interval. Cards with interval >= 21d are "mature" in Anki stats.
// A word tile is mastered when its FSRS interval_days reaches 21. Mastered
// words then pay points to their letters: each mastered word containing
// letter i gives that letter +2% (cap +200%), but ONLY once the letter
// itself is mastered (mastery >= 0.8) — words extend mastered letters.

/** Anki "mature" threshold in days — matches backend WORD_MATURE_INTERVAL_DAYS. */
export const WORD_MATURE_INTERVAL_DAYS = 21
/** Per mastered word containing the letter: +2% to that letter's rate. */
export const WORD_LETTER_BONUS = 0.02
/** Ceiling on the word→letter bonus: +200%. */
export const WORD_LETTER_CAP = 2.0

/** Anki-style check: mastered = interval until next review reached maturity. */
export function isWordMastered(word) {
  if (!word) return false
  if (typeof word.mastered === 'boolean') return word.mastered
  return (word.interval_days || 0) >= WORD_MATURE_INTERVAL_DAYS
}

// ── Word tiers: frequency rank → curriculum level ───────────────────────
// The 500-word list spreads across levels so Word Tiles decks unlock in
// stages (Cookie-Clicker building tiers): Shema 0-49 → L4, Daily 50-149 →
// L5, Prophets 150-299 → L6, Writings/Rare 300+ → L7. Single source of
// truth shared by the seeder (fresh DBs) and the tier migration (existing).
export function wordTier(rank) {
  const r = Number(rank) || 0
  if (r < 50) return 4
  if (r < 150) return 5
  if (r < 300) return 6
  return 7
}

/** Letter indices appearing in a word's bare (unpointed) form. */
export function wordLetterIndices(bare = '') {
  const out = []
  for (const ch of bare || '') {
    let idx = LETTERS.indexOf(ch)
    if (idx < 0 && FINAL_TO_BASE[ch] !== undefined) idx = FINAL_TO_BASE[ch]
    if (idx < 0 || out.includes(idx)) continue
    out.push(idx)
  }
  return out
}

/** Count mastered words per letter index: {letterIndex: count}. */
export function countWordLetters(masteredWords = []) {
  const counts = {}
  for (const w of masteredWords || []) {
    if (!w || !w.bare) continue
    for (const i of wordLetterIndices(w.bare)) counts[i] = (counts[i] || 0) + 1
  }
  return counts
}

/**
 * This letter's word bonus. Gated: unmastered letters get ×1 — words extend
 * mastered letters, they don't shortcut them.
 */
export function letterWordMultiplier(i, masteredWords = [], mastery = {}) {
  if ((mastery[i] ?? 0) < MASTERY_THRESHOLD) return 1
  let hits = 0
  for (const w of masteredWords || []) {
    if (!w || !w.bare) continue
    if (wordLetterIndices(w.bare).includes(i)) hits++
  }
  return 1 + Math.min(hits * WORD_LETTER_BONUS, WORD_LETTER_CAP)
}

/**
 * Sync mastered-word details into idle state from a Word Tiles fetch.
 * Keeps state.words (count → global +2%/word) and state.masteredWords
 * (per-letter details → +2%/letter) consistent. Returns counts for the HUD.
 * # ponytail: stores bare forms only; upgrade path is node_id-keyed rows when
 * the vocab SRS covers all 500 words.
 */
export function syncMasteredWords(state, words = []) {
  const mastered = (words || []).filter(isWordMastered).map(w => ({ bare: w.bare, rank: w.rank }))
  state.masteredWords = mastered
  state.words = mastered.length
  return { words: mastered.length, perLetter: countWordLetters(mastered) }
}

// ── Roots tier: self-graded study + staged deck gates ───────────────────
// Roots mature by study reps (3 net knows), not FSRS — per-root FSRS nodes
// cover only 17/500 roots, so invented intervals would lie. Upgrade path:
// per-root review_state rows when root_* coverage reaches 100+.

/** Net knows needed for a root to count as mature (feeds word synergy). */
export const ROOT_MATURE_REPS = 3
/** Word decks 3+ (ranks 150+) need 10 mastered words; decks 6+ (300+) need 40. */
export const WORD_DECK_GATES = { 3: 10, 6: 40 }
/** Roots Tiles screen needs 25 mastered words. */
export const ROOTS_TILES_GATE = 25

/** Record one self-graded root study rep. Returns {knows, mature}. */
export function recordRootStudy(state, root, known) {
  if (!root) return { knows: 0, mature: false }
  const reps = state.rootReps || (state.rootReps = {})
  const r = reps[root] || (reps[root] = { k: 0, s: 0 })
  if (known) r.k++
  else r.s++
  const mature = (r.k - r.s) >= ROOT_MATURE_REPS
  return { knows: r.k - r.s, mature }
}

/** Count of mature roots in idle state (word↔root synergy input). */
export function matureRootCount(state) {
  let n = 0
  for (const r of Object.values(state.rootReps || {})) {
    if ((r.k - r.s) >= ROOT_MATURE_REPS) n++
  }
  return n
}

/** Word deck d (0-indexed, 50/deck) unlocked with this many mastered words. */
export function wordDeckUnlocked(deckIdx, masteredTotal) {
  let need = 0
  for (const [d, g] of Object.entries(WORD_DECK_GATES)) {
    if (deckIdx >= Number(d)) need = Math.max(need, g)
  }
  return (masteredTotal || 0) >= need
}

/** Letters of a bare word that the workshop does NOT own yet. */
export function wordLockedLetters(word, owned = {}) {
  const missing = []
  for (const ch of word.bare || '') {
    let idx = LETTERS.indexOf(ch)
    if (idx < 0 && FINAL_TO_BASE[ch] !== undefined) idx = FINAL_TO_BASE[ch]
    if (idx < 0) continue // punctuation/unknown — never blocks
    if (!(owned[idx] > 0) && !missing.includes(idx)) missing.push(idx)
  }
  return missing
}

/** Top-500 words the player currently knows (readable = all letters owned). */
export function knownWords(state, topWords = []) {
  const owned = state.owned || {}
  return topWords.filter(w => w.bare && w.gloss && wordLockedLetters(w, owned).length === 0)
}

function rankSet(topWords) {
  const m = {}
  for (const w of topWords || []) m[w.lemma] = w.rank
  return m
}

/** Roots with 2+ known example words (examples resolved through top-500 ranks). */
export function knownRoots(state, topWords = [], topRoots = []) {
  const known = new Set(knownWords(state, topWords).map(w => w.rank))
  const byRank = rankSet(topWords)
  const out = []
  for (const r of topRoots || []) {
    const hits = (r.examples || []).filter(l => known.has(byRank[l])).length
    if (hits >= 2) out.push(r)
  }
  return out
}

/** Grammar studied: mastered grammar/syntax/verb curriculum nodes. */
export function grammarStudied(mastery = {}, categories = {}) {
  let n = 0
  for (const [k, v] of Object.entries(mastery)) {
    const c = categories[k]
    if ((c === 'grammar' || c === 'syntax' || c === 'verb') && (v || 0) >= 0.8) n++
  }
  return n
}

// ── Grammar tracks: 3 rows × 5 tiers, derived (no migration) ───────────
// verb → binyanim, syntax → clauses, noun+grammar → nominals. Tier follows
// node level (L3→1 … L7→5). A tier is complete when it has ≥1 node and every
// node is mastered; each complete tier pays +5% global (cap +50%, CC CpS%
// cookies). Empty cells are the content backlog — visible, not hidden.

/** Category → grammar track (null = not a grammar node). */
export const GRAMMAR_TRACKS = { verb: 'binyanim', syntax: 'clauses', noun: 'nominals', grammar: 'nominals' }
/** Per complete track-tier: +5% global Ohr. */
export const TRACK_BONUS_PER_TIER = 0.05
/** Ceiling on track income: +50%. */
export const TRACK_BONUS_CAP = 0.5

/** {track, tier} for a curriculum node, or null. */
export function grammarTrack(node) {
  if (!node) return null
  const track = GRAMMAR_TRACKS[node.category]
  if (!track) return null
  const tier = Math.min(5, Math.max(1, (node.level || 3) - 2))
  return { track, tier }
}

/**
 * Track grid + income from curriculum nodes.
 * Returns {bonus, complete, grid, backlog}: grid[track][tier] =
 * {total, mastered, ids}; backlog = [{track, tier, reason}] for incomplete
 * cells ('unfinished') and never-seeded cells ('empty' = content backlog).
 */
export function grammarTrackBonus(nodes = []) {
  const grid = {}
  for (const n of nodes || []) {
    const t = grammarTrack(n)
    if (!t) continue
    const cell = ((grid[t.track] ||= {})[t.tier] ||= { total: 0, mastered: 0, ids: [] })
    cell.total++
    if ((n.mastery || 0) >= MASTERY_THRESHOLD) cell.mastered++
    cell.ids.push(n.id)
  }
  let complete = 0
  const backlog = []
  for (const track of Object.keys(GRAMMAR_TRACKS).map(c => GRAMMAR_TRACKS[c]).filter((v, i, a) => a.indexOf(v) === i)) {
    for (let tier = 1; tier <= 5; tier++) {
      const cell = grid[track]?.[tier]
      if (!cell) backlog.push({ track, tier, reason: 'empty' })
      else if (cell.mastered >= cell.total) complete++
      else backlog.push({ track, tier, reason: 'unfinished', done: cell.mastered, total: cell.total })
    }
  }
  return { bonus: Math.min(complete * TRACK_BONUS_PER_TIER, TRACK_BONUS_CAP), complete, grid, backlog }
}

/** Tier gate: 100 known words + 100 known roots + studied grammar. */
export function translationUnlocked(state, topWords = [], topRoots = [], mastery = {}, categories = {}) {
  return knownWords(state, topWords).length >= WORD_KNOWN_TARGET
    && knownRoots(state, topWords, topRoots).length >= ROOT_KNOWN_TARGET
    && grammarStudied(mastery, categories) >= 1
}

/** Translation candidates: 90% known words (the known set passed in). */
export function wordCandidates(state, topWords = [], topRoots = [], mastery = {}, categories = {}) {
  if (!translationUnlocked(state, topWords, topRoots, mastery, categories)) return []
  return knownWords(state, topWords)
}

/** EN→HE or HE→EN choice quiz, 6 single-script options, exact-match judged. */
export function makeWordQuiz(candidates, rng = Math.random, foilPool = []) {
  const word = candidates[Math.floor(rng() * candidates.length)]
  const direction = rng() < 0.5 ? 'en-he' : 'he-en'
  const answer = direction === 'en-he' ? word.hebrew : word.gloss
  // Foils come from the full word list (locked words make fine wrong answers),
  // so a small unlocked set can never starve the option count.
  const foils = (foilPool.length ? foilPool : candidates).filter(w => w.rank !== word.rank)
  const options = [answer]
  let guard = 0
  while (options.length < QUIZ_OPTIONS && guard++ < 300) {
    const cand = foils[Math.floor(rng() * foils.length)]
    if (!cand) break
    const val = direction === 'en-he' ? cand.hebrew : cand.gloss
    if (val && !options.includes(val)) options.push(val)
  }
  // Deterministic fill over distinct foil values (constant seeds terminate).
  const seenVals = new Set(options)
  for (const cand of foils) {
    if (options.length >= QUIZ_OPTIONS) break
    const val = direction === 'en-he' ? cand.hebrew : cand.gloss
    if (val && !seenVals.has(val)) { seenVals.add(val); options.push(val) }
  }
  // Last resort (degenerate pool): repeat-proof numbered suffix on the answer
  // script — terminates unconditionally, never mixes scripts.
  for (let k = 2; options.length < QUIZ_OPTIONS; k++) {
    const val = `${answer} (${k})`
    if (!seenVals.has(val)) { seenVals.add(val); options.push(val) }
  }
  for (let i = options.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[options[i], options[j]] = [options[j], options[i]]
  }
  return { kind: 'word', direction, hebrew: word.hebrew, bare: word.bare, gloss: word.gloss, rank: word.rank, translit: word.translit || word.transliteration || '', options, answer }
}

/** Root↔gloss choice quiz from known roots (same 6-option, exact-match shape). */
export function makeRootQuiz(knownR, allRoots = [], rng = Math.random) {
  const root = knownR[Math.floor(rng() * knownR.length)]
  const direction = rng() < 0.5 ? 'en-he' : 'he-en'
  const answer = direction === 'en-he' ? root.root : root.gloss
  const foils = (allRoots.length ? allRoots : knownR).filter(r => r.root !== root.root)
  const options = [answer]
  let guard = 0
  while (options.length < QUIZ_OPTIONS && guard++ < 300) {
    const cand = foils[Math.floor(rng() * foils.length)]
    if (!cand) break
    const val = direction === 'en-he' ? cand.root : cand.gloss
    if (val && !options.includes(val)) options.push(val)
  }
  const seenVals = new Set(options)
  for (const cand of foils) {
    if (options.length >= QUIZ_OPTIONS) break
    const val = direction === 'en-he' ? cand.root : cand.gloss
    if (val && !seenVals.has(val)) { seenVals.add(val); options.push(val) }
  }
  for (let k = 2; options.length < QUIZ_OPTIONS; k++) {
    const val = `${answer} (${k})`
    if (!seenVals.has(val)) { seenVals.add(val); options.push(val) }
  }
  for (let i = options.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[options[i], options[j]] = [options[j], options[i]]
  }
  return { kind: 'root', direction, root: root.root, gloss: root.gloss, options, answer }
}

/**
 * Answer the popup quiz. Correct inside the window → buff (or Prophet
 * choice); wrong or expired → fizzle, nothing lost. Same reward shape as
 * resolveGoldenPrompt so the HUD treats both alike.
 */
export function answerGoldenQuiz(state, choiceIdx, now = Date.now(), perSec = 0) {
  const g = state.golden
  if (!g) return null
  const expired = now > g.expiresAt
  const quiz = g.quiz
  const answer = quiz ? (quiz.answer ?? quiz.letter) : undefined
  const correct = !expired && quiz && quiz.options[choiceIdx] === answer
  state.golden = null
  if (expired) return { fizzled: true, reason: 'expired' }
  // Letter quizzes feed the letter deck; words and roots feed their own SRS
  // tracks — partial correctness is the point: strong items graduate while
  // weak ones keep coming back, each on its own streak.
  if (quiz) {
    if (quiz.kind === 'word' && quiz.rank) recordWordAnswer(state, quiz.rank, !!correct, now)
    else if (quiz.kind === 'root' && quiz.root) recordRootAnswer(state, quiz.root, !!correct, now)
    else if (typeof quiz.letter === 'number') recordGoldenAnswer(state, quiz.letter, !!correct, now)
  }
  if (!correct) return { fizzled: true, reason: 'wrong' }
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
  if (p.kind === 'hours') {
    const granted = perSec * 3600 * (p.hours || 0)
    state.ohr += granted
    state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
    return { claimed: p, granted }
  }
  return { fizzled: true, reason: 'unknown' }
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
  if (p.kind === 'blast') {
    // Binyan Special (Cookie Building Special): the bigger the workshop,
    // the louder the blast. Stacks WITH gale/frenzy (combo engine).
    const mult = 1 + totalOwned(state) / 20
    state.buffs = { ...(state.buffs || {}), blastEndsAt: now + p.seconds * 1000, blastMult: mult }
    return { claimed: { ...p, desc: `workshop blast: production ×${mult.toFixed(1)} for 60s` }, granted: 0 }
  }
  const granted = dewGrant(state, perSec)
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

// ── Root Garden: the first minigame (Cookie-Clicker Garden, Hebrew soil) ─
// 6 plots. Plant a readable root for 15min of production; 2h growth through
// sprout→bud→mature; harvest grants 30min production + 5 Kavod + 1 study rep
// for the root (reps mature roots → +5% word income each, Track B3).
// Cross-breed: harvesting beside a DIFFERENT mature root has a 25% mutation:
// +15 Kavod and a rep for the neighbor root too. No wither, no rot — the
// game never punishes (Ohr = wait, Kavod = know; planting costs only Ohr).

export const GARDEN_PLOTS = 6
export const GARDEN_GROW_MS = 2 * 3600 * 1000
export const GARDEN_COST_HOURS = 0.25
export const GARDEN_REWARD_HOURS = 0.5
export const GARDEN_KAVOD = 5
export const GARDEN_MUTATION_CHANCE = 0.25
export const GARDEN_MUTATION_KAVOD = 15

/** Plot array (length 6): null | {root, plantedAt}. */
export function gardenPlots(state) {
  const plots = [...(state.garden?.plots || [])]
  while (plots.length < GARDEN_PLOTS) plots.push(null)
  return plots.slice(0, GARDEN_PLOTS)
}

/** Growth stage 0 (sprout) / 1 (bud) / 2 (mature) by elapsed thirds. */
export function gardenStage(plot, now = Date.now()) {
  if (!plot) return -1
  const el = now - (plot.plantedAt || 0)
  if (el >= GARDEN_GROW_MS) return 2
  if (el >= GARDEN_GROW_MS / 3 * 2) return 1
  return 0
}

export function gardenReady(state, i, now = Date.now()) {
  return gardenStage(gardenPlots(state)[i], now) === 2
}

/** Adjacent plot indices in the 3×2 grid (no wraparound). */
export function gardenNeighbors(i) {
  const out = []
  const row = Math.floor(i / 3), col = i % 3
  if (col > 0) out.push(i - 1)
  if (col < 2) out.push(i + 1)
  if (row > 0) out.push(i - 3)
  if (row < 1) out.push(i + 3)
  return out
}

/** Roots the workshop can read (every letter owned). Accepts strings or {root}. */
export function readableRoots(owned = {}, roots = []) {
  return (roots || []).filter(r => {
    const s = typeof r === 'string' ? r : r.root
    if (!s) return false
    const idx = wordLetterIndices(s)
    return idx.length > 0 && idx.every(j => (owned[j] || 0) > 0)
  })
}

/** Plant a root: costs 15min of production. Returns false if occupied/unaffordable. */
export function plantGardenRoot(state, i, root, perSec, now = Date.now()) {
  if (!root || i < 0 || i >= GARDEN_PLOTS) return false
  const plots = gardenPlots(state)
  if (plots[i]) return false
  const cost = (perSec || 0) * GARDEN_COST_HOURS * 3600
  if ((state.ohr || 0) < cost) return false
  state.ohr -= cost
  plots[i] = { root, plantedAt: now }
  state.garden = { ...(state.garden || {}), plots }
  return true
}

/**
 * Harvest a mature plot. Grants production + Kavod + a study rep for the
 * root; adjacent different mature roots may mutate (+Kavod, rep for the
 * neighbor). Clears the plot. Returns null unless mature.
 */
export function harvestGardenRoot(state, i, perSec, now = Date.now(), rng = Math.random) {
  const plots = gardenPlots(state)
  const plot = plots[i]
  if (gardenStage(plot, now) !== 2) return null
  const granted = (perSec || 0) * GARDEN_REWARD_HOURS * 3600
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  let kavod = GARDEN_KAVOD
  let mutated = false
  let neighbor = null
  for (const j of gardenNeighbors(i)) {
    const nb = plots[j]
    if (nb && nb.root !== plot.root && gardenStage(nb, now) === 2) { neighbor = nb.root; break }
  }
  if (neighbor && rng() < GARDEN_MUTATION_CHANCE) {
    mutated = true
    kavod += GARDEN_MUTATION_KAVOD
    recordRootStudy(state, neighbor, true)
  }
  recordRootStudy(state, plot.root, true)
  state.kavod = (state.kavod || 0) + kavod
  plots[i] = null
  state.garden = { ...(state.garden || {}), plots }
  return { granted, kavod, mutated, neighbor: mutated ? neighbor : null, root: plot.root }
}

// ── Sanhedrin: the second minigame (Cookie-Clicker Pantheon, sages) ────
// Seat three sages out of six. Seats scale the effect (Honor ×1.0, Wisdom
// ×0.6, Learning ×0.3); every sage has a gift and a price, so the loadout
// is buildcraft, not a checklist. Swapping a seat starts a 4h cooldown on
// that seat. Effects flow through sageEffects(state) into production, costs,
// taps, Kavod, offline and Shemen — one choke point, no signature sprawl.

export const SANHEDRIN_SEATS = [
  { id: 'honor', name: 'Seat of Honor', mult: 1.0 },
  { id: 'wisdom', name: 'Seat of Wisdom', mult: 0.6 },
  { id: 'learning', name: 'Seat of Learning', mult: 0.3 },
]
export const SAGE_SWAP_COOLDOWN_MS = 4 * 3600 * 1000
export const SAGES = [
  { id: 'rashi', name: 'Rashi', icon: '📖', desc: '+10% Ohr · +10% letter costs', fx: { global: 0.10, cost: 0.10 } },
  { id: 'hillel', name: 'Hillel', icon: '🕊️', desc: '+15% tap value · −5% Ohr', fx: { tap: 0.15, global: -0.05 } },
  { id: 'shammai', name: 'Shammai', icon: '⚖️', desc: '−10% letter costs · −5% tap value', fx: { cost: -0.10, tap: -0.05 } },
  { id: 'akiva', name: 'Akiva', icon: '🔥', desc: '+20% Kavod from answers · −5% Ohr', fx: { kavod: 0.20, global: -0.05 } },
  { id: 'miriam', name: 'Miriam', icon: '🌊', desc: '+15% Shemen effect · +5% letter costs', fx: { milk: 0.15, cost: 0.05 } },
  { id: 'elijah', name: 'Elijah', icon: '⚡', desc: '+15% offline earnings · −5% tap value', fx: { offline: 0.15, tap: -0.05 } },
]

/** Combined sage multipliers {global, cost, tap, kavod, offline, milk} (all 1 when empty). */
export function sageEffects(state) {
  const out = { global: 1, cost: 1, tap: 1, kavod: 1, offline: 1, milk: 1 }
  const seats = state.sanhedrin?.seats || {}
  for (const seat of SANHEDRIN_SEATS) {
    const sage = SAGES.find(s => s.id === seats[seat.id])
    if (!sage) continue
    for (const [k, v] of Object.entries(sage.fx)) {
      if (out[k] !== undefined) out[k] *= (1 + v * seat.mult)
    }
  }
  return out
}

/** Seat a sage (or replace). One sage sits once; the seat cools 4h. False when locked/cooling. */
export function swapSage(state, seatId, sageId, now = Date.now()) {
  const seat = SANHEDRIN_SEATS.find(s => s.id === seatId)
  if (!seat || !SAGES.some(s => s.id === sageId)) return false
  const cd = state.sanhedrin?.cooldowns || {}
  if ((cd[seatId] || 0) > now) return false
  const seats = { ...(state.sanhedrin?.seats || {}) }
  for (const k of Object.keys(seats)) if (seats[k] === sageId) delete seats[k]
  seats[seatId] = sageId
  state.sanhedrin = { seats, cooldowns: { ...cd, [seatId]: now + SAGE_SWAP_COOLDOWN_MS } }
  return true
}

/** Cooldown ms remaining on a seat (0 = swappable). */
export function sageCooldownLeft(state, seatId, now = Date.now()) {
  return Math.max(0, (state.sanhedrin?.cooldowns?.[seatId] || 0) - now)
}

// ── Shuk: the third minigame (Cookie-Clicker Stock Market, stalls) ─────
// Five goods priced in production-seconds (auto-scales to your era, like
// Cookie's $=CpS-seconds). Prices ride deterministic smooth cycles (47min +
// 11min sines, per-good phases) — no stored prices, always tradeable, real
// buy-low-sell-high play. A 2% bid/ask spread stops instant flips.
// "Learn on credit": grant 1h of production now, −25% for 4h after (one
// loan at a time, 24h cooldown). Debt never stacks with itself.

export const SHUK_GOODS = [
  { id: 'oil', name: 'Olive Oil', icon: '🫒', baseSecs: 90, ph1: 0.0, ph2: 0.0 },
  { id: 'wheat', name: 'Wheat', icon: '🌾', baseSecs: 30, ph1: 0.37, ph2: 0.73 },
  { id: 'wine', name: 'Wine', icon: '🍷', baseSecs: 120, ph1: 0.74, ph2: 0.46 },
  { id: 'honey', name: 'Honey', icon: '🍯', baseSecs: 240, ph1: 0.11, ph2: 0.19 },
  { id: 'linen', name: 'Linen', icon: '🧵', baseSecs: 60, ph1: 0.52, ph2: 0.91 },
]
export const SHUK_SPREAD = 0.02
export const SHUK_SLOW_MIN = 47
export const SHUK_FAST_MIN = 11
export const SHUK_LOAN_HOURS = 1
export const SHUK_DEBT_MULT = 0.75
export const SHUK_DEBT_HOURS = 4
export const SHUK_LOAN_COOLDOWN_MS = 24 * 3600 * 1000

function shukGood(id) {
  return SHUK_GOODS.find(g => g.id === id) || null
}

/** Mid price in Ohr (deterministic cycles, floored at 20% of base). */
export function shukPrice(goodId, perSec, now = Date.now()) {
  const g = shukGood(goodId)
  if (!g || !(perSec > 0)) return 0
  const t = now / 60000
  const f = 1
    + 0.35 * Math.sin(2 * Math.PI * (t / SHUK_SLOW_MIN + g.ph1))
    + 0.15 * Math.sin(2 * Math.PI * (t / SHUK_FAST_MIN + g.ph2))
  return Math.max(0.2, f) * (perSec || 0) * g.baseSecs
}

/** {bid, ask, trend} — trend is +1/−1/0 from the 5-minute slope. */
export function shukQuote(goodId, perSec, now = Date.now()) {
  const mid = shukPrice(goodId, perSec, now)
  const prev = shukPrice(goodId, perSec, now - 5 * 60000)
  return {
    bid: mid * (1 - SHUK_SPREAD),
    ask: mid * (1 + SHUK_SPREAD),
    trend: mid > prev * 1.001 ? 1 : mid < prev * 0.999 ? -1 : 0,
  }
}

/** Buy n units at ask. Returns spent Ohr (0 when unaffordable/unknown). */
export function buyShuk(state, goodId, n = 1, perSec = 0, now = Date.now()) {
  const g = shukGood(goodId)
  if (!g || !(n > 0)) return 0
  const { ask } = shukQuote(goodId, perSec, now)
  const spend = ask * n
  if ((state.ohr || 0) < spend) return 0
  state.ohr -= spend
  const holdings = { ...(state.shuk?.holdings || {}) }
  holdings[goodId] = (holdings[goodId] || 0) + n
  state.shuk = { ...(state.shuk || {}), holdings }
  return spend
}

/** Sell n units (clamped to holdings) at bid. Returns granted Ohr. */
export function sellShuk(state, goodId, n = 1, perSec = 0, now = Date.now()) {
  const g = shukGood(goodId)
  if (!g || !(n > 0)) return 0
  const have = state.shuk?.holdings?.[goodId] || 0
  const k = Math.min(n, have)
  if (k <= 0) return 0
  const { bid } = shukQuote(goodId, perSec, now)
  const granted = bid * k
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  const holdings = { ...(state.shuk?.holdings || {}), [goodId]: have - k }
  state.shuk = { ...(state.shuk || {}), holdings }
  return granted
}

/** Debt multiplier (1 normally, 0.75 while learning on credit). */
export function shukDebt(state, now = Date.now()) {
  return (state.shuk?.debtUntil || 0) > now ? SHUK_DEBT_MULT : 1
}

/**
 * Learn on credit: +1h production now, −25% for 4h. One loan at a time,
 * 24h cooldown after the debt clears. Returns granted Ohr (0 if refused).
 */
export function takeShukLoan(state, perSec, now = Date.now()) {
  if ((state.shuk?.debtUntil || 0) > now) return 0
  if ((state.shuk?.loanCooldownUntil || 0) > now) return 0
  const granted = (perSec || 0) * 3600 * SHUK_LOAN_HOURS
  state.ohr += granted
  state.lifetimeOhr = (state.lifetimeOhr || 0) + granted
  state.shuk = {
    ...(state.shuk || {}),
    holdings: { ...(state.shuk?.holdings || {}) },
    debtUntil: now + SHUK_DEBT_HOURS * 3600 * 1000,
    loanCooldownUntil: now + (SHUK_DEBT_HOURS * 3600 * 1000 + SHUK_LOAN_COOLDOWN_MS),
  }
  return granted
}

// ── Achievements → Shemen (oil): +4% Ohr each ────────────────────────
// Derived from state — no extra bookkeeping, no way to lose one.
// ("Talmidim multipliers read Shemen" from the plan is moot: there is no
//  building ladder — letters are the generators — so Shemen is a global.)

export const SHEMEN_PER_ACHIEVEMENT = 0.04

export const ACHIEVEMENTS = [
  { id: 'first_letter', name: 'First Light', icon: '🕯️', desc: 'Inscribe your first golem', check: s => totalOwned(s) >= 1 },
  { id: 'own10', name: 'Minyan', icon: '🕍', desc: 'Own 10 golems — a quorum', check: s => totalOwned(s) >= 10 },
  { id: 'own100', name: 'Kehillah', icon: '⛺', desc: 'Own 100 golems — a whole congregation', check: s => totalOwned(s) >= 100 },
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
  { id: 'crit50', name: 'True Aim', icon: '🎯', desc: 'Land 50 crits — emet, true', hidden: true, check: s => (s.crits || 0) >= 50 },
  { id: 'hoarder10', name: 'Patient', icon: '🏦', desc: 'Hold 10 unspent sparks at once', hidden: true, check: s => availableSparks(s) >= 10 },
]

export function achievementsEarned(state) {
  return ACHIEVEMENTS.filter(a => { try { return a.check(state) } catch { return false } })
}

export function shemenMultiplier(state) {
  return (1 + achievementsEarned(state).length * SHEMEN_PER_ACHIEVEMENT) * sageEffects(state).milk
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
  a(goldenRemainingSec(gp, 1000) === GOLDEN_WINDOW_SEC, 'claim window is 30s')
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
  a(buffMultiplier(gp4, 1000) === 3 * 7, 'different-kind buffs MULTIPLY (combo engine: frenzy x gale)')
  a(activeBuffCount(gp4, 1000) === 2, 'two buffs counted for the combo display')
  a(galeMultiplier(gp4, 6000) === 1, 'gale expires')
  const gp5 = defaultIdleState()
  gp5.buffs = { ...gp5.buffs, tapEndsAt: 5000 }
  a(tapBuffMultiplier(gp5, 1000) === 3, 'rush = x3 tap')
  a(tapValue(0, 0, {}, null, {}, tapBuffMultiplier(gp5, 1000)) === 3, 'tap value reflects the rush buff')
  const gp6 = defaultIdleState()
  gp6.golden = { id: 'dew', expiresAt: 99999 }
  gp6.ohr = 10 * 3600 * 20 // fat bank: full 2h pours out
  const dew = resolveGoldenPrompt(gp6, true, 1000, 10)
  a(dew.granted === 10 * 3600 * 2, 'dew grants 2h of production with a full bank')
  const gp6b = defaultIdleState()
  gp6b.golden = { id: 'dew', expiresAt: 99999 }
  gp6b.ohr = 0 // empty bank: floor of 15min, never nothing
  const dewPoor = resolveGoldenPrompt(gp6b, true, 1000, 10)
  a(dewPoor.granted === 10 * 3600 * DEW_MIN_HOURS, 'dew floor is 15min on an empty bank')
  const gpx7 = defaultIdleState()
  gpx7.owned = { 0: 10, 1: 10 }
  gpx7.golden = { id: 'shofar', expiresAt: 99999 }
  const sho = resolveGoldenPrompt(gpx7, true, 1000, 10)
  a(sho.claimed && shofarMultiplier(gpx7, 1000) === 1 + 20 / 20, 'shofar blast scales with workshop size (20 golems = x2)')
  a(Math.abs(buffMultiplier(gpx7, 1000) - 2) < 1e-9, 'shofar feeds the combo multiplier')
  const gpx8 = defaultIdleState()
  gpx8.buffs = { ...gpx8.buffs, galeEndsAt: 99999 }
  spawnGoldenPrompt(gpx8, 1000, () => 0.99)
  const [lox8] = GOLDEN_INTERVAL_SEC
  a(gpx8.nextGoldenAt <= 1000 + (lox8 + 0.99 * (180 - lox8)) * 1000 * 0.5 + 1, 'get lucky: buffed visits come twice as fast')
  a(pickGoldenPrompt(() => 0).id === 'gale' && pickGoldenPrompt(() => 0.99).id === 'shofar', 'weighted pick is ordered (rarest last)')
  a(GOLDEN_PROMPTS.every(p => p.weight > 0), 'every prompt has weight')
  a(spawnGoldenPrompt(defaultIdleState(), 1000, Math.random, 0) === null, 'no golden prompt with zero production')
  const gp7 = defaultIdleState()
  spawnGoldenPrompt(gp7, 1000, () => 0.5)
  a(expireGoldenPrompt(gp7, 1000 + (GOLDEN_WINDOW_SEC + 1) * 1000) === true && gp7.golden === null, 'expired prompt auto-clears')
  a(expireGoldenPrompt(defaultIdleState(), 1000) === false, 'nothing to expire when none pending')
  // Popup quiz: the prompt asks its own letter question (6 options, Anki deck)
  const gq = defaultIdleState()
  gq.owned = { 0: 1, 5: 2 }
  const quiz = makeGoldenQuiz(gq, () => 0.5, {}, 1000)
  a(quiz.options.length === 6 && new Set(quiz.options).size === 6, 'quiz has 6 distinct options')
  a(quiz.options.includes(quiz.letter), 'quiz includes the correct letter')
  a(!!gq.quizDeck && gq.quizDeck.newLetters.length === 3, 'first quiz deals a 3-letter daily set')
  a(gq.quizDeck.day === dayKey(1000), 'deck stamped with today')
  // Adaptive: struggling → high-mastery confidence pick; cruising → weak + confusables
  const gqE = defaultIdleState()
  const qE = makeGoldenQuiz(gqE, () => 0.5, { mastery: { 0: 0.9, 1: 0.1 }, bias: 0.5 }, 1000)
  a(qE.letter === 0, 'struggling players get high-mastery questions')
  a(qE.qtype === 'name', 'struggling players get recognition questions')
  const gqH = defaultIdleState()
  const qH = makeGoldenQuiz(gqH, () => 0.5, { mastery: { 0: 0.9, 1: 0.05, 2: 0.5 }, bias: -0.5 }, 1000)
  a(qH.letter === 1, 'cruising players get low-mastery questions')
  a(qH.options.includes(5), 'hard mode foils with the confusable (bet→vav)')
  a(qH.qtype === 'glyph' || qH.qtype === 'audio', 'cruising players get recall questions')
  // No immediate repeats while alternatives exist
  const gqN = defaultIdleState()
  const qN1 = makeGoldenQuiz(gqN, () => 0, {}, 1000)
  const qN2 = makeGoldenQuiz(gqN, () => 0, {}, 1000)
  a(qN2.letter !== qN1.letter, 'same letter never quizzed twice in a row')
  // Spaced repetition: correct stretches, wrong returns in minutes
  const gqR = defaultIdleState()
  recordGoldenAnswer(gqR, 3, true, 1000)
  a(gqR.quizDeck.due[3] === 1000 + 86400000, 'correct schedules review in 1d')
  recordGoldenAnswer(gqR, 3, true, 1000)
  a(gqR.quizDeck.due[3] === 1000 + 3 * 86400000, 'second correct stretches to 3d')
  recordGoldenAnswer(gqR, 4, false, 1000)
  a(gqR.quizDeck.due[4] === 1000 + 10 * 60000, 'wrong returns in 10 minutes')
  // Day rollover: fresh letters dealt, reviews carried
  const gqD = defaultIdleState()
  recordGoldenAnswer(gqD, 0, true, 1000)
  ensureQuizDeck(gqD, 1000 + 86400000 + 1)
  a(gqD.quizDeck.day === dayKey(1000 + 86400000 + 1), 'deck rolls to the new day')
  a(gqD.quizDeck.due[0] === 1000 + 86400000, 'reviews carry across days')
  a(gqD.quizDeck.newLetters.length === 3 && !gqD.quizDeck.newLetters.includes(0), 'seen letters are not re-dealt')
  const gq2 = defaultIdleState()
  gq2.golden = { id: 'gale', expiresAt: 99999, quiz: { letter: 3, options: [3, 7, 11, 0, 1, 2] } }
  a(answerGoldenQuiz(gq2, 0, 1000, 0).claimed?.id === 'gale', 'right option claims the buff')
  a(gq2.golden === null, 'quiz answer clears the prompt')
  const gq3 = defaultIdleState()
  gq3.golden = { id: 'gale', expiresAt: 99999, quiz: { letter: 3, options: [3, 7, 11, 0, 1, 2] } }
  a(answerGoldenQuiz(gq3, 2, 1000, 0).fizzled === true, 'wrong option fizzles, never drains')
  const gq4 = defaultIdleState()
  gq4.golden = { id: 'gale', expiresAt: 5000, quiz: { letter: 3, options: [3, 7, 11, 0, 1, 2] } }
  a(answerGoldenQuiz(gq4, 0, 99999, 0).reason === 'expired', 'late quiz answer fizzles')
  a(answerGoldenQuiz(defaultIdleState(), 0, 1000, 0) === null, 'no quiz answer when none pending')
  a(GEMATRIA.length === 22 && GEMATRIA[0] === 1 && GEMATRIA[21] === 400, 'gematria table covers all 22 letters')
  a(letterRate(defaultIdleState(), {}, 0) === 0, 'unowned letter contributes nothing')
  {
    const ls = defaultIdleState()
    ls.owned = { 0: 5, 3: 2 }
    const mast = { 0: 0.9, 3: 0.2 }
    let sum = 0
    for (let i = 0; i < 22; i++) sum += letterRate(ls, mast, i)
    a(Math.abs(sum - statePerSecond(ls, mast)) < 1e-6, 'letter rates sum to the workshop rate')
    a(letterRate(ls, mast, 0) > letterRate(ls, mast, 3), 'more owned + mastered earns more')
  }
  const gq5 = defaultIdleState()
  gq5.golden = { id: 'prophet', expiresAt: 99999, options: ['gale', 'dew', 'rush'], quiz: { letter: 0, options: [0, 1, 2] } }
  a((answerGoldenQuiz(gq5, 0, 1000, 0).choice || []).length === 3, 'prophet quiz opens the blessing choice')
  // Word/root tier: 100 known words + 100 known roots + studied grammar
  const SAMPLE_WORDS = [
    { rank: 1, lemma: 'L1', hebrew: 'אֵת', bare: 'את', gloss: 'Direct object marker', transliteration: 'ʾēṯ' },
    { rank: 2, lemma: 'L2', hebrew: 'בְּרֵאשִׁית', bare: 'בראשית', gloss: 'In the beginning', transliteration: 'bərēʾšîṯ' },
    { rank: 3, lemma: 'L3', hebrew: 'אָמַר', bare: 'אמר', gloss: 'He said', transliteration: 'ʾāmar' },
    { rank: 4, lemma: 'L4', hebrew: 'יוֹם', bare: 'יום', gloss: 'Day', transliteration: 'yôm' },
    { rank: 5, lemma: 'L5', hebrew: 'אֶרֶץ', bare: 'ארץ', gloss: 'Land', transliteration: 'ʾereṣ' },
    { rank: 6, lemma: 'L6', hebrew: 'הָיָה', bare: 'היה', gloss: 'He was', transliteration: 'hāyâ' },
    { rank: 7, lemma: 'L7', hebrew: 'אֱלֹהִים', bare: 'אלהים', gloss: 'God', transliteration: 'ʾĕlōhîm' },
  ]
  const SAMPLE_ROOTS = [
    { root: 'אמר', gloss: 'say', examples: ['L3', 'L9'] },
    { root: 'יום', gloss: 'day', examples: ['L4', 'L8'] },
  ]
  const GRAM = { mastery: { g1: 0.9 }, categories: { g1: 'grammar' } }
  const gwPoor = defaultIdleState()
  gwPoor.owned = { 0: 1 }
  a(wordCandidates(gwPoor, SAMPLE_WORDS, SAMPLE_ROOTS, {}, {}).length === 0, 'word tier locked below 100 known')
  a(translationUnlocked(gwPoor, SAMPLE_WORDS, SAMPLE_ROOTS, {}, {}) === false, 'tier gate closed when nothing known')
  // Rich workshop: all sample letters owned → all 7 words known; roots need
  // 2 known examples each — L3/L9 and L4/L8 are half outside the sample.
  const gwRich = defaultIdleState()
  gwRich.owned = { 0: 5, 1: 1, 19: 1, 4: 1, 9: 1, 20: 1, 12: 1, 5: 1, 13: 1, 15: 1, 17: 1, 11: 1 }
  a(knownWords(gwRich, SAMPLE_WORDS).length === 5, 'known words are the readable ones')
  a(knownRoots(gwRich, SAMPLE_WORDS, SAMPLE_ROOTS).length === 0, 'roots need 2 known examples')
  a(wordLockedLetters(SAMPLE_WORDS[1], { 0: 1 }).length > 0, 'missing letters block the word')
  a(grammarStudied({}, {}) === 0 && grammarStudied(GRAM.mastery, GRAM.categories) === 1, 'grammar gate counts mastered grammar')
  // Unlock opens with scale: simulate 100 known via owned-everything + big lists
  const gwFull = defaultIdleState()
  const big = []
  for (let i = 0; i < 120; i++) big.push({ rank: 100 + i, lemma: 'LX' + i, hebrew: 'א', bare: 'א', gloss: 'g' + i, transliteration: 'x' })
  gwFull.owned = { 0: 3 }
  const bigRoots = []
  for (let i = 0; i < 100; i++) bigRoots.push({ root: 'R' + i, gloss: 'rg' + i, examples: ['LX' + i, 'LX' + ((i + 1) % 120)] })
  a(translationUnlocked(gwFull, big, bigRoots, GRAM.mastery, GRAM.categories) === true, 'tier opens at 100/100 + grammar')
  const wq = makeWordQuiz(knownWords(gwFull, big), () => 0.1, big)
  a(wq.options.length === 6 && new Set(wq.options).size === 6, 'word quiz has 6 distinct options')
  a(wq.options.includes(wq.answer), 'word quiz includes the answer')
  const gwA = defaultIdleState()
  const ai = wq.options.indexOf(wq.answer)
  gwA.golden = { id: 'dew', expiresAt: 99999, quiz: wq }
  a(answerGoldenQuiz(gwA, ai, 1000, 10).claimed?.id === 'dew', 'right word answer claims the buff')
  // Word/root SRS: partial correctness lives per item
  const gwS = defaultIdleState()
  recordWordAnswer(gwS, 5, true, 1000)
  recordWordAnswer(gwS, 5, true, 1000)
  a(gwS.quizDeck.wordStats[5].due === 1000 + 3 * 86400000, 'word correct stretches 1d then 3d')
  recordWordAnswer(gwS, 6, false, 1000)
  a(gwS.quizDeck.wordStats[6].due === 1000 + 10 * 60000, 'word wrong returns in 10 min')
  recordRootAnswer(gwS, 'אמר', true, 1000)
  a(gwS.quizDeck.rootStats['אמר'].streak === 1, 'root answers tracked separately')
  const rq = makeRootQuiz([{ root: 'אמר', gloss: 'say', examples: [] }], [{ root: 'אמר', gloss: 'say' }, { root: 'יום', gloss: 'day' }, { root: 'ארץ', gloss: 'land' }, { root: 'היה', gloss: 'be' }, { root: 'אלה', gloss: 'god' }, { root: 'דעת', gloss: 'know' }, { root: 'שמע', gloss: 'hear' }], () => 0.1)
  a(rq.options.length === 6 && rq.options.includes(rq.answer), 'root quiz is 6 distinct with the answer')
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
  const dewState = defaultIdleState()
  dewState.ohr = 10 * 3600 * 20 // bank rule applies to blessings too
  const dewChoice = applyProphetChoice(dewState, 'dew', 10)
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
  // Word tiers (rank → level) + word→letter gains
  a(wordTier(0) === 4 && wordTier(49) === 4, 'Shema words are L4')
  a(wordTier(50) === 5 && wordTier(149) === 5, 'Daily words are L5')
  a(wordTier(150) === 6 && wordTier(299) === 6, 'Prophets words are L6')
  a(wordTier(300) === 7 && wordTier(499) === 7, 'Writings/Rare words are L7')
  a(isWordMastered({ interval_days: 21 }) && !isWordMastered({ interval_days: 20 }), 'mature at 21d (Anki rule)')
  const wMastery = { 0: 0.9, 2: 0.1 }
  a(letterWordMultiplier(0, [{ bare: 'אב' }], wMastery) === 1 + WORD_LETTER_BONUS, 'mastered letter gains per containing word')
  a(letterWordMultiplier(2, [{ bare: 'אבג' }], wMastery) === 1, 'unmastered letter gets no word bonus')
  a(wordLetterIndices('אב').length === 2 && wordLetterIndices('ך')[0] === 11, 'final forms map to base letters')
  // Word↔root synergy + staged gates + root study reps
  a(Math.abs(globalMultiplier(0, 100, {}, 0) - (1 + 100 * 0.02) * (1 + 100 * ROOT_WORD_SYNERGY)) < 1e-9, 'words feed the roots term +0.1% each')
  a(Math.abs(globalMultiplier(0, 100, {}, 4) / globalMultiplier(0, 100, {}, 0) - (1 + 4 * WORD_ROOT_SYNERGY)) < 1e-9, 'mature roots lift the word term +5% each')
  a(wordDeckUnlocked(0, 0) && wordDeckUnlocked(2, 0) && !wordDeckUnlocked(3, 9) && wordDeckUnlocked(3, 10), 'decks 3+ gate on 10 mastered')
  a(!wordDeckUnlocked(6, 39) && wordDeckUnlocked(6, 40), 'decks 6+ gate on 40 mastered')
  const rs = defaultIdleState()
  a(matureRootCount(rs) === 0, 'no mature roots at start')
  recordRootStudy(rs, 'אמר', true); recordRootStudy(rs, 'אמר', true); recordRootStudy(rs, 'אמר', false)
  a(matureRootCount(rs) === 0, '2-1 is not mature')
  recordRootStudy(rs, 'אמר', true); recordRootStudy(rs, 'אמר', true)
  a(matureRootCount(rs) === 1, '3 net knows matures a root')
  // Grammar tracks (derived, no migration)
  a(grammarTrack({ category: 'verb', level: 5 }).track === 'binyanim', 'verbs map to binyanim')
  a(grammarTrack({ category: 'syntax', level: 6 }).track === 'clauses', 'syntax maps to clauses')
  a(grammarTrack({ category: 'noun', level: 6 }).track === 'nominals', 'nouns map to nominals')
  a(grammarTrack({ category: 'grammar', level: 3 }).track === 'nominals', 'grammar maps to nominals')
  a(grammarTrack({ category: 'word', level: 4 }) === null, 'words are not track nodes')
  a(grammarTrack({ category: 'verb', level: 3 }).tier === 1 && grammarTrack({ category: 'verb', level: 7 }).tier === 5, 'tiers follow level L3->1 … L7->5')
  const gt = grammarTrackBonus([
    { id: 'v1', category: 'verb', level: 3, mastery: 0.9 },
    { id: 'v2', category: 'verb', level: 3, mastery: 0.2 },
    { id: 's1', category: 'syntax', level: 6, mastery: 1.0 },
  ])
  a(gt.complete === 1 && Math.abs(gt.bonus - TRACK_BONUS_PER_TIER) < 1e-9, 'one complete tier pays +5%')
  a(gt.backlog.some(b => b.reason === 'empty'), 'unseeded cells surface as backlog')
  // Root Garden minigame
  const gs = defaultIdleState()
  gs.ohr = 100000
  a(gardenPlots(gs).length === GARDEN_PLOTS && gardenPlots(gs).every(p => !p), 'six empty plots at start')
  a(plantGardenRoot(gs, 0, 'אמר', 10, 1000) === true, 'planting takes root + Ohr')
  a(Math.abs(gs.ohr - (100000 - 10 * GARDEN_COST_HOURS * 3600)) < 1e-9, 'planting costs 15min of production')
  a(plantGardenRoot(gs, 0, 'דבר', 10, 1000) === false, 'occupied plot refuses')
  a(gardenStage({ root: 'אמר', plantedAt: 1000 }, 1000) === 0, 'sprout at planting')
  a(gardenStage({ root: 'אמר', plantedAt: 1000 }, 1000 + GARDEN_GROW_MS) === 2, 'mature at 2h')
  a(gardenReady(gs, 0, 1000 + GARDEN_GROW_MS) === true, 'plot ready at 2h')
  a(harvestGardenRoot(gs, 0, 10, 1000) === null, 'unripe harvest refuses')
  const hr = harvestGardenRoot(gs, 0, 10, 1000 + GARDEN_GROW_MS, () => 0.99)
  a(hr && Math.abs(hr.granted - 10 * GARDEN_REWARD_HOURS * 3600) < 1e-9 && hr.kavod === GARDEN_KAVOD && !hr.mutated, 'harvest grants 30min + 5 Kavod + no mutation alone')
  a(gardenPlots(gs)[0] === null, 'harvest clears the plot')
  const mut0 = defaultIdleState()
  mut0.ohr = 100000
  plantGardenRoot(mut0, 0, 'אמר', 10, 1000)
  plantGardenRoot(mut0, 1, 'דבר', 10, 1000)
  const mut = harvestGardenRoot(mut0, 0, 10, 1000 + GARDEN_GROW_MS, () => 0.0)
  a(mut && mut.mutated && mut.neighbor === 'דבר' && mut.kavod === GARDEN_KAVOD + GARDEN_MUTATION_KAVOD, 'adjacent different mature roots mutate')
  a(JSON.stringify(gardenNeighbors(0).sort()) === JSON.stringify([1, 3]), 'corner neighbors without wraparound')
  a(JSON.stringify(gardenNeighbors(4).sort()) === JSON.stringify([1, 3, 5]), 'center neighbors')
  const allLetters = Object.fromEntries(LETTERS.map((_, k) => [k, 1]))
  a(readableRoots(allLetters, ['אמר', { root: 'דבר' }]).length === 2, 'all readable when all letters owned')
  a(readableRoots({}, ['אמר']).length === 0, 'nothing readable with no letters')
  // Sanhedrin sages
  const se = defaultIdleState()
  const fx0 = sageEffects(se)
  a(Object.values(fx0).every(v => v === 1), 'empty sanhedrin is neutral')
  a(swapSage(se, 'honor', 'rashi', 1000) === true, 'seat Rashi with honor')
  a(Math.abs(sageEffects(se).global - 1.10) < 1e-9, 'honor seat ×1.0: +10% Ohr')
  a(swapSage(se, 'honor', 'hillel', 2000) === false, 'cooling seat refuses')
  a(swapSage(se, 'wisdom', 'hillel', 2000) === true, 'second seat takes Hillel')
  a(Math.abs(sageEffects(se).tap - (1 + 0.15 * 0.6)) < 1e-9, 'wisdom seat ×0.6: +9% tap')
  a(swapSage(se, 'learning', 'hillel', 2000) === true && !se.sanhedrin.seats.wisdom, 'one sage sits once (moves seats)')
  a(swapSage(se, 'nope', 'rashi', 99999999) === false && swapSage(se, 'honor', 'bogus', 99999999) === false, 'bad seat/sage refuse')
  a(sageCooldownLeft(se, 'honor', 1000 + SAGE_SWAP_COOLDOWN_MS + 1) === 0, 'cooldown expires after 4h')
  const scx = defaultIdleState()
  scx.owned = { 0: 10 }
  swapSage(scx, 'honor', 'akiva', 0)
  const before = scx.kavod || 0
  applyCorrectAnswer(scx, 1, () => 0.99)
  a(scx.kavod - before >= 1, 'Akiva Kavod bonus flows through answers')
  // Shuk market
  a(shukPrice('oil', 10, 1000) === shukPrice('oil', 10, 1000), 'prices are deterministic')
  a(shukPrice('bogus', 10, 1000) === 0 && shukPrice('oil', 0, 1000) === 0, 'unknown goods and zero rate price at 0')
  const qq = shukQuote('wheat', 10, 600000)
  a(qq.ask > qq.bid && Math.abs(qq.ask / qq.bid - (1 + SHUK_SPREAD) / (1 - SHUK_SPREAD)) < 1e-9, '2% spread stops instant flips')
  a([-1, 0, 1].includes(qq.trend), 'trend is a direction')
  const shk = defaultIdleState()
  shk.ohr = 100000
  a(buyShuk(shk, 'bogus', 1, 10) === 0, 'unknown goods refuse')
  const spent = buyShuk(shk, 'wheat', 2, 10, 600000)
  a(spent > 0 && shk.shuk.holdings.wheat === 2, 'buying fills holdings')
  const got = sellShuk(shk, 'wheat', 1, 10, 600000)
  a(got > 0 && got < spent / 2 + 1 && shk.shuk.holdings.wheat === 1, 'selling pays bid (below ask)')
  a(sellShuk(shk, 'wheat', 99, 10, 600000) > 0 && shk.shuk.holdings.wheat === 0, 'oversell clamps to holdings')
  const poor = defaultIdleState()
  a(buyShuk(poor, 'oil', 1, 10) === 0, 'broke buyers refused')
  const ln = defaultIdleState()
  const grant = takeShukLoan(ln, 10, 1000)
  a(grant === 10 * 3600 * SHUK_LOAN_HOURS, 'credit grants an hour now')
  a(shukDebt(ln, 1000) === SHUK_DEBT_MULT, 'debt weighs production')
  a(Math.abs(buffMultiplier(ln, 1000) - SHUK_DEBT_MULT) < 1e-9, 'debt flows through the combo multiplier')
  a(takeShukLoan(ln, 10, 2000) === 0, 'no second loan while indebted')
  a(shukDebt(ln, 1000 + SHUK_DEBT_HOURS * 3600 * 1000 + 1) === 1, 'debt clears after 4h')
  a(takeShukLoan(ln, 10, 1000 + SHUK_DEBT_HOURS * 3600 * 1000 + 2) === 0, 'cooldown outlives the debt')
}
