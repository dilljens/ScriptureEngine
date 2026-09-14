---
status: implemented
kind: report
area: api
author: external
created: 2026-08-30
resolved: 2026-09-14
resolution: Per-psalm offsets ship on verse payloads (Ps 51 +2 admitted; unmeasured psalms say so), Jonah -1/+1 included, same block on interlinear responses, ?layer= now filters (unknown layers 400 with the valid list), orient documents route coverage + text_resources has no JST rows. Open questions back to you: DB download URL (your call) and filing location (inbox works — keeping it). Missing-edge generation still open (data pipeline). Also closed the stale field-notes/orient-doc statuses flagged in Housekeeping where applicable.
---

# Follow-up — the 2026-08-25 fixes verified, and the versification one is wider than Psalms

**From:** James Jensen. Companion to
[`report-api-field-notes.md`](report-api-field-notes.md) and
[`proposal-api-orient.md`](proposal-api-orient.md). Five of the six items in
those docs are closed; the Psalms one needs another pass.

All six items in the July report are fixed on production. Verified live
2026-08-30 against `scriptureengine.org`, each with the repro command from the
original report:

| Reported | Now |
|---|---|
| `scripture_gematria` wrapper: `transliterate() got an unexpected keyword argument 'strip_accents'` | `GET /api/v1/tools/scripture_gematria?word=אור` returns 200 with the full gematria block. |
| Unknown `/api/*` paths returned HTTP 200 with SPA HTML | Real JSON 404: `{"ok":false,"error":"Unknown API endpoint: …","see":"/api/v1/orient"}`. |
| `/metrics` advertised but unserved | 200 `text/plain`. |
| Errors did not teach | `/api/v1/verses/matt.16.999` returns 404 with `hint` naming the fix and `see` pointing at `orient`. The `Genesis 1:1` case is better still: it names the dotted form *and* the books route. |
| No orientation endpoint | `GET /api/v1/orient` plus the five depth topics. |
| Psalms KJV-vs-MT | Not closed. The stated +1 is wrong for Psalm 51 (+2), the payloads mix KJV-indexed English with MT-indexed Hebrew, and the problem is not confined to Psalms: Jonah 1 measures **-1**. Three sections below. |

Two notes on the fixes themselves, since you cannot see your own API from
outside:

- **The `orient/limits` topic is the highest-value part.** It answers the
  question a caller cannot answer for themselves: is this thing missing, or am
  I asking wrong? Putting the LXX gap there converts the worst wrong conclusion
  (*"the corpus shows no Greek link, so there is no allusion"*) into a known
  boundary. Carrying the Cloudflare User-Agent behavior there was the right
  call too. It is not your bug, but `orient` is the only place a client will
  read it before it costs them an hour.
- **Scoping the SPA catch-all to `/api/*` is correct** and I do not want it
  widened. A base-URL typo landing outside `/api/` still returns HTML at 200,
  but that is the SPA doing its job, and a client that checks the content type
  is covered.

## Wrong — a verse payload can hold two different verses, and the stated rule is not always +1

Found 2026-08-30 while working the Come Follow Me block for this week
(`cfm.2026.35`, Psalms 49–51; 61–66; 69–72; 77–78; 85–86), which is mostly
superscripted psalms. Two problems, both in the fix rather than around it.

**1. `text_english` and `text_hebrew` in one payload are different verses.**

```bash
curl -s .../api/v1/verses/psa.51.1 | jq '{en: .data.text_english, he: .data.text_hebrew}'
# en: "Have mercy upon me, O God, according to thy lovingkindness…"   <- KJV 51:1
# he: "לַ/מְנַצֵּ֗חַ מִזְמ֥וֹר לְ/דָוִֽד"                                    <- MT 51:1, the superscription
```

The English is KJV-indexed and the Hebrew is MT-indexed, and the payload uses
one verse number for both. On `psa.69.2` the same thing happens one verse apart:
`text_english` is *"I sink in deep mire"* while `text_hebrew` is the Hebrew of
KJV 69:1, *"Save me, O God."* The `versification` block you added is inside this
same payload, which makes it a note describing the mismatch rather than a fix
for it. A caller reading `text_hebrew` next to `text_english` gets a word study
built on the wrong verse, with the two halves of the evidence disagreeing and
nothing marking which one is displaced.

