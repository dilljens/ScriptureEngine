import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import CardQueue from './CardQueue'
import HebrewKeyboard from './HebrewKeyboard'
import { stripMorphSeparators } from '../lib/hebrew-utils'

/** Book ID → display name mapping for user-facing verse references */
const BOOK_NAMES = {
  gen: 'Genesis', exo: 'Exodus', lev: 'Leviticus', num: 'Numbers', deu: 'Deuteronomy',
  josh: 'Joshua', judg: 'Judges', ruth: 'Ruth', '1sam': '1 Samuel', '2sam': '2 Samuel',
  '1kgs': '1 Kings', '2kgs': '2 Kings', '1chr': '1 Chronicles', '2chr': '2 Chronicles',
  ezra: 'Ezra', neh: 'Nehemiah', esth: 'Esther', job: 'Job', psa: 'Psalms',
  prov: 'Proverbs', eccl: 'Ecclesiastes', song: 'Song of Solomon',
  isa: 'Isaiah', jer: 'Jeremiah', lam: 'Lamentations', ezek: 'Ezekiel',
  dan: 'Daniel', hos: 'Hosea', joel: 'Joel', amos: 'Amos', obad: 'Obadiah',
  jonah: 'Jonah', mic: 'Micah', nah: 'Nahum', hab: 'Habakkuk',
  zeph: 'Zephaniah', hag: 'Haggai', zech: 'Zechariah', mal: 'Malachi',
  matt: 'Matthew', mark: 'Mark', luke: 'Luke', john: 'John',
  acts: 'Acts', rom: 'Romans', '1cor': '1 Corinthians', '2cor': '2 Corinthians',
  gal: 'Galatians', eph: 'Ephesians', phil: 'Philippians', col: 'Colossians',
  '1thes': '1 Thessalonians', '2thes': '2 Thessalonians',
  '1tim': '1 Timothy', '2tim': '2 Timothy', titus: 'Titus', philem: 'Philemon',
  heb: 'Hebrews', james: 'James', '1pet': '1 Peter', '2pet': '2 Peter',
  '1john': '1 John', '2john': '2 John', '3john': '3 John', jude: 'Jude', rev: 'Revelation',
  '1ne': '1 Nephi', '2ne': '2 Nephi', jacob: 'Jacob', enos: 'Enos',
  jarom: 'Jarom', omni: 'Omni', wom: 'Words of Mormon',
  mosiah: 'Mosiah', alma: 'Alma', hel: 'Helaman', '3ne': '3 Nephi',
  '4ne': '4 Nephi', morm: 'Mormon', ether: 'Ether', moro: 'Moroni',
  dc: 'D&C', moses: 'Moses', abraham: 'Abraham', jsm: 'Joseph Smith—Matthew',
  jsh: 'Joseph Smith—History', aoff: 'Articles of Faith',
}

function formatRef(book, ch, vs) {
  const name = BOOK_NAMES[book.toLowerCase()] || book
  return vs ? `${name} ${ch}:${vs}` : vs ? `${name} ${ch}:${vs}` : `${name} ${ch}`
}

