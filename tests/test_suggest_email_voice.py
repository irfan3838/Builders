"""Suggestion chips tool, live voice prompt/config, and external email recipients for messages.
No SMTP and no OpenAI is touched (the `mail` fixture is autouse; the live client is faked)."""

import json
from types import SimpleNamespace

import httpx
import openai
import pytest
from sqlalchemy import func, select

from app import db
from app.agent import purser
from app.agent.context import PurserContext
from app.agent.tools import suggestions
from app.errors import DomainError
from app.models import Message, User
from app.services import messaging
from app.services.actions import SendMessage
from app.voice import live_bridge
from tests.conftest import make_actor
from tests.test_people_extra import mail  # noqa: F401  (autouse safety fixture)


# ------------------------------------------------------------------ 1. suggest_next_actions

async def _call(tool, ctx, **args):
    from agents.tool_context import ToolContext
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="call_1", tool_arguments=json.dumps(args))
    out = await tool.on_invoke_tool(tc, json.dumps(args))
    return json.loads(out) if isinstance(out, str) else out


async def _ctx(seeded):
    return PurserContext(actor=await make_actor(seeded))


def _items(*pairs):
    return [{"label": l, "utterance": u} for l, u in pairs]


async def test_suggestions_registered():
    assert suggestions.suggest_next_actions in purser.ALL_TOOLS


async def test_suggestions_caps_at_three(seeded):
    ctx = await _ctx(seeded)
    r = await _call(suggestions.suggest_next_actions, ctx, items=_items(*[(f"l{i}", f"u{i}") for i in range(6)]))
    assert r == {"ok": True, "shown": 3}
    assert len(ctx.ui) == 1 and ctx.ui[0]["card"] == "suggestions"
    assert [i["utterance"] for i in ctx.ui[0]["items"]] == ["u0", "u1", "u2"]


async def test_suggestions_trim_and_collapse_whitespace(seeded):
    ctx = await _ctx(seeded)
    label = "  word  " * 20
    utt = "a \n\t b   " + "x" * 300
    await _call(suggestions.suggest_next_actions, ctx, items=_items((label, utt)))
    it = ctx.ui[0]["items"][0]
    assert len(it["label"]) <= 40 and "  " not in it["label"] and it["label"] == " ".join(label.split())[:40]
    assert len(it["utterance"]) == 160 and it["utterance"].startswith("a b xxx")


async def test_suggestions_dedupe_utterances(seeded):
    ctx = await _ctx(seeded)
    r = await _call(suggestions.suggest_next_actions, ctx, items=_items(("A", "same"), ("B", "same"), ("C", " same "), ("D", "other")))
    assert r["shown"] == 2
    assert [i["label"] for i in ctx.ui[0]["items"]] == ["A", "D"]


@pytest.mark.parametrize("items", [[], _items(("", "x")), _items(("x", "")), _items(("  ", " \n ")), _items(("  ", "x"), ("y", "   "))])
async def test_suggestions_empty_is_error_no_card(seeded, items):
    ctx = await _ctx(seeded)
    r = await _call(suggestions.suggest_next_actions, ctx, items=items)
    assert r["ok"] is False and r["code"] == "EMPTY"
    assert ctx.ui == []


async def test_suggestions_second_call_replaces_only_suggestions(seeded):
    ctx = await _ctx(seeded)
    ctx.show({"card": "chart", "x": 1})
    await _call(suggestions.suggest_next_actions, ctx, items=_items(("one", "u1")))
    ctx.show({"card": "table", "y": 2})
    await _call(suggestions.suggest_next_actions, ctx, items=_items(("two", "u2")))
    assert [c["card"] for c in ctx.ui].count("suggestions") == 1
    assert [c["card"] for c in ctx.ui if c["card"] != "suggestions"] == ["chart", "table"]
    assert next(c for c in ctx.ui if c["card"] == "suggestions")["items"] == [{"label": "two", "utterance": "u2"}]


async def test_suggestions_failed_second_call_keeps_first(seeded):
    ctx = await _ctx(seeded)
    await _call(suggestions.suggest_next_actions, ctx, items=_items(("one", "u1")))
    await _call(suggestions.suggest_next_actions, ctx, items=_items(("", "")))
    assert len(ctx.ui) == 1 and ctx.ui[0]["items"][0]["utterance"] == "u1"


# ------------------------------------------------------------------ 2. voice prompt / config

def test_instructions_no_ek_second_filler():
    ins = live_bridge.FRONTEND_INSTRUCTIONS
    assert 'say at most a short filler like "ek second"' not in ins
    for line in ins.splitlines():
        if "ek second" in line:
            # allowed only as a prohibition, or as one example among varied fillers that must not repeat
            assert 'Never say "ek second"' in line or ("different one each time" in line and "Never repeat the filler" in line)


