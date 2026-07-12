#!/usr/bin/env python3
"""Seed interpretive disagreements — contradictory readings across traditions.

Adds well-known interpretive disagreements that represent genuine
contradictory readings between major traditions (Jewish, Christian,
critical, LDS, etc.).

Usage:
    python3 scripts/seed_disagreements.py
    python3 scripts/seed_disagreements.py --dry-run   # preview only
"""

import sys, sqlite3, os, json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "processed" / "scripture.db"

DISAGREEMENTS = [
    # ── Isaiah 7:14 — Virgin vs Young Woman ──
    {
        "verse_id": "isa.7.14",
        "tradition_a": "Jewish",
        "tradition_b": "Christian",
        "description": "Christian tradition reads 'almah' as 'virgin' (parthenos in LXX), interpreting this as a prophecy of Jesus's virgin birth. Jewish tradition reads 'almah' as 'young woman' (not necessarily a virgin), referring to Isaiah's contemporary context — a young woman who would bear a child as a sign to King Ahaz.",
        "resolved_by": "The Hebrew word 'almah (עלמה) means 'young woman of marriageable age.' The LXX translates as parthenos (virgin). The context (Isa 7:1-17) is about Ahaz's immediate political crisis, but Matthew 1:23 applies it to Jesus typologically.",
    },
    {
        "verse_id": "isa.7.14",
        "tradition_a": "Christian",
        "tradition_b": "Critical",
        "description": "Christian tradition reads this as a direct prophecy of Jesus's virgin birth (cited in Matt 1:23). Critical scholars read it as referring to an 8th-century BCE young woman in Ahaz's court, with Matthew's use being a 're-reading' or midrashic reinterpretation rather than a predictive fulfillment.",
    },

    # ── Psalm 110:1 — Davidic vs Messianic ──
    {
        "verse_id": "psa.110.1",
        "tradition_a": "Jewish",
        "tradition_b": "Christian",
        "description": "Christian tradition reads 'The Lord said to my Lord' as God the Father speaking to Jesus/Yeshua (cited in Matt 22:44, Acts 2:34-35, Heb 1:13). Jewish tradition reads it as David speaking of a human king (traditionally Abraham, or a Davidic king exalted to God's right hand). The 'adonai' (my lord) is a human superior, not divine.",
        "resolved_by": "The Hebrew says 'ne'um YHWH la'doni' (oracle of YHWH to my lord). The question hinges on whether 'adoni' (my lord, human) or a divine 'adonai' is intended. Both readings agree it's messianic; they disagree on the nature of the Messiah.",
    },

    # ── Psalm 22:16 — Pierced vs Like a Lion ──
    {
        "verse_id": "psa.22.16",
        "tradition_a": "Christian",
        "tradition_b": "Jewish",
        "description": "Christian tradition reads 'they pierced my hands and my feet' (following LXX and some Hebrew manuscripts), seeing a prophecy of crucifixion. Jewish tradition reads 'like a lion (ka'ari) my hands and my feet' — the sufferer is surrounded by enemies who 'encircle' like a lion, not pierced.",
        "resolved_by": "The MT reads כארי (ka'ari = like a lion). The LXX reads ωρυξαν (oryxan = they pierced). The difference is one letter: כארו (karu = they dug/pierced) vs כארי (ka'ari = like a lion). The Dead Sea Scrolls (5/6HevPs) have כרה ('pierced/digged'). So the Hebrew textual evidence supports 'pierced.'",
    },

    # ── Genesis 1:1 — Creation ex nihilo vs ordering ──
    {
        "verse_id": "gen.1.1",
        "tradition_a": "Christian",
        "tradition_b": "Critical",
        "description": "Christian tradition (following later theology) reads 'In the beginning God created (bara) the heavens and the earth' as creation ex nihilo — God brought matter into existence from nothing. Critical scholars note that bara does not necessarily mean ex nihilo; the passage describes God ordering pre-existing chaos (tohu wa-bohu, deep, waters in v. 2). The word bara is used elsewhere for 'bringing order' or 'assigning roles.'",
        "resolved_by": "Genesis 1:1-3 describes God bringing order out of chaos (tohu wa-bohu). Whether this is ex nihilo or ordering of pre-existent matter depends on whether one reads v. 1 as a summary statement, a temporal clause ('when God began to create…'), or the first creative act. The Hebrew syntax of 'b'reishit bara' is ambiguous and supports both readings.",
    },

    # ── Exodus 3:14 — I AM vs I Will Be ──
    {
        "verse_id": "exo.3.14",
        "tradition_a": "Christian",
        "tradition_b": "Jewish",
        "description": "Christian tradition reads 'I AM THAT I AM' (ehyeh asher ehyeh) as a declaration of God's eternal self-existence, often linked to Jesus's 'I AM' statements in John. Jewish tradition reads 'I Will Be What I Will Be' or 'I Am Who I Am' — God's statement is about presence and faithful availability, not abstract metaphysical being. The Hebrew verb 'ehyeh' is an imperfect tense that primarily expresses future or incomplete action.",
        "resolved_by": "Ehyeh asher ehyeh is intentionally ambiguous: 'I am/will be what/who I am/will be.' It is a statement of God's freedom and presence, not a philosophical definition of being. The LXX translates as 'ego eimi ho on' (I am the being one), which influenced the Christian reading.",
    },

    # ── Isaiah 53 — Suffering Servant ──
    {
        "verse_id": "isa.53.5",
        "tradition_a": "Christian",
        "tradition_b": "Jewish",
        "description": "Christian tradition identifies the suffering servant of Isaiah 53 as Jesus Christ — 'he was wounded for our transgressions' is a direct prophecy of the crucifixion. Jewish tradition (following Rashi and others) identifies the servant as the nation of Israel itself, which suffers vicariously for the sins of the nations. The singular 'he' is understood as collective personification of Israel.",
        "resolved_by": "The servant in Isaiah 52:13-53:12 is identified as 'my servant' by YHWH. Both the collective (Israel) and individual (Messiah) readings have ancient support. The Targum Jonathan reads the servant as the Messiah. Rashi reads it as Israel. The New Testament applies it to Jesus (Matt 8:17, Acts 8:32-35, 1 Pet 2:24-25).",
    },

    # ── Daniel 9:24-27 — 70 Weeks ──
    {
        "verse_id": "dan.9.24",
        "tradition_a": "Christian",
        "tradition_b": "Jewish",
        "description": "Christian tradition interprets the 70 weeks (shavuim) as 490 years culminating in the crucifixion of Christ or the destruction of Jerusalem in 70 AD. Jewish tradition interprets them as the period from the decree to rebuild Jerusalem (Artaxerxes) to the destruction of the Second Temple. The starting point, duration of 'weeks,' and the identity of 'an anointed one' are all disputed.",
        "resolved_by": "The number of interpretations rivals the number of interpreters. The starting point (decree of Cyrus, Artaxerxes, or the 'going forth of the word') and whether 'weeks' are literal years or symbolic periods are the key variables.",
    },

    # ── John 1:1 — The Word was God ──
    {
        "verse_id": "john.1.1",
        "tradition_a": "Christian",
        "tradition_b": "Critical",
        "description": "Christian tradition reads 'the Word was God' (kai theos en ho logos) as affirming the full deity of Christ — the Word (Logos) is identified as God. Critical scholars and Jehovah's Witnesses note the absence of the definite article before theos (theos, not ho theos), reading 'the Word was divine' or 'the Word was a god.' The Colwell rule for predicate nominatives is invoked on both sides.",
        "resolved_by": "John 1:1c has an anarthrous predicate nominative (theos) before the verb (en). Colwell's rule normally requires the article when the predicate is definite and precedes the verb, but theos without article can mean 'divine' or 'a god' depending on context. The context of Jewish monotheism and the Prologue's structure supports the traditional reading of full divinity.",
    },

    # ── Genesis 22:2 — Only Son vs Beloved Son ──
    {
        "verse_id": "gen.22.2",
        "tradition_a": "Jewish",
        "tradition_b": "Christian",
        "description": "Christian tradition reads 'your only son Isaac' as a type of God the Father sacrificing His only Son Jesus. Jewish tradition notes that Abraham had two sons (Ishmael and Isaac), so 'only son' (yachid) means 'beloved/unique son' not 'only begotten.' The Akedah (binding of Isaac) is read as the ultimate test of faith, not a prefiguration.",
        "resolved_by": "Yachid (יחיד) means 'only one' or 'unique.' Abraham had Ishmael, so Isaac is not his only biological son. The word emphasizes Isaac's unique status as the son of promise. Both readings agree this is a profound test; they differ on typological connections to the New Testament.",
    },

    # ── Deuteronomy 21:23 — Cursed is Everyone Hanged on a Tree ──
    {
        "verse_id": "deu.21.23",
        "tradition_a": "Jewish",
        "tradition_b": "Christian",
        "description": "Christian tradition (via Paul in Gal 3:13) reads 'cursed is everyone who hangs on a tree' as Christ taking the curse of the law upon Himself through crucifixion. Jewish tradition reads this as a law about post-execution display of a criminal's body — the body must not remain overnight because it is a reproach to God, not a metaphysical curse on the person being hanged.",
        "resolved_by": "The Hebrew 'ki kilelat elohim taluy' means 'for a hanged person is a reproach/curse of God.' The passage is about proper treatment of executed criminals, not a prophecy. Paul's use in Galatians is typological — Christ identified with the cursed criminal to redeem from the curse of the law.",
    },

    # ── Genesis 6:1-4 — Sons of God ──
    {
        "verse_id": "gen.6.2",
        "tradition_a": "Jewish",
        "tradition_b": "Christian",
        "description": "Jewish tradition (Rashi) reads 'sons of God' (benei Elohim) as human judges/rulers or sons of nobility who took wives from common people. Christian tradition often reads it as fallen angels (sons of God = angelic beings) intermarrying with human women, producing the Nephilim. The Septuagint translates as 'angels of God,' supporting the angelic interpretation.",
        "resolved_by": "Benei Elohim appears elsewhere in the OT for angels (Job 1:6, 2:1, 38:7). The context of the Nephilim and divine judgment favors the angelic reading, but ancient Jewish sources (Targum, Rashi) favor the 'judges' interpretation due to theological discomfort with angels sinning. Both have early attestation.",
    },

    # ── Hosea 6:7 — Like Adam vs Like Men ──
    {
        "verse_id": "hos.6.7",
        "tradition_a": "Jewish",
        "tradition_b": "Christian",
        "description": "Christian tradition reads 'like Adam, they have transgressed the covenant' — Adam's individual transgression in Eden as a type of Israel's covenant-breaking. Jewish tradition reads 'like men/adam' (ke'adam) or 'like the men of' a specific place — a general statement about human covenant-breaking, not a reference to the Eden narrative.",
        "resolved_by": "The Hebrew ke'adam means either 'like Adam' (the person) or 'like men/humans.' The context of covenant-breaking and the parallel to Eden in Hos 6:7b ('there they dealt treacherously against me') supports the individual Adam reference, but the general 'like humans' reading is also grammatically valid.",
    },

    # ── Psalm 2:7-9 — Decree ──
    {
        "verse_id": "psa.2.7",
        "tradition_a": "Jewish",
        "tradition_b": "Christian",
        "description": "Christian tradition reads 'You are my Son, today I have begotten you' as a messianic prophecy of Jesus's divine sonship (cited in Acts 13:33, Heb 1:5, 5:5). Jewish tradition reads it as a coronation psalm for the Davidic king — the king is adopted as God's 'son' in a covenant sense at his enthronement, not a statement of ontological divinity.",
        "resolved_by": "The psalm describes a royal coronation ceremony. 'You are my son' is an adoption formula for the Davidic king (cf. 2 Sam 7:14). The New Testament applies it to Jesus as the ultimate Davidic king. Both recognize it as messianic; they differ on whether the sonship is adoptive or ontological.",
    },

    # ── Ezekiel 28:12-19 — King of Tyre vs Satan ──
    {
        "verse_id": "ezek.28.13",
        "tradition_a": "Christian",
        "tradition_b": "Critical",
        "description": "Christian tradition often reads Ezekiel's lamentation over the King of Tyre as a description of Satan's original state — 'in Eden, the garden of God,' 'the anointed cherub,' 'perfect in your ways from the day you were created till unrighteousness was found in you.' Critical scholars read this as a hyperbolic taunt against a human king of Tyre, using Eden imagery to mock his pride, not as a description of a pre-existent fallen angel.",
        "resolved_by": "The passage is addressed to a human king ('you are a man, and not God' in v. 2). The Eden imagery is hyperbolic comparison. The 'cherub' language may be the king's self-image or a poetic description of his position. Later Christian tradition read this as describing Satan based on the 'fall from perfection' narrative, but the original context is Tyre's king.",
    },

    # ── 1 Peter 3:19 — Spirits in Prison ──
    {
        "verse_id": "1pe.3.19",
        "tradition_a": "Christian",
        "tradition_b": "Christian",
        "description": "Among Christian traditions there is significant disagreement: Catholic tradition reads this as Christ descending to the dead (harrowing of hell) to preach to the righteous dead of the Old Testament. Protestant Reformed tradition reads it as Christ (through the Spirit) preaching to Noah's disobedient contemporaries through Noah's ministry. LDS tradition reads it as Christ visiting spirit prison to organize missionary work among the dead.",
        "resolved_by": "The key questions: Who are the 'spirits in prison'? When did Christ 'go and preach' to them? Did he descend after death, or preach through Noah before the flood? The phrase 'spirits in prison' (pneumasin en phylake) is unique in the NT and ambiguous.",
    },

    # ── Matthew 16:18 — On This Rock ──
    {
        "verse_id": "matt.16.18",
        "tradition_a": "Catholic",
        "tradition_b": "Protestant",
        "description": "Catholic tradition reads 'on this rock (petra) I will build my church' as referring to Peter himself (petros) — the first pope, establishing papal authority. Protestant tradition reads 'this rock' as Peter's confession of faith ('You are the Christ, the Son of the living God') — the church is built on the confession, not the man.",
        "resolved_by": "Jesus plays on words: 'You are Peter (Petros), and on this rock (petra) I will build my church.' In Greek, Petros vs petra is a distinction (stone vs rock). In Aramaic (which Jesus likely spoke), both would be kepha. The early church fathers are divided on the interpretation.",
    },

    # ── Romans 9:13 — Jacob Loved, Esau Hated ──
    {
        "verse_id": "rom.9.13",
        "tradition_a": "Calvinist",
        "tradition_b": "Arminian",
        "description": "Calvinist tradition reads 'Jacob I loved, Esau I hated' as God's unconditional election — before birth, God chose Jacob for salvation and Esau for reprobation, demonstrating sovereign predestination. Arminian tradition reads it as God's sovereign choice of Jacob over Esau for the covenant line (not individual salvation), based on God's foreknowledge of their response. The 'hate' is understood as 'loved less' (Hebrew idiom) or 'passed over,' not active condemnation.",
        "resolved_by": "Paul cites Malachi 1:2-3 in context of God's sovereign choice in salvation history, not individual predestination to heaven or hell. The immediately preceding context (Rom 9:6-13) is about which physical descendants of Abraham constitute 'Israel' — the covenant line, not all individuals.",
    },

    # ── Revelation 20:1-6 — Millennium ──
    {
        "verse_id": "rev.20.2",
        "tradition_a": "Premillennial",
        "tradition_b": "Amillennial",
        "description": "Premillennial tradition reads a literal 1,000-year reign of Christ on earth after His second coming, with Satan bound and the martyrs reigning with Christ. Amillennial tradition reads the millennium symbolically as the current church age — Satan is bound (restricted from preventing the gospel's spread) and the saints reign with Christ in heaven. The 1,000 years is a symbolic number for a complete age.",
        "resolved_by": "The 'thousand years' (chilia ete) appears 6 times in Rev 20:1-7. Whether this is literal or symbolic depends on one's hermeneutic for Revelation. Premillennialism was the dominant view of the early church (Papias, Justin Martyr, Irenaeus). Amillennialism became dominant after Augustine.",
    },

    # ── 1 Corinthians 11:10 — Authority on Her Head ──
    {
        "verse_id": "1co.11.10",
        "tradition_a": "Traditional",
        "tradition_b": "Critical",
        "description": "Traditional reading: 'a woman ought to have a symbol of authority on her head' means a head covering (veil) as a sign of her husband's authority over her, based on the creation order. Critical/feminist reading: 'exousia' (authority) here means the woman's own authority to pray/prophesy — the covering is a sign of her authority (not submission), or Paul is quoting a Corinthian slogan that he qualifies. 'Because of the angels' remains obscure.",
        "resolved_by": "The Greek 'exousian echein epi tes kephales' literally means 'to have authority on/over the head.' It can mean either the husband's authority (traditional) or the woman's own authority to minister (critical). The closest parallel in Paul's argument is the honor/shame culture of 1st-century Corinth.",
    },
]

