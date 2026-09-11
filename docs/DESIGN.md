# EMET — design constitution (game design best practices applied)

Theme: **the Golem**. You are a *Baal Shem* animating clay servants by inscribing
Hebrew letters. Letters are the generators. Knowledge is the currency.
Prestige = erasing the א of אמת (truth → מת, death) and re-inscribing stronger.

Sources: MDA, flow, SDT/PENS, Koster, Schell, Vlambeer screenshake,
Pecorella "Math of Idle Games", Bjork desirable difficulties, Habgood &
Ainsworth intrinsic integration, Duolingo HLR + streak findings, L4D AI Director.

## Target aesthetics (MDA) — pick these, defend them
**Discovery + Sensation + Submission (pastime)**, light **Challenge**.
Not a puzzle app. If a feature raises difficulty but not discovery/sensation, cut it.

## The one rule (intrinsic integration)
The Hebrew must *be* the mechanic, never a quiz bolted on.
Recalling a letter animates it; a wrong recall fizzles the golem, never drains the bank.
(Evidence: Habgood & Ainsworth — intrinsic versions were learned more AND played 7x longer.)

## Fun checklist (apply to every feature)
- [ ] 30-second loop feels good **and** the long arc has peaks + breathers (Koster sine wave).
- [ ] Real choice (autonomy): which letter, when to forge a root, which boost.
- [ ] Clear feedback on every action (competence): Koster's 4 questions — what can I do,
      did I do it, what changed, did it help.
- [ ] Regular "better than expected" jumps (predictive-processing engine of idle fun).
- [ ] No dead time — every gap has a quest or a due review.
- [ ] Numbers anchored to meaning ("you know 300 words"), not raw digits.
- [ ] Juice = gameplay here, not decoration (low-interaction game).

## Juice budget (highest ROI first)
1. Core action: squash-stretch + floating number + sound + 3px shake. *(done: tap floater)*
2. **Visible agents** — the Incremancer lesson. Abstract number → golems roaming. *(this build)*
3. rAF counters, transform/opacity only, `prefers-reduced-motion`, mobile particle caps.
4. Sound with ±10% pitch variation + mute.
5. Milestone permanence (leave a mark, don't delete effects).

## Idle math rules
- cost_next = base·1.15^owned (exponential); production linear × multipliers → walls on schedule.
- Leaders must **shift** over time (no permanently dominant letter) — use mastery multipliers
  and synergy so studying a *new* letter beats spamming a maxed one.
- Automation is a **design feature, not cheating** (Pecorella): bulk-buy done; autobuy later.
- Prestige formula chosen for behavior: **independent/since-reset leans short repeat sessions**
  (Duolingo: bingers quit more) → reward consistency, not binges.
- Offline = gift, capped; show "while you were away". Rest is supported, never punished.

## Learning integrity
- Retrieval is the core verb (intrinsic).
- Per-item strength (curriculum mastery) drives yield; rusty letters weak.
- Interleave H↔E↔audio; errors informative + cheap + instantly retryable.
- Meta-rewards only flow through learning. Never randomize whether learning succeeds.
- Measure learning (mastery deltas), not just session length.

## Onboarding (first 5 minutes)
0:00 tap a letter → golem rises + word/meaning/audio. 0:45 first automation reveals.
2:00 first real choice. 3:00 first due-review quest. 5:00 offline preview.
≤3 new concepts at once (working memory). Prime → Teach → Observe. Fade scaffolding.

## Difficulty
Flow channel; hidden gentle DDA (L4D director); help the weak without changing the strong.
Player-steered bias buttons + implicit 70–90% accuracy targeting *(done)*.
Fair failure, cheap retry, informative errors.

## Anti-patterns we will not ship
- Feedback with no problem underneath (Koster: "shallow, at worst exploitative").
- Meaningless choices / one dominant generator.
- Runaway number soup with no meaning anchors.
- Streak anxiety (give an Amulet-style break).
- Pay-to-win: there is nothing to pay — learning is the only speed currency.
- Reflex gates (13s golden cookie) → replaced by 20s accuracy windows.
