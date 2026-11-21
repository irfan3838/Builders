"""Budget writes as propose -> confirm -> receipt actions: change (transfer / top-up / reduce), close a month,
apply trend recommendations. Each execute() re-runs every guard inside the confirming transaction."""

from __future__ import annotations

from app.errors import VALIDATION, DomainError
from app.money import format_inr, rupees_to_paise
from app.services import budget_months as bm
from app.services.actions import Execution, Plan
from app.services.records import today_ist


def _paise(v) -> int:
    try:
        return rupees_to_paise(v)
    except Exception as e:  # noqa: BLE001 - any unparsable amount is a validation error
        raise DomainError(VALIDATION, f"Could not read the amount '{v}'.") from e


async def _change_plan(s, actor, args: dict) -> bm.ChangePlan:
    return await bm.plan_change(
        s, actor, today_ist(), kind=args.get("change", ""), amount_paise=_paise(args.get("amount_rupees")),
        months=args.get("months") or [], source=args.get("source"), dest=args.get("dest"), reason=args.get("reason") or "",
        split=args.get("split") or "equal",
        amounts_paise=[_paise(a) for a in args["amounts_rupees"]] if args.get("amounts_rupees") else None,
        shares_bp=[int(round(float(x) * 100)) for x in args["shares_pct"]] if args.get("shares_pct") else None)


class BudgetChange:
    kind = "budget_change"

    async def plan(self, s, actor, args):
        p = await _change_plan(s, actor, args)
        title, lines, speak = bm.describe_change(p)
        return Plan(title, lines, speak, [])

    async def execute(self, s, actor, args, receipt_id):
        p = await _change_plan(s, actor, args)
        after = await bm.apply_change(s, actor, p, receipt_id)
        title, _lines, _ = bm.describe_change(p)
        return Execution(f"{title} ({', '.join(bm.label(m) for m in p.months)}).", [{"type": "budget_change", **after}])


async def _close_plan(s, actor, args: dict):
    variances = {v["category"]: (v.get("reason") or "other", v.get("note")) for v in args.get("variances") or []}
    return await bm.plan_close(s, actor, today_ist(), args.get("month") or "", variances=variances, carry_over=args.get("carry_over") or [])


class CloseMonth:
    kind = "close_month"

    async def plan(self, s, actor, args):
        m, nxt, rows = await _close_plan(s, actor, args)
        lines = [f"Freeze {bm.label(m)} for {len(rows)} categories. Later bills will not change these month-end figures."]
        for r in rows:
            line = f"{r.category}: spent {format_inr(r.actual)} of {format_inr(r.adjusted)} — {r.status.lower().replace('_', ' ')}"
            if r.variance_reason:
                line += f"; reason: {r.variance_reason.replace('_', ' ')}"
            if r.carry:
                line += f"; carry {format_inr(r.carry)} into {bm.label(nxt)}"
            elif r.status == "UNDERUSED":
                line += "; surplus absorbed"
            lines.append(line + ".")
        missing = [r.category for r in rows if r.status in ("OVERRUN", "UNDERUSED") and not r.variance_reason]
        if missing:
            lines.append(f"No variance reason recorded for: {', '.join(missing)}.")
        return Plan(f"Close {bm.label(m)}", lines, f"Close {bm.label(m)} with these month-end figures?", [])

    async def execute(self, s, actor, args, receipt_id):
        m, nxt, rows = await _close_plan(s, actor, args)
        after = await bm.apply_close(s, actor, m, nxt, rows, receipt_id)
        carried = sum(r.carry for r in rows)
        return Execution(f"{bm.label(m)} closed for {len(rows)} categories" + (f"; {format_inr(carried)} carried into {bm.label(nxt)}"
                         if carried else "") + ".", [{"type": "budget_close", **after}])


def step_id(p) -> str:
    return f"{p.kind}:{p.source or '-'}>{p.dest or '-'}"


async def _rec_plans(s, actor, args: dict):
    today = today_ist()
    target = bm.parse_month(args["target_month"], today) if args.get("target_month") else bm.default_target(today)
    steps = await bm.still_to_do(s, actor, target)
    want = args.get("step_ids") or [step_id(p) for p in steps]
    chosen = [p for p in steps if step_id(p) in want]
    unknown = set(want) - {step_id(p) for p in steps}
    if unknown:
        raise DomainError(VALIDATION, "Some steps are no longer in the plan (already applied or the trend changed). Ask for the "
                          "recommendations again.", unknown_steps=sorted(unknown))
    if not chosen:
        raise DomainError(VALIDATION, f"There is nothing left to apply for {bm.label(target)}.")
    plans = [await bm.plan_change(s, actor, today, kind=p.kind, amount_paise=p.amount_paise, months=[target.isoformat()[:7]],
                                  source=p.source, dest=p.dest, reason=p.reason) for p in chosen]
    return target, plans


class ApplyRecommendations:
    kind = "apply_recommendations"

    async def plan(self, s, actor, args):
        target, plans = await _rec_plans(s, actor, args)
        lines = [f"Apply {len(plans)} recommended change(s) to {bm.label(target)}. All steps succeed together or none does."]
        for p in plans:
            title, ls, _ = bm.describe_change(p)
            lines.append(title + ": " + " ".join(ls[1:-2]))
        net = sum(p.annual_delta for p in plans)
        lines.append("Total budget unchanged." if net == 0 else f"Total budget {'grows' if net > 0 else 'shrinks'} by {format_inr(abs(net))}.")
        return Plan(f"Apply budget recommendations for {bm.label(target)}", lines,
                    f"Apply these {len(plans)} recommended change(s) for {bm.label(target)}?", [])

    async def execute(self, s, actor, args, receipt_id):
        target, plans = await _rec_plans(s, actor, args)
        done = [await bm.apply_change(s, actor, p, receipt_id) for p in plans]
        return Execution(f"Applied {len(done)} recommended change(s) for {bm.label(target)}.",
                         [{"type": "budget_change", **d} for d in done])


ALL = (BudgetChange(), CloseMonth(), ApplyRecommendations())
