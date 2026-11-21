"""Contract tools: review an uploaded agreement, read liabilities / deadlines / flags across the portfolio, and propose
the confirmed writes. Reads come from stored findings (SQL), never from the model's memory of the text."""

from __future__ import annotations

from typing import Literal

from agents import RunContextWrapper, function_tool

from app import db
from app.agent.context import PurserContext, safe_tool
from app.agent.tools.proposals import _propose
from app.errors import DomainError
from app.money import format_inr
from app.services.contracts import review, store
from app.services.contracts.catalogue import CONTRACT_TYPES, NAMES

Ctx = RunContextWrapper[PurserContext]
REVIEW_WAIT_SECONDS = 25  # a voice turn has a 90 s budget; extraction may already have used part of it
Bearer = Literal["us", "counterparty", "mutual", "unclear"]
CAVEAT = ("This is an automated reading of the wording: say it is for Legal to confirm, and never call the contract safe or "
          "complete. Name who bears each liability; if a bearer is 'unclear', say so.")


def _staged_view(document_id: int, st: dict) -> dict:
    risky = [f for f in st["findings"] if f["state"] == "proposed"]

    def one(f: dict) -> dict:
        li = f.get("liability") or {}
        return {"clause": NAMES.get(f["clause_type"], f["clause_type"]), "risk": f["risk"], "quote": " ".join(f["quote"].split())[:300],
                "who_bears": store.BEARER_WORDS.get(li.get("bearer") or "unclear"), "bearer_term": li.get("bearer_term"),
                "beneficiary": li.get("beneficiary"), "cap": format_inr(li["cap_paise"]) if li.get("cap_paise") else None,
                "cap_basis": li.get("cap_basis"), "carve_outs": [c["quote"] for c in li.get("carve_outs") or []],
                "notice_days": li.get("notice_days")}

    det = st["details"]
    return {
        "document_id": document_id, "title": st["title"], "type": CONTRACT_TYPES.get(st["contract_type"]),
        "counterparty": st.get("counterparty"), "effective_on": (det.get("effective_on") or {}).get("value"),
        "expiry_on": (det.get("expiry_on") or {}).get("value"), "detail_notes": det.get("notes"),
        "flags_for_review": [one(f) for f in risky],
        "standard_clauses": sorted({NAMES.get(f["clause_type"], f["clause_type"]) for f in st["findings"] if f["state"] == "tagged"}),
        "caps": [one(f) for f in st["findings"] if f["clause_type"] == "limitation_of_liability"],
        "deadlines": st["deadlines"], "pages": st.get("pages"), "read_by": st.get("text_source"),
        "model_read_all": st.get("scanned_by_model"), "coverage_note": st.get("coverage_note"),
    }


@function_tool
@safe_tool
async def review_contract(ctx: Ctx, document_id: int) -> dict:
    """Read an uploaded contract (inspect_document said doc_type 'contract'): clauses, liabilities (who bears them, caps,
    carve-outs), notice periods and dated obligations. Nothing is saved; propose_create_contract saves it."""
    a = ctx.context.actor
    try:
        st = await review.ensure(a, document_id, wait_seconds=REVIEW_WAIT_SECONDS)
    except DomainError:
        raise
    except Exception as e:  # noqa: BLE001 - reported aloud, never guessed
        return {"ok": False, "code": "CONTRACT_READ_FAILED", "message": f"Could not read the contract ({type(e).__name__}). Ask for a clearer copy."}
    ctx.context.show({"card": "contract_review", "document_id": document_id})
    if st is None:
        return {"ok": True, "status": "still_reading", "document_id": document_id,
                "guidance": "Say you are still reading the contract (long or scanned agreements take up to a minute) and that "
                            "the summary will appear on screen; when the user asks again, call review_contract again. "
                            "Do not describe any finding yet."}
    return {"ok": True, **_staged_view(document_id, st), "guidance": CAVEAT + " Then offer to save it (propose_create_contract)."}


@function_tool
@safe_tool
async def propose_create_contract(ctx: Ctx, document_id: int, title: str | None = None,
                                  contract_type: Literal["nda", "msa", "sow", "vendor", "other"] | None = None,
                                  counterparty: str | None = None) -> dict:
    """Propose saving a reviewed contract with its findings and deadlines. Omit title/type/counterparty to keep what was
    read; pass them only when the user corrected them (the counterparty must be written in the contract)."""
    return await _propose(ctx, "create_contract", {"document_id": document_id, "title": title, "contract_type": contract_type,
                                                   "counterparty": counterparty})


@function_tool
@safe_tool
async def search_contracts(ctx: Ctx, words: str | None = None, counterparty: str | None = None,
                           contract_type: Literal["nda", "msa", "sow", "vendor", "other"] | None = None,
                           status: Literal["active", "expired", "terminated"] | None = None) -> dict:
    """Find contracts by words in their text/title, counterparty, type or status."""
    async with db.session_scope() as s:
        rows = await store.search(s, ctx.context.actor, words=words, contract_type=contract_type, status=status, counterparty=counterparty)
    ctx.context.show({"card": "record_list", "title_hint": "contracts",
                      "items": [{"kind": "contract", "ref": r["ref"], "who": r["counterparty"], "date": r["expiry_on"],
                                 "detail": f"{r['title']} · {r['open_flags']} open flag(s)", "amount": None} for r in rows[:10]]})
    return {"ok": True, "count": len(rows), "contracts": rows[:20]}


