---
status: open
kind: report
area: api
author: external
created: 2026-07-27
updated: 2026-08-23
---

# Field notes — driving the ScriptureEngine API from outside

**From:** James Jensen.
**Basis:** built a complete lesson against the live API — ~10 passage guides, ~30
cross-reference text fetches, and word-by-word verification of every language claim.
All findings re-verified against `scriptureengine.org` on **2026-07-27 and again
on 2026-08-23** — every defect below is still live on the second check.

Companion to [`proposal-api-orient.md`](proposal-api-orient.md), which proposes the structural fix. This doc is
the raw material: what actually happened, and the specific defects.

---

## First, the part that worked

The API carried a real piece of work end to end. `/verses/{ref}/guide` → collect targets
→ batch-fetch texts → `scripture_interlinear` to verify is a genuinely excellent research
loop, and it is fast enough to run interactively. Unauthenticated reads meant zero setup
friction. Several of the strongest findings in the finished lesson came from connections
graded merely `suggested` — the low grades are not noise, they are leads.

Three examples of things the engine surfaced that a human would plausibly have missed,
all of which survived verification and went in front of a class:

- `matt.16.23` → `matt.4.10`, which is what makes "Get thee behind me, Satan" legible:
  Peter is unknowingly restating the wilderness temptation.
- `luke.22.31` → `zech.3.1`, Joshua the high priest with Satan at his right hand — the
  whole shape of Peter's night, already present in Zechariah.
- `matt.14.30` → `psa.69.2`/`psa.69.14`, the "sinking" psalm the NT applies to Christ.

That is the system doing exactly what it exists to do.

---

## Defects

### 1. `scripture_gematria` tool wrapper is broken — **still live 2026-08-23**

```bash
curl -s "https://scriptureengine.org/api/v1/tools/scripture_gematria?word=אור"
# {"detail":"transliterate() got an unexpected keyword argument 'strip_accents'"}

curl -s -G "https://scriptureengine.org/api/v1/gematria" --data-urlencode "word=אור"
# {"ok":true,"data":{"word":"אור","gematria":{"standard":207,"ordinal":27,...}}}
```

The direct route is fine; only the tool wrapper fails. Looks like a `transliterate()`
signature drift where the wrapper passes `strip_accents=` and the current function
doesn't accept it. **Impact is larger than one tool** — anything driving the API through
the generic `/tools/{name}` dispatcher (which is the natural integration path, since it
is self-describing) hits this, while anything using the REST routes does not. Worth a
smoke test that calls every registered tool once with its schema's example values.

### 2. Unknown paths return HTTP 200 with SPA HTML — **still live 2026-08-23**

```bash
curl -s -o /dev/null -w '%{http_code} %{content_type} %{size_download}\n' \
  https://scriptureengine.org/api/v1/no-such-endpoint
# 200 text/html; charset=utf-8 1974
```

The SPA catch-all sits in front of unmatched `/api/*` paths. Consequences:

- Status-code-based probing silently lies. Every wrong guess looks like a success.
- A client that JSON-parses the response gets a confusing parse error rather than a 404.
- It masks genuinely missing endpoints — see (3).

Suggested fix: exclude the `/api/` prefix from the SPA fallback and return a real JSON
404. That single change would also give a natural home for the "hint" mechanism proposed
in the companion doc.

### 3. `/metrics` is advertised but not served — **still live**

`/metrics` appears in `/openapi.json` as "Prometheus Metrics," but requesting it returns
the same 1974-byte SPA HTML. Either the route isn't mounted in the deployed config or the
proxy shadows it. Currently a monitoring client would scrape HTML forever without error.

### 4. Psalms versification differs between endpoints — **confirmed 2026-07-27**

```bash
# English text endpoint — KJV numbering
/api/v1/verses/psa.69.14        → "Deliver me out of the mire, and let me not sink..."

# Interlinear tool — Hebrew (MT) numbering, superscription counted as verse 1
/api/v1/tools/scripture_interlinear?book=psa&chapter=69&verse=15
                                → haṣṣîlēnî miṭṭîṭ wəʾal ʾeṭbāʿāh...   (same verse)
```

For any psalm carrying a superscription the interlinear index is KJV + 1. This is not a
bug so much as two correct-but-different conventions colliding in one API, and it is
*silent* — you get a real verse either way, just the wrong one. It will quietly corrupt
any automated word study over the Psalms.

Options: normalize both to one scheme; or return both numbers in every Psalms response
(`"kjv_verse": 14, "mt_verse": 15`); or, cheapest, document it loudly. Returning both
seems best — it is honest about the ambiguity instead of picking a winner.

### 5. No Septuagint in the corpus — a limit worth publishing

