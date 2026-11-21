"""Revenue gate 2: FX pricing and month rates, billing cycles, balance transfers, project end, and the propose ->
confirm actions that drive them. Oracles are the worked examples in the owner's CLIENT_REVENUE.md (Billing cycles,
Balance transfers and project closure, Foreign exchange). Business date pinned to 2026-11-21, FX provider is the
offline fixture (no network). Postgres only."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app import db
from app.config import get_settings
from app.errors import FORBIDDEN, VALIDATION, DomainError
from app.models import ClientCycle, FxMonth, FxQuote, Invoice, Party
from app.services import proposals
from app.services.revenue import clients as cl
from app.services.revenue import cycles, fx, fx_months, project_end, suggest
from app.services.revenue import invoices as inv
from app.services.revenue.core import (
    BAD_STATUS,
    MIXED_CURRENCY,
    NOTHING_PENDING,
    RATE_UNAVAILABLE,
    SAME_STATE,
    Rev,
)
from app.services.revenue.money import MICRO, rate_str, share_minor, to_rate_micro, total_paise
from tests.conftest import make_actor

TODAY = date(2026, 11, 21)
R = 100  # paise per rupee
USD_83_40, USD_83_90, USD_84_10 = 83_400_000, 83_900_000, 84_100_000


@pytest.fixture(autouse=True)
def pinned(monkeypatch):
    monkeypatch.setenv("FX_PROVIDER", "fixture")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.records.today_ist", lambda: TODAY)
    for mod in ("app.services.revenue_actions", "app.agent.tools.revenue"):
        monkeypatch.setattr(f"{mod}.today_ist", lambda: TODAY, raising=False)
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


# ---------------------------------------------------------------- helpers


def rv_of(ids, who="priya", today=TODAY) -> Rev:
    return Rev(ids["workspace_id"], ids[f"{who}_id"], today, "ui")


async def run(ids, fn, who="priya", today=TODAY):
    """fn(ss, rv) on a sync session in one committed transaction; return plain data."""
    rv = rv_of(ids, who, today)
    async with db.session_scope() as s:
        return await s.run_sync(lambda ss: fn(ss, rv))


def client_by(ss, name: str) -> Party:
    return ss.scalars(select(Party).where(Party.kind == "customer", Party.name.like(f"{name}%"))).one()


def inv_of(ss, name: str, y: int, m: int, kind: str = "regular") -> Invoice:
    c = client_by(ss, name)
    return ss.scalars(select(Invoice).where(Invoice.customer_party_id == c.id, Invoice.year == y, Invoice.month == m,
                                            Invoice.kind == kind)).one()


def invs_of(ss, name: str) -> list[Invoice]:
    c = client_by(ss, name)
    return list(ss.scalars(select(Invoice).where(Invoice.customer_party_id == c.id).order_by(Invoice.year, Invoice.month, Invoice.id)))


def ym_status(ss, name: str) -> dict:
    return {(i.year, i.month): i.status for i in invs_of(ss, name)}


def code_of(exc) -> str:
    return exc.value.code


async def priya(ids):
    """Approver with no conversation: grounding skipped (the on-screen form path)."""
    return await make_actor(ids, "priya", conversation=False)


async def propose_confirm(actor, kind, args):
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, kind, args)
    async with db.session_scope() as s:
        out = await proposals.confirm(s, actor, p.id, via="button")
    return p, out


async def set_quote(rate_micro=USD_84_10, *, ccy="USD", day=date(2026, 11, 20), age=timedelta(0)):
    """Upsert the cached ECB quote for (ccy, day) with fetched_at = now - age."""
    async with db.session_scope() as s:
        row = (await s.execute(select(FxQuote).where(FxQuote.currency == ccy, FxQuote.rate_date == day))).scalars().first()
        at = datetime.now(UTC) - age
        if row is None:
            s.add(FxQuote(currency=ccy, rate_date=day, rate_micro=rate_micro, fetched_at=at))
        else:
            row.rate_micro, row.fetched_at = rate_micro, at


def mk_client(ss, rv, name="Zed Co", currency="INR"):
    return cl.create_client(ss, rv, name=name, currency=currency)


def mk_invoice(ss, rv, client, minor, month, currency="INR", priced=None, **kw):
    [i] = inv.create_invoices(ss, rv, client=client, months=[month], amount_minor=minor, currency=currency,
                              priced=priced or inv.price(ss, rv, currency, months=[month]), **kw)
    return i


def part_paid_zed(ss, rv, rupees=10_000, got=4_000, month=(2026, 10)):
    """Guide example: Rs 10,000 invoice, Rs 4,000 received, part paid."""
    z = client_by(ss, "Zed") if ss.scalars(select(Party).where(Party.name == "Zed Co")).first() else mk_client(ss, rv)
    i = mk_invoice(ss, rv, z, rupees * R, month)
    inv.set_status(ss, rv, i, "sent", on=date(2026, 10, 2))
    inv.record_payment(ss, rv, i, amount_paise=got * R, received_on=date(2026, 11, 1), settled=False)
    return i


# ================================================================ 1. FX pricing order


async def test_price_inr_is_one(seeded):
    def go(ss, rv):
        p = inv.price(ss, rv, "INR", manual_rate_micro=99_000_000, months=[(2026, 10)])
        return p.rate_micro, p.source, p.rate_date

    assert await run(seeded, go) == (MICRO, "inr", None)


async def test_price_manual_beats_month_and_ecb(seeded):
    def go(ss, rv):
        p = inv.price(ss, rv, "USD", 85_500_000, [(2026, 10)])
        return p.rate_micro, p.source

    assert await run(seeded, go) == (85_500_000, "manual")


async def test_price_month_rate_explicit_beats_ecb(seeded):
    def go(ss, rv):
        a = inv.price(ss, rv, "USD", None, [(2026, 9)])
        b = inv.price(ss, rv, "USD", None, [(2026, 10)])
        return (a.rate_micro, a.source), (b.rate_micro, b.source)

    assert await run(seeded, go) == ((USD_83_40, "month"), (USD_83_90, "month"))


async def test_price_month_rate_carries_forward_and_into_next_fy(seeded):
    def go(ss, rv):
        dec = inv.price(ss, rv, "USD", None, [(2026, 12)])
        next_fy = inv.price(ss, rv, "USD", None, [(2027, 5)])
        return (dec.rate_micro, dec.source), (next_fy.rate_micro, next_fy.source)

    assert await run(seeded, go) == ((USD_83_90, "month"), (USD_83_90, "month"))


async def test_price_month_before_any_rate_falls_back_to_ecb(seeded):
    def go(ss, rv):
        p = inv.price(ss, rv, "USD", None, [(2026, 8)])  # earlier than the first month rate (Sep)
        return p.rate_micro, p.source, p.rate_date

    assert await run(seeded, go) == (USD_84_10, "ecb", date(2026, 11, 20))


async def test_price_ecb_from_cache_when_no_months_given(seeded):
    def go(ss, rv):
        p = inv.price(ss, rv, "USD")
        return p.rate_micro, p.source, p.stale

    assert await run(seeded, go) == (USD_84_10, "ecb", False)


async def test_price_no_cache_raises_rate_unavailable(seeded):
    def go(ss, rv):
        inv.price(ss, rv, "EUR")  # nothing cached for EUR

    with pytest.raises(DomainError) as e:
        await run(seeded, go)
    assert code_of(e) == RATE_UNAVAILABLE


async def test_price_aed_is_manual_only_even_with_a_cached_row(seeded):
    await set_quote(25_000_000, ccy="AED")

    def no_manual(ss, rv):
        inv.price(ss, rv, "AED")

    with pytest.raises(DomainError) as e:
        await run(seeded, no_manual)
    assert code_of(e) == RATE_UNAVAILABLE

    def manual(ss, rv):
        p = inv.price(ss, rv, "AED", 22_900_000)
        return p.rate_micro, p.source

    assert await run(seeded, manual) == (22_900_000, "manual")


async def test_latest_flags_stale_after_a_day(seeded):
    await set_quote(age=timedelta(days=2))

    def go(ss, rv):
        return fx.latest(ss, "USD").stale, inv.price(ss, rv, "USD").stale

    assert await run(seeded, go) == (True, True)


async def test_latest_fresh_quote_not_stale(seeded):
    await set_quote(age=timedelta(hours=23))
    assert await run(seeded, lambda ss, rv: fx.latest(ss, "USD").stale) is False


async def test_fx_cached_returns_micro_or_none(seeded):
    def go(ss, rv):
        return fx.cached(ss, "USD"), fx.cached(ss, "INR"), fx.cached(ss, "EUR")

    assert await run(seeded, go) == (USD_84_10, MICRO, None)


async def test_refresh_fixture_is_noop_within_six_hours(seeded):
    async with db.session_scope() as s:
        out = await fx.refresh(s, {"USD"}, TODAY)
        n = (await s.execute(select(func.count()).select_from(FxQuote).where(FxQuote.currency == "USD"))).scalar_one()
    assert out == {"USD": "cached"} and n == 1


async def test_refresh_fixture_writes_quote_when_missing_or_old(seeded):
    async with db.session_scope() as s:
        out = await fx.refresh(s, {"EUR", "INR", "AED"}, TODAY)  # INR and manual-only AED are skipped
        eur = (await s.execute(select(FxQuote).where(FxQuote.currency == "EUR"))).scalars().one()
        assert (eur.rate_micro, eur.rate_date) == (90_500_000, TODAY)
    assert out == {"EUR": "fresh"}
    await set_quote(age=timedelta(hours=7))  # the USD seed quote is now older than 6 h
    async with db.session_scope() as s:
        out = await fx.refresh(s, ["USD"], TODAY)
        rows = list((await s.execute(select(FxQuote).where(FxQuote.currency == "USD").order_by(FxQuote.rate_date))).scalars())
    assert out == {"USD": "fresh"}
    assert [(r.rate_date, r.rate_micro) for r in rows] == [(date(2026, 11, 20), USD_84_10), (TODAY, USD_84_10)]


async def test_refresh_same_day_updates_instead_of_duplicating(seeded):
    await set_quote(age=timedelta(hours=8))  # age the seed quote past the 6 h window
    await set_quote(age=timedelta(hours=7), day=TODAY, rate_micro=80_000_000)
    async with db.session_scope() as s:
        out = await fx.refresh(s, {"USD"}, TODAY)
        rows = list((await s.execute(select(FxQuote).where(FxQuote.currency == "USD", FxQuote.rate_date == TODAY))).scalars())
    assert out == {"USD": "fresh"} and len(rows) == 1 and rows[0].rate_micro == USD_84_10  # updated in place, not duplicated


async def test_refresh_nothing_to_do_returns_empty(seeded):
    async with db.session_scope() as s:
        assert await fx.refresh(s, {"INR", "AED", "XXX"}, TODAY) == {}


# ================================================================ 2. Month rates


async def test_preview_new_month_lists_unpaid_ticked_and_paid_with_reason(seeded):
    def go(ss, rv):
        p = fx_months.preview(ss, rv, "USD", [(2026, 9)], 85_000_000)
        rows = {(a.invoice.year, a.invoice.month): (a.repriceable, a.ticked, a.reason) for a in p.invoices}
        return rows, p.carried

    rows, carried = await run(seeded, go)
    assert carried == [(2026, m) for m in (10, 11, 12)] + [(2027, m) for m in (1, 2, 3)]
    assert rows[(2026, 9)] == (False, False, "Paid: keeps its rate")
    assert rows[(2026, 10)] == (False, False, "Part paid: keeps its rate")
    for ym in [(2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)]:
        assert rows[ym] == (True, True, "")


async def test_preview_sent_invoice_is_repriceable(seeded):
    def go(ss, rv):
        i = inv_of(ss, "Northwind", 2026, 11)
        inv.set_status(ss, rv, i, "sent", on=TODAY)
        p = fx_months.preview(ss, rv, "USD", [(2026, 11)], 85_000_000)
        a = next(a for a in p.invoices if a.invoice.id == i.id)
        return a.repriceable, a.ticked, a.new_total

    assert await run(seeded, go) == (True, True, 150_000 * 85)  # $1,500 at 85 = Rs 127,500 = 12,750,000 paise


async def test_preview_already_at_rate_not_ticked(seeded):
    def go(ss, rv):
        p = fx_months.preview(ss, rv, "USD", [(2026, 11)], USD_83_90)
        return {(a.invoice.year, a.invoice.month): (a.repriceable, a.ticked, a.reason) for a in p.invoices}

    rows = await run(seeded, go)
    assert rows[(2026, 11)] == (True, False, "Already at this rate")


async def test_preview_manual_rate_follows_unless_unticked(seeded):
    def go(ss, rv):
        i = inv_of(ss, "Northwind", 2026, 11)
        inv.update_invoice(ss, rv, i, priced=inv.Price(86_000_000, "manual", None))
        p = fx_months.preview(ss, rv, "USD", [(2026, 11)], 85_000_000)
        a = next(a for a in p.invoices if a.invoice.id == i.id)
        return a.repriceable, a.ticked, a.reason

    assert await run(seeded, go) == (True, True, "Was typed on the invoice")


async def test_preview_ignores_other_currency_invoices(seeded):
    def go(ss, rv):
        p = fx_months.preview(ss, rv, "USD", [(2026, 10)], 85_000_000)
        return {a.invoice.currency for a in p.invoices}

    assert await run(seeded, go) == {"USD"}  # Kaveri's INR Oct/Jan rows are not listed


async def test_set_month_clears_later_explicit_months_through_march(seeded):
    """Guide: changing a month clears later explicit settings in the affected span through March."""
    def go(ss, rv):
        before = sorted((r.year, r.month) for r in ss.scalars(select(FxMonth)))
        plan, _ = fx_months.apply(ss, rv, "USD", [(2026, 9)], 85_000_000, [])
        ss.expire_all()
        after = {(r.year, r.month): r.rate_micro for r in ss.scalars(select(FxMonth))}
        eff = fx_months.effective(ss, rv, "USD", [(2026, 10), (2027, 3)])
        return before, after, plan.carried, eff

    before, after, carried, eff = await run(seeded, go)
    assert before == [(2026, 9), (2026, 10)]
    assert after == {(2026, 9): 85_000_000}  # Oct's own 83.90 gave way
    assert (2026, 10) in carried and (2027, 3) in carried
    assert eff == {(2026, 10): 85_000_000, (2027, 3): 85_000_000}


async def test_carried_months_runs_to_march_not_beyond(seeded):
    def go(ss, rv):
        return fx_months.carried_months(ss, rv, "USD", [(2027, 1)]), fx_months.carried_months(ss, rv, "USD", [(2027, 3)])

    assert await run(seeded, go) == ([(2027, 2), (2027, 3)], [])


async def test_apply_reprices_ticked_and_leaves_paid_and_part_paid(seeded):
    def go(ss, rv):
        p = fx_months.preview(ss, rv, "USD", [(2026, 11)], 85_000_000)
        ticked = [a.invoice.id for a in p.invoices if a.ticked]
        _plan, repriced = fx_months.apply(ss, rv, "USD", [(2026, 11)], 85_000_000, ticked)
        rows = {(i.year, i.month): (i.fx_rate_micro, i.fx_source, i.total_paise) for i in invs_of(ss, "Northwind")}
        return len(repriced), rows

    n, rows = await run(seeded, go)
    assert n == 5  # Nov-Mar
    for ym in [(2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)]:
        assert rows[ym] == (85_000_000, "month", 150_000 * 85)
    assert rows[(2026, 9)][0] == USD_83_40 and rows[(2026, 10)][0] == USD_83_90


async def test_apply_rejects_reprice_ids_not_in_preview(seeded):
    def paid(ss, rv):
        fx_months.apply(ss, rv, "USD", [(2026, 11)], 85_000_000, [inv_of(ss, "Northwind", 2026, 9).id])

    def part(ss, rv):
        fx_months.apply(ss, rv, "USD", [(2026, 11)], 85_000_000, [inv_of(ss, "Northwind", 2026, 10).id])

    def other_ccy(ss, rv):
        fx_months.apply(ss, rv, "USD", [(2026, 11)], 85_000_000, [inv_of(ss, "Kaveri", 2027, 1).id])

    for fn in (paid, part, other_ccy):
        with pytest.raises(DomainError) as e:
            await run(seeded, fn)
        assert code_of(e) == VALIDATION and e.value.args  # nothing was committed either

    def rates(ss, rv):
        return sorted((r.year, r.month, r.rate_micro) for r in ss.scalars(select(FxMonth)))

    assert await run(seeded, rates) == [(2026, 9, USD_83_40), (2026, 10, USD_83_90)]


async def test_foreign_and_inr_month_inputs_validated(seeded):
    def inr(ss, rv):
        fx_months.preview(ss, rv, "INR", [(2026, 11)], 85_000_000)

    def unknown(ss, rv):
        fx_months.preview(ss, rv, "ZZZ", [(2026, 11)], 85_000_000)

    for fn in (inr, unknown):
        with pytest.raises(DomainError) as e:
            await run(seeded, fn)
        assert code_of(e) == VALIDATION
    assert fx_months.parse_months(["2026-11", "2026-10", "2026-11"]) == [(2026, 10), (2026, 11)]
    for bad in (["2026-13"], ["Nov 2026"], []):
        with pytest.raises(DomainError):
            fx_months.parse_months(bad)


async def test_rev_fx_month_executes_and_reprices(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85"})
    assert out.status == "executed"

    def go(ss, rv):
        return {ym: (i.fx_rate_micro, i.fx_source) for ym, i in ((k, inv_of(ss, "Northwind", *k)) for k in [(2026, 10), (2026, 11), (2027, 3)])}

    got = await run(seeded, go)
    assert got[(2026, 10)] == (USD_83_90, "month") and got[(2026, 11)] == (85_000_000, "month") and got[(2027, 3)] == (85_000_000, "month")


async def test_rev_fx_month_keep_leaves_invoice_at_old_rate(seeded):
    p = await priya(seeded)
    keep_ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 12).ref)
    _, out = await propose_confirm(p, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85", "keep": [keep_ref]})
    assert out.status == "executed"

    def go(ss, rv):
        return inv_of(ss, "Northwind", 2026, 12).fx_rate_micro, inv_of(ss, "Northwind", 2027, 1).fx_rate_micro

    assert await run(seeded, go) == (USD_83_90, 85_000_000)


async def test_rev_fx_month_requires_months_and_valid_rate(seeded):
    p = await priya(seeded)
    for args in ({"currency": "USD", "months": [], "rate": "85"}, {"currency": "USD", "months": ["2026-11"], "rate": "abc"},
                 {"currency": "INR", "months": ["2026-11"], "rate": "85"}):
        async with db.session_scope() as s:
            with pytest.raises(DomainError) as e:
                await proposals.create(s, p, "rev_fx_month", args)
        assert e.value.code == VALIDATION


async def test_rate_only_edit_of_foreign_invoice_becomes_month_rate_and_reprices_unpaid(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 11).ref)
    _, out = await propose_confirm(p, "rev_edit_invoice", {"ref": ref, "rate": "86"})
    assert out.status == "executed"

    def go(ss, rv):
        months = {(r.year, r.month): r.rate_micro for r in ss.scalars(select(FxMonth))}
        rows = {(i.year, i.month): (i.fx_rate_micro, i.fx_source, i.status) for i in invs_of(ss, "Northwind")}
        return months, rows

    months, rows = await run(seeded, go)
    assert months[(2026, 11)] == 86_000_000
    for ym in [(2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)]:
        assert rows[ym] == (86_000_000, "month", "to_raise")
    assert rows[(2026, 10)][:2] == (USD_83_90, "month")  # Oct is before the month: untouched


async def test_amount_edit_with_rate_is_a_manual_rate_not_month_rate(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 11).ref)
    _, out = await propose_confirm(p, "rev_edit_invoice", {"ref": ref, "amount": "1600", "rate": "86"})
    assert out.status == "executed"

    def go(ss, rv):
        i = inv_of(ss, "Northwind", 2026, 11)
        dec = inv_of(ss, "Northwind", 2026, 12)
        return (i.fx_source, i.fx_rate_micro, i.amount_minor), dec.fx_rate_micro, sorted(r.month for r in ss.scalars(select(FxMonth)))

    assert await run(seeded, go) == (("manual", 86_000_000, 160_000), USD_83_90, [9, 10])


async def test_history_lists_month_and_invoice_changes_newest_first(seeded):
    await run(seeded, lambda ss, rv: fx_months.apply(ss, rv, "USD", [(2026, 11)], 85_000_000, [], actor_name="Priya"))
    await run(seeded, lambda ss, rv: fx_months.apply(ss, rv, "USD", [(2026, 12)], 86_000_000, [], actor_name="Priya"))

    def one_invoice(ss, rv):
        i = inv_of(ss, "Northwind", 2027, 2)
        inv.update_invoice(ss, rv, i, priced=inv.Price(87_000_000, "manual", None))

    await run(seeded, one_invoice)

    def go(ss, rv):
        changes, nxt = fx_months.history(ss, rv)
        return [(c.kind, c.currency, c.new, c.old, c.by) for c in changes], nxt

    rows, nxt = await run(seeded, go)
    assert nxt is None
    assert rows[0] == ("invoice", "USD", "87.0000", "83.9000", "Priya")  # the name is borrowed from the actor's month-set rows
    assert rows[1][:3] == ("month", "USD", "86.0000") and rows[1][4] == "Priya"
    assert rows[2][:3] == ("month", "USD", "85.0000")
    assert rows[3][:3] == ("month", "USD", "83.9000")  # seeded Oct and Sep follow, newest first
    assert rows[4][:3] == ("month", "USD", "83.4000")


async def test_history_filters_currency_fy_invoice_and_pages(seeded):
    await run(seeded, lambda ss, rv: fx_months.apply(ss, rv, "USD", [(2026, 11)], 85_000_000, []))
    await run(seeded, lambda ss, rv: fx_months.apply(ss, rv, "USD", [(2027, 5)], 88_000_000, []))  # FY 2027-28

    def go(ss, rv):
        eur, _ = fx_months.history(ss, rv, currency="EUR")
        fy27, _ = fx_months.history(ss, rv, fy="2027-28")
        fy26, _ = fx_months.history(ss, rv, fy="2026-27")
        page1, nxt = fx_months.history(ss, rv, limit=2)
        page2, nxt2 = fx_months.history(ss, rv, after=nxt, limit=2)
        i = inv_of(ss, "Northwind", 2026, 12)
        inv.update_invoice(ss, rv, i, priced=inv.Price(89_000_000, "manual", None))
        mine, _ = fx_months.history(ss, rv, invoice_id=i.id)
        return (len(eur), [c.new for c in fy27], [c.new for c in fy26], [c.new for c in page1], [c.new for c in page2], nxt is not None,
                [c.new for c in mine])

    eur, fy27, fy26, p1, p2, has_next, mine = await run(seeded, go)
    assert eur == 0
    assert fy27 == ["88.0000"]
    assert fy26 == ["85.0000", "83.9000", "83.4000"]
    assert p1 == ["88.0000", "85.0000"] and p2 == ["83.9000", "83.4000"] and has_next
    assert mine == ["89.0000"]


async def test_fx_grid_marks_carried_months(seeded):
    def go(ss, rv):
        g = fx_months.grid(ss, rv, "2026-27")
        usd = next(r for r in g["rows"] if r["currency"] == "USD")
        return {c["key"]: (c["rate"], c["carried"]) for c in usd["cells"]}

    cells = await run(seeded, go)
    assert cells["2026-09"] == ("83.4000", None) and cells["2026-10"] == ("83.9000", None)
    assert cells["2026-12"] == (None, "83.9000") and cells["2026-08"] == (None, None)


# ================================================================ 3. Send reprices only ECB-estimated drafts


def _aug_ecb(ss, rv):
    c = mk_client(ss, rv, "Ecb Co", "USD")
    i = mk_invoice(ss, rv, c, 100_000, (2026, 8), "USD")  # before any month rate: priced from ECB
    return c.id, i.id


async def test_send_reprices_ecb_draft_from_fresh_quote(seeded):
    _cid, iid = await run(seeded, _aug_ecb)
    await set_quote(85_000_000, day=TODAY)

    def go(ss, rv):
        i = ss.get(Invoice, iid)
        before = (i.fx_source, i.fx_rate_micro)
        inv.set_status(ss, rv, i, "sent", on=TODAY)
        return before, (i.fx_source, i.fx_rate_micro, i.fx_date, i.total_paise)

    before, after = await run(seeded, go)
    assert before == ("ecb", USD_84_10)
    assert after == ("ecb", 85_000_000, TODAY, 100_000 * 85)


async def test_send_does_not_reprice_ecb_draft_when_quote_is_stale(seeded):
    _cid, iid = await run(seeded, _aug_ecb)
    await set_quote(USD_84_10, age=timedelta(days=3))
    await set_quote(90_000_000, day=date(2026, 11, 19), age=timedelta(days=3))  # older date, ignored; newest date is 11-20

    def go(ss, rv):
        i = ss.get(Invoice, iid)
        inv.set_status(ss, rv, i, "sent", on=TODAY)
        return i.fx_rate_micro

    assert await run(seeded, go) == USD_84_10


async def test_send_does_not_reprice_manual_or_month_priced(seeded):
    await set_quote(95_000_000, day=TODAY)

    def go(ss, rv):
        month_priced = inv_of(ss, "Northwind", 2026, 11)
        c = client_by(ss, "Northwind")
        manual = mk_invoice(ss, rv, c, 50_000, (2026, 8), "USD", priced=inv.price(ss, rv, "USD", 85_000_000))
        inv.set_status(ss, rv, month_priced, "sent", on=TODAY)
        inv.set_status(ss, rv, manual, "sent", on=TODAY)
        return (month_priced.fx_source, month_priced.fx_rate_micro), (manual.fx_source, manual.fx_rate_micro)

    assert await run(seeded, go) == (("month", USD_83_90), ("manual", 85_000_000))


async def test_send_due_date_is_period_end_never_before_send_day(seeded):
    def go(ss, rv):
        k = inv_of(ss, "Kaveri", 2027, 1)  # Jan-Mar period
        inv.set_status(ss, rv, k, "sent", on=date(2027, 1, 2))
        late = inv_of(ss, "Northwind", 2026, 11)
        inv.set_status(ss, rv, late, "sent", on=date(2026, 12, 15))  # after the Nov period end
        return k.due_on, late.due_on, k.number is not None

    assert await run(seeded, go) == (date(2027, 3, 31), date(2026, 12, 15), True)


# ================================================================ 4. Cycles


def _cycle_client(ss, rv, **kw):
    c = mk_client(ss, rv, "Cyc Co")
    base = dict(from_year=2026, from_month=10, monthly_minor=10_000 * R, currency="INR", period_months=3, timing="advance", mode="combined")
    ci = cycles.CycleIn(**{**base, **kw})
    plan, _row = cycles.apply(ss, rv, c, ci)
    return c, plan


async def test_guide_quarterly_advance_combined_books_30000_in_october_due_31_dec(seeded):
    def go(ss, rv):
        _c, plan = _cycle_client(ss, rv)
        octo = inv_of(ss, "Cyc", 2026, 10)
        return ([(p.year, p.month, p.amount_minor) for p in plan.create], octo.amount_minor, octo.status, cycles.due_on(octo),
                cycles.raise_on(octo), cycles.covers(octo), cycles.period_text(octo), cycles.combined(octo), octo.kind, octo.currency)

    plan, amount, status, due, raise_on, covers, text, combined, kind, ccy = await run(seeded, go)
    assert plan == [(2026, 10, 30_000 * R), (2027, 1, 30_000 * R)]
    assert (amount, status, due, raise_on) == (30_000 * R, "to_raise", date(2026, 12, 31), date(2026, 10, 1))
    assert covers == [(2026, 10), (2026, 11), (2026, 12)] and text == "Oct'26 to Dec'26"
    assert combined is True and kind == "regular" and ccy == "INR"


async def test_guide_arrears_books_in_december_and_raises_at_period_end(seeded):
    def go(ss, rv):
        _c, plan = _cycle_client(ss, rv, timing="arrears")
        dec = inv_of(ss, "Cyc", 2026, 12)
        return [(p.year, p.month) for p in plan.create], cycles.raise_on(dec), cycles.due_on(dec), cycles.period_end(dec)

    created, raise_on, due, end = await run(seeded, go)
    assert created == [(2026, 12), (2027, 3)]
    assert raise_on == date(2026, 12, 31) and due == date(2026, 12, 31) and end == (2026, 12)


async def test_guide_monthly_mode_emits_three_rows_sharing_the_period(seeded):
    def go(ss, rv):
        _c, plan = _cycle_client(ss, rv, mode="monthly")
        rows = [inv_of(ss, "Cyc", 2026, m) for m in (10, 11, 12)]
        grp = cycles.period_group(ss, rows[1])
        return ([(p.year, p.month, p.amount_minor) for p in plan.create[:3]], [(r.period_from, r.period_months) for r in rows],
                [cycles.due_on(r) for r in rows], [cycles.raise_on(r) for r in rows], [g.month for g in grp], len(plan.create))

    created, periods, dues, raises, grp, n = await run(seeded, go)
    assert created == [(2026, 10, 10_000 * R), (2026, 11, 10_000 * R), (2026, 12, 10_000 * R)]
    assert periods == [(202610, 3)] * 3 and dues == [date(2026, 12, 31)] * 3 and raises == [date(2026, 10, 1)] * 3
    assert grp == [10, 11, 12] and n == 6  # a second period Jan-Mar


async def test_schedule_periods_are_anchored_to_the_cycle_start(seeded):
    c = cycles.CycleIn(2026, 10, 1_000 * R, "INR", 3, "advance", "combined")
    got = cycles.schedule(c, (2026, 11), (2027, 3))  # Nov falls inside the Oct period: next starts Jan
    assert [(p.year, p.month, p.period_from, p.period_months) for p in got] == [(2027, 1, 202701, 3)]
    assert cycles.schedule(c, (2026, 4), (2026, 9)) == []  # nothing before the cycle begins
    # the planning horizon selects period starts: the last period may run past March
    wide = cycles.schedule(cycles.CycleIn(2027, 2, 1_000 * R, "INR", 3), (2027, 2), (2027, 3))
    assert [(p.year, p.month, p.months[-1]) for p in wide] == [(2027, 2, (2027, 4))]


async def test_schedule_yearly_and_odd_periods(seeded):
    yearly = cycles.schedule(cycles.CycleIn(2026, 4, 1_000 * R, "INR", 12), (2026, 4), (2027, 3))
    assert [(p.year, p.month, p.amount_minor) for p in yearly] == [(2026, 4, 12_000 * R)]
    arrears = cycles.schedule(cycles.CycleIn(2026, 4, 1_000 * R, "INR", 12, "arrears"), (2026, 4), (2027, 3))
    assert [(p.year, p.month) for p in arrears] == [(2027, 3)]


async def test_cycle_check_rejects_bad_input(seeded):
    ok = dict(from_year=2026, from_month=10, monthly_minor=100, currency="INR")
    for bad in (dict(period_months=0), dict(period_months=13), dict(timing="whenever"), dict(mode="weekly"), dict(monthly_minor=0),
                dict(currency="EUR"), dict(from_month=13), dict(from_year=1999)):
        with pytest.raises(DomainError) as e:
            cycles.check(cycles.CycleIn(**{**ok, **bad}))
        assert e.value.code == VALIDATION


async def test_change_cycle_midyear_removes_only_to_raise_from_the_change_month(seeded):
    def go(ss, rv):
        c = client_by(ss, "Northwind")
        plan, _row = cycles.apply(ss, rv, c, cycles.CycleIn(2026, 12, 200_000, "USD", 1, "advance", "monthly"))
        rows = {(i.year, i.month): (i.amount_minor, i.status, i.fx_rate_micro) for i in invs_of(ss, "Northwind")}
        return [p.label for p in plan.create], len(plan.remove), rows, len(cycles.cycles(ss, c.id))

    created, removed, rows, ncycles = await run(seeded, go)
    assert created == ["Dec'26", "Jan'27", "Feb'27", "Mar'27"] and removed == 4
    assert rows[(2026, 9)][1] == "paid" and rows[(2026, 10)][1] == "part_paid"
    assert rows[(2026, 11)] == (150_000, "to_raise", USD_83_90)  # before the change month: untouched
    for ym in [(2026, 12), (2027, 1), (2027, 2), (2027, 3)]:
        assert rows[ym] == (200_000, "to_raise", USD_83_90)  # rebuilt, priced at the carried month rate
    assert ncycles == 2  # the Sep rule stays; the new one starts Dec


async def test_change_cycle_keeps_raised_and_paid_and_skips_their_months(seeded):
    def go(ss, rv):
        c = client_by(ss, "Northwind")
        oct_before = inv_of(ss, "Northwind", 2026, 10)
        v_before, paid_before = oct_before.version, oct_before.paid_paise
        plan = cycles.preview(ss, c, cycles.CycleIn(2026, 10, 175_000, "USD", 1, "advance", "monthly"))
        out = ([i.ref for i in plan.keep], [p.label for p in plan.skipped], [p.label for p in plan.create], len(plan.remove))
        cycles.apply(ss, rv, c, cycles.CycleIn(2026, 10, 175_000, "USD", 1, "advance", "monthly"))
        ss.expire_all()
        octo = inv_of(ss, "Northwind", 2026, 10)
        return out, (octo.amount_minor, octo.status, octo.paid_paise == paid_before, octo.version == v_before), inv_of(ss, "Northwind", 2026, 11).amount_minor

    (keep, skipped, create, removed), octo, nov_amount = await run(seeded, go)
    assert len(keep) == 1 and skipped == ["Oct'26"] and create == ["Nov'26", "Dec'26", "Jan'27", "Feb'27", "Mar'27"] and removed == 5
    assert octo == (150_000, "part_paid", True, True)
    assert nov_amount == 175_000


async def test_change_cycle_skips_months_covered_by_a_kept_combined_invoice(seeded):
    """Kaveri's paid Oct invoice covers Oct-Dec: a monthly cycle from Nov must not double-bill Nov and Dec."""
    def go(ss, rv):
        c = client_by(ss, "Kaveri")
        plan, _ = cycles.apply(ss, rv, c, cycles.CycleIn(2026, 11, 25_000 * R, "INR", 1, "advance", "monthly"))
        return [p.label for p in plan.skipped], [p.label for p in plan.create], ym_status(ss, "Kaveri")

    skipped, created, status = await run(seeded, go)
    assert skipped == ["Nov'26", "Dec'26"] and created == ["Jan'27", "Feb'27", "Mar'27"]
    assert status[(2026, 10)] == "paid" and (2026, 11) not in status and (2026, 12) not in status


