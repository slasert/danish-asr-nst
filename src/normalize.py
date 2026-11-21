"""The ONE text-normalization policy, applied to references and hypotheses of every system.

Steps (order matters):
1. Unicode NFC (so "a" + combining ring and "å" are the same string).
2. Lowercase.
3. Numbers: every digit run is written out as a Danish cardinal with num2words
   ("2015" -> "totusinde og femten"). The NST sentence transcripts contain no digits (numbers
   are written as words in the manuscripts), so this only affects hypotheses: a system that
   writes "21" is not punished for using digits. Cardinal form only; ordinals and other
   spellings ("enogtyvende", "to tusind og femten") still count as errors.
4. Letters with diacritics that are NOT part of the Danish alphabet (é, ü, ö, ä, á ...)
   are reduced to their base letter. Danish letters æ ø å are kept. Reason: the accent in
   "idé", "én", "café" is optional in Danish spelling and used inconsistently by systems.
5. Apostrophes are deleted.
6. Hyphens, dashes and all other punctuation become spaces ("tv-apparater" -> "tv apparater").
7. Whitespace is collapsed.

We do NOT use Whisper's EnglishTextNormalizer (English-specific spelling rules).
"""
from __future__ import annotations

import re
import unicodedata

from num2words import num2words

DANISH_LETTERS = set("æøå")
_DIGITS = re.compile(r"\d+")
_APOS = re.compile(r"['’ʼ`´ˮ]")
_NON_WORD = re.compile(r"[^\w\s]|_")


def _num(m: re.Match) -> str:
    return " " + num2words(int(m.group(0)), lang="da") + " "


def _fold_foreign(ch: str) -> str:
    if ch in DANISH_LETTERS or ch.isascii():
        return ch
    base = unicodedata.normalize("NFD", ch)[0]
    return base if base.isascii() and base.isalpha() else ch


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", text).lower()
    t = _DIGITS.sub(_num, t)
    t = "".join(_fold_foreign(c) for c in t)
    t = _APOS.sub("", t)
    t = _NON_WORD.sub(" ", t)
    return " ".join(t.split())


def orthographic(text: str) -> str:
    """Orthographic form: keep casing and punctuation, only NFC + whitespace collapse."""
    return " ".join(unicodedata.normalize("NFC", text).split())
