import React from 'react'

/**
 * TabButton — bottom navigation tab for mobile.
 * Renders an icon + label with active state highlighting.
 */
export default function TabButton({ icon, label, active, onClick }) {
  return (
    <button onClick={onClick}
      className={`flex flex-col items-center justify-center gap-0.5 px-3 py-1 rounded-lg transition-colors cursor-pointer ${
        active
          ? 'text-indigo-600 dark:text-indigo-400'
          : 'text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-400'
      }`}
      title={label}>
      <span className={active ? '' : 'opacity-70'}>{icon}</span>
      <span className="text-[9px] font-medium leading-tight">{label}</span>
    </button>
  )
}