async def test_change_cycle_replaces_later_rules_and_updates_client_currency(seeded):
    def go(ss, rv):
        c = client_by(ss, "Northwind")
        cycles.apply(ss, rv, c, cycles.CycleIn(2026, 12, 200_000, "USD", 1))
        plan, _ = cycles.apply(ss, rv, c, cycles.CycleIn(2026, 12, 25_000 * R, "INR", 1))
        rows = [(r.from_year, r.from_month, r.currency, r.monthly_minor) for r in cycles.cycles(ss, c.id)]
        dec = inv_of(ss, "Northwind", 2026, 12)
        return len(plan.replaces), rows, c.currency, (dec.currency, dec.fx_source, dec.fx_rate_micro, dec.total_paise)

    replaced, rows, ccy, dec = await run(seeded, go)
    assert replaced == 1
    assert rows == [(2026, 9, "USD", 150_000), (2026, 12, "INR", 25_000 * R)]
    assert ccy == "INR" and dec == ("INR", "inr", MICRO, 25_000 * R)


async def test_cycle_active_and_current_rules(seeded):
    def go(ss, rv):
        c = client_by(ss, "Northwind")
        cycles.apply(ss, rv, c, cycles.CycleIn(2027, 1, 200_000, "USD", 1))
        a = cycles.active(ss, c.id, 2026, 12), cycles.active(ss, c.id, 2027, 1), cycles.active(ss, c.id, 2026, 8)
        cur = cycles.current(ss, c.id, TODAY)
        return [x.monthly_minor if x else None for x in a], cur.monthly_minor

    assert await run(seeded, go) == ([150_000, 200_000, None], 150_000)


