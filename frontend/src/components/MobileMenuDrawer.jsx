import React, { useEffect, useRef } from 'react'

/**
 * Mobile menu drawer — slide-out panel with overflow navigation.
 * Primary destinations (Hebrew, Memorize, Learn) live in the bottom nav;
 * this drawer holds everything else: placement quiz, paths, reading, tools.
 */
export default function MobileMenuDrawer({
  open, onClose,
  onWiki, onLayers, onHistory, onStructure,
  darkMode, onToggleDarkMode,
  fontSize, onChangeFontSize,
  onSettings,
  onPlacement, onHubNotes, onStudies, onArticles,
  authUser, authAvatar, onSignIn, onSignOut,
}) {
  const touchStartY = useRef(null)
  useEffect(() => {
    if (!open) return
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 sm:hidden" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30" aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="More options"
        className="absolute bottom-0 inset-x-0 bg-white dark:bg-neutral-900 rounded-t-2xl shadow-2xl p-4 max-h-[80vh] max-h-[80dvh] overflow-y-auto overscroll-contain"
        style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))', touchAction: 'pan-y' }}
        onClick={e => e.stopPropagation()}
        onTouchStart={e => { touchStartY.current = e.touches[0]?.clientY ?? null }}
        onTouchEnd={e => {
          const start = touchStartY.current
          const end = e.changedTouches[0]?.clientY
          touchStartY.current = null
          if (start !== null && end !== undefined && end - start > 72) onClose?.()
        }}>
        <div className="w-10 h-1 rounded-full bg-neutral-300 dark:bg-neutral-600 mx-auto mb-4" aria-hidden="true" />

        {/* Learning Row */}
        <p className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2 px-1">Learning</p>
        <div className="grid grid-cols-4 gap-3 mb-4">
          <MenuButton icon="📝" label="Placement" onClick={onPlacement} badge="new" />
          <MenuButton icon="🗺️" label="Paths" onClick={onHubNotes} />
          <MenuButton icon="📜" label="Articles" onClick={onArticles} />
          <MenuButton icon="📖" label="Wiki" onClick={onWiki} />
          <MenuButton icon="🎓" label="Studies" onClick={onStudies} />
        </div>

        {/* Tools Row */}
        <p className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2 px-1">Tools</p>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <MenuButton icon="☰" label="Layers" onClick={onLayers} />
          <MenuButton icon="⊞" label="Structure" onClick={onStructure} />
          <MenuButton icon="🕐" label="History" onClick={onHistory} />
        </div>

        {/* Account Row */}
        <p className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2 px-1">Account</p>
        <div className="grid grid-cols-3 gap-3 mb-4">
          {onSignIn && !authUser ? (
            <button onClick={onSignIn}
              className="col-span-3 flex items-center gap-3 p-3 rounded-xl bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
              <span className="text-lg">👤</span>
              <div className="text-left">
                <div className="text-xs font-medium text-neutral-700 dark:text-neutral-300">Sign In</div>
                <div className="text-[9px] text-neutral-400">Sync conversations across devices</div>
              </div>
            </button>
          ) : onSignOut && authUser ? (
            <button onClick={onSignOut}
              className="col-span-3 flex items-center gap-3 p-3 rounded-xl bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
              {authAvatar ? (
                <img src={authAvatar} alt="" className="w-8 h-8 rounded-full" />
              ) : (
                <span className="text-lg">👤</span>
              )}
              <div className="text-left flex-1">
                <div className="text-xs font-medium text-neutral-700 dark:text-neutral-300">{authUser}</div>
                <div className="text-[9px] text-neutral-400">Tap to sign out</div>
              </div>
            </button>
          ) : null}
        </div>

        {/* Settings Row */}
        <p className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2 px-1">Settings</p>
        <div className="grid grid-cols-3 gap-3">
          <MenuButton icon={darkMode ? '🌙' : '☀️'} label={darkMode ? 'Light' : 'Dark'} onClick={onToggleDarkMode} />
          <div className="flex flex-col items-center justify-center gap-1 p-2 rounded-xl bg-neutral-100 dark:bg-neutral-800">
            <span className="text-[9px] text-neutral-400 font-medium">Font</span>
            <div className="flex items-center gap-2">
              <button aria-label="Decrease font size" onClick={() => onChangeFontSize(-1)} className="text-sm w-9 h-9 rounded bg-white dark:bg-neutral-700 cursor-pointer">A−</button>
              <span className="text-[10px] w-5 text-center font-mono">{fontSize}%</span>
              <button aria-label="Increase font size" onClick={() => onChangeFontSize(1)} className="text-sm w-9 h-9 rounded bg-white dark:bg-neutral-700 cursor-pointer">A+</button>
            </div>
          </div>
          <MenuButton icon="⚙" label="Settings" onClick={onSettings} />
        </div>

        <button onClick={onClose} className="w-full mt-4 py-2 text-sm text-neutral-500 bg-neutral-100 dark:bg-neutral-800 rounded-xl cursor-pointer">
          Close
        </button>
      </div>
    </div>
  )
}

function MenuButton({ icon, label, onClick, badge }) {
  return (
    <button onClick={onClick}
      className="relative flex flex-col items-center justify-center gap-1 p-3 rounded-xl bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
      {badge && (
        <span className="absolute top-1 right-1 text-[8px] px-1 py-0.5 rounded-full bg-indigo-500 text-white font-bold">{badge}</span>
      )}
      <span className="text-xl">{icon}</span>
      <span className="text-[10px] font-medium text-neutral-500 dark:text-neutral-400">{label}</span>
    </button>
  )
}