def _settings(monkeypatch, **kw):
    st = live_bridge.get_settings().model_copy(update=kw)
    monkeypatch.setattr(live_bridge, "get_settings", lambda: st)
    return st


def test_session_config_voice_and_speed(monkeypatch):
    st = _settings(monkeypatch, openai_voice_name="cedar", openai_voice_speed=1.2)
    out = live_bridge.session_config()["audio"]["output"]
    assert out == {"voice": "cedar", "speed": 1.2}
    assert live_bridge.session_config()["instructions"] == live_bridge.FRONTEND_INSTRUCTIONS
    assert live_bridge.session_config()["model"] == st.openai_model_voice


@pytest.mark.parametrize("raw,clamped", [(5.0, 1.5), (0.01, 0.25), (1.5, 1.5), (0.25, 0.25)])
def test_session_config_speed_clamped(monkeypatch, raw, clamped):
    _settings(monkeypatch, openai_voice_speed=raw)
    assert live_bridge.session_config()["audio"]["output"]["speed"] == clamped


@pytest.mark.parametrize("raw", [1.0, 0.0])
def test_session_config_no_speed_when_default_or_zero(monkeypatch, raw):
    _settings(monkeypatch, openai_voice_speed=raw)
    assert "speed" not in live_bridge.session_config()["audio"]["output"]


def test_session_config_with_speed_false(monkeypatch):
    _settings(monkeypatch, openai_voice_name="cedar", openai_voice_speed=1.3)
    assert live_bridge.session_config(with_speed=False)["audio"]["output"] == {"voice": "cedar"}


async def test_start_retries_without_speed(monkeypatch):
    _settings(monkeypatch, openai_voice_speed=1.3)
    calls = []

    class Live:
        async def create(self, *, session, transport):
            calls.append(session)
            if "speed" in session["audio"]["output"]:
                req = httpx.Request("POST", "http://x/live")
                raise openai.BadRequestError("bad speed", response=httpx.Response(400, request=req), body=None)
            return SimpleNamespace(session=SimpleNamespace(id="sess_1"), model_dump=lambda mode: {"ok": True})

    monkeypatch.setattr(live_bridge, "client", lambda: SimpleNamespace(live=Live()))

    conv = SimpleNamespace(live_session_id=None, channel="text")

    class FakeSession:
        async def get(self, model, pk):
            return conv

    class Scope:
        async def __aenter__(self):
            return FakeSession()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(live_bridge.db, "session_scope", lambda: Scope())

    class FakeBridge:
        def __init__(self, *a, **k):
            pass

        async def run(self):
            return None

    monkeypatch.setattr(live_bridge, "LiveBridge", FakeBridge)
    actor = SimpleNamespace(conversation_id="c-test-1")
    out = await live_bridge.start(actor, "v=0 sdp")
    assert out == {"ok": True}
    assert len(calls) == 2
    assert "speed" in calls[0]["audio"]["output"] and "speed" not in calls[1]["audio"]["output"]
    assert calls[1]["audio"]["output"]["voice"] == calls[0]["audio"]["output"]["voice"]
    assert (conv.live_session_id, conv.channel) == ("sess_1", "live")
    task = live_bridge._tasks.pop("c-test-1")
    await task


# ------------------------------------------------------------------ 3. external email recipients

async def _plan(ids, args, allow=None, mail_=None):
    actor = await make_actor(ids)
    async with db.session_scope() as s:
        return await SendMessage().plan(s, actor, {"audience": "person", "body": "hello", "subject": "Hi", **args})


async def _execute(ids, args):
    actor = await make_actor(ids)
    async with db.session_scope() as s:
        before = (await s.execute(select(func.coalesce(func.max(Message.id), 0)))).scalar_one()
    async with db.session_scope() as s:
        out = await SendMessage().execute(s, actor, {"audience": "person", "body": "hello", "subject": "Hi", **args}, None)
    async with db.session_scope() as s:
        rows = list((await s.execute(select(Message).where(Message.id > before).order_by(Message.id))).scalars())
    return out, rows


async def test_plan_external_allowed_wildcard_and_channel_added(seeded, mail):  # noqa: F811
    mail.enable("*")
    plan = await _plan(seeded, {"external_emails": ["Abc@Gmail.com "], "channels": ["inbox"]})
    text = "\n".join(plan.lines)
    assert "Email to abc@gmail.com: will be sent." in text
    assert "To: abc@gmail.com (1 person)." in text
    assert "Channels: Purser inbox + email." in text
    assert mail.sent == []


async def test_plan_external_not_on_allowlist(seeded, mail):  # noqa: F811
    mail.enable("someone@else.test")
    text = "\n".join((await _plan(seeded, {"external_emails": ["abc@gmail.com"]})).lines)
    assert "Email to abc@gmail.com: cannot be sent (not on the allow-list)." in text


