"""Role gates shared by tools, services and HTTP routes. Services stay the enforcement point; tool hiding is extra."""

from __future__ import annotations

from app.actor import Actor
from app.errors import FORBIDDEN, DomainError

FINANCE_READ_MSG = "Budget, revenue and company finance figures are limited to finance and leadership. I can help with your own claims, leave, tasks and meetings."
READ_ONLY_MSG = "The CEO view is read-only, so I can't make changes from this login. I can show or explain anything."


def require_finance_read(actor: Actor) -> None:
    if not actor.can_read_finance:
        raise DomainError(FORBIDDEN, FINANCE_READ_MSG)


def require_writer(actor: Actor) -> None:
    if actor.read_only:
        raise DomainError(FORBIDDEN, READ_ONLY_MSG)


def http_finance_read(actor: Actor) -> None:
    from fastapi import HTTPException
    if not actor.can_read_finance:
        raise HTTPException(403, "Finance and leadership only")
