#!/usr/bin/env python3
"""Seed ~25 connections following Michael Heiser's divine council theology."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import add_connection, get_db

CONNECTIONS = [
    # 1. Divine council
    {
        "source": "deu.32.8", "target": "deu.32.9", "type": "divine_council", "strength": 0.95,
        "note": "When the Most High divided the nations... he set the bounds of the people according to the number of the sons of God. For the LORD's portion is his people, Jacob the lot of his inheritance",
    },
    {
        "source": "deu.32.8", "target": "psa.82.8", "type": "divine_council", "strength": 0.9,
        "note": "The sons of God / divine council — YHWH's inheritance is Israel, the other nations assigned to other elohim",
    },
    {
        "source": "deu.32.8", "target": "dan.10.13", "type": "divine_council", "strength": 0.85,
        "note": "The prince of Persia withstood me — the national elohim of Deuteronomy 32 in action. Territorial spirits over the nations",
    },
    {
        "source": "psa.82.1", "target": "john.10.34", "type": "divine_council", "strength": 0.9,
        "note": "Jesus quotes Psalm 82 — 'I said, Ye are gods' — the divine council members judged for injustice",
    },
    {
        "source": "psa.82.6", "target": "heb.2.5", "type": "divine_council", "strength": 0.8,
        "note": "The world to come is not put in subjection to angels — the divine council's role is being superseded by the Son",
    },
    {
        "source": "1kgs.22.19", "target": "job.1.6", "type": "divine_council", "strength": 0.85,
        "note": "Micaiah's vision of the heavenly host and Job's sons of God presenting themselves — the same divine council",
    },
    {
        "source": "job.1.6", "target": "job.2.1", "type": "divine_council", "strength": 0.9,
        "note": "The sons of God presenting themselves before YHWH, and Satan also among them — the council in session",
    },
    {
        "source": "isa.14.13", "target": "psa.48.2", "type": "divine_council", "strength": 0.8,
        "note": "The 'mount of the congregation in the sides of the north' — the divine council's mountain assembly",
    },
    {
        "source": "isa.14.13", "target": "ezek.28.14", "type": "divine_council", "strength": 0.8,
        "note": "The mount of God, the divine council, where the king of Babylon and the king of Tyre sought to ascend",
    },
    # 2. Divine family / sons of God
    {
        "source": "gen.6.1", "target": "job.1.6", "type": "divine_council", "strength": 0.85,
        "note": "The sons of God in Genesis 6 who took wives are the same divine council beings — the Watcher tradition",
    },
    {
        "source": "gen.6.2", "target": "jude.1.6", "type": "divine_council", "strength": 0.85,
        "note": "The Watchers who kept not their first estate — the sin of the divine council members bound in chains",
    },
    {
        "source": "gen.6.4", "target": "2pet.2.4", "type": "divine_council", "strength": 0.85,
        "note": "God spared not the angels that sinned, but cast them down to hell — the Watcher judgment",
    },
    {
        "source": "exo.4.22", "target": "hos.11.1", "type": "divine_council", "strength": 0.9,
        "note": "Israel is my son, even my firstborn — the corporate sonship of Israel, distinct from the divine council",
    },
    {
        "source": "rom.8.14", "target": "gal.3.26", "type": "divine_council", "strength": 0.85,
        "note": "Ye are all the children of God by faith in Christ Jesus — believers join the divine family",
    },
    {
        "source": "eph.1.10", "target": "col.1.16", "type": "divine_council", "strength": 0.8,
        "note": "He might gather together in one all things in Christ — the reunification of the divided nations",
    },
    # 3. Deuteronomy 32 worldview
    {
        "source": "deu.32.8", "target": "acts.17.26", "type": "divine_council", "strength": 0.85,
        "note": "Paul's 'determined the bounds of their habitation' echoes Deuteronomy 32 — the allocation of nations under divine council governance",
    },
    {
        "source": "deu.32.8", "target": "rom.1.18", "type": "divine_council", "strength": 0.75,
        "note": "The wrath of God against ungodliness — the nations under the elohim went into darkness and idolatry",
    },
    {
        "source": "deu.32.9", "target": "eph.1.18", "type": "divine_council", "strength": 0.75,
        "note": "The riches of the glory of his inheritance in the saints — the great reversal: Israel's inheritance and now the church's",
    },
    {
        "source": "deu.32.8", "target": "rev.11.15", "type": "divine_council", "strength": 0.85,
        "note": "The kingdoms of this world are become the kingdoms of our Lord and of his Christ — the restoration of the nations to YHWH",
    },
    {
        "source": "deu.32.8", "target": "mat.28.19", "type": "divine_council", "strength": 0.85,
        "note": "Go ye therefore and teach all nations — the Great Commission reclaims the nations for YHWH",
    },
    # 4. Angel of YHWH as divine being
    {
        "source": "exo.23.21", "target": "exo.3.2", "type": "angel_of_yhwh", "strength": 0.9,
        "note": "The angel in whom YHWH's name is — the same angel who appeared in the burning bush, speaking as YHWH",
    },
    {
        "source": "josh.5.13", "target": "exo.3.2", "type": "angel_of_yhwh", "strength": 0.85,
        "note": "The captain of the Lord's host — a pre-incarnate Christophany, commander of the heavenly army",
    },
    {
        "source": "judg.6.11", "target": "gen.16.7", "type": "angel_of_yhwh", "strength": 0.85,
        "note": "The Angel of YHWH appears to Gideon and to Hagar — the same divine messenger who speaks as God",
    },
    # 5. Elohim terminology
    {
        "source": "psa.82.1", "target": "exo.22.28", "type": "divine_council", "strength": 0.85,
        "note": "Ye are gods (elohim) — the divine council members, called elohim, appointed over the nations",
    },
    {
        "source": "exo.22.28", "target": "heb.2.5", "type": "divine_council", "strength": 0.75,
        "note": "Thou shalt not revile the gods (elohim) — the divine council as governing authorities",
    },
    {
        "source": "psa.86.8", "target": "psa.89.6", "type": "divine_council", "strength": 0.8,
        "note": "Among the gods (elohim) there is none like unto thee, O Lord — YHWH as supreme over the council",
    },
    {
        "source": "psa.89.6", "target": "dan.10.13", "type": "divine_council", "strength": 0.8,
        "note": "The elohim of the nations — the spiritual powers behind earthly kingdoms",
    },
]

_META = {"scholar": "Michael S. Heiser", "source": "The Unseen Realm", "tag": "heiser_council"}

def main():
    db = get_db()
    inserted = 0
    for c in CONNECTIONS:
        meta = dict(_META, note=c["note"])
        add_connection(db, c["source"], c["target"], "sod", c["type"],
                       strength=c["strength"], discovered_by="human", metadata=meta)
        inserted += 1
    print(f"Processed {inserted} Heiser connections")

    cursor = db.execute(
        "SELECT COUNT(*) FROM connections WHERE json_extract(metadata, '$.tag') = 'heiser_council'"
    )
    total = cursor.fetchone()[0]
    print(f"Total Heiser connections in DB: {total}")
    db.close()

if __name__ == "__main__":
    main()
