"""B4/B5 gate: airports, flight search normalisation, search_flights tool, simulated booking, location API, affirmation."""

from dataclasses import replace
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select

from app import db
from app.agent.tools import travel
from app.errors import FORBIDDEN, NOT_FOUND, VALIDATION
from app.models import FlightBooking, GoogleOp, Message, ResultSnapshot, Trip, User
from app.services import proposals
from app.services.affirmation import Affirmation, classify
from app.services.records import today_ist
from app.services.travel import airports, booking, flights
from tests.b25_helpers import FAKE_GOOGLE, LINKED, REAL_CLIENT, linked, pin
from tests.conftest import make_actor
from tests.test_api_intake import client_for
from tests.test_intake_extra import call
from tests.test_ledger_gates import propose_and_confirm
from tests.test_people_extra import mail  # noqa: F401  (autouse safety fixture: no SMTP)


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    pin(monkeypatch, serpapi_api_key="", google_client_id="", google_client_secret="", google_refresh_token="", google_linked_email="")
    flights._cache.clear()

    def no_net(*a, **k):
        if "transport" not in k:
            raise AssertionError("a travel test opened a real httpx client")
        return REAL_CLIENT(*a, **k)
    monkeypatch.setattr(httpx, "AsyncClient", no_net)
    yield
    flights._cache.clear()


def day(n=5) -> date:
    return today_ist() + timedelta(days=n)


# ------------------------------------------------------------------ airports


@pytest.mark.parametrize("text,iata", [
    ("Mumbai", "BOM"), ("Bombay", "BOM"), ("bombay", "BOM"), ("BOM", "BOM"), ("bom", "BOM"), ("Bangalore", "BLR"), ("Bengaluru", "BLR"),
    ("Bangalore airport", "BLR"), ("Madras", "MAA"), ("Calcutta", "CCU"), ("New Delhi", "DEL"), ("Gurgaon", "DEL"), ("  delhi ", "DEL"),
    ("Poona", "PNQ"), ("Goa", "GOI"), ("North Goa", "GOX"), ("Vizag", "VTZ"), ("Cochin", "COK"), ("Dubai", "DXB"),
    ("Chhatrapati Shivaji International Mumbai", "BOM")])
def test_resolve_aliases(text, iata):
    assert airports.resolve(text)["iata"] == iata


@pytest.mark.parametrize("text", ["Paris", "Tokyo", "", "   ", "Atlantis", "12345"])
def test_resolve_unknown(text):
    assert airports.resolve(text) is None


def test_resolve_view_shape():
    assert airports.resolve("Bombay") == {"iata": "BOM", "city": "Mumbai", "airport": "Chhatrapati Shivaji Maharaj International"}


@pytest.mark.xfail(strict=True, reason="BUG: resolve() substring-matches aliases inside the user's text: resolve('Goalpara') returns GOI (Goa) "
                   "because alias 'goa' in 'goalpara'; an unknown city silently becomes another airport instead of 'ask the user'")
def test_resolve_does_not_match_alias_inside_other_word():
    assert airports.resolve("Goalpara") is None


@pytest.mark.parametrize("lat,lon,iata", [(19.07, 72.87, "BOM"), (13.08, 80.27, "MAA"), (18.52, 73.85, "PNQ"), (12.97, 77.59, "BLR"),
                                          (28.61, 77.21, "DEL"), (22.57, 88.36, "CCU"), (17.38, 78.48, "HYD"), (1.35, 103.8, "SIN"), (51.5, -0.12, "LHR")])
def test_nearest(lat, lon, iata):
    n = airports.nearest(lat, lon)
    assert n["iata"] == iata and isinstance(n["distance_km"], int) and n["distance_km"] < 80


def test_nearest_exact_airport_is_zero_and_far_point_still_answers():
    bom = airports.BY_CODE["BOM"]
    assert airports.nearest(bom[3], bom[4])["distance_km"] == 0
    far = airports.nearest(-33.9, 151.2)  # Sydney: nothing close, still returns the closest known
    assert far["iata"] in airports.BY_CODE and far["distance_km"] > 1000


