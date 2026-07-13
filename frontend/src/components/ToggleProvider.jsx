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

  // Search scope — which works and layers the LLM should use
  const [searchWorks, setSearchWorks] = useState({
    ot: true, nt: true, bom: true, dc: true, pgp: true,
    dss: true, apoc: true, pseu: true, expanded: true,
  })
  const [searchLayers, setSearchLayers] = useState({
    linguistic: true, intertextual: true, structural: true, interpretive: true,
    sod: true, symbolic: true, chronological: true, numerical: true,
    geographic: true, textual: true, frequency: true,
  })
  const [searchLang, setSearchLang] = useState('all') // 'all' | 'english' | 'hebrew' | 'greek'

  // Bible version for LLM references
  const [bibleVersion, setBibleVersion] = useState('LSV') // 'LSV' | 'WEB' | 'KJV'

  // Tool categories the LLM is allowed to use
  const [enabledTools, setEnabledTools] = useState({
    lookup: true, search: true, connections: true, graph: true,
    gematria: true, study: true, staging: false,
  })

  // Display language — which language to show verses in
  const [displayLang, setDisplayLang] = useState('english') // 'english' | 'hebrew' | 'greek'
  const [showTranslit, setShowTranslit] = useState(true)
  const [showEnglish, setShowEnglish] = useState(true)

  return <ToggleCtx.Provider value={{ toggles, dispatch, searchWorks, setSearchWorks, searchLayers, setSearchLayers, searchLang, setSearchLang, bibleVersion, setBibleVersion, enabledTools, setEnabledTools, displayLang, setDisplayLang, showTranslit, setShowTranslit, showEnglish, setShowEnglish }}>{children}</ToggleCtx.Provider>
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
  const { toggles, dispatch, searchWorks, setSearchWorks, searchLayers, setSearchLayers, searchLang, setSearchLang, displayLang, setDisplayLang, showTranslit, setShowTranslit, showEnglish, setShowEnglish, bibleVersion, setBibleVersion, enabledTools, setEnabledTools } = useToggles()
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

        {/* Display Language */}
        <div className="px-1 py-1.5">
          <div className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1.5">Display Language</div>
          <div className="flex gap-1">
            {[
              { id: 'english', label: 'English' },
              { id: 'hebrew', label: 'Hebrew' },
              { id: 'greek', label: 'Greek' },
            ].map(lang => (
              <button key={lang.id} onClick={() => setDisplayLang(lang.id)}
                className={`flex-1 px-2 py-1 rounded text-[10px] font-medium transition-all cursor-pointer ${
                  displayLang === lang.id
                    ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                    : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 border border-transparent hover:bg-neutral-200 dark:hover:bg-neutral-600'
                }`}>
                {lang.label}
              </button>
            ))}
          </div>
          {displayLang !== 'english' && (
            <div className="flex flex-col gap-1 mt-1.5 px-0.5">
              <label className="flex items-center gap-2 cursor-pointer text-[11px] text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
                onClick={() => setShowTranslit(!showTranslit)}>
                <div className={`w-6 h-3.5 rounded-full p-0.5 transition-colors ${showTranslit ? 'bg-blue-500' : 'bg-neutral-300 dark:bg-neutral-600'}`}>
                  <div className={`w-2.5 h-2.5 rounded-full bg-white shadow-sm transition-transform ${showTranslit ? 'translate-x-3' : 'translate-x-0'}`} />
                </div>
                Show transliteration
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-[11px] text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
                onClick={() => setShowEnglish(!showEnglish)}>
                <div className={`w-6 h-3.5 rounded-full p-0.5 transition-colors ${showEnglish ? 'bg-blue-500' : 'bg-neutral-300 dark:bg-neutral-600'}`}>
                  <div className={`w-2.5 h-2.5 rounded-full bg-white shadow-sm transition-transform ${showEnglish ? 'translate-x-3' : 'translate-x-0'}`} />
                </div>
                Show English
              </label>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="border-t border-neutral-200 dark:border-neutral-700 my-2" />

        {/* Search Scope — collapsible */}
        <details className="group px-1 pb-1">
          <summary className="text-[10px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider py-1.5 cursor-pointer hover:text-neutral-600 dark:hover:text-neutral-300 list-none flex items-center gap-1 select-none">
            <span className="transition-transform group-open:rotate-90 text-[8px]">▶</span>
            Search Scope
          </summary>
          <div className="pl-2">
            {/* Works */}
            <div className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 mb-1">Works</div>
            <ScopeRow label="Old Testament" id="ot" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="New Testament" id="nt" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="Book of Mormon" id="bom" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="Doctrine &amp; Covenants" id="dc" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="Pearl of Great Price" id="pgp" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="Dead Sea Scrolls" id="dss" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="Apocrypha" id="apoc" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="Pseudepigrapha" id="pseu" value={searchWorks} setter={setSearchWorks} />
            <ScopeRow label="Expanded Canon" id="expanded" value={searchWorks} setter={setSearchWorks} />

            {/* Language */}
            <div className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 mt-2 mb-1">Language</div>
            <div className="flex gap-1 mb-2">
              {[
                { id: 'all', label: 'All' },
                { id: 'english', label: 'English' },
                { id: 'hebrew', label: 'Hebrew' },
                { id: 'greek', label: 'Greek' },
              ].map(lang => (
                <button key={lang.id} onClick={() => setSearchLang(lang.id)}
                  className={`flex-1 px-1.5 py-1 rounded text-[10px] font-medium transition-all cursor-pointer ${
                    searchLang === lang.id
                      ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700'
                      : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-500 dark:text-neutral-400 border border-transparent hover:bg-neutral-200 dark:hover:bg-neutral-600'
                  }`}>
                  {lang.label}
                </button>
              ))}
            </div>

            {/* Bible Version */}
            <div className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 mt-2 mb-1">Bible Version</div>
            <select value={bibleVersion} onChange={e => setBibleVersion(e.target.value)}
              className="w-full px-1.5 py-1 rounded border border-neutral-300 dark:border-neutral-600 text-[10px] bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 cursor-pointer mb-2">
              <option value="LSV">LSV - Literal Standard Version</option>
              <option value="WEB">WEB - World English Bible</option>
              <option value="KJV">KJV - King James Version</option>
            </select>

            {/* Tool Categories */}
            <div className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 mt-2 mb-1">Tools</div>
            {[
              { id: 'lookup', label: 'Lookup' },
              { id: 'search', label: 'Search' },
              { id: 'connections', label: 'Connections' },
              { id: 'graph', label: 'Graph' },
              { id: 'gematria', label: 'Gematria' },
              { id: 'study', label: 'Study Guides' },
              { id: 'staging', label: 'Staging (propose data)' },
            ].map(tool => (
              <div key={tool.id} onClick={() => setEnabledTools(p => ({ ...p, [tool.id]: !p[tool.id] }))}
                role="button" tabIndex={0}
                onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setEnabledTools(p => ({ ...p, [tool.id]: !p[tool.id] })) } }}
                className="flex items-center justify-between py-1 pl-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer">
                <span className="text-[11px] text-neutral-600 dark:text-neutral-400">{tool.label}</span>
                <div className={`w-6 h-3.5 rounded-full p-0.5 transition-colors ${enabledTools[tool.id] ? 'bg-blue-500' : 'bg-neutral-300 dark:bg-neutral-600'}`}>
                  <div className={`w-2.5 h-2.5 rounded-full bg-white shadow-sm transition-transform ${enabledTools[tool.id] ? 'translate-x-3' : 'translate-x-0'}`} />
                </div>
              </div>
            ))}

            {/* Layers */}
            <div className="text-[9px] font-medium text-neutral-400 dark:text-neutral-500 mt-2 mb-1">Connection Layers</div>
            <ScopeRow label="Linguistic" id="linguistic" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Intertextual" id="intertextual" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Structural" id="structural" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Interpretive" id="interpretive" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Sod (Hidden)" id="sod" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Symbolic" id="symbolic" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Chronological" id="chronological" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Numerical" id="numerical" value={searchLayers} setter={setSearchLayers} />
            <ScopeRow label="Geographic" id="geographic" value={searchLayers} setter={setSearchLayers} />
          </div>
        </details>

        {/* All On / All Off */}
        <div className="flex gap-2 pt-3 pb-1.5">
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

/* ── Compact scope toggle row (for works/layers) ── */
function ScopeRow({ label, id, value, setter }) {
  const on = value[id] ?? true
  return (
    <div onClick={() => setter(p => ({ ...p, [id]: !on }))} role="button" tabIndex={0}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setter(p => ({ ...p, [id]: !on })) } }}
      className="flex items-center justify-between py-1 pl-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer">
      <span className="text-[11px] text-neutral-600 dark:text-neutral-400">{label}</span>
      <div className={`w-7 h-3.5 rounded-full p-0.5 transition-colors ${on ? 'bg-blue-500' : 'bg-neutral-300 dark:bg-neutral-600'}`}>
        <div className={`w-2.5 h-2.5 rounded-full bg-white shadow-sm transition-transform ${on ? 'translate-x-3.5' : 'translate-x-0'}`} />
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
