---
status: proposed
kind: proposal
area: frontend
author: axe
created: 2026-09-29
---

# Unified navigation: one IA for the whole app

**Problem:** the app currently has five overlapping navigation systems that
disagree about names, and three search inputs that parse the same queries
independently. A user can reach the same destination four ways with four
different labels (Subjects / Tiles / WS; Learn / Knowledge / 📚; Wiki / 📖 vs
Essays / 📜 vs Studies / 🎓; Memorize / Review / 🧠), and Hebrew, History, and
HubNotes each exist both as full-screen `show*` overlays *and* as tab
`viewLevel`s, with a `mobileActiveTab` heuristic papering over which one is
visible. The prev/next arrows also change meaning per view level (chapter →
book → work → essay → study → history-back), so the same button surprises.

Prior cleanup (2026-09-29) fixed the acute symptoms: removed the colliding
TileDashboard bottom bar, unified Review→Memorize, deduplicated drawer icons,
and repaired the dead `/graph?verse=` links. This proposal is the structural
fix underneath.

## Proposed canonical IA

One primary switcher per form factor, one overflow menu, one search:

| Surface | Canonical role |
|---|---|
| Desktop header breadcrumb + tab strip | Location + open tabs (keep) |
| Mobile bottom nav | Primary switcher: Read, Chat, Hebrew, Learn, Memorize (keep) |
| Mobile drawer / desktop Menu | Overflow *only*: Paths, Essays, Wiki, Studies, Layers, Structure, History, Settings (remove duplicates of bottom-nav destinations) |
| Command palette (`/`) | The *only* search/go-to input; SearchBar and mobile "Go to…" become thin skins over it |
| Library | Single home for Wiki, Essays, Studies, HubNotes, Collections, CFM (today: 6 top-level destinations) |

Vocabulary: **Subjects** everywhere (drop Tiles/WS from user-visible copy;
workspace stays as the code word, as "tab group" does in browsers).

## Phases, cheapest first

1. **Drawer/menu dedupe (~30 lines).** Remove Learn/Memorize/Hebrew entries
   from the drawer and desktop Menu — they duplicate the bottom nav and tab
   strip. Drawer keeps Paths, Essays, Wiki, Studies, Tools, Account, Settings.
2. **Single search entry (~80 lines).** Route SearchBar and the mobile "Go
   to…" input through the CommandInput parser UI instead of their own
   `parseAndFuzzy` + dropdown implementations. Same results, one code path.
3. **Overlays → tabs (~120 lines).** Delete the `showHebrewLearn`,
   `showHebrewDiagnostic`, `showHubNotes`, `showHistory` overlay branches in
   `MainContentView`; those destinations already exist as `viewLevel`s
   (`hebrew`, `hubnote`, chat-history tab). Overlays remain for true modals
   only (Structure, Settings, split-picker, Assessment, cheatsheet).
   `mobileActiveTab` heuristic in `App.jsx` collapses to a viewLevel lookup.
4. **Arrow semantics (~60 lines).** Prev/next step *within the level* only;
   history back/forward moves to explicit buttons (already in More menu on
   mobile; add to desktop header). No silent fallback from "next essay" to
   "history back".
5. **Library consolidation (~200 lines, optional).** Wiki/Articles/Studies/
   HubNotes/Collections/CFM render inside the Library view with sub-tabs
   instead of top-level viewLevels. Biggest win, biggest diff — defer until
   1–4 prove the pattern.

## What we would ask for, cheapest first

Phases 1–2 are pure deletion with no behavior change and could ship
independently. Phase 3 is the only one that moves user-visible state (deep
links to `?study=`/`?wiki=` keep working; in-flight overlay state does not
transfer — acceptable, overlays hold no persistent data). Phase 5 is
explicitly separable and may be rejected without losing 1–4.

## Verification

Existing suites (`vitest run`, `pytest tests/test_api.py`, `vite build`) plus
the Playwright `navigation.spec.ts` / `app.spec.ts` specs, which already cover
the tab strip and bottom nav. No backend changes in any phase.
