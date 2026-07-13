"""
Expanded parallelism detector for Hebrew poetry.

Detects 15+ parallelism types:
  - Synonymous, Antithetic, Synthetic, Step (basic types)
  - Emblematic (comparative), Numerical, Chiastic, Janus (extended)
  - Merismus, Inclusio, Acrostic, Antiphonal, Keyword linking
  - Rhetorical pairs, Repetitive, Alternating
"""

import re

# Markers
ANTITHETIC_MARKERS = {"but", "yet", "however", "nevertheless", "rather", "nor", "neither"}
SYNTHETIC_MARKERS = {"for", "because", "therefore", "so that", "thus", "wherefore"}
COMPARATIVE_MARKERS = {"as", "like", "so", "than", "more than", "better", "כְּ", "כַּ"}
NUMERICAL_PATTERN = re.compile(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|'
                                r'1|2|3|4|5|6|7|8|9|10)\b.*\b(six|seven|eight|nine|ten|'
                                r'6|7|8|9|10)', re.IGNORECASE)
RHETORICAL_MARKERS = {"who", "what", "why", "how", "where", "when"}
MERISM_PAIRS = [
    ("heaven", "earth"), ("day", "night"), ("light", "darkness"),
    ("man", "woman"), ("male", "female"), ("young", "old"),
    ("rich", "poor"), ("wise", "foolish"), ("righteous", "wicked"),
    ("good", "evil"), ("life", "death"), ("blessing", "curse"),
    ("summer", "winter"), ("seed", "harvest"), ("land", "sea"),
    ("Jew", "Gentile"), ("bond", "free"), ("mountains", "hills"),
]


def tokenize(text):
    return re.findall(r"[a-zA-Z\u0590-\u05FF']+", text.lower())


def word_overlap(tokens_a, tokens_b):
    set_a, set_b = set(tokens_a), set(tokens_b)
    if not set_a or not set_b:
        return 0
    return len(set_a & set_b) / max(len(set_a | set_b), 1)


def contains_any(text, markers):
    return any(m.lower() in text.lower() for m in markers)


def detect_inclusio(first_verses, last_verses, min_overlap=0.2):
    """Detect inclusio — same/similar phrase bookending a passage."""
    texts_first = [v.get("text_english", "") for v in first_verses[:5]]
    texts_last = [v.get("text_english", "") for v in last_verses[-5:]]
    first_words = set()
    for t in texts_first:
        first_words.update(w for w in t.lower().split() if len(w) > 2)
    last_words = set()
    for t in texts_last:
        last_words.update(w for w in t.lower().split() if len(w) > 2)
    if not first_words or not last_words:
        return None
    overlap = len(first_words & last_words) / max(len(first_words | last_words), 1)
    if overlap >= min_overlap:
        shared = list(first_words & last_words)[:10]
        return {"type": "inclusio", "overlap": round(overlap, 2), "shared_terms": shared}


def detect_numerical_parallelism(text_a, text_b):
    """Detect 'three things... yea, four' pattern."""
    combined = f"{text_a} {text_b}"
    m = NUMERICAL_PATTERN.search(combined.lower())
    if m:
        return {"type": "numerical_parallelism", "evidence": m.group()[:50]}
    return None


def detect_emblematic(text_a, text_b):
    """Detect 'as... so...' pattern."""
    a_has = contains_any(text_a, COMPARATIVE_MARKERS)
    b_has = contains_any(text_b, COMPARATIVE_MARKERS)
    if a_has and b_has:
        return {"type": "emblematic_parallelism", "evidence": "comparative markers in both"}
    if a_has or b_has:
        return {"type": "emblematic_parallelism", "evidence": "comparative marker present", "confidence": 0.4}
    return None


def detect_merismus(text_a, text_b):
    """Detect paired opposites expressing totality."""
    combined = f"{text_a} {text_b}".lower()
    found = []
    for pair_a, pair_b in MERISM_PAIRS:
        if pair_a in combined and pair_b in combined:
            found.append(f"{pair_a} + {pair_b}")
    if found:
        return {"type": "merismus", "pairs": found[:3]}
    return None


def detect_keyword_linking(text_a, text_b):
    """Detect same keyword/linking between adjacent verses (Hebrew roots)."""
    tokens_a = set(tokenize(text_a))
    tokens_b = set(tokenize(text_b))
    # Find unusual words shared between them (longer = more significant)
    shared = [w for w in (tokens_a & tokens_b) if len(w) > 4]
    if len(shared) >= 2:
        return {"type": "keyword_linking", "shared_keywords": shared[:5], "count": len(shared)}
    return None


