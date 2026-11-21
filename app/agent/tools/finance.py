"""Read-only finance tools. Every number returned comes from a fixed, workspace-scoped query."""

from __future__ import annotations

from datetime import timedelta

from agents import RunContextWrapper, function_tool
from sqlalchemy import and_, or_, select

from app import db
from app.agent.context import MunshiContext, safe_tool
from app.models import AuditEvent, Bill, BudgetLine, Claim, Invoice, Message, Party, Receipt, Settlement
from app.money import format_inr
from app.services import budget, records

Ctx = RunContextWrapper[MunshiContext]


def _pos_view(line: BudgetLine, p: dict) -> dict:
    return {
        "category": line.category, "department": line.department, "fy": line.fy,
        "allocated": format_inr(p["allocated_paise"]), "reserved": format_inr(p["reserved_paise"]),
        "committed": format_inr(p["committed_paise"]), "spent": format_inr(p["spent_paise"]),
        "available": format_inr(p["available_paise"]), "pending_claims_not_in_budget_yet": format_inr(p["pending_claims_paise"]),
        "basis": "available = allocated − reserved − committed − spent (cash-based operational budget)",
    }


@function_tool
@safe_tool
async def get_budget_status(ctx: Ctx, category: str) -> dict:
    """Budget position for one category (e.g. Travel): allocated, reserved, committed, spent, available, pending claims."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        line = await budget.get_line(s, a.workspace_id, category=category)
        p = await budget.position(s, a.workspace_id, line.id)
    ctx.context.show({"card": "budget", "line_id": line.id, "category": line.category})
    return {"ok": True, **_pos_view(line, p)}


@function_tool
@safe_tool
async def list_budget_categories(ctx: Ctx) -> dict:
    """List budget categories with their available amounts."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        lines = (await s.execute(select(BudgetLine).where(BudgetLine.workspace_id == a.workspace_id).order_by(BudgetLine.category))).scalars().all()
        out = []
        for line in lines:
            p = await budget.position(s, a.workspace_id, line.id)
            out.append({"category": line.category, "available": format_inr(p["available_paise"]), "allocated": format_inr(p["allocated_paise"])})
    return {"ok": True, "categories": out}


