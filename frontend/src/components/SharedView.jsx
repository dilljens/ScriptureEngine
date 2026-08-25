/**
 * SharedView — read-only viewer for a shared conversation snapshot.
 *
 * Shared links are unlisted: anyone with the slug can read the frozen
 * transcript. Asking a follow-up question auto-forks the snapshot into a
 * new conversation session owned by the current user, then hands off to
 * the chat tab (which picks the session up from localStorage and sends
 * the question through the normal chat flow).
 */
import React, { useState, useEffect } from 'react'
import { sharedGet, sharedFork } from '../api'

// Link bare verse refs (gen.1.1) — same convention as ConversationHistory.
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

export default function SharedView({ slug, onNavigate, onAsk }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)

  useEffect(() => {
    let cancelled = false
    setData(null)
    setError('')
    sharedGet(slug)
      .then(res => {
        if (cancelled) return
        if (res.ok && res.data) setData(res.data)
        else setError(res.error || 'Shared conversation not found')
      })
      .catch(e => { if (!cancelled) setError(e.message || 'Failed to load shared conversation') })
    return () => { cancelled = true }
  }, [slug])

  const ask = async () => {
    const q = question.trim()
    if (!q || asking || !onAsk) return
    setAsking(true)
    try {
      const res = await sharedFork(slug)
      if (res.ok && res.data?.session_id) {
        onAsk(res.data.session_id, q)
      } else {
        setError(res.error || 'Could not start a follow-up conversation')
      }
    } catch (e) {
      setError(e.message || 'Could not start a follow-up conversation')
    }
    setAsking(false)
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-12 text-center">
        <p className="text-sm text-neutral-500 dark:text-neutral-400">{error}</p>
      </div>
    )
  }
  if (!data) {
    return <div className="p-8 text-sm text-neutral-400 animate-pulse text-center">Loading shared conversation...</div>
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-6 flex flex-col h-full">
      {/* Header */}
      <div className="mb-4">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{data.title}</h2>
        <p className="text-[11px] text-neutral-400 dark:text-neutral-500 mt-1">
          Shared conversation · {data.messages?.length || 0} messages
          {data.created_at ? ` · ${String(data.created_at).slice(0, 10)}` : ''}
          {' '}· read-only snapshot
        </p>
      </div>

      {/* Transcript */}
      <div className="flex-1 overflow-y-auto space-y-3 min-h-0 pb-4">
        {data.messages?.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed ${
              m.role === 'user'
                ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-900 dark:text-indigo-200'
                : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200'
            }`}>
              <div className="text-[10px] text-neutral-400 dark:text-neutral-500 mb-1 font-medium uppercase tracking-wider">
                {m.role}
              </div>
              <div className="prose prose-sm max-w-none [&_strong]:font-semibold [&_italic]:italic">
                {String(m.content || '').split('\n').map((line, j) => (
                  <p key={j} className="my-0.5">{linkRefs(line, onNavigate)}</p>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Follow-up input — forks the snapshot into your own conversation */}
      <div className="border-t border-neutral-200 dark:border-neutral-700 pt-3 mt-2">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') ask() }}
            placeholder="Ask a follow-up question — this continues in your own conversation..."
            disabled={asking}
            className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 disabled:opacity-50"
          />
          <button onClick={ask} disabled={asking || !question.trim()}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 cursor-pointer transition-colors shrink-0">
            {asking ? 'Forking…' : 'Ask'}
          </button>
        </div>
        <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1.5">
          Your question forks this snapshot into a new private conversation — the original stays untouched.
        </p>
      </div>
    </div>
  )
}
