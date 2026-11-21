"""Dynamic charts: validation, chart-type rules, totals vs independent SQL, revisions, read_value, scoping, wiring."""

from datetime import date

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app import db
from app.errors import AMBIGUOUS, FORBIDDEN, NOT_FOUND, VALIDATION, DomainError
from app.main import app
from app.services import budget, charts
from app.services.charts import ChartSpec, ChartSpecPatch
from seed.seed_v1 import seed
from tests.conftest import make_actor

TODAY = date(2026, 11, 21)
ORIGIN = "http://localhost:8000"


def spec(**kw) -> ChartSpec:
    return ChartSpec.model_validate(kw)


async def run(actor, **kw) -> dict:
    async with db.session_scope() as s:
        return await charts.run_spec(s, actor, spec(**kw), today=TODAY)


async def build(actor, **kw) -> str:
    async with db.session_scope() as s:
        payload = await charts.run_spec(s, actor, spec(**kw), today=TODAY)
        return (await charts.store(s, actor, payload)).id


async def sql(q: str, **params):
    async with db.session_scope() as s:
        return (await s.execute(text(q), params)).all()


async def err(coro_or_actor_kw) -> DomainError:
    with pytest.raises(DomainError) as e:
        await coro_or_actor_kw
    return e.value


async def priya_arjun(ids):
    return await make_actor(ids, "priya"), await make_actor(ids, "arjun")


async def client_for(email, password="purser-demo"):
    c = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN, headers={"origin": ORIGIN})
    r = await c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    c.headers["x-csrf-token"] = r.json()["csrf"]
    return c


# ---------------------------------------------------------------- 1. validation

def test_pydantic_rejects_unknown_measure_and_extra_fields():
    with pytest.raises(ValidationError):
        spec(measures=["budget_allocated", "budget_reserved", "budget_spent", "budget_available"])
    with pytest.raises(ValidationError):
        spec(measures=["profit_margin"])
    with pytest.raises(ValidationError):
        spec(measures=["receivables_outstanding"], sql="DROP TABLE invoices")
    with pytest.raises(ValidationError):
        spec(measures=["receivables_outstanding"], dimension="planet")
    with pytest.raises(ValidationError):
        spec(measures=[])
    with pytest.raises(ValidationError):
        ChartSpecPatch.model_validate({"bogus": 1})


BAD_SPECS = [
    ("mixed sources", dict(measures=["receivables_outstanding", "bill_amount"])),
    ("amount and count", dict(measures=["receivables_outstanding", "invoice_count"], dimension="customer")),
    ("budget by vendor", dict(measures=["budget_allocated"], dimension="vendor")),
    ("series_by without dimension", dict(measures=["receivables_outstanding"], series_by="status")),
    ("series_by equals dimension", dict(measures=["receivables_outstanding"], dimension="customer", series_by="customer")),
    ("series_by with 2 measures", dict(measures=["receivables_outstanding", "invoiced_amount"], dimension="customer", series_by="status")),
    ("overdue_only on budget", dict(measures=["budget_allocated"], dimension="category", overdue_only=True)),
    ("overdue_only on claims", dict(measures=["claims_amount"], dimension="category", overdue_only=True)),
    ("date range on budget", dict(measures=["budget_allocated"], date_from="2026-01-01")),
    ("date_from after date_to", dict(measures=["invoiced_amount"], date_from="2026-11-01", date_to="2026-10-01")),
    ("top_n with time dimension", dict(measures=["invoiced_amount"], dimension="issue_month", top_n=3)),
    ("duplicate measure", dict(measures=["invoiced_amount", "invoiced_amount"], dimension="customer")),
    ("filter dimension not in source", dict(measures=["budget_allocated"], filters=[{"dimension": "vendor", "values": ["x"]}])),
    ("two filters same dimension", dict(measures=["invoiced_amount"], filters=[
        {"dimension": "customer", "values": ["Nimbus"]}, {"dimension": "customer", "values": ["Lotus"]}])),
]


