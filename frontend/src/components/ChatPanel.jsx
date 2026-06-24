/**
 * LLM Chat Panel — triggered by Ctrl+P.
 *
 * Auto-saves every message to the server for persistence and review.
 * Uses react-markdown for content rendering with clickable VerseChips.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import VerseChip from './VerseChip'
import VersePopup from './VersePopup'
import { conversationCreate, conversationAddMessage, conversationGet, conversationList, chat } from '../api'

// ── Verse ref detection ──

const VERSE_REF_RE = /([a-z0-9_]+)\.(\d+)\.(\d+)/gi

/** Pre-process markdown to wrap verse refs in a custom placeholder */
function preprocessVerses(markdown) {
  if (!markdown) return ''
  // Wrap verse refs like gen.1.1 in a custom marker that we can detect
  return markdown.replace(
    VERSE_REF_RE,
    (match, book, ch, vs) => `%%%VERSE:${book.toLowerCase()}.${ch}.${vs}%%%`
  )
}

/** Check if a line looks like a standalone verse reference (not inside a code block or heading) */
function isStandaloneVerse(line) {
  return VERSE_REF_RE.test(line)
}


// ── Chat Panel Component ──

export default function ChatPanel({ open, onClose, onNavigate, onOpenTab, initialMessage, variant = 'overlay' }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [waiting, setWaiting] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showRecent, setShowRecent] = useState(false)
  const [recentSessions, setRecentSessions] = useState([])
  const [loadingRecent, setLoadingRecent] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [popupRef, setPopupRef] = useState(null)
  const [editingIdx, setEditingIdx] = useState(null)   // index of user message being edited, or null
  const [editText, setEditText] = useState('')          // text while editing
  const [copiedIdx, setCopiedIdx] = useState(null)      // index of just-copied message for feedback
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const sessionRef = useRef(null)
  const titleSet = useRef(false)

  useEffect(() => { sessionRef.current = sessionId }, [sessionId])

  // ── Initialize session on mount ──
  useEffect(() => {
    if (!open) return

    const init = async () => {
      setRestoring(true)
      const storedId = loadSessionId()
      if (storedId) {
        try {
          const res = await conversationGet(storedId)
          if (res.ok && res.data) {
            const s = res.data
            setSessionId(storedId)
            const restored = [
              { role: 'assistant', content: welcomeMessage(), timestamp: new Date().toISOString() },
              ...s.messages.map(m => ({
                role: m.role, content: m.content, timestamp: m.timestamp,
              })),
            ]
            setMessages(restored)
            titleSet.current = s.messages.length > 0
            setRestoring(false)
            if (initialMessage) setTimeout(() => sendMessage(initialMessage), 300)
            return
          }
        } catch {}
        clearSessionId()
      }

      try {
        const res = await conversationCreate({ title: 'Chat Session' })
        if (res.ok && res.data) {
          setSessionId(res.data.id)
          saveSessionId(res.data.id)
        }
      } catch {}

      setMessages([{ role: 'assistant', content: welcomeMessage(), timestamp: new Date().toISOString() }])
      titleSet.current = false
      setRestoring(false)
      if (initialMessage) setTimeout(() => sendMessage(initialMessage), 300)
    }
    init()
  }, [open])

  function welcomeMessage() {
    return `Hi! I'm connected to **deepseek-v4-flash** with **32 tools** to explore the canon.

Try asking:
- *"Look up gen.1.1 and explain its gematria"*
- *"What connections does isa.6.1 have to the NT?"*
- *"Trace the Son of Man from Daniel to Jesus"*
- *"Find the path between gen.1.1 and john.1.1"*

Verse references like \`gen.1.1\` render as clickable **📖 chips** — tap to see the verse.`
  }

  // ── Scroll on new messages ──
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Auto-title ──
  const autoTitle = useCallback(async (text) => {
    if (titleSet.current || !sessionRef.current) return
    titleSet.current = true
    const title = text.length > 60 ? text.slice(0, 57) + '...' : text
    try {
      await fetch(`/api/v1/conversations/${sessionRef.current}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      })
    } catch {}
  }, [])

  // ── Save message ──
  const saveMessage = useCallback(async (role, content, metadata) => {
    const sid = sessionRef.current
    if (!sid) return
    setSaving(true)
    try { await conversationAddMessage(sid, role, content, metadata) } catch {}
    setSaving(false)
  }, [])

  // ── Clipboard helpers ──
  const copyToClipboard = async (text, idx) => {
    try { await navigator.clipboard.writeText(text) } catch {}
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 1500)
  }

  const formatConversation = () => {
    return messages
      .filter(m => m.role !== 'system')
      .map(m => `**${m.role === 'user' ? 'You' : 'Assistant'}:** ${m.content}`)
      .join('\n\n---\n\n')
  }

  const copyAllMessages = () => copyToClipboard(formatConversation(), -1)

  // ── Edit helpers ──
  const startEditing = (idx, content) => {
    setEditingIdx(idx)
    setEditText(content)
  }

  const cancelEditing = () => {
    setEditingIdx(null)
    setEditText('')
  }

  // Shared core: send message list to LLM, append assistant response
  const performChat = async (allMessages) => {
    setWaiting(true)
    try {
      const res = await chat(allMessages, { max_tokens: 30000 })
      if (res.ok && res.data) {
        const { content, reasoning_content: reasoningContent, usage, cost, model, tool_results: toolResults } = res.data
        const assistantMsg = { role: 'assistant', content, reasoning_content: reasoningContent, usage, cost, model, toolResults, timestamp: new Date().toISOString() }
        setMessages(prev => [...prev, assistantMsg])
        saveMessage('assistant', content, { reasoning_content: reasoningContent, usage, cost, model, toolResults })
      } else {
        const errorMsg = res?.error || 'Unknown error'
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `⚠️ **LLM unavailable**: ${errorMsg}\n\nI can still search local scriptures. Try:\n• \`find scriptures about faith\`\n• \`show me isaiah 55:6\``,
          timestamp: new Date().toISOString(),
        }])
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ **Connection error**: ${err.message}\n\nMake sure the API server is running and try again.`,
        timestamp: new Date().toISOString(),
      }])
    }
    setWaiting(false)
  }

  // ── Send message (append to end) ──
  const sendMessage = async (text) => {
    if (!text.trim()) return
    const timestamp = new Date().toISOString()
    const userMsg = { role: 'user', content: text, timestamp }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    autoTitle(text)
    saveMessage('user', text)

    const allMessages = [
      ...messages.filter(m => m.role !== 'system').map(m => {
        const base = { role: m.role, content: m.content }
        if (m.reasoning_content) base.reasoning_content = m.reasoning_content
        return base
      }),
      { role: 'user', content: text },
    ]
    await performChat(allMessages)
  }

  // ── Edit + resend (replace from a given index) ──
  const handleResendEdit = async (idx, newText) => {
    if (!newText.trim()) return
    const timestamp = new Date().toISOString()
    const userMsg = { role: 'user', content: newText, timestamp }

    // Build message list from before the edited message
    const priorMessages = messages.slice(0, idx).filter(m => m.role !== 'system').map(m => {
      const base = { role: m.role, content: m.content }
      if (m.reasoning_content) base.reasoning_content = m.reasoning_content
      return base
    })
    const allMessages = [...priorMessages, { role: 'user', content: newText }]

    // Update state: truncate to before the edited message, then add new user message
    setMessages(prev => [...prev.slice(0, idx), userMsg])
    setEditingIdx(null)
    setInput('')

    await performChat(allMessages)
  }

  // ── Load recent sessions ──
  const loadRecent = async () => {
    setLoadingRecent(true)
    try {
      const res = await conversationList(1, 20)
      if (res.ok && res.data) setRecentSessions(res.data.sessions || [])
    } catch {}
    setLoadingRecent(false)
    setShowRecent(true)
  }

  // ── Restore session ──
  const restoreSession = async (sid) => {
    try {
      const res = await conversationGet(sid)
      if (res.ok && res.data) {
        const s = res.data
        setSessionId(sid)
        saveSessionId(sid)
        titleSet.current = s.messages.length > 0
        setMessages([
          { role: 'assistant', content: `_Restored: **${s.title || 'Untitled'}**_`, timestamp: new Date().toISOString() },
          ...s.messages.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp })),
        ])
      }
    } catch {}
    setShowRecent(false)
  }

  const handleClose = () => { clearSessionId(); onClose() }

  if (variant === 'overlay' && !open) return null

  // ── Markdown components with verse chip integration ──
  const markdownComponents = {
    p: ({ children }) => (
      <p className="my-0.5 text-sm leading-relaxed">{children}</p>
    ),
    strong: ({ children }) => (
      <strong className="font-semibold text-neutral-900 dark:text-neutral-100">{children}</strong>
    ),
    em: ({ children }) => (
      <em className="italic text-neutral-700 dark:text-neutral-300">{children}</em>
    ),
    code: ({ className, children, ...props }) => {
      const isInline = !className
      return isInline ? (
        <code className="bg-neutral-100 dark:bg-neutral-800 px-1 rounded text-[10px] font-mono text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700" {...props}>
          {children}
        </code>
      ) : (
        <pre className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-3 my-1.5 overflow-x-auto text-[11px] font-mono text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
          <code className={className} {...props}>{children}</code>
        </pre>
      )
    },
    blockquote: ({ children }) => (
      <blockquote className="border-l-3 border-indigo-300 dark:border-indigo-600 pl-3 py-1 my-1.5 text-neutral-700 dark:text-neutral-300 text-sm italic">
        {children}
      </blockquote>
    ),
    h3: ({ children }) => (
      <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mt-3 mb-1 first:mt-0 text-sm">{children}</h3>
    ),
    ul: ({ children }) => (
      <ul className="list-disc list-inside space-y-0.5 my-1.5 text-sm text-neutral-700 dark:text-neutral-300">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside space-y-0.5 my-1.5 text-sm text-neutral-700 dark:text-neutral-300">{children}</ol>
    ),
    hr: () => <hr className="my-2 border-neutral-200 dark:border-neutral-700" />,
  }

  // ── Render message content with markdown + verse chips ──
  function renderContent(content) {
    if (!content) return null

    // Pre-process: replace verse refs with custom markers
    const processed = preprocessVerses(content)

    // If no verse refs, just render markdown
    if (processed === content) {
      return (
        <Markdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {content}
        </Markdown>
      )
    }

    // Split on verse markers and render with chips
    const parts = processed.split(/(%%%VERSE:[^%]+%%%)/g)
    const elements = parts.map((part, i) => {
      const verseMatch = part.match(/%%%VERSE:([^%]+)%%%/)
      if (verseMatch) {
        const ref = verseMatch[1]
        return (
          <span key={i} className="inline-block mx-0.5 align-middle">
            <VerseChip ref={ref} onOpenCard={setPopupRef} />
          </span>
        )
      }
      // Render markdown for text parts
      return (
        <span key={i} className="inline">
          <Markdown remarkPlugins={[remarkGfm]} components={{
            ...markdownComponents,
            // Prevent wrapping in <p> for inline fragments
            p: ({ children }) => <>{children}</>,
          }}>
            {part}
          </Markdown>
        </span>
      )
    })

    return <div className="space-y-1">{elements}</div>
  }

  // ── Shared chat body (messages + input) ──
  const chatBody = (
    <>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[300px]">
        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            {/* Edit mode: textarea for user messages */}
            {msg.role === 'user' && editingIdx === i ? (
              <div className="w-full max-w-[85%] flex flex-col gap-1.5">
                <textarea
                  value={editText}
                  onChange={e => setEditText(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Escape') { e.preventDefault(); cancelEditing(); return }
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleResendEdit(i, editText); return }
                  }}
                  className="w-full px-3 py-2 rounded-lg border border-blue-400 dark:border-blue-500 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:ring-2 focus:ring-blue-400 resize-none"
                  rows={3}
                  autoFocus
                />
                <div className="flex items-center gap-2 text-[10px]">
                  <button onClick={() => handleResendEdit(i, editText)}
                    className="px-2.5 py-1 rounded bg-blue-600 text-white font-medium hover:bg-blue-700 cursor-pointer transition-colors">
                    Resend
                  </button>
                  <button onClick={cancelEditing}
                    className="px-2.5 py-1 rounded text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
                    Cancel
                  </button>
                  <span className="text-neutral-400 dark:text-neutral-500 italic">Ctrl+Enter to resend · Esc to cancel</span>
                </div>
              </div>
            ) : (
              <div className={`group relative max-w-[85%] w-fit px-4 py-2.5 text-sm leading-relaxed shadow-sm
                ${msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-2xl rounded-br-md'
                  : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 rounded-2xl rounded-bl-md'
                }`}>
                {/* Copy button (top-right, on hover) — for assistant messages */}
                {msg.role === 'assistant' && (
                  <button onClick={() => copyToClipboard(msg.content, i)}
                    className="absolute -top-1.5 -right-1.5 opacity-0 group-hover:opacity-100 transition-opacity w-5 h-5 flex items-center justify-center rounded-full bg-white dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 shadow-sm hover:bg-neutral-100 dark:hover:bg-neutral-600 cursor-pointer text-[10px]"
                    title="Copy message">
                    {copiedIdx === i ? (
                      <span className="text-green-600 dark:text-green-400 text-[8px]">✓</span>
                    ) : (
                      <span className="text-neutral-400 dark:text-neutral-400">📋</span>
                    )}
                  </button>
                )}
                {renderContent(msg.content)}

                {/* Tool results */}
                {msg.toolResults && msg.toolResults.length > 0 && (
                  <div className="mt-2 space-y-1.5 pt-1.5 border-t border-neutral-200 dark:border-neutral-700">
                    {msg.toolResults.map((tr, ti) => (
                      <details key={ti} className="group">
                        <summary className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono cursor-pointer hover:text-neutral-600 dark:hover:text-neutral-300 list-none flex items-center gap-1.5 select-none">
                          <span className="text-blue-500">🔧</span>
                          <span className="font-medium">{tr.name}</span>
                          <span className="text-[8px] text-neutral-300 dark:text-neutral-600 truncate max-w-[120px]">
                            {JSON.stringify(tr.args).slice(0, 80)}
                          </span>
                          <span className="ml-auto text-[9px] text-neutral-300 dark:text-neutral-600 group-open:rotate-90 transition-transform">▶</span>
                        </summary>
                        <div className="mt-1 px-2 py-1.5 rounded bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-[10px] font-mono text-neutral-600 dark:text-neutral-400 max-h-32 overflow-y-auto whitespace-pre-wrap break-all">
                          {JSON.stringify(tr.result, null, 2).slice(0, 1000)}
                          {JSON.stringify(tr.result, null, 2).length > 1000 && '\n... (truncated)'}
                        </div>
                      </details>
                    ))}
                  </div>
                )}

                {/* Token display */}
                {msg.usage && (() => {
                  const total = msg.usage.total_tokens || 1
                  const promptPct = Math.round(msg.usage.prompt_tokens / total * 100)
                  const compPct = Math.round(msg.usage.completion_tokens / total * 100)
                  return (
                    <div className="flex items-center gap-2 mt-1.5 text-[9px] text-neutral-400 dark:text-neutral-500 font-mono">
                      <div className="flex-1 h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden max-w-[60px]">
                        <div className="h-full flex">
                          <div className="bg-blue-400 dark:bg-blue-500 h-full" style={{ width: `${promptPct}%` }} />
                          <div className="bg-green-400 dark:bg-green-500 h-full" style={{ width: `${compPct}%` }} />
                        </div>
                      </div>
                      <span>{msg.usage.prompt_tokens} in</span>
                      <span>{msg.usage.completion_tokens} out</span>
                      {msg.cost?.total !== undefined && (
                        <span className="text-amber-600 dark:text-amber-400">${Number(msg.cost.total).toFixed(5)}</span>
                      )}
                      {msg.model && (
                        <span className="text-[8px] text-neutral-300 dark:text-neutral-600 truncate max-w-[80px]">{msg.model.replace('deepseek-', '')}</span>
                      )}
                    </div>
                  )
                })()}

                {/* Edit button (bottom-right, on hover) — for user messages (not while waiting) */}
                {msg.role === 'user' && !waiting && (
                  <button onClick={() => startEditing(i, msg.content)}
                    className="absolute -bottom-1.5 -right-1.5 opacity-0 group-hover:opacity-100 transition-opacity w-5 h-5 flex items-center justify-center rounded-full bg-white dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 shadow-sm hover:bg-neutral-100 dark:hover:bg-neutral-600 cursor-pointer text-[10px]"
                    title="Edit message">
                    ✏️
                  </button>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Thinking indicator */}
        {waiting && (
          <div className="flex justify-start">
            <div className="bg-neutral-100 dark:bg-neutral-800 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-neutral-500 dark:text-neutral-400 italic flex items-center gap-2 shadow-sm">
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
              <span>Thinking</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 flex gap-2 shrink-0">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Escape' && variant === 'overlay') { handleClose(); return }
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); return }
          }}
          placeholder="Ask about scriptures..."
          className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 placeholder-neutral-400 dark:placeholder-neutral-500"
          disabled={waiting || restoring}
        />
        <button onClick={() => sendMessage(input)} disabled={waiting || restoring || !input.trim()}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium
            hover:bg-indigo-700 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 disabled:cursor-not-allowed cursor-pointer transition-colors">
          Send
        </button>
      </div>
    </>
  )

  // ── Shared overlays (Verse popup + Recent sessions) ──
  const overlays = (
    <>
      {popupRef && (
        <VersePopup
          verseRef={popupRef}
          onClose={() => setPopupRef(null)}
          onNavigate={(book, chapter) => {
            setPopupRef(null)
            onNavigate(book, chapter)
          }}
        />
      )}
      {showRecent && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[10vh]"
          onClick={() => setShowRecent(false)}>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-md mx-4 max-h-[50vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
              <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Recent Conversations</h3>
              <button onClick={() => setShowRecent(false)}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-sm px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800">Close</button>
            </div>
            {loadingRecent && <div className="px-4 py-8 text-center text-sm text-neutral-400 italic">Loading...</div>}
            {!loadingRecent && recentSessions.length === 0 && <div className="px-4 py-8 text-center text-sm text-neutral-400">No conversations yet</div>}
            {!loadingRecent && recentSessions.map(s => (
              <button key={s.id} onClick={() => restoreSession(s.id)}
                className="w-full text-left px-4 py-3 border-b border-neutral-100 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800 cursor-pointer transition-colors">
                <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">{s.title || 'Untitled'}</div>
                <div className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-0.5">
                  {s.message_count || 0} messages · {s.created_at?.slice(0, 10) || ''}
                  {s.is_starred ? ' · ⭐' : ''}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  )

  // ── Tab variant: inline in main content ──
  if (variant === 'tab') {
    return (
      <div className="flex flex-col h-full bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Chat</h2>
            {saving && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">saving...</span>}
            {restoring && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">restoring...</span>}
          </div>
          <div className="flex items-center gap-1">
            {messages.length > 0 && (
              <button onClick={copyAllMessages}
                className="text-[11px] text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 cursor-pointer px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                title="Copy all messages">
                {copiedIdx === -1 ? '✓ Copied' : 'Copy all'}
              </button>
            )}
            <button onClick={loadRecent}
              className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 cursor-pointer px-2 py-0.5 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
              Recent
            </button>
          </div>
        </div>
        {chatBody}
        {overlays}
      </div>
    )
  }

  // ── Overlay variant: fixed position popup ──
  return (
    <>
      <div className="fixed inset-0 z-50 flex items-end justify-center pb-4 pointer-events-none">
        <div className="w-full max-w-3xl mx-4 bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 pointer-events-auto flex flex-col max-h-[80vh]"
          onClick={e => e.stopPropagation()}>

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Scripture Chat</h2>
              {saving && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">saving...</span>}
              {restoring && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">restoring...</span>}
            </div>
            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button onClick={copyAllMessages}
                  className="text-[11px] text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 cursor-pointer px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                  title="Copy all messages">
                  {copiedIdx === -1 ? '✓ Copied' : 'Copy all'}
                </button>
              )}
              <button onClick={loadRecent}
                className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 cursor-pointer px-2 py-0.5 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                Recent
              </button>
              <button onClick={handleClose}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-sm px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                ESC close
              </button>
            </div>
          </div>

          {chatBody}
        </div>
      </div>
      {overlays}
    </>
  )
}

// ── Persistence helpers ──

const STORAGE_KEY = 'current_chat_session'
function loadSessionId() { try { return localStorage.getItem(STORAGE_KEY) } catch { return null } }
function saveSessionId(id) { try { localStorage.setItem(STORAGE_KEY, id) } catch {} }
function clearSessionId() { try { localStorage.removeItem(STORAGE_KEY) } catch {} }
