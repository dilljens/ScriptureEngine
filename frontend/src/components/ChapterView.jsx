import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useToggles } from './ToggleProvider'
import { useProgress } from '../progress'
import { getFootnotes, getTskCrossrefs, getChapterGrammar, getChapterConnections } from '../api'
import ChiasmPanel from './ChiasmPanel'
import VerseBlock from './VerseBlock'

function useChapterData(book, chapter) {
  const cache = {}
  const [d, sd] = useState(null); const [l, sl] = useState(true); const [e, se] = useState(null)
  useEffect(() => {
    const key = `${book}.${chapter}`
    const c = cache[key]
    if (c) { sd(c); sl(false); se(null); return }
    let cancel = false; let att = 0
    const tf = () => {
      if (cancel) return
      sl(true); se(null)
      fetch(`/api/v1/chapter/${key}`)
        .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
        .then(r => { if (!cancel) { cache[key] = r.data; sd(r.data); sl(false) } })
        .catch(err => { if (cancel) return; att++; if (att < 5) setTimeout(tf, Math.min(1000 * 2 ** att, 8000)); else { se(err.message); sl(false) } })
    }
    tf()
    return () => { cancel = true }
  }, [book, chapter])
  return { data: d, loading: l, error: e }
}

export default function ChapterView({ book, chapter, poetryMode, highlightVerse }) {
  const { toggles, displayLang, showTranslit, showEnglish } = useToggles()
  const { data, loading, error } = useChapterData(book, chapter)
  const [footnotes, setFootnotes] = useState(null)
  const [tskRefs, setTskRefs] = useState(null)
  const [wordData, setWordData] = useState(null)
  const [chapterConnections, setChapterConnections] = useState(null)
  const { isReviewed, toggleReviewed, markReviewed } = useProgress()
  const [verseJump, setVerseJump] = useState('')
  const verseInputRef = useRef(null)

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

  if (loading) return (
    <div className="flex items-center justify-center py-20 text-neutral-400 dark:text-neutral-500 text-sm">
      <svg className="animate-spin h-5 w-5 mr-2" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
      Loading chapter…
    </div>
  )
  if (error) return (
    <div className="mx-4 mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
      {error}
      <button onClick={() => window.location.reload()} className="ml-3 underline hover:text-red-800 cursor-pointer">Retry</button>
    </div>
  )
  if (!data) return null

  const totalVerses = data.verses?.length || 0
  const reviewedCount = data.verses?.filter(v => isReviewed(`${book}.${chapter}.${v.verse}`)).length || 0
  const progressPct = totalVerses > 0 ? Math.round(reviewedCount / totalVerses * 100) : 0

  return (
    <div className="max-w-6xl mx-auto px-6 py-6">
      <div className="mb-3 flex items-center gap-3 text-[10px] text-neutral-400 dark:text-neutral-500">
        <div className="flex-1 h-1.5 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden">
          <div className="h-full rounded-full bg-blue-500 dark:bg-blue-400 transition-all duration-300" style={{ width: `${progressPct}%` }} />
        </div>
        <span className="shrink-0">{reviewedCount}/{totalVerses} verses reviewed</span>
        {footnotes && <span className="shrink-0">· {footnotes.length} fn</span>}
        {tskRefs && <span className="shrink-0">· {tskRefs.length} tsk</span>}
        <div className="shrink-0 flex items-center gap-1 ml-auto">
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
      </div>

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
