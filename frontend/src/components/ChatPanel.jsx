/**
 * LLM Chat Panel — triggered by Ctrl+P.
 *
 * Auto-saves every message to the server for persistence and review.
 * Uses react-markdown for content rendering with clickable VerseChips.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import QuizCard from './QuizCard'
import HebrewQuizCard from './HebrewQuizCard'
import VersePopup from './VersePopup'
import VersePreviewCard from './VersePreviewCard'
import { useToggles } from './ToggleProvider'
import { conversationCreate, conversationAddMessage, conversationGet, conversationList, chat } from '../api'
import { preprocess as preprocessScripture, createComponents } from '../lib/scripture-markdown'
import { parseStandardRef, resolveBook } from '../refParser'

// ── Verse ref detection ──

const VERSE_REF_RE = /([a-z0-9_]+)\.(\d+)\.(\d+)/gi

// Map full book names to their IDs — matches the LLM's 📖 output format
const BOOK_NAME_MAP = {
  // Apocrypha
  tobit: 'tob', judith: 'jdt',
  wisdom: 'wis', 'wisdom of solomon': 'wis', sirach: 'sir',
  'ecclesiasticus': 'sir', baruch: 'bar', 'prayer of manasses': 'man',
  '1 maccabees': '1ma', '2 maccabees': '2ma',
  '1 esdras': '1esd', '2 esdras': '2esd',
  'additions to esther': 'esga', 'song of three': 's3y',
  susanna: 'sus', 'bel and the dragon': 'bel', 'psalm 151': 'psa151',

  genesis: 'gen', exodus: 'exo', leviticus: 'lev', numbers: 'num', deuteronomy: 'deu',
  joshua: 'josh', judges: 'judg', ruth: 'ruth',
  '1 samuel': '1sam', '2 samuel': '2sam', '1 kings': '1kgs', '2 kings': '2kgs',
  '1 chronicles': '1chr', '2 chronicles': '2chr', ezra: 'ezra', nehemiah: 'neh',
  esther: 'esth', job: 'job', psalm: 'psa', psalms: 'psa', proverbs: 'prov',
  ecclesiastes: 'eccl', 'song of solomon': 'song', isaiah: 'isa', jeremiah: 'jer',
  lamentations: 'lam', ezekiel: 'ezek', daniel: 'dan', hosea: 'hos', joel: 'joel',
  amos: 'amos', obadiah: 'obad', jonah: 'jonah', micah: 'mic', nahum: 'nah',
  habakkuk: 'hab', zephaniah: 'zeph', haggai: 'hag', zechariah: 'zech', malachi: 'mal',
  matthew: 'matt', mark: 'mark', luke: 'luke', john: 'john', acts: 'acts',
  romans: 'rom', '1 corinthians': '1cor', '2 corinthians': '2cor', galatians: 'gal',
  ephesians: 'eph', philippians: 'phil', colossians: 'col',
  '1 thessalonians': '1thes', '2 thessalonians': '2thes',
  '1 timothy': '1tim', '2 timothy': '2tim', titus: 'titus', philemon: 'philem',
  hebrews: 'heb', james: 'james', '1 peter': '1pet', '2 peter': '2pet',
  '1 john': '1john', '2 john': '2john', '3 john': '3john', jude: 'jude',
  revelation: 'rev',
  '1 nephi': '1ne', '2 nephi': '2ne', jacob: 'jacob', enos: 'enos',
  jarom: 'jarom', omni: 'omni', 'words of mormon': 'wom', mosiah: 'mosiah',
  alma: 'alma', helaman: 'hel', '3 nephi': '3ne', '4 nephi': '4ne',
  mormon: 'morm', ether: 'ether', moroni: 'moro',
  moses: 'moses', abraham: 'abraham', 'joseph smith—matthew': 'jsm',
  'joseph smith—history': 'jsh', 'articles of faith': 'aoff',
  'doctrine and covenants': 'dc',
  // Common abbreviations the LLM might use
  ezr: 'ezra', est: 'esth', eccl: 'eccl',
  jon: 'jonah',
  mrk: 'mark', lk: 'luke', jn: 'john',
  '1 cor': '1cor', '2 cor': '2cor',
  '1 thes': '1thes', '2 thes': '2thes', '1 tim': '1tim', '2 tim': '2tim',
  tit: 'titus', heb: 'heb', jam: 'james',
  '1 pet': '1pet', '2 pet': '2pet', '1 jn': '1john', '2 jn': '2john', '3 jn': '3john',
  rev: 'rev',
  '1 ne': '1ne', '2 ne': '2ne', wom: 'wom',
  hel: 'hel', '3 ne': '3ne', '4 ne': '4ne',
  abr: 'abraham', 'd&c': 'dc', dc: 'dc',
  // Additional standard abbreviations used by the LLM
  exod: 'exo', deut: 'deu',
  '1 sam': '1sam', '2 sam': '2sam', '1 kgs': '1kgs', '2 kgs': '2kgs',
  '1 chr': '1chr', '2 chr': '2chr',
  ps: 'psa',
  mt: 'matt', mk: 'mark',
  jas: 'james',
  'joseph smith-matthew': 'jsm', 'joseph smith-history': 'jsh',
  // DSS
  'community rule': '1QS', 'serek hayahad': '1QS', 'serek': '1QS',
  'war scroll': '1QM', 'milhamah': '1QM',
  'hodayot': '1QHa', 'thanksgiving hymns': '1QHa', 'thanksgiving scroll': '1QHa',
  'pesher habakkuk': '1QpHab',
  'melchizedek scroll': '11Q13', '11q13': '11Q13',
  'temple scroll': '11Q19', '11q19': '11Q19',
  'damascus document': 'CD', 'cd': 'CD',
  'songs of sabbath sacrifice': '4Q400', 'sabbath sacrifice': '4Q400',
  'genesis apocryphon': '1Q20',
  'book of giants': 'bookgiants',
  // Pseudepigrapha
  '1 enoch': '1en', 'ethiopic enoch': '1en',
  '2 enoch': '2en', 'slavonic enoch': '2en',
  'jubilees': 'jub', 'book of jubilees': 'jub',
  'ascension of isaiah': 'ascis',
  'assumption of moses': 'asmos',
  'testament of abraham': 'tabr',
  'testament of job': 'tjob',
  'testament of solomon': 'tsol',
  'life of adam and eve': '1adae',
  'apocalypse of abraham': 'apabr',
  'apocalypse of elijah': 'apelj',
  'apocryphon of joshua': 'apjosh',
  'psalms of solomon': 'psssol',
  'odes of solomon': 'odessol',
  'joseph and asenath': 'josasen',
  'book of jasher': 'jasher', 'jasher': 'jasher',
  'ladder of jacob': 'ladjac',
  'prayer of azariah': 'azar',
  // Expanded Canon
  'shepherd of hermas': '1her', 'hermas': '1her',
  'apocalypse of peter': 'apet',
  'epistle of barnabas': 'barn', 'barnabas': 'barn',
  'gospel of nicodemus': 'gnic', 'nicodemus': 'gnic',
}

function resolveBookName(name) {
  const key = name.trim().toLowerCase().replace(/[—–]/g, '—')
  if (BOOK_NAME_MAP[key]) return BOOK_NAME_MAP[key]
  const firstWord = key.split(/\s/)[0]
  if (BOOK_NAME_MAP[firstWord]) return BOOK_NAME_MAP[firstWord]
  return null
}

/** Pre-process markdown to detect verse references in 📖 format + gen.1.1 */
function preprocessVerses(markdown) {
  if (!markdown) return ''
  let result = markdown

  // Strip Bible version annotations like (WEB), (KJV) so they don't interfere with ref matching
  result = result.replace(/\(WEB\)|\(KJV\)|\(LEB\)|\(BSB\)|\(YLT\)/gi, '')

  // Match criteria: must be a known book name from BOOK_NAME_MAP
  function tryReplaceBookRef(match, bookName, chapter, verseStr) {
    const bookId = resolveBookName(bookName)
    if (!bookId) return match // not a known book, leave as-is
    const firstVerse = verseStr ? verseStr.split(/[-,]/)[0] : '1'
    return `:verse[${bookId}.${chapter}.${firstVerse}]`
  }

  // 1. Match "Book Name ch:vs" or "Book Name ch.vs" with optional leading ** or 📖
  // Handles: Genesis 1:1, Isaiah 2:3-4, **📖 Genesis 1:1**, 📖Genesis 1.1, etc.
  // Also matches number-prefixed books: "1 Nephi 3:7", "2 Corinthians 5:17"
  result = result.replace(
    /\*{0,2}📖?\s*(?:(?:[1-5]\s+)?[A-Za-z][A-Za-z\s—–&-]+?)\s*(\d+)(?:([:.])(\d+(?:\s*[-,]\s*\d+)*))?\*{0,2}/g,
    (match, chapter, _sep, verseStr) => {
      // Extract the book name: strip leading ** and 📖, take everything before the chapter number
      let clean = match.replace(/^\*{0,2}📖?\s*/, '').replace(/\s*\d+(?:[:.]\d+(?:\s*[-,]\s*\d+)*)?\*{0,2}$/, '').trim()
      // Strip leading >, blockquote markers, and noise words like "See", "cf.", "in"
      clean = clean.replace(/^[>|]+\s*/i, '')
      clean = clean.replace(/^(?:see|cf\.?|in|of|as|like|read|from)\s+/i, '')
      // Strip trailing punctuation that might stick to book name: .,;:!?()[]"'—
      clean = clean.replace(/[.,;:!?()\[\]""'—–-]+$/g, '').trim()
      const bookId = resolveBookName(clean)
      if (!bookId) return match
      // Keep verse ranges intact (e.g. "1-12" stays as "1-12"), but strip comma lists. Normalize spaces around dashes.
      const versePart = verseStr ? verseStr.replace(/,.*$/, '').replace(/\s*-\s*/g, '-').trim() : '1'
      return `:verse[${bookId}.${chapter}.${versePart}]`
    }
  )

  // 2. Replace gen.1.1 or gen:1:1 format (book.chapter.verse)
  // Also captures ranges like gen.1.1-12 or exo.25.18-22
  result = result.replace(
    /:verse\[[^\]]+\]|([a-z0-9_]+)[.:](\d+)[.:](\d+)(?:[-,](\d+))?/gi,
    (match, book, ch, vs, vsEnd) => {
      if (book) {
        const versePart = vsEnd ? `${vs}-${vsEnd}` : vs
        return `:verse[${book.toLowerCase()}.${ch}.${versePart}]`
      }
      return match // already a marker
    }
  )

  // 3. Replace book.chapter format (gen.3, isa.55) — 2-part refs (skip existing markers)
  // Must have at least one letter to be a valid book ID (avoids matching "26.1" or "1.2")
  result = result.replace(
    /:verse\[[^\]]+\]|([a-z0-9_]*[a-z][a-z0-9_]*)\.(\d+)\b(?!\.\d+)/gi,
    (match, book, ch) => {
      if (book) return `:verse[${book.toLowerCase()}.${ch}.1]`
      return match // already a marker
    }
  )

  // Post-process: convert D&C refs from "dc.N.V" to "dcN.N.V"
  // D&C uses section numbers as book IDs, e.g. dc76.76.22 not dc.76.22
  result = result.replace(
    /:verse\[dc\.(\d+)\.(\d+(?:-\d+)?)\]/g,
    (match, ch, vs) => `:verse[dc${ch}.${ch}.${vs}]`
  )

  return result
}

