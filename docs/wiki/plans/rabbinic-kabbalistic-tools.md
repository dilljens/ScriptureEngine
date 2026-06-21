# Rabbinic & Kabbalistic Tools — Planned Items

## Already Built

| Tool | File | Type |
|------|------|------|
| Albam, Atbah, Avgad ciphers | `lib/sod/temurah.py` | Letter substitution |
| Milui, Kellali, Kidmi, Boneh gematria | `lib/gematria.py` | Gematria systems |
| Value columns in DB | `gematria.value_milui/kellali/kidmi/boneh` | Database |
| Semuchin (adjacent verses) | `generators/semuchin.py` | Connection generator |
| Kal v'Chomer (light/heavy) | `generators/kal_vchomer.py` | Keyword detection |

## Planned — Agent-Driven

These items need the agent to read the text systematically and make judgments. No API, no cost — the agent reads verses directly and writes judgment files.

### Mukdam u'Meuchar (מוקדם ומאוחר) — Non-Chronological Order ✅ IMPLEMENTED

**Status: Algorithmic seeding done (2026-06-17). 6 cases identified from rabbinic tradition.**

The principle that the Torah does not always follow chronological order. Earlier events can be mentioned after later ones.

**Implementation:** `generators/mukdam_umeuchar.py` with 6 known cases:
1. Genesis 38 — Judah and Tamar interrupts the Joseph narrative
2. Genesis 36:31 — Kings of Edom mentioned before kings ruled Israel
3. Genesis 35:8 — Deborah's death mentioned out of sequence
4. Exodus 6:14-27 — Genealogy interrupts Moses' call narrative
5. Numbers 7 — Tabernacle offerings chronologically displaced
6. Numbers 9:1-14 — Second Passover before the cloud narrative

**What to detect:**
- A passage that clearly references an event that hasn't happened yet in the narrative timeline
- Cross-book chronological anomalies (e.g., a king mentioned before his reign begins)

**Example:** Genesis 38 (Judah and Tamar) interrupts the Joseph narrative chronologically. The rabbis discussed why this story is placed here.

**Remaining expansion:** Additional cases from Talmudic literature and narrative timeline analysis of the Prophets and Writings.

---

### Sefirotic Mapping

Map verses/words to the 10 sefirot (Kabbalistic tree of life).

**Approach:** Create a mapping table of keywords and concepts to sefirot:
- Keter (Crown): "crown", "head", "will"
- Chokhmah (Wisdom): "wisdom", "beginning", "father"
- Binah (Understanding): "understanding", "mother", "return"
- Chesed (Mercy): "mercy", "lovingkindness", "right hand"
- Gevurah (Judgment): "judgment", "fear", "left hand"
- Tiferet (Beauty): "beauty", "truth", "compassion"
- Netzach (Victory): "victory", "eternity", "prophecy"
- Hod (Splendor): "splendor", "glory", "thanksgiving"
- Yesod (Foundation): "foundation", "covenant", "tzaddik"
- Malkhut (Kingdom): "kingdom", "shekinah", "bride"

**Agent task:** Read verses matching each sefirah's keywords and judge whether the verse is describing that sefirah. Write judgments to `data/agent_connections/sefirot_judgments.json`.

**Estimated effort:** 2-3 sessions. Seed table can be built algorithmically, then refined by agent reading.

---

### Binyan Av (בנין אב) — Establishing a Pattern

One passage establishes a legal/principle pattern that applies to many others.

**Agent task:** Read a passage and judge: "Is this passage establishing a general principle that applies elsewhere?" Requires reading the legal reasoning in Torah.

**Example:** "Thou shalt not seethe a kid in his mother's milk" (Exodus 23:19) — the rabbis derived many dietary laws from this single principle.

**Estimated effort:** 3-4 sessions. Requires strong grounding in what the text actually says vs. what interpreters added.

---

### Mashal (משל) — Parable Interpretation

Identifying when a passage is a parable and what it illustrates.

**Agent task:** Read a passage and judge: "Is this a parable or narrative?" + "What does it illustrate?" Requires literary genre analysis from the text itself.

**Example:** Nathan's parable of the ewe lamb (2 Samuel 12) — a narrative that is actually a rebuke of David.

**Estimated effort:** 2-3 sessions. Genre classification can be done algorithmically (story-within-story markers), but interpretation requires reading.
