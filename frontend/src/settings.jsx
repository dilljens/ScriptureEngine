/**
 * Settings and preferences — persisted in localStorage, synced to server.
 *
 * Provides:
 *  - SettingsProvider (context)
 *  - useSettings() → { fontSize, changeFontSize, darkMode, toggleDarkMode,
 *                       getHotkey, setHotkey, DEFAULT_HOTKEYS, resetHotkeys,
 *                       hotkeys, showQuickAsk, hebrewOnly, onToggleHebrewOnly,
 *                       sessionToken, setSessionToken, persist, syncStatus }
 *  - useHistory() → { goBack, goForward, push }
 *
 * Sync flow:
 *  1. Settings are saved to localStorage immediately (offline-first)
 *  2. If sessionToken is set, also POST to /api/v1/user/settings
 *  3. On mount with sessionToken, GET /api/v1/user/settings and merge
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'

const SETTINGS_KEY = 'scripture_settings'
const HISTORY_KEY = 'scripture_history'
const TOKEN_KEY = 'scripture_session_token'

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
    hebrewOnly: false,
  }
}

function saveSettings(s) {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(s))
  } catch {}
}

async function syncSettingsToServer(settings, token) {
  if (!token) return
  try {
    await fetch('/api/v1/user/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_token: token, settings }),
    })
  } catch { /* offline — will sync on next request */ }
}

async function loadServerSettings(token) {
  if (!token) return null
  try {
    const r = await fetch(`/api/v1/user/settings?session_token=${encodeURIComponent(token)}`)
    const d = await r.json()
    if (d.ok && d.data?.settings) return d.data.settings
  } catch {}
  return null
}

function loadSessionToken() {
  try { return localStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
}

function saveSessionToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {}
}

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(loadSettings)
  const [sessionToken, setSessionTokenState] = useState(loadSessionToken)
  const [syncStatus, setSyncStatus] = useState('offline') // offline | syncing | synced | error

  // Load server settings on mount if token exists
  useEffect(() => {
    const token = loadSessionToken()
    if (!token) return
    setSyncStatus('syncing')
    loadServerSettings(token).then(serverSettings => {
      if (serverSettings) {
        setSettings(prev => {
          const merged = { ...serverSettings, ...prev }  // local wins for conflicts
          saveSettings(merged)
          return merged
        })
      }
      setSyncStatus('synced')
    }).catch(() => setSyncStatus('error'))
  }, [])

  const setSessionToken = useCallback((token) => {
    saveSessionToken(token)
    setSessionTokenState(token)
    if (token) {
      setSyncStatus('syncing')
      loadServerSettings(token).then(serverSettings => {
        if (serverSettings) {
          setSettings(prev => {
            const merged = { ...serverSettings, ...prev }
            saveSettings(merged)
            return merged
          })
        }
        setSyncStatus('synced')
      }).catch(() => setSyncStatus('synced'))
    } else {
      setSyncStatus('offline')
    }
  }, [])

  const persist = useCallback((partial) => {
    setSettings(prev => {
      const next = { ...prev, ...partial }
      saveSettings(next)
      // Fire-and-forget sync to server
      const token = loadSessionToken()
      if (token) syncSettingsToServer(next, token)
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

  const onToggleHebrewOnly = useCallback(() => {
    persist({ hebrewOnly: !settings.hebrewOnly })
  }, [settings.hebrewOnly, persist])

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
    hebrewOnly: settings.hebrewOnly ?? false,
    onToggleHebrewOnly,
    sessionToken,
    setSessionToken,
    syncStatus,
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
      hebrewOnly: false,
      onToggleHebrewOnly: () => {},
      sessionToken: '',
      setSessionToken: () => {},
      syncStatus: 'offline',
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
