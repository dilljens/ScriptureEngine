import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * useVerseReadAlong — per-verse audio playback with inline word highlighting.
 *
 * Fetches the verse's read-along data (word timestamps + Shmueloff raw audio),
 * exposes a togglePlay() and seekWord(i) control, and tracks curWord as the
 * audio plays so the UI can highlight the word being read.
 *
 * Returns { readAlong, playState, curWord, togglePlay, seekWord, hasAudio }.
 */
export function useVerseReadAlong(verseId, enabled = true) {
  const [readAlong, setReadAlong] = useState(null)      // {word_timestamps, duration, raw_audio_url, audio_url}
  const [playState, setPlayState] = useState('idle')    // idle | loading | playing
  const [curWord, setCurWord] = useState(-1)
  const audioRef = useRef(null)
  const animRef = useRef(null)

  // Load alignment for this verse
  useEffect(() => {
    if (!verseId || !enabled) return
    let alive = true
    fetch(`/api/v1/read-along/${verseId}`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (alive && d?.data) setReadAlong(d.data) })
      .catch(() => {})
    return () => { alive = false }
  }, [verseId, enabled])

  // Track current word while playing
  const tick = useCallback(() => {
    if (!audioRef.current || !readAlong?.word_timestamps) return
    const t = audioRef.current.currentTime
    const idx = readAlong.word_timestamps.findIndex(w => t >= w.start && t < w.end)
    setCurWord(idx)
    if (audioRef.current.ended) {
      setPlayState('idle'); setCurWord(-1); return
    }
    animRef.current = requestAnimationFrame(tick)
  }, [readAlong])

  const togglePlay = useCallback(() => {
    if (playState === 'loading') return
    if (playState === 'playing') {
      audioRef.current?.pause(); setPlayState('idle'); setCurWord(-1)
      cancelAnimationFrame(animRef.current)
      return
    }
    if (!audioRef.current) {
      const src = readAlong?.raw_audio_url
        || readAlong?.audio_url
        || `/api/v1/audio/play/${verseId}`
      const a = new Audio(src)
      a.preload = 'metadata'
      a.onended = () => { setPlayState('idle'); setCurWord(-1) }
      a.onerror = () => { setPlayState('idle') }
      audioRef.current = a
      setPlayState('loading')
      a.play().then(() => {
        setPlayState('playing')
        animRef.current = requestAnimationFrame(tick)
      }).catch(() => setPlayState('idle'))
    } else {
      audioRef.current.currentTime = 0
      audioRef.current.play()
      setPlayState('playing')
      animRef.current = requestAnimationFrame(tick)
    }
  }, [playState, readAlong, verseId, tick])

  const seekWord = useCallback((idx) => {
    const w = readAlong?.word_timestamps?.[idx]
    if (!w || !audioRef.current) return
    audioRef.current.currentTime = w.start
    if (playState !== 'playing') {
      audioRef.current.play()
      setPlayState('playing')
      animRef.current = requestAnimationFrame(tick)
    }
  }, [readAlong, playState, tick])

  // Cleanup on unmount
  useEffect(() => {
    return () => { cancelAnimationFrame(animRef.current); audioRef.current?.pause() }
  }, [])

  const hasAudio = !!(readAlong?.raw_audio_url || readAlong?.audio_url)
  return { readAlong, playState, curWord, togglePlay, seekWord, hasAudio }
}
