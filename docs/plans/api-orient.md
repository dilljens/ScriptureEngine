---
status: completed
kind: plan
area: api
author: external (James Jensen) / opencode
created: 2026-08-25
completed: 2026-08-25
inbox: docs/inbox/proposal-api-orient.md, docs/inbox/report-api-field-notes.md
---

# Project: API Orient — Ship the Instructions Inside the API

Implement the actionable items from James Jensen's field-tested proposal and
report. Priority order is his; every defect below was verified live twice.

## Requirements

- [x] R1: Unknown `/api/*` paths return a real JSON 404, never the SPA HTML.
- [x] R2: API errors teach: verse-ref 404s carry `hint` + `see` pointers.
- [x] R3: Every registered tool works through `/api/v1/tools/{name}` — the
  `scripture_gematria` wrapper's `transliterate(strip_accents=)` drift is
  fixed and an all-tools smoke test locks it.
- [x] R4: `GET /api/v1/orient` gives a machine its first-call briefing
  (< ~6KB): what this is, live health incl. degraded capabilities,
  conventions, capability map with when-to-use, topic index with next-step.
- [x] R5: `GET /api/v1/orient/{topic}` serves depth on demand for
  refs / quality / layers / limits / research.
- [x] R6: Orient is discoverable from `/`, OpenAPI description, and the
  JSON 404 body (`see`).
- [x] R7: Health reports which capabilities are degraded, not just flags.
- [x] R8: Psalms responses expose dual numbering (`kjv_verse`/`mt_verse`)
  where interlinear vs KJV diverge; convention documented in `refs` topic.
- [x] R9: Corpus limits are published (no LXX; Cloudflare UA behavior noted
  for client authors).

## Non-goals

- No auth, no rate-limit changes, no schema churn beyond additive fields.
- `/metrics` mounting decision deferred unless it's a one-liner (verify why
  it's advertised but unserved first).
- No LXX ingestion — documenting the limit, not closing it.

## Phases

### Phase J1: Honest 404s + errors that teach `[x]`
SPA catch-all excludes `/api/*`; exception handler adds `hint`/`see` to
verse-not-found and unknown-tool errors. Tests: unknown API path → JSON 404;
bad ref → hint present.

### Phase J2: Gematria wrapper fix + all-tools smoke `[x]`
Fix `transliterate()` call drift; smoke test calls every registered tool once
with schema-example args against a fixture DB, asserting no 500-class errors.

### Phase J3: orient endpoint + topics `[x]`
`web/routes/orient.py`: index route + topic routes reading markdown-ish
constants; health section reuses server health checks incl. degraded list;
discoverability hooks (root payload line, OpenAPI description, 404 `see`).

### Phase J4: Dual psalm numbering + health degradation `[x]`
Additive fields on verse payloads for superscripted psalms; `/health`
gains `degraded: [...]` with consequence strings.

### Phase J5: Verification + docs `[x]`
Full pytest/vitest; wiki web-api page updated; deploy.

## Acceptance

A fresh client can: probe safely by status code, learn ref syntax from the
first error it triggers, orient itself under 6KB, verify language claims via
documented loop, and know exactly what the corpus cannot see.
