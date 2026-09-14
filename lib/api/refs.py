"""Scripture reference helpers: D&C short-form aliases and display formatting.

The Doctrine and Covenants is the only work whose section is a book
(dc1..dc138), so its canonical ids repeat the number (dc121.121.7) while
every other work is book.chapter.verse. Callers shouldn't need a special
case per work; these helpers absorb it.
"""

import re

_DC_BOOK = re.compile(r"^dc(\d+)$", re.IGNORECASE)
_DC_BARE = re.compile(r"^d&c$", re.IGNORECASE)


def normalize_ref(ref: str, expect: str = "verse") -> str:
    """Expand D&C short forms to canonical verse/chapter ids.

    dc121.7   -> dc121.121.7   (the shape written by analogy with gen.1.1)
    dc.121.7 / D&C.121.7 -> dc121.121.7
    dc121     -> dc121.121     (chapter-level)
    dc.121    -> dc121.121     (chapter-level)
    dc121.121.7 (canonical) -> unchanged. Anything else -> unchanged.

    `dc1.1` is genuinely ambiguous (chapter dc1.1 vs verse dc1.1.1):
    verse routes read it as the verse, chapter routes as the chapter.
    """
    if not ref:
        return ref
    parts = ref.split(".")
    if len(parts) == 1:
        m = _DC_BOOK.match(parts[0])
        if m:
            return f"{parts[0]}.{m.group(1)}"  # dc121 -> dc121.121 (chapter-level)
        return ref
    if len(parts) == 2:
        book, second = parts
        m = _DC_BOOK.match(book)
        if m and second.isdigit():
            if expect == "chapter":
                return ref  # dc121.121 is the chapter; dc121.7 is meaningless here (404s downstream)
            # Verse route: dc121.7 is the verse in disguise — even when the
            # digits coincide (dc1.1 means verse dc1.1.1 to a verse route).
            return f"{book}.{m.group(1)}.{second}"
        if (book == "dc" or _DC_BARE.match(book)) and second.isdigit():
            return f"dc{second}.{second}"
        return ref
    if len(parts) == 3:
        book, ch, vs = parts
        if (book == "dc" or _DC_BARE.match(book)) and ch.isdigit() and vs.isdigit():
            return f"dc{ch}.{ch}.{vs}"
        return ref
    return ref


def format_reference(book_title: str, verse_id: str, chapter, verse) -> str:
    """Human reference string without the D&C doubled number.

    "Doctrine and Covenants 121" + chapter 121 -> "Doctrine and Covenants
    121:7" (not "...121 121:7"). Every other work formats as before.
    """
    title = book_title or ""
    m = _DC_BOOK.match((verse_id or "").split(".")[0])
    if m:
        suffix = f" {m.group(1)}"
        if title.endswith(suffix):
            title = title[: -len(suffix)]
    return f"{title} {chapter}:{verse}"


# Measured MT-minus-KJV offsets (inbox report-api-followup-2026-08-30: verse
# counts per psalm/chapter walked to the last verse in both schemes).
# A superscription does NOT predict the shift (psalms 50/66/78/86 carry titles
# without shifting); only the counts decide. Unlisted psalms/chapters are
# UNMEASURED — callers must check, never assume.
MEASURED_OFFSETS = {
    ("psa", 49): 1, ("psa", 50): 0, ("psa", 51): 2,
    ("psa", 61): 1, ("psa", 62): 1, ("psa", 63): 1, ("psa", 64): 1,
    ("psa", 65): 1, ("psa", 66): 0, ("psa", 69): 1, ("psa", 70): 1,
    ("psa", 71): 0, ("psa", 72): 0, ("psa", 77): 1, ("psa", 78): 0,
    ("psa", 85): 1, ("psa", 86): 0,
    ("jonah", 1): -1, ("jonah", 2): 1,
}

OFFSET_BOOKS = ("psa", "jonah")


def versification_offset(book: str, chapter) -> int | None:
    """MT-minus-KJV verse offset for (book, chapter), or None if unmeasured."""
    try:
        return MEASURED_OFFSETS.get(((book or "").lower(), int(chapter)))
    except (ValueError, TypeError):
        return None


def versification_block(book: str, chapter) -> dict | None:
    """Payload block disclosing the interlinear numbering for a ref.

    Returns None outside psalms/Jonah (general caution lives in orient/refs).
    A measured offset names the number; an unmeasured psalm says the offset
    varies 0-2 and must be checked — never a confident wrong rule.
    """
    if (book or "").lower() not in OFFSET_BOOKS:
        return None
    offset = versification_offset(book, chapter)
    base = {
        "english_scheme": "kjv",
        "interlinear_scheme": "mt",
        "offset": offset,
        "see": "/api/v1/orient/refs",
    }
    if offset is None:
        base["note"] = ("Offset unmeasured for this psalm (0-2 observed): "
                        "verify word studies against both numbers.")
    elif offset == 0:
        base["note"] = "Schemes aligned for this chapter — no shift."
    else:
        sign = f"{offset:+d}"
        base["note"] = (f"For this chapter the interlinear (MT) index is KJV {sign}.")
    return base
