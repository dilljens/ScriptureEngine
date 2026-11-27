import React, { useState, useEffect, useCallback, useRef } from 'react'
import HebrewKeyboard from './HebrewKeyboard'
import { currentSessionToken, hebrewSessionUser, fetchJSON } from '../api'

/**
 * TutorTurn — grounded Socratic tutor conversation (T1).
 *
 * Server-validated turn shapes only: ask (question, no answer) → learner
 * types → correct (recast + rule + citation, graded server-side) → next.
 * Explain turns carry citations; uncited text can only ask. Every correction
 * lands in the attempt log, so FSRS sees tutoring like any quiz.
 */
const CITATION_LABEL = { node_id: 'lesson', verse_ref: 'verse' }

function Citations({ cites, onOpenLesson }) {
  if (!cites?.length) return null
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {cites.map((c, i) => {
        const label = c.node_id || c.verse_ref || 'source'
        return (
          <button key={i}
            onClick={() => c.node_id && onOpenLesson?.(c.node_id)}
            title={`${CITATION_LABEL[Object.keys(c).find(k => k === 'node_id' || k === 'verse_ref')] || 'source'}: ${label}`}
            className={`text-[10px] px-2 py-0.5 rounded-full border cursor-pointer transition-colors ${
              c.node_id
                ? 'bg-indigo-50 dark:bg-indigo-900/30 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 hover:border-indigo-400'
                : 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
            }`}>
            📖 {label}
          </button>
        )
      })}
    </div>
  )
}

