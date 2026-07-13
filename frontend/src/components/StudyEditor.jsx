import React, { useState, useEffect, useCallback, useRef } from 'react'
import VersePreviewCard from './VersePreviewCard'
import StudyViewer from './StudyViewer'

/**
 * StudyEditor — full study creation/editing with LLM-assisted modification.
 *
 * The LLM can directly propose changes to the study via structured <study-action> blocks in its response.
 * Supported actions:
 *   {"action": "add_step", "step_number": 4, "verse": "num.19.2", "title": "...", "explanation": "..."}
 *   {"action": "remove_step", "step_number": 3}
 *   {"action": "update_step", "step_number": 2, "title": "...", "explanation": "..."}
 *   {"action": "reorder", "step_order": [3, 1, 2, 4]}
 *   {"action": "set_title", "title": "New Title"}
 *   {"action": "set_description", "description": "New description"}
 *
 * Props:
 *   study: initial study data (from API)
 *   guideId: study guide ID for API calls
 *   onSave: callback when study is changed
 *   onNavigate: (book, chapter) => void
 *   onOpenTab: (book, chapter, opts) => void
 *   showQuickAsk: boolean
 */
export default function StudyEditor({ study: initialStudy, guideId, onSave, onNavigate, onOpenTab, showQuickAsk }) {
  const [steps, setSteps] = useState(initialStudy?.steps || [])
  const [title, setTitle] = useState(initialStudy?.title || '')
  const [description, setDescription] = useState(initialStudy?.description || '')
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [qaInput, setQaInput] = useState('')
  const [qaMessages, setQaMessages] = useState([])
  const [qaWaiting, setQaWaiting] = useState(false)
  const [pendingActions, setPendingActions] = useState([])
  const [showPreview, setShowPreview] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState(null)
  const qaEndRef = useRef(null)

  // Auto-scroll QA
  useEffect(() => { qaEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [qaMessages])

  // Mark dirty when steps change
  useEffect(() => { setDirty(true) }, [steps, title, description])

  const addStep = useCallback(() => {
    setSteps(prev => [...prev, {
      step: prev.length + 1,
      verse: '',
      verse_text: '',
      title: '',
      explanation: '',
      connections: [],
      choices: [],
    }])
  }, [])

  const removeStep = useCallback((idx) => {
    setSteps(prev => {
      const filtered = prev.filter((_, i) => i !== idx)
      return filtered.map((s, i) => ({ ...s, step: i + 1 }))
    })
  }, [])

  const updateStep = useCallback((idx, field, value) => {
    setSteps(prev => prev.map((s, i) => i === idx ? { ...s, [field]: value } : s))
  }, [])

  const moveStep = useCallback((idx, direction) => {
    const newIdx = idx + direction
    if (newIdx < 0 || newIdx >= steps.length) return
    setSteps(prev => {
      const arr = [...prev]
      const [removed] = arr.splice(idx, 1)
      arr.splice(newIdx, 0, removed)
      return arr.map((s, i) => ({ ...s, step: i + 1 }))
    })
  }, [steps.length])

  const save = useCallback(async () => {
    setError(null)
    setSaving(true)
    try {
      // Save title/description first
      if (title !== initialStudy?.title || description !== initialStudy?.description) {
        await fetch(`/api/v1/studies/${guideId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, description }),
        })
      }
      // Bulk update steps
      const stepData = steps.map(s => ({
        verse: s.verse,
        title: s.title,
        explanation: s.explanation,
        connection_from: s.connection_from || '',
        connection_type: s.connection_type || '',
        connection_layer: s.connection_layer || '',
        choices: s.choices || [],
      }))
      const res = await fetch(`/api/v1/studies/${guideId}/steps`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: stepData }),
      })
      const data = await res.json()
      if (data.ok) {
        setDirty(false)
        onSave?.()
      }
    } catch (err) {
      setError(err.message || 'Save failed')
    } finally {
      setSaving(false)
    }
  }, [steps, title, description, guideId, initialStudy, onSave])

  // ─── LLM Integration ───

  // Parse <study-action> blocks from LLM response
  const parseActions = useCallback((text) => {
    const actions = []
    const regex = /<study-action>([\s\S]*?)<\/study-action>/g
    let match
    while ((match = regex.exec(text)) !== null) {
      try {
        const action = JSON.parse(match[1].trim())
        actions.push(action)
      } catch (e) {
        if (import.meta.env.DEV) { console.warn('Failed to parse study-action:', match[1], e) }
      }
    }
    return actions
  }, [])

  // Apply a single action to the study
  const applyAction = useCallback((action) => {
    switch (action.action) {
      case 'add_step': {
        const stepNum = action.step_number || steps.length + 1
        const newStep = {
          step: stepNum,
          verse: action.verse || '',
          verse_text: action.verse_text || '',
          book_title: action.book_title || '',
          title: action.title || '',
          explanation: action.explanation || '',
          connections: action.connections || [],
          choices: action.choices || [],
        }
        setSteps(prev => {
          const arr = [...prev]
          arr.splice(stepNum - 1, 0, newStep)
          return arr.map((s, i) => ({ ...s, step: i + 1 }))
        })
        break
      }
      case 'remove_step': {
        const idx = (action.step_number || 1) - 1
        setSteps(prev => prev.filter((_, i) => i !== idx).map((s, i) => ({ ...s, step: i + 1 })))
        break
      }
      case 'update_step': {
        const uIdx = (action.step_number || 1) - 1
        setSteps(prev => prev.map((s, i) => {
          if (i !== uIdx) return s
          return { ...s, ...action, step: s.step }
        }))
        break
      }
      case 'set_title':
        setTitle(action.title || '')
        break
      case 'set_description':
        setDescription(action.description || '')
        break
      case 'reorder': {
        if (!action.step_order) break
        // step_order is an array of current step numbers in new order
        setSteps(prev => {
          const map = {}
          prev.forEach(s => { map[s.step] = s })
          const reordered = action.step_order.map(n => ({ ...map[n], step: undefined }))
          return reordered.map((s, i) => ({ ...s, step: i + 1 }))
        })
        break
      }
      default:
        if (import.meta.env.DEV) { console.warn('Unknown study action:', action.action) }
    }
    setDirty(true)
  }, [steps.length])

  // Apply all pending actions at once
  const applyAllActions = useCallback(() => {
    pendingActions.forEach(a => applyAction(a))
    setPendingActions([])
  }, [pendingActions, applyAction])

  // Send LLM query
  const handleQASend = useCallback(async () => {
    const q = qaInput.trim()
    if (!q || qaWaiting) return

    const studyContext = {
      title,
      description,
      steps: steps.map(s => ({
        step: s.step, verse: s.verse, title: s.title,
        explanation: s.explanation?.slice(0, 200),
        connections_count: (s.connections || []).length,
      })),
    }

    const newMessages = [
      ...qaMessages,
      { role: 'user', content: q },
    ]
    setQaMessages(newMessages)
    setQaInput('')
    setQaWaiting(true)

    try {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [
            {
              role: 'system',
              content: `You are a scripture study editor assistant. You help create and modify studies.

Current study:
${JSON.stringify(studyContext, null, 2)}

To make changes to the study, include one or more <study-action> blocks in your response.
Each block is a JSON object on a single line:

<study-action>{"action":"add_step","step_number":2,"verse":"gen.1.1","title":"In the Beginning","explanation":"In the beginning God created..."}</study-action>

Supported actions:
- add_step: {action, step_number, verse, title, explanation, verse_text, book_title, connections, choices}
- remove_step: {action, step_number}
- update_step: {action, step_number, title?, explanation?, verse?, ...}
- set_title: {action, title}
- set_description: {action, description}
- reorder: {action, step_order: [1,3,2,4]}

Always explain what you're changing before the action block.
Users must click "Apply" to execute changes — don't apply them automatically.`,
            },
            ...qaMessages,
            { role: 'user', content: q },
          ],
          model: 'deepseek-chat',
          max_tokens: 2000,
          temperature: 0.5,
        }),
      })
      const data = await res.json()
      const answer = data?.choices?.[0]?.message?.content || data?.message?.content || data?.content || 'No response.'
      const actions = parseActions(answer)

      setQaMessages(prev => [...prev, { role: 'assistant', content: answer, actions }])
      if (actions.length > 0) {
        setPendingActions(prev => [...prev, ...actions])
      }
    } catch (err) {
      setQaMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setQaWaiting(false)
    }
  }, [qaInput, qaWaiting, qaMessages, steps, title, description, parseActions])

  const clearQA = useCallback(() => {
    setQaMessages([])
    setPendingActions([])
  }, [])

  // ── Preview mode (read-only view of current state) ──
  if (showPreview) {
    const previewStudy = {
      ...initialStudy,
      title,
      description,
      steps: steps.map(s => ({
        ...s,
        // Build a minimal verse_refs array needed by StudyViewer
        verse_refs: s.verse ? [s.verse] : [],
      })),
    }
    return (
      <div>
        <div className="max-w-4xl mx-auto px-6 pt-4">
          <button onClick={() => setShowPreview(false)}
            className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
            ← Back to Editing
          </button>
        </div>
        <StudyViewer study={previewStudy} onNavigate={onNavigate} onOpenTab={onOpenTab} showQuickAsk={false} />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-6">
      {/* Title & Description */}
      <div className="mb-6 space-y-3">
        <input type="text" value={title} onChange={e => setTitle(e.target.value)}
          className="w-full text-xl font-bold bg-transparent border-none outline-none text-neutral-900 dark:text-neutral-100 placeholder-neutral-300 dark:placeholder-neutral-600"
          placeholder="Study title..." />
        <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2}
          className="w-full text-sm bg-transparent border-none outline-none text-neutral-500 dark:text-neutral-400 placeholder-neutral-300 dark:placeholder-neutral-600 resize-none"
          placeholder="Description (optional)" />
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step, idx) => (
          <div key={idx} className="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2 bg-neutral-50 dark:bg-neutral-800/50 border-b border-neutral-100 dark:border-neutral-700">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-500 text-white text-[10px] font-bold shrink-0">
                {step.step}
              </span>
              <div className="flex gap-1 ml-auto">
                <button onClick={() => moveStep(idx, -1)} disabled={idx === 0}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-500 hover:text-neutral-700 disabled:opacity-30 cursor-pointer">↑</button>
                <button onClick={() => moveStep(idx, 1)} disabled={idx === steps.length - 1}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-500 hover:text-neutral-700 disabled:opacity-30 cursor-pointer">↓</button>
                <button onClick={() => removeStep(idx)}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 dark:bg-red-900/20 text-red-500 hover:text-red-700 cursor-pointer">✕</button>
              </div>
            </div>
            <div className="px-3 py-2 space-y-2">
              <input type="text" value={step.verse} onChange={e => updateStep(idx, 'verse', e.target.value)}
                className="w-full text-xs font-mono bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded px-2 py-1 outline-none focus:border-blue-400 text-neutral-800 dark:text-neutral-200"
                placeholder="Verse (e.g., lev.17.11)" />
              {step.verse && (
                <VersePreviewCard refs={step.verse} onNavigate={onNavigate} maxHeight="6rem" />
              )}
              <input type="text" value={step.title} onChange={e => updateStep(idx, 'title', e.target.value)}
                className="w-full text-sm font-medium bg-transparent border-none outline-none text-neutral-800 dark:text-neutral-200 placeholder-neutral-300 dark:placeholder-neutral-600"
                placeholder="Step title..." />
              <textarea value={step.explanation || ''} onChange={e => updateStep(idx, 'explanation', e.target.value)} rows={3}
                className="w-full text-sm bg-neutral-50 dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded px-2 py-1 outline-none focus:border-blue-400 text-neutral-700 dark:text-neutral-300 placeholder-neutral-300 dark:placeholder-neutral-600 resize-none"
                placeholder="Explanation..." />
            </div>
          </div>
        ))}
      </div>

      {/* Add Step Button */}
      <button onClick={addStep}
        className="w-full mt-3 px-4 py-2.5 rounded-lg border-2 border-dashed border-neutral-300 dark:border-neutral-600 text-sm text-neutral-400 dark:text-neutral-500 hover:text-blue-600 dark:hover:text-blue-400 hover:border-blue-300 dark:hover:border-blue-700 transition-all cursor-pointer">
        + Add Step
      </button>

      {/* Toolbar: Save / Preview / Export / Import */}
      <div className="flex items-center gap-2 mt-4 flex-wrap">
        <button onClick={save} disabled={!dirty || saving}
          className={`px-4 py-1.5 rounded-lg text-xs font-medium transition-all cursor-pointer
            ${dirty && !saving
              ? 'bg-blue-500 text-white hover:bg-blue-600'
              : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 cursor-not-allowed'
            }`}>
          {saving ? 'Saving...' : dirty ? 'Save Changes' : 'Saved ✓'}
        </button>
        {dirty && <span className="text-[10px] text-amber-500">Unsaved changes</span>}
        {error && (
          <span className="flex items-center gap-1 text-[10px] text-red-500">
            <span>Error: {error}</span>
            <button onClick={() => setError(null)} className="hover:text-red-700 cursor-pointer">✕</button>
          </span>
        )}

        <button onClick={() => setShowPreview(true)}
          className="px-4 py-1.5 rounded-lg text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
          👁 Preview
        </button>

        <button onClick={() => {
          const studyData = { title, description, steps }
          const blob = new Blob([JSON.stringify(studyData, null, 2)], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `${title || 'study'}.json`.replace(/[^a-zA-Z0-9._-]/g, '_')
          a.click()
          URL.revokeObjectURL(url)
        }}
          className="px-4 py-1.5 rounded-lg text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
          ⬇ Export JSON
        </button>

        {/* Hidden file input for import */}
        <input type="file" accept=".json" onChange={async (e) => {
          const file = e.target.files?.[0]
          if (!file) return
          try {
            const text = await file.text()
            const data = JSON.parse(text)
            if (data.steps) setSteps(data.steps.map((s, i) => ({ ...s, step: i + 1 })))
            if (data.title) setTitle(data.title)
            if (data.description) setDescription(data.description || '')
          } catch (err) {
            alert('Invalid JSON file: ' + err.message)
          }
          e.target.value = ''
        }}
          className="hidden" id="import-json-input" />
        <label htmlFor="import-json-input"
          className="px-4 py-1.5 rounded-lg text-xs font-medium bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer transition-colors inline-block">
          ⬆ Import JSON
        </label>
      </div>

      {/* Drag-and-drop import zone */}
      {dragging && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={async (e) => {
            e.preventDefault()
            setDragging(false)
            const file = e.dataTransfer.files?.[0]
            if (!file) return
            try {
              const text = await file.text()
              const data = JSON.parse(text)
              if (data.steps) setSteps(data.steps.map((s, i) => ({ ...s, step: i + 1 })))
              if (data.title) setTitle(data.title)
              if (data.description) setDescription(data.description || '')
            } catch (err) {
              alert('Invalid JSON file: ' + err.message)
            }
          }}>
          <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl p-8 text-center border-2 border-dashed border-blue-400">
            <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">Drop JSON file here</p>
            <p className="text-sm text-neutral-500 mt-1">Import a study from JSON</p>
          </div>
        </div>
      )}

      {/* Global drag-over listener */}
      <div onDragOver={e => { e.preventDefault(); setDragging(true) }} className="hidden" />

      {/* ─── LLM Assistant ─── */}
      {showQuickAsk && (
        <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">🤖 LLM Study Assistant</span>
            {qaMessages.length > 0 && (
              <button onClick={clearQA}
                className="text-[10px] text-neutral-400 hover:text-red-500 ml-auto cursor-pointer">Clear</button>
            )}
          </div>

          {/* Messages */}
          {qaMessages.length > 0 && (
            <div className="mb-3 max-h-80 overflow-y-auto space-y-2">
              {qaMessages.map((msg, i) => (
                <div key={i} className={`p-3 rounded-lg text-sm ${msg.role === 'user' ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200' : 'bg-neutral-50 dark:bg-neutral-800/50 text-neutral-700 dark:text-neutral-300'}`}>
                  <div className="text-[10px] font-medium text-neutral-400 mb-1">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                  <div className="whitespace-pre-wrap">{msg.content.replace(/<study-action>[\s\S]*?<\/study-action>/g, '')}</div>
                  {msg.actions?.length > 0 && (
                    <div className="mt-1 text-[10px] text-amber-600 dark:text-amber-400">
                      ({msg.actions.length} action{msg.actions.length > 1 ? 's' : ''} proposed — see below)
                    </div>
                  )}
                </div>
              ))}
              <div ref={qaEndRef} />
            </div>
          )}

          {/* Pending Actions */}
          {pendingActions.length > 0 && (
            <div className="mb-3 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-amber-700 dark:text-amber-400">
                  {pendingActions.length} change{pendingActions.length > 1 ? 's' : ''} proposed
                </span>
                <button onClick={applyAllActions}
                  className="ml-auto px-3 py-1 rounded text-[10px] font-medium bg-amber-500 text-white hover:bg-amber-600 cursor-pointer">
                  Apply All
                </button>
                <button onClick={() => setPendingActions([])}
                  className="px-3 py-1 rounded text-[10px] font-medium bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400 hover:bg-neutral-300 cursor-pointer">
                  Dismiss
                </button>
              </div>
              <div className="space-y-1">
                {pendingActions.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] text-neutral-600 dark:text-neutral-400">
                    <span className="font-mono text-amber-600 dark:text-amber-400">{a.action}</span>
                    <span className="truncate">{a.title || a.verse || a.step_number || ''}</span>
                    <button onClick={() => { applyAction(a); setPendingActions(prev => prev.filter((_, j) => j !== i)) }}
                      className="ml-auto text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">Apply</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="flex gap-2">
            <input type="text" value={qaInput} onChange={e => setQaInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleQASend() }}
              placeholder="Ask the LLM to modify the study (e.g., 'Add a step about the Red Heifer between steps 3 and 4')"
              className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 placeholder-neutral-400 dark:placeholder-neutral-500" />
            <button onClick={handleQASend} disabled={qaWaiting || !qaInput.trim()}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer
                ${qaWaiting ? 'bg-neutral-200 dark:bg-neutral-700 text-neutral-400 cursor-not-allowed'
                : 'bg-blue-500 text-white hover:bg-blue-600 active:bg-blue-700'}`}>
              {qaWaiting ? '…' : 'Send'}
            </button>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-6 text-center text-[10px] text-neutral-300 dark:text-neutral-600">
        {steps.length} step{steps.length !== 1 ? 's' : ''} · StudyEditor v1
      </div>
    </div>
  )
}
