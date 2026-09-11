# Learning review — is the current design optimal for learning?

Assessed against the evidence (Bjork & Bjork desirable difficulties; Roediger &
Karpicke 2006 test-enhanced learning; Rohrer & Taylor 2007 interleaving;
Habgood & Ainsworth 2011 intrinsic integration; Settles & Meeder 2016
half-life regression; Mogavi et al. 2022 on gamification misuse).

## Verdict: strong on retrieval, was weak on feedback. Fixed.

| Dimension | Grade | Evidence / notes |
|---|---|---|
| Retrieval practice (testing effect) | **Strong** | The entire game *is* retrieval — correct answers are the only tap that earns. No passive reading loop to game. |
| Corrective feedback | **was Failing → now Adequate+** | The server returned only a bare `is_correct`. No correct answer, no explanation, despite both existing in `hebrew_practice_items`. Fixed: `POST /hebrew/progress` now returns `correct_answer` + `explanation`, and the quiz shows them after every answer (right or wrong). |
| Spacing | **Adequate** | FSRS-5 schedules each node's next review; `hebrew_review_state` tracks stability/difficulty/due. But the game did not *surface* due items — now the "🔁 Review due" button pulls exactly those. |
| Interleaving | **Adequate** | Cumulative quiz mixes categories (good); per-lesson quiz is blocked to one node, partially offset by **confusable distractors** from `hebrew_confusability` (non-interference/discrimination practice). Evidence says interleaved beats blocked ~63% vs 20% on delayed tests, so the game should drift toward interleaved as history accrues. |
| Desirable difficulty | **Adequate** | Per-question timers + the adaptive `bias` (explicit buttons + implicit 70–90% accuracy targeting). Production items (typing) are genuinely hard; recognition (MC) is easy. Ordered recognition → production within a lesson. |
| Generation effect | **Strong** for typing/recall | Flashcards ask for the answer rather than showing it. |
| Bidirectional (H→E and E→H) | **Partial** | Both directions exist in the item bank (`What is '{hebrew}' mean?` vs `What is Hebrew for '{gloss}'?` / `Type the Hebrew word`), but the mix is not *enforced* per session. A learner could get a run of only-recognition items. |
| Mastery gating | **Good** | Prerequisites unlock at mastery ≥ 0.8; `source` distinguishes practised vs tested-out so placement credit can't masquerade as mastery. |
| Intrinsic integration | **Strong** | Habgood & Ainsworth's finding (intrinsic > extrinsic, and 7× more time on task) is the design's spine: recall *is* the game verb, not a quiz bolted between levels. |
| Error handling | **Good** | A wrong answer costs only the streak — it never drains Ohr, never punishes. Evidence: unsuccessful retrieval attempts still enhance later learning, so errors are pedagogically valuable. |
| Gamification risk | **Watch** | Mogavi et al.: learners fixate on the meta-game and get distracted. Mitigation in place — learning is the *only* path to the reward (no way to buy Kavod), and there is no separate XP grind to optimise instead of study. |
| Pronunciation / audio | **Absent (opted out)** | User listens to audiobooks; sound is deliberately out of scope. Note this is a real gap for Hebrew specifically (the script encodes sound), flagged but not actioned. |

## What changed in this pass

1. **Corrective feedback** (backend + quiz UI) — the biggest defect. Answers now
   come with the correct answer and a one-line explanation.
2. **In-game practice popup** (`GameReviewModal`) — you no longer leave the game
   to learn; the lesson quiz runs in an overlay over the golems. This protects the
   flow state (and the intrinsic-integration premise) that navigating away broke.
3. **Due-review surfaced** — a "Review due" button wired to the FSRS queue, so
   spacing is available from inside the game, not only via the curriculum page.

## Still suboptimal (ranked)

1. **Direction mix unenforced.** Guarantee ≥40% production (E→H / typing) per
   session; a run of multiple-choice is recognition training, not recall.
2. **No re-ask of missed items.** Re-presenting a failed item before the session
   ends exploits the "unsuccessful retrieval enhances learning" finding and
   closes the correction loop immediately.
3. **Recognition-heavy bank.** Check the type distribution per node; if MC
   dominates, weight `typing`/`recall` as mastery rises.
4. **Interleaving only at the cumulative level.** Prefer interleaved practice in
   the game popup once the learner has enough history for it to return items.
5. **No pronunciation input.** Deferred by choice; would matter most for real
   Hebrew fluency.
