"""Deterministic citation checks for chat answers (plan Track A3, stage 1).

Stage 1 is mechanical by design: every direct quotation that sits next to a
verse reference must actually appear in that verse's retrieved text. This
catches the most damaging failure class — a real-looking quotation attached
to the wrong verse, or to no verse at all — without an LLM in the loop and
without exposing any chain-of-thought. NLI-style entailment remains a later
stage per the plan's fallback ordering.

Pure functions only: the caller supplies how verse text is fetched, so this
module stays unit-testable and dependency-free.
"""

import re
from typing import Any, Callable, Optional

# Dotted book refs: gen.1.1, 1ne.4.3, dc88.88.67 (numeric-capable book ids).
_REF_RE = re.compile(r"\b([1-3]?[a-z0-9]{2,5})\.(\d{1,3})\.(\d{1,3})\b")

# Curly or straight double-quoted spans plausibly quotations (word-count
# gating happens after normalization, so this floor stays low).
_QUOTE_RE = re.compile(r"[“\"]([^“\"]{12,400})[“\"]")

# Anything that is not a word character or whitespace breaks matching.
_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)

# Verse-text elisions inside a quotation.
_ELLIPSIS_RE = re.compile(r"\s*(\.{3,}|…)\s*")

MIN_QUOTE_WORDS = 4
WINDOW_CHARS = 160  # how far from a quotation a ref may sit


def normalize(text: Optional[str]) -> str:
    """Casefolded, punctuation-stripped, whitespace-collapsed text."""
    if not text:
        return ""
    return " ".join(_NON_WORD_RE.sub(" ", text.casefold()).split())


def extract_refs(text: str) -> list[str]:
    """Unique dotted verse refs in first-seen order."""
    seen: dict[str, None] = {}
    for m in _REF_RE.finditer(text or ""):
        seen.setdefault(m.group(0), None)
    return list(seen)


def _fragments(raw_quote: str) -> list[str]:
    """Split an elided quotation on its ellipses FIRST, then normalize each
    fragment — normalizing before splitting would erase the ellipses."""
    parts = [p for p in re.split(r"\s*(?:\.{3,}|…)\s*", raw_quote) if p]
    norms = [normalize(p) for p in parts]
    frags = [n for n in norms if len(n.split()) >= MIN_QUOTE_WORDS]
    return frags or ([normalize(raw_quote)] if normalize(raw_quote) else [])


def check_quotations(
    answer: str,
    lookup: Callable[[str], Optional[str]],
    max_lookups: int = 6,
) -> dict[str, Any]:
    """Verify quoted spans in *answer* against verse text via *lookup(ref)*.

    Returns:
        {
          "quotes_checked": quotations that had an adjacent ref,
          "supported": of those, found verbatim in the cited verse,
          "unsupported": [{quote, ref}, ...] not found (or verse unavailable),
          "refs_seen": every ref a lookup was attempted for
        }

    A quotation with no adjacent ref, or shorter than MIN_QUOTE_WORDS after
    normalization, is ignored: stage 1 flags misattribution, not style.
    A ref whose text cannot be fetched counts as unsupported — an unverifiable
    citation must not silently pass.
    """
    result: dict[str, Any] = {
        "quotes_checked": 0,
        "supported": 0,
        "unsupported": [],
        "refs_seen": [],
    }
    verse_cache: dict[str, Optional[str]] = {}
    budget = max_lookups

    for m in _QUOTE_RE.finditer(answer):
        quote = m.group(1)
        window = answer[max(0, m.start() - WINDOW_CHARS): m.end() + WINDOW_CHARS]
        refs = extract_refs(window)
        if not refs:
            continue
        quote_norm = normalize(quote)
        if len(quote_norm.split()) < MIN_QUOTE_WORDS:
            continue

        result["quotes_checked"] += 1
        ref = refs[0]  # nearest ref in reading order
        if ref not in verse_cache and budget > 0:
            try:
                verse_cache[ref] = lookup(ref)
            except Exception:
                verse_cache[ref] = None
            budget -= 1

        verse_text = normalize(verse_cache.get(ref))
        if not verse_text:
            # Unverifiable: either lookup failed or we ran out of budget when
            # the ref was new. Flag it; never wave it through.
            if ref in verse_cache:
                result["unsupported"].append({"quote": quote[:120], "ref": ref})
            continue

        if any(frag in verse_text for frag in _fragments(quote)):
            result["supported"] += 1
        else:
            result["unsupported"].append({"quote": quote[:120], "ref": ref})

    result["refs_seen"] = sorted(verse_cache)
    return result
