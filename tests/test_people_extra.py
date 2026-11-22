"""People-ops coverage (PLAN_v5): leave ledger and decisions, messaging outbox, onboarding, people/inbox API, people tools.

No real email can leave this file: the autouse `mail` fixture disables Gmail settings, replaces _send_smtp with a
recorder and makes smtplib.SMTP_SSL fail loudly."""

import asyncio
import smtplib
import time
from datetime import date

import httpx
import pytest
from sqlalchemy import func, select

from app import db
from app.actor import Actor
from app.agent.tools import people as people_tools
from app.agent.tools import proposals as proposal_tools
from app.config import get_settings
from app.errors import AMBIGUOUS, FORBIDDEN, INVALID_STATE, NOT_FOUND, SELF_APPROVAL, VALIDATION, DomainError
from app.main import app
from app.models import AuditEvent, LeaveMovement, LeaveRequest, Message, OnboardingTask, Party, Proposal, Receipt, User
from app.services import audit, confirmation, messaging, people, proposals
from seed.seed_v1 import seed
from tests.conftest import make_actor
from tests.test_api_intake import ORIGIN, client_for
from tests.test_intake_extra import call
from tests.test_ledger_gates import propose_and_confirm

MON, TUE, WED = "2026-11-30", "2026-12-01", "2026-12-02"
SAT, SUN = "2026-12-05", "2026-12-06"


# ------------------------------------------------------------------ fixtures and helpers


class Mail:
    def __init__(self, mp, orig):
        self._mp, self.real_send, self.sent, self.delay = mp, orig, [], 0.0

    def fake_send(self, to, subject, body):
        if self.delay:
            time.sleep(self.delay)
        self.sent.append({"to": to, "subject": subject, "body": body})
        return f"<fake-{len(self.sent)}@test>"

    def enable(self, *allow):
        base = get_settings()
        patched = base.model_copy(update={"gmail_address": "purser@test.invalid", "gmail_app_password": "not-a-secret",
                                          "email_allowed_recipients": ",".join(allow)})
        self._mp.setattr(messaging, "get_settings", lambda: patched)


@pytest.fixture(autouse=True)
def mail(monkeypatch):
    base = get_settings()
    off = base.model_copy(update={"gmail_address": "", "gmail_app_password": "", "email_allowed_recipients": ""})
    m = Mail(monkeypatch, messaging._send_smtp)
    monkeypatch.setattr(messaging, "get_settings", lambda: off)
    monkeypatch.setattr(messaging, "_send_smtp", m.fake_send)

    def boom(*a, **k):
        raise AssertionError("a test tried to open a real SMTP connection")

    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)
    monkeypatch.setattr(messaging, "dispatch_soon", lambda: None)  # tests call dispatch() explicitly
    return m


async def count(model, *where) -> int:
    async with db.session_scope() as s:
        return (await s.execute(select(func.count()).select_from(model).where(*where))).scalar_one()


async def set_notify(user_id: int, email: str | None):
    async with db.session_scope() as s:
        (await s.get(User, user_id)).notify_email = email


async def bal(user_id: int, ws: int = 1) -> dict:
    async with db.session_scope() as s:
        return await people.balance(s, ws, user_id)


async def conv(actor: Actor) -> Actor:
    """Same user, fresh conversation (a second session)."""
    async with db.session_scope() as s:
        from app.models import Conversation
        c = Conversation(workspace_id=actor.workspace_id, user_id=actor.user_id, channel="text")
        s.add(c)
        await s.flush()
        return Actor(actor.user_id, actor.workspace_id, actor.role, actor.party_id, actor.display_name, c.id)


async def code_of(actor, kind, args) -> str:
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.create(s, actor, kind, args)
    return e.value.code


async def present(actor, kind, args) -> Proposal:
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, kind, args)
        await proposals.mark_presented(s, p.id)
        return p


async def apply(actor, start, end=None, lt="CL", **extra):
    _, out = await propose_and_confirm(actor, "apply_leave", {"leave_type": lt, "start_date": start, "end_date": end or start, **extra})
    return out.receipt.effects[0]["ref"], out


async def add_employee(ids, name, reports_to: int | None, dept="Sales", email=None) -> int:
    async with db.session_scope() as s:
        p = Party(workspace_id=ids["workspace_id"], kind="employee", name=name, normalized_name=name.lower(), aliases=[])
        s.add(p)
        await s.flush()
        u = User(workspace_id=ids["workspace_id"], email=email or f"{name.lower().replace(' ', '.')}@purser.demo", display_name=name, role="employee",
                 password_hash="x", party_id=p.id, department=dept, designation="Exec", reports_to_id=reports_to, status="active")
        s.add(u)
        await s.flush()
        for code, (_, days) in people.LEAVE_TYPES.items():
            await people.post_leave(s, ids["workspace_id"], u.id, code, "granted", days, "annual_grant")
        return u.id


async def assert_leave_conservation(ws=1):
    async with db.session_scope() as s:
        for u in (await s.execute(select(User).where(User.workspace_id == ws))).scalars():
            b = await people.balance(s, ws, u.id)
            for code, v in b.items():
                assert min(v["granted"], v["reserved"], v["used"], v["available"]) >= 0, (u.display_name, code, v)
                held = (await s.execute(select(func.coalesce(func.sum(LeaveRequest.days), 0)).where(
                    LeaveRequest.user_id == u.id, LeaveRequest.leave_type == code, LeaveRequest.state == "submitted"))).scalar_one()
                assert v["reserved"] == held, (u.display_name, code, v, held)
                assert v["available"] == v["granted"] - v["reserved"] - v["used"]


async def messages_for(receipt_id: int) -> list[Message]:
    async with db.session_scope() as s:
        return list((await s.execute(select(Message).where(Message.receipt_id == receipt_id).order_by(Message.id))).scalars())


# ------------------------------------------------------------------ people.py: pure helpers and directory


@pytest.mark.parametrize("start,end,expected", [
    ("2026-11-30", "2026-11-30", 1), ("2026-11-30", "2026-12-04", 5), ("2026-12-04", "2026-12-07", 2),   # Fri..Mon
    ("2026-12-05", "2026-12-06", 0), ("2026-12-05", "2026-12-05", 0), ("2026-11-27", "2026-11-28", 1),
    ("2026-11-30", "2026-12-11", 10), ("2026-12-02", "2026-12-01", 0),
])
def test_working_days(start, end, expected):
    assert people.working_days(date.fromisoformat(start), date.fromisoformat(end)) == expected


async def test_seeded_leave_days_match_working_days(seeded):
    async with db.session_scope() as s:
        for lr in (await s.execute(select(LeaveRequest))).scalars():
            assert lr.days == people.working_days(lr.start_date, lr.end_date), (lr.ref, lr.days)
    assert (await bal(seeded["neha_id"]))["CL"]["reserved"] == 2


async def test_seed_balances_match_spec(seeded):
    ids = seeded
    arjun, neha, priya = await bal(ids["arjun_id"]), await bal(ids["neha_id"]), await bal(ids["priya_id"])
    assert (arjun["CL"]["granted"], arjun["CL"]["used"], arjun["CL"]["available"]) == (12, 3, 9)
    assert (arjun["SL"]["available"], arjun["EL"]["available"]) == (8, 15)
    assert (neha["SL"]["used"], neha["SL"]["available"], neha["CL"]["reserved"], neha["CL"]["available"]) == (1, 7, 2, 10)
    assert (priya["CL"]["available"], priya["EL"]["granted"]) == (12, 15)
    assert await count(LeaveRequest) == 1 and await count(__import__("app.models", fromlist=["Policy"]).Policy) == 6
    await assert_leave_conservation()


