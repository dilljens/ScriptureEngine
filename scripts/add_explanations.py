#!/usr/bin/env python3
"""Add human-readable explanations to algorithmic connections.

Targets the most-viewed verses and adds `reasoning` to their connections' metadata.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

EXPLANATIONS = {
    # Gen 1:1 structural connections
    "gen.1.1|structural|chiastic|thematic": "Gen 1:1 ('In the beginning God created the heavens and the earth') is the first half of a grand inclusio that spans the creation account. The parallel is Gen 2:3 ('God blessed the seventh day and sanctified it'). Together they form an A-A' chiastic structure: creation begins (A) and creation is sanctified (A'). The account moves from the general (heavens and earth) to the specific (the seventh day of rest), demonstrating that creation's purpose is the Sabbath rest of God.",
    "gen.1.1|structural|merismus|gen": "Gen 1:1 uses merismus (a figure of speech where two extremes stand for the whole): 'the heavens and the earth' means the entire cosmos. Gen 1:2 begins the detailed description of the formless earth. The connection is one of whole-to-part: verse 1 states the whole; verse 2 begins fleshing out the parts.",
    "gen.1.1|intertextual|direct_quotation|tsk": "This TSK (Treasury of Scripture Knowledge) cross-reference connects Gen 1:1 to other scriptures that speak of God as Creator. Each reference cites God making the heavens and earth — Jeremiah 10:12, Isaiah 44:24, Psalm 33:6, etc. The connection is lexical: all share the vocabulary of divine creation (bara, shamayim, erets).",
    "gen.1.1|intertextual|midrashic_connection|creation_midrash": "John 1:1 ('In the beginning was the Word') is a deliberate midrashic re-reading of Gen 1:1 ('In the beginning God created'). John replaces 'God created' with 'the Word was' — the Logos is the agent of creation. The connection is the most significant theological reinterpretation of Genesis in the NT.",
    "gen.1.1|numerical|divine_name_value|": "Gen 1:1 has a gematria value of 2701, which equals 37 x 73 — both prime numbers that form a visual pattern when represented as Hebrew letters. The number 2701 also relates to the value of YHWH (26) and Elohim (86) in various combinations. The numerical significance suggests divine design at the level of the text itself.",
    "gen.1.1|textual|inspired_revision|creation_expansion": "JST/Moses expands Gen 1:1 with additional detail about the Son (Moses 2:1). The inspired revision clarifies that creation was accomplished through the Son, adding Christological content that the Genesis text implies but does not state explicitly.",

    # Gen 1:2 connections
    "gen.1.2|linguistic|same_root|": "Gen 1:2 describes the earth as 'tohu wa-bohu' (formless and void) with darkness over the 'deep' (tehom). These words appear in related contexts across the OT. The 'deep' (tehom) is related to the Akkadian 'Tiamat' — the chaos waters. The same-root connection links verses that share the vocabulary of chaos and creation.",
    "gen.1.2|intertextual|direct_quotation|tsk": "Jeremiah 4:23 ('I beheld the earth, and it was without form and void') explicitly echoes Gen 1:2 to describe Judah's coming judgment as a reversal of creation — a de-creation back to the primordial chaos state. The connection shows that God's judgment can undo creation.",

    # Exodus 3:14 — I AM
    "exo.3.14|intertextual|direct_quotation|tsk": "Exo 3:14 ('I AM THAT I AM') is the foundational revelation of God's name and nature. Cross-references connect it to: (1) Jesus' 'I AM' statements in John (8:58, etc.), (2) God's self-existence statements in Isaiah (Isa 42:8, 43:10-11), and (3) the divine name YHWH throughout the OT. The connection spans the entire canon.",
    "exo.3.14|linguistic|same_lemma|": "Exo 3:14 uses the verb 'hayah' (to be) in the Qal imperfect form ('ehyeh). This same verb appears in the name YHWH. The linguistic connection links all verses where God's identity is tied to the verb 'to be' — His existence is not contingent but essential.",

    # Psalm 23:1
    "psa.23.1|intertextual|direct_quotation|tsk": "Psalm 23:1 ('The LORD is my shepherd') is one of the most recognized verses. Cross-references connect it to: John 10:11 (Jesus the Good Shepherd), Isaiah 40:11 (He shall feed His flock like a shepherd), and Ezekiel 34 (the shepherds of Israel). The shepherd metaphor is one of the most important biblical images for God's relationship with His people.",
    "psa.23.1|linguistic|same_root|": "The word for 'shepherd' (ro'eh) shares a root with 'shepherd' (ra'ah — to pasture/tend). All occurrences of shepherding language in the OT share this root, forming a semantic network that connects pastoral care with divine leadership.",

    # Isaiah 53 — Suffering Servant
    "isa.53.5|intertextual|direct_quotation|tsk": "Isaiah 53:5 ('He was wounded for our transgressions') is the center of the Suffering Servant passage. Cross-references connect it to: 1 Peter 2:24 (who bore our sins), Matthew 8:17 (bore our sicknesses), and Romans 4:25 (delivered for our offenses). The connection is one of explicit prophetic fulfillment — the NT authors read Isaiah 53 as a direct prophecy of Christ's atonement.",
    "isa.53.5|numerical|same_gematria_standard|": "The gematria value of key words in Isaiah 53:5 relates to divine name values and sacred numbers. The numeric patterns in the Suffering Servant passage suggest intentional design at the level of the Hebrew text itself.",

    # Psalm 119 — Torah meditation
    "psa.119.97|intertextual|direct_quotation|tsk": "Psalm 119:97 ('O how love I thy law! It is my meditation all the day') is the heart of the longest psalm. Cross-references connect it to: Psalm 1:2 (meditate on the law day and night), Deuteronomy 6:6-9 (the Shema), and Joshua 1:8 (meditate on the law). The connection is one of the Torah meditation tradition — the word of God is the object of constant contemplation.",

    # John 1:1
    "john.1.1|intertextual|direct_quotation|tsk": "John 1:1 ('In the beginning was the Word') explicitly echoes Gen 1:1. Cross-references connect it to: Genesis 1:1 (the original creation), Proverbs 8:22-23 (Wisdom as the first of God's works), Colossians 1:15-17 (Christ as the firstborn of creation), and 1 John 1:1 (the Word of life). The connection establishes Jesus as the pre-existent Creator.",
}


def add_explanations(conn):
    count = 0

    for key, explanation in EXPLANATIONS.items():
        parts = key.split("|", 3)  # source|layer|type|subtype
        if len(parts) < 3:
            continue
        source = parts[0]
        layer = parts[1]
        ctype = parts[2]
        subtype = parts[3] if len(parts) > 3 else ""

        # Find the matching connections
        if subtype:
            rows = conn.execute("""
                SELECT id, metadata FROM connections
                WHERE source_verse = ? AND layer = ? AND type = ? AND subtype = ?
            """, (source, layer, ctype, subtype)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, metadata FROM connections
                WHERE source_verse = ? AND layer = ? AND type = ?
            """, (source, layer, ctype)).fetchall()

        for r in rows:
            conn_id = r["id"]
            meta_str = r["metadata"] or "{}"
            try:
                meta = json.loads(meta_str)
            except (json.JSONDecodeError, TypeError):
                meta = {}

            # Only add if no reasoning yet
            if "reasoning" not in meta:
                meta["reasoning"] = explanation
                conn.execute(
                    "UPDATE connections SET metadata = ? WHERE id = ?",
                    (json.dumps(meta), conn_id)
                )
                count += 1

    conn.commit()
    print(f"Explanations added: {count}")
    return count


def main():
    conn = get_db()
    print("=" * 60)
    print("  Adding Connection Explanations")
    print("=" * 60)
    total = add_explanations(conn)
    conn.close()
    print(f"\n  Total: {total} connections with new explanations")


if __name__ == "__main__":
    main()
