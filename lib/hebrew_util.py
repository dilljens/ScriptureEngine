"""
Hebrew text utilities — transliteration, accent stripping, RTL-safe output.

Three improvements for terminal/plaintext display:

1. **strip_cantillation(text)** — remove trope marks (accents) for cleaner reading
2. **transliterate(text)** — simple letter-by-letter scholarly transliteration
3. **rtl_mark(text)** — wraps text with Unicode RTL markers for correct rendering
"""

import re
import unicodedata

# ── Unicode ranges ──────────────────────────────────────────────
CANTILLATION = set(range(0x0591, 0x05A2)) | {0x05A3, 0x05A4, 0x05A5, 0x05A6, 0x05A7, 0x05A8, 0x05A9, 0x05AA, 0x05AB, 0x05AC, 0x05AD, 0x05AE, 0x05AF}
# Everything between 0x0591-0x05AF is accents/cantillation
CANTILLATION_RANGE = range(0x0591, 0x05B0)
PUNCTUATION_HEB = {0x05C0, 0x05C3, 0x05C6, 0x05F3, 0x05F4}

# RTL marker
RLM = "\u200F"  # RIGHT-TO-LEFT MARK
LRM = "\u200E"  # LEFT-TO-RIGHT MARK

# ── Letter map (simple ASCII) ──────────────────────────────────
# For terminals w/o good Unicode support, fall back to ASCII
# When Unicode is available (default), use combining-diacritic chars

LETTER_MAP = {
    0x05D0: "ʾ",     # alef
    0x05D1: "b",     # bet (with dagesh) — we handle dagesh below
    0x05D2: "g",     # gimel
    0x05D3: "d",     # dalet
    0x05D4: "h",     # he
    0x05D5: "w",     # vav
    0x05D6: "z",     # zayin
    0x05D7: "ḥ",     # het (underdot h)
    0x05D8: "ṭ",     # tet (underdot t)
    0x05D9: "y",     # yod
    0x05DB: "k",     # kaf
    0x05DA: "k",     # final kaf
    0x05DC: "l",     # lamed
    0x05DE: "m",     # mem
    0x05DD: "m",     # final mem
    0x05E0: "n",     # nun
    0x05DF: "n",     # final nun
    0x05E1: "s",     # samekh
    0x05E2: "ʿ",     # ayin
    0x05E4: "p",     # pe (with dagesh)
    0x05E3: "p",     # final pe
    0x05E6: "ṣ",     # tsade (underdot s)
    0x05E5: "ṣ",     # final tsade
    0x05E7: "q",     # qof
    0x05E8: "r",     # resh
    0x05E9: "š",     # shin
    0x05EA: "t",     # tav
}

# Letters that change sound without dagesh (begadkefat)
BEGADKEFAT = {0x05D1: "ḇ", 0x05DB: "ḵ", 0x05E4: "p̄"}  # bet/vet, kaf/khaf, pe/fe
# Actually simpler: bet without dagesh = v, kaf without dagesh = kh, pe without dagesh = f
BEGADKEFAT_SOFT = {
    0x05D1: "v",    # bet → vet
    0x05DB: "ḵ",    # kaf → khaf
    0x05E4: "f",    # pe → fe
}

SHIN_SIN_DOT = {
    0x05C1: "š",    # shin dot (right) → sh
    0x05C2: "ś",    # sin dot (left) → s
}

# Vowel mapping
VOWEL_MAP = {
    0x05B0: "ə",   # sheva
    0x05B1: "ĕ",   # hataf segol
    0x05B2: "ă",   # hataf patah
    0x05B3: "ŏ",   # hataf qamats
    0x05B4: "i",   # hiriq
    0x05B5: "ē",   # tsere
    0x05B6: "e",   # segol
    0x05B7: "a",   # patah
    0x05B8: "ā",   # qamats
    0x05B9: "ō",   # holam (haser)
    0x05BA: "ō",   # holam (male) — only appears in fully pointed text
    0x05BB: "u",   # qubuts
}

# ── Functions ──────────────────────────────────────────────────

def strip_cantillation(text):
    """Remove cantillation/trope marks for cleaner reading.

    Keeps vowel points, dagesh, shin/sin dots — removes only accents.
    """
    return "".join(c for c in text if unicodedata.category(c) != "Mn"
                   or ord(c) not in CANTILLATION_RANGE)


def strip_vowels(text):
    """Remove all vowel pointing and accents — leaves bare consonants."""
    # Remove combining marks in Hebrew ranges (vowels + accents + dagesh)
    return "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
        and ord(c) not in {0x05C1, 0x05C2}  # keep shin/sin dots
    )


