"""Hebrew poetic detectors — 8 scholarship-based patterns for Isaiah.

Covers the gap list from docs/hebrew-poetic-patterns-scholarship.md §7:
  (a) Janus candidates (proposed)      — subtype janus_candidate
  (b) x//x+1 number parallels         — subtype number_parallel
  (c) emblematic similes (as..so)     — subtype emblematic_simile
  (d) anaphora / epiphora runs        — subtypes anaphora_open / epiphora_close
  (e) chapter inclusio (rare-lemma)    — subtype inclusio_isa
  (f) sound pairs (phonological)       — subtype sound_pair
  (g) tercet classifier aab/abb/aaa   — subtypes tercet_aab / tercet_abb / tercet_aaa
  (h) particle hinges (hinneh/akh/ki) — subtype particle_hinge

On language variation (user question): YES, detectors are possible, but Hebrew
varies by pointing, morphology, and translation, so every detector below uses a
DUAL strategy — Hebrew lemma (stable) + English gloss/text (fuzzy) — with
conservative thresholds and low confidence (0.3–0.6). They NARROW 1293 Isaiah
verses to dozens of candidates; Janus / simile / tercet-abc still need human
eyes to confirm. Metadata always says how the hit was made and, for Janus,
"proposed": true. Never cite a detector alone as proof.

Scholars per detector: Lowth (b,c); Kugel/Alter (g,h); Berlin/Jakobson (d,e,f);
Watson/Rendsburg (a); Melamed breakup + number formula (b); Douglas (e).
"""

import re
from collections import Counter, defaultdict

BOOK = "isa"

SUBTYPES = [
    "janus_candidate",
    "number_parallel",
    "emblematic_simile",
    "anaphora_open",
    "epiphora_close",
    "inclusio_isa",
    "sound_pair",
    "tercet_aab",
    "tercet_abb",
    "tercet_aaa",
    "particle_hinge",
]

STOP_LEMMAS = {
    "853",
    "5921",
    "5922",
    "3966",
    "3588",
    "3808",
    "4100",
    "1697",
    "3068",
    "3069",
    "430",
    "3478",
    "1121",
    "6440",
    "3117",
    "776",
    "8064",
    "4325",
    "784",
    "376",
    "559",
    "1961",
    "6213",
    "1980",
    "7200",
    "8085",
    "3045",
    "5375",
    "5414",
    "7760",
    "1696",
    "7725",
    "7971",
    "413",
    "5921 a",
    "5922 a",
    "834 a",
    "3588 a",
    "1121 a",
    "6213 a",
    "3117 a",
    "853 a",
    "l",
    "c/l",
    "c",
    "d",
    "b",
    "m",
    "k",
    "s",
    "i",
    "413 a",
}

STOPWORDS = {
    "the",
    "and",
    "of",
    "to",
    "in",
    "that",
    "for",
    "is",
    "it",
    "his",
    "with",
    "he",
    "they",
    "them",
    "her",
    "you",
    "your",
    "a",
    "an",
    "as",
    "so",
    "shall",
    "will",
    "be",
    "are",
    "was",
    "were",
    "by",
    "from",
    "upon",
    "unto",
    "hath",
    "doth",
    "saith",
}


def _norm_lemma(raw):
    if not raw:
        return ""
    raw = raw.strip()
    if "/" in raw:
        raw = raw.split("/")[-1].strip()
    return raw


