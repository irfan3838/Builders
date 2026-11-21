# Ported from copilot/expenses/backend/app/services/budget/projection.py (pre-existing code written by the project owner, reused unchanged except imports).
"""Where a budget is heading, and what a change would do to it ("IT may go up 15% from December — is
the annual budget enough?"). Integer paise, pure: the assistant feeds it SQL numbers and prints it.

- Months already over: what was spent. This month: its run rate (`forecast.month_outlook`). Months to
  come: the *pace*, the average of the last (up to) 3 full months, the rule `forecast.year_outlook`
  uses. With no full month yet, each month's own budget stands in for the pace (the answer says so).
- A change applies from its start month to its end (inclusive) on top of that: a % of the month's
  projected spend, an amount every month, or an amount once.
"""

from dataclasses import dataclass

from app.services.budgeting import forecast

PACE_MONTHS = 3
MONTHS = 12


@dataclass(frozen=True)
class Change:
    start: int  # FY month index, 0 = April
    end: int  # inclusive
    percent_bp: int = 0  # basis points of the month's projected spend (15% = 1500; -20% = -2000)
    amount: int = 0  # paise, already times the count
    per_month: bool = False  # the amount every month of the window, else once in the start month


@dataclass(frozen=True)
class Month:
    index: int
    budget: int
    actual: bool  # spent (an over month), else projected
    spend: int  # spent, or the projection with no change
    changed: int  # with the changes
    left: int  # the year's budget minus everything up to and including this month (with the changes)


@dataclass(frozen=True)
class Projection:
    budget: int  # the FY budget now
    spent: int  # so far (this month included)
    pace: int  # a month to come, at today's pace
    pace_months: int  # full months the pace is the average of (0: the budget stands in)
    baseline: int  # year-end spend with no change
    projected: int  # year-end spend with the changes
    months: list[Month]

    @property
    def extra(self) -> int:
        """What the changes add by year end (negative: what they save)."""
        return self.projected - self.baseline

    @property
    def headroom(self) -> int:
        """Budget left at year end with the changes (negative: short by)."""
        return self.budget - self.projected

    @property
    def runs_out(self) -> int | None:
        """The first month the year's spend passes the year's budget, with the changes; None if never."""
        return next((m.index for m in self.months if m.left < 0), None)


def pace_of(actuals: list[int], current: int) -> tuple[int, int]:
    """(pace, how many full months it averages): the last up to 3 months before `current`."""
    full = actuals[max(0, current - PACE_MONTHS) : max(0, current)]
    return (sum(full) // len(full), len(full)) if full else (0, 0)


def _share(paise: int, bp: int) -> int:
    """paise x bp / 10000, rounded toward zero (whole paise; never a float)."""
    out = abs(paise) * abs(bp) // 10_000
    return out if (paise >= 0) == (bp >= 0) else -out


def project(
    budgets: list[int],
    actuals: list[int],
    current: int,
    day: int,
    days_in_month: int,
    changes: list[Change] | None = None,
    pace: tuple[int, int] | None = None,
) -> Projection:
    """budgets / actuals: the FY's 12 months (April first). current: this month's index; 12 when the
    FY is over, -1 when it has not begun (then `pace` should come from the year before)."""
    pace_paise, pace_months = pace if pace is not None else pace_of(actuals, current)
    rows: list[Month] = []
    total = sum(budgets)
    running = 0
    for i in range(MONTHS):
        if i < current:
            base, actual = actuals[i], True
        elif i == current:
            base, actual = forecast.month_outlook(budgets[i], actuals[i], day, days_in_month).predicted, False
        else:
            base, actual = (pace_paise if pace_months else budgets[i]), False
        changed = base
        if not actual:
            for c in changes or []:
                if c.start <= i <= c.end:
                    changed += _share(base, c.percent_bp)
                    if c.per_month or i == c.start:
                        changed += c.amount
            changed = max(0, changed)
        running += changed
        rows.append(Month(i, budgets[i], actual, base, changed, total - running))
    return Projection(
        budget=total,
        spent=sum(actuals[: max(0, min(current + 1, MONTHS))]),
        pace=pace_paise if pace_months else 0,
        pace_months=pace_months,
        baseline=sum(r.spend for r in rows),
        projected=sum(r.changed for r in rows),
        months=rows,
    )


def scaled(months: list[int], percent_bp: int) -> list[int]:
    """Each month's spend grown (or cut) by a %: next year's need from this year's projection."""
    return [max(0, m + _share(m, percent_bp)) for m in months]
