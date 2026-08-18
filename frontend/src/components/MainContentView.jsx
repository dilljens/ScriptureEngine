import React, { Suspense } from 'react'
import { getBooks } from '../api'
import ErrorBoundary from './ErrorBoundary'
import ChapterView from './ChapterView'
import BookView from './BookView'
import WorkView from './WorkView'
import LibraryView from './LibraryView'
import CollectionView from './CollectionView'
import CfmStudyView from './CfmStudyView'
import ConversationHistory from './ConversationHistory'
import TileDashboard from './TileDashboard'
import { useTabs, useSettings } from '../tabContext.jsx'
import { useToggles } from './ToggleProvider'

const ChatPanel = React.lazy(() => import('./ChatPanel'))
const StudyViewer = React.lazy(() => import('./StudyViewer'))
const HubNoteView = React.lazy(() => import('./HubNoteView'))
const MemorizeView = React.lazy(() => import('./MemorizeView'))
const HebrewDiagnostic = React.lazy(() => import('./HebrewDiagnostic'))
const HebrewLessonView = React.lazy(() => import('./HebrewLessonView'))
const HebrewLearnView = React.lazy(() => import('./HebrewLearnView'))
const WikiArticleViewer = React.lazy(() => import('./WikiArticleViewer'))
const HebrewPassageReader = React.lazy(() => import('./HebrewPassageReader'))
const LearnView = React.lazy(() => import('./LearnView'))
const StudiesListView = React.lazy(() => import('./StudiesListView'))

/**
 * MainContentView — renders the active tab's view (chapter, book, work,
 * library, chat, wiki, hebrew, memorize, study, tiles, ...).
 *
 * Extracted from App.jsx to break the god-file: App.jsx's fan-out (30+
 * component imports) triggered sentrux no_god_files, and this switch was
 * AppInner's biggest cyclomatic-complexity contributor. The view state
 * comes from the tab/settings/toggles contexts; the remaining AppInner
 * UI state (diagnostic/lesson/history/study overrides) arrives via props.
 */
