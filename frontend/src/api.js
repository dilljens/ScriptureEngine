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

// ─── Study collections (Come Follow Me + General Conference browsing) ───

export function getCfmCollections() {
  return fetchJSON('/cfm/collections')
}

export function getCfmLessons(year) {
  const q = year ? `?year=${encodeURIComponent(year)}` : ''
  return fetchJSON(`/cfm/lessons${q}`)
}

export function getCfmLesson(refId) {
  return fetchJSON(`/cfm/lessons/${encodeURIComponent(refId)}`)
}

export function getCfmLessonScriptures(refId) {
  return fetchJSON(`/cfm/lessons/${encodeURIComponent(refId)}/scriptures`)
}

export function getChapter(ref) {
  return fetchJSON(`/chapter/${ref}`)
}

export function getConferenceTalks(year) {
  const q = year ? `?year=${encodeURIComponent(year)}` : ''
  return fetchJSON(`/conference/talks${q}`)
}

export function getConferenceTalk(refId) {
  return fetchJSON(`/conference/talks/${encodeURIComponent(refId)}`)
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
 * Streaming chat — background job + polling (survives phone minimize).
 *
 * Creates a server-side chat job (POST /api/v1/chat/jobs) and polls it
 * (GET /api/v1/chat/jobs/{id}?after_seq=N). The DeepSeek run proceeds on the
 * server independent of this connection, so minimizing the app / network
 * drops no longer cancel it — the next poll picks up where it left off.
 *
 * Calls onEvent callbacks as events arrive:
 *   onThinking(content)   — reasoning/thinking chunks
 *   onText(content)       — visible response chunks
 *   onToolProgress(tools) — tool names being executed
 *   onTruncated()         — response hit the output limit and is regenerating
 *   onDone(event)         — final event {usage, cost, model, tool_results,
 *                            finish_reason, final_content, final_reasoning}
 *   onError(message)      — error event
 *
 * Guarantees: the promise ALWAYS settles. Polling only runs while the page is
 * visible; when backgrounded the job keeps running server-side and the next
 * poll after visibilitychange catches up.
 */
export function chatStream(messages, opts = {}) {
  const {
    model = 'deepseek-v4-flash', max_tokens = 128000, temperature = 0.7,
    disabled_tools = [], scopes = [], mode = 'chat',
    session_id = '', client_message_id = '', signal,
  } = opts
  const { onThinking, onText, onToolProgress, onTruncated, onDone, onError } = opts
  const POLL_MS = 2000

  return new Promise((resolve, reject) => {
    let settled = false
    let jobId = null
    let lastSeq = 0
    let pollTimer = null
    let backoff = POLL_MS
    let visible = typeof document !== 'undefined' ? document.visibilityState !== 'hidden' : true
    let cancelled = false
    let abortHandler = null

    const cleanup = () => {
      clearTimeout(pollTimer)
      if (abortHandler && signal) signal.removeEventListener('abort', abortHandler)
      if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', onVisibility)
    }
    const finish = (fn, value) => {
      if (settled) return
      settled = true
      cleanup()
      if (fn) fn(value)
    }

    const processEvent = (event) => {
      if (!event || settled) return
      if (event.type === 'error' || (event.ok === false && event.error)) {
        const message = event.message || event.error || 'Unknown error'
        finish(() => { onError?.(message); reject(new Error(message)) })
        return
      }
      switch (event.type) {
        case 'thinking': onThinking?.(event.content); break
        case 'text': onText?.(event.content); break
        case 'tool_progress': onToolProgress?.(event.tools || []); break
        case 'truncated': onTruncated?.(); break
        case 'done':
          finish(() => { onDone?.(event); resolve(event) })
          break
        default: break // heartbeat and any future event types
      }
    }

    const schedule = (ms) => {
      if (cancelled || settled) return
      clearTimeout(pollTimer)
      if (!visible) return // job keeps running server-side; resume on visibilitychange
      pollTimer = setTimeout(pollOnce, ms)
    }

    const onVisibility = () => {
      visible = typeof document !== 'undefined' ? document.visibilityState !== 'hidden' : true
      if (visible && !settled && jobId) {
        backoff = POLL_MS
        clearTimeout(pollTimer)
        pollOnce() // catch up on everything that happened while backgrounded
      }
    }

    const pollOnce = async () => {
      if (cancelled || settled) return
      let data
      try {
        data = await fetchJSON(`/chat/jobs/${jobId}?after_seq=${lastSeq}`)
      } catch (err) {
        if (cancelled || settled) return
        // Transient network failure — retry with backoff (job survives server-side)
        schedule(backoff)
        backoff = Math.min(backoff * 2, 10000)
        return
      }
      if (cancelled || settled) return
      backoff = POLL_MS
      const d = data?.data || {}
      if (Array.isArray(d.events)) {
        for (const ev of d.events) {
          if (ev?.seq) lastSeq = Math.max(lastSeq, ev.seq)
          processEvent(ev)
          if (settled) return
        }
      }
      if (d.status === 'done' || d.status === 'failed') {
        if (!settled && d.status === 'done' && d.done) {
          // Terminal event may have been missed (other worker / eviction) —
          // synthesize it from the final snapshot.
          finish(() => {
            const ev = {
              type: 'done',
              usage: d.done.usage || {},
              cost: d.done.cost,
              model: d.done.model,
              tool_results: d.done.tool_results || [],
              finish_reason: d.done.finish_reason || '',
              final_content: d.done.content || '',
              final_reasoning: d.done.reasoning || '',
            }
            onDone?.(ev)
            resolve(ev)
          })
        } else if (!settled) {
          finish(() => { onError?.(d.error || 'Chat job failed.'); reject(new Error(d.error || 'Chat job failed.')) })
        }
        return
      }
      // Still running — poll again shortly (only while visible)
      schedule(POLL_MS)
    }

    // Stop button / caller abort → cancel the job server-side too
    if (signal) {
      abortHandler = () => {
        cancelled = true
        cleanup()
        if (jobId) {
          fetch(`/api/v1/chat/jobs/${jobId}/cancel`, { method: 'POST' }).catch(() => {})
        }
        const err = new Error('Chat request aborted')
        err.name = 'AbortError'
        reject(err)
      }
      if (signal.aborted) abortHandler()
      else signal.addEventListener('abort', abortHandler)
    }
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', onVisibility)

    // Create the background job, then start polling
    fetchJSON('/chat/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, model, max_tokens, temperature, disabled_tools, scopes, mode, session_id, client_message_id }),
    }).then((res) => {
      if (cancelled) return
      const d = res?.data || {}
      if (!d.job_id) throw new Error('Chat job was not created')
      jobId = d.job_id
      lastSeq = d.seq || 0
      pollOnce()
    }).catch((err) => {
      if (cancelled) return
      finish(() => { onError?.(err.message || 'Failed to start chat.'); reject(err) })
    })
  })
}

/**
 * Non-streaming chat via the background job endpoint — returns the final
 * {content, reasoning_content, usage, cost, model, finish_reason,
 * tool_results}. Also survives phone minimize (job runs server-side).
 */
export async function chatComplete(messages, opts = {}) {
  const result = await chatStream(messages, opts)
  return {
    content: result.final_content || '',
    reasoning_content: result.final_reasoning || '',
    usage: result.usage,
    cost: result.cost,
    model: result.model,
    finish_reason: result.finish_reason || '',
    tool_results: result.tool_results || [],
  }
}
