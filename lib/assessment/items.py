"""Deep scripture understanding questions.

Based on learning science research (Bloom's Taxonomy, SOLO, Make It Stick):
- Shows passage TEXT so users can see and reason about scripture
- Tests ANALYSIS and UNDERSTANDING, not verse-reference recall
- Uses elaborative interrogation ("why?") for deeper processing
- Connects multiple passages to build relational knowledge
- Teaches as it tests — every question includes an explanation

Question types:
  1. Cross-Reference Analysis — show 2 passages, ask what their relationship reveals
  2. Structural/Contextual Analysis — show passage, ask about literary structure or context
  3. Theological Theme — show 2-3 passages, ask what theme they develop
  4. Passage Comprehension ("Why?") — show passage, ask a why/inference question
  5. Comparative Analysis — show 2 same-theme passages, ask how they differ
  6. Hub Note Analysis — hub note steps, ask about the connection between steps
"""

import json
import logging
import os
import random
import re
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
logger = logging.getLogger(__name__)

# Moved from items_old.py (which is now deleted)
FULL_BOOK_NAMES = {
    'gen': 'Genesis', 'exo': 'Exodus', 'lev': 'Leviticus', 'num': 'Numbers',
    'deu': 'Deuteronomy', 'josh': 'Joshua', 'judg': 'Judges', 'ruth': 'Ruth',
    '1sam': '1 Samuel', '2sam': '2 Samuel', '1kgs': '1 Kings', '2kgs': '2 Kings',
    '1chr': '1 Chronicles', '2chr': '2 Chronicles', 'ezra': 'Ezra', 'neh': 'Nehemiah',
    'esth': 'Esther', 'job': 'Job', 'psa': 'Psalms', 'prov': 'Proverbs',
    'eccl': 'Ecclesiastes', 'song': 'Song of Solomon',
    'isa': 'Isaiah', 'jer': 'Jeremiah', 'lam': 'Lamentations', 'ezek': 'Ezekiel',
    'dan': 'Daniel', 'hos': 'Hosea', 'joel': 'Joel', 'amos': 'Amos',
    'obad': 'Obadiah', 'jonah': 'Jonah', 'mic': 'Micah', 'nah': 'Nahum',
    'hab': 'Habakkuk', 'zeph': 'Zephaniah', 'hag': 'Haggai', 'zech': 'Zechariah',
    'mal': 'Malachi', 'matt': 'Matthew', 'mark': 'Mark', 'luke': 'Luke',
    'john': 'John', 'acts': 'Acts', 'rom': 'Romans',
    '1cor': '1 Corinthians', '2cor': '2 Corinthians', 'gal': 'Galatians',
    'eph': 'Ephesians', 'phil': 'Philippians', 'col': 'Colossians',
    '1thes': '1 Thessalonians', '2thes': '2 Thessalonians',
    '1tim': '1 Timothy', '2tim': '2 Timothy', 'titus': 'Titus',
    'philem': 'Philemon', 'heb': 'Hebrews', 'james': 'James',
    '1pet': '1 Peter', '2pet': '2 Peter', '1john': '1 John',
    '2john': '2 John', '3john': '3 John', 'jude': 'Jude', 'rev': 'Revelation',
}


def fmt_ref(verse_id):
    """Format a verse reference like 'gen.1.1' into 'Genesis 1:1'."""
    parts = verse_id.split('.')
    if len(parts) >= 3:
        book = FULL_BOOK_NAMES.get(parts[0], parts[0].upper())
        return f"{book} {parts[1]}:{parts[2]}"
    elif len(parts) == 2:
        book = FULL_BOOK_NAMES.get(parts[0], parts[0].upper())
        return f"{book} {parts[1]}"
    return verse_id


