"""Ported from copilot services/cycles.py (user's own code), workspace-scoped for Munshi.

A client's payment cycle: how much a month, billed every N months, in advance or in arrears, as one
combined invoice per period or a separate invoice per month (raised and due together).

A cycle row starts in a month and holds until the next row. Changing the cycle mid-year is a preview
first: from the month it takes effect, the invoices still "to raise" are rebuilt from the new schedule;
sent, part-paid and paid invoices are never touched, and the months they cover are skipped. Every
change writes one `cycle_set` audit row; the invoices go through `invoices.create_invoices` /
`delete_invoice`, so pricing (the month's FX rate) and their own audit rows stay on one path.
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClientCycle, Invoice
from app.models import Party as Client
from app.services.revenue.core import Rev, invalid, log
from app.services.revenue.fiscal import add_months, from_index, fy_months, fy_of, last_day, month_index, month_label
from app.services.revenue.money import CLIENT_CURRENCIES, format_amount, from_minor

CYCLE_TIMINGS = ("advance", "arrears")
CYCLE_MODES = ("combined", "monthly")

PERIOD_LABEL = {1: "Monthly", 2: "Every 2 months", 3: "Quarterly", 6: "Half-yearly", 12: "Yearly"}


def period_label(n: int) -> str:
    return PERIOD_LABEL.get(n, f"Every {n} months")


def describe(c: "ClientCycle | CycleIn") -> str:
    """'Quarterly · in advance · one combined invoice'"""
    if c.period_months == 1:
        per = "one invoice a month"
    elif c.mode == "combined":
        per = "one combined invoice"
    else:
        per = "monthly invoices, paid together"
    return f"{period_label(c.period_months)} · in {c.timing} · {per}"


REGULAR = "regular"  # the invoices a cycle plans (a balance or combined one is the user's own)


def ym_key(y: int, m: int) -> int:
    return y * 100 + m


def key_ym(key: int) -> tuple[int, int]:
    return key // 100, key % 100


def _later(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return a if month_index(*a) >= month_index(*b) else b


def _earlier(a: tuple[int, int], b: tuple[int, int]) -> tuple[int, int]:
    return a if month_index(*a) <= month_index(*b) else b


# --- what an invoice covers ------------------------------------------------------------------------


def combined(inv: Invoice) -> bool:
    """One invoice standing for several months (a combined cycle period)."""
    return bool(
        inv.period_from and (inv.period_months or 1) > 1 and inv.cycle and inv.cycle.mode == "combined"
    )


def covers(inv: Invoice) -> list[tuple[int, int]]:
    """The months an invoice stands for: its period for a combined invoice, else its own month."""
    if combined(inv):
        y, m = key_ym(inv.period_from or 0)
        return [add_months(y, m, i) for i in range(inv.period_months or 1)]
    return [(inv.year, inv.month)]


def period_end(inv: Invoice) -> tuple[int, int]:
    """The last month of the period an invoice belongs to (its own month when it has none)."""
    if inv.period_from and inv.period_months:
        y, m = key_ym(inv.period_from)
        return add_months(y, m, inv.period_months - 1)
    return inv.year, inv.month


def due_on(inv: Invoice) -> date:
    """An invoice is due on the last day of the period it covers."""
    return last_day(*period_end(inv))


def raise_on(inv: Invoice) -> date:
    """When an unraised invoice should go out: the day set on it (a balance dated ahead), else the
    period's first day (advance) or its last (arrears)."""
    if inv.raise_on is not None:
        return inv.raise_on
    if inv.cycle is not None and inv.cycle.timing == "arrears":
        return last_day(*period_end(inv))
    if inv.period_from:
        y, m = key_ym(inv.period_from)
        return date(y, m, 1)
    return date(inv.year, inv.month, 1)


def period_text(inv: Invoice) -> str:
    """ "Oct'26 to Dec'26" for an invoice of a several-month period, else ''."""
    if not inv.period_from or (inv.period_months or 1) <= 1:
        return ""
    y, m = key_ym(inv.period_from)
    return f"{month_label(y, m)} to {month_label(*period_end(inv))}"


def period_group(session: Session, inv: Invoice) -> list[Invoice]:
    """The invoices billed together with this one (the same cycle period), oldest first."""
    if not inv.period_from or not inv.cycle_id:
        return [inv]
    rows = session.scalars(
        select(Invoice)
        .where(
            Invoice.workspace_id == inv.workspace_id,
            Invoice.customer_party_id == inv.customer_party_id,
            Invoice.cycle_id == inv.cycle_id,
            Invoice.period_from == inv.period_from,
        )
        .order_by(Invoice.year, Invoice.month)
    )
    return list(rows) or [inv]


# --- the cycle in force ----------------------------------------------------------------------------


def cycles(session: Session, client_id: int) -> list[ClientCycle]:
    return list(
        session.scalars(
            select(ClientCycle)
            .where(ClientCycle.client_id == client_id)
            .order_by(ClientCycle.from_year, ClientCycle.from_month)
        )
    )


