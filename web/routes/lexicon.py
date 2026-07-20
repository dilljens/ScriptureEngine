"""Lexicon and grammar API routes."""

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def get_db():
    from lib.db import get_db as _get_db
    return _get_db()


@router.get("/api/v1/lexicon/search")
def lexicon_search(q: str = Query("", description="Search term — lemma, Hebrew, or English"), limit: int = Query(20, description="Max results")):
    """Search the scripture lexicon by lemma number, Hebrew word, or English translation."""
    from lib.lexicon import search_lexicon
    conn = get_db()
    results = search_lexicon(conn, q, limit)
    conn.close()
    return {"ok": True, "data": {"query": q, "results": results, "total": len(results)}}


@router.get("/api/v1/lexicon/lemma/{lemma}")
def lexicon_lemma(lemma: str):
    """Get full lexicon entry for a lemma (Strong's number)."""
    from lib.lexicon import get_lexicon_entry
    conn = get_db()
    entry = get_lexicon_entry(conn, lemma)
    conn.close()
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Lemma not found: {lemma}")
    return {"ok": True, "data": entry}


@router.get("/api/v1/lexicon/root/{root_letters}")
def lexicon_root(root_letters: str):
    """Get all lemmas sharing a triconsonantal root."""
    from lib.lexicon import get_root_family
    conn = get_db()
    members = get_root_family(conn, root_letters)
    conn.close()
    return {"ok": True, "data": {"root": root_letters, "members": members, "total": len(members)}}


@router.get("/api/v1/lexicon/domain/{domain_name}")
def lexicon_domain(domain_name: str):
    """Browse all lemmas in a semantic domain."""
    from lib.lexicon import get_domain_members
    conn = get_db()
    members = get_domain_members(conn, domain_name)
    conn.close()
    return {"ok": True, "data": {"domain": domain_name, "members": members, "total": len(members)}}


@router.get("/api/v1/lexicon/domains")
def lexicon_domains():
    """List all semantic domains."""
    conn = get_db()
    rows = conn.execute("SELECT name, description, ai_generated FROM semantic_domains ORDER BY name").fetchall()
    conn.close()
    return {"ok": True, "data": {"domains": [dict(r) for r in rows]}}


@router.get("/api/v1/lexicon/concordance/{lemma}")
def lexicon_concordance(lemma: str, limit: int = Query(50, description="Max verses to return")):
    """Get all verses containing a lemma (Strong's number)."""
    from lib.lexicon import get_concordance
    conn = get_db()
    verses = get_concordance(conn, lemma, limit)
    conn.close()
    return {"ok": True, "data": {"lemma": lemma, "verses": verses, "total": len(verses)}}


# ─── Grammar / Morphology ───────────────────────────────────────────────

MORPH_COLORS = {
    'HV': '#d4a574', 'HN': '#74a8d4', 'HA': '#a8d474', 'HR': '#d4d474',
    'HC': '#d474a8', 'HT': '#a8a8a8', 'HP': '#74d4d4', 'HD': '#d4a8d4',
    'AN': '#74d4a8', 'AV': '#d4a874', 'AA': '#a8d4a8', 'AR': '#d4d4a8',
}

MORPH_POS = {
    'HV': 'verb', 'HN': 'noun', 'HA': 'adjective', 'HR': 'preposition',
    'HC': 'conjunction', 'HT': 'particle', 'HP': 'pronoun', 'HD': 'adverb',
    'AN': 'aramaic_noun', 'AV': 'aramaic_verb', 'AA': 'aramaic_adjective', 'AR': 'aramaic_preposition',
}


@router.get("/api/v1/verses/{ref}/grammar")
def get_grammar(ref: str):
    """Get a verse with morphologically-tagged words — grammar coloring data."""
    import re
    ref = ref.replace(":", ".").replace(" ", ".").lower()
    m = re.match(r'([a-zA-Z0-9_]+)\.?(\d+)\.?(\d+)', ref)
    vid = f"{m.group(1)}.{int(m.group(2))}.{int(m.group(3))}" if m else ref

    conn = get_db()
    words = conn.execute("""
        SELECT g.word_hebrew, g.word_english, g.morph, g.lemma,
               g.value_standard, g.value_ordinal, g.value_reduced
        FROM gematria g WHERE g.verse_id = ?
        ORDER BY g.word_index
    """, (vid,)).fetchall()

    result = []
    for w in words:
        morph = w["morph"] or ""
        pos = MORPH_POS.get(morph[:2], "unknown")
        color = MORPH_COLORS.get(morph[:2], "#999999")
        result.append({
            "hebrew": w["word_hebrew"],
            "english": w["word_english"],
            "morph": morph,
            "lemma": w["lemma"],
            "pos": pos,
            "color": color,
            "gematria": {
                "standard": w["value_standard"],
                "ordinal": w["value_ordinal"],
                "reduced": w["value_reduced"],
            },
        })

    conn.close()
    return {"ok": True, "data": {"verse": vid, "words": result, "total": len(result)}}


@router.get("/api/v1/grammar/{ref:path}")
def get_grammar_alt(ref: str):
    """Alias for /api/v1/verses/{ref}/grammar."""
    return get_grammar(ref)
