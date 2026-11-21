"""Read -> scan -> details -> liabilities for one uploaded document, staged on its extraction (no contract row yet;
creating the contract is a confirmed write). Like copilot's staged scan: confirmation reuses the stored result.

Upload starts the review in the background (prefetch) as soon as the document is classified as a contract, so the
agent's reply and the model calls overlap."""

from __future__ import annotations

import asyncio
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.actor import ADMIN, Actor
from app.config import get_settings
from app.errors import FORBIDDEN, INVALID_STATE, DomainError
from app.models import Workspace
from app.services import records, storage
from app.services.contracts import catalogue, liability, metadata, reading, scan

log = logging.getLogger("purser.contracts")
_tasks: dict[tuple[int, int], asyncio.Task] = {}


def can_view(actor: Actor) -> bool:
    return actor.can_read_finance


def can_decide(actor: Actor) -> bool:
    return actor.role == ADMIN


def require_view(actor: Actor) -> None:
    if not can_view(actor):
        raise DomainError(FORBIDDEN, "Contracts are visible to the admin and finance approvers only.")


def require_decide(actor: Actor) -> None:
    if not can_decide(actor):
        raise DomainError(FORBIDDEN, "Only the admin can decide contract findings or change a contract.")


async def our_names(s: AsyncSession, actor: Actor) -> tuple[str, ...]:
    """Our company's names, lower-case without spaces (how metadata/liability compare): config + workspace name."""
    names = [n.strip() for n in get_settings().our_party_names.split(",") if n.strip()]
    ws = await s.get(Workspace, actor.workspace_id)
    if ws is not None:
        base = re.sub(r"\(.*?\)", "", ws.name)
        names.append(records.normalize_name(base))
    return tuple(dict.fromkeys(n.lower().replace(" ", "") for n in names if len(n) >= 4))


_TYPES = (("nda", r"non[\s-]*disclosure|confidentiality\s+agreement|\bNDA\b"), ("msa", r"master\s+services?\s+agreement|\bMSA\b"),
          ("sow", r"statement\s+of\s+work|\bSOW\b"),
          ("vendor", r"supply\s+agreement|purchase\s+agreement|vendor\s+agreement|service\s+agreement"))


def guess_type(text: str, filename: str) -> str:
    head = filename + "\n" + text[:1500]
    for key, rx in _TYPES:
        if re.search(rx, head, re.I):
            return key
    return "other"


def guess_title(text: str, filename: str) -> str:
    for line in text.splitlines():
        t = " ".join(line.split())
        if 6 <= len(t) <= 120 and re.search(r"agreement|contract|memorandum|statement\s+of\s+work|terms", t, re.I):
            return t.title() if t.isupper() else t
    return re.sub(r"\.[a-z0-9]+$", "", filename)[:120] or "Contract"


def clean_name(name: str) -> str:
    """'Northwind Labs Inc, a company incorporated in Delaware' -> 'Northwind Labs Inc'."""
    name = re.split(r",?\s+an?\s+(?:company|corporation|firm|entity|partnership)\b|\s*\(\s*hereinafter", name, maxsplit=1, flags=re.I)[0]
    return " ".join(name.split()).strip(" ,.")[:200]


async def analyse(text: str, filename: str, ours: tuple[str, ...], *, use_model: bool = True) -> dict:
    """The whole review of a text: findings with liabilities, details, deadlines. Pure (no DB)."""
    (found, scanned_by_model), details = await asyncio.gather(
        scan.scan(text, catalogue.rules(), use_model=use_model), metadata.read(text, filename, ours, use_model=use_model))
    counterparty = clean_name(details.client.value) if details.client else None
    lis, parties, liab_by_model = await liability.assess(text, found, ours, counterparty, use_model=use_model)
    eff = details.effective_on.value if details.effective_on else None
    exp = details.expiry_on.value if details.expiry_on else None
    dls = liability.deadlines(text, found, lis, eff, exp, details.expiry_on.evidence if details.expiry_on else None)
    findings = []
    for i, f in enumerate(found):
        li = lis.get(i)
        findings.append({
            "clause_type": f.type_key, "start": f.start, "stop": f.stop, "quote": f.quote[:2000], "risk": f.risk,
            "confidence": f.confidence, "note": f.note, "state": "tagged" if f.risk == "standard" else "proposed",
            "liability": liability.as_dict(li) if li else None,
        })
    return {
        "title": guess_title(text, filename), "contract_type": guess_type(text, filename), "counterparty": counterparty,
        "details": details.as_json(), "parties": parties, "findings": findings, "scanned_by_model": scanned_by_model,
        "liability_by_model": liab_by_model,
        "deadlines": [{"kind": d.kind, "due_on": d.due_on.isoformat(), "basis": d.basis, "finding_index": d.finding_index} for d in dls],
    }


async def _review(actor: Actor, document_id: int) -> dict:
    async with db.session_scope() as s:
        doc = await records.document(s, actor, document_id)
        ex = await records.extraction(s, actor, doc.id)
        if ex is not None and (ex.fields or {}).get("contract_review"):
            return ex.fields["contract_review"]
        if ex is None or ex.doc_type != "contract":
            raise DomainError(INVALID_STATE, "This document has not been read as a contract.")
        key, media, filename = doc.storage_key, doc.media_type, doc.filename
        ours = await our_names(s, actor)
    read = await reading.read(await storage.get(key), media)
    staged = await analyse(read.text, filename, ours)
    staged.update(text=read.text, text_source=read.source, pages=read.pages, vision_pages=read.vision_pages,
                  unread_pages=read.unread_pages, coverage_note=read.coverage_note())
    async with db.session_scope() as s:
        doc = await records.document(s, actor, document_id, for_update=True)
        ex = await records.extraction(s, actor, doc.id)
        if (ex.fields or {}).get("contract_review"):
            return ex.fields["contract_review"]
        ex.fields = {**(ex.fields or {}), "contract_review": staged}
        doc.version += 1
    return staged


def prefetch(actor: Actor, document_id: int) -> asyncio.Task | None:
    if not can_view(actor):
        return None
    k = (actor.workspace_id, document_id)
    task = _tasks.get(k)
    if task is None or (task.done() and (task.cancelled() or task.exception() is not None)):
        task = asyncio.create_task(_review(actor, document_id))
        _tasks[k] = task
        task.add_done_callback(lambda t: not t.cancelled() and t.exception()
                               and log.warning("contract review failed doc=%s: %r", document_id, t.exception()))
    return task


async def ensure(actor: Actor, document_id: int, *, wait_seconds: float | None = None) -> dict | None:
    """The staged review. With wait_seconds, returns None if it is still running (it keeps running in the background,
    so a voice turn never waits past its budget; the card polls and a later call returns the result)."""
    require_view(actor)
    task = prefetch(actor, document_id)
    try:
        if wait_seconds is None:
            return await asyncio.shield(task)
        return await asyncio.wait_for(asyncio.shield(task), wait_seconds)
    except TimeoutError:
        return None
    finally:
        if task.done():
            _tasks.pop((actor.workspace_id, document_id), None)
