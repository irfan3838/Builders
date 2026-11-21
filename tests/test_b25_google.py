"""B2 gate: Gmail/Calendar helpers, google_actions (queue/dispatch/perform), google tools. Google is never contacted."""

import base64
import email
import json
from dataclasses import replace
from datetime import timedelta

import pytest
from agents import RunContextWrapper
from sqlalchemy import select

from app import db
from app.agent import tool_access
from app.agent.context import PurserContext
from app.agent.tools import google as gtools
from app.errors import FORBIDDEN, VALIDATION, DomainError
from app.models import AuditEvent, GoogleOp
from app.services import actions, google_actions
from app.services.google import auth, gcal, gmail
from app.services.records import today_ist
from seed.role_users import seed_roles
from tests.b25_helpers import FAKE_GOOGLE, LINKED, actor_by_email, linked, pin
from tests.conftest import make_actor
from tests.test_intake_extra import call
from tests.test_ledger_gates import propose_and_confirm
from tests.test_people_extra import mail  # noqa: F401  (autouse safety fixture: no SMTP)


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    pin(monkeypatch, **FAKE_GOOGLE)
    import httpx

    def no_net(*a, **k):
        raise AssertionError("a google test opened a real httpx client")

    async def no_call(*a, **k):
        raise AssertionError("a google test reached auth.call (real Google)")
    monkeypatch.setattr(httpx, "AsyncClient", no_net)
    monkeypatch.setattr(auth, "call", no_call)
    for mod in (gmail, gcal):
        monkeypatch.setattr(mod, "call", no_call)


def b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def parse(raw: str):
    return email.message_from_bytes(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))


async def ops():
    async with db.session_scope() as s:
        return list((await s.execute(select(GoogleOp).order_by(GoogleOp.id))).scalars())


# ------------------------------------------------------------------ gmail helpers


def test_build_raw_plain_message():
    m = parse(gmail.build_raw("me@x.com", ["a@x.com", "b@x.com"], "Hello", "Body text", cc=["c@x.com"]))
    assert m["From"] == "me@x.com" and m["To"] == "a@x.com, b@x.com" and m["Cc"] == "c@x.com" and m["Subject"] == "Hello"
    assert m["In-Reply-To"] is None and m["References"] is None
    assert m.get_payload(decode=True).decode().strip() == "Body text"


def test_build_raw_reply_headers():
    m = parse(gmail.build_raw("me@x.com", ["a@x.com"], "Re: Plan", "ok", in_reply_to="<m3@x>", references="<m1@x> <m2@x>"))
    assert m["In-Reply-To"] == "<m3@x>"
    assert m["References"] == "<m1@x> <m2@x> <m3@x>"
    m2 = parse(gmail.build_raw("me@x.com", ["a@x.com"], "Re: Plan", "ok", in_reply_to="<m3@x>"))
    assert m2["References"] == "<m3@x>"


def test_build_raw_subject_is_single_line_and_capped():
    m = parse(gmail.build_raw("me@x.com", ["a@x.com"], "Line one\r\nBcc: evil@x.com\nline  three", "b"))
    assert "\n" not in m["Subject"] and m["Bcc"] is None
    assert m["Subject"] == "Line one Bcc: evil@x.com line three"
    long = parse(gmail.build_raw("me@x.com", ["a@x.com"], "x" * 400, "b"))
    from email.header import decode_header, make_header
    assert str(make_header(decode_header(long["Subject"]))) == "x" * 250


def test_text_prefers_plain_over_html():
    payload = {"mimeType": "multipart/alternative", "parts": [
        {"mimeType": "text/html", "body": {"data": b64("<p>HTML version</p>")}},
        {"mimeType": "text/plain", "body": {"data": b64("Plain version")}}]}
    assert gmail._text(payload) == "Plain version"


