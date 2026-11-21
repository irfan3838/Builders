"""Inbox + email outbox. Composing happens inside the confirm transaction; email delivery happens after
commit (dispatch), so a rolled-back or replayed confirmation never sends anything."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import uuid
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import make_msgid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import db
from app.actor import Actor
from app.config import get_settings
from app.models import Message, User

log = logging.getLogger("purser.messaging")


def email_plan(user: User) -> tuple[str | None, str]:
    """Where an email to this user would go, and whether it is deliverable in this demo."""
    st = get_settings()
    target = (user.notify_email or "").strip().lower() or None
    if not target:
        return None, "no_email"
    if not st.email_enabled:
        return target, "email_not_configured"
    if "*" not in st.email_allowlist and target not in st.email_allowlist:  # "*" = send to any address
        return target, "not_on_allowlist"
    return target, "deliverable"


async def compose(s: AsyncSession, actor: Actor, recipients: list[User], *, kind: str, subject: str, body: str,
                  channels: list[str], receipt_id: int | None) -> dict:
    batch = uuid.uuid4().hex
    counts = {"inbox": 0, "email_queued": 0, "email_skipped": 0}
    for u in recipients:
        if "inbox" in channels:
            s.add(Message(workspace_id=actor.workspace_id, ref="pending", kind=kind, channel="inbox", sender_id=actor.user_id,
                          recipient_user_id=u.id, subject=subject, body=body, status="delivered", batch_id=batch, receipt_id=receipt_id))
            counts["inbox"] += 1
        if "email" in channels:
            to, verdict = email_plan(u)
            ok = verdict == "deliverable"
            s.add(Message(workspace_id=actor.workspace_id, ref="pending", kind=kind, channel="email", sender_id=actor.user_id,
                          recipient_user_id=u.id, email_to=to, subject=subject, body=body,
                          status="queued" if ok else "skipped", status_detail=None if ok else verdict, batch_id=batch,
                          receipt_id=receipt_id))
            counts["email_queued" if ok else "email_skipped"] += 1
    await s.flush()
    for m in (await s.execute(select(Message).where(Message.batch_id == batch))).scalars():
        m.ref = f"M{m.id}"
    return {"batch_id": batch, **counts}


def _send_smtp(to: str, subject: str, body: str) -> str:
    st = get_settings()
    msg = EmailMessage()
    msg["From"] = f"Purser <{st.gmail_address}>"
    msg["To"] = to
    msg["Subject"] = " ".join(subject.split())[:200]  # header values may not contain newlines
    msg["Message-ID"] = make_msgid(domain="purser.demo")
    msg.set_content(body + "\n\n— Sent by Purser (hackathon demo, synthetic company data)")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
        smtp.login(st.gmail_address, st.gmail_app_password)
        smtp.send_message(msg)
    return msg["Message-ID"]


async def dispatch(limit: int = 20) -> int:
    """Send queued emails. Each row is claimed with SKIP LOCKED so concurrent dispatchers never double-send."""
    sent = 0
    for _ in range(limit):
        async with db.session_scope() as s:
            m = (await s.execute(select(Message).where(Message.channel == "email", Message.status == "queued")
                                 .order_by(Message.id).limit(1).with_for_update(skip_locked=True))).scalars().first()
            if m is None:
                return sent
            try:
                m.provider_id = await asyncio.to_thread(_send_smtp, m.email_to, m.subject, m.body)
                m.status, m.sent_at = "sent", datetime.now(UTC)
                sent += 1
            except Exception as e:  # keep the error, never retry blindly (acceptance unknown -> manual check)
                m.status, m.status_detail = "failed", f"{type(e).__name__}: {str(e)[:200]}"
                log.warning("email failed %s: %s", m.ref, m.status_detail)
    return sent


def dispatch_soon() -> None:
    try:
        asyncio.get_running_loop().create_task(dispatch())
    except RuntimeError:
        pass
