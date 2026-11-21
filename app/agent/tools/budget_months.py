"""Monthly budget tools: read the month grid, alerts, recommendations, forecasts and history; propose changes,
month close and recommendation plans (propose -> present -> confirm, like every other write)."""

from __future__ import annotations

from typing import Literal

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel, ConfigDict, Field

from app import db
from app.agent.context import PurserContext, safe_tool
from app.agent.tools.proposals import _propose
from app.services import budget
from app.services import budget_months as bm
from app.services.budget_actions import step_id
from app.services.records import today_ist

Ctx = RunContextWrapper[PurserContext]


@function_tool
@safe_tool
async def get_budget_month(ctx: Ctx, category: str | None = None, month: str | None = None) -> dict:
    """This month's (or a given month's) budget per category: budget, spent, remaining, used %, status
    (UNDERUSED below 85%, ON_TRACK 85-107%, OVERRUN above 107%) and, for the current month, pacing.
    month: YYYY-MM or a month name; omit for the current month. Omit category for all categories."""
    a, today = ctx.context.actor, today_ist()
    m = bm.parse_month(month, today)
    async with db.session_scope() as s:
        cells = await bm.grid(s, a, today, category=category, months=[m])
        line = await budget.get_line(s, a.workspace_id, category=category) if category else None
    if line:
        ctx.context.show({"card": "budget", "line_id": line.id, "category": line.category})
    return {"ok": True, "month": bm.label(m), "as_of": today.isoformat(), "categories": [c.view() for c in cells],
            "total": bm._sum_cells(cells),
            "how_to_read": "remaining is exact rupees; status grades utilisation with a 7% tolerance; pacing compares spend with days elapsed"}


@function_tool
@safe_tool
async def get_budget_year(ctx: Ctx, category: str) -> dict:
    """One category month by month for this financial year: base plan, current budget, spent, remaining, status,
    closed or open. Use for 'Software month by month' or 'is Travel on plan this year'."""
    a, today = ctx.context.actor, today_ist()
    async with db.session_scope() as s:
        cells = await bm.grid(s, a, today, category=category)
        line = await budget.get_line(s, a.workspace_id, category=category)
    ctx.context.show({"card": "budget", "line_id": line.id, "category": line.category})
    return {"ok": True, "category": line.category, "fy": bm.fy_of(today), "months": [c.view() for c in cells if c.adjusted or c.actual],
            "year": bm._sum_cells(cells)}


@function_tool
@safe_tool
async def get_budget_alerts(ctx: Ctx) -> dict:
    """Budget warnings now: categories at/over their monthly limit, approaching it, or burning fast early in the month;
    months waiting to be closed; and how many trend recommendations are open."""
    async with db.session_scope() as s:
        out = await bm.alerts(s, ctx.context.actor, today_ist())
    return {"ok": True, **out}


@function_tool
@safe_tool
async def get_budget_recommendations(ctx: Ctx, target_month: str | None = None) -> dict:
    """Trend recommendations from the last 3 CLOSED months (consistent overrun or under-use above 15% on average)
    and the plan that acts on them for one month (move money from under-used to over-running categories first,
    then top up or take back). Advisory only until applied with propose_apply_recommendations."""
    a, today = ctx.context.actor, today_ist()
    if not a.is_approver:
        return {"ok": False, "code": "FORBIDDEN", "message": "Budget recommendations are for finance approvers and admins."}
    target = bm.parse_month(target_month, today) if target_month else bm.default_target(today)
    async with db.session_scope() as s:
        recs = await bm.recommendations(s, a)
        steps = await bm.still_to_do(s, a, target)
    return {"ok": True, "target_month": bm.label(target),
            "recommendations": [{"category": r.category, "direction": r.direction.lower(), "average_variance_pct": r.avg_variance_pct,
                                 "suggested_monthly_change": bm.format_inr(r.suggested_delta_paise), "months": r.months} for r in recs],
            "plan": [{"step_id": step_id(p), "kind": p.kind, "amount": bm.format_inr(p.amount_paise), "from": p.source, "to": p.dest,
                      "reason": p.reason} for p in steps],
            "note": "A trend is advice. Check the bills behind it before moving money." if recs else
                    "No category has 3 closed months in a row over or under budget by more than 15%."}


