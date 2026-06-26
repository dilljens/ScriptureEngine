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
import { useToggles } from './ToggleProvider'
import { conversationCreate, conversationAddMessage, conversationGet, conversationList, chat } from '../api'

// ── Verse ref detection ──

const VERSE_REF_RE = /([a-z0-9_]+)\.(\d+)\.(\d+)/gi

// Map full book names to their IDs — matches the LLM's 📖 output format
const BOOK_NAME_MAP = {
  genesis: 'gen', exodus: 'exo', leviticus: 'lev', numbers: 'num', deuteronomy: 'deu',
  joshua: 'josh', judges: 'judg', ruth: 'ruth',
  '1 samuel': '1sam', '2 samuel': '2sam', '1 kings': '1kgs', '2 kings': '2kgs',
  '1 chronicles': '1chr', '2 chronicles': '2chr', ezra: 'ezra', nehemiah: 'neh',
  esther: 'esth', job: 'job', psalm: 'psa', psalms: 'psa', proverbs: 'prov',
  ecclesiastes: 'eccl', 'song of solomon': 'song', isaiah: 'isa', jeremiah: 'jer',
  lamentations: 'lam', ezekiel: 'ezek', daniel: 'dan', hosea: 'hos', joel: 'joel',
  amos: 'amos', obadiah: 'obad', jonah: 'jonah', micah: 'mic', nahum: 'nah',
  habakkuk: 'hab', zephaniah: 'zeph', haggai: 'hag', zechariah: 'zech', malachi: 'mal',
  matthew: 'matt', mark: 'mark', luke: 'luke', john: 'john', acts: 'acts',
  romans: 'rom', '1 corinthians': '1cor', '2 corinthians': '2cor', galatians: 'gal',
  ephesians: 'eph', philippians: 'phil', colossians: 'col',
  '1 thessalonians': '1thes', '2 thessalonians': '2thes',
  '1 timothy': '1tim', '2 timothy': '2tim', titus: 'titus', philemon: 'philem',
  hebrews: 'heb', james: 'james', '1 peter': '1pet', '2 peter': '2pet',
  '1 john': '1john', '2 john': '2john', '3 john': '3john', jude: 'jude',
  revelation: 'rev',
  '1 nephi': '1ne', '2 nephi': '2ne', jacob: 'jacob', enos: 'enos',
  jarom: 'jarom', omni: 'omni', 'words of mormon': 'wom', mosiah: 'mosiah',
  alma: 'alma', helaman: 'hel', '3 nephi': '3ne', '4 nephi': '4ne',
  mormon: 'morm', ether: 'ether', moroni: 'moro',
  moses: 'moses', abraham: 'abraham', 'joseph smith—matthew': 'jsm',
  'joseph smith—history': 'jsh', 'articles of faith': 'aoff',
  'doctrine and covenants': 'dc',
  // Common abbreviations the LLM might use (only unique ones not in full names)
  ezr: 'ezra', est: 'esth', eccl: 'eccl',
  jon: 'jonah',
  mrk: 'mark', lk: 'luke', jn: 'john',
  '1 cor': '1cor', '2 cor': '2cor',
  '1 thes': '1thes', '2 thes': '2thes', '1 tim': '1tim', '2 tim': '2tim',
  tit: 'titus', heb: 'heb', jam: 'james',
  '1 pet': '1pet', '2 pet': '2pet', '1 jn': '1john', '2 jn': '2john', '3 jn': '3john',
  rev: 'rev',
  '1 ne': '1ne', '2 ne': '2ne', wom: 'wom',
  hel: 'hel', '3 ne': '3ne', '4 ne': '4ne',
  abr: 'abraham', 'd&c': 'dc',
}

function resolveBookName(name) {
  const key = name.trim().toLowerCase().replace(/[—–]/g, '—')
  if (BOOK_NAME_MAP[key]) return BOOK_NAME_MAP[key]
  const firstWord = key.split(/\s/)[0]
  if (BOOK_NAME_MAP[firstWord]) return BOOK_NAME_MAP[firstWord]
  return null
}

