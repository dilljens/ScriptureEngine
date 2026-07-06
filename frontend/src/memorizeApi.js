/**
 * API client for the Go memorization microservice.
 * All requests go through Vite proxy → /api/memorize/* → localhost:8090
 */
const BASE = '/api/memorize'
const TIMEOUT_MS = 15_000

async function fetchJSON(url, options = {}) {
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
      throw new Error(`Memorize API ${res.status}: ${body.slice(0, 200)}`)
    }
    const ct = res.headers.get('content-type') || ''
    if (ct.includes('application/json')) return res.json()
    return res
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error(`Memorize API request to ${url} timed out`)
    }
    throw err
  } finally {
    clearTimeout(timer)
  }
}

export const memorizeApi = {
  get: (url) => fetchJSON(url),
  post: (url, body) => fetchJSON(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }),
  upload: (url, formData) => fetch(url, {
    method: 'POST',
    body: formData,
  }),
}
