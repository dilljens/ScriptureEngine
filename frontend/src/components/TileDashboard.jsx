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
  onSelectTab, onCloseTab, onMoveTab,
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

    </div>
  )
}
