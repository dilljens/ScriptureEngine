#!/usr/bin/env python3
"""Bilingual anchor test for LXX gap fills: does the Greek cell genuinely
correspond to the English verse, or just resemble it in English?

Method: transliterate the Greek cell to Latin, then look for distinctive
shared content words (proper names + common biblical vocabulary) present
on BOTH sides. A candidate passes with >= 2 distinct anchor hits.
Single shared names (e.g. 'Joshua' occurring in two different verses)
are NOT enough -- cf. lxx_josh.9.34, an exact English match whose Greek
is a different verse sharing only the name Joshua.

The lexicon maps English stems to sets of transliterated-Greek stems.
Stems are matched by common prefix >= ANCHOR_MIN (5), so inflection
(kurios/kuriou/kurion) does not matter. Transliteration: NFD-strip
diacritics, then a fixed Greek->Latin map.
"""

import re
import unicodedata

ANCHOR_MIN = 4  # min common-prefix length for a hit (full-token
# equality also counts for short stems, e.g. earth = γῆς = "ges")
ANCHOR_NEED = 2  # distinct anchors required to pass

_GR_MAP = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e",
    "ζ": "z", "η": "e", "θ": "th", "ι": "i", "κ": "k",
    "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o",
    "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t",
    "υ": "y", "φ": "ph", "χ": "ch", "ψ": "ps", "ω": "o",
}


def transliterate(gr):
    # NFD exposes rough breathing only as combining U+0314, which
    # naive stripping would delete (hagios -> agios). Upsilons are
    # diphthong-aware: au/eu/eu/ou stay together (holokautoma, ous),
    # standalone u -> y (kyrios), ui+rough -> hui (huios). Diaeresis
    # (U+0308, pronounced separately) never merges.
    s = unicodedata.normalize("NFD", gr.lower())
    M = "[\u0300-\u0307\u0309-\u036f]*"  # marks except diaeresis
    RB = "\u0314"  # combining reversed comma above = rough breathing
    s = re.sub("\u03c5\u03b9" + RB + M, "hui", s)  # ui+rough
    s = re.sub("\u03b1\u03c5" + M, "au", s)
    s = re.sub("\u03b5\u03c5" + M, "eu", s)
    s = re.sub("\u03b7\u03c5" + M, "eu", s)
    s = re.sub("\u03bf\u03c5" + M, "ou", s)
    s = re.sub("\u03c5" + M + RB, "hu", s)  # rough-bearing upsilon
    s = s.replace("\u03c1" + RB, "rh")  # rhema, rhabdos
    for v in "\u03b1\u03b5\u03b7\u03b9\u03bf\u03c5\u03c9":
        s = s.replace(v + RB, "h" + v)
    out = []
    for c in s:
        if unicodedata.category(c).startswith("M"):
            continue
        out.append(_GR_MAP.get(c, c))
    return "".join(out)


def gr_tokens(gr):
    return re.findall(r"[a-z]+", transliterate(gr))


