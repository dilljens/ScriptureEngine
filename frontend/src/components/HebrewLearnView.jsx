import React, { useState, useEffect, useMemo } from 'react'
import HebrewVerbDrill from './HebrewVerbDrill'
import CardQueue from './CardQueue'
import AnkiReview from './AnkiReview'
import PassageReader from './PassageReader'
import DailyVerse from './DailyVerse'
import AudioReviewSession from './AudioReviewSession'
import { hebrewToCards, drillsToCards, interleaveCards } from '../lib/card-factory'

/**
 * HebrewLearnView — curriculum dashboard with gamification.
 * - 602 lessons across 9 categories with mastery tracking
 * - Server-side streak + XP + badges
 * - 5-minute quick session mode
 * - Category filter tabs
 * - Mastery Map visualization
 * - Progress bar showing mastered/total
 */

const CATEGORY_STYLES = {
  consonant: { bg: 'bg-amber-100 dark:bg-amber-900/30', border: 'border-amber-300 dark:border-amber-700', text: 'text-amber-800 dark:text-amber-200', label: 'Letters', icon: 'א' },
  vowel: { bg: 'bg-blue-100 dark:bg-blue-900/30', border: 'border-blue-300 dark:border-blue-700', text: 'text-blue-800 dark:text-blue-200', label: 'Vowels', icon: 'ַ' },
  syllable: { bg: 'bg-cyan-100 dark:bg-cyan-900/30', border: 'border-cyan-300 dark:border-cyan-700', text: 'text-cyan-800 dark:text-cyan-200', label: 'Syllables', icon: '◌' },
  word: { bg: 'bg-green-100 dark:bg-green-900/30', border: 'border-green-300 dark:border-green-700', text: 'text-green-800 dark:text-green-200', label: 'Vocabulary', icon: 'מ' },
  verb: { bg: 'bg-purple-100 dark:bg-purple-900/30', border: 'border-purple-300 dark:border-purple-700', text: 'text-purple-800 dark:text-purple-200', label: 'Verbs', icon: 'ע' },
  noun: { bg: 'bg-pink-100 dark:bg-pink-900/30', border: 'border-pink-300 dark:border-pink-700', text: 'text-pink-800 dark:text-pink-200', label: 'Nouns', icon: 'ד' },
  syntax: { bg: 'bg-orange-100 dark:bg-orange-900/30', border: 'border-orange-300 dark:border-orange-700', text: 'text-orange-800 dark:text-orange-200', label: 'Syntax', icon: '⇄' },
  reading: { bg: 'bg-indigo-100 dark:bg-indigo-900/30', border: 'border-indigo-300 dark:border-indigo-700', text: 'text-indigo-800 dark:text-indigo-200', label: 'Reading', icon: 'ק' },
  grammar: { bg: 'bg-rose-100 dark:bg-rose-900/30', border: 'border-rose-300 dark:border-rose-700', text: 'text-rose-800 dark:text-rose-200', label: 'Grammar', icon: 'דק' },
  root: { bg: 'bg-teal-100 dark:bg-teal-900/30', border: 'border-teal-300 dark:border-teal-700', text: 'text-teal-800 dark:text-teal-200', label: 'Roots', icon: 'ש' },
  root_concept: { bg: 'bg-teal-100 dark:bg-teal-900/30', border: 'border-teal-300 dark:border-teal-700', text: 'text-teal-800 dark:text-teal-200', label: 'Roots', icon: 'ש' },
  phrase: { bg: 'bg-yellow-100 dark:bg-yellow-900/30', border: 'border-yellow-300 dark:border-yellow-700', text: 'text-yellow-800 dark:text-yellow-200', label: 'Phrases', icon: 'כ' },
}

