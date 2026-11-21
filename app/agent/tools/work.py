"""Tasks (to-dos) and helpdesk tickets for everyone. Own to-dos are saved directly; anything that notifies other people
(assigning a task, raising or resolving a ticket) is proposed and confirmed."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from agents import RunContextWrapper, function_tool

from app import db
from app.agent.context import PurserContext, safe_tool
from app.agent.tools.proposals import _propose
from app.errors import INVALID_STATE, DomainError
from app.rbac import require_writer
from app.services import work

Ctx = RunContextWrapper[PurserContext]


@function_tool
@safe_tool
async def list_tasks(ctx: Ctx, scope: Literal["mine", "team", "assigned_by_me"] = "mine", include_done: bool = False) -> dict:
    """Open tasks: mine (default), my team's (managers/HR), or ones I assigned to others. Overdue first."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        rows = await work.tasks(s, a, scope, include_done)
        nm = await work.names(s, a.workspace_id)
    items = [work.task_view(t, nm) for t in rows]
    ctx.context.show({"card": "tasks", "scope": scope, "items": items})
    return {"ok": True, "count": len(items), "tasks": items}


@function_tool
@safe_tool
async def add_task(ctx: Ctx, title: str, due_on: str | None = None, priority: Literal["low", "normal", "high"] = "normal",
                   notes: str | None = None) -> dict:
    """Add a to-do for the speaker ('remind me to send the deck by Friday' -> due_on YYYY-MM-DD from today).
    Saved directly (it only affects the speaker). Say the task and date back."""
    async with db.session_scope() as s:
        t = await work.add_task(s, ctx.context.actor, title, due_on, priority, notes)
        out = work.task_view(t)
    return {"ok": True, "task": out}


@function_tool
@safe_tool
async def complete_task(ctx: Ctx, ref: str) -> dict:
    """Mark one of the speaker's tasks done (T…)."""
    a = ctx.context.actor
    require_writer(a)
    async with db.session_scope() as s:
        t = await work.task_by_ref(s, a, ref)
        if t.status == "done":
            raise DomainError(INVALID_STATE, f"{t.ref} is already done.")
        t.status, t.done_at = "done", datetime.now(UTC)
        out = work.task_view(t)
    return {"ok": True, "task": out}


@function_tool
@safe_tool
async def propose_assign_task(ctx: Ctx, assignee_user_id: int, title: str, due_on: str | None = None,
                              priority: Literal["low", "normal", "high"] = "normal", notes: str | None = None) -> dict:
    """Propose giving a task to someone in your team (find_people for the user id). They are notified on confirm."""
    return await _propose(ctx, "assign_task", {"assignee_user_id": assignee_user_id, "title": title, "due_on": due_on,
                                               "priority": priority, "notes": notes})


@function_tool
@safe_tool
async def list_tickets(ctx: Ctx, scope: Literal["mine", "all"] = "mine") -> dict:
    """Helpdesk tickets: mine (raised by or assigned to me) or all (admin/HR team)."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        rows = await work.tickets(s, a, scope)
        nm = await work.names(s, a.workspace_id)
    items = [work.ticket_view(t, nm) for t in rows]
    ctx.context.show({"card": "tickets", "scope": scope, "items": items})
    return {"ok": True, "count": len(items), "tickets": items}


@function_tool
@safe_tool
async def propose_ticket(ctx: Ctx, category: Literal["it", "admin", "facilities", "hr", "finance"], title: str,
                         description: str | None = None, priority: Literal["low", "normal", "high"] = "normal") -> dict:
    """Propose raising a helpdesk ticket ('my laptop won't charge', 'need VPN access', 'AC not working in room 3').
    Write a clear one-line title yourself and put the details in description. The admin team is notified on confirm."""
    return await _propose(ctx, "raise_ticket", {"category": category, "title": title, "description": description, "priority": priority})


@function_tool
@safe_tool
async def propose_ticket_update(ctx: Ctx, ref: str, status: Literal["open", "in_progress", "resolved"], resolution: str | None = None) -> dict:
    """Admin/HR: propose changing a ticket's status (HD…), with a short resolution note for the requester."""
    return await _propose(ctx, "update_ticket", {"ref": ref, "status": status, "resolution": resolution})


TOOLS = [list_tasks, add_task, complete_task, propose_assign_task, list_tickets, propose_ticket, propose_ticket_update]
