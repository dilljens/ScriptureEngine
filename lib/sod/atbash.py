"""Atbash cipher — letter substitution pattern detection.

Atbash (אתבש) replaces each Hebrew letter with its mirror from the
opposite end of the alphabet: א→ת, ב→ש, ג→ר, etc.

The most famous example is Jeremiah 25:26 and 51:41 where ששך
(Sheshach) decodes to בבל (Babylon) via Atbash.
"""

# Hebrew alphabet in order (22 letters)
ALEPH_BET = list("אבגדהוזחטיכלמנסעפצקרשת")


def decode_atbash(text):
    """Decode a Hebrew word using Atbash substitution.
    
    Only operates on consonants. Maps each letter to its mirror
    position in the alphabet.
    
    Args:
        text: Hebrew word (with or without niqqud)
    
    Returns:
        decoded word as Hebrew consonants
    """
    result = []
    # Map final forms to their standard form for alphabet lookup
    FINAL_MAP = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}

    for ch in text:
        cp = ord(ch)
        letter = None
        # Extract the base letter (strip niqqud/cantillation)
        if 0x05D0 <= cp <= 0x05EA:
            letter = FINAL_MAP.get(ch, ch)  # Convert final forms to standard
        
        if letter and letter in ALEPH_BET:
            idx = ALEPH_BET.index(letter)
            # Mirror position: position 0 ↔ 21, 1 ↔ 20, etc.
            mirrored = ALEPH_BET[-(idx + 1)]
            result.append(mirrored)
    
    return "".join(result)
