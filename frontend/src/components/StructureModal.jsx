import React, { useState, useEffect } from 'react'
import { getBooks } from '../api'

export default function StructureModal({ open, onClose, onNavigate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    getBooks()
      .then(res => setData(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-12 pb-8 bg-black/30 dark:bg-black/50" onClick={onClose}>
      <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-y-auto mx-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Isaiah Book Structure</h2>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 text-xl leading-none cursor-pointer">&times;</button>
        </div>
        {loading && <div className="p-6 text-sm text-neutral-400 text-center">Loading structures...</div>}
        {error && <div className="p-6 text-sm text-red-500">{error}</div>}
        {data && (
          <div className="p-6 space-y-6">
            {data.structures?.map(s => (
              <div key={s.id} className="border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
                <div className="flex items-center gap-3 px-4 py-3 bg-neutral-50 dark:bg-neutral-800/50 border-b border-neutral-200 dark:border-neutral-700">
                  <span className="text-sm font-mono text-indigo-600 dark:text-indigo-400 font-bold">⟷</span>
                  <span className="font-medium text-neutral-800 dark:text-neutral-200">{s.scholar}</span>
                  <span className="text-xs text-neutral-400 dark:text-neutral-500 ml-auto">confidence: {s.confidence}</span>
                </div>
              </div>
            ))}
            {(!data.structures || data.structures.length === 0) && (
              <p className="text-sm text-neutral-400 text-center">No structures available</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
