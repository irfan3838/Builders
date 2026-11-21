"""People-ops tools: directory, leave, onboarding, messages/announcements, inbox, HR policy answers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from agents import RunContextWrapper, function_tool
from sqlalchemy import select

from app import db
from app.agent.context import MunshiContext, safe_tool
from app.agent.tools.proposals import _propose
from app.models import Message, User
from app.services import people

Ctx = RunContextWrapper[MunshiContext]


def _person(u: User, private: bool) -> dict:
    d = {"user_id": u.id, "name": u.display_name, "department": u.department, "designation": u.designation}
    if private:
        d.update(email=u.email, start_date=u.start_date.isoformat() if u.start_date else None, status=u.status,
                 reports_to_id=u.reports_to_id, role=u.role)
    return d


@function_tool
@safe_tool
async def find_people(ctx: Ctx, name: str | None = None, department: str | None = None) -> dict:
    """Look up colleagues by spoken name and/or department. Several close matches mean: ask which one."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        found = await people.find_people(s, a, name, department)
        out = [_person(u, people.can_view_person_private(a, u)) for u in found[:8]]
    return {"ok": True, "people": out, "ambiguous": bool(name) and len(out) > 1}


@function_tool
@safe_tool
async def get_leave_balance(ctx: Ctx, user_id: int | None = None) -> dict:
    """Leave balance (CL, SL, EL: granted, held for pending requests, used, available). Defaults to the speaker."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        u = await people.user(s, a, user_id or a.user_id)
        if not people.can_view_person_private(a, u):
            return {"ok": False, "code": "FORBIDDEN", "message": "You can only see your own or your team's leave."}
        bal = await people.balance(s, a.workspace_id, u.id)
    ctx.context.show({"card": "leave", "user_id": u.id})
    return {"ok": True, "person": u.display_name, "balances": bal, "basis": "working days; available = granted − held − used"}


@function_tool
@safe_tool
async def list_leave_requests(ctx: Ctx, scope: Literal["mine", "awaiting_my_decision", "team"] = "mine") -> dict:
    """Leave requests: the speaker's own, those waiting for their decision (manager/HR), or their team's."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        rows = await people.leave_requests(s, a, scope)
    items = [{"ref": lr.ref, "person": u.display_name, "type": lr.leave_type, "from": lr.start_date.isoformat(),
              "to": lr.end_date.isoformat(), "days": lr.days, "state": lr.state, "reason": lr.reason} for lr, u in rows]
    ctx.context.show({"card": "leave_requests", "scope": scope})
    return {"ok": True, "requests": items}


@function_tool
@safe_tool
async def propose_leave(ctx: Ctx, leave_type: Literal["CL", "SL", "EL"], start_date: str, end_date: str | None = None,
                        reason: str | None = None, user_id: int | None = None) -> dict:
    """Propose a leave application (CL casual, SL sick, EL earned). Dates YYYY-MM-DD; resolve 'kal', 'next Monday'
    against today's date in your instructions. user_id only when HR applies on someone's behalf."""
    return await _propose(ctx, "apply_leave", {"leave_type": leave_type, "start_date": start_date, "end_date": end_date,
                                               "reason": reason, "user_id": user_id})


@function_tool
@safe_tool
async def propose_leave_decision(ctx: Ctx, ref: str, decision: Literal["approve", "reject"], note: str | None = None) -> dict:
    """Propose approving or rejecting a leave request (L…). The employee is notified after confirmation."""
    kind = "approve" if decision == "approve" else "reject_leave"
    return await _propose(ctx, kind, {"ref": ref, "note": note})


@function_tool
@safe_tool
async def propose_onboarding(ctx: Ctx, name: str, designation: str, department: str, start_date: str,
                             manager_user_id: int | None = None, work_email: str | None = None,
                             personal_email: str | None = None) -> dict:
    """Propose onboarding a new employee: login, department, manager, leave balances, onboarding checklist and a
    welcome message. Resolve the manager with find_people first. personal_email only if the user gave one."""
    return await _propose(ctx, "onboard_employee", {"name": name, "designation": designation, "department": department,
                                                    "start_date": start_date, "manager_user_id": manager_user_id,
                                                    "work_email": work_email, "personal_email": personal_email})


@function_tool
@safe_tool
async def propose_message(ctx: Ctx, audience: Literal["person", "department", "all"], subject: str, body: str,
                          user_ids: list[int] | None = None, department: str | None = None,
                          channels: list[Literal["inbox", "email"]] | None = None) -> dict:
    """Propose sending a message or announcement. Draft the subject and body yourself in the user's language and
    tone; the preview shows exact text, recipients and channels. channels default to the Munshi inbox; add 'email'
    when the user asks for email."""
    return await _propose(ctx, "send_message", {"audience": audience, "subject": subject, "body": body, "user_ids": user_ids,
                                                "department": department, "channels": channels or ["inbox"]})


@function_tool
@safe_tool
async def read_inbox(ctx: Ctx, unread_only: bool = True, limit: int = 5) -> dict:
    """The speaker's Munshi inbox (announcements, leave decisions, messages), newest first. Marks returned items read."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        q = select(Message, User.display_name).join(User, User.id == Message.sender_id, isouter=True).where(
            Message.workspace_id == a.workspace_id, Message.recipient_user_id == a.user_id, Message.channel == "inbox")
        if unread_only:
            q = q.where(Message.read_at.is_(None))
        rows = (await s.execute(q.order_by(Message.id.desc()).limit(max(1, min(limit, 20))))).all()
        now = datetime.now(UTC)
        for m, _ in rows:
            m.read_at = m.read_at or now
    ctx.context.show({"card": "inbox"})
    return {"ok": True, "messages": [{"ref": m.ref, "from": name or "Munshi", "subject": m.subject, "body": m.body,
                                      "at": m.created_at.isoformat()} for m, name in rows]}


@function_tool
@safe_tool
async def get_onboarding_status(ctx: Ctx, user_id: int) -> dict:
    """Onboarding checklist for a new joiner: each task, owner, due date and status."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        u = await people.user(s, a, user_id)
        if not people.can_view_person_private(a, u):
            return {"ok": False, "code": "FORBIDDEN", "message": "Not visible to you."}
        tasks = await people.onboarding_tasks(s, a.workspace_id, u.id)
    ctx.context.show({"card": "person", "user_id": u.id})
    return {"ok": True, "person": u.display_name, "status": u.status,
            "tasks": [{"task": t.title, "owner": t.owner, "due": t.due_date.isoformat() if t.due_date else None, "status": t.status} for t in tasks]}


@function_tool
@safe_tool
async def lookup_policy(ctx: Ctx, question: str) -> dict:
    """Search the company's HR/finance policy handbook. Answer ONLY from the returned sections and cite the code
    (e.g. HR-3.1). If nothing relevant comes back, say the handbook does not cover it."""
    async with db.session_scope() as s:
        found = await people.search_policies(s, ctx.context.actor.workspace_id, question)
    return {"ok": True, "sections": [{"code": p.code, "title": p.title, "text": p.body} for p in found]}


TOOLS = [find_people, get_leave_balance, list_leave_requests, propose_leave, propose_leave_decision, propose_onboarding,
         propose_message, read_inbox, get_onboarding_status, lookup_policy]
