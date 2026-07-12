import React, { useEffect, useState } from 'react'
import MemorizeQueue from './MemorizeQueue'
import CardQueue from './CardQueue'

/**
 * MemorizeView — spaced repetition verse memorization.
 * Now uses the generic CardQueue for the review interface.
 */
export default function MemorizeView() {
  const [view, setView] = useState('queue') // queue | review
  const [reviewData, setReviewData] = useState([])
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
        // Map backend reviews to generic card format
        const cards = (d.data.reviews || []).map(item => ({
          id: item.queue_id || item.verse_id,
          type: 'verse',
          queue_id: item.queue_id,
          data: {
            reference: item.verse_id,
            text: item.text,
            book: item.verse_id?.split('.')[0],
            chapter: parseInt(item.verse_id?.split('.')[1]) || 1,
            verse: parseInt(item.verse_id?.split('.')[2]) || 1,
          },
        }))
        setReviewData(cards)
        setView('review')
      }
    } catch {}
  }

  const handleRate = async (card, rating) => {
    if (card.queue_id) {
      await fetch(`/api/v1/memorize/review/${card.queue_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating }),
      })
    }
  }

  const handleComplete = () => {
    setView('queue')
    loadStats()
  }

  useEffect(() => { loadStats() }, [])

  if (view === 'review') {
    return (
      <CardQueue
        cards={reviewData}
        onRate={handleRate}
        onComplete={handleComplete}
        title="Verse Review"
        emptyMessage="No verses due for review."
      />
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
