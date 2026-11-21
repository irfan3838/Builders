"""GPT-Live sideband bridge: server-observed transcripts -> voice_turns; delegations -> PurserAgent;
results -> session.commentary.append. Proven in spikes/voice_spike (docs/architecture.md)."""

from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI, BadRequestError

from app import db, events
from app.actor import Actor
from app.agent.runner import run_turn
from app.config import get_settings
from app.services import confirmation, proposals

log = logging.getLogger("purser.live")
_client: AsyncOpenAI | None = None
_tasks: dict[str, asyncio.Task] = {}

FRONTEND_INSTRUCTIONS = """You are Purser, a voice finance assistant for an Indian company. Speak briefly and warmly.
Speak English by default. Switch to Hindi, Hinglish or another language only when the user clearly speaks it, and stay in it until they switch back; short words like "ok", "yes" or "haan" never change the language.
Delegate EVERY request to the backend except a plain greeting: finance, HR, leave, tasks, tickets, mail, calendar, meetings, flights, travel, charts, briefings, anything. This includes "yes", "haan", "no", "cancel", "approve" and corrections, because those answer a pending question.
Speak only what the backend returns. Never state an amount, name, date or status the backend did not give you.
Never say something was approved, submitted or recorded unless the backend said so.
Speak at a brisk, natural conversational pace, especially in Hindi and Hinglish; do not drag words or pause between phrases.
While waiting for the backend, say one short, natural filler in the language you are speaking, picking a different one each time (English: "one moment", "let me check", "sure, checking", "give me a second", "on it"; Hindi only if the user speaks Hindi: "ek second", "abhi batati hoon"). Never repeat the filler you used on the previous turn, and say only one per turn. On yes, no or cancel turns keep it to a word or skip it.
When the backend reply ends with a suggested next step or question, speak it exactly as given.
"""


def client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(max_retries=1)
    return _client


def session_config(wake_text: str | None = None, *, with_speed: bool = True) -> dict:
    if wake_text:
        opener = (f"The user woke you by saying 'Purser' and continued: «{wake_text[:300]}». "
                  "Treat that as their request: delegate it to the backend now and speak the answer.")
    else:
        opener = "The user just said your name to wake you. Greet them in at most four words, in English, e.g. 'Hi, how can I help?'"
    st = get_settings()
    output: dict = {"voice": st.openai_voice_name}
    if with_speed and st.openai_voice_speed and st.openai_voice_speed != 1.0:
        output["speed"] = max(0.25, min(1.5, st.openai_voice_speed))
    return {
        "input": [{"type": "message", "role": "developer", "content": [{"type": "input_text", "text": opener}]}],
        "model": st.openai_model_voice,
        "audio": {"output": output},
        "instructions": FRONTEND_INSTRUCTIONS,
        "delegation": {"type": "client"},
        "client": {"data_channel": {  # untrusted browser: may only close; receives captions + lifecycle
            "allowed_client_events": ["session.close"],
            "allowed_server_events": [{"type": t} for t in (
                "session.started", "session.closed", "session.input_transcript.delta", "session.output_transcript.delta", "error")],
        }},
    }


_bridges: dict[str, LiveBridge] = {}


def is_live(conversation_id: str) -> bool:
    return conversation_id in _bridges


def bridge_for(conversation_id: str) -> LiveBridge | None:
    return _bridges.get(conversation_id)


async def say(conversation_id: str, text: str) -> bool:
    """Speak text in the live session if it is still open. Never raises; returns whether it was sent."""
    b = _bridges.get(conversation_id)
    return await b.speak(text) if b else False