# English stem -> transliterated Greek stems (multiple allomorphs OK).
# Proper names first, then common biblical vocabulary. Stems are
# deliberately short; matching is by common prefix >= ANCHOR_MIN.
LEXICON = {
    # patriarchs / leaders
    "abraham": {"abraam"}, "isaac": {"isaak"}, "jacob": {"iakob"},
    "joseph": {"ioseph"}, "moses": {"mouses", "mose", "moyse", "mouse"}, "aaron": {"aaron"},
    "joshua": {"iesou"}, "jesus": {"iesou"}, "samuel": {"samouel"},
    "saul": {"saoul"}, "david": {"dauid", "dabid"}, "solomon": {"solomon"},
    "elijah": {"eliou", "elias"}, "eliu": {"eliou", "elias"}, "elisha": {"elisaie"},
    "isaiah": {"esaiou"}, "esaias": {"esaiou"},
    "jeremiah": {"ieremi"}, "jeremias": {"ieremi"},
    "ezekiel": {"iezeki"}, "daniel": {"daniel"},
    "josiah": {"iosiou"}, "josias": {"iosi"}, "joakim": {"ioakim"},
    "sedekias": {"sedeki"}, "zedechias": {"sedeki"},
    "nabuchodonosor": {"naboucho"}, "nebuchadnezzar": {"naboucho"},
    "pharaoh": {"pharao"}, "pharao": {"pharao"},
    "hiram": {"chiram"}, "chiram": {"chiram"},
    "baruch": {"barouch"}, "barouch": {"barouch"},
    "gideon": {"gedeon"}, "samson": {"sampson"},
    "goliath": {"goliath"}, "goliah": {"goliath"},
    "balaam": {"balaam"}, "balac": {"balak"}, "balak": {"balak"},
    "cyrus": {"kyro"}, "darius": {"darei"}, "artaxerxes": {"arthasastha"},
    # peoples / places
    "israel": {"israel"}, "judah": {"iouda"}, "juda": {"iouda"},
    "jerusalem": {"ierousa"}, "sion": {"sion"}, "egypt": {"aigypt"},
    "babylon": {"babylon"}, "assyria": {"assyri"}, "assyrian": {"assyri"},
    "moab": {"moab"}, "ammon": {"ammon"}, "edom": {"edom", "idoum"},
    "amalek": {"amalek"}, "amalec": {"amalek"}, "midian": {"madiam"},
    "canaan": {"chanaan"}, "philistine": {"allophyl"},
    "amorite": {"amorrhai"}, "amorrhite": {"amorrhai"},
    "hittite": {"chettai"}, "jebusite": {"iebousai"},
    "tyre": {"tyro"}, "tyrus": {"tyro"}, "sidon": {"sidon"},
    "gabaon": {"gabaon"}, "galgala": {"galgala"}, "galgal": {"galgal"},
    "jordan": {"iordan"}, "euphrates": {"euphrat"},
    "lebanon": {"liban"}, "carmel": {"karmel"}, "sinai": {"sina"},
    "horeb": {"choreb"}, "ephraim": {"ephraim"}, "manasseh": {"manasse"},
    "manasses": {"manasse"}, "benjamin": {"beniamin"},
    "nephthalim": {"nephthal"}, "nephthali": {"nephthal"},
    "zabulon": {"zaboulon"}, "issachar": {"issachar"},
    "gilead": {"galaad"}, "bashan": {"basan"}, "damascus": {"damask"},
    "sodom": {"sodom"}, "gomorrha": {"gomorrh"}, "sodomit": {"sodom"},
    "aelon": {"ealon"}, "maceda": {"makeda"}, "makeda": {"makeda"},
    "bethoron": {"baithoron"}, "bethhoron": {"baithoron"},
    # God / divine
    "god": {"theo"}, "lord": {"kyrio"}, "almighty": {"pantokrat"},
    "holy": {"hagi"}, "heaven": {"ouran"}, "angel": {"angel"},
    "cherub": {"cheroub"}, "seraph": {"seraph"},
    # people / society
    "king": {"basil"}, "queen": {"basiliss"}, "prince": {"archon"},
    "elder": {"presbyt"}, "judge": {"krit"}, "priest": {"hiere"},
    "prophet": {"prophet"}, "levite": {"leuit"}, "scribe": {"grammat"},
    "servant": {"doulo", "paido", "pais"}, "master": {"kyrio", "despot"},
    "slave": {"doulo"}, "people": {"lao"}, "nation": {"ethno"},
    "tribe": {"phyl"}, "multitude": {"pletho", "ochlo"},
    "man": {"aner", "anthropo"}, "men": {"aner", "anthropo", "andron"},
    "woman": {"gyne", "gynaik"}, "women": {"gyne", "gynaik"}, "wife": {"gynaik"},
    "husband": {"aner", "andros"}, "father": {"pater", "patro", "patros"},
    "mother": {"meter", "metro", "metros"}, "son": {"huio"}, "sons": {"huio"},
    "daughter": {"thygat"}, "brother": {"adelph"}, "sister": {"adelph"},
    "child": {"paid", "tekno"}, "children": {"paid", "tekno", "huio"},
    "virgin": {"parthen"}, "widow": {"chera"}, "stranger": {"proselyt"},
    "neighbour": {"plesion"}, "friend": {"phil"}, "enemy": {"echthr"},
    "shepherd": {"poimen"}, "fisherman": {"halie"},
    # body / life
    "hand": {"cheir"}, "hands": {"cheir"}, "mouth": {"stoma", "stomat"},
    "eye": {"ophthalm"}, "eyes": {"ophthalm"}, "ear": {"ous", "oto"},
    "heart": {"kardi"}, "soul": {"psyche"}, "flesh": {"sarx", "sark"},
    "blood": {"haima", "haimat"}, "bone": {"osteo"}, "head": {"kephal"},
    "foot": {"pous", "pod"}, "feet": {"pous", "pod"}, "life": {"zoe"}, "death": {"thanat"},
    "voice": {"phone"}, "name": {"onoma", "onomat"},
    # nature
    "earth": {"ges", "gen", "gaia"}, "land": {"ge", "ges", "chor"},
    "sea": {"thalass"}, "water": {"hydor", "hydat"}, "waters": {"hydor", "hydat"},
    "river": {"potamos", "potam"}, "fountain": {"peg"}, "well": {"phrear"},
    "mountain": {"oro"}, "mount": {"oro"}, "hill": {"bouno", "loph"},
    "rock": {"petr"}, "stone": {"lith"}, "stones": {"lith"},
    "field": {"agro"}, "garden": {"paradeis"}, "vineyard": {"ampelon"},
    "tree": {"xylo", "dendr"}, "wood": {"xylo"}, "cedar": {"kedr"},
    "sun": {"helio"}, "moon": {"selene"}, "star": {"aster"},
    "day": {"hemer"}, "night": {"nyx", "nykt"}, "morning": {"proi"},
    "evening": {"hesper"}, "year": {"eto", "eniaut"}, "month": {"men"},
    "sabbath": {"sabbat"}, "cloud": {"nephel"}, "wind": {"anem", "pneum"},
    "fire": {"pyr"}, "flame": {"phlox", "phlog"}, "smoke": {"kapn"},
    "rain": {"huet"}, "dew": {"dros"}, "snow": {"chion"},
    "bread": {"arto"}, "wine": {"oino"}, "oil": {"elaio"},
    "honey": {"meli"}, "salt": {"hal"}, "manna": {"manna"},
    "milk": {"gala"},
    # animals
    "ox": {"bous", "mosch"}, "oxen": {"bous", "mosch"},
    "calf": {"mosch"}, "bullock": {"mosch"}, "heifer": {"damal"},
    "sheep": {"probat"}, "lamb": {"amno"}, "ram": {"krio"},
    "goat": {"chimar", "trag", "aix"}, "kid": {"chimar", "trag", "aix"},
    "horse": {"hipp"}, "ass": {"ono", "hypozyg"}, "camel": {"kamel"},
    "dove": {"peristera", "perister"}, "eagle": {"aeto"}, "serpent": {"ophi"},
    "lion": {"leon", "leont"}, "bear": {"arkto"}, "dog": {"kyon", "kyn"},
    # war
    "war": {"polem"}, "battle": {"polem", "paratax"},
    "sword": {"machair", "romphai"}, "bow": {"toxo"}, "arrow": {"bel"},
    "shield": {"thyre", "aspi"}, "spear": {"dory", "dorat", "gaison", "lonche"},
    "chariot": {"harma"}, "army": {"strat", "parembol"}, "host": {"strat"},
    "camp": {"parembol"}, "siege": {"perioche", "perioch", "sygkleism"},
    # cult
    "altar": {"thysiaster"}, "sacrifice": {"thysi"},
    "offering": {"thysi", "dor", "holokau", "prosphor"},
    "burnt": {"holokau"}, "incense": {"thymiam"},
    "censer": {"thyisk", "libanot"}, "laver": {"louter"},
    "veil": {"katapetasm"}, "lamp": {"lychni"}, "candlestick": {"lychni"},
    "table": {"trapez"}, "ark": {"kibot"}, "tabernacle": {"sken"},
    "temple": {"nao", "oiko"}, "sanctuary": {"hagiasm", "nao"},
    "covenant": {"diathek"}, "testament": {"diathek"},
    "oath": {"horko"}, "vow": {"euche"}, "prayer": {"proseuch"},
    "psalm": {"psalm"}, "song": {"ode"}, "blessing": {"eulogi"},
    "curse": {"katar"}, "feast": {"heort"}, "passover": {"pascha"},
    "jubilee": {"iobeli"}, "atonement": {"exilasmos", "exilasm"},
    # city / house
    "city": {"pol"}, "cities": {"pol"}, "house": {"oiko", "oikia"},
    "door": {"thyr"}, "gate": {"pyl"}, "wall": {"teich"},
    "tower": {"pyrg"}, "tent": {"sken"}, "palace": {"aul", "oiko"},
    "throne": {"thron"}, "crown": {"stephan"}, "sceptre": {"rhabd"},
    "garment": {"himat"}, "robe": {"stol"}, "sackcloth": {"sakk"},
    "shoe": {"hypodem"}, "girdle": {"zone", "zon"},
    # metals / materials
    "gold": {"chryso", "chrys"}, "silver": {"argyr"},
    "brass": {"chalk"}, "iron": {"sider"}, "lead": {"molibd", "molybd"},
    # abstractions
    "word": {"log", "rhem"}, "words": {"log", "rhem"},
    "wisdom": {"sophi"}, "fool": {"aphron", "mor"}, "folly": {"aphrosyn"},
    "righteous": {"dikaio"}, "just": {"dikaio"},
    "sinner": {"hamartol"}, "sin": {"hamarti"}, "sins": {"hamarti"},
    "mercy": {"eleo"}, "judgment": {"krim", "kris"},
    "peace": {"eiren"}, "truth": {"alethei"}, "lie": {"pseud"},
    "faith": {"pist"}, "hope": {"elpid"}, "love": {"agap"},
    "fear": {"phob"}, "joy": {"char", "euphrosyn"}, "anger": {"org", "thym"},
    "strength": {"ischy"}, "glory": {"dox"}, "honour": {"tim", "dox"},
    "shame": {"aischyn", "entrop"}, "praise": {"aino", "eulog"},
    "thanksgiving": {"eucharist"}, "salvation": {"soter"},
    "captive": {"aichmalot"}, "captivity": {"aichmalos", "apoiki"},
    "famine": {"limo"}, "pestilence": {"thanat"}, "plague": {"mastix", "mastig"},
    "dream": {"enypni"}, "vision": {"horas", "horam"},
    "parable": {"parabol"}, "proverb": {"paroimi"},
    # numbers (stable, match numerals-as-words on both sides)
    # NB: no heis for "one" -- norm-collides with eis ("into")
    "one": {"hen", "mia"}, "two": {"dyo"},
    "three": {"treis", "tria"}, "four": {"tessar"},
    "five": {"pente"}, "six": {"hex"}, "seven": {"hepta"},
    "eight": {"okto"}, "nine": {"ennea"}, "ten": {"deka"},
    "eleven": {"hendeka"}, "twelve": {"dodeka"},
    "twenty": {"eikosi"}, "thirty": {"triakonta"},
    "hundred": {"hekaton"}, "thousand": {"chilias", "chilioi"},
    "first": {"protos"}, "second": {"deuteros"},
    "third": {"tritos"}, "fourth": {"tetartos"},
    # food, vessels, materials, cult objects
    "bed": {"koite"}, "cauldron": {"lebes"}, "wheat": {"pyros"},
    "barley": {"krithe"}, "flour": {"aleuron"}, "beans": {"kyamos"},
    "meal": {"alphit"}, "vessel": {"skeuos"}, "frog": {"batrach"},
    "scourge": {"mastig", "mastix"}, "dwelling": {"skenoma"},
    "chamber": {"thee"}, "palm": {"phoinik"}, "measure": {"metr"},
    "reward": {"misth"}, "lover": {"erast"}, "birth": {"genes"},
    "wash": {"lou"}, "tooth": {"odont"},
    "maid": {"therapaina", "paidiske"},
    "handmaid": {"therapaina", "paidiske"}, "clay": {"pelos"},
    "brick": {"plinth"}, "grate": {"eschara"}, "horn": {"keras"},
    "wreath": {"stephane"}, "skins": {"derris"}, "cubit": {"pechys"},
    "seed": {"spor"}, "harvest": {"amet"}, "ephod": {"epomis"},
    "blue": {"hyakinth"}, "purple": {"porphyr"},
    "scarlet": {"kokkin"}, "linen": {"byssos"}, "anoint": {"chrio"},
    "ossifrage": {"gryps"}, "died": {"apothan"}, "die": {"apothan"},
    "steal": {"klept"}, "sell": {"apodot"}, "buried": {"thapt"},
    "pure": {"kathar"}, "apple": {"melon"}, "bear": {"arkt"},
    # Brenton name spellings met in the cells
    "sarrha": {"sarra"}, "sarah": {"sarra"}, "agar": {"agar"},
    "ishmael": {"ismael"}, "ismael": {"ismael"},
    "abraam": {"abraam"},
    # verbs (common stems)
    "said": {"eipen", "elalesen", "legon", "eipon"},
    "speak": {"lalesen", "lalesei", "legon"}, "spoke": {"elalesen", "eipen"},
    "answered": {"apekrith"},
    "commanded": {"eneteil", "synetax"}, "sent": {"apesteil", "pemp"},
    "chosen": {"ekleg", "eklekt"}, "choose": {"ekleg"},
    "anointed": {"echris"}, "appointed": {"etax", "katesthes"},
    "numbered": {"arithm"}, "counted": {"arithm"},
    "written": {"egraph"}, "spoil": {"skyl", "pronomeus"},
    "spoils": {"skyl", "pronomeus"},
    "took": {"elab", "eph"}, "gave": {"edok", "didomi"},
    "made": {"epoie", "egenet"}, "built": {"okodom"}, "destroyed": {"exolothreus", "katestreps", "diephtheir"},
    "killed": {"apektein", "ephoneus"}, "slew": {"apektein"},
    "smote": {"epatax"}, "fought": {"epolem"}, "fled": {"ephyg", "phyge"},
    "went": {"eporeuth", "exelth", "apelth"}, "came": {"elth", "paregenet"},
    "arose": {"anest", "exanest"}, "stood": {"este", "histemi"},
    "sat": {"ekathis"}, "dwelt": {"katoik", "oike"}, "slept": {"ekoimeth"},
    "ate": {"ephag"}, "drank": {"epie"}, "saw": {"eid"}, "heard": {"ekous"},
    "knew": {"egno"}, "remembered": {"emnesth"}, "forgot": {"epelathet"},
    "blessed": {"euloges"}, "cursed": {"katerasat", "epikatarat"},
    "prayed": {"proseuxat"}, "sang": {"es", "psal"}, "wept": {"eklaus"},
    "rejoiced": {"euphranth", "echar"}, "feared": {"ephobeth"},
    "trusted": {"episteus", "pepoith"}, "trust": {"pist", "pepoith"},
    "saved": {"esos"}, "delivered": {"paredok", "erysat", "exeilat"},
    "strengthened": {"ischyr", "enischys", "kratai"},
    "established": {"ethemeli", "estereos"},
    "foundation": {"themel"}, "foundations": {"themel"},
    # adjectives/misc
    "great": {"megas", "megal"}, "small": {"mikr"}, "little": {"mikr", "olig"},
    "many": {"polloi", "polys", "poll"}, "few": {"olig"}, "much": {"polloi", "polys", "poll"},
    "good": {"agath"}, "evil": {"poner", "kak"}, "wicked": {"aseb", "anom"},
    "new": {"kain"}, "old": {"palai", "archai"},
    "first": {"prot"}, "last": {"eschat"},
    "high": {"hypsel"}, "deep": {"bathy"}, "broad": {"plat", "eury"},
    "long": {"makr"}, "short": {"syntom", "brach"},
    "strong": {"ischyr", "kratai"}, "weak": {"asthen"},
    "clean": {"kathar"}, "unclean": {"akathart"},
}


