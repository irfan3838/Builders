"""Workspace read models (app/api/workspace.py), claim_review cards from agent tools, and Purser rename fallout. No model calls."""

from datetime import date

import pytest
from sqlalchemy import func, select

from app import db
from app.models import Message, Proposal
from app.services import budget, proposals
from tests.conftest import add_inspected_document, make_actor
from tests.test_api_intake import client_for
from tests.test_intake_extra import call
from tests.test_ledger_gates import propose_and_confirm, submit_arjun_hotel_claim

R = 100


async def travel_available(ids) -> int:
    async with db.session_scope() as s:
        from app.models import BudgetLine
        line = (await s.execute(select(BudgetLine).where(BudgetLine.category == "Travel"))).scalars().first()
        return (await budget.position(s, line.workspace_id, line.id))["available_paise"]


async def new_claim(ids, total=4800) -> tuple[str, "object"]:
    priya = await make_actor(ids)
    ref = await submit_arjun_hotel_claim(ids, priya, total)
    return ref, priya


# ------------------------------------------------------------------ claim review


async def test_claim_review_impact_matches_plan_preview(seeded):
    ref, priya = await new_claim(seeded)
    avail = await travel_available(seeded)  # before approval; claim submission itself changes nothing
    assert avail == 45_000 * R
    c = await client_for()
    j = (await c.get("/api/claim-review", params={"ref": ref})).json()
    assert j["status"] == "submitted" and j["ref"] == ref
    imp = j["impact"]
    assert imp["final"] is False and imp["category"] == "Travel"
    assert imp["before_paise"] == 45_000 * R and imp["after_paise"] == 45_200 * R
    # must equal what ApproveClaim.plan previews
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "approve", {"ref": ref})
        lines = p.preview["lines"]
    assert any("45,000" in ln and "45,200" in ln for ln in lines), lines
    assert j["receipt"]["total_paise"] == 4800 * R
    assert j["comparison"]["reserved_paise"] == 5000 * R and j["comparison"]["difference_paise"] == 200 * R and j["comparison"]["below"]
    labels = {k["label"]: k["ok"] for k in j["checks"]}
    assert labels["Date within trip"] is True and labels["Within reserved amount"] is True
    await c.aclose()


async def test_claim_review_after_approval_uses_receipt(seeded):
    ref, priya = await new_claim(seeded)
    _, out = await propose_and_confirm(priya, "approve", {"ref": ref})
    assert out.status == "executed"
    c = await client_for()
    j = (await c.get("/api/claim-review", params={"ref": ref})).json()
    assert j["status"] == "approved"
    imp = j["impact"]
    assert imp["final"] is True and imp["receipt"] == out.receipt.ref
    assert (imp["before_paise"], imp["after_paise"]) == (45_000 * R, 45_200 * R)
    assert j["proposal"] is None
    await c.aclose()


async def test_claim_review_checks_fail_when_over_amount_and_outside_trip(seeded):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, total_rupees=6000, bdate=date(2026, 11, 25), sha="b" * 64)
    c = await client_for()
    j = (await c.get("/api/claim-review", params={"document_id": doc, "reservation_id": seeded["reservation_id"]})).json()
    labels = {k["label"]: k["ok"] for k in j["checks"]}
    assert labels["Date within trip"] is False and labels["Within reserved amount"] is False
    assert j["status"] == "receipt" and j["comparison"]["below"] is False
    await c.aclose()


async def test_claim_review_requires_ref_or_document(seeded):
    c = await client_for()
    assert (await c.get("/api/claim-review")).status_code == 400
    await c.aclose()


async def test_claim_review_by_document_shows_open_submit_proposal(seeded):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya)
    async with db.session_scope() as s:
        await proposals.create(s, priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": seeded["arjun_party_id"], "category": "Travel",
                                                          "reservation_id": seeded["reservation_id"], "reservation_treatment": "final"})
    c = await client_for()
    j = (await c.get("/api/claim-review", params={"document_id": doc, "reservation_id": seeded["reservation_id"]})).json()
    assert j["proposal"] and j["proposal"]["kind"] == "submit_claim"
    assert j["impact"]["after_paise"] == 45_200 * R
    await c.aclose()


