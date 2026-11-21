"""Save / delete user routines (custom workflows). Chat goes through propose -> confirm like every other write; the
Settings screen calls `save` / `delete` directly after an explicit, CSRF-checked click. Both re-validate in code."""

from __future__ import annotations

from sqlalchemy import select

from app.actor import Actor
from app.errors import FORBIDDEN, NOT_FOUND, DomainError
from app.models import CustomWorkflow
from app.rbac import require_writer
from app.services import audit
from app.services.actions import Execution, Plan


def _custom():
    from app.agent.workflows import custom  # lazy: the agent layer imports the services layer

    return custom


def _forget(actor: Actor) -> None:
    from app.services import briefing  # lazy: briefing pulls in many services

    briefing.forget(actor.user_id)


def view(row: CustomWorkflow, actor: Actor, owner_name: str = "") -> dict:
    return {"id": row.id, "title": row.title, "when": row.when, "examples": list(row.examples or []),
            "tools": list(row.tools or []), "checklist": list(row.checklist or []), "shared": bool(row.shared),
            "owner": owner_name, "mine": row.owner_user_id == actor.user_id,
            "editable": row.owner_user_id == actor.user_id or (bool(row.shared) and actor.role == "admin"),
            "run": f"Run {row.title}"}


async def _check(s, actor: Actor, args: dict):
    require_writer(actor)
    c = _custom()
    checked = c.validate(actor, args, source_prompt=str(args.get("source_prompt") or ""), shared=bool(args.get("shared")))
    await c.check_unique(s, actor, checked.title)
    return checked


async def save(s, actor: Actor, args: dict, receipt_id: int | None = None) -> CustomWorkflow:
    checked = await _check(s, actor, args)
    row = CustomWorkflow(workspace_id=actor.workspace_id, owner_user_id=actor.user_id, shared=bool(args.get("shared")),
                         title=checked.title, when=checked.when, examples=checked.examples, tools=checked.tools,
                         checklist=checked.checklist, source_prompt=str(args.get("source_prompt") or "")[:4000])
    s.add(row)
    await s.flush()
    _forget(actor)
    await audit.record(s, actor, "custom_workflow.saved", record_type="custom_workflow", record_id=row.id,
                       record_ref=f"RT{row.id}", after={"title": row.title, "tools": row.tools, "shared": row.shared},
                       receipt_id=receipt_id)
    return row


async def load_editable(s, actor: Actor, ref: str | int) -> CustomWorkflow:
    """A routine this actor may delete: their own, or (admin) a shared one. Matches an id or a title."""
    c = _custom()
    rows = [r for r, _ in await c.rows_for(s, actor)]
    key = str(ref).strip()
    digits = key.upper().removeprefix("RT").removeprefix(c.PREFIX.upper())
    row = next((r for r in rows if digits.isdigit() and r.id == int(digits)), None)
    if row is None:
        want = c._core_words(key, c.FILLER)
        row = next((r for r in rows if c._core_words(r.title, c.FILLER) == want), None)
    if row is None:
        raise DomainError(NOT_FOUND, f"No routine called '{key}'.", routines=[r.title for r in rows])
    if row.owner_user_id != actor.user_id and not (row.shared and actor.role == "admin"):
        raise DomainError(FORBIDDEN, f"'{row.title}' was shared by someone else; only an admin can remove it.")
    return row


async def delete(s, actor: Actor, ref: str | int, receipt_id: int | None = None) -> str:
    require_writer(actor)
    row = await load_editable(s, actor, ref)
    title = row.title
    await audit.record(s, actor, "custom_workflow.deleted", record_type="custom_workflow", record_id=row.id,
                       record_ref=f"RT{row.id}", before={"title": title, "tools": row.tools, "shared": row.shared},
                       receipt_id=receipt_id)
    await s.delete(row)
    _forget(actor)
    return title


class SaveCustomWorkflow:
    kind = "save_custom_workflow"

    async def plan(self, s, actor, args):
        checked = await _check(s, actor, args)
        lines = [f"Routine: {checked.title}" + (" (shared with everyone)" if args.get("shared") else " (only you)"),
                 *[f"{i}. {c}" for i, c in enumerate(checked.checklist, 1)],
                 f"Uses: {', '.join(checked.tools)}",
                 f"To run it, say: \"Run {checked.title}\""]
        warn = [str(w) for w in (args.get("warnings") or [])][:2]
        lines += [f"Note: {w}" for w in warn]
        speak = (f"Save your routine '{checked.title}'? It has {len(checked.checklist)} steps, starting with: "
                 f"{checked.checklist[0].rstrip('.')}. Any change it prepares still waits for your yes. "
                 + (warn[0] + " " if warn else "") + "Shall I save it?")
        return Plan("Save routine", lines, speak, [])

    async def execute(self, s, actor, args, receipt_id):
        row = await save(s, actor, args, receipt_id)
        return Execution(f"Routine '{row.title}' saved. Say 'run {row.title}' any time",
                         [{"type": "custom_workflow", "id": row.id, "title": row.title}])


class DeleteCustomWorkflow:
    kind = "delete_custom_workflow"

    async def plan(self, s, actor, args):
        require_writer(actor)
        row = await load_editable(s, actor, args.get("ref") or "")
        who = "everyone in the workspace" if row.shared else "you"
        return Plan("Delete routine", [f"Routine: {row.title}", f"Used by: {who}"],
                    f"Delete the routine '{row.title}'? It is used by {who}.", [])

    async def execute(self, s, actor, args, receipt_id):
        title = await delete(s, actor, args.get("ref") or "", receipt_id)
        return Execution(f"Routine '{title}' deleted", [{"type": "custom_workflow", "title": title, "deleted": True}])


CUSTOM_WORKFLOW_ACTIONS = (SaveCustomWorkflow(), DeleteCustomWorkflow())
