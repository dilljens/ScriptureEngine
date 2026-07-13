#!/usr/bin/env python3
"""Seed hub notes — curated canonical learning paths through the scripture graph.

Creates the hub_notes, hub_note_steps, hub_note_progress, and hub_topic_links
tables, then seeds 15 hub notes with 8-15 steps each.

Usage:
    python3 scripts/seed_hub_notes.py
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS hub_notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    theme TEXT NOT NULL,
    icon TEXT DEFAULT '',
    seed_verse TEXT,
    tg_topic_ids TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    version INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS hub_note_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hub_id TEXT NOT NULL REFERENCES hub_notes(id),
    step_number INTEGER NOT NULL,
    verse_id TEXT NOT NULL,
    title TEXT NOT NULL,
    explanation TEXT NOT NULL,
    connection_type TEXT,
    pa_r_de_s_level TEXT,
    tg_topic_ids TEXT DEFAULT '[]',
    UNIQUE(hub_id, step_number)
);

CREATE TABLE IF NOT EXISTS hub_note_progress (
    user_id TEXT NOT NULL DEFAULT 'default',
    hub_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (user_id, hub_id, step_number)
);

CREATE TABLE IF NOT EXISTS hub_topic_links (
    hub_id TEXT NOT NULL REFERENCES hub_notes(id),
    topic_id TEXT NOT NULL REFERENCES topical_guide(id),
    relevance_weight REAL DEFAULT 0.5,
    PRIMARY KEY (hub_id, topic_id)
);
"""


# ── 15 hub notes with 8-15 steps each ──

