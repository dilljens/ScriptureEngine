import { useState, useCallback, createContext, useContext, useEffect, useRef } from 'react'

export const TOGGLE_DEFS = [
  { key: 'footnotes', label: 'Footnotes (LDS Notes)', icon: 'ᵃ', group: 'annotations' },
  { key: 'gematria', label: 'Gematria', icon: '🔢', group: 'annotations' },
  { key: 'lemma', label: 'Lexicon', icon: 'λ', group: 'annotations' },
  { key: 'synonymous', label: 'Synonymous', icon: '≡', group: 'parallelism' },
  { key: 'antithetic', label: 'Antithetic', icon: '⇄', group: 'parallelism' },
  { key: 'synthetic', label: 'Synthetic', icon: '→', group: 'parallelism' },
  { key: 'staircase', label: 'Staircase', icon: '⊻', group: 'parallelism' },
  { key: 'chiasmus', label: 'Chiasmus', icon: '⟷', group: 'parallelism' },
  { key: 'tsk', label: 'TSK Cross-refs', icon: 'ᵗ', group: 'intertextual' },
  { key: 'direct', label: 'Direct Quotes', icon: '📖', group: 'intertextual' },
  { key: 'allusion', label: 'Allusions', icon: '🔗', group: 'intertextual' },
  { key: 'echo', label: 'Echoes', icon: '💬', group: 'intertextual' },
  { key: 'times', label: 'Times', icon: '📅', group: 'reference' },
  { key: 'places', label: 'Places', icon: '🌍', group: 'reference' },
  { key: 'isaiah', label: 'Isaiah Patterns', icon: '🔍', group: 'reference' },
]

const GROUPS = [
  { key: 'annotations', label: 'Annotations' },
  { key: 'parallelism', label: 'Parallelism' },
  { key: 'intertextual', label: 'Intertextual' },
  { key: 'reference', label: 'Reference' },
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

/* ── Pill toggle switch (iOS-style) ── */
function PillToggle({ on, onClick }) {
  return (
    <button type="button" onClick={onClick}
      className={`relative w-9 h-5 rounded-full p-0.5 transition-colors cursor-pointer shrink-0 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-offset-1 dark:focus:ring-offset-neutral-900 ${
        on ? 'bg-blue-500' : 'bg-neutral-300 dark:bg-neutral-600'
      }`}
      aria-checked={on} role="switch">
      <span className={`block w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-150 ${on ? 'translate-x-4' : 'translate-x-0'}`} />
    </button>
  )
}

/* ── Toggle row (label + pill) ── */
function ToggleRow({ def, on, onToggle }) {
  return (
    <div onClick={onToggle} role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}
      className="flex items-center justify-between py-1.5 px-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer group"
      aria-label={def.label}>
      <span className="text-xs text-neutral-700 dark:text-neutral-300 group-hover:text-neutral-900 dark:group-hover:text-neutral-100">{def.label}</span>
      <PillToggle on={on} onClick={onToggle} />
    </div>
  )
}

/* ── Layers popover ── */
export function LayersPopover({ open, onClose, poetryMode, setPoetryMode, buttonRef }) {
  const { toggles, dispatch } = useToggles()
  const popoverRef = useRef(null)

  // Click outside + Escape
  useEffect(() => {
    if (!open) return
    function handleKey(e) { if (e.key === 'Escape') onClose() }
    function handleClick(e) {
      if (popoverRef.current && !popoverRef.current.contains(e.target) &&
          buttonRef?.current && !buttonRef.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('keydown', handleKey)
    document.addEventListener('mousedown', handleClick)
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.removeEventListener('mousedown', handleClick)
    }
  }, [open, onClose, buttonRef])

  if (!open) return null

  const allOn = Object.values(toggles).every(v => v)

  return (
    <div ref={popoverRef}
      className="absolute top-full right-0 mt-1 w-72 bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-xl shadow-xl z-50 animate-scale-in origin-top-right overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1.5">
        <span className="text-xs font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider">Layers</span>
        <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer p-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-700">
          <svg width={14} height={14} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </button>
      </div>

      {/* Groups */}
      <div className="px-3 pb-2 max-h-[360px] overflow-y-auto">
        {GROUPS.map((g) => {
          const groupDefs = TOGGLE_DEFS.filter(t => t.group === g.key)
          return (
            <div key={g.key} className="mb-1">
              <div className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider px-1 py-1.5">{g.label}</div>
              {groupDefs.map(t => (
                <ToggleRow key={t.key} def={t} on={toggles[t.key]} onToggle={() => dispatch(t.key)} />
              ))}
            </div>
          )
        })}

        {/* Divider */}
        <div className="border-t border-neutral-200 dark:border-neutral-700 my-2" />

        {/* View Mode */}
        <div className="px-1 py-1.5">
          <div className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1.5">View Mode</div>
          <div className="flex gap-1.5">
            <button onClick={() => setPoetryMode(true)}
              className={`flex-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                poetryMode
                  ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                  : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 border border-transparent hover:bg-neutral-200 dark:hover:bg-neutral-600'
              }`}>Poetry</button>
            <button onClick={() => setPoetryMode(false)}
              className={`flex-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                !poetryMode
                  ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                  : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 border border-transparent hover:bg-neutral-200 dark:hover:bg-neutral-600'
              }`}>Narrative</button>
          </div>
        </div>

        {/* All On / All Off */}
        <div className="flex gap-2 pt-1 pb-1.5">
          <button onClick={() => { if (!allOn) dispatch('all') }}
            className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              allOn
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 border border-transparent hover:bg-neutral-200 dark:hover:bg-neutral-600'
            }`}>All On</button>
          <button onClick={() => { if (allOn) dispatch('all') }}
            className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer ${
              !allOn
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800'
                : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 border border-transparent hover:bg-neutral-200 dark:hover:bg-neutral-600'
            }`}>All Off</button>
        </div>
      </div>
    </div>
  )
}

/* ── Legacy bar (kept for backward compat, no longer used by default) ── */
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

/* ── Legacy Poetry Toggle (kept for backward compat) ── */
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
