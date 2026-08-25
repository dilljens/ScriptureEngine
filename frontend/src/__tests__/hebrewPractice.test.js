import { describe, expect, it } from 'vitest'
import { gradePracticeAnswer } from '../components/HebrewLessonView'
import { getAuthoritativeCorrect } from '../components/HebrewQuiz'

describe('Hebrew practice grading', () => {
  it('grades exact multiple-choice answers', () => {
    expect(gradePracticeAnswer('Consonant doubling', 'Consonant doubling')).toBe(true)
    expect(gradePracticeAnswer('A long vowel', 'Consonant doubling')).toBe(false)
  })

  it('preserves meaningful Hebrew points while ignoring cantillation', () => {
    expect(gradePracticeAnswer('בְּרֵאשִׁית', 'בְּרֵאשִׁ֖ית')).toBe(true)
    expect(gradePracticeAnswer('שׂ', 'שׁ')).toBe(false)
    expect(gradePracticeAnswer('ב', 'בּ')).toBe(false)
    expect(gradePracticeAnswer('ָ', 'ָ')).toBe(true)
  })

  it('ignores the OSHB morpheme separator slash in typed answers', () => {
    // Typed answers are stored as unpointed skeletons; slashes are ignored on both sides.
    expect(gradePracticeAnswer('דהוא', 'דהוא')).toBe(true)
    expect(gradePracticeAnswer('ד/הוא', 'דהוא')).toBe(true)
    expect(gradePracticeAnswer('מלכא', 'מלכא')).toBe(true)
  })

  it('preserves alternative free-text answers', () => {
    expect(gradePracticeAnswer('first', 'first or second')).toBe(true)
    expect(gradePracticeAnswer('second', 'first|second')).toBe(true)
  })

  it('does not treat confidence as an answer', () => {
    expect(gradePracticeAnswer('', 'א')).toBe(false)
  })

  it('uses a returned per-answer grading boolean without mistaking counters for it', () => {
    expect(getAuthoritativeCorrect({ ok: true, data: { is_correct: true, correct: 4 } })).toBe(true)
    expect(getAuthoritativeCorrect({ ok: true, data: { grading: { is_correct: false } } })).toBe(false)
    expect(getAuthoritativeCorrect({ ok: true, data: { correct: 4 } })).toBe(null)
  })
})
