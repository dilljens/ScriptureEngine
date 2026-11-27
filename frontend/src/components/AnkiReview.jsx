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
 * repairMode — guarantee no blank faces. A dealt direction is only kept
 * when its stimulus can actually render; otherwise fall back to a direction
 * that can (never train the scheduler on a stimulus-less trial):
 *   picture w/o image  -> forward (needs hebrew) else drop
 *   reverse w/o gloss   -> forward (needs hebrew) else drop
 *   forward w/o hebrew  -> reverse (needs gloss) else drop
 *   hearing             -> kept while audio is unknown (hasAudio undefined,
 *                            resolved lazily at show time); known-missing audio
 *                            -> forward (needs hebrew), unresolvable -> drop
 * Returns the mode to deal, or null to drop the card.
 * Pure (vitest-covered) — keeps blank-face repair separate from the
 * server's due-mode pass-through in modesForCard.
 */
export function repairMode(mode, { hebrew, gloss, hasPicture, hasAudio } = {}) {
  const ok = (s) => typeof s === 'string' && s.trim().length > 0
  if (mode === 'picture' && !hasPicture) mode = 'forward'
  if (mode === 'reverse' && !ok(gloss)) mode = 'forward'
  if (mode === 'forward' && !ok(hebrew)) mode = ok(gloss) ? 'reverse' : null
  if (mode === 'hearing' && !ok(hebrew)) mode = ok(gloss) ? 'reverse' : null
  if (mode === 'hearing' && hasAudio === false) mode = ok(hebrew) ? 'forward' : null
  if (mode === 'picture' && !ok(hebrew)) mode = null
  return mode
}

/**
 * resolveDealModes — deal every card through modesForCard, then repair each
 * dealt direction against the prefetched picture cache. Drops only cards
 * with nothing renderable (both stimuli missing); converts the rest.
 * Pure (vitest-covered).
 */
export function resolveDealModes(cards, imageCache) {
  const out = []
  for (const c of cards || []) {
    for (const mode of modesForCard(c, !!(imageCache || {})[c.hebrew])) {
      const fixed = repairMode(mode, { hebrew: c.hebrew, gloss: c.gloss, hasPicture: !!(imageCache || {})[c.hebrew] })
      if (!fixed) continue
      out.push({ ...c, mode: fixed, id: `${c.node_id || c.hebrew}_${fixed}` })
    }
  }
  return out
}

/**
 * Modes for one card: server due_modes win when present; otherwise all four
 * directions — minus picture when no Tier-0 picture is cached for the word.
 * Pure (vitest-covered); deal-time repair in resolveDealModes handles the
 * remaining unrenderable cases (missing gloss, missing audio at show time).
 */
export function modesForCard(card, hasPicture) {
  if (card.modes && card.modes.length) return card.modes
  return hasPicture ? CARD_MODES : CARD_MODES.filter(m => m !== 'picture')
}

/**
 * Live re-deal position for a relearn card (intraday learn-ahead collapse).
 * The card returns after a few others rather than after wall-clock minutes
 * — the same collapse Anki's learn-ahead limit performs. Pure; capped by
 * the caller (max 2 re-deals per card per session).
 */
export const RELEARN_REDEAL_GAP = 3
export const MAX_REDEALS_PER_CARD = 2
export function relearnInsertAt(pos, total) {
  if (total <= 0) return 0
  return Math.min(total, Math.max(0, pos) + 1 + RELEARN_REDEAL_GAP)
}

/**
 * CardFront — pure presentational face of a flashcard (no state, no effects).
 * Exported so the front/back stimulus invariants (card-rules rule 1/2:
 * front = ONE stimulus, never the answer) are executable assertions in
 * `src/__tests__/ankiCardFaces.test.js` instead of eyeball checks.
 *
 * Props: mode, hebrew, gloss, transliteration, img ({image_url} | null),
 * audioUrl (string | null), onReplay (replay-audio callback).
 */
