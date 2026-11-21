"""Tasks (to-dos) and helpdesk tickets.

Own to-dos are saved directly (like reminders). Assigning a task to someone else, raising a ticket and resolving a
ticket go through propose -> confirm, because they notify other people.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import or_, select

from app.actor import Actor
from app.errors import FORBIDDEN, INVALID_STATE, NOT_FOUND, VALIDATION, DomainError
from app.models import Task, Ticket, User
from app.rbac import require_writer
from app.services import audit, messaging, people
from app.services.actions import Execution, Plan

PRIORITIES = ("low", "normal", "high")
CATEGORIES = {"it": "IT", "admin": "Admin", "facilities": "Facilities", "hr": "HR", "finance": "Finance"}
STATUSES = ("open", "in_progress", "resolved")


def parse_due(v: str | None) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise DomainError(VALIDATION, "Give the due date as YYYY-MM-DD (resolve 'Friday' from today first).") from None


def task_view(t: Task, names: dict[int, str] | None = None) -> dict:
    return {"ref": t.ref, "title": t.title, "notes": t.notes, "due_on": t.due_on.isoformat() if t.due_on else None,
            "priority": t.priority, "status": t.status, "assignee": (names or {}).get(t.assignee_id),
            "assigned_by": (names or {}).get(t.created_by)}


def ticket_view(t: Ticket, names: dict[int, str] | None = None) -> dict:
    return {"ref": t.ref, "category": CATEGORIES.get(t.category, t.category), "title": t.title, "description": t.description,
            "priority": t.priority, "status": t.status, "requester": (names or {}).get(t.requester_id),
            "resolution": t.resolution, "opened": t.created_at.isoformat() if t.created_at else None}


async def names(s, ws: int) -> dict[int, str]:
    return dict((await s.execute(select(User.id, User.display_name).where(User.workspace_id == ws))).all())


async def add_task(s, actor: Actor, title: str, due_on: str | None, priority: str, notes: str | None) -> Task:
    require_writer(actor)
    title = " ".join(title.split())[:200]
    if not title:
        raise DomainError(VALIDATION, "What is the task?")
    t = Task(workspace_id=actor.workspace_id, ref="pending", title=title, notes=(notes or None), assignee_id=actor.user_id,
             created_by=actor.user_id, due_on=parse_due(due_on), priority=priority if priority in PRIORITIES else "normal", status="open")
    s.add(t)
    await s.flush()
    t.ref = f"T{t.id}"
    return t


async def task_by_ref(s, actor: Actor, ref: str) -> Task:
    t = (await s.execute(select(Task).where(Task.workspace_id == actor.workspace_id, Task.ref == ref.strip().upper()))).scalars().first()
    if t is None:
        raise DomainError(NOT_FOUND, f"Task {ref} not found")
    owner = await s.get(User, t.assignee_id)
    if not (t.assignee_id == actor.user_id or t.created_by == actor.user_id or actor.is_hr
            or (owner and owner.reports_to_id == actor.user_id)):
        raise DomainError(NOT_FOUND, f"Task {ref} not found")
    return t


async def tasks(s, actor: Actor, scope: str, include_done: bool = False) -> list[Task]:
    q = select(Task).where(Task.workspace_id == actor.workspace_id)
    if scope == "team":
        if actor.is_hr or actor.read_only:
            pass
        else:
            team = [u for (u,) in (await s.execute(select(User.id).where(User.reports_to_id == actor.user_id))).all()]
            q = q.where(Task.assignee_id.in_(team or [-1]))
    elif scope == "assigned_by_me":
        q = q.where(Task.created_by == actor.user_id, Task.assignee_id != actor.user_id)
    else:
        q = q.where(Task.assignee_id == actor.user_id)
    if not include_done:
        q = q.where(Task.status == "open")
    return list((await s.execute(q.order_by(Task.due_on.asc().nulls_last(), Task.id).limit(30))).scalars().all())


async def tickets(s, actor: Actor, scope: str) -> list[Ticket]:
    q = select(Ticket).where(Ticket.workspace_id == actor.workspace_id)
    if scope == "all":
        if not (actor.is_hr or actor.read_only):
            raise DomainError(FORBIDDEN, "Only the admin/HR team sees every ticket.")
    else:
        q = q.where(or_(Ticket.requester_id == actor.user_id, Ticket.assignee_id == actor.user_id))
    return list((await s.execute(q.order_by(Ticket.status != "open", Ticket.id.desc()).limit(30))).scalars().all())


async def _support_team(s, actor: Actor) -> list[User]:
    return list((await s.execute(select(User).where(User.workspace_id == actor.workspace_id,
                                                    User.role.in_(("admin", "hr_admin")), User.status == "active"))).scalars().all())


class AssignTask:
    kind = "assign_task"

    async def _inputs(self, s, actor, args):
        who = await people.user(s, actor, int(args["assignee_user_id"]))
        if who.id != actor.user_id and not (actor.is_hr or who.reports_to_id == actor.user_id):
            raise DomainError(FORBIDDEN, f"You can assign tasks to your own team only; {who.display_name} does not report to you.")
        title = " ".join((args.get("title") or "").split())[:200]
        if not title:
            raise DomainError(VALIDATION, "What is the task?")
        pr = args.get("priority") or "normal"
        return who, title, parse_due(args.get("due_on")), pr if pr in PRIORITIES else "normal", args.get("notes")

    async def plan(self, s, actor, args):
        who, title, due, pr, notes = await self._inputs(s, actor, args)
        lines = [f"Task: {title}", f"For: {who.display_name}", f"Due: {due:%a %d %b %Y}" if due else "Due: no date", f"Priority: {pr}"]
        if notes:
            lines.append(f"Notes: {notes}")
        lines.append(f"{who.display_name.split()[0]} gets it in their Purser inbox and on their home screen.")
        return Plan("Assign task", lines, f"Assign '{title}' to {who.display_name}?", [])

    async def execute(self, s, actor, args, receipt_id):
        who, title, due, pr, notes = await self._inputs(s, actor, args)
        t = Task(workspace_id=actor.workspace_id, ref="pending", title=title, notes=notes, assignee_id=who.id, created_by=actor.user_id,
                 due_on=due, priority=pr, status="open")
        s.add(t)
        await s.flush()
        t.ref = f"T{t.id}"
        await messaging.compose(s, actor, [who], kind="task", subject=f"New task from {actor.display_name}: {title}"[:200],
                                body=f"{title}\nDue: {due:%a %d %b} " if due else title, channels=["inbox"], receipt_id=receipt_id)
        await audit.record(s, actor, "task.assigned", record_type="task", record_id=t.id, record_ref=t.ref,
                           after={"title": title, "assignee": who.id, "due": str(due)}, receipt_id=receipt_id)
        return Execution(f"Task {t.ref} '{title}' assigned to {who.display_name}.", [{"type": "task", "ref": t.ref}])


class RaiseTicket:
    kind = "raise_ticket"

    def _inputs(self, args):
        cat = (args.get("category") or "it").lower()
        if cat not in CATEGORIES:
            raise DomainError(VALIDATION, f"Category must be one of {', '.join(CATEGORIES)}.")
        title = " ".join((args.get("title") or "").split())[:200]
        if not title:
            raise DomainError(VALIDATION, "What is the problem? Give a one-line title.")
        pr = args.get("priority") or "normal"
        return cat, title, (args.get("description") or "").strip()[:2000] or None, pr if pr in PRIORITIES else "normal"

    async def plan(self, s, actor, args):
        cat, title, desc, pr = self._inputs(args)
        team = await _support_team(s, actor)
        lines = [f"{CATEGORIES[cat]} ticket: {title}", f"Priority: {pr}"] + ([f"Details: {desc}"] if desc else [])
        lines.append("Goes to: " + (", ".join(u.display_name for u in team) or "the admin team") + " (Purser inbox).")
        return Plan("Raise helpdesk ticket", lines, f"Raise this {CATEGORIES[cat]} ticket?", [])

    async def execute(self, s, actor, args, receipt_id):
        cat, title, desc, pr = self._inputs(args)
        team = await _support_team(s, actor)
        t = Ticket(workspace_id=actor.workspace_id, ref="pending", requester_id=actor.user_id, category=cat, title=title, description=desc,
                   priority=pr, status="open", assignee_id=team[0].id if team else None)
        s.add(t)
        await s.flush()
        t.ref = f"HD{t.id}"
        if team:
            await messaging.compose(s, actor, team, kind="ticket", subject=f"[{t.ref}] {CATEGORIES[cat]}: {title}"[:200],
                                    body=f"From {actor.display_name} ({pr} priority)\n\n{desc or title}", channels=["inbox", "email"],
                                    receipt_id=receipt_id)
        await audit.record(s, actor, "ticket.raised", record_type="ticket", record_id=t.id, record_ref=t.ref,
                           after={"category": cat, "title": title, "priority": pr}, receipt_id=receipt_id)
        return Execution(f"Ticket {t.ref} raised with the admin team.", [{"type": "ticket", "ref": t.ref}])


class UpdateTicket:
    kind = "update_ticket"

    async def _load(self, s, actor, args):
        if not actor.is_hr:
            raise DomainError(FORBIDDEN, "Only the admin/HR team updates tickets.")
        t = (await s.execute(select(Ticket).where(Ticket.workspace_id == actor.workspace_id,
                                                  Ticket.ref == (args.get("ref") or "").strip().upper()))).scalars().first()
        if t is None:
            raise DomainError(NOT_FOUND, f"Ticket {args.get('ref')} not found")
        st = args.get("status")
        if st not in STATUSES:
            raise DomainError(VALIDATION, "Status must be open, in_progress or resolved.")
        if t.status == "resolved" and st == "resolved":
            raise DomainError(INVALID_STATE, f"{t.ref} is already resolved.")
        return t, st, (args.get("resolution") or "").strip() or None

    async def plan(self, s, actor, args):
        t, st, note = await self._load(s, actor, args)
        req = await s.get(User, t.requester_id)
        lines = [f"{t.ref}: {t.title}", f"Status: {t.status} → {st}"] + ([f"Note: {note}"] if note else [])
        lines.append(f"{req.display_name if req else 'The requester'} is told in their Purser inbox.")
        return Plan("Update ticket", lines, f"Mark {t.ref} as {st.replace('_', ' ')}?", [{"table": "tickets", "id": t.id}])

    async def execute(self, s, actor, args, receipt_id):
        t, st, note = await self._load(s, actor, args)
        t.status, t.resolution = st, note or t.resolution
        t.resolved_at = datetime.now(UTC) if st == "resolved" else None
        req = await s.get(User, t.requester_id)
        if req:
            await messaging.compose(s, actor, [req], kind="ticket", subject=f"[{t.ref}] {st.replace('_', ' ')}: {t.title}"[:200],
                                    body=note or f"Your ticket is now {st.replace('_', ' ')}.", channels=["inbox"], receipt_id=receipt_id)
        await audit.record(s, actor, "ticket.updated", record_type="ticket", record_id=t.id, record_ref=t.ref,
                           after={"status": st}, receipt_id=receipt_id)
        return Execution(f"Ticket {t.ref} is now {st.replace('_', ' ')}.", [{"type": "ticket", "ref": t.ref, "status": st}])


WORK_ACTIONS = (AssignTask(), RaiseTicket(), UpdateTicket())
