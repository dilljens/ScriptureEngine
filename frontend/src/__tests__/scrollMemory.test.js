import { describe, it, expect, beforeEach } from 'vitest'
import { saveScrollPos, readScrollPos, clearScrollPos, parseVerseAnchor } from '../lib/scrollMemory'

// vitest runs in node env — stub the browser storage the module uses.
const store = new Map()
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
}

beforeEach(() => {
  localStorage.clear()
})

describe('scrollMemory', () => {
  it('saves and reads a position per tab', () => {
    saveScrollPos('tab1', 'isa', 6, 12)
    expect(readScrollPos('tab1')).toMatchObject({ book: 'isa', chapter: 6, verse: 12 })
  })

  it('keeps tabs independent', () => {
    saveScrollPos('tab1', 'isa', 6, 12)
    saveScrollPos('tab2', 'gen', 1, 1)
    expect(readScrollPos('tab1').verse).toBe(12)
    expect(readScrollPos('tab2').verse).toBe(1)
  })

  it('returns null for unknown tabs', () => {
    expect(readScrollPos('nope')).toBeNull()
    expect(readScrollPos(null)).toBeNull()
  })

  it('ignores incomplete saves', () => {
    saveScrollPos('tab1', 'isa', 6, null)
    expect(readScrollPos('tab1')).toBeNull()
  })

  it('clears a tab position', () => {
    saveScrollPos('tab1', 'isa', 6, 12)
    clearScrollPos('tab1')
    expect(readScrollPos('tab1')).toBeNull()
  })

  it('survives corrupt storage', () => {
    localStorage.setItem('scripture_scroll', '[[broken')
    expect(readScrollPos('tab1')).toBeNull()
    saveScrollPos('tab1', 'isa', 6, 1)
    expect(readScrollPos('tab1')).toMatchObject({ verse: 1 })
  })

  it('parses verse anchor ids', () => {
    expect(parseVerseAnchor('verse-gen.1.1')).toEqual({ book: 'gen', chapter: 1, verse: 1 })
    expect(parseVerseAnchor('verse-dc76.76.22')).toEqual({ book: 'dc76', chapter: 76, verse: 22 })
    expect(parseVerseAnchor('wiki-verse-gen.1.1')).toBeNull()
    expect(parseVerseAnchor('verse-gen.1')).toBeNull()
    expect(parseVerseAnchor(null)).toBeNull()
  })
})
