"""Ported from copilot services/fx_months.py (user's own code), workspace-scoped for Munshi.

A currency's conversion rate per month, set by hand (Clients -> FX rates).

A rate carries forward: a month without its own rate takes the latest one set before it (into later FYs
too), until another month sets a new one. An invoice of a month in that currency is priced at that
month's rate (a rate typed on the invoice still wins; the ECB rate is the fallback when no rate was ever
set). Setting a rate is a preview first: the invoices of the months it sets, and of the following months
it now carries into (every later month to March: the newest change wins from its month on, so a later
month's older rate gives way), are listed; the unpaid ones are
ticked to reprice; paid and part-paid invoices keep their rate. Every change writes one `fx_month_set`
audit row; each repriced invoice writes its own `rate_changed` row.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditEvent as AuditLog
from app.models import FxMonth, Invoice
from app.models import Party as Client
from app.services.revenue.core import Rev, invalid, log
from app.services.revenue.fiscal import add_months, fy_months, fy_of, month_label
from app.services.revenue.money import CURRENCIES, INR, format_inr, rate_str, total_paise

MAX_MONTHS = 24
_YM = re.compile(r"^(\d{4})-(\d{2})$")
# the statuses whose rate may still change: once money has come in, the rate is history
REPRICEABLE = ("to_raise", "sent")


def parse_months(values: list[str]) -> list[tuple[int, int]]:
    """['2026-04', '2026-05'] -> [(2026, 4), (2026, 5)], sorted, no repeats."""
    out: set[tuple[int, int]] = set()
    for v in values:
        m = _YM.match(v.strip())
        if not m or not 1 <= int(m.group(2)) <= 12 or not 2000 <= int(m.group(1)) <= 2100:
            raise invalid(f"Not a month: {v} (use YYYY-MM)", field="months")
        out.add((int(m.group(1)), int(m.group(2))))
    if not out:
        raise invalid("Pick at least one month", field="months")
    if len(out) > MAX_MONTHS:
        raise invalid(f"At most {MAX_MONTHS} months at a time", field="months")
    return sorted(out)


def foreign(currency: str) -> str:
    code = currency.strip().upper()
    if code not in CURRENCIES:
        raise invalid(f"Unknown currency {currency}", field="currency")
    if code == INR:
        raise invalid("INR needs no conversion rate", field="currency")
    return code


def effective(session: Session, rv: Rev, currency: str, months: list[tuple[int, int]]) -> dict[tuple[int, int], int]:
    """Each month's rate in force (rate_micro): its own, else the latest set before it; months with no
    rate set on or before them are left out (they fall back to ECB)."""
    if not months or currency == INR:
        return {}
    hi = max(y * 100 + m for y, m in months)
    rows = list(
        session.scalars(
            select(FxMonth)
            .where(FxMonth.workspace_id == rv.ws, FxMonth.currency == currency, FxMonth.year * 100 + FxMonth.month <= hi)
            .order_by(FxMonth.year, FxMonth.month)
        )
    )
    out: dict[tuple[int, int], int] = {}
    for y, m in months:
        key = y * 100 + m
        found = None
        for r in rows:
            if r.year * 100 + r.month > key:
                break
            found = r.rate_micro
        if found is not None:
            out[(y, m)] = found
    return out


def carried_months(session: Session, rv: Rev, currency: str, months: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """The months, not among those being set, that will follow the new rate: every month after the
    first one set, to the end of its FY. The newest change wins from its month on: a later month's own
    rate, set before, gives way (it is cleared on apply)."""
    if not months:
        return []
    chosen = set(months)
    out: list[tuple[int, int]] = []
    for ym in sorted(chosen):
        fy_end = fy_months(fy_of(*ym))[-1]
        y, m = add_months(*ym, 1)
        while (y, m) <= fy_end and (y, m) not in chosen:
            if (y, m) not in out:
                out.append((y, m))
            y, m = add_months(y, m, 1)
    return sorted(out)


def rates(session: Session, rv: Rev, currency: str, months: list[tuple[int, int]]) -> dict[tuple[int, int], int]:
    """The month rates set for exactly these months (rate_micro), missing months left out."""
    if not months or currency == INR:
        return {}
    keys = [y * 100 + m for y, m in months]
    rows = session.scalars(
        select(FxMonth).where(FxMonth.workspace_id == rv.ws, FxMonth.currency == currency, (FxMonth.year * 100 + FxMonth.month).in_(keys))
    )
    return {(r.year, r.month): r.rate_micro for r in rows}


def grid(session: Session, rv: Rev, fy: str) -> dict[str, Any]:
    """Every currency in use (clients' and invoices') or with a month rate this FY, by month."""
    months = fy_months(fy)
    keys = [y * 100 + m for y, m in months]
    used = {c for c in session.scalars(select(Client.currency).where(
        Client.workspace_id == rv.ws, Client.kind == "customer", Client.archived_at.is_(None))) if c}
    invs = list(session.scalars(select(Invoice).where(Invoice.workspace_id == rv.ws, (Invoice.year * 100 + Invoice.month).in_(keys))))
    used |= {i.currency for i in invs}
    set_rows = list(session.scalars(select(FxMonth).where(FxMonth.workspace_id == rv.ws, (FxMonth.year * 100 + FxMonth.month).in_(keys))))
    used |= {r.currency for r in set_rows}
    used.discard(INR)
    by = {(r.currency, r.year, r.month): r for r in set_rows}
    count: dict[tuple[str, int, int], int] = {}
    for i in invs:
        count[(i.currency, i.year, i.month)] = count.get((i.currency, i.year, i.month), 0) + 1
    out = []
    for ccy in sorted(used):
        cells = []
        carried = effective(session, rv, ccy, months)
        for y, m in months:
            r = by.get((ccy, y, m))
            cells.append(
                {
                    "key": f"{y}-{m:02d}",
                    "label": month_label(y, m),
                    "rate": rate_str(r.rate_micro) if r else None,
                    # a month without its own rate follows the last one set before it
                    "carried": rate_str(carried[(y, m)]) if r is None and (y, m) in carried else None,
                    "set_at": r.set_at.isoformat() if r and r.set_at else None,
                    "invoices": count.get((ccy, y, m), 0),
                }
            )
        out.append({"currency": ccy, "cells": cells})
    return {"fy": fy, "months": [month_label(y, m) for y, m in months], "rows": out}


@dataclass
class Affected:
    invoice: Invoice
    new_total: int
    repriceable: bool
    ticked: bool  # ticked by default in the preview
    reason: str


@dataclass
class Preview:
    currency: str
    rate_micro: int
    months: list[tuple[int, int]]
    before: dict[tuple[int, int], int | None]
    invoices: list[Affected] = field(default_factory=list)
    carried: list[tuple[int, int]] = field(default_factory=list)  # following months that take the rate


def preview(session: Session, rv: Rev, currency: str, months: list[tuple[int, int]], rate_micro: int) -> Preview:
    currency = foreign(currency)
    carried = carried_months(session, rv, currency, months)
    keys = [y * 100 + m for y, m in [*months, *carried]]
    current = effective(session, rv, currency, months)
    invs = session.scalars(
        select(Invoice)
        .join(Client, Client.id == Invoice.customer_party_id)
        .options(selectinload(Invoice.client), selectinload(Invoice.payments))
        .where(Invoice.workspace_id == rv.ws, Invoice.currency == currency, (Invoice.year * 100 + Invoice.month).in_(keys))
        .order_by(Invoice.year, Invoice.month, Client.name)
    )
    out = Preview(currency, rate_micro, months, {ym: current.get(ym) for ym in months}, carried=carried)
    for inv in invs:
        new_total = total_paise(inv.amount_minor, inv.currency, rate_micro)
        if inv.status not in REPRICEABLE:
            reason = {
                "paid": "Paid: keeps its rate",
                "part_paid": "Part paid: keeps its rate",
                "written_off": "Written off: keeps its rate",
                "merged": "Merged: keeps its rate",
            }.get(inv.status, "Keeps its rate")
            out.invoices.append(Affected(inv, new_total, False, False, reason))
        elif inv.fx_rate_micro == rate_micro:
            out.invoices.append(Affected(inv, new_total, True, False, "Already at this rate"))
        elif inv.fx_source == "manual":  # an older typed rate follows the new one too (untick to keep it)
            out.invoices.append(Affected(inv, new_total, True, True, "Was typed on the invoice"))
        else:
            out.invoices.append(Affected(inv, new_total, True, True, ""))
    return out


def apply(
    session: Session,
    rv: Rev,
    currency: str,
    months: list[tuple[int, int]],
    rate_micro: int,
    reprice: list[int],
    *,
    actor_name: str = "",
) -> tuple[Preview, list[Invoice]]:
    """Set the rate for these months and reprice the ticked invoices (only ones the preview allows)."""
    from app.services.revenue import invoices as inv_svc  # invoices prices from here: import late

    plan = preview(session, rv, currency, months, rate_micro)
    allowed = {a.invoice.id: a for a in plan.invoices if a.repriceable}
    if any(i not in allowed for i in reprice):
        raise invalid(
            "Only unpaid invoices of these months (and the ones that follow them) in this currency can be "
            "repriced",
            field="reprice",
        )
    existing = {
        (r.year, r.month): r
        for r in session.scalars(
            select(FxMonth).where(
                FxMonth.workspace_id == rv.ws,
                FxMonth.currency == plan.currency,
                (FxMonth.year * 100 + FxMonth.month).in_([y * 100 + m for y, m in months]),
            )
        )
    }
    # the months that now follow the new rate drop their own (older) one
    for r in session.scalars(
        select(FxMonth).where(
            FxMonth.workspace_id == rv.ws,
            FxMonth.currency == plan.currency,
            (FxMonth.year * 100 + FxMonth.month).in_([y * 100 + m for y, m in plan.carried]),
        )
    ):
        plan.before.setdefault((r.year, r.month), r.rate_micro)
        session.delete(r)
    for y, m in months:
        row = existing.get((y, m))
        if row is None:
            session.add(
                FxMonth(workspace_id=rv.ws, currency=plan.currency, year=y, month=m, rate_micro=rate_micro, set_by=rv.actor_id)
            )
        else:
            row.rate_micro, row.set_by = rate_micro, rv.actor_id
    session.flush()
    repriced: list[Invoice] = []
    priced = inv_svc.Price(rate_micro, "month", None)
    for inv_id in dict.fromkeys(reprice):
        inv = allowed[inv_id].invoice
        inv_svc.update_invoice(session, rv, inv, priced=priced)
        repriced.append(inv)
    log(
        session,
        rv,
        "fx_month_set",
        record_type="fx_month",
        record_ref=plan.currency,
        before={
            "currency": plan.currency,
            "rates": {f"{y}-{m:02d}": rate_str(r) if r else None for (y, m), r in plan.before.items()},
        },
        after={
            "currency": plan.currency,
            "months": [f"{y}-{m:02d}" for y, m in months],
            "carried": [f"{y}-{m:02d}" for y, m in plan.carried],
            "rate": rate_str(rate_micro),
            "by": actor_name,
            "repriced": [
                {"ref": i.ref, "label": inv_svc.label(i), "total": format_inr(i.total_paise)} for i in repriced
            ],
        },
    )
    return plan, repriced


def set_from_invoice(session: Session, rv: Rev, inv: Invoice, rate_micro: int, *, actor_name: str = "") -> list[Invoice]:
    """A rate typed on an invoice is the currency's rate from that month on: it becomes the month's rate,
    and the unpaid invoices of that month and every month after it to March are repriced at it.
    Returns the invoices repriced."""
    months = [(inv.year, inv.month)]
    plan = preview(session, rv, inv.currency, months, rate_micro)
    ticked = [a.invoice.id for a in plan.invoices if a.ticked or (a.invoice.id == inv.id and a.repriceable)]
    _plan, repriced = apply(session, rv, inv.currency, months, rate_micro, ticked, actor_name=actor_name)
    return repriced


# --- history: every rate change, newest first ------------------------------------------------------

HISTORY_ACTIONS = tuple(f"revenue.{a}" for a in ("fx_month_set", "rate_changed", "invoice_updated", "status_changed"))
HISTORY_LIMIT = 50


@dataclass
class Change:
    id: int
    at: datetime
    actor_id: int | None
    by: str  # a name when one was recorded, else ""
    channel: str
    kind: str  # "month" (a month rate set) | "invoice" (one invoice's rate)
    currency: str
    what: str  # "Apr'26 to Jun'26" or "Ancora Health May'26"
    old: str  # "88.5000", "88.5000 / —" (several months), or "—"
    new: str
    repriced: list[str]  # invoice labels repriced with a month rate


def _months_text(keys: list[str]) -> str:
    ym = sorted((int(k[:4]), int(k[5:7])) for k in keys)
    runs: list[list[tuple[int, int]]] = []
    for y, m in ym:
        if runs and (y * 12 + m) - (runs[-1][-1][0] * 12 + runs[-1][-1][1]) == 1:
            runs[-1].append((y, m))
        else:
            runs.append([(y, m)])
    return ", ".join(month_label(*r[0]) + (f" to {month_label(*r[-1])}" if len(r) > 1 else "") for r in runs)


def history(
    session: Session,
    rv: Rev,
    *,
    currency: str | None = None,
    fy: str | None = None,
    after: tuple[datetime, int] | None = None,
    invoice_id: int | None = None,
    limit: int = HISTORY_LIMIT,
) -> tuple[list[Change], tuple[datetime, int] | None]:
    """Month rates set and invoice rates changed (by hand, by a month rate, refreshed or repriced on
    sending), newest first, keyset-paged on (at, id). `fy` keeps the changes to that FY's months."""
    fy_keys = {f"{y}-{m:02d}" for y, m in fy_months(fy)} if fy else None
    q = (
        select(AuditLog)
        .where(AuditLog.workspace_id == rv.ws, AuditLog.action.in_(HISTORY_ACTIONS))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    if invoice_id is not None:  # one invoice's own rate changes
        q = q.where(AuditLog.record_type == "invoice", AuditLog.record_id == invoice_id)
    if after is not None:
        q = q.where(or_(AuditLog.created_at < after[0], and_(AuditLog.created_at == after[0], AuditLog.id < after[1])))
    rows = list(session.scalars(q))
    names: dict[int, str] = {}
    for r in rows:
        if r.action == "revenue.fx_month_set" and r.actor_id and isinstance(r.after, dict) and r.after.get("by"):
            names.setdefault(r.actor_id, r.after["by"])
    inv_ids = {r.record_id for r in rows if r.action != "revenue.fx_month_set" and r.record_id}
    invs = {
        i.id: i
        for i in session.scalars(
            select(Invoice).options(selectinload(Invoice.client)).where(Invoice.workspace_id == rv.ws, Invoice.id.in_(inv_ids))
        )
    }
    out: list[Change] = []
    last: tuple[datetime, int] | None = None
    for r in rows:
        last = (r.created_at, r.id)
        before = r.before if isinstance(r.before, dict) else {}
        after_ = r.after if isinstance(r.after, dict) else {}
        channel = str(after_.get("channel", ""))
        if r.action == "revenue.fx_month_set":
            ccy = str(after_.get("currency", ""))
            months = [str(k) for k in after_.get("months", [])]
            if currency and ccy != currency:
                continue
            if fy_keys is not None and not fy_keys.intersection(months):
                continue
            olds = sorted({v or "—" for v in (before.get("rates") or {}).values()})
            out.append(
                Change(
                    r.id, r.created_at, r.actor_id, names.get(r.actor_id or 0, ""), channel, "month", ccy,
                    _months_text(months), " / ".join(olds) or "—", str(after_.get("rate", "")),
                    [str(x.get("label", "")) for x in after_.get("repriced", []) if isinstance(x, dict)],
                )
            )  # fmt: skip
        else:
            if before.get("rate") is None or before.get("rate") == after_.get("rate"):
                continue
            inv = invs.get(r.record_id)
            ccy = inv.currency if inv else ""
            if inv is None or ccy == INR or (currency and ccy != currency):
                continue
            if fy_keys is not None and str(after_.get("month")) not in fy_keys:
                continue
            out.append(
                Change(
                    r.id, r.created_at, r.actor_id, names.get(r.actor_id or 0, ""), channel, "invoice", ccy,
                    f"{after_.get('client') or inv.client.name} {month_label(inv.year, inv.month)}",
                    str(before.get("rate")), str(after_.get("rate")), [],
                )
            )  # fmt: skip
        if len(out) >= limit:
            return out, last
    return out, None
