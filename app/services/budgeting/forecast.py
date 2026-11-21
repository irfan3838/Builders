# Ported from copilot/expenses/backend/app/services/budget/forecast.py (pre-existing code written by the project owner, reused unchanged except imports).
"""Where spend is heading (run rate), for the CEO's three bars: allocated, spent, predicted. Paise, pure.

- Month: spent so far / days elapsed x days in the month.
- Year: spent in the months already over + this month at its run rate + the average of the last (up
  to) 3 full months for every month still to come.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Outlook:
    allocated: int  # the budget now (after transfers / top-ups)
    spent: int  # so far
    predicted: int  # at the current run rate, by the end of the period


def month_outlook(budget: int, spent: int, day: int, days_in_month: int) -> Outlook:
    day = max(1, min(day, days_in_month))
    return Outlook(budget, spent, spent * days_in_month // day)


def year_outlook(
    budgets: list[int], spends: list[int], current: int, day: int, days_in_month: int
) -> Outlook:
    """budgets / spends: the FY's 12 months in order; current: index of this month (0 = April)."""
    full = spends[:current]
    this = month_outlook(budgets[current], spends[current], day, days_in_month).predicted
    recent = full[-3:]
    pace = sum(recent) // len(recent) if recent else this
    ahead = 11 - current
    return Outlook(sum(budgets), sum(spends[: current + 1]), sum(full) + this + pace * ahead)
