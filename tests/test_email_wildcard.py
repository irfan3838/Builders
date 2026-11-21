"""EMAIL_ALLOWED_RECIPIENTS="*" wildcard: email_plan, plan text, and the demo seed. No SMTP is ever touched
(the autouse `mail` fixture from test_people_extra swaps _send_smtp and makes smtplib.SMTP_SSL fail loudly)."""

import pytest
from sqlalchemy import select

from app import db
from app.models import User
from app.services import messaging
from app.services.actions import OnboardEmployee, SendMessage
from tests.conftest import make_actor
from tests.test_demo_seed import _wipe_and_seed
from tests.test_people_extra import mail  # noqa: F401  (autouse safety fixture)


@pytest.mark.parametrize("notify,allow,expect", [
    ("anyone@random.org", ["*"], ("anyone@random.org", "deliverable")),
    ("Anyone@Random.ORG ", ["*"], ("anyone@random.org", "deliverable")),
    ("zed@y.com", ["a@x.com", "*"], ("zed@y.com", "deliverable")),
    ("a@x.com", ["a@x.com", "*"], ("a@x.com", "deliverable")),
    ("zed@y.com", ["a@x.com"], ("zed@y.com", "not_on_allowlist")),
])
async def test_email_plan_wildcard(mail, notify, allow, expect):  # noqa: F811
    mail.enable(*allow)
    assert messaging.email_plan(User(notify_email=notify)) == expect


@pytest.mark.parametrize("notify", [None, "", "   "])
async def test_wildcard_without_notify_email_is_no_email(mail, notify):  # noqa: F811
    mail.enable("*")
    assert messaging.email_plan(User(notify_email=notify)) == (None, "no_email")


async def test_wildcard_but_email_not_configured(mail, monkeypatch):  # noqa: F811
    from app.config import get_settings
    st = get_settings().model_copy(update={"gmail_address": "", "gmail_app_password": "", "email_allowed_recipients": "*"})
    monkeypatch.setattr(messaging, "get_settings", lambda: st)
    assert messaging.email_plan(User(notify_email="a@x.com")) == ("a@x.com", "email_not_configured")


async def test_send_message_plan_reports_wildcard_email_deliverable(seeded, mail):  # noqa: F811
    ids = seeded
    priya = await make_actor(ids)
    mail.enable("*")
    async with db.session_scope() as s:
        (await s.get(User, ids["arjun_id"])).notify_email = "arjun@anywhere.test"
        plan = await SendMessage().plan(s, priya, {"audience": "person", "user_ids": [ids["arjun_id"]], "body": "hi", "channels": ["inbox", "email"]})
    text = "\n".join(plan.lines)
    assert "Email: 1 will be emailed; 0 get the inbox copy only." in text
    assert mail.sent == []


async def test_send_message_plan_without_wildcard_not_deliverable(seeded, mail):  # noqa: F811
    ids = seeded
    priya = await make_actor(ids)
    mail.enable("other@x.com")
    async with db.session_scope() as s:
        (await s.get(User, ids["arjun_id"])).notify_email = "arjun@anywhere.test"
        plan = await SendMessage().plan(s, priya, {"audience": "person", "user_ids": [ids["arjun_id"]], "body": "hi", "channels": ["inbox", "email"]})
    assert "Email: 0 will be emailed; 1 get the inbox copy only" in "\n".join(plan.lines)


async def test_onboard_plan_wildcard_welcome_email(seeded, mail):  # noqa: F811
    priya = await make_actor(seeded)
    mail.enable("*")
    async with db.session_scope() as s:
        plan = await OnboardEmployee().plan(s, priya, {"name": "Ravi Kumar", "personal_email": "ravi@home.test", "start_date": "2026-12-01"})
    assert "welcome email to ravi@home.test" in "\n".join(plan.lines)


async def _notify(monkeypatch, allow: str):
    monkeypatch.setenv("EMAIL_ALLOWED_RECIPIENTS", allow)
    ids = await _wipe_and_seed()
    try:
        async with db.session_scope() as s:
            return {u.display_name: u.notify_email for u in (await s.execute(select(User))).scalars()}
    finally:
        await db.engine().dispose()


@pytest.mark.parametrize("allow,arjun,neha", [
    ("*", None, None),
    ("*,a@x.com,b@x.com", "a@x.com", "b@x.com"),
    ("a@x.com,*,b@x.com", "a@x.com", "b@x.com"),
    ("a@x.com", "a@x.com", None),
    ("", None, None),
])
async def test_seed_ignores_wildcard_as_address(monkeypatch, allow, arjun, neha):
    n = await _notify(monkeypatch, allow)
    assert (n["Arjun Mehta"], n["Neha Iyer"]) == (arjun, neha)
    assert "*" not in n.values()
