"""Ported from copilot services/project_end.py (user's own code), workspace-scoped for Purser.

A project is over: what happens to its pending invoices, then the client is ended.

- `separate`: each invoice still to raise is raised (marked sent on the end day).
- `combine`: they become one `combined` invoice in a month the user picks (one currency; priced at that
  month's rate), sent on the end day when asked; each one folded in is `merged` (it points to it).
- `ignore`: the invoices from a month on that are not paid (to raise, sent, part paid) are written off:
  kept, greyed, out of every money figure (what part of one came in still counts as received).
- `none`: the client is just ended, as before.

Preview first (`plan`, no writes); `apply` runs the same plan and the client's state change in one
transaction, with one `project_closed` audit row for the choice plus each invoice's own row.
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models import Invoice
from app.models import Party as Client
from app.services.revenue import clients as cl_svc
from app.services.revenue import invoices as inv_svc
from app.services.revenue.core import MIXED_CURRENCY, NOTHING_PENDING, SAME_STATE, Rev, conflict, invalid, log
from app.services.revenue.fiscal import month_index, month_label
from app.services.revenue.money import total_paise

PENDING = ("none", "separate", "combine", "ignore")
PENDING_LABEL = {
    "none": "Just end it",
    "separate": "Raise each pending invoice",
    "combine": "One combined invoice",
    "ignore": "Ignore invoices from a month on",
}


@dataclass
class EndPlan:
    client: Client
    on: date
    pending: str
    affected: list[Invoice] = field(default_factory=list)  # the invoices the choice changes
    combine_month: tuple[int, int] | None = None
    ignore_from: tuple[int, int] | None = None
    send_now: bool = True
    currency: str | None = None  # the combined invoice's
    amount_minor: int = 0
    priced: inv_svc.Price | None = None

    @property
    def total_paise(self) -> int:
        """The combined invoice's INR total, or what the affected invoices add up to."""
        if self.pending == "combine" and self.priced is not None and self.currency:
            return total_paise(self.amount_minor, self.currency, self.priced.rate_micro)
        if self.pending == "ignore":
            return sum(inv_svc.remaining_paise(i) for i in self.affected)
        return sum(i.total_paise for i in self.affected)

    def summary(self) -> str:
        n = len(self.affected)
        s = "" if n == 1 else "s"
        if self.pending == "separate":
            return f"Raise {n} pending invoice{s} on {self.on:%d %b %Y}" if n else "No invoices to raise"
        if self.pending == "combine" and self.combine_month:
            when = month_label(*self.combine_month)
            sent = f", sent on {self.on:%d %b %Y}" if self.send_now else ", to raise"
            return f"Combine {n} pending invoice{s} into one invoice in {when}{sent}"
        if self.pending == "ignore" and self.ignore_from:
            frm = month_label(*self.ignore_from)
            return f"Write off {n} unpaid invoice{s} from {frm} on" if n else f"Nothing unpaid from {frm} on"
        return "End the project; invoices stay as they are"


def _later_or_same(inv: Invoice, ym: tuple[int, int]) -> bool:
    return month_index(inv.year, inv.month) >= month_index(*ym)