async def test_plan_fy_fills_missing_months_only_and_is_idempotent(seeded):
    def go(ss, rv):
        c = client_by(ss, "Northwind")
        assert cycles.plan_fy(ss, rv, c, "2026-27") == []  # already fully planned from Sep
        inv.delete_invoice(ss, rv, inv_of(ss, "Northwind", 2026, 12))
        first = cycles.plan_fy(ss, rv, c, "2026-27")
        second = cycles.plan_fy(ss, rv, c, "2026-27")
        return [(i.year, i.month, i.amount_minor, i.fx_source) for i in first], second

    first, second = await run(seeded, go)
    assert first == [(2026, 12, 150_000, "month")] and second == []


async def test_plan_fy_next_year_continues_the_cycle_priced_at_the_carried_rate(seeded):
    def go(ss, rv):
        c = client_by(ss, "Northwind")
        k = client_by(ss, "Kaveri")
        nw = cycles.plan_fy(ss, rv, c, "2027-28")
        kv = cycles.plan_fy(ss, rv, k, "2027-28")
        again = cycles.plan_fy(ss, rv, c, "2027-28") + cycles.plan_fy(ss, rv, k, "2027-28")
        return ([(i.year, i.month, i.fx_rate_micro, i.fx_source) for i in nw], [(i.year, i.month, i.amount_minor) for i in kv], again)

    nw, kv, again = await run(seeded, go)
    assert len(nw) == 12 and nw[0] == (2027, 4, USD_83_90, "month") and nw[-1][:2] == (2028, 3)
    assert kv == [(2027, 4, 75_000 * R), (2027, 7, 75_000 * R), (2027, 10, 75_000 * R), (2028, 1, 75_000 * R)]  # periods anchored on Oct
    assert again == []