# ------------------------------------------------------------------ flights.search


def leg(airline="IndiGo", no="6E 123", frm="DEL", to="BOM", dep="2026-12-01 06:00", arr="2026-12-01 08:10", dur=130):
    return {"airline": airline, "flight_number": no, "departure_airport": {"id": frm, "time": dep}, "arrival_airport": {"id": to, "time": arr},
            "duration": dur, "travel_class": "Economy"}


BODY = {
    "best_flights": [
        {"flights": [leg()], "total_duration": 130, "price": 5200, "airline_logo": "http://logo/6e.png"},
        {"flights": [leg("Air India", "AI 101", dep="2026-12-01 09:25", arr="2026-12-01 11:35")], "total_duration": 130, "price": 6100},
        {"flights": [leg("Vistara", "UK 1", dep="2026-12-01 10:00", arr="2026-12-01 12:00")], "total_duration": 120},  # no price
    ],
    "other_flights": [
        {"flights": [leg("Akasa Air", "QP 1", "DEL", "HYD", "2026-12-01 05:00", "2026-12-01 07:00", 120),
                     leg("Akasa Air", "QP 2", "HYD", "BOM", "2026-12-01 08:30", "2026-12-01 10:00", 90)],
         "layovers": [{"id": "HYD", "name": "Hyderabad"}], "total_duration": 300, "price": 4100.0},
        {"flights": [leg("IndiGo", "6E 5", "DEL", "AMD", "2026-12-01 20:00", "2026-12-02 00:10", 250),
                     leg("Air India", "AI 9", "AMD", "BOM", "2026-12-02 01:00", "2026-12-02 02:00", 60)], "price": 3900,
         "layovers": [{"name": "Ahmedabad"}]},
    ],
}


def serp(monkeypatch, handler, key="k"):
    pin(monkeypatch, serpapi_api_key=key, google_client_id="", google_client_secret="", google_refresh_token="", google_linked_email="")
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), timeout=kw.get("timeout")))


async def test_serpapi_normalisation(monkeypatch):
    seen = []

    def handler(req):
        seen.append(dict(req.url.params))
        return httpx.Response(200, json=BODY)
    serp(monkeypatch, handler)
    r = await flights.search("DEL", "BOM", date(2026, 12, 1), adults=2)
    p = seen[0]
    assert p["engine"] == "google_flights" and p["departure_id"] == "DEL" and p["arrival_id"] == "BOM" and p["outbound_date"] == "2026-12-01"
    assert p["currency"] == "INR" and p["adults"] == "2" and p["type"] == "2" and p["api_key"] == "k"
    assert r["source"] == "serpapi" and r["note"] is None
    o = r["options"]
    assert len(o) == 4  # the option without a price is dropped
    assert [x["best"] for x in o] == [True, True, False, False]
    assert [x["airline"] for x in o] == ["IndiGo", "Air India", "Akasa Air", "IndiGo + Air India"]
    first = o[0]
    assert first["price_inr"] == 5200 and first["depart_time"] == "06:00" and first["arrive_time"] == "08:10" and first["stops"] == 0
    assert first["flight_no"] == "6E 123" and first["from"] == "DEL" and first["to"] == "BOM" and first["duration_min"] == 130
    assert first["logo"] == "http://logo/6e.png" and first["layovers"] == [] and first["depart"] == "2026-12-01 06:00"
    multi = o[2]
    assert multi["stops"] == 1 and multi["layovers"] == ["HYD"] and multi["flight_no"] == "QP 1, QP 2" and multi["duration_min"] == 300
    assert multi["to"] == "BOM" and multi["from"] == "DEL" and isinstance(multi["price_inr"], int) and multi["price_inr"] == 4100
    last = o[3]  # no total_duration: summed from legs; overnight arrival keeps both dates
    assert last["duration_min"] == 310 and last["layovers"] == ["Ahmedabad"] and last["arrive"] == "2026-12-02 02:00"