/** Pre-process markdown to detect verse references in 📖 format + gen.1.1 */
function preprocessVerses(markdown) {
  if (!markdown) return ''
  let result = markdown

  // Strip Bible version annotations like (WEB), (KJV) so they don't interfere with ref matching
  result = result.replace(/\(WEB\)|\(KJV\)|\(LEB\)|\(BSB\)|\(YLT\)/gi, '')

  // Match criteria: must be a known book name from BOOK_NAME_MAP
  function tryReplaceBookRef(match, bookName, chapter, verseStr) {
    const bookId = resolveBookName(bookName)
    if (!bookId) return match // not a known book, leave as-is
    const firstVerse = verseStr ? verseStr.split(/[-,]/)[0] : '1'
    return `%%%VERSE:${bookId}.${chapter}.${firstVerse}%%%`
  }

  // 1. Match "Book Name ch:vs" or "Book Name ch.vs" with optional leading ** or 📖
  // Handles: Genesis 1:1, Isaiah 2:3-4, **📖 Genesis 1:1**, 📖Genesis 1.1, etc.
  result = result.replace(
    /\*{0,2}📖?\s*([A-Za-z][A-Za-z\s—–-]+?)\s*(\d+)(?:([:.])(\d+(?:[-,]\d+)*))?\*{0,2}/g,
    (match, bookName, chapter, _sep, verseStr) => tryReplaceBookRef(match, bookName, chapter, verseStr)
  )

  // 2. Replace gen.1.1 or gen:1:1 format (fallback)
  result = result.replace(
    /([a-z0-9_]+)[.:](\d+)[.:](\d+)/gi,
    (match, book, ch, vs) => `%%%VERSE:${book.toLowerCase()}.${ch}.${vs}%%%`
  )

  return result
}

/** Check if a line looks like a standalone verse reference (not inside a code block or heading) */
function isStandaloneVerse(line) {
  return VERSE_REF_RE.test(line)
}


// ── Chat Panel Component ──