async def test_find_and_resolve_people(seeded):
    ids = seeded
    priya = await make_actor(ids)
    async with db.session_scope() as s:
        assert [u.display_name for u in await people.find_people(s, priya, "arjun")] == ["Arjun Mehta"]
        assert [u.display_name for u in await people.find_people(s, priya, "Arjun Meta")] == ["Arjun Mehta"]       # speech-to-text typo
        assert await people.find_people(s, priya, "Zzzzz Qqqq") == []
        sales = {u.display_name for u in await people.find_people(s, priya, department="SALES")}
        assert {"Arjun Mehta", "Neha Iyer"} <= sales
        assert (await people.resolve_person(s, priya, "Neha")).display_name == "Neha Iyer"
        with pytest.raises(DomainError) as e:
            await people.resolve_person(s, priya, "Rohit Verma")
        assert e.value.code == NOT_FOUND
    kapoor = await add_employee(ids, "Neha Kapoor", ids["priya_id"])
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await people.resolve_person(s, priya, "Neha")
        assert e.value.code == AMBIGUOUS and {c["user_id"] for c in e.value.details["candidates"]} == {ids["neha_id"], kapoor}
        assert (await people.resolve_person(s, priya, "Neha Kapoor")).id == kapoor      # a full name is not ambiguous


