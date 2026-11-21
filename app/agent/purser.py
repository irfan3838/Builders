"""PurserAgent: one conversational agent with typed tools. Same agent for voice (delegation) and text."""

from __future__ import annotations

from pathlib import Path

from agents import Agent, ModelSettings, RunContextWrapper
from openai.types.shared import Reasoning

from app.agent import tool_access
from app.agent.context import PurserContext
from app.agent.tools import (
    budget_months,
    charts,
    clarify,
    contracts,
    finance,
    google,
    intake,
    people,
    proposals,
    revenue,
    suggestions,
    travel,
    work,
)
from app.config import get_settings
from app.services.records import today_ist

PROMPT = (Path(__file__).parent / "prompts" / "purser.md").read_text()
ALL_TOOLS = tool_access.apply([*finance.TOOLS, *budget_months.TOOLS, *charts.TOOLS, *intake.TOOLS, *proposals.TOOLS, *people.TOOLS, *revenue.TOOLS, *contracts.TOOLS, *google.TOOLS, *clarify.TOOLS, *travel.TOOLS, *work.TOOLS, *suggestions.TOOLS])


def _instructions(ctx: RunContextWrapper[PurserContext], agent: Agent) -> str:
    a = ctx.context.actor
    role = {"admin": "admin (finance approver and HR)", "finance_approver": "finance approver", "hr_admin": "HR admin",
            "ceo": "CEO, read-only"}.get(a.role, "employee")
    base = PROMPT.format(user_id=a.user_id, workspace="the company", user_name=a.display_name, role=role,
                         today=today_ist().strftime("%A %d %b %Y"))
    note = tool_access.ROLE_NOTES.get(a.role, tool_access.ROLE_NOTES["employee"])
    google = (" Their real Gmail and Google Calendar are connected." if a.uses_google else
              " Their mail is the Purser inbox and their meetings are in the Purser calendar (no Google account is connected).")
    return f"{base}\n\n## This user's access\n{note}{google}\n"


def build_agent(model: str | None = None) -> Agent[PurserContext]:
    return Agent[PurserContext](
        name="Purser",
        model=model or get_settings().agent_model,
        instructions=_instructions,
        tools=ALL_TOOLS,
        model_settings=ModelSettings(reasoning=Reasoning(effort="low"), parallel_tool_calls=False),
    )
