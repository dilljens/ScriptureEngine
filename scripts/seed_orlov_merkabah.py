"""Seed ~20 scholarly connections for Orlov's Enoch-Metatron and Schäfer's Hekhalot traditions."""

from lib.db import get_db

CONNECTIONS = [
    # ── Enoch-Metatron tradition (orlov_merkabah) ──
    {
        "source": "gen.5.24", "target": "heb.11.5",
        "type": "heavenly_ascent",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "Enoch walked with God and was not — the first human translated to heaven, template for mystical ascent"
        }
    },
    {
        "source": "ezek.1.1", "target": "rev.4.1",
        "type": "merkabah",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "Ezekiel's vision of the chariot (merkabah) and John's vision of the heavenly throne — the same throne vision tradition"
        }
    },
    {
        "source": "ezek.1.26", "target": "dan.7.9",
        "type": "merkabah",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "The throne of sapphire stone in Ezekiel and the Ancient of Days in Daniel — the merkabah tradition develops"
        }
    },
    {
        "source": "dan.7.9", "target": "rev.4.2",
        "type": "theophany",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "The Ancient of Days on his throne and, in Revelation, the One seated on the throne — the same theophanic tradition"
        }
    },
    {
        "source": "isa.6.1", "target": "1kgs.22.19",
        "type": "heavenly_council",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "Isaiah's vision of YHWH in the temple and Micaiah's vision of the heavenly court — prophetic participation in the celestial council"
        }
    },
    {
        "source": "dan.10.5", "target": "rev.1.13",
        "type": "angelophany",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "A man clothed in linen with a golden girdle — the angelophany pattern shared between Daniel and Revelation"
        }
    },

    # ── Two powers in heaven (orlov_merkabah / schafer_hekhalot) ──
    {
        "source": "exo.23.21", "target": "exo.24.1",
        "type": "two_powers",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "The angel in whom YHWH's name dwells — a distinct divine being, the 'lesser YHWH'"
        }
    },
    {
        "source": "exo.24.1", "target": "deu.4.36",
        "type": "two_powers",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "The sons of the gods/God and the voice from heaven — the 'two powers' tradition in the Sinai revelation"
        }
    },
    {
        "source": "psa.110.1", "target": "heb.1.13",
        "type": "two_powers",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "'The Lord said unto my Lord, Sit thou at my right hand' — the two Lords in heaven, foundational for Christology"
        }
    },
    {
        "source": "psa.110.1", "target": "acts.7.55",
        "type": "two_powers",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "Stephen sees Jesus standing at the right hand of God — the two powers tradition fulfilled"
        }
    },
    {
        "source": "jude.1.14", "target": "dan.7.13",
        "type": "divine_mediator",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "Enoch's prophecy and Daniel's Son of Man — the divine mediator figure"
        }
    },

    # ── Heavenly ascent (orlov_merkabah) ──
    {
        "source": "2cor.12.2", "target": "ezek.1.1",
        "type": "heavenly_ascent",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "Paul caught up to the third heaven — a merkabah-style ascent like Ezekiel's"
        }
    },
    {
        "source": "2cor.12.2", "target": "1kgs.22.19",
        "type": "heavenly_ascent",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "Paul's ascent parallels Micaiah's vision — seeing into the heavenly council"
        }
    },

    # ── Angelic transformation / theosis (orlov_merkabah) ──
    {
        "source": "ezek.1.26", "target": "dan.7.9",
        "type": "angelomorphic",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "The appearance of a man on the throne — human-like form on the divine throne, key to angelomorphic Christology"
        }
    },
    {
        "source": "ezek.1.26", "target": "phil.2.5",
        "type": "angelomorphic",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "The human form on the throne prefigures Christ's human-divine nature"
        }
    },
    {
        "source": "exo.24.9", "target": "exo.33.20",
        "type": "theosis",
        "metadata": {
            "scholar": "Andrei Orlov",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
            "note": "The elders saw God and ate in his presence — the ultimate ascent, seeing God and living"
        }
    },

    # ── Hekhalot literature (schafer_hekhalot) ──
    {
        "source": "ezek.1.1", "target": "song.1.1",
        "type": "hekhalot",
        "metadata": {
            "scholar": "Peter Schäfer",
            "source": "The Origins of Jewish Mysticism",
            "tag": "schafer_hekhalot",
            "note": "Ezekiel's merkabah and the Song of Solomon — the Song as liturgical text for Hekhalot mysticism"
        }
    },
    {
        "source": "ezek.1.1", "target": "isa.6.1",
        "type": "hekhalot",
        "metadata": {
            "scholar": "Peter Schäfer",
            "source": "The Origins of Jewish Mysticism",
            "tag": "schafer_hekhalot",
            "note": "The two great throne visions that become the foundation for Hekhalot literature — Ezekiel and Isaiah"
        }
    },
    {
        "source": "song.1.1", "target": "1kgs.22.19",
        "type": "hekhalot",
        "metadata": {
            "scholar": "Peter Schäfer",
            "source": "The Origins of Jewish Mysticism",
            "tag": "schafer_hekhalot",
            "note": "The Song of Solomon used by Hekhalot mystics as a liturgical guide for heavenly ascent"
        }
    },
]


def seed():
    db = get_db()
    count = 0
    skipped = 0

    for c in CONNECTIONS:
        # Verify both verses exist
        src_ok = db.execute("SELECT 1 FROM verses WHERE id = ?", (c["source"],)).fetchone()
        tgt_ok = db.execute("SELECT 1 FROM verses WHERE id = ?", (c["target"],)).fetchone()
        if not src_ok:
            print(f"  SKIP  {c['source']} — verse not in database")
            skipped += 1
            continue
        if not tgt_ok:
            print(f"  SKIP  {c['target']} — verse not in database")
            skipped += 1
            continue

        # Check for duplicates so we can skip gracefully
        existing = db.execute(
            """SELECT id FROM connections
               WHERE source_verse = ? AND target_verse = ?
               AND layer = 'sod' AND type = ? AND subtype = ''""",
            (c["source"], c["target"], c["type"]),
        ).fetchone()

        if existing:
            print(f"  SKIP  {c['source']} → {c['target']}  (already exists)")
            skipped += 1
            continue

        db.execute(
            """INSERT INTO connections
               (source_verse, target_verse, layer, type, subtype,
                strength, confidence, discovered_by, metadata,
                quality_level, hermeneutic)
               VALUES (?, ?, 'sod', ?, '', 0.7, 0.8, 'human', ?, 'scholarly', ?)""",
            (c["source"], c["target"], c["type"],
             __import__("json").dumps(c["metadata"]),
             c["metadata"]["note"]),
        )
        count += 1
        tag = c["metadata"]["tag"]
        print(f"  OK    {c['source']} → {c['target']}  [{tag}]")

    db.commit()
    db.close()
    print(f"\nSeeded: {count} connections")
    print(f"Skipped: {skipped}")
    return count


if __name__ == "__main__":
    seed()
