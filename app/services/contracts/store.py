"""Contract rows: create from a staged review, find by spoken mention, liability / deadline / open-flag reads, and the
views the cards and the agent share. Every read is workspace-scoped and role-gated (admin, finance approver)."""

from __future__ import annotations

import re
from datetime import date, timedelta
from difflib import SequenceMatcher

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import AMBIGUOUS, NOT_FOUND, DomainError
from app.models import Contract, ContractDeadline, ContractFinding, Document, Party
from app.money import format_inr
from app.services import audit, records
from app.services.contracts.catalogue import CONTRACT_TYPES, NAMES
from app.services.contracts.review import require_view

STANDING = ("proposed", "accepted", "modified")  # copilot exposure: risky clauses not rejected
RISKY = ("high", "medium", "low")
CAP_TYPES = ("limitation_of_liability", "unlimited_liability")
BEARER_WORDS = {"us": "binds us", "counterparty": "binds the other party", "mutual": "binds both sides",
                "unclear": "who bears it is unclear"}


# --------------------------------------------------------------------------- create


async def match_party(s: AsyncSession, actor: Actor, name: str | None) -> int | None:
    """An existing customer or vendor with this name (strong match only), else None."""
    if not name:
        return None
    cands = await records.resolve_party(s, actor, name)
    cands = [c for c in cands if c["kind"] in ("customer", "vendor") and c["score"] >= 0.8]
    if len(cands) == 1 or (len(cands) > 1 and cands[0]["score"] - cands[1]["score"] > 0.08):
        return cands[0]["party_id"]
    return None


def _date(v: str | None) -> date | None:
    return date.fromisoformat(v) if v else None


async def create_from_review(s: AsyncSession, actor: Actor, doc: Document, staged: dict, *, title: str,
                             contract_type: str, counterparty: str | None, party_id: int | None) -> Contract:
    det = staged["details"]
    c = Contract(workspace_id=actor.workspace_id, ref="pending", document_id=doc.id, title=title[:200],
                 contract_type=contract_type, counterparty_name=counterparty, party_id=party_id,
                 effective_on=_date((det.get("effective_on") or {}).get("value")),
                 expiry_on=_date((det.get("expiry_on") or {}).get("value")),
                 details={"evidence": det, "parties": staged.get("parties", {}), "pages": staged.get("pages"),
                          "vision_pages": staged.get("vision_pages", []), "unread_pages": staged.get("unread_pages", []),
                          "coverage_note": staged.get("coverage_note"), "filename": doc.filename},
                 text=staged["text"], text_source=staged["text_source"], scanned_by_model=bool(staged.get("scanned_by_model")),
                 created_by=actor.user_id)
    s.add(c)
    await s.flush()
    c.ref = f"AG{c.id}"
    await add_findings(s, actor, c, staged["findings"], staged["deadlines"])
    return c


async def add_findings(s: AsyncSession, actor: Actor, c: Contract, findings: list[dict], deadlines: list[dict]) -> list[ContractFinding]:
    rows: list[ContractFinding] = []
    for f in findings:
        li = f.get("liability") or {}
        row = ContractFinding(
            workspace_id=actor.workspace_id, contract_id=c.id, clause_type=f["clause_type"], start=f["start"], stop=f["stop"],
            quote=f["quote"], risk=f["risk"], confidence=f["confidence"], state=f["state"], source="ai", note=f.get("note"),
            bearer=li.get("bearer"), bearer_term=(li.get("bearer_term") or None) and li["bearer_term"][:120],
            beneficiary=(li.get("beneficiary") or None) and li["beneficiary"][:120], trigger_quote=li.get("trigger_quote"),
            cap_paise=li.get("cap_paise"), cap_basis=li.get("cap_basis"), carve_outs=li.get("carve_outs") or [],
            notice_days=li.get("notice_days"), liability_source=li.get("source") if li else None)
        s.add(row)
        rows.append(row)
    await s.flush()
    for d in deadlines:
        fi = d.get("finding_index")
        s.add(ContractDeadline(workspace_id=actor.workspace_id, contract_id=c.id, kind=d["kind"], due_on=_date(d["due_on"]),
                               basis=d["basis"], finding_id=rows[fi].id if fi is not None and fi < len(rows) else None))
    await s.flush()
    return rows


# --------------------------------------------------------------------------- lookups


