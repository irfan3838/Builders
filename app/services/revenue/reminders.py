"""Reminders ("remind me Friday to chase Acme"): in-app, shown in the bell when they fall due.
Ported from copilot services/reminders.py, workspace-scoped. Non-financial: written directly, audited."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Reminder
from app.services.revenue.core import TEXT_MAX, Rev, conflict, invalid, log, not_found, utcnow


def open_reminders(ss: Session, rv: Rev) -> list[Reminder]:
    return list(ss.scalars(select(Reminder).options(selectinload(Reminder.client))
                           .where(Reminder.workspace_id == rv.ws, Reminder.done_at.is_(None))
                           .order_by(Reminder.due_on, Reminder.created_at, Reminder.id)))


def due(ss: Session, rv: Rev) -> list[Reminder]:
    return [r for r in open_reminders(ss, rv) if r.due_on <= rv.today]


def add(ss: Session, rv: Rev, *, due_on: date, text: str, client_id: int | None = None,
        invoice_id: int | None = None) -> Reminder:
    text = " ".join((text or "").split())
    if not text or len(text) > TEXT_MAX:
        raise invalid("A reminder needs a note (up to 200 characters)", field="text")
    r = Reminder(workspace_id=rv.ws, due_on=due_on, text=text, client_id=client_id, invoice_id=invoice_id,
                 created_by=rv.actor_id)
    ss.add(r)
    ss.flush()
    log(ss, rv, "reminder_added", record_type="reminder", record_id=r.id, after={"due_on": due_on.isoformat(), "text": text})
    return r


def done(ss: Session, rv: Rev, reminder_id: int) -> Reminder:
    r = ss.get(Reminder, reminder_id)
    if r is None or r.workspace_id != rv.ws:
        raise not_found("No such reminder")
    if r.done_at is not None:
        raise conflict("That reminder is already done")
    r.done_at = utcnow()
    ss.flush()
    log(ss, rv, "reminder_done", record_type="reminder", record_id=r.id, before={"text": r.text})
    return r


def view(r: Reminder, today: date) -> dict:
    return {"id": r.id, "due_on": r.due_on.isoformat(), "text": r.text, "client": r.client.name if r.client else None,
            "due": r.due_on <= today}
