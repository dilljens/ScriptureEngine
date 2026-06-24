import React, { useState, useEffect, useRef } from 'react'
import { useTabs } from '../tabContext'

export default function WorkView({ workId }) {
  const { goToBook, currentTab } = useTabs()
  const [search, setSearch] = useState('')
  const [sel, setSel] = useState(0)
  const inputRef = useRef(null)

  let workInfo = null
  let books = []
  if (window.__bookData?.works) {
    for (const w of window.__bookData.works) {
      if (w.id === workId) { workInfo = w; books = w.books; break }
    }
  }
  const filtered = search
    ? books.filter(b => b.id.toLowerCase().includes(search.toLowerCase()) || b.title.toLowerCase().includes(search.toLowerCase()))
    : books

  useEffect(() => { setSel(0) }, [search])

  const go = (b) => { goToBook(currentTab?.id, b.id, b.title); setSearch('') }

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{workInfo?.title || workId}</h2>
        <input ref={inputRef} type="text" value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && filtered[sel]) { go(filtered[sel]) }
            if (e.key === 'ArrowUp') { e.preventDefault(); setSel(i => Math.max(0, i - 1)) }
            if (e.key === 'ArrowDown') { e.preventDefault(); setSel(i => Math.min(filtered.length - 1, i + 1)) }
            if (e.key === 'Escape') { setSearch(''); inputRef.current?.blur() }
          }}
          className="w-48 px-2 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
          placeholder="filter books..." />
      </div>
      {filtered.length === 0 && <p className="text-sm text-neutral-500 dark:text-neutral-400">No books match "{search}"</p>}
      <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
        {filtered.map((b, i) => (
          <button key={b.id} onClick={() => go(b)}
            className={`text-left px-4 py-3 rounded-lg border transition-all cursor-pointer ${i === sel ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-400 dark:border-blue-600 shadow-sm' : 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300'}`}>
            <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{b.title}</span>
            <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono ml-2">{b.id}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
