#!/usr/bin/env python3
"""Label all connections with tradition, hermeneutic, and consensus_score.

Uses the connection's type, layer, and discovered_by fields to determine
which tradition(s) recognize this connection.

Objective connections (verifiable from the text itself) get tradition='none'.
Interpretive connections get tagged with their specific tradition.
"""
import sqlite3, sys, os, time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"

# Mapping: connection type → (tradition, hermeneutic, consensus_score, note)
# tradition: the tradition that identifies/sees this connection
# hermeneutic: the hermeneutical framework (linguistic, faith, historical_critical, both)

TYPE_LABELS = {
    # ═══════════════════════════════════════════════════════════
    # OBJECTIVE — verifiable from text
    # ═══════════════════════════════════════════════════════════
    "same_lemma":             ("none", "linguistic", 1.0, "Both passages use the same Hebrew or Greek word — verifiable from the lexicon."),
    "same_root":              ("none", "linguistic", 1.0, "Both passages use words sharing the same triconsonantal Hebrew root."),
    "same_morphology":        ("none", "linguistic", 1.0, "Both passages share the same grammatical form or morphological pattern."),
    "direct_quotation":       ("none", "linguistic", 1.0, "One passage directly quotes the other with significant wording overlap."),
    "allusion":               ("none", "linguistic", 0.8, "One passage echoes the other through shared phrasing, though not a direct quote."),
    "echo":                   ("none", "linguistic", 0.6, "A subtle verbal echo between passages — shared language that may or may not be intentional."),
    "parallel_synonymous":    ("none", "linguistic", 0.9, "Two passages express the same idea in parallel form — a feature of Hebrew poetry."),
    "parallel_antithetic":    ("none", "linguistic", 0.9, "Two passages contrast opposing ideas in parallel structure."),
    "chiastic":               ("none", "structural", 0.8, "Both passages share a chiastic (mirror) structural pattern — A-B-C-C'-B'-A'."),
    "keyword_linking":        ("none", "linguistic", 0.7, "A significant keyword appears in both passages, linking them thematically."),
    "key_word_count":         ("none", "frequency", 0.8, "A word appears with notable frequency in both passages."),
    "repetition_pattern":     ("none", "structural", 0.7, "Both passages share a pattern of repetition."),
    "12_fold_pattern":        ("none", "structural", 0.5, "Both passages exhibit a 12-fold structural pattern."),
    "10_fold_pattern":        ("none", "structural", 0.5, "Both passages exhibit a 10-fold structural pattern."),
    "7_fold_pattern":         ("none", "structural", 0.5, "Both passages exhibit a 7-fold structural pattern."),
    "genealogical":           ("none", "linguistic", 1.0, "A genealogical connection — shared names or lineage."),
    "journey_path":           ("none", "geographic", 0.9, "Both passages reference the same geographic journey or location."),
    "emblematic_parallelism": ("none", "structural", 0.7, "Both passages use emblematic parallelism — a comparison where one element illuminates the other."),
    "formula_marker":         ("none", "structural", 0.8, "Both passages share a formulaic expression or structural marker."),
    "semuchin":               ("none", "linguistic", 0.6, "Words appear adjacent to each other in both passages (semuchin adjacency pattern)."),
    "hapax_legomenon":        ("none", "frequency", 0.7, "A rare word (hapax legomenon — appearing only once in the text) links both passages."),
    "dislegomenon":           ("none", "frequency", 0.6, "A rare word (appearing only twice) links both passages."),
    "vulgate_variant":        ("none", "textual", 0.9, "A textual variant found in the Latin Vulgate connects these passages."),
    "septuagint_difference":  ("none", "textual", 0.9, "A difference in the Greek Septuagint version connects these passages."),
    "jst_change":             ("none", "textual", 0.8, "A textual change in the Joseph Smith Translation connects these passages."),

    # ═══════════════════════════════════════════════════════════
    # GEMATRIA — numbers are objective, significance is interpretive
    # ═══════════════════════════════════════════════════════════
    "gematria_factor":        ("multiple", "linguistic", 0.7, "Numerical relationship between word values in the original languages. The mathematical relationship is factual; its interpretive significance depends on tradition."),
    "same_gematria_reduced":  ("multiple", "linguistic", 0.7, "Words with the same reduced gematria value. The numerical fact is objective."),
    "same_gematria_standard": ("multiple", "linguistic", 0.7, "Words with the same standard gematria value. The numerical fact is objective."),
    "verse_gematria_total":   ("multiple", "linguistic", 0.6, "The total gematria value of the verse matches another verse. The number is factual."),
    "gematria_sum_relationship": ("multiple", "linguistic", 0.6, "A mathematical relationship between word totals. The sum is factual."),

    # ═══════════════════════════════════════════════════════════
    # INTERPRETIVE — require a specific lens
    # ═══════════════════════════════════════════════════════════
    "type_antitype":          ("christian", "faith", 0.5, "Christian tradition sees the earlier passage as a type (foreshadowing) fulfilled by the later passage (antitype). This is a Christological reading."),
    "prophetic_fulfillment":  ("christian", "faith", 0.5, "Christian tradition sees the earlier passage as a prophecy fulfilled by the later event. This reflects a specific interpretive framework."),
    "angel_of_yhwh":          ("christian", "faith", 0.4, "Christian tradition identifies the 'Angel of the Lord' as a pre-incarnate appearance of Christ. Jewish tradition reads this as a divine messenger."),
    "divine_council":         ("christian", "faith", 0.4, "Both passages reference the divine council — God's heavenly court. The significance of this council is interpreted differently across traditions."),
    "shared_symbol":          ("multiple", "faith", 0.5, "Both passages use the same symbolic imagery. The meaning of symbols is interpreted differently across traditions."),
    "name_symbolic":          ("multiple", "faith", 0.4, "A name with symbolic significance appears in both passages. The symbolic meaning depends on interpretive tradition."),
    "giliadi_pattern":        ("christian", "faith", 0.3, "A pattern identified by scholar Yuri Giliadi — this is a specific interpretive lens."),

    # ═══════════════════════════════════════════════════════════
    # SOD / HIDDEN — explicitly esoteric
    # ═══════════════════════════════════════════════════════════
    "hekhalot":               ("jewish", "faith", 0.3, "Both passages share language or imagery from the Hekhalot (heavenly palace) mystical tradition. This is an esoteric reading."),
    "hidden_name":            ("multiple", "faith", 0.3, "Both passages reference or encode a hidden name of God. Traditions differ on what names are encoded."),

    # ═══════════════════════════════════════════════════════════
    # SEFARIA — Jewish interpretive tradition
    # ═══════════════════════════════════════════════════════════
    "rabbinic_midrash":          ("jewish", "faith", 0.85, "Classical Jewish commentary (Rashi, Ramban, Ibn Ezra, etc.) on this verse — the foundation of Jewish biblical interpretation."),
    "midrash_rabbah":            ("jewish", "faith", 0.75, "Midrash Rabbah — homiletical interpretation from the classical rabbinic period."),
    "talmud_quotation":          ("jewish", "faith", 0.8, "The Talmud quotes or references this verse in its legal or aggadic discussions."),
    "targum_commentary":         ("jewish", "textual", 0.85, "The Aramaic Targum translates/paraphrases this verse, often adding interpretive elements."),
    "zohar_commentary":          ("jewish", "faith", 0.7, "The Zohar, the foundational work of Kabbalah, comments on this verse with mystical interpretation."),
    "kabbalistic_interpretation":("jewish", "faith", 0.7, "A Kabbalistic interpretation of this verse, drawing on esoteric traditions."),
    "mishnah_reference":         ("jewish", "faith", 0.8, "The Mishnah references this verse in its legal/traditional framework."),
    "scriptural_reference":      ("jewish", "faith", 0.5, "A reference to this verse within Jewish textual tradition."),

    # ═══════════════════════════════════════════════════════════
    # TG / BD — LDS-specific
    # ═══════════════════════════════════════════════════════════
    "topical_guide":          ("lds", "faith", 0.9, "This connection is listed in the LDS Topical Guide — a human-curated collection of scripture references organized by doctrinal theme."),
    "topical_see_also":       ("lds", "faith", 0.9, "The LDS Topical Guide lists these topics as related under 'See also'."),
    "topical_shared_verses":  ("lds", "faith", 0.7, "These topics share multiple verses in the LDS Topical Guide, indicating thematic overlap."),
    "bible_dictionary":       ("lds", "faith", 0.9, "This connection comes from the LDS Bible Dictionary."),
    "bible_dictionary_tg":    ("lds", "faith", 0.8, "A Bible Dictionary entry relates to this Topical Guide topic."),
}

