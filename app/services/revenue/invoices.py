"""Customer invoices: create, send, pay, allocate, edit, delete, move a part payment's balance.

Ported from copilot services/invoices.py (the user's own module), adapted to Munshi: sync SQLAlchemy run via
`AsyncSession.run_sync`, every query scoped to the workspace, audit into `audit_events`, client = Party.
Totals are computed here from the amount and the rate, never taken as given. `paid_paise` on the invoice is a
cache of its payments, refreshed by `_cache` on every change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Invoice, InvoicePayment, Party
from app.services.revenue import cycles, fx, fx_months
from app.services.revenue.core import (
    BAD_STATUS,
    INVOICE_PAID,
    MONTH_TAKEN,
    NOTHING_LEFT,
    RATE_UNAVAILABLE,
    TEXT_MAX,
    Rev,
    conflict,
    invalid,
    log,
    not_found,
)
from app.services.revenue.fiscal import fy_of, month_label
from app.services.revenue.money import CURRENCIES, INR, MICRO, format_amount, format_inr, rate_str, share_minor, total_paise

UNPAID = ("to_raise", "sent", "part_paid")
STATUS_LABEL = {"to_raise": "To raise", "sent": "Sent", "part_paid": "Part paid", "paid": "Paid",
                "written_off": "Written off", "merged": "Merged"}
CLOSED = ("written_off", "merged")  # out of every money figure
MAX_MONTHS = 24


# --- pricing ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Price:
    rate_micro: int
    source: str  # ecb | manual | inr | month
    rate_date: date | None
    stale: bool = False

    def as_args(self) -> dict:
        return {"rate_micro": self.rate_micro, "source": self.source,
                "rate_date": self.rate_date.isoformat() if self.rate_date else None}

    @classmethod
    def from_args(cls, d: dict | None) -> Price | None:
        if not d:
            return None
        return cls(int(d["rate_micro"]), d["source"], date.fromisoformat(d["rate_date"]) if d.get("rate_date") else None)


def price(ss: Session, rv: Rev, currency: str, manual_rate_micro: int | None = None,
          months: list[tuple[int, int]] | None = None) -> Price:
    """INR is 1; a typed rate is manual; then the currency's month rate in force for the first month given;
    else the latest cached ECB quote."""
    if currency == INR:
        return Price(MICRO, "inr", None)
    if manual_rate_micro is not None:
        return Price(manual_rate_micro, "manual", None)
    if months:
        in_force = fx_months.effective(ss, rv, currency, months[:1])
        if months[0] in in_force:
            return Price(in_force[months[0]], "month", None)
    try:
        r = fx.latest(ss, currency)
    except fx.RateUnavailable as exc:
        raise invalid(str(exc), code=RATE_UNAVAILABLE, field="rate") from exc
    return Price(r.rate_micro, r.source, r.rate_date, r.stale)


# --- reading ---------------------------------------------------------------------------------------


def invoice(ss: Session, rv: Rev, invoice_id: int) -> Invoice:
    found = ss.get(Invoice, invoice_id)
    if found is None or found.workspace_id != rv.ws:
        raise not_found("No such invoice")
    return found


def by_ref(ss: Session, rv: Rev, ref: str) -> Invoice:
    r = (ref or "").strip().upper()
    if r.startswith("S") and r[1:].isdigit():
        return invoice(ss, rv, int(r[1:]))
    found = ss.scalars(select(Invoice).where(Invoice.workspace_id == rv.ws, Invoice.number == ref.strip())).first()
    if found is None:
        raise not_found(f"No invoice {ref}")
    return found


def received_paise(inv: Invoice) -> int:
    return sum(p.amount_paise for p in inv.payments)


def billed_paise(inv: Invoice) -> int:
    """Projection: total less a balance moved on (counted there). Merged: 0; written off: what came in."""
    if inv.status == "merged":
        return 0
    if inv.status == "written_off":
        return received_paise(inv)
    return inv.total_paise - inv.moved_paise


def remaining_paise(inv: Invoice) -> int:
    if inv.status in CLOSED:
        return 0
    return max(inv.total_paise - received_paise(inv) - inv.moved_paise, 0)


def outstanding_paise(inv: Invoice) -> int:
    """Sent for payment and not in: sent / part paid only (a draft is 'to raise', a settled short pay is 0)."""
    return remaining_paise(inv) if inv.status in ("sent", "part_paid") else 0


def overdue_days(inv: Invoice, today: date) -> int:
    if inv.status in ("sent", "part_paid") and inv.due_on and inv.due_on < today and remaining_paise(inv) > 0:
        return (today - inv.due_on).days
    return 0


def fx_gain_paise(inv: Invoice) -> int:
    return received_paise(inv) + inv.moved_paise - inv.total_paise if inv.status == "paid" else 0


def last_received_on(inv: Invoice) -> date | None:
    days = [p.received_on for p in inv.payments if p.received_on]
    return max(days) if days else None


def label(inv: Invoice) -> str:
    """'Acme Traders Oct'26' ('… balance' / '… combined' for those kinds)."""
    tail = "" if inv.kind == "regular" else f" {inv.kind}"
    return f"{inv.client.name} {month_label(inv.year, inv.month)}{tail}"


