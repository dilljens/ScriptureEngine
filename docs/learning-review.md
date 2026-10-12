# Learning Review: Is the Current Design Optimal for Learning?

## Abstract

This review asks whether a Hebrew-vocabulary game built around retrieval is optimal for learning, judged against six learning-science findings. The method is evidence-against-design audit: each mechanism (retrieval, feedback, spacing, interleaving, integration, gamification) is graded against what the cited studies found. The finding is that the design was strong on retrieval but failing on feedback, and that the present pass fixes feedback, in-game practice, and due-review surfacing — while direction mix, re-asking, bank balance, interleaving depth, and pronunciation remain suboptimal.

## Introduction

The problem is practical: a game that rewards correct taps may train tapping rather than Hebrew. The question therefore is not whether learners play, but whether each loop — answering, feedback, scheduling, mixing — matches what the evidence says causes durable learning. Why it matters is that design choices compound: a missing feedback step or an unenforced direction mix silently converts recall training into recognition training.

The roadmap is as follows. First, the six studies this verdict rests on, each with what it found and why it governs here; then the graded audit, dimension by dimension, with each grade unpacked; then what changed in this pass and why; then ranked remaining gaps with threats to the verdict; and finally a conclusion.

## Context: The Studies Argued With

Every cited work is introduced here so no name stands as a bare authority.

- **Bjork & Bjork on desirable difficulties.** Who: Robert and Elizabeth Bjork (UCLA), the psychologists of difficulty-as-feature. What they found: conditions that slow initial performance (spacing, interleaving, generation, varied practice) improve long-term retention. Why they matter here: they supply the "Adequate" standard for timers, adaptive bias, and production difficulty.
- **Roediger & Karpicke (2006) on test-enhanced learning.** Who: the testing-effect researchers. What they found: retrieval practice produces stronger delayed retention than restudying. Why they matter here: they justify the "Strong" on retrieval — the entire game *is* retrieval — and the generation-effect grade.
- **Rohrer & Taylor (2007) on interleaving.** Who: the mathematics-learning interleaving researchers. What they found: interleaved practice beats blocked practice (here cited as ~63% vs 20% on delayed tests). Why they matter here: they set the bar the per-lesson blocked quiz only partly meets, and the reason the game should drift toward interleaved as history accrues.
- **Habgood & Ainsworth (2011) on intrinsic integration.** Who: the game-based-learning researchers. What they found: intrinsic integration (learning as the game verb) outperforms extrinsic framing, with far more time on task (here cited as 7×). Why they matter here: they are the design's spine — recall *is* the game verb — and the reason the practice popup protects flow instead of navigating away.
- **Settles & Meeder (2016) on half-life regression.** Who: the Duolingo researchers whose half-life regression model for recall informs modern schedulers including FSRS. What they found: recall likelihood can be modeled as decay with half-life regression for scheduling. Why they matter here: they underwrite the spacing grade — FSRS-5 schedules each node's next review via stability/difficulty/due in `hebrew_review_state`.
- **Mogavi et al. (2022) on gamification misuse.** Who: the authors of a case study on gamification's failure modes. What they found: learners fixate on the meta-game and get distracted from learning. Why they matter here: they motivate the "Watch" grade and its mitigation — learning as the *only* path to reward, with no separate XP grind.

## Audit: Dimension by Dimension

The verdict overall is **strong on retrieval, was weak on feedback — now fixed**. Each dimension below states the grade, what it says, what it means, and why the evidence supports it.

**Retrieval practice (testing effect): Strong.** The entire game *is* retrieval — correct answers are the only tap that earns, with no passive reading loop to game. That means every rewarded action is a retrieval attempt, which is exactly what Roediger & Karpicke found durable.

**Corrective feedback: was Failing → now Adequate+ (pending code-diff verification).** The server returned only a bare `is_correct`, with no correct answer and no explanation, despite both existing in `hebrew_practice_items`. What that meant was that errors ended the trial without correction. Fixed: `POST /hebrew/progress` now returns `correct_answer` + `explanation`, and the quiz shows them after every answer (right or wrong).

**Spacing: Adequate (pending code-diff verification).** FSRS-5 schedules each node's next review; `hebrew_review_state` tracks stability/difficulty/due. What was missing was surfacing: the game did not *surface* due items. Now the "🔁 Review due" button pulls exactly those, so scheduling is available from inside the game per Settles & Meeder's logic.

**Interleaving: Partial.** The cumulative quiz mixes categories (good); the per-lesson quiz is blocked to one node, partially offset by **confusable distractors** from `hebrew_confusability` (non-interference/discrimination practice — related but not interleaving). What this means against Rohrer & Taylor is a split grade: mixed at the top, blocked at the bottom. Evidence says interleaved beats blocked ~63% vs 20% on delayed tests, so the game should drift toward interleaved as history accrues.

**Desirable difficulty: Adequate.** Per-question timers plus the adaptive `bias` (explicit buttons + implicit 70–90% accuracy targeting) hold difficulty in the productive band. Production items (typing) are genuinely hard; recognition (MC) is easy, and ordering recognition → production within a lesson follows the Bjorks' gradient from easier to harder retrieval.

