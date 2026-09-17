import React, { useState, useEffect } from 'react'
import {
  SHUK_GOODS,
  SHUK_LOAN_HOURS,
  SHUK_DEBT_MULT,
  SHUK_DEBT_HOURS,
  shukQuote,
  buyShuk,
  sellShuk,
  shukDebt,
  takeShukLoan,
} from '../lib/idle-game'

/**
 * ShukPanel — market stalls minigame (Cookie-Clicker Stock Market).
 *
 * Five goods priced in production-seconds (auto-scales to your era) riding
 * smooth deterministic cycles — buy low, sell high. A 2% bid/ask spread
 * stops instant flips. "Learn on credit": +1h production now, −25% for 4h
 * after (one loan at a time, 24h cooldown).
 */

function fmtOhr(n) {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return Math.floor(n).toLocaleString()
}

function fmtWait(ms) {
  if (ms <= 0) return ''
  const h = Math.floor(ms / 3600000)
  const m = Math.ceil((ms % 3600000) / 60000)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

export default function ShukPanel({ state, perSec, onUpdate }) {
  const [, setNow] = useState(Date.now())
  const [flash, setFlash] = useState(null)

  // Prices breathe on minute cycles — refresh the board twice a minute.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30000)
    return () => clearInterval(t)
  }, [])

  const now = Date.now()
  const holdings = state.shuk?.holdings || {}
  const indebted = (state.shuk?.debtUntil || 0) > now
  const loanCd = Math.max(0, (state.shuk?.loanCooldownUntil || 0) - now)

  const trade = (fn, ...args) => {
    const next = { ...state, shuk: { ...(state.shuk || {}), holdings: { ...holdings } } }
    const res = fn(next, ...args)
    if (res) onUpdate(next)
    return res
  }

  const doLoan = () => {
    const next = { ...state, shuk: { ...(state.shuk || {}), holdings: { ...holdings } } }
    const granted = takeShukLoan(next, perSec || 0)
    if (!granted) return
    setFlash(`+${fmtOhr(granted)} ✨ on credit — −25% production for ${SHUK_DEBT_HOURS}h`)
    setTimeout(() => setFlash(null), 4000)
    onUpdate(next)
  }

  return (
    <div>
      <div className="space-y-1.5">
        {SHUK_GOODS.map(g => {
          const q = shukQuote(g.id, perSec || 0)
          const have = holdings[g.id] || 0
          return (
            <div key={g.id} className="p-2 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center gap-2">
                <span className="text-xl">{g.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-neutral-700 dark:text-neutral-200">
                    {g.name} <span className="text-neutral-400">{q.trend > 0 ? '📈' : q.trend < 0 ? '📉' : '➖'}</span>
                  </div>
                  <div className="text-[10px] text-neutral-500 tabular-nums">
                    {fmtOhr(q.ask)} ✨{have > 0 && <span> · holds {have}</span>}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => trade(buyShuk, g.id, 1, perSec || 0)}
                    disabled={(state.ohr || 0) < q.ask}
                    className="min-h-[44px] px-2.5 rounded-lg text-xs font-semibold bg-green-500 hover:bg-green-600 text-white disabled:opacity-40 cursor-pointer" aria-label={`Buy 1 ${g.name}`}>
                    +1
                  </button>
                  <button onClick={() => trade(buyShuk, g.id, 10, perSec || 0)}
                    disabled={(state.ohr || 0) < q.ask * 10}
                    className="min-h-[44px] px-2.5 rounded-lg text-xs font-semibold border border-green-500 text-green-600 dark:text-green-400 disabled:opacity-40 cursor-pointer" aria-label={`Buy 10 ${g.name}`}>
                    +10
                  </button>
                  <button onClick={() => trade(sellShuk, g.id, have, perSec || 0)}
                    disabled={have <= 0}
                    className="min-h-[44px] px-2.5 rounded-lg text-xs font-semibold border border-amber-500 text-amber-600 dark:text-amber-400 disabled:opacity-40 cursor-pointer" aria-label={`Sell all ${g.name}`}>
                    Sell
                  </button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <button onClick={doLoan} disabled={indebted || loanCd > 0}
        className={`mt-2 w-full min-h-[48px] p-2 rounded-xl text-xs font-semibold cursor-pointer active:scale-[0.99] ${indebted || loanCd > 0 ? 'border border-neutral-300 dark:border-neutral-600 text-neutral-400' : 'bg-indigo-600 hover:bg-indigo-700 text-white'}`}>
        {indebted
          ? `📜 Debt weighs −${Math.round((1 - SHUK_DEBT_MULT) * 100)}% for ${fmtWait((state.shuk.debtUntil || 0) - now)} more`
          : loanCd > 0
            ? `📜 Next credit in ${fmtWait(loanCd)}`
            : `📜 Learn on credit: +${SHUK_LOAN_HOURS}h ✨ now, −25% for ${SHUK_DEBT_HOURS}h`}
      </button>

      {flash && (
        <div className="mt-2 p-2 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-300 dark:border-indigo-700 text-xs text-indigo-800 dark:text-indigo-200 text-center" aria-live="polite">
          {flash}
        </div>
      )}

      <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-2 text-center">
        Prices breathe on slow cycles — buy the dips 📉, sell the crests 📈. 2% spread per trade.
      </p>
    </div>
  )
}
