import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { currentSessionToken, fetchJSON, hebrewSessionUser } from '../api'
import { fetchAudioUrl, playUrl } from '../lib/audio-pool'
import RatingButtons from './RatingButtons'

/**
 * AnkiReview — Dedicated flip-card study view for Hebrew vocabulary.
 *
 * Three card modes (shuffled for interleaving):
 *   "hearing"  — Listen to audio, think of translation. Flip to see answer.
 *   "reverse"  — See English gloss, think of Hebrew word. Flip to see answer.
 *   "forward"  — See Hebrew word, think of English gloss. Flip to see answer.
 *   "picture"  — See the WHV deck picture, think of the Hebrew word. Flip to
 *     see answer. Only assigned when a Tier-0 picture exists (see modesForCard).
 *
 * On the back: answer + image + audio + transliteration + verse example.
 * Rating: Again(1) / Hard(2) / Good(3) / Easy(4) — FSRS-5 compatible.
 *
 * Props:
 *   cards: Array of { node_id, hebrew, gloss, transliteration, image_url, audio_url }
 *     node_id may be '' for non-curriculum words — hebrew text is sent
 *     instead and the backend resolves it (see hebrew-card-rules.md rule 7).
 *   onComplete: () => void  — Called after all cards rated
 *   title: String — Optional title for the session
 *   onBack: () => void — Go back to previous view
 */
const CARD_MODES = ['hearing', 'reverse', 'forward', 'picture']

/**
 * Modes for one card: server due_modes win when present; otherwise all four
 * directions — minus picture when no Tier-0 picture is cached for the word.
 * Pure (vitest-covered); keeps imageless words from drawing blank fronts.
 */
export function modesForCard(card, hasPicture) {
  if (card.modes && card.modes.length) return card.modes
  return hasPicture ? CARD_MODES : CARD_MODES.filter(m => m !== 'picture')
}

