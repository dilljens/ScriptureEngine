import React, { useEffect, useMemo, useState } from 'react'
import { reportIdleAnswer } from './HebrewIdleBar'
import { currentSessionToken, hebrewSessionUser } from '../api'
import {
  WORD_MATURE_INTERVAL_DAYS,
  ROOT_MATURE_REPS,
  ROOTS_TILES_GATE,
  isWordMastered,
  wordDeckUnlocked,
  LETTERS,
  loadIdleState,
  saveIdleState,
  syncMasteredWords,
  recordRootStudy,
} from '../lib/idle-game'

/**
 * WordTilesView — 50 tiles at once, Anki-style. Two kinds:
 *
 * words: top-500 vocabulary with FSRS status (mastered = interval 21+d,
 *   Anki "mature"). Mastered words pay +2% Ohr/sec to each contained letter.
 *   Decks 3+ / 6+ gate on 10 / 40 mastered words (staged progression).
 *
 * roots: top-500 roots with example words. Roots mature by study reps
 *   (3 net knows — honest self-grading, since per-root FSRS covers only
 *   17/500 roots). Mature roots lift the word income term +5% each
 *   (word↔root synergy). Unlocks at 25 mastered words.
 */

const RATINGS = [
  { value: 1, label: 'Again', cls: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200' },
  { value: 2, label: 'Hard', cls: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 hover:bg-amber-200' },
  { value: 3, label: 'Good', cls: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200' },
  { value: 4, label: 'Easy', cls: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200' },
]

function tileStyle(word) {
  if (isWordMastered(word)) return 'bg-yellow-100 dark:bg-yellow-900/30 border-yellow-400 dark:border-yellow-600'
  const iv = word.interval_days || 0
  if (iv > 0) return 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'
  if ((word.mastery || 0) > 0) return 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700'
  return 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
}

function rootTileStyle(t) {
  if (t.mature) return 'bg-yellow-100 dark:bg-yellow-900/30 border-yellow-400 dark:border-yellow-600'
  if (t.known) return 'bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700'
  return 'bg-white dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700'
}

function statusLine(word) {
  if (isWordMastered(word)) return `✓ ${word.interval_days}d — mastered`
  if ((word.interval_days || 0) > 0) {
    const due = word.due_in_days
    if (typeof due === 'number' && due > 0) return `due in ${due}d · int ${word.interval_days}d`
    if (typeof due === 'number') return `due now · int ${word.interval_days}d`
    return `int ${word.interval_days}d`
  }
  if ((word.mastery || 0) > 0) return 'learning…'
  return 'new'
}

function rootStatusLine(t) {
  if (t.mature) return `✓ mature (${t.reps} net)`
  if (t.known) return `${t.hits} examples known`
  return 'new'
}

const FINAL_TO_BASE = { 'ך': 11, 'ם': 12, 'ן': 13, 'ף': 16, 'ץ': 17 }
function bareReadable(bare, owned) {
  for (const ch of bare || '') {
    let idx = LETTERS.indexOf(ch)
    if (idx < 0 && FINAL_TO_BASE[ch] !== undefined) idx = FINAL_TO_BASE[ch]
    if (idx < 0) continue
    if (!(owned[idx] > 0)) return false
  }
  return true
}

export default function WordTilesView({ initialWords = [], kind = 'words', onClose }) {
  const isRoots = kind === 'roots'
  const [words, setWords] = useState(isRoots ? [] : initialWords)
  const [roots, setRoots] = useState([])
  const [topLite, setTopLite] = useState([]) // top-500 bare/lemma/rank for root examples
  const [loading, setLoading] = useState(true)
  const [locked, setLocked] = useState(false)
  const [selected, setSelected] = useState(null) // rank key
  const [revealed, setRevealed] = useState(false)
  const [grading, setGrading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(isRoots ? 500 : (initialWords.length >= 50 ? 500 : initialWords.length))
  const [auxTick, setAuxTick] = useState(0) // refresh root reps/readability
  // Mastered words across ALL visited decks (rank -> {bare, rank}) so the
  // per-letter Ohr bonus never shrinks when paging. Union, never replace.
  const [masteredUnion, setMasteredUnion] = useState(() => {
    const m = {}
    for (const w of initialWords) if (isWordMastered(w) && w.bare) m[w.rank ?? w.hebrew] = { bare: w.bare, rank: w.rank }
    return m
  })
  const DECK = 50
  const deckCount = Math.max(1, Math.ceil(total / DECK))
  const deckIdx = Math.floor(offset / DECK)
  const masteredTotal = Object.keys(masteredUnion).length

  const syncUnion = (next) => {
    setMasteredUnion(prev => {
      const m = { ...prev }
      for (const w of next) {
        const k = w.rank ?? w.hebrew
        if (isWordMastered(w) && w.bare) m[k] = { bare: w.bare, rank: w.rank }
        else if (k in m && !isWordMastered(w)) delete m[k]
      }
      try {
        const s = loadIdleState()
        syncMasteredWords(s, Object.values(m))
        saveIdleState(s)
      } catch {}
      return m
    })
  }

  const authHeaders = () => {
    const token = currentSessionToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }
  const userSuffix = async () => {
    const uid = await hebrewSessionUser().catch(() => '')
    return uid && uid !== 'default' ? `&user_id=${encodeURIComponent(uid)}` : ''
  }

  const loadDeck = async (off) => {
    setLoading(true)
    try {
      const q = await userSuffix()
      const r = await fetch(`/api/v1/hebrew/top-words?limit=${DECK}&offset=${off}&with_status=1${q}`, {
        headers: authHeaders(),
      })
      const d = await r.json()
      if (d.ok) {
        setWords(d.data.words || [])
        setTotal(d.data.total || 0)
        syncUnion(d.data.words || [])
      }
    } catch {}
    setLoading(false)
  }

  const loadRoots = async (off) => {
    setLoading(true)
    try {
      // Gate: roots study unlocks at 25 mastered words (staged progression).
      let idle = null
      try { idle = loadIdleState() } catch {}
      if ((idle?.masteredWords?.length || 0) < ROOTS_TILES_GATE) {
        setLocked(true)
        setLoading(false)
        return
      }
      const [rr, tw] = await Promise.all([
        fetch(`/api/v1/hebrew/top-roots?limit=${DECK}&offset=${off}`, { headers: authHeaders() }).then(r => r.json()),
        topLite.length ? null : fetch('/api/v1/hebrew/top-words?limit=500', { headers: authHeaders() }).then(r => r.json()),
      ])
      if (tw?.ok) setTopLite(tw.data.words || [])
      if (rr?.ok) {
        setRoots(rr.data.roots || [])
        setTotal(rr.data.total || 0)
      }
      setAuxTick(t => t + 1)
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    if (isRoots) { loadRoots(0); return }
    if (initialWords.length) { syncUnion(initialWords); setLoading(false); return }
    loadDeck(0)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const goDeck = (off) => {
    const target = Math.floor(off / DECK)
    if (!isRoots && !wordDeckUnlocked(target, masteredTotal)) return
    setOffset(off)
    setSelected(null)
    setRevealed(false)
    if (isRoots) loadRoots(off)
    else loadDeck(off)
  }

  // Roots auxiliary: owned letters + mastered ranks + root reps → per-root status.
  const aux = useMemo(() => {
    // eslint-disable-next-line no-unused-vars
    void auxTick
    let owned = {}, reps = {}
    try {
      const s = loadIdleState()
      owned = s.owned || {}
      reps = s.rootReps || {}
    } catch {}
    const lite = topLite.length ? topLite : []
    const lemmaToRank = {}
    const rankToBare = {}
    for (const w of lite) {
      if (w.lemma != null) lemmaToRank[w.lemma] = w.rank
      rankToBare[w.rank] = w.bare
    }
    const masteredRanks = new Set(Object.values(masteredUnion).map(w => w.rank))
    return { owned, reps, lemmaToRank, rankToBare, masteredRanks }
  }, [topLite, masteredUnion, auxTick])

  const rootTiles = useMemo(() => {
    if (!isRoots) return []
    return roots.map(r => {
      const examples = (r.examples || []).slice(0, 6)
      let hits = 0
      for (const lemma of (r.examples || [])) {
        const rank = aux.lemmaToRank[lemma]
        if (rank == null) continue
        if (aux.masteredRanks.has(rank)) { hits++; continue }
        const bare = aux.rankToBare[rank]
        if (bare && bareReadable(bare, aux.owned)) hits++
      }
      const rep = aux.reps[r.root] || { k: 0, s: 0 }
      const net = rep.k - rep.s
      return {
        key: `root-${r.rank}`,
        hebrew: r.root,
        gloss: r.gloss,
        examples,
        hits,
        reps: net,
        known: hits >= 2,
        mature: net >= ROOT_MATURE_REPS,
      }
    })
  }, [isRoots, roots, aux])

  const stats = useMemo(() => {
    if (isRoots) {
      const mature = rootTiles.filter(t => t.mature).length
      const known = rootTiles.filter(t => !t.mature && t.known).length
      return { mature, known, total: rootTiles.length }
    }
    const mastered = words.filter(isWordMastered).length
    const due = words.filter(w => !isWordMastered(w) && typeof w.due_in_days === 'number' && w.due_in_days <= 0 && (w.interval_days || 0) > 0).length
    return { mastered, total: words.length, due }
  }, [isRoots, words, rootTiles])

  // Due-first order (Anki review-queue rule): overdue first, then new,
  // then waiting-for-review, mastered last and dimmed.
  const ordered = useMemo(() => {
    const rank = (w) => {
      if (isWordMastered(w)) return 3
      if ((w.interval_days || 0) > 0 && typeof w.due_in_days === 'number' && w.due_in_days <= 0) return 0
      if ((w.interval_days || 0) === 0 && (w.mastery || 0) === 0) return 1
      return 2
    }
    return [...words].sort((a, b) => rank(a) - rank(b) || (a.due_in_days ?? 0) - (b.due_in_days ?? 0))
  }, [words])

  const orderedRoots = useMemo(() => {
    const rank = (t) => (t.mature ? 2 : t.known ? 1 : 0)
    return [...rootTiles].sort((a, b) => rank(a) - rank(b))
  }, [rootTiles])

  const sel = selected != null
    ? (isRoots ? rootTiles.find(t => t.key === selected) : words.find(w => (w.rank ?? w.hebrew) === selected))
    : null

  const grade = async (word, rating) => {
    if (!word || grading) return
    setGrading(true)
    const t0 = Date.now()
    let data = null
    try {
      const token = currentSessionToken()
      const headers = { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }
      const body = word.node_id
        ? { node_id: word.node_id, rating, session_token: token || undefined }
        : { hebrew: word.hebrew, rating, session_token: token || undefined }
      let r = await fetch('/api/v1/hebrew/fsrs/review', { method: 'POST', headers, body: JSON.stringify(body) })
      let d = await r.json().catch(() => ({}))
      if ((!d.ok || !d.data) && !word.node_id && word.hebrew) {
        // No vocab node yet for this top-500 word — create one, then grade.
        try {
          const uid = await hebrewSessionUser().catch(() => 'default')
          await fetch(`/api/v1/hebrew/add-word?word=${encodeURIComponent(word.hebrew)}&user_id=${encodeURIComponent(uid || 'default')}`, {
            method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {},
          })
          r = await fetch('/api/v1/hebrew/fsrs/review', { method: 'POST', headers, body: JSON.stringify(body) })
          d = await r.json().catch(() => ({}))
        } catch {}
      }
      data = d.data || null
    } catch {}
    // FSRS pass threshold is rating >= 2 (backend correct-count) — that is
    // what earns Ohr/Kavod here, same as every other review surface.
    reportIdleAnswer(rating >= 2, Date.now() - t0, { source: 'word-tiles', hebrew: word.hebrew })
    setWords(prev => {
      const next = prev.map(w => {
        if ((w.rank ?? w.hebrew) !== (word.rank ?? word.hebrew)) return w
        if (!data) return w
        const interval_days = data.interval ?? w.interval_days ?? 0
        return {
          ...w,
          node_id: data.node_id || w.node_id,
          mastery: data.mastery ?? w.mastery,
          interval_days,
          due: data.due || w.due,
          mastered: interval_days >= WORD_MATURE_INTERVAL_DAYS,
        }
      })
      syncUnion(next)
      return next
    })
    setRevealed(false)
    setSelected(null)
    setGrading(false)
  }

  const gradeRoot = async (tile, known) => {
    if (!tile || grading) return
    setGrading(true)
    const t0 = Date.now()
    try {
      const s = loadIdleState()
      recordRootStudy(s, tile.hebrew, known)
      saveIdleState(s)
    } catch {}
    reportIdleAnswer(known, Date.now() - t0, { source: 'root-tiles', hebrew: tile.hebrew })
    setAuxTick(t => t + 1)
    setRevealed(false)
    setSelected(null)
    setGrading(false)
  }

  if (loading) {
    return (
      <div className="max-w-lg mx-auto px-6 py-12 text-center">
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-4">Loading 50 {isRoots ? 'root' : 'word'} tiles…</p>
        <button onClick={onClose}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
          ← Back to Curriculum
        </button>
      </div>
    )
  }

  if (locked) {
    return (
      <div className="max-w-lg mx-auto px-6 py-12 text-center">
        <p className="text-2xl mb-2">🌱</p>
        <p className="text-sm text-neutral-600 dark:text-neutral-300 mb-1 font-medium">Roots unlock at {ROOTS_TILES_GATE} mastered words</p>
        <p className="text-xs text-neutral-500 dark:text-neutral-400 mb-4">Master words first — roots grow out of vocabulary you own. Check Word Tiles for your count.</p>
        <button onClick={onClose}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
          ← Back to Curriculum
        </button>
      </div>
    )
  }

  const nextLocked = !isRoots && !wordDeckUnlocked(deckIdx + 1, masteredTotal)

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-200">{isRoots ? '🌱 Root Tiles' : '🔠 Word Tiles'}</h2>
        <button onClick={onClose}
          className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer">
          ← Back to Curriculum
        </button>
      </div>
      {isRoots ? (
        <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mb-3">
          Deck {deckIdx + 1}/{deckCount} · {stats.mature}/{stats.total} mature here · {stats.known} readable · Mature = {ROOT_MATURE_REPS} net knows.
          Mature roots give +5% word income each (word↔root synergy).
        </p>
      ) : (
        <p className="text-[11px] text-neutral-500 dark:text-neutral-400 mb-3">
          Deck {deckIdx + 1}/{deckCount} · {stats.mastered}/{stats.total} mastered here · {masteredTotal} mastered total · {stats.due} due · Mastered = next review {WORD_MATURE_INTERVAL_DAYS}+ days out (Anki “mature”).
          Mastered words give +2% Ohr/sec to each letter they contain.
        </p>
      )}
      <div className="flex items-center gap-2 mb-3">
        <button disabled={offset === 0 || loading} onClick={() => goDeck(Math.max(0, offset - DECK))}
          className="px-3 py-1.5 rounded-lg text-xs font-medium border border-neutral-300 dark:border-neutral-600 cursor-pointer disabled:opacity-40">
          ← Prev deck
        </button>
        <span className="text-[11px] text-neutral-500 dark:text-neutral-400 tabular-nums">{isRoots ? 'roots' : 'words'} {offset + 1}–{Math.min(offset + DECK, total)} of {total}</span>
        <button disabled={offset + DECK >= total || loading || nextLocked} onClick={() => goDeck(offset + DECK)}
          title={nextLocked ? `Deck ${deckIdx + 2} needs ${deckIdx + 1 >= 6 ? 40 : 10} mastered words` : undefined}
          className="px-3 py-1.5 rounded-lg text-xs font-medium border border-neutral-300 dark:border-neutral-600 cursor-pointer disabled:opacity-40">
          {nextLocked ? `🔒 Next deck` : 'Next deck →'}
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2 mb-4">
        {(isRoots ? orderedRoots : ordered).map(w => {
          const key = isRoots ? w.key : (w.rank ?? w.hebrew)
          const active = selected === key
          return (
            <button key={key} onClick={() => { setSelected(key); setRevealed(false) }}
              className={`p-2.5 rounded-xl border-2 text-center transition-all cursor-pointer hover:ring-2 hover:ring-indigo-400 ${(isRoots ? rootTileStyle(w) : tileStyle(w))} ${active ? 'ring-2 ring-indigo-500' : ''}`}>
              <div className="text-xl font-serif leading-snug" dir="rtl">{w.hebrew}</div>
              <div className="text-[10px] text-neutral-500 dark:text-neutral-400 truncate mt-0.5">{w.gloss || '—'}</div>
              <div className="text-[9px] text-neutral-400 dark:text-neutral-500 mt-0.5">{isRoots ? rootStatusLine(w) : statusLine(w)}</div>
            </button>
          )
        })}
      </div>

      {sel && !isRoots && (
        <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <div className="text-center mb-3">
            <div className="text-3xl font-serif" dir="rtl">{sel.hebrew}</div>
            {sel.transliteration && <div className="text-xs text-neutral-400 mt-1">{sel.transliteration}</div>}
            {revealed
              ? <div className="text-sm text-neutral-700 dark:text-neutral-300 mt-2">{sel.gloss || '—'}</div>
              : <button onClick={() => setRevealed(true)}
                  className="mt-2 px-4 py-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-xs font-medium cursor-pointer">
                  Reveal meaning
                </button>}
          </div>
          {revealed && (
            <div className="flex gap-2 justify-center">
              {RATINGS.map(r => (
                <button key={r.value} disabled={grading} onClick={() => grade(sel, r.value)}
                  className={`px-4 py-2 rounded-lg text-xs font-medium cursor-pointer transition-colors disabled:opacity-50 ${r.cls}`}>
                  {r.label}
                </button>
              ))}
            </div>
          )}
          <p className="text-center text-[10px] text-neutral-400 mt-2">
            Again = forgot · Hard/Good/Easy schedule the next review like Anki (1 → days → weeks).
          </p>
        </div>
      )}

      {sel && isRoots && (
        <div className="p-4 rounded-xl bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
          <div className="text-center mb-3">
            <div className="text-3xl font-serif" dir="rtl">{sel.hebrew}</div>
            {revealed ? (
              <>
                <div className="text-sm text-neutral-700 dark:text-neutral-300 mt-2">{sel.gloss || '—'}</div>
                <div className="flex flex-wrap gap-1.5 justify-center mt-2">
                  {(sel.examples || []).map(ex => (
                    <span key={ex} className="px-2 py-0.5 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-[11px] font-serif" dir="rtl">{ex}</span>
                  ))}
                </div>
              </>
            ) : (
              <button onClick={() => setRevealed(true)}
                className="mt-2 px-4 py-1.5 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-xs font-medium cursor-pointer">
                Reveal meaning + examples
              </button>
            )}
          </div>
          {revealed && (
            <div className="flex gap-2 justify-center">
              <button disabled={grading} onClick={() => gradeRoot(sel, false)}
                className="px-4 py-2 rounded-lg text-xs font-medium cursor-pointer transition-colors disabled:opacity-50 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
                Still learning
              </button>
              <button disabled={grading} onClick={() => gradeRoot(sel, true)}
                className="px-4 py-2 rounded-lg text-xs font-medium cursor-pointer transition-colors disabled:opacity-50 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
                I know it ✓
              </button>
            </div>
          )}
          <p className="text-center text-[10px] text-neutral-400 mt-2">
            {ROOT_MATURE_REPS} net knows mature a root (+5% word income each). Honest grading — reps never schedule FSRS.
          </p>
        </div>
      )}
    </div>
  )
}