async def test_serpapi_caps_options_at_15(monkeypatch):
    many = {"best_flights": [{"flights": [leg(no=f"6E {i}")], "total_duration": 100, "price": 1000 + i} for i in range(20)]}
    serp(monkeypatch, lambda req: httpx.Response(200, json=many))
    r = await flights.search("DEL", "BOM", date(2026, 12, 1))
    assert len(r["options"]) == 15 and r["options"][0]["price_inr"] == 1000


@pytest.mark.parametrize("resp", [
    httpx.Response(200, json={"error": "Invalid API key"}),
    httpx.Response(429, json={"error": "rate limited"}),
    httpx.Response(500, text="<html>bad gateway</html>"),
    httpx.Response(200, text="not json")])
async def test_serpapi_error_falls_back_to_sample(monkeypatch, resp):
    serp(monkeypatch, lambda req: resp)
    r = await flights.search("DEL", "BOM", date(2026, 12, 1))
    assert r["source"] == "sample" and "SAMPLE" in r["note"] and len(r["options"]) == 6
    assert all(o["from"] == "DEL" and o["to"] == "BOM" for o in r["options"])


async def test_serpapi_transport_error_falls_back(monkeypatch):
    def boom(req):
        raise httpx.ConnectError("down")
    serp(monkeypatch, boom)
    r = await flights.search("DEL", "BOM", date(2026, 12, 1))
    assert r["source"] == "sample" and "SAMPLE" in r["note"]


async def test_serpapi_empty_result_falls_back_with_note(monkeypatch):
    serp(monkeypatch, lambda req: httpx.Response(200, json={"best_flights": [], "other_flights": [{"flights": [leg()]}]}))
    r = await flights.search("DEL", "BOM", date(2026, 12, 1))
    assert r["source"] == "sample" and "No flights found" in r["note"]


async def test_no_key_is_sample_and_makes_no_request(monkeypatch):
    r = await flights.search("DEL", "BOM", date(2026, 12, 1))
    assert r["source"] == "sample" and "not configured" in r["note"] and "SAMPLE" in r["note"]


async def test_sample_shape_and_determinism():
    a = await flights.search("BOM", "DEL", date(2026, 12, 1))
    b = await flights.search("BOM", "DEL", date(2026, 12, 1))
    c = await flights.search("BOM", "DEL", date(2026, 12, 2))
    assert a == b and a != c
    for o in a["options"]:
        assert o["depart"].startswith("2026-12-01") and 3800 <= o["price_inr"] < 9000 and o["duration_min"] > 0
        assert o["best"] if "best" in o else True
        assert set(o) >= {"airline", "flight_no", "depart", "arrive", "depart_time", "arrive_time", "from", "to", "duration_min", "stops",
                          "layovers", "price_inr", "cabin", "overnight"}
        assert len(o["depart_time"]) == 5 and o["stops"] == len(o["layovers"])


async def test_serpapi_results_are_cached_by_route_date_adults(monkeypatch):
    n = []

    def handler(req):
        n.append(1)
        return httpx.Response(200, json=BODY)
    serp(monkeypatch, handler)
    a = await flights.search("DEL", "BOM", date(2026, 12, 1))
    b = await flights.search("DEL", "BOM", date(2026, 12, 1))
    assert a is b and len(n) == 1
    await flights.search("DEL", "BOM", date(2026, 12, 1), adults=2)
    await flights.search("DEL", "BOM", date(2026, 12, 2))
    await flights.search("BOM", "DEL", date(2026, 12, 1))
    assert len(n) == 4


async def test_failure_is_not_cached_so_next_call_recovers(monkeypatch):
    state = {"ok": False}

    def handler(req):
        return httpx.Response(200, json=BODY) if state["ok"] else httpx.Response(500, text="x")
    serp(monkeypatch, handler)
    assert (await flights.search("DEL", "BOM", date(2026, 12, 1)))["source"] == "sample"
    state["ok"] = True
    assert (await flights.search("DEL", "BOM", date(2026, 12, 1)))["source"] == "serpapi"


