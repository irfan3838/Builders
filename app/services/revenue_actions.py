"""Revenue writes as propose -> present -> confirm -> receipt actions (copilot's assistant operations, Munshi's
trust boundary).

plan() runs the real service inside a SAVEPOINT and rolls it back: the preview is exactly what confirm will do,
and the rows it touched (with their versions) become the proposal's `affected`, so any change in between makes
the proposal stale. execute() runs the same service for real inside the confirming transaction.

Amounts and rates the model passes must appear in the user's recent server-observed words (grounding.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.actor import Actor
from app.errors import FORBIDDEN, VALIDATION, DomainError
from app.models import Invoice, Party
from app.services.actions import Execution, Plan
from app.services.records import today_ist
from app.services.revenue import clients as cl
from app.services.revenue import cycles, fx, fx_months, grounding, project_end
from app.services.revenue import invoices as inv
from app.services.revenue.core import Rev
from app.services.revenue.fiscal import fy_months, fy_today, month_label, month_number
from app.services.revenue.money import INR, format_amount, format_inr, rate_str, to_minor, to_rate_micro

TABLE = {"invoice": ("invoices", Invoice), "client": ("parties", Party)}


def require_view(actor: Actor) -> None:
    if not actor.is_approver:
        raise DomainError(FORBIDDEN, "Revenue is visible to finance only.")


def require_edit(actor: Actor) -> None:
    if not actor.is_approver:
        raise DomainError(FORBIDDEN, "Your role cannot change revenue.")


# --- argument parsing (model arguments are routing + the user's own numbers, re-checked here) ---------


def _clean_num(v) -> str:
    return str(v).replace(",", "").replace("₹", "").replace("$", "").replace("Rs", "").strip()


def money_minor(v, currency: str, what: str = "amount") -> int:
    try:
        return to_minor(_clean_num(v), currency)
    except (ValueError, ArithmeticError) as e:
        raise DomainError(VALIDATION, f"Could not read the {what} '{v}'.", field=what) from e


def rate_micro(v) -> int:
    try:
        return to_rate_micro(_clean_num(v))
    except (ValueError, ArithmeticError) as e:
        raise DomainError(VALIDATION, f"Could not read the rate '{v}' (rupees per unit, e.g. 84.20).", field="rate") from e


def parse_month(v: str | None, today: date) -> tuple[int, int]:
    """'2026-11', 'Nov 2026', "Nov'26", 'november' (in the current FY), 'this month', 'next month'."""
    t = (v or "").strip().lower()
    if not t or t in ("this month", "current", "now"):
        return today.year, today.month
    if t in ("next month",):
        y, m = (today.year + (today.month == 12), today.month % 12 + 1)
        return y, m
    if t in ("last month", "previous month"):
        return (today.year - (today.month == 1), (today.month - 2) % 12 + 1)
    import re

    if m := re.fullmatch(r"(\d{4})-(\d{1,2})", t):
        y, mo = int(m.group(1)), int(m.group(2))
    elif m := re.fullmatch(r"([a-z]+)[\s'-]*(\d{2,4})", t):
        mo = month_number(m.group(1)) or 0
        y = int(m.group(2)) + (2000 if len(m.group(2)) == 2 else 0)
    else:
        mo = month_number(t) or 0
        y = next((yy for yy, mm in fy_months(fy_today(today)) if mm == mo), today.year)
    if not (1 <= mo <= 12 and 2000 <= y <= 2100):
        raise DomainError(VALIDATION, f"Not a month: '{v}'. Say it like 'November 2026'.", field="month")
    return y, mo


def parse_date(v: str | None, today: date, what: str = "date") -> date:
    if not v:
        return today
    try:
        return date.fromisoformat(str(v).strip())
    except ValueError as e:
        raise DomainError(VALIDATION, f"Not a date: '{v}' (use YYYY-MM-DD).", field=what) from e


def parse_fy(v: str | None, today: date) -> str:
    from app.services.revenue.fiscal import fy_start

    if not v:
        return fy_today(today)
    try:
        fy_start(v)
    except ValueError as e:
        raise DomainError(VALIDATION, f"Not a financial year: '{v}' (like 2026-27).", field="fy") from e
    return v


def _ccy(v: str | None) -> str | None:
    return v.strip().upper() if v else None


# --- the action frame -----------------------------------------------------------------------------


@dataclass
class Outcome:
    title: str
    lines: list[str]
    speak: str
    summary: str
    effects: list[dict] = field(default_factory=list)


class RevAction:
    kind = ""
    channel = "assistant"

    def grounded(self, args: dict) -> dict[str, str | None]:
        """{label: value} the user must have said."""
        return {}

    def currencies(self, ss: Session, rv: Rev, args: dict) -> set[str]:
        """Foreign currencies whose live quote the run may need (fetched before the sync run)."""
        return {c for c in [_ccy(args.get("currency"))] if c and c != INR}

    def run(self, ss: Session, rv: Rev, args: dict) -> Outcome:  # pragma: no cover - abstract
        raise NotImplementedError

    async def _prefetch(self, s: AsyncSession, actor: Actor, rv: Rev, args: dict) -> None:
        ccys = await s.run_sync(lambda ss: self.currencies(ss, rv, args))
        if ccys:
            await fx.refresh(s, ccys, rv.today)

    async def plan(self, s: AsyncSession, actor: Actor, args: dict) -> Plan:
        require_edit(actor)
        await grounding.require_said(s, actor, self.grounded(args))
        rv = Rev.of(actor, today_ist(), channel=self.channel)
        await self._prefetch(s, actor, rv, args)

        def trial(ss: Session) -> tuple[Outcome, list[dict]]:
            ss.info["rev_touched"] = []
            sp = ss.begin_nested()
            try:
                out = self.run(ss, rv, args)
                touched = list(dict.fromkeys(ss.info["rev_touched"]))
            finally:
                sp.rollback()
                ss.info.pop("rev_touched", None)
            affected = []
            for rtype, rid in touched:
                if rtype not in TABLE:
                    continue
                table, model = TABLE[rtype]
                row = ss.get(model, rid)
                if row is not None and row.workspace_id == rv.ws:  # created in the trial: nothing to lock yet
                    affected.append({"table": table, "id": rid, "version": row.version})
            return out, affected

        out, affected = await s.run_sync(trial)
        return Plan(out.title, out.lines, out.speak, affected)

    async def execute(self, s: AsyncSession, actor: Actor, args: dict, receipt_id: int) -> Execution:
        require_edit(actor)
        rv = Rev.of(actor, today_ist(), channel=self.channel, receipt_id=receipt_id)
        out = await s.run_sync(lambda ss: self.run(ss, rv, args))
        return Execution(out.summary, out.effects)


def _fx_note(i: Invoice) -> str:
    if i.currency == INR:
        return ""
    src = {"manual": "your rate", "month": "month rate", "ecb": f"ECB {i.fx_date:%d %b}" if i.fx_date else "ECB"}.get(i.fx_source, i.fx_source)
    return f" at ₹{rate_str(i.fx_rate_micro)} ({src}) = {format_inr(i.total_paise)}"


def _eff(i: Invoice, today: date) -> dict:
    return {"type": "invoice", **inv.view(i, today)}


def _invoices_by_refs(ss: Session, rv: Rev, refs) -> list[Invoice]:
    if isinstance(refs, str):
        refs = [refs]
    if not refs:
        raise DomainError(VALIDATION, "Which invoice? Give its reference (S…).", field="refs")
    return [inv.by_ref(ss, rv, r) for r in refs]


# --- invoices -------------------------------------------------------------------------------------


class AddInvoices(RevAction):
    """New invoices (to raise) for one client: one month, a run of months, or per-month amounts."""

    kind = "rev_add_invoices"

    def grounded(self, a):
        g = {"amount": a.get("amount"), "rate": a.get("rate")}
        for n, v in enumerate(a.get("amounts") or []):
            g[f"amount #{n + 1}"] = v
        return g

    def currencies(self, ss, rv, a):
        c = _ccy(a.get("currency"))
        if not c:
            found, sure = cl.find_clients(ss, rv, a.get("client") or "")
            c = (found[0].currency if sure and found else None) or INR
        return {c} - {INR}

    def run(self, ss, rv, a):
        name = a.get("client") or ""
        found, sure = cl.find_clients(ss, rv, name)
        if sure and len(found) == 1:
            client = found[0]
        elif a.get("new_client"):
            client = cl.create_client(ss, rv, name=name, currency=_ccy(a.get("currency")) or INR)
        else:
            client = cl.resolve(ss, rv, name)  # raises AMBIGUOUS / NOT_FOUND
        currency = _ccy(a.get("currency")) or client.currency or INR
        months = [parse_month(m, rv.today) for m in (a.get("months") or [])]
        if a.get("until"):
            start = months[0] if months else parse_month(a.get("from"), rv.today)
            end = parse_month(a["until"], rv.today)
            from app.services.revenue.fiscal import add_months, month_index

            n = month_index(*end) - month_index(*start)
            if n < 0:
                raise DomainError(VALIDATION, "The last month is before the first.", field="until")
            if n >= inv.MAX_MONTHS:
                raise DomainError(VALIDATION, f"At most {inv.MAX_MONTHS} months at a time.", field="until")
            months = [add_months(*start, k) for k in range(n + 1)]
        if not months:
            months = [parse_month(a.get("from"), rv.today)]
        if a.get("amounts"):
            amount = [money_minor(x, currency) for x in a["amounts"]]
        elif a.get("amount") not in (None, ""):
            amount = money_minor(a["amount"], currency)
        else:
            raise DomainError(VALIDATION, "How much is each invoice?", field="amount")
        manual = rate_micro(a["rate"]) if a.get("rate") and currency != INR else None
        priced = inv.price(ss, rv, currency, manual, months)
        rows = inv.create_invoices(ss, rv, client=client, months=months, amount_minor=amount, currency=currency,
                                   priced=priced, notes=a.get("notes") or "")
        total = sum(r.total_paise for r in rows)
        lines = [f"{inv.label(r)}: {format_amount(r.amount_minor, r.currency)}{_fx_note(r)} — to raise" for r in rows]
        if priced.stale:
            lines.append("The ECB rate is from the last cached quote (the live fetch failed).")
        n = len(rows)
        return Outcome(f"Add {n} invoice{'s' * (n != 1)} for {client.name}", lines,
                       f"Add {n} invoice{'s' * (n != 1)} for {client.name}, {format_inr(total)} in all?",
                       f"Added {n} invoice{'s' * (n != 1)} for {client.name} ({', '.join(r.ref for r in rows)}), {format_inr(total)}, to raise.",
                       [_eff(r, rv.today) for r in rows])


class SendInvoices(RevAction):
    kind = "rev_send"

    def currencies(self, ss, rv, a):
        return {i.currency for i in _invoices_by_refs(ss, rv, a.get("refs"))} - {INR}

    def run(self, ss, rv, a):
        on = parse_date(a.get("on"), rv.today, "on")
        rows = _invoices_by_refs(ss, rv, a.get("refs"))
        lines = []
        for r in rows:
            inv.set_status(ss, rv, r, "sent", on=on)
            lines.append(f"{inv.label(r)} → sent {on:%d %b}, number {r.number}, due {r.due_on:%d %b %Y}: "
                         f"{format_amount(r.amount_minor, r.currency)}{_fx_note(r) or ''}" + ("" if r.currency != INR else ""))
        n = len(rows)
        return Outcome(f"Send {n} invoice{'s' * (n != 1)}", lines, f"Mark {', '.join(inv.label(r) for r in rows)} as sent on {on:%d %b}?",
                       f"Sent {', '.join(f'{inv.label(r)} ({r.number}, due {r.due_on:%d %b})' for r in rows)}.",
                       [_eff(r, rv.today) for r in rows])


class UnsendInvoice(RevAction):
    kind = "rev_unsend"

    def run(self, ss, rv, a):
        r = inv.by_ref(ss, rv, a.get("ref") or "")
        inv.set_status(ss, rv, r, "to_raise", on=rv.today)
        return Outcome(f"Undo send: {inv.label(r)}", [f"{inv.label(r)} → back to 'to raise'; send and due dates cleared."],
                       f"Move {inv.label(r)} back to 'to raise'?", f"{inv.label(r)} is back to 'to raise'.", [_eff(r, rv.today)])


class RecordPayment(RevAction):
    """INR credited against one invoice, or one credit allocated oldest-first across several of one client."""

    kind = "rev_payment"

    def grounded(self, a):
        return {"amount": a.get("amount")}

    def run(self, ss, rv, a):
        rows = _invoices_by_refs(ss, rv, a.get("refs"))
        amount = money_minor(a["amount"], INR) if a.get("amount") not in (None, "") else None
        on = parse_date(a.get("received_on"), rv.today, "received_on")
        settled = bool(a.get("settled", True))
        if len(rows) == 1:
            r = rows[0]
            before_left = inv.remaining_paise(r)
            inv.record_payment(ss, rv, r, amount_paise=amount, received_on=on, settled=settled)
            plan = [(r, amount if amount is not None else before_left, before_left)]
        else:
            lefts = {r.id: inv.remaining_paise(r) for r in rows}
            allocs = inv.plan_allocation(rows, amount, settled)
            inv.record_payments(ss, rv, rows, amount_paise=amount, received_on=on, settled=settled)
            plan = [(al.invoice, al.share_paise, lefts[al.invoice.id]) for al in allocs]
        lines, follow = [], []
        for r, got, left_before in plan:
            line = f"{inv.label(r)}: {format_inr(got)} received {on:%d %b} → {inv.STATUS_LABEL[r.status].lower()}"
            if r.status == "part_paid":
                line += f", {format_inr(inv.remaining_paise(r))} still due"
                follow.append(r)
            elif got != left_before:
                diff = got - left_before
                line += f" ({'+' if diff > 0 else ''}{format_inr(diff)} {'gain' if diff > 0 else 'short'}, shown as FX/settlement difference)"
            lines.append(line)
        total = sum(g for _r, g, _ in plan)
        summary = f"Recorded {format_inr(total)} from {rows[0].client.name}: " + "; ".join(lines) + "."
        if follow:
            f = follow[0]
            summary += (f" {format_inr(inv.remaining_paise(f))} of {inv.label(f)} is still due. Ask the user: leave it outstanding, "
                        f"raise a new balance invoice, or carry it onto another month's invoice ({f.ref}).")
        return Outcome(f"Record payment from {rows[0].client.name}", lines,
                       f"Record {format_inr(total)} received from {rows[0].client.name}?", summary, [_eff(r, rv.today) for r, _, _ in plan])


class EditInvoice(RevAction):
    """Amount, currency, rate or notes of an unpaid invoice. A new rate on a foreign invoice becomes that
    currency's month rate and reprices the month's other unpaid invoices too (copilot set_from_invoice)."""

    kind = "rev_edit_invoice"

    def grounded(self, a):
        return {"amount": a.get("amount"), "rate": a.get("rate")}

    def currencies(self, ss, rv, a):
        return {c for c in [_ccy(a.get("currency"))] if c} - {INR}

    def run(self, ss, rv, a):
        r = inv.by_ref(ss, rv, a.get("ref") or "")
        before = f"{format_amount(r.amount_minor, r.currency)}{_fx_note(r)}"
        ccy = _ccy(a.get("currency"))
        amount = money_minor(a["amount"], ccy or r.currency) if a.get("amount") not in (None, "") else None
        rate = rate_micro(a["rate"]) if a.get("rate") else None
        lines: list[str] = []
        if rate is not None and amount is None and ccy in (None, r.currency) and r.currency != INR:
            repriced = fx_months.set_from_invoice(ss, rv, r, rate)
            lines.append(f"{r.currency} rate for {month_label(r.year, r.month)} onward → ₹{rate_str(rate)} (month rate).")
            lines += [f"{inv.label(x)} repriced → {format_inr(x.total_paise)}" for x in repriced]
            if a.get("notes") is not None:
                inv.update_invoice(ss, rv, r, notes=a["notes"])
        else:
            priced = inv.Price(rate, "manual", None) if rate is not None else None
            inv.update_invoice(ss, rv, r, amount_minor=amount, currency=ccy, priced=priced, notes=a.get("notes"))
            if amount is not None or ccy is not None or priced is not None:
                lines.append(f"{inv.label(r)}: {before} → {format_amount(r.amount_minor, r.currency)}{_fx_note(r)}")
            if a.get("notes") is not None:
                lines.append(f"Notes: {r.notes or '—'}")
        return Outcome(f"Change {inv.label(r)}", lines, f"Change {inv.label(r)} as shown?", " ".join(lines), [_eff(r, rv.today)])


class RefreshRate(RevAction):
    kind = "rev_refresh_rate"

    def currencies(self, ss, rv, a):
        return {inv.by_ref(ss, rv, a.get("ref") or "").currency} - {INR}

    def run(self, ss, rv, a):
        r = inv.by_ref(ss, rv, a.get("ref") or "")
        old = r.total_paise
        inv.refresh_rate(ss, rv, r)
        line = f"{inv.label(r)}: {format_inr(old)} → {format_inr(r.total_paise)}{_fx_note(r)}"
        return Outcome(f"Refresh rate: {inv.label(r)}", [line], f"Reprice {inv.label(r)} at today's rate?", line, [_eff(r, rv.today)])


class DeleteDraft(RevAction):
    kind = "rev_delete_draft"

    def run(self, ss, rv, a):
        r = inv.by_ref(ss, rv, a.get("ref") or "")
        lbl, total = inv.label(r), r.total_paise
        restored = [inv.label(x) for x in ss.query(Invoice).filter(Invoice.workspace_id == rv.ws, Invoice.moved_to_id == r.id)]
        inv.delete_invoice(ss, rv, r)
        lines = [f"Delete {lbl} ({format_inr(total)}, not raised yet)."] + [f"{x}: what was moved into it comes back." for x in restored]
        return Outcome(f"Delete {lbl}", lines, f"Delete {lbl}?", " ".join(lines), [{"type": "invoice_deleted", "label": lbl}])


class MoveBalance(RevAction):
    """A part-paid invoice's balance: onto a month's invoice, or a new balance invoice dated `on`."""

    kind = "rev_move_balance"

    def currencies(self, ss, rv, a):
        return {inv.by_ref(ss, rv, a.get("ref") or "").currency} - {INR}

    def run(self, ss, rv, a):
        r = inv.by_ref(ss, rv, a.get("ref") or "")
        to = a.get("to") or ("month" if a.get("month") else "new")
        y = m = None
        on = None
        if to == "month":
            y, m = parse_month(a.get("month"), rv.today)
        else:
            on = parse_date(a.get("on"), rv.today, "on")
        plan = inv.plan_balance(ss, rv, r, to=to, on=on, year=y, month=m)
        summary = plan.summary()
        target = inv.move_balance(ss, rv, r, to=to, on=on, year=y, month=m, priced=plan.priced)
        lines = [summary + ".", f"{inv.label(r)} counts {format_inr(inv.billed_paise(r))} billed; "
                 f"{inv.label(target)} now {format_inr(target.total_paise)} ({inv.STATUS_LABEL[target.status].lower()})."]
        return Outcome(f"Move balance of {inv.label(r)}", lines, f"{summary}?", " ".join(lines), [_eff(r, rv.today), _eff(target, rv.today)])


# --- clients, cycles, project end ------------------------------------------------------------------


class ClientChange(RevAction):
    kind = "rev_client"
    OPS = ("add", "rename", "pause", "resume", "archive", "restore", "currency")

    def run(self, ss, rv, a):
        op = a.get("op")
        if op not in self.OPS:
            raise DomainError(VALIDATION, f"op is one of {', '.join(self.OPS)}", field="op")
        if op == "add":
            c = cl.create_client(ss, rv, name=a.get("client") or "", currency=_ccy(a.get("currency")) or INR)
            line = f"New client {c.name}, billed in {c.currency}."
        elif op == "restore":
            arch = [x for x in cl.clients(ss, rv, archived=True) if x.archived_at is not None]
            found = [x for x in arch if x.normalized_name == cl.normalize_name(a.get("client") or "")]
            if not found:
                raise DomainError("NOT_FOUND", f"No deleted client called '{a.get('client')}'")
            c = cl.update_client(ss, rv, found[0], archived=False)
            line = f"{c.name} restored with its history."
        else:
            c = cl.resolve(ss, rv, a.get("client") or "")
            if op == "rename":
                old = c.name
                cl.update_client(ss, rv, c, name=a.get("new_name") or "")
                line = f"{old} → {c.name}."
            elif op == "currency":
                cl.update_client(ss, rv, c, currency=_ccy(a.get("currency")) or "")
                line = f"{c.name} is now billed in {c.currency} (existing invoices keep theirs)."
            elif op == "archive":
                cl.update_client(ss, rv, c, archived=True)
                line = f"{c.name} deleted (kept with its history; add the name again to restore)."
            else:
                state = {"pause": "paused", "resume": "active"}[op]
                cl.set_client_state(ss, rv, c, state, on=parse_date(a.get("on"), rv.today, "on"))
                line = f"{c.name} → {cl.STATE_LABEL[state].lower()}" + ("; no billing suggestions until resumed." if state == "paused" else ".")
        return Outcome(f"Client: {c.name}", [line], f"{line[:-1]}?" if line.endswith(".") else line, line,
                       [{"type": "client", "client": c.name, "state": c.state, "currency": c.currency}])


class SetCycle(RevAction):
    """A client's billing cycle from a month on; rebuilds the 'to raise' invoices from there (raised ones stay)."""

    kind = "rev_set_cycle"

    def grounded(self, a):
        return {"amount": a.get("amount")}

    def currencies(self, ss, rv, a):
        c = _ccy(a.get("currency"))
        if not c:
            found, sure = cl.find_clients(ss, rv, a.get("client") or "")
            c = (found[0].currency if sure and found else None) or INR
        return {c} - {INR}

    def run(self, ss, rv, a):
        c = cl.resolve(ss, rv, a.get("client") or "")
        currency = _ccy(a.get("currency")) or c.currency or INR
        y, m = parse_month(a.get("from"), rv.today)
        if a.get("amount") in (None, ""):
            raise DomainError(VALIDATION, "How much a month?", field="amount")
        per = int(a.get("period_months") or 1)
        monthly = money_minor(a["amount"], currency)
        if a.get("amount_is_per_period"):
            if monthly % per:
                raise DomainError(VALIDATION, "That period amount doesn't split evenly by month.", field="amount")
            monthly //= per
        ci = cycles.CycleIn(y, m, monthly, currency, per, a.get("timing") or "advance", a.get("mode") or "combined")
        plan, _row = cycles.apply(ss, rv, c, ci)
        lines = [cycles.summary(ci) + "."]
        if plan.remove:
            lines.append(f"Replaces {len(plan.remove)} invoice(s) still to raise: {', '.join(inv.label(i) for i in plan.remove)}.")
        if plan.keep:
            lines.append(f"Keeps {len(plan.keep)} raised/paid: {', '.join(inv.label(i) for i in plan.keep)}.")
        lines.append(f"Plans {len(plan.create)} invoice(s) to {month_label(*plan.until)}: "
                     + ", ".join(f"{p.label} {format_amount(p.amount_minor, currency)}" for p in plan.create[:8])
                     + (" …" if len(plan.create) > 8 else "") + ".")
        if plan.skipped:
            lines.append(f"Skips {', '.join(p.label for p in plan.skipped)} (already covered).")
        return Outcome(f"Billing cycle: {c.name}", lines, f"Set {c.name}'s cycle: {cycles.summary(ci)}?", " ".join(lines),
                       [{"type": "cycle", "client": c.name, "summary": cycles.summary(ci), "created": len(plan.create)}])