async def by_mention(s: AsyncSession, actor: Actor, mention: str | int, *, for_update: bool = False) -> Contract:
    """'AG3', '3', a title or a counterparty name. Ambiguous names return candidates, never a guess."""
    require_view(actor)
    m = str(mention).strip()
    q = select(Contract).where(Contract.workspace_id == actor.workspace_id)
    if for_update:
        q = q.with_for_update()
    if re.fullmatch(r"(?i)(ag)?\s*\d+", m):
        c = (await s.execute(q.where(Contract.id == int(re.sub(r"\D", "", m))))).scalars().first()
        if c is None:
            raise DomainError(NOT_FOUND, f"Contract {m} not found")
        return c
    target = records.normalize_name(m)
    scored = []
    for c in (await s.execute(q)).scalars().all():
        names = [records.normalize_name(c.title), records.normalize_name(c.counterparty_name or "")]
        score = max(SequenceMatcher(None, target, n).ratio() for n in names)
        if any(target and target in n for n in names):
            score = max(score, 0.9)
        if score >= 0.6:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        raise DomainError(NOT_FOUND, f"No contract matching '{m}'")
    if len(scored) > 1 and scored[1][0] >= scored[0][0] - 0.05:
        raise DomainError(AMBIGUOUS, f"More than one contract matches '{m}'",
                          candidates=[{"ref": c.ref, "title": c.title, "counterparty": c.counterparty_name} for _, c in scored[:4]])
    return scored[0][1]


async def finding(s: AsyncSession, actor: Actor, finding_id: int, *, for_update: bool = False) -> tuple[ContractFinding, Contract]:
    require_view(actor)
    q = select(ContractFinding).where(ContractFinding.workspace_id == actor.workspace_id, ContractFinding.id == int(finding_id))
    if for_update:
        q = q.with_for_update()
    f = (await s.execute(q)).scalars().first()
    if f is None:
        raise DomainError(NOT_FOUND, f"Finding #{finding_id} not found")
    return f, await s.get(Contract, f.contract_id)


# --------------------------------------------------------------------------- views


def finding_view(f: ContractFinding, c: Contract | None = None) -> dict:
    out = {
        "finding_id": f.id, "clause": NAMES.get(f.clause_type, f.clause_type), "clause_type": f.clause_type, "risk": f.risk,
        "state": f.state, "confidence": f.confidence, "quote": " ".join(f.quote.split())[:400], "note": f.note,
        "explanation": f.explanation, "bearer": f.bearer, "who_bears": BEARER_WORDS.get(f.bearer or "", None),
        "bearer_term": f.bearer_term, "beneficiary": f.beneficiary, "trigger": f.trigger_quote,
        "cap": format_inr(f.cap_paise) if f.cap_paise else None, "cap_basis": f.cap_basis,
        "carve_outs": [x["quote"] for x in f.carve_outs or []], "notice_days": f.notice_days, "start": f.start, "stop": f.stop,
    }
    if c is not None:
        out.update(contract=c.ref, contract_title=c.title, counterparty=c.counterparty_name)
    return out


def contract_view(c: Contract, findings: list[ContractFinding], deadlines: list[ContractDeadline]) -> dict:
    risky = [f for f in findings if f.risk in RISKY and f.state in STANDING]
    return {
        "ref": c.ref, "contract_id": c.id, "title": c.title, "type": CONTRACT_TYPES.get(c.contract_type, c.contract_type),
        "counterparty": c.counterparty_name, "party_id": c.party_id, "status": c.status, "our_role": c.our_role,
        "effective_on": c.effective_on.isoformat() if c.effective_on else None,
        "expiry_on": c.expiry_on.isoformat() if c.expiry_on else None,
        "liabilities": [finding_view(f) for f in risky],
        "other_clauses": [{"finding_id": f.id, "clause": NAMES.get(f.clause_type, f.clause_type), "state": f.state, "risk": f.risk}
                          for f in findings if f not in risky],
        "caps": [finding_view(f) for f in findings if f.clause_type in CAP_TYPES and f.state != "rejected"],
        "open_flags": sum(1 for f in findings if f.state == "proposed"),
        "binds_us": sum(1 for f in risky if f.bearer == "us"),
        "deadlines": [{"kind": d.kind, "due_on": d.due_on.isoformat(), "basis": d.basis} for d in sorted(deadlines, key=lambda d: d.due_on)],
        "coverage": {"text_source": c.text_source, "model_read_all": c.scanned_by_model,
                     "note": (c.details or {}).get("coverage_note"),
                     "caveat": "Automated reading of the wording; Legal decides each flag. An empty list does not certify the contract."},
    }


async def load_full(s: AsyncSession, c: Contract) -> tuple[list[ContractFinding], list[ContractDeadline]]:
    fs = (await s.execute(select(ContractFinding).where(ContractFinding.contract_id == c.id, ContractFinding.workspace_id == c.workspace_id)
                          .order_by(ContractFinding.start))).scalars().all()
    ds = (await s.execute(select(ContractDeadline).where(ContractDeadline.contract_id == c.id,
                                                         ContractDeadline.workspace_id == c.workspace_id))).scalars().all()
    return list(fs), list(ds)


# --------------------------------------------------------------------------- portfolio reads


