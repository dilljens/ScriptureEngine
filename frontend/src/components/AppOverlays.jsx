import React, { Suspense } from 'react'
import { useTabs } from '../tabContext.jsx'
import { useSettings } from '../settings.jsx'
import { useToggles } from './ToggleProvider'
import ErrorBoundary from './ErrorBoundary'
import StructureModal from './StructureModal'
import SettingsPanel from './SettingsPanel'
import HotkeyCheatsheet from './HotkeyCheatsheet'
import CommandInput from './CommandInput'
import MobileBottomNav from './MobileBottomNav'
import MobileMenuDrawer from './MobileMenuDrawer'
import { resetHebrewSessionUser } from '../api'
const ChatPanel = React.lazy(() => import('./ChatPanel'))
const AssessmentView = React.lazy(() => import('./AssessmentView'))

/**
 * AppOverlays — modal overlays rendered above the main view: structure modal,
 * chat panel, command palette, split-picker, settings, assessment, hotkey
 * cheatsheet, global Hebrew keyboard.
 *
 * Extracted from App.jsx (god-file decomposition, sentrux no_god_files).
 */
export default function AppOverlays(props) {
  const {
    chatInitialMsg, mobileActiveTab, showAssessment, showChat, showCheatsheet,
    showCommand, showGlobalKeyboard, showHistory, showLayers, showMobileMenu,
    showSettings, showSplitPicker, showStructure, splitTarget, userId, userName, userAvatar,
    uiVisible,
    setChatInitialMsg, setShowAssessment, setShowChat, setShowCheatsheet,
    setShowCommand, setShowGlobalKeyboard, setShowHistory, setShowLayers,
    setShowMobileMenu, setShowSettings, setShowSplitPicker, setShowStructure,
    setSplitTarget, setUiVisible, setUserAvatar, setUserId, setUserName,
    allBooks, handleChatNavigate, handleChatOpenTab, handleCommandChat,
    handleCommandNav, handleConfirmSplit, handleSearchCommand, openLibraryView,
    openTilesView, setCollection, setHebrewLessonId, setStudyWeek,
    setShowHebrewDiagnostic,
  } = props

  const {
    currentTab, viewLevel, goToChapter, updateTab,
    currentWorkspace, selectTab, openChatTab, openHebrewTab, openLearnTab,
    openMemorizeTab, openWikiTab, openHubNoteTab, openStudiesTab, openArticlesTab,
  } = useTabs()
  const {
    hotkeys, getHotkey, setHotkey, resetHotkeys, DEFAULT_HOTKEYS,
    fontSize, changeFontSize, darkMode, toggleDarkMode, showQuickAsk,
    hebrewOnly, persist, sessionToken, setSessionToken, syncStatus,
  } = useSettings()
  const { dispatch } = useToggles()

  const handleSignOut = () => {
    // Keep the anonymous device identity, but drop all account-scoped state.
    try {
      localStorage.removeItem('scripture_session_token')
      localStorage.removeItem('scripture_user_name')
      localStorage.removeItem('scripture_user_avatar')
      localStorage.removeItem('scripture_auth_user_id')
    } catch {}
    setSessionToken('')
    resetHebrewSessionUser()
    setUserName('')
    setUserAvatar('')
  }

  return (
    <>
      {/* Overlays */}
      <StructureModal open={showStructure} onClose={() => setShowStructure(false)}
        onNavigate={(ref) => { if (ref && currentTab?.id) { const p = ref.split('.'); if (p.length >= 2) goToChapter(currentTab.id, p[0], parseInt(p[1]) || 1) }; setShowStructure(false) }} />
      <Suspense fallback={null}>
        <ChatPanel open={showChat} onClose={() => { setShowChat(false); setChatInitialMsg('') }}
          initialMessage={chatInitialMsg}
          onInitialConsumed={() => setChatInitialMsg('')}
          onNavigate={handleChatNavigate} onOpenTab={handleChatOpenTab} />
      </Suspense>
      <CommandInput open={showCommand} onClose={() => setShowCommand(false)}
        allBooks={allBooks}
        onNavigate={handleCommandNav} onChat={handleCommandChat} onCommand={handleSearchCommand} />

      {/* Split-pane chapter picker */}
      {showSplitPicker && (
        <div role="dialog" aria-modal="true" aria-label="Split with chapter" className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowSplitPicker(false)}>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl border border-neutral-200 dark:border-neutral-700 p-4 w-72" onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-3">Split with chapter</h3>
            <div className="flex items-center gap-2 mb-3">
              <input value={splitTarget.book} onChange={e => setSplitTarget({ ...splitTarget, book: e.target.value })}
                placeholder="Book (e.g. isa)"
                className="flex-1 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-xs bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 placeholder-neutral-400" />
              <input value={splitTarget.chapter} onChange={e => setSplitTarget({ ...splitTarget, chapter: e.target.value.replace(/[^0-9]/g, '') })}
                placeholder="Ch"
                className="w-16 px-2 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-xs bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 placeholder-neutral-400 text-center" />
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowSplitPicker(false)}
                className="flex-1 px-3 py-1.5 rounded-lg text-xs font-medium text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
                Cancel
              </button>
              <button onClick={handleConfirmSplit}
                className="flex-1 px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 cursor-pointer transition-colors">
                Split
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings panel */}
      {/* Hotkey Cheatsheet */}
      {showCheatsheet && <HotkeyCheatsheet onClose={() => setShowCheatsheet(false)} getHotkey={getHotkey} DEFAULT_HOTKEYS={DEFAULT_HOTKEYS} />}

      {showSettings && (
        <SettingsPanel
          onClose={() => setShowSettings(false)}
          hotkeys={hotkeys}
          getHotkey={getHotkey}
          setHotkey={setHotkey}
          resetHotkeys={resetHotkeys}
          DEFAULT_HOTKEYS={DEFAULT_HOTKEYS}
          fontSize={fontSize}
          changeFontSize={changeFontSize}
          darkMode={darkMode}
          toggleDarkMode={toggleDarkMode}
          showQuickAsk={showQuickAsk}
          onToggleQuickAsk={() => persist({ showQuickAsk: !showQuickAsk })}
          hebrewOnly={hebrewOnly}
          onToggleHebrewOnly={() => persist({ hebrewOnly: !hebrewOnly })}
          sessionToken={sessionToken}
          setSessionToken={setSessionToken}
          syncStatus={syncStatus}
        />
      )}

      {showAssessment && (
        <div role="dialog" aria-modal="true" aria-label="Assessment" className="fixed inset-0 z-50 flex items-start justify-center pt-8 pb-8 bg-black/30 dark:bg-black/50">
          <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
              <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">📝 Scripture Assessment</h2>
              <button onClick={() => setShowAssessment(false)}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-lg">&times;</button>
            </div>
            <div className="p-4">
              <Suspense fallback={<div className="p-8 text-center text-sm text-neutral-400 animate-pulse">Loading assessment...</div>}>
                <AssessmentView user_id={userId} onBack={() => setShowAssessment(false)} />
              </Suspense>
            </div>
          </div>
        </div>
      )}

      {/* Global Hebrew keyboard (floating at bottom) */}
      {showGlobalKeyboard && (
        <div className="fixed bottom-0 inset-x-0 z-50 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700 p-2 shadow-2xl">
          <div className="flex items-center justify-between mb-2 px-1">
            <span className="text-[10px] text-neutral-500 dark:text-neutral-400 font-medium">Hebrew Keyboard</span>
            <button onClick={() => setShowGlobalKeyboard(false)}
              className="text-[10px] text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">✕</button>
          </div>
          {React.createElement(React.lazy(() => import('./HebrewKeyboard')), {
            value: '',
            onCharClick: (c) => {
              // Dispatch keyboard input event for any focused Hebrew input
              const el = document.activeElement
              if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                const start = el.selectionStart || 0
                const end = el.selectionEnd || 0
                el.value = el.value.substring(0, start) + c + el.value.substring(end)
                el.selectionStart = el.selectionEnd = start + c.length
                el.dispatchEvent(new Event('input', { bubbles: true }))
                el.focus()
              }
            },
            onBackspace: () => {
              const el = document.activeElement
              if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                const start = el.selectionStart || 0
                if (start > 0) {
                  el.value = el.value.substring(0, start - 1) + el.value.substring(el.selectionEnd || start)
                  el.selectionStart = el.selectionEnd = start - 1
                  el.dispatchEvent(new Event('input', { bubbles: true }))
                  el.focus()
                }
              }
            },
            onClear: () => {
              const el = document.activeElement
              if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA')) {
                el.value = ''
                el.dispatchEvent(new Event('input', { bubbles: true }))
                el.focus()
              }
            },
            onDone: () => setShowGlobalKeyboard(false),
          })}
        </div>
      )}

      {/* Mobile: Bottom Navigation — hidden when uiVisible is false (immersion mode) */}
      <MobileBottomNav activeTab={mobileActiveTab} visible={uiVisible} onTab={(tab) => {
        switch (tab) {
          case 'read': {
            setShowCommand(false); setShowMobileMenu(false)
            // "Read" must only land on a scripture-reading tab — a learn/hebrew/
            // wiki/memorize tab must not masquerade as Read (bug: showed Learn).
            const READ_VIEWS = ['chapter', 'book', 'work', 'library']
            const alreadyReading = READ_VIEWS.includes(currentTab?.view)
            const readTab = currentWorkspace?.tabs?.slice().reverse().find(t => READ_VIEWS.includes(t.view))
            if (readTab && readTab.id !== currentTab?.id) {
              selectTab(readTab.id)
            } else if (!alreadyReading) {
              // No other reading tab — exit any study/collection view to the grid
              setCollection(null); setStudyWeek(null)
              openLibraryView()
            }
            // Already reading where you left off — stay put.
            break
          }
          case 'chat': {
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); setHebrewLessonId(null)
            const chatTab = currentWorkspace?.tabs?.find(t => t.view === 'chat')
            if (chatTab) {
              selectTab(chatTab.id)
            } else {
              openChatTab()
            }
            break
          }
          case 'hebrew':
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); setHebrewLessonId(null); openHebrewTab()
            break
          case 'learn':
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); openLearnTab()
            break
          case 'memorize':
            setShowMobileMenu(false); setShowHebrewDiagnostic(false); openMemorizeTab()
            break
          case 'tiles':
            openTilesView(); setShowMobileMenu(false)
            break
          case 'command':
            setShowCommand(true); setShowMobileMenu(false)
            break
          case 'menu':
            setShowMobileMenu(p => !p)
            break
        }
      }} />

      {/* Mobile: Menu Drawer */}
      <MobileMenuDrawer
        open={showMobileMenu}
        onClose={() => setShowMobileMenu(false)}
        onArticles={() => { setShowMobileMenu(false); openArticlesTab() }}
        onWiki={() => { setShowMobileMenu(false); openWikiTab() }}
        onLayers={() => { setShowMobileMenu(false); setShowLayers(true) }}
        onHistory={() => { setShowMobileMenu(false); setShowHistory(true) }}
        onStructure={() => { setShowMobileMenu(false); setShowStructure(true) }}
        onHebrew={() => { setShowMobileMenu(false); setShowHebrewDiagnostic(true); setHebrewLessonId(null) }}
        onMemorize={() => { setShowMobileMenu(false); openMemorizeTab() }}
        onKnowledge={() => { setShowMobileMenu(false); openLearnTab() }}
        onHubNotes={() => { setShowMobileMenu(false); openHubNoteTab() }}
        onStudies={() => { setShowMobileMenu(false); openStudiesTab() }}
        darkMode={darkMode}
        onToggleDarkMode={toggleDarkMode}
        fontSize={fontSize}
        onChangeFontSize={changeFontSize}
        onSettings={() => { setShowMobileMenu(false); setShowSettings(true) }}
        authUser={userName || null}
        authAvatar={userAvatar || null}
        onSignIn={() => { setShowMobileMenu(false); document.querySelector('#google-signin-btn')?.click() }}
        onSignOut={handleSignOut}
      />

      {/* Spacer to prevent content from being hidden behind bottom nav — hidden when UI is hidden */}
      <div className={`sm:hidden transition-all duration-300 ${uiVisible ? 'h-14' : 'h-0'}`} />

    </>
  )
}
