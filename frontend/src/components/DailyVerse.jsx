import React, { useState, useEffect, useRef } from 'react'
import { preprocess, createComponents } from '../lib/scripture-markdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

/**
 * DailyVerse — maintenance mode: one random verse per day with analysis.
 *
 * Inspired by Daily Dose of Hebrew.
 * Shows verse with word-by-word breakdown, gematria, connections.
 * Plays real audio from Schmueloff recordings when available,
 * falls back to browser TTS.
 */
export default function DailyVerse({ onNavigate, onOpenLesson }) {
  const [verse, setVerse] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showBreakdown, setShowBreakdown] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [audioInfo, setAudioInfo] = useState(null)
  const [studiedWords, setStudiedWords] = useState(new Set())
  const [unmasteredInVerse, setUnmasteredInVerse] = useState([])
  const [showStudyMode, setShowStudyMode] = useState(false)
  const [studyIdx, setStudyIdx] = useState(0)
  const audioRef = useRef(null)

  const loadVerse = async () => {
    setLoading(true)
    setAudioInfo(null)
    try {
      const r = await fetch('/api/v1/verse-of-day')
      const d = await r.json()
      if (d.ok) {
        setVerse(d.data)
        // Also fetch audio info for this verse
        try {
          const ar = await fetch(`/api/v1/read-along/${d.data.verse_id}`)
          const ad = await ar.json()
          if (ad.ok) setAudioInfo(ad.data)
        } catch {}
      }
    } catch {}
    setLoading(false)
  }

  useEffect(() => { loadVerse() }, [])

  // Fetch studied vocabulary to highlight known words
  useEffect(() => {
    fetch('/api/v1/hebrew/curriculum').then(r => r.json()).then(d => {
      if (d.ok && d.data?.nodes) {
        const studied = new Set()
        for (const node of d.data.nodes) {
          if (node.category === 'word' && node.unlocked && node.mastery > 0) {
            const heb = node.title?.split(' — ')[0]?.trim()
            if (heb) studied.add(heb)
          }
        }
        setStudiedWords(studied)
      }
    }).catch(() => {})
  }, [])

  // When verse loads, find unmastered words
  useEffect(() => {
    if (!verse?.text_hebrew || studiedWords.size === 0) return
    const words = verse.text_hebrew.split(/\s+/).filter(Boolean)
    const unmastered = []
    for (const w of words) {
      const clean = w.replace(/[\/\u0591-\u05bd\u05bf\u05c1-\u05c7]/g, '').replace(/[^a-zA-Z\u0590-\u05fe]/g, '')
      if (clean && !studiedWords.has(clean)) {
        unmastered.push(clean)
      }
    }
    setUnmasteredInVerse([...new Set(unmastered)].slice(0, 10))
  }, [verse, studiedWords])

  const handleSpeak = () => {
    if (!verse?.text_hebrew) return

    // If real audio is available, use it
    if (audioInfo?.audio_url && (audioInfo.audio_source === 'schmueloff' || audioInfo.word_timestamps?.length > 0)) {
      if (speaking && audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
        setSpeaking(false)
        return
      }
      const audio = new Audio(audioInfo.audio_url)
      audioRef.current = audio
      audio.onended = () => setSpeaking(false)
      audio.onerror = () => {
        // Fallback to TTS if audio fails
        useTTS()
      }
      setSpeaking(true)
      audio.play().catch(() => useTTS())
      return
    }

    // Fallback: browser TTS
    useTTS()
  }

  const useTTS = () => {
    if (!window.speechSynthesis) return
    if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); return }
    const utterance = new SpeechSynthesisUtterance(
      (verse?.text_hebrew || '').replace(/[/\u0591-\u05bd\u05bf\u05c1-\u05c7]/g, '')
    )
    utterance.lang = 'he-IL'
    utterance.rate = 0.8
    utterance.onend = () => setSpeaking(false)
    setSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  if (loading) return (
    <div className="max-w-2xl mx-auto px-4 py-8 text-center">
      <div className="animate-pulse space-y-3">
        <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3 mx-auto" />
        <div className="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-2/3 mx-auto" />
        <div className="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2 mx-auto" />
      </div>
    </div>
  )

  if (!verse) return (
    <div className="max-w-2xl mx-auto px-4 py-8 text-center">
      <p className="text-sm text-neutral-400">No verse available.</p>
      <button onClick={loadVerse}
        className="mt-3 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium cursor-pointer hover:bg-indigo-700 transition-colors">
        Try Again
      </button>
    </div>
  )

  // Study mode: show unmastered words one at a time for practice
  if (showStudyMode) {
    const word = unmasteredInVerse[studyIdx]
    if (!word) {
      return (
        <div className="max-w-2xl mx-auto px-4 py-8 text-center">
          <p className="text-sm text-green-600 dark:text-green-400 mb-4">All words studied! 🎉</p>
          <button onClick={() => setShowStudyMode(false)} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Back to verse</button>
        </div>
      )
    }
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-amber-200 dark:border-amber-800 shadow-sm text-center">
          <span className="text-[9px] font-medium text-neutral-400 uppercase tracking-wider">Study Word {studyIdx + 1} of {unmasteredInVerse.length}</span>
          <p className="text-3xl font-serif my-6" dir="rtl" style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>{word}</p>
          <div className="flex gap-3 justify-center">
            <button onClick={() => { setStudyIdx(i => i + 1) }}
              className="px-6 py-2 rounded-xl bg-green-600 hover:bg-green-700 text-white text-sm font-medium cursor-pointer transition-colors">✓ Know it</button>
            <button onClick={() => {
              // Open the vocabulary study for this word
              if (onOpenLesson) {
                const nid = `vocab_${word.replace(/[^\u0590-\u05fe]/g, '')}`
                onOpenLesson(nid)
              }
            }}
              className="px-6 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">📖 Study</button>
            <button onClick={() => setShowStudyMode(false)}
              className="px-6 py-2 rounded-xl bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 text-sm font-medium cursor-pointer transition-colors">← Back</button>
          </div>
        </div>
      </div>
    )
  }

  const hebWords = (verse.text_hebrew || '').split(/\s+/).filter(w => w.length > 0)

  // Helper: split Hebrew text into words with known/unknown markers
  const renderHebrewWithHighlights = (text) => {
    const words = text.split(/\s+/).filter(Boolean)
    return words.map((w, i) => {
      const clean = w.replace(/[\/\u0591-\u05bd\u05bf\u05c1-\u05c7]/g, '').replace(/[^\u0590-\u05fe]/g, '')
      const isStudied = studiedWords.has(clean)
      return (
        <span key={i}
          className={`inline-block px-0.5 rounded transition-colors ${
            isStudied
              ? 'text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/20'
              : 'text-neutral-700 dark:text-neutral-300'
          }`}
          title={isStudied ? 'Studied ✓' : 'New word'}>
          {w}
        </span>
      )
    })
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      {/* Date badge */}
      <div className="text-center mb-4">
        <span className="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </span>
      </div>

      {/* Verse card */}
      <div className="p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-indigo-200 dark:border-indigo-800 shadow-sm">
        {/* Hebrew with known-word highlighting */}
        <div className="text-center mb-4">
          <p className="text-xl font-serif leading-relaxed flex flex-wrap justify-center gap-1"
            style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
            dir="rtl">
            {renderHebrewWithHighlights(verse.text_hebrew || '')}
          </p>
        </div>

        {/* Audio button */}
        <div className="text-center mb-4">
          <button onClick={handleSpeak}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
              speaking
                ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-600'
            }`}>
            {speaking ? '⏹ Stop' : '🔊 Listen'}
          </button>
        </div>

        {/* Study These Words button */}
        {unmasteredInVerse.length > 0 && (
          <div className="text-center mb-4">
            <button onClick={() => setShowStudyMode(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/30 border border-amber-200 dark:border-amber-700 cursor-pointer transition-colors">
              📚 Study These Words ({unmasteredInVerse.length})
            </button>
          </div>
        )}
        {unmasteredInVerse.length === 0 && studiedWords.size > 0 && (
          <div className="text-center mb-4">
            <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400">
              All words known! 🎉
            </span>
          </div>
        )}

        {/* English */}
        <p className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed text-center italic">
          {verse.text_english}
        </p>
      </div>

      {/* Reference + navigation */}
      <div className="text-center mt-3">
        <button onClick={() => {
          const p = verse.verse_id.split('.')
          if (p.length >= 2 && onNavigate) onNavigate(p[0], parseInt(p[1]))
        }}
          className="text-xs font-mono text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">
          {verse.reference || verse.verse_id}
        </button>
      </div>

      {/* Word breakdown toggle */}
      <div className="mt-4">
        <button onClick={() => setShowBreakdown(!showBreakdown)}
          className="w-full px-3 py-2 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 cursor-pointer transition-colors text-center border border-neutral-200 dark:border-neutral-700">
          {showBreakdown ? '▲ Hide word breakdown' : '▼ Show word breakdown'}
        </button>

        {showBreakdown && (
          <div className="mt-2 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
            <h3 className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Word Breakdown</h3>
            <div className="space-y-1">
              {hebWords.map((w, i) => {
                const clean = w.replace(/[^\u0590-\u05fe]/g, '')
                return (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="font-serif text-sm text-neutral-800 dark:text-neutral-200"
                      style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
                      {clean}
                    </span>
                    <span className="text-[9px] text-neutral-400 font-mono">{w.length} letters</span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Stats footer */}
      <div className="mt-4 flex items-center justify-center gap-4 text-[9px] text-neutral-400">
        <span>{verse.word_count} words</span>
        {verse.has_gematria && <span>Has gematria</span>}
        <span>{verse.connections_count} connections</span>
      </div>

      {/* New verse button */}
      <div className="text-center mt-4">
        <button onClick={loadVerse}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors">
          Next Verse →
        </button>
      </div>
    </div>
  )
}
