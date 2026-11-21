"""B2 gate: login briefing (role sections, Today from agenda, degradation, rule-based next action, cache, API, tool)."""

import asyncio
from dataclasses import replace
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app import db
from app.agent.tools import finance as fin_tools
from app.models import Meeting, Task
from app.services import agenda, briefing
from app.services.google import gcal, gmail
from app.services.records import today_ist
from tests.b25_helpers import FAKE_GOOGLE, LINKED, linked, pin
from tests.conftest import make_actor
from tests.test_api_intake import client_for
from tests.test_intake_extra import call
from tests.test_people_extra import mail  # noqa: F401  (autouse safety fixture: no SMTP)

IST = ZoneInfo("Asia/Kolkata")
FINANCE_LABELS = {"Approvals waiting", "Overdue invoices", "Budget alerts", "Received this month", "Outstanding", "Overdue"}


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    briefing._cache.clear()
    pin(monkeypatch, google_client_id="", google_client_secret="", google_refresh_token="", google_linked_email="")

    import httpx
    real = httpx.AsyncClient

    def no_net(*a, **k):
        if "transport" not in k:  # in-process ASGI test clients are fine; anything else would hit the network
            raise AssertionError("a briefing test opened a real httpx client")
        return real(*a, **k)
    monkeypatch.setattr(httpx, "AsyncClient", no_net)
    yield
    briefing._cache.clear()


def sec(b, title):
    return next((s for s in b["sections"] if s.get("title") == title), None)


def kpi_labels(b):
    return [i["label"] for s in b["sections"] if s["type"] == "kpi_strip" for i in s["items"]]


async def add_task(actor, title, due, ref="T900"):
    async with db.session_scope() as s:
        s.add(Task(workspace_id=actor.workspace_id, ref=ref, title=title, assignee_id=actor.user_id, created_by=actor.user_id,
                   due_on=due, status="open"))


async def add_meeting(actor_org, title, att_ids, hh=12, ref="MTX1", day=None):
    day = day or today_ist()
    start = datetime.combine(day, time(hh, 0), tzinfo=IST)
    async with db.session_scope() as s:
        s.add(Meeting(workspace_id=actor_org.workspace_id, ref=ref, kind="meeting", title=title, start_at=start, end_at=start + timedelta(minutes=30),
                      timezone="Asia/Kolkata", organizer_id=actor_org.user_id, attendee_user_ids=att_ids, guest_emails=[],
                      google_event_id=f"ev-{ref}-{title}"[:60], status="saved"))


# ------------------------------------------------------------------ role sections


async def test_admin_sections(seeded):
    b = await briefing.build(await make_actor(seeded, "priya"), fresh=True)
    assert b["role"] == "admin" and b["greeting"].startswith("Good ") and b["google"] is False
    assert "Approvals waiting" in kpi_labels(b)
    assert sec(b, "Priorities") is not None
    assert sec(b, "Risks to watch") is None
    assert b["sections"][0]["type"] == "kpi_strip"
    assert b["sections"][1]["title"] == "Today"


async def test_ceo_read_only_sections(seeded):
    ceo = replace(await make_actor(seeded, "priya"), role="ceo")
    b = await briefing.build(ceo, fresh=True)
    assert sec(b, "Risks to watch") is not None
    assert sec(b, "Priorities") is None
    labels = kpi_labels(b)
    assert "Approvals waiting" not in labels
    assert "Budget alerts" in labels and "People" in labels
    assert "Received this month" in labels, labels  # revenue KPIs for the CEO
    blob = str(b["next_action"]).lower()
    assert "approval" not in blob
    assert b["sections"][1]["title"] == "Today"


async def test_employee_sections_have_no_finance(seeded):
    b = await briefing.build(await make_actor(seeded, "arjun"), fresh=True)
    assert set(kpi_labels(b)) == {"Open tasks", "Leave available", "Claims in progress", "Unread inbox"}
    titles = [s.get("title") for s in b["sections"]]
    assert titles == [None, "Today", "My tasks", "My requests", "Your routines"]  # routines section added by custom workflows
    assert not (set(kpi_labels(b)) & FINANCE_LABELS)
    assert sec(b, "Priorities") is None and sec(b, "Risks to watch") is None
    blob = str(b)
    for forbidden in ("Budget", "Received this month", "Outstanding", "Approvals waiting", "Risks to watch"):
        assert forbidden not in blob, forbidden


