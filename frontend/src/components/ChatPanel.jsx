/**
 * LLM Chat Panel — triggered by Ctrl+P.
 *
 * Placeholder LLM: uses regex patterns to respond to queries.
 * Eventually swappable for a real API call.
 *
 * Can call "functions":
 *   - search(q) → find verses by keyword
 *   - lookup(ref) → show a verse
 *   - gematria(word) → get Hebrew word value
 *   - navigate(book, chapter) → open a chapter tab
 *   - open_verses(book, chapter, verses) → open tab with highlights
 */

import React, { useState, useEffect, useRef } from 'react'
import VersePreviewCard from './VersePreviewCard'

// ── Placeholder "LLM" — regex-based responses ──

const SCRIPTURE_DB = [
  // Faith
  { ref: 'heb.11.1', text: 'Now faith is the substance of things hoped for, the evidence of things not seen.', book: 'heb', chapter: 11, verse: 1, keywords: ['faith', 'substance', 'hope'] },
  { ref: 'heb.11.6', text: 'But without faith it is impossible to please him: for he that cometh to God must believe that he is, and that he is a rewarder of them that diligently seek him.', book: 'heb', chapter: 11, verse: 6, keywords: ['faith', 'god', 'believe'] },
  { ref: 'alma.32.21', text: 'And now as I said concerning faith—faith is not to have a perfect knowledge of things; therefore if ye have faith ye hope for things which are not seen, which are true.', book: 'alma', chapter: 32, verse: 21, keywords: ['faith', 'hope', 'knowledge'] },
  { ref: 'moroni.7.26', text: 'And after that he came men also were saved by faith in his name; and by faith, they become the sons of God.', book: 'moro', chapter: 7, verse: 26, keywords: ['faith', 'saved', 'god'] },
  { ref: 'acts.16.31', text: 'And they said, Believe on the Lord Jesus Christ, and thou shalt be saved, and thy house.', book: 'acts', chapter: 16, verse: 31, keywords: ['believe', 'faith', 'saved'] },
  { ref: 'rom.10.17', text: 'So then faith cometh by hearing, and hearing by the word of God.', book: 'rom', chapter: 10, verse: 17, keywords: ['faith', 'hearing', 'word'] },
  { ref: '2cor.5.7', text: 'For we walk by faith, not by sight:', book: '2cor', chapter: 5, verse: 7, keywords: ['faith', 'walk', 'sight'] },
  { ref: 'alma.32.27', text: 'But behold, if ye will awake and arouse your faculties, even to an experiment upon my words, and exercise a particle of faith, yea, even if ye can no more than desire to believe, let this desire work in you.', book: 'alma', chapter: 32, verse: 27, keywords: ['faith', 'desire', 'believe', 'experiment'] },

  // Grace
  { ref: 'eph.2.8', text: 'For by grace are ye saved through faith; and that not of yourselves: it is the gift of God:', book: 'eph', chapter: 2, verse: 8, keywords: ['grace', 'faith', 'saved', 'gift'] },
  { ref: '2cor.12.9', text: 'And he said unto me, My grace is sufficient for thee: for my strength is made perfect in weakness.', book: '2cor', chapter: 12, verse: 9, keywords: ['grace', 'strength', 'weakness'] },
  { ref: 'moroni.10.32', text: 'Yea, come unto Christ, and be perfected in him, and deny yourselves of all ungodliness; and if ye shall deny yourselves of all ungodliness and love God with all your might, mind and strength, then is his grace sufficient for you.', book: 'moro', chapter: 10, verse: 32, keywords: ['grace', 'christ', 'perfect'] },
  { ref: 'jacob.4.7', text: 'Nevertheless, the Lord God showeth us our weakness that we may know that it is by his grace, and his great condescensions unto the children of men, that we have power to do these things.', book: 'jacob', chapter: 4, verse: 7, keywords: ['grace', 'weakness', 'god'] },

  // Covenant
  { ref: 'gen.17.7', text: 'And I will establish my covenant between me and thee and thy seed after thee in their generations for an everlasting covenant, to be a God unto thee, and to thy seed after thee.', book: 'gen', chapter: 17, verse: 7, keywords: ['covenant', 'everlasting', 'seed'] },
  { ref: 'exo.19.5', text: 'Now therefore, if ye will obey my voice indeed, and keep my covenant, then ye shall be a peculiar treasure unto me above all people: for all the earth is mine:', book: 'exo', chapter: 19, verse: 5, keywords: ['covenant', 'obey', 'treasure'] },
  { ref: 'jer.31.33', text: 'But this shall be the covenant that I will make with the house of Israel; After those days, saith the Lord, I will put my law in their inward parts, and write it in their hearts; and will be their God, and they shall be my people.', book: 'jer', chapter: 31, verse: 33, keywords: ['covenant', 'heart', 'law'] },
  { ref: 'dc.84.57', text: 'And they shall remain under this condemnation until they repent and remember the new covenant, even the Book of Mormon and the former commandments which I have given them.', book: 'dc', section: 84, verse: 57, keywords: ['covenant', 'book of mormon'] },
]

