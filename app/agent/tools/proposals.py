"""Write tools. They only PROPOSE; execution happens via confirm_pending_proposal, which requires a
server-observed affirmative user turn after the preview (or the on-screen Confirm button)."""

from __future__ import annotations

from typing import Literal

from agents import RunContextWrapper, function_tool

from app import db
from app.agent.context import PurserContext, safe_tool
from app.errors import NOT_FOUND, DomainError
from app.models import Proposal
from app.services import confirmation, proposals

Ctx = RunContextWrapper[PurserContext]


def _proposal_view(p: Proposal) -> dict:
    return {"proposal_id": p.id, "status": p.status, "kind": p.kind, "preview": p.preview["lines"], "say": p.preview["speak"],
            "budget_effect": p.preview.get("budget_effect"),
            "instruction": "Read the preview to the user and ask for confirmation. Do NOT confirm in the same turn."}


async def _propose(ctx: Ctx, kind: str, args: dict) -> dict:
    async with db.session_scope() as s:
        p = await proposals.create(s, ctx.context.actor, kind, args)
    ctx.context.show({"card": "proposal", "proposal_id": p.id})
    return {"ok": True, **_proposal_view(p)}


@function_tool
@safe_tool
async def propose_submit_claim(ctx: Ctx, document_id: int, beneficiary_party_id: int, category: str,
                               reservation_id: int | None = None,
                               reservation_treatment: Literal["final", "none"] = "none") -> dict:
    """Propose submitting an employee-paid expense as a reimbursement claim. Amount/date/merchant come from the
    inspected document. Use reservation_treatment='final' only when the user confirmed this receipt is the final
    charge for that reservation."""
    if reservation_id:
        ctx.context.show({"card": "claim_review", "document_id": document_id, "reservation_id": reservation_id})
    return await _propose(ctx, "submit_claim", {"document_id": document_id, "beneficiary_party_id": beneficiary_party_id,
                                                "category": category, "reservation_id": reservation_id,
                                                "reservation_treatment": reservation_treatment if reservation_id else "none"})


@function_tool
@safe_tool
async def propose_submit_bill(ctx: Ctx, document_id: int, category: str, vendor_party_id: int | None = None,
                              new_vendor_name: str | None = None, due_date: str | None = None) -> dict:
    """Propose entering an unpaid vendor invoice into payables. Give vendor_party_id for a known vendor, or
    new_vendor_name if the user confirmed it is a new vendor. due_date YYYY-MM-DD if not printed."""
    return await _propose(ctx, "submit_bill", {"document_id": document_id, "category": category, "vendor_party_id": vendor_party_id,
                                               "new_vendor_name": new_vendor_name, "due_date": due_date})


@function_tool
@safe_tool
async def propose_approval(ctx: Ctx, ref: str) -> dict:
    """Propose approving a submitted claim (C…) or vendor bill (B…). Shows the exact budget effect."""
    if ref.strip().upper().startswith("C"):
        ctx.context.show({"card": "claim_review", "ref": ref.strip().upper()})
    return await _propose(ctx, "approve", {"ref": ref})


@function_tool
@safe_tool
async def propose_settlement(ctx: Ctx, ref: str, reference: str, business_date: str | None = None) -> dict:
    """Propose recording that an approved claim or bill was paid in full outside Purser (no money moves).
    reference = UTR/cheque/transaction reference the user gave; business_date YYYY-MM-DD (default today)."""
    return await _propose(ctx, "settle", {"ref": ref, "reference": reference, "business_date": business_date})


@function_tool
@safe_tool
async def get_pending_proposal(ctx: Ctx) -> dict:
    """The current open proposal awaiting the user's decision in this conversation, if any."""
    async with db.session_scope() as s:
        p = await proposals.get_open(s, ctx.context.actor)
    if p is None:
        return {"ok": True, "pending": None}
    ctx.context.show({"card": "proposal", "proposal_id": p.id})
    return {"ok": True, "pending": _proposal_view(p)}


@function_tool
@safe_tool
async def confirm_pending_proposal(ctx: Ctx) -> dict:
    """Execute the open proposal ONLY after the user clearly said yes to its preview in their latest reply.
    The server checks the user's own latest utterance; if it is not a clear yes, nothing happens.
    Speak success only from the returned receipt."""
    from app.services import messaging
    out = await _confirm(ctx)
    messaging.dispatch_soon()  # emails go out only after the confirming transaction has committed
    return out


async def _confirm(ctx: Ctx) -> dict:
    """Execute the open proposal ONLY after the user clearly said yes to its preview in their latest reply.
    The server checks the user's own latest utterance; if it is not a clear yes, nothing happens.
    Speak success only from the returned receipt."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        p = await proposals.get_open(s, a)
        if p is None:
            raise DomainError(NOT_FOUND, "There is no pending proposal to confirm.")
        evidence = await confirmation.spoken_confirmation(s, a, p)
        out = await proposals.confirm(s, a, p.id, via=f"voice:{evidence['source']}", evidence=evidence)
        if out.status in ("executed", "replayed"):
            r = out.receipt
            ctx.context.show({"card": "receipt", "receipt_id": r.id})
            return {"ok": True, "status": out.status, "receipt": r.ref, "summary": r.summary, "effects": r.effects}
        new = out.new_proposal
        if new is not None:
            ctx.context.show({"card": "proposal", "proposal_id": new.id})
        return {"ok": False, "code": "STALE_PROPOSAL", "status": out.status,
                "message": "Records changed since the preview; nothing was executed. Present the new preview and ask again.",
                "new_proposal": _proposal_view(new) if new else None}


@function_tool
@safe_tool
async def cancel_pending_proposal(ctx: Ctx) -> dict:
    """Cancel the open proposal (user said no / cancel / changed their mind)."""
    async with db.session_scope() as s:
        p = await proposals.get_open(s, ctx.context.actor)
        if p is None:
            return {"ok": True, "cancelled": None}
        await proposals.cancel(s, ctx.context.actor, p.id)
    return {"ok": True, "cancelled": p.id}


TOOLS = [propose_submit_claim, propose_submit_bill, propose_approval, propose_settlement, get_pending_proposal,
         confirm_pending_proposal, cancel_pending_proposal]