# ------------------------------------------------------------------ search_flights tool


def fake_search(source="serpapi", note=None):
    opts = [dict(o, **{"best": i == 0}) for i, o in enumerate(flights._sample("DEL", "BOM", day()))]

    async def _s(origin, dest, d, adults=1):
        _s.calls.append((origin, dest, d, adults))
        return {"source": source, "options": opts, "note": note}
    _s.calls = []
    _s.opts = opts
    return _s


async def snap(search_id):
    async with db.session_scope() as s:
        return await s.get(ResultSnapshot, search_id)


async def test_search_flights_success_stores_snapshot(seeded, monkeypatch):
    fs = fake_search()
    monkeypatch.setattr(flights, "search", fs)
    a = await make_actor(seeded, "arjun")
    out, ctx = await call(travel.search_flights, a, destination="Bombay", origin="Delhi", depart_date=day().isoformat(), adults=2)
    assert out["ok"] is True and fs.calls == [("DEL", "BOM", day(), 2)]
    assert out["to"]["iata"] == "BOM" and out["from"]["iata"] == "DEL" and out["origin_from"] == "named by the user" and out["count"] == 6
    ids = [o["id"] for o in out["options"]]
    assert ids == [1, 2, 3, 4, 5, 6]
    assert out["cheapest"]["price_inr"] == min(o["price_inr"] for o in fs.opts) and out["fastest"]["duration_min"] == min(o["duration_min"] for o in fs.opts)
    sn = await snap(out["search_id"])
    assert sn.meta["kind"] == "flights" and sn.meta["source"] == "serpapi" and sn.actor_id == a.user_id and sn.conversation_id == a.conversation_id
    assert sn.spec == {"origin": "DEL", "destination": "BOM", "date": day().isoformat(), "adults": 2}
    assert [o["id"] for o in sn.rows] == ids
    (card,) = ctx.ui
    assert card["card"] == "flight_options" and card["search_id"] == out["search_id"] and len(card["options"]) == 6 and card["destination"]["iata"] == "BOM"


@pytest.mark.parametrize("adults,expected", [(0, 1), (-3, 1), (99, 6), (3, 3)])
async def test_adults_clamped(seeded, monkeypatch, adults, expected):
    fs = fake_search()
    monkeypatch.setattr(flights, "search", fs)
    out, _ = await call(travel.search_flights, await make_actor(seeded), destination="BOM", origin="DEL", depart_date=day().isoformat(), adults=adults)
    assert out["ok"] and fs.calls[0][3] == expected


async def test_search_validation(seeded, monkeypatch):
    fs = fake_search()
    monkeypatch.setattr(flights, "search", fs)
    a = await make_actor(seeded)
    d = day().isoformat()
    cases = [
        (dict(destination="BOM", origin="DEL", depart_date=(today_ist() - timedelta(days=1)).isoformat()), "in the past"),
        (dict(destination="Atlantis", origin="DEL", depart_date=d), "don't know an airport for 'Atlantis'"),
        (dict(destination="BOM", origin="Atlantis", depart_date=d), "don't know an airport for 'Atlantis'"),
        (dict(destination="Mumbai", origin="Bombay", depart_date=d), "both Mumbai"),
        (dict(destination="BOM", origin="DEL", depart_date="next week"), "YYYY-MM-DD"),
        (dict(destination="BOM", origin="DEL", depart_date="2026-13-45"), "YYYY-MM-DD"),
    ]
    for args, msg in cases:
        out, ctx = await call(travel.search_flights, a, **args)
        assert out["ok"] is False and out["code"] == VALIDATION and msg in out["message"], (args, out)
        assert ctx.ui == []
    assert fs.calls == []
    async with db.session_scope() as s:
        assert (await s.execute(select(ResultSnapshot))).scalars().all() == []


