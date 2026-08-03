import React, { useCallback, useEffect, useState } from 'react'
import { getCfmLessons, getCfmLesson, getCfmLessonScriptures, getChapter } from '../api'

const CFM_YEAR = 2026

export default function CfmStudyView({ week, onBack, onBrowse, onNavigate, onStudyInChat }) {
  const [lessons, setLessons] = useState(null)      // all 52 weeks
  const [lesson, setLesson] = useState(null)        // active lesson detail
  const [scriptures, setScriptures] = useState(null)// parsed scripture blocks
  const [err, setErr] = useState('')
  // week slug ('03' …); null = current week
  const [weekSlug, setWeekSlug] = useState(week || null)
  const [currentWeek, setCurrentWeek] = useState(null) // slug of the actual current week
  const [expandedKey, setExpandedKey] = useState(null)   // 'gen.1' … — expanded chapter
  const [chapters, setChapters] = useState({})           // 'gen.1' → {verses:[…]}
  const [loadingCh, setLoadingCh] = useState(null)

  // Load the 52-week list once
  useEffect(() => {
    let cancelled = false
    getCfmLessons(CFM_YEAR)
      .then(r => { if (!cancelled) setLessons(r.data?.lessons || []) })
      .catch(() => { if (!cancelled) setErr('Could not load the Come Follow Me schedule.') })
    return () => { cancelled = true }
  }, [])

  // Resolve the active week (explicit slug, else the current calendar week)
  useEffect(() => {
    if (!lessons || lessons.length === 0) return
    const today = new Date().toISOString().slice(0, 10)
    const current = lessons.find(l => l.start_date <= today && today <= l.end_date) || lessons[0]
    setCurrentWeek(current?.week_slug || null)
    if (!weekSlug) setWeekSlug(current?.week_slug || lessons[0]?.week_slug)
  }, [lessons, weekSlug])

  // Load the active lesson + its scripture blocks
  useEffect(() => {
    if (!weekSlug) return
    let cancelled = false
    setLesson(null); setScriptures(null); setExpandedKey(null); setChapters({})
    const refId = `cfm.${CFM_YEAR}.${weekSlug}`
    getCfmLesson(refId)
      .then(r => { if (!cancelled) setLesson(r.data) })
      .catch(() => { if (!cancelled) setErr(`Could not load lesson ${weekSlug}.`) })
    getCfmLessonScriptures(refId)
      .then(r => { if (!cancelled) setScriptures(r.data?.blocks || []) })
      .catch(() => {})
    return () => { cancelled = true }
  }, [weekSlug])

  const active = lessons?.find(l => l.week_slug === weekSlug) || null
  const currentIdx = lessons?.findIndex(l => l.week_slug === weekSlug) ?? -1

  const goWeek = useCallback((delta) => {
    if (!lessons || currentIdx < 0) return
    const target = lessons[Math.max(0, Math.min(lessons.length - 1, currentIdx + delta))]
    if (target) setWeekSlug(target.week_slug)
  }, [lessons, currentIdx])

  const loadChapter = useCallback(async (bookId, ch) => {
    const key = `${bookId}.${ch}`
    setExpandedKey(key)
    if (chapters[key]) return
    setLoadingCh(key)
    try {
      const r = await getChapter(key)
      setChapters(p => ({ ...p, [key]: r.data || {} }))
    } catch {
      setChapters(p => ({ ...p, [key]: { error: true } }))
    } finally {
      setLoadingCh(null)
    }
  }, [chapters])

  const askAboutLesson = () => {
    const title = lesson?.title || active?.title || `week ${weekSlug}`
    const block = active?.scripture_block || lesson?.scripture_block || ''
    onStudyInChat?.(
      `I'm studying this week's Come Follow Me lesson: "${title}"${block ? ` (${block})` : ''}. ` +
      'Help me study it — start with what the lesson text says, walk me through the scriptures it points to, and answer my questions as we go.',
      'cfm',
    )
  }

  const askAboutVerse = (bookId, ch, v) => {
    onStudyInChat?.(
      `In this week's Come Follow Me lesson, what does ${bookId} ${ch}:${v} say, and how does it connect to the lesson's theme?`,
      'cfm',
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <button onClick={onBack}
          className="px-3 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
          ← Library
        </button>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">📖 Come Follow Me — Weekly Study</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">Old Testament 2026 · read the lesson, read the scriptures, ask chat</p>
        </div>
        <button onClick={onBrowse}
          className="px-3 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
          Browse all lessons
        </button>
      </div>

      {err && <div className="text-sm text-rose-500 py-4 text-center">{err}</div>}
      {!lessons && !err && (
        <div className="text-center py-12">
          <div className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">Loading schedule…</p>
        </div>
      )}

      {/* Week selector */}
      {lessons && (
        <div className="flex items-center gap-2 mb-5 flex-wrap">
          <button onClick={() => goWeek(-1)} disabled={currentIdx <= 0}
            className="px-3 py-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-neutral-100 dark:disabled:hover:bg-neutral-700 transition-colors cursor-pointer">
            ← Last week
          </button>
          <select value={weekSlug || ''} onChange={e => setWeekSlug(e.target.value)}
            className="flex-1 min-w-[220px] px-2.5 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 outline-none focus:border-blue-400 cursor-pointer">
            {lessons.map(l => (
              <option key={l.week_slug} value={l.week_slug}>
                {`Wk ${l.week_slug} · ${l.date_range} — ${l.scripture_block}${l.week_slug === currentWeek ? ' (this week)' : ''}`}
              </option>
            ))}
          </select>
          <button onClick={() => goWeek(1)} disabled={currentIdx >= lessons.length - 1}
            className="px-3 py-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-neutral-100 dark:disabled:hover:bg-neutral-700 transition-colors cursor-pointer">
            Next week →
          </button>
          {currentWeek && weekSlug !== currentWeek && (
            <button onClick={() => setWeekSlug(currentWeek)}
              className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors cursor-pointer">
              ⦿ Jump to this week
            </button>
          )}
        </div>
      )}

      {/* Lesson card */}
      {lesson && (
        <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-5 mb-6">
          <div className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider mb-1">{active?.date_range}</div>
          <h3 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200 leading-snug">{lesson.title}</h3>
          {lesson.scripture_block && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {lesson.scripture_block.split(';').map((s, i) => (
                <span key={i} className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-800/60 text-amber-700 dark:text-amber-300">{s.trim()}</span>
              ))}
            </div>
          )}
          <div className="mt-4 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{lesson.text}</div>
        </div>
      )}

      {/* Scripture reading */}
      {scriptures && scriptures.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2">Read the Scriptures</h3>
          <div className="space-y-3">
            {scriptures.map((b, bi) => {
              const rangeLabel = b.whole_book ? b.book : `${b.book} ${b.chapters[0]}–${b.chapters[b.chapters.length - 1]}`
              const chCount = b.chapters.length
              return (
                <div key={`${b.book_id}-${bi}`} className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-2.5 bg-neutral-50 dark:bg-neutral-800/60">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">{rangeLabel}</span>
                      <span className="text-[10px] text-neutral-400 dark:text-neutral-500">{chCount} chapter{chCount > 1 ? 's' : ''}</span>
                    </div>
                    <button
                      onClick={() => onNavigate?.(b.book_id, b.chapters[0])}
                      className="text-[11px] px-2 py-1 rounded-md text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors cursor-pointer">
                      Open in reader ↗
                    </button>
                  </div>
                  <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
                    {b.chapters.map(ch => (
                      <ChapterRow key={`${b.book_id}.${ch}`} bookId={b.book_id} book={b.book} ch={ch}
                        chapters={chapters} expandedKey={expandedKey} loadingCh={loadingCh}
                        onToggle={loadChapter} onAsk={askAboutVerse} />
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
      {scriptures && scriptures.length === 0 && lesson && (
        <div className="text-sm text-neutral-500 dark:text-neutral-400 mb-6 py-3 text-center border border-dashed border-neutral-300 dark:border-neutral-600 rounded-xl">
          This week's lesson has no scripture block (introductory / holiday lesson).
        </div>
      )}

      {/* Ask chat */}
      {lesson && (
        <div className="sticky bottom-4 flex justify-center">
          <button onClick={askAboutLesson}
            className="px-5 py-2.5 rounded-full bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-medium shadow-lg transition-colors cursor-pointer">
            💬 Ask chat about this lesson
          </button>
        </div>
      )}
    </div>
  )
}

function ChapterRow({ bookId, book, ch, chapters, expandedKey, loadingCh, onToggle, onAsk }) {
  const key = `${bookId}.${ch}`
  const isOpen = expandedKey === key
  const data = chapters[key]

  return (
    <div>
      <button onClick={() => onToggle(bookId, ch)}
        className="w-full flex items-center justify-between px-4 py-2 text-left hover:bg-neutral-50 dark:hover:bg-neutral-700/40 transition-colors cursor-pointer">
        <span className="text-[13px] font-medium text-neutral-700 dark:text-neutral-300">{book} {ch}</span>
        <span className="text-[10px] text-neutral-400">{isOpen ? '▲' : '▼'}</span>
      </button>
      {isOpen && (
        <div className="px-4 pb-3">
          {loadingCh === key ? (
            <div className="animate-pulse text-xs text-neutral-400 py-2">Loading {book} {ch}…</div>
          ) : data?.error ? (
            <div className="text-xs text-rose-500 py-2">Couldn't load {book} {ch}.</div>
          ) : data?.verses ? (
            <div className="space-y-2">
              {data.verses.map(v => (
                <div key={v.verse} className="flex gap-2 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
                  <span className="text-[10px] font-semibold text-blue-500 dark:text-blue-400 mt-1 shrink-0 w-6 text-right">{v.verse}</span>
                  <span className="flex-1">{v.text_english}</span>
                  <button
                    onClick={() => onAsk(bookId, ch, v.verse)}
                    title="Ask chat about this verse"
                    className="text-[10px] px-1.5 py-0.5 rounded text-indigo-500 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors cursor-pointer shrink-0">
                    💬
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-neutral-400 py-2">No verses.</div>
          )}
        </div>
      )}
    </div>
  )
}
