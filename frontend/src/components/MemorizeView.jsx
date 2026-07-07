import React, { useEffect, useState } from 'react'
import { memorizeApi } from '../memorizeApi'
import { MemorizeIcon } from '../icons'
import ReviewSession from './ReviewSession'
import PalaceList from './PalaceList'
import PalaceBuilder from './PalaceBuilder'

export default function MemorizeView() {
  const [view, setView] = useState('loading') // 'loading' | 'dashboard' | 'review' | 'palaces' | 'palace-builder'
  const [activePalaceId, setActivePalaceId] = useState(null)
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    memorizeApi.get('/stats')
      .then(data => {
        if (cancelled) return
        setStats(data.stats || {})
        // Direct-to-review: skip dashboard if cards due
        if (data.stats?.DueCards > 0) {
          setView('review')
        } else {
          setView('dashboard')
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err.message)
          setView('dashboard')
        }
      })
    return () => { cancelled = true }
  }, [])

  if (view === 'review') {
    return <ReviewSession onDone={() => setView('dashboard')} />
  }

  if (view === 'palaces') {
    return <PalaceList
      onSelect={(id) => { setActivePalaceId(id); setView('palace-builder') }}
      onCreate={() => {}}
    />
  }

  if (view === 'palace-builder' && activePalaceId) {
    return <PalaceBuilder palaceId={activePalaceId} onBack={() => setView('palaces')} />
  }

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

      {/* Connection error */}
      {error && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4 text-sm text-amber-700 dark:text-amber-400 mb-4">
          <p className="font-medium">Memorization service unavailable</p>
          <p className="mt-1 text-xs opacity-80">
            Start the Go backend to enable review features.
          </p>
        </div>
      )}

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-4 gap-2 mb-6">
          <StatBox label="Cards" value={stats.TotalCards || 0} />
          <StatBox label="Due" value={stats.DueCards || 0} highlight />
          <StatBox label="Mastered" value={stats.Mastered || 0} />
          <StatBox label="Streak" value={`${stats.Streak || 0}d`} />
        </div>
      )}

      {/* Quick start */}
      {stats && stats.DueCards > 0 && (
        <button
          onClick={() => setView('review')}
          className="w-full py-3 px-4 rounded-lg bg-indigo-500 hover:bg-indigo-600 text-white font-medium text-sm mb-6 transition-colors"
        >
          Start Review ({stats.DueCards} cards due)
        </button>
      )}

      {/* Feature cards */}
      <div className="grid gap-3">
        <FeatureCard
          icon="📋"
          title="Review Queue"
          description="FSRS spaced repetition — review due cards"
          badge={stats && stats.DueCards > 0 ? `${stats.DueCards} due` : 'Up to date'}
          ready={stats && stats.DueCards > 0}
        />
        <button onClick={() => setView('palaces')} className="w-full text-left">
          <FeatureCard
            icon="🏛️"
            title="Memory Palaces"
            description="Upload photos, place loci, assign verses"
            badge="Ready"
            ready={true}
          />
        </button>
        <FeatureCard
          icon="🎨"
          title="Image Studio"
          description="Generate concept images for each verse"
          badge="Phase 4"
          ready={false}
        />
        <FeatureCard
          icon="🎤"
          title="Audio Studio"
          description="Record and review your recitations"
          badge="Phase 8"
          ready={false}
        />
        <FeatureCard
          icon="📊"
          title="Analytics"
          description="Streak, heat maps, accuracy trends"
          badge="Phase 9"
          ready={false}
        />
      </div>
    </div>
  )
}

function StatBox({ label, value, highlight }) {
  return (
    <div className={`rounded-lg border p-3 text-center ${
      highlight
        ? 'border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-950/30'
        : 'border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900'
    }`}>
      <div className={`text-lg font-bold tabular-nums ${
        highlight
          ? 'text-indigo-600 dark:text-indigo-400'
          : 'text-neutral-900 dark:text-neutral-100'
      }`}>{value}</div>
      <div className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-0.5">{label}</div>
    </div>
  )
}

function FeatureCard({ icon, title, description, badge, ready }) {
  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900">
      <span className="text-lg shrink-0 mt-0.5">{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{title}</h3>
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
            ready
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
