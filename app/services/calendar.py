"""Google Calendar + Meet: create the event for a confirmed meeting, after the confirming transaction commits.

The event id is chosen by us when the meeting is queued, so a retried or replayed create returns the existing event
instead of making a duplicate. Google emails the invites (sendUpdates=all) to every guest address.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx
from sqlalchemy import select

from app import db
from app.config import get_settings
from app.models import Meeting, Message

log = logging.getLogger("purser.calendar")

TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


class CalendarError(Exception):
    pass


async def _access_token(client: httpx.AsyncClient) -> str:
    st = get_settings()
    r = await client.post(TOKEN_URL, data={"client_id": st.google_client_id, "client_secret": st.google_client_secret,
                                           "refresh_token": st.google_refresh_token, "grant_type": "refresh_token"})
    if r.status_code != 200:
        err = r.json().get("error", r.status_code) if r.headers.get("content-type", "").startswith("application/json") else r.status_code
        if err == "invalid_grant":
            raise CalendarError("Google login expired or was revoked; run scripts/google_oauth.py again.")
        raise CalendarError(f"Google token refresh failed ({err}).")
    return r.json()["access_token"]


def event_body(m: Meeting) -> dict:
    return {
        "id": m.google_event_id,
        "summary": m.title,
        "description": (m.description or "") + ("\n\n" if m.description else "") + "Scheduled by Purser.",
        "start": {"dateTime": m.start_at.isoformat(), "timeZone": m.timezone},
        "end": {"dateTime": m.end_at.isoformat(), "timeZone": m.timezone},
        "attendees": [{"email": e} for e in m.guest_emails],
        "conferenceData": {"createRequest": {"requestId": m.google_event_id,
                                             "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
        "reminders": {"useDefault": True},
    }


def _meet_url(ev: dict) -> str | None:
    if ev.get("hangoutLink"):
        return ev["hangoutLink"]
    for ep in (ev.get("conferenceData") or {}).get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            return ep.get("uri")
    return None


def _google_error(r: httpx.Response) -> str:
    try:
        return r.json()["error"]["message"][:200]
    except Exception:
        return r.text[:200]


async def create_event(m: Meeting) -> tuple[str | None, str | None]:
    """Create (or fetch, if it already exists) the Google event. Returns (meet_url, event_url)."""
    params = {"conferenceDataVersion": 1, "sendUpdates": "all"}
    async with httpx.AsyncClient(timeout=20) as client:
        headers = {"Authorization": f"Bearer {await _access_token(client)}"}
        r = await client.post(EVENTS_URL, params=params, headers=headers, json=event_body(m))
        if r.status_code == 409:  # already created by an earlier attempt: same event id
            r = await client.get(f"{EVENTS_URL}/{m.google_event_id}", headers=headers)
        if r.status_code >= 400:
            raise CalendarError(f"Google Calendar HTTP {r.status_code}: {_google_error(r)}")
        ev = r.json()
        for _ in range(3):  # Meet creation is usually immediate; it can briefly be "pending"
            if _meet_url(ev) or (ev.get("conferenceData") or {}).get("createRequest", {}).get("status", {}).get("statusCode") != "pending":
                break
            await asyncio.sleep(1)
            ev = (await client.get(f"{EVENTS_URL}/{m.google_event_id}", headers=headers)).json()
    return _meet_url(ev), ev.get("htmlLink")


def when_text(m: Meeting) -> str:
    from zoneinfo import ZoneInfo
    start = m.start_at.astimezone(ZoneInfo(m.timezone))
    end = m.end_at.astimezone(ZoneInfo(m.timezone))
    return f"{start:%a %d %b %Y, %I:%M %p} to {end:%I:%M %p}".replace(" 0", " ")


async def _notify(s, m: Meeting) -> None:
    """Inbox copy with the Meet link for the organizer and every internal attendee."""
    users = list(dict.fromkeys([m.organizer_id, *m.attendee_user_ids]))
    body = (f"{m.title}\nWhen: {when_text(m)} ({m.timezone})\n"
            + (f"Google Meet: {m.meet_url}\n" if m.meet_url else "")
            + (f"\n{m.description}" if m.description else ""))
    rows = [Message(workspace_id=m.workspace_id, ref="pending", kind="meeting", channel="inbox", sender_id=m.organizer_id,
                    recipient_user_id=uid, subject=f"{'Interview' if m.kind == 'interview' else 'Meeting'}: {m.title}"[:200],
                    body=body, status="delivered", receipt_id=m.receipt_id) for uid in users]
    s.add_all(rows)
    await s.flush()
    for row in rows:
        row.ref = f"M{row.id}"


async def dispatch(limit: int = 10) -> int:
    """Create queued meetings at Google. Rows are claimed with SKIP LOCKED so concurrent dispatchers never double-create."""
    if not get_settings().calendar_enabled:
        return 0
    done = 0
    for _ in range(limit):
        async with db.session_scope() as s:
            m = (await s.execute(select(Meeting).where(Meeting.status == "queued").order_by(Meeting.id).limit(1)
                                 .with_for_update(skip_locked=True))).scalars().first()
            if m is None:
                return done
            try:
                m.meet_url, m.event_url = await create_event(m)
                m.status = "created"
                m.status_detail = None if m.meet_url else "event created without a Meet link"
                await _notify(s, m)
                done += 1
            except Exception as e:  # keep the error; the event id makes a manual retry safe
                m.status, m.status_detail = "failed", f"{type(e).__name__}: {str(e)[:250]}"
                log.warning("meeting %s failed: %s", m.ref, m.status_detail)
    return done


def is_future(start: datetime) -> bool:
    from datetime import UTC
    return start > datetime.now(UTC)