@pytest.mark.parametrize("name,kw", BAD_SPECS, ids=[b[0] for b in BAD_SPECS])
async def test_invalid_specs_are_validation_errors(seeded, name, kw):
    priya = await make_actor(seeded)
    e = await err(run(priya, **kw))
    assert e.code == VALIDATION, (name, e.code, e.message)


# ---------------------------------------------------------------- 2. chart type rules

CHART_PROBLEMS = [
    ("line without dimension", dict(measures=["invoiced_amount"], chart="line")),
    ("line with category dim", dict(measures=["invoiced_amount"], dimension="customer", chart="line")),
    ("area with category dim", dict(measures=["invoiced_amount"], dimension="customer", chart="area")),
    ("kpi with dimension", dict(measures=["invoiced_amount"], dimension="customer", chart="kpi")),
    ("donut two measures", dict(measures=["invoiced_amount", "received_amount"], dimension="customer", chart="donut")),
    ("donut time dim", dict(measures=["invoiced_amount"], dimension="issue_month", chart="donut")),
    ("grouped single series", dict(measures=["invoiced_amount"], dimension="customer", chart="grouped_bar")),
    ("stacked single series", dict(measures=["invoiced_amount"], dimension="customer", chart="stacked_bar")),
    ("bar without dimension", dict(measures=["invoiced_amount"], chart="bar")),
]


@pytest.mark.parametrize("name,kw", CHART_PROBLEMS, ids=[b[0] for b in CHART_PROBLEMS])
async def test_chart_type_rules_reject(seeded, name, kw):
    priya = await make_actor(seeded)
    e = await err(run(priya, **kw))
    assert e.code == VALIDATION, name


async def test_auto_chart_selection(seeded):
    priya = await make_actor(seeded)
    assert (await run(priya, measures=["receivables_outstanding"]))["meta"]["chart"] == "kpi"
    assert (await run(priya, measures=["invoiced_amount"], dimension="issue_month"))["meta"]["chart"] == "line"
    assert (await run(priya, measures=["invoiced_amount", "received_amount"], dimension="customer"))["meta"]["chart"] == "grouped_bar"
    ok = await run(priya, measures=["invoiced_amount", "received_amount"], dimension="customer", chart="stacked_bar")
    assert ok["meta"]["chart"] == "stacked_bar"


# ---------------------------------------------------------------- 3. totals equal source rows

async def test_receivables_totals_and_rows_match_sql(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["receivables_outstanding"], dimension="customer")
    expected = dict(await sql("""
        select p.name, sum(greatest(i.amount_paise - i.paid_paise - i.moved_paise, 0)) from invoices i
        join parties p on p.id = i.customer_party_id
        where i.workspace_id=:w and i.status in ('sent', 'part_paid') and p.archived_at is null
          and i.amount_paise - i.paid_paise - i.moved_paise > 0 group by p.name""", w=seeded["workspace_id"]))
    got = {r["key"]: r["values"]["receivables_outstanding"] for r in out["rows"]}
    assert got == {k: int(v) for k, v in expected.items()}
    assert out["totals"]["receivables_outstanding"] == sum(int(v) for v in expected.values()) == 64_855_000
    # 6 legacy open invoices (54,27,000) + Northwind Oct balance (65,850) + Orbit Aug (40,000); drafts / paid / to_raise excluded
    assert out["meta"]["source_record_count"] == 8


