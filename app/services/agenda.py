"""The user's meetings for a time window: real Google Calendar for the linked login, Purser meetings otherwise."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select

from app import db
from app.actor import Actor
from app.config import get_settings
from app.models import Meeting, User
from app.services.google import gcal


async def meetings(actor: Actor, start: datetime, end: datetime) -> tuple[list[dict], str]:
    """Returns (events, source). Google errors propagate (callers decide whether to degrade)."""
    if actor.uses_google:
        return await gcal.list_events(start, end), "google_calendar"
    tz = ZoneInfo(get_settings().calendar_timezone)
    async with db.session_scope() as s:
        rows = (await s.execute(select(Meeting).where(
            Meeting.workspace_id == actor.workspace_id, Meeting.start_at >= start, Meeting.start_at < end,
            or_(Meeting.organizer_id == actor.user_id, Meeting.attendee_user_ids.contains([actor.user_id]))).order_by(Meeting.start_at))).scalars().all()
        names = dict((await s.execute(select(User.id, User.display_name).where(User.workspace_id == actor.workspace_id))).all())
    return [{"event_id": m.ref, "title": m.title, "start": m.start_at.astimezone(tz).isoformat(), "end": m.end_at.astimezone(tz).isoformat(),
             "all_day": False, "meet_url": m.meet_url, "organizer": names.get(m.organizer_id),
             "attendees": [names.get(u, "") for u in m.attendee_user_ids][:10] + m.guest_emails[:5]} for m in rows], "purser"
