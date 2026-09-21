import React from 'react'

/**
 * RatingButtons — the single Again/Hard/Good/Easy control used by every
 * FSRS review surface (scripture memorize + Hebrew vocab). Same algorithm
 * behind both (lib/api/fsrs.py), same look here.
 *
 * Props:
 *   intervals — {1:{label},…} next-review waits (Anki-style), or null
 *   onRate    — (rating 1-4) => void
 *   variant   — 'row' (memorize) | 'grid' (Hebrew vocab)
 *   showKeys  — show the 1-4 key hints (keyboard-shortcut surfaces)
 *   disabled  — disable all buttons (e.g. while submitting)
 */
const DEFS = [
  { val: 1, label: 'Again', desc: 'Forgot', color: 'bg-red-500 hover:bg-red-600' },
  { val: 2, label: 'Hard', desc: 'Struggled', color: 'bg-amber-500 hover:bg-amber-600' },
  { val: 3, label: 'Good', desc: 'Recalled', color: 'bg-green-500 hover:bg-green-600' },
  { val: 4, label: 'Easy', desc: 'Instant', color: 'bg-blue-500 hover:bg-blue-600' },
]

export default function RatingButtons({ intervals, onRate, variant = 'row', showKeys = false, disabled = false }) {
  return (
    <div className={variant === 'grid' ? 'grid grid-cols-4 gap-2 pt-2' : 'flex gap-2 justify-center'}>
      {DEFS.map(b => (
        <button key={b.val}
          onClick={() => onRate?.(b.val)}
          disabled={disabled}
          title={`${b.label} — ${b.desc}`}
          className={`pressable flex flex-col items-center justify-center rounded-lg text-white cursor-pointer transition-colors disabled:opacity-40 ${b.color} ${
            variant === 'grid' ? 'py-3 text-xs font-medium' : 'px-4 py-2 text-sm font-medium min-w-[70px]'
          }`}>
          {showKeys && <span className="text-sm leading-tight">{b.val}</span>}
          <span>{b.label}</span>
          {intervals?.[b.val]?.label && (
            <span className="text-[11px] font-semibold opacity-95 leading-tight">{intervals[b.val].label}</span>
          )}
          <span className="text-[9px] opacity-80">{b.desc}</span>
        </button>
      ))}
    </div>
  )
}
