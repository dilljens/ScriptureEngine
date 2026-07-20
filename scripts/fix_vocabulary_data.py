#!/usr/bin/env python3
"""
Fix vocabulary data: wrong glosses, archaic English, inflected forms.

This script corrects:
1. hebrew_nodes.title — node display title
2. hebrew_nodes.description — node description  
3. hebrew_lessons.content_json — the content JSON blob
4. hebrew_practice_items — question text and correct answers
5. lemma_gloss in scripture.db — source data for future rebuilds

Usage:
    python3 scripts/fix_vocabulary_data.py
"""

import json
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"

# ── Correction map ──
# Format: {node_id: {"hebrew": new_hebrew_or_None, "gloss": new_gloss_or_None}}
# If "hebrew" is set, the Hebrew word in the lesson changes.
# If "gloss" is set, the English gloss changes.
# If "title" is set, the display title changes (otherwise auto-generated from hebrew+gloss).

CORRECTIONS = {

    # ── Complete wrong gloss ──
    "vocab_את_0":      {"gloss": "direct object marker", "title": "אֶת — direct object marker"},
    "vocab_לא_8":      {"gloss": "not / no"},
    "vocab_עשה_13":    {"hebrew": "עָשָׂה", "gloss": "to make / to do"},
    "vocab_הביא_15":   {"hebrew": "בּוֹא", "gloss": "to come / to go / to bring"},
    "vocab_מן_19":     {"gloss": "from"},
    "vocab_עד_20":     {"gloss": "until / as far as / forever"},
    "vocab_לפני_21":   {"hebrew": "לִפְנֵי", "gloss": "before / in front of", "title": "לִפְנֵי — before, in front of"},
    "vocab_אתה_47":    {"gloss": "you (m. sg.)"},
    "vocab_אנכי_101":  {"gloss": "I (first person)"},
    "vocab_הזה_32":    {"hebrew": "זֶה", "gloss": "this (m. sg.)", "title": "זֶה — this (m. sg.)"},
    "vocab_הזאת_109":  {"hebrew": "זֹאת", "gloss": "this (f. sg.)", "title": "זֹאת — this (f. sg.)"},
    "vocab_אדני_66":   {"hebrew": "אֲדֹנָי", "gloss": "Lord / my Lord", "title": "אֲדֹנָי — Lord / my Lord"},
    "vocab_הם_74":     {"gloss": "they (m.)"},
    "vocab_מאת_64":    {"hebrew": "מֵאֵת", "gloss": "from (with direct object marker)", "title": "מֵאֵת — from"},
    "vocab_או_127":    {"gloss": "or"},
    "vocab_ועתה_104":  {"hebrew": "עַתָּה", "gloss": "now", "title": "עַתָּה — now"},
    "vocab_מי_95":     {"gloss": "who?"},
    "vocab_עמה_25":    {"hebrew": "עִם", "gloss": "with", "title": "עִם — with"},
    "vocab_ויאמ_9":    {"hebrew": "אָמַר", "gloss": "to say", "title": "אָמַר — to say"},
    "vocab_ויהי_12":   {"hebrew": "הָיָה", "gloss": "to be / to become", "title": "הָיָה — to be, to become"},
    "vocab_ויקח_49":   {"hebrew": "לָקַח", "gloss": "to take", "title": "לָקַח — to take"},
    "vocab_נתתי_17":   {"hebrew": "נָתַן", "gloss": "to give", "title": "נָתַן — to give"},
    "vocab_ביתך_18":   {"hebrew": "בַּיִת", "gloss": "house / household", "title": "בַּיִת — house, household"},
    "vocab_שובך_52":   {"hebrew": "שׁוּב", "gloss": "to return / to repent", "title": "שׁוּב — to return, to repent"},
    "vocab_אביו_24":   {"hebrew": "אָב", "gloss": "father", "title": "אָב — father"},
    "vocab_ידו_30":    {"hebrew": "יָד", "gloss": "hand / power", "title": "יָד — hand, power"},
    "vocab_אפיך_135":  {"hebrew": "אַף", "gloss": "nose / anger / wrath", "title": "אַף — nose, anger, wrath"},
    "vocab_ראית_35":   {"hebrew": "רָאָה", "gloss": "to see / to perceive", "title": "רָאָה — to see, to perceive"},
    "vocab_שמעת_27":   {"hebrew": "שָׁמַע", "gloss": "to hear / to obey", "title": "שָׁמַע — to hear, to obey"},
    "vocab_תוצא_48":   {"hebrew": "יָצָא", "gloss": "to go out / to come forth", "title": "יָצָא — to go out, to come forth"},
    "vocab_הארץ_23":   {"hebrew": "אֶרֶץ", "gloss": "earth / land", "title": "אֶרֶץ — earth, land"},
    "vocab_אתה_47":    {"gloss": "you (m. sg.)"},
    "vocab_אתם_138":   {"gloss": "you (m. pl.)"},
    "vocab_שם_37":     {"gloss": "there"},
    "vocab_אם_38":     {"gloss": "if / whether / when"},
    "vocab_כן_50":     {"gloss": "so / thus / therefore"},
    "vocab_עוד_68":    {"gloss": "again / still / yet / more"},
    "vocab_נא_72":     {"gloss": "please / now / I pray"},
    "vocab_אלה_92":    {"gloss": "these / those"},
    "vocab_מה_63":     {"gloss": "what? / how?"},
    "vocab_כה_43":     {"gloss": "thus / so"},
    "vocab_גם_58":     {"gloss": "also / even / indeed"},
    "vocab_אין_59":    {"gloss": "there is not / nothing"},
    "vocab_אך_178":    {"gloss": "surely / only / but"},
    "vocab_רק_256":    {"gloss": "only / but / however"},
    "vocab_פן_218":    {"gloss": "lest / otherwise"},
    "vocab_אז_238":    {"gloss": "then / at that time"},
    "vocab_אחרי_45":   {"gloss": "after / behind"},
    "vocab_בין_122":   {"gloss": "between / among"},
    "vocab_למען_117":  {"gloss": "for the sake of / in order that"},
    "vocab_עולם_129":  {"gloss": "eternity / forever / ancient times"},
    "vocab_מאד_100":   {"gloss": "very / exceedingly"},
    "vocab_יען_280":   {"gloss": "because / therefore"},
    "vocab_עבר_93":    {"gloss": "to pass over / to cross"},
    "vocab_אכל_60":    {"hebrew": "אָכַל", "gloss": "to eat", "title": "אָכַל — to eat"},
    "vocab_ידע_39":    {"hebrew": "יָדַע", "gloss": "to know", "title": "יָדַע — to know"},    
    "vocab_הוא_16":    {"gloss": "he / it / that (m. sg.)"},
    "vocab_הן_94":     {"gloss": "behold / if / lo"},
    "vocab_הנה_55":    {"gloss": "behold! / see! / lo!"},
    "vocab_אני_33":    {"gloss": "I (first person)"},
    "vocab_עולם_129":  {"gloss": "eternity / forever / perpetual"},
    "vocab_עוד_68":    {"gloss": "again / still / yet / more"},
    "vocab_אחר_189":   {"gloss": "other / another / different"},
    "vocab_כי_5":      {"gloss": "for / because / that / when"},
    "vocab_על_3":      {"gloss": "upon / on / over / about"},
    "vocab_אל_2":      {"gloss": "to / toward / unto / against"},
    "vocab_אשר_4":     {"gloss": "who / which / that"},

    # ── Archaic English modernizations ──
    "vocab_ויקר_81":   {"hebrew": "קָרָא", "gloss": "to call / to proclaim", "title": "קָרָא — to call, to proclaim"},
    "vocab_וישם_107":  {"hebrew": "שִׂים", "gloss": "to put / to set / to appoint", "title": "שִׂים — to put, to set"},
    "vocab_ותלך_57":   {"hebrew": "הָלַךְ", "gloss": "to go / to walk", "title": "הָלַךְ — to go, to walk"},
    "vocab_ויכו_114":  {"hebrew": "נָכָה", "gloss": "to strike / to smite", "title": "נָכָה — to strike, to smite"},
    "vocab_ישלח_70":   {"hebrew": "שָׁלַח", "gloss": "to send / to stretch out", "title": "שָׁלַח — to send, to stretch out"},
    "vocab_מצא_99":    {"gloss": "to find / to meet / to discover"},
    "vocab_מות_73":    {"gloss": "to die / to be killed"},
    "vocab_נשא_75":    {"hebrew": "נָשָׂא", "gloss": "to lift / to carry / to forgive", "title": "נָשָׂא — to lift, to carry, to forgive"},
    "vocab_ישב_40":    {"gloss": "to sit / to dwell / to remain"},
    "vocab_עמד_111":   {"gloss": "to stand / to stand firm"},
    "vocab_עבד_41":    {"gloss": "servant / slave / worshiper"},
    "vocab_דבר_26":    {"hebrew": "דָּבָר", "gloss": "word / thing / matter", "title": "דָּבָר — word, thing, matter"},
    "vocab_צוית_69":   {"hebrew": "צִוָּה", "gloss": "to command / to appoint", "title": "צִוָּה — to command, to appoint"},
    "vocab_אמר_559":   {"gloss": "to say / to speak"},
    "vocab_וינס_349":  {"hebrew": "נוּס", "gloss": "to flee", "title": "נוּס — to flee"},
    "vocab_ויגש_425":  {"hebrew": "נָגַשׁ", "gloss": "to approach / to draw near", "title": "נָגַשׁ — to approach, to draw near"},
    "vocab_ויחן_278":  {"hebrew": "חָנָה", "gloss": "to encamp", "title": "חָנָה — to encamp"},
    "vocab_ויחר_441":  {"gloss": "to burn / to be angry"},
    "vocab_ויסע_277":  {"hebrew": "נָסַע", "gloss": "to journey / to set out", "title": "נָסַע — to journey, to set out"},
    "vocab_ויען_154":  {"hebrew": "עָנָה", "gloss": "to answer", "title": "עָנָה — to answer"},
    "vocab_ויטי_208":  {"hebrew": "נָטָה", "gloss": "to stretch out / to incline", "title": "נָטָה — to stretch out, to incline"},
    "vocab_ויתן_239":  {"hebrew": "שָׁחָה", "gloss": "to bow down / to worship", "title": "שָׁחָה — to bow down, to worship"},
    "vocab_נפלו_125":  {"gloss": "to fall / to lie down"},
    "vocab_תשמר_105":  {"hebrew": "שָׁמַר", "gloss": "to keep / to guard / to observe", "title": "שָׁמַר — to keep, to guard"},
    "vocab_תשאל_294":  {"hebrew": "שָׁאַל", "gloss": "to ask", "title": "שָׁאַל — to ask"},
    "vocab_תשכח_332":  {"hebrew": "שָׁכַח", "gloss": "to forget", "title": "שָׁכַח — to forget"},
    "vocab_ויגד_165":  {"hebrew": "נָגַד", "gloss": "to tell / to declare", "title": "נָגַד — to tell, to declare"},
    "vocab_הציל_223":  {"hebrew": "נָצַל", "gloss": "to deliver / to save", "title": "נָצַל — to deliver, to save"},
    "vocab_הקריב_207": {"hebrew": "קָרַב", "gloss": "to offer / to bring near", "title": "קָרַב — to offer, to bring near"},
    "vocab_ויקב_417":  {"hebrew": "קָבַץ", "gloss": "to gather / to assemble", "title": "קָבַץ — to gather, to assemble"},
    "vocab_וילכ_368":  {"gloss": "to capture / to take captive"},
    "vocab_וינס_349":  {"gloss": "to flee"},
    "vocab_ותבך_409":  {"hebrew": "בָּכָה", "gloss": "to weep", "title": "בָּכָה — to weep"},
    "vocab_ותשל_362":  {"hebrew": "שָׁלַךְ", "gloss": "to cast / to throw", "title": "שָׁלַךְ — to cast, to throw"},
    "vocab_יחדו_283":  {"hebrew": "יַחַד", "gloss": "together / unitedly", "title": "יַחַד — together"},
    "vocab_ישפט_244":  {"hebrew": "שָׁפַט", "gloss": "to judge", "title": "שָׁפַט — to judge"},
    "vocab_רדפו_358":  {"hebrew": "רָדַף", "gloss": "to pursue / to chase", "title": "רָדַף — to pursue, to chase"},
    "vocab_שפך_369":  {"hebrew": "שָׁפַךְ", "gloss": "to pour out / to shed", "title": "שָׁפַךְ — to pour out, to shed"},
    "vocab_שבר_293":  {"gloss": "to break / to shatter"},
    "vocab_שתה_266":  {"hebrew": "שָׁתָה", "gloss": "to drink", "title": "שָׁתָה — to drink"},
    "vocab_שכן_363":  {"hebrew": "שָׁכַן", "gloss": "to dwell / to settle", "title": "שָׁכַן — to dwell, to settle"},

    # ── Noun/adjective fixes ──
    "vocab_בנים_6":    {"hebrew": "בֵּן", "gloss": "son", "title": "בֵּן — son"},
    "vocab_בנות_82":   {"hebrew": "בַּת", "gloss": "daughter", "title": "בַּת — daughter"},
    "vocab_אשה_67":    {"gloss": "woman / wife"},
    "vocab_איש_14":    {"gloss": "man / husband / person"},
    "vocab_אדם_86":    {"gloss": "man / humanity / Adam"},
    "vocab_נפש_42":    {"gloss": "soul / life / living being"},
    "vocab_רוחי_108":  {"hebrew": "רוּחַ", "gloss": "wind / breath / spirit", "title": "רוּחַ — wind, breath, spirit"},
    "vocab_לבו_56":    {"hebrew": "לֵב", "gloss": "heart / mind / inner self", "title": "לֵב — heart, mind"},
    "vocab_דרך_85":    {"gloss": "way / road / path / conduct"},
    "vocab_מים_90":    {"gloss": "water / waters"},
    "vocab_אש_185":    {"gloss": "fire"},
    "vocab_אור_400":   {"gloss": "light"},
    "vocab_עיר_78":    {"hebrew": "עִיר", "gloss": "city / town", "title": "עִיר — city, town"},
    "vocab_ציון_248":  {"gloss": "Zion"},
    "vocab_תורה_263":  {"gloss": "law / instruction / Torah"},
    "vocab_חטאת_200":  {"hebrew": "חַטָּאת", "gloss": "sin / sin offering", "title": "חַטָּאת — sin, sin offering"},
    "vocab_משפט_130":  {"gloss": "judgment / justice / ordinance"},
    "vocab_צדק_312":   {"gloss": "righteousness / justice"},
    "vocab_חסד_145":   {"hebrew": "חֶסֶד", "gloss": "lovingkindness / steadfast love", "title": "חֶסֶד — lovingkindness, steadfast love"},
    "vocab_אמת_397":   {"gloss": "truth / faithfulness"},
    "vocab_שלום_220":  {"gloss": "peace / completeness / welfare"},
    "vocab_חיים_274":  {"hebrew": "חַיִּים", "gloss": "life", "title": "חַיִּים — life"},
    "vocab_חכמה_271":  {"gloss": "wisdom"},
    "vocab_כהנים_53":  {"hebrew": "כֹּהֵן", "gloss": "priest", "title": "כֹּהֵן — priest"},
    "vocab_נביא_149":  {"hebrew": "נָבִיא", "gloss": "prophet", "title": "נָבִיא — prophet"},
    "vocab_מלך_22":    {"gloss": "king"},
    "vocab_מלכה_450":  {"hebrew": "מַלְכָּה", "gloss": "queen", "title": "מַלְכָּה — queen"},
    "vocab_ממלכ_373":  {"gloss": "kingdom / reign"},
    "vocab_שמים_118":  {"hebrew": "שָׁמַיִם", "gloss": "heavens / sky", "title": "שָׁמַיִם — heavens, sky"},
    "vocab_ארץ_23":    {"hebrew": "אֶרֶץ", "gloss": "earth / land", "title": "אֶרֶץ — earth, land"},
    "vocab_ימים_184":  {"hebrew": "יָם", "gloss": "sea / west", "title": "יָם — sea, west"},
    "vocab_הרי_140":   {"hebrew": "הַר", "gloss": "mountain / hill", "title": "הַר — mountain, hill"},
    "vocab_בשר_161":   {"gloss": "flesh / body"},
    "vocab_דם_181":    {"hebrew": "דָּם", "gloss": "blood", "title": "דָּם — blood"},
    "vocab_עץ_143":    {"gloss": "tree / wood"},
    "vocab_אבן_204":   {"gloss": "stone"},
    "vocab_כסף_133":   {"gloss": "silver / money"},
    "vocab_זהב_131":   {"gloss": "gold"},

    # ── Numbers ──
    "vocab_אחד_44":    {"gloss": "one"},
    "vocab_שני_54":    {"hebrew": "שְׁנַיִם", "gloss": "two", "title": "שְׁנַיִם — two"},
    "vocab_שלש_98":    {"hebrew": "שָׁלוֹשׁ", "gloss": "three (f.)", "title": "שָׁלוֹשׁ — three"},
    "vocab_ארבע_170":  {"gloss": "four"},
    "vocab_חמש_164":   {"gloss": "five"},
    "vocab_שש_203":    {"gloss": "six"},
    "vocab_שבע_103":   {"gloss": "seven"},
    "vocab_שמנה_434":  {"gloss": "eight"},
    "vocab_תשע_":      {"gloss": "nine"},  # May not exist
    "vocab_עשר_211":   {"gloss": "ten"},
    "vocab_עשרה_97":   {"gloss": "ten (in compounds)"},
    "vocab_עשרים_142": {"gloss": "twenty"},
    "vocab_שלשים_254": {"gloss": "thirty"},
    "vocab_ארבעים_286":{"gloss": "forty"},
    "vocab_חמשים_285": {"gloss": "fifty"},
    "vocab_שבעים_383": {"gloss": "seventy"},
    "vocab_מאה_64":    {"hebrew": "מֵאָה", "gloss": "hundred", "title": "מֵאָה — hundred"},
    "vocab_אלף_80":    {"gloss": "thousand / clan"},

    # ── Proper names (mostly OK, just format fixes) ──
    "vocab_יהוה_1":    {"title": "יְהוָה — LORD (YHWH)"},
    "vocab_אלהי_11":   {"gloss": "God / gods / divine beings"},
    "vocab_ישרא_10":   {"gloss": "Israel"},
    "vocab_משה_31":    {"gloss": "Moses"},
    "vocab_אהרן_115":  {"gloss": "Aaron"},
    "vocab_דוד_28":    {"gloss": "David"},
    "vocab_שלמה_123":  {"gloss": "Solomon"},
    "vocab_יעקב_110":  {"gloss": "Jacob"},
    "vocab_יצחק_331":  {"gloss": "Isaac"},
    "vocab_אברה_210":  {"hebrew": "אַבְרָהָם", "gloss": "Abraham", "title": "אַבְרָהָם — Abraham"},
    "vocab_יוסף_153":  {"gloss": "Joseph"},
    "vocab_שמוא_246":  {"hebrew": "שְׁמוּאֵל", "gloss": "Samuel", "title": "שְׁמוּאֵל — Samuel"},
    "vocab_ירמי_219":  {"hebrew": "יִרְמְיָהוּ", "gloss": "Jeremiah", "title": "יִרְמְיָהוּ — Jeremiah"},
    "vocab_יהוש_152":  {"hebrew": "יְהוֹשֻׁעַ", "gloss": "Joshua", "title": "יְהוֹשֻׁעַ — Joshua"},
    "vocab_שאול_91":   {"gloss": "Saul"},
    "vocab_דן_483":    {"gloss": "Dan"},
    "vocab_גד_388":    {"gloss": "Gad"},
    "vocab_אדום_327":  {"gloss": "Edom"},
    "vocab_מואב_188":  {"gloss": "Moab"},
    "vocab_עמון_270":  {"gloss": "Ammon"},
    "vocab_מצרי_62":   {"hebrew": "מִצְרַיִם", "gloss": "Egypt", "title": "מִצְרַיִם — Egypt"},
    "vocab_בבל_132":   {"gloss": "Babylon"},
    "vocab_אשור_215":  {"gloss": "Assyria"},
    "vocab_ארם_255":   {"gloss": "Aram / Syria"},
    "vocab_ירוש_84":   {"hebrew": "יְרוּשָׁלַיִם", "gloss": "Jerusalem", "title": "יְרוּשָׁלַיִם — Jerusalem"},
    "vocab_ציון_248":  {"gloss": "Zion"},
    "vocab_פרעה_134":  {"gloss": "Pharaoh"},
    "vocab_עשו_336":   {"gloss": "Esau"},
    "vocab_לבן_361":   {"hebrew": "לָבָן", "gloss": "Laban", "title": "לָבָן — Laban"},
    "vocab_בלעם_461":  {"gloss": "Balaam"},
    "vocab_גלעד_355":  {"gloss": "Gilead"},
    "vocab_כנען_313":  {"gloss": "Canaan"},
    "vocab_מדין_489":  {"gloss": "Midian"},
    "vocab_ראוב_384":  {"hebrew": "רְאוּבֵן", "gloss": "Reuben", "title": "רְאוּבֵן — Reuben"},
    "vocab_בנימ_245":  {"hebrew": "בִּנְיָמִין", "gloss": "Benjamin", "title": "בִּנְיָמִין — Benjamin"},
    "vocab_אפרי_193":  {"hebrew": "אֶפְרַיִם", "gloss": "Ephraim", "title": "אֶפְרַיִם — Ephraim"},
    "vocab_מנשה_258":  {"gloss": "Manasseh"},
    "vocab_יהוד_36":   {"hebrew": "יְהוּדָה", "gloss": "Judah", "title": "יְהוּדָה — Judah"},

    # ── Inflected verb forms → lemmas ──
    "vocab_אהבת_202":  {"hebrew": "אָהַב", "gloss": "to love", "title": "אָהַב — to love"},
    "vocab_אדרש_281":  {"hebrew": "דָּרַשׁ", "gloss": "to seek / to inquire", "title": "דָּרַשׁ — to seek, to inquire"},
    "vocab_בנה_167":   {"hebrew": "בָּנָה", "gloss": "to build", "title": "בָּנָה — to build"},
    "vocab_בחרו_196":  {"hebrew": "בָּחַר", "gloss": "to choose", "title": "בָּחַר — to choose"},
    "vocab_זכרת_160":  {"hebrew": "זָכַר", "gloss": "to remember", "title": "זָכַר — to remember"},
    "vocab_חטאת_156":  {"hebrew": "חָטָא", "gloss": "to sin", "title": "חָטָא — to sin"},
    "vocab_יכלו_157":  {"hebrew": "יָכֹל", "gloss": "to be able", "title": "יָכֹל — to be able"},
    "vocab_כרת_199":   {"hebrew": "כָּרַת", "gloss": "to cut / to make a covenant", "title": "כָּרַת — to cut, to covenant"},
    "vocab_מלא_459":   {"hebrew": "מָלֵא", "gloss": "to be full / to fill", "title": "מָלֵא — to be full, to fill"},
    "vocab_מלכו_187":  {"hebrew": "מָלַךְ", "gloss": "to reign / to become king", "title": "מָלַךְ — to reign, to become king"},
    "vocab_נגלו_243":  {"hebrew": "גָּלָה", "gloss": "to uncover / to reveal", "title": "גָּלָה — to uncover, to reveal"},
    "vocab_נטה_208":   {"gloss": "to stretch out / to extend"},
    "vocab_נסבו_324":  {"hebrew": "סָבַב", "gloss": "to surround / to go around", "title": "סָבַב — to surround"},
    "vocab_עלת_197":   {"hebrew": "עָלָה", "gloss": "to go up / to ascend", "title": "עָלָה — to go up, to ascend"},
    "vocab_פקד_168":   {"hebrew": "פָּקַד", "gloss": "to visit / to appoint / to number", "title": "פָּקַד — to visit, to appoint"},
    "vocab_קדש_119":   {"hebrew": "קָדֹשׁ", "gloss": "holy / set apart", "title": "קָדֹשׁ — holy, set apart"},
    "vocab_שמח_309":   {"hebrew": "שָׂמַח", "gloss": "to rejoice", "title": "שָׂמַח — to rejoice"},
}

