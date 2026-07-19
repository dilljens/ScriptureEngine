"""
Built-in scholarly claims for truth evaluation, organized by topic.
Each topic contains claims from multiple scholars with verse references.
"""

SCHOLARLY_CLAIMS = {
    "temple_microcosm": [
        {
            "scholar": "G.K. Beale",
            "claim": "Eden was the first temple — a proto-sanctuary where God dwelt, and the later tabernacle/temple was designed as a microcosm of Edenic creation",
            "verses": ["gen.2.8", "gen.2.15", "ezek.28.13", "exo.25.1"],
        },
        {
            "scholar": "G.K. Beale",
            "claim": "The 7-branch menorah in the tabernacle represents the 7 days of creation",
            "verses": ["exo.25.31", "exo.25.37", "gen.1.1"],
        },
        {
            "scholar": "Margaret Barker",
            "claim": "The first temple was understood as the microcosm of creation, with the veil representing the cosmos",
            "verses": ["exo.26.31", "exo.28.15", "2chr.3.14"],
        },
        {
            "scholar": "John H. Walton",
            "claim": "Genesis 1 describes God assigning functions to His cosmic temple, not the origin of material stuff",
            "verses": ["gen.1.1", "gen.1.14", "isa.66.1"],
        },
        {
            "scholar": "G.K. Beale",
            "claim": "Adam was the first priest-king, commissioned to extend Eden's sanctuary to fill the earth",
            "verses": ["gen.1.28", "gen.2.15", "rev.21.1"],
        },
    ],
    "angel_yhwh_divine_council": [
        {
            "scholar": "Michael S. Heiser",
            "claim": "The term 'elohim' is a label for any member of the divine council, not a proper name for God",
            "verses": ["psa.82.1", "psa.82.6", "deu.32.17", "exo.22.28"],
        },
        {
            "scholar": "Michael S. Heiser",
            "claim": "Deuteronomy 32:8 originally read 'sons of God' (divine beings), not 'sons of Israel'",
            "verses": ["deu.32.8", "deu.32.9"],
        },
        {
            "scholar": "Michael S. Heiser",
            "claim": "Psalm 82 depicts Yahweh judging the divine council for ruling the nations unjustly",
            "verses": ["psa.82.1", "psa.82.6", "john.10.34"],
        },
        {
            "scholar": "Margaret Barker",
            "claim": "The Angel of YHWH was understood as a distinct divine being — a second Yahweh figure who was visible",
            "verses": ["exo.3.2", "exo.3.6", "gen.22.11", "gen.31.13", "judg.6.11"],
        },
        {
            "scholar": "Margaret Barker",
            "claim": "First Temple religion was binitarian — it recognized two divine powers in heaven",
            "verses": ["dan.7.9", "dan.7.13", "phil.2.6", "heb.1.1"],
        },
        {
            "scholar": "Margaret Barker",
            "claim": "The Angel of YHWH was identified with the divine Name (Shem) and the Glory (Kavod)",
            "verses": ["exo.23.21", "deu.12.5", "john.17.6"],
        },
    ],
    "josiah_reform": [
        {
            "scholar": "Margaret Barker",
            "claim": "Josiah's reform was a catastrophic rupture that destroyed First Temple religion, including its binitarian theology and Asherah worship",
            "verses": ["2kgs.22.1", "2kgs.23.4", "2kgs.23.6", "2kgs.23.11", "jer.44.15"],
        },
        {
            "scholar": "Frank Moore Cross / E.W. Nicholson",
            "claim": "Josiah's reform produced the 'Book of the Law' (Deuteronomy) to authorize centralization and purge of non-Yahwistic elements",
            "verses": ["2kgs.22.8", "deu.12.1", "deu.16.21", "2kgs.23.1"],
        },
        {
            "scholar": "Scholarly Consensus",
            "claim": "Josiah's reform centralized all worship to Jerusalem, eliminating local shrines and changing Israelite religion into a centralized state cult",
            "verses": ["2kgs.23.4", "2kgs.23.8", "deu.12.5", "2kgs.18.22"],
        },
        {
            "scholar": "Margaret Barker / William Dever",
            "claim": "Josiah's reform suppressed popular religion involving Asherah, household deities, and family rituals that had coexisted with Yahweh worship for centuries",
            "verses": ["2kgs.23.4", "2kgs.23.24", "jer.44.15", "deu.16.21"],
        },
    ],
    "queen_of_heaven_asherah": [
        {
            "scholar": "William G. Dever / Raphael Patai",
            "claim": "Asherah was YHWH's consort, as confirmed by archaeological inscriptions from Kuntillet Ajrud and Khirbet el-Qom",
            "verses": ["jer.7.18", "jer.44.17", "1kgs.14.23", "2kgs.23.6"],
        },
        {
            "scholar": "Raphael Patai / Margaret Barker",
            "claim": "Asherah was the Mother Goddess, her symbols (the Asherah pole, sacred trees) were fixtures in the Jerusalem temple before Josiah",
            "verses": ["judg.3.7", "1kgs.15.13", "2kgs.21.7", "2kgs.23.6", "deu.16.21"],
        },
        {
            "scholar": "Susan Ackerman / Othmar Keel",
            "claim": "The 'Queen of Heaven' is specifically Ishtar/Astarte, not Asherah, based on Mesopotamian titles and rituals",
            "verses": ["jer.7.18", "jer.44.19", "1kgs.11.5", "ezek.8.14"],
        },
    ],
    "two_yahwehs_origins": [
        {
            "scholar": "Margaret Barker",
            "claim": "The 'two Yahwehs' tradition originated in the First Temple, distinguishing the Most High from the visible Angel/Son",
            "verses": ["dan.7.9", "dan.7.13", "mal.3.1", "john.1.1"],
        },
        {
            "scholar": "Alan Segal / Daniel Boyarin",
            "claim": "Second Temple Judaism had a 'Two Powers in Heaven' theology that early Christianity inherited",
            "verses": ["dan.7.9", "dan.7.13", "john.1.1"],
        },
        {
            "scholar": "Michael S. Heiser",
            "claim": "The Bible presents two distinct Yahweh figures — the visible Angel and the invisible YHWH — without violating monotheism",
            "verses": ["gen.16.7", "gen.16.13", "gen.48.15", "1tim.6.16"],
        },
        {
            "scholar": "Richard Bauckham",
            "claim": "New Testament writers applied YHWH texts (Isaiah 45:23, Joel 2:32, Psalm 102) to Jesus, placing Him within the unique divine identity",
            "verses": ["isa.45.23", "phil.2.10", "joel.2.32", "rom.10.13", "psa.102.25"],
        },
        {
            "scholar": "Mark S. Smith / Frank Moore Cross",
            "claim": "YHWH was originally a divine warrior deity from Edom/Midian who was later merged with the Canaanite high god El",
            "verses": ["deu.33.2", "judg.5.4", "hab.3.3", "exo.3.1"],
        },
    ],
}
