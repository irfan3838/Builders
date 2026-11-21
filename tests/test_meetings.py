"""Schedule-meeting coverage: validation, plan text, execute, calendar dispatch, event body, Google HTTP via MockTransport.

No test reaches real Google: settings are pinned in an autouse fixture (the .env GOOGLE_* values are never used),
`calendar.create_event` is replaced in every dispatch test, and httpx.AsyncClient is swapped for a MockTransport client
in the HTTP-level tests."""

import dataclasses
import smtplib
from datetime import UTC, datetime

import httpx
import pytest
from sqlalchemy import select

import app.config as config_mod
from app import db
from app.agent.tools import people as people_tools
from app.config import get_settings
from app.errors import VALIDATION, DomainError
from app.models import AuditEvent, Meeting, Message, User
from app.services import actions, calendar, messaging
from tests.conftest import make_actor
from tests.test_intake_extra import call
from tests.test_ledger_gates import propose_and_confirm
from tests.test_people_extra import count

_REAL_CREATE = calendar.create_event
_REAL_CLIENT = httpx.AsyncClient
FUTURE = "2027-03-15T10:00"
LINKED = "priya.linked@test.invalid"
FAKE = {"google_client_id": "cid", "google_client_secret": "csecret", "google_refresh_token": "rtoken",
        "google_linked_email": LINKED}


def linked(actor):
    """The organizer is the Google-linked login (Actor.uses_google), so events are really created."""
    return dataclasses.replace(actor, email=LINKED.upper())
OFF = {"google_client_id": "", "google_client_secret": "", "google_refresh_token": ""}


def pin(mp, **update):
    patched = get_settings().model_copy(update={"calendar_timezone": "Asia/Kolkata", **update})
    mp.setattr(config_mod, "get_settings", lambda: patched)
    mp.setattr(calendar, "get_settings", lambda: patched)
    return patched


@pytest.fixture(autouse=True)
def cal(monkeypatch):
    """Calendar disabled by default; a test calls pin(monkeypatch, **FAKE) to enable. Also forbid network and SMTP."""
    pin(monkeypatch, **OFF)
    sent = []

    async def no_network(m):
        raise AssertionError("a test reached the real create_event")

    monkeypatch.setattr(calendar, "create_event", no_network)

    def boom(*a, **k):
        raise AssertionError("real SMTP attempted")

    monkeypatch.setattr(smtplib, "SMTP_SSL", boom)
    monkeypatch.setattr(messaging, "_send_smtp", lambda to, subj, body: sent.append(to) or f"<id-{len(sent)}>")
    monkeypatch.setattr(messaging, "dispatch_soon", lambda: None)

    def blocked(*a, **k):
        raise AssertionError("a test opened a real httpx client")

    monkeypatch.setattr(calendar.httpx, "AsyncClient", blocked)
    return sent


def args(**kw):
    base = {"title": "Sync", "start": FUTURE, "guest_emails": ["a@x.com"]}
    base.update(kw)
    return base


async def code_for(actor, a):
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await actions.ACTIONS["schedule_meeting"].plan(s, actor, a)
    assert e.value.code == VALIDATION
    return str(e.value)


async def meetings():
    async with db.session_scope() as s:
        return list((await s.execute(select(Meeting).order_by(Meeting.id))).scalars())


# ------------------------------------------------------------------ validation


async def test_validation_cases(seeded):
    priya = await make_actor(seeded)
    assert "title" in (await code_for(priya, args(title="   "))).lower()
    assert "too long" in await code_for(priya, args(title="x" * 151))
    assert "Start time" in await code_for(priya, args(start="garbage"))
    assert "Start time" in await code_for(priya, {"title": "t", "guest_emails": ["a@x.com"]})
    assert "passed" in await code_for(priya, args(start="2020-01-01T10:00"))
    assert "Duration" in await code_for(priya, args(duration_minutes=5))
    assert "Duration" in await code_for(priya, args(duration_minutes=481))
    assert "Duration" in await code_for(priya, args(duration_minutes="abc"))
    assert "not a valid email" in await code_for(priya, args(guest_emails=["nope"]))
    assert "at least one attendee" in await code_for(priya, args(guest_emails=[]))
    assert "Too many" in await code_for(priya, args(guest_emails=[f"g{i}@x.com" for i in range(26)]))


