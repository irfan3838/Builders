"""Deterministic classifier for a confirmation utterance (English, Hindi, Hinglish).

AFFIRM only when the whole utterance is affirmation (plus politeness filler). Anything with a
negation, a correction or extra content is AMBIGUOUS or NEGATIVE, so it never commits a write.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum


class Affirmation(StrEnum):
    AFFIRM = "affirm"
    NEGATIVE = "negative"
    AMBIGUOUS = "ambiguous"


_AFFIRM_PHRASES = sorted(
    {
        # English
        "yes", "yes please", "yeah", "yep", "yup", "confirm", "confirmed", "i confirm", "go ahead",
        "do it", "proceed", "ok", "okay", "sure", "correct", "that's right", "thats right", "approve it",
        "record it", "submit it", "please do", "yes do it", "yes go ahead", "absolutely",
        # Hinglish (romanized)
        "haan", "han", "haa", "ha", "haanji", "haan ji", "ji haan", "ji ha", "ji", "theek hai", "thik hai",
        "theek he", "thik he", "kar do", "kardo", "kar dijiye", "kar dijie", "bilkul", "sahi hai", "chalo",
        "haan kar do", "haan theek hai", "ho jaye", "ho jaaye",
        # Devanagari
        "हाँ", "हां", "हा", "जी", "जी हाँ", "जी हां", "हाँ जी", "हां जी", "ठीक है", "कर दो", "कर दीजिए",
        "बिल्कुल", "सही है", "हाँ कर दो", "हां कर दो",
    },
    key=len,
    reverse=True,
)
_FILLER = {"please", "plz", "sir", "madam", "ma'am", "bhai", "na", "toh", "to", "abhi", "so", "um", "uh", "hmm", "and", "aur", "ab", "जी", "अभी", "ना"}
_NEGATION = {
    "no", "nope", "not", "don't", "dont", "cancel", "stop", "wait", "hold", "wrong", "change", "nahi", "nahin",
    "nai", "na", "mat", "ruko", "ruk", "galat", "badlo", "lekin", "but", "magar", "par",
    "नहीं", "नही", "मत", "रुको", "गलत", "लेकिन", "मगर", "पर", "बदलो", "कैंसल",
}
# Tokens that are negation-like only in isolation-sensitive contexts are handled above; "na" is both
# a softener ("kar do na") and a negation. We treat a standalone "na" as negative only at the start.


def _normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", text).lower().strip()
    t = t.replace("’", "'")
    t = re.sub(r"[\.\,\!\?\।\"“”…:;\-–—]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def classify(text: str | None) -> Affirmation:
    if not text or not text.strip():
        return Affirmation.AMBIGUOUS
    t = _normalize(text)
    tokens = t.split()
    if tokens and (tokens[0] in ("na", "ना") or tokens[0] in _NEGATION):
        return Affirmation.NEGATIVE  # leads with a refusal: "na", "no, ...", "don't do it", "ruko"
    if any(tok in _NEGATION and tok != "na" for tok in tokens):
        return Affirmation.NEGATIVE if not _contains_affirm(t) else Affirmation.AMBIGUOUS
    rest = f" {t} "
    matched = False
    for phrase in _AFFIRM_PHRASES:
        needle = f" {phrase} "
        while needle in rest:
            rest = rest.replace(needle, " ", 1)
            matched = True
    leftover = [tok for tok in rest.split() if tok not in _FILLER]
    if matched and not leftover:
        return Affirmation.AFFIRM
    return Affirmation.AMBIGUOUS


def _contains_affirm(t: str) -> bool:
    padded = f" {t} "
    return any(f" {p} " in padded for p in _AFFIRM_PHRASES)
