import React, { useState, useEffect } from 'react'

const HOTKEY_LIST = [
  { action: 'search', label: 'Search scriptures' },
  { action: 'command', label: 'Command palette' },
  { action: 'chat', label: 'Chat panel' },
  { action: 'historyBack', label: 'History back' },
  { action: 'historyForward', label: 'History forward' },
  { action: 'darkMode', label: 'Toggle dark mode' },
  { action: 'fontUp', label: 'Increase font size' },
  { action: 'fontDown', label: 'Decrease font size' },
  { action: 'newTab', label: 'New tab' },
  { action: 'goUp', label: 'Zoom out (chapter→book→work)' },
  { action: 'goDown', label: 'Zoom in (work→book→chapter)' },
  { action: 'prevChapter', label: 'Previous chapter' },
  { action: 'nextChapter', label: 'Next chapter' },
  { action: 'toggleSynonymous', label: 'Toggle: Synonymous' },
  { action: 'toggleAntithetic', label: 'Toggle: Antithetic' },
  { action: 'toggleSynthetic', label: 'Toggle: Synthetic' },
  { action: 'toggleStaircase', label: 'Toggle: Staircase' },
  { action: 'toggleChiasmus', label: 'Toggle: Chiasmus' },
  { action: 'toggleFootnotes', label: 'Toggle: LDS Notes' },
  { action: 'toggleGematria', label: 'Toggle: Gematria' },
  { action: 'toggleLemma', label: 'Toggle: Lexicon' },
  { action: 'toggleTsk', label: 'Toggle: TSK cross-refs' },
  { action: 'toggleDirect', label: 'Toggle: Direct Quotes' },
  { action: 'toggleAllusion', label: 'Toggle: Allusions' },
  { action: 'toggleEcho', label: 'Toggle: Echoes' },
  { action: 'toggleTimes', label: 'Toggle: Times' },
  { action: 'togglePlaces', label: 'Toggle: Places' },
  { action: 'toggleIsaiah', label: 'Toggle: Isaiah patterns' },
  { action: 'structureModal', label: 'Isaiah structure' },
  { action: 'settingsPanel', label: 'Settings panel' },
]

export default function SettingsPanel({ onClose, hotkeys, getHotkey, setHotkey, resetHotkeys, DEFAULT_HOTKEYS, fontSize, changeFontSize, darkMode, toggleDarkMode, showQuickAsk, onToggleQuickAsk }) {
  const [editing, setEditing] = useState(null)
  const [tempKey, setTempKey] = useState('')

  // Key capture for rebinding
  useEffect(() => {
    if (!editing) return
    const handler = (e) => {
      e.preventDefault()
      e.stopPropagation()
      const parts = []
      if (e.ctrlKey || e.metaKey) parts.push(e.metaKey ? 'Cmd' : 'Ctrl')
      if (e.altKey) parts.push('Alt')
      if (e.shiftKey) parts.push('Shift')
      if (['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) return
      parts.push(e.key.length === 1 ? e.key.toUpperCase() : e.key)
      const combo = parts.join('+')
      setTempKey(combo)
      setEditing(null)
      setHotkey(editing, combo)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [editing, setHotkey])

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-12 pb-8 bg-black/30 dark:bg-black/50" onClick={onClose}>
      <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Settings</h2>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-lg">&times;</button>
        </div>

        {/* Quick settings */}
        <div className="px-6 py-4 border-b border-neutral-100 dark:border-neutral-700 space-y-3">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Display</h3>
          <div className="flex items-center justify-between">
            <span className="text-sm text-neutral-700 dark:text-neutral-300">Dark mode</span>
            <button onClick={toggleDarkMode} className={`px-3 py-1 rounded-lg text-xs font-medium cursor-pointer transition-colors ${darkMode ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300'}`}>
              {darkMode ? 'On' : 'Off'}
            </button>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-neutral-700 dark:text-neutral-300">Font size</span>
            <div className="flex items-center gap-2">
              <button onClick={() => changeFontSize(-1)} className="px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-sm cursor-pointer">−</button>
              <span className="text-sm w-8 text-center">{fontSize}%</span>
              <button onClick={() => changeFontSize(1)} className="px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-sm cursor-pointer">+</button>
            </div>
          </div>
        </div>

        {/* LLM settings */}
        <div className="px-6 py-4 border-b border-neutral-100 dark:border-neutral-700 space-y-3">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">LLM</h3>
          <div className="flex items-center justify-between">
            <span className="text-sm text-neutral-700 dark:text-neutral-300">Show Quick Ask in studies</span>
            <button onClick={onToggleQuickAsk}
              className={`px-3 py-1 rounded-lg text-xs font-medium cursor-pointer transition-colors ${showQuickAsk ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300'}`}>
              {showQuickAsk ? 'On' : 'Off'}
            </button>
          </div>
          <p className="text-[10px] text-neutral-400 dark:text-neutral-500">When on, a compact LLM chat bar appears at the bottom of study tabs for quick questions.</p>
        </div>

        {/* Hotkeys */}
        <div className="px-6 py-4 space-y-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Hotkeys</h3>
            <button onClick={resetHotkeys} className="text-[10px] text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">Reset defaults</button>
          </div>
          {HOTKEY_LIST.map(({ action, label }) => {
            const current = getHotkey(action)
            const isDefault = DEFAULT_HOTKEYS[action] === current
            const isEditing = editing === action
            return (
              <div key={action} className="flex items-center justify-between py-1.5 group">
                <span className="text-xs text-neutral-700 dark:text-neutral-300">{label}</span>
                <button
                  onClick={() => { setEditing(action); setTempKey('') }}
                  className={`px-2.5 py-1 rounded text-[10px] font-mono cursor-pointer transition-all border
                    ${isEditing ? 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-400 text-yellow-700 dark:text-yellow-300 animate-pulse' :
                      'bg-neutral-100 dark:bg-neutral-700 border-neutral-200 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600'}`}>
                  {isEditing ? 'Press keys...' : current || '—'}
                </button>
              </div>
            )
          })}
        </div>

        <div className="px-6 py-4 border-t border-neutral-100 dark:border-neutral-700 flex justify-between text-[10px] text-neutral-400">
          <span>Click a hotkey to rebind</span>
          <button onClick={onClose} className="text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">Close</button>
        </div>
      </div>
    </div>
  )
}
