import React from 'react'

export default function ChiasmPanel({ chiasm }) {
  const borderColors = {
    'A': 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/20',
    "A'": 'border-red-400 dark:border-red-600 bg-red-50 dark:bg-red-900/20',
    'B': 'border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20',
    "B'": 'border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20',
    'C': 'border-green-400 dark:border-green-600 bg-green-50 dark:bg-green-900/20',
    "C'": 'border-green-400 dark:border-green-600 bg-green-50 dark:bg-green-900/20',
  }

  return (
    <div className="bg-white dark:bg-neutral-800 border border-indigo-200 dark:border-indigo-900 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/30 border-b border-indigo-200 dark:border-indigo-900">
        <span className="text-sm font-mono text-indigo-600 dark:text-indigo-300 font-bold">⟷</span>
        <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{chiasm.scholar} — {chiasm.chiasm_type || 'chiasm'}</span>
        <span className="text-xs text-neutral-400 dark:text-neutral-500 ml-auto">confidence: {chiasm.confidence}</span>
      </div>
      {chiasm.chapter_section && (
        <div className="px-3 pt-3">
          <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300">
            <span className="font-bold font-mono">{chiasm.chapter_section.label}</span>—<span>{chiasm.chapter_section.name}</span>
          </span>
        </div>
      )}
      {chiasm.elements?.length > 0 && (
        <div className="p-3 space-y-1.5">
          {chiasm.elements.map((el, i) => {
            const c = borderColors[el.label] || 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20'
            return (
              <div key={i} className={`flex items-center gap-3 px-3 py-1.5 rounded border-l-4 ${c}`}>
                <span className="text-xs font-bold font-mono w-6 text-neutral-600 dark:text-neutral-400">{el.label}</span>
                {el.verse > 0 && <span className="text-xs text-neutral-500 dark:text-neutral-400 font-mono w-8">v{el.verse}</span>}
                {el.text_snippet && <span className="text-xs text-neutral-600 dark:text-neutral-400 truncate">{el.text_snippet}</span>}
              </div>
            )
          })}
        </div>
      )}
      {chiasm.pivot_in_chapter && (
        <div className="px-3 pb-1 flex items-center gap-2 text-xs text-yellow-700 dark:text-yellow-400 font-medium">
          <span>◆</span> Pivot at verse {chiasm.pivot_verse_num}
        </div>
      )}
      {chiasm.notes && (
        <div className="px-3 pb-3 text-xs text-neutral-500 dark:text-neutral-400 italic">{chiasm.notes}</div>
      )}
    </div>
  )
}