class LiveBridge:
    def __init__(self, actor: Actor, session_id: str, wake_text: str | None = None):
        self.wake_text = (wake_text or "").strip() or None  # browser-relayed: a request, never a confirmation
        self.actor = actor
        self.session_id = session_id
        self.seen: set[str] = set()
        self.pending: list[dict] = []  # input deltas not yet assigned to a turn
        self.timeline_ms = 0
        self.conn = None
        self.lock = asyncio.Lock()  # one delegation at a time keeps turn order and confirmations unambiguous

    async def speak(self, text: str) -> bool:
        conn = self.conn
        if conn is None:
            return False
        try:
            await conn.session.commentary.append(delegation_id=None, content=text[:1800])
            return True
        except Exception as e:  # session closed meanwhile: the caller still shows the text on screen
            log.info("speak skipped conv=%s (%s)", self.actor.conversation_id, type(e).__name__)
            return False

    async def run(self) -> None:
        _bridges[self.actor.conversation_id] = self
        try:
            async with client().live.sideband.connect(session_id=self.session_id) as conn:
                self.conn = conn
                log.info("sideband attached conv=%s", self.actor.conversation_id)
                async for ev in conn:
                    eid = getattr(ev, "event_id", None)
                    if eid:
                        if eid in self.seen:
                            continue
                        self.seen.add(eid)
                    end = getattr(ev, "end_ms", None) or getattr(ev, "offset_ms", None)
                    if isinstance(end, int):
                        self.timeline_ms = max(self.timeline_ms, end)
                    if ev.type == "session.input_transcript.delta":
                        self.pending.append({"text": ev.delta, "start_ms": ev.start_ms, "end_ms": ev.end_ms})
                    elif ev.type == "session.delegation.created":
                        asyncio.create_task(self._delegate(conn, ev.delegation.id, ev.offset_ms))
                    elif ev.type == "error":
                        log.warning("live error conv=%s %s", self.actor.conversation_id, ev.model_dump(mode="json").get("error"))
                    elif ev.type == "session.closed":
                        break
        except Exception:
            log.exception("sideband failed conv=%s", self.actor.conversation_id)
        finally:
            self.conn = None
            _tasks.pop(self.actor.conversation_id or "", None)
            _bridges.pop(self.actor.conversation_id or "", None)

    async def _delegate(self, conn, delegation_id: str, offset_ms: int) -> None:
        async with self.lock:
            chunk = [d for d in self.pending if d["start_ms"] <= offset_ms] or list(self.pending)
            self.pending = [d for d in self.pending if d not in chunk]
            text = "".join(d["text"] for d in chunk).strip()
            server_heard = bool(text)
            if not text and self.wake_text:
                text, self.wake_text = self.wake_text, None
            if not text:
                text = "(the user's words were not captured; ask them to repeat)"
            start = chunk[0]["start_ms"] if chunk else offset_ms
            end = chunk[-1]["end_ms"] if chunk else offset_ms
            if server_heard:  # only server-observed speech can later count as a confirmation
                async with db.session_scope() as s:
                    await confirmation.record_turn(s, self.actor, text, source="live_sideband", start_ms=start, end_ms=end)
            events.publish(self.actor.conversation_id, {"type": "user_turn", "text": text})
            reply = ""
            try:  # the client unlocks its composer on assistant_turn, so it must be sent on every path
                try:
                    r = await run_turn(self.actor, text, channel="live", source="live_sideband", record_turn=False,
                                       presented_offset_ms=None)
                    reply = r.reply
                    for card in r.ui:
                        events.publish(self.actor.conversation_id, {"type": "card", **card})
                except Exception:
                    log.exception("delegation failed conv=%s", self.actor.conversation_id)
                    reply = "Sorry, I couldn't reach the books just now. Please say that again."
                try:
                    await conn.session.commentary.append(delegation_id=delegation_id, content=reply[:1800])
                except Exception as e:
                    log.info("reply not spoken conv=%s (%s)", self.actor.conversation_id, type(e).__name__)
                # Bind presentation to the live timeline: a confirming reply must START after this point.
                async with db.session_scope() as s:
                    p = await proposals.get_open(s, self.actor)
                    if p is not None and p.presented_offset_ms is None:
                        p.presented_offset_ms = max(self.timeline_ms, end)
            finally:
                events.publish(self.actor.conversation_id, {"type": "assistant_turn", "text": reply})


async def start(actor: Actor, sdp: str, wake_text: str | None = None) -> dict:
    transport = {"type": "webrtc", "sdp": sdp}
    try:
        result = await client().live.create(session=session_config(wake_text), transport=transport)
    except BadRequestError as e:  # the live API may not accept audio.output.speed; never let pacing break voice
        log.warning("live session rejected speed, retrying without it: %s", str(e)[:200])
        result = await client().live.create(session=session_config(wake_text, with_speed=False), transport=transport)
    async with db.session_scope() as s:
        from app.models import Conversation

        conv = await s.get(Conversation, actor.conversation_id)
        conv.live_session_id, conv.channel = result.session.id, "live"
    bridge = LiveBridge(actor, result.session.id, wake_text)
    _tasks[actor.conversation_id] = asyncio.create_task(bridge.run())
    return result.model_dump(mode="json")
