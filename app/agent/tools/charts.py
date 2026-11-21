"""Chart and view tools. The model composes typed specs; every number comes from a stored ResultSnapshot."""

from __future__ import annotations

from agents import RunContextWrapper, function_tool

from app import db
from app.agent.context import PurserContext, safe_tool
from app.services import charts
from app.services.charts import ChartSpec, ChartSpecPatch, ViewSpec

Ctx = RunContextWrapper[PurserContext]


def _card(snap, **extra) -> dict:
    return {"card": "chart", "snapshot_id": snap.id, "lineage": snap.meta.get("lineage", snap.id), **extra}


@function_tool
@safe_tool
async def describe_chart_options(ctx: Ctx) -> dict:
    """What can be charted for this user: sources, measures (with units), dimensions, chart types and rules.
    Call this when unsure which measure or dimension fits a question."""
    return {"ok": True, **charts.options(ctx.context.actor)}


@function_tool
@safe_tool
async def build_chart(ctx: Ctx, spec: ChartSpec) -> dict:
    """Build a chart from a typed spec and show it. Examples:
    'kaun paisa dena baaki hai / who owes us' -> measures=[receivables_outstanding], dimension=customer.
    'allocated vs spent by category' -> measures=[budget_allocated, budget_spent], dimension=category.
    'monthly bills' -> measures=[bill_amount], dimension=bill_month.
    'spend by category as a treemap' -> measures=[bill_amount], dimension=category, chart=treemap.
    'budget utilisation heatmap' -> measures=[budget_utilisation_pct], dimension=budget_month, series_by=category, chart=heatmap.
    'budget kahan se kahan gaya / transfers' -> measures=[budget_moved], dimension=from_category, series_by=to_category, chart=sankey.
    'daily claims calendar' -> measures=[claims_amount], dimension=day, chart=calendar_heatmap.
    'bills this quarter vs last' -> measures=[bill_amount], date_from/date_to = this quarter, compare=prev_period.
    'liabilities by counterparty / kaunse contract mein kitni liability' -> measures=[liability_count], dimension=counterparty.
    Speak only the returned totals, rows and insights; they are what the screen shows."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        payload = await charts.run_spec(s, a, spec)
        snap = await charts.store(s, a, payload)
        out = charts.summarize(snap)
        ctx.context.show(_card(snap))
    from app.agent.tools.clarify import bump
    await bump(a, "chart", reset=True)  # a rendered chart closes the clarification round
    return {"ok": True, **out}


@function_tool
@safe_tool
async def revise_chart(ctx: Ctx, patch: ChartSpecPatch, snapshot_id: str | None = None) -> dict:
    """Change the current chart ('sirf overdue / only overdue' -> overdue_only=true; 'make it monthly';
    'just Acme' -> add_filters). Omitted fields keep their value, so the grouping is kept.
    snapshot_id defaults to the latest chart in this conversation."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        parent = await charts.load(s, a, snapshot_id)
        spec = charts.apply_patch(ChartSpec.model_validate(parent.spec), patch)
        payload = await charts.run_spec(s, a, spec)
        snap = await charts.store(s, a, payload, parent=parent)
        out = charts.summarize(snap)
        ctx.context.show(_card(snap))
    return {"ok": True, "revised_from": parent.id, **out}


@function_tool
@safe_tool
async def read_chart_value(ctx: Ctx, label: str, series: str | None = None, snapshot_id: str | None = None) -> dict:
    """Read one bar/row of the chart on screen ('Acme ka amount padho'). Reads the stored snapshot, with its filters,
    never a fresh query. If the label is ambiguous, ask which one. Highlights the row on screen."""
    a = ctx.context.actor
    async with db.session_scope() as s:
        snap = await charts.load(s, a, snapshot_id)
        out = charts.read_value(snap, label, series=series)
        ctx.context.show(_card(snap, highlight=out["label"]))
    return {"ok": True, **out}


@function_tool
@safe_tool
async def present_view(ctx: Ctx, view: ViewSpec) -> dict:
    """Arrange up to four charts already built in this conversation into one view (e.g. a briefing),
    each shown as its chart, a table, or a headline number (kpi). Build the charts first."""
    a = ctx.context.actor
    items = []
    async with db.session_scope() as s:
        for it in view.items:
            snap = await charts.load(s, a, it.snapshot_id)
            items.append({"snapshot_id": snap.id, "display": (it.display or "chart"),
                          "title": snap.meta["title"], "totals": charts.summarize(snap)["totals"]})
    ctx.context.show({"card": "view", "title": view.title.strip(), "items": [{"snapshot_id": i["snapshot_id"], "display": i["display"]} for i in items]})
    return {"ok": True, "title": view.title.strip(), "items": items}


TOOLS = [describe_chart_options, build_chart, revise_chart, read_chart_value, present_view]