def snapshot(inv: Invoice) -> dict[str, Any]:
    return {
        "ref": inv.ref, "client": inv.client.name if inv.client else None, "month": f"{inv.year}-{inv.month:02d}",
        "amount": format_amount(inv.amount_minor, inv.currency), "rate": rate_str(inv.fx_rate_micro),
        "total": format_inr(inv.total_paise), "status": inv.status,
        "sent_on": inv.sent_on.isoformat() if inv.sent_on else None, "received": format_inr(received_paise(inv)),
        **({"notes": inv.notes} if inv.notes else {}),
        **({"kind": inv.kind} if inv.kind != "regular" else {}),
        **({"moved": format_inr(inv.moved_paise)} if inv.moved_paise else {}),
    }


def view(inv: Invoice, today: date) -> dict[str, Any]:
    """What a tool / card shows for one invoice (display strings + exact paise)."""
    od = overdue_days(inv, today)
    return {
        "ref": inv.ref, "number": inv.number, "client": inv.client.name, "client_id": inv.customer_party_id,
        "label": label(inv), "month": f"{inv.year}-{inv.month:02d}", "fy": fy_of(inv.year, inv.month),
        "kind": inv.kind, "status": inv.status, "status_label": STATUS_LABEL.get(inv.status, inv.status),
        "amount": format_amount(inv.amount_minor, inv.currency), "currency": inv.currency,
        "rate": rate_str(inv.fx_rate_micro) if inv.currency != INR else None, "fx_source": inv.fx_source,
        "fx_date": inv.fx_date.isoformat() if inv.fx_date else None,
        "total": format_inr(inv.total_paise), "total_paise": inv.total_paise,
        "received": format_inr(received_paise(inv)), "received_paise": received_paise(inv),
        "remaining": format_inr(remaining_paise(inv)), "remaining_paise": remaining_paise(inv),
        "sent_on": inv.sent_on.isoformat() if inv.sent_on else None,
        "due_on": inv.due_on.isoformat() if inv.due_on else None, "overdue_days": od,
        "period": cycles.period_text(inv) or None, "raise_on": cycles.raise_on(inv).isoformat() if inv.status == "to_raise" else None,
        "moved": format_inr(inv.moved_paise) if inv.moved_paise else None,
        "moved_to": inv.moved_to_id and f"S{inv.moved_to_id}", "notes": inv.notes or None,
        "payments": [{"amount": format_inr(p.amount_paise), "received_on": p.received_on.isoformat() if p.received_on else None}
                     for p in inv.payments],
    }


def list_invoices(ss: Session, rv: Rev, *, months: list[tuple[int, int]] | None = None, client_id: int | None = None,
                  statuses: list[str] | None = None, archived: bool = False) -> list[Invoice]:
    q = (select(Invoice).join(Party, Party.id == Invoice.customer_party_id)
         .options(selectinload(Invoice.payments), selectinload(Invoice.client), selectinload(Invoice.cycle))
         .where(Invoice.workspace_id == rv.ws, Party.workspace_id == rv.ws)
         .order_by(Invoice.year, Invoice.month, Party.name, Invoice.id))
    if months:
        q = q.where((Invoice.year * 100 + Invoice.month).in_([y * 100 + m for y, m in months]))
    if client_id:
        q = q.where(Invoice.customer_party_id == client_id)
    if statuses:
        q = q.where(Invoice.status.in_(statuses))
    if not archived and not client_id:
        q = q.where(Party.archived_at.is_(None))
    return list(ss.scalars(q))


# --- writing ---------------------------------------------------------------------------------------


def _cache(inv: Invoice) -> None:
    inv.paid_paise = received_paise(inv)


