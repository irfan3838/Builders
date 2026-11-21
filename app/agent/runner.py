"""One user turn through MunshiAgent. Shared by the text channel, push-to-talk and voice delegation."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from agents import Runner
from agents.extensions.memory import SQLAlchemySession
from sqlalchemy import select

from app import db
from app.actor import Actor
from app.agent.context import MunshiContext
from app.agent.munshi import build_agent
from app.models import Proposal
from app.services import confirmation, proposals

log = logging.getLogger("munshi.runner")
TURN_TIMEOUT_S = 90


@dataclass
class TurnResult:
    reply: str
    ui: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    latency_ms: int = 0
    usage: dict = field(default_factory=dict)


def memory(conversation_id: str) -> SQLAlchemySession:
    return SQLAlchemySession(conversation_id, engine=db.engine(), create_tables=True, ensure_ascii=False)


async def run_turn(actor: Actor, user_text: str, *, channel: str = "text", source: str = "text",
                   start_ms: int | None = None, end_ms: int | None = None, presented_offset_ms: int | None = None,
                   model: str | None = None, record_turn: bool = True) -> TurnResult:
    assert actor.conversation_id, "a conversation is required"
    if record_turn:
        async with db.session_scope() as s:
            await confirmation.record_turn(s, actor, user_text, source=source, start_ms=start_ms, end_ms=end_ms)
    ctx = MunshiContext(actor=actor, channel=channel)
    t0 = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            Runner.run(build_agent(model), user_text, context=ctx, session=memory(actor.conversation_id), max_turns=12),
            timeout=TURN_TIMEOUT_S,
        )
        reply = str(result.final_output)
        usage = {}
        for r in result.raw_responses:
            if r.usage:
                usage["input_tokens"] = usage.get("input_tokens", 0) + r.usage.input_tokens
                usage["output_tokens"] = usage.get("output_tokens", 0) + r.usage.output_tokens
    except TimeoutError:
        reply, usage = "Sorry, that took too long. Please say it again.", {}
    latency = int((time.perf_counter() - t0) * 1000)
    # Any proposal created during this turn has now been presented to the user.
    async with db.session_scope() as s:
        open_ids = (await s.execute(select(Proposal.id).where(Proposal.conversation_id == actor.conversation_id,
                                                              Proposal.status == "open", Proposal.presented_at.is_(None)))).scalars().all()
        for pid in open_ids:
            await proposals.mark_presented(s, pid, offset_ms=presented_offset_ms)
    log.info("turn conv=%s channel=%s tools=%s ms=%s usage=%s", actor.conversation_id, channel,
             [t["tool"] + ":" + t["outcome"] for t in ctx.tool_log], latency, usage)
    return TurnResult(reply=reply, ui=ctx.ui, tools=ctx.tool_log, latency_ms=latency, usage=usage)
