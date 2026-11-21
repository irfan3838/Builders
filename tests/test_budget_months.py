"""Monthly budget: pure maths (owner's handbook cases), seed facts, month close, changes, actions, what-if, charts, API, tool wiring.
All amounts are integer paise. Dates are pinned to 2026-11-21."""

import json
import re
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app import db
from app.errors import FORBIDDEN, INVALID_STATE, VALIDATION, DomainError
from app.models import AuditEvent, BudgetMovement, BudgetPeriod
from app.services import budget, charts
from app.services import budget_months as bm
from app.services.budgeting import distribution, forecast, pacing
from app.services.budgeting import recommend as rec
from app.services.budgeting.status import compute_status
from seed.seed_v1 import seed
from tests.conftest import make_actor
from tests.test_api_intake import client_for
from tests.test_intake_extra import call
from tests.test_ledger_gates import propose_and_confirm, submit_arjun_hotel_claim

TODAY = date(2026, 11, 21)
R = 100
IT, EV, TR, OS = "IT & Cloud", "Events", "Travel", "Office Supplies"


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr("app.services.records.today_ist", lambda: TODAY)
    for mod in ("app.services.budget_actions", "app.agent.tools.budget_months", "app.services.charts"):
        monkeypatch.setattr(f"{mod}.today_ist", lambda: TODAY, raising=False)


# ---------------------------------------------------------------- helpers

def paise(s: str) -> int:
    return int((Decimal(re.sub(r"[^\d.]", "", s)) * 100).quantize(Decimal("1")))


async def cells(actor, today=TODAY, **kw):
    async with db.session_scope() as s:
        return await bm.grid(s, actor, today, **kw)


def pick(cs, cat, month: date):
    return next(c for c in cs if c.category == cat and c.month == month)


async def allocated(ids, cat=None) -> int:
    async with db.session_scope() as s:
        q = select(func.coalesce(func.sum(BudgetMovement.amount_paise), 0)).where(
            BudgetMovement.workspace_id == ids["workspace_id"], BudgetMovement.bucket == "allocation")
        if cat:
            from app.models import BudgetLine
            q = q.join(BudgetLine, BudgetLine.id == BudgetMovement.line_id).where(BudgetLine.category == cat)
        return int((await s.execute(q)).scalar_one())


async def allocated_in(ids, cat, month: date) -> int:
    async with db.session_scope() as s:
        from app.models import BudgetLine
        q = (select(func.coalesce(func.sum(BudgetMovement.amount_paise), 0)).join(BudgetLine, BudgetLine.id == BudgetMovement.line_id)
             .where(BudgetMovement.workspace_id == ids["workspace_id"], BudgetMovement.bucket == "allocation",
                    BudgetLine.category == cat, BudgetMovement.fiscal_month == month))
        return int((await s.execute(q)).scalar_one())


async def change(actor, **args):
    p, out = await propose_and_confirm(actor, "budget_change", args)
    assert out.status == "executed", out
    return p, out


async def close(actor, month="2026-10", **args):
    return await propose_and_confirm(actor, "close_month", {"month": month, "variances": [], "carry_over": [], **args})


async def close_oct(actor):
    p, out = await close(actor, variances=[{"category": IT, "reason": "vendor_price_change"}], carry_over=[EV])
    assert out.status == "executed", out
    return out


async def code_of(coro) -> str:
    with pytest.raises(DomainError) as e:
        await coro
    return e.value.code


async def plan(actor, **kw):
    async with db.session_scope() as s:
        return await bm.plan_change(s, actor, kw.pop("today", TODAY), **kw)


# ---------------------------------------------------------------- A. pure maths

def test_compute_status_boundaries():
    b = 100_000 * R
    assert compute_status(b, 8_499_999) == "UNDERUSED"
    assert compute_status(b, 8_500_000) == "ON_TRACK"
    assert compute_status(b, 10_700_000) == "ON_TRACK"
    assert compute_status(b, 10_700_001) == "OVERRUN"
    assert compute_status(0, 500) == "OPEN"
    assert compute_status(-5, 0) == "OPEN"


