import React, { useState, useEffect, useCallback } from 'react'

/**
 * ScrollView — verse-unit feed tab (replaces Learn in nav).
 *
 * v0 stub: tries the ranked feed API (GET /api/v1/feed, Track C1) and falls
 * back to the verse-of-day card until the ranking engine lands. Vote buttons
 * POST to /api/v1/feed/interact when the endpoint exists (best-effort).
 * Sort tabs mirror the planned scorers 1:1 (hot/top/new/controversial/best).
 */

const SORTS = [
  { id: 'hot', label: 'Hot' },
  { id: 'top', label: 'Top' },
  { id: 'new', label: 'New' },
  { id: 'controversial', label: 'Controversial' },
  { id: 'best', label: 'Best' },
]

function navigateToVerseId(verseId) {
  const p = String(verseId || '').split('.')
  if (p.length >= 2) {
    window.dispatchEvent(new CustomEvent('scripture-navigate', {
      detail: {
        book: p[0], chapter: parseInt(p[1]) || 1,
        verse: p.length >= 3 ? parseInt(p[2]) || undefined : undefined,
      },
    }))
  }
}

function UnitCard({ unit, onVote }) {
  const verses = unit.verses || (unit.verse_id ? [unit] : [])
  const title = unit.span_ref || unit.reference || unit.verse_id || ''
  return (
    <article className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 shadow-sm">
      <div className="flex gap-3">
        {/* Vote column — wires into Hot/Wilson inputs (Track A) */}
        <div className="flex flex-col items-center gap-0.5 shrink-0 pt-0.5">
          <button onClick={() => onVote(unit, 'up')} aria-label="Upvote"
            className="w-7 h-7 grid place-items-center rounded text-neutral-400 hover:text-orange-500 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer transition-colors">▲</button>
          <span className="text-[10px] font-mono text-neutral-400">{unit.score_display ?? ''}</span>
          <button onClick={() => onVote(unit, 'down')} aria-label="Downvote"
            className="w-7 h-7 grid place-items-center rounded text-neutral-400 hover:text-indigo-500 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer transition-colors">▼</button>
        </div>
        <div className="flex-1 min-w-0">
          {verses.map((v, i) => (
            <div key={v.verse_id || i} className={i > 0 ? 'mt-2 pt-2 border-t border-neutral-100 dark:border-neutral-700/60' : ''}>
              <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">{v.text_english}</p>
            </div>
          ))}
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <button onClick={() => navigateToVerseId(verses[0]?.verse_id)}
              className="text-xs font-mono text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">{title}</button>
            {unit.canon_status && unit.canon_status !== 'canon' && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                {unit.canon_status} · {unit.work || ''}
              </span>
            )}
            {unit.unit_reason && (
              <span className="text-[10px] text-neutral-400 dark:text-neutral-500" title={unit.why_grouped || ''}>
                {unit.unit_reason === 'complete_thought' ? '· single verse' : `· ${verses.length} verses grouped: ${unit.unit_reason.replace(/_/g, ' ')}`}
              </span>
            )}
          </div>
          {unit.reflection_prompt && (
            <p className="mt-2 text-xs italic text-neutral-500 dark:text-neutral-400">💭 {unit.reflection_prompt}</p>
          )}
          <div className="mt-2 flex items-center gap-3 text-[11px] text-neutral-400 dark:text-neutral-500">
            <button onClick={() => onVote(unit, 'save')} className="hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">🔖 Save</button>
            <button onClick={() => onVote(unit, 'share')} className="hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">↗ Share</button>
            <span>💬 {unit.comment_count ?? 0}</span>
          </div>
        </div>
      </div>
    </article>
  )
}

export default function ScrollView() {
  const [sort, setSort] = useState('hot')
  const [units, setUnits] = useState([])
  const [cursor, setCursor] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [feedLive, setFeedLive] = useState(false)

  const load = useCallback(async (sortId, nextCursor, append) => {
    if (append) setLoadingMore(true); else setLoading(true)
    try {
      const url = `/api/v1/feed?limit=10&sort=${sortId}` + (nextCursor ? `&cursor=${encodeURIComponent(nextCursor)}` : '')
      const r = await fetch(url)
      const d = await r.json()
      if (d.ok && Array.isArray(d.data?.units)) {
        setFeedLive(true)
        setUnits(prev => append ? [...prev, ...d.data.units] : d.data.units)
        setCursor(d.data.next_cursor || null)
        return
      }
      throw new Error('feed unavailable')
    } catch {
      // Fallback until Track C1 lands: verse-of-day as a single unit.
      setFeedLive(false)
      if (!append) {
        try {
          const r = await fetch('/api/v1/verse-of-day')
          const d = await r.json()
          if (d.ok && d.data) {
            const v = d.data
            setUnits([{
              verse_id: v.verse_id, span_ref: v.reference || v.verse_id,
              verses: [{ verse_id: v.verse_id, text_english: v.text_english }],
              unit_reason: 'complete_thought', comment_count: 0,
            }])
          }
        } catch { /* offline — empty state below */ }
      }
    } finally {
      setLoading(false); setLoadingMore(false)
    }
  }, [])

  useEffect(() => { setCursor(null); setUnits([]); load(sort, null, false) }, [sort, load])

  const onVote = useCallback(async (unit, action) => {
    const id = unit.verse_id || unit.unit_id || unit.verses?.[0]?.verse_id
    if (!id) return
    if (action === 'share') {
      const text = `${unit.span_ref || id}\n${unit.verses?.[0]?.text_english || ''}`
      try {
        if (navigator.share) await navigator.share({ text })
        else await navigator.clipboard.writeText(text)
      } catch { /* dismissed */ }
      return
    }
    // Best-effort until /api/v1/feed/interact exists.
    try {
      await fetch('/api/v1/feed/interact', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verse_id: id, action }),
      })
    } catch { /* endpoint not yet built — vote is local-only */ }
  }, [])

  return (
    <div className="max-w-2xl mx-auto px-4 py-4">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">📜 Scroll</h2>
        {!feedLive && (
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-400 border border-neutral-200 dark:border-neutral-700">
            daily verse preview — ranked feed lands with the feed engine
          </span>
        )}
      </div>
      {/* Sort tabs = planned scorers (hot/top/new/controversial/best) */}
      <div className="flex gap-1.5 mb-4 overflow-x-auto">
        {SORTS.map(s => (
          <button key={s.id} onClick={() => setSort(s.id)}
            className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-colors border ${
              sort === s.id
                ? 'bg-neutral-900 dark:bg-neutral-100 text-white dark:text-neutral-900 border-transparent'
                : 'bg-white dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700 hover:border-neutral-300'
            }`}>
            {s.label}
          </button>
        ))}
      </div>
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <div key={i} className="h-32 rounded-xl bg-neutral-100 dark:bg-neutral-800 animate-pulse" />)}
        </div>
      ) : units.length === 0 ? (
        <p className="text-sm text-neutral-400 text-center py-10">Nothing here yet — check your connection and try again.</p>
      ) : (
        <div className="space-y-3">
          {units.map((u, i) => <UnitCard key={u.unit_id || u.verse_id || i} unit={u} onVote={onVote} />)}
          {cursor && (
            <button onClick={() => load(sort, cursor, true)} disabled={loadingMore}
              className="w-full py-2.5 rounded-xl bg-neutral-100 dark:bg-neutral-800 text-sm text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
              {loadingMore ? 'Loading…' : 'More'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
