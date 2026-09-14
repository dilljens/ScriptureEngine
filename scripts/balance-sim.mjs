// Headless balance sim — drives the real idle-game.js pure functions with a
// greedy "engaged player" policy and reports milestone timings.
//
//   node scripts/balance-sim.mjs [days] [dtSeconds] [no-vows]
//
// This is an OPTIMISTIC UPPER BOUND: ~5 graded answers/min with no breaks,
// perfect greedy buying, no distractions. Treat bot times as floor estimates —
// a real learner is roughly 10-50x slower, so a bot time of hours is a real
// time of days. Use it to catch orders-of-magnitude errors (a "meta" layer that
// completes in 40 minutes), not to fine-tune minutes.
//
// Every event goes through the same functions the app calls, so a regression in
// the pure formulas shows up here too.
import * as g from '../frontend/src/lib/idle-game.js'

const DAYS = Number(process.argv[2] || 7)
const DT = Number(process.argv[3] || 5) // seconds per step
const VOWS = process.argv[4] !== 'no-vows' // pass no-vows for the unconstrained baseline
const TOTAL = Math.floor(DAYS * 86400)
const ANSWER_EVERY = 12 // seconds between graded answers (~5/min)
const ACCURACY = 0.85

const state = g.defaultIdleState()
state.ohr = g.STARTING_OHR
state.lifetimeOhr = g.STARTING_OHR
const mastery = {}
const ms = {}
const mark = (k, t) => { if (!(k in ms)) ms[k] = t }

let answers = 0
let nextAnswer = 0
let nextUpgradeCheck = 0
let rngState = 12345
const rnd = () => { rngState = (rngState * 1103515245 + 12345) & 0x7fffffff; return rngState / 0x7fffffff }

g.plantFig(state, 0)
g.plantVineyard(state, 0)

function cheapest() {
  let best = 0, bestCost = Infinity
  for (let i = 0; i < g.LETTERS.length; i++) {
    if (!g.exileAllows(state, i)) continue // the vow binds the bot too
    const c = g.generatorCost(i, state.owned[i] || 0, state.difficulty)
    if (c < bestCost) { bestCost = c; best = i }
  }
  return { i: best, cost: bestCost }
}
const nextHeavenly = () => {
  // Left-hand path, deterministically: first incomplete tier, first option.
  // Keeps timings comparable across runs; branch coverage lives in self-checks.
  for (const t of g.HEAVENLY_TIERS) {
    if (g.heavenlyTierOwned(state, t)) continue
    return g.HEAVENLY_UPGRADES.find(u => u.tier === t)
  }
  return null
}

