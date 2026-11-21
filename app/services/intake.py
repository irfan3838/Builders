"""Upload intake: validate, store, de-duplicate by hash, render pages, extract, check arithmetic.

Every upload gets an explicit outcome. Document contents are evidence, never instructions.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from datetime import date, timedelta

import filetype
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.config import get_settings
from app.errors import DomainError
from app.models import Bill, Claim, CompanyPayment, Document, Extraction, Party, Reservation, Trip
from app.money import format_inr
from app.services import audit, records, storage

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ALLOWED = {"application/pdf", "image/jpeg", "image/png", DOCX}


@dataclass
class UploadResult:
    document_id: int | None
    outcome: str  # accepted | exact_replay | unsupported | too_large | too_many_pages | encrypted | unreadable
    message: str
    existing: dict | None = None


def _pdf_pages(data: bytes) -> tuple[int | None, str | None]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        r = PdfReader(io.BytesIO(data))
        if r.is_encrypted:
            return None, "encrypted"
        return len(r.pages), None
    except (PdfReadError, Exception):
        return None, "unreadable"


async def accept_upload(s: AsyncSession, actor: Actor, filename: str, data: bytes) -> UploadResult:
    st = get_settings()
    max_bytes = max(st.upload_max_bytes, st.contract_max_bytes)  # bills are re-checked against their own limit at intake
    if len(data) > max_bytes:
        return UploadResult(None, "too_large", f"The file is {len(data) // 1024 // 1024} MB; the limit is {max_bytes // 1024 // 1024} MB.")
    kind = filetype.guess(data)
    media = kind.mime if kind else "application/octet-stream"
    if media not in ALLOWED:
        return UploadResult(None, "unsupported", f"This file type ({media}) is not supported. Upload a PDF, JPEG or PNG receipt or bill, or a PDF/Word contract.")
    pages = 1
    if media == "application/pdf":
        n, err = _pdf_pages(data)
        if err == "encrypted":
            return UploadResult(None, "encrypted", "The PDF is password protected, so I cannot read it. Upload an unlocked copy.")
        if err:
            return UploadResult(None, "unreadable", "I could not read this PDF. It may be damaged.")
        pages = n or 0
        max_pages = max(st.upload_max_pages, st.contract_max_pages)  # bills: upload_max_pages, enforced at intake
        if pages > max_pages:
            return UploadResult(None, "too_many_pages", f"The PDF has {pages} pages; this release reads up to {max_pages}.")

    sha = hashlib.sha256(data).hexdigest()
    prior = (await s.execute(select(Document).where(Document.workspace_id == actor.workspace_id, Document.sha256 == sha)
                             .order_by(Document.id))).scalars().first()
    if prior is not None:
        if not actor.is_approver and prior.uploader_id != actor.user_id:
            # Do not reveal another user's document or record; just say it is already in the books.
            return UploadResult(None, "exact_replay", "This exact file was already submitted by someone else in your company.")
        existing = await describe_outcome(s, actor, prior)
        return UploadResult(prior.id, "exact_replay", "This exact file was uploaded before.", existing)

    doc = Document(workspace_id=actor.workspace_id, uploader_id=actor.user_id, storage_key="pending", filename=filename[:300],
                   sha256=sha, media_type=media, pages=pages, size_bytes=len(data))
    s.add(doc)
    await s.flush()
    doc.storage_key = f"ws{actor.workspace_id}/documents/{doc.id}/{sha[:16]}"
    await storage.put(doc.storage_key, data, media)
    await audit.record(s, actor, "document.uploaded", record_type="document", record_id=doc.id,
                       after={"media_type": media, "pages": pages, "size_bytes": len(data)})
    return UploadResult(doc.id, "accepted", "Received.")


async def describe_outcome(s: AsyncSession, actor: Actor, doc: Document) -> dict:
    out = {"document_id": doc.id, "status": doc.status, "outcome": doc.outcome}
    if doc.outcome == "contract":
        from app.models import Contract

        c = (await s.execute(select(Contract).where(Contract.workspace_id == actor.workspace_id, Contract.document_id == doc.id))).scalars().first()
        if c:
            out.update(record_ref=c.ref, title=c.title)
    if doc.outcome in ("claim", "bill"):
        model = Claim if doc.outcome == "claim" else Bill
        rec = (await s.execute(select(model).where(model.workspace_id == actor.workspace_id, model.document_id == doc.id))).scalars().first()
        if rec:
            out.update(record_ref=rec.ref, record_state=rec.state, settlement_state=rec.settlement_state, amount=format_inr(rec.amount_paise))
    return out


def render_pages(data: bytes, media: str, *, scale: float = 2.0, max_pages: int = 5) -> list[bytes]:
    """Return PNG bytes per page (images pass through as a single page)."""
    if media != "application/pdf":
        return [data]
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    out = []
    for i in range(min(len(pdf), max_pages)):
        img = pdf[i].render(scale=scale).to_pil()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        out.append(buf.getvalue())
    return out


# ------------------------------------------------------------------ validation


def check_arithmetic(fields: dict) -> str:
    """ok | mismatch | unverifiable. Only checks when components exist. Tolerance ₹1 for rounding."""
    total, expected = fields.get("total_paise"), breakdown_sum(fields)
    if not total or expected is None:
        return "unverifiable"
    return "ok" if abs(expected - int(total)) <= 100 else "mismatch"


def breakdown_sum(fields: dict) -> int | None:
    """Sum of printed components (subtotal or line items, plus taxes and charges, minus discount), or None."""
    taxes = sum(int(t.get("amount_paise") or 0) for t in fields.get("taxes") or [])
    sub = fields.get("subtotal_paise")
    items = [int(li.get("amount_paise") or 0) for li in fields.get("line_items") or [] if li.get("amount_paise") is not None]
    if sub:
        expected = int(sub) + taxes + int(fields.get("other_charges_paise") or 0) - int(fields.get("discount_paise") or 0)
    elif items:
        expected = sum(items) + taxes + int(fields.get("other_charges_paise") or 0) - int(fields.get("discount_paise") or 0)
    else:
        return None
    return expected


# ------------------------------------------------------------------ duplicates and matching


def _similar(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    a, b = records.normalize_name(a or ""), records.normalize_name(b or "")
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 0.95
    return SequenceMatcher(None, a, b).ratio()


async def probable_duplicates(s: AsyncSession, actor: Actor, doc_id: int, fields: dict) -> list[dict]:
    """Same party, same amount, business date within three days (v4 §2.3)."""
    amt, d, party = fields.get("total_paise"), fields.get("date"), fields.get("vendor")
    if not (amt and d and party):
        return []
    day = date.fromisoformat(d)
    lo, hi = day - timedelta(days=3), day + timedelta(days=3)
    out = []
    claims = (await s.execute(select(Claim).where(Claim.workspace_id == actor.workspace_id, Claim.amount_paise == amt,
                                                  Claim.business_date.between(lo, hi)))).scalars().all()
    for c in claims:
        if c.document_id != doc_id and _similar(c.merchant, party) >= 0.75:
            out.append({"type": "claim", "ref": c.ref, "merchant": c.merchant, "amount": format_inr(c.amount_paise),
                        "date": c.business_date.isoformat(), "state": c.state, "settlement_state": c.settlement_state})
    bills = (await s.execute(select(Bill, Party).join(Party, Party.id == Bill.vendor_party_id).where(
        Bill.workspace_id == actor.workspace_id, Bill.amount_paise == amt, Bill.business_date.between(lo, hi)))).all()
    for b, p in bills:
        if b.document_id != doc_id and _similar(p.name, party) >= 0.75:
            out.append({"type": "bill", "ref": b.ref, "vendor": p.name, "amount": format_inr(b.amount_paise),
                        "date": b.business_date.isoformat(), "state": b.state, "settlement_state": b.settlement_state})
    return out


async def company_payment_matches(s: AsyncSession, actor: Actor, fields: dict) -> list[dict]:
    amt, d, party = fields.get("total_paise"), fields.get("date"), fields.get("vendor")
    if not (amt and party):
        return []
    q = select(CompanyPayment).where(CompanyPayment.workspace_id == actor.workspace_id, CompanyPayment.amount_paise == amt)
    out = []
    for p in (await s.execute(q)).scalars().all():
        if _similar(p.payee_name, party) >= 0.7 and (not d or abs((p.paid_on - date.fromisoformat(d)).days) <= 5):
            out.append({"payment_id": p.id, "payee": p.payee_name, "amount": format_inr(p.amount_paise),
                        "paid_on": p.paid_on.isoformat(), "reference": p.reference, "method": p.method})
    return out


async def reservation_candidates(s: AsyncSession, actor: Actor, fields: dict, employee_party_id: int | None = None) -> list[dict]:
    """Open reservations whose trip dates cover the document date. Trip dates alone never pick the employee."""
    q = select(Reservation, Trip, Party).join(Trip, Trip.id == Reservation.trip_id, isouter=True).join(
        Party, Party.id == Reservation.employee_party_id, isouter=True).where(
        Reservation.workspace_id == actor.workspace_id, Reservation.status == "open")
    if employee_party_id:
        q = q.where(Reservation.employee_party_id == employee_party_id)
    d = date.fromisoformat(fields["date"]) if fields.get("date") else None
    out = []
    for r, t, p in (await s.execute(q)).all():
        covers = bool(t and d and t.start_date - timedelta(days=1) <= d <= t.end_date + timedelta(days=1))
        out.append({"reservation_id": r.id, "ref": r.ref, "employee": p.name if p else None, "employee_party_id": r.employee_party_id,
                    "description": r.description, "amount": format_inr(r.amount_paise), "amount_paise": r.amount_paise,
                    "trip": f"{t.city} {t.start_date:%d %b}–{t.end_date:%d %b}" if t else None, "date_within_trip": covers})
    out.sort(key=lambda x: not x["date_within_trip"])
    return out


async def save_extraction(s: AsyncSession, actor: Actor, doc: Document, doc_type: str, fields: dict, evidence: dict,
                          model: str, latency_ms: int) -> Extraction:
    ex = Extraction(workspace_id=actor.workspace_id, document_id=doc.id, doc_type=doc_type, fields=fields, evidence=evidence,
                    arithmetic=check_arithmetic(fields), model=model, latency_ms=latency_ms)
    s.add(ex)
    doc.status, doc.version = "inspected", doc.version + 1
    await s.flush()
    await audit.record(s, actor, "document.extracted", record_type="document", record_id=doc.id,
                       after={"doc_type": doc_type, "arithmetic": ex.arithmetic, "model": model})
    return ex


CORRECTABLE = {"vendor", "date", "total_paise", "invoice_no", "due_date", "currency"}


async def correct_field(s: AsyncSession, actor: Actor, doc: Document, ex: Extraction, field: str, value) -> Extraction:
    from datetime import UTC, datetime

    if field not in CORRECTABLE:
        raise DomainError("VALIDATION", f"'{field}' cannot be corrected here. Correctable: {sorted(CORRECTABLE)}")
    try:
        if field in ("date", "due_date"):
            value = date.fromisoformat(str(value).strip()).isoformat()
        if field == "total_paise":
            value = int(value)
    except (TypeError, ValueError) as e:
        hint = "a date as YYYY-MM-DD" if field in ("date", "due_date") else "a whole amount"
        raise DomainError("VALIDATION", f"'{value}' is not {hint}.") from e
    if field == "total_paise":
        if value <= 0:
            raise DomainError("VALIDATION", "Amount must be positive.")
    old = records.effective_fields(ex).get(field)
    ex.corrections = [*(ex.corrections or []), {"field": field, "value": value, "previous": old, "at": datetime.now(UTC).isoformat()}]
    doc.version += 1
    await audit.record(s, actor, "document.corrected", record_type="document", record_id=doc.id, before={field: old}, after={field: value})
    await s.flush()
    return ex


async def close(s: AsyncSession, actor: Actor, doc: Document, outcome: str, reason: str) -> Document:
    allowed = {"contract", "contract_out_of_scope", "unsupported", "matched_payment", "reconciliation", "duplicate", "not_business", "failed"}
    if outcome not in allowed:
        raise DomainError("VALIDATION", f"Outcome must be one of {sorted(allowed)}")
    if doc.outcome:
        raise DomainError("INVALID_STATE", f"Intake already closed as {doc.outcome}.")
    doc.outcome, doc.outcome_reason, doc.status, doc.version = outcome, reason[:500], "closed", doc.version + 1
    await audit.record(s, actor, "document.closed", record_type="document", record_id=doc.id, after={"outcome": outcome, "reason": reason[:500]})
    return doc
