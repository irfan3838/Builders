"""Monthly budget: base, adjusted, actual, remaining, status, pacing, changes, month close, trend
recommendations and forecasts. Async, workspace-scoped, over the same append-only ledger as budget.py.

- Adjusted budget of a month = SUM(allocation movements with that fiscal_month).
- Base budget = the opening allocation only. Actual = committed + spent (approved spend; settlement
  only moves money between those two buckets, so it never changes the actual).
- A closed month (budget_periods.closed_at) keeps its frozen actual and status; nothing may change it.
- The maths (status bands, pacing, forecast, projection, distribution, trend + plan) is the owner's
  copilot code, ported unchanged into app/services/budgeting/.
"""

from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import FORBIDDEN, INVALID_STATE, NOT_FOUND, VALIDATION, DomainError
from app.models import AuditEvent, BudgetLine, BudgetMovement, BudgetPeriod
from app.money import format_inr
from app.services import audit, budget
from app.services.budgeting import distribution, forecast, pacing, projection
from app.services.budgeting import recommend as rec
from app.services.budgeting.status import compute_status

BASE_KINDS = ("opening_allocation",)
CHANGE_KINDS = ("transfer", "top_up", "reduce")
VARIANCE_REASONS = ("vendor_price_change", "unplanned_one_off", "delayed_project_or_hiring", "scope_expansion", "other")
SPLITS = ("one", "equal", "custom", "shares")


# ------------------------------------------------------------------ calendar helpers

def fy_of(d: date) -> str:
    start = d.year if d.month >= 4 else d.year - 1
    return f"FY{start}-{(start + 1) % 100:02d}"


def fy_months(fy: str) -> list[date]:
    start = int(fy[2:6])
    return [date(start + (1 if m < 4 else 0), m, 1) for m in (4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3)]


def label(m: date) -> str:
    return m.strftime("%b %Y")


def short(m: date) -> str:
    return f"{calendar.month_abbr[m.month]}'{m.year % 100:02d}"


_MONTH_WORDS = {name.lower(): i for i, name in enumerate(calendar.month_name) if name}
_MONTH_WORDS.update({name.lower(): i for i, name in enumerate(calendar.month_abbr) if name})
_MONTH_WORDS.update({"sept": 9, "जनवरी": 1, "फरवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6, "जुलाई": 7,
                     "अगस्त": 8, "सितंबर": 9, "अक्टूबर": 10, "नवंबर": 11, "दिसंबर": 12})


def parse_month(text: str | None, today: date) -> date:
    """'2026-12', 'December', 'dec 2026', 'दिसंबर' -> first of that month; a bare month name means the
    one inside the current FY. None means the current month."""
    if not text:
        return today.replace(day=1)
    t = text.strip().lower().replace(",", " ")
    try:
        y, m = t.split("-")[:2]
        return date(int(y), int(m), 1)
    except (ValueError, TypeError):
        pass
    parts = t.split()
    m = _MONTH_WORDS.get(parts[0]) if parts else None
    if m is None:
        raise DomainError(VALIDATION, f"Could not read the month '{text}'. Use YYYY-MM, e.g. 2026-12.")
    if len(parts) > 1 and parts[1].isdigit():
        return date(int(parts[1]), m, 1)
    fy = fy_of(today)
    return next(d for d in fy_months(fy) if d.month == m)


def _pacing_day(m: date, today: date) -> tuple[int, int]:
    days = pacing.days_in_month(m)
    cur = today.replace(day=1)
    if m < cur:
        return days, days
    if m > cur:
        return 0, days
    return today.day, days


# ------------------------------------------------------------------ reading the grid

