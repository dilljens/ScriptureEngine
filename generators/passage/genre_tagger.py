"""
Genre Tagger — classify passages by literary genre and create same-genre connections.

Two passes:
  1. Book-level default genres (known genre per book)
  2. Structural marker detection (refine per-passage using structural_formulas table)

Output: passage_genres table entries + passage_connections for same-genre groups.
"""

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Book-level genre defaults ────────────────────────────────────────
# Based on standard biblical genre classifications (longenecker, alter, gunkel)
# Format: { book_id: [(genre, subgenre, confidence, start_verse, end_verse), ...] }

BOOK_GENRES: dict[str, list[tuple[str, str, float, str, str]]] = {
    # ── Torah / Pentateuch ──
    "gen": [
        ("historical_narrative", "patriarchal_narrative", 0.9, "gen.1.1", "gen.50.26"),
        ("genealogy", "lineal_genealogy", 0.8, "gen.5.1", "gen.5.32"),
        ("genealogy", "table_of_nations", 0.9, "gen.10.1", "gen.10.32"),
        ("genealogy", "lineal_genealogy", 0.8, "gen.11.10", "gen.11.32"),
    ],
    "exod": [
        ("historical_narrative", "deliverance_narrative", 0.9, "exod.1.1", "exod.18.27"),
        ("legal", "covenant_code", 0.9, "exod.20.1", "exod.23.33"),
        ("legal", "tabernacle_instructions", 0.9, "exod.25.1", "exod.31.18"),
        ("historical_narrative", "golden_calf", 0.8, "exod.32.1", "exod.34.35"),
        ("legal", "tabernacle_construction", 0.9, "exod.35.1", "exod.40.38"),
    ],
    "lev": [
        ("legal", "sacrificial_law", 0.9, "lev.1.1", "lev.7.38"),
        ("legal", "priestly_code", 0.9, "lev.8.1", "lev.10.20"),
        ("legal", "purity_law", 0.9, "lev.11.1", "lev.15.33"),
        ("legal", "holiness_code", 0.9, "lev.17.1", "lev.26.46"),
    ],
    "num": [
        ("historical_narrative", "wilderness_narrative", 0.9, "num.1.1", "num.36.13"),
        ("genealogy", "census", 0.9, "num.1.1", "num.4.49"),
        ("legal", "supplementary_law", 0.8, "num.5.1", "num.10.10"),
    ],
    "deut": [
        ("legal", "deuteronomic_code", 0.9, "deut.12.1", "deut.26.19"),
        ("covenant_suit", "moses_farewell", 0.9, "deut.28.1", "deut.30.20"),
        ("song_hymn", "song_of_moses", 0.9, "deut.32.1", "deut.32.47"),
        ("prophecy_oracle", "blessing_of_moses", 0.8, "deut.33.1", "deut.33.29"),
    ],

    # ── Historical Books ──
    "josh": [("historical_narrative", "conquest_narrative", 0.9, "josh.1.1", "josh.24.33")],
    "judg": [("historical_narrative", "judges_cycle", 0.9, "judg.1.1", "judg.21.25")],
    "ruth": [("historical_narrative", "idyll", 0.9, "ruth.1.1", "ruth.4.22")],
    "1sam": [("historical_narrative", "prophetic_history", 0.9, "1sam.1.1", "1sam.31.13")],
    "2sam": [("historical_narrative", "prophetic_history", 0.9, "2sam.1.1", "2sam.24.25")],
    "1kgs": [("historical_narrative", "prophetic_history", 0.9, "1kgs.1.1", "1kgs.22.53")],
    "2kgs": [("historical_narrative", "prophetic_history", 0.9, "2kgs.1.1", "2kgs.25.30")],
    "1chr": [("historical_narrative", "chronicle", 0.9, "1chr.1.1", "1chr.29.30")],
    "2chr": [("historical_narrative", "chronicle", 0.9, "2chr.1.1", "2chr.36.23")],
    "ezra": [("historical_narrative", "restoration_narrative", 0.9, "ezra.1.1", "ezra.10.44")],
    "neh": [("historical_narrative", "restoration_narrative", 0.9, "neh.1.1", "neh.13.31")],
    "esth": [("historical_narrative", "court_tale", 0.9, "esth.1.1", "esth.10.3")],

    # ── Wisdom / Writings ──
    "job": [("wisdom", "disputation", 0.9, "job.1.1", "job.42.17")],
    "psa": [("psalm", "psalter", 0.9, "psa.1.1", "psa.150.6")],
    "prov": [("wisdom", "proverb", 0.9, "prov.1.1", "prov.31.31")],
    "eccl": [("wisdom", "reflection", 0.9, "eccl.1.1", "eccl.12.14")],
    "song": [("song_hymn", "love_poetry", 0.9, "song.1.1", "song.8.14")],

    # ── Major Prophets ──
    "isa": [
        ("prophecy_oracle", "judgment_oracle", 0.85, "isa.1.1", "isa.39.8"),
        ("prophecy_oracle", "salvation_oracle", 0.85, "isa.40.1", "isa.55.13"),
        ("prophecy_oracle", "trito_isaiah", 0.8, "isa.56.1", "isa.66.24"),
    ],
    "jer": [
        ("prophecy_oracle", "judgment_oracle", 0.9, "jer.1.1", "jer.52.34"),
        ("lament", "jeremiad", 0.9, "jer.1.1", "jer.52.34"),
    ],
    "lam": [("lament", "communal_lament", 0.9, "lam.1.1", "lam.5.22")],
    "ezek": [
        ("vision_report", "throne_vision", 0.9, "ezek.1.1", "ezek.3.27"),
        ("prophecy_oracle", "judgment_oracle", 0.85, "ezek.4.1", "ezek.32.32"),
        ("vision_report", "valley_of_bones", 0.9, "ezek.37.1", "ezek.37.28"),
        ("vision_report", "temple_vision", 0.9, "ezek.40.1", "ezek.48.35"),
    ],
    "dan": [
        ("historical_narrative", "court_tale", 0.85, "dan.1.1", "dan.6.28"),
        ("apocalyptic", "vision_report", 0.9, "dan.7.1", "dan.12.13"),
    ],

    # ── Minor Prophets ──
    "hos": [("prophecy_oracle", "judgment_oracle", 0.85, "hos.1.1", "hos.14.9")],
    "joel": [
        ("prophecy_oracle", "judgment_oracle", 0.8, "joel.1.1", "joel.2.32"),
        ("apocalyptic", "end_times", 0.8, "joel.2.28", "joel.3.21"),
    ],
    "amos": [("prophecy_oracle", "judgment_oracle", 0.9, "amos.1.1", "amos.9.15")],
    "obad": [("prophecy_oracle", "judgment_oracle", 0.9, "obad.1.1", "obad.1.21")],
    "jonah": [("historical_narrative", "prophetic_narrative", 0.9, "jonah.1.1", "jonah.4.11")],
    "mic": [("prophecy_oracle", "judgment_oracle", 0.85, "mic.1.1", "mic.7.20")],
    "nahum": [("prophecy_oracle", "judgment_oracle", 0.9, "nahum.1.1", "nahum.3.19")],
    "hab": [("prophecy_oracle", "judgment_oracle", 0.85, "hab.1.1", "hab.3.19")],
    "zeph": [("prophecy_oracle", "judgment_oracle", 0.85, "zeph.1.1", "zeph.3.20")],
    "hag": [("prophecy_oracle", "salvation_oracle", 0.85, "hag.1.1", "hag.2.23")],
    "zech": [
        ("vision_report", "night_visions", 0.9, "zech.1.1", "zech.6.15"),
        ("prophecy_oracle", "salvation_oracle", 0.8, "zech.7.1", "zech.14.21"),
    ],
    "mal": [("prophecy_oracle", "judgment_oracle", 0.85, "mal.1.1", "mal.4.6")],

    # ── Gospels ──
    "matt": [("gospel", "synoptic", 0.9, "matt.1.1", "matt.28.20")],
    "mark": [("gospel", "synoptic", 0.9, "mark.1.1", "mark.16.20")],
    "luke": [("gospel", "synoptic", 0.9, "luke.1.1", "luke.24.53")],
    "john": [("gospel", "johannine", 0.9, "john.1.1", "john.21.25")],

    # ── Acts ──
    "acts": [("historical_narrative", "apostolic_history", 0.9, "acts.1.1", "acts.28.31")],

    # ── Pauline Epistles ──
    "rom": [("epistle", "pauline", 0.9, "rom.1.1", "rom.16.27")],
    "1cor": [("epistle", "pauline", 0.9, "1cor.1.1", "1cor.16.24")],
    "2cor": [("epistle", "pauline", 0.9, "2cor.1.1", "2cor.13.14")],
    "gal": [("epistle", "pauline", 0.9, "gal.1.1", "gal.6.18")],
    "eph": [("epistle", "pauline", 0.9, "eph.1.1", "eph.6.24")],
    "phil": [("epistle", "pauline", 0.9, "phil.1.1", "phil.4.23")],
    "col": [("epistle", "pauline", 0.9, "col.1.1", "col.4.18")],
    "1thess": [("epistle", "pauline", 0.9, "1thess.1.1", "1thess.5.28")],
    "2thess": [("epistle", "pauline", 0.9, "2thess.1.1", "2thess.3.18")],
    "1tim": [("epistle", "pastoral", 0.9, "1tim.1.1", "1tim.6.21")],
    "2tim": [("epistle", "pastoral", 0.9, "2tim.1.1", "2tim.4.22")],
    "titus": [("epistle", "pastoral", 0.9, "titus.1.1", "titus.3.15")],
    "phlm": [("epistle", "pauline", 0.9, "phlm.1.1", "phlm.1.25")],

    # ── General Epistles ──
    "heb": [("epistle", "homily", 0.9, "heb.1.1", "heb.13.25")],
    "james": [("epistle", "general", 0.9, "james.1.1", "james.5.20")],
    "1pet": [("epistle", "general", 0.9, "1pet.1.1", "1pet.5.14")],
    "2pet": [("epistle", "general", 0.9, "2pet.1.1", "2pet.3.18")],
    "1john": [("epistle", "general", 0.9, "1john.1.1", "1john.5.21")],
    "2john": [("epistle", "general", 0.9, "2john.1.1", "2john.1.13")],
    "3john": [("epistle", "general", 0.9, "3john.1.1", "3john.1.15")],
    "jude": [("epistle", "general", 0.9, "jude.1.1", "jude.1.25")],

    # ── Apocalyptic ──
    "rev": [
        ("apocalyptic", "apocalypse", 0.95, "rev.1.1", "rev.22.21"),
        ("epistle", "prophetic_letter", 0.85, "rev.2.1", "rev.3.22"),
        ("vision_report", "heavenly_throne", 0.9, "rev.4.1", "rev.5.14"),
    ],

    # ── Deuterocanon / Apocrypha ──
    "tob": [("wisdom", "didactic_narrative", 0.8, "tob.1.1", "tob.14.15")],
    "judith": [("historical_narrative", "didactic_narrative", 0.8, "judith.1.1", "judith.16.25")],
    "wis": [("wisdom", "reflection", 0.9, "wis.1.1", "wis.19.22")],
    "sir": [("wisdom", "proverb", 0.9, "sir.1.1", "sir.51.30")],
    "bar": [("prophecy_oracle", "judgment_oracle", 0.8, "bar.1.1", "bar.6.72")],
    "1ma": [("historical_narrative", "maccabean_history", 0.9, "1ma.1.1", "1ma.16.24")],
    "2ma": [("historical_narrative", "maccabean_history", 0.85, "2ma.1.1", "2ma.15.39")],
    "1esd": [("historical_narrative", "restoration_narrative", 0.8, "1esd.1.1", "1esd.9.55")],
    "2esd": [("apocalyptic", "vision_report", 0.85, "2esd.1.1", "2esd.16.78")],
    "prayer_man": [("lament", "penitential", 0.8, "prman.1.1", "prman.1.15")],
    "song_three": [("song_hymn", "thanksgiving", 0.8, "song3.1.1", "song3.1.68")],
    "susanna": [("historical_narrative", "court_tale", 0.8, "sus.1.1", "sus.1.64")],
    "bel": [("historical_narrative", "court_tale", 0.8, "bel.1.1", "bel.1.42")],

    # ── Pseudepigrapha (selected) ──
    "1en": [("apocalyptic", "vision_report", 0.85, "1en.1.1", "1en.108.15")],
    "jub": [("historical_narrative", "rewritten_bible", 0.85, "jub.1.1", "jub.50.13")],
    "asmp": [("apocalyptic", "testament", 0.7, "asmp.1.1", "asmp.12.13")],
}


