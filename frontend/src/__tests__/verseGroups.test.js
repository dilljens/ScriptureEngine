import { describe, it, expect } from 'vitest'
import { groupVerses } from '../lib/verseGroups'

describe('groupVerses', () => {
  it('merges consecutive highlighted verses into one block', () => {
    const verses = [{ verse: 1 }, { verse: 2 }, { verse: 3 }, { verse: 4 }]
    const segs = groupVerses(verses, v => v.verse === 1 || v.verse === 2)
    expect(segs).toHaveLength(2)
    expect(segs[0].highlighted).toBe(true)
    expect(segs[0].verses.map(v => v.verse)).toEqual([1, 2])
    expect(segs[1].highlighted).toBe(false)
  })

  it('keeps separate ranges apart', () => {
    const verses = [1, 2, 3, 4, 5].map(n => ({ verse: n }))
    const segs = groupVerses(verses, v => v.verse === 1 || v.verse === 2 || v.verse === 5)
    expect(segs.map(s => s.verses.map(v => v.verse))).toEqual([[1, 2], [3, 4], [5]])
  })

  it('handles empty and all-plain input', () => {
    expect(groupVerses([], () => true)).toEqual([])
    expect(groupVerses(null, () => true)).toEqual([])
    const verses = [{ verse: 1 }]
    expect(groupVerses(verses, () => false)).toEqual([{ verses, highlighted: false }])
  })
})
