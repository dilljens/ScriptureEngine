import React, { useState } from 'react'
import { preprocess, createComponents } from '../lib/scripture-markdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'

/**
 * CardRenderer — renders the front of a learning card based on its type.
 *
 * Each card has: { id, type, data, queue_id }
 * The renderer shows the prompt/question on the front.
 * After rating, the back (answer/explanation) is shown.
 *
 * Some card types (learn_question) show interactive input on the front
 * and use onAnswer callback to handle submission before rating.
 */

export default function CardRenderer({ card, showAnswer, onAnswer, answerState, hebrewOnly }) {
  if (!card) return null

  // Dispatch to type-specific renderer
  switch (card.type) {
    case 'verse':
      return <VerseCardRenderer card={card} showAnswer={showAnswer} />
    case 'knowledge':
      return <KnowledgeCardRenderer card={card} showAnswer={showAnswer} />
    case 'connection':
      return <ConnectionCardRenderer card={card} showAnswer={showAnswer} />
    case 'gematria':
      return <GematriaCardRenderer card={card} showAnswer={showAnswer} />
    case 'vocab':
      return <VocabCardRenderer card={card} showAnswer={showAnswer} hebrewOnly={hebrewOnly} />
    case 'drill':
      return <DrillCardRenderer card={card} showAnswer={showAnswer} />
    case 'study_step':
      return <StudyStepCardRenderer card={card} showAnswer={showAnswer} />
    case 'hebrew_letter':
      return <HebrewLetterCardRenderer card={card} showAnswer={showAnswer} />
    case 'cloze':
      return <ClozeCardRenderer card={card} showAnswer={showAnswer} />
    case 'translation':
      return <TranslationCardRenderer card={card} showAnswer={showAnswer} />
    case 'learn_question':
      return <LearnQuestionRenderer card={card} showAnswer={showAnswer} onAnswer={onAnswer} answerState={answerState} />
    case 'assessment_question':
      return <AssessmentQuestionRenderer card={card} showAnswer={showAnswer} onAnswer={onAnswer} />
    default:
      return <div className="text-sm text-red-500">Unknown card type: {card.type}</div>
  }
}

function go(ref) {
  const p = (ref || '').split('.')
  if (p.length >= 2) window.dispatchEvent(new CustomEvent('scripture-navigate', {detail: {book: p[0], chapter: parseInt(p[1])}}))
}

// ── Verse Memory Card ──
// Front: show reference, user must recall text
// Back: show verse text
function VerseCardRenderer({ card, showAnswer }) {
  const { reference, text, book, chapter, verse } = card.data || {}
  const refStr = reference || `${book}.${chapter}.${verse}`
  return (
    <div className="text-center">
      <button onClick={() => go(refStr)} className="text-[10px] font-mono text-indigo-400 dark:text-indigo-300 mb-3 hover:text-indigo-600 dark:hover:text-indigo-200 cursor-pointer transition-colors">
        {refStr}
      </button>
      {showAnswer ? (
        <p className="text-base leading-relaxed text-neutral-800 dark:text-neutral-200 italic">
          "{text || card.data?.text_english || ''}"
        </p>
      ) : (
        <p className="text-base leading-relaxed text-neutral-500 dark:text-neutral-400">
          Recall this verse from memory…
        </p>
      )}
    </div>
  )
}