for (let t = 0; t < TOTAL; t += DT) {
  // Answers fire on their own cadence, independent of the accrual step size.
  while (nextAnswer < t + DT) {
    const at = Math.floor(nextAnswer)
    nextAnswer += ANSWER_EVERY
    const correct = rnd() < ACCURACY
    const rate0 = g.statePerSecond(state, mastery)
    if (correct) {
      g.applyCorrectAnswer(state, rate0)
      g.recordDailyCorrect(state, at * 1000)
      mastery[answers % g.LETTERS.length] = Math.min(1, (mastery[answers % g.LETTERS.length] || 0) + 0.05)
    } else g.applyWrongAnswer(state)
    answers++
    const gres = g.resolveGoldenPrompt(state, correct, at * 1000, rate0 * g.buffMultiplier(state))
    if (gres?.choice) {
      // Greedy prophet: hours scale best late, then mult, tap, kavod, timers.
      const prio = ['dew', 'gale', 'rush', 'manna', 'early']
      const pick = prio.find(p => gres.choice.includes(p)) || gres.choice[0]
      g.applyProphetChoice(state, pick, rate0 * g.buffMultiplier(state), at * 1000)
    }
    g.spawnGoldenPrompt(state, at * 1000, rnd, rate0)
    g.expireGoldenPrompt(state, at * 1000)
  }

  const gain = g.statePerSecond(state, mastery) * g.buffMultiplier(state) * DT
  state.ohr += gain
  state.lifetimeOhr += gain

  let buys = 0
  while (buys < 10) {
    const { i, cost } = cheapest()
    if (state.ohr < cost) break
    state.ohr -= cost
    state.owned = { ...state.owned, [i]: (state.owned[i] || 0) + 1 }
    buys++
  }

  if (t >= nextUpgradeCheck) {
    nextUpgradeCheck = t + 30
    for (let i = 0; i < g.LETTERS.length; i++) {
      const us = g.availableLetterUpgrades(state, i)
      for (const u of us) if (state.ohr >= u.cost) g.buyLetterUpgrade(state, i, u.k)
    }
    // Spend Kavod like an engaged player: keep the frenzy chained. Without
    // this the sim prices exile's +Kavod payoff at zero (it never spends it).
    g.buyFrenzy(state, t * 1000)
    const nh = nextHeavenly()
    if (nh && g.availableSparks(state) >= nh.cost) g.buyHeavenly(state, nh.id)
  }

  if (g.figReady(state, t * 1000)) g.harvestFig(state, g.statePerSecond(state, mastery), t * 1000)

  // Vineyard tends itself perfectly: harvest every ripe vine at the buffed
  // rate, exactly as the app's Tend button does.
  for (let v = 0; v < g.VINE_COUNT; v++) {
    if (g.vineReady(state, v, t * 1000)) {
      g.harvestVine(state, v, g.statePerSecond(state, mastery) * g.buffMultiplier(state), t * 1000)
    }
  }

  if (g.shouldPrestige(state.lifetimeOhr, state.roots || 0)) g.applyPrestige(state)
  // Taste each vow once, with a standing workshop, AFTER the meta layer opens
  // (first heavenly upgrade): freezing new buying during hypergrowth costs
  // 20x, while mature economies barely notice — vows are endgame spice for
  // committed students, not early detours. Neither may strand the run: both
  // require a productive workshop, and an uncompletable vow releases
  // uncounted after 24h.
  const metaOpen = g.heavenlyOwned(state, 'h_legacy')
  if (VOWS && metaOpen && !state.exile && (state.prestiges || 0) >= 2 && g.totalOwned(state) >= 50
      && (state.exilesCompleted || 0) < 1) {
    g.startExile(state, g.rollExileLetters(rnd), t * 1000)
  }
  if (VOWS && metaOpen && !state.exile && (state.prestiges || 0) >= 3 && g.totalOwned(state) >= 10
      && (state.exilesCompleted || 0) >= 1 && (state.exilesCompleted || 0) < 2) {
    g.startShemittah(state, t * 1000)
  }
  if (g.checkShemittah(state, t * 1000)) mark('shemittah_done', t)
  if (g.vowReleased(state, t * 1000)) mark('vow_released', t)

  if (g.totalOwned(state) >= 1) mark('first_letter', t)
  if ((state.roots || 0) >= 1) mark('first_root', t)
  if ((state.roots || 0) >= 10) mark('roots_10', t)
  if (g.sparksEarned(state.lifetimeOhr) >= 1) mark('spark_1', t)
  if (g.sparksEarned(state.lifetimeOhr) >= 3) mark('spark_3', t)
  if (g.heavenlyOwned(state, 'h_legacy')) mark('heavenly_1', t)
  if (g.heavenlyOwned(state, 'h_key')) mark('heavenly_all', t)
  if ((state.figs?.level || 0) >= 1) mark('fig_1', t)
  if ((state.figs?.level || 0) >= 10) mark('fig_10', t)
  if ((state.vineyard?.level || 0) >= 1) mark('vineyard_1', t)
  if ((state.vineyard?.level || 0) >= 10) mark('vineyard_10', t)
  if ((state.exilesCompleted || 0) >= 1) mark('exile_done', t)
  if (state.lifetimeOhr >= 1e6) mark('life_1e6', t)
  if (state.lifetimeOhr >= 1e9) mark('life_1e9', t)
  if (state.lifetimeOhr >= 1e12) mark('life_1e12', t)
}

const fmt = (s) => s === undefined ? 'never' : s < 3600 ? `${(s / 60).toFixed(0)}m` : s < 86400 ? `${(s / 3600).toFixed(1)}h` : `${(s / 86400).toFixed(1)}d`
console.log(`sim ${DAYS}d (DT=${DT}s) | answers ${answers} | perSec ${g.statePerSecond(state, mastery).toFixed(1)} | lifetime ${state.lifetimeOhr.toExponential(2)} | roots ${state.roots} | sparks ${g.availableSparks(state)}/${g.sparksEarned(state.lifetimeOhr)} | fig lvl ${state.figs?.level} | vineyard lvl ${state.vineyard?.level} | vows ${state.exilesCompleted || 0} | owned ${g.totalOwned(state)}`)
for (const k of ['first_letter', 'first_root', 'roots_10', 'spark_1', 'spark_3', 'heavenly_1', 'heavenly_all', 'fig_1', 'fig_10', 'vineyard_1', 'vineyard_10', 'exile_done', 'shemittah_done', 'vow_released', 'life_1e6', 'life_1e9', 'life_1e12'])
  console.log(`  ${k.padEnd(13)} ${fmt(ms[k])}`)