async def test_plan_fy_before_cycle_starts_creates_nothing(seeded):
    assert await run(seeded, lambda ss, rv: cycles.plan_fy(ss, rv, client_by(ss, "Northwind"), "2025-26")) == []


async def test_plan_fy_splits_at_the_next_rule(seeded):
    def go(ss, rv):
        c = client_by(ss, "Northwind")
        cycles.apply(ss, rv, c, cycles.CycleIn(2027, 7, 300_000, "USD", 1))  # from Jul 2027: $3,000 a month
        made = cycles.plan_fy(ss, rv, c, "2027-28")
        return made and [(i.year, i.month, i.amount_minor) for i in made]

    got = await run(seeded, go)
    # apply() already planned Jul 2027 to Mar 2028 at the new rate; plan_fy fills Apr-Jun 2027 from the old rule
    assert got == [(2027, 4, 150_000), (2027, 5, 150_000), (2027, 6, 150_000)]


async def test_needs_plan(seeded):
    def go(ss, rv):
        nw, kv, orbit = client_by(ss, "Northwind"), client_by(ss, "Kaveri"), client_by(ss, "Orbit")
        return (cycles.needs_plan(ss, nw, "2026-27"), cycles.needs_plan(ss, nw, "2027-28"), cycles.needs_plan(ss, kv, "2027-28"),
                cycles.needs_plan(ss, kv, "2025-26"), cycles.needs_plan(ss, orbit, "2027-28"))

    assert await run(seeded, go) == (False, True, True, False, False)


