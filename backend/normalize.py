"""Arabic text normalization for robust word/line comparison.

Whisper output and Quran text differ in diacritics, alef variants, tatweel,
and other orthographic marks. We strip/normalize so the comparison engine
compares on the same footing.
"""

import re
import unicodedata

# combining diacritics (harakat + Quranic marks) to strip
_HARAKAT = [
    0x064B, 0x064C, 0x064D, 0x064E, 0x064F, 0x0650, 0x0651, 0x0652,  # fatha/kasra/damma/sukun etc.
    0x0653, 0x0654, 0x0655, 0x0656, 0x0657, 0x0658, 0x0659, 0x065A,
    0x065B, 0x065C, 0x065D, 0x065E, 0x065F,
]
_HARAKAT_SET = frozenset(_HARAKAT)

# letter form unification
_LETTER_MAP = {
    0x0622: 0x0627, 0x0623: 0x0627, 0x0625: 0x0627, 0x0671: 0x0627,  # أإآٱ -> ا
    0x0670: 0x0627,  # superscript alif (dagger alif) -> ا
    0x0629: 0x0647,  # ة -> ه
    0x0649: 0x064A,  # ى -> ي
    0x0624: 0x0648,  # ؤ -> و
    0x0626: 0x064A,  # ئ -> ي
    0x0621: None,    # ء removed
    0x0640: None,    # tatweel ـ removed
}

_WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Strip diacritics, unify letter forms, collapse whitespace."""
    out = []
    for ch in unicodedata.normalize("NFKC", text):
        cp = ord(ch)
        if cp in _HARAKAT_SET:
            continue
        mapped = _LETTER_MAP.get(cp, None)
        if mapped is None:
            if cp in _LETTER_MAP:
                continue
            out.append(ch)
        else:
            out.append(chr(mapped))
    return _WS_RE.sub(" ", "".join(out).strip())


def normalize_words(words: list[str]) -> list[str]:
    return [normalize(w) for w in words]


def remove_small(word: str) -> str:
    """Remove punctuation/verse-number digits from a word token."""
    return re.sub(r"[\u0660-\u0669\u06DD\u06DE۝·.,؛:،]", "", word)