class PlanFY(RevAction):
    kind = "rev_plan_fy"

    def currencies(self, ss, rv, a):
        c = cl.resolve(ss, rv, a.get("client") or "")
        return {x.currency for x in cycles.cycles(ss, c.id)} - {INR}

    def run(self, ss, rv, a):
        c = cl.resolve(ss, rv, a.get("client") or "")
        fy = parse_fy(a.get("fy"), rv.today)
        if not cycles.cycles(ss, c.id):
            raise DomainError(VALIDATION, f"{c.name} has no billing cycle to plan from. Set one first.")
        rows = cycles.plan_fy(ss, rv, c, fy)
        lines = [f"{inv.label(r)}: {format_amount(r.amount_minor, r.currency)}{_fx_note(r)}" for r in rows] or [f"FY {fy} is already planned for {c.name}."]
        return Outcome(f"Plan FY {fy}: {c.name}", lines, f"Plan {len(rows)} invoice(s) for {c.name} in FY {fy}?",
                       f"Planned {len(rows)} invoice(s) for {c.name} in FY {fy}.", [_eff(r, rv.today) for r in rows])


class FxMonthRate(RevAction):
    """Set a currency's conversion rate for months; it carries forward to March. Unpaid invoices of those
    months reprice (untick with `keep`); paid / part-paid keep their rate."""

    kind = "rev_fx_month"

    def grounded(self, a):
        return {"rate": a.get("rate")}

    def run(self, ss, rv, a):
        ccy = fx_months.foreign(a.get("currency") or "")
        months = sorted({parse_month(m, rv.today) for m in (a.get("months") or [])})
        if not months:
            raise DomainError(VALIDATION, "Which months does this rate apply to?", field="months")
        rate = rate_micro(a.get("rate"))
        keep = {inv.by_ref(ss, rv, k).id for k in (a.get("keep") or [])}
        prev = fx_months.preview(ss, rv, ccy, months, rate)
        ticked = [x.invoice.id for x in prev.invoices if x.ticked and x.invoice.id not in keep]
        affected_lines = [
            f"{inv.label(x.invoice)}: {format_inr(x.invoice.total_paise)} → {format_inr(x.new_total)}"
            if x.invoice.id in ticked else f"{inv.label(x.invoice)}: keeps {format_inr(x.invoice.total_paise)} ({x.reason or 'kept'})"
            for x in prev.invoices]
        when = ", ".join(month_label(*ym) for ym in months)
        carried = f"; carries into {month_label(*prev.carried[0])}–{month_label(*prev.carried[-1])}" if prev.carried else ""
        _plan, repriced = fx_months.apply(ss, rv, ccy, months, rate, ticked)
        lines = [f"{ccy} rate for {when} → ₹{rate_str(rate)}{carried}."] + affected_lines
        return Outcome(f"{ccy} rate: {when}", lines, f"Set the {ccy} rate to ₹{rate_str(rate)} for {when}?",
                       f"{ccy} rate set to ₹{rate_str(rate)} for {when}{carried}; {len(repriced)} invoice(s) repriced.",
                       [_eff(r, rv.today) for r in repriced])