export default function ChatPanel({ open, onClose, onNavigate, onOpenTab, initialMessage, variant = 'overlay' }) {
  const { searchWorks, searchLayers, searchLang, bibleVersion, enabledTools } = useToggles?.() || {}
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
  const [visitedRefs, setVisitedRefs] = useState(new Set())
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

  // Map tool categories to actual tool names
  const TOOL_CATEGORY_MAP = {
    lookup: ['scripture_verse', 'scripture_passage_guide', 'scripture_interlinear', 'scripture_verse_text'],
    search: ['scripture_search', 'scripture_search_xlingual'],
    connections: ['scripture_connections', 'scripture_intertext', 'scripture_sod', 'scripture_sources', 'scripture_sources_by_scholar', 'scripture_sources_list', 'scripture_consensus', 'scripture_disagreements'],
    graph: ['scripture_graph_path', 'scripture_graph_reachable', 'scripture_graph_entities', 'scripture_graph_shared_entities', 'scripture_graph_entity_network', 'scripture_graph_hubs', 'scripture_graph_centrality'],
    gematria: ['scripture_gematria', 'scripture_strongs'],
    study: ['scripture_study_suggest', 'scripture_study_list', 'scripture_study_get'],
    staging: ['scripture_stage_connection', 'scripture_stage_study'],
  }

  // Shared core: send message list to LLM, append assistant response
  const performChat = async (allMessages) => {
    setWaiting(true)
    try {
      // Build disabled tools list from enabledTools state
      let disabledTools = []
      if (enabledTools) {
        for (const [cat, enabled] of Object.entries(enabledTools)) {
          if (!enabled && TOOL_CATEGORY_MAP[cat]) {
            disabledTools = disabledTools.concat(TOOL_CATEGORY_MAP[cat])
          }
        }
      }
      const res = await chat(allMessages, { max_tokens: 30000, disabled_tools: disabledTools })
      if (res.ok && res.data) {
        const { content, reasoning_content: reasoningContent, usage, cost, model, tool_results: toolResults } = res.data
        // If the LLM returned only tool calls with no content, show a cleaner placeholder
        const effectiveContent = content || (toolResults?.length > 0
          ? '_Let me look that up for you..._'
          : '')
        const assistantMsg = { role: 'assistant', content: effectiveContent, reasoning_content: reasoningContent, usage, cost, model, toolResults, timestamp: new Date().toISOString() }
        setMessages(prev => [...prev, assistantMsg])
        saveMessage('assistant', effectiveContent, { reasoning_content: reasoningContent, usage, cost, model, toolResults })
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

    // Build scope instructions from search filters
    let scopeInstr = ''
    if (searchWorks) {
      const disabled = Object.entries(searchWorks).filter(([, v]) => !v).map(([k]) => k.toUpperCase())
      if (disabled.length > 0) scopeInstr += `Only search within these works: ALL EXCEPT ${disabled.join(', ')}.`
    }
    if (searchLayers) {
      const disabled = Object.entries(searchLayers).filter(([, v]) => !v).map(([k]) => k)
      if (disabled.length > 0) scopeInstr += ` Exclude these connection layers: ${disabled.join(', ')}.`
    }
    if (searchLang && searchLang !== 'all') {
      scopeInstr += ` Use ${searchLang} language for scripture searches.`
    }
    if (bibleVersion) {
      scopeInstr += ` Use the ${bibleVersion} Bible version.`
    }
    if (enabledTools) {
      const disabled = Object.entries(enabledTools).filter(([, v]) => !v).map(([k]) => k)
      if (disabled.length > 0) scopeInstr += ` Do not use these tool categories: ${disabled.join(', ')}.`
    }

    const allMessages = [
      ...(scopeInstr ? [{ role: 'system', content: `[Scope: ${scopeInstr}]` }] : []),
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
    table: ({ children }) => (
      <div className="overflow-x-auto my-2">
        <table className="w-full text-xs border-collapse border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
          {children}
        </table>
      </div>
    ),
    thead: ({ children }) => (
      <thead className="bg-neutral-100 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        {children}
      </thead>
    ),
    tbody: ({ children }) => (
      <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
        {children}
      </tbody>
    ),
    tr: ({ children }) => (
      <tr className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">{children}</tr>
    ),
    th: ({ children }) => (
      <th className="px-3 py-1.5 text-left font-semibold text-neutral-700 dark:text-neutral-300 text-[10px] uppercase tracking-wider">{children}</th>
    ),
    td: ({ children }) => (
      <td className="px-3 py-1.5 text-neutral-600 dark:text-neutral-400">{children}</td>
    ),
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
            <VerseChip ref={ref} onOpenCard={setPopupRef}
              visited={visitedRefs.has(ref)}
              onVisit={(v) => setVisitedRefs(prev => new Set([...prev, v]))} />
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
              <div className={`group relative max-w-2xl w-fit px-4 py-2.5 text-sm leading-relaxed shadow-sm
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

                {/* Reasoning — collapsible thought process */}
                {msg.reasoning_content && (
                  <details className="group mt-1">
                    <summary className="text-[9px] text-neutral-400 dark:text-neutral-500 font-mono cursor-pointer hover:text-neutral-600 dark:hover:text-neutral-300 list-none flex items-center gap-1 select-none">
                      <span className="transition-transform group-open:rotate-90 text-[8px]">▶</span>
                      <span className="italic">reasoning</span>
                    </summary>
                    <div className="mt-0.5 px-2 py-1 rounded bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-[10px] text-neutral-500 dark:text-neutral-400 leading-relaxed whitespace-pre-wrap">
                      {msg.reasoning_content}
                    </div>
                  </details>
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
      <div className="flex flex-col h-full bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 max-w-5xl mx-auto w-full">
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
