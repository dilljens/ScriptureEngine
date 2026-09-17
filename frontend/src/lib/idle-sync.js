/**
 * idle-sync.js — cross-device sync for the idle workshop (localStorage roamer).
 *
 * Server holds last-write-wins by updated_at. Pull on mount adopts the
 * server copy only when strictly newer than local lastSeen (a fresh phone
 * never clobbers a rich computer, and vice versa). Pushes are debounced;
 * pagehide flushes via sendBeacon (POST + session_token in body, since
 * beacons can't set headers). Logged-out play stays local-only, unchanged.
 */
import { currentSessionToken } from '../api'

function authed(init = {}) {
  const token = currentSessionToken()
  if (!token) return null
  return { ...init, headers: { ...(init.headers || {}), Authorization: `Bearer ${token}` } }
}

/** Pull server copy. Returns {state, updated_at} or null (logged out / none / error). */
export async function pullIdleState() {
  const req = authed()
  if (!req) return null
  try {
    const r = await fetch('/api/v1/hebrew/idle-state', req)
    const d = await r.json()
    if (d.ok && d.data?.state) return { state: d.data.state, updated_at: d.data.updated_at }
  } catch {}
  return null
}

/** Push local copy. Returns server updated_at or null. Fire-and-forget safe. */
export async function pushIdleState(state) {
  const token = currentSessionToken()
  if (!token || !state) return null
  try {
    const r = await fetch('/api/v1/hebrew/idle-state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ state }),
    })
    const d = await r.json()
    return d.ok ? d.data?.updated_at || true : null
  } catch {
    return null
  }
}

/** pagehide-safe push (sendBeacon POSTs; token rides in the body). */
export function beaconIdleState(state) {
  const token = currentSessionToken()
  if (!token || !state || typeof navigator === 'undefined' || !navigator.sendBeacon) return false
  try {
    const blob = new Blob([JSON.stringify({ state, session_token: token })], { type: 'application/json' })
    return navigator.sendBeacon('/api/v1/hebrew/idle-state', blob)
  } catch {
    return false
  }
}

/** Should the server copy replace local? Strictly-newer wins. */
export function serverIsNewer(serverUpdatedAt, localLastSeen) {
  if (!serverUpdatedAt) return false
  if (!localLastSeen) return true
  // Server stamps UTC "YYYY-MM-DD HH:MM:SS" (no zone) — parse as UTC.
  const serverMs = Date.parse(String(serverUpdatedAt).replace(' ', 'T') + 'Z')
  if (!Number.isFinite(serverMs)) return false
  return serverMs > (localLastSeen || 0)
}