function llmRespond(query) {
  const q = query.toLowerCase()

  // Help / commands
  if (/^(help|\?|commands)/.test(q)) {
    return {
      type: 'text',
      content: `I can search scriptures and open tabs with results.

**Available commands:**
• Search: \`find scriptures about [topic]\` / \`search for [keyword]\`
• Lookup: \`show me [book] [chapter]:[verse]\`
• Navigate: \`go to [book] [chapter]\`
• Open: \`open [book] [chapter] as tab\`
• Analyze: \`what is the gematria of [word]\`

**Try:** "find scriptures about faith" or "show me isaiah 55:6"`
    }
  }

  // Search by topic/keyword
  const searchMatch = q.match(/(?:find|search|show|lookup|verses about|scriptures about)\s+(.+)/i)
  if (searchMatch) {
    const topic = searchMatch[1].toLowerCase()
    const results = SCRIPTURE_DB.filter(s =>
      s.keywords.some(k => topic.includes(k) || k.includes(topic))
      || s.text.toLowerCase().includes(topic)
    )

    if (results.length === 0) {
      return {
        type: 'text',
        content: `I don't have specific results for "${topic}" in my local database yet. Try: faith, grace, covenant, hope, love, or a specific verse reference.`
      }
    }

    return {
      type: 'search_results',
      topic,
      results: results.map(r => ({
        ref: r.ref,
        text: r.text.slice(0, 120) + '...',
        book: r.book,
        chapter: r.chapter,
        verse: r.verse,
      })),
      content: `Found **${results.length}** scripture${results.length > 1 ? 's' : ''} about "${topic}":\n\n` +
        results.map(r => `• **${r.ref}** — ${r.text.slice(0, 100)}...`).join('\n'),
    }
  }

  // Lookup verse
  const lookupMatch = q.match(/(?:show|open|lookup|read|go to)\s+(\w[\w.]*)\s*(\d+)?:*(\d+)?/i)
  if (lookupMatch) {
    let book = lookupMatch[1].toLowerCase()
    let chapter = parseInt(lookupMatch[2]) || 1
    const verse = parseInt(lookupMatch[3])

    // Handle "isaiah 55:6" format
    const altMatch = q.match(/(\w+)\s+(\d+):(\d+)/i)
    if (altMatch) {
      book = altMatch[1].toLowerCase()
      chapter = parseInt(altMatch[2])
    }

    return {
      type: 'navigate',
      book: book === 'isaiah' ? 'isa' : book,
      chapter,
      verse,
      content: `Opening **${book === 'isaiah' ? 'isa' : book} ${chapter}${verse ? ':' + verse : ''}** as a new tab.`,
    }
  }

  // Gematria
  const gematriaMatch = q.match(/(?:gematria|value|number)\s+(?:of\s+)?(.+)/i)
  if (gematriaMatch) {
    return {
      type: 'gematria',
      word: gematriaMatch[1].trim(),
      content: `The gematria lookup for "${gematriaMatch[1].trim()}" would show its numeric value. (Full integration coming with real API.)`,
    }
  }

  // Fallback
  return {
    type: 'text',
    content: `I can search scriptures by topic or look up verses. Try:\n\n• \`find scriptures about faith\`\n• \`show me isaiah 55:6\`\n• \`help\` for all commands`,
  }
}


// ── Chat Panel Component ──

