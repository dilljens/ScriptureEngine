import React, { useState } from 'react'
import {
  WATCHMEN,
  WATCH_SEATS,
  WATCH_SWAP_COOLDOWN_MS,
  watchEffects,
  seatWatchman,
  watchCooldownLeft,
  totalOwned,
  saveIdleState,
} from '../lib/idle-game'

/**
 * WatchmenPanel — watchmen minigame (Cookie-Clicker Pantheon, Isaiah 62:6).
 *
 * Seat 3 of 6 watchmen on the walls. Seats scale the gift (Honor ×1.0, Wisdom ×0.6,
 * Learning ×0.3); every gift has a price, so the loadout is buildcraft.
 * Swapping a seat cools it for 4h. Unlocks once the workshop is real
 * (10+ letters owned or a root forged).
 */

function fmtCooldown(ms) {
  if (ms <= 0) return ''
  const h = Math.floor(ms / 3600000)
  const m = Math.ceil((ms % 3600000) / 60000)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function WatchmenPanel({ state, onUpdate }) {
  const [pickSeat, setPickSeat] = useState(null)
  const unlocked = totalOwned(state) >= 10 || (state.roots || 0) > 0

  if (!unlocked) {
    return (
      <div className="p-4 text-center">
        <div className="text-2xl mb-1">🎓</div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400">
          The watch convenes once your workshop is real — own <b>10 letters</b> or forge a root.
        </p>
      </div>
    )
  }

  const seats = state.sanhedrin?.seats || {}
  const fx = watchEffects(state)
  const effLine = [
    fx.global !== 1 && `✨ ×${fx.global.toFixed(2)} Ohr`,
    fx.cost !== 1 && `${fx.cost > 1 ? '+' : ''}${Math.round((fx.cost - 1) * 100)}% letter costs`,
    fx.tap !== 1 && `${fx.tap > 1 ? '+' : ''}${Math.round((fx.tap - 1) * 100)}% tap`,
    fx.kavod !== 1 && `+${Math.round((fx.kavod - 1) * 100)}% 🌟`,
    fx.offline !== 1 && `+${Math.round((fx.offline - 1) * 100)}% offline`,
    fx.milk !== 1 && `+${Math.round((fx.milk - 1) * 100)}% 🫒`,
  ].filter(Boolean).join(' · ') || 'No watchmen seated — no effects.'

  const doSwap = (seatId, watchId) => {
    const next = { ...state, sanhedrin: { seats: { ...(state.sanhedrin?.seats || {}) }, cooldowns: { ...(state.sanhedrin?.cooldowns || {}) } } }
    if (!seatWatchman(next, seatId, watchId)) return
    setPickSeat(null)
    onUpdate(next)
  }

  return (
    <div>
      <div className="grid grid-cols-3 gap-1.5">
        {WATCH_SEATS.map(seat => {
          const watch = WATCHMEN.find(s => s.id === seats[seat.id])
          const cd = watchCooldownLeft(state, seat.id)
          return (
            <button key={seat.id} onClick={() => setPickSeat(pickSeat === seat.id ? null : seat.id)}
              className={`p-2 rounded-xl border-2 text-center cursor-pointer transition-all min-h-[84px] ${watch ? 'border-violet-400 dark:border-violet-600 bg-violet-50 dark:bg-violet-900/20' : 'border-dashed border-neutral-300 dark:border-neutral-600'}`}
              aria-label={`${seat.name}: ${watch ? watch.name : 'empty'}`}>
              <div className="text-2xl leading-none">{watch ? watch.icon : '💺'}</div>
              <div className="text-[10px] font-semibold text-neutral-600 dark:text-neutral-300 truncate">
                {watch ? watch.name : seat.name}
              </div>
              <div className="text-[9px] text-neutral-400 tabular-nums">
                ×{seat.mult}{cd > 0 ? ` · ${fmtCooldown(cd)}` : ''}
              </div>
            </button>
          )
        })}
      </div>

      <p className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-2 text-center" aria-live="polite">
        {effLine}
      </p>

      {pickSeat && (
        <div className="mt-2 p-2 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <div className="text-[10px] text-neutral-500 dark:text-neutral-400 mb-1.5">
            Set which watchman on the {WATCH_SEATS.find(s => s.id === pickSeat)?.name}? Swapping cools the seat 4h.
          </div>
          <div className="space-y-1">
            {WATCHMEN.map(s => {
              const seatedElsewhere = Object.entries(seats).some(([k, v]) => v === s.id && k !== pickSeat)
              return (
                <button key={s.id} onClick={() => doSwap(pickSeat, s.id)}
                  className="w-full px-2.5 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700 text-left cursor-pointer hover:border-violet-400 active:scale-[0.99] min-h-[44px]">
                  <div className="text-xs font-medium text-neutral-700 dark:text-neutral-200">
                    <span className="mr-1">{s.icon}</span>{s.name}
                    {seatedElsewhere && <span className="ml-1 text-[9px] text-neutral-400">(moves seat)</span>}
                  </div>
                  <div className="text-[10px] text-neutral-500 dark:text-neutral-400">{s.desc}</div>
                </button>
              )
            })}
          </div>
          <button onClick={() => setPickSeat(null)} className="mt-1.5 text-[10px] text-neutral-400 hover:underline cursor-pointer">cancel</button>
        </div>
      )}
    </div>
  )
}
