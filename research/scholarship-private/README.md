# Scholarship Shelf — PRIVATE STUDY ONLY

Barker-vein commentary for the purity-ranking plan (`docs/plans/purity-ranking.md`).
First-Temple / Deuteronomist-reform / divine-council / temple-symbolism sources
that test Joseph Smith restoration claims.

## ⛔ DO NOT INGEST — NOT FOR LLM CHAT

- These files are **git-tracked for persistence only**.
- They are **never** read by `scripts/ingest.py` (which reads `data/raw` only),
  never embedded (`scripts/embed_verses.py` embeds DB verses only), and never
  exposed through any MCP tool or HTTP endpoint (all 63 tools are DB-backed:
  verse / search / graph / gematria — see `lib/api/__init__.py`,
  `web/routes/chat.py` function-calling proxy).
- The app's LLM chat therefore **cannot retrieve them**. Cite them by hand
  (short fair-use quotes + official URL), never paste full pages publicly.
- Full PDFs are NOT stored here (binaries bloat git). Re-download from the
  official URLs below; `.txt` files here were converted via
  `pdftotext -layout` 2026-09-08 and are byte-identical to PDF text layer.

## Contents (all open-access, free download, all rights reserved unless noted)

| File | Source paper | Official URL | License |
|---|---|---|---|
| barker-josiah.txt | Barker, *What Did Josiah Reform?* Glimpses ch.17, pp.523-542 | https://scholarsarchive.byu.edu/mi/39/ | FARMS free download ©2004 |
| barker-wisdom-tree.txt | Barker, *Wisdom and the Other Tree* SBL 2012, 8pp | http://www.margaretbarker.com/Papers/WisdomOtherTree.pdf | Author-posted, personal use |
| barker-highpriest.txt | Barker, *Our Great High Priest* Schmemann Lecture 2012, 15pp | http://www.margaretbarker.com/Papers/OurGreatHighPriest.pdf | Author-posted, personal use |
| barker-veil.txt | Barker, *Beyond the Veil* SJT 51/1 1998, 12pp | http://www.margaretbarker.com/Papers/BeyondtheVeil.pdf | Author-posted, personal use |
| heiser-diss.txt | Heiser diss. 2004, 271pp, UW-Madison | https://facultyshare.liberty.edu/ portal 40214537 | Liberty repo free download |
| heiser-otgodhead.txt | Heiser, *OT Godhead Language* 4pp | https://thedivinecouncil.com/OTGodheadLanguage.pdf | Author-posted |
| heiser-deut32.txt | Heiser, *Deut 32 Worldview* 3pp | https://thedivinecouncil.com/Deuteronomy32OTWorldview.pdf | Author-posted |
| christensen-paradigms.txt | Christensen, *Paradigms Regained* 102pp | https://archive.bookofmormoncentral.org/ .../kevin_christensen_op2_paradigms_regained_2001.pdf | FARMS/Archive free |
| bradshaw-temple.txt | Bradshaw, *Moses 6-7 and the Book of Giants* ~40pp | https://www.templethemes.net/publications/211019-Bradshaw-jmb-s.pdf | Free download |
| bradshaw-giants.html | Same, Interpreter mirror | https://interpreterfoundation.org/journal/moses-6-7-and-the-book-of-giants-remarkable-witnesses-of-enochs-ministry | CC BY-NC-ND |
| bokovoy-jacob.html | Bokovoy, *Ancient Temple Imagery in Jacob* | https://interpreterfoundation.org/journal/ancient-temple-imagery-in-the-sermons-of-jacob | CC BY-NC-ND |
| hamblin-josiah.html | Hamblin, *Vindicating Josiah* (counterpoint) | https://interpreterfoundation.org/journal/vindicating-josiah | CC BY-NC-ND |
| pike-elohim.html | Pike, *Name and Titles of God* RSC | https://rsc.byu.edu/vol-11-no-1-2010/name-titles-god-old-testament | BYU RSC free |
| symbol-index.json | 601-entry private symbol index | generated 2026-09-08, see below | derived, private |

Paywalled (preview/review only, never fetched as full text): Barker *Great Angel /
Mother Vol.1 / Temple Theology*, Smith *Early History*, Dever *Did God Have a Wife*,
Sommer *Bodies of God*, Heiser *Unseen Realm* book, Bradshaw Enoch book full PDF.

## Page-anchored citation in chat (how-to)

`symbol-index.json` entries look like:

```json
{"file": "barker-josiah.txt", "pdf_page": 5, "symbol": "Asherah",
 "snippet": "Proverbs describes wisdom as the tree of life..."}
```

- `pdf_page` = PDF page from `pdftotext` form-feed split (verified against
  `pdfinfo` counts: Josiah 21pp, Wisdom 8pp, HighPriest 15pp, Veil 12pp,
  Heiser diss 271pp, Paradigms 102pp, Bradshaw temple 216pp).
- Printed page = PDF page + offset (Josiah chapter: print p523 = PDFp1).
- In chat, answer in own words + short quote (<~250 words) + line:
  `Barker, *What Did Josiah Reform?*, Glimpses p531 (=PDFp9) — full paper: <URL>`
- Never paste full pages; never serve these files over HTTP.

## Regeneration

```bash
# PDFs live in /tmp/purity-shelf (not git). Re-convert after re-download:
pdftotext -layout <file>.pdf research/scholarship-private/<file>.txt
python3 -c "import json; ..."  # rebuild symbol-index.json (see session 2026-09-08)
```

## Sub-shelves (added 2026-09-08)

- `giants-watchers/` — Gen 6 / Watchers / BG scholarship. Vendored: Goff 2021, Heiser Tyndale 2014, Augsburg Ch.1 sample (+ root Bradshaw/Heiser-diss). Link-only: Annus MDPI, Goff FSU, Doak, Stuckenbruck, Wright, Hendel, Collins, Charles Enoch/Jubilees (PD links), DSS images. See `giants-watchers/SOURCES.md`.
- `astral-religion/` — planet/hosts/Queen-of-Heaven scholarship. Vendored: Steele 2018, Cohn JBQ. Link-only: Reiner NYU, Rochberg NYU/Cambridge sample, Cooley, Smith, Taylor, Keel, Dever MDPI, Barker Temple-Hidden, Heiser Helel, Angelini, Boeckle, Daniels. See `astral-religion/SOURCES.md`.
- `ancient-myths/` — PD-US originals vendored (Gutenberg): Hesiod, Iliad, Odyssey, Aeneid, Ovid I-XV, Babylonian Legends/Creation, OB Gilgamesh, Book of Dead. Link-only: Pyramid Mercer, ETCSL, Perseus, Theoi, CDLI/ORACC, UEE, Met/BM essays; copyright warnings for Foster/Dalley/Faulkner/Allen/Kovacs/Martinez. See `ancient-myths/SOURCES.md`.
- `symbol-index.json` now covers all 27 files, 535 entries, 50 symbols (page-level `pdf_page` where a PDF twin exists).
