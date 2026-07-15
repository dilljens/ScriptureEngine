import React from 'react'
import { useTabs } from '../tabContext'

export const WORK_LABEL = {
  'ot': 'Old Testament', 'nt': 'New Testament', 'bom': 'Book of Mormon',
  'dc': 'Doctrine & Covenants', 'pgp': 'Pearl of Great Price',
  'dss': 'Dead Sea Scrolls', 'apoc': 'Apocrypha',
  'pseu': 'Pseudepigrapha', 'expanded': 'Expanded Canon',
}

const workCardColors = {
  'ot': { bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800', hover: 'hover:bg-amber-100 dark:hover:bg-amber-900/30', badge: 'bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300', icon: '📜' },
  'nt': { bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-200 dark:border-blue-800', hover: 'hover:bg-blue-100 dark:hover:bg-blue-900/30', badge: 'bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300', icon: '✝️' },
  'bom': { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-200 dark:border-green-800', hover: 'hover:bg-green-100 dark:hover:bg-green-900/30', badge: 'bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300', icon: '📖' },
  'dc': { bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-200 dark:border-purple-800', hover: 'hover:bg-purple-100 dark:hover:bg-purple-900/30', badge: 'bg-purple-100 dark:bg-purple-800 text-purple-700 dark:text-purple-300', icon: '⚡' },
  'pgp': { bg: 'bg-pink-50 dark:bg-pink-900/20', border: 'border-pink-200 dark:border-pink-800', hover: 'hover:bg-pink-100 dark:hover:bg-pink-900/30', badge: 'bg-pink-100 dark:bg-pink-800 text-pink-700 dark:text-pink-300', icon: '💎' },
  'dss': { bg: 'bg-yellow-50 dark:bg-yellow-900/20', border: 'border-yellow-200 dark:border-yellow-800', hover: 'hover:bg-yellow-100 dark:hover:bg-yellow-900/30', badge: 'bg-yellow-100 dark:bg-yellow-800 text-yellow-700 dark:text-yellow-300', icon: '🏺' },
  'apoc': { bg: 'bg-rose-50 dark:bg-rose-900/20', border: 'border-rose-200 dark:border-rose-800', hover: 'hover:bg-rose-100 dark:hover:bg-rose-900/30', badge: 'bg-rose-100 dark:bg-rose-800 text-rose-700 dark:text-rose-300', icon: '📚' },
  'pseu': { bg: 'bg-indigo-50 dark:bg-indigo-900/20', border: 'border-indigo-200 dark:border-indigo-800', hover: 'hover:bg-indigo-100 dark:hover:bg-indigo-900/30', badge: 'bg-indigo-100 dark:bg-indigo-800 text-indigo-700 dark:text-indigo-300', icon: '🔮' },
  'expanded': { bg: 'bg-teal-50 dark:bg-teal-900/20', border: 'border-teal-200 dark:border-teal-800', hover: 'hover:bg-teal-100 dark:hover:bg-teal-900/30', badge: 'bg-teal-100 dark:bg-teal-800 text-teal-700 dark:text-teal-300', icon: '⛪' },
}

export default function LibraryView({ bookData, onNavigate, bookError, onRetry }) {
  const { goToWork: ctxGoToWork, goToBook, currentTab, viewRef } = useTabs()
  const works = bookData?.works || []
  const focusedWorkId = viewRef || works[0]?.id || null

  // Error state with retry
  if (bookError) {
    return (
      <div className="max-w-lg mx-auto px-6 py-12 text-center">
        <div className="text-4xl mb-4">⚠️</div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Couldn't load library</h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">{bookError}</p>
        <button onClick={onRetry}
          className="px-4 py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium transition-colors">
          Retry
        </button>
      </div>
    )
  }

  // Works where "books" are really chapters/sections (single-chapter books).
  // D&C: 138 sections, each stored as a 1-chapter "book" — skip book list.
  const FLAT_WORKS = new Set(['dc'])

  const goToWork = (workId) => {
    const w = works.find(wi => wi.id === workId)
    if (!w) return
    if (FLAT_WORKS.has(workId) && w.books?.[0]) {
      // Jump straight to the first section/chapter
      goToBook(currentTab?.id, w.books[0].id, w.title || workId)
    } else {
      // Show book list (WorkView) — pass first book ID so breadcrumb works
      ctxGoToWork(currentTab?.id, w.id, w.title || w.id, w.books?.[0]?.id)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-6">Library</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {works.map((w) => {
          const colors = workCardColors[w.id] || { bg: 'bg-neutral-50 dark:bg-neutral-800', border: 'border-neutral-200 dark:border-neutral-700', hover: 'hover:bg-neutral-100 dark:hover:bg-neutral-700/50', badge: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400', icon: '📚' }
          const isFocused = w.id === focusedWorkId
          return (
            <button key={w.id} onClick={() => goToWork(w.id)}
              className={`flex flex-col gap-2 p-5 rounded-xl border-2 transition-all cursor-pointer text-left
                ${isFocused
                  ? `${colors.bg} ${colors.border} shadow-md -translate-y-0.5 ring-2 ring-blue-400 dark:ring-blue-500`
                  : `${colors.bg} border-neutral-200 dark:border-neutral-700 ${colors.hover} hover:shadow-md hover:-translate-y-0.5`
                } active:translate-y-0`}>
              <div className="flex items-center gap-2">
                <span className="text-xl">{colors.icon}</span>
                <h3 className="text-base font-semibold text-neutral-800 dark:text-neutral-200">{w.title}</h3>
              </div>
              {w.subtitle && <p className="text-xs text-neutral-500 dark:text-neutral-400">{w.subtitle}</p>}
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${colors.badge}`}>
                  {w.books?.length || 0} books
                </span>
                {w.id && <span className="text-[9px] text-neutral-400 dark:text-neutral-500">{WORK_LABEL[w.id] || w.id}</span>}
              </div>
              {isFocused && <span className="text-[10px] text-blue-600 dark:text-blue-400 font-medium mt-1">Press Enter or click to browse →</span>}
            </button>
          )
        })}
      </div>
      {works.length === 0 && !bookError && (
        <div className="text-center py-12">
          <div className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">Loading library...</p>
        </div>
      )}
      <p className="text-[10px] text-neutral-400 dark:text-neutral-500 text-center mt-6">
        ← → navigate works · ↑↓ zoom in/out · Enter to open
      </p>
    </div>
  )
}
