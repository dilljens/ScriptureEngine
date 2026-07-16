import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { getWikiArticle, getWikiBrowse, getWikiSearch } from '../api'
import { preprocess, createComponents } from '../lib/scripture-markdown'

/**
 * WikiArticleViewer — Wikipedia-style wiki viewer with sidebar, search, and browse.
 *
 * Layout:
 * ┌─────────────────────────────────────────────┐
 * │  [≡ sidebar toggle]  Wiki Search [________] │  ← top bar
 * ├──────────┬──────────────────────────────────┤
 * │ SIDEBAR  │  MAIN CONTENT                    │
 * │          │                                  │
 * │ Browse:  │  Article / Browse / Search       │
 * │  Entities│  results                         │
 * │  Books   │                                  │
 * │  Works   │                                  │
 * │  Layers  │                                  │
 * │          │                                  │
 * │ Index:   │                                  │
 │  A B C D  │                                  │
 * │  E F G H │                                  │
 * └──────────┴──────────────────────────────────┘
 */
const TYPE_ICONS = {
  person: '👤',
  place: '📍',
  concept: '💡',
  title: '👑',
  being: '✨',
}

const TYPE_COLORS = {
  person: { bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300', border: 'border-blue-200 dark:border-blue-800' },
  place: { bg: 'bg-green-50 dark:bg-green-900/20', text: 'text-green-700 dark:text-green-300', border: 'border-green-200 dark:border-green-800' },
  concept: { bg: 'bg-purple-50 dark:bg-purple-900/20', text: 'text-purple-700 dark:text-purple-300', border: 'border-purple-200 dark:border-purple-800' },
  title: { bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-300', border: 'border-amber-200 dark:border-amber-800' },
  being: { bg: 'bg-indigo-50 dark:bg-indigo-900/20', text: 'text-indigo-700 dark:text-indigo-300', border: 'border-indigo-200 dark:border-indigo-800' },
}

// Browse categories available in the sidebar
const BROWSE_CATEGORIES = [
  { key: 'entity', label: 'Entities', icon: '📖' },
  { key: 'book', label: 'Books', icon: '📚' },
  { key: 'doctrine', label: 'Doctrines', icon: '💡' },
  { key: 'work', label: 'Works', icon: '📜' },
  { key: 'layer', label: 'Layers', icon: '🔗' },
  { key: 'language', label: 'Languages', icon: '🔤' },
]

// Alphabet for the index
const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

/** Handle verse navigation from wiki content */
function handleWikiVerse(ref) {
  window.dispatchEvent(new CustomEvent('scripture-navigate', {
    detail: { ref }
  }))
}

export default function WikiArticleViewer({ entityId, browseType, searchQuery, onNavigate, onOpenTab }) {
  const [article, setArticle] = useState(null)
  const [browseResults, setBrowseResults] = useState([])
  const [searchResults, setSearchResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState(entityId ? 'article' : searchQuery ? 'search' : 'browse')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sidebarSearch, setSidebarSearch] = useState('')
  const [activeCategory, setActiveCategory] = useState(browseType || 'entity')
  const [allArticles, setAllArticles] = useState([])  // Full list for sidebar index
  const [alphaFilter, setAlphaFilter] = useState('')
  const searchInputRef = useRef(null)

  // ── Data fetching ──

  // Fetch article
  useEffect(() => {
    if (!entityId) return
    setLoading(true); setError(null); setActiveTab('article')
    getWikiArticle(entityId)
      .then(res => {
        if (res.ok && res.data) setArticle(res.data)
        else setError(res.error || 'Article not found')
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [entityId])

  // Fetch full article list for sidebar (all categories)
  useEffect(() => {
    getWikiBrowse('entity')
      .then(res => {
        if (res.ok && res.data) setAllArticles(prev => {
          const existing = new Map(prev.map(a => [a.id, a]))
          for (const a of (res.data.articles || [])) existing.set(a.id, a)
          return [...existing.values()]
        })
      })
      .catch(() => {})
  }, [])

  // Fetch browse list when category changes
  useEffect(() => {
    if (activeTab === 'article' && entityId) return
    setLoading(true)
    getWikiBrowse(activeCategory)
      .then(res => {
        if (res.ok && res.data) {
          const articles = res.data.articles || []
          setBrowseResults(articles)
          // Also merge into allArticles for index
          setAllArticles(prev => {
            const existing = new Map(prev.map(a => [a.id, a]))
            for (const a of articles) existing.set(a.id, a)
            return [...existing.values()]
          })
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [activeCategory, entityId, activeTab])

  // Search
  const doSearch = useCallback((q) => {
    if (!q || q.length < 2) {
      setSearchResults([])
      if (!entityId) setActiveTab('browse')
      return
    }
    setLoading(true); setActiveTab('search')
    getWikiSearch(q)
      .then(res => {
        if (res.ok && res.data) setSearchResults(res.data.results || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [entityId])

  // Handle sidebar search
  const handleSidebarSearch = useCallback((e) => {
    const val = e.target.value
    setSidebarSearch(val)
    doSearch(val)
  }, [doSearch])

  const handleEntityClick = useCallback((eid) => {
    setArticle(null)
    setActiveTab('article')
    if (onNavigate) onNavigate(eid)
  }, [onNavigate])

  // ── Sidebar article list (filtered) ──

  const sidebarArticles = useMemo(() => {
    let items = browseResults.length > 0 ? browseResults : allArticles
    if (alphaFilter) {
      items = items.filter(a => a.title?.[0]?.toUpperCase() === alphaFilter)
    }
    // Sort alphabetically
    return [...items].sort((a, b) => (a.title || '').localeCompare(b.title || ''))
  }, [browseResults, allArticles, alphaFilter])

  // Active category label
  const activeCategoryLabel = BROWSE_CATEGORIES.find(c => c.key === activeCategory)?.label || activeCategory
  const activeCategoryIcon = BROWSE_CATEGORIES.find(c => c.key === activeCategory)?.icon || '📖'

  // ── Loading state ──
  if (loading && activeTab === 'article' && !article) return (
    <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500 text-sm">
      <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
      Loading wiki article…
    </div>
  )

  // ── Error state ──
  if (error && !article) return (
    <div className="flex h-full">
      {/* Sidebar (always visible on error) */}
      <SidebarPanel
        sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen}
        sidebarSearch={sidebarSearch} handleSidebarSearch={handleSidebarSearch}
        searchInputRef={searchInputRef}
        activeCategory={activeCategory} setActiveCategory={setActiveCategory}
        alphaFilter={alphaFilter} setAlphaFilter={setAlphaFilter}
        sidebarArticles={sidebarArticles} handleEntityClick={handleEntityClick}
        activeCategoryLabel={activeCategoryLabel} activeCategoryIcon={activeCategoryIcon}
        currentEntityId={entityId}
      />
      <div className="flex-1 p-6">
        <div className="max-w-3xl mx-auto p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
          {error}
          <button onClick={() => window.location.reload()} className="ml-3 underline hover:text-red-800 cursor-pointer">Retry</button>
        </div>
      </div>
    </div>
  )

  // ── Main render: two-column layout ──
  return (
    <div className="flex h-full">
      {/* Left Sidebar */}
      <SidebarPanel
        sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen}
        sidebarSearch={sidebarSearch} handleSidebarSearch={handleSidebarSearch}
        searchInputRef={searchInputRef}
        activeCategory={activeCategory} setActiveCategory={setActiveCategory}
        alphaFilter={alphaFilter} setAlphaFilter={setAlphaFilter}
        sidebarArticles={sidebarArticles} handleEntityClick={handleEntityClick}
        activeCategoryLabel={activeCategoryLabel} activeCategoryIcon={activeCategoryIcon}
        currentEntityId={entityId}
      />

      {/* Main Content */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        {/* Top bar with mobile sidebar toggle + search */}
        <div className="sticky top-0 z-10 bg-white/80 dark:bg-neutral-900/80 backdrop-blur-sm border-b border-neutral-200 dark:border-neutral-700 px-3 py-2 flex items-center gap-2">
          <button onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-500 dark:text-neutral-400 cursor-pointer"
            title="Toggle sidebar">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          <div className="flex-1" />
          <div className="relative max-w-xs w-full">
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search wiki…"
              value={sidebarSearch}
              onChange={handleSidebarSearch}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            {sidebarSearch && (
              <button onClick={() => { setSidebarSearch(''); setSearchResults([]); setActiveTab(entityId ? 'article' : 'browse') }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 cursor-pointer">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            )}
          </div>
        </div>

        {/* Content area */}
        <div className="p-4 md:p-6">
          {renderContent()}
        </div>
      </div>
    </div>
  )

  // ── Content router ──
  function renderContent() {
    // Article view
    if (activeTab === 'article' && article) return <ArticleView article={article} onEntityClick={handleEntityClick} onOpenTab={onOpenTab} />

    // Search results
    if (activeTab === 'search' && sidebarSearch && sidebarSearch.length >= 2) {
      if (searchResults.length === 0 && !loading) {
        return (
          <div className="max-w-3xl mx-auto text-center py-16 text-neutral-400 dark:text-neutral-500">
            <p className="text-sm">No wiki articles found for "<strong>{sidebarSearch}</strong>"</p>
          </div>
        )
      }
      if (searchResults.length > 0) {
        return (
          <div className="max-w-3xl mx-auto">
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-3">
              Wiki Search: "<strong>{sidebarSearch}</strong>" — {searchResults.length} result{searchResults.length !== 1 ? 's' : ''}
            </h2>
            <div className="space-y-1.5">
              {searchResults.map(r => (
                <button key={r.id} onClick={() => handleEntityClick(r.id)}
                  className="w-full text-left p-2.5 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-colors">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-blue-600 dark:text-blue-400">{r.title}</span>
                    {r.article_type && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">
                        {r.article_type}
                      </span>
                    )}
                  </div>
                  {r.summary && <div className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-2">{r.summary}</div>}
                </button>
              ))}
            </div>
          </div>
        )
      }
    }

    // Browse view (default when no article or search)
    return (
      <div className="max-w-3xl mx-auto">
        <div className="mb-4">
          <h2 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">
            Browse <strong className="text-neutral-800 dark:text-neutral-200">{activeCategoryLabel}</strong>
          </h2>
          <p className="text-[11px] text-neutral-400 dark:text-neutral-500 mt-0.5">
            {sidebarArticles.length} article{sidebarArticles.length !== 1 ? 's' : ''}
            {alphaFilter ? ` starting with "${alphaFilter}"` : ''}
          </p>
        </div>
        <div className="space-y-1">
          {sidebarArticles.map(a => (
            <button key={a.id} onClick={() => handleEntityClick(a.id)}
              className="w-full text-left p-2.5 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-colors">
              <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{a.title}</div>
              {a.summary && <div className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-1">{a.summary}</div>}
            </button>
          ))}
          {sidebarArticles.length === 0 && !loading && (
            <div className="text-center py-12 text-neutral-400 dark:text-neutral-500 text-sm">
              No articles found in this category.
            </div>
          )}
        </div>
      </div>
    )
  }
}


// ═══════════════════════════════════════════════════════════════════════
// Sidebar Panel Component
// ═══════════════════════════════════════════════════════════════════════

function SidebarPanel({
  sidebarOpen, setSidebarOpen,
  sidebarSearch, handleSidebarSearch,
  searchInputRef,
  activeCategory, setActiveCategory,
  alphaFilter, setAlphaFilter,
  sidebarArticles, handleEntityClick,
  activeCategoryLabel, activeCategoryIcon,
  currentEntityId,
}) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <>
      {/* Desktop sidebar */}
      <aside className={`hidden md:flex flex-col border-r border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 transition-all duration-200 ${sidebarOpen ? 'w-64' : 'w-0 overflow-hidden'}`}>
        {sidebarOpen && (
          <div className="flex flex-col h-full">
            {/* Sidebar header */}
            <div className="p-3 border-b border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xs font-semibold text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Wiki</h2>
                <button onClick={() => setSidebarOpen(false)}
                  className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600 cursor-pointer">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" /></svg>
                </button>
              </div>
              {/* Sidebar search */}
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search articles…"
                  value={sidebarSearch}
                  onChange={handleSidebarSearch}
                  className="w-full pl-7 pr-2 py-1.5 text-xs rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-blue-400"
                />
                <svg className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              </div>
            </div>

            {/* Browse categories */}
            <div className="px-3 py-2 border-b border-neutral-100 dark:border-neutral-800">
              <div className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1.5">Browse</div>
              <div className="flex flex-wrap gap-1">
                {BROWSE_CATEGORIES.map(cat => (
                  <button key={cat.key} onClick={() => { setActiveCategory(cat.key); setAlphaFilter('') }}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors cursor-pointer ${
                      activeCategory === cat.key
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                        : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700'
                    }`}>
                    {cat.icon} {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Alphabet index */}
            <div className="px-3 py-1.5 border-b border-neutral-100 dark:border-neutral-800">
              <div className="flex flex-wrap gap-0.5">
                <button onClick={() => setAlphaFilter('')}
                  className={`w-5 h-5 flex items-center justify-center rounded text-[9px] font-medium cursor-pointer ${
                    !alphaFilter ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                  }`}>ALL</button>
                {ALPHABET.map(l => (
                  <button key={l} onClick={() => setAlphaFilter(alphaFilter === l ? '' : l)}
                    className={`w-5 h-5 flex items-center justify-center rounded text-[9px] font-medium cursor-pointer ${
                      alphaFilter === l ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                    }`}>{l}</button>
                ))}
              </div>
            </div>

            {/* Article list */}
            <div className="flex-1 overflow-y-auto">
              <div className="px-3 py-2">
                <div className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1.5">
                  {activeCategoryIcon} {activeCategoryLabel} ({sidebarArticles.length})
                </div>
                <div className="space-y-0.5">
                  {sidebarArticles.map(a => (
                    <button key={a.id} onClick={() => handleEntityClick(a.id)}
                      className={`w-full text-left px-2 py-1 rounded text-[11px] transition-colors cursor-pointer ${
                        currentEntityId === a.id
                          ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 font-medium'
                          : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-800 dark:hover:text-neutral-200'
                      }`}>
                      <span className="truncate block">{a.title}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSidebarOpen(false)} />
          <aside className="relative z-10 w-72 bg-white dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-700 overflow-y-auto">
            <div className="p-3 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
              <h2 className="text-xs font-semibold text-neutral-600 dark:text-neutral-400 uppercase tracking-wider">Wiki</h2>
              <button onClick={() => setSidebarOpen(false)}
                className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 cursor-pointer">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
            <div className="p-3">
              <input
                type="text"
                placeholder="Search articles…"
                value={sidebarSearch}
                onChange={handleSidebarSearch}
                className="w-full pl-7 pr-2 py-1.5 text-xs rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 placeholder-neutral-400 dark:placeholder-neutral-500 focus:outline-none focus:ring-1 focus:ring-blue-400"
              />
            </div>
            <div className="px-3 pb-2">
              <div className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1">Browse</div>
              <div className="flex flex-wrap gap-1">
                {BROWSE_CATEGORIES.map(cat => (
                  <button key={cat.key} onClick={() => { setActiveCategory(cat.key); setSidebarOpen(false) }}
                    className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors cursor-pointer ${
                      activeCategory === cat.key
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                        : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400'
                    }`}>
                    {cat.icon} {cat.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="px-3 pb-3">
              <div className="text-[9px] font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-1">
                {activeCategoryIcon} {activeCategoryLabel} ({sidebarArticles.length})
              </div>
              <div className="space-y-0.5 max-h-[50vh] overflow-y-auto">
                {sidebarArticles.slice(0, 50).map(a => (
                  <button key={a.id} onClick={() => { handleEntityClick(a.id); setSidebarOpen(false) }}
                    className={`w-full text-left px-2 py-1 rounded text-[11px] transition-colors cursor-pointer ${
                      currentEntityId === a.id
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 font-medium'
                        : 'text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'
                    }`}>
                    {a.title}
                  </button>
                ))}
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  )
}


// ═══════════════════════════════════════════════════════════════════════
// Article View Component
// ═══════════════════════════════════════════════════════════════════════

function ArticleView({ article, onEntityClick, onOpenTab }) {
  const colors = TYPE_COLORS[article.article_type] || TYPE_COLORS.concept
  const icon = TYPE_ICONS[article.article_type] || '📖'

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className={`mb-5 p-4 rounded-lg border ${colors.border} ${colors.bg}`}>
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">{article.title}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                {article.article_type}
              </span>
              {article.summary && (
                <span className="text-[11px] text-neutral-500 dark:text-neutral-400 line-clamp-1">{article.summary}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Article Content (Markdown) */}
      <div className="prose prose-sm dark:prose-invert max-w-none
        prose-headings:text-neutral-800 dark:prose-headings:text-neutral-200
        prose-a:text-blue-600 dark:prose-a:text-blue-400
        prose-strong:text-neutral-800 dark:prose-strong:text-neutral-200
        prose-code:text-[11px] prose-code:bg-neutral-100 dark:prose-code:bg-neutral-800 prose-code:px-1 prose-code:rounded
        prose-td:text-[12px] prose-th:text-[11px]
        prose-table:border-collapse prose-table:border prose-table:border-neutral-200 dark:prose-table:border-neutral-700
        prose-th:bg-neutral-50 dark:prose-th:bg-neutral-800 prose-th:px-2 prose-th:py-1
        prose-td:px-2 prose-td:py-1 prose-td:border prose-td:border-neutral-200 dark:prose-td:border-neutral-700
        prose-blockquote:text-neutral-500 dark:prose-blockquote:text-neutral-400 prose-blockquote:border-l-neutral-300 dark:prose-blockquote:border-l-neutral-600">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw]}
          components={createComponents({
            onOpenVerse: handleWikiVerse,
            customComponents: {
              img: ({ src, alt }) => src?.startsWith('http') ? (
                <img src={src} alt={alt} className="max-w-sm rounded-lg shadow-md my-4" loading="lazy" />
              ) : null,
            },
          })}>
          {preprocess(article.content || '')}
        </ReactMarkdown>
      </div>

      {/* Key Verses */}
      {article.key_verses?.length > 0 && (
        <div className="mt-5 p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800/30">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">Key Verses</h3>
          <div className="flex flex-wrap gap-1.5">
            {article.key_verses.map((v, i) => (
              <span key={i}
                className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 text-[10px] font-mono cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors"
                onClick={() => {
                  const parts = v.split('.')
                  if (parts.length >= 2 && onOpenTab) onOpenTab(parts[0], parseInt(parts[1]), { verse: parseInt(parts[2] || '1') })
                }}>
                {v}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Related Entities */}
      {article.cross_references?.length > 0 && (
        <div className="mt-4">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">Related Entities</h3>
          <div className="flex flex-wrap gap-1.5">
            {article.cross_references.map((ref, i) => (
              <button key={i} onClick={() => onEntityClick(ref)}
                className="px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 text-[10px] font-medium border border-amber-200 dark:border-amber-800 cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors">
                {ref}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Test Yourself */}
      {article.id && (
        <div className="mt-4">
          <a href={`/api/v1/assess/entity/${article.id}`}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium transition-colors cursor-pointer"
            onClick={(e) => {
              e.preventDefault()
              if (onOpenTab) onOpenTab('assessment', 1, { entityId: article.id, label: `Test: ${article.title}` })
            }}>
            Test Yourself on {article.title}
          </a>
          {article.total_connections > 0 && (
            <span className="ml-3 text-[11px] text-neutral-400 dark:text-neutral-500">
              {article.total_connections} connections in knowledge graph
            </span>
          )}
        </div>
      )}
    </div>
  )
}