_IRREGULAR = {
    "children": "child", "women": "woman", "men": "man",
    "feet": "foot", "teeth": "tooth", "oxen": "ox",
}


def en_anchors(en):
    """Distinct lexicon-matched English stems in the verse."""
    found = {}
    for tok in re.findall(r"[A-Za-zÆæŒœ]+", en.lower()):
        if len(tok) < 3:
            continue
        stem = tok
        if stem not in LEXICON:
            if stem in _IRREGULAR:
                stem = _IRREGULAR[stem]
            elif stem.endswith("ies") and len(stem) > 5:
                stem = stem[:-3] + "y"
            elif stem.endswith("en") and len(stem) > 5 \
                    and stem[:-2] in LEXICON:
                stem = stem[:-2]  # golden->gold, wooden->wood
            elif stem.endswith("ed") and len(stem) > 6 and \
                    stem[:-2] in LEXICON:
                stem = stem[:-2]  # salted->salt
            elif stem.endswith("ed") and len(stem) > 6 and \
                    stem[:-1] in LEXICON:
                stem = stem[:-1]  # anointed->anoint
            elif stem.endswith("es") and stem[:-2] in LEXICON:
                stem = stem[:-2]  # houses->house (before -s rule)
            elif stem.endswith("s") and stem[:-1] in LEXICON:
                stem = stem[:-1]  # foundations->foundation
        if stem in LEXICON:
            found.setdefault(stem, tok)
    return found


