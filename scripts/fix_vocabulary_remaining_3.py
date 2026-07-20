#!/usr/bin/env python3
"""
Third pass: fix remaining issues not caught by passes 1 and 2.

1. Entries with Strong's-style descriptions
2. Entries with wrong glosses from obscure Strong's mappings
3. Remaining parenthetical old-gloss patterns
"""

import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"

# ── Additional gloss corrections for entries with wrong/noisy glosses ──
ADDITIONAL_CORRECTIONS = {
    # Completely wrong glosses from Strong's
    "vocab_אבדה_276":  {"hebrew": "אָבַד", "gloss": "to perish / to be lost", "title": "אָבַד — to perish, to be lost"},
    "vocab_און_354":   {"hebrew": "אוֹן", "gloss": "vigor / wealth / sorrow", "title": "אוֹן — vigor, wealth"},
    "vocab_אזנו_289":  {"hebrew": "אֹזֶן", "gloss": "ear", "title": "אֹזֶן — ear"},
    "vocab_אחאב_347":  {"hebrew": "אַחְאָב", "gloss": "Ahab", "title": "אַחְאָב — Ahab"},
    "vocab_אחיו_65":   {"hebrew": "אָח", "gloss": "brother", "title": "אָח — brother"},
    "vocab_אחתי_287":  {"hebrew": "אָחוֹת", "gloss": "sister", "title": "אָחוֹת — sister"},
    "vocab_איבי_124":  {"hebrew": "אֹיֵב", "gloss": "enemy / foe", "title": "אֹיֵב — enemy, foe"},
    "vocab_איל_353":   {"hebrew": "אַיִל", "gloss": "ram / leader / oak", "title": "אַיִל — ram, leader"},
    "vocab_איעצ_438":  {"hebrew": "עֵצָה", "gloss": "counsel / advice", "title": "עֵצָה — counsel, advice"},
    "vocab_אלהא_374":  {"hebrew": "אֱלָהּ", "gloss": "god (Aramaic)", "title": "אֱלָהּ — god (Aramaic)"},
    "vocab_אלוה_447":  {"hebrew": "אֱלוֹהַּ", "gloss": "God / god", "title": "אֱלוֹהַּ — God"},
    "vocab_אליה_414":  {"hebrew": "אֵלִיָּהוּ", "gloss": "Elijah", "title": "אֵלִיָּהוּ — Elijah"},
    "vocab_אלעז_436":  {"hebrew": "אֶלְעָזָר", "gloss": "Eleazar", "title": "אֶלְעָזָר — Eleazar"},
    "vocab_אמה_249":   {"hebrew": "אַמָּה", "gloss": "cubit / forearm", "title": "אַמָּה — cubit"},
    "vocab_אנחנ_301":  {"hebrew": "אֲנַחְנוּ", "gloss": "we", "title": "אֲנַחְנוּ — we"},
    "vocab_אסתר_421":  {"hebrew": "אֶסְתֵּר", "gloss": "Esther", "title": "אֶסְתֵּר — Esther"},
    "vocab_אף_275":    {"hebrew": "אַף", "gloss": "also / even / nose", "title": "אַף — also, even"},
    "vocab_אצלה_466":  {"hebrew": "אֵצֶל", "gloss": "beside / near / with", "title": "אֵצֶל — beside, near"},
    "vocab_ארבע_286":  {"hebrew": "אַרְבָּעִים", "gloss": "forty", "title": "אַרְבָּעִים — forty"},
    "vocab_ארון_230":  {"hebrew": "אָרוֹן", "gloss": "ark / chest / coffin", "title": "אָרוֹן — ark, chest"},
    "vocab_ארך_345":   {"hebrew": "אֹרֶךְ", "gloss": "length", "title": "אֹרֶךְ — length"},
    "vocab_אשית_382":  {"hebrew": "אָשִׁים", "gloss": "Dimon (place)", "title": "אָשִׁים — Dimon"},
    "vocab_בבקר_290":  {"hebrew": "בֹּקֶר", "gloss": "morning", "title": "בֹּקֶר — morning"},
    "vocab_בגדי_186":  {"hebrew": "בֶּגֶד", "gloss": "garment / clothing / treachery", "title": "בֶּגֶד — garment, clothing"},
    "vocab_בטח_306":   {"hebrew": "בָּטַח", "gloss": "to trust / to be confident", "title": "בָּטַח — to trust, to be confident"},
    "vocab_בעדו_348":  {"hebrew": "חַלּוֹן", "gloss": "window", "title": "חַלּוֹן — window"},
    "vocab_בעת_252":   {"gloss": "time / moment"},
    "vocab_ברוך_144":  {"hebrew": "בָּרוּךְ", "gloss": "blessed", "title": "בָּרוּךְ — blessed"},
    "vocab_ברית_136":  {"hebrew": "בְּרִית", "gloss": "covenant / treaty", "title": "בְּרִית — covenant"},
    "vocab_גבול_194":  {"gloss": "border / boundary / territory"},
    "vocab_גבר_267":   {"hebrew": "גִּבּוֹר", "gloss": "mighty man / warrior", "title": "גִּבּוֹר — mighty man, warrior"},
    "vocab_גדלה_344":  {"gloss": "to be great / to be magnified"},
    "vocab_דד_493":    {"hebrew": "דּוֹד", "gloss": "beloved / uncle", "title": "דּוֹד — beloved, uncle"},
    "vocab_דהוא_147":  {"hebrew": "דָּנִיֵּאל", "gloss": "Daniel", "title": "דָּנִיֵּאל — Daniel"},
    "vocab_דנה_492":   {"hebrew": "דָּנָה", "gloss": "judgment / interpretation", "title": "דָּנָה — judgment, interpretation"},
    "vocab_דעת_471":   {"hebrew": "דַּעַת", "gloss": "knowledge", "title": "דַּעַת — knowledge"},
    "vocab_האדמ_241":  {"gloss": "the ground / the land"},
    "vocab_האמי_325":  {"hebrew": "אָמַן", "gloss": "to be faithful / to trust", "title": "אָמַן — to be faithful"},
    "vocab_האסף_273":  {"hebrew": "אָסַף", "gloss": "to gather / to assemble", "title": "אָסַף — to gather"},
    "vocab_הבל_478":   {"hebrew": "הֶבֶל", "gloss": "vapor / vanity / breath", "title": "הֶבֶל — vapor, vanity"},
    "vocab_הגוי_137":  {"hebrew": "גּוֹי", "gloss": "nation / people (pl. Gentiles)", "title": "גּוֹי — nation, people"},
    "vocab_הוחל_308":  {"hebrew": "חָלַל", "gloss": "to profane / to defile", "title": "חָלַל — to profane"},
    "vocab_החצר_440":  {"hebrew": "חָצֵר", "gloss": "court / courtyard", "title": "חָצֵר — court, courtyard"},
    "vocab_היהו_453":  {"hebrew": "יְהוּדִי", "gloss": "Jew / Jewish", "title": "יְהוּדִי — Jew, Jewish"},
    "vocab_הירד_195":  {"gloss": "the Jordan"},
    "vocab_הכנע_479":  {"gloss": "the Canaanite / merchant"},
    "vocab_הלבי_391":  {"gloss": "to clothe / to be clothed"},
    "vocab_הלוי_175":  {"hebrew": "לֵוִי", "gloss": "Levi / Levite", "title": "לֵוִי — Levi, Levite"},
    "vocab_המון_470":  {"gloss": "multitude / tumult / crowd"},
    "vocab_המזב_159":  {"hebrew": "מִזְבֵּחַ", "gloss": "altar", "title": "מִזְבֵּחַ — altar"},
    "vocab_המחנ_340":  {"gloss": "the camp / the army"},
    "vocab_המלט_446":  {"hebrew": "מָלַט", "gloss": "to escape / to deliver", "title": "מָלַט — to escape"},
    "vocab_המקו_214":  {"hebrew": "מָקוֹם", "gloss": "place", "title": "מָקוֹם — place"},
    "vocab_המשכ_357":  {"hebrew": "מִשְׁכָּן", "gloss": "tabernacle / dwelling place", "title": "מִשְׁכָּן — tabernacle"},
    "vocab_הנבי_149":  {"hebrew": "נָבִיא", "gloss": "prophet", "title": "נָבִיא — prophet"},
    "vocab_העדה_339":  {"hebrew": "עֵדָה", "gloss": "congregation / assembly", "title": "עֵדָה — congregation"},
    "vocab_הערב_408":  {"gloss": "evening / mixed multitude"},
    "vocab_הפכי_433":  {"hebrew": "הָפַךְ", "gloss": "to turn / to overthrow", "title": "הָפַךְ — to turn, to overthrow"},
    "vocab_הקרי_207":  {"hebrew": "קָרֵב", "gloss": "to approach / to offer", "title": "קָרֵב — to approach"},
    "vocab_הראש_262":  {"gloss": "the first / former"},
    "vocab_הרחק_463":  {"hebrew": "רָחוֹק", "gloss": "far / distant", "title": "רָחוֹק — far, distant"},
    "vocab_הרימ_226":  {"hebrew": "הֵרִים", "gloss": "to lift up / to offer", "title": "הֵרִים — to lift up"},
    "vocab_השבע_216":  {"gloss": "to swear / to take an oath"},
    "vocab_השדה_213":  {"hebrew": "שָׂדֶה", "gloss": "field / open country", "title": "שָׂדֶה — field"},
    "vocab_השלי_367":  {"gloss": "third / the third"},
    "vocab_השמה_455":  {"gloss": "desolate / ruined"},
    "vocab_השמש_300":  {"hebrew": "שֶׁמֶשׁ", "gloss": "sun", "title": "שֶׁמֶשׁ — sun"},
    "vocab_השני_247":  {"gloss": "second / the second"},
    "vocab_ואקב_305":  {"hebrew": "קָבַר", "gloss": "to bury", "title": "קָבַר — to bury"},
    "vocab_וביו_377":  {"gloss": "in the day of / when"},
    "vocab_והלו_389":  {"gloss": "and the Levites"},
    "vocab_והקט_416":  {"hebrew": "קְטֹרֶת", "gloss": "incense", "title": "קְטֹרֶת — incense"},
    "vocab_וישת_239":  {"hebrew": "שָׁחָה", "gloss": "to bow down / to worship", "title": "שָׁחָה — to bow down, to worship"},
    "vocab_וישח_473":  {"hebrew": "שָׁחַט", "gloss": "to slaughter / to kill", "title": "שָׁחַט — to slaughter"},
    "vocab_ויתפ_484":  {"hebrew": "פָּלַל", "gloss": "to pray / to intervene", "title": "פָּלַל — to pray, to intervene"},
    "vocab_ויתר_418":  {"hebrew": "יָתַר", "gloss": "to remain / to be left over", "title": "יָתַר — to remain"},
    "vocab_ולבנ_361":  {"gloss": "and the sons of"},
    "vocab_ונלח_403":  {"hebrew": "לָחַם", "gloss": "to fight / to do battle", "title": "לָחַם — to fight"},
    "vocab_זבח_269":   {"hebrew": "זֶבַח", "gloss": "sacrifice", "title": "זֶבַח — sacrifice"},
    "vocab_זכר_432":   {"gloss": "male / masculine"},
    "vocab_זרה_411":   {"gloss": "strange / foreign / illicit"},
    "vocab_זרע_222":   {"gloss": "seed / offspring / descendants"},
    "vocab_חזקי_237":  {"gloss": "Hezekiah"},
    "vocab_חילם_172":  {"hebrew": "חַיִל", "gloss": "strength / army / wealth", "title": "חַיִל — strength, army, wealth"},
    "vocab_חלקם_460":  {"hebrew": "חֵלֶק", "gloss": "portion / share / allotment", "title": "חֵלֶק — portion, share"},
    "vocab_חמה_424":   {"gloss": "wall / heat / anger / venom"},
    "vocab_חמס_491":   {"hebrew": "חָמָס", "gloss": "violence / wrong", "title": "חָמָס — violence"},
    "vocab_חמת_330":   {"hebrew": "חֵמָה", "gloss": "heat / rage / fury", "title": "חֵמָה — heat, fury"},
    "vocab_חן_387":    {"gloss": "grace / favor / charm"},
    "vocab_חפץ_375":   {"hebrew": "חָפֵץ", "gloss": "to delight in / to desire", "title": "חָפֵץ — to delight in, to desire"},
    "vocab_חק_399":    {"hebrew": "חֹק", "gloss": "statute / decree / ordinance", "title": "חֹק — statute, ordinance"},
    "vocab_חקות_428":  {"gloss": "statute / decree"},
    "vocab_חשך_490":   {"hebrew": "חֹשֶׁךְ", "gloss": "darkness", "title": "חֹשֶׁךְ — darkness"},
    "vocab_טהרה_381":  {"hebrew": "טָהוֹר", "gloss": "clean / pure", "title": "טָהוֹר — clean, pure"},
    "vocab_טמא_307":   {"gloss": "unclean / defiled"},
    "vocab_יהונ_427":  {"gloss": "Jonathan"},
    "vocab_יהוש_410":  {"gloss": "Jehoshaphat"},
    "vocab_יהרג_297":  {"hebrew": "הָרַג", "gloss": "to kill / to slay", "title": "הָרַג — to kill, to slay"},
    "vocab_יואב_251":  {"gloss": "Joab"},
    "vocab_יורש_303":  {"hebrew": "יָרַשׁ", "gloss": "to possess / to inherit", "title": "יָרַשׁ — to possess, to inherit"},
    "vocab_יין_398":   {"gloss": "wine"},
    "vocab_ימין_320":  {"gloss": "right hand / south"},
    "vocab_ימשל_449":  {"hebrew": "מָשַׁל", "gloss": "to rule / to have dominion", "title": "מָשַׁל — to rule"},
    "vocab_ינחמ_457":  {"hebrew": "נָחַם", "gloss": "to comfort / to console", "title": "נָחַם — to comfort"},
    "vocab_יספר_404":  {"hebrew": "סָפַר", "gloss": "to count / to recount / to tell", "title": "סָפַר — to count, to tell"},
    "vocab_יעזב_183":  {"hebrew": "עָזַב", "gloss": "to abandon / to forsake", "title": "עָזַב — to abandon, to forsake"},
    "vocab_יעיר_431":  {"hebrew": "עוּר", "gloss": "to rouse / to awaken", "title": "עוּר — to rouse, to awaken"},
    "vocab_יעלה_61":   {"hebrew": "עָלָה", "gloss": "to go up / to ascend", "title": "עָלָה — to go up, to ascend"},
    "vocab_ירב_190":   {"hebrew": "רָבָה", "gloss": "to be many / to increase", "title": "רָבָה — to be many, to increase"},
    "vocab_ירבע_315":  {"gloss": "Jeroboam"},
    "vocab_יש_279":    {"hebrew": "יֵשׁ", "gloss": "there is / there are", "title": "יֵשׁ — there is, there are"},
    "vocab_ישכב_272":  {"hebrew": "שָׁכַב", "gloss": "to lie down / to sleep", "title": "שָׁכַב — to lie down, to sleep"},
    "vocab_יתבש_292":  {"hebrew": "בּוֹשׁ", "gloss": "to be ashamed", "title": "בּוֹשׁ — to be ashamed"},
    "vocab_כבד_338":   {"gloss": "heavy / glorious / honorable / weighty"},
    "vocab_כבוד_206":  {"hebrew": "כָּבוֹד", "gloss": "glory / honor / weight", "title": "כָּבוֹד — glory, honor"},
    "vocab_כבשי_386":  {"hebrew": "כֶּבֶשׂ", "gloss": "lamb", "title": "כֶּבֶשׂ — lamb"},
    "vocab_כחה_314":   {"hebrew": "כֹּחַ", "gloss": "strength / power / ability", "title": "כֹּחַ — strength, power"},
    "vocab_כלי_151":   {"gloss": "vessel / utensil / weapon / instrument"},
    "vocab_כמנו_217":  {"gloss": "like / as / according to"},
    "vocab_כנף_360":   {"gloss": "wing / edge / extremity"},
    "vocab_כסאו_268":  {"hebrew": "כִּסֵּא", "gloss": "throne / seat", "title": "כִּסֵּא — throne"},
    "vocab_כסתה_326":  {"hebrew": "כָּסָה", "gloss": "to cover / to conceal", "title": "כָּסָה — to cover"},
    "vocab_כפי_233":   {"gloss": "spoon / palm / branch"},
    "vocab_כרם_477":   {"gloss": "vineyard"},
    "vocab_כתב_228":   {"hebrew": "כָּתַב", "gloss": "to write", "title": "כָּתַב — to write"},
    "vocab_לבבי_155":  {"hebrew": "לֵבָב", "gloss": "heart / inner self", "title": "לֵבָב — heart"},
    "vocab_לבדו_234":  {"gloss": "alone / only / by himself"},
    "vocab_לבלת_328":  {"hebrew": "לְבִלְתִּי", "gloss": "lest / in order not", "title": "לְבִלְתִּי — lest, in order not"},
    "vocab_לדרת_366":  {"gloss": "generation / period / dwelling"},
    "vocab_להוא_452":  {"hebrew": "לְהוּא", "gloss": "clay", "title": "לְהוּא — clay"},
    "vocab_לחדש_265":  {"hebrew": "חֹדֶשׁ", "gloss": "month / new moon", "title": "חֹדֶשׁ — month, new moon"},
    "vocab_לילה_299":  {"gloss": "night"},
    "vocab_למשפ_264":  {"gloss": "family / clan"},
    "vocab_לרב_439":   {"gloss": "multitude / abundance"},
    "vocab_לשון_346":  {"gloss": "tongue / language"},
    "vocab_מגרש_422":  {"gloss": "pasture land / common / suburb"},
    "vocab_מדוע_407":  {"gloss": "why?"},
    "vocab_מהלל_298":  {"hebrew": "הָלַל", "gloss": "to praise", "title": "הָלַל — to praise"},
    "vocab_מועד_162":  {"gloss": "appointed time / festival / meeting"},
    "vocab_מושי_236":  {"hebrew": "נוּעַ", "gloss": "to save / to deliver", "title": "נוּעַ — to save, to deliver"},
    "vocab_מזמו_426":  {"hebrew": "מִזְמוֹר", "gloss": "psalm / song", "title": "מִזְמוֹר — psalm, song"},
    "vocab_מחוץ_429":  {"hebrew": "חוּץ", "gloss": "outside / street", "title": "חוּץ — outside, street"},
    "vocab_מטה_317":   {"gloss": "staff / rod / tribe"},
    "vocab_מלאך_205":  {"gloss": "messenger / angel"},
    "vocab_מלאכ_311":  {"gloss": "work / occupation / business"},
    "vocab_מלחמ_232":  {"gloss": "war / battle"},
    "vocab_מלכא_227":  {"gloss": "Daniel (Aramaic name)"},
    "vocab_מלמד_469":  {"gloss": "to learn / to teach"},
    "vocab_מלפנ_356":  {"gloss": "from before / from the presence of"},
    "vocab_מנחה_302":  {"hebrew": "מִנְחָה", "gloss": "gift / offering / tribute", "title": "מִנְחָה — gift, offering"},
    "vocab_מספר_335":  {"gloss": "number / count / tale"},
    "vocab_מעשי_179":  {"hebrew": "מַעֲשֶׂה", "gloss": "work / deed / action", "title": "מַעֲשֶׂה — work, deed"},
    "vocab_מצות_240":  {"hebrew": "מִצְוָה", "gloss": "commandment", "title": "מִצְוָה — commandment"},
    "vocab_מצרי_482":  {"gloss": "Egyptian"},
    "vocab_מקים_89":   {"hebrew": "קוּם", "gloss": "to arise / to stand / to establish", "title": "קוּם — to arise, to establish"},
    "vocab_משמר_445":  {"hebrew": "מִשְׁמֶרֶת", "gloss": "guard / charge / obligation", "title": "מִשְׁמֶרֶת — guard, charge"},
    "vocab_משרת_494":  {"hebrew": "שָׁרַת", "gloss": "to minister / to serve", "title": "שָׁרַת — to minister, to serve"},
    "vocab_מתהל_83":   {"gloss": "to walk / to go"},
    "vocab_מתנב_406":  {"gloss": "to prophesy"},
    "vocab_נבון_229":  {"hebrew": "בִּין", "gloss": "to understand / to discern", "title": "בִּין — to understand, to discern"},
    "vocab_נבכד_458":  {"gloss": "Nebuchadnezzar"},
    "vocab_נגד_318":   {"gloss": "opposite / before / in front of"},
    "vocab_נדר_488":   {"gloss": "vow"},
    "vocab_נהר_476":   {"gloss": "river / stream"},
    "vocab_נזבח_412":  {"gloss": "we will sacrifice"},
    "vocab_נחל_405":   {"gloss": "brook / torrent / inheritance"},
    "vocab_נחלת_209":  {"gloss": "inheritance / possession"},
    "vocab_נחשב_284":  {"hebrew": "חָשַׁב", "gloss": "to think / to count / to regard", "title": "חָשַׁב — to think, to count"},
    "vocab_נחשת_352":  {"gloss": "bronze / copper / brass"},
    "vocab_נכון_180":  {"hebrew": "כּוּן", "gloss": "to be established / to be firm", "title": "כּוּן — to be established, to be firm"},
    "vocab_נערי_296":  {"gloss": "young men / servants / youths"},
    "vocab_נפלא_497":  {"hebrew": "פָּלָא", "gloss": "to be wonderful / to be extraordinary", "title": "פָּלָא — to be wonderful"},
    "vocab_נפתח_288":  {"hebrew": "פָּתַח", "gloss": "to open", "title": "פָּתַח — to open"},
    "vocab_נרדה_158":  {"hebrew": "יָרַד", "gloss": "to go down / to descend", "title": "יָרַד — to go down, to descend"},
    "vocab_נשאר_341":  {"hebrew": "שָׁאַר", "gloss": "to remain / to be left over", "title": "שָׁאַר — to remain"},
    "vocab_נשחת_351":  {"hebrew": "שָׁחַת", "gloss": "to destroy / to corrupt", "title": "שָׁחַת — to destroy"},
    "vocab_סגר_456":   {"gloss": "to shut / to close / to deliver up"},
    "vocab_סורו_148":  {"hebrew": "סוּר", "gloss": "to turn aside / to depart", "title": "סוּר — to turn aside"},
    "vocab_סלה_337":   {"hebrew": "סֶלָה", "gloss": "Selah (musical term)", "title": "סֶלָה — Selah"},
    "vocab_עבדת_323":  {"gloss": "work / service / labor"},
    "vocab_עוני_177":  {"hebrew": "עָוֹן", "gloss": "iniquity / guilt / punishment", "title": "עָוֹן — iniquity, guilt"},
    "vocab_עזי_343":   {"hebrew": "עֹז", "gloss": "strength / power / might", "title": "עֹז — strength, might"},
    "vocab_עזרנ_499":  {"gloss": "he helped us / our help"},
    "vocab_עיני_87":   {"hebrew": "עַיִן", "gloss": "eye / spring (water)", "title": "עַיִן — eye, spring"},
    "vocab_פנימ_21":   {"hebrew": "פָּנִים", "gloss": "face / presence", "title": "פָּנִים — face, presence"},
    "vocab_פנית_396":  {"hebrew": "פָּנָה", "gloss": "to turn / to face", "title": "פָּנָה — to turn, to face"},
    "vocab_פעלת_496":  {"hebrew": "פָּעַל", "gloss": "to do / to make / to work", "title": "פָּעַל — to do, to work"},
    "vocab_פעמי_319":  {"hebrew": "פַּעַם", "gloss": "once / time / step / anvil", "title": "פַּעַם — time, once"},
    "vocab_פרי_329":   {"gloss": "fruit / produce / reward"},
    "vocab_פרים_370":  {"gloss": "bull / bullock"},
    "vocab_פשעי_359":  {"hebrew": "פֶּשַׁע", "gloss": "transgression / rebellion", "title": "פֶּשַׁע — transgression"},
    "vocab_פתח_231":   {"gloss": "door / opening / entrance"},
    "vocab_צבאם_257":  {"gloss": "their army / their host"},
    "vocab_צדקה_390":  {"gloss": "righteousness / charity / justice"},
    "vocab_צדקי_443":  {"gloss": "Zedekiah"},
    "vocab_צוית_69":   {"gloss": "to command / to charge"},
    "vocab_צפנה_333":  {"hebrew": "צָפוֹן", "gloss": "north", "title": "צָפוֹן — north"},
    "vocab_צריך_475":  {"gloss": "adversary / foe / enemy"},
    "vocab_צרתי_474":  {"hebrew": "צָרָה", "gloss": "trouble / distress / adversary", "title": "צָרָה — trouble, distress"},
    "vocab_קדוש_295":  {"gloss": "holy / sacred / set apart"},
    "vocab_קלו_495":   {"gloss": "light / swift / trifling"},
    "vocab_קנית_442":  {"hebrew": "קָנָה", "gloss": "to buy / to acquire / to create", "title": "קָנָה — to buy, to acquire"},
    "vocab_קרבה_487":  {"gloss": "near / approaching"},
    "vocab_קרבן_342":  {"hebrew": "קָרְבָּן", "gloss": "offering / sacrifice / oblation", "title": "קָרְבָּן — offering, sacrifice"},
    "vocab_קרנת_465":  {"gloss": "horns / rays of light"},
    "vocab_רגלה_163":  {"hebrew": "רֶגֶל", "gloss": "foot / leg", "title": "רֶגֶל — foot"},
    "vocab_רחבה_464":  {"hebrew": "רֹחַב", "gloss": "breadth / width", "title": "רֹחַב — breadth, width"},
    "vocab_רכב_481":   {"gloss": "chariot / rider / to ride"},
    "vocab_רעה_316":   {"gloss": "to pasture / to shepherd / to feed"},
    "vocab_רעהו_225":  {"hebrew": "רֵעַ", "gloss": "neighbor / friend / companion", "title": "רֵעַ — neighbor, friend"},
    "vocab_רעת_173":   {"gloss": "evil / bad / harm"},
    "vocab_שאלה_480":  {"hebrew": "שְׁאוֹל", "gloss": "Sheol / grave / underworld", "title": "שְׁאוֹל — Sheol, grave"},
    "vocab_שארי_486":  {"gloss": "remnant / rest / remainder"},
    "vocab_שבט_224":   {"gloss": "staff / rod / tribe / scepter"},
    "vocab_שבר_293":   {"gloss": "grain / corn / to break"},
    "vocab_שיר_419":   {"gloss": "song / psalm"},
    "vocab_שלמת_394":  {"gloss": "completeness / compensation / peace offering"},
    "vocab_שמן_393":   {"gloss": "fat / oil / richness"},
    "vocab_שמרו_413":  {"gloss": "Samaria"},
    "vocab_שנאי_260":  {"gloss": "haters / those who hate"},
    "vocab_שער_198":   {"gloss": "gate / door / measurement"},
    "vocab_שפה_192":   {"gloss": "lip / language / edge / shore"},
    "vocab_שקר_291":   {"gloss": "falsehood / lie / deception"},
    "vocab_תאבה_472":  {"hebrew": "אָבָה", "gloss": "to be willing / to consent", "title": "אָבָה — to be willing"},
    "vocab_תבקש_201":  {"hebrew": "בָּקַשׁ", "gloss": "to seek / to search for", "title": "בָּקַשׁ — to seek"},
    "vocab_תגעו_310":  {"hebrew": "נָגַע", "gloss": "to touch / to strike", "title": "נָגַע — to touch"},
    "vocab_תועב_350":  {"hebrew": "תּוֹעֵבָה", "gloss": "abomination / detestable thing", "title": "תּוֹעֵבָה — abomination"},
    "vocab_תורה_263":  {"gloss": "law / instruction / teaching / Torah"},
    "vocab_תחתנ_71":   {"hebrew": "תַּחַת", "gloss": "under / beneath / instead of", "title": "תַּחַת — under, beneath"},
    "vocab_תיטי_415":  {"hebrew": "יָטַב", "gloss": "to be good / to do well", "title": "יָטַב — to be good, to do well"},
    "vocab_תירא_128":  {"gloss": "to fear / to be afraid / to revere"},
    "vocab_תכלנ_250":  {"hebrew": "כָּלָה", "gloss": "to be completed / to be consumed", "title": "כָּלָה — to be completed"},
    "vocab_תלדי_116":  {"hebrew": "יָלַד", "gloss": "to bear / to bring forth / to beget", "title": "יָלַד — to bear, to bring forth"},
    "vocab_תם_485":    {"gloss": "complete / perfect / blameless"},
    "vocab_תמאס_423":  {"hebrew": "מָאַס", "gloss": "to reject / to despise", "title": "מָאַס — to reject"},
    "vocab_תמיד_322":  {"gloss": "continually / always / regularly"},
    "vocab_תסף_212":   {"hebrew": "יָסַף", "gloss": "to add / to continue", "title": "יָסַף — to add, to continue"},
    "vocab_תענה_498":  {"hebrew": "עָנָה", "gloss": "to afflict / to humble", "title": "עָנָה — to afflict, to humble"},
    "vocab_תפלת_454":  {"hebrew": "תְּפִלָּה", "gloss": "prayer", "title": "תְּפִלָּה — prayer"},
    "vocab_תרעו_420":  {"gloss": "to do evil / to act wickedly"},
    "vocab_תשבע_395":  {"hebrew": "שָׂבַע", "gloss": "to be satisfied / to be full", "title": "שָׂבַע — to be satisfied"},
    "vocab_תשרפ_379":  {"hebrew": "שָׂרַף", "gloss": "to burn", "title": "שָׂרַף — to burn"},
    "vocab_תסף_212":   {"gloss": "to add / to continue / to do again"},
}


