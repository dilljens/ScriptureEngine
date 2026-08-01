import { describe, expect, it } from 'vitest'
import { gradePracticeAnswer } from '../components/HebrewLessonView'

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

  it('does not treat confidence as an answer', () => {
    expect(gradePracticeAnswer('', 'א')).toBe(false)
  })
})