async def test_duration_bounds_and_defaults_are_accepted(seeded):
    priya = await make_actor(seeded)
    for kw in ({"duration_minutes": 10}, {"duration_minutes": 480}, {}):
        async with db.session_scope() as s:
            plan = await actions.ACTIONS["schedule_meeting"].plan(s, priya, args(**kw))
        assert plan.title == "Schedule meeting"
    async with db.session_scope() as s:
        plan = await actions.ACTIONS["schedule_meeting"].plan(s, priya, args(kind="interview"))
    assert plan.title == "Schedule interview" and plan.lines[0].startswith("Interview:")
    assert "(30 min, Asia/Kolkata)" in plan.lines[1]


async def test_unknown_colleague_is_rejected(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        with pytest.raises(DomainError):
            await actions.ACTIONS["schedule_meeting"].plan(s, priya, args(user_ids=[99999]))


# ------------------------------------------------------------------ plan text


async def test_plan_text_disabled_vs_enabled(seeded, monkeypatch):
    ids, priya = seeded, await make_actor(seeded)
    async with db.session_scope() as s:
        (await s.get(User, ids["arjun_id"])).notify_email = "Arjun@Test.Invalid"
        (await s.get(User, ids["neha_id"])).notify_email = None  # seed may fill it from .env
    a = args(user_ids=[ids["arjun_id"], ids["neha_id"]], guest_emails=["Cand@X.com"])
    async with db.session_scope() as s:
        off = await actions.ACTIONS["schedule_meeting"].plan(s, priya, a)
    assert any("only for the linked Google account" in ln for ln in off.lines) and not any("Google Meet link;" in ln for ln in off.lines)
    pin(monkeypatch, **FAKE)
    async with db.session_scope() as s:
        on = await actions.ACTIONS["schedule_meeting"].plan(s, linked(priya), a)
    invite_line = next(ln for ln in on.lines if "Google emails the invite" in ln)
    assert "cand@x.com" in invite_line and "arjun@test.invalid" in invite_line
    assert any("No email on file for Neha Iyer" in ln for ln in on.lines)
    assert "Arjun Mehta" in on.lines[2] and "Neha Iyer" in on.lines[2] and "cand@x.com" in on.lines[2]


# ------------------------------------------------------------------ execute


async def test_execute_skipped_when_calendar_not_configured(seeded):
    priya = await make_actor(seeded)
    p, out = await propose_and_confirm(priya, "schedule_meeting", args(description="  bring CV  "))
    assert out.status == "executed"
    [m] = await meetings()
    assert (m.status, m.status_detail, m.ref) == ("skipped", "calendar_not_configured", f"MT{m.id}")
    assert m.description == "bring CV" and m.guest_emails == ["a@x.com"] and m.timezone == "Asia/Kolkata"
    assert m.organizer_id == priya.user_id and (m.end_at - m.start_at).seconds == 1800
    assert m.start_at.astimezone(UTC).hour == 4 and m.start_at.astimezone(UTC).minute == 30  # 10:00 IST
    assert len(m.google_event_id) == 32
    async with db.session_scope() as s:
        ev = (await s.execute(select(AuditEvent).where(AuditEvent.record_type == "meeting"))).scalars().all()
    assert len(ev) == 1 and ev[0].action == "meeting.scheduled"
    assert await count(Message, Message.kind == "meeting") == 0  # nothing dispatched or notified


async def test_execute_queued_dedupes_and_lowercases_invites(seeded, monkeypatch):
    ids, priya = seeded, linked(await make_actor(seeded))
    pin(monkeypatch, **FAKE)
    async with db.session_scope() as s:
        (await s.get(User, ids["arjun_id"])).notify_email = "Arjun@Test.Invalid"
    _, out = await propose_and_confirm(priya, "schedule_meeting", args(
        kind="interview", user_ids=[ids["arjun_id"], ids["arjun_id"]], guest_emails=["ARJUN@test.invalid", "c@x.com"]))
    assert out.status == "executed"
    [m] = await meetings()
    assert m.status == "queued" and m.status_detail is None and m.kind == "interview"
    assert m.guest_emails == ["arjun@test.invalid", "c@x.com"] and m.attendee_user_ids == [ids["arjun_id"]]
    assert out.receipt.effects[0]["status"] == "queued"


async def test_non_linked_organizer_is_skipped_even_when_calendar_enabled(seeded, monkeypatch):
    priya = dataclasses.replace(await make_actor(seeded), email="someone.else@test.invalid")
    pin(monkeypatch, **FAKE)
    await propose_and_confirm(priya, "schedule_meeting", args())
    [m] = await meetings()
    assert m.status == "skipped"


async def test_each_execute_gets_a_distinct_event_id(seeded):
    priya = await make_actor(seeded)
    await propose_and_confirm(priya, "schedule_meeting", args())
    await propose_and_confirm(priya, "schedule_meeting", args())
    a, b = await meetings()
    assert a.google_event_id != b.google_event_id and a.ref != b.ref


# ------------------------------------------------------------------ dispatch


async def queue_meeting(ids, priya, monkeypatch, **kw):
    pin(monkeypatch, **FAKE)
    await propose_and_confirm(linked(priya), "schedule_meeting", args(**kw))
    return (await meetings())[-1]


async def test_dispatch_success_stores_link_and_notifies_without_duplicates(seeded, monkeypatch):
    ids, priya = seeded, await make_actor(seeded)
    await queue_meeting(ids, priya, monkeypatch, user_ids=[ids["arjun_id"], ids["priya_id"], ids["arjun_id"]],
                        description="Agenda")
    calls = []

    async def fake(m):
        calls.append(m.google_event_id)
        return "https://meet.google.com/abc-defg-hij", "https://calendar.google.com/event?eid=1"

    monkeypatch.setattr(calendar, "create_event", fake)
    assert await calendar.dispatch() == 1
    [m] = await meetings()
    assert (m.status, m.status_detail, m.meet_url) == ("created", None, "https://meet.google.com/abc-defg-hij")
    assert m.event_url.startswith("https://calendar.google.com")
    async with db.session_scope() as s:
        msgs = (await s.execute(select(Message).where(Message.kind == "meeting"))).scalars().all()
    assert sorted(x.recipient_user_id for x in msgs) == sorted([ids["priya_id"], ids["arjun_id"]])
    for x in msgs:
        assert x.channel == "inbox" and x.status == "delivered" and x.ref == f"M{x.id}" and x.sender_id == ids["priya_id"]
        assert x.subject == "Meeting: Sync" and "https://meet.google.com/abc-defg-hij" in x.body and "Agenda" in x.body
    assert await calendar.dispatch() == 0 and len(calls) == 1  # idempotent: created rows are not picked again


async def test_dispatch_without_meet_link_flags_detail(seeded, monkeypatch):
    ids, priya = seeded, await make_actor(seeded)
    await queue_meeting(ids, priya, monkeypatch, user_ids=[ids["arjun_id"]], kind="interview")

    async def fake(m):
        return None, "https://cal/e"

    monkeypatch.setattr(calendar, "create_event", fake)
    assert await calendar.dispatch() == 1
    [m] = await meetings()
    assert m.status == "created" and m.status_detail == "event created without a Meet link" and m.meet_url is None
    async with db.session_scope() as s:
        msgs = (await s.execute(select(Message).where(Message.kind == "meeting"))).scalars().all()
    assert all("Google Meet" not in x.body and x.subject == "Interview: Sync" for x in msgs)


async def test_dispatch_failure_marks_failed_and_email_still_sends(seeded, monkeypatch, cal):
    ids, priya = seeded, await make_actor(seeded)
    await queue_meeting(ids, priya, monkeypatch, user_ids=[ids["arjun_id"]])
    async with db.session_scope() as s:
        s.add(Message(workspace_id=1, ref="M900", kind="message", channel="email", sender_id=ids["priya_id"],
                      recipient_user_id=ids["arjun_id"], email_to="arjun@test.invalid", subject="Hi", body="b", status="queued"))

    async def fail(m):
        raise calendar.CalendarError("Google Calendar HTTP 403: nope")

    monkeypatch.setattr(calendar, "create_event", fail)
    assert await messaging.dispatch() == 1  # the email was sent even though calendar failed
    assert cal == ["arjun@test.invalid"]
    [m] = await meetings()
    assert m.status == "failed" and m.status_detail == "CalendarError: Google Calendar HTTP 403: nope" and m.meet_url is None
    assert await count(Message, Message.kind == "meeting") == 0
    assert await calendar.dispatch() == 0  # failed meetings are not retried automatically


async def test_messaging_dispatch_survives_calendar_dispatch_crash(seeded, monkeypatch, cal):
    ids = seeded
    async with db.session_scope() as s:
        s.add(Message(workspace_id=1, ref="M901", kind="message", channel="email", sender_id=ids["priya_id"],
                      recipient_user_id=ids["arjun_id"], email_to="arjun@test.invalid", subject="Hi", body="b", status="queued"))

    async def explode(limit=10):
        raise RuntimeError("calendar down")

    monkeypatch.setattr(calendar, "dispatch", explode)
    assert await messaging.dispatch() == 1 and cal == ["arjun@test.invalid"]


async def test_dispatch_noop_when_calendar_disabled(seeded, monkeypatch):
    ids, priya = seeded, await make_actor(seeded)
    await queue_meeting(ids, priya, monkeypatch)
    pin(monkeypatch, **OFF)  # create_event is the "no network" bomb: reaching it would raise and mark failed
    assert await calendar.dispatch() == 0
    [m] = await meetings()
    assert m.status == "queued"


async def test_dispatch_respects_limit_and_order(seeded, monkeypatch):
    ids, priya = seeded, await make_actor(seeded)
    for t in ("A", "B", "C"):
        await queue_meeting(ids, priya, monkeypatch, title=t)
    order = []

    async def fake(m):
        order.append(m.title)
        return "https://meet/x", None

    monkeypatch.setattr(calendar, "create_event", fake)
    assert await calendar.dispatch(limit=2) == 2 and order == ["A", "B"]
    assert [m.status for m in await meetings()] == ["created", "created", "queued"]


# ------------------------------------------------------------------ pure helpers


def make_meeting(**kw):
    base = dict(title="Sync", description=None, timezone="Asia/Kolkata", google_event_id="ev123",
                start_at=datetime(2027, 3, 15, 4, 30, tzinfo=UTC), end_at=datetime(2027, 3, 15, 5, 0, tzinfo=UTC),
                guest_emails=["a@x.com", "b@x.com"])
    base.update(kw)
    return Meeting(**base)


def test_event_body_shape():
    b = calendar.event_body(make_meeting())
    assert b["id"] == "ev123" and b["summary"] == "Sync" and b["description"] == "Scheduled by Purser."
    assert b["attendees"] == [{"email": "a@x.com"}, {"email": "b@x.com"}]
    assert b["start"] == {"dateTime": "2027-03-15T04:30:00+00:00", "timeZone": "Asia/Kolkata"}
    assert b["end"]["timeZone"] == "Asia/Kolkata"
    assert b["conferenceData"] == {"createRequest": {"requestId": "ev123", "conferenceSolutionKey": {"type": "hangoutsMeet"}}}
    assert calendar.event_body(make_meeting(description="Agenda"))["description"] == "Agenda\n\nScheduled by Purser."


def test_meet_url_fallbacks():
    assert calendar._meet_url({"hangoutLink": "https://meet/a", "conferenceData": {"entryPoints": [
        {"entryPointType": "video", "uri": "https://meet/b"}]}}) == "https://meet/a"
    assert calendar._meet_url({"conferenceData": {"entryPoints": [
        {"entryPointType": "phone", "uri": "tel:1"}, {"entryPointType": "video", "uri": "https://meet/b"}]}}) == "https://meet/b"
    assert calendar._meet_url({"conferenceData": {"entryPoints": [{"entryPointType": "phone", "uri": "tel:1"}]}}) is None
    assert calendar._meet_url({"conferenceData": None}) is None
    assert calendar._meet_url({}) is None


def test_when_text_uses_meeting_timezone():
    assert calendar.when_text(make_meeting()) == "Mon 15 Mar 2027, 10:00 AM to 10:30 AM"


def test_is_future():
    assert calendar.is_future(datetime(2099, 1, 1, tzinfo=UTC)) and not calendar.is_future(datetime(2000, 1, 1, tzinfo=UTC))


def test_calendar_enabled_rules(monkeypatch):
    base = get_settings()
    on = base.model_copy(update=FAKE)
    assert on.calendar_enabled
    assert not base.model_copy(update={**FAKE, "google_client_id": "replace-me"}).calendar_enabled
    assert not base.model_copy(update={**FAKE, "google_refresh_token": "replace-me"}).calendar_enabled
    assert not base.model_copy(update={**FAKE, "google_client_secret": ""}).calendar_enabled
    assert not base.model_copy(update=OFF).calendar_enabled


def test_settings_strip_google_values():
    from app.config import Settings
    s = Settings(google_client_id="  id  ", google_client_secret=" s ", google_refresh_token=" r ")
    assert (s.google_client_id, s.google_client_secret, s.google_refresh_token) == ("id", "s", "r") and s.calendar_enabled


# ------------------------------------------------------------------ Google HTTP (MockTransport, no network)


def route(monkeypatch, handler):
    real = _REAL_CLIENT
    seen = []

    def wrapped(request):
        seen.append(request)
        return handler(request)

    monkeypatch.setattr(calendar.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(wrapped)))
    return seen


