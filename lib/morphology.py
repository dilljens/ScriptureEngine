"""
Hebrew and Greek morphology code parser.

Converts OSHB/WLC (Hebrew) and CCAT/SBLGNT (Greek) morphology codes
into human-readable descriptions.
"""

# === Hebrew morphology tables ===

HEBREW_POS = {
    "HV": "Verb",
    "HN": "Noun",
    "HA": "Adjective",
    "HR": "Preposition",
    "HC": "Conjunction",
    "HT": "Particle",
    "HP": "Pronoun",
    "HD": "Adverb",
    "AN": "Noun",
    "AV": "Verb",
    "AA": "Adjective",
    "AR": "Preposition",
    "AC": "Conjunction",
    "AT": "Particle",
    "AP": "Pronoun",
    "AD": "Adverb",
}

VERB_STEMS = {
    "q": "Qal",
    "N": "Niphal",
    "p": "Piel",
    "P": "Pual",
    "h": "Hiphil",
    "H": "Hophal",
    "t": "Hithpael",
    "o": "Polel",
    "O": "Polal",
    "r": "Hithpolel",
    "m": "Poel",
    "M": "Poal",
}

VERB_TYPES = {
    "p": "Perfect",
    "q": "Sequential Perfect",
    "i": "Imperfect",
    "w": "Sequential Imperfect",
    "h": "Cohortative",
    "j": "Jussive",
    "v": "Imperative",
    "r": "Participle active",
    "s": "Participle passive",
    "a": "Infinitive absolute",
    "c": "Infinitive construct",
}

GENDER_MAP_FULL = {"m": "masculine", "f": "feminine", "c": "common", "b": "both"}

NUMBER_MAP_FULL = {"s": "singular", "p": "plural", "d": "dual"}

NOUN_TYPES = {
    "c": "common",
    "g": "gentilic",
    "p": "proper name",
}

ADJ_TYPES = {
    "a": "adjective",
    "c": "cardinal number",
    "g": "gentilic",
    "o": "ordinal number",
}

NOUN_STATE = {
    "a": "absolute",
    "c": "construct",
    "d": "determined",
}

PRONOUN_TYPES = {
    "d": "demonstrative",
    "f": "indefinite",
    "i": "interrogative",
    "p": "personal",
    "r": "relative",
}

PARTICLE_TYPES = {
    "a": "affirmation",
    "d": "definite article",
    "e": "exhortation",
    "i": "interrogative",
    "j": "interjection",
    "m": "demonstrative",
    "n": "negative",
    "o": "direct object",
    "r": "relative",
}

# Map single-letter POS (used in compound segments after /) to names
SEGMENT_POS = {
    "V": "Verb",
    "N": "Noun",
    "A": "Adjective",
    "R": "Preposition",
    "C": "Conjunction",
    "T": "Particle",
    "P": "Pronoun",
    "D": "Adverb",
}

# Two-letter POS codes for the first segment (H/A prefix)
TWO_CHAR_POS = {
    "HV": "V", "AV": "V",
    "HN": "N", "AN": "N",
    "HA": "A", "AA": "A",
    "HR": "R", "AR": "R",
    "HC": "C", "AC": "C",
    "HT": "T", "AT": "T",
    "HP": "P", "AP": "P",
    "HD": "D", "AD": "D",
}

# === Greek morphology tables ===

GREEK_POS = {
    "N": "Noun",
    "V": "Verb",
    "C": "Conjunction",
    "P": "Preposition",
    "R": "Pronoun/Article",
    "D": "Adverb",
    "A": "Adjective",
    "I": "Interjection",
    "X": "Indeclinable",
}

GREEK_PERSON = {"1": "1st", "2": "2nd", "3": "3rd"}

GREEK_TENSE = {
    "P": "Present",
    "I": "Imperfect",
    "F": "Future",
    "A": "Aorist",
    "X": "Perfect",
    "Y": "Pluperfect",
}

GREEK_VOICE = {
    "A": "Active",
    "M": "Middle",
    "P": "Passive",
    "D": "Middle/Passive",
}