def test_text_strips_html_script_style_and_unescapes():
    html = "<html><style>p{color:red}</style><script>alert(1)</script><body><p>Hi&nbsp;there &amp; <b>welcome</b></p></body></html>"
    out = gmail._text({"mimeType": "text/html", "body": {"data": b64(html)}})
    assert "alert" not in out and "color" not in out and "<" not in out
    assert "Hi" in out and "& welcome" in out


def test_text_truncates_with_marker():
    out = gmail._text({"mimeType": "text/plain", "body": {"data": b64("a" * 2500)}})
    assert out == "a" * gmail.BODY_LIMIT + " …[truncated]"
    exact = gmail._text({"mimeType": "text/plain", "body": {"data": b64("b" * 2000)}})
    assert exact == "b" * 2000


def test_text_nested_parts_and_empty():
    nested = {"mimeType": "multipart/mixed", "parts": [{"mimeType": "multipart/alternative", "parts": [
        {"mimeType": "text/plain", "body": {"data": b64("deep text")}}]}]}
    assert gmail._text(nested) == "deep text"
    assert gmail._text({"mimeType": "multipart/mixed", "parts": []}) == ""


def test_summary_and_addresses():
    msg = {"id": "1", "threadId": "t", "labelIds": ["INBOX", "UNREAD", "IMPORTANT"], "snippet": "a &amp; b",
           "payload": {"headers": [{"name": "from", "value": "Asha <asha@x.com>"}, {"name": "Subject", "value": "Hi"}]}}
    s = gmail.summary(msg)
    assert s["from"] == "Asha" and s["from_email"] == "asha@x.com" and s["unread"] and s["important"] and s["in_inbox"]
    assert s["snippet"] == "a & b" and s["subject"] == "Hi"
    assert gmail.summary({"id": "2", "payload": {"headers": []}})["subject"] == "(no subject)"
    assert gmail.addresses("A <a@x.com>, b@x.com") == ["a@x.com", "b@x.com"]


def test_gcal_view_all_day_and_meet():
    v = gcal.view({"id": "e", "start": {"date": "2026-12-01"}, "end": {"date": "2026-12-02"}, "status": "confirmed"})
    assert v["all_day"] is True and v["title"] == "(no title)" and v["meet_url"] is None
    v2 = gcal.view({"id": "e", "summary": "S", "start": {"dateTime": "2026-12-01T10:00:00+05:30"}, "end": {"dateTime": "2026-12-01T11:00:00+05:30"},
                    "conferenceData": {"entryPoints": [{"entryPointType": "video", "uri": "https://meet/x"}]},
                    "attendees": [{"email": "a@x.com"}, {}]})
    assert v2["all_day"] is False and v2["meet_url"] == "https://meet/x" and v2["attendees"] == ["a@x.com"]


async def test_list_events_drops_cancelled(monkeypatch):
    async def fake(method, url, params=None, json=None, timeout=15):
        return {"items": [{"id": "a", "status": "cancelled", "start": {}, "end": {}},
                          {"id": "b", "summary": "Keep", "start": {"dateTime": "x"}, "end": {"dateTime": "y"}}]}
    monkeypatch.setattr(gcal, "call", fake)
    from datetime import datetime
    ev = await gcal.list_events(datetime(2026, 12, 1), datetime(2026, 12, 2))
    assert [e["title"] for e in ev] == ["Keep"]


# ------------------------------------------------------------------ SendEmail validation / forbidden


async def plan(kind, actor, args):
    async with db.session_scope() as s:
        return await actions.ACTIONS[kind].plan(s, actor, args)


async def plan_err(kind, actor, args):
    with pytest.raises(DomainError) as e:
        await plan(kind, actor, args)
    return e.value


GOOD = {"to": ["Bob@Example.com"], "subject": "Hello", "body": "Hi Bob"}


async def test_actions_registered():
    for k in ("gmail_send", "gmail_action", "gcal_reschedule", "gcal_cancel"):
        assert k in actions.ACTIONS


