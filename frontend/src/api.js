const BASE = '/api/v1'
const TIMEOUT_MS = 10_000

async function fetchJSON(url, options = {}) {
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
      throw new Error(`API ${res.status}: ${body.slice(0, 200)}`)
    }
    return res.json()
  } catch (err) {
    if (err.name === 'AbortError') {
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

export function conversationCreate(data = {}) {
  return fetchJSON('/conversations', {
    method: 'POST',
    body: JSON.stringify({ title: data.title || '', theme: data.theme || '' }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function conversationAddMessage(sessionId, role, content, metadata) {
  return fetchJSON(`/conversations/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ role, content, metadata: metadata || {} }),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function conversationList(page = 1, perPage = 20) {
  return fetchJSON(`/conversations?page=${page}&per_page=${perPage}`)
}

export function conversationGet(sessionId) {
  return fetchJSON(`/conversations/${sessionId}`)
}

export function conversationUpdate(sessionId, data) {
  return fetchJSON(`/conversations/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
    headers: { 'Content-Type': 'application/json' },
  })
}

export function conversationDelete(sessionId) {
  return fetchJSON(`/conversations/${sessionId}`, { method: 'DELETE' })
}

export function conversationConnections(sessionId) {
  return fetchJSON(`/conversations/${sessionId}/connections`)
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

export function chat(messages, opts = {}) {
  const { model = 'deepseek-v4-flash', max_tokens = 30000, temperature = 0.7, signal } = opts
  // LLM calls need longer timeout — use provided signal or create one with 60s
  const controller = signal ? null : new AbortController()
  const timer = controller ? setTimeout(() => controller.abort(), 120_000) : null
  return fetchJSON('/chat', {
    method: 'POST',
    body: JSON.stringify({ messages, model, max_tokens, temperature, disabled_tools: opts.disabled_tools || [] }),
    headers: { 'Content-Type': 'application/json' },
    signal: controller ? controller.signal : signal,
  }).finally(() => { if (timer) clearTimeout(timer) })
}

