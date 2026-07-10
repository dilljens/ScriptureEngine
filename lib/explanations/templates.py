#!/usr/bin/env python3
"""Explanation templates for every connection type in the scripture graph.

Each template function takes connection metadata and returns a human-readable
explanation string. If data is insufficient, returns None (falls through to LLM).

Usage:
    from lib.explanations.templates import explain, get_templates
    explanation = explain("direct_quotation", {"source": "gen.1.1", "target": "john.1.1"})
"""

import json

# ── Connection type metadata ──
CONNECTION_TYPE_LABELS = {
    "direct_quotation": "Direct Quotation",
    "same_lemma": "Same Hebrew/Greek Word",
    "same_root": "Same Hebrew Root",
    "allusion": "Allusion",
    "parallel_synonymous": "Synonymous Parallelism",
    "parallel_antithetic": "Antithetic Parallelism",
    "chiastic": "Chiastic Structure",
    "gematria": "Gematria",
    "type_antitype": "Type/Antitype",
    "prophetic_fulfillment": "Prophecy Fulfilled",
    "topical_guide": "Topical Guide",
    "topical_see_also": "TG Key References",
    "topical_shared_verses": "TG Shared Verses",
    "bible_dictionary": "Bible Dictionary",
    "bible_dictionary_tg": "Bible Dictionary → TG",
    "hebrew_grammar": "Hebrew Grammar",
    "linguistic": "Linguistic",
    "structural": "Structural",
    "interpretive": "Interpretive",
    "symbolic": "Symbolic",
    "frequency": "Word Frequency",
    "textual": "Textual",
    "geographic": "Geographic",
    "chronological": "Chronological",
    "sod_level": "Hidden (Sod)",
    "same_morphology": "Same Morphology",
    "semuchin": "Semuchin (Adjacent)",
    "formula_marker": "Formula Marker",
    "hapax_legomenon": "Hapax Legomenon",
    "dislegomenon": "Dislegomenon",
}


def fmt_verse(vid):
    """Format a verse ID or topic/BD ID for display."""
    if vid.startswith("tg:"):
        name = vid[3:].replace("-", " ").title()
        return f"**{name}** (Topical Guide)"
    if vid.startswith("bd:"):
        name = vid[3:].replace("-", " ").title()
        return f"**{name}** (Bible Dictionary)"
    return f"**{vid}**"


def explain(conn_type, meta):
    """Generate a human-readable explanation for a connection.
    
    Args:
        conn_type: string like "direct_quotation", "same_lemma", etc.
        meta: dict with connection metadata (source, target, strength, etc.)
    
    Returns:
        string explanation, or None if template can't handle this type
    """
    template_fn = _TEMPLATES.get(conn_type)
    if template_fn:
        return template_fn(meta)
    return None


def get_templates():
    """Return list of supported connection types."""
    return list(_TEMPLATES.keys())


# ── Template implementations ──

