"""One user turn through PurserAgent. Shared by the text channel, push-to-talk and voice delegation."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

import openai
from agents import Runner
from agents.extensions.memory import SQLAlchemySession
from sqlalchemy import select

from app import db
from app.actor import Actor
from app.agent.context import PurserContext
from app.agent.purser import build_agent
from app.config import get_settings
from app.models import Proposal
from app.services import confirmation, proposals

log = logging.getLogger("purser.runner")
TURN_TIMEOUT_S = 90
NO_KEY_REPLY = ("AI is off on this server: OPENAI_API_KEY is not set. Add it to .env and restart to talk to Purser. "
                "Logins, dashboards, records and uploads still work.")
AI_DOWN_REPLY = "I can't reach the AI service right now (the OpenAI key was rejected or the network is down). Please try again."


@dataclass
class TurnResult:
    reply: str
    ui: list[dict] = field(default_factory=list)
    tools: list[dict] = field(default_factory=list)
    latency_ms: int = 0
    usage: dict = field(default_factory=dict)
    # Per-turn cost/context metrics for the eval harness: route, llm_calls, tokens per model, history_items, ...
    metrics: dict = field(default_factory=dict)


def add_usage(metrics: dict, model: str, raw_responses) -> None:
    """Accumulate token usage per model from SDK raw responses into metrics["models"][model]."""
    m = metrics.setdefault("models", {}).setdefault(model, {"calls": 0, "input_tokens": 0, "cached_tokens": 0,
                                                            "output_tokens": 0})
    for r in raw_responses:
        u = r.usage
        if not u:
            continue
        m["calls"] += 1
        m["input_tokens"] += u.input_tokens
        m["output_tokens"] += u.output_tokens
        details = getattr(u, "input_tokens_details", None)
        m["cached_tokens"] += getattr(details, "cached_tokens", 0) or 0


def memory(conversation_id: str) -> SQLAlchemySession:
    return SQLAlchemySession(conversation_id, engine=db.engine(), create_tables=True, ensure_ascii=False)


async def run_turn(actor: Actor, user_text: str, *, channel: str = "text", source: str = "text",
                   start_ms: int | None = None, end_ms: int | None = None, presented_offset_ms: int | None = None,
                   model: str | None = None, record_turn: bool = True) -> TurnResult:
    assert actor.conversation_id, "a conversation is required"
    if record_turn:
        async with db.session_scope() as s:
            await confirmation.record_turn(s, actor, user_text, source=source, start_ms=start_ms, end_ms=end_ms)
    if not get_settings().ai_enabled:
        return TurnResult(reply=NO_KEY_REPLY, metrics={"route": "no_key"})
    if get_settings().purser_workflows and model is None:
        return await _run_workflow_turn(actor, user_text, channel=channel, presented_offset_ms=presented_offset_ms)
    ctx = PurserContext(actor=actor, channel=channel)
    agent = build_agent(model)
    metrics: dict = {"route": "agent"}
    session = memory(actor.conversation_id)
    t0 = time.perf_counter()
    try:
        metrics["history_items"] = len(await session.get_items())
        result = await asyncio.wait_for(
            Runner.run(agent, user_text, context=ctx, session=session, max_turns=12),
            timeout=TURN_TIMEOUT_S,
        )
        reply = str(result.final_output)
        usage = {}
        for r in result.raw_responses:
            if r.usage:
                usage["input_tokens"] = usage.get("input_tokens", 0) + r.usage.input_tokens
                usage["output_tokens"] = usage.get("output_tokens", 0) + r.usage.output_tokens
        add_usage(metrics, str(agent.model), result.raw_responses)
    except TimeoutError:
        reply, usage = "Sorry, that took too long. Please say it again.", {}
        metrics["timeout"] = True
    except (openai.AuthenticationError, openai.APIConnectionError) as e:
        log.error("turn failed: openai %s", type(e).__name__)
        reply, usage = AI_DOWN_REPLY, {}
        metrics["ai_error"] = type(e).__name__
    latency = int((time.perf_counter() - t0) * 1000)
    await _mark_presented(actor, presented_offset_ms)
    log.info("turn conv=%s channel=%s tools=%s ms=%s usage=%s", actor.conversation_id, channel,
             [t["tool"] + ":" + t["outcome"] for t in ctx.tool_log], latency, usage)
    return TurnResult(reply=reply, ui=ctx.ui, tools=ctx.tool_log, latency_ms=latency, usage=usage, metrics=metrics)


async def _mark_presented(actor: Actor, presented_offset_ms: int | None) -> None:
    """Any proposal created during this turn has now been presented to the user."""
    async with db.session_scope() as s:
        open_ids = (await s.execute(select(Proposal.id).where(Proposal.conversation_id == actor.conversation_id,
                                                              Proposal.status == "open", Proposal.presented_at.is_(None)))).scalars().all()
        for pid in open_ids:
            await proposals.mark_presented(s, pid, offset_ms=presented_offset_ms)


async def _run_workflow_turn(actor: Actor, user_text: str, *, channel: str,
                             presented_offset_ms: int | None) -> TurnResult:
    """PURSER_WORKFLOWS=1: the workflow engine handles the turn (app/agent/workflows/engine.py)."""
    from app.agent.workflows import engine

    t0 = time.perf_counter()
    try:
        res = await asyncio.wait_for(engine.run(actor, user_text, channel=channel), timeout=TURN_TIMEOUT_S)
        reply, ctx, metrics = res.reply, res.ctx, res.metrics
    except TimeoutError:
        reply, ctx = "Sorry, that took too long. Please say it again.", PurserContext(actor=actor, channel=channel)
        metrics = {"route": "workflow", "timeout": True}
    except (openai.AuthenticationError, openai.APIConnectionError) as e:
        log.error("workflow turn failed: openai %s", type(e).__name__)
        reply, ctx = AI_DOWN_REPLY, PurserContext(actor=actor, channel=channel)
        metrics = {"route": "workflow", "ai_error": type(e).__name__}
    latency = int((time.perf_counter() - t0) * 1000)
    await _mark_presented(actor, presented_offset_ms)
    usage = {"input_tokens": sum(m["input_tokens"] for m in metrics.get("models", {}).values()),
             "output_tokens": sum(m["output_tokens"] for m in metrics.get("models", {}).values())}
    log.info("turn conv=%s channel=%s route=%s workflow=%s tools=%s ms=%s usage=%s", actor.conversation_id, channel,
             metrics.get("route"), metrics.get("workflow"), [t["tool"] + ":" + t["outcome"] for t in ctx.tool_log],
             latency, usage)
    return TurnResult(reply=reply, ui=ctx.ui, tools=ctx.tool_log, latency_ms=latency, usage=usage, metrics=metrics)