export default function ChatPanel({ open, onClose, onNavigate, onOpenTab, initialMessage }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [waiting, setWaiting] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100)
      if (messages.length === 0) {
        setMessages([{
          role: 'assistant',
          content: 'Hi! I can search scriptures and open tabs. Try: **find scriptures about faith** or **show me isaiah 55:6**',
          timestamp: new Date().toISOString(),
        }])
        // Auto-send initial message if provided (from /chat command)
        if (initialMessage) {
          setTimeout(() => sendMessage(initialMessage), 300)
        }
      }
    }
  }, [open])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = (text) => {
    if (!text.trim()) return
    const userMsg = { role: 'user', content: text, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setWaiting(true)

    // Simulate LLM delay
    setTimeout(() => {
      const response = llmRespond(text)
      const assistantMsg = {
        role: 'assistant',
        content: response.content,
        data: response,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMsg])
      setWaiting(false)

      // Auto-open tab for navigate/search_results type
      if (response.type === 'navigate') {
        onNavigate(response.book, response.chapter)
      } else if (response.type === 'search_results' && response.results) {
        // Group results by (book, chapter) and open tabs
        const groups = {}
        response.results.forEach(r => {
          const key = `${r.book}.${r.chapter}`
          if (!groups[key]) groups[key] = { book: r.book, chapter: r.chapter, verses: [] }
          groups[key].verses.push(r.verse)
        })
        Object.values(groups).forEach(g => {
          onOpenTab(g.book, g.chapter, {
            label: `${g.book}.${g.chapter} — ${g.verses.join(', ')}`,
            highlights: g.verses,
          })
        })
      }
    }, 500)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pb-4 pointer-events-none">
      <div className="w-full max-w-2xl mx-4 bg-white rounded-xl shadow-2xl border border-neutral-200 pointer-events-auto flex flex-col max-h-[60vh]"
        onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
          <h2 className="text-sm font-semibold text-neutral-800">Scripture Chat</h2>
          <button onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 cursor-pointer text-sm px-2 py-0.5 rounded hover:bg-neutral-100">
            ESC close
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[200px] max-h-[40vh]">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed
                ${msg.role === 'user'
                  ? 'bg-indigo-100 text-indigo-900'
                  : 'bg-neutral-100 text-neutral-800'
                }`}>
                {/* Render markdown-style text */}
                <div className="prose prose-sm max-w-none [&_strong]:font-semibold [&_em]:italic">
                  {msg.content.split('\n').map((line, j) => (
                    <p key={j} className="my-0.5">{renderInline(line)}</p>
                  ))}
                </div>

                {/* Verse preview cards for search results */}
                {msg.data?.type === 'search_results' && msg.data.results && (
                  <div className="mt-2 space-y-2">
                    {/* Group results by (book, chapter) */}
                    {(() => {
                      const groups = {}
                      msg.data.results.forEach(r => {
                        const key = `${r.book}.${r.chapter}`
                        if (!groups[key]) groups[key] = { book: r.book, chapter: r.chapter, verses: [] }
                        groups[key].verses.push(r.verse || 1)
                      })
                      const refs = Object.values(groups).map(g =>
                        g.verses.map(v => `${g.book}.${g.chapter}.${v}`)
                      ).flat()

                      return (
                        <>
                          <VersePreviewCard refs={refs} onNavigate={onNavigate} maxHeight="10rem" />
                          <button onClick={() => {
                              Object.values(groups).forEach(g => {
                                onOpenTab(g.book, g.chapter, {
                                  label: `${g.book}.${g.chapter}`,
                                  highlights: g.verses,
                                })
                              })
                            }}
                            className="w-full text-[10px] text-indigo-600 hover:text-indigo-800 font-medium cursor-pointer underline text-center">
                            Open all as tabs →
                          </button>
                        </>
                      )
                    })()}
                  </div>
                )}

                {/* Action buttons for navigate */}
                {msg.data?.type === 'navigate' && (
                  <div className="mt-1 text-xs text-indigo-600">
                    ✓ Opened in new tab
                  </div>
                )}
              </div>
            </div>
          ))}
          {waiting && (
            <div className="flex justify-start">
              <div className="bg-neutral-100 rounded-lg px-3.5 py-2.5 text-sm text-neutral-500 italic">
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-neutral-200 flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Escape') { onClose(); return }
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); return }
            }}
            placeholder="Ask about scriptures..."
            className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400"
            disabled={waiting}
          />
          <button onClick={() => sendMessage(input)} disabled={waiting || !input.trim()}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium
              hover:bg-indigo-700 disabled:bg-neutral-300 disabled:cursor-not-allowed cursor-pointer transition-colors">
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

// Simple inline renderer for bold/italic
function renderInline(text) {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}
