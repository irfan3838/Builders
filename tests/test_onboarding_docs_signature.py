"""Standard email signature + pre-onboarding document request (signature.py, onboarding_docs.py).

No real email can leave this file: Gmail settings are patched and smtplib.SMTP_SSL fails loudly."""

import smtplib
from datetime import date

import pytest
from sqlalchemy import select

from app import db
from app.agent.workflows import registry
from app.config import get_settings
from app.errors import FORBIDDEN, VALIDATION, DomainError
from app.models import AuditEvent, Message, User
from app.services import actions, messaging, onboarding_docs, records, signature  # actions first: circular import
from tests.conftest import make_actor

SIG = signature.render("Priya Sharma", "HR Head", "People", "Acme Pvt Ltd", "priya@acme.test")


@pytest.fixture(autouse=True)
def mail(monkeypatch):
    off = get_settings().model_copy(update={"gmail_address": "", "gmail_app_password": "", "email_allowed_recipients": "",
                                            "signature_company": "", "signature_phone": "", "signature_website": ""})
    monkeypatch.setattr(messaging, "get_settings", lambda: off)
    monkeypatch.setattr(signature, "get_settings", lambda: off)
    monkeypatch.setattr(onboarding_docs, "get_settings", lambda: off)
    monkeypatch.setattr(messaging, "dispatch_soon", lambda: None)

    def boom(*a, **k):
        raise AssertionError("real SMTP attempted")

    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)

    def enable(*allow):
        on = off.model_copy(update={"gmail_address": "purser@test.invalid", "gmail_app_password": "x",
                                    "email_allowed_recipients": ",".join(allow)})
        monkeypatch.setattr(messaging, "get_settings", lambda: on)
    return enable


# ------------------------------------------------------------------ signature (pure)


def test_render_full_and_minimal():
    assert SIG == "Warm regards,\n\nPriya Sharma\nHR Head | People\nAcme Pvt Ltd\npriya@acme.test"
    bare = signature.render("Neha", None, None, "Acme", None)
    assert bare == "Warm regards,\n\nNeha\nAcme"
    full = signature.render("N", "D", None, "Acme", "n@a.test", phone="123", website="acme.test")
    assert full.splitlines()[-2:] == ["n@a.test | 123", "acme.test"]


@pytest.mark.parametrize("closing", ["Best regards,", "Regards", "Thanks!", "Warm regards,", "Kind regards.", "Sincerely,",
                                     "Yours sincerely,", "Cheers", "Dhanyavaad,", "--", "Many thanks,"])
def test_strip_signoff_removes_common_closings(closing):
    assert signature.strip_signoff(f"Hello Arjun,\n\nPlease join at 10.\n\n{closing}\nIrfan") == "Hello Arjun,\n\nPlease join at 10."


def test_strip_signoff_no_signoff_is_unchanged_modulo_trailing_whitespace():
    assert signature.strip_signoff("Hello,\n\nSee you Monday.\n\n") == "Hello,\n\nSee you Monday."


def test_strip_signoff_deep_in_body_not_stripped():
    body = "Thanks,\nIntro line\nl2\nl3\nl4\nl5\nl6"  # closing-like line is 7th from the end: outside the 5-line tail
    assert signature.strip_signoff(body) == body


def test_strip_signoff_does_not_strip_sentences_that_start_with_a_closing_word():
    body = "Hi,\n\nThanks for your time yesterday.\nSee you soon."
    assert signature.strip_signoff(body) == body


def test_sign_replaces_model_closing_with_standard_signature():
    out = signature.sign("Hello,\n\nSee you.\n\nBest regards,\nIrfan", SIG)
    assert out == f"Hello,\n\nSee you.\n\n{SIG}"
    assert "Irfan" not in out and out.count("Warm regards,") == 1


def test_sign_is_idempotent():
    once = signature.sign("Hello,\n\nSee you.", SIG)
    assert signature.sign(once, SIG) == once
    assert signature.sign(signature.sign("Hi\nRegards,\nX", SIG), SIG).count(SIG) == 1


# ------------------------------------------------------------------ for_actor + compose


