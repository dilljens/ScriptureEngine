import React, { useState, useEffect, useCallback } from 'react'
import HebrewKeyboard from './HebrewKeyboard'
import { currentSessionToken, hebrewSessionUser } from '../api'

/**
 * VerseDictation — R3-verse opt-in (see scripts/seed_verse_dictation.py).
 *
 * Gloss cue + FULL-VERSE audio; type the word you hear. No Hebrew text
 * anywhere on the front — the ears do the segmenting, not the eyes.
 * Grading is the same skeleton match as every other card (/hebrew/progress),
 * so FSRS, history, and stats all work with zero new backend.
 *
 * The server gates serving on 80% word-level dictation retention unless
 * the learner explicitly opts in (unlock=1) — this component IS the
 * opt-in, so it always passes unlock=1 and shows the retention readout
 * the server returns.
 */
export default function VerseDictation({ onBack, onOpenLesson }) {
  const [cards, setCards] = useState(null)
  const [gate, setGate] = useState({ word_retention: null, gated: false })
  const [idx, setIdx] = useState(0)
  const [answer, setAnswer] = useState('')
  const [showKeyboard, setShowKeyboard] = useState(false)
  const [result, setResult] = useState(null) // null | {correct, correctAnswer, explanation}
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(0)
  const [correct, setCorrect] = useState(0)

  const load = useCallback(async (withUnlock = true) => {
    try {
      const uid = await hebrewSessionUser()
      const uq = uid && uid !== 'default' ? `?user_id=${encodeURIComponent(uid)}&` : '?'
      const token = currentSessionToken()
      const r = await fetch(`/api/v1/hebrew/verse-dictation/next${uq}limit=8${withUnlock ? '&unlock=1' : ''}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      const d = await r.json()
      if (d.ok) {
        setCards(d.data.cards || [])
        setGate({ word_retention: d.data.word_retention, gated: d.data.gated })
      }
    } catch {}
  }, [])

  useEffect(() => { load() }, [load]);

  const current = cards?.[idx]

  const submit = async () => {
    if (!current || !answer.trim() || submitting) return
    setSubmitting(true)
    try {
      const token = currentSessionToken()
      const r = await fetch('/api/v1/hebrew/progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          node_id: current.node_id, question_id: current.question_id,
          answer: answer.trim(), user_id: await hebrewSessionUser(), session_token: token,
        }),
      })
      const d = await r.json()
      const ok = !!(d.ok && d.data?.is_correct)
      setResult({ correct: ok, correctAnswer: d.data?.correct_answer, explanation: d.data?.explanation })
      setDone(n => n + 1)
      if (ok) setCorrect(n => n + 1)
    } catch {
      setResult({ correct: null, correctAnswer: '', explanation: 'Could not verify — check connection.' })
    } finally {
      setSubmitting(false)
    }
  }

  const next = () => {
    setAnswer('')
    setResult(null)
    setShowKeyboard(false)
    setIdx(i => i + 1)
  }

  if (!cards) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        <p className="text-sm text-neutral-500 dark:text-neutral-400 animate-pulse">Loading verse dictation…</p>
      </div>
    )
  }

  if (cards.length === 0) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        <div className="text-4xl mb-4">🎧</div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">No verse dictation ready</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
          {gate.gated
            ? `Word-level dictation is at ${Math.round((gate.word_retention ?? 0) * 100)}% — verse level unlocks at 80%. Keep practicing words first.`
            : 'No verse cards are due right now — check back after more reviews.'}
        </p>
        {onBack && (
          <button onClick={onBack}
            className="px-6 py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-sm font-medium cursor-pointer">← Back</button>
        )}
      </div>
    )
  }

  if (idx >= cards.length) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        <div className="text-4xl mb-4">🎧</div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Round complete</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">{correct} / {done} segmented correctly</p>
        <div className="flex gap-3 justify-center">
          <button onClick={onBack}
            className="px-6 py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 text-sm font-medium cursor-pointer">← Back</button>
          <button onClick={() => { setIdx(0); setDone(0); setCorrect(0); load() }}
            className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer">🔁 More</button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">🎧 Verse dictation</h2>
        {onBack && (
          <button onClick={onBack}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Room
          </button>
        )}
      </div>
      <p className="text-[11px] text-neutral-400 mb-3 text-center">
        {typeof gate.word_retention === 'number'
          ? `Word-level dictation: ${Math.round(gate.word_retention * 100)}% — ${gate.gated ? 'verse level unlocks at 80%' : 'verse level unlocked'}`
          : 'Answer from the full-verse audio — no text hints.'}
      </p>

      <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
        <div className="text-xs text-neutral-500 dark:text-neutral-400 mb-1">Which word means “{current.gloss || '…'}”?</div>
        {current.audio_url
          ? <audio key={current.question_id} controls preload="auto" src={current.audio_url} className="w-full h-9 my-2" />
          : <p className="text-xs text-amber-600 my-2">No audio for this verse.</p>}
        {!result ? (
          <>
            <input value={answer} autoFocus
              onChange={e => setAnswer(e.target.value)}
              onFocus={() => setShowKeyboard(true)}
              onKeyDown={e => { if (e.key === 'Enter') submit() }}
              placeholder="Type what you hear (Hebrew)…"
              dir="auto" disabled={submitting}
              className="w-full px-4 py-3 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-800 dark:text-neutral-100 text-sm outline-none focus:border-indigo-400 font-hebrew-biblical" />
            {showKeyboard && (
              <div className="mt-2">
                <HebrewKeyboard onCharClick={(c) => setAnswer(a => a + c)}
                  onBackspace={() => setAnswer(a => a.slice(0, -1))}
                  onClear={() => setAnswer('')} value={answer} />
                <button onClick={() => setShowKeyboard(false)}
                  className="mt-1 text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">
                  Hide keyboard
                </button>
              </div>
            )}
            <button onClick={submit} disabled={!answer.trim() || submitting}
              className="mt-3 w-full py-2.5 rounded-xl text-sm font-medium bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white cursor-pointer transition-colors">
              {submitting ? 'Checking…' : 'Check'}
            </button>
          </>
        ) : (
          <div className={`p-4 rounded-lg ${result.correct === true
            ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
            : result.correct === false
              ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
              : 'bg-neutral-50 dark:bg-neutral-900/20 border border-neutral-200 dark:border-neutral-800'}`}>
            <p className="text-sm font-medium">
              {result.correct === true ? '✓ Correct — you segmented it from real speech.'
                : result.correct === false ? '✗ Not quite — replay the verse and listen again.' : 'Unable to verify'}
            </p>
            {result.correct === false && result.correctAnswer && (
              <p className="text-xs text-neutral-600 dark:text-neutral-300 mt-1">
                The word was <span className="font-semibold text-green-700 dark:text-green-400 font-hebrew-biblical" dir="rtl">{result.correctAnswer}</span>
              </p>
            )}
            {result.explanation && (
              <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{result.explanation}</p>
            )}
            <button onClick={next}
              className="mt-3 w-full py-2.5 rounded-xl text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer transition-colors">
              {idx + 1 >= cards.length ? 'See results' : 'Next verse →'}
            </button>
          </div>
        )}
      </div>
      <p className="text-[11px] text-neutral-400 text-center mt-3">{done} answered · card {Math.min(idx + 1, cards.length)}/{cards.length}</p>
    </div>
  )
}
