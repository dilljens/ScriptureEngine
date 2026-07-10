# Hebrew Learning System — Improvement Plan

Based on gap analysis against The Math Academy Way (June 2026 draft).

## Completed (Phase 1)
- Automaticity timed drills (per-question countdown, type-scaled limits)
- Targeted remediation (prerequisite suggestions on wrong answers)
- Speed stats in lesson results

## Remaining Phases

### Phase 2: Diagnostic Pre-Assessment
**Goal:** Determine what the learner already knows before starting, skip mastered topics.

**Implementation:**
1. Create `GET /api/v1/hebrew/diagnostic` endpoint that:
   - Selects 2-3 sample questions from each category (consonant, vowel, word, grammar, reading)
   - Returns them as a pre-assessment batch
2. Create diagnostic UI before entering curriculum:
   - Shows 10-15 quick questions covering all categories
   - On 100% correct per category → mark all those category nodes as mastered
   - On 60-80% → mark as "review only" (mastery = 0.7)
   - On <60% → keep full curriculum
3. Store diagnostic results in `hebrew_progress` table

**Files:** `web/server.py` (or routes/hebrew.py), `frontend/src/components/HebrewDiagnostic.jsx`, `frontend/src/components/HebrewLearnView.jsx`

**Effort:** Medium | **Impact:** 🔴 Critical

---

### Phase 3: Systematic Interleaving
**Goal:** Replace random quick mode with cross-category mixed practice.

**Implementation:**
1. Update review queue endpoint to enforce category diversity:
   - No 2 consecutive questions from same category
   - Balance across: recognition (MC/TF), recall (transliteration/cloze), production (typing)
   - Ensure connected topics aren't practiced back-to-back
2. Update quick session mode to pull from diverse categories
3. Track practice history per session to maintain spread

**Files:** `web/routes/hebrew.py` (review queue logic), `frontend/src/components/HebrewLearnView.jsx` (quick mode)

**Effort:** Medium | **Impact:** 🟡 High

---

### Phase 4: Micro-Scaffolding (3 KPs per Lesson)
**Goal:** Each lesson has progressive Knowledge Points like Math Academy.

**Implementation:**
1. Restructure HebrewLessonView to support 3-stage KPs:
   - **KP1: Recognition** (MC easy) — worked example → 2 practice
   - **KP2: Recall** (cloze/translit) — worked example → 2 practice
   - **KP3: Production** (typing/sentence) — worked example → 2 practice
2. Each KP must be passed before advancing to next
3. Failed KP → review that KP's content specifically
4. Generate KP structure from existing practice items (classify by type)

**Files:** `frontend/src/components/HebrewLessonView.jsx`

**Effort:** Medium | **Impact:** 🟡 High

---

### Phase 5: Connect FSRS-5 + FIRe for Hebrew
**Goal:** Use the existing FSRS-5 engine (verified against Rust test vectors) for Hebrew concept scheduling.

**Implementation:**
1. Create bridge endpoint: `POST /api/go-srs/hebrew/review`
   - Takes node_id + rating (again/hard/good/easy)
   - Routes to Go backend's FSRS-5 engine
   - Returns next review interval
2. Create FIRe bridge: `POST /api/go-srs/hebrew/fire/{node_id}`
   - Routes to Go backend FIRe engine
   - Gives implicit repetition credit to connected prerequisite nodes
3. Update review queue to pull from FSRS-scheduled reviews instead of the current simple formula
4. The Go backend already has FSRS-5 tested, `hebrew_nodes` table, `hebrew_edges` table — it's ready

**Files:** `web/server.py` (proxy routes), `backend/go-srs/internal/handlers/handlers.go` (may need adjustment), `frontend/src/components/HebrewLearnView.jsx`

**Effort:** Medium | **Impact:** 🟡 High

---

### Phase 6: Non-Interference in Topic Ordering
**Goal:** Similar/confusable topics are separated by 2-3 other lessons.

**Implementation:**
1. Build confusability matrix:
   - Shin (שׁ) vs Sin (שׂ) — same letter, different dot
   - He (ה) vs Chet (ח) — similar pronunciation in some traditions
   - Bet (ב) vs Vav (ו) — similar sounds
   - Samekh (ס) vs Sin (שׂ) — same sound
   - Tet (ט) vs Tav (ת) — similar in some traditions
   - Ayin (ע) vs Aleph (א) — both gutturals
2. In curriculum generation, ensure confusable pairs are separated by ≥3 other nodes
3. Label confusable pairs in the DB for reference

**Files:** `scripts/seed_hebrew_confusability.py` (new), `web/routes/hebrew.py`

**Effort:** Low | **Impact:** 🔵 Medium

---

### Phase 7: Student-Topic Learning Speeds
**Goal:** Track per-user ability per-topic via ability/difficulty ratio.

**Implementation:**
1. Track per-user per-topic accuracy over time (add to hebrew_progress table)
2. Compute ability: user's recent weighted accuracy across all practiced topics
3. Compute difficulty: 1 - average accuracy of all users on this topic
4. learning_speed = ability / difficulty
5. Adjust review intervals: interval *= (1 / learning_speed)
6. If learning_speed < 0.5, force explicit reviews (no FIRe credit)

**Files:** `web/routes/hebrew.py` (review queue logic), `frontend/src/components/HebrewLessonView.jsx` (accuracy tracking)

**Effort:** High | **Impact:** 🟡 Medium
