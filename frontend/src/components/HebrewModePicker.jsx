import React from 'react'
import HebrewIdleBar from './HebrewIdleBar'
import { logEvent } from '../lib/analytics'

/**
 * HebrewModePicker — Classic Study vs Games, + the games registry.
 *
 * To add a game: append {id, name, icon, tagline, available: true, Component}
 * to HEBREW_GAMES. Locked entries (available: false) render as teasers.
 * LearnView renders the active game's Component — no other wiring needed.
 */

export const HEBREW_GAMES = [
  {
    id: 'emet',
    name: 'EMET — Golem Maker',
    icon: '🗿',
    tagline: 'Inscribe letters, animate golems. They mine Ohr while you study. Erase the א to ascend.',
    available: true,
    Component: HebrewIdleBar,
  },
  {
    id: 'desert-wanderer',
    name: 'Desert Wanderer',
    icon: '🏜️',
    tagline: 'Tap the right vowel to keep walking · 30-second bursts while Ohr accrues',
    available: false,
    Component: null,
  },
  {
    id: 'verb-slasher',
    name: 'Verb Slasher',
    icon: '⚔️',
    tagline: 'Conjugations fall — tap the right binyan before it lands · streaks are combos',
    available: false,
    Component: null,
  },
]

export function getGame(id) {
  return HEBREW_GAMES.find(g => g.id === id && g.available && g.Component)
    || HEBREW_GAMES.find(g => g.available && g.Component)
}

export const LEARN_MODE_KEY = 'hebrew-learn-mode'
export const GAME_ID_KEY = 'hebrew-game-id'

export function loadLearnMode() {
  try { return localStorage.getItem(LEARN_MODE_KEY) || 'classic' } catch { return 'classic' }
}

export function loadGameId() {
  let id = 'emet'
  try { id = localStorage.getItem(GAME_ID_KEY) || 'emet' } catch { return 'emet' }
  // Normalize stale/unknown ids (e.g. legacy 'aleph-revelation') to a real game.
  if (!HEBREW_GAMES.some(g => g.id === id && g.available)) {
    id = 'emet'
    try { localStorage.setItem(GAME_ID_KEY, id) } catch {}
  }
  return id
}

export default function HebrewModePicker({ mode, onMode, activeGameId, onGame }) {
  const setMode = (m) => {
    try { localStorage.setItem(LEARN_MODE_KEY, m) } catch {}
    try { logEvent('mode_switch', { mode: m }) } catch {}
    onMode(m)
  }
  const setGame = (id) => {
    try { localStorage.setItem(GAME_ID_KEY, id) } catch {}
    try { logEvent('game_switch', { game: id }) } catch {}
    onGame(id)
  }

  return (
    <div className="mb-4">
      {/* Segmented control — big touch targets, mobile-first */}
      <div className="flex gap-2" role="tablist" aria-label="Learning mode">
        {[
          { id: 'classic', icon: '📖', label: 'Classic Study', desc: 'Curriculum as always' },
          { id: 'game', icon: '🎮', label: 'Games', desc: 'Learn by playing' },
        ].map(t => (
          <button key={t.id} role="tab" aria-selected={mode === t.id}
            onClick={() => setMode(t.id)}
            className={`flex-1 min-h-[52px] px-3 rounded-xl border-2 text-left transition-colors cursor-pointer active:scale-[0.98] ${mode === t.id
              ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/30'
              : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800'}`}>
            <div className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">
              <span className="mr-1.5">{t.icon}</span>{t.label}
            </div>
            <div className="text-[10px] text-neutral-500 dark:text-neutral-400">{t.desc}</div>
          </button>
        ))}
      </div>

      {/* Game shelf — only in game mode */}
      {mode === 'game' && (
        <div className="mt-2 grid gap-2 sm:grid-cols-3">
          {HEBREW_GAMES.map(g => {
            const locked = !g.available || !g.Component
            const active = activeGameId === g.id && !locked
            return (
              <button key={g.id} disabled={locked} onClick={() => setGame(g.id)}
                className={`min-h-[64px] p-2.5 rounded-xl border-2 text-left transition-colors ${locked
                  ? 'border-dashed border-neutral-200 dark:border-neutral-700 opacity-60 cursor-not-allowed'
                  : active
                    ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/30 cursor-pointer'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 cursor-pointer active:scale-[0.98]'}`}>
                <div className="text-xs font-semibold text-neutral-800 dark:text-neutral-200">
                  <span className="mr-1.5">{g.icon}</span>{g.name}
                  {locked && <span className="ml-1.5 text-[9px] font-normal text-neutral-400">🔒 soon</span>}
                </div>
                <div className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-0.5">{g.tagline}</div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
