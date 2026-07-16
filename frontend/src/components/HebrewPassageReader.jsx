/**
 * HebrewPassageReader — LingQ-style Hebrew passage study mode.
 *
 * Renders Hebrew text word-by-word. Click any word to see:
 *   - English gloss / translation
 *   - Morphological parse (verb stem, tense, person, etc.)
 *   - Strong's number with lexicon link
 *   - Gematria values
 *
 * Side panel shows passage word list with "known" / "learning" status
 * persisted to localStorage.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'

const API = window.__API_URL__ || ''

// ── Morphology parser ──
// Translates morphology codes like "HVqp3ms" into human-readable labels
function parseMorph(code) {
  if (!code) return ''
  const parts = []
  // Language prefix
  if (code.startsWith('H')) parts.push('Hebrew')
  else if (code.startsWith('G')) parts.push('Greek')
  else return code

  const rest = code.slice(1)
  // Part of speech
  const posMap = {
    'V': 'Verb',
    'N': 'Noun',
    'A': 'Adjective',
    'R': 'Preposition',
    'D': 'Adverb',
    'C': 'Conjunction',
    'P': 'Pronoun',
    'T': 'Particle/Direct Object',
    'M': 'Number',
    'X': 'Interjection',
  }
  const pos = rest[0]
  if (posMap[pos]) parts.push(posMap[pos])

  // Verb specifics (after 'V')
  if (pos === 'V' && rest.length >= 5) {
    const stemMap = { 'q': 'Qal', 'n': 'Niphal', 'p': 'Piel', 'h': 'Hiphil',
                      'u': 'Hophal', 't': 'Hithpael', 'd': 'Pual', 'm': 'Hithpolel' }
    const tenseMap = { 'p': 'Perfect', 'q': 'Imperfect', 'i': 'Imperative',
                       'c': 'Participle', 'h': 'Cohortative', 'j': 'Jussive', 'v': 'Infinitive' }
    const personMap = { '1': '1st', '2': '2nd', '3': '3rd' }
    const genderMap = { 'm': 'masculine', 'f': 'feminine', 'c': 'common' }
    const numberMap = { 's': 'singular', 'p': 'plural', 'd': 'dual' }

    const stem = rest[1]
    const tense = rest[2]
    const person = rest[3]
    const gender = rest[4]
    const number = rest.length > 5 ? rest[5] : ''

    if (stemMap[stem]) parts.push(stemMap[stem])
    if (tenseMap[tense]) parts.push(tenseMap[tense])
    if (personMap[person]) parts.push(personMap[person])
    if (genderMap[gender]) parts.push(genderMap[gender])
    if (numberMap[number]) parts.push(numberMap[number])
  }

  // Noun specifics
  if (pos === 'N' && rest.length >= 3) {
    const nGenderMap = { 'm': 'masculine', 'f': 'feminine', 'c': 'common' }
    const nNumberMap = { 's': 'singular', 'p': 'plural', 'd': 'dual' }
    const nStateMap = { 'a': 'absolute', 'c': 'construct', 'd': 'determined' }
    if (nGenderMap[rest[1]]) parts.push(nGenderMap[rest[1]])
    if (nNumberMap[rest[2]]) parts.push(nNumberMap[rest[2]])
    if (rest.length > 3 && nStateMap[rest[3]]) parts.push(nStateMap[rest[3]])
  }

  return parts.join(' · ')
}


// ── Word status persistence (localStorage) ──
function getKnownWords() {
  try {
    return new Set(JSON.parse(localStorage.getItem('heb_passage_known') || '[]'))
  } catch { return new Set() }
}

function saveKnownWords(set) {
  localStorage.setItem('heb_passage_known', JSON.stringify([...set]))
}


export default function HebrewPassageReader({ verseRef, onClose }) {
  const [words, setWords] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeWord, setActiveWord] = useState(null)
  const [knownWords, setKnownWords] = useState(getKnownWords)
  const [verseText, setVerseText] = useState('')
  const [sidePanel, setSidePanel] = useState(true)
  const popupRef = useRef(null)

  // Fetch word data
  useEffect(() => {
    if (!verseRef) return
    setLoading(true)
    setActiveWord(null)

    // Fetch grammar (word-level) data and verse text
    Promise.all([
      fetch(`${API}/api/v1/verses/${verseRef}/grammar`).then(r => r.json()),
      fetch(`${API}/api/v1/verses/${verseRef}`).then(r => r.json()),
    ]).then(([grammar, verse]) => {
      if (grammar.ok && grammar.data?.words) {
        setWords(grammar.data.words)
      }
      if (verse.ok && verse.data) {
        setVerseText(verse.data.text_hebrew || verse.data.text_english || '')
      }
    }).catch(() => {}).finally(() => setLoading(false))
  }, [verseRef])

  // Close popup on outside click
  useEffect(() => {
    function handleClick(e) {
      if (popupRef.current && !popupRef.current.contains(e.target)) {
        setActiveWord(null)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const toggleKnown = useCallback((hebrew) => {
    setKnownWords(prev => {
      const next = new Set(prev)
      if (next.has(hebrew)) next.delete(hebrew)
      else next.add(hebrew)
      saveKnownWords(next)
      return next
    })
  }, [])

  const wordStats = {
    total: words.length,
    known: words.filter(w => knownWords.has(w.hebrew)).length,
    learning: words.filter(w => !knownWords.has(w.hebrew)).length,
  }

  return (
    <div className="flex h-full">
      {/* Main passage area */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-sm border-b border-neutral-200 dark:border-neutral-700 px-4 py-2.5 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Passage Study</h2>
            <span className="text-[11px] text-neutral-400 dark:text-neutral-500 font-mono">{verseRef}</span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setSidePanel(!sidePanel)}
              className="px-2 py-1 rounded text-[10px] font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer">
              {sidePanel ? 'Hide List' : 'Show List'}
            </button>
            <button onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 cursor-pointer">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <div className="p-4 md:p-6">
          {loading ? (
            <div className="flex items-center justify-center py-20 text-neutral-400 text-sm">
              <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              Loading word data…
            </div>
          ) : words.length === 0 ? (
            <div className="text-center py-20 text-neutral-400 dark:text-neutral-500">
              <p className="text-sm">No word-level data available for {verseRef}.</p>
              <p className="text-[11px] mt-1">Hebrew text with morphology is needed for passage study mode.</p>
            </div>
          ) : (
            <>
              {/* Word-by-word Hebrew text */}
              <div className="mb-6 p-4 md:p-6 bg-white dark:bg-neutral-800/30 border border-neutral-200 dark:border-neutral-700 rounded-lg"
                style={{ direction: 'rtl', fontFamily: '"SBL Hebrew", "Times New Roman", serif' }}>
                <div className="flex flex-wrap gap-2 justify-center leading-loose">
                  {words.map((w, i) => (
                    <WordChip
                      key={i}
                      word={w}
                      isActive={activeWord?.hebrew === w.hebrew && activeWord?.index === i}
                      isKnown={knownWords.has(w.hebrew)}
                      onClick={() => setActiveWord(activeWord?.hebrew === w.hebrew && activeWord?.index === i ? null : { ...w, index: i })}
                    />
                  ))}
                </div>
              </div>

              {/* Active word popup */}
              {activeWord && (
                <div ref={popupRef} className="mb-6 p-4 border border-blue-200 dark:border-blue-800 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-hebrew-biblical" style={{ direction: 'rtl' }}>{activeWord.hebrew}</span>
                      <div>
                        <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{activeWord.english || '—'}</div>
                        <div className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-0.5">
                          {activeWord.lemma && <span className="mr-2">Strong's {activeWord.lemma}</span>}
                          {activeWord.gematria?.standard > 0 && <span>Gematria: {activeWord.gematria.standard}</span>}
                        </div>
                      </div>
                    </div>
                    <button onClick={() => toggleKnown(activeWord.hebrew)}
                      className={`px-2.5 py-1 rounded text-[10px] font-medium cursor-pointer transition-colors ${
                        knownWords.has(activeWord.hebrew)
                          ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                          : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                      }`}>
                      {knownWords.has(activeWord.hebrew) ? '✓ Known' : 'Mark Known'}
                    </button>
                  </div>
                  <div className="text-[11px] text-neutral-600 dark:text-neutral-400">
                    <div><strong>Morphology:</strong> {parseMorph(activeWord.morph) || activeWord.morph || '—'}</div>
                    <div className="mt-1"><strong>Morph code:</strong> <code className="text-[10px] bg-blue-100 dark:bg-blue-900/40 px-1 rounded">{activeWord.morph || '—'}</code></div>
                    {activeWord.gematria && (
                      <div className="mt-1 flex gap-3 text-[10px]">
                        {activeWord.gematria.standard > 0 && <span>Standard: <strong>{activeWord.gematria.standard}</strong></span>}
                        {activeWord.gematria.ordinal > 0 && <span>Ordinal: <strong>{activeWord.gematria.ordinal}</strong></span>}
                        {activeWord.gematria.reduced > 0 && <span>Reduced: <strong>{activeWord.gematria.reduced}</strong></span>}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* English text for reference */}
              {verseText && (
                <details className="text-xs text-neutral-400 dark:text-neutral-500">
                  <summary className="cursor-pointer hover:text-neutral-600 dark:hover:text-neutral-300">Show English</summary>
                  <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{verseText}</p>
                </details>
              )}
            </>
          )}
        </div>
      </div>

      {/* Side panel — word list */}
      {sidePanel && (
        <aside className="hidden md:flex flex-col w-64 border-l border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900">
          <div className="px-3 py-2.5 border-b border-neutral-200 dark:border-neutral-700">
            <h3 className="text-[11px] font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Word List</h3>
            <div className="flex gap-3 mt-1 text-[10px] text-neutral-400 dark:text-neutral-500">
              <span>{wordStats.total} words</span>
              <span className="text-green-500">{wordStats.known} known</span>
              <span className="text-amber-500">{wordStats.learning} learning</span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {words.map((w, i) => (
                <button key={i} onClick={() => setActiveWord({ ...w, index: i })}
                  className={`w-full text-left px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors cursor-pointer ${
                    activeWord?.hebrew === w.hebrew && activeWord?.index === i ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                  }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-hebrew-biblical" style={{ direction: 'rtl' }}>{w.hebrew}</span>
                    {knownWords.has(w.hebrew) && <span className="text-[9px] text-green-500">✓</span>}
                  </div>
                  <div className="text-[10px] text-neutral-400 dark:text-neutral-500 truncate">
                    {w.english || '—'}
                  </div>
                  <div className="text-[9px] text-neutral-300 dark:text-neutral-600 truncate">
                    {parseMorph(w.morph) || w.morph || ''}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Word Chip Component
// ═══════════════════════════════════════════════════════════════════════

function WordChip({ word, isActive, isKnown, onClick }) {
  return (
    <button onClick={onClick}
      className={`inline-block px-1.5 py-0.5 rounded text-lg transition-all cursor-pointer ${
        isActive
          ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200 shadow-sm scale-110'
          : isKnown
            ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200 hover:bg-green-100 dark:hover:bg-green-900/40'
            : 'bg-amber-50 dark:bg-amber-900/10 text-amber-900 dark:text-amber-200 hover:bg-amber-100 dark:hover:bg-amber-900/30'
      }`}
      title={`${word.english || ''} · ${parseMorph(word.morph) || word.morph || ''}`}>
      {word.hebrew}
    </button>
  )
}
