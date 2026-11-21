"""Contract writes as propose -> present -> confirm -> receipt actions (the same trust boundary as bills and revenue).

Values a person decides (title, type, the counterparty, dates, a decision) come from the model's arguments and are
read back in the preview; amounts, caps and periods only ever come from the contract text, parsed by code.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import delete, select

from app.errors import INVALID_STATE, VALIDATION, DomainError
from app.models import Contract, ContractDeadline, ContractFinding
from app.services import audit, intake, records
from app.services.actions import Execution, Plan
from app.services.contracts import liability, review, scan, store
from app.services.contracts.catalogue import CONTRACT_TYPES, NAMES

STATUSES = ("active", "expired", "terminated")


def _iso(v: str | None, what: str) -> date | None:
    if v in (None, ""):
        return None
    try:
        return date.fromisoformat(str(v).strip())
    except ValueError as e:
        raise DomainError(VALIDATION, f"'{v}' is not a date for {what} (use YYYY-MM-DD).") from e


def _type(v: str | None) -> str | None:
    if v is None:
        return None
    k = str(v).strip().lower()
    if k not in CONTRACT_TYPES:
        raise DomainError(VALIDATION, f"Contract type must be one of {', '.join(CONTRACT_TYPES)}.")
    return k


def _fmt(d: date | None) -> str:
    return d.strftime("%d %b %Y") if d else "not stated"


async def _staged(s, actor, args):
    review.require_view(actor)
    doc = await records.document(s, actor, int(args["document_id"]))
    if doc.outcome:
        raise DomainError(INVALID_STATE, f"Document {doc.id} intake is already closed as {doc.outcome}.")
    ex = await records.extraction(s, actor, doc.id)
    staged = (ex.fields or {}).get("contract_review") if ex else None
    if not staged:
        raise DomainError(INVALID_STATE, "Review the contract first (review_contract).")
    dup = (await s.execute(select(Contract).where(Contract.workspace_id == actor.workspace_id, Contract.document_id == doc.id))).scalars().first()
    if dup:
        raise DomainError(INVALID_STATE, f"This document is already contract {dup.ref}.")
    counterparty = (args.get("counterparty") or staged.get("counterparty") or "").strip() or None
    if args.get("counterparty") and not liability._has(staged["text"], counterparty):
        raise DomainError(VALIDATION, f"'{counterparty}' is not named in the contract text. Say the name as written in the contract.")
    party_id = await store.match_party(s, actor, counterparty)
    title = (args.get("title") or staged["title"]).strip()[:200]
    ctype = _type(args.get("contract_type")) or staged["contract_type"]
    return doc, staged, title, ctype, counterparty, party_id


class CreateContract:
    kind = "create_contract"

    async def plan(self, s, actor, args):
        doc, staged, title, ctype, cp, party_id = await _staged(s, actor, args)
        det = staged["details"]
        risky = [f for f in staged["findings"] if f["state"] == "proposed"]
        us = [f for f in risky if (f.get("liability") or {}).get("bearer") == "us"]
        lines = [f"Save contract '{title}' ({CONTRACT_TYPES[ctype]}) with {cp or 'an unnamed counterparty'}"
                 + (f", linked to {await store.party_name(s, party_id)}" if party_id else "") + ".",
                 f"Effective {_fmt(store._date((det.get('effective_on') or {}).get('value')))}, "
                 f"ends {_fmt(store._date((det.get('expiry_on') or {}).get('value')))}.",
                 f"{len(staged['findings'])} clauses found; {len(risky)} flagged for review, {len(us)} of them bind us.",
                 f"{len(staged['deadlines'])} dated obligation(s) tracked."]
        if staged.get("coverage_note"):
            lines.append(staged["coverage_note"])
        return Plan("Save contract", lines, f"Save '{title}' with {len(risky)} flags for review?",
                    [{"table": "documents", "id": doc.id, "version": doc.version}])

    async def execute(self, s, actor, args, receipt_id):
        doc, staged, title, ctype, cp, party_id = await _staged(s, actor, args)
        c = await store.create_from_review(s, actor, doc, staged, title=title, contract_type=ctype, counterparty=cp, party_id=party_id)
        doc_locked = await records.document(s, actor, doc.id, for_update=True)
        await intake.close(s, actor, doc_locked, "contract", f"Saved as contract {c.ref}")
        await store.record_created(s, actor, c, receipt_id, len(staged["findings"]))
        flags = sum(1 for f in staged["findings"] if f["state"] == "proposed")
        return Execution(f"Contract {c.ref} '{c.title}' saved with {flags} flag(s) for review.",
                         [{"type": "contract", "ref": c.ref, "contract_id": c.id}])


async def _finding_inputs(s, actor, args):
    review.require_decide(actor)
    f, c = await store.finding(s, actor, int(args["finding_id"]))
    decision = str(args.get("decision") or "").lower()
    if decision not in ("accept", "reject", "modify"):
        raise DomainError(VALIDATION, "Decision must be accept, reject or modify.")
    if f.state == "tagged" and decision != "modify":
        raise DomainError(INVALID_STATE, "This is a standard clause tag, not a flag; only 'modify' can raise its risk.")
    risk = args.get("risk")
    if risk is not None and risk not in ("high", "medium", "low", "standard"):
        raise DomainError(VALIDATION, "Risk must be high, medium, low or standard.")
    bearer = args.get("bearer")
    if bearer is not None and bearer not in ("us", "counterparty", "mutual", "unclear"):
        raise DomainError(VALIDATION, "Bearer must be us, counterparty, mutual or unclear.")
    if decision == "modify" and not (risk or args.get("explanation") or bearer):
        raise DomainError(VALIDATION, "To modify, give a new risk level, bearer or explanation.")
    return f, c, decision, risk, bearer


class ReviewFinding:
    kind = "review_contract_finding"

    async def plan(self, s, actor, args):
        f, c, decision, risk, bearer = await _finding_inputs(s, actor, args)
        name = NAMES.get(f.clause_type, f.clause_type)
        verb = {"accept": "Accept (the risk stands)", "reject": "Reject as a false positive", "modify": "Modify"}[decision]
        lines = [f"{verb}: {name} (#{f.id}) in {c.ref} '{c.title}', now {f.risk} risk, {f.state}."]
        if risk:
            lines.append(f"Risk {f.risk} -> {risk}.")
        if bearer:
            lines.append(f"Who bears it: {f.bearer or 'unclear'} -> {bearer}.")
        if args.get("explanation"):
            lines.append(f"Explanation: {args['explanation'][:400]}")
        if decision == "reject" or risk == "standard":
            lines.append("It leaves the liabilities list; the decision is kept in history.")
        return Plan("Review contract flag", lines, f"{verb.split(' (')[0]} the {name} flag on {c.ref}?",
                    [{"table": "contract_findings", "id": f.id, "version": f.version}])

    async def execute(self, s, actor, args, receipt_id):
        f, c, decision, risk, bearer = await _finding_inputs(s, actor, args)
        before = {"state": f.state, "risk": f.risk, "bearer": f.bearer}
        f.state = {"accept": "accepted", "reject": "rejected", "modify": "modified"}[decision]
        if risk:
            f.risk = risk
        if bearer:
            f.bearer, f.liability_source = bearer, "reviewer"
        if args.get("explanation"):
            f.explanation = str(args["explanation"])[:400]
        if args.get("comment"):
            f.comment = str(args["comment"])[:500]
        f.reviewer_id, f.reviewed_at, f.version = actor.user_id, datetime.now(UTC), f.version + 1
        await audit.record(s, actor, "contract.finding_reviewed", record_type="contract_finding", record_id=f.id, record_ref=c.ref,
                           before=before, after={"state": f.state, "risk": f.risk, "bearer": f.bearer}, receipt_id=receipt_id)
        return Execution(f"{NAMES.get(f.clause_type, f.clause_type)} on {c.ref} {f.state}.",
                         [{"type": "contract_finding", "finding_id": f.id, "state": f.state}])


async def recompute_deadlines(s, actor, c: Contract) -> None:
    """Deadlines follow the contract's current expiry and its auto-renewal notice periods (code, not model)."""
    await s.execute(delete(ContractDeadline).where(ContractDeadline.contract_id == c.id, ContractDeadline.workspace_id == c.workspace_id))
    rows = (await s.execute(select(ContractFinding).where(ContractFinding.contract_id == c.id,
                                                          ContractFinding.workspace_id == c.workspace_id))).scalars().all()
    found = [scan.Found(r.clause_type, r.start, r.stop, r.quote, r.risk, r.confidence) for r in rows]
    lis = {i: liability.Liability(notice_days=r.notice_days) for i, r in enumerate(rows) if r.clause_type == "auto_renewal"}
    for d in liability.deadlines(c.text, found, lis, c.effective_on, c.expiry_on, "Contract end date"):
        s.add(ContractDeadline(workspace_id=c.workspace_id, contract_id=c.id, kind=d.kind, due_on=d.due_on, basis=d.basis,
                               finding_id=rows[d.finding_index].id if d.finding_index is not None else None))
    await s.flush()