async def search(s: AsyncSession, actor: Actor, *, words: str | None = None, contract_type: str | None = None,
                 status: str | None = None, counterparty: str | None = None) -> list[dict]:
    require_view(actor)
    q = select(Contract).where(Contract.workspace_id == actor.workspace_id)
    if contract_type:
        q = q.where(Contract.contract_type == contract_type)
    if status:
        q = q.where(Contract.status == status)
    if counterparty:
        q = q.where(Contract.counterparty_name.icontains(counterparty.strip(), autoescape=True))
    if words:
        w = words.strip()  # user wildcards (% _) are matched literally
        q = q.where(or_(Contract.title.icontains(w, autoescape=True), Contract.counterparty_name.icontains(w, autoescape=True),
                        Contract.text.icontains(w, autoescape=True)))
    rows = (await s.execute(q.order_by(Contract.id))).scalars().all()
    out = []
    for c in rows:
        n = (await s.execute(select(func.count()).where(ContractFinding.contract_id == c.id, ContractFinding.state == "proposed"))).scalar()
        out.append({"ref": c.ref, "title": c.title, "type": CONTRACT_TYPES.get(c.contract_type), "counterparty": c.counterparty_name,
                    "status": c.status, "expiry_on": c.expiry_on.isoformat() if c.expiry_on else None, "open_flags": n})
    return out


async def liabilities(s: AsyncSession, actor: Actor, *, bearer: str | None = None, risk: str | None = None,
                      counterparty: str | None = None, contract: str | None = None, include_decided: bool = True) -> list[dict]:
    """Copilot's Exposure plus who bears it: risky clauses that are proposed, accepted or modified."""
    require_view(actor)
    states = STANDING if include_decided else ("proposed",)
    q = (select(ContractFinding, Contract).join(Contract, and_(Contract.id == ContractFinding.contract_id,
                                                              Contract.workspace_id == ContractFinding.workspace_id))
         .where(ContractFinding.workspace_id == actor.workspace_id, ContractFinding.risk.in_(RISKY), ContractFinding.state.in_(states)))
    if bearer:
        q = q.where(ContractFinding.bearer == bearer)
    if risk:
        q = q.where(ContractFinding.risk == risk)
    if counterparty:
        q = q.where(Contract.counterparty_name.icontains(counterparty.strip(), autoescape=True))
    if contract:
        c = await by_mention(s, actor, contract)
        q = q.where(Contract.id == c.id)
    order = {"high": 0, "medium": 1, "low": 2}
    rows = (await s.execute(q)).all()
    rows.sort(key=lambda r: (order.get(r[0].risk, 3), r[1].id, r[0].start))
    return [finding_view(f, c) for f, c in rows]


async def caps(s: AsyncSession, actor: Actor, contract_ids: list[int] | None = None) -> list[dict]:
    """Stated liability caps (and 'no cap' clauses) with their carve-outs, per contract."""
    require_view(actor)
    q = (select(ContractFinding, Contract).join(Contract, and_(Contract.id == ContractFinding.contract_id,
                                                              Contract.workspace_id == ContractFinding.workspace_id))
         .where(ContractFinding.workspace_id == actor.workspace_id, ContractFinding.clause_type.in_(CAP_TYPES),
                ContractFinding.state != "rejected"))
    if contract_ids is not None:
        q = q.where(Contract.id.in_(contract_ids))
    return [{"contract": c.ref, "counterparty": c.counterparty_name, "whose_liability": BEARER_WORDS.get(f.bearer or "unclear"),
             "cap": format_inr(f.cap_paise) if f.cap_paise else None, "cap_basis": f.cap_basis,
             "carve_outs": [x["quote"] for x in f.carve_outs or []], "finding_id": f.id}
            for f, c in (await s.execute(q.order_by(Contract.id))).all()]


async def deadlines(s: AsyncSession, actor: Actor, days: int = 90) -> list[dict]:
    require_view(actor)
    today = records.today_ist()
    q = (select(ContractDeadline, Contract).join(Contract, and_(Contract.id == ContractDeadline.contract_id,
                                                               Contract.workspace_id == ContractDeadline.workspace_id))
         .where(ContractDeadline.workspace_id == actor.workspace_id, Contract.status == "active",
                ContractDeadline.due_on >= today, ContractDeadline.due_on <= today + timedelta(days=max(1, min(days, 1100))))
         .order_by(ContractDeadline.due_on))
    return [{"contract": c.ref, "title": c.title, "counterparty": c.counterparty_name, "kind": d.kind,
             "due_on": d.due_on.isoformat(), "days_left": (d.due_on - today).days, "basis": d.basis}
            for d, c in (await s.execute(q)).all()]


async def record_created(s: AsyncSession, actor: Actor, c: Contract, receipt_id: int, n_findings: int) -> None:
    await audit.record(s, actor, "contract.created", record_type="contract", record_id=c.id, record_ref=c.ref,
                       after={"title": c.title, "counterparty": c.counterparty_name, "findings": n_findings}, receipt_id=receipt_id)


async def party_name(s: AsyncSession, party_id: int | None) -> str | None:
    if not party_id:
        return None
    p = await s.get(Party, party_id)
    return p.name if p else None
