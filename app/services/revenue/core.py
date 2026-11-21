"""Shared plumbing for the revenue port.

The revenue services are *sync* SQLAlchemy (ported from the copilot module, which leans on ORM
relationships). Async callers run them through `AsyncSession.run_sync`, which gives them a sync Session on
the same connection and transaction, so lazy loads work and the propose -> confirm transaction stays one.

`Rev` carries what the copilot module took from its host: workspace, actor, business date, channel, and the
action receipt when a write runs inside a confirmed proposal. Every query filters on `rev.ws`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from app.errors import INVALID_STATE, NOT_FOUND, VALIDATION, DomainError
from app.models import AuditEvent, Invoice, Party

NAME_MAX = 120
TEXT_MAX = 200

# Revenue-specific error codes (DomainError.code)
CLIENT_EXISTS = "CLIENT_EXISTS"
MONTH_TAKEN = "MONTH_TAKEN"
BAD_STATUS = "BAD_STATUS"
INVOICE_PAID = "INVOICE_PAID"
RATE_UNAVAILABLE = "RATE_UNAVAILABLE"
NOTHING_LEFT = "NOTHING_LEFT"
NOTHING_PENDING = "NOTHING_PENDING"
MIXED_CURRENCY = "MIXED_CURRENCY"
SAME_STATE = "SAME_STATE"


@dataclass(frozen=True)
class Rev:
    ws: int
    actor_id: int | None
    today: date
    channel: str = "assistant"  # assistant | ui | seed
    receipt_id: int | None = None
    proposal_id: str | None = None

    @classmethod
    def of(cls, actor, today: date, *, channel: str = "assistant", receipt_id: int | None = None) -> Rev:
        return cls(actor.workspace_id, actor.user_id, today, channel, receipt_id)


def utcnow() -> datetime:
    return datetime.now(UTC)


def invalid(message: str, *, field: str | None = None, code: str | None = None) -> DomainError:
    return DomainError(code or VALIDATION, message, **({"field": field} if field else {}))


def conflict(message: str, code: str | None = None) -> DomainError:
    return DomainError(code or INVALID_STATE, message)


def not_found(message: str) -> DomainError:
    return DomainError(NOT_FOUND, message)


def log(
    ss: Session,
    rv: Rev,
    action: str,
    *,
    record_type: str,
    record_id: int | None = None,
    record_ref: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append one audit event (Purser's audit_events), tagged with the channel like copilot's audit log."""
    ev = AuditEvent(
        workspace_id=rv.ws,
        actor_id=rv.actor_id,
        action=f"revenue.{action}",
        record_type=record_type,
        record_id=record_id,
        record_ref=record_ref[:30] if record_ref else None,  # the column is short; the full name is in the snapshot
        before=before,
        after={**(after or {}), "channel": rv.channel},
        proposal_id=rv.proposal_id,
        receipt_id=rv.receipt_id,
    )
    ss.add(ev)
    ss.flush()
    touched = ss.info.get("rev_touched")
    if touched is not None and record_id is not None:
        touched.append((record_type, record_id))
    return ev


@event.listens_for(Session, "before_flush")
def _bump_versions(ss: Session, _ctx, _instances) -> None:
    """Any change to an invoice or a client bumps its version, so an open proposal built on the old state
    goes stale at confirm (proposals.confirm compares versions). Automatic: no write path can forget it."""
    for obj in ss.dirty:
        if isinstance(obj, (Invoice, Party)) and ss.is_modified(obj, include_collections=False):
            if not inspect(obj).attrs.version.history.has_changes():
                obj.version = (obj.version or 0) + 1