async def _details_inputs(s, actor, args):
    review.require_decide(actor)
    c = await store.by_mention(s, actor, args["contract"])
    changes: dict = {}
    if args.get("title"):
        changes["title"] = str(args["title"]).strip()[:200]
    if args.get("contract_type"):
        changes["contract_type"] = _type(args["contract_type"])
    if args.get("counterparty"):
        cp = str(args["counterparty"]).strip()
        if not liability._has(c.text, cp):
            raise DomainError(VALIDATION, f"'{cp}' is not named in the contract text.")
        changes["counterparty_name"] = cp
    if args.get("party_name"):
        p = await records.resolve_single_party(s, actor, str(args["party_name"]))
        if p["kind"] not in ("customer", "vendor"):
            raise DomainError(VALIDATION, f"{p['name']} is not a customer or vendor.")
        changes["party_id"] = p["party_id"]
    for k in ("effective_on", "expiry_on"):
        if args.get(k):
            changes[k] = _iso(args[k], k.replace("_on", ""))
    eff, exp = changes.get("effective_on", c.effective_on), changes.get("expiry_on", c.expiry_on)
    if eff and exp and exp < eff:
        raise DomainError(VALIDATION, "The end date is before the start date.")
    if not changes:
        raise DomainError(VALIDATION, "Nothing to change. Give a title, type, counterparty, linked party or dates.")
    return c, changes