def seed(conn, dry_run=False):
    existing = set()
    for r in conn.execute("SELECT verse_id, tradition_a, tradition_b FROM interpretive_disagreements").fetchall():
        existing.add((r[0], r[1], r[2]))

    added = 0
    for d in DISAGREEMENTS:
        key = (d["verse_id"], d["tradition_a"], d["tradition_b"])
        reverse_key = (d["verse_id"], d["tradition_b"], d["tradition_a"])
        if key in existing or reverse_key in existing:
            continue
        if dry_run:
            print(f"  Would add: {d['verse_id']} — {d['tradition_a']} vs {d['tradition_b']}")
            added += 1
            continue
        conn.execute(
            """INSERT INTO interpretive_disagreements (verse_id, tradition_a, tradition_b, description, resolved_by)
               VALUES (?, ?, ?, ?, ?)""",
            (d["verse_id"], d["tradition_a"], d["tradition_b"],
             d["description"][:500], d.get("resolved_by", "")[:500])
        )
        added += 1

    if not dry_run:
        conn.commit()

    print(f"  Added {added} new disagreements" + (" (dry run)" if dry_run else ""))
    total = conn.execute("SELECT COUNT(*) FROM interpretive_disagreements").fetchone()[0]
    print(f"  Total in DB: {total}")
    return added


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    seed(conn, dry_run=dry_run)
    conn.close()
