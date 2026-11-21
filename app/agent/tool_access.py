"""Which tools each role is offered. The model never sees a tool its role cannot use, so it cannot offer the action,
and the prompt stays smaller (faster turns). Services still enforce every rule; this is defence in depth."""

from __future__ import annotations

from collections.abc import Iterable

from agents import Agent, FunctionTool, RunContextWrapper

from app.agent.context import PurserContext

# Company finance (budget, revenue, payables/receivables, contracts, audit): finance approvers, admin, CEO.
FINANCE_READ = {
    "get_budget_status", "explain_budget_change", "get_audit_history", "get_budget_month", "get_budget_year",
    "get_budget_alerts", "get_budget_recommendations", "forecast_budget", "what_if", "get_budget_history",
    "get_revenue_overview", "list_client_invoices", "get_invoice", "get_client", "get_revenue_suggestions", "get_fx_rates",
    "review_contract", "search_contracts", "get_contract", "list_liabilities", "contract_deadlines", "show_contract_clause",
}
# Finance writes: offered only to roles that can approve money (admin, finance approver).
FINANCE_WRITE = {
    "propose_budget_change", "propose_close_month", "propose_apply_recommendations", "propose_submit_bill",
    "propose_approval", "propose_settlement", "propose_invoices", "propose_invoice_status", "propose_payment",
    "propose_invoice_change", "propose_balance_move", "propose_client_change", "propose_billing_cycle",
    "propose_fx_month_rate", "propose_end_project", "add_reminder", "complete_reminder", "mark_not_yet",
    "propose_create_contract", "propose_review_contract_finding", "propose_contract_details", "propose_contract_status",
    "propose_rescan_contract",
}
# Any write at all (hidden from the read-only CEO login). propose_* is matched by prefix as well.
OTHER_WRITES = {"confirm_pending_proposal", "cancel_pending_proposal", "get_pending_proposal", "correct_extracted_field",
                "close_intake", "add_task", "complete_task", "save_mail_draft"}
# Real Gmail / Google Calendar: only the linked login (GOOGLE_LINKED_EMAIL).
GOOGLE_ONLY: set[str] = {"search_mail", "read_mail_thread", "save_mail_draft", "propose_email", "propose_mail_action",
                         "propose_reschedule_meeting", "propose_cancel_meeting"}


def _allowed(name: str, ctx: RunContextWrapper[PurserContext]) -> bool:
    a = ctx.context.actor
    if name in GOOGLE_ONLY and not a.uses_google:
        return False
    if name in FINANCE_READ and not a.can_read_finance:
        return False
    if name in FINANCE_WRITE and not a.is_approver:
        return False
    if a.read_only and (name.startswith("propose_") or name in OTHER_WRITES or name in FINANCE_WRITE):
        return False
    return True


def apply(tools: Iterable[FunctionTool]) -> list[FunctionTool]:
    out = []
    for t in tools:
        name = t.name

        def enabled(ctx: RunContextWrapper[PurserContext], agent: Agent, _n: str = name) -> bool:
            return _allowed(_n, ctx)

        t.is_enabled = enabled
        out.append(t)
    return out


ROLE_NOTES = {
    "ceo": ("This is the CEO's login and it is READ-ONLY: you can show, chart and explain anything (finance, revenue, budget, "
            "people), but you cannot prepare or make any change. If asked to change something, say the CEO view is read-only "
            "and name who can do it (finance or HR). Lead with company-level numbers and risks, briefly."),
    "employee": ("This is an employee login. They can manage their own claims, leave, tasks, tickets, meetings, travel and "
                 "messages. Company budget, revenue, payables, receivables and contracts are NOT visible to them; if asked, "
                 "say politely that those figures are limited to finance and leadership, and offer what you can do instead."),
    "hr_admin": "This is an HR admin login: people, leave, onboarding and announcements; no company finance figures.",
    "finance_approver": "This is a finance approver login: full finance access including approvals.",
    "admin": "This is the admin login: full access to finance, HR and admin.",
}
