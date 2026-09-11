# Balancing analytics — read the logs, tune the game

Export: open Hebrew → 🎮 Games → scroll to the pace row → **📊 Log**.
You get `hebrew-analytics-YYYY-MM-DD.json`: `{exported_at, count, events}`.
Each event: `{t, session, mode, game, type, data}`.

## Event schema

| type | data | logged where |
|---|---|---|
| `session_start` | `{touch, w}` | HebrewLearnView mount |
| `mode_switch` | `{mode}` | Classic ↔ Games picker |
| `game_switch` | `{game}` | game shelf |
| `answer` | `{correct, ms, source: quiz\|audio, qtype?, nodeId?, hebrew?}` | HebrewQuiz grade, audio review |
| `purchase` | `{letter, n, spend, bulk, ohr_left}` | letter shop buy |
| `prestige` | `{gained, roots, lifetime, prestiges}` | root forge |
| `quest` | `{id, reward}` | quest claim |
| `boost` | `{kind: frenzy\|warp, cost, granted?, warps?}` | Frenzy / Time Warp buy |
| `milestone` | `{milestone, bonus}` | streak burst |
| `offline_earned` | `{earned, elapsed_h}` | return computation |
| `offline_claim` | `{earned}` | tap-to-claim |
| `feedback` | `{kind, bias}` | pace buttons |

Ring buffer caps at 2000 events (oldest evicted). No backend yet (Track D3).

## Queries (paste into node against the exported file)

```js
const log = require('./hebrew-analytics-2026-09-10.json').events;
const by = (t) => log.filter(e => e.type === t);
const ans = by('answer');

// 1. Accuracy overall + by source (target 70–90%; <60% = too hard, >90% = too easy)
const acc = (rows) => rows.length ? rows.filter(e => e.data.correct).length / rows.length : null;
console.log('overall', acc(ans));
for (const s of [...new Set(ans.map(e => e.data.source))])
  console.log(s, acc(ans.filter(e => e.data.source === s)));

// 2. Response-time median by source (quiz timers live here)
const med = (a) => { const s = [...a].sort((x,y)=>x-y); return s[Math.floor(s.length/2)]; };
console.log('median ms', med(ans.map(e => e.data.ms)));

// 3. Time to first prestige (target 30–90 min of wall-clock)
const t0 = log[0]?.t, p1 = by('prestige')[0];
console.log('min to first root:', p1 ? ((p1.t - t0) / 60000).toFixed(1) : 'not yet');

// 4. Kavod economy: earned vs spent (should hover ~spend/earn 0.5–0.9; hoarding >0.9 = costs too high)
const kavodIn = ans.reduce((a,e) => a + (e.data.correct ? 1 : 0), 0); // ≈ base; streak/crit add more
const kavodOut = by('boost').reduce((a,e) => a + (e.data.cost || 0), 0);
console.log('kavod out/in ≈', (kavodOut / Math.max(1, kavodIn)).toFixed(2));

// 5. Quest funnel: which quest stalls? (progress events are implicit —
//    last claimed quest id vs answers count tells you where players sit)
console.log('quests claimed:', by('quest').map(e => e.data.id));

// 6. Feedback drift: explicit vs implicit difficulty
console.log('feedback:', by('feedback').map(e => `${e.data.kind}@${e.data.bias.toFixed(2)}`));

// 7. Classic vs Games split (are players even opting into games?)
console.log('modes:', [...new Set(log.map(e => e.mode))],
  'mode_switches:', by('mode_switch').length);
```

## Tuning thresholds → knob to turn

| Signal | Threshold | Fix (all in `lib/idle-game.js`) |
|---|---|---|
| Accuracy < 60% over 20 | too hard | auto-ease handles it; if explicit 😅 spam too, lower `baseCost` growth `4.2 → 3.5` |
| Accuracy > 92% sustained | too easy | raise growth, or tighten `getTimeLimit` in HebrewQuiz |
| First root > 120 min | prestige too slow | lower `lifetimeForRoots` divisor `1e6 → 5e5` |
| First root < 15 min | prestige too fast | raise divisor or quest-gate forge behind `root1` quest |
| Kavod out/in > 0.95 | boosts priced out | lower `FRENZY_COST` / warp base 30 |
| Kavod out/in < 0.3 | boosts too cheap | raise costs; frenzy is meant to be 1–2 per session |
| Quest stall at same id 3+ sessions | quest badly tuned | lower that quest's goal or raise its reward |
| Offline claims >> session earnings | idle dominates | cut offline efficiency 0.5, or raise active tap % |
| 😅 after 😌 (whiplash) | auto-tune too jumpy | halve `recordAttempt` bias steps (0.05/0.10) |
| Games mode < 20% of sessions | discovery problem | move picker above Continue Learning, default new users to Games |

## Cadence
Playtest → export → run queries → change ONE number → playtest. The log is the playtester that never sleeps.