def run(conn, book_ids=None) -> int:
    """Tag passages with genres and create same-genre connections.

    Phase 1: Apply book-level genre defaults from BOOK_GENRES
    Phase 2: Create passage_connections between passages sharing the same genre

    Returns count of passage connections created.
    """
    # Phase 1: Write genre classifications to passage_genres
    tag_count = _write_genres(conn, book_ids)
    logger.info("genre_tagger: %d genre tags written", tag_count)

    # Phase 2: Create same-genre connections
    conn_count = _create_genre_connections(conn)
    logger.info("genre_tagger: %d same-genre passage connections created", conn_count)

    return conn_count


def _write_genres(conn, book_ids=None) -> int:
    """Write genre classifications to passage_genres table."""
    count = 0
    for book_id, genres in BOOK_GENRES.items():
        if book_ids and book_id not in book_ids:
            continue
        for genre, subgenre, confidence, start, end in genres:
            try:
                conn.execute("""
                    INSERT INTO passage_genres (start_verse, end_verse, genre, subgenre, confidence, assigned_by, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(start_verse, end_verse, genre) DO UPDATE SET
                        subgenre=excluded.subgenre, confidence=excluded.confidence
                """, (start, end, genre, subgenre, confidence, "algorithm",
                      f"Book-level default for {book_id}"))
                count += 1
            except Exception as e:
                logger.warning("genre_tagger: insert error for %s: %s", book_id, e)
    conn.commit()
    return count