export default function TutorTurn({ onClose, onOpenLesson }) {
  const [turns, setTurns] = useState([])
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [showKeyboard, setShowKeyboard] = useState(false)
  const bottomRef = useRef(null)

  const callTurn = useCallback(async (payload) => {
    setBusy(true)
    setError(null)
    try {
      await hebrewSessionUser()
      const token = currentSessionToken()
      const r = await fetchJSON('/hebrew/tutor/turn', {
        method: 'POST',
        body: JSON.stringify({ user_id: await hebrewSessionUser(), session_token: token, ...payload }),
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      })
      if (!r.ok) throw new Error(r.error || 'tutor turn failed')
      setTurns(prev => [...prev, r.data]);
      return r.data
    } catch (e) {
      setError(e.message || 'tutor turn failed');
      return null
    } finally {
      setBusy(false)
    }
  }, []);

  // Open with a production ask picked from the weakest material.
  // Guarded: StrictMode double-invokes effects in dev (two identical
  // asks), and a remount must not spend a second question.
  const openedRef = useRef(false)
  useEffect(() => {
    if (openedRef.current) return
    openedRef.current = true
    callTurn({ mode: 'ask' })
  }, [callTurn])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [turns])

  const currentAsk = [...turns].reverse().find(t => t.kind === 'ask' && !t.answered)

  const submitAnswer = async () => {
    if (!currentAsk || !answer.trim() || busy) return
    const askIdx = turns.lastIndexOf(currentAsk)
    setTurns(prev => prev.map((t, i) => i === askIdx ? { ...t, answered: true } : t))
    setAnswer('')
    setShowKeyboard(false)
    await callTurn({
      mode: 'correct',
      node_id: currentAsk.node_id,
      question_id: currentAsk.question_id,
      answer: answer.trim(),
    })
  }

  const askExplain = async () => {
    const last = [...turns].reverse().find(t => t.node_id)
    if (!last?.node_id || busy) return
    await callTurn({ mode: 'explain', node_id: last.node_id })
  }

  const finish = async () => {
    await callTurn({ mode: 'done' })
  }

  return (
    <div className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm flex items-start sm:items-center justify-center p-2 sm:p-4 overflow-y-auto"
      role="dialog" aria-modal="true" aria-label="Tutor conversation"
      onClick={onClose}>
      <div
        className="w-full max-w-2xl bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl my-2 sm:my-6 overflow-hidden flex flex-col max-h-[92dvh]"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">
              💬 Tutor — you produce, I correct
            </div>
            <div className="text-[11px] text-neutral-500 dark:text-neutral-400 truncate">
              Grounded in your lessons · corrections count toward review
            </div>
          </div>
          <button onClick={onClose} aria-label="Close tutor"
            className="min-h-[44px] min-w-[44px] rounded-lg border border-neutral-200 dark:border-neutral-700 text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 cursor-pointer shrink-0">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {turns.map((t, i) => (
            <div key={i}>
              {t.kind === 'ask' && (
                <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800">
                  <div className="text-[10px] uppercase tracking-wider text-indigo-500 mb-1">Your turn — answer from memory</div>
                  <div className="text-sm text-neutral-800 dark:text-neutral-100 whitespace-pre-wrap">{t.question}</div>
                  {t.prompt && <div className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1">{t.prompt}</div>}
                  {t.verse_ref && <div className="text-[11px] text-neutral-400 mt-1">📖 {t.verse_ref}</div>}
                </div>
              )}
              {t.kind === 'correct' && (
                <div className={`p-3 rounded-xl border ${t.was_correct
                  ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                  : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'}`}>
                  <div className="text-sm font-medium text-neutral-800 dark:text-neutral-100">{t.recast}</div>
                  <div className="text-xs text-neutral-600 dark:text-neutral-300 mt-1">{t.rule}</div>
                  {t.correct_answer && !t.was_correct && (
                    <div className="text-xs mt-1">Answer: <span className="font-semibold text-green-700 dark:text-green-400">{t.correct_answer}</span></div>
                  )}
                  {t.explanation && !t.was_correct && (
                    <div className="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{t.explanation}</div>
                  )}
                  <Citations cites={t.citations} onOpenLesson={onOpenLesson} />
                </div>
              )}
              {t.kind === 'explain' && (
                <div className="p-3 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
                  <div className="text-sm text-neutral-700 dark:text-neutral-200 leading-relaxed whitespace-pre-wrap">{t.text}</div>
                  <Citations cites={t.citations} onOpenLesson={onOpenLesson} />
                </div>
              )}
              {t.kind === 'done' && (
                <div className="p-3 rounded-xl bg-neutral-50 dark:bg-neutral-900/40 border border-neutral-200 dark:border-neutral-700 text-center">
                  <div className="text-sm text-neutral-600 dark:text-neutral-300">{t.summary}</div>
                  {typeof t.due_now === 'number' && (
                    <div className="text-[11px] text-neutral-400 mt-1">{t.due_now} due now · {t.goal ? `goal: ${t.goal}` : 'no goal set'}</div>
                  )}
                </div>
              )}
            </div>
          ))}
          {busy && (
            <div className="text-xs text-neutral-400 animate-pulse">Tutor is thinking…</div>
          )}
          {error && (
            <div className="text-xs text-red-600 dark:text-red-400 text-center">{error}</div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 shrink-0">
          {currentAsk ? (
            <div className="flex gap-2">
              <input value={answer} autoFocus
                onChange={e => setAnswer(e.target.value)}
                onFocus={() => setShowKeyboard(true)}
                onKeyDown={e => { if (e.key === 'Enter') submitAnswer() }}
                placeholder="Type your answer in Hebrew…"
                dir="auto" disabled={busy}
                className="flex-1 px-3 py-2.5 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-indigo-400 font-hebrew-biblical" />
              <button onClick={submitAnswer} disabled={busy || !answer.trim()}
                className="px-4 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium cursor-pointer">
                →
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <button onClick={() => callTurn({ mode: 'ask' })} disabled={busy}
                className="flex-1 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium cursor-pointer">
                Next question →
              </button>
              <button onClick={askExplain} disabled={busy}
                className="px-4 rounded-lg border border-neutral-200 dark:border-neutral-700 text-sm text-neutral-600 dark:text-neutral-300 cursor-pointer hover:border-indigo-300">
                Explain
              </button>
              <button onClick={finish} disabled={busy}
                className="px-4 rounded-lg border border-neutral-200 dark:border-neutral-700 text-sm text-neutral-600 dark:text-neutral-300 cursor-pointer hover:border-indigo-300">
                Done
              </button>
            </div>
          )}
          {showKeyboard && currentAsk && (
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
        </div>
      </div>
    </div>
  )
}