class EndProject(RevAction):
    """Project over: raise each pending invoice (separate), fold them into one (combine), write off unpaid from a
    month (ignore), or just end it (none)."""

    kind = "rev_end_project"

    def currencies(self, ss, rv, a):
        c = cl.resolve(ss, rv, a.get("client") or "")
        return {i.currency for i in inv.list_invoices(ss, rv, client_id=c.id, statuses=["to_raise"])} - {INR}

    def run(self, ss, rv, a):
        c = cl.resolve(ss, rv, a.get("client") or "")
        pending = a.get("pending") or "none"
        on = parse_date(a.get("on"), rv.today, "on")
        cm = parse_month(a["combine_month"], rv.today) if a.get("combine_month") else None
        ig = parse_month(a["ignore_from"], rv.today) if a.get("ignore_from") else None
        send_now = bool(a.get("send_now", True))
        p = project_end.plan(ss, rv, c, on=on, pending=pending, combine_month=cm, ignore_from=ig, send_now=send_now)
        lines = [p.summary() + "."] + [f"{inv.label(i)}: {format_inr(inv.remaining_paise(i) if pending == 'ignore' else i.total_paise)}" for i in p.affected]
        if pending in ("combine", "ignore") and p.affected:
            lines.append(f"Total {format_inr(p.total_paise)}.")
        lines.append(f"{c.name} is then marked project over.")
        p2, combined = project_end.apply(ss, rv, c, on=on, pending=pending, combine_month=cm, ignore_from=ig, send_now=send_now,
                                         priced=p.priced)
        effects = [{"type": "client", "client": c.name, "state": c.state}]
        if combined is not None:
            effects.append(_eff(combined, rv.today))
        return Outcome(f"End project: {c.name}", lines, f"{p.summary()}, and end {c.name}'s project?", " ".join(lines), effects)


REVENUE_ACTIONS = [AddInvoices(), SendInvoices(), UnsendInvoice(), RecordPayment(), EditInvoice(), RefreshRate(), DeleteDraft(),
                   MoveBalance(), ClientChange(), SetCycle(), PlanFY(), FxMonthRate(), EndProject()]


__all__ = ["REVENUE_ACTIONS", "require_view", "require_edit", "parse_month", "parse_date", "parse_fy"]
