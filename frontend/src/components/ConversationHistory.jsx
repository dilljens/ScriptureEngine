/**
 * ConversationHistory — Review past LLM conversations and their connections.
 *
 * Two modes:
 *   LIST — browse all past sessions (paginated, searchable)
 *   DETAIL — view a session's messages + extracted connections side by side
 *
 * Connections are split into:
 *   - Retrieved (existing in graph, grey)
 *   - Discovered (new, highlighted with Promote button)
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  conversationList, conversationGet, conversationUpdate,
  conversationDelete, conversationConnections
} from '../api'

const PER_PAGE = 20

// ── Verse ref styling ──
function linkRefs(text, onNavigate) {
  const parts = text.split(/([a-z0-9_]+\.\d+\.\d+)/gi)
  return parts.map((part, i) => {
    const m = part.match(/^([a-z0-9_]+)\.(\d+)\.(\d+)$/i)
    if (m) {
      return (
        <button key={i} onClick={() => onNavigate(m[1].toLowerCase(), parseInt(m[2]))}
          className="text-blue-600 hover:text-blue-800 underline font-medium cursor-pointer">
          {part}
        </button>
      )
    }
    return part
  })
}


// ── Connection Badge ──

function ConnectionBadge({ type }) {
  const colors = {
    retrieved: 'bg-neutral-100 text-neutral-600 border-neutral-300',
    discovered: 'bg-amber-50 text-amber-700 border-amber-300',
    suggested: 'bg-blue-50 text-blue-700 border-blue-300',
  }
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${colors[type] || colors.discovered}`}>
      {type}
    </span>
  )
}


// ── Main Component ──

export default function ConversationHistory({ onNavigate, onClose }) {
  const [mode, setMode] = useState('list')       // 'list' | 'detail'
  const [sessions, setSessions] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  // Detail state
  const [detail, setDetail] = useState(null)      // full session data
  const [connections, setConnections] = useState([])
  const [promoting, setPromoting] = useState(null) // connection id being promoted
  const [promoteForm, setPromoteForm] = useState(null) // {id, source, target} for modal

  // Fetch sessions
  const fetchList = useCallback(async (p = 1, q = '') => {
    setLoading(true)
    try {
      const res = await conversationList(p, PER_PAGE)
      if (res.ok && res.data) {
        setSessions(res.data.sessions || [])
        setTotal(res.data.total || 0)
        setPage(res.data.page || 1)
        setPages(res.data.pages || 1)
      }
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchList(1) }, [fetchList])

  // Search with debounce
  useEffect(() => {
    const timer = setTimeout(() => fetchList(1, search), 300)
    return () => clearTimeout(timer)
  }, [search, fetchList])

  // Open detail view
  const openDetail = async (sid) => {
    setLoading(true)
    try {
      const [res, connRes] = await Promise.all([
        conversationGet(sid),
        conversationConnections(sid),
      ])
      if (res.ok && res.data) {
        setDetail(res.data)
        setConnections(connRes.ok ? (connRes.data?.connections || []) : [])
        setMode('detail')
      }
    } catch {}
    setLoading(false)
  }

  // Star toggle
  const toggleStar = async (sid, current) => {
    try {
      await conversationUpdate(sid, { is_starred: !current })
      fetchList(page)
    } catch {}
  }

  // Delete
  const handleDelete = async (sid) => {
    if (!confirm('Delete this conversation?')) return
    try {
      await conversationDelete(sid)
      if (detail?.id === sid) setMode('list')
      fetchList(page)
    } catch {}
  }

  // Promote
  const handlePromote = async (connId) => {
    setPromoting(connId)
    // Find the connection in our list
    const conn = connections.find(c => c.id === connId)
    if (!conn) { setPromoting(null); return }

    // Default form values
    setPromoteForm({
      id: connId,
      source: conn.source_verse,
      target: conn.target_verse,
      layer: 'intertextual',
      type_name: 'parallel',
      subtype: '',
      strength: 0.5,
      confidence: conn.confidence || 0.5,
    })
    setPromoting(null)
  }

  const submitPromote = async () => {
    if (!promoteForm) return
    try {
      const res = await fetch(`/api/v1/conversations/${detail?.id}/connections/${promoteForm.id}/promote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          layer: promoteForm.layer,
          type_name: promoteForm.type_name,
          subtype: promoteForm.subtype,
          strength: promoteForm.strength,
          confidence: promoteForm.confidence,
        }),
      })
      const data = await res.json()
      if (data.ok) {
        setConnections(prev => prev.map(c =>
          c.id === promoteForm.id ? { ...c, promoted: 1 } : c
        ))
      } else {
        alert(data.error || 'Promotion failed')
      }
    } catch (e) {
      alert('Promotion failed: ' + e.message)
    }
    setPromoteForm(null)
  }

  // Back to list
  const backToList = () => {
    setMode('list')
    setDetail(null)
    setConnections([])
    setPromoteForm(null)
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">
          {mode === 'list' ? 'Conversation History 🕐' : 'Conversation Detail'}
        </h2>
        {mode === 'detail' && (
          <button onClick={backToList}
            className="text-xs text-indigo-600 hover:text-indigo-800 cursor-pointer underline">
            ← Back to list
          </button>
        )}
      </div>

      {mode === 'list' && (
        <>
          {/* Search */}
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search conversations..."
            className="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 mb-4"
          />

          {/* Session list */}
          {loading && <div className="text-sm text-neutral-400 italic py-8 text-center">Loading...</div>}
          {!loading && sessions.length === 0 && (
            <div className="text-sm text-neutral-400 py-8 text-center">
              {search ? 'No conversations match your search.' : 'No conversations yet. Open the Chat Panel (Ctrl+P) to start one!'}
            </div>
          )}

          {!loading && sessions.length > 0 && (
            <div className="space-y-2">
              {sessions.map(s => (
                <div key={s.id}
                  className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg px-4 py-3 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <button onClick={() => openDetail(s.id)}
                        className="text-sm font-medium text-neutral-800 dark:text-neutral-200 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer text-left truncate w-full">
                        {s.title || 'Untitled Conversation'}
                      </button>
                      <div className="flex items-center gap-2 mt-1 text-[10px] text-neutral-400 dark:text-neutral-500">
                        <span>{s.message_count || 0} messages</span>
                        <span>·</span>
                        <span>{s.created_at?.slice(0, 10) || ''}</span>
                        {s.theme && <><span>·</span><span className="text-indigo-400">{s.theme}</span></>}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button onClick={() => toggleStar(s.id, s.is_starred)}
                        className="text-sm cursor-pointer hover:scale-110 transition-transform"
                        title={s.is_starred ? 'Unstar' : 'Star'}>
                        {s.is_starred ? '⭐' : '☆'}
                      </button>
                      <button onClick={() => handleDelete(s.id)}
                        className="text-xs text-neutral-400 hover:text-red-500 cursor-pointer px-1"
                        title="Delete">🗑</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-6">
              <button onClick={() => fetchList(page - 1, search)} disabled={page <= 1}
                className="px-3 py-1 text-xs rounded border border-neutral-300 dark:border-neutral-600 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                ← Prev
              </button>
              <span className="text-xs text-neutral-500">{page} / {pages}</span>
              <button onClick={() => fetchList(page + 1, search)} disabled={page >= pages}
                className="px-3 py-1 text-xs rounded border border-neutral-300 dark:border-neutral-600 disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                Next →
              </button>
            </div>
          )}
        </>
      )}

      {mode === 'detail' && detail && (
        <div className="flex gap-6">
          {/* Left: Messages */}
          <div className="flex-1 min-w-0">
            {detail.messages?.length === 0 && (
              <div className="text-sm text-neutral-400 py-8 text-center italic">No messages in this session</div>
            )}
            <div className="space-y-3">
              {detail.messages?.map(m => (
                <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-900 dark:text-indigo-200'
                      : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200'
                  }`}>
                    <div className="text-[10px] text-neutral-400 dark:text-neutral-500 mb-1 font-medium uppercase tracking-wider">
                      {m.role}
                    </div>
                    <div className="prose prose-sm max-w-none [&_strong]:font-semibold [&_italic]:italic">
                      {m.content.split('\n').map((line, j) => (
                        <p key={j} className="my-0.5">{linkRefs(line, onNavigate)}</p>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Connection sidebar */}
          <div className="w-72 shrink-0">
            <div className="sticky top-24">
              <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider mb-3">
                Connections ({connections.length})
              </h3>

              {connections.length === 0 && (
                <p className="text-xs text-neutral-400 italic">No connections extracted from this conversation.</p>
              )}

              {/* Retrieved */}
              {connections.filter(c => c.connection_type === 'retrieved').length > 0 && (
                <div className="mb-4">
                  <h4 className="text-[10px] text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-neutral-400 inline-block" />
                    Retrieved <span className="font-normal">(existing in graph)</span>
                  </h4>
                  <div className="space-y-1.5">
                    {connections.filter(c => c.connection_type === 'retrieved').map(c => (
                      <div key={c.id}
                        className="text-xs bg-neutral-50 dark:bg-neutral-800/50 border border-neutral-200 dark:border-neutral-700 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-1.5 mb-1">
                          <ConnectionBadge type="retrieved" />
                          {c.promoted ? <span className="text-[10px] text-green-600">✓ Promoted</span> : null}
                        </div>
                        <div className="text-neutral-800 dark:text-neutral-200 font-mono">
                          <button onClick={() => { const p = c.source_verse.split('.'); onNavigate(p[0], parseInt(p[1])) }}
                            className="hover:text-blue-600 cursor-pointer">{c.source_verse}</button>
                          <span className="text-neutral-300 mx-1">→</span>
                          <button onClick={() => { const p = c.target_verse.split('.'); onNavigate(p[0], parseInt(p[1])) }}
                            className="hover:text-blue-600 cursor-pointer">{c.target_verse}</button>
                        </div>
                        {c.relationship && <div className="text-[10px] text-neutral-400 mt-0.5">{c.relationship}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Discovered */}
              {connections.filter(c => c.connection_type === 'discovered' || c.connection_type === 'suggested').length > 0 && (
                <div>
                  <h4 className="text-[10px] text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
                    Discovered <span className="font-normal">(new — promote to save)</span>
                  </h4>
                  <div className="space-y-1.5">
                    {connections.filter(c => c.connection_type === 'discovered' || c.connection_type === 'suggested').map(c => (
                      <div key={c.id}
                        className="text-xs bg-amber-50/50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">
                        <div className="flex items-center gap-1.5 mb-1">
                          <ConnectionBadge type={c.connection_type} />
                          {c.promoted ? (
                            <span className="text-[10px] text-green-600">✓ Promoted</span>
                          ) : (
                            <button onClick={() => handlePromote(c.id)} disabled={promoting === c.id}
                              className="text-[10px] text-indigo-600 hover:text-indigo-800 cursor-pointer disabled:opacity-50 underline ml-auto">
                              {promoting === c.id ? '...' : 'Promote'}
                            </button>
                          )}
                        </div>
                        <div className="text-neutral-800 dark:text-neutral-200 font-mono">
                          <button onClick={() => { const p = c.source_verse.split('.'); onNavigate(p[0], parseInt(p[1])) }}
                            className="hover:text-blue-600 cursor-pointer">{c.source_verse}</button>
                          <span className="text-neutral-300 mx-1">→</span>
                          <button onClick={() => { const p = c.target_verse.split('.'); onNavigate(p[0], parseInt(p[1])) }}
                            className="hover:text-blue-600 cursor-pointer">{c.target_verse}</button>
                        </div>
                        {c.relationship && <div className="text-[10px] text-neutral-400 mt-0.5">type: {c.relationship}</div>}
                        {c.confidence && <div className="text-[10px] text-neutral-400 mt-0.5">
                          confidence: {Math.round(c.confidence * 100)}%
                        </div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Promote Modal */}
      {promoteForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 dark:bg-black/50"
          onClick={() => setPromoteForm(null)}>
          <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-md mx-4 p-6"
            onClick={e => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-4">Promote Connection</h3>

            <div className="mb-4 text-xs text-neutral-600 dark:text-neutral-400 font-mono bg-neutral-50 dark:bg-neutral-900 rounded-lg px-3 py-2 flex items-center gap-2">
              <span className="text-blue-600">{promoteForm.source}</span>
              <span className="text-neutral-300">→</span>
              <span className="text-blue-600">{promoteForm.target}</span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[10px] text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Layer</label>
                <select value={promoteForm.layer} onChange={e => setPromoteForm(f => ({...f, layer: e.target.value}))}
                  className="w-full px-2 py-1.5 rounded border border-neutral-300 dark:border-neutral-600 text-xs bg-white dark:bg-neutral-800 mt-1">
                  <option value="intertextual">Intertextual</option>
                  <option value="linguistic">Linguistic</option>
                  <option value="structural">Structural</option>
                  <option value="thematic">Thematic</option>
                  <option value="symbolic">Symbolic</option>
                  <option value="geographic">Geographic</option>
                  <option value="chronological">Chronological</option>
                </select>
              </div>
              <div>
                <label className="text-[10px] text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Type</label>
                <input type="text" value={promoteForm.type_name}
                  onChange={e => setPromoteForm(f => ({...f, type_name: e.target.value}))}
                  className="w-full px-2 py-1.5 rounded border border-neutral-300 dark:border-neutral-600 text-xs bg-white dark:bg-neutral-800 mt-1" />
              </div>
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="text-[10px] text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Confidence</label>
                  <input type="range" min="0" max="1" step="0.05" value={promoteForm.confidence}
                    onChange={e => setPromoteForm(f => ({...f, confidence: parseFloat(e.target.value)}))}
                    className="w-full mt-1" />
                  <div className="text-[10px] text-neutral-400 text-center">{Math.round(promoteForm.confidence * 100)}%</div>
                </div>
                <div className="flex-1">
                  <label className="text-[10px] text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Strength</label>
                  <input type="range" min="0" max="1" step="0.05" value={promoteForm.strength}
                    onChange={e => setPromoteForm(f => ({...f, strength: parseFloat(e.target.value)}))}
                    className="w-full mt-1" />
                  <div className="text-[10px] text-neutral-400 text-center">{Math.round(promoteForm.strength * 100)}%</div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6">
              <button onClick={() => setPromoteForm(null)}
                className="px-4 py-1.5 text-xs rounded-lg border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
                Cancel
              </button>
              <button onClick={submitPromote}
                className="px-4 py-1.5 text-xs rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 cursor-pointer transition-colors">
                Promote to Graph
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
