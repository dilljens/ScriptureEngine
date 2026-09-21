/**
 * Mobile bottom navigation — 5 tabs + More button.
 * Fixed to bottom of screen at all times on mobile.
 */

import React from 'react'

const TABS = [
  { id: 'read', label: 'Read', icon: '📖' },
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'hebrew', label: 'Hebrew', icon: 'א' },
  { id: 'learn', label: 'Learn', icon: '📚' },
  { id: 'memorize', label: 'Review', icon: '🧠' },
]

export default function MobileBottomNav({ activeTab, onTab, visible = true }) {
  return (
    <nav style={{ paddingBottom: 'env(safe-area-inset-bottom)' }} className={`sm:hidden fixed bottom-0 inset-x-0 z-50 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700 transition-transform duration-300 ${visible ? 'translate-y-0' : 'translate-y-full'}`}>
      <div className="flex items-center justify-around h-14 max-w-lg mx-auto">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTab(tab.id)}
            aria-label={tab.label}
            aria-current={activeTab === tab.id ? 'page' : undefined}
            className={`pressable flex flex-col items-center justify-center flex-1 h-full text-[11px] font-medium transition-colors cursor-pointer min-w-0 px-0.5
              ${activeTab === tab.id
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200'}`}
          >
            <span className={`text-lg leading-none mb-0.5 px-4 py-0.5 rounded-full transition-colors ${activeTab === tab.id ? 'bg-blue-100 dark:bg-blue-900/40' : ''}`}>{tab.icon}</span>
            <span className="truncate max-w-full">{tab.label}</span>
          </button>
        ))}
        <button onClick={() => onTab('menu')}
          aria-label="More options"
          className="pressable flex flex-col items-center justify-center h-full text-[11px] font-medium text-neutral-500 dark:text-neutral-400 min-w-0 px-0.5 hover:text-neutral-700 dark:hover:text-neutral-200 cursor-pointer">
          <span className="text-lg leading-none mb-0.5 px-4 py-0.5">⋮</span>
          <span className="truncate max-w-full">More</span>
        </button>
      </div>
    </nav>
  )
}
