"""Formal onboarding welcome: new wording, standard signature on the email copy only, signature lines in the plan preview
only when the personal email is deliverable. No SMTP is ever touched (autouse `mail` fixture)."""

from sqlalchemy import select

from app import db
from app.models import Message
from app.services import signature
from app.services.actions import OnboardEmployee
from tests.conftest import make_actor
from tests.test_ledger_gates import propose_and_confirm
from tests.test_people_extra import ONBOARD, mail, messages_for  # noqa: F401  (autouse safety fixture)

ARGS = {**ONBOARD, "personal_email": "neha@home.test"}


async def _sig(actor) -> str:
    async with db.session_scope() as s:
        return await signature.for_actor(s, actor)


async def test_welcome_email_row_is_formal_and_signed(seeded, mail):  # noqa: F811
    priya = await make_actor(seeded)
    mail.enable("neha@home.test")
    _, out = await propose_and_confirm(priya, "onboard_employee", {**ARGS, "manager_user_id": seeded["priya_id"]})
    sig = await _sig(priya)
    email = [m for m in await messages_for(out.receipt.id) if m.channel == "email"][0]
    assert email.body.endswith(sig) and sig.startswith("Warm regards,") and "Priya Sharma" in sig
    assert email.body.startswith("Dear Neha,\n\nWelcome to the team! You join as Sales Executive in Sales on ")
    assert ", reporting to Priya Sharma." in email.body
    assert "PAN, Aadhaar and bank details" in email.body and "original Aadhaar and PAN" in email.body
    assert "We look forward to working with you.\n\nWarm regards," in email.body
    assert email.body.count("Warm regards,") == 1


async def test_welcome_inbox_row_is_unsigned(seeded, mail):  # noqa: F811
    priya = await make_actor(seeded)
    mail.enable("neha@home.test")
    _, out = await propose_and_confirm(priya, "onboard_employee", ARGS)
    inbox = [m for m in await messages_for(out.receipt.id) if m.channel == "inbox"][0]
    assert "Warm regards," not in inbox.body and inbox.body.endswith("We look forward to working with you.")
    assert inbox.body.startswith("Dear Neha,")


async def test_welcome_without_manager_omits_reporting_clause(seeded, mail):  # noqa: F811
    priya = await make_actor(seeded)
    _, out = await propose_and_confirm(priya, "onboard_employee", ONBOARD)
    inbox = [m for m in await messages_for(out.receipt.id) if m.channel == "inbox"][0]
    assert "reporting to" not in inbox.body and "in Sales on 01 Dec 2026.\n\n" in inbox.body


async def test_plan_preview_includes_signature_only_when_deliverable(seeded, mail):  # noqa: F811
    priya = await make_actor(seeded)
    sig_lines = (await _sig(priya)).splitlines()

    async def plan(args):
        async with db.session_scope() as s:
            return (await OnboardEmployee().plan(s, priya, args)).lines

    mail.enable("neha@home.test")
    lines = await plan(ARGS)
    i = lines.index("Welcome email signature:")
    assert lines[i + 1:] == sig_lines

    for label, args, allow in [("not allow-listed", ARGS, ("other@x.com",)), ("no personal email", ONBOARD, ("neha@home.test",))]:
        mail.enable(*allow)
        lines = await plan(args)
        assert "Welcome email signature:" not in lines and "Warm regards," not in lines, label

    # email not configured at all
    mail.enable("neha@home.test")
    from app.services import messaging
    st = messaging.get_settings().model_copy(update={"gmail_address": "", "gmail_app_password": ""})
    mail._mp.setattr(messaging, "get_settings", lambda: st)
    assert "Welcome email signature:" not in await plan(ARGS)
