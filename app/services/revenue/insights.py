"""Ported from copilot services/insights.py (user's own code), workspace-scoped for Purser.

The client-income dashboard, for one FY: every figure is summed here from the stored rows (paise)."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.services.revenue import invoices as inv_svc
from app.services.revenue.core import Rev
from app.services.revenue.fiscal import fy_months, month_label

AGE_BUCKETS = ("Not due", "1-30 days", "31-60 days", "61-90 days", "90+ days")


@dataclass
class Kpis:
    projection: int = 0  # every invoice of the FY, INR
    received: int = 0  # money in
    outstanding: int = 0  # sent, not yet received
    overdue: int = 0  # outstanding past its due date
    to_raise: int = 0  # not invoiced yet
    fx_gain: int = 0  # received - total, on paid invoices
    overdue_count: int = 0
    to_raise_due_count: int = 0  # to raise for this month or earlier


@dataclass
class Month:
    label: str
    paid: int = 0
    sent: int = 0
    to_raise: int = 0


@dataclass
class ClientLine:
    client_id: int
    name: str
    projection: int = 0
    received: int = 0
    outstanding: int = 0
    overdue: int = 0


@dataclass
class Exposure:
    currency: str
    amount_minor: int = 0  # unpaid, in the currency
    paise: int = 0  # the same at the rows' rates


@dataclass
class Due:
    invoice_id: int
    label: str
    due_on: date
    outstanding: int
    days: int  # negative: overdue by that many days
    ref: str | None = None


@dataclass
class Insights:
    fy: str
    kpis: Kpis
    months: list[Month]
    clients: list[ClientLine]
    ageing: list[tuple[str, int]]
    exposure: list[Exposure]
    upcoming: list[Due] = field(default_factory=list)


def age_bucket(days_past_due: int) -> str:
    if days_past_due <= 0:
        return AGE_BUCKETS[0]
    if days_past_due <= 30:
        return AGE_BUCKETS[1]
    if days_past_due <= 60:
        return AGE_BUCKETS[2]
    if days_past_due <= 90:
        return AGE_BUCKETS[3]
    return AGE_BUCKETS[4]


def build(
    session: Session,
    rv: Rev,
    fy: str,
    months: list[tuple[int, int]] | None = None,
    *,
    client_id: int | None = None,
) -> Insights:
    """`months`: a period of the FY (a quarter, one month); every figure counts only those months.
    `client_id`: one client's figures only (a chat answer's tab)."""
    months = months or fy_months(fy)
    position = {ym: i for i, ym in enumerate(months)}
    k = Kpis()
    per_month = [Month(month_label(y, m)) for y, m in months]
    today = rv.today
    per_client: dict[int, ClientLine] = {}
    ageing: dict[str, int] = defaultdict(int)
    exposure: dict[str, Exposure] = {}
    upcoming: list[Due] = []
    this_month = (today.year, today.month)
    for inv in inv_svc.list_invoices(session, rv, months=months, client_id=client_id):
        got = inv_svc.received_paise(inv)
        left = inv_svc.remaining_paise(inv)
        line = per_client.setdefault(inv.customer_party_id, ClientLine(inv.customer_party_id, inv.client.name))
        bucket = per_month[position[(inv.year, inv.month)]]
        billed = inv_svc.billed_paise(inv)
        k.projection += billed
        line.projection += billed
        k.received += got
        line.received += got
        if inv.status in inv_svc.CLOSED:  # written off / merged: only what came in counts
            bucket.paid += got
            continue
        if inv.status == "paid":
            k.fx_gain += inv_svc.fx_gain_paise(inv)
            bucket.paid += billed
        elif inv.status == "to_raise":
            k.to_raise += inv.total_paise
            bucket.to_raise += inv.total_paise
            if (inv.year, inv.month) <= this_month:
                k.to_raise_due_count += 1
        else:  # sent / part paid
            bucket.paid += min(got, inv.total_paise)
            bucket.sent += left
            k.outstanding += left
            line.outstanding += left
            past = (today - inv.due_on).days if inv.due_on and left > 0 else 0
            ageing[age_bucket(past)] += left
            if past > 0 and left > 0:
                k.overdue += left
                k.overdue_count += 1
                line.overdue += left
            if inv.due_on and past >= -14:
                upcoming.append(Due(inv.id, inv_svc.label(inv), inv.due_on, left, -past, inv.ref))
        if inv.status != "paid" and inv.currency != "INR":
            e = exposure.setdefault(inv.currency, Exposure(inv.currency))
            share = inv.amount_minor if not got else inv.amount_minor * left // max(inv.total_paise, 1)
            e.amount_minor += share
            e.paise += left if inv.status != "to_raise" else inv.total_paise
    return Insights(
        fy=fy,
        kpis=k,
        months=per_month,
        clients=sorted(per_client.values(), key=lambda c: -c.projection),
        ageing=[(b, ageing.get(b, 0)) for b in AGE_BUCKETS],
        exposure=sorted(exposure.values(), key=lambda e: -e.paise),
        upcoming=sorted(upcoming, key=lambda d: d.due_on),
    )
