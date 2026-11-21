"""Login briefing: what matters right now for THIS user, without them asking.

Every figure comes from SQL or the Google APIs (never from a model). The fast model may only PICK one of the
rule-ranked candidates as the next best action and phrase why (3 s budget, rule fallback). Sections are typed
(kpi_strip | list) so the screen renders them generically, and the same payload is spoken by get_briefing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time as _time
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select

from app import db
from app.actor import Actor
from app.config import get_settings
from app.errors import DomainError
from app.models import Claim, LeaveRequest, Message, Task, Ticket, User
from app.money import format_inr
from app.services import agenda, people
from app.services.records import today_ist

log = logging.getLogger("purser.briefing")
_cache: dict[int, tuple[float, dict]] = {}
CACHE_S = 60
GOOGLE_TIMEOUT = 4.0


def _tz() -> ZoneInfo:
    return ZoneInfo(get_settings().calendar_timezone)


def _hm(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone(_tz()).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return iso


def _greeting(name: str) -> str:
    h = datetime.now(_tz()).hour
    part = "morning" if h < 12 else "afternoon" if h < 17 else "evening"
    return f"Good {part}, {name.split()[0]}."


async def _safe(coro, default, what: str, notes: list[str]):
    try:
        return await asyncio.wait_for(coro, GOOGLE_TIMEOUT)
    except Exception as e:  # a slow or failing source degrades its section only
        log.warning("briefing %s unavailable: %s", what, type(e).__name__)
        notes.append(f"{what} unavailable right now")
        return default


async def _meetings_today(a: Actor, notes: list[str]) -> tuple[list[dict], str]:
    tz = _tz()
    now = datetime.now(tz)
    start, end = datetime.combine(now.date(), time.min, tzinfo=tz), datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=tz)
    events, source = await _safe(agenda.meetings(a, start, end), ([], "unavailable"), "Calendar", notes)
    return events, source


async def _important_mail(a: Actor, notes: list[str]) -> list[dict]:
    if not a.uses_google:
        return []
    from app.services.google import gmail
    return await _safe(gmail.search("in:inbox is:unread newer_than:2d", 5), [], "Gmail", notes)


def _meeting_items(events: list[dict]) -> list[dict]:
    now = datetime.now(_tz())
    out = []
    for e in events:
        try:
            end = datetime.fromisoformat(e["end"])
        except (TypeError, ValueError):
            end = now
        done = end < now
        out.append({"title": e["title"], "sub": "All day" if e.get("all_day") else f"{_hm(e['start'])} – {_hm(e['end'])}",
                    "meta": "done" if done else ("Meet" if e.get("meet_url") else ""), "url": e.get("meet_url"),
                    "tone": "muted" if done else None})
    return out


async def _common(s, a: Actor) -> dict:
    today = today_ist()
    unread = (await s.execute(select(func.count()).select_from(Message).where(
        Message.workspace_id == a.workspace_id, Message.recipient_user_id == a.user_id, Message.channel == "inbox",
        Message.read_at.is_(None)))).scalar_one()
    tasks = (await s.execute(select(Task).where(Task.workspace_id == a.workspace_id, Task.assignee_id == a.user_id,
                                                Task.status == "open").order_by(Task.due_on.asc().nulls_last(), Task.id))).scalars().all()
    tickets = (await s.execute(select(Ticket).where(Ticket.workspace_id == a.workspace_id, Ticket.requester_id == a.user_id,
                                                    Ticket.status != "resolved").order_by(Ticket.id.desc()))).scalars().all()
    return {"today": today, "unread": int(unread), "tasks": tasks, "tickets": tickets}


def _task_items(tasks, today) -> list[dict]:
    out = []
    for t in tasks[:6]:
        if t.due_on and t.due_on < today:
            sub, tone = f"Overdue since {t.due_on:%d %b}", "warn"
        elif t.due_on == today:
            sub, tone = "Due today", "warn"
        else:
            sub, tone = (f"Due {t.due_on:%d %b}" if t.due_on else "No due date"), None
        out.append({"title": t.title, "sub": sub, "meta": t.ref, "tone": tone, "utterance": f"Mark task {t.ref} as done"})
    return out


def _task_candidates(tasks, today) -> list[dict]:
    c = []
    for t in tasks:
        if t.due_on and t.due_on <= today:
            late = t.due_on < today
            c.append({"score": 85 if late else 80, "title": f"Finish “{t.title}”",
                      "why": f"It was due {t.due_on:%d %b}." if late else "It is due today.",
                      "utterance": f"Tell me about task {t.ref}"})
    return c


def _meeting_candidates(events) -> list[dict]:
    now = datetime.now(_tz())
    c = []
    for e in events:
        try:
            st = datetime.fromisoformat(e["start"])
        except (TypeError, ValueError):
            continue
        mins = (st - now).total_seconds() / 60
        if 0 <= mins <= 60 and not e.get("all_day"):
            c.append({"score": 90, "title": f"Get ready for “{e['title']}”", "why": f"It starts at {_hm(e['start'])}, in {int(mins)} minutes.",
                      "utterance": f"Brief me for my {_hm(e['start'])} meeting"})
    return c


async def _admin(s, a: Actor, base: dict, notes: list[str]) -> tuple[list[dict], list[dict]]:
    from app.agent.tools.finance import _attention
    from app.services import budget_months as bm
    att = await _attention(s, a)
    try:
        alerts = (await bm.alerts(s, a, base["today"]))["alerts"]
    except DomainError:
        alerts = []
    approvals = [i for i in att if i["kind"].endswith("awaiting_approval")]
    overdue = [i for i in att if "overdue" in i["kind"]]
    kpis = [{"label": "Approvals waiting", "value": str(len(approvals)), "tone": "warn" if approvals else None, "utterance": "What needs my approval?"},
            {"label": "Overdue invoices", "value": str(len(overdue)), "tone": "warn" if overdue else None, "utterance": "Which client invoices are overdue?"},
            {"label": "Budget alerts", "value": str(len(alerts)), "tone": "warn" if alerts else None, "utterance": "Any budget alerts?"},
            {"label": "Open tasks", "value": str(len(base["tasks"])), "utterance": "What are my tasks?"}]
    pri = []
    for i in att[:5]:
        amt = i.get("amount") or ""
        pri.append({"title": f"{i['kind'].replace('_', ' ').capitalize()}: {i.get('who', '')}", "sub": " · ".join(x for x in (amt, i.get("detail")) if x),
                    "meta": i.get("ref"), "utterance": f"Show {i['ref']}" if i.get("ref") else None})
    for al in alerts[:2]:
        pri.append({"title": f"Budget: {al['category']} {al['alert']}", "sub": f"{al['spent']} of {al['budget']} this month", "tone": "warn",
                    "utterance": f"Explain the {al['category']} budget alert"})
    cands = []
    if approvals:
        cands.append({"score": 70, "title": f"Review {len(approvals)} approval{'s' if len(approvals) > 1 else ''}",
                      "why": f"The oldest has waited since {datetime.fromisoformat(min(i['date'] for i in approvals if i.get('date'))):%d %b}." if any(i.get("date") for i in approvals) else "They are waiting on you.",
                      "utterance": "What needs my approval?"})
    if overdue:
        cands.append({"score": 65, "title": f"Chase {len(overdue)} overdue invoice{'s' if len(overdue) > 1 else ''}",
                      "why": "Money owed to the company is past its due date.", "utterance": "Which client invoices are overdue?"})
    if alerts:
        cands.append({"score": 60, "title": f"Look at the {alerts[0]['category']} budget", "why": f"{alerts[0]['category']}: {alerts[0]['alert']}.",
                      "utterance": f"Explain the {alerts[0]['category']} budget alert"})
    return [{"type": "kpi_strip", "items": kpis}, {"type": "list", "title": "Priorities", "items": pri,
                                                     "empty": "Nothing is waiting on you."}], cands


async def _ceo(s, a: Actor, base: dict, notes: list[str]) -> tuple[list[dict], list[dict]]:
    from app.services import budget_months as bm
    from app.services.revenue import reads
    from app.services.revenue.core import Rev
    from app.services.revenue.fiscal import fy_today
    today = base["today"]
    rv = Rev.of(a, today)
    try:
        ov = await s.run_sync(lambda ss: reads.overview(ss, rv, fy_today(today), f"{today:%Y-%m}", None))
        k = ov["kpis"]
    except Exception as e:
        log.warning("briefing revenue unavailable: %s", e)
        k, ov = None, {}
    try:
        al = await bm.alerts(s, a, today)
    except DomainError:
        al = {"alerts": [], "months_due_for_close": []}
    head = (await s.execute(select(func.count()).select_from(User).where(User.workspace_id == a.workspace_id, User.status == "active"))).scalar_one()
    on_leave = (await s.execute(select(func.count()).select_from(LeaveRequest).where(
        LeaveRequest.workspace_id == a.workspace_id, LeaveRequest.state == "approved", LeaveRequest.start_date <= today,
        LeaveRequest.end_date >= today))).scalar_one()
    kpis = []
    if k:
        kpis += [{"label": "Received this month", "value": k["received"], "sub": f"of {k['projected']} billed", "utterance": "How is revenue this month?"},
                 {"label": "Outstanding", "value": k["outstanding"], "utterance": "Who owes us money?"},
                 {"label": "Overdue", "value": k["overdue"], "sub": f"{k['overdue_count']} invoice{'s' if k['overdue_count'] != 1 else ''}",
                  "tone": "warn" if k["overdue_count"] else None, "utterance": "Show overdue receivables by customer"}]
    kpis += [{"label": "Budget alerts", "value": str(len(al["alerts"])), "tone": "warn" if al["alerts"] else None, "utterance": "Any budget alerts?"},
             {"label": "People", "value": str(head), "sub": f"{on_leave} on leave today", "utterance": "Who is on leave today?"}]
    risks = []
    for c in (ov.get("clients") or [])[:5]:
        if c["overdue"] not in ("₹0", "₹0.00"):
            risks.append({"title": f"{c['client']} overdue {c['overdue']}", "sub": f"Outstanding {c['outstanding']}", "tone": "warn",
                          "utterance": f"Show {c['client']}'s invoices"})
    for x in al["alerts"][:3]:
        risks.append({"title": f"{x['category']}: {x['alert']}", "sub": f"{x['spent']} of {x['budget']} this month", "tone": "warn",
                      "utterance": f"Explain the {x['category']} budget alert"})
    if al.get("months_due_for_close"):
        risks.append({"title": f"Month close pending: {', '.join(al['months_due_for_close'])}", "sub": "Finance has not closed these months yet"})
    cands = []
    if k and k["overdue_count"]:
        cands.append({"score": 66, "title": f"Ask finance about {k['overdue']} overdue", "why": f"{k['overdue_count']} client invoice(s) are past due.",
                      "utterance": "Show overdue receivables by customer"})
    if al["alerts"]:
        cands.append({"score": 62, "title": f"Check the {al['alerts'][0]['category']} spend", "why": f"{al['alerts'][0]['category']}: {al['alerts'][0]['alert']}.",
                      "utterance": f"Explain the {al['alerts'][0]['category']} budget alert"})
    return [{"type": "kpi_strip", "items": kpis}, {"type": "list", "title": "Risks to watch", "items": risks[:5],
                                                     "empty": "No open risks right now."}], cands


async def _employee(s, a: Actor, base: dict, notes: list[str]) -> tuple[list[dict], list[dict]]:
    today = base["today"]
    bal = await people.balance(s, a.workspace_id, a.user_id)
    claims = (await s.execute(select(Claim).where(Claim.workspace_id == a.workspace_id,
                                                  or_(Claim.submitter_id == a.user_id, Claim.beneficiary_party_id == a.party_id),
                                                  or_(Claim.state == "submitted", Claim.settlement_state == "unpaid"))
                              .order_by(Claim.id.desc()).limit(5))).scalars().all()
    leaves = (await s.execute(select(LeaveRequest).where(LeaveRequest.workspace_id == a.workspace_id, LeaveRequest.user_id == a.user_id,
                                                         LeaveRequest.end_date >= today).order_by(LeaveRequest.start_date).limit(4))).scalars().all()
    kpis = [{"label": "Open tasks", "value": str(len(base["tasks"])), "utterance": "What are my tasks?"},
            {"label": "Leave available", "value": f"{bal.get('EL', {}).get('available', 0)} EL · {bal.get('CL', {}).get('available', 0)} CL",
             "utterance": "What is my leave balance?"},
            {"label": "Claims in progress", "value": str(len(claims)), "utterance": "What's the status of my claims?"},
            {"label": "Unread inbox", "value": str(base["unread"]), "utterance": "Read my inbox"}]
    reqs = [{"title": f"Claim {c.ref}: {c.merchant}", "sub": f"{format_inr(c.amount_paise)} · {'awaiting approval' if c.state == 'submitted' else 'approved, payment pending'}",
             "meta": c.ref, "utterance": f"What's the status of claim {c.ref}?"} for c in claims]
    reqs += [{"title": f"Leave {lr.ref}: {lr.leave_type} {lr.start_date:%d %b}–{lr.end_date:%d %b}", "sub": lr.state, "meta": lr.ref,
              "tone": "warn" if lr.state == "rejected" else None} for lr in leaves]
    reqs += [{"title": f"Ticket {t.ref}: {t.title}", "sub": t.status.replace("_", " "), "meta": t.ref,
              "utterance": f"What's the status of ticket {t.ref}?"} for t in base["tickets"][:3]]
    cands = []
    if base["unread"]:
        cands.append({"score": 50, "title": f"Read {base['unread']} new message{'s' if base['unread'] > 1 else ''}", "why": "They arrived in your Purser inbox.",
                      "utterance": "Read my inbox"})
    return [{"type": "kpi_strip", "items": kpis},
            {"type": "list", "title": "My tasks", "items": _task_items(base["tasks"], today), "empty": "No open tasks."},
            {"type": "list", "title": "My requests", "items": reqs, "empty": "No open claims, leave or tickets."}], cands


async def _pick(cands: list[dict], role: str) -> dict | None:
    """Rule order decides; the fast model may re-pick among the top candidates and phrase why (3 s budget)."""
    if not cands:
        return None
    cands = sorted(cands, key=lambda c: -c["score"])
    top = cands[0]
    st = get_settings()
    if len(cands) < 2 or not os.environ.get("OPENAI_API_KEY"):
        return top
    try:
        from openai import AsyncOpenAI
        opts = [{"i": i, "title": c["title"], "why": c["why"]} for i, c in enumerate(cands[:4])]
        r = await asyncio.wait_for(AsyncOpenAI(max_retries=0).responses.create(
            model=st.openai_model_fast,
            input=[{"role": "system", "content": "Pick the single most valuable next action for this user right now. Answer JSON "
                    '{"i": <index>, "why": "<one short sentence, only facts from the options>"}.'},
                   {"role": "user", "content": json.dumps({"role": role, "options": opts})}],
            text={"format": {"type": "json_object"}}), 3.0)
        got = json.loads(r.output_text)
        chosen = dict(cands[int(got["i"])])
        if isinstance(got.get("why"), str) and 0 < len(got["why"]) <= 160:
            chosen["why"] = got["why"]
        chosen["picked_by"] = "model"
        return chosen
    except Exception as e:
        log.info("next-best-action model skipped: %s", type(e).__name__)
        return top


async def _routines(a: Actor) -> dict | None:
    """The user's saved routines (and shared ones): tapping one runs it. Empty -> one item that starts creating one."""
    if a.read_only:
        return None
    from app.agent.workflows import custom  # lazy: the agent layer imports services

    items = [{"title": w.title, "sub": (f"Shared by {w.owner_name}" if w.shared and w.owner_id != a.user_id else
                                         f"{len(w.checklist)} steps"), "utterance": f"Run {w.title}"}
             for w in (await custom.for_actor(a))[:4]]
    if not items:
        items = [{"title": "Create your own routine", "sub": "Describe steps you repeat; Purser saves them",
                  "utterance": "Help me set up a custom routine"}]
    return {"type": "list", "title": "Your routines", "items": items}


