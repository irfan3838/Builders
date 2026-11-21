from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.models import AuditEvent


async def record(
    s: AsyncSession,
    actor: Actor | None,
    action: str,
    *,
    workspace_id: int | None = None,
    record_type: str | None = None,
    record_id: int | None = None,
    record_ref: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    proposal_id: str | None = None,
    receipt_id: int | None = None,
) -> AuditEvent:
    ev = AuditEvent(
        workspace_id=workspace_id or (actor.workspace_id if actor else None),
        actor_id=actor.user_id if actor else None,
        action=action,
        record_type=record_type,
        record_id=record_id,
        record_ref=record_ref,
        before=before,
        after=after,
        proposal_id=proposal_id,
        receipt_id=receipt_id,
    )
    s.add(ev)
    await s.flush()
    return ev
