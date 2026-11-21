"""Revenue tools (customer invoices, ported from the copilot Revenue module).

Reads answer from stored rows; writes only PROPOSE (rev_* actions) and go through confirm_pending_proposal.
Reminders and the weekly "not yet" check are non-financial and written directly (audited), as in copilot.
"""

from __future__ import annotations

from typing import Literal

from agents import RunContextWrapper, function_tool

from app import db
from app.agent.context import PurserContext, safe_tool
from app.agent.tools.proposals import _propose
from app.services.records import today_ist
from app.services.revenue import clients as cl
from app.services.revenue import fx, reads, reminders
from app.services.revenue import invoices as inv
from app.services.revenue.core import Rev
from app.services.revenue_actions import parse_date, parse_fy, parse_month, require_edit, require_view

Ctx = RunContextWrapper[PurserContext]


def _period(period: str | None, today) -> str | None:
    """'fy', 'q1'..'q4', 'YYYY-MM', 'YYYY-MM..YYYY-MM', or a month name ('November')."""
    if not period or period.lower() in ("fy", "year", "this year"):
        return None
    p = period.strip().lower()
    if p in ("q1", "q2", "q3", "q4") or ".." in p:
        return p
    y, m = parse_month(period, today)
    return f"{y}-{m:02d}"


async def _read(ctx: Ctx, fn, *, fy_currencies: bool = False):
    a = ctx.context.actor
    require_view(a)
    rv = Rev.of(a, today_ist())
    async with db.session_scope() as s:
        if fy_currencies:
            used = await s.run_sync(lambda ss: {c.currency for c in cl.clients(ss, rv) if c.currency})
            await fx.refresh(s, used, rv.today)
        return await s.run_sync(lambda ss: fn(ss, rv))


@function_tool
@safe_tool
async def get_revenue_overview(ctx: Ctx, fy: str | None = None, period: str | None = None, client: str | None = None) -> dict:
    """Money coming in from clients: projected (billed), received, outstanding (sent, not yet paid), overdue and yet to
    raise, plus per-client lines, ageing, foreign-currency exposure and dues in the next 14 days. fy like 2026-27
    (default current); period: 'q3', a month ('November' or 2026-11) or a span 2026-08..2026-10; client: one client."""
    today = today_ist()
    f, p = parse_fy(fy, today), _period(period, today)

    def go(ss, rv):
        cid = cl.resolve(ss, rv, client).id if client else None
        return reads.overview(ss, rv, f, p, cid), cid

    out, cid = await _read(ctx, go)
    ctx.context.show({"card": "revenue", "fy": f, "period": p or "fy", "client_id": cid})
    out.pop("grid", None)  # on screen; too long to speak
    return {"ok": True, **out}


@function_tool
@safe_tool
async def list_client_invoices(ctx: Ctx, card: Literal["all", "received", "outstanding", "overdue", "to_raise", "paid"] = "all",
                               client: str | None = None, period: str | None = None, fy: str | None = None) -> dict:
    """Customer invoices with their S… references, status, amounts, due dates and payments. Use before any invoice
    write to find the right reference. card picks the figure: outstanding (sent, unpaid), overdue, to_raise (not
    invoiced yet), received, paid, all."""
    today = today_ist()
    f, p = parse_fy(fy, today), _period(period, today)

    def go(ss, rv):
        cid = cl.resolve(ss, rv, client).id if client else None
        return reads.invoice_list(ss, rv, f, p, card, cid)

    out = await _read(ctx, go)
    return {"ok": True, **out}


@function_tool
@safe_tool
async def get_invoice(ctx: Ctx, ref: str) -> dict:
    """One customer invoice (S… or its number): amount, currency and rate source, INR total, status, sent/due dates,
    payments, balance moved, notes."""
    out = await _read(ctx, lambda ss, rv: inv.view(inv.by_ref(ss, rv, ref), rv.today))
    ctx.context.show({"card": "invoice", "ref": out["ref"]})
    return {"ok": True, **out}


@function_tool
@safe_tool
async def get_client(ctx: Ctx, name: str) -> dict:
    """A revenue client: billing currency, state (active / paused / project over), billing cycle, open invoice refs."""
    out = await _read(ctx, lambda ss, rv: reads.client_info(ss, rv, name))
    return {"ok": True, **out}


@function_tool
@safe_tool
async def get_revenue_suggestions(ctx: Ctx, limit: int = 5) -> dict:
    """What to do next on revenue, most urgent first: reminders due, invoices to chase (overdue), invoices to raise,
    due soon, 'has it been paid?' weekly check-ins, foreign rates that moved over 2%, a month missing, an FY to plan.
    Each item has `do` (the action to offer) and `ref`. Speak at most three."""
    out = await _read(ctx, lambda ss, rv: reads.suggestions(ss, rv, max(1, min(limit, 10))), fy_currencies=True)
    ctx.context.show({"card": "record_list", "title_hint": "revenue",
                      "items": [{"kind": i["kind"], "ref": i["ref"] or i["kind"], "who": i["title"], "detail": i["detail"]} for i in out["items"]]})
    return {"ok": True, **out}


