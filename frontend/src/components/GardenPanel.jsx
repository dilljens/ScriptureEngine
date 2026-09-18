import React, { useEffect, useState } from 'react'
import {
  GARDEN_GROW_MS,
  GARDEN_COST_HOURS,
  gardenPlots,
  gardenStage,
  gardenNeighbors,
  readableRoots,
  plantGardenRoot,
  harvestGardenRoot,
  isFeastDay,
  fmtBig,
} from '../lib/idle-game'

/**
 * GardenPanel — Root Garden minigame (6 plots, 3×2).
 *
 * Plant a readable root for 15min of production → 2h growth
 * (sprout 🌱 → bud 🌿 → mature 🌳) → harvest 30min production + 5 Kavod
 * + 1 study rep (reps mature roots → +5% word income each).
 * Harvesting beside a DIFFERENT mature root may mutate (+15 Kavod + rep
 * for the neighbor). No wither, no rot — the game never punishes.
 *
 * Compact by design: the whole panel fits a phone screen with the HUD.
 */

const STAGE_EMOJI = ['🌱', '🌿', '🌳']

function fmtLeft(ms) {
  if (ms <= 0) return 'ready'
  const m = Math.ceil(ms / 60000)
  if (m < 60) return `${m}m left`
  return `${Math.floor(m / 60)}h ${m % 60}m left`
}

export default function GardenPanel({ state, perSec, onUpdate }) {
  const [, setNow] = useState(Date.now())
  const [pickPlot, setPickPlot] = useState(null) // plot index with picker open
  const [rootNames, setRootNames] = useState([]) // candidate root strings
  const [flash, setFlash] = useState(null) // harvest result text

  // Re-render for growth stages/countdowns (cheap 30s tick, panel-local).
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30000)
    return () => clearInterval(t)
  }, [])

  // Candidate roots: top-roots list, once (names only; readability is local).
  useEffect(() => {
    let cancelled = false
    fetch('/api/v1/hebrew/top-roots?limit=100')
      .then(r => r.json())
      .then(d => { if (!cancelled && d.ok) setRootNames((d.data.roots || []).map(r => r.root).filter(Boolean)) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  const plots = gardenPlots(state)
  const owned = state.owned || {}
  // Sukkot, the harvest feast: everything grows twice as fast.
  const growMs = isFeastDay('sukkot') ? GARDEN_GROW_MS / 2 : GARDEN_GROW_MS
  const choices = readableRoots(owned, rootNames.length ? rootNames : []).slice(0, 12)
  const cost = (perSec || 0) * GARDEN_COST_HOURS * 3600

  const doPlant = (i, root) => {
    const next = { ...state }
    if (!plantGardenRoot(next, i, root, perSec || 0)) return
    setPickPlot(null)
    onUpdate(next)
  }

  const doHarvest = (i) => {
    const next = { ...state }
    const res = harvestGardenRoot(next, i, perSec || 0, Date.now(), Math.random, growMs)
    if (!res) return
    setFlash(
      `+${fmtBig(res.granted)} ✨ +${res.kavod} 🌟 ${res.root}` +
      (res.mutated ? ` · 🧬 mutation with ${res.neighbor}!` : '')
    )
    setTimeout(() => setFlash(null), 4000)
    onUpdate(next)
  }

  return (
    <div>
      <div className="grid grid-cols-3 gap-1.5">
        {plots.map((plot, i) => {
          const stage = gardenStage(plot, Date.now(), growMs)
          const ready = stage === 2
          // Mutation hint: a different mature neighbor is adjacent.
          const neighborReady = plot && !ready && gardenNeighbors(i).some(j => {
            const nb = plots[j]
            return nb && nb.root !== plot.root && gardenStage(nb, Date.now(), growMs) === 2
          })
          return (
            <div key={i}>
              {!plot ? (
                <button onClick={() => setPickPlot(pickPlot === i ? null : i)}
                  className="w-full min-h-[76px] rounded-xl border-2 border-dashed border-neutral-300 dark:border-neutral-600 text-neutral-400 text-xl cursor-pointer hover:border-amber-400"
                  aria-label={`Plant plot ${i + 1}`}>
                  ＋
                </button>
              ) : (
                <button onClick={() => ready && doHarvest(i)} disabled={!ready}
                  className={`w-full min-h-[76px] rounded-xl border-2 p-1 text-center cursor-pointer transition-all ${ready ? 'border-yellow-400 dark:border-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 animate-pulse' : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800'}`}
                  aria-label={`${plot.root} ${ready ? 'ready to harvest' : 'growing'}`}>
                  <div className="text-2xl leading-none">{STAGE_EMOJI[Math.max(0, stage)]}</div>
                  <div className="text-sm font-serif leading-tight truncate" dir="rtl">{plot.root}</div>
                  <div className="text-[9px] text-neutral-400 tabular-nums">
                    {ready ? 'tap to harvest' : fmtLeft(plot.plantedAt + growMs - Date.now())}
                    {neighborReady ? ' · 🧬' : ''}
                  </div>
                </button>
              )}
            </div>
          )
        })}
      </div>

      {pickPlot != null && (
        <div className="mt-2 p-2 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <div className="text-[10px] text-neutral-500 dark:text-neutral-400 mb-1.5">
            Plant plot {pickPlot + 1} — costs {fmtBig(cost)} ✨ (15min of production)
          </div>
          {choices.length === 0 ? (
            <div className="text-[11px] text-neutral-500">No readable roots yet — own every letter of a root to plant it. Study letters first 👆</div>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {choices.map(r => (
                <button key={r} onClick={() => doPlant(pickPlot, r)}
                  disabled={(state.ohr || 0) < cost}
                  className="px-2.5 py-1.5 rounded-lg text-sm font-serif bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 cursor-pointer disabled:opacity-40" dir="rtl">
                  {r}
                </button>
              ))}
            </div>
          )}
          <button onClick={() => setPickPlot(null)} className="mt-1.5 text-[10px] text-neutral-400 hover:underline cursor-pointer">cancel</button>
        </div>
      )}

      {flash && (
        <div className="mt-2 p-2 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-300 dark:border-green-700 text-xs text-green-800 dark:text-green-200 text-center" aria-live="polite">
          {flash}
        </div>
      )}

      <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-2 text-center">
        Harvest = 30min ✨ + 5 🌟 + 1 root rep · 🧬 beside a different mature root: 25% mutation (+15 🌟 + neighbor rep)
      </p>
    </div>
  )
}