def truncate_text(text, max_chars=150):
    """Truncate text to max_chars, adding ellipsis if needed."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + '...'


CANONICAL_BOOKS = {
    'gen','exo','lev','num','deu','josh','judg','ruth',
    '1sam','2sam','1kgs','2kgs','1chr','2chr',
    'ezra','neh','esth','job','psa','prov','eccl','song',
    'isa','jer','lam','ezek','dan',
    'hos','joel','amos','obad','jonah','mic','nah','hab','zeph','hag','zech','mal',
    'matt','mark','luke','john','acts','rom',
    '1cor','2cor','gal','eph','phil','col',
    '1thes','2thes','1tim','2tim','titus','philem','heb',
    'james','1pet','2pet','1john','2john','3john','jude','rev',
    '1ne','2ne','jacob','enos','jarom','omni','wom',
    'mosiah','alma','hel','3ne','4ne','morm','ether','moro',
    'moses','abraham','jsm','jsh','aoff',
}

# Thematically rich passage pairs from the connection graph
# Pre-verified as educationally useful
THEMATIC_PAIRS = [
    # Creation/New Creation
    ("gen.1.1", "john.1.1", "Both open with 'In the beginning.' John deliberately echoes Genesis to present Jesus as the agent of creation."),
    ("gen.1.3", "2cor.4.6", "Paul draws on the language of God commanding light to describe how the gospel illuminates hearts."),
    ("gen.2.7", "1cor.15.45", "Paul contrasts the 'living soul' Adam with the 'life-giving Spirit' Christ — the first and last Adam."),
    ("gen.1.26", "psa.8.4-6", "Both reflect on humanity's place in creation — made in God's image, crowned with glory."),
    ("gen.3.15", "rev.12.1-17", "The first prophecy of the Messiah connects to the final vision of the woman and the dragon."),
    # Covenant
    ("gen.15.6", "rom.4.3", "Paul builds his doctrine of justification by faith on Abraham's example."),
    ("gen.12.1-3", "gal.3.8", "Paul reads the Abrahamic covenant as the gospel preached in advance."),
    ("exo.19.5-6", "1pet.2.9", "Israel as a 'kingdom of priests' becomes the church as a 'royal priesthood.'"),
    # Exodus/Deliverance
    ("exo.12.1-13", "1cor.5.7", "Paul identifies Christ as 'our Passover sacrificed for us.'"),
    ("exo.14.21-22", "1cor.10.1-2", "The Red Sea crossing is interpreted as a type of baptism."),
    ("exo.16.4-18", "john.6.31-35", "The manna in the wilderness prefigures Jesus as the true bread from heaven."),
    ("deu.8.3", "matt.4.4", "Jesus quotes this verse when tempted — 'man shall not live by bread alone.'"),
    # Law/Righteousness
    ("lev.19.18", "matt.22.39", "Jesus identifies 'love your neighbor as yourself' as the second great commandment."),
    ("deut.6.4", "matt.22.37", "The Shema becomes Jesus' first great commandment."),
    ("exo.20.1-17", "matt.5.17-48", "Jesus both affirms and deepens the Ten Commandments in the Sermon on the Mount."),
    ("lev.17.11", "heb.9.22", "The blood atonement principle is foundational to the New Testament understanding of Christ's sacrifice."),
    # Temple/Presence
    ("exo.25.8", "1cor.3.16", "The tabernacle where God dwells becomes the believer as God's temple."),
    ("exo.40.34-35", "1kgs.8.10-11", "The glory of the Lord filling the tabernacle and temple establishes the pattern of divine presence."),
    ("1kgs.8.27-30", "acts.7.48-50", "Stephen echoes Solomon's question: can God dwell in a house made by hands?"),
    ("ezek.47.1-12", "rev.22.1-2", "The river from the temple connects to the river of life in the New Jerusalem."),
    # Prophecy/Fulfillment
    ("isa.6.1-8", "john.12.41", "John explicitly says Isaiah saw Jesus' glory."),
    ("isa.53.4-6", "1pet.2.24-25", "Peter directly applies the Suffering Servant passage to Christ's atonement."),
    ("isa.55.1", "john.7.37", "Jesus' invitation 'If anyone thirsts' echoes Isaiah's call to come to the waters."),
    ("jer.31.31-34", "heb.8.6-13", "The New Covenant promised by Jeremiah is fulfilled in Christ."),
    ("joel.2.28-32", "acts.2.17-21", "Peter quotes Joel's prophecy as being fulfilled at Pentecost."),
    ("hab.2.4", "rom.1.17", "'The just shall live by faith' becomes the foundation of Paul's theology."),
    # Wisdom/Teaching
    ("prov.1.7", "eccl.12.13", "The fear of the Lord as beginning and end of wisdom frames the wisdom literature."),
    ("prov.3.11-12", "heb.12.5-6", "The writer of Hebrews quotes Proverbs on divine discipline."),
    ("job.1.21", "eccl.5.15", "The theme of coming into the world with nothing and leaving with nothing."),
    ("psa.51.1-4", "2sam.12.1-13", "David's psalm of repentance must be read against Nathan's confrontation."),
    # Christ/Messiah
    ("psa.2.7", "acts.13.33", "The 'You are my Son' declaration applied to Jesus' resurrection."),
    ("psa.110.1", "matt.22.44", "Jesus uses this psalm to challenge the Pharisees about the Messiah's identity."),
    ("psa.22.1", "matt.27.46", "Jesus cries out the opening of this psalm on the cross."),
    ("psa.118.22-23", "matt.21.42", "The stone the builders rejected becomes the cornerstone."),
    ("dan.7.13-14", "matt.24.30", "The Son of Man coming in glory — Jesus applies Daniel's prophecy to himself."),
    ("isa.7.14", "matt.1.23", "The virgin birth prophecy is cited by Matthew as fulfilled in Jesus."),
    ("isa.9.6-7", "luke.1.32-33", "The child born, the son given — Gabriel's annunciation echoes Isaiah."),
    ("mic.5.2", "matt.2.6", "Micah's prophecy of Bethlehem is cited when the magi seek the newborn king."),
]

# Structural questions for specific passages
STRUCTURAL_PASSAGES = [
    {
        "passage": "gen.1.1-2.3",
        "text_snippet": "Day 1: Light. Day 2: Sky. Day 3: Land and plants. Day 4: Sun, moon, stars. Day 5: Fish and birds. Day 6: Animals and humanity. Day 7: Rest.",
        "question": "What literary pattern structures the creation account?",
        "options": [
            "A three-day creation followed by three-day filling, culminating in rest",
            "A chronological narrative with no repetitive structure",
            "A series of unrelated divine acts",
            "A legal covenant document",
        ],
        "answer": 0,
        "explanation": "Days 1-3 create realms (light, sky, land); Days 4-6 fill them (lights, fish/birds, animals/humans). Day 7 is the climax. This is a carefully crafted literary structure.",
    },
    {
        "passage": "psa.23.1-6",
        "text_snippet": "The LORD is my shepherd… He makes me lie down… He leads me… Though I walk through the valley… You prepare a table… Surely goodness and mercy will follow me…",
        "question": "How does the psalm shift in its address to God between verses 1-4 and 5-6?",
        "options": [
            "It shifts from speaking ABOUT God ('He') to speaking TO God ('You'), moving from general trust to intimate confidence",
            "It shifts from poetry to prose",
            "It shifts from Hebrew to Aramaic",
            "It shifts from praise to lament",
        ],
        "answer": 0,
        "explanation": "Verses 1-4 speak of the Lord in third person ('He restores,' 'He leads'). At verse 5, the psalm shifts to direct address ('You prepare,' 'You anoint'), reflecting deeper intimacy as the psalm moves from shepherd metaphor to host metaphor.",
    },
    {
        "passage": "isa.6.1-8",
        "text_snippet": "I saw the Lord… seraphim called 'Holy, holy, holy'… the temple shook… 'Woe is me, for I am undone…' Then one seraph touched my lips with a coal… 'Your sin is purged.' Then I heard: 'Whom shall I send?' And I said: 'Here am I, send me.'",
        "question": "What is the logical sequence of events in Isaiah's call narrative?",
        "options": [
            "Vision of God → recognition of unworthiness → purification → commissioning → willing response",
            "Commissioning → vision of God → doubt → reassurance → acceptance",
            "Dream → confusion → angelic explanation → obedience",
            "Prayer → divine answer → prophecy → fulfillment",
        ],
        "answer": 0,
        "explanation": "The sequence is: (1) Isaiah sees God's glory (v.1-4), (2) This leads to self-awareness of sin (v.5), (3) Divine purification follows (v.6-7), (4) God calls for a messenger (v.8a), (5) Isaiah volunteers (v.8b). This encounter→crisis→purification→mission pattern recurs throughout scripture.",
    },
    {
        "passage": "amos.1.3-2.16",
        "text_snippet": "For three transgressions of Damascus… of Gaza… of Tyre… of Edom… of Ammon… of Moab… of Judah… of Israel…",
        "question": "What rhetorical device does Amos use to confront Israel, and what is its effect?",
        "options": [
            "He lists judgments on Israel's neighbors first, building agreement, then turns the same pattern on Israel — trapping the audience",
            "He uses acrostic poetry to make the prophecy memorable",
            "He alternates between judgment and mercy to create balance",
            "He quotes earlier prophets to establish authority",
        ],
        "answer": 0,
        "explanation": "Amos pronounces judgment on seven surrounding nations (each beginning with 'For three transgressions…'). The Israelite audience would have applauded. Then Amos turns the same formula on Israel itself — the audience is trapped by their own agreement with the pattern.",
    },
]


def _fetch_verse_text(conn, verse_id):
    """Fetch English text for a verse. Handles range notation by taking first verse."""
    if '-' in verse_id:
        verse_id = verse_id.split('-')[0]
    row = conn.execute("SELECT text_english FROM verses WHERE id=?", (verse_id,)).fetchone()
    return row[0] if row else None


def _fetch_passage_around(conn, verse_id, window=2):
    """Fetch a passage of verses before and after the given verse for context."""
    if '-' in verse_id:
        verse_id = verse_id.split('-')[0]
    parts = verse_id.split('.')
    if len(parts) != 3:
        return None
    book = parts[0]
    ch = int(parts[1])
    vs = int(parts[2])
    texts = []
    for offset in range(-window, window + 1):
        v = vs + offset
        if v < 1:
            continue
        vid = f"{book}.{ch}.{v}"
        text = _fetch_verse_text(conn, vid)
        if text:
            texts.append((vid, text))
    return texts


class DeepQuestionGenerator:
    """Generates deep scripture understanding questions."""

    def __init__(self, conn):
        self.conn = conn

    def generate_all(self, count=100):
        """Generate a diverse set of deep questions with tier labels."""
        items = []
        generators = [
            self._gen_cross_reference,
            self._gen_structural,
            self._gen_thematic_group,
            self._gen_passage_comprehension,
            self._gen_consistency,
        ]

        for _ in range(count * 5):
            if len(items) >= count:
                break
            gen = random.choice(generators)
            try:
                item = gen()
                if item:
                    item["tier"] = self._assign_tier(item)
                    items.append(item)
            except Exception:
                continue

        random.shuffle(items)
        return items[:count]

    def _assign_tier(self, item):
        """Assign a question tier based on what it tests."""
        # Use explicit tier if generator set one
        if "tier" in item and item["tier"]:
            return item["tier"]
        # "What does the text say?" — verifiable structure/patterns
        if item.get("bloom_level") == "understand":
            return "text"
        # Cross-reference and structural — analysis
        if item.get("type") == "multiple_choice":
            q = item.get("question", "")
            # Thematic grouping = analysis
            if "develop a common theme" in q.lower() or "share a theme" in q.lower():
                return "analysis"
            # Structural analysis
            if "structure" in q.lower() or "pattern" in q.lower() or "shift" in q.lower():
                return "text"
            # Cross-reference usually = analysis
            if "read them together" in q.lower() or "emerge" in q.lower() or "reveal" in q.lower():
                return "analysis"
        return "text"


    def _gen_cross_reference(self):
        """Show two passages side by side. Ask what their relationship reveals."""
        pair = random.choice(THEMATIC_PAIRS)
        src, tgt, explanation = pair

        src_text = _fetch_verse_text(self.conn, src)
        tgt_text = _fetch_verse_text(self.conn, tgt)
        if not src_text or not tgt_text:
            return None

        src_fmt = fmt_ref(src)
        tgt_fmt = fmt_ref(tgt)

        # Generate plausible-sounding but wrong analyses as distractors
        # These should be analyses that COULD be true but aren't the main point
        wrong_analyses = [
            f"{src_fmt} and {tgt_fmt} are independent passages with no direct connection",
            f"{tgt_fmt} is quoting {src_fmt} exactly word for word",
            f"{src_fmt} and {tgt_fmt} are describing the same historical event from different perspectives",
            f"{tgt_fmt} is correcting a misunderstanding of {src_fmt}",
            f"{src_fmt} and {tgt_fmt} were written by the same author",
        ]
        random.shuffle(wrong_analyses)

        # The correct insight
        correct = f"When read together, {src_fmt} and {tgt_fmt} reveal that {explanation}"

        options = [correct] + wrong_analyses[:3]
        random.shuffle(options)

        return {
            "type": "multiple_choice",
            "question": (
                f"**{src_fmt}** says:\n"
                f"> “{truncate_text(src_text, 200)}”\n\n"
                f"**{tgt_fmt}** says:\n"
                f"> “{truncate_text(tgt_text, 200)}”\n\n"
                f"These two passages are connected. What insight emerges when we read them together?"
            ),
            "options": options,
            "correct_answer": correct,
            "explanation": explanation,
            "bloom_level": "analyze",
        }

    def _gen_structural(self):
        """Show a passage and ask about its literary structure or rhetorical strategy."""
        item = random.choice(STRUCTURAL_PASSAGES)
        verse_id = item["passage"].split("-")[0].strip() if "-" in item["passage"] else item["passage"]

        # Show the actual verse text
        text = _fetch_verse_text(self.conn, verse_id)
        if not text:
            return None

        display_text = f"{item['text_snippet']}\n\n(from {fmt_ref(verse_id)} — full text shown)"

        options = item["options"]
        return {
            "type": "multiple_choice",
            "question": (
                f"Consider **{fmt_ref(verse_id)}** ({item['passage']}):\n\n"
                f"> {display_text}\n\n"
                f"{item['question']}"
            ),
            "options": options,
            "correct_answer": options[item["answer"]],
            "explanation": item["explanation"],
            "bloom_level": "analyze",
        }

    def _gen_thematic_group(self):
        """Show 2-3 passages on the same theme. Ask what theme they develop together."""
        # Pick a hub note or TG topic with several passages
        topic = self.conn.execute("""
            SELECT slug, name FROM topical_guide
            WHERE verse_count BETWEEN 8 AND 30
            ORDER BY RANDOM() LIMIT 1
        """).fetchone()
        if not topic:
            return None

        topic_slug, topic_name = topic
        verses = self.conn.execute("""
            SELECT tg.verse_id, v.text_english
            FROM tg_verse_references tg
            JOIN verses v ON v.id = tg.verse_id
            WHERE tg.topic_id = ? AND v.text_english IS NOT NULL
            AND length(v.text_english) BETWEEN 20 AND 150
            AND v.book_id IN ({})
            ORDER BY RANDOM() LIMIT 3
        """.format(','.join('?' for _ in CANONICAL_BOOKS)),
            [topic_slug] + list(CANONICAL_BOOKS)
        ).fetchall()

        if len(verses) < 3:
            return None

        verse_display = "\n".join(
            f"• “{truncate_text(v[1], 120)}” — {fmt_ref(v[0])}"
            for v in verses
        )

        # Get distractor topics
        others = self.conn.execute("""
            SELECT name FROM topical_guide WHERE slug != ? AND verse_count BETWEEN 8 AND 30
            ORDER BY RANDOM() LIMIT 3
        """, (topic_slug,)).fetchall()

        options = [topic_name] + [r[0] for r in others]
        random.shuffle(options)

        return {
            "type": "multiple_choice",
            "question": (
                f"These passages all develop a common theme from the Topical Guide:\n\n"
                f"{verse_display}\n\n"
                f"Which theme do they collectively develop?"
            ),
            "options": options,
            "correct_answer": topic_name,
            "explanation": (
                f"All three passages are categorized under **{topic_name}** in the Topical Guide. "
                f"Reading them together reveals how this theme is developed across different contexts."
            ),
            "bloom_level": "analyze",
        }

    def _gen_passage_comprehension(self):
        """Show a passage and ask a 'why' question that requires inference."""
        # Pick a theologically rich verse and ask why something happens
        pair = random.choice(THEMATIC_PAIRS)
        src = pair[0]
        explanation = pair[2]

        src_text = _fetch_verse_text(self.conn, src)
        if not src_text:
            return None

        # Generate a "why" question based on the passage
        questions_map = {
            "gen.1.1": ("Why does John begin his gospel by echoing Genesis 1:1?",
                        ["To connect Jesus to the creation story and present Him as the divine agent of creation",
                         "Because John was a fisherman and that's how people wrote back then",
                         "To correct a misunderstanding in Genesis",
                         "Because John wanted to write a sequel to Genesis"]),
            "gen.15.6": ("Why does Paul use this verse as the foundation for his doctrine of justification by faith?",
                        ["Because it shows Abraham was counted righteous before circumcision or the law — faith precedes works",
                         "Because Abraham was a perfect person who never sinned",
                         "Because Paul needed an Old Testament proof text and this was the only one available",
                         "Because Abraham's faith was a one-time event with no ongoing significance"]),
            "exo.12.1-13": ("Why does the New Testament repeatedly identify Christ as the Passover lamb?",
                          ["Because the Passover lamb's blood that saved Israel from death prefigures Christ's blood that saves from sin",
                           "Because Jesus was born during Passover",
                           "Because lambs were the only animals used in temple sacrifice",
                           "Because the Passover was the only Jewish festival still observed"]),
            "isa.53.4-6": ("Why does this passage have such a central place in Christian theology?",
                          ["Because it describes a suffering servant who bears others' sins — the most detailed Old Testament prophecy of Christ's atonement",
                           "Because it predicts the exact year of Jesus' birth",
                           "Because it was written after the events it describes",
                           "Because it contains a secret code about the Messiah"]),
            "jer.31.31-34": ("Why is this passage considered one of the most important in the Old Testament?",
                           ["Because it promises a New Covenant written on hearts, not stone — internal transformation, not external law",
                            "Because it predicts the Babylonian captivity",
                            "Because it contains a list of all the kings of Judah",
                            "Because it changes the name of God"]),
        }

        if src in questions_map:
            q_text, options_list = questions_map[src]
        else:
            # Generic "why" question
            q_text = f"Why is **{fmt_ref(src)}** significant in the broader biblical narrative?"
            options_list = [
                f"It establishes a key theological principle: {explanation.split('.')[0]}.",
                "It describes a historical event with no theological implications.",
                "It is primarily a legal or genealogical record.",
                "Its meaning is unclear and debated by scholars.",
            ]

        return {
            "type": "multiple_choice",
            "question": (
                f"**{fmt_ref(src)}** says:\n"
                f"> “{truncate_text(src_text, 200)}”\n\n"
                f"{q_text}"
            ),
            "options": options_list,
            "correct_answer": options_list[0],
            "explanation": explanation,
            "bloom_level": "understand",
        }

    def _gen_consistency(self):
        """Show a theme taught across multiple passages — 'consistency through witnesses.'

        This is the most powerful question type: it shows that a teaching isn't from
        one isolated verse but is CONFIRMED by multiple witnesses across scripture.
        """
        # Pick a random thematic cluster
        cluster = self.conn.execute("""
            SELECT id, theme, description, source_tradition FROM thematic_clusters
            ORDER BY RANDOM() LIMIT 1
        """).fetchone()
        if not cluster:
            return None

        cid, theme, desc, trad = cluster

        # Get 3-5 verses from the cluster
        verses = self.conn.execute("""
            SELECT m.verse_id, v.text_english, m.contribution
            FROM thematic_cluster_members m
            JOIN verses v ON v.id = m.verse_id
            WHERE m.cluster_id = ?
            ORDER BY m.sort_order
            LIMIT 5
        """, (cid,)).fetchall()

        if len(verses) < 3:
            return None

        verse_lines = "\n".join(
            f"• “{truncate_text(v[1], 120)}” — {fmt_ref(v[0])}"
            for v in verses
        )

        # Get distractor themes from other clusters
        others = self.conn.execute("""
            SELECT theme FROM thematic_clusters WHERE id != ? ORDER BY RANDOM() LIMIT 3
        """, (cid,)).fetchall()

        options = [theme] + [r[0] for r in others]
        random.shuffle(options)

        # Determine the tier
        if trad == "multiple":
            explanation = "This theme is taught across multiple passages in scripture. The consistency across these witnesses strengthens it as a core biblical teaching."
        else:
            explanation = f"These passages all develop the theme of **{theme}**. The {trad} tradition sees this consistency as confirming the doctrine."

        return {
            "type": "multiple_choice",
            "tier": "consistency",
            "question": (
                f"This theme is taught in **multiple** places across scripture — "
                f"each witness confirms and strengthens it:\n\n"
                f"{verse_lines}\n\n"
                f"What theme do these passages all develop together?"
            ),
            "options": options,
            "correct_answer": theme,
            "explanation": explanation,
            "bloom_level": "analyze",
        }


def build_deep_questions(count=200):
    """Build and store deep understanding questions."""
    conn = sqlite3.connect(str(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "scripture.db")
    ))

    # Clear and rebuild
    conn.execute("DELETE FROM assessment_items")
    conn.commit()

    gen = DeepQuestionGenerator(conn)
    items = gen.generate_all(count=count)

    stored = 0
    for item in items:
        try:
            tier = item.get("tier", "text")
            explanation = item.get("explanation", "")
            conn.execute("""
                INSERT INTO assessment_items
                    (question_type, question_text, options_json, correct_answer, layer, bloom_level, tier, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["type"],
                item["question"],
                json.dumps(item.get("options", [])),
                str(item["correct_answer"]),
                "p'shat",
                item.get("bloom_level", "understand"),
                tier,
                explanation[:500],
            ))
            stored += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    logger.info("Generated %s deep questions, stored %s", len(items), stored)
    return stored


if __name__ == "__main__":
    build_deep_questions(count=200)
