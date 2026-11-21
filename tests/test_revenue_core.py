"""Revenue core: money maths, invoice lifecycle, allocation, reporting figures, suggestions, propose->confirm actions,
spoken-number grounding, API access, version bumps. Oracles are the worked examples in the owner's CLIENT_REVENUE.md.
Business date pinned to 2026-11-21; FX provider is the offline fixture (no network). Postgres only."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app import db
from app.config import get_settings
from app.errors import FORBIDDEN, NOT_FOUND, VALIDATION, DomainError
from app.models import AuditEvent, Invoice, InvoicePayment, Party
from app.services import proposals
from app.services.confirmation import record_turn
from app.services.revenue import clients as cl
from app.services.revenue import cycles, grounding, insights, reads, reminders, suggest
from app.services.revenue import invoices as inv
from app.services.revenue.core import (
    BAD_STATUS,
    CLIENT_EXISTS,
    INVOICE_PAID,
    MONTH_TAKEN,
    Rev,
)
from app.services.revenue.money import (
    format_inr,
    numbers_in,
    paise_str,
    rate_str,
    to_minor,
    to_rate_micro,
    total_paise,
)
from seed.seed_v1 import seed
from tests.conftest import make_actor
from tests.test_api_intake import client_for
from tests.test_intake_extra import call

TODAY = date(2026, 11, 21)
FY = "2026-27"
R = 100  # paise per rupee


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


def rv_of(ids, who="priya", channel="ui") -> Rev:
    return Rev(ids["workspace_id"], ids[f"{who}_id"], TODAY, channel)


async def run(ids, fn, who="priya"):
    """Run fn(ss, rv) on a sync session inside one committed transaction; return what fn returns (plain data)."""
    rv = rv_of(ids, who)
    async with db.session_scope() as s:
        return await s.run_sync(lambda ss: fn(ss, rv))


def mk_client(ss, rv, name="Zed Co", currency="INR"):
    return cl.create_client(ss, rv, name=name, currency=currency)


def mk_inr(ss, rv, client, rupees, month=(2026, 11)):
    [i] = inv.create_invoices(ss, rv, client=client, months=[month], amount_minor=rupees * R, currency="INR",
                              priced=inv.price(ss, rv, "INR"))
    return i


def send(ss, rv, i, on=date(2026, 11, 1)):
    return inv.set_status(ss, rv, i, "sent", on=on)


def code_of(exc: pytest.ExceptionInfo) -> str:
    return exc.value.code


def row(ss, ref):
    return ss.scalars(select(Invoice).where(Invoice.ref == ref)).one()


async def propose_confirm(actor, kind, args, via="button"):
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, kind, args)
    async with db.session_scope() as s:
        out = await proposals.confirm(s, actor, p.id, via=via)
    return p, out


async def priya(ids):
    """Approver with no conversation: grounding is skipped (the on-screen form path)."""
    return await make_actor(ids, "priya", conversation=False)


# ---------------------------------------------------------------- 1. money (pure)


def test_usd_booked_total_matches_guide_example():
    assert total_paise(25_000, "USD", to_rate_micro("83.1250")) == 2_078_125
    assert format_inr(2_078_125) == "₹20,781.25"


def test_jpy_has_zero_decimals():
    assert to_minor("100", "JPY") == 100
    with pytest.raises(ValueError):
        to_minor("100.5", "JPY")
    assert total_paise(100, "JPY", 560_000) == 5_600  # 100 yen at 0.56 INR = Rs 56


@pytest.mark.parametrize("bad", ["-1", "abc", "1.234", "NaN", "Infinity"])
def test_to_minor_rejects_bad_usd_amounts(bad):
    with pytest.raises(ValueError):
        to_minor(bad, "USD")


def test_to_minor_accepts_grouped_and_decimal():
    assert to_minor("2,000.50", "USD") == 200_050


@pytest.mark.parametrize("rate", ["0", "-3", "100001", "x"])
def test_to_rate_micro_rejects_insane_rates(rate):
    with pytest.raises(ValueError):
        to_rate_micro(rate)


def test_rate_and_paise_formatting():
    assert rate_str(83_125_000) == "83.1250"
    assert paise_str(-12_345) == "-123.45"
    assert format_inr(12_345_600) == "₹1,23,456"  # Indian grouping, no paise shown when zero


def test_numbers_in_scales():
    assert Decimal(150_000) in numbers_in("received 1.5L from them")
    assert Decimal(2000) in numbers_in("2,000 only")
    assert Decimal(30_000) in numbers_in("about 30k")


# ---------------------------------------------------------------- 2. lifecycle


async def test_usd_invoice_send_part_payment_and_cache(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv, "Zenith USD", "USD")
        [i] = inv.create_invoices(ss, rv, client=c, months=[(2026, 10)], amount_minor=25_000, currency="USD",
                                  priced=inv.Price(to_rate_micro("83.1250"), "manual", None))
        assert i.total_paise == 2_078_125 and i.status == "to_raise" and i.ref == f"S{i.id}"
        inv.set_status(ss, rv, i, "sent", on=date(2026, 10, 12))
        assert i.status == "sent" and i.sent_on == date(2026, 10, 12) and i.due_on == date(2026, 10, 31)
        assert i.number == f"INV-2026-{i.id:04d}"
        inv.record_payment(ss, rv, i, amount_paise=10_000 * R, received_on=date(2026, 11, 2), settled=False)
        ss.expire_all()
        i = ss.get(Invoice, i.id)
        return (i.status, inv.outstanding_paise(i), i.paid_paise, sum(p.amount_paise for p in i.payments))

    status, outstanding, cached, summed = await run(seeded, go)
    assert status == "part_paid"
    assert outstanding == 1_078_125  # Rs 10,781.25
    assert cached == summed == 1_000_000


async def test_unsend_blocked_once_payment_exists(seeded):
    def go(ss, rv):
        i = send(ss, rv, mk_inr(ss, rv, mk_client(ss, rv), 5000))
        inv.record_payment(ss, rv, i, amount_paise=100 * R, received_on=TODAY, settled=False)
        with pytest.raises(DomainError) as e:
            inv.set_status(ss, rv, i, "to_raise", on=TODAY)
        return code_of(e)

    assert await run(seeded, go) == BAD_STATUS


async def test_unsend_clears_dates_when_no_payment(seeded):
    def go(ss, rv):
        i = send(ss, rv, mk_inr(ss, rv, mk_client(ss, rv), 5000))
        inv.set_status(ss, rv, i, "to_raise", on=TODAY)
        return i.status, i.sent_on, i.due_on

    assert await run(seeded, go) == ("to_raise", None, None)


async def test_paid_invoice_rejects_payment_and_financial_edit_but_allows_notes(seeded):
    def go(ss, rv):
        i = send(ss, rv, mk_inr(ss, rv, mk_client(ss, rv), 5000))
        inv.record_payment(ss, rv, i, amount_paise=None, received_on=TODAY, settled=True)
        assert i.status == "paid"
        with pytest.raises(DomainError) as e1:
            inv.record_payment(ss, rv, i, amount_paise=100, received_on=TODAY, settled=True)
        with pytest.raises(DomainError) as e2:
            inv.update_invoice(ss, rv, i, amount_minor=9999 * R)
        inv.update_invoice(ss, rv, i, notes="thanks")
        return code_of(e1), code_of(e2), i.notes, i.total_paise

    assert await run(seeded, go) == (INVOICE_PAID, INVOICE_PAID, "thanks", 5000 * R)


async def test_delete_only_when_to_raise(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        sent = send(ss, rv, mk_inr(ss, rv, c, 1000, (2026, 10)))
        draft = mk_inr(ss, rv, c, 2000, (2026, 11))
        with pytest.raises(DomainError) as e:
            inv.delete_invoice(ss, rv, sent)
        did = draft.id
        inv.delete_invoice(ss, rv, draft)
        return code_of(e), ss.get(Invoice, did)

    assert await run(seeded, go) == (BAD_STATUS, None)


async def test_second_regular_row_same_month_is_refused(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        mk_inr(ss, rv, c, 1000)
        with pytest.raises(DomainError) as e:
            mk_inr(ss, rv, c, 2000)
        return code_of(e)

    assert await run(seeded, go) == MONTH_TAKEN


async def test_create_cap_and_duplicate_months(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        p = inv.price(ss, rv, "INR")
        months = [(2026 + (4 + k) // 12, (4 + k) % 12 + 1) for k in range(25)]
        with pytest.raises(DomainError) as cap:
            inv.create_invoices(ss, rv, client=c, months=months, amount_minor=100, currency="INR", priced=p)
        with pytest.raises(DomainError) as dup:
            inv.create_invoices(ss, rv, client=c, months=[(2026, 12), (2026, 12)], amount_minor=100, currency="INR", priced=p)
        ok = inv.create_invoices(ss, rv, client=c, months=months[:24], amount_minor=100, currency="INR", priced=p)
        return code_of(cap), code_of(dup), len(ok)

    assert await run(seeded, go) == (VALIDATION, VALIDATION, 24)


async def test_zero_or_negative_amount_refused(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        with pytest.raises(DomainError) as e:
            inv.create_invoices(ss, rv, client=c, months=[(2026, 12)], amount_minor=0, currency="INR",
                                priced=inv.price(ss, rv, "INR"))
        return code_of(e)

    assert await run(seeded, go) == VALIDATION


async def test_duplicate_client_name_and_archive_restore(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv, "Dup Co")
        with pytest.raises(DomainError) as e:
            cl.create_client(ss, rv, name="dup  co")
        cl.update_client(ss, rv, c, archived=True)
        back = cl.create_client(ss, rv, name="Dup Co")  # returning client keeps its record
        return code_of(e), back.id == c.id, back.archived_at

    assert await run(seeded, go) == (CLIENT_EXISTS, True, None)


async def test_payment_without_send_stamps_send_date(seeded):
    def go(ss, rv):
        i = mk_inr(ss, rv, mk_client(ss, rv), 3000)
        inv.record_payment(ss, rv, i, amount_paise=None, received_on=date(2026, 11, 5), settled=True)
        return i.status, i.sent_on, i.number is not None

    assert await run(seeded, go) == ("paid", date(2026, 11, 5), True)


# ---------------------------------------------------------------- 3. allocation


async def test_credit_allocated_oldest_first_guide_example(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        older = send(ss, rv, mk_inr(ss, rv, c, 10_000, (2026, 9)), on=date(2026, 9, 1))
        newer = send(ss, rv, mk_inr(ss, rv, c, 12_000, (2026, 10)), on=date(2026, 10, 1))
        inv.record_payments(ss, rv, [newer, older], amount_paise=16_000 * R, received_on=TODAY, settled=False)
        return (older.status, newer.status, inv.remaining_paise(newer), inv.outstanding_paise(older))

    assert await run(seeded, go) == ("paid", "part_paid", 6_000 * R, 0)


async def test_allocation_across_two_clients_rejected(seeded):
    def go(ss, rv):
        a = send(ss, rv, mk_inr(ss, rv, mk_client(ss, rv, "A Co"), 1000))
        b = send(ss, rv, mk_inr(ss, rv, mk_client(ss, rv, "B Co"), 1000))
        with pytest.raises(DomainError) as e:
            inv.plan_allocation([a, b], 1500 * R, False)
        return code_of(e)

    assert await run(seeded, go) == VALIDATION


async def test_allocation_without_amount_pays_each_remaining(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        a = send(ss, rv, mk_inr(ss, rv, c, 1000, (2026, 9)))
        b = send(ss, rv, mk_inr(ss, rv, c, 2000, (2026, 10)))
        inv.record_payments(ss, rv, [a, b], amount_paise=None, received_on=TODAY, settled=True)
        return a.status, b.status

    assert await run(seeded, go) == ("paid", "paid")


# ---------------------------------------------------------------- 4. reporting figures


def figures(ss, rv, client):
    k = insights.build(ss, rv, FY, client_id=client.id).kpis
    return {"proj": k.projection, "recv": k.received, "out": k.outstanding, "over": k.overdue, "to_raise": k.to_raise,
            "fx": k.fx_gain, "over_n": k.overdue_count}


async def test_due_today_is_outstanding_not_overdue(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        i = send(ss, rv, mk_inr(ss, rv, c, 5000))
        i.due_on = TODAY
        ss.flush()
        today_fig = figures(ss, rv, c)
        i.due_on = date(2026, 11, 20)
        ss.flush()
        return today_fig, figures(ss, rv, c)

    due_today, yesterday = await run(seeded, go)
    assert due_today["out"] == 5000 * R and due_today["over"] == 0 and due_today["over_n"] == 0
    assert yesterday["over"] == 5000 * R and yesterday["over_n"] == 1


async def test_settled_short_payment_zero_outstanding_negative_fx(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        i = send(ss, rv, mk_inr(ss, rv, c, 10_000))
        inv.record_payment(ss, rv, i, amount_paise=9_000 * R, received_on=TODAY, settled=True)
        return figures(ss, rv, c), inv.remaining_paise(i)

    f, remaining = await run(seeded, go)
    assert f == {"proj": 10_000 * R, "recv": 9_000 * R, "out": 0, "over": 0, "to_raise": 0, "fx": -1_000 * R, "over_n": 0}
    assert remaining == 1_000 * R  # arithmetic leftover exists but is not collectible


async def test_settled_over_payment_positive_fx_gain(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        i = send(ss, rv, mk_inr(ss, rv, c, 10_000))
        inv.record_payment(ss, rv, i, amount_paise=10_500 * R, received_on=TODAY, settled=True)
        return figures(ss, rv, c)["fx"], inv.remaining_paise(i)

    assert await run(seeded, go) == (500 * R, 0)


async def test_to_raise_counts_total_only_in_to_raise(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        mk_inr(ss, rv, c, 7_000)
        return figures(ss, rv, c)

    f = await run(seeded, go)
    assert f["to_raise"] == 7_000 * R and f["out"] == 0 and f["proj"] == 7_000 * R and f["recv"] == 0


async def test_part_paid_outstanding_is_remaining(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        i = send(ss, rv, mk_inr(ss, rv, c, 10_000))
        inv.record_payment(ss, rv, i, amount_paise=4_000 * R, received_on=TODAY, settled=False)
        return figures(ss, rv, c)

    f = await run(seeded, go)
    assert (f["recv"], f["out"], f["fx"]) == (4_000 * R, 6_000 * R, 0)


async def test_written_off_counts_only_what_came_in_and_merged_counts_zero(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        a = send(ss, rv, mk_inr(ss, rv, c, 10_000, (2026, 10)))
        inv.record_payment(ss, rv, a, amount_paise=3_000 * R, received_on=TODAY, settled=False)
        a.status = "written_off"
        m = mk_inr(ss, rv, c, 8_000, (2026, 11))
        m.status = "merged"
        ss.flush()
        return (inv.billed_paise(a), inv.remaining_paise(a), inv.outstanding_paise(a), inv.billed_paise(m), figures(ss, rv, c))

    billed, remaining, outstanding, merged_billed, f = await run(seeded, go)
    assert (billed, remaining, outstanding, merged_billed) == (3_000 * R, 0, 0, 0)
    assert f["proj"] == 3_000 * R and f["recv"] == 3_000 * R and f["out"] == 0 and f["to_raise"] == 0


async def test_balance_move_guide_example(seeded):
    """Rs 10,000 Oct with Rs 4,000 in; move Rs 6,000 to Nov: moved_paise 600000, Oct billed 4,000, FX 0; Nov draft 6,000."""
    def go(ss, rv):
        c = mk_client(ss, rv)
        i = send(ss, rv, mk_inr(ss, rv, c, 10_000, (2026, 10)), on=date(2026, 10, 1))
        inv.record_payment(ss, rv, i, amount_paise=4_000 * R, received_on=TODAY, settled=False)
        target = inv.move_balance(ss, rv, i, to="month", year=2026, month=11)
        f = figures(ss, rv, c)
        return (i.moved_paise, i.status, i.moved_to_id == target.id, inv.billed_paise(i), inv.fx_gain_paise(i),
                target.total_paise, target.status, target.kind, f["proj"], f["to_raise"])

    got = await run(seeded, go)
    assert got == (6_000 * R, "paid", True, 4_000 * R, 0, 6_000 * R, "to_raise", "balance", 10_000 * R, 6_000 * R)


async def test_deleting_balance_destination_restores_source(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        i = send(ss, rv, mk_inr(ss, rv, c, 10_000, (2026, 10)), on=date(2026, 10, 1))
        inv.record_payment(ss, rv, i, amount_paise=4_000 * R, received_on=TODAY, settled=False)
        target = inv.move_balance(ss, rv, i, to="month", year=2026, month=11)
        inv.delete_invoice(ss, rv, target)
        ss.expire_all()
        i = ss.get(Invoice, i.id)
        return i.status, i.moved_paise, i.moved_to_id, inv.outstanding_paise(i)

    assert await run(seeded, go) == ("part_paid", 0, None, 6_000 * R)


async def test_cycle_quarterly_combined_advance_books_in_first_month(seeded):
    """Rs 10,000 a month, 3-month period from Oct, combined/advance: Rs 30,000 in Oct due end of Dec."""
    def go(ss, rv):
        c = mk_client(ss, rv, "Cyc Co")
        cycles.apply(ss, rv, c, cycles.CycleIn(2026, 10, 10_000 * R, "INR", 3, "advance", "combined"))
        rows = {(i.year, i.month): i for i in inv.list_invoices(ss, rv, client_id=c.id)}
        octo = rows[(2026, 10)]
        send(ss, rv, octo, on=date(2026, 10, 1))
        return octo.total_paise, octo.due_on, (2026, 11) in rows

    total, due, nov_row = await run(seeded, go)
    assert total == 30_000 * R and due == date(2026, 12, 31) and not nov_row


async def test_cycle_monthly_mode_emits_one_row_per_month(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv, "Cyc Two")
        cycles.apply(ss, rv, c, cycles.CycleIn(2026, 10, 10_000 * R, "INR", 3, "advance", "monthly"))
        rows = {(i.year, i.month): i for i in inv.list_invoices(ss, rv, client_id=c.id)}
        return [rows[(2026, m)].total_paise for m in (10, 11, 12)]

    assert await run(seeded, go) == [10_000 * R] * 3


# ---- seeded figures (hand-checked against the seed rows)


async def test_seeded_overview_figures(seeded):
    ov = await run(seeded, lambda ss, rv: reads.overview(ss, rv, FY))
    p = ov["kpis"]["paise"]
    # received: S6 20,000 + S7 124,950 + S14 75,000 + S8 60,000 = 279,950 rupees
    assert p["received"] == 27_995_000
    # outstanding: S16 40,000 + S4 82,500 + S1 125,000 + S6 27,200 + S8 65,850 + S3 60,000 + S2 38,000 + S5 210,000
    assert p["outstanding"] == 64_855_000
    # overdue: S16, S4, S1, S6, S8 (S2, S3, S5 not due yet)
    assert p["overdue"] == 34_055_000 and ov["kpis"]["overdue_count"] == 5
    # to raise: Northwind Nov-Mar 5 x 125,850 + Kaveri Jan 75,000
    assert p["to_raise"] == 70_425_000
    # fx: Northwind Sep settled Rs 150 short
    assert p["fx_gain"] == -15_000
    assert {g["client"] for g in ov["grid"]} >= {"Northwind Labs (synthetic)", "Kaveri Foods (synthetic)", "Orbit Design Studio (synthetic)"}


async def test_seeded_northwind_nov_priced_at_carried_oct_rate(seeded):
    def go(ss, rv):
        i = row(ss, seeded["northwind_nov_ref"])
        return i.fx_rate_micro, i.fx_source, i.total_paise, i.status

    assert await run(seeded, go) == (83_900_000, "month", 12_585_000, "to_raise")


async def test_period_filter_limits_figures(seeded):
    ov = await run(seeded, lambda ss, rv: reads.overview(ss, rv, FY, "2026-11"))
    # November billing month: S9 to raise 125,850 + S2 + S3 + S5 outstanding
    assert ov["kpis"]["paise"]["to_raise"] == 12_585_000
    assert ov["kpis"]["paise"]["outstanding"] == (38_000 + 60_000 + 210_000) * R


# ---------------------------------------------------------------- 5. suggestions


def sugg(ss, rv):
    return [(s.kind, s.ref, s.title) for s in suggest.build(ss, rv)]


async def test_chase_for_overdue_sent_invoice(seeded):
    def go(ss, rv):
        i = send(ss, rv, mk_inr(ss, rv, mk_client(ss, rv, "Late Co"), 5000, (2026, 10)), on=date(2026, 10, 12))
        return i.ref, sugg(ss, rv)

    ref, out = await run(seeded, go)
    assert ("chase", ref) in [(k, r) for k, r, _ in out]


async def test_raise_when_raise_date_arrived_not_before(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv, "Raise Co")
        now = mk_inr(ss, rv, c, 1000, (2026, 11))  # advance: raise on the 1st of its month
        later = mk_inr(ss, rv, c, 1000, (2026, 12))
        return now.ref, later.ref, sugg(ss, rv)

    now, later, out = await run(seeded, go)
    refs = {(k, r) for k, r, _ in out}
    assert ("raise", now) in refs and ("raise", later) not in refs


async def test_paid_check_a_week_after_send_and_not_yet_defers(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv, "Check Co")
        a = send(ss, rv, mk_inr(ss, rv, c, 1000, (2026, 11)), on=date(2026, 11, 14))  # 7 days ago
        b = send(ss, rv, mk_inr(ss, rv, mk_client(ss, rv, "Check Two"), 1000, (2026, 11)), on=date(2026, 11, 15))
        before = {(k, r) for k, r, _ in sugg(ss, rv)}
        inv.not_paid_yet(ss, rv, a, on=TODAY)
        after = {(k, r) for k, r, _ in sugg(ss, rv)}
        return a.ref, b.ref, before, after, inv.check_due_on(a)

    a, b, before, after, nxt = await run(seeded, go)
    assert ("paid_check", a) in before and ("paid_check", b) not in before
    assert ("paid_check", a) not in after
    assert nxt == date(2026, 11, 28)


async def test_reminder_due_today_appears_future_does_not(seeded):
    def go(ss, rv):
        reminders.add(ss, rv, due_on=TODAY, text="Chase Zed")
        reminders.add(ss, rv, due_on=date(2026, 11, 30), text="Far future")
        return [t for k, _r, t in sugg(ss, rv) if k == "reminder"]

    titles = await run(seeded, go)
    assert "Chase Zed" in titles and "Far future" not in titles
    assert any("Lotus" in t for t in titles)  # the seeded one


async def test_paused_client_gets_no_billing_suggestions(seeded):
    out = await run(seeded, sugg)
    assert not any(r == "S16" or "Orbit" in t for _k, r, t in out)  # Orbit: paused with an overdue sent invoice

    def go(ss, rv):
        c = mk_client(ss, rv, "Pause Co")
        i = send(ss, rv, mk_inr(ss, rv, c, 1000, (2026, 10)), on=date(2026, 10, 12))
        cl.set_client_state(ss, rv, c, "paused", on=TODAY)
        return i.ref, sugg(ss, rv)

    ref, out = await run(seeded, go)
    assert not any(r == ref for _k, r, _t in out)


async def test_custom_reminder_survives_pause(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv, "Pause Rem")
        cl.set_client_state(ss, rv, c, "paused", on=TODAY)
        reminders.add(ss, rv, due_on=TODAY, text="Ring Pause Rem", client_id=c.id)
        return [t for k, _r, t in sugg(ss, rv) if k == "reminder"]

    assert "Ring Pause Rem" in await run(seeded, go)


# ---------------------------------------------------------------- 6. actions via proposals


async def test_add_invoices_action_inr_new_client_with_receipt(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_add_invoices", {"client": "Fresh Client", "new_client": True, "amount": "10,000",
                                                            "months": ["2026-12", "2027-01"]})
    assert out.status == "executed" and out.receipt.ref.startswith("R") and "Added 2 invoices" in out.receipt.summary

    def go(ss, rv):
        c = cl.resolve(ss, rv, "Fresh Client")
        return [(i.year, i.month, i.total_paise, i.status) for i in inv.list_invoices(ss, rv, client_id=c.id)]

    assert await run(seeded, go) == [(2026, 12, 1_000_000, "to_raise"), (2027, 1, 1_000_000, "to_raise")]


async def test_add_invoices_action_usd_with_typed_rate(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_add_invoices", {"client": "Northwind Labs (synthetic)", "amount": "250",
                                                            "months": ["2027-04"], "currency": "USD", "rate": "83.1250"})
    assert out.status == "executed"
    eff = out.receipt.effects[0]
    assert eff["total_paise"] == 2_078_125 and eff["fx_source"] == "manual"


async def test_send_and_unsend_actions(seeded):
    p = await priya(seeded)
    ref = seeded["northwind_nov_ref"]
    _, sent = await propose_confirm(p, "rev_send", {"refs": [ref], "on": "2026-11-21"})
    assert sent.status == "executed" and sent.receipt.effects[0]["status"] == "sent"
    assert sent.receipt.effects[0]["due_on"] == "2026-11-30" and sent.receipt.effects[0]["number"]
    _, back = await propose_confirm(p, "rev_unsend", {"ref": ref})
    assert back.status == "executed" and back.receipt.effects[0]["status"] == "to_raise"
    assert back.receipt.effects[0]["due_on"] is None


async def test_payment_action_settles_and_summarises(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_payment", {"refs": ["S4"], "amount": "82500", "received_on": "2026-11-21"})
    assert out.status == "executed"
    assert "Recorded" in out.receipt.summary and out.receipt.effects[0]["status"] == "paid"
    assert out.receipt.effects[0]["received_paise"] == 8_250_000


async def test_payment_action_allocates_oldest_first(seeded):
    p = await priya(seeded)
    # Acme Traders S1 (Oct, Rs 125,000) and S2 (Nov, Rs 38,000): Rs 140,000 credit, not settled
    _, out = await propose_confirm(p, "rev_payment", {"refs": ["S2", "S1"], "amount": "140000", "settled": False})
    by_ref = {e["ref"]: e for e in out.receipt.effects}
    assert by_ref["S1"]["status"] == "paid"
    assert by_ref["S2"]["status"] == "part_paid" and by_ref["S2"]["remaining_paise"] == 2_300_000
    assert "still due" in out.receipt.summary


async def test_payment_replay_is_idempotent(seeded):
    p = await priya(seeded)
    prop, first = await propose_confirm(p, "rev_payment", {"refs": ["S5"], "amount": "50000", "settled": False})
    async with db.session_scope() as s:
        again = await proposals.confirm(s, p, prop.id, via="button")
    assert first.status == "executed" and again.status == "replayed" and again.receipt.id == first.receipt.id

    async with db.session_scope() as s:
        n = (await s.execute(select(func.count()).select_from(InvoicePayment).where(InvoicePayment.invoice_id == 5))).scalar_one()
    assert n == 1


async def test_edit_invoice_action_amount_and_notes(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_edit_invoice", {"ref": "S5", "amount": "200000", "notes": "revised scope"})
    assert out.status == "executed"
    eff = out.receipt.effects[0]
    assert eff["total_paise"] == 20_000_000 and eff["notes"] == "revised scope"


async def test_refresh_rate_action(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_refresh_rate", {"ref": seeded["northwind_nov_ref"]})
    assert out.status == "executed" and out.receipt.summary


async def test_delete_draft_action_and_non_draft_rejected(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_delete_draft", {"ref": "S13"})
    assert out.status == "executed" and out.receipt.effects[0]["type"] == "invoice_deleted"
    assert await run(seeded, lambda ss, rv: ss.get(Invoice, 13)) is None
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, p, "rev_delete_draft", {"ref": "S4"})
    assert e.value.code == BAD_STATUS


async def test_move_balance_action_lotus_balance_to_december(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_move_balance", {"ref": "S6", "to": "month", "month": "2026-12"})
    assert out.status == "executed"

    def go(ss, rv):
        s6 = row(ss, "S6")
        dest = ss.get(Invoice, s6.moved_to_id)
        return s6.status, s6.moved_paise, inv.billed_paise(s6), dest.kind, dest.total_paise, (dest.year, dest.month)

    assert await run(seeded, go) == ("paid", 2_720_000, 2_000_000, "balance", 2_720_000, (2026, 12))


async def test_client_actions_add_and_pause(seeded):
    p = await priya(seeded)
    _, a = await propose_confirm(p, "rev_client", {"op": "add", "client": "Brand New Ltd", "currency": "USD"})
    assert a.status == "executed" and a.receipt.effects[0]["currency"] == "USD"
    _, b = await propose_confirm(p, "rev_client", {"op": "pause", "client": "Patel Agro Exports"})
    assert b.status == "executed" and b.receipt.effects[0]["state"] == "paused"


async def test_set_cycle_action_builds_invoices(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_set_cycle", {"client": "Patel Agro Exports", "amount": "10000", "from": "2026-12",
                                                         "period_months": 1, "timing": "advance", "mode": "monthly"})
    assert out.status == "executed" and out.receipt.effects[0]["created"] >= 4  # Dec..Mar

    def go(ss, rv):
        c = cl.resolve(ss, rv, "Patel Agro Exports")
        return sorted((i.year, i.month) for i in inv.list_invoices(ss, rv, client_id=c.id) if i.status == "to_raise")[:2]

    assert await run(seeded, go) == [(2026, 12), (2027, 1)]


async def test_plan_fy_action_fills_next_year(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_plan_fy", {"client": "Kaveri Foods (synthetic)", "fy": "2027-28"})
    assert out.status == "executed" and len(out.receipt.effects) >= 1
    assert all(e["status"] == "to_raise" for e in out.receipt.effects)


async def test_fx_month_action_reprices_unpaid_invoices(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_fx_month", {"currency": "USD", "months": ["2026-11"], "rate": "85.00"})
    assert out.status == "executed"

    def go(ss, rv):
        nov = row(ss, seeded["northwind_nov_ref"])
        oct_ = row(ss, seeded["northwind_oct_ref"])
        return nov.total_paise, nov.fx_rate_micro, oct_.fx_rate_micro  # part-paid Oct keeps its rate

    assert await run(seeded, go) == (12_750_000, 85_000_000, 83_900_000)


async def test_end_project_none_ends_client_and_ignore_writes_off(seeded):
    p = await priya(seeded)
    _, a = await propose_confirm(p, "rev_end_project", {"client": "Kaveri Foods (synthetic)", "pending": "none"})
    assert a.status == "executed" and a.receipt.effects[0]["state"] == "ended"
    _, b = await propose_confirm(p, "rev_end_project", {"client": "Patel Agro Exports", "pending": "ignore", "ignore_from": "2026-11"})
    assert b.status == "executed"

    def go(ss, rv):
        s5 = row(ss, "S5")
        return s5.status, inv.billed_paise(s5), inv.outstanding_paise(s5)

    assert await run(seeded, go) == ("written_off", 0, 0)


async def test_stale_proposal_after_other_change_to_same_invoice(seeded):
    p = await priya(seeded)
    async with db.session_scope() as s:
        first = await proposals.create(s, p, "rev_payment", {"refs": ["S5"], "amount": "210000"})
    _, edit = await propose_confirm(p, "rev_edit_invoice", {"ref": "S5", "notes": "touched"})
    assert edit.status == "executed"
    async with db.session_scope() as s:
        out = await proposals.confirm(s, p, first.id, via="button")
    assert out.status == "stale" and out.new_proposal is not None and out.new_proposal.id != first.id

    def go(ss, rv):
        return row(ss, "S5").status

    assert await run(seeded, go) == "sent"  # the stale payment never ran


async def test_employee_forbidden_to_propose_and_read(seeded):
    arjun = await make_actor(seeded, "arjun")
    for kind, args in [("rev_payment", {"refs": ["S4"], "amount": "100"}), ("rev_client", {"op": "add", "client": "X"})]:
        async with db.session_scope() as s:
            with pytest.raises(DomainError) as e:
                await proposals.create(s, arjun, kind, args)
        assert e.value.code == FORBIDDEN
    from app.agent.tools import revenue as rt

    res, _ = await call(rt.get_revenue_overview, arjun)
    assert res["ok"] is False and res["code"] == FORBIDDEN
    res, _ = await call(rt.get_invoice, arjun, ref="S4")
    assert res["code"] == FORBIDDEN
    res, _ = await call(rt.mark_not_yet, arjun, ref="S2")
    assert res["code"] == FORBIDDEN


async def test_approver_tools_read_and_propose(seeded):
    from app.agent.tools import revenue as rt

    actor = await make_actor(seeded, "priya")
    res, _ = await call(rt.get_invoice, actor, ref="S6")
    assert res["ok"] is True and res["remaining_paise"] == 2_720_000
    res, _ = await call(rt.mark_not_yet, actor, ref="S2")
    assert res["ok"] is True and res["next_check"] == "2026-11-28"


async def test_seed_second_workspace_does_not_collide_on_fx_quote(seeded):
    async with db.session_scope() as s:
        await seed(s, workspace_name="Other Co (SYNTHETIC)", email_domain="other.demo")


async def test_invoice_ref_from_other_workspace_is_not_found(seeded):
    from sqlalchemy import delete

    from app.models import FxQuote

    async with db.session_scope() as s:
        await s.execute(delete(FxQuote))  # workaround for the seed collision above (global quote cache)
        other = await seed(s, workspace_name="Other Co", email_domain="other.test")
    foreign_ref = other["northwind_oct_ref"]  # exists, but in the other workspace

    def go(ss, rv):
        with pytest.raises(DomainError) as e:
            inv.by_ref(ss, rv, foreign_ref)
        with pytest.raises(DomainError) as e2:
            inv.invoice(ss, rv, int(foreign_ref[1:]))
        return code_of(e), code_of(e2)

    assert await run(seeded, go) == (NOT_FOUND, NOT_FOUND)

    p = await priya(seeded)
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, p, "rev_payment", {"refs": [foreign_ref], "amount": "100"})
    assert e.value.code == NOT_FOUND

    c = await client_for()
    r = await c.get(f"/api/revenue/invoices/{foreign_ref}")
    assert r.status_code == 404
    await c.aclose()


async def test_actions_write_audit_with_receipt(seeded):
    p = await priya(seeded)
    _, out = await propose_confirm(p, "rev_edit_invoice", {"ref": "S5", "notes": "audit me"})
    async with db.session_scope() as s:
        evs = (await s.execute(select(AuditEvent).where(AuditEvent.receipt_id == out.receipt.id,
                                                          AuditEvent.action.like("revenue.%")))).scalars().all()
    assert evs and all(e.receipt_id == out.receipt.id for e in evs)
    assert evs[0].after["channel"] == "assistant"


async def test_revenue_audit_rows_carry_proposal_id(seeded):
    p = await priya(seeded)
    prop, out = await propose_confirm(p, "rev_edit_invoice", {"ref": "S5", "notes": "audit me"})
    async with db.session_scope() as s:
        evs = (await s.execute(select(AuditEvent).where(AuditEvent.receipt_id == out.receipt.id,
                                                          AuditEvent.action.like("revenue.%")))).scalars().all()
    assert evs and all(e.proposal_id == prop.id for e in evs)


@pytest.mark.parametrize("kind,args", [
    ("rev_edit_invoice", {"ref": "S5", "notes": "pid check"}),
    ("rev_payment", {"refs": ["S4"], "amount": "82500", "received_on": "2026-11-21"}),
    ("rev_delete_draft", {"ref": "S13"}),
])
async def test_revenue_audit_proposal_id_matches_confirmed_proposal(seeded, kind, args):
    p = await priya(seeded)
    prop, out = await propose_confirm(p, kind, args)
    async with db.session_scope() as s:
        evs = (await s.execute(select(AuditEvent).where(AuditEvent.receipt_id == out.receipt.id,
                                                          AuditEvent.action.like("revenue.%")))).scalars().all()
    assert evs, "no revenue audit rows"
    assert {e.proposal_id for e in evs} == {prop.id}


# ---------------------------------------------------------------- 7. grounding


async def test_spoken_amount_grounded_and_ungrounded_rejected(seeded):
    actor = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        await record_turn(s, actor, "Nimbus se pachaas hazaar aaye", source="text")
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, "rev_payment", {"refs": ["S4"], "amount": "50000", "settled": False})
        assert p.kind == "rev_payment"
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, actor, "rev_payment", {"refs": ["S4"], "amount": "45000"})
    assert e.value.code == VALIDATION and e.value.details["ungrounded"] == "45000"


async def test_grounded_rate_and_amount_on_add_invoices(seeded):
    actor = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        await record_turn(s, actor, "raise 2,500 dollars for Northwind at 84.5", source="text")
    async with db.session_scope() as s:
        await proposals.create(s, actor, "rev_add_invoices", {"client": "Northwind", "amount": "2500", "months": ["2027-04"],
                                                              "currency": "USD", "rate": "84.5"})
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, actor, "rev_add_invoices", {"client": "Northwind", "amount": "2500", "months": ["2027-05"],
                                                                  "currency": "USD", "rate": "99.9"})
    assert e.value.code == VALIDATION and e.value.details["ungrounded"] == "99.9"


@pytest.mark.parametrize("words,value", [
    ("dedh lakh", 150_000), ("twelve thousand five hundred", 12_500), ("pachaas hazaar", 50_000),
    ("saade teen lakh", 350_000), ("2 lakh 10 hazaar", 210_000), ("1.5L", 150_000), ("50,000", 50_000),
    ("fifty thousand", 50_000),
    ("sawa lakh", 125_000), ("sawa do lakh", 225_000), ("ek lakh", 100_000),
])
def test_grounding_parses_spoken_numbers(words, value):
    assert grounding.said_in(value, words)


def test_sawa_lakh_is_not_100000():
    assert not grounding.said_in(100_000, "sawa lakh")
    assert not grounding.said_in(125_000, "ek lakh")


async def test_sawa_lakh_payment_grounded_for_125000_not_100000(seeded):
    actor = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        await record_turn(s, actor, "Nimbus se sawa lakh aaye", source="text")
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, "rev_payment", {"refs": ["S4"], "amount": "125000", "settled": False})
        assert p.kind == "rev_payment"
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, actor, "rev_payment", {"refs": ["S4"], "amount": "100000"})
    assert e.value.code == VALIDATION and e.value.details["ungrounded"] == "100000"


def test_grounding_does_not_confuse_numbers():
    assert not grounding.said_in(45_000, "pachaas hazaar")
    assert not grounding.said_in("abc", "fifty thousand")


async def test_no_conversation_skips_grounding(seeded):
    actor = await priya(seeded)
    async with db.session_scope() as s:
        p = await proposals.create(s, actor, "rev_payment", {"refs": ["S4"], "amount": "12345"})
    assert p.status == "open"


async def test_grounding_ignores_other_conversations_words(seeded):
    said = await make_actor(seeded, "priya")
    async with db.session_scope() as s:
        await record_turn(s, said, "pachaas hazaar", source="text")
    other = await make_actor(seeded, "priya")  # a different conversation
    async with db.session_scope() as s:
        with pytest.raises(DomainError) as e:
            await proposals.create(s, other, "rev_payment", {"refs": ["S4"], "amount": "50000"})
    assert e.value.code == VALIDATION


# ---------------------------------------------------------------- 8. API


async def test_overview_api_priya_gets_kpis_arjun_403(seeded):
    c = await client_for()
    r = await c.get("/api/revenue/overview")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kpis"]["paise"]["overdue"] == 34_055_000 and body["fy"] == FY and body["as_of"] == "2026-11-21"
    r = await c.get("/api/revenue/overview", params={"period": "q3"})
    assert r.status_code == 200 and body["kpis"]["paise"] != r.json()["kpis"]["paise"]
    r = await c.get("/api/revenue/invoices/S6")
    assert r.status_code == 200 and r.json()["remaining_paise"] == 2_720_000
    r = await c.get("/api/revenue/fx")
    assert r.status_code == 200
    await c.aclose()

    a = await client_for("arjun@purser.demo")
    for path in ("/api/revenue/overview", "/api/revenue/invoices/S6", "/api/revenue/fx"):
        assert (await a.get(path)).status_code == 403, path
    await a.aclose()


async def test_overview_api_bad_input_is_a_clean_error(seeded):
    c = await client_for()
    r = await c.get("/api/revenue/overview", params={"fy": "2026-99"})
    assert r.status_code in (409, 422), r.text
    r = await c.get("/api/revenue/invoices/S99999")
    assert r.status_code == 404
    await c.aclose()


async def test_overview_requires_login(seeded):
    import httpx

    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as c:
        assert (await c.get("/api/revenue/overview")).status_code == 401


# ---------------------------------------------------------------- 9. version bump


async def test_any_invoice_change_bumps_version(seeded):
    def go(ss, rv):
        i = mk_inr(ss, rv, mk_client(ss, rv), 5000)
        v0 = i.version
        send(ss, rv, i)
        ss.flush()
        v1 = i.version
        inv.update_invoice(ss, rv, i, notes="n")
        ss.flush()
        v2 = i.version
        inv.record_payment(ss, rv, i, amount_paise=100, received_on=TODAY, settled=False)
        ss.flush()
        return v0, v1, v2, i.version

    v0, v1, v2, v3 = await run(seeded, go)
    assert v0 < v1 < v2 < v3


async def test_client_change_bumps_party_version(seeded):
    def go(ss, rv):
        c = mk_client(ss, rv)
        v0 = c.version
        cl.set_client_state(ss, rv, c, "paused", on=TODAY)
        ss.flush()
        return v0, c.version

    v0, v1 = await run(seeded, go)
    assert v1 > v0


async def test_version_persists_across_sessions(seeded):
    async def version():
        async with db.session_scope() as s:
            return (await s.execute(select(Invoice.version).where(Invoice.ref == "S5"))).scalar_one()

    before = await version()
    await run(seeded, lambda ss, rv: inv.update_invoice(ss, rv, row(ss, "S5"), notes="bump"))
    assert await version() == before + 1


async def test_party_count_sanity(seeded):
    """Revenue clients are customer Parties in the same workspace table (no separate client table)."""
    async with db.session_scope() as s:
        n = (await s.execute(select(func.count()).select_from(Party).where(Party.kind == "customer",
                                                                            Party.workspace_id == seeded["workspace_id"]))).scalar_one()
    assert n >= 8