**Generation effect: Strong for typing/recall.** Flashcards ask for the answer rather than showing it — the learner generates before judging — which is the Roediger-side mechanism in miniature.

**Bidirectional (H→E and E→H): Partial.** Both directions exist in the item bank (`What is '{hebrew}' mean?` vs `What is Hebrew for '{gloss}'?` / `Type the Hebrew word`), but the mix is not *enforced* per session. A learner could get a run of only-recognition items, which would mean recognition training masquerading as recall training.

**Mastery gating: Good.** Prerequisites unlock at mastery ≥ 0.8; `source` distinguishes practised vs tested-out so placement credit can't masquerade as mastery. The threshold plus the provenance flag together keep advancement honest.

**Intrinsic integration: Strong.** Habgood & Ainsworth's finding (intrinsic > extrinsic, and 7× more time on task) is the design's spine: recall *is* the game verb, not a quiz bolted between levels. Because progress requires recall, there is no path that bypasses learning.

**Error handling: Good.** A wrong answer costs only the streak — it never drains Ohr, never punishes. What this means pedagogically is that errors stay safe; why it matters is the evidence that unsuccessful retrieval attempts still enhance later learning, so errors are pedagogically valuable rather than merely tolerated.

**Gamification risk: Watch.** Mogavi et al. found learners fixate on the meta-game and get distracted. Mitigation in place — learning is the *only* path to the reward (no way to buy Kavod), and there is no separate XP grind to optimise instead of study — but the risk is structural, not solved.

**Pronunciation / audio: Absent (opted out).** The user listens to audiobooks; sound is deliberately out of scope. This is flagged as a real gap for Hebrew specifically (the script encodes sound) — noted but not actioned.

## What Changed in This Pass

Three fixes, each tied to the audit above. First, **corrective feedback** (backend + quiz UI) — the biggest defect: answers now come with the correct answer and a one-line explanation. Second, **in-game practice popup** (`GameReviewModal`) — the learner no longer leaves the game to learn; the lesson quiz runs in an overlay over the golems, which protects the flow state (and the intrinsic-integration premise) that navigating away broke. Third, **due-review surfaced** — a "Review due" button wired to the FSRS queue, so spacing is available from inside the game, not only via the curriculum page.

## Still Suboptimal, Ranked — With Threats to the Verdict

1. **Direction mix unenforced.** Guarantee ≥40% production (E→H / typing) per session; a run of multiple-choice is recognition training, not recall. Threat: the "Strong on retrieval" verdict overstates if sessions skew recognition.
2. **No re-ask of missed items.** Re-presenting a failed item before the session ends exploits the "unsuccessful retrieval enhances learning" finding and closes the correction loop immediately. Threat: feedback without re-ask corrects without consolidating.
3. **Recognition-heavy bank.** Check the type distribution per node; if MC dominates, weight `typing`/`recall` as mastery rises. Threat: bank composition, not session logic, quietly sets difficulty.
4. **Interleaving only at the cumulative level.** Prefer interleaved practice in the game popup once the learner has enough history for it to return items. Threat: per-lesson blocking caps the Rohrer & Taylor benefit.
5. **No pronunciation input.** Deferred by choice; would matter most for real Hebrew fluency. Threat: orthography–phonology mapping stays untested, a real gap for this script.

Further threats: grades rest on design inspection plus cited effects, not on learner-outcome data (session event logs exist — the game's analytics export, documented in `docs/balancing-analytics.md` — but no A/B outcome results); the 63%-vs-20% and 7× figures are carried from the cited studies' contexts, not measured in this game.

## Conclusion

Retrieval is the game, feedback now closes the loop, spacing is surfaced, and integration holds — but enforcement (direction mix, re-ask, interleaving depth) is what turns an adequate design into an optimal one. The next pass should enforce the mix, re-ask misses, and weight production as mastery rises.

## Works Argued With

- Bjork, Robert A. (1994), "Memory and Metamemory Considerations in the Training of Human Beings," in Metcalfe & Shimamura (eds.), *Metacognition* (MIT Press) — coinage of desirable difficulties; accessible synthesis in Bjork & Bjork (2011), "Making Things Hard on Yourself…," in Gernsbacher et al. (eds.), *Psychology and the Real World* (Worth).
- Roediger, H. L. & Karpicke, J. D. (2006), "Test-Enhanced Learning," *Psychological Science* 17(3) — retrieval practice; source of the delayed-retention figures.
- Rohrer, D. & Taylor, K. (2007), "The Shuffling of Mathematics Problems Improves Learning," *Instructional Science* 35(6) — interleaving (~63% vs 20% delayed).
- Habgood, M. P. J. & Ainsworth, S. (2011), "Motivating Children to Learn Effectively," *Journal of the Learning Sciences* 20(2) — intrinsic integration (7× time on task).
- Settles, B. & Meeder, B. (2016), "A Trainable Spaced Repetition Model for Language Learning," *Proc. ACL* (long papers) — half-life regression; informs FSRS scheduling (venue corrected from earlier drafts).
- Mogavi, R. H. et al. (2022), "When Gamification Spoils Your Learning," *Proc. L@S* — gamification-misuse case study (not a systematic review).