@function_tool
@safe_tool
async def get_fx_rates(ctx: Ctx, currency: str | None = None, fy: str | None = None, history: bool = False) -> dict:
    """Conversion rates for foreign-currency clients: each month's rate set by hand (or carried from an earlier
    month), the latest ECB reference quote (flagged stale if the live fetch failed), and with history=true the
    recent rate changes and invoices repriced."""
    f = parse_fy(fy, today_ist())
    out = await _read(ctx, lambda ss, rv: reads.fx_view(ss, rv, f, currency, history), fy_currencies=True)
    ctx.context.show({"card": "fx_rates", "fy": f})
    return {"ok": True, **out}


# --- proposals ------------------------------------------------------------------------------------


@function_tool
@safe_tool
async def propose_invoices(ctx: Ctx, client: str, amount: str | None = None, months: list[str] | None = None,
                           until: str | None = None, amounts: list[str] | None = None, currency: str | None = None,
                           rate: str | None = None, new_client: bool = False, notes: str | None = None) -> dict:
    """Propose new client invoices (they start 'to raise'). months: one or more months ('2026-11' or 'November');
    with `until`, every month from the first through `until` at `amount`; or `amounts` one per month. amount is in
    the client's currency exactly as the user said it (e.g. '50000', '1500'). rate only if the user said a rate
    (INR per unit). new_client=true only after the user confirmed it is a new client."""
    return await _propose(ctx, "rev_add_invoices", {"client": client, "amount": amount, "months": months, "until": until,
                                                    "amounts": amounts, "currency": currency, "rate": rate,
                                                    "new_client": new_client or None, "notes": notes})


@function_tool
@safe_tool
async def propose_invoice_status(ctx: Ctx, refs: list[str], status: Literal["sent", "to_raise"], on: str | None = None) -> dict:
    """Propose marking invoices sent (raised) on a date (YYYY-MM-DD, default today): stamps the number and due date.
    status='to_raise' undoes a send (one invoice, only if no payment is recorded)."""
    if status == "to_raise":
        return await _propose(ctx, "rev_unsend", {"ref": refs[0] if refs else ""})
    return await _propose(ctx, "rev_send", {"refs": refs, "on": on})


@function_tool
@safe_tool
async def propose_payment(ctx: Ctx, refs: list[str], amount: str | None = None, received_on: str | None = None,
                          settled: bool = True) -> dict:
    """Propose recording INR a client paid. One ref, or several refs of the same client for one credit (spread oldest
    first). amount = INR credited exactly as the user said; omit when they paid in full. settled=false when they said
    it is a part payment (the rest still due); settled=true closes it even if the bank credited a little less/more."""
    return await _propose(ctx, "rev_payment", {"refs": refs, "amount": amount, "received_on": received_on,
                                               "settled": settled})


@function_tool
@safe_tool
async def propose_invoice_change(ctx: Ctx, ref: str, action: Literal["edit", "refresh_rate", "delete"] = "edit",
                                 amount: str | None = None, rate: str | None = None, currency: str | None = None,
                                 notes: str | None = None) -> dict:
    """Propose changing an unpaid invoice: edit its amount / currency / rate / notes (a new rate on a foreign invoice
    becomes that month's rate and reprices the month's other unpaid invoices), refresh_rate to today's ECB quote, or
    delete an invoice not raised yet."""
    if action == "delete":
        return await _propose(ctx, "rev_delete_draft", {"ref": ref})
    if action == "refresh_rate":
        return await _propose(ctx, "rev_refresh_rate", {"ref": ref})
    return await _propose(ctx, "rev_edit_invoice", {"ref": ref, "amount": amount, "rate": rate, "currency": currency, "notes": notes})


@function_tool
@safe_tool
async def propose_balance_move(ctx: Ctx, ref: str, to: Literal["month", "new"], month: str | None = None, on: str | None = None) -> dict:
    """After a part payment: move the balance of invoice `ref` onto another month's invoice (to='month', month like
    'December'), or into a new balance invoice dated `on` (to='new', YYYY-MM-DD; today or earlier is sent at once).
    The part-paid invoice then closes as paid for what came in. Leaving it outstanding needs no tool."""
    return await _propose(ctx, "rev_move_balance", {"ref": ref, "to": to, "month": month, "on": on})


@function_tool
@safe_tool
async def propose_client_change(ctx: Ctx, op: Literal["add", "rename", "pause", "resume", "archive", "restore", "currency"],
                                client: str, new_name: str | None = None, currency: str | None = None) -> dict:
    """Propose a client change: add a client (currency INR/USD/…), rename, pause / resume billing, archive (delete,
    keeps history), restore, or change its billing currency. Ending a project uses propose_end_project."""
    return await _propose(ctx, "rev_client", {"op": op, "client": client, "new_name": new_name, "currency": currency})


