/**
 * Card Factory — converts various content types into generic cards
 * consumable by CardQueue.
 *
 * Each card has: { id, type, data, queue_id }
 */

/**
 * Convert lesson module questions to learn_question cards for CardQueue.
 * Supports both MC and open-ended questions with adaptive option visibility.
 *
 * Adaptive MC (TMAW Ch 20): if user has struggled with a question before,
 * show options. If they've been correct, hide options for pure recall.
 *
 * @param {Object} module — module with questions array
 * @param {Object} progress — { [question_id]: { correct, attempts } }
 * @returns {Array} learn_question cards
 */
export function lessonToCards(module, progress = {}) {
  if (!module?.questions) return []
  return module.questions.map((q, i) => {
    const prog = progress[q.id] || {}
    const showOptions = prog.attempts > 0 && prog.correct < prog.attempts
    return {
      id: `lesson-${module.id}-q-${q.id || i}`,
      type: 'learn_question',
      data: {
        question_id: q.id,
        question: q.question,
        options: q.options || [],
        correct_answer: q.correct_answer,
        explanation: q.explanation || '',
        tier: q.tier || '',
        bloom_level: q.bloom_level || '',
        is_open: Boolean(q.is_open),
        source: module.title,
        show_options: showOptions && (q.options?.length > 0),
      },
    }
  })
}

/**
 * Convert wiki article entities to knowledge cards.
 */
export function wikiToCards(articles) {
  if (!articles?.length) return []
  return articles.map(a => ({
    id: `wiki-${a.id}`,
    type: 'knowledge',
    data: {
      question: `What is "${a.title}"?`,
      answer: a.summary || a.content?.slice(0, 200) || '',
      explanation: '',
      source: 'Wiki',
    },
  }))
}

/**
 * Convert Hebrew curriculum nodes to vocabulary/hebrew_letter cards.
 */
export function hebrewToCards(nodes) {
  if (!nodes?.length) return []
  const cards = []
  for (const n of nodes) {
    if (n.category === 'consonant' && n.hebrew) {
      cards.push({
        id: `heb-letter-${n.id}`,
        type: 'hebrew_letter',
        data: {
          letter: n.hebrew,
          name: n.title,
          transliteration: n.transliteration || '',
          classification: n.category || 'consonant',
          example: n.example || '',
        },
      })
    } else if (n.category === 'word' && n.hebrew) {
      cards.push({
        id: `heb-vocab-${n.id}`,
        type: 'vocab',
        data: {
          word: n.hebrew,
          transliteration: n.transliteration || '',
          definition: n.title || n.description || '',
          lemma: n.lemma || '',
          language: 'hebrew',
        },
      })
    }
  }
  return cards
}

/**
 * Convert verse connection data to connection cards.
 * @param {string} sourceVerse - The anchor verse
 * @param {Array} connections - Array of connection objects
 */
export function connectionsToCards(sourceVerse, connections) {
  if (!connections?.length) return []
  return connections.map((c, i) => ({
    id: `conn-${sourceVerse}-${i}`,
    type: 'connection',
    data: {
      source_verse: sourceVerse,
      target_verse: c.target || c.to || '',
      connection_type: c.type || '',
      layer: c.layer || '',
      strength: c.strength || c.confidence || 0.5,
      target_text: c.target_text || c.to_text || '',
    },
  }))
}

/**
 * Convert gematria data to gematria cards.
 */
export function gematriaToWords(words) {
  if (!words?.length) return []
  return words.map((w, i) => ({
    id: `gem-${i}`,
    type: 'gematria',
    data: {
      word: w.word_hebrew || w.word || '',
      value: w.value_standard || w.value || 0,
      meaning: w.meaning || '',
      verse_ref: w.verse_id || '',
    },
  }))
}

/**
 * Convert study guide steps to study_step cards.
 */
export function studyToCards(study) {
  if (!study?.steps?.length) return []
  return study.steps.map((s, i) => ({
    id: `study-${study.id || study.guide_id}-step-${i}`,
    type: 'study_step',
    data: {
      title: s.title || '',
      explanation: s.explanation || '',
      verse: s.verse || s.verse_id || '',
      connections: (s.connections || []).slice(0, 5),
      choices: s.choices || [],
    },
  }))
}

/**
 * Convert Hebrew verb drills to drill cards.
 */
export function drillsToCards(drills) {
  if (!drills?.length) return []
  return drills.map((d, i) => ({
    id: `drill-${d.node_id || i}`,
    type: 'drill',
    data: {
      question: d.question || '',
      options: typeof d.options === 'string' ? JSON.parse(d.options) : (d.options || []),
      correct: d.correct || '',
      explanation: d.explanation || '',
    },
  }))
}

/**
 * Generate cloze deletion cards from a verse.
 * Masks one or more key words for recall.
 */