/** Split text on scripture references like gen.1.1, exo.3.14 or Gen 1:1, Exo 3:14 */
function renderTextWithRefs(text, onNavigate) {
  if (!text) return text

  // Split into segments: refs, Hebrew words, and plain text.
  // Matches: dotted refs (gen.1.1), colon refs (Gen 1:1), Hebrew words.
  const hebRe = /[\u0590-\u05FF\u05B0-\u05C7]+/g
  const dotRefRe = /\b([a-z]{2,6})\.(\d+)\.(\d+)\b/gi
  const colRefRe = /\b([A-Za-z][a-z]{2,6})\s+(\d+):(\d+)\b/g

  // Tokenize: split text into an array of {type, value} tokens
  const tokens = []
  let remaining = text
  let tokenId = 0

  while (remaining.length > 0) {
    // Try matching each pattern at the current position
    const dotMatch = dotRefRe.exec(remaining)
    const colMatch = colRefRe.exec(remaining)
    let hebMatch

    // Find the next Hebrew word by scanning from current position
    hebRe.lastIndex = 0
    const hebTest = hebRe.exec(remaining)
    const hebPos = hebTest ? hebTest.index : -1

    // Build list of all matches at current position
    const candidates = []
    if (dotMatch) candidates.push({ type: 'ref_dot', match: dotMatch, pos: dotMatch.index })
    if (colMatch) candidates.push({ type: 'ref_col', match: colMatch, pos: colMatch.index })
    if (hebPos >= 0) candidates.push({ type: 'hebrew', match: hebTest, pos: hebPos })

    if (candidates.length === 0) {
      // No more matches — emit remaining as text
      tokens.push({ type: 'text', value: remaining })
      break
    }

    // Sort by position, take the earliest
    candidates.sort((a, b) => a.pos - b.pos)
    const first = candidates[0]

    // Emit text before the match
    if (first.pos > 0) {
      tokens.push({ type: 'text', value: remaining.slice(0, first.pos) })
    }

    // Emit the match
    if (first.type === 'ref_dot') {
      const m = first.match
      tokens.push({ type: 'ref', book: m[1], ch: m[2], vs: m[3], raw: m[0] })
      remaining = remaining.slice(m.index + m[0].length)
    } else if (first.type === 'ref_col') {
      const m = first.match
      tokens.push({ type: 'ref', book: m[1], ch: m[2], vs: m[3], raw: m[0] })
      remaining = remaining.slice(m.index + m[0].length)
    } else if (first.type === 'hebrew') {
      const m = first.match
      tokens.push({ type: 'hebrew', value: m[0] })
      remaining = remaining.slice(m.index + m[0].length)
    }

    // Reset regex lastIndex for next iteration
    dotRefRe.lastIndex = 0
    colRefRe.lastIndex = 0
  }

  // Render tokens
  const elems = tokens.map((t, i) => {
    if (t.type === 'text') {
      return <span key={i}>{t.value}</span>
    }
    if (t.type === 'ref') {
      return (
        <button key={i}
          onClick={() => onNavigate?.(`${t.book.toLowerCase()}.${t.ch}`)}
          className="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer font-medium"
          title={`Open ${t.book}.${t.ch}`}>
          {t.raw}
        </button>
      )
    }
    if (t.type === 'hebrew') {
      const word = t.value
      const clean = word.replace(/[\u0591-\u05C7]/g, '').trim()
      return (
        <span key={i}
          onClick={(e) => {
            e.stopPropagation()
            window.dispatchEvent(new CustomEvent('word-click', {
              detail: { word: clean, wordIndex: 0, verseId: '', transliteration: '', english: '' }
            }))
          }}
          className="cursor-pointer hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          title={`Click to explore: ${clean}`}>
          {word}
        </span>
      )
    }
    return null
  })

  return <>{elems}</>
}

/**
 * HebrewLessonView — timed drills + targeted remediation + micro-scaffolding.
 *
 * Micro-scaffolding (Math Academy Ch. 14): 3 Knowledge Points per lesson.
 * KP1: Recognition (MC/TF) → worked example → practice
 * KP2: Recall (transliteration/cloze) → worked example → practice
 * KP3: Production (typing/recall) → worked example → practice
 * Must pass each KP before advancing to the next.
 *
 * Automaticity: each question has a time limit per type.
 * Timed out = incorrect (builds speed, not just accuracy).
 * Remediation: wrong answers trigger prerequisite review suggestions.
 */

const TYPE_COLORS = {
  multiple_choice: 'border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20',
  cloze: 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20',
  recall: 'border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-900/20',
  typing: 'border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20',
  transliteration: 'border-cyan-200 dark:border-cyan-800 bg-cyan-50 dark:bg-cyan-900/20',
}

// Dynamic time limit: scales with content difficulty.
// Base limits per type + extra time for longer text/answers.
function getTimeLimit(q) {
  if (!q) return 15
  const text = q.question_text || ''
  const wordCount = text.split(/\s+/).filter(Boolean).length
  const readingBonus = Math.max(0, Math.floor((wordCount - 10) / 5)) * 2  // +2s per 5 extra words

  let base = 15
  switch (q.question_type) {
    case 'multiple_choice': base = 6; break
    case 'true_false': base = 5; break
    case 'transliteration': base = 12; break
    case 'cloze': base = 18; break
    case 'recall': base = 15; break
    case 'typing': base = 30; break
  }

  // For questions with options, extra options = extra reading
  let optionBonus = 0
  if (q.options_json) {
    try {
      const opts = JSON.parse(q.options_json)
      optionBonus = Math.max(0, opts.length - 2) * 1.5  // +1.5s per extra option
    } catch {}
  }

  // For typing/cloze, longer expected answer = more time
  let answerBonus = 0
  if (['typing', 'cloze', 'recall'].includes(q.question_type)) {
    const ansWords = (q.correct_answer || '').split(/\s+/).filter(Boolean).length
    answerBonus = Math.max(0, ansWords - 1) * 3  // +3s per extra word in answer
  }

  return Math.round(base + readingBonus + optionBonus + answerBonus)
}

