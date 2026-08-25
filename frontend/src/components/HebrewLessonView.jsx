import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import CardQueue from './CardQueue'
import CardRenderer from './CardRenderer'
import HebrewQuiz, { submitHebrewProgress } from './HebrewQuiz'
import { stripMorphSeparators } from '../lib/hebrew-utils'
import {
  ANSWER_MODES,
  answerModeForQuestion,
  gradeQuizAnswer,
  normalizeQuizAnswer,
} from '../lib/quiz-grading'
import { currentSessionToken } from '../api'

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
  return vs ? `${name} ${ch}:${vs}` : `${name} ${ch}`
}

/** Split text on scripture references like gen.1.1, exo.3.14 or Gen 1:1, Exo 3:14 */
function renderTextWithRefs(text, onNavigate) {
  if (!text) return text
  const hebRe = /[\u0590-\u05FF\u05B0-\u05C7]+/g
  const dotRefRe = /\b([a-z]{2,6})\.(\d+)\.(\d+)\b/gi
  const colRefRe = /\b([A-Za-z][a-z]{2,6})\s+(\d+):(\d+)\b/g
  const tokens = []
  let remaining = text

  while (remaining.length > 0) {
    const dotMatch = dotRefRe.exec(remaining)
    const colMatch = colRefRe.exec(remaining)
    hebRe.lastIndex = 0
    const hebTest = hebRe.exec(remaining)
    const hebPos = hebTest ? hebTest.index : -1
    const candidates = []
    if (dotMatch) candidates.push({ type: 'ref_dot', match: dotMatch, pos: dotMatch.index })
    if (colMatch) candidates.push({ type: 'ref_col', match: colMatch, pos: colMatch.index })
    if (hebPos >= 0) candidates.push({ type: 'hebrew', match: hebTest, pos: hebPos })

    if (candidates.length === 0) {
      tokens.push({ type: 'text', value: remaining })
      break
    }
    candidates.sort((a, b) => a.pos - b.pos)
    const first = candidates[0]
    if (first.pos > 0) tokens.push({ type: 'text', value: remaining.slice(0, first.pos) })

    if (first.type === 'ref_dot' || first.type === 'ref_col') {
      const m = first.match
      tokens.push({ type: 'ref', book: m[1], ch: m[2], vs: m[3], raw: m[0] })
      remaining = remaining.slice(m.index + m[0].length)
    } else if (first.type === 'hebrew') {
      const m = first.match
      tokens.push({ type: 'hebrew', value: m[0] })
      remaining = remaining.slice(m.index + m[0].length)
    }
    dotRefRe.lastIndex = 0
    colRefRe.lastIndex = 0
  }

  return tokens.map((t, i) => {
    if (t.type === 'text') return <span key={i}>{t.value}</span>
    if (t.type === 'ref') return (
      <button key={i}
        onClick={() => window.dispatchEvent(new CustomEvent('scripture-navigate', {
          detail: { book: t.book.toLowerCase(), chapter: parseInt(t.ch), verse: parseInt(t.vs) }
        }))}
        className="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer font-medium"
        title={`Open ${t.book}.${t.ch}.${t.vs}`}>
        {t.raw}
      </button>
    )
    if (t.type === 'hebrew') {
      const clean = t.value.replace(/[\u0591-\u05C7]/g, '').trim()
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
          {t.value}
        </span>
      )
    }
    return null
  })
}

export const normalizePracticeAnswer = normalizeQuizAnswer

export function gradePracticeAnswer(answer, expected) {
  return gradeQuizAnswer({
    answer,
    correctAnswer: expected,
    mode: ANSWER_MODES.FREE_TEXT,
  })
}

/**
 * StagedPractice — Math Academy-style 3-KP flow: recognition → recall → production.
 *
 * Each stage shows up to 2 practice items (cycling through the stage's pool on
 * retry). A stage passes only when every item in the attempt is answered
 * correctly; a failed stage surfaces the "review this stage" panel and retries
 * with a fresh pair. When all stages pass, the lesson is complete.
 *
 * The single-pass flashcard flow remains available as "quick" mode via the
 * toggle (passed as onSwitchMode).
 */
