import React, { useEffect, useState } from 'react'
import { getCfmLessons, getCfmLesson, getConferenceTalks, getConferenceTalk } from '../api'

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']

const COLORS = {
  cfm: {
    bg: 'bg-amber-50 dark:bg-amber-900/20', border: 'border-amber-200 dark:border-amber-800',
    badge: 'bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-300', icon: '📖',
  },
  conference: {
    bg: 'bg-sky-50 dark:bg-sky-900/20', border: 'border-sky-200 dark:border-sky-800',
    badge: 'bg-sky-100 dark:bg-sky-800 text-sky-700 dark:text-sky-300', icon: '🎤',
  },
}

const COLLECTION_META = {
  cfm: { label: 'Come Follow Me', sub: 'Weekly lessons · Old Testament 2026', scope: 'cfm' },
  conference: { label: 'General Conference', sub: 'Talks · 2021–2026', scope: 'conference' },
}

function monthFromDate(iso) {
  if (!iso) return ''
  const m = parseInt(String(iso).slice(5, 7), 10)
  return Number.isFinite(m) && m >= 1 && m <= 12 ? MONTHS[m - 1] : ''
}

function conferenceLabel(year, month) {
  return `${MONTHS[month - 1]} ${year}`
}

export default function CollectionView({ collection, onBack, onStudyInChat }) {
  const meta = COLLECTION_META[collection] || COLLECTION_META.cfm
  const colors = COLORS[collection] || COLORS.cfm
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(null) // ref_id of expanded item
  const [detail, setDetail] = useState(null)     // full text of expanded item
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setItems(null); setError(''); setExpanded(null); setDetail(null)
    const load = collection === 'cfm' ? getCfmLessons : getConferenceTalks
    load()
      .then(r => { if (!cancelled && r.data) setItems(r.data.lessons || r.data.talks || []) })
      .catch(e => { if (!cancelled) setError('Could not load collection.') })
    return () => { cancelled = true }
  }, [collection])

  const toggle = async (refId) => {
    if (expanded === refId) { setExpanded(null); setDetail(null); return }
    setExpanded(refId); setDetail(null); setDetailLoading(true)
    try {
      const load = collection === 'cfm' ? getCfmLesson : getConferenceTalk
      const r = await load(refId)
      setDetail(r.data?.text || '')
    } catch {
      setDetail('')
    } finally {
      setDetailLoading(false)
    }
  }

  const studyInChat = (refId, label) => {
    const scopeHint = meta.scope
    const msg = collection === 'cfm'
      ? `Study the Come Follow Me lesson "${label}" with me. Start with what the lesson text says, then connect it to the actual scripture it points to.`
      : `Study the General Conference talk "${label}" with me. Start with what the talk says, then connect it to the actual scripture it cites.`
    onStudyInChat?.(msg, scopeHint)
  }

  // Group CFM by month, GC by year+month then session
  const groups = []
  if (items) {
    if (collection === 'cfm') {
      const byMonth = {}
      for (const it of items) {
        const m = monthFromDate(it.start_date)
        ;(byMonth[m] = byMonth[m] || []).push(it)
      }
      for (const m of MONTHS) {
        if (byMonth[m]) groups.push({ key: m, title: m, entries: byMonth[m] })
      }
    } else {
      const byConf = {}
      for (const it of items) {
        const k = conferenceLabel(it.year, it.month)
        ;(byConf[k] = byConf[k] || { year: it.year, month: it.month, sessions: {} })[k]
        ;(byConf[k].sessions[it.session] = byConf[k].sessions[it.session] || []).push(it)
      }
      for (const k of Object.keys(byConf).sort().reverse()) {
        const c = byConf[k]
        const sessionGroups = Object.entries(c.sessions).map(([s, talks]) => ({ session: s, talks }))
        groups.push({ key: k, title: k, conferences: sessionGroups, isConf: true })
      }
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={onBack}
          className="px-3 py-1.5 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors cursor-pointer">
          ← Library
        </button>
        <span className={`text-2xl ${colors.icon}`} />
        <div>
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{meta.label}</h2>
          <p className="text-xs text-neutral-500 dark:text-neutral-400">{meta.sub}</p>
        </div>
      </div>

      {error && <div className="text-sm text-rose-500 py-8 text-center">{error}</div>}
      {!items && !error && (
        <div className="text-center py-12">
          <div className="animate-spin h-6 w-6 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">Loading…</p>
        </div>
      )}
      {items && items.length === 0 && (
        <div className="text-center py-12 text-sm text-neutral-500 dark:text-neutral-400">
          Nothing here yet — run the importer to load this collection.
        </div>
      )}

      {groups.map(g => (
        <div key={g.key} className="mb-8">
          <h3 className="text-xs font-semibold text-neutral-400 dark:text-neutral-500 uppercase tracking-wider mb-2">{g.title}</h3>
          {g.isConf
            ? g.conferences.map(sg => (
                <div key={sg.session} className="mb-3">
                  <div className="text-[11px] font-medium text-neutral-400 dark:text-neutral-500 mb-1">{sg.session}</div>
                  {sg.talks.map(t => <Row key={t.ref_id} item={t} collection={collection} colors={colors} expanded={expanded} detail={detail} detailLoading={detailLoading} toggle={toggle} studyInChat={studyInChat} />)}
                </div>
              ))
            : g.entries.map(it => <Row key={it.ref_id} item={it} collection={collection} colors={colors} expanded={expanded} detail={detail} detailLoading={detailLoading} toggle={toggle} studyInChat={studyInChat} />)}
        </div>
      ))}
    </div>
  )
}

function Row({ item, collection, colors, expanded, detail, detailLoading, toggle, studyInChat }) {
  const isOpen = expanded === item.ref_id
  const title = collection === 'cfm' ? item.title : `${item.speaker} — ${item.title}`
  const sub = collection === 'cfm'
    ? `${item.date_range} · ${item.scripture_block}`
    : item.session

  return (
    <div className={`rounded-lg border mb-2 overflow-hidden transition-colors ${isOpen ? `${colors.bg} ${colors.border}` : 'border-neutral-200 dark:border-neutral-700 hover:border-neutral-300 dark:hover:border-neutral-600'}`}>
      <button onClick={() => toggle(item.ref_id)} className="w-full text-left px-4 py-2.5 flex items-start gap-3 cursor-pointer hover:bg-black/[0.02] dark:hover:bg-white/[0.03]">
        <div className="flex-1 min-w-0">
          <div className="text-sm text-neutral-800 dark:text-neutral-200 line-clamp-1">{title}</div>
          <div className="text-[11px] text-neutral-500 dark:text-neutral-400 mt-0.5">{sub}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); studyInChat(item.ref_id, collection === 'cfm' ? item.title : item.title) }}
            className="px-2 py-1 rounded-md text-[10px] font-medium bg-indigo-500 hover:bg-indigo-600 text-white transition-colors cursor-pointer">
            Study in chat
          </button>
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${colors.badge}`}>{isOpen ? '▲' : '▼'}</span>
        </div>
      </button>
      {isOpen && (
        <div className="px-4 pb-4 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
          {detailLoading ? (
            <div className="animate-pulse text-neutral-400 py-4">Loading text…</div>
          ) : detail ? (
            detail
          ) : (
            <div className="text-neutral-400 py-4">No text available.</div>
          )}
        </div>
      )}
    </div>
  )
}