export function CardFront({ mode, hebrew, gloss, transliteration, img, audioUrl, onReplay, onShowHint, hintShown }) {
  switch (mode) {
    case 'hearing':
      return (
        <div className="text-center">
          <span className="sr-only">Listen and think of the Hebrew, then flip to check</span>
          <button onClick={(e) => { e.stopPropagation(); onReplay?.() }}
            aria-label={audioUrl ? 'Replay pronunciation audio' : 'Play pronunciation audio'}
            className="touch-target px-4 py-2 min-h-[44px] rounded-lg bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-sm text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors">
            ▶ {audioUrl ? 'Replay' : 'Loading… tap to play'}
          </button>
          {/* Optional peek at the written word: it IS the answer, so it is
              gated behind an explicit hint tap — autoplaying audio is the
              graded retrieval stimulus, the text is the fallback. */}
          {!hintShown ? (
            <div>
              <button onClick={(e) => { e.stopPropagation(); onShowHint?.() }}
                className="mt-3 text-xs text-neutral-400 hover:text-indigo-500 transition-colors cursor-pointer"
                aria-label="Show written word as a hint">
                Show word
              </button>
            </div>
          ) : (
            <div className="mt-3 text-3xl font-serif leading-relaxed text-neutral-500 dark:text-neutral-400 font-hebrew-biblical"
              dir="rtl" lang="he" aria-label={`Written hint: ${hebrew}`}>
              {hebrew}
            </div>
          )}
        </div>
      )
    case 'reverse':
      return (
        <div className="text-center">
          <span className="sr-only">English shown — think of the Hebrew, then flip to check</span>
          <div className="text-3xl font-semibold text-neutral-800 dark:text-neutral-200">
            {gloss}
          </div>
        </div>
      )
    case 'forward':
      return (
        <div className="text-center">
          <span className="sr-only">Hebrew shown — think of the English, then flip to check</span>
          {/* Sound accompanies the written stimulus: the retrieval work is
              meaning from form, and either channel counts as the prompt —
              hearing the word cannot leak the English answer. Same rule as
              the back face (audio via onReplay, which no-ops when absent). */}
          <button onClick={(e) => { e.stopPropagation(); onReplay?.() }}
            aria-label={audioUrl ? 'Replay pronunciation audio' : 'Play pronunciation audio'}
            className="mb-3 px-4 py-2 min-h-[44px] rounded-lg bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-sm text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors">
            ▶ {audioUrl ? 'Replay' : 'Play'}
          </button>
          <div className="text-4xl font-serif leading-relaxed text-neutral-800 dark:text-neutral-200 font-hebrew-biblical"
            dir="rtl" lang="he">
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
          <span className="sr-only">Picture shown — think of the Hebrew, then flip to check</span>
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

/**
 * CardBack — the answer face: writing + audio replay + gloss (+ image).
 * Rule 2: the back always carries the full answer, whatever the front was.
 *
 * Props: hebrew, gloss, transliteration, img, audioUrl, intervals,
 * onReplay (prefetched replay — free for cached audio, silent when absent),
 * onRate (rating 1-4), onSuspend (wholeWord: boolean).
 */
export function CardBack({ hebrew, gloss, transliteration, img, audioUrl, intervals, onReplay, onRate, onSuspend }) {
  return (
    <div className="space-y-4">
      {/* Answer display */}
      <div className="text-center">
        <div className="text-3xl font-serif leading-relaxed text-neutral-800 dark:text-neutral-200 font-hebrew-biblical"
          dir="rtl" lang="he">
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

      {/* Audio replay on the back (hear the answer, link sound to meaning) */}
      {/* Reverse keeps audio here only: sound on the front would BE the answer. */}
      {(audioUrl || onReplay) && (
        <div className="text-center">
          <button onClick={(e) => { e.stopPropagation(); audioUrl ? playUrl(audioUrl) : onReplay?.() }}
            aria-label="Play pronunciation audio"
            className="touch-target px-4 py-2 min-h-[44px] rounded-lg bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-sm text-neutral-700 dark:text-neutral-300 cursor-pointer transition-colors">
            🔊 {audioUrl ? 'Replay audio' : 'Play audio'}
          </button>
        </div>
      )}

      {/* Rating buttons */}
      <RatingButtons intervals={intervals} onRate={(v) => onRate?.(v)} variant="grid" showKeys />
      {/* B2: suspend controls */}
      <div className="flex items-center justify-center gap-3 pt-1">
        <button onClick={() => onSuspend?.(false)}
          className="text-[11px] text-neutral-400 hover:text-amber-500 transition-colors">
          🚫 Suspend this direction
        </button>
        <button onClick={() => onSuspend?.(true)}
          className="text-[11px] text-neutral-400 hover:text-amber-500 transition-colors">
          suspend whole word
        </button>
      </div>
    </div>
  )
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
      // Deal through resolveDealModes: server due_modes pass through
      // modesForCard untouched, then each direction is repaired against
      // what can actually render (imageless picture -> forward, etc.) so
      // no card ever draws a blank face. Cards with nothing renderable
      // (no hebrew AND no gloss) are dropped — rating them would poison
      // the FSRS schedule with noise.
      const withModes = resolveDealModes(initialCards, cache)
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
  // Hearing-mode hint: the written word is the answer, so it stays hidden
  // behind an explicit "Show word" tap (per card — reset on every advance).
  const [hintShown, setHintShown] = useState(false)
  const [ratings, setRatings] = useState({})
  const [saveFailed, setSaveFailed] = useState(0)
  const [audioUrl, setAudioUrl] = useState(null)
  const [lastRated, setLastRated] = useState(null)
  const [undoMsg, setUndoMsg] = useState('')
  const [suspendedUndo, setSuspendedUndo] = useState(null)
  const redealsRef = useRef({})
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

  // On-arrival audio prefetch: the prompt AND the answer both speak now —
  // forward prompts read the Hebrew aloud, hearing auto-plays (below),
  // reverse fronts deliberately stay silent (sound would be the answer).
  // Known-missing audio resolves to null here (fetched once, then free).
  useEffect(() => {
    if (!currentCard?.hebrew) return
    if (!['forward', 'hearing', 'picture', 'drill'].includes(currentCard.mode)) return
    let cancelled = false
    fetchAudioUrl(currentCard.hebrew).then(url => {
      if (cancelled || !url) return
      setAudioUrl(prev => prev || url)
    })
    return () => { cancelled = true }
  }, [currentCard?.id])

  // Auto-play audio for hearing mode when card is shown (pooled: cached URL + shared element).
  // Known-missing audio converts the trial to forward (same repair rule as
  // deal time): a silent hearing card is a blank stimulus, and rating it
  // would schedule noise. The due hearing rep stays due server-side.
  useEffect(() => {
    if (!currentCard || flipped) return
    if (currentCard.mode === 'hearing' && currentCard.hebrew) {
      let cancelled = false
      fetchAudioUrl(currentCard.hebrew).then(url => {
        if (cancelled) return
        if (!url) {
          const fixed = repairMode('hearing', {
            hebrew: currentCard.hebrew, gloss: currentCard.gloss,
            hasPicture: !!imageCache[currentCard.hebrew], hasAudio: false,
          })
          if (fixed && fixed !== 'hearing') {
            const newId = `${currentCard.id}~${fixed}`
            setCards(prev => (prev || []).map(c =>
              c.id === currentCard.id ? { ...c, mode: fixed, id: newId } : c))
          }
          return
        }
        setAudioUrl(url)
        playUrl(url)
      })
      return () => { cancelled = true }
    }
  }, [currentCard?.id, flipped])

  const replayAudio = useCallback(() => {
    if (!currentCard?.hebrew) return
    fetchAudioUrl(currentCard.hebrew).then(url => {
      if (!url) return
      setAudioUrl(url)
      playUrl(url)
    })
  }, [currentCard?.hebrew])

  const handleFlip = useCallback(() => {
    if (!flipped) setFlipped(true)
  }, [flipped])

  // B2 suspend undo — suspension hides the card with no other way back
  // from this screen, so offer one tap to restore it.
  const handleUnsuspend = useCallback(async () => {
    if (!suspendedUndo) return
    try {
      const sessionToken = currentSessionToken()
      await fetchJSON('/hebrew/unsuspend', {
        method: 'POST',
        body: JSON.stringify({
          node_id: suspendedUndo.node_id, card_mode: suspendedUndo.mode,
          hebrew: suspendedUndo.hebrew || '', lemma: suspendedUndo.lemma || '',
          user_id: await hebrewSessionUser(), session_token: sessionToken,
        }),
        headers: {
          'Content-Type': 'application/json',
          ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
        },
      })
      setUndoMsg('Suspended card restored to your queue.')
    } catch {
      setUndoMsg('Could not unsuspend — it stays hidden for now.')
    }
    setSuspendedUndo(null)
  }, [suspendedUndo])

  const handleRate = useCallback(async (rating) => {
    if (!currentCard || !flipped) return
    setRatings(prev => ({ ...prev, [currentCard.id]: rating }))
    // Submit rating to FSRS
    try {
      await hebrewSessionUser()
      const sessionToken = currentSessionToken()
      const res = await fetchJSON('/hebrew/fsrs/review', {
        method: 'POST',
        body: JSON.stringify({
          node_id: currentCard.node_id, rating, user_id: await hebrewSessionUser(),
          hebrew: currentCard.hebrew || '', lemma: currentCard.lemma || '',
          session_token: sessionToken, card_mode: currentCard.mode,
        }),
        headers: {
          'Content-Type': 'application/json',
          ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
        },
      })
      // Intraday relearn: the card pops back up a few cards later
      // (learn-ahead collapse), capped per card so a hard card can't loop.
      if (res.ok && res.data?.is_relearn) {
        const mins = res.data.relearn_in_min || 10
        const dealt = redealsRef.current[currentCard.id] || 0
        if (dealt < MAX_REDEALS_PER_CARD) {
          redealsRef.current[currentCard.id] = dealt + 1
          setCards(prev => {
            if (!prev) return prev
            const pos = prev.findIndex(c => c.id === currentCard.id)
            const at = relearnInsertAt(pos >= 0 ? pos : currentIdx, prev.length)
            return [...prev.slice(0, at), { ...currentCard }, ...prev.slice(at)]
          })
        }
        setUndoMsg(`Back in ~${mins} min — it'll resurface in a few cards.`)
      }
      setLastRated({
        node_id: currentCard.node_id, mode: currentCard.mode,
        hebrew: currentCard.hebrew || '', lemma: currentCard.lemma || '',
      })
      if (!(res.ok && res.data?.is_relearn)) setUndoMsg('')
    } catch (_) { setSaveFailed(n => n + 1) }
    // Advance
    setFlipped(false)
    setHintShown(false)
    setAudioUrl(null)
    setCurrentIdx(i => i + 1)
  }, [currentCard, flipped])

  // B2: single-step undo — restores the prior schedule+mastery row, then
  // steps back so the learner can re-rate the same card.
  const handleUndo = useCallback(async () => {
    if (!lastRated) return
    try {
      const sessionToken = currentSessionToken()
      const r = await fetchJSON('/hebrew/fsrs/undo', {
        method: 'POST',
        body: JSON.stringify({
          node_id: lastRated.node_id, card_mode: lastRated.mode,
          hebrew: lastRated.hebrew || '', lemma: lastRated.lemma || '',
          user_id: await hebrewSessionUser(), session_token: sessionToken,
        }),
        headers: {
          'Content-Type': 'application/json',
          ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
        },
      })
      if (!r.ok) throw new Error(r.error || 'undo failed')
      // Drop the undone rating and step back to that card.
      setRatings(prev => {
        const next = { ...prev }
        delete next[`${lastRated.node_id || lastRated.hebrew}_${lastRated.mode}`]
        return next
      })
      setCurrentIdx(i => Math.max(0, i - 1))
      setFlipped(false)
      setHintShown(false)
      setLastRated(null)
      setUndoMsg('Undone — card restored, rate it again.')
    } catch (_) {
      setUndoMsg('Undo failed — schedule kept the last rating.')
    }
  }, [lastRated])

  // B2: suspend this direction (card stays out of queues until unsuspended).
  const handleSuspend = useCallback(async (wholeNode = false) => {
    if (!currentCard) return
    try {
      const sessionToken = currentSessionToken()
      await fetchJSON('/hebrew/suspend', {
        method: 'POST',
        body: JSON.stringify({
          node_id: currentCard.node_id, card_mode: wholeNode ? '' : currentCard.mode,
          hebrew: currentCard.hebrew || '', lemma: currentCard.lemma || '',
          user_id: await hebrewSessionUser(), session_token: sessionToken,
        }),
        headers: {
          'Content-Type': 'application/json',
          ...(sessionToken ? { Authorization: `Bearer ${sessionToken}` } : {}),
        },
      })
      setLastRated(null)
      setSuspendedUndo({
        node_id: currentCard.node_id, mode: wholeNode ? '' : currentCard.mode,
        hebrew: currentCard.hebrew || '', lemma: currentCard.lemma || '',
      })
      setUndoMsg(wholeNode ? 'Suspended whole word — it will no longer appear.' : 'Suspended this direction — it will no longer appear.')
      setFlipped(false)
      setHintShown(false)
      setAudioUrl(null)
      setCurrentIdx(i => i + 1)
    } catch (_) { setSaveFailed(n => n + 1) }
  }, [currentCard])

  // Keyboard shortcuts (Ctrl/Cmd+Z = undo last rating — button works too).
  useEffect(() => {
    function handleKey(e) {
      if (onBack && e.key === 'Escape') { onBack(); return }
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        handleUndo()
        return
      }
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
  }, [flipped, handleFlip, handleRate, handleUndo, onBack])

  // Loading state while the two-pass build prefetches pictures + deals modes
  if (!cards) {
    return (
      <div className="max-w-lg mx-auto px-6 py-12 text-center" role="status" aria-live="polite">
        <div className="animate-pulse space-y-4" aria-hidden="true">
          <div className="h-6 w-32 mx-auto rounded bg-neutral-200 dark:bg-neutral-700" />
          <div className="h-40 rounded-xl bg-neutral-100 dark:bg-neutral-800" />
          <div className="h-4 w-48 mx-auto rounded bg-neutral-200 dark:bg-neutral-700" />
        </div>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-4">
          Loading cards…
        </p>
      </div>
    )
  }

  // Empty state: never leave a blank review (audit skill: icon + message + CTA).
  if (cards.length === 0) {
    return (
      <div className="max-w-lg mx-auto px-6 py-12 text-center">
        <div className="text-4xl mb-3" aria-hidden="true">📭</div>
        <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200 mb-1">No cards due</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-5">Nothing to review right now — new cards appear as lessons unlock or reviews come due.</p>
        {onBack ? (
          <button onClick={onBack} className="px-5 py-2.5 min-h-[44px] rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">← Back to lessons</button>
        ) : onComplete ? (
          <button onClick={onComplete} className="px-5 py-2.5 min-h-[44px] rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">Done</button>
        ) : null}
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

  const frontContent = () => (
    <CardFront mode={mode} hebrew={hebrew} gloss={gloss} transliteration={transliteration}
      img={img} audioUrl={audioUrl} onReplay={replayAudio}
      onShowHint={() => setHintShown(true)} hintShown={hintShown} />
  )

  const backContent = () => (
    <CardBack hebrew={hebrew} gloss={gloss} transliteration={transliteration}
      img={img} audioUrl={audioUrl} intervals={intervals}
      onReplay={replayAudio}
      onRate={handleRate} onSuspend={(whole) => handleSuspend(whole)} />
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
          {lastRated && (
            <button onClick={handleUndo}
              title="Undo last rating (Ctrl+Z)"
              className="text-xs text-indigo-500 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors px-2 py-1 rounded hover:bg-indigo-50 dark:hover:bg-indigo-950">
              ↩ Undo
            </button>
          )}
        </div>
        <span className="text-xs text-neutral-400 font-mono">
          {currentIdx + 1}/{totalCards}
        </span>
      </div>
      {(undoMsg || suspendedUndo) && (
        <p role="status" aria-live="polite" className="text-xs text-center mb-2 text-neutral-500 dark:text-neutral-400">{undoMsg}
          {suspendedUndo && (
            <button onClick={handleUnsuspend}
              className="ml-2 text-indigo-500 hover:text-indigo-700 dark:hover:text-indigo-300 underline cursor-pointer">
              ↩ Undo suspend
            </button>
          )}
        </p>
      )}

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-indigo-500 rounded-full transition-all duration-300"
          style={{ width: `${((currentIdx) / totalCards) * 100}%` }}
        />
      </div>

      {/* Card */}
      <div
        role="button" tabIndex={0} aria-label={flipped ? 'Answer shown. Rate this card 1 to 4.' : 'Flashcard. Activate to reveal the answer.'}
        onKeyDown={(e) => { if (!flipped && (e.key === ' ' || e.key === 'Enter')) { e.preventDefault(); handleFlip() } }}
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