@dataclass
class Cell:
    line_id: int
    category: str
    department: str
    month: date
    base: int
    adjusted: int
    actual: int
    remaining: int
    used_pct: float | None
    status: str
    closed: bool
    source: str  # ledger | imported_snapshot
    when: str  # past | current | future
    pacing: dict | None = None
    variance_reason: str | None = None

    def view(self) -> dict:
        out = {"category": self.category, "month": label(self.month), "base": format_inr(self.base),
               "budget": format_inr(self.adjusted), "spent": format_inr(self.actual), "remaining": format_inr(self.remaining),
               "used_pct": self.used_pct, "status": self.status, "closed": self.closed, "when": self.when}
        if self.source == "imported_snapshot":
            out["source"] = "imported historical snapshot (synthetic)"
        if self.pacing:
            out["pacing"] = self.pacing
        if self.variance_reason:
            out["variance_reason"] = self.variance_reason
        return out


async def lines(s: AsyncSession, ws: int, category: str | None = None) -> list[BudgetLine]:
    if category:
        return [await budget.get_line(s, ws, category=category)]
    return list((await s.execute(select(BudgetLine).where(BudgetLine.workspace_id == ws).order_by(BudgetLine.category))).scalars())


async def grid(s: AsyncSession, actor: Actor, today: date, *, category: str | None = None,
               months: list[date] | None = None) -> list[Cell]:
    """Every (line, month) cell of the FY of `today` (or the given months), category order then month order."""
    ws = actor.workspace_id
    ls = await lines(s, ws, category)
    months = months or fy_months(fy_of(today))
    ids = [ln.id for ln in ls]
    m = BudgetMovement
    rows = (await s.execute(
        select(m.line_id, m.fiscal_month,
               func.coalesce(func.sum(case((m.bucket == "allocation", m.amount_paise), else_=0)), 0),
               func.coalesce(func.sum(case(((m.bucket == "allocation") & m.kind.in_(BASE_KINDS), m.amount_paise), else_=0)), 0),
               func.coalesce(func.sum(case((m.bucket.in_(("committed", "spent")), m.amount_paise), else_=0)), 0))
        .where(m.workspace_id == ws, m.line_id.in_(ids), m.fiscal_month.in_(months))
        .group_by(m.line_id, m.fiscal_month))).all()
    led = {(r[0], r[1]): (int(r[2]), int(r[3]), int(r[4])) for r in rows}
    per = {(p.line_id, p.fiscal_month): p for p in (await s.execute(
        select(BudgetPeriod).where(BudgetPeriod.workspace_id == ws, BudgetPeriod.line_id.in_(ids),
                                   BudgetPeriod.fiscal_month.in_(months)))).scalars()}
    cur = today.replace(day=1)
    out = []
    for ln in ls:
        for mo in months:
            adjusted, base, actual = led.get((ln.id, mo), (0, 0, 0))
            p = per.get((ln.id, mo))
            closed = bool(p and p.closed_at)
            if closed:
                adjusted, actual = p.adjusted_paise or 0, p.actual_paise or 0
            status = p.status if closed and p.status else compute_status(adjusted, actual)
            when = "past" if mo < cur else "current" if mo == cur else "future"
            pc = None
            if when == "current":
                day, days = _pacing_day(mo, today)
                r = pacing.compute(actual, adjusted, day, days)
                pc = {"day": r.day, "days_in_month": r.days_in_month, "expected_pct": r.expected_pct, "actual_pct": r.actual_pct,
                      "velocity": r.velocity, "health": r.health, "alert": r.alert}
            out.append(Cell(ln.id, ln.category, ln.department, mo, base, adjusted, actual, adjusted - actual,
                            round(actual / adjusted * 100, 2) if adjusted > 0 else None, status, closed,
                            p.source if p else "ledger", when, pc, p.variance_reason if p else None))
    return out


def _sum_cells(cells: list[Cell]) -> dict:
    a, b, act = sum(c.adjusted for c in cells), sum(c.base for c in cells), sum(c.actual for c in cells)
    return {"base": format_inr(b), "budget": format_inr(a), "spent": format_inr(act), "remaining": format_inr(a - act),
            "used_pct": round(act / a * 100, 2) if a > 0 else None, "changed_from_base": format_inr(a - b)}


ALERT_WORDS = {"LIMIT_REACHED": "limit reached (100% or more used)", "APPROACHING_LIMIT": "approaching limit (90% or more)",
               "CRITICAL_BURN": "critical burn (80% used before day 15)"}


