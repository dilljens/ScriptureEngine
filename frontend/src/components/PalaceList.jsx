import React, { useEffect, useState } from 'react'
import { memorizeApi } from '../memorizeApi'

export default function PalaceList({ onSelect, onCreate }) {
  const [palaces, setPalaces] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')

  const loadPalaces = () => {
    setLoading(true)
    memorizeApi.get('/palaces')
      .then(data => { setPalaces(data.palaces || []); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }

  useEffect(() => { loadPalaces() }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    try {
      const result = await memorizeApi.post('/palaces', { name: newName.trim(), photo_path: '' })
      setShowCreate(false)
      setNewName('')
      if (result.palace_id) onSelect(result.palace_id)
      loadPalaces()
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) {
    return <div className="p-4 text-sm text-neutral-400 text-center">Loading palaces...</div>
  }

  return (
    <div className="max-w-2xl mx-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Memory Palaces</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 text-sm rounded-lg bg-indigo-500 text-white hover:bg-indigo-600"
        >+ New</button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950/30 p-3 text-sm text-red-700 dark:text-red-400 mb-4">{error}</div>
      )}

      {showCreate && (
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Palace name..."
            className="flex-1 px-3 py-2 text-sm rounded-lg border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 text-neutral-900 dark:text-neutral-100"
            autoFocus
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
          />
          <button onClick={handleCreate} className="px-3 py-2 text-sm rounded-lg bg-green-500 text-white hover:bg-green-600">Create</button>
        </div>
      )}

      <div className="grid gap-3">
        {palaces.map(p => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className="flex items-start gap-3 p-4 rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 hover:shadow-sm transition-shadow text-left w-full"
          >
            <div className="w-12 h-12 rounded-lg bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-xl shrink-0">
              🏛️
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{p.name}</h3>
              <p className="text-xs text-neutral-500 mt-0.5">Created {new Date(p.created_at).toLocaleDateString()}</p>
            </div>
          </button>
        ))}
        {palaces.length === 0 && !loading && (
          <div className="text-center py-12 text-neutral-400">
            <div className="text-3xl mb-2">🏛️</div>
            <p className="text-sm">No palaces yet.</p>
            <p className="text-xs mt-1">Create one to start building your memory palace.</p>
          </div>
        )}
      </div>
    </div>
  )
}