def active(session: Session, client_id: int, y: int, m: int) -> ClientCycle | None:
    """The cycle in force in a month: the latest one starting on or before it."""
    now = ym_key(y, m)
    found = [c for c in cycles(session, client_id) if ym_key(c.from_year, c.from_month) <= now]
    return found[-1] if found else None


def current(session: Session, client_id: int, today: date) -> ClientCycle | None:
    """The cycle in force today, else the first one still to start."""
    rows = cycles(session, client_id)
    now = ym_key(today.year, today.month)
    past = [c for c in rows if ym_key(c.from_year, c.from_month) <= now]
    return past[-1] if past else (rows[0] if rows else None)


# --- the schedule (pure) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Planned:
    year: int
    month: int
    amount_minor: int
    period_from: int  # yyyymm
    period_months: int

    @property
    def label(self) -> str:
        return month_label(self.year, self.month)

    @property
    def months(self) -> list[tuple[int, int]]:
        y, m = key_ym(self.period_from)
        return [add_months(y, m, i) for i in range(self.period_months)]


@dataclass(frozen=True)
class CycleIn:
    from_year: int
    from_month: int
    monthly_minor: int
    currency: str
    period_months: int = 1
    timing: str = "advance"
    mode: str = "combined"


def check(c: CycleIn) -> None:
    if not 1 <= c.period_months <= 12:
        raise invalid("A cycle is every 1 to 12 months", field="period_months")
    if c.timing not in CYCLE_TIMINGS:
        raise invalid("A cycle is billed in advance or in arrears", field="timing")
    if c.mode not in CYCLE_MODES:
        raise invalid("One combined invoice, or one invoice a month", field="mode")
    if c.monthly_minor <= 0:
        raise invalid("The amount a month must be more than zero", field="amount")
    if c.currency not in CLIENT_CURRENCIES:
        raise invalid("A client is billed in INR or USD", field="currency")
    if not 1 <= c.from_month <= 12 or not 2000 <= c.from_year <= 2100:
        raise invalid("Not a month", field="from")


def schedule(c: CycleIn | ClientCycle, start: tuple[int, int], end: tuple[int, int]) -> list[Planned]:
    """The invoices of every period that starts from `start` to `end` (inclusive). Periods are counted
    from the cycle's first month, so a period that started before `start` is not split."""
    first = month_index(c.from_year, c.from_month)
    lo, hi = max(month_index(*start), first), month_index(*end)
    n = c.period_months
    p = first + ((lo - first) + n - 1) // n * n  # the first period starting on or after `lo`
    out: list[Planned] = []
    while p <= hi:
        key = ym_key(*from_index(p))
        if c.mode == "combined" or n == 1:
            y, m = from_index(p if c.timing == "advance" else p + n - 1)
            out.append(Planned(y, m, c.monthly_minor * n, key, n))
        else:
            out += [Planned(*from_index(p + i), c.monthly_minor, key, n) for i in range(n)]
        p += n
    return out


def fy_end(y: int, m: int) -> tuple[int, int]:
    return fy_months(fy_of(y, m))[-1]


def _clashes(p: Planned, mode: str, taken: set[tuple[int, int]], covered: set[tuple[int, int]]) -> bool:
    """A planned row lands on a month an invoice already has, or (combined) its period overlaps one."""
    months = p.months if mode == "combined" else [(p.year, p.month)]
    return (p.year, p.month) in taken or any(ym in covered for ym in months)


# --- a change: preview, then apply -----------------------------------------------------------------


@dataclass
class ChangePlan:
    client: Client
    cycle: CycleIn
    until: tuple[int, int]
    remove: list[Invoice] = field(default_factory=list)  # still to raise: replaced
    keep: list[Invoice] = field(default_factory=list)  # raised or paid from this month on: untouched
    create: list[Planned] = field(default_factory=list)
    skipped: list[Planned] = field(default_factory=list)  # a month an invoice kept already covers
    replaces: list[ClientCycle] = field(default_factory=list)  # cycles from this month on, superseded


def preview(session: Session, client: Client, c: CycleIn) -> ChangePlan:
    check(c)
    start = (c.from_year, c.from_month)
    start_i = month_index(*start)
    # only the regular invoices follow the cycle: a balance or combined invoice is the user's own
    rows = _regular(session, client.id)
    later = sorted((i for i in rows if month_index(i.year, i.month) >= start_i), key=_order)
    remove = [i for i in later if i.status == "to_raise"]
    kept_all = [i for i in rows if i.status != "to_raise"]
    until = fy_end(*start)
    for i in remove:  # rows already planned further ahead are rebuilt too
        until = _later(until, fy_end(i.year, i.month))
    covered = {ym for i in kept_all for ym in covers(i)}
    taken = {(i.year, i.month) for i in kept_all}
    plan = ChangePlan(client, c, until, remove=remove, keep=[i for i in later if i.status != "to_raise"])
    for p in schedule(c, start, until):
        (plan.skipped if _clashes(p, c.mode, taken, covered) else plan.create).append(p)
    plan.replaces = [
        r for r in cycles(session, client.id) if ym_key(r.from_year, r.from_month) >= ym_key(*start)
    ]
    return plan