@pytest.mark.parametrize("bad", ["nope", "a@b", "a b@c.com", "@c.com", ""])
async def test_send_bad_address(seeded, bad):
    priya = linked(await make_actor(seeded))
    e = await plan_err("gmail_send", priya, {**GOOD, "to": [bad]})
    assert e.code == VALIDATION


async def test_send_bad_cc(seeded):
    e = await plan_err("gmail_send", linked(await make_actor(seeded)), {**GOOD, "cc": ["bad"]})
    assert e.code == VALIDATION and "cc" in str(e)


async def test_send_missing_fields(seeded):
    priya = linked(await make_actor(seeded))
    assert "subject" in str(await plan_err("gmail_send", priya, {**GOOD, "subject": "  "}))
    assert "subject" in str(await plan_err("gmail_send", priya, {"to": ["a@b.com"], "body": "x"}))
    assert "body" in str(await plan_err("gmail_send", priya, {**GOOD, "body": " "}))
    assert "body" in str(await plan_err("gmail_send", priya, {"to": ["a@b.com"], "subject": "s"}))
    assert "5,000" in str(await plan_err("gmail_send", priya, {**GOOD, "body": "x" * 5001}))
    e = await plan_err("gmail_send", priya, {"subject": "s", "body": "b"})
    assert e.code == VALIDATION and "Who" in str(e)


async def test_send_plan_lowercases_dedupes_and_shows_preview(seeded):
    priya = linked(await make_actor(seeded))
    p = await plan("gmail_send", priya, {**GOOD, "to": ["Bob@Example.com", "bob@example.com"], "cc": ["c@x.com"]})
    assert p.title == "Send email from Gmail"
    assert f"From: {LINKED} (your Gmail)" in p.lines and "To: bob@example.com" in p.lines and "Cc: c@x.com" in p.lines
    assert "Subject: Hello" in p.lines and "Hi Bob" in p.lines
    assert p.lines[1] == "To: bob@example.com"


async def test_send_reply_uses_thread_context(seeded, monkeypatch):
    async def ctx(tid):
        return {"to": ["asha@x.com"], "subject": "Re: Plan", "in_reply_to": "<m@x>", "references": "<r@x>", "thread_id": tid,
                "replying_to": "Asha — Plan"}
    monkeypatch.setattr(gmail, "reply_context", ctx)
    priya = linked(await make_actor(seeded))
    p = await plan("gmail_send", priya, {"body": "Thanks", "reply_thread_id": "T1"})
    assert "To: asha@x.com" in p.lines and "Subject: Re: Plan" in p.lines and "Reply in the thread: Asha — Plan" in p.lines
    assert p.speak.startswith("Send this reply")


async def test_google_failure_in_reply_context_is_domain_error(seeded, monkeypatch):
    async def boom(tid):
        raise auth.GoogleError("token revoked")
    monkeypatch.setattr(gmail, "reply_context", boom)
    e = await plan_err("gmail_send", linked(await make_actor(seeded)), {"body": "x", "reply_thread_id": "T"})
    assert e.code == "GOOGLE_UNAVAILABLE"


@pytest.mark.parametrize("kind,args", [
    ("gmail_send", GOOD), ("gmail_action", {"message_ids": ["1"], "action": "archive"}),
    ("gcal_reschedule", {"event_id": "e", "start": "2030-01-01T10:00"}), ("gcal_cancel", {"event_id": "e"})])
async def test_non_linked_user_forbidden(seeded, kind, args):
    arjun = await make_actor(seeded, "arjun")  # no email at all
    assert (await plan_err(kind, arjun, args)).code == FORBIDDEN
    priya_other = replace(await make_actor(seeded), email="someone@else.com")
    assert (await plan_err(kind, priya_other, args)).code == FORBIDDEN
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await actions.ACTIONS[kind].execute(s, arjun, args, None)
    assert e.value.code == FORBIDDEN
    assert await ops() == []


