import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import CardQueue from './CardQueue'
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
        onClick={() => onNavigate?.(`${t.book.toLowerCase()}.${t.ch}`)}
        className="text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer font-medium"
        title={`Open ${t.book}.${t.ch}`}>
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
  const audioRef = useRef(null)

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
        setPractice(practiceRes.data?.items || [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [nodeId])

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

  // Flashcard rating → progress API
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

      {/* CardQueue — flashcards sorted by difficulty (MC → recall → typing) */}
      {cards.length > 0 ? (
        <div className="mb-6">
          <CardQueue
            cards={cards}
            onRate={handleFlashcardRate}
            onComplete={() => {}}
            title={node?.title || 'Practice'}
            emptyMessage="All done! Start another lesson or come back later."
          />
        </div>
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