def _regular(session: Session, client_id: int) -> list[Invoice]:
    q = select(Invoice).where(Invoice.customer_party_id == client_id, Invoice.kind == REGULAR)
    return list(session.scalars(q))


def _order(i: Invoice) -> tuple[int, int]:
    return i.year, i.month


def apply(session: Session, rv: Rev, client: Client, c: CycleIn) -> tuple[ChangePlan, ClientCycle]:
    from app.services.revenue import invoices as inv_svc  # invoices imports this module: import late

    plan = preview(session, client, c)
    before = [_snap(r) for r in cycles(session, client.id)]
    removed = [inv_svc.label(i) for i in plan.remove]
    for inv in plan.remove:
        inv_svc.delete_invoice(session, rv, inv)
    for r in plan.replaces:
        session.delete(r)
    session.flush()
    row = ClientCycle(
        workspace_id=rv.ws,
        client_id=client.id,
        from_year=c.from_year,
        from_month=c.from_month,
        monthly_minor=c.monthly_minor,
        currency=c.currency,
        period_months=c.period_months,
        timing=c.timing,
        mode=c.mode,
        created_by=rv.actor_id,
    )
    session.add(row)
    client.currency = c.currency
    session.flush()
    _create(session, rv, client, row, plan.create)
    log(
        session,
        rv,
        "cycle_set",
        record_type="client",
        record_id=client.id,
        record_ref=client.name,
        before={"cycles": before},
        after={"cycle": _snap(row), "removed": removed, "created": [p.label for p in plan.create]},
    )
    return plan, row


def _create(session: Session, rv: Rev, client: Client, cycle: ClientCycle, planned: list[Planned]) -> list[Invoice]:
    from app.services.revenue import invoices as inv_svc

    out: list[Invoice] = []
    for i in range(0, len(planned), 24):
        chunk = planned[i : i + 24]
        out += inv_svc.create_invoices(
            session,
            rv,
            client=client,
            months=[(p.year, p.month) for p in chunk],
            amount_minor=[p.amount_minor for p in chunk],
            currency=cycle.currency,
            priced=inv_svc.price(session, rv, cycle.currency),
            periods=[(p.period_from, p.period_months) for p in chunk],
            cycle_id=cycle.id,
        )
    return out


def plan_fy(session: Session, rv: Rev, client: Client, fy: str) -> list[Invoice]:
    """Fill an FY from the cycles in force: each cycle's periods that start in the FY, skipping months
    an invoice already has or covers."""
    months = fy_months(fy)
    rows = cycles(session, client.id)
    have = _regular(session, client.id)
    covered = {ym for i in have for ym in covers(i)}
    taken = {(i.year, i.month) for i in have}
    out: list[Invoice] = []
    for k, cyc in enumerate(rows):
        start = _later(months[0], (cyc.from_year, cyc.from_month))
        stop = months[-1]
        if k + 1 < len(rows):
            stop = _earlier(stop, add_months(rows[k + 1].from_year, rows[k + 1].from_month, -1))
        if month_index(*start) > month_index(*stop):
            continue
        todo = [p for p in schedule(cyc, start, stop) if not _clashes(p, cyc.mode, taken, covered)]
        out += _create(session, rv, client, cyc, todo)
    return out


def needs_plan(session: Session, client: Client, fy: str) -> bool:
    """A cycle runs into this FY but none of the FY's months has an invoice yet."""
    months = fy_months(fy)
    rows = cycles(session, client.id)
    if not rows or ym_key(rows[0].from_year, rows[0].from_month) > ym_key(*months[-1]):
        return False
    keys = [ym_key(y, m) for y, m in months]
    has = session.scalars(
        select(Invoice.id).where(
            Invoice.customer_party_id == client.id, (Invoice.year * 100 + Invoice.month).in_(keys)
        )
    ).first()
    return has is None


def _snap(c: ClientCycle) -> dict[str, object]:
    return {
        "from": f"{c.from_year}-{c.from_month:02d}",
        "amount": from_minor(c.monthly_minor, c.currency),
        "currency": c.currency,
        "every": c.period_months,
        "timing": c.timing,
        "mode": c.mode,
    }


def summary(c: ClientCycle | CycleIn) -> str:
    """'$1,750.00 a month · Quarterly · in advance · one combined invoice, from Oct'26'"""
    return (
        f"{format_amount(c.monthly_minor, c.currency)} a month · {describe(c)}, "
        f"from {month_label(c.from_year, c.from_month)}"
    )