async def test_employee_cannot_see_others_claim_review(seeded):
    # claim for Neha (not Arjun) submitted by priya
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, vendor="Cafe X", total_rupees=900, sha="c" * 64)
    from app.models import User
    async with db.session_scope() as s:
        neha_party_id = (await s.get(User, seeded["neha_id"])).party_id
    _, out = await propose_and_confirm(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": neha_party_id, "category": "Travel"})
    ref = out.receipt.effects[0]["ref"]
    arjun = await client_for("arjun@purser.demo")
    assert (await arjun.get("/api/claim-review", params={"ref": ref})).status_code == 404
    lst = (await arjun.get("/api/claims")).json()["claims"]
    assert ref not in [x["ref"] for x in lst]
    neha = await client_for("neha@purser.demo")
    assert ref in [x["ref"] for x in (await neha.get("/api/claims")).json()["claims"]]
    await arjun.aclose()
    await neha.aclose()


# ------------------------------------------------------------------ lists + authorization


async def test_claims_state_filter(seeded):
    ref, priya = await new_claim(seeded)
    c = await client_for()
    sub = [x["ref"] for x in (await c.get("/api/claims", params={"state": "submitted"})).json()["claims"]]
    assert ref in sub and all(x["state"] == "submitted" for x in (await c.get("/api/claims", params={"state": "submitted"})).json()["claims"])
    assert ref not in [x["ref"] for x in (await c.get("/api/claims", params={"state": "approved"})).json()["claims"]]
    await c.aclose()


async def test_bills_and_payments_approver_only(seeded):
    arjun = await client_for("arjun@purser.demo")
    assert (await arjun.get("/api/bills")).status_code == 403
    assert (await arjun.get("/api/payments")).status_code == 403
    await arjun.aclose()
    c = await client_for()
    bills = (await c.get("/api/bills")).json()["bills"]
    assert bills and all("ref" in b and "amount_paise" in b for b in bills)
    await c.aclose()


async def test_payments_awaiting_is_approved_and_unpaid(seeded):
    ref, priya = await new_claim(seeded)
    c = await client_for()
    before = (await c.get("/api/payments")).json()
    assert ref not in [x["id"] for x in before["awaiting"]]  # submitted, not approved
    await propose_and_confirm(priya, "approve", {"ref": ref})
    mid = (await c.get("/api/payments")).json()
    row = next(x for x in mid["awaiting"] if x["id"] == ref)
    assert row["status"] == "awaiting_payment" and row["method"] == "Reimbursement"
    await propose_and_confirm(priya, "settle", {"ref": ref, "reference": "UTR123", "business_date": "2026-11-20"})
    after = (await c.get("/api/payments")).json()
    assert ref not in [x["id"] for x in after["awaiting"]]
    assert any(h["record"] == ref and h["reference"] == "UTR123" and h["status"] == "settled" for h in after["history"])
    await c.aclose()


async def test_budget_lines_shape(seeded):
    c = await client_for()
    lines = (await c.get("/api/budget/lines")).json()["lines"]
    travel = next(x for x in lines if x["category"] == "Travel")
    assert travel["available_paise"] == 45_000 * R and travel["available"].startswith("₹")
    assert [x["category"] for x in lines] == sorted(x["category"] for x in lines)
    await c.aclose()


async def test_trips_employee_sees_only_own(seeded):
    ref, _ = await new_claim(seeded)
    arjun = await client_for("arjun@purser.demo")
    t = (await arjun.get("/api/trips")).json()["trips"]
    assert len(t) == 1 and t[0]["city"] == "Pune"
    assert t[0]["reservations"][0]["claim"]["ref"] == ref
    neha = await client_for("neha@purser.demo")
    assert (await neha.get("/api/trips")).json()["trips"] == []
    priya = await client_for()
    assert len((await priya.get("/api/trips")).json()["trips"]) == 1
    for x in (arjun, neha, priya):
        await x.aclose()


async def test_priorities_and_alerts(seeded):
    await new_claim(seeded)
    c = await client_for()
    p = (await c.get("/api/priorities")).json()
    assert p["approvals"] >= 1 and p["claims_pending"] >= 1 and set(p) == {"approvals", "reimbursements", "budget_alerts", "claims_pending", "unread_mail"}
    assert (await c.get("/api/budget/alerts")).status_code == 200
    arjun = await client_for("arjun@purser.demo")
    pa = (await arjun.get("/api/priorities")).json()
    assert pa["approvals"] == 0 and pa["claims_pending"] == 0 and pa["reimbursements"] == 0
    await c.aclose()
    await arjun.aclose()


async def test_people_directory_excludes_self(seeded):
    c = await client_for()
    names = [p["name"] for p in (await c.get("/api/people")).json()["people"]]
    assert names and "Priya" not in " ".join(names).split()[0:0] and len(names) == len(set(names))
    me = (await c.get("/api/me")).json()["name"]
    assert me not in names
    await c.aclose()


async def test_documents_list_scoping(seeded):
    priya = await make_actor(seeded)
    await add_inspected_document(priya)
    c = await client_for()
    assert len((await c.get("/api/documents")).json()["documents"]) == 1
    arjun = await client_for("arjun@purser.demo")
    assert (await arjun.get("/api/documents")).json()["documents"] == []
    await c.aclose()
    await arjun.aclose()


# ------------------------------------------------------------------ mail


async def msg_count() -> int:
    async with db.session_scope() as s:
        return (await s.execute(select(func.count()).select_from(Message))).scalar_one()


async def test_draft_creates_proposal_only_then_confirm_sends(seeded):
    c = await client_for()
    arjun_id = seeded["arjun_id"]
    n0 = await msg_count()
    r = await c.post("/api/messages/draft", json={"user_ids": [arjun_id], "subject": "Hello", "body": "Welcome aboard"})
    assert r.status_code == 201
    pid = r.json()["proposal_id"]
    assert await msg_count() == n0  # nothing sent by drafting
    async with db.session_scope() as s:
        p = await s.get(Proposal, pid)
        assert p.kind == "send_message" and p.status == "open"
    ok = await c.post(f"/api/proposals/{pid}/confirm")
    assert ok.status_code == 200 and ok.json()["status"] == "executed"
    assert await msg_count() == n0 + 1
    again = await c.post(f"/api/proposals/{pid}/confirm")
    assert again.json()["status"] == "replayed" and await msg_count() == n0 + 1
    sent = (await c.get("/api/messages/sent")).json()["messages"]
    assert sent and sent[0]["subject"] == "Hello" and sent[0]["to"]
    # recipient sees it, marks read
    arjun = await client_for("arjun@purser.demo")
    ref = sent[0]["ref"]
    unread = (await arjun.get("/api/priorities")).json()["unread_mail"]
    assert unread >= 1  # includes seeded unread mail
    assert (await arjun.post(f"/api/inbox/{ref}/read")).json() == {"ref": ref, "unread": False}
    assert (await arjun.get("/api/priorities")).json()["unread_mail"] == unread - 1
    # sender cannot mark someone else's inbox message
    assert (await c.post(f"/api/inbox/{ref}/read")).status_code == 404
    await c.aclose()
    await arjun.aclose()


async def test_draft_validation(seeded):
    c = await client_for()
    for bad in ({"user_ids": [], "subject": "x", "body": "y"}, {"user_ids": [1], "subject": "", "body": "y"},
                {"user_ids": [1], "subject": "x", "body": ""}):
        assert (await c.post("/api/messages/draft", json=bad)).status_code == 422
    await c.aclose()


async def test_writes_require_csrf(seeded):
    c = await client_for()
    del c.headers["x-csrf-token"]
    assert (await c.post("/api/messages/draft", json={"user_ids": [seeded["arjun_id"]], "subject": "s", "body": "b"})).status_code == 403
    assert (await c.post("/api/inbox/M1/read")).status_code == 403
    assert (await c.post("/api/records/C1/prepare-approval")).status_code == 403
    await c.aclose()


async def test_writes_reject_foreign_origin(seeded):
    c = await client_for()
    c.headers["origin"] = "http://evil.example"
    assert (await c.post("/api/records/C1/prepare-approval")).status_code == 403
    await c.aclose()


async def test_unauthenticated_workspace_endpoints_rejected(seeded):
    import httpx

    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as c:
        for path in ("/api/claims", "/api/bills", "/api/payments", "/api/trips", "/api/priorities", "/api/people", "/api/documents",
                     "/api/budget/lines", "/api/claim-review?ref=C1", "/api/messages/sent"):
            assert (await c.get(path)).status_code == 401, path


# ------------------------------------------------------------------ prepare-approval


async def test_prepare_approval_creates_proposal_without_executing(seeded):
    ref, priya = await new_claim(seeded)
    c = await client_for()
    before = await travel_available(seeded)
    r = await c.post(f"/api/records/{ref}/prepare-approval")
    assert r.status_code == 201
    pid = r.json()["proposal_id"]
    assert await travel_available(seeded) == before
    async with db.session_scope() as s:
        p = await s.get(Proposal, pid)
        assert p.kind == "approve" and p.status == "open"
    j = (await c.get("/api/claim-review", params={"ref": ref})).json()
    assert j["status"] == "submitted" and j["proposal"]["id"] == pid
    await c.aclose()


async def test_prepare_approval_lowercase_ref_normalised(seeded):
    ref, _ = await new_claim(seeded)
    c = await client_for()
    assert (await c.post(f"/api/records/{ref.lower()}/prepare-approval")).status_code == 201
    await c.aclose()


async def test_prepare_approval_employee_forbidden(seeded):
    ref, _ = await new_claim(seeded)
    arjun = await client_for("arjun@purser.demo")
    r = await arjun.post(f"/api/records/{ref}/prepare-approval")
    assert r.status_code in (403, 404)
    await arjun.aclose()


async def test_prepare_approval_unknown_ref(seeded):
    c = await client_for()
    assert (await c.post("/api/records/C9999/prepare-approval")).status_code == 404
    await c.aclose()


async def test_self_approval_refused(seeded):
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, vendor="Taxi Co", total_rupees=700, sha="d" * 64)
    _, out = await propose_and_confirm(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": priya.party_id, "category": "Travel"})
    ref = out.receipt.effects[0]["ref"]
    c = await client_for()
    r = await c.post(f"/api/records/{ref}/prepare-approval")
    assert r.status_code == 409 and r.json()["code"] == "SELF_APPROVAL"
    await c.aclose()


async def test_duplicate_confirm_does_not_double_apply(seeded):
    ref, _ = await new_claim(seeded)
    c = await client_for()
    pid = (await c.post(f"/api/records/{ref}/prepare-approval")).json()["proposal_id"]
    r1 = (await c.post(f"/api/proposals/{pid}/confirm")).json()
    after1 = await travel_available(seeded)
    r2 = (await c.post(f"/api/proposals/{pid}/confirm")).json()
    assert r1["status"] == "executed" and r2["status"] == "replayed"
    assert after1 == 45_200 * R and await travel_available(seeded) == after1
    await c.aclose()


# ------------------------------------------------------------------ agent tool cards


def cards(mc, name="claim_review"):
    return [x for x in mc.ui if x.get("card") == name]


async def test_tool_find_reservations_emits_claim_review(seeded):
    from app.agent.tools import intake as t
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya)
    res, mc = await call(t.find_reservations, priya, document_id=doc, employee_party_id=seeded["arjun_party_id"])
    cs = cards(mc)
    assert len(cs) == 1 and cs[0]["document_id"] == doc and cs[0]["reservation_id"] == seeded["reservation_id"]


