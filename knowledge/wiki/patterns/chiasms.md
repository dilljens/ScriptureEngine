# Chiastic Structures

Chiasms (also called chiasmus or ring structures) are literary patterns where elements are repeated in reverse order: A-B-C-C'-B'-A'. The name comes from the Greek letter Chi (Χ), representing the crossing pattern.

## Detection

The algorithmic chipatic detector in `lib/patterns/chiastic.py`:
1. Tokenizes verses into key terms (removing stop words)
2. Looks for mirrored word/phrase sequences at distance
3. Scores chiasms by shared term count + number of inner layers

Confidence thresholds:
- >0.6: Strong chiasm (likely intentional)
- 0.4–0.6: Moderate pattern (suggestive)
- <0.4: Weak (may be coincidental)

## Known Chiasms in the Canon

### Book of Mormon
- **Alma 36**: Widely recognized as one of the most perfectly structured chiasms in scripture
- **Mosiah 5:10–12**: Chiastic structure around taking Christ's name
- **1 Nephi 1**: Lehi's vision experience forms a chiasm

### Old Testament
- **Genesis 6–9**: The Flood narrative has a complex chiastic structure
- **Leviticus**: The Holiness Code contains extensive chiastic patterns
- **Isaiah 6**: Temple vision chiasm (A: vision → B: response → C: confession → C': commission → B': message → A': remnant)
- **Amos**: The oracles against nations form a seven-part chiastic structure

### New Testament
- **Matthew 1–28**: The entire Gospel may have chiastic macrostructure
- **John 1:1–18**: The Prologue forms an intricate chiasm
- **Romans 5–8**: Paul's argument on justification has chiastic elements
- **Hebrews**: Temple theology structured as extended chiasm

## Giliadi's Contributions

Avraham Giliadi has documented unprecedented chiastic structures throughout the Bible, including:
- Word-count based chiasms (uneven member lengths that mirror each other)
- Thematic chiasms spanning entire books
- Numerical chiasms where word counts form mirror patterns
- Multi-level chiasms (chiasm within chiasm within chiasm)

His methodology focuses on the integral structure of each biblical book as a unified literary composition.

## Future Work

- Run chiastic detector on all chapters of Genesis and Isaiah
- Cross-reference detected chiasms with known structures from scholarly literature
- Flag previously undocumented chiasms for human review
- Train AI to recognize chiastic patterns using known examples
