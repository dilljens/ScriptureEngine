"""Split scripture verses into poetic lines (cola/stichs).

Strategy:
  English: split on ; then : (strong line boundaries).
           Avoid splitting after speech introducers ("said:", "crying:", etc.).
           If no strong boundary, split on , before clause conjunctions.
  Hebrew:  split on atnach (֑) and other major disjunctive accents.
           Remove WLC / prefix markers for clean display.

  If English and Hebrew line counts diverge, align by merging or falling
  back to a single block.
"""

import re

# ── Hebrew accent / pause markers ──

# Major disjunctive accents that mark poetic line breaks in Hebrew.
# Only etnachta (֑, U+0591) is the reliable mid-verse caesura marker.
# Other disjunctives (zinqa, tippa, etc.) are too granular for poetic lines.
ETNACHTA = "֑"

# ── Speech introducers — don't split after these ──

SPEECH_INTRODUCERS = re.compile(
    r'(said|saith|saying|cried|crying|crieth|spake|spoke|answered|reply|'
    r'responded|asked|began|continued|wrote|prophesied)\s*[:;]',
    re.IGNORECASE,
)

# ── Clause conjunctions that might indicate a parallel line ──

CLAUSE_CONJUNCTIONS = re.compile(
    r'^\s*(and|but|for|yet|so|then|nor|or|neither|that|when|where|'
    r'therefore|wherefore|nevertheless|howbeit|behold)\b',
    re.IGNORECASE,
)

# Imperative verbs that start parallel poetic lines (common in KJV poetry)
PARALLEL_IMPERATIVES = re.compile(
    r'^\s*(seek|call|hear|harken|go|come|make|let|take|give|bring|cast|'
    r'put|set|turn|lift|raise|praise|sing|shout|tell|declare|prepare|'
    r'remember|forget|fear|trust|wait|look|see|behold|arise|awake|stand|'
    r'know|consider|think|do|keep|observe|love|hate|chose|choose|follow)\b',
    re.IGNORECASE,
)

# Possessive adjectives that start a parallel noun phrase (appositive parallelism)
# e.g., "but Israel doth not know, my people doth not consider"
POSSESSIVE_ADJECTIVES = re.compile(
    r'^\s*(my|thy|his|her|our|your|their|its)\b',
    re.IGNORECASE,
)


def clean_hebrew(text):
    """Remove WLC / prefix markers for display."""
    if not text:
        return ""
    return text.replace("/", "")


def split_english(text):
    """Split English verse text into poetic lines.

    Two-level split:
      1. Split on ; then : for major poetic lines
      2. Within each major line, split on , + conjunction/imperative for sub-lines

    Returns list of (cleaned) line strings, or [text] if no split.
    """
    if not text:
        return [""]

    # Step 1: Split on ; then : for major poetic boundaries
    major = _split_on_punctuation(text)
    major = [p.strip() for p in major if _is_valid_line(p)]

    # Step 2: Within each major line, try comma-conjunction splitting
    result = []
    for part in major:
        sub = _split_on_comma_conjunctions(part)
        if len(sub) >= 2:
            valid_sub = [s.strip() for s in sub if _is_valid_line(s)]
            if len(valid_sub) >= 2 and _is_balanced_split(valid_sub):
                result.extend(valid_sub)
            else:
                result.append(part)
        else:
            result.append(part)

    # Validate the full result: max 6 lines
    if 2 <= len(result) <= 6:
        word_counts = [len(l.split()) for l in result]
        if all(w >= 2 for w in word_counts) and _is_balanced_split(result):
            return result

    # Too many lines from two-level split — use only the punctuation split
    if len(major) >= 2:
        word_counts = [len(l.split()) for l in major]
        if all(w >= 2 for w in word_counts) and _is_balanced_split(major):
            return major

    # Fallback: try comma-conjunction on the full text directly
    parts = _split_on_comma_conjunctions(text)
    if len(parts) >= 2:
        valid = [p.strip() for p in parts if _is_valid_line(p)]
        if 2 <= len(valid) <= 6 and _is_balanced_split(valid):
            word_counts = [len(l.split()) for l in valid]
            if all(w >= 2 for w in word_counts):
                return valid

    return [text.strip()]


def split_hebrew(text):
    """Split Hebrew verse text into poetic lines.

    Uses etnachta (֑, U+0591) as the primary mid-verse pause marker.
    Splits at WORD boundaries (spaces), not mid-word.
    Returns list of (cleaned, /-removed) line strings, or [text] if no split.
    """
    if not text:
        return [""]

    cleaned = clean_hebrew(text)

    # Find words that contain etnachta (the reliable poetic caesura)
    words = cleaned.split()
    split_after = []
    for i, word in enumerate(words):
        if ETNACHTA in word:
            split_after.append(i)

    if split_after:
        parts = []
        start = 0
        for idx in split_after:
            part = " ".join(words[start:idx + 1])
            if part.strip():
                parts.append(part.strip())
            start = idx + 1
        remaining = " ".join(words[start:])
        if remaining.strip():
            parts.append(remaining.strip())

        if len(parts) >= 2:
            # Validate: each part should have at least 2 real words
            valid = [p for p in parts if len(p.split()) >= 1]
            if len(valid) >= 2:
                return valid

    # Fallback: split on sof pasuq (׃) — verse-final marker
    parts = [p.strip() for p in cleaned.split("׃") if p.strip()]
    if len(parts) >= 2:
        return parts

    return [cleaned.strip()]


