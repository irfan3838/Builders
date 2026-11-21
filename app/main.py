"""FastAPI app: auth, upload, agent turns, button confirmation, source previews, health."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile  # noqa: E402
from fastapi.responses import JSONResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from app import auth, db  # noqa: E402
from app.actor import Actor  # noqa: E402
from app.agent.runner import run_turn  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.errors import DomainError  # noqa: E402
from app.models import Conversation, Proposal, Receipt  # noqa: E402
from app.money import format_inr  # noqa: E402
from app.services import budget, intake, proposals, records, storage  # noqa: E402

logging.basicConfig(level=get_settings().log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    import asyncio

    from app.services import messaging

    async def sweeper():  # backstop: deliver any queued email left by a crash or restart
        while True:
            try:
                await messaging.dispatch()
            except Exception:
                logging.getLogger("munshi.messaging").exception("dispatch sweep failed")
            await asyncio.sleep(30)

    task = asyncio.create_task(sweeper())
    yield
    task.cancel()


app = FastAPI(title="Munshi", docs_url=None, redoc_url=None, lifespan=lifespan)


@app.exception_handler(DomainError)
async def domain_error(_: Request, e: DomainError) -> JSONResponse:
    status = {"NOT_FOUND": 404, "FORBIDDEN": 403}.get(e.code, 409)
    return JSONResponse(e.as_dict(), status_code=status)


@app.middleware("http")
async def no_shared_cache(request: Request, call_next):
    resp = await call_next(request)
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, private"
    return resp


@app.get("/health")
async def health() -> dict:
    async with db.engine().connect() as c:
        await c.execute(text("select 1"))
    return {"ok": True}


class LoginIn(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


@app.post("/api/auth/login")
async def login(body: LoginIn, response: Response, request: Request) -> dict:
    origin = request.headers.get("origin")
    if origin and origin != get_settings().app_origin:
        raise HTTPException(403, "Unexpected origin")
    return await auth.login(response, body.email, body.password)


@app.post("/api/auth/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(auth.COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request, actor: Actor = auth.ActorDep) -> dict:
    return {"id": actor.user_id, "name": actor.display_name, "role": actor.role, "csrf": await auth.current_csrf(request)}


@app.post("/api/conversations", status_code=201)
async def new_conversation(actor: Actor = auth.ActorDep, channel: str = "text") -> dict:
    if channel not in ("text", "live", "realtime", "ptt"):
        raise HTTPException(400, "bad channel")
    async with db.session_scope() as s:
        c = Conversation(workspace_id=actor.workspace_id, user_id=actor.user_id, channel=channel)
        s.add(c)
        await s.flush()
        return {"conversation_id": c.id}


@app.post("/api/documents", status_code=201)
async def upload(file: UploadFile = File(...), actor: Actor = auth.ActorDep, announce: bool = False) -> dict:
    limit = get_settings().upload_max_bytes
    data = await file.read(limit + 1)
    async with db.session_scope() as s:
        r = await intake.accept_upload(s, actor, file.filename or "upload", data)
        if r.document_id and actor.conversation_id:
            c = await s.get(Conversation, actor.conversation_id)
            if c:
                c.current_document_id = r.document_id
    out = {"document_id": r.document_id, "outcome": r.outcome, "message": r.message, "existing": r.existing, "reply": None, "ui": []}
    if announce and actor.conversation_id:
        from app.voice import live_bridge
        bridge = live_bridge.bridge_for(actor.conversation_id)
        if r.document_id and r.outcome == "accepted":
            from app.agent import reading
            reading.prefetch(actor, r.document_id)  # start reading now, in parallel with the agent's first step
            if bridge:
                await bridge.speak("The user just handed you a document. Say only a short acknowledgement like "
                                   "'Mil gaya, padh raha hoon' — the details follow in a moment.")
        note = (f"(App event, not words spoken by the user) The user just uploaded '{file.filename}'. Upload result: {r.outcome}"
                + (f", document_id={r.document_id}" if r.document_id else "") + f". {r.message} "
                + ("Inspect it and briefly tell the user what it is, then ask the next question." if r.outcome == "accepted"
                   else "Tell the user this outcome in their language."))
        if bridge:
            async with bridge.lock:  # keep turn order with spoken delegations
                t = await run_turn(actor, note, channel="live", record_turn=False)
            await bridge.speak(t.reply)
        else:
            t = await run_turn(actor, note, channel="text", record_turn=False)
        out.update(reply=t.reply, ui=t.ui)
    return out


@app.get("/api/documents/{document_id}/pages/{page}")
async def document_page(document_id: int, page: int, actor: Actor = auth.ActorDep) -> StreamingResponse:
    async with db.session_scope() as s:
        doc = await records.document(s, actor, document_id)
        key, media, pages = doc.storage_key, doc.media_type, doc.pages
    if not 1 <= page <= pages:
        raise HTTPException(404, "No such page")
    png = intake.render_pages(await storage.get(key), media, scale=1.5, max_pages=page)[page - 1]
    out_media = "image/png" if media == "application/pdf" else media
    return StreamingResponse(io.BytesIO(png), media_type=out_media, headers={"Cache-Control": "private, max-age=300"})


class TurnIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@app.post("/api/agent/text")
async def agent_text(body: TurnIn, actor: Actor = auth.ActorDep) -> dict:
    if not actor.conversation_id:
        raise HTTPException(400, "X-Conversation-Id header required")
    r = await run_turn(actor, body.text, channel="text", source="text")
    return {"reply": r.reply, "ui": r.ui, "tools": r.tools, "latency_ms": r.latency_ms}


@app.get("/api/proposals/{proposal_id}")
async def get_proposal(proposal_id: str, actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        p = await proposals.load(s, actor, proposal_id)
        return {"id": p.id, "kind": p.kind, "status": p.status, "preview": p.preview, "expires_at": p.expires_at.isoformat(),
                "receipt_id": p.receipt_id}


@app.post("/api/proposals/{proposal_id}/confirm")
async def confirm_button(proposal_id: str, actor: Actor = auth.ActorDep) -> dict:
    """User-operated Confirm button: explicit intent from an authenticated, CSRF-checked click."""
    from app.services import messaging
    async with db.session_scope() as s:
        out = await proposals.confirm(s, actor, proposal_id, via="button", evidence={"channel": "button"})
        r = out.receipt
        body = {"status": out.status, "receipt": {"id": r.id, "ref": r.ref, "summary": r.summary, "effects": r.effects} if r else None,
                "new_proposal_id": out.new_proposal.id if out.new_proposal else None}
    messaging.dispatch_soon()
    return body


@app.post("/api/proposals/{proposal_id}/cancel")
async def cancel_button(proposal_id: str, actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        p = await proposals.cancel(s, actor, proposal_id)
        return {"status": p.status}


@app.get("/api/receipts/{receipt_id}")
async def get_receipt(receipt_id: int, actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        r = (await s.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.workspace_id == actor.workspace_id))).scalars().first()
        if r is None or (not actor.is_approver and r.actor_id != actor.user_id):
            raise HTTPException(404, "Receipt not found")
        p = await s.get(Proposal, r.proposal_id)
        return {"id": r.id, "ref": r.ref, "summary": r.summary, "effects": r.effects, "confirmed_via": r.confirmed_via,
                "created_at": r.created_at.isoformat(), "preview": p.preview if p else None}


# ---------------------------------------------------------------- card data (cards reference server objects)


@app.get("/api/documents/{document_id}")
async def document_detail(document_id: int, actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        d = await records.document(s, actor, document_id)
        ex = await records.extraction(s, actor, d.id)
        out = {"id": d.id, "filename": d.filename, "media_type": d.media_type, "pages": d.pages, "status": d.status,
               "outcome": d.outcome, "outcome_reason": d.outcome_reason, "extraction": None}
        if d.outcome in ("claim", "bill"):
            out["record"] = await intake.describe_outcome(s, actor, d)
        if ex:
            f = records.effective_fields(ex)
            out["extraction"] = {
                "doc_type": ex.doc_type, "arithmetic": ex.arithmetic, "evidence": ex.evidence, "corrections": ex.corrections,
                "fields": {"vendor": f.get("vendor"), "date": f.get("date"), "total": format_inr(f["total_paise"]) if f.get("total_paise") else None,
                           "invoice_no": f.get("invoice_no"), "due_date": f.get("due_date"), "customer_or_guest": f.get("customer_or_guest"),
                           "payment_status": f.get("payment_status"),
                           "breakdown_sum": format_inr(b) if (b := intake.breakdown_sum(f)) is not None else None},
            }
        return out


@app.get("/api/budget/lines/{line_id}")
async def budget_line(line_id: int, actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        line = await budget.get_line(s, actor.workspace_id, line_id=line_id)
        p = await budget.position(s, actor.workspace_id, line.id)
        mv = await budget.movements(s, actor.workspace_id, line.id, limit=8)
        refs = dict((await s.execute(select(Receipt.id, Receipt.ref).where(Receipt.id.in_({m.receipt_id for m in mv if m.receipt_id}))))
                    .all()) if mv else {}
    return {"line_id": line.id, "category": line.category, "department": line.department, "fy": line.fy,
            "position": {k: {"paise": v, "inr": format_inr(v)} for k, v in p.items()},
            "movements": [{"id": m.id, "bucket": m.bucket, "amount": format_inr(m.amount_paise), "amount_paise": m.amount_paise,
                           "kind": m.kind, "memo": m.memo, "receipt": refs.get(m.receipt_id), "at": m.created_at.isoformat()} for m in mv]}


@app.get("/api/records/{ref}")
async def record_detail(ref: str, actor: Actor = auth.ActorDep) -> dict:
    from app.models import Claim
    async with db.session_scope() as s:
        r = await records.record_by_ref(s, actor, ref)
        is_claim = isinstance(r, Claim)
        party = await records.party(s, actor, r.beneficiary_party_id if is_claim else r.vendor_party_id)
        line = await budget.get_line(s, actor.workspace_id, line_id=r.line_id)
    return {"ref": r.ref, "type": "claim" if is_claim else "bill", "party": party.name, "amount": format_inr(r.amount_paise),
            "business_date": r.business_date.isoformat(), "category": line.category, "state": r.state,
            "settlement_state": r.settlement_state, "document_id": r.document_id,
            "detail": r.merchant if is_claim else (r.invoice_no or r.description)}


@app.get("/api/audit")
async def audit_feed(actor: Actor = auth.ActorDep, ref: str | None = None) -> dict:
    from app.models import AuditEvent, User
    if not actor.is_approver:
        raise HTTPException(403, "Finance approvers only")
    async with db.session_scope() as s:
        q = select(AuditEvent, User.display_name).join(User, User.id == AuditEvent.actor_id, isouter=True).where(
            AuditEvent.workspace_id == actor.workspace_id, AuditEvent.action.notlike("proposal.%"))
        if ref:
            q = q.where(AuditEvent.record_ref == ref.upper())
        rows = (await s.execute(q.order_by(AuditEvent.id.desc()).limit(25))).all()
        rec = dict((await s.execute(select(Receipt.id, Receipt.ref).where(Receipt.id.in_({e.receipt_id for e, _ in rows if e.receipt_id}))))
                   .all()) if rows else {}
    return {"events": [{"id": e.id, "at": e.created_at.isoformat(), "action": e.action, "record": e.record_ref, "by": name,
                        "receipt": rec.get(e.receipt_id), "after": e.after} for e, name in rows]}


@app.get("/api/inbox")
async def inbox(actor: Actor = auth.ActorDep) -> dict:
    from app.models import Message, User
    async with db.session_scope() as s:
        rows = (await s.execute(select(Message, User.display_name).join(User, User.id == Message.sender_id, isouter=True).where(
            Message.workspace_id == actor.workspace_id, Message.recipient_user_id == actor.user_id, Message.channel == "inbox")
            .order_by(Message.id.desc()).limit(10))).all()
    return {"messages": [{"ref": m.ref, "from": n or "Munshi", "subject": m.subject, "body": m.body, "kind": m.kind,
                          "unread": m.read_at is None, "at": m.created_at.isoformat()} for m, n in rows]}


@app.get("/api/people/{user_id}/leave")
async def leave_card(user_id: int, actor: Actor = auth.ActorDep) -> dict:
    from app.services import people
    async with db.session_scope() as s:
        u = await people.user(s, actor, user_id)
        if not people.can_view_person_private(actor, u):
            raise HTTPException(404, "Not found")
        bal = await people.balance(s, actor.workspace_id, u.id)
    return {"user_id": u.id, "name": u.display_name, "balances": bal}


@app.get("/api/leave-requests")
async def leave_requests_card(actor: Actor = auth.ActorDep, scope: str = "mine") -> dict:
    from app.services import people
    if scope not in ("mine", "awaiting_my_decision", "team"):
        raise HTTPException(400, "bad scope")
    async with db.session_scope() as s:
        rows = await people.leave_requests(s, actor, scope)
    return {"scope": scope, "requests": [{"ref": lr.ref, "person": u.display_name, "type": lr.leave_type, "from": lr.start_date.isoformat(),
                                          "to": lr.end_date.isoformat(), "days": lr.days, "state": lr.state} for lr, u in rows]}


@app.get("/api/people/{user_id}")
async def person_card(user_id: int, actor: Actor = auth.ActorDep) -> dict:
    from app.models import User
    from app.services import people
    async with db.session_scope() as s:
        u = await people.user(s, actor, user_id)
        private = people.can_view_person_private(actor, u)
        mgr = await s.get(User, u.reports_to_id) if u.reports_to_id else None
        tasks = await people.onboarding_tasks(s, actor.workspace_id, u.id) if private else []
    return {"user_id": u.id, "name": u.display_name, "designation": u.designation, "department": u.department,
            "manager": mgr.display_name if mgr else None, "start_date": u.start_date.isoformat() if (private and u.start_date) else None,
            "status": u.status if private else None,
            "tasks": [{"title": t.title, "owner": t.owner, "due": t.due_date.isoformat() if t.due_date else None, "status": t.status} for t in tasks]}


@app.get("/api/receipts/{receipt_id}/deliveries")
async def receipt_deliveries(receipt_id: int, actor: Actor = auth.ActorDep) -> dict:
    from app.models import Message, User
    async with db.session_scope() as s:
        r = (await s.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.workspace_id == actor.workspace_id))).scalars().first()
        if r is None or (not actor.is_approver and not actor.is_hr and r.actor_id != actor.user_id):
            raise HTTPException(404, "Receipt not found")
        rows = (await s.execute(select(Message, User.display_name).join(User, User.id == Message.recipient_user_id, isouter=True)
                                .where(Message.receipt_id == r.id).order_by(Message.id))).all()
    return {"deliveries": [{"ref": m.ref, "to": n, "channel": m.channel, "status": m.status, "detail": m.status_detail} for m, n in rows]}


class SDPIn(BaseModel):
    sdp: str = Field(min_length=1, max_length=65536)
    wake_text: str | None = Field(None, max_length=500)


@app.post("/api/voice/session", status_code=201)
async def voice_session(body: SDPIn, actor: Actor = auth.ActorDep) -> dict:
    """Exchange the browser's WebRTC offer for a GPT-Live answer; the backend attaches a sideband."""
    from openai import APIError

    from app.voice import live_bridge
    if not actor.conversation_id:
        raise HTTPException(400, "X-Conversation-Id header required")
    try:
        return await live_bridge.start(actor, body.sdp, body.wake_text)
    except APIError as e:
        logging.getLogger("munshi.live").error("live.create failed: %s", getattr(e, "status_code", "?"))
        raise HTTPException(502, "Voice session could not start. Use push-to-talk or type instead.") from e


@app.get("/api/events")
async def event_stream(request: Request, actor: Actor = auth.ActorDep) -> StreamingResponse:
    """Server-sent events for this conversation: cards, user/assistant turns."""
    import asyncio
    import json

    from app import events
    if not actor.conversation_id:
        raise HTTPException(400, "X-Conversation-Id header required")
    q = events.subscribe(actor.conversation_id)

    async def gen():
        try:
            yield ": connected\n\n"
            while not await request.is_disconnected():
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"id: {ev['id']}\ndata: {json.dumps(ev, ensure_ascii=False, default=str)}\n\n"
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            events.unsubscribe(actor.conversation_id, q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


_web = Path(__file__).resolve().parent.parent / "web" / "dist"
if _web.is_dir():
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
