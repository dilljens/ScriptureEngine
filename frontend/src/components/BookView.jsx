import React, { useState, useEffect, useRef } from 'react'
import { useTabs } from '../tabContext'

const CHAPTER_COUNTS = {
  gen:50, exo:40, lev:27, num:36, deu:34, josh:24, judg:21, ruth:4,
  '1sam':31, '2sam':24, '1kgs':22, '2kgs':25, '1chr':29, '2chr':36,
  ezra:10, neh:13, esth:10, job:42, psa:150, prov:31, eccl:12, song:8,
  isa:66, jer:52, lam:5, ezek:48, dan:12, hos:14, joel:3, amos:9,
  obad:1, jonah:4, mic:7, nah:3, hab:3, zeph:3, hag:2, zech:14, mal:4,
  matt:28, mark:16, luke:24, john:21, acts:28, rom:16, '1cor':16,
  '2cor':13, gal:6, eph:6, phil:4, col:4, '1thes':5, '2thes':3,
  '1tim':6, '2tim':4, titus:3, philem:1, heb:13, james:5, '1pet':5,
  '2pet':3, '1john':5, '2john':1, '3john':1, jude:1, rev:22,
  '1ne':22, '2ne':33, jacob:7, enos:1, jarom:1, omni:1, wom:1,
  mosiah:29, alma:63, hel:16, '3ne':30, '4ne':1, morm:9, ether:15, moro:10,
  moses:8, abraham:5, jsm:1, jsh:1, aoff:1,
}

function getMaxChapter(bookId) {
  if (bookId?.startsWith('dc')) return 1
  return CHAPTER_COUNTS[bookId] || 50
}

export default function BookView({ bookId }) {
  const { goToChapter, currentTab } = useTabs()
  const [search, setSearch] = useState('')
  const inputRef = useRef(null)
  let bookInfo = null

  // Auto-focus input when entering BookView
  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 100)
  }, [bookId])

  // Also route any number key to the input when not focused
  useEffect(() => {
    const handler = (e) => {
      if (e.target === inputRef.current) return
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      if (e.key >= '0' && e.key <= '9') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  if (window.__bookData?.works) {
    for (const w of window.__bookData.works) {
      bookInfo = w.books.find(b => b.id === bookId)
      if (bookInfo) break
    }
  }
  const maxCh = getMaxChapter(bookId)
  const chapters = Array.from({ length: maxCh }, (_, i) => i + 1)
  const filtered = search ? chapters.filter(ch => String(ch).startsWith(search)) : chapters

  const go = (s) => {
    const n = parseInt(s, 10)
    if (n >= 1 && n <= maxCh) { goToChapter(currentTab?.id, bookId, n); setSearch('') }
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{bookInfo?.title || bookId}</h2>
        <input ref={inputRef} type="text" value={search}
          onChange={e => setSearch(e.target.value.replace(/[^0-9]/g, ''))}
          onKeyDown={e => {
            if (e.key === 'Enter' && search) { go(search) }
            if (e.key === 'Escape') { setSearch(''); inputRef.current?.blur() }
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown') {
              inputRef.current?.blur()
            }
          }}
          className="w-24 px-2 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
          placeholder="chapter #" />
      </div>
      {search && <p className="text-sm text-blue-600 dark:text-blue-400 mb-3">Jump to chapter: <strong>{search}</strong> <kbd className="text-[10px] font-mono bg-blue-100 dark:bg-blue-900/50 px-1 rounded ml-1">Enter</kbd></p>}
      <div className="grid grid-cols-8 sm:grid-cols-10 md:grid-cols-12 lg:grid-cols-15 gap-1.5">
        {filtered.map(ch => <button key={ch} onClick={() => goToChapter(currentTab?.id, bookId, ch)}
          className={`px-2 py-1.5 rounded text-xs font-mono text-center transition-all cursor-pointer ${search && String(ch).startsWith(search) ? 'bg-blue-100 dark:bg-blue-900/50 border-blue-400 text-blue-700 dark:text-blue-300 border-2 shadow-sm' : 'text-neutral-600 dark:text-neutral-400 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300'}`}>{ch}</button>)}
      </div>
    </div>
  )
}
