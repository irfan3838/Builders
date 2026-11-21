"""Hour-0 voice spike (docs/PLAN_v4.md §5, block 0-1).

Proves: one spoken question -> GPT-Live client delegation -> server sideband
-> OpenAI Agents SDK Runner with one real function tool -> spoken result.
Also logs server-observed input transcripts (the basis for confirm-by-voice).

Run:  uv run uvicorn spikes.voice_spike.server:app --port 8000
Open: http://localhost:8000
Fixture data below is SYNTHETIC.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from openai import APIError, AsyncOpenAI
from pydantic import BaseModel, Field

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("voice_spike")

HERE = Path(__file__).parent
EVIDENCE = HERE / "evidence"
EVIDENCE.mkdir(exist_ok=True)

VOICE_MODEL = os.getenv("OPENAI_MODEL_VOICE", "gpt-live-1.1")
AGENT_MODEL = os.getenv("OPENAI_MODEL_FAST", "gpt-5.4-mini")
ALLOWED_ORIGIN = os.getenv("APP_ORIGIN", "http://localhost:8000")

client = AsyncOpenAI(max_retries=0)
app = FastAPI()
_bridges: set[asyncio.Task] = set()

# --- one real tool over a SYNTHETIC fixture ---------------------------------
_BUDGET = {"travel": {"allocated": 5_000_000, "reserved": 500_000, "committed": 0, "spent": 0}}


@function_tool
def get_budget_status(category: str) -> dict:
    """Return allocated, reserved, committed, spent and available (INR) for a budget category."""
    line = _BUDGET.get(category.strip().lower())
    if line is None:
        return {"ok": False, "code": "UNKNOWN_CATEGORY", "known": sorted(_BUDGET)}
    available = line["allocated"] - line["reserved"] - line["committed"] - line["spent"]
    inr = lambda p: p // 100  # noqa: E731
    return {
        "ok": True,
        "category": category,
        "allocated_inr": inr(line["allocated"]),
        "reserved_inr": inr(line["reserved"]),
        "committed_inr": inr(line["committed"]),
        "spent_inr": inr(line["spent"]),
        "available_inr": inr(available),
        "source": "synthetic spike fixture",
    }


munshi = Agent(
    name="Munshi (spike)",
    model=AGENT_MODEL,
    instructions=(
        "You help a finance approver in a live voice conversation. Transcripts may contain "
        "mistakes. Use tools for every number; never invent figures. Reply briefly in the "
        "user's language (Hindi, English or Hinglish). Return the facts to be spoken."
    ),
    tools=[get_budget_status],
)

FRONTEND_INSTRUCTIONS = (
    "You are Munshi, a voice finance assistant. Speak briefly and match the user's language "
    "(Hindi, English or Hinglish). For ANY question about budgets, bills, claims, invoices or "
    "money, delegate to the backend and speak only what the backend returns. Never state a "
    "number the backend did not give you."
)


# --- sideband bridge ---------------------------------------------------------
class Bridge:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.seen: set[str] = set()
        self.input_deltas: list[dict] = []  # server-observed user speech
        self.consumed = 0
        self.history: list[dict] = []
        self.log = (EVIDENCE / f"{int(time.time())}_{session_id[-8:]}.jsonl").open("a")

    def record(self, kind: str, **data) -> None:
        self.log.write(json.dumps({"t": time.time(), "kind": kind, **data}, ensure_ascii=False) + "\n")
        self.log.flush()

    async def run(self) -> None:
        async with client.live.sideband.connect(session_id=self.session_id) as conn:
            self.record("sideband_attached", session_id=self.session_id)
            async for event in conn:
                eid = getattr(event, "event_id", None)
                if eid:
                    if eid in self.seen:  # 3 s replay on attach
                        continue
                    self.seen.add(eid)
                et = event.type
                if et == "session.input_transcript.delta":
                    self.input_deltas.append({"text": event.delta, "start_ms": event.start_ms, "end_ms": event.end_ms})
                    self.record("input_delta", text=event.delta, start_ms=event.start_ms, end_ms=event.end_ms)
                elif et == "session.output_transcript.delta":
                    self.record("output_delta", text=event.delta, start_ms=event.start_ms)
                elif et == "session.delegation.created":
                    asyncio.create_task(self.handle_delegation(conn, event))
                elif et in ("session.closed", "error"):
                    self.record(et, raw=event.model_dump(mode="json"))
                    if et == "session.closed":
                        break

    async def handle_delegation(self, conn, event) -> None:
        did = event.delegation.id
        new = self.input_deltas[self.consumed :]
        self.consumed = len(self.input_deltas)
        user_text = "".join(d["text"] for d in new).strip()
        self.record("delegation", delegation_id=did, offset_ms=event.offset_ms, user_text=user_text)
        started = time.perf_counter()
        try:
            prompt = self.history[-6:] + [{"role": "user", "content": user_text or "(unclear audio)"}]
            result = await asyncio.wait_for(Runner.run(munshi, prompt, max_turns=6), timeout=45)
            answer = str(result.final_output)
            tools_called = [
                i.raw_item.name for i in result.new_items if getattr(i, "type", "") == "tool_call_item"
            ]
        except Exception as exc:  # report, never crash the bridge
            log.exception("agent run failed")
            answer, tools_called = "Sorry, I could not reach the books just now.", [f"error:{type(exc).__name__}"]
        latency = round(time.perf_counter() - started, 2)
        self.history += [{"role": "user", "content": user_text}, {"role": "assistant", "content": answer}]
        self.record("agent_result", delegation_id=did, tools=tools_called, latency_s=latency, answer=answer)
        await conn.session.commentary.append(delegation_id=did, content=answer[:1800])


# --- HTTP ---------------------------------------------------------------------
class SDPOffer(BaseModel):
    sdp: str = Field(min_length=1, max_length=65536)


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (HERE / "index.html").read_text()


@app.post("/api/session", status_code=201)
async def create_session(offer: SDPOffer, request: Request) -> dict:
    if request.headers.get("origin") != ALLOWED_ORIGIN:
        raise HTTPException(403, "unexpected origin")
    try:
        result = await client.live.create(
            session={
                "model": VOICE_MODEL,
                "instructions": FRONTEND_INSTRUCTIONS,
                "delegation": {"type": "client"},
                # Untrusted browser: may only close the session; receives captions + lifecycle.
                "client": {
                    "data_channel": {
                        "allowed_client_events": ["session.close"],
                        "allowed_server_events": [
                            {"type": "session.started"},
                            {"type": "session.closed"},
                            {"type": "session.input_transcript.delta"},
                            {"type": "session.output_transcript.delta"},
                            {"type": "error"},
                        ],
                    }
                },
            },
            transport={"type": "webrtc", "sdp": offer.sdp},
        )
    except APIError as exc:
        log.error("live.create failed: %s %s", getattr(exc, "status_code", "?"), exc.message)
        raise HTTPException(502, f"live session creation failed: {exc.message}") from exc
    bridge = Bridge(result.session.id)
    task = asyncio.create_task(bridge.run())
    _bridges.add(task)
    task.add_done_callback(_bridges.discard)
    return result.model_dump(mode="json")
