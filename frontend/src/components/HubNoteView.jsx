/**
 * HubNoteView — curated learning paths through the connection graph.
 * 
 * Shows 14 thematic paths (covenant, temple, lamb_of_god, etc.) as
 * sequential steps. Each step shows a verse with explanation and TG topics.
 * Tracks progress via API.
 */
import React, { useState, useEffect } from 'react'

function fmtRef(ref) {
  if (!ref) return ''
  const parts = ref.split('.')
  if (parts.length >= 3) return `${parts[0].toUpperCase()} ${parts[1]}:${parts[2]}`
  return ref
}

export default function HubNoteView({ hubId, onNavigate, onGraph }) {
  const [notes, setNotes] = useState([])
  const [currentHub, setCurrentHub] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeStep, setActiveStep] = useState(null)

  // Load hubs on mount or when hubId changes
  const loadHubs = async () => {
    setLoading(true)
    try {
      const r = await fetch('/api/v1/hub-notes')
      const d = await r.json()
      if (d.ok) setNotes(d.data.notes)
      else setError(d.error || 'Failed to load')
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  const loadHub = async (id) => {
    setLoading(true)
    try {
      const r = await fetch(`/api/v1/hub-notes/${id}`)
      const d = await r.json()
      if (d.ok) setCurrentHub(d.data)
      else setError(d.error || 'Failed')
    } catch (e) { setError(e.message) }
    setLoading(false)
  }

  const completeStep = async (hubId, stepNumber) => {
    try {
      await fetch(`/api/v1/hub-notes/${hubId}/step/${stepNumber}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'default' }),
      })
      // Reload hub to reflect progress
      loadHub(hubId)
    } catch {}
  }

  useEffect(() => { if (hubId) loadHub(hubId); else loadHubs() }, [hubId])

  if (error) return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">{error}</div>
    </div>
  )

  if (loading) return (
    <div className="max-w-4xl mx-auto px-6 py-8 animate-pulse space-y-4">
      <div className="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-1/3" />
      <div className="h-32 bg-neutral-100 dark:bg-neutral-800 rounded-xl" />
    </div>
  )

  // Hub detail view
  if (currentHub) {
    const hub = currentHub
    const completed = hub.completed_steps || 0
    const total = hub.total_steps || 0
    const pct = total > 0 ? Math.round(completed / total * 100) : 0

    return (
      <div className="max-w-4xl mx-auto px-6 py-8">
        <button onClick={() => setCurrentHub(null)} className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline mb-4 cursor-pointer">
          ← All Study Paths
        </button>

        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <span className="text-3xl">{hub.icon || '📖'}</span>
          <div>
            <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{hub.title}</h2>
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-0.5">{hub.description}</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-6 p-4 rounded-xl bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center justify-between text-xs text-neutral-500 mb-2">
            <span>Progress: {completed}/{total} steps</span>
            <span>{pct}%</span>
          </div>
          <div className="h-2 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
            <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>

        {/* TG topics */}
        {hub.tg_topics && hub.tg_topics.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-6">
            <span className="text-[9px] font-semibold uppercase tracking-wider text-neutral-400 self-center">Related Topics:</span>
            {hub.tg_topics.map(t => (
              <span key={t.slug} className="px-2 py-0.5 rounded-full bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 text-[10px] text-red-600 dark:text-red-400">
                🏷️ {t.name}
              </span>
            ))}
          </div>
        )}

        {/* Steps */}
        <div className="space-y-3">
          {hub.steps.map((step, i) => {
            const isCompleted = step.completed
            const isActive = activeStep === step.step_number
            return (
              <div key={step.step_number}
                className={`p-4 rounded-xl border-2 transition-all ${
                  isCompleted
                    ? 'border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-900/10'
                    : isActive
                      ? 'border-indigo-300 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/10'
                      : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-200 dark:hover:border-indigo-700'
                }`}>

                {/* Step header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      isCompleted
                        ? 'bg-green-500 text-white'
                        : 'bg-neutral-200 dark:bg-neutral-700 text-neutral-500'
                    }`}>
                      {isCompleted ? '✓' : step.step_number}
                    </span>
                    <span className="text-sm font-medium text-neutral-800 dark:text-neutral-200">{step.title}</span>
                    <span className="text-[9px] text-neutral-400 font-mono">{fmtRef(step.verse_id)}</span>
                    {step.connection_type && (
                      <span className="text-[8px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-500">
                        {step.connection_type.replace(/_/g, ' ')}
                      </span>
                    )}
                    {step.pa_r_de_s_level && (
                      <span className="text-[8px] px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/30 text-indigo-500">
                        {step.pa_r_de_s_level}
                      </span>
                    )}
                  </div>
                  {isCompleted && <span className="text-[10px] text-green-600 font-medium">Complete ✓</span>}
                </div>

                {/* Verse text */}
                {step.verse_text && (
                  <div className="ml-8 mb-3 p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700 text-xs leading-relaxed text-neutral-700 dark:text-neutral-300 italic">
                    “{step.verse_text}”
                  </div>
                )}

                {/* Explanation */}
                <p className="ml-8 text-xs text-neutral-600 dark:text-neutral-400 leading-relaxed mb-2">
                  {step.explanation}
                </p>

                {/* Step TG topics */}
                {step.tg_topic_ids && step.tg_topic_ids.length > 0 && (
                  <div className="ml-8 flex flex-wrap gap-1 mt-1">
                    {step.tg_topic_ids.map(tid => (
                      <span key={tid} className="text-[8px] px-1 py-0.5 rounded bg-red-50 dark:bg-red-900/20 text-red-500">
                        {tid.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}

                {/* Actions */}
                <div className="ml-8 mt-2 flex gap-2">
                  {!isCompleted && (
                    <button onClick={() => completeStep(hub.id, step.step_number)}
                      className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-medium cursor-pointer transition-colors">
                      Mark Complete ✓
                    </button>
                  )}
                  {onNavigate && (
                    <button onClick={() => onNavigate?.(step.verse_id)}
                      className="px-3 py-1 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 text-[10px] font-medium cursor-pointer transition-colors">
                      Open Verse
                    </button>
                  )}
                  {onGraph && (
                    <button onClick={() => onGraph?.(step.verse_id)}
                      className="px-3 py-1 rounded-lg bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 text-[10px] font-medium cursor-pointer transition-colors">
                      View Graph
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  // Hub listing view
  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 mb-2">Study Paths</h2>
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-6">
        Curated learning paths through the connection graph — trace themes across the canon.
      </p>

      {notes.length === 0 && (
        <div className="p-8 text-center text-sm text-neutral-400">No study paths available.</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {notes.map(note => {
          const pct = note.total_steps > 0 ? Math.round(note.completed_steps / note.total_steps * 100) : 0
          return (
            <button key={note.id} onClick={() => loadHub(note.id)}
              className="text-left p-4 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 hover:border-indigo-300 dark:hover:border-indigo-600 hover:shadow-sm transition-all cursor-pointer group">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{note.icon || '📖'}</span>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 truncate">{note.title}</h3>
                  <p className="text-[10px] text-neutral-400">{note.total_steps} steps · {note.completed_steps} completed</p>
                </div>
              </div>
              <p className="text-xs text-neutral-500 dark:text-neutral-400 line-clamp-2 mb-2">{note.description}</p>
              {note.tg_topics && note.tg_topics.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {note.tg_topics.slice(0, 3).map(t => (
                    <span key={t.slug} className="text-[8px] px-1 py-0.5 rounded bg-red-50 dark:bg-red-900/20 text-red-500">
                      {t.name}
                    </span>
                  ))}
                </div>
              )}
              <div className="h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                <div className="h-full rounded-full bg-green-500 transition-all" style={{ width: `${pct}%` }} />
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
