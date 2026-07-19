import { describe, it, expect } from 'vitest'
import { preprocess } from '../lib/scripture-markdown'

describe('preprocess', () => {
  it('converts :verse[gen.1.1] to span tag', () => {
    const result = preprocess('See :verse[gen.1.1] for context')
    expect(result).toContain('<span data-type="verse" data-ref="gen.1.1">')
    expect(result).not.toContain(':verse[')
  })

  it('converts :entity[Abraham] to span tag', () => {
    const result = preprocess('Learn about :entity[Abraham]')
    expect(result).toContain('<span data-type="entity" data-entity="Abraham">')
    expect(result).not.toContain(':entity[')
  })

  it('converts :gematria[יהוה=26] to span tag', () => {
    const result = preprocess('Value: :gematria[יהוה=26]')
    expect(result).toContain('<span data-type="gematria" data-value="יהוה=26">')
  })

  it('converts :strong[H430] to span tag', () => {
    const result = preprocess('Word: :strong[H430]')
    expect(result).toContain('<span data-type="strong" data-lemma="H430">')
  })

  it('converts :conn[gen.1.1↔john.1.1] to span tag', () => {
    const result = preprocess('Link: :conn[gen.1.1↔john.1.1]')
    expect(result).toContain('<span data-type="conn" data-conn="gen.1.1↔john.1.1">')
  })

  it('handles multiple markers in one string', () => {
    const result = preprocess(':verse[gen.1.1] connects to :verse[john.1.1]')
    const matches = result.match(/data-type="verse"/g)
    expect(matches).toHaveLength(2)
  })

  it('handles mixed marker types', () => {
    const result = preprocess(':entity[Abraham] met :entity[Melchizedek] in :verse[gen.14.18]')
    const entityMatches = result.match(/data-type="entity"/g)
    const verseMatches = result.match(/data-type="verse"/g)
    expect(entityMatches).toHaveLength(2)
    expect(verseMatches).toHaveLength(1)
  })

  it('returns empty string for empty input', () => {
    expect(preprocess('')).toBe('')
    expect(preprocess(null)).toBeNull()
    expect(preprocess(undefined)).toBeUndefined()
  })

  it('passes through plain text unchanged', () => {
    const text = 'Hello, this is plain text with no markers.'
    expect(preprocess(text)).toBe(text)
  })

  it('escapes HTML special chars like < > in marker values', () => {
    const result = preprocess(':entity[<script>]')
    expect(result).toContain('&lt;script&gt;')
    expect(result).not.toContain('<script>')
  })

  it('handles D&C refs in :verse[]', () => {
    const result = preprocess(':verse[dc76.76.22]')
    expect(result).toContain('data-ref="dc76.76.22"')
  })

  it('does not double-process existing span tags', () => {
    const input = 'Some text <span data-type="verse">already processed</span>'
    const result = preprocess(input)
    // Should not add another span tag inside the existing one
    expect(result).toBe(input)
  })
})
