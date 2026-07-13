"""
Label interpretive connections with hermeneutic category.
Adds `hermeneutic` column and maps subtypes → faith / historical_critical / both.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db

HERMENEUTIC_MAP = {
    # Canonical subtypes (from types.py)
    "rabbinic_midrash": "faith",
    "patristic_reading": "faith",
    "reformation_view": "faith",
    "giliadi_pattern": "faith",
    "latter_day_saint_reading": "faith",
    "prophetic_quote": "faith",
    "lectio_divina": "faith",
    "critical_scholarship": "historical_critical",
    # Existing DB subtypes
    "patristic": "faith",
    "reformation": "faith",
    "latter_day_saint": "faith",
    "jewish": "faith",
    "kal_vchomer_how_much_more": "faith",
    "kal_vchomer_how_much_rather": "faith",
    "kal_vchomer_much_more": "faith",
    "joseph_smith_first_vision": "faith",
    "joseph_smith_marvelous_work": "faith",
    "joseph_smith_translation": "faith",
    "joseph_branch": "faith",
    "stick_of_joseph": "faith",
    "barker_temple_theology": "faith",
    "mercy_and_truth_atonement": "faith",
    "holy_ground_access": "faith",
    "holy_ghost_teacher": "faith",
    "bless_the_lord": "faith",
    "good_shepherd": "faith",
    "living_water": "faith",
    "living_water_temple": "faith",
    "jacobs_ladder": "faith",
    "taste_and_see": "faith",
    "one_thing_necessary": "faith",
    "torah_meditation": "faith",
    "new_heart_new_birth": "faith",
    "true_false_worship": "faith",
    "pilgrim_joy": "faith",
    "water_of_life": "faith",
    "zion_built_up": "faith",
    "throne_vision": "faith",
    "benediction_fulfillment": "faith",
    "elijah_return": "faith",
    "gathering_of_israel": "faith",
    "restoration_gospel_preached": "faith",
    "temple_gathering": "faith",
    "wilderness_testing": "faith",
    "sealed_book": "faith",
    "tithe_law": "faith",
    "jubilee_reading": "faith",
    "other_sheep": "faith",
    "beatitudes_contemplation": "faith",
    "nearness_kills": "faith",
    "end_times_comparison": "faith",
    "bridal_mysticism": "faith",
    "aaron_excuse": "faith",
    "yhw_violation": "faith",
    "spiritual_level_babylon": "faith",
    "spiritual_level_israel": "faith",
    "spiritual_level_jehovah": "faith",
    "spiritual_level_perdition": "faith",
    "spiritual_level_seraphim": "faith",
    "spiritual_level_sons_daughters": "faith",
    "spiritual_level_zion": "faith",
    "x_babylon": "faith",
    "x_israel": "faith",
    "x_jehovah": "faith",
    "x_perdition": "faith",
    "x_seraphim": "faith",
    "x_sons_daughters": "faith",
    "x_zion": "faith",
    "mukdam_umeuchar_01": "faith",
    "mukdam_umeuchar_02": "faith",
    "mukdam_umeuchar_03": "faith",
    "mukdam_umeuchar_04": "faith",
    "mukdam_umeuchar_05": "faith",
    "mukdam_umeuchar_06": "faith",
    "mukdam_umeuchar_07": "faith",
    "mukdam_umeuchar_08": "faith",
    "mukdam_umeuchar_09": "faith",
    # Historical-critical readings
    "critical": "historical_critical",
}


def main():
    conn = get_db()

    # Check if column exists
    cols = conn.execute("PRAGMA table_info(connections)").fetchall()
    col_names = {r["name"] for r in cols}
    if "hermeneutic" not in col_names:
        conn.execute(
            "ALTER TABLE connections ADD COLUMN hermeneutic TEXT DEFAULT NULL"
        )
        conn.commit()
        print("Added hermeneutic column to connections table")
    else:
        print("hermeneutic column already exists")

    # Get all interpretive connections
    rows = conn.execute(
        """
        SELECT id, subtype FROM connections
        WHERE layer = 'interpretive'
        """
    ).fetchall()

    updated = 0
    counts = {"faith": 0, "historical_critical": 0, "both": 0}

    for r in rows:
        label = HERMENEUTIC_MAP.get(r["subtype"])
        if label:
            conn.execute(
                "UPDATE connections SET hermeneutic = ? WHERE id = ?",
                (label, r["id"]),
            )
            updated += 1
            counts[label] = counts.get(label, 0) + 1

    conn.commit()

    faith_count = counts.get("faith", 0)
    hc_count = counts.get("historical_critical", 0)
    counts.get("both", 0)
    print(f"Labeled {updated} connections: {faith_count} faith, {hc_count} historical_critical")
    conn.close()


if __name__ == "__main__":
    main()
