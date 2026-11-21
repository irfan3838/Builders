"""Revenue clients = Party(kind="customer"). Ported from copilot services/invoices.py (client half).

Names compare on Munshi's `normalize_name` (the same key resolve_party uses). A deleted client is archived:
kept with its history and restored when its name is added again.
"""

from __future__ import annotations

from datetime import date
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Party
from app.services.records import normalize_name
from app.services.revenue.core import CLIENT_EXISTS, NAME_MAX, SAME_STATE, Rev, conflict, invalid, log, not_found, utcnow
from app.services.revenue.money import CURRENCIES, INR

CLIENT_STATES = ("active", "paused", "ended")
STATE_LABEL = {"active": "Active", "paused": "Paused", "ended": "Project over"}


def _q(rv: Rev):
    return select(Party).where(Party.workspace_id == rv.ws, Party.kind == "customer")


def clients(ss: Session, rv: Rev, *, archived: bool = False) -> list[Party]:
    q = _q(rv).order_by(Party.name)
    if not archived:
        q = q.where(Party.archived_at.is_(None))
    return list(ss.scalars(q))


def client(ss: Session, rv: Rev, client_id: int) -> Party:
    found = ss.get(Party, client_id)
    if found is None or found.workspace_id != rv.ws or found.kind != "customer":
        raise not_found("No such client")
    return found


def find_clients(ss: Session, rv: Rev, mention: str, limit: int = 3) -> tuple[list[Party], bool]:
    """Clients the words name: (matches, exact). Exact, unique prefix or unique word match wins; else fuzzy
    candidates (never auto-picked unless clearly ahead)."""
    key = normalize_name(mention)
    if not key:
        return [], False
    live = clients(ss, rv)
    exact = [c for c in live if c.normalized_name == key]
    if exact:
        return exact, True
    prefix = [c for c in live if c.normalized_name.startswith(key) or key.startswith(c.normalized_name)]
    if len(prefix) == 1:
        return prefix, True
    words = [c for c in live if key in c.normalized_name.split()]
    if len(words) == 1:
        return words, True
    scored = sorted(((SequenceMatcher(None, key, c.normalized_name).ratio(), c) for c in live), key=lambda t: -t[0])
    hits = [c for score, c in scored[:limit] if score >= 0.6]
    exact = len(hits) == 1 and scored[0][0] >= 0.85
    if len(scored) > 1 and scored[0][0] >= 0.85 and scored[0][0] - scored[1][0] >= 0.2:
        return [scored[0][1]], True
    return (prefix or hits), exact


def resolve(ss: Session, rv: Rev, mention: str) -> Party:
    """One client for the words, or an AMBIGUOUS / NOT_FOUND error the agent can ask about."""
    from app.errors import AMBIGUOUS, DomainError

    found, sure = find_clients(ss, rv, mention)
    if sure and len(found) == 1:
        return found[0]
    if not found:
        raise not_found(f"No client called '{mention}'")
    raise DomainError(AMBIGUOUS, f"Which client did you mean by '{mention}'?", candidates=[c.name for c in found])


def snapshot(c: Party) -> dict[str, Any]:
    return {"name": c.name, "currency": c.currency or INR, "state": c.state, "archived": bool(c.archived_at)}


def _name(name: str) -> str:
    name = " ".join((name or "").split())
    if not name or len(name) > NAME_MAX:
        raise invalid("A client needs a name (up to 120 characters)", field="name")
    return name


def _currency(currency: str) -> str:
    code = (currency or INR).strip().upper()
    if code not in CURRENCIES:
        raise invalid(f"Unknown currency {currency}", field="currency")
    return code


def create_client(ss: Session, rv: Rev, *, name: str, currency: str = INR) -> Party:
    name, currency = _name(name), _currency(currency)
    key = normalize_name(name)
    existing = ss.scalars(_q(rv).where(Party.normalized_name == key)).first()
    if existing is not None:
        if existing.archived_at is None:
            raise conflict(f"{existing.name} is already a client", CLIENT_EXISTS)
        existing.archived_at = None  # a returning client comes back with their history
        ss.flush()
        log(ss, rv, "client_restored", record_type="client", record_id=existing.id, record_ref=existing.name,
            after=snapshot(existing))
        return existing
    c = Party(workspace_id=rv.ws, kind="customer", name=name, normalized_name=key, aliases=[], currency=currency, state="active")
    ss.add(c)
    ss.flush()
    log(ss, rv, "client_created", record_type="client", record_id=c.id, record_ref=c.name, after={"name": name, "currency": currency})
    return c


def update_client(ss: Session, rv: Rev, c: Party, *, name: str | None = None, currency: str | None = None,
                  archived: bool | None = None) -> Party:
    before = snapshot(c)
    if name is not None:
        name = _name(name)
        key = normalize_name(name)
        clash = ss.scalars(_q(rv).where(Party.normalized_name == key, Party.id != c.id)).first()
        if clash is not None:
            raise conflict(f"{clash.name} is already a client", CLIENT_EXISTS)
        c.name, c.normalized_name = name, key
    if currency is not None and _currency(currency) != (c.currency or INR):
        c.currency = _currency(currency)
    action = "client_updated"
    if archived is not None and archived != bool(c.archived_at):
        c.archived_at = utcnow() if archived else None
        action = "client_archived" if archived else "client_restored"
    ss.flush()
    after = snapshot(c)
    if after != before:
        log(ss, rv, action, record_type="client", record_id=c.id, record_ref=c.name, before=before, after=after)
    return c


def set_client_state(ss: Session, rv: Rev, c: Party, state: str, *, on: date) -> Party:
    """Pause, resume, or end (project over). Rows stay as they are; a paused/ended client stops getting
    suggestions (custom reminders still come up)."""
    if state not in CLIENT_STATES:
        raise invalid("A client is active, paused or ended", field="state")
    if state == c.state:
        raise conflict(f"{c.name} is already {STATE_LABEL[state].lower()}", SAME_STATE)
    before = snapshot(c)
    c.state, c.state_on = state, (None if state == "active" else on)
    ss.flush()
    action = {"active": "client_resumed", "paused": "client_paused", "ended": "client_ended"}[state]
    log(ss, rv, action, record_type="client", record_id=c.id, record_ref=c.name, before=before, after=snapshot(c))
    return c


def active(c: Party) -> bool:
    return c.state == "active" and c.archived_at is None
