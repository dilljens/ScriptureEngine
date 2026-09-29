import { describe, it, expect } from 'vitest'
import { preprocessVerses } from '../components/ChatPanel'

describe('chat reference normalization', () => {
  it.each([
    ['1 Nephi 3:1-7', '1ne.3.1-7'],
    ['1 Nephi 3: 1 - 7', '1ne.3.1-7'],
    ['1 Nephi 3:1–7', '1ne.3.1-7'],
    ['1 Nephi 3:1, 5, 7', '1ne.3.1,5,7'],
  ])('normalizes %s', (input, ref) => {
    expect(preprocessVerses(input)).toContain(`:verse[${ref}]`)
  })

  it('leaves cross-chapter ranges for shared preprocessing instead of truncating them', () => {
    const input = 'Read Exodus 33:22–34:6 tonight'
    const result = preprocessVerses(input)
    expect(result).toBe(input)
  })
})