async def alerts(s: AsyncSession, actor: Actor, today: date) -> dict:
    """The budget bell: current-month pacing alerts, fast burners, months due for close, open recommendations."""
    cells = await grid(s, actor, today)
    cur = [c for c in cells if c.when == "current"]
    items = []
    for c in cur:
        p = c.pacing or {}
        if p.get("alert") or p.get("health") == pacing.HEALTH_HIGH_RISK:
            items.append({"category": c.category, "month": label(c.month), "alert": ALERT_WORDS.get(p.get("alert"), "spending fast"),
                          "spent": format_inr(c.actual), "budget": format_inr(c.adjusted), "remaining": format_inr(c.remaining),
                          "used_pct": p.get("actual_pct"), "month_elapsed_pct": p.get("expected_pct"), "velocity": p.get("velocity")})
    order = {"LIMIT_REACHED": 0, "APPROACHING_LIMIT": 1, "CRITICAL_BURN": 2}
    items.sort(key=lambda i: (order.get(next((k for k, v in ALERT_WORDS.items() if v == i["alert"]), ""), 9), i["category"]))
    due = sorted({c.month for c in cells if c.when == "past" and not c.closed and (c.adjusted or c.actual)})
    out = {"as_of": today.isoformat(), "alerts": items, "months_due_for_close": [label(m) for m in due]}
    if actor.is_approver:
        out["recommendations_open"] = len(await recommendations(s, actor))
    return out


# ------------------------------------------------------------------ changes: transfer / top-up / reduce

@dataclass
class Leg:
    line_id: int
    category: str
    month: date
    delta: int  # + receives, - gives
    before_budget: int
    before_remaining: int

    def view(self) -> dict:
        return {"category": self.category, "month": label(self.month), "change": format_inr(self.delta),
                "budget_before": format_inr(self.before_budget), "budget_after": format_inr(self.before_budget + self.delta),
                "remaining_before": format_inr(self.before_remaining), "remaining_after": format_inr(self.before_remaining + self.delta)}


@dataclass
class ChangePlan:
    kind: str
    amount: int
    legs: list[Leg]
    reason: str
    source: str | None
    dest: str | None
    months: list[date]
    annual_delta: int = field(default=0)


def _require_admin(actor: Actor, what: str) -> None:
    if not actor.is_approver:
        raise DomainError(FORBIDDEN, f"Only a finance approver or admin can {what}.")


