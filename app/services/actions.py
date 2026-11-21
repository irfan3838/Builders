"""Business writes, expressed as plan (preview, no side effects) + execute (inside the confirm txn).

Amounts, dates and merchants come from stored extractions or records, never from model arguments.
The model supplies only routing decisions (who, which category, which reservation, reference).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import (
    ALREADY_SETTLED,
    FORBIDDEN,
    INVALID_STATE,
    NOT_FOUND,
    SELF_APPROVAL,
    VALIDATION,
    DomainError,
)
from app.models import Bill, Claim, Meeting, Party, Reservation, Settlement
from app.money import format_inr
from app.services import audit, budget, records


@dataclass
class Plan:
    title: str
    lines: list[str]
    speak: str
    affected: list[dict] = field(default_factory=list)  # [{table, id, version}]
    budget_effect: dict | None = None

    def preview(self) -> dict:
        return {"title": self.title, "lines": self.lines, "speak": self.speak, "budget_effect": self.budget_effect}


@dataclass
class Execution:
    summary: str
    effects: list[dict]


class Action(Protocol):
    kind: str

    async def plan(self, s: AsyncSession, actor: Actor, args: dict) -> Plan: ...
    async def execute(self, s: AsyncSession, actor: Actor, args: dict, receipt_id: int) -> Execution: ...


def _fmt_date(d: date) -> str:
    return d.strftime("%d %b %Y")


def _require_approver(actor: Actor, what: str) -> None:
    if not actor.is_approver:
        raise DomainError(FORBIDDEN, f"Your role cannot {what}.")


def _budget_effect(line, before: dict, after: dict) -> dict:
    return {
        "category": line.category,
        "line_id": line.id,
        "before": before,
        "after": after,
        "available_delta_paise": after["available_paise"] - before["available_paise"],
    }


def _apply(pos: dict, **delta: int) -> dict:
    out = dict(pos)
    for k, v in delta.items():
        out[f"{k}_paise"] += v
    out["available_paise"] = out["allocated_paise"] - out["reserved_paise"] - out["committed_paise"] - out["spent_paise"]
    return out


# ---------------------------------------------------------------- claims


async def _claim_inputs(s: AsyncSession, actor: Actor, args: dict):
    doc = await records.document(s, actor, int(args["document_id"]))
    if doc.outcome:
        raise DomainError(INVALID_STATE, f"Document {doc.id} intake is already closed as {doc.outcome}.")
    ex = await records.extraction(s, actor, doc.id)
    if ex is None:
        raise DomainError(INVALID_STATE, "Document has not been inspected yet.")
    f = records.effective_fields(ex)
    if ex.arithmetic == "mismatch" and not any(c.get("field") == "total_paise" for c in ex.corrections or []):
        raise DomainError(VALIDATION, "The breakdown does not add up to the total. Correct the amount first.")
    missing = [k for k in ("total_paise", "date", "vendor") if not f.get(k)]
    if missing:
        raise DomainError(VALIDATION, f"Missing fields: {', '.join(missing)}", missing=missing)
    if (f.get("currency") or "INR").upper() != "INR":
        raise DomainError(VALIDATION, "Only INR documents are supported in this release.")
    beneficiary = await records.party(s, actor, int(args["beneficiary_party_id"]), kind="employee")
    if not actor.is_approver and beneficiary.id != actor.party_id:
        raise DomainError(FORBIDDEN, "Employees can only submit their own claims.")
    line = await budget.get_line(s, actor.workspace_id, category=args["category"])
    res = None
    if args.get("reservation_id"):
        res = await s.get(Reservation, int(args["reservation_id"]))
        if res is None or res.workspace_id != actor.workspace_id:
            raise DomainError(VALIDATION, "Reservation not found.")
        if res.status != "open":
            raise DomainError(INVALID_STATE, f"Reservation {res.ref} is already {res.status}.")
        if res.employee_party_id != beneficiary.id or res.line_id != line.id:
            raise DomainError(VALIDATION, f"Reservation {res.ref} belongs to a different employee or budget line.")
    return doc, f, beneficiary, line, res


class SubmitClaim:
    kind = "submit_claim"

    async def plan(self, s, actor, args):
        doc, f, ben, line, res = await _claim_inputs(s, actor, args)
        amt = int(f["total_paise"])
        d = date.fromisoformat(f["date"])
        lines = [f"Submit expense claim for {ben.name}: {format_inr(amt)} at {f['vendor']}, dated {_fmt_date(d)}, budget {line.category}."]
        if res:
            lines.append(f"Linked to reservation {res.ref} ({format_inr(res.amount_paise)}); on approval it is replaced as the final charge.")
        lines.append(f"No budget change until approval; it shows as a pending claim of {format_inr(amt)}.")
        affected = [{"table": "documents", "id": doc.id, "version": doc.version}]
        if res:
            affected.append({"table": "reservations", "id": res.id, "version": res.version})
        speak = f"Submit {format_inr(amt)} claim for {ben.name} from {f['vendor']} under {line.category}" + (
            f", replacing reservation {res.ref} on approval?" if res else "?"
        )
        return Plan("Submit claim", lines, speak, affected)

    async def execute(self, s, actor, args, receipt_id):
        doc, f, ben, line, res = await _claim_inputs(s, actor, args)
        c = Claim(
            workspace_id=actor.workspace_id,
            ref="pending",
            beneficiary_party_id=ben.id,
            submitter_id=actor.user_id,
            document_id=doc.id,
            merchant=f["vendor"],
            description=f.get("description"),
            amount_paise=int(f["total_paise"]),
            business_date=date.fromisoformat(f["date"]),
            line_id=line.id,
            reservation_id=res.id if res else None,
            reservation_treatment=args.get("reservation_treatment") or ("final" if res else "none"),
        )
        s.add(c)
        await s.flush()
        c.ref = f"C{c.id}"
        doc.outcome, doc.status, doc.version = "claim", "closed", doc.version + 1
        await audit.record(s, actor, "claim.submitted", record_type="claim", record_id=c.id, record_ref=c.ref,
                           after={"amount_paise": c.amount_paise, "beneficiary": ben.name, "submitter_id": actor.user_id},
                           receipt_id=receipt_id)
        return Execution(f"Claim {c.ref} submitted: {format_inr(c.amount_paise)} for {ben.name}.",
                         [{"type": "claim_submitted", "ref": c.ref, "amount_paise": c.amount_paise}])


async def _approve_claim_inputs(s, actor, args, for_update=False):
    _require_approver(actor, "approve claims")
    c = await records.claim_by_ref(s, actor, args["ref"], for_update=for_update)
    if c.state != "submitted":
        raise DomainError(INVALID_STATE, f"Claim {c.ref} is {c.state}, not awaiting approval.")
    if actor.party_id is not None and c.beneficiary_party_id == actor.party_id:
        raise DomainError(SELF_APPROVAL, "You cannot approve your own reimbursement.")
    res = await s.get(Reservation, c.reservation_id) if c.reservation_id else None
    if res is not None and res.status != "open":
        res = None
    line = await budget.get_line(s, actor.workspace_id, line_id=c.line_id)
    ben = await records.party(s, actor, c.beneficiary_party_id)
    return c, res, line, ben


class ApproveClaim:
    kind = "approve_claim"

    async def plan(self, s, actor, args):
        c, res, line, ben = await _approve_claim_inputs(s, actor, args)
        before = await budget.position(s, actor.workspace_id, line.id)
        release = res.amount_paise if (res and c.reservation_treatment == "final") else 0
        after = _apply(before, reserved=-release, committed=c.amount_paise)
        lines = [f"Approve claim {c.ref}: {format_inr(c.amount_paise)} to {ben.name}, {c.merchant}, budget {line.category}."]
        if release:
            lines.append(f"Release reservation {res.ref} ({format_inr(release)}) and commit {format_inr(c.amount_paise)} in one step.")
        else:
            lines.append(f"Commit {format_inr(c.amount_paise)} to {line.category}.")
        lines.append(f"{line.category} available: {format_inr(before['available_paise'])} → {format_inr(after['available_paise'])}.")
        affected = [{"table": "claims", "id": c.id, "version": c.version}]
        if release:
            affected.append({"table": "reservations", "id": res.id, "version": res.version})
        speak = f"Approve claim {c.ref}, {format_inr(c.amount_paise)} for {ben.name}? {line.category} available becomes {format_inr(after['available_paise'])}."
        return Plan("Approve claim", lines, speak, affected, _budget_effect(line, before, after))

    async def execute(self, s, actor, args, receipt_id):
        c, res, line, ben = await _approve_claim_inputs(s, actor, args, for_update=True)
        before = await budget.position(s, actor.workspace_id, line.id)
        if res and c.reservation_treatment == "final":
            await budget.post(s, actor.workspace_id, line.id, "reserved", -res.amount_paise, "reservation_release",
                              source_type="reservation", source_id=res.id, economic_event_id=c.economic_event_id,
                              receipt_id=receipt_id, memo=f"{res.ref} replaced by final charge {c.ref}", fiscal_month=c.business_date)
            res.status, res.version = "released", res.version + 1
        await budget.post(s, actor.workspace_id, line.id, "committed", c.amount_paise, "claim_approved",
                          source_type="claim", source_id=c.id, economic_event_id=c.economic_event_id,
                          receipt_id=receipt_id, memo=f"{c.ref} approved", fiscal_month=c.business_date)
        c.state, c.approver_id, c.version = "approved", actor.user_id, c.version + 1
        after = await budget.position(s, actor.workspace_id, line.id)
        await audit.record(s, actor, "claim.approved", record_type="claim", record_id=c.id, record_ref=c.ref,
                           before={"state": "submitted"}, after={"state": "approved", "approver_id": actor.user_id},
                           receipt_id=receipt_id)
        return Execution(
            f"Claim {c.ref} approved. {line.category} available {format_inr(before['available_paise'])} → {format_inr(after['available_paise'])}.",
            [{"type": "claim_approved", "ref": c.ref}, {"type": "budget", **_budget_effect(line, before, after)}],
        )


# ---------------------------------------------------------------- settlement (claims and bills)


async def _settle_inputs(s, actor, args, for_update=False):
    _require_approver(actor, "record settlements")
    ref = args["ref"].strip().upper()
    rec = (await records.claim_by_ref(s, actor, ref, for_update=for_update)) if ref.startswith("C") else (
        await records.bill_by_ref(s, actor, ref, for_update=for_update))
    rtype = "claim" if isinstance(rec, Claim) else "bill"
    existing = (await s.execute(select(Settlement).where(
        Settlement.workspace_id == actor.workspace_id, Settlement.record_type == rtype, Settlement.record_id == rec.id))).scalars().first()
    if existing or rec.settlement_state == "settled":
        raise DomainError(ALREADY_SETTLED, f"{rec.ref} is already settled (reference {existing.reference if existing else '?'}).")
    if rec.state != "approved":
        raise DomainError(INVALID_STATE, f"{rec.ref} is {rec.state}; only approved records can be settled.")
    reference = (args.get("reference") or "").strip()
    if not reference:
        raise DomainError(VALIDATION, "A payment reference is required.")
    bdate = date.fromisoformat(args["business_date"]) if args.get("business_date") else records.today_ist()
    if bdate > records.today_ist():
        raise DomainError(VALIDATION, "Settlement date cannot be in the future; this records a past payment.")
    payee_id = rec.beneficiary_party_id if rtype == "claim" else rec.vendor_party_id
    payee = await records.party(s, actor, payee_id)
    line = await budget.get_line(s, actor.workspace_id, line_id=rec.line_id)
    return rec, rtype, payee, line, reference, bdate


class Settle:
    kind = "settle"

    async def plan(self, s, actor, args):
        rec, rtype, payee, line, reference, bdate = await _settle_inputs(s, actor, args)
        before = await budget.position(s, actor.workspace_id, line.id)
        after = _apply(before, committed=-rec.amount_paise, spent=rec.amount_paise)
        lines = [
            f"Record {format_inr(rec.amount_paise)} paid to {payee.name} against {rtype} {rec.ref}, reference {reference}, dated {_fmt_date(bdate)}.",
            "This records a payment already made outside Purser. No money is transferred.",
            f"{line.category}: {format_inr(rec.amount_paise)} moves from committed to spent; available stays {format_inr(after['available_paise'])}.",
        ]
        speak = f"Record {format_inr(rec.amount_paise)} to {payee.name} against {rec.ref}, reference {reference}?"
        table = "claims" if rtype == "claim" else "bills"
        return Plan("Record settlement", lines, speak, [{"table": table, "id": rec.id, "version": rec.version}],
                    _budget_effect(line, before, after))

    async def execute(self, s, actor, args, receipt_id):
        rec, rtype, payee, line, reference, bdate = await _settle_inputs(s, actor, args, for_update=True)
        before = await budget.position(s, actor.workspace_id, line.id)
        s.add(Settlement(workspace_id=actor.workspace_id, record_type=rtype, record_id=rec.id, amount_paise=rec.amount_paise,
                         business_date=bdate, reference=reference, recorded_by=actor.user_id, receipt_id=receipt_id))
        await budget.post(s, actor.workspace_id, line.id, "committed", -rec.amount_paise, f"{rtype}_settled",
                          source_type=rtype, source_id=rec.id, economic_event_id=rec.economic_event_id, receipt_id=receipt_id,
                          fiscal_month=rec.business_date)
        await budget.post(s, actor.workspace_id, line.id, "spent", rec.amount_paise, f"{rtype}_settled",
                          source_type=rtype, source_id=rec.id, economic_event_id=rec.economic_event_id, receipt_id=receipt_id,
                          fiscal_month=rec.business_date)
        rec.settlement_state, rec.version = "settled", rec.version + 1
        after = await budget.position(s, actor.workspace_id, line.id)
        await audit.record(s, actor, f"{rtype}.settled", record_type=rtype, record_id=rec.id, record_ref=rec.ref,
                           after={"reference": reference, "amount_paise": rec.amount_paise, "business_date": bdate.isoformat()},
                           receipt_id=receipt_id)
        return Execution(f"Recorded {format_inr(rec.amount_paise)} to {payee.name} against {rec.ref}, reference {reference}.",
                         [{"type": "settled", "ref": rec.ref, "reference": reference}, {"type": "budget", **_budget_effect(line, before, after)}])


# ---------------------------------------------------------------- vendor bills


async def _bill_inputs(s, actor, args):
    _require_approver(actor, "submit vendor bills")
    doc = await records.document(s, actor, int(args["document_id"]))
    if doc.outcome:
        raise DomainError(INVALID_STATE, f"Document {doc.id} intake is already closed as {doc.outcome}.")
    ex = await records.extraction(s, actor, doc.id)
    if ex is None:
        raise DomainError(INVALID_STATE, "Document has not been inspected yet.")
    f = records.effective_fields(ex)
    if ex.arithmetic == "mismatch" and not any(c.get("field") == "total_paise" for c in ex.corrections or []):
        raise DomainError(VALIDATION, "The breakdown does not add up to the total. Correct the amount first.")
    missing = [k for k in ("total_paise", "date") if not f.get(k)]
    if missing:
        raise DomainError(VALIDATION, f"Missing fields: {', '.join(missing)}", missing=missing)
    if args.get("vendor_party_id"):
        vendor = await records.party(s, actor, int(args["vendor_party_id"]), kind="vendor")
    elif (args.get("new_vendor_name") or "").strip():
        norm = records.normalize_name(args["new_vendor_name"])
        existing = (await s.execute(select(Party).where(Party.workspace_id == actor.workspace_id, Party.kind == "vendor",
                                                        Party.normalized_name == norm))).scalars().first()
        vendor = existing or Party(workspace_id=actor.workspace_id, kind="vendor", name=args["new_vendor_name"].strip()[:200],
                       normalized_name=records.normalize_name(args["new_vendor_name"]), aliases=[])  # transient until execute
    else:
        raise DomainError(VALIDATION, "Choose an existing vendor or give the new vendor's name.")
    line = await budget.get_line(s, actor.workspace_id, category=args["category"])
    due = date.fromisoformat(args["due_date"]) if args.get("due_date") else (
        date.fromisoformat(f["due_date"]) if f.get("due_date") else None)
    return doc, f, vendor, line, due


class SubmitBill:
    kind = "submit_bill"

    async def plan(self, s, actor, args):
        doc, f, vendor, line, due = await _bill_inputs(s, actor, args)
        amt = int(f["total_paise"])
        lines = [f"New vendor '{vendor.name}' will be added."] if vendor.id is None else []
        lines += [
            f"Enter vendor bill from {vendor.name}: {format_inr(amt)}, invoice {f.get('invoice_no') or 'not shown'}, dated {_fmt_date(date.fromisoformat(f['date']))}"
            + (f", due {_fmt_date(due)}" if due else "") + f", budget {line.category}.",
            "It goes to payables awaiting approval; budget changes only on approval.",
        ]
        return Plan("Submit vendor bill", lines, f"Enter {format_inr(amt)} bill from {vendor.name} under {line.category}?",
                    [{"table": "documents", "id": doc.id, "version": doc.version}])

    async def execute(self, s, actor, args, receipt_id):
        doc, f, vendor, line, due = await _bill_inputs(s, actor, args)
        if vendor.id is None:
            s.add(vendor)
            await s.flush()
        b = Bill(workspace_id=actor.workspace_id, ref="pending", vendor_party_id=vendor.id, document_id=doc.id,
                 invoice_no=f.get("invoice_no"), description=f.get("description"), amount_paise=int(f["total_paise"]),
                 business_date=date.fromisoformat(f["date"]), due_date=due, line_id=line.id, submitter_id=actor.user_id)
        s.add(b)
        await s.flush()
        b.ref = f"B{b.id}"
        doc.outcome, doc.status, doc.version = "bill", "closed", doc.version + 1
        await audit.record(s, actor, "bill.submitted", record_type="bill", record_id=b.id, record_ref=b.ref,
                           after={"amount_paise": b.amount_paise, "vendor": vendor.name}, receipt_id=receipt_id)
        return Execution(f"Bill {b.ref} entered: {format_inr(b.amount_paise)} from {vendor.name}.",
                         [{"type": "bill_submitted", "ref": b.ref, "amount_paise": b.amount_paise}])


async def _approve_bill_inputs(s, actor, args, for_update=False):
    _require_approver(actor, "approve vendor bills")
    b = await records.bill_by_ref(s, actor, args["ref"], for_update=for_update)
    if b.state != "submitted":
        raise DomainError(INVALID_STATE, f"Bill {b.ref} is {b.state}, not awaiting approval.")
    vendor = await records.party(s, actor, b.vendor_party_id)
    line = await budget.get_line(s, actor.workspace_id, line_id=b.line_id)
    return b, vendor, line


class ApproveBill:
    kind = "approve_bill"

    async def plan(self, s, actor, args):
        b, vendor, line = await _approve_bill_inputs(s, actor, args)
        before = await budget.position(s, actor.workspace_id, line.id)
        after = _apply(before, committed=b.amount_paise)
        lines = [
            f"Approve bill {b.ref}: {format_inr(b.amount_paise)} to {vendor.name}, budget {line.category}.",
            f"{line.category} available: {format_inr(before['available_paise'])} → {format_inr(after['available_paise'])}.",
        ]
        return Plan("Approve bill", lines, f"Approve bill {b.ref}, {format_inr(b.amount_paise)} to {vendor.name}?",
                    [{"table": "bills", "id": b.id, "version": b.version}], _budget_effect(line, before, after))

    async def execute(self, s, actor, args, receipt_id):
        b, vendor, line = await _approve_bill_inputs(s, actor, args, for_update=True)
        before = await budget.position(s, actor.workspace_id, line.id)
        await budget.post(s, actor.workspace_id, line.id, "committed", b.amount_paise, "bill_approved",
                          source_type="bill", source_id=b.id, economic_event_id=b.economic_event_id, receipt_id=receipt_id,
                          fiscal_month=b.business_date)
        b.state, b.approver_id, b.version = "approved", actor.user_id, b.version + 1
        after = await budget.position(s, actor.workspace_id, line.id)
        await audit.record(s, actor, "bill.approved", record_type="bill", record_id=b.id, record_ref=b.ref,
                           before={"state": "submitted"}, after={"state": "approved"}, receipt_id=receipt_id)
        return Execution(f"Bill {b.ref} approved.", [{"type": "bill_approved", "ref": b.ref}, {"type": "budget", **_budget_effect(line, before, after)}])


class Approve:
    """Dispatch approval by record ref prefix (C = claim, B = bill)."""

    kind = "approve"

    def _target(self, args: dict[str, Any]) -> Action:
        r = args["ref"].strip().upper()
        if r.startswith("L"):
            return DecideLeave("approve")
        return ApproveClaim() if r.startswith("C") else ApproveBill()

    async def plan(self, s, actor, args):
        return await self._target(args).plan(s, actor, args)

    async def execute(self, s, actor, args, receipt_id):
        return await self._target(args).execute(s, actor, args, receipt_id)





# ---------------------------------------------------------------- people operations

LEAVE_NAMES = {"CL": "casual leave", "SL": "sick leave", "EL": "earned leave"}


async def _leave_inputs(s, actor, args):
    from app.services import people
    lt = args["leave_type"].upper()
    if lt not in people.LEAVE_TYPES:
        raise DomainError(VALIDATION, f"Leave type must be one of {sorted(people.LEAVE_TYPES)}.")
    try:
        start, end = date.fromisoformat(args["start_date"]), date.fromisoformat(args.get("end_date") or args["start_date"])
    except ValueError as e:
        raise DomainError(VALIDATION, "Dates must be YYYY-MM-DD.") from e
    if end < start:
        raise DomainError(VALIDATION, "End date is before start date.")
    who = await people.user(s, actor, int(args.get("user_id") or actor.user_id))
    if who.id != actor.user_id and not actor.is_hr:
        raise DomainError(FORBIDDEN, "You can only apply for your own leave.")
    days = people.working_days(start, end)
    if days == 0:
        raise DomainError(VALIDATION, "Those dates are all weekend days; no leave is needed.")
    clash = await people.overlapping(s, actor.workspace_id, who.id, start, end)
    if clash:
        raise DomainError(INVALID_STATE, f"Overlaps leave {clash.ref} ({clash.start_date:%d %b}–{clash.end_date:%d %b}, {clash.state}).")
    bal = (await people.balance(s, actor.workspace_id, who.id))[lt]
    if bal["available"] < days:
        raise DomainError(VALIDATION, f"Only {bal['available']} day(s) of {LEAVE_NAMES[lt]} available; {days} requested.",
                          available=bal["available"])
    return who, lt, start, end, days, bal


class ApplyLeave:
    kind = "apply_leave"

    async def plan(self, s, actor, args):
        who, lt, start, end, days, bal = await _leave_inputs(s, actor, args)
        span = _fmt_date(start) if start == end else f"{_fmt_date(start)} to {_fmt_date(end)}"
        lines = [f"Apply {days} day(s) of {LEAVE_NAMES[lt]} for {who.display_name}: {span}."
                 + (f" Reason: {args['reason']}." if args.get("reason") else ""),
                 f"{LEAVE_NAMES[lt].capitalize()} available after approval: {bal['available'] - days} of {bal['granted']}.",
                 "It goes to the manager for approval; the days are held until then."]
        return Plan("Apply for leave", lines, f"Apply {days} day {LEAVE_NAMES[lt]} for {span}?", [])

    async def execute(self, s, actor, args, receipt_id):
        from app.models import LeaveRequest
        from app.services import people
        who, lt, start, end, days, bal = await _leave_inputs(s, actor, args)
        lr = LeaveRequest(workspace_id=actor.workspace_id, ref="pending", user_id=who.id, submitted_by=actor.user_id, leave_type=lt,
                          start_date=start, end_date=end, days=days, reason=(args.get("reason") or None))
        s.add(lr)
        await s.flush()
        lr.ref = f"L{lr.id}"
        await people.post_leave(s, actor.workspace_id, who.id, lt, "reserved", days, "leave_requested", source_id=lr.id, receipt_id=receipt_id)
        await audit.record(s, actor, "leave.submitted", record_type="leave", record_id=lr.id, record_ref=lr.ref,
                           after={"user_id": who.id, "type": lt, "days": days}, receipt_id=receipt_id)
        return Execution(f"Leave {lr.ref} submitted: {days} day(s) {LEAVE_NAMES[lt]} for {who.display_name}, awaiting approval.",
                         [{"type": "leave_submitted", "ref": lr.ref, "user_id": who.id}])


async def _leave_decision_inputs(s, actor, args, for_update=False):
    from app.services import people
    lr = await people.leave_by_ref(s, actor, args["ref"], for_update=for_update)
    owner = await people.user(s, actor, lr.user_id)
    if lr.state != "submitted":
        raise DomainError(INVALID_STATE, f"Leave {lr.ref} is {lr.state}.")
    if lr.user_id == actor.user_id:
        raise DomainError(SELF_APPROVAL, "You cannot decide your own leave.")
    if not (actor.is_hr or owner.reports_to_id == actor.user_id):
        raise DomainError(FORBIDDEN, "Only the manager or HR can decide this leave.")
    return lr, owner


class DecideLeave:
    def __init__(self, decision: str):
        self.decision = decision
        self.kind = "approve_leave" if decision == "approve" else "reject_leave"

    async def plan(self, s, actor, args):
        lr, owner = await _leave_decision_inputs(s, actor, args)
        verb = "Approve" if self.decision == "approve" else "Reject"
        lines = [f"{verb} leave {lr.ref}: {owner.display_name}, {lr.days} day(s) {LEAVE_NAMES[lr.leave_type]}, "
                 f"{_fmt_date(lr.start_date)} to {_fmt_date(lr.end_date)}.",
                 f"{owner.display_name.split()[0]} is told in the Purser inbox" + (" and by email." if owner.notify_email else ".")]
        if self.decision == "reject" and args.get("note"):
            lines.append(f"Reason given: {args['note']}")
        return Plan(f"{verb} leave", lines, f"{verb} {owner.display_name}'s {lr.days}-day leave?",
                    [{"table": "leave_requests", "id": lr.id, "version": lr.version}])

    async def execute(self, s, actor, args, receipt_id):
        from app.services import messaging, people
        lr, owner = await _leave_decision_inputs(s, actor, args, for_update=True)
        await people.post_leave(s, actor.workspace_id, lr.user_id, lr.leave_type, "reserved", -lr.days, f"leave_{self.decision}d",
                                source_id=lr.id, receipt_id=receipt_id)
        if self.decision == "approve":
            await people.post_leave(s, actor.workspace_id, lr.user_id, lr.leave_type, "used", lr.days, "leave_approved",
                                    source_id=lr.id, receipt_id=receipt_id)
        lr.state = "approved" if self.decision == "approve" else "rejected"
        lr.approver_id, lr.decision_note, lr.version = actor.user_id, (args.get("note") or None), lr.version + 1
        word = "approved" if self.decision == "approve" else "not approved"
        body = (f"Hi {owner.display_name.split()[0]},\n\nYour {LEAVE_NAMES[lr.leave_type]} ({lr.ref}) from {_fmt_date(lr.start_date)} "
                f"to {_fmt_date(lr.end_date)}, {lr.days} day(s), has been {word} by {actor.display_name}."
                + (f"\nNote: {lr.decision_note}" if lr.decision_note else ""))
        sent = await messaging.compose(s, actor, [owner], kind="leave_decision", subject=f"Leave {lr.ref} {word}", body=body,
                                       channels=["inbox", "email"], receipt_id=receipt_id)
        await audit.record(s, actor, f"leave.{lr.state}", record_type="leave", record_id=lr.id, record_ref=lr.ref,
                           after={"state": lr.state, "note": lr.decision_note}, receipt_id=receipt_id)
        return Execution(f"Leave {lr.ref} {word}; {owner.display_name} notified.",
                         [{"type": f"leave_{lr.state}", "ref": lr.ref}, {"type": "messages", **sent}])


async def _onboard_inputs(s, actor, args):
    from app.models import User
    from app.services import people
    if not actor.is_hr:
        raise DomainError(FORBIDDEN, "Only HR/admin can onboard employees.")
    name = (args.get("name") or "").strip()
    if len(name.split()) < 1 or len(name) < 2:
        raise DomainError(VALIDATION, "Full name is required.")
    if len(name) > 120:
        raise DomainError(VALIDATION, "That name is too long (max 120 characters).")
    email = (args.get("work_email") or "").strip().lower()
    if not email or "@" not in email:
        local = ".".join(normalize_part for normalize_part in name.lower().split())
        email = f"{local}@purser.demo"
    if (await s.execute(select(User).where(User.email == email))).scalars().first():
        raise DomainError(INVALID_STATE, f"A login for {email} already exists.")
    manager = await people.user(s, actor, int(args["manager_user_id"])) if args.get("manager_user_id") else None
    try:
        start = date.fromisoformat(args["start_date"])
    except (KeyError, ValueError) as e:
        raise DomainError(VALIDATION, "Start date YYYY-MM-DD is required.") from e
    return name, email, manager, start


class OnboardEmployee:
    kind = "onboard_employee"

    async def plan(self, s, actor, args):
        from app.services import messaging, people
        name, email, manager, start = await _onboard_inputs(s, actor, args)
        grants = ", ".join(f"{v[1]} {k}" for k, v in people.LEAVE_TYPES.items())
        fake = type("U", (), {"notify_email": args.get("personal_email")})()
        to, verdict = messaging.email_plan(fake)
        mail = {"deliverable": f"welcome email to {to}", "not_on_allowlist": f"no email ({to} is not on the email allow-list)",
                "email_not_configured": "no email (email not configured)", "no_email": "no personal email given"}[verdict]
        lines = [f"Create employee login for {name} <{email}>: {args.get('designation') or 'Employee'}, "
                 f"{args.get('department') or 'unassigned'} department, starting {_fmt_date(start)}.",
                 f"Reports to {manager.display_name}." if manager else "No manager set yet.",
                 f"Leave balances for this year: {grants}.",
                 f"Onboarding checklist: {len(people.ONBOARDING_CHECKLIST)} tasks (laptop, KYC and bank details, policy acknowledgement, first-week plan).",
                 f"Welcome message in the Purser inbox; {mail}."]
        return Plan("Onboard employee", lines, f"Onboard {name} as {args.get('designation') or 'employee'} in "
                    f"{args.get('department') or 'the company'}, starting {_fmt_date(start)}?", [])

    async def execute(self, s, actor, args, receipt_id):
        import secrets

        from argon2 import PasswordHasher

        from app.models import OnboardingTask, User
        from app.services import messaging, people
        name, email, manager, start = await _onboard_inputs(s, actor, args)
        party = Party(workspace_id=actor.workspace_id, kind="employee", name=name, normalized_name=records.normalize_name(name), aliases=[])
        s.add(party)
        await s.flush()
        u = User(workspace_id=actor.workspace_id, email=email, display_name=name, role="employee", party_id=party.id,
                 password_hash=PasswordHasher().hash(secrets.token_urlsafe(18)), department=args.get("department"),
                 designation=args.get("designation"), reports_to_id=manager.id if manager else None, start_date=start,
                 status="invited", notify_email=(args.get("personal_email") or None))
        s.add(u)
        await s.flush()
        for code, (_, days) in people.LEAVE_TYPES.items():
            await people.post_leave(s, actor.workspace_id, u.id, code, "granted", days, "annual_grant", receipt_id=receipt_id,
                                    memo="Onboarding grant")
        for title, owner, offset in people.ONBOARDING_CHECKLIST:
            s.add(OnboardingTask(workspace_id=actor.workspace_id, user_id=u.id, title=title, owner=owner,
                                 due_date=start + timedelta(days=offset), status="done" if owner == "hr" and offset == 0 else "open",
                                 done_by=actor.user_id if owner == "hr" and offset == 0 else None))
        body = (f"Welcome to the team, {name.split()[0]}!\n\nYou join as {args.get('designation') or 'a team member'} in "
                f"{args.get('department') or 'the company'} on {_fmt_date(start)}"
                + (f", reporting to {manager.display_name}" if manager else "") + ".\n"
                "Your Purser account is ready: ask it about leave, expenses and policies by voice, in Hindi or English.\n"
                "Before day one, please keep your PAN, Aadhaar and bank details ready.")
        sent = await messaging.compose(s, actor, [u], kind="welcome", subject="Welcome aboard", body=body,
                                       channels=["inbox", "email"], receipt_id=receipt_id)
        await audit.record(s, actor, "employee.onboarded", record_type="user", record_id=u.id, record_ref=f"U{u.id}",
                           after={"name": name, "email": email, "department": u.department, "manager_id": u.reports_to_id},
                           receipt_id=receipt_id)
        return Execution(f"{name} onboarded (U{u.id}); welcome message sent.",
                         [{"type": "employee_onboarded", "user_id": u.id}, {"type": "messages", **sent}])


async def _message_inputs(s, actor, args):
    from app.models import User
    from app.services import people
    audience = args.get("audience", "person")
    q = select(User).where(User.workspace_id == actor.workspace_id)
    if audience == "all":
        if not actor.is_hr:
            raise DomainError(FORBIDDEN, "Only HR/admin can message the whole company.")
        recipients = list((await s.execute(q)).scalars().all())
    elif audience == "department":
        dept = (args.get("department") or "").strip()
        if not actor.is_hr:
            raise DomainError(FORBIDDEN, "Only HR/admin can message a whole department.")
        recipients = list((await s.execute(q.where(func.lower(User.department) == dept.lower()))).scalars().all())
        if not recipients:
            raise DomainError(NOT_FOUND, f"No one in department '{dept}'.")
    else:
        ids = [int(i) for i in (args.get("user_ids") or [])]
        recipients = [await people.user(s, actor, i) for i in ids]
    external = []
    for e in args.get("external_emails") or []:
        e = (e or "").strip().lower()
        if not _EMAIL_RE.match(e):
            raise DomainError(VALIDATION, f"'{e}' is not a valid email address.")
        if e not in external:
            external.append(e)
    if audience == "person" and not recipients and not external:
        raise DomainError(VALIDATION, "Choose at least one recipient (a colleague or an email address).")
    recipients = [u for u in recipients if u.id != actor.user_id] or recipients
    subject, body = (args.get("subject") or "").strip(), (args.get("body") or "").strip()
    if not body:
        raise DomainError(VALIDATION, "The message body is empty.")
    if len(subject) > 200:
        raise DomainError(VALIDATION, "The subject is too long (max 200 characters); shorten it.")
    channels = [c for c in (args.get("channels") or ["inbox"]) if c in ("inbox", "email")] or ["inbox"]
    if external and "email" not in channels:
        channels.append("email")  # outsiders have no Purser inbox; email is the only way to reach them
    return recipients, subject or body[:60], body, channels, audience, external


class SendMessage:
    kind = "send_message"

    async def plan(self, s, actor, args):
        from app.services import messaging
        recipients, subject, body, channels, audience, external = await _message_inputs(s, actor, args)
        everyone = [u.display_name for u in recipients] + external
        names = ", ".join(everyone[:5]) + (f" and {len(everyone) - 5} more" if len(everyone) > 5 else "")
        lines = [f"To: {names} ({len(everyone)} {'person' if len(everyone) == 1 else 'people'}).", f"Subject: {subject}", f"Message: {body}"]
        if "email" in channels:
            verdicts = [messaging.email_plan(u)[1] for u in recipients]
            ok = verdicts.count("deliverable")
            if recipients:
                lines.append(f"Email: {ok} will be emailed; {len(recipients) - ok} get the inbox copy only"
                             + (" (email not configured)." if "email_not_configured" in verdicts else " (no allow-listed address)." if ok < len(recipients) else "."))
            for e in external:
                v = messaging.address_plan(e)[1]
                lines.append(f"Email to {e}: " + ("will be sent." if v == "deliverable" else
                             "cannot be sent (email not configured)." if v == "email_not_configured" else "cannot be sent (not on the allow-list)."))
        lines.append("Channels: " + " + ".join("Purser inbox" if c == "inbox" else "email" for c in channels) + ".")
        kind = "announcement" if audience in ("all", "department") else "message"
        return Plan("Send announcement" if kind == "announcement" else "Send message", lines,
                    f"Send this {kind} to {names}?", [])

    async def execute(self, s, actor, args, receipt_id):
        from app.services import messaging
        recipients, subject, body, channels, audience, external = await _message_inputs(s, actor, args)
        kind = "announcement" if audience in ("all", "department") else "message"
        sent = await messaging.compose(s, actor, recipients, kind=kind, subject=subject, body=body, channels=channels,
                                       receipt_id=receipt_id, external_emails=external)
        await audit.record(s, actor, f"{kind}.sent", record_type="message", after={"subject": subject, "recipients": len(recipients) + len(external),
                           **{k: v for k, v in sent.items() if k != "batch_id"}}, receipt_id=receipt_id)
        detail = f"{sent['inbox']} inbox" + (f", {sent['email_queued']} email queued, {sent['email_skipped']} email skipped" if "email" in channels else "")
        return Execution(f"{kind.capitalize()} '{subject}' sent to {len(recipients) + len(external)} ({detail}).", [{"type": "messages", **sent}])


# ---------------------------------------------------------------- meetings (Google Calendar + Meet)

_EMAIL_RE = __import__("re").compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def _meeting_inputs(s, actor, args):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from app.config import get_settings
    from app.services import calendar, people
    tz = get_settings().calendar_timezone
    title = " ".join((args.get("title") or "").split())
    if not title:
        raise DomainError(VALIDATION, "A meeting title is required.")
    if len(title) > 150:
        raise DomainError(VALIDATION, "The title is too long (max 150 characters).")
    kind = "interview" if args.get("kind") == "interview" else "meeting"
    try:
        start = datetime.fromisoformat(str(args["start"])).replace(tzinfo=ZoneInfo(tz), second=0, microsecond=0)
    except (KeyError, ValueError) as e:
        raise DomainError(VALIDATION, "Start time YYYY-MM-DDTHH:MM is required.") from e
    if not calendar.is_future(start):
        raise DomainError(VALIDATION, "That time has already passed. Pick a time in the future.")
    try:
        minutes = int(args.get("duration_minutes") or 30)
    except (TypeError, ValueError) as e:
        raise DomainError(VALIDATION, "Duration must be a number of minutes.") from e
    if not 10 <= minutes <= 480:
        raise DomainError(VALIDATION, "Duration must be between 10 minutes and 8 hours.")
    users = [await people.user(s, actor, int(i)) for i in dict.fromkeys(args.get("user_ids") or [])]
    guests = []
    for e in args.get("guest_emails") or []:
        e = (e or "").strip().lower()
        if not _EMAIL_RE.match(e):
            raise DomainError(VALIDATION, f"'{e}' is not a valid email address.")
        guests.append(e)
    if not users and not guests:
        raise DomainError(VALIDATION, "Add at least one attendee (a colleague or an email address).")
    invite = list(dict.fromkeys([*guests, *[u.notify_email.strip().lower() for u in users if u.notify_email]]))
    if len(invite) > 25:
        raise DomainError(VALIDATION, "Too many guests (max 25).")
    description = (args.get("description") or "").strip()[:2000] or None
    return title, kind, start, start + timedelta(minutes=minutes), minutes, tz, users, guests, invite, description


class ScheduleMeeting:
    kind = "schedule_meeting"

    async def plan(self, s, actor, args):
        from app.config import get_settings
        from app.services import calendar
        title, kind, start, end, minutes, tz, users, guests, invite, description = await _meeting_inputs(s, actor, args)
        probe = Meeting(start_at=start, end_at=end, timezone=tz)
        who = [u.display_name for u in users] + guests
        lines = [f"{'Interview' if kind == 'interview' else 'Meeting'}: {title}",
                 f"When: {calendar.when_text(probe)} ({minutes} min, {tz}).",
                 "With: " + ", ".join(who) + "."]
        if description:
            lines.append(f"Notes: {description}")
        if get_settings().calendar_enabled and actor.uses_google:
            lines.append("Google Calendar event with a Google Meet link; Google emails the invite to "
                         + (", ".join(invite) if invite else "no one (no email addresses on file)") + ".")
            no_mail = [u.display_name for u in users if not u.notify_email]
            if no_mail:
                lines.append(f"No email on file for {', '.join(no_mail)}: they get the link in the Purser inbox only.")
        else:
            lines.append("Saved in the Purser calendar and the attendees' Purser inboxes (Google Calendar is connected for the linked account only, so no Meet link).")
        return Plan("Schedule interview" if kind == "interview" else "Schedule meeting", lines,
                    f"Schedule '{title}' on {calendar.when_text(probe)} with {', '.join(who[:3])}"
                    + (f" and {len(who) - 3} more" if len(who) > 3 else "") + "?", [])

    async def execute(self, s, actor, args, receipt_id):
        import uuid

        from app.config import get_settings
        title, kind, start, end, minutes, tz, users, guests, invite, description = await _meeting_inputs(s, actor, args)
        enabled = get_settings().calendar_enabled and actor.uses_google
        m = Meeting(workspace_id=actor.workspace_id, ref="pending", kind=kind, title=title, description=description,
                    start_at=start, end_at=end, timezone=tz, organizer_id=actor.user_id, attendee_user_ids=[u.id for u in users],
                    guest_emails=invite, google_event_id=uuid.uuid4().hex, status="queued" if enabled else "skipped",
                    status_detail=None if enabled else "calendar_not_configured", receipt_id=receipt_id)
        s.add(m)
        await s.flush()
        m.ref = f"MT{m.id}"
        await audit.record(s, actor, f"{kind}.scheduled", record_type="meeting", record_id=m.id, record_ref=m.ref,
                           after={"title": title, "start": start.isoformat(), "minutes": minutes, "guests": len(invite),
                                  "attendees": len(users), "status": m.status}, receipt_id=receipt_id)
        tail = "creating the Google Meet link and sending invites" if enabled else "saved in the Purser calendar"
        return Execution(f"{'Interview' if kind == 'interview' else 'Meeting'} {m.ref} '{title}' scheduled; {tail}.",
                         [{"type": "meeting", "ref": m.ref, "status": m.status, "guests": len(invite)}])


ACTIONS: dict[str, Action] = {a.kind: a for a in (SubmitClaim(), SubmitBill(), Approve(), Settle(), ApplyLeave(),
                                                  DecideLeave("reject"), OnboardEmployee(), SendMessage(),
                                                  ScheduleMeeting())}

# Budget planning writes live in their own module; registered here so proposals see one ACTIONS table.
from app.services.budget_actions import ALL as _BUDGET_ACTIONS  # noqa: E402

ACTIONS.update({a.kind: a for a in _BUDGET_ACTIONS})

# Revenue (customer invoices, ported from the copilot Revenue module): same propose -> confirm -> receipt path.
from app.services.revenue_actions import REVENUE_ACTIONS as _REVENUE_ACTIONS  # noqa: E402

ACTIONS.update({a.kind: a for a in _REVENUE_ACTIONS})

# Contracts (copilot contracts module, lean port): create, review flags, details, status, rescan.
from app.services.contract_actions import CONTRACT_ACTIONS as _CONTRACT_ACTIONS  # noqa: E402

ACTIONS.update({a.kind: a for a in _CONTRACT_ACTIONS})

# Gmail + Google Calendar changes on the linked account (send/reply, inbox housekeeping, move/cancel an event).
from app.services.google_actions import GOOGLE_ACTIONS as _GOOGLE_ACTIONS  # noqa: E402

ACTIONS.update({a.kind: a for a in _GOOGLE_ACTIONS})

# Travel: simulated flight booking with a confirmation email (and a calendar hold for the linked Google account).
from app.services.travel.booking import TRAVEL_ACTIONS as _TRAVEL_ACTIONS  # noqa: E402

ACTIONS.update({a.kind: a for a in _TRAVEL_ACTIONS})

# Tasks assigned to others and helpdesk tickets (own to-dos are saved directly by the tools).
from app.services.work import WORK_ACTIONS as _WORK_ACTIONS  # noqa: E402

ACTIONS.update({a.kind: a for a in _WORK_ACTIONS})

# User routines (custom workflows): saving or deleting one is confirmed like any other change.
from app.services.custom_workflows import CUSTOM_WORKFLOW_ACTIONS as _CUSTOM_WORKFLOW_ACTIONS  # noqa: E402

ACTIONS.update({a.kind: a for a in _CUSTOM_WORKFLOW_ACTIONS})
