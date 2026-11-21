"""H1-4 gates from docs/PLAN_v4.md §5: replay, stale proposal, self-approval, ₹45,200, conservation, roles."""

import pytest
from sqlalchemy import func, select

from app import db
from app.errors import ALREADY_SETTLED, CONFIRMATION_REQUIRED, FORBIDDEN, NOT_FOUND, SELF_APPROVAL, DomainError
from app.models import BudgetMovement, Claim, Proposal
from app.services import budget, confirmation, proposals
from app.services.affirmation import Affirmation, classify
from seed.seed_v1 import seed
from tests.conftest import add_inspected_document, make_actor

R = 100


async def travel(ids):
    async with db.session_scope() as s:
        return await budget.position(s, ids["workspace_id"], ids["travel_line_id"])


async def propose_and_confirm(actor, kind, args):
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, kind, args)
        await proposals.mark_presented(s, p.id)
    async with db.session_scope() as s:
        out = await proposals.confirm(s, actor, p.id, via="button")
    return p, out


async def submit_arjun_hotel_claim(ids, priya, total=4800):
    doc = await add_inspected_document(priya, total_rupees=total)
    _, out = await propose_and_confirm(priya, "submit_claim", {
        "document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel",
        "reservation_id": ids["reservation_id"], "reservation_treatment": "final"})
    assert out.status == "executed"
    return out.receipt.effects[0]["ref"]


async def test_budget_fixture_45200(seeded):
    ids, priya = seeded, await make_actor(seeded)
    assert (await travel(ids))["available_paise"] == 45_000 * R
    ref = await submit_arjun_hotel_claim(ids, priya)
    pos = await travel(ids)
    assert (pos["reserved_paise"], pos["committed_paise"], pos["available_paise"], pos["pending_claims_paise"]) == (5_000 * R, 0, 45_000 * R, 4_800 * R)

    _, out = await propose_and_confirm(priya, "approve", {"ref": ref})  # submitter may approve (v4 §2.5)
    pos = await travel(ids)
    assert (pos["reserved_paise"], pos["committed_paise"], pos["spent_paise"], pos["available_paise"]) == (0, 4_800 * R, 0, 45_200 * R)

    _, out = await propose_and_confirm(priya, "settle", {"ref": ref, "reference": "4471"})
    pos = await travel(ids)
    assert (pos["reserved_paise"], pos["committed_paise"], pos["spent_paise"], pos["available_paise"]) == (0, 0, 4_800 * R, 45_200 * R)


async def test_other_amount_narrates_actual_delta(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya, total=5_600)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "approve", {"ref": ref})
        assert p.preview["budget_effect"]["available_delta_paise"] == -600 * R  # not hardcoded to +200


async def test_replay_returns_same_receipt(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    p, first = await propose_and_confirm(priya, "approve", {"ref": ref})
    async with db.session_scope() as s:
        n_before = (await s.execute(select(func.count()).select_from(BudgetMovement))).scalar_one()
    async with db.session_scope() as s:
        again = await proposals.confirm(s, priya, p.id, via="button")
    async with db.session_scope() as s:
        n_after = (await s.execute(select(func.count()).select_from(BudgetMovement))).scalar_one()
    assert again.status == "replayed" and again.receipt.id == first.receipt.id and n_after == n_before


async def test_stale_proposal_returns_new_preview(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "approve", {"ref": ref})
        await proposals.mark_presented(s, p.id)
    async with db.session_scope() as s:  # concurrent change to the claim
        c = (await s.execute(select(Claim).where(Claim.ref == ref))).scalar_one()
        c.version += 1
    async with db.session_scope() as s:
        out = await proposals.confirm(s, priya, p.id, via="button")
    assert out.status == "stale" and out.new_proposal is not None and out.receipt is None
    assert (await travel(ids))["committed_paise"] == 0
    async with db.session_scope() as s:
        assert (await s.get(Proposal, p.id)).status == "stale"


async def test_beneficiary_cannot_self_approve(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya, vendor="Cafe Coffee Day", total_rupees=640)
    _, out = await propose_and_confirm(priya, "submit_claim", {
        "document_id": doc, "beneficiary_party_id": ids["priya_party_id"], "category": "Travel"})
    ref = out.receipt.effects[0]["ref"]
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.create(s, priya, "approve", {"ref": ref})
    assert e.value.code == SELF_APPROVAL


async def test_double_settlement_rejected(seeded):
    priya = await make_actor(seeded)
    from app.models import Bill
    async with db.session_scope() as s:
        b = (await s.execute(select(Bill).where(Bill.state == "approved", Bill.settlement_state == "unpaid"))).scalar_one()
    _, out = await propose_and_confirm(priya, "settle", {"ref": b.ref, "reference": "UTR-1"})
    assert out.status == "executed"
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.create(s, priya, "settle", {"ref": b.ref, "reference": "UTR-2"})
    assert e.value.code == ALREADY_SETTLED


async def test_ledger_conservation(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    await propose_and_confirm(priya, "approve", {"ref": ref})
    await propose_and_confirm(priya, "settle", {"ref": ref, "reference": "4471"})
    from app.models import BudgetLine
    async with db.session_scope() as s:
        for line in (await s.execute(select(BudgetLine))).scalars():
            p = await budget.position(s, line.workspace_id, line.id)
            assert min(p["reserved_paise"], p["committed_paise"], p["spent_paise"]) >= 0
            assert p["reserved_paise"] + p["committed_paise"] + p["spent_paise"] + p["available_paise"] == p["allocated_paise"]


async def test_spoken_confirmation_requires_clear_yes_after_preview(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "approve", {"ref": ref})
        await confirmation.record_turn(s, priya, "haan", source="text")  # said BEFORE preview presented
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await confirmation.spoken_confirmation(s, priya, await s.get(Proposal, p.id))
        assert e.value.code == CONFIRMATION_REQUIRED
        await proposals.mark_presented(s, p.id)
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "haan lekin amount galat hai", source="live_sideband")
    async with db.session_scope() as s:
        with pytest.raises(DomainError):
            await confirmation.spoken_confirmation(s, priya, await s.get(Proposal, p.id))
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "Haan ji, kar do.", source="live_sideband")
    async with db.session_scope() as s:
        ev = await confirmation.spoken_confirmation(s, priya, await s.get(Proposal, p.id))
        assert ev["classification"] == "affirm"


