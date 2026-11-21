"""Chart engine v2: new chart types, time grains, pct ratios, series cap, compare, budget_flows, contracts."""

from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app import db
from app.errors import AMBIGUOUS, FORBIDDEN, VALIDATION, DomainError
from app.services import budget, charts
from app.services.charts import ChartSpec, ChartSpecPatch
from seed.seed_v1 import seed
from tests.conftest import make_actor
from tests.test_charts import TODAY, run, spec, sql


# ---------------------------------------------------------------- helpers (independent of the engine)

def fyq(d: date) -> str:
    start = d.year if d.month >= 4 else d.year - 1
    return f"FY{start}-{str(start + 1)[-2:]} Q{((d.month - 4) % 12) // 3 + 1}"


def fy(d: date) -> str:
    start = d.year if d.month >= 4 else d.year - 1
    return f"FY{start}-{str(start + 1)[-2:]}"


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


async def expect_validation(actor, **kw) -> DomainError:
    with pytest.raises(DomainError) as e:
        await run(actor, **kw)
    assert e.value.code == VALIDATION, (kw, e.value.code, e.value.message)
    assert e.value.message
    return e.value


async def bills():
    """(business_date, amount, vendor, category) of non-rejected bills."""
    rows = await sql("""select b.business_date, b.amount_paise, p.name, l.category from bills b
                        join parties p on p.id=b.vendor_party_id join budget_lines l on l.id=b.line_id
                        where b.state <> 'rejected' order by b.id""")
    return [tuple(r) for r in rows]


async def set_bill_dates(dates: list[date]):
    ids = [r[0] for r in await sql("select id from bills order by id")]
    assert len(ids) == len(dates)
    async with db.session_scope() as s:
        from sqlalchemy import text
        for i, d in zip(ids, dates):
            await s.execute(text("update bills set business_date=:d where id=:i"), {"d": d, "i": i})


async def lines_by_cat():
    return {c: i for i, c in await sql("select id, category from budget_lines")}


async def post_move(ws, line, amount, kind, month, *, receipt=None, event=None):
    async with db.session_scope() as s:
        await budget.post(s, ws, line, "allocation", amount, kind, receipt_id=receipt, economic_event_id=event, fiscal_month=month)


async def as_role(ids, who, role):
    return replace(await make_actor(ids, who), role=role)


# ---------------------------------------------------------------- 1. new chart types: shape rules

OK_SHAPES = [
    ("pie", dict(measures=["bill_amount"], dimension="vendor", chart="pie")),
    ("donut", dict(measures=["bill_amount"], dimension="vendor", chart="donut")),
    ("treemap flat", dict(measures=["bill_amount"], dimension="vendor", chart="treemap")),
    ("treemap nested", dict(measures=["bill_amount"], dimension="category", series_by="vendor", chart="treemap")),
    ("heatmap", dict(measures=["budget_allocated"], dimension="budget_month", series_by="category", chart="heatmap")),
    ("calendar", dict(measures=["bill_amount"], dimension="day", chart="calendar_heatmap")),
    ("sankey", dict(measures=["bill_amount"], dimension="category", series_by="vendor", chart="sankey")),
]

BAD_SHAPES = [
    ("pie no dim", dict(measures=["bill_amount"], chart="pie")),
    ("pie time dim", dict(measures=["bill_amount"], dimension="bill_month", chart="pie")),
    ("pie two measures", dict(measures=["bill_amount", "payables_outstanding"], dimension="vendor", chart="pie")),
    ("pie series_by", dict(measures=["bill_amount"], dimension="vendor", series_by="category", chart="pie")),
    ("pie quarter dim", dict(measures=["bill_amount"], dimension="quarter", chart="pie")),
    ("treemap no dim", dict(measures=["bill_amount"], chart="treemap")),
    ("treemap time dim", dict(measures=["bill_amount"], dimension="bill_month", chart="treemap")),
    ("treemap two measures", dict(measures=["bill_amount", "payables_outstanding"], dimension="vendor", chart="treemap")),
    ("heatmap no series", dict(measures=["bill_amount"], dimension="vendor", chart="heatmap")),
    ("heatmap no dim", dict(measures=["bill_amount"], chart="heatmap")),
    ("calendar non-day", dict(measures=["bill_amount"], dimension="vendor", chart="calendar_heatmap")),
    ("calendar month", dict(measures=["bill_amount"], dimension="bill_month", chart="calendar_heatmap")),
    ("calendar with series", dict(measures=["bill_amount"], dimension="day", series_by="vendor", chart="calendar_heatmap")),
    ("calendar no dim", dict(measures=["bill_amount"], chart="calendar_heatmap")),
    ("sankey no series", dict(measures=["bill_amount"], dimension="category", chart="sankey")),
    ("sankey time dim", dict(measures=["bill_amount"], dimension="bill_month", series_by="vendor", chart="sankey")),
    ("sankey two measures", dict(measures=["bill_amount", "payables_outstanding"], dimension="category", series_by="vendor", chart="sankey")),
]


@pytest.mark.parametrize("name,kw", OK_SHAPES, ids=[b[0] for b in OK_SHAPES])
def test_chart_problem_accepts_valid_shapes(name, kw):
    assert charts.chart_problem(spec(**kw)) is None


@pytest.mark.parametrize("name,kw", BAD_SHAPES, ids=[b[0] for b in BAD_SHAPES])
def test_chart_problem_rejects_bad_shapes(name, kw):
    assert charts.chart_problem(spec(**kw))


def test_two_measure_heatmap_rejected_by_chart_problem():
    s = spec(measures=["bill_amount", "payables_outstanding"], dimension="category", series_by="vendor", chart="heatmap")
    assert charts.chart_problem(s)


@pytest.mark.parametrize("name,kw", BAD_SHAPES, ids=[b[0] for b in BAD_SHAPES])
async def test_bad_shapes_are_validation_errors(seeded, name, kw):
    priya = await make_actor(seeded)
    await expect_validation(priya, **kw)


@pytest.mark.parametrize("name,kw", OK_SHAPES, ids=[b[0] for b in OK_SHAPES])
async def test_valid_shapes_run_and_keep_requested_type(seeded, name, kw):
    priya = await make_actor(seeded)
    out = await run(priya, **kw)
    assert out["meta"]["chart"] == kw["chart"]
    (exp,) = await sql("select sum(amount_paise) from bills where state<>'rejected'") if kw["measures"] == ["bill_amount"] else [None]
    if exp is not None:
        assert out["totals"]["bill_amount"] == int(exp[0])


def test_donut_message_names_donut_and_pie():
    assert "donut" in charts.chart_problem(spec(measures=["bill_amount"], chart="donut", dimension="bill_month"))
    assert "pie" in charts.chart_problem(spec(measures=["bill_amount"], chart="pie", dimension="bill_month"))


