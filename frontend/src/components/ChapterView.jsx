import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useToggles } from './ToggleProvider'
import { useProgress } from '../progress'
import { getFootnotes, getTskCrossrefs, getChapterGrammar, getChapterConnections } from '../api'
import ChiasmPanel from './ChiasmPanel'
import VerseBlock from './VerseBlock'
import VerseAudioPlayer from './VerseAudioPlayer'
import WikiLayout from './WikiLayout'
import { useTabs } from '../tabContext'

const LS_WIKI_KEY = 'scriptureengine.wikiMode'

function useChapterData(book, chapter) {
  const cache = {}
  const [d, sd] = useState(null); const [l, sl] = useState(true); const [e, se] = useState(null)
  // Expose a retry counter so the caller can trigger a refetch
  const [retryCount, setRetryCount] = useState(0)
  useEffect(() => {
    const key = `${book}.${chapter}`
    const c = cache[key]
    if (c && retryCount === 0) { sd(c); sl(false); se(null); return }
    let cancel = false; let att = 0
    const tf = () => {
      if (cancel) return
      sl(true); se(null)
      fetch(`/api/v1/chapter/${key}`)
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`, { cause: { status: r.status } })
          return r.json()
        })
        .then(r => { if (!cancel) { cache[key] = r.data; sd(r.data); sl(false) } })
        .catch(err => {
          if (cancel) return
          // Don't retry on 4xx errors — they're permanent (book doesn't have that chapter)
          const status = err.cause?.status || 0
          if (status >= 400 && status < 500) {
            se(err.message); sl(false); return
          }
          att++; if (att < 5) setTimeout(tf, Math.min(1000 * 2 ** att, 8000)); else { se(err.message); sl(false) }
        })
    }
    tf()
    return () => { cancel = true }
  }, [book, chapter, retryCount])
  const retry = () => setRetryCount(c => c + 1)
  return { data: d, loading: l, error: e, retry }
}

export default function ChapterView({ book, chapter, poetryMode, highlightVerse, onSplit, companionLabel, onCloseCompanion }) {
  const { toggles, displayLang, setDisplayLang, showTranslit, setShowTranslit, showEnglish, setShowEnglish, hebrewDisplayMode } = useToggles()
  const { data, loading, error, retry } = useChapterData(book, chapter)
  const [footnotes, setFootnotes] = useState(null)
  const [tskRefs, setTskRefs] = useState(null)
  const [wordData, setWordData] = useState(null)
  const [chapterConnections, setChapterConnections] = useState(null)
  const { isReviewed, toggleReviewed, markReviewed } = useProgress()
  const [verseJump, setVerseJump] = useState('')
  const verseInputRef = useRef(null)
  const [wikiMode, setWikiMode] = useState(() => localStorage.getItem(LS_WIKI_KEY) === 'true')
  const { openWikiTab } = useTabs()

  useEffect(() => {
    const handler = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return
      if (/^[0-9]$/.test(e.key)) { e.preventDefault(); verseInputRef.current?.focus() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const jumpToVerse = (vnum) => {
    if (!vnum) return
    const el = document.getElementById(`verse-${book}.${chapter}.${vnum}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('ring-2', 'ring-blue-400', 'rounded-lg')
      setTimeout(() => el.classList.remove('ring-2', 'ring-blue-400', 'rounded-lg'), 2000)
    }
    setVerseJump('')
    verseInputRef.current?.blur()
  }

  // Parallel fetch sub-requests — only for toggles that are enabled
  useEffect(() => {
    const ref = `${book}.${chapter}`
    const fetches = []

    if (toggles.footnotes) fetches.push(
      getFootnotes(ref).then(r => { setFootnotes(r.data?.footnotes || []) }).catch(() => setFootnotes([]))
    )
    if (toggles.tsk) fetches.push(
      getTskCrossrefs(ref).then(r => setTskRefs(r.data?.cross_references || [])).catch(() => setTskRefs([]))
    )
    if (toggles.gematria || toggles.lemma || displayLang !== 'english') fetches.push(
      getChapterGrammar(ref).then(r => setWordData(r.data?.verses || {})).catch(() => setWordData({}))
    )
    // Only fetch connections if any connection-related toggle is on
    const hasConnToggles = toggles.direct || toggles.allusion || toggles.echo || toggles.places || toggles.times || toggles.isaiah
    if (hasConnToggles) fetches.push(
      getChapterConnections(ref).then(r => setChapterConnections(r.data?.verses || {})).catch(() => setChapterConnections({}))
    )

    if (fetches.length > 0) Promise.all(fetches)

    // Prefetch adjacent chapters after current loads
    const prefetchNext = () => {
      const nextCh = chapter + 1
      const prevCh = chapter - 1
      // Prefetch next chapter
      const n = document.createElement('link')
      n.rel = 'prefetch'; n.href = `/api/v1/chapter/${book}.${nextCh}`
      document.head.appendChild(n)
      // Prefetch previous chapter if not first
      if (prevCh >= 1) {
        const p = document.createElement('link')
        p.rel = 'prefetch'; p.href = `/api/v1/chapter/${book}.${prevCh}`
        document.head.appendChild(p)
      }
    }
    // Delay prefetch slightly so current rendering gets priority
    const prefetchTimer = setTimeout(prefetchNext, 2000)
    return () => { clearTimeout(prefetchTimer) }
  }, [book, chapter, toggles, displayLang])

  const verseRefs = useRef({})
  useEffect(() => {
    if (highlightVerse && verseRefs.current[highlightVerse]) {
      verseRefs.current[highlightVerse].scrollIntoView({ behavior: 'smooth', block: 'center' })
      markReviewed(`${book}.${chapter}.${highlightVerse}`)
    }
  }, [highlightVerse, book, chapter])

  const LAYER_MAP = {
    intertextual: [
      { toggle: 'direct', types: ['direct_quotation', 'modified_quotation'] },
      { toggle: 'allusion', types: ['allusion'] },
      { toggle: 'echo', types: ['echo'] },
    ],
    geographic: [
      { toggle: 'places', types: ['same_location', 'journey_path', 'wilderness_sojourn', 'exile_route', 'promised_land', 'mountain_of_god', 'temple_location', 'garden_presence'] },
    ],
    chronological: [
      { toggle: 'times', types: ['same_time_period', 'feast_connection', 'chronological_marker', 'sabbatical_cycle', 'jubilee_cycle', 'dispensation', 'prophetic_timeline'] },
    ],
    interpretive: [
      { toggle: 'isaiah', types: ['giliadi_pattern'] },
    ],
  }

  const connectionsByVerse = useMemo(() => {
    if (!chapterConnections) return {}
    const result = {}
    for (const [vnum, conns] of Object.entries(chapterConnections)) {
      const grouped = {}
      for (const c of conns) {
        for (const rules of Object.values(LAYER_MAP)) {
          for (const rule of rules) {
            if (rule.types.includes(c.type) && toggles[rule.toggle]) {
              if (!grouped[rule.toggle]) grouped[rule.toggle] = []
              grouped[rule.toggle].push(c)
              break
            }
          }
        }
      }
      if (Object.keys(grouped).length > 0) result[vnum] = grouped
    }
    return result
  }, [chapterConnections, toggles])

  // Wiki mode: render Wikipedia-style layout instead of normal chapter view
  if (wikiMode) {
    return (
      <div className="max-w-6xl mx-auto px-3 py-2">
        <div className="mb-1 flex items-center gap-1.5 text-[10px] text-neutral-400 dark:text-neutral-500 flex-wrap">
          <button onClick={() => {
              const next = false
              setWikiMode(next)
              localStorage.setItem(LS_WIKI_KEY, String(next))
            }}
            className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-700 cursor-pointer transition-colors">
            Simple
          </button>
          <span className="text-neutral-300 dark:text-neutral-600">|</span>
          {companionLabel && <span className="text-neutral-400">{companionLabel}</span>}
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500 text-sm">
            <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Loading chapter…
          </div>
        ) : error ? (
          <div className="mx-4 mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
            {error}
            <button onClick={retry} className="ml-3 underline hover:text-red-800 cursor-pointer">Retry</button>
          </div>
        ) : (
          <WikiLayout data={data} book={book} chapter={chapter} toggles={toggles} chapterConnections={chapterConnections}
            onOpenWiki={(entityId, name) => openWikiTab(entityId, `Wiki: ${name}`)} />
        )}
      </div>
    )
  }

  if (loading) return (
    <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500 text-sm">
      <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
      Loading chapter…
    </div>
  )
  if (error) return (
    <div className="mx-4 mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
      {error}
      <button onClick={retry} className="ml-3 underline hover:text-red-800 cursor-pointer">Retry</button>
    </div>
  )
  if (!data) return null

  const totalVerses = data.verses?.length || 0
  const reviewedCount = data.verses?.filter(v => isReviewed(`${book}.${chapter}.${v.verse}`)).length || 0
  const progressPct = totalVerses > 0 ? Math.round(reviewedCount / totalVerses * 100) : 0

  return (
    <div className="max-w-6xl mx-auto px-3 py-2">
      <div className="mb-1 flex items-center gap-1.5 text-[10px] text-neutral-400 dark:text-neutral-500 flex-wrap">
        {/* Language selector */}
        <div className="flex items-center gap-1">
          <span className="text-neutral-400 dark:text-neutral-500 font-medium">Language:</span>
          <select value={displayLang} onChange={e => setDisplayLang(e.target.value)}
            className="px-1 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 text-[9px] font-mono bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 cursor-pointer">
            <option value="english">English</option>
            <option value="hebrew">Hebrew</option>
            <option value="greek">Greek</option>
          </select>
        </div>
        {displayLang !== 'english' && (
          <>
            <label className="flex items-center gap-1 cursor-pointer select-none hover:text-neutral-600 dark:hover:text-neutral-300">
              <input type="checkbox" checked={showTranslit} onChange={() => setShowTranslit(!showTranslit)}
                className="w-2.5 h-2.5 rounded border-neutral-300 text-blue-600 focus:ring-blue-500 cursor-pointer" />
              <span>Translit</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer select-none hover:text-neutral-600 dark:hover:text-neutral-300">
              <input type="checkbox" checked={showEnglish} onChange={() => setShowEnglish(!showEnglish)}
                className="w-2.5 h-2.5 rounded border-neutral-300 text-blue-600 focus:ring-blue-500 cursor-pointer" />
              <span>English</span>
            </label>
          </>
        )}
        {/* Stats */}
        {footnotes?.length > 0 && <span className="shrink-0">· {footnotes.length} fn</span>}
        {tskRefs?.length > 0 && <span className="shrink-0">· {tskRefs.length} tsk</span>}
        {/* Wiki mode toggle */}
        <button onClick={() => {
            const next = !wikiMode
            setWikiMode(next)
            localStorage.setItem(LS_WIKI_KEY, String(next))
          }}
          className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-mono cursor-pointer transition-colors ${
            wikiMode
              ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-700'
              : 'text-neutral-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 border border-transparent'
          }`}
          title={wikiMode ? 'Switch to Simple view' : 'Switch to Wikipedia-style view'}>
          {wikiMode ? 'Simple' : 'Wiki'}
        </button>
        {/* Split-pane controls */}
        {onCloseCompanion ? (
          <div className="shrink-0 flex items-center gap-1 ml-auto">
            <span className="text-[10px] text-neutral-400 dark:text-neutral-500 font-mono">{companionLabel || 'companion'}</span>
            <button onClick={onCloseCompanion}
              className="px-1.5 py-0.5 rounded text-[10px] text-neutral-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 cursor-pointer transition-colors"
              title="Close split view">✕</button>
          </div>
        ) : (
          <div className="shrink-0 flex items-center gap-1 ml-auto">
            {onSplit && (
              <button onClick={onSplit}
                className="px-1.5 py-0.5 rounded text-[10px] text-neutral-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 cursor-pointer transition-colors"
                title="Split view with another chapter">⊞ Split</button>
            )}
            <span className="text-neutral-300 dark:text-neutral-600">⏎</span>
            <input ref={verseInputRef} type="text" value={verseJump}
              onChange={e => setVerseJump(e.target.value.replace(/[^0-9]/g, ''))}
              onKeyDown={e => {
                if (e.key === 'Enter' && verseJump) { jumpToVerse(parseInt(verseJump)) }
                if (e.key === 'Escape') { setVerseJump(''); verseInputRef.current?.blur() }
              }}
              placeholder="v#"
              className="w-12 px-1.5 py-0.5 rounded border border-neutral-300 dark:border-neutral-600 text-[10px] font-mono bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 placeholder-neutral-400 dark:placeholder-neutral-500" />
          </div>
        )}
      </div>

      {/* Audio player for Hebrew — auto checks if alignment exists */}
      {displayLang === 'hebrew' && data.verses?.[0] && (
        <div className="mb-2">
          <VerseAudioPlayer
            verseId={`${book}.${chapter}.${data.verses[0].verse}`}
            verseTextHebrew={data.verses[0]?.text_hebrew}
            autoPlay={false}
          />
        </div>
      )}

      {data.verses?.map(v => {
        const vs = String(v.verse)
        const verseFns = footnotes?.filter(f => { const vn = f.verse_id?.split('.').pop(); return vn === vs }) || []
        const verseTsk = tskRefs?.filter(r => { const vn = r.source_verse?.split('.').pop(); return vn === vs }) || []
        const verseWords = wordData?.[`${book}.${chapter}.${v.verse}`] || null
        const verseExtra = connectionsByVerse[vs] || null
        const reviewed = isReviewed(`${book}.${chapter}.${v.verse}`)
        return (
          <div key={v.verse} id={`verse-${book}.${chapter}.${v.verse}`} ref={el => verseRefs.current[v.verse] = el} className={highlightVerse === v.verse ? 'scroll-mt-20' : ''}>
            <VerseBlock verse={v} toggles={toggles} poetryMode={poetryMode}
              chiasms={data.chiasms} highlights={[]}
              footnotes={toggles.footnotes ? verseFns : []}
              tskRefs={toggles.tsk ? verseTsk : []}
              wordData={displayLang !== 'english' ? verseWords : (toggles.gematria || toggles.lemma ? verseWords : null)}
              extraConnections={verseExtra}
              reviewed={reviewed}
              onToggleReview={() => toggleReviewed(`${book}.${chapter}.${v.verse}`)}
              displayLang={displayLang} showTranslit={showTranslit} showEnglish={showEnglish}
              hebrewDisplayMode={hebrewDisplayMode}
            />
          </div>
        )
      })}
      {toggles.chiasmus && data.chiasms?.length > 0 && (
        <div className="mt-10 space-y-3">
          <h3 className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider px-1">Chiasmus Structures</h3>
          {data.chiasms.filter(ch => ch.elements?.length > 0 || ch.chapter_section).map(ch => <ChiasmPanel key={ch.chiasm_id} chiasm={ch} />)}
        </div>
      )}
    </div>
  )
}