async def test_plan_suggestion_only_for_current_fy_until_february(seeded):
    def go(ss, rv):
        return sorted(s.id for s in suggest.build(ss, rv) if s.kind == "plan")

    assert await run(seeded, go) == []  # November: this FY is planned, next FY is not yet offered
    feb = await run(seeded, go, today=date(2027, 2, 10))
    mar = await run(seeded, go, today=date(2027, 3, 5))
    assert len(feb) == 2 and all(i.endswith("-2027-28") for i in feb)  # Northwind and Kaveri
    assert feb == mar


async def test_plan_suggestion_current_fy_when_nothing_planned(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv, "Late Co")
        # a cycle that began in an earlier FY and left this FY unplanned: apply plans only to the FY end, so delete this FY's rows
        cycles.apply(ss, rv, c, cycles.CycleIn(2026, 3, 1_000 * R, "INR", 1))
        for i in invs_of(ss, "Late"):
            if (i.year, i.month) >= (2026, 4):
                inv.delete_invoice(ss, rv, i)
        sug = [s for s in suggest.build(ss, rv) if s.kind == "plan" and "Late" in s.title]
        return [(s.id.endswith("2026-27"), s.act, s.ref) for s in sug]

    assert await run(seeded, go) == [(True, "plan_fy", "Late Co|2026-27")]


async def test_paused_and_ended_clients_get_no_billing_suggestions(seeded):
    def kinds(ss, rv, name):
        return sorted({s.kind for s in suggest.build(ss, rv) if name in s.title or name in s.detail})

    # Orbit (paused) has a sent Aug invoice, long overdue: no chase while paused, chase after resuming
    assert await run(seeded, lambda ss, rv: kinds(ss, rv, "Orbit")) == []

    def resume(ss, rv):
        cl.set_client_state(ss, rv, client_by(ss, "Orbit"), "active", on=TODAY)
        return kinds(ss, rv, "Orbit")

    assert await run(seeded, resume) == ["chase"]

    # Northwind: the Nov draft is due to raise; once the project is ended nothing is suggested
    def nw_before(ss, rv):
        return [s.kind for s in suggest.build(ss, rv) if "Northwind" in s.title or "Northwind" in s.detail]

    assert "raise" in await run(seeded, nw_before)

    def end(ss, rv):
        project_end.apply(ss, rv, client_by(ss, "Northwind"), on=TODAY, pending="none")
        return nw_before(ss, rv)

    assert await run(seeded, end) == []


async def test_rate_moved_suggestion_skips_month_priced_invoices(seeded):
    _cid, iid = await run(seeded, _aug_ecb)
    await set_quote(90_000_000, day=TODAY)  # +7% against the 84.10 the Aug draft was priced at

    def go(ss, rv):
        sug = [s for s in suggest.build(ss, rv) if s.kind == "rate"]
        return [(s.ref, s.act) for s in sug]

    got = await run(seeded, go)
    assert got == [(f"S{iid}", "refresh_rate")]  # Northwind's month-priced drafts are never nagged


async def test_rate_moved_suggestion_needs_more_than_two_percent(seeded):
    await run(seeded, _aug_ecb)
    await set_quote(85_000_000, day=TODAY)  # +1.07%
    assert await run(seeded, lambda ss, rv: [s for s in suggest.build(ss, rv) if s.kind == "rate"]) == []


# ================================================================ 5. Balance transfer


