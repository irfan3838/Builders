"""Shared helpers for the B2-B5 gate tests (briefing, google, clarify, travel). No network, no OpenAI, no SMTP."""

from dataclasses import replace

import httpx

import app.config as config_mod
from app import db
from app.actor import Actor
from app.config import get_settings
from app.models import User

LINKED = "linked@purser.test"
FAKE_GOOGLE = {"google_client_id": "cid", "google_client_secret": "csecret", "google_refresh_token": "rtoken",
               "google_linked_email": LINKED}
REAL_CLIENT = httpx.AsyncClient


def pin(mp, **update):
    """Replace get_settings everywhere it was imported by name, so one patched Settings object is seen by all modules."""
    patched = get_settings().model_copy(update={"calendar_timezone": "Asia/Kolkata", **update})
    mp.setattr(config_mod, "get_settings", lambda: patched)
    for mod in ("app.services.briefing", "app.services.agenda", "app.services.google_actions", "app.services.travel.booking",
                "app.services.travel.flights", "app.agent.tools.google"):
        m = __import__(mod, fromlist=["x"])
        if hasattr(m, "get_settings"):
            mp.setattr(m, "get_settings", lambda: patched)
    return patched


def linked(actor: Actor) -> Actor:
    return replace(actor, email=LINKED)


async def actor_by_email(email: str, *, conversation: bool = True) -> Actor:
    from sqlalchemy import select

    from app.models import Conversation
    async with db.session_scope() as s:
        u = (await s.execute(select(User).where(User.email == email))).scalars().one()
        cid = None
        if conversation:
            c = Conversation(workspace_id=u.workspace_id, user_id=u.id, channel="text")
            s.add(c)
            await s.flush()
            cid = c.id
        return Actor(u.id, u.workspace_id, u.role, u.party_id, u.display_name, cid, u.email)
