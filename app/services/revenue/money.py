"""Ported from copilot clients_mod/money.py (user's own code), unchanged except this line.

Money without floats: amounts in a currency's minor units, rates as integer micro-rupees.

- `amount_minor`: the invoice amount in its currency's smallest unit (cents, paise, yen).
- `rate_micro`: rupees per one unit of the currency x 10^6 (EUR at 89.123456 -> 89_123_456).
- `total_paise`: the INR total, computed here only (never by a model, never in the browser).
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

INR = "INR"
# The ECB reference currencies Frankfurter quotes (plus INR itself). The CHECK constraint uses this list.
CURRENCIES: tuple[str, ...] = (
    "INR", "USD", "EUR", "GBP", "AUD", "CAD", "CHF", "SGD", "JPY", "CNY", "HKD", "NZD", "SEK",
    "NOK", "DKK", "ZAR", "AED", "BGN", "BRL", "CZK", "HUF", "IDR", "ILS", "ISK", "KRW", "MXN",
    "MYR", "PHP", "PLN", "RON", "THB", "TRY",
)  # fmt: skip
# what a client is billed in (and the dashboard shows): older rows may hold any of CURRENCIES
CLIENT_CURRENCIES: tuple[str, ...] = ("INR", "USD")
# AED is not an ECB currency: its rate is always entered by hand
MANUAL_ONLY = frozenset({"AED"})
ZERO_DECIMAL = frozenset({"JPY", "KRW", "ISK"})
SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "AUD": "A$", "CAD": "C$", "SGD": "S$"}
MICRO = 1_000_000
RATE_MAX = Decimal("100000")  # no currency is worth a lakh of rupees a unit


def digits(currency: str) -> int:
    return 0 if currency in ZERO_DECIMAL else 2


def to_minor(amount: str | int | Decimal, currency: str) -> int:
    """'2,000.50' EUR -> 200050. Raises ValueError for anything that is not a non-negative amount."""
    try:
        value = Decimal(str(amount).replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError("not an amount") from exc
    if not value.is_finite() or value < 0:
        raise ValueError("not an amount")
    scaled = value * (10 ** digits(currency))
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{currency} takes at most {digits(currency)} decimals")
    return int(scaled)


def from_minor(minor: int, currency: str) -> str:
    """200050 EUR -> '2000.50' (the API's string form)."""
    d = digits(currency)
    return str(minor) if d == 0 else f"{Decimal(minor).scaleb(-d):.{d}f}"


def to_rate_micro(rate: str | Decimal) -> int:
    """'89.12' -> 89_120_000. Must be positive and sane; rounded to six decimals."""
    try:
        value = Decimal(str(rate).replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError("not a rate") from exc
    if not value.is_finite() or value <= 0 or value > RATE_MAX:
        raise ValueError("not a rate")
    return int((value * MICRO).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def rate_str(rate_micro: int) -> str:
    """89_123_456 -> '89.123456'; at least four decimals ('89.1200')."""
    text = f"{Decimal(rate_micro).scaleb(-6):.6f}".rstrip("0")
    whole, _, frac = text.partition(".")
    return f"{whole}.{frac.ljust(4, '0')}"


def total_paise(amount_minor: int, currency: str, rate_micro: int) -> int:
    """INR total of an amount at a rate, rounded half up to the paisa."""
    if currency == INR:
        return amount_minor
    paise_per_minor = Decimal(rate_micro) * 100 / (MICRO * 10 ** digits(currency))
    return int((Decimal(amount_minor) * paise_per_minor).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def paise_to(paise: int, currency: str, rate_micro: int) -> int:
    """An INR figure in another currency's minor units at a rate (rupees per unit x 10^6), half up:
    the year grid shown in USD. Display only; stored figures stay in paise."""
    if currency == INR:
        return paise
    minor = Decimal(paise) * MICRO * 10 ** digits(currency) / (Decimal(rate_micro) * 100)
    return int(minor.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def share_minor(amount_minor: int, part_paise: int, total_paise: int) -> int:
    """The part of an invoice amount (its currency's minor units) that `part_paise` is of its INR
    total, half up: what is left of a part-paid invoice, in the client's currency."""
    if total_paise <= 0:
        return 0
    share = Decimal(amount_minor) * part_paise / total_paise
    return int(share.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def paise_str(paise: int) -> str:
    """API form of rupees: 123456 -> '1234.56'."""
    sign = "-" if paise < 0 else ""
    return f"{sign}{abs(paise) // 100}.{abs(paise) % 100:02d}"


def rupees_to_paise(rupees: str | int | Decimal) -> int:
    return to_minor(rupees, INR)


def _indian(n: int) -> str:
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups) + "," + tail


def format_inr(paise: int, *, whole: bool = False) -> str:
    """'₹1,23,456' (Indian grouping); paise shown only when there are some, never with `whole`
    (rounded half up to the rupee: the year grid, like the sheet)."""
    sign = "-" if paise < 0 else ""
    rupees, rest = divmod(abs(paise), 100)
    if whole:
        rupees, rest = rupees + (1 if rest >= 50 else 0), 0
    return f"{sign}₹{_indian(rupees)}" + (f".{rest:02d}" if rest else "")


def format_amount(minor: int, currency: str) -> str:
    """'€2,000', '$1,750.50', '₹21,390': Indian grouping for INR, thousands for the rest."""
    if currency == INR:
        return format_inr(minor)
    d = digits(currency)
    whole, rest = divmod(minor, 10**d)
    body = f"{whole:,}" + (f".{rest:0{d}d}" if d and rest else "")
    sym = SYMBOLS.get(currency)
    return f"{sym}{body}" if sym else f"{body} {currency}"


_CURRENCY_WORDS = {
    "usd": "USD", "dollar": "USD", "dollars": "USD",
    "eur": "EUR", "euro": "EUR", "euros": "EUR",
    "gbp": "GBP", "pound": "GBP", "pounds": "GBP", "sterling": "GBP",
    "inr": "INR", "rs": "INR", "rupee": "INR", "rupees": "INR",
    "yen": "JPY", "dirham": "AED", "dirhams": "AED",
}  # fmt: skip
_CURRENCY_SIGNS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}


def currencies_in(text: str) -> set[str]:
    """Currencies the user named: codes, symbols or words ('2000 euros', '$1,750', 'in GBP')."""
    found = {c for c in CURRENCIES if re.search(rf"\b{c}\b", text, re.IGNORECASE)}
    found |= {code for sign, code in _CURRENCY_SIGNS.items() if sign in text}
    found |= {
        code for word, code in _CURRENCY_WORDS.items() if re.search(rf"\b{word}\b", text, re.IGNORECASE)
    }
    return found


_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(k|lakhs?|lacs?|l|crores?|cr|mn|m)?\b", re.IGNORECASE)
_SCALE = {"k": 1_000, "l": 100_000, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000}
_SCALE |= {"cr": 10_000_000, "crore": 10_000_000, "crores": 10_000_000, "m": 1_000_000, "mn": 1_000_000}


def numbers_in(text: str) -> set[Decimal]:
    """Every number the user wrote, with k / lakh / crore applied ('1.5L' -> 150000, '2,000' -> 2000)."""
    out: set[Decimal] = set()
    for m in _NUMBER.finditer(text):
        try:
            value = Decimal(m.group(1).replace(",", ""))
        except InvalidOperation:
            continue
        out.add(value)
        if m.group(2):
            out.add(value * _SCALE[m.group(2).lower()])
    return out


def said(value: Decimal | int | str, text: str) -> bool:
    """The number appears in the user's words (a model never invents an amount)."""
    try:
        wanted = Decimal(str(value))
    except InvalidOperation:
        return False
    return wanted in numbers_in(text)
