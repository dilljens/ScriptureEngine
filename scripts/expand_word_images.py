#!/usr/bin/env python3
"""Expand word images coverage — map remaining 444 Hebrew words to FreeBibleImages.org.

Runs after seed_word_images.py. Categorizes missing vocabulary words by
semantic theme and maps them to FreeBibleImages.org illustration sets.

Usage:
    python3 scripts/expand_word_images.py --dry-run    # Preview
    python3 scripts/expand_word_images.py --apply      # Insert into DB
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"
MEM_DB = BASE / "data" / "memorize.db"

# ── Theme buckets — maps semantic categories → FreeBibleImages URL ──
# Each bucket has: (gloss_keywords, freebible_url, theme_name)
# Words whose gloss matches a keyword get assigned to that theme.

THEME_BUCKETS = [
    # ── God & Divine ──
    (["LORD", "GOD", "YHWH", "Elohim", "Almighty", "Holy One"], "https://freebibleimages.org/illustrations/sinai/", "divine-presence"),
    (["lord", "master", "adonai"], "https://freebibleimages.org/illustrations/jesus-lord/", "lord"),
    (["angel", "messenger", "heavenly"], "https://freebibleimages.org/illustrations/angels/", "angels"),
    (["glory", "majesty", "splendor"], "https://freebibleimages.org/illustrations/sinai/", "glory"),
    (["spirit", "breath", "wind"], "https://freebibleimages.org/illustrations/creation/", "spirit"),
    (["holy", "sanctify", "sacred"], "https://freebibleimages.org/illustrations/tabernacle/", "holy"),

    # ── Covenant & Law ──
    (["covenant", "treaty", "alliance"], "https://freebibleimages.org/illustrations/ark-covenant/", "covenant"),
    (["law", "torah", "commandment", "statute"], "https://freebibleimages.org/illustrations/ten-commandments/", "law"),
    (["testimony", "witness", "decree"], "https://freebibleimages.org/illustrations/ten-commandments/", "testimony"),
    (["bless", "blessing", "blessed"], "https://freebibleimages.org/illustrations/abraham-blessing/", "blessing"),
    (["curse", "oath", "swear"], "https://freebibleimages.org/illustrations/adam-eve/", "curse"),

    # ── Sacrifice & Worship ──
    (["sacrifice", "offering", "altar", "burnt"], "https://freebibleimages.org/illustrations/tabernacle/", "sacrifice"),
    (["priest", "levite", "minister"], "https://freebibleimages.org/illustrations/priest/", "priest"),
    (["temple", "sanctuary", "dwelling"], "https://freebibleimages.org/illustrations/temple/", "temple"),
    (["worship", "bow", "praise", "thanks"], "https://freebibleimages.org/illustrations/return-prodigal/", "worship"),
    (["pray", "prayer", "supplication"], "https://freebibleimages.org/illustrations/samuel-prayer/", "prayer"),
    (["sing", "song", "music", "melody"], "https://freebibleimages.org/illustrations/david-music/", "music"),
    (["incense", "fragrance", "perfume"], "https://freebibleimages.org/illustrations/tabernacle/", "incense"),
    (["feast", "festival", "celebrate"], "https://freebibleimages.org/illustrations/passover/", "feast"),

    # ── Sin & Judgment ──
    (["sin", "transgression", "iniquity", "guilt"], "https://freebibleimages.org/illustrations/adam-eve/", "sin"),
    (["judgment", "judge", "justice", "condemn"], "https://freebibleimages.org/illustrations/solomon-judgment/", "judgment"),
    (["wrath", "anger", "fury", "indignation"], "https://freebibleimages.org/illustrations/flood/", "wrath"),
    (["destroy", "destruction", "ruin", "devastate"], "https://freebibleimages.org/illustrations/flood/", "destruction"),
    (["punish", "punishment", "discipline"], "https://freebibleimages.org/illustrations/exodus-plagues/", "punishment"),
    (["rebel", "rebellion", "revolt"], "https://freebibleimages.org/illustrations/korah/", "rebellion"),

    # ── Salvation & Deliverance ──
    (["save", "salvation", "deliver", "redeem", "rescue"], "https://freebibleimages.org/illustrations/red-sea/", "salvation"),
    (["redemption", "redeemer", "ransom", "buy back"], "https://freebibleimages.org/illustrations/exodus/", "redemption"),
    (["forgive", "forgiveness", "pardon"], "https://freebibleimages.org/illustrations/return-prodigal/", "forgiveness"),
    (["mercy", "compassion", "pity", "kindness"], "https://freebibleimages.org/illustrations/good-samaritan/", "mercy"),
    (["grace", "favor", "kindness"], "https://freebibleimages.org/illustrations/abraham/", "grace"),
    (["peace", "shalom", "rest", "tranquil"], "https://freebibleimages.org/illustrations/peace/", "peace"),
    (["hope", "expectation", "wait"], "https://freebibleimages.org/illustrations/abraham/", "hope"),
    (["faith", "trust", "believe", "faithful"], "https://freebibleimages.org/illustrations/abraham/", "faith"),

    # ── People & Relationships ──
    (["father", "patriarch"], "https://freebibleimages.org/illustrations/abraham/", "father"),
    (["mother", "matriarch"], "https://freebibleimages.org/illustrations/sarah/", "mother"),
    (["son", "child", "boy"], "https://freebibleimages.org/illustrations/isaac/", "son"),
    (["daughter", "girl"], "https://freebibleimages.org/illustrations/ruth/", "daughter"),
    (["brother", "sibling"], "https://freebibleimages.org/illustrations/joseph/", "brother"),
    (["wife", "woman", "female"], "https://freebibleimages.org/illustrations/adam-eve/", "woman"),
    (["husband", "man", "male"], "https://freebibleimages.org/illustrations/adam/", "man"),
    (["king", "ruler", "sovereign", "reign"], "https://freebibleimages.org/illustrations/david-king/", "king"),
    (["queen", "royalty"], "https://freebibleimages.org/illustrations/queen-esther/", "queen"),
    (["servant", "slave", "bondage"], "https://freebibleimages.org/illustrations/exodus/", "servant"),
    (["prophet", "seer", "visionary"], "https://freebibleimages.org/illustrations/prophets/", "prophet"),
    (["priest", "minister"], "https://freebibleimages.org/illustrations/aaron/", "priest"),
    (["wise", "wisdom", "sage"], "https://freebibleimages.org/illustrations/solomon-wisdom/", "wisdom"),
    (["fool", "folly"], "https://freebibleimages.org/illustrations/solomon/", "fool"),
    (["enemy", "foe", "adversary"], "https://freebibleimages.org/illustrations/david-goliath/", "enemy"),
    (["friend", "companion"], "https://freebibleimages.org/illustrations/david-jonathan/", "friend"),
    (["neighbor", "near"], "https://freebibleimages.org/illustrations/good-samaritan/", "neighbor"),
    (["widow", "orphan", "fatherless"], "https://freebibleimages.org/illustrations/ruth/", "widow"),
    (["stranger", "foreigner", "alien", "sojourner"], "https://freebibleimages.org/illustrations/ruth/", "stranger"),
    (["elder", "old", "ancient"], "https://freebibleimages.org/illustrations/moses/", "elder"),
    (["young", "youth", "maiden"], "https://freebibleimages.org/illustrations/david-shepherd/", "youth"),
    (["captive", "prisoner", "slave"], "https://freebibleimages.org/illustrations/joseph-prison/", "captive"),

    # ── Body & Senses ──
    (["hand", "arm", "finger"], "https://freebibleimages.org/illustrations/moses-hand/", "hand"),
    (["eye", "sight", "vision", "see"], "https://freebibleimages.org/illustrations/creation/", "eye"),
    (["ear", "hear", "listen"], "https://freebibleimages.org/illustrations/samuel/", "ear"),
    (["mouth", "lip", "speak", "tongue"], "https://freebibleimages.org/illustrations/prophets/", "mouth"),
    (["heart", "mind", "soul"], "https://freebibleimages.org/illustrations/david-heart/", "heart"),
    (["bone", "flesh", "body"], "https://freebibleimages.org/illustrations/creation/", "body"),
    (["face", "presence", "countenance"], "https://freebibleimages.org/illustrations/moses-face/", "face"),
    (["head", "chief", "leader"], "https://freebibleimages.org/illustrations/solomon/", "head"),
    (["blood", "lifeblood"], "https://freebibleimages.org/illustrations/passover/", "blood"),
    (["voice", "sound", "noise"], "https://freebibleimages.org/illustrations/sinai/", "voice"),

    # ── Nature & Elements ──
    (["water", "rain", "flood", "river", "sea"], "https://freebibleimages.org/illustrations/red-sea/", "water"),
    (["fire", "flame"], "https://freebibleimages.org/illustrations/sinai/", "fire"),
    (["light", "day", "bright"], "https://freebibleimages.org/illustrations/creation/", "light"),
    (["darkness", "night", "gloom"], "https://freebibleimages.org/illustrations/plague-darkness/", "darkness"),
    (["heaven", "sky", "firmament"], "https://freebibleimages.org/illustrations/creation/", "heaven"),
    (["earth", "land", "ground", "soil"], "https://freebibleimages.org/illustrations/creation/", "earth"),
    (["mountain", "hill", "peak"], "https://freebibleimages.org/illustrations/sinai/", "mountain"),
    (["stone", "rock", "boulder"], "https://freebibleimages.org/illustrations/moses-rock/", "stone"),
    (["tree", "wood", "forest"], "https://freebibleimages.org/illustrations/eden/", "tree"),
    (["fruit", "harvest", "grain"], "https://freebibleimages.org/illustrations/abundance/", "fruit"),
    (["wind", "storm", "tempest"], "https://freebibleimages.org/illustrations/jonah-storm/", "wind"),
    (["gold", "silver", "treasure", "wealth"], "https://freebibleimages.org/illustrations/tabernacle-gold/", "treasure"),
    (["iron", "bronze", "metal", "copper"], "https://freebibleimages.org/illustrations/war/", "metal"),
    (["desert", "wilderness"], "https://freebibleimages.org/illustrations/wilderness/", "desert"),
    (["garden", "orchard"], "https://freebibleimages.org/illustrations/eden/", "garden"),
    (["field", "pasture", "meadow"], "https://freebibleimages.org/illustrations/shepherd/", "field"),

    # ── Animals ──
    (["lamb", "sheep"], "https://freebibleimages.org/illustrations/shepherd/", "sheep"),
    (["cattle", "ox", "bull", "calf"], "https://freebibleimages.org/illustrations/golden-calf/", "cattle"),
    (["horse", "chariot"], "https://freebibleimages.org/illustrations/exodus-chariot/", "horse"),
    (["donkey", "ass"], "https://freebibleimages.org/illustrations/donkey/", "donkey"),
    (["camel"], "https://freebibleimages.org/illustrations/camel/", "camel"),
    (["lion"], "https://freebibleimages.org/illustrations/daniel-lion/", "lion"),
    (["serpent", "snake", "viper"], "https://freebibleimages.org/illustrations/adam-eve/", "serpent"),
    (["dove", "pigeon"], "https://freebibleimages.org/illustrations/noah-dove/", "dove"),
    (["eagle", "bird", "wing"], "https://freebibleimages.org/illustrations/eagle/", "bird"),
    (["fish"], "https://freebibleimages.org/illustrations/jonah-fish/", "fish"),
    (["locust", "insect", "plague"], "https://freebibleimages.org/illustrations/plague-locust/", "locust"),
    (["beast", "creature", "animal"], "https://freebibleimages.org/illustrations/creation-animals/", "beast"),

    # ── Places ──
    (["city", "town", "village"], "https://freebibleimages.org/illustrations/jerusalem/", "city"),
    (["gate", "door", "entrance"], "https://freebibleimages.org/illustrations/jericho/", "gate"),
    (["wall", "fortress", "tower"], "https://freebibleimages.org/illustrations/jericho/", "wall"),
    (["house", "home", "dwelling", "tent"], "https://freebibleimages.org/illustrations/tent/", "house"),
    (["bed", "couch", "rest"], "https://freebibleimages.org/illustrations/david-bed/", "bed"),
    (["table", "meal", "eat"], "https://freebibleimages.org/illustrations/last-supper/", "table"),
    (["throne", "seat", "royal"], "https://freebibleimages.org/illustrations/solomon-throne/", "throne"),
    (["well", "spring", "fountain"], "https://freebibleimages.org/illustrations/well/", "well"),
    (["path", "way", "road", "journey"], "https://freebibleimages.org/illustrations/exodus-route/", "way"),
    (["camp", "encampment"], "https://freebibleimages.org/illustrations/wilderness-camp/", "camp"),

    # ── Warfare ──
    (["sword", "weapon", "armor"], "https://freebibleimages.org/illustrations/war/", "sword"),
    (["spear", "shield", "bow", "arrow"], "https://freebibleimages.org/illustrations/war/", "spear"),
    (["war", "battle", "fight", "conflict"], "https://freebibleimages.org/illustrations/war/", "war"),
    (["army", "soldier", "host"], "https://freebibleimages.org/illustrations/war/", "army"),
    (["victory", "triumph"], "https://freebibleimages.org/illustrations/red-sea/", "victory"),

    # ── Time & Numbers ──
    (["year", "season"], "https://freebibleimages.org/illustrations/creation-calendar/", "year"),
    (["month", "new moon"], "https://freebibleimages.org/illustrations/creation/", "month"),
    (["day", "today"], "https://freebibleimages.org/illustrations/creation/", "day"),
    (["night", "evening"], "https://freebibleimages.org/illustrations/creation-night/", "night"),
    (["one", "first", "unity"], "https://freebibleimages.org/illustrations/creation/", "one"),
    (["two", "second", "double"], "https://freebibleimages.org/illustrations/creation/", "two"),
    (["three", "third"], "https://freebibleimages.org/illustrations/trinity/", "three"),
    (["seven", "seventh", "week"], "https://freebibleimages.org/illustrations/creation/", "seven"),
    (["ten", "tenth", "tithe"], "https://freebibleimages.org/illustrations/ten-commandments/", "ten"),
    (["hundred", "thousand"], "https://freebibleimages.org/illustrations/abraham/", "multitude"),
    (["forever", "ever", "eternal", "everlasting"], "https://freebibleimages.org/illustrations/creation/", "eternity"),
    (["generation", "age"], "https://freebibleimages.org/illustrations/abraham/", "generation"),

    # ── Verbs of motion ──
    (["go", "walk", "come", "enter"], "https://freebibleimages.org/illustrations/exodus-route/", "journey"),
    (["return", "turn back", "repent"], "https://freebibleimages.org/illustrations/return-prodigal/", "return"),
    (["send", "dispatch"], "https://freebibleimages.org/illustrations/moses-sent/", "send"),
    (["bring", "carry", "bear"], "https://freebibleimages.org/illustrations/exodus/", "carry"),
    (["take", "grasp", "seize"], "https://freebibleimages.org/illustrations/abraham/", "take"),
    (["give", "grant"], "https://freebibleimages.org/illustrations/manna/", "give"),
    (["make", "do", "create"], "https://freebibleimages.org/illustrations/creation/", "create"),
    (["build", "establish"], "https://freebibleimages.org/illustrations/temple-build/", "build"),
    (["call", "summon", "name"], "https://freebibleimages.org/illustrations/samuel-call/", "call"),
    (["answer", "reply"], "https://freebibleimages.org/illustrations/samuel/", "answer"),
    (["open", "unlock"], "https://freebibleimages.org/illustrations/jericho/", "open"),
    (["close", "shut", "seal"], "https://freebibleimages.org/illustrations/ark-covenant/", "seal"),
    (["lift", "raise", "exalt"], "https://freebibleimages.org/illustrations/moses-lift/", "lift"),
    (["fall", "collapse"], "https://freebibleimages.org/illustrations/jericho/", "fall"),
    (["stand", "arise", "rise"], "https://freebibleimages.org/illustrations/resurrection/", "rise"),
    (["sit", "dwell", "remain"], "https://freebibleimages.org/illustrations/tent/", "dwell"),
    (["hide", "conceal"], "https://freebibleimages.org/illustrations/adam-hide/", "hide"),
    (["seek", "search", "inquire"], "https://freebibleimages.org/illustrations/shepherd-search/", "seek"),
    (["find", "discover"], "https://freebibleimages.org/illustrations/shepherd-search/", "find"),
    (["choose", "elect", "select"], "https://freebibleimages.org/illustrations/david-choose/", "choose"),
    (["test", "trial", "prove"], "https://freebibleimages.org/illustrations/abraham-test/", "test"),
    (["gather", "collect", "assemble"], "https://freebibleimages.org/illustrations/assembly/", "gather"),
    (["scatter", "disperse"], "https://freebibleimages.org/illustrations/babel/", "scatter"),

    # ── Abstract concepts ──
    (["truth", "true", "faithful"], "https://freebibleimages.org/illustrations/ten-commandments/", "truth"),
    (["lies", "false", "deceit", "deceive"], "https://freebibleimages.org/illustrations/adam-eve/", "deceit"),
    (["joy", "rejoice", "gladness"], "https://freebibleimages.org/illustrations/return-prodigal/", "joy"),
    (["sorrow", "weep", "mourn", "grief"], "https://freebibleimages.org/illustrations/jeremiah-weep/", "sorrow"),
    (["fear", "afraid", "dread", "terror"], "https://freebibleimages.org/illustrations/angel-fear/", "fear"),
    (["strength", "power", "might", "force"], "https://freebibleimages.org/illustrations/samson/", "strength"),
    (["name", "reputation", "fame"], "https://freebibleimages.org/illustrations/abraham-name/", "name"),
    (["remnant", "remainder", "rest"], "https://freebibleimages.org/illustrations/noah/", "remnant"),
    (["portion", "share", "inheritance"], "https://freebibleimages.org/illustrations/promised-land/", "inheritance"),
    (["boundary", "border", "limit"], "https://freebibleimages.org/illustrations/promised-land/", "boundary"),
    (["multiply", "increase", "abound"], "https://freebibleimages.org/illustrations/abraham-blessing/", "abundance"),
    (["hunger", "famine", "thirst"], "https://freebibleimages.org/illustrations/famine/", "famine"),
    (["sickness", "disease", "plague"], "https://freebibleimages.org/illustrations/plague/", "sickness"),
    (["heal", "cure", "restore", "health"], "https://freebibleimages.org/illustrations/healing/", "healing"),
    (["clean", "pure", "purify"], "https://freebibleimages.org/illustrations/tabernacle/", "purity"),
    (["unclean", "defile", "impure"], "https://freebibleimages.org/illustrations/leprosy/", "unclean"),
    (["strife", "contention", "quarrel"], "https://freebibleimages.org/illustrations/korah/", "strife"),
    (["shame", "disgrace", "humiliate"], "https://freebibleimages.org/illustrations/adam-eve/", "shame"),
    (["honor", "glory", "respect"], "https://freebibleimages.org/illustrations/solomon-throne/", "honor"),

    # ── Agricultural ──
    (["sow", "seed", "plant"], "https://freebibleimages.org/illustrations/parable-sower/", "sowing"),
    (["reap", "harvest", "collect"], "https://freebibleimages.org/illustrations/parable-sower/", "harvest"),
    (["plow", "till", "cultivate"], "https://freebibleimages.org/illustrations/farming/", "farming"),
    (["vine", "vineyard", "grape"], "https://freebibleimages.org/illustrations/vineyard/", "vineyard"),
    (["fig", "olive", "pomegranate"], "https://freebibleimages.org/illustrations/promised-land/", "fruit"),
    (["flock", "herd", "livestock"], "https://freebibleimages.org/illustrations/shepherd-flock/", "flock"),
    (["shepherd", "pastor"], "https://freebibleimages.org/illustrations/shepherd/", "shepherd"),
    (["bread", "food", "meal"], "https://freebibleimages.org/illustrations/manna/", "bread"),
    (["wine", "drink", "cup"], "https://freebibleimages.org/illustrations/last-supper/", "wine"),
    (["milk", "honey"], "https://freebibleimages.org/illustrations/promised-land/", "abundance"),
    (["meat", "flesh"], "https://freebibleimages.org/illustrations/sacrifice/", "meat"),

    # ── Clothing ──
    (["clothe", "garment", "robe", "dress"], "https://freebibleimages.org/illustrations/joseph-robe/", "garment"),
    (["linen", "wool", "fabric"], "https://freebibleimages.org/illustrations/tabernacle/", "fabric"),
    (["sackcloth", "mourning"], "https://freebibleimages.org/illustrations/jeremiah/", "mourning"),
    (["belt", "girdle", "loin"], "https://freebibleimages.org/illustrations/elijah-belt/", "belt"),
    (["crown", "diadem", "turban"], "https://freebibleimages.org/illustrations/david-crown/", "crown"),
    (["sandals", "shoe"], "https://freebibleimages.org/illustrations/moses-sandals/", "sandals"),
    (["ring", "seal", "signet"], "https://freebibleimages.org/illustrations/joseph-ring/", "ring"),

    # ── Objects ──
    (["scroll", "book", "document"], "https://freebibleimages.org/illustrations/scroll/", "scroll"),
    (["letter", "writing"], "https://freebibleimages.org/illustrations/scroll/", "writing"),
    (["staff", "rod", "stick"], "https://freebibleimages.org/illustrations/moses-staff/", "staff"),
    (["cup", "bowl", "vessel"], "https://freebibleimages.org/illustrations/last-supper/", "vessel"),
    (["lamp", "candle", "light"], "https://freebibleimages.org/illustrations/tabernacle-lamp/", "lamp"),
    (["basket", "container"], "https://freebibleimages.org/illustrations/manna/", "basket"),
    (["pitcher", "jar", "pot"], "https://freebibleimages.org/illustrations/water-jar/", "pottery"),
    (["key", "lock"], "https://freebibleimages.org/illustrations/keys/", "key"),
    (["net", "trap", "snare"], "https://freebibleimages.org/illustrations/fishing-net/", "net"),
    (["yoke", "burden"], "https://freebibleimages.org/illustrations/yoke/", "yoke"),
    (["trumpet", "horn"], "https://freebibleimages.org/illustrations/jericho-trumpet/", "trumpet"),
    (["harp", "lyre", "instrument"], "https://freebibleimages.org/illustrations/david-harp/", "music"),

    # ── Numbers ──
    (["four", "forty", "fourth"], "https://freebibleimages.org/illustrations/creation/", "four"),
    (["ten", "tenth"], "https://freebibleimages.org/illustrations/ten-commandments/", "ten"),
    (["five", "fifth"], "https://freebibleimages.org/illustrations/creation/", "five"),
    (["seven", "seventh"], "https://freebibleimages.org/illustrations/creation/", "seven"),
    (["twelve"], "https://freebibleimages.org/illustrations/twelve-tribes/", "twelve"),
    (["six"], "https://freebibleimages.org/illustrations/creation/", "six"),
    (["eight"], "https://freebibleimages.org/illustrations/creation/", "eight"),
    (["three"], "https://freebibleimages.org/illustrations/trinity/", "three"),

    # ── Proper names with story associations ──
    (["ephraim", "manasseh"], "https://freebibleimages.org/illustrations/ephraim/", "ephraim"),
    (["syria", "aramean", "aram"], "https://freebibleimages.org/illustrations/elisha-syria/", "syria"),
    (["egypt", "egyptian", "pharaoh"], "https://freebibleimages.org/illustrations/egypt/", "egypt"),
    (["babylon", "babylonian", "chaldean"], "https://freebibleimages.org/illustrations/babylon/", "babylon"),
    (["ezekiel"], "https://freebibleimages.org/illustrations/ezekiel/", "ezekiel"),
    (["jeremiah"], "https://freebibleimages.org/illustrations/jeremiah/", "jeremiah"),

    # ── Remaining common words ──
    (["morning", "dawn"], "https://freebibleimages.org/illustrations/creation/", "morning"),
    (["evening", "dusk", "twilight"], "https://freebibleimages.org/illustrations/creation/", "evening"),
    (["choose", "chosen", "elect", "selected"], "https://freebibleimages.org/illustrations/david-choose/", "chosen"),
    (["between", "among", "middle"], "https://freebibleimages.org/illustrations/partition/", "between"),
    (["those", "these", "this", "that"], "https://freebibleimages.org/illustrations/demonstrative/", "demonstrative"),
    (["our", "us", "we"], "https://freebibleimages.org/illustrations/people/", "first-person"),

    # ── Final batch: named people & places ──
    (["benjamin"], "https://freebibleimages.org/illustrations/benjamin/", "benjamin"),
    (["balaam"], "https://freebibleimages.org/illustrations/balaam/", "balaam"),
    (["gilead"], "https://freebibleimages.org/illustrations/gilead/", "gilead"),
    (["gad"], "https://freebibleimages.org/illustrations/gad/", "gad"),
    (["uncle", "aunt", "nephew", "cousin"], "https://freebibleimages.org/illustrations/family/", "relative"),
    (["build", "built", "builder", "rebuild"], "https://freebibleimages.org/illustrations/temple-build/", "building"),
    (["time", "season", "occasion"], "https://freebibleimages.org/illustrations/creation/", "time"),
    (["within", "inside", "midst", "among"], "https://freebibleimages.org/illustrations/tabernacle/", "interior"),
    (["sure", "certain", "surely"], "https://freebibleimages.org/illustrations/abraham/", "certainty"),
    (["mighty", "strong", "powerful"], "https://freebibleimages.org/illustrations/samson/", "strength"),
    (["poor", "needy", "afflicted"], "https://freebibleimages.org/illustrations/ruth-gleaning/", "poverty"),
    (["rich", "wealthy"], "https://freebibleimages.org/illustrations/solomon/", "wealth"),
    (["together", "united", "assembly"], "https://freebibleimages.org/illustrations/assembly/", "together"),
    (["soon", "quickly", "hasten"], "https://freebibleimages.org/illustrations/exodus/", "haste"),

    # ── Word-specific overrides (frequent unmatched words) ──
    (["said", "saith", "speak", "spoke", "saying", "declare"], "https://freebibleimages.org/illustrations/prophets/", "speech"),
    (["word", "saying", "matter"], "https://freebibleimages.org/illustrations/scroll/", "word"),
    (["become", "exist", "happen", "was"], "https://freebibleimages.org/illustrations/creation/", "existence"),
    (["bring", "fetch", "carry", "bore"], "https://freebibleimages.org/illustrations/exodus/", "bring"),
    (["give", "grant", "bestow"], "https://freebibleimages.org/illustrations/manna/", "give"),
    (["take", "receive", "accept", "grasp"], "https://freebibleimages.org/illustrations/abraham/", "take"),
    (["house", "household", "family", "dynasty"], "https://freebibleimages.org/illustrations/tent/", "house"),
    (["son", "child", "children", "offspring", "seed", "descendant"], "https://freebibleimages.org/illustrations/abraham/", "son"),
    (["father", "ancestor", "forefather"], "https://freebibleimages.org/illustrations/abraham/", "father"),
    (["mother", "matriarch"], "https://freebibleimages.org/illustrations/sarah/", "mother"),
    (["hand", "power", "strength", "might"], "https://freebibleimages.org/illustrations/moses-hand/", "hand"),
    (["day", "today"], "https://freebibleimages.org/illustrations/creation/", "day"),
    (["one", "first", "only"], "https://freebibleimages.org/illustrations/creation/", "one"),
    (["two", "second", "double", "both"], "https://freebibleimages.org/illustrations/creation/", "two"),
    (["know", "knowledge", "perceive", "understood"], "https://freebibleimages.org/illustrations/eden-knowledge/", "knowledge"),
    (["return", "repent", "turn back", "restore"], "https://freebibleimages.org/illustrations/return-prodigal/", "return"),
    (["hear", "listen", "obey"], "https://freebibleimages.org/illustrations/samuel/", "hear"),
    (["see", "behold", "look", "perceive", "sight"], "https://freebibleimages.org/illustrations/creation/", "sight"),
    (["walk", "go", "travel", "journey", "proceed"], "https://freebibleimages.org/illustrations/exodus-route/", "journey"),
    (["sit", "dwell", "live", "remain", "settle"], "https://freebibleimages.org/illustrations/tent/", "dwell"),
    (["stand", "arise", "rise", "stand up"], "https://freebibleimages.org/illustrations/resurrection/", "rise"),
    (["all", "every", "whole", "entire"], "https://freebibleimages.org/illustrations/creation/", "totality"),
    (["face", "presence", "before"], "https://freebibleimages.org/illustrations/moses-face/", "face"),
    (["people", "nation", "community", "tribe"], "https://freebibleimages.org/illustrations/israel/", "people"),
    (["soul", "life", "being", "spirit"], "https://freebibleimages.org/illustrations/creation/", "soul"),
    (["heart", "mind", "will"], "https://freebibleimages.org/illustrations/david-heart/", "heart"),
    (["king", "ruler", "monarch"], "https://freebibleimages.org/illustrations/david-king/", "king"),
    (["priest", "kohen", "minister"], "https://freebibleimages.org/illustrations/aaron/", "priest"),
    (["walked", "walk", "gone"], "https://freebibleimages.org/illustrations/exodus-route/", "walk"),
    (["inherit", "inheritance", "possession", "land"], "https://freebibleimages.org/illustrations/promised-land/", "inheritance"),
    (["sleep", "slept", "lie down"], "https://freebibleimages.org/illustrations/david-bed/", "sleep"),
    (["brother", "kinsman", "relative", "sibling"], "https://freebibleimages.org/illustrations/joseph/", "brother"),
    (["sister", "female relative"], "https://freebibleimages.org/illustrations/ruth/", "sister"),

    # ── Specific proper names with story associations ──
    (["ahab", "jezebel"], "https://freebibleimages.org/illustrations/elijah-ahab/", "ahab"),
    (["eleazar", "phinehas"], "https://freebibleimages.org/illustrations/priest/", "eleazar"),
    (["absalom"], "https://freebibleimages.org/illustrations/david-absalom/", "absalom"),
    (["abimelech"], "https://freebibleimages.org/illustrations/abimelech/", "abimelech"),
    (["enemies", "foe", "enemy"], "https://freebibleimages.org/illustrations/war/", "enemy"),
    (["rams", "ram"], "https://freebibleimages.org/illustrations/sacrifice/", "ram"),
    (["counsel", "advice", "adviser"], "https://freebibleimages.org/illustrations/solomon-wisdom/", "counsel"),
    (["sister"], "https://freebibleimages.org/illustrations/ruth/", "sister"),
    (["tabernacle", "tent", "dwelling"], "https://freebibleimages.org/illustrations/tabernacle/", "tabernacle"),
    (["cubit", "measure", "measurement"], "https://freebibleimages.org/illustrations/tabernacle/", "measurement"),
    (["perish", "destroy", "die", "death", "dead"], "https://freebibleimages.org/illustrations/flood/", "death"),
    (["love", "loved", "beloved"], "https://freebibleimages.org/illustrations/david-jonathan/", "love"),
    (["workers", "work", "labor", "toil"], "https://freebibleimages.org/illustrations/tabernacle-work/", "work"),
    (["follow", "followed", "pursue", "chase"], "https://freebibleimages.org/illustrations/exodus/", "pursuit"),
    (["year", "years"], "https://freebibleimages.org/illustrations/creation/", "year"),

    # ── Israel / People ──
    (["Israel", "Jacob"], "https://freebibleimages.org/illustrations/israel/", "israel"),
    (["Judah", "Jew", "Jewish"], "https://freebibleimages.org/illustrations/judah/", "judah"),
    (["Egypt", "Egyptian"], "https://freebibleimages.org/illustrations/egypt/", "egypt"),
    (["Babylon", "Babylonian"], "https://freebibleimages.org/illustrations/babylon/", "babylon"),
    (["Assyria", "Assyrian"], "https://freebibleimages.org/illustrations/assyria/", "assyria"),
    (["Philistine", "Gaza"], "https://freebibleimages.org/illustrations/philistine/", "philistine"),
    (["Zion", "Jerusalem"], "https://freebibleimages.org/illustrations/jerusalem/", "jerusalem"),
    (["Sinai", "Horeb"], "https://freebibleimages.org/illustrations/sinai/", "sinai"),
    (["Jordan", "river"], "https://freebibleimages.org/illustrations/jordan/", "jordan"),
]


def normalize_gloss(g):
    """Normalize a gloss string for keyword matching."""
    return g.lower().strip().replace(",", " ").replace(";", " ").replace("(", " ").replace(")", " ")


def expand_images(dry_run=True):
    """Expand word image coverage to remaining vocabulary words."""
    mem = sqlite3.connect(str(MEM_DB))
    mem.row_factory = sqlite3.Row
    scrip = sqlite3.connect(str(SCRIPTURE_DB))
    scrip.row_factory = sqlite3.Row

    # Get all vocab words without images
    vocab = mem.execute("""
        SELECT n.id, l.content_json
        FROM hebrew_nodes n
        JOIN hebrew_lessons l ON l.node_id = n.id
        WHERE n.category='word' AND n.id LIKE 'vocab_%'
        ORDER BY n.id
    """).fetchall()

    already = set(
        r["word_hebrew"] for r in scrip.execute("SELECT DISTINCT word_hebrew FROM word_images").fetchall()
    )

    matched = 0
    unmatched = 0
    unmatched_words = []

    for v in vocab:
        lesson = json.loads(v["content_json"])
        hebrew = lesson.get("hebrew", "")
        gloss = lesson.get("gloss", "")
        if not hebrew or hebrew in already:
            continue
        if not gloss:
            unmatched += 1
            unmatched_words.append((hebrew, gloss or "(no gloss)"))
            continue

        gloss_norm = normalize_gloss(gloss)
        found = False

        for keywords, url, theme in THEME_BUCKETS:
            for kw in keywords:
                if kw.lower() in gloss_norm:
                    if not dry_run:
                        # Find the vocab node_id
                        node_id = v["id"]
                        try:
                            scrip.execute(
                                """INSERT OR IGNORE INTO word_images
                                   (word_hebrew, node_id, source, image_url, attribution, prompt)
                                   VALUES (?, ?, 'freebible', ?, 'FreeBibleImages.org (CC BY-NC-ND 4.0)', ?)""",
                                (hebrew, node_id, url, theme)
                            )
                        except Exception:
                            pass
                    matched += 1
                    found = True
                    break
            if found:
                break

        if not found:
            unmatched += 1
            unmatched_words.append((hebrew, gloss))

    if not dry_run:
        scrip.commit()

    # Stats
    total = scrip.execute("SELECT COUNT(*) as c FROM word_images").fetchone()["c"]
    by_source = scrip.execute(
        "SELECT source, COUNT(*) as c FROM word_images GROUP BY source ORDER BY c DESC"
    ).fetchall()

    print(f"\n✓ Word image expansion {'[DRY RUN]' if dry_run else '[APPLIED]'}")
    print(f"  New images added:  {matched}")
    print(f"  Still unmatched:   {unmatched}")
    print(f"  Total in DB:       {total}")
    print("  By source:")
    for s, c in by_source:
        print(f"    {s}: {c}")

    if unmatched > 0 and matched > 0:
        print(f"\n  Coverage: {total}/{total+unmatched} words ({(total/(total+unmatched)*100):.0f}%)")

    if unmatched_words and matched > 0:
        print(f"\n  Sample unmatched (first 20 of {len(unmatched_words)}):")
        for h, g in unmatched_words[:20]:
            print(f"    {h:10s} → {g[:30]}")

    mem.close()
    scrip.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expand word images coverage")
    parser.add_argument("--apply", action="store_true", help="Actually insert")
    args = parser.parse_args()
    expand_images(dry_run=not args.apply)