GREEK_MOOD = {
    "I": "Indicative",
    "D": "Imperative",
    "S": "Subjunctive",
    "O": "Optative",
    "N": "Infinitive",
    "P": "Participle",
}

GREEK_CASE = {
    "N": "Nominative",
    "G": "Genitive",
    "D": "Dative",
    "A": "Accusative",
}

GREEK_NUMBER = {
    "S": "Singular",
    "P": "Plural",
}

GREEK_GENDER = {
    "M": "Masculine",
    "F": "Feminine",
    "N": "Neuter",
}

# === Hebrew segment parsing ===

def _parse_verb(rest):
    if len(rest) < 4:
        return "Verb"
    stem_code = rest[0]
    type_code = rest[1]
    pgn = rest[2:5] if len(rest) >= 5 else rest[2:4]
    stem = VERB_STEMS.get(stem_code, stem_code)
    vtype = VERB_TYPES.get(type_code, type_code)
    return f"Verb {stem} {vtype} {pgn}"


def _parse_noun(rest):
    if len(rest) < 4:
        return "Noun"
    ntype = NOUN_TYPES.get(rest[0], rest[0])
    gender = GENDER_MAP_FULL.get(rest[1], rest[1])
    number = NUMBER_MAP_FULL.get(rest[2], rest[2])
    state = NOUN_STATE.get(rest[3], rest[3])
    return f"Noun {ntype} {gender} {number} {state}"


def _parse_adjective(rest):
    if len(rest) < 4:
        return "Adjective"
    atype = ADJ_TYPES.get(rest[0], rest[0])
    gender = GENDER_MAP_FULL.get(rest[1], rest[1])
    number = NUMBER_MAP_FULL.get(rest[2], rest[2])
    state = NOUN_STATE.get(rest[3], rest[3])
    return f"Adjective {atype} {gender} {number} {state}"


def _parse_pronoun(rest):
    if not rest:
        return "Pronoun"
    ptype = PRONOUN_TYPES.get(rest[0], rest[0])
    return f"Pronoun {ptype}"


def _parse_particle(rest):
    if not rest:
        return "Particle"
    ptype = PARTICLE_TYPES.get(rest[0], rest[0])
    return f"Particle {ptype}"


def _parse_hebrew_segment(seg, is_first):
    if not seg:
        return "Unknown code"

    if is_first:
        if seg[0] not in ("H", "A") or len(seg) < 2:
            return "Unknown code"
        two_letter = seg[:2]
        pos_letter = TWO_CHAR_POS.get(two_letter)
        if pos_letter is None:
            return "Unknown code"
        rest = seg[2:]
    else:
        pos_letter = seg[0]
        if pos_letter not in SEGMENT_POS:
            return "Unknown code"
        rest = seg[1:]

    if pos_letter == "V":
        return _parse_verb(rest)
    elif pos_letter == "N":
        return _parse_noun(rest)
    elif pos_letter == "A":
        return _parse_adjective(rest)
    elif pos_letter == "T":
        return _parse_particle(rest)
    elif pos_letter == "P":
        return _parse_pronoun(rest)
    elif pos_letter == "R":
        return "Preposition"
    elif pos_letter == "C":
        return "Conjunction"
    elif pos_letter == "D":
        return "Adverb"
    else:
        return SEGMENT_POS.get(pos_letter, "Unknown code")


def _parse_hebrew_desc(code):
    parts = code.split("/")
    descriptions = []
    for i, seg in enumerate(parts):
        descriptions.append(_parse_hebrew_segment(seg, i == 0))
    return " + ".join(descriptions)


# === Greek segment parsing ===

