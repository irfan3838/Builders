# Ported from copilot/expenses/backend/app/services/budget/pacing.py (pre-existing code written by the project owner, reused unchanged except imports).
"""The pacing / burn-velocity engine and the proactive alert levels (PRD §4). Pure functions over
integer paise and calendar position; no DB, no floats stored (percentages are display figures)."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

# Health bands by burn velocity (actual% / expected%), PRD §4.1.
VELOCITY_HIGH_RISK = 1.3  # burning substantially faster than time elapsed
VELOCITY_HEALTHY_LOW = 0.7  # below this: significantly under-utilised

# Alert levels, PRD §4.2.
ALERT_LIMIT_REACHED = "LIMIT_REACHED"  # spend >= 100%
ALERT_APPROACHING = "APPROACHING_LIMIT"  # spend >= 90%
ALERT_CRITICAL_BURN = "CRITICAL_BURN"  # spend >= 80% before day 15

# Health labels.
HEALTH_HIGH_RISK = "HIGH_RISK"
HEALTH_HEALTHY = "HEALTHY"
HEALTH_UNDERUTILISED = "UNDERUTILISED"


@dataclass(frozen=True)
class Pacing:
    day: int
    days_in_month: int
    expected_pct: float  # how far through the month, by calendar
    actual_pct: float  # how much of the adjusted budget is spent
    velocity: float | None  # actual% / expected%; None before the month starts elapsing
    health: str
    alert: str | None


def days_in_month(fiscal_month: date) -> int:
    return monthrange(fiscal_month.year, fiscal_month.month)[1]


def _round2(x: float) -> float:
    return round(x, 2)


def compute(actual_paise: int, adjusted_paise: int, day: int, total_days: int) -> Pacing:
    """`day` is the current day of the month (1..total_days); use total_days for a fully elapsed
    (closed) month."""
    day = max(0, min(day, total_days))
    expected = (day / total_days * 100) if total_days else 0.0
    actual = (actual_paise / adjusted_paise * 100) if adjusted_paise > 0 else 0.0
    # Burn velocity needs both a budget to measure against and some elapsed time.
    velocity = (actual / expected) if (expected > 0 and adjusted_paise > 0) else None

    if velocity is None:
        health = HEALTH_HEALTHY
    elif velocity > VELOCITY_HIGH_RISK:
        health = HEALTH_HIGH_RISK
    elif velocity < VELOCITY_HEALTHY_LOW:
        health = HEALTH_UNDERUTILISED
    else:
        health = HEALTH_HEALTHY

    alert: str | None = None
    if actual >= 100:
        alert = ALERT_LIMIT_REACHED
    elif actual >= 90:
        alert = ALERT_APPROACHING
    elif actual >= 80 and day < 15:
        alert = ALERT_CRITICAL_BURN

    return Pacing(
        day=day,
        days_in_month=total_days,
        expected_pct=_round2(expected),
        actual_pct=_round2(actual),
        velocity=_round2(velocity) if velocity is not None else None,
        health=health,
        alert=alert,
    )