TOKEN = httpx.Response(200, json={"access_token": "tok"})


async def test_create_event_posts_with_bearer_and_returns_links(monkeypatch):
    pin(monkeypatch, **FAKE)

    def handler(req):
        if req.url.host == "oauth2.googleapis.com":
            assert b"refresh_token=rtoken" in req.content
            return TOKEN
        assert req.headers["authorization"] == "Bearer tok" and req.method == "POST"
        assert req.url.params["conferenceDataVersion"] == "1" and req.url.params["sendUpdates"] == "all"
        return httpx.Response(200, json={"hangoutLink": "https://meet/z", "htmlLink": "https://cal/z"})

    route(monkeypatch, handler)
    monkeypatch.setattr(calendar, "create_event", _REAL_CREATE)
    assert await calendar.create_event(make_meeting()) == ("https://meet/z", "https://cal/z")


async def test_create_event_409_fetches_existing_event(monkeypatch):
    pin(monkeypatch, **FAKE)

    def handler(req):
        if req.url.host == "oauth2.googleapis.com":
            return TOKEN
        if req.method == "POST":
            return httpx.Response(409, json={"error": {"message": "exists"}})
        assert req.method == "GET" and req.url.path.endswith("/events/ev123")
        return httpx.Response(200, json={"hangoutLink": "https://meet/old", "htmlLink": "https://cal/old"})

    seen = route(monkeypatch, handler)
    monkeypatch.setattr(calendar, "create_event", _REAL_CREATE)
    assert await calendar.create_event(make_meeting()) == ("https://meet/old", "https://cal/old")
    assert [r.method for r in seen] == ["POST", "POST", "GET"]


