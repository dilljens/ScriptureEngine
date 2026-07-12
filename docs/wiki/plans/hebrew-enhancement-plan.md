# Hebrew Learning System — Enhancement Plan

> Based on gap analysis against Duolingo, Memrise, Drops, Aleph with Beth,
> Pimsleur, Rosetta Stone, Anki, LingQ, Mondly, BYU, Daily Dose of Hebrew.

## Priority Order (impact → effort)

| # | Feature | Effort | Impact | Existing Infrastructure |
|---|---------|--------|--------|------------------------|
| **1** | Cloze deletion card type | 1h | High | CardRenderer, card-factory, FSRS-5 |
| **2** | Frequency-ordered top 1000 vocab | 1h | High | Lexicon table with frequency column |
| **3** | Passage study mode (LingQ-style) | 4h | **Critical** | All verse data, Strong's, card-factory |
| **4** | Two-way translation cards | 2h | High | CardRenderer, FSRS-5 |
| **5** | Daily maintenance mode | 2h | Medium | Random verse API, CardQueue |
| **6** | Audio-first / commute mode | 3h | Medium | TTS, CardQueue |
| **7** | Hebrew-only visual mode | 2h | Medium | CardRenderer toggle |

---

## 1. Cloze Deletion Card Type (1h)

### What
A card that shows a verse with one or more words blanked out. User must recall the missing word(s). This is Anki's most effective card type for grammar acquisition.

### Implementation
- New `cloze` type in CardRenderer
- Card data: `{text (with blanks marked as ___ ), answer, verse_ref}`
- On front: show verse with `[___]` replacing the target word
- On back: show the complete verse with the target word highlighted
- Generate from existing verses by masking specific words (e.g., the verb in each verse)

### Card Example
```
Front: "In the [___] God created the heaven and the earth."
Back:  "In the **beginning** God created the heaven and the earth." (Gen 1:1)
```

## 2. Frequency-Ordered Top 1000 Vocabulary (1h)

### What
The lexicon table already has frequency counts. This feature builds a structured "top 1000" vocabulary list ordered by biblical frequency, and creates cards for them.

### Implementation
- Query lexicon ORDER BY frequency DESC LIMIT 1000
- Skip function words (prepositions, particles, conjunctions — already known)
- Create `hebrew_vocab_frequency` table mapping lemma → rank
- Add "Most Frequent Words" section to HebrewLearnView
- Let users study in frequency order or by frequency range (top 100, 100-500, etc.)

### Top Words (Content Words)
```
1. יהוה (YHWH) — 5701 verses
2. בָּנִים (sons) — 3065 verses
3. כָּל (all) — 2812
4. אָמַר (said) — 2627
5. בָּא (came) — 1852
6. אֶרֶץ (land) — 1621
7. מֶלֶךְ (king) — 1529
8. עָשָׂה (made) — 1499
9. דָּבָר (word) — 1140
... 
```

## 3. Passage Study Mode (LingQ-Style) — CRITICAL (4h)

### What
User selects any passage → system parses every word → color-codes by known status → generates vocabulary cards from unknown words.

### Architecture
```
User selects passage
       │
       ▼
┌─────────────────────┐
│  Passage Reader      │  ← HebrewLearnView.jsx extension
│  (HebrewLearnView)   │
│                      │
│  gen.22.1-19         │
│  וַיְהִ֗י אַחַר֙     │  ← color-coded: green=known, red=new
│  הַדְּבָרִ֣ים הָאֵ֔לֶּה│
│  וְהָ֣אֱלֹהִ֔ים נִסָּ֖ה│
│  אֶת־אַבְרָהָ֑ם      │
│                      │
│  Click word → popup: │
│  נִסָּה (H5254)       │
│  "tested, tried"     │
│  Root: נסה           │
│  Occurrences: 36     │
│  +Add to vocab cards │  ← creates FSRS-5 cards
└─────────────────────┘
```

### Components
- `PassageReader.jsx` — renders passage with color-coded words
- `WordPopup.jsx` — already exists, extend with frequency data
- Backend: `GET /api/v1/passage/{book}.{ch}.{vs}-{end}` — returns parsed passage
- Backend: `GET /api/v1/passage/{book}.{ch}.{vs}/analyze` — word-by-word breakdown

## 4. Two-Way Translation Cards (2h)

### What
Instead of just showing Hebrew → English (recognition), also show English → Hebrew (production). The user sees an English phrase and must recall the Hebrew.

### Implementation
- New `translation` card type in CardRenderer
- Front: show English text
- Back: show Hebrew text + transliteration + audio
- Generate pairs from existing verse data (verse text is bilingual)
- FSRS-5 scheduling on production cards

## 5. Daily Maintenance Mode (2h)

### What
A "verse of the day" feature — one random verse per day with grammar notes, vocabulary breakdown, and audio. For users who've completed the curriculum.

### Implementation
- Backend: `GET /api/v1/hebrew/verse-of-day` — returns random verse with analysis
- Frontend: simple component showing the verse with word-by-word breakdown
- Add to HebrewLearnView as a new section
- Notification/sticky to encourage daily return

## 6. Audio-First / Commute Mode (3h)

### What
An eyes-free mode for walking/driving/exercising. Audio plays a Hebrew word/phrase → pause for user to recall → audio gives the answer → next.

### Implementation
- New `AudioReviewSession` component
- Uses existing TTS or pre-recorded audio
- CardQueue adaptation: show nothing on screen, just audio controls
- Track progress via FSRS-5 (same as visual cards)

## 7. Hebrew-Only Visual Mode (2h)

### What
Toggle on vocabulary cards to hide English translations. User sees only the Hebrew word and must recall the meaning. Optional: show an image instead of English.

### Implementation
- Add `hebrewOnly` prop to VocabCardRenderer
- When enabled: hide English definition, show only Hebrew + transliteration
- User reveals meaning by clicking/flipping the card
- Can be a per-user setting (stored in localStorage)
