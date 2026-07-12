import React, { useState, useEffect, useMemo } from 'react'
import CardQueue from './CardQueue'
import { lessonToCards } from '../lib/card-factory'

/**
 * PassageReader — LingQ-style passage study mode.
 *
 * Reads a biblical passage, color-codes each Hebrew word by known status,
 * lets users click words for definitions, and generates vocabulary cards.
 *
 * Props:
 *   passageId: string (e.g., "gen.22.1-19" or "gen.22" for chapter)
 *   userId: string
 *   onNavigate: (book, chapter) => void
 */
export default function PassageReader({ passageId, userId = 'default', onNavigate }) {
  const [verses, setVerses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [knownWords, setKnownWords] = useState(new Set())
  const [selectedWord, setSelectedWord] = useState(null)
  const [showCards, setShowCards] = useState(false)
  const [practiceCards, setPracticeCards] = useState([])

  // Parse passage ID
  const passageInfo = useMemo(() => {
    if (!passageId) return null
    const parts = passageId.split('.')
    const book = parts[0]
    const ch = parseInt(parts[1])
    let startVerse = 1
    let endVerse = null
    if (parts[2]?.includes('-')) {
      const vr = parts[2].split('-')
      startVerse = parseInt(vr[0])
      endVerse = parseInt(vr[1])
    } else if (parts[2]) {
      startVerse = parseInt(parts[2])
      endVerse = parts[3] ? parseInt(parts[3]) : startVerse
    }
    return { book, chapter: ch, startVerse, endVerse }
  }, [passageId])

  useEffect(() => {
    if (!passageInfo) return
    setLoading(true)
    setError(null)

    const { book, chapter, startVerse, endVerse } = passageInfo
    const limit = endVerse ? endVerse - startVerse + 1 : 50

    fetch(`/api/v1/chapter/${book}.${chapter}?limit=${limit}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          const vs = (d.data?.verses || d.data?.verse_list || []).filter(v => {
            const vn = parseInt(v.verse || v.verse_num)
            return vn >= startVerse && (!endVerse || vn <= endVerse)
          }).map(v => ({
            id: v.id || `${book}.${chapter}.${v.verse || v.verse_num}`,
            text_english: v.text_english || v.text || '',
            text_hebrew: v.text_hebrew || '',
            verse: parseInt(v.verse || v.verse_num),
          }))
          setVerses(vs)
        } else {
          setError(d.detail || 'Failed to load passage')
        }
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [passageInfo])

  // Load known words from user's learning progress
  useEffect(() => {
    if (!userId) return
    fetch(`/api/v1/learn/modules?user_id=${userId}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          // Collect mastered vocabulary
          const known = new Set()
          for (const m of (d.data?.modules || [])) {
            if (m.status === 'mastered') known.add(m.title.toLowerCase())
          }
          setKnownWords(known)
        }
      })
      .catch(() => {})
  }, [userId])

  // Tokenize Hebrew text into word tokens
  const tokens = useMemo(() => {
    if (!verses.length) return []
    const result = []
    for (const v of verses) {
      if (!v.text_hebrew) continue
      // Split Hebrew into individual word tokens
      const words = v.text_hebrew.split(/\s+/).filter(w => w.length > 0)
      for (const w of words) {
        const cleaned = w.replace(/[^\u0590-\u05fe]/g, '')
        result.push({
          word: w,
          cleaned,
          verse_id: v.id,
          known: knownWords.has(w) || knownWords.has(cleaned),
        })
      }
    }
    return result
  }, [verses, knownWords])

  // Look up a word's definition
  const lookupWord = async (word) => {
    const cleaned = word.replace(/[^\u0590-\u05fe]/g, '')
    try {
      const r = await fetch(`/api/v1/lexicon/search?q=${encodeURIComponent(cleaned)}&limit=1`)
      const d = await r.json()
      if (d.ok && d.data?.results?.length > 0) {
        const entry = d.data.results[0]
        setSelectedWord({
          word: cleaned,
          definition: entry.definition || 'No definition available',
          lemma: entry.lemma || '',
          root: entry.root_letters || '',
          transliteration: entry.transliteration || '',
          frequency: entry.frequency || '',
        })
      } else {
        // Try Strong's lookup
        const gem = await fetch(`/api/v1/strongs?word=${encodeURIComponent(cleaned)}`)
        const gd = await gem.json()
        if (gd.ok) {
          setSelectedWord({
            word: cleaned,
            definition: gd.data?.definition || 'Word not found in lexicon',
            lemma: gd.data?.lemma || '',
          })
        } else {
          setSelectedWord({ word: cleaned, definition: 'Word not found', lemma: '' })
        }
      }
    } catch {
      setSelectedWord({ word: cleaned, definition: 'Lookup failed', lemma: '' })
    }
  }

  // Add unknown words to practice queue
  const generatePractice = () => {
    const unknown = tokens.filter(t => !t.known && t.cleaned.length > 1)
      .slice(0, 10)
    const cards = unknown.map((t, i) => ({
      id: `passage-vocab-${i}`,
      type: 'vocab',
      data: {
        word: t.word,
        language: 'hebrew',
        verse_ref: t.verse_id,
      },
    }))
    setPracticeCards(cards)
    setShowCards(true)
  }

  if (loading) return <div className="p-8 text-center text-sm text-neutral-400 animate-pulse">Loading passage…</div>
  if (error) return <div className="p-4 text-red-500 text-sm">{error}</div>
  if (!verses.length) return <div className="p-8 text-center text-sm text-neutral-400">No verses found.</div>

  if (showCards) {
    return (
      <div>
        <div className="max-w-3xl mx-auto px-4 pt-2">
          <button onClick={() => { setShowCards(false); setPracticeCards([]) }}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Passage
          </button>
        </div>
        <CardQueue
          cards={practiceCards}
          title="Passage Vocabulary"
          emptyMessage="No new words to learn!"
        />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">
            {passageInfo.book}.{passageInfo.chapter}
            {passageInfo.startVerse}{passageInfo.endVerse ? `-${passageInfo.endVerse}` : ''}
          </h2>
          <p className="text-xs text-neutral-500">{tokens.length} words · {verses.length} verses</p>
        </div>
        <button onClick={generatePractice}
          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors">
          Practice Unknown ({tokens.filter(t => !t.known && t.cleaned.length > 1).length})
        </button>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 mb-4 text-[10px] text-neutral-500">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500" /> Known
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Learning
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Unknown
        </span>
      </div>

      {/* Passage text — Hebrew with color-coded words */}
      <div className="p-5 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-sm">
        <div className="text-xl font-serif leading-loose text-right"
          style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
          dir="rtl">
          {tokens.map((t, i) => (
            <span key={i}
              onClick={() => lookupWord(t.cleaned)}
              className={`cursor-pointer transition-colors rounded px-0.5 ${
                t.known
                  ? 'text-green-600 dark:text-green-400'
                  : t.cleaned.length > 1
                    ? 'text-red-500 dark:text-red-300 hover:bg-red-100 dark:hover:bg-red-900/30'
                    : 'text-neutral-400'
              }`}
              title={t.cleaned}>
              {t.word}{' '}
            </span>
          ))}
        </div>
      </div>

      {/* English side-by-side */}
      <details className="mt-3">
        <summary className="text-xs text-neutral-400 cursor-pointer hover:text-neutral-600">Show English</summary>
        <div className="mt-2 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/50 text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
          {verses.map((v, i) => (
            <p key={i} className="mb-1">{v.text_english}</p>
          ))}
        </div>
      </details>

      {/* Word definition popup */}
      {selectedWord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setSelectedWord(null)}>
          <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-xl border border-neutral-200 dark:border-neutral-700 p-5 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
            <div className="text-right mb-3">
              <p className="text-2xl font-serif text-neutral-800 dark:text-neutral-200"
                style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
                {selectedWord.word || ''}
              </p>
            </div>
            <p className="text-sm text-neutral-700 dark:text-neutral-300">{selectedWord.definition}</p>
            <div className="flex flex-wrap gap-2 mt-2 text-[10px] text-neutral-400">
              {selectedWord.lemma && <span>Strong's: {selectedWord.lemma}</span>}
              {selectedWord.root && <span>Root: {selectedWord.root}</span>}
              {selectedWord.transliteration && <span>{selectedWord.transliteration}</span>}
              {selectedWord.frequency && <span>Occurrences: {selectedWord.frequency}</span>}
            </div>
            <button onClick={() => {
              // Add this word to practice cards
              setSelectedWord(null)
            }}
              className="mt-3 w-full py-1.5 rounded-lg text-xs font-medium bg-indigo-600 text-white hover:bg-indigo-700 cursor-pointer transition-colors">
              Add to vocabulary practice
            </button>
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="mt-4 flex items-center gap-4 text-[10px] text-neutral-400">
        <span>Known: {tokens.filter(t => t.known).length}/{tokens.length}</span>
        <span>Unknown: {tokens.filter(t => !t.known && t.cleaned.length > 1).length}</span>
        <span>{Math.round((tokens.filter(t => t.known).length / tokens.length) * 100)}% complete</span>
      </div>
    </div>
  )
}