async def test_employee_tasks_and_overdue_next_action(seeded):
    arjun = await make_actor(seeded, "arjun")
    await add_task(arjun, "File the GST sheet", today_ist() - timedelta(days=2))
    b = await briefing.build(arjun, fresh=True)
    items = sec(b, "My tasks")["items"]
    assert items[0]["title"] == "File the GST sheet" and items[0]["sub"].startswith("Overdue since") and items[0]["tone"] == "warn"
    assert items[0]["utterance"] == "Mark task T900 as done"
    assert next(i for s in b["sections"] if s["type"] == "kpi_strip" for i in s["items"] if i["label"] == "Open tasks")["value"] == "1"
    # rule-based pick: overdue task (score 85) wins; no OPENAI key so picked_by never appears
    assert b["next_action"]["title"] == "Finish “File the GST sheet”"
    assert "due" in b["next_action"]["why"]
    assert set(b["next_action"]) <= {"title", "why", "utterance"}


async def test_next_action_none_when_nothing_to_do(seeded):
    assert await briefing._pick([], "employee") is None


async def test_pick_survives_model_failure(seeded, monkeypatch):
    """A key is present but the model call blows up: fall back to the top rule candidate, never raise."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    import openai

    class Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("no network in tests")
    monkeypatch.setattr(openai, "AsyncOpenAI", Boom)
    got = await briefing._pick([{"score": 10, "title": "low", "why": "w"}, {"score": 90, "title": "high", "why": "w"}], "admin")
    assert got["title"] == "high"


# ------------------------------------------------------------------ Today from agenda (DB meetings for non-Google users)


async def test_today_lists_organizer_and_attendee_meetings_only(seeded):
    priya, arjun = await make_actor(seeded, "priya"), await make_actor(seeded, "arjun")
    await add_meeting(priya, "Priya with Arjun", [arjun.user_id], 12, "MTA")
    await add_meeting(priya, "Priya solo", [], 13, "MTB")
    await add_meeting(arjun, "Arjun own", [], 14, "MTC")
    b = await briefing.build(arjun, fresh=True)
    today = sec(b, "Today")
    assert today["source"] == "purser"
    assert [i["title"] for i in today["items"]] == ["Priya with Arjun", "Arjun own"]
    assert b["sections"][1] is today
    b2 = await briefing.build(priya, fresh=True)
    assert [i["title"] for i in sec(b2, "Today")["items"]] == ["Priya with Arjun", "Priya solo"]


async def test_today_empty_message(seeded):
    b = await briefing.build(await make_actor(seeded, "arjun"), fresh=True)
    assert sec(b, "Today")["items"] == [] and sec(b, "Today")["empty"] == "No meetings today."


async def test_agenda_other_day_excluded(seeded):
    arjun = await make_actor(seeded, "arjun")
    await add_meeting(arjun, "Tomorrow thing", [], 10, "MTD", day=today_ist() + timedelta(days=1))
    b = await briefing.build(arjun, fresh=True)
    assert sec(b, "Today")["items"] == []
    start = datetime.combine(today_ist() + timedelta(days=1), time.min, tzinfo=IST)
    ev, src = await agenda.meetings(arjun, start, start + timedelta(days=1))
    assert [e["title"] for e in ev] == ["Tomorrow thing"] and src == "purser"
    assert ev[0]["organizer"] == arjun.display_name and ev[0]["all_day"] is False


# ------------------------------------------------------------------ degradation


async def test_calendar_failure_degrades_to_note(seeded, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("calendar exploded")
    monkeypatch.setattr(agenda, "meetings", boom)
    b = await briefing.build(await make_actor(seeded, "arjun"), fresh=True)
    assert "Calendar unavailable right now" in b["notes"]
    t = sec(b, "Today")
    assert t["source"] == "unavailable" and t["items"] == [] and t["empty"] == "Calendar unavailable right now."


async def test_calendar_timeout_degrades(seeded, monkeypatch):
    async def slow(*a, **k):
        await asyncio.sleep(2)
    monkeypatch.setattr(agenda, "meetings", slow)
    monkeypatch.setattr(briefing, "GOOGLE_TIMEOUT", 0.05)
    b = await briefing.build(await make_actor(seeded, "arjun"), fresh=True)
    assert any("Calendar" in n for n in b["notes"]) and sec(b, "Today")["source"] == "unavailable"


async def test_linked_user_google_failures_are_notes(seeded, monkeypatch):
    pin(monkeypatch, **FAKE_GOOGLE)
    priya = linked(await make_actor(seeded, "priya"))

    async def cal_boom(*a, **k):
        raise RuntimeError("calendar 500")

    async def mail_boom(*a, **k):
        raise RuntimeError("gmail 500")
    monkeypatch.setattr(gcal, "list_events", cal_boom)
    monkeypatch.setattr(gmail, "search", mail_boom)
    b = await briefing.build(priya, fresh=True)
    assert b["google"] is True
    assert "Calendar unavailable right now" in b["notes"] and "Gmail unavailable right now" in b["notes"]
    assert sec(b, "Unread in Gmail") is None


async def test_linked_user_sees_google_calendar_and_mail(seeded, monkeypatch):
    pin(monkeypatch, **FAKE_GOOGLE)
    priya = linked(await make_actor(seeded, "priya"))
    soon = datetime.now(IST) + timedelta(minutes=30)

    async def events(start, end, max_results=25):
        return [{"event_id": "g1", "title": "Board call", "start": soon.isoformat(), "end": (soon + timedelta(minutes=30)).isoformat(),
                 "all_day": False, "meet_url": "https://meet.google.com/x", "attendees": []}]

    async def search(q, n=8):
        assert "is:unread" in q
        return [{"id": "m1", "from": "HDFC", "subject": "Statement", "important": True}]
    monkeypatch.setattr(gcal, "list_events", events)
    monkeypatch.setattr(gmail, "search", search)
    b = await briefing.build(priya, fresh=True)
    t = sec(b, "Today")
    assert t["source"] == "google_calendar" and t["items"][0]["title"] == "Board call" and t["items"][0]["meta"] == "Meet"
    assert sec(b, "Unread in Gmail")["items"][0]["title"] == "Statement"
    assert b["notes"] == []
    # meeting starting within the hour outranks admin approvals (90)
    assert b["next_action"]["title"] == "Get ready for “Board call”"


# ------------------------------------------------------------------ cache / spoken / tool / API


async def test_cache_60s_and_fresh_bypass(seeded):
    arjun = await make_actor(seeded, "arjun")
    b1 = await briefing.build(arjun, fresh=True)
    await add_task(arjun, "Late task", today_ist())
    assert await briefing.build(arjun) is b1  # cached object
    assert sec(b1, "My tasks")["items"] == []
    b3 = await briefing.build(arjun, fresh=True)
    assert [i["title"] for i in sec(b3, "My tasks")["items"]] == ["Late task"]
    assert await briefing.build(arjun) is b3
    # per user
    priya = await make_actor(seeded, "priya")
    assert (await briefing.build(priya))["role"] == "admin"


async def test_cache_expires(seeded, monkeypatch):
    arjun = await make_actor(seeded, "arjun")
    b1 = await briefing.build(arjun, fresh=True)
    ts, val = briefing._cache[arjun.user_id]
    briefing._cache[arjun.user_id] = (ts - briefing.CACHE_S - 1, val)
    assert await briefing.build(arjun) is not b1


async def test_spoken_is_compact(seeded):
    b = await briefing.build(await make_actor(seeded, "arjun"), fresh=True)
    sp = briefing.spoken(b)
    assert set(sp) == {"greeting", "next_action", "sections", "notes"}
    assert "Today" in sp["sections"] and "My tasks" in sp["sections"]
    assert all(len(v) <= 4 for v in sp["sections"].values())
    assert "utterance" not in str(sp["sections"])


async def test_get_briefing_tool_is_fresh(seeded):
    arjun = await make_actor(seeded, "arjun")
    out, _ = await call(fin_tools.get_briefing, arjun)
    assert out["ok"] is True and out["greeting"].startswith("Good ")
    await add_task(arjun, "Brand new task", today_ist())
    out2, _ = await call(fin_tools.get_briefing, arjun)
    assert "Brand new task" in out2["sections"]["My tasks"]


async def test_api_briefing_by_role(seeded):
    c = await client_for("arjun@purser.demo")
    r = await c.get("/api/briefing")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "employee" and "Open tasks" in kpi_labels(body)
    assert "Approvals waiting" not in kpi_labels(body)
    r2 = await c.get("/api/briefing?fresh=true")
    assert r2.status_code == 200
    c2 = await client_for("priya@purser.demo")
    assert "Approvals waiting" in kpi_labels((await c2.get("/api/briefing")).json())


async def test_api_briefing_requires_login(seeded):
    import httpx

    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as c:
        assert (await c.get("/api/briefing")).status_code == 401
