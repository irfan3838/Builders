"""MunshiAgent: one conversational agent with typed tools. Same agent for voice (delegation) and text."""

from __future__ import annotations

from pathlib import Path

from agents import Agent, ModelSettings, RunContextWrapper
from openai.types.shared import Reasoning

from app.agent.context import MunshiContext
from app.agent.tools import finance, intake, proposals
from app.config import get_settings
from app.services.records import today_ist

PROMPT = (Path(__file__).parent / "prompts" / "munshi.md").read_text()
ALL_TOOLS = [*finance.TOOLS, *intake.TOOLS, *proposals.TOOLS]


def _instructions(ctx: RunContextWrapper[MunshiContext], agent: Agent) -> str:
    a = ctx.context.actor
    role = "finance approver" if a.is_approver else "employee"
    return PROMPT.format(workspace="the company (synthetic demo workspace)", user_name=a.display_name, role=role,
                         today=today_ist().strftime("%d %b %Y"))


def build_agent(model: str | None = None) -> Agent[MunshiContext]:
    return Agent[MunshiContext](
        name="Munshi",
        model=model or get_settings().agent_model,
        instructions=_instructions,
        tools=ALL_TOOLS,
        model_settings=ModelSettings(reasoning=Reasoning(effort="low"), parallel_tool_calls=False),
    )
