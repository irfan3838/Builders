"""Spoken confirmation is valid only from a server-observed user turn that started after the
preview was presented. A model or browser claiming "the user said yes" is never evidence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actor import Actor
from app.errors import CONFIRMATION_REQUIRED, DomainError
from app.models import Proposal, VoiceTurn
from app.services.affirmation import Affirmation, classify

SERVER_OBSERVED = ("live_sideband", "realtime_sideband", "ptt_server", "text")


async def record_turn(
    s: AsyncSession,
    actor: Actor,
    transcript: str,
    *,
    source: str,
    start_ms: int | None = None,
    end_ms: int | None = None,
    completed: bool = True,
    interrupted: bool = False,
) -> VoiceTurn:
    assert source in SERVER_OBSERVED
    t = VoiceTurn(
        workspace_id=actor.workspace_id,
        conversation_id=actor.conversation_id,
        source=source,
        transcript=transcript,
        start_ms=start_ms,
        end_ms=end_ms,
        completed=completed,
        interrupted=interrupted,
    )
    s.add(t)
    await s.flush()
    return t


async def spoken_confirmation(s: AsyncSession, actor: Actor, p: Proposal) -> dict:
    """Return evidence for confirming `p`, or raise CONFIRMATION_REQUIRED with the reason."""
    if p.presented_at is None:
        raise DomainError(CONFIRMATION_REQUIRED, "The preview has not been presented yet. Present it and wait for the user's reply.")
    if p.conversation_id != actor.conversation_id:
        raise DomainError(CONFIRMATION_REQUIRED, "This proposal belongs to another conversation.")
    q = (
        select(VoiceTurn)
        .where(VoiceTurn.conversation_id == actor.conversation_id, VoiceTurn.source.in_(SERVER_OBSERVED))
        .order_by(VoiceTurn.id.desc())
        .limit(1)
    )
    turn = (await s.execute(q)).scalars().first()
    if turn is None or turn.created_at <= p.presented_at:
        raise DomainError(CONFIRMATION_REQUIRED, "No reply from the user after the preview yet. Ask for confirmation.")
    if p.presented_offset_ms is not None and turn.start_ms is not None and turn.start_ms < p.presented_offset_ms:
        raise DomainError(CONFIRMATION_REQUIRED, "The user's reply began before the preview finished. Ask again.")
    if not turn.completed or turn.interrupted:
        raise DomainError(CONFIRMATION_REQUIRED, "The reply was interrupted. Ask again.")
    verdict = classify(turn.transcript)
    if verdict is not Affirmation.AFFIRM:
        raise DomainError(
            CONFIRMATION_REQUIRED,
            "The user's latest reply is not a clear yes. Do not execute; address what they said or ask again.",
            heard=turn.transcript,
            classification=verdict.value,
        )
    return {"turn_id": turn.id, "source": turn.source, "transcript": turn.transcript, "classification": verdict.value}