async def test_guide_balance_moves_6000_to_november_draft(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        target = inv.move_balance(ss, rv, src, to="month", year=2026, month=11)
        ss.expire_all()
        return (src.moved_paise, src.status, inv.billed_paise(src), inv.received_paise(src), inv.fx_gain_paise(src), src.moved_to_id == target.id,
                inv.outstanding_paise(src), (target.kind, target.year, target.month, target.total_paise, target.status, target.notes),
                inv.billed_paise(target), inv.remaining_paise(target))

    out = await run(seeded, go)
    assert out[:7] == (600_000, "paid", 400_000, 400_000, 0, True, 0)
    assert out[7] == ("balance", 2026, 11, 600_000, "to_raise", "Balance of Oct'26")
    assert out[8:] == (600_000, 600_000)


async def test_balance_onto_existing_to_raise_month_adds_at_its_rate(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        nov = mk_invoice(ss, rv, client_by(ss, "Zed"), 10_000 * R, (2026, 11))
        n_before = len(invs_of(ss, "Zed"))
        target = inv.move_balance(ss, rv, src, to="month", year=2026, month=11)
        return target.id == nov.id, len(invs_of(ss, "Zed")) == n_before, nov.amount_minor, nov.total_paise, nov.status, nov.notes, src.moved_to_id == nov.id

    same, no_new, amount, total, status, notes, linked = await run(seeded, go)
    assert same and no_new and linked
    assert (amount, total, status) == (16_000 * R, 16_000 * R, "to_raise")
    assert notes == "+ Balance of Oct'26"


async def test_balance_foreign_uses_proportional_share_half_up_at_destination_rate(seeded):
    """Northwind Oct: $1,500 at 83.90 = Rs 125,850; Rs 60,000 in; Rs 65,850 left = $784.86 (78,486.29 cents, half up)."""
    p = await priya(seeded)
    oct_ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 10).ref)
    _, out = await propose_confirm(p, "rev_move_balance", {"ref": oct_ref, "month": "2026-11"})
    assert out.status == "executed"

    expected_minor = int((Decimal(150_000) * 6_585_000 / Decimal(12_585_000)).quantize(Decimal(1), rounding="ROUND_HALF_UP"))
    assert expected_minor == 78_486

    def go(ss, rv):
        octo, nov = inv_of(ss, "Northwind", 2026, 10), inv_of(ss, "Northwind", 2026, 11)
        return (octo.status, octo.moved_paise, octo.moved_to_id == nov.id, inv.billed_paise(octo), nov.amount_minor, nov.fx_rate_micro,
                nov.fx_source, nov.total_paise)

    status, moved, linked, billed, amount, rate, source, total = await run(seeded, go)
    assert (status, moved, linked, billed) == ("paid", 6_585_000, True, 6_000_000)
    assert amount == 150_000 + expected_minor and (rate, source) == (USD_83_90, "month")  # added at the destination's own rate
    assert total == total_paise(150_000 + expected_minor, "USD", USD_83_90)


async def test_share_minor_and_total_paise_round_half_up(seeded):
    assert share_minor(1, 1, 2) == 1 and share_minor(3, 1, 2) == 2 and share_minor(100, 1, 3) == 33 and share_minor(100, 2, 3) == 67
    assert share_minor(150_000, 6_585_000, 12_585_000) == 78_486
    assert share_minor(100, 50, 0) == 0 and share_minor(100, 50, -1) == 0
    assert total_paise(1, "USD", 84_500_000) == 85  # 84.5 paise rounds half up
    assert total_paise(1, "USD", 84_499_999) == 84
    assert total_paise(150_000, "USD", USD_83_90) == 12_585_000
    assert total_paise(500_000, "INR", 99_000_000) == 500_000
    assert to_rate_micro("83.405") == 83_405_000 and rate_str(83_400_000) == "83.4000" and rate_str(83_123_456) == "83.123456"


