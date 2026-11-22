"""A model never supplies a booked amount or rate on its own: the number must appear in what the user said.

Copilot checked typed chat text with `money.said`. Purser is voice-first, so the transcript may hold digits
("50,000", "1.5L") or words in English / Hindi / Hinglish ("fifty thousand", "pachaas hazaar", "dedh lakh").
`numbers_spoken` reads both. The words come from server-observed turns only (VoiceTurn), never from the model.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import VALIDATION, DomainError
from app.models import VoiceTurn
from app.services.confirmation import SERVER_OBSERVED
from app.services.revenue.money import numbers_in

LOOKBACK_TURNS = 6  # the amount may have been said a few turns before (clarifying the client, the month)

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    # Hindi / Hinglish (romanised, common spellings)
    "ek": 1, "do": 2, "teen": 3, "tin": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "chhah": 6,
    "che": 6, "saat": 7, "sat": 7, "aath": 8, "ath": 8, "nau": 9, "das": 10, "dus": 10, "gyarah": 11, "barah": 12,
    "baarah": 12, "terah": 13, "chaudah": 14, "pandrah": 15, "solah": 16, "satrah": 17, "atharah": 18,
    "unnis": 19, "bees": 20, "bis": 20, "pachchis": 25, "pachees": 25, "pachis": 25, "tees": 30, "tis": 30,
    "paintis": 35, "chalis": 40, "chaalis": 40, "paintalis": 45, "pachaas": 50, "pachas": 50, "pachpan": 55,
    "saath": 60, "painsath": 65, "sattar": 70, "pachattar": 75, "assi": 80, "pachasi": 85, "nabbe": 90, "nabbey": 90,
    "aadha": Decimal("0.5"), "dedh": Decimal("1.5"), "dhai": Decimal("2.5"), "dhaai": Decimal("2.5"),
    "sawa": None, "saade": None, "sadhe": None,  # modifiers, handled below
}
_SCALES = {"hundred": 100, "sau": 100, "thousand": 1_000, "hazaar": 1_000, "hazar": 1_000, "hajar": 1_000,
           "k": 1_000, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "crore": 10_000_000,
           "crores": 10_000_000, "cr": 10_000_000, "million": 1_000_000}
# Devanagari number words (the live transcript often writes Hindi speech in Devanagari: "दो लाख दस हज़ार").
_DEVA_UNITS = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "छे": 6, "सात": 7, "आठ": 8,
    "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12, "तेरह": 13, "चौदह": 14, "पंद्रह": 15, "पन्द्रह": 15, "सोलह": 16,
    "सत्रह": 17, "अठारह": 18, "उन्नीस": 19, "बीस": 20, "पच्चीस": 25, "तीस": 30, "पैंतीस": 35, "चालीस": 40,
    "पैंतालीस": 45, "पचास": 50, "पचपन": 55, "साठ": 60, "पैंसठ": 65, "सत्तर": 70, "पचहत्तर": 75, "अस्सी": 80,
    "पचासी": 85, "नब्बे": 90, "आधा": Decimal("0.5"), "डेढ़": Decimal("1.5"), "ढाई": Decimal("2.5"),
}
_DEVA_WORDS = {"सवा": "sawa", "साढ़े": "saade", "साढे": "saade", "सौ": "sau", "हज़ार": "hazaar", "हजार": "hazaar",
               "लाख": "lakh", "करोड़": "crore", "करोड": "crore", "और": "aur", "रुपये": "rupaye", "रुपए": "rupaye"}
_nfc = lambda w: unicodedata.normalize("NFC", w)  # noqa: E731 - nukta letters (ज़, ढ़) have two encodings
_UNITS.update({_nfc(k): v for k, v in _DEVA_UNITS.items()})
_DEVA_WORDS = {_nfc(k): v for k, v in _DEVA_WORDS.items()}
_TOKEN = re.compile(r"\d+(?:\.\d+)?|[a-z]+|[\u0900-\u097F]+")


def _words_to_numbers(text: str) -> set[Decimal]:
    """Every number written as words. 'pachaas hazaar' -> 50000, 'dedh lakh' -> 150000, 'saade teen lakh' -> 350000,
    'twelve thousand five hundred' -> 12500, '2 lakh 10 hazaar' -> 210000."""
    out: set[Decimal] = set()
    tokens = [_DEVA_WORDS.get(t, t) for t in _TOKEN.findall(_nfc(text).lower().replace(",", ""))]
    total, current, active, modifier = Decimal(0), Decimal(0), False, None
    for tok in tokens + ["<end>"]:
        if tok in ("sawa", "saade", "sadhe"):
            modifier = tok
            continue
        val: Decimal | None = None
        if re.fullmatch(r"\d+(?:\.\d+)?", tok):
            val = Decimal(tok)
        elif tok in _UNITS and _UNITS[tok] is not None:
            val = Decimal(str(_UNITS[tok]))
        if val is not None:
            if modifier == "sawa":
                val += Decimal("0.25")
            elif modifier in ("saade", "sadhe"):
                val += Decimal("0.5")
            modifier = None
            current += val
            active = True
            continue
        if tok in _SCALES and not active and modifier:  # 'sawa lakh' = 1.25 lakh, 'saade hazaar' = 1.5 thousand
            current, active = Decimal("1.25") if modifier == "sawa" else Decimal("1.5"), True
            modifier = None
        if tok in _SCALES and active:
            scale = _SCALES[tok]
            if scale == 100:
                current = (current or 1) * 100
            else:
                total += (current or 1) * scale
                current = Decimal(0)
            out.add(total + current)
            continue
        if tok in ("and", "aur"):
            continue
        if active:
            out.add(total + current)
        total, current, active, modifier = Decimal(0), Decimal(0), False, None
    return {v for v in out if v > 0}


def numbers_spoken(text: str) -> set[Decimal]:
    return numbers_in(text) | _words_to_numbers(text)


def _normal(v: Decimal | str) -> Decimal:
    return Decimal(str(v)).normalize()


def said_in(value: Decimal | int | str, text: str) -> bool:
    try:
        wanted = _normal(value)
    except Exception:  # noqa: BLE001 - not a number: not said
        return False
    return any(_normal(n) == wanted for n in numbers_spoken(text))


async def recent_words(s: AsyncSession, actor: Actor) -> str | None:
    """The user's last few server-observed turns in this conversation, newest last. None outside a conversation
    (the on-screen form and the API, where a person typed the number into a field)."""
    if not actor.conversation_id:
        return None
    q = (select(VoiceTurn.transcript).where(VoiceTurn.conversation_id == actor.conversation_id,
                                           VoiceTurn.source.in_(SERVER_OBSERVED))
         .order_by(VoiceTurn.id.desc()).limit(LOOKBACK_TURNS))
    rows = list((await s.execute(q)).scalars())
    return " \n ".join(reversed(rows))


async def require_said(s: AsyncSession, actor: Actor, values: dict[str, str | None]) -> None:
    """Each non-empty value must appear in the user's recent words, else ask them to say it."""
    words = await recent_words(s, actor)
    if words is None:
        return
    for what, v in values.items():
        if v in (None, ""):
            continue
        clean = str(v).replace(",", "").replace("₹", "").replace("$", "").strip()
        if not said_in(clean, words):
            raise DomainError(VALIDATION, f"I didn't hear the {what} {v} from you. Please say the {what} again.",
                              field=what, ungrounded=str(v))
