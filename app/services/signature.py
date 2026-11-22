"""One standard, formal signature on every outgoing email (Purser outbox, Gmail send/reply, Gmail drafts).

Built from the sender's directory record and the workspace name, so the model never writes a sign-off: any closing
it adds ("Regards, Irfan") is stripped and replaced, and signing twice is a no-op."""

from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.config import get_settings
from app.models import User, Workspace

CLOSING = "Warm regards,"
_CLOSING_RE = re.compile(
    r"^(warm(est)?|kind|best|with)?\s*(regards|wishes)[,.!]*$|^(best|thanks|thank you|many thanks|cheers|sincerely)[,.!]*$|"
    r"^yours\s+(sincerely|truly|faithfully)[,.!]*$|^(regards|dhanyavaad|shukriya)[,.!]*$|^[-—–]{1,3}\s*$", re.I)
_TAIL_LINES = 5  # a model-written closing sits in the last few lines; never cut deeper into the body


def render(name: str, designation: str | None, department: str | None, company: str, email: str | None,
           phone: str | None = None, website: str | None = None) -> str:
    role = " | ".join(p for p in (designation, department) if p)
    contact = " | ".join(p for p in (email, phone) if p)
    lines = [CLOSING, "", name]
    lines += [role] if role else []
    lines += [company]
    lines += [contact] if contact else []
    lines += [website] if website else []
    return "\n".join(lines)


async def for_actor(s: AsyncSession, actor: Actor) -> str:
    st = get_settings()
    u = await s.get(User, actor.user_id)
    ws = await s.get(Workspace, actor.workspace_id)
    return render(u.display_name if u else actor.display_name, u.designation if u else None, u.department if u else None,
                  (st.signature_company or (ws.name if ws else "") or "Purser").strip(), u.email if u else actor.email,
                  st.signature_phone or None, st.signature_website or None)


def strip_signoff(body: str) -> str:
    """Drop a closing the model wrote ('Best,\\nIrfan') so the standard signature is the only one."""
    lines = body.rstrip().splitlines()
    start = max(0, len(lines) - _TAIL_LINES)
    for i in range(start, len(lines)):
        if _CLOSING_RE.match(lines[i].strip()):
            return "\n".join(lines[:i]).rstrip()
    return body.rstrip()


def sign(body: str, signature: str) -> str:
    body = body.rstrip()
    if body.endswith(signature):
        return body
    return f"{strip_signoff(body)}\n\n{signature}"
