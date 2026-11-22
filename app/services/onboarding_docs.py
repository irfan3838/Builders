"""Pre-onboarding: email a selected candidate a formal request for the details and documents HR needs before day one.

The email is a fixed template filled by code (no model-written prose), signed with the standard signature, previewed
in full, and sent only after HR confirms. The login itself is created later by onboard_employee."""

from __future__ import annotations

import re
from datetime import date, timedelta

from app.config import get_settings
from app.errors import FORBIDDEN, VALIDATION, DomainError
from app.models import Workspace
from app.services import audit, messaging, people, records, signature
from app.services.actions import Execution, Plan

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EXTRA, MAX_EXTRA_CHARS = 6, 120

PERSONAL = ["Full name (exactly as on your Aadhaar and PAN cards)", "Date of birth",
            "Mobile number (with WhatsApp, if different)", "Personal email address",
            "Current and permanent residential address",
            "Emergency contact (name, relationship and phone number)"]
IDENTITY = ["Aadhaar card (front and back)", "PAN card", "One recent passport-size photograph"]
BANK = ["Bank account number, IFSC code and bank/branch name (for salary credit)",
        "Cancelled cheque or the first page of your bank passbook"]
PRIOR = ["Highest educational qualification certificate and mark sheet",
         "Relieving letter and last three payslips from your previous employer (if applicable)",
         "UAN (Universal Account Number) for PF transfer (if applicable)"]


def _long(d: date) -> str:
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"


def _reply_by(start: date, today: date) -> date | None:
    """Three working days before joining; None when that has already passed (then: 'at the earliest')."""
    d, left = start, 3
    while left:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return d if d > today else None


async def _inputs(s, actor, args) -> dict:
    if not actor.is_hr:
        raise DomainError(FORBIDDEN, "Only HR/admin can request onboarding documents.")
    name = " ".join((args.get("name") or "").split())
    if len(name) < 2 or len(name) > 120:
        raise DomainError(VALIDATION, "The candidate's full name is required (max 120 characters).")
    designation = " ".join((args.get("designation") or "").split())
    if not designation or len(designation) > 80:
        raise DomainError(VALIDATION, "The position (designation) is required (max 80 characters).")
    department = " ".join((args.get("department") or "").split()) or None
    email = (args.get("personal_email") or "").strip().lower()
    if not email:
        raise DomainError(VALIDATION, "What is the candidate's personal email address? The request goes there.")
    if not _EMAIL_RE.match(email):
        raise DomainError(VALIDATION, f"'{email}' is not a valid email address.")
    try:
        start = date.fromisoformat(str(args["start_date"]))
    except (KeyError, ValueError) as e:
        raise DomainError(VALIDATION, "Joining date YYYY-MM-DD is required.") from e
    today = records.today_ist()
    if start < today:
        raise DomainError(VALIDATION, f"The joining date {start:%d %b %Y} has already passed.")
    extra = []
    for item in args.get("extra_items") or []:
        item = " ".join(str(item or "").split())
        if item and item not in extra:
            if len(item) > MAX_EXTRA_CHARS:
                raise DomainError(VALIDATION, f"Keep each extra item under {MAX_EXTRA_CHARS} characters.")
            extra.append(item)
    if len(extra) > MAX_EXTRA:
        raise DomainError(VALIDATION, f"At most {MAX_EXTRA} extra items.")
    manager = await people.user(s, actor, int(args["manager_user_id"])) if args.get("manager_user_id") else None
    st = get_settings()
    ws = await s.get(Workspace, actor.workspace_id)
    company = (st.signature_company or (ws.name if ws else "") or "Purser").strip()
    return {"name": name, "designation": designation, "department": department, "email": email, "start": start,
            "today": today, "extra": extra, "manager": manager, "company": company}


def compose_email(i: dict, sig: str) -> tuple[str, str]:
    """(subject, signed body). Pure function of the inputs: same request, same email."""
    first = i["name"].split()[0]
    team = f" in the {i['department']} team" if i["department"] else ""
    subject = f"Documents required for your onboarding - {i['designation']}, {i['company']}"
    n = 0

    def section(title: str, items: list[str]) -> list[str]:
        nonlocal n
        out = ["", title]
        for it in items:
            n += 1
            out.append(f"  {n}. {it}")
        return out

    by = _reply_by(i["start"], i["today"])
    lines = [f"Dear {first},", "",
             f"Congratulations on your selection for the position of {i['designation']}{team} at {i['company']}. "
             f"We are delighted to have you join us and look forward to welcoming you on {_long(i['start'])}"
             + (f", when you will be reporting to {i['manager'].display_name}" if i["manager"] else "") + ".", "",
             "To complete your onboarding formalities before your joining date, please reply to this email with the "
             "following details and clear scanned copies (PDF or JPG) of the documents listed below."]
    lines += section("Personal details", PERSONAL)
    lines += section("Identity documents", IDENTITY)
    lines += section("Bank details", BANK)
    lines += section("Education and previous employment", PRIOR)
    if i["extra"]:
        lines += section("Additional requirements", i["extra"])
    lines += ["",
              (f"Kindly share these by {_long(by)}" if by else "Kindly share these at the earliest") +
              " so that your employee account, payroll and system access are ready on your first day.", "",
              "Please also carry your original Aadhaar card and PAN card on your joining day for verification; they "
              "will be returned to you immediately.", "",
              f"Your information will be kept confidential and used only for employment records and statutory "
              f"compliance at {i['company']}. If you have any questions, simply reply to this email.", "",
              f"We look forward to working with you, {first}."]
    return subject, signature.sign("\n".join(lines), sig)


class RequestOnboardingDocuments:
    kind = "request_onboarding_documents"

    async def plan(self, s, actor, args):
        i = await _inputs(s, actor, args)
        subject, body = compose_email(i, await signature.for_actor(s, actor))
        _, verdict = messaging.address_plan(i["email"])
        status = {"deliverable": "will be sent", "email_not_configured": "cannot be sent (email is not configured)",
                  "not_on_allowlist": "cannot be sent (address is not on the email allow-list)"}.get(verdict, verdict)
        lines = [f"To: {i['email']} ({status})", f"Subject: {subject}", "", *body.splitlines()]
        return Plan("Request onboarding documents", lines,
                    f"Send the onboarding document request to {i['name']} at {i['email']}?", [])

    async def execute(self, s, actor, args, receipt_id):
        i = await _inputs(s, actor, args)
        subject, body = compose_email(i, await signature.for_actor(s, actor))
        sent = await messaging.compose(s, actor, [], kind="onboarding_documents", subject=subject, body=body,
                                       channels=["email"], receipt_id=receipt_id, external_emails=[i["email"]])
        await audit.record(s, actor, "onboarding.documents_requested", record_type="message",
                           after={"candidate": i["name"], "designation": i["designation"], "department": i["department"],
                                  "start_date": i["start"].isoformat(), "email": i["email"],
                                  "email_queued": sent["email_queued"]}, receipt_id=receipt_id)
        if sent["email_queued"]:
            summary = (f"Document request emailed to {i['name']} ({i['email']}). When the documents are in, say "
                       f"'create {i['name'].split()[0]}'s login' to finish onboarding.")
        else:
            summary = (f"Document request for {i['name']} recorded, but the email was NOT sent "
                       f"({messaging.address_plan(i['email'])[1].replace('_', ' ')}).")
        return Execution(summary, [{"type": "messages", **sent},
                                   {"type": "onboarding_documents_requested", "email": i["email"]}])


ONBOARDING_DOC_ACTIONS = [RequestOnboardingDocuments()]
