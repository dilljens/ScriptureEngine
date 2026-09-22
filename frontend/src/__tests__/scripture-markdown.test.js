import { describe, it, expect } from 'vitest'
import { openVerseRef, preprocess } from '../lib/scripture-markdown'
import { BOOK_TITLES } from '../bookNames'

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

  it('auto-links bare dot refs like gen.1.1', () => {
    const result = preprocess('See gen.1.1 for context')
    expect(result).toContain('<span data-type="verse" data-ref="gen.1.1">gen.1.1</span>')
  })

  it('auto-links "Genesis 1:1" style refs', () => {
    const result = preprocess('Read Genesis 1:1 carefully')
    expect(result).toContain('<span data-type="verse" data-ref="gen.1.1">Genesis 1:1</span>')
  })

  it('auto-links refs inside otherwise-plain sentences', () => {
    const result = preprocess('In gen.2.4 the LORD God made the earth.')
    expect(result).toContain('data-ref="gen.2.4"')
  })

  it('does not mislink plain numbers or unknown book names', () => {
    expect(preprocess('Chapter 1:2 is a title')).not.toContain('data-type="verse"')
    expect(preprocess('This is step 3.1')).not.toContain('data-type="verse"')
    expect(preprocess('Fakebook 3:4 here')).not.toContain('data-type="verse"')
  })

  it('auto-links D&C dot refs and ranges', () => {
    expect(preprocess('See dc76.76.22 for context')).toContain('data-ref="dc76.76.22"')
    expect(preprocess('Read gen.1.1-12 now')).toContain('data-ref="gen.1.1-12"')
  })

  it('auto-links colon-style refs with book names and ranges', () => {
    expect(preprocess('Psalm 23:1 is well known')).toContain('data-ref="psa.23.1"')
    expect(preprocess('Exodus 20:3-17 lists commands')).toContain('data-ref="exo.20.3-17"')
  })

  it('keeps DSS refs with digits in book id', () => {
    expect(preprocess('The book of 1QS.1.1 matters')).toContain('data-ref="1QS.1.1"')
  })

  it('auto-links numbered books like 1 Nephi and 2 Corinthians', () => {
    expect(preprocess('Read 1 Nephi 1:5 today')).toContain('data-ref="1ne.1.5"')
    expect(preprocess('See 2 Corinthians 3:7 here')).toContain('data-ref="2cor.3.7"')
    expect(preprocess('Hear Him in 3 Nephi 11:7')).toContain('data-ref="3ne.11.7"')
  })

  it('auto-links chapter-only refs without inventing verse 1', () => {
    expect(preprocess('Read 1 John 3 today')).toContain('data-ref="1john.3"')
    expect(preprocess('In Genesis 1 we read')).toContain('data-ref="gen.1"')
    expect(preprocess('Read Psalm 23 tonight')).toContain('data-ref="psa.23"')
    expect(preprocess('as in 2 Peter 1 and Jude 3')).toContain('data-ref="2pet.1"')
    expect(preprocess('as in 2 Peter 1 and Jude 3')).toContain('data-ref="jude.3"')
  })

  it('links chapter-only refs preceded by prose without eating the prose', () => {
    const r = preprocess('we see in 1 John 3 the love of God')
    expect(r).toContain('data-ref="1john.3"')
    expect(r).toContain('we see in ')
    expect(r).toContain(' the love of God')
  })

  it('auto-links section-only D&C refs', () => {
    expect(preprocess('See D&C 76 for context')).toContain('data-ref="dc76"')
  })

  it('does not double-link chapter-only prefixes of ch:vs refs', () => {
    const r = preprocess('Read Genesis 1:1 carefully')
    expect(r).toContain('data-ref="gen.1.1"')
    expect(r.match(/data-type="verse"/g)).toHaveLength(1)
    const r2 = preprocess('the love of God in 1 John 4:7-8 is clear')
    expect(r2).toContain('data-ref="1john.4.7-8"')
    expect(r2.match(/data-type="verse"/g)).toHaveLength(1)
  })

  it('auto-links long book names like Deuteronomy', () => {
    expect(preprocess('As in Deuteronomy 4:12')).toContain('data-ref="deu.4.12"')
  })

  it('auto-links D&C colon refs', () => {
    expect(preprocess('Every soul per D&C 93:1')).toContain('data-ref="dc93.93.1"')
  })

  it('links multi-verse continuations sharing book context', () => {
    const r = preprocess('Awake in Isaiah 52:1-2, 54:2 today')
    expect(r).toContain('data-ref="isa.52.1-2"')
    expect(r).toContain('data-ref="isa.54.2"')
  })

  it('links verse-only continuations like Isaiah 53:5, 11', () => {
    const r = preprocess('Healed in Isaiah 53:5, 11 forever')
    expect(r).toContain('data-ref="isa.53.5"')
    expect(r).toContain('data-ref="isa.53.11"')
  })

  it('links cross-chapter en-dash ranges', () => {
    const r = preprocess('Read Exodus 33:22–34:6 tonight')
    expect(r).toContain('data-ref="exo.33.22"')
    expect(r).toContain('data-ref="exo.34.6"')
  })

  it('does not link numbers glued to words', () => {
    expect(preprocess('In Isaiah 40:31, 66th verse lurks')).not.toContain('isa.40.66')
  })

  it('auto-links bare refs appearing before explicit markers', () => {
    const r = preprocess('Genesis 1:1 and :verse[gen.1.2] together')
    expect(r).toContain('data-ref="gen.1.1"')
    expect(r).toContain('data-ref="gen.1.2"')
  })
})