export default function HebrewLearnView({ onOpenLesson }) {
  const [curriculum, setCurriculum] = useState(null)
  const [gamification, setGamification] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [showMasteryMap, setShowMasteryMap] = useState(false)
  const [showVerbDrill, setShowVerbDrill] = useState(false)
  const [showHebrewReview, setShowHebrewReview] = useState(false)
  const [hebrewReviewCards, setHebrewReviewCards] = useState([])
  const [showPassageReader, setShowPassageReader] = useState(false)
  const [passageInput, setPassageInput] = useState('gen.1.1')
  const [quickMode, setQuickMode] = useState(false)
  const [quickQuestions, setQuickQuestions] = useState([])
  const [quickIdx, setQuickIdx] = useState(0)
  const [timeLeft, setTimeLeft] = useState(300)
  const [quickScore, setQuickScore] = useState(0)
  const [toast, setToast] = useState(null) // {message, type}
  const [showDailyVerse, setShowDailyVerse] = useState(false)
  const [showFreqVocab, setShowFreqVocab] = useState(false)
  const [freqVocabCards, setFreqVocabCards] = useState([])
  const [showAudioReview, setShowAudioReview] = useState(false)
  const [audioWords, setAudioWords] = useState([])

  // Load curriculum + gamification in parallel
  const loadAll = () => {
    setLoading(true)
    Promise.all([
      fetch('/api/v1/hebrew/curriculum').then(r => r.json()),
      fetch('/api/v1/hebrew/gamification').then(r => r.json()),
    ])
      .then(([curData, gamData]) => {
        if (curData.ok) setCurriculum(curData.data)
        else setError(curData.detail || 'Failed to load')
        if (gamData.ok) setGamification(gamData.data)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(loadAll, [])

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  // Start quick session
  const startQuickSession = () => {
    if (!curriculum?.nodes) return
    const unlocked = curriculum.nodes.filter(n => n.unlocked && n.mastery < 0.8)
    if (unlocked.length === 0) {
      unlocked.push(...curriculum.nodes.filter(n => n.mastery >= 0.8))
    }
    const shuffled = [...unlocked].sort(() => Math.random() - 0.5).slice(0, 10)
    setQuickQuestions(shuffled)
    setQuickIdx(0)
    setQuickScore(0)
    setTimeLeft(300)
    setQuickMode(true)
  }

  // Quick session timer
  useEffect(() => {
    if (!quickMode) return
    if (timeLeft <= 0) { setQuickMode(false); return }
    const timer = setInterval(() => setTimeLeft(t => t - 1), 1000)
    return () => clearInterval(timer)
  }, [quickMode, timeLeft])

  if (loading) return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
        <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/4" />
        {[1,2,3,4].map(i => <div key={i} className="h-16 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />)}
      </div>
    </div>
  )

  if (error) return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">Failed to load: {error}</div>
    </div>
  )

  if (!curriculum) return null

  const { nodes, total, mastered, in_progress, locked } = curriculum
  const filtered = filter === 'all' ? nodes : nodes.filter(n => n.category === filter)
  const byLevel = {}
  for (const n of filtered) {
    if (!byLevel[n.level]) byLevel[n.level] = []
    byLevel[n.level].push(n)
  }

  // Passage reader mode
  if (showPassageReader) {
    return (
      <div>
        <div className="max-w-4xl mx-auto px-6 pt-4">
          <div className="flex items-center gap-3 mb-4">
            <button onClick={() => setShowPassageReader(false)}
              className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer shrink-0">
              ← Back to Curriculum
            </button>
            <input type="text" value={passageInput}
              onChange={e => setPassageInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') setShowPassageReader(true) }}
              placeholder="e.g. gen.22.1-19 or isa.55"
              className="flex-1 max-w-xs px-2 py-1 rounded text-xs border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400" />
            <button onClick={() => {
              // Force re-render by toggling key
              setShowPassageReader(false)
              setTimeout(() => setShowPassageReader(true), 50)
            }}
              className="px-2 py-1 rounded text-xs bg-blue-600 text-white hover:bg-blue-700 cursor-pointer font-medium transition-colors">
              Load
            </button>
          </div>
        </div>
        <PassageReader key={passageInput} passageId={passageInput} />
      </div>
    )
  }

  // Verb drill mode
  if (showVerbDrill) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">Verb Conjugation Drills</h2>
          <button onClick={() => setShowVerbDrill(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
        <HebrewVerbDrill />
      </div>
    )
  }

  // Hebrew review mode — Anki-style flashcard review
  if (showHebrewReview) {
    // Convert curriculum nodes to AnkiReview-compatible cards
    const ankiCards = hebrewReviewCards
      .filter(c => c.data?.hebrew)
      .map(c => ({
        node_id: c.data?.node_id || c.id?.replace(/heb-/, '') || '',
        hebrew: c.data?.hebrew || '',
        gloss: c.data?.gloss || c.data?.definition?.split(' — ')[1] || c.data?.definition || '',
        transliteration: c.data?.transliteration || '',
      }))

    if (ankiCards.length === 0) {
      return (
        <div className="max-w-lg mx-auto px-6 py-12 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">No words to review right now.</p>
          <button onClick={() => setShowHebrewReview(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
      )
    }

    return (
      <AnkiReview
        cards={ankiCards}
        onComplete={() => { setShowHebrewReview(false); setHebrewReviewCards([]) }}
        onBack={() => { setShowHebrewReview(false); setHebrewReviewCards([]) }}
        title="Hebrew Review"
      />
    )
  }

  // Daily Verse mode
  if (showDailyVerse) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📆 Verse of the Day</h2>
          <button onClick={() => setShowDailyVerse(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
        <DailyVerse />
      </div>
    )
  }

  // Audio review mode
  if (showAudioReview) {
    if (audioWords.length === 0) {
      return (
        <div className="max-w-lg mx-auto px-6 py-12 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">No audio words loaded.</p>
          <button onClick={() => setShowAudioReview(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
      )
    }
    return (
      <div className="max-w-lg mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">🎧 Audio Review</h2>
          <button onClick={() => setShowAudioReview(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back
          </button>
        </div>
        <AudioReviewSession words={audioWords} onComplete={() => setShowAudioReview(false)} />
      </div>
    )
  }

  // Frequency vocab mode
  if (showFreqVocab) {
    if (freqVocabCards.length === 0) {
      return (
        <div className="max-w-lg mx-auto px-6 py-12 text-center">
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">Loading top vocabulary...</p>
          <button onClick={() => setShowFreqVocab(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
      )
    }
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📊 Top 100 Vocabulary</h2>
          <button onClick={() => setShowFreqVocab(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        </div>
        <CardQueue cards={freqVocabCards} title="Frequency Vocab" emptyMessage="All done!" />
      </div>
    )
  }

  // Quick mode rendering
  if (quickMode) {
    const q = quickQuestions[quickIdx]
    if (!q) {
      setQuickMode(false)
      return null
    }
    const mins = Math.floor(timeLeft / 60)
    const secs = timeLeft % 60
    return (
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="text-center mb-6">
          <span className={`text-2xl font-mono font-bold ${timeLeft < 30 ? 'text-red-500' : 'text-indigo-600 dark:text-indigo-400'}`}>
            {mins}:{String(secs).padStart(2, '0')}
          </span>
          <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">Quick Session · {quickScore}/{quickQuestions.length}</p>
        </div>
        <div className="p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-indigo-200 dark:border-indigo-800 text-center">
          <p className="text-lg font-serif leading-relaxed mb-2" dir="rtl" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
            {q.title?.split('—')[0]?.trim() || q.title}
          </p>
          <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-1">{q.title?.split('—')[1]?.trim() || q.description}</p>
          <p className="text-xs text-neutral-400 dark:text-neutral-500 mb-6">Level {q.level} · {q.category}</p>
          <button onClick={() => { onOpenLesson(q.id); setQuickMode(false) }}
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-medium cursor-pointer transition-colors">
            Practice this word
          </button>
          <div className="flex gap-2 justify-center mt-3">
            <button onClick={() => { setQuickIdx(prev => Math.min(prev + 1, quickQuestions.length - 1)); setQuickScore(s => s + 1) }}
              className="px-3 py-1.5 rounded-lg bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs font-medium cursor-pointer transition-colors">Know it ✓</button>
            <button onClick={() => setQuickIdx(prev => Math.min(prev + 1, quickQuestions.length - 1))}
              className="px-3 py-1.5 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-medium cursor-pointer transition-colors">Skip →</button>
          </div>
        </div>
        <button onClick={() => setQuickMode(false)} className="mt-4 w-full py-2 rounded-lg text-sm text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300 cursor-pointer transition-colors">
          End session
        </button>
      </div>
    )
  }

  const gam = gamification || {}

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Toast notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-xl shadow-lg text-sm font-medium transition-all animate-slide-down ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-amber-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-1">Biblical Hebrew</h2>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">{total} lessons · {mastered} mastered · {locked} locked</p>
        </div>
        <div className="flex items-center gap-3">
          {gam.streak > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700">
              <span className="text-sm">🔥</span>
              <span className="text-sm font-bold text-amber-700 dark:text-amber-300">{gam.streak}</span>
              <span className="text-[9px] text-amber-500 dark:text-amber-400">day streak</span>
            </div>
          )}
          {gam.badge_count > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700">
              <span className="text-sm">🏅</span>
              <span className="text-sm font-bold text-purple-700 dark:text-purple-300">{gam.badge_count}</span>
            </div>
          )}
          {gam.xp > 0 && (
            <div className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700">
              <span className="text-sm">✨</span>
              <span className="text-sm font-bold text-indigo-700 dark:text-indigo-300">{gam.xp}</span>
              <span className="text-[9px] text-indigo-500 dark:text-indigo-400">XP</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats + Quick mode button */}
      <div className="flex items-center gap-3 mb-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700">
        <div className="flex-1 min-w-0">
          <div className="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${(mastered / Math.max(total, 1)) * 100}%` }} />
          </div>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-neutral-500 dark:text-neutral-400 flex-wrap">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500" /> {mastered} mastered</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> {in_progress}</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-neutral-300 dark:bg-neutral-600" /> {locked} locked</span>
          {curriculum.overall_ability !== undefined && (
            <span className="flex items-center gap-1 ml-2 pl-2 border-l border-neutral-200 dark:border-neutral-700">
              <span className="text-xs">{curriculum.avg_learning_speed > 1.2 ? '⚡' : curriculum.avg_learning_speed >= 0.8 ? '→' : '～'}</span>
              <span className="text-[9px]">speed {Math.round(curriculum.avg_learning_speed * 100)}%</span>
            </span>
          )}
        </div>
        <button onClick={() => setShowMasteryMap(!showMasteryMap)}
          className="px-3 py-2 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 text-[10px] font-medium cursor-pointer transition-colors shrink-0">
          {showMasteryMap ? '📋 List' : '🗺️ Map'}
        </button>
        <button onClick={startQuickSession}
          className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          ⏱ 5-min quick
        </button>
        <button onClick={() => setShowDailyVerse(true)}
          className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          📆 Verse of Day
        </button>
        <button onClick={() => setShowPassageReader(true)}
          className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          📖 Read Passage
        </button>
        <button onClick={() => setShowVerbDrill(true)}
          className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          ע Verb Drills
        </button>
        <button onClick={async () => {
          try {
            const r = await fetch('/api/v1/vocabulary?top=100&cutoff=10')
            const d = await r.json()
            const cards = (d.words || []).map(w => ({
              id: `vocab-${w.rank}-${w.hebrew?.replace(/[^a-zA-Z\u0590-\u05ff]/g, '')}`,
              type: 'vocab',
              data: {
                word: w.hebrew,
                definition: w.gloss,
                transliteration: w.transliteration,
                lemma: w.root || '',
                language: 'hebrew',
              },
            }))
            setFreqVocabCards(cards)
          } catch {}
          setShowFreqVocab(true)
        }}
          className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          📊 Top Vocab
        </button>
        <button onClick={async () => {
          try {
            const r = await fetch('/api/v1/vocabulary?top=50&cutoff=10')
            const d = await r.json()
            const words = (d.words || []).filter(w => w.hebrew && w.gloss).map(w => ({
              hebrew: w.hebrew,
              english: w.gloss,
              transliteration: w.transliteration,
            }))
            setAudioWords(words)
          } catch {}
          setShowAudioReview(true)
        }}
          className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          🎧 Audio Review
        </button>
        <button onClick={async () => {
          // Load both node cards and drill cards, interleave them
          const unlocked = curriculum?.nodes?.filter(n => n.unlocked) || []
          const nodeCards = hebrewToCards(unlocked)
          let drillCards = []
          try {
            const r = await fetch('/api/v1/hebrew/verb-drill?limit=8')
            const d = await r.json()
            if (d.ok) drillCards = drillsToCards(d.data.drills || [])
          } catch {}
          setHebrewReviewCards(interleaveCards([nodeCards, drillCards]))
          setShowHebrewReview(true)
        }}
          className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium cursor-pointer transition-colors shrink-0">
          🔄 Review 🔀
        </button>
      </div>

      {/* Badges row */}
      {gam.badge_catalog && gam.badge_catalog.filter(b => b.earned).length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4 px-4 py-3 rounded-xl bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
          <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mr-1">Badges</span>
          {gam.badge_catalog.filter(b => b.earned).map(b => (
            <span key={b.id} className="flex items-center gap-1 px-2 py-1 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-700 text-xs" title={b.desc}>
              <span>{b.icon}</span>
              <span className="text-[10px] font-medium text-purple-700 dark:text-purple-300">{b.name}</span>
            </span>
          ))}
          {gam.next_badges && gam.next_badges.length > 0 && (
            <span className="text-[9px] text-neutral-400 ml-2">
              Next: {gam.next_badges.map(b => b.name).join(', ')}
            </span>
          )}
        </div>
      )}

      {/* Category filter */}
      <div className="flex flex-wrap gap-1.5 mb-6">
        {[{id:'all',count:total,label:'All'}].concat(
          Object.entries(CATEGORY_STYLES).map(([cat, cs]) => ({
            id: cat, count: nodes.filter(n => n.category === cat).length, ...cs
          })).filter(c => c.count > 0)
        ).map(c => (
          <button key={c.id} onClick={() => setFilter(c.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer ${
              filter === c.id
                ? 'bg-indigo-600 text-white'
                : `${c.bg || 'bg-neutral-100 dark:bg-neutral-800'} ${c.text || 'text-neutral-600 dark:text-neutral-400'} hover:bg-neutral-200 dark:hover:bg-neutral-700`
            }`}>
            {c.icon && <span className="mr-1">{c.icon}</span>}
            {c.label || c.id} ({c.count})
          </button>
        ))}
      </div>

      {/* Mastery Map grid (toggle) */}
      {showMasteryMap && (
        <div className="mb-6 p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3">
            Mastery Map · {mastered}/{total} nodes mastered ({Math.round(mastered / Math.max(total, 1) * 100)}%)
          </h3>
          <div className="grid grid-cols-8 sm:grid-cols-10 md:grid-cols-12 gap-1.5">
            {nodes.map(node => {
              const locked = !node.unlocked
              const masteryPct = node.mastery || 0
              let color = ''
              if (locked) color = 'bg-neutral-200 dark:bg-neutral-700'
              else if (masteryPct >= 1.0) color = 'bg-yellow-400 dark:bg-yellow-500'
              else if (masteryPct >= 0.8) color = 'bg-green-500'
              else if (masteryPct >= 0.6) color = 'bg-blue-400'
              else if (masteryPct >= 0.3) color = 'bg-amber-400'
              else if (masteryPct > 0) color = 'bg-red-300 dark:bg-red-700'
              else color = 'bg-neutral-100 dark:bg-neutral-600'
              
              return (
                <button key={node.id}
                  onClick={() => { if (!locked) onOpenLesson?.(node.id) }}
                  disabled={locked}
                  className={`w-full aspect-square rounded-md ${color} transition-all hover:ring-2 hover:ring-indigo-400 cursor-pointer disabled:cursor-not-allowed relative group`}
                  title={`${node.title} (${Math.round(masteryPct * 100)}%)`}>
                  {/* Tooltip on hover */}
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 rounded bg-neutral-800 text-white text-[9px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    {node.title} — {Math.round(masteryPct * 100)}%
                  </span>
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-3 mt-3 text-[9px] text-neutral-400">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-400" /> Mastered</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500" /> 80%+</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-blue-400" /> Learning</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-400" /> Started</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-300" /> Needs work</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-neutral-200 dark:bg-neutral-700" /> Locked</span>
          </div>
        </div>
      )}

      {/* Lessons by level */}
      {!showMasteryMap && (
        <div className="space-y-6">
          {Object.entries(byLevel).map(([level, levelNodes]) => (
            <div key={level}>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-400 dark:text-neutral-500 mb-3">Level {level}</h3>
              <div className="space-y-1.5">
                {levelNodes.map(node => {
                  const cs = CATEGORY_STYLES[node.category] || {}
                  const isMastered = node.mastery >= 0.8
                  const isLearning = node.mastery > 0 && node.mastery < 0.8
                  const isLocked = !node.unlocked

                  return (
                    <button key={node.id} onClick={() => { if (!isLocked) onOpenLesson?.(node.id) }} disabled={isLocked}
                      className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left cursor-pointer group
                        ${isLocked ? 'opacity-40 cursor-not-allowed border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/30'
                          : isMastered ? `${cs.bg} ${cs.border} hover:shadow-sm`
                          : isLearning ? 'border-amber-200 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 hover:shadow-sm'
                          : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm'
                        }`}>
                      {/* Status dot */}
                      <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                        isLocked ? 'bg-neutral-300 dark:bg-neutral-600'
                          : isMastered ? 'bg-green-500'
                          : isLearning ? 'bg-amber-500'
                          : 'bg-neutral-200 dark:bg-neutral-700'
                      }`} />

                      {/* Level */}
                      <span className="text-[10px] font-mono text-neutral-400 dark:text-neutral-500 w-6 shrink-0">L{node.level}</span>

                      {/* Title + category */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-medium truncate ${isLocked ? 'text-neutral-400 dark:text-neutral-500' : 'text-neutral-800 dark:text-neutral-200'}`}>
                            {node.title}
                          </span>
                          {cs?.label && (
                            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium shrink-0 ${cs.bg} ${cs.text} ${cs.border} border`}>
                              {cs.icon} {cs.label}
                            </span>
                          )}
                        </div>
                        {node.description && (
                          <p className={`text-xs mt-0.5 truncate ${isLocked ? 'text-neutral-400' : 'text-neutral-500 dark:text-neutral-400'}`}>{node.description}</p>
                        )}
                      </div>

                      {/* Mastery bar */}
                      <div className="w-14 shrink-0">
                        <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${isMastered ? 'bg-green-500' : isLearning ? 'bg-amber-500' : 'bg-neutral-300 dark:bg-neutral-600'}`}
                            style={{ width: `${node.mastery * 100}%` }} />
                        </div>
                        <span className="text-[8px] text-neutral-400 dark:text-neutral-500 mt-0.5 block text-right">{Math.round(node.mastery * 100)}%</span>
                      </div>

                      {/* Learning speed indicator */}
                      {!isLocked && node.learning_speed !== undefined && (
                        <div className="w-6 shrink-0 flex items-center justify-center" title={
                          node.learning_speed > 1.5 ? 'Fast learner on this topic' :
                          node.learning_speed >= 0.8 ? 'Normal pace' :
                          node.learning_speed >= 0.4 ? 'Needs extra practice' :
                          'Struggling — review prerequisites'
                        }>
                          <span className={`text-xs ${
                            node.learning_speed > 1.5 ? 'text-green-500' :
                            node.learning_speed >= 0.8 ? 'text-blue-400' :
                            node.learning_speed >= 0.4 ? 'text-amber-500' :
                            'text-red-500'
                          }`}>
                            {node.learning_speed > 1.5 ? '⚡' :
                             node.learning_speed >= 0.8 ? '→' :
                             node.learning_speed >= 0.4 ? '～' :
                             '⚠'}
                          </span>
                        </div>
                      )}

                      {isLocked && <span className="text-xs text-neutral-400 shrink-0">🔒</span>}
                      {!isLocked && !isMastered && <span className="text-xs text-indigo-500 dark:text-indigo-400 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">→</span>}
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {filtered.length === 0 && (
        <div className="p-8 text-center text-sm text-neutral-500 dark:text-neutral-400">
          No lessons in this category. Try another filter.
        </div>
      )}
    </div>
  )
}
