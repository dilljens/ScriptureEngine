import { describe, expect, it } from 'vitest'
import { modesForCard, relearnInsertAt, RELEARN_REDEAL_GAP, MAX_REDEALS_PER_CARD } from '../components/AnkiReview'

describe('AnkiReview modesForCard (C1 picture direction)', () => {
  it('deals all four directions when a Tier-0 picture exists', () => {
    expect(modesForCard({ hebrew: 'אב' }, true)).toEqual(
      ['hearing', 'reverse', 'forward', 'picture'])
  })

  it('drops picture (no blank fronts) when no picture is cached', () => {
    expect(modesForCard({ hebrew: 'אב' }, false)).toEqual(
      ['hearing', 'reverse', 'forward'])
  })

  it('server due_modes pass through untouched either way', () => {
    expect(modesForCard({ hebrew: 'אב', modes: ['reverse'] }, true)).toEqual(['reverse'])
    expect(modesForCard({ hebrew: 'אב', modes: ['picture'] }, false)).toEqual(['picture'])
  })
})

describe('AnkiReview relearnInsertAt (live re-deal)', () => {
  it('returns the card a few positions later', () => {
    expect(relearnInsertAt(0, 10)).toBe(1 + RELEARN_REDEAL_GAP)
    expect(relearnInsertAt(5, 10)).toBe(6 + RELEARN_REDEAL_GAP)
  })

  it('clamps at the end of the deck', () => {
    expect(relearnInsertAt(9, 10)).toBe(10)
    expect(relearnInsertAt(0, 0)).toBe(0)
  })

  it('caps re-deals per card', () => {
    expect(MAX_REDEALS_PER_CARD).toBe(2)
  })
})

describe('repairMode / resolveDealModes (no blank faces)', () => {
  it('converts imageless picture to forward, drops it when nothing can render', async () => {
    const { repairMode } = await import('../components/AnkiReview')
    expect(repairMode('picture', { hebrew: 'אב', gloss: 'father', hasPicture: false })).toBe('forward')
    // No hebrew for the forward fall-back, but gloss sustains reverse.
    expect(repairMode('picture', { hebrew: '', gloss: 'father', hasPicture: false })).toBe('reverse')
    expect(repairMode('picture', { hebrew: '', gloss: '', hasPicture: false })).toBeNull()
  })

  it('converts glossless reverse to forward, drops it when hebrew is missing too', async () => {
    const { repairMode } = await import('../components/AnkiReview')
    expect(repairMode('reverse', { hebrew: 'אב', gloss: '', hasPicture: false })).toBe('forward')
    expect(repairMode('reverse', { hebrew: '', gloss: '', hasPicture: false })).toBeNull()
  })

  it('keeps hearing while audio is unknown, converts to forward when known missing', async () => {
    const { repairMode } = await import('../components/AnkiReview')
    expect(repairMode('hearing', { hebrew: 'אב', gloss: 'father' })).toBe('hearing')
    expect(repairMode('hearing', { hebrew: 'אב', gloss: 'father', hasAudio: false })).toBe('forward')
    expect(repairMode('hearing', { hebrew: '', gloss: '', hasAudio: false })).toBeNull()
  })

  it('leaves fully-renderable modes untouched', async () => {
    const { repairMode } = await import('../components/AnkiReview')
    expect(repairMode('forward', { hebrew: 'אב', gloss: 'father', hasPicture: true })).toBe('forward')
    expect(repairMode('reverse', { hebrew: 'אב', gloss: 'father', hasPicture: true })).toBe('reverse')
    expect(repairMode('picture', { hebrew: 'אב', gloss: 'father', hasPicture: true })).toBe('picture')
  })

  it('resolveDealModes repairs imageless and glossless cards, drops the hopeless', async () => {
    const { resolveDealModes } = await import('../components/AnkiReview')
    const cards = [
      { node_id: 'n1', hebrew: 'אב', gloss: 'father' },
      { node_id: 'n2', hebrew: 'אם', gloss: '' },
      { node_id: 'n3', hebrew: '', gloss: '' },
    ]
    const dealt = resolveDealModes(cards, {})
    const byNode = {}
    for (const c of dealt) (byNode[c.node_id] = byNode[c.node_id] || []).push(c.mode)
    // n1: no picture cached -> picture converts to forward (2x forward + hearing + reverse)
    expect(byNode.n1).toContain('forward')
    expect(byNode.n1).not.toContain('picture')
    expect(byNode.n1).toContain('hearing')
    expect(byNode.n1).toContain('reverse')
    // n2: reverse converts (gloss missing), picture converts
    expect(byNode.n2).not.toContain('picture')
    expect(byNode.n2).not.toContain('reverse')
    // n3: nothing renderable -> dropped entirely
    expect(byNode.n3).toBeUndefined()
  })
})
