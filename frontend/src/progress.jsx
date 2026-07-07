/**
 * Progress tracking — marks verses as reviewed/read.
 *
 * Provides:
 *  - ProgressProvider (context)
 *  - useProgress() → { isReviewed, toggleReviewed, markReviewed }
 *
 * Each function takes a verse key string (e.g. "gen.1.1").
 * Reviewed state is persisted in localStorage.
 */

import React, { createContext, useContext, useState, useCallback } from 'react'

const REVIEWED_KEY = 'scripture_reviewed'
const ProgressContext = createContext(null)

function loadReviewed() {
  try {
    const raw = localStorage.getItem(REVIEWED_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return new Set(parsed)
    }
  } catch {}
  return new Set()
}

function saveReviewed(set) {
  try {
    localStorage.setItem(REVIEWED_KEY, JSON.stringify([...set]))
  } catch {}
}

export function ProgressProvider({ children }) {
  const [reviewed, setReviewed] = useState(loadReviewed)

  const isReviewed = useCallback((key) => {
    return reviewed.has(key)
  }, [reviewed])

  const toggleReviewed = useCallback((key) => {
    setReviewed(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      saveReviewed(next)
      return next
    })
  }, [])

  const markReviewed = useCallback((key) => {
    setReviewed(prev => {
      if (prev.has(key)) return prev
      const next = new Set(prev)
      next.add(key)
      saveReviewed(next)
      return next
    })
  }, [])

  const value = { isReviewed, toggleReviewed, markReviewed }

  return React.createElement(ProgressContext.Provider, { value }, children)
}

export function useProgress() {
  const ctx = useContext(ProgressContext)
  if (!ctx) {
    return {
      isReviewed: () => false,
      toggleReviewed: () => {},
      markReviewed: () => {},
    }
  }
  return ctx
}
