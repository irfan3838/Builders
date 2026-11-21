"""Google Calendar reads and changes for the linked account (creation with Meet stays in app/services/calendar.py)."""

from __future__ import annotations

from datetime import datetime

from app.services.google.auth import call

EVENTS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def view(ev: dict) -> dict:
    start, end = ev.get("start", {}), ev.get("end", {})
    meet = ev.get("hangoutLink") or next((e.get("uri") for e in (ev.get("conferenceData") or {}).get("entryPoints", [])
                                          if e.get("entryPointType") == "video"), None)
    return {"event_id": ev["id"], "title": ev.get("summary") or "(no title)", "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"), "all_day": "date" in start and "dateTime" not in start,
            "location": ev.get("location"), "meet_url": meet, "organizer": (ev.get("organizer") or {}).get("email"),
            "attendees": [a.get("email") for a in ev.get("attendees", []) if a.get("email")][:10],
            "status": ev.get("status"), "url": ev.get("htmlLink")}


async def list_events(start: datetime, end: datetime, max_results: int = 25) -> list[dict]:
    r = await call("GET", EVENTS, params={"timeMin": start.isoformat(), "timeMax": end.isoformat(), "singleEvents": "true",
                                          "orderBy": "startTime", "maxResults": max(1, min(max_results, 50))})
    return [view(e) for e in r.get("items", []) if e.get("status") != "cancelled"]


async def get_event(event_id: str) -> dict:
    return view(await call("GET", f"{EVENTS}/{event_id}"))


async def move_event(event_id: str, start: datetime, end: datetime, tz: str) -> dict:
    body = {"start": {"dateTime": start.isoformat(), "timeZone": tz}, "end": {"dateTime": end.isoformat(), "timeZone": tz}}
    return view(await call("PATCH", f"{EVENTS}/{event_id}", params={"sendUpdates": "all"}, json=body))


async def delete_event(event_id: str) -> dict:
    await call("DELETE", f"{EVENTS}/{event_id}", params={"sendUpdates": "all"})
    return {"event_id": event_id, "deleted": True}


async def create_simple(title: str, start: datetime, end: datetime, tz: str, description: str = "") -> dict:
    """A plain event with no guests and no Meet link (for example a flight hold)."""
    body = {"summary": title, "description": description, "start": {"dateTime": start.isoformat(), "timeZone": tz},
            "end": {"dateTime": end.isoformat(), "timeZone": tz}, "reminders": {"useDefault": True}}
    return view(await call("POST", EVENTS, json=body))
