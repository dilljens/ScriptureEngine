# Hebrew Curriculum: Expert-Teacher Evaluation

**Reviewer stance:** a Hebrew instructor with 20 cohorts behind them, asked
"would this teach a real student?" — not "is the code clean?" Graded
against what actually moves beginners to readers: sequencing, explanation
quality, exercise design, feedback, and coverage of the known hard parts.

**Verdict: B+ as a curriculum, A- as a system.** The content spine is
sound and the exercise engineering is genuinely excellent. The gaps are
specific and fixable — mostly sequencing decisions and a few
over-simplifications that a teacher would red-pen on day one.

## What's strong (keep)

1. **Sequencing follows the language, not the textbook.** Letters →
   vowels → syllables (L1–L3) before any vocabulary, then 7 levels of
   graded material. This is exactly how good ulpan-style Biblical Hebrew
   courses run. Prerequisites are a real DAG (304 edges), not a list.
2. **Production is engineered, not promised.** Cloze on real verses,
   dictation with audio, parse drills graded by keyword (binyan+form+person
   all required), typed production on verb forms and roots — this is the
   hardest thing to build in a self-study tool and it's here, wired to one
   scheduler. The 40%-production floor with an auditable `mix` field is
   better than most commercial apps do.
3. **Explanations respect the language.** Qal Perfect is taught as *qatal
   with aspect determined by context/genre*, not "past tense." Weak verbs
   get per-class treatment (hollow verbs explain the disappearing vav with
   קָם/יָקוּם). This is teacher-grade content, not phrasebook Hebrew.
4. **Difficulty is real.** Parse requires every token. Typing is
   niqqud-insensitive but sofit-sensitive in grading paths. Distractor pools
   are same-script and sibling-sourced. Nobody is getting fluent by tapping.
5. **The Room + verse blocks.** Authentic text (real pointed verses + audio)
   as the session anchor is exactly what keeps self-study students past
   month three. Coverage dial + tap-to-mine closes the loop Krashen would
   ask for.

## Findings, ordered by teaching impact

### 1. Verb system arrives too late and too thin in places (biggest gap)
Qal Perfect/Imperfect sit at L4–L5 and weak-verb classes carry 4–6 items
each. A student meets wayyiqtol narrative (וַיֹּאמֶר — "and he said") on
page 1 of Genesis, but the curriculum's verbs unlock after ~200 vocab
nodes. Real cohorts need: (a) wayyiqtol recognition *early* (recognition
only, no full conjugation — "this is past narrative, move on"), and
(b) more items on the high-frequency weak classes (hollow, III-He).
Recommend: a `wayyiqtol_recognition` node at L3, +2–3 items each on the
top-5 weak classes.

### 2. Aspect is taught right in one place, contradicted in another
The Qal Perfect lesson correctly teaches aspect-over-tense. But 41+
`typing` drills across verb lessons reduce to "write the 3ms/1cs form" —
pure morphology with no aspect judgment. Students will ace the forms and
still mistranslate qatal as past-tense everywhere. Recommend: a
`discourse_function` item type — "this qatal is past / present / gnomic:
why?" — even 1 per verb lesson changes what the drills select for.

### 3. Vocabulary glosses over-specify, then the grader over-accepts
Spot-check (צָבָא glossed "army / host / warfare"): correct but the
practice items accept any of them via slash-splitting, so a student can
always answer "army" and never learn "host" — and never meets צבאות as
"hosts" in the divine-title sense except incidentally. Recommend: rotate
*which* gloss is the expected answer per item (already have the data —
`additional glosses` exist), and add 1 divine-title context card for the
top ~20 theologically loaded words (אלהים, יהוה, צבאות, קדש...).

### 4. No explicit syntax-to-reading bridge
Syntax nodes (construct chains, nominal clauses) exist; reading nodes
exist; but nothing asks the student to *parse a real verse's syntax*.
The cloze cards blank words, the T/F checks word presence — neither asks
"what is the subject of this clause?" Recommend: `syntax_parse` items on
reading nodes — bracket the construct chain / find the verb — auto-gradable
(choose the head noun / verb from 4 verse words).

### 5. Transliteration scheme is never taught as a system
Transliteration appears as hints and answers, but no lesson teaches the
scheme itself (e.g. why כָּתַב = kātav, what the macrons mean). Students
infer it — or don't, and the hints become noise. Recommend: one short
L2 lesson "How to read the pronunciation guides."

### 6. Minor content bugs (fix directly)
- `binyan_intro` shipped a templated nonsense question ("function of the
  Introduction to Binyanim binyan?") — FIXED this session + validator
  guard added. Audit remaining titles for the same template (15 nodes had
  the pattern; only binyan_intro was semantically broken).
- Root lesson `derived_words` sometimes includes marginal forms; fine at
  this stage, revisit if learners report confusion.

## Coverage map (expert pass)

| Skill | Verdict |
|---|---|
| Alphabet/vowels/syllables | Strong. Complete, well-sequenced. |
| Core vocab (top ~500) | Strong both directions + audio + context. |
| Qal system | Good explanations, adequate drills; needs aspect judgment (finding 2). |
| Weak verbs | Present and correct, thin on reps for hollow/III-He. |
| Nouns/adjectives/construct | Present; application thin (16 R2 cards total — grow to ~40). |
| Syntax → reading transfer | **Missing** (finding 4). Highest-leverage addition. |
| Roots | Good (17 families + extraction writing). |
| Listening | Word-level dictation only; verse-level gated sensibly. |
| Reading stamina | Verse blocks + passage reader exist; no timed/progressed reading ladder yet. |

## Bottom line for the T1 tutor spec
The bank is strong enough that a tutor can stay grounded in it without
needing to invent content — which is exactly the constraint the T1 spec
below enforces. The tutor's highest-value moves map to the gaps above:
aspect judgments, theological-gloss rotation, syntax parses of real
verses, and wayyiqtol recognition — all *orchestration* of existing
content, not new content.