def _settle(inv: Invoice) -> None:
    """Receipts covering the total close it as paid."""
    if inv.payments and inv.status == "part_paid" and received_paise(inv) + inv.moved_paise >= inv.total_paise:
        inv.status = "paid"


def create_invoices(ss: Session, rv: Rev, *, client: Party, months: list[tuple[int, int]], amount_minor: int | list[int],
                    currency: str, priced: Price, notes: str = "", periods: list[tuple[int, int]] | None = None,
                    cycle_id: int | None = None, kind: str = "regular", raise_on: date | None = None) -> list[Invoice]:
    """One row per month (same amount each, or one amount per month), all starting 'to raise'. A month the
    client already has (regular) is refused. A month with its own rate takes it unless the rate was typed."""
    if not months:
        raise invalid("Pick at least one month", field="month")
    if len(set(months)) != len(months):
        raise invalid("Each month once", field="month")
    amounts = amount_minor if isinstance(amount_minor, list) else [amount_minor] * len(months)
    if len(amounts) != len(months):
        raise invalid("One amount per month", field="amount")
    if len(months) > MAX_MONTHS:
        raise invalid(f"At most {MAX_MONTHS} months at a time", field="until")
    if currency not in CURRENCIES:
        raise invalid(f"Unknown currency {currency}", field="currency")
    if any(a <= 0 for a in amounts):
        raise invalid("The amount must be more than zero", field="amount")
    if any(not (2000 <= y <= 2100 and 1 <= m <= 12) for y, m in months):
        raise invalid("Not a month", field="month")
    if kind == "regular":
        taken = set(ss.execute(select(Invoice.year, Invoice.month).where(
            Invoice.workspace_id == rv.ws, Invoice.customer_party_id == client.id, Invoice.kind == "regular")).tuples())
        clash = [month_label(y, m) for y, m in months if (y, m) in taken]
        if clash:
            raise conflict(f"{client.name} already has {', '.join(clash)}: change that invoice instead", MONTH_TAKEN)
    month_rates = fx_months.effective(ss, rv, currency, months) if priced.source in ("ecb", "month") else {}
    out = []
    spans = periods or [(0, 0)] * len(months)
    for (y, m), amount, (p_from, p_n) in zip(months, amounts, spans, strict=True):
        p = Price(month_rates[(y, m)], "month", None) if (y, m) in month_rates else priced
        inv = Invoice(
            workspace_id=rv.ws, customer_party_id=client.id, year=y, month=m, amount_minor=amount, currency=currency,
            fx_rate_micro=p.rate_micro, fx_source=p.source, fx_date=p.rate_date,
            amount_paise=total_paise(amount, currency, p.rate_micro), paid_paise=0, status="to_raise",
            notes=(notes or "")[:TEXT_MAX], period_from=p_from or None, period_months=p_n or None, cycle_id=cycle_id,
            kind=kind, raise_on=raise_on, moved_paise=0, created_by=rv.actor_id, updated_by=rv.actor_id, version=1,
        )
        inv.client = client
        ss.add(inv)
        out.append(inv)
    ss.flush()
    for inv in out:
        inv.ref = f"S{inv.id}"
    ss.flush()
    for inv in out:
        log(ss, rv, "invoice_created", record_type="invoice", record_id=inv.id, record_ref=inv.ref, after=snapshot(inv))
    return out


def update_invoice(ss: Session, rv: Rev, inv: Invoice, *, amount_minor: int | None = None, currency: str | None = None,
                   priced: Price | None = None, notes: str | None = None) -> Invoice:
    """Amount, currency, rate or notes. A paid invoice keeps its numbers (its receipts are history)."""
    before = snapshot(inv)
    if inv.status in CLOSED:
        raise conflict(f"{label(inv)} is {STATUS_LABEL[inv.status].lower()}", BAD_STATUS)
    money_change = amount_minor is not None or currency is not None or priced is not None
    if money_change and inv.status == "paid":
        raise conflict("A paid invoice keeps its amount and rate", INVOICE_PAID)
    if amount_minor is not None:
        if amount_minor <= 0:
            raise invalid("The amount must be more than zero", field="amount")
        inv.amount_minor = amount_minor
    if currency is not None:
        if currency not in CURRENCIES:
            raise invalid(f"Unknown currency {currency}", field="currency")
        if currency != inv.currency and priced is None:
            priced = price(ss, rv, currency, months=[(inv.year, inv.month)])
        inv.currency = currency
    if priced is not None:
        inv.fx_rate_micro, inv.fx_source, inv.fx_date = priced.rate_micro, priced.source, priced.rate_date
    if inv.currency == INR:
        inv.fx_rate_micro, inv.fx_source, inv.fx_date = MICRO, "inr", None
    inv.total_paise = total_paise(inv.amount_minor, inv.currency, inv.fx_rate_micro)
    if notes is not None:
        inv.notes = notes.strip()[:TEXT_MAX]
    inv.updated_by = rv.actor_id
    _settle(inv)
    ss.flush()
    after = snapshot(inv)
    if after != before:
        action = "rate_changed" if priced is not None and amount_minor is None else "invoice_updated"
        log(ss, rv, action, record_type="invoice", record_id=inv.id, record_ref=inv.ref, before=before, after=after)
    return inv


