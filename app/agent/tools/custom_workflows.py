"""User routines (custom workflows) by voice or chat: describe one, hear the preview, say yes to save. Running a saved
routine needs no tool: the workflow engine routes "run <title>" to it."""

from __future__ import annotations

from agents import RunContextWrapper, function_tool

from app import db
from app.agent.context import PurserContext, safe_tool
from app.agent.tools.proposals import _propose
from app.rbac import require_writer
from app.services import custom_workflows as svc

Ctx = RunContextWrapper[PurserContext]


@function_tool
@safe_tool
async def propose_custom_workflow(ctx: Ctx, description: str, shared: bool = False) -> dict:
    """Turn the user's description of a routine they repeat ('every Monday show my tasks, my meetings and pending
    approvals') into a saved routine. Pass their words as the description (in English if they spoke Hindi). Returns a
    preview to read out; it is saved only after they say yes. shared=True (admins only) makes it available to everyone."""
    from app.agent.workflows import custom  # lazy: the workflow package imports the tool list

    a = ctx.context.actor
    require_writer(a)
    checked = await custom.compile_routine(a, description, shared=shared)
    return await _propose(ctx, "save_custom_workflow", {**checked.as_args(), "shared": shared,
                                                        "source_prompt": description[:2000],
                                                        "warnings": checked.warnings})


@function_tool
@safe_tool
async def list_custom_workflows(ctx: Ctx) -> dict:
    """The user's saved routines and the ones shared with the workspace, with the phrase that runs each."""
    from app.agent.workflows import custom

    a = ctx.context.actor
    async with db.session_scope() as s:
        items = [svc.view(r, a, n) for r, n in await custom.rows_for(s, a)]
    return {"ok": True, "count": len(items),
            "routines": [{k: i[k] for k in ("title", "run", "shared", "owner", "mine", "checklist")} for i in items]}


@function_tool
@safe_tool
async def propose_delete_custom_workflow(ctx: Ctx, title_or_id: str) -> dict:
    """Propose deleting one of the user's routines (by its title). Admins can also remove a shared routine."""
    return await _propose(ctx, "delete_custom_workflow", {"ref": title_or_id})


TOOLS = [propose_custom_workflow, list_custom_workflows, propose_delete_custom_workflow]
