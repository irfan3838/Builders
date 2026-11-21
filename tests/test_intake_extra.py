"""Hours 4-7 coverage: intake service, SubmitBill new-vendor path, agent tools (no model calls) and the HTTP layer.
Maps to PLAN_v4 §2 items 1-4 and the §6 case list (duplicates, payer routing, wrong total, contract, cross-actor)."""

import io
import json

import httpx
import pytest
from pypdf import PdfWriter
from sqlalchemy import func, select

from app import db
from app.actor import Actor
from app.agent.context import PurserContext
from app.agent.tools import finance as finance_tools
from app.agent.tools import intake as intake_tools
from app.agent.tools import proposals as proposal_tools
from app.config import get_settings
from app.errors import FORBIDDEN, INVALID_STATE, NOT_FOUND, VALIDATION, DomainError
from app.main import app
from app.models import AuditEvent, Bill, BudgetMovement, Claim, Conversation, Document, Extraction, Party, Proposal, Receipt
from app.services import confirmation, intake, proposals, records
from seed.seed_v1 import seed
from tests.conftest import add_inspected_document, make_actor
from tests.test_api_intake import ORIGIN, PNG, client_for
from tests.test_ledger_gates import propose_and_confirm

R = 100
FINANCE_TABLES = (Bill, Claim, BudgetMovement)


# ------------------------------------------------------------------ helpers


async def count(model, *where) -> int:
    async with db.session_scope() as s:
        return (await s.execute(select(func.count()).select_from(model).where(*where))).scalar_one()


async def finance_counts() -> list[int]:
    return [await count(m) for m in FINANCE_TABLES]


async def add_doc(actor: Actor, fields: dict, *, doc_type="receipt", arithmetic=None, sha=None, status="inspected") -> int:
    """Document + Extraction with arbitrary fields (no model call)."""
    async with db.session_scope() as s:
        n = (await s.execute(select(func.count()).select_from(Document))).scalar_one()
        d = Document(workspace_id=actor.workspace_id, uploader_id=actor.user_id, storage_key="test/key", filename="x.pdf",
                     sha256=sha or f"{n + 1:064x}", media_type="application/pdf", pages=1, size_bytes=10, status=status)
        s.add(d)
        await s.flush()
        s.add(Extraction(workspace_id=actor.workspace_id, document_id=d.id, doc_type=doc_type, fields=fields,
                         arithmetic=arithmetic or intake.check_arithmetic(fields)))
        return d.id


def F(vendor="Sunrise Residency Pune", rupees=4800, day="2026-11-19", **extra) -> dict:
    return {"vendor": vendor, "date": day, "total_paise": rupees * R, "currency": "INR", **extra}


async def call(tool, actor: Actor, **args):
    """Invoke a FunctionTool exactly as the SDK would, minus the model. Returns (result, PurserContext)."""
    from agents.tool_context import ToolContext

    mc = PurserContext(actor)
    raw = json.dumps(args)
    tctx = ToolContext(context=mc, tool_name=tool.name, tool_call_id="call_1", tool_arguments=raw)
    out = await tool.on_invoke_tool(tctx, raw)
    return (json.loads(out) if isinstance(out, str) and out[:1] in "{[" else out), mc


async def code_of(actor, kind, args) -> str:
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.create(s, actor, kind, args)
    return e.value.code


async def with_conv(seeded, who="priya") -> Actor:
    return await make_actor(seeded, who)


def _pdf(pages=1, garbage=False) -> bytes:
    if garbage:
        return b"%PDF-1.4\nthis is not a real pdf body"
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(200, 200)
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


# ------------------------------------------------------------------ upload validation + replay (service level)


async def test_accepted_upload_records_document_audit_and_storage(seeded):
    from app.services import storage

    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        r = await intake.accept_upload(s, priya, "receipt.png", PNG)
    assert r.outcome == "accepted" and r.document_id
    async with db.session_scope() as s:
        d = await s.get(Document, r.document_id)
        assert (d.workspace_id, d.uploader_id, d.media_type, d.pages, d.size_bytes, d.status) == (priya.workspace_id, priya.user_id, "image/png", 1, len(PNG), "uploaded")
        assert len(d.sha256) == 64 and d.storage_key.startswith(f"ws{priya.workspace_id}/documents/{d.id}/")
        key = d.storage_key
    assert await storage.get(key) == PNG
    assert await count(AuditEvent, AuditEvent.action == "document.uploaded", AuditEvent.record_id == r.document_id) == 1


