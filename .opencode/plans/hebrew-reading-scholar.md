# Plan: Hebrew Display — Reading/Scholar Modes + Fonts + Interlinear

## Goal
Give users three display modes for Hebrew text: Reading (clean, large), Scholar (with morphology/Strong's), and Interlinear (word-by-word stacked). Bundle proper Hebrew fonts, fix text sizing for mobile niqqud readability, and fix the client-side transliteration.

---

## Pre-resolved Decisions

### Fonts to bundle
| Font | License | Source |
|------|---------|--------|
| **Ezra SIL** | ✅ SIL OFL (free, commercial OK) | `software.sil.org/ezra/` — WOFF2 available |
| **SBL Hebrew** | ⚠ Free for non-commercial, needs TTF→WOFF2 conversion | `sbl-site.org/resources/fonts/` |
| **Taamey Frank CLM** | ✅ GPL+font exception (free) | Culmus project |

**Recommendation**: Bundle Ezra SIL (WOFF2) as the primary. It's OFL-licensed, has official web fonts, and covers all Biblical Hebrew diacritics. Add SBL Hebrew as a secondary `@font-face` if the user's usage is non-commercial.

### Display modes
1. **Reading** — Clean Hebrew (no `/`, no Strong's), large font, extra line-height
2. **Scholar** — Morphological separators visible, Strong's numbers as superscripts, parsed forms below
3. **Interlinear** — Word-by-word stacked: Hebrew / transliteration / English gloss / morph code

### Transliteration
Replace the broken client-side map with the server-side `biblical_transliteration` SBL scheme (already deployed). Send transliteration from the API instead of computing it in the browser.

### Font sizes
| Context | Size (mobile) | Size (desktop) |
|---------|--------------|----------------|
| Reading mode | `clamp(1.25rem, 5vw, 1.75rem)` | `1.5rem` |
| Scholar mode | `1.125rem` | `1.25rem` |
| Interlinear (Hebrew) | `1.125rem` | `1.25rem` |
| Interlinear (gloss/translit) | `0.75rem` | `0.8125rem` |
| Line height | `1.8` for reading, `1.6` for scholar | |

---

## Track A: Hebrew Font Bundle `[ ]`

### Phase A1: Download and convert fonts `[ ]`
- [ ] Download Ezra SIL WOFF2 from SIL (official web font package)
- [ ] Download SBL Hebrew TTF, convert to WOFF2 via `pyftsubset`
- [ ] Download Taamey Frank CLM TTF, convert to WOFF2
- [ ] Add fonts to `frontend/public/fonts/`
- 📏 Scope: ~3-6 font files, ~500KB each
- ✅ Checkpoint: `ls frontend/public/fonts/*.woff2 | wc -l` >= 3
- ⚙ Fallback: Use Google Fonts Noto Sans Hebrew CDN as fallback

### Phase A2: Add @font-face declarations `[ ]`
- [ ] Add `@font-face` blocks in `frontend/src/index.css` or a new `fonts.css`
- [ ] Create CSS font stack utility classes: `.font-hebrew-biblical`, `.font-hebrew-modern`
- [ ] Use `unicode-range: U+0590-05FF, U+FB1D-FB4F` to avoid affecting Latin text
- [ ] Use `font-display: swap` for fast first paint
- 📏 Scope: 1 CSS file, ~30 lines
- ✅ Checkpoint: Fonts load on the page (check via devtools Network tab)
- ⚙ Fallback: System fonts as fallback chain

---

## Track B: Three Display Modes `[ ]`

### Phase B1: Create mode state and toggle UI `[ ]`
- [ ] Add `hebrewDisplayMode` to ToggleProvider: `'reading' | 'scholar' | 'interlinear'`
- [ ] Add mode selector UI in the toolbar (or LayersPopover): three pill buttons
- [ ] Persist preference in localStorage
- 📏 Scope: 2 files (ToggleProvider, App/LayersPopover), ~40 lines
- ✅ Checkpoint: Mode selector visible, clicking changes state
- ⚙ Fallback: Start with just Reading + Scholar, add Interlinear later

### Phase B2: Reading mode — clean Hebrew `[ ]`
- [ ] In `VerseBlock.jsx`: when `hebrewDisplayMode === 'reading'`:
  - Strip `/` from `text_hebrew` (or use `text_hebrew` field that was already cleaned)
  - Apply `.font-hebrew-biblical` class
  - Font size `clamp(1.25rem, 5vw, 1.75rem)`
  - Line height `1.8`
  - No transliteration, no glosses visible by default
  - Show English translation below as a block, not interleaved
- 📏 Scope: 1 file (VerseBlock), ~30 lines
- ✅ Checkpoint: Reading mode shows clean Hebrew at large size, English below
- ⚙ Fallback: Fall back to current word-by-word display if mode not set

### Phase B3: Scholar mode — annotated Hebrew `[ ]`
- [ ] Show morphological separators (`/` preserved or shown as thin space)
- [ ] Strong's numbers as superscripts above/beside each word
- [ ] Morphological parsing codes below words (e.g., `V-Qal-Perf-3MS`)
- [ ] Color-coded by part of speech
- [ ] Root letters highlighted in bold/color
- 📏 Scope: 1 file (VerseBlock), ~50 lines
- ✅ Checkpoint: Genesis 1:1 shows Strong's + morph codes + color
- ⚙ Fallback: Show just Strong's numbers if morph data unavailable

### Phase B4: Interlinear mode — word-by-word stacking `[ ]`
- [ ] Word-by-word vertical stacking: Hebrew / transliteration / English gloss / morph
- [ ] Use server-provided transliteration (SBL scheme) not client-side map
- [ ] Color-code by part of speech
- [ ] Responsive: on mobile, stack vertically; on desktop, allow horizontal scrolling
- 📏 Scope: 2 files (VerseBlock, CardRenderer), ~60 lines
- ✅ Checkpoint: Word-by-word display with 4-line stacks per word
- ⚙ Fallback: Fall back to 2-line (Hebrew + English) if transliteration not available

---

## Track C: Hebrew Text Display Cleanup `[ ]`

### Phase C1: Strip `/` from Hebrew at display time `[ ]`
- [ ] Create utility function `cleanHebrew(text)` that strips `/`
- [ ] Apply in all Hebrew display locations:
  - `VerseBlock.jsx`
  - `HebrewLessonView.jsx`
  - `HebrewQuizCard.jsx`
  - `WikiLayout.jsx`
  - `MemorizeQueue.jsx`
  - `CardRenderer.jsx`
  - Any other component rendering `text_hebrew`
- [ ] Scholar mode preserves the `/` (it's meaningful)
- 📏 Scope: ~7 files, ~70 lines
- ✅ Checkpoint: Reading mode shows no slashes, Scholar mode shows them
- ⚙ Fallback: Just do a global `.replace(/\//g, '')` as a first pass

### Phase C2: Fix client-side transliteration `[ ]`
- [ ] Fix the shin/sin dot bug: don't strip `\u05C1` or `\u05C2` from `HEBREW_TRANSLIT` regex
- [ ] Better: replace the client-side transliterateHebrew with the server-provided transliteration data
- [ ] Ensure the API endpoint for verse/word data includes SBL-scheme transliteration
- 📏 Scope: 2 files, ~20 lines
- ✅ Checkpoint: `שָׁלוֹם` transliterates as `šālôm` not `שלום`
- ⚙ Fallback: Remove client-side transliteration entirely, always use server data

### Phase C3: Increase Hebrew text size on mobile `[ ]`
- [ ] Audit all Hebrew text rendering for minimum 1.25rem (20px) on mobile
- [ ] Add responsive size classes: `text-lg sm:text-xl lg:text-2xl`
- [ ] Increase line-height to 1.6-1.8 for niqqud/cantillation clearance
- 📏 Scope: ~5 files, ~40 lines
- ✅ Checkpoint: Hebrew text at 20px minimum on 375px viewport
- ⚙ Fallback: Focus on the most-used components first (VerseBlock, HebrewLessonView)

---

## Track D: Server-side transliteration improvements `[ ]`

### Phase D1: Add SBL transliteration to verse API `[ ]`
- [ ] In `web/server.py` verse endpoint, add `transliteration_sbl` field using SBL scheme
- [ ] Also add to the passage guide endpoint
- [ ] Update frontend to prefer server-provided transliteration over client-side
- 📏 Scope: 2 files (web, frontend), ~15 lines
- ✅ Checkpoint: Verse API returns `transliteration_sbl` with proper SBL diacritics
- ⚙ Fallback: Client-side map continues to work as fallback

---

## Execution Order

1. **Phase C1** — Strip `/` (quick win, fixes the immediate user complaint)
2. **Phase A1 + A2** — Download and bundle fonts
3. **Phase B1** — Create mode toggle state
4. **Phase B2** — Reading mode (uses clean Hebrew from C1)
5. **Phase C2 + C3** — Fix transliteration + mobile sizing
6. **Phase B3** — Scholar mode
7. **Phase B4** — Interlinear mode
8. **Phase D1** — Server-side SBL transliteration
