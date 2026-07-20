"""
Built-in scholarly claims for truth evaluation, organized by topic.
Each topic contains claims from multiple scholars with verse references.
Evidence levels: L1_LITERAL (text says it), L1_HISTORICAL (text narrates it),
L2_CONTEXTUAL (implied), L3_INTERPRETIVE (scholar reads it), L3_SPECULATIVE (reconstructed).
"""

SCHOLARLY_CLAIMS = {
    "temple_microcosm": [
        {
            "scholar": 'G.K. Beale',
            "claim": 'Eden was the first temple — a proto-sanctuary where God dwelt, and the later tabernacle/temple was designed as a microcosm of Edenic creation',
            "verses": ['gen.2.8', 'gen.2.15', 'ezek.28.13', 'exo.25.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'G.K. Beale',
            "claim": 'The 7-branch menorah in the tabernacle represents the 7 days of creation',
            "verses": ['exo.25.31', 'exo.25.37', 'gen.1.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'The first temple was understood as the microcosm of creation, with the veil representing the cosmos',
            "verses": ['exo.26.31', 'exo.28.15', '2chr.3.14'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'John H. Walton',
            "claim": 'Genesis 1 describes God assigning functions to His cosmic temple, not the origin of material stuff',
            "verses": ['gen.1.1', 'gen.1.14', 'isa.66.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'G.K. Beale',
            "claim": "Adam was the first priest-king, commissioned to extend Eden's sanctuary to fill the earth",
            "verses": ['gen.1.28', 'gen.2.15', 'rev.21.1'],
            "level": "L2_CONTEXTUAL",
        },
    ],
    "angel_yhwh_divine_council": [
        {
            "scholar": 'Michael S. Heiser',
            "claim": "The term 'elohim' is a label for any member of the divine council, not a proper name for God",
            "verses": ['psa.82.1', 'psa.82.6', 'deu.32.17', 'exo.22.28'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Michael S. Heiser',
            "claim": "Deuteronomy 32:8 originally read 'sons of God' (divine beings), not 'sons of Israel'",
            "verses": ['deu.32.8', 'deu.32.9'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Michael S. Heiser',
            "claim": 'Psalm 82 depicts Yahweh judging the divine council for ruling the nations unjustly',
            "verses": ['psa.82.1', 'psa.82.6', 'john.10.34'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'The Angel of YHWH was understood as a distinct divine being — a second Yahweh figure who was visible',
            "verses": ['exo.3.2', 'exo.3.6', 'gen.22.11', 'gen.31.13', 'judg.6.11'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'First Temple religion was binitarian — it recognized two divine powers in heaven',
            "verses": ['dan.7.9', 'dan.7.13', 'phil.2.6', 'heb.1.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'The Angel of YHWH was identified with the divine Name (Shem) and the Glory (Kavod)',
            "verses": ['exo.23.21', 'deu.12.5', 'john.17.6'],
            "level": "L2_CONTEXTUAL",
        },
    ],
    "josiah_reform": [
        {
            "scholar": 'Margaret Barker',
            "claim": "Josiah's reform was a catastrophic rupture that destroyed First Temple religion, including its binitarian theology and Asherah worship",
            "verses": ['2kgs.22.1', '2kgs.23.4', '2kgs.23.6', '2kgs.23.11', 'jer.44.15'],
            "level": "L1_HISTORICAL",
        },
        {
            "scholar": 'Frank Moore Cross / E.W. Nicholson',
            "claim": "Josiah's reform produced the 'Book of the Law' (Deuteronomy) to authorize centralization and purge of non-Yahwistic elements",
            "verses": ['2kgs.22.8', 'deu.12.1', 'deu.16.21', '2kgs.23.1'],
            "level": "L1_HISTORICAL",
        },
        {
            "scholar": 'Scholarly Consensus',
            "claim": "Josiah's reform centralized all worship to Jerusalem, eliminating local shrines and changing Israelite religion into a centralized state cult",
            "verses": ['2kgs.23.4', '2kgs.23.8', 'deu.12.5', '2kgs.18.22'],
            "level": "L1_HISTORICAL",
        },
        {
            "scholar": 'Margaret Barker / William Dever',
            "claim": "Josiah's reform suppressed popular religion involving Asherah, household deities, and family rituals that had coexisted with Yahweh worship for centuries",
            "verses": ['2kgs.23.4', '2kgs.23.24', 'jer.44.15', 'deu.16.21'],
            "level": "L1_HISTORICAL",
        },
    ],
    "queen_of_heaven_asherah": [
        {
            "scholar": 'William G. Dever / Raphael Patai',
            "claim": "Asherah was YHWH's consort, as confirmed by archaeological inscriptions from Kuntillet Ajrud and Khirbet el-Qom",
            "verses": ['jer.7.18', 'jer.44.17', '1kgs.14.23', '2kgs.23.6'],
            "level": "L1_HISTORICAL",
        },
        {
            "scholar": 'Raphael Patai / Margaret Barker',
            "claim": 'Asherah was the Mother Goddess, her symbols (the Asherah pole, sacred trees) were fixtures in the Jerusalem temple before Josiah',
            "verses": ['judg.3.7', '1kgs.15.13', '2kgs.21.7', '2kgs.23.6', 'deu.16.21'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Susan Ackerman / Othmar Keel',
            "claim": "The 'Queen of Heaven' is specifically Ishtar/Astarte, not Asherah, based on Mesopotamian titles and rituals",
            "verses": ['jer.7.18', 'jer.44.19', '1kgs.11.5', 'ezek.8.14'],
            "level": "L2_CONTEXTUAL",
        },
    ],
    "two_yahwehs_origins": [
        {
            "scholar": 'Margaret Barker',
            "claim": "The 'two Yahwehs' tradition originated in the First Temple, distinguishing the Most High from the visible Angel/Son",
            "verses": ['dan.7.9', 'dan.7.13', 'mal.3.1', 'john.1.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Alan Segal / Daniel Boyarin',
            "claim": "Second Temple Judaism had a 'Two Powers in Heaven' theology that early Christianity inherited",
            "verses": ['dan.7.9', 'dan.7.13', 'john.1.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Michael S. Heiser',
            "claim": 'The Bible presents two distinct Yahweh figures — the visible Angel and the invisible YHWH — without violating monotheism',
            "verses": ['gen.16.7', 'gen.16.13', 'gen.48.15', '1tim.6.16'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Richard Bauckham',
            "claim": 'New Testament writers applied YHWH texts (Isaiah 45:23, Joel 2:32, Psalm 102) to Jesus, placing Him within the unique divine identity',
            "verses": ['isa.45.23', 'phil.2.10', 'joel.2.32', 'rom.10.13', 'psa.102.25'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Mark S. Smith / Frank Moore Cross',
            "claim": 'YHWH was originally a divine warrior deity from Edom/Midian who was later merged with the Canaanite high god El',
            "verses": ['deu.33.2', 'judg.5.4', 'hab.3.3', 'exo.3.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": "In First Temple theology, Yahweh (the Son) was distinguished from El Elyon (the Father) — Yahweh was the visible manifestation of the invisible Most High, the 'Great Angel,' and Jesus was recognized as this Yahweh figure",
            "verses": ['deu.32.8', 'deu.32.9', 'psa.82.1', 'psa.82.6', 'dan.7.9', 'gen.16.7', 'gen.16.13', 'exo.3.2', 'exo.23.20', 'john.1.1', 'john.8.58', '1cor.8.5'],
            "level": "L2_CONTEXTUAL",
        },
    ],
    "atonement_theosis": [
        {
            "scholar": 'Margaret Barker',
            "claim": 'When the high priest entered the Holy of Holies on the Day of Atonement, he shed his earthly garments and was transformed into a divine being — this was a theosis transformation ritual',
            "verses": ['lev.16.2', 'lev.16.17', 'lev.16.32', 'exo.28.2', 'exo.30.22', 'heb.9.1', 'heb.10.19'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": "The 'Son of Man' figure in Daniel 7 derives from First Temple high priest ideology — the vision of a human figure ascending to God describes the high priest's apotheosis in the Holy of Holies",
            "verses": ['dan.7.9', 'dan.7.13', 'dan.7.14', 'psa.110.1', 'psa.110.4', 'matt.26.64', 'mark.14.62', 'rev.1.7'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": "The high priest was the original messianic figure — the 'anointed one' who wore the divine name, entered the Holy of Holies, ate the bread of the Presence, and made the atonement offering",
            "verses": ['exo.28.36', 'exo.28.39', 'lev.24.5', 'lev.16.15', 'psa.110.4', 'heb.4.14', 'heb.5.5', 'heb.7.11', 'gen.14.18'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'Theosis — the transformation of humans into divine beings — was the central purpose of First Temple ritual, not a later Hellenistic import; the anointing oil was the sacrament of becoming divine',
            "verses": ['psa.82.6', 'exo.30.22', 'john.10.34', 'john.17.21', '2pet.1.4', 'rom.8.14', '1john.3.2', 'rev.3.21'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": "Early Christianity was not a new Hellenistic religion but a direct restoration of First Temple religion suppressed by Josiah's reforms — the gospel was about restoring the original temple, its priesthood, and its liturgy",
            "verses": ['2kgs.23.1', '2kgs.23.25', 'heb.9.1', 'rev.4.1', 'rev.21.1', 'matt.5.17', '1cor.3.16', 'acts.7.44'],
            "level": "L1_HISTORICAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'The First Temple venerated a divine feminine figure — Wisdom/Sophia/Asherah — understood as the mother of the Lord and consort of El Elyon, symbolized by the menorah and violently suppressed by Josiah',
            "verses": ['prov.8.22', 'prov.8.31', 'jer.44.17', '2kgs.23.4', '2kgs.23.7', 'gen.1.27', 'exo.25.31', '1kgs.15.13'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'The menorah was understood as the Tree of Life in the temple; the Asherah pole removed by Josiah was a stylised tree, and the only stylised tree in the temple was the menorah',
            "verses": ['exo.25.31', 'exo.25.37', 'gen.2.9', 'gen.3.22', 'rev.2.7', 'rev.22.2', '1kgs.7.49', 'zec.4.1'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'The early Christian Eucharist combined two rituals originally exclusive to the high priest: carrying blood into the holy of holies on Yom Kippur and eating the showbread on the Sabbath',
            "verses": ['lev.16.15', 'lev.24.5', 'lev.24.9', 'heb.9.11', 'heb.10.19', '1cor.11.23', 'matt.26.26'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": 'The Book of Revelation is steeped in temple imagery and preserves the original temple worldview — the heavenly temple, the ark of the covenant, the altar, the incense, the seven lampstands',
            "verses": ['rev.1.12', 'rev.4.1', 'rev.4.11', 'rev.8.3', 'rev.11.19', 'rev.15.5', 'rev.21.22'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Margaret Barker',
            "claim": "The Book of Mormon's depiction of pre-exilic Israelite religion — multiple divine persons, temple theology, tree of life symbolism, lost truths — aligns with reconstructed First Temple religion",
            "verses": ['1ne.1.1', '1ne.8.1', '1ne.8.35', '1ne.13.40', '2ne.25.23', 'mosiah.13.11', 'alma.11.26', 'alma.42.1'],
            "level": "L2_CONTEXTUAL",
        },
    ],
    "bom_temple": [
        {
            "scholar": 'Dave Butler',
            "claim": "Nephi's first sentence (1 Nephi 1:1) uses temple language — 'goodness of God' refers to the peace offering and 'mysteries of God' refers to the Holy of Holies — establishing the Book of Mormon as a temple text",
            "verses": ['1ne.1.1'],
            "level": "L3_INTERPRETIVE",
        },
        {
            "scholar": 'Dave Butler',
            "claim": "Lehi's dream (1 Nephi 8) is a literary temple ceremony corresponding to the three rooms of Solomon's Temple — courtyard, holy place, and holy of holies — culminating at the Tree of Life",
            "verses": ['1ne.8.1', '1ne.8.35', '1kgs.6.1', 'exo.25.31'],
            "level": "L3_INTERPRETIVE",
        },
        {
            "scholar": 'Dave Butler',
            "claim": "Nephi's vision in 1 Nephi 11-14 follows the Day of Atonement pattern — the Lord's coming from His temple, judgment of the people, and redemption of the righteous",
            "verses": ['1ne.11.1', '1ne.14.30', 'lev.16.1', 'lev.16.34'],
            "level": "L2_CONTEXTUAL",
        },
        {
            "scholar": 'Dave Butler',
            "claim": "Josiah's reforms removed 'plain and precious things' from Hebrew scripture and temple practice; Lehi and Nephi fled Jerusalem to preserve the true temple religion that Josiah suppressed",
            "verses": ['2kgs.22.1', '2kgs.23.37', '1ne.1.1', '1ne.1.20', '1ne.13.26'],
            "level": "L1_HISTORICAL",
        },
        {
            "scholar": 'Dave Butler',
            "claim": "The 'Worship of the Shalems' (from Hebrew shalem = peace offering) was a temple ceremony where initiates passed through three temple rooms, were washed and anointed, shared a sacred meal, and petitioned at the veil",
            "verses": ['exo.24.1', 'exo.24.18', 'lev.3.1', 'lev.7.11'],
            "level": "L3_SPECULATIVE",
        },
        {
            "scholar": 'Dave Butler',
            "claim": 'The temple ordinance of the visionary men included a dramatic representation of the expulsion of Adam and Eve from Eden and their return, embodying doctrines of the Fall and Redemption',
            "verses": ['gen.3.1', 'gen.3.24', 'moses.4.1', '2ne.2.1', '2ne.2.30'],
            "level": "L3_SPECULATIVE",
        },
        {
            "scholar": 'Dave Butler',
            "claim": "The Sermon on the Mount (Matthew 5-7) follows the same structural pattern as a temple ceremony — an ascent through progressive stages of holiness culminating in entering God's presence",
            "verses": ['matt.5.1', 'matt.7.29'],
            "level": "L3_INTERPRETIVE",
        },
        {
            "scholar": 'Dave Butler',
            "claim": "Book of Mormon prophets were members of a 'visionary men' lineage who wrote using temple language as a symbolic vocabulary, expecting readers with 'eyes to see and ears to hear'",
            "verses": ['1ne.1.1', '2ne.4.1', 'isa.6.1', 'matt.13.13'],
            "level": "L3_INTERPRETIVE",
        },
    ],
}