def forget(user_id: int) -> None:
    _cache.pop(user_id, None)


async def build(a: Actor, *, fresh: bool = False) -> dict:
    hit = _cache.get(a.user_id)
    if hit and not fresh and _time.time() - hit[0] < CACHE_S:
        return hit[1]
    notes: list[str] = []
    events_task = asyncio.create_task(_meetings_today(a, notes))
    mail_task = asyncio.create_task(_important_mail(a, notes))
    async with db.session_scope() as s:
        base = await _common(s, a)
        if a.read_only:
            sections, cands = await _ceo(s, a, base, notes)
        elif a.is_approver:
            sections, cands = await _admin(s, a, base, notes)
        else:
            sections, cands = await _employee(s, a, base, notes)
    events, source = await events_task
    mail = await mail_task
    cands += _meeting_candidates(events) + _task_candidates(base["tasks"], base["today"])
    if mail:
        cands.append({"score": 55, "title": f"Reply to {mail[0]['from']}", "why": f"Unread: “{mail[0]['subject']}”.",
                      "utterance": f"Read the email from {mail[0]['from']} about {mail[0]['subject']}"})
    today_section = {"type": "list", "title": "Today", "source": source, "items": _meeting_items(events),
                     "empty": "No meetings today." if source != "unavailable" else "Calendar unavailable right now."}
    sections.insert(1, today_section)
    if a.is_approver and base["tasks"]:
        sections.append({"type": "list", "title": "My tasks", "items": _task_items(base["tasks"], base["today"]), "empty": "No open tasks."})
    if mail:
        sections.append({"type": "list", "title": "Unread in Gmail", "items": [
            {"title": m["subject"], "sub": m["from"], "meta": "important" if m["important"] else "",
             "utterance": f"Summarise the email from {m['from']} about {m['subject']}"} for m in mail]})
    routines = await _routines(a)
    if routines is not None:
        sections.append(routines)
    nba = await _pick(cands, a.role)
    out = {"greeting": _greeting(a.display_name), "role": a.role, "as_of": datetime.now(_tz()).isoformat(timespec="minutes"),
           "next_action": {k: nba[k] for k in ("title", "why", "utterance") if k in nba} if nba else None,
           "sections": sections, "notes": notes, "google": a.uses_google}
    _cache[a.user_id] = (_time.time(), out)
    return out


def spoken(b: dict) -> dict:
    """A compact version for the agent to speak (no UI fields)."""
    sec = {x.get("title") or x["type"]: [i.get("title") or f"{i.get('label')}: {i.get('value')}" for i in x["items"]][:4] for x in b["sections"]}
    return {"greeting": b["greeting"], "next_action": b["next_action"], "sections": sec, "notes": b["notes"]}