@function_tool
@safe_tool
async def get_contract(ctx: Ctx, contract: str) -> dict:
    """One contract by ref (AG3), title or counterparty: liabilities with who bears them, caps, carve-outs, deadlines."""
    async with db.session_scope() as s:
        c = await store.by_mention(s, ctx.context.actor, contract)
        fs, ds = await store.load_full(s, c)
        view = store.contract_view(c, fs, ds)
    ctx.context.show({"card": "contract", "ref": c.ref})
    return {"ok": True, **view, "guidance": CAVEAT}


@function_tool
@safe_tool
async def list_liabilities(ctx: Ctx, bearer: Bearer | None = None, risk: Literal["high", "medium", "low"] | None = None,
                           counterparty: str | None = None, contract: str | None = None, undecided_only: bool = False) -> dict:
    """Liabilities across contracts (risky clauses not rejected), with who bears each, caps and carve-outs.
    bearer='us' answers 'which liabilities are on us'. undecided_only=True lists only flags waiting for review."""
    async with db.session_scope() as s:
        rows = await store.liabilities(s, ctx.context.actor, bearer=bearer, risk=risk, counterparty=counterparty, contract=contract,
                                       include_decided=not undecided_only)
        ids = sorted({int(r["contract"][2:]) for r in rows})
        caps = await store.caps(s, ctx.context.actor, ids)
    ctx.context.show({"card": "contract_liabilities", "bearer": bearer, "risk": risk, "counterparty": counterparty,
                      "contract": contract, "undecided_only": undecided_only})
    return {"ok": True, "count": len(rows), "contracts": len({r["contract"] for r in rows}),
            "by_bearer": {b: sum(1 for r in rows if r["bearer"] == b) for b in ("us", "counterparty", "mutual", "unclear")},
            "caps_in_these_contracts": caps,
            "liabilities": rows[:15], "guidance": CAVEAT + " One contract can have several rows; count contracts separately."}


@function_tool
@safe_tool
async def contract_deadlines(ctx: Ctx, days: int = 90) -> dict:
    """Dated contract obligations in the next `days` days: expiry, renewal-notice cut-off, end of surviving duties."""
    async with db.session_scope() as s:
        rows = await store.deadlines(s, ctx.context.actor, days)
    ctx.context.show({"card": "contract_deadlines", "days": days})
    return {"ok": True, "days": days, "count": len(rows), "deadlines": rows}


@function_tool
@safe_tool
async def show_contract_clause(ctx: Ctx, finding_id: int) -> dict:
    """Show the contract text around one finding, with the cited words highlighted."""
    async with db.session_scope() as s:
        f, c = await store.finding(s, ctx.context.actor, finding_id)
        view = store.finding_view(f, c)
    ctx.context.show({"card": "contract_clause", "finding_id": finding_id})
    return {"ok": True, "shown": True, **view}


@function_tool
@safe_tool
async def propose_review_contract_finding(ctx: Ctx, finding_id: int, decision: Literal["accept", "reject", "modify"],
                                          risk: Literal["high", "medium", "low", "standard"] | None = None,
                                          bearer: Bearer | None = None, explanation: str | None = None,
                                          comment: str | None = None) -> dict:
    """Propose Legal's decision on a flag: accept (risk stands), reject (false positive, e.g. it binds only the other
    side), or modify (new risk, corrected bearer, or explanation). Admin only."""
    return await _propose(ctx, "review_contract_finding", {"finding_id": finding_id, "decision": decision, "risk": risk,
                                                           "bearer": bearer, "explanation": explanation, "comment": comment})


@function_tool
@safe_tool
async def propose_contract_details(ctx: Ctx, contract: str, title: str | None = None,
                                   contract_type: Literal["nda", "msa", "sow", "vendor", "other"] | None = None,
                                   counterparty: str | None = None, party_name: str | None = None,
                                   effective_on: str | None = None, expiry_on: str | None = None) -> dict:
    """Propose correcting a contract's details. party_name links it to an existing customer/vendor. Dates YYYY-MM-DD."""
    return await _propose(ctx, "set_contract_details", {"contract": contract, "title": title, "contract_type": contract_type,
                                                        "counterparty": counterparty, "party_name": party_name,
                                                        "effective_on": effective_on, "expiry_on": expiry_on})


@function_tool
@safe_tool
async def propose_contract_status(ctx: Ctx, contract: str, status: Literal["active", "expired", "terminated"]) -> dict:
    """Propose marking a contract active, expired or terminated."""
    return await _propose(ctx, "set_contract_status", {"contract": contract, "status": status})


@function_tool
@safe_tool
async def propose_rescan_contract(ctx: Ctx, contract: str) -> dict:
    """Propose re-reading a saved contract's text with the clause catalogue (keeps reviewed decisions)."""
    return await _propose(ctx, "rescan_contract", {"contract": contract})


TOOLS = [review_contract, propose_create_contract, search_contracts, get_contract, list_liabilities, contract_deadlines,
         show_contract_clause, propose_review_contract_finding, propose_contract_details, propose_contract_status,
         propose_rescan_contract]