def _direct_quotation(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    return f"{s} is directly quoting {t} — the wording is nearly identical."


def _same_lemma(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    lemma = m.get("lemma", "")
    gloss = m.get("gloss", "")
    word_info = f" '{lemma}' ({gloss})" if lemma else ""
    return f"{s} and {t} share the Hebrew word{word_info}, linking the passages thematically."


def _same_root(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    root = m.get("root", "")
    meaning = m.get("root_meaning", "")
    root_info = f"**{root}** ({meaning})" if root and meaning else (f"**{root}**" if root else "")
    return f"{s} and {t} share the Hebrew root {root_info}, connecting their core meaning."


def _allusion(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    theme = m.get("theme", "")
    return f"{s} alludes to {t} through shared imagery{f' of **{theme}**' if theme else ''}."


def _parallel_synonymous(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    return f"{s} and {t} express the same idea in parallel — they say the same thing in different words."


def _parallel_antithetic(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    return f"{s} contrasts with {t}: the first idea is set against the second for emphasis."


def _chiastic(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    center = m.get("center", "")
    center_info = f" centered on **{center}**" if center else ""
    return f"{s} and {t} form a chiastic mirror{center_info} — an A-B-C / C'-B'-A' pattern."


def _gematria(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    val_s = m.get("value_source", m.get("value_a", ""))
    val_t = m.get("value_target", m.get("value_b", ""))
    word = m.get("word", "")
    word_info = f" of '{word}'" if word else ""
    return f"The gematria value{word_info} in {s} ({val_s}) equals the value in {t} ({val_t}), creating a numerical link."


def _type_antitype(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    return f"{s} prefigures {t} as a type pointing forward to its fulfillment in Christ."


def _prophetic_fulfillment(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    return f"{s} prophesied of {t}, which records its fulfillment."


def _topical_guide(m):
    s = fmt_verse(m.get("source", ""))
    topic = m.get("topic_name", "")
    if m.get("target", "").startswith("tg:"):
        topic = m.get("topic_name", m["target"][3:].replace("-", " ").title())
    return f"{s} is categorized under **{topic}** in the LDS Topical Guide."


def _topical_see_also(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    a_name = s
    b_name = t
    if m.get("source", "").startswith("tg:"):
        a_name = m["source"][3:].replace("-", " ").title()
    if m.get("target", "").startswith("tg:"):
        b_name = m["target"][3:].replace("-", " ").title()
    return f"In the Topical Guide, **{a_name}** lists **{b_name}** as a related topic under 'See also'."


def _topical_shared_verses(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    shared = m.get("shared_verses", m.get("jaccard", ""))
    shared_info = f" — they appear together in {shared} verses" if shared else ""
    return f"{s} and {t} are thematically linked{shared_info}."


def _bible_dictionary(m):
    entry = m.get("entry_name", "")
    t = fmt_verse(m.get("target", ""))
    return f"The Bible Dictionary entry for **{entry}** references {t}."


def _bible_dictionary_tg(m):
    entry = m.get("entry_name", "")
    t = fmt_verse(m.get("target", ""))
    return f"The Bible Dictionary entry for **{entry}** relates to {t}."


def _hebrew_grammar(m):
    s = fmt_verse(m.get("source", ""))
    concept = m.get("concept", "")
    return f"**{concept}** — {s} uses this Hebrew grammar concept, which you studied in your lessons."


def _linguistic(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    detail = m.get("detail", "")
    return f"{s} and {t} share linguistic features{f': {detail}' if detail else ''}."


def _structural(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    pattern = m.get("pattern", "")
    return f"{s} and {t} share the literary structure of **{pattern}**."


def _interpretive(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    tradition = m.get("tradition", "")
    interpretation = m.get("interpretation", "")
    result = ""
    if tradition:
        result += f"**{tradition}** interprets "
    else:
        result += "Interpretive tradition connects "
    result += f"{s} to {t}"
    if interpretation:
        result += f": {interpretation}"
    return result + "."


def _symbolic(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    symbol = m.get("symbol", "")
    return f"{s} and {t} share the symbolic motif of **{symbol}**."


def _frequency(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    word = m.get("word", "")
    return f"Both {s} and {t} feature the word **{word}** with unusual frequency."


def _default(m):
    s = fmt_verse(m.get("source", ""))
    t = fmt_verse(m.get("target", ""))
    ctype = m.get("connection_type", m.get("type", "connected"))
    label = CONNECTION_TYPE_LABELS.get(ctype, ctype.replace("_", " ").title())
    return f"{s} and {t} are connected via **{label}**."


# ── Template registry ──
_TEMPLATES = {
    "direct_quotation": _direct_quotation,
    "same_lemma": _same_lemma,
    "same_root": _same_root,
    "allusion": _allusion,
    "parallel_synonymous": _parallel_synonymous,
    "parallel_antithetic": _parallel_antithetic,
    "chiastic": _chiastic,
    "gematria": _gematria,
    "type_antitype": _type_antitype,
    "prophetic_fulfillment": _prophetic_fulfillment,
    "topical_guide": _topical_guide,
    "topical_see_also": _topical_see_also,
    "topical_shared_verses": _topical_shared_verses,
    "bible_dictionary": _bible_dictionary,
    "bible_dictionary_tg": _bible_dictionary_tg,
    "hebrew_grammar": _hebrew_grammar,
    "linguistic": _linguistic,
    "structural": _structural,
    "interpretive": _interpretive,
    "symbolic": _symbolic,
    "frequency": _frequency,
}

# For unknown types, use default
_TEMPLATES["__default__"] = _default
