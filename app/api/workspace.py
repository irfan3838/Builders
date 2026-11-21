"""Read models for the Purser workspace views (sidebar lists, priorities, claim review) and the mail composer.

Read-only except /api/messages/draft, which only creates a proposal; sending still needs Confirm.
All amounts come from SQL in paise and are formatted on the server.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select

from app import auth, db
from app.actor import Actor
from app.errors import DomainError
from app.models import (Bill, BudgetLine, Claim, CompanyPayment, Document, Message, Party, Proposal, Receipt, Reservation,
                        Settlement, Trip, User)
from app.money import format_inr
from app.services import budget, intake, proposals, records

router = APIRouter()


def _inr(p: int | None) -> str | None:
    return format_inr(p) if p is not None else None


def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().replace(".", " ").split())


# ------------------------------------------------------------------ claim review (flagship artifact)


async def _reservation_view(s, r: Reservation | None) -> dict | None:
    if r is None:
        return None
    t = await s.get(Trip, r.trip_id) if r.trip_id else None
    return {"id": r.id, "ref": r.ref, "description": r.description, "amount_paise": r.amount_paise, "amount": format_inr(r.amount_paise),
            "status": r.status, "trip": f"{t.city} Trip" if t else None, "city": t.city if t else None,
            "start": t.start_date.isoformat() if t else None, "end": t.end_date.isoformat() if t else None,
            "kind": "Hotel stay" if "hotel" in (r.merchant_hint or r.description or "").lower() else (r.merchant_hint or "Reservation")}


@router.get("/api/claim-review")
async def claim_review(actor: Actor = auth.ActorDep, document_id: int | None = None, ref: str | None = None,
                       reservation_id: int | None = None) -> dict:
    """Receipt vs reservation vs budget for one claim (by ref) or one receipt that may become a claim (by document)."""
    if not (document_id or ref):
        raise HTTPException(400, "document_id or ref required")
    async with db.session_scope() as s:
        claim = await records.claim_by_ref(s, actor, ref) if ref else None
        if claim is None and document_id:
            claim = (await s.execute(select(Claim).where(Claim.workspace_id == actor.workspace_id, Claim.document_id == document_id)
                                     .order_by(Claim.id.desc()))).scalars().first()
            if claim is not None:
                claim = await records.claim_by_ref(s, actor, claim.ref)  # access check
        doc_id = claim.document_id if claim else document_id
        doc = await records.document(s, actor, doc_id) if doc_id else None
        ex = await records.extraction(s, actor, doc.id) if doc else None
        f = records.effective_fields(ex) if ex else {}

        res = None
        rid = (claim.reservation_id if claim else None) or reservation_id
        if rid:
            res = await s.get(Reservation, rid)
            if res is not None and res.workspace_id != actor.workspace_id:
                res = None
        elif f and not claim:
            cands = [c for c in await intake.reservation_candidates(s, actor, f) if c["date_within_trip"]]
            if len(cands) == 1:
                res = await s.get(Reservation, cands[0]["reservation_id"])

        claimed = claim.amount_paise if claim else f.get("total_paise")
        line_id = claim.line_id if claim else (res.line_id if res else None)
        line = await s.get(BudgetLine, line_id) if line_id else None
        pos = await budget.position(s, actor.workspace_id, line.id) if line else None

        # Budget impact: from the executed receipt once approved, else projected exactly like ApproveClaim.plan.
        impact = None
        status = claim.state if claim else ("receipt" if doc else "unknown")
        if claim and claim.state == "approved":
            rc = (await s.execute(select(Receipt).where(Receipt.workspace_id == actor.workspace_id,
                                                        Receipt.effects.contains([{"type": "claim_approved", "ref": claim.ref}]))
                                  .order_by(Receipt.id.desc()))).scalars().first()
            eff = next((e for e in (rc.effects if rc else []) if e.get("type") == "budget"), None)
            if eff:
                impact = {"category": eff["category"], "before_paise": eff["before"]["available_paise"],
                          "after_paise": eff["after"]["available_paise"], "final": True, "receipt": rc.ref}
        elif pos and claimed is not None and (claim is None or claim.state == "submitted"):
            final = res is not None and res.status == "open" and (claim is None or claim.reservation_treatment == "final")
            release = res.amount_paise if final else 0
            impact = {"category": line.category, "before_paise": pos["available_paise"],
                      "after_paise": pos["available_paise"] + release - int(claimed), "final": False}
        if impact:
            impact["before"], impact["after"] = format_inr(impact["before_paise"]), format_inr(impact["after_paise"])

        # Open proposal tied to this claim/receipt in the actor's workspace (newest first).
        prop = None
        q = select(Proposal).where(Proposal.workspace_id == actor.workspace_id, Proposal.actor_id == actor.user_id,
                                   Proposal.status == "open")
        conds = []
        if claim:
            conds.append(and_(Proposal.kind == "approve", func.upper(Proposal.args["ref"].astext) == claim.ref.upper()))
        if doc:
            conds.append(and_(Proposal.kind == "submit_claim", Proposal.args["document_id"].astext == str(doc.id)))
        if conds:
            p = (await s.execute(q.where(or_(*conds)).order_by(Proposal.created_at.desc()))).scalars().first()
            if p:
                prop = {"id": p.id, "kind": p.kind, "title": p.preview.get("title"), "lines": p.preview.get("lines", [])}

        ben = await s.get(Party, claim.beneficiary_party_id) if claim else None
        guest = f.get("customer_or_guest")
        emp = None
        if res and res.employee_party_id:
            emp = await s.get(Party, res.employee_party_id)
        d = f.get("date") or (claim.business_date.isoformat() if claim else None)
        rv = await _reservation_view(s, res)
        checks = []
        if rv:
            within = bool(d and rv["start"] and date.fromisoformat(rv["start"]) <= date.fromisoformat(d) <= date.fromisoformat(rv["end"]))
            checks.append({"label": "Date within trip", "ok": within})
            who = (ben.name if ben else None) or (emp.name if emp else None)
            if guest and who:
                checks.append({"label": "Guest matches employee", "ok": _norm(who).split()[0] in _norm(guest)})
            if claimed is not None:
                checks.append({"label": "Within reserved amount", "ok": int(claimed) <= res.amount_paise})

    return {
        "ref": claim.ref if claim else None, "status": status,
        "employee": (ben.name if ben else None) or (emp.name if emp else None) or guest,
        "document": {"id": doc.id, "filename": doc.filename, "pages": doc.pages} if doc else None,
        "extracted": bool(ex),
        "receipt": {"vendor": f.get("vendor") or (claim.merchant if claim else None), "guest": guest, "date": d,
                    "invoice_no": f.get("invoice_no"),
                    "items": [{"label": li.get("description"), "amount": _inr(li.get("amount_paise"))} for li in f.get("line_items") or []],
                    "taxes": [{"label": t.get("label"), "amount": _inr(t.get("amount_paise"))} for t in f.get("taxes") or []],
                    "total_paise": claimed, "total": _inr(claimed),
                    "arithmetic": ex.arithmetic if ex else None} if (doc or claim) else None,
        "reservation": rv,
        "comparison": {"reserved_paise": res.amount_paise, "claimed_paise": int(claimed),
                       "difference_paise": res.amount_paise - int(claimed), "difference": format_inr(abs(res.amount_paise - int(claimed))),
                       "below": int(claimed) <= res.amount_paise} if (res and claimed is not None) else None,
        "checks": checks,
        "impact": impact,
        "proposal": prop,
    }


# ------------------------------------------------------------------ sidebar lists


async def _party_names(s, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict((await s.execute(select(Party.id, Party.name).where(Party.id.in_(ids)))).all())


async def _line_names(s, ws: int) -> dict[int, str]:
    return dict((await s.execute(select(BudgetLine.id, BudgetLine.category).where(BudgetLine.workspace_id == ws))).all())


@router.get("/api/claims")
async def list_claims(actor: Actor = auth.ActorDep, state: str | None = None) -> dict:
    async with db.session_scope() as s:
        q = select(Claim).where(Claim.workspace_id == actor.workspace_id)
        if not actor.is_approver:
            q = q.where(or_(Claim.beneficiary_party_id == actor.party_id, Claim.submitter_id == actor.user_id))
        if state:
            q = q.where(Claim.state == state)
        rows = (await s.execute(q.order_by(Claim.id.desc()).limit(50))).scalars().all()
        names = await _party_names(s, {c.beneficiary_party_id for c in rows})
        lines = await _line_names(s, actor.workspace_id)
    return {"claims": [{"ref": c.ref, "employee": names.get(c.beneficiary_party_id), "merchant": c.merchant, "description": c.description,
                        "amount": format_inr(c.amount_paise), "amount_paise": c.amount_paise, "date": c.business_date.isoformat(),
                        "category": lines.get(c.line_id), "state": c.state, "settlement_state": c.settlement_state,
                        "document_id": c.document_id, "reservation": bool(c.reservation_id)} for c in rows]}


@router.get("/api/bills")
async def list_bills(actor: Actor = auth.ActorDep) -> dict:
    if not actor.is_approver:
        raise HTTPException(403, "Finance approvers only")
    async with db.session_scope() as s:
        rows = (await s.execute(select(Bill).where(Bill.workspace_id == actor.workspace_id).order_by(Bill.business_date.desc()).limit(50))).scalars().all()
        names = await _party_names(s, {b.vendor_party_id for b in rows})
        lines = await _line_names(s, actor.workspace_id)
    return {"bills": [{"ref": b.ref, "vendor": names.get(b.vendor_party_id), "invoice_no": b.invoice_no, "description": b.description,
                       "amount": format_inr(b.amount_paise), "amount_paise": b.amount_paise, "date": b.business_date.isoformat(),
                       "due": b.due_date.isoformat() if b.due_date else None, "category": lines.get(b.line_id), "state": b.state,
                       "settlement_state": b.settlement_state, "document_id": b.document_id} for b in rows]}


@router.get("/api/payments")
async def list_payments(actor: Actor = auth.ActorDep) -> dict:
    """Recorded settlements (money moved outside Purser), company-card payments, and approved-but-unpaid items.
    Purser never moves money: 'awaiting_payment' means approved, not paid."""
    if not actor.is_approver:
        raise HTTPException(403, "Finance approvers only")
    async with db.session_scope() as s:
        st = (await s.execute(select(Settlement).where(Settlement.workspace_id == actor.workspace_id).order_by(Settlement.business_date.desc()).limit(30))).scalars().all()
        bill_refs = dict((await s.execute(select(Bill.id, Bill.ref).where(Bill.id.in_({x.record_id for x in st if x.record_type == "bill"})))).all()) if st else {}
        claim_refs = dict((await s.execute(select(Claim.id, Claim.ref).where(Claim.id.in_({x.record_id for x in st if x.record_type == "claim"})))).all()) if st else {}
        cp = (await s.execute(select(CompanyPayment).where(CompanyPayment.workspace_id == actor.workspace_id).order_by(CompanyPayment.paid_on.desc()))).scalars().all()
        due_b = (await s.execute(select(Bill).where(Bill.workspace_id == actor.workspace_id, Bill.state == "approved", Bill.settlement_state == "unpaid"))).scalars().all()
        due_c = (await s.execute(select(Claim).where(Claim.workspace_id == actor.workspace_id, Claim.state == "approved", Claim.settlement_state == "unpaid"))).scalars().all()
        names = await _party_names(s, {b.vendor_party_id for b in due_b} | {c.beneficiary_party_id for c in due_c})
    out = [{"id": f"S{x.id}", "status": "settled", "record": (bill_refs if x.record_type == "bill" else claim_refs).get(x.record_id),
            "payee": None, "amount": format_inr(x.amount_paise), "date": x.business_date.isoformat(), "reference": x.reference,
            "method": "Recorded payment"} for x in st]
    out += [{"id": f"CP{x.id}", "status": "settled", "record": None, "payee": x.payee_name, "amount": format_inr(x.amount_paise),
             "date": x.paid_on.isoformat(), "reference": x.reference, "method": "Company card"} for x in cp]
    due = [{"id": b.ref, "status": "awaiting_payment", "record": b.ref, "payee": names.get(b.vendor_party_id), "amount": format_inr(b.amount_paise),
            "date": (b.due_date or b.business_date).isoformat(), "reference": None, "method": "Vendor bill"} for b in due_b]
    due += [{"id": c.ref, "status": "awaiting_payment", "record": c.ref, "payee": names.get(c.beneficiary_party_id), "amount": format_inr(c.amount_paise),
             "date": c.business_date.isoformat(), "reference": None, "method": "Reimbursement"} for c in due_c]
    return {"awaiting": due, "history": sorted(out, key=lambda r: r["date"], reverse=True)}


@router.get("/api/budget/lines")
async def list_budget_lines(actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        lines = (await s.execute(select(BudgetLine).where(BudgetLine.workspace_id == actor.workspace_id).order_by(BudgetLine.category))).scalars().all()
        out = []
        for ln in lines:
            p = await budget.position(s, actor.workspace_id, ln.id)
            out.append({"line_id": ln.id, "category": ln.category, "department": ln.department, "fy": ln.fy,
                        **{k: v for k, v in p.items()}, **{k.replace("_paise", ""): format_inr(v) for k, v in p.items()}})
    return {"lines": out}


@router.get("/api/trips")
async def list_trips(actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        q = select(Trip).where(Trip.workspace_id == actor.workspace_id)
        if not actor.is_approver:
            q = q.where(Trip.employee_party_id == actor.party_id)
        trips = (await s.execute(q.order_by(Trip.start_date.desc()))).scalars().all()
        names = await _party_names(s, {t.employee_party_id for t in trips})
        res = (await s.execute(select(Reservation).where(Reservation.workspace_id == actor.workspace_id,
                                                         Reservation.trip_id.in_({t.id for t in trips})))).scalars().all() if trips else []
        claims = (await s.execute(select(Claim).where(Claim.workspace_id == actor.workspace_id,
                                                      Claim.reservation_id.in_({r.id for r in res})))).scalars().all() if res else []
    by_res = {c.reservation_id: c for c in claims}
    return {"trips": [{"id": t.id, "employee": names.get(t.employee_party_id), "city": t.city, "purpose": t.purpose,
                       "start": t.start_date.isoformat(), "end": t.end_date.isoformat(),
                       "reservations": [{"ref": r.ref, "description": r.description, "amount": format_inr(r.amount_paise), "status": r.status,
                                         "claim": ({"ref": by_res[r.id].ref, "state": by_res[r.id].state, "amount": format_inr(by_res[r.id].amount_paise)}
                                                   if r.id in by_res else None)}
                                        for r in res if r.trip_id == t.id]} for t in trips]}


@router.get("/api/priorities")
async def priorities(actor: Actor = auth.ActorDep) -> dict:
    from app.services import budget_months as bm
    from app.services.records import today_ist
    async with db.session_scope() as s:
        approvals = reimb = 0
        if actor.is_approver:
            approvals = (await s.execute(select(func.count()).select_from(Claim).where(Claim.workspace_id == actor.workspace_id, Claim.state == "submitted"))).scalar_one()
            approvals += (await s.execute(select(func.count()).select_from(Bill).where(Bill.workspace_id == actor.workspace_id, Bill.state == "submitted"))).scalar_one()
            reimb = (await s.execute(select(func.count()).select_from(Claim).where(Claim.workspace_id == actor.workspace_id, Claim.state == "approved",
                                                                                    Claim.settlement_state == "unpaid"))).scalar_one()
        pending_claims = (await s.execute(select(func.count()).select_from(Claim).where(Claim.workspace_id == actor.workspace_id, Claim.state == "submitted"))).scalar_one() if actor.is_approver else 0
        try:
            al = await bm.alerts(s, actor, today_ist())
            alerts = len(al.get("alerts", []))
        except DomainError:
            alerts = 0
        unread = (await s.execute(select(func.count()).select_from(Message).where(Message.workspace_id == actor.workspace_id,
                                                                                    Message.recipient_user_id == actor.user_id,
                                                                                    Message.channel == "inbox", Message.read_at.is_(None)))).scalar_one()
    return {"approvals": int(approvals), "reimbursements": int(reimb), "budget_alerts": alerts, "claims_pending": int(pending_claims),
            "unread_mail": int(unread)}


@router.get("/api/budget/alerts")
async def budget_alerts(actor: Actor = auth.ActorDep) -> dict:
    from app.services import budget_months as bm
    from app.services.records import today_ist
    async with db.session_scope() as s:
        return await bm.alerts(s, actor, today_ist())


# ------------------------------------------------------------------ mail


@router.get("/api/people")
async def people_directory(actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        rows = (await s.execute(select(User).where(User.workspace_id == actor.workspace_id).order_by(User.display_name))).scalars().all()
    return {"people": [{"id": u.id, "name": u.display_name, "department": u.department, "designation": u.designation}
                       for u in rows if u.id != actor.user_id]}


@router.get("/api/messages/sent")
async def sent_messages(actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        rows = (await s.execute(select(Message, User.display_name).join(User, User.id == Message.recipient_user_id, isouter=True)
                                .where(Message.workspace_id == actor.workspace_id, Message.sender_id == actor.user_id)
                                .order_by(Message.id.desc()).limit(60))).all()
    batches: dict[str, dict] = {}
    for m, name in rows:
        b = batches.setdefault(m.batch_id or m.ref, {"ref": m.ref, "subject": m.subject, "body": m.body, "kind": m.kind,
                                                      "at": m.created_at.isoformat(), "to": [], "email": []})
        if m.channel == "inbox" and name and name not in b["to"]:
            b["to"].append(name)
        if m.channel == "email":
            b["email"].append({"status": m.status, "detail": m.status_detail})
    return {"messages": list(batches.values())[:20]}


@router.post("/api/inbox/{ref}/read")
async def mark_read(ref: str, actor: Actor = auth.ActorDep) -> dict:
    from datetime import UTC, datetime
    async with db.session_scope() as s:
        m = (await s.execute(select(Message).where(Message.workspace_id == actor.workspace_id, Message.recipient_user_id == actor.user_id,
                                                   Message.ref == ref, Message.channel == "inbox"))).scalars().first()
        if m is None:
            raise HTTPException(404, "Message not found")
        m.read_at = m.read_at or datetime.now(UTC)
    return {"ref": ref, "unread": False}


class DraftIn(BaseModel):
    user_ids: list[int] = Field(min_length=1, max_length=50)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    email: bool = False


@router.post("/api/messages/draft", status_code=201)
async def draft_message(body: DraftIn, actor: Actor = auth.ActorDep) -> dict:
    """Prepare a send_message proposal from the mail composer. Nothing is sent until the proposal is confirmed."""
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, "send_message", {"audience": "person", "user_ids": body.user_ids, "subject": body.subject,
                                                              "body": body.body, "department": None,
                                                              "channels": ["inbox", "email"] if body.email else ["inbox"]})
        return {"proposal_id": p.id, "preview": p.preview}


@router.get("/api/documents")
async def list_documents(actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        q = select(Document).where(Document.workspace_id == actor.workspace_id)
        if not actor.is_approver:
            q = q.where(Document.uploader_id == actor.user_id)
        rows = (await s.execute(q.order_by(Document.id.desc()).limit(30))).scalars().all()
    return {"documents": [{"id": d.id, "filename": d.filename, "status": d.status, "outcome": d.outcome, "at": d.created_at.isoformat()} for d in rows]}


@router.post("/api/records/{ref}/prepare-approval", status_code=201)
async def prepare_approval(ref: str, actor: Actor = auth.ActorDep) -> dict:
    """PREPARE_APPROVAL from the UI: builds the same 'approve' proposal the agent would. Executes only on Confirm."""
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, "approve", {"ref": ref.strip().upper()})
        return {"proposal_id": p.id, "preview": p.preview}
