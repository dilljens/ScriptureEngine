import React from 'react'

/**
 * On-screen Hebrew keyboard for typing practice.
 * Click letters to build Hebrew words without needing a Hebrew keyboard layout.
 */

const LETTERS = [
  // Row 1
  ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט'],
  // Row 2
  ['י', 'כ', 'ך', 'ל', 'מ', 'ם', 'נ', 'ן', 'ס'],
  // Row 3
  ['ע', 'פ', 'ף', 'צ', 'ץ', 'ק', 'ר', 'ש', 'ת'],
]

const LETTER_NAMES = {
  'א': 'Aleph', 'ב': 'Bet', 'ג': 'Gimel', 'ד': 'Dalet', 'ה': 'He',
  'ו': 'Vav', 'ז': 'Zayin', 'ח': 'Chet', 'ט': 'Tet',
  'י': 'Yod', 'כ': 'Kaf', 'ך': 'Kaf final', 'ל': 'Lamed', 'מ': 'Mem',
  'ם': 'Mem final', 'נ': 'Nun', 'ן': 'Nun final', 'ס': 'Samekh',
  'ע': 'Ayin', 'פ': 'Pe', 'ף': 'Pe final', 'צ': 'Tsade', 'ץ': 'Tsade final',
  'ק': 'Qof', 'ר': 'Resh', 'ש': 'Shin/Sin', 'ת': 'Tav',
}

export default function HebrewKeyboard({ onCharClick, onBackspace, onClear, onDone, value }) {
  return (
    <div className="w-full max-w-md mx-auto">
      {/* Input display */}
      <div className="mb-3 p-3 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-right" dir="rtl">
        <span className="text-2xl font-serif leading-relaxed" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
          {value || '‎'}
        </span>
      </div>

      {/* Keyboard rows */}
      {LETTERS.map((row, ri) => (
        <div key={ri} className="flex justify-center gap-1 mb-1">
          {row.map((letter) => (
            <button
              key={letter}
              onClick={() => onCharClick(letter)}
              className="w-10 h-10 flex items-center justify-center rounded-lg bg-neutral-100 dark:bg-neutral-700 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 border border-neutral-200 dark:border-neutral-600 text-lg font-serif cursor-pointer transition-colors active:scale-95"
              style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
              title={LETTER_NAMES[letter] || letter}
              dir="rtl"
            >
              {letter}
            </button>
          ))}
        </div>
      ))}

      {/* Control buttons */}
      <div className="flex justify-center gap-2 mt-2">
        <button onClick={onBackspace}
          className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-600 hover:bg-neutral-300 dark:hover:bg-neutral-500 text-sm font-medium cursor-pointer transition-colors">
          ← Backspace
        </button>
        <button onClick={onClear}
          className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-600 hover:bg-neutral-300 dark:hover:bg-neutral-500 text-sm font-medium cursor-pointer transition-colors">
          Clear
        </button>
        <button onClick={onDone}
          className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
          Done ✓
        </button>
      </div>
    </div>
  )
}
