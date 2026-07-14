# Progress: Hebrew Learning & UI Fixes

## Session 2026-07-14
- Current track: None yet (planning phase)
- [ ] Track A: Audio & Letter Pronunciation (not started)
- [ ] Track B: Practice Item Content Quality (not started)
- [ ] Track C: Hebrew Keyboard Vowels (not started)
- [ ] Track D: Memorize Verse Click & Review (not started)
- [ ] Track E: Top Bar Tab Labeling (not started)
- [ ] Track F: Navigation & Command Button (not started)
- [ ] Track G: Verse Ref Formatting (not started)
- [ ] Track H: Scripture Letter Recognition (not started)

## Key Findings
- 428 practice items across `hebrew_practice_items` table, 8 per consonant/vowel node
- ~47 letter/vowel nodes with 8 items each = 376 items needing the most urgent fix
- OmniVoice pipeline already exists at `scripts/generate_audio.py` with voice cloning
- HebrewKeyboard has 27 consonant buttons, zero vowel support
- MemorizeQueue verse cards have no onClick handler
- Top bar unconditionally shows breadcrumb regardless of tab type
- Verse refs use raw dot format (gen.1.1) instead of book names (Genesis 1:1)

## Decisions Made
- All tracks independent (no cross-track dependencies)
- Priority order: B (content quality) → C (keyboard) → A (audio) → D (memorize) → E (top bar) → G (verse refs) → H (letter recognition) → F (navigation)
- Practice items: fix in DB migration script, not in frontend
- Audio: generate once, serve as static files