// ── Knowledge Card ──
// Front: show question/prompt
// Back: show answer/explanation
function KnowledgeCardRenderer({ card, showAnswer }) {
  const { question, answer, explanation, source } = card.data || {}
  return (
    <div>
      <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-2">
        {question || card.data?.prompt || ''}
      </p>
      {showAnswer && (
        <div className="mt-3 p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800">
          <p className="text-sm text-neutral-700 dark:text-neutral-300">{answer || ''}</p>
          {explanation && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-2">{explanation}</p>
          )}
          {source && (
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">Source: {source}</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Connection Card ──
// Front: "Which verse connects to X via type Y?"
// Back: show the connected verse + connection details
function ConnectionCardRenderer({ card, showAnswer }) {
  const { source_verse, target_verse, connection_type, layer, strength, target_text } = card.data || {}
  return (
    <div>
      <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-1">Connection Recall</p>
      <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
        {source_verse
          ? `Which verse connects to ${source_verse} via ${(connection_type || '').replace(/_/g, ' ')}?`
          : `Recall a ${(connection_type || '').replace(/_/g, ' ')} connection`}
      </p>
      {showAnswer && target_verse && (
        <div className="mt-3 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
          <button onClick={() => go(target_verse)} className="text-sm font-medium text-green-700 dark:text-green-300 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer transition-colors">{target_verse}</button>
          {target_text && <p className="text-xs text-green-600 dark:text-green-400 mt-1 italic">"{target_text.slice(0, 120)}…"</p>}
          <p className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-1">
            {connection_type} · {layer} · strength {strength?.toFixed(2)}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Gematria Card ──
// Front: show Hebrew word, ask for value
// Back: show value + meaning
function GematriaCardRenderer({ card, showAnswer }) {
  const { word, value, meaning, verse_ref } = card.data || {}
  return (
    <div className="text-center">
      {word && (
        <p className="text-2xl font-serif mb-2 text-neutral-800 dark:text-neutral-200" dir="rtl"
          style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
          {word}
        </p>
      )}
      <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
        {showAnswer ? 'Value' : 'What is the gematria value?'}
      </p>
      {showAnswer && (
        <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
          <p className="text-2xl font-bold text-amber-700 dark:text-amber-300">{value || '—'}</p>
          {meaning && <p className="text-xs text-neutral-600 dark:text-neutral-400 mt-1">{meaning}</p>}
          {verse_ref && <button onClick={() => go(verse_ref)} className="text-[10px] text-neutral-400 mt-1 hover:text-indigo-500 cursor-pointer transition-colors">{verse_ref}</button>}
        </div>
      )}
    </div>
  )
}

// ── Vocabulary Card ──
// Front: show word, ask for meaning (or vice versa)
// When hebrewOnly is true, hide transliteration on front (pure immersion)
function VocabCardRenderer({ card, showAnswer, hebrewOnly }) {
  const { word, transliteration, definition, lemma, language } = card.data || {}
  const isHebrew = language === 'hebrew' || !language
  return (
    <div className="text-center">
      <p className={`text-xl font-serif mb-2 text-neutral-800 dark:text-neutral-200 ${isHebrew ? 'text-2xl' : 'text-lg'}`}
        dir={isHebrew ? 'rtl' : 'ltr'}
        style={isHebrew ? { fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" } : {}}>
        {word || ''}
      </p>
      {transliteration && !showAnswer && !hebrewOnly && (
        <p className="text-xs text-neutral-400 italic">{transliteration}</p>
      )}
      {!showAnswer && hebrewOnly && (
        <p className="text-xs text-neutral-400 mt-2">What does this word mean?</p>
      )}
      {showAnswer && (
        <div className="mt-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
          <p className="text-sm font-medium text-blue-700 dark:text-blue-300">{definition || '—'}</p>
          {transliteration && <p className="text-xs text-neutral-500 mt-1">{transliteration}</p>}
          {lemma && <p className="text-[10px] text-neutral-400 mt-1">Strong's: {lemma}</p>}
        </div>
      )}
    </div>
  )
}

// ── Drill Card ──
// Front: show multiple-choice question
// Back: show correct answer + explanation
function DrillCardRenderer({ card, showAnswer }) {
  const { question, options, correct, explanation } = card.data || {}
  const opts = Array.isArray(options) ? options : (typeof options === 'string' ? JSON.parse(options || '[]') : [])
  return (
    <div>
      <p className="text-sm font-medium text-neutral-800 dark:text-neutral-200 mb-3">{question || ''}</p>
      {showAnswer ? (
        <div className="space-y-2">
          {opts.map((opt, i) => {
            const isCorrect = String(opt) === String(correct)
            return (
              <div key={i} className={`px-3 py-2 rounded-lg text-sm border ${
                isCorrect
                  ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                  : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-400'
              }`}>
                <span className="font-medium mr-2 text-xs">{String.fromCharCode(65 + i)}.</span>
                {opt}
              </div>
            )
          })}
          {explanation && (
            <p className="text-xs text-neutral-500 dark:text-neutral-400 mt-2 p-2 rounded bg-neutral-50 dark:bg-neutral-800/50">
              {explanation}
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-1.5">
          {opts.map((opt, i) => (
            <div key={i} className="px-3 py-2 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-500 dark:text-neutral-400">
              <span className="font-medium mr-2 text-xs">{String.fromCharCode(65 + i)}.</span>
              {opt}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Study Step Card ──
// Front: show explanation
// Back: show connections + choices
function StudyStepCardRenderer({ card, showAnswer }) {
  const { title, explanation, verse, connections, choices } = card.data || {}
  return (
    <div>
      {title && <p className="text-sm font-semibold text-neutral-800 dark:text-neutral-200 mb-2">{title}</p>}
      {verse && <p className="text-[10px] font-mono text-indigo-400 mb-1">{verse}</p>}
      {!showAnswer ? (
        <p className="text-sm text-neutral-600 dark:text-neutral-400 leading-relaxed">
          {explanation || 'Review this study step…'}
        </p>
      ) : (
        <div className="mt-3 space-y-2">
          {explanation && (
            <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">{explanation}</p>
          )}
          {connections?.length > 0 && (
            <div className="p-2 rounded bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800">
              <p className="text-[10px] font-semibold text-green-600 dark:text-green-400 uppercase mb-1">Connections</p>
              {connections.map((c, i) => (
                <p key={i} className="text-xs text-green-700 dark:text-green-300">
                  {c.type} → {c.to || ''}
                </p>
              ))}
            </div>
          )}
          {choices?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {choices.map((ch, i) => (
                <span key={i} className="text-[10px] px-2 py-1 rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400">
                  {ch.label || ch.verse} →
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Learn Question Card ──
// Handles both MC and open-ended questions from LearnView modules.
// Front: shows question + adaptive MC options (if user struggled) or pure recall prompt
// Back: shows correct answer + explanation + LLM grade
// Adaptive MC (TMAW Ch 20): options hidden for pure recall if user has been correct before
function LearnQuestionRenderer({ card, showAnswer, onAnswer, answerState }) {
  const { question, options, correct_answer, explanation, tier, bloom_level, is_open, show_options } = card.data || {}
  const [selected, setSelected] = useState(null)
  const [openInput, setOpenInput] = useState('')
  const [submitted, setSubmitted] = useState(false)

  // Front (not yet revealed): show question + adaptive MC options or pure recall prompt
  if (!showAnswer) {
    return (
      <div>
        <div className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 whitespace-pre-wrap">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={createComponents()}>
            {preprocess(question || '')}
          </ReactMarkdown>
        </div>

        {/* Source module */}
        {card.data?.source && (
          <p className="text-[10px] text-neutral-400 mt-2 italic">from {card.data.source}</p>
        )}

        {/* Adaptive MC options — only shown if user previously struggled */}
        {!is_open && show_options && options?.length > 0 && (
          <div className="space-y-1.5 mt-3">
            {options.map((opt, i) => (
              <button key={i} onClick={() => {
                setSelected(opt)
                onAnswer?.({ selected: opt })
              }}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs border transition-all cursor-pointer ${
                  selected === opt
                    ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                    : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
                }`}>
                {opt}
              </button>
            ))}
          </div>
        )}

        {/* Pure recall prompt — no options shown */}
        {!is_open && (!show_options || !options?.length) && (
          <p className="text-xs text-neutral-400 dark:text-neutral-500 italic text-center mt-4">
            Recall the answer, then click to reveal
          </p>
        )}

        {/* Open-ended input */}
        {is_open && (
          <div className="mt-3">
            <textarea value={openInput} onChange={e => setOpenInput(e.target.value)}
              placeholder="Type your answer..."
              className="w-full px-3 py-2 rounded-lg text-sm border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-indigo-400 resize-none"
              rows={3} />
            <button onClick={() => {
              if (openInput.trim()) onAnswer?.({ openInput: openInput.trim() })
            }}
              className="mt-2 px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium cursor-pointer transition-colors">
              Submit for AI Evaluation
            </button>
          </div>
        )}
      </div>
    )
  }

  // Back (answer revealed): show correct answer + explanation + LLM grade
  return (
    <div className="space-y-3">
      <div className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200 whitespace-pre-wrap">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={createComponents()}>
          {preprocess(question || '')}
        </ReactMarkdown>
      </div>
      {is_open && answerState?.llmGrade && (
        <div className="p-3 rounded-lg bg-neutral-50 dark:bg-neutral-900/30 border border-neutral-200 dark:border-neutral-700">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">AI Evaluation</p>
          <div className="grid grid-cols-2 gap-2 mb-2">
            {['text_engagement', 'reasoning', 'depth', 'context'].map(k => {
              const score = answerState.llmGrade?.scores?.[k] || answerState.llmGrade?.[k]
              if (score === undefined) return null
              return (
                <div key={k}>
                  <div className="text-[9px] text-neutral-400 capitalize mb-0.5">{k.replace('_', ' ')}</div>
                  <div className="h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
                    <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(score / 10) * 100}%` }} />
                  </div>
                  <span className="text-[10px] font-mono text-neutral-500">{score}/10</span>
                </div>
              )
            })}
          </div>
          {answerState.llmGrade.feedback && <p className="text-xs text-neutral-600 dark:text-neutral-400">{answerState.llmGrade.feedback}</p>}
        </div>
      )}
      {!is_open && (
        <div className="space-y-1.5">
          {(options || []).map((opt, i) => {
            const isCorrect = String(opt) === String(correct_answer)
            return (
              <div key={i} className={`px-3 py-2 rounded-lg text-sm border ${
                isCorrect
                  ? 'border-green-500 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-200 font-medium'
                  : 'border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 text-neutral-500'
              }`}>
                <span className="font-medium mr-2 text-xs text-neutral-400">{String.fromCharCode(65 + i)}.</span>
                {opt}
              </div>
            )
          })}
        </div>
      )}
      {explanation && (
        <div className="p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 text-xs text-neutral-700 dark:text-neutral-300 leading-relaxed">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={createComponents()}>
            {preprocess(explanation)}
          </ReactMarkdown>
        </div>
    )}
  </div>
  )
}

// ── Assessment Question Card ──
// Front: passage + question (adaptive: shows MC options if user previously struggled)
// Back: correct answer + explanation + tier/type badges
// Follows The Math Academy Way Ch 20: retrieval before reveal
function AssessmentQuestionRenderer({ card, showAnswer, onAnswer }) {
  const { question, answer, explanation, options, tier, bloom_level, layer, show_options } = card.data || {}
  const [selected, setSelected] = useState(null)

  const handleSelect = (opt) => {
    if (selected) return
    setSelected(opt)
    onAnswer?.({ selected: opt })
  }

  return (
    <div>
      {/* Question text (shown on both front and back) */}
      <div className="prose prose-sm dark:prose-invert max-w-none mb-3">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
          {question || ''}
        </ReactMarkdown>
      </div>

      {/* Tier/type badges */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        {tier && (
          <span className="text-[9px] px-2 py-0.5 rounded-full font-medium bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-700">
            {tier === 'text' ? '🔬' : tier === 'analysis' ? '🔍' : '🤝'} {tier}
          </span>
        )}
        {bloom_level && (
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-500">
            {bloom_level}
          </span>
        )}
        {layer && (
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400">
            {layer}
          </span>
        )}
      </div>

      {/* Adaptive MC options — only shown if user previously struggled */}
      {!showAnswer && show_options && options?.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {options.map((opt, i) => (
            <button key={i} onClick={() => handleSelect(opt)}
              className={`w-full text-left px-3 py-2 rounded-lg text-xs border transition-all cursor-pointer ${
                selected === opt
                  ? 'border-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-300'
                  : 'border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:border-indigo-300 dark:hover:border-indigo-600'
              }`}>
              {opt}
            </button>
          ))}
        </div>
      )}

      {/* No options shown — prompt user to recall */}
      {!showAnswer && (!show_options || !options?.length) && (
        <p className="text-xs text-neutral-400 dark:text-neutral-500 italic text-center py-2">
          {options?.length ? 'Select an option above, then flip to check' : 'Recall the answer, then click to reveal'}
        </p>
      )}

      {/* Back: answer + explanation */}
      {showAnswer && (
        <div className="space-y-3 mt-2 p-4 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-700">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-indigo-500 dark:text-indigo-400 mb-1">
              {selected ? (selected === answer ? '✅ Correct' : '❌ Incorrect') : 'Answer'}
            </p>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                {answer || ''}
              </ReactMarkdown>
            </div>
          </div>
          {explanation && (
            <div className="p-3 rounded-lg bg-white dark:bg-neutral-800 border border-indigo-100 dark:border-neutral-700">
              <p className="text-[9px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Explanation</p>
              <div className="prose prose-xs dark:prose-invert max-w-none text-xs">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                  {explanation}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}



// ── Cloze Deletion Card ──
// Front: shows verse with a word replaced by [___]
// Back: shows complete verse with target word highlighted
function ClozeCardRenderer({ card, showAnswer }) {
  const { passage, answer, verse_ref, hint, word_hebrew } = card.data || {}
  return (
    <div>
      {verse_ref && <button onClick={() => go(verse_ref)} className="text-[10px] font-mono text-indigo-400 mb-2 hover:text-indigo-600 dark:hover:text-indigo-200 cursor-pointer transition-colors">{verse_ref}</button>}
      {!showAnswer ? (
        <div>
          <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
            {passage || ''}
          </p>
          {hint && <p className="text-xs text-neutral-400 mt-2 italic">Hint: {hint}</p>}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
            {answer || passage || ''}
          </p>
          {word_hebrew && (
            <p className="text-lg font-serif text-center text-indigo-600 dark:text-indigo-400 mt-2"
              style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
              dir="rtl">
              {word_hebrew}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Two-Way Translation Card ──
// Front: shows English phrase, user must recall Hebrew
// Back: shows Hebrew text + transliteration + audio
function TranslationCardRenderer({ card, showAnswer }) {
  const { english, hebrew, transliteration, verse_ref, lemma } = card.data || {}
  return (
    <div>
      {verse_ref && <button onClick={() => go(verse_ref)} className="text-[10px] font-mono text-indigo-400 mb-2 hover:text-indigo-600 dark:hover:text-indigo-200 cursor-pointer transition-colors">{verse_ref}</button>}
      {!showAnswer ? (
        <p className="text-sm leading-relaxed text-neutral-800 dark:text-neutral-200">
          {english || ''}
        </p>
      ) : (
        <div className="space-y-3 text-center">
          <p className="text-lg font-serif text-neutral-800 dark:text-neutral-200"
            style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}
            dir="rtl">
            {hebrew || ''}
          </p>
          {transliteration && <p className="text-sm text-neutral-500 italic">{transliteration}</p>}
          {english && <p className="text-xs text-neutral-400">{english}</p>}
          {lemma && <p className="text-[9px] text-neutral-400">Strong's: {lemma}</p>}
        </div>
      )}
    </div>
  )
}

// ── Hebrew Letter Card ──
// Front: show letter, ask for name/sound
// Back: show name, transliteration, classification
function HebrewLetterCardRenderer({ card, showAnswer }) {
  const { letter, name, transliteration, classification, example } = card.data || {}
  return (
    <div className="text-center">
      <p className="text-5xl font-serif mb-4 text-neutral-800 dark:text-neutral-200"
        style={{ fontFamily: "'SBL_Hebrew','Ezra_SIL','Times_New_Roman',serif" }}>
        {letter || ''}
      </p>
      {showAnswer && (
        <div className="space-y-2">
          {name && <p className="text-lg font-medium text-indigo-600 dark:text-indigo-400">{name}</p>}
          {transliteration && <p className="text-sm text-neutral-500 italic">{transliteration}</p>}
          {classification && <p className="text-xs text-neutral-400">{classification}</p>}
          {example && <p className="text-xs text-neutral-400 mt-2">Example: {example}</p>}
        </div>
      )}
    </div>
  )
}
