---
status: implemented
kind: proposal
area: api
author: external
created: 2026-07-27
updated: 2026-08-23
---

# Proposal — ship the instructions *inside* the API (`/api/v1/orient`)

**From:** James Jensen, after building a lesson end-to-end against the live API.
**Status:** proposal, not a patch. Nothing here has been implemented.

Originally sent by email 2026-07-27; landed here 2026-08-23 so it lives where
the work does. **Every figure below re-verified against `scriptureengine.org` on
2026-08-23**, and the case has grown rather than shrunk — see *What changed*
at the end.

---

## The ask in one sentence

Add a single endpoint that tells a machine how to use this API correctly — capability
map, the handful of conventions that prevent most first-hour errors, and an index of
deeper topics to fetch on demand — so that a new client's first call teaches it
everything it needs to make the second call.

## Why this is worth doing here specifically

You already have the instinct. `GET /api/v1/chat/instructions` returns a 48,000-character
system prompt with a tool index by family, a "typical study flow," and a rules section.
That is genuinely good, and most projects don't have it.

But it is aimed at **the model inside your chat box**, not at **a client driving your
HTTP API**. It tells an assistant how to *think about scripture*. It does not tell an
integrator that verse references are dotted book IDs, that unknown paths return HTTP 200
with SPA HTML, or that `quality: "suggested"` means "an algorithm proposed this."

Every one of those cost real time on first contact. None of them are discoverable from
`/openapi.json`, because they are conventions and semantics rather than schemas — exactly
the class of knowledge an OpenAPI document cannot carry.

**The gap is not documentation. It is that the operational knowledge lives in a
maintainer's head and in a Swagger page a machine won't read.**

## The model: `orient` from machine-context

The pattern being proposed is borrowed from a tool we use locally called
`machine-context`. Its `orient` command is the first thing any agent runs. Its output is
roughly:

1. **Who you are acting as** — identity and what each identity can do
2. **A capability map** with *when to use which*
3. **Live health** of subsystems, so degraded capability is visible up front
4. **Conventions** — the short list of rules that prevent the common mistakes
5. **A topic index with `when-to-use` lines**, so the agent fetches only what its task
   needs rather than swallowing everything
6. **A NEXT line** — an explicit instruction on what to read before acting

The essential trick is (5): **orient stays small by being an index, not a manual.** It
names topics and says when each matters. Depth is a second call.

## Concrete proposal

### 1. `GET /api/v1/orient` — the front door

Small (target: under 4 KB), stable, and safe to call on every session start.

```jsonc
{
  "ok": true,
  "data": {
    "service": "Scripture Knowledge Engine",
    "version": "1.0.0",
    "what_this_is": "77,231 verses across 19 works with 1.91M typed connections. Read-only public API; no key required.",

    "health": {
      "database": true, "fts_index": true, "vector_search": true,
      "go_srs": false,
      "degraded": ["go_srs — spaced-repetition scheduling unavailable; /memorize/* may 5xx"]
    },

    "conventions": [
      "Verse refs are dotted book IDs: gen.1.1, matt.16.16, dc88.88.67. Human strings like 'Genesis 1:1' will 404. Get IDs from /api/v1/books.",
      "Unknown paths return HTTP 200 with the SPA's HTML, not 404. Check for an {ok:...} body, never status alone.",
      "All JSON responses are {ok:true,data:...} or {ok:false,error:...}; HTTP errors are FastAPI {detail:...}.",
      "Psalms: the English endpoints use KJV numbering, the interlinear uses Hebrew (MT) numbering. For psalms with a superscription these differ by one.",
      "connection.quality grades confidence, not truth: 'suggested' and 'pattern' are algorithmic proposals, 'tsk' means Treasury of Scripture Knowledge. Verify before citing."
    ],

    "capabilities": [
      {"name": "lookup",      "when": "you have a reference and want text, gematria, JST, connections", "start": "/api/v1/verses/{ref}"},
      {"name": "guide",       "when": "you want everything precomputed about one verse, bucketed by layer", "start": "/api/v1/verses/{ref}/guide"},
      {"name": "search",      "when": "you have words, not a reference", "start": "/api/v1/search?q="},
      {"name": "language",    "when": "you need to VERIFY a claim about the Greek or Hebrew", "start": "/api/v1/tools/scripture_interlinear"},
      {"name": "tools",       "when": "you want the whole callable surface with JSON Schemas", "start": "/api/v1/tools"}
    ],

    "topics": [
      {"id": "refs",        "when": "before constructing any verse reference"},
      {"id": "quality",     "when": "before citing a connection as evidence"},
      {"id": "layers",      "when": "before interpreting the 11 connection layers"},
      {"id": "limits",      "when": "before concluding the corpus does not contain something"},
      {"id": "research",    "when": "doing multi-verse study — the guide→targets→verify loop"}
    ],

    "next": "Read the topics matching your task via /api/v1/orient/{id} BEFORE acting. If you are about to quote a cross-reference, read 'quality' first."
  }
}
```

### 2. `GET /api/v1/orient/{topic}` — depth on demand

Returns prose (markdown is fine). This is where the real knowledge goes, and it costs a
client nothing until they need it. Suggested starting set:

