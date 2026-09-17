/**
 * audio-pool.js — singleton audio for Hebrew learning sounds (perf Track D2).
 *
 * Before: every letter buy / quiz popup / replay did `fetch(url)` +
 * `new Audio(url)` — a network round-trip and a fresh media element per
 * event. Now: letter URLs are fetched once and shared; one reusable Audio
 * element plays them (latest play wins, correct for short blips).
 * Other components (PassageReader, AnkiReview, …) can adopt these helpers
 * incrementally — same behavior, fewer requests.
 */

const urlCache = new Map() // glyph -> audio url ("" = known missing)
const inflight = new Map() // glyph -> pending fetch promise
let el = null

function element() {
  if (!el && typeof Audio !== 'undefined') el = new Audio()
  return el
}

/** Fetch (and cache) the audio URL for a Hebrew glyph. Null when missing. */
export async function fetchAudioUrl(glyph) {
  if (!glyph) return null
  if (urlCache.has(glyph)) return urlCache.get(glyph) || null
  if (inflight.has(glyph)) return inflight.get(glyph)
  const p = fetch(`/api/v1/hebrew/audio/${encodeURIComponent(glyph)}`)
    .then(r => r.json())
    .then(d => {
      const url = d?.data?.audio_url || d?.audio_url || null
      urlCache.set(glyph, url || '')
      inflight.delete(glyph)
      return url
    })
    .catch(() => {
      inflight.delete(glyph)
      return null
    })
  inflight.set(glyph, p)
  return p
}

/** Play a known URL through the shared element. Never throws. */
export async function playUrl(url) {
  if (!url) return
  try {
    const a = element()
    if (!a) return
    a.src = url
    await a.play()
  } catch {}
}

/** Fetch (cached) + play the audio for a Hebrew glyph. Never throws. */
export async function playHebrewAudio(glyph) {
  const url = await fetchAudioUrl(glyph)
  if (url) await playUrl(url)
}

/** Warm the cache without playing (hover/popup-open prefetch). */
export function prefetchHebrewAudio(glyph) {
  fetchAudioUrl(glyph).catch(() => {})
}
