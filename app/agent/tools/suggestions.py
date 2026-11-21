"""Next-step suggestion chips. Writes nothing: a clicked chip only sends a normal user turn."""

from __future__ import annotations

from typing import Literal

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel, Field

from app.agent.context import PurserContext, safe_tool

Ctx = RunContextWrapper[PurserContext]
MAX_SUGGESTIONS = 3


class Suggestion(BaseModel):
    label: str = Field(description="Short chip text, at most 40 characters, in the language of your reply (English by default).")
    utterance: str = Field(description="The exact request sent when the chip is tapped, in the language of your reply (English by default).")


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


VIEWS_BY_ROLE = {
    "finance": ["workspace", "dashboards", "mail", "tasks", "helpdesk", "expenses", "travel", "claims", "payments", "budgets", "reports"],
    "ceo": ["workspace", "dashboards", "mail", "budgets", "reports"],
    "other": ["workspace", "mail", "tasks", "helpdesk", "expenses", "travel", "claims"],
}


@function_tool
@safe_tool
async def open_view(ctx: Ctx, view: Literal["workspace", "dashboards", "mail", "tasks", "helpdesk", "expenses", "travel", "claims",
                                            "payments", "budgets", "reports"]) -> dict:
    """Open a screen for the user by voice ('open my tasks', 'go home', 'show the budgets page', 'open mail').
    workspace is the home briefing. Only screens this role may see open."""
    a = ctx.context.actor
    allowed = VIEWS_BY_ROLE["ceo" if a.role == "ceo" else "finance" if a.is_approver else "other"]
    if view not in allowed:
        return {"ok": False, "code": "FORBIDDEN", "message": f"The {view} screen is not available for this login."}
    ctx.context.show({"card": "navigate", "view": view})
    return {"ok": True, "opened": view}


TOOLS = [suggest_next_actions, open_view]