async def test_search_today_is_allowed(seeded, monkeypatch):
    monkeypatch.setattr(flights, "search", fake_search())
    out, _ = await call(travel.search_flights, await make_actor(seeded), destination="BOM", origin="DEL", depart_date=today_ist().isoformat())
    assert out["ok"] is True


async def test_no_origin_no_location(seeded, monkeypatch):
    fs = fake_search()
    monkeypatch.setattr(flights, "search", fs)
    a = await make_actor(seeded)
    out, ctx = await call(travel.search_flights, a, destination="BOM", depart_date=day().isoformat())
    assert out["ok"] is False and out["code"] == "NO_LOCATION" and fs.calls == [] and ctx.ui == []
    out, _ = await call(travel.get_my_location, a)
    assert out["ok"] is False and out["code"] == "NO_LOCATION"


async def test_origin_defaults_to_stored_location(seeded, monkeypatch):
    fs = fake_search()
    monkeypatch.setattr(flights, "search", fs)
    a = await make_actor(seeded)
    async with db.session_scope() as s:
        u = await s.get(User, a.user_id)
        u.last_lat, u.last_lon = 13.08, 80.27  # Chennai
    out, _ = await call(travel.get_my_location, a)
    assert out["ok"] and out["nearest_airport"]["iata"] == "MAA"
    out, _ = await call(travel.search_flights, a, destination="Mumbai", depart_date=day().isoformat())
    assert out["ok"] and out["from"]["iata"] == "MAA" and out["origin_from"] == "the user's current location" and fs.calls[0][:2] == ("MAA", "BOM")
    out, _ = await call(travel.search_flights, a, destination="Chennai", depart_date=day().isoformat())
    assert out["ok"] is False and out["code"] == VALIDATION  # stored location resolves to the destination


async def test_search_resets_flight_clarify_count(seeded, monkeypatch):
    from app.agent.tools import clarify
    monkeypatch.setattr(flights, "search", fake_search())
    a = await make_actor(seeded)
    await clarify.bump(a, "flight")
    await clarify.bump(a, "flight")
    await call(travel.search_flights, a, destination="BOM", origin="DEL", depart_date=day().isoformat())
    assert await clarify.current(a, "flight") == 0


async def test_sample_source_is_reported_to_the_agent(seeded):
    out, ctx = await call(travel.search_flights, await make_actor(seeded), destination="BOM", origin="DEL", depart_date=day().isoformat())
    assert out["ok"] and out["source"] == "sample" and "SAMPLE" in out["note"] and "sample fares" in out["say"]
    assert ctx.ui[0]["source"] == "sample"


# ------------------------------------------------------------------ booking


async def do_search(actor, monkeypatch, source="serpapi", n=0):
    monkeypatch.setattr(flights, "search", fake_search(source=source, note=None if source == "serpapi" else "sample note"))
    out, _ = await call(travel.search_flights, actor, destination="BOM", origin="DEL", depart_date=day(5 + n).isoformat())
    assert out["ok"], out
    return out["search_id"], out["options"]


async def one(model, *where):
    async with db.session_scope() as s:
        return list((await s.execute(select(model).where(*where).order_by(model.id))).scalars())


