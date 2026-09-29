import { describe, it, expect } from 'vitest'
import { bookChapterOf, chapterKey, getCachedChapter, setCachedChapter } from '../lib/chapterCache'

describe('chapterCache', () => {
  it('splits verse ids into book+chapter', () => {
    expect(bookChapterOf('isa.55.6')).toEqual({ book: 'isa', chapter: 55 })
    expect(bookChapterOf('isa.55.6-8')).toEqual({ book: 'isa', chapter: 55 })
    expect(bookChapterOf('gen.1')).toEqual({ book: 'gen', chapter: 1 })
    expect(bookChapterOf('1ne.3.7')).toEqual({ book: '1ne', chapter: 3 })
  })

  it('handles D&C section refs', () => {
    expect(bookChapterOf('dc76.76.22')).toEqual({ book: 'dc76', chapter: 76 })
  })

  it('returns null for non-refs', () => {
    expect(bookChapterOf('')).toBeNull()
    expect(bookChapterOf('hello')).toBeNull()
    expect(bookChapterOf(null)).toBeNull()
  })

  it('round-trips set/get with normalized keys', () => {
    expect(getCachedChapter('isa', 55)).toBeNull()
    setCachedChapter('ISA', 55, { verses: [] })
    expect(getCachedChapter('isa', 55)).toEqual({ verses: [] })
    expect(chapterKey('ISA', 55)).toBe('isa.55')
  })
})

describe('prefetchChapter', () => {
  it('dedupes concurrent fetches and caches the result', async () => {
    const { prefetchChapter, getCachedChapter } = await import('../lib/chapterCache')
    let calls = 0
    globalThis.fetch = async () => {
      calls += 1
      return { json: async () => ({ ok: true, data: { verses: [{ verse: 1 }] } }) }
    }
    try {
      const [a, b] = await Promise.all([prefetchChapter('ps', 23), prefetchChapter('ps', 23)])
      expect(a).toEqual({ verses: [{ verse: 1 }] })
      expect(b).toEqual(a)
      expect(calls).toBe(1)
      expect(getCachedChapter('ps', 23)).toEqual(a)
      // Cached: no further fetch.
      await prefetchChapter('ps', 23)
      expect(calls).toBe(1)
    } finally {
      delete globalThis.fetch
    }
  })
})