describe('openVerseRef', () => {
  it('dispatches verse targets but leaves chapter-only refs unhighlighted', () => {
    const events = []
    const previousWindow = globalThis.window
    const previousCustomEvent = globalThis.CustomEvent
    globalThis.CustomEvent = class CustomEvent {
      constructor(type, init) { this.type = type; this.detail = init.detail }
    }
    globalThis.window = { dispatchEvent: event => events.push(event) }

    try {
      openVerseRef('gen.1')
      openVerseRef('gen.1.2-4')
      openVerseRef('dc76')

      expect(events[0].detail).toMatchObject({ book: 'gen', chapter: 1 })
      expect(events[0].detail.verses).toBeUndefined()
      expect(events[1].detail).toMatchObject({ book: 'gen', chapter: 1, verse: 2, verses: [2, 3, 4] })
      expect(events[2].detail).toMatchObject({ book: 'dc76', chapter: 76 })
      expect(events[2].detail.verses).toBeUndefined()
    } finally {
      globalThis.window = previousWindow
      globalThis.CustomEvent = previousCustomEvent
    }
  })
})

// ── Library-wide sweep: every book id must link by its full title ──
// Several ids share one display title (Damascus Document, Songs of Sabbath
// Sacrifice, 4QMMT) — the linker resolves those to the first id, so only
// the first id per title is asserted.
const SWEEP_SEEN_TITLES = new Set()
const SWEEP_EXCLUDE = {
  // Title is ambiguous with a ch:vs read: "Psalm 151 1:1" parses as
  // Psalms ch.151, not book psa151. Genuinely ambiguous input — excluded.
  psa151: true,
}
describe('every library book links', () => {
  for (const [id, title] of Object.entries(BOOK_TITLES)) {
    if (SWEEP_EXCLUDE[id]) continue
    if (SWEEP_SEEN_TITLES.has(title)) continue
    SWEEP_SEEN_TITLES.add(title)
    it(`links "${title} 1:1" → ${id}.1.1`, () => {
      expect(preprocess(`${title} 1:1`)).toContain(`data-ref="${id}.1.1"`)
    })
    it(`links chapter-only "${title} 3" → ${id}.3`, () => {
      expect(preprocess(`${title} 3`)).toContain(`data-ref="${id}.3"`)
    })
  }

  // D&C section ids (dcN) are dynamic — not in BOOK_TITLES. Spot-check the
  // reported failure plus neighbors, colon and section-only forms.
  it('links D&C 19:16 (reported failure)', () => {
    expect(preprocess('Read D&C 19:16 today')).toContain('data-ref="dc19.19.16"')
  })
  it('links D&C section refs across a range of sections', () => {
    for (const n of [1, 19, 76, 93, 121, 132, 138]) {
      expect(preprocess(`See D&C ${n}:7 here`)).toContain(`data-ref="dc${n}.${n}.7"`)
      expect(preprocess(`See D&C ${n} here`)).toContain(`data-ref="dc${n}"`)
    }
  })
})