async def test_booking_plan_is_labelled_simulated(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    sid, opts = await do_search(a, monkeypatch)
    async with db.session_scope() as s:
        plan = await booking.BookFlight().plan(s, a, {"search_id": sid, "option_id": 2})
    assert plan.title == "Book flight"
    assert any(booking.PAY_NOTE in l for l in plan.lines) and any("Purser takes no payment" in l for l in plan.lines)
    assert any(f"{opts[1]['airline']} {opts[1]['flight_no']}" in l for l in plan.lines)
    assert any("live Google Flights fare" in l for l in plan.lines)
    assert plan.speak.startswith("Approve ") and plan.speak.endswith("?")


async def test_booking_plan_flags_sample_fare(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    sid, _ = await do_search(a, monkeypatch, source="sample")
    async with db.session_scope() as s:
        plan = await booking.BookFlight().plan(s, a, {"search_id": sid, "option_id": 1})
    assert any("estimated fare" in l for l in plan.lines)


async def test_book_flight_confirm_creates_records(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    sid, opts = await do_search(a, monkeypatch)
    o = opts[2]
    full = (await snap(sid)).rows[2]
    _, out = await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": o["id"]})
    assert out.status == "executed"
    (b,) = await one(FlightBooking)
    import re
    assert re.fullmatch(r"PUR-\d{3}[A-Z]", b.ref), b.ref
    assert b.user_id == a.user_id and b.status == "pending_payment" and b.source == "serpapi"
    assert (b.origin, b.destination) == (full["from"], full["to"]) and b.flight_no == full["flight_no"] and b.airline == full["airline"]
    assert b.price_paise == full["price_inr"] * 100 and b.depart_at == full["depart"] and b.receipt_id == out.receipt.id
    assert b.details["cabin"] == "Economy"
    (trip,) = await one(Trip, Trip.purpose.contains(b.ref))
    assert b.trip_id == trip.id and trip.employee_party_id == a.party_id and b.ref in trip.purpose and trip.city == "Mumbai"
    msgs = await one(Message, Message.kind == "flight")
    inbox = [m for m in msgs if m.channel == "inbox"]
    assert len(inbox) == 1 and inbox[0].recipient_user_id == a.user_id and b.ref in inbox[0].subject and "Purser takes no payment" in inbox[0].body
    assert "complete payment" in inbox[0].subject
    assert await one(GoogleOp) == []  # not the linked login: no Google traffic
    assert b.ref in out.receipt.summary and "Trip approved" in out.receipt.summary
    kinds = [e["type"] for e in out.receipt.effects]
    assert kinds == ["payment_link", "booking"]
    pay = out.receipt.effects[0]
    assert pay["what"] == "flight" and pay["method"] == "GET" and pay["url"].startswith("https://www.google.com/") and pay["exact"] is False
    assert out.receipt.effects[1] == {"type": "booking", "ref": b.ref}


async def test_booking_confirm_is_idempotent(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    sid, _ = await do_search(a, monkeypatch)
    p, out = await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": 1})
    async with db.session_scope() as s:
        again = await proposals.confirm(s, a, p.id, via="button")
    assert again.status == "replayed"
    assert len(await one(FlightBooking)) == 1


async def test_booking_refs_are_unique(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    sid, _ = await do_search(a, monkeypatch)
    await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": 1})
    await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": 2})
    refs = [b.ref for b in await one(FlightBooking)]
    assert len(set(refs)) == 2
    out, _ = await call(travel.list_my_flights, a)
    assert out["ok"] and [b["ref"] for b in out["bookings"]] == refs[::-1]
    assert out["bookings"][0]["price"].startswith("₹") and out["bookings"][0]["status"] == "pending_payment"


async def test_booking_for_linked_user_queues_two_google_ops(seeded, monkeypatch):
    pin(monkeypatch, **FAKE_GOOGLE)
    a = linked(await make_actor(seeded, "priya"))
    sid, opts = await do_search(a, monkeypatch)
    async with db.session_scope() as s:
        plan = await booking.BookFlight().plan(s, a, {"search_id": sid, "option_id": 1})
    assert any("Calendar holds" in l for l in plan.lines) and any(LINKED in l for l in plan.lines)
    _, out = await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": 1})
    assert out.status == "executed"
    ops = await one(GoogleOp)
    assert [o.kind for o in ops] == ["send_email", "create_event"] and all(o.status == "queued" and o.ref == f"G{o.id}" for o in ops)
    (b,) = await one(FlightBooking)
    send, create = ops
    assert send.payload["to"] == [LINKED] and send.payload["sender"] == LINKED and b.ref in send.payload["subject"] and "Purser takes no payment" in send.payload["body"]
    assert create.payload["start"] < create.payload["end"] and b.ref in create.payload["description"] and "Payment on the airline site" in create.payload["description"]
    assert opts[0]["airline"] in create.payload["title"]
    inbox = [m for m in await one(Message, Message.kind == "flight") if m.channel == "inbox"]
    assert len(inbox) == 1  # inbox copy only; the email goes through Gmail, not SMTP


async def test_booking_option_not_in_search_is_validation(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    sid, _ = await do_search(a, monkeypatch)
    out, _ = await call(travel.propose_flight_booking, a, search_id=sid, option_id=99)
    assert out["ok"] is False and out["code"] == VALIDATION and "1 to 6" in out["message"]
    out, _ = await call(travel.propose_flight_booking, a, search_id=sid, option_id=0)
    assert out["code"] == VALIDATION
    assert await one(FlightBooking) == []


async def test_booking_another_users_search_is_not_found(seeded, monkeypatch):
    priya, arjun = await make_actor(seeded), await make_actor(seeded, "arjun")
    sid, _ = await do_search(priya, monkeypatch)
    out, ctx = await call(travel.propose_flight_booking, arjun, search_id=sid, option_id=1)
    assert out["ok"] is False and out["code"] == NOT_FOUND and ctx.ui == []
    out, _ = await call(travel.propose_flight_booking, arjun, search_id="does-not-exist", option_id=1)
    assert out["code"] == NOT_FOUND


async def test_booking_non_flight_snapshot_is_not_found(seeded):
    a = await make_actor(seeded, "arjun")
    async with db.session_scope() as s:
        sn = ResultSnapshot(workspace_id=a.workspace_id, conversation_id=a.conversation_id, actor_id=a.user_id, spec={}, rows=[{"id": 1}], totals={}, meta={"kind": "chart"})
        s.add(sn)
        await s.flush()
        sid = sn.id
    out, _ = await call(travel.propose_flight_booking, a, search_id=sid, option_id=1)
    assert out["ok"] is False and out["code"] == NOT_FOUND


async def test_ceo_cannot_propose_booking(seeded, monkeypatch):
    priya = await make_actor(seeded)
    sid, _ = await do_search(priya, monkeypatch)
    ceo = replace(priya, role="ceo")
    out, _ = await call(travel.propose_flight_booking, ceo, search_id=sid, option_id=1)
    assert out["ok"] is False and out["code"] == FORBIDDEN
    assert await one(FlightBooking) == []


async def test_propose_flight_booking_shows_proposal_card(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    sid, _ = await do_search(a, monkeypatch)
    out, ctx = await call(travel.propose_flight_booking, a, search_id=sid, option_id=3)
    assert out["ok"] is True and ctx.ui[-1]["card"] == "proposal"
    assert await one(FlightBooking) == []  # proposing books nothing


# ------------------------------------------------------------------ POST /api/me/location


async def test_location_api_stores_and_returns_nearest(seeded):
    c = await client_for("arjun@purser.demo")
    r = await c.post("/api/me/location", json={"lat": 19.07, "lon": 72.87})
    assert r.status_code == 200 and r.json()["nearest_airport"]["iata"] == "BOM"
    async with db.session_scope() as s:
        u = (await s.execute(select(User).where(User.email == "arjun@purser.demo"))).scalars().one()
        assert (u.last_lat, u.last_lon) == (19.07, 72.87) and u.last_loc_at is not None
    r = await c.post("/api/me/location", json={"lat": 28.6, "lon": 77.2})
    assert r.json()["nearest_airport"]["iata"] == "DEL"
    # and the tool now defaults to it
    from tests.test_intake_extra import call as _call
    a = await make_actor(seeded, "arjun")
    out, _ = await _call(travel.get_my_location, a)
    assert out["ok"] and out["nearest_airport"]["iata"] == "DEL"


@pytest.mark.parametrize("body", [{"lat": 91, "lon": 0}, {"lat": 0, "lon": 181}, {"lat": -91, "lon": 0}, {"lat": "x", "lon": 0}, {"lat": 1}, {}])
async def test_location_api_rejects_bad_input(seeded, body):
    c = await client_for("arjun@purser.demo")
    assert (await c.post("/api/me/location", json=body)).status_code == 422
    async with db.session_scope() as s:
        u = (await s.execute(select(User).where(User.email == "arjun@purser.demo"))).scalars().one()
        assert u.last_lat is None


async def test_location_api_requires_login_and_csrf(seeded):
    from app.main import app
    async with REAL_CLIENT(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000", headers={"origin": "http://localhost:8000"}) as c:
        assert (await c.post("/api/me/location", json={"lat": 1, "lon": 1})).status_code == 401
    c = await client_for("arjun@purser.demo")
    del c.headers["x-csrf-token"]
    assert (await c.post("/api/me/location", json={"lat": 1, "lon": 1})).status_code == 403


# ------------------------------------------------------------------ affirmation (new phrases)


@pytest.mark.parametrize("t", ["approve", "Approve!", "book it", "Book it.", "yes, approve", "ok book it", "yes please book it", "send it", "do that"])
def test_affirm_new_phrases(t):
    assert classify(t) == Affirmation.AFFIRM


@pytest.mark.parametrize("t,want", [("don't book it", Affirmation.NEGATIVE), ("no approve", Affirmation.NEGATIVE), ("book it for tomorrow", Affirmation.AMBIGUOUS),
                                    ("approve but change the date", Affirmation.AMBIGUOUS), ("book the 9:25 one", Affirmation.AMBIGUOUS),
                                    ("approved by whom", Affirmation.AMBIGUOUS), ("", Affirmation.AMBIGUOUS)])
def test_not_affirm(t, want):
    assert classify(t) == want


# ------------------------------------------------------------------ checkout_link (payment hand-off)


async def test_checkout_link_without_token_or_key_is_google_flights_search():
    r = await flights.checkout_link("DEL", "BOM", date(2026, 12, 1), None)
    assert r["method"] == "GET" and r["via"] == "Google Flights" and r["exact"] is False and r["url"].startswith("https://www.google.com/")
    r2 = await flights.checkout_link("DEL", "BOM", date(2026, 12, 1), "tok")  # token but no SerpAPI key: still no request
    assert r2 == r


async def test_checkout_link_prefers_airline_and_survives_errors(monkeypatch):
    body = {"booking_options": [
        {"together": {"book_with": "MakeMyTrip", "price": 5000, "booking_request": {"url": "https://www.google.com/travel/clk/f", "post_data": "u=1"}}},
        {"together": {"book_with": "IndiGo", "airline": True, "price": 5200, "booking_request": {"url": "https://www.google.com/travel/clk/g", "post_data": "u=2"}}},
        {"together": {"book_with": "Evil", "booking_request": {"url": "https://evil.example/pay"}}}]}
    serp(monkeypatch, lambda req: httpx.Response(200, json=body))
    r = await flights.checkout_link("DEL", "BOM", date(2026, 12, 1), "tok")
    assert r["via"] == "IndiGo" and r["method"] == "POST" and r["post_data"] == "u=2" and r["exact"] is True
    serp(monkeypatch, lambda req: httpx.Response(200, json={"booking_options": [{"together": {"booking_request": {"url": "https://evil.example/pay"}}}]}))
    assert (await flights.checkout_link("DEL", "BOM", date(2026, 12, 1), "tok"))["exact"] is False  # non-Google URLs are rejected

    def boom(req):
        raise httpx.ConnectError("down")
    serp(monkeypatch, boom)
    assert (await flights.checkout_link("DEL", "BOM", date(2026, 12, 1), "tok"))["exact"] is False
    serp(monkeypatch, lambda req: httpx.Response(200, text="not json"))
    assert (await flights.checkout_link("DEL", "BOM", date(2026, 12, 1), "tok"))["exact"] is False
