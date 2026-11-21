# Ported from copilot/expenses/backend/app/services/budget/recommend.py (pre-existing code written by the
# project owner). `trend()` keeps the original rules over plain values instead of ORM rows; `plan()` is
# unchanged apart from carrying a category name/id instead of the ORM Category.
"""Trend recommendations: if a category has over- (or under-) run its budget for the past 3 closed
months by more than 15% on average, recommend increasing (or decreasing) that budget. Pure, paise."""

from dataclasses import dataclass

TREND_MONTHS = 3
TREND_THRESHOLD_PCT = 15.0
REASON_PREFIX = "Recommendation"


@dataclass(frozen=True)
class ClosedMonth:
    label: str  # e.g. "Aug'26"
    adjusted: int
    actual: int
    status: str


@dataclass(frozen=True)
class Recommendation:
    category_id: int
    category: str
    direction: str  # "INCREASE" | "DECREASE"
    avg_variance_pct: float  # average over/under-spend magnitude, percent (display, rounded after the test)
    suggested_delta_paise: int  # average monthly over/under amount (magnitude), floored to a paise
    months: list[str]


def trend(category_id: int, category: str, closed_chrono: list[ClosedMonth]) -> Recommendation | None:
    """`closed_chrono`: the category's closed months, oldest first (any number)."""
    recent = closed_chrono[-TREND_MONTHS:]
    if len(recent) < TREND_MONTHS or any(p.adjusted <= 0 for p in recent):
        return None
    months = [p.label for p in recent]
    if all(p.status == "OVERRUN" for p in recent):
        avg = sum((p.actual - p.adjusted) / p.adjusted * 100 for p in recent) / TREND_MONTHS
        if avg > TREND_THRESHOLD_PCT:
            delta = sum(p.actual - p.adjusted for p in recent) // TREND_MONTHS
            return Recommendation(category_id, category, "INCREASE", round(avg, 1), delta, months)
    elif all(p.status == "UNDERUSED" for p in recent):
        avg = sum((p.adjusted - p.actual) / p.adjusted * 100 for p in recent) / TREND_MONTHS
        if avg > TREND_THRESHOLD_PCT:
            delta = sum(p.adjusted - p.actual for p in recent) // TREND_MONTHS
            return Recommendation(category_id, category, "DECREASE", round(avg, 1), delta, months)
    return None


@dataclass(frozen=True)
class PlannedChange:
    """One budget change that acts on the recommendations, for one month (amounts in paise)."""

    kind: str  # "transfer" | "top_up" | "reduce"
    amount_paise: int
    source: str | None  # category name: transfer / reduce
    dest: str | None  # category name: transfer / top_up
    reason: str


def _whole_rupees(paise: int) -> int:
    return paise // 100 * 100


@dataclass
class _Slot:
    rec: Recommendation
    left: int  # paise still to cover (a need) or to give (a surplus)


def plan(recs: list[Recommendation]) -> list[PlannedChange]:
    """Act on the recommendations for one month, moving money before adding any: each over-running
    category (largest gap first) is fed from the under-used ones (largest surplus first); what no surplus
    covers is a top-up, and a surplus nobody needs is taken back. Exact whole-rupee paise; pure."""

    def slots(direction: str) -> list[_Slot]:
        out = [_Slot(r, _whole_rupees(r.suggested_delta_paise)) for r in recs if r.direction == direction]
        return sorted(out, key=lambda x: (-x.left, x.rec.category))

    needs, spare = slots("INCREASE"), slots("DECREASE")
    out: list[PlannedChange] = []
    for need in needs:
        name, months = need.rec.category.strip(), ", ".join(need.rec.months)
        for give in spare:
            amount = min(need.left, give.left)
            if amount <= 0:
                continue
            src = give.rec.category.strip()
            why = f"{REASON_PREFIX}: {src} under-used, {name} over budget ({months})"
            out.append(PlannedChange("transfer", amount, give.rec.category, need.rec.category, why))
            need.left -= amount
            give.left -= amount
        if need.left > 0:
            why = f"{REASON_PREFIX}: over budget ~{need.rec.avg_variance_pct}% ({months})"
            out.append(PlannedChange("top_up", need.left, None, need.rec.category, why))
    for give in spare:
        if give.left > 0:
            why = f"{REASON_PREFIX}: under-used ~{give.rec.avg_variance_pct}% ({', '.join(give.rec.months)})"
            out.append(PlannedChange("reduce", give.left, give.rec.category, None, why))
    return out