def clean_hebrew(text):
    """Clean up the database format: remove slashes, collapse whitespace."""
    text = text.replace("/", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def transliterate(text, strip_accents=True):
    """Convert pointed Hebrew text to scholarly transliteration.

    Handles mater lectionis (vav+holam=ō, yod+tsere=ê, etc.),
    begadkefat spirantization, and dagesh/shuruq.

    Args:
        text: Hebrew text (possibly with / separators from DB, cantillation, vowels)
        strip_accents: Remove cantillation marks (default: True)

    Returns:
        Transliterated string (left-to-right)
    """
    if not text:
        return ""

    text = clean_hebrew(text)

    result = []
    chars = list(text)
    i = 0
    n = len(chars)

    def _marks_set(pos):
        """Return set of combining-mark codepoints starting at pos, plus next pos."""
        s = set()
        while pos < n and unicodedata.category(chars[pos]) == "Mn":
            s.add(ord(chars[pos]))
            pos += 1
        return s, pos

    while i < n:
        cp = ord(chars[i])

        # ── Vowel points (before generic Mn skip) ──
        if cp in VOWEL_MAP:
            val = VOWEL_MAP[cp]
            # Check if this tsere/segol/hiriq is followed by yod mater
            if cp in (0x05B5, 0x05B6, 0x05B4):
                # Scan past combining marks to see if next letter is yod
                j = i + 1
                while j < n and unicodedata.category(chars[j]) == "Mn":
                    j += 1
                if j < n and ord(chars[j]) == 0x05D9:  # yod follows
                    # Suppress the yod — output the combined vowel
                    if cp == 0x05B5:
                        val = "ê"
                    elif cp == 0x05B6:
                        val = "e"
                    elif cp == 0x05B4:
                        val = "î"
                    i = j + 1  # skip yod too
                    result.append(val)
                    continue
            result.append(val)
            i += 1
            continue

        # ── Skip combining marks (dagesh, meteg, etc.) ──
        if unicodedata.category(chars[i]) == "Mn":
            i += 1
            continue

        # ── Skip spaces and DB separators ──
        if chars[i] in (" ", "/"):
            result.append(" ")
            i += 1
            continue

        # ── Shin (ש) — output consonant, let vowel marks through ──
        if cp == 0x05E9:
            # Look ahead for sin dot or dagesh
            sin_dot = False
            has_dagesh_shin = False
            j = i + 1
            while j < n and unicodedata.category(chars[j]) == "Mn":
                oc = ord(chars[j])
                if oc == 0x05C2:
                    sin_dot = True
                elif oc == 0x05BC:
                    has_dagesh_shin = True
                j += 1
            if sin_dot:
                result.append("ś")
            elif has_dagesh_shin:
                result.append("šš")  # geminated
            else:
                result.append("š")
            i += 1
            # Skip the next combining char if it's the dot or dagesh we consumed
            while i < n and ord(chars[i]) in {0x05C1, 0x05C2, 0x05BC}:
                i += 1
            continue

        # ── Letters (including mater lectionis detection) ──
        if cp in LETTER_MAP:
            marks_set, next_i = _marks_set(i + 1)
            has_dagesh = 0x05BC in marks_set
            has_holam = 0x05B9 in marks_set or 0x05BA in marks_set

            # ── Mater lectionis: output vowel, skip all combining marks ──
            # Vav (ו) + holam → ō
            if cp == 0x05D5 and has_holam:
                result.append("ō")
                i = next_i
                continue
            # Vav (ו) + dagesh → ū (shuruq)
            if cp == 0x05D5 and has_dagesh:
                result.append("ū")
                i = next_i
                continue
            # Yod (י) + tsere → ê
            if cp == 0x05D9 and 0x05B5 in marks_set:
                result.append("ê")
                i = next_i
                continue
            # Yod (י) + segol → e
            if cp == 0x05D9 and 0x05B6 in marks_set:
                result.append("e")
                i = next_i
                continue
            # Yod (י) + hiriq → î (word-final hireq-yod mater only)
            if cp == 0x05D9 and 0x05B4 in marks_set:
                # Only a mater if yod is word-final
                is_word_final = True
                j = next_i
                while j < n:
                    if chars[j] == " ":
                        j += 1
                        continue
                    if unicodedata.category(chars[j]) != "Mn":
                        is_word_final = False
                        break
                    j += 1
                if is_word_final:
                    result.append("î")
                    i = next_i
                    continue

            # ── Not a mater — output consonant ──
            if cp in BEGADKEFAT_SOFT and not has_dagesh:
                # Begadkefat soft: bet→v, kaf→ḵ, pe→f
                result.append(BEGADKEFAT_SOFT[cp])
            elif cp in BEGADKEFAT_SOFT:
                # Begadkefat hard (with dagesh): b, k, p (single, no gemination)
                result.append(LETTER_MAP[cp])
            elif has_dagesh and cp not in {0x05D0, 0x05D4, 0x05D7, 0x05E2, 0x05E8}:
                # Dagesh forte = gemination (double the consonant)
                # Gutturals (א, ה, ח, ע) and resh never geminate
                c = LETTER_MAP[cp]
                result.append(c + c)
            else:
                result.append(LETTER_MAP[cp])
            i += 1
            continue

        # ── Unknown — pass through ──
        result.append(chars[i])
        i += 1

    return "".join(result)


def rtl_mark(text):
    """Wrap text with Unicode RTL markers for correct terminal display.

    Use for any Hebrew text embedded in LTR output.
    """
    return f"{RLM}{text}{RLM}"


def ltr_mark(text):
    """Wrap plain text with LTR markers to reset direction."""
    return f"{LRM}{text}{LRM}"


def display_verse(text_hebrew, translit=None, fmt="text"):
    """Format Hebrew text for display, with optional transliteration.

    Args:
        text_hebrew: Hebrew text (possibly raw from DB with slashes)
        translit: Pre-computed transliteration (or None to compute)

    Returns:
        Formatted string safe for terminal/plaintext display
    """
    if not text_hebrew:
        return ""

    clean = clean_hebrew(text_hebrew)
    bare = strip_cantillation(clean)
    if translit is None:
        translit = transliterate(clean)

    return f"{rtl_mark(bare)} [{translit}]"