/** Check if a line looks like a standalone verse reference (not inside a code block or heading) */
function isStandaloneVerse(line) {
  return VERSE_REF_RE.test(line)
}


// ── System Prompt ──

const SYSTEM_PROMPT = `You are a scripture study assistant for the Scripture Engine — a comprehensive digital library spanning 9 works: Old Testament, New Testament, Book of Mormon, Doctrine & Covenants, Pearl of Great Price, Dead Sea Scrolls, Apocrypha, Pseudepigrapha, and Expanded Canon.

## Tools Available
You have access to these categories of tools (invoked by the user's request):
- **Lookup**: verse text, passage guides (instant connections + gematria + entities for any verse)
- **Search**: full-text search across all works, cross-lingual search (Hebrew/Greek/English)
- **Connections**: typed connections between verses (linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, sod/hidden)
- **Graph**: shortest path between verses, reachable verses, hubs, entity networks
- **Gematria**: Hebrew gematria (standard/ordinal/reduced), Greek isopsephy, Strong's definitions
- **Study**: create/edit/export/publish guided study journeys through the canon

## Formatting — USE THIS IN YOUR RESPONSES
Always format scripture references and entities using these special markers so they become interactive:

### For verse references:
- Use :verse[book.chapter.verse] format
- Examples: :verse[gen.1.1], :verse[isa.55.6], :verse[matt.5.3]
- For verse ranges: :verse[exo.25.18-22]
- For D&C sections: :verse[dc76.76.22] (use "dcNN" as book ID for section NN)
- For whole chapters just mention the chapter reference

### For entities (people, places, concepts):
- Use :entity[Name] format
- Examples: :entity[Abraham], :entity[Melchizedek], :entity[Zion], :entity[Covenant]

### For Gematria:
- Use :gematria[word=value] format
- Example: :gematria[Messiah=358]

### For Strong's numbers:
- Use :strong[H430] for Hebrew, :strong[G26] for Greek
- Example: :strong[H430] (Elohim)

### For connections:
- Use :conn[verseA↔verseB] format
- Example: :conn[gen.1.1↔john.1.1]

## Scripture Study Approach
1. Start with what the text actually says — quote the actual words
2. Distinguish linguistic connections (what the Hebrew/Greek says) from interpretive connections (what traditions say)
3. Label traditions clearly: "Rashi interprets...", "Calvin says...", "The early church taught..."
4. When Jesus and the Pharisees disagreed, Jesus was restoring the original intent of Torah against added traditions
5. Connect themes across the canon using the connection graph

## Hebrew Learning
- You can teach Biblical Hebrew using aleph-bet, vowels, grammar, vocabulary, and root concepts
- Use :verse[] markers to reference scripture examples
- Use :strong[] for word studies
- Format Hebrew words with transliteration when needed

Be concise, accurate, and cite verse references.`


// ── Chat Panel Component ──

