#!/usr/bin/env python3
"""Seed G.K. Beale's temple-creation typology connections from 'The Temple and the Church's Mission' (IVP, 2004)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection


# 1. Eden as Temple
EDEN_TEMPLE = [
    ("gen.2.8", "ezek.28.13",
     "Eden was the first temple — the garden of God on the holy mountain. Ezekiel describes the king of Tyre as having been in Eden, the garden of God"),
    ("gen.2.8", "exo.25.8",
     "The garden of Eden as the archetypal sanctuary — God dwelling with man in the garden"),
    ("gen.2.15", "exo.40.34",
     "Adam's commission to 'dress and keep' the garden uses the same verbs as priestly service in the tabernacle"),
    ("gen.2.15", "lev.26.3",
     "The conditions for remaining in the land (Eden-temple) are covenant obedience — the same as remaining in God's presence"),
    ("gen.3.23", "rev.22.14",
     "Expulsion from Eden reverses to re-entry — 'Blessed are they that do his commandments, that they may have right to the tree of life'"),
    ("gen.3.23", "ezek.47.1",
     "The cherubim guarding Eden's east gate correspond to the temple's east-facing entrance"),
]

# 2. Temple as Microcosm
TEMPLE_MICROCOSM = [
    ("exo.25.40", "heb.9.24",
     "The tabernacle as 'the pattern of things in the heavens' — a microcosm of the heavenly temple"),
    ("gen.1.1", "psa.78.69",
     "He built his sanctuary like the high heavens, like the earth which he founded forever"),
    ("exo.25.9", "1chr.28.19",
     "David gave Solomon the pattern of the temple — written by the hand of the Lord, as the tabernacle was shown to Moses"),
    ("gen.1.1", "1kgs.6.1",
     "The temple construction begins exactly 480 years after the Exodus — creation typology"),
    ("gen.1.1", "rev.21.1",
     "The new heavens and new earth are the ultimate temple — God dwelling with man without a sanctuary"),
]

# 3. Temple-as-Creation
TEMPLE_CREATION = [
    ("gen.1.3", "exo.25.31",
     "The golden lampstand parallels the creation of light on day 1 — the menorah as 'light of the world'"),
    ("gen.1.6", "exo.26.1",
     "The firmament dividing waters above from waters below corresponds to the temple veil dividing holy from holy of holies"),
    ("gen.1.9", "exo.26.1",
     "The gathering of waters corresponds to the bronze sea in the temple court"),
    ("gen.1.11", "exo.25.23",
     "The vegetation and trees correspond to the table of showbread — the garden/tree symbolism"),
    ("gen.1.14", "exo.25.31",
     "The lights in the firmament correspond to the lampstand — the menorah's seven branches correspond to the seven planets"),
    ("gen.1.20", "exo.25.18",
     "The birds and fish correspond to the cherubim — creatures of the air and water on the ark"),
    ("gen.1.24", "exo.25.18",
     "The land animals correspond to the cherubim — all creation represented in the temple"),
    ("gen.2.1", "exo.39.32",
     "The completion of heaven and earth echoes the completion of the tabernacle — 'thus was finished all the work'"),
    ("gen.2.2", "exo.31.17",
     "God rested on the seventh day — the Sabbath as a temple day, a day of entering God's rest"),
    ("gen.2.2", "psa.132.8",
     "Arise, O LORD, into thy rest — the temple as God's resting place, like creation's seventh day"),
]

# 4. New Creation Temple
TEMPLE_ESCHATON = [
    ("ezek.40.1", "rev.21.10",
     "Ezekiel's temple vision and John's New Jerusalem — both on a high mountain, both coming from God"),
    ("ezek.47.1", "rev.22.1",
     "The river flowing from the temple parallels the river of life from the throne of God and the Lamb"),
    ("ezek.47.12", "rev.22.2",
     "The trees of life on either side of the river, with leaves for healing — Eden restored"),
    ("rev.21.2", "gen.2.8",
     "New Jerusalem as the restored Eden-temple — the end is like the beginning, but better"),
    ("rev.21.22", "exo.25.8",
     "No temple in the New Jerusalem because God and the Lamb are the temple — the presence is direct, no longer mediated"),
]

# 5. Church as Temple
CHURCH_TEMPLE = [
    ("1cor.3.16", "exo.25.8",
     "Know ye not that ye are the temple of God? — the church continues the temple presence"),
    ("eph.2.21", "1pet.2.5",
     "Ye also, as lively stones, are built up a spiritual house — the church as the new temple"),
    ("john.2.19", "exo.40.34",
     "Destroy this temple, and in three days I will raise it up — Christ's body as the true temple"),
]


def seed_group(conn, label, pairs, tag_subtype):
    count = 0
    for src, tgt, note in pairs:
        try:
            add_connection(conn, src, tgt,
                          layer="sod", type_name="typology",
                          subtype=tag_subtype,
                          strength=0.8, confidence=0.85,
                          discovered_by="human",
                          metadata={
                              "scholar": "G.K. Beale",
                              "source": "The Temple and the Church's Mission",
                              "tag": "beale_temple",
                              "note": note,
                          })
            count += 1
        except Exception:
            pass
    return count


def main():
    conn = get_db()

    print("=" * 60)
    print("  G.K. BEALE — Temple-Creation Typology")
    print("=" * 60)

    print("\n--- Eden as Temple ---", flush=True)
    c1 = seed_group(conn, "1. Eden as Temple", EDEN_TEMPLE, "beale_eden_temple")

    print("\n--- Temple as Microcosm ---", flush=True)
    c2 = seed_group(conn, "2. Temple as Microcosm", TEMPLE_MICROCOSM, "beale_temple_microcosm")

    print("\n--- Temple-as-Creation ---", flush=True)
    c3 = seed_group(conn, "3. Temple-as-Creation", TEMPLE_CREATION, "beale_temple_creation")

    print("\n--- New Creation Temple ---", flush=True)
    c4 = seed_group(conn, "4. New Creation Temple", TEMPLE_ESCHATON, "beale_temple_eschaton")

    print("\n--- Church as Temple ---", flush=True)
    c5 = seed_group(conn, "5. Church as Temple", CHURCH_TEMPLE, "beale_church_temple")

    conn.commit()

    total = c1 + c2 + c3 + c4 + c5
    print(f"\n  Total new connections: {total}")

    # Verify
    c = conn.execute("SELECT COUNT(*) FROM connections WHERE metadata LIKE '%beale_temple%'").fetchone()[0]
    print(f"  Beale connections: {c}")
    conn.close()


if __name__ == "__main__":
    main()
