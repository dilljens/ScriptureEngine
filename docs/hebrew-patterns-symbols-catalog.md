# Big List: All Discovered Hebrew Patterns & Symbols

Source of truth: `data/processed/scripture.db` + `generators/`. Counts are live row counts,
not estimates. Isaiah anchors given where the pattern lives most densely.
Companion: `docs/isaiah-first-temple-deep-dive.md` (First-Temple reading),
`docs/ascending-to-presence-article.md` (ascent essay).

---

## PART A — LITERARY / STRUCTURAL PATTERNS

### A1. Chiasms (27 in `known_chiasms`)
| # | Scholar | Structure | Span | Pivot | Type | Conf |
|---|---------|-----------|------|-------|------|------|
| 1 | Giliadi | Genesis integral | gen.1.1–50.26 | gen.25.19 | integral | 0.6 |
| 2 | Giliadi | Flood | gen.6.9–9.29 | gen.8.1 ("God remembered Noah") | word_count | 0.8 |
| 3 | Giliadi | Exodus | exo.1.1–15.21 | exo.6.2 | integral | 0.55 |
| 4 | Giliadi | **Isaiah integral** (1–35 judgment / 40–66 consolation, hinge 36–39 Hezekiah) | isa.1.1–66.24 | isa.36.1 | integral | 0.5 |
| 5 | Douglas-line | Leviticus ring (holiness code center) | lev.1.1–27.34 | lev.19.1 | thematic | 0.7 |
| 6 | Welch | **Alma 36** (the model word-level chiasm) | alma.36.1–30 | alma.36.18 | word_level | 0.95 |
| 7–9 | Welch | Mos 5:10–12; 1 Ne 1:1–20; 2 Ne 29 | — | — | mixed | 0.7–0.85 |
| 10–11 | Lund/Welch | Matthew macro; John 1:1–18 prologue | — | matt.13.1 / john.1.9 | mixed | 0.5–0.8 |
| 12–13 | Multiple | Amos 1–2; Gen 1 forming/filling (days 1–3 // 4–6) | — | — | mixed | 0.9 |
| 14–15 | deepseek_ai | Gen 19–35 and Gen 3–50 word-count chiasms | — | gen.25.19 | word_count | 0.55–0.85 |
| **16** | Gileadi | **Bifid Isaiah: 7 pairs A–G // A'–G'** (Ruin/Rebirth, Rebellion/Compliance, Punishment/Deliverance, Humiliation/Exaltation, Suffering/Salvation, Disloyalty/Loyalty, Disinheritance/Inheritance) | isa.1.1–66.24 | isa.33.24 | integral | 0.7 |
| **17** | Gileadi | **Servant–Tyrant 21-verse antithesis** (Isa 14 king of Babylon "I will ascend" ↔ Isa 52–53 Servant humbled → "very high") | isa.14.1–53.12 | isa.53.1 | word_level | 0.8 |
| **18** | Gileadi | **Zion ideology 40+ minis** (destruction → intercession → deliverance, every one a Hezekiah 37 in miniature) | isa.1.1–66.24 | isa.37.1 | thematic | 0.65 |
| **19** | Gileadi | **Trouble → Exile → Homecoming** (1–39 / 40–54 / 55–66) | isa.1.1–66.24 | isa.40.1 | thematic | 0.7 |
| 20–21 | Welch | Mosiah 3; Helaman 6 | — | — | word_level | 0.7–0.75 |
| 22–27 | Multiple | Joshua macro; Exo 1–15; Psa 1; Psa 136 (26-fold refrain); Lord's Prayer; D&C 1 | — | — | mixed | 0.6–0.9 |

### A2. Gileadi Isaiah machinery (`generators/isaiah_advanced.py`)
- **2 Days of Jehovah:** midpoint isa.34–35 (vengeance on nations/Edom → wilderness blooms → new exodus) vs final isa.63–66 (vengeance → descent → new creation → final separation).
- **3 Threats (escalating):** T1 Assyria vs Israel (5–10, climax 10:5) → T2 Assyrian world conquest (13–24, climax 14:12) → T3 final Day (34–35, climax 34:8).
- **11 curse→blessing reversals:** 1:2–15→1:16–31 (repent→cleanse); 3:1–4:1→4:2–6 (judgment→Branch); 5→12 (wild grapes→salvation song); 9:8–10:4→11–12 (Ephraim fall→Jesse rod); 22→23; 28–29→30–33; 40:1–11→40:12–31; 42:18–43:28→44–45; 50–51:8→51:9–52:12; 59→60–62; 63–64→65–66.
- **8 destruction→deliverance pairs:** 13–14:23→14:24–32 (Babylon→Zion); 15–16:14→16:1–5 (Moab→Davidic throne); 17→18; 19:1–17→19:18ff (Egypt smitten→healed); 21→22:20–25 (→Eliakim); 34–35 internal; 47→52 (Babylon→Zion awakes); 64→65–66.
- **Tabernacle ladder (7 rungs):** Court/Gate (Perdition) → Bronze Altar (Babylon/repentance) → Laver (Jacob/washing) → Table (Zion/fellowship) → Lampstand (sons/daughters/ministry) → Incense (seraphim/intercession) → Holy of Holies (Jehovah/presence). Anchors: exo.25–30 → isa.6.1.
- **30 cyclical types:** Flood→end desolation (24–27); Sodom→Babylon fall (13–14:23); Exodus→new exodus (43–44); Sinai→end covenant (2–4); Jericho→kingdom (11–12); Hezekiah deliverance→remnant (36–39); Passover→redemption (52:11–15); Sinai theophany→descent (63–64); Creation→new creation (65:17–66:24); Eden→millennial paradise (51:3); + pillar-of-cloud, temple-dedication, judges, consuming fire, Midian/Assyria pairs, etc.
- **Overlays:** 3-part (Trouble 1–39 / Exile 40–54 / Homecoming 55–66); 4-part AJRS (Apostasy 1–9 / Judgment 10–34 / Restoration 35–59 / Salvation 60–66); 2-part curses/blessings (1–39 // 40–66); 3 tests (allegiance 1–38 / idols 39–48 / persecution 49–66).
- **15 Servant–Tyrant verse pairs** (14:4→52:13 … 14:18→53:12): taunt→exaltation; scepter broken→marred; rage→sprinkling; rest→"who believed"; cypresses→no form; Sheol stirred→despised; weak→bore griefs; pomp→wounds; dawn fallen→sheep astray; ascend→lamb to slaughter; Most High→cut off; Pit→grave with wicked; beholders→pleased Jehovah; wilderness→satisfied; kings in glory→portion with great.
- **12 chaos/de-creation motifs:** dust (עפר, laid low), chaff (מץ, wind-driven), stubble (קש, fire food), mire (טיט), clay (חמר, molded/cast), dross (סיג, smelted out), refuse, smoke (עשן), wind (רוח), tempest (סער), hail (ברד, judgment), darkness (חשך, no light/truth). Cluster = Genesis-1-in-reverse, covenant-collapse signal (Isa 24).
- **20 DSS 1QIsa seams** (petuchah/setumah): 1, 2–4, 5, 6, 7–8, 9–10, 11–12, 13–14, 15–16, 17–18, 19–20, 24–27, 28–33, 34–35, 36–39, 40–48, 49–55, 56–59, 60–62, 63–66.

### A3. Formula markers (422 in `structural_formulas`)
- **behold (2009 הִנֵּה) — 206x.** "Behold" = disclosure flag; in Isaiah often theophany or judgment unveiling (e.g. isa.52:13 "Behold, my servant").
- **came_to_pass — 94x** (Isaiah form "it shall come to pass," e.g. isa.2.2, 3:24, 4:3): eschatological hinge.
- **god_said — 51x; thus_says_lord — 35x** (כֹּה־אָמַר יְהוָה): messenger formula; Isaiah clusters in 40–48 trial speeches.
- **woe (הוֹי) — 21x** (isa.3:9, 3:11, 5:8…; six in Isa 5; prophet's own אוֹי־לִי in 6:5): covenant-lawsuit (רִיב) + funeral dirge fused.
- **toledot ("generations") — 10x; word_came — 2x; blessed — 3x** ("Blessed be the LORD").

### A4. Staircase chains (186 in `patterns`, all `staircase_chain`)
Verse-to-verse catchword сцепление: repeated word lifts next verse (e.g. isa.1.7–11 chain on Sodom/Gomorrah/LORD/left). Algorithm-found via shared-word overlap; every one lists `repeated_words`, `chain_length`, `avg_overlap`. Densest in Isaiah 1–5, 28–33.

---

## PART B — LEXICAL LINKAGE PATTERNS (how verses are sewn together)

| Mechanism | Rows | What it is | Isaiah anchor |
|-----------|------|------------|---------------|
| `rare_word_cluster` | 16,770 | Verses sharing a rare lemma (hapax-adjacent glue) | cross-book rarity bridges |
| `linked_words` | 12,324 | Same-lemma verse↔verse links | backbone of keyword web |
| `semuchin` | 6,690 | Construct-chain (סמיכות, "X-of-Y") noun pairs | e.g. throne-room, holy-mountain compounds |
| `hapax_dense` | 6,555 | Verses dense with once-words (vision hotspots) | Isa 6, 14, 24–27, 40 |
| `giliadi_catchword` | 4,317 | Gileadi catchwords binding antithetical halves | 7-pair structure seams |
| `x_catchword` / `cross_canon_pseudonym` | 3,212 / 2,991 | Cross-canon same-word links (incl. servant/tyrant) | Isa 14↔52–53; Isa↔BoM |
| `isaiah_keyword` | 2,151 | Hebrew stems in BOTH halves of a parallel pair (Gileadi method, stops filtered) | forest→city→people chains |
| `isaiah_domino_chain` | 411 | Same keyword in ADJACENT pairs = transitive bridge | A→B→C…A'→G' ladder |
| `word_collocations` | 50,216 pairs | Top Isaiah pairs: 3588a+3068 (כִּי+יהוה, 130x), 3808+3588a (לֹא+כִּי, 127x), 5921a+3068 (עַל+יהוה, 89x), 559+3068 (אָמַר+יהוה, 83x), 6635b+3068 (צָבָא+יהוה = "LORD of hosts," 59x) | Isa 6:3 signature |

### Twin-pair pseudonyms (`generators/isaiah_pseudonyms.py` + `cross_canon_pseudonyms.py`)
Same Strong's, two actors; hubs SERVANT isa.42.1 ("Behold my servant") vs TYRANT isa.10.5 ("Assyrian, rod of anger").
**12 twin pairs:** Hand (3027: 11:11/49:22/51:16/62:8 vs 5:25/10:5/47:6/64:7); Ensign (5251: 11:10–12/49:22/62:10 vs 5:26/13:2); Rod (7626: 11:4 vs 9:4/10:5,15,24/14:5); Staff (4938: 10:26/30:32 vs 9:4/10:5,15/14:5); Sword (2719: 27:1/31:8/41:2 vs 1:20/34:5–6/66:16); Fire (784: 10:16–17/30:30/31:9 vs 1:7/9:18–19/47:14); Mouth (6310: 1:20/11:4/49:2 vs 5:14/37:29); Voice (6963: 40:3,6/58:1 vs 13:2/33:3); Light/Darkness (216/2822: 9:2/42:6/49:6/60:1 vs 5:20/42:7,16/59:9); Sea/River (3220/5104: 11:15/27:1 vs 5:30/8:7–8/51:15); Arm (2220: 30:30/40:10–11/51:5/52:10/59:16 vs 33:2); Breath/Wind (7307: 11:4 vs 30:28/33:11).
**Servant-only:** Arrow (49:2), Bird of prey (46:11), Trumpet (18:3/27:13/58:1), Righteousness (41:2/46:12–13/51:5), Covenant (42:6/49:8), Stone (28:16), Whip (10:26), Zeal (9:7/26:11/37:32/63:15).
**Tyrant-only:** Anger (10:5,25/63:3), Wrath (10:5,25/13:5,9), Darkness, Death (25:8 swallowed vs 28:15,18 covenant with death), Yoke (9:4/10:27/14:25/47:6), Broom (14:23), Axe/Saw (10:15), Flood-river (8:7/28:2,15,18).
Extended set in `isaiah_advanced.py` adds Hail, Ensign-variants, Anger/Wrath with same split.

### Gematria systems (`gematria`: 392,256 word rows; 9 value columns)
Per word: standard, ordinal, reduced, mispar_gadol, milui, kellali, kidmi, boneh + morph + lemma. Enables: equal-value word links (`gematria_sum`, `gematria_factor`, `ordinal_reduced_gematria`, `sod_fill`, `sefirot_mapper`, `shem_hamephorash` generators), 7/12/40-style number theology checks, and atbash-style concealment tests. Most-connected Hebrew lemmas overall: 853 (את, 8,730x), 3068 (יהוה, 5,701x), 413 (אֶל/אֵת, 5,164x), 834a (אֲשֶׁר, 4,807x), 1121a (בֵּן, 4,012x), 3478 (יִשְׂרָאֵל, 2,259x), 3027 (יָד/hand, 413 glossed + 1,456 raw).

---

## PART C — NUMBER SYMBOLS (in `symbols`, food/object/number rows)

- **seven (שֶׁבַע) — perfection/completeness/covenant.** Menorah 7 flames = Isa 11:2 seven spirits; 7 connection-subtypes (`seven_x8`, `seven_x20` ≈ 3.5k+5k rows); Rev lampstands (typology 28: lampstand→churches).
- **twelve — government/people of God.** 12 tribes/apostles; Isa 49:22 ensign to nations.
- **forty — testing/preparation.** 40 years/40 days (typology: wilderness→testing); Isa 40 comfort after exile arithmetic.
- **three — divine completeness/testimony.** Triple Holy 6:3 (superlative); thrice-Amen (3 Ne 19 // Jeu).
- **ten — order/responsibility; thousand — fullness/Lord's day; four — earth/universality; hundred — Abrahamic fullness.** Connection subtypes `ten_x3…x14`, `forty_x2`, `fifty_x2`, `seventy_x2`, `twelve_x3` encode multiples found across canon.

---

## PART D — SYMBOL CATALOG (all 88 in `symbols`, grouped)

### Animals (11)
lamb (sacrifice/atonement/innocence — Isa 53:7); lion (Judah/kingship — 11:6–7 wolf+**lamb**? lion with calf); serpent (adversary — yet seraphim are fiery serpents, 6:2,6); serpent_bronze (lifted healing — Num 21 // Isa 53 lifted Servant); dove (Spirit/peace); dragon (chaos/end-opposition — Isa 27:1 Leviathan); eagle (protection/judgment — 40:31 wings); horse (warfare/judgment); fish (multiply); fox (deception); wolf (false prophets — 11:6 wolf dwells with lamb = peace reversal).

### Beings (8)
seraphim (worshipers/purifiers — **Isa 6 only major OT occurrence**); cherubim (throne bearers — Eden guard 3:24 // temple veil embroidery); living_creatures (heavenly worship); angel_of_lord (theophany/pre-incarnate); lamb_slain; beast_from_sea/earth (end powers); (plus watchers-adjacent in Barker rows).

### Body parts (6)
right_hand (power — Isa 41:10; 48:13; 62:8); horns (kingship); heart (לֵב, 344x gloss — Isa 6:10 heart fat/lest understand); eyes (watchfulness — anointing opens eyelids); wings (shelter — 6:2; 40:31); feet (conduct/submission).

### Colors — veil + vesture set (6)
white (purity/victory — Isa 1:18 snow/wool; 6:1 train; Rev 3:5); red_scarlet (sin/blood/war — 1:18 scarlet/crimson pair = one stain doubly imaged); blue (heaven/priesthood — veil thread); purple (royalty — veil thread); green (life); black (mourning/famine). Veil = blue+purple+scarlet+white = air+sea+fire+earth (Barker/Josephus War 5.212–213); high-priest robe same four (Wisd 18:24 "whole world").

### Elements (7)
fire (presence/purge/Spirit — 4:4 burning; 6:6 coal; 33:14 devouring fire); light (Christ/truth — 9:2; 42:6; 49:6; 60:1); darkness (separation — 5:20; 42:7,16; 59:9); cloud (presence/covering — 4:5 cloud+fire over assembly); water (cleansing/Spirit); wind (רוּחַ Spirit/power — 11:4 breath; 40:7); earthquake (shaking — Sinai/temple idiom).

### Food (6)
bread (word/provision/body — Table, 12 loaves; Isa 55:1–2 buy without price); wine (covenant blood/joy); manna (heavenly bread — wilderness type); honey (word/sweetness); milk (pure word); water_living (Spirit/eternal life — temple river Ezek 47 // Rev 22 // Isa 12:3 wells of salvation).

### Materials (6)
gold (divinity/kingship — Holy of Holies overlay); silver (redemption); brass_bronze (judgment/endurance — altar/sea); iron (oppression); clay (חֹמֶר humanity — Isa 29:16; 45:9; 64:8 "we are clay, thou potter"); stone (אֶבֶן foundation — 28:16 tested cornerstone → Servant-only pseudonym).

### Objects — temple furniture + regalia (16)
throne (sovereignty — 6:1; throne_vision 5,725 links); altar (sacrifice/covenant — 6:6 coal source); incense (prayers — smoke fills house 6:4); lampstand (Spirit/church — 7 lamps; Zech 4 // Rev 1:20); seal (ownership — 8:16 bind/seal; Rev 7:3); robe (righteousness/authority — 52:1; 61:10 garment of praise); crown (victory); scepter (rule); sword (word/judgment — twin-pair); scroll (word/prophecy — eaten sweet Ezek 3 // Rev 10); key (authority — 22:22 key of David); trumpet (assembly/voice); shield (protection); rock (refuge — צוּר // "form" wordplay per Barker); cornerstone; measuring_rod (standard — Ezek 40 // Rev 11); ark_noah (salvation vessel).

### Places (6)
mountain (presence/revelation — 2:2–3 mountain of LORD's house; 11:9 holy mountain; 25:6–9 feast mountain; 52:7 feet on mountains); temple_house (dwelling — 6:1 הֵיכָל); garden (Eden/presence — 51:3 wilderness→Eden; 58:11 watered garden); city (Babylon-pride vs Jerusalem-presence); sea (chaos/nations — 8:7 flood; 11:15; 27:1; 51:15); wilderness (testing/refuge — 35:1 blooms; 40:3 highway; 41:17–20).

### Plants — tree theology cluster (8)
tree_of_life (wisdom/Christ — Prov 3:18; Rev 2:7/22:14; Isa 51:3 Eden; menorah as almond tree Exod 25:31–39); vine (Israel/covenant — 5:1–7 song of vineyard); olive_tree (covenant/Spirit/peace); fig_tree (fruitfulness/judgment); cedar (strength/pride/Lebanon — temple timber); lily; mustard_seed; thorns (curse — Gen 3 // Isa crown).

---

## PART E — HEBREW THEOLOGICAL KEYWORDS (gloss + First-Temple set)

Top canonical lemmas (`lemma_gloss` by frequency): 3068 LORD (5,619); 3478 Israel (2,212); 430 GOD (1,734); 1121a Son (1,766); 1004b House (1,037); 4428 King (973); 8034 Name (420); 3027 Hand (413); 3820a Heart (344); 3389 Jerusalem (346); 776 Land (461); 3117 Day (439).
Isaiah-essay Hebrew core (`ascending-to-presence` §3): **qadosh** (set apart; qiddesh Piel consecrate; hitqaddesh present-as-holy; miqdash sanctuary; 6:3 triple = superlative); **tahor/tame/chol** (fit/unfit/common; 1:16 rachatsu wash + hizzakku clean reflexive; 52:11 hibbaru Niphal be-pure); **kavod** (weight — presence has mass; 6:3 earth full); **panim** (face/audience; 8:17 hidden face = exile); **yada** (covenant acquaintance, 52:6); **shuv** (homecoming, 55:7; 30:15); **kaphar** (cover; 6:7 tekhuppar Pual from altar); **shema** (hear=obey; 50:4 wakened ear); **qavah** (hope/expect — braiding image homiletical only); **dakka/shefal/ani/nekheh/chared** (contrite cluster 57:15/66:2); **hineni/hinneh** (availability vs disclosure, 6:8/58:9); **neqi/bar** (innocent hands/pure heart, Ps 24 // Isa 33:14–17); **menuchah** (ark-rest/residence, Ps 132 // Isa 11:10); parallelism, rib (lawsuit), hoy/oy (woe), proposed chiasm/inclusio labels.

---

## PART F — FIRST-TEMPLE PATTERN CLUSTER (connection subtypes with counts)

Angel/order: `barker_angel` 5,922; `divine_angel` 5,922; `throne_vision` 5,725; `heavenly_court` 2,590; `heavenly_temple` 2,366; `heavenly_mediator` 3,102; `visionary_ascent` 1,848; `mountain_of_god` 1,737; `temple_location` 1,391; `cosmos_temple` 1,260; `throne` 770; `creation_temple` 323.
Wisdom/Word: `wisdom_logos` 5,500; `church_as_temple` 3,159; `new_creation_temple` 860; `beale_*` ≈ 25; `eden_as_prototype_temple` 7.
Veil/boundary/water: `veil_boundary` 5,096; `temple_water` 5,571; `axis_mundi` 6,860; `journey_path` 9,559; `exile_route` 1,820; `wilderness_sojourn` 1,790; `promised_land` 2,002; `veil_rent/veil_of_temple/veiled` ≈ 25; `temple_river/living_water` ≈ 7; `moses_veil_horns`, `glory_fills_temple` 1 each.
Priesthood/atonement/covenant: `melchizedek*` ≈ 9; `day_of_atonement*` ≈ 9; `atonement*` ≈ 8; `covenant_eternal/renewal/blood/creation_order` ≈ 5; `priestly_covenant`, `sacrifice_atonement`, `mercy_and_truth_atonement` 1 each; `sacred_marriage_temple` 3.
Divine-name web: `divine_1…8` ≈ 10–13k each (87k total); `יהוה` 4,863; `אל` 4,711; `divine_title` 4,539; `el_x2` 2,480; `yhwh_x2/x5`, `adonai_x2` ≈ 1.5–2.4k; `divine_sonship` 5,999; `formula_child_of` 5,532; `same_person_eve` 7,006 (Eve/Church); `joseph_smith` 8,796 (Restoration comparators).
Hebrew staples in links: `קדש` (holy) 1,652; `צדקה` (righteousness) 1,713; `שלום` (peace) 2,333; `עבד` (servant) 1,846; `בנים` (sons) 3,397; `הנה` (behold) 1,971; `דבר` (word) 1,514; `מדבר` (wilderness) 2,574; `טוב` (good) 3,039; `מקום` (place) 3,715; `לילה` (night — Ps 134 // Isa 62:6 watchmen) 1,735.

---

## PART G — TYPOLOGY (28 in `typology`)
Adam→Christ (2); Eve→Church; **Melchizedek→Christ (Gen 14:18→Heb 7; Ps 110:4→Heb 7:17)**; Moses→Christ (2); David→Christ; Jonah→Christ; Elijah→John; Joshua→Jesus; Passover→Crucifixion (3, incl. unbroken bones Exod 12:46→John 19:36); Exodus→Redemption; Flood→Baptism/Judgment; Wilderness→Testing (2); **Tabernacle→Heavenly Temple (Exod 25:40→Heb 8:5)**; **Day of Atonement→Christ (Lev 16→Heb 9)**; Bronze serpent→Cross; Manna→Bread of Life; Rock/water→Christ (2); Cities of Refuge→Refuge; Brazen Altar→Cross; **Lampstand→Church/Spirit (Exod 25:31→Rev 1:20)**; **Veil→Body of Christ (Exod 26:31→Heb 10:20)**.

## PART H — SEMANTIC DOMAINS (15) + study lenses
1 sacrifice · 2 temple · 3 covenant · 4 judgment · 5 kingship · 6 warfare · 7 agriculture · 8 wisdom · 9 prophecy · 10 praise · 11 repentance · 12 creation · 13 exile · 14 tribulation · 15 redemption. Use as cross-cutting filters: e.g. Isa 6 = 2+5+9+11; Isa 24 = 4+12+3; Isa 40 = 12+8+5; Isa 52–53 = 1+3+11+15; Isa 60–62 = 2+5+10.

---

## How to use this list
1. Start from PART D when you see an object (robe, veil, coal, branch) — it points to PART F/G for its First-Temple force.
2. Start from PART B when a word repeats across halves — check twin-pair table before assigning it to servant or tyrant.
3. Treat PART A2's 30 types as the "hidden table of contents": every judgment panel has a deliverance twin; find its address before concluding.
4. Numbers (PART C) + gematria (PART B) are confirmatory, never load-bearing alone.
