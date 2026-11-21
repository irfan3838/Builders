# Ported from copilot/expenses/backend/app/services/budget/distribution.py (pre-existing code written by the project owner, reused unchanged except imports).
"""Annual -> monthly budget distribution (PRD §3). Integer paise only; no paise is ever lost.

An even split divides the annual amount across the 12 FY months and spreads the remainder one
paise at a time, so the months always sum back to the annual total. `rebalance` supports the
"a single month was edited -> recalculate the remaining months evenly to retain the annual
total" prompt: the edited (locked) months are kept and the rest absorb the difference.
"""

from collections.abc import Sequence
from fractions import Fraction

MONTHS_IN_YEAR = 12


def even_split(total_paise: int, n: int = MONTHS_IN_YEAR) -> list[int]:
    """Divide `total_paise` into `n` parts that sum exactly to it (remainder on the first parts)."""
    if n <= 0:
        raise ValueError("n must be positive")
    base, rem = divmod(total_paise, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def rebalance(amounts: Sequence[int], locked: set[int], total_paise: int) -> list[int]:
    """Keep the `locked` month indices as given and spread `total_paise - sum(locked)` evenly over
    the rest, so the twelve months still sum to the annual total. If every month is locked the
    amounts are returned unchanged (the caller decides whether to keep the mismatch)."""
    out = list(amounts)
    free = [i for i in range(len(out)) if i not in locked]
    if not free:
        return out
    remaining = total_paise - sum(out[i] for i in locked)
    split = even_split(remaining, len(free))
    for slot, i in enumerate(sorted(free)):
        out[i] = split[slot]
    return out


# --- spreading one change over several months (reallocate / top-up / reduce) -----------------------

PLAN_KINDS = ("one", "equal", "custom", "shares", "step")
BASIS_POINTS = 10_000  # 100% in basis points: shares are whole hundredths of a percent
FY_ORDER = (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)


def by_weights(total_paise: int, weights: Sequence[Fraction]) -> list[int]:
    """Split `total_paise` in proportion to `weights` (exact fractions, no floats). Each part is floored
    and the paise left over go one at a time to the largest remainders (earliest month on a tie), so the
    parts always sum to the total."""
    if not weights or any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError("weights must be non-negative and not all zero")
    whole = sum(weights)
    exact = [Fraction(total_paise) * w / whole for w in weights]
    parts = [int(x) for x in exact]  # floor: the total and weights are non-negative
    left = total_paise - sum(parts)
    order = sorted(range(len(exact)), key=lambda i: (-(exact[i] - parts[i]), i))
    for i in order[:left]:
        parts[i] += 1
    return parts


def step_weights(months: Sequence[int], steps: Sequence[tuple[int, int, int]]) -> list[Fraction]:
    """Growing shares: the first month weighs 1 and each next month weighs the one before x (1 + step),
    where `step` (basis points) is that of the segment `(from, until, step_bp)` the month falls in (no
    segment = no growth). `from`/`until` are calendar months, compared in FY order."""
    pos = {m: i for i, m in enumerate(FY_ORDER)}
    out: list[Fraction] = []
    for i, m in enumerate(months):
        if i == 0:
            out.append(Fraction(1))
            continue
        bp = next((s for a, b, s in steps if pos[a] <= pos[m] <= pos[b]), 0)
        out.append(out[-1] * Fraction(BASIS_POINTS + bp, BASIS_POINTS))
    return out


def spread(
    total_paise: int,
    months: Sequence[int],
    kind: str,
    *,
    amounts: Sequence[int] | None = None,
    shares_bp: Sequence[int] | None = None,
    steps: Sequence[tuple[int, int, int]] | None = None,
) -> list[int]:
    """The paise each of `months` gets out of `total_paise` (same order, summing to the total):
    `one`/`equal` evenly, `custom` the given amounts (must sum to the total), `shares` by % shares in
    basis points (must sum to 100%), `step` in growing shares (`step_weights`)."""
    if kind not in PLAN_KINDS:
        raise ValueError(f"unknown plan {kind!r}")
    if not months:
        raise ValueError("no months to spread over")
    if kind == "one" and len(months) != 1:
        raise ValueError("a one-month change takes exactly one month")
    if kind in ("one", "equal"):
        return even_split(total_paise, len(months))
    if kind == "custom":
        if amounts is None or len(amounts) != len(months):
            raise ValueError("give one amount per month")
        if any(a < 0 for a in amounts) or sum(amounts) != total_paise:
            raise ValueError("the monthly amounts must add up to the total")
        return list(amounts)
    if kind == "shares":
        if shares_bp is None or len(shares_bp) != len(months):
            raise ValueError("give one share per month")
        if any(s < 0 for s in shares_bp) or sum(shares_bp) != BASIS_POINTS:
            raise ValueError("the shares must add up to 100%")
        return by_weights(total_paise, [Fraction(s) for s in shares_bp])
    return by_weights(total_paise, step_weights(months, steps or []))
