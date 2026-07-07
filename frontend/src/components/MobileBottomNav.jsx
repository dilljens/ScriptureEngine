/**
 * Mobile bottom navigation — 5-tab bar (read, chat, tiles, command, menu).
 */

import React from 'react'

const TABS = [
  { id: 'read', label: 'Read', icon: '📖' },
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'tiles', label: 'Tiles', icon: '▦' },
  { id: 'command', label: 'Go', icon: '🔍' },
  { id: 'menu', label: 'Menu', icon: '☰' },
]

export default function MobileBottomNav({ activeTab, onTab }) {
  return (
    <nav className="fixed bottom-0 inset-x-0 z-50 sm:hidden bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700">
      <div className="flex items-center justify-around h-14">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTab(tab.id)}
            className={`flex flex-col items-center justify-center flex-1 h-full text-[10px] font-medium transition-colors cursor-pointer
              ${activeTab === tab.id
                ? 'text-blue-600 dark:text-blue-400'
                : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300'}`}
          >
            <span className="text-lg leading-none mb-0.5">{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>
    </nav>
  )
}