class SetContractDetails:
    kind = "set_contract_details"

    async def plan(self, s, actor, args):
        c, changes = await _details_inputs(s, actor, args)
        lines = [f"Update {c.ref} '{c.title}':"]
        for k, v in changes.items():
            old = getattr(c, k)
            if k == "party_id":
                old, v = await store.party_name(s, old), await store.party_name(s, v)
                k = "linked party"
            lines.append(f"{k.replace('_', ' ')}: {old if old is not None else 'none'} -> {v}")
        if "expiry_on" in changes:
            lines.append("Expiry and renewal-notice deadlines are recomputed.")
        return Plan("Update contract", lines, f"Update {c.ref} as shown?", [{"table": "contracts", "id": c.id, "version": c.version}])

    async def execute(self, s, actor, args, receipt_id):
        c, changes = await _details_inputs(s, actor, args)
        before = {k: str(getattr(c, k)) for k in changes}
        for k, v in changes.items():
            setattr(c, k, v)
        c.version += 1
        if "expiry_on" in changes or "effective_on" in changes:
            await recompute_deadlines(s, actor, c)
        await audit.record(s, actor, "contract.updated", record_type="contract", record_id=c.id, record_ref=c.ref,
                           before=before, after={k: str(v) for k, v in changes.items()}, receipt_id=receipt_id)
        return Execution(f"{c.ref} updated.", [{"type": "contract", "ref": c.ref, "contract_id": c.id}])


