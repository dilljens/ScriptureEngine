"""Machine orientation endpoint — ship the instructions inside the API.

Implements docs/inbox/proposal-api-orient.md: a small first-call briefing
(what this is, live health, conventions, capability map, topic index) plus
on-demand depth topics. Orient is an INDEX, not a manual: it names what to
fetch next rather than dumping everything.
"""

from fastapi import APIRouter

router = APIRouter()

# ── Depth topics (markdown) ─────────────────────────────────────────────────

TOPICS = {
    "refs": """# Verse references

- Refs are **dotted book IDs**: `gen.1.1`, `matt.16.16`, `1ne.1.1`, `dc88.88.67`.
  Human strings ("Genesis 1:1") will fail — get IDs from `GET /api/v1/books`.
- Book IDs are case-insensitive on lookup but preserved canonically
  (DSS sigla like `1QS` keep their case).
- **D&C double-numbering:** sections are stored as `dc<section>.<section>.<verse>`
  (e.g. `dc88.88.67` = D&C 88:67). Both chapter numbers are the section.
  Short forms work everywhere a ref is taken: `dc121.7`, `dc.121.7`,
  and `D&C 121:7` all resolve to `dc121.121.7`; `dc121` means the chapter.
  Display strings never repeat the number ("Doctrine and Covenants 121:7").
- **Psalms versification differs by endpoint** (see below).
- **DSS material** uses a `dss.` prefix (`dss.1QS...` style rows exist for
  some content); chapter/verse shapes vary by scroll — expect misses when
  probing sigla directly.

## Psalms: two correct conventions — and the shift is per-psalm, not +1

The English endpoints use **KJV numbering**. The interlinear tool indexes
the Hebrew (MT) text. The MT-minus-KJV offset is measured per psalm, not
stated as a rule: Psalm 51 is **+2**, ten psalms are +1, six are aligned
(50, 66, 71, 72, 78, 86) — a superscription does NOT predict the shift,
only verse counts do. Payloads for `psa.*` carry a `versification` block
with the measured `offset` for that psalm (unmeasured psalms say so).
The same block rides `scripture_interlinear` responses, which is the side
that actually uses MT numbering.
Beyond Psalms: Jonah 1 is **−1**, Jonah 2 is **+1** (also on the payload),
and Joel, Malachi, Numbers and the Samuels move boundaries the same way —
unmeasured, so verify word studies against both numbers everywhere.
There is no per-verse MT mapping table in this corpus;
verify word studies against both numbers.
""",

    "quality": """# Connection quality — confidence, not truth

Every connection carries `quality`. It grades how the link was established,
NOT whether it is doctrine:

| Grade | Means |
|---|---|
| `certain` / high tiers | direct textual grounding (quotation, same passage) |
| `tsk` (`discovered_by`) | Treasury of Scripture Knowledge cross-reference |
| `pattern` | algorithmic literary detection (chiasm scans, formulas) |
| `suggested` | algorithmic proposal — candidate evidence |

Rough corpus shape: most connections (~70%+) are algorithmic proposals.
**These are leads, not scholarship**: verify against the actual text before
citing. Numerical-layer evidence is additionally hard-capped below textual,
linguistic, and intertextual evidence regardless of score — a gematria match
can never outrank a quotation (enforced in calibration, exposed as
`evidence_class: numerical_candidate`).

Use `GET /api/v1/verses/{ref}?show_signals=true` for the per-connection
quality-signal breakdown.
""",

    "layers": """# The 11 connection layers

| Layer | What generates it | Textual vs computed |
|---|---|---|
| linguistic | shared roots, lemmas, cognates | computed from lexicon |
| numerical | gematria/isopsephy exact matches | computed, **ceiling-capped** |
| structural | chiasms, formulas, patterns | algorithmic detection |
| intertextual | quotations & allusions (incl. TSK) | curated + algorithmic |
| textual | manuscript variants (JST, DSS) | curated |
| geographic | place co-references | computed |
| chronological | timeline links | computed |
| interpretive | traditional readings | curated |
| frequency | word-count relationships | computed |
| symbolic | typology | curated |
| sod | hidden-pattern analyses (atbash…) | explicit-request analysis |

Filter any connection listing with `?layer=`; layer semantics differ enough
that cross-layer score comparison is meaningless.

Route coverage (same question, different doors):
- `GET /api/v1/verses/{ref}/guide` serves **intertextual** links at verse
  scale (quotations, allusions, TSK).
- `GET /api/v1/chapter/{book}/{chapter}/connections` serves **structural**
  and **interpretive** links at passage scale (parallels, chiasms, readings).
  The two answers are near-disjoint by design — the chapter route is NOT a
  cheaper version of the guide.
- `GET /api/v1/chapter/{ref}/guides` returns the per-verse guide for every
  verse in a chapter in one call (batch form of the first).
- `GET /api/v1/search` (full text) reaches what the graph cannot: a hit in
  search with no graph edge means the relationship is real but unlinked,
  not absent.
""",

    "limits": """# What this corpus cannot see

Knowing the boundaries prevents the worst wrong conclusion: *"no connection
exists"* when the true answer is *"this corpus cannot see that kind of
connection."*

- **No Septuagint.** OT text is Hebrew-only. You cannot check whether an NT
  Greek word matches the LXX wording of the verse it echoes — often the
  strongest allusion evidence. `text_greek` fields on OT verses are null by
  design (`has_greek: false`).
- **Two Pearl of Great Price books have no verses**: Joseph Smith—Matthew
  (`jsm`) and Articles of Faith (`aoff`) are listed in `/api/v1/books` with
  `available: false` and zero verses. Joseph Smith—History (`jsh`) is complete
  (75 verses). A listed-but-empty book is a known gap, not a bad ref.
- **The connection graph has no Old Testament → Restoration edges.** Search
  finds what the graph cannot (e.g. Psalm 51:17's "broken heart" family
  across the Book of Mormon and D&C); the graph carries zero of those links.
  Treat a missing edge as unlinked, never as evidence of no relationship.
- **No JST variants loaded.** `text_jst` is absent and `jst_diff` never fires;
  do not diff English against a JST field that is not there.
- **Psalms MT numbering** is implicit in the interlinear only; there is no
  MT-numbered verse table (see the `refs` topic).
- **Cloudflare fronts this site** and rejects the default Python urllib
  User-Agent with HTTP 403 (error 1010) while curl passes. Set a real
  User-Agent header in your client — otherwise every endpoint looks down.
- Gematria values are bounded candidate evidence, never proof of authorship,
  doctrine, prophecy, or history.
""",

    "research": """# The research loop that works

1. **Guide** — `GET /api/v1/verses/{ref}/guide` returns everything
   precomputed about one verse, bucketed by layer.
2. **Collect targets** — pick cross-references worth reading. Low-quality
   grades are leads, not noise; some of the best findings grade `suggested`.
3. **Batch-fetch texts** — `GET /api/v1/verses/{ref}` for each target (or
   `scripture_batch_lookup` via `/api/v1/tools/`) to read them in context.
4. **Verify language claims** — before asserting anything about a Hebrew or
   Greek word, confirm via `GET /api/v1/tools/scripture_interlinear`
   (word-by-word, Strong's, morphology). Never cite a gloss you have not seen.
5. Optionally audit contested claims with `POST /api/v1/tools/scripture_truth_check`.

Round-trip cost is low enough to run interactively.
""",
}