- **`refs`** — book ID list by work, the D&C `dc88.88.67` double-numbering, Psalms
  versification, what happens with apocryphal/DSS sigla like `1QS` and `4Q400`.
- **`quality`** — what each grade means, corpus-wide distribution (733K `suggested`,
  643K `pattern`), what `discovered_by: tsk` means, and an explicit "these are leads,
  verify before citing" statement. **This one matters most** — it is the difference
  between a careful consumer and one who launders machine-proposed links as scholarship.
- **`layers`** — the 11 layers, what generated each, which are textual vs computed.
- **`limits`** — what the corpus does *not* have. Currently at minimum: **no Septuagint**
  (the OT is Hebrew-only), so a client cannot check whether an NT Greek word matches
  the LXX of the verse it echoes. A client that doesn't know this will silently conclude
  "no link found."
- **`research`** — the loop that actually works: `guide` → collect targets → batch-fetch
  target texts → `interlinear` to verify any language claim. Worth stating because it is
  non-obvious and it is what the API is *for*.

### 3. Make errors teach (highest value-per-line-of-code)

Today:

```json
{"detail": "Verse not found: Genesis.1.1"}
```

Proposed:

```json
{"detail": "Verse not found: Genesis.1.1",
 "hint": "Verse refs are dotted book IDs — try 'gen.1.1'.",
 "see": "/api/v1/orient/refs"}
```

The error already knows exactly what the caller got wrong. A caller who mis-forms a
reference is, by definition, a caller who has not read the docs — so the error is the
only place the instruction is guaranteed to be seen. **If only one item from this
proposal ships, make it this one.**

### 4. Make orient discoverable

An orient endpoint nobody finds is a file nobody reads. Three cheap hooks:

- `GET /` and `/docs` mention it in one line.
- Add it to the OpenAPI description field, so schema-reading clients see it.
- Return `"see": "/api/v1/orient"` in the SPA-fallback body for unknown `/api/*` paths
  — which would also fix the 200-with-HTML trap for any path under `/api/`.

## Why not just improve the OpenAPI doc?

Because OpenAPI carries *shape*, and every item above is *semantics or convention*:

| Knowledge | Fits OpenAPI? |
|---|---|
| `/api/v1/verses/{ref}` takes a string | yes, already there |
| That string must be `gen.1.1`, not `Genesis 1:1` | no — it is a `string` either way |
| `quality` is an enum | yes |
| `suggested` means "an algorithm proposed this; verify it" | no |
| A 200 response may be SPA HTML | no — it violates the schema silently |
| The corpus has no LXX | no — absence is not in a schema |

`description` fields can carry a little of this, but nobody reads 170-odd path descriptions,
and a client cannot ask "what do I most need to know before I start?"

## Scope and cost

Deliberately small. Items 1, 3 and 4 are a single route module, a helper on the 404 path,
and three one-line mentions. Item 2 is markdown files served by an existing route pattern
— the content is the work, not the code, and most of it already exists scattered across
`README.md`, `chat/instructions`, and the maintainer's head.

**Suggested order if this gets picked up at all:** (3) errors that teach → (1) orient →
(4) discoverability → (2) topics as they get written.

## The general principle

*Instructions on how to use a system should ship inside the system, be fetchable by the
consumer at runtime, and be indexed by when-to-use rather than dumped whole.*

A system whose operating knowledge lives only in a README is one where every new
consumer relearns the same lessons by making the same mistakes. Everything in the
`conventions` block above was learned that way over about an hour, and every item is
one sentence long. Those sentences are worth more than any amount of schema.

---

### What prompted this

Built a full lesson against the live API on 2026-07-25 — passage guides for ~10 verses,
batch text fetches for ~30 cross-references, and interlinear verification of every
language claim before it went in front of a class. The API handled all of it, unauthenticated,
without a hiccup. The engine is genuinely good and the connection data earned its place
in the finished work.

Field notes and the specific bugs found are in the companion doc,
[`report-api-field-notes.md`](report-api-field-notes.md).

---

## What changed between the email and this doc (2026-07-27 -> 2026-08-23)

Four weeks of your commits later, re-checked today:

- **The tool surface grew 70 -> 81**, and the CFM + General Conference corpora
  landed. That is more capability for a new client to discover unaided, not
  less — `scripture_cfm_lesson` with no arguments returning the current week is
  lovely, and completely invisible from `/openapi.json`.
- **`/api/v1/chat/instructions` grew from ~14K to ~48K characters.** This
  strengthens the argument rather than weakening it: 48K is far too large for an
  API client to swallow at session start, which is precisely the case for an
  index-shaped `orient` whose depth is a second call.
- **All the defects in the companion doc are still live**, including the
  `scripture_gematria` wrapper and the 200-with-SPA-HTML behaviour.
- **One new item for the `limits` topic:** Cloudflare fronts the site and
  rejects the default `Python-urllib/3.x` User-Agent with HTTP 403
  `error code: 1010`, while `curl` passes. A Python client therefore sees a total
  outage where the shell sees perfect health. Not your code — but it is exactly
  the class of thing an `orient`/`limits` topic exists to tell a client before it
  wastes an hour.