def test_pacing_critical_burn_window():
    p = pacing.compute(82_000 * R, 100_000 * R, 10, 30)
    assert p.velocity == 2.46 and p.alert == "CRITICAL_BURN" and p.health == "HIGH_RISK"
    assert pacing.compute(82_000 * R, 100_000 * R, 14, 30).alert == "CRITICAL_BURN"
    assert pacing.compute(82_000 * R, 100_000 * R, 15, 30).alert is None


def test_pacing_approaching_and_limit():
    assert pacing.compute(90_000 * R, 100_000 * R, 20, 30).alert == "APPROACHING_LIMIT"
    assert pacing.compute(100_000 * R, 100_000 * R, 20, 30).alert == "LIMIT_REACHED"
    assert pacing.compute(120_000 * R, 100_000 * R, 20, 30).alert == "LIMIT_REACHED"
    z = pacing.compute(5_000, 0, 10, 30)
    assert z.velocity is None and z.health == "HEALTHY"


def cm(adjusted, *actuals_rupees):
    return [rec.ClosedMonth(f"M{i}", adjusted * R, a * R, compute_status(adjusted * R, a * R)) for i, a in enumerate(actuals_rupees)]


def test_trend_increase_decrease_and_none_cases():
    sw = rec.trend(1, "Software", cm(100_000, 120_000, 118_000, 122_000))
    assert (sw.direction, sw.avg_variance_pct, sw.suggested_delta_paise) == ("INCREASE", 20.0, 20_000 * R)
    tr = rec.trend(2, "Travel", cm(50_000, 40_000, 41_000, 39_000))
    assert (tr.direction, tr.avg_variance_pct, tr.suggested_delta_paise) == ("DECREASE", 20.0, 10_000 * R)
    assert rec.trend(3, "Utilities", cm(100_000, 115_000, 115_000, 115_000)) is None  # exactly 15%
    assert rec.trend(4, "Supplies", cm(100_000, 120_000, 100_000, 120_000)) is None  # middle month on track
    assert rec.trend(5, "Few", cm(100_000, 130_000, 130_000)) is None
    assert rec.trend(6, "Zero", [rec.ClosedMonth("a", 0, 5, "OPEN")] * 3) is None


def test_plan_transfers_then_tops_up():
    sw = rec.trend(1, "Software", cm(100_000, 120_000, 118_000, 122_000))
    tr = rec.trend(2, "Travel", cm(50_000, 40_000, 41_000, 39_000))
    steps = [(p.kind, p.amount_paise, p.source, p.dest) for p in rec.plan([sw, tr])]
    assert steps == [("transfer", 10_000 * R, "Travel", "Software"), ("top_up", 10_000 * R, None, "Software")]


def test_forecast_and_even_split():
    assert forecast.month_outlook(100_000 * R, 30_000 * R, 10, 30).predicted == 90_000 * R
    parts = distribution.even_split(1_000_003, 12)
    assert sum(parts) == 1_000_003 and parts == sorted(parts, reverse=True) and max(parts) - min(parts) == 1
    assert distribution.even_split(100, 12)[:5] == [9, 9, 9, 9, 8]


# ---------------------------------------------------------------- B. seed facts