# ── Archaic/weird gloss auto-fixes ──
# These patterns will be caught during practice item patching
ARCHAIC_MAP = {
    "Saith": "says / said",
    "Thither": "there",
    "Art": "you are (m. sg.)",
    "Forth": "go forth / come out",
    "Slept": "with",  # Already handled above for עמה
    "Woof": "or",
    "Rebellest": "",  # handled individually
    "Procured": "",   # handled individually
    "Pare": "midst / among",  # בתוך
    "Chronicles": "they",
    "Possess": "you (m. pl.)",
    "Sibbechai": "then",
    "Tacklings": "",  
    "Purtenance": "", 
    "LORD": "LORD", # OK
    "GOD": "God", # OK
    "Behold": "behold", # OK
}

def fix_lemma_gloss_source():
    """Fix the source lemma_gloss table so future rebuilds start clean."""
    if not SCRIPTURE_DB.exists():
        print("  SKIP: scripture.db not found")
        return

    conn = sqlite3.connect(str(SCRIPTURE_DB))
    patches = [
        ('3808', 'not / no'),
        ('6213 a', 'to make / to do'),
        ('4480 a', 'from'),
        ('559', 'to say / said'),
        ('5414', 'to give'),
        ('7200', 'to see'),
        ('8085', 'to hear'),
        ('3045', 'to know'),
        ('3318', 'to go out / to come forth'),
        ('7725', 'to return / to repent'),
        ('3947', 'to take'),
        ('559', 'to say / said'),
        ('1961', 'to be / to become'),
        ('1696', 'to speak'),
        ('935', 'to come / to go / to bring'),
        ('6213 a', 'to make / to do'),
        ('376', 'man / husband'),
        ('376', 'man / husband / person'),
        ('120', 'man / humanity'),
        ('802', 'woman / wife'),
        ('1121 a', 'son'),
        ('1323', 'daughter'),
        ('1004 b', 'house / household'),
        ('5704', 'until / as far as'),
        ('6440', 'face / presence'),
        ('8033', 'there'),
        ('859 a', 'you (m. sg.)'),
        ('859', 'you (m. sg.)'),
        ('2088', 'this (m. sg.)'),
        ('2063', 'this (f. sg.)'),
        ('518 a', 'if / whether'),
        ('5973 a', 'with'),
        ('5973 b', 'with'),
        ('3808', 'not / no'),
        ('3651 c', 'so / thus / therefore'),
        ('3541', 'thus / so'),
        ('1571', 'also / even'),
        ('369', 'there is not / nothing'),
        ('389', 'surely / only / but'),
        ('7535', 'only / but'),
        ('6435', 'lest / otherwise'),
        ('227', 'then / at that time'),
        ('310 a', 'after / behind'),
        ('996', 'between / among'),
        ('4616', 'for the sake of / in order that'),
        ('5769', 'eternity / forever'),
        ('3966', 'very / exceedingly'),
        ('3282', 'because / therefore'),
        ('5674', 'to pass over / to cross'),
        ('398', 'to eat'),
        ('3045', 'to know'),
        ('1931', 'he / it / that'),
        ('2005', 'behold / if'),
        ('2009', 'behold! / lo!'),
        ('589', 'I'),
        ('595', 'I'),
        ('5750', 'again / still / yet'),
        ('312', 'other / another'),
        ('3588 a', 'for / because / that / when'),
        ('5921 a', 'upon / on / over / about'),
        ('413', 'to / toward / unto'),
        ('834 a', 'who / which / that'),
        ('3068', 'LORD (YHWH)'),
        ('430', 'God / gods'),
        ('3478', 'Israel'),
        ('4872', 'Moses'),
        ('175', 'Aaron'),
        ('1732', 'David'),
        ('8010', 'Solomon'),
        ('3290', 'Jacob'),
        ('3327', 'Isaac'),
        ('85', 'Abraham'),
        ('3130', 'Joseph'),
        ('8050', 'Samuel'),
        ('3414', 'Jeremiah'),
        ('3091', 'Joshua'),
        ('7586', 'Saul'),
        ('1835', 'Dan'),
        ('1410', 'Gad'),
        ('123', 'Edom'),
        ('4124', 'Moab'),
        ('5983', 'Ammon'),
        ('4714', 'Egypt'),
        ('894', 'Babylon'),
        ('804', 'Assyria'),
        ('758', 'Aram / Syria'),
        ('3389', 'Jerusalem'),
        ('6726', 'Zion'),
        ('6547', 'Pharaoh'),
        ('6215', 'Esau'),
        ('3837', 'Laban'),
        ('1109', 'Balaam'),
        ('1568', 'Gilead'),
        ('3667', 'Canaan'),
        ('4080', 'Midian'),
        ('7205', 'Reuben'),
        ('1144', 'Benjamin'),
        ('669', 'Ephraim'),
        ('4519', 'Manasseh'),
        ('3063', 'Judah'),
        ('157', 'to love'),
        ('1875', 'to seek / to inquire'),
        ('1129', 'to build'),
        ('977', 'to choose'),
        ('2142', 'to remember'),
        ('2398', 'to sin'),
        ('3201', 'to be able'),
        ('3772', 'to cut / to covenant'),
        ('4390', 'to be full / to fill'),
        ('4427', 'to reign'),
        ('1540', 'to uncover / to reveal'),
        ('5186', 'to stretch out'),
        ('5437', 'to surround'),
        ('5927', 'to go up / to ascend'),
        ('6485', 'to visit / to appoint'),
        ('6918', 'holy / set apart'),
        ('8055', 'to rejoice'),
        ('1242', 'to dread / to fear'),
        ('3427', 'to sit / to dwell'),
        ('5975', 'to stand'),
        ('5650', 'servant / worshiper'),
        ('1697', 'word / thing / matter'),
        ('6680', 'to command'),
        ('5127', 'to flee'),
        ('5066', 'to approach'),
        ('2583', 'to encamp'),
        ('2734', 'to burn / to be angry'),
        ('5265', 'to journey'),
        ('6030', 'to answer'),
        ('5186', 'to stretch out'),
        ('7812', 'to bow down / to worship'),
        ('5307', 'to fall'),
        ('8104', 'to keep / to guard'),
        ('7592', 'to ask'),
        ('7911', 'to forget'),
        ('5046', 'to tell / to declare'),
        ('5337', 'to deliver / to save'),
        ('7126', 'to approach / to offer'),
        ('6908', 'to gather'),
        ('1058', 'to weep'),
        ('7993', 'to cast / to throw'),
        ('8199', 'to judge'),
        ('7291', 'to pursue'),
        ('8210', 'to pour out'),
        ('7665', 'to break'),
        ('8354', 'to drink'),
        ('7931', 'to dwell'),
        ('6828', 'to know / to experience'),
        ('802', 'woman / wife'),
        ('376', 'man / husband'),
        ('120', 'humanity'),
        ('5315', 'soul / life'),
        ('7307', 'wind / breath / spirit'),
        ('3820 a', 'heart / mind'),
        ('1870', 'way / road / path'),
        ('4325', 'water'),
        ('784', 'fire'),
        ('216', 'light'),
        ('5892 b', 'city / town'),
        ('8451', 'law / instruction / Torah'),
        ('2403', 'sin / sin offering'),
        ('4941', 'judgment / justice'),
        ('6664', 'righteousness'),
        ('2617', 'lovingkindness / steadfast love'),
        ('571', 'truth / faithfulness'),
        ('7965', 'peace / completeness'),
        ('2416', 'life'),
        ('2451', 'wisdom'),
        ('3548', 'priest'),
        ('5030', 'prophet'),
        ('4428', 'king'),
        ('4438', 'kingdom / reign'),
        ('8064', 'heavens / sky'),
        ('776', 'earth / land'),
        ('3220', 'sea / west'),
        ('2022', 'mountain'),
        ('1320', 'flesh'),
        ('1818', 'blood'),
        ('6086', 'tree / wood'),
        ('68', 'stone'),
        ('3701', 'silver / money'),
        ('2091', 'gold'),
        ('259', 'one'),
        ('8147', 'two'),
        ('7969', 'three'),
        ('702', 'four'),
        ('2568', 'five'),
        ('8337', 'six'),
        ('7651', 'seven'),
        ('8083', 'eight'),
        ('8672', 'ten'),
        ('6235', 'ten (in compounds)'),
        ('6242', 'twenty'),
        ('7970', 'thirty'),
        ('705', 'forty'),
        ('2572', 'fifty'),
        ('7657', 'seventy'),
        ('3967', 'hundred'),
        ('505', 'thousand'),
        ('3069', 'LORD (YHWH)'),
    ]
    
    updated = 0
    for lemma, gloss in patches:
        existing = conn.execute("SELECT english_gloss FROM lemma_gloss WHERE lemma=?", (lemma,)).fetchone()
        if existing and existing[0] != gloss:
            conn.execute("UPDATE lemma_gloss SET english_gloss=? WHERE lemma=?", (gloss, lemma))
            updated += 1
            print(f"  PATCH lemma_gloss {lemma}: '{existing[0]}' → '{gloss}'")
    
    conn.commit()
    conn.close()
    print(f"  Updated {updated} lemma_gloss entries")


