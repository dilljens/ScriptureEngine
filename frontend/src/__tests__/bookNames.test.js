import { describe, it, expect } from 'vitest'
import { parseRef, formatRef, BOOK_TITLES } from '../bookNames'

describe('parseRef', () => {
  it('parses a standard 3-part verse ref (gen.1.1)', () => {
    const r = parseRef('gen.1.1')
    expect(r).not.toBeNull()
    expect(r.label).toBe('Genesis 1:1')
    expect(r.book).toBe('gen')
    expect(r.chapter).toBe(1)
    expect(r.verse).toBe(1)
    expect(r.bookName).toBe('Genesis')
    expect(r.workId).toBe('ot')
  })

  it('parses a chapter-only ref (exo.20)', () => {
    const r = parseRef('exo.20')
    expect(r).not.toBeNull()
    expect(r.label).toBe('Exodus 20')
    expect(r.book).toBe('exo')
    expect(r.chapter).toBe(20)
    expect(r.verse).toBeNull()
    expect(r.workId).toBe('ot')
  })

  it('parses NT ref (matt.5.3)', () => {
    const r = parseRef('matt.5.3')
    expect(r).not.toBeNull()
    expect(r.label).toBe('Matthew 5:3')
    expect(r.book).toBe('matt')
    expect(r.workId).toBe('nt')
  })

  it('parses BoM ref (1ne.1.1)', () => {
    const r = parseRef('1ne.1.1')
    expect(r).not.toBeNull()
    expect(r.label).toBe('1 Nephi 1:1')
    expect(r.workId).toBe('bom')
  })

  it('parses D&C ref: "dc76" (section only)', () => {
    const r = parseRef('dc76')
    expect(r).not.toBeNull()
    expect(r.label).toBe('D&C 76')
    expect(r.book).toBe('dc76')
    expect(r.chapter).toBe(1)
    expect(r.verse).toBeNull()
    expect(r.workId).toBe('dc')
  })

  it('parses D&C ref: "dc76.1" (section + verse, 2-part)', () => {
    const r = parseRef('dc76.1')
    expect(r).not.toBeNull()
    expect(r.label).toBe('D&C 76:1')
    expect(r.book).toBe('dc76')
    expect(r.chapter).toBe(1)
    expect(r.verse).toBe(1)
    expect(r.workId).toBe('dc')
  })

  it('parses D&C ref: "dc76.76.22" (section.section.verse, 3-part LLM format)', () => {
    const r = parseRef('dc76.76.22')
    expect(r).not.toBeNull()
    expect(r.label).toBe('D&C 76:22')
    expect(r.book).toBe('dc76')
    expect(r.chapter).toBe(1)
    expect(r.verse).toBe(22)
    expect(r.workId).toBe('dc')
  })

  it('parses DSS ref (1QS.1.1)', () => {
    const r = parseRef('1QS.1.1')
    expect(r).not.toBeNull()
    expect(r.book).toBe('1qs')
    expect(r.chapter).toBe(1)
    expect(r.verse).toBe(1)
    expect(r.workId).toBe('dss')
  })

  it('parses Pseudepigrapha ref (1en.1.1)', () => {
    const r = parseRef('1en.1.1')
    expect(r).not.toBeNull()
    expect(r.label).toContain('1 Enoch')
    expect(r.workId).toBe('pseu')
  })

  it('returns null for invalid ref', () => {
    expect(parseRef('')).toBeNull()
    expect(parseRef(null)).toBeNull()
    expect(parseRef('invalid')).toBeNull()
    expect(parseRef('abc.def')).toBeNull()
  })

  it('returns null for unknown book ID', () => {
    expect(parseRef('nonexistent.1.1')).toBeNull()
  })
})

describe('formatRef', () => {
  it('formats a 3-part ref', () => {
    expect(formatRef('gen', 1, 1)).toBe('gen.1.1')
  })

  it('formats a chapter-only ref', () => {
    expect(formatRef('isa', 55, null)).toBe('isa.55')
  })

  it('formats with undefined verse', () => {
    expect(formatRef('matt', 5, undefined)).toBe('matt.5')
  })
})