async def test_media_type_is_sniffed_from_bytes_not_filename(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        ok = await intake.accept_upload(s, priya, "renamed.txt", PNG)
        bad = await intake.accept_upload(s, priya, "invoice.pdf", b"MZ\x90\x00 definitely an exe, not a pdf")
    assert ok.outcome == "accepted" and bad.outcome == "unsupported" and bad.document_id is None


async def test_too_large_and_unreadable_pdf_create_no_document(seeded):
    priya = await make_actor(seeded)
    st = get_settings()
    limit = max(st.upload_max_bytes, st.contract_max_bytes)
    before = await count(Document)
    async with db.session_scope() as s:
        big = await intake.accept_upload(s, priya, "big.pdf", b"%PDF-" + b"0" * limit)
        broken = await intake.accept_upload(s, priya, "broken.pdf", _pdf(garbage=True))
        five = await intake.accept_upload(s, priya, "five.pdf", _pdf(pages=5))
        six = await intake.accept_upload(s, priya, "six.pdf", _pdf(pages=6))
    assert (big.outcome, broken.outcome, five.outcome, six.outcome) == ("too_large", "unreadable", "accepted", "accepted")
    assert await count(Document) == before + 2


async def test_exact_replay_reports_closed_outcome_of_the_first_upload(seeded):
    ids, priya = seeded, await make_actor(seeded)
    async with db.session_scope() as s:
        first = await intake.accept_upload(s, priya, "r.png", PNG)
    async with db.session_scope() as s:
        again = await intake.accept_upload(s, priya, "r2.png", PNG)
    assert again.outcome == "exact_replay" and again.document_id == first.document_id and again.existing["outcome"] is None
    # once it became a claim the replay names the claim, so the user is not asked to start over
    async with db.session_scope() as s:
        s.add(Extraction(workspace_id=priya.workspace_id, document_id=first.document_id, doc_type="receipt", fields=F(), arithmetic="unverifiable"))
        (await s.get(Document, first.document_id)).status = "inspected"
    _, out = await propose_and_confirm(priya, "submit_claim", {"document_id": first.document_id, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"})
    async with db.session_scope() as s:
        again = await intake.accept_upload(s, priya, "r3.png", PNG)
    assert again.existing["outcome"] == "claim" and again.existing["record_ref"] == out.receipt.effects[0]["ref"]
    assert again.existing["record_state"] == "submitted" and again.existing["amount"] == "₹4,800" or "4,800" in again.existing["amount"]
    assert await count(Document, Document.sha256 == (await _sha(first.document_id))) == 1


async def _sha(doc_id):
    async with db.session_scope() as s:
        return (await s.get(Document, doc_id)).sha256


async def test_same_bytes_in_another_workspace_is_not_a_replay(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
        await intake.accept_upload(s, priya, "r.png", PNG)
    other_priya = await make_actor(other)
    async with db.session_scope() as s:
        r = await intake.accept_upload(s, other_priya, "r.png", PNG)
    assert r.outcome == "accepted"


# ------------------------------------------------------------------ arithmetic


@pytest.mark.parametrize("fields,expected,total", [
    ({"total_paise": 10_000, "subtotal_paise": 9_900}, "ok", 9_900),            # ₹1 tolerance, exactly 100 paise off
    ({"total_paise": 10_000, "subtotal_paise": 9_899}, "mismatch", 9_899),      # 101 paise off
    ({"total_paise": 10_000, "subtotal_paise": 9_000, "discount_paise": 500, "other_charges_paise": 1_500}, "ok", 10_000),
    ({"total_paise": 10_000, "subtotal_paise": 9_000, "discount_paise": 500}, "mismatch", 8_500),
    ({"total_paise": 10_000, "line_items": [{"amount_paise": 4_000}, {"amount_paise": None}, {"amount_paise": 6_000}]}, "ok", 10_000),
    ({"total_paise": 10_000, "line_items": [{"amount_paise": 4_000}], "taxes": [{"amount_paise": 720}]}, "mismatch", 4_720),
    ({"total_paise": 10_000, "line_items": [{"amount_paise": None}]}, "unverifiable", None),
    ({"total_paise": 10_000, "line_items": []}, "unverifiable", None),
    ({"subtotal_paise": 9_000}, "unverifiable", 9_000),                          # no total to compare
    ({"total_paise": 0, "subtotal_paise": 100}, "unverifiable", 100),
    ({}, "unverifiable", None),
])
def test_arithmetic_and_breakdown_sum(fields, expected, total):
    assert intake.check_arithmetic(fields) == expected
    assert intake.breakdown_sum(fields) == total


# ------------------------------------------------------------------ probable duplicates


async def test_probable_duplicate_matches_existing_claim_and_bill(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        c = await intake.probable_duplicates(s, priya, 999, F("Meru Cabs", 1350, "2026-11-18"))  # Neha's seeded claim
        b = await intake.probable_duplicates(s, priya, 999, F("Shree Ganesh Printers", 18_500, "2026-11-10"))  # seeded bill B1, 2 days apart
    assert [(d["type"], d["state"]) for d in c] == [("claim", "submitted")] and c[0]["amount"] == "₹1,350"
    assert [d["type"] for d in b] == ["bill"] and b[0]["vendor"] == "Shree Ganesh Printers" and b[0]["state"] == "approved"
    assert b[0]["settlement_state"] == "unpaid"


@pytest.mark.parametrize("vendor,rupees,day,expect", [
    ("Shree Ganesh Printers", 18_500, "2026-11-11", True),    # exactly +3 days
    ("Shree Ganesh Printers", 18_500, "2026-11-05", True),    # exactly -3 days
    ("Shree Ganesh Printers", 18_500, "2026-11-12", False),   # +4 days
    ("Shree Ganesh Printers", 18_501, "2026-11-08", False),   # amount differs by ₹1
    ("Kaveri Caterers", 18_500, "2026-11-08", False),         # other vendor, same amount and date
    ("Ganesh Printers", 18_500, "2026-11-08", True),          # fuzzy: contained name
])
async def test_probable_duplicate_window_and_party_rules(seeded, vendor, rupees, day, expect):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        out = await intake.probable_duplicates(s, priya, 999, F(vendor, rupees, day))
    assert bool(out) is expect


async def test_probable_duplicate_excludes_own_document_and_needs_all_fields(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya)
    await propose_and_confirm(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"})
    async with db.session_scope() as s:
        assert await intake.probable_duplicates(s, priya, doc, F()) == []            # the claim's own source document
        same_other_doc = await intake.probable_duplicates(s, priya, doc + 1, F())    # a different upload of the same receipt
        assert [d["type"] for d in same_other_doc] == ["claim"]
        for missing in ("vendor", "date", "total_paise"):
            f = F()
            f.pop(missing)
            assert await intake.probable_duplicates(s, priya, doc + 1, f) == []


async def test_probable_duplicate_is_workspace_scoped(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    other_priya = await make_actor(other)
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        mine = await intake.probable_duplicates(s, priya, 999, F("Meru Cabs", 1350, "2026-11-18"))
        theirs = await intake.probable_duplicates(s, other_priya, 999, F("Meru Cabs", 1350, "2026-11-18"))
    assert len(mine) == 1 and len(theirs) == 1 and mine[0]["ref"] != theirs[0]["ref"]


# ------------------------------------------------------------------ payer routing data


async def test_company_payment_match_found_and_absent(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        hit = await intake.company_payment_matches(s, priya, F("Sunrise Residency", 3_200, "2026-11-12"))
        far = await intake.company_payment_matches(s, priya, F("Sunrise Residency Pune", 3_200, "2026-11-16"))   # 6 days after card payment
        edge = await intake.company_payment_matches(s, priya, F("Sunrise Residency Pune", 3_200, "2026-11-15"))  # 5 days
        wrong_amt = await intake.company_payment_matches(s, priya, F("Sunrise Residency Pune", 3_201, "2026-11-10"))
        wrong_payee = await intake.company_payment_matches(s, priya, F("Kaveri Caterers", 3_200, "2026-11-10"))
        nothing = await intake.company_payment_matches(s, priya, F("Sunrise Residency Pune", 4_800, "2026-11-19"))
        no_vendor = await intake.company_payment_matches(s, priya, {"total_paise": 3_200 * R, "date": "2026-11-10"})
    assert len(hit) == 1 and hit[0]["reference"] == "CARD-7781" and hit[0]["amount"] == "₹3,200" and hit[0]["paid_on"] == "2026-11-10"
    assert len(edge) == 1
    assert far == wrong_amt == wrong_payee == nothing == no_vendor == []


async def test_company_payment_match_is_workspace_scoped(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    priya, other_priya = await make_actor(seeded), await make_actor(other)
    async with db.session_scope() as s:
        a = await intake.company_payment_matches(s, priya, F("IndiGo Airlines", 6_850, "2026-11-12"))
        b = await intake.company_payment_matches(s, other_priya, F("IndiGo Airlines", 6_850, "2026-11-12"))
    assert len(a) == 1 == len(b) and a[0]["payment_id"] != b[0]["payment_id"]


async def test_reservation_candidates_trip_window_and_employee_filter(seeded):
    ids, priya = seeded, await make_actor(seeded)
    async with db.session_scope() as s:
        inside = await intake.reservation_candidates(s, priya, F(day="2026-11-19"))
        edge = await intake.reservation_candidates(s, priya, F(day="2026-11-20"))      # trip ends 19th, +1 day grace
        outside = await intake.reservation_candidates(s, priya, F(day="2026-11-25"))
        nodate = await intake.reservation_candidates(s, priya, {})
        arjun_only = await intake.reservation_candidates(s, priya, F(day="2026-11-19"), ids["arjun_party_id"])
        priya_only = await intake.reservation_candidates(s, priya, F(day="2026-11-19"), ids["priya_party_id"])
    assert len(inside) == 1 and inside[0]["ref"] == "RS1" and inside[0]["date_within_trip"] and inside[0]["amount_paise"] == 5_000 * R
    assert inside[0]["employee"] == "Arjun Mehta" and "Pune" in inside[0]["trip"]
    assert edge[0]["date_within_trip"] is True
    assert outside[0]["date_within_trip"] is False and nodate[0]["date_within_trip"] is False  # still offered, never auto-matched
    assert len(arjun_only) == 1 and priya_only == []


async def test_released_reservation_is_no_longer_a_candidate(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya)
    _, out = await propose_and_confirm(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel",
                                                              "reservation_id": ids["reservation_id"], "reservation_treatment": "final"})
    await propose_and_confirm(priya, "approve", {"ref": out.receipt.effects[0]["ref"]})
    async with db.session_scope() as s:
        assert await intake.reservation_candidates(s, priya, F()) == []


# ------------------------------------------------------------------ correction + close


async def test_wrong_total_blocks_submit_until_amount_corrected(seeded):
    ids, priya = seeded, await make_actor(seeded)
    f = F(rupees=5_000, subtotal_paise=428_571, taxes=[{"label": "GST", "amount_paise": 51_429}])  # parts sum to ₹4,800
    doc = await add_doc(priya, f, arithmetic="mismatch")
    args = {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"}
    assert await code_of(priya, "submit_claim", args) == VALIDATION
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        await intake.correct_field(s, priya, d, await records.extraction(s, priya, doc), "total_paise", 4_800 * R)
        ex = await records.extraction(s, priya, doc)
        assert ex.corrections[0]["previous"] == 5_000 * R and records.effective_fields(ex)["total_paise"] == 4_800 * R
        assert ex.fields["total_paise"] == 5_000 * R  # original extraction is preserved
    _, out = await propose_and_confirm(priya, "submit_claim", args)
    assert out.receipt.effects[0]["amount_paise"] == 4_800 * R  # corrected amount, not the printed one
    assert await count(AuditEvent, AuditEvent.action == "document.corrected", AuditEvent.record_id == doc) == 1


async def test_correcting_unrelated_field_does_not_clear_total_mismatch(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_doc(priya, F(rupees=5_000, subtotal_paise=428_571, taxes=[{"label": "GST", "amount_paise": 51_429}]), arithmetic="mismatch")
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        await intake.correct_field(s, priya, d, await records.extraction(s, priya, doc), "vendor", "Sunrise Residency")
    assert await code_of(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"}) == VALIDATION


async def test_proposal_goes_stale_when_document_is_corrected_after_preview(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya, total_rupees=4_800)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"})
        await proposals.mark_presented(s, p.id)
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        await intake.correct_field(s, priya, d, await records.extraction(s, priya, doc), "total_paise", 4_200 * R)
    async with db.session_scope() as s:
        out = await proposals.confirm(s, priya, p.id, via="button")
    assert out.status == "stale" and out.receipt is None and "4,200" in out.new_proposal.preview["speak"]
    assert await count(Claim) == 1  # only Neha's seeded claim


@pytest.mark.parametrize("field,value", [("amount", 5), ("total_paise", 0), ("total_paise", -5), ("total_paise", "abc"), ("date", "2026-13-45"),
                                         ("due_date", "next friday"), ("line_items", [])])
async def test_correct_field_rejects_invalid_input(seeded, field, value):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya)
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        ex = await records.extraction(s, priya, doc)
        with pytest.raises((DomainError, ValueError)):
            await intake.correct_field(s, priya, d, ex, field, value)
        assert not ex.corrections


async def test_close_validates_outcome_and_is_single_shot(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya, doc_type="contract")
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        with pytest.raises(DomainError) as e:
            await intake.close(s, priya, d, "made_up_outcome", "x")
        assert e.value.code == VALIDATION
        await intake.close(s, priya, d, "contract_out_of_scope", "MSA " + "x" * 800)
        assert d.status == "closed" and len(d.outcome_reason) == 500
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        with pytest.raises(DomainError) as e:
            await intake.close(s, priya, d, "unsupported", "again")
        assert e.value.code == INVALID_STATE and d.outcome == "contract_out_of_scope"
    assert await code_of(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"}) == INVALID_STATE


async def test_claimed_document_cannot_be_closed_afterwards(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya)
    await propose_and_confirm(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"})
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        with pytest.raises(DomainError) as e:
            await intake.close(s, priya, d, "duplicate", "oops")
    assert e.value.code == INVALID_STATE


# ------------------------------------------------------------------ SubmitBill new vendor path


async def test_new_vendor_bill_creates_vendor_only_on_confirm(seeded):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, vendor="Lakshmi Tent House", total_rupees=7_500, sha="1" * 64, doc_type="invoice")
    parties_before = await count(Party)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "submit_bill", {"document_id": doc, "category": "Events", "new_vendor_name": "  Lakshmi Tent House  "})
        await proposals.mark_presented(s, p.id)
    assert "New vendor 'Lakshmi Tent House' will be added." in p.preview["lines"][0]
    assert await count(Party) == parties_before  # planning writes nothing
    async with db.session_scope() as s:
        await proposals.cancel(s, priya, p.id)
    assert await count(Party) == parties_before and await count(Bill, Bill.document_id == doc) == 0

    _, out = await propose_and_confirm(priya, "submit_bill", {"document_id": doc, "category": "Events", "new_vendor_name": "Lakshmi Tent House"})
    async with db.session_scope() as s:
        v = (await s.execute(select(Party).where(Party.name == "Lakshmi Tent House"))).scalar_one()
        b = (await s.execute(select(Bill).where(Bill.ref == out.receipt.effects[0]["ref"]))).scalar_one()
        assert (v.kind, v.workspace_id, v.normalized_name) == ("vendor", priya.workspace_id, "lakshmi tent house")
        assert b.vendor_party_id == v.id and b.state == "submitted" and b.amount_paise == 7_500 * R
    assert await count(Party) == parties_before + 1


async def test_bill_needs_a_vendor_and_prefers_existing_id(seeded):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, sha="2" * 64)
    assert await code_of(priya, "submit_bill", {"document_id": doc, "category": "Events"}) == VALIDATION
    assert await code_of(priya, "submit_bill", {"document_id": doc, "category": "Events", "new_vendor_name": "   "}) == VALIDATION
    kaveri = (await _party_id("Kaveri Caterers"))
    before = await count(Party)
    _, out = await propose_and_confirm(priya, "submit_bill", {"document_id": doc, "category": "Events", "vendor_party_id": kaveri, "new_vendor_name": "Ignored Name"})
    assert await count(Party) == before and await count(Party, Party.name == "Ignored Name") == 0
    assert out.status == "executed"


async def _party_id(name):
    async with db.session_scope() as s:
        return (await s.execute(select(Party.id).where(Party.name == name))).scalar_one()


async def test_new_vendor_name_matching_existing_vendor_does_not_create_duplicate(seeded):
    """If the model passes new_vendor_name for a vendor that already exists, payables must not fork the vendor."""
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, sha="3" * 64)
    before = await count(Party, Party.name == "Kaveri Caterers")
    await propose_and_confirm(priya, "submit_bill", {"document_id": doc, "category": "Events", "new_vendor_name": "Kaveri Caterers"})
    assert await count(Party, Party.name == "Kaveri Caterers") == before


# ------------------------------------------------------------------ agent tools (SDK invocation, no model)


async def test_safe_tool_turns_domain_error_into_structured_result_and_logs_it(seeded):
    priya = await make_actor(seeded)
    out, ctx = await call(proposal_tools.propose_settlement, priya, ref="B1", reference="")
    assert out["ok"] is False and out["code"] == VALIDATION and out["message"]
    assert ctx.tool_log[-1]["tool"] == "propose_settlement" and ctx.tool_log[-1]["outcome"] == VALIDATION
    assert ctx.ui == []  # no card for a failed proposal
    out, _ = await call(proposal_tools.propose_approval, priya, ref="C99999")
    assert (out["ok"], out["code"]) == (False, NOT_FOUND)


async def test_tools_enforce_role_and_ownership_from_actor_not_arguments(seeded):
    ids, arjun = seeded, await make_actor(seeded, "arjun")
    out, _ = await call(proposal_tools.propose_approval, arjun, ref=ids["neha_claim_ref"])
    assert out["ok"] is False and out["code"] in (FORBIDDEN, NOT_FOUND)
    out, _ = await call(proposal_tools.propose_settlement, arjun, ref="B1", reference="X")
    assert out["ok"] is False and out["code"] == FORBIDDEN
    out, _ = await call(finance_tools.get_record, arjun, ref=ids["neha_claim_ref"])
    assert out["ok"] is False and out["code"] == NOT_FOUND
    assert await count(Proposal) == 0


async def test_propose_tools_only_propose_never_write(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya)
    before = await finance_counts()
    out, ctx = await call(proposal_tools.propose_submit_claim, priya, document_id=doc, beneficiary_party_id=ids["arjun_party_id"], category="Travel",
                          reservation_id=ids["reservation_id"], reservation_treatment="final")
    assert out["ok"] and out["status"] == "open" and "Do NOT confirm" in out["instruction"]
    assert ctx.ui == [{"card": "proposal", "proposal_id": out["proposal_id"]}]
    assert await finance_counts() == before and await count(Receipt) == 0


async def test_reservation_treatment_is_dropped_without_reservation_id(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya)
    out, _ = await call(proposal_tools.propose_submit_claim, priya, document_id=doc, beneficiary_party_id=ids["arjun_party_id"], category="Travel",
                        reservation_treatment="final")
    async with db.session_scope() as s:
        assert (await s.get(Proposal, out["proposal_id"])).args["reservation_treatment"] == "none"


async def test_confirm_tool_requires_reply_after_preview_then_executes(seeded):
    priya = await make_actor(seeded)
    out, _ = await call(proposal_tools.confirm_pending_proposal, priya)
    assert (out["ok"], out["code"]) == (False, NOT_FOUND)

    out, _ = await call(proposal_tools.propose_settlement, priya, ref="B1", reference="UTR-77")
    pid = out["proposal_id"]
    out, _ = await call(proposal_tools.confirm_pending_proposal, priya)   # preview never marked as presented
    assert out["ok"] is False and out["code"] == "CONFIRMATION_REQUIRED" and await _status(pid) == "open"
    async with db.session_scope() as s:
        await proposals.mark_presented(s, pid)
    out, _ = await call(proposal_tools.confirm_pending_proposal, priya)   # presented, but the user has said nothing yet
    assert out["code"] == "CONFIRMATION_REQUIRED"
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "haan, but make it 5000", source="live_sideband")
    out, _ = await call(proposal_tools.confirm_pending_proposal, priya)
    assert out["code"] == "CONFIRMATION_REQUIRED" and out["classification"] == "ambiguous" and await count(Receipt) == 0
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "haan ji", source="live_sideband")
    out, ctx = await call(proposal_tools.confirm_pending_proposal, priya)
    assert out["ok"] and out["status"] == "executed" and out["receipt"].startswith("R")
    assert ctx.ui == [{"card": "receipt", "receipt_id": (await _receipt_id(pid))}]
    async with db.session_scope() as s:
        r = (await s.execute(select(Receipt))).scalar_one()
        assert r.confirmed_via == "voice:live_sideband" and r.confirmation_evidence["transcript"] == "haan ji"


async def _status(pid):
    async with db.session_scope() as s:
        return (await s.get(Proposal, pid)).status


async def _receipt_id(pid):
    async with db.session_scope() as s:
        return (await s.get(Proposal, pid)).receipt_id


async def test_confirm_tool_reports_stale_with_new_preview_and_executes_nothing(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya, total_rupees=4_800)
    out, _ = await call(proposal_tools.propose_submit_claim, priya, document_id=doc, beneficiary_party_id=ids["arjun_party_id"], category="Travel")
    async with db.session_scope() as s:
        await proposals.mark_presented(s, out["proposal_id"])
        d = await records.document(s, priya, doc, for_update=True)
        await intake.correct_field(s, priya, d, await records.extraction(s, priya, doc), "total_paise", 4_100 * R)
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "yes", source="live_sideband")
    claims_before = await count(Claim)
    out2, ctx = await call(proposal_tools.confirm_pending_proposal, priya)
    assert out2["ok"] is False and out2["code"] == "STALE_PROPOSAL" and "4,100" in out2["new_proposal"]["say"]
    assert out2["new_proposal"]["proposal_id"] != out["proposal_id"] and await count(Claim) == claims_before
    assert ctx.ui[-1]["card"] == "proposal"


async def test_cancel_and_get_pending_tools(seeded):
    priya = await make_actor(seeded)
    out, _ = await call(proposal_tools.cancel_pending_proposal, priya)
    assert out == {"ok": True, "cancelled": None}
    out, _ = await call(proposal_tools.get_pending_proposal, priya)
    assert out == {"ok": True, "pending": None}
    p, _ = await call(proposal_tools.propose_settlement, priya, ref="B1", reference="UTR-1")
    pend, _ = await call(proposal_tools.get_pending_proposal, priya)
    assert pend["pending"]["proposal_id"] == p["proposal_id"]
    out, _ = await call(proposal_tools.cancel_pending_proposal, priya)
    assert out["cancelled"] == p["proposal_id"] and await _status(p["proposal_id"]) == "cancelled"


async def test_propose_bill_tool_with_new_vendor(seeded):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, sha="4" * 64)
    out, _ = await call(proposal_tools.propose_submit_bill, priya, document_id=doc, category="Events", new_vendor_name="Lakshmi Tent House")
    assert out["ok"] and any("New vendor" in line for line in out["preview"])
    out, _ = await call(proposal_tools.propose_submit_bill, priya, document_id=doc, category="Events")
    assert out["ok"] is False and out["code"] == VALIDATION


async def test_inspect_document_surfaces_company_payment_and_reservation_routing_data(seeded):
    priya = await make_actor(seeded)
    paid = await add_doc(priya, F("Sunrise Residency", 3_200, "2026-11-12"))
    out, ctx = await call(intake_tools.inspect_document, priya, document_id=paid)
    assert out["ok"] and out["vendor"] == "Sunrise Residency" and out["total"] == "₹3,200"
    assert [m["reference"] for m in out["company_payment_matches"]] == ["CARD-7781"] and out["probable_duplicates"] == []
    assert out["open_reservations"] == [] or out["open_reservations"][0]["date_within_trip"] is False  # 12 Nov is before the 16-19 Nov trip
    assert ctx.ui[0] == {"card": "source", "document_id": paid, "highlight": ["vendor", "date", "total_paise"]}

    hotel = await add_doc(priya, F("Sunrise Residency Pune", 4_800, "2026-11-19"))
    out, _ = await call(intake_tools.inspect_document, priya, document_id=hotel)
    assert out["company_payment_matches"] == []                                  # nothing paid by the company: routing is employee-paid
    assert [(r["ref"], r["date_within_trip"]) for r in out["open_reservations"]] == [("RS1", True)]
    assert "Resolve the economic event" in out["next_step"]
    async with db.session_scope() as s:
        assert (await s.get(Conversation, priya.conversation_id)).current_document_id == hotel


async def test_inspect_document_flags_probable_duplicate_and_mismatch(seeded):
    ids, priya = seeded, await make_actor(seeded)
    first = await add_inspected_document(priya, total_rupees=4_800, sha="5" * 64)
    _, out = await propose_and_confirm(priya, "submit_claim", {"document_id": first, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"})
    ref = out.receipt.effects[0]["ref"]
    second = await add_doc(priya, F("Sunrise Residency Pune", 4_800, "2026-11-20"))
    res, _ = await call(intake_tools.inspect_document, priya, document_id=second)
    assert [(d["ref"], d["type"]) for d in res["probable_duplicates"]] == [(ref, "claim")]
    assert res["next_step"].startswith("Probable duplicate found")
    bad = await add_doc(priya, F(rupees=5_000, subtotal_paise=428_571, taxes=[{"label": "GST", "amount_paise": 51_429}]), arithmetic="mismatch")
    res, _ = await call(intake_tools.inspect_document, priya, document_id=bad)
    assert "DOES NOT ADD UP" in res["arithmetic"] and res["breakdown_sum"] == "₹4,800" and res["taxes"] == ["GST: ₹514.29"]


async def test_inspect_document_contract_next_step_and_closed_short_circuit(seeded):
    priya = await make_actor(seeded)
    doc = await add_doc(priya, {"vendor": "Acme Traders", "date": "2026-11-01", "total_paise": 5_000_000}, doc_type="contract")
    out, _ = await call(intake_tools.inspect_document, priya, document_id=doc)
    assert "call review_contract(document_id)" in out["next_step"] and out["open_reservations"] == []
    before = await finance_counts()
    res, _ = await call(intake_tools.close_intake, priya, document_id=doc, outcome="contract_out_of_scope", reason="MSA")
    assert res == {"ok": True, "document_id": doc, "outcome": "contract_out_of_scope", "finance_records_created": 0}
    assert await finance_counts() == before
    out, _ = await call(intake_tools.inspect_document, priya, document_id=doc)
    assert out["closed"] is True and out["outcome"] == "contract_out_of_scope" and out["reason"] == "MSA"
    again, _ = await call(intake_tools.close_intake, priya, document_id=doc, outcome="duplicate", reason="x")
    assert again["ok"] is False and again["code"] == INVALID_STATE


async def test_inspect_and_close_respect_document_ownership(seeded):
    priya, arjun = await make_actor(seeded), await make_actor(seeded, "arjun")
    doc = await add_doc(priya, F())
    for tool, args in ((intake_tools.inspect_document, {}), (intake_tools.show_source, {}),
                       (intake_tools.close_intake, {"outcome": "unsupported", "reason": "x"})):
        out, _ = await call(tool, arjun, document_id=doc, **args)
        assert out["ok"] is False and out["code"] == NOT_FOUND, tool.name
    async with db.session_scope() as s:
        assert (await records.document(s, priya, doc)).outcome is None


async def test_correct_extracted_field_tool(seeded):
    priya = await make_actor(seeded)
    doc = await add_doc(priya, F(rupees=5_000))
    out, ctx = await call(intake_tools.correct_extracted_field, priya, document_id=doc, field="total", value="₹4,800.50")
    assert out["ok"] and out["updated"]["total"] == "₹4,800.50" and ctx.ui[-1]["highlight"] == ["total_paise"]
    async with db.session_scope() as s:
        ex = await records.extraction(s, priya, doc)
        assert ex.corrections[-1]["value"] == 480_050 and ex.corrections[-1]["previous"] == 5_000 * R
    bad, _ = await call(intake_tools.correct_extracted_field, priya, document_id=doc, field="total", value="about five thousand")
    assert (bad["ok"], bad["code"]) == (False, VALIDATION)
    neg, _ = await call(intake_tools.correct_extracted_field, priya, document_id=doc, field="total", value="-10")
    assert neg["ok"] is False and neg["code"] == VALIDATION
    fresh = await _uninspected_doc(priya)
    out, _ = await call(intake_tools.correct_extracted_field, priya, document_id=fresh, field="vendor", value="X")
    assert (out["ok"], out["code"]) == (False, INVALID_STATE)


async def _uninspected_doc(actor):
    async with db.session_scope() as s:
        d = Document(workspace_id=actor.workspace_id, uploader_id=actor.user_id, storage_key="k", filename="f.png", sha256="e" * 64,
                     media_type="image/png", pages=1, size_bytes=1)
        s.add(d)
        await s.flush()
        return d.id


async def test_correct_extracted_field_bad_date_is_structured_validation_error(seeded):
    priya = await make_actor(seeded)
    doc = await add_doc(priya, F())
    out, _ = await call(intake_tools.correct_extracted_field, priya, document_id=doc, field="date", value="tomorrow")
    assert isinstance(out, dict) and out["ok"] is False and out["code"] == VALIDATION


async def test_find_reservations_tool_scopes_to_employee_and_uses_effective_date(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_doc(priya, F(day="2026-12-30"))
    out, _ = await call(intake_tools.find_reservations, priya, document_id=doc, employee_party_id=ids["arjun_party_id"])
    assert out["ok"] and [(r["ref"], r["date_within_trip"]) for r in out["reservations"]] == [("RS1", False)]
    async with db.session_scope() as s:
        d = await records.document(s, priya, doc, for_update=True)
        await intake.correct_field(s, priya, d, await records.extraction(s, priya, doc), "date", "2026-11-18")
    out, _ = await call(intake_tools.find_reservations, priya, document_id=doc, employee_party_id=ids["arjun_party_id"])
    assert out["reservations"][0]["date_within_trip"] is True
    none, _ = await call(intake_tools.find_reservations, priya, document_id=doc, employee_party_id=ids["priya_party_id"])
    assert none["reservations"] == []


# ------------------------------------------------------------------ HTTP: auth, CSRF, origin, conversation ownership


async def test_login_sets_hardened_cookie_and_normalizes_email(seeded):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as c:
        r = await c.post("/api/auth/login", json={"email": "  PRIYA@purser.demo ", "password": "purser-demo"})
        assert r.status_code == 200 and r.json()["user"]["role"] == "admin"
        cookie = r.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie and "path=/" in cookie
        assert "no-store" in r.headers["cache-control"]
        bad = await c.post("/api/auth/login", json={"email": "nobody@purser.demo", "password": "purser-demo"})
        assert bad.status_code == 401


async def test_wrong_origin_and_wrong_csrf_rejected_on_writes(seeded):
    c = await client_for()
    r = await c.post("/api/conversations", headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    r = await c.post("/api/conversations", headers={"x-csrf-token": "not-the-token"})
    assert r.status_code == 403
    assert (await c.post("/api/conversations")).status_code == 201
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as anon:
        r = await anon.post("/api/auth/login", headers={"origin": "https://evil.example"}, json={"email": "priya@purser.demo", "password": "purser-demo"})
        assert r.status_code == 403
    await c.aclose()


async def test_tampered_cookie_and_logout_end_the_session(seeded):
    c = await client_for()
    assert (await c.get("/api/me")).status_code == 200
    good = c.cookies.get("purser_session")
    c.cookies.set("purser_session", good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB"))
    assert (await c.get("/api/me")).status_code == 401
    c.cookies.set("purser_session", good)
    assert (await c.get("/api/me")).status_code == 200
    out = await c.post("/api/auth/logout")
    assert out.status_code == 200 and "max-age=0" in out.headers["set-cookie"].lower()  # browser drops the cookie
    c.cookies.clear()
    assert (await c.get("/api/me")).status_code == 401
    await c.aclose()


async def test_other_users_or_workspaces_conversation_id_is_404(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    priya, arjun, other_priya = await client_for(), await client_for("arjun@purser.demo"), await client_for("priya@other.demo")
    priya_conv, other_conv = priya.headers["x-conversation-id"], other_priya.headers["x-conversation-id"]
    assert (await arjun.get("/api/me", headers={"x-conversation-id": priya_conv})).status_code == 404
    assert (await priya.get("/api/me", headers={"x-conversation-id": other_conv})).status_code == 404
    assert (await priya.get("/api/me", headers={"x-conversation-id": "does-not-exist"})).status_code == 404
    own = arjun.headers.pop("x-conversation-id")
    assert (await arjun.get(f"/api/me?conversation_id={priya_conv}")).status_code == 404   # query-param form used by the event stream
    assert (await arjun.get(f"/api/me?conversation_id={own}")).status_code == 200
    arjun.headers["x-conversation-id"] = own
    assert (await arjun.post("/api/documents", headers={"x-conversation-id": priya_conv}, files={"file": ("r.png", PNG, "image/png")})).status_code == 404
    assert await count(Document) == 0  # the rejected upload stored nothing
    assert (await priya.get("/api/me", headers={"x-conversation-id": priya_conv})).status_code == 200
    assert other["workspace_id"] != seeded["workspace_id"]
    for c in (priya, arjun, other_priya):
        await c.aclose()


async def test_agent_text_requires_conversation_header_and_text(seeded):
    c = await client_for()
    del c.headers["x-conversation-id"]
    assert (await c.post("/api/agent/text", json={"text": "hello"})).status_code == 400
    c.headers["x-conversation-id"] = (await c.post("/api/conversations")).json()["conversation_id"]
    assert (await c.post("/api/agent/text", json={"text": ""})).status_code == 422
    assert (await c.post("/api/agent/text", json={"text": "x" * 2001})).status_code == 422
    await c.aclose()


async def test_conversation_channel_is_validated_and_api_is_not_cached(seeded):
    c = await client_for()
    assert (await c.post("/api/conversations?channel=carrier-pigeon")).status_code == 400
    r = await c.get("/api/me")
    assert "no-store" in r.headers["cache-control"]
    await c.aclose()


# ------------------------------------------------------------------ HTTP: upload, preview, visibility


async def test_upload_sets_current_document_and_pdf_pages_render(seeded):
    c = await client_for()
    two_pages = _pdf(pages=2)
    r = (await c.post("/api/documents", files={"file": ("two.pdf", two_pages, "application/pdf")})).json()
    doc = r["document_id"]
    async with db.session_scope() as s:
        assert (await s.get(Conversation, c.headers["x-conversation-id"])).current_document_id == doc
    for page, status in ((1, 200), (2, 200), (0, 404), (3, 404)):
        resp = await c.get(f"/api/documents/{doc}/pages/{page}")
        assert resp.status_code == status, page
        if status == 200:
            assert resp.headers["content-type"] == "image/png" and resp.content[:4] == b"\x89PNG"
    await c.aclose()


async def test_upload_requires_file_and_session(seeded):
    c = await client_for()
    assert (await c.post("/api/documents")).status_code == 422
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as anon:
        assert (await anon.post("/api/documents", files={"file": ("r.png", PNG, "image/png")})).status_code == 401
        assert (await anon.get("/api/documents/1/pages/1")).status_code == 401
    await c.aclose()


async def test_employee_upload_visibility(seeded):
    priya, arjun = await client_for(), await client_for("arjun@purser.demo")
    mine = (await arjun.post("/api/documents", files={"file": ("a.png", PNG, "image/png")})).json()["document_id"]
    assert (await arjun.get(f"/api/documents/{mine}/pages/1")).status_code == 200
    assert (await priya.get(f"/api/documents/{mine}/pages/1")).status_code == 200        # approver sees the workspace's uploads
    other = (await priya.post("/api/documents", files={"file": ("p.pdf", _pdf(), "application/pdf")})).json()["document_id"]
    assert (await arjun.get(f"/api/documents/{other}/pages/1")).status_code == 404
    assert (await arjun.get("/api/documents/999999/pages/1")).status_code == 404
    await priya.aclose()
    await arjun.aclose()


async def test_cross_workspace_document_page_is_404(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    other_priya = await make_actor(other)
    other_doc = await add_inspected_document(other_priya, sha="6" * 64)
    priya = await client_for()
    assert (await priya.get(f"/api/documents/{other_doc}/pages/1")).status_code == 404
    await priya.aclose()


async def test_exact_replay_does_not_leak_other_users_document_to_employee(seeded):
    priya, arjun = await client_for(), await client_for("arjun@purser.demo")
    first = (await priya.post("/api/documents", files={"file": ("r.png", PNG, "image/png")})).json()
    second = (await arjun.post("/api/documents", files={"file": ("r.png", PNG, "image/png")})).json()
    assert second["document_id"] != first["document_id"] or second["existing"] is None
    await priya.aclose()
    await arjun.aclose()


# ------------------------------------------------------------------ HTTP: proposals + receipts


async def _http_proposal(seeded, c, kind="settle", args=None):
    priya = await make_actor(seeded)
    priya = Actor(priya.user_id, priya.workspace_id, priya.role, priya.party_id, priya.display_name, c.headers["x-conversation-id"])
    b = await _approved_bill()
    async with db.session_scope() as s:
        return await proposals.create(s, priya, kind, args or {"ref": b.ref, "reference": "UTR-H"}), b


async def _approved_bill():
    async with db.session_scope() as s:
        return (await s.execute(select(Bill).where(Bill.state == "approved", Bill.settlement_state == "unpaid"))).scalars().first()


async def test_button_cancel_then_confirm_is_409_and_other_actor_cannot_cancel(seeded):
    c, arjun = await client_for(), await client_for("arjun@purser.demo")
    p, b = await _http_proposal(seeded, c)
    assert (await arjun.post(f"/api/proposals/{p.id}/cancel")).status_code == 404
    assert (await arjun.get(f"/api/proposals/{p.id}")).status_code == 404
    got = (await c.get(f"/api/proposals/{p.id}")).json()
    assert got["status"] == "open" and got["kind"] == "settle" and got["preview"]["lines"]
    no_csrf = dict(c.headers)
    del no_csrf["x-csrf-token"]
    assert (await c.post(f"/api/proposals/{p.id}/cancel", headers={"x-csrf-token": ""})).status_code == 403
    assert (await c.post(f"/api/proposals/{p.id}/cancel")).json() == {"status": "cancelled"}
    r = await c.post(f"/api/proposals/{p.id}/confirm")
    assert r.status_code == 409 and r.json()["code"] == "PROPOSAL_CLOSED"
    assert await count(Settlement_model(), Settlement_model().record_id == b.id) == 0
    await c.aclose()
    await arjun.aclose()


def Settlement_model():
    from app.models import Settlement
    return Settlement


async def test_button_confirm_records_channel_evidence_and_receipt_is_fetchable(seeded):
    c = await client_for()
    p, b = await _http_proposal(seeded, c)
    out = (await c.post(f"/api/proposals/{p.id}/confirm")).json()
    assert out["status"] == "executed" and out["receipt"]["effects"][0]["ref"] == b.ref
    rid = out["receipt"]["id"]
    r = (await c.get(f"/api/receipts/{rid}")).json()
    assert r["confirmed_via"] == "button" and r["preview"]["title"] == "Record settlement" and r["ref"] == f"R{rid}"
    async with db.session_scope() as s:
        assert (await s.get(Receipt, rid)).confirmation_evidence == {"channel": "button"}
    await c.aclose()


async def test_button_confirm_of_stale_proposal_returns_new_proposal_id(seeded):
    ids = seeded
    c = await client_for()
    priya = await make_actor(seeded)
    priya = Actor(priya.user_id, priya.workspace_id, priya.role, priya.party_id, priya.display_name, c.headers["x-conversation-id"])
    doc = await add_inspected_document(priya)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"})
        d = await records.document(s, priya, doc, for_update=True)
        await intake.correct_field(s, priya, d, await records.extraction(s, priya, doc), "total_paise", 100 * R)
    r = (await c.post(f"/api/proposals/{p.id}/confirm")).json()
    assert r["status"] == "stale" and r["receipt"] is None and r["new_proposal_id"] and r["new_proposal_id"] != p.id
    assert await count(Receipt) == 0
    await c.aclose()


async def test_cross_workspace_receipt_and_proposal_are_404(seeded):
    async with db.session_scope() as s:
        await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    c, other_c = await client_for(), await client_for("priya@other.demo")
    p, _ = await _http_proposal(seeded, c)
    rid = (await c.post(f"/api/proposals/{p.id}/confirm")).json()["receipt"]["id"]
    assert (await c.get(f"/api/receipts/{rid}")).status_code == 200
    assert (await other_c.get(f"/api/receipts/{rid}")).status_code == 404
    assert (await other_c.get(f"/api/proposals/{p.id}")).status_code == 404
    assert (await other_c.post(f"/api/proposals/{p.id}/confirm")).status_code == 404
    assert (await c.get("/api/receipts/987654")).status_code == 404
    await c.aclose()
    await other_c.aclose()


async def test_employee_cannot_read_approvers_receipt(seeded):
    c, arjun = await client_for(), await client_for("arjun@purser.demo")
    p, _ = await _http_proposal(seeded, c)
    rid = (await c.post(f"/api/proposals/{p.id}/confirm")).json()["receipt"]["id"]
    assert (await arjun.get(f"/api/receipts/{rid}")).status_code in (403, 404)
    await c.aclose()
    await arjun.aclose()


async def test_health_endpoint(seeded):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as c:
        r = await c.get("/health")
    assert r.status_code == 200 and r.json() == {"ok": True}