@function_tool
@safe_tool
async def explain_budget_change(ctx: Ctx, category: str, limit: int = 6) -> dict:
    """The most recent ledger movements on a budget line, newest first, each with its receipt and reason.
    Use this to answer 'what changed' or 'why did available go up/down'."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        line = await budget.get_line(s, a.workspace_id, category=category)
        mv = await budget.movements(s, a.workspace_id, line.id, limit=max(1, min(limit, 20)))
        rec_refs = {}
        ids = {m.receipt_id for m in mv if m.receipt_id}
        if ids:
            rec_refs = dict((await s.execute(select(Receipt.id, Receipt.ref).where(Receipt.id.in_(ids)))).all())
        p = await budget.position(s, a.workspace_id, line.id)
    sign = {"allocation": 1, "reserved": -1, "committed": -1, "spent": -1}
    rows = [{
        "movement_id": m.id, "bucket": m.bucket, "amount": format_inr(m.amount_paise), "kind": m.kind, "memo": m.memo,
        "effect_on_available": format_inr(sign[m.bucket] * m.amount_paise), "receipt": rec_refs.get(m.receipt_id),
        "at": m.created_at.isoformat() if m.created_at else None,
    } for m in mv]
    ctx.context.show({"card": "ledger", "line_id": line.id, "movement_ids": [m.id for m in mv]})
    return {"ok": True, "category": line.category, "available_now": format_inr(p["available_paise"]), "movements": rows}


@function_tool
@safe_tool
async def resolve_party(ctx: Ctx, name: str, kind: str | None = None) -> dict:
    """Find vendors, customers or employees by spoken name. kind: vendor | customer | employee.
    If several candidates are close, ask the user which one — never pick for them."""
    async with db.session_scope() as s:
        c = await records.resolve_party(s, ctx.context.actor, name, kind)
    return {"ok": True, "candidates": c[:5], "ambiguous": len(c) > 1 and c[1]["score"] >= c[0]["score"] - 0.08}


async def _attention(s, a) -> list[dict]:
    today = records.today_ist()
    items: list[dict] = []
    if a.is_approver:
        for c, p in (await s.execute(select(Claim, Party).join(Party, Party.id == Claim.beneficiary_party_id).where(
                Claim.workspace_id == a.workspace_id, Claim.state == "submitted"))).all():
            items.append({"kind": "claim_awaiting_approval", "ref": c.ref, "who": p.name, "amount_paise": c.amount_paise,
                          "date": c.business_date.isoformat(), "detail": c.merchant})
        for b, p in (await s.execute(select(Bill, Party).join(Party, Party.id == Bill.vendor_party_id).where(
                Bill.workspace_id == a.workspace_id, or_(Bill.state == "submitted",
                and_(Bill.state == "approved", Bill.settlement_state == "unpaid", Bill.due_date <= today + timedelta(days=7)))))).all():
            kind = "bill_awaiting_approval" if b.state == "submitted" else "approved_bill_due"
            items.append({"kind": kind, "ref": b.ref, "who": p.name, "amount_paise": b.amount_paise,
                          "date": (b.due_date or b.business_date).isoformat(), "detail": f"due {b.due_date:%d %b}" if b.due_date else None})
        for inv, p in (await s.execute(select(Invoice, Party).join(Party, Party.id == Invoice.customer_party_id).where(
                Invoice.workspace_id == a.workspace_id, Invoice.due_date < today, Invoice.amount_paise > Invoice.paid_paise))).all():
            items.append({"kind": "overdue_invoice", "ref": inv.number, "who": p.name, "amount_paise": inv.amount_paise - inv.paid_paise,
                          "date": inv.due_date.isoformat(), "detail": f"{(today - inv.due_date).days} days overdue"})
    else:
        for c in (await s.execute(select(Claim).where(Claim.workspace_id == a.workspace_id, Claim.beneficiary_party_id == a.party_id,
                                                      Claim.settlement_state == "unpaid"))).scalars():
            items.append({"kind": f"my_claim_{c.state}", "ref": c.ref, "who": "you", "amount_paise": c.amount_paise,
                          "date": c.business_date.isoformat(), "detail": c.merchant})
    from app.services import people as ppl
    for lr, u in await ppl.leave_requests(s, a, "awaiting_my_decision"):
        items.append({"kind": "leave_awaiting_decision", "ref": lr.ref, "who": u.display_name, "amount_paise": 0,
                      "date": lr.start_date.isoformat(), "detail": f"{lr.days} day(s) {lr.leave_type}"})
    unread = (await s.execute(select(Message).where(Message.workspace_id == a.workspace_id, Message.recipient_user_id == a.user_id,
                                                   Message.channel == "inbox", Message.read_at.is_(None)))).scalars().all()
    if unread:
        items.append({"kind": "unread_messages", "ref": f"{len(unread)} unread", "who": "Inbox", "amount_paise": 0,
                      "date": None, "detail": unread[0].subject})
    # Stable order: dated items first, oldest date first, then larger amount, then ref.
    items.sort(key=lambda i: (i["date"] is None, i["date"] or "", -i["amount_paise"], i["ref"]))
    for i in items:
        p = i.pop("amount_paise")
        i["amount"] = format_inr(p) if p else None
    return items


@function_tool
@safe_tool
async def get_attention_items(ctx: Ctx, limit: int = 3) -> dict:
    """What needs attention: pending approvals (claims, bills, leave), bills due within 7 days, overdue invoices, unread inbox.
    Returns at most `limit` (default 3) in a stable order plus the total count. Speak the same list shown on screen."""
    async with db.session_scope() as s:
        items = await _attention(s, ctx.context.actor)
    top = items[: max(1, min(limit, 10))]
    ctx.context.show({"card": "record_list", "title_hint": "attention", "items": top})
    return {"ok": True, "items": top, "total": len(items), "as_of": records.today_ist().isoformat()}


@function_tool
@safe_tool
async def get_record(ctx: Ctx, ref: str) -> dict:
    """Details of a claim (C…) or bill (B…): parties, amount, state, settlement, source document, receipts."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        r = await records.record_by_ref(s, a, ref)
        rtype = "claim" if isinstance(r, Claim) else "bill"
        party_id = r.beneficiary_party_id if rtype == "claim" else r.vendor_party_id
        party = await records.party(s, a, party_id)
        line = await budget.get_line(s, a.workspace_id, line_id=r.line_id)
        st = (await s.execute(select(Settlement).where(Settlement.workspace_id == a.workspace_id, Settlement.record_type == rtype,
                                                      Settlement.record_id == r.id))).scalars().first()
    out = {"ok": True, "type": rtype, "ref": r.ref, "party": party.name, "amount": format_inr(r.amount_paise),
           "business_date": r.business_date.isoformat(), "category": line.category, "state": r.state,
           "settlement_state": r.settlement_state, "document_id": r.document_id,
           "settlement": {"reference": st.reference, "date": st.business_date.isoformat()} if st else None}
    if rtype == "bill":
        out.update(invoice_no=r.invoice_no, due_date=r.due_date.isoformat() if r.due_date else None)
    else:
        out.update(merchant=r.merchant, submitter_id=r.submitter_id, reservation_id=r.reservation_id)
    ctx.context.show({"card": "record", "ref": r.ref})
    return out


@function_tool
@safe_tool
async def get_audit_history(ctx: Ctx, ref: str | None = None, limit: int = 10) -> dict:
    """Decision history: who did what, when, with which receipt. Optionally for one record ref."""
    a = ctx.context.actor
    if not a.is_approver:
        return {"ok": False, "code": "FORBIDDEN", "message": "Only finance approvers can view the audit history."}
    async with db.session_scope() as s:
        q = select(AuditEvent).where(AuditEvent.workspace_id == a.workspace_id, AuditEvent.action.notlike("proposal.%"))
        if ref:
            q = q.where(AuditEvent.record_ref == ref.strip().upper())
        ev = (await s.execute(q.order_by(AuditEvent.id.desc()).limit(max(1, min(limit, 30))))).scalars().all()
        rec = dict((await s.execute(select(Receipt.id, Receipt.ref).where(Receipt.id.in_({e.receipt_id for e in ev if e.receipt_id})))).all()) if ev else {}
    rows = [{"at": e.created_at.isoformat(), "action": e.action, "record": e.record_ref, "actor_id": e.actor_id,
             "receipt": rec.get(e.receipt_id), "after": e.after} for e in ev]
    ctx.context.show({"card": "audit_trail", "ref": ref, "event_ids": [e.id for e in ev]})
    return {"ok": True, "events": rows}


TOOLS = [get_budget_status, list_budget_categories, explain_budget_change, resolve_party, get_attention_items, get_record, get_audit_history]
