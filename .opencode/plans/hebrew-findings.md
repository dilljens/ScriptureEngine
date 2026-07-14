# Findings: Hebrew Learning & UI Fixes

## Requirements (from user)
1. **Memorize verse click does nothing** → Add quick review popup for single verse
2. **Review should work like Anki** → Target language first, language swap resets mastery
3. **Audio for letters doesn't work** → Pre-generate via OmniVoice voice cloning from Schmueloff recordings
4. **Letter recognition shows English not Hebrew** → Display Hebrew with letter highlighted
5. **Verse refs show gen.1.2 not Genesis 1:2** → Format refs with full book names
6. **Hebrew keyboard has no vowels** → Add toggle row + long-press vowel popup
7. **Transliteration/multiple choice give away answer** → Fix all 428 practice items
8. **Top bar shows OT Genesis on Hebrew tab** → Show tab label for non-chapter views
9. **Two sets of arrows** → Keep arrows + add command/nav button + wiki button
10. **Review all hebrew learning content quality** → Full practice item audit (included in #7)

## Pre-resolved Decisions

### Audio: Letter pronunciation via OmniVoice cloning
- Existing `scripts/generate_audio.py` already uses OmniVoice (`k2-fsa/OmniVoice`) with voice cloning via reference audio (`data/audio/clone/schmueloff_8s.wav`)
- Will write `scripts/generate_letter_audio.py` following the same pattern
- Output: `data/audio/letters/{letter_id}.wav` (e.g., `aleph.wav`, `bet.wav`)
- Letter names will be spoken in Hebrew with Schmueloff's voice
- Audio endpoint needs fallback to serve these files

### Keyboard vowels: Toggle row + long-press
- Current `HebrewKeyboard.jsx` has 3 rows, 27 consonant buttons, NO vowels
- Vowel row (toggleable): ְ ֻ ֹ ִ ֶ ַ ָ ֵ ּ ֶ ֱ ֲ ֳ
- Long-press: Hold consonant 500ms → popup shows that consonant with common vowel combinations
- Both approaches implemented

### Practice item audit (428 items in hebrew_practice_items)
Key issues found per category:
- **consonant (224 items / 28 nodes × 8)**: Question text gives away answer (e.g., "What is the name of this Hebrew letter: Ayin?" with options including "Ayin")
- **vowel (152 items / 19 nodes × 8)**: Same pattern as consonants
- **word (518 nodes but only some have items)**: Need to check — likely similar issues
- All 4 question types affected: multiple_choice, transliteration, typing, recall

### Memorize queue click → quick review
- `MemorizeQueue.jsx` currently has no onClick on verse cards
- `CardQueue.jsx` already supports single-card review
- Adding reviewVerse state + inline CardQueue for single verse

### Top bar tab naming
- Current: toolbar shows breadcrumb (Work/Book/Chapter) regardless of view
- Fix: When viewLevel not in ['chapter', 'book', 'work'], show tab.label instead
- Tab labels are already set correctly in tabContext.jsx (e.g., "Biblical Hebrew")

### Verse ref formatting
- Book ID → Display Name mapping exists in `books` table in scripture.db
- e.g., `gen` → `Genesis`, `exo` → `Exodus`
- Will use a lookup object in the frontend

## Architecture Notes

### Practice item fix approach
```python
# scripts/fix_hebrew_practice_items.py
for each item:
  if node_category in ('consonant', 'vowel'):
    if type == 'multiple_choice':
      # Old: "What is the name of this Hebrew letter: Ayin?"
      # New: "What is the name of this Hebrew letter: ע?"
      question_text = question_text.rsplit(': ', 1)[0] + ': ' + hebrew_char
      # Verify options don't reveal the answer trivially
    elif type == 'transliteration':
      # Old: "How is this letter transliterated: Ayin?"
      # New: "How is ע transliterated?"
    elif type == 'typing':
      # Old: "Type the Hebrew letter: Ayin" answer=Ayin
      # New: "Type the Hebrew letter named Ayin: ___" answer=ע
    elif type == 'recall':
      # Old: "What is the Hebrew letter named 'Ayin'?" answer=Ayin
      # New: "What Hebrew letter is this: ע?" answer=Ayin
```

### OmniVoice letter generation approach
```python
# scripts/generate_letter_audio.py
model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda:0")
for letter_id, hebrew_char, name in letters:
    text = f"{hebrew_char} — {name}"  # e.g., "א — Aleph"
    audio = model.generate(text=text, ref_audio="data/audio/clone/schmueloff_8s.wav", speed=1.0)
    sf.write(f"data/audio/letters/{letter_id}.wav", audio[0], 24000)
```

### Audio endpoint update
```python
# In web/routes/hebrew.py, get_hebrew_audio()
# After existing lookups fail, before raising 404:
letter_path = BASE_DIR / "data" / "audio" / "letters" / f"{word_clean}.wav"
if letter_path.exists():
    return {"ok": True, "data": {
        "audio_url": f"/api/v1/audio/play-raw/letters/{word_clean}.wav",
        "word": word_clean, "source": "letters",
    }}
```

## Open Questions → Resolved
- Q: Audio for letters — how to generate? → A: Use existing OmniVoice pipeline with voice cloning from Schmueloff reference
- Q: Practice item scope? → A: Full audit, all 428 items
- Q: Memorize click behavior? → A: Quick review popup (single card)
- Q: Top bar behavior? → A: Show tab label for non-chapter views
- Q: Keyboard vowels? → A: Both toggle row and long-press
- Q: Navigation buttons? → A: Keep arrows + add command/nav button + wiki button
- Q: Verse ref formatting? → A: Use book title mapping from DB