async def test_linked_email_but_google_not_configured_is_forbidden(seeded, monkeypatch):
    pin(monkeypatch, google_client_id="", google_client_secret="", google_refresh_token="", google_linked_email=LINKED)
    assert (await plan_err("gmail_send", linked(await make_actor(seeded)), GOOD)).code == FORBIDDEN


async def test_linked_email_match_is_case_insensitive(seeded):
    priya = replace(await make_actor(seeded), email=LINKED.upper())
    assert priya.uses_google
    await plan("gmail_send", priya, GOOD)


# ------------------------------------------------------------------ execute queues exactly one GoogleOp


async def test_send_confirm_queues_one_op(seeded):
    priya = linked(await make_actor(seeded))
    _, out = await propose_and_confirm(priya, "gmail_send", {**GOOD, "cc": ["c@x.com"]})
    assert out.status == "executed"
    got = await ops()
    assert len(got) == 1
    op = got[0]
    assert op.kind == "send_email" and op.status == "queued" and op.ref == f"G{op.id}" and op.user_id == priya.user_id
    assert op.payload["to"] == ["bob@example.com"] and op.payload["sender"] == LINKED and op.payload["subject"] == "Hello"
    assert op.payload["body"] == "Hi Bob" and op.receipt_id == out.receipt.id
    assert out.receipt.effects == [{"type": "google_op", "ref": op.ref, "kind": "send_email"}]
    assert op.ref in out.receipt.summary
    # confirm is idempotent: replay does not queue a second op
    async with db.session_scope() as s:
        from app.services import proposals
        p = (await proposals.get_open(s, priya))
    assert p is None
    assert len(await ops()) == 1


async def test_audit_does_not_leak_email_body(seeded):
    priya = linked(await make_actor(seeded))
    await propose_and_confirm(priya, "gmail_send", {**GOOD, "body": "SECRET-BODY-TEXT"})
    async with db.session_scope() as s:
        ev = (await s.execute(select(AuditEvent).where(AuditEvent.action == "google.send_email"))).scalars().all()
    assert len(ev) == 1 and "SECRET-BODY-TEXT" not in json.dumps(ev[0].after)


async def test_mail_action_validation_and_queue(seeded):
    priya = linked(await make_actor(seeded))
    assert "Which emails" in str(await plan_err("gmail_action", priya, {"message_ids": [], "action": "archive"}))
    assert "Unknown action" in str(await plan_err("gmail_action", priya, {"message_ids": ["1"], "action": "delete"}))
    assert "Which label" in str(await plan_err("gmail_action", priya, {"message_ids": ["1"], "action": "label", "label": " "}))
    p = await plan("gmail_action", priya, {"message_ids": ["1", "1", "2"], "action": "archive", "titles": ["A", "B"]})
    assert p.lines[0] == "Archive 2 emails in your Gmail." and "• A" in p.lines
    _, out = await propose_and_confirm(priya, "gmail_action", {"message_ids": ["1", "1", "2"], "action": "star"})
    assert out.status == "executed"
    (op,) = await ops()
    assert op.kind == "mail_action" and op.payload == {"ids": ["1", "2"], "action": "star", "label": None}


async def test_mail_action_caps_ids_at_25(seeded):
    priya = linked(await make_actor(seeded))
    _, out = await propose_and_confirm(priya, "gmail_action", {"message_ids": [str(i) for i in range(40)], "action": "mark_read"})
    (op,) = await ops()
    assert len(op.payload["ids"]) == 25


EVENT = {"event_id": "ev1", "title": "Design review", "start": "2030-05-01T10:00:00+05:30", "end": "2030-05-01T11:00:00+05:30",
         "all_day": False, "attendees": ["a@x.com"]}


