/**
 * Two-layer tab system: Workspaces (top) → Tabs (bottom)
 * Persisted in localStorage.
 *
 * Structure:
 *   workspaces: [{ id, name, tabs: [{ id, book, chapter, label }] }]
 *   activeWorkspace: id
 *   activeTab: id
 */

import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'scripture_tabs'
let nextId = 100

function genId() {
  return `tab_${nextId++}_${Date.now()}`
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed.workspaces?.length > 0) return parsed
    }
  } catch {}
  // Default: one workspace with Isaiah 6
  return {
    workspaces: [{
      id: genId(),
      name: 'My Study',
      tabs: [{
        id: genId(),
        book: 'isa',
        chapter: 6,
        label: 'Isaiah 6',
        view: 'chapter',
        viewRef: null,
        highlights: [],
        companion: null,
      }],
    }],
    activeWorkspace: null,
    activeTab: null,
  }
}

function saveState(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      workspaces: state.workspaces,
      activeWorkspace: state.activeWorkspace,
      activeTab: state.activeTab,
    }))
  } catch {}
}

function reducer(state, action) {
  let s
  switch (action.type) {
    case 'INIT': {
      const loaded = loadState()
      // Migrate legacy tabs (add view/viewRef defaults)
      for (const w of loaded.workspaces) {
        for (const t of w.tabs) {
          if (!t.view) t.view = 'chapter'
          if (!t.viewRef) t.viewRef = null
          if (!t.highlights) t.highlights = []
          if (!t.companion) t.companion = null
        }
      }
      if (!loaded.workspaces.find(w => w.id === loaded.activeWorkspace)) {
        loaded.activeWorkspace = loaded.workspaces[0]?.id || null
      }
      const ws = loaded.workspaces.find(w => w.id === loaded.activeWorkspace)
      if (ws && !ws.tabs.find(t => t.id === loaded.activeTab)) {
        loaded.activeTab = ws.tabs[0]?.id || null
      }
      return loaded
    }

    case 'NEW_WORKSPACE':
      s = { ...state }
      s.workspaces = [...s.workspaces, {
        id: genId(),
        name: action.name || 'New Workspace',
        tabs: [],
      }]
      s.activeWorkspace = s.workspaces[s.workspaces.length - 1].id
      s.activeTab = null
      saveState(s)
      return s

    case 'RENAME_WORKSPACE': {
      s = { ...state }
      s.workspaces = s.workspaces.map(w =>
        w.id === action.id ? { ...w, name: action.name } : w
      )
      saveState(s)
      return s
    }

    case 'DELETE_WORKSPACE':
      s = { ...state }
      s.workspaces = s.workspaces.filter(w => w.id !== action.id)
      if (s.activeWorkspace === action.id) {
        s.activeWorkspace = s.workspaces[0]?.id || null
        const ws = s.workspaces.find(w => w.id === s.activeWorkspace)
        s.activeTab = ws?.tabs[0]?.id || null
      }
      saveState(s)
      return s

    case 'SELECT_WORKSPACE':
      s = { ...state }
      s.activeWorkspace = action.id
      const wsTarget = s.workspaces.find(w => w.id === action.id)
      s.activeTab = wsTarget?.tabs[0]?.id || null
      saveState(s)
      return s

    case 'NEW_TAB': {
      s = { ...state }
      const ws = s.workspaces.find(w => w.id === s.activeWorkspace)
      if (!ws) return state
      const tab = {
        id: genId(),
        book: action.book || 'isa',
        chapter: action.chapter || 1,
        label: action.label || `${action.book || 'isa'} ${action.chapter || 1}`,
        view: action.view || 'chapter',
        viewRef: action.viewRef || null,
        highlights: action.highlights || [],
        companion: null,
      }
      ws.tabs = [...ws.tabs, tab]
      s.activeTab = tab.id
      saveState(s)
      return s
    }

    case 'CLOSE_TAB':
      s = { ...state }
      const wsClose = s.workspaces.find(w => w.id === s.activeWorkspace)
      if (!wsClose) return state
      wsClose.tabs = wsClose.tabs.filter(t => t.id !== action.id)
      if (s.activeTab === action.id) {
        s.activeTab = wsClose.tabs[wsClose.tabs.length - 1]?.id || null
      }
      saveState(s)
      return s

    case 'MOVE_TAB': {
      s = { ...state }
      const fromWs = s.workspaces.find(w => w.id === action.fromWorkspaceId)
      const toWs = s.workspaces.find(w => w.id === action.toWorkspaceId)
      if (!fromWs || !toWs) return state
      const tab = fromWs.tabs.find(t => t.id === action.tabId)
      if (!tab) return state
      fromWs.tabs = fromWs.tabs.filter(t => t.id !== action.tabId)
      toWs.tabs = [...toWs.tabs, tab]
      // If moved from active workspace, update activeTab
      if (s.activeWorkspace === action.fromWorkspaceId && s.activeTab === action.tabId) {
        s.activeWorkspace = action.toWorkspaceId
      }
      saveState(s)
      return s
    }

    case 'SELECT_TAB':
      s = { ...state }
      s.activeTab = action.id
      saveState(s)
      return s

    case 'UPDATE_TAB': {
      s = { ...state }
      const wsU = s.workspaces.find(w => w.id === s.activeWorkspace)
      if (!wsU) return state
      wsU.tabs = wsU.tabs.map(t =>
        t.id === action.id ? { ...t, ...action.updates } : t
      )
      saveState(s)
      return s
    }

    case 'SPLIT_VIEW': {
      s = { ...state }
      const wsSv = s.workspaces.find(w => w.id === s.activeWorkspace)
      if (!wsSv) return state
      wsSv.tabs = wsSv.tabs.map(t =>
        t.id === action.tabId ? { ...t, companion: action.companionId || null } : t
      )
      saveState(s)
      return s
    }

    default:
      return state
  }
}

