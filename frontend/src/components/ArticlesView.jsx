import React, { useEffect, useState } from 'react'

/**
 * ArticlesView — the hand-written, in-depth essays, kept separate from the
 * auto-generated wiki entity stubs (Adam, Moses, …). Those entities are ~700
 * chars of generated summary; these are substantive pieces (11k–52k chars).
 * Mixing them made the real work impossible to find.
 *
 * Reads article_type='doctrine' from /api/v1/wiki/browse/doctrine and opens the
 * full essay in the wiki viewer.
 */
export default function ArticlesView({ onOpenArticle }) {
  const [articles, setArticles] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/api/v1/wiki/browse/doctrine')
      .then(r => r.json())
      .then(d => { if (!cancelled) { if (d.ok) setArticles(d.data.articles || []); else setError('Could not load essays') } })
      .catch(e => { if (!cancelled) setError(e.message) })
    return () => { cancelled = true }
  }, [])

  const readingTime = (len) => {
    const words = Math.round((len || 0) / 6)
    const mins = Math.max(1, Math.round(words / 220))
    return mins >= 60 ? `${(mins / 60).toFixed(1)} hr` : `${mins} min`
  }

  if (error) return (
    <div className="max-w-3xl mx-auto px-4 py-10 text-sm text-neutral-500 dark:text-neutral-400">{error}</div>
  )
  if (!articles) return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <div className="animate-pulse space-y-3">
        {[1, 2, 3].map(i => <div key={i} className="h-20 rounded-xl bg-neutral-100 dark:bg-neutral-800" />)}
      </div>
    </div>
  )
  if (articles.length === 0) return (
    <div className="max-w-3xl mx-auto px-4 py-10 text-sm text-neutral-500 dark:text-neutral-400">
      No essays yet.
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto px-4 py-6">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📜 Essays</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          In-depth studies — written and cross-referenced, not auto-generated summaries.
        </p>
      </div>

      <div className="grid gap-3">
        {articles.map(a => (
          <button key={a.id} onClick={() => onOpenArticle?.(a.id, a.title)}
            className="w-full text-left p-4 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm transition-all cursor-pointer min-h-[44px]">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{a.title}</h3>
                {a.summary && (
                  <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">{a.summary}…</p>
                )}
              </div>
              <span className="shrink-0 text-[10px] px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                {readingTime(a.length)}
              </span>
            </div>
          </button>
        ))}
      </div>

      <p className="mt-5 text-[11px] text-neutral-400 dark:text-neutral-500">
        Looking for a person or place? Those are the shorter wiki entries — open 📖 Wiki from the menu.
      </p>
    </div>
  )
}