async def test_overdue_total_and_filters_match_sql(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["receivables_outstanding"], dimension="customer", overdue_only=True)
    expected = await sql("""
        select p.name, sum(greatest(i.amount_paise - i.paid_paise - i.moved_paise, 0)) from invoices i
        join parties p on p.id = i.customer_party_id
        where i.workspace_id=:w and i.status in ('sent', 'part_paid') and p.archived_at is null and i.due_date < :t
          and i.amount_paise - i.paid_paise - i.moved_paise > 0 group by p.name""",
                         w=seeded["workspace_id"], t=TODAY)
    assert {r["key"]: r["values"]["receivables_outstanding"] for r in out["rows"]} == {k: int(v) for k, v in expected}
    assert out["totals"]["receivables_outstanding"] == 34_055_000  # 2,34,700 legacy + 65,850 Northwind Oct + 40,000 Orbit Aug
    assert {r["key"] for r in out["rows"]} == {"Acme Traders", "Nimbus Retail", "Lotus Hospitality",
                                               "Northwind Labs (synthetic)", "Orbit Design Studio (synthetic)"}


async def test_date_range_filter_matches_sql(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["invoiced_amount"], date_from=date(2026, 10, 1), date_to=date(2026, 10, 31))
    (exp,) = await sql("select sum(amount_paise) from invoices where workspace_id=:w and issue_date between :a and :b",
                       w=seeded["workspace_id"], a=date(2026, 10, 1), b=date(2026, 10, 31))
    assert out["totals"]["invoiced_amount"] == int(exp[0])


async def test_bills_totals_match_sql(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["bill_amount"], dimension="vendor")
    exp = dict(await sql("""select p.name, sum(b.amount_paise) from bills b join parties p on p.id=b.vendor_party_id
                            where b.workspace_id=:w and b.state <> 'rejected' group by p.name""", w=seeded["workspace_id"]))
    assert {r["key"]: r["values"]["bill_amount"] for r in out["rows"]} == {k: int(v) for k, v in exp.items()}
    assert out["totals"]["bill_amount"] == 11_640_000
    unpaid = await run(priya, measures=["payables_outstanding"])
    (e2,) = await sql("select sum(amount_paise) from bills where workspace_id=:w and settlement_state='unpaid' and state<>'rejected'",
                      w=seeded["workspace_id"])
    assert unpaid["totals"]["payables_outstanding"] == int(e2[0])


async def test_budget_by_category_matches_movements(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["budget_allocated", "budget_spent", "budget_available"], dimension="category")
    exp = await sql("""
        select l.category,
          coalesce(sum(m.amount_paise) filter (where m.bucket='allocation'),0),
          coalesce(sum(m.amount_paise) filter (where m.bucket='reserved'),0),
          coalesce(sum(m.amount_paise) filter (where m.bucket='spent'),0),
          coalesce(sum(m.amount_paise) filter (where m.bucket='committed'),0)
        from budget_movements m join budget_lines l on l.id=m.line_id where m.workspace_id=:w group by l.category""",
                    w=seeded["workspace_id"])
    want = {c: {"budget_allocated": int(a), "budget_spent": int(sp), "budget_available": int(a - r - sp - co)}
            for c, a, r, sp, co in exp}
    assert {r["key"]: r["values"] for r in out["rows"]} == want


async def test_top_n_folds_into_other_keeping_totals_and_refs(seeded):
    priya = await make_actor(seeded)
    full = await run(priya, measures=["receivables_outstanding"], dimension="customer")
    out = await run(priya, measures=["receivables_outstanding"], dimension="customer", top_n=2)
    assert out["totals"] == full["totals"]
    keys = [r["key"] for r in out["rows"]]
    assert keys == ["Patel Agro Exports", "Acme Traders", "Other"]
    other = out["rows"][-1]
    assert other["values"]["receivables_outstanding"] == 8_250_000 + 6_585_000 + 6_000_000 + 4_000_000 + 2_720_000
    full_refs = {x for r in full["rows"] for x in r["refs"]}
    assert {x for r in out["rows"] for x in r["refs"]} == full_refs
    assert set(other["refs"]) == {"INV-2026-118", "INV-2026-097", "INV-2026-104", "INV-2026-0008", "INV-2026-0016"}