export default function MainContentView(props) {
  const {
    bookData, bookError, chatInitialMsg, collection, hebrewLessonId,
    hubNoteId, passageStudyRef, readingLessonId, poetryMode,
    showHebrewDiagnostic, showHebrewLearn, showHistory, showHubNotes,
    studyWeek, userId,
    setBookData, setBookError, setChatInitialMsg, setCollection,
    setHebrewLessonId, setPassageStudyRef, setReadingLessonId, setShowChat,
    setShowHebrewDiagnostic, setShowHebrewLearn, setShowHistory, setStudyWeek,
    handleChatNavigate, handleChatOpenTab, handleOpenSplitPicker,
    navigateRef, studyFromCollection,
  } = props

  const {
    currentTab, viewLevel, updateTab, openTab, workspaces, activeWorkspace, activeTab,
    selectWorkspace, goToBook, goToWork, openHebrewTab, openHubNoteTab, openLearnTab,
    openMemorizeTab, openWikiTab, selectTab, closeTab, moveTab,
  } = useTabs()
  const { showQuickAsk } = useSettings()
  const { dispatch } = useToggles()

  const book = currentTab?.book || 'isa'
  const chapter = currentTab?.chapter || 1
  const viewRef = currentTab?.viewRef ?? null
  const bookTitle = book
  const highlightVerse = currentTab?.highlights?.[0] || null

  if (showHebrewDiagnostic) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading diagnostic...</div>}>
        <HebrewDiagnostic onComplete={() => { setShowHebrewDiagnostic(false); setShowHebrewLearn(true) }} />
      </Suspense>
    )
  }
  if (hebrewLessonId !== null) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading lesson...</div>}>
        <HebrewLessonView nodeId={hebrewLessonId} onBack={() => setHebrewLessonId(null)} />
      </Suspense>
    )
  }
  if (showHubNotes) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading paths...</div>}>
        <HubNoteView hubId={hubNoteId} onNavigate={(v) => navigateRef(v)} onGraph={(v) => window.open(`/graph?verse=${v}`, '_blank')} />
      </Suspense>
    )
  }
  if (showHebrewLearn) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading curriculum...</div>}>
        <HebrewLearnView onOpenLesson={(nodeId) => setHebrewLessonId(nodeId)} onOpenPassage={(ref, lessonId) => { setPassageStudyRef(ref); setReadingLessonId(lessonId || null) }} />
      </Suspense>
    )
  }
  if (showHistory) return <ErrorBoundary><ConversationHistory onNavigate={handleChatNavigate} onClose={() => setShowHistory(false)} /></ErrorBoundary>
  if (viewLevel === 'library') {
    if (studyWeek) {
      return (
        <CfmStudyView
          week={studyWeek === 'current' ? null : studyWeek}
          onBack={() => { setStudyWeek(null); setCollection(null) }}
          onBrowse={() => { setStudyWeek(null); setCollection('cfm') }}
          onNavigate={(b, ch) => handleChatNavigate(b, ch)}
          onStudyInChat={studyFromCollection}
        />
      )
    }
    if (collection) {
      return <CollectionView collection={collection} onBack={() => setCollection(null)} onStudyInChat={studyFromCollection} onStudy={(slug) => { setCollection(null); setStudyWeek(slug) }} />
    }
    return <LibraryView bookData={bookData} bookError={bookError} onRetry={() => { setBookError(null); getBooks().then(r => { setBookData(r.data); window.__bookData = r.data }).catch(() => { setBookError('Still could not load.') }) }} onNavigate={handleChatNavigate} onOpenCollection={setCollection} onOpenStudy={() => { setCollection(null); setStudyWeek('current') }} />
  }
  if (viewLevel === 'work' && viewRef) return <WorkView workId={viewRef} />
  if (viewLevel === 'book') return <BookView bookId={book} />
  // Chat view — render ChatPanel inline
  if (viewLevel === 'chat') {
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400">Loading chat...</div>}>
        <ChatPanel
        variant="tab"
        open={true}
        initialMessage={chatInitialMsg}
        onNavigate={handleChatNavigate}
        onOpenTab={handleChatOpenTab}
        onClose={() => {}}
      />
    </Suspense>
    )
  }
  // Memorize view
  if (viewLevel === 'memorize') {
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400">Loading memorize...</div>}>
        <MemorizeView />
      </Suspense>
    )
  }
  // Tiles view — subject/chapter dashboard
  if (viewLevel === 'tiles') {
    return (
      <TileDashboard
        workspaces={workspaces}
        activeWorkspace={activeWorkspace}
        activeTab={activeTab}
        onSelectWorkspace={selectWorkspace}
        onNewWorkspace={newWorkspace}
        onRenameWorkspace={renameWorkspace}
        onDeleteWorkspace={deleteWorkspace}
        onDeleteWorkspaces={deleteWorkspaces}
        onReorderWorkspaces={reorderWorkspaces}
        onSelectTab={selectTab}
        onCloseTab={closeTab}
        onMoveTab={moveTab}
        onOpenTab={openTab}
        book={book} chapter={chapter} bookTitle={bookTitle}
      />
    )
  }
  // Wiki view — render WikiArticleViewer
  if (viewLevel === 'wiki') {
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading wiki...</div>}>
        <WikiArticleViewer
          entityId={viewRef}
          onNavigate={(eid) => updateTab(currentTab?.id, { view: 'wiki', viewRef: eid, label: `Wiki: ${eid}` })}
          onOpenTab={(b, ch, opts) => openTab(b, ch, opts)}
        />
      </Suspense>
    )
  }

  // Passage study view — Hebrew word-by-word reader
  if (viewLevel === 'passage-study' && viewRef) {
    return (
      <Suspense fallback={<div className="p-8 text-sm text-neutral-400 animate-pulse">Loading passage reader...</div>}>
        <HebrewPassageReader verseRef={viewRef} onClose={() => dispatch({ type: 'CLOSE_TAB' })} />
      </Suspense>
    )
  }

  // HubNote tab view
  if (viewLevel === 'hubnote') {
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading study path...</div>}>
        <HubNoteView hubId={viewRef} onNavigate={(v) => navigateRef(v)} onGraph={(v) => window.open(`/graph?verse=${v}`, '_blank')} />
      </Suspense>
    )
  }

  // Hebrew view — if viewRef is set, show lesson; otherwise show curriculum
  if (viewLevel === 'hebrew') {
    if (viewRef && typeof viewRef === 'string' && !viewRef.startsWith('heb-')) {
      const HebrewLessonView = React.lazy(() => import('./components/HebrewLessonView'))
      return (
        <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading lesson...</div>}>
          <HebrewLessonView
            nodeId={viewRef}
            onBack={(fallbackNodeId) => {
              if (currentTab?.id) {
                if (fallbackNodeId) {
                  updateTab(currentTab.id, { viewRef: fallbackNodeId, label: `Hebrew: ${fallbackNodeId}` })
                } else {
                  updateTab(currentTab.id, { viewRef: null, label: 'Biblical Hebrew' })
                }
              }
            }}
            onNavigate={(verseId) => {
              const parts = verseId.split('.')
              if (parts.length >= 2) {
                handleChatNavigate?.(parts[0], parseInt(parts[1]) || 1)
              }
            }}
          />
        </Suspense>
      )
    }
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading Hebrew...</div>}>
        <HebrewLearnView onOpenLesson={(nodeId) => {
          if (currentTab?.id) updateTab(currentTab.id, { viewRef: nodeId, label: `Hebrew: ${nodeId}` })
        }} />
      </Suspense>
    )
  }

  // Learn view
  if (viewLevel === 'learn') {
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading learn...</div>}>
        <LearnView userId={userId} onBack={() => {}} />
      </Suspense>
    )
  }

  // Studies list view
  if (viewLevel === 'studies') {
    const StudiesListView = React.lazy(() => import('./components/StudiesListView'))
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400 animate-pulse">Loading studies...</div>}>
        <StudiesListView onOpenStudy={(slug, title) => {
          const label = title || `Study: ${slug}`
          openTab(slug, 1, { view: 'study', viewRef: slug, label })
        }} />
      </Suspense>
    )
  }

  // Study view — render StudyViewer
  if (viewLevel === 'study' && viewRef) {
    // Load study from API using the slug
    const fetchStudy = async () => {
      const res = await fetch(`/api/v1/studies/published/${viewRef}`)
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Failed to load study')
      return data.data
    }
    return (
      <Suspense fallback={<div className="p-4 text-sm text-neutral-400">Loading study...</div>}>
        <StudyViewer
          onFetch={fetchStudy}
          onNavigate={handleChatNavigate}
          onOpenTab={(b, ch, opts) => openTab(b, ch, opts)}
          showQuickAsk={showQuickAsk}
          onChatOpen={(msg) => { setChatInitialMsg(msg); setShowChat(true) }}
          guideId={null}
        />
      </Suspense>
    )
  }
  // Split-pane reading: if companion is set, render two ChapterViews side by side
  const companion = currentTab?.companion
  if (companion?.book && companion?.chapter) {
    return (
      <div className="flex h-full">
        <div className="flex-1 min-w-0 overflow-y-auto border-r border-neutral-200 dark:border-neutral-700">
          <ChapterView book={book} chapter={chapter} poetryMode={poetryMode} highlightVerse={highlightVerse}
            onSplit={null}
            companionLabel={null}
            onCloseCompanion={() => {
              if (currentTab?.id) updateTab(currentTab.id, { companion: null })
            }} />
        </div>
        <div className="flex-1 min-w-0 overflow-y-auto bg-neutral-50/50 dark:bg-neutral-900/50">
          <ChapterView book={companion.book} chapter={companion.chapter} poetryMode={poetryMode} highlightVerse={null}
            onSplit={null}
            companionLabel={`${companion.book} ${companion.chapter}`}
            onCloseCompanion={() => {
              if (currentTab?.id) updateTab(currentTab.id, { companion: null })
            }} />
        </div>
      </div>
    )
  }
  return <ChapterView book={book} chapter={chapter} poetryMode={poetryMode} highlightVerse={highlightVerse}
    onSplit={handleOpenSplitPicker}
    companionLabel={null}
    onCloseCompanion={null} />
}