async def test_create_event_http_error_raises_calendar_error(monkeypatch):
    pin(monkeypatch, **FAKE)
    route(monkeypatch, lambda req: TOKEN if req.url.host == "oauth2.googleapis.com"
          else httpx.Response(403, json={"error": {"message": "Forbidden thing"}}))
    monkeypatch.setattr(calendar, "create_event", _REAL_CREATE)
    with pytest.raises(calendar.CalendarError, match="HTTP 403: Forbidden thing"):
        await calendar.create_event(make_meeting())


async def test_invalid_grant_maps_to_clear_error(monkeypatch):
    pin(monkeypatch, **FAKE)
    route(monkeypatch, lambda req: httpx.Response(400, json={"error": "invalid_grant"}))
    monkeypatch.setattr(calendar, "create_event", _REAL_CREATE)
    with pytest.raises(calendar.CalendarError, match="expired or was revoked"):
        await calendar.create_event(make_meeting())


async def test_other_token_failure_and_non_json_body(monkeypatch):
    pin(monkeypatch, **FAKE)
    monkeypatch.setattr(calendar, "create_event", _REAL_CREATE)
    route(monkeypatch, lambda req: httpx.Response(401, json={"error": "invalid_client"}))
    with pytest.raises(calendar.CalendarError, match=r"token refresh failed \(invalid_client\)"):
        await calendar.create_event(make_meeting())
    route(monkeypatch, lambda req: httpx.Response(502, text="<html>bad gateway</html>"))
    with pytest.raises(calendar.CalendarError, match=r"token refresh failed \(502\)"):
        await calendar.create_event(make_meeting())


