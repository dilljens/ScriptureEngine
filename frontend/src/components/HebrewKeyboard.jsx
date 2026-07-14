import React, { useState, useRef, useCallback, useEffect } from 'react'

/**
 * On-screen Hebrew keyboard for typing practice.
 * Click letters to build Hebrew words without needing a Hebrew keyboard layout.
 *
 * Features:
 * - 3 rows of Hebrew consonants + 5 final forms
 * - Toggleable vowel row (niqqud marks)
 * - Long-press on a consonant shows vowel variant popup
 */

const LETTERS = [
  ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט'],
  ['י', 'כ', 'ך', 'ל', 'מ', 'ם', 'נ', 'ן', 'ס'],
  ['ע', 'פ', 'ף', 'צ', 'ץ', 'ק', 'ר', 'ש', 'ת'],
]

const VOWELS = [
  ['ַ', 'ָ', 'ִ', 'ֵ', 'ֶ', 'ֹ', 'ֻ', 'ְ'],
  ['ֲ', 'ֳ', 'ֱ', 'ּ', 'ׁ', 'ׂ'],
]

const LETTER_NAMES = {
  'א': 'Aleph', 'ב': 'Bet', 'ג': 'Gimel', 'ד': 'Dalet', 'ה': 'He',
  'ו': 'Vav', 'ז': 'Zayin', 'ח': 'Chet', 'ט': 'Tet',
  'י': 'Yod', 'כ': 'Kaf', 'ך': 'Kaf final', 'ל': 'Lamed', 'מ': 'Mem',
  'ם': 'Mem final', 'נ': 'Nun', 'ן': 'Nun final', 'ס': 'Samekh',
  'ע': 'Ayin', 'פ': 'Pe', 'ף': 'Pe final', 'צ': 'Tsade', 'ץ': 'Tsade final',
  'ק': 'Qof', 'ר': 'Resh', 'ש': 'Shin/Sin', 'ת': 'Tav',
}

const VOWEL_NAMES = {
  'ַ': 'Patah', 'ָ': 'Qamats', 'ִ': 'Hiriq', 'ֵ': 'Tsere',
  'ֶ': 'Segol', 'ֹ': 'Holam', 'ֻ': 'Qubuts', 'ְ': 'Sheva',
  'ֲ': 'Hataf Patah', 'ֳ': 'Hataf Qamats', 'ֱ': 'Hataf Segol',
  'ּ': 'Dagesh', 'ׁ': 'Shin dot', 'ׂ': 'Sin dot',
}

/** Common vowel combos shown on long-press */
const VOWEL_COMBOS = {
  'א': ['אַ', 'אָ', 'אִ', 'אֵ', 'אֶ', 'אֹ', 'אֻ'],
  'ב': ['בַּ', 'בָּ', 'בִּ', 'בֵּ', 'בֶּ', 'בֹּ', 'בְּ'],
  'ג': ['גַּ', 'גָּ', 'גִּ', 'גֵּ', 'גֶּ', 'גֹּ', 'גְּ'],
  'ד': ['דַּ', 'דָּ', 'דִּ', 'דֵּ', 'דֶּ', 'דֹּ', 'דְּ'],
  'ה': ['הַ', 'הָ', 'הִ', 'הֵ', 'הֶ', 'הֹ', 'הְ'],
  'ו': ['וַ', 'וָ', 'וִ', 'וֵ', 'וֶ', 'וְ'],
  'ז': ['זַ', 'זָ', 'זִ', 'זֵ', 'זֶ', 'זֹ', 'זְ'],
  'ח': ['חַ', 'חָ', 'חִ', 'חֵ', 'חֶ', 'חֹ', 'חֲ'],
  'ט': ['טַ', 'טָ', 'טִ', 'טֵ', 'טֶ', 'טֹ', 'טְ'],
  'י': ['יַ', 'יָ', 'יִ', 'יֵ', 'יֶ', 'יֹ', 'יְ'],
  'כ': ['כַּ', 'כָּ', 'כִּ', 'כֵּ', 'כֶּ', 'כֹּ', 'כְּ'],
  'ך': ['ךְ'],
  'ל': ['לַ', 'לָ', 'לִ', 'לֵ', 'לֶ', 'לֹ', 'לְ'],
  'מ': ['מַ', 'מָ', 'מִ', 'מֵ', 'מֶ', 'מֹ', 'מְ'],
  'ם': ['םְ'],
  'נ': ['נַ', 'נָ', 'נִ', 'נֵ', 'נֶ', 'נֹ', 'נְ'],
  'ן': ['ןְ'],
  'ס': ['סַ', 'סָ', 'סִ', 'סֵ', 'סֶ', 'סֹ', 'סְ'],
  'ע': ['עַ', 'עָ', 'עִ', 'עֵ', 'עֶ', 'עֹ', 'עֲ'],
  'פ': ['פַּ', 'פָּ', 'פִּ', 'פֵּ', 'פֶּ', 'פֹּ', 'פְּ'],
  'ף': ['ףְ'],
  'צ': ['צַ', 'צָ', 'צִ', 'צֵ', 'צֶ', 'צֹ', 'צְ'],
  'ץ': ['ץְ'],
  'ק': ['קַ', 'קָ', 'קִ', 'קֵ', 'קֶ', 'קֹ', 'קְ'],
  'ר': ['רַ', 'רָ', 'רִ', 'רֵ', 'רֶ', 'רֹ', 'רְ'],
  'ש': ['שַׁ', 'שָׁ', 'שִׁ', 'שֵׁ', 'שֶׁ', 'שֹׁ', 'שְׁ', 'שַׂ', 'שָׂ', 'שִׂ', 'שֵׂ', 'שֶׂ'],
  'ת': ['תַּ', 'תָּ', 'תִּ', 'תֵּ', 'תֶּ', 'תֹּ', 'תְּ'],
}