async def test_series_fold_over_three_keeps_totals(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["invoiced_amount"], dimension="issue_month", series_by="customer")
    (exp,) = await sql("select sum(amount_paise) from invoices where workspace_id=:w", w=seeded["workspace_id"])
    assert out["totals"]["invoiced_amount"] == int(exp[0])
    series = {r["series"] for r in out["rows"]}
    assert len(series) == 4 and "Other" in series  # 3 kept + Other
    assert out["meta"]["folded"]["series"]["kept"] == 3
    assert {x for r in out["rows"] for x in r["refs"]} == {n for (n,) in await sql("select coalesce(number, ref) from invoices")}


# ---------------------------------------------------------------- 4. revision keeps grouping

async def test_overdue_revision_keeps_dimension_and_lineage(seeded):
    priya = await make_actor(seeded)
    async with db.session_scope() as s:
        p1 = await charts.run_spec(s, priya, spec(measures=["receivables_outstanding"], dimension="customer"), today=TODAY)
        parent = await charts.store(s, priya, p1)
        new = charts.apply_patch(ChartSpec.model_validate(parent.spec), ChartSpecPatch(overdue_only=True))
        assert new.dimension == "customer" and new.overdue_only is True
        child = await charts.store(s, priya, await charts.run_spec(s, priya, new, today=TODAY), parent=parent)
        child2 = await charts.store(s, priya, await charts.run_spec(s, priya, new, today=TODAY), parent=child)
        assert child.parent_id == parent.id
        assert child.meta["lineage"] == parent.id == child2.meta["lineage"]
        assert parent.meta["lineage"] == parent.id
        assert child.totals["receivables_outstanding"] == 34_055_000


def test_add_filters_replaces_and_clear_filters():
    base = spec(measures=["receivables_outstanding"], dimension="customer", overdue_only=True,
                filters=[{"dimension": "customer", "values": ["Acme Traders"]}], date_from="2026-01-01")
    p = ChartSpecPatch.model_validate({"add_filters": [{"dimension": "customer", "values": ["Nimbus Retail"]}]})
    new = charts.apply_patch(base, p)
    assert [(f.dimension.value, f.values) for f in new.filters] == [("customer", ["Nimbus Retail"])]
    cleared = charts.apply_patch(new, ChartSpecPatch(clear_filters=True))
    assert cleared.filters is None and not cleared.overdue_only and cleared.date_from is None
    assert cleared.dimension == "customer"
    removed = charts.apply_patch(base, ChartSpecPatch.model_validate({"remove_filters": ["customer"]}))
    assert removed.filters is None and removed.overdue_only is True


def test_month_to_customer_with_line_falls_back_to_auto():
    base = spec(measures=["invoiced_amount"], dimension="issue_month", chart="line")
    new = charts.apply_patch(base, ChartSpecPatch.model_validate({"dimension": "customer"}))
    assert new.dimension == "customer" and new.chart == "auto"
    # explicit incompatible chart in the same patch is left alone so validation can report it
    kept = charts.apply_patch(base, ChartSpecPatch.model_validate({"dimension": "customer", "chart": "line"}))
    assert kept.chart == "line"


# ---------------------------------------------------------------- 5. read_value from the snapshot

async def test_read_value_uses_filtered_snapshot(seeded):
    priya = await make_actor(seeded)
    unfiltered = await build(priya, measures=["receivables_outstanding"], dimension="customer")
    over = await build(priya, measures=["receivables_outstanding"], dimension="customer", overdue_only=True)
    async with db.session_scope() as s:
        snap = await charts.load(s, priya, unfiltered)
        e = await err_sync(lambda: charts.read_value(snap, "Acme"))
        assert e.code == AMBIGUOUS and set(e.details["candidates"]) == {"Acme Traders", "Acme Tradelinks"}
        snap2 = await charts.load(s, priya, over)
        out = charts.read_value(snap2, "Acme")
        assert out["label"] == "Acme Traders"
        assert out["values"]["outstanding"] == "₹1,25,000"
        assert out["source_records"] == ["INV-2026-101"]
        assert (await err_sync(lambda: charts.read_value(snap2, "Zebra Corp"))).code == NOT_FOUND


