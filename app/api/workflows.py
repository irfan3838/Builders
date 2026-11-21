"""Settings > My routines: draft (compile + validate, nothing saved), save, list and delete custom workflows.
CSRF and origin are checked by auth.ActorDep on every POST/DELETE; save and delete re-validate on the server."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import auth, db
from app.actor import Actor
from app.rbac import require_writer
from app.services import custom_workflows as svc

router = APIRouter()


class DraftIn(BaseModel):
    prompt: str = Field(min_length=8, max_length=2000)
    shared: bool = False


class SaveIn(BaseModel):
    title: str = Field(max_length=200)
    when: str = Field(max_length=400)
    examples: list[str] = Field(default_factory=list, max_length=5)
    tools: list[str] = Field(max_length=20)
    checklist: list[str] = Field(max_length=20)
    shared: bool = False
    source_prompt: str = Field(default="", max_length=2000)


@router.get("/api/workflows")
async def list_routines(actor: Actor = auth.ActorDep) -> dict:
    from app.agent.workflows import custom

    async with db.session_scope() as s:
        items = [svc.view(r, actor, n) for r, n in await custom.rows_for(s, actor)]
    return {"items": items, "can_share": actor.role == "admin", "can_create": not actor.read_only,
            "catalogue": custom.catalogue(actor)}


@router.post("/api/workflows/draft")
async def draft_routine(body: DraftIn, actor: Actor = auth.ActorDep) -> dict:
    """Compile a description into a routine for review. Nothing is saved."""
    from app.agent.workflows import custom

    require_writer(actor)
    checked = await custom.compile_routine(actor, body.prompt, shared=body.shared)
    return {"draft": {**checked.as_args(), "shared": body.shared, "source_prompt": body.prompt},
            "warnings": checked.warnings}


@router.post("/api/workflows", status_code=201)
async def save_routine(body: SaveIn, actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        row = await svc.save(s, actor, body.model_dump())
        return {"item": svc.view(row, actor, actor.display_name)}


@router.delete("/api/workflows/{routine_id}")
async def delete_routine(routine_id: int, actor: Actor = auth.ActorDep) -> dict:
    async with db.session_scope() as s:
        title = await svc.delete(s, actor, routine_id)
    return {"deleted": title}