def _create_genre_connections(conn) -> int:
    """Create passage_connections between passages sharing the same genre."""
    # Get all genre classifications
    rows = conn.execute("""
        SELECT genre, subgenre, start_verse, end_verse
        FROM passage_genres
        ORDER BY genre, subgenre
    """).fetchall()

    if not rows:
        return 0

    # Group by genre+subgenre
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        key = f"{r['genre']}:{r['subgenre']}"
        groups[key].append(dict(r))

    count = 0
    for key, passages in groups.items():
        genre, subgenre = key.split(":", 1)
        if len(passages) < 2:
            continue

        # Create passage_connections for each pair within the same genre
        for i in range(len(passages)):
            for j in range(i + 1, len(passages)):
                a, b = passages[i], passages[j]
                if a["start_verse"] == b["start_verse"] and a["end_verse"] == b["end_verse"]:
                    continue  # Skip self-pairs

                metadata = json.dumps({
                    "genre": genre,
                    "subgenre": subgenre,
                    "source": "genre_tagger",
                })

                try:
                    conn.execute("""
                        INSERT INTO passage_connections
                            (source_start, source_end, target_start, target_end, layer, type,
                             strength, confidence, discovered_by, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(source_start, source_end, target_start, target_end, layer, type, subtype)
                        DO NOTHING
                    """, (
                        a["start_verse"], a["end_verse"],
                        b["start_verse"], b["end_verse"],
                        "interpretive", "pericope_parallel" if genre == "historical_narrative" else genre,
                        0.8, 0.8,
                        "algorithm", metadata,
                    ))
                    count += 1
                except Exception as e:
                    logger.warning("genre_tagger: connection error: %s", e)

    conn.commit()
    return count
