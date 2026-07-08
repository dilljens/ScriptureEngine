import React, { useState, useEffect, useRef, useCallback } from 'react'

/**
 * WordPopup — appears when clicking a Hebrew word.
 * Shows: Hebrew word, transliteration, English gloss,
 * Strong's definition, morphology, root, gematria.
 * Plays audio for that specific word from the Shmueloff recording.
 */
export default function WordPopup({ data, onClose, readAlongData }) {
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef(null)
  const popupRef = useRef(null)

  // Close on Escape
  useEffect(() => {
    function handleKey(e) { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  // Close on click outside
  useEffect(() => {
    function handleClick(e) {
      if (popupRef.current && !popupRef.current.contains(e.target)) onClose()
    }
    // Delay to avoid immediate close from the click that opened it
    const timer = setTimeout(() => document.addEventListener('mousedown', handleClick), 100)
    return () => { clearTimeout(timer); document.removeEventListener('mousedown', handleClick) }
  }, [onClose])

  const playWordAudio = useCallback(() => {
    if (!audioRef.current || !readAlongData?.word_timestamps) return
    const ts = readAlongData.word_timestamps[data.wordIndex]
    if (!ts) return

    // Build play-raw URL for this word
    const rawAudioUrl = readAlongData.raw_audio_url
    if (!rawAudioUrl) return

    // Parse the base URL from raw_audio_url to reuse
    const baseUrl = rawAudioUrl.split('?')[0]
    const url = `${baseUrl}?start=${ts.start}&end=${ts.end}`

    if (playing) {
      audioRef.current.pause()
      audioRef.current = null
      setPlaying(false)
    } else {
      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => { setPlaying(false); audioRef.current = null }
      audio.onerror = () => { setPlaying(false); audioRef.current = null }
      audio.play().then(() => setPlaying(true)).catch(() => setPlaying(false))
    }
  }, [data.wordIndex, readAlongData, playing])

  useEffect(() => {
    return () => { if (audioRef.current) { audioRef.current.pause(); audioRef.current = null } }
  }, [])

  const lemma = data.lemma || ''
  const strongsNum = lemma.replace(/^[a-z]\//, '').split(' ')[0]
  const strongsLabel = strongsNum ? `H${strongsNum}` : ''

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/20 dark:bg-black/40">
      <div ref={popupRef}
        className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 max-w-sm w-full overflow-hidden animate-in fade-in zoom-in duration-150"
        dir="rtl"
      >
        {/* Word header */}
        <div className="p-5 text-center border-b border-neutral-100 dark:border-neutral-800">
          <div className="text-3xl font-serif leading-relaxed mb-2"
            style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
            {data.word}
          </div>
          {data.transliteration && (
            <div className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-1" dir="ltr">
              {data.transliteration}
            </div>
          )}
          {data.english && (
            <div className="text-xs text-blue-600 dark:text-blue-400 font-medium" dir="ltr">
              {data.english}
            </div>
          )}
        </div>

        {/* Word details */}
        <div className="p-4 space-y-3 text-sm" dir="ltr">
          {/* Strong's + POS */}
          <div className="flex items-center gap-2 flex-wrap">
            {strongsLabel && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300">
                {strongsLabel}
              </span>
            )}
            {data.pos && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400">
                {data.pos}
              </span>
            )}
            {data.root && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300">
                Root: {data.root}
              </span>
            )}
            {data.morph && (
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-100 dark:bg-cyan-900/40 text-cyan-700 dark:text-cyan-300">
                {data.morph}
              </span>
            )}
          </div>

          {/* Gematria */}
          {data.gematria && (data.gematria.standard || data.gematria.ordinal || data.gematria.reduced) && (
            <div className="flex items-center gap-2 text-[10px] text-neutral-500 dark:text-neutral-400 border-t border-neutral-100 dark:border-neutral-800 pt-2">
              {data.gematria.standard != null && <span>Standard: {data.gematria.standard}</span>}
              {data.gematria.ordinal != null && <span>Ordinal: {data.gematria.ordinal}</span>}
              {data.gematria.reduced != null && <span>Reduced: {data.gematria.reduced}</span>}
            </div>
          )}

          {/* Definition */}
          {data.definition && (
            <div className="border-t border-neutral-100 dark:border-neutral-800 pt-2">
              <p className="text-xs leading-relaxed text-neutral-600 dark:text-neutral-400">
                {data.definition}
              </p>
            </div>
          )}

          {/* Audio play button */}
          {readAlongData?.word_timestamps?.[data.wordIndex] && (
            <div className="border-t border-neutral-100 dark:border-neutral-800 pt-3">
              <button
                onClick={playWordAudio}
                className="w-full py-2 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium transition-colors flex items-center justify-center gap-2"
              >
                <span>{playing ? '⏸' : '▶'}</span>
                <span>{playing ? 'Playing...' : 'Play this word'}</span>
              </button>
            </div>
          )}
        </div>

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 left-3 w-7 h-7 rounded-full bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 text-neutral-500 dark:text-neutral-400 flex items-center justify-center text-xs transition-colors"
        >
          ✕
        </button>
      </div>
    </div>
  )
}
