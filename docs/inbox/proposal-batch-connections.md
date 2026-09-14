---
status: implemented
kind: proposal
area: api
author: external
created: 2026-08-30
resolved: 2026-09-14
resolution: GET /api/v1/chapter/{ref}/guides returns per-verse guides for a chapter (with ?layer= passthrough). Batch form chosen: chapter scope fits existing routes.
---

# Batch the connections the way you already batch verses

**From:** James Jensen. A future request, not a defect — nothing is broken here.

`scripture_batch_lookup` takes up to 50 refs and returns them in one call.
Measured just now: **50 verses in 1.0 s batched against 19.6 s one at a time**,
a factor of nineteen, and one request against your host instead of fifty. The
shape is right and it already exists.

There is no equivalent for connections, and connections are where the volume is.

## What this costs today

A week of Come Follow Me is a block of psalms. To ask *"which verses in this
block does the New Testament use"* — the question that produced most of what we
have found worth writing — there is one call per verse:

| Week | Verses in the block | Requests | Wall time |
|---|---|---|---|
| 2026-08-24 | 290 | ~290 | ~15 min |
| 2026-08-31 | 441 | ~441 | ~21 min |

We cache aggressively now, so we pay that once per week rather than per run. It
is not painful for us. It is 441 requests landing on your host for a question
that is one query underneath, and anyone else doing corpus-scale reading pays it
again from scratch.

## The smallest version that would help

A chapter-scoped guide, matching the `/chapter/…` family already in the spec:

```
GET /api/v1/chapter/{ref}/guides
```

returning what `/verses/{ref}/guide` returns, for every verse in the chapter, in
one response. That collapses a 441-request week to **19**.

`/api/v1/chapter/{ref}` already returns every verse of a chapter with its text
and parallelism data, so the fan-out pattern and the route shape both exist. This
is the same move applied to the connection layers.

A batch form taking arbitrary refs — `POST /api/v1/connections/batch` with a list,
capped at 50 like `scripture_batch_lookup` — would serve the same need and suit
callers whose refs are scattered rather than contiguous. Either would do; the
chapter form is probably less work and fits the existing routes better.

## Why it is worth your time and not just ours

- **It is your load.** Every consumer doing distribution analysis is currently
  generating hundreds of requests for one logical query.
- **It makes a class of question practical that currently is not.** Sweeping a
  whole book for where a pattern is dense and where it stops takes hours per
  book today. At 19 requests a chapter it is minutes, and that kind of
  distribution reading is where the non-obvious findings have come from — the
  New Testament uses 29 of Psalm 69's 36 verses and not verse 5, which is the
  one that confesses sin. Nobody arrives at verse 5 by picking seed verses.
- **The cap makes it safe.** Fifty refs or one chapter bounds the response the
  way `scripture_batch_lookup` already does.

No urgency from our side. We have the cache and we can wait.