const TabCtx = createContext()

export function TabProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, null)

  // Load initial state
  useEffect(() => {
    if (!state) {
      dispatch({ type: 'INIT' })
    }
  }, [state])

  // Convenience actions
  const actions = {
    newWorkspace: useCallback(name => dispatch({ type: 'NEW_WORKSPACE', name }), []),
    renameWorkspace: useCallback((id, name) => dispatch({ type: 'RENAME_WORKSPACE', id, name }), []),
    deleteWorkspace: useCallback(id => dispatch({ type: 'DELETE_WORKSPACE', id }), []),
    selectWorkspace: useCallback(id => dispatch({ type: 'SELECT_WORKSPACE', id }), []),

    openTab: useCallback((book, chapter, opts = {}) => {
      dispatch({
        type: 'NEW_TAB',
        book,
        chapter,
        label: opts.label || `${book}.${chapter}`,
        view: opts.view || 'chapter',
        viewRef: opts.viewRef || null,
        highlights: opts.highlights || [],
      })
    }, []),

    closeTab: useCallback(id => dispatch({ type: 'CLOSE_TAB', id }), []),
    moveTab: useCallback((tabId, fromWorkspaceId, toWorkspaceId) =>
      dispatch({ type: 'MOVE_TAB', tabId, fromWorkspaceId, toWorkspaceId }), []),
    selectTab: useCallback(id => dispatch({ type: 'SELECT_TAB', id }), []),

    updateTab: useCallback((id, updates) => dispatch({ type: 'UPDATE_TAB', id, updates }), []),
    splitView: useCallback((tabId, companionId) =>
      dispatch({ type: 'SPLIT_VIEW', tabId, companionId }), []),

    // Navigate within the CURRENT tab (updates in place, no new tab)
    navigateTo: useCallback((tabId, updates) => {
      dispatch({ type: 'UPDATE_TAB', id: tabId, updates })
    }, []),

    // Convenience: navigate to chapter view
    goToChapter: useCallback((tabId, book, chapter, label) => {
      dispatch({ type: 'UPDATE_TAB', id: tabId, updates: {
        book, chapter, view: 'chapter', viewRef: null,
        label: label || `${book} ${chapter}`,
      }})
    }, []),

    // Convenience: navigate to book view (shows chapter list)
    goToBook: useCallback((tabId, bookId, bookLabel) => {
      dispatch({ type: 'UPDATE_TAB', id: tabId, updates: {
        book: bookId, chapter: 1, view: 'book', viewRef: bookId,
        label: bookLabel || bookId,
      }})
    }, []),

    // Convenience: navigate to work view (shows book list)
    goToWork: useCallback((tabId, workId, workLabel) => {
      dispatch({ type: 'UPDATE_TAB', id: tabId, updates: {
        book: 'isa', chapter: 1, view: 'work', viewRef: workId,
        label: workLabel || workId,
      }})
    }, []),

    // Open verses from chat results as a new tab with highlights
    openVersesAsTab: useCallback((book, chapter, verses) => {
      dispatch({
        type: 'NEW_TAB',
        book,
        chapter,
        label: `${book}.${chapter} — ${verses.length} highlighted verses`,
        highlights: verses,
      })
    }, []),

    // Open (or focus) a memorize tab — creates view: 'memorize'
    openMemorizeTab: useCallback((label) => {
      const ws = state?.workspaces.find(w => w.id === state?.activeWorkspace)
      const existing = ws?.tabs.find(t => t.view === 'memorize')
      if (existing) {
        dispatch({ type: 'SELECT_TAB', id: existing.id })
      } else {
        dispatch({
          type: 'NEW_TAB',
          book: 'gen',
          chapter: 1,
          label: label || 'Memorize',
          view: 'memorize',
        })
      }
    }, [state]),

    // Open (or focus) a chat tab — creates view: 'chat'
    openChatTab: useCallback((label) => {
      // Check if a chat tab already exists in the active workspace
      const ws = state?.workspaces.find(w => w.id === state?.activeWorkspace)
      const existing = ws?.tabs.find(t => t.view === 'chat')
      if (existing) {
        dispatch({ type: 'SELECT_TAB', id: existing.id })
      } else {
        dispatch({
          type: 'NEW_TAB',
          book: 'gen',
          chapter: 1,
          label: label || 'Chat',
          view: 'chat',
        })
      }
    }, [state]),
  }

  const currentWorkspace = state
    ? state.workspaces.find(w => w.id === state.activeWorkspace) || state.workspaces[0]
    : null
  const currentTab = currentWorkspace
    ? currentWorkspace.tabs.find(t => t.id === state.activeTab) || currentWorkspace.tabs[0]
    : null

  // Current view level
  const viewLevel = currentTab?.view || 'chapter'
  const viewUp = viewLevel === 'chapter' ? 'book' : viewLevel === 'book' ? 'work' : viewLevel === 'work' ? 'library' : viewLevel === 'library' ? 'tiles' : null
  const viewDown = viewLevel === 'tiles' ? 'library' : viewLevel === 'library' ? 'work' : viewLevel === 'work' ? 'book' : viewLevel === 'book' ? 'chapter' : null
  const isLibraryView = viewLevel === 'library'

  // Is the current view a chapter (showing verses)?
  const isChapterView = viewLevel === 'chapter'

  return (
    <TabCtx.Provider value={{
      workspaces: state?.workspaces || [],
      activeWorkspace: state?.activeWorkspace || null,
      activeTab: state?.activeTab || null,
      currentWorkspace,
      currentTab,
      viewLevel,
      viewRef: currentTab?.viewRef || null,
      viewUp,
      viewDown,
      isChapterView,
      isLibraryView,
      ...actions,
    }}>
      {children}
    </TabCtx.Provider>
  )
}

export function useTabs() {
  const ctx = useContext(TabCtx)
  if (!ctx) throw new Error('useTabs must be used within TabProvider')
  return ctx
}
