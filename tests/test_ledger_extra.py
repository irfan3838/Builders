"""Extra ledger/proposal/confirmation coverage for PLAN_v4 §2, §3 and §6 (lifecycle, roles, settlement
validation, bill flow, voice-evidence edge cases, audit trail)."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select, update

from app import db
from app.errors import (
    ALREADY_SETTLED,
    CONFIRMATION_REQUIRED,
    FORBIDDEN,
    INVALID_STATE,
    NOT_FOUND,
    PROPOSAL_CLOSED,
    VALIDATION,
    DomainError,
)
from app.models import AuditEvent, Bill, BudgetLine, BudgetMovement, Claim, Conversation, Party, Proposal, Receipt, Settlement
from app.services import budget, confirmation, proposals, records
from app.services.affirmation import Affirmation, classify
from tests.conftest import add_inspected_document, make_actor
from tests.test_ledger_gates import propose_and_confirm, submit_arjun_hotel_claim, travel

R = 100


# ------------------------------------------------------------------ helpers


async def count(model, *where) -> int:
    async with db.session_scope() as s:
        return (await s.execute(select(func.count()).select_from(model).where(*where))).scalar_one()


async def create_presented(actor, kind, args) -> Proposal:
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, kind, args)
        await proposals.mark_presented(s, p.id)
        return p


async def status_of(pid) -> str:
    async with db.session_scope() as s:
        return (await s.get(Proposal, pid)).status


async def code_of(actor, kind, args, *, confirm=False) -> str:
    """Return the DomainError code raised when planning (or confirming) the action."""
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            p = await proposals.create(s, actor, kind, args)
            if confirm:
                await proposals.confirm(s, actor, p.id, via="button")
    return e.value.code


async def assert_conservation():
    async with db.session_scope() as s:
        for line in (await s.execute(select(BudgetLine))).scalars():
            p = await budget.position(s, line.workspace_id, line.id)
            assert min(p["reserved_paise"], p["committed_paise"], p["spent_paise"]) >= 0, (line.category, p)
            assert p["available_paise"] == p["allocated_paise"] - p["reserved_paise"] - p["committed_paise"] - p["spent_paise"]
            assert p["available_paise"] >= 0, (line.category, p)


async def line_pos(category):
    async with db.session_scope() as s:
        line = await budget.get_line(s, 1, category=category)
        return await budget.position(s, line.workspace_id, line.id)


async def vendor_id(name):
    async with db.session_scope() as s:
        return (await s.execute(select(Party.id).where(Party.name == name))).scalar_one()


async def seeded_bill(state, settlement="unpaid"):
    async with db.session_scope() as s:
        return (await s.execute(select(Bill).where(Bill.state == state, Bill.settlement_state == settlement).order_by(Bill.id))).scalars().first()


# ------------------------------------------------------------------ proposal lifecycle


async def test_expired_proposal_does_not_execute_and_returns_fresh_preview(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    p = await create_presented(priya, "approve", {"ref": ref})
    async with db.session_scope() as s:
        await s.execute(update(Proposal).where(Proposal.id == p.id).values(expires_at=func.now() - timedelta(seconds=5)))
    async with db.session_scope() as s:
        out = await proposals.confirm(s, priya, p.id, via="button")
    assert out.status == "expired" and out.receipt is None and out.new_proposal is not None
    assert out.new_proposal.id != p.id and out.new_proposal.status == "open"
    assert (await travel(ids))["committed_paise"] == 0
    assert await status_of(p.id) == "expired"
    async with db.session_scope() as s:
        assert (await s.get(Proposal, p.id)).superseded_by == out.new_proposal.id
    assert await code_of_confirm_closed(priya, p.id) == PROPOSAL_CLOSED  # an expired proposal can never be revived


async def code_of_confirm_closed(actor, pid) -> str:
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.confirm(s, actor, pid, via="button")
    return e.value.code


async def test_new_proposal_supersedes_foreground_and_old_cannot_confirm(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    p1 = await create_presented(priya, "approve", {"ref": ref})
    p2 = await create_presented(priya, "settle", {"ref": (await seeded_bill("approved")).ref, "reference": "UTR-9"})
    assert await status_of(p1.id) == "superseded" and await status_of(p2.id) == "open"
    async with db.session_scope() as s:
        conv = await s.get(Conversation, priya.conversation_id)
        assert conv.foreground_proposal_id == p2.id
        assert (await proposals.get_open(s, priya)).id == p2.id
    assert await code_of_confirm_closed(priya, p1.id) == PROPOSAL_CLOSED
    assert (await travel(ids))["committed_paise"] == 0  # the superseded approval left no trace


async def test_cancel_then_confirm_is_rejected_and_changes_nothing(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    p = await create_presented(priya, "approve", {"ref": ref})
    movements_before, receipts_before = await count(BudgetMovement), await count(Receipt)
    async with db.session_scope() as s:
        assert (await proposals.cancel(s, priya, p.id)).status == "cancelled"
    assert await code_of_confirm_closed(priya, p.id) == PROPOSAL_CLOSED
    assert await count(BudgetMovement) == movements_before and await count(Receipt) == receipts_before
    async with db.session_scope() as s:
        assert await proposals.get_open(s, priya) is None
        c = (await s.execute(select(Claim).where(Claim.ref == ref))).scalar_one()
        assert c.state == "submitted"
    assert await count(AuditEvent, AuditEvent.action == "proposal.cancelled", AuditEvent.proposal_id == p.id) == 1


async def test_cancel_after_execution_does_not_undo(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    p, out = await propose_and_confirm(priya, "approve", {"ref": ref})
    async with db.session_scope() as s:
        assert (await proposals.cancel(s, priya, p.id)).status == "executed"
    assert (await travel(ids))["committed_paise"] == 4_800 * R and out.status == "executed"


async def test_cannot_confirm_or_cancel_another_actors_proposal(seeded):
    ids, priya = seeded, await make_actor(seeded)
    arjun = await make_actor(seeded, "arjun")
    ref = await submit_arjun_hotel_claim(ids, priya)
    p = await create_presented(priya, "approve", {"ref": ref})
    assert await code_of_confirm_closed(arjun, p.id) == NOT_FOUND
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.cancel(s, arjun, p.id)
    assert e.value.code == NOT_FOUND
    assert await status_of(p.id) == "open" and (await travel(ids))["committed_paise"] == 0


async def test_cannot_confirm_proposal_from_other_workspace(seeded):
    priya = await make_actor(seeded)
    from seed.seed_v1 import seed
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    other_priya = await make_actor(other)
    p = await create_presented(other_priya, "approve", {"ref": other["neha_claim_ref"]})
    assert await code_of_confirm_closed(priya, p.id) == NOT_FOUND


async def test_two_proposals_for_same_document_only_one_claim_created(seeded):
    ids = seeded
    p1_actor = await make_actor(ids)
    p2_actor = await make_actor(ids)  # second session/conversation, so the proposals do not supersede each other
    doc = await add_inspected_document(p1_actor)
    args = {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"}
    a = await create_presented(p1_actor, "submit_claim", args)
    b = await create_presented(p2_actor, "submit_claim", args)
    async with db.session_scope() as s:
        assert (await proposals.confirm(s, p1_actor, a.id, via="button")).status == "executed"
    with pytest.raises(DomainError) as e:  # second confirm sees the document closed (stale -> re-plan -> INVALID_STATE)
        async with db.session_scope() as s:
            await proposals.confirm(s, p2_actor, b.id, via="button")
    assert e.value.code == INVALID_STATE
    assert await count(Claim, Claim.document_id == doc) == 1
    assert await status_of(b.id) == "open"  # rolled back: nothing half-applied


async def test_submit_claim_on_closed_document_rejected(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya)
    args = {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"}
    await propose_and_confirm(priya, "submit_claim", args)
    assert await code_of(priya, "submit_claim", args) == INVALID_STATE


async def test_approving_already_approved_claim_rejected(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    await propose_and_confirm(priya, "approve", {"ref": ref})
    assert await code_of(priya, "approve", {"ref": ref}) == INVALID_STATE


# ------------------------------------------------------------------ roles


async def test_employee_submits_own_claim_but_not_for_someone_else(seeded):
    ids, arjun = seeded, await make_actor(seeded, "arjun")
    doc = await add_inspected_document(arjun, vendor="Meru Cabs", total_rupees=640, sha="c" * 64)
    # for a colleague: forbidden at plan time, nothing persisted
    before = await count(Proposal)
    assert await code_of(arjun, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["priya_party_id"], "category": "Conveyance"}) == FORBIDDEN
    assert await count(Proposal) == before and await count(Claim, Claim.document_id == doc) == 0
    # for self: allowed, and the claim is attributed to him and stays pending (no budget change)
    pos_before = await line_pos("Conveyance")
    _, out = await propose_and_confirm(arjun, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Conveyance"})
    assert out.status == "executed"
    async with db.session_scope() as s:
        c = (await s.execute(select(Claim).where(Claim.document_id == doc))).scalar_one()
        assert (c.submitter_id, c.beneficiary_party_id, c.state, c.amount_paise) == (arjun.user_id, ids["arjun_party_id"], "submitted", 640 * R)
    pos_after = await line_pos("Conveyance")
    assert pos_after["committed_paise"] == pos_before["committed_paise"] and pos_after["available_paise"] == pos_before["available_paise"]
    assert pos_after["pending_claims_paise"] == pos_before["pending_claims_paise"] + 640 * R


async def test_employee_cannot_use_another_users_document(seeded):
    ids, priya, arjun = seeded, await make_actor(seeded), await make_actor(seeded, "arjun")
    doc = await add_inspected_document(priya, sha="d" * 64)
    assert await code_of(arjun, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel"}) == NOT_FOUND


async def test_employee_cannot_approve_settle_or_submit_bill(seeded):
    ids, priya, arjun = seeded, await make_actor(seeded), await make_actor(seeded, "arjun")
    ref = await submit_arjun_hotel_claim(ids, priya)
    assert await code_of(arjun, "approve", {"ref": ref}) == FORBIDDEN
    assert await code_of(arjun, "settle", {"ref": ref, "reference": "X1"}) == FORBIDDEN
    doc = await add_inspected_document(arjun, sha="e" * 64)
    assert await code_of(arjun, "submit_bill", {"document_id": doc, "vendor_party_id": await vendor_id("Shree Ganesh Printers"), "category": "Office Supplies"}) == FORBIDDEN


async def test_vendor_party_cannot_be_used_as_beneficiary(seeded):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, sha="f" * 64)
    assert await code_of(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": await vendor_id("Kaveri Caterers"), "category": "Events"}) == NOT_FOUND


# ------------------------------------------------------------------ settlement validation


async def test_settle_rejects_empty_reference(seeded):
    priya, b = await make_actor(seeded), await seeded_bill("approved")
    for ref_value in ("", "   ", None):
        args = {"ref": b.ref, **({} if ref_value is None else {"reference": ref_value})}
        assert await code_of(priya, "settle", args) == VALIDATION
    assert await count(Settlement, Settlement.record_id == b.id, Settlement.record_type == "bill") == 0


async def test_settle_rejects_future_date_but_accepts_today_and_past(seeded):
    priya, b = await make_actor(seeded), await seeded_bill("approved")
    tomorrow = records.today_ist() + timedelta(days=1)
    assert await code_of(priya, "settle", {"ref": b.ref, "reference": "UTR-F", "business_date": tomorrow.isoformat()}) == VALIDATION
    assert await count(Settlement, Settlement.record_id == b.id, Settlement.record_type == "bill") == 0
    past = records.today_ist() - timedelta(days=3)
    _, out = await propose_and_confirm(priya, "settle", {"ref": b.ref, "reference": "UTR-P", "business_date": past.isoformat()})
    assert out.status == "executed"
    async with db.session_scope() as s:
        st = (await s.execute(select(Settlement).where(Settlement.record_id == b.id, Settlement.record_type == "bill"))).scalar_one()
        assert (st.business_date, st.reference, st.amount_paise) == (past, "UTR-P", b.amount_paise)


async def test_settle_defaults_to_today_ist(seeded):
    priya, b = await make_actor(seeded), await seeded_bill("approved")
    await propose_and_confirm(priya, "settle", {"ref": b.ref, "reference": "UTR-T"})
    async with db.session_scope() as s:
        st = (await s.execute(select(Settlement).where(Settlement.record_id == b.id, Settlement.record_type == "bill"))).scalar_one()
        assert st.business_date == records.today_ist()


async def test_settle_unapproved_records_rejected(seeded):
    ids, priya = seeded, await make_actor(seeded)
    submitted_bill = await seeded_bill("submitted")
    assert await code_of(priya, "settle", {"ref": submitted_bill.ref, "reference": "UTR-1"}) == INVALID_STATE
    claim_ref = await submit_arjun_hotel_claim(ids, priya)  # submitted, not approved
    assert await code_of(priya, "settle", {"ref": claim_ref, "reference": "UTR-2"}) == INVALID_STATE
    assert await count(Settlement, Settlement.record_id.in_([submitted_bill.id])) == 0
    await assert_conservation()


async def test_settle_ref_is_case_and_space_insensitive_and_unknown_ref_not_found(seeded):
    priya, b = await make_actor(seeded), await seeded_bill("approved")
    _, out = await propose_and_confirm(priya, "settle", {"ref": f"  {b.ref.lower()} ", "reference": "UTR-c"})
    assert out.status == "executed"
    assert await code_of(priya, "settle", {"ref": "B99999", "reference": "UTR-x"}) == NOT_FOUND


async def test_settle_already_settled_seed_bill_rejected(seeded):
    priya, b = await make_actor(seeded), await seeded_bill("approved", "settled")
    assert await code_of(priya, "settle", {"ref": b.ref, "reference": "UTR-again"}) == ALREADY_SETTLED


async def test_double_settle_via_two_open_proposals_executes_once(seeded):
    priya, priya2, b = await make_actor(seeded), await make_actor(seeded), await seeded_bill("approved")
    a = await create_presented(priya, "settle", {"ref": b.ref, "reference": "UTR-A"})
    c = await create_presented(priya2, "settle", {"ref": b.ref, "reference": "UTR-B"})
    async with db.session_scope() as s:
        assert (await proposals.confirm(s, priya, a.id, via="button")).status == "executed"
    with pytest.raises(DomainError) as e:  # stale -> re-plan -> already settled
        async with db.session_scope() as s:
            await proposals.confirm(s, priya2, c.id, via="button")
    assert e.value.code == ALREADY_SETTLED
    assert await count(Settlement, Settlement.record_id == b.id, Settlement.record_type == "bill") == 1
    assert (await line_pos("Office Supplies"))["spent_paise"] == b.amount_paise
    await assert_conservation()


# ------------------------------------------------------------------ vendor bill flow


async def test_vendor_bill_submit_approve_settle_balances(seeded):
    priya = await make_actor(seeded)
    start = await line_pos("Office Supplies")
    amt = 12_000 * R
    doc = await add_inspected_document(priya, vendor="Shree Ganesh Printers", total_rupees=12_000, sha="9" * 64, doc_type="invoice")
    vid = await vendor_id("Shree Ganesh Printers")

    _, out = await propose_and_confirm(priya, "submit_bill", {"document_id": doc, "vendor_party_id": vid, "category": "Office Supplies"})
    ref = out.receipt.effects[0]["ref"]
    assert ref.startswith("B") and out.receipt.effects[0]["amount_paise"] == amt
    assert await line_pos("Office Supplies") == start  # entering a bill moves no money

    _, out = await propose_and_confirm(priya, "approve", {"ref": ref})  # Approve dispatches B-prefix to bills
    mid = await line_pos("Office Supplies")
    assert mid["committed_paise"] == start["committed_paise"] + amt
    assert mid["available_paise"] == start["available_paise"] - amt
    assert mid["spent_paise"] == start["spent_paise"] and mid["reserved_paise"] == start["reserved_paise"]
    assert out.receipt.effects[1]["available_delta_paise"] == -amt

    _, out = await propose_and_confirm(priya, "settle", {"ref": ref, "reference": "NEFT-5001"})
    end = await line_pos("Office Supplies")
    assert end["committed_paise"] == start["committed_paise"]
    assert end["spent_paise"] == start["spent_paise"] + amt
    assert end["available_paise"] == mid["available_paise"]  # settlement never changes availability
    async with db.session_scope() as s:
        b = (await s.execute(select(Bill).where(Bill.ref == ref))).scalar_one()
        assert (b.state, b.settlement_state) == ("approved", "settled")
        d = await records.document(s, priya, doc)
        assert (d.outcome, d.status) == ("bill", "closed")
    await assert_conservation()
    assert await code_of(priya, "settle", {"ref": ref, "reference": "NEFT-5002"}) == ALREADY_SETTLED


async def test_bill_cannot_be_approved_twice_and_submitter_may_approve_bill(seeded):
    priya, b = await make_actor(seeded), await seeded_bill("submitted")
    await propose_and_confirm(priya, "approve", {"ref": b.ref})  # PLAN v4 §2.5: no segregation rule on bills
    assert await code_of(priya, "approve", {"ref": b.ref}) == INVALID_STATE


async def test_bill_submit_rejects_claim_party_and_arithmetic_mismatch(seeded):
    ids, priya = seeded, await make_actor(seeded)
    doc = await add_inspected_document(priya, sha="8" * 64)
    assert await code_of(priya, "submit_bill", {"document_id": doc, "vendor_party_id": ids["arjun_party_id"], "category": "Office Supplies"}) == NOT_FOUND
    bad = await add_inspected_document(priya, sha="7" * 64, arithmetic="mismatch")
    assert await code_of(priya, "submit_bill", {"document_id": bad, "vendor_party_id": await vendor_id("Shree Ganesh Printers"), "category": "Office Supplies"}) == VALIDATION
    assert await code_of(priya, "submit_bill", {"document_id": doc, "vendor_party_id": await vendor_id("Shree Ganesh Printers"), "category": "Nonexistent"}) == NOT_FOUND


async def test_claim_without_reservation_commits_exactly_amount(seeded):
    ids, priya = seeded, await make_actor(seeded)
    start = await line_pos("Conveyance")
    doc = await add_inspected_document(priya, vendor="Meru Cabs", total_rupees=900, sha="6" * 64)
    _, out = await propose_and_confirm(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Conveyance"})
    _, _ = await propose_and_confirm(priya, "approve", {"ref": out.receipt.effects[0]["ref"]})
    end = await line_pos("Conveyance")
    assert end["committed_paise"] - start["committed_paise"] == 900 * R and end["reserved_paise"] == start["reserved_paise"]
    assert end["available_paise"] == start["available_paise"] - 900 * R
    await assert_conservation()


async def test_reservation_cannot_be_reused_after_final_charge(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    await propose_and_confirm(priya, "approve", {"ref": ref})
    doc = await add_inspected_document(priya, sha="5" * 64, total_rupees=1000)
    code = await code_of(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": ids["arjun_party_id"], "category": "Travel",
                                                  "reservation_id": ids["reservation_id"], "reservation_treatment": "final"})
    assert code == INVALID_STATE


# ------------------------------------------------------------------ audit + receipt per confirmed action


async def test_full_claim_flow_writes_receipt_and_audit_per_action(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    p_appr, appr = await propose_and_confirm(priya, "approve", {"ref": ref})
    p_set, sett = await propose_and_confirm(priya, "settle", {"ref": ref, "reference": "4471"})
    receipts = {appr.receipt.id, sett.receipt.id}
    assert len(receipts) == 2 and await count(Receipt) == 3  # submit + approve + settle
    async with db.session_scope() as s:
        for pid, out, action in ((p_appr.id, appr, "claim.approved"), (p_set.id, sett, "claim.settled")):
            r = await s.get(Receipt, out.receipt.id)
            assert r.proposal_id == pid and r.confirmed_via == "button" and r.actor_id == priya.user_id and r.summary and r.effects
            prop = await s.get(Proposal, pid)
            assert (prop.status, prop.receipt_id) == ("executed", r.id) and r.idempotency_key == prop.idempotency_key
            rows = (await s.execute(select(AuditEvent).where(AuditEvent.receipt_id == r.id))).scalars().all()
            assert {a.action for a in rows} == {"proposal.confirmed", action}
            assert all(a.actor_id == priya.user_id and a.workspace_id == priya.workspace_id for a in rows)
            domain = next(a for a in rows if a.action == action)
            assert domain.record_ref == ref
            moved = (await s.execute(select(func.count()).select_from(BudgetMovement).where(BudgetMovement.receipt_id == r.id))).scalar_one()
            assert moved >= 1  # every budget movement is traceable to a receipt
        created = (await s.execute(select(AuditEvent).where(AuditEvent.action == "proposal.created", AuditEvent.proposal_id == p_appr.id))).scalars().all()
        assert len(created) == 1
        st = (await s.execute(select(Settlement).where(Settlement.record_type == "claim"))).scalar_one()
        assert st.receipt_id == sett.receipt.id and st.recorded_by == priya.user_id


async def test_replay_writes_no_extra_audit_or_receipt(seeded):
    ids, priya = seeded, await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    p, first = await propose_and_confirm(priya, "approve", {"ref": ref})
    n_audit, n_rcpt, n_mov = await count(AuditEvent), await count(Receipt), await count(BudgetMovement)
    for _ in range(3):
        async with db.session_scope() as s:
            again = await proposals.confirm(s, priya, p.id, via="voice")
        assert again.status == "replayed" and again.receipt.id == first.receipt.id
    assert (await count(AuditEvent), await count(Receipt), await count(BudgetMovement)) == (n_audit, n_rcpt, n_mov)
    async with db.session_scope() as s:
        assert (await s.get(Receipt, first.receipt.id)).confirmed_via == "button"  # replay does not rewrite provenance


async def test_rejected_attempts_leave_no_receipt_or_movement(seeded):
    priya = await make_actor(seeded)
    b = await seeded_bill("approved")
    n_rcpt, n_mov = await count(Receipt), await count(BudgetMovement)
    await code_of(priya, "settle", {"ref": b.ref, "reference": ""})
    await code_of(priya, "approve", {"ref": b.ref})  # already approved
    assert (await count(Receipt), await count(BudgetMovement)) == (n_rcpt, n_mov)


async def test_stale_after_other_actor_settles_creates_no_second_effect(seeded):
    """Preview was for approve; the claim is approved by a different conversation first."""
    ids, priya = seeded, await make_actor(seeded)
    priya_b = await make_actor(seeded)
    ref = await submit_arjun_hotel_claim(ids, priya)
    a = await create_presented(priya, "approve", {"ref": ref})
    b = await create_presented(priya_b, "approve", {"ref": ref})
    async with db.session_scope() as s:
        await proposals.confirm(s, priya, a.id, via="button")
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.confirm(s, priya_b, b.id, via="button")
    assert e.value.code == INVALID_STATE
    pos = await travel(ids)
    assert (pos["committed_paise"], pos["reserved_paise"]) == (4_800 * R, 0)  # committed once, reservation released once
    await assert_conservation()


# ------------------------------------------------------------------ spoken confirmation evidence


async def _present_then_turn(actor, p, text, **kw):
    async with db.session_scope() as s:
        await proposals.mark_presented(s, p.id, offset_ms=kw.pop("offset_ms", None))
    async with db.session_scope() as s:
        await confirmation.record_turn(s, actor, text, source=kw.pop("source", "live_sideband"), **kw)


async def _spoken(actor, pid):
    async with db.session_scope() as s:
        return await confirmation.spoken_confirmation(s, actor, await s.get(Proposal, pid))


async def _open_approve(ids, priya):
    ref = await submit_arjun_hotel_claim(ids, priya)
    async with db.session_scope() as s:
        return await proposals.create(s, priya, "approve", {"ref": ref})


async def test_interrupted_or_incomplete_turn_is_not_confirmation(seeded):
    ids, priya = seeded, await make_actor(seeded)
    p = await _open_approve(ids, priya)
    await _present_then_turn(priya, p, "haan kar do", interrupted=True)
    with pytest.raises(DomainError) as e:
        await _spoken(priya, p.id)
    assert e.value.code == CONFIRMATION_REQUIRED and "interrupted" in e.value.message
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "yes", source="live_sideband", completed=False)
    with pytest.raises(DomainError) as e:
        await _spoken(priya, p.id)
    assert e.value.code == CONFIRMATION_REQUIRED
    async with db.session_scope() as s:  # a later, clean turn becomes the evidence
        await confirmation.record_turn(s, priya, "yes", source="live_sideband")
    assert (await _spoken(priya, p.id))["classification"] == "affirm"


async def test_reply_that_began_before_preview_finished_is_rejected(seeded):
    ids, priya = seeded, await make_actor(seeded)
    p = await _open_approve(ids, priya)
    await _present_then_turn(priya, p, "haan", offset_ms=5_000, start_ms=3_000, end_ms=3_800)
    with pytest.raises(DomainError) as e:
        await _spoken(priya, p.id)
    assert e.value.code == CONFIRMATION_REQUIRED and "before the preview finished" in e.value.message
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "haan", source="live_sideband", start_ms=6_000, end_ms=6_500)
    assert (await _spoken(priya, p.id))["classification"] == "affirm"


async def test_old_yes_cannot_confirm_a_newer_proposal(seeded):
    ids, priya = seeded, await make_actor(seeded)
    p1 = await _open_approve(ids, priya)
    await _present_then_turn(priya, p1, "haan")
    ev = await _spoken(priya, p1.id)
    async with db.session_scope() as s:
        out = await proposals.confirm(s, priya, p1.id, via="voice", evidence=ev)
    assert out.status == "executed"
    async with db.session_scope() as s:
        r = await s.get(Receipt, out.receipt.id)
        assert r.confirmed_via == "voice" and r.confirmation_evidence["transcript"] == "haan" and r.confirmation_evidence["turn_id"] == ev["turn_id"]
    b = await seeded_bill("approved")
    p2 = await create_presented(priya, "settle", {"ref": b.ref, "reference": "UTR-V"})
    with pytest.raises(DomainError) as e:  # the only turn on record predates p2's preview
        await _spoken(priya, p2.id)
    assert e.value.code == CONFIRMATION_REQUIRED


async def test_unpresented_or_foreign_conversation_proposal_not_confirmable(seeded):
    ids, priya = seeded, await make_actor(seeded)
    p = await _open_approve(ids, priya)
    other_conv = await make_actor(seeded)  # same user, different conversation
    await _present_then_turn(priya, p, "haan")
    async with db.session_scope() as s:
        await confirmation.record_turn(s, other_conv, "haan", source="text")
    with pytest.raises(DomainError) as e:
        await _spoken(other_conv, p.id)
    assert e.value.code == CONFIRMATION_REQUIRED and "another conversation" in e.value.message


async def test_latest_turn_wins_a_later_no_revokes_an_earlier_yes(seeded):
    ids, priya = seeded, await make_actor(seeded)
    p = await _open_approve(ids, priya)
    await _present_then_turn(priya, p, "haan")
    async with db.session_scope() as s:
        await confirmation.record_turn(s, priya, "nahi ruko", source="live_sideband")
    with pytest.raises(DomainError) as e:
        await _spoken(priya, p.id)
    assert e.value.details["classification"] == "negative" and e.value.details["heard"] == "nahi ruko"


async def test_client_controlled_source_is_not_accepted_as_evidence(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        with pytest.raises(AssertionError):
            await confirmation.record_turn(s, priya, "haan", source="browser_claim")


# ------------------------------------------------------------------ Hindi / Hinglish / English classifier edges


@pytest.mark.parametrize("text", [
    "HAAN JI", "Haan, ji!", "haan haan", "ji haan, bilkul", "OK.", "okay okay", "हाँ जी, कर दीजिए।", "हां  जी", "जी हाँ",
    "बिल्कुल सही है", "ठीक है, कर दो", "theek hai bhai", "kar do toh", "Yes, please!", "go ahead", "I confirm", "haan ji kar do abhi",
])
def test_affirm_variants(text):
    assert classify(text) is Affirmation.AFFIRM


@pytest.mark.parametrize("text", [
    "na kar do", "no no no", "नहीं नहीं", "nahi", "रुको", "mat karo", "cancel", "stop", "wait", "नहीं, गलत है",
])
def test_negative_variants(text):
    assert classify(text) is Affirmation.NEGATIVE


@pytest.mark.parametrize("text", [
    "haan nahi", "yes no", "ok but wait", "ठीक है लेकिन रुको", "हाँ पर राशि गलत है", "haan 4800 hai na", "yes, and also approve the other one",
    "haan kal karna", "हाँ 5000", "   ", "...", "hmm", "ji bataiye", "kitna hai", "not okay", "do it tomorrow", "yes yes change the vendor",
])
def test_not_a_clear_yes_never_affirms(text):
    assert classify(text) is not Affirmation.AFFIRM


def test_empty_and_none_are_ambiguous():
    assert classify(None) is Affirmation.AMBIGUOUS and classify("") is Affirmation.AMBIGUOUS


def test_devanagari_softener_na_affirms():
    assert classify("कर दो ना") is Affirmation.AFFIRM


def test_dont_do_it_is_negative():
    assert classify("don't do it") is Affirmation.NEGATIVE