def refresh_rate(ss: Session, rv: Rev, inv: Invoice) -> Invoice:
    if inv.status not in ("to_raise", "sent"):
        raise conflict("Only an unpaid invoice takes a new rate", INVOICE_PAID)
    if inv.currency == INR:
        return inv
    return update_invoice(ss, rv, inv, priced=price(ss, rv, inv.currency, months=[(inv.year, inv.month)]))


def _reprice(ss: Session, inv: Invoice) -> None:
    try:
        r = fx.latest(ss, inv.currency)
    except fx.RateUnavailable:
        return
    if r.stale:
        return
    inv.fx_rate_micro, inv.fx_date = r.rate_micro, r.rate_date
    inv.total_paise = total_paise(inv.amount_minor, inv.currency, r.rate_micro)


def set_status(ss: Session, rv: Rev, inv: Invoice, status: str, *, on: date) -> Invoice:
    """to_raise <-> sent. Sending stamps the date, the due date (last day of the period it covers, never before
    the send day) and an invoice number; an ECB-estimated draft takes the fresh ECB quote."""
    before = snapshot(inv)
    if status == "sent":
        if inv.status not in ("to_raise", "sent"):
            raise conflict(f"{label(inv)} is already {STATUS_LABEL[inv.status].lower()}", BAD_STATUS)
        if inv.status == "to_raise" and inv.fx_source == "ecb":
            _reprice(ss, inv)
        inv.status, inv.sent_on = "sent", on
        inv.due_on = max(cycles.due_on(inv), on)
        if not inv.number:
            inv.number = f"INV-{on.year}-{inv.id:04d}"
    elif status == "to_raise":
        if inv.payments:
            raise conflict(f"{label(inv)} has payments recorded", BAD_STATUS)
        if inv.status != "sent":
            raise conflict(f"{label(inv)} is {STATUS_LABEL[inv.status].lower()}, not sent", BAD_STATUS)
        inv.status, inv.sent_on, inv.due_on = "to_raise", None, None
    else:
        raise invalid("Status is 'to_raise' or 'sent'; record a payment to mark it paid", field="status")
    inv.updated_by = rv.actor_id
    ss.flush()
    log(ss, rv, "status_changed", record_type="invoice", record_id=inv.id, record_ref=inv.ref, before=before, after=snapshot(inv))
    return inv


def record_payment(ss: Session, rv: Rev, inv: Invoice, *, amount_paise: int | None, received_on: date | None,
                   settled: bool) -> Invoice:
    """INR actually credited. None = what is left. `settled` closes it as paid even when the bank credited
    less or more than the total (the difference shows as FX gain/loss)."""
    if inv.status == "paid":
        raise conflict(f"{label(inv)} is already paid", INVOICE_PAID)
    if inv.status in CLOSED:
        raise conflict(f"{label(inv)} is {STATUS_LABEL[inv.status].lower()}", BAD_STATUS)
    amount = remaining_paise(inv) if amount_paise is None else amount_paise
    if amount <= 0:
        raise invalid("The amount received must be more than zero", field="amount")
    before = snapshot(inv)
    inv.payments.append(InvoicePayment(workspace_id=rv.ws, received_on=received_on, amount_paise=amount,
                                       created_by=rv.actor_id, receipt_id=rv.receipt_id))
    if inv.sent_on is None:  # paid without a recorded send: it was raised by the time it was paid
        inv.sent_on = received_on
        if not inv.number and received_on:
            inv.number = f"INV-{received_on.year}-{inv.id:04d}"
    inv.status = "paid" if settled else "part_paid"
    _settle(inv)
    _cache(inv)
    inv.updated_by = rv.actor_id
    ss.flush()
    log(ss, rv, "payment_recorded", record_type="invoice", record_id=inv.id, record_ref=inv.ref, before=before,
        after={**snapshot(inv), "credited": format_inr(amount)})
    return inv


