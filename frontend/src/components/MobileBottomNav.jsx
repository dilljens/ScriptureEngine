/**
 * Mobile bottom navigation — 7 tabs with Hebrew, Learn, Memory.
 * Fixed to bottom of screen at all times on mobile.
 */

import React from 'react'

const TABS = [
  { id: 'read', label: 'Read', icon: '📖' },
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'hebrew', label: 'Hebrew', icon: 'א' },
  { id: 'learn', label: 'Learn', icon: '📚' },
  { id: 'memorize', label: 'Review', icon: '🧠' },
  { id: 'command', label: 'Go', icon: '🔍' },
  { id: 'menu', label: 'Menu', icon: '☰' },
]

export default function MobileBottomNav({ activeTab, onTab, visible = true }) {
  return (
    <nav className={`sm:hidden fixed bottom-0 inset-x-0 z-50 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700 safe-area-bottom transition-transform duration-300 ${visible ? 'translate-y-0' : 'translate-y-full'}`}>
      <div className="flex items-center justify-around h-14 max-w-lg mx-auto">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTab(tab.id)}
            className={`flex flex-col items-center justify-center flex-1 h-full text-[9px] font-medium transition-colors cursor-pointer min-w-0 px-0.5
              ${activeTab === tab.id
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300'}`}
          >
            <span className="text-base leading-none mb-0.5">{tab.icon}</span>
            <span className="truncate max-w-full">{tab.label}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}
