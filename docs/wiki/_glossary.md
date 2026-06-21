# Glossary

## Project Terms

| Term | Definition |
|------|------------|
| **Connection** | A typed link between two verses with layer, type, subtype, strength, confidence |
| **Layer** | Top-level connection category (linguistic, numerical, structural, etc.) — 10 total |
| **Type** | Specific connection kind within a layer (same_lemma, chiastic, allusion, etc.) — ~80 total |
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
| **Connection Panel** | Collapsible per-verse panel in the React frontend — groups connections by type, filterable, with confidence dots |
| **Footnote Tooltip** | Rich HTML popover that appears on hover over footnote markers/words — shows category, context word, and referenced verse text |
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
