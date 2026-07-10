import React, { useEffect, useState } from 'react'
import MemorizeQueue from './MemorizeQueue'

/**
 * MemorizeView — spaced repetition verse memorization.
 * Uses Python backend (web/routes/memorize.py) with FSRS-5 scheduling.
 */
export default function MemorizeView() {
  const [view, setView] = useState('queue') // queue | review
  const [reviewData, setReviewData] = useState([])
  const [reviewIdx, setReviewIdx] = useState(0)
  const [rating, setRating] = useState(null)
  const [stats, setStats] = useState({ total: 0, mastered: 0, learning: 0 })

  const loadStats = async () => {
    try {
      const r = await fetch('/api/v1/memorize/queue')
      const d = await r.json()
      if (d.ok) {
        const verses = d.data.verses || []
        setStats({
          total: verses.length,
          mastered: verses.filter(v => (v.mastery || 0) >= 0.8).length,
          learning: verses.filter(v => (v.mastery || 0) > 0 && (v.mastery || 0) < 0.8).length,
        })
      }
    } catch {}
  }

  const startReview = async () => {
    try {
      const r = await fetch('/api/v1/memorize/review?limit=10')
      const d = await r.json()
      if (d.ok) {
        setReviewData(d.data.reviews || [])
        setReviewIdx(0)
        setRating(null)
        setView('review')
      }
    } catch {}
  }

  const submitRating = async (r) => {
    if (!reviewData[reviewIdx]) return
    try {
      await fetch(`/api/v1/memorize/review/${reviewData[reviewIdx].queue_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: r }),
      })
    } catch {}
    setRating(r)
    setTimeout(() => {
      if (reviewIdx + 1 < reviewData.length) {
        setReviewIdx(p => p + 1)
        setRating(null)
      } else {
        setView('queue')
        loadStats()
      }
    }, 1000)
  }

  useEffect(() => { loadStats() }, [])

  if (view === 'review' && reviewData.length > 0) {
    const item = reviewData[reviewIdx]
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="flex items-center justify-between mb-4">
          <button onClick={() => setView('queue')} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">← Queue</button>
          <span className="text-[10px] text-neutral-400">{reviewIdx + 1}/{reviewData.length}</span>
        </div>
        <div className="p-6 rounded-xl bg-white dark:bg-neutral-800 border-2 border-indigo-200 dark:border-indigo-800 text-center">
          <p className="text-[10px] font-mono text-indigo-400 mb-2">{item.verse_id}</p>
          <p className="text-base leading-relaxed text-neutral-800 dark:text-neutral-200 mb-6 italic">"{item.text}"</p>
          <div className="flex gap-2 justify-center">
            {rating === null ? (
              <>
                {[
                  { val: 1, label: 'Again', color: 'bg-red-500 hover:bg-red-600' },
                  { val: 2, label: 'Hard', color: 'bg-amber-500 hover:bg-amber-600' },
                  { val: 3, label: 'Good', color: 'bg-green-500 hover:bg-green-600' },
                  { val: 4, label: 'Easy', color: 'bg-blue-500 hover:bg-blue-600' },
                ].map(b => (
                  <button key={b.val} onClick={() => submitRating(b.val)}
                    className={`px-4 py-2 rounded-lg text-white text-sm font-medium cursor-pointer transition-colors ${b.color}`}>
                    {b.label}
                  </button>
                ))}
              </>
            ) : (
              <p className="text-sm text-green-600 font-medium">✓ Recorded</p>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <MemorizeQueue onStartReview={startReview} />
      {stats.total > 0 && (
        <div className="max-w-2xl mx-auto px-4 pb-4">
          <div className="flex items-center gap-3 text-[10px] text-neutral-400">
            <span>{stats.total} verses</span>
            <span>{stats.mastered} mastered</span>
            <span>{stats.learning} learning</span>
          </div>
        </div>
      )}
    </div>
  )
}