async def test_dispatch_records_invalid_grant_as_failed(seeded, monkeypatch):
    ids, priya = seeded, await make_actor(seeded)
    await queue_meeting(ids, priya, monkeypatch)
    route(monkeypatch, lambda req: httpx.Response(400, json={"error": "invalid_grant"}))
    monkeypatch.setattr(calendar, "create_event", _REAL_CREATE)
    assert await calendar.dispatch() == 0
    [m] = await meetings()
    assert m.status == "failed" and "scripts/google_oauth.py" in m.status_detail


# ------------------------------------------------------------------ agent tool + full flow


def test_propose_meeting_registered_in_tools():
    assert people_tools.propose_meeting in people_tools.TOOLS
    assert "propose_meeting" in [t.name for t in people_tools.TOOLS]


async def test_propose_meeting_tool_then_confirm_flow(seeded, monkeypatch):
    ids, priya = seeded, linked(await make_actor(seeded))
    pin(monkeypatch, **FAKE)
    out, ctx = await call(people_tools.propose_meeting, priya, title="Interview Ravi", start=FUTURE, duration_minutes=45,
                          kind="interview", user_ids=[ids["arjun_id"]], guest_emails=["ravi@x.com"])
    assert out["ok"] and out["kind"] == "schedule_meeting" and ctx.ui[0]["card"] == "proposal"
    assert any("Interview: Interview Ravi" in ln for ln in out["preview"]) and await count(Meeting) == 0  # nothing before confirm
    from app.services import proposals
    async with db.session_scope() as s:
        await proposals.mark_presented(s, out["proposal_id"])
    async with db.session_scope() as s:
        res = await proposals.confirm(s, priya, out["proposal_id"], via="button")
    assert res.status == "executed"
    [m] = await meetings()
    assert (m.status, m.kind, m.title) == ("queued", "interview", "Interview Ravi") and (m.end_at - m.start_at).seconds == 2700

    async def fake(mm):
        return "https://meet/q", "https://cal/q"

    monkeypatch.setattr(calendar, "create_event", fake)
    assert await calendar.dispatch() == 1
    assert (await meetings())[0].meet_url == "https://meet/q"


async def test_propose_meeting_tool_returns_validation_error(seeded):
    priya = await make_actor(seeded)
    out, _ = await call(people_tools.propose_meeting, priya, title="x", start="2020-01-01T10:00", guest_emails=["a@x.com"])
    assert out["ok"] is False and out["code"] == VALIDATION and await count(Meeting) == 0


