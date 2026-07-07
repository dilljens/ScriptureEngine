/**
 * Settings and preferences — persisted in localStorage.
 *
 * Provides:
 *  - SettingsProvider (context)
 *  - useSettings() → { fontSize, changeFontSize, darkMode, toggleDarkMode,
 *                       getHotkey, setHotkey, DEFAULT_HOTKEYS, resetHotkeys,
 *                       hotkeys, showQuickAsk, persist }
 *  - useHistory() → { goBack, goForward, push }
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'

const SETTINGS_KEY = 'scripture_settings'
const HISTORY_KEY = 'scripture_history'

export const DEFAULT_HOTKEYS = {
  chat: '?',
  command: '/',
  commandAlt: 'Ctrl+P',
  historyBack: 'Alt+ArrowLeft',
  historyForward: 'Alt+ArrowRight',
  darkMode: 'Ctrl+D',
  fontUp: 'Ctrl+=',
  fontDown: 'Ctrl+-',
  newTab: 'Ctrl+T',
  structureModal: 'Ctrl+I',
  settingsPanel: 'Ctrl+,',
  toggleFootnotes: 'Ctrl+F',
  toggleGematria: 'Ctrl+G',
  toggleLemma: 'Ctrl+L',
  toggleSynonymous: 'Ctrl+1',
  toggleAntithetic: 'Ctrl+2',
  toggleSynthetic: 'Ctrl+3',
  toggleStaircase: 'Ctrl+4',
  toggleChiasmus: 'Ctrl+5',
  toggleTsk: 'Ctrl+6',
  toggleDirect: 'Ctrl+7',
  toggleAllusion: 'Ctrl+8',
  toggleEcho: 'Ctrl+9',
  toggleTimes: 'Ctrl+0',
  togglePlaces: 'Shift+Ctrl+0',
  toggleIsaiah: 'Ctrl+I',
  goUp: 'ArrowUp',
  goDown: 'ArrowDown',
}

const SettingsContext = createContext(null)
const HistoryContext = createContext(null)

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return {
    fontSize: 100,
    darkMode: false,
    hotkeys: { ...DEFAULT_HOTKEYS },
    showQuickAsk: true,
  }
}

function saveSettings(s) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
  } catch {}
}

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(loadSettings)

  const persist = useCallback((partial) => {
    setSettings(prev => {
      const next = { ...prev, ...partial }
      saveSettings(next)
      return next
    })
  }, [])

  const changeFontSize = useCallback((delta) => {
    persist({ fontSize: Math.max(60, Math.min(200, (settings.fontSize || 100) + delta)) })
  }, [settings.fontSize, persist])

  const toggleDarkMode = useCallback(() => {
    persist({ darkMode: !settings.darkMode })
  }, [settings.darkMode, persist])

  const getHotkey = useCallback((action) => {
    return settings.hotkeys?.[action] || DEFAULT_HOTKEYS[action]
  }, [settings.hotkeys])

  const setHotkey = useCallback((action, combo) => {
    persist({ hotkeys: { ...settings.hotkeys, [action]: combo } })
  }, [settings.hotkeys, persist])

  const resetHotkeys = useCallback(() => {
    persist({ hotkeys: { ...DEFAULT_HOTKEYS } })
  }, [persist])

  const value = {
    fontSize: settings.fontSize ?? 100,
    changeFontSize,
    darkMode: settings.darkMode ?? false,
    toggleDarkMode,
    getHotkey,
    setHotkey,
    DEFAULT_HOTKEYS,
    resetHotkeys,
    hotkeys: settings.hotkeys ?? DEFAULT_HOTKEYS,
    showQuickAsk: settings.showQuickAsk ?? true,
    persist,
  }

  return React.createElement(SettingsContext.Provider, { value }, children)
}

export function useSettings() {
  const ctx = useContext(SettingsContext)
  if (!ctx) {
    // Fallback for testing / edge cases
    return {
      fontSize: 100,
      changeFontSize: () => {},
      darkMode: false,
      toggleDarkMode: () => {},
      getHotkey: () => '',
      setHotkey: () => {},
      DEFAULT_HOTKEYS,
      resetHotkeys: () => {},
      hotkeys: DEFAULT_HOTKEYS,
      showQuickAsk: true,
      persist: () => {},
    }
  }
  return ctx
}

// ─── Navigation history ───

export function useHistory() {
  const stackRef = useRef([])
  const [idx, setIdx] = useState(-1)

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (Array.isArray(parsed.entries)) {
          stackRef.current = parsed.entries
          setIdx(parsed.idx ?? -1)
        }
      }
    } catch {}
  }, [])

  // Persist on change
  const persistHistory = useCallback((entries, index) => {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify({ entries, idx: index }))
    } catch {}
  }, [])

  const goBack = useCallback(() => {
    if (idx < 1) return null
    const newIdx = idx - 1
    setIdx(newIdx)
    persistHistory(stackRef.current, newIdx)
    return stackRef.current[newIdx]
  }, [idx, persistHistory])

  const goForward = useCallback(() => {
    if (idx >= stackRef.current.length - 1) return null
    const newIdx = idx + 1
    setIdx(newIdx)
    persistHistory(stackRef.current, newIdx)
    return stackRef.current[newIdx]
  }, [idx, persistHistory])

  const push = useCallback((entry) => {
    // If we've gone back, truncate future entries
    const entries = stackRef.current.slice(0, idx + 1)
    entries.push(entry)
    // Cap at 200 entries
    if (entries.length > 200) entries.splice(0, entries.length - 200)
    stackRef.current = entries
    const newIdx = entries.length - 1
    setIdx(newIdx)
    persistHistory(entries, newIdx)
  }, [idx, persistHistory])

  return { goBack, goForward, push }
}
