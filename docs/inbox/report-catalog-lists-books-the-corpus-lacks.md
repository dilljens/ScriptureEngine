---
status: implemented
kind: report
area: api
author: external
created: 2026-09-06
resolved: 2026-09-14
resolution: /api/v1/books now carries verses + available per book (a listed book with zero verses is explicit, never mistaken for a bad ref); orient/limits lists the JSM/AoF gaps. JSH is complete in the corpus (75 verses — the report predates scripts/import_jsh.py). JSM/AoF NOT loaded — no verse sources in repo. The pseu/pseudepigrapha duplicate does not reproduce (single Pseudepigrapha work in the catalog).
---

# `/api/v1/books` advertises three books the corpus does not hold

**From:** James Jensen. A defect report, and the reason it is worse than a
missing book rather than equal to one.

Under Pearl of Great Price, `/api/v1/books` lists five books. Two have content.
Three do not:

| id | title | status |
|---|---|---|
| `moses` | Moses | present |
| `abraham` | Abraham | present |
| `jsm` | Joseph Smith—Matthew | **listed, no content** |
| `jsh` | Joseph Smith—History | **listed, no content** |
| `aoff` | Articles of Faith | **listed, no content** |

## Verified four ways, 2026-09-06

Nothing resolves for the three, by any route we could find:

```
GET /api/v1/verses/jsh.1.17            404  Verse not found
GET /api/v1/verses/aoff.1.1            404  Verse not found
GET /api/v1/chapter/jsh.{0,1,2,3}      404  Chapter not found
GET /api/v1/chapter/aoff.{0,1,2,3}     404  Chapter not found
GET /api/v1/book/aoff/connection-summary    {"error":"Book not found: aoff"}
GET /api/v1/book/jsh/connection-summary     {"error":"Book not found: jsh"}
```

And they are not in the search index either: a full-text search for the opening
words of the first Article of Faith returns hits from John, D&C and 1 John, and
nothing from `aoff`. So this is not an id we are spelling wrong; the content is
absent while the catalog says it is there.

## Why this is worse than the books simply being absent

If the catalog did not list them, a consumer asking for Joseph Smith—History
would get "no such book" and know where it stood. Because the catalog does list
them, a careful consumer is led somewhere worse.

Our quotation checker merges your live `/books` table over its own hardcoded
one, deliberately: a hand-maintained book list is how a document that cites
Habakkuk gets silently under-checked, so we treat your catalog as the authority.
That means for a document quoting Joseph Smith—History, the name **resolves**, a
well-formed ref gets built, the fetch 404s, and the checker reports the failure
in the only vocabulary it has: **the document misquoted the verse.**

The document is correct. The corpus is incomplete. The tool says the author is
wrong. That inversion is the reason we are writing this up rather than working
around it.

## What we would ask for

1. **Make the catalog and the content store unable to disagree.** Either drop
   the three entries, or carry an explicit field — `"verses": 0`, or
   `"available": false` — so a consumer can tell "not in this corpus" from
   "you asked wrong". The field is better than dropping them: it says the gap is
   known rather than leaving a reader to wonder whether the book was overlooked.
2. **If loading them is easy, load them.** All three are short, and Articles of
   Faith in particular is cited constantly in LDS-facing material.
3. **List known corpus gaps in `/api/v1/orient/limits`**, beside the LXX entry
   already there. That page is the right home for "what this corpus cannot see"
   and it is where we now look first.

We have added a guard on our side: on a failed lookup the checker probes
`connection-summary` and, if the book is not in the content store, reports a
corpus gap and refuses to count the quotation as checked. That is the honest
report for us to make, but it costs a request per failure and it is a workaround
for something only the catalog can state.

## A smaller one in the same file

`/api/v1/books` returns **two works both titled "Pseudepigrapha"**, with ids
`pseu` and `pseudepigrapha`. Anything keying on the display title merges them or
drops one, silently. Distinct titles would fix it.