class SetContractStatus:
    kind = "set_contract_status"

    async def _inputs(self, s, actor, args):
        review.require_decide(actor)
        c = await store.by_mention(s, actor, args["contract"])
        st = str(args.get("status") or "").lower()
        if st not in STATUSES:
            raise DomainError(VALIDATION, f"Status must be one of {', '.join(STATUSES)}.")
        if st == c.status:
            raise DomainError(INVALID_STATE, f"{c.ref} is already {st}.")
        if c.status == "terminated":
            raise DomainError(INVALID_STATE, "A terminated contract cannot change status.")
        return c, st

    async def plan(self, s, actor, args):
        c, st = await self._inputs(s, actor, args)
        lines = [f"{c.ref} '{c.title}': {c.status} -> {st}."]
        if st != "active":
            lines.append("Its deadlines leave the reminders.")
        return Plan("Change contract status", lines, f"Mark {c.ref} as {st}?", [{"table": "contracts", "id": c.id, "version": c.version}])

    async def execute(self, s, actor, args, receipt_id):
        c, st = await self._inputs(s, actor, args)
        before, c.status, c.version = c.status, st, c.version + 1
        await audit.record(s, actor, "contract.status_changed", record_type="contract", record_id=c.id, record_ref=c.ref,
                           before={"status": before}, after={"status": st}, receipt_id=receipt_id)
        return Execution(f"{c.ref} is now {st}.", [{"type": "contract", "ref": c.ref, "contract_id": c.id}])


class RescanContract:
    """Copilot rescan: replaces automated proposed/tagged rows, keeps manual findings and reviewed decisions, and
    skips fresh hits that overlap a preserved finding of the same type."""

    kind = "rescan_contract"

    async def plan(self, s, actor, args):
        review.require_decide(actor)
        c = await store.by_mention(s, actor, args["contract"])
        fs, _ = await store.load_full(s, c)
        kept = [f for f in fs if f.source != "ai" or f.state not in ("proposed", "tagged")]
        return Plan("Rescan contract", [f"Re-read {c.ref} '{c.title}' with the current clause catalogue.",
                                        f"{len(fs) - len(kept)} automated finding(s) are replaced; {len(kept)} reviewed or manual kept.",
                                        "Deadlines are recomputed."],
                    f"Rescan {c.ref}?", [{"table": "contracts", "id": c.id, "version": c.version}])

    async def execute(self, s, actor, args, receipt_id):
        review.require_decide(actor)
        c = await store.by_mention(s, actor, args["contract"], for_update=True)
        fs, _ = await store.load_full(s, c)
        kept = [f for f in fs if f.source != "ai" or f.state not in ("proposed", "tagged")]
        await s.execute(delete(ContractFinding).where(ContractFinding.contract_id == c.id, ContractFinding.workspace_id == c.workspace_id,
                                                      ContractFinding.source == "ai", ContractFinding.state.in_(("proposed", "tagged"))))
        staged = await review.analyse(c.text, (c.details or {}).get("filename", ""), await review.our_names(s, actor))
        fresh = [f for f in staged["findings"]
                 if not any(k.clause_type == f["clause_type"] and f["start"] < k.stop and k.start < f["stop"] for k in kept)]
        await store.add_findings(s, actor, c, fresh, [])
        c.scanned_by_model, c.version = bool(staged["scanned_by_model"]), c.version + 1
        await recompute_deadlines(s, actor, c)
        await audit.record(s, actor, "contract.rescanned", record_type="contract", record_id=c.id, record_ref=c.ref,
                           after={"fresh": len(fresh), "kept": len(kept)}, receipt_id=receipt_id)
        return Execution(f"{c.ref} rescanned: {len(fresh)} new finding(s), {len(kept)} kept.",
                         [{"type": "contract", "ref": c.ref, "contract_id": c.id}])


CONTRACT_ACTIONS = (CreateContract(), ReviewFinding(), SetContractDetails(), SetContractStatus(), RescanContract())
