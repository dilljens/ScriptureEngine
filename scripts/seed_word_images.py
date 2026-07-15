#!/usr/bin/env python3
"""Seed word images from FreeBibleImages.org for Hebrew vocabulary.

Maps concrete Hebrew nouns to curated Bible illustration images.
Abstract/theological words get conceptual representations.

FreeBibleImages.org provides 1,600+ curated Bible story image sets,
all free for teaching. This script maps Hebrew vocabulary to the
closest image theme.

Usage:
    python3 scripts/seed_word_images.py              # Dry run — show what would be mapped
    python3 scripts/seed_word_images.py --apply      # Actually insert into DB
    python3 scripts/seed_word_images.py --apply --all # Map all 500 words
"""

import argparse
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"
MEM_DB = BASE / "data" / "memorize.db"

# ── FreeBibleImages.org theme → Hebrew word mappings ──
# Each entry maps a conceptual theme to concrete Hebrew words that
# appear in Bible illustrations from FreeBibleImages.org
# Format: (hebrew_word, theme/description, source_url_or_category)

IMAGE_MAP = [
    # ── Creation & Patriarchs (Gen 1-11) ──
    ("אור", "light/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("מים", "water/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("ארץ", "earth/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("יום", "day/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("לילה", "night/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("שמש", "sun/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("ירח", "moon/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("כוכב", "star/creation", "https://freebibleimages.org/illustrations/creation/"),
    ("עץ", "tree/garden-eden", "https://freebibleimages.org/illustrations/eden/"),
    ("נהר", "river/garden-eden", "https://freebibleimages.org/illustrations/eden/"),
    ("אדם", "adam/creation", "https://freebibleimages.org/illustrations/adam-eve/"),
    ("אשה", "eve/creation", "https://freebibleimages.org/illustrations/adam-eve/"),
    ("נח", "noah/ark", "https://freebibleimages.org/illustrations/noah/"),
    ("תבה", "ark/noah", "https://freebibleimages.org/illustrations/noah/"),
    ("מבול", "flood/noah", "https://freebibleimages.org/illustrations/noah/"),
    ("קשת", "rainbow/noah", "https://freebibleimages.org/illustrations/noah/"),

    # ── Patriarchs (Gen 12-50) ──
    ("אברהם", "abraham/patriarch", "https://freebibleimages.org/illustrations/abraham/"),
    ("שרה", "sarah/abraham", "https://freebibleimages.org/illustrations/abraham/"),
    ("יצחק", "isaac/abraham", "https://freebibleimages.org/illustrations/abraham/"),
    ("יעקב", "jacob/patriarch", "https://freebibleimages.org/illustrations/jacob/"),
    ("יוסף", "joseph/egypt", "https://freebibleimages.org/illustrations/joseph/"),
    ("אח", "brother/joseph", "https://freebibleimages.org/illustrations/joseph/"),
    ("חלום", "dream/joseph", "https://freebibleimages.org/illustrations/joseph/"),
    ("בור", "pit/joseph", "https://freebibleimages.org/illustrations/joseph/"),

    # ── Exodus & Wilderness ──
    ("משה", "moses/exodus", "https://freebibleimages.org/illustrations/moses/"),
    ("אהרן", "aaron/priest", "https://freebibleimages.org/illustrations/aaron/"),
    ("פרעה", "pharaoh/egypt", "https://freebibleimages.org/illustrations/exodus/"),
    ("מצרים", "egypt/exodus", "https://freebibleimages.org/illustrations/exodus/"),
    ("ים", "sea/red-sea", "https://freebibleimages.org/illustrations/red-sea/"),
    ("מדבר", "desert/wilderness", "https://freebibleimages.org/illustrations/wilderness/"),
    ("הר", "mountain/sinai", "https://freebibleimages.org/illustrations/sinai/"),
    ("אש", "fire/sinai", "https://freebibleimages.org/illustrations/sinai/"),
    ("ענן", "cloud/sinai", "https://freebibleimages.org/illustrations/sinai/"),
    ("עגל", "calf/idol", "https://freebibleimages.org/illustrations/golden-calf/"),
    ("אוהל", "tent/tabernacle", "https://freebibleimages.org/illustrations/tabernacle/"),
    ("מזבח", "altar/sacrifice", "https://freebibleimages.org/illustrations/tabernacle/"),
    ("מקדש", "temple/jerusalem", "https://freebibleimages.org/illustrations/temple/"),

    # ── Conquest & Judges ──
    ("יהושע", "joshua/conquest", "https://freebibleimages.org/illustrations/joshua/"),
    ("חומה", "wall/jericho", "https://freebibleimages.org/illustrations/jericho/"),
    ("עיר", "city/conquest", "https://freebibleimages.org/illustrations/joshua/"),
    ("שמשון", "samson/judges", "https://freebibleimages.org/illustrations/samson/"),
    ("דבורה", "debora/judge", "https://freebibleimages.org/illustrations/debora/"),

    # ── Monarchy ──
    ("שמואל", "samuel/prophet", "https://freebibleimages.org/illustrations/samuel/"),
    ("שאול", "saul/king", "https://freebibleimages.org/illustrations/saul/"),
    ("דוד", "david/king", "https://freebibleimages.org/illustrations/david/"),
    ("גלית", "goliath/philistine", "https://freebibleimages.org/illustrations/david-goliath/"),
    ("שלמה", "solomon/king", "https://freebibleimages.org/illustrations/solomon/"),
    ("מלך", "king/monarchy", "https://freebibleimages.org/illustrations/solomon/"),
    ("כסא", "throne/king", "https://freebibleimages.org/illustrations/solomon/"),
    ("חרב", "sword/war", "https://freebibleimages.org/illustrations/david/"),
    ("חנית", "spear/warrior", "https://freebibleimages.org/illustrations/david/"),
    ("מגן", "shield/war", "https://freebibleimages.org/illustrations/david/"),

    # ── Prophets ──
    ("אליהו", "elijah/prophet", "https://freebibleimages.org/illustrations/elijah/"),
    ("אלישע", "elisha/prophet", "https://freebibleimages.org/illustrations/elisha/"),
    ("ישעיה", "isaiah/prophet", "https://freebibleimages.org/illustrations/isaiah/"),
    ("ירמיה", "jeremiah/prophet", "https://freebibleimages.org/illustrations/jeremiah/"),
    ("יחזקאל", "ezekiel/prophet", "https://freebibleimages.org/illustrations/ezekiel/"),
    ("דניאל", "daniel/prophet", "https://freebibleimages.org/illustrations/daniel/"),
    ("אריה", "lion/daniel", "https://freebibleimages.org/illustrations/daniel/"),
    ("נבואה", "prophecy/vision", "https://freebibleimages.org/illustrations/prophets/"),

    # ── Temple & Worship ──
    ("כוהן", "priest/temple", "https://freebibleimages.org/illustrations/priest/"),
    ("קרבן", "sacrifice/altar", "https://freebibleimages.org/illustrations/sacrifice/"),
    ("מנורה", "lampstand/temple", "https://freebibleimages.org/illustrations/tabernacle/"),
    ("ארון", "ark/covenant", "https://freebibleimages.org/illustrations/ark-covenant/"),
    ("ברית", "covenant/ark", "https://freebibleimages.org/illustrations/ark-covenant/"),
    ("שופר", "ram-horn/sound", "https://freebibleimages.org/illustrations/jericho/"),

    # ── Animals ──
    ("שה", "lamb/sheep", "https://freebibleimages.org/illustrations/shepherd/"),
    ("צאן", "sheep/flock", "https://freebibleimages.org/illustrations/shepherd/"),
    ("רועה", "shepherd/flock", "https://freebibleimages.org/illustrations/shepherd/"),
    ("בקר", "cattle/ox", "https://freebibleimages.org/illustrations/farming/"),
    ("חמור", "donkey/riding", "https://freebibleimages.org/illustrations/jesus-triumphal/"),
    ("גמל", "camel/desert", "https://freebibleimages.org/illustrations/abraham/"),
    ("יונה", "dove/peace", "https://freebibleimages.org/illustrations/noah/"),
    ("נחש", "serpent/temptation", "https://freebibleimages.org/illustrations/adam-eve/"),
    ("דג", "fish/sea", "https://freebibleimages.org/illustrations/jonah/"),
    ("צפור", "bird/fowl", "https://freebibleimages.org/illustrations/creation/"),

    # ── Nature ──
    ("גשם", "rain/weather", "https://freebibleimages.org/illustrations/noah/"),
    ("רוח", "wind/spirit", "https://freebibleimages.org/illustrations/creation/"),
    ("אבן", "stone/rock", "https://freebibleimages.org/illustrations/moses/"),
    ("סלע", "rock/cliff", "https://freebibleimages.org/illustrations/moses/"),
    ("עפר", "dust/ground", "https://freebibleimages.org/illustrations/creation/"),
    ("זהב", "gold/treasure", "https://freebibleimages.org/illustrations/tabernacle/"),
    ("כסף", "silver/money", "https://freebibleimages.org/illustrations/tabernacle/"),
    ("נחושת", "bronze/metal", "https://freebibleimages.org/illustrations/tabernacle/"),
    ("ברזל", "iron/metal", "https://freebibleimages.org/illustrations/war/"),

    # ── People & Daily Life ──
    ("אב", "father/family", "https://freebibleimages.org/illustrations/family/"),
    ("אם", "mother/family", "https://freebibleimages.org/illustrations/family/"),
    ("בן", "son/child", "https://freebibleimages.org/illustrations/family/"),
    ("בת", "daughter/child", "https://freebibleimages.org/illustrations/family/"),
    ("איש", "man/person", "https://freebibleimages.org/illustrations/people/"),
    ("עבד", "servant/slave", "https://freebibleimages.org/illustrations/exodus/"),
    ("מלך", "king/ruler", "https://freebibleimages.org/illustrations/solomon/"),
    ("שופט", "judge/justice", "https://freebibleimages.org/illustrations/debora/"),
    ("נביא", "prophet/seer", "https://freebibleimages.org/illustrations/prophets/"),
    ("חכם", "wise/sage", "https://freebibleimages.org/illustrations/solomon/"),
    ("רופא", "healer/doctor", "https://freebibleimages.org/illustrations/jesus-healing/"),

    # ── Home & Daily Life ──
    ("בית", "house/home", "https://freebibleimages.org/illustrations/house/"),
    ("דלת", "door/gate", "https://freebibleimages.org/illustrations/passover/"),
    ("שער", "gate/city", "https://freebibleimages.org/illustrations/jericho/"),
    ("חלון", "window/home", "https://freebibleimages.org/illustrations/house/"),
    ("מיטה", "bed/rest", "https://freebibleimages.org/illustrations/david/"),
    ("שלחן", "table/meal", "https://freebibleimages.org/illustrations/last-supper/"),
    ("כסא", "chair/throne", "https://freebibleimages.org/illustrations/solomon/"),
    ("נר", "lamp/light", "https://freebibleimages.org/illustrations/tabernacle/"),

    # ── Food ──
    ("לחם", "bread/food", "https://freebibleimages.org/illustrations/manna/"),
    ("יין", "wine/drink", "https://freebibleimages.org/illustrations/last-supper/"),
    ("מים", "water/drink", "https://freebibleimages.org/illustrations/moses-water/"),
    ("בשר", "meat/food", "https://freebibleimages.org/illustrations/manna/"),
    ("דבש", "honey/sweet", "https://freebibleimages.org/illustrations/promised-land/"),
    ("שמן", "oil/anoint", "https://freebibleimages.org/illustrations/samuel-anoints-david/"),
    ("פרי", "fruit/tree", "https://freebibleimages.org/illustrations/eden/"),
    ("זרע", "seed/plant", "https://freebibleimages.org/illustrations/parable-sower/"),

    # ── Places ──
    ("ירושלים", "jerusalem/city", "https://freebibleimages.org/illustrations/jerusalem/"),
    ("ציון", "zion/jerusalem", "https://freebibleimages.org/illustrations/jerusalem/"),
    ("ישראל", "israel/people", "https://freebibleimages.org/illustrations/israel/"),
    ("יהודה", "judah/tribe", "https://freebibleimages.org/illustrations/david/"),
    ("בבל", "babylon/empire", "https://freebibleimages.org/illustrations/babylon/"),
    ("אשור", "assyria/empire", "https://freebibleimages.org/illustrations/jonah/"),
]

# Abstract concepts — use conceptual imagery from Bible themes
ABSTRACT_MAP = [
    ("חסד", "hesed/loving-kindness", "https://freebibleimages.org/illustrations/covenant/"),
    ("אמת", "truth/faithfulness", "https://freebibleimages.org/illustrations/ten-commandments/"),
    ("צדק", "righteousness/justice", "https://freebibleimages.org/illustrations/solomon-judgment/"),
    ("משפט", "judgment/justice", "https://freebibleimages.org/illustrations/solomon-judgment/"),
    ("שלום", "peace/wholeness", "https://freebibleimages.org/illustrations/peace/"),
    ("אהבה", "love/covenant", "https://freebibleimages.org/illustrations/creation/"),
    ("תקוה", "hope/future", "https://freebibleimages.org/illustrations/abraham/"),
    ("אמונה", "faith/trust", "https://freebibleimages.org/illustrations/abraham/"),
    ("שמחה", "joy/celebration", "https://freebibleimages.org/illustrations/return-prodigal/"),
    ("ברכה", "blessing/covenant", "https://freebibleimages.org/illustrations/abraham-blessing/"),
    ("קדוש", "holy/set-apart", "https://freebibleimages.org/illustrations/sinai/"),
    ("כבוד", "glory/presence", "https://freebibleimages.org/illustrations/sinai/"),
    ("חכמה", "wisdom/knowledge", "https://freebibleimages.org/illustrations/solomon-wisdom/"),
    ("דעת", "knowledge/understand", "https://freebibleimages.org/illustrations/solomon-wisdom/"),
    ("תורה", "torah/law", "https://freebibleimages.org/illustrations/ten-commandments/"),
    ("מצוה", "commandment/law", "https://freebibleimages.org/illustrations/ten-commandments/"),
    ("חטא", "sin/transgression", "https://freebibleimages.org/illustrations/adam-eve/"),
    ("סליחה", "forgiveness/pardon", "https://freebibleimages.org/illustrations/return-prodigal/"),
    ("גאולה", "redemption/deliverance", "https://freebibleimages.org/illustrations/exodus/"),
    ("ישועה", "salvation/deliverance", "https://freebibleimages.org/illustrations/red-sea/"),
    ("נס", "miracle/wonder", "https://freebibleimages.org/illustrations/red-sea/"),
    ("תפילה", "prayer/supplication", "https://freebibleimages.org/illustrations/samuel-prayer/"),
    ("הלל", "praise/worship", "https://freebibleimages.org/illustrations/return-prodigal/"),
    ("זבח", "sacrifice/offering", "https://freebibleimages.org/illustrations/tabernacle/"),
    ("נדר", "vow/pledge", "https://freebibleimages.org/illustrations/jephthah/"),
    ("שבועה", "oath/covenant", "https://freebibleimages.org/illustrations/covenant/"),
    ("אסיר", "captive/prisoner", "https://freebibleimages.org/illustrations/joseph/"),
    ("גר", "foreigner/stranger", "https://freebibleimages.org/illustrations/ruth/"),
    ("יתום", "orphan/fatherless", "https://freebibleimages.org/illustrations/ruth/"),
    ("אלמנה", "widow/woman", "https://freebibleimages.org/illustrations/ruth/"),
]


# ── Node ID mapping (from memorize.db) ──
# Maps Hebrew word → learning node_id for the word_images.node_id FK
def build_node_map(mem_conn):
    """Build a mapping from Hebrew word → node_id using hebrew_lessons content_json."""
    node_map = {}
    try:
        rows = mem_conn.execute(
            "SELECT node_id, content_json FROM hebrew_lessons WHERE node_id LIKE 'vocab_%'"
        ).fetchall()
        for node_id, content_json in rows:
            try:
                content = json.loads(content_json)
                hebrew = content.get("hebrew", "")
                if hebrew:
                    for h in hebrew.split("/"):
                        h = h.strip()
                        if h:
                            node_map[h] = node_id
            except (json.JSONDecodeError, AttributeError):
                pass
    except Exception:
        pass
    return node_map


def seed_images(scripture_db, mem_db, dry_run=True):
    """Seed word_images table from FreeBibleImages.org theme mappings."""
    conn = sqlite3.connect(str(scripture_db))
    conn.row_factory = sqlite3.Row

    # Build node mapping from memorize.db
    try:
        mem_conn = sqlite3.connect(str(mem_db))
        node_map = build_node_map(mem_conn)
        mem_conn.close()
    except Exception:
        node_map = {}
        print("  Note: memorize.db not available, no node_id mapping")

    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS word_images (
            word_hebrew TEXT NOT NULL,
            node_id TEXT,
            source TEXT DEFAULT 'freebible',
            image_url TEXT NOT NULL,
            attribution TEXT DEFAULT '',
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            prompt TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (word_hebrew, source)
        )
    """)
    conn.commit()

    # Seed concrete nouns
    concrete_added = 0
    for hebrew, theme, url in IMAGE_MAP:
        node_id = node_map.get(hebrew, "")
        if dry_run:
            concrete_added += 1
        else:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO word_images
                       (word_hebrew, node_id, source, image_url, attribution, prompt)
                       VALUES (?, ?, 'freebible', ?, 'FreeBibleImages.org (CC BY-NC-ND 4.0)', ?)""",
                    (hebrew, node_id, url, theme)
                )
                if conn.total_changes > 0:
                    concrete_added += 1
            except Exception:
                pass

    # Seed abstract concepts
    abstract_added = 0
    for hebrew, theme, url in ABSTRACT_MAP:
        node_id = node_map.get(hebrew, "")
        if dry_run:
            abstract_added += 1
        else:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO word_images
                       (word_hebrew, node_id, source, image_url, attribution, prompt)
                       VALUES (?, ?, 'freebible', ?, 'FreeBibleImages.org (CC BY-NC-ND 4.0)', ?)""",
                    (hebrew, node_id, url, theme)
                )
                if conn.total_changes > 0:
                    abstract_added += 1
            except Exception:
                pass

    conn.commit()

    # Show stats
    total = conn.execute("SELECT COUNT(*) as c FROM word_images").fetchone()["c"]
    by_source = conn.execute(
        "SELECT source, COUNT(*) as c FROM word_images GROUP BY source ORDER BY c DESC"
    ).fetchall()

    print(f"\n✓ Word images seeded!")
    print(f"  New concrete: {concrete_added}")
    print(f"  New abstract: {abstract_added}")
    print(f"  Total in DB:  {total}")
    print("  By source:")
    for s, c in by_source:
        print(f"    {s}: {c}")
    print(f"\n  {'[DRY RUN — use --apply to persist]' if dry_run else '[Changes applied]'}")

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed word images from FreeBibleImages.org")
    parser.add_argument("--apply", action="store_true", help="Actually insert into DB")
    parser.add_argument("--scripture-db", default=str(SCRIPTURE_DB))
    parser.add_argument("--mem-db", default=str(MEM_DB))
    args = parser.parse_args()

    print("=== Word Image Seeder ===")
    print(f"  Source: FreeBibleImages.org")
    print(f"  Scripture DB: {args.scripture_db}")
    print(f"  Memorize DB: {args.mem_db}")
    print(f"  Mode: {'APPLY' if args.apply else 'DRY RUN'}")

    seed_images(args.scripture_db, args.mem_db, dry_run=not args.apply)
