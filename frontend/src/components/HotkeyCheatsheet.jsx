import React from 'react'

const GROUPS = [
  { title: 'Navigation', actions: ['goUp', 'goDown', 'prevChapter', 'nextChapter', 'historyBack', 'historyForward'] },
  { title: 'Tabs', actions: ['newTab'] },
  { title: 'Display', actions: ['darkMode', 'fontUp', 'fontDown'] },
  { title: 'Tools', actions: ['search', 'command', 'chat', 'settingsPanel'] },
  { title: 'Toggles', actions: ['toggleFootnotes', 'toggleGematria', 'toggleLemma', 'toggleSynonymous', 'toggleAntithetic', 'toggleSynthetic', 'toggleStaircase', 'toggleChiasmus', 'toggleTsk'] },
  { title: 'Quotations', actions: ['toggleDirect', 'toggleAllusion', 'toggleEcho'] },
  { title: 'Context', actions: ['toggleTimes', 'togglePlaces', 'toggleIsaiah'] },
  { title: 'Structure', actions: ['structureModal'] },
]

const LABELS = {
  goUp: 'Zoom out', goDown: 'Zoom in', prevChapter: 'Prev chapter', nextChapter: 'Next chapter',
  historyBack: 'History back', historyForward: 'History forward', newTab: 'New tab',
  darkMode: 'Toggle dark mode', fontUp: 'Increase font', fontDown: 'Decrease font',
  search: 'Search scriptures', command: 'Command palette', chat: 'Chat panel',
  settingsPanel: 'Settings', toggleSynonymous: '≡ Synonymous', toggleAntithetic: '⇄ Antithetic',
  toggleSynthetic: '→ Synthetic', toggleStaircase: '⊻ Staircase', toggleChiasmus: '⟷ Chiasmus',
  toggleFootnotes: 'ᵃ LDS Notes', toggleGematria: '🔢 Gematria', toggleLemma: 'λ Lexicon',
  toggleTsk: 'ᵗ TSK', toggleDirect: '📖 Direct', toggleAllusion: '🔗 Allusion',
  toggleEcho: '💬 Echo', toggleTimes: '📅 Times', togglePlaces: '🌍 Places',
  toggleIsaiah: '🔍 Isaiah', structureModal: 'Isaiah structure',
}

export default function HotkeyCheatsheet({ onClose, getHotkey, DEFAULT_HOTKEYS }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 dark:bg-black/50" onClick={onClose}>
      <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Keyboard Shortcuts</h2>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-lg">&times;</button>
        </div>
        <div className="px-6 py-4 space-y-4">
          {GROUPS.map(group => (
            <div key={group.title}>
              <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">{group.title}</h3>
              <div className="space-y-1.5">
                {group.actions.map(action => (
                  <div key={action} className="flex items-center justify-between py-0.5">
                    <span className="text-xs text-neutral-700 dark:text-neutral-300">{LABELS[action] || action}</span>
                    <kbd className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 text-neutral-600 dark:text-neutral-300">
                      {getHotkey(action) || DEFAULT_HOTKEYS[action] || '—'}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="px-6 py-3 border-t border-neutral-100 dark:border-neutral-700 flex justify-between text-[10px] text-neutral-400">
          <span>Customize in Settings (<kbd className="font-mono bg-neutral-100 dark:bg-neutral-700 px-1 rounded">{getHotkey('settingsPanel')}</kbd>)</span>
          <button onClick={onClose} className="text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">Close</button>
        </div>
      </div>
    </div>
  )
}