function StageItemCard({ card, onSubmitted, onContinue, isLast }) {
  const [submitted, setSubmitted] = useState(false)
  const [answer, setAnswer] = useState('')
  const [serverCorrect, setServerCorrect] = useState(null)
  const [grading, setGrading] = useState(false)

  const correct = serverCorrect
  const handleAnswer = (ans) => {
    setAnswer(ans)
    setSubmitted(true)
    setGrading(true)
    const resolution = onSubmitted?.(card, ans)
    if (resolution && typeof resolution.then === 'function') {
      resolution.then(authoritative => {
        if (typeof authoritative === 'boolean') setServerCorrect(authoritative)
      }).catch(() => {}).finally(() => setGrading(false))
    } else {
      setGrading(false)
    }
  }

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800/60 p-4">
      <CardRenderer
        card={card}
        showAnswer={submitted}
        onAnswer={handleAnswer}
        answerState={{ [card.id]: { submitted, answer, correct } }}
      />
      {submitted && (
        <button onClick={onContinue} disabled={grading}
          className="mt-4 w-full px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-wait text-white text-sm font-medium cursor-pointer transition-colors">
          {grading ? 'Checking…' : isLast ? 'Continue →' : 'Next →'}
        </button>
      )}
    </div>
  )
}

function StagedPractice({ stages, nodeId, toCards, onGrade, onSwitchMode, title }) {
  const [stageIdx, setStageIdx] = useState(0)
  const [cycle, setCycle] = useState(0)          // retry cycle → fresh item pair
  const [pos, setPos] = useState(0)
  const [passedFlags, setPassedFlags] = useState([])
  const [showRetry, setShowRetry] = useState(false)
  const [done, setDone] = useState(false)

  const stage = stages[stageIdx]
  const stageName = stage?.stage || 'stage'
  const stageLabel = stageName.charAt(0).toUpperCase() + stageName.slice(1)
  const allItems = stage?.items || []

  // 2 practice items per attempt; cycle through the stage's pool so retries
  // present fresh items instead of rote repetition of the same pair.
  const attemptItems = useMemo(() => {
    if (allItems.length === 0) return []
    const n = Math.min(2, allItems.length)
    const start = (cycle * 2) % allItems.length
    const picked = []
    for (let k = 0; k < n; k++) picked.push(allItems[(start + k) % allItems.length])
    return picked
  }, [allItems, cycle])

  const cards = useMemo(() => toCards(attemptItems), [attemptItems, toCards])
  const current = cards[pos]

  // A stage with no practice items can never block the lesson — pass through.
  useEffect(() => {
    if (!done && allItems.length === 0 && stage) {
      if (stageIdx + 1 < stages.length) {
        setStageIdx(stageIdx + 1)
      } else {
        setDone(true)
      }
    }
  }, [allItems, stage, stageIdx, stages.length, done])

  const handleSubmitted = (card, _ans, correct) => {
    const cardIndex = cards.findIndex(item => item.id === card.id)
    const setPassedResult = value => {
      if (typeof value !== 'boolean' || cardIndex < 0) return value
      setPassedFlags(prev => {
        const next = [...prev]
        next[cardIndex] = value
        return next
      })
      return value
    }
    setPassedFlags(prev => {
      const next = [...prev]
      next[cardIndex >= 0 ? cardIndex : pos] = correct
      return next
    })
    const resolution = onGrade?.(card, _ans)
    if (resolution && typeof resolution.then === 'function') {
      return resolution.then(setPassedResult)
    }
    return setPassedResult(resolution)
  }

  const handleContinue = () => {
    if (pos + 1 < cards.length) {
      setPos(pos + 1)
      return
    }
    const allCorrect = cards.length > 0 && passedFlags.length === cards.length && passedFlags.every(Boolean)
    if (allCorrect) {
      if (stageIdx + 1 < stages.length) {
        setStageIdx(stageIdx + 1)
        setCycle(0)
        setPos(0)
        setPassedFlags([])
        setShowRetry(false)
      } else {
        setDone(true)
      }
    } else {
      setShowRetry(true)   // failed stage → review this stage's content
    }
  }

  const handleRetry = () => {
    setCycle(c => c + 1)
    setPos(0)
    setPassedFlags([])
    setShowRetry(false)
  }

  if (done) {
    return (
      <div className="p-6 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-center">
        <span className="text-4xl block mb-3">🎉</span>
        <h3 className="text-base font-semibold text-neutral-800 dark:text-neutral-200 mb-1">Lesson Complete</h3>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">
          All {stages.length} stages passed — {title || 'practice'} complete.
        </p>
        <button onClick={onSwitchMode}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
          Continue to Quick practice
        </button>
      </div>
    )
  }

  if (!stage) return null

  return (
    <div className="mb-6">
      {/* Stage progress segments */}
      <div className="flex items-center gap-1.5 mb-3">
        {stages.map((s, i) => (
          <div key={s.stage}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              i < stageIdx ? 'bg-green-500'
                : i === stageIdx ? 'bg-indigo-500'
                  : 'bg-neutral-200 dark:bg-neutral-700'}`} />
        ))}
      </div>

      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-indigo-500 dark:text-indigo-400">
            Stage {stageIdx + 1} of {stages.length} — {stageLabel}
          </span>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
            {cards.length > 0 ? `${pos + 1} of ${cards.length} · answer all correctly to continue` : 'No practice items'}
          </p>
        </div>
        <button onClick={onSwitchMode}
          className="text-[10px] text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer transition-colors"
          title="Switch to the single-pass flashcard flow">
          ⚡ Quick mode
        </button>
      </div>

      {showRetry ? (
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-700 mb-4">
          <p className="text-sm text-amber-800 dark:text-amber-200 font-medium mb-1">Review this stage</p>
          <p className="text-xs text-amber-700 dark:text-amber-300 mb-3">
            Review the material above, then retry the {stageLabel.toLowerCase()} practice.
          </p>
          <button onClick={handleRetry}
            className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-sm font-medium cursor-pointer transition-colors">
            Retry stage
          </button>
        </div>
      ) : (
        current && (
          <StageItemCard
            key={`${stage.stage}-${cycle}-${pos}`}
            card={current}
            onSubmitted={handleSubmitted}
            onContinue={handleContinue}
            isLast={pos === cards.length - 1}
          />
        )
      )}
    </div>
  )
}

/**
 * HebrewLessonView — Math Academy-style: compact intro → verse attestations → flashcard practice.
 *
 * The lesson explanation acts as a "worked example" — showing letter/word + essential info.
 * Practice items are sorted by difficulty (MC → recall → typing) following Math Academy's
 * micro-scaffolding principle: recognition first, open recall next, production last.
 * CardQueue provides SRS-style retrieval with Again/Hard/Good/Easy rating.
 */

export default function HebrewLessonView({ nodeId, onBack, onNavigate }) {
  const [node, setNode] = useState(null)
  const [practice, setPractice] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [audioPlaying, setAudioPlaying] = useState(null)
  const [practiceAnswers, setPracticeAnswers] = useState({})
  const [showQuiz, setShowQuiz] = useState(false)
  const [wordImage, setWordImage] = useState(null) // {image_url, attribution}
  const audioRef = useRef(null)
  // Practice flow: 'staged' (recognition → recall → production with pass gates)
  // or 'quick' (single-pass flashcards). Choice persists per learner.
  const [practiceMode, setPracticeMode] = useState(() => {
    try { return localStorage.getItem('hebrew.practiceMode') || 'staged' } catch { return 'staged' }
  })

  // Load lesson data
  useEffect(() => {
    setLoading(true)
    setPracticeAnswers({})
    Promise.all([
      fetch(`/api/v1/hebrew/lesson/${nodeId}`).then(r => r.json()),
      fetch(`/api/v1/hebrew/practice/${nodeId}`).then(r => r.json()),
    ])
      .then(([nodeRes, practiceRes]) => {
        if (!nodeRes.ok) throw new Error(nodeRes.detail || 'Failed to load')
        setNode(nodeRes.data)
        setPractice(practiceRes.data?.items || [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [nodeId])

  // Fetch a word image when the lesson is a vocabulary word with a gloss
  useEffect(() => {
    if (!node || !node.hebrew) return
    let cancelled = false
    fetch(`/api/v1/hebrew/image/${encodeURIComponent(node.hebrew)}`)
      .then(r => r.json())
      .then(d => { if (!cancelled && d.ok) setWordImage(d.data) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [node])

  // Convert practice items to cards, sorted by difficulty (MC first = Math Academy scaffolding)
  const practiceToCards = useCallback((items) => {
    const sorted = [...items].sort((a, b) => (a.difficulty || 0) - (b.difficulty || 0))
    return sorted.map((q, i) => {
      const hebWord = node?.hebrew || node?.title?.match(/\(([^)]+)\)/)?.[1] || ''
      let opts = []
      try { opts = JSON.parse(q.options_json || '[]') } catch {}
      return {
        id: `heb-practice-${nodeId}-${i}`,
        type: 'drill',
        data: {
          question_id: q.id,
          question: q.question_text,
          options: opts,
          explanation: q.explanation || '',
          hebrew_word: hebWord,
          question_type: q.question_type,
          answer_mode: q.answer_mode || answerModeForQuestion({
            type: q.question_type,
            options: opts,
          }),
          node_id: nodeId,
        },
      }
    })
  }, [nodeId, node])

  const handlePracticeAnswer = useCallback((card, answer) => {
    setPracticeAnswers(previous => ({
      ...previous,
      [card.id]: {
        submitted: true,
        answer,
        correct: null,
      },
    }))
  }, [])

  // Confidence follows objective grading; it does not determine correctness.
  const handleFlashcardRate = useCallback(async (card, _rating) => {
    const answerState = practiceAnswers[card.id] || {}
    if (card.data?.question_id === undefined || card.data?.question_id === null) return null

    const progress = {
      node_id: card.data?.node_id || nodeId,
      user_id: 'default',
      session_token: currentSessionToken(),
      question_id: card.data.question_id,
      answer: answerState.answer ?? '',
      answer_mode: card.data.answer_mode || answerModeForQuestion(card.data),
    }
    const authoritativeCorrect = await submitHebrewProgress(progress)
    if (typeof authoritativeCorrect === 'boolean') {
      setPracticeAnswers(previous => {
        const state = previous[card.id]
        if (!state) return previous
        return {
          ...previous,
          [card.id]: { ...state, correct: authoritativeCorrect, serverCorrect: authoritativeCorrect },
        }
      })
    }
    return authoritativeCorrect
  }, [nodeId, practiceAnswers])

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

  // Listen for play-hebrew-audio events from CardQueue
  useEffect(() => {
    const handler = (e) => playAudio(e.detail?.word)
    window.addEventListener('play-hebrew-audio', handler)
    return () => {
      window.removeEventListener('play-hebrew-audio', handler)
      if (audioRef.current) audioRef.current.pause()
    }
  }, [playAudio])

  const cards = useMemo(() => practiceToCards(practice), [practice, practiceToCards])
  const hebrewWord = node?.hebrew || node?.title?.split('—')[0]?.trim() || ''
  const explanation = node?.lesson?.explanation || ''
  // Micro-scaffolding stage map from the lesson payload (server-derived).
  const stages = useMemo(() => node?.kp_stages || [], [node])
  const hasStages = stages.length > 0

  const togglePracticeMode = useCallback((mode) => {
    setPracticeMode(mode)
    try { localStorage.setItem('hebrew.practiceMode', mode) } catch {}
  }, [])

  // Staged-mode grading posts straight to /hebrew/progress (same SRS feed as
  // the flashcard flow).
  const handleStagedGrade = useCallback(async (card, answer) => {
    if (card.data?.question_id === undefined || card.data?.question_id === null) return null
    return submitHebrewProgress({
      node_id: card.data?.node_id || nodeId,
      user_id: 'default',
      session_token: currentSessionToken(),
      question_id: card.data.question_id,
      answer: answer ?? '',
      answer_mode: card.data.answer_mode || answerModeForQuestion(card.data),
    })
  }, [nodeId])

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

  // Quiz mode — full-screen per-lesson quiz (retrieval practice that feeds SRS)
  if (showQuiz) {
    return (
      <HebrewQuiz
        nodeId={nodeId}
        count={8}
        onBack={() => setShowQuiz(false)}
        onOpenLesson={(nid) => { setShowQuiz(false); onNavigate?.(nid) }}
      />
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back</button>
        <div className="flex items-center gap-2">
          {hasStages && cards.length > 0 && (
            <button onClick={() => togglePracticeMode(practiceMode === 'staged' ? 'quick' : 'staged')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 text-xs font-medium hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors"
              title={practiceMode === 'staged'
                ? 'Staged mode: recognition → recall → production with pass gates'
                : 'Quick mode: single-pass flashcards'}>
              <span>{practiceMode === 'staged' ? '⚡' : '📚'}</span>
              <span>{practiceMode === 'staged' ? 'Quick' : 'Staged'}</span>
            </button>
          )}
          {cards.length > 0 && (
            <button onClick={() => setShowQuiz(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors"
              title="Quiz yourself on this lesson — answers feed your spaced-repetition review">
              <span>📝</span>
              <span>Start Quiz</span>
            </button>
          )}
          {hebrewWord && (
            <button onClick={() => playAudio(hebrewWord)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-xs font-medium hover:bg-amber-200 dark:hover:bg-amber-900/50 cursor-pointer transition-colors">
              <span>{audioPlaying === hebrewWord ? '🔊' : '🔈'}</span>
              <span>{audioPlaying === hebrewWord ? 'Playing...' : 'Play'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Title + metadata */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500">Level {node.level}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">{node.category}</span>
        </div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{node.title}</h2>
        {node.description && <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">{node.description}</p>}
      </div>

      {/* Word image — concrete nouns get a picture (cow → 🐄), with attribution */}
      {wordImage?.image_url && (
        <div className="mb-6">
          <div className="relative w-full overflow-hidden rounded-xl border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50">
            <img
              src={wordImage.image_url}
              alt={node.hebrew || node.title}
              className="w-full h-48 sm:h-56 object-cover"
              loading="lazy"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          </div>
          {wordImage.attribution && (
            <p className="text-[9px] text-neutral-400 dark:text-neutral-500 mt-1" dir="ltr">{wordImage.attribution}</p>
          )}
        </div>
      )}

      {/* Prerequisites — quick cross-links */}
      {node?.prerequisites?.length > 0 && (
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

      {/* Consolidated explanation — one compact block (Math Academy "worked example") */}
      {explanation && (
        <div className="mb-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
          <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
            {renderTextWithRefs(explanation, onNavigate)}
          </p>
        </div>
      )}

      {/* Key points — the essential takeaways (Math Academy "knowledge points") */}
      {node?.lesson?.key_points?.length > 0 && (
        <div className="mb-6">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2 block">Key Points</span>
          <ul className="space-y-1.5">
            {node.lesson.key_points.map((kp, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-neutral-700 dark:text-neutral-300">
                <span className="mt-1 h-1.5 w-1.5 rounded-full bg-indigo-400 dark:bg-indigo-500 shrink-0" />
                <span>{renderTextWithRefs(String(kp), onNavigate)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Worked examples — step-by-step demonstrations before practice (Math Academy KP structure) */}
      {node?.lesson?.worked_examples?.length > 0 && (
        <div className="mb-6">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-2 block">Worked Example{node.lesson.worked_examples.length > 1 ? 's' : ''}</span>
          <div className="space-y-3">
            {node.lesson.worked_examples.map((we, i) => (
              <details key={i} open={i === 0} className="group rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800/60 overflow-hidden">
                <summary className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-neutral-800 dark:text-neutral-200 cursor-pointer select-none hover:bg-neutral-50 dark:hover:bg-neutral-800">
                  <span className="text-indigo-500 dark:text-indigo-400">{String(i + 1).padStart(2, '0')}</span>
                  <span className="flex-1">{renderTextWithRefs(String(we.question || 'Example'), onNavigate)}</span>
                  <span className="text-xs text-neutral-400 group-open:hidden">Show steps ▸</span>
                  <span className="text-xs text-neutral-400 hidden group-open:inline">Hide steps ▾</span>
                </summary>
                <div className="px-4 pb-4 pt-1 space-y-2">
                  {Array.isArray(we.steps) && we.steps.map((step, si) => (
                    <div key={si} className="flex items-start gap-2 text-sm text-neutral-600 dark:text-neutral-300">
                      <span className="mt-0.5 text-[10px] font-mono text-neutral-400 shrink-0">Step {si + 1}</span>
                      <span className="flex-1 leading-relaxed">{renderTextWithRefs(String(step), onNavigate)}</span>
                    </div>
                  ))}
                  {we.answer && (
                    <div className="mt-2 p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-sm text-emerald-700 dark:text-emerald-300">
                      <span className="font-semibold">Answer: </span>
                      <span className="inline">{renderTextWithRefs(String(we.answer), onNavigate)}</span>
                    </div>
                  )}
                </div>
              </details>
            ))}
          </div>
        </div>
      )}

      {/* Verse attestations — real scripture examples */}
      {node?.verse_attestations?.length > 0 && (
        <div className="mb-6 p-4 rounded-xl bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm">📖</span>
            <span className="text-[10px] font-semibold uppercase tracking-wider text-green-600 dark:text-green-400">
              In Scripture — {node.verse_attestations.length} witnesses
            </span>
          </div>
          <div className="space-y-2">
            {node.verse_attestations.map((att, i) => {
              const isLetterRecog = att.attestation_type === 'letter_recognition'
              const hebText = stripMorphSeparators(att.text_hebrew || '')
              let highlightedHebrew = null
              if (isLetterRecog && hebText && hebText.length > 0) {
                const hebChar = node?.title?.match(/\(([^)]+)\)/)?.[1] || ''
                if (hebChar) {
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
                    if (idx > 20) break
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

      {/* Practice — staged 3-KP flow (default) or single-pass quick mode */}
      {cards.length > 0 ? (
        practiceMode === 'staged' && hasStages ? (
          <StagedPractice
            stages={stages}
            nodeId={nodeId}
            toCards={practiceToCards}
            onGrade={handleStagedGrade}
            onSwitchMode={() => togglePracticeMode('quick')}
            title={node?.title || 'Practice'}
          />
        ) : (
          <div className="mb-6">
            <CardQueue
              cards={cards}
              onAnswer={handlePracticeAnswer}
              answerState={practiceAnswers}
              onRate={handleFlashcardRate}
              onComplete={() => {}}
              title={node?.title || 'Practice'}
              emptyMessage="All done! Start another lesson or come back later."
            />
          </div>
        )
      ) : (
        <div className="p-6 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">No practice items for this lesson.</p>
          <button onClick={onBack}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
            ← Back
          </button>
        </div>
      )}

      <audio ref={audioRef} />
    </div>
  )
}