async def err_sync(fn) -> DomainError:
    with pytest.raises(DomainError) as e:
        fn()
    return e.value


async def test_read_value_does_not_requery(seeded):
    priya = await make_actor(seeded)
    sid = await build(priya, measures=["receivables_outstanding"], dimension="customer")
    async with db.session_scope() as s:
        await s.execute(text("update invoices set paid_paise = amount_paise where number='INV-2026-101'"))
    async with db.session_scope() as s:
        snap = await charts.load(s, priya, sid)
        out = charts.read_value(snap, "Acme Traders")
    assert out["values"]["outstanding"] == "₹1,63,000"  # snapshot value, not the mutated DB


# ---------------------------------------------------------------- 6. scoping

async def test_employee_forbidden_for_receivables_and_payables(seeded):
    _, arjun = await priya_arjun(seeded)
    for kw in (dict(measures=["receivables_outstanding"]), dict(measures=["bill_amount"], dimension="vendor")):
        assert (await err(run(arjun, **kw))).code == FORBIDDEN


async def test_employee_claims_scoped_to_self(seeded):
    from tests.test_ledger_gates import submit_arjun_hotel_claim
    priya, arjun = await priya_arjun(seeded)
    all_claims = await run(priya, measures=["claims_amount"], dimension="employee")
    assert {r["key"] for r in all_claims["rows"]} == {"Neha Iyer"}
    mine = await run(arjun, measures=["claims_amount"], dimension="employee")
    assert mine["rows"] == [] and mine["meta"]["scope"] == "your own claims only"
    ref = await submit_arjun_hotel_claim(seeded, priya)
    mine = await run(arjun, measures=["claims_amount"], dimension="employee")
    assert {r["key"] for r in mine["rows"]} == {"Arjun Mehta"}
    assert [x for r in mine["rows"] for x in r["refs"]] == [ref]
    boss = await run(priya, measures=["claims_amount"], dimension="employee")
    assert {r["key"] for r in boss["rows"]} == {"Arjun Mehta", "Neha Iyer"}


async def test_snapshot_load_other_actor_and_workspace(seeded):
    priya, arjun = await priya_arjun(seeded)
    sid = await build(priya, measures=["receivables_outstanding"])
    async with db.session_scope() as s:
        assert (await charts.load(s, priya, sid)).id == sid
        with pytest.raises(DomainError) as e:
            await charts.load(s, arjun, sid)
        assert e.value.code == NOT_FOUND
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    other_priya = await make_actor(other, "priya")
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await charts.load(s, other_priya, sid)
        assert e.value.code == NOT_FOUND
        # the other workspace's own chart has other numbers and is not mixed with ours
    out = await run(other_priya, measures=["receivables_outstanding"])
    assert out["totals"]["receivables_outstanding"] == 64_855_000  # same seed data, own workspace rows only
    async with db.session_scope() as s:
        n = (await s.execute(text("select count(*) from invoices"))).scalar_one()
    assert n == 32 and out["meta"]["source_record_count"] == 8  # 16 invoices per workspace


async def test_http_snapshot_access(seeded):
    priya, _ = await priya_arjun(seeded)
    sid = await build(priya, measures=["receivables_outstanding"], dimension="customer")
    owner = await client_for("priya@purser.demo")
    arjun_c = await client_for("arjun@purser.demo")
    try:
        r = await owner.get(f"/api/snapshots/{sid}")
        assert r.status_code == 200
        body = r.json()
        assert body["totals"]["receivables_outstanding"] == {"value": 64_855_000, "display": "₹6,48,550"}
        assert (await arjun_c.get(f"/api/snapshots/{sid}")).status_code == 404
        assert (await owner.get("/api/snapshots/nope")).status_code == 404
    finally:
        await owner.aclose()
        await arjun_c.aclose()


# ---------------------------------------------------------------- 7. filter value resolution

