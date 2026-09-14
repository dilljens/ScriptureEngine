---
status: implemented
kind: proposal
area: api
author: external
created: 2026-09-06
resolved: 2026-09-14
resolution: lib/api/refs.py normalizes dc121.7 / dc.121.7 / D&C 121:7 (and dc121 chapter form) on verse, chapter, entities, guides, and connection-chapter routes; display strings never repeat the number; orient/refs + conventions document the shape. Genuinely ambiguous dc1.1 reads as verse to verse routes, chapter to chapter routes.
---

# The Doctrine and Covenants cannot be addressed from a human citation

**From:** James Jensen. One small change would remove a special case that every
consumer of this API has to carry.

The Doctrine and Covenants is the only work in the corpus whose **section is a
book**. `/api/v1/books` returns 138 of them, `dc1` through `dc138`, where every
other work is one book with many chapters. The canonical verse id therefore
repeats the number:

```
psa.23.1        Psalms 23:1          book=psa    chapter=23
2ne.31.20       2 Nephi 31:20        book=2ne    chapter=31
dc121.121.7     D&C 121:7            book=dc121  chapter=121   <- repeated
```

Nothing about that is wrong as a data model. The cost is at the boundary.

## The concrete problem

**A citation parser cannot name the book without first parsing the chapter.**
Every other book resolves from its name alone: `"Genesis" -> gen`. The D&C
resolves only from name *and* section: `"D&C", 121 -> dc121`. So a function with
the natural signature `book_id(name)` returns nothing for the entire work, and
the fix is to change the signature everywhere.

We hit this building a lesson that quotes D&C 45, 121 and 132. Our quotation
checker merges your `/api/v1/books` table over its own precisely so a stale local
list cannot cause a silent under-check. It still reported all five D&C
quotations as `no book resolved, skipped` — and **exited clean**, because
skipping is not failing. A checker that checks less than its name promises is
the failure mode we care most about, and this is a shape in the API that
produces it in a caller that was trying to be careful.

The near forms all fail, so there is no lucky guess:

```
dc121.121.7   200
dc121.7       404   the shape written by analogy with gen.1.1
dc.121.7      404   well-formed; there is no book "dc"
dc121.1.7     404   chapter slot must repeat the section
```

## Two display strings are also wrong, and only for this work

**1. `reference` prints the number twice**, for all 138 books:

```
GET /api/v1/verses/dc121.121.7   ->  "reference": "Doctrine and Covenants 121 121:7"
GET /api/v1/verses/psa.23.1      ->  "reference": "Psalms 23:1"
GET /api/v1/verses/moses.1.39    ->  "reference": "Moses 1:39"
```

Every other work formats correctly. This one is presumably `f"{book_title}
{chapter}:{verse}"` where the title already ends in the chapter number.

**2. Search returns a truncated book name.** `/api/v1/search` gives `"book":
"Doctrine"` for every D&C hit — cut at the first space:

```
dc132.132.45   book="Doctrine"
dc124.124.34   book="Doctrine"
dc84.84.26     book="Doctrine"
```

A consumer grouping results by `book` gets one bucket called "Doctrine" holding
138 sections, and cannot tell them apart without re-parsing the verse id.

## What we would ask for, cheapest first

1. **Accept the short forms as aliases** on any route taking a ref:
   `dc121.7`, `dc.121.7`, and ideally `D&C 121:7`, all resolving to
   `dc121.121.7`. This is the one that removes the special case rather than
   documenting it, and it is not a breaking change: the canonical form keeps
   working and nothing that exists today starts to mean something else.
2. **Fix the two display strings.** `reference` should read
   `"Doctrine and Covenants 121:7"`; search's `book` should carry the full title.
3. **Document the shape in `/api/v1/orient`**, in `conventions`, beside the
   Psalms versification note that already lives there. Today the only way to
   learn it is to fetch `/books` and notice 138 entries where you expected one.

We have implemented (1) locally, in our own client, because we needed it this
week. It is roughly twenty lines and we are happy to hand over the normalizer
and its tests if that is useful. It belongs in the API, though: every consumer
that does not implement it gets a 404 that reads like a bad verse number.

## The general point, offered rather than argued

**Reference conventions vary per work, and each variation costs a caller a day
to discover.** The Psalms KJV-versus-MT offset was the first one and took us
about that. This is the second. A single table in `orient` — per work, the ref
shape, and anything a caller must know before building an id — would have
prevented both, and it is documentation rather than engineering.