_CONVENTIONS = [
    "Verse refs are dotted book IDs: gen.1.1, matt.16.16, dc88.88.67. "
    "Human strings like 'Genesis 1:1' will 404 (with a hint). IDs: /api/v1/books.",
    "All JSON responses are {ok:true,data:...}; errors add {ok:false,error,hint?,see?}. "
    "FastAPI-shaped {detail} may also appear on legacy errors.",
    "Unknown /api/* paths return a real JSON 404 — never SPA HTML.",
    "connection.quality grades confidence, not truth: 'suggested' and 'pattern' "
    "are algorithmic proposals. Verify before citing (topic: quality).",
    "Psalms: English endpoints use KJV numbering, the interlinear uses Hebrew "
    "(MT); the shift is per-psalm 0-2, never a blanket +1 (topic: refs).",
    "D&C short forms resolve everywhere a ref is taken: dc121.7, dc.121.7, "
    "'D&C 121:7' all mean dc121.121.7. Display strings never repeat the number.",
    "Writes are authenticated except where noted: /debug/log needs a session "
    "token, /forum/posts resolves the author server-side (a body author is "
    "ignored), conversations keep a legacy anonymous path. No rate limiter — "
    "batch endpoints (chapter guides, batch lookup) exist to keep load down.",
]

_CAPABILITIES = [
    {"name": "lookup", "when": "you have a reference and want text, gematria, "
     "JST, connections", "start": "/api/v1/verses/{ref}"},
    {"name": "guide", "when": "you want everything precomputed about one verse",
     "start": "/api/v1/verses/{ref}/guide"},
    {"name": "search", "when": "you have words, not a reference",
     "start": "/api/v1/search?q="},
    {"name": "language", "when": "you need to VERIFY a claim about Greek/Hebrew",
     "start": "/api/v1/tools/scripture_interlinear"},
    {"name": "tools", "when": "you want the whole callable surface with schemas",
     "start": "/api/v1/tools"},
]

_TOPIC_INDEX = [
    {"id": "refs", "when": "before constructing any verse reference"},
    {"id": "quality", "when": "before citing a connection as evidence"},
    {"id": "layers", "when": "before interpreting the 11 connection layers"},
    {"id": "limits", "when": "before concluding the corpus does not contain something"},
    {"id": "research", "when": "doing multi-verse study — the guide→targets→verify loop"},
]


@router.get("/api/v1/orient")
def orient():
    """First-call briefing for machine clients. Read topics before acting."""
    from web.server import health_check  # deferred import avoids cycles

    h = health_check().get("data", {})
    subs = h.get("subsystems", {})
    return {
        "ok": True,
        "data": {
            "service": "Scripture Knowledge Engine",
            "version": h.get("version", "1.0.0"),
            "what_this_is": (
                f"{h.get('verses', 0):,} verses across the canon and related "
                f"ancient works, with {h.get('connections', 0):,} typed "
                "connections. Read-only public API; no key required."
            ),
            "health": {
                "database": subs.get("database"),
                "fts_index": subs.get("fts_index"),
                "vector_search": subs.get("vector_search"),
                "go_srs": subs.get("go_srs"),
                "degraded": h.get("degraded", []),
            },
            "conventions": _CONVENTIONS,
            "capabilities": _CAPABILITIES,
            "topics": _TOPIC_INDEX,
            "next": (
                "Read the topics matching your task via /api/v1/orient/{id} "
                "BEFORE acting. About to quote a cross-reference? "
                "Read 'quality' first."
            ),
        },
    }


@router.get("/api/v1/orient/{topic}")
def orient_topic(topic: str):
    body = TOPICS.get(topic)
    if body is None:
        from web.server import _teaching_404
        valid = ", ".join(sorted(TOPICS))
        return _teaching_404(
            f"Unknown orient topic: {topic}",
            hint=f"Valid topics: {valid}",
        )
    return {"ok": True, "data": {"topic": topic, "markdown": body}}