async def test_for_actor_uses_directory_record_and_workspace_name(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        u = await s.get(User, priya.user_id)
        sig = await signature.for_actor(s, priya)
    assert sig.startswith(f"Warm regards,\n\n{u.display_name}\n")
    assert u.email in sig.splitlines()[-1]
    assert sig.count("\n") >= 3  # name, company, contact lines


async def test_for_actor_signature_company_override(seeded, monkeypatch):
    st = get_settings().model_copy(update={"signature_company": "Override Co", "signature_phone": "+91 99999", "signature_website": ""})
    monkeypatch.setattr(signature, "get_settings", lambda: st)
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        sig = await signature.for_actor(s, priya)
    assert "Override Co" in sig.splitlines() and "+91 99999" in sig


async def test_compose_signs_email_rows_but_not_inbox_rows(seeded, mail):
    mail("arjun@purser.demo")
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        arjun = await s.get(User, seeded["arjun_id"])
        arjun.notify_email = "arjun@purser.demo"
        sig = await signature.for_actor(s, priya)
        await messaging.compose(s, priya, [arjun], kind="message", subject="Hi", body="Hello Arjun,\n\nPlease sync.\n\nBest,\nIrfan",
                                channels=["inbox", "email"], receipt_id=None)
    async with db.session_scope() as s:
        rows = {m.channel: m for m in (await s.execute(select(Message).where(Message.kind == "message", Message.subject == "Hi"))).scalars()}
    assert rows["email"].body == f"Hello Arjun,\n\nPlease sync.\n\n{sig}"
    assert rows["inbox"].body == "Hello Arjun,\n\nPlease sync.\n\nBest,\nIrfan"
    assert rows["email"].status == "queued"


def test_send_smtp_no_longer_appends_sent_by_purser(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): ...
        def login(self, *a): ...
        def send_message(self, msg): sent["m"] = msg

    st = get_settings().model_copy(update={"gmail_address": "p@test.invalid", "gmail_app_password": "x"})
    monkeypatch.setattr(messaging, "get_settings", lambda: st)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    messaging._send_smtp("a@b.test", "S", "Body\n\nWarm regards,\nP")
    text = sent["m"].get_content()
    assert "Sent by Purser" not in text and text.strip() == "Body\n\nWarm regards,\nP"


async def test_send_message_plan_lists_signature_only_for_email(seeded):
    priya = await make_actor(seeded)
    base = {"audience": "person", "user_ids": [seeded["arjun_id"]], "subject": "S", "body": "B"}
    async with db.session_scope() as s:
        with_email = await actions.ACTIONS["send_message"].plan(s, priya, {**base, "channels": ["inbox", "email"]})
        inbox_only = await actions.ACTIONS["send_message"].plan(s, priya, {**base, "channels": ["inbox"]})
        sig = await signature.for_actor(s, priya)
    i = with_email.lines.index("Email signature:")
    assert with_email.lines[i + 1:] == sig.splitlines()
    assert "Email signature:" not in inbox_only.lines


# ------------------------------------------------------------------ compose_email (pure)


def _inp(**kw):
    base = {"name": "Ananya Rao", "designation": "Backend Engineer", "department": None, "email": "ananya@gmail.test",
            "start": date(2026, 12, 14), "today": date(2026, 11, 22), "extra": [], "manager": None, "company": "Acme Pvt Ltd"}
    return {**base, **kw}


def test_compose_email_subject_and_content():
    subject, body = onboarding_docs.compose_email(_inp(), SIG)
    assert subject == "Documents required for your onboarding - Backend Engineer, Acme Pvt Ltd"
    assert body.startswith("Dear Ananya,")
    for needle in ("Aadhaar card (front and back)", "PAN card", "Bank account number", "original Aadhaar card and PAN card",
                   "Monday, 14 December 2026", "Personal details", "Identity documents", "Bank details"):
        assert needle in body
    assert "Additional requirements" not in body and "reporting to" not in body
    assert body.endswith(SIG) and body.count("Warm regards,") == 1


def test_compose_email_numbering_is_continuous_and_extras_appended():
    _, body = onboarding_docs.compose_email(_inp(extra=["Passport copy", "Vaccination certificate"]), SIG)
    nums = [int(l.split(".")[0]) for l in body.splitlines() if l.startswith("  ") and l.strip()[:1].isdigit()]
    assert nums == list(range(1, len(nums) + 1))
    assert body.index("Additional requirements") < body.index("Passport copy") < body.index("Vaccination certificate")
    assert f"  {nums[-1]}. Vaccination certificate" in body


def test_compose_email_department_and_manager():
    class M: display_name = "Neha Iyer"
    _, body = onboarding_docs.compose_email(_inp(department="Engineering", manager=M()), SIG)
    assert "in the Engineering team at Acme Pvt Ltd" in body and "reporting to Neha Iyer" in body


def test_compose_email_is_deterministic():
    assert onboarding_docs.compose_email(_inp(), SIG) == onboarding_docs.compose_email(_inp(), SIG)


def test_reply_by_saturday_start_counts_back_over_weekend():
    assert onboarding_docs._reply_by(date(2026, 12, 12), date(2026, 11, 22)) == date(2026, 12, 9)  # Fri, Thu, Wed


def test_reply_by_exact_for_monday_and_wednesday_start():
    assert onboarding_docs._reply_by(date(2026, 12, 14), date(2026, 11, 22)) == date(2026, 12, 9)
    assert onboarding_docs._reply_by(date(2026, 12, 16), date(2026, 11, 22)) == date(2026, 12, 11)


def test_reply_by_passed_means_at_the_earliest():
    assert onboarding_docs._reply_by(date(2026, 11, 24), date(2026, 11, 23)) is None
    _, body = onboarding_docs.compose_email(_inp(start=date(2026, 11, 24), today=date(2026, 11, 23)), SIG)
    assert "Kindly share these at the earliest" in body and "Kindly share these by" not in body


def test_compose_email_reply_by_line_has_date():
    _, body = onboarding_docs.compose_email(_inp(), SIG)
    assert "Kindly share these by Wednesday, 9 December 2026" in body


# ------------------------------------------------------------------ _inputs validation


GOOD = {"name": "Ananya Rao", "designation": "Backend Engineer", "personal_email": "Ananya@Gmail.test", "start_date": "2099-01-05"}


async def _err(actor, args):
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await onboarding_docs._inputs(s, actor, args)
    return e.value


async def test_inputs_hr_only(seeded):
    arjun = await make_actor(seeded, "arjun")
    assert (await _err(arjun, GOOD)).code == FORBIDDEN


async def test_inputs_normalises_and_accepts_good_input(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        i = await onboarding_docs._inputs(s, priya, {**GOOD, "name": "  Ananya   Rao ", "extra_items": ["A", "A", "", "B"]})
    assert i["name"] == "Ananya Rao" and i["email"] == "ananya@gmail.test" and i["extra"] == ["A", "B"]
    assert i["start"] == date(2099, 1, 5) and i["manager"] is None and i["company"]


@pytest.mark.parametrize("patch", [
    {"name": ""}, {"name": "A"}, {"name": "x" * 121}, {"designation": ""}, {"designation": "x" * 81},
    {"personal_email": ""}, {"personal_email": "not-an-email"}, {"personal_email": "a@b"}, {"personal_email": "a b@c.test"},
    {"start_date": "14/12/2099"}, {"start_date": "2000-01-01"},
    {"extra_items": ["x" * 121]}, {"extra_items": [f"item {n}" for n in range(7)]},
])
async def test_inputs_validation_errors(seeded, patch):
    priya = await make_actor(seeded)
    assert (await _err(priya, {**GOOD, **patch})).code == VALIDATION


async def test_inputs_missing_start_date_and_past_date_message(seeded):
    priya = await make_actor(seeded)
    bad = {k: v for k, v in GOOD.items() if k != "start_date"}
    assert (await _err(priya, bad)).code == VALIDATION
    assert "already passed" in (await _err(priya, {**GOOD, "start_date": "2000-01-01"})).message


async def test_inputs_start_today_is_allowed_and_six_extras_ok(seeded, monkeypatch):
    priya = await make_actor(seeded)
    monkeypatch.setattr(records, "today_ist", lambda: date(2099, 1, 5))
    async with db.session_scope() as s:
        i = await onboarding_docs._inputs(s, priya, {**GOOD, "extra_items": [f"item {n}" for n in range(6)]})
    assert i["start"] == i["today"] and len(i["extra"]) == 6


async def test_inputs_manager_resolved(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        i = await onboarding_docs._inputs(s, priya, {**GOOD, "manager_user_id": seeded["arjun_id"]})
    assert i["manager"].id == seeded["arjun_id"]


# ------------------------------------------------------------------ plan / execute


def test_action_registered():
    assert actions.ACTIONS["request_onboarding_documents"].kind == "request_onboarding_documents"


async def test_plan_preview_states_deliverability(seeded, mail):
    priya = await make_actor(seeded)
    act = actions.ACTIONS["request_onboarding_documents"]
    async with db.session_scope() as s:
        p = await act.plan(s, priya, GOOD)
        sig = await signature.for_actor(s, priya)
    assert p.lines[0] == "To: ananya@gmail.test (cannot be sent (email is not configured))"
    assert p.lines[1].startswith("Subject: Documents required for your onboarding - Backend Engineer, ")
    assert "Aadhaar card" in "\n".join(p.lines) and p.lines[-len(sig.splitlines()):] == sig.splitlines()
    mail("someone@else.test")
    async with db.session_scope() as s:
        assert "allow-list" in (await act.plan(s, priya, GOOD)).lines[0]
    mail("ananya@gmail.test")
    async with db.session_scope() as s:
        assert (await act.plan(s, priya, GOOD)).lines[0] == "To: ananya@gmail.test (will be sent)"


async def test_plan_forbidden_for_non_hr(seeded):
    arjun = await make_actor(seeded, "arjun")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await actions.ACTIONS["request_onboarding_documents"].plan(s, arjun, GOOD)
    assert e.value.code == FORBIDDEN


async def _msgs():
    async with db.session_scope() as s:
        return (await s.execute(select(Message).where(Message.kind == "onboarding_documents"))).scalars().all()


async def test_execute_queues_signed_email_and_audits(seeded, mail):
    mail("ananya@gmail.test")
    priya = await make_actor(seeded)
    act = actions.ACTIONS["request_onboarding_documents"]
    async with db.session_scope() as s:
        out = await act.execute(s, priya, GOOD, None)
        sig = await signature.for_actor(s, priya)
    assert "emailed to Ananya Rao" in out.summary
    rows = await _msgs()
    assert len(rows) == 1
    m = rows[0]
    assert (m.channel, m.email_to, m.status, m.recipient_user_id) == ("email", "ananya@gmail.test", "queued", None)
    assert m.subject.startswith("Documents required for your onboarding") and m.body.endswith(sig) and m.body.count("Warm regards,") == 1
    async with db.session_scope() as s:
        ev = (await s.execute(select(AuditEvent).where(AuditEvent.action == "onboarding.documents_requested"))).scalars().all()
    assert len(ev) == 1 and ev[0].after["email"] == "ananya@gmail.test" and ev[0].after["email_queued"] == 1
    assert ev[0].after["start_date"] == "2099-01-05"


async def test_execute_skipped_when_not_allow_listed(seeded, mail):
    mail("someone@else.test")
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        out = await actions.ACTIONS["request_onboarding_documents"].execute(s, priya, GOOD, None)
    assert "NOT sent" in out.summary and "not on allowlist" in out.summary
    m = (await _msgs())[0]
    assert (m.status, m.status_detail) == ("skipped", "not_on_allowlist")


async def test_execute_email_not_configured_is_skipped(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        out = await actions.ACTIONS["request_onboarding_documents"].execute(s, priya, GOOD, None)
    assert "NOT sent" in out.summary
    assert (await _msgs())[0].status == "skipped"


async def test_execute_rejects_non_hr_and_writes_nothing(seeded):
    arjun = await make_actor(seeded, "arjun")
    async with db.session_scope() as s:
        with pytest.raises(DomainError):
            await actions.ACTIONS["request_onboarding_documents"].execute(s, arjun, GOOD, None)
    assert await _msgs() == []


# ------------------------------------------------------------------ registry / tool wiring


def test_registry_check_and_onboarding_workflow_lists_tool():
    wfs = registry.workflows()
    registry.check(wfs)
    assert any("propose_onboarding_documents" in wf.tools for wf in wfs.values())


def test_tool_is_exported():
    from app.agent.tools import people as pt
    assert any(getattr(t, "name", None) == "propose_onboarding_documents" for t in pt.TOOLS)
