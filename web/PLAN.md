# Scripture Knowledge Engine — Web UI Plan

## Architecture

```
                    ┌─────────────────────────────────┐
                    │   Any LLM (Claude, GPT, etc.)    │
                    │   Uses API via function calling   │
                    └─────────────┬───────────────────┘
                                  │ HTTP
┌─────────────────────────────────▼─────────────────────────────────┐
│                      FastAPI /api/v1/                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Verses   │ │ Search   │ │ Gematria │ │ Sod      │ │ PaRDeS   │ │
│  │ + Guide  │ │ (tri-   │ │ (word /  │ │ (atbash, │ │ (levels) │ │
│  │ (pre-    │ │ lingual) │ │  value)  │ │ acrost.) │ │          │ │
│  │ computed)│ │          │ │          │ │          │ │          │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────────────────────┐ │
│  │ Tabs     │ │ Custom   │ │ Info / Health                       │ │
│  │ (UI      │ │ Tabs     │ │                                     │ │
│  │ state)   │ │ (CRUD)   │ │                                     │ │
│  └──────────┘ └──────────┘ └────────────────────────────────────┘ │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │ same data
                    ┌─────────────▼─────────────┐
                    │    scripture.db             │
                    │    42K verses               │
                    │    218K connections          │
                    │    41K passage guides       │
                    │    305K gematria entries    │
                    │    137K isopsephy entries   │
                    └───────────────────────────┘
```

## Frontend Tech Stack

```
Framework:     React 19 + Vite
Styling:       Tailwind CSS 4
State:         React Context (useReducer for tab state)
Routing:       Client-side (hash-based, no router needed)
PWA:           manifest.json + workbox service worker
Mobile:        Bottom tab bar, swipe gestures, drawer panel
Deploy:        Static build served by FastAPI
```

## Component Tree

```
<App>
  ├── <SearchBar />              — Cross-lingual search input
  ├── <TabBar />                 — Two-layer tab navigation
  │   ├── <TopicTabs />           — Top-level (Torah, Gospels, My Study...)
  │   └── <SubTabs />             — Within-topic (Genesis, Exodus...)
  ├── <VerseView />              — Main content area
  │   ├── <VerseText />           — Scripture with [[wikilink]] anchors
  │   └── <FootnotePopup />       — Connection details on click
  ├── <ConnectionPanel />        — Sidebar / bottom drawer
  │   ├── <LayerToggles />       — Per-layer visibility
  │   ├── <PaRDeSFilter />       — P'shat / Remez / Drash / Sod
  │   ├── <SkepticToggle />      — Quality level (verified→speculative)
  │   └── <ConnectionList />     — Filtered connections with targets
  ├── <SearchPanel />            — Search results
  ├── <GuidedStudyPlayer />      — Step-through study interface
  └── <CreateTabModal />         — New custom tab dialog
```

## Tab System

### Two-Layer Navigation

```
Top-level:   [Torah] [Prophets] [Writings] [Gospels] [Last Days] [My Study] [+]
Subtabs:     [Genesis] [Exodus] [Leviticus] [Numbers] [Deuteronomy]
```

- Click a topic → shows its subtabs
- Click a subtab → loads content
- `[+]` → opens dialog: name + icon + content type (verses, search, study)
- Tabs persist via `/api/v1/tabs` endpoints
- Custom tabs stored via `/api/v1/custom-tabs` CRUD

### Tab Content Types

| Type | What Displays | Data Source |
|------|--------------|-------------|
| `verse` | Single verse with connections | `GET /api/v1/verses/{ref}` |
| `chapter` | Full chapter, sequential | `GET /api/v1/verses?range=...` |
| `search` | Search results | `GET /api/v1/search?q=...` |
| `study` | Guided study step | `GET /api/v1/studies/{id}` |
| `custom` | User-defined collection | `custom-tabs/{id}/content` |

## Verse Display

### Wikilink Footnoting

Each verse is displayed with inline anchors. Words/phrases that have connections get superscript numbers:

```
In the beginning[1] God[2] created the heaven and the earth[3].

[1] 📊 Intertextual → John 1:1
[2] 💡 Numerical → Elohim = 86
[3] 📊 Linguistic → same_lemma H776 with Psa 148:13
```

```jsx
function VerseText({ text, connections }) {
  // Split text at connection anchors, render [[wikilinks]]
  // Each anchor gets a superscript number
  // Clicking opens a tooltip with connection details
}
```

### Connection Icons

| Icon | Layer | Color |
|------|-------|-------|
| 📝 | Linguistic | Green |
| 🔢 | Numerical | Purple |
| 📐 | Structural | Blue |
| 📖 | Intertextual | Teal |
| 📜 | Textual | Brown |
| 🌍 | Geographic | Earth |
| 📅 | Chronological | Orange |
| 💭 | Interpretive | Pink |
| 📊 | Frequency | Gray |
| 🔮 | Symbolic | Indigo |

### Quality Markers

| Emoji | Level | When |
|-------|-------|------|
| ✅ | Strong | p < 0.01 + null control |
| 📊 | Probable | p < 0.05 + null control |
| 💡 | Suggested | Detected, not tested |
| ❓ | Speculative | Weak signal |
| ❌ | Rejected | Failed controls |

## Connection Panel

Located in a sidebar (desktop) or bottom drawer (mobile):