async def test_reschedule_and_cancel(seeded, monkeypatch):
    async def get_event(eid):
        assert eid == "ev1"
        return dict(EVENT)
    monkeypatch.setattr(gcal, "get_event", get_event)
    priya = linked(await make_actor(seeded))
    p = await plan("gcal_reschedule", priya, {"event_id": "ev1", "start": "2030-05-02T15:30"})
    assert "Event: Design review" in p.lines and any("guest" in l for l in p.lines)
    assert "3:30 PM – 4:30 PM" in p.lines[2]  # duration (60 min) preserved
    _, out = await propose_and_confirm(priya, "gcal_reschedule", {"event_id": "ev1", "start": "2030-05-02T15:30"})
    assert out.status == "executed"
    (op,) = await ops()
    assert op.kind == "reschedule_event" and op.status == "queued" and op.payload["tz"] == "Asia/Kolkata"
    assert op.payload["start"].startswith("2030-05-02T15:30") and op.payload["end"].startswith("2030-05-02T16:30")
    _, out2 = await propose_and_confirm(priya, "gcal_cancel", {"event_id": "ev1"})
    assert out2.status == "executed" and [o.kind for o in await ops()] == ["reschedule_event", "cancel_event"]


async def test_reschedule_validation(seeded, monkeypatch):
    async def get_event(eid):
        return {**EVENT, "all_day": eid == "allday"}
    monkeypatch.setattr(gcal, "get_event", get_event)
    priya = linked(await make_actor(seeded))
    assert "YYYY-MM-DDTHH:MM" in str(await plan_err("gcal_reschedule", priya, {"event_id": "ev1", "start": "tomorrow 3pm"}))
    assert "all-day" in str(await plan_err("gcal_reschedule", priya, {"event_id": "allday", "start": "2030-05-02T15:30"}))
    p = await plan("gcal_reschedule", priya, {"event_id": "ev1", "start": "2030-05-02T15:30", "minutes": 15})
    assert "3:30 PM – 3:45 PM" in p.lines[2]


# ------------------------------------------------------------------ dispatch / perform


async def queue_two(seeded):
    priya = linked(await make_actor(seeded))
    await propose_and_confirm(priya, "gmail_send", GOOD)
    await propose_and_confirm(priya, "gmail_action", {"message_ids": ["1"], "action": "archive"})


async def test_dispatch_marks_done_and_failed(seeded, monkeypatch):
    await queue_two(seeded)
    seen = []

    async def fake_perform(op):
        seen.append(op.kind)
        if op.kind == "mail_action":
            raise RuntimeError("gmail said no " + "x" * 400)
        return {"gmail_id": "g1"}
    monkeypatch.setattr(google_actions, "perform", fake_perform)
    assert await google_actions.dispatch() == 1
    assert seen == ["send_email", "mail_action"]
    a, b = await ops()
    assert (a.status, a.result) == ("done", {"gmail_id": "g1"})
    assert b.status == "failed" and b.status_detail.startswith("RuntimeError: gmail said no") and len(b.status_detail) <= 300
    # nothing left in the queue: a failed op is never retried blindly
    assert await google_actions.dispatch() == 0 and seen == ["send_email", "mail_action"]


async def test_dispatch_respects_limit(seeded, monkeypatch):
    await queue_two(seeded)

    async def ok(op):
        return {}
    monkeypatch.setattr(google_actions, "perform", ok)
    assert await google_actions.dispatch(limit=1) == 1
    assert [o.status for o in await ops()] == ["done", "queued"]


async def test_dispatch_noop_when_google_not_configured(seeded, monkeypatch):
    await queue_two(seeded)
    pin(monkeypatch, google_client_id="", google_client_secret="", google_refresh_token="")
    assert await google_actions.dispatch() == 0
    assert [o.status for o in await ops()] == ["queued", "queued"]


