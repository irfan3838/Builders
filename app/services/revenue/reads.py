"""Read models shared by the agent tools and the UI endpoints (one source for what is spoken and shown)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.revenue import clients as cl
from app.services.revenue import cycles, fx_months, insights, reminders, suggest
from app.services.revenue import invoices as inv
from app.services.revenue.core import Rev
from app.services.revenue.fiscal import fy_months, month_label, period_label, period_months
from app.services.revenue.money import format_amount, format_inr

CARDS = ("all", "received", "outstanding", "overdue", "to_raise", "paid")


def _months(fy: str, period: str | None) -> list[tuple[int, int]]:
    return period_months(fy, period or "fy")


def overview(ss: Session, rv: Rev, fy: str, period: str | None = None, client_id: int | None = None) -> dict:
    """KPIs, per-client lines, ageing, foreign exposure, upcoming dues, and the client x month grid."""
    months = _months(fy, period)
    ins = insights.build(ss, rv, fy, months, client_id=client_id)
    k = ins.kpis
    rows = inv.list_invoices(ss, rv, months=months, client_id=client_id)
    grid: dict[int, dict] = {}
    for c in ([cl.client(ss, rv, client_id)] if client_id else cl.clients(ss, rv)):
        grid[c.id] = {"client_id": c.id, "client": c.name, "state": c.state, "cells": {}, "total_paise": 0}
    for i in rows:
        g = grid.setdefault(i.customer_party_id, {"client_id": i.customer_party_id, "client": i.client.name,
                                                   "state": i.client.state, "cells": {}, "total_paise": 0})
        key = f"{i.year}-{i.month:02d}"
        cell = g["cells"].setdefault(key, {"refs": [], "billed_paise": 0, "statuses": [], "overdue": False})
        cell["refs"].append(i.ref)
        cell["billed_paise"] += inv.billed_paise(i)
        cell["statuses"].append(i.status)
        cell["overdue"] = cell["overdue"] or inv.overdue_days(i, rv.today) > 0
        g["total_paise"] += inv.billed_paise(i)
    for g in grid.values():
        for cell in g["cells"].values():
            live = [s for s in cell["statuses"] if s not in inv.CLOSED] or cell["statuses"]
            cell["status"] = live[0] if len(set(live)) == 1 else "part_paid"
            cell["billed"] = format_inr(cell["billed_paise"], whole=True)
        g["total"] = format_inr(g["total_paise"], whole=True)
    return {
        "fy": fy, "period": period or "fy", "period_label": period_label(fy, period or "fy"), "as_of": rv.today.isoformat(),
        "kpis": {
            "projected": format_inr(k.projection), "received": format_inr(k.received),
            "outstanding": format_inr(k.outstanding), "overdue": format_inr(k.overdue), "to_raise": format_inr(k.to_raise),
            "fx_gain": format_inr(k.fx_gain), "overdue_count": k.overdue_count, "to_raise_due_count": k.to_raise_due_count,
            "paise": {"projected": k.projection, "received": k.received, "outstanding": k.outstanding, "overdue": k.overdue,
                      "to_raise": k.to_raise, "fx_gain": k.fx_gain},
        },
        "clients": [{"client": c.name, "projected": format_inr(c.projection), "received": format_inr(c.received),
                     "outstanding": format_inr(c.outstanding), "overdue": format_inr(c.overdue)} for c in ins.clients[:10]],
        "ageing": [{"bucket": b, "amount": format_inr(v), "paise": v} for b, v in ins.ageing],
        "exposure": [{"currency": e.currency, "amount": format_amount(e.amount_minor, e.currency), "inr": format_inr(e.paise)}
                     for e in ins.exposure],
        "upcoming": [{"ref": d.ref, "label": d.label, "due_on": d.due_on.isoformat(), "outstanding": format_inr(d.outstanding),
                      "days": d.days} for d in ins.upcoming[:8]],
        "months": [{"key": f"{y}-{m:02d}", "label": month_label(y, m)} for y, m in months],
        "grid": sorted(grid.values(), key=lambda g: g["client"].lower()),
        "definitions": "projected = billed (less balances moved on); received = INR credited, by invoice month; outstanding = sent or "
                       "part-paid not yet in; overdue = outstanding past due date; to raise = not invoiced yet",
    }


def invoice_list(ss: Session, rv: Rev, fy: str, period: str | None = None, card: str = "all", client_id: int | None = None,
                 limit: int = 25) -> dict:
    if card not in CARDS:
        card = "all"
    rows = inv.list_invoices(ss, rv, months=_months(fy, period), client_id=client_id)
    pick = {
        "all": lambda i: True,
        "received": lambda i: inv.received_paise(i) > 0,
        "outstanding": lambda i: inv.outstanding_paise(i) > 0,
        "overdue": lambda i: inv.overdue_days(i, rv.today) > 0,
        "to_raise": lambda i: i.status == "to_raise",
        "paid": lambda i: i.status == "paid",
    }[card]
    measure = {"received": inv.received_paise, "outstanding": inv.outstanding_paise, "overdue": inv.outstanding_paise,
               "to_raise": lambda i: i.total_paise}.get(card, inv.billed_paise)
    chosen = [i for i in rows if pick(i)]
    total = sum(measure(i) for i in chosen)
    return {"fy": fy, "period": period or "fy", "card": card, "count": len(chosen), "total": format_inr(total), "total_paise": total,
            "invoices": [inv.view(i, rv.today) for i in chosen[:limit]], "truncated": len(chosen) > limit}


def suggestions(ss: Session, rv: Rev, limit: int = 6) -> dict:
    out = suggest.build(ss, rv)
    return {"total": len(out), "as_of": rv.today.isoformat(),
            "items": [{"kind": s.kind, "priority": s.priority, "title": s.title, "detail": s.detail, "do": s.act, "ref": s.ref,
                       "alt": s.alt_act, "ask": s.ask} for s in out[:limit]],
            "open_reminders": [reminders.view(r, rv.today) for r in reminders.open_reminders(ss, rv)[:10]]}


def client_info(ss: Session, rv: Rev, name: str) -> dict:
    c = cl.resolve(ss, rv, name)
    cyc = cycles.current(ss, c.id, rv.today)
    rows = inv.list_invoices(ss, rv, client_id=c.id)
    return {"client_id": c.id, "client": c.name, "currency": c.currency or "INR", "state": cl.STATE_LABEL[c.state],
            "state_on": c.state_on.isoformat() if c.state_on else None, "archived": bool(c.archived_at),
            "cycle": cycles.summary(cyc) if cyc else None,
            "invoices": len(rows), "outstanding": format_inr(sum(inv.outstanding_paise(i) for i in rows)),
            "to_raise": format_inr(sum(i.total_paise for i in rows if i.status == "to_raise")),
            "open_refs": [i.ref for i in rows if i.status in inv.UNPAID][:12]}


def fx_view(ss: Session, rv: Rev, fy: str, currency: str | None = None, history: bool = False) -> dict:
    from app.services.revenue import fx

    g = fx_months.grid(ss, rv, fy)
    if currency:
        g["rows"] = [r for r in g["rows"] if r["currency"] == currency.upper()]
    quotes = {}
    for r in g["rows"]:
        try:
            q = fx.latest(ss, r["currency"])
            quotes[r["currency"]] = {"rate": f"{q.rate_micro / 1_000_000:.4f}", "date": q.rate_date.isoformat() if q.rate_date else None,
                                     "stale": q.stale, "source": "ECB (Frankfurter)"}
        except fx.RateUnavailable:
            quotes[r["currency"]] = None
    out = {**g, "months_keys": [f"{y}-{m:02d}" for y, m in fy_months(fy)], "ecb": quotes}
    if history:
        changes, _next = fx_months.history(ss, rv, currency=currency.upper() if currency else None, fy=fy, limit=10)
        out["history"] = [{"at": c.at.isoformat(), "kind": c.kind, "currency": c.currency, "what": c.what, "old": c.old, "new": c.new,
                           "repriced": c.repriced} for c in changes]
    return out