```
┌────────────────────────────────────┐
│ 🔍 Connections — Genesis 1:1       │
│                                    │
│ ☑ Linguistic   (12)  [P'shat]     │
│ ☑ Numerical    (5)   [Sod]        │
│ ☑ Structural   (2)   [P'shat]     │
│ ☑ Intertextual (3)   [Remez]      │
│ ☐ Textual      (0)   [P'shat]     │
│ ☐ Geographic   (0)   [Drash]      │
│ ☐ Symbolic     (2)   [Remez]      │
│                                    │
│ PaRDeS: [P'shat] [Remez] [Drash] [Sod]
│                                      │
│ Quality: [All] [Strong] [Probable] [Skeptic]
│                                      │
│ ▽ intertextual (3)                   │
│   📖 direct_quotation → John 1:1    │
│   📖 allusion → Rev 21:1            │
│                                      │
│ ▽ numerical (5)                      │
│   🔢 Elohim = 86 (divine name)      │
│   🔢 Total gematria 2701             │
└────────────────────────────────────┘
```

## Search Panel

```
┌────────────────────────────────────┐
│ 🔍                                  │
│ [covenant.......................]   │
│                                    │
│ ◉ All    ○ English   ○ Hebrew  ○ Greek
│                                    │
│ Results: 496 verses                │
│ ┌─────────────────────────────┐   │
│ │ Gen 17:7  covenant ...      │   │
│ │ Exo 2:24  remembered his    │   │
│ │          covenant ...       │   │
│ │ Lev 26:42 I will remember   │   │
│ │          my covenant ...    │   │
│ └─────────────────────────────┘   │
└────────────────────────────────────┘
```

## Files to Create

```
frontend/
├── package.json
├── vite.config.js
├── index.html
├── manifest.json              ← PWA installable
├── sw.js                      ← Service worker cache
├── tailwind.config.js
├── postcss.config.js
├── src/
│   ├── main.jsx
│   ├── App.jsx                — Tab state, active verse, layout
│   ├── App.css
│   ├── components/
│   │   ├── TabBar.jsx         — Two-layer tab navigation
│   │   ├── VerseView.jsx      — Scripture text with wikilinks
│   │   ├── ConnectionPanel.jsx— Sidebar with layer toggles
│   │   ├── LayerToggles.jsx   — Per-layer visibility
│   │   ├── PaRDeSFilter.jsx   — P'shat/Remez/Drash/Sod
│   │   ├── SkepticToggle.jsx  — Quality filter
│   │   ├── SearchPanel.jsx    — Search + results
│   │   ├── GuidedStudyPlayer.jsx — Study step player
│   │   └── CreateTabModal.jsx — New custom tab dialog
│   └── api.js                 — API client (fetch wrapper)
```

## Build Order

| Phase | Files | Time |
|-------|-------|------|
| 1 | `index.html`, `vite.config.js`, `package.json`, `tailwind.config.js`, `postcss.config.js`, `manifest.json`, `sw.js` | 30 min |
| 2 | `main.jsx`, `App.jsx`, `App.css`, `api.js` | 45 min |
| 3 | `TabBar.jsx` — two-layer tabs, create tab modal | 30 min |
| 4 | `VerseView.jsx` — wikilinks, footnote popup | 45 min |
| 5 | `ConnectionPanel.jsx`, `LayerToggles.jsx`, `PaRDeSFilter.jsx`, `SkepticToggle.jsx` | 45 min |
| 6 | `SearchPanel.jsx` — cross-lingual search | 30 min |
| 7 | `GuidedStudyPlayer.jsx` — study player | 30 min |
| 8 | Polish, mobile responsive, PWA testing | 60 min |

**Total: ~6 hours**

## API Endpoints (for LLM)

| Endpoint | Purpose | LLM Usage Example |
|----------|---------|-------------------|
| `GET /api/v1/verses/{ref}` | Verse + all connections | "Show me Genesis 1:1" |
| `GET /api/v1/verses/{ref}/connections?layer=&min_quality=` | Filtered connections | "What probable intertextual links does Isa 6 have?" |
| `GET /api/v1/search?q=&lang=` | Cross-lingual search | "Find verses about covenant in Hebrew" |
| `GET /api/v1/gematria?word=` | Gematria lookup | "What is the gematria of YHWH?" |
| `GET /api/v1/gematria?value=26` | Find verses by value | "What verses have gematria 26?" |
| `GET /api/v1/sod?verse=` | Hidden patterns | "Show hidden patterns in Gen 1:1" |
| `GET /api/v1/sod?atbash_word=ששך` | Atbash decode | "Decode Sheshach" |
| `GET /api/v1/sod?acrostic_book=prov` | Acrostic detection | "Find acrostics in Proverbs" |
| `GET /api/v1/pardes/{ref}` | PaRDeS grouping | "Show Sod-level connections" |
| `GET /api/v1/tabs` | List open tabs | "What do I have open?" |
| `POST /api/v1/tabs` | Open a new tab | "Open Genesis 1" |
| `DELETE /api/v1/tabs/{id}` | Close a tab | "Close the search tab" |
| `GET /api/v1/info` | Database stats | "How many connections exist?" |
| `GET /api/v1/health` | Health check | "Is the server running?" |

All endpoints return `{"ok": true/false, "data": ...}`.

OpenAPI docs at `/docs`.
