"""People operations: directory, leave ledger, leave requests, onboarding checklist, policies.

Leave balances mirror the budget ledger: available = granted - reserved - used, from append-only movements.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import AMBIGUOUS, NOT_FOUND, DomainError
from app.models import LeaveMovement, LeaveRequest, OnboardingTask, Policy, User
from app.services.records import normalize_name

LEAVE_TYPES = {"CL": ("Casual leave", 12), "SL": ("Sick leave", 8), "EL": ("Earned leave", 15)}
ONBOARDING_CHECKLIST = [
    ("Send welcome message and sign-in invite", "hr", 0),
    ("Prepare laptop and email account", "it", -2),
    ("Collect PAN, Aadhaar and bank details", "hr", 3),
    ("Policy acknowledgement (leave, expenses, code of conduct)", "employee", 5),
    ("First-week plan and buddy assigned", "manager", 1),
]


def working_days(start: date, end: date) -> int:
    """Monday-Friday count, inclusive. (Holiday calendar is a roadmap item; weekends are excluded.)"""
    if end < start:
        return 0
    return sum(1 for i in range((end - start).days + 1) if (start + timedelta(days=i)).weekday() < 5)


async def user(s: AsyncSession, actor: Actor, user_id: int) -> User:
    u = await s.get(User, user_id)
    if u is None or u.workspace_id != actor.workspace_id:
        raise DomainError(NOT_FOUND, f"Person {user_id} not found")
    return u


def can_view_person_private(actor: Actor, u: User) -> bool:
    return actor.is_hr or actor.user_id == u.id or u.reports_to_id == actor.user_id


async def find_people(s: AsyncSession, actor: Actor, name: str | None = None, department: str | None = None) -> list[User]:
    q = select(User).where(User.workspace_id == actor.workspace_id)
    if department:
        q = q.where(func.lower(User.department) == department.strip().lower())
    people = list((await s.execute(q.order_by(User.display_name))).scalars().all())
    if name:
        from difflib import SequenceMatcher

        target = normalize_name(name)
        scored = []
        for u in people:
            n = normalize_name(u.display_name)
            sc = max(SequenceMatcher(None, target, n).ratio(), 0.9 if target and target in n.split() else 0)
            if sc >= 0.6:
                scored.append((sc, u))
        scored.sort(key=lambda x: -x[0])
        people = [u for _, u in scored]
    return people


async def resolve_person(s: AsyncSession, actor: Actor, name: str) -> User:
    found = await find_people(s, actor, name)
    if not found:
        raise DomainError(NOT_FOUND, f"No one named '{name}'")
    if len(found) > 1 and normalize_name(found[0].display_name) != normalize_name(name):
        raise DomainError(AMBIGUOUS, f"More than one person matches '{name}'",
                          candidates=[{"user_id": u.id, "name": u.display_name, "department": u.department} for u in found[:4]])
    return found[0]


async def balance(s: AsyncSession, workspace_id: int, user_id: int) -> dict[str, dict]:
    rows = (await s.execute(select(LeaveMovement.leave_type, LeaveMovement.bucket, func.sum(LeaveMovement.days))
                            .where(LeaveMovement.workspace_id == workspace_id, LeaveMovement.user_id == user_id)
                            .group_by(LeaveMovement.leave_type, LeaveMovement.bucket))).all()
    out = {code: {"name": name, "granted": 0, "reserved": 0, "used": 0} for code, (name, _) in LEAVE_TYPES.items()}
    for lt, bucket, days in rows:
        out.setdefault(lt, {"name": lt, "granted": 0, "reserved": 0, "used": 0})[bucket] = int(days)
    for v in out.values():
        v["available"] = v["granted"] - v["reserved"] - v["used"]
    return out


async def post_leave(s: AsyncSession, workspace_id: int, user_id: int, leave_type: str, bucket: str, days: int, kind: str,
                     *, source_id: int | None = None, receipt_id: int | None = None, memo: str | None = None) -> None:
    s.add(LeaveMovement(workspace_id=workspace_id, user_id=user_id, leave_type=leave_type, bucket=bucket, days=days, kind=kind,
                        source_id=source_id, receipt_id=receipt_id, memo=memo))
    await s.flush()


async def overlapping(s: AsyncSession, workspace_id: int, user_id: int, start: date, end: date) -> LeaveRequest | None:
    q = select(LeaveRequest).where(LeaveRequest.workspace_id == workspace_id, LeaveRequest.user_id == user_id,
                                   LeaveRequest.state.in_(("submitted", "approved")),
                                   LeaveRequest.start_date <= end, LeaveRequest.end_date >= start)
    return (await s.execute(q)).scalars().first()


async def leave_by_ref(s: AsyncSession, actor: Actor, ref: str, *, for_update: bool = False) -> LeaveRequest:
    q = select(LeaveRequest).where(LeaveRequest.workspace_id == actor.workspace_id,
                                   func.upper(LeaveRequest.ref) == ref.strip().upper())
    if for_update:
        q = q.with_for_update()
    lr = (await s.execute(q)).scalars().first()
    if lr is None:
        raise DomainError(NOT_FOUND, f"Leave request {ref} not found")
    owner = await s.get(User, lr.user_id)
    if not (actor.is_hr or lr.user_id == actor.user_id or (owner and owner.reports_to_id == actor.user_id)):
        raise DomainError(NOT_FOUND, f"Leave request {ref} not found")
    return lr


async def leave_requests(s: AsyncSession, actor: Actor, scope: str) -> list[tuple[LeaveRequest, User]]:
    q = select(LeaveRequest, User).join(User, User.id == LeaveRequest.user_id).where(LeaveRequest.workspace_id == actor.workspace_id)
    if scope == "mine":
        q = q.where(LeaveRequest.user_id == actor.user_id)
    elif scope == "awaiting_my_decision":
        q = q.where(LeaveRequest.state == "submitted", LeaveRequest.user_id != actor.user_id)
        if not actor.is_hr:
            q = q.where(User.reports_to_id == actor.user_id)
    else:  # team / all
        if not actor.is_hr:
            q = q.where(or_(User.reports_to_id == actor.user_id, LeaveRequest.user_id == actor.user_id))
    return list((await s.execute(q.order_by(LeaveRequest.start_date))).all())


async def onboarding_tasks(s: AsyncSession, workspace_id: int, user_id: int) -> list[OnboardingTask]:
    return list((await s.execute(select(OnboardingTask).where(OnboardingTask.workspace_id == workspace_id,
                                                              OnboardingTask.user_id == user_id).order_by(OnboardingTask.id))).scalars())


async def search_policies(s: AsyncSession, workspace_id: int, query: str) -> list[Policy]:
    words = [w for w in normalize_name(query).split() if len(w) > 2]
    pols = (await s.execute(select(Policy).where(Policy.workspace_id == workspace_id))).scalars().all()
    scored = []
    for p in pols:
        hay = f"{p.topic} {p.title} {p.body}".lower()
        sc = sum(hay.count(w) for w in words) + (5 if any(w in p.topic.lower() for w in words) else 0)
        if sc:
            scored.append((sc, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:3]]
