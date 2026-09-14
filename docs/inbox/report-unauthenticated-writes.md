---
status: implemented
kind: report
area: api
author: external
created: 2026-08-30
resolved: 2026-09-14
resolution: /debug/log and /debug/logs require a valid session token (ErrorBoundary attaches it; fields truncated server-side); /forum/posts resolves the author server-side and ignores the body author; conversations keeps its documented legacy anonymous path, now declared in orient conventions alongside the write-auth rules.
---

# The public API accepts unauthenticated writes

**From:** James Jensen. Filed separately from
[`report-api-followup-2026-08-30.md`](report-api-followup-2026-08-30.md)
because it is the one item here you may want to act on before reading the rest.

**Read from source and from the live OpenAPI document. Not exercised.** We have
never sent a write to your production instance and will not without your say-so.
Every claim below is a code reading or a spec reading, so treat the severity as
unconfirmed until you test it yourself. The reason to look is that the reading is
simple and the routes are live.

## What the spec says

`GET /openapi.json` on production, 2026-08-30: **52 write operations
(POST/PUT/PATCH/DELETE), none of which declare a security scheme.**
`components.securitySchemes` is empty, which the July field notes recorded as a
reasonable property of a read-only public API. It is a different property now
that the same surface accepts writes.

`web/server.py` adds `CORSMiddleware` and `GZipMiddleware` and nothing else. No
global dependency, no auth middleware, no rate limiter. So per-route handling is
the whole story.

## Three routes where the reading is unambiguous

**`POST /api/v1/debug/log`** (`web/routes/admin.py:42`) takes a bare `dict`,
creates `client_logs` if absent, and inserts `message`, `stack`, `url` and
`user_agent` from the body. No identity, no size limit, no rate limit. Anyone
who can reach the host can append rows to your database for as long as they care
to. On a 1.4 GB SQLite file with a live FTS index, unbounded third-party inserts
are a disk and a lock problem before they are anything else.

**`POST /api/v1/forum/posts`** (`web/routes/forum.py:57`) takes `author` from the
request body and writes it straight in, then bumps `post_count`. The author of a
post is whatever the caller typed. Anyone can post as anyone, including as you.

**`POST /api/v1/conversations`** (`web/routes/conversations.py:130`) resolves the
owner properly when an identity is supplied, and falls back to
`body.created_by or "anonymous"` when none is. The comment marks this as the
legacy anonymous path, so it is deliberate. Worth confirming it is still
deliberate now that the instance is public and indexed.

## What we are not claiming

We have not tested whether Cloudflare in front of you rate-limits or blocks any
of this. It may well absorb the volume case. It cannot fix the forged-`author`
case, which is an application-layer decision.

## The cheap end of the fix

You know the architecture; this is only what an outside reader would reach for.

1. **`debug/log`**: require the same session token the rest of the user surface
   uses, or drop the route and let the frontend log to the console. It exists for
   your own frontend, and your own frontend can authenticate.
2. **`forum/posts`**: ignore `author` from the body and resolve it server-side
   from the session, the way `conversations.py` already does with `_owner_id`.
   The pattern is in the codebase; the forum route predates it.
3. **Declare what is public.** If some writes are meant to be open, saying so in
   the OpenAPI security block turns "no scheme declared" from ambiguous into a
   decision. That also makes `orient` able to tell a client which half of the API
   it may write to, which is the question a client actually has.

None of this is urgent in the sense of "someone is doing it now." We looked
because the July notes left the question open (*"write endpoints appear
unauthenticated, deliberate?"*), and the answer from the source is that at least
`debug/log` and `forum/posts` are open by oversight rather than by choice.