async def test_perform_each_kind(seeded, monkeypatch):
    calls = {}

    async def send(sender, to, subject, body, **kw):
        calls["send"] = (sender, to, subject, body, kw)
        return {"id": "m1", "threadId": "t1"}

    async def modify(ids, add, remove):
        calls["modify"] = (ids, add, remove)
        return {}

    async def move(eid, start, end, tz):
        calls["move"] = (eid, start, end, tz)
        return {"event_id": eid, "start": start.isoformat()}

    async def delete(eid):
        calls["delete"] = eid
        return {"event_id": eid, "deleted": True}

    async def create(title, start, end, tz, description=""):
        calls["create"] = (title, tz, description)
        return {"event_id": "n1", "url": "https://cal/n1"}
    monkeypatch.setattr(gmail, "send", send)
    monkeypatch.setattr(gmail, "modify", modify)
    monkeypatch.setattr(gcal, "move_event", move)
    monkeypatch.setattr(gcal, "delete_event", delete)
    monkeypatch.setattr(gcal, "create_simple", create)

    def op(kind, **payload):
        return GoogleOp(workspace_id=1, user_id=1, ref="G1", kind=kind, payload=payload)
    r = await google_actions.perform(op("send_email", sender="me@x.com", to=["a@x.com"], subject="S", body="B", cc=["c@x.com"], thread_id="t"))
    assert r == {"gmail_id": "m1", "thread_id": "t1"} and calls["send"][4]["thread_id"] == "t" and calls["send"][4]["cc"] == ["c@x.com"]
    assert await google_actions.perform(op("mail_action", ids=["1", "2"], action="archive", label=None)) == {"modified": 2}
    assert calls["modify"] == (["1", "2"], [], ["INBOX"])
    await google_actions.perform(op("mail_action", ids=["1"], action="mark_unread", label=None))
    assert calls["modify"] == (["1"], ["UNREAD"], [])
    r = await google_actions.perform(op("reschedule_event", event_id="e", start="2030-01-01T10:00:00+05:30", end="2030-01-01T11:00:00+05:30", tz="Asia/Kolkata"))
    assert r["event_id"] == "e" and calls["move"][3] == "Asia/Kolkata"
    assert await google_actions.perform(op("cancel_event", event_id="e")) == {"event_id": "e", "deleted": True}
    r = await google_actions.perform(op("create_event", title="T", start="2030-01-01T10:00:00+05:30", end="2030-01-01T11:00:00+05:30", tz="Asia/Kolkata"))
    assert r == {"event_id": "n1", "url": "https://cal/n1"} and calls["create"] == ("T", "Asia/Kolkata", "")
    with pytest.raises(ValueError):
        await google_actions.perform(op("explode"))


async def test_perform_label_reuses_existing_or_creates(seeded, monkeypatch):
    mods = []

    async def labels():
        return [{"id": "L9", "name": "Invoices"}]

    async def modify(ids, add, remove):
        mods.append((ids, add, remove))
        return {}
    created = []

    async def fake_call(method, url, **kw):
        created.append((method, kw["json"]))
        return {"id": "NEW"}
    monkeypatch.setattr(gmail, "labels", labels)
    monkeypatch.setattr(gmail, "modify", modify)
    monkeypatch.setattr(auth, "call", fake_call)
    mk = lambda lab: GoogleOp(workspace_id=1, user_id=1, ref="G", kind="mail_action", payload={"ids": ["1"], "action": "label", "label": lab})  # noqa: E731
    await google_actions.perform(mk("  invoices "))
    assert mods[-1] == (["1"], ["L9"], []) and created == []
    await google_actions.perform(mk("Taxes"))
    assert mods[-1] == (["1"], ["NEW"], []) and created == [("POST", {"name": "Taxes"})]