@function_tool
@safe_tool
async def propose_billing_cycle(ctx: Ctx, client: str, action: Literal["set", "plan_fy"] = "set", amount: str | None = None,
                                amount_is_per_period: bool = False, start: str | None = None, period_months: int = 1,
                                timing: Literal["advance", "arrears"] = "advance",
                                mode: Literal["combined", "monthly"] = "combined", currency: str | None = None,
                                fy: str | None = None) -> dict:
    """Set a client's recurring billing from a month (start, e.g. 'December'): amount a month (or per period with
    amount_is_per_period=true, e.g. '₹30,000 a quarter'), every period_months (1 monthly, 3 quarterly, 6, 12), billed
    in advance or arrears, one combined invoice per period or one per month. Rebuilds invoices still to raise;
    raised ones stay. action='plan_fy' fills an FY (fy like 2027-28) from the cycle."""
    if action == "plan_fy":
        return await _propose(ctx, "rev_plan_fy", {"client": client, "fy": fy})
    return await _propose(ctx, "rev_set_cycle", {"client": client, "amount": amount, "amount_is_per_period": amount_is_per_period or None,
                                                 "from": start, "period_months": period_months, "timing": timing, "mode": mode,
                                                 "currency": currency})


@function_tool
@safe_tool
async def propose_fx_month_rate(ctx: Ctx, currency: str, months: list[str], rate: str, keep: list[str] | None = None) -> dict:
    """Set a conversion rate (INR per unit, as the user said it) for a currency's months; it carries forward to
    March. The preview lists the unpaid invoices that reprice; keep = refs the user wants to leave at their old rate.
    Paid and part-paid invoices always keep their rate."""
    return await _propose(ctx, "rev_fx_month", {"currency": currency, "months": months, "rate": rate, "keep": keep})


@function_tool
@safe_tool
async def propose_end_project(ctx: Ctx, client: str, pending: Literal["none", "separate", "combine", "ignore"],
                              combine_month: str | None = None, ignore_from: str | None = None, send_now: bool = True,
                              on: str | None = None) -> dict:
    """End a client's project and decide its pending invoices: separate = raise each one now; combine = one combined
    invoice in combine_month (send_now to send it today); ignore = write off unpaid invoices from ignore_from on (what
    came in still counts); none = just end it. Ask which if the user did not say."""
    return await _propose(ctx, "rev_end_project", {"client": client, "pending": pending, "combine_month": combine_month,
                                                   "ignore_from": ignore_from, "send_now": send_now, "on": on})


# --- direct, non-financial ------------------------------------------------------------------------


async def _write(ctx: Ctx, fn):
    a = ctx.context.actor
    require_edit(a)
    rv = Rev.of(a, today_ist())
    async with db.session_scope() as s:
        return await s.run_sync(lambda ss: fn(ss, rv))


@function_tool
@safe_tool
async def add_reminder(ctx: Ctx, text: str, due_on: str, client: str | None = None, invoice_ref: str | None = None) -> dict:
    """Set an in-app reminder ('remind me Friday to chase Acme'): due_on YYYY-MM-DD resolved from today's date, a short
    note, optionally about a client or an invoice. It shows in the bell when due. Not a financial write."""
    def go(ss, rv):
        cid = cl.resolve(ss, rv, client).id if client else None
        iid = inv.by_ref(ss, rv, invoice_ref).id if invoice_ref else None
        r = reminders.add(ss, rv, due_on=parse_date(due_on, rv.today, "due_on"), text=text, client_id=cid, invoice_id=iid)
        return reminders.view(r, rv.today)

    return {"ok": True, "reminder": await _write(ctx, go)}


@function_tool
@safe_tool
async def complete_reminder(ctx: Ctx, reminder_id: int) -> dict:
    """Mark a reminder done (from get_revenue_suggestions / open_reminders)."""
    return {"ok": True, "reminder": await _write(ctx, lambda ss, rv: reminders.view(reminders.done(ss, rv, reminder_id), rv.today))}


@function_tool
@safe_tool
async def mark_not_yet(ctx: Ctx, ref: str) -> dict:
    """The user says a sent invoice has NOT been paid yet (answer to the weekly 'has it been paid?' check): Purser asks
    again in a week. If they say it HAS been paid, use propose_payment instead."""
    def go(ss, rv):
        r = inv.not_paid_yet(ss, rv, inv.by_ref(ss, rv, ref), on=rv.today)
        return {"ref": r.ref, "label": inv.label(r), "next_check": inv.check_due_on(r).isoformat()}

    return {"ok": True, **await _write(ctx, go)}


TOOLS = [get_revenue_overview, list_client_invoices, get_invoice, get_client, get_revenue_suggestions, get_fx_rates,
         propose_invoices, propose_invoice_status, propose_payment, propose_invoice_change, propose_balance_move,
         propose_client_change, propose_billing_cycle, propose_fx_month_rate, propose_end_project,
         add_reminder, complete_reminder, mark_not_yet]