export default function AnkiReview({ cards: initialCards, onComplete, title, onBack }) {
  // Two-pass build: prefetch Tier-0 pictures first, then assign modes so the
  // picture direction is only dealt to words that actually have a picture.
  // (Server due_modes pass through untouched via modesForCard.)
  const [cards, setCards] = useState(null)
  const [imageCache, setImageCache] = useState({})
  useEffect(() => {
    let cancelled = false
    const seen = new Set()
    Promise.all(initialCards.filter(c => c.hebrew && !seen.has(c.hebrew) && seen.add(c.hebrew)).map(async (c) => {
      try {
        const r = await fetchJSON(`/hebrew/image/${encodeURIComponent(c.hebrew)}`)
        if (r.ok && r.data?.image_url) return [c.hebrew, r.data]
      } catch (_) {}
      return [c.hebrew, null]
    })).then(results => {
      if (cancelled) return
      const cache = {}
      for (const [hebrew, data] of results) if (data) cache[hebrew] = data
      setImageCache(cache)
      const withModes = initialCards.flatMap(c =>
        modesForCard(c, !!cache[c.hebrew]).map(mode => ({ ...c, mode, id: `${c.node_id || c.hebrew}_${mode}` }))
      )
      // Fisher-Yates shuffle
      for (let i = withModes.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [withModes[i], withModes[j]] = [withModes[j], withModes[i]]
      }
      setCards(withModes)
    })
    return () => { cancelled = true }
  }, [initialCards])

  const [currentIdx, setCurrentIdx] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [ratings, setRatings] = useState({})
  const [saveFailed, setSaveFailed] = useState(0)
  const [audioUrl, setAudioUrl] = useState(null)
  const spaceRef = useRef(false)

  const currentCard = cards?.[currentIdx]
  const isComplete = !!cards && currentIdx >= cards.length
  const totalCards = cards?.length || 0
  // Anki-style interval preview, same shared scheduler as memorize.
  // Cleared on card change so a stale card's waits never flash.
  const [intervals, setIntervals] = useState(null)
  const intervalsCard = useRef(null)
  useEffect(() => {
    const nid = currentCard?.node_id
    const cmode = currentCard?.mode || ''
    const key = `${nid}|${cmode}`
    if (intervalsCard.current !== key) {
      intervalsCard.current = key
      setIntervals(null)
    }
    if ((!nid && !currentCard?.hebrew) || !flipped) return
    const sessionToken = currentSessionToken()
    const params = new URLSearchParams({ node_id: nid, card_mode: cmode, hebrew: currentCard?.hebrew || '', lemma: currentCard?.lemma || '' })
    fetch(`/api/v1/hebrew/fsrs/intervals?${params}`, {
      headers: sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {},
    })
      .then(r => r.json())
      .then(d => {
        if (intervalsCard.current !== key) return
        setIntervals(d.ok ? d.data?.intervals || null : null)
      })
      .catch(() => { if (intervalsCard.current === key) setIntervals(null) })
  }, [currentCard?.node_id, currentCard?.mode, flipped, currentIdx])

  // NOTE: image prefetch now happens in the two-pass build above (modes need
  // to know which words have Tier-0 pictures before cards are dealt).

  // Auto-play audio for hearing mode when card is shown (pooled: cached URL + shared element).
  useEffect(() => {
    if (!currentCard || flipped) return
    if (currentCard.mode === 'hearing' && currentCard.hebrew) {
      let cancelled = false
      fetchAudioUrl(currentCard.hebrew).then(url => {
        if (cancelled || !url) return
        setAudioUrl(url)
        playUrl(url)
      })
      return () => { cancelled = true }
    }
  }, [currentCard?.id, flipped])

  const handleFlip = useCallback(() => {
    if (!flipped) setFlipped(true)
  }, [flipped])

  const handleRate = useCallback(async (rating) => {
    if (!currentCard || !flipped) return
    setRatings(prev => ({ ...prev, [currentCard.id]: rating }))
    // Submit rating to FSRS
    try {
      await hebrewSessionUser()
      const sessionToken = currentSessionToken()
      await fetchJSON('/hebrew/fsrs/review', {
        method: 'POST',
        body: JSON.stringify({
          node_id: currentCard.node_id, rating, user_id: 'default',
          hebrew: currentCard.hebrew || '', lemma: currentCard.lemma || '',
          session_token: sessionToken, card_mode: currentCard.mode,
        }),
        headers: {
          'Content-Type': 'application/json',
          ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
        },
      })
    } catch (_) { setSaveFailed(n => n + 1) }
    // Advance
    setFlipped(false)
    setAudioUrl(null)
    setCurrentIdx(i => i + 1)
  }, [currentCard, flipped])

  // Keyboard shortcuts
  useEffect(() => {
    function handleKey(e) {
      if (onBack && e.key === 'Escape') { onBack(); return }
      if (!flipped && (e.key === ' ' || e.key === 'Enter')) {
        e.preventDefault()
        spaceRef.current = true
        handleFlip()
        return
      }
      if (flipped && ['1', '2', '3', '4'].includes(e.key)) {
        handleRate(parseInt(e.key))
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [flipped, handleFlip, handleRate, onBack])

  // Loading state while the two-pass build prefetches pictures + deals modes
  if (!cards) {
    return (
      <div className="max-w-lg mx-auto px-6 py-12 text-center">
        <p className="text-sm text-neutral-500 dark:text-neutral-400 animate-pulse">
          Loading cards…
        </p>
      </div>
    )
  }

  // Completion screen
  if (isComplete) {
    const counts = { 1: 0, 2: 0, 3: 0, 4: 0 }
    Object.values(ratings).forEach(r => { counts[r] = (counts[r] || 0) + 1 })
    return (
      <div className="max-w-lg mx-auto px-6 py-12 text-center">
        <div className="text-4xl mb-4">🎉</div>
        <h2 className="text-xl font-semibold text-neutral-800 dark:text-neutral-200 mb-2">
          Review Complete!
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
          {totalCards} cards studied
        </p>
        {saveFailed > 0 && (
          <p className="text-xs text-amber-600 dark:text-amber-400 mb-6">
            ⚠️ {saveFailed} rating{saveFailed === 1 ? '' : 's'} couldn't be saved to the schedule — those cards will come up again.
          </p>
        )}
        <div className="flex justify-center gap-4 mb-8">
          {[1, 2, 3, 4].map(r => (
            <div key={r} className="text-center">
              <div className={`text-lg font-bold ${r === 1 ? 'text-red-500' : r === 2 ? 'text-amber-500' : r === 3 ? 'text-green-500' : 'text-blue-500'}`}>
                {counts[r] || 0}
              </div>
              <div className="text-[10px] text-neutral-400">
                {['Again', 'Hard', 'Good', 'Easy'][r - 1]}
              </div>
            </div>
          ))}
        </div>
        <button onClick={onComplete}
          className="px-6 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium transition-colors">
          Done
        </button>
      </div>
    )
  }

  // Current card front/back
  const { hebrew, gloss, transliteration, mode } = currentCard
  const img = imageCache[hebrew]

  const frontContent = () => {
    switch (mode) {
      case 'hearing':
        return (
          <div className="text-center">
            <div className="text-lg text-neutral-400 mb-4">🔊 Listen & Translate</div>
            <div className="text-sm text-neutral-500 dark:text-neutral-400 animate-pulse">
              Audio playing...
            </div>
          </div>
        )
      case 'reverse':
        return (
          <div className="text-center">
            <div className="text-lg text-neutral-400 mb-4">🇺🇸 English → Hebrew</div>
            <div className="text-3xl font-semibold text-neutral-800 dark:text-neutral-200">
              {gloss}
            </div>
          </div>
        )
      case 'forward':
        return (
          <div className="text-center">
            <div className="text-lg text-neutral-400 mb-4">🇮🇱 Hebrew → English</div>
            <div className="text-4xl font-serif leading-relaxed text-neutral-800 dark:text-neutral-200"
              style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
              {hebrew}
            </div>
            {transliteration && (
              <div className="text-sm text-neutral-500 mt-2">{transliteration}</div>
            )}
          </div>
        )
      case 'picture':
        return (
          <div className="text-center">
            <div className="text-lg text-neutral-400 mb-4">🖼️ Picture → Hebrew</div>
            {img?.image_url ? (
              <img
                src={img.image_url}
                alt="Think of the Hebrew word"
                className="w-full h-48 object-cover rounded-lg"
                loading="lazy"
                onError={(e) => { e.target.style.display = 'none' }}
              />
            ) : (
              <div className="text-sm text-neutral-500 dark:text-neutral-400 animate-pulse">
                Loading picture...
              </div>
            )}
          </div>
        )
      default:
        return null
    }
  }

  const backContent = () => (
    <div className="space-y-4">
      {/* Answer display */}
      <div className="text-center">
        <div className="text-3xl font-serif leading-relaxed text-neutral-800 dark:text-neutral-200"
          style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
          {hebrew}
        </div>
        <div className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
          {transliteration}
        </div>
        <div className="text-lg font-medium text-blue-600 dark:text-blue-400 mt-2">
          {gloss}
        </div>
      </div>

      {/* Image (Anki-style Extra field) */}
      {img?.image_url && (
        <div className="relative w-full overflow-hidden rounded-lg bg-neutral-50 dark:bg-neutral-800 max-h-64">
          <img
            src={img.image_url}
            alt={hebrew}
            className="w-full h-48 object-cover"
            loading="lazy"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        </div>
      )}

      {/* Verse context fallback if no image */}
      {!img?.image_url && gloss && (
        <div className="text-xs text-neutral-400 text-center italic">
          {gloss}
        </div>
      )}

      {/* Rating buttons */}
      <RatingButtons intervals={intervals} onRate={(v) => handleRate(v)} variant="grid" showKeys />
    </div>
  )

  return (
    <div className="max-w-lg mx-auto px-4 py-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {onBack && (
            <button onClick={onBack}
              className="text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors px-2 py-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800">
              ← Back
            </button>
          )}
          <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            {title || 'Flashcard Review'}
          </h3>
        </div>
        <span className="text-xs text-neutral-400 font-mono">
          {currentIdx + 1}/{totalCards}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all duration-300"
          style={{ width: `${((currentIdx) / totalCards) * 100}%` }}
        />
      </div>

      {/* Card */}
      <div
        className="bg-white dark:bg-neutral-900 rounded-xl shadow-lg border border-neutral-200 dark:border-neutral-700 p-6 min-h-[300px] flex flex-col justify-center cursor-pointer select-none"
        onClick={handleFlip}
      >
        {!flipped ? frontContent() : backContent()}
      </div>

      {/* Hint */}
      {!flipped && (
        <p className="text-xs text-neutral-400 text-center mt-3">
          Click or press Space to flip
        </p>
      )}
      {flipped && (
        <p className="text-xs text-neutral-400 text-center mt-3">
          Press 1-4 to rate
        </p>
      )}
    </div>
  )
}
