import React from 'react'
import { listPublishedStudies } from '../api'

/**
 * Studies list view — shows all published studies, each tappable to open.
 */
export default function StudiesListView({ onOpenStudy }) {
  const [studies, setStudies] = React.useState(null)
  const [error, setError] = React.useState(null)

  React.useEffect(() => {
    listPublishedStudies().then(r => {
      if (r.ok) setStudies(r.data)
      else setError(r.error || 'Failed to load')
    }).catch(e => setError(e.message))
  }, [])

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-4">
      <h2 className="text-lg font-bold text-neutral-800 dark:text-neutral-100">📖 Published Studies</h2>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {!studies && !error && <p className="text-sm text-neutral-400 animate-pulse">Loading studies...</p>}
      {studies && studies.length === 0 && <p className="text-sm text-neutral-400">No published studies yet.</p>}
      {studies && studies.map(s => (
        <button key={s.slug || s.id} onClick={() => onOpenStudy(s.slug, s.title)}
          className="w-full text-left p-4 rounded-xl bg-white dark:bg-neutral-800 shadow-sm border border-neutral-200 dark:border-neutral-700 hover:border-indigo-300 dark:hover:border-indigo-600 transition-colors cursor-pointer space-y-1">
          <div className="font-medium text-sm text-neutral-800 dark:text-neutral-100">{s.title}</div>
          {s.description && <div className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2">{s.description}</div>}
          {s.author?.name && <div className="text-[10px] text-neutral-400 dark:text-neutral-500">by {s.author.name}</div>}
        </button>
      ))}
    </div>
  )
}