@function_tool
@safe_tool
async def forecast_budget(ctx: Ctx, category: str | None = None) -> dict:
    """Where spend is heading at today's run rate: this month's projected month-end and the financial year's
    projected year-end versus budget. A forecast is an estimate, not a recommendation or a change."""
    async with db.session_scope() as s:
        out = await bm.outlook(s, ctx.context.actor, today_ist(), category)
    return {"ok": True, **out}


@function_tool
@safe_tool
async def what_if(ctx: Ctx, category: str | None = None, percent: float | None = None, amount_rupees: float | None = None,
                  per_month: bool = False, start_month: str | None = None, end_month: str | None = None) -> dict:
    """Scenario: 'if software costs rise 15% from December, how much is left in March?' -> category='IT & Cloud',
    percent=15, start_month='2026-12'. amount_rupees for a fixed extra cost (once, or every month with per_month=true);
    negative values model savings. Changes nothing."""
    async with db.session_scope() as s:
        out = await bm.what_if(s, ctx.context.actor, today_ist(), category=category, percent=percent,
                               amount_paise=bm_round(amount_rupees), per_month=per_month, start=start_month, end=end_month)
    return {"ok": True, **out}


def bm_round(rupees: float | None) -> int | None:
    from app.money import rupees_to_paise
    return rupees_to_paise(rupees) if rupees else None


@function_tool
@safe_tool
async def get_budget_history(ctx: Ctx, category: str | None = None) -> dict:
    """Who changed the budget, when, why and by how much (transfers, top-ups, reductions, month closes, carry-overs),
    newest first, with before/after amounts per month."""
    async with db.session_scope() as s:
        out = await bm.history(s, ctx.context.actor, category)
    return {"ok": True, "changes": out}


class MonthSplit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    months: list[str] = Field(min_length=1, max_length=12, description="YYYY-MM months the change applies to")
    split: Literal["equal", "custom", "shares"] | None = Field(None, description="How the amount spreads over several months")
    amounts_rupees: list[float] | None = Field(None, description="custom: one amount per month, summing to the total")
    shares_pct: list[float] | None = Field(None, description="shares: one % per month, summing to 100")


@function_tool
@safe_tool
async def propose_budget_change(ctx: Ctx, change: Literal["transfer", "top_up", "reduce"], amount_rupees: float, when: MonthSplit,
                                reason: str, source_category: str | None = None, dest_category: str | None = None) -> dict:
    """Propose moving budget: transfer (source -> dest, total unchanged), top_up (dest, adds new money) or
    reduce (source, takes money back). The preview shows each month's budget and remaining before and after.
    A past month can only give; a closed month cannot change."""
    return await _propose(ctx, "budget_change", {
        "change": change, "amount_rupees": str(amount_rupees), "months": when.months, "split": when.split or "equal",
        "amounts_rupees": [str(x) for x in when.amounts_rupees] if when.amounts_rupees else None,
        "shares_pct": when.shares_pct, "source": source_category, "dest": dest_category, "reason": reason})


class Variance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    reason: Literal["vendor_price_change", "unplanned_one_off", "delayed_project_or_hiring", "scope_expansion", "other"]
    note: str | None = Field(None, max_length=200)


@function_tool
@safe_tool
async def propose_close_month(ctx: Ctx, month: str, variances: list[Variance] | None = None,
                              carry_over: list[str] | None = None) -> dict:
    """Propose closing a finished month: freezes each category's budget, spent and status. Record a variance reason for
    over-running or under-used categories, and list under-used categories whose surplus should carry into next month
    (others are absorbed). Read get_budget_month for that month first."""
    return await _propose(ctx, "close_month", {"month": month, "variances": [v.model_dump() for v in variances or []],
                                                "carry_over": carry_over or []})


@function_tool
@safe_tool
async def propose_apply_recommendations(ctx: Ctx, step_ids: list[str] | None = None, target_month: str | None = None) -> dict:
    """Propose applying the recommendation plan (all steps, or the chosen step_ids from get_budget_recommendations)."""
    return await _propose(ctx, "apply_recommendations", {"step_ids": step_ids, "target_month": target_month})


TOOLS = [get_budget_month, get_budget_year, get_budget_alerts, get_budget_recommendations, forecast_budget, what_if,
         get_budget_history, propose_budget_change, propose_close_month, propose_apply_recommendations]