export default function HebrewKeyboard({ onCharClick, onBackspace, onClear, onDone, value }) {
  const [showVowels, setShowVowels] = useState(false)
  const [longPressLetter, setLongPressLetter] = useState(null)
  const [popupPos, setPopupPos] = useState({})
  const longPressTimer = useRef(null)
  const popupRef = useRef(null)

  // Cancel long-press on any click outside
  useEffect(() => {
    const handler = () => {
      if (longPressTimer.current) {
        clearTimeout(longPressTimer.current)
        longPressTimer.current = null
      }
      setLongPressLetter(null)
    }
    window.addEventListener('click', handler)
    window.addEventListener('scroll', handler)
    return () => {
      window.removeEventListener('click', handler)
      window.removeEventListener('scroll', handler)
    }
  }, [])

  const handlePointerDown = useCallback((letter, e) => {
    if (longPressTimer.current) clearTimeout(longPressTimer.current)
    // Start long-press timer
    longPressTimer.current = setTimeout(() => {
      const combos = VOWEL_COMBOS[letter]
      if (combos && combos.length > 0) {
        const rect = e.currentTarget.getBoundingClientRect()
        setPopupPos({
          top: rect.top - 10,
          left: rect.left + rect.width / 2,
        })
        setLongPressLetter(letter)
      }
      longPressTimer.current = null
    }, 500)
  }, [])

  const handlePointerUp = useCallback((letter) => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
      // If timer hasn't fired yet, this is a regular click
      if (!longPressLetter) {
        onCharClick(letter)
      }
    }
  }, [onCharClick, longPressLetter])

  const handleVowelComboClick = useCallback((combo) => {
    onCharClick(combo)
    setLongPressLetter(null)
  }, [onCharClick])

  // Close popup with Escape
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') setLongPressLetter(null)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="w-full max-w-md mx-auto relative">
      {/* Input display */}
      <div className="mb-3 p-3 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 text-right" dir="rtl">
        <span className="text-2xl font-serif leading-relaxed break-all" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
          {value || '‎'}
        </span>
      </div>

      {/* Vowel toggle button */}
      <div className="flex justify-center gap-2 mb-2">
        <button
          onClick={() => setShowVowels(!showVowels)}
          className={`px-3 py-1 rounded-lg text-[10px] font-medium transition-colors cursor-pointer ${
            showVowels
              ? 'bg-amber-500 text-white'
              : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-300 dark:hover:bg-neutral-600'
          }`}
          title="Toggle niqqud (vowel marks)"
        >
          {showVowels ? 'Niqqud ▴' : 'Niqqud ▾'}
        </button>
      </div>

      {/* Vowel row (toggleable) */}
      {showVowels && (
        <div className="mb-2">
          {VOWELS.map((row, ri) => (
            <div key={ri} className="flex justify-center gap-1 mb-1">
              {row.map((vowel) => (
                <button
                  key={vowel}
                  onClick={() => onCharClick(vowel)}
                  className="w-9 h-9 flex items-center justify-center rounded-lg bg-amber-50 dark:bg-amber-900/30 hover:bg-amber-100 dark:hover:bg-amber-900/50 border border-amber-200 dark:border-amber-700 text-lg font-serif cursor-pointer transition-colors active:scale-95"
                  style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
                  title={VOWEL_NAMES[vowel] || vowel}
                  dir="rtl"
                >
                  {vowel}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* Keyboard rows */}
      {LETTERS.map((row, ri) => (
        <div key={ri} className="flex justify-center gap-1 mb-1">
          {row.map((letter) => (
            <button
              key={letter}
              onPointerDown={(e) => handlePointerDown(letter, e)}
              onPointerUp={() => handlePointerUp(letter)}
              onPointerLeave={() => {
                if (longPressTimer.current && !longPressLetter) {
                  clearTimeout(longPressTimer.current)
                  longPressTimer.current = null
                }
              }}
              className="w-10 h-10 flex items-center justify-center rounded-lg bg-neutral-100 dark:bg-neutral-700 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 border border-neutral-200 dark:border-neutral-600 text-lg font-serif cursor-pointer transition-colors active:scale-95 select-none"
              style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
              title={LETTER_NAMES[letter] || letter}
              dir="rtl"
            >
              {letter}
            </button>
          ))}
        </div>
      ))}

      {/* Long-press popup */}
      {longPressLetter && (
        <div
          ref={popupRef}
          className="fixed z-50 transform -translate-x-1/2 -translate-y-full"
          style={{ top: popupPos.top, left: popupPos.left }}
        >
          <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-xl border border-neutral-200 dark:border-neutral-700 p-2">
            <div className="flex items-center gap-1.5 mb-1 px-1">
              <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
                {LETTER_NAMES[longPressLetter]} + vowel
              </span>
            </div>
            <div className="flex flex-wrap justify-center gap-1 max-w-[200px]">
              {(VOWEL_COMBOS[longPressLetter] || []).map((combo) => (
                <button
                  key={combo}
                  onClick={() => handleVowelComboClick(combo)}
                  className="w-10 h-10 flex items-center justify-center rounded-lg bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 border border-indigo-200 dark:border-indigo-700 text-lg font-serif cursor-pointer transition-colors active:scale-95"
                  style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
                  dir="rtl"
                >
                  {combo}
                </button>
              ))}
            </div>
            <button
              onClick={() => setLongPressLetter(null)}
              className="mt-1 w-full text-center text-[10px] text-neutral-400 hover:text-neutral-600 cursor-pointer py-1"
            >
              ✕ close
            </button>
          </div>
        </div>
      )}

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