export default function ChatPanel({ open, onClose, onNavigate, onOpenTab, initialMessage, variant = 'overlay' }) {
  const { searchWorks, searchLayers, searchLang, bibleVersion, enabledTools } = useToggles?.() || {}
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [waiting, setWaiting] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showRecent, setShowRecent] = useState(false)
  const [recentSessions, setRecentSessions] = useState([])
  const [loadingRecent, setLoadingRecent] = useState(false)
  const [restoring, setRestoring] = useState(false)
  const [popupRef, setPopupRef] = useState(null)
  const [editingIdx, setEditingIdx] = useState(null)   // index of user message being edited, or null
  const [editText, setEditText] = useState('')          // text while editing
  const [copiedIdx, setCopiedIdx] = useState(null)      // index of just-copied message for feedback
  const [visitedRefs, setVisitedRefs] = useState(new Set())
  const [previewRef, setPreviewRef] = useState(null) // { ref: "gen.1.1", label: "Genesis 1:1" }
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const sessionRef = useRef(null)
  const abortRef = useRef(null)
  const titleSet = useRef(false)

  useEffect(() => { sessionRef.current = sessionId }, [sessionId])

  // ── Verse preview detection in input ──
  useEffect(() => {
    const trimmed = input.trim()
    if (!trimmed) { setPreviewRef(null); return }
    // Try parsing as a verse reference using the same parser as SearchBar
    const parsed = parseStandardRef(trimmed)
    if (parsed) {
      // Build refs: for a range, create array of verse refs; for chapter, just the book.chapter
      const refs = parsed.verses?.length > 0
        ? parsed.verses.map(v => `${parsed.book}.${parsed.chapter}.${v}`)
        : `${parsed.book}.${parsed.chapter}`
      const label = parsed.verse
        ? `${parsed.book} ${parsed.chapter}:${parsed.verse}${parsed.verses?.length > 1 ? `-${parsed.verses[parsed.verses.length-1]}` : ''}`
        : `${parsed.book} ${parsed.chapter}`
      setPreviewRef({ ref: refs, label, book: parsed.book, chapter: parsed.chapter })
    } else {
      // Check if it looks like a natural language verse reference
      const verseMatch = trimmed.match(/^([\w\s]+?)\s*(\d+)(?::(\d+(?:[-,]\d+)*))?$/)
      if (verseMatch) {
        const bookId = resolveBook(verseMatch[1].trim())
        if (bookId) {
          const ch = parseInt(verseMatch[2])
          const vs = verseMatch[3]
          const refs = vs ? `${bookId}.${ch}.${vs.split(/[-,]/)[0]}` : `${bookId}.${ch}`
          setPreviewRef({ ref: refs, label: trimmed, book: bookId, chapter: ch })
        } else {
          setPreviewRef(null)
        }
      } else {
        setPreviewRef(null)
      }
    }
  }, [input])

  // ── Initialize session on mount ──
  useEffect(() => {
    if (!open) return

    const init = async () => {
      setRestoring(true)
      const storedId = loadSessionId()
      if (storedId) {
        try {
          const res = await conversationGet(storedId)
          if (res.ok && res.data) {
            const s = res.data
            setSessionId(storedId)
            const restored = [
              { role: 'assistant', content: welcomeMessage(), timestamp: new Date().toISOString() },
              ...s.messages.map(m => ({
                role: m.role, content: m.content, timestamp: m.timestamp,
              })),
            ]
            setMessages(restored)
            titleSet.current = s.messages.length > 0
            setRestoring(false)
            if (initialMessage) setTimeout(() => sendMessage(initialMessage), 300)
            return
          }
        } catch {}
        clearSessionId()
      }

      try {
        const res = await conversationCreate({ title: 'Chat Session' })
        if (res.ok && res.data) {
          setSessionId(res.data.id)
          saveSessionId(res.data.id)
        }
      } catch {}

      setMessages([{ role: 'assistant', content: welcomeMessage(), timestamp: new Date().toISOString() }])
      titleSet.current = false
      setRestoring(false)
      if (initialMessage) setTimeout(() => sendMessage(initialMessage), 300)
    }
    init()
  }, [open])

  const TIPS = [
    "Gematria assigns numerical values to Hebrew letters. gen.1.1 totals 2701 (37x73), a famous palindromic prime pair — numbers that echo creation's mathematical design.",
    "PaRDeS is a four-level Jewish hermeneutic: P'shat (literal), Remez (hinted), Drash (comparative), Sod (hidden/temple). Connections are tagged by level.",
    "The 'sod' (hidden) layer contains temple theology — angelic mediation, the two Yahwehs tradition, cosmic mountain, and the throne vision.",
    "Intertextual connections are quotations and allusions between verses. Linguistic connections share Hebrew or Greek roots across different passages.",
    "A chiasm is an A-B-C-B'-A' literary structure. The center is the pivot point — often the theological key. Many temple texts use chiastic framing.",
    "The connection graph tracks over 1 million typed connections across 11 layers. Click the graph icon in the toolbar to visualize paths between verses.",
    "The Septuagint (LXX) is the Greek translation of the Hebrew Bible used by the NT writers. The Masoretic Text (MT) is the Hebrew tradition.",
    "YHWH is the tetragrammaton — the four-letter divine name. The LSV uses YHWH directly. Its gematria value is 26, the same as the number of generations in Matthew's genealogy.",
    "11 connection layers: linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, and sod.",
    "The engine spans 9 works: OT, NT, Book of Mormon, Doctrine & Covenants, Pearl of Great Price, Dead Sea Scrolls, Apocrypha, Pseudepigrapha, and Expanded Canon.",
    "Switch between English, Hebrew, and Greek display in the Layers popover. Hebrew mode shows word-by-word transliteration with English glosses.",
    "Every connection has a confidence score from 0 to 1. Scores above 0.8 are high-confidence — reported as percentages in chat.",
    "The temple thread runs through all scripture: Eden is the first temple, the Tabernacle is a mobile Eden, the Temple is a permanent one, and Christ is the final temple.",
    "The atonement in the OT temple: the lamb is slain, the priest carries the blood into the Holy of Holies, and sprinkles it on the mercy seat — a direct type of Christ's sacrifice (heb.9.11-14).",
    "Yom Kippur (Day of Atonement) is the only day the High Priest enters the Holy of Holies. Christ enters the heavenly sanctuary once for all — the anti-type of the entire ritual.",
    "The scapegoat on Yom Kippur (lev.16) carries Israel's sins into the wilderness. Christ is both the sacrifice and the scapegoat — he bears our sins outside the camp (heb.13.11-13).",
    "Enoch walks with God and is taken (gen.5.24) — the first human to ascend. The Enochic tradition deeply influenced NT Christology and temple mysticism.",
    "The Melchizedek priesthood (gen.14.18, psalm.110.4, heb.7) connects bread and wine, kingship, and eternal priesthood — a central temple-Christ typology.",
    "The Tabernacle of Moses is a microcosm of creation: 7-branch menorah (7 days), veil (firmament), laver (waters below). Building it mirrors creation week.",
    "The Angel of YHWH appears throughout the OT as YHWH's visible form — seen by Hagar, Abraham, Moses, Joshua, Gideon, and Manoah. Identified with the pre-incarnate Christ by early Christians.",
    "The Mercy Seat (kapporet) on the Ark is where YHWH dwells between the cherubim. Paul calls Christ our kapporet (hilasterion) in rom.3.25 — the place of atonement.",
    "The divine council (psa.82, 1kgs.22, job.1-2) depicts YHWH ruling among the heavenly host — a template for understanding the Son of Man's enthronement.",
    "The Book of Revelation is saturated with temple imagery: 7 lampstands (menorah), sea of glass (laver), altar, incense, ark of the covenant, and the Lamb as temple.",
  ]

  const SUGGESTIONS = [
    'Trace the Angel of YHWH from Genesis to the NT',
    'Show me the temple connections in the Tabernacle chapters',
    'Walk through the chiasm of Isaiah 6',
    'How does Yom Kippur point to Christ\'s atonement?',
    'Find the path from Melchizedek to Christ in the connection graph',
    'Explain the gematria of YHWH and Adam',
    'Compare the creation accounts in Genesis and the Old Testament Temple',
  ]

  // ── Pre-generated responses for suggestions (no LLM call needed) ──
  const PREBUILT_RESPONSES = {
    'Trace the Angel of YHWH from Genesis to the NT': `The **Angel of YHWH** (Malakh YHWH / \u05de\u05b7\u05dc\u05b0\u05d0\u05b7\u05da\u05b0 \u05d9\u05b0\u05d4\u05d5\u05b8\u05d4) is a unique figure in the Hebrew Bible who appears as YHWH himself while being distinct from him — a visible, embodied form of God.

**Key appearances (in order):**

**1. Hagar** (gen.16.7-13) — The first appearance. The Angel finds Hagar in the wilderness, promises descendants, and she names the place "El Roi" — the God who sees me. She identifies the Angel as God himself.

**2. Abraham at Moriah** (gen.22.11-18) — The Angel of YHWH calls from heaven to stop the sacrifice of Isaac, then swears by himself: "I will bless you." The Angel speaks as YHWH, using first-person divine authority.

**3. The Burning Bush** (exo.3.2-6) — The Angel of YHWH appears in the flame. The text immediately says "YHWH saw" and "God called to him out of the bush." The Angel \u2192 YHWH identification is seamless.

**4. Balaam** (num.22.22-35) — The Angel of YHWH stands as an adversary with a drawn sword. Balaam bows and the Angel delivers a message from YHWH.

**5. Joshua** (josh.5.13-15) — The "commander of YHWH's army" appears to Joshua with a drawn sword. Joshua worships him. The ground is declared holy — the same command Moses received at the burning bush (exo.3.5).

**6. Gideon** (judg.6.11-24) — The Angel of YHWH sits under the oak and commissions Gideon. Gideon builds an altar and calls it "YHWH is Peace." The Angel is identified as YHWH.

**7. Manoah** (judg.13.3-22) — The Angel appears to announce Samson's birth. Manoah says "We have seen God" and fears death. The Angel's name is "wonderful" (pele) — the same root as isa.9.6's "Wonderful Counselor."

**8. Elijah** (1kgs.19.5-7) — The Angel touches Elijah and provides food for the journey to Horeb.

**Connection to Christ:**
Early Christian writers (Justin Martyr, Irenaeus, Tertullian) identified the Angel of YHWH as the **pre-incarnate Christ** — the Logos before his incarnation. The logic:
- The Angel speaks as YHWH ("I am the God of Abraham")
- The Angel is seen by human eyes (unlike the Father, whom no one has seen, john.1.18)
- The Angel is sent by YHWH yet speaks with divine authority — a distinction-in-unity pattern

The **sod** layer in this engine connects these as \`angel_of_yhwh\` appearances: a thread of theophanic Christophanies running through the OT, culminating in john.1.14 — "the Word became flesh."`,

    'Show me the temple connections in the Tabernacle chapters': `The **Tabernacle** (exo.25-40) is not just a tent — it is a **microcosm of creation** and a **type of the heavenly sanctuary**. Every element maps to creation, Eden, and Christ.

**Creation-Tabernacle Parallel:**

| Creation (gen.1) | Tabernacle (exo.25-40) |
|---|---|
| 7 days | 7 speeches of instruction (exo.25.1-30.10) |
| Light (day 1) | Golden lampstand / menorah (exo.25.31-40) — 7 branches |
| Waters gathered (day 3) | Bronze laver / sea (exo.30.17-21) |
| Sun & moon (day 4) | Incense altar — daily offerings mark time |
| Adam placed in garden | High Priest enters the Holy of Holies |
| God rests on day 7 | Tabernacle completed — YHWH's glory fills it (exo.40.34) |

**Eden-Tabernacle Typology:**
- Eden is planted by God \u2192 Tabernacle is built by God's pattern
- Adam guards/keeps (\u05e9\u05c1\u05b8\u05de\u05b7\u05e8) the garden \u2192 Priests guard/keep (\u05e9\u05c1\u05b8\u05de\u05b7\u05e8) the sanctuary (num.3.7-8)
- Cherubim guard Eden's entrance (gen.3.24) \u2192 Cherubim woven on the veil + overshadow the ark (exo.26.1, 25.18-20)
- Tree of Life in the garden \u2192 Golden menorah as the Tree of Life (symbolic)
- Rivers flow from Eden \u2192 Water from the rock / laver

**The 7-branch Menorah:**
The menorah's 7 branches mirror the 7 days of creation. It is the only light source inside the Holy Place — just as light was created on day 1. The almond-blossom design (exo.25.33-34) connects to Aaron's rod that budded (num.17.8), linking priesthood to resurrection life.

**Tabernacle \u2192 Temple \u2192 Christ \u2192 Us:**
- Tabernacle (mobile) \u2192 Solomon's Temple (permanent) \u2192 Christ's body (john.2.19-21) \u2192 believers as living stones (1pet.2.5)
- The veil \u2192 Christ's flesh (heb.10.20)
- The High Priest \u2192 Christ as eternal High Priest (heb.7.23-28)
- The sacrifices \u2192 Christ's once-for-all sacrifice (heb.9.11-14)

**Christ as the True Tabernacle:**
John 1:14 says "the Word became flesh and **tabernacled** (\u1f10\u03c3\u03ba\u03ae\u03bd\u03c9\u03c3\u03b5\u03bd) among us." The Greek verb \u03c3\u03ba\u03b7\u03bd\u03cc\u03c9 (skenoo) means "to pitch a tent" — a direct allusion to the Tabernacle. Christ is the true dwelling place of God among humanity.

The **sod** and **symbolic** layers in the engine tag these connections: \`temple_creation\`, \`cosmic_mountain\`, \`mercy_seat_typology\`, and \`menorah_creation\`.`,

    'Walk through the chiasm of Isaiah 6': `**Isaiah 6:1-13** is a tightly structured chiasm centered on the throne vision and the prophet's commissioning.

**The Chiastic Structure:**

> A — The Throne Vision (v.1-4)
> > B — The Prophet's Awe (v.5)
> > > C — The Seraph's Atonement (v.6-7)
> > B' — The Prophet's Response (v.8)
> A' — The Commissioning (v.9-13)

**A — The Throne Vision (v.1-4)**
"In the year that king Uzziah died, I saw the Lord sitting on a throne, high and lifted up..." The hem of his robe fills the temple. Seraphim cry "Holy, holy, holy is YHWH of hosts." The doorposts shake, the house fills with smoke.

This echoes the Sinai theophany (exo.19.16-19) — shaking mountain, smoke, divine presence. It is also a temple vision: the "train" of the robe is the \u05e9\u05c1\u05bb\u05dc\u05b0\u05db\u05bc\u05b8\u0591\u05d4 (shulkah), a term used in exo.28.33-34 for the high priest's hem with bells and pomegranates.

**B — The Prophet's Awe (v.5)**
"Woe is me, for I am undone..." Isaiah's response is not casual reverence but existential crisis — he sees the King and realizes his own uncleanness and his people's. The word "undone" (\u05e0\u05b4\u05d3\u05b0\u05de\u05b5\u05bc\u05ea\u05b4\u05d9) means "silenced/destroyed."

**C — The Seraph's Atonement (v.6-7) — THE CENTER / PIVOT**
A seraph flies to Isaiah with a live coal from the altar. He touches Isaiah's mouth and says: "Your iniquity is taken away, and your sin purged." This is the theological center of the chiasm — **atonement is applied before the commission**.

The altar here is the incense altar (golden altar) inside the Holy Place — the altar of intercession. The live coal carries fire from YHWH's presence. The mouth is cleansed because Isaiah will be a prophet — a mouthpiece for God. Compare with jer.1.9 (YHWH touches Jeremiah's mouth).

**B' — The Prophet's Response (v.8)**
"Here am I. Send me." The atonement produces willing service. Isaiah's response mirrors Moses' and Jeremiah's calls but without hesitation — the coal has already purified.

**A' — The Commissioning (v.9-13)**
The commission is paradoxical: "Go and tell this people: keep on hearing but do not understand." The hardening is judicial — a judgment on a people who have already rejected YHWH. Yet the ending holds hope: "a holy seed is the stump" (v.13).

**Connections across the canon:**
- **john.12.37-41** — John explicitly connects Isaiah's vision to Jesus: "Isaiah said these things because he saw his glory and spoke of him." John identifies the King Isaiah saw as Christ.
- **acts.28.25-27** — Paul uses the same passage to explain Jewish rejection of the gospel.
- **rev.4.2-8** — John's throne vision directly echoes Isaiah 6: the throne, the seraphim, the threefold "holy."

**The chiasm structure** is tagged in the \`structural\` layer as \`chiastic\` type — the engine detects this pattern algorithmically and connects it to other temple-throne visions (ezek.1, 1kgs.22, rev.4).`,

    'How does Yom Kippur point to Christ\'s atonement?': `**Yom Kippur** (the Day of Atonement, lev.16) is the most detailed ritual type of Christ's sacrifice in the Hebrew Bible. Every element maps directly to the events of the crucifixion and Christ's heavenly ministry.

**The Ritual (lev.16):**

**1. The High Priest's Preparation**
Aaron takes off his ordinary priestly garments, bathes, and puts on **linen garments** — not his golden high priestly robes, but simple white linen. He brings a bull for a sin offering and a ram for a burnt offering.
- Christ put off his glory and took on humble human flesh (phil.2.5-8)
- The linen symbolizes righteousness (rev.19.8)

**2. The Two Goats — The Crucial Type**
Two goats are presented before YHWH. Lots are cast:
- **Goat 1 (for YHWH)** — sacrificed as a sin offering, its blood carried into the Holy of Holies
- **Goat 2 (the scapegoat / Azazel)** — the high priest lays both hands on its head, confesses Israel's sins over it, and sends it away into the wilderness

This is one of the deepest types of Christ in the OT:
- Christ is **both goats** — he dies (goat 1) AND he bears our sins away (goat 2)
- The scapegoat carries sins "to a solitary land" — Christ was crucified outside the camp (heb.13.11-13)
- The laying on of hands transfers sin — our iniquity was laid on Christ (isa.53.6)

**3. The Blood in the Holy of Holies**
The high priest takes the bull's blood and the goat's blood behind the veil. He sprinkles it **seven times** on the mercy seat (\u05d4\u05b7\u05db\u05bc\u05b7\u05e4\u05bc\u05b9\u05e8\u05b6\u05ea / kapporet) and before it.
- Christ entered the heavenly Holy of Holies **once for all** with his own blood (heb.9.11-12)
- The mercy seat is where YHWH dwells between the cherubim — Paul calls Christ our \u1f31\u03bb\u03b1\u03c3\u03c4\u03ae\u03c1\u03b9\u03bf\u03bd (hilasterion / mercy seat) in rom.3.25
- Seven = perfection/completion — Christ's sacrifice is sufficient forever

**4. The Scapegoat Released**
"A fit man" leads the scapegoat into the wilderness. The goat bears their iniquities "to a land not inhabited."
- Christ "bore our sins in his body on the tree" (1pet.2.24)
- As far as the east is from the west, so far has he removed our transgressions (psa.103.12)

**5. The Burnt Offerings**
After the atonement ritual, the high priest offers burnt offerings for himself and the people — symbolizing complete dedication.

**The Fulfillment in Christ:**

| Yom Kippur Element | Christ's Fulfillment | Reference |
|---|---|---|
| High Priest enters Holy of Holies | Christ enters heaven itself | heb.9.24 |
| Blood of bulls and goats | Christ's own blood (once for all) | heb.9.12-14 |
| Incense cloud covers the ark | Christ's intercession precedes judgment | heb.7.25 |
| Hands on scapegoat + confession | Christ bore our sins | isa.53.6 |
| Scapegoat sent away | Christ crucified outside the gate | heb.13.12 |
| Atonement made once per year | Christ's once-for-all sacrifice | heb.10.10-14 |

The **intertextual** layer connects lev.16 to heb.9-10 as \`type_antitype\` connections, and the **sod** layer tags the temple-atomement theme across both testaments.`,

    'Find the path from Melchizedek to Christ in the connection graph': `**Melchizedek to Christ** is one of the richest typological threads in scripture, spanning gen.14, psa.110, and heb.5-7. Here is the path, traced through the connection graph:

**Node 1: Melchizedek Appears — gen.14.18-20**
After Abram rescues Lot, Melchizedek — king of Salem and **priest of God Most High** (\u05d0\u05b5\u05dc \u05e2\u05b6\u05dc\u05b0\u05d9\u05d5\u05b9\u05df) — brings out bread and wine and blesses Abram. Abram gives him a tenth of everything.

Key features:
- He is both **king** and **priest** (a rare combination in Israel — kings and priests were separate offices)
- He brings **bread and wine** (Eucharistic type)
- He blesses Abram (the greater blesses the lesser — heb.7.7)
- No genealogy, no birth, no death — "without father, without mother, without descent" (heb.7.3)

**Node 2: The Royal Psalm — psa.110.4**
David writes: "YHWH has sworn and will not change his mind: **You are a priest forever after the order of Melchizedek**." This verse is the most quoted OT verse in the NT.

The connection: an eternal priesthood that is NOT Aaronic (Levitical), but royal — a priesthood of the order of Melchizedek.

**Node 3: Christ Identified as Melchizedek's Heir — heb.5.5-10**
The author of Hebrews makes the explicit connection: Christ did not take the honor of high priesthood upon himself, but was appointed by God as "a priest forever after the order of Melchizedek."

**Node 4: The Full Argument — heb.7.1-28**
This is the theological center of the Melchizedek typology:
- Abraham, the patriarch, tithed to Melchizedek — meaning Levi (Abraham's descendant) was still "in Abraham's loins" when this happened (heb.7.9-10)
- The Levitical priesthood was therefore inferior to Melchizedek's
- If perfection came through Levi, why would another priest arise after Melchizedek's order? (heb.7.11)
- "The former commandment is set aside because of its weakness... a better hope is introduced" (heb.7.18-19)
- Christ is **guarantee of a better covenant** (heb.7.22)

**Node 5: The Last Supper — matt.26.26-28**
Melchizedek brought bread and wine to Abram. At the Last Supper, Christ takes bread and wine and says "This is my body... this is my blood of the covenant." The Melchizedekian bread-and-wine ministry becomes the Eucharistic institution.

**The Graph Path:**

gen.14.18 (Abram meets Melchizedek)
  \u2192 \u2191 \u2014\u2014 linguistic: \`same_name\` ("king of righteousness" = Adonizedek)
  \u2192 \u2193 \u2014\u2014 intertextual: \`quotation\` "after the order of Melchizedek"
psa.110.4 (Davidic oracle)
  \u2192 \u2193 \u2014\u2014 intertextual: \`direct_quotation\` (most-cited OT verse in NT)
heb.5.6 (applied to Christ)
  \u2192 \u2193 \u2014\u2014 intertextual: \`exposition\` (heb.7 unpacking)
heb.6.20 \u2192 heb.7.1-28 (full Melchizedek theology)
  \u2192 \u2193 \u2014\u2014 intertextual: \`type_antitype\`
matt.26.26-28 (Last Supper \u2192 fulfillment of bread/wine type)

The connection graph also links to related nodes like:
- Jesus as King of Kings (rev.19.16) — linking to "king of Salem" (king of peace)
- Jesus as High Priest (heb.4.14-16) — linking to the priestly aspect
- The Eucharist (1cor.11.23-26) — linking the bread and wine type to the sacrament`,

    'Explain the gematria of YHWH and Adam': `**Gematria** is the Hebrew practice of assigning numerical values to letters. The gematria of names reveals patterns of meaning that the biblical authors embedded in the text.

**The Gematria of YHWH (\u05d9\u05d4\u05d5\u05d4):**

| Letter | Name | Value |
|---|---|---|
| \u05d9 | Yod | 10 |
| \u05d4 | He | 5 |
| \u05d5 | Vav | 6 |
| \u05d4 | He | 5 |
| **Total** | | **26** |

26 is the number of YHWH. This number appears throughout scripture:
- There are **26 generations** from Adam to Moses in Matthew's genealogy (matt.1.1-17) — Matthew is showing that Christ sums up the generations of YHWH's covenant people
- The word "glory" (\u05db\u05bc\u05b8\u05d1\u05d5\u05b9\u05d3 / kavod) also equals 26 when counting by ordinal value (kaf=11, bet=2, vav=6, dalet=4 = 23... different calculation systems exist)
- The sum of YHWH + Elohim (26 + 86) = 112 = "YHWH Most High"

**The Gematria of Adam (\u05d0\u05d3\u05dd):**

| Letter | Name | Value |
|---|---|---|
| \u05d0 | Aleph | 1 |
| \u05d3 | Dalet | 4 |
| \u05dd | Mem (final) | 40 |
| **Total** | | **45** |

But there is a deeper pattern: the **ordinal** (positional) value of Adam:
- Aleph = 1 (first letter)
- Dalet = 4 (fourth letter)
- Mem = 13 (thirteenth letter)
- **Ordinal total: 1 + 4 + 13 = 18**

**18 = Life** (\u05d7\u05b7\u05d9 / chai) — the same gematria as \u05d7\u05d9 (chet=8, yod=10). "Adam" = "life" in ordinal gematria.

**The Creation connection (gen.1.1):**
The first verse of the Bible has a total gematria of **2701**, which is 37 \u00d7 73 — a palindromic prime pair (37 and 73 are both prime, and their product reverses to 1072). This is also the sum of all 7 words in gen.1.1.

The first word of gen.1.1 — \u05d1\u05bc\u05b0\u05e8\u05b5\u05d0\u05e9\u05c1\u05b4\u05d9\u05ea (bereshit / "in the beginning") — has a gematria of **913**, which is the sum of:
- 26 (YHWH) + 86 (Elohim) + 45 (Adam) + 405 (the full 5-word phrase for "the heavens and the earth") + 351 (...complex kabbalistic breakdown)

**The Deep Pattern:**
The gematria of Adam (45) connects to YHWH (26) through the creation:
- Adam is made in the **image** / \u05e6\u05b6\u05dc\u05b6\u05dd (tzelem) of Elohim — \u05e6\u05dc\u05dd = 90 + 30 + 40 = **160**
- The word "image" links man to God structurally
- Paul calls Christ the "last Adam" (1cor.15.45) — the \u03c0\u03bd\u03b5\u1fe6\u03bc\u03b1 \u03b6\u1ff3\u03bf\u03c0\u03bf\u03b9\u03bf\u1fe6\u03bd (life-giving spirit)

The gematria for YHWH (26) appears in the center of gen.1.1 as \u05d0\u05b5\u05ea (\u05d0=1, \u05ea=400 = 401) — the untranslated marker of the definite direct object — framed by "God" (86) on one side and "the heavens and the earth" on the other. This is a numerical chiasm: YHWH's name (26) is structurally central in creation.

**Explore in the engine:**
Use the gematria tool (\`scripture_gematria\`) to see values for any Hebrew word. The engine also supports ordinal and reduced gematria, Mispar Gadol (large), and Milui (filling) values.`,

    'Compare the creation accounts in Genesis and the Old Testament Temple': `The **creation account** (gen.1-2) and the **Tabernacle/Temple construction** are deliberately parallel in structure. The Bible presents the Temple as a microcosm — a miniature universe where heaven and earth meet.

**The 7-Day Structure:**

| Day | Genesis Creation | Tabernacle Construction (exo.25-31, 35-40) |
|---|---|---|
| 1 | Light created | Menorah (lampstand) — 7 branches = 7 days |
| 2 | Firmament separates waters | Veil separates Holy Place from Holy of Holies |
| 3 | Dry ground + vegetation | Bronze altar + laver + showbread |
| 4 | Sun, moon, stars | Incense altar + lamps (timekeeping) |
| 5 | Fish + birds | Priestly garments — colors of sea and sky |
| 6 | Man + woman | High Priest enters the sanctuary |
| 7 | God rests (\u05e9\u05c1\u05b8\u05d1\u05b7\u05ea) | YHWH's glory fills the Tabernacle (exo.40.34) |

**The 7 Speeches Pattern:**
In exo.25.1-30.10, there are **7 speeches** of YHWH to Moses on the mountain, matching the 7 days of creation. The 7th speech completes the pattern just as the 7th day completes creation. The phrase "as YHWH commanded Moses" is repeated 7 times in the construction account (exo.39-40).

**Eden as the First Temple:**
The connections between Eden and the Temple are extensive and intentional:

| Eden | Temple |
|---|---|
| Garden planted by God | Sanctuary built by divine pattern |
| \u05e2\u05b5\u05d3\u05b6\u05df (\u00b5eden) = "delight" | \u05e7\u05b9\u05d3\u05b6\u05e9\u05c1 (qodesh) = "holy" |
| Cherubim guard the way (gen.3.24) | Cherubim guard the ark + woven on veil (exo.25.18-22, 26.1) |
| Tree of Life | Menorah (symbolic Tree of Life) |
| Rivers flow from Eden | Water from the rock / laver |
| Adam works/guards (\u05e2\u05b8\u05d1\u05b7\u05d3 \u05d5\u05b0\u05e9\u05c1\u05b8\u05de\u05b7\u05e8) | Priests serve/guard the sanctuary (same verbs, num.3.7-8) |
| God walks in the garden (\u05de\u05b4\u05ea\u05b0\u05d4\u05b7\u05dc\u05bc\u05b5\u05da\u05b0) | YHWH dwells\/walks in the Tabernacle (lev.26.11-12) |

**The Cosmic Mountain:**
Eden is described as being on a mountain (ezek.28.13-14) — the "garden of God" on "the holy mountain of God." Zion\/Temple is also a mountain (psa.48.1-2, isa.2.2-3). The Temple on Mount Moriah is the cosmic mountain where heaven and earth meet — the same place where Abraham offered Isaac (gen.22.2, 2chr.3.1).

**New Testament Fulfillment:**

Christ identifies himself as the true Temple (john.2.19-21). Paul calls the church the "temple of the living God" (2cor.6.16). In Revelation, the New Jerusalem has no temple "for the Lord God Almighty and the Lamb are its temple" (rev.21.22) — creation and temple finally reunite.

The **sod** layer tags these connections as \`cosmic_mountain\`, \`eden_temple\`, and \`creation_tabernacle\`. The \`interpretive\` layer includes the Margaret Barker strand connecting temple theology to creation theology throughout scripture.`
  }

  function handleSuggestion(text) {
    const prebuilt = PREBUILT_RESPONSES[text]
    if (prebuilt) {
      // Add user message + prebuilt response (bypasses LLM call — pre-generated)
      const timestamp = new Date().toISOString()
      const userMsg = { role: 'user', content: text, timestamp }
      const assistantMsg = { role: 'assistant', content: prebuilt, timestamp }
      setMessages(prev => [...prev, userMsg, assistantMsg])
      setInput('')
      autoTitle(text)
      saveMessage('user', text)
      saveMessage('assistant', prebuilt)
    } else {
      sendMessage(text)
    }
  }

  function welcomeMessage() {
    const tip = TIPS[Math.floor(Math.random() * TIPS.length)]
    const suggestionsMarkup = SUGGESTIONS.map((s, i) => `%%%SUGGEST:${i}%%%`).join('\n')
    return `I'm connected to the scripture engine to explore the canon.

Try asking:
${suggestionsMarkup}

──────────
${tip}
──────────

Verse references like gen.1.1 are clickable — tap one to view the verse.`
  }

  // ── Scroll on new messages ──
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Auto-title ──
  const autoTitle = useCallback(async (text) => {
    if (titleSet.current || !sessionRef.current) return
    titleSet.current = true
    const title = text.length > 60 ? text.slice(0, 57) + '...' : text
    try {
      await fetch(`/api/v1/conversations/${sessionRef.current}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      })
    } catch {}
  }, [])

  // ── Save message ──
  const saveMessage = useCallback(async (role, content, metadata) => {
    const sid = sessionRef.current
    if (!sid) return
    setSaving(true)
    try { await conversationAddMessage(sid, role, content, metadata) } catch {}
    setSaving(false)
  }, [])

  // ── Clipboard helpers ──
  const copyToClipboard = async (text, idx) => {
    try { await navigator.clipboard.writeText(text) } catch {}
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 1500)
  }

  const formatConversation = () => {
    return messages
      .filter(m => m.role !== 'system')
      .map(m => `**${m.role === 'user' ? 'You' : 'Assistant'}:** ${m.content}`)
      .join('\n\n---\n\n')
  }

  const copyAllMessages = () => copyToClipboard(formatConversation(), -1)

  // ── Edit helpers ──
  const startEditing = (idx, content) => {
    setEditingIdx(idx)
    setEditText(content)
  }

  const cancelEditing = () => {
    setEditingIdx(null)
    setEditText('')
  }

  // Map tool categories to actual tool names
  const TOOL_CATEGORY_MAP = {
    lookup: ['scripture_verse', 'scripture_passage_guide', 'scripture_interlinear', 'scripture_verse_text'],
    search: ['scripture_search', 'scripture_search_xlingual'],
    connections: ['scripture_connections', 'scripture_intertext', 'scripture_sod', 'scripture_sources', 'scripture_sources_by_scholar', 'scripture_sources_list', 'scripture_consensus', 'scripture_disagreements'],
    graph: ['scripture_graph_path', 'scripture_graph_reachable', 'scripture_graph_entities', 'scripture_graph_shared_entities', 'scripture_graph_entity_network', 'scripture_graph_hubs', 'scripture_graph_centrality'],
    gematria: ['scripture_gematria', 'scripture_strongs'],
    study: ['scripture_study_suggest', 'scripture_study_list', 'scripture_study_get'],
    staging: ['scripture_stage_connection', 'scripture_stage_study'],
  }

  // Shared core: send message list to LLM, append assistant response
  // Abort in-flight request if component unmounts (e.g. user navigates to Read)
  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort()
    }
  }, [])

  const performChat = async (allMessages) => {
    // Cancel any previous in-flight request
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setWaiting(true)
    try {
      // Build disabled tools list from enabledTools state
      let disabledTools = []
      if (enabledTools) {
        for (const [cat, enabled] of Object.entries(enabledTools)) {
          if (!enabled && TOOL_CATEGORY_MAP[cat]) {
            disabledTools = disabledTools.concat(TOOL_CATEGORY_MAP[cat])
          }
        }
      }
      const res = await chat(allMessages, { max_tokens: 128000, disabled_tools: disabledTools, signal: controller.signal })
      if (res.ok && res.data) {
        const { content, reasoning_content: reasoningContent, usage, cost, model, tool_results: toolResults } = res.data
        // If the LLM returned only tool calls with no content, show a cleaner placeholder
        const effectiveContent = content || (toolResults?.length > 0
          ? '_Let me look that up for you..._'
          : '')
        const assistantMsg = { role: 'assistant', content: effectiveContent, reasoning_content: reasoningContent, usage, cost, model, toolResults, timestamp: new Date().toISOString() }
        setMessages(prev => [...prev, assistantMsg])
        saveMessage('assistant', effectiveContent, { reasoning_content: reasoningContent, usage, cost, model, toolResults })
      } else {
        const errorMsg = res?.error || 'Unknown error'
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `**LLM unavailable**: ${errorMsg}\n\nI can still search local scriptures. Try:\n• \`find scriptures about faith\`\n• \`show me isaiah 55:6\``,
          timestamp: new Date().toISOString(),
        }])
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        // Component unmounted while LLM was thinking — silently abort
        abortRef.current = null
        setWaiting(false)
        return
      }
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `**Connection error**: ${err.message}\n\nMake sure the API server is running and try again.`,
        timestamp: new Date().toISOString(),
      }])
    }
    setWaiting(false)
    abortRef.current = null
  }

  // ── Send message (append to end) ──
  const sendMessage = async (text) => {
    if (!text.trim()) return
    const timestamp = new Date().toISOString()
    const userMsg = { role: 'user', content: text, timestamp }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    autoTitle(text)
    saveMessage('user', text)

    // Build scope instructions from search filters
    let scopeInstr = ''
    if (searchWorks) {
      const disabled = Object.entries(searchWorks).filter(([, v]) => !v).map(([k]) => k.toUpperCase())
      if (disabled.length > 0) scopeInstr += `Only search within these works: ALL EXCEPT ${disabled.join(', ')}.`
    }
    if (searchLayers) {
      const disabled = Object.entries(searchLayers).filter(([, v]) => !v).map(([k]) => k)
      if (disabled.length > 0) scopeInstr += ` Exclude these connection layers: ${disabled.join(', ')}.`
    }
    if (searchLang && searchLang !== 'all') {
      scopeInstr += ` Use ${searchLang} language for scripture searches.`
    }
    if (bibleVersion && bibleVersion !== 'KJV') {
      scopeInstr += ` Prefer the ${bibleVersion} version when citing verses.`
    }
    if (enabledTools) {
      const disabled = Object.entries(enabledTools).filter(([, v]) => !v).map(([k]) => k)
      if (disabled.length > 0) scopeInstr += ` Do not use these tool categories: ${disabled.join(', ')}.`
    }

    const allMessages = [
      { role: 'system', content: SYSTEM_PROMPT },
      ...(scopeInstr ? [{ role: 'system', content: `[Scope: ${scopeInstr}]` }] : []),
      ...messages.filter(m => m.role !== 'system').map(m => {
        const base = { role: m.role, content: m.content }
        if (m.reasoning_content) base.reasoning_content = m.reasoning_content
        return base
      }),
      { role: 'user', content: text },
    ]
    await performChat(allMessages)
  }

  // ── Edit + resend (replace from a given index) ──
  const handleResendEdit = async (idx, newText) => {
    if (!newText.trim()) return
    const timestamp = new Date().toISOString()
    const userMsg = { role: 'user', content: newText, timestamp }

    // Build message list from before the edited message
    const priorMessages = messages.slice(0, idx).filter(m => m.role !== 'system').map(m => {
      const base = { role: m.role, content: m.content }
      if (m.reasoning_content) base.reasoning_content = m.reasoning_content
      return base
    })
    const allMessages = [...priorMessages, { role: 'user', content: newText }]

    // Update state: truncate to before the edited message, then add new user message
    setMessages(prev => [...prev.slice(0, idx), userMsg])
    setEditingIdx(null)
    setInput('')

    await performChat(allMessages)
  }

  // ── Load recent sessions ──
  const loadRecent = async () => {
    setLoadingRecent(true)
    try {
      const res = await conversationList(1, 20)
      if (res.ok && res.data) setRecentSessions(res.data.sessions || [])
    } catch {}
    setLoadingRecent(false)
    setShowRecent(true)
  }

  // ── Restore session ──
  const restoreSession = async (sid) => {
    try {
      const res = await conversationGet(sid)
      if (res.ok && res.data) {
        const s = res.data
        setSessionId(sid)
        saveSessionId(sid)
        titleSet.current = s.messages.length > 0
        setMessages([
          { role: 'assistant', content: `_Restored: **${s.title || 'Untitled'}**_`, timestamp: new Date().toISOString() },
          ...s.messages.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp })),
        ])
      }
    } catch {}
    setShowRecent(false)
  }

  const handleClose = () => { clearSessionId(); onClose() }

  if (variant === 'overlay' && !open) return null

  // ── Markdown components with scripture integration ──
  // Uses the shared scripture-markdown module for :verse[], :entity[], :gematria[], etc.
  const markdownComponents = createComponents({
    onOpenVerse: (ref) => setPopupRef(ref),
    customComponents: {
      // Chat-specific overrides for standard elements
      p: ({ children }) => (
        <p className="my-0.5 text-sm leading-relaxed break-words">{children}</p>
      ),
      strong: ({ children }) => (
        <strong className="font-semibold text-neutral-900 dark:text-neutral-100">{children}</strong>
      ),
      em: ({ children }) => (
        <em className="italic text-neutral-700 dark:text-neutral-300">{children}</em>
      ),
      code: ({ className, children, ...props }) => {
        const isInline = !className
        return isInline ? (
          <code className="bg-neutral-100 dark:bg-neutral-800 px-1 rounded text-[10px] font-mono text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700" {...props}>
            {children}
          </code>
        ) : (
          <pre className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-3 my-1.5 overflow-x-auto text-[11px] font-mono text-neutral-700 dark:text-neutral-300 border border-neutral-200 dark:border-neutral-700">
            <code className={className} {...props}>{children}</code>
          </pre>
        )
      },
      blockquote: ({ children }) => (
        <blockquote className="border-l-3 border-indigo-300 dark:border-indigo-600 pl-3 py-1 my-1.5 text-neutral-700 dark:text-neutral-300 text-sm italic">
          {children}
        </blockquote>
      ),
      a: ({ href, children }) => (
        <a href={href} target="_blank" rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline hover:decoration-dotted">
          {children}
        </a>
      ),
      h3: ({ children }) => (
        <h3 className="font-semibold text-neutral-800 dark:text-neutral-200 mt-3 mb-1 first:mt-0 text-sm">{children}</h3>
      ),
      ul: ({ children }) => (
        <ul className="list-disc list-inside space-y-0.5 my-1.5 text-sm text-neutral-700 dark:text-neutral-300">{children}</ul>
      ),
      ol: ({ children }) => (
        <ol className="list-decimal list-inside space-y-0.5 my-1.5 text-sm text-neutral-700 dark:text-neutral-300">{children}</ol>
      ),
      hr: () => <hr className="my-2 border-neutral-200 dark:border-neutral-700" />,
      table: ({ children }) => (
        <div className="overflow-x-auto my-3">
          <table className="w-full text-xs sm:text-sm border-collapse border border-neutral-300 dark:border-neutral-700 rounded-lg overflow-hidden">
            {children}
          </table>
        </div>
      ),
      thead: ({ children }) => (
        <thead className="bg-neutral-100 dark:bg-neutral-800 border-b-2 border-neutral-300 dark:border-neutral-700">
          {children}
        </thead>
      ),
      tbody: ({ children }) => (
        <tbody className="divide-y divide-neutral-200 dark:divide-neutral-700">
          {children}
        </tbody>
      ),
      tr: ({ children }) => (
        <tr className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">{children}</tr>
      ),
      th: ({ children }) => (
        <th className="px-3 py-2 text-left font-semibold text-neutral-700 dark:text-neutral-300 text-[11px] uppercase tracking-wider">{children}</th>
      ),
      td: ({ children }) => (
        <td className="px-3 py-2 text-neutral-600 dark:text-neutral-400 align-top leading-relaxed">{children}</td>
      ),
    },
  })

  // ── Split text into segments at %% markers (inline, html-safe) ──
  // Returns an array of plain text and React elements.
  // Note: verse references are now handled by the :verse[] syntax and scripture-markdown module
  function renderWithMarkers(text) {
    if (!text) return text
    const parts = text.split(/(%%%(?:CLICK|QUIZ|HEBREW|HEBREW_QUIZ):(?:\[[^%]*\]|{[^%]*}|[^%]+)%%%)/g)
    if (parts.length === 1) return text  // no markers, return as-is

    const elements = parts.map((part, i) => {
      const cm = part.match(/%%%CLICK:([^%]+)%%%/)
      if (cm) {
        return (
          <button key={`c${i}`} onClick={() => handleSuggestion(cm[1])}
            className="inline-flex items-center gap-1 px-3 py-1.5 my-0.5 mx-0.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-xs font-medium hover:bg-blue-100 dark:hover:bg-blue-900/50 border border-blue-200 dark:border-blue-700 transition-colors cursor-pointer">
            {cm[1]}
          </button>
        )
      }
      const qm = part.match(/%%%QUIZ:((?:\[[^%]*\]|{[^%]*}))%%%/)
      if (qm) {
        try {
          const quizData = JSON.parse(qm[1])
          // Handle both single question and array of questions
          const questions = Array.isArray(quizData) ? quizData : [quizData]
          return <QuizCard key={`q${i}`} questions={questions} />
        } catch { return <span className="text-red-500 text-xs">[invalid quiz]</span> }
      }
      const hqm = part.match(/%%%HEBREW_QUIZ:({[^%]+})%%%/)
      if (hqm) {
        try {
          const quizData = JSON.parse(hqm[1])
          return <HebrewQuizCard key={`hq${i}`} quizData={quizData} />
        } catch { return <span className="text-red-500 text-xs">[invalid hebrew quiz]</span> }
      }
      const hm = part.match(/%%%HEBREW:({[^%]+})%%%/)
      if (hm) {
        try {
          const hd = JSON.parse(hm[1])
          return (
            <span key={`h${i}`} className="inline-flex flex-col items-center mx-1 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700/50" dir="rtl">
              <span className="text-lg font-serif leading-relaxed">{hd.hebrew}</span>
              {hd.translit && <span className="text-[10px] text-neutral-500 dark:text-neutral-400 mt-0.5">{hd.translit}</span>}
              {hd.gloss && <span className="text-[9px] text-blue-600 dark:text-blue-400 mt-0.5">{hd.gloss}</span>}
            </span>
          )
        } catch { return <span className="text-red-500 text-xs">[invalid hebrew]</span> }
      }
      return part  // plain text
    })

    // Merge adjacent plain-text segments and wrap in a container
    const merged = []
    for (const el of elements) {
      if (typeof el === 'string' && typeof merged[merged.length - 1] === 'string') {
        merged[merged.length - 1] += el
      } else {
        merged.push(el)
      }
    }
    return merged
  }

  // ── Pre-process content: replace refs + suggestions, then render ──
  // Instead of a remark plugin (which breaks), we pre-process the content
  // string, then pass it through react-markdown which handles all markdown
  // structure (tables, blockquotes). The markers in the text are preserved
  // through markdown and caught by the markdownComponents.
  //
  // Strategy: convert markers to zero-width HTML comments that pass through
  // react-markdown's HTML handling, then post-process rendered elements.
  // ACTUALLY: the simplest approach — render the full text as markdown first
  // to get correct structure (tables, blockquotes), then replace markers
  // inline in the output.

  function renderContent(content) {
    if (!content) return null

    // Step 1: Pre-process: replace natural-language refs with :verse[book.ch.vs] syntax
    let processed = preprocessVerses(content)
    // Convert %%SUGGEST:N%% → %%%CLICK:text%%%
    processed = processed.replace(/%%%SUGGEST:(\d+)%%%/g, (m, idx) => {
      const text = SUGGESTIONS[parseInt(idx)]
      return text ? `%%%CLICK:${text}%%%` : m
    })

    // Step 2: Convert :verse[], :entity[], etc. to <span data-type=""> tags
    processed = preprocessScripture(processed)

    // Check if there are any action markers that need special rendering
    // (CLICK, QUIZ, HEBREW, HEBREW_QUIZ — verse refs handled by scripture-markdown)
    const hasActionMarkers = /%%%(?:CLICK|QUIZ|HEBREW|HEBREW_QUIZ):[^%]+%%%/g.test(processed)
    if (!hasActionMarkers) {
      return (
        <Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={markdownComponents}>
          {processed}
        </Markdown>
      )
    }

    // For content with action markers, split at marker boundaries
    const parts = processed.split(/(%%%(?:CLICK|QUIZ|HEBREW|HEBREW_QUIZ):[^%]+%%%)/g)
    const segments = parts.map((part, i) => {
      if (part.startsWith('%%%CLICK:')) {
        return renderWithMarkers(part)
      }
      if (part.startsWith('%%%QUIZ:') || part.startsWith('%%%HEBREW_QUIZ:') || part.startsWith('%%%HEBREW:')) {
        return renderWithMarkers(part)
      }
      // Regular markdown text (with <span> tags from scripture) — render with Markdown component
      if (part.trim()) {
        return (
          <Markdown key={i} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]} components={markdownComponents}>
            {part}
          </Markdown>
        )
      }
      return null
    })

    return <>{segments}</>
  }

  // ── Shared chat body (messages + input) ──
  const chatBody = (
    <>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-[300px]">
        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            {/* Edit mode: textarea for user messages */}
            {msg.role === 'user' && editingIdx === i ? (
              <div className="w-full max-w-[85%] flex flex-col gap-1.5">
                <textarea
                  value={editText}
                  onChange={e => setEditText(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Escape') { e.preventDefault(); cancelEditing(); return }
                    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleResendEdit(i, editText); return }
                  }}
                  className="w-full px-3 py-2 rounded-lg border border-blue-400 dark:border-blue-500 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:ring-2 focus:ring-blue-400 resize-none"
                  rows={3}
                  autoFocus
                />
                <div className="flex items-center gap-2 text-[10px]">
                  <button onClick={() => handleResendEdit(i, editText)}
                    className="px-2.5 py-1 rounded bg-blue-600 text-white font-medium hover:bg-blue-700 cursor-pointer transition-colors">
                    Resend
                  </button>
                  <button onClick={cancelEditing}
                    className="px-2.5 py-1 rounded text-neutral-500 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700 cursor-pointer transition-colors">
                    Cancel
                  </button>
                  <span className="text-neutral-400 dark:text-neutral-500 italic">Ctrl+Enter to resend · Esc to cancel</span>
                </div>
              </div>
            ) : (
              <div className={`group relative max-w-full w-fit px-4 py-2.5 text-sm leading-relaxed shadow-sm break-words
                ${msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-2xl rounded-br-md'
                  : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 rounded-2xl rounded-bl-md'
                }`}>
                {/* Copy button (top-right, on hover) — for assistant messages */}
                {msg.role === 'assistant' && (
                  <button onClick={() => copyToClipboard(msg.content, i)}
                    className="absolute -top-1.5 -right-1.5 opacity-0 group-hover:opacity-100 transition-opacity w-5 h-5 flex items-center justify-center rounded-full bg-white dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 shadow-sm hover:bg-neutral-100 dark:hover:bg-neutral-600 cursor-pointer text-[10px]"
                    title="Copy message">
                    {copiedIdx === i ? (
                      <span className="text-green-600 dark:text-green-400 text-[8px]">✓</span>
                    ) : (
                      <span className="text-neutral-400 dark:text-neutral-400">📋</span>
                    )}
                  </button>
                )}
                {renderContent(msg.content)}

                {/* Reasoning — collapsible thought process */}
                {msg.reasoning_content && (
                  <details className="group mt-1">
                    <summary className="text-[9px] text-neutral-400 dark:text-neutral-500 font-mono cursor-pointer hover:text-neutral-600 dark:hover:text-neutral-300 list-none flex items-center gap-1 select-none">
                      <span className="transition-transform group-open:rotate-90 text-[8px]">▶</span>
                      <span className="italic">reasoning</span>
                    </summary>
                    <div className="mt-0.5 px-2 py-1 rounded bg-neutral-50 dark:bg-neutral-900/50 border border-neutral-200 dark:border-neutral-700 text-[10px] text-neutral-500 dark:text-neutral-400 leading-relaxed whitespace-pre-wrap">
                      {msg.reasoning_content}
                    </div>
                  </details>
                )}

                {/* Token display */}
                {msg.usage && (() => {
                  const total = msg.usage.total_tokens || 1
                  const promptPct = Math.round(msg.usage.prompt_tokens / total * 100)
                  const compPct = Math.round(msg.usage.completion_tokens / total * 100)
                  return (
                    <div className="flex items-center gap-2 mt-1.5 text-[9px] text-neutral-400 dark:text-neutral-500 font-mono">
                      <div className="flex-1 h-1 rounded-full bg-neutral-200 dark:bg-neutral-700 overflow-hidden max-w-[60px]">
                        <div className="h-full flex">
                          <div className="bg-blue-400 dark:bg-blue-500 h-full" style={{ width: `${promptPct}%` }} />
                          <div className="bg-green-400 dark:bg-green-500 h-full" style={{ width: `${compPct}%` }} />
                        </div>
                      </div>
                      <span>{msg.usage.prompt_tokens} in</span>
                      <span>{msg.usage.completion_tokens} out</span>
                      {msg.cost?.total !== undefined && (
                        <span className="text-amber-600 dark:text-amber-400">${Number(msg.cost.total).toFixed(5)}</span>
                      )}
                      {msg.model && (
                        <span className="text-[8px] text-neutral-300 dark:text-neutral-600 truncate max-w-[80px]">{msg.model.replace('deepseek-', '')}</span>
                      )}
                    </div>
                  )
                })()}

                {/* Edit button (bottom-right, on hover) — for user messages (not while waiting) */}
                {msg.role === 'user' && !waiting && (
                  <button onClick={() => startEditing(i, msg.content)}
                    className="absolute -bottom-1.5 -right-1.5 opacity-0 group-hover:opacity-100 transition-opacity w-5 h-5 flex items-center justify-center rounded-full bg-white dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 shadow-sm hover:bg-neutral-100 dark:hover:bg-neutral-600 cursor-pointer text-[10px]"
                    title="Edit message">
                    Edit
                  </button>
                )}
              </div>
            )}
          </div>
        ))}

        {/* Thinking indicator */}
        {waiting && (
          <div className="flex justify-start">
            <div className="bg-neutral-100 dark:bg-neutral-800 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-neutral-500 dark:text-neutral-400 italic flex items-center gap-2 shadow-sm">
              <span className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-neutral-400 dark:bg-neutral-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
              <span>Thinking</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-neutral-200 dark:border-neutral-700 shrink-0">
        {/* Verse preview inline */}
        {previewRef && (
          <div className="mb-3">
            <VersePreviewCard refs={previewRef.ref} onNavigate={(b, c) => { onNavigate(b, c); handleClose() }} maxHeight="10rem" compact />
            <div className="flex items-center gap-2 mt-1.5">
              <button onClick={() => {
                const refs = Array.isArray(previewRef.ref) ? previewRef.ref : [previewRef.ref]
                const msg = refs.map(r => `:verse[${r}]`).join(', ')
                sendMessage(msg)
                setPreviewRef(null)
              }}
                className="px-2.5 py-1 rounded-lg bg-blue-600 text-white text-[10px] font-medium hover:bg-blue-700 cursor-pointer transition-colors"
                title="Send this verse as context">
                + Add as context
              </button>
              <button onClick={() => setPreviewRef(null)}
                className="text-[10px] text-neutral-400 dark:text-neutral-500 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer">
                Dismiss
              </button>
              <span className="text-[9px] text-neutral-400 dark:text-neutral-500 ml-auto">{previewRef.label}</span>
            </div>
          </div>
        )}
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Escape' && variant === 'overlay') { handleClose(); return }
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); return }
            }}
            placeholder="Ask about scriptures... (type a verse ref to preview)"
            className="flex-1 px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 text-sm bg-white dark:bg-neutral-800 text-neutral-800 dark:text-neutral-200 outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 placeholder-neutral-400 dark:placeholder-neutral-500"
            disabled={waiting || restoring}
          />
          <button onClick={() => sendMessage(input)} disabled={waiting || restoring || !input.trim()}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium
              hover:bg-indigo-700 disabled:bg-neutral-300 dark:disabled:bg-neutral-700 disabled:cursor-not-allowed cursor-pointer transition-colors">
            Send
          </button>
        </div>
      </div>
    </>
  )

  // ── Shared overlays (Verse popup + Recent sessions) ──
  const overlays = (
    <>
      {popupRef && (
        <VersePopup
          verseRef={popupRef}
          onClose={() => setPopupRef(null)}
          onNavigate={(book, chapter) => {
            setPopupRef(null)
            onNavigate(book, chapter)
          }}
        />
      )}
      {showRecent && (
        <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[10vh]"
          onClick={() => setShowRecent(false)}>
          <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-md mx-4 max-h-[50vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
              <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Recent Conversations</h3>
              <button onClick={() => setShowRecent(false)}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-sm px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800">Close</button>
            </div>
            {loadingRecent && <div className="px-4 py-8 text-center text-sm text-neutral-400 italic">Loading...</div>}
            {!loadingRecent && recentSessions.length === 0 && <div className="px-4 py-8 text-center text-sm text-neutral-400">No conversations yet</div>}
            {!loadingRecent && recentSessions.map(s => (
              <button key={s.id} onClick={() => restoreSession(s.id)}
                className="w-full text-left px-4 py-3 border-b border-neutral-100 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800 cursor-pointer transition-colors">
                <div className="text-sm font-medium text-neutral-800 dark:text-neutral-200 truncate">{s.title || 'Untitled'}</div>
                <div className="text-[10px] text-neutral-400 dark:text-neutral-500 mt-0.5">
                  {s.message_count || 0} messages · {s.created_at?.slice(0, 10) || ''}
                  {s.is_starred ? ' · ⭐' : ''}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  )

  // ── Tab variant: inline in main content ──
  if (variant === 'tab') {
    return (
      <div className="flex flex-col h-full bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 max-w-5xl mx-auto w-full">
        <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Chat</h2>
            {saving && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">saving...</span>}
            {restoring && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">restoring...</span>}
          </div>
          <div className="flex items-center gap-1">
            {messages.length > 0 && (
              <button onClick={copyAllMessages}
                className="text-[11px] text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 cursor-pointer px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                title="Copy all messages">
                {copiedIdx === -1 ? '✓ Copied' : 'Copy all'}
              </button>
            )}
            {messages.length > 0 && (
              <button onClick={() => { clearSessionId(); setMessages([]); setSessionId(null) }}
                className="text-[11px] text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 cursor-pointer px-2 py-0.5 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors font-medium"
                title="Start a new chat">
                + New
              </button>
            )}
            <button onClick={loadRecent}
              className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 cursor-pointer px-2 py-0.5 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
              Recent
            </button>
          </div>
        </div>
        {chatBody}
        {overlays}
      </div>
    )
  }

  // ── Overlay variant: fixed position popup ──
  return (
    <>
      <div className="fixed inset-0 z-50 flex items-end justify-center pb-4 pointer-events-none">
        <div className="w-full max-w-3xl mx-4 bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 pointer-events-auto flex flex-col max-h-[80vh]"
          onClick={e => e.stopPropagation()}>

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 shrink-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-neutral-800 dark:text-neutral-200">Scripture Chat</h2>
              {saving && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">saving...</span>}
              {restoring && <span className="text-[10px] text-neutral-400 dark:text-neutral-500 italic">restoring...</span>}
            </div>
            <div className="flex items-center gap-1">
              {messages.length > 0 && (
                <button onClick={copyAllMessages}
                  className="text-[11px] text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 cursor-pointer px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                  title="Copy all messages">
                  {copiedIdx === -1 ? '✓ Copied' : 'Copy all'}
                </button>
              )}
              {messages.length > 0 && (
                <button onClick={() => { clearSessionId(); setMessages([]); setSessionId(null) }}
                  className="text-[11px] text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 cursor-pointer px-2 py-0.5 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors font-medium"
                  title="Start a new chat">
                  + New
                </button>
              )}
              <button onClick={loadRecent}
                className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 cursor-pointer px-2 py-0.5 rounded hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors">
                Recent
              </button>
              <button onClick={handleClose}
                className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 cursor-pointer text-sm px-2 py-0.5 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                ESC close
              </button>
            </div>
          </div>

          {chatBody}
        </div>
      </div>
      {overlays}
    </>
  )
}

// ── Persistence helpers ──

const STORAGE_KEY = 'current_chat_session'
function loadSessionId() { try { return localStorage.getItem(STORAGE_KEY) } catch { return null } }
function saveSessionId(id) { try { localStorage.setItem(STORAGE_KEY, id) } catch {} }
function clearSessionId() { try { localStorage.removeItem(STORAGE_KEY) } catch {} }
