"""Loads every workflow spec, checks coverage against the real tool set, and builds role-filtered picker menus."""

from __future__ import annotations

from functools import lru_cache
from types import SimpleNamespace

from agents import FunctionTool

from app.actor import Actor
from app.agent import tool_access
from app.agent.purser import ALL_TOOLS
from app.agent.workflows.spec import COMMON_TOOLS, ENGINE_ONLY, Workflow
from app.agent.workflows.specs import budget, charts, contracts, core, documents, mail_calendar, people, revenue, travel, work

_MODULES = (core, documents, budget, charts, revenue, contracts, people, mail_calendar, work, travel)


class RegistryError(RuntimeError):
    pass


@lru_cache
def workflows() -> dict[str, Workflow]:
    out: dict[str, Workflow] = {}
    for m in _MODULES:
        for wf in m.WORKFLOWS:
            if wf.name in out:
                raise RegistryError(f"duplicate workflow name {wf.name}")
            out[wf.name] = wf
    check(out)
    return out


@lru_cache
def tools_by_name() -> dict[str, FunctionTool]:
    return {t.name: t for t in ALL_TOOLS}


def check(wfs: dict[str, Workflow]) -> None:
    """Fail loudly if a spec names a tool that does not exist, uses an engine-only tool, or a real tool is not
    reachable from any workflow (it would then only work through escalation)."""
    real = set(tools_by_name())
    used: set[str] = set(COMMON_TOOLS) | ENGINE_ONLY
    for wf in wfs.values():
        unknown = set(wf.all_tools) - real
        if unknown:
            raise RegistryError(f"workflow {wf.name} names unknown tools {sorted(unknown)}")
        if set(wf.tools) & ENGINE_ONLY:
            raise RegistryError(f"workflow {wf.name} may not use engine-only tools")
        if wf.required and not set(wf.required) <= set(wf.all_tools):
            raise RegistryError(f"workflow {wf.name} requires tools it cannot call")
        used |= set(wf.all_tools)
    missing = real - used
    if missing:
        raise RegistryError(f"tools not covered by any workflow: {sorted(missing)}")


def _ctx(actor: Actor):
    return SimpleNamespace(context=SimpleNamespace(actor=actor))


# Lookups any role may call that say nothing about whether the workflow's real action is open to this role.
GENERIC_TOOLS = {"list_budget_categories", "get_record", "get_attention_items", "find_people", "resolve_party",
                 "get_my_location", "inspect_document"}


def allowed(actor: Actor, wf: Workflow) -> bool:
    """A workflow is offered when this role may use at least one of its own tools other than generic lookups."""
    if wf.roles is not None and actor.role not in wf.roles:
        return False
    if not wf.tools:
        return True
    core = [t for t in wf.tools if t not in GENERIC_TOOLS] or list(wf.tools)
    return any(tool_access._allowed(t, _ctx(actor)) for t in core)


def menu(actor: Actor) -> list[Workflow]:
    return [wf for wf in workflows().values() if allowed(actor, wf)]


def tools_for(wf: Workflow) -> list[FunctionTool]:
    """The workflow's FunctionTools (role gating still applies through each tool's is_enabled)."""
    by = tools_by_name()
    return [by[n] for n in wf.all_tools]


def module_tools(module: str) -> list[FunctionTool]:
    names: dict[str, None] = {}
    for wf in workflows().values():
        if wf.module == module or wf.module == "core":
            names.update(dict.fromkeys(wf.all_tools))
    names.update(dict.fromkeys(("get_pending_proposal",)))
    by = tools_by_name()
    return [by[n] for n in names]
