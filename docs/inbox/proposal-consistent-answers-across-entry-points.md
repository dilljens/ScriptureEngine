---
status: implemented
kind: proposal
area: api
author: external
created: 2026-08-30
resolved: 2026-09-14
resolution: orient/layers documents route coverage; /tools/{name} validates required params (422 naming them); chapter + book-summary errors use the teaching envelope; orient/limits documents the Restoration graph gap. Item 4 (generating the missing edges) NOT done — data pipeline, still open.
---

# The same question through different doors gives different answers

**From:** James Jensen. A design request rather than a bug list, though several
of the items below are individually reportable.

Driving this API hard for two weeks, the single recurring cost has not been any
one defect. It is that **asking the same question by a different route returns a
materially different answer, and nothing says which route is authoritative.**
Each instance is small. Together they mean a caller cannot trust a result
without cross-checking it against another endpoint, which defeats the point of
having the endpoint.

Five instances, all verified.

## 1. Two connection routes, almost disjoint

`/api/v1/verses/{ref}/guide` across Psalm 110's seven verses returns 79 targets.
`/api/v1/chapter/psa/110/connections` returns 68. **They share three.**

Reading the layer table in `orient/layers`, this looks intended: the chapter
route serves `structural` and `interpretive` at passage scale, the guide serves
`intertextual` at verse scale. If so, the data is right and only the naming is
misleading — two routes called "connections" that answer different questions.

We nearly substituted one for the other on the assumption that the chapter route
was a cheaper version of the same query. One line in `orient` saying what each
route covers would have prevented it.

## 2. Full-text search reaches what the connection graph cannot

`GET /api/v1/search?q=broken heart and a contrite spirit` returns fourteen
verses, twelve of them in Restoration scripture — D&C 59:8, 3 Nephi 9:20,
Mormon 2:14, Moroni 6:2, 2 Nephi 2:7. Every one is quoting Psalm 51:17.

The connection graph has **no edge** between Psalm 51:17 and any of them. We
checked eight seed verses across Psalms 49–86 and found zero connections into the
Book of Mormon, the D&C or the Pearl of Great Price.

So the corpus contains the relationship, one subsystem can find it, and the
subsystem built to find relationships cannot. For a tool whose audience is
Latter-day Saints this is the connection they would most expect to exist.

## 3. The graph finds the family and misses the head

For `psa.86.15` the guide surfaces Numbers 14:18, Joel 2:13, Nehemiah 9:17,
Psalms 103:8 and 145:8 — the whole family of the "merciful and gracious, slow to
anger" formula — and **not Exodus 34:6, where the formula is spoken.**

That is a different failure from the one above. Here the graph reaches the right
neighborhood and omits its center, so a caller who trusts it gets a coherent and
incomplete picture, which is harder to notice than an empty one.

## 4. The tool dispatcher does not enforce the schema it publishes

`GET /api/v1/tools` advertises `scripture_batch_lookup` as requiring `verses`.
Calling it with a wrong or missing parameter returns:

```
HTTP 500  {"detail":"lookup_verses() missing 1 required positional argument: 'verses'"}
```

An internal signature error at 500, where the published schema has everything
needed to answer 422 with the parameter's name. This is the same shape as the
`scripture_gematria` wrapper from the July report: the generic `/tools/{name}`
path and the library behind it disagreeing, with the caller getting the
traceback.

Worth saying plainly: **the July fix was excellent** and the teaching 404s are
the best thing in the API. This is that same idea not yet reaching the tool
dispatcher, which is the entry point most machine callers use.

## 5. Three routes, three error envelopes

Added 2026-09-06. The teaching 404 you shipped in July is the best thing in this
API, and it is on one route out of three:

| Route | Error shape |
|---|---|
| `/api/v1/verses/{ref}` | `{"detail": "Verse not found: …", "hint": "…", "see": "/api/v1/orient"}` |
| `/api/v1/chapter/{ref}` | `{"detail": "Chapter not found: jsh.1"}` |
| `/api/v1/book/{b}/connection-summary` | `{"error": "Book not found: aoff"}` |

Three shapes for the same class of answer, and the third uses a different key
entirely. A caller that learned to read `hint` and `see` from the verses route
gets nothing from the other two, and a caller that keys on `detail` breaks on
the third. Our client had to grow a branch per route to report an error usefully.

This is the cheapest item in this document to fix and it makes the July work pay
off everywhere instead of on one path.

## What would resolve it

Not a rewrite. In rough order of value per hour:

1. **Say what each route covers**, in `orient`. Which layers each connection
   endpoint serves, and that search and the graph have different reach. A caller
   who knows the boundary can work inside it; a caller who does not will assume
   the boundaries are the same and be wrong quietly.
2. **Validate tool calls against the published schema** before dispatch, and
   answer 422 with the missing parameter named — the teaching-error treatment,
   applied to `/tools/{name}`.
3. **Say what the graph does not cover**, in `orient/limits`, alongside the LXX
   entry that is already there. If Restoration scripture has no inbound edges
   from the Old Testament, that sentence saves every LDS-facing consumer the
   afternoon we spent concluding it ourselves.
4. **Generate the missing edges** where it is cheap. Item 2 above is a hundred or
   so quotations that full-text search can already locate, so the input exists.

Items 1 and 3 are documentation and would remove most of the cost. Item 4 is real
work and can wait; knowing the gap is there is most of the value.