async def test_auth_call_maps_errors(monkeypatch):
    """Token refresh failure surfaces as GoogleError, never leaks the secret."""
    import httpx
    monkeypatch.undo()  # use the real auth module with a mock transport
    pin_settings = None  # noqa: F841
    auth._cache.update(token="", exp=0.0)

    async def run(handler):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await auth.access_token(c)
    from tests.b25_helpers import REAL_CLIENT  # noqa: F401
    import app.config as config_mod
    from app.config import get_settings
    patched = get_settings().model_copy(update=FAKE_GOOGLE)
    monkeypatch.setattr(config_mod, "get_settings", lambda: patched)
    monkeypatch.setattr(auth, "get_settings", lambda: patched)
    with pytest.raises(auth.GoogleError, match="expired or was revoked"):
        await run(lambda r: httpx.Response(400, json={"error": "invalid_grant"}))
    with pytest.raises(auth.GoogleError) as e:
        await run(lambda r: httpx.Response(500, text="oops"))
    assert "csecret" not in str(e.value) and "rtoken" not in str(e.value)
    tok = await run(lambda r: httpx.Response(200, json={"access_token": "AT", "expires_in": 3600}))
    assert tok == "AT"
    assert await run(lambda r: (_ for _ in ()).throw(AssertionError("cached token must be reused"))) == "AT"
    auth._cache.update(token="", exp=0.0)


# ------------------------------------------------------------------ tools


GOOGLE_ONLY = ["search_mail", "read_mail_thread", "save_mail_draft", "propose_email", "propose_mail_action",
               "propose_reschedule_meeting", "propose_cancel_meeting"]
ARGS = {"search_mail": {}, "read_mail_thread": {"thread_id": "t"}, "save_mail_draft": {"body": "b", "to": ["a@b.com"], "subject": "s"},
        "propose_email": {"body": "b", "to": ["a@b.com"], "subject": "s"},
        "propose_mail_action": {"message_ids": ["1"], "action": "archive"},
        "propose_reschedule_meeting": {"event_id": "e", "start": "2030-01-01T10:00"}, "propose_cancel_meeting": {"event_id": "e"}}


def tool(name):
    return next(t for t in gtools.TOOLS if t.name == name)


@pytest.mark.parametrize("name", GOOGLE_ONLY)
async def test_google_tools_forbidden_for_non_linked(seeded, name):
    arjun = await make_actor(seeded, "arjun")
    out, ctx = await call(tool(name), arjun, **ARGS[name])
    assert out["ok"] is False and out["code"] == FORBIDDEN
    assert ctx.ui == [] and await ops() == []


@pytest.mark.parametrize("name", GOOGLE_ONLY)
async def test_google_tools_hidden_from_model_unless_linked(seeded, name):
    arjun = await make_actor(seeded, "arjun")
    wrapped = lambda a: RunContextWrapper(context=PurserContext(actor=a))  # noqa: E731
    assert tool_access._allowed(name, wrapped(arjun)) is False
    assert tool_access._allowed(name, wrapped(linked(await make_actor(seeded)))) is True
    assert tool_access._allowed("list_meetings", wrapped(arjun)) is True


async def test_search_and_read_for_linked(seeded, monkeypatch):
    async def search(q, n):
        assert q == "in:inbox is:unread" and n == 8
        return [{"id": "1", "subject": "Hi", "from": "A"}]

    async def thread(tid):
        return {"thread_id": tid, "messages": [{"from": "A", "subject": "Hi", "date": "d", "body": "text", "message_id_header": "<x>", "references": "r"}]}
    monkeypatch.setattr(gmail, "search", search)
    monkeypatch.setattr(gmail, "get_thread", thread)
    priya = linked(await make_actor(seeded))
    out, ctx = await call(tool("search_mail"), priya)
    assert out["ok"] and out["count"] == 1 and "untrusted" in out["caution"] and ctx.ui[0]["card"] == "mail_list"
    out, ctx = await call(tool("read_mail_thread"), priya, thread_id="T")
    assert out["ok"] and "message_id_header" not in out["messages"][0] and "references" not in out["messages"][0]
    assert ctx.ui[0]["card"] == "mail_thread" and set(ctx.ui[0]["messages"][0]) == {"from", "subject", "date", "body"}


