# Glossary

## Project Terms

| Term | Definition |
|------|------------|
| **Connection** | A typed link between two verses with layer, type, subtype, strength, confidence |
| **Layer** | Top-level connection category — 11 total (linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, sod) |
| **Type** | Specific connection kind within a layer (same_lemma, chiastic, allusion, etc.) — 125 types defined |
| **septuagint_difference** | Textual variant where the LXX (Greek OT) differs from the Masoretic Hebrew text — 8,601 connections |
| **textual_variant** | Manuscript variant where Greek NT editions differ (NA, TR, SBL, etc.) — 3,117 connections |
| **quotation_variant** | NT quotation of OT where the source text differs between editions — 1,833 connections |
| **peshitta_variant** | Syriac Peshitta variant — no data source found yet (last empty type) |
| **Subtype** | Optional refinement within a type (rare_word_cluster, giliadi_catchword, etc.) |
| **Passage Guide** | Pre-computed JSON blob per verse with all connections, gematria, quality |
| **PaRDeS** | Four-level hermeneutical framework: P'shat, Remez, Drash, Sod |
| **Gematria** | Hebrew letter-to-number system (standard, ordinal, reduced, mispar gadol) |
| **Isopsephy** | Greek letter-to-number system (equivalent to gematria) |
| **Sod** | Hidden/mystical connections — Atbash, acrostics, hidden names, notarikon |
| **Null-Text** | Baseline text with no real connections — used for statistical validation |
| **Pre-registration** | Pre-committing a hypothesis before testing to prevent p-hacking |
| **Speculative** | Lowest quality level — connections that need review before promotion |
| **MCP** | Model Context Protocol — stdio JSON-RPC for AI tool consumption |
| **TOOL_REGISTRY** | Central registry in lib/api/__init__.py — all 23 tools registered here |

## Scripture Terms

| Term | Definition |
|------|------------|
| **Lemma** | Dictionary/base form of a word (typically Strong's number) |
| **Strong's Number** | Standard numbering system for Hebrew (Hxxxx) and Greek (Gxxxx) words |
| **Triconsonantal Root** | The three-consonant core shared by related Hebrew words (e.g., שׂ-ה-ה) |
| **Masoretic Text (MT)** | The traditional Hebrew text of the OT |
| **Septuagint (LXX)** | The ancient Greek translation of the OT |
| **Type/Antitype** | OT person/event/institution that prefigures (type) its NT fulfillment (antitype) |
| **Chiasm** | Literary mirror structure: A-B-C-C'-B'-A' |
| **Inclusio** | Same phrase opening and closing a literary unit |
| **Midrash** | Rabbinic interpretive reading that connects texts |

## Frontend Terms

| Term | Definition |
|------|------------|
| **Command Palette** | Universal `/` command input — fuzzy book search, `/chat`, `/search`, `/dark`, `/font`, `/toggle`, etc. |
| **Connection Panel** | Collapsible per-verse panel in the React frontend — groups connections by type, filterable, with confidence dots |
| **Footnote Tooltip** | Rich HTML popover that appears on hover over footnote markers/words — shows category, context word, and referenced verse text |
| **Verse Jump** | Type a verse number in chapter view → scroll to that verse with highlight |
| **Library View** | Top-level view showing all 7 works as color-coded cards (OT, NT, BoM, D&C, PGP, DSS, CH) |
| **Tab-based Chat** | Ctrl+P opens a chat tab (not overlay) with edit/resend, copy per-message, copy all |
| **VersePreviewCard** | React component that fetches a full chapter and renders a scrollable preview with highlighted target verse(s) |
| **fn-marker** | CSS class on footnote superscript elements (`<sup class="fn-marker">`) |
| **fn-word** | CSS class on the annotated word span in the verse text |
| **TSK Popup** | Modal overlay showing Treasury of Scripture Knowledge cross-references for a verse |

## Suggested Terms

| Term | Notes |
|------|-------|
| **Lexicon** | The planned word dictionary (one entry per lemma) |
| **Semantic Domain** | Conceptual grouping of related words (thesaurus categories) |
| **Text Wiki** | Entity/concept articles auto-summarized from the text |
| **Discovered By** | Source of a connection: 'algorithm', 'ai', or 'human' |
| **Quality Level** | Calibration tier: certain → probable → speculative → suggested → rejected |
| **Context Budget** | 300K token limit per chat call, compaction at 200K strips old tool traces |
| **Library View** | Highest zoom level — shows all works as cards |
