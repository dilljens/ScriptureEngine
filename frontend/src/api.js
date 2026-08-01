const BASE = '/api/v1'
const TIMEOUT_MS = 60_000
const MAX_RETRIES = 1

export async function fetchJSON(url, options = {}, _retry = 0) {
  // AbortController for timeout
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    const res = await fetch(`${BASE}${url}`, {
      ...options,
      headers: { 'Accept': 'application/json', ...options.headers },
      signal: options.signal || controller.signal,
    })
    if (!res.ok) {
      const body = await res.text()
      // Retry on 5xx (server errors including 524) — one retry with 2s backoff
      if (res.status >= 500 && _retry < MAX_RETRIES) {
        clearTimeout(timer)
        await new Promise(r => setTimeout(r, 2000))
        return fetchJSON(url, options, _retry + 1)
      }
      // Clean up error: strip HTML from Cloudflare error pages
      const cleanBody = body.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim()
      throw new Error(`API ${res.status}: ${cleanBody.slice(0, 200)}`)
    }
    return res.json()
  } catch (err) {
    if (err.name === 'AbortError') {
      // Retry on timeout — one retry
      if (_retry < MAX_RETRIES) {
        await new Promise(r => setTimeout(r, 2000))
        return fetchJSON(url, options, _retry + 1)
      }
      throw new Error(`API request to ${url} timed out`)
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export function getParallelism(book, chapter) {
  return fetchJSON(`/parallelism/${book}/${chapter}`)
}

export function getChapterParallelism(book, chapter) {
  if (book === 'isa') {
    return fetchJSON(`/parallelism/isaiah/${chapter}`)
  }
  // Generic chapter endpoint with connections for any book
  return fetchJSON(`/chapter/${book}.${chapter}`)
}

export function getVerse(ref) {
  return fetchJSON(`/verses/${ref}`)
}

export function getIsaiahStructure() {
  return fetchJSON('/parallelism/isaiah/structure')
}

export function getFootnotes(ref) {
  return fetchJSON(`/footnotes/${ref}`)
}

export function getTskCrossrefs(ref) {
  return fetchJSON(`/tsk-crossrefs/${ref}`)
}

export function getChapterGrammar(ref) {
  return fetchJSON(`/grammar/${ref}`)
}

export function getChapterConnections(ref) {
  return fetchJSON(`/connections/chapter/${ref}`)
}

export function getChapterEntities(ref) {
  return fetchJSON(`/chapter/${ref}/entities`)
}

export function searchVerses(query, opts = {}) {
  const { lang = 'english', limit = 10, offset = 0, book = '' } = opts
  const params = `q=${encodeURIComponent(query)}&lang=${lang}&limit=${limit}&offset=${offset}${book ? `&book=${encodeURIComponent(book)}` : ''}`
  return fetchJSON(`/search?${params}`)
}

export function semanticSearch(query, opts = {}) {
  const { limit = 10 } = opts
  return fetchJSON(`/semantic-search?q=${encodeURIComponent(query)}&limit=${limit}`)
}

export function getBooks() {
  return fetchJSON('/books')
}

// ─── Conversation / Chat API ───

// Stable per-device identity used to scope conversation ownership.
// Matches the anonymous id generated in App.jsx; authenticated users get
// their account id from scripture_auth_user_id.
export function currentUserId() {
  try {
    return (
      localStorage.getItem('scripture_auth_user_id')
      || localStorage.getItem('scripture_user_id')
      || 'anonymous'
    )
  } catch { return 'anonymous' }
}

export function currentSessionToken() {
  try { return localStorage.getItem('scripture_session_token') || '' } catch { return '' }
}

const userQuery = () => {
  return `user_id=${encodeURIComponent(currentUserId())}`
}

const ownerHeaders = () => {
  const token = currentSessionToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function conversationCreate(data = {}) {
  return fetchJSON(`/conversations?${userQuery()}`, {
    method: 'POST',
    body: JSON.stringify({ title: data.title || '', theme: data.theme || '', created_by: data.created_by || currentUserId() }),
    headers: { 'Content-Type': 'application/json', ...ownerHeaders() },
  })
}

export function conversationAddMessage(sessionId, role, content, metadata) {
  return fetchJSON(`/conversations/${sessionId}/messages?${userQuery()}`, {
    method: 'POST',
    body: JSON.stringify({ role, content, metadata: metadata || {} }),
    headers: { 'Content-Type': 'application/json', ...ownerHeaders() },
  })
}

export function conversationList(page = 1, perPage = 20, search = '') {
  const q = search ? `&search=${encodeURIComponent(search)}` : ''
  return fetchJSON(`/conversations?page=${page}&per_page=${perPage}&${userQuery()}${q}`, { headers: ownerHeaders() })
}

export function conversationGet(sessionId) {
  return fetchJSON(`/conversations/${sessionId}?${userQuery()}`, { headers: ownerHeaders() })
}

export function conversationUpdate(sessionId, data) {
  return fetchJSON(`/conversations/${sessionId}?${userQuery()}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json', ...ownerHeaders() },
  })
}

export function conversationDelete(sessionId) {
  return fetchJSON(`/conversations/${sessionId}?${userQuery()}`, { method: 'DELETE', headers: ownerHeaders() })
}

export function conversationConnections(sessionId) {
  return fetchJSON(`/conversations/${sessionId}/connections?${userQuery()}`, { headers: ownerHeaders() })
}

export function conversationPromoteConnection(sessionId, connectionId, data) {
  return fetchJSON(`/conversations/${sessionId}/connections/${connectionId}/promote?${userQuery()}`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json', ...ownerHeaders() },
  })
}

// ─── Study API ───

export function getStudyGuide(guideId) {
  return fetchJSON(`/studies/${guideId}`)
}

export function updateStudyGuide(guideId, data) {
  return fetchJSON(`/studies/${guideId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function addStudyStep(guideId, data) {
  return fetchJSON(`/studies/${guideId}/steps`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function deleteStudyStep(guideId, stepNumber) {
  return fetchJSON(`/studies/${guideId}/steps/${stepNumber}`, { method: 'DELETE' })
}

export function bulkUpdateStudySteps(guideId, steps) {
  return fetchJSON(`/studies/${guideId}/steps`, {
    method: 'PUT',
    body: JSON.stringify({ steps }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function createStudyGuide(data) {
  return fetchJSON('/studies', {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function exportStudyJson(guideId) {
  return fetchJSON(`/studies/${guideId}/export.json`)
}

export function publishStudy(guideId, data = {}) {
  return fetchJSON(`/studies/${guideId}/publish`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function getPublishedStudy(slug) {
  return fetchJSON(`/studies/published/${slug}`)
}

export function listPublishedStudies(limit = 20, offset = 0) {
  return fetchJSON(`/studies/published?limit=${limit}&offset=${offset}`)
}

export function forkStudy(slug, createdBy = 'user') {
  return fetchJSON(`/studies/published/${slug}/fork`, {
    method: 'POST',
    body: JSON.stringify({ created_by: createdBy }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function getInfo() {
  return fetchJSON('/info')
}

// ─── Wiki API ───

export function getWikiArticle(entityId) {
  return fetchJSON(`/wiki/${encodeURIComponent(entityId)}`)
}

export function getWikiBrowse(type = 'entity') {
  return fetchJSON(`/wiki/browse/${encodeURIComponent(type)}`)
}

export function getWikiSearch(query) {
  return fetchJSON(`/wiki/search?q=${encodeURIComponent(query)}`)
}

export function chat(messages, opts = {}) {
  const { model = 'deepseek-v4-flash', max_tokens = 128000, temperature = 0.7, signal } = opts
  // LLM calls need longer timeout — DeepSeek thinking mode can take 8+ min
  const controller = signal ? null : new AbortController()
  const timer = controller ? setTimeout(() => controller.abort(), 600_000) : null
  return fetchJSON('/chat', {
    method: 'POST',
    body: JSON.stringify({ messages, model, max_tokens, temperature, disabled_tools: opts.disabled_tools || [] }),
    headers: { 'Content-Type': 'application/json' },
    signal: controller ? controller.signal : signal,
  }).finally(() => { if (timer) clearTimeout(timer) })
}

/**
 * Streaming chat — reads SSE events from /api/v1/chat/stream
 *
 * Calls onEvent callbacks as events arrive:
 *   onThinking(content)   — reasoning/thinking chunks
 *   onText(content)       — visible response chunks
 *   onToolProgress(tools) — tool names being executed
 *   onDone({usage, cost, model, tool_results, final_content, final_reasoning}) — final event
 *   onError(message)      — error event
 *
 * Guarantees: the promise ALWAYS settles. EOF without a terminal event
 * (proxy close, mid-stream crash) is treated as an error so callers never
 * hang waiting for a response that will never arrive.
 */
export function chatStream(messages, opts = {}) {
  const { model = 'deepseek-v4-flash', max_tokens = 128000, temperature = 0.7, disabled_tools = [], signal } = opts
  const { onThinking, onText, onToolProgress, onDone, onError } = opts

  return new Promise((resolve, reject) => {
    let settled = false
    const once = (fn, ...args) => { if (!settled && fn) { settled = true; fn(...args) } }

    fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, model, max_tokens, temperature, disabled_tools }),
      signal,
    }).then(async (response) => {
      if (!response.ok) {
        const msg = response.status === 500
          ? 'The server encountered an error. Please try again.'
          : `Server error: ${response.status}`
        once(onError, msg)
        reject(new Error(msg))
        return
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let terminal = false

      const processEvent = (event) => {
        if (!event || terminal) return
        if (event.type === 'error' || (event.ok === false && event.error)) {
          const message = event.message || event.error || 'Unknown error'
          terminal = true
          once(onError, message)
          reject(new Error(message))
          return
        }
        switch (event.type) {
          case 'thinking':
            onThinking?.(event.content)
            break
          case 'text':
            onText?.(event.content)
            break
          case 'tool_progress':
            onToolProgress?.(event.tools || [])
            break
          case 'done':
            terminal = true
            once(onDone, event)
            resolve(event)
            break
          default:
            // heartbeat and any future event types — ignore
            break
        }
      }

      while (!terminal) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue

          let event
          try { event = JSON.parse(raw) } catch { continue }
          processEvent(event)
          if (terminal) return
        }
      }

      // Flush a final partial line when the server closes without a trailing
      // newline (common with abrupt proxy disconnects).
      buffer += decoder.decode()
      for (const line of buffer.split('\n')) {
        if (!line.startsWith('data: ')) continue
        const raw = line.slice(6).trim()
        if (!raw) continue
        try { processEvent(JSON.parse(raw)) } catch { /* malformed tail */ }
        if (terminal) return
      }

      // EOF without a terminal event — treat as failure, never hang
      const msg = 'The connection closed before the response finished. Please try again.'
      once(onError, msg)
      reject(new Error(msg))
    }).catch((err) => {
      if (err.name === 'AbortError') {
        reject(err)
      } else {
        once(onError, err.message)
        reject(err)
      }
    })
  })
}
