import { describe, expect, it } from 'vitest'
import { modesForCard } from '../components/AnkiReview'

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
