"""Scoped record lookups. Every read derives scope from the Actor; out-of-scope looks like not-found."""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import AMBIGUOUS, NOT_FOUND, DomainError
from app.models import Bill, Claim, Document, Extraction, Party

IST = ZoneInfo("Asia/Kolkata")


def today_ist() -> date:
    from datetime import datetime

    return datetime.now(IST).date()


def _not_found(what: str) -> DomainError:
    return DomainError(NOT_FOUND, f"{what} not found")


async def claim_by_ref(s: AsyncSession, actor: Actor, ref: str, *, for_update: bool = False) -> Claim:
    q = select(Claim).where(Claim.workspace_id == actor.workspace_id, func.upper(Claim.ref) == ref.strip().upper())
    if for_update:
        q = q.with_for_update()
    c = (await s.execute(q)).scalars().first()
    if c is None:
        raise _not_found(f"Claim {ref}")
    if not actor.can_read_finance and c.beneficiary_party_id != actor.party_id and c.submitter_id != actor.user_id:
        raise _not_found(f"Claim {ref}")
    return c


async def bill_by_ref(s: AsyncSession, actor: Actor, ref: str, *, for_update: bool = False) -> Bill:
    if not actor.can_read_finance:
        raise _not_found(f"Bill {ref}")
    q = select(Bill).where(Bill.workspace_id == actor.workspace_id, func.upper(Bill.ref) == ref.strip().upper())
    if for_update:
        q = q.with_for_update()
    b = (await s.execute(q)).scalars().first()
    if b is None:
        raise _not_found(f"Bill {ref}")
    return b


async def record_by_ref(s: AsyncSession, actor: Actor, ref: str) -> Claim | Bill:
    r = ref.strip().upper()
    if r.startswith("C"):
        return await claim_by_ref(s, actor, r)
    if r.startswith("B"):
        return await bill_by_ref(s, actor, r)
    raise _not_found(f"Record {ref}")


async def party(s: AsyncSession, actor: Actor, party_id: int, *, kind: str | None = None) -> Party:
    p = await s.get(Party, party_id)
    if p is None or p.workspace_id != actor.workspace_id or (kind and p.kind != kind):
        raise _not_found(f"{kind or 'Party'} {party_id}")
    return p


async def document(s: AsyncSession, actor: Actor, document_id: int, *, for_update: bool = False) -> Document:
    q = select(Document).where(Document.workspace_id == actor.workspace_id, Document.id == document_id)
    if for_update:
        q = q.with_for_update()
    d = (await s.execute(q)).scalars().first()
    if d is None or (not actor.can_read_finance and d.uploader_id != actor.user_id):
        raise _not_found(f"Document {document_id}")
    return d


async def extraction(s: AsyncSession, actor: Actor, document_id: int) -> Extraction | None:
    q = select(Extraction).where(Extraction.workspace_id == actor.workspace_id, Extraction.document_id == document_id)
    return (await s.execute(q)).scalars().first()


def effective_fields(ex: Extraction) -> dict:
    """Extracted fields with the user's spoken corrections applied, latest correction wins."""
    fields = dict(ex.fields or {})
    for c in ex.corrections or []:
        fields[c["field"]] = c["value"]
    return fields


def normalize_name(name: str) -> str:
    import re

    t = re.sub(r"[^a-z0-9ऀ-ॿ ]+", " ", name.lower())
    for w in (" pvt", " ltd", " private", " limited", " llp", " inc", " co "):
        t = t.replace(w, " ")
    return re.sub(r"\s+", " ", t).strip()


async def resolve_party(s: AsyncSession, actor: Actor, name: str, kind: str | None = None) -> list[dict]:
    """Return scored candidates. Never auto-picks when more than one plausibly matches."""
    from difflib import SequenceMatcher

    q = select(Party).where(Party.workspace_id == actor.workspace_id)
    if kind:
        q = q.where(Party.kind == kind)
    target = normalize_name(name)
    out = []
    for p in (await s.execute(q)).scalars().all():
        names = [p.normalized_name] + [normalize_name(a) for a in (p.aliases or [])]
        score = max(
            max(SequenceMatcher(None, target, n).ratio() for n in names),
            0.9 if any(target and (target in n.split() or n.startswith(target)) for n in names) else 0,
        )
        if score >= 0.55:
            out.append({"party_id": p.id, "name": p.name, "kind": p.kind, "score": round(score, 2)})
    out.sort(key=lambda c: (-c["score"], c["name"]))
    return out


async def resolve_single_party(s: AsyncSession, actor: Actor, name: str, kind: str | None = None) -> dict:
    cands = await resolve_party(s, actor, name, kind)
    if not cands:
        raise DomainError(NOT_FOUND, f"No {kind or 'party'} matching '{name}'")
    if len(cands) > 1 and cands[1]["score"] >= cands[0]["score"] - 0.08:
        raise DomainError(AMBIGUOUS, f"More than one {kind or 'party'} matches '{name}'", candidates=cands[:4])
    return cands[0]