@pytest.mark.parametrize("text,expected", [
    ("yes", Affirmation.AFFIRM), ("Haan ji", Affirmation.AFFIRM), ("haan kar do na", Affirmation.AFFIRM),
    ("ठीक है", Affirmation.AFFIRM), ("हाँ, कर दो।", Affirmation.AFFIRM), ("Yes please, go ahead.", Affirmation.AFFIRM),
    ("no", Affirmation.NEGATIVE), ("nahi ruko", Affirmation.NEGATIVE), ("नहीं", Affirmation.NEGATIVE),
    ("haan lekin amount galat hai", Affirmation.AMBIGUOUS), ("yes but change the date", Affirmation.AMBIGUOUS),
    ("what is the amount", Affirmation.AMBIGUOUS), ("", Affirmation.AMBIGUOUS), ("haan 5000 karo", Affirmation.AMBIGUOUS),
])
def test_affirmation_classifier(text, expected):
    assert classify(text) is expected


async def test_employee_cannot_view_other_claim(seeded):
    arjun = await make_actor(seeded, "arjun")
    from app.services import records
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await records.claim_by_ref(s, arjun, seeded["neha_claim_ref"])
    assert e.value.code == NOT_FOUND


async def test_employee_cannot_approve_bill(seeded):
    arjun = await make_actor(seeded, "arjun")
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.create(s, arjun, "approve", {"ref": "B2"})
    assert e.value.code in (FORBIDDEN, NOT_FOUND)


async def test_cross_workspace_object_ids_not_found(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    other_priya = await make_actor(other)
    other_doc = await add_inspected_document(other_priya, sha="b" * 64)
    from app.services import records
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e1:
            await records.claim_by_ref(s, priya, other["neha_claim_ref"])  # exists only in the other workspace
    assert e1.value.code == NOT_FOUND
    with pytest.raises(DomainError) as e2:
        async with db.session_scope() as s:
            await proposals.create(s, priya, "submit_claim", {"document_id": other_doc, "beneficiary_party_id": seeded["arjun_party_id"], "category": "Travel"})
    assert e2.value.code == NOT_FOUND


async def test_failure_preserves_balances(seeded, monkeypatch):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "approve", {"ref": ref})
        await proposals.mark_presented(s, p.id)
    from app.services import audit

    async def boom(*a, **k):
        raise RuntimeError("injected failure mid-transaction")

    monkeypatch.setattr(audit, "record", boom)
    with pytest.raises(RuntimeError):
        async with db.session_scope() as s:
            await proposals.confirm(s, priya, p.id, via="button")
    monkeypatch.undo()
    pos = await travel(ids)
    assert (pos["reserved_paise"], pos["committed_paise"], pos["available_paise"]) == (5_000 * R, 0, 45_000 * R)
    async with db.session_scope() as s:
        assert (await s.get(Proposal, p.id)).status == "open"