async def test_options_lists_new_chart_types_and_rules(seeded):
    priya = await make_actor(seeded)
    o = charts.options(priya)
    for t in ("pie", "treemap", "heatmap", "calendar_heatmap", "sankey"):
        assert t in o["chart_types"]


# ---------------------------------------------------------------- 2. time grains

async def test_bills_by_quarter_and_fy_match_independent_sums(seeded):
    priya = await make_actor(seeded)
    rows = await bills()
    for dim, fn in (("quarter", fyq), ("fy", fy)):
        out = await run(priya, measures=["bill_amount"], dimension=dim)
        want: dict = {}
        for d, amt, *_ in rows:
            want[fn(d)] = want.get(fn(d), 0) + int(amt)
        assert {r["key"]: r["values"]["bill_amount"] for r in out["rows"]} == want
        assert out["totals"]["bill_amount"] == sum(want.values())


async def test_quarter_boundaries_follow_indian_fy(seeded):
    priya = await make_actor(seeded)
    dates = [date(2026, 3, 31), date(2026, 4, 1), date(2026, 6, 30), date(2026, 7, 1), date(2027, 1, 1)]
    await set_bill_dates(dates)
    rows = await bills()
    out = await run(priya, measures=["bill_amount"], dimension="quarter")
    got = {r["key"]: r["values"]["bill_amount"] for r in out["rows"]}
    want: dict = {}
    for d, amt, *_ in rows:
        want[fyq(d)] = want.get(fyq(d), 0) + int(amt)
    assert got == want
    # explicit expectations independent of fyq(): Mar-31-2026 is Q4 of FY2025-26, Apr-1 and Jun-30 are Q1, Jul-1 is Q2, Jan-1-2027 is Q4
    assert set(got) == {"FY2025-26 Q4", "FY2026-27 Q1", "FY2026-27 Q2", "FY2026-27 Q4"}
    # keys sort in time order and rows come out in that order
    assert [r["key"] for r in out["rows"]] == sorted(got)
    fy_out = await run(priya, measures=["bill_amount"], dimension="fy")
    assert {r["key"] for r in fy_out["rows"]} == {"FY2025-26", "FY2026-27"}


async def test_quarter_and_fy_labels(seeded):
    priya = await make_actor(seeded)
    q = await run(priya, measures=["bill_count"], dimension="quarter")
    assert [(r["key"], r["label"]) for r in q["rows"]] == [("FY2026-27 Q3", "Q3 FY26-27")]
    f = await run(priya, measures=["bill_count"], dimension="fy")
    assert [(r["key"], r["label"]) for r in f["rows"]] == [("FY2026-27", "FY 2026-27")]
    assert charts.key_label("FY2025-26 Q4", "quarter") == "Q4 FY25-26"
    assert charts.key_label("FY2026-27", "fy") == "FY 2026-27"
    assert charts.key_label("FY2099-00", "fy") == "FY 2099-00"


async def test_bills_by_day_and_week(seeded):
    priya = await make_actor(seeded)
    rows = await bills()
    day = await run(priya, measures=["bill_amount"], dimension="day")
    want_day: dict = {}
    for d, amt, *_ in rows:
        want_day[d.isoformat()] = want_day.get(d.isoformat(), 0) + int(amt)
    assert {r["key"]: r["values"]["bill_amount"] for r in day["rows"]} == want_day
    assert len(day["rows"]) == len(want_day)  # no gap-fill for the day grain
    assert day["rows"][0]["label"] == date.fromisoformat(day["rows"][0]["key"]).strftime("%d %b %Y")
    wk = await run(priya, measures=["bill_amount"], dimension="week")
    want_wk: dict = {}
    for d, amt, *_ in rows:
        want_wk[monday(d).isoformat()] = want_wk.get(monday(d).isoformat(), 0) + int(amt)
    assert {r["key"]: r["values"]["bill_amount"] for r in wk["rows"]} == want_wk
    assert all(date.fromisoformat(r["key"]).weekday() == 0 for r in wk["rows"])
    assert wk["rows"][0]["label"].startswith("Week of ")
    assert wk["totals"]["bill_amount"] == day["totals"]["bill_amount"]


