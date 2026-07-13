#!/usr/bin/env python3
"""Seed Sod-layer connections from Margaret Barker's Temple Theology."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import add_connection, get_db

CONNECTIONS = [
    # Angel of YHWH — the "lesser YHWH" / second god
    ("exo.23.20", "gen.16.7", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: The angel with YHWH's name in him (Ex 23) is the same divine being as the Angel of the Lord who appears to Hagar — a distinct divine persona"),
    ("exo.23.21", "exo.3.2", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: 'My name is in him' — the same angel who appeared in the burning bush, a manifestation of YHWH himself"),
    ("exo.23.20", "josh.5.13", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: The captain of the Lord's host is the same divine warrior-angel — the commander of the heavenly army"),
    ("exo.23.21", "mal.3.1", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: The 'messenger of the covenant' in Malachi is the same divine Angel — the Lord whom ye seek shall suddenly come to his temple"),
    ("gen.16.7", "judg.13.3", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: The Angel appears to Hagar and to Manoah's wife — same divine messenger who speaks as God in first person"),
    ("judg.13.3", "luke.1.11", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: The annunciation pattern — Angel appears to barren woman, announces birth of a deliverer — connects Samson's birth to John the Baptist's annunciation"),
    ("dan.7.13", "rev.1.13", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: Daniel's 'Son of Man' coming with clouds is the same divine figure as Revelation's Son of Man — the Divine Angel who receives dominion"),
    ("dan.7.13", "matt.26.64", "angel_of_yhwh", "barker_angel_of_yhwh",
     "Barker: Jesus identifies himself as Daniel's Son of Man — 'ye shall see the Son of Man sitting on the right hand of power and coming in the clouds of heaven'"),

    # Temple as microcosm of creation
    ("gen.1.1", "exo.25.40", "temple_microcosm", "creation_temple_microcosm",
     "Barker: The seven days of creation correspond to the seven-branched lampstand — the temple was a model of the created order, 'the pattern of things in the heavens'"),
    ("gen.1.1", "exo.25.9", "temple_microcosm", "creation_temple_microcosm",
     "Barker: 'According to all that I show thee, after the pattern of the tabernacle' — the earthly tabernacle was a microcosm of the heavenly temple"),
    ("exo.25.9", "heb.9.24", "temple_microcosm", "creation_temple_microcosm",
     "Barker: 'The patterns of things in the heavens' — the earthly sanctuary was a copy of the heavenly, established at creation"),
    ("isa.66.1", "acts.7.49", "temple_microcosm", "creation_temple_microcosm",
     "Barker: Stephen quotes Isaiah 66 — 'Heaven is my throne, earth is my footstool' — the temple-cosmos identification is the foundation of temple theology"),
    ("psa.78.69", "gen.1.1", "temple_microcosm", "creation_temple_microcosm",
     "Barker: 'He built his sanctuary like the high heavens, like the earth which he founded forever' — the temple is explicitly compared to creation"),

    # Divine council
    ("1kgs.22.19", "isa.6.1", "divine_council", "barker_divine_council",
     "Barker: Micaiah's vision of the heavenly council and Isaiah's temple vision are the same theology — YHWH as Divine King surrounded by his heavenly court"),
    ("job.1.6", "psa.82.1", "divine_council", "barker_divine_council",
     "Barker: The divine council (sons of God presenting themselves before YHWH) is the original temple theology — a heavenly court mirroring the earthly temple"),
    ("job.1.6", "1kgs.22.19", "divine_council", "barker_divine_council",
     "Barker: Job's divine council scene and Micaiah's vision share the same template — YHWH presides, angels report, decisions are made"),
    ("psa.82.1", "john.10.34", "divine_council", "barker_divine_council",
     "Barker: Jesus quotes Psalm 82 'Ye are gods' to argue that divine sonship is inherent in the original covenant — the council theology underlies theosis"),
    ("deu.32.8", "psa.82.1", "divine_council", "barker_divine_council",
     "Barker: 'When the Most High divided the nations... he set the bounds of the people according to the number of the sons of God' — the divine council governed the nations"),
    ("deu.32.8", "acts.17.26", "divine_council", "barker_divine_council",
     "Barker: Paul's 'determined the bounds of their habitation' echoes Deuteronomy 32 — the divine council's role in allocating nations"),

    # Eden as temple / garden-temple
    ("gen.2.8", "ezek.28.13", "eden_temple", "eden_as_prototype_temple",
     "Barker: Eden was the first temple — the garden of God, where God walked, on the holy mountain. Ezekiel describes the king of Tyre as having been in Eden, the garden of God"),
    ("gen.2.8", "rev.22.1", "eden_temple", "eden_as_prototype_temple",
     "Barker: The river flowing from Eden prefigures the river of life from the throne of God in the New Jerusalem — creation to new creation"),
    ("gen.2.15", "exo.25.8", "eden_temple", "eden_as_prototype_temple",
     "Barker: Adam placed in the garden to 'dress and keep it' — priestly language. The tabernacle and temple continue Eden — God dwelling with man"),
    ("gen.3.24", "exo.26.31", "eden_temple", "eden_as_prototype_temple",
     "Barker: The cherubim guarding Eden's east gate are the same as the cherubim on the temple veil — the veil represents the expulsion from Eden"),
    ("ezek.47.1", "gen.2.10", "eden_temple", "eden_as_prototype_temple",
     "Barker: Ezekiel's temple river parallels Eden's river — both water sources that bring life. The temple restores Eden"),
    ("gen.2.9", "1kgs.6.29", "eden_temple", "eden_as_prototype_temple",
     "Barker: The tree of life in Eden is replicated in the temple's carved palm trees and cherubim — the temple as restored Eden"),

    # Holy of Holies / Day of Atonement
    ("lev.16.1", "heb.9.7", "holy_of_holies", "day_of_atonement_access",
     "Barker: The Day of Atonement was the central ritual — the high priest entering the Holy of Holies is the type of Christ entering heaven"),
    ("lev.16.8", "rev.20.2", "holy_of_holies", "day_of_atonement_access",
     "Barker: The two goats — one for YHWH, one for Azazel — represent the two powers in heaven. Azazel, originally a divine being, becomes Satan"),
    ("lev.16.14", "1jn.2.1", "holy_of_holies", "day_of_atonement_access",
     "Barker: The blood sprinkled on the mercy seat — Christ as our Advocate (Paraclete) with the Father is the heavenly Day of Atonement"),
    ("lev.16.12", "rev.8.3", "holy_of_holies", "day_of_atonement_access",
     "Barker: The incense cloud on the Day of Atonement — the angel offering incense with the prayers of the saints at the golden altar before the throne"),
    ("lev.16.15", "heb.10.19", "holy_of_holies", "day_of_atonement_access",
     "Barker: 'Boldness to enter the holiest by the blood of Jesus' — Christ's blood is the new Day of Atonement, granting access"),
    ("lev.16.15", "matt.27.51", "holy_of_holies", "day_of_atonement_access",
     "Barker: The temple veil rent at Christ's death — access to the Holy of Holies opened. The Day of Atonement typology fulfilled"),

    # Mercy seat / kapporet
    ("exo.25.17", "rom.3.25", "mercy_seat", "mercy_seat_typology",
     "Barker: The mercy seat (kapporet) between the cherubim — Paul says Christ is our 'hilasterion' (mercy seat), the place of atonement"),
    ("exo.25.17", "psa.80.1", "mercy_seat", "mercy_seat_typology",
     "Barker: 'Thou that dwellest between the cherubim' — YHWH's throne is the mercy seat, the place of divine presence"),
    ("exo.25.22", "rev.11.19", "mercy_seat", "mercy_seat_typology",
     "Barker: 'There I will meet with thee' — the ark of the covenant in the heavenly temple, seen in Revelation"),

    # Divine ascent / visionary ascent
    ("gen.28.12", "john.1.51", "divine_ascent", "visionary_ascent",
     "Barker: Jacob's ladder — the heavenly ascent between earth and heaven. Jesus says 'Ye shall see heaven open, and the angels of God ascending and descending upon the Son of Man'"),
    ("isa.6.1", "john.12.41", "divine_ascent", "visionary_ascent",
     "Barker: 'Isaiah saw his glory and spake of him' — Isaiah's temple vision of YHWH is identified by John as a vision of Christ"),
    ("ezek.1.1", "rev.4.1", "divine_ascent", "visionary_ascent",
     "Barker: Ezekiel's vision of the chariot-throne and John's vision of the heavenly throne room — the same merkabah tradition"),
    ("2cor.12.2", "1kgs.22.19", "divine_ascent", "visionary_ascent",
     "Barker: Paul caught up to the third heaven — a visionary ascent like Micaiah's vision of the heavenly council"),
    ("exo.24.9", "gen.28.12", "divine_ascent", "visionary_ascent",
     "Barker: The elders ascending Sinai to see God and eat in his presence — the first biblical 'temple ascent' narrative"),

    # Theosis / becoming divine
    ("psa.82.6", "john.10.34", "theosis", "becoming_divine_through_covenant",
     "Barker: Jesus' use of Psalm 82 at John 10:34 is the key text for early Christian theosis — 'if he called them gods unto whom the word of God came'"),
    ("2pet.1.4", "psa.82.6", "theosis", "becoming_divine_through_covenant",
     "Barker: 'Partakers of the divine nature' (2 Pet 1:4) and 'Ye are gods' (Ps 82:6) reflect the temple theology of theosis — humans can become divine through covenant"),
    ("rom.8.29", "1jn.3.2", "theosis", "becoming_divine_through_covenant",
     "Barker: 'Predestinated to be conformed to the image of his Son' and 'we shall be like him' represent theosis"),

    # Melchizedek / royal priesthood
    ("gen.14.18", "heb.7.1", "kingdom_priesthood", "melchizedek_priesthood",
     "Barker: Melchizedek as 'priest of El Elyon (God Most High)' represents the pre-Levitical, original priesthood — the order of the Son of God"),
    ("psa.110.4", "heb.7.17", "kingdom_priesthood", "melchizedek_priesthood",
     "Barker: 'Thou art a priest forever after the order of Melchizedek' — this is not a new order but the restoration of the original temple priesthood"),
    ("exo.19.6", "1pet.2.9", "kingdom_priesthood", "melchizedek_priesthood",
     "Barker: 'A kingdom of priests' — the original covenant envisioned all Israel as priests. The Levitical priesthood was a later restriction"),
    ("gen.14.18", "11Q13", "kingdom_priesthood", "melchizedek_priesthood",
     "Barker: The DSS Melchizedek Scroll (11Q13) identifies Melchizedek as a heavenly high priest who will execute judgment — the template for Hebrews 7"),
    ("11Q13", "heb.7.1", "kingdom_priesthood", "melchizedek_priesthood",
     "Barker: Hebrews' Melchizedek theology is rooted in the same tradition as the DSS Melchizedek Scroll — a heavenly, not earthly, high priest"),

    # Divine marriage
    ("hos.2.19", "rev.19.7", "divine_marriage", "sacred_marriage_temple",
     "Barker: 'I will betroth thee unto me forever' — Hosea's marriage metaphor for the covenant is the root of Revelation's marriage of the Lamb"),
    ("song.1.1", "eph.5.25", "divine_marriage", "sacred_marriage_temple",
     "Barker: The Song of Solomon read as temple liturgy — the union of the king and the land/people, which Paul applies to Christ and the Church"),
    ("eph.5.25", "rev.19.7", "divine_marriage", "sacred_marriage_temple",
     "Barker: Christ's love for the Church and the marriage of the Lamb — the temple marriage tradition from creation to new creation"),

    # Sacred center / cosmic mountain
    ("psa.24.3", "isa.2.2", "cosmic_mountain", "mountain_of_god",
     "Barker: 'The mountain of the Lord's house shall be established in the top of the mountains' — Zion as the cosmic mountain, the center of the world"),
    ("psa.24.3", "ezek.40.2", "cosmic_mountain", "mountain_of_god",
     "Barker: Ezekiel's temple vision on a 'very high mountain' continues the cosmic mountain tradition — the mountain of God"),
    ("gen.28.12", "john.1.51", "cosmic_mountain", "mountain_of_god",
     "Barker: Bethel as the 'gate of heaven' — Jacob's ladder is the axis mundi, the connection between heaven and earth, which Jesus claims as himself"),
    ("ezek.28.14", "gen.2.8", "eden_temple", "eden_as_prototype_temple",
     "Barker: 'Thou wast upon the holy mountain of God' — the king of Tyre as an Eden figure, showing Eden was understood as the mountain of God"),

    # Watchers / Enochic tradition
    ("gen.6.1", "jude.1.6", "watchers_enedochic", "barker_watchers",
     "Barker: The 'sons of God' in Genesis 6 — the Watcher tradition of 1 Enoch is essential background for understanding Jude and 2 Peter"),
    ("gen.6.4", "1pet.3.19", "watchers_enedochic", "barker_watchers",
     "Barker: 'Spirits in prison' (1 Pet 3:19) are the imprisoned Watchers of Enochic tradition — Christ's descent to them is part of this temple theology"),
    ("jude.1.6", "1enoch.10.4", "watchers_enedochic", "barker_watchers",
     "Barker: Jude's quotation of 1 Enoch shows the Watcher tradition was integral to early Christian theology"),
]

def main():
    conn = get_db()
    print("=" * 60)
    print("  Margaret Barker — Sod Layer Expansion")
    print("=" * 60)

    count = 0
    for source, target, conn_type, subtype, note in CONNECTIONS:
        try:
            # Check if this connection already exists
            existing = conn.execute(
                "SELECT COUNT(*) FROM connections WHERE source_verse = ? AND target_verse = ? AND type = ? AND subtype = ?",
                (source, target, conn_type, subtype)
            ).fetchone()[0]

            if existing == 0:
                add_connection(conn, source, target, layer="sod",
                              type_name=conn_type, subtype=subtype,
                              strength=0.55, confidence=0.45,
                              discovered_by="human",
                              metadata={"scholar": "Margaret Barker",
                                       "note": note[:200],
                                       "source": "Temple Theology"})
                count += 1
        except Exception:
            pass

    conn.commit()
    total_sod = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='sod'").fetchone()["c"]
    print(f"  Added {count} new Barker Sod connections")
    print(f"  Sod layer total: {total_sod}")
    conn.close()

if __name__ == "__main__":
    main()
