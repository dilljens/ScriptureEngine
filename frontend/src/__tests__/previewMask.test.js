import { describe, it, expect } from 'vitest'
import { fadeMask, firstLetterMask, previewCapNote } from '../lib/previewMask'

const TEXT = 'In the beginning God created'

describe('fadeMask', () => {
  it('shows full text at 100', () => {
    expect(fadeMask(TEXT, 100)).toBe(TEXT)
  })

  it('shows only first letters at 0', () => {
    expect(fadeMask(TEXT, 0)).toBe('I t b G c')
  })

  it('blends full words and first letters at 50', () => {
    // Evenly-spread deterministic reveal (same pattern as firstLetterMask)
    expect(fadeMask(TEXT, 50)).toBe('I the b God c')
  })

  it('reveals more words as the level rises', () => {
    const count = (s) => s.split(' ').filter(w => w.length > 1).length
    expect(count(fadeMask(TEXT, 25))).toBeLessThanOrEqual(count(fadeMask(TEXT, 50)))
    expect(count(fadeMask(TEXT, 50))).toBeLessThanOrEqual(count(fadeMask(TEXT, 75)))
  })

  it('handles empty text', () => {
    expect(fadeMask('', 50)).toBe('')
  })

  it('never emits blanks — every word shows something', () => {
    for (const pct of [25, 50, 75]) {
      expect(fadeMask(TEXT, pct)).not.toContain('___')
    }
  })
})

describe('previewCapNote', () => {
  it('notes the fade cap', () => {
    expect(previewCapNote('fade_words', 50)).toContain('Good')
    expect(previewCapNote('fade_words', 100)).toContain('Hard')
  })

  it('keeps existing notes', () => {
    expect(previewCapNote('full_text', 0)).toContain('Hard')
    expect(previewCapNote('first_letters', 75)).toContain('Good')
    expect(previewCapNote('none', 0)).toBeNull()
  })
})