async def plan_change(s: AsyncSession, actor: Actor, today: date, *, kind: str, amount_paise: int, months: list[str],
                      source: str | None = None, dest: str | None = None, reason: str = "",
                      split: str = "equal", amounts_paise: list[int] | None = None, shares_bp: list[int] | None = None) -> ChangePlan:
    _require_admin(actor, "change a budget")
    if kind not in CHANGE_KINDS:
        raise DomainError(VALIDATION, f"Unknown change '{kind}'. Use transfer, top_up or reduce.")
    if amount_paise <= 0:
        raise DomainError(VALIDATION, "The amount must be positive.")
    if not reason or not reason.strip():
        raise DomainError(VALIDATION, "Give a short reason for the change; it goes into the history.")
    need_src, need_dst = kind in ("transfer", "reduce"), kind in ("transfer", "top_up")
    if need_src != bool(source) or need_dst != bool(dest):
        raise DomainError(VALIDATION, {"transfer": "A transfer needs a source and a destination category.",
                                       "top_up": "A top-up needs only a destination category.",
                                       "reduce": "A reduction needs only a source category."}[kind])
    ms = [parse_month(x, today) for x in months] if months else [today.replace(day=1)]
    if len(set(ms)) != len(ms):
        raise DomainError(VALIDATION, "A month is listed twice.")
    ms.sort()
    fy = fy_of(ms[0])
    if any(fy_of(m) != fy for m in ms):
        raise DomainError(VALIDATION, "All months of one change must be in the same financial year.")
    if split not in SPLITS:
        raise DomainError(VALIDATION, f"Unknown split '{split}'.")
    split = "one" if len(ms) == 1 else ("equal" if split == "one" else split)
    try:
        parts = distribution.spread(amount_paise, [m.month for m in ms], split, amounts=amounts_paise, shares_bp=shares_bp)
    except ValueError as e:
        raise DomainError(VALIDATION, str(e)) from e
    src_line = await budget.get_line(s, actor.workspace_id, category=source) if source else None
    dst_line = await budget.get_line(s, actor.workspace_id, category=dest) if dest else None
    if src_line and dst_line and src_line.id == dst_line.id:
        raise DomainError(VALIDATION, "Source and destination are the same category for the same months.")
    ids = [ln.id for ln in (src_line, dst_line) if ln]
    cells = {(c.line_id, c.month): c for c in await grid(s, actor, today, months=ms) if c.line_id in ids}
    cur = today.replace(day=1)
    legs: list[Leg] = []
    for m, part in zip(ms, parts, strict=True):
        for ln, sign in ((src_line, -1), (dst_line, 1)):
            if ln is None:
                continue
            c = cells[(ln.id, m)]
            if c.closed:
                raise DomainError(INVALID_STATE, f"{label(m)} is closed for {ln.category}; a closed month cannot change.")
            if sign > 0 and m < cur:
                raise DomainError(VALIDATION, f"{label(m)} is in the past; a past month can only give money, not receive it.")
            if sign < 0 and part > c.remaining:
                raise DomainError(VALIDATION, f"{ln.category} has only {format_inr(max(0, c.remaining))} left in {label(m)}; "
                                  f"it cannot give {format_inr(part)}.", available=format_inr(max(0, c.remaining)))
            legs.append(Leg(ln.id, ln.category, m, sign * part, c.adjusted, c.remaining))
    annual = amount_paise if kind == "top_up" else -amount_paise if kind == "reduce" else 0
    return ChangePlan(kind, amount_paise, legs, reason.strip()[:200], src_line.category if src_line else None,
                      dst_line.category if dst_line else None, ms, annual)


def describe_change(p: ChangePlan) -> tuple[str, list[str], str]:
    when = ", ".join(label(m) for m in p.months)
    title = {"transfer": f"Move {format_inr(p.amount)} from {p.source} to {p.dest}",
             "top_up": f"Add {format_inr(p.amount)} to {p.dest}", "reduce": f"Take back {format_inr(p.amount)} from {p.source}"}[p.kind]
    lines = [f"{title} ({when})."]
    for leg in p.legs:
        lines.append(f"{leg.category} {label(leg.month)}: budget {format_inr(leg.before_budget)} → "
                     f"{format_inr(leg.before_budget + leg.delta)}; remaining {format_inr(leg.before_remaining)} → "
                     f"{format_inr(leg.before_remaining + leg.delta)}.")
    lines.append("The company's total budget is unchanged." if p.annual_delta == 0 else
                 f"The company's total budget {'grows' if p.annual_delta > 0 else 'shrinks'} by {format_inr(abs(p.annual_delta))}.")
    lines.append(f"Reason: {p.reason}")
    return title, lines, f"{title} for {when}. Shall I make this change?"


async def apply_change(s: AsyncSession, actor: Actor, p: ChangePlan, receipt_id: int) -> dict:
    kinds = {("transfer", -1): "budget_transfer_out", ("transfer", 1): "budget_transfer_in",
             ("top_up", 1): "budget_top_up", ("reduce", -1): "budget_reduction"}
    for leg in p.legs:
        await budget.post(s, actor.workspace_id, leg.line_id, "allocation", leg.delta, kinds[(p.kind, 1 if leg.delta > 0 else -1)],
                          source_type="budget_change", receipt_id=receipt_id, memo=p.reason, fiscal_month=leg.month)
    after = {"kind": p.kind, "amount_paise": p.amount, "source": p.source, "dest": p.dest, "reason": p.reason,
             "months": [m.isoformat() for m in p.months], "annual_delta_paise": p.annual_delta,
             "cells": [leg.view() for leg in p.legs]}
    await audit.record(s, actor, f"budget.{p.kind}", record_type="budget", record_ref=p.dest or p.source, after=after,
                       receipt_id=receipt_id)
    return after