The OT is Hebrew-only. That means a consumer cannot check whether an NT Greek word
matches the LXX wording of the OT verse it echoes — which is the strongest available
evidence for an allusion. Concretely: Matthew 14:30 has Peter *καταποντίζεσθαι*, and the
question "does the Greek Psalter use that root in Psalm 69?" is unanswerable here.

Not a defect — corpora have boundaries. But it belongs in a published `limits` topic,
because the failure mode is a client concluding "no connection exists" when the real
answer is "this corpus cannot see that kind of connection."

### 6. `go_srs: false` in health, with no stated consequence

`/api/v1/health` has reported `"go_srs": false` on every check across three days
(uptime 22h at last look, so this survives restarts). Health says `"status": "ok"`
regardless. A consumer cannot tell whether that subsystem being down means "memorize
endpoints will 500," "reviews fall back to a Python scheduler," or "nobody cares, this
flag is vestigial." Whatever the answer, `health` should say which capabilities are
degraded rather than only which flags are false.

---

## Conventions that cost time to discover

None of these are defects; all of them are things a newcomer must learn by failing. They
are the argument for the companion proposal.

| Learned | Cost |
|---|---|
| Verse refs are dotted book IDs (`gen.1.1`), not `Genesis 1:1` | first lookup 404s with no hint |
| D&C double-numbers: `dc88.88.67`, book id then chapter | two failed guesses |
| `{ok:true,data:…}` vs FastAPI `{detail:…}` — two error shapes | client needs both paths |
| `quality` grades *confidence*, not truth | risk of laundering machine guesses as scholarship |
| `discovered_by: tsk` = Treasury of Scripture Knowledge | changes how much to trust a link |
| The `/tools/{name}` dispatcher mirrors the REST routes | wasn't obvious which to build against |
| `/verses/{ref}/guide` is the workhorse | found it late; it should be the headline |

The single most valuable sentence anywhere in the system would be, in the `quality`
documentation: *"`suggested` and `pattern` are algorithmic proposals — verify against the
text before citing."* Corpus-wide that is 1.38M of the 1.82M connections. A careless
consumer will present them as scholarship, and the engine will get blamed for it.

---

## Suggested priority

1. **Errors that teach** (`hint` + `see` on 404s) — smallest change, largest effect
2. **Real JSON 404s under `/api/`** — fixes (2) and unblocks (1)'s delivery mechanism
3. **`scripture_gematria` wrapper** + an all-tools smoke test
4. **Psalms dual numbering** in responses
5. **`/api/v1/orient`** per the companion proposal
6. `/metrics`, and a `limits` topic covering the LXX gap

---

*Offered as a user of the thing, not a critic of it. The engine did work here that would
have taken days by hand, and the lesson it produced is better for it.*


---

## Re-verification, 2026-08-23

All six defects above are still live. Two are worth a note rather than a bare
tick:

- **Psalms versification (4)** — confirmed by word content, not just numbering.
  `scripture_interlinear?book=psa&chapter=69&verse=15` returns the Hebrew for
  *"Deliver me out of the mire... let me not sink... them that hate me"*, which
  is **KJV 69:14**; `verse=14` returns *"my prayer... in an acceptable time"*,
  KJV 69:13. The offset is exactly as reported.
- **No Septuagint (5)** — still true, but the shape has changed in a way that
  looks like progress: `/api/v1/verses/{ref}` now returns `text_greek` and
  `text_greek_source` fields on OT verses, and they are `null` with
  `has_greek: false`. The schema now anticipates an LXX that isn't loaded. That
  is *more* confusing for a client, not less — a field that exists and is empty
  reads as "no connection here" rather than "this corpus cannot see that."

Also worth recording: the corpus has grown from 9 works to **19** (Josephus,
Philo, Nag Hammadi, Ugaritic texts, Targums, Mishnah, Sibylline Oracles and
more), and connections from 1.82M to 1.91M.

---

## Added 2026-08-23 — Cloudflare blocks the default Python User-Agent

Not a defect in your application, but it presents as one and cost an hour:

```bash
curl -s .../api/v1/health                       # 200, healthy JSON
python3 -c "import urllib.request as u; u.urlopen('https://scriptureengine.org/api/v1/health')"
# urllib.error.HTTPError: HTTP Error 403: Forbidden   -> body says "error code: 1010"
```

Cloudflare's browser-integrity check rejects `Python-urllib/3.x`. Any client
setting a real `User-Agent` passes. The failure mode is nasty because it is
total and uniform — every endpoint 403s, so it reads as "the service is down"
or "I have been rate-limited / banned", not "my UA is wrong". Two cheap fixes,
either one sufficient: relax the check for `/api/*`, or say so in the docs (and
in `orient`, if that ships).
