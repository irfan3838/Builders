"""MCQ clarifications: one tappable question at a time, at most three per topic, then Purser must answer anyway.

The count lives on the conversation (survives voice/text turns). For charts, options are checked against the chart
registry, so a button can only offer a metric, grouping or chart type that really exists for this user.
"""

from __future__ import annotations

import uuid
from typing import Literal

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel, Field
from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.agent.context import PurserContext, safe_tool
from app.errors import VALIDATION, DomainError
from app.models import Conversation
from app.services import charts

Ctx = RunContextWrapper[PurserContext]
MAX_QUESTIONS = 3


class Choice(BaseModel):
    label: str = Field(description="Button text, at most 40 characters, in the language you are replying in.")
    value: str = Field(description="What the answer means for you: a registry name (measure, dimension, chart type), a date, an airport code, etc.")


def _registry_values(actor, kind: str) -> set[str] | None:
    opts = charts.options(actor)
    if kind == "measure":
        return {m["name"] for s in opts["sources"] for m in s["measures"]}
    if kind == "dimension":
        return {d["name"] for s in opts["sources"] for d in s["dimensions"]}
    if kind == "chart_type":
        return set(opts["chart_types"])
    return None


async def bump(actor, topic: str, *, reset: bool = False) -> int:
    """Increment (or reset) the per-topic question count; returns the count after the change."""
    if not actor.conversation_id:
        return 0 if reset else 1
    async with db.session_scope() as s:
        c = await s.get(Conversation, actor.conversation_id)
        if c is None:
            return 0
        counts = dict(c.clarify_counts or {})
        counts[topic] = 0 if reset else counts.get(topic, 0) + 1
        c.clarify_counts = counts
        flag_modified(c, "clarify_counts")
        return counts[topic]


async def current(actor, topic: str) -> int:
    if not actor.conversation_id:
        return 0
    async with db.session_scope() as s:
        c = await s.get(Conversation, actor.conversation_id)
        return int((c.clarify_counts or {}).get(topic, 0)) if c else 0


@function_tool
@safe_tool
async def ask_choice(ctx: Ctx, question: str, options: list[Choice],
                     topic: Literal["chart", "flight", "general"] = "general",
                     kind: Literal["measure", "dimension", "chart_type", "time_range", "grouping", "date", "origin", "other"] = "other") -> dict:
    """Ask ONE short multiple-choice question with 2-5 tappable answers, then STOP and wait for the reply (tap or voice).
    Use only when the request is genuinely ambiguous and the answer changes what you do. Ask one gap at a time.
    Never more than 3 per topic: when the limit is reached, proceed with sensible defaults and say which you chose.
    For charts use registry names as values (describe_chart_options): kind=measure | dimension | chart_type, or time_range."""
    a = ctx.context.actor
    q = " ".join(question.split())[:160]
    clean, seen = [], set()
    for o in options:
        label, value = " ".join(o.label.split())[:40], o.value.strip()[:80]
        if label and value and value not in seen:
            seen.add(value)
            clean.append({"label": label, "value": value})
    if not q or not 2 <= len(clean) <= 5:
        raise DomainError(VALIDATION, "Give one question with 2 to 5 distinct options.")
    if topic == "chart":
        allowed = _registry_values(a, kind)
        if allowed is not None:
            bad = [o["value"] for o in clean if o["value"] not in allowed]
            if bad:
                raise DomainError(VALIDATION, f"Not in the chart registry for this user: {', '.join(bad)}. Use describe_chart_options names.",
                                  allowed=sorted(allowed)[:40])
    asked = await current(a, topic)
    if asked >= MAX_QUESTIONS:
        return {"ok": False, "code": "LIMIT_REACHED", "asked": asked,
                "message": "Three questions already asked on this. Do not ask again: proceed now with sensible defaults "
                           "(for a chart, build_chart) and say in one short sentence which defaults you chose."}
    n = await bump(a, topic)
    ctx.context.show({"card": "choice", "id": uuid.uuid4().hex[:12], "question": q, "options": clean, "topic": topic,
                      "step": n, "max": MAX_QUESTIONS})
    return {"ok": True, "asked": n, "remaining": MAX_QUESTIONS - n,
            "instruction": "Say the question in one short sentence (the options are on screen as buttons; read them only if "
                           "there are three or fewer). Then STOP and wait for the user's answer."}


TOOLS = [ask_choice]
