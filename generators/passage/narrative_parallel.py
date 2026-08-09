"""Narrative Parallel — connect structurally parallel narratives across books.

For each narrative motif (birth/annunciation, deliverance/crossing, covenant
ratification, theophany, wilderness journey, judgment/restoration, calling),
scans verse text for motif keywords, clusters matches into passages, and
connects same-motif passages in different books.

This is a discovery generator (passage-level): outputs go to
passage_connections with type='narrative_parallel'.
"""

import logging

from ._common import cluster_passages, scan_keywords, upsert

logger = logging.getLogger(__name__)

# ── Motif definitions ─────────────────────────────────────────────────
# Each motif: name + keywords matched against text_english.

MOTIFS = [
    {
        "name": "birth_annunciation",
        "description": "Birth, annunciation, and barren-womb reversals",
        "keywords": [
            "conceive", "bore a son", "give birth", "barren", "child born",
            "blessed among women", "she conceived", "her womb", "opened her womb",
            "the lord visited", "had compassion on",
        ],
    },
    {
        "name": "deliverance_crossing",
        "description": "Deliverance through waters and mighty acts of rescue",
        "keywords": [
            "divided", "sea", "waters parted", "crossed over", "dry ground",
            "brought out", "mighty hand", "outstretched arm", "delivered",
            "redeemed", "salvation of the lord",
        ],
    },
    {
        "name": "covenant_ratification",
        "description": "Covenant making, oath, and treaty ratification",
        "keywords": [
            "covenant", "oath", "swore", "cut a covenant", "these are the words",
            "make a covenant", "everlasting covenant", "established his covenant",
            "sign of the covenant",
        ],
    },
    {
        "name": "theophany",
        "description": "Divine manifestation on mountain, in fire, cloud, and glory",
        "keywords": [
            "voice of the lord", "fire", "cloud", "mountain of god", "holy ground",
            "glory of the lord", "thunder", "lightning", "the lord descended",
            "filled the house",
        ],
    },
    {
        "name": "wilderness_journey",
        "description": "Wilderness wandering, testing, and provision",
        "keywords": [
            "wilderness", "desert", "forty years", "wander", "journey",
            "manna", "quail", "hungry", "thirst", "tested", "prove",
        ],
    },
    {
        "name": "judgment_restoration",
        "description": "Judgment followed by repentance and restoration",
        "keywords": [
            "repent", "return", "restore", "judgment", "captivity", "rebuild",
            "gather you", "restore the fortunes", "break up your fallow ground",
            "turn from your evil ways",
        ],
    },
    {
        "name": "calling_commission",
        "description": "Divine call and commissioning of a servant",
        "keywords": [
            "fear not", "i am with you", "called", "commission", "go to",
            "i send you", "whom shall i send", "here am i", "take off your shoes",
            "i will be with you",
        ],
    },
]


def run(conn, book_ids=None) -> int:
    """Connect same-motif narrative passages across books.

    Returns the number of passage_connections created.
    """
    total = 0
    for motif in MOTIFS:
        matches = scan_keywords(conn, motif["keywords"], book_ids)
        if not matches:
            continue
        passages = cluster_passages([m["verse"] for m in matches])
        if len(passages) < 2:
            continue
        for i in range(len(passages)):
            for j in range(i + 1, len(passages)):
                a, b = passages[i], passages[j]
                if a["book"] == b["book"]:
                    continue  # same-book parallels are too trivial
                strength = min(0.5 + (a["count"] + b["count"]) * 0.05, 1.0)
                confidence = min(0.4 + strength * 0.2, 0.65)
                if upsert(
                    conn, a, b, "interpretive", "narrative_parallel",
                    strength=strength, confidence=confidence,
                    metadata={"motif": motif["name"], "matches_a": a["count"],
                              "matches_b": b["count"], "source": "narrative_parallel"},
                ):
                    total += 1
        conn.commit()

    logger.info("narrative_parallel: %d connections created", total)
    return total
