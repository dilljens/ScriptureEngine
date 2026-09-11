/**
 * analytics.js — local event log for Hebrew games (Track D, Phase D1).
 *
 * Every gameplay + learning event in BOTH games (Classic study and Games)
 * is appended here with mode/game tags, so balancing can be tuned from logs.
 * Local-first: ring buffer in localStorage (cap 2000), no backend needed.
 * Backend batch upload is Track D Phase D3.
 *
 * Event shape: {t, session, mode, game, type, data}
 *   mode: 'classic' | 'game' (from localStorage hebrew-learn-mode)
 *   game: game id (from localStorage hebrew-game-id) or 'classic'
 *
 * Node-safe: storage falls back to memory when window is undefined,
 * so the self-check below runs under plain `node`.
 */

const STORAGE_KEY = 'hebrew-analytics-v1'
const SENT_KEY = 'hebrew-analytics-sent'
const MAX_EVENTS = 2000

function getStore() {
  if (typeof window !== 'undefined' && window.localStorage) return window.localStorage
  return null
}

const memStore = {}
function readRaw() {
  try {
    const s = getStore()
    if (s) return s.getItem(STORAGE_KEY)
    return memStore[STORAGE_KEY] || null
  } catch {
    return memStore[STORAGE_KEY] || null
  }
}
function writeRaw(v) {
  try {
    const s = getStore()
    if (s) { s.setItem(STORAGE_KEY, v); return }
    memStore[STORAGE_KEY] = v
  } catch {
    memStore[STORAGE_KEY] = v
  }
}

let sessionId = null
function getSession() {
  if (sessionId) return sessionId
  sessionId = `s-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`
  return sessionId
}

function currentModeGame() {
  let mode = 'classic'
  let game = 'classic'
  try {
    const s = getStore()
    if (s) {
      mode = s.getItem('hebrew-learn-mode') || 'classic'
      game = mode === 'game' ? (s.getItem('hebrew-game-id') || 'emet') : 'classic'
    }
  } catch {}
  return { mode, game }
}

export function readLog() {
  try {
    const raw = readRaw()
    if (!raw) return []
    const arr = JSON.parse(raw)
    return Array.isArray(arr) ? arr : []
  } catch {
    return []
  }
}

/** Append one event. Returns the event. */
export function logEvent(type, data = {}) {
  const { mode, game } = currentModeGame()
  const ev = { t: Date.now(), session: getSession(), mode, game, type, data }
  const log = readLog()
  log.push(ev)
  while (log.length > MAX_EVENTS) log.shift()
  try {
    writeRaw(JSON.stringify(log))
  } catch {}
  return ev
}

/** Mark a session start (call once on mount, e.g. HebrewLearnView). */
export function markSessionStart(extra = {}) {
  const touch = typeof window !== 'undefined' && ('ontouchstart' in window || (window.navigator && window.navigator.maxTouchPoints > 0))
  return logEvent('session_start', {
    touch: !!touch,
    w: typeof window !== 'undefined' ? window.innerWidth : 0,
    ...extra,
  })
}

// ── Server flush (Track D3): append-only JSONL so logs survive the browser ──
function getSent() {
  try {
    const s = getStore()
    if (s) return parseInt(s.getItem(SENT_KEY) || '0', 10) || 0
    return memStore[SENT_KEY] ? parseInt(memStore[SENT_KEY], 10) || 0 : 0
  } catch { return 0 }
}
function setSent(n) {
  try {
    const s = getStore()
    if (s) { s.setItem(SENT_KEY, String(n)); return }
  } catch {}
  memStore[SENT_KEY] = String(n)
}

/** Flush unsent events to the backend. Silent, fire-and-forget. */
export async function flushLog({ beacon = false } = {}) {
  const log = readLog()
  const sent = getSent()
  if (sent >= log.length) return 0
  const batch = log.slice(sent)
  if (!batch.length) return 0
  try {
    const payload = JSON.stringify({ events: batch })
    if (beacon && typeof navigator !== 'undefined' && navigator.sendBeacon) {
      navigator.sendBeacon('/api/v1/hebrew/analytics', new Blob([payload], { type: 'application/json' }))
      setSent(log.length)
      return batch.length
    }
    const res = await fetch('/api/v1/hebrew/analytics', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload,
    })
    if (res.ok) { setSent(log.length); return batch.length }
  } catch {}
  return 0
}

/** Start periodic flushing (browser only). Returns a stop function. */
export function startAutoFlush(intervalMs = 8000) {
  if (typeof window === 'undefined') return () => {}
  const t = setInterval(() => { flushLog() }, intervalMs)
  const onHide = () => { flushLog({ beacon: true }) }
  document.addEventListener('visibilitychange', onHide)
  window.addEventListener('pagehide', onHide)
  return () => {
    clearInterval(t)
    document.removeEventListener('visibilitychange', onHide)
    window.removeEventListener('pagehide', onHide)
    flushLog({ beacon: true })
  }
}

/** Download the full log as JSON (human + script readable). */
export function exportLog() {
  const log = readLog()
  const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), count: log.length, events: log }, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `hebrew-analytics-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 5000)
  return log.length
}

/** Summarize one session for quick balance reads. */
export function summarizeSession(events, session) {
  const rows = events.filter(e => !session || e.session === session)
  const byType = {}
  for (const e of rows) byType[e.type] = (byType[e.type] || 0) + 1
  const answers = rows.filter(e => e.type === 'answer')
  const correct = answers.filter(e => e.data && e.data.correct).length
  const spanMin = rows.length > 1 ? (rows[rows.length - 1].t - rows[0].t) / 60000 : 0
  return {
    session: session || 'all',
    events: rows.length,
    span_min: Math.round(spanMin * 10) / 10,
    by_type: byType,
    answers: answers.length,
    accuracy: answers.length ? Math.round((correct / answers.length) * 100) / 100 : null,
    modes: [...new Set(rows.map(e => e.mode))],
    games: [...new Set(rows.map(e => e.game))],
  }
}

// Self-check (node): memory-backed, no window needed.
if (typeof process !== 'undefined' && process.argv?.[1]?.endsWith('analytics.js')) {
  const a = (cond, msg) => { if (!cond) { console.error('FAIL:', msg); process.exit(1) } else console.log('ok:', msg) }
  sessionId = null
  const e1 = logEvent('answer', { correct: true, ms: 1200 })
  a(e1.type === 'answer' && e1.session && e1.t > 0, 'answer event logged with session+time')
  logEvent('purchase', { letter: 0, n: 1, spend: 10 })
  const log = readLog()
  a(log.length === 2, 'ring buffer holds events')
  const s = summarizeSession(log)
  a(s.answers === 1 && s.accuracy === 1 && s.by_type.purchase === 1, 'session summary: accuracy + counts')
  for (let i = 0; i < 2500; i++) logEvent('tick', { i })
  a(readLog().length === MAX_EVENTS, `ring buffer caps at ${MAX_EVENTS}`)
  a(readLog()[0].data.i === 500, 'oldest events evicted first')
}
