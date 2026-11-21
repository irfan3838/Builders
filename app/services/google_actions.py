"""Confirmed changes on the linked Google account: send/reply email, inbox housekeeping, move or cancel an event.

Same contract as every other write: plan() is a side-effect-free preview (it may READ Google to show exactly what will
change); execute() runs inside the confirm transaction and only queues a GoogleOp; dispatch() performs it after commit.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app import db
from app.config import get_settings
from app.errors import FORBIDDEN, VALIDATION, DomainError
from app.models import GoogleOp
from app.services import audit
from app.services.actions import Execution, Plan
from app.services.google import gcal, gmail
from app.services.google.auth import GoogleError

log = logging.getLogger("purser.google")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAIL_ACTIONS = {"archive": ([], ["INBOX"]), "mark_read": ([], ["UNREAD"]), "mark_unread": (["UNREAD"], []),
                "star": (["STARRED"], []), "unstar": ([], ["STARRED"]), "move_to_inbox": (["INBOX"], [])}


def _require_google(actor) -> None:
    if not actor.uses_google:
        raise DomainError(FORBIDDEN, "Gmail and Google Calendar are connected only for the linked account; this login uses the Purser inbox and the Purser calendar.")


def _emails(values: list[str] | None, what: str) -> list[str]:
    out = []
    for v in values or []:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise DomainError(VALIDATION, f"'{v}' is not a valid {what} email address. Spell it out and try again.")
        out.append(v)
    return list(dict.fromkeys(out))


def _local(text: str) -> datetime:
    tz = ZoneInfo(get_settings().calendar_timezone)
    try:
        d = datetime.fromisoformat(text.strip())
    except ValueError:
        raise DomainError(VALIDATION, "Give the new time as YYYY-MM-DDTHH:MM.") from None
    return d if d.tzinfo else d.replace(tzinfo=tz)


async def _wrap(coro):
    try:
        return await coro
    except GoogleError as e:
        raise DomainError("GOOGLE_UNAVAILABLE", str(e)) from None


async def _queue(s, actor, kind: str, payload: dict, receipt_id: int, summary: str) -> Execution:
    op = GoogleOp(workspace_id=actor.workspace_id, user_id=actor.user_id, ref="pending", kind=kind, payload=payload,
                  status="queued", receipt_id=receipt_id)
    s.add(op)
    await s.flush()
    op.ref = f"G{op.id}"
    await audit.record(s, actor, f"google.{kind}", record_type="google_op", record_id=op.id, record_ref=op.ref,
                       after={k: v for k, v in payload.items() if k != "body"}, receipt_id=receipt_id)
    return Execution(f"{summary} ({op.ref}); doing it in Google now.", [{"type": "google_op", "ref": op.ref, "kind": kind}])


class SendEmail:
    kind = "gmail_send"

    async def _resolve(self, args: dict) -> dict:
        body = (args.get("body") or "").strip()
        if not body:
            raise DomainError(VALIDATION, "The email needs a body.")
        if len(body) > 5000:
            raise DomainError(VALIDATION, "Keep the email under 5,000 characters.")
        out = {"body": body, "cc": _emails(args.get("cc"), "cc")}
        if args.get("reply_thread_id"):
            ctx = await _wrap(gmail.reply_context(args["reply_thread_id"]))
            out.update(to=_emails(args.get("to"), "recipient") or ctx["to"], subject=args.get("subject") or ctx["subject"],
                       thread_id=ctx["thread_id"], in_reply_to=ctx["in_reply_to"], references=ctx["references"],
                       replying_to=ctx["replying_to"])
        else:
            out.update(to=_emails(args.get("to"), "recipient"), subject=(args.get("subject") or "").strip())
            if not out["subject"]:
                raise DomainError(VALIDATION, "The email needs a subject.")
        if not out["to"]:
            raise DomainError(VALIDATION, "Who should the email go to? Give an email address.")
        return out

    async def plan(self, s, actor, args):
        _require_google(actor)
        r = await self._resolve(args)
        lines = [f"From: {actor.email} (your Gmail)", f"To: {', '.join(r['to'])}"]
        if r["cc"]:
            lines.append(f"Cc: {', '.join(r['cc'])}")
        if r.get("replying_to"):
            lines.append(f"Reply in the thread: {r['replying_to']}")
        lines += [f"Subject: {r['subject']}", "", r["body"]]
        verb = "Send this reply" if r.get("thread_id") else "Send this email"
        return Plan("Send email from Gmail", lines, f"{verb} to {', '.join(r['to'][:2])}?", [])

    async def execute(self, s, actor, args, receipt_id):
        _require_google(actor)
        r = await self._resolve(args)
        return await _queue(s, actor, "send_email", {**r, "sender": actor.email}, receipt_id,
                            f"Email '{r['subject']}' to {', '.join(r['to'][:2])} queued")


class MailAction:
    kind = "gmail_action"

    async def plan(self, s, actor, args):
        _require_google(actor)
        ids, action = list(dict.fromkeys(args.get("message_ids") or []))[:25], args.get("action")
        if not ids:
            raise DomainError(VALIDATION, "Which emails? Search the inbox first and pass their ids.")
        if action not in MAIL_ACTIONS and action != "label":
            raise DomainError(VALIDATION, f"Unknown action {action}. Use archive, mark_read, mark_unread, star, unstar, move_to_inbox or label.")
        if action == "label" and not (args.get("label") or "").strip():
            raise DomainError(VALIDATION, "Which label?")
        what = {"archive": "Archive", "mark_read": "Mark as read", "mark_unread": "Mark as unread", "star": "Star", "unstar": "Unstar",
                "move_to_inbox": "Move back to the inbox", "label": f"Add the label '{args.get('label')}' to"}[action]
        titles = args.get("titles") or []
        lines = [f"{what} {len(ids)} email{'s' if len(ids) > 1 else ''} in your Gmail."] + [f"• {t}" for t in titles[:8]]
        return Plan("Gmail inbox change", lines, f"{what} {len(ids)} email{'s' if len(ids) > 1 else ''}?", [])

    async def execute(self, s, actor, args, receipt_id):
        _require_google(actor)
        return await _queue(s, actor, "mail_action", {"ids": list(dict.fromkeys(args["message_ids"]))[:25], "action": args["action"],
                                                       "label": args.get("label")}, receipt_id, f"Gmail {args['action'].replace('_', ' ')}")


class RescheduleEvent:
    kind = "gcal_reschedule"

    async def plan(self, s, actor, args):
        _require_google(actor)
        ev = await _wrap(gcal.get_event(args["event_id"]))
        start = _local(args["start"])
        if ev["all_day"]:
            raise DomainError(VALIDATION, "That is an all-day event; I can only move timed meetings.")
        old_s, old_e = datetime.fromisoformat(ev["start"]), datetime.fromisoformat(ev["end"])
        minutes = int(args.get("minutes") or (old_e - old_s).total_seconds() // 60)
        end = start + timedelta(minutes=minutes)
        lines = [f"Event: {ev['title']}", f"From: {old_s:%a %d %b, %I:%M %p}".replace(" 0", " "),
                 f"To: {start:%a %d %b, %I:%M %p} – {end:%I:%M %p}".replace(" 0", " "),
                 "Google emails the updated time to every guest." if ev["attendees"] else "No guests to notify."]
        return Plan("Reschedule meeting", lines, f"Move '{ev['title']}' to {start:%a %d %b at %I:%M %p}?".replace(" 0", " "), [])

    async def execute(self, s, actor, args, receipt_id):
        _require_google(actor)
        ev = await _wrap(gcal.get_event(args["event_id"]))
        start = _local(args["start"])
        old_s, old_e = datetime.fromisoformat(ev["start"]), datetime.fromisoformat(ev["end"])
        minutes = int(args.get("minutes") or (old_e - old_s).total_seconds() // 60)
        return await _queue(s, actor, "reschedule_event", {"event_id": args["event_id"], "title": ev["title"], "start": start.isoformat(),
                                                            "end": (start + timedelta(minutes=minutes)).isoformat(),
                                                            "tz": get_settings().calendar_timezone},
                            receipt_id, f"'{ev['title']}' moved")


class CancelEvent:
    kind = "gcal_cancel"

    async def plan(self, s, actor, args):
        _require_google(actor)
        ev = await _wrap(gcal.get_event(args["event_id"]))
        lines = [f"Event: {ev['title']}", f"When: {ev['start']}",
                 "Google emails a cancellation to every guest." if ev["attendees"] else "No guests to notify."]
        return Plan("Cancel meeting", lines, f"Cancel '{ev['title']}'?", [])

    async def execute(self, s, actor, args, receipt_id):
        _require_google(actor)
        ev = await _wrap(gcal.get_event(args["event_id"]))
        return await _queue(s, actor, "cancel_event", {"event_id": args["event_id"], "title": ev["title"]}, receipt_id,
                            f"'{ev['title']}' cancelled")


GOOGLE_ACTIONS = (SendEmail(), MailAction(), RescheduleEvent(), CancelEvent())


async def _label_id(name: str) -> str:
    for lab in await gmail.labels():
        if lab.get("name", "").lower() == name.strip().lower():
            return lab["id"]
    from app.services.google.auth import call
    made = await call("POST", f"{gmail.BASE}/labels", json={"name": name.strip()[:60]})
    return made["id"]


async def perform(op: GoogleOp) -> dict:
    p = op.payload
    if op.kind == "send_email":
        r = await gmail.send(p["sender"], p["to"], p["subject"], p["body"], cc=p.get("cc"), thread_id=p.get("thread_id"),
                             in_reply_to=p.get("in_reply_to"), references=p.get("references"))
        return {"gmail_id": r.get("id"), "thread_id": r.get("threadId")}
    if op.kind == "mail_action":
        if p["action"] == "label":
            add, remove = [await _label_id(p["label"])], []
        else:
            add, remove = MAIL_ACTIONS[p["action"]]
        await gmail.modify(p["ids"], add, remove)
        return {"modified": len(p["ids"])}
    if op.kind == "reschedule_event":
        ev = await gcal.move_event(p["event_id"], datetime.fromisoformat(p["start"]), datetime.fromisoformat(p["end"]), p["tz"])
        return {"event_id": ev["event_id"], "start": ev["start"]}
    if op.kind == "cancel_event":
        return await gcal.delete_event(p["event_id"])
    if op.kind == "create_event":
        ev = await gcal.create_simple(p["title"], datetime.fromisoformat(p["start"]), datetime.fromisoformat(p["end"]), p["tz"],
                                      p.get("description", ""))
        return {"event_id": ev["event_id"], "url": ev["url"]}
    raise ValueError(f"unknown google op {op.kind}")


async def dispatch(limit: int = 10) -> int:
    """Perform queued Google ops once each (SKIP LOCKED; a failure is kept, never retried blindly)."""
    if not get_settings().calendar_enabled:
        return 0
    done = 0
    for _ in range(limit):
        async with db.session_scope() as s:
            op = (await s.execute(select(GoogleOp).where(GoogleOp.status == "queued").order_by(GoogleOp.id).limit(1)
                                  .with_for_update(skip_locked=True))).scalars().first()
            if op is None:
                return done
            try:
                op.result = await perform(op)
                op.status = "done"
                done += 1
            except Exception as e:
                op.status, op.status_detail = "failed", f"{type(e).__name__}: {str(e)[:250]}"
                log.warning("google op %s failed: %s", op.ref, op.status_detail)
    return done
