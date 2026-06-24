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
      className={`inline font-medium
        transition-all cursor-pointer
        text-blue-600 dark:text-blue-400
        hover:text-blue-800 dark:hover:text-blue-300
        hover:underline
        ${compact ? 'text-[10px]' : 'text-sm'}
      `}
      title={`Click to view ${info.label}`}
    >
      {compact ? `${info.book} ${info.chapter}:${info.verse}` : info.label}
    </button>
  )
}
