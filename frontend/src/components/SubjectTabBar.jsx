import React from 'react'

/**
 * SubjectTabBar — a horizontal row of workspace pills for desktop.
 * Shows above the chapter tab strip, visible on sm: and up.
 * Each pill is a workspace — click to switch.
 */
export default function SubjectTabBar({ workspaces, activeWorkspace, onSelect, onNew }) {
  if (!workspaces?.length) return null

  return (
    <div className="hidden sm:flex bg-neutral-50 dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 px-2 py-1 items-center gap-1 overflow-x-auto">
      {workspaces.map(ws => (
        <button
          key={ws.id}
          onClick={() => onSelect?.(ws.id)}
          className={`
            inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium
            transition-all cursor-pointer whitespace-nowrap shrink-0
            ${ws.id === activeWorkspace
              ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700 shadow-sm'
              : 'text-neutral-500 dark:text-neutral-400 border border-transparent hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-700 dark:hover:text-neutral-300'
            }
          `}
        >
          <span>{ws.name}</span>
          <span className={`text-[9px] font-mono px-1 rounded-full ${ws.id === activeWorkspace ? 'bg-blue-200 dark:bg-blue-800 text-blue-600 dark:text-blue-300' : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 dark:text-neutral-500'}`}>
            {ws.tabs?.length || 0}
          </span>
        </button>
      ))}
      <button onClick={() => onNew?.()}
        className="inline-flex items-center px-2 py-1 rounded text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800 cursor-pointer shrink-0 transition-colors">
        +
      </button>
    </div>
  )
}
