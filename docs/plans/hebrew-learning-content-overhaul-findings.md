# Findings: Biblical Hebrew learning content overhaul

## Existing system

The live learning database contains 671 nodes, 671 lessons, 4,622 practice
items, 270 prerequisite edges, and 1,716 verse attestations. It has useful
coverage and a promising passage reader, but lesson JSON has multiple schemas,
base graph edges are reversed relative to newer seeders, and several UI paths
do not actually grade learner answers.

## Highest-risk audit findings

1. Base prerequisite edges use the reverse of the API's expected direction.
2. Normal lesson drills reveal answers and accept self-ratings without objective assessment.
3. Two diagnostic questions can mark an entire category—including 518 words—mastered.
4. Vocabulary examples use substring matching across all works; many examples come from DSS.
5. Review, keyboard, quiz-result, timed-question, vocabulary/audio, and reading flows contain wiring defects.
6. Seed content includes errors in begadkephat, syllabification, root extraction,
   construct chains, suffixes, verbal semantics, numerals, and verse references.

## Authoritative source policy

- **Embed:** Open Scriptures Hebrew Bible (WLC text public domain; morphology and
  lemmas CC BY 4.0), Tanach.us UXLC Hebrew text, and STEP Bible Data (CC BY 4.0),
  with exact version and attribution.
- **Conditional:** ETCBC/BHSA and SHEBANQ are CC BY-NC 4.0; obtain permission for
  commercial use.
- **Link only until license verification:** Sefaria versions without explicit
  compatible metadata, Mechon Mamre, Bible OL exercises, Aleph with Beth media,
  and Daily Dose of Hebrew media.
- **Grammar:** produce original prose informed by public-domain Gesenius-Kautzsch-Cowley
  and cited modern scholarship; do not reproduce copyrighted tables or exercises.

## Pedagogy

Use short meaningful reading from the beginning, but combine it with concise
explicit explanations suitable for adults. Require retrieval before reveal,
space reviews over time, and interleave confusable forms after a short blocked
introduction. Score script recognition, segmentation, parsing, interpretation,
and lexicon use separately.

## Essential reading sequence

1. Consonants/final forms, niqqud, begadkephat, shewa, dagesh, and syllables.
2. Maqqef, stress, major accents, furtive patah, qamets qatan, and matres lectionis.
3. Segmentation: conjunction/article/prepositions, noun state, construct chains,
   agreement, and pronominal suffixes.
4. Strong verbs, stems as lexical patterns rather than fixed meanings, and full parsing.
5. Narrative wayyiqtol/weqatal, weak verbs, ketiv/qere, lexicon use, and unseen reading.

## Unicode and RTL rules

Store Hebrew in logical order; never reverse strings manually. Preserve the
canonical corpus form and use a separate normalized search key. Mark Hebrew UI
with `dir="rtl"` and `lang="he"`; do not indiscriminately NFC-normalize OSHB
combining marks. Keep maqqef, accents, and ketiv/qere metadata even when a
beginner display hides them.

## Research sources

- <https://github.com/openscriptures/morphhb>
- <https://www.tanach.us/>
- <https://github.com/STEPBible/STEPBible-Data>
- <https://github.com/ETCBC/bhsa>
- <https://shebanq.ancient-data.org/>
- <https://learner.bible/>
- <https://freehebrew.online/>
- <https://dailydoseofhebrew.com/>
- <https://en.wikisource.org/wiki/Gesenius%27_Hebrew_Grammar>
- <https://unicode.org/reports/tr9/>
- <https://www.w3.org/International/questions/qa-html-dir>
- Roediger & Karpicke (2006), Cepeda et al. (2006), Dunlosky et al. (2013),
  Nation's Four Strands, and ACTFL target-language guidance.
