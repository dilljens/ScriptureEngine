# ADR 0001: FSRS scheduler ownership — Python authoritative, Go demoted

Status: accepted (2026-09-21) · Plan: hebrew-tutor-phase2 Track P2-C
Deciders: opencode (agent) — overturn on review
Revisit if: palace UI is revived, push notifications ship (P2-B/P10),
or Python/Go scheduling math is unified.

## Context

Two FSRS implementations schedule reviews independently:

- **Python A** — `web/routes/memorize.py:109-183` (verse SRS): state in
  `data/processed/scripture.db` (`memorize_progress`, `memorize_reviews`,
  `memorize_queue`); served at `/api/v1/memorize/*`, `/api/v1/review/*`.
- **Python B** — `web/routes/hebrew.py:44-139` (concept SRS): state in
  `data/memorize.db` (`hebrew_review_state`, `hebrew_progress`,
  `hebrew_attempt_events`); served at `/api/v1/hebrew/*`.
- **Go** — `backend/go-srs/internal/fsrs/fsrs.go` (full fsrs-rs port):
  own store (default `backend/go-srs/data/memorize.db`, NOT the repo file);
  served at `:8090`.

## Investigation findings (2026-09-21)

1. **Same weights, different math.** All three share W and retention 0.9,
   but Go is a full fsrs-rs port (retrievability-dependent stability,
   linear damping, max-interval cap) while both Pythons are simplified —
   and the two Pythons differ from each other (fail threshold
   `rating<=2` vs `rating==1`; speed clamps 0.3–3.0 vs 0.25–4.0).
   Schedules are NOT interchangeable across implementations.
2. **Zero scheduling delegation.** No code path calls across the boundary
   for scheduling: Python→Go is one health probe (`web/server.py:3407`)
   plus one fire-and-forget FIRe-credit POST (`lib/api/assessment.py:500`).
   Go never calls Python. No adapter layer exists — and none is needed:
   the stores are disjoint with zero shared writes.
3. **Go serves no live traffic.** Its only frontend clients
   (`PalaceList`, `PalaceBuilder`, `ReviewSession` via `memorizeApi.js`)
   are orphaned — nothing imports them. Its push endpoints have no
   callers. Prod deploys + restarts the binary and health-checks it, but
   nothing consumes its schedules.
4. **Dev/prod split-brain (latent trap).** Vite proxies `/api/memorize/*`
   → Go `:8090`, but Caddy routes the same prefix → Python `:8000`,
   where those paths 404 (Python serves `/api/v1/memorize/*`). Anyone
   testing memorize UI in dev exercises Go, never prod behavior.
5. **DB collision rule.** Go's schema defines `hebrew_nodes/edges/progress`
   with different columns than Python's. Starting Go with
   `--db data/memorize.db` (repo root) would corrupt Python's tables.
   Default launch is safe (own file); keep it that way.

## Decision

**Python owns all FSRS scheduling state** (verse + concept paths above).
Go retains NO scheduling authority. The Go service stays deployed as a
dormant backend (fsrs-rs reference for future math-parity work; palace/
push host if those UIs are ever revived) — it is not proxied, not fed
ratings, and not read for queues.

## Consequences / rules

- Ratings flow only into Python endpoints; review queues are read only
  from Python endpoints.
- Never start Go with `--db` pointing at repo-root `data/memorize.db`.
- Do NOT build a Python↔Go schedule adapter: disjoint stores, divergent
  math, no consumers — an adapter would be scope without a reader.
- Before reviving palace/push UI, first fix the split-brain: either
  retarget the Vite `/api/memorize` proxy at Python (and rewire or delete
  the orphaned Go-only components) or add an explicit Caddy route for Go
  paths. Until then, dev testing of those components proves nothing.
- Python A vs B math differences (fail threshold, speed clamps) are now
  documented tech debt, not a bug: unifying them is a separate change
  with user-visible scheduling effects — do not sneak it into this ADR.