def plan(
    session: Session,
    rv: Rev,
    client: Client,
    *,
    on: date,
    pending: str,
    combine_month: tuple[int, int] | None = None,
    ignore_from: tuple[int, int] | None = None,
    send_now: bool = True,
    priced: inv_svc.Price | None = None,
) -> EndPlan:
    """`priced`: the combined invoice's rate a confirmed proposal was shown (else the month's rate now)."""
    if pending not in PENDING:
        raise invalid("Raise them separately, combine them, ignore them, or just end it", field="pending")
    if client.state == "ended":
        raise conflict(f"{client.name}'s project is already over", SAME_STATE)
    rows = inv_svc.list_invoices(session, rv, client_id=client.id)
    p = EndPlan(client, on, pending, send_now=send_now)
    if pending == "separate":
        p.affected = [i for i in rows if i.status == "to_raise"]
    elif pending == "combine":
        if combine_month is None:
            raise invalid("Pick the month of the combined invoice", field="combine_month")
        p.combine_month = combine_month
        p.affected = [i for i in rows if i.status == "to_raise"]
        if not p.affected:
            raise conflict(f"{client.name} has no invoices waiting to be raised", NOTHING_PENDING)
        currencies = {i.currency for i in p.affected}
        if len(currencies) > 1:
            raise conflict(
                f"The pending invoices are in {', '.join(sorted(currencies))}: "
                "one invoice takes one currency",
                MIXED_CURRENCY,
            )
        p.currency = currencies.pop()
        p.amount_minor = sum(i.amount_minor for i in p.affected)
        p.priced = priced or inv_svc.price(session, rv, p.currency, months=[combine_month])
    elif pending == "ignore":
        if ignore_from is None:
            raise invalid("Pick the month from which invoices are ignored", field="ignore_from")
        p.ignore_from = ignore_from
        p.affected = [i for i in rows if i.status in inv_svc.UNPAID and _later_or_same(i, ignore_from)]
    return p


def apply(
    session: Session,
    rv: Rev,
    client: Client,
    *,
    on: date,
    pending: str,
    combine_month: tuple[int, int] | None = None,
    ignore_from: tuple[int, int] | None = None,
    send_now: bool = True,
    priced: inv_svc.Price | None = None,
) -> tuple[EndPlan, Invoice | None]:
    """Run the plan, then end the client. Returns the plan and the combined invoice (if one was made)."""
    p = plan(
        session,
        rv,
        client,
        on=on,
        pending=pending,
        combine_month=combine_month,
        ignore_from=ignore_from,
        send_now=send_now,
        priced=priced,
    )
    labels = [inv_svc.label(i) for i in p.affected]
    combined: Invoice | None = None
    if pending == "separate":
        for inv in p.affected:
            inv_svc.set_status(session, rv, inv, "sent", on=on)
    elif pending == "combine" and p.combine_month and p.currency and p.priced:
        months = ", ".join(month_label(i.year, i.month) for i in p.affected)
        [combined] = inv_svc.create_invoices(
            session,
            rv,
            client=client,
            months=[p.combine_month],
            amount_minor=p.amount_minor,
            currency=p.currency,
            priced=p.priced,
            notes=f"Combined at project end: {months}",
            kind="combined",
        )
        for inv in p.affected:
            _close(session, rv, inv, "merged", into=combined)
        if send_now:
            inv_svc.set_status(session, rv, combined, "sent", on=on)
    elif pending == "ignore":
        for inv in p.affected:
            _close(session, rv, inv, "written_off")
    cl_svc.set_client_state(session, rv, client, "ended", on=on)
    log(
        session,
        rv,
        "project_closed",
        record_type="client",
        record_id=client.id,
        record_ref=client.name,
        after={
            "pending": pending,
            "on": on.isoformat(),
            "invoices": labels,
            "combine_month": f"{p.combine_month[0]}-{p.combine_month[1]:02d}" if p.combine_month else None,
            "ignore_from": f"{p.ignore_from[0]}-{p.ignore_from[1]:02d}" if p.ignore_from else None,
            "combined": inv_svc.label(combined) if combined else None,
        },
    )
    return p, combined


def _close(session: Session, rv: Rev, inv: Invoice, status: str, *, into: Invoice | None = None) -> None:
    before = inv_svc.snapshot(inv)
    inv.status = status
    if into is not None:
        inv.moved_paise, inv.moved_to_id = inv.total_paise, into.id
    inv.updated_by = rv.actor_id
    session.flush()
    after = inv_svc.snapshot(inv)
    if into is not None:
        after["merged_into"] = inv_svc.label(into)
    log(
        session,
        rv,
        "invoice_merged" if status == "merged" else "invoice_written_off",
        record_type="invoice",
        record_id=inv.id,
        record_ref=inv.ref,
        before=before,
        after=after,
    )