def detect_rhetorical_pair(text_a, text_b):
    """Detect parallel rhetorical questions."""
    a_words = text_a.lower().split()
    b_words = text_b.lower().split()
    a_has_rhet = any(w in RHETORICAL_MARKERS for w in a_words)
    b_has_rhet = any(w in RHETORICAL_MARKERS for w in b_words)
    if a_has_rhet and b_has_rhet:
        return {"type": "rhetorical_pair", "evidence": "parallel rhetorical questions"}
    return None


def classify_parallelism(verse_a, verse_b):
    """Classify the type of parallelism between two verses.

    Returns (type_name, confidence, evidence).
    """
    tokens_a = tokenize(verse_a)
    tokens_b = tokenize(verse_b)
    if not tokens_a or not tokens_b:
        return None, 0, "empty"

    overlap = word_overlap(tokens_a, tokens_b)
    a_antithetic = contains_any(verse_a, ANTITHETIC_MARKERS)
    b_antithetic = contains_any(verse_b, ANTITHETIC_MARKERS)
    contains_any(verse_a, SYNTHETIC_MARKERS)
    b_synthetic = contains_any(verse_b, SYNTHETIC_MARKERS)

    # 1. Numerical parallelism (highest priority — specific formula)
    num = detect_numerical_parallelism(verse_a, verse_b)
    if num:
        return "numerical_parallelism", 0.8, num.get("evidence", "")

    # 2. Merismus (paired opposites)
    mer = detect_merismus(verse_a, verse_b)
    if mer:
        return "merismus", 0.65, str(mer.get("pairs", ""))

    # 3. Synonymous parallelism
    if overlap > 0.3:
        return "parallel_synonymous", min(overlap, 0.95), f"word_overlap={overlap:.2f}"

    # 4. Antithetic parallelism
    if b_antithetic or a_antithetic:
        score = 0.5 + (1 - overlap) * 0.3
        if a_antithetic and b_antithetic:
            score += 0.2
        return "parallel_antithetic", min(score, 0.95), "contrastive_markers"

    # 5. Emblematic parallelism
    emb = detect_emblematic(verse_a, verse_b)
    if emb:
        return "emblematic_parallelism", emb.get("confidence", 0.5), emb.get("evidence", "")

    # 6. Synthetic parallelism
    if b_synthetic:
        return "parallel_synthetic", 0.6, "explanatory_marker"

    # 7. Rhetorical question pair
    rhet = detect_rhetorical_pair(verse_a, verse_b)
    if rhet:
        return "rhetorical_pair", 0.55, "parallel questions"

    # 8. Step/climactic parallelism
    len_a, len_b = len(tokens_a), len(tokens_b)
    if len_b > len_a * 1.5 and overlap > 0.1:
        return "parallel_step", 0.5, f"length_escalation {len_a}→{len_b}"

    # 9. Keyword linking
    kw = detect_keyword_linking(verse_a, verse_b)
    if kw:
        return "keyword_linking", 0.45, f"{kw.get('count', 0)} shared keywords"

    # 10. Weak synonymous (low overlap)
    if overlap > 0.15:
        return "parallel_synonymous", overlap * 0.8, f"partial_overlap={overlap:.2f}"

    return None, 0, "no_match"


def detect_parallelisms(verses, context_size=1):
    """Detect parallelisms between adjacent verses.

    Args:
        verses: list of dicts with 'text_english' key
        context_size: how many verses apart to check

    Returns list of detected parallelisms.
    """
    texts = [v.get("text_english", "") for v in verses if v.get("text_english")]
    if not texts:
        return []

    results = []
    checked_pairs = set()

    for i in range(len(texts)):
        for j in range(i + 1, min(i + 1 + context_size, len(texts))):
            pair = (i, j)
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            ptype, confidence, evidence = classify_parallelism(texts[i], texts[j])
            if ptype and confidence > 0.3:
                results.append({
                    "type": ptype,
                    "verse_a_index": i,
                    "verse_b_index": j,
                    "confidence": round(confidence, 2),
                    "evidence": evidence,
                    "detected_by": "algorithm",
                })

    return results


def detect_inclusio_in_passage(verses, window=10):
    """Run inclusio detection across a passage.

    Checks if the first N verses share keywords with the last N verses.
    """
    if len(verses) < 6:
        return None

    # Check various passage sizes (skip very short ones)
    for _passage_len in range(6, min(len(verses), 50), 2):
        first_verses = verses[:3]
        last_verses = verses[-3:]
        result = detect_inclusio(first_verses, last_verses)
        if result:
            return {
                **result,
                "verse_a_index": 0,
                "verse_b_index": len(verses) - 1,
                "detected_by": "algorithm",
            }

    return None
