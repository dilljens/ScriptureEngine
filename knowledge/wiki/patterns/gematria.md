# Gematria — Sacred Numbers and Patterns

Gematria is the Jewish system of assigning numerical value to Hebrew letters. Words or phrases with equal numerical values may be meaningfully connected.

## Gematria Systems

| System | Description | Example: צדק (righteousness) |
|--------|-------------|------|
| **Standard** (Mispar Hechrachi) | א=1, ב=2, ... ת=400 | 90+4+100 = 194 |
| **Ordinal** (Mispar Siduri) | Letter position in alphabet (1–22) | 18+4+19 = 41 |
| **Reduced** (Mispar Katan) | Standard → sum digits repeatedly | 1+9+4 = 14 → 1+4 = 5 |
| **Gadol** (Mispar Gadol) | Final forms get extended values (ך=500, ם=600, etc.) | 90+4+100 = 194 |

## Divine Names and Their Values

| Name | Hebrew | Value | Category |
|------|--------|-------|----------|
| YHWH | יהוה | 26 | Core name |
| Elohim | אלהים | 86 | God (Creator/Judge) |
| Adonai | אדני | 65 | Lord (Master) |
| El Shaddai | אל שדי | 345 | God Almighty |
| El | אל | 31 | God (generic) |
| Mashiach | משיח | 358 | Messiah |
| Yeshua | ישוע | 386 | Jesus/Salvation |
| Shekinah | שכינה | 385 | Divine presence |

## Sacred Numbers

| Number | Significance | Examples |
|--------|-------------|----------|
| **7** | Divine perfection, rest | 7 days of creation, 7-fold repetition |
| **10** | Divine order, completeness | 10 commandments, 10 plagues |
| **12** | Divine government | 12 tribes, 12 apostles |
| **26** | YHWH (יהוה) — the divine name | Found throughout in patterns |
| **40** | Testing, preparation, trial | 40 days flood, 40 years wilderness |
| **70** | Nations, elders | 70 nations of Genesis 10, 70 elders |
| **86** | Elohim (אלהים) — God | Creator, Judge |
| **358** | Mashiach (משיח) — Messiah | Redemption |
| **613** | Mitzvot — commandments | Torah commandments |

## Notable Patterns

### Genesis 1:1
- **7 Hebrew words** (7 = divine perfection)
- **28 letters** (7×4, triangular number of 7)
- **2701 total** = 37 × 73 (prime factors that mirror each other: 37 and 73 are digit reversals)
- **913** (first word "in beginning") reappears throughout scripture in patterns

### YHWH = 26 = "One" + "Love"
- **Echad** (אחד, "one") = 13 = half of 26
- **Ahavah** (אהבה, "love") = 13 = half of 26
- Thus "YHWH is One" (Deut 6:4) = 26 + 13 = 39
- And "God is Love" => Elohim (86) + Ahavah (13) = 99

### Mashiach = 358
- **Nachash** (נחש, serpent/bronze serpent) = 358
- The one "lifted up" (Moses' serpent and the Son of Man)
- **Shaddai** (שדי, Almighty) = 314, and **Mashiach** = 358 → difference of 44

## How to Use

- `scripture_gematria({"word": "יהוה"})` — get gematria of a Hebrew word
- `scripture_gematria({"verse": "gen.1.1"})` — get gematria of all words in a verse
- `scripture_gematria({"value": 26})` — find all verses with gematria value 26
- `scripture_gematria({"divine_names": true})` — show all divine names table