async def test_tool_find_reservations_no_card_when_date_outside_trip(seeded):
    from app.agent.tools import intake as t
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya, bdate=date(2026, 12, 20), sha="e" * 64)
    _, mc = await call(t.find_reservations, priya, document_id=doc, employee_party_id=seeded["arjun_party_id"])
    assert cards(mc) == []


async def test_tool_propose_submit_claim_card_only_with_reservation(seeded):
    from app.agent.tools import proposals as t
    priya = await make_actor(seeded)
    doc = await add_inspected_document(priya)
    _, mc = await call(t.propose_submit_claim, priya, document_id=doc, beneficiary_party_id=seeded["arjun_party_id"], category="Travel",
                       reservation_id=seeded["reservation_id"], reservation_treatment="final")
    assert cards(mc) == [{"card": "claim_review", "document_id": doc, "reservation_id": seeded["reservation_id"]}]
    assert len(cards(mc, "proposal")) == 1
    priya2 = await make_actor(seeded)
    doc2 = await add_inspected_document(priya2, vendor="Cafe", total_rupees=300, sha="f" * 64)
    _, mc2 = await call(t.propose_submit_claim, priya2, document_id=doc2, beneficiary_party_id=seeded["arjun_party_id"], category="Travel")
    assert cards(mc2) == []


