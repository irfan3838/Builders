"""Hindi-number grounding, workflow flight/hotel search memory, and the part-payment summary wording.
No network, no OpenAI."""

import unicodedata
from datetime import date

import pytest

from app import db
from app.agent.workflows import engine
from app.config import get_settings
from app.services.revenue import invoices as inv
from app.services.revenue.core import Rev
from app.services.revenue.grounding import numbers_spoken, said_in
from app.services.revenue_actions import RecordPayment
from tests.test_revenue_fx_cycles import R, mk_client, mk_invoice

TODAY = date(2026, 11, 21)


# ------------------------------------------------------------------ 1. grounding
@pytest.mark.parametrize("value,text", [
    (210000, "दो लाख दस हज़ार"),
    (201000, "नहीं नहीं, दो लाख एक हज़ार आए"),
    (150000, "डेढ़ लाख"),
    (350000, "साढ़े तीन लाख"),
    (125000, "सवा लाख"),
    (50000, "पचास हजार"),
    (210000, "2 लाख 10 हज़ार"),
    (210000, "do lakh das hazaar"),
    (210000, "2,10,000"),
    (210000, "2.1 lakh"),
    (210000, "210k"),
    (210000, "two lakh ten thousand"),
])
def test_said_in_positive(value, text):
    assert said_in(value, text), (text, numbers_spoken(text))


@pytest.mark.parametrize("value,text", [
    (210000, "दो लाख दस हज़ार"),
    (201000, "नहीं नहीं, दो लाख एक हज़ार आए"),
    (150000, "डेढ़ लाख"),
    (350000, "साढ़े तीन लाख"),
    (50000, "पचास हजार"),
])
def test_said_in_nfd_decomposed_forms(value, text):
    assert said_in(value, unicodedata.normalize("NFD", text))


def test_different_number_not_said():
    assert not said_in(210000, "दो लाख एक हज़ार")
    assert not said_in(201000, "दो लाख दस हज़ार")
    assert not said_in(150000, "साढ़े तीन लाख")


def test_plain_devanagari_without_numbers_yields_nothing():
    assert numbers_spoken("नमस्ते, कैसे हैं आप") == set()
    assert not said_in(1000, "नमस्ते, कैसे हैं आप")


# ------------------------------------------------------------------ 2. workflow search memory
def _flight_card(sid="f1", n=8, **kw):
    c = {"card": "flight_options", "search_id": sid, "origin": {"iata": "DEL"}, "destination": {"iata": "BOM"},
         "date": "2026-12-01", "source": "sample", "note": "",
         "options": [{"id": i, "airline": "Air India", "flight_no": f"AI{i}", "depart_time": "09:25", "price_inr": 5000 + i}
                     for i in range(n)]}
    c.update(kw)
    return c


def _hotel_card(sid="h1", n=8, **kw):
    c = {"card": "hotel_options", "search_id": sid, "city": "Pune", "check_in": "2026-12-01", "check_out": "2026-12-03",
         "nights": 2, "source": "sample", "note": "",
         "options": [{"id": i, "name": f"Hotel {i}", "price_per_night_inr": 3000 + i} for i in range(n)]}
    c.update(kw)
    return c


def test_remember_flight_and_hotel():
    st: dict = {}
    engine._remember_searches(st, [_flight_card(), _hotel_card()])
    fs, hs = st["flight_search"], st["hotel_search"]
    assert fs["search_id"] == "f1" and fs["route"] == "DEL->BOM" and fs["date"] == "2026-12-01"
    assert hs["search_id"] == "h1" and hs["city"] == "Pune" and hs["dates"] == "2026-12-01 to 2026-12-03"
    assert "Air India" in fs["options"][0] and "Rs5000" in fs["options"][0]
    assert "Hotel 0" in hs["options"][0] and "Rs3000/night" in hs["options"][0]


def test_options_capped_at_six():
    st: dict = {}
    engine._remember_searches(st, [_flight_card(n=10), _hotel_card(n=10)])
    assert len(st["flight_search"]["options"]) == 6 and len(st["hotel_search"]["options"]) == 6


def test_later_search_overwrites_earlier():
    st: dict = {}
    engine._remember_searches(st, [_flight_card("f1"), _hotel_card("h1")])
    engine._remember_searches(st, [_flight_card("f2", destination={"iata": "BLR"}), _hotel_card("h2", city="Goa")])
    assert st["flight_search"]["search_id"] == "f2" and st["flight_search"]["route"] == "DEL->BLR"
    assert st["hotel_search"]["search_id"] == "h2" and st["hotel_search"]["city"] == "Goa"
    # two cards in one turn: the last wins
    engine._remember_searches(st, [_flight_card("f3"), _flight_card("f4")])
    assert st["flight_search"]["search_id"] == "f4"


def test_cards_without_search_id_or_unrelated_are_ignored():
    st: dict = {}
    engine._remember_searches(st, [_flight_card(sid=None), _hotel_card(sid=""), {"card": "suggestions", "items": []},
                                   {"card": "invoice_table", "search_id": "x"}])
    assert st == {}
    st = {"flight_search": {"search_id": "keep"}}
    engine._remember_searches(st, [_flight_card(sid=None)])
    assert st["flight_search"]["search_id"] == "keep"


def test_brief_includes_searches_and_is_unchanged_without():
    assert engine._brief({}, None) == "(new conversation)"
    st = {"memo": ["did x"]}
    base = engine._brief(st, None, "note!")
    assert "search_id" not in base and base.endswith("note!")
    engine._remember_searches(st, [_flight_card(), _hotel_card()])
    b = engine._brief(st, None, "note!")
    assert "Last flight search shown (search_id=f1" in b and "DEL->BOM" in b
    assert "Last hotel search shown (search_id=h1" in b and "Pune" in b
    assert b.index("Last flight search") < b.index("Last hotel search") < b.index("note!")
    only_f: dict = {}
    engine._remember_searches(only_f, [_flight_card()])
    assert "Last hotel search" not in engine._brief(only_f, None)


# ------------------------------------------------------------------ 3. part-payment summary
@pytest.fixture
def pinned(monkeypatch):
    monkeypatch.setenv("FX_PROVIDER", "fixture")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_part_payment_summary_is_user_facing(seeded, pinned):
    rv = Rev(seeded["workspace_id"], seeded["priya_id"], TODAY, "ui")

    def go(ss):
        c = mk_client(ss, rv)
        i = mk_invoice(ss, rv, c, 10_000 * R, (2026, 10))
        inv.set_status(ss, rv, i, "sent", on=date(2026, 10, 2))
        ref = i.ref
        out = RecordPayment().run(ss, rv, {"refs": [ref], "amount": "4000", "received_on": "2026-11-01", "settled": False})
        return ref, out.summary

    async with db.session_scope() as s:
        ref, summary = await s.run_sync(go)
    assert "Ask the user" not in summary
    assert f"({ref})" not in summary
    assert "still due" in summary
    assert "Should I leave it outstanding" in summary and summary.rstrip().endswith("?")
