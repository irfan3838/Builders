"""Intake tools: inspect an uploaded document, correct fields by voice, match reservations, close intake."""

from __future__ import annotations

from typing import Literal

from agents import RunContextWrapper, function_tool

from app import db
from app.agent import reading
from app.agent.context import MunshiContext, safe_tool
from app.errors import DomainError
from app.models import Conversation
from app.money import format_inr, rupees_to_paise
from app.services import intake, records

Ctx = RunContextWrapper[MunshiContext]


def _view(fields: dict, arithmetic: str, doc_type: str) -> dict:
    money = lambda k: format_inr(fields[k]) if fields.get(k) else None  # noqa: E731
    return {
        "doc_type": doc_type, "why": fields.get("doc_type_reason"), "vendor": fields.get("vendor"),
        "customer_or_guest": fields.get("customer_or_guest"), "date": fields.get("date"), "due_date": fields.get("due_date"),
        "invoice_no": fields.get("invoice_no"), "currency": fields.get("currency"), "total": money("total_paise"),
        "subtotal": money("subtotal_paise"), "taxes": [f"{t['label']}: {format_inr(t['amount_paise'] or 0)}" for t in fields.get("taxes") or []],
        "line_items": len(fields.get("line_items") or []), "payment_status": fields.get("payment_status"),
        "payment_evidence": fields.get("payment_evidence"), "stay": [fields.get("stay_check_in"), fields.get("stay_check_out")],
        "arithmetic": {"ok": "breakdown adds up to the total",
                       "mismatch": "BREAKDOWN DOES NOT ADD UP — pause and ask for a correction",
                       "unverifiable": "could not verify the breakdown (total only)"}[arithmetic],
        "breakdown_sum": format_inr(s) if (s := intake.breakdown_sum(fields)) is not None else None,
        "legibility_notes": fields.get("legibility_notes"),
    }


@function_tool
@safe_tool
async def inspect_document(ctx: Ctx, document_id: int) -> dict:
    """Read an uploaded document (runs extraction the first time). Returns type, fields, arithmetic check,
    probable duplicates, matching company payments and open reservations. Use before routing a receipt or bill."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        doc = await records.document(s, a, document_id)
        ex = await records.extraction(s, a, doc.id)
        if doc.outcome and doc.outcome not in ("claim", "bill"):
            return {"ok": True, "document_id": doc.id, "closed": True, "outcome": doc.outcome, "reason": doc.outcome_reason}
        if doc.outcome in ("claim", "bill"):
            return {"ok": True, "document_id": doc.id, "closed": True, **(await intake.describe_outcome(s, a, doc))}
    if ex is None:
        try:
            ex = await reading.ensure_extraction(a, document_id)
        except DomainError:
            raise
        except Exception as e:  # provider/parse failure is reported aloud, never guessed
            return {"ok": False, "code": "EXTRACTION_FAILED", "message": f"Could not read the document ({type(e).__name__}). Ask the user to re-upload a clearer copy."}
    async with db.session_scope() as s:
        f = records.effective_fields(ex)
        dups = await intake.probable_duplicates(s, a, document_id, f)
        pays = await intake.company_payment_matches(s, a, f)
        res = await intake.reservation_candidates(s, a, f) if ex.doc_type == "receipt" else []
        if a.conversation_id:
            conv = await s.get(Conversation, a.conversation_id)
            if conv:
                conv.current_document_id = document_id
    ctx.context.show({"card": "source", "document_id": document_id, "highlight": ["vendor", "date", "total_paise"]})
    next_step = {
        "contract": "Tell the user contract review is outside this release, then close_intake(outcome='contract_out_of_scope').",
        "uncertain": "Ask the user what kind of document this is before doing anything else.",
        "bank_statement": "Bank statements are not supported yet; close_intake(outcome='unsupported').",
        "other": "Ask the user what this document is for; it does not look like a receipt or bill.",
    }.get(ex.doc_type, "Resolve the economic event: did an employee pay, did the company already pay, or is the vendor still owed?")
    if dups:
        next_step = "Probable duplicate found. Read it to the user and resolve before submitting anything. " + next_step
    return {"ok": True, "document_id": document_id, **_view(f, ex.arithmetic, ex.doc_type), "corrections": ex.corrections,
            "probable_duplicates": dups, "company_payment_matches": pays, "open_reservations": res, "next_step": next_step}


@function_tool
@safe_tool
async def correct_extracted_field(ctx: Ctx, document_id: int, field: Literal["vendor", "date", "total", "invoice_no", "due_date", "currency"], value: str) -> dict:
    """Apply the user's spoken correction to an extracted field. Dates as YYYY-MM-DD; total in rupees (e.g. '4800').
    Returns the updated preview; any earlier proposal for this document must be re-proposed."""
    a = ctx.context.actor
    key = "total_paise" if field == "total" else field
    val: object = value.strip()
    if key == "total_paise":
        try:
            val = rupees_to_paise(str(val).replace(",", "").replace("₹", ""))
        except Exception as e:
            raise DomainError("VALIDATION", f"'{value}' is not an amount.") from e
    async with db.session_scope() as s:
        doc = await records.document(s, a, document_id, for_update=True)
        ex = await records.extraction(s, a, doc.id)
        if ex is None:
            raise DomainError("INVALID_STATE", "Inspect the document first.")
        await intake.correct_field(s, a, doc, ex, key, val)
        f = records.effective_fields(ex)
    ctx.context.show({"card": "source", "document_id": document_id, "highlight": [key]})
    return {"ok": True, "updated": _view(f, ex.arithmetic, ex.doc_type), "note": "Correction recorded with the original value kept in history."}


@function_tool
@safe_tool
async def find_reservations(ctx: Ctx, document_id: int, employee_party_id: int) -> dict:
    """Open budget reservations for an employee that this receipt could replace (e.g. a hotel booked for a trip)."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        ex = await records.extraction(s, a, document_id)
        f = records.effective_fields(ex) if ex else {}
        cands = await intake.reservation_candidates(s, a, f, employee_party_id)
    return {"ok": True, "reservations": cands,
            "guidance": "If exactly one matches and the user says this receipt is the full/final charge, use reservation_treatment='final'. "
                        "For a partial stay or unclear match, ask."}


@function_tool
@safe_tool
async def close_intake(ctx: Ctx, document_id: int,
                       outcome: Literal["contract_out_of_scope", "unsupported", "matched_payment", "reconciliation", "duplicate", "not_business"],
                       reason: str) -> dict:
    """Finish intake WITHOUT any finance write, with an explicit outcome (contract, already-paid by company, duplicate, ...)."""
    async with db.session_scope() as s:
        doc = await records.document(s, ctx.context.actor, document_id, for_update=True)
        await intake.close(s, ctx.context.actor, doc, outcome, reason)
    return {"ok": True, "document_id": document_id, "outcome": outcome, "finance_records_created": 0}


@function_tool
@safe_tool
async def show_source(ctx: Ctx, document_id: int, field: Literal["vendor", "date", "total", "all"] = "all") -> dict:
    """Show the original document page on screen, highlighting where a field was read from."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        await records.document(s, a, document_id)
        ex = await records.extraction(s, a, document_id)
    key = "total_paise" if field == "total" else field
    cite = (ex.evidence or {}).get(key) if ex and key != "all" else None
    ctx.context.show({"card": "source", "document_id": document_id, "highlight": [key] if key != "all" else ["vendor", "date", "total_paise"]})
    return {"ok": True, "shown": True, "citation": cite}


TOOLS = [inspect_document, correct_extracted_field, find_reservations, close_intake, show_source]
