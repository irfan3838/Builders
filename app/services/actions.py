"""Business writes, expressed as plan (preview, no side effects) + execute (inside the confirm txn).

Amounts, dates and merchants come from stored extractions or records, never from model arguments.
The model supplies only routing decisions (who, which category, which reservation, reference).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import (
    ALREADY_SETTLED,
    FORBIDDEN,
    INVALID_STATE,
    SELF_APPROVAL,
    VALIDATION,
    DomainError,
)
from app.models import Bill, Claim, Party, Reservation, Settlement
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
                              receipt_id=receipt_id, memo=f"{res.ref} replaced by final charge {c.ref}")
            res.status, res.version = "released", res.version + 1
        await budget.post(s, actor.workspace_id, line.id, "committed", c.amount_paise, "claim_approved",
                          source_type="claim", source_id=c.id, economic_event_id=c.economic_event_id,
                          receipt_id=receipt_id, memo=f"{c.ref} approved")
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
            "This records a payment already made outside Munshi. No money is transferred.",
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
                          source_type=rtype, source_id=rec.id, economic_event_id=rec.economic_event_id, receipt_id=receipt_id)
        await budget.post(s, actor.workspace_id, line.id, "spent", rec.amount_paise, f"{rtype}_settled",
                          source_type=rtype, source_id=rec.id, economic_event_id=rec.economic_event_id, receipt_id=receipt_id)
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
                          source_type="bill", source_id=b.id, economic_event_id=b.economic_event_id, receipt_id=receipt_id)
        b.state, b.approver_id, b.version = "approved", actor.user_id, b.version + 1
        after = await budget.position(s, actor.workspace_id, line.id)
        await audit.record(s, actor, "bill.approved", record_type="bill", record_id=b.id, record_ref=b.ref,
                           before={"state": "submitted"}, after={"state": "approved"}, receipt_id=receipt_id)
        return Execution(f"Bill {b.ref} approved.", [{"type": "bill_approved", "ref": b.ref}, {"type": "budget", **_budget_effect(line, before, after)}])


class Approve:
    """Dispatch approval by record ref prefix (C = claim, B = bill)."""

    kind = "approve"

    def _target(self, args: dict[str, Any]) -> Action:
        return ApproveClaim() if args["ref"].strip().upper().startswith("C") else ApproveBill()

    async def plan(self, s, actor, args):
        return await self._target(args).plan(s, actor, args)

    async def execute(self, s, actor, args, receipt_id):
        return await self._target(args).execute(s, actor, args, receipt_id)


ACTIONS: dict[str, Action] = {a.kind: a for a in (SubmitClaim(), SubmitBill(), Approve(), Settle())}