def fix_vocabulary_in_memorize():
    """Fix hebrew_nodes, hebrew_lessons, and hebrew_practice_items."""
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    
    fixed_nodes = 0
    fixed_lessons = 0
    fixed_practice = 0
    
    for node_id, corr in CORRECTIONS.items():
        # Check node exists
        node = conn.execute("SELECT * FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
        if not node:
            print(f"  SKIP {node_id}: not found")
            continue
        
        old_title = node['title']
        old_desc = node['description'] or ''
        
        # Determine new Hebrew word and gloss
        new_hebrew = corr.get('hebrew')
        new_gloss = corr.get('gloss')
        new_title = corr.get('title')
        
        # Parse old title: "העברי — English" or similar
        old_parts = old_title.split(' — ', 1)
        old_hebrew = old_parts[0] if len(old_parts) > 1 else ''
        old_gloss = old_parts[1] if len(old_parts) > 1 else old_title
        
        # Use existing hebrew if not changing
        if not new_hebrew:
            new_hebrew = old_hebrew
        
        # Generate title from hebrew + gloss if not explicitly set
        if not new_title:
            if new_gloss:
                new_title = f"{new_hebrew} — {new_gloss}"
            else:
                new_title = old_title  # no change
        
        # Update hebrew_nodes
        conn.execute("UPDATE hebrew_nodes SET title=? WHERE id=?", (new_title, node_id))
        
        # Update description if gloss changed (strip old gloss from desc)
        if new_gloss and old_gloss and old_gloss != new_gloss:
            # Description often starts with the gloss — clean it
            new_desc = old_desc
            if old_desc.lower().startswith(old_gloss.lower()):
                new_desc = new_gloss + old_desc[len(old_gloss):]
            conn.execute("UPDATE hebrew_nodes SET description=? WHERE id=?", (new_desc, node_id))
        
        fixed_nodes += 1
        
        # Update hebrew_lessons content_json
        lesson_row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
        if lesson_row:
            try:
                content = json.loads(lesson_row['content_json'])
            except (json.JSONDecodeError, TypeError):
                content = {}
            
            changed = False
            if new_hebrew and content.get('hebrew') and content['hebrew'] != new_hebrew:
                content['hebrew'] = new_hebrew
                changed = True
            if new_gloss and content.get('gloss') and content['gloss'] != new_gloss:
                content['gloss'] = new_gloss
                changed = True
            if content.get('title') and new_title and content['title'] != new_title:
                content['title'] = new_title
                changed = True
            
            if changed:
                conn.execute("UPDATE hebrew_lessons SET content_json=? WHERE node_id=?", 
                           (json.dumps(content, ensure_ascii=False), node_id))
                fixed_lessons += 1
        
        # Update practice items
        items = conn.execute("""
            SELECT id, question_type, question_text, correct_answer, options_json
            FROM hebrew_practice_items WHERE node_id=?
        """, (node_id,)).fetchall()
        
        for item in items:
            qtext = item['question_text']
            cans = item['correct_answer']
            opts = item['options_json']
            changed = False
            
            # Fix question text that references the old gloss
            if old_gloss and new_gloss and old_gloss != new_gloss:
                # "What does 'X' mean? → answer: OLD_GLOSS"
                if cans == old_gloss:
                    conn.execute("UPDATE hebrew_practice_items SET correct_answer=? WHERE id=?", 
                               (new_gloss, item['id']))
                    changed = True
                    fixed_practice += 1
                
                # "What does 'X' mean?" → update answer reference
                if qtext.endswith(f"'{old_gloss}'?") or old_gloss in qtext:
                    new_qtext = qtext.replace(old_gloss, new_gloss)
                    if new_qtext != qtext:
                        conn.execute("UPDATE hebrew_practice_items SET question_text=? WHERE id=?", 
                                   (new_qtext, item['id']))
                        changed = True
                
                # Update options_json if it contains the old gloss
                if opts:
                    try:
                        opts_list = json.loads(opts)
                        if isinstance(opts_list, list):
                            new_opts = [new_gloss if o == old_gloss else o for o in opts_list]
                            if new_opts != opts_list:
                                conn.execute("UPDATE hebrew_practice_items SET options_json=? WHERE id=?", 
                                           (json.dumps(new_opts, ensure_ascii=False), item['id']))
                                changed = True
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            # Update question text and answers that reference old Hebrew form
            if new_hebrew and new_hebrew != old_hebrew:
                # Questions containing the old Hebrew word
                if old_hebrew in qtext:
                    new_qtext = qtext.replace(old_hebrew, new_hebrew)
                    conn.execute("UPDATE hebrew_practice_items SET question_text=? WHERE id=?", 
                               (new_qtext, item['id']))
                    changed = True
                # Correct answer matching old Hebrew
                if cans == old_hebrew:
                    conn.execute("UPDATE hebrew_practice_items SET correct_answer=? WHERE id=?", 
                               (new_hebrew, item['id']))
                    changed = True
                # Options containing old Hebrew
                if opts:
                    try:
                        opts_list = json.loads(opts)
                        if isinstance(opts_list, list):
                            new_opts = [new_hebrew if o == old_hebrew else o for o in opts_list]
                            if new_opts != opts_list:
                                conn.execute("UPDATE hebrew_practice_items SET options_json=? WHERE id=?", 
                                           (json.dumps(new_opts, ensure_ascii=False), item['id']))
                                changed = True
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            # Fix explanation field
            if changed:
                expl = conn.execute("SELECT explanation FROM hebrew_practice_items WHERE id=?", (item['id'],)).fetchone()
                if expl and expl[0]:
                    new_expl = expl[0]
                    if old_gloss and new_gloss and old_gloss in new_expl:
                        new_expl = new_expl.replace(old_gloss, new_gloss)
                    if new_hebrew and old_hebrew and old_hebrew in new_expl:
                        new_expl = new_expl.replace(old_hebrew, new_hebrew)
                    if new_expl != expl[0]:
                        conn.execute("UPDATE hebrew_practice_items SET explanation=? WHERE id=?", 
                                   (new_expl, item['id']))
        
        if old_title != new_title:
            print(f"  FIX {node_id}: '{old_title}' → '{new_title}'")
    
    conn.commit()
    conn.close()
    print(f"\n  Fixed {fixed_nodes} nodes, {fixed_lessons} lessons, {fixed_practice}+ practice items")


def main():
    print("=== Fixing source lemma_gloss ===")
    fix_lemma_gloss_source()
    
    print("\n=== Fixing vocabulary in memorize.db ===")
    fix_vocabulary_in_memorize()
    
    print("\n✓ Done!")


if __name__ == '__main__':
    main()
