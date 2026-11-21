"""Ported from copilot services/suggest.py (user's own code), workspace-scoped for Munshi.

What the finance user should do next, from the rows alone (no model): recomputed on every read, so a suggestion
disappears the moment its row changes.

Rules, most urgent first:
- reminder  — a reminder that is due;
- chase     — a sent invoice past its due date;
- raise     — an invoice still to raise, from the start of its period (billed in advance) or its end
              (in arrears); high once the period is over;
- due_soon  — a sent invoice due within 5 days;
- rate      — an unpaid foreign invoice whose rate moved more than 2% since it was priced;
- paid_check — a sent invoice, not yet due, a week after it was sent (then every week, 7 days after the
              last "not yet"): has the payment come in? Yes records it, Not yet asks again in a week;
- missing   — a client billed last month with nothing for this month yet (and no cycle covering it);
- plan      — a client's cycle runs into an FY (this one, or the next from February) with no invoices
              planned there yet.
A paused or ended client gets none of these (its rows stay; custom reminders still come up).
Each carries what does it: a row action (`act` + `ref`, no model) and/or words for the chat (`ask`).
"""

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from app.services.revenue import clients as cl_svc
from app.services.revenue import cycles, fx, reminders
from app.services.revenue import invoices as inv_svc
from app.services.revenue.core import Rev
from app.services.revenue.fiscal import add_months, fy_of, fy_today, month_label
from app.services.revenue.money import format_amount, format_inr, total_paise

Kind = Literal["reminder", "chase", "raise", "due_soon", "rate", "missing", "plan", "paid_check"]
Priority = Literal["high", "medium", "low"]
DUE_SOON_DAYS = 5
RATE_MOVE_BP = 200  # 2%, in basis points
ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Suggestion:
    id: str
    kind: Kind
    priority: Priority
    title: str
    detail: str
    act: str | None = None  # what Munshi offers to do: a propose_* tool on `ref` (an invoice S…, client, reminder)
    ref: str | None = None
    ask: str | None = None  # words for the Workspace chat
    alt_act: str | None = None  # a second button on the same row (the check-in's "Not yet")