async def test_seed_travel_position_and_golden_path(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        assert (await budget.position(s, seeded["workspace_id"], seeded["travel_line_id"]))["available_paise"] == 4_500_000
    ref = await submit_arjun_hotel_claim(seeded, priya)
    await propose_and_confirm(priya, "approve", {"ref": ref})
    async with db.session_scope() as s:
        assert (await budget.position(s, seeded["workspace_id"], seeded["travel_line_id"]))["available_paise"] == 4_520_000


async def test_monthly_sums_equal_annual_for_every_line(seeded):
    priya = await make_actor(seeded)
    cs = await cells(priya)
    cats = {c.category for c in cs}
    assert len(cats) == 6
    async with db.session_scope() as s:
        lines = await bm.lines(s, seeded["workspace_id"])
        for ln in lines:
            pos = await budget.position(s, seeded["workspace_id"], ln.id)
            assert sum(c.adjusted for c in cs if c.line_id == ln.id) == pos["allocated_paise"], ln.category


async def test_seed_periods_jul_sep_closed_snapshot_oct_open(seeded):
    priya = await make_actor(seeded)
    cs = await cells(priya)
    for m in (7, 8, 9):
        for c in (x for x in cs if x.month == date(2026, m, 1) and (x.adjusted or x.actual)):
            assert c.closed and c.source == "imported_snapshot", (c.category, m)
    assert not any(c.closed for c in cs if c.month == date(2026, 10, 1))
    async with db.session_scope() as s:
        srcs = set((await s.execute(select(BudgetPeriod.source).where(BudgetPeriod.closed_at.isnot(None)))).scalars())
    assert srcs == {"imported_snapshot"}


async def test_seed_alerts_and_no_recommendations_before_oct_close(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        out = await bm.alerts(s, priya, TODAY)
        assert await bm.recommendations(s, priya) == []
    os_alert = next(a for a in out["alerts"] if a["category"] == OS)
    assert os_alert["alert"].startswith("limit reached") and os_alert["month"] == "Nov 2026"
    assert paise(os_alert["spent"]) == 18_500 * R and paise(os_alert["budget"]) == 11_000 * R
    assert out["months_due_for_close"] == ["Oct 2026"]
    assert out["recommendations_open"] == 0


# ---------------------------------------------------------------- C. close month

async def test_close_oct_freezes_and_carries(seeded):
    priya = await make_actor(seeded)
    ev_nov_before = pick(await cells(priya), EV, date(2026, 11, 1)).adjusted
    annual_before = await allocated(seeded, EV)
    await close_oct(priya)
    cs = await cells(priya)
    it, ev = pick(cs, IT, date(2026, 10, 1)), pick(cs, EV, date(2026, 10, 1))
    assert it.closed and it.status == "OVERRUN" and it.actual == 3_980_000 and it.variance_reason == "vendor_price_change"
    assert ev.closed and ev.status == "UNDERUSED"
    assert pick(cs, EV, date(2026, 11, 1)).adjusted == ev_nov_before + 250_000
    assert await allocated_in(seeded, EV, date(2026, 10, 1)) == 0
    assert await allocated(seeded, EV) == annual_before


async def test_recommendations_and_still_to_do_after_close(seeded):
    priya = await make_actor(seeded)
    await close_oct(priya)
    async with db.session_scope() as s:
        recs = {r.category: r for r in await bm.recommendations(s, priya)}
        steps = await bm.still_to_do(s, priya, date(2026, 12, 1))
    assert set(recs) == {EV, IT}
    assert (recs[EV].direction, recs[EV].avg_variance_pct) == ("DECREASE", 66.7)
    assert (recs[IT].direction, recs[IT].avg_variance_pct) == ("INCREASE", 68.4)
    assert [(p.kind, p.amount_paise, p.source, p.dest) for p in steps] == [
        ("transfer", 166_600, EV, IT), ("top_up", 860_000, None, IT)]


async def test_close_rejections(seeded):
    priya = await make_actor(seeded)

    async def pc(month, carry=(), today=TODAY):
        async with db.session_scope() as s:
            return await bm.plan_close(s, priya, today, month, variances={}, carry_over=list(carry))

    assert await code_of(pc("2026-11")) == VALIDATION  # current month
    assert await code_of(pc("2026-12")) == VALIDATION  # future
    assert await code_of(pc("2026-10", [IT])) == VALIDATION  # overrun cannot carry
    assert await code_of(pc("2027-03", [EV], today=date(2027, 4, 15))) == VALIDATION  # March has no next month
    await close_oct(priya)
    assert await code_of(pc("2026-10")) == INVALID_STATE
    from app.services import proposals

    async def via_action():
        async with db.session_scope() as s:
            await proposals.create(s, priya, "close_month", {"month": "2026-10", "variances": [], "carry_over": []})
    assert await code_of(via_action()) == INVALID_STATE


# ---------------------------------------------------------------- D. changes

async def test_transfer_conserves_total_and_moves_each_line(seeded):
    priya = await make_actor(seeded)
    total, it0, ev0 = await allocated(seeded), await allocated(seeded, IT), await allocated(seeded, EV)
    await change(priya, change="transfer", amount_rupees="1000", months=["2026-12"], source=IT, dest=EV, reason="cover events")
    assert await allocated(seeded) == total
    assert await allocated(seeded, IT) == it0 - 100_000 and await allocated(seeded, EV) == ev0 + 100_000


async def test_top_up_and_reduce_change_annual_by_amount(seeded):
    priya = await make_actor(seeded)
    total, ev0 = await allocated(seeded), await allocated(seeded, EV)
    await change(priya, change="top_up", amount_rupees="3000", months=["2026-12"], dest=EV, reason="more events")
    assert await allocated(seeded, EV) == ev0 + 300_000 and await allocated(seeded) == total + 300_000
    await change(priya, change="reduce", amount_rupees="1000", months=["2026-12"], source=EV, reason="trim")
    assert await allocated(seeded, EV) == ev0 + 200_000 and await allocated(seeded) == total + 200_000


async def test_closed_month_cannot_change(seeded):
    priya = await make_actor(seeded)
    assert await code_of(plan(priya, kind="reduce", amount_paise=10_000, months=["2026-07"], source=IT, reason="x")) == INVALID_STATE


async def test_past_open_month_cannot_receive_but_can_give(seeded):
    priya = await make_actor(seeded)
    assert await code_of(plan(priya, kind="top_up", amount_paise=10_000, months=["2026-10"], dest=EV, reason="x")) == VALIDATION
    p = await plan(priya, kind="reduce", amount_paise=100_000, months=["2026-10"], source=EV, reason="give back")
    assert p.legs[0].delta == -100_000


async def test_source_cannot_give_more_than_remaining(seeded):
    priya = await make_actor(seeded)
    # Events Dec allocation is 3,875: asking for 5,000 must fail, exactly 3,875 must pass
    assert await code_of(plan(priya, kind="reduce", amount_paise=500_000, months=["2026-12"], source=EV, reason="x")) == VALIDATION
    p = await plan(priya, kind="reduce", amount_paise=387_500, months=["2026-12"], source=EV, reason="all of it")
    assert p.legs[0].delta == -387_500


async def test_same_source_and_dest_and_missing_reason_rejected(seeded):
    priya = await make_actor(seeded)
    assert await code_of(plan(priya, kind="transfer", amount_paise=10_000, months=["2026-12"], source=EV, dest=EV, reason="x")) == VALIDATION
    for reason in ("", "   "):
        assert await code_of(plan(priya, kind="top_up", amount_paise=10_000, months=["2026-12"], dest=EV, reason=reason)) == VALIDATION


async def test_splits_sum_exactly(seeded):
    priya = await make_actor(seeded)
    months = ["2026-12", "2027-01", "2027-02"]
    eq = await plan(priya, kind="top_up", amount_paise=1_000_001, months=months, dest=IT, reason="x", split="equal")
    assert [leg.delta for leg in eq.legs] == [333_334, 333_334, 333_333]
    cu = await plan(priya, kind="top_up", amount_paise=1_000_001, months=months, dest=IT, reason="x", split="custom",
                    amounts_paise=[1, 500_000, 500_000])
    assert [leg.delta for leg in cu.legs] == [1, 500_000, 500_000]
    sh = await plan(priya, kind="top_up", amount_paise=1_000_001, months=months, dest=IT, reason="x", split="shares",
                    shares_bp=[3333, 3333, 3334])
    assert sum(leg.delta for leg in sh.legs) == 1_000_001
    assert await code_of(plan(priya, kind="top_up", amount_paise=100, months=months, dest=IT, reason="x", split="custom",
                              amounts_paise=[1, 1, 1])) == VALIDATION
    assert await code_of(plan(priya, kind="top_up", amount_paise=100, months=months, dest=IT, reason="x", split="shares",
                              shares_bp=[5000, 4000, 500])) == VALIDATION


async def test_transfer_split_legs_balance(seeded):
    priya = await make_actor(seeded)
    p = await plan(priya, kind="transfer", amount_paise=1_000_001, months=["2026-12", "2027-01", "2027-02"], source=IT, dest=EV, reason="x")
    assert sum(leg.delta for leg in p.legs) == 0 and p.annual_delta == 0


async def test_months_across_two_fys_rejected(seeded):
    priya = await make_actor(seeded)
    assert await code_of(plan(priya, kind="top_up", amount_paise=100, months=["2027-03", "2027-04"], dest=EV, reason="x")) == VALIDATION


async def test_employee_is_forbidden(seeded):
    arjun = await make_actor(seeded, "arjun")
    assert await code_of(plan(arjun, kind="top_up", amount_paise=100, months=["2026-12"], dest=EV, reason="x")) == FORBIDDEN

    async def pc():
        async with db.session_scope() as s:
            return await bm.plan_close(s, arjun, TODAY, "2026-10", variances={}, carry_over=[])
    assert await code_of(pc()) == FORBIDDEN
    async with db.session_scope() as s:
        assert "recommendations_open" not in await bm.alerts(s, arjun, TODAY)
    res, _ = await call(__import__("app.agent.tools.budget_months", fromlist=["x"]).get_budget_recommendations, arjun)
    assert res["ok"] is False and res["code"] == FORBIDDEN
    # and the actions refuse him too, once there is something to apply
    priya = await make_actor(seeded)
    await close_oct(priya)
    from app.services import proposals
    for kind, args in (("apply_recommendations", {}), ("close_month", {"month": "2026-09"}),
                       ("budget_change", {"change": "top_up", "amount_rupees": "10", "months": ["2026-12"], "dest": EV, "reason": "x"})):
        with pytest.raises(DomainError) as e:
            async with db.session_scope() as s:
                await proposals.create(s, arjun, kind, args)
        assert e.value.code == FORBIDDEN, kind


# ---------------------------------------------------------------- E. actions end to end

async def test_budget_change_receipt_and_replay(seeded):
    priya = await make_actor(seeded)
    p, out = await change(priya, change="top_up", amount_rupees="2000", months=["2026-12"], dest=EV, reason="more events")
    assert out.receipt is not None and out.receipt.effects[0]["type"] == "budget_change"
    ev0 = await allocated(seeded, EV)
    from app.services import proposals
    async with db.session_scope() as s:
        again = await proposals.confirm(s, priya, p.id, via="button")
    assert again.status == "replayed" and again.receipt.id == out.receipt.id
    assert await allocated(seeded, EV) == ev0


async def test_apply_recommendations_then_nothing_left(seeded):
    priya = await make_actor(seeded)
    await close_oct(priya)
    total = await allocated(seeded)
    p, out = await propose_and_confirm(priya, "apply_recommendations", {"target_month": "2026-12"})
    assert out.status == "executed" and len(out.receipt.effects) == 2
    # transfer nets to zero, top-up adds exactly 8,600
    assert await allocated(seeded) == total + 860_000
    async with db.session_scope() as s:
        assert await bm.still_to_do(s, priya, date(2026, 12, 1)) == []
    from app.services import proposals
    with pytest.raises(DomainError) as e:
        async with db.session_scope() as s:
            await proposals.create(s, priya, "apply_recommendations", {"target_month": "2026-12"})
    assert e.value.code == VALIDATION and "nothing left" in e.value.message
    # replaying the confirmed proposal does not double post
    async with db.session_scope() as s:
        again = await proposals.confirm(s, priya, p.id, via="button")
    assert again.status == "replayed" and again.receipt.id == out.receipt.id
    assert await allocated(seeded) == total + 860_000


async def test_history_newest_first_with_cells(seeded):
    priya = await make_actor(seeded)
    await change(priya, change="top_up", amount_rupees="1000", months=["2026-12"], dest=EV, reason="first")
    await change(priya, change="reduce", amount_rupees="500", months=["2026-12"], source=EV, reason="second")
    async with db.session_scope() as s:
        h = await bm.history(s, priya)
        hev = await bm.history(s, priya, category=EV)
    assert [x["reason"] for x in h[:2]] == ["second", "first"]
    c = h[1]["cells"][0]
    assert paise(c["budget_after"]) == paise(c["budget_before"]) + 100_000 and c["month"] == "Dec 2026"
    assert len(hev) >= 2 and all("reason" in x or "categories_closed" in x for x in hev)
    async with db.session_scope() as s:
        n = (await s.execute(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.like("budget.%")))).scalar_one()
    assert n >= 2


# ---------------------------------------------------------------- F. what-if

async def count_movements() -> int:
    async with db.session_scope() as s:
        return (await s.execute(select(func.count()).select_from(BudgetMovement))).scalar_one()


async def test_what_if_projects_without_writing(seeded):
    priya = await make_actor(seeded)
    n = await count_movements()
    async with db.session_scope() as s:
        out = await bm.what_if(s, priya, TODAY, category=IT, percent=15, amount_paise=None, per_month=False, start="2026-12", end="2027-03")
    assert paise(out["projected_with_change"]) > paise(out["projected_without_change"])
    assert out["change"]["moved_to_now"] is False and out["change"]["from"] == "Dec 2026"
    assert await count_movements() == n
    async with db.session_scope() as s:
        past = await bm.what_if(s, priya, TODAY, category=IT, percent=15, amount_paise=None, per_month=False, start="2026-07", end="2027-03")
    assert past["change"]["moved_to_now"] is True and past["change"]["from"] == "Nov 2026"
    assert await count_movements() == n


# ---------------------------------------------------------------- G. charts

async def test_budget_month_chart_for_it_and_cloud(seeded):
    priya = await make_actor(seeded)
    spec = charts.ChartSpec.model_validate({"measures": ["budget_allocated", "budget_actual"], "dimension": "budget_month",
                                            "filters": [{"dimension": "category", "values": [IT]}]})
    async with db.session_scope() as s:
        out = await charts.run_spec(s, priya, spec, today=TODAY)
    rows = out["rows"]
    assert [r["label"] for r in rows][0].startswith("Jul") and len(rows) == 9, [r["key"] for r in rows]
    cs = await cells(priya, category=IT)
    by = {r["key"][:7]: r["values"] for r in rows}
    for c in cs:
        if c.month >= date(2026, 7, 1):
            v = by[c.month.isoformat()[:7]]
            assert v["budget_allocated"] == c.adjusted, c.month
            assert v["budget_actual"] == c.actual, c.month
    assert by["2026-10"]["budget_actual"] == 3_980_000


# ---------------------------------------------------------------- H. API

async def test_months_endpoint(seeded):
    c = await client_for()
    r = await c.get(f"/api/budget/lines/{seeded['travel_line_id']}/months")
    assert r.status_code == 200
    body = r.json()
    assert body["category"] == TR and len(body["months"]) == 12 and body["months"][0]["month"] == "2026-04-01"
    assert sum(m["budget_paise"] for m in body["months"]) == 5_000_000
    await c.aclose()


async def test_months_endpoint_other_workspace_404(seeded):
    async with db.session_scope() as s:
        await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    c = await client_for("priya@other.demo")
    assert (await c.get(f"/api/budget/lines/{seeded['travel_line_id']}/months")).status_code == 404
    await c.aclose()


# ---------------------------------------------------------------- I. tool wiring

def test_ten_tools_wired_with_strict_schemas():
    from app.agent import munshi
    from app.agent.tools import budget_months as t
    assert len(t.TOOLS) == 10
    names = {x.name for x in munshi.ALL_TOOLS}
    for tool in t.TOOLS:
        assert tool.name in names
        assert tool.strict_json_schema is True
        json.dumps(tool.params_json_schema)
        assert tool.params_json_schema.get("additionalProperties") is False, tool.name


async def test_budget_action_kinds_registered(seeded):
    from app.services.actions import ACTIONS
    assert {"budget_change", "close_month", "apply_recommendations"} <= set(ACTIONS)
