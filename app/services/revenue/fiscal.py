"""Ported from copilot clients_mod/fiscal.py (user's own code), unchanged except this line.

Financial year April-March ('2026-27'), and month labels ('Oct'26')."""

import calendar
import re
from datetime import date

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_FY = re.compile(r"^(\d{4})-(\d{2})$")


def fy_of(year: int, month: int) -> str:
    start = year if month >= 4 else year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def fy_today(today: date) -> str:
    return fy_of(today.year, today.month)


def fy_start(fy: str) -> int:
    m = _FY.match(fy)
    if not m or (int(m.group(1)) + 1) % 100 != int(m.group(2)):
        raise ValueError(f"not a financial year: {fy}")
    return int(m.group(1))


def fy_months(fy: str) -> list[tuple[int, int]]:
    """[(2026, 4), (2026, 5), ... (2027, 3)]"""
    start = fy_start(fy)
    return [(start, m) for m in range(4, 13)] + [(start + 1, m) for m in range(1, 4)]


def month_label(year: int, month: int) -> str:
    return f"{MONTHS[month - 1]}'{year % 100:02d}"


def month_index(year: int, month: int) -> int:
    return year * 12 + month - 1


def from_index(index: int) -> tuple[int, int]:
    return index // 12, index % 12 + 1


def add_months(year: int, month: int, n: int) -> tuple[int, int]:
    return from_index(month_index(year, month) + n)


def last_day(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


_NAMES = {name.lower(): i + 1 for i, name in enumerate(MONTHS)}
_NAMES |= {calendar.month_name[i].lower(): i for i in range(1, 13)}
_NAMES |= {"sept": 9}


def month_number(text: str) -> int | None:
    """'Oct', 'october', '10', 'Oct'26' -> 10."""
    t = text.strip().lower().split("'")[0].split("-")[0].strip()
    if t.isdigit() and 1 <= int(t) <= 12:
        return int(t)
    return _NAMES.get(t)


# --- periods inside an FY: the whole year, a quarter (Q1 = Apr-Jun) or one month --------------------

QUARTERS = ("q1", "q2", "q3", "q4")
GROUPS = ("month", "quarter", "year")


RANGE_RE = re.compile(r"^(\d{4})-(\d{2})\.\.(\d{4})-(\d{2})$")


def period_months(fy: str, period: str) -> list[tuple[int, int]]:
    """'fy' -> the 12 months; 'q2' -> Jul..Sep; '2026-10' -> [(2026, 10)]; '2026-08..2026-10' -> Aug..Oct
    (every month in the FY)."""
    months = fy_months(fy)
    if period == "fy":
        return months
    if r := RANGE_RE.match(period):
        a, b = (int(r.group(1)), int(r.group(2))), (int(r.group(3)), int(r.group(4)))
        if a in months and b in months and months.index(a) <= months.index(b):
            return months[months.index(a) : months.index(b) + 1]
        raise ValueError(f"not a span of FY {fy}: {period}")
    if period in QUARTERS:
        q = QUARTERS.index(period)
        return months[q * 3 : q * 3 + 3]
    m = re.match(r"^(\d{4})-(\d{2})$", period)
    if m and (int(m.group(1)), int(m.group(2))) in months:
        return [(int(m.group(1)), int(m.group(2)))]
    raise ValueError(f"not a period of FY {fy}: {period}")


def quarter_of(fy: str, year: int, month: int) -> int:
    """0..3: the quarter of the FY a month falls in."""
    return fy_months(fy).index((year, month)) // 3


def period_label(fy: str, period: str) -> str:
    if period == "fy":
        return f"FY {fy}"
    if period in QUARTERS:
        months = period_months(fy, period)
        return f"{period.upper()} ({MONTHS[months[0][1] - 1]}-{MONTHS[months[-1][1] - 1]})"
    if RANGE_RE.match(period):
        months = period_months(fy, period)
        return f"{month_label(*months[0])} to {month_label(*months[-1])}"
    y, m = period_months(fy, period)[0]
    return month_label(y, m)


def bucket_label(fy: str, group: str, index: int) -> str:
    if group == "year":
        return f"FY {fy}"
    if group == "quarter":
        return period_label(fy, QUARTERS[index])
    y, m = fy_months(fy)[index]
    return month_label(y, m)