async def test_plan_external_email_not_configured(seeded, mail):  # noqa: F811
    text = "\n".join((await _plan(seeded, {"external_emails": ["abc@gmail.com"]})).lines)
    assert "Email to abc@gmail.com: cannot be sent (email not configured)." in text


@pytest.mark.parametrize("bad", ["nope", "a@b", "a b@c.com", "@x.com", ""])
async def test_invalid_external_address_validation(seeded, mail, bad):  # noqa: F811
    mail.enable("*")
    with pytest.raises(DomainError) as e:
        await _plan(seeded, {"external_emails": [bad]})
    assert e.value.code == "VALIDATION"


async def test_no_recipients_validation(seeded, mail):  # noqa: F811
    for args in ({}, {"user_ids": [], "external_emails": []}, {"external_emails": None}):
        with pytest.raises(DomainError) as e:
            await _plan(seeded, args)
        assert e.value.code == "VALIDATION"


async def test_execute_external_allowed_queued(seeded, mail):  # noqa: F811
    mail.enable("*")
    out, rows = await _execute(seeded, {"external_emails": ["Abc@Gmail.com", "abc@gmail.com"]})
    assert len(rows) == 1                                   # deduped, no inbox row
    m = rows[0]
    assert (m.channel, m.recipient_user_id, m.email_to, m.status, m.status_detail) == ("email", None, "abc@gmail.com", "queued", None)
    assert m.ref == f"M{m.id}"
    assert mail.sent == []


async def test_execute_external_skipped_not_on_allowlist(seeded, mail):  # noqa: F811
    mail.enable("other@x.com")
    _, rows = await _execute(seeded, {"external_emails": ["abc@gmail.com"]})
    m = rows[0]
    assert (m.channel, m.recipient_user_id, m.email_to, m.status, m.status_detail) == ("email", None, "abc@gmail.com", "skipped", "not_on_allowlist")


async def test_execute_mixed_colleague_and_external(seeded, mail):  # noqa: F811
    ids = seeded
    mail.enable("*")
    async with db.session_scope() as s:
        (await s.get(User, ids["arjun_id"])).notify_email = "arjun@anywhere.test"
    out, rows = await _execute(ids, {"user_ids": [ids["arjun_id"]], "external_emails": ["abc@gmail.com"], "channels": ["inbox"]})
    by = {(m.channel, m.recipient_user_id): m for m in rows}
    assert set(by) == {("email", None), ("inbox", ids["arjun_id"]), ("email", ids["arjun_id"])}
    assert by[("email", None)].email_to == "abc@gmail.com" and by[("email", None)].status == "queued"
    assert by[("inbox", ids["arjun_id"])].status == "delivered"
    assert by[("email", ids["arjun_id"])].email_to == "arjun@anywhere.test"
    assert "sent to 2" in out.summary if hasattr(out, "summary") else True


async def test_colleague_only_behaviour_unchanged(seeded, mail):  # noqa: F811
    ids = seeded
    mail.enable("arjun@anywhere.test")
    async with db.session_scope() as s:
        (await s.get(User, ids["arjun_id"])).notify_email = "arjun@anywhere.test"
    _, rows = await _execute(ids, {"user_ids": [ids["arjun_id"]], "channels": ["inbox", "email"]})
    assert sorted((m.channel, m.status) for m in rows) == [("email", "queued"), ("inbox", "delivered")]
    assert all(m.recipient_user_id == ids["arjun_id"] for m in rows)


async def test_colleague_inbox_only_no_email_rows(seeded, mail):  # noqa: F811
    ids = seeded
    _, rows = await _execute(ids, {"user_ids": [ids["arjun_id"]]})
    assert [(m.channel, m.status) for m in rows] == [("inbox", "delivered")]


@pytest.mark.parametrize("addr,enabled,allow,expect", [
    (None, True, ["*"], (None, "no_email")),
    ("  ", True, ["*"], (None, "no_email")),
    ("A@X.com ", True, ["*"], ("a@x.com", "deliverable")),
    ("a@x.com", True, ["a@x.com"], ("a@x.com", "deliverable")),
    ("A@x.com", True, ["a@x.com"], ("a@x.com", "deliverable")),
    ("b@x.com", True, ["a@x.com"], ("b@x.com", "not_on_allowlist")),
    ("b@x.com", False, [], ("b@x.com", "email_not_configured")),
])
async def test_address_plan_mirrors_email_plan(seeded, mail, addr, enabled, allow, expect):  # noqa: F811
    if enabled:
        mail.enable(*allow)
    assert messaging.address_plan(addr) == expect
    assert messaging.email_plan(User(notify_email=addr)) == expect