async def test_filter_exact_case_insensitive(seeded):
    priya = await make_actor(seeded)
    out = await run(priya, measures=["receivables_outstanding"], dimension="customer",
                    filters=[{"dimension": "customer", "values": ["acme traders"]}])
    assert [r["key"] for r in out["rows"]] == ["Acme Traders"]
    assert out["totals"]["receivables_outstanding"] == 16_300_000
    assert out["meta"]["filters_resolved"][0]["values"] == ["Acme Traders"]


async def test_filter_ambiguous_unknown_and_exclude(seeded):
    priya = await make_actor(seeded)
    e = await err(run(priya, measures=["receivables_outstanding"], filters=[{"dimension": "customer", "values": ["acme"]}]))
    assert e.code == AMBIGUOUS and e.details["candidates"] == ["Acme Tradelinks", "Acme Traders"]
    e = await err(run(priya, measures=["receivables_outstanding"], filters=[{"dimension": "customer", "values": ["Zeta"]}]))
    assert e.code == VALIDATION and "Nimbus Retail" in e.details["available"]
    ex = await run(priya, measures=["receivables_outstanding"], dimension="customer",
                   filters=[{"dimension": "customer", "values": ["Patel"], "exclude": True}])
    assert "Patel Agro Exports" not in {r["key"] for r in ex["rows"]}
    assert ex["totals"]["receivables_outstanding"] == 64_855_000 - 21_000_000


@pytest.mark.parametrize("evil", ["x' OR 1=1 --", "'; DROP TABLE invoices; --", "%", "_", "Acme%' --", "\\"])
async def test_injection_strings_just_fail_to_match(seeded, evil):
    priya = await make_actor(seeded)
    with pytest.raises(DomainError) as e:
        await run(priya, measures=["receivables_outstanding"], filters=[{"dimension": "customer", "values": [evil]}])
    # normalize_name strips punctuation, so "Acme%' --" reduces to "acme" (ambiguous); still a clean DomainError, no SQL error
    assert e.value.code in (VALIDATION, AMBIGUOUS)
    if evil != "Acme%' --":
        assert e.value.code == VALIDATION
    (n,) = await sql("select count(*) from invoices")
    assert n[0] == 16  # nothing dropped: 6 legacy + 10 revenue-seed invoices


# ---------------------------------------------------------------- 8. budget after the golden path

async def test_budget_available_after_golden_path(seeded):
    from tests.test_ledger_gates import propose_and_confirm, submit_arjun_hotel_claim
    priya = await make_actor(seeded)
    before = await run(priya, measures=["budget_available"], dimension="category",
                       filters=[{"dimension": "category", "values": ["Travel"]}])
    assert before["totals"]["budget_available"] == 4_500_000
    ref = await submit_arjun_hotel_claim(seeded, priya)
    await propose_and_confirm(priya, "approve", {"ref": ref})
    out = await run(priya, measures=["budget_available"], dimension="category",
                    filters=[{"dimension": "category", "values": ["Travel"]}])
    assert out["totals"]["budget_available"] == 4_520_000
    async with db.session_scope() as s:
        pos = await budget.position(s, seeded["workspace_id"], seeded["travel_line_id"])
    assert pos["available_paise"] == out["totals"]["budget_available"]
    summary = None
    async with db.session_scope() as s:
        snap = await charts.store(s, priya, out)
        summary = charts.summarize(snap)
    assert summary["totals"]["available"] == "₹45,200"


# ---------------------------------------------------------------- 9. tool wiring

def test_agent_tools_wired_and_strict_schemas_build():
    from app.agent.purser import ALL_TOOLS
    names = {t.name for t in ALL_TOOLS}
    want = {"describe_chart_options", "build_chart", "revise_chart", "read_chart_value", "present_view"}
    assert want <= names
    for t in ALL_TOOLS:
        if t.name in want:
            assert t.strict_json_schema is True
            sch = t.params_json_schema
            assert sch["type"] == "object" and sch.get("additionalProperties") is False