async def test_google_outage_in_tool_is_graceful(seeded, monkeypatch):
    async def boom(q, n):
        raise auth.GoogleError("Google token refresh failed (500).")
    monkeypatch.setattr(gmail, "search", boom)
    out, _ = await call(tool("search_mail"), linked(await make_actor(seeded)))
    assert out["ok"] is False and out["code"] == "GOOGLE_UNAVAILABLE" and "Purser inbox" in out["message"]


async def test_propose_email_creates_proposal_card(seeded):
    priya = linked(await make_actor(seeded))
    out, ctx = await call(tool("propose_email"), priya, body="Hello", to=["a@b.com"], subject="S")
    assert out["ok"] is True and ctx.ui[0]["card"] == "proposal"
    out, ctx = await call(tool("propose_email"), priya, body="Hello", to=["bad"], subject="S")
    assert out["ok"] is False and out["code"] == VALIDATION
    assert await ops() == []  # proposing never queues anything


async def test_save_mail_draft_new_requires_to_and_subject(seeded, monkeypatch):
    drafts = []

    async def create(sender, to, subject, body, **kw):
        drafts.append((sender, to, subject, body))
        return {"id": "D1"}
    monkeypatch.setattr(gmail, "create_draft", create)
    priya = linked(await make_actor(seeded))
    out, _ = await call(tool("save_mail_draft"), priya, body="b")
    assert out["ok"] is False and out["code"] == VALIDATION and drafts == []
    out, _ = await call(tool("save_mail_draft"), priya, body="b", to=["a@b.com"], subject="s")
    assert out["ok"] and out["draft_id"] == "D1" and drafts == [(LINKED, ["a@b.com"], "s", "b")]


async def test_list_meetings_demo_users_see_only_their_own(seeded):
    async with db.session_scope() as s:
        await seed_roles(s)
    ceo = await actor_by_email("irfan@dzruptiv.ai")
    emp = await actor_by_email("ia383813@gmail.com")
    today = today_ist().isoformat()
    tomorrow = (today_ist() + timedelta(days=1)).isoformat()
    t = tool("list_meetings")
    out, ctx = await call(t, ceo, on=today)
    assert out["ok"] and out["source"] == "purser"
    # the CEO organises two and is also an attendee of the employee's pipeline review
    assert sorted(m["title"] for m in out["meetings"]) == ["Board pre-read review", "Q3 sales pipeline review", "Weekly leadership sync"]
    assert ctx.ui[0]["card"] == "meetings" and ctx.ui[0]["source"] == "purser"
    out, _ = await call(t, emp, on=today)
    assert sorted(m["title"] for m in out["meetings"]) == ["Q3 sales pipeline review", "Weekly leadership sync"]
    out, _ = await call(t, emp, on=tomorrow)
    assert [m["title"] for m in out["meetings"]] == ["Client call: Nimbus Retail renewal"]
    out, _ = await call(t, ceo, on=tomorrow)
    assert [m["title"] for m in out["meetings"]] == ["Investor update call"]
    out, _ = await call(t, await make_actor(seeded, "arjun"), on=today)
    assert out["count"] == 0 and out["note"].startswith("No meetings")


async def test_list_meetings_bad_date_and_ranges(seeded):
    arjun = await make_actor(seeded, "arjun")
    out, _ = await call(tool("list_meetings"), arjun, on="21/11/2026")
    assert out["ok"] is False and out["code"] == VALIDATION
    for rng, label in (("today", "today"), ("tomorrow", "tomorrow"), ("week", "the next 7 days"), ("upcoming", "the next two weeks")):
        out, _ = await call(tool("list_meetings"), arjun, range=rng)
        assert out["ok"] and out["range"] == label


async def test_list_meetings_linked_uses_google_calendar(seeded, monkeypatch):
    async def events(start, end, max_results=25):
        return [{"event_id": "g1", "title": "Real meeting"}]
    monkeypatch.setattr(gcal, "list_events", events)
    out, _ = await call(tool("list_meetings"), linked(await make_actor(seeded)))
    assert out["source"] == "google_calendar" and out["meetings"][0]["title"] == "Real meeting"
