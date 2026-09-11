import { describe, it, expect } from 'vitest'
import { HEBREW_GAMES, getGame, loadGameId } from '../components/HebrewModePicker'

// Registry + stale-id migration. This is the surface where a rename can
// silently strand a saved game id (regression: aleph-revelation → emet).
describe('hebrew games registry', () => {
  it('exposes at least one playable game with a component', () => {
    const playable = HEBREW_GAMES.filter(g => g.available && g.Component)
    expect(playable.length).toBeGreaterThan(0)
  })

  it('emet is available and backed by a component', () => {
    const emet = HEBREW_GAMES.find(g => g.id === 'emet')
    expect(emet).toBeTruthy()
    expect(emet.available).toBe(true)
    expect(typeof emet.Component).toBe('function')
  })

  it('getGame returns the requested game', () => {
    expect(getGame('emet').id).toBe('emet')
  })

  it('getGame falls back for stale/unknown ids (migration safety)', () => {
    // legacy id from before the Emet rename
    expect(getGame('aleph-revelation').id).toBe('emet')
    expect(getGame('does-not-exist').id).toBe('emet')
    expect(getGame(undefined).id).toBe('emet')
  })

  it('locked games never resolve as the active game', () => {
    const locked = HEBREW_GAMES.find(g => !g.available)
    if (locked) expect(getGame(locked.id).id).not.toBe(locked.id)
  })

  it('loadGameId returns a valid game id with no storage (node/private mode)', () => {
    expect(HEBREW_GAMES.some(g => g.id === loadGameId() && g.available)).toBe(true)
  })
})