# ------------------------------------------------------------------ month close, variance, carry-over

@dataclass
class CloseRow:
    line_id: int
    category: str
    adjusted: int
    actual: int
    status: str
    variance_reason: str | None
    variance_note: str | None
    carry: int  # paise carried into next month (0 = absorbed / nothing to carry)


async def plan_close(s: AsyncSession, actor: Actor, today: date, month: str, *, variances: dict[str, tuple[str, str | None]],
                     carry_over: list[str]) -> tuple[date, date | None, list[CloseRow]]:
    _require_admin(actor, "close a month")
    m = parse_month(month, today)
    if m >= today.replace(day=1):
        raise DomainError(VALIDATION, f"{label(m)} has not ended yet; only a finished month can be closed.")
    cells = await grid(s, actor, today, months=[m])
    if any(c.closed for c in cells):
        raise DomainError(INVALID_STATE, f"{label(m)} is already closed.")
    names = {c.category.lower(): c for c in cells}
    for cat in list(variances) + list(carry_over):
        if cat.strip().lower() not in names:
            raise DomainError(NOT_FOUND, f"No budget line '{cat}'.", known_categories=sorted(c.category for c in cells))
    for cat, (reason, _note) in variances.items():
        if reason not in VARIANCE_REASONS:
            raise DomainError(VALIDATION, f"Variance reason for {cat} must be one of {', '.join(VARIANCE_REASONS)}.")
    months = fy_months(fy_of(m))
    nxt = months[months.index(m) + 1] if months.index(m) + 1 < len(months) else None
    carry = {c.strip().lower() for c in carry_over}
    rows = []
    for c in cells:
        key = c.category.lower()
        amount = 0
        if key in carry:
            if c.status != "UNDERUSED" or c.remaining <= 0:
                raise DomainError(VALIDATION, f"{c.category} is {c.status.lower().replace('_', ' ')} in {label(m)}; "
                                  "only an under-used month's surplus can be carried over.")
            if nxt is None:
                raise DomainError(VALIDATION, "March is the last month of the financial year; there is no next month to carry into.")
            amount = c.remaining
        v = next(((r, n) for k, (r, n) in variances.items() if k.strip().lower() == key), (None, None))
        rows.append(CloseRow(c.line_id, c.category, c.adjusted, c.actual, c.status, v[0], (v[1] or None), amount))
    return m, nxt, rows


async def apply_close(s: AsyncSession, actor: Actor, m: date, nxt: date | None, rows: list[CloseRow], receipt_id: int | None,
                      *, source: str = "ledger") -> dict:
    now = datetime.now(UTC)
    existing = {p.line_id: p for p in (await s.execute(
        select(BudgetPeriod).where(BudgetPeriod.workspace_id == actor.workspace_id, BudgetPeriod.fiscal_month == m)
        .with_for_update())).scalars()}
    if any(p.closed_at for p in existing.values()):
        raise DomainError(INVALID_STATE, f"{label(m)} is already closed.")
    for r in rows:
        p = existing.get(r.line_id) or BudgetPeriod(workspace_id=actor.workspace_id, line_id=r.line_id, fiscal_month=m)
        p.closed_at, p.closed_by, p.adjusted_paise, p.actual_paise, p.status = now, actor.user_id, r.adjusted, r.actual, r.status
        p.source, p.variance_reason, p.variance_note, p.receipt_id = source, r.variance_reason, r.variance_note, receipt_id
        p.surplus_action = "carried" if r.carry else ("absorbed" if r.status == "UNDERUSED" else None)
        s.add(p)
        if r.carry and nxt:
            memo = f"Surplus carried over from {label(m)}"
            await budget.post(s, actor.workspace_id, r.line_id, "allocation", -r.carry, "rollover_out", source_type="budget_close",
                              receipt_id=receipt_id, memo=memo, fiscal_month=m)
            await budget.post(s, actor.workspace_id, r.line_id, "allocation", r.carry, "rollover_in", source_type="budget_close",
                              receipt_id=receipt_id, memo=memo, fiscal_month=nxt)
    after = {"month": m.isoformat(), "rows": [{**asdict(r), "adjusted": format_inr(r.adjusted), "actual": format_inr(r.actual),
                                               "carry": format_inr(r.carry)} for r in rows]}
    await audit.record(s, actor, "budget.close_month", record_type="budget", record_ref=label(m), after=after, receipt_id=receipt_id)
    await s.flush()
    return after


