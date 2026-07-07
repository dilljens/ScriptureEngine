import React, { useEffect, useState, useRef, useCallback } from 'react'

export default function VerseAudioPlayer({ verseId, verseTextHebrew, autoPlay }) {
  const [alignment, setAlignment] = useState(null)
  const [currentWordIdx, setCurrentWordIdx] = useState(-1)
  const [playing, setPlaying] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const audioRef = useRef(null)
  const animFrameRef = useRef(null)

  // Load alignment data
  useEffect(() => {
    if (!verseId) return
    setLoading(true)
    setError(null)
    fetch(`/api/v1/audio/align/${verseId}`)
      .then(r => r.ok ? r.json() : Promise.reject('Not found'))
      .then(d => { setAlignment(d.data); setLoading(false) })
      .catch(e => { setError(e); setLoading(false) })
  }, [verseId])

  // Track audio position to highlight current word
  const updateWord = useCallback(() => {
    if (!audioRef.current || !alignment) return
    const t = audioRef.current.currentTime
    const idx = alignment.words.findIndex(w => t >= w.start && t < w.end)
    setCurrentWordIdx(idx)
    if (audioRef.current.ended) {
      setPlaying(false)
      setCurrentWordIdx(-1)
      return
    }
    animFrameRef.current = requestAnimationFrame(updateWord)
  }, [alignment])

  const togglePlay = () => {
    if (!audioRef.current) return
    if (playing) {
      audioRef.current.pause()
      setPlaying(false)
      cancelAnimationFrame(animFrameRef.current)
    } else {
      audioRef.current.play()
      setPlaying(true)
      animFrameRef.current = requestAnimationFrame(updateWord)
    }
  }

  const seekTo = (idx) => {
    if (!audioRef.current || !alignment) return
    const word = alignment.words[idx]
    if (word) {
      audioRef.current.currentTime = word.start
      if (!playing) {
        audioRef.current.play()
        setPlaying(true)
        animFrameRef.current = requestAnimationFrame(updateWord)
      }
    }
  }

  useEffect(() => {
    return () => cancelAnimationFrame(animFrameRef.current)
  }, [])

  if (!verseId) return null

  return (
    <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 overflow-hidden">
      {/* Audio element (hidden) */}
      <audio ref={audioRef} preload="metadata" onEnded={() => { setPlaying(false); setCurrentWordIdx(-1) }}>
        <source src={`/api/v1/audio/play/${verseId}`} type="audio/wav" />
      </audio>

      {/* Playback controls */}
      <div className="flex items-center gap-3 p-3 border-b border-neutral-100 dark:border-neutral-800">
        <button
          onClick={togglePlay}
          disabled={loading || error}
          className="w-10 h-10 rounded-full bg-indigo-500 hover:bg-indigo-600 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 text-white flex items-center justify-center transition-colors shrink-0"
        >
          {loading ? (
            <span className="animate-pulse text-xs">...</span>
          ) : (
            <span className="text-lg">{playing ? '⏸' : '▶'}</span>
          )}
        </button>
        <div className="text-xs text-neutral-500 dark:text-neutral-400">
          {error ? (
            <span className="text-red-500">Audio not available</span>
          ) : alignment ? (
            <span>{alignment.word_count} words · {alignment.duration.toFixed(1)}s</span>
          ) : loading ? (
            <span className="animate-pulse">Loading...</span>
          ) : null}
        </div>
      </div>

      {/* Hebrew text with word highlighting */}
      {verseTextHebrew && alignment && (
        <div className="p-4 text-right" dir="rtl">
          <p className="text-xl leading-loose text-neutral-800 dark:text-neutral-200 font-serif">
            {alignment.words.map((w, i) => (
              <span
                key={i}
                onClick={() => seekTo(i)}
                className={`cursor-pointer transition-colors duration-150 rounded px-0.5 ${
                  i === currentWordIdx
                    ? 'bg-indigo-200 dark:bg-indigo-700 text-indigo-900 dark:text-indigo-100 shadow-sm'
                    : 'hover:bg-neutral-100 dark:hover:bg-neutral-800'
                }`}
              >
                {w.word}{' '}
              </span>
            ))}
          </p>
        </div>
      )}

      {/* Word list (small, for precise clicking) */}
      {alignment && (
        <div className="px-4 pb-3">
          <details className="text-xs text-neutral-400">
            <summary className="cursor-pointer hover:text-neutral-600">Word list</summary>
            <div className="mt-2 space-y-1 max-h-32 overflow-y-auto" dir="rtl">
              {alignment.words.map((w, i) => (
                <button
                  key={i}
                  onClick={() => seekTo(i)}
                  className={`block w-full text-right px-2 py-1 rounded text-sm transition-colors ${
                    i === currentWordIdx
                      ? 'bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300'
                      : 'hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300'
                  }`}
                >
                  <span className="float-left text-[10px] text-neutral-400 tabular-nums mt-0.5">
                    {w.start.toFixed(1)}s
                  </span>
                  {w.word}
                </button>
              ))}
            </div>
          </details>
        </div>
      )}

      {/* Fallback: no alignment, just show verse text */}
      {verseTextHebrew && !alignment && !loading && (
        <div className="p-4 text-right" dir="rtl">
          <p className="text-xl leading-loose text-neutral-800 dark:text-neutral-200 font-serif">
            {verseTextHebrew}
          </p>
        </div>
      )}
    </div>
  )
}