# English stems whose Greek form is (practically) invariable, so its
# ABSENCE from a candidate Greek cell contradicts correspondence.
# Proper names (transliterated, never translated) plus a handful of
# ultra-stable nouns. Common vocabulary is deliberately excluded:
# synonyms (sent = apesteil/pemp/exaposteil...) would false-positive.
CONTRA = {
    "abraham", "isaac", "jacob", "joseph", "moses", "aaron",
    "joshua", "jesus", "samuel", "saul", "david", "solomon",
    "elijah", "eliu", "elisha", "isaiah", "esaias",
    "jeremiah", "jeremias", "ezekiel", "daniel",
    "josiah", "josias", "joakim", "sedekias", "zedechias",
    "nabuchodonosor", "nebuchadnezzar", "pharaoh", "pharao",
    "hiram", "chiram", "baruch", "barouch",
    "gideon", "samson", "goliath", "goliah",
    "balaam", "balac", "balak", "cyrus", "darius", "artaxerxes",
    "israel", "judah", "juda", "jerusalem", "sion", "egypt",
    "babylon", "assyria", "assyrian", "moab", "ammon", "edom",
    "amalek", "amalec", "midian", "canaan", "philistine",
    "amorite", "amorrhite", "hittite", "jebusite",
    "tyre", "tyrus", "sidon", "gabaon", "galgala", "galgal",
    "jordan", "euphrates", "lebanon", "carmel", "sinai",
    "horeb", "ephraim", "manasseh", "manasses", "benjamin",
    "nephthalim", "nephthali", "zabulon", "issachar",
    "gilead", "bashan", "damascus", "sodom", "gomorrha",
    "aelon", "maceda", "makeda", "bethoron", "bethhoron",
    "god", "lord", "king", "house", "city",
}