# ------------------------------------------------------------------ recommendations

async def recommendations(s: AsyncSession, actor: Actor) -> list[rec.Recommendation]:
    ws = actor.workspace_id
    q = (select(BudgetPeriod, BudgetLine).join(BudgetLine, BudgetLine.id == BudgetPeriod.line_id)
         .where(BudgetPeriod.workspace_id == ws, BudgetPeriod.closed_at.isnot(None)).order_by(BudgetPeriod.fiscal_month))
    hist: dict[int, tuple[str, list[rec.ClosedMonth]]] = {}
    for p, ln in (await s.execute(q)).all():
        hist.setdefault(ln.id, (ln.category, []))[1].append(
            rec.ClosedMonth(short(p.fiscal_month), p.adjusted_paise or 0, p.actual_paise or 0, p.status or "OPEN"))
    out = [r for lid, (cat, months) in sorted(hist.items(), key=lambda kv: kv[1][0]) if (r := rec.trend(lid, cat, months))]
    return out


async def still_to_do(s: AsyncSession, actor: Actor, target: date) -> list[rec.PlannedChange]:
    """The plan for `target`, without steps already applied for that month (same kind, source and destination,
    with a 'Recommendation' reason): applying it twice never doubles a change."""
    done = set()
    for ev in (await s.execute(select(AuditEvent).where(AuditEvent.workspace_id == actor.workspace_id,
                                                         AuditEvent.action.in_([f"budget.{k}" for k in CHANGE_KINDS])))).scalars():
        a = ev.after or {}
        if str(a.get("reason", "")).startswith(rec.REASON_PREFIX) and target.isoformat() in (a.get("months") or []):
            done.add((a.get("kind"), a.get("source"), a.get("dest")))
    return [p for p in rec.plan(await recommendations(s, actor)) if (p.kind, p.source, p.dest) not in done]


def default_target(today: date) -> date:
    """Recommendations act on the next month that can still receive money (the coming month; March stays in its FY)."""
    cur = today.replace(day=1)
    months = fy_months(fy_of(cur))
    i = months.index(cur)
    return months[i + 1] if i + 1 < len(months) else cur


# ------------------------------------------------------------------ forecasts and what-ifs

async def _series(s: AsyncSession, actor: Actor, today: date, category: str | None) -> tuple[list[date], list[int], list[int], int]:
    months = fy_months(fy_of(today))
    cells = await grid(s, actor, today, category=category, months=months)
    budgets, actuals = [0] * 12, [0] * 12
    for c in cells:
        i = months.index(c.month)
        budgets[i] += c.adjusted
        actuals[i] += c.actual
    return months, budgets, actuals, months.index(today.replace(day=1))


