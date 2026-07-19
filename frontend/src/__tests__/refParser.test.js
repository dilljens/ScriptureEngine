import { describe, it, expect } from 'vitest'
import { scoreFuzzy, parseStandardRef, parseAndFuzzy, resolveBook } from '../refParser'

describe('scoreFuzzy', () => {
  it('returns Infinity score for empty query', () => {
    const r = scoreFuzzy('genesis', '')
    expect(r.score).toBe(Infinity)
    expect(r.matchIdxs).toEqual([])
  })

  it('returns null for no match', () => {
    expect(scoreFuzzy('genesis', 'xyz')).toBeNull()
  })

  it('scores an exact match highly', () => {
    const r = scoreFuzzy('genesis', 'genesis')
    expect(r).not.toBeNull()
    expect(r.score).toBeGreaterThan(0)
    expect(r.matchIdxs.length).toBe(7)
  })

  it('scores a prefix match well', () => {
    const r = scoreFuzzy('genesis', 'gen')
    expect(r).not.toBeNull()
    expect(r.score).toBeGreaterThan(0)
  })

  it('scores a fuzzy match with gap penalty', () => {
    const r = scoreFuzzy('exodus', 'exs')
    expect(r).not.toBeNull()
    // 'e' → 0, 'x' → 1, 's' → 5 (gap of 3 after 'x': o-d-u)
    expect(r.score).toBeGreaterThan(0)
    expect(r.matchIdxs).toEqual([0, 1, 5])
  })

  it('handles typos via fuzzy matching (missing letter)', () => {
    const r = scoreFuzzy('colossians', 'colosians')
    expect(r).not.toBeNull()
    expect(r.score).toBeGreaterThan(10)
  })

  it('scores short query "ot" against work name', () => {
    const r = scoreFuzzy('old testament ot old_testament', 'ot')
    expect(r).not.toBeNull()
    expect(r.score).toBeGreaterThan(10)  // "ot" should match work name
  })
})

describe('parseStandardRef', () => {
  it('parses "book chapter:verse" format', () => {
    const r = parseStandardRef('isa 55:6')
    expect(r).not.toBeNull()
    expect(r.book).toBe('isa')
    expect(r.chapter).toBe(55)
    expect(r.verse).toBe(6)
  })

  it('parses "book chapter" format', () => {
    const r = parseStandardRef('genesis 1')
    expect(r).not.toBeNull()
    expect(r.book).toBe('gen')
    expect(r.chapter).toBe(1)
    expect(r.verse).toBeNull()
  })

  it('parses "book:chapter" format', () => {
    const r = parseStandardRef('exo:20')
    expect(r).not.toBeNull()
    expect(r.book).toBe('exo')
    expect(r.chapter).toBe(20)
  })

  it('parses "book.chapter" format', () => {
    const r = parseStandardRef('matt.5')
    expect(r).not.toBeNull()
    expect(r.book).toBe('matt')
    expect(r.chapter).toBe(5)
  })

  it('parses D&C "dcN:M" format', () => {
    const r = parseStandardRef('dc76:22')
    expect(r).not.toBeNull()
    expect(r.book).toBe('dc76')
    expect(r.chapter).toBe(76)
    expect(r.verse).toBe(22)
  })

  it('parses "bookN" compact format', () => {
    const r = parseStandardRef('isa3')
    expect(r).not.toBeNull()
    expect(r.book).toBe('isa')
    expect(r.chapter).toBe(3)
  })

  it('returns null for non-biblical input', () => {
    expect(parseStandardRef('hello world')).toBeNull()
    expect(parseStandardRef('')).toBeNull()
  })
})

describe('resolveBook', () => {
  it('resolves standard book names', () => {
    expect(resolveBook('genesis')).toBe('gen')
    expect(resolveBook('isaiah')).toBe('isa')
    expect(resolveBook('matthew')).toBe('matt')
  })

  it('resolves book aliases', () => {
    expect(resolveBook('isa')).toBe('isa')
    expect(resolveBook('gen')).toBe('gen')
    expect(resolveBook('1ne')).toBe('1ne')
  })

  it('resolves D&C sections', () => {
    expect(resolveBook('dc76')).toBe('dc76')
    expect(resolveBook('dc138')).toBe('dc138')
  })

  it('returns null for unknown books', () => {
    expect(resolveBook('nonexistent')).toBeNull()
  })
})

describe('parseAndFuzzy', () => {
  const mockBooks = [
    { workId: 'ot', workLabel: 'Old Testament', bookId: 'gen', bookTitle: 'Genesis', searchText: 'Genesis gen Old Testament' },
    { workId: 'ot', workLabel: 'Old Testament', bookId: 'exo', bookTitle: 'Exodus', searchText: 'Exodus exo Old Testament' },
    { workId: 'ot', workLabel: 'Old Testament', bookId: 'isa', bookTitle: 'Isaiah', searchText: 'Isaiah isa Old Testament' },
    { workId: 'ot', workLabel: 'Old Testament', bookId: 'psa', bookTitle: 'Psalms', searchText: 'Psalms psa Old Testament' },
    { workId: 'nt', workLabel: 'New Testament', bookId: 'matt', bookTitle: 'Matthew', searchText: 'Matthew matt New Testament' },
    { workId: 'nt', workLabel: 'New Testament', bookId: 'john', bookTitle: 'John', searchText: 'John john New Testament' },
    { workId: 'bom', workLabel: 'Book of Mormon', bookId: '1ne', bookTitle: '1 Nephi', searchText: '1 Nephi 1ne Book of Mormon' },
    { workId: 'dc', workLabel: 'Doctrine & Covenants', bookId: 'dc76', bookTitle: 'D&C 76', searchText: 'D&C 76 dc76 Doctrine & Covenants' },
  ]

  it('returns navigate results for book name', () => {
    const r = parseAndFuzzy('genesis', mockBooks)
    expect(r.type).toBe('navigate')
    expect(r.results.length).toBeGreaterThanOrEqual(1)
    expect(r.results[0].book).toBe('gen')
  })

  it('returns navigate results for fuzzy book name', () => {
    const r = parseAndFuzzy('isah', mockBooks)
    expect(r.type).toBe('navigate')
    expect(r.results[0].book).toBe('isa')
  })

  it('returns navigate result for standard ref', () => {
    const r = parseAndFuzzy('isa 55:6', mockBooks)
    expect(r.type).toBe('navigate')
    expect(r.results[0].book).toBe('isa')
    expect(r.results[0].chapter).toBe(55)
  })

  it('returns navigate result for chapter only', () => {
    const r = parseAndFuzzy('isa 55', mockBooks)
    expect(r.type).toBe('navigate')
    expect(r.results[0].chapter).toBe(55)
  })

  it('returns chat type for /chat command', () => {
    const r = parseAndFuzzy('/chat hello', mockBooks)
    expect(r.type).toBe('chat')
    expect(r.message).toBe('hello')
  })

  it('returns search type for /search command', () => {
    const r = parseAndFuzzy('/search covenant', mockBooks)
    expect(r.type).toBe('search')
    expect(r.query).toBe('covenant')
  })

  it('returns error for nonsense input', () => {
    const r = parseAndFuzzy('zzzxxxnonexistent', mockBooks)
    expect(r.type).toBe('error')
  })

  it('returns empty for empty input', () => {
    const r = parseAndFuzzy('', mockBooks)
    expect(r.type).toBe('empty')
  })
})
