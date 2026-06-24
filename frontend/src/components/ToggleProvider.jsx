import React, { useState, useCallback, createContext, useContext } from 'react'

export const TOGGLE_DEFS = [
  { key: 'footnotes', label: 'LDS Notes', icon: 'ᵃ' },
  { key: 'gematria', label: 'Gematria', icon: '🔢' },
  { key: 'lemma', label: 'Lexicon', icon: 'λ' },
  { key: 'synonymous', label: 'Synonymous', icon: '≡' },
  { key: 'antithetic', label: 'Antithetic', icon: '⇄' },
  { key: 'synthetic', label: 'Synthetic', icon: '→' },
  { key: 'staircase', label: 'Staircase', icon: '⊻' },
  { key: 'chiasmus', label: 'Chiasmus', icon: '⟷' },
  { key: 'tsk', label: 'TSK', icon: 'ᵗ' },
  { key: 'direct', label: 'Direct', icon: '📖' },
  { key: 'allusion', label: 'Allusion', icon: '🔗' },
  { key: 'echo', label: 'Echo', icon: '💬' },
  { key: 'times', label: 'Times', icon: '📅' },
  { key: 'places', label: 'Places', icon: '🌍' },
  { key: 'isaiah', label: 'Isaiah', icon: '🔍' },
]

const ToggleCtx = createContext()
export function useToggles() { return useContext(ToggleCtx) }

export function ToggleProvider({ children }) {
  const [toggles, st] = useState({
    footnotes: true, gematria: false, lemma: false,
    synonymous: false, antithetic: false, synthetic: false, staircase: false, chiasmus: false,
    tsk: false,
    direct: false, allusion: false, echo: false,
    times: false, places: false, isaiah: false,
  })
  const dispatch = useCallback((k) => {
    if (k === 'all') {
      const on = Object.values(toggles).every(v => v)
      st(Object.fromEntries(TOGGLE_DEFS.map(t => [t.key, !on])))
    } else st(p => ({ ...p, [k]: !p[k] }))
  }, [toggles])
  return <ToggleCtx.Provider value={{ toggles, dispatch }}>{children}</ToggleCtx.Provider>
}

export function ToggleBar() {
  const { toggles, dispatch } = useToggles()
  return (
    <div className="flex flex-wrap gap-2 items-center px-4 py-2 bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800">
      {TOGGLE_DEFS.map(t => (
        <button key={t.key} onClick={() => dispatch(t.key)}
          className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all cursor-pointer select-none
            ${toggles[t.key] ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 border-blue-300 dark:border-blue-700 shadow-sm' : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-700'}`}>
          <span className="mr-1">{t.icon}</span>{t.label}
        </button>
      ))}
      <button onClick={() => dispatch('all')}
        className="ml-auto px-3 py-1.5 rounded-full text-sm font-medium border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-all cursor-pointer select-none">
        {Object.values(toggles).every(v => v) ? 'All Off' : 'All On'}
      </button>
    </div>
  )
}

export function PoetryToggle({ poetryMode, setPoetryMode }) {
  return (
    <div className="flex items-center gap-2 px-4 py-1.5 bg-neutral-50 dark:bg-neutral-900/50 border-b border-neutral-200 dark:border-neutral-800">
      <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">View:</span>
      <button onClick={() => setPoetryMode(true)}
        className={`px-2.5 py-1 rounded text-xs font-medium transition-all cursor-pointer ${poetryMode ? 'bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 border border-neutral-300 dark:border-neutral-600 shadow-sm' : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300'}`}>Poetry</button>
      <button onClick={() => setPoetryMode(false)}
        className={`px-2.5 py-1 rounded text-xs font-medium transition-all cursor-pointer ${!poetryMode ? 'bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 border border-neutral-300 dark:border-neutral-600 shadow-sm' : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300'}`}>Narrative</button>
    </div>
  )
}
