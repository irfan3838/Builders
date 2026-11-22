"""No-key mode (Settings.ai_enabled, run_turn early exit, voice 503) and first-boot seed idempotency. No model calls."""

import os

import httpx
import openai
import pytest
from sqlalchemy import func, select, text

from app import db
from app.agent import runner
from app.config import Settings, get_settings
from app.models import Base, User, VoiceTurn, Workspace
from seed import bootstrap as bs
from tests.conftest import make_actor
from tests.test_api_intake import client_for


def _test_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", get_settings().test_database_url)
    assert url.rsplit("/", 1)[-1] != "munshi", "refusing to touch the dev database"
    return url


# ------------------------------------------------------------------ ai_enabled
@pytest.mark.parametrize("value,expected", [
    (None, False), ("", False), ("   ", False), ("replace-me", False),
    ("fake-test-key-1", True),
])
def test_ai_enabled(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", value)
    assert Settings().ai_enabled is expected


# ------------------------------------------------------------------ run_turn
async def test_run_turn_no_key_returns_notice_without_calling_model(seeded, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    actor = await make_actor(seeded, "priya")

    async def boom(*a, **k):
        raise AssertionError("model must not be called in no-key mode")

    monkeypatch.setattr(runner.Runner, "run", boom)
    monkeypatch.setattr(runner, "build_agent", lambda *a, **k: boom())
    t = await runner.run_turn(actor, "show overdue invoices")
    assert t.reply == runner.NO_KEY_REPLY and t.metrics == {"route": "no_key"}
    # the user's turn is still recorded
    async with db.session_scope() as s:
        n = (await s.execute(select(func.count()).select_from(VoiceTurn).where(
            VoiceTurn.conversation_id == actor.conversation_id))).scalar_one()
    assert n >= 1


async def test_run_turn_placeholder_key_is_no_key(seeded, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "replace-me")
    actor = await make_actor(seeded, "priya")
    t = await runner.run_turn(actor, "hi")
    assert t.reply == runner.NO_KEY_REPLY


@pytest.mark.parametrize("exc_factory", [
    lambda: openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses")),
    lambda: openai.AuthenticationError("bad key", response=httpx.Response(401, request=httpx.Request("POST", "https://x")), body=None),
])
async def test_run_turn_openai_failure_returns_ai_down(seeded, monkeypatch, exc_factory):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key-2")
    monkeypatch.setattr(get_settings(), "purser_workflows", False)
    actor = await make_actor(seeded, "priya")

    async def fail(*a, **k):
        raise exc_factory()

    monkeypatch.setattr(runner.Runner, "run", fail)
    monkeypatch.setattr(runner, "build_agent", lambda *a, **k: type("A", (), {"model": "fake"})())
    t = await runner.run_turn(actor, "hi")
    assert t.reply == runner.AI_DOWN_REPLY
    assert t.metrics["ai_error"] in ("APIConnectionError", "AuthenticationError")


async def test_workflow_turn_openai_failure_returns_ai_down(seeded, monkeypatch):
    from app.agent.workflows import engine

    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key-2")
    monkeypatch.setattr(get_settings(), "purser_workflows", True)
    actor = await make_actor(seeded, "priya")

    async def fail(*a, **k):
        raise openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))

    monkeypatch.setattr(engine, "run", fail)
    t = await runner.run_turn(actor, "hi")
    assert t.reply == runner.AI_DOWN_REPLY and t.metrics["route"] == "workflow"


# ------------------------------------------------------------------ voice endpoint
async def test_voice_session_503_without_key(seeded, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    c = await client_for()
    r = await c.post("/api/voice/session", json={"sdp": "v=0\r\n"})
    assert r.status_code == 503 and "OPENAI_API_KEY" in r.text


# ------------------------------------------------------------------ bootstrap
async def _counts() -> tuple[int, int]:
    async with db.session_scope() as s:
        w = (await s.execute(select(func.count()).select_from(Workspace))).scalar_one()
        u = (await s.execute(select(func.count()).select_from(User))).scalar_one()
    return w, u


async def test_bootstrap_is_noop_on_seeded_db(seeded):
    before = await _counts()
    assert before[0] >= 1
    out = await bs.bootstrap(_test_url())
    assert out["seeded"] is False and "already seeded" in out["reason"]
    assert await _counts() == before
    await db.engine().dispose()


async def test_bootstrap_seeds_empty_test_db(seeded, monkeypatch):
    """Empty DB -> seeds. role_users.main() reads settings.database_url, so point it at the TEST db first."""
    url = _test_url()
    monkeypatch.setattr(get_settings(), "database_url", url)
    async with db.engine().begin() as conn:
        tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    assert (await _counts())[0] == 0
    out = await bs.bootstrap(url)
    assert out["seeded"] is True
    w, u = await _counts()
    assert w == 1 and u > 0
    # second run is a no-op
    again = await bs.bootstrap(url)
    assert again["seeded"] is False and await _counts() == (w, u)
    await db.engine().dispose()
