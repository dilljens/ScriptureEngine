"""Temurah (תמורה) — letter substitution ciphers beyond Atbash.

The Kabbalistic tradition of Temurah includes several letter-substitution
methods for revealing hidden meanings in Hebrew text:

  - **Albam** (אלב"ם): Split alphabet in half (11 letters each), map
    first half onto second half. א→ל, ב→מ, ג→נ ... ל→א, מ→ב, נ→ג
  - **Atbah** (אטב"ח): Within-half mirroring. א↔ט, ב↔ח, ג↔ז, ד↔ו, ה↔ה
  - **Avgad** (אבג"ד): Shift by one. א→ב, ב→ג, ג→ד ... ת→א
  - **Atbash** (אתב"ש): Already implemented in atbash.py — first↔last letter
"""

ALEPH_BET = list("אבגדהוזחטיכלמנסעפצקרשת")

# Map final forms to their standard equivalent
FINAL_MAP = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}
FINAL_REVERSE = {'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פ': 'ף', 'צ': 'ץ'}


def _extract_letters(text):
    """Extract Hebrew consonants from text, converting final forms to standard."""
    letters = []
    for ch in text:
        cp = ord(ch)
        if 0x05D0 <= cp <= 0x05EA:
            letters.append(FINAL_MAP.get(ch, ch))
        elif 0x05EF <= cp <= 0x05F2:
            letters.append(ch)
    return letters


def _restore_final(letter, original_idx, original_letters):
    """Restore final form if the original had one."""
    if letter in FINAL_REVERSE:
        # Check if this was a final form in original
        orig = original_letters[original_idx] if original_idx < len(original_letters) else letter
        for f, std in FINAL_MAP.items():
            if std == letter and orig == f:
                return f
    return letter


def decode_albam(text):
    """Albam (אלב"ם) — split alphabet in half, map across.

    First half (letters 1-11): אבגדהוזחטיכ
    Second half (letters 12-22): למנסעפצקרשת

    א→ל, ב→מ, ג→נ, ... ל→א, מ→ב, נ→ג, ...

    Named after the first pair: אלב"ם (Aleph→Lamed, Bet→Mem)
    """
    half = 11  # 22 letters / 2
    result = []
    for ch in text:
        cp = ord(ch)
        letter = FINAL_MAP.get(ch, ch) if (0x05D0 <= cp <= 0x05EA) else ch
        if letter in ALEPH_BET:
            idx = ALEPH_BET.index(letter)
            new_idx = (idx + half) % 22
            mirrored = ALEPH_BET[new_idx]
            # Restore final forms
            if ch in FINAL_MAP:
                mirrored = FINAL_REVERSE.get(mirrored, mirrored)
            result.append(mirrored)
        else:
            result.append(ch)
    return "".join(result)


def decode_atbah(text):
    """Atbah (אטב"ח) — within-half mirrored pairs.

    Split into 5 pairs of 2 + 2 unpaired middle letters:
    א↔ט, ב↔ח, ג↔ז, ד↔ו, ה↔ה, י↔י, כ↔כ, ל↔ל, מ↔מ, נ↔נ, ס↔ס, ע↔ע,
    פ↔פ, צ↔צ, ק↔ק, ר↔ר, ש↔ש, ת↔ת

    Actually the traditional Atbah is: א=ט, ב=ח, ג=ז, ד=ו, ה=ה (and beyond that,
    letters map to themselves). So it's only the first 5 pairs.
    """
    # Atbah pairs: א↔ט, ב↔ח, ג↔ז, ד↔ו, ה↔ה
    atbah_map = {
        'א': 'ט', 'ט': 'א',
        'ב': 'ח', 'ח': 'ב',
        'ג': 'ז', 'ז': 'ג',
        'ד': 'ו', 'ו': 'ד',
        'ה': 'ה',  # self-mapping
    }
    # Letters beyond the first 5 pairs map to themselves
    for letter in ALEPH_BET:
        if letter not in atbah_map:
            atbah_map[letter] = letter

    result = []
    for ch in text:
        cp = ord(ch)
        letter = FINAL_MAP.get(ch, ch) if (0x05D0 <= cp <= 0x05EA) else ch
        if letter in atbah_map:
            mirrored = atbah_map[letter]
            if ch in FINAL_MAP:
                mirrored = FINAL_REVERSE.get(mirrored, mirrored)
            result.append(mirrored)
        else:
            result.append(ch)
    return "".join(result)


def decode_avgad(text):
    """Avgad (אבג"ד) — shift each letter forward by one position.

    א→ב, ב→ג, ג→ד, ... ת→א

    Named after the first pair: אבג"ד (Aleph→Bet, Bet→Gimel, Gimel→Dalet)
    """
    result = []
    for ch in text:
        cp = ord(ch)
        letter = FINAL_MAP.get(ch, ch) if (0x05D0 <= cp <= 0x05EA) else ch
        if letter in ALEPH_BET:
            idx = ALEPH_BET.index(letter)
            new_idx = (idx + 1) % 22
            shifted = ALEPH_BET[new_idx]
            if ch in FINAL_MAP:
                shifted = FINAL_REVERSE.get(shifted, shifted)
            result.append(shifted)
        else:
            result.append(ch)
    return "".join(result)


# Also add the reverse shift (Avgad backwards)
def decode_avgad_reverse(text):
    """Reverse Avgad — shift each letter back by one position.

    א→ת, ב→א, ג→ב, ... ת→ש
    """
    result = []
    for ch in text:
        cp = ord(ch)
        letter = FINAL_MAP.get(ch, ch) if (0x05D0 <= cp <= 0x05EA) else ch
        if letter in ALEPH_BET:
            idx = ALEPH_BET.index(letter)
            new_idx = (idx - 1) % 22
            shifted = ALEPH_BET[new_idx]
            if ch in FINAL_MAP:
                shifted = FINAL_REVERSE.get(shifted, shifted)
            result.append(shifted)
        else:
            result.append(ch)
    return "".join(result)


# Registry of all temurah ciphers for discovery
TEMURAH_CIPHERS = {
    "atbash": {"name": "Atbash", "func": None, "description": "First↔last letter mirror"},  # imported from atbash.py
    "albam": {"name": "Albam", "func": decode_albam, "description": "Split alphabet in half, map across"},
    "atbah": {"name": "Atbah", "func": decode_atbah, "description": "First 5 letter pairs mirrored"},
    "avgad": {"name": "Avgad", "func": decode_avgad, "description": "Shift forward by 1"},
    "avgad_reverse": {"name": "Avgad Reverse", "func": decode_avgad_reverse, "description": "Shift backward by 1"},
}
