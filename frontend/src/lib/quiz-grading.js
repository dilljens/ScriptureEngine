/**
 * Canonical answer semantics shared by interactive quiz cards.
 *
 * Choice answers are indexes into `options`; free-text answers are normalized
 * strings. A stored choice label is accepted as a compatibility representation
 * of the canonical choice index, but a numeric answer is never treated as
 * free text unless the caller explicitly selects FREE_TEXT.
 */
export const ANSWER_MODES = Object.freeze({
  CHOICE_INDEX: 'choice_index',
  FREE_TEXT: 'free_text',
})

export const CHOICE_QUESTION_TYPES = new Set([
  'multiple_choice',
  'true_false',
  'letter_name',
  'letter_recognition',
  'classification',
])

export function normalizeQuizAnswer(value) {
  const text = String(value ?? '').trim().toLowerCase().replace(/\s+/g, ' ')
  return /[\u0590-\u05ff]/.test(text)
    ? text.replace(/[\u0591-\u05af]/g, '').replace(/\//g, '')
    : text
}

function integerIndex(value) {
  if (typeof value === 'number' && Number.isInteger(value)) return value
  if (typeof value === 'string' && /^\d+$/.test(value.trim())) return Number(value.trim())
  return null
}

/** Resolve either an explicit index or a legacy option label to its index. */
export function getChoiceIndex(value, options = []) {
  if (!Array.isArray(options) || options.length === 0) return null

  const index = integerIndex(value)
  if (index !== null) return index >= 0 && index < options.length ? index : null

  const normalized = normalizeQuizAnswer(value)
  if (!normalized) return null
  const found = options.findIndex(option => normalizeQuizAnswer(option) === normalized)
  return found >= 0 ? found : null
}

export function getCorrectChoiceIndex(correctAnswer, options = []) {
  return getChoiceIndex(correctAnswer, options)
}

function answerAlternatives(value) {
  const text = String(value ?? '')
  return [text, ...text.split(/\s+or\s+|[|/]/i)]
}

export function gradeQuizAnswer({
  answer,
  correctAnswer,
  options = [],
  mode = ANSWER_MODES.FREE_TEXT,
} = {}) {
  if (mode === ANSWER_MODES.CHOICE_INDEX) {
    const actualIndex = getChoiceIndex(answer, options)
    const correctIndex = getCorrectChoiceIndex(correctAnswer, options)
    return actualIndex !== null && correctIndex !== null && actualIndex === correctIndex
  }

  const actual = normalizeQuizAnswer(answer)
  if (!actual) return false
  return answerAlternatives(correctAnswer)
    .map(normalizeQuizAnswer)
    .some(candidate => candidate === actual)
}

export function answerModeForQuestion(question = {}) {
  if (question.answer_mode) return question.answer_mode
  const type = question.type || question.questionType || question.question_type
  return CHOICE_QUESTION_TYPES.has(type) && (question.options || []).length > 0
    ? ANSWER_MODES.CHOICE_INDEX
    : ANSWER_MODES.FREE_TEXT
}

/**
 * Keep option feedback mutually exclusive. Unknown answer keys are left
 * neutral instead of painting the selected option red by accident.
 */
export function getChoiceFeedback({ answer, optionIndex, correctAnswer, options = [] } = {}) {
  const selectedIndex = getChoiceIndex(answer, options)
  const correctIndex = getCorrectChoiceIndex(correctAnswer, options)
  const isAnswerCorrect = selectedIndex !== null
    && correctIndex !== null
    && selectedIndex === correctIndex
  return {
    selectedIndex,
    correctIndex,
    isAnswerCorrect,
    isCorrectOption: correctIndex !== null && optionIndex === correctIndex,
    isIncorrectSelection: correctIndex !== null
      && selectedIndex !== null
      && optionIndex === selectedIndex
      && selectedIndex !== correctIndex,
  }
}
