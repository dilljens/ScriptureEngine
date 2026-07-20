import { describe, it, expect } from 'vitest'
import { assessmentToCards, lessonToCards, interleaveCards, clozeFromVerse, translationFromVerse } from '../lib/card-factory'

describe('assessmentToCards', () => {
  const sampleItems = [
    {
      question_id: 1,
      question: '**Genesis 1:1** says: > In the beginning...',
      correct_answer: 'God created the heavens and the earth',
      options: ['Option A', 'Option B', 'Option C'],
      tier: 'text',
      bloom_level: 'remember',
      layer: 'p\'shat',
      explanation: 'This is the foundational creation account.',
    },
  ]

  it('returns empty array for null/undefined input', () => {
    expect(assessmentToCards(null)).toEqual([])
    expect(assessmentToCards(undefined)).toEqual([])
    expect(assessmentToCards([])).toEqual([])
  })

  it('creates assessment_question card from item', () => {
    const cards = assessmentToCards(sampleItems)
    expect(cards).toHaveLength(1)
    expect(cards[0].type).toBe('assessment_question')
    expect(cards[0].id).toBe('assessment-1')
    expect(cards[0].data.question).toContain('Genesis 1:1')
    expect(cards[0].data.answer).toBe('God created the heavens and the earth')
    expect(cards[0].data.tier).toBe('text')
  })

  it('hides options when user has been correct before', () => {
    const progress = { 1: { correct: 3, attempts: 3 } }
    const cards = assessmentToCards(sampleItems, progress)
    expect(cards[0].data.show_options).toBe(false)
  })

  it('shows options when user has struggled', () => {
    const progress = { 1: { correct: 1, attempts: 4 } }
    const cards = assessmentToCards(sampleItems, progress)
    expect(cards[0].data.show_options).toBe(true)
  })

  it('hides options when user has never seen the question', () => {
    const progress = {}
    const cards = assessmentToCards(sampleItems, progress)
    expect(cards[0].data.show_options).toBe(false)
  })

  it('passes through all data fields', () => {
    const cards = assessmentToCards(sampleItems)
    expect(cards[0].data.explanation).toBeTruthy()
    expect(cards[0].data.options).toEqual(['Option A', 'Option B', 'Option C'])
    expect(cards[0].data.bloom_level).toBe('remember')
    expect(cards[0].data.layer).toBe("p'shat")
  })
})

describe('lessonToCards', () => {
  const sampleModule = {
    id: 5,
    title: 'Basic Hebrew Letters',
    questions: [
      {
        id: 10,
        question: 'What is the first letter of the Hebrew alphabet?',
        options: ['Bet', 'Aleph', 'Gimel'],
        correct_answer: 'Aleph',
        tier: 'text',
      },
    ],
  }

  it('returns empty array for null input', () => {
    expect(lessonToCards(null)).toEqual([])
  })

  it('creates learn_question card from module question', () => {
    const cards = lessonToCards(sampleModule)
    expect(cards).toHaveLength(1)
    expect(cards[0].type).toBe('learn_question')
    expect(cards[0].id).toBe('lesson-5-q-10')
    expect(cards[0].data.question).toContain('first letter')
    expect(cards[0].data.source).toBe('Basic Hebrew Letters')
  })

  it('shows options adaptively based on progress', () => {
    const cardsWithProgress = lessonToCards(sampleModule, { 10: { correct: 0, attempts: 2 } })
    expect(cardsWithProgress[0].data.show_options).toBe(true)

    const cardsWithoutProgress = lessonToCards(sampleModule, { 10: { correct: 3, attempts: 3 } })
    expect(cardsWithoutProgress[0].data.show_options).toBe(false)
  })
})

describe('interleaveCards', () => {
  it('returns empty for no input', () => {
    expect(interleaveCards([])).toEqual([])
    expect(interleaveCards([[], []])).toEqual([])
  })

  it('interleaves cards from multiple sources', () => {
    const a = [{ id: 'a1', type: 'verse' }, { id: 'a2', type: 'verse' }]
    const b = [{ id: 'b1', type: 'vocab' }, { id: 'b2', type: 'vocab' }]
    const result = interleaveCards([a, b])
    // Should alternate types, max 2 consecutive same
    expect(result).toHaveLength(4)
    const types = result.map(c => c.type)
    // Check no more than 2 consecutive same type
    for (let i = 0; i < types.length - 2; i++) {
      expect(types[i] === types[i+1] && types[i] === types[i+2]).toBe(false)
    }
  })

  it('respects maxConsecutive parameter', () => {
    const a = [{ id: 'a1', type: 'verse' }, { id: 'a2', type: 'verse' }]
    const b = [{ id: 'b1', type: 'vocab' }, { id: 'b2', type: 'vocab' }]
    const result = interleaveCards([a, b], 1)
    // With maxConsecutive=1, same types should not appear consecutively
    // when there are enough cards of other types to alternate
    for (let i = 0; i < result.length - 1; i++) {
      expect(result[i].type).not.toBe(result[i+1].type)
    }
  })
})

describe('clozeFromVerse', () => {
  it('returns empty for verse with too few words', () => {
    expect(clozeFromVerse({ id: 'gen.1.1', text_english: 'Hello' })).toEqual([])
  })

  it('creates cloze cards for a verse', () => {
    const cards = clozeFromVerse({
      id: 'gen.1.1',
      text_english: 'In the beginning God created the heaven and the earth.',
    })
    expect(cards.length).toBeGreaterThanOrEqual(1)
    expect(cards.length).toBeLessThanOrEqual(2)
    expect(cards[0].type).toBe('cloze')
    expect(cards[0].data.passage).toContain('[___]')
    expect(cards[0].data.answer).toContain('beginning')
  })
})

describe('translationFromVerse', () => {
  it('returns empty for verse without Hebrew', () => {
    expect(translationFromVerse({ id: 'gen.1.1', text_english: 'test' })).toEqual([])
  })

  it('creates translation card for bilingual verse', () => {
    const cards = translationFromVerse({
      id: 'gen.1.1',
      text_english: 'In the beginning God created',
      text_hebrew: 'בראשית ברא אלהים',
    })
    expect(cards).toHaveLength(1)
    expect(cards[0].type).toBe('translation')
    expect(cards[0].data.english).toBe('In the beginning God created')
    expect(cards[0].data.hebrew).toBe('בראשית ברא אלהים')
  })
})