@dataclass(frozen=True)
class Allocation:
    invoice: Invoice
    share_paise: int
    settles: bool


def plan_allocation(invs: list[Invoice], amount_paise: int | None, settled: bool) -> list[Allocation]:
    """One credit spread oldest first, each taking what it has left; the last takes the rest (a small FX
    difference). None = each paid what it has left. Pure: the preview and the confirm use the same plan."""
    todo = sorted((i for i in invs if i.status in UNPAID), key=lambda i: (i.year, i.month, i.id))
    if not todo:
        raise conflict("These invoices are already paid", INVOICE_PAID)
    if len({i.customer_party_id for i in todo}) > 1:
        raise invalid("One payment comes from one client", field="invoice_refs")
    if len(todo) > MAX_MONTHS:
        raise invalid(f"At most {MAX_MONTHS} invoices in one payment", field="invoice_refs")
    if amount_paise is None:
        return [Allocation(i, remaining_paise(i), True) for i in todo]
    if amount_paise <= 0:
        raise invalid("The amount received must be more than zero", field="amount")
    left, out = amount_paise, []
    for n, inv in enumerate(todo):
        last = n == len(todo) - 1
        share = left if last else min(remaining_paise(inv), left)
        if share <= 0:
            break
        left -= share
        out.append(Allocation(inv, share, settled or share >= remaining_paise(inv)))
    return out


def record_payments(ss: Session, rv: Rev, invs: list[Invoice], *, amount_paise: int | None, received_on: date | None,
                    settled: bool) -> list[Invoice]:
    return [record_payment(ss, rv, a.invoice, amount_paise=a.share_paise, received_on=received_on, settled=a.settles)
            for a in plan_allocation(invs, amount_paise, settled)]


CHECK_EVERY_DAYS = 7  # the "has it been paid?" check-in: a week after sending, then weekly


def check_due_on(inv: Invoice) -> date | None:
    if inv.status not in ("sent", "part_paid") or inv.sent_on is None:
        return None
    last = max(inv.sent_on, inv.checked_on) if inv.checked_on else inv.sent_on
    return last + timedelta(days=CHECK_EVERY_DAYS)


def not_paid_yet(ss: Session, rv: Rev, inv: Invoice, *, on: date) -> Invoice:
    """'Not yet' to the check-in: ask again in a week. Non-financial (no proposal), audited."""
    if inv.status not in ("sent", "part_paid"):
        raise conflict(f"{label(inv)} is not waiting for a payment", BAD_STATUS)
    before = {"checked_on": inv.checked_on.isoformat() if inv.checked_on else None}
    inv.checked_on = on
    ss.flush()
    log(ss, rv, "payment_checked", record_type="invoice", record_id=inv.id, record_ref=inv.ref, before=before,
        after={"checked_on": on.isoformat(), "paid": False, "next": (on + timedelta(days=CHECK_EVERY_DAYS)).isoformat()})
    return inv


def delete_invoice(ss: Session, rv: Rev, inv: Invoice) -> None:
    """Only an invoice not raised yet. What was moved into it comes back: a part-paid invoice's balance (part
    paid again), the invoices merged into a combined one (to raise again)."""
    if inv.status != "to_raise":
        raise conflict("Only an invoice not raised yet can be deleted", BAD_STATUS)
    log(ss, rv, "invoice_deleted", record_type="invoice", record_id=inv.id, record_ref=inv.ref, before=snapshot(inv))
    for src in list(ss.scalars(select(Invoice).where(Invoice.workspace_id == rv.ws, Invoice.moved_to_id == inv.id))):
        before = snapshot(src)
        src.status = "to_raise" if src.status == "merged" else "part_paid"
        src.moved_paise, src.moved_to_id = 0, None
        src.updated_by = rv.actor_id
        ss.flush()
        log(ss, rv, "invoice_updated", record_type="invoice", record_id=src.id, record_ref=src.ref, before=before, after=snapshot(src))
    ss.delete(inv)
    ss.flush()


# --- a part payment's balance ----------------------------------------------------------------------

BALANCE_TO = ("new", "month")