export default function HebrewLessonView({ nodeId, onBack, onNavigate, batchSize = 5 }) {
  const [node, setNode] = useState(null)
  const [practice, setPractice] = useState([])
  const [lessonContent, setLessonContent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [batch, setBatch] = useState(0)
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState({})
  const [timedOut, setTimedOut] = useState({}) // { questionIdx: true } if timer expired
  const [responseTimes, setResponseTimes] = useState({}) // { questionIdx: seconds }
  const [startTimes, setStartTimes] = useState({}) // { questionIdx: Date.now() }
  const [showKeyboard, setShowKeyboard] = useState(false)
  const [keyboardTarget, setKeyboardTarget] = useState(null)
  const [results, setResults] = useState({ correct: 0, total: 0, streak: 0, bestStreak: 0, totalTime: 0 })
  const [completed, setCompleted] = useState(false)
  const [remediation, setRemediation] = useState(null) // { node_id, title }[] for wrong answers
  const [kpState, setKpState] = useState({ kp1: null, kp2: null, kp3: null }) // which KPs passed
  const [currentKP, setCurrentKP] = useState(1) // 1,2,3
  const [flashcardMode, setFlashcardMode] = useState(false) // use CardQueue instead of batch
  const [fcards, setFcards] = useState([]) // flashcard card array
  const [audioPlaying, setAudioPlaying] = useState(null)
  const audioRef = useRef(null)
  const timersRef = useRef({})

  // Load lesson data
  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetch(`/api/v1/hebrew/lesson/${nodeId}`).then(r => r.json()),
      fetch(`/api/v1/hebrew/practice/${nodeId}`).then(r => r.json()),
    ])
      .then(([nodeRes, practiceRes]) => {
        if (!nodeRes.ok) throw new Error(nodeRes.detail || 'Failed to load')
        setNode(nodeRes.data)
        let content = nodeRes.data.lesson || nodeRes.data.content || ''
        if (typeof content === 'object') content = JSON.stringify(content, null, 2)
        setLessonContent(content)
        setPractice(practiceRes.data?.items || [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [nodeId])

  // Start timers when batch questions load
  useEffect(() => {
    if (!batchQuestions.length || Object.keys(submitted).length > 0) return
    const now = Date.now()
    const newStartTimes = {}
    batchQuestions.forEach((q, i) => {
      const idx = startIdx + i
      newStartTimes[idx] = now
    })
    setStartTimes(newStartTimes)

    // Clear previous timers
    Object.values(timersRef.current).forEach(clearTimeout)
    timersRef.current = {}

    // Start per-question timers
    batchQuestions.forEach((q, i) => {
      const idx = startIdx + i
      const limit = getTimeLimit(q) || 15
      timersRef.current[idx] = setTimeout(() => {
        setTimedOut(prev => ({ ...prev, [idx]: true }))
        // Auto-submit on timeout: mark unanswered as incorrect
        setSubmitted(prev => {
          if (idx in prev) return prev
          return { ...prev, [idx]: false }
        })
        setResponseTimes(prev => ({ ...prev, [idx]: limit }))
      }, limit * 1000)
    })

    return () => { Object.values(timersRef.current).forEach(clearTimeout) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batch, nodeId])

  // Convert practice questions to cards for CardQueue flashcard mode
  const practiceToCards = useCallback((items) => {
    return items.map((q, i) => {
      const hebWord = node?.hebrew || node?.title?.match(/\(([^)]+)\)/)?.[1] || ''
      let opts = []
      try { opts = JSON.parse(q.options_json || '[]') } catch {}
      return {
        id: `heb-practice-${nodeId}-${i}`,
        type: 'drill',
        data: {
          question: q.question_text,
          options: opts,
          correct: q.correct_answer,
          explanation: q.explanation || '',
          hebrew_word: hebWord,
          question_type: q.question_type,
          node_id: nodeId,
        },
      }
    })
  }, [nodeId, node])

  // Flashcard mode: handle rate callback
  const handleFlashcardRate = useCallback(async (card, rating) => {
    const correct = rating >= 3
    try {
      await fetch('/api/v1/hebrew/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: card.data?.node_id || nodeId, correct, user_id: 'default' }),
      })
    } catch {}
  }, [nodeId])

  // Start flashcard mode
  const startFlashcards = useCallback(() => {
    setFcards(practiceToCards(practice))
    setFlashcardMode(true)
  }, [practice, practiceToCards])

  const playAudio = useCallback(async (word) => {
    if (!word) return
    try {
      const r = await fetch(`/api/v1/hebrew/audio/${encodeURIComponent(word)}`)
      const d = await r.json()
      if (d.ok && d.data?.audio_url) {
        if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
        const audio = new Audio(d.data.audio_url)
        audioRef.current = audio
        audio.onended = () => setAudioPlaying(null)
        audio.onerror = () => setAudioPlaying(null)
        audio.play().then(() => setAudioPlaying(word)).catch(() => setAudioPlaying(null))
      }
    } catch {}
  }, [])

  // Listen for play-hebrew-audio events from CardQueue/DrillCardRenderer
  useEffect(() => {
    const handler = (e) => playAudio(e.detail?.word)
    window.addEventListener('play-hebrew-audio', handler)
    return () => {
      window.removeEventListener('play-hebrew-audio', handler)
      if (audioRef.current) audioRef.current.pause()
    }
  }, [playAudio])

  const startIdx = batch * batchSize
  const batchQuestions = practice.slice(startIdx, startIdx + batchSize)
  const totalBatches = Math.ceil(practice.length / batchSize)

  // Record response time when user interacts with a question
  const recordInteraction = (idx) => {
    if (startTimes[idx] && !responseTimes[idx]) {
      const elapsed = (Date.now() - startTimes[idx]) / 1000
      setResponseTimes(prev => ({ ...prev, [idx]: Math.round(elapsed * 10) / 10 }))
    }
  }

  // Submit batch
  const handleSubmitBatch = async () => {
    // Clear all timers
    Object.values(timersRef.current).forEach(clearTimeout)
    timersRef.current = {}

    const newSubmitted = {}
    let batchCorrect = 0
    let batchTotal = 0
    let failedNodes = []

    batchQuestions.forEach((q, i) => {
      const idx = startIdx + i
      const ans = answers[idx]
      if (ans === undefined || ans === null || ans === '') {
        newSubmitted[idx] = false // timeout or unanswered = incorrect
        batchTotal++
        return
      }

      // Record response time
      recordInteraction(idx)

      let correct = false
      if (['typing', 'recall', 'cloze', 'transliteration'].includes(q.question_type)) {
        const expected = (q.correct_answer || '').toLowerCase().trim()
        const given = (ans || '').toLowerCase().trim()
        correct = given === expected || given.includes(expected) || expected.includes(given)
      } else {
        correct = ans === q.correct_answer
      }
      newSubmitted[idx] = correct
      if (correct) batchCorrect++
      else failedNodes.push(nodeId) // track for remediation
      batchTotal++
    })

    setSubmitted(prev => ({ ...prev, ...newSubmitted }))

    // Report progress
    for (const [idx, correct] of Object.entries(newSubmitted)) {
      try {
        await fetch('/api/v1/hebrew/progress', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ node_id: nodeId, correct, user_id: 'default' }),
        })
      } catch {}
    }

    // Targeted remediation: fetch prerequisites for failed questions
    if (failedNodes.length > 0 && node?.prerequisites?.length > 0) {
      setRemediation(node.prerequisites)
    }

    setResults(prev => ({
      correct: prev.correct + batchCorrect,
      total: prev.total + batchTotal,
      streak: batchCorrect === batchTotal ? prev.streak + 1 : 0,
      bestStreak: Math.max(prev.bestStreak, batchCorrect === batchTotal ? prev.streak + 1 : 0),
      totalTime: prev.totalTime + Object.values(responseTimes).reduce((a, b) => a + b, 0),
    }))
  }

  const handleNextBatch = () => {
    if (batch < totalBatches - 1) {
      setBatch(prev => prev + 1)
      setAnswers({})
      setSubmitted({})
      setTimedOut({})
      setResponseTimes({})
      setStartTimes({})
      setRemediation(null)
    } else {
      setCompleted(true)
    }
  }

  const setAnswer = (idx, value) => {
    recordInteraction(idx)
    setAnswers(prev => ({ ...prev, [idx]: value }))
  }

  const hebrewWord = node?.hebrew || node?.title?.split('—')[0]?.trim() || ''

  // Micro-scaffolding: classify questions into 3 Knowledge Points
  const kpQuestions = useMemo(() => {
    const kp1 = practice.filter(q => ['multiple_choice', 'true_false'].includes(q.question_type))
    const kp2 = practice.filter(q => ['transliteration', 'cloze'].includes(q.question_type))
    const kp3 = practice.filter(q => ['recall', 'typing'].includes(q.question_type))
    // Shuffle within each KP for variety
    const shuffle = (arr) => {
      const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]] } return a
    }
    return { kp1: shuffle(kp1), kp2: shuffle(kp2), kp3: shuffle(kp3) }
  }, [practice])

  const currentKPQuestions = currentKP === 1 ? kpQuestions.kp1 : currentKP === 2 ? kpQuestions.kp2 : kpQuestions.kp3

  // Determine which KP a question index belongs to
  const getKPForIndex = (idx) => {
    const kp1Count = kpQuestions.kp1.length
    const kp2Count = kpQuestions.kp2.length
    if (idx < kp1Count) return 1
    if (idx < kp1Count + kp2Count) return 2
    return 3
  }

  const getTimeRemaining = (idx) => {
    if (submitted[idx] || timedOut[idx]) return 0
    if (!startTimes[idx]) return 0
    // Find the question for this index
    const relIdx = idx - startIdx
    const q = batchQuestions[relIdx]
    if (!q) return 0
    const limit = getTimeLimit(q) || 15
    const elapsed = (Date.now() - startTimes[idx]) / 1000
    return Math.max(0, limit - elapsed)
  }

  if (loading) return (
    <div className="max-w-3xl mx-auto px-6 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2" />
      <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
    </div>
  )

  if (error) return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">← Back</button>
      <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">{error}</div>
    </div>
  )

  if (!node) return null

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        <div className="flex items-center gap-2">
          {hebrewWord && (
            <button onClick={() => playAudio(hebrewWord)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-xs font-medium hover:bg-amber-200 dark:hover:bg-amber-900/50 cursor-pointer transition-colors">
              <span>{audioPlaying === hebrewWord ? '🔊' : '🔈'}</span>
              <span>{audioPlaying === hebrewWord ? 'Playing...' : 'Play'}</span>
            </button>
          )}
          {/* Flashcard mode toggle */}
          {practice.length > 0 && !completed && (
            <button onClick={flashcardMode ? () => setFlashcardMode(false) : startFlashcards}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                flashcardMode
                  ? 'bg-indigo-600 text-white'
                  : 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/50'
              }`}>
              🃏 {flashcardMode ? 'Flashcard Mode' : 'Flashcards'}
            </button>
          )}
          {/* KP indicator */}
          <div className="flex items-center gap-1.5">
            {[1,2,3].map(kp => (
              <span key={kp} className={`text-[9px] px-2 py-0.5 rounded-full font-medium transition-colors ${
                currentKP === kp
                  ? 'bg-indigo-600 text-white'
                  : kpState[`kp${kp}`]
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                    : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500'
              }`}>
                KP{kp}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Title */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500">Level {node.level}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">{node.category}</span>
          <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400 font-medium">⏱ Timed</span>
        </div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{node.title}</h2>
        {node.description && <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{node.description}</p>}
      </div>

      {/* Prerequisites cross-links */}
      {node?.prerequisites?.length > 0 && batch === 0 && Object.keys(submitted).length === 0 && (
        <div className="mb-4">
          <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-1.5 block">Prerequisites</span>
          <div className="flex flex-wrap gap-1.5">
            {node.prerequisites.map((prereq, i) => (
              <button key={i} onClick={() => onNavigate?.(prereq.node_id || prereq.id)}
                className="text-[9px] px-2 py-1 rounded-full bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 border border-indigo-200 dark:border-indigo-700 cursor-pointer transition-colors"
                title={`Open prerequisite: ${prereq.title || ''}`}>
                {prereq.title || prereq.id}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Lesson content — explanation, key points, worked examples */}
      {batch === 0 && node?.lesson && Object.keys(submitted).length === 0 && (
        <div className="mb-6 space-y-4">
          {/* Explanation */}
          {node.lesson.explanation && (
            <div className="p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
              <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
                {renderTextWithRefs(node.lesson.explanation, onNavigate)}
              </p>
            </div>
          )}
          {/* Key Points */}
          {node.lesson.key_points?.length > 0 && (
            <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400 mb-2 block">Key Points</span>
              <ul className="space-y-1">
                {node.lesson.key_points.map((kp, i) => (
                  <li key={i} className="text-xs text-neutral-700 dark:text-neutral-300 flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5 shrink-0">•</span>
                    <span>{renderTextWithRefs(kp, onNavigate)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {/* Worked Examples */}
          {node.lesson.worked_examples?.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400 mb-2 block">💡 Worked Examples</span>
              {node.lesson.worked_examples.map((we, i) => (
                <div key={i} className="mb-3 last:mb-0">
                  <p className="text-xs font-medium text-neutral-800 dark:text-neutral-200 mb-1">Q: {we.question}</p>
                  <div className="space-y-0.5 ml-2">
                    {(we.steps || []).map((step, si) => (
                      <p key={si} className="text-[11px] text-neutral-600 dark:text-neutral-400">{renderTextWithRefs(step, onNavigate)}</p>
                    ))}
                  </div>
                  {we.answer && (
                    <p className="text-[11px] text-green-700 dark:text-green-300 mt-1 font-medium">{renderTextWithRefs(we.answer, onNavigate)}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Verse attestations — show real scripture examples of this concept */}
      {batch === 0 && node?.verse_attestations?.length > 0 && Object.keys(submitted).length === 0 && (
        <div className="mb-6 p-4 rounded-xl bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm">📖</span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-green-600 dark:text-green-400">
              In Scripture — {node.verse_attestations.length} witnesses
            </span>
            <span className="text-[8px] text-green-500 dark:text-green-400">
              (consistency through multiple attestations)
            </span>
          </div>
          <div className="space-y-2">
            {node.verse_attestations.map((att, i) => {
              // For letter recognition, extract the Hebrew character and the word containing it
              const isLetterRecog = att.attestation_type === 'letter_recognition'
              const hebText = stripMorphSeparators(att.text_hebrew || '')
              let highlightedHebrew = null
              if (isLetterRecog && hebText && hebText.length > 0) {
                // Try to find the node's Hebrew character in the verse
                const hebChar = node?.title?.match(/\(([^)]+)\)/)?.[1] || ''
                if (hebChar) {
                  // Split the Hebrew text into parts, highlighting the target character
                  const parts = []
                  let remaining = hebText
                  let idx = 0
                  while (remaining.length > 0) {
                    const ci = remaining.indexOf(hebChar)
                    if (ci < 0) { parts.push({ t: remaining, hl: false }); break }
                    if (ci > 0) parts.push({ t: remaining.slice(0, ci), hl: false })
                    parts.push({ t: remaining.slice(ci, ci + hebChar.length), hl: true })
                    remaining = remaining.slice(ci + hebChar.length)
                    idx++
                    if (idx > 20) break // safety
                  }
                  if (parts.length > 0) highlightedHebrew = parts
                }
              }
              return (
              <div key={i} className="p-2.5 rounded-lg bg-white dark:bg-neutral-800 border border-green-200 dark:border-green-700">
                <div className="flex items-center gap-1.5 mb-1">
                  <button onClick={() => onNavigate?.(att.verse_id)}
                    className="text-[10px] font-mono font-medium text-green-700 dark:text-green-300 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer hover:underline transition-colors"
                    title={`Open ${att.verse_id}`}>
                    {formatRef(...(att.verse_id?.split('.') || []))}
                  </button>
                  {att.attestation_type && (
                    <span className="text-[8px] px-1 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400">
                      {att.attestation_type.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
                {/* Hebrew text with highlighted target letter */}
                {highlightedHebrew && (
                  <div className="mb-1 text-right" dir="rtl">
                    <span className="text-xl leading-relaxed font-hebrew-biblical">
                      {highlightedHebrew.map((p, pi) =>
                        p.hl
                          ? <mark key={pi} className="bg-yellow-300 dark:bg-yellow-600/50 text-neutral-900 dark:text-neutral-100 px-0.5 rounded">{p.t}</mark>
                          : <span key={pi}>{p.t}</span>
                      )}
                    </span>
                  </div>
                )}
                {att.text && (
                  <p className="text-[11px] text-neutral-700 dark:text-neutral-300 italic leading-relaxed">
                    “{att.text}”
                  </p>
                )}
                {att.explanation && (
                  <p className="text-[9px] text-neutral-500 dark:text-neutral-400 mt-0.5">{renderTextWithRefs(att.explanation, onNavigate)}</p>
                )}
              </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Progress + speed */}
      <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <div className="flex-1">
          <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${(results.total / Math.max(practice.length, 1)) * 100}%` }} />
          </div>
        </div>
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">{results.correct}/{results.total}</span>
        {results.totalTime > 0 && (
          <span className="text-[9px] text-neutral-400 dark:text-neutral-500 font-mono">
            ⏱ {(results.totalTime / Math.max(results.total, 1)).toFixed(1)}s/avg
          </span>
        )}
        {results.streak > 1 && <span className="text-[10px] text-amber-600 dark:text-amber-400 font-mono">🔥{results.streak}</span>}
      </div>

      {/* Flashcard mode — CardQueue */}
      {flashcardMode && fcards.length > 0 ? (
        <div className="mb-6">
          <CardQueue
            cards={fcards}
            onRate={handleFlashcardRate}
            onComplete={() => { setFlashcardMode(false); setCompleted(true) }}
            title={`${node?.title || ''} Practice`}
            emptyMessage="All done!"
          />
        </div>
      ) : completed ? (
        <div className="p-6 rounded-xl bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-center">
          <span className="text-3xl block mb-2">🎉</span>
          <h3 className="text-base font-semibold text-green-800 dark:text-green-200 mb-1">Complete!</h3>
          <p className="text-sm text-green-600 dark:text-green-400 mb-1">
            {results.correct}/{results.total} ({Math.round(results.correct / Math.max(results.total, 1) * 100)}%)
          </p>
          {results.totalTime > 0 && (
            <p className="text-xs text-green-500 dark:text-green-400 mb-1">
              Avg response: {(results.totalTime / Math.max(results.total, 1)).toFixed(1)}s
              {results.totalTime / Math.max(results.total, 1) < 5 ? ' ⚡ Fast!' : results.totalTime / Math.max(results.total, 1) < 10 ? ' 👍 Good pace' : ' 🐢 Needs speed'}
            </p>
          )}
          {results.bestStreak > 2 && <p className="text-xs text-green-500 dark:text-green-400 mb-4">Best streak: {results.bestStreak} 🔥</p>}
          <div className="flex gap-2 justify-center">
            <button onClick={onBack} className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Back</button>
            <button onClick={() => { setBatch(0); setAnswers({}); setSubmitted({}); setTimedOut({}); setResponseTimes({}); setStartTimes({}); setCompleted(false); setResults({ correct: 0, total: 0, streak: 0, bestStreak: 0, totalTime: 0 }); setRemediation(null) }}
              className="px-4 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-sm font-medium cursor-pointer transition-colors">Retry</button>
          </div>
        </div>
      ) : batchQuestions.length > 0 ? (
        <div className="space-y-4">
          <p className="text-[9px] text-neutral-400 dark:text-neutral-500 flex items-center gap-2">
            <span>⏱ Each question has a time limit. Unanswered = incorrect.</span>
            <span className="text-[8px] px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400">Build automaticity</span>
          </p>

          {batchQuestions.map((q, qi) => {
            const idx = startIdx + qi
            const isSubmitted = idx in submitted
            const isCorrect = submitted[idx]
            const answer = answers[idx]
            const limit = getTimeLimit(q)
            const remaining = isSubmitted ? 0 : Math.max(0, limit - ((Date.now() - (startTimes[idx] || Date.now())) / 1000))
            const pct = isSubmitted ? 0 : (remaining / limit) * 100
            const isUrgent = remaining < 3 && !isSubmitted

            return (
              <div key={idx} className={`p-4 rounded-xl border ${TYPE_COLORS[q.question_type] || 'bg-neutral-50 dark:bg-neutral-900/50 border-neutral-200 dark:border-neutral-700'} ${timedOut[idx] && !isSubmitted ? 'opacity-75' : ''}`}>
                {/* Header with timer */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                      Q{idx + 1} · {q.question_type?.replace(/_/g, ' ')}
                    </span>
                    {!isSubmitted && (
                      <span className={`text-[9px] font-mono ${isUrgent ? 'text-red-500 animate-pulse' : 'text-neutral-400'}`}>
                        {remaining.toFixed(0)}s
                      </span>
                    )}
                  </div>
                  {isSubmitted && (
                    <span className={`text-[10px] font-medium ${isCorrect ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {timedOut[idx] ? '⏰ Timed out' : isCorrect ? '✓ Correct' : '✗ Incorrect'}
                    </span>
                  )}
                </div>

                {/* Timer bar */}
                {!isSubmitted && (
                  <div className="h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 mb-3 overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-300 ${isUrgent ? 'bg-red-500' : 'bg-indigo-400'}`}
                      style={{ width: `${pct}%` }} />
                  </div>
                )}

                {/* Question text — handle mixed English/Hebrew lines */}
                <div className="mb-3">
                  {q.question_text.split('\n').map((line, li) => {
                    const hasHeb = /[\u0590-\u05FF]/.test(line)
                    if (!hasHeb) {
                      return <p key={li} className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-1">{line}</p>
                    }
                    // Mixed line: split into Hebrew and non-Hebrew segments
                    const segments = line.split(/([\u0590-\u05FF]+)/g)
                    return (
                      <p key={li} className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 mb-1">
                        {segments.map((seg, si) =>
                          /[\u0590-\u05FF]/.test(seg)
                            ? <span key={si} className="text-xl font-hebrew-biblical" dir="rtl">{seg}</span>
                            : <span key={si}>{seg}</span>
                        )}
                      </p>
                    )
                  })}
                </div>

                {/* Answer area */}
                {['typing', 'recall', 'cloze', 'transliteration'].includes(q.question_type) ? (
                  <div className="flex items-center gap-2">
                    <input type="text" value={answer || ''} onChange={e => setAnswer(idx, e.target.value)}
                      disabled={isSubmitted}
                      placeholder={q.question_type === 'transliteration' ? 'Type transliteration...' : 'Type answer...'}
                      className={`flex-1 px-3 py-2 rounded-lg border text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 disabled:opacity-60
                        ${isSubmitted ? (isCorrect ? 'border-green-400 bg-green-50 dark:bg-green-900/20' : 'border-red-400 bg-red-50 dark:bg-red-900/20') : 'border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200'}`}
                      dir={q.question_type === 'typing' || q.question_type === 'cloze' ? 'rtl' : 'ltr'} />
                    {q.question_type !== 'transliteration' && (
                      <button onClick={() => { setShowKeyboard(true); setKeyboardTarget(idx) }}
                        className="px-2.5 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-xs font-medium cursor-pointer transition-colors shrink-0">⌨</button>
                    )}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {(q.options_json ? (() => { try { return JSON.parse(q.options_json) } catch { return [] } })() : []).map((opt, oi) => {
                      const isSelected = answer === opt || answer === String(oi)
                      let cls = 'w-full text-left px-3 py-2 rounded-lg text-sm border transition-all cursor-pointer '
                      if (isSubmitted) {
                        const isOptCorrect = opt === q.correct_answer || String(oi) === String(q.correct_answer)
                        cls += isOptCorrect ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                          : isSelected && !isOptCorrect ? 'border-red-400 bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                          : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500 dark:text-neutral-400'
                      } else {
                        cls += isSelected
                          ? 'border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 text-indigo-800 dark:text-indigo-200 font-medium'
                          : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                      }
                      return (
                        <button key={oi} onClick={() => { if (!isSubmitted) setAnswer(idx, opt) }} className={cls}>
                          <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + oi)}.</span>
                          {/[\u0590-\u05FF]/.test(opt)
                            ? <span className="text-lg font-hebrew-biblical" dir="rtl">{opt}</span>
                            : <span>{opt}</span>}
                        </button>
                      )
                    })}
                  </div>
                )}

                {/* Explanation on submit */}
                {isSubmitted && q.explanation && (
                  <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400 leading-relaxed">{q.explanation}</div>
                )}

                {/* Response time */}
                {isSubmitted && responseTimes[idx] && (
                  <div className="mt-1 text-[9px] text-neutral-400 dark:text-neutral-500">
                    Response: {responseTimes[idx]}s {responseTimes[idx] < limit * 0.5 ? '⚡' : responseTimes[idx] < limit * 0.8 ? '✓' : '🐢'}
                  </div>
                )}
              </div>
            )
          })}

          {/* Remediation */}
          {remediation && remediation.length > 0 && (
            <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
              <p className="text-[10px] font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wider mb-2">📚 Review Prerequisites</p>
              <p className="text-xs text-amber-600 dark:text-amber-400 mb-2">You had some incorrect answers. Strengthen your foundations:</p>
              <div className="flex flex-wrap gap-1.5">
                {remediation.map((prereq) => (
                  <button key={prereq.id} onClick={() => {
                    setBatch(0); setAnswers({}); setSubmitted({}); setTimedOut({});
                    setResponseTimes({}); setStartTimes({}); setRemediation(null);
                    // Navigate to prerequisite lesson via parent
                    onBack(prereq.id)
                  }}
                    className="text-xs px-3 py-1.5 rounded-full bg-white dark:bg-neutral-800 border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40 cursor-pointer transition-colors">
                    {prereq.title}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Submit / Next */}
          <div className="flex gap-2">
            {!batchQuestions.some((_, i) => (startIdx + i) in submitted) ? (
              <button onClick={handleSubmitBatch}
                disabled={false}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium cursor-pointer transition-colors">
                {timedOut && Object.keys(timedOut).length > 0 ? 'Finish (time is up)' : 'Submit All Answers'}
              </button>
            ) : (
              <button onClick={handleNextBatch}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
                {batch < totalBatches - 1 ? `Next Batch (${batch + 2}/${totalBatches}) →` : 'See Results'}
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="p-6 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border-neutral-200 dark:border-neutral-700 text-center text-sm text-neutral-500 dark:text-neutral-400">
          No questions for this lesson.
          <button onClick={onBack} className="block mt-3 mx-auto px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Back</button>
        </div>
      )}

      {/* Keyboard overlay */}
      {showKeyboard && (
        <div className="fixed inset-0 z-50 bg-black/30 flex items-end justify-center" onClick={() => setShowKeyboard(false)}>
          <div className="bg-white dark:bg-neutral-900 rounded-t-2xl p-4 w-full max-w-lg" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-neutral-500 dark:text-neutral-400">Hebrew Keyboard</span>
              <button onClick={() => setShowKeyboard(false)} className="text-xs text-neutral-400 hover:text-neutral-600 cursor-pointer">✕</button>
            </div>
            <HebrewKeyboard
              value={answers[keyboardTarget] || ''}
              onCharClick={c => { if (keyboardTarget !== null) setAnswer(keyboardTarget, (answers[keyboardTarget] || '') + c) }}
              onBackspace={() => { if (keyboardTarget !== null) setAnswer(keyboardTarget, (answers[keyboardTarget] || '').slice(0, -1)) }}
              onClear={() => { if (keyboardTarget !== null) setAnswer(keyboardTarget, '') }}
              onDone={() => setShowKeyboard(false)} />
          </div>
        </div>
      )}

      <audio ref={audioRef} />
    </div>
  )
}
