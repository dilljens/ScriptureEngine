import React, { useState, useEffect, useMemo, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { getWikiArticle, getWikiBrowse, getWikiSearch } from '../api'
import { preprocess, createComponents } from '../lib/scripture-markdown'

/**
 * WikiArticleViewer — renders a wiki article about a biblical entity.
 *
 * Supports:
 * - Direct entity lookup (entityId prop)
 * - Entity browsing by type (browseType prop)
 * - Search (searchQuery prop)
 * - Markdown rendering with verse refs
 * - Related entity cross-links
 * - "Test Yourself" assessment link
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

  // Fetch article
  useEffect(() => {
    if (!entityId) return
    setLoading(true); setError(null)
    getWikiArticle(entityId)
      .then(res => {
        if (res.ok && res.data) setArticle(res.data)
        else setError(res.error || 'Article not found')
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [entityId])

  // Fetch browse list
  useEffect(() => {
    if (!browseType || entityId) return
    setLoading(true)
    getWikiBrowse(browseType)
      .then(res => {
        if (res.ok && res.data) setBrowseResults(res.data.articles || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [browseType, entityId])

  // Search
  useEffect(() => {
    if (!searchQuery) return
    setLoading(true); setActiveTab('search')
    getWikiSearch(searchQuery)
      .then(res => {
        if (res.ok && res.data) setSearchResults(res.data.results || [])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [searchQuery])

  const handleEntityClick = useCallback((eid) => {
    if (onNavigate) onNavigate(eid)
  }, [onNavigate])

  if (loading) return (
    <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500 text-sm">
      <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
      Loading wiki article…
    </div>
  )

  if (error) return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
        {error}
        <button onClick={() => window.location.reload()} className="ml-3 underline hover:text-red-800 cursor-pointer">Retry</button>
      </div>
    </div>
  )

  // ── Entity Browser ──
  if (activeTab === 'browse' && browseResults.length > 0) {
    const byType = {}
    for (const a of browseResults) {
      const t = a.article_type || 'entity'
      if (!byType[t]) byType[t] = []
      byType[t].push(a)
    }

    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-4">
          Wiki — Browse {browseType}
        </h2>
        <div className="space-y-6">
          {Object.entries(byType).map(([type, articles]) => (
            <div key={type}>
              <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                {TYPE_ICONS[type] || '📖'} {type}s ({articles.length})
              </h3>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {articles.map(a => (
                  <button key={a.id} onClick={() => handleEntityClick(a.id)}
                    className="text-left p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-colors">
                    <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{a.title}</div>
                    {a.summary && <div className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">{a.summary}</div>}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── Search Results ──
  if (activeTab === 'search' && searchResults.length > 0) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-4">
          Wiki Search: "{searchQuery}"
        </h2>
        <div className="space-y-2">
          {searchResults.map(r => (
            <button key={r.id} onClick={() => handleEntityClick(r.id)}
              className="w-full text-left p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-blue-300 dark:hover:border-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-colors">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-blue-600 dark:text-blue-400">{r.title}</span>
                {r.article_type && (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">
                    {r.article_type}
                  </span>
                )}
              </div>
              {r.summary && <div className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-1 line-clamp-2">{r.summary}</div>}
            </button>
          ))}
        </div>
      </div>
    )
  }

  // ── No article / empty state ──
  if (!article) return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="text-center py-20 text-neutral-400 dark:text-neutral-500">
        <p className="text-sm">Select an entity from the sidebar or search to view its wiki article</p>
      </div>
    </div>
  )

  // ── Article View ──
  const colors = TYPE_COLORS[article.article_type] || TYPE_COLORS.concept
  const icon = TYPE_ICONS[article.article_type] || '📖'

  return (
    <div className="max-w-4xl mx-auto px-6 py-6">
      {/* Header */}
      <div className={`mb-6 p-4 rounded-lg border ${colors.border} ${colors.bg}`}>
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{icon}</span>
          <div>
            <h1 className="text-xl font-bold text-neutral-900 dark:text-neutral-100">{article.title}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${colors.bg} ${colors.text}`}>
                {article.article_type}
              </span>
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
        <div className="mt-6 p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800/30">
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

      {/* Test Yourself */}
      <div className="mt-6 flex items-center gap-3">
        <a href={`/api/v1/assess/entity/${article.id}`}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium transition-colors cursor-pointer"
          onClick={(e) => {
            e.preventDefault()
            if (onOpenTab) onOpenTab('assessment', 1, { entityId: article.id, label: `Test: ${article.title}` })
          }}>
          Test Yourself on {article.title}
        </a>
        {article.total_connections > 0 && (
          <span className="text-[11px] text-neutral-400 dark:text-neutral-500">
            {article.total_connections} connections in the knowledge graph
          </span>
        )}
      </div>

      {/* Cross-references */}
      {article.cross_references?.length > 0 && (
        <div className="mt-4">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-2">Related Entities</h3>
          <div className="flex flex-wrap gap-1.5">
            {article.cross_references.map((ref, i) => (
              <button key={i} onClick={() => handleEntityClick(ref)}
                className="px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 text-[10px] font-medium border border-amber-200 dark:border-amber-800 cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors">
                {ref}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