def build(session: Session, rv: Rev) -> list[Suggestion]:
    today = rv.today
    out: list[Suggestion] = []
    this_month = (today.year, today.month)
    for r in reminders.due(session, rv):
        late = (today - r.due_on).days
        out.append(
            Suggestion(
                f"reminder-{r.id}",
                "reminder",
                "high",
                r.text,
                "Due today"
                if late == 0
                else f"Due {r.due_on:%d %b} ({late} day{'s' if late != 1 else ''} ago)",
                act="done_reminder",
                ref=str(r.id),
            )
        )
    unpaid = inv_svc.list_invoices(session, rv, statuses=list(inv_svc.UNPAID))
    for inv in unpaid:
        if not cl_svc.active(inv.client):
            continue
        name = inv_svc.label(inv)
        check = inv_svc.check_due_on(inv)
        not_due = inv.due_on is None or inv.due_on >= today  # once overdue, "chase" asks instead
        if check is not None and check <= today and not_due:
            left = inv_svc.remaining_paise(inv)
            ago = (today - inv.sent_on).days if inv.sent_on else 0
            out.append(
                Suggestion(
                    f"paid-{inv.id}",
                    "paid_check",
                    "medium",
                    f"Has {inv.client.name} paid {month_label(inv.year, inv.month)}?",
                    f"Sent {inv.sent_on:%d %b} ({ago} days ago), {format_inr(left)} to come",
                    act="mark_paid",
                    ref=inv.ref,
                    alt_act="not_yet",
                )
            )
        if inv.status in ("sent", "part_paid") and inv.due_on:
            left = inv_svc.remaining_paise(inv)
            days = (today - inv.due_on).days
            if days > 0:
                out.append(
                    Suggestion(
                        f"chase-{inv.id}",
                        "chase",
                        "high",
                        f"Chase {inv.client.name}: {format_inr(left)} overdue",
                        f"{name}, due {inv.due_on:%d %b}, {days} day{'s' if days != 1 else ''} late",
                        act="mark_paid",
                        ref=inv.ref,
                        ask=f"remind me tomorrow to chase {inv.client.name} for "
                        f"{month_label(inv.year, inv.month)}",
                    )
                )
            elif -days <= DUE_SOON_DAYS:
                out.append(
                    Suggestion(
                        f"due-{inv.id}",
                        "due_soon",
                        "low",
                        f"{inv.client.name} {format_inr(left)} due {inv.due_on:%d %b}",
                        f"{name}: due in {-days} day{'s' if days != -1 else ''}"
                        if days
                        else f"{name}: due today",
                        act="mark_paid",
                        ref=inv.ref,
                    )
                )
        if inv.status == "to_raise" and cycles.raise_on(inv) <= today:
            late = cycles.period_end(inv) < this_month
            out.append(
                Suggestion(
                    f"raise-{inv.id}",
                    "raise",
                    "high" if late else "medium",
                    f"Raise {name} invoice ({format_amount(inv.amount_minor, inv.currency)})",
                    "From an earlier month, still not raised"
                    if late
                    else f"Due to go out ({cycles.period_text(inv) or month_label(inv.year, inv.month)})",
                    act="mark_sent",
                    ref=inv.ref,
                )
            )
        # a month's own rate is the user's choice (Clients -> FX rates): never nag to refresh it
        if inv.status in ("to_raise", "sent") and inv.currency != "INR" and inv.fx_source != "month":
            now = fx.cached(session, inv.currency)
            if now and abs(now - inv.fx_rate_micro) * 10_000 > RATE_MOVE_BP * inv.fx_rate_micro:
                new_total = total_paise(inv.amount_minor, inv.currency, now)
                out.append(
                    Suggestion(
                        f"rate-{inv.id}",
                        "rate",
                        "medium",
                        f"Refresh the rate on {name}",
                        f"{format_amount(inv.amount_minor, inv.currency)} is now about "
                        f"{format_inr(new_total)} "
                        f"(priced at {format_inr(inv.total_paise)})",
                        act="refresh_rate",
                        ref=inv.ref,
                    )
                )
    out.extend(_missing(session, rv))
    out.extend(_plan(session, rv))
    return sorted(out, key=lambda s: ORDER[s.priority])


def _plan(session: Session, rv: Rev) -> list[Suggestion]:
    today = rv.today
    """A cycle with nothing planned in this FY, or (from February) in the next one."""
    fys = [fy_today(today)]
    if today.month in (2, 3):
        fys.append(fy_of(*add_months(today.year, today.month, 2)))
    out = []
    for c in cl_svc.clients(session, rv):
        if not cl_svc.active(c):
            continue
        for fy in fys:
            if cycles.needs_plan(session, c, fy):
                out.append(
                    Suggestion(
                        f"plan-{c.id}-{fy}",
                        "plan",
                        "medium",
                        f"Plan {c.name}'s invoices for FY {fy}",
                        "From its payment cycle",
                        act="plan_fy",
                        ref=f"{c.name}|{fy}",
                    )
                )
    return out


def _missing(session: Session, rv: Rev) -> list[Suggestion]:
    today = rv.today
    """Billed last month, nothing for this month: offer the same again (the rate is fetched on Confirm)."""
    last = add_months(today.year, today.month, -1)
    now = (today.year, today.month)
    have_now = {inv.customer_party_id for inv in inv_svc.list_invoices(session, rv, months=[now])}
    out = []
    seen: set[int] = set()
    for inv in inv_svc.list_invoices(session, rv, months=[last]):
        if inv.customer_party_id in have_now or inv.customer_party_id in seen or not cl_svc.active(inv.client):
            continue
        if now in cycles.covers(inv) or cycles.cycles(session, inv.customer_party_id):
            continue
        seen.add(inv.customer_party_id)  # a period invoice covers this month, or the cycle plans the client's invoices
        out.append(
            Suggestion(
                f"missing-{inv.customer_party_id}",
                "missing",
                "low",
                f"Add {inv.client.name} {month_label(*now)}?",
                f"Last month: {format_amount(inv.amount_minor, inv.currency)}",
                act="repeat_last",
                ref=inv.ref,
            )
        )
    return out
