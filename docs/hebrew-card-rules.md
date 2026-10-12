# Hebrew Flashcard Rules

Derived from the Schwartz-Groves Westminster Hebrew Vocabulary deck
(`Biblical Hebrew Vocabulary (WHV)` — 686 headwords × 3 directions + 1
info card). Every future Hebrew vocab card set MUST follow these rules
so cards stay consistent with each other and with the app's FSRS scheduler.

## 1. Three directions per headword — no exceptions

Every headword ships all three (Anki ord 0/1/2; app modes
`forward` / `reverse` / `hearing`):

| # | Direction | Front (question) | Back (answer) |
|---|-----------|------------------|---------------|
| 1 | Hebrew → English (`forward`) | Hebrew writing only | Audio + gloss + metadata (rule 2) |
| 2 | English → Hebrew (`reverse`) | Primary + additional gloss | Audio + Hebrew writing |
| 3 | Sound → English (`hearing`) | Audio autoplay only; Hebrew writing hidden behind a hint | Full answer: writing + glosses + metadata |
| 4 | Picture → Hebrew (`picture`) | Deck picture only (Tier-0 png) | Full answer: writing + glosses + metadata |

Why: recognition (He→En), production (En→He), and listening (Sound→En)
are separate memory traces. The scheduler tracks each `(node, mode)` pair
independently (`hebrew_review_state`), so a word can be mature in one
direction and new in another.

Direction 4 is conditional: only headwords with a Tier-0 deck picture
(WHV: 683/686) draw picture cards. Imageless words practice the other
three — never deal a blank front (`modesForCard` in `AnkiReview.jsx`).

## 2. Front = stimulus only; back = everything

- Front shows ONE stimulus. Never show the answer on the front (no gloss
  on He→En fronts, no Hebrew on En→He fronts, no writing on audio fronts).
- Back always shows: Hebrew writing, audio replay, primary gloss,
  additional glosses, frequency data (`#rank | word class | N×`), notes.
- Audio fronts MUST autoplay and offer replay ("r" key convention).

## 3. Required fields per note

`Hebrew Text` (headword, pointed), `Frequency Sequence` (rank),
`Primary Gloss(es)`, `Additional Gloss(es)`, `Notes`, `Word Class`,
`Occurrences`, `Hebrew Writing` (image or styled text), `Hebrew Audio`
(`[sound:file.mp3]`).

## 4. Media conventions

- One audio clip per headword, named `<headword>.mp3` (e.g. `אֱלֹהִים.mp3`).
- One image per headword, named `<headword>.png`.
- Import path: `scripts/import_apkg_pack.py <deck>.apkg --apply`
  → `data/audio/anki/<hebrew>__<orig>.mp3` + `manifest.json`
  (gitignored; Anki shared decks are personal-study only, never commit).
  Per-pack user-import guide (Hackett/BBH2): `docs/hebrew-pack-imports.md`.
- The `/hebrew/audio/{word}` endpoint serves manifest audio as Tier-0.

## 5. No boilerplate cards

Exactly one deck-info card max (the WHV deck has 1). Never generate
per-word info cards — metadata lives on the back of real cards.

## 6. Scheduling

- Per-direction FSRS state; do NOT share intervals across directions.
- Mastered = interval ≥ 21 days (`WORD_MATURE_INTERVAL_DAYS`), per direction.
- New cards enter all available directions unless `due_modes` says otherwise
  (picture only where a Tier-0 png exists).

## 7. App mapping

- `AnkiReview.jsx` `CARD_MODES = ['hearing', 'reverse', 'forward', 'picture']`
  is the reference renderer. New modes need a backend `card_mode`
  allowlist entry (intervals + review submit in `web/routes/hebrew.py`).
  `picture` is deliberately NOT in backend `CARD_MODES` — the scheduler
  never auto-deals it; the frontend adds it only where a Tier-0 picture
  exists, and the queue surfaces due `picture` rows once rated.
- Cards without a curriculum `node_id` MUST still send `hebrew` text (plus
  Strong's `lemma` when known) in review/interval calls — the backend
  resolves exact → folded (niqqud-stripped) → affix-strip → lemma → LIKE.
