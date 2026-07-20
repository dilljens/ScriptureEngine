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


export default function HebrewPassageReader({ verseRef, onClose, readingLessonId }) {
  const [words, setWords] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeWord, setActiveWord] = useState(null)
  const [knownWords, setKnownWords] = useState(getKnownWords)
  const [verseText, setVerseText] = useState('')
  const [sidePanel, setSidePanel] = useState(true)
  const [readingInfo, setReadingInfo] = useState(null)
  const [showReadingNotes, setShowReadingNotes] = useState(false)
  const [audioCache, setAudioCache] = useState({})  // { word: audioUrl }
  const [audioPlaying, setAudioPlaying] = useState(null)
  const [verseAudio, setVerseAudio] = useState(null)  // { audio_url, word_timestamps }
  const [connections, setConnections] = useState([])  // notable connections for current verse
  const [showConnections, setShowConnections] = useState(false)
  const [vocabMastery, setVocabMastery] = useState({})  // { hebrew_word: mastery_level }
  const [studiedVocab, setStudiedVocab] = useState(new Set())  // set of hebrew words studied
  const [versePlaying, setVersePlaying] = useState(false)
  const [activeWordIdx, setActiveWordIdx] = useState(null)  // index of currently highlighted word during verse playback
  const popupRef = useRef(null)
  const audioElt = useRef(null)
  const verseAudioElt = useRef(null)
  const highlightInterval = useRef(null)

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

    // Fetch reading lesson content if this is a reading lesson
    if (readingLessonId) {
      fetch(`${API}/api/v1/hebrew/lesson/${readingLessonId}`).then(r => r.json()).then(d => {
        if (d.ok && d.data?.lesson) setReadingInfo(d.data.lesson)
      }).catch(() => {})
    }

    // Fetch verse audio (read-along data)
    fetch(`${API}/api/v1/read-along/${verseRef}`).then(r => r.json()).then(d => {
      if (d.ok && d.data) setVerseAudio(d.data)
    }).catch(() => {})

    // Fetch notable connections
    fetch(`${API}/api/v1/verses/${verseRef}/connections?limit=5&min_confidence=0.3`).then(r => r.json()).then(d => {
      if (d.ok && d.data?.connections) {
        // Collect all connections across layers, deduplicate by target
        const all = []
        const seen = new Set()
        for (const [, conns] of Object.entries(d.data.connections)) {
          for (const c of conns) {
            if (c.target && !seen.has(c.target)) {
              seen.add(c.target)
              all.push(c)
            }
          }
        }
        setConnections(all.slice(0, 5))
      }
    }).catch(() => {})

    // Fetch vocabulary mastery to highlight known words
    fetch(`${API}/api/v1/hebrew/curriculum`).then(r => r.json()).then(d => {
      if (d.ok && d.data?.nodes) {
        const studied = new Set()
        const mastery = {}
        for (const node of d.data.nodes) {
          if (node.category === 'word' && node.unlocked && node.mastery > 0) {
            const heb = node.title?.split(' — ')[0]?.trim()
            if (heb) {
              studied.add(heb)
              mastery[heb] = node.mastery || 0
            }
          }
        }
        setStudiedVocab(studied)
        setVocabMastery(mastery)
      }
    }).catch(() => {})
  }, [verseRef, readingLessonId])

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

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioElt.current) { audioElt.current.pause(); audioElt.current = null }
      if (verseAudioElt.current) { verseAudioElt.current.pause(); verseAudioElt.current = null }
      if (highlightInterval.current) clearInterval(highlightInterval.current)
    }
  }, [])

  // Play entire verse audio with word highlighting
  const playVerse = useCallback(() => {
    if (versePlaying) {
      // Toggle off
      if (verseAudioElt.current) verseAudioElt.current.pause()
      if (highlightInterval.current) clearInterval(highlightInterval.current)
      setVersePlaying(false)
      setActiveWordIdx(null)
      return
    }

    // Try real audio first
    if (verseAudio?.word_timestamps?.length > 0 && verseAudio?.audio_url) {
      const audio = new Audio(verseAudio.audio_url)
      verseAudioElt.current = audio
      audio.onended = () => { setVersePlaying(false); setActiveWordIdx(null) }
      audio.onerror = () => { /* fallback to TTS */ }
      setVersePlaying(true)
      audio.play().catch(() => { /* fallback handled below */ })

      // Highlight words based on timestamps
      const timestamps = verseAudio.word_timestamps
      if (highlightInterval.current) clearInterval(highlightInterval.current)
      highlightInterval.current = setInterval(() => {
        if (!audio || audio.paused || audio.ended) {
          clearInterval(highlightInterval.current)
          highlightInterval.current = null
          return
        }
        const currentTime = audio.currentTime
        let foundIdx = -1
        for (let i = 0; i < timestamps.length; i++) {
          const t = timestamps[i]
          if (currentTime >= t.start && currentTime < t.end) {
            foundIdx = i
            break
          }
        }
        setActiveWordIdx(foundIdx >= 0 ? foundIdx : null)
      }, 100)
      return
    }

    // Fallback: browser TTS
    if (!window.speechSynthesis) return
    if (versePlaying) { window.speechSynthesis.cancel(); setVersePlaying(false); return }
    const hebText = words.map(w => w.hebrew).join(' ')
    const utterance = new SpeechSynthesisUtterance(hebText.replace(/[\u0591-\u05bd\u05bf\u05c1-\u05c7]/g, ''))
    utterance.lang = 'he-IL'
    utterance.rate = 0.8
    utterance.onend = () => setVersePlaying(false)
    setVersePlaying(true)
    window.speechSynthesis.speak(utterance)
  }, [verseAudio, versePlaying, words])

  // Cancel audio on verseRef change
  useEffect(() => {
    return () => {
      if (highlightInterval.current) clearInterval(highlightInterval.current)
    }  }, [verseRef])

  // Play audio for a single word
  const playAudio = useCallback(async (word) => {
    if (!word) return
    // Check cache first
    if (audioCache[word]) {
      if (audioElt.current) { audioElt.current.pause(); audioElt.current = null }
      const audio = new Audio(audioCache[word])
      audioElt.current = audio
      audio.onended = () => setAudioPlaying(null)
      audio.onerror = () => setAudioPlaying(null)
      audio.play().then(() => setAudioPlaying(word)).catch(() => setAudioPlaying(null))
      return
    }
    // Fetch audio URL
    try {
      const r = await fetch(`${API}/api/v1/hebrew/audio/${encodeURIComponent(word)}`)
      const d = await r.json()
      if (d.ok && d.data?.audio_url) {
        setAudioCache(prev => ({ ...prev, [word]: d.data.audio_url }))
        if (audioElt.current) { audioElt.current.pause(); audioElt.current = null }
        const audio = new Audio(d.data.audio_url)
        audioElt.current = audio
        audio.onended = () => setAudioPlaying(null)
        audio.onerror = () => setAudioPlaying(null)
        audio.play().then(() => setAudioPlaying(word)).catch(() => setAudioPlaying(null))
      }
    } catch {}
  }, [audioCache])

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
            {verseAudio && (
              <button onClick={playVerse}
                className={`px-2 py-1 rounded text-[10px] font-medium cursor-pointer transition-colors ${
                  versePlaying
                    ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                }`}>
                {versePlaying ? '⏹ Stop' : '🔊 Play Verse'}
              </button>
            )}
            {readingInfo && (
              <button onClick={() => setShowReadingNotes(!showReadingNotes)}
                className={`px-2 py-1 rounded text-[10px] font-medium cursor-pointer transition-colors ${
                  showReadingNotes
                    ? 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                }`}>
                📖 Notes
              </button>
            )}
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

        {/* Reading Notes panel */}
        {showReadingNotes && readingInfo && (
          <div className="px-4 py-3 border-b border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/10">
            <h3 className="text-[10px] font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2">
              {readingInfo.title || 'Reading Notes'}
            </h3>
            <div className="text-xs text-neutral-700 dark:text-neutral-300 leading-relaxed whitespace-pre-line">
              {readingInfo.explanation || ''}
            </div>
            {readingInfo.key_points?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {readingInfo.key_points.map((kp, i) => (
                  <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400">
                    {kp}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

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
                      isHighlighted={activeWordIdx === i}
                      isKnown={knownWords.has(w.hebrew)}
                      isStudied={studiedVocab.has(w.hebrew.replace(/[\/].*$/, '').replace(/[ְִֵֶַָֹֻּׂ̇̇̇]/g, ''))}
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
                    <div className="flex items-center gap-2">
                      <button onClick={() => playAudio(activeWord.hebrew)}
                        className={`px-2 py-1 rounded text-[10px] font-medium cursor-pointer transition-colors ${
                          audioPlaying === activeWord.hebrew
                            ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                            : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                        }`}>
                        {audioPlaying === activeWord.hebrew ? '🔊 Playing' : '🔈 Play'}
                      </button>
                      <button onClick={() => toggleKnown(activeWord.hebrew)}
                        className={`px-2.5 py-1 rounded text-[10px] font-medium cursor-pointer transition-colors ${
                          knownWords.has(activeWord.hebrew)
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                        }`}>
                        {knownWords.has(activeWord.hebrew) ? '✓ Known' : 'Mark Known'}
                      </button>
                    </div>
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

              {/* Connections indicator */}
              {connections.length > 0 && (
                <div className="mb-4">
                  <button onClick={() => setShowConnections(!showConnections)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-medium bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/30 border border-purple-200 dark:border-purple-700 cursor-pointer transition-colors">
                    <span>🔗</span>
                    <span>{connections.length} connection{connections.length > 1 ? 's' : ''} with other scriptures</span>
                    <span className="text-[9px]">{showConnections ? '▲' : '▼'}</span>
                  </button>
                  {showConnections && (
                    <div className="mt-2 space-y-1.5">
                      {connections.map((c, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-white dark:bg-neutral-800 border border-purple-200 dark:border-purple-700">
                          <div className="flex items-center justify-between mb-0.5">
                            <span className="text-[10px] font-mono font-medium text-purple-700 dark:text-purple-300">{c.target}</span>
                            <span className="text-[8px] px-1 py-0.5 rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 uppercase">{c.type}</span>
                          </div>
                          <div className="text-[9px] text-neutral-500 dark:text-neutral-400">
                            {c.subtype && <span>via {c.subtype}</span>}
                            {c.confidence && <span> · confidence: {c.confidence}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
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

function WordChip({ word, isActive, isHighlighted, isKnown, isStudied, onClick }) {
  return (
    <button onClick={onClick}
      className={`inline-block px-1.5 py-0.5 rounded text-lg transition-all cursor-pointer ${
        isHighlighted
          ? 'bg-yellow-300 dark:bg-yellow-500/50 text-neutral-900 dark:text-neutral-100 scale-110 shadow-md ring-2 ring-yellow-400 dark:ring-yellow-300'
          : isActive
            ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200 shadow-sm scale-110'
            : isKnown
              ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200 hover:bg-green-100 dark:hover:bg-green-900/40'
              : isStudied
                ? 'bg-sky-100 dark:bg-sky-900/20 text-sky-800 dark:text-sky-200 hover:bg-sky-200 dark:hover:bg-sky-900/40 ring-1 ring-sky-300 dark:ring-sky-700'
                : 'bg-amber-50 dark:bg-amber-900/10 text-amber-900 dark:text-amber-200 hover:bg-amber-100 dark:hover:bg-amber-900/30'
      }`}
      title={`${word.english || ''} · ${parseMorph(word.morph) || word.morph || ''}`}>
      {word.hebrew}
    </button>
  )
}