**2. The offset is not always 1.** The `versification` note and `orient/refs`
both state *interlinear = KJV + 1*. Psalm 51 carries a two-clause superscription
that the MT splits across two verses, so it runs **KJV + 2**:

```
MT 51:1  לַמְנַצֵּחַ מִזְמוֹר לְדָוִד                       "To the chief Musician, A Psalm of David"
MT 51:2  בְּבוֹא אֵלָיו נָתָן הַנָּבִיא כַּאֲשֶׁר בָּא אֶל בַּת שָׁבַע   "when Nathan the prophet came unto him…"
MT 51:3  חָנֵּנִי אֱלֹהִים כְּחַסְדֶּךָ                        = KJV 51:1
```

Verse counts across this week's seventeen psalms, taken by walking both schemes
to their last verse:

| Offset | Psalms |
|---|---|
| KJV + 2 | 51 |
| KJV + 1 | 49, 61, 62, 63, 64, 65, 69, 70, 77, 85 |
| aligned | 50, 66, 71, 72, 78, 86 |

Six of seventeen are aligned even though five of those six carry a title, because
the MT sometimes folds the superscription into verse 1 rather than numbering it
separately (Psalm 86, `תְּפִלָּה לְדָוִד`, is the clear case). So "does this psalm have a
superscription" does not predict the offset, and neither does a fixed +1. The
count difference per psalm is the only thing that does.

A stated rule that is wrong for one psalm in seventeen is worse than no rule: it
is precisely reliable enough to be trusted. Psalm 51 is not an obscure case
either — it is the repentance psalm, and it is one of the four teaching blocks
in this week's curriculum.

**What would close it.** Publishing the per-psalm delta is the honest fix, since
the corpus can compute it: `versification.offset` on the payload, resolved for
that psalm, replacing the general rule with the actual number. Failing that,
correcting the note to say the offset is 1 **or 2** and must be checked per
psalm is a one-line change that stops the confident wrong answer.

The measurement is cheap and you already have the data. We take the difference
in verse count between the two schemes, per psalm, by bisecting each to its last
verse. Ours for this week's block, if it saves you the run:

```json
{"psa.49":1, "psa.50":0, "psa.51":2, "psa.61":1, "psa.62":1, "psa.63":1,
 "psa.64":1, "psa.65":1, "psa.66":0, "psa.69":1, "psa.70":1, "psa.71":0,
 "psa.72":0, "psa.77":1, "psa.78":0, "psa.85":1, "psa.86":0,
 "jonah.1":-1, "jonah.2":1}
```

Two notes from doing it, in case they are useful. A superscription-marker test
against the Hebrew of verse 1 does **not** work: the corpus returns fully
pointed text, so `"מזמור" in "מִזְמ֥וֹר"` is false, and stripping U+0591–U+05C7
first still gives the wrong answer because psalms 50, 66, 78 and 86 carry titles
without shifting. Verse counts are the only thing that decides it.

**3. It is not a Psalms problem.** Found the same day, working Jonah as a
cross-reference. The MT numbers KJV Jonah 1:17 as Jonah 2:1, so:

```
Jonah 1:  KJV 17 verses, MT 16   ->  offset -1
Jonah 2:  KJV 10 verses, MT 11   ->  offset +1
```

`interlinear(jonah, 2, 5)` returns the Hebrew of **KJV Jonah 2:4** with no
signal at all, because the `versification` block and `orient/refs` both scope
this to Psalms. The offset is also **negative** in Jonah 1, which no
superscription rule can produce.

Special-casing Psalms leaves
every other divergent book silently wrong, and the divergences are well known:
Joel, Malachi, Numbers, the Samuels and others move chapter boundaries the same
way. A caller who reads `orient/refs`, sees a Psalms caveat, and concludes the
rest of the corpus is aligned has been told something false by omission.

We now measure the delta per book and chapter rather than per psalm, for any
book, because a list of special cases is exactly what goes quietly wrong at the
edges.

## Also open — `scripture_interlinear` omits the `versification` block

Verse payloads carry it. The interlinear tool payload, which is the side that
actually uses MT numbering, does not:

```bash
curl -s .../api/v1/verses/psa.69.2 | jq .data.versification
# {"english_scheme":"kjv","interlinear_scheme":"mt",
#  "note":"For superscripted psalms the interlinear index is KJV + 1 …",
#  "see":"/api/v1/orient/refs"}

curl -s -X POST .../api/v1/tools/scripture_interlinear \
  -H 'Content-Type: application/json' -d '{"book":"psa","chapter":69,"verse":2}' \
  | jq '.data | keys'
# ["reference","verse_id","word_count","words"]
```

The disclosure is on the endpoint that is already correct by the caller's
assumption, and absent from the one that will silently mislead them. A word
study runs through the interlinear: that is where the note is needed, and where
the client is holding the wrong verse number without any signal. Same block,
same `see`, on `psa.*` interlinear responses would close it.

Our client still emits its own per-call warning on `psa` interlinear lookups.
That stops being necessary the day the payload carries the note.

## One more, found later the same day: nothing connects the Psalms to the Restoration corpus

The corpus carries it — `2ne.2.25`, `alma.36.3`, `dc88.88.67` and `moses.1.39`
all resolve and return text. The **connection graph** does not reach it from the
Psalms. Eight seed verses across Psalms 49–86, through `/verses/{ref}/guide`,
returned zero connections into the Book of Mormon, the Doctrine and Covenants or
the Pearl of Great Price. Not few. Zero.

Checked the other way before reporting it, since a gap in a result is usually a
gap in the query: the books resolve individually, so this is the graph and not
the corpus or my filter.

Here is the sharpest case, because your own full-text search finds what the
graph does not. `GET /api/v1/search?q=broken heart and a contrite spirit` returns
fourteen verses, **twelve of them in Restoration scripture** — D&C 59:8,
3 Nephi 9:20, Mormon 2:14, Moroni 6:2, 2 Nephi 2:7 and more. Every one is
quoting Psalm 51:17. The graph carries no edge between any of them and that
psalm.

So the data is in the corpus and reachable by one endpoint and not the other.
That phrase is plausibly the most reused Old Testament line in the Book of
Mormon, and it is invisible to the subsystem built to find reuse. For a tool
whose audience is Latter-day Saints, that is the connection most users would
expect to exist. Not a defect in anything
that is built; a gap in what has been built, and possibly just a generator that
has not been run over those works yet.

Related, and much smaller: `text_jst` is present on Psalms and differs from
`text_english` only by punctuation on the three I compared (49:15, 51:17, 86:5) —
a colon against a comma. If that is all the JST field ever carries for a book,
saying so in `orient` would stop a client diffing the two fields and reporting
phantom variants.

## Smaller: the documented `?layer=` filter has no effect

`orient/layers` ends with *"Filter any connection listing with `?layer=`."* On
`/api/v1/verses/{ref}/guide` it does nothing: `?layer=interpretive`,
`?layer=symbolic` and `?layer=textual` all return the same 16 connections with
the same buckets.

Harmless on its own, since the unfiltered guide already returns every bucket. It
is the same shape as the versification rule though: documentation describing
behavior the code does not have, which costs a caller the time it takes to
discover the doc is wrong rather than their query.

While there: `/chapter/{book}/{chapter}/connections` and the per-verse guide
return almost disjoint sets for the same chapter — for Psalm 110, three targets
in common out of seventy-nine. Reading the layer table, that looks intended: the
chapter route serving `structural` and `interpretive` at passage scale, the guide
serving `intertextual` at verse scale. If it is intended, one line in `orient`
saying so would stop the next caller assuming the cheap route is a faster version
of the expensive one. I nearly swapped one for the other.

## Two questions

- **Is the 1.4 GB database downloadable without running the full `setup.sh`?**
  We drive the hosted instance for everything, which puts load on your host for
  work that is read-only and batchy. A plain URL for the DB file would let us
  take that off you.
- **Do you want defects filed here, or somewhere else?** This inbox has worked
  well from our side. Two docs, two days, everything shipped. Happy to keep
  using it, and happy to switch if you would rather have issues.

## Housekeeping

`report-api-field-notes.md` is still `status: open` and `proposal-api-orient.md`
is still `status: proposal`, though both are done. Yours to close, and we have
no write access to do it: our remote for this repo is read-only, so these docs
arrive as a branch or an attachment rather than a push.
