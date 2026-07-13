"""Chronological marker generator — chronological_marker connections.

Connects verses that share chronological time reference formulas:
  - Regnal years ("in the X year of King Y")
  - Prophetic time markers ("in that day", "in those days", "after these things")
  - Age references ("at the age of X")
  - Seasonal markers ("in the spring", "at harvest time")
  - Sequential markers ("after this", "before that", "when")
"""

import re
from collections import defaultdict

# Time marker patterns: (regex, marker_name, description)
TIME_MARKERS = [
    # Regnal and dating formulas
    (r"\bin the \w+ year of\b", "regnal_year", "Regnal dating formula"),
    (r"\bin the year\b", "year_formula", "Year reference"),
    (r"\bin the \d+th year\b", "numbered_year", "Numbered year"),
    (r"\bthe \d+th day of the \w+ month\b", "exact_date", "Exact date"),
    (r"\bin the \w+ month\b", "month_reference", "Month reference"),

    # Prophetic formulas
    (r"\bin that day\b", "in_that_day", "Prophetic 'in that day'"),
    (r"\bin those days\b", "in_those_days", "Time period reference"),
    (r"\bat that time\b", "at_that_time", "Temporal marker"),
    (r"\bthe day of the (lord|lord's|yahweh)\b", "day_of_the_lord", "Day of the Lord"),
    (r"\bin the latter days\b", "latter_days", "Eschatological time"),
    (r"\bin the last days\b", "last_days", "Eschatological time"),
    (r"\bthe end of days\b", "end_of_days", "Eschatological time"),

    # Sequential markers
    (r"\bafter these things?\b", "after_these", "Sequential marker"),
    (r"\bafter this\b", "after_this", "Sequential marker"),
    (r"\bfrom that (day|time|hour) forward\b", "from_then", "Temporal transition"),
    (r"\bfrom that time\b", "from_that_time", "Temporal transition"),
    (r"\bfrom the beginning\b", "from_beginning", "Origin reference"),

    # Age references
    (r"\bat the age of\b", "age_reference", "Age reference"),
    (r"\bwas \d+ years old\b", "specific_age", "Specific age"),
    (r"\blived \d+ years\b", "lifespan", "Lifespan reference"),

    # Seasonal and cyclical
    (r"\b(time of harvest|harvest time)\b", "harvest_time", "Harvest season"),
    (r"\bin the spring\b", "spring", "Spring season"),
    (r"\bin the autumn\b", "autumn", "Autumn season"),
    (r"\bat the end of \d+ years\b", "cycle_end", "Cyclical end"),
    (r"\bfrom year to year\b", "yearly", "Annual reference"),
    (r"\bday by day\b", "daily", "Daily reference"),

    # Covenant/patriarchal time formulas (Book of Mormon style)
    (r"\band it came to pass that\b", "it_came_to_pass", "Narrative transition"),
    (r"\band thus we see\b", "thus_we_see", "Moral observation"),
    (r"\bnow it came to pass\b", "now_it_came_to_pass", "Narrative opening"),
    (r"\bnow after\b", "now_after", "Temporal transition"),
    (r"\band it came to pass in\b", "it_came_to_pass_in", "Dated narrative transition"),
]


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Generate chronological marker connections.

    For each time marker pattern, find all verses containing it,
    then connect verses sharing the same marker type.

    Returns count of connections created.
    """
    count = 0
    batch = []

    # Get all English verse text
    query = """
        SELECT id, text_english FROM verses
        WHERE text_english != ''
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" AND book_id IN ({placeholders})"
    rows = conn.execute(query).fetchall()

    print(f"  Scanning {len(rows)} verses for chronological markers...", flush=True)

    # Build marker->verses index
    marker_verses = defaultdict(set)
    for r in rows:
        verse_id = r[0]
        text = r["text_english"] or ""
        text_lower = text.lower()
        for pattern, marker_name, _description in TIME_MARKERS:
            if re.search(pattern, text_lower):
                marker_verses[marker_name].add(verse_id)

    print(f"  Found {len(marker_verses)} marker types with verses")

    # Connect verses sharing the same marker type
    for marker_name, verses in marker_verses.items():
        if len(verses) < 2:
            continue

        verse_list = sorted(verses)

        # Hub-and-spoke for very common markers (it_came_to_pass)
        if len(verse_list) > 50:
            hub = verse_list[0]
            for v in verse_list[1:]:
                batch.append((
                    hub, v, "chronological",
                    "chronological_marker", marker_name,
                    0.45, 0.5, "algorithm",
                    '{"marker": "' + marker_name + '"}'
                ))
                count += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
        elif len(verse_list) <= 30:
            # Full mesh for less common markers
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    batch.append((
                        verse_list[i], verse_list[j], "chronological",
                        "chronological_marker", marker_name,
                        0.5, 0.55, "algorithm",
                        '{"marker": "' + marker_name + '"}'
                    ))
                    count += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
        else:
            # Middle ground: connect adjacent in sorted order
            for i in range(len(verse_list) - 1):
                batch.append((
                    verse_list[i], verse_list[i + 1], "chronological",
                    "chronological_marker", marker_name,
                    0.45, 0.5, "algorithm",
                    '{"marker": "' + marker_name + '"}'
                ))
                count += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Chronological Markers: {count} connections")
    return count