async def test_balance_new_dated_today_is_sent_at_once(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        t = inv.move_balance(ss, rv, src, to="new", on=TODAY)
        return t.kind, (t.year, t.month), t.status, t.sent_on, t.due_on, t.raise_on, t.number is not None, t.total_paise

    kind, ym, status, sent_on, due_on, raise_on, numbered, total = await run(seeded, go)
    assert (kind, ym, status, sent_on, raise_on, numbered, total) == ("balance", (2026, 11), "sent", TODAY, None, True, 600_000)
    assert due_on == date(2026, 11, 30)


async def test_balance_new_dated_in_the_past_is_also_sent_on_that_date(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        t = inv.move_balance(ss, rv, src, to="new", on=date(2026, 11, 10))
        return t.status, t.sent_on

    assert await run(seeded, go) == ("sent", date(2026, 11, 10))


async def test_balance_new_dated_ahead_gets_raise_on_and_stays_draft(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        t = inv.move_balance(ss, rv, src, to="new", on=date(2026, 12, 5))
        return t.status, t.raise_on, (t.year, t.month), cycles.raise_on(t), t.sent_on

    assert await run(seeded, go) == ("to_raise", date(2026, 12, 5), (2026, 12), date(2026, 12, 5), None)


async def test_balance_into_other_currency_month_makes_its_own_balance_invoice(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        usd_nov = mk_invoice(ss, rv, client_by(ss, "Zed"), 100_000, (2026, 11), "USD", priced=inv.price(ss, rv, "USD", 85_000_000))
        t = inv.move_balance(ss, rv, src, to="month", year=2026, month=11)
        return t.id != usd_nov.id, t.kind, t.currency, usd_nov.amount_minor

    assert await run(seeded, go) == (True, "balance", "INR", 100_000)


async def test_balance_delete_destination_restores_source_to_part_paid(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        t = inv.move_balance(ss, rv, src, to="month", year=2026, month=11)
        inv.delete_invoice(ss, rv, t)
        ss.expire_all()
        return src.status, src.moved_paise, src.moved_to_id, inv.remaining_paise(src), inv.outstanding_paise(src), inv.billed_paise(src)

    assert await run(seeded, go) == ("part_paid", 0, None, 600_000, 600_000, 1_000_000)


async def test_balance_delete_requires_unraised_destination(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        t = inv.move_balance(ss, rv, src, to="new", on=TODAY)  # sent at once
        inv.delete_invoice(ss, rv, t)

    with pytest.raises(DomainError) as e:
        await run(seeded, go)
    assert code_of(e) == BAD_STATUS


async def test_plan_balance_validation(seeded):
    def not_part_paid(ss, rv):
        c = mk_client(ss, rv)
        i = mk_invoice(ss, rv, c, 10_000 * R, (2026, 10))
        inv.plan_balance(ss, rv, i, to="month", year=2026, month=11)

    def bad_to(ss, rv):
        inv.plan_balance(ss, rv, part_paid_zed(ss, rv), to="elsewhere")

    def new_needs_date(ss, rv):
        inv.plan_balance(ss, rv, part_paid_zed(ss, rv), to="new")

    def month_needs_month(ss, rv):
        inv.plan_balance(ss, rv, part_paid_zed(ss, rv), to="month")

    for fn, code in [(not_part_paid, BAD_STATUS), (bad_to, VALIDATION), (new_needs_date, VALIDATION), (month_needs_month, VALIDATION)]:
        with pytest.raises(DomainError) as e:
            await run(seeded, fn)
        assert code_of(e) == code


async def test_plan_balance_preview_writes_nothing(seeded):
    def go(ss, rv):
        src = part_paid_zed(ss, rv)
        plan = inv.plan_balance(ss, rv, src, to="month", year=2026, month=11)
        ss.expire_all()
        return plan.balance_paise, plan.balance_minor, plan.new_total_paise, plan.onto, src.status, len(invs_of(ss, "Zed")), "to raise" in plan.summary()

    assert await run(seeded, go) == (600_000, 600_000, 600_000, None, "part_paid", 1, True)


# ================================================================ 6. Project end


def _end(ss, rv, name="Northwind", **kw):
    p, combined = project_end.apply(ss, rv, client_by(ss, name), on=date(2026, 11, 30), **kw)
    return p, combined


async def test_end_none_ends_client_and_leaves_invoices(seeded):
    def go(ss, rv):
        before = ym_status(ss, "Northwind")
        p, combined = _end(ss, rv, pending="none")
        return client_by(ss, "Northwind").state, ym_status(ss, "Northwind") == before, combined, p.affected, p.summary()

    state, same, combined, affected, summary = await run(seeded, go)
    assert (state, same, combined, affected) == ("ended", True, None, []) and "invoices stay as they are" in summary


async def test_end_separate_sends_each_to_raise_on_the_end_day(seeded):
    def go(ss, rv):
        p, _ = _end(ss, rv, pending="separate")
        rows = invs_of(ss, "Northwind")
        return len(p.affected), [(i.year, i.month, i.status, i.sent_on) for i in rows], client_by(ss, "Northwind").state

    n, rows, state = await run(seeded, go)
    assert n == 5 and state == "ended"
    assert rows[0][2] == "paid" and rows[1][2] == "part_paid"
    assert all(r[2] == "sent" and r[3] == date(2026, 11, 30) for r in rows[2:])


async def test_end_combine_merges_sources_into_one_priced_at_the_month_rate(seeded):
    def go(ss, rv):
        p, combined = _end(ss, rv, pending="combine", combine_month=(2026, 11))
        srcs = [inv_of(ss, "Northwind", *ym) for ym in [(2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)]]
        return ((combined.kind, combined.amount_minor, combined.fx_rate_micro, combined.fx_source, combined.total_paise, combined.status,
                 combined.sent_on, "Combined at project end" in combined.notes),
                [(s.status, s.moved_paise == s.total_paise, s.moved_to_id == combined.id, inv.billed_paise(s)) for s in srcs],
                p.total_paise, client_by(ss, "Northwind").state, (combined.year, combined.month))

    comb, srcs, plan_total, state, ym = await run(seeded, go)
    assert comb == ("combined", 750_000, USD_83_90, "month", 62_925_000, "sent", date(2026, 11, 30), True)
    assert srcs == [("merged", True, True, 0)] * 5
    assert plan_total == 62_925_000 and state == "ended" and ym == (2026, 11)


async def test_end_combine_send_now_false_leaves_a_draft_and_delete_restores_sources(seeded):
    def go(ss, rv):
        _p, combined = _end(ss, rv, pending="combine", combine_month=(2027, 3), send_now=False)
        status = combined.status
        inv.delete_invoice(ss, rv, combined)
        ss.expire_all()
        srcs = [inv_of(ss, "Northwind", *ym) for ym in [(2026, 11), (2026, 12), (2027, 1), (2027, 2), (2027, 3)]]
        return status, [(s.status, s.moved_paise, s.moved_to_id) for s in srcs]

    status, srcs = await run(seeded, go)
    assert status == "to_raise" and srcs == [("to_raise", 0, None)] * 5


async def test_end_combine_requires_common_currency_and_something_pending(seeded):
    def mixed(ss, rv):
        c = mk_client(ss, rv, "Mix Co")
        mk_invoice(ss, rv, c, 10_000 * R, (2026, 11))
        mk_invoice(ss, rv, c, 100_000, (2026, 12), "USD")
        project_end.plan(ss, rv, c, on=TODAY, pending="combine", combine_month=(2026, 12))

    def nothing(ss, rv):
        project_end.plan(ss, rv, client_by(ss, "Orbit"), on=TODAY, pending="combine", combine_month=(2026, 11))

    def no_month(ss, rv):
        project_end.plan(ss, rv, client_by(ss, "Northwind"), on=TODAY, pending="combine")

    for fn, code in [(mixed, MIXED_CURRENCY), (nothing, NOTHING_PENDING), (no_month, VALIDATION)]:
        with pytest.raises(DomainError) as e:
            await run(seeded, fn)
        assert code_of(e) == code


async def test_end_ignore_writes_off_unpaid_from_month_but_receipts_still_count(seeded):
    def go(ss, rv):
        dry = project_end.plan(ss, rv, client_by(ss, "Northwind"), on=TODAY, pending="ignore", ignore_from=(2026, 10))
        total = dry.total_paise  # read before applying: written-off rows have nothing remaining
        p, _ = _end(ss, rv, pending="ignore", ignore_from=(2026, 10))
        octo = inv_of(ss, "Northwind", 2026, 10)
        nov = inv_of(ss, "Northwind", 2026, 11)
        sep = inv_of(ss, "Northwind", 2026, 9)
        return (len(p.affected), total, ym_status(ss, "Northwind"),
                (inv.received_paise(octo), inv.billed_paise(octo), inv.outstanding_paise(octo), inv.remaining_paise(octo)),
                (inv.billed_paise(nov), inv.remaining_paise(nov)), sep.status)

    n, total, status, octo, nov, sep = await run(seeded, go)
    assert n == 6 and total == (12_585_000 - 6_000_000) + 5 * 12_585_000  # Oct's unpaid part + five full drafts
    assert status[(2026, 9)] == "paid" and all(s == "written_off" for ym, s in status.items() if ym >= (2026, 10))
    assert octo == (6_000_000, 6_000_000, 0, 0)  # Rs 60,000 still counts as received and billed
    assert nov == (0, 0) and sep == "paid"


async def test_end_ignore_from_a_later_month_spares_earlier_unpaid(seeded):
    def go(ss, rv):
        p, _ = _end(ss, rv, pending="ignore", ignore_from=(2027, 2))
        return len(p.affected), ym_status(ss, "Northwind")

    n, status = await run(seeded, go)
    assert n == 2 and status[(2027, 1)] == "to_raise" and status[(2027, 2)] == status[(2027, 3)] == "written_off"
    assert status[(2026, 10)] == "part_paid"


async def test_end_ignore_with_nothing_unpaid_still_ends_client(seeded):
    def go(ss, rv):
        p, _ = _end(ss, rv, "Orbit", pending="ignore", ignore_from=(2027, 1))
        return p.affected, "Nothing unpaid" in p.summary(), client_by(ss, "Orbit").state

    assert await run(seeded, go) == ([], True, "ended")


async def test_end_ignore_needs_a_month_and_pending_must_be_known(seeded):
    def no_month(ss, rv):
        project_end.plan(ss, rv, client_by(ss, "Northwind"), on=TODAY, pending="ignore")

    def unknown(ss, rv):
        project_end.plan(ss, rv, client_by(ss, "Northwind"), on=TODAY, pending="burn")

    for fn in (no_month, unknown):
        with pytest.raises(DomainError) as e:
            await run(seeded, fn)
        assert code_of(e) == VALIDATION


async def test_ending_an_ended_client_is_same_state(seeded):
    await run(seeded, lambda ss, rv: _end(ss, rv, pending="none"))
    with pytest.raises(DomainError) as e:
        await run(seeded, lambda ss, rv: _end(ss, rv, pending="separate"))
    assert code_of(e) == SAME_STATE


async def test_end_plan_is_a_dry_run(seeded):
    def go(ss, rv):
        p = project_end.plan(ss, rv, client_by(ss, "Northwind"), on=TODAY, pending="separate")
        return len(p.affected), ym_status(ss, "Northwind")[(2026, 11)], client_by(ss, "Northwind").state

    assert await run(seeded, go) == (5, "to_raise", "active")


async def test_end_writes_a_project_closed_audit_row(seeded):
    from app.models import AuditEvent

    await run(seeded, lambda ss, rv: _end(ss, rv, pending="separate"))

    def go(ss, rv):
        ev = ss.scalars(select(AuditEvent).where(AuditEvent.action == "revenue.project_closed")).one()
        return ev.after["pending"], len(ev.after["invoices"]), ev.after["channel"]

    assert await run(seeded, go) == ("separate", 5, "ui")


# ================================================================ 7. Through proposals


async def test_rev_set_cycle_executes(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_set_cycle", {"client": "Northwind", "from": "2026-12", "amount": "2000", "currency": "USD",
                                                       "period_months": 1, "timing": "advance", "mode": "monthly"})
    assert out.status == "executed" and "Plans 4 invoice(s)" in out.receipt.summary

    def go(ss, rv):
        return inv_of(ss, "Northwind", 2026, 12).amount_minor, inv_of(ss, "Northwind", 2026, 11).amount_minor

    assert await run(seeded, go) == (200_000, 150_000)


async def test_rev_set_cycle_amount_is_per_period_and_must_split_evenly(seeded):
    p = await priya(seeded)
    base = {"client": "Cyc", "from": "2026-10", "currency": "INR", "period_months": 3, "amount_is_per_period": True}
    await run(seeded, lambda ss, rv: mk_client(ss, rv, "Cyc Co"))
    _, out = await propose_confirm(p, "rev_set_cycle", {**base, "amount": "30000"})
    assert out.status == "executed"
    assert await run(seeded, lambda ss, rv: inv_of(ss, "Cyc", 2026, 10).amount_minor) == 30_000 * R
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, p, "rev_set_cycle", {**base, "amount": "30001"})
    assert e.value.code == VALIDATION


async def test_rev_plan_fy_executes_and_second_run_says_already_planned(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_plan_fy", {"client": "Northwind", "fy": "2027-28"})
    assert out.status == "executed" and "Planned 12 invoice(s)" in out.receipt.summary
    async with db.session_scope() as s:
        again = await proposals.create(s, p, "rev_plan_fy", {"client": "Northwind", "fy": "2027-28"})
    assert again.preview["lines"] == ["FY 2027-28 is already planned for Northwind Labs (synthetic)."]


async def test_rev_plan_fy_without_a_cycle_is_refused(seeded):
    p = await priya(seeded)
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, p, "rev_plan_fy", {"client": "Orbit", "fy": "2026-27"})
    assert e.value.code == VALIDATION


async def test_rev_move_balance_new_invoice_dated_today(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 10).ref)
    _, out = await propose_confirm(p, "rev_move_balance", {"ref": ref, "to": "new", "on": "2026-11-21"})
    assert out.status == "executed"

    def go(ss, rv):
        bal = inv_of(ss, "Northwind", 2026, 11, "balance")
        return bal.status, bal.sent_on, bal.fx_source, bal.fx_rate_micro

    assert await run(seeded, go) == ("sent", TODAY, "month", USD_83_90)


async def test_rev_move_balance_on_a_paid_invoice_is_refused(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 9).ref)
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, p, "rev_move_balance", {"ref": ref, "month": "2026-11"})
    assert e.value.code == BAD_STATUS


async def test_rev_delete_draft_restores_moved_balance(seeded):
    p = await priya(seeded)
    oct_ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 10).ref)
    await propose_confirm(p, "rev_move_balance", {"ref": oct_ref, "to": "new", "on": "2026-12-05"})
    bal_ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 12, "balance").ref)
    _, out = await propose_confirm(p, "rev_delete_draft", {"ref": bal_ref})
    assert out.status == "executed"

    def go(ss, rv):
        octo = inv_of(ss, "Northwind", 2026, 10)
        gone = ss.scalars(select(Invoice).where(Invoice.ref == bal_ref)).first()
        return octo.status, octo.moved_paise, octo.moved_to_id, gone

    assert await run(seeded, go) == ("part_paid", 0, None, None)


