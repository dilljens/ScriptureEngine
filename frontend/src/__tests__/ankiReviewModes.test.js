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
