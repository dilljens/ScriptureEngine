import React from 'react'
import { parseRef } from '../bookNames'

/**
 * VerseChip — inline clickable verse reference badge.
 *
 * Renders as a compact colored chip like "[📖 Genesis 1:1]"
 * Clicking opens a VersePopup with full verse context.
 */
export default function VerseChip({ ref: verseRef, onOpenCard, compact }) {
  const info = parseRef(verseRef)
  if (!info) {
    return <span className="text-red-500 text-xs">{verseRef}</span>
  }

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        e.preventDefault()
        if (onOpenCard) onOpenCard(verseRef)
      }}
      className={`inline-flex items-center gap-0.5 font-medium
        rounded-md transition-all cursor-pointer leading-none
        bg-blue-50 dark:bg-blue-900/30
        text-blue-700 dark:text-blue-300
        border border-blue-200 dark:border-blue-800
        hover:bg-blue-100 dark:hover:bg-blue-900/50
        hover:border-blue-300 dark:hover:border-blue-600
        shadow-sm hover:shadow
        ${compact ? 'px-1 py-0.5 text-[10px]' : 'px-1.5 py-0.5 text-xs'}
      `}
      title={`Click to preview ${info.label}`}
    >
      <span className="text-[10px] mr-0.5 leading-none" style={{ fontStyle: 'normal' }}>📖</span>
      {compact ? `${info.book} ${info.chapter}:${info.verse}` : info.label}
    </button>
  )
}