def split_verse(text_english, text_hebrew):
    """Split a verse into aligned poetic lines.

    Returns list of dicts:
        {"english": str, "hebrew": str}

    If alignment fails, returns [{"english": text_english, "hebrew": clean_hebrew(text_hebrew)}]
    """
    en_lines = split_english(text_english)
    he_lines = split_hebrew(text_hebrew)

    # Strategy: use English as the authoritative split.
    # If Hebrew aligns, use it. If not, duplicate Hebrew across English lines.

    # Perfect alignment
    if len(en_lines) == len(he_lines):
        return [
            {"english": en.strip(), "hebrew": he.strip()}
            for en, he in zip(en_lines, he_lines)
        ]

    # Use English lines with Hebrew duplicated across each
    heb_full = he_lines[0] if he_lines else clean_hebrew(text_hebrew)
    result = [{"english": en.strip(), "hebrew": heb_full} for en in en_lines]
    if len(result) >= 2:
        return result  # English split is authoritative

    # Use Hebrew lines with English duplicated across each
    # Only do this if the English has clear poetic markers (colons, semicolons)
    # to avoid splitting narrative verses based on Hebrew accent marks.
    if re.search(r'[;:]', text_english):
        eng_full = en_lines[0] if en_lines else text_english.strip()
        result = [{"english": eng_full, "hebrew": he.strip()} for he in he_lines]
        if len(result) >= 2:
            return result

    # Fallback: single block
    return [{"english": text_english.strip(), "hebrew": clean_hebrew(text_hebrew).strip()}]


# ── Internal helpers ──


def _split_on_punctuation(text):
    """Split on ; then :, avoiding speech introducers."""
    # First pass: split on ;
    parts = re.split(r";", text)
    # Second pass: split each part on : (if not after a speech introducer)
    result = []
    for part in parts:
        sub = re.split(r":(?!.*\))", part)  # Simple colon split
        # Check for speech introducers and re-join if needed
        merged = []
        for s in sub:
            if merged and SPEECH_INTRODUCERS.search(merged[-1]):
                merged[-1] = merged[-1] + ": " + s
            else:
                merged.append(s)
        result.extend(merged)
    return result


def _split_on_comma_conjunctions(text):
    """Split on comma followed by a clause or imperative parallel line.

    Looks for:
      1. Comma + clause conjunction ('and', 'but', 'for', etc.)
      2. Comma + imperative verb ('Seek', 'Call', 'Hear', etc.)
      3. Comma + possessive adjective noun phrase ('my', 'thy', 'his', etc.)
    """
    result = []
    last_end = 0
    for m in re.finditer(r",", text):
        after = text[m.end():].lstrip()
        if (CLAUSE_CONJUNCTIONS.match(after)
            or PARALLEL_IMPERATIVES.match(after)
            or POSSESSIVE_ADJECTIVES.match(after)):
            result.append(text[last_end:m.start()].strip())
            last_end = m.end()
    result.append(text[last_end:].strip())
    result = [r for r in result if r]
    return result if len(result) >= 2 else [text]


def _is_valid_line(text):
    """Check if text is a valid poetic line (not too short, has real content)."""
    words = text.strip().split()
    return len(words) >= 2 and any(len(w) > 2 for w in words)


def _is_balanced_split(lines):
    """Check that the split is balanced — no line is disproportionately short.

    This prevents narrative continuation from being treated as a poetic line.
    E.g., 'and his train filled the temple' (6 words) vs 'In the year...' (16 words) → reject.
    For 3+ lines, assume intentional poetic structure.
    """
    if len(lines) < 2:
        return True
    word_counts = [len(l.split()) for l in lines]
    max_w = max(word_counts)
    min_w = min(word_counts)

    # For 2-line splits: check that the shorter line isn't too short
    # (catches narrative continuation like 'and his train filled the temple')
    if len(lines) == 2:
        if min_w < 3:
            return False
        if max_w > 8 and min_w / max_w < 0.4:
            return False

    # For 3+ lines: only reject if any line is truly trivial (1 word)
    return all(w >= 2 for w in word_counts)


def _align_by_merge(more_lines, fewer_lines, hebrew_first=False):
    """Merge smaller lines in `more_lines` to match count of `fewer_lines`."""
    if len(fewer_lines) == 0:
        return None

    target_count = len(fewer_lines)
    # Greedy merge: combine smallest adjacent lines until we reach target_count
    merged = list(more_lines)
    while len(merged) > target_count:
        # Find the shortest adjacent pair
        best_idx = 0
        best_len = float("inf")
        for i in range(len(merged) - 1):
            pair_len = len(merged[i]) + len(merged[i + 1])
            if pair_len < best_len:
                best_len = pair_len
                best_idx = i
        # Merge
        merged[best_idx] = merged[best_idx] + " " + merged[best_idx + 1]
        del merged[best_idx + 1]

    if hebrew_first:
        return [
            {"english": en.strip(), "hebrew": he.strip()}
            for he, en in zip(merged, fewer_lines)
        ]
    else:
        return [
            {"english": en.strip(), "hebrew": he.strip()}
            for en, he in zip(merged, fewer_lines)
        ]