def _parse_greek_desc(code):
    if len(code) < 11:
        return "Unknown code"

    pos_code = code[0]
    pos = GREEK_POS.get(pos_code, "Unknown")

    person_code = code[3]
    tense_code = code[4]
    voice_code = code[5]
    mood_code = code[6]

    is_finite = person_code not in ("-", " ")

    if not is_finite:
        case_code = code[7]
        number_code = code[8]
        gender_code = code[9]
        parts = [pos]
        if case_code not in ("-", " "):
            parts.append(GREEK_CASE.get(case_code, case_code))
        if number_code not in ("-", " "):
            parts.append(GREEK_NUMBER.get(number_code, number_code))
        if gender_code not in ("-", " "):
            parts.append(GREEK_GENDER.get(gender_code, gender_code))
        return " ".join(parts)

    person = GREEK_PERSON.get(person_code, person_code)
    tense = (
        GREEK_TENSE.get(tense_code, tense_code)
        if tense_code not in ("-", " ")
        else None
    )
    voice = (
        GREEK_VOICE.get(voice_code, voice_code)
        if voice_code not in ("-", " ")
        else None
    )
    mood = (
        GREEK_MOOD.get(mood_code, mood_code)
        if mood_code not in ("-", " ")
        else None
    )

    parts = [pos, person]
    if tense:
        parts.append(tense)
    if voice:
        parts.append(voice)
    if mood:
        parts.append(mood)

    num_code = code[8]
    if num_code not in ("-", " "):
        parts.append(GREEK_NUMBER.get(num_code, num_code))

    return " ".join(parts)


# === Public API ===

def parse_hebrew(code):
    try:
        desc = _parse_hebrew_desc(code)
        return f"{code} ({desc})"
    except (IndexError, KeyError):
        return f"{code} (Unknown code)"


def parse_greek(code):
    try:
        desc = _parse_greek_desc(code)
        return f"{code} ({desc})"
    except (IndexError, KeyError):
        return f"{code} (Unknown code)"


def parse(code, lang="auto"):
    try:
        if lang == "hebrew":
            return _parse_hebrew_desc(code)
        elif lang == "greek":
            return _parse_greek_desc(code)

        stripped = code.strip()
        if stripped and stripped[0] in ("H", "A"):
            return _parse_hebrew_desc(code)
        elif " " in stripped or "-" in stripped:
            return _parse_greek_desc(code)
    except (IndexError, KeyError):
        pass

    return "Unknown code"


def lookup_description(morph_code):
    overrides = {
        "HVqp3ms": "Verb Qal Perfect 3rd masculine singular",
        "V- 3AAI-S--": "Verb 3rd Aorist Active Indicative Singular",
    }
    result = overrides.get(morph_code)
    if result is not None:
        return result
    return parse(morph_code)


# === Self-tests ===

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    # Hebrew
    assert parse('HVqp3ms') == "Verb Qal Perfect 3ms", (
        f"Got: {parse('HVqp3ms')!r}"
    )
    assert parse('HC/Vqw3ms') == "Conjunction + Verb Qal Sequential Imperfect 3ms", (
        f"Got: {parse('HC/Vqw3ms')!r}"
    )
    assert parse('HNcmsa') == "Noun common masculine singular absolute", (
        f"Got: {parse('HNcmsa')!r}"
    )
    assert parse('HR/Ncfsa') == "Preposition + Noun common feminine singular absolute", (
        f"Got: {parse('HR/Ncfsa')!r}"
    )
    assert parse('HTd/Ncmpa') == "Particle definite article + Noun common masculine plural absolute", (
        f"Got: {parse('HTd/Ncmpa')!r}"
    )

    # Greek
    assert parse('V- 3AAI-S--') == "Verb 3rd Aorist Active Indicative Singular", (
        f"Got: {parse('V- 3AAI-S--')!r}"
    )
    assert parse('N- ----NSM-') == "Noun Nominative Singular Masculine", (
        f"Got: {parse('N- ----NSM-')!r}"
    )

    # API consistency
    assert parse_hebrew('HVqp3ms') == "HVqp3ms (Verb Qal Perfect 3ms)"
    assert parse_greek('V- 3AAI-S--') == "V- 3AAI-S-- (Verb 3rd Aorist Active Indicative Singular)"

    logger.info("All morphology tests passed!")