async def outlook(s: AsyncSession, actor: Actor, today: date, category: str | None) -> dict:
    months, budgets, actuals, cur = await _series(s, actor, today, category)
    day, days = _pacing_day(months[cur], today)
    mo = forecast.month_outlook(budgets[cur], actuals[cur], day, days)
    yr = forecast.year_outlook(budgets, actuals, cur, day, days)
    return {
        "scope": category or "all categories", "as_of": today.isoformat(),
        "this_month": {"month": label(months[cur]), "budget": format_inr(mo.allocated), "spent_so_far": format_inr(mo.spent),
                       "projected_month_end": format_inr(mo.predicted), "projected_remaining": format_inr(mo.allocated - mo.predicted),
                       "day": day, "days_in_month": days},
        "this_fy": {"budget": format_inr(yr.allocated), "spent_so_far": format_inr(yr.spent), "projected_year_end": format_inr(yr.predicted),
                    "projected_remaining": format_inr(yr.allocated - yr.predicted)},
        "method": "Month: spend so far × days in month ÷ days elapsed. Year: completed months + this month at its run rate "
                  "+ the average of up to 3 recent full months for each month still to come.",
    }


async def what_if(s: AsyncSession, actor: Actor, today: date, *, category: str | None, percent: float | None,
                  amount_paise: int | None, per_month: bool, start: str | None, end: str | None) -> dict:
    if not percent and not amount_paise:
        raise DomainError(VALIDATION, "Give a percentage change or an amount.")
    months, budgets, actuals, cur = await _series(s, actor, today, category)
    day, days = _pacing_day(months[cur], today)
    st = parse_month(start, today) if start else months[cur]
    en = parse_month(end, today) if end else months[-1]
    if fy_of(st) != fy_of(today) or fy_of(en) != fy_of(today):
        raise DomainError(VALIDATION, "A scenario stays inside the current financial year.")
    si, ei = max(months.index(st), cur), months.index(en)  # a window that starts in the past moves to now
    if ei < si:
        raise DomainError(VALIDATION, "The scenario window has no month left in this financial year.")
    change = projection.Change(si, ei, percent_bp=int(round((percent or 0) * 100)), amount=amount_paise or 0, per_month=per_month)
    pr = projection.project(budgets, actuals, cur, day, days, [change])
    runs = pr.runs_out
    return {
        "scope": category or "all categories", "as_of": today.isoformat(),
        "change": {"percent": percent, "amount": format_inr(amount_paise) if amount_paise else None, "per_month": per_month,
                   "from": label(months[si]), "to": label(months[ei]), "moved_to_now": months.index(st) < cur},
        "fy_budget": format_inr(pr.budget), "spent_so_far": format_inr(pr.spent),
        "projected_without_change": format_inr(pr.baseline), "projected_with_change": format_inr(pr.projected),
        "extra_cost" if pr.extra >= 0 else "saving": format_inr(abs(pr.extra)),
        "year_end_headroom": format_inr(pr.headroom), "needs_cover": pr.headroom < 0,
        "first_month_over_budget": label(months[runs]) if runs is not None else None,
        "pace_basis": f"average of the last {pr.pace_months} full month(s)" if pr.pace_months else "each future month's own budget",
        "months": [{"month": label(months[r.index]), "kind": "actual" if r.actual else "projected", "budget": format_inr(r.budget),
                    "spend": format_inr(r.changed), "fy_left_after": format_inr(r.left)} for r in pr.months],
        "note": "A scenario changes nothing. Moving money needs a confirmed budget change.",
    }


# ------------------------------------------------------------------ history

async def history(s: AsyncSession, actor: Actor, category: str | None = None, limit: int = 15) -> list[dict]:
    q = select(AuditEvent).where(AuditEvent.workspace_id == actor.workspace_id, AuditEvent.action.like("budget.%"))
    evs = (await s.execute(q.order_by(AuditEvent.id.desc()).limit(200))).scalars().all()
    out = []
    for e in evs:
        a = e.after or {}
        if category:
            cats = {a.get("source"), a.get("dest"), *(c.get("category") for c in a.get("cells", []) + a.get("rows", []))}
            if category.strip().lower() not in {str(c).lower() for c in cats if c}:
                continue
        out.append({"at": e.created_at.isoformat() if e.created_at else None, "action": e.action, "actor_id": e.actor_id,
                    "receipt_id": e.receipt_id, **{k: v for k, v in a.items() if k != "rows"},
                    **({"categories_closed": len(a["rows"])} if "rows" in a else {})})
        if len(out) >= limit:
            break
    return out
