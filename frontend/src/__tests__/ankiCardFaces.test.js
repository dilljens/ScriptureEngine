import { describe, expect, it } from 'vitest'
import { CardBack, CardFront } from '../components/AnkiReview'

/**
 * Card-rules rule 1/2 validation (image-before ordering):
 * front = ONE stimulus, never the answer; back = the full answer.
 * Harvests text + alt from the unrendered element tree (node env, no DOM).
 */
function harvest(el, out = { text: [], alt: [] }) {
  if (el == null || typeof el === 'boolean') return out
  if (typeof el === 'string' || typeof el === 'number') {
    out.text.push(String(el))
    return out
  }
  if (Array.isArray(el)) {
    el.forEach((c) => harvest(c, out))
    return out
  }
  if (typeof el === 'object' && el.props) {
    if (typeof el.props.alt === 'string') out.alt.push(el.props.alt)
    harvest(el.props.children, out)
    return out
  }
  return out
}

const SAMPLE = {
  hebrew: 'מֶלֶךְ',
  gloss: 'sovereign ruler',
  transliteration: 'melekh',
  img: { image_url: 'https://example.com/king.png' },
  audioUrl: 'https://example.com/king.mp3',
}
const noop = () => {}

function front(mode, overrides = {}) {
  const h = harvest(CardFront({ mode, ...SAMPLE, onReplay: noop, ...overrides }))
  return { text: h.text.join(' '), alt: h.alt.join(' ') }
}

function back(overrides = {}) {
  const h = harvest(
    CardBack({ ...SAMPLE, intervals: null, onRate: noop, onSuspend: noop, ...overrides }),
  )
  return { text: h.text.join(' '), alt: h.alt.join(' ') }
}

describe('AnkiReview card faces (rule 1/2: image-before ordering)', () => {
  it('picture front shows the image but never the answer', () => {
    const f = front('picture')
    expect(f.text.length).toBeGreaterThan(0) // never a blank front
    expect(f.text).not.toContain(SAMPLE.hebrew)
    expect(f.text).not.toContain(SAMPLE.gloss)
    expect(f.text).not.toContain(SAMPLE.transliteration)
    expect(f.alt).not.toContain(SAMPLE.hebrew)
    expect(f.alt).not.toContain(SAMPLE.gloss)
  })

  it('picture front degrades to a loading state, still with no answer', () => {
    const f = front('picture', { img: null })
    expect(f.text.length).toBeGreaterThan(0)
    expect(f.text).not.toContain(SAMPLE.hebrew)
    expect(f.text).not.toContain(SAMPLE.gloss)
  })

  it('hearing front leaks no text stimulus', () => {
    const f = front('hearing')
    expect(f.text).not.toContain(SAMPLE.hebrew)
    expect(f.text).not.toContain(SAMPLE.gloss)
    expect(f.text).not.toContain(SAMPLE.transliteration)
  })

  it('reverse front shows English stimulus only (no Hebrew answer)', () => {
    const f = front('reverse')
    expect(f.text).toContain(SAMPLE.gloss)
    expect(f.text).not.toContain(SAMPLE.hebrew)
  })

  it('forward front shows Hebrew stimulus only (no gloss answer)', () => {
    const f = front('forward')
    expect(f.text).toContain(SAMPLE.hebrew)
    expect(f.text).not.toContain(SAMPLE.gloss)
  })

  it('back always carries the full answer: writing + transliteration + gloss', () => {
    const b = back()
    expect(b.text).toContain(SAMPLE.hebrew)
    expect(b.text).toContain(SAMPLE.gloss)
    expect(b.text).toContain(SAMPLE.transliteration)
  })

  it('back still answers fully when the word has no picture', () => {
    const b = back({ img: null })
    expect(b.text).toContain(SAMPLE.hebrew)
    expect(b.text).toContain(SAMPLE.gloss)
  })
})

describe('direction labels stay off the visual front (sr-only for AT)', () => {
  it('shows no visible English/Hebrew direction text on any front', async () => {
    const { CardFront } = await import('../components/AnkiReview')
    const noop = () => {}
    const base = { hebrew: 'מֶלֶךְ', gloss: 'sovereign ruler', transliteration: 'melekh', img: { image_url: 'https://example.com/k.png' }, audioUrl: 'u', onReplay: noop }
    for (const mode of ['hearing', 'reverse', 'forward', 'picture']) {
      const h = harvest(CardFront({ mode, ...base }))
      const text = h.text.join(' ')
      expect(text).not.toMatch(/English → Hebrew|Hebrew → English|Listen & Translate|Picture → Hebrew/)
      expect(text.length).toBeGreaterThan(0)
    }
  })
})