@dataclass(frozen=True)
class BalancePlan:
    """Where a part-paid invoice's balance goes: a new invoice dated `on` (sent then when the day has come,
    else raised from it), or another month: added to its invoice when that one is still to raise in the
    same currency (`onto`), else a balance invoice of its own in that month."""

    invoice: Invoice
    to: str
    year: int
    month: int
    on: date | None
    send: bool
    balance_paise: int
    balance_minor: int
    onto: Invoice | None
    priced: Price

    @property
    def new_total_paise(self) -> int:
        return total_paise(self.balance_minor, self.invoice.currency, self.priced.rate_micro)

    def summary(self) -> str:
        amount = format_amount(self.balance_minor, self.invoice.currency)
        where = month_label(self.year, self.month)
        if self.onto is not None:
            head = f"Add {amount} to {label(self.onto)} (still to raise)"
        elif self.on is not None:
            head = (f"New invoice for {amount}, sent on {self.on:%d %b %Y}" if self.send
                    else f"New invoice for {amount} in {where}, to raise on {self.on:%d %b %Y}")
        else:
            head = f"New invoice for {amount} in {where}, to raise"
        return f"{head}; {label(self.invoice)} is closed as paid"


def plan_balance(ss: Session, rv: Rev, inv: Invoice, *, to: str, on: date | None = None, year: int | None = None,
                 month: int | None = None, priced: Price | None = None) -> BalancePlan:
    if inv.status != "part_paid":
        raise conflict(f"{label(inv)} is not part paid", BAD_STATUS)
    if to not in BALANCE_TO:
        raise invalid("The balance goes to a new invoice or another month", field="to")
    left = remaining_paise(inv)
    minor = share_minor(inv.amount_minor, left, inv.total_paise)
    if left <= 0 or minor <= 0:
        raise conflict(f"Nothing is left to move on {label(inv)}", NOTHING_LEFT)
    if to == "new":
        if on is None:
            raise invalid("Pick the date of the new invoice", field="on")
        year, month = on.year, on.month
    else:
        if year is None or month is None:
            raise invalid("Pick the month the balance goes to", field="month")
        on = None
    if not (2000 <= year <= 2100 and 1 <= month <= 12):
        raise invalid("Pick a month", field="month")
    onto = None
    if to == "month":
        found = ss.scalars(select(Invoice).where(Invoice.workspace_id == rv.ws, Invoice.customer_party_id == inv.customer_party_id,
                                                 Invoice.year == year, Invoice.month == month, Invoice.kind == "regular")).first()
        if found is not None and found.id != inv.id and found.currency == inv.currency and found.status == "to_raise":
            onto = found
    if onto is not None:
        priced = Price(onto.fx_rate_micro, onto.fx_source, onto.fx_date)
    elif priced is None:
        priced = price(ss, rv, inv.currency, months=[(year, month)])
    return BalancePlan(inv, to, year, month, on, on is not None and on <= rv.today, left, minor, onto, priced)


def move_balance(ss: Session, rv: Rev, inv: Invoice, *, to: str, on: date | None = None, year: int | None = None,
                 month: int | None = None, priced: Price | None = None) -> Invoice:
    """The balance goes on; the part-paid invoice closes as paid for what came in (the moved amount stays on
    it, so it is neither outstanding nor an FX loss). Returns the invoice that took the balance."""
    plan = plan_balance(ss, rv, inv, to=to, on=on, year=year, month=month, priced=priced)
    before = snapshot(inv)
    tag = f"Balance of {month_label(inv.year, inv.month)}"
    if plan.onto is not None:
        notes = f"{plan.onto.notes}; + {tag}" if plan.onto.notes else f"+ {tag}"
        target = update_invoice(ss, rv, plan.onto, amount_minor=plan.onto.amount_minor + plan.balance_minor, notes=notes)
    else:
        [target] = create_invoices(ss, rv, client=inv.client, months=[(plan.year, plan.month)], amount_minor=plan.balance_minor,
                                   currency=inv.currency, priced=plan.priced, notes=tag, kind="balance",
                                   raise_on=plan.on if plan.on is not None and not plan.send else None)
        if plan.send and plan.on is not None:
            set_status(ss, rv, target, "sent", on=plan.on)
    inv.moved_paise += plan.balance_paise
    inv.moved_to_id = target.id
    inv.status = "paid"
    inv.updated_by = rv.actor_id
    ss.flush()
    log(ss, rv, "balance_moved", record_type="invoice", record_id=inv.id, record_ref=inv.ref, before=before,
        after={**snapshot(inv), "moved_to": label(target), "moved_to_ref": target.ref})
    return target
