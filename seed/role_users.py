"""Idempotent: the three role logins used in the demo, added to the existing (synthetic) workspace.

  irfmed38@gmail.com    admin    "Irfan"    - main access; the ONLY login whose real Gmail + Calendar Purser uses
  irfan@dzruptiv.ai     ceo      "CEO"      - read-only executive
  ia383813@gmail.com    employee "Employee" - no company finance access

Run after seed_v1:  python -m seed.role_users   (safe to run again; the three logins always get the agreed role and name).
It also gives the three logins day-to-day activity (meetings, tasks, a ticket, a leave request, inbox messages) and
removes test labels from display text in the database (company and client names, policies, memos, contracts).
Honest disclosure of what is generated lives in docs/SUBMISSION.md, not in the product UI.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from argon2 import PasswordHasher
from sqlalchemy import select, text

from app import db
from app.models import LeaveRequest, Meeting, Message, Party, Task, Ticket, User, Workspace
from app.services import people
from app.services.records import normalize_name, today_ist

IST = ZoneInfo("Asia/Kolkata")

# (email, display name, role, department, designation)
ROLE_USERS = [
    ("irfmed38@gmail.com", "Irfan", "admin", "Leadership", "Founder & Admin"),
    ("irfan@dzruptiv.ai", "CEO", "ceo", "Leadership", "Chief Executive Officer"),
    ("ia383813@gmail.com", "Employee", "employee", "Sales", "Sales Executive"),
]


def _at(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm), tzinfo=IST)


async def seed_roles(s) -> dict:
    ph = PasswordHasher()
    pw = ph.hash(os.getenv("SEED_PASSWORD", "purser-demo"))
    ws = (await s.execute(select(Workspace).order_by(Workspace.id))).scalars().first()
    if ws is None:
        raise SystemExit("No workspace: run python -m seed.seed_v1 --reset [--demo] first.")
    W = ws.id
    admin = (await s.execute(select(User).where(User.workspace_id == W, User.role == "admin").order_by(User.id))).scalars().first()
    made: dict[str, int] = {}
    for email, name, role, dept, title in ROLE_USERS:
        u = (await s.execute(select(User).where(User.email == email))).scalars().first()
        if u is None:
            p = Party(workspace_id=W, kind="employee", name=name, normalized_name=normalize_name(name), aliases=[])
            s.add(p)
            await s.flush()
            u = User(workspace_id=W, email=email, display_name=name, role=role, password_hash=pw, party_id=p.id,
                     preferred_language="english", department=dept, designation=title, start_date=date(2024, 4, 1),
                     reports_to_id=admin.id if (admin and role == "employee") else None,
                     notify_email=email if not email.endswith("@purser.demo") else None)
            s.add(u)
            await s.flush()
            fy = "FY2026-27"
            for code, (_, days) in people.LEAVE_TYPES.items():
                await people.post_leave(s, W, u.id, code, "granted", days, "annual_grant", memo=f"{fy} grant")
        else:  # already there: enforce the agreed role and name (never silently keep an old role)
            u.role, u.display_name, u.status = role, name, "active"
        made[role] = u.id

    # Purser-calendar meetings (DB only) for the CEO and employee logins.
    today = today_ist()
    ceo, emp = made["ceo"], made["employee"]
    demo = [
        (ceo, [emp], "Weekly leadership sync", today, 11, 30),
        (ceo, [], "Board pre-read review", today, 16, 45),
        (emp, [ceo], "Q3 sales pipeline review", today, 15, 30),
        (emp, [], "Client call: Nimbus Retail renewal", today + timedelta(days=1), 10, 60),
        (ceo, [], "Investor update call", today + timedelta(days=1), 12, 30),
    ]
    n = 0
    for org, att, title, d, hh, mins in demo:
        exists = (await s.execute(select(Meeting.id).where(Meeting.workspace_id == W, Meeting.title == title,
                                                           Meeting.organizer_id == org, Meeting.start_at == _at(d, hh)))).first()
        if exists:
            continue
        m = Meeting(workspace_id=W, ref="pending", kind="meeting", title=title, description=None,
                    start_at=_at(d, hh), end_at=_at(d, hh) + timedelta(minutes=mins), timezone="Asia/Kolkata",
                    organizer_id=org, attendee_user_ids=att, guest_emails=[], google_event_id=uuid.uuid4().hex,
                    status="saved", status_detail=None)
        s.add(m)
        await s.flush()
        m.ref = f"MT{m.id}"
        n += 1
    # Tasks and one helpdesk ticket so the home screens have items.
    admin_id = made["admin"]
    tasks = [
        (emp, admin_id, "Send the Nimbus Retail renewal proposal", today, "high"),
        (emp, emp, "Submit October cab receipts", today - timedelta(days=2), "normal"),
        (emp, admin_id, "Update the Q3 pipeline sheet", today + timedelta(days=3), "normal"),
        (admin_id, admin_id, "Review the vendor contract renewals", today + timedelta(days=1), "high"),
        (admin_id, admin_id, "Approve pending reimbursements before payroll", today, "normal"),
    ]
    t_added = 0
    for who, by, title, due, pr in tasks:
        if (await s.execute(select(Task.id).where(Task.workspace_id == W, Task.assignee_id == who, Task.title == title))).first():
            continue
        t = Task(workspace_id=W, ref="pending", title=title, assignee_id=who, created_by=by, due_on=due, priority=pr, status="open")
        s.add(t)
        await s.flush()
        t.ref = f"T{t.id}"
        t_added += 1
    if not (await s.execute(select(Ticket.id).where(Ticket.workspace_id == W, Ticket.requester_id == emp))).first():
        tk = Ticket(workspace_id=W, ref="pending", requester_id=emp, category="it", title="Laptop battery drains in an hour",
                    description="Dell Latitude, since last week. Need a replacement battery or charger.", priority="normal",
                    status="in_progress", assignee_id=admin_id)
        s.add(tk)
        await s.flush()
        tk.ref = f"HD{tk.id}"
    # The employee reports to the main admin, so their leave lands in the admin's approvals.
    emp_user = await s.get(User, emp)
    emp_user.reports_to_id = admin_id
    if not (await s.execute(select(LeaveRequest.id).where(LeaveRequest.workspace_id == W, LeaveRequest.user_id == emp))).first():
        a, b = today + timedelta(days=10), today + timedelta(days=11)
        while a.weekday() >= 5:
            a, b = a + timedelta(days=1), b + timedelta(days=1)
        days = people.working_days(a, b)
        lr = LeaveRequest(workspace_id=W, ref="pending", user_id=emp, submitted_by=emp, leave_type="CL", start_date=a, end_date=b,
                          days=days, reason="Family function in Coimbatore", state="submitted")
        s.add(lr)
        await s.flush()
        lr.ref = f"L{lr.id}"
        await people.post_leave(s, W, emp, "CL", "reserved", days, "leave_requested", source_id=lr.id)
    inbox = [
        (emp, admin_id, "announcement", "Q3 sales kickoff on Monday", "Team, the Q3 kickoff is on Monday at 10 AM in the main conference room. Please bring your pipeline updates."),
        (emp, admin_id, "message", "Reimbursement policy update", "Cab claims above Rs 1,500 now need the trip purpose in the description. Submit receipts within 30 days."),
        (ceo, admin_id, "message", "Board pack ready for review", "The board pack draft is ready. Revenue and budget sections are updated as of this week."),
    ]
    for to_id, frm, kind, subj, body in inbox:
        if (await s.execute(select(Message.id).where(Message.workspace_id == W, Message.recipient_user_id == to_id, Message.subject == subj))).first():
            continue
        msg = Message(workspace_id=W, ref="pending", kind=kind, channel="inbox", sender_id=frm, recipient_user_id=to_id, subject=subj,
                      body=body, status="delivered")
        s.add(msg)
        await s.flush()
        msg.ref = f"M{msg.id}"
    for email in DISABLED_LOGINS:
        await s.execute(text("UPDATE users SET status = 'disabled' WHERE email = :e"), {"e": email})
    cleaned = await clean_labels(s)
    return {"users": made, "meetings_added": n, "tasks_added": t_added, "labels_cleaned": cleaned}


# Old logins that must not sign in any more (their records stay: claims, approvals, history).
DISABLED_LOGINS = ("irfan@purser.demo",)


# Display text only: strip test labels so the product never shows them. Idempotent; emails and ids are untouched.
_STRIP = r"\s*\((synthetic|SYNTHETIC|Synthetic demo policy\.?)\)"
LABEL_UPDATES = [
    ("parties", "name"), ("parties", "normalized_name"), ("trips", "purpose"), ("budget_movements", "memo"),
    ("contracts", "title"), ("documents", "filename"), ("audit_events", "record_ref"), ("policies", "body"),
]


async def clean_labels(s) -> int:
    n = 0
    for table, col in LABEL_UPDATES:
        r = await s.execute(text(f"UPDATE {table} SET {col} = regexp_replace({col}, :pat, '', 'g') WHERE {col} ~ :pat"), {"pat": _STRIP})
        n += r.rowcount or 0
    for sql in (
        "UPDATE parties SET normalized_name = regexp_replace(normalized_name, '\\s*synthetic\\M', '', 'g') WHERE normalized_name ~* 'synthetic'",
        "UPDATE audit_events SET record_ref = regexp_replace(record_ref, '\\s*\\((synthetic|SYNTHETIC)\\)?', '', 'g') WHERE record_ref ~* 'synthetic'",
        "UPDATE documents SET filename = regexp_replace(filename, '[_ -]*(synthetic|SYNTHETIC)', '', 'g') WHERE filename ~* 'synthetic'",
        "UPDATE documents SET filename = regexp_replace(filename, '^(live_)?demo_', '', 'g') WHERE filename ~* '^(live_)?demo_'",
        "UPDATE contracts SET text = regexp_replace(text, '(Munshi|Purser) Demo Traders', 'Purser Traders', 'g') WHERE text ~ 'Demo Traders'",
        "UPDATE contracts SET details = regexp_replace(regexp_replace(regexp_replace(details::text, '(Munshi|Purser) Demo Traders', 'Purser Traders', 'g'), ' ?\\((synthetic|SYNTHETIC)\\)', '', 'g'), 'SYNTHETIC TEST DOCUMENT - fictional parties, not a real agreement\\.', '', 'g')::jsonb WHERE details::text ~* 'synthetic|Demo Traders'",
        "UPDATE extractions SET fields = regexp_replace(regexp_replace(fields::text, '(Munshi|Purser) Demo Traders', 'Purser Traders', 'g'), ' ?\\((synthetic|SYNTHETIC)\\)', '', 'g')::jsonb, evidence = regexp_replace(regexp_replace(evidence::text, '(Munshi|Purser) Demo Traders', 'Purser Traders', 'g'), ' ?\\((synthetic|SYNTHETIC)\\)', '', 'g')::jsonb WHERE fields::text ~* 'synthetic|Demo Traders' OR evidence::text ~* 'synthetic|Demo Traders'",
        "UPDATE extractions SET fields = regexp_replace(regexp_replace(fields::text, 'SYNTHETIC TEST DOCUMENT ?- ?fictional parties, not a real agreement\\.?', '', 'g'), 'Synthetic test document; ?', '', 'g')::jsonb WHERE fields::text ~* 'synthetic test document'",
        "UPDATE workspaces SET name = 'Purser Traders Pvt Ltd' WHERE name ~* 'synthetic|demo'",
        "UPDATE contracts SET text = replace(replace(text, 'SYNTHETIC TEST DOCUMENT - fictional parties, not a real agreement.', ''), 'Purser Demo Traders', 'Purser Traders') WHERE text ~ 'SYNTHETIC|Purser Demo Traders'",
        "UPDATE meetings SET description = NULL, status = 'saved', status_detail = NULL WHERE status = 'demo' OR description ~* 'synthetic'",
        "UPDATE parties SET name = replace(name, 'Purser Demo Traders', 'Purser Traders') WHERE name ~ 'Purser Demo Traders'",
    ):
        n += (await s.execute(text(sql))).rowcount or 0
    return n


async def main() -> dict:
    sm = db.configure(None)
    async with sm() as s, s.begin():
        return await seed_roles(s)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    print(asyncio.run(main()))