async def test_directory_is_workspace_scoped(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    priya, other_priya = await make_actor(seeded), await make_actor(other)
    async with db.session_scope() as s:
        mine = await people.find_people(s, priya, "Arjun")
        theirs = await people.find_people(s, other_priya, "Arjun")
        assert {u.workspace_id for u in mine} == {seeded["workspace_id"]} and {u.workspace_id for u in theirs} == {other["workspace_id"]}
        with pytest.raises(DomainError) as e:
            await people.user(s, priya, other["arjun_id"])
        assert e.value.code == NOT_FOUND


async def test_search_policies(seeded):
    ws = seeded["workspace_id"]
    async with db.session_scope() as s:
        leave = await people.search_policies(s, ws, "how many casual leave days do I get")
        hotel = await people.search_policies(s, ws, "hotel reimbursement limit")
        hours = await people.search_policies(s, ws, "what are the office working hours")
        nothing = await people.search_policies(s, ws, "quantum chromodynamics")
        short = await people.search_policies(s, ws, "is it ok")
    assert leave[0].code == "HR-3.1" and len(leave) <= 3 and all(p.code.startswith("HR-3") for p in leave[:2])
    assert hotel[0].code == "FIN-2.1" and hours[0].code == "HR-5.1"
    assert nothing == [] and short == []


async def test_search_policies_is_workspace_scoped(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    async with db.session_scope() as s:
        found = await people.search_policies(s, other["workspace_id"], "casual leave")
    assert found and {p.workspace_id for p in found} == {other["workspace_id"]}


# ------------------------------------------------------------------ leave visibility and listing


async def test_leave_by_ref_visibility(seeded):
    ids = seeded
    priya, arjun, neha = await make_actor(ids), await make_actor(ids, "arjun"), await make_actor(ids, "neha")
    ref = ids["neha_leave_ref"]
    async with db.session_scope() as s:
        assert (await people.leave_by_ref(s, priya, ref)).ref == ref                       # HR (also her manager)
        assert (await people.leave_by_ref(s, neha, ref.lower())).ref == ref                # owner, case-insensitive
        for stranger in (arjun,):
            with pytest.raises(DomainError) as e:
                await people.leave_by_ref(s, stranger, ref)
            assert e.value.code == NOT_FOUND                                              # hidden, not FORBIDDEN
        with pytest.raises(DomainError):
            await people.leave_by_ref(s, priya, "L9999")
    dev = await add_employee(ids, "Dev Rao", ids["arjun_id"])
    async with db.session_scope() as s:
        d = await s.get(User, dev)
        lr = LeaveRequest(workspace_id=1, ref="LX1", user_id=dev, submitted_by=dev, leave_type="CL", start_date=date(2026, 12, 7),
                          end_date=date(2026, 12, 7), days=1)
        s.add(lr)
        await s.flush()
        assert d.reports_to_id == ids["arjun_id"]
        assert (await people.leave_by_ref(s, arjun, "LX1")).user_id == dev                  # the manager sees a report's leave
        with pytest.raises(DomainError):
            await people.leave_by_ref(s, neha, "LX1")


async def test_leave_request_scopes(seeded):
    ids = seeded
    priya, arjun, neha = await make_actor(ids), await make_actor(ids, "arjun"), await make_actor(ids, "neha")
    own, _ = await apply(priya, MON)
    arj, _ = await apply(arjun, TUE)

    async def refs(actor, scope):
        async with db.session_scope() as s:
            return sorted(lr.ref for lr, _ in await people.leave_requests(s, actor, scope))

    assert await refs(priya, "mine") == [own]
    assert await refs(priya, "awaiting_my_decision") == sorted([ids["neha_leave_ref"], arj])   # never her own request
    assert await refs(priya, "team") == sorted([own, arj, ids["neha_leave_ref"]])
    assert await refs(arjun, "mine") == [arj] and await refs(arjun, "awaiting_my_decision") == [] and await refs(arjun, "team") == [arj]
    assert await refs(neha, "team") == [ids["neha_leave_ref"]]
    dev = await add_employee(ids, "Dev Rao", ids["arjun_id"])
    async with db.session_scope() as s:
        s.add(LeaveRequest(workspace_id=1, ref="LX2", user_id=dev, submitted_by=dev, leave_type="CL", start_date=date(2026, 12, 7),
                           end_date=date(2026, 12, 7), days=1))
    assert await refs(arjun, "awaiting_my_decision") == ["LX2"] and await refs(arjun, "team") == sorted([arj, "LX2"])


# ------------------------------------------------------------------ ApplyLeave


async def test_apply_leave_reserves_days_and_previews_balance(seeded):
    ids, arjun = seeded, await make_actor(seeded, "arjun")
    async with db.session_scope() as s:
        p = await proposals.create(s, arjun, "apply_leave", {"leave_type": "cl", "start_date": MON, "end_date": WED, "reason": "Family trip"})
    assert "3 day(s) of casual leave" in p.preview["lines"][0] and "Family trip" in p.preview["lines"][0]
    assert "available after approval: 6 of 12" in p.preview["lines"][1]
    assert (await bal(ids["arjun_id"]))["CL"]["reserved"] == 0     # planning writes nothing
    ref, out = await apply(arjun, MON, WED, lt="cl", reason="Family trip")
    b = (await bal(ids["arjun_id"]))["CL"]
    assert (b["reserved"], b["used"], b["available"]) == (3, 3, 6)
    async with db.session_scope() as s:
        lr = (await s.execute(select(LeaveRequest).where(LeaveRequest.ref == ref))).scalar_one()
        assert (lr.leave_type, lr.days, lr.state, lr.user_id, lr.submitted_by, lr.reason) == ("CL", 3, "submitted", ids["arjun_id"], ids["arjun_id"], "Family trip")
        mv = (await s.execute(select(LeaveMovement).where(LeaveMovement.source_id == lr.id))).scalar_one()
        assert (mv.bucket, mv.days, mv.receipt_id) == ("reserved", 3, out.receipt.id)
        audit_rows = (await s.execute(select(AuditEvent).where(AuditEvent.receipt_id == out.receipt.id))).scalars().all()
        assert {a.action for a in audit_rows} == {"proposal.confirmed", "leave.submitted"}
    await assert_leave_conservation()


async def test_apply_leave_rejections(seeded):
    ids, arjun = seeded, await make_actor(seeded, "arjun")
    before = await count(LeaveRequest)
    assert await code_of(arjun, "apply_leave", {"leave_type": "CL", "start_date": SAT, "end_date": SUN}) == VALIDATION       # weekend only
    assert await code_of(arjun, "apply_leave", {"leave_type": "CL", "start_date": SAT}) == VALIDATION
    assert await code_of(arjun, "apply_leave", {"leave_type": "XX", "start_date": MON}) == VALIDATION
    assert await code_of(arjun, "apply_leave", {"leave_type": "CL", "start_date": "next monday"}) == VALIDATION
    assert await code_of(arjun, "apply_leave", {"leave_type": "CL", "start_date": WED, "end_date": MON}) == VALIDATION
    assert await count(LeaveRequest) == before and (await bal(ids["arjun_id"]))["CL"]["reserved"] == 0


async def test_insufficient_balance_boundary(seeded):
    ids, arjun = seeded, await make_actor(seeded, "arjun")
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.create(s, arjun, "apply_leave", {"leave_type": "CL", "start_date": MON, "end_date": "2026-12-11"})  # 10 days, 9 left
    assert e.value.code == VALIDATION and e.value.details["available"] == 9
    await apply(arjun, MON, "2026-12-10")                                   # exactly 9 working days: allowed
    b = (await bal(ids["arjun_id"]))["CL"]
    assert (b["available"], b["reserved"]) == (0, 9)
    assert await code_of(arjun, "apply_leave", {"leave_type": "CL", "start_date": "2026-12-14"}) == VALIDATION
    assert (await bal(ids["arjun_id"]))["SL"]["available"] == 8            # other types are untouched
    await assert_leave_conservation()


async def test_overlap_rules_and_reapply_after_rejection(seeded):
    ids = seeded
    priya, neha = await make_actor(ids), await make_actor(ids, "neha")
    assert await code_of(neha, "apply_leave", {"leave_type": "SL", "start_date": "2026-11-27"}) == INVALID_STATE   # clashes with pending L1
    assert await code_of(neha, "apply_leave", {"leave_type": "CL", "start_date": "2026-11-26", "end_date": "2026-11-27"}) == INVALID_STATE
    ref, _ = await apply(neha, MON)                                                                                 # adjacent working day: fine
    assert await code_of(neha, "apply_leave", {"leave_type": "CL", "start_date": MON, "end_date": TUE}) == INVALID_STATE
    await propose_and_confirm(priya, "reject_leave", {"ref": ref})
    again, _ = await apply(neha, MON, TUE)                                                                          # rejected leave no longer blocks
    assert again != ref
    await propose_and_confirm(priya, "approve", {"ref": again})
    assert await code_of(neha, "apply_leave", {"leave_type": "CL", "start_date": TUE}) == INVALID_STATE            # approved leave blocks too


async def test_apply_for_someone_else_rights(seeded):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    assert await code_of(arjun, "apply_leave", {"leave_type": "CL", "start_date": MON, "user_id": ids["neha_id"]}) == FORBIDDEN
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    assert await code_of(priya, "apply_leave", {"leave_type": "CL", "start_date": MON, "user_id": other["arjun_id"]}) == NOT_FOUND
    ref, _ = await apply(priya, MON, user_id=ids["arjun_id"])                                # HR on Arjun's behalf
    async with db.session_scope() as s:
        lr = (await s.execute(select(LeaveRequest).where(LeaveRequest.ref == ref))).scalar_one()
        assert (lr.user_id, lr.submitted_by) == (ids["arjun_id"], ids["priya_id"])
    assert (await bal(ids["arjun_id"]))["CL"]["reserved"] == 1 and (await bal(ids["priya_id"]))["CL"]["reserved"] == 0


async def test_two_open_applications_for_same_dates_reserve_once(seeded):
    ids = seeded
    a, b = await make_actor(ids, "arjun"), await conv(await make_actor(ids, "arjun"))
    args = {"leave_type": "CL", "start_date": MON, "end_date": TUE}
    p1, p2 = await present(a, "apply_leave", args), await present(b, "apply_leave", args)
    async with db.session_scope() as s:
        assert (await proposals.confirm(s, a, p1.id, via="button")).status == "executed"
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.confirm(s, b, p2.id, via="button")
    assert e.value.code == INVALID_STATE
    assert (await bal(ids["arjun_id"]))["CL"]["reserved"] == 2 and await count(LeaveRequest, LeaveRequest.user_id == ids["arjun_id"]) == 1
    await assert_leave_conservation()


# ------------------------------------------------------------------ DecideLeave


async def test_approve_moves_reserved_to_used_and_notifies(seeded):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    ref, _ = await apply(arjun, MON, WED)
    p, out = await propose_and_confirm(priya, "approve", {"ref": ref})
    b = (await bal(ids["arjun_id"]))["CL"]
    assert (b["reserved"], b["used"], b["available"]) == (0, 6, 6)
    async with db.session_scope() as s:
        lr = (await s.execute(select(LeaveRequest).where(LeaveRequest.ref == ref))).scalar_one()
        assert (lr.state, lr.approver_id, lr.version) == ("approved", ids["priya_id"], 2)
        kinds = {(m.bucket, m.days, m.kind) for m in (await s.execute(select(LeaveMovement).where(LeaveMovement.source_id == lr.id))).scalars()}
        assert kinds == {("reserved", 3, "leave_requested"), ("reserved", -3, "leave_approved"), ("used", 3, "leave_approved")}
    msgs = await messages_for(out.receipt.id)
    inbox = [m for m in msgs if m.channel == "inbox"]
    assert len(inbox) == 1 and inbox[0].recipient_user_id == ids["arjun_id"] and inbox[0].kind == "leave_decision" and inbox[0].status == "delivered"
    assert inbox[0].subject == f"Leave {ref} approved" and "approved by Priya Sharma" in inbox[0].body and inbox[0].sender_id == ids["priya_id"]
    assert inbox[0].ref == f"M{inbox[0].id}" and inbox[0].read_at is None
    assert {a for a in (await _audit_actions(out.receipt.id))} == {"proposal.confirmed", "leave.approved"}
    await assert_leave_conservation()


async def _audit_actions(receipt_id):
    async with db.session_scope() as s:
        return {a.action for a in (await s.execute(select(AuditEvent).where(AuditEvent.receipt_id == receipt_id))).scalars()}


async def test_reject_releases_reserved_days_and_records_note(seeded):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    ref, _ = await apply(arjun, MON, WED)
    async with db.session_scope() as s:
        pv = await proposals.create(s, priya, "reject_leave", {"ref": ref, "note": "Release freeze"})
    assert "Reason given: Release freeze" in pv.preview["lines"][-1]
    _, out = await propose_and_confirm(priya, "reject_leave", {"ref": ref, "note": "Release freeze"})
    b = (await bal(ids["arjun_id"]))["CL"]
    assert (b["reserved"], b["used"], b["available"]) == (0, 3, 9)       # back to the pre-request position
    async with db.session_scope() as s:
        lr = (await s.execute(select(LeaveRequest).where(LeaveRequest.ref == ref))).scalar_one()
        assert (lr.state, lr.decision_note) == ("rejected", "Release freeze")
    inbox = next(m for m in await messages_for(out.receipt.id) if m.channel == "inbox")
    assert inbox.subject == f"Leave {ref} not approved" and "Note: Release freeze" in inbox.body
    assert "leave.rejected" in await _audit_actions(out.receipt.id)
    assert await code_of(priya, "approve", {"ref": ref}) == INVALID_STATE   # a decided request cannot be decided again
    await assert_leave_conservation()


async def test_decision_rights_self_manager_hr_unrelated(seeded):
    ids = seeded
    priya, arjun, neha = await make_actor(ids), await make_actor(ids, "arjun"), await make_actor(ids, "neha")
    assert await code_of(arjun, "approve", {"ref": ids["neha_leave_ref"]}) == NOT_FOUND          # unrelated employee: not even visible
    assert await code_of(arjun, "reject_leave", {"ref": ids["neha_leave_ref"]}) == NOT_FOUND
    assert await code_of(neha, "approve", {"ref": ids["neha_leave_ref"]}) == SELF_APPROVAL       # owner cannot self-decide
    assert await code_of(neha, "reject_leave", {"ref": ids["neha_leave_ref"]}) == SELF_APPROVAL
    mine, _ = await apply(priya, MON)
    assert await code_of(priya, "approve", {"ref": mine}) == SELF_APPROVAL                      # HR cannot approve own leave either
    dev = await add_employee(ids, "Dev Rao", ids["arjun_id"])
    devactor = Actor(dev, 1, "employee", None, "Dev Rao", None)
    ref, _ = await apply(devactor, TUE)
    assert await code_of(neha, "approve", {"ref": ref}) == NOT_FOUND                            # peers cannot see it
    _, out = await propose_and_confirm(arjun, "approve", {"ref": ref})                          # line manager (an employee role) can decide
    assert out.status == "executed" and (await bal(dev))["CL"]["used"] == 1
    ref2, _ = await apply(devactor, WED)
    _, out = await propose_and_confirm(priya, "reject_leave", {"ref": ref2})                    # HR can decide for anyone
    assert out.status == "executed"
    assert await code_of(priya, "approve", {"ref": "L99999"}) == NOT_FOUND


async def test_manager_who_is_not_hr_cannot_decide_non_reports(seeded):
    ids = seeded
    arjun = await make_actor(ids, "arjun")
    assert await code_of(arjun, "approve", {"ref": ids["neha_leave_ref"]}) == NOT_FOUND


async def test_double_decision_from_two_sessions_applies_once(seeded):
    ids = seeded
    priya = await make_actor(ids)
    priya2 = await conv(priya)
    a = await present(priya, "approve", {"ref": ids["neha_leave_ref"]})
    b = await present(priya2, "reject_leave", {"ref": ids["neha_leave_ref"]})
    async with db.session_scope() as s:
        assert (await proposals.confirm(s, priya, a.id, via="button")).status == "executed"
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.confirm(s, priya2, b.id, via="button")
    assert e.value.code == INVALID_STATE
    n = (await bal(ids["neha_id"]))["CL"]
    assert n["reserved"] == 0 and n["used"] == 2 and n["available"] == 10     # reservation released exactly once
    assert await count(Message, Message.kind == "leave_decision", Message.channel == "inbox") == 1
    await assert_leave_conservation()


async def test_leave_decision_goes_stale_when_request_changes_after_preview(seeded):
    ids, priya = seeded, await make_actor(seeded)
    p = await present(priya, "approve", {"ref": ids["neha_leave_ref"]})
    async with db.session_scope() as s:
        (await people.leave_by_ref(s, priya, ids["neha_leave_ref"])).version += 1
    async with db.session_scope() as s:
        out = await proposals.confirm(s, priya, p.id, via="button")
    assert out.status == "stale" and out.new_proposal is not None and await count(Message) == 1   # only the seeded M0
    assert (await bal(ids["neha_id"]))["CL"]["reserved"] == 2


async def test_kind_reject_is_not_a_valid_action_name(seeded):
    priya = await make_actor(seeded)
    with pytest.raises(KeyError):
        async with db.session_scope() as s:
            await proposals.create(s, priya, "reject", {"ref": "L1"})


# ------------------------------------------------------------------ email policy


@pytest.mark.parametrize("notify,enabled,allow,expect", [
    (None, False, [], (None, "no_email")), ("   ", True, ["a@x.com"], (None, "no_email")),
    ("a@x.com", False, ["a@x.com"], ("a@x.com", "email_not_configured")),
    ("a@x.com", True, ["b@x.com"], ("a@x.com", "not_on_allowlist")),
    ("A@X.com", True, ["a@x.com"], ("a@x.com", "deliverable")),
    ("  a@x.com ", True, ["A@X.COM"], ("a@x.com", "deliverable")),
])
async def test_email_plan(seeded, mail, notify, enabled, allow, expect):
    if enabled:
        mail.enable(*allow)
    assert messaging.email_plan(User(notify_email=notify)) == expect


async def test_decision_email_states_inbox_always_delivered(seeded, mail):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    rows = {}
    scenarios = [("none", None, False, []), ("unconfigured", "arjun@gmail.test", False, ["arjun@gmail.test"]),
                 ("off_list", "arjun@gmail.test", True, ["someone.else@gmail.test"]), ("ok", "arjun@gmail.test", True, ["arjun@gmail.test"])]
    for i, (name, notify, enabled, allow) in enumerate(scenarios):
        await set_notify(ids["arjun_id"], notify)
        if enabled:
            mail.enable(*allow)
        ref, _ = await apply(arjun, f"2026-12-{7 + i:02d}")
        _, out = await propose_and_confirm(priya, "approve", {"ref": ref})
        rows[name] = await messages_for(out.receipt.id)
    for name, msgs in rows.items():
        assert [m.channel for m in msgs] == ["inbox", "email"], name
        assert msgs[0].status == "delivered" and msgs[0].email_to is None
    assert [(m[1].status, m[1].status_detail, m[1].email_to) for m in (rows["none"], rows["unconfigured"], rows["off_list"])] == [
        ("skipped", "no_email", None), ("skipped", "email_not_configured", "arjun@gmail.test"), ("skipped", "not_on_allowlist", "arjun@gmail.test")]
    assert (rows["ok"][1].status, rows["ok"][1].status_detail, rows["ok"][1].email_to) == ("queued", None, "arjun@gmail.test")
    assert mail.sent == []                      # nothing is sent by the confirm transaction itself


async def test_dispatch_sends_only_after_commit_once_and_records_provider_id(seeded, mail):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    await set_notify(ids["arjun_id"], "arjun@gmail.test")
    mail.enable("arjun@gmail.test")
    ref, _ = await apply(arjun, MON)
    p, out = await propose_and_confirm(priya, "approve", {"ref": ref})
    assert mail.sent == []
    assert await messaging.dispatch() == 1
    assert [(m["to"], m["subject"]) for m in mail.sent] == [("arjun@gmail.test", f"Leave {ref} approved")]
    email = next(m for m in await messages_for(out.receipt.id) if m.channel == "email")
    assert (email.status, email.provider_id, email.status_detail) == ("sent", "<fake-1@test>", None) and email.sent_at is not None
    async with db.session_scope() as s:
        again = await proposals.confirm(s, priya, p.id, via="button")      # replay
    assert again.status == "replayed" and again.receipt.id == out.receipt.id
    assert await messaging.dispatch() == 0 and len(mail.sent) == 1
    assert len(await messages_for(out.receipt.id)) == 2                    # no duplicate inbox/email rows


async def test_rolled_back_confirm_composes_and_sends_nothing(seeded, mail, monkeypatch):
    ids = seeded
    priya = await make_actor(ids)
    await set_notify(ids["neha_id"], "neha@gmail.test")
    mail.enable("neha@gmail.test")
    p = await present(priya, "approve", {"ref": ids["neha_leave_ref"]})

    async def boom(*a, **k):
        raise RuntimeError("injected failure after compose")

    monkeypatch.setattr(audit, "record", boom)
    with pytest.raises(RuntimeError):
        async with db.session_scope() as s:
            await proposals.confirm(s, priya, p.id, via="button")
    monkeypatch.undo()
    assert await count(Message) == 1 and await count(Receipt) == 0         # only the seeded M0; no outbox row survived
    assert await messaging.dispatch() == 0 and mail.sent == []
    n = (await bal(ids["neha_id"]))["CL"]
    assert (n["reserved"], n["used"]) == (2, 0)
    async with db.session_scope() as s:
        assert (await s.get(Proposal, p.id)).status == "open"
        assert (await people.leave_by_ref(s, priya, ids["neha_leave_ref"])).state == "submitted"


async def test_dispatch_failure_is_recorded_and_not_retried(seeded, mail, monkeypatch):
    ids = seeded
    await set_notify(ids["arjun_id"], "arjun@gmail.test")
    mail.enable("arjun@gmail.test")
    priya = await make_actor(ids)
    _, out = await propose_and_confirm(priya, "send_message", {"audience": "person", "user_ids": [ids["arjun_id"]], "subject": "Hi",
                                                              "body": "Hello Arjun", "channels": ["inbox", "email"]})

    def refuse(to, subject, body):
        raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr(messaging, "_send_smtp", refuse)
    assert await messaging.dispatch() == 0
    email = next(m for m in await messages_for(out.receipt.id) if m.channel == "email")
    assert email.status == "failed" and email.status_detail.startswith("SMTPAuthenticationError") and email.provider_id is None
    monkeypatch.setattr(messaging, "_send_smtp", mail.fake_send)
    assert await messaging.dispatch() == 0 and mail.sent == []             # unknown acceptance is never blindly retried
    assert next(m for m in await messages_for(out.receipt.id) if m.channel == "inbox").status == "delivered"


async def test_concurrent_dispatchers_never_double_send(seeded, mail):
    ids = seeded
    for uid, addr in ((ids["arjun_id"], "arjun@gmail.test"), (ids["neha_id"], "neha@gmail.test")):
        await set_notify(uid, addr)
    mail.enable("arjun@gmail.test", "neha@gmail.test")
    mail.delay = 0.05
    priya = await make_actor(ids)
    await propose_and_confirm(priya, "send_message", {"audience": "all", "subject": "Hello", "body": "Office closed Friday", "channels": ["email"]})
    assert await count(Message, Message.status == "queued") == 2
    a, b = await asyncio.gather(messaging.dispatch(), messaging.dispatch())
    assert a + b == 2 and sorted(m["to"] for m in mail.sent) == ["arjun@gmail.test", "neha@gmail.test"]
    assert await count(Message, Message.status == "sent") == 2


# ------------------------------------------------------------------ _send_smtp message building (smtplib faked)


class FakeSMTP:
    instances: list = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.sent, self.creds = host, port, [], None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, user, pw):
        self.creds = (user, pw)

    def send_message(self, msg):
        self.sent.append(msg)


@pytest.fixture
def smtp(monkeypatch, mail):
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    mail.enable("a@x.com")
    return mail.real_send


def test_send_smtp_builds_expected_message(smtp):
    mid = smtp("arjun@gmail.test", "Leave L2 approved", "Hi Arjun")
    srv = FakeSMTP.instances[0]
    msg = srv.sent[0]
    assert (srv.host, srv.port, srv.creds) == ("smtp.gmail.com", 465, ("purser@test.invalid", "not-a-secret"))
    assert msg["To"] == "arjun@gmail.test" and msg["From"] == "Purser <purser@test.invalid>" and msg["Subject"] == "Leave L2 approved"
    assert mid == msg["Message-ID"] and mid.startswith("<") and msg.get_content().strip() == "Hi Arjun"   # body sent as-is, no footer


def test_send_smtp_never_allows_header_injection(smtp):
    try:
        smtp("a@x.com", "Hello\r\nBcc: evil@x.com", "body")
    except ValueError:
        return  # refused outright is acceptable
    assert FakeSMTP.instances[0].sent[0]["Bcc"] is None


def test_multiline_default_subject_can_be_emailed(smtp):
    body = "Office closed on Friday.\nPlease plan your work accordingly."
    smtp("a@x.com", body[:60], body)
    sent = FakeSMTP.instances[0].sent
    assert sent and "\n" not in str(sent[0]["Subject"]) and "\r" not in str(sent[0]["Subject"])
    assert "Office closed on Friday." in str(sent[0]["Subject"])


async def test_multiline_announcement_without_subject_keeps_inbox_copy_and_defaults_subject(seeded):
    priya = await make_actor(seeded)
    body = "Office closed on Friday.\nPlease plan accordingly."
    _, out = await propose_and_confirm(priya, "send_message", {"audience": "all", "body": body})
    inbox = [m for m in await messages_for(out.receipt.id) if m.channel == "inbox"]
    assert len(inbox) == 2 and {m.subject for m in inbox} == {body[:60]}


# ------------------------------------------------------------------ SendMessage


async def test_message_audience_rights(seeded):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    for args in ({"audience": "all", "body": "x"}, {"audience": "department", "department": "Sales", "body": "x"}):
        assert await code_of(arjun, "send_message", args) == FORBIDDEN
    assert await count(Message) == 1
    assert await code_of(priya, "send_message", {"audience": "department", "department": "Nowhere", "body": "x"}) == NOT_FOUND
    _, out = await propose_and_confirm(arjun, "send_message", {"audience": "person", "user_ids": [ids["neha_id"]], "body": "Lunch?"})
    assert out.receipt.effects[0]["inbox"] == 1 and out.status == "executed"


async def test_message_recipient_scoping_and_kinds(seeded):
    ids = seeded
    priya = await make_actor(ids)
    _, one = await propose_and_confirm(priya, "send_message", {"audience": "person", "user_ids": [ids["arjun_id"]], "subject": "Hi", "body": "Hello"})
    _, dept = await propose_and_confirm(priya, "send_message", {"audience": "department", "department": "sales", "subject": "Sales", "body": "Standup 10am"})
    _, everyone = await propose_and_confirm(priya, "send_message", {"audience": "all", "subject": "All", "body": "Holiday"})
    one_m, dept_m, all_m = [await messages_for(o.receipt.id) for o in (one, dept, everyone)]
    assert [(m.recipient_user_id, m.kind) for m in one_m] == [(ids["arjun_id"], "message")]
    assert sorted(m.recipient_user_id for m in dept_m) == sorted([ids["arjun_id"], ids["neha_id"]]) and {m.kind for m in dept_m} == {"announcement"}
    assert sorted(m.recipient_user_id for m in all_m) == sorted([ids["arjun_id"], ids["neha_id"]])    # sender excluded
    assert all(m.sender_id == ids["priya_id"] and m.status == "delivered" for m in one_m + dept_m + all_m)
    assert len({m.ref for m in one_m + dept_m + all_m}) == 5 and all(m.ref == f"M{m.id}" for m in all_m)
    assert len({m.batch_id for m in all_m}) == 1 and all_m[0].batch_id != dept_m[0].batch_id


@pytest.mark.parametrize("args,code", [
    ({"audience": "person", "user_ids": [2], "body": ""}, VALIDATION), ({"audience": "person", "user_ids": [2], "body": "   \n "}, VALIDATION),
    ({"audience": "person", "user_ids": [], "body": "hi"}, VALIDATION), ({"audience": "person", "body": "hi"}, VALIDATION),
    ({"audience": "person", "user_ids": [999999], "body": "hi"}, NOT_FOUND),
])
async def test_message_validation(seeded, args, code):
    priya = await make_actor(seeded)
    assert await code_of(priya, "send_message", args) == code
    assert await count(Message) == 1


async def test_message_cannot_reach_other_workspace(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    priya = await make_actor(seeded)
    assert await code_of(priya, "send_message", {"audience": "person", "user_ids": [other["arjun_id"]], "body": "hi"}) == NOT_FOUND
    _, out = await propose_and_confirm(priya, "send_message", {"audience": "all", "body": "hello team"})
    assert {m.workspace_id for m in await messages_for(out.receipt.id)} == {seeded["workspace_id"]}


async def test_message_channels_and_preview(seeded, mail):
    ids, priya = seeded, await make_actor(seeded)
    await set_notify(ids["arjun_id"], "arjun@gmail.test")
    mail.enable("arjun@gmail.test")
    async with db.session_scope() as s:
        p = await proposals.create(s, priya, "send_message", {"audience": "all", "subject": "Close", "body": "Office closed Friday",
                                                              "channels": ["inbox", "email", "sms"]})
    head = p.preview["lines"][0]
    assert head.startswith("To: ") and head.endswith("(2 people).") and "Arjun Mehta" in head and "Neha Iyer" in head
    assert "Message: Office closed Friday" in p.preview["lines"] and "Email: 1 will be emailed; 1 get the inbox copy only" in " ".join(p.preview["lines"])
    lines = p.preview["lines"]
    ci = next(i for i, ln in enumerate(lines) if ln.startswith("Channels: "))
    assert lines[ci] == "Channels: Purser inbox + email."          # 'sms' silently dropped
    assert lines[ci + 1].startswith("Email signature:")
    _, out = await propose_and_confirm(priya, "send_message", {"audience": "all", "subject": "Close", "body": "Office closed Friday",
                                                              "channels": ["inbox", "email", "sms"]})
    assert out.receipt.effects[0]["inbox"] == 2 and out.receipt.effects[0]["email_queued"] == 1 and out.receipt.effects[0]["email_skipped"] == 1
    _, only_sms = await propose_and_confirm(priya, "send_message", {"audience": "person", "user_ids": [ids["neha_id"]], "body": "x", "channels": ["sms"]})
    assert [m.channel for m in await messages_for(only_sms.receipt.id)] == ["inbox"]      # falls back to inbox
    assert "announcement.sent" in await _audit_actions(out.receipt.id)


async def test_message_replay_creates_no_duplicates_and_no_second_email(seeded, mail):
    ids, priya = seeded, await make_actor(seeded)
    await set_notify(ids["arjun_id"], "arjun@gmail.test")
    mail.enable("arjun@gmail.test")
    p, out = await propose_and_confirm(priya, "send_message", {"audience": "person", "user_ids": [ids["arjun_id"]], "subject": "Hi",
                                                              "body": "Hello", "channels": ["inbox", "email"]})
    await messaging.dispatch()
    for _ in range(2):
        async with db.session_scope() as s:
            r = await proposals.confirm(s, priya, p.id, via="voice")
        assert r.status == "replayed"
        await messaging.dispatch()
    assert len(await messages_for(out.receipt.id)) == 2 and len(mail.sent) == 1


async def test_overlong_subject_is_handled(seeded):
    priya = await make_actor(seeded)
    before = await count(Message)
    assert await code_of(priya, "send_message", {"audience": "all", "subject": "S" * 250, "body": "hello"}) == VALIDATION
    assert await count(Message) == before


# ------------------------------------------------------------------ onboarding


ONBOARD = {"name": "Neha Kapoor", "designation": "Sales Executive", "department": "Sales", "start_date": "2026-12-01"}


async def test_onboarding_creates_everything_in_one_transaction(seeded):
    ids, priya = seeded, await make_actor(seeded)
    args = {**ONBOARD, "manager_user_id": ids["priya_id"]}
    users_before, parties_before = await count(User), await count(Party)
    async with db.session_scope() as s:
        pv = await proposals.create(s, priya, "onboard_employee", args)
    assert any("neha.kapoor@purser.demo" in ln and "Sales" in ln for ln in pv.preview["lines"])
    assert any("12 CL" in ln and "8 SL" in ln and "15 EL" in ln for ln in pv.preview["lines"])
    assert any("Reports to Priya Sharma" in ln for ln in pv.preview["lines"]) and any("5 tasks" in ln for ln in pv.preview["lines"])
    assert (await count(User), await count(Party)) == (users_before, parties_before)     # planning creates nothing
    p, out = await propose_and_confirm(priya, "onboard_employee", args)
    uid = out.receipt.effects[0]["user_id"]
    async with db.session_scope() as s:
        u = await s.get(User, uid)
        party = await s.get(Party, u.party_id)
        assert (u.email, u.display_name, u.role, u.status, u.department, u.designation, u.reports_to_id, u.start_date) == (
            "neha.kapoor@purser.demo", "Neha Kapoor", "employee", "invited", "Sales", "Sales Executive", ids["priya_id"], date(2026, 12, 1))
        assert (party.kind, party.workspace_id, party.name) == ("employee", 1, "Neha Kapoor") and not u.password_hash.startswith("munshi")
        tasks = (await s.execute(select(OnboardingTask).where(OnboardingTask.user_id == uid).order_by(OnboardingTask.id))).scalars().all()
        assert len(tasks) == 5 and [t.status for t in tasks].count("done") == 1 and tasks[0].status == "done" and tasks[0].done_by == ids["priya_id"]
        assert {t.owner for t in tasks} == {"hr", "it", "employee", "manager"} and tasks[1].due_date == date(2026, 11, 29)
        grants = {(m.leave_type, m.bucket, m.days, m.receipt_id) for m in (await s.execute(select(LeaveMovement).where(LeaveMovement.user_id == uid))).scalars()}
        assert grants == {("CL", "granted", 12, out.receipt.id), ("SL", "granted", 8, out.receipt.id), ("EL", "granted", 15, out.receipt.id)}
    msgs = await messages_for(out.receipt.id)
    assert [(m.channel, m.kind, m.recipient_user_id, m.status) for m in msgs][0] == ("inbox", "welcome", uid, "delivered")
    assert msgs[1].channel == "email" and msgs[1].status == "skipped" and msgs[1].status_detail == "no_email"
    assert msgs[0].body.startswith("Dear Neha,\n\nWelcome to the team! You join as Sales Executive in Sales on ") and "Welcome to the team, Neha!" not in msgs[0].body
    assert "reporting to Priya Sharma" in msgs[0].body
    assert "employee.onboarded" in await _audit_actions(out.receipt.id)
    assert (await bal(uid))["CL"]["available"] == 12 and (await bal(uid))["EL"]["available"] == 15
    await assert_leave_conservation()


async def test_onboarding_replay_creates_one_user(seeded):
    priya = await make_actor(seeded)
    p, out = await propose_and_confirm(priya, "onboard_employee", ONBOARD)
    users = await count(User)
    async with db.session_scope() as s:
        assert (await proposals.confirm(s, priya, p.id, via="button")).status == "replayed"
    assert await count(User) == users and await count(OnboardingTask) == 5 and len(await messages_for(out.receipt.id)) == 2


async def test_onboarding_rejects_duplicates_and_bad_input(seeded):
    priya = await make_actor(seeded)
    assert await code_of(priya, "onboard_employee", {**ONBOARD, "work_email": "ARJUN@purser.demo"}) == INVALID_STATE   # case-insensitive
    await propose_and_confirm(priya, "onboard_employee", ONBOARD)
    assert await code_of(priya, "onboard_employee", ONBOARD) == INVALID_STATE                                         # derived email now taken
    assert await code_of(priya, "onboard_employee", {**ONBOARD, "name": "X"}) == VALIDATION
    assert await code_of(priya, "onboard_employee", {**ONBOARD, "name": "Ravi Shah", "start_date": "1st December"}) == VALIDATION
    bad = {k: v for k, v in ONBOARD.items() if k != "start_date"}
    assert await code_of(priya, "onboard_employee", {**bad, "name": "Ravi Shah"}) == VALIDATION
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    assert await code_of(priya, "onboard_employee", {**ONBOARD, "name": "Ravi Shah", "manager_user_id": other["priya_id"]}) == NOT_FOUND
    assert await count(User, User.display_name == "Ravi Shah") == 0


async def test_non_hr_cannot_onboard_and_invited_user_cannot_sign_in(seeded):
    arjun, priya = await make_actor(seeded, "arjun"), await make_actor(seeded)
    users = await count(User)
    assert await code_of(arjun, "onboard_employee", ONBOARD) == FORBIDDEN and await count(User) == users
    await propose_and_confirm(priya, "onboard_employee", ONBOARD)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as c:
        for pw in ("purser-demo", "", "password"):
            assert (await c.post("/api/auth/login", json={"email": "neha.kapoor@purser.demo", "password": pw})).status_code == 401


async def test_onboarding_welcome_email_follows_allowlist(seeded, mail):
    priya = await make_actor(seeded)
    mail.enable("kapoor@gmail.test")
    async with db.session_scope() as s:
        pv = await proposals.create(s, priya, "onboard_employee", {**ONBOARD, "personal_email": "kapoor@gmail.test"})
        pv2 = await proposals.create(s, priya, "onboard_employee", {**ONBOARD, "name": "Ravi Shah", "personal_email": "ravi@gmail.test"})
    mail_line = lambda pv_: next(ln for ln in pv_.preview["lines"] if ln.startswith("Welcome message in the Purser inbox"))  # signature lines follow it when deliverable
    assert "welcome email to kapoor@gmail.test" in mail_line(pv) and "not on the email allow-list" in mail_line(pv2)
    _, out = await propose_and_confirm(priya, "onboard_employee", {**ONBOARD, "personal_email": "kapoor@gmail.test"})
    email = next(m for m in await messages_for(out.receipt.id) if m.channel == "email")
    assert (email.status, email.email_to) == ("queued", "kapoor@gmail.test")
    assert await messaging.dispatch() == 1 and mail.sent[0]["to"] == "kapoor@gmail.test" and mail.sent[0]["subject"] == "Welcome aboard"


async def test_onboarding_failure_leaves_nothing_behind(seeded, monkeypatch):
    priya = await make_actor(seeded)
    p = await present(priya, "onboard_employee", ONBOARD)
    users, parties = await count(User), await count(Party)

    async def boom(*a, **k):
        raise RuntimeError("injected")

    monkeypatch.setattr(audit, "record", boom)
    with pytest.raises(RuntimeError):
        async with db.session_scope() as s:
            await proposals.confirm(s, priya, p.id, via="button")
    monkeypatch.undo()
    assert (await count(User), await count(Party)) == (users, parties)
    assert await count(OnboardingTask) == 0 and await count(Message) == 1 and await count(Receipt) == 0


async def test_overlong_name_is_handled(seeded):
    priya = await make_actor(seeded)
    users, parties = await count(User), await count(Party)
    assert await code_of(priya, "onboard_employee", {**ONBOARD, "name": "N" * 200}) == VALIDATION
    assert (await count(User), await count(Party)) == (users, parties)


# ------------------------------------------------------------------ people tools (SDK invocation, no model)


async def test_people_tools_visibility(seeded):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    out, _ = await call(people_tools.find_people, arjun, name="Neha")
    assert out["ok"] and out["people"][0]["name"] == "Neha Iyer" and set(out["people"][0]) == {"user_id", "name", "department", "designation"}
    out, _ = await call(people_tools.find_people, priya, name="Neha")
    assert {"email", "start_date", "status", "reports_to_id", "role"} <= set(out["people"][0])
    own, _ = await call(people_tools.find_people, arjun, name="Arjun")
    assert "email" in own["people"][0]                                               # your own record is private-visible to you
    out, _ = await call(people_tools.get_leave_balance, arjun, user_id=ids["neha_id"])
    assert (out["ok"], out["code"]) == (False, "FORBIDDEN")
    out, _ = await call(people_tools.get_onboarding_status, arjun, user_id=ids["neha_id"])
    assert (out["ok"], out["code"]) == (False, "FORBIDDEN")
    out, ctx = await call(people_tools.get_leave_balance, arjun)
    assert out["ok"] and out["balances"]["CL"]["available"] == 9 and ctx.ui == [{"card": "leave", "user_id": ids["arjun_id"]}]
    out, _ = await call(people_tools.get_leave_balance, priya, user_id=ids["neha_id"])
    assert out["ok"] and out["balances"]["CL"]["reserved"] == 2
    out, _ = await call(people_tools.get_leave_balance, priya, user_id=999999)
    assert (out["ok"], out["code"]) == (False, NOT_FOUND)


async def test_leave_tools_end_to_end(seeded):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    out, ctx = await call(people_tools.propose_leave, arjun, leave_type="CL", start_date=MON, end_date=TUE, reason="Wedding")
    assert out["ok"] and out["status"] == "open" and "2 day(s) of casual leave" in out["preview"][0] and ctx.ui[0]["card"] == "proposal"
    assert (await bal(ids["arjun_id"]))["CL"]["reserved"] == 0
    bad, _ = await call(people_tools.propose_leave, arjun, leave_type="CL", start_date=SAT, end_date=SUN)
    assert (bad["ok"], bad["code"]) == (False, VALIDATION)
    # Arjun confirms by voice, then Priya decides with the tool
    async with db.session_scope() as s:
        await proposals.mark_presented(s, out["proposal_id"])
    async with db.session_scope() as s:
        await confirmation.record_turn(s, arjun, "haan ji", source="live_sideband")
    done, _ = await call(proposal_tools.confirm_pending_proposal, arjun)
    assert done["ok"] and done["status"] == "executed"
    reqs, _ = await call(people_tools.list_leave_requests, priya, scope="awaiting_my_decision")
    ref = next(r["ref"] for r in reqs["requests"] if r["person"] == "Arjun Mehta")
    assert {r["person"] for r in reqs["requests"]} == {"Arjun Mehta", "Neha Iyer"}
    mine, _ = await call(people_tools.list_leave_requests, arjun)
    assert [r["ref"] for r in mine["requests"]] == [ref] and mine["requests"][0]["reason"] == "Wedding"
    none, _ = await call(people_tools.list_leave_requests, arjun, scope="awaiting_my_decision")
    assert none["requests"] == []
    approve, _ = await call(people_tools.propose_leave_decision, priya, ref=ref, decision="approve")
    assert approve["ok"] and approve["kind"] == "approve"
    reject, _ = await call(people_tools.propose_leave_decision, priya, ref=ids["neha_leave_ref"], decision="reject", note="Busy week")
    assert reject["ok"] and reject["kind"] == "reject_leave" and any("Busy week" in ln for ln in reject["preview"])
    denied, _ = await call(people_tools.propose_leave_decision, arjun, ref=ids["neha_leave_ref"], decision="approve")
    assert (denied["ok"], denied["code"]) == (False, NOT_FOUND)


async def test_message_and_onboarding_tools_enforce_roles(seeded):
    ids = seeded
    priya, arjun = await make_actor(ids), await make_actor(ids, "arjun")
    out, _ = await call(people_tools.propose_message, arjun, audience="all", subject="Hey", body="hello")
    assert (out["ok"], out["code"]) == (False, FORBIDDEN)
    out, _ = await call(people_tools.propose_onboarding, arjun, **{k: v for k, v in ONBOARD.items()})
    assert (out["ok"], out["code"]) == (False, FORBIDDEN)
    out, ctx = await call(people_tools.propose_message, priya, audience="department", department="Sales", subject="Standup", body="10am", channels=["inbox"])
    assert out["ok"] and any("Arjun Mehta" in ln for ln in out["preview"]) and ctx.ui[0]["card"] == "proposal" and await count(Message) == 1
    out, _ = await call(people_tools.propose_onboarding, priya, manager_user_id=ids["priya_id"], **ONBOARD)
    assert out["ok"] and out["kind"] == "onboard_employee" and await count(User, User.display_name == "Neha Kapoor") == 0


async def test_read_inbox_tool_scopes_marks_read_and_clamps(seeded):
    ids = seeded
    priya, arjun, neha = await make_actor(ids), await make_actor(ids, "arjun"), await make_actor(ids, "neha")
    out, _ = await call(people_tools.read_inbox, neha)
    assert out == {"ok": True, "messages": []}
    out, _ = await call(people_tools.read_inbox, arjun)
    assert [(m["ref"], m["from"], m["subject"]) for m in out["messages"]] == [("M0", "Priya Sharma", "Quarter-end expense deadline")]
    out, _ = await call(people_tools.read_inbox, arjun)                          # already read
    assert out["messages"] == []
    out, _ = await call(people_tools.read_inbox, arjun, unread_only=False)
    assert len(out["messages"]) == 1
    await propose_and_confirm(priya, "send_message", {"audience": "person", "user_ids": [ids["arjun_id"]], "subject": "A", "body": "one"})
    await propose_and_confirm(priya, "send_message", {"audience": "person", "user_ids": [ids["arjun_id"]], "subject": "B", "body": "two"})
    out, _ = await call(people_tools.read_inbox, arjun, unread_only=False, limit=0)   # clamped to 1, newest first
    assert [m["subject"] for m in out["messages"]] == ["B"]
    out, _ = await call(people_tools.read_inbox, arjun, unread_only=True, limit=50)
    assert [m["subject"] for m in out["messages"]] == ["A"]
    out, _ = await call(people_tools.read_inbox, neha, unread_only=False)
    assert out["messages"] == []                                                  # Arjun's mail is never Neha's


async def test_onboarding_status_and_policy_tools(seeded):
    ids = seeded
    priya = await make_actor(ids)
    _, out = await propose_and_confirm(priya, "onboard_employee", {**ONBOARD, "manager_user_id": ids["priya_id"]})
    uid = out.receipt.effects[0]["user_id"]
    res, ctx = await call(people_tools.get_onboarding_status, priya, user_id=uid)
    assert res["ok"] and res["status"] == "invited" and len(res["tasks"]) == 5 and ctx.ui[0] == {"card": "person", "user_id": uid}
    assert res["tasks"][0]["status"] == "done" and res["tasks"][1]["due"] == "2026-11-29"
    pol, _ = await call(people_tools.lookup_policy, priya, question="how many sick leave days")
    assert pol["ok"] and pol["sections"][0]["code"] == "HR-3.1" and "Synthetic demo policy" in pol["sections"][0]["text"]
    none, _ = await call(people_tools.lookup_policy, priya, question="stock options vesting schedule")
    assert none == {"ok": True, "sections": []}


# ------------------------------------------------------------------ HTTP API


async def test_inbox_api_scoping(seeded):
    ids = seeded
    priya_c, arjun_c, neha_c = await client_for(), await client_for("arjun@purser.demo"), await client_for("neha@purser.demo")
    a = (await arjun_c.get("/api/inbox")).json()["messages"]
    assert [(m["ref"], m["from"], m["unread"], m["kind"]) for m in a] == [("M0", "Priya Sharma", True, "announcement")]
    assert (await neha_c.get("/api/inbox")).json() == {"messages": []} and (await priya_c.get("/api/inbox")).json() == {"messages": []}
    priya = await make_actor(ids)
    await propose_and_confirm(priya, "send_message", {"audience": "person", "user_ids": [ids["neha_id"]], "subject": "Hi", "body": "hello", "channels": ["inbox", "email"]})
    n = (await neha_c.get("/api/inbox")).json()["messages"]
    assert [m["subject"] for m in n] == ["Hi"]                                    # the email outbox row is not an inbox item
    assert len((await arjun_c.get("/api/inbox")).json()["messages"]) == 1
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as anon:
        assert (await anon.get("/api/inbox")).status_code == 401
    for c in (priya_c, arjun_c, neha_c):
        await c.aclose()


async def test_person_and_leave_cards_api(seeded):
    ids = seeded
    priya_c, arjun_c = await client_for(), await client_for("arjun@purser.demo")
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    neha_card = (await arjun_c.get(f"/api/people/{ids['neha_id']}")).json()
    assert (neha_card["name"], neha_card["department"], neha_card["manager"]) == ("Neha Iyer", "Sales", "Priya Sharma")
    assert neha_card["start_date"] is None and neha_card["status"] is None and neha_card["tasks"] == []
    hr_view = (await priya_c.get(f"/api/people/{ids['neha_id']}")).json()
    assert hr_view["start_date"] == "2025-02-03" and hr_view["status"] == "active"
    own = (await arjun_c.get(f"/api/people/{ids['arjun_id']}")).json()
    assert own["start_date"] == "2024-08-12"
    assert (await arjun_c.get(f"/api/people/{other['arjun_id']}")).status_code == 404 and (await priya_c.get("/api/people/999999")).status_code == 404
    assert (await arjun_c.get(f"/api/people/{ids['neha_id']}/leave")).status_code == 404
    mine = (await arjun_c.get(f"/api/people/{ids['arjun_id']}/leave")).json()
    assert mine["balances"]["CL"]["available"] == 9 and mine["balances"]["SL"]["available"] == 8
    assert (await priya_c.get(f"/api/people/{ids['neha_id']}/leave")).json()["balances"]["CL"]["reserved"] == 2
    assert (await priya_c.get(f"/api/people/{other['arjun_id']}/leave")).status_code == 404
    await priya_c.aclose()
    await arjun_c.aclose()


async def test_leave_requests_api(seeded):
    ids = seeded
    priya_c, arjun_c, neha_c = await client_for(), await client_for("arjun@purser.demo"), await client_for("neha@purser.demo")
    assert (await priya_c.get("/api/leave-requests?scope=bogus")).status_code == 400
    r = (await priya_c.get("/api/leave-requests?scope=awaiting_my_decision")).json()
    assert [(x["ref"], x["person"], x["type"], x["days"], x["state"]) for x in r["requests"]] == [(ids["neha_leave_ref"], "Neha Iyer", "CL", 2, "submitted")]
    assert (await priya_c.get("/api/leave-requests")).json()["requests"] == []                    # default scope is "mine"
    assert len((await neha_c.get("/api/leave-requests")).json()["requests"]) == 1
    for scope in ("awaiting_my_decision", "team", "mine"):
        assert (await arjun_c.get(f"/api/leave-requests?scope={scope}")).json()["requests"] == []
    for c in (priya_c, arjun_c, neha_c):
        await c.aclose()


async def test_receipt_deliveries_api_scoping(seeded):
    ids = seeded
    priya_c, arjun_c, neha_c = await client_for(), await client_for("arjun@purser.demo"), await client_for("neha@purser.demo")
    async with db.session_scope() as s:
        await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    other_c = await client_for("priya@other.demo")
    priya = await make_actor(ids)
    _, out = await propose_and_confirm(priya, "approve", {"ref": ids["neha_leave_ref"]})
    rid = out.receipt.id
    d = (await priya_c.get(f"/api/receipts/{rid}/deliveries")).json()["deliveries"]
    assert [(x["to"], x["channel"]) for x in d] == [("Neha Iyer", "inbox"), ("Neha Iyer", "email")]
    assert d[0]["status"] == "delivered" and d[1]["status"] in ("skipped", "queued") and d[0]["ref"].startswith("M")
    for c in (arjun_c, other_c):
        assert (await c.get(f"/api/receipts/{rid}/deliveries")).status_code == 404
    assert (await priya_c.get("/api/receipts/987654/deliveries")).status_code == 404
    assert (await neha_c.get(f"/api/receipts/{rid}/deliveries")).status_code == 404               # recipient is not the actor
    for c in (priya_c, arjun_c, neha_c, other_c):
        await c.aclose()


async def test_http_confirm_of_leave_decision_end_to_end(seeded):
    ids = seeded
    priya_c = await client_for()
    priya = await make_actor(ids)
    priya = Actor(priya.user_id, priya.workspace_id, priya.role, priya.party_id, priya.display_name, priya_c.headers["x-conversation-id"])
    p = await present(priya, "approve", {"ref": ids["neha_leave_ref"]})
    out = (await priya_c.post(f"/api/proposals/{p.id}/confirm")).json()
    assert out["status"] == "executed" and out["receipt"]["effects"][0] == {"type": "leave_approved", "ref": ids["neha_leave_ref"]}
    assert out["receipt"]["effects"][1]["inbox"] == 1
    again = (await priya_c.post(f"/api/proposals/{p.id}/confirm")).json()
    assert again["status"] == "replayed" and again["receipt"]["id"] == out["receipt"]["id"]
    assert await count(Message, Message.kind == "leave_decision") == 2   # one inbox + one email row, not four
    await priya_c.aclose()