async def test_tool_propose_approval_card_for_claims_not_bills(seeded):
    from app.agent.tools import proposals as t
    ref, _ = await new_claim(seeded)
    priya = await make_actor(seeded)
    _, mc = await call(t.propose_approval, priya, ref=ref.lower())
    assert cards(mc) == [{"card": "claim_review", "ref": ref}]
    async with db.session_scope() as s:
        from app.models import Bill
        bref = (await s.execute(select(Bill.ref).where(Bill.state == "submitted"))).scalars().first()
    if bref:
        priya3 = await make_actor(seeded)
        _, mcb = await call(t.propose_approval, priya3, ref=bref)
        assert cards(mcb) == []


async def test_tool_get_record_card_variants(seeded):
    from app.agent.tools import finance as t
    ref, _ = await new_claim(seeded)
    priya = await make_actor(seeded)
    _, mc = await call(t.get_record, priya, ref=ref)
    assert cards(mc) == [{"card": "claim_review", "ref": ref}] and cards(mc, "record") == []
    doc = await add_inspected_document(priya, vendor="Cafe", total_rupees=300, sha="9" * 64)
    _, _o = await propose_and_confirm(priya, "submit_claim", {"document_id": doc, "beneficiary_party_id": seeded["arjun_party_id"], "category": "Travel"})
    plain = _o.receipt.effects[0]["ref"]
    priya2 = await make_actor(seeded)
    _, mc2 = await call(t.get_record, priya2, ref=plain)
    assert cards(mc2) == [] and cards(mc2, "record") == [{"card": "record", "ref": plain}]


# ------------------------------------------------------------------ rename fallout


def test_purser_rename_surface():
    from app.agent import purser
    from app.agent.context import PurserContext
    assert callable(purser.build_agent) and PurserContext
    import importlib.util
    assert importlib.util.find_spec("app.agent.munshi") is None
    from pathlib import Path
    assert Path("app/agent/prompts/purser.md").exists() and not Path("app/agent/prompts/munshi.md").exists()


async def test_session_cookie_name_is_purser(seeded):
    import httpx

    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as c:
        r = await c.post("/api/auth/login", json={"email": "priya@purser.demo", "password": "purser-demo"})
    assert "purser_session" in r.headers.get("set-cookie", "")
