import React, { useEffect, useState } from 'react'
import { memorizeApi } from '../memorizeApi'
import { MemorizeIcon } from '../icons'

export default function MemorizeView() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    memorizeApi.get('/health')
      .then(data => { if (!cancelled) setStats({ status: data.status }) })
      .catch(err => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  return (
    <div className="max-w-2xl mx-auto p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
          <MemorizeIcon />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Memorize</h1>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">
            Spaced repetition · Memory palaces · AI imagery
          </p>
        </div>
      </div>

      {/* Status */}
      {loading && (
        <div className="text-sm text-neutral-400 animate-pulse">Connecting to memorization service...</div>
      )}
      {error && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4 text-sm text-amber-700 dark:text-amber-400">
          <p className="font-medium">Memorization service unavailable</p>
          <p className="mt-1 text-xs opacity-80">Start the Go backend at <code className="text-[10px] bg-amber-100 dark:bg-amber-900/40 px-1 rounded">backend/go-srs/</code> to enable review and palace features.</p>
          <p className="mt-1 text-xs opacity-60">Error: {error}</p>
        </div>
      )}

      {/* Feature cards (placeholder until Go backend is running) */}
      <div className="grid gap-3 mt-4">
        <FeatureCard
          icon="📋"
          title="Review Queue"
          description="Due cards from your spaced repetition schedule"
          badge={stats ? 'Ready' : 'Offline'}
        />
        <FeatureCard
          icon="🏛️"
          title="Memory Palaces"
          description="Upload photos, place loci, assign verses"
          badge="Coming in Phase 5"
        />
        <FeatureCard
          icon="🎨"
          title="AI Image Studio"
          description="Generate concept images for each verse (local SD 3.5)"
          badge="Coming in Phase 4"
        />
        <FeatureCard
          icon="🎤"
          title="Audio Studio"
          description="Record and review your recitations"
          badge="Coming in Phase 8"
        />
        <FeatureCard
          icon="📊"
          title="Analytics"
          description="Streak, heat maps, accuracy trends"
          badge="Coming in Phase 9"
        />
      </div>
    </div>
  )
}

function FeatureCard({ icon, title, description, badge }) {
  const isReady = badge === 'Ready'
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
      <span className="text-lg shrink-0 mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{title}</h3>
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
            isReady
              ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400'
              : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-400 dark:text-neutral-500'
          }`}>
            {badge}
          </span>
        </div>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">{description}</p>
      </div>
    </div>
  )
}
