import React, { useState, useRef, useEffect, useCallback } from 'react'
import { memorizeApi } from '../memorizeApi'

export default function PalaceBuilder({ palaceId, onBack }) {
  const [palace, setPalace] = useState(null)
  const [loci, setLoci] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [newLocusLabel, setNewLocusLabel] = useState('')
  const [placingLocus, setPlacingLocus] = useState(false)
  const [selectedLocus, setSelectedLocus] = useState(null)
  const [showVersePicker, setShowVersePicker] = useState(false)
  const [verseSearch, setVerseSearch] = useState('')
  const [verseResults, setVerseResults] = useState([])
  const canvasRef = useRef(null)
  const imgRef = useRef(null)

  const loadPalace = useCallback(async () => {
    setLoading(true)
    try {
      const data = await memorizeApi.get(`/palaces/${palaceId}`)
      setPalace(data.palace)
      setLoci(data.loci || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [palaceId])

  useEffect(() => { loadPalace() }, [loadPalace])

  // Handle canvas click to place a new locus
  const handleCanvasClick = useCallback((e) => {
    if (!placingLocus || !newLocusLabel.trim()) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = (e.clientY - rect.top) / rect.height

    memorizeApi.post(`/palaces/${palaceId}/loci`, {
      label: newLocusLabel.trim(),
      x_pct: Math.round(x * 1000) / 1000,
      y_pct: Math.round(y * 1000) / 1000,
    }).then(() => {
      setNewLocusLabel('')
      setPlacingLocus(false)
      loadPalace()
    }).catch(err => setError(err.message))
  }, [placingLocus, newLocusLabel, palaceId, loadPalace])

  // Assign verse to locus
  const handleAssignVerse = async (verseId) => {
    if (!selectedLocus) return
    try {
      await memorizeApi.post(`/loci/${selectedLocus.id}/assign`, { verse_id: verseId })
      setShowVersePicker(false)
      setVerseSearch('')
      loadPalace()
    } catch (err) {
      setError(err.message)
    }
  }

  // Search verses
  const handleVerseSearch = async (query) => {
    setVerseSearch(query)
    if (query.length < 3) return
    try {
      // Use the main scripture search API through the Vite proxy
      const res = await fetch(`/api/v1/search?q=${encodeURIComponent(query)}&limit=10`)
      const data = await res.json()
      setVerseResults(data.results || [])
    } catch {
      setVerseResults([])
    }
  }

  if (loading) {
    return <div className="p-4 text-neutral-400">Loading palace...</div>
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="rounded-lg bg-red-50 dark:bg-red-950/30 p-3 text-sm text-red-700 dark:text-red-400">{error}</div>
        <button onClick={onBack} className="mt-2 text-sm text-indigo-500 underline">Back</button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <button onClick={onBack} className="text-sm text-indigo-500 hover:text-indigo-600">← Palaces</button>
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{palace?.name}</h2>
      </div>

      {/* Photo canvas */}
      <div className="relative rounded-xl overflow-hidden border border-neutral-200 dark:border-neutral-800 bg-neutral-100 dark:bg-neutral-900 mb-4"
           style={{ minHeight: '300px' }}
           onClick={handleCanvasClick}>
        {palace?.photo_path ? (
          <img ref={imgRef} src={palace.photo_path} alt={palace.name} className="w-full" />
        ) : (
          <div className="flex items-center justify-center h-64 text-neutral-400 text-sm">
            Upload a photo to get started
          </div>
        )}

        {/* Render loci on canvas */}
        {loci.map(locus => (
          <button
            key={locus.id}
            className={`absolute w-8 h-8 -ml-4 -mt-4 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all ${
              selectedLocus?.id === locus.id
                ? 'bg-indigo-500 text-white border-indigo-300 scale-110 z-10'
                : 'bg-white/90 text-indigo-600 border-indigo-400 hover:scale-110'
            }`}
            style={{ left: `${locus.x_pct * 100}%`, top: `${locus.y_pct * 100}%` }}
            onClick={(e) => { e.stopPropagation(); setSelectedLocus(locus) }}
          >
            {locus.label[0]}
          </button>
        ))}

        {/* Placing mode crosshair */}
        {placingLocus && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-indigo-500 text-sm bg-white/80 dark:bg-neutral-900/80 px-3 py-1 rounded-full">
              Click to place "{newLocusLabel}"
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={newLocusLabel}
          onChange={e => setNewLocusLabel(e.target.value)}
          placeholder="Locus label..."
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100"
        />
        <button
          onClick={() => { if (newLocusLabel.trim()) setPlacingLocus(!placingLocus) }}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${
            placingLocus
              ? 'bg-red-500 text-white'
              : 'bg-indigo-500 text-white hover:bg-indigo-600'
          }`}
        >
          {placingLocus ? 'Cancel' : 'Place Locus'}
        </button>
      </div>

      {/* Selected locus panel */}
      {selectedLocus && (
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 p-3 mb-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{selectedLocus.label}</h3>
            <button
              onClick={() => setSelectedLocus(null)}
              className="text-xs text-neutral-400 hover:text-neutral-600"
            >×</button>
          </div>
          <p className="text-xs text-neutral-500 mb-2">Position: ({selectedLocus.x_pct}, {selectedLocus.y_pct})</p>
          {selectedLocus.verse_id ? (
            <div className="flex items-center justify-between">
              <span className="text-xs text-indigo-600 dark:text-indigo-400">{selectedLocus.verse_id}</span>
              <button
                onClick={() => {
                  memorizeApi.post(`/loci/${selectedLocus.id}/assign`, { verse_id: '' })
                  setSelectedLocus({ ...selectedLocus, verse_id: null })
                  loadPalace()
                }}
                className="text-xs text-red-500 underline"
              >Remove</button>
            </div>
          ) : (
            <button
              onClick={() => setShowVersePicker(true)}
              className="text-xs text-indigo-500 hover:text-indigo-600 underline"
            >Assign verse</button>
          )}
        </div>
      )}

      {/* Verse picker modal */}
      {showVersePicker && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center pt-20 px-4">
          <div className="bg-white dark:bg-neutral-900 rounded-xl w-full max-w-md p-4 shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Pick a verse</h3>
              <button onClick={() => setShowVersePicker(false)} className="text-neutral-400">×</button>
            </div>
            <input
              type="text"
              value={verseSearch}
              onChange={e => handleVerseSearch(e.target.value)}
              placeholder="Search verses..."
              className="w-full px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 mb-2"
              autoFocus
            />
            <div className="max-h-60 overflow-y-auto">
              {verseResults.map(v => (
                <button
                  key={v.id}
                  onClick={() => handleAssignVerse(v.id)}
                  className="w-full text-left p-2 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-xs"
                >
                  <span className="font-medium text-indigo-600 dark:text-indigo-400">{v.id}</span>
                  <span className="text-neutral-500 ml-2">{v.text?.slice(0, 80)}</span>
                </button>
              ))}
              {verseSearch.length >= 3 && verseResults.length === 0 && (
                <p className="text-xs text-neutral-400 text-center py-4">No results</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Loci list */}
      <div className="mt-4">
        <h3 className="text-xs font-medium text-neutral-500 mb-2 uppercase tracking-wider">Loci ({loci.length})</h3>
        <div className="space-y-1">
          {loci.map(l => (
            <div key={l.id}
              className={`flex items-center gap-2 p-2 rounded-lg text-xs cursor-pointer ${
                selectedLocus?.id === l.id ? 'bg-indigo-50 dark:bg-indigo-950/30' : 'hover:bg-neutral-50 dark:hover:bg-neutral-800'
              }`}
              onClick={() => setSelectedLocus(l)}
            >
              <span className="w-6 h-6 rounded-full bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-[10px] font-bold">
                {l.label[0]}
              </span>
              <span className="text-neutral-700 dark:text-neutral-300 flex-1">{l.label}</span>
              <span className="text-neutral-400">{l.verse_id || '—'}</span>
            </div>
          ))}
          {loci.length === 0 && (
            <p className="text-xs text-neutral-400 text-center py-4">No loci yet. Add one above.</p>
          )}
        </div>
      </div>
    </div>
  )
}
