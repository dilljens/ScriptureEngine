import React, { useState, useEffect, useCallback } from 'react'
import GameReviewModal from './GameReviewModal'
import { currentSessionToken, hebrewSessionUser } from '../api'

/**
 * HebrewRoom — one study session, composed (R4b).
 *
 * The daily-session endpoint composes due reviews (all modes interleaved),
 * new cards to the daily cap, and one authentic verse block: the verse most
 * represented among the due items. This view renders the verse block with
 * read-along audio and runs practice through the existing quiz modal —
 * no new scheduler, no new grading path (rule 7 holds everywhere).
 */
export default function HebrewRoom({ onBack, onOpenLesson }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [reviewTarget, setReviewTarget] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const uid = await hebrewSessionUser()
      const uq = uid && uid !== 'default' ? `?user_id=${encodeURIComponent(uid)}` : ''
      const token = currentSessionToken()
      const r = await fetch(`/api/v1/hebrew/daily-session?limit=20${uq}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      const d = await r.json()
      if (d.ok) setSession(d.data)
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-12 text-center">
        <p className="text-sm text-neutral-500 dark:text-neutral-400 animate-pulse">Composing today's session…</p>
      </div>
    )
  }

  const vb = session?.verse_block
  const newOnes = (session?.reviews || []).filter(r => r.is_new || r.scheduler === 'new')
  const firstNew = newOnes.find(r => r.node_id)?.node_id
    || (session?.verse_block?.node_ids || [])[0]

  return (
    <div className="max-w-2xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">🏠 Today's Room</h2>
        {onBack && (
          <button onClick={onBack}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Curriculum
          </button>
        )}
      </div>

      {/* Authentic block: the verse your due words live in */}
      {vb?.text_hebrew && (
        <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 mb-3">
          <div className="text-[10px] uppercase tracking-wider text-neutral-400 mb-1">
            📖 Read where your words live — {vb.verse_ref}
          </div>
          <p className="text-lg leading-loose font-serif text-neutral-800 dark:text-neutral-100 mb-1"
            style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL',serif" }} dir="rtl">
            {vb.text_hebrew}
          </p>
          {vb.text_english && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 italic mb-2">“{vb.text_english}”</p>
          )}
          {vb.audio_url && (
            <audio controls preload="none" src={vb.audio_url} className="w-full h-9" />
          )}
        </div>
      )}

      {/* Session actions */}
      <div className="grid gap-2 mb-3">
        <button onClick={() => setReviewTarget('due')}
          className="px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors text-left">
          🔁 Review due ({session?.due_count ?? 0}) — interleaved, all modes
        </button>
        {firstNew && (
          <button onClick={() => setReviewTarget(firstNew)}
            className="px-4 py-3 rounded-xl bg-white dark:bg-neutral-800 border border-indigo-200 dark:border-indigo-800 hover:border-indigo-400 text-indigo-700 dark:text-indigo-300 text-sm font-medium cursor-pointer transition-colors text-left">
            ✨ New words ({session?.new_cards_available ?? 0} today) — start with {(session?.reviews || []).find(r => r.node_id === firstNew)?.title || firstNew}
          </button>
        )}
      </div>
      <p className="text-[11px] text-neutral-400 text-center">
        Again returns in minutes, not tomorrow. Suspend anything annoying — it stays out.
      </p>

      {reviewTarget && (
        <GameReviewModal
          nodeId={reviewTarget === 'due' ? null : reviewTarget}
          title={reviewTarget === 'due' ? 'Due review (interleaved)' : 'New words'}
          onClose={() => setReviewTarget(null)}
          onFinished={() => { setReviewTarget(null); load() }}
        />
      )}
    </div>
  )
}