export function clozeFromVerse(verse) {
  if (!verse?.text_english || !verse?.id) return []
  const text = verse.text_english
  const words = text.split(/\s+/)
  if (words.length < 5) return []

  // Find the most significant word to blank (verb or noun, not article/prep)
  const skipWords = new Set(['the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'at', 'by', 'with', 'from', 'for'])
  const candidates = words.filter(w => w.length > 3 && !skipWords.has(w.toLowerCase().replace(/[^a-z]/g, '')))

  if (candidates.length === 0) return []

  const cards = []
  // Create cloze cards for up to 2 key words in this verse
  const chosen = candidates.slice(0, 2)
  for (const target of chosen) {
    const blanked = text.replace(new RegExp(`\\b${target.replace(/[.*+?^${}()|[\]\\]/g, '\\$')}\\b`, 'i'), '[___]')
    if (blanked === text) continue  // no replacement happened

    cards.push({
      id: `cloze-${verse.id}-${target.toLowerCase().replace(/[^a-z]/g, '')}`,
      type: 'cloze',
      data: {
        passage: blanked,
        answer: text,
        verse_ref: verse.id,
        word_hebrew: verse.text_hebrew || '',
        hint: `${target.length} letters`,
      },
    })
  }
  return cards
}

/**
 * Generate two-way translation cards from a verse.
 * Front: English. Back: Hebrew + transliteration.
 */
export function translationFromVerse(verse) {
  if (!verse?.text_english || !verse?.text_hebrew || !verse?.id) return []
  return [{
    id: `trans-${verse.id}`,
    type: 'translation',
    data: {
      english: verse.text_english,
      hebrew: verse.text_hebrew,
      transliteration: verse.transliteration || '',
      verse_ref: verse.id,
    },
  }]
}

/**
 * Interleave cards from multiple sources, preventing blocking.
 * No more than `maxConsecutive` cards of the same type appear consecutively.
 * Within each type group, original order is preserved.
 *
 * @param {...Array[]} cardArrays — multiple arrays of cards
 * @param {number} maxConsecutive — max same-type in a row (default 2)
 * @returns {Array} interleaved card array
 */
export function interleaveCards(cardArrays, maxConsecutive = 2) {
  const sources = cardArrays.filter(arr => arr?.length > 0)
  if (sources.length === 0) return []
  if (sources.length === 1) return [...sources[0]]

  // Group cards by type
  const byType = {}
  const typeOrder = []
  for (const arr of sources) {
    for (const card of arr) {
      const t = card.type || 'unknown'
      if (!byType[t]) { byType[t] = []; typeOrder.push(t) }
      byType[t].push(card)
    }
  }

  const result = []
  let consecutive = 0
  let lastType = null
  const ptr = {}
  for (const t of typeOrder) ptr[t] = 0

  const total = Object.values(byType).reduce((sum, arr) => sum + arr.length, 0)

  while (result.length < total) {
    let picked = false
    for (const t of typeOrder) {
      if (ptr[t] >= byType[t].length) continue
      if (t === lastType && consecutive >= maxConsecutive) continue
      result.push(byType[t][ptr[t]++])
      if (t === lastType) { consecutive++ }
      else { consecutive = 1; lastType = t }
      picked = true
      break
    }
    // Fallback: if all blocked, take next available
    if (!picked) {
      for (const t of typeOrder) {
        if (ptr[t] >= byType[t].length) continue
        result.push(byType[t][ptr[t]++])
        lastType = t
        consecutive = 1
        break
      }
    }
  }

  return result
}


/**
 * Convert assessment items to flashcards.
 * Follows The Math Academy Way Ch 20: retrieval before reveal.
 *
 * Adaptive MC: if user has struggled (answered wrong before), show options.
 * If user has been correct, hide options for pure recall.
 *
 * @param {Array} items — assessment_items rows from /api/v1/quiz
 * @param {Object} progress — { [question_id]: { correct, attempts } } from quiz_progress
 * @returns {Array} assessment_question cards
 */
export function assessmentToCards(items, progress = {}) {
  if (!items?.length) return []
  return items.map(item => {
    const prog = progress[item.question_id] || progress[item.id] || { correct: 0, attempts: 0 }
    // Show MC options if the user has ever answered this item wrong
    const showOptions = prog.attempts > 0 && prog.correct < prog.attempts
    return {
      id: `assessment-${item.question_id || item.id}`,
      type: 'assessment_question',
      data: {
        question: item.question || item.question_text,
        answer: item.correct_answer,
        explanation: item.explanation || '',
        options: item.options || [],
        tier: item.tier || 'text',
        bloom_level: item.bloom_level || '',
        layer: item.layer || '',
        show_options: showOptions && (item.options?.length > 0),
      },
    }
  })
}
