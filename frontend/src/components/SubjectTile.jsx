import React, { useState } from 'react'
import ChapterTile from './ChapterTile'

/**
 * SubjectTile — a workspace represented as a card.
 * Shows a name and the number of tabs.
 * Tapping expands to show chapter tiles.
 * Chapters can be dragged into/out of this subject.
 */
export default function SubjectTile({ workspace, activeTab, onSelectTab, onCloseTab, onSelectWorkspace, onRename, onDelete, onMoveTab }) {
  const [expanded, setExpanded] = useState(false)
  const tabCount = workspace.tabs?.length || 0

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 overflow-hidden shadow-sm">
      {/* Subject header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors"
      >
        <span className="text-lg">{expanded ? '▾' : '▸'}</span>
        <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 flex-1 truncate">
          {workspace.name}
        </span>
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono bg-neutral-100 dark:bg-neutral-800 px-2 py-0.5 rounded-full">
          {tabCount}
        </span>
      </div>

      {/* Chapter tiles (visible when expanded) */}
      {expanded && (
        <div
          className="px-3 pb-3 space-y-1.5"
          onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }}
          onDrop={(e) => {
            e.preventDefault()
            try {
              const data = JSON.parse(e.dataTransfer.getData('text/plain'))
              if (data.tabId && data.fromWsId && data.fromWsId !== workspace.id) {
                onMoveTab?.(data.tabId, data.fromWsId, workspace.id)
              }
            } catch {}
          }}
        >
          {tabCount === 0 && (
            <p className="text-xs text-neutral-400 dark:text-neutral-500 italic text-center py-2">
              Drag chapters here
            </p>
          )}
          {(workspace.tabs || []).map(tab => (
            <div key={tab.id}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({
                  tabId: tab.id, fromWsId: workspace.id
                }))
              }}>
              <ChapterTile
                tab={tab}
                isActive={tab.id === activeTab}
                onSelect={onSelectTab}
                onClose={onCloseTab}
              />
            </div>
          ))}
          {/* Chapter tiles from other workspaces can be dropped here */}
          <div className="mt-1 text-[9px] text-neutral-300 dark:text-neutral-600 text-center italic">
            Drop chapters here to add to this subject
          </div>
        </div>
      )}
    </div>
  )
}