def _batch_insert(conn, batch):
    if not batch:
        return
    conn.executemany(
        """
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        batch,
    )
    conn.commit()


def _isa_verses(conn):
    rows = conn.execute(
        """
        SELECT id, chapter, verse, text_english, text_hebrew
        FROM verses WHERE book_id = ? ORDER BY chapter, verse
    """,
        (BOOK,),
    ).fetchall()
    return [dict(r) for r in rows]


def _lemma_freq(conn):
    rows = conn.execute(
        """
        SELECT lemma, COUNT(*) n FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        WHERE v.book_id = ? AND lemma IS NOT NULL AND lemma != ''
        GROUP BY lemma
    """,
        (BOOK,),
    ).fetchall()
    freq = Counter()
    for r in rows:
        freq[_norm_lemma(r["lemma"])] = r["n"]
    return freq


def _verse_lemmas(conn, verse_id, freq=None):
    rows = conn.execute(
        "SELECT lemma FROM gematria WHERE verse_id = ?", (verse_id,)
    ).fetchall()
    out = set()
    for r in rows:
        s = _norm_lemma(r["lemma"])
        if s and s not in STOP_LEMMAS and len(s) > 1:
            out.add(s)
    return out


# ─── (a) JANUS candidates — data-driven polysemy + neighbor-sense split ───
def seed_janus(conn):
    """A polysemous word (multi-sense lexicon entry) whose neighboring verses
    each echo a DIFFERENT sense. Classic Janus (Song 2:12 zamir; Gen 49:26) is
    by definition untranslatable, so every hit is 'proposed' — human confirms.
    Senses come from lexicon definitions (numbered uses), matched against
    neighbor-verse English content words. KJV translates each lemma consistently,
    so gematria word_english cannot supply the polysemy — lexicon can."""
    batch, count = [], 0
    verses = _isa_verses(conn)
    eng = {v["id"]: (v["text_english"] or "").lower() for v in verses}
    order = [v["id"] for v in verses]
    idx = {vid: i for i, vid in enumerate(order)}
    freq = _lemma_freq(conn)

    def _sense_chunks(definition):
        parts = re.split(r"\(\d+\)|\b\d+\)", definition or "")
        chunks = []
        for part in parts:
            toks = {
                t
                for t in re.findall(r"[a-z']+", part.lower())
                if len(t) >= 5 and t not in STOPWORDS
            }
            if len(toks) >= 2:
                chunks.append(toks)
        return chunks

    # candidate lemmas: mid-frequency in Isaiah + multi-sense lexicon entry
    cand = []
    for r in conn.execute("SELECT lemma, definition FROM lexicon"):
        s = _norm_lemma(r["lemma"])
        if not s or s in STOP_LEMMAS or not 3 <= freq.get(s, 0) <= 60:
            continue
        chunks = _sense_chunks(r["definition"])
        if len(chunks) >= 2:
            cand.append((s, chunks))
    cand = sorted(cand)[:150]

    for lemma, chunks in cand:
        vrows = conn.execute(
            """
            SELECT DISTINCT verse_id FROM gematria g JOIN verses v ON v.id = g.verse_id
            WHERE v.book_id = ? AND g.lemma LIKE ?
        """,
            (BOOK, f"%{lemma}%"),
        ).fetchall()
        for (vid,) in vrows:
            i = idx.get(vid)
            if i is None or i == 0 or i >= len(order) - 1:
                continue
            prev_words = set(re.findall(r"[a-z']+", eng[order[i - 1]]))
            next_words = set(re.findall(r"[a-z']+", eng[order[i + 1]]))
            uniq_prev, uniq_next = prev_words - next_words, next_words - prev_words
            best = None
            for a in range(len(chunks)):
                for b in range(a + 1, len(chunks)):
                    if (chunks[a] & uniq_prev and chunks[b] & uniq_next) or (
                        chunks[b] & uniq_prev and chunks[a] & uniq_next
                    ):
                        best = (sorted(chunks[a])[:6], sorted(chunks[b])[:6])
                        break
                if best:
                    break
            if not best:
                continue
            batch.append(
                (
                    order[i - 1],
                    order[i + 1],
                    "linguistic",
                    "janus",
                    "janus_candidate",
                    0.3,
                    0.3,
                    "algorithm",
                    f'{{"lemma": "{lemma}", "pivot": "{vid}", '
                    f'"sense_a": "{", ".join(best[0])}", "sense_b": "{", ".join(best[1])}", '
                    f'"proposed": true, '
                    f'"scholar": "Watson/Rendsburg Janus type", "needs_human": true}}',
                )
            )
            count += 1
            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []
            if count >= 150:
                break
        if count >= 150:
            break
    _batch_insert(conn, batch)
    print(f"  (a) Janus candidates: {count} (all proposed, need human)")
    return count


# ─── (b) NUMBER parallels x//x+1 ───
NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "thousand": 1000,
    "ten thousand": 10000,
    "hundred": 100,
}
NUM_RE = re.compile(
    r"\b(ten thousand|one|two|three|four|five|six|seven|eight|nine|ten|thousand|hundred)\b"
)


PRONOUN_ONE_RE = re.compile(r"\b(every|no|any|each)\s+one\b")


def _nums_in(text):
    t = PRONOUN_ONE_RE.sub(" ", (text or "").lower())  # "every one" is a pronoun
    found = []
    for m in NUM_RE.finditer(t):
        w = m.group(1)
        found.append(NUMBERS[w])
    return found


def seed_numbers(conn):
    batch, count = [], 0
    verses = _isa_verses(conn)
    by_ch = defaultdict(list)
    for v in verses:
        by_ch[v["chapter"]].append(v)
    for ch, vs in by_ch.items():
        for a, b in zip(vs, vs[1:], strict=False):
            na, nb = _nums_in(a["text_english"]), _nums_in(b["text_english"])
            hit = None
            for x in na:
                for y in nb:
                    if y == x + 1 or (x == 1000 and y == 10000):
                        hit = (x, y)
            if hit:
                batch.append(
                    (
                        a["id"],
                        b["id"],
                        "structural",
                        "number_parallel",
                        "number_parallel",
                        0.7,
                        0.7,
                        "algorithm",
                        f'{{"pair": "{hit[0]}//{hit[1]}", "chapter": {ch}, '
                        f'"scholar": "Lowth number formula x//x+1"}}',
                    )
                )
                count += 1
    _batch_insert(conn, batch)
    print(f"  (b) Number parallels: {count}")
    return count


# ─── (c) EMBLEMATIC simile (as/like .. so) ───
SIM_RE = re.compile(r"\b(as|like)\b.{0,80}\bso\b", re.IGNORECASE)


def seed_simile(conn):
    batch, count = [], 0
    verses = _isa_verses(conn)
    for v in verses:
        if not SIM_RE.search(v["text_english"] or ""):
            continue
        # Hebrew confirm: lemma 3644 (kemo, like/as) or 3651 (ken, so)
        rows = conn.execute(
            "SELECT DISTINCT lemma FROM gematria WHERE verse_id = ?", (v["id"],)
        ).fetchall()
        lems = {_norm_lemma(r["lemma"]) for r in rows}
        hebrew_ok = ("3644" in lems) or ("3651" in lems) or ("3651 c" in lems)
        m = SIM_RE.search(v["text_english"] or "")
        batch.append(
            (
                v["id"],
                v["id"],
                "literary",
                "emblematic",
                "emblematic_simile",
                0.55 if hebrew_ok else 0.4,
                0.5 if hebrew_ok else 0.4,
                "algorithm",
                f'{{"frame": "{(m.group(0)[:60] if m else "")}", '
                f'"hebrew_confirm": {"true" if hebrew_ok else "false"}, '
                f'"scholar": "Lowth emblematic parallelism", "needs_human": {"false" if hebrew_ok else "true"}}}',
            )
        )
        count += 1
    _batch_insert(conn, batch)
    print(f"  (c) Emblematic similes: {count}")
    return count


# ─── (d) ANAPHORA / EPIPHORA runs ───
def _shingle(text, n=3, tail=False):
    words = re.findall(r"[a-z']+", (text or "").lower())
    words = [w for w in words if w not in STOPWORDS]
    if len(words) < n:
        return None
    seq = words[-n:] if tail else words[:n]
    return " ".join(seq)


def seed_anaphora(conn):
    batch, count = [], 0
    verses = _isa_verses(conn)
    by_ch = defaultdict(list)
    for v in verses:
        by_ch[v["chapter"]].append(v)
    for ch, vs in by_ch.items():
        num = {v["id"]: (v["chapter"], v["verse"]) for v in vs}
        opens = defaultdict(list)
        closes = defaultdict(list)
        for v in vs:
            o, c = _shingle(v["text_english"]), _shingle(v["text_english"], tail=True)
            if o:
                opens[o].append(v["id"])
            if c and c != o:
                closes[c].append(v["id"])
        for phrase, ids in opens.items():
            if len(ids) >= 3:
                ordered = sorted(ids, key=lambda vid: num[vid])
                for a, b in zip(ordered, ordered[1:], strict=False):
                    batch.append(
                        (
                            a,
                            b,
                            "structural",
                            "anaphora",
                            "anaphora_open",
                            0.5,
                            0.55,
                            "algorithm",
                            f'{{"phrase": "{phrase[:60]}", "chapter": {ch}, '
                            f'"occurrences": {len(ids)}, "scholar": "Berlin/Jakobson anaphora"}}',
                        )
                    )
                    count += 1
        for phrase, ids in closes.items():
            if len(ids) >= 3:
                ordered2 = sorted(ids, key=lambda vid: num[vid])
                for a, b in zip(ordered2, ordered2[1:], strict=False):
                    batch.append(
                        (
                            a,
                            b,
                            "structural",
                            "epiphora",
                            "epiphora_close",
                            0.5,
                            0.55,
                            "algorithm",
                            f'{{"phrase": "{phrase[:60]}", "chapter": {ch}, '
                            f'"occurrences": {len(ids)}, "scholar": "Berlin/Jakobson epiphora"}}',
                        )
                    )
                    count += 1
    _batch_insert(conn, batch)
    print(f"  (d) Anaphora/epiphora links: {count}")
    return count


# ─── (e) INCLUSIO (rare-lemma bracket per chapter) ───
def seed_inclusio(conn):
    batch, count = [], 0
    freq = _lemma_freq(conn)
    verses = _isa_verses(conn)
    by_ch = defaultdict(list)
    for v in verses:
        by_ch[v["chapter"]].append(v)
    for ch, vs in sorted(by_ch.items()):
        if len(vs) < 6:
            continue
        head_ids = [v["id"] for v in vs[:3]]
        tail_ids = [v["id"] for v in vs[-3:]]
        head_lems, tail_lems = set(), set()
        for vid in head_ids:
            head_lems |= _verse_lemmas(conn, vid)
        for vid in tail_ids:
            tail_lems |= _verse_lemmas(conn, vid)
        shared = [s for s in (head_lems & tail_lems) if freq.get(s, 99) <= 12]
        for s in shared[:3]:
            batch.append(
                (
                    head_ids[0],
                    tail_ids[-1],
                    "structural",
                    "inclusio",
                    "inclusio_isa",
                    0.5,
                    0.5,
                    "algorithm",
                    f'{{"lemma": "{s}", "chapter": {ch}, '
                    f'"scholar": "Douglas ring/inclusio"}}',
                )
            )
            count += 1
    _batch_insert(conn, batch)
    print(f"  (e) Inclusio brackets: {count}")
    return count


# ─── (f) SOUND pairs (shared 2-letter Hebrew opening, different lemma) ───
def seed_sound(conn):
    batch, count = [], 0
    verses = _isa_verses(conn)
    # preload (prefix -> set(lemmas)) per verse
    verse_pref = {}
    for v in verses:
        rows = conn.execute(
            "SELECT hebrew_plain, lemma FROM gematria WHERE verse_id = ?", (v["id"],)
        ).fetchall()
        d = defaultdict(set)
        for r in rows:
            hp = (r["hebrew_plain"] or "").strip()
            s = _norm_lemma(r["lemma"])
            core = hp.split("/")[-1]  # strip particle prefixes (w/, b/, k/, l/, m/)
            if len(core) >= 3 and s and s not in STOP_LEMMAS:
                d[core[:2]].add(s)
        verse_pref[v["id"]] = d
    for a, b in zip(verses, verses[1:], strict=False):
        if a["chapter"] != b["chapter"]:
            continue
        da, db = verse_pref[a["id"]], verse_pref[b["id"]]
        made = 0
        for pref, la in da.items():
            if pref in db and not (la & db[pref]) and made < 3:
                batch.append(
                    (
                        a["id"],
                        b["id"],
                        "linguistic",
                        "sound_pair",
                        "sound_pair",
                        0.4,
                        0.4,
                        "algorithm",
                        f'{{"prefix": "{pref}", "scholar": "Berlin phonological level / Jakobson"}}',
                    )
                )
                count += 1
                made += 1
        if count >= 400:
            break
    _batch_insert(conn, batch)
    print(f"  (f) Sound pairs: {count} (capped)")
    return count


# ─── (g) TERCET classifier ───
def seed_tercet(conn):
    batch, count = [], 0
    freq = _lemma_freq(conn)
    verses = _isa_verses(conn)

    def rare(vid):
        return {s for s in _verse_lemmas(conn, vid) if freq.get(s, 99) <= 25}

    for v1, v2, v3 in zip(verses, verses[1:], verses[2:], strict=False):
        if not (v1["chapter"] == v2["chapter"] == v3["chapter"]):
            continue
        A, B, C = rare(v1["id"]), rare(v2["id"]), rare(v3["id"])
        s12, s23, s13 = len(A & B), len(B & C), len(A & C)
        sub, conf = None, 0.45
        if s12 >= 1 and s23 >= 1:
            sub = "tercet_aaa"
            conf = 0.5
        elif s12 >= 1:
            sub = "tercet_aab"
        elif s23 >= 1:
            sub = "tercet_abb"
        elif s13 >= 1:
            sub = "tercet_aab"  # envelope tercet; human sorts out
            conf = 0.35
        if sub:
            batch.append(
                (
                    v1["id"],
                    v3["id"],
                    "structural",
                    "tercet",
                    sub,
                    0.45,
                    conf,
                    "algorithm",
                    f'{{"shared12": {s12}, "shared23": {s23}, "shared13": {s13}, '
                    f'"scholar": "Kugel/Alter tercet 2+1/1+2", "needs_human": true}}',
                )
            )
            count += 1
            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []
        if count >= 300:
            break
    _batch_insert(conn, batch)
    print(f"  (g) Tercets: {count} (capped, need human for abc)")
    return count


# ─── (h) PARTICLE hinges ───
PARTICLES = {"2009": "hinneh", "389": "akh", "3588 a": "ki", "3588": "ki"}


def seed_particles(conn):
    batch, count = [], 0
    verses = _isa_verses(conn)
    by_ch = defaultdict(list)
    for v in verses:
        by_ch[v["chapter"]].append(v)
    for ch, vs in sorted(by_ch.items()):
        hinges = []
        for v in vs:
            rows = conn.execute(
                "SELECT lemma FROM gematria WHERE verse_id = ?", (v["id"],)
            ).fetchall()
            lems = {_norm_lemma(r["lemma"]) for r in rows}
            # normalize ki variants
            has = [PARTICLES.get(s) or ("ki" if s == "3588" else None) for s in lems]
            parts = sorted({h for h in has if h})
            if not parts:
                continue
            speech = bool({"3068", "3069", "559", "1697"} & lems)
            hinges.append((v["id"], parts, speech))
        # chain hinges within chapter
        for (a, pa, sa), (b, pb, sb) in zip(hinges, hinges[1:], strict=False):
            batch.append(
                (
                    a,
                    b,
                    "structural",
                    "discourse_hinge",
                    "particle_hinge",
                    0.55 if (sa or sb) else 0.45,
                    0.5,
                    "algorithm",
                    f'{{"from": {pa}, "to": {pb}, "speech": {"true" if (sa or sb) else "false"}, '
                    f'"chapter": {ch}, "density": {len(hinges)}, '
                    f'"scholar": "Kugel/Alter sequence; Berlin particles"}}',
                )
            )
            count += 1
    _batch_insert(conn, batch)
    print(f"  (h) Particle hinges: {count}")
    return count


def run(conn, book_ids=None):
    """Run all 8 poetic detectors (Isaiah default). Clears own subtypes first."""
    global BOOK
    if book_ids:
        BOOK = book_ids[0] if isinstance(book_ids, list) else book_ids
    for s in SUBTYPES:
        conn.execute("DELETE FROM connections WHERE subtype=?", (s,))
    conn.commit()
    total = 0
    total += seed_janus(conn)
    total += seed_numbers(conn)
    total += seed_simile(conn)
    total += seed_anaphora(conn)
    total += seed_inclusio(conn)
    total += seed_sound(conn)
    total += seed_tercet(conn)
    total += seed_particles(conn)
    print(f"  Total poetic-detector connections ({BOOK}): {total}")
    return total
