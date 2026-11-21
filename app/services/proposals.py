"""Propose -> present -> confirm -> receipt. The only path by which business records change.

* One foreground proposal per conversation: a new proposal supersedes the previous open one.
* Confirm runs in the caller's transaction: lock proposal, lock + version-check affected rows,
  execute, persist receipt + audit. Repeated confirm returns the original receipt.
* A stale preview never executes; a fresh preview is produced instead.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.config import get_settings
from app.errors import NOT_FOUND, PROPOSAL_CLOSED, DomainError
from app.models import (
    Bill,
    Claim,
    Contract,
    ContractFinding,
    Conversation,
    Document,
    Invoice,
    LeaveRequest,
    Party,
    Proposal,
    Receipt,
    Reservation,
)
from app.services import audit
from app.services.actions import ACTIONS

VERSIONED = {"documents": Document, "reservations": Reservation, "claims": Claim, "bills": Bill, "leave_requests": LeaveRequest,
             "invoices": Invoice, "parties": Party, "contracts": Contract, "contract_findings": ContractFinding}


def _now() -> datetime:
    return datetime.now(UTC)


def canonical(args: dict) -> tuple[dict, str]:
    clean = {k: v for k, v in sorted(args.items()) if v is not None}
    blob = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
    return clean, hashlib.sha256(blob.encode()).hexdigest()


async def create(s: AsyncSession, actor: Actor, kind: str, args: dict) -> Proposal:
    action = ACTIONS[kind]
    clean, h = canonical(args)
    plan = await action.plan(s, actor, clean)  # raises DomainError when not allowed / invalid
    if actor.conversation_id:
        await s.execute(
            update(Proposal)
            .where(Proposal.conversation_id == actor.conversation_id, Proposal.status == "open")
            .values(status="superseded")
        )
    p = Proposal(
        workspace_id=actor.workspace_id,
        conversation_id=actor.conversation_id,
        actor_id=actor.user_id,
        kind=kind,
        args=clean,
        args_hash=h,
        affected=plan.affected,
        preview=plan.preview(),
        expires_at=_now() + timedelta(seconds=get_settings().proposal_ttl_seconds),
    )
    s.add(p)
    await s.flush()
    if actor.conversation_id:
        conv = await s.get(Conversation, actor.conversation_id)
        if conv is not None:
            conv.foreground_proposal_id = p.id
    await audit.record(s, actor, "proposal.created", proposal_id=p.id, after={"kind": kind, "args": clean})
    return p


async def mark_presented(s: AsyncSession, proposal_id: str, *, offset_ms: int | None = None) -> None:
    p = await s.get(Proposal, proposal_id)
    if p is not None and p.status == "open" and p.presented_at is None:
        p.presented_at = _now()
        p.presented_offset_ms = offset_ms


async def get_open(s: AsyncSession, actor: Actor) -> Proposal | None:
    if not actor.conversation_id:
        return None
    q = select(Proposal).where(
        Proposal.workspace_id == actor.workspace_id,
        Proposal.conversation_id == actor.conversation_id,
        Proposal.actor_id == actor.user_id,
        Proposal.status == "open",
    ).order_by(Proposal.created_at.desc())
    return (await s.execute(q)).scalars().first()


async def load(s: AsyncSession, actor: Actor, proposal_id: str, *, for_update: bool = False) -> Proposal:
    q = select(Proposal).where(Proposal.id == proposal_id, Proposal.workspace_id == actor.workspace_id)
    if for_update:
        q = q.with_for_update()
    p = (await s.execute(q)).scalars().first()
    if p is None or p.actor_id != actor.user_id:
        raise DomainError(NOT_FOUND, "Proposal not found")
    return p


async def cancel(s: AsyncSession, actor: Actor, proposal_id: str) -> Proposal:
    p = await load(s, actor, proposal_id, for_update=True)
    if p.status == "open":
        p.status = "cancelled"
        await audit.record(s, actor, "proposal.cancelled", proposal_id=p.id)
    return p


@dataclass
class ConfirmOutcome:
    status: str  # executed | replayed | stale | expired
    receipt: Receipt | None = None
    new_proposal: Proposal | None = None
    error: DomainError | None = None


async def confirm(s: AsyncSession, actor: Actor, proposal_id: str, *, via: str, evidence: dict | None = None) -> ConfirmOutcome:
    p = await load(s, actor, proposal_id, for_update=True)
    if p.status == "executed":
        return ConfirmOutcome("replayed", receipt=await s.get(Receipt, p.receipt_id))
    if p.status != "open":
        raise DomainError(PROPOSAL_CLOSED, f"This proposal was {p.status}. Ask again for a fresh preview.", status=p.status)
    if _now() > p.expires_at:
        p.status = "expired"
        return ConfirmOutcome("expired", new_proposal=await _refresh(s, actor, p))

    for a in p.affected:
        model = VERSIONED[a["table"]]
        row = (await s.execute(select(model).where(model.id == a["id"]).with_for_update())).scalars().first()
        if row is None or row.workspace_id != actor.workspace_id or row.version != a["version"]:
            p.status = "stale"
            return ConfirmOutcome("stale", new_proposal=await _refresh(s, actor, p))

    receipt = Receipt(
        workspace_id=actor.workspace_id,
        ref="pending",
        proposal_id=p.id,
        idempotency_key=p.idempotency_key,
        actor_id=actor.user_id,
        confirmed_via=via,
        confirmation_evidence=evidence or {},
        summary="",
    )
    s.add(receipt)
    await s.flush()
    receipt.ref = f"R{receipt.id}"
    result = await ACTIONS[p.kind].execute(s, actor, p.args, receipt.id)
    receipt.summary, receipt.effects = result.summary, result.effects
    p.status, p.receipt_id = "executed", receipt.id
    await audit.record(s, actor, "proposal.confirmed", proposal_id=p.id, receipt_id=receipt.id,
                       after={"via": via, "summary": result.summary})
    await s.flush()
    return ConfirmOutcome("executed", receipt=receipt)


async def _refresh(s: AsyncSession, actor: Actor, old: Proposal) -> Proposal | None:
    """Re-plan with the same arguments against current state. Errors (e.g. now settled) propagate."""
    new = await create(s, actor, old.kind, old.args)
    old.superseded_by = new.id
    return new
