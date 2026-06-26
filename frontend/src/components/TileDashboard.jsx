import React, { useState } from 'react'
import SubjectTile from './SubjectTile'

/**
 * TileDashboard — a tile-based view of workspaces and tabs.
 * Mobile: replaces the tab strip as the primary navigation.
 * Desktop: an optional view mode (like Library/Work/Book views).
 */
export default function TileDashboard({
  workspaces, activeWorkspace, activeTab,
  onSelectWorkspace, onNewWorkspace, onRenameWorkspace, onDeleteWorkspace,
  onSelectTab, onCloseTab, onMoveTab, onOpenTab,
  book, chapter, bookTitle,
}) {
  const [newName, setNewName] = useState('')

  const handleNew = () => {
    const name = newName.trim() || `Subject ${workspaces.length + 1}`
    onNewWorkspace?.(name)
    setNewName('')
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">My Subjects</h2>
        <div className="flex items-center gap-2">
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleNew() }}
            placeholder="New subject..."
            className="w-36 px-2.5 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-xs bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 placeholder-neutral-400"
          />
          <button onClick={handleNew}
            className="px-3 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 cursor-pointer transition-colors">
            + Add
          </button>
        </div>
      </div>

      {/* Subject tiles grid */}
      {workspaces.length === 0 ? (
        <div className="text-center py-20 text-sm text-neutral-400 dark:text-neutral-500">
          No subjects yet. Create one to start organizing your study.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {workspaces.map(ws => (
            <SubjectTile
              key={ws.id}
              workspace={ws}
              activeTab={activeTab}
              onSelectTab={onSelectTab}
              onCloseTab={onCloseTab}
              onSelectWorkspace={onSelectWorkspace}
              onRename={onRenameWorkspace}
              onDelete={onDeleteWorkspace}
              onMoveTab={onMoveTab}
            />
          ))}
        </div>
      )}

      {/* Mobile: compact now-reading bar */}
      <div className="sm:hidden fixed bottom-0 left-0 right-0 bg-white/90 dark:bg-neutral-950/90 backdrop-blur border-t border-neutral-200 dark:border-neutral-800 px-3 py-2">
        <div className="flex items-center gap-2 max-w-5xl mx-auto">
          <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-medium uppercase tracking-wider">Now reading</span>
          <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300 truncate">
            {bookTitle} {chapter}
          </span>
          <button onClick={() => onOpenTab?.(book, chapter, { label: `${bookTitle} ${chapter}` })}
            className="ml-auto px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[10px] font-medium hover:bg-blue-700 cursor-pointer transition-colors">
            Open
          </button>
        </div>
      </div>
    </div>
  )
}