def fix_remaining():
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    fixed_nodes = 0
    fixed_lessons = 0
    fixed_practice = 0

    # Phase 1: Apply corrections
    for node_id, corr in ADDITIONAL_CORRECTIONS.items():
        node = conn.execute("SELECT * FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
        if not node:
            print(f"  SKIP {node_id}: not found")
            continue

        old_title = node['title']
        new_gloss = corr.get('gloss')
        new_hebrew = corr.get('hebrew')
        new_title = corr.get('title')

        old_parts = old_title.split(' — ', 1)
        old_hebrew = old_parts[0] if len(old_parts) > 1 else ''
        old_gloss = old_parts[1] if len(old_parts) > 1 else old_title

        if not new_hebrew:
            new_hebrew = old_hebrew
        if not new_title:
            new_title = f"{new_hebrew} — {new_gloss}" if new_gloss else old_title

        # Skip if nothing changed
        if old_title == new_title:
            continue

        # Update node title
        conn.execute("UPDATE hebrew_nodes SET title=? WHERE id=?", (new_title, node_id))

        # Clean up Strong's-style description
        old_desc = node['description'] or ''
        if old_desc and (old_desc.startswith('1)') or old_desc.startswith('1.')):
            new_desc = f"{new_gloss}" if new_gloss else old_gloss
            conn.execute("UPDATE hebrew_nodes SET description=? WHERE id=?", (new_desc, node_id))

        print(f"  FIX {node_id}: '{old_title}' → '{new_title}'")
        fixed_nodes += 1

        # Update lesson content
        lesson_row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
        if lesson_row and lesson_row[0]:
            try:
                content = json.loads(lesson_row[0]) if isinstance(lesson_row[0], str) else lesson_row[0]
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
            if content.get('transliteration'):
                # Fix transliteration if it starts with wrong letter pattern
                pass
            if changed:
                conn.execute("UPDATE hebrew_lessons SET content_json=? WHERE node_id=?",
                           (json.dumps(content, ensure_ascii=False), node_id))
                fixed_lessons += 1

        # Update practice items
        items = conn.execute(
            "SELECT id, question_type, question_text, correct_answer, options_json FROM hebrew_practice_items WHERE node_id=?",
            (node_id,)).fetchall()
        for item in items:
            qtext = item['question_text']
            cans = item['correct_answer']
            opts = item['options_json']

            repl = False
            new_qtext = qtext
            new_cans = cans

            if old_gloss and new_gloss and old_gloss != new_gloss:
                if cans == old_gloss:
                    new_cans = new_gloss
                    repl = True
                if old_gloss in qtext:
                    new_qtext = qtext.replace(old_gloss, new_gloss)
                    if new_qtext != qtext:
                        repl = True
                if opts:
                    try:
                        opts_list = json.loads(opts)
                        if isinstance(opts_list, list):
                            new_opts = [new_gloss if o == old_gloss else o for o in opts_list]
                            if new_opts != opts_list:
                                conn.execute("UPDATE hebrew_practice_items SET options_json=? WHERE id=?",
                                           (json.dumps(new_opts, ensure_ascii=False), item['id']))
                                fixed_practice += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

            if new_hebrew and old_hebrew and new_hebrew != old_hebrew:
                if old_hebrew in new_qtext and new_hebrew not in new_qtext:
                    new_qtext = new_qtext.replace(old_hebrew, new_hebrew)
                    repl = True
                if new_cans == old_hebrew:
                    new_cans = new_hebrew
                    repl = True
                if opts:
                    try:
                        opts_list = json.loads(opts)
                        if isinstance(opts_list, list):
                            new_opts = [new_hebrew if o == old_hebrew else o for o in opts_list]
                            if new_opts != opts_list:
                                conn.execute("UPDATE hebrew_practice_items SET options_json=? WHERE id=?",
                                           (json.dumps(new_opts, ensure_ascii=False), item['id']))
                                fixed_practice += 1
                    except (json.JSONDecodeError, TypeError):
                        pass

            if repl:
                if new_qtext != qtext:
                    conn.execute("UPDATE hebrew_practice_items SET question_text=? WHERE id=?", (new_qtext, item['id']))
                if new_cans != cans:
                    conn.execute("UPDATE hebrew_practice_items SET correct_answer=? WHERE id=?", (new_cans, item['id']))
                fixed_practice += 1

    # Phase 2: Remove Strong's-style descriptions from any remaining entries
    print("\n  Cleaning Strong's-style descriptions...")
    strongs = conn.execute("""
        SELECT id, description FROM hebrew_nodes 
        WHERE category='word' AND (description LIKE '1)%' OR description LIKE '1.%')
    """).fetchall()
    for r in strongs:
        title = conn.execute("SELECT title FROM hebrew_nodes WHERE id=?", (r['id'],)).fetchone()[0]
        parts = title.split(' — ', 1)
        gloss = parts[1] if len(parts) > 1 else title
        # Take first meaningful sentence from the Strong's entry
        desc = r['description']
        # Extract content after the numbered list
        lines = desc.split('\n')
        clean_parts = []
        for line in lines:
            line = line.strip()
            if line and not line[0].isdigit() and not line.startswith('1)'):
                clean_parts.append(line)
        if clean_parts:
            new_desc = ' '.join(clean_parts)[:200]
        else:
            new_desc = gloss
        conn.execute("UPDATE hebrew_nodes SET description=? WHERE id=?", (new_desc, r['id']))
        print(f"  CLEAN {r['id']}: Strong's description → '{new_desc[:60]}...'")

    conn.commit()
    conn.close()
    print(f"\n  Additional fixes: {fixed_nodes} nodes, {fixed_lessons} lessons, {fixed_practice}+ practice items")


def fix_source():
    if not SCRIPTURE_DB.exists():
        return
    conn = sqlite3.connect(str(SCRIPTURE_DB))
    patches = [
        ("6", "to perish / to be lost"),
        ("202", "vigor / wealth / sorrow"),
        ("241", "ear"),
        ("256", "brother"),
        ("269", "sister"),
        ("341", "enemy / foe"),
        ("352", "ram / leader"),
        ("6098", "counsel / advice"),
        ("426", "god (Aramaic)"),
        ("433", "God / god"),
        ("452", "Elijah"),
        ("499", "Eleazar"),
        ("520", "cubit"),
        ("587", "we"),
        ("635", "Esther"),
        ("637", "also / even"),
        ("681", "beside / near"),
        ("727", "ark / chest"),
        ("753", "length"),
        ("809", "morning"),
        ("899", "garment / clothing"),
        ("982", "to trust / to be confident"),
        ("2474", "window"),
        ("6256", "time / moment"),
        ("1288", "blessed"),
        ("1285", "covenant / treaty"),
        ("1366", "border / boundary"),
        ("1368", "mighty man / warrior"),
        ("1732", "beloved / uncle"),
        ("1840", "Daniel"),
        ("1844", "knowledge"),
        ("127", "the ground / the land"),
        ("539", "to be faithful / to trust"),
        ("622", "to gather / to assemble"),
        ("1892", "vapor / vanity"),
        ("1471", "nation / people"),
        ("2490", "to profane / to defile"),
        ("2691", "court / courtyard"),
        ("3064", "Jew / Jewish"),
        ("3383", "the Jordan"),
        ("3669", "the Canaanite"),
        ("3871", "multitude / crowd"),
        ("4196", "altar"),
        ("4264", "camp / army"),
        ("4422", "to escape / to deliver"),
        ("4725", "place"),
        ("4908", "tabernacle / dwelling"),
        ("5030", "prophet"),
        ("5712", "congregation / assembly"),
        ("6153", "evening"),
        ("2015", "to turn / to overthrow"),
        ("7126", "to approach / to offer"),
        ("7223", "first / former"),
        ("7350", "far / distant"),
        ("7311", "to lift up / to offer"),
        ("7650", "to swear"),
        ("7704", "field / open country"),
        ("7992", "third"),
        ("8074", "desolate / ruined"),
        ("8121", "sun"),
        ("8145", "second"),
        ("6912", "to bury"),
        ("7004", "incense"),
        ("7812", "to bow down / to worship"),
        ("7819", "to slaughter"),
        ("6419", "to pray / to intervene"),
        ("3498", "to remain / to be left over"),
        ("3898", "to fight / to do battle"),
        ("2076", "sacrifice"),
        ("2145", "male / masculine"),
        ("2114", "strange / foreign"),
        ("2233", "seed / offspring"),
        ("2396", "Hezekiah"),
        ("2428", "strength / army / wealth"),
        ("2506", "portion / share"),
        ("2346", "wall / heat / anger"),
        ("2555", "violence / wrong"),
        ("2534", "heat / rage / fury"),
        ("2580", "grace / favor"),
        ("2654", "to delight in / to desire"),
        ("2706", "statute / decree"),
        ("2822", "darkness"),
        ("2889", "clean / pure"),
        ("2931", "unclean / defiled"),
        ("3129", "Jonathan"),
        ("3092", "Jehoshaphat"),
        ("2026", "to kill / to slay"),
        ("3097", "Joab"),
        ("3423", "to possess / to inherit"),
        ("3196", "wine"),
        ("3225", "right hand / south"),
        ("4910", "to rule / to have dominion"),
        ("5162", "to comfort / to console"),
        ("5608", "to count / to recount"),
        ("5800", "to abandon / to forsake"),
        ("5782", "to rouse / to awaken"),
        ("5927", "to go up / to ascend"),
        ("7235", "to be many / to increase"),
        ("3426", "there is / there are"),
        ("7901", "to lie down / to sleep"),
        ("954", "to be ashamed"),
        ("3519", "glory / honor / weight"),
        ("3535", "lamb"),
        ("3581", "strength / power"),
        ("3627", "vessel / utensil"),
        ("3671", "wing / edge"),
        ("3678", "throne / seat"),
        ("3680", "to cover / to conceal"),
        ("3709", "palm / spoon"),
        ("3754", "vineyard"),
        ("3789", "to write"),
        ("3824", "heart / inner self"),
        ("905", "alone / apart / only"),
        ("1115", "lest / in order not"),
        ("1755", "generation / period"),
        ("2320", "month / new moon"),
        ("3915", "night"),
        ("4940", "family / clan"),
        ("7230", "multitude / abundance"),
        ("3956", "tongue / language"),
        ("4054", "pasture land / suburb"),
        ("4069", "why?"),
        ("1984", "to praise"),
        ("4150", "appointed time / festival"),
        ("3467", "to save / to deliver"),
        ("4210", "psalm / song"),
        ("2351", "outside / street"),
        ("4294", "staff / rod / tribe"),
        ("4397", "messenger / angel"),
        ("4399", "work / occupation"),
        ("4421", "war / battle"),
        ("3925", "to learn / to teach"),
        ("4503", "gift / offering / tribute"),
        ("4557", "number / count"),
        ("4639", "work / deed / action"),
        ("4687", "commandment"),
        ("4713", "Egyptian"),
        ("6965", "to arise / to stand"),
        ("4931", "guard / charge"),
        ("8334", "to minister / to serve"),
        ("1980", "to walk / to go"),
        ("5012", "to prophesy"),
        ("995", "to understand / to discern"),
        ("5046", "to tell / to declare"),
        ("5087", "vow"),
        ("5104", "river / stream"),
        ("5158", "brook / torrent"),
        ("5159", "inheritance / possession"),
        ("2803", "to think / to count"),
        ("5178", "bronze / copper"),
        ("3559", "to be established"),
        ("5288", "young man / servant"),
        ("6381", "to be wonderful"),
        ("6605", "to open"),
        ("3381", "to go down / to descend"),
        ("7604", "to remain / to be left"),
        ("7843", "to destroy / to corrupt"),
        ("5462", "to shut / to close"),
        ("5493", "to turn aside / to depart"),
        ("5542", "Selah"),
        ("5656", "work / service / labor"),
        ("5771", "iniquity / guilt"),
        ("5797", "strength / might"),
        ("5828", "help"),
        ("5869", "eye / spring"),
        ("6437", "to turn / to face"),
        ("6466", "to do / to work"),
        ("6471", "once / time / step"),
        ("6529", "fruit / produce"),
        ("6499", "bull / bullock"),
        ("6588", "transgression / rebellion"),
        ("6607", "door / opening"),
        ("6666", "righteousness / charity"),
        ("6828", "north"),
        ("6862", "adversary / foe"),
        ("6869", "trouble / distress"),
        ("6918", "holy / sacred"),
        ("7031", "light / swift"),
        ("7069", "to buy / to acquire"),
        ("7126", "near / approaching"),
        ("7133", "offering / oblation"),
        ("7161", "horns / rays"),
        ("7272", "foot / leg"),
        ("7341", "breadth / width"),
        ("7393", "chariot / to ride"),
        ("7462", "to pasture / to shepherd"),
        ("7453", "neighbor / friend"),
        ("7455", "evil / bad / harm"),
        ("7585", "Sheol / grave / underworld"),
        ("7611", "remnant / rest"),
        ("7626", "staff / rod / tribe"),
        ("7668", "grain / corn"),
        ("7892", "song / psalm"),
        ("8002", "completeness / peace offering"),
        ("8081", "fat / oil"),
        ("8111", "Samaria"),
        ("8130", "to hate"),
        ("8179", "gate / door"),
        ("8193", "lip / language"),
        ("8267", "falsehood / lie"),
        ("14", "to be willing / to consent"),
        ("1245", "to seek / to search"),
        ("5060", "to touch / to strike"),
        ("8441", "abomination"),
        ("8451", "law / instruction / Torah"),
        ("8478", "under / beneath"),
        ("3190", "to be good / to do well"),
        ("3372", "to fear / to revere"),
        ("3615", "to be completed / to be consumed"),
        ("3205", "to bear / to bring forth"),
        ("8549", "complete / perfect / blameless"),
        ("3988", "to reject / to despise"),
        ("8548", "continually / always"),
        ("3254", "to add / to continue"),
        ("6031", "to afflict / to humble"),
        ("8605", "prayer"),
        ("7489", "to do evil / to act wickedly"),
        ("7646", "to be satisfied / to be full"),
        ("8313", "to burn"),
    ]
    updated = 0
    for lemma, gloss in patches:
        existing = conn.execute("SELECT english_gloss FROM lemma_gloss WHERE lemma=?", (lemma,)).fetchone()
        if existing and existing[0] != gloss:
            conn.execute("UPDATE lemma_gloss SET english_gloss=? WHERE lemma=?", (gloss, lemma))
            updated += 1
    conn.commit()
    conn.close()
    print(f"  Updated {updated} lemma_gloss entries")


if __name__ == '__main__':
    print("=== Fixing source data ===")
    fix_source()
    print("\n=== Fixing remaining vocabulary entries ===")
    fix_remaining()
    print("\n✓ Done!")
