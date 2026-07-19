import React from 'react'

/**
 * Mobile menu drawer — slide-out panel with navigation options.
 * Includes Hebrew, Memorize, Knowledge, Wiki, and settings.
 */
export default function MobileMenuDrawer({
  open, onClose,
  onWiki, onLayers, onHistory, onStructure,
  darkMode, onToggleDarkMode,
  fontSize, onChangeFontSize,
  onSettings,
  onHebrew, onMemorize, onKnowledge, onHubNotes,
  authUser, authAvatar, onSignIn, onSignOut,
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 sm:hidden" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30" />
      <div className="absolute bottom-0 inset-x-0 bg-white dark:bg-neutral-900 rounded-t-2xl shadow-2xl p-4 pb-8 max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="w-10 h-1 rounded-full bg-neutral-300 dark:bg-neutral-600 mx-auto mb-4" />

        {/* Learning Row */}
        <p className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2 px-1">Learning</p>
        <div className="grid grid-cols-4 gap-3 mb-4">
          <MenuButton icon="📖" label="Hebrew" onClick={onHebrew} badge="new" />
          <MenuButton icon="🧠" label="Memorize" onClick={onMemorize} badge="" />
          <MenuButton icon="📚" label="Learn" onClick={onKnowledge} badge="" />
          <MenuButton icon="🗺️" label="Paths" onClick={onHubNotes} />
          <MenuButton icon="📖" label="Wiki" onClick={onWiki} />
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
              <button onClick={() => onChangeFontSize(-1)} className="text-sm w-6 h-6 rounded bg-white dark:bg-neutral-700 cursor-pointer">A−</button>
              <span className="text-[10px] w-5 text-center font-mono">{fontSize}%</span>
              <button onClick={() => onChangeFontSize(1)} className="text-sm w-6 h-6 rounded bg-white dark:bg-neutral-700 cursor-pointer">A+</button>
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
