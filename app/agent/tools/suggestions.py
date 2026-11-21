"""Next-step suggestion chips. Writes nothing: a clicked chip only sends a normal user turn."""

from __future__ import annotations

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel, Field

from app.agent.context import PurserContext, safe_tool

Ctx = RunContextWrapper[PurserContext]
MAX_SUGGESTIONS = 3


class Suggestion(BaseModel):
    label: str = Field(description="Short chip text, at most 40 characters, in the user's language.")
    utterance: str = Field(description="The exact request sent when the chip is tapped, in the user's language.")


@function_tool
@safe_tool
async def suggest_next_actions(ctx: Ctx, items: list[Suggestion]) -> dict:
    """Show 1-3 tappable next-step chips under your reply. The first must match the offer you speak.
    Only suggest things your tools can actually do. Do not call this while a proposal awaits confirmation."""
    clean = []
    for it in items:
        label, utt = " ".join(it.label.split())[:40], " ".join(it.utterance.split())[:160]
        if label and utt and all(c["utterance"] != utt for c in clean):
            clean.append({"label": label, "utterance": utt})
        if len(clean) == MAX_SUGGESTIONS:
            break
    if not clean:
        return {"ok": False, "code": "EMPTY", "message": "No usable suggestions."}
    ctx.context.ui[:] = [c for c in ctx.context.ui if c.get("card") != "suggestions"]
    ctx.context.show({"card": "suggestions", "items": clean})
    return {"ok": True, "shown": len(clean)}


TOOLS = [suggest_next_actions]
