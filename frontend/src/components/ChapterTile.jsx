import React from 'react'
import { parseRef } from '../bookNames'

/**
 * ChapterTile — a small card representing a chapter tab.
 * Tap to open/switch to that chapter.
 * Long-press to drag (mobile).
 */
export default function ChapterTile({ tab, isActive, onSelect, onClose, onDragStart }) {
  const ref = parseRef(`${tab.book}.${tab.chapter}`)

  const workColors = {
    ot: 'border-l-amber-500', nt: 'border-l-blue-500',
    bom: 'border-l-green-500', dc: 'border-l-purple-500',
    pgp: 'border-l-pink-500', apoc: 'border-l-yellow-500',
  }
  const work = ref?.workId || 'ot'
  const borderColor = workColors[work] || 'border-l-neutral-400'

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart?.(tab, e)}
      onClick={() => onSelect?.(tab.id)}
      className={`
        flex items-center gap-2 px-2.5 py-2 rounded-lg border border-neutral-200 dark:border-neutral-700
        bg-white dark:bg-neutral-800 border-l-4 ${borderColor}
        cursor-pointer active:scale-95 transition-transform select-none
        ${isActive ? 'shadow-md ring-2 ring-blue-300 dark:ring-blue-700' : 'shadow-sm hover:shadow'}
      `}
    >
      <span className="text-xs font-mono font-bold text-neutral-700 dark:text-neutral-300 shrink-0">
        {ref?.book?.toUpperCase() || tab.book}
      </span>
      <span className="text-xs text-neutral-500 dark:text-neutral-400 font-mono">
        {tab.chapter}
      </span>
      <span className="flex-1 text-[10px] text-neutral-500 dark:text-neutral-400 truncate">
        {tab.label}
      </span>
      <button onClick={(e) => { e.stopPropagation(); onClose?.(tab.id) }}
        className="text-neutral-300 dark:text-neutral-600 hover:text-red-500 dark:hover:text-red-400 cursor-pointer text-sm leading-none shrink-0 px-1">
        ×
      </button>
    </div>
  )
}