async def test_claims_have_all_four_grains(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        from sqlalchemy import text
        await s.execute(text("update claims set business_date=:d"), {"d": date(2027, 2, 10)})
    for dim, key in (("day", "2027-02-10"), ("week", "2027-02-08"), ("quarter", "FY2026-27 Q4"), ("fy", "FY2026-27")):
        out = await run(priya, measures=["claims_amount"], dimension=dim)
        assert [r["key"] for r in out["rows"]] == [key], dim
        assert out["totals"]["claims_amount"] == 135000


async def test_receivables_and_budget_have_only_quarter_and_fy(seeded):
    priya = await make_actor(seeded)
    for m in ("invoice_count", "budget_allocated"):
        for dim in ("day", "week"):
            await expect_validation(priya, measures=[m], dimension=dim)
        for dim in ("quarter", "fy"):
            out = await run(priya, measures=[m], dimension=dim)
            assert out["rows"]


async def test_receivables_by_quarter_matches_billing_month(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["invoice_count"], dimension="quarter")
    exp: dict = {}
    for y, mth in await sql("select year, month from invoices"):
        k = fyq(date(y, mth, 1))
        exp[k] = exp.get(k, 0) + 1
    assert {r["key"]: r["values"]["invoice_count"] for r in out["rows"]} == exp
    fyo = await run(priya, measures=["invoice_count"], dimension="fy")
    assert {r["key"]: r["values"]["invoice_count"] for r in fyo["rows"]} == {"FY2026-27": 16}


async def test_budget_by_quarter_and_fy_match_movements(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["budget_allocated", "budget_spent"], dimension="quarter")
    exp: dict = {}
    for fm, bucket, amt in await sql("select fiscal_month, bucket, sum(amount_paise) from budget_movements group by 1,2"):
        e = exp.setdefault(fyq(fm), {"budget_allocated": 0, "budget_spent": 0})
        if bucket == "allocation":
            e["budget_allocated"] += int(amt)
        if bucket == "spent":
            e["budget_spent"] += int(amt)
    assert {r["key"]: r["values"] for r in out["rows"]} == exp
    assert set(exp) == {"FY2026-27 Q2", "FY2026-27 Q3", "FY2026-27 Q4"}  # not gap-filled, no month keys mixed in
    fyo = await run(priya, measures=["budget_allocated"], dimension="fy")
    assert [r["key"] for r in fyo["rows"]] == ["FY2026-27"]


async def test_line_chart_accepts_any_time_dimension_and_no_gap_fill_outside_month(seeded):
    priya = await make_actor(seeded)
    for dim in ("day", "week", "quarter", "fy"):
        out = await run(priya, measures=["bill_amount"], dimension=dim, chart="line")
        assert out["meta"]["chart"] == "line" and out["meta"]["dimension"]["kind"] == "time"
        assert out["meta"]["dimension"]["grain"] == dim
    # month grain still gap-fills
    await set_bill_dates([date(2026, 8, 1), date(2026, 8, 5), date(2026, 11, 1), date(2026, 11, 8), date(2026, 11, 14)])
    m = await run(priya, measures=["bill_amount"], dimension="bill_month", chart="line")
    assert [r["key"] for r in m["rows"]] == ["2026-08", "2026-09", "2026-10", "2026-11"]
    d = await run(priya, measures=["bill_amount"], dimension="day", chart="line")
    assert len(d["rows"]) == 5  # only days that have bills (no gap-fill)


async def test_auto_chart_for_new_time_dims_is_line(seeded):
    priya = await make_actor(seeded)
    for dim in ("day", "week", "quarter", "fy"):
        out = await run(priya, measures=["bill_amount"], dimension=dim)
        assert out["meta"]["chart"] == "line"


# ---------------------------------------------------------------- 3. pct ratio measure

async def pct_expected():
    rows = await sql("""select l.category,
        coalesce(sum(m.amount_paise) filter (where m.bucket in ('committed','spent')),0) n,
        coalesce(sum(m.amount_paise) filter (where m.bucket='allocation'),0) d
        from budget_movements m join budget_lines l on l.id=m.line_id group by 1""")
    return {c: (int(n), int(d)) for c, n, d in rows}


async def test_utilisation_pct_by_category_is_ratio_of_sums(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["budget_utilisation_pct"], dimension="category")
    exp = await pct_expected()
    got = {r["key"]: r["values"]["budget_utilisation_pct"] for r in out["rows"]}
    assert got == {c: (round(n * 10000 / d) if d else 0) for c, (n, d) in exp.items()}
    tn, td = sum(n for n, _ in exp.values()), sum(d for _, d in exp.values())
    assert out["totals"]["budget_utilisation_pct"] == round(tn * 10000 / td)
    assert out["totals"]["budget_utilisation_pct"] != sum(got.values())
    assert all(r["parts"]["budget_utilisation_pct"] == list(exp[r["key"]]) for r in out["rows"])
    assert out["meta"]["measures"][0]["unit"] == "pct"


async def test_utilisation_pct_single_total_and_by_month(seeded):
    priya = await make_actor(seeded)
    exp = await pct_expected()
    out = await run(priya, measures=["budget_utilisation_pct"])
    tn, td = sum(n for n, _ in exp.values()), sum(d for _, d in exp.values())
    assert out["totals"]["budget_utilisation_pct"] == round(tn * 10000 / td)
    # per month: group parts then ratio
    bym = await run(priya, measures=["budget_utilisation_pct"], dimension="budget_month")
    rows = await sql("""select to_char(fiscal_month,'YYYY-MM'),
        coalesce(sum(amount_paise) filter (where bucket in ('committed','spent')),0),
        coalesce(sum(amount_paise) filter (where bucket='allocation'),0) from budget_movements group by 1""")
    want = {k: (round(int(n) * 10000 / int(d)) if int(d) else 0) for k, n, d in rows}
    assert {r["key"]: r["values"]["budget_utilisation_pct"] for r in bym["rows"]} == want
    # July: 2,360,000 spent of 2,375,000 allocated = 99.37% -> 9937 bp
    assert want["2026-07"] == round(2_360_000 * 10000 / 2_375_000)


async def test_pct_top_n_refused(seeded):
    priya = await make_actor(seeded)
    e = await expect_validation(priya, measures=["budget_utilisation_pct"], dimension="category", top_n=2)
    assert "top_n" in e.message


async def test_pct_series_not_folded_into_other(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["budget_utilisation_pct"], dimension="category", series_by="budget_month", chart="grouped_bar")
    series = {r["series"] for r in out["rows"]}
    assert "Other" not in series
    assert len(series) == 9  # Jul..Mar, all kept
    assert out["meta"]["folded"] is None
    # same shape for a non-pct measure does fold
    flat = await run(priya, measures=["budget_allocated"], dimension="category", series_by="budget_month", chart="grouped_bar")
    assert "Other" in {r["series"] for r in flat["rows"]}


def test_fmt_value_pct():
    assert charts.fmt_value(8534, "pct") == "85.3%"
    assert charts.fmt_value(0, "pct") == "0.0%"
    assert charts.fmt_value(12000, "pct") == "120.0%"
    assert charts.fmt_value(5, "count") == "5"


async def test_pct_summarize_reports_highest_lowest_not_largest_and_public_display(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        payload = await charts.run_spec(s, priya, spec(measures=["budget_utilisation_pct"], dimension="budget_month", series_by="category",
                                                       chart="heatmap"), today=TODAY)
        snap = await charts.store(s, priya, payload)
        sm = charts.summarize(snap)
        pub = charts.public(snap)
    joined = " | ".join(sm["insights"])
    assert "Highest:" in joined and "Lowest:" in joined
    assert "Largest" not in joined
    vals = [r["values"]["budget_utilisation_pct"] for r in snap.rows]
    assert f"{max(vals) / 100:.1f}%" in joined and f"{min(vals) / 100:.1f}%" in joined
    assert sm["totals"]["utilisation"].endswith("%")
    t = pub["totals"]["budget_utilisation_pct"]
    assert t["display"] == f"{t['value'] / 100:.1f}%"


async def test_non_pct_summarize_still_has_largest(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        snap = await charts.store(s, priya, await charts.run_spec(s, priya, spec(measures=["bill_amount"], dimension="vendor"), today=TODAY))
        sm = charts.summarize(snap)
    assert any(i.startswith("Largest:") for i in sm["insights"])


# ---------------------------------------------------------------- 4. series cap skipped for heatmap / sankey / treemap

async def test_series_cap_skipped_for_heatmap_sankey_treemap_but_not_grouped(seeded):
    priya = await make_actor(seeded)
    cats = {c for (c,) in await sql("select category from budget_lines")}
    months = {m for (m,) in await sql("select distinct to_char(fiscal_month,'YYYY-MM') from budget_movements")}
    assert len(cats) == 6 and len(months) == 9
    # heatmap of 6 categories as rows keeps all 6 (and sankey / treemap keep every series)
    h = await run(priya, measures=["budget_allocated"], dimension="budget_month", series_by="category", chart="heatmap")
    assert {r["series"] for r in h["rows"]} == cats and h["meta"]["folded"] is None
    for chart in ("heatmap", "sankey", "treemap"):
        out = await run(priya, measures=["budget_allocated"], dimension="category", series_by="budget_month", chart=chart)
        assert len({r["series"] for r in out["rows"]}) == 9, chart
        assert "Other" not in {r["series"] for r in out["rows"]} and out["meta"]["folded"] is None
        assert out["totals"] == h["totals"]
    g = await run(priya, measures=["budget_allocated"], dimension="budget_month", series_by="category", chart="grouped_bar")
    assert len({r["series"] for r in g["rows"]}) == 4 and "Other" in {r["series"] for r in g["rows"]}
    assert g["meta"]["folded"]["series"]["kept"] == 3
    assert g["totals"] == h["totals"]


async def test_heatmap_rows_are_full_category_by_month_grid_sums(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["budget_allocated"], dimension="budget_month", series_by="category", chart="heatmap")
    exp = {(m, c): int(a) for m, c, a in await sql("""select to_char(m.fiscal_month,'YYYY-MM'), l.category, sum(m.amount_paise)
        from budget_movements m join budget_lines l on l.id=m.line_id where m.bucket='allocation' group by 1,2""")}
    got = {(r["key"], r["series"]): r["values"]["budget_allocated"] for r in out["rows"]}
    assert got == exp


# ---------------------------------------------------------------- 5. compare

async def bill_sum(d1, d2):
    (r,) = await sql("select coalesce(sum(amount_paise),0) from bills where state<>'rejected' and business_date between :a and :b",
                     a=d1, b=d2)
    return int(r[0])


async def test_prev_period_whole_month_matches_sql(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["bill_amount"], dimension="vendor", date_from=date(2026, 11, 1), date_to=date(2026, 11, 30),
                    compare="prev_period")
    cur, prev = await bill_sum(date(2026, 11, 1), date(2026, 11, 30)), await bill_sum(date(2026, 10, 1), date(2026, 10, 31))
    assert cur > 0 and prev > 0
    c = out["meta"]["compare"]
    assert (c["current"], c["previous"]) == ("Nov 2026", "Oct 2026")
    assert (c["current_total"], c["previous_total"]) == (cur, prev)
    assert c["change_pct"] == round(100 * (cur - prev) / prev, 1)
    assert out["totals"]["bill_amount"] == cur  # current window only
    by = {}
    for r in out["rows"]:
        by.setdefault(r["series"], 0)
        by[r["series"]] += r["values"]["bill_amount"]
    assert by == {"Nov 2026": cur, "Oct 2026": prev}
    assert out["meta"]["series_by"]["name"] == "period"


async def test_prev_period_multi_month_window_uses_n_months_before(seeded):
    priya = await make_actor(seeded)
    await set_bill_dates([date(2026, 7, 15), date(2026, 9, 30), date(2026, 10, 1), date(2026, 11, 8), date(2026, 12, 31)])
    out = await run(priya, measures=["bill_amount"], dimension="vendor", date_from=date(2026, 10, 1), date_to=date(2026, 12, 31),
                    compare="prev_period")
    c = out["meta"]["compare"]
    assert c["previous"] == "Jul 2026–Sep 2026" and c["current"] == "Oct 2026–Dec 2026"
    assert c["current_total"] == await bill_sum(date(2026, 10, 1), date(2026, 12, 31))
    assert c["previous_total"] == await bill_sum(date(2026, 7, 1), date(2026, 9, 30))
    assert c["previous_total"] > 0


async def test_prev_period_non_whole_window_uses_same_number_of_days(seeded):
    priya = await make_actor(seeded)
    d1, d2 = date(2026, 11, 5), date(2026, 11, 14)  # 10 days
    out = await run(priya, measures=["bill_amount"], dimension="vendor", date_from=d1, date_to=d2, compare="prev_period")
    p1, p2 = d1 - timedelta(days=10), d1 - timedelta(days=1)
    c = out["meta"]["compare"]
    assert c["current_total"] == await bill_sum(d1, d2)
    assert c["previous_total"] == await bill_sum(p1, p2)
    assert c["previous"] == f"{p1:%d %b %Y}–{p2:%d %b %Y}"


async def test_prev_period_zero_previous_gives_none_change(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["bill_amount"], dimension="vendor", date_from=date(2026, 10, 1), date_to=date(2026, 12, 31),
                    compare="prev_period")
    c = out["meta"]["compare"]
    assert c["previous_total"] == 0 and c["change_pct"] is None
    assert c["current_total"] == await bill_sum(date(2026, 10, 1), date(2026, 12, 31))


async def test_yoy_shifts_twelve_months_and_aligns_month_axis(seeded):
    priya = await make_actor(seeded)
    await set_bill_dates([date(2025, 10, 15), date(2025, 11, 3), date(2026, 10, 1), date(2026, 11, 8), date(2026, 11, 14)])
    out = await run(priya, measures=["bill_amount"], dimension="bill_month", date_from=date(2026, 10, 1), date_to=date(2026, 11, 30),
                    compare="yoy")
    c = out["meta"]["compare"]
    assert (c["current"], c["previous"]) == ("Oct 2026–Nov 2026", "Oct 2025–Nov 2025")
    cur, prev = await bill_sum(date(2026, 10, 1), date(2026, 11, 30)), await bill_sum(date(2025, 10, 1), date(2025, 11, 30))
    assert (c["current_total"], c["previous_total"]) == (cur, prev) and prev > 0
    assert c["change_pct"] == round(100 * (cur - prev) / prev, 1)
    # previous-year rows sit on the current-year month keys
    assert {r["key"] for r in out["rows"]} == {"2026-10", "2026-11"}
    by = {(r["key"], r["series"]): r["values"]["bill_amount"] for r in out["rows"]}
    assert by[("2026-10", "Oct 2025–Nov 2025")] == await bill_sum(date(2025, 10, 1), date(2025, 10, 31))
    assert by[("2026-11", "Oct 2025–Nov 2025")] == await bill_sum(date(2025, 11, 1), date(2025, 11, 30))
    assert out["totals"]["bill_amount"] == cur
    assert out["meta"]["chart"] == "line"
    assert {r["label"] for r in out["rows"]} == {"Oct 2026", "Nov 2026"}


async def test_prev_period_month_axis_aligns_onto_current(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["bill_amount"], dimension="bill_month", date_from=date(2026, 11, 1), date_to=date(2026, 12, 31),
                    compare="prev_period")
    c = out["meta"]["compare"]
    assert c["previous"] == "Sep 2026–Oct 2026"
    # October bills of the previous window show up under December on the shared axis
    by = {(r["key"], r["series"]): r["values"]["bill_amount"] for r in out["rows"]}
    assert by[("2026-12", "Sep 2026–Oct 2026")] == await bill_sum(date(2026, 10, 1), date(2026, 10, 31))
    assert c["current_total"] == await bill_sum(date(2026, 11, 1), date(2026, 12, 31))


async def test_compare_on_other_sources_and_grouped_chart(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["invoice_count"], dimension="customer", date_from=date(2026, 11, 1), date_to=date(2026, 11, 30),
                    compare="prev_period", chart="grouped_bar")
    cur = (await sql("select count(*) from invoices where year=2026 and month=11"))[0][0]
    prev = (await sql("select count(*) from invoices where year=2026 and month=10"))[0][0]
    assert (out["meta"]["compare"]["current_total"], out["meta"]["compare"]["previous_total"]) == (cur, prev)
    assert out["meta"]["chart"] == "grouped_bar"
    # compare plus > 3 customers: series cap must not fold the two periods
    assert {r["series"] for r in out["rows"]} == {"Nov 2026", "Oct 2026"}


COMPARE_BAD = [
    ("no dates", dict(measures=["bill_amount"], dimension="vendor", compare="prev_period")),
    ("one date", dict(measures=["bill_amount"], dimension="vendor", date_from=date(2026, 11, 1), compare="yoy")),
    ("series_by", dict(measures=["bill_amount"], dimension="vendor", series_by="category", date_from=date(2026, 11, 1),
                       date_to=date(2026, 11, 30), compare="prev_period")),
    ("two measures", dict(measures=["bill_amount", "payables_outstanding"], dimension="vendor", date_from=date(2026, 11, 1),
                          date_to=date(2026, 11, 30), compare="yoy")),
    ("day axis", dict(measures=["bill_amount"], dimension="day", date_from=date(2026, 11, 1), date_to=date(2026, 11, 30), compare="prev_period")),
    ("quarter axis", dict(measures=["bill_amount"], dimension="quarter", date_from=date(2026, 10, 1), date_to=date(2026, 12, 31),
                          compare="yoy")),
    ("partial month axis", dict(measures=["bill_amount"], dimension="bill_month", date_from=date(2026, 11, 5), date_to=date(2026, 11, 30),
                                compare="prev_period")),
    ("partial month end", dict(measures=["bill_amount"], dimension="bill_month", date_from=date(2026, 11, 1), date_to=date(2026, 11, 29),
                               compare="yoy")),
    ("source without dates", dict(measures=["budget_allocated"], dimension="category", date_from=date(2026, 11, 1),
                                  date_to=date(2026, 11, 30), compare="prev_period")),
    ("mom category dim", dict(measures=["bill_amount"], dimension="vendor", compare="mom")),
    ("mom no dim", dict(measures=["bill_amount"], compare="mom")),
    ("mom quarter dim", dict(measures=["bill_amount"], dimension="quarter", compare="mom")),
    ("mom series_by", dict(measures=["bill_amount"], dimension="bill_month", series_by="vendor", compare="mom")),
    ("mom two measures", dict(measures=["bill_amount", "bill_count"], dimension="bill_month", compare="mom")),
]


@pytest.mark.parametrize("name,kw", COMPARE_BAD, ids=[b[0] for b in COMPARE_BAD])
async def test_compare_validation(seeded, name, kw):
    priya = await make_actor(seeded)
    await expect_validation(priya, **kw)


async def test_compare_none_is_inert(seeded):
    priya = await make_actor(seeded)
    a = await run(priya, measures=["bill_amount"], dimension="vendor")
    b = await run(priya, measures=["bill_amount"], dimension="vendor", compare="none")
    assert a["rows"] == b["rows"] and b["meta"]["compare"] is None and b["meta"]["changes"] is None


async def test_mom_changes_against_previous_row(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["budget_spent"], dimension="budget_month", compare="mom")
    rows = await sql("""select to_char(fiscal_month,'YYYY-MM'), coalesce(sum(amount_paise) filter (where bucket='spent'),0)
                        from budget_movements group by 1 order by 1""")
    vals = [(k, int(v)) for k, v in rows]
    exp, prev = [], None
    for k, v in vals:
        exp.append(round(100 * (v - prev) / abs(prev), 1) if prev else None)
        prev = v
    ch = out["meta"]["changes"]
    assert [c["change_pct"] for c in ch] == exp
    assert ch[0]["change_pct"] is None  # first row
    assert [c["label"] for c in ch] == [r["label"] for r in out["rows"]]
    # a month that follows a zero month has no % (Dec follows Nov spent 0), and Nov is -100%
    by = {r["key"]: c["change_pct"] for r, c in zip(out["rows"], ch)}
    assert by["2026-11"] == -100.0 and by["2026-12"] is None


async def test_mom_on_gap_filled_month_axis(seeded):
    priya = await make_actor(seeded)
    await set_bill_dates([date(2026, 8, 1), date(2026, 8, 5), date(2026, 11, 1), date(2026, 11, 8), date(2026, 11, 14)])
    out = await run(priya, measures=["bill_amount"], dimension="bill_month", compare="mom")
    ch = out["meta"]["changes"]
    assert [c["label"] for c in ch] == ["Aug 2026", "Sep 2026", "Oct 2026", "Nov 2026"]
    assert [c["change_pct"] for c in ch] == [None, -100.0, None, None]
    s = None
    async with db.session_scope() as sess:
        snap = await charts.store(sess, priya, out)
        s = charts.summarize(snap)
    assert all(c["change_pct"] is not None for c in s["month_over_month"])


async def test_summarize_includes_comparison(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        out = await charts.run_spec(s, priya, spec(measures=["bill_amount"], dimension="vendor", date_from=date(2026, 11, 1),
                                                   date_to=date(2026, 11, 30), compare="prev_period"), today=TODAY)
        sm = charts.summarize(await charts.store(s, priya, out))
    assert sm["comparison"]["current"] == "Nov 2026" and sm["comparison"]["current_total"].startswith("₹")


# ---------------------------------------------------------------- 6. budget_flows

M = date(2026, 12, 1)


async def flows(actor, **kw):
    return await run(actor, **kw)


async def test_budget_flows_empty_on_fresh_seed(seeded):
    priya = await make_actor(seeded)
    out = await flows(priya, measures=["budget_moved"], dimension="from_category", series_by="to_category", chart="sankey")
    assert out["rows"] == [] and out["totals"]["budget_moved"] == 0
    kpi = await flows(priya, measures=["budget_moved"])
    assert kpi["totals"]["budget_moved"] == 0


async def test_budget_flows_conservation_and_directions(seeded):
    ws, priya = seeded["workspace_id"], await make_actor(seeded)
    L = await lines_by_cat()
    # transfer 300_000 Travel -> Events (receipt 501), same month
    await post_move(ws, L["Travel"], -300_000, "budget_transfer_out", M, receipt=501)
    await post_move(ws, L["Events"], 300_000, "budget_transfer_in", M, receipt=501)
    # transfer via the seed-style economic event id
    await post_move(ws, L["Logistics"], -50_000, "budget_transfer_out", M, event="evt-9")
    await post_move(ws, L["Conveyance"], 50_000, "budget_transfer_in", M, event="evt-9")
    # top-up and reduction
    await post_move(ws, L["IT & Cloud"], 700_000, "budget_top_up", M, receipt=502)
    await post_move(ws, L["Office Supplies"], -120_000, "budget_reduction", M, receipt=503)
    out = await flows(priya, measures=["budget_moved"], dimension="from_category", series_by="to_category", chart="sankey")
    got = {(r["key"], r["series"]): r["values"]["budget_moved"] for r in out["rows"]}
    assert got == {("Travel", "Events"): 300_000, ("Logistics", "Conveyance"): 50_000,
                   ("New budget", "IT & Cloud"): 700_000, ("Office Supplies", "Returned"): 120_000}
    assert out["totals"]["budget_moved"] == 300_000 + 50_000 + 700_000 + 120_000
    # conservation against the ledger: positive legs of transfers + top-ups + |reductions|
    (ledger,) = await sql("""select
        coalesce(sum(amount_paise) filter (where kind='budget_transfer_in'),0)
      + coalesce(sum(amount_paise) filter (where kind='budget_top_up'),0)
      + coalesce(-sum(amount_paise) filter (where kind='budget_reduction'),0) from budget_movements""")
    assert out["totals"]["budget_moved"] == int(ledger[0])
    assert out["meta"]["chart"] == "sankey" and out["meta"]["folded"] is None


async def test_budget_flows_other_dimensions_and_filters(seeded):
    ws, priya = seeded["workspace_id"], await make_actor(seeded)
    L = await lines_by_cat()
    await post_move(ws, L["Travel"], -300_000, "budget_transfer_out", date(2026, 12, 1), receipt=601)
    await post_move(ws, L["Events"], 300_000, "budget_transfer_in", date(2026, 12, 1), receipt=601)
    await post_move(ws, L["IT & Cloud"], 100_000, "budget_top_up", date(2027, 2, 1), receipt=602)
    byq = await flows(priya, measures=["budget_moved"], dimension="quarter")
    assert {r["key"]: r["values"]["budget_moved"] for r in byq["rows"]} == {"FY2026-27 Q3": 300_000, "FY2026-27 Q4": 100_000}
    byfy = await flows(priya, measures=["budget_moved"], dimension="fy")
    assert [(r["key"], r["values"]["budget_moved"]) for r in byfy["rows"]] == [("FY2026-27", 400_000)]
    bym = await flows(priya, measures=["budget_moved"], dimension="budget_month")
    assert {r["key"]: r["values"]["budget_moved"] for r in bym["rows"]}["2026-12"] == 300_000
    flt = await flows(priya, measures=["budget_moved"], dimension="to_category",
                      filters=[{"dimension": "from_category", "values": ["New budget"]}])
    assert {r["key"]: r["values"]["budget_moved"] for r in flt["rows"]} == {"IT & Cloud": 100_000}
    ranged = await flows(priya, measures=["budget_moved"], date_from=date(2027, 1, 1), date_to=date(2027, 3, 31))
    assert ranged["totals"]["budget_moved"] == 100_000


async def test_budget_flows_unpaired_leg_makes_no_transfer(seeded):
    ws, priya = seeded["workspace_id"], await make_actor(seeded)
    L = await lines_by_cat()
    await post_move(ws, L["Travel"], -300_000, "budget_transfer_out", M, receipt=701)  # no in leg
    await post_move(ws, L["Events"], 200_000, "budget_transfer_in", M, receipt=702)  # no out leg
    # legs with the same receipt but different months do not pair
    await post_move(ws, L["Logistics"], -80_000, "budget_transfer_out", date(2026, 12, 1), receipt=703)
    await post_move(ws, L["Conveyance"], 80_000, "budget_transfer_in", date(2027, 1, 1), receipt=703)
    out = await flows(priya, measures=["budget_moved"], dimension="from_category", series_by="to_category")
    assert out["rows"] == [] and out["totals"]["budget_moved"] == 0


async def test_budget_flows_multi_month_transfer_pairs_per_month(seeded):
    ws, priya = seeded["workspace_id"], await make_actor(seeded)
    L = await lines_by_cat()
    for m, amt in ((date(2026, 12, 1), 100_000), (date(2027, 1, 1), 150_000)):  # one receipt, two months (how apply_change posts it)
        await post_move(ws, L["Travel"], -amt, "budget_transfer_out", m, receipt=801)
        await post_move(ws, L["Events"], amt, "budget_transfer_in", m, receipt=801)
    out = await flows(priya, measures=["budget_moved"], dimension="from_category", series_by="to_category")
    assert out["totals"]["budget_moved"] == 250_000
    assert [(r["key"], r["series"], r["values"]["budget_moved"]) for r in out["rows"]] == [("Travel", "Events", 250_000)]


async def test_budget_flows_does_not_change_budget_source_and_is_workspace_scoped(seeded):
    ws, priya = seeded["workspace_id"], await make_actor(seeded)
    L = await lines_by_cat()
    await post_move(ws, L["IT & Cloud"], 123_000, "budget_top_up", M, receipt=901)
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    other_priya = await make_actor(other, "priya")
    mine = await flows(priya, measures=["budget_moved"])
    theirs = await flows(other_priya, measures=["budget_moved"])
    assert mine["totals"]["budget_moved"] == 123_000 and theirs["totals"]["budget_moved"] == 0


async def test_budget_flows_forbidden_for_employees_and_hr(seeded):
    arjun, neha = await make_actor(seeded, "arjun"), await make_actor(seeded, "neha")
    hr = await as_role(seeded, "priya", "hr_admin")
    for a in (arjun, neha, hr):
        with pytest.raises(DomainError) as e:
            await run(a, measures=["budget_moved"])
        assert e.value.code == FORBIDDEN
    fa = await as_role(seeded, "priya", "finance_approver")
    assert (await run(fa, measures=["budget_moved"]))["totals"]["budget_moved"] == 0


async def test_budget_flows_dimension_and_measure_mixing_rules(seeded):
    priya = await make_actor(seeded)
    await expect_validation(priya, measures=["budget_moved"], dimension="vendor")
    await expect_validation(priya, measures=["budget_moved"], dimension="category")
    await expect_validation(priya, measures=["budget_moved", "budget_allocated"], dimension="from_category")
    await expect_validation(priya, measures=["budget_allocated"], dimension="from_category")  # flow dims only on the flows source


# ---------------------------------------------------------------- 7. contracts

async def finds(where="true"):
    return [tuple(r) for r in await sql(f"""select c.counterparty_name, c.contract_type, f.risk, f.bearer, f.clause_type, f.state, f.cap_paise
                                           from contracts c left join contract_findings f on f.contract_id=c.id where {where}""")]


RISKY = ("high", "medium", "low")
LIVE = ("proposed", "accepted", "modified")


async def test_contract_totals_match_direct_queries(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["liability_count", "contract_count"], dimension="counterparty")
    allf = await finds()
    want_l: dict = {}
    for cp, _t, risk, _b, _c, st, _cap in allf:
        want_l.setdefault(cp, 0)
        if risk in RISKY and st in LIVE:
            want_l[cp] += 1
    got = {r["key"]: r["values"]["liability_count"] for r in out["rows"]}
    assert got == want_l
    assert {r["values"]["contract_count"] for r in out["rows"]} == {1}
    assert out["totals"]["liability_count"] == sum(want_l.values()) > 0
    assert (await run(priya, measures=["contract_count"]))["totals"]["contract_count"] == 4


async def test_capped_liability_total_and_by_counterparty(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["capped_liability_amount"])
    assert out["totals"]["capped_liability_amount"] == 120_000_000
    by = await run(priya, measures=["capped_liability_amount"], dimension="counterparty")
    got = {r["key"]: r["values"]["capped_liability_amount"] for r in by["rows"]}
    assert got["Lotus Hospitality Private Limited"] == 100_000_000 and got["Shree Ganesh Printers"] == 20_000_000
    assert sum(got.values()) == 120_000_000
    (direct,) = await sql("select sum(cap_paise) from contract_findings where clause_type='limitation_of_liability' and state<>'rejected'")
    assert int(direct[0]) == 120_000_000


async def test_rejected_cap_excluded_and_review_state_changes_liability_count(seeded):
    priya = await make_actor(seeded)
    from sqlalchemy import text
    async with db.session_scope() as s:
        await s.execute(text("update contract_findings set state='rejected' where clause_type='limitation_of_liability' and cap_paise=20000000"))
        await s.execute(text("update contract_findings set state='rejected' where clause_type='unlimited_liability'"))
    assert (await run(priya, measures=["capped_liability_amount"]))["totals"]["capped_liability_amount"] == 100_000_000
    expected = len([f for f in await finds() if f[2] in RISKY and f[5] in LIVE])
    assert (await run(priya, measures=["liability_count"]))["totals"]["liability_count"] == expected


async def test_liability_count_by_bearer_and_risk_and_clause(seeded):
    priya = await make_actor(seeded)
    allf = await finds()
    by_b = await run(priya, measures=["liability_count"], dimension="bearer")
    got = {r["key"]: r["values"]["liability_count"] for r in by_b["rows"]}
    us = len([f for f in allf if f[3] == "us" and f[2] in RISKY and f[5] in LIVE])
    assert got["us"] == us > 0
    by_r = await run(priya, measures=["liability_count"], dimension="risk")
    gr = {r["key"]: r["values"]["liability_count"] for r in by_r["rows"]}
    assert gr["high"] == len([f for f in allf if f[2] == "high" and f[5] in LIVE])
    assert gr.get("standard", 0) == 0
    by_c = await run(priya, measures=["liability_count"], dimension="clause_type")
    labels = {r["key"]: r["values"]["liability_count"] for r in by_c["rows"]}
    assert labels["Unlimited liability"] == 1 and labels["Broad indemnity"] == 3
    assert by_c["totals"]["liability_count"] == by_b["totals"]["liability_count"] == by_r["totals"]["liability_count"]


async def test_contract_count_distinct_across_dimensions(seeded):
    priya = await make_actor(seeded)
    for dim in ("risk", "bearer", "clause_type", "review_state"):
        out = await run(priya, measures=["contract_count"], dimension=dim)
        for r in out["rows"]:  # a contract with 5 findings counts once per group, never once per finding
            (n,) = await sql("select count(*) from contracts")
            assert r["values"]["contract_count"] <= n[0]
    ct = await run(priya, measures=["contract_count"], dimension="contract_type")
    assert {r["key"]: r["values"]["contract_count"] for r in ct["rows"]} == {"NDA": 2, "MSA": 1, "Vendor agreement": 1}
    st = await run(priya, measures=["contract_count"], dimension="status")
    assert {r["key"]: r["values"]["contract_count"] for r in st["rows"]} == {"active": 4}
    rs = await run(priya, measures=["contract_count"], dimension="review_state")
    assert {r["key"] for r in rs["rows"]} == {"tagged", "proposed"}
    (direct,) = await sql("select count(distinct contract_id) from contract_findings where state='proposed'")
    assert {r["key"]: r["values"]["contract_count"] for r in rs["rows"]}["proposed"] == direct[0]


async def test_expiry_month_dimension_handles_missing_expiry(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["contract_count"], dimension="expiry_month")
    assert out["totals"]["contract_count"] == 4
    keyed = {r["key"]: r["values"]["contract_count"] for r in out["rows"] if r["key"]}
    assert keyed["2026-12"] == 1 and keyed["2027-02"] == 1 and keyed["2027-06"] == 1
    assert sum(r["values"]["contract_count"] for r in out["rows"]) == 4  # the contract with no expiry is not dropped


async def test_contract_filters_and_ranges(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["capped_liability_amount"], filters=[{"dimension": "counterparty", "values": ["Lotus"]}])
    assert out["totals"]["capped_liability_amount"] == 100_000_000
    out2 = await run(priya, measures=["contract_count"], date_from=date(2027, 1, 1), date_to=date(2027, 12, 31))
    assert out2["totals"]["contract_count"] == 2  # Lotus (Feb 2027) and Nimbus (Jun 2027)
    out3 = await run(priya, measures=["liability_count"], dimension="counterparty", chart="pie")
    assert out3["meta"]["chart"] == "pie"


async def test_contracts_approver_only(seeded):
    employee = await make_actor(seeded, "arjun")
    hr = await as_role(seeded, "priya", "hr_admin")
    for a in (employee, hr):
        for m in ("liability_count", "capped_liability_amount", "contract_count"):
            with pytest.raises(DomainError) as e:
                await run(a, measures=[m])
            assert e.value.code == FORBIDDEN, (a.role, m)
    for role in ("admin", "finance_approver"):
        a = await as_role(seeded, "priya", role)
        assert (await run(a, measures=["contract_count"]))["totals"]["contract_count"] == 4


async def test_contracts_workspace_scoped(seeded):
    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    me, them = await make_actor(seeded), await make_actor(other, "priya")
    for a in (me, them):
        assert (await run(a, measures=["contract_count"]))["totals"]["contract_count"] == 4
        assert (await run(a, measures=["capped_liability_amount"]))["totals"]["capped_liability_amount"] == 120_000_000
    (n,) = await sql("select count(*) from contracts")
    assert n[0] == 8


async def test_contract_dimensions_rejected_on_other_sources(seeded):
    priya = await make_actor(seeded)
    await expect_validation(priya, measures=["bill_amount"], dimension="counterparty")
    await expect_validation(priya, measures=["contract_count"], dimension="vendor")
    await expect_validation(priya, measures=["contract_count"], dimension="day")
    await expect_validation(priya, measures=["contract_count", "bill_count"])
    await expect_validation(priya, measures=["liability_count", "capped_liability_amount"])  # count and paise


# ---------------------------------------------------------------- 8. apply_patch and options

def test_apply_patch_keeps_and_sets_compare():
    base = spec(measures=["bill_amount"], dimension="vendor", date_from=date(2026, 11, 1), date_to=date(2026, 11, 30), compare="prev_period")
    kept = charts.apply_patch(base, ChartSpecPatch.model_validate({"overdue_only": True}))
    assert kept.compare == "prev_period"
    changed = charts.apply_patch(base, ChartSpecPatch.model_validate({"compare": "yoy"}))
    assert changed.compare == "yoy" and changed.dimension.value == "vendor"
    cleared = charts.apply_patch(base, ChartSpecPatch.model_validate({"compare": "none"}))
    assert cleared.compare == "none"
    plain = spec(measures=["bill_amount"], dimension="bill_month")
    mom = charts.apply_patch(plain, ChartSpecPatch.model_validate({"compare": "mom"}))
    assert mom.compare == "mom"
    again = charts.apply_patch(mom, ChartSpecPatch.model_validate({"top_n": 3}))
    assert again.compare == "mom"


def test_apply_patch_resets_chart_that_no_longer_fits():
    heat = spec(measures=["budget_allocated"], dimension="budget_month", series_by="category", chart="heatmap")
    new = charts.apply_patch(heat, ChartSpecPatch.model_validate({"clear_series_by": True}))
    assert new.chart.value == "auto"
    pie = spec(measures=["bill_amount"], dimension="vendor", chart="pie")
    assert charts.apply_patch(pie, ChartSpecPatch.model_validate({"dimension": "bill_month"})).chart.value == "auto"
    cmp_grouped = spec(measures=["bill_amount"], dimension="vendor", chart="grouped_bar", compare="prev_period")
    assert charts.chart_problem(cmp_grouped) is None


async def test_options_by_role(seeded):
    priya, arjun = await make_actor(seeded), await make_actor(seeded, "arjun")
    admin = {s["source"]: s for s in charts.options(priya)["sources"]}
    assert {"budget_flows", "contracts", "receivables", "payables", "claims", "budget"} <= set(admin)
    emp = {s["source"] for s in charts.options(arjun)["sources"]}
    assert "budget_flows" not in emp and "contracts" not in emp and "claims" in emp
    assert "budget" not in emp  # budget source is finance-only now (round 6)
    import dataclasses
    ceo = {s["source"] for s in charts.options(dataclasses.replace(priya, role="ceo"))["sources"]}
    assert set(admin) <= ceo  # CEO (can_read_finance) sees every source
    assert [m["name"] for m in admin["budget_flows"]["measures"]] == ["budget_moved"]
    assert {m["name"] for m in admin["contracts"]["measures"]} == {"liability_count", "capped_liability_amount", "contract_count"}
    dims = {s: {d["name"] for d in admin[s]["dimensions"]} for s in admin}
    assert {"day", "week", "quarter", "fy"} <= dims["payables"] and {"day", "week", "quarter", "fy"} <= dims["claims"]
    assert {"quarter", "fy"} <= dims["receivables"] and not {"day", "week"} & dims["receivables"]
    assert {"quarter", "fy"} <= dims["budget"] and not {"day", "week"} & dims["budget"]
    assert dims["budget_flows"] == {"from_category", "to_category", "budget_month", "quarter", "fy"}
    assert dims["contracts"] == {"risk", "bearer", "counterparty", "clause_type", "contract_type", "expiry_month", "review_state", "status"}
    unit = {m["name"]: m["unit"] for s in admin.values() for m in s["measures"]}
    assert unit["budget_utilisation_pct"] in ("INR", "count", "percent")


async def test_options_reports_pct_unit_distinctly(seeded):
    """BUG candidate: options() maps every non-paise unit to 'count', so the model is told utilisation is a count."""
    priya = await make_actor(seeded)
    budget_src = {s["source"]: s for s in charts.options(priya)["sources"]}["budget"]
    unit = {m["name"]: m["unit"] for m in budget_src["measures"]}["budget_utilisation_pct"]
    assert unit != "count"


# ---------------------------------------------------------------- 9. injection

EVIL = ["x' OR 1=1 --", "'; DROP TABLE contracts; --", "%", "_", "Acme%' --", "\\", "Lotus'); DELETE FROM budget_movements; --"]


@pytest.mark.parametrize("evil", EVIL)
async def test_injection_on_counterparty_filter(seeded, evil):
    priya = await make_actor(seeded)
    real = {c for (c,) in await sql("select counterparty_name from contracts")}
    try:
        out = await run(priya, measures=["contract_count"], filters=[{"dimension": "counterparty", "values": [evil]}])
    except DomainError as e:
        assert e.code in (VALIDATION, AMBIGUOUS)
    else:  # matched safely: only to a real counterparty, never executed
        assert set(out["meta"]["filters_resolved"][0]["values"]) <= real
    assert (await sql("select count(*) from contracts"))[0][0] == 4


@pytest.mark.parametrize("evil", EVIL)
async def test_injection_on_from_category_filter(seeded, evil):
    ws, priya = seeded["workspace_id"], await make_actor(seeded)
    L = await lines_by_cat()
    await post_move(ws, L["IT & Cloud"], 100_000, "budget_top_up", M, receipt=1)
    real = {"New budget", "IT & Cloud"}
    try:
        out = await run(priya, measures=["budget_moved"], filters=[{"dimension": "from_category", "values": [evil]}])
    except DomainError as e:
        assert e.code in (VALIDATION, AMBIGUOUS)
    else:
        assert set(out["meta"]["filters_resolved"][0]["values"]) <= real
    assert (await sql("select count(*) from budget_movements where kind='budget_top_up'"))[0][0] == 1


async def test_injection_in_pydantic_enum_fields_rejected():
    from pydantic import ValidationError
    for bad in ("counterparty; drop table contracts", "from_category' or '1'='1"):
        with pytest.raises(ValidationError):
            spec(measures=["contract_count"], dimension=bad)
    with pytest.raises(ValidationError):
        spec(measures=["contract_count"], compare="yoy; drop")


# ---------------------------------------------------------------- 10. misc regressions of the new surface

async def test_read_value_works_on_quarter_and_compare_snapshots(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        out = await charts.run_spec(s, priya, spec(measures=["bill_amount"], dimension="quarter"), today=TODAY)
        snap = await charts.store(s, priya, out)
        rv = charts.read_value(snap, "Q3 FY26-27")
    assert rv["label"] == "Q3 FY26-27" and rv["share_of_total_pct"] == 100.0


async def test_summarize_with_simple_namespace_for_pct_no_parts_rows():
    """summarize() must not crash on pct rows that lack 'parts' (e.g. an older snapshot)."""
    snap = SimpleNamespace(id="x", totals={"budget_utilisation_pct": 5000}, rows=[
        {"key": "A", "label": "A", "series": None, "values": {"budget_utilisation_pct": 4000}, "refs": []},
        {"key": "B", "label": "B", "series": None, "values": {"budget_utilisation_pct": 6000}, "refs": []}],
        meta={"measures": [{"name": "budget_utilisation_pct", "label": "Utilisation", "unit": "pct"}], "record_label": "budget lines",
              "title": "t", "chart": "bar", "as_of": "2026-11-21", "filters_applied": [], "scope": "w", "group_count": 2,
              "source_record_count": 0, "dimension": {"kind": "category"}})
    sm = charts.summarize(snap)
    assert sm["insights"][0] == "Highest: B, 60.0%" and "Lowest: A, 40.0%" in sm["insights"]
    assert not any("Largest" in i for i in sm["insights"])