HUB_NOTES = [
    {
        "id": "covenant",
        "title": "The Covenant Thread",
        "description": "Trace God's covenant relationship with His people from Noah through Abraham, Moses, David, the New Covenant, and its fulfillment in Christ.",
        "theme": "covenant",
        "icon": "🤝",
        "seed_verse": "gen.9.8",
        "tg_topic_ids": ["covenant", "abrahamic-covenant", "grace"],
        "steps": [
            {"step": 1, "verse": "gen.9.8-17", "title": "Noahic Covenant", "explanation": "God establishes His first covenant with Noah after the flood, promising never to destroy the earth by water again. The rainbow is given as the sign of this covenant.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["covenant"]},
            {"step": 2, "verse": "gen.15.1-21", "title": "Abrahamic Covenant", "explanation": "God cuts covenant with Abraham, promising innumerable seed and the land of Canaan. The smoking furnace and burning lamp pass between the pieces, signifying God's unilateral oath.", "conn": "type_antitype", "pardes": "remez", "tg": ["abrahamic-covenant", "covenant"]},
            {"step": 3, "verse": "gen.17.1-14", "title": "Sign of the Covenant", "explanation": "Circumcision is given as the token of the Abrahamic Covenant. This physical sign marks the covenant people and prefigures the circumcision of the heart.", "conn": "same_lemma", "pardes": "pshat", "tg": ["covenant", "circumcision"]},
            {"step": 4, "verse": "exo.24.1-8", "title": "Mosaic Covenant", "explanation": "Moses ratifies the covenant at Sinai with blood sacrifice. The blood of the covenant binds Israel to obey God's law. This becomes the foundation of Israel's national identity.", "conn": "type_antitype", "pardes": "pshat", "tg": ["covenant", "law-of-moses"]},
            {"step": 5, "verse": "2sam.7.1-17", "title": "Davidic Covenant", "explanation": "God promises David an everlasting dynasty. The throne of David's kingdom will be established forever. This covenant points forward to the Messiah as the ultimate Son of David.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["covenant", "david"]},
            {"step": 6, "verse": "jer.31.31-34", "title": "New Covenant Promised", "explanation": "Jeremiah prophesies a New Covenant — not like the old one Israel broke. God will write His law on hearts, and all shall know Him. This is the climax of the covenant narrative.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["covenant", "new-covenant"]},
            {"step": 7, "verse": "luke.22.14-20", "title": "Christ's Blood of the Covenant", "explanation": "At the Last Supper, Jesus institutes the sacrament, declaring that His blood is the blood of the New Covenant, shed for the remission of sins. The Passover is fulfilled.", "conn": "direct_quotation", "pardes": "drash", "tg": ["jesus-christ", "atonement", "sacrament"]},
            {"step": 8, "verse": "heb.8.6-13", "title": "Christ as Mediator", "explanation": "Christ is the mediator of a better covenant, established on better promises. The old covenant is made obsolete by the new. This is the theological explanation of the covenant transition.", "conn": "interpretive", "pardes": "drash", "tg": ["jesus-christ", "covenant", "priesthood"]},
            {"step": 9, "verse": "gal.3.1-29", "title": "Covenant and Faith", "explanation": "Paul explains that those who have faith are children of Abraham. The covenant was given before the law and is not annulled by it. All are one in Christ Jesus.", "conn": "interpretive", "pardes": "sod", "tg": ["faith", "abrahamic-covenant", "grace"]},
            {"step": 10, "verse": "dc.132.1-33", "title": "New and Everlasting Covenant", "explanation": "The covenant of eternal marriage — the new and everlasting covenant — seals families for eternity. This is the restoration of the covenant in its fulness.", "conn": "interpretive", "pardes": "sod", "tg": ["covenant", "marriage", "exaltation"]},
        ]
    },
    {
        "id": "temple",
        "title": "The Temple Pattern",
        "description": "Follow the temple through scripture — from Eden as God's first sanctuary, through the Tabernacle, Solomon's Temple, Christ as the Temple, and the heavenly temple.",
        "theme": "temple",
        "icon": "🏛️",
        "seed_verse": "gen.2.8",
        "tg_topic_ids": ["temple", "holiness", "worship"],
        "steps": [
            {"step": 1, "verse": "gen.2.8-14", "title": "Eden as Sanctuary", "explanation": "The Garden of Eden is described in temple-like language — a sacred space where God walks with man. The rivers, precious stones, and cherubim all foreshadow the later Tabernacle.", "conn": "structural", "pardes": "pshat", "tg": ["temple", "creation"]},
            {"step": 2, "verse": "exo.25.1-9", "title": "The Tabernacle Commanded", "explanation": "God commands Moses to build a sanctuary 'that I may dwell among them.' The pattern shown on the mountain becomes the blueprint for Israel's mobile temple.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["tabernacle", "temple", "worship"]},
            {"step": 3, "verse": "exo.40.1-38", "title": "Tabernacle Consecrated", "explanation": "Moses consecrates the Tabernacle and the glory of the Lord fills it. The cloud and fire rest upon it, signaling God's presence with His people.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["tabernacle", "glory-of-god"]},
            {"step": 4, "verse": "1kgs.6.1-38", "title": "Solomon Builds the Temple", "explanation": "Solomon builds the first permanent Temple in Jerusalem. Its dimensions, materials, and furnishings follow the Tabernacle pattern but on a grander scale.", "conn": "structural", "pardes": "pshat", "tg": ["temple", "solomon"]},
            {"step": 5, "verse": "1kgs.8.1-66", "title": "Temple Dedicated", "explanation": "Solomon dedicates the Temple with prayer and sacrifice. The glory of the Lord fills the house, and Solomon prays that all who pray toward this house will be heard.", "conn": "direct_quotation", "pardes": "remez", "tg": ["temple", "prayer", "dedication"]},
            {"step": 6, "verse": "ezek.40.1-4", "title": "Ezekiel's Temple Vision", "explanation": "Ezekiel sees a detailed vision of a future temple. An angel measures every part of it. This vision points to both the post-exilic temple and a future, eschatological temple.", "conn": "prophetic_fulfillment", "pardes": "sod", "tg": ["temple", "ezekiel"]},
            {"step": 7, "verse": "john.2.18-22", "title": "Christ's Body is the Temple", "explanation": "Jesus declares, 'Destroy this temple and in three days I will raise it up.' He speaks of His body as the true temple — the meeting place between God and man.", "conn": "type_antitype", "pardes": "drash", "tg": ["jesus-christ", "temple", "resurrection"]},
            {"step": 8, "verse": "1cor.3.16-17", "title": "We Are God's Temple", "explanation": "Paul teaches that believers collectively are the temple of God. The Spirit dwells in us. This shifts the temple concept from a building to a people.", "conn": "interpretive", "pardes": "drash", "tg": ["temple", "holy-ghost", "church-of-god"]},
            {"step": 9, "verse": "heb.9.1-28", "title": "Heavenly Sanctuary", "explanation": "Christ enters the heavenly sanctuary, not made with hands. The earthly temple was a copy and shadow of the heavenly reality. This is the ultimate temple theology.", "conn": "interpretive", "pardes": "sod", "tg": ["temple", "jesus-christ", "atonement"]},
            {"step": 10, "verse": "rev.21.1-22", "title": "The Temple is the Lord God Almighty", "explanation": "In the New Jerusalem, John sees no temple — because the Lord God Almighty and the Lamb are the temple. The temple has become God's direct presence with His people.", "conn": "type_antitype", "pardes": "sod", "tg": ["temple", "jerusalem", "celestial-glory"]},
        ]
    },
    {
        "id": "lamb_of_god",
        "title": "The Lamb of God",
        "description": "Trace the sacrificial lamb through scripture — from the Binding of Isaac through Passover, Isaiah's Suffering Servant, John the Baptist's proclamation, and the heavenly worship of the Lamb.",
        "theme": "atonement",
        "icon": "🐑",
        "seed_verse": "gen.22.8",
        "tg_topic_ids": ["jesus-christ", "atonement", "sacrifice"],
        "steps": [
            {"step": 1, "verse": "gen.22.1-14", "title": "The Binding of Isaac", "explanation": "Abraham's willingness to sacrifice Isaac prefigures the Father's sacrifice of His Son. Isaac carries the wood up Mount Moriah; God provides the ram as a substitute.", "conn": "type_antitype", "pardes": "remez", "tg": ["sacrifice", "obedience", "jesus-christ-prophecies-about"]},
            {"step": 2, "verse": "exo.12.1-28", "title": "The Passover Lamb", "explanation": "The Passover lamb must be without blemish. Its blood on the doorposts saves Israel from the destroyer. This becomes the defining type of Christ's atoning sacrifice.", "conn": "type_antitype", "pardes": "remez", "tg": ["passover", "sacrifice", "jesus-christ"]},
            {"step": 3, "verse": "isa.53.1-12", "title": "The Suffering Servant", "explanation": "Isaiah prophesies the Servant who is 'led as a lamb to the slaughter.' He bears our griefs, is wounded for our transgressions, and makes his soul an offering for sin.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["jesus-christ-prophecies-about", "atonement", "sacrifice"]},
            {"step": 4, "verse": "john.1.29-36", "title": "Behold the Lamb of God", "explanation": "John the Baptist identifies Jesus as 'the Lamb of God who takes away the sin of the world.' This explicitly connects Jesus to the entire sacrificial system.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["jesus-christ", "john-the-baptist", "atonement"]},
            {"step": 5, "verse": "1cor.5.7-8", "title": "Christ Our Passover", "explanation": "Paul declares 'Christ our Passover is sacrificed for us.' The feast of unleavened bread takes on new meaning — we are to live in sincerity and truth.", "conn": "interpretive", "pardes": "drash", "tg": ["jesus-christ", "passover", "atonement"]},
            {"step": 6, "verse": "1pet.1.18-21", "title": "Redeemed by His Blood", "explanation": "We are redeemed not with corruptible things but with the precious blood of Christ, as of a lamb without blemish and without spot. This connects the Passover type to our redemption.", "conn": "interpretive", "pardes": "drash", "tg": ["redemption", "atonement", "jesus-christ"]},
            {"step": 7, "verse": "rev.5.1-14", "title": "Worthy is the Lamb", "explanation": "In heavenly worship, the Lamb appears as though it had been slain. All creation worships the Lamb who was slain and has redeemed us by His blood. The Lamb is central.", "conn": "symbolic", "pardes": "sod", "tg": ["jesus-christ", "worship", "book-of-life"]},
        ]
    },
    {
        "id": "angel_of_the_lord",
        "title": "The Angel of the Lord",
        "description": "Track the mysterious Angel of the Lord (Malach YHWH) through the Old Testament — a divine messenger who speaks as God and receives worship.",
        "theme": "angel",
        "icon": "👼",
        "seed_verse": "gen.16.7",
        "tg_topic_ids": ["angels", "jesus-christ-appearances-of"],
        "steps": [
            {"step": 1, "verse": "gen.16.7-14", "title": "Hagar in the Wilderness", "explanation": "The Angel of the Lord finds Hagar fleeing from Sarah. He speaks with divine authority ('I will multiply your seed') and she names the place 'Thou God seest me.'", "conn": "direct_quotation", "pardes": "pshat", "tg": ["angels", "god-body-of-heavenly-father"]},
            {"step": 2, "verse": "gen.22.11-18", "title": "Abraham and Isaac", "explanation": "The Angel of the Lord calls from heaven to stop Abraham from sacrificing Isaac. He speaks as God: 'now I know that you fear God.' This is a theophany.", "conn": "direct_quotation", "pardes": "remez", "tg": ["angels", "jesus-christ-appearances-of", "obedience"]},
            {"step": 3, "verse": "exo.3.1-15", "title": "The Burning Bush", "explanation": "The Angel of the Lord appears in the burning bush. He identifies Himself as 'I AM' — the God of Abraham, Isaac, and Jacob. This is one of the clearest pre-mortal Christophanies.", "conn": "direct_quotation", "pardes": "remez", "tg": ["jesus-christ-appearances-of", "burning-bush"]},
            {"step": 4, "verse": "josh.5.13-15", "title": "Captain of the Lord's Host", "explanation": "Joshua meets a man with a drawn sword who identifies Himself as 'Captain of the Lord's host.' Joshua worships Him, and He tells Joshua to remove his shoes — holy ground.", "conn": "direct_quotation", "pardes": "remez", "tg": ["jesus-christ-appearances-of", "god-presence-of"]},
            {"step": 5, "verse": "judg.6.11-24", "title": "Gideon's Call", "explanation": "The Angel of the Lord sits under an oak at Ophrah and calls Gideon to deliver Israel. Gideon prepares a sacrifice, which the Angel consumes with fire. Gideon fears for his life, having seen God.", "conn": "direct_quotation", "pardes": "remez", "tg": ["angels", "jesus-christ-appearances-of"]},
            {"step": 6, "verse": "judg.13.3-23", "title": "Samson's Parents", "explanation": "The Angel of the Lord appears to Manoah and his wife, foretelling Samson's birth. Manoah asks His name; He says it is 'wonderful.' He ascends in the altar flame. Manoah fears they will die for seeing God.", "conn": "direct_quotation", "pardes": "remez", "tg": ["angels", "jesus-christ-appearances-of", "samson"]},
        ]
    },
    {
        "id": "exodus",
        "title": "The Exodus Motif",
        "description": "The exodus from Egypt is the defining salvation event of the Old Testament, echoed by prophets and fulfilled in Christ's redemption.",
        "theme": "exodus",
        "icon": "🌊",
        "seed_verse": "exo.12.1",
        "tg_topic_ids": ["exodus", "deliverance", "redemption"],
        "steps": [
            {"step": 1, "verse": "exo.12.1-28", "title": "The Passover", "explanation": "The exodus begins with the Passover — the blood of the lamb saves Israel from the destroyer. This becomes the foundation of Israel's identity as a redeemed people.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["passover", "exodus", "sacrifice"]},
            {"step": 2, "verse": "exo.14.1-31", "title": "Crossing the Red Sea", "explanation": "Israel passes through the Red Sea on dry ground. The waters are a wall on their right and left. This is Israel's baptism into Moses and their definitive salvation event.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["exodus", "deliverance", "miracle"]},
            {"step": 3, "verse": "exo.15.1-21", "title": "The Song of Moses", "explanation": "Moses and Israel sing the first hymn of redemption: 'The Lord is my strength and song, and He has become my salvation.' This is the template for all later redemption songs.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["exodus", "praise", "god-power-of"]},
            {"step": 4, "verse": "isa.40.3-5", "title": "A New Exodus", "explanation": "Isaiah prophesies a new exodus — prepare the way of the Lord. The wilderness will blossom and God will lead His people home again. This reimagines exodus as future hope.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["exodus", "isaiah", "redemption"]},
            {"step": 5, "verse": "isa.43.14-21", "title": "Do Not Remember the Former Things", "explanation": "God declares He will do a new thing — rivers in the desert. The former exodus is so eclipsed by the new that it should not even be remembered.", "conn": "allusion", "pardes": "remez", "tg": ["exodus", "redemption", "isaiah"]},
            {"step": 6, "verse": "luke.9.28-36", "title": "The Transfiguration", "explanation": "Moses and Elijah appear with Jesus on the mount. They speak of 'His decease which He should accomplish at Jerusalem' — literally His 'exodus.' The new exodus is about to happen.", "conn": "same_lemma", "pardes": "drash", "tg": ["jesus-christ", "transfiguration", "exodus"]},
            {"step": 7, "verse": "1cor.10.1-13", "title": "Lessons from the Exodus", "explanation": "Paul interprets the exodus typologically: the sea crossing as baptism, the manna as spiritual food, the rock as Christ. These things happened as examples for us.", "conn": "interpretive", "pardes": "drash", "tg": ["exodus", "baptism", "sacrament"]},
            {"step": 8, "verse": "rev.15.1-4", "title": "The Song of Moses and the Lamb", "explanation": "The redeemed sing the song of Moses and the Lamb — the exodus song reinterpreted through Christ's redemption. The two songs merge into one: salvation belongs to God.", "conn": "type_antitype", "pardes": "sod", "tg": ["exodus", "redemption", "worship"]},
        ]
    },
    {
        "id": "atonement",
        "title": "Atonement",
        "description": "Follow the atonement theme from the Day of Atonement through the Suffering Servant, Christ's sacrifice, and its application in our lives.",
        "theme": "atonement",
        "icon": "🕊️",
        "seed_verse": "lev.17.11",
        "tg_topic_ids": ["atonement", "sacrifice", "jesus-christ"],
        "steps": [
            {"step": 1, "verse": "lev.16.1-34", "title": "The Day of Atonement", "explanation": "The High Priest enters the Holy of Holies on Yom Kippur to make atonement for Israel. Two goats: one sacrificed, one sent into the wilderness (scapegoat). This is the most sacred ritual.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["atonement", "sacrifice", "priesthood-aaronic"]},
            {"step": 2, "verse": "lev.17.11", "title": "Blood Makes Atonement", "explanation": "'The life of the flesh is in the blood, and I have given it to you upon the altar to make an atonement for your souls.' This is the theological basis of blood atonement.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["atonement", "blood", "sacrifice"]},
            {"step": 3, "verse": "isa.53.1-12", "title": "Stricken for Our Transgressions", "explanation": "The Suffering Servant is wounded for our transgressions, bruised for our iniquities. The Lord lays on Him the iniquity of us all. This is the atonement prophesied.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["atonement", "jesus-christ-prophecies-about", "sacrifice"]},
            {"step": 4, "verse": "rom.3.21-26", "title": "Justified by His Grace", "explanation": "Paul explains that we are justified freely by God's grace through the redemption that is in Christ Jesus. God set forth Christ as a propitiation by His blood.", "conn": "interpretive", "pardes": "drash", "tg": ["atonement", "grace", "justification"]},
            {"step": 5, "verse": "rom.5.6-11", "title": "While We Were Yet Sinners", "explanation": "Christ died for the ungodly. While we were enemies, we were reconciled to God by the death of His Son. This is the depth of God's love.", "conn": "interpretive", "pardes": "drash", "tg": ["atonement", "jesus-christ", "grace"]},
            {"step": 6, "verse": "heb.9.1-28", "title": "Christ Enters the Heavenly Sanctuary", "explanation": "Christ, the High Priest, enters the greater and more perfect tabernacle with His own blood. He obtains eternal redemption. The old sacrifices foreshadowed His single, perfect sacrifice.", "conn": "interpretive", "pardes": "sod", "tg": ["atonement", "jesus-christ", "priesthood"]},
            {"step": 7, "verse": "1john.1.7-2.2", "title": "Cleansed by His Blood", "explanation": "The blood of Jesus Christ cleanses us from all sin. He is the propitiation for our sins — and not for ours only but for the whole world. This is the application of atonement.", "conn": "direct_quotation", "pardes": "drash", "tg": ["atonement", "forgiveness", "jesus-christ"]},
        ]
    },
]

# Additional hub notes (abbreviated for brevity)
HUB_NOTES_SHORT = [
    {
        "id": "wisdom",
        "title": "Wisdom",
        "description": "The wisdom tradition in scripture — from Proverbs to Job to Ecclesiastes to Christ as the Wisdom of God.",
        "theme": "wisdom",
        "icon": "📜",
        "seed_verse": "prov.1.7",
        "tg_topic_ids": ["wisdom", "understanding", "knowledge"],
        "steps": [
            {"step": 1, "verse": "prov.1.1-7", "title": "Fear of the Lord", "explanation": "'The fear of the Lord is the beginning of knowledge.' Proverbs establishes wisdom as the practical skill of living rightly before God.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["wisdom", "knowledge"]},
            {"step": 2, "verse": "prov.8.1-36", "title": "Wisdom Personified", "explanation": "Wisdom personified as a woman who was with God before creation. She rejoiced in His inhabited world. This prefigures Christ as the Logos.", "conn": "same_lemma", "pardes": "remez", "tg": ["wisdom", "jesus-christ"]},
            {"step": 3, "verse": "eccl.1.1-18", "title": "Vanity of Vanities", "explanation": "All is vanity under the sun. Ecclesiastes tests the limits of human wisdom, concluding that fearing God and keeping His commandments is the whole duty of man.", "conn": "parallel_synonymous", "pardes": "pshat", "tg": ["wisdom", "vanity"]},
            {"step": 4, "verse": "job.28.1-28", "title": "Where is Wisdom?", "explanation": "Job asks where wisdom can be found. It cannot be bought with gold. The answer: 'Behold, the fear of the Lord, that is wisdom; and to depart from evil is understanding.'", "conn": "parallel_synonymous", "pardes": "remez", "tg": ["wisdom", "understanding", "fear-of-god"]},
            {"step": 5, "verse": "1cor.1.18-31", "title": "Christ the Wisdom of God", "explanation": "Paul declares that Christ is the power of God and the wisdom of God. The foolishness of God is wiser than men. True wisdom is found in the cross.", "conn": "interpretive", "pardes": "drash", "tg": ["jesus-christ", "wisdom", "understanding"]},
            {"step": 6, "verse": "james.3.13-18", "title": "Wisdom from Above", "explanation": "James distinguishes earthly wisdom from heavenly wisdom. The wisdom from above is pure, peaceable, gentle, easy to be entreated, full of mercy and good fruits.", "conn": "parallel_antithetic", "pardes": "drash", "tg": ["wisdom", "knowledge", "understanding"]},
        ]
    },
    {
        "id": "son_of_man",
        "title": "The Son of Man",
        "description": "The Son of Man — from Daniel's vision of the Ancient of Days, through Jesus' self-identification, to the glorified Son of Man in Revelation.",
        "theme": "jesus_christ",
        "icon": "🌟",
        "seed_verse": "dan.7.13",
        "tg_topic_ids": ["jesus-christ-prophecies-about", "son-of-man"],
        "steps": [
            {"step": 1, "verse": "dan.7.1-28", "title": "The Ancient of Days", "explanation": "Daniel sees 'one like the Son of Man' coming with the clouds to the Ancient of Days. He receives dominion, glory, and an everlasting kingdom.", "conn": "direct_quotation", "pardes": "remez", "tg": ["jesus-christ-prophecies-about", "son-of-man"]},
            {"step": 2, "verse": "matt.9.1-8", "title": "Authority to Forgive", "explanation": "Jesus heals the paralytic to demonstrate that the Son of Man has authority on earth to forgive sins. This is His first public claim to divine authority.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["jesus-christ", "son-of-man", "forgiveness"]},
            {"step": 3, "verse": "matt.17.22-23", "title": "The Son of Man Will Suffer", "explanation": "Jesus foretells that the Son of Man will be betrayed, killed, and raised on the third day. This transforms the expected political Son of Man into a suffering one.", "conn": "direct_quotation", "pardes": "remez", "tg": ["jesus-christ", "atonement"]},
            {"step": 4, "verse": "acts.7.54-60", "title": "Stephen's Vision", "explanation": "Stephen, full of the Holy Ghost, sees the heavens opened and the Son of Man standing on the right hand of God. This confirms Jesus' identity as the Danielic Son of Man.", "conn": "direct_quotation", "pardes": "drash", "tg": ["jesus-christ", "son-of-man", "martyrdom"]},
            {"step": 5, "verse": "rev.1.9-20", "title": "The Glorified Son of Man", "explanation": "John sees the Son of Man in glory — eyes as a flame of fire, feet like fine brass, voice as many waters. He holds the seven stars and walks among the golden candlesticks.", "conn": "prophetic_fulfillment", "pardes": "sod", "tg": ["jesus-christ", "revelation", "son-of-man"]},
        ]
    },
    {
        "id": "restoration",
        "title": "Restoration",
        "description": "The restoration theme — from the Deuteronomic promise of return, through the prophets, the apostolic promise of restitution, to the Restoration of all things.",
        "theme": "restoration",
        "icon": "🔄",
        "seed_verse": "deut.30.1",
        "tg_topic_ids": ["restoration-of-the-gospel", "dispensations", "israel-gathering-of"],
        "steps": [
            {"step": 1, "verse": "deut.30.1-10", "title": "The Promise of Return", "explanation": "Moses promises that when Israel repents, God will gather them from all nations and circumcise their hearts. This is the foundational restoration promise.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["israel-gathering-of", "repentance", "restoration-of-the-gospel"]},
            {"step": 2, "verse": "jer.16.14-21", "title": "The Greater Exodus", "explanation": "Jeremiah prophesies that the return from exile will eclipse the exodus itself. People will no longer say 'the Lord brought us out of Egypt' but 'the Lord brought us from the north country.'", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["israel-gathering-of", "restoration-of-the-gospel", "exodus"]},
            {"step": 3, "verse": "ezek.37.1-28", "title": "Valley of Dry Bones", "explanation": "Ezekiel's vision of dry bones coming to life symbolizes Israel's restoration. The two sticks becoming one represents the reunification of Ephraim and Judah.", "conn": "symbolic", "pardes": "remez", "tg": ["israel-gathering-of", "restoration-of-the-gospel", "ezekiel"]},
            {"step": 4, "verse": "acts.3.19-21", "title": "Times of Refreshing", "explanation": "Peter promises 'times of refreshing' from the presence of the Lord and the 'restitution of all things' spoken by the prophets since the world began.", "conn": "direct_quotation", "pardes": "drash", "tg": ["restoration-of-the-gospel", "jesus-christ", "repentance"]},
            {"step": 5, "verse": "dc.27.5-18", "title": "The Dispensation of the Fulness of Times", "explanation": "The Lord reveals that all things will be gathered together in Christ in the dispensation of the fulness of times. This is the climax of restoration.", "conn": "interpretive", "pardes": "sod", "tg": ["dispensations", "restoration-of-the-gospel", "fulness-of-times"]},
        ]
    },
    {
        "id": "garden_to_city",
        "title": "From Garden to City",
        "description": "The biblical narrative from the Garden of Eden through the wilderness to the New Jerusalem — God's presence with His people from beginning to end.",
        "theme": "creation",
        "icon": "🌳",
        "seed_verse": "gen.2.8",
        "tg_topic_ids": ["creation", "earth-purpose-of", "celestial-glory"],
        "steps": [
            {"step": 1, "verse": "gen.2.1-25", "title": "The Garden of Eden", "explanation": "God plants a garden in Eden and places man there. The garden is the first sanctuary — where God walks with man in the cool of the day.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["creation", "temple"]},
            {"step": 2, "verse": "gen.3.1-24", "title": "The Fall", "explanation": "Adam and Eve eat the forbidden fruit and are driven from the garden. Cherubim guard the way to the tree of life. The presence of God is no longer accessible.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["fall-of-man", "sin"]},
            {"step": 3, "verse": "isa.65.17-25", "title": "New Heavens and New Earth", "explanation": "Isaiah prophesies new heavens and a new earth where the former things are not remembered. The wolf and lamb feed together, and God's people enjoy the work of their hands.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["creation", "paradise", "millennium"]},
            {"step": 4, "verse": "rev.21.1-22.5", "title": "The New Jerusalem", "explanation": "John sees the holy city, New Jerusalem, coming down from God. The tree of life is there, and the throne of God and the Lamb are in the city. The garden-city has returned.", "conn": "type_antitype", "pardes": "sod", "tg": ["jerusalem", "celestial-glory", "temple"]},
        ]
    },
    {
        "id": "zion",
        "title": "Zion",
        "description": "The Zion theme from Enoch's city, through the Psalms, to the New Jerusalem and the modern establishment of Zion.",
        "theme": "zion",
        "icon": "🏔️",
        "seed_verse": "moses.7.1",
        "tg_topic_ids": ["zion", "city-of-zion", "jerusalem"],
        "steps": [
            {"step": 1, "verse": "moses.7.1-69", "title": "Enoch's Zion", "explanation": "Enoch builds a city called Zion. The people are of one heart and one mind, dwelling in righteousness. Zion is taken up to heaven.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["zion", "city-of-zion", "enoch"]},
            {"step": 2, "verse": "psa.48.1-14", "title": "The City of God", "explanation": "Mount Zion is beautiful for situation, the joy of the whole earth. God is known in her palaces as a refuge.", "conn": "parallel_synonymous", "pardes": "remez", "tg": ["zion", "jerusalem", "temple"]},
            {"step": 3, "verse": "isa.2.1-5", "title": "Zion as the Mountain of the Lord", "explanation": "In the last days, the mountain of the Lord's house shall be established, and all nations shall flow unto it. Out of Zion shall go forth the law.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["zion", "temple", "millennium"]},
            {"step": 4, "verse": "heb.12.18-29", "title": "Mount Zion, the Heavenly Jerusalem", "explanation": "We have come to Mount Zion, the city of the living God, the heavenly Jerusalem. This is the spiritual Zion accessible through Christ.", "conn": "interpretive", "pardes": "drash", "tg": ["zion", "jerusalem", "jesus-christ"]},
            {"step": 5, "verse": "rev.14.1-5", "title": "The Lamb on Mount Zion", "explanation": "John sees the Lamb standing on Mount Zion with 144,000 who have His name written on their foreheads. They sing a new song before the throne.", "conn": "symbolic", "pardes": "sod", "tg": ["zion", "jesus-christ", "millennium"]},
            {"step": 6, "verse": "dc.97.1-28", "title": "Modern Zion", "explanation": "The Lord reveals the law of Zion in modern times. Zion is the pure in heart. The city of Zion is to be built as a place of gathering and refuge.", "conn": "interpretive", "pardes": "sod", "tg": ["zion", "city-of-zion", "gathering"]},
        ]
    },
    {
        "id": "priesthood",
        "title": "Priesthood",
        "description": "The priesthood from Melchizedek through Aaron and the Levites to Christ's Melchizedek Priesthood and its restoration.",
        "theme": "priesthood",
        "icon": "✝️",
        "seed_verse": "gen.14.18",
        "tg_topic_ids": ["priesthood", "melchizedek-priesthood", "aaronic-priesthood"],
        "steps": [
            {"step": 1, "verse": "gen.14.18-24", "title": "Melchizedek", "explanation": "Melchizedek, king of Salem and priest of the Most High God, brings bread and wine and blesses Abraham. Abraham pays tithes to him.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["melchizedek-priesthood", "tithing"]},
            {"step": 2, "verse": "exo.28.1-43", "title": "The Aaronic Priesthood", "explanation": "Aaron and his sons are consecrated as priests. Their garments are described in detail — the breastplate, ephod, robe, and mitre.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["aaronic-priesthood", "priesthood"]},
            {"step": 3, "verse": "psa.110.1-7", "title": "Priest After the Order of Melchizedek", "explanation": "David prophesies a priest after the order of Melchizedek — an eternal priesthood. This is the most quoted Old Testament verse in the New Testament.", "conn": "prophetic_fulfillment", "pardes": "remez", "tg": ["melchizedek-priesthood", "jesus-christ"]},
            {"step": 4, "verse": "heb.5.1-10", "title": "Christ as High Priest", "explanation": "Christ is called of God as High Priest after the order of Melchizedek. He learned obedience by the things He suffered and became the author of eternal salvation.", "conn": "interpretive", "pardes": "drash", "tg": ["melchizedek-priesthood", "jesus-christ", "atonement"]},
            {"step": 5, "verse": "1pet.2.1-10", "title": "A Royal Priesthood", "explanation": "All believers are a chosen generation, a royal priesthood, a holy nation. The priesthood extends to all who come to Christ.", "conn": "interpretive", "pardes": "drash", "tg": ["priesthood", "jesus-christ", "church-of-god"]},
        ]
    },
    {
        "id": "faith_unto_salvation",
        "title": "Faith unto Salvation",
        "description": "The thread of saving faith from Abraham's example through the prophets to Christ and its application in our lives.",
        "theme": "faith",
        "icon": "🔥",
        "seed_verse": "gen.15.6",
        "tg_topic_ids": ["faith", "hope", "salvation"],
        "steps": [
            {"step": 1, "verse": "gen.15.1-6", "title": "Abraham Believed God", "explanation": "Abraham believed in the Lord, and it was counted to him for righteousness. This is the first explicit statement of justification by faith.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["faith", "abraham", "righteousness"]},
            {"step": 2, "verse": "hab.2.1-4", "title": "The Just Shall Live by Faith", "explanation": "Habakkuk learns that the just shall live by faith. This becomes the rallying cry of the Reformation and the key to understanding salvation.", "conn": "direct_quotation", "pardes": "remez", "tg": ["faith", "salvation"]},
            {"step": 3, "verse": "heb.11.1-40", "title": "The Hall of Faith", "explanation": "Hebrews 11 defines faith as the substance of things hoped for, the evidence of things not seen. It catalogs the heroes of faith from Abel to the prophets.", "conn": "interpretive", "pardes": "drash", "tg": ["faith", "hope", "salvation"]},
            {"step": 4, "verse": "eph.2.1-10", "title": "Saved by Grace Through Faith", "explanation": "Paul's great summary: by grace are you saved through faith — not of works, lest any man should boast. We are created in Christ Jesus unto good works.", "conn": "interpretive", "pardes": "drash", "tg": ["faith", "grace", "salvation"]},
            {"step": 5, "verse": "james.2.14-26", "title": "Faith Without Works is Dead", "explanation": "James balances Paul: faith without works is dead. Abraham was justified by works when he offered Isaac. Faith and works are two sides of one coin.", "conn": "parallel_antithetic", "pardes": "drash", "tg": ["faith", "works", "justification"]},
        ]
    },
    {
        "id": "dispensations",
        "title": "Dispensations",
        "description": "The dispensations of the gospel from Adam through Christ to the fulness of times — God's progressive revelation to His children.",
        "theme": "dispensations",
        "icon": "⏳",
        "seed_verse": "dc.27.5",
        "tg_topic_ids": ["dispensations", "restoration-of-the-gospel", "fulness-of-times"],
        "steps": [
            {"step": 1, "verse": "dc.29.42-45", "title": "The Dispensation of Adam", "explanation": "Adam was given the priesthood and the gospel. He was the first patriarch to receive the promise of redemption.", "conn": "direct_quotation", "pardes": "pshat", "tg": ["adam", "dispensations"]},
            {"step": 2, "verse": "moses.7.1-69", "title": "The Dispensation of Enoch", "explanation": "Enoch preached righteousness and built Zion. His people were translated and taken to heaven. This is a high point in the dispensational timeline.", "conn": "structural", "pardes": "pshat", "tg": ["enoch", "zion", "dispensations"]},
            {"step": 3, "verse": "gen.9.1-17", "title": "The Dispensation of Noah", "explanation": "Noah, a preacher of righteousness, is given the covenant after the flood. This begins a new dispensation with God's promise to all flesh.", "conn": "structural", "pardes": "pshat", "tg": ["noah", "covenant", "dispensations"]},
            {"step": 4, "verse": "dc.27.5-18", "title": "The Dispensation of the Fulness of Times", "explanation": "The Lord reveals that all things will be gathered together in Christ in the dispensation of the fulness of times — the summing up of all previous dispensations.", "conn": "interpretive", "pardes": "sod", "tg": ["dispensations", "fulness-of-times", "restoration-of-the-gospel"]},
        ]
    },
]


def main():
    conn = sqlite3.connect(str(DB_PATH))

    # Create tables
    for stmt in SCHEMA.split(";"):
        if stmt.strip():
            conn.execute(stmt)

    # Skip if already seeded
    existing = conn.execute("SELECT COUNT(*) FROM hub_notes").fetchone()[0]
    if existing > 0:
        print(f"Hub notes already seeded ({existing} notes). Use --force to re-seed.")
        conn.close()
        return

    all_notes = HUB_NOTES + HUB_NOTES_SHORT
    total_steps = 0

    for hub in all_notes:
        # Insert hub note
        conn.execute("""
            INSERT INTO hub_notes (id, title, description, theme, icon, seed_verse, tg_topic_ids)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            hub["id"], hub["title"], hub["description"], hub["theme"],
            hub.get("icon", ""), hub.get("seed_verse", ""),
            json.dumps(hub.get("tg_topic_ids", []))
        ))

        # Insert steps
        for step in hub["steps"]:
            conn.execute("""
                INSERT INTO hub_note_steps (hub_id, step_number, verse_id, title, explanation, connection_type, pa_r_de_s_level, tg_topic_ids)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hub["id"], step["step"], step["verse"], step["title"],
                step["explanation"], step.get("conn", ""),
                step.get("pardes", "pshat"),
                json.dumps(step.get("tg", []))
            ))
            total_steps += 1

        # Insert hub-topic links
        for tid in hub.get("tg_topic_ids", []):
            conn.execute("""
                INSERT OR IGNORE INTO hub_topic_links (hub_id, topic_id, relevance_weight)
                VALUES (?, ?, 0.7)
            """, (hub["id"], tid))

    conn.commit()
    conn.close()

    print(f"✅ Seeded {len(all_notes)} hub notes with {total_steps} total steps")
    print(f"   Notes: {', '.join(h['id'] for h in all_notes)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed hub notes")
    parser.add_argument("--force", action="store_true", help="Re-seed even if already seeded")
    args = parser.parse_args()

    if args.force:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("DROP TABLE IF EXISTS hub_notes")
        conn.execute("DROP TABLE IF EXISTS hub_note_steps")
        conn.execute("DROP TABLE IF EXISTS hub_note_progress")
        conn.execute("DROP TABLE IF EXISTS hub_topic_links")
        conn.commit()
        conn.close()

    main()
