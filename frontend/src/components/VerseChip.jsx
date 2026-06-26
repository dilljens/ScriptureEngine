import React from 'react'
import { parseRef } from '../bookNames'

/**
 * VerseChip — inline clickable verse reference.
 * Renders as blue underlined text. Turns green after first click (visited).
 * No emoji, no background — just clean text.
 */
export default function VerseChip({ ref: verseRef, onOpenCard, compact, visited, onVisit }) {
  const info = parseRef(verseRef)
  if (!info) {
    return <span className="text-red-500 text-xs">{verseRef}</span>
  }

  return (
    <span
      onClick={(e) => {
        e.stopPropagation()
        e.preventDefault()
        if (onVisit) onVisit(verseRef)
        if (onOpenCard) onOpenCard(verseRef)
      }}
      className={`
        inline align-baseline font-medium
        transition-colors cursor-pointer
        ${visited
          ? 'text-green-600 dark:text-green-400'
          : 'text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300'
        }
        hover:underline
        ${compact ? 'text-[10px]' : 'text-sm'}
      `}
      title={`Click to view ${info.label}`}
    >
      {compact ? `${info.book} ${info.chapter}:${info.verse}` : info.label}
    </span>
  )
}
