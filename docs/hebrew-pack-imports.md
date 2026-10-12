# Hebrew Pack Imports (user-local)

Anki shared decks are **personal study only** — never commit `.apkg`
files, `data/audio/`, or generated TTS/weights. The repo stores scripts
+ manifests only; you reproduce media locally with one command per pack.
This applies to third-party AND generated audio alike.

## Generic path (every pack)

```bash
python3 scripts/import_apkg_pack.py ~/Downloads/<deck>.apkg --dry-run
python3 scripts/import_apkg_pack.py ~/Downloads/<deck>.apkg --pack <name> --apply
```

`--dry-run` prints the deck's real note types, field names, tags, and
media kinds — correct the `--pack` preset (or pass `--hebrew-field` /
`--gloss-field` / `--exclude-tag` / `--exclude-media` explicitly) and
re-run. `--apply` writes gitignored `data/audio/anki/*.mp3` +
`manifest.json` and prints `pack.json` (`{hebrew, gloss, audio, images}`
per note) for vocab seeding. Verify counts + manifest; `git status`
must show nothing under `data/audio/`.

## Hackett (`--pack hackett`)

- Source: "Biblical Hebrew, A Basic Introduction to, by Jo Ann Hackett
  — 950+ cards", AnkiWeb shared deck
  <https://ankiweb.net/shared/info/1662721723>
  (download via Anki Desktop → Tools → Get Shared Decks, or the
  AnkiWeb page; save the `.apkg`, then run the importer above).
- Content: every Hackett vocab word, chapter-tagged, with picture cards
  and audio — most audio clips are Allen Ross recordings (third-party
  terms), plus some author-recorded clips.
- The `hackett` preset pre-filters Ross-sourced media
  (`--exclude-media ross --exclude-media Ross`); keep it unless you
  have verified the terms on those clips. Field names are best-effort —
  `--dry-run` first, the deck's real fields win.
- Expected yield: ~hundreds of notes (deck reports 220 notes / 456+
  cards at last polish pass, growing to 950+ cards); check the dry-run
  counts against the deck description before `--apply`.

## BBH2 / Basics of Biblical Hebrew (`--pack bbh2`)

- Same generic path; no vendored source in repo. Download the BBH2
  shared `.apkg` yourself, `--dry-run` to discover its fields, then
  `--pack bbh2 --apply` (override fields explicitly if dry-run
  disagrees with the preset).
- Fallback if no usable shared deck exists: a spreadsheet/CSV wordlist
  through the same field map (`--hebrew-field` / `--gloss-field`);
  the importer is field-generic by design (A1).

## After import

`pack.json` is the seeding input; the current vocab backbone is the
in-repo lexicon frequency list (`seed_hebrew_vocabulary.py`), so a new
pack proves the importer first (manifest + counts) and seeds second.
Card rules for anything seeded: `docs/hebrew-card-rules.md`.