async def test_rev_delete_draft_refuses_a_sent_invoice(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 10).ref)
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, p, "rev_delete_draft", {"ref": ref})
    assert e.value.code == BAD_STATUS


async def test_rev_end_project_each_choice(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_end_project", {"client": "Northwind", "pending": "combine", "combine_month": "2026-11", "on": "2026-11-30"})
    assert out.status == "executed"

    def go(ss, rv):
        comb = inv_of(ss, "Northwind", 2026, 11, "combined")
        return client_by(ss, "Northwind").state, comb.status, comb.total_paise, ym_status(ss, "Northwind")[(2027, 3)]

    assert await run(seeded, go) == ("ended", "sent", 62_925_000, "merged")

    _, out2 = await propose_confirm(p, "rev_end_project", {"client": "Kaveri", "pending": "separate", "on": "2026-11-30"})
    assert out2.status == "executed"
    assert await run(seeded, lambda ss, rv: (client_by(ss, "Kaveri").state, ym_status(ss, "Kaveri")[(2027, 1)])) == ("ended", "sent")

    _, out3 = await propose_confirm(p, "rev_end_project", {"client": "Orbit", "pending": "ignore", "ignore_from": "2026-08"})
    assert out3.status == "executed"
    assert await run(seeded, lambda ss, rv: (client_by(ss, "Orbit").state, ym_status(ss, "Orbit")[(2026, 8)])) == ("ended", "written_off")


async def test_rev_end_project_again_is_refused(seeded):
    p = await priya(seeded)
    await propose_confirm(p, "rev_end_project", {"client": "Northwind", "pending": "none"})
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, p, "rev_end_project", {"client": "Northwind", "pending": "none"})
    assert e.value.code == SAME_STATE


async def test_rev_refresh_rate_reprices_an_ecb_draft(seeded):
    _cid, iid = await run(seeded, _aug_ecb)
    await set_quote(90_000_000, day=TODAY)
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_refresh_rate", {"ref": f"S{iid}"})
    assert out.status == "executed"

    def go(ss, rv):
        i = ss.get(Invoice, iid)
        return i.fx_rate_micro, i.fx_source, i.total_paise, i.fx_date

    assert await run(seeded, go) == (90_000_000, "ecb", 100_000 * 90, TODAY)


async def test_rev_refresh_rate_refuses_paid_invoice(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 9).ref)
    async with db.session_scope() as s:
        with pytest.raises(DomainError):
            await proposals.create(s, p, "rev_refresh_rate", {"ref": ref})


async def test_rev_send_ecb_draft_through_proposal_takes_fresh_quote(seeded):
    _cid, iid = await run(seeded, _aug_ecb)
    await set_quote(88_000_000, day=TODAY)
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_send", {"refs": [f"S{iid}"], "on": "2026-11-21"})
    assert out.status == "executed"
    assert await run(seeded, lambda ss, rv: ss.get(Invoice, iid).fx_rate_micro) == 88_000_000


async def test_proposal_preview_writes_nothing(seeded):
    p = await priya(seeded)
    async with db.session_scope() as s:
        prop = await proposals.create(s, p, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85"})
        assert prop.affected  # the invoices the plan would touch are locked in by version

    def go(ss, rv):
        return ([(r.year, r.month) for r in ss.scalars(select(FxMonth))], inv_of(ss, "Northwind", 2026, 11).fx_rate_micro,
                ss.scalars(select(func.count()).select_from(ClientCycle)).one())

    months, rate, _n = await run(seeded, go)
    assert sorted(months) == [(2026, 9), (2026, 10)] and rate == USD_83_90


async def test_rev_fx_month_goes_stale_when_an_affected_invoice_changes(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 12).ref)
    async with db.session_scope() as s:
        first = await proposals.create(s, p, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85"})
    _, edit = await propose_confirm(p, "rev_edit_invoice", {"ref": ref, "notes": "touched"})
    assert edit.status == "executed"
    async with db.session_scope() as s:
        out = await proposals.confirm(s, p, first.id, via="button")
    assert out.status == "stale" and out.new_proposal is not None and out.new_proposal.id != first.id

    def go(ss, rv):
        return [(r.year, r.month) for r in ss.scalars(select(FxMonth))], inv_of(ss, "Northwind", 2026, 11).fx_rate_micro

    months, rate = await run(seeded, go)
    assert sorted(months) == [(2026, 9), (2026, 10)] and rate == USD_83_90  # the stale proposal never ran


async def test_rev_move_balance_goes_stale_when_destination_changes(seeded):
    p = await priya(seeded)
    oct_ref, nov_ref = await run(seeded, lambda ss, rv: (inv_of(ss, "Northwind", 2026, 10).ref, inv_of(ss, "Northwind", 2026, 11).ref))
    async with db.session_scope() as s:
        first = await proposals.create(s, p, "rev_move_balance", {"ref": oct_ref, "month": "2026-11"})
    await propose_confirm(p, "rev_edit_invoice", {"ref": nov_ref, "notes": "changed meanwhile"})
    async with db.session_scope() as s:
        out = await proposals.confirm(s, p, first.id, via="button")
    assert out.status == "stale"
    assert await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2026, 10).status) == "part_paid"


async def test_rev_set_cycle_goes_stale_when_a_draft_it_replaces_changes(seeded):
    p = await priya(seeded)
    ref = await run(seeded, lambda ss, rv: inv_of(ss, "Northwind", 2027, 1).ref)
    async with db.session_scope() as s:
        first = await proposals.create(s, p, "rev_set_cycle", {"client": "Northwind", "from": "2026-12", "amount": "2000", "currency": "USD",
                                                              "period_months": 1, "mode": "monthly"})
    await propose_confirm(p, "rev_edit_invoice", {"ref": ref, "notes": "edited"})
    async with db.session_scope() as s:
        out = await proposals.confirm(s, p, first.id, via="button")
    assert out.status == "stale"


async def test_confirming_twice_replays(seeded):
    p = await priya(seeded)
    prop, out = await propose_confirm(p, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85"})
    async with db.session_scope() as s:
        again = await proposals.confirm(s, p, prop.id, via="button")
    assert out.status == "executed" and again.status == "replayed" and again.receipt.id == out.receipt.id

    def go(ss, rv):
        return ss.scalars(select(func.count()).select_from(FxMonth).where(FxMonth.month == 11)).one()

    assert await run(seeded, go) == 1


async def test_employee_forbidden_for_every_fx_cycle_balance_end_action(seeded):
    arjun = await make_actor(seeded, "arjun")
    cases = [
        ("rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85"}),
        ("rev_set_cycle", {"client": "Northwind", "from": "2026-12", "amount": "2000", "currency": "USD"}),
        ("rev_plan_fy", {"client": "Northwind", "fy": "2027-28"}),
        ("rev_move_balance", {"ref": "S1", "month": "2026-11"}),
        ("rev_end_project", {"client": "Northwind", "pending": "none"}),
        ("rev_edit_invoice", {"ref": "S1", "rate": "86"}),
        ("rev_refresh_rate", {"ref": "S1"}),
        ("rev_delete_draft", {"ref": "S1"}),
    ]
    for kind, args in cases:
        async with db.session_scope() as s:
            with pytest.raises(DomainError) as e:
                await proposals.create(s, arjun, kind, args)
        assert e.value.code == FORBIDDEN, kind


async def test_conversation_actor_must_have_said_the_rate_and_amount(seeded):
    """With a conversation the model cannot invent the rate: the number must be in the user's own words."""
    from app.services.confirmation import record_turn

    actor = await make_actor(seeded, "priya")  # conversation attached
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, actor, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85"})
    assert e.value.code == VALIDATION
    async with db.session_scope() as s:
        await record_turn(s, actor, "set the dollar rate to 85 for November", source="text")
    async with db.session_scope() as s:
        prop = await proposals.create(s, actor, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85"})
    assert prop.status == "open"


async def test_seeding_a_second_workspace_does_not_collide_on_the_global_fx_quote(seeded):
    from seed.seed_v1 import seed

    async with db.session_scope() as s:
        other = await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")
    assert other["workspace_id"] != seeded["workspace_id"]