# Default for unlabeled types
DEFAULT_LABEL = ("none", "linguistic", 0.3, "Connection type not explicitly categorized.")


def main():
    conn = sqlite3.connect(str(DB_PATH))
    
    # Get total
    total = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
    print(f"Total connections to label: {total:,}")
    
    # Get unique type values
    types = conn.execute("SELECT DISTINCT type FROM connections WHERE deprecated=0 ORDER BY type").fetchall()
    print(f"Unique connection types: {len(types)}")
    
    # Count by type
    for r in types:
        ct = r[0]
        count = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0 AND type=?", (ct,)).fetchone()[0]
        label_info = TYPE_LABELS.get(ct, DEFAULT_LABEL)
        trad, herm = label_info[0], label_info[1]
        print(f"  {count:>8,} × {ct:35s} → {trad:15s} ({herm})")
    
    # Update in batches
    updated = 0
    batch_size = 50000
    
    for r in types:
        ct = r[0]
        label_info = TYPE_LABELS.get(ct, DEFAULT_LABEL)
        tradition, hermeneutic, consensus, note = label_info
        
        # Handle connections that already have a non-NULL hermeneutic
        if hermeneutic:
            conn.execute("""
                UPDATE connections SET tradition=?, hermeneutic=?, consensus_score=?, tradition_note=?
                WHERE deprecated=0 AND type=? AND (tradition IS NULL OR tradition='none' OR hermeneutic IS NULL)
            """, (tradition, hermeneutic, consensus, note, ct))
        else:
            conn.execute("""
                UPDATE connections SET tradition=?, consensus_score=?, tradition_note=?
                WHERE deprecated=0 AND type=? AND (tradition IS NULL OR tradition='none')
            """, (tradition, consensus, note, ct))
        
        affected = conn.total_changes
        updated += affected
        conn.commit()
    
    # Verify
    untagged = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0 AND (tradition IS NULL OR tradition='none')").fetchone()[0]
    tagged = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0 AND tradition NOT NULL AND tradition != 'none'").fetchone()[0]
    total_now = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
    
    print(f"\n{'='*60}")
    print(f"Labeling complete:")
    print(f"  Updated: {updated:,}")
    print(f"  Still untagged (tradition='none'): {untagged:,}")
    print(f"  Tagged with specific tradition: {tagged:,}")
    print(f"  Total active: {total_now:,}")
    
    # Show distribution by tradition
    dist = conn.execute("""
        SELECT COALESCE(tradition, 'unset') as t, COUNT(*) as cnt 
        FROM connections WHERE deprecated=0 
        GROUP BY t ORDER BY cnt DESC
    """).fetchall()
    
    print(f"\nDistribution by tradition:")
    for t, cnt in dist:
        pct = cnt / total_now * 100
        print(f"  {t:25s}: {cnt:>8,} ({pct:5.1f}%)")
    
    conn.close()


if __name__ == "__main__":
    main()
