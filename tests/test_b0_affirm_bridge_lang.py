"""B0 gate: new affirm phrases, live bridge assistant_turn on every path, English-default prompts.
No DB, no OpenAI: everything the bridge touches is monkeypatched."""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from pathlib import Path

import pytest

from app.services.affirmation import Affirmation, classify
from app.voice import live_bridge

# ------------------------------------------------------------------ 1. affirmation

@pytest.mark.parametrize("phrase", [
    "approve", "approved", "book it", "yes book it", "send it", "yes send it", "schedule it", "do that",
    "Approve!", "Book it.", "yes, send it", "please schedule it", "Do that, please",
])
def test_new_phrases_affirm(phrase):
    assert classify(phrase) == Affirmation.AFFIRM


@pytest.mark.parametrize("phrase", ["don't approve", "no, don't book it", "no send it", "dont schedule it",
                                    "cancel, don't do that", "wait, approve"])
def test_negation_wins_over_new_phrases(phrase):
    assert classify(phrase) in (Affirmation.NEGATIVE, Affirmation.AMBIGUOUS)
    assert classify(phrase) != Affirmation.AFFIRM


def test_approve_then_no_wait_is_not_affirm():
    assert classify("approve? no wait") != Affirmation.AFFIRM


@pytest.mark.parametrize("phrase", ["approve the invoice for Acme", "book it for Friday", "send it to Rahul"])
def test_extra_content_is_not_affirm(phrase):
    assert classify(phrase) == Affirmation.AMBIGUOUS


@pytest.mark.parametrize("phrase,expected", [
    ("yes", Affirmation.AFFIRM), ("haan kar do", Affirmation.AFFIRM), ("हाँ", Affirmation.AFFIRM),
    ("no", Affirmation.NEGATIVE), ("nahi", Affirmation.NEGATIVE), ("", Affirmation.AMBIGUOUS),
    ("what is my budget", Affirmation.AMBIGUOUS),
])
def test_existing_behaviour_unchanged(phrase, expected):
    assert classify(phrase) == expected


# ------------------------------------------------------------------ 2. bridge assistant_turn

class _Conn:
    def __init__(self, fail=False):
        self.fail = fail
        self.appended = []
        outer = self

        class _Commentary:
            async def append(self, **kw):
                if outer.fail:
                    raise RuntimeError("session closed")
                outer.appended.append(kw)

        self.session = SimpleNamespace(commentary=_Commentary())


@pytest.fixture
def bridge(monkeypatch):
    published = []
    monkeypatch.setattr(live_bridge.events, "publish", lambda cid, ev: published.append(ev))

    @asynccontextmanager
    async def fake_scope():
        yield object()

    async def fake_record(*a, **k):
        return None

    async def fake_get_open(s, actor):
        return None

    async def ok_turn(*a, **k):
        return SimpleNamespace(reply="Your budget is fine.", ui=[{"kind": "chart"}])

    monkeypatch.setattr(live_bridge.db, "session_scope", fake_scope)
    monkeypatch.setattr(live_bridge.confirmation, "record_turn", fake_record)
    monkeypatch.setattr(live_bridge.proposals, "get_open", fake_get_open)
    monkeypatch.setattr(live_bridge, "run_turn", ok_turn)
    actor = SimpleNamespace(conversation_id="c1")
    b = live_bridge.LiveBridge(actor, "sess")
    b.pending = [{"text": "show budget", "start_ms": 0, "end_ms": 10}]
    return b, published


def _types(published, t):
    return [e for e in published if e["type"] == t]


async def test_normal_path_one_user_one_assistant(bridge):
    b, pub = bridge
    conn = _Conn()
    await b._delegate(conn, "d1", 20)
    assert len(_types(pub, "user_turn")) == 1
    a = _types(pub, "assistant_turn")
    assert len(a) == 1 and a[0]["text"] == "Your budget is fine."
    assert len(_types(pub, "card")) == 1
    assert len(conn.appended) == 1


async def test_run_turn_raises_still_publishes(bridge, monkeypatch):
    b, pub = bridge

    async def boom(*a, **k):
        raise RuntimeError("llm down")

    monkeypatch.setattr(live_bridge, "run_turn", boom)
    conn = _Conn()
    await b._delegate(conn, "d1", 20)
    assert len(_types(pub, "user_turn")) == 1
    a = _types(pub, "assistant_turn")
    assert len(a) == 1 and "Sorry" in a[0]["text"]
    assert conn.appended and "Sorry" in conn.appended[0]["content"]


async def test_commentary_append_raises_still_publishes(bridge):
    b, pub = bridge
    await b._delegate(_Conn(fail=True), "d1", 20)
    assert len(_types(pub, "user_turn")) == 1
    a = _types(pub, "assistant_turn")
    assert len(a) == 1 and a[0]["text"] == "Your budget is fine."


async def test_db_block_after_reply_raises_still_publishes(bridge, monkeypatch):
    b, pub = bridge

    async def bad_get_open(s, actor):
        raise RuntimeError("db gone")

    monkeypatch.setattr(live_bridge.proposals, "get_open", bad_get_open)
    with pytest.raises(RuntimeError, match="db gone"):
        await b._delegate(_Conn(), "d1", 20)
    assert len(_types(pub, "user_turn")) == 1
    a = _types(pub, "assistant_turn")
    assert len(a) == 1 and a[0]["text"] == "Your budget is fine."


async def test_open_proposal_gets_presented_offset(bridge, monkeypatch):
    b, pub = bridge
    p = SimpleNamespace(presented_offset_ms=None)

    async def get_open(s, actor):
        return p

    monkeypatch.setattr(live_bridge.proposals, "get_open", get_open)
    b.timeline_ms = 500
    await b._delegate(_Conn(), "d1", 20)
    assert p.presented_offset_ms == 500
    assert len(_types(pub, "assistant_turn")) == 1


async def test_cancellation_during_run_turn_publishes_assistant_turn(bridge, monkeypatch):
    b, pub = bridge
    started = asyncio.Event()

    async def hang(*a, **k):
        started.set()
        await asyncio.sleep(60)

    monkeypatch.setattr(live_bridge, "run_turn", hang)
    task = asyncio.create_task(b._delegate(_Conn(), "d1", 20))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(_types(pub, "assistant_turn")) == 1  # finally-block publishes with empty reply


# ------------------------------------------------------------------ 3. English default

def test_wake_opener_is_english(monkeypatch):
    cfg = live_bridge.session_config(None)
    blob = str(cfg)
    assert "in English" in blob
    assert "Hi, how can I help?" in blob
    assert "Haan ji" not in blob and "Hinglish, e.g." not in blob


def test_frontend_instructions_english_default():
    assert "English by default" in live_bridge.FRONTEND_INSTRUCTIONS


def test_purser_prompt_english_default():
    txt = (Path(live_bridge.__file__).parents[1] / "agent" / "prompts" / "purser.md").read_text()
    assert "English is the default" in txt
    assert "Your first reply in a conversation is English" in txt