def anchor_contradictions(en, gr):
    """Subset of CONTRA anchors present in the English but with no
    matching form in the Greek: evidence the cells are different
    verses sharing vocabulary (e.g. same formula, another king)."""
    gtoks = gr_tokens(gr)
    bad = {}
    for stem, tok in en_anchors(en).items():
        if stem not in CONTRA:
            continue
        ok = any(_match(g, t) for g in LEXICON[stem] for t in gtoks)
        if not ok:
            bad[stem] = tok
    return bad


def _prefix_hit(g, t):
    n = 0
    for a, b in zip(g, t):
        if a != b:
            break
        n += 1
    return n >= ANCHOR_MIN or (n == min(len(g), len(t))
                               and min(len(g), len(t)) >= 3)


def _norm_breathing(t):
    # The source edition is inconsistent about rough breathings
    # (Ἰησοῦς spelled smooth, Ἱερουσαλήμ rough) and upsilon takes
    # rough as hu- but smooth/bare as y-. Worse, bare υε/υι spellings
    # (υετός for ὑετός) produce ye-/yi- initials. Normalize all
    # upsilon-initial and h-initial forms to one shape so lexicon
    # stems match either spelling. (No non-upsilon token begins with
    # these clusters, and articles ohi/ahi are never anchors.)
    if t[:3] in ("hui", "hyi", "yui"):
        return "u" + t[3:]
    if t[:2] in ("hu", "hy", "yu", "ye", "yi", "yg", "yo"):
        return "u" + t[2:]
    if t[:1] == "h":
        return t[1:]
    return t


def _match(g, t):
    return (_prefix_hit(g, t)
            or _prefix_hit(_norm_breathing(g), _norm_breathing(t)))


def anchor_hits(en, gr):
    """Return {en_stem: (en_tok, gr_tok)} for each anchor with a
    transliterated-Greek token sharing a common prefix >= ANCHOR_MIN
    (or full-token equality for short stems like earth = γῆς)."""
    gtoks = gr_tokens(gr)
    hits = {}
    for stem, tok in en_anchors(en).items():
        for g in LEXICON[stem]:
            for t in gtoks:
                if _match(g, t):
                    hits[stem] = (tok, t)
                    break
            if stem in hits:
                break
    return hits
