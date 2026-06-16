# Biblical Hebrew — Reference

## Alphabet

| Letter | Name | Final | Standard Gematria | Gadol |
|--------|------|-------|-------------------|-------|
| א | Aleph | | 1 | 1 |
| ב | Bet | | 2 | 2 |
| ג | Gimel | | 3 | 3 |
| ד | Dalet | | 4 | 4 |
| ה | He | | 5 | 5 |
| ו | Vav | | 6 | 6 |
| ז | Zayin | | 7 | 7 |
| ח | Chet | | 8 | 8 |
| ט | Tet | | 9 | 9 |
| י | Yud | | 10 | 10 |
| כ | Kaf | ך | 20 | 500 |
| ל | Lamed | | 30 | 30 |
| מ | Mem | ם | 40 | 600 |
| נ | Nun | ן | 50 | 700 |
| ס | Samech | | 60 | 60 |
| ע | Ayin | | 70 | 70 |
| פ | Pe | ף | 80 | 800 |
| צ | Tsade | ץ | 90 | 900 |
| ק | Qof | | 100 | 100 |
| ר | Resh | | 200 | 200 |
| ש | Shin/Sin | | 300 | 300 |
| ת | Tav | | 400 | 400 |

## Morphological Codes

The morphhb dataset uses **Logos/MorphHB coding**. The format is `H` + [part of speech][morphology].

### Prefixes
| Code | Meaning | Examples |
|------|---------|----------|
| H | Hebrew | prefix for all Hebrew words |
| R | Preposition (prefix) | ב=in, ל=to, כ=as |
| Td | Definite article (ה) | הַ/שָּׁמַיִם = "the heavens" |
| C | Conjunction (ו) | and, but |
| Tc | Direct object marker (את) | |
| R | Preposition | various prepositions |

### Stem (Verb)
| Code | Meaning | Usage |
|------|---------|-------|
| Vq | Qal | Simple active |
| Vn | Niphal | Simple passive/reflexive |
| Vp | Piel | Intensive active |
| Vm | Pual | Intensive passive |
| Vh | Hiphil | Causative active |
| Vo | Hophal | Causative passive |
| Vt | Hithpael | Intensive reflexive |

### Verb Forms
| Code | Meaning |
|------|---------|
| Vqp | Qal Perfect (completed action) |
| Vqi | Qal Imperfect (incomplete/future) |
| Vqw | Qal Waw-Consecutive (narrative past) |
| Vqj | Qal Jussive (cohortative) |
| Vqr | Qal Participle (active) |
| Vqn | Qal Infinitive |
| Vqs | Qal Imperative |

### Verb Person/Number/Gender
| Code | Meaning |
|------|---------|
| 3ms | 3rd person masculine singular |
| 3fs | 3rd person feminine singular |
| 2ms | 2nd person masculine singular |
| 2fs | 2nd person feminine singular |
| 1cs | 1st person common singular |
| 3mp | 3rd person masculine plural |
| 3fp | 3rd person feminine plural |
| 2mp | 2nd person masculine plural |
| 1cp | 1st person common plural |

### Noun Types
| Code | Meaning |
|------|---------|
| Nc | Common noun |
| Nb | Proper noun (name) |
| Np | Proper noun (place) |
| Ng | Gentilic (people group) |

### Noun Number/Gender/State
| Code | Meaning |
|------|---------|
| cmsa | Common masculine singular absolute |
| cmsc | Common masculine singular construct |
| cfsa | Common feminine singular absolute |
| cmp | Common masculine plural |
| cfp | Common feminine plural |
| cms | Common masculine singular (unspecified) |

### Other
| Code | Meaning |
|------|---------|
| R | Preposition |
| D | Determiner (article) |
| To | Direct object marker |
| Ti | Interrogative |

## Gematria Notes

### Prefix Handling
Hebrew prefixes (ב=in, ל=to, כ=as, ו=and, ה=the) are separated by `/` in the morphhb text:
- `בְּ/רֵאשִׁ֖ית` = prefix ב + the word ראשית
- The `/` indicates a morphological boundary but doesn't affect gematria computation — the full form including the prefix is computed.

### Notable Divine Name Matches
See `patterns/gematria.md` for the full divine names table.
