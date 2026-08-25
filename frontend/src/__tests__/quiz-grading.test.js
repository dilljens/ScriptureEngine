import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import CardRenderer from '../components/CardRenderer'
import {
  ANSWER_MODES,
  answerModeForQuestion,
  getChoiceFeedback,
  gradeQuizAnswer,
} from '../lib/quiz-grading'

describe('canonical quiz grading', () => {
  const options = ['Aleph', 'Bet', 'Gimel']

  it('resolves a stored choice label when the submitted answer is an index', () => {
    expect(gradeQuizAnswer({
      answer: 1,
      correctAnswer: 'Bet',
      options,
      mode: ANSWER_MODES.CHOICE_INDEX,
    })).toBe(true)
  })

  it('does not treat a choice index as free text', () => {
    expect(gradeQuizAnswer({
      answer: 1,
      correctAnswer: 'Bet',
      options,
      mode: ANSWER_MODES.FREE_TEXT,
    })).toBe(false)
  })

  it('honors explicit free-text mode even when options are present', () => {
    const question = {
      type: 'multiple_choice',
      options,
      answer_mode: ANSWER_MODES.FREE_TEXT,
    }

    expect(answerModeForQuestion(question)).toBe(ANSWER_MODES.FREE_TEXT)
    expect(gradeQuizAnswer({
      answer: 'write in answer',
      correctAnswer: 'write in answer',
      options,
      mode: answerModeForQuestion(question),
    })).toBe(true)
    expect(gradeQuizAnswer({
      answer: 0,
      correctAnswer: 'write in answer',
      options,
      mode: answerModeForQuestion(question),
    })).toBe(false)
  })

  it('renders a text input instead of option-index controls for explicit free text', () => {
    const html = renderToStaticMarkup(React.createElement(CardRenderer, {
      card: {
        id: 'free-text-with-options',
        type: 'drill',
        data: {
          question: 'Explain the answer in your own words',
          options,
          correct: 'A written answer',
          answer_mode: ANSWER_MODES.FREE_TEXT,
        },
      },
      showAnswer: false,
    }))

    expect(html).toContain('<input')
    expect(html).not.toContain('Aleph')
    expect(html).not.toContain('Bet')
  })

  it('keeps correct choice feedback mutually exclusive from incorrect feedback', () => {
    const feedback = getChoiceFeedback({
      answer: 1,
      optionIndex: 1,
      correctAnswer: 'Bet',
      options,
    })

    expect(feedback.isAnswerCorrect).toBe(true)
    expect(feedback.isCorrectOption).toBe(true)
    expect(feedback.isIncorrectSelection).toBe(false)
  })

  it('marks only a wrong selected option red', () => {
    const feedback = getChoiceFeedback({
      answer: 0,
      optionIndex: 0,
      correctAnswer: 'Bet',
      options,
    })

    expect(feedback.isAnswerCorrect).toBe(false)
    expect(feedback.isCorrectOption).toBe(false)
    expect(feedback.isIncorrectSelection).toBe(true)
  })
})
