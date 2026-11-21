"""Trips gate: hotel search normalisation, flight checkout_link, search_hotels/search_flights tools, flight+hotel booking
(pending_payment, payment links, on-behalf booking, email / Google routing). No network, no SMTP, no OpenAI."""

import re
from dataclasses import replace
from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import select, update

from app import db
from app.agent.tools import proposals as proposal_tools
from app.agent.tools import travel
from app.errors import FORBIDDEN, NOT_FOUND, VALIDATION
from app.models import FlightBooking, GoogleOp, HotelBooking, Message, ResultSnapshot, Trip, User
from app.services import confirmation, proposals
from app.services.records import today_ist
from app.services.travel import booking, flights, hotels
from tests.b25_helpers import FAKE_GOOGLE, LINKED, REAL_CLIENT, linked, pin
from tests.conftest import make_actor
from tests.test_intake_extra import call
from tests.test_ledger_gates import propose_and_confirm
from tests.test_people_extra import mail  # noqa: F401  (autouse safety fixture: no SMTP)


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    p = pin(monkeypatch, serpapi_api_key="", google_client_id="", google_client_secret="", google_refresh_token="", google_linked_email="")
    monkeypatch.setattr(hotels, "get_settings", lambda: p)
    flights._cache.clear()
    hotels._cache.clear()

    def no_net(*a, **k):
        if "transport" not in k:
            raise AssertionError("a trips test opened a real httpx client")
        return REAL_CLIENT(*a, **k)
    monkeypatch.setattr(httpx, "AsyncClient", no_net)
    yield
    flights._cache.clear()
    hotels._cache.clear()


def day(n=5) -> date:
    return today_ist() + timedelta(days=n)


def serp(monkeypatch, handler, key="k"):
    """Live-search mode: the SerpAPI key is set and every httpx client is wired to `handler`."""
    p = pin(monkeypatch, serpapi_api_key=key, google_client_id="", google_client_secret="", google_refresh_token="", google_linked_email="")
    monkeypatch.setattr(hotels, "get_settings", lambda: p)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: REAL_CLIENT(transport=httpx.MockTransport(handler), timeout=kw.get("timeout")))
    return p


async def one(model, *where):
    async with db.session_scope() as s:
        return list((await s.execute(select(model).where(*where).order_by(model.id))).scalars())


# ------------------------------------------------------------------ hotels.search

def prop(name="Taj", rate=5000, total=10000, **kw):
    p = {"name": name, "type": "hotel", "extracted_hotel_class": 4, "overall_rating": 4.5, "reviews": 1200,
         "rate_per_night": {"extracted_lowest": rate}, "total_rate": {"extracted_lowest": total},
         "images": [{"thumbnail": "https://img/t.jpg"}], "link": "https://taj.example/book",
         "amenities": ["Wi-Fi", "Pool", "Spa", "Gym", "Bar", "Parking", "Breakfast"],
         "nearby_places": [{"name": "Airport"}, {"name": "Beach"}, {"name": "Mall"}], "check_in_time": "2:00 PM"}
    p.update(kw)
    return p


async def test_hotels_serpapi_normalisation(monkeypatch):
    seen = []

    def handler(req):
        seen.append(dict(req.url.params))
        return httpx.Response(200, json={"search_metadata": {"google_hotels_url": "https://www.google.com/travel/hotels/x"}, "properties": [
            prop(),
            {"name": "No rate", "overall_rating": 4.0},  # dropped
            prop("Bad link", 3000, None, link="javascript:alert(1)", images=[]),
            prop("Ftp link", 2000, 4000, link="ftp://x"),
            prop("Http link", 1000, 2000, link="http://plain.example"),
            prop("Float rate", 1234.0, 2468.0),
        ]})

    serp(monkeypatch, handler)
    r = await hotels.search("Mumbai", day(5), day(7), adults=2)
    assert r["source"] == "serpapi" and r["note"] is None and r["nights"] == 2
    assert r["search_url"] == "https://www.google.com/travel/hotels/x"
    names = [o["name"] for o in r["options"]]
    assert names == ["Taj", "Bad link", "Ftp link", "Http link", "Float rate"]  # property without a rate dropped
    taj = r["options"][0]
    assert taj["price_per_night_inr"] == 5000 and taj["total_inr"] == 10000 and taj["image"] == "https://img/t.jpg"
    assert taj["link"] == "https://taj.example/book" and taj["amenities"] == ["Wi-Fi", "Pool", "Spa", "Gym", "Bar"]
    assert taj["stars"] == 4 and taj["rating"] == 4.5 and taj["nearby"] == ["Airport", "Beach"]
    bad = r["options"][1]
    assert bad["link"] is None and bad["image"] is None and bad["total_inr"] == 6000  # no total_rate -> rate * nights
    assert r["options"][2]["link"] is None and r["options"][3]["link"] == "http://plain.example"
    assert isinstance(r["options"][4]["price_per_night_inr"], int)
    (q,) = seen
    assert q["engine"] == "google_hotels" and q["check_in_date"] == day(5).isoformat() and q["check_out_date"] == day(7).isoformat() and q["adults"] == "2"


async def test_hotels_search_url_falls_back_to_google_hotels_when_metadata_missing(monkeypatch):
    serp(monkeypatch, lambda req: httpx.Response(200, json={"properties": [prop()]}))
    r = await hotels.search("Pune", day(5), day(6))
    assert r["search_url"] == hotels.google_hotels_url("Pune", day(5), day(6)) and r["search_url"].startswith("https://www.google.com/travel/hotels")


@pytest.mark.parametrize("resp", [
    httpx.Response(200, json={"error": "Invalid API key"}),
    httpx.Response(200, json={"properties": []}),
    httpx.Response(200, json={"properties": [{"name": "norate"}]}),
    httpx.Response(200, content=b"not json"),
])
async def test_hotels_failures_fall_back_to_sample(monkeypatch, resp):
    serp(monkeypatch, lambda req: resp)
    r = await hotels.search("Pune", day(5), day(7))
    assert r["note"] in ("Estimated rates: live hotel prices are unavailable right now. The hotel site shows the final price.",
                         "No hotels found for those dates by the live search.")
    assert r["source"] == "sample" and len(r["options"]) == 6 and all(o["name"].startswith("Pune ") and "(sample)" not in o["name"] for o in r["options"])
    assert r["search_url"].startswith("https://www.google.com/travel/hotels") and r["nights"] == 2


async def test_hotels_transport_error_falls_back(monkeypatch):
    def boom(req):
        raise httpx.ConnectError("down")
    serp(monkeypatch, boom)
    r = await hotels.search("Pune", day(5), day(6))
    assert r["source"] == "sample" and r["note"] == "Estimated rates: live hotel prices are unavailable right now. The hotel site shows the final price."


async def test_hotels_no_key_is_sample_and_makes_no_request():
    r = await hotels.search("Goa", day(5), day(8))  # isolate() forbids any real client
    assert r["source"] == "sample" and r["note"] == "Estimated rates: live hotel prices are unavailable right now. The hotel site shows the final price." and r["nights"] == 3
    assert all(o["total_inr"] == o["price_per_night_inr"] * 3 and o["link"] is None for o in r["options"])


async def test_hotels_nights_min_one_for_same_day_and_reversed():
    assert (await hotels.search("Goa", day(5), day(5)))["nights"] == 1
    assert (await hotels.search("Goa", day(5), day(3)))["nights"] == 1


async def test_hotels_live_result_cached_and_failure_not_cached(monkeypatch):
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(200, json={"properties": [prop()]})
    serp(monkeypatch, handler)
    await hotels.search("Pune", day(5), day(6))
    await hotels.search("pune", day(5), day(6))  # city key is case-insensitive
    assert len(calls) == 1
    await hotels.search("Pune", day(5), day(6), adults=2)
    assert len(calls) == 2


# ------------------------------------------------------------------ flights.search + checkout_link

def leg(**kw):
    d = {"airline": "IndiGo", "flight_number": "6E 123", "departure_airport": {"id": "DEL", "time": "2026-12-01 06:00"},
         "arrival_airport": {"id": "BOM", "time": "2026-12-01 08:10"}, "duration": 130, "travel_class": "Economy"}
    d.update(kw)
    return d


async def test_flight_options_carry_booking_token_and_search_url(monkeypatch):
    body = {"search_metadata": {"google_flights_url": "https://www.google.com/travel/flights/x"},
            "best_flights": [{"flights": [leg()], "total_duration": 130, "price": 5200, "booking_token": "TOK1"}],
            "other_flights": [{"flights": [leg()], "total_duration": 130, "price": 6200}]}
    serp(monkeypatch, lambda req: httpx.Response(200, json=body))
    r = await flights.search("DEL", "BOM", day())
    assert r["search_url"] == "https://www.google.com/travel/flights/x"
    assert [o["booking_token"] for o in r["options"]] == ["TOK1", None]


async def test_flights_sample_has_search_url():
    r = await flights.search("DEL", "BOM", day())
    assert r["source"] == "sample" and r["search_url"] == flights.google_flights_url("DEL", "BOM", day())


def fallback_url():
    return flights.google_flights_url("DEL", "BOM", day())


async def test_checkout_link_no_token_or_no_key_is_get_fallback(monkeypatch):
    for token in (None, ""):
        r = await flights.checkout_link("DEL", "BOM", day(), token)  # no key, no network
        assert r == {"method": "GET", "url": fallback_url(), "via": "Google Flights", "exact": False}
    serp(monkeypatch, lambda req: (_ for _ in ()).throw(AssertionError("no request without a token")))
    r = await flights.checkout_link("DEL", "BOM", day(), None)
    assert r["exact"] is False and r["method"] == "GET"
    pin(monkeypatch, serpapi_api_key="")
    r = await flights.checkout_link("DEL", "BOM", day(), "TOK")  # token but no key
    assert r["exact"] is False and r["url"] == fallback_url()


def booking_body(*opts):
    return {"booking_options": [{"together": o} for o in opts]}


async def test_checkout_link_prefers_airline_post(monkeypatch):
    seen = []

    def handler(req):
        seen.append(dict(req.url.params))
        return httpx.Response(200, json=booking_body(
            {"book_with": "MakeMyTrip", "price": 5000, "booking_request": {"url": "https://www.google.com/travel/clk/ota", "post_data": "a=1"}},
            {"book_with": "IndiGo", "airline": True, "price": 5200, "booking_request": {"url": "https://www.google.com/travel/clk/air", "post_data": "b=2"}}))
    serp(monkeypatch, handler)
    r = await flights.checkout_link("DEL", "BOM", day(), "TOK", adults=2)
    assert r == {"method": "POST", "url": "https://www.google.com/travel/clk/air", "post_data": "b=2", "via": "IndiGo", "price_inr": 5200, "exact": True}
    assert seen[0]["booking_token"] == "TOK" and seen[0]["adults"] == "2"


async def test_checkout_link_get_when_no_post_data_and_first_when_no_airline(monkeypatch):
    serp(monkeypatch, lambda req: httpx.Response(200, json=booking_body(
        {"book_with": "OTA", "price": 1, "booking_request": {"url": "https://www.google.com/travel/clk/ota"}})))
    r = await flights.checkout_link("DEL", "BOM", day(), "TOK")
    assert r["method"] == "GET" and r["url"] == "https://www.google.com/travel/clk/ota" and r["via"] == "OTA" and r["exact"] is True


@pytest.mark.parametrize("resp", [
    httpx.Response(200, json={}),
    httpx.Response(200, json={"booking_options": []}),
    httpx.Response(200, json=booking_body({"book_with": "Evil", "airline": True, "booking_request": {"url": "https://evil.example/x", "post_data": "p"}})),
    httpx.Response(200, json=booking_body({"book_with": "Evil", "booking_request": {"url": "http://www.google.com/x"}})),
    httpx.Response(200, json=booking_body({"book_with": "NoReq"})),
    httpx.Response(200, content=b"<html>"),
    httpx.Response(500, json={"error": "x"}),
])
async def test_checkout_link_bad_responses_fall_back_never_raise(monkeypatch, resp):
    serp(monkeypatch, lambda req: resp)
    r = await flights.checkout_link("DEL", "BOM", day(), "TOK")
    assert r == {"method": "GET", "url": fallback_url(), "via": "Google Flights", "exact": False}


async def test_checkout_link_transport_error_falls_back(monkeypatch):
    def boom(req):
        raise httpx.ConnectError("down")
    serp(monkeypatch, boom)
    r = await flights.checkout_link("DEL", "BOM", day(), "TOK")
    assert r["exact"] is False and r["method"] == "GET"


async def test_checkout_link_only_other_option_unsafe_picks_safe_one(monkeypatch):
    serp(monkeypatch, lambda req: httpx.Response(200, json=booking_body(
        {"book_with": "Evil", "airline": True, "booking_request": {"url": "https://evil.example/x", "post_data": "p"}},
        {"book_with": "OTA", "booking_request": {"url": "https://www.google.com/ok", "post_data": "q"}})))
    r = await flights.checkout_link("DEL", "BOM", day(), "TOK")
    assert r["url"] == "https://www.google.com/ok" and r["via"] == "OTA"


# ------------------------------------------------------------------ search_hotels tool

def fake_hotel_search(source="serpapi", nights=None, n=4):
    async def _s(city, ci, co, adults=1):
        _s.calls.append((city, ci, co, adults))
        opts = [{"name": f"{city} H{i}", "type": "hotel", "stars": 3 + i % 3, "rating": 3.5 + i * 0.3, "reviews": 100 * (i + 1),
                 "price_per_night_inr": 4000 - i * 500, "total_inr": (4000 - i * 500) * max(1, (co - ci).days), "image": None,
                 "link": f"https://h{i}.example" if i % 2 == 0 else None, "amenities": [], "nearby": [], "check_in_time": None} for i in range(n)]
        return {"source": source, "options": opts, "note": None if source == "serpapi" else "sample note",
                "nights": nights or max(1, (co - ci).days), "search_url": "https://www.google.com/travel/hotels?q=x"}
    _s.calls = []
    return _s


async def snap(sid):
    async with db.session_scope() as s:
        return await s.get(ResultSnapshot, sid)


async def test_search_hotels_stores_snapshot_and_card(seeded, monkeypatch):
    fs = fake_hotel_search()
    monkeypatch.setattr(hotels, "search", fs)
    a = await make_actor(seeded, "arjun")
    out, ctx = await call(travel.search_hotels, a, city="Bombay", check_in=day(5).isoformat(), check_out=day(8).isoformat(), adults=2)
    assert out["ok"] is True and fs.calls == [("Mumbai", day(5), day(8), 2)]  # alias resolved to the airport city
    assert out["nights"] == 3 and out["count"] == 4 and out["cheapest"]["price_per_night_inr"] == 2500
    assert out["best_rated"]["rating"] == max(o["rating"] for o in out["options"])
    sn = await snap(out["search_id"])
    assert sn.meta["kind"] == "hotels" and sn.meta["nights"] == 3 and sn.meta["search_url"] == "https://www.google.com/travel/hotels?q=x"
    assert sn.spec == {"city": "Mumbai", "check_in": day(5).isoformat(), "check_out": day(8).isoformat(), "adults": 2}
    assert sn.actor_id == a.user_id and [o["id"] for o in sn.rows] == [1, 2, 3, 4]
    (card,) = ctx.ui
    assert card["card"] == "hotel_options" and card["search_id"] == out["search_id"] and card["nights"] == 3 and len(card["options"]) == 4
    assert card["check_in"] == day(5).isoformat() and card["city"] == "Mumbai"


async def test_search_hotels_unknown_city_uses_title_cased_input(seeded, monkeypatch):
    fs = fake_hotel_search()
    monkeypatch.setattr(hotels, "search", fs)
    a = await make_actor(seeded, "arjun")
    out, _ = await call(travel.search_hotels, a, city="  shimla ", check_in=day(5).isoformat(), check_out=day(6).isoformat())
    assert out["ok"] and out["city"] == "Shimla" and fs.calls[0][0] == "Shimla"


@pytest.mark.parametrize("ci,co", [(-1, 2), (5, 5), (5, 4), (5, 36)])
async def test_search_hotels_date_validation(seeded, monkeypatch, ci, co):
    monkeypatch.setattr(hotels, "search", fake_hotel_search())
    a = await make_actor(seeded, "arjun")
    out, ctx = await call(travel.search_hotels, a, city="Pune", check_in=day(ci).isoformat(), check_out=day(co).isoformat())
    assert out["ok"] is False and out["code"] == VALIDATION and ctx.ui == []
    assert await one(ResultSnapshot) == []


async def test_search_hotels_boundaries_today_and_30_nights_ok(seeded, monkeypatch):
    fs = fake_hotel_search()
    monkeypatch.setattr(hotels, "search", fs)
    a = await make_actor(seeded, "arjun")
    out, _ = await call(travel.search_hotels, a, city="Pune", check_in=day(0).isoformat(), check_out=day(30).isoformat())
    assert out["ok"] is True and out["nights"] == 30


async def test_search_hotels_bad_date_format(seeded, monkeypatch):
    monkeypatch.setattr(hotels, "search", fake_hotel_search())
    a = await make_actor(seeded, "arjun")
    out, _ = await call(travel.search_hotels, a, city="Pune", check_in="next friday", check_out=day(6).isoformat())
    assert out["ok"] is False and out["code"] == VALIDATION


@pytest.mark.parametrize("adults,expected", [(0, 1), (-2, 1), (50, 6), (3, 3)])
async def test_search_hotels_adults_clamped(seeded, monkeypatch, adults, expected):
    fs = fake_hotel_search()
    monkeypatch.setattr(hotels, "search", fs)
    a = await make_actor(seeded, "arjun")
    await call(travel.search_hotels, a, city="Pune", check_in=day(5).isoformat(), check_out=day(6).isoformat(), adults=adults)
    assert fs.calls[0][3] == expected


async def test_search_hotels_sample_source_reported(seeded, monkeypatch):
    monkeypatch.setattr(hotels, "search", fake_hotel_search(source="sample"))
    a = await make_actor(seeded, "arjun")
    out, ctx = await call(travel.search_hotels, a, city="Pune", check_in=day(5).isoformat(), check_out=day(6).isoformat())
    assert out["source"] == "sample" and out["note"] == "sample note" and ctx.ui[0]["source"] == "sample"


# ------------------------------------------------------------------ search_flights card hides booking_token

def fake_flight_search(token="SECRET-TOKEN"):
    opts = [dict(o, best=i == 0, booking_token=f"{token}-{i}") for i, o in enumerate(flights._sample("DEL", "BOM", day()))]

    async def _s(origin, dest, d, adults=1):
        return {"source": "serpapi", "options": opts, "note": None, "search_url": "https://www.google.com/travel/flights?q=x"}
    return _s, opts


async def test_search_flights_card_and_result_hide_booking_token_but_snapshot_keeps_it(seeded, monkeypatch):
    fs, _ = fake_flight_search()
    monkeypatch.setattr(flights, "search", fs)
    a = await make_actor(seeded, "arjun")
    out, ctx = await call(travel.search_flights, a, destination="BOM", origin="DEL", depart_date=day().isoformat())
    assert out["ok"], out
    assert "SECRET-TOKEN" not in repr(out) and "SECRET-TOKEN" not in repr(ctx.ui)
    assert all("booking_token" not in o for o in ctx.ui[0]["options"])
    sn = await snap(out["search_id"])
    assert all(o["booking_token"].startswith("SECRET-TOKEN") for o in sn.rows)
    assert sn.meta["search_url"] == "https://www.google.com/travel/flights?q=x"


# ------------------------------------------------------------------ booking fixtures

def fake_checkout(monkeypatch, *, method="POST", url="https://www.google.com/travel/clk/abc", via="IndiGo", exact=True):
    calls = []

    async def _c(origin, dest, d, token, adults=1):
        calls.append((origin, dest, d, token, adults))
        return {"method": method, "url": url, "post_data": "x=1" if method == "POST" else None, "via": via, "price_inr": 5000, "exact": exact}
    monkeypatch.setattr(flights, "checkout_link", _c)
    return calls


async def seed_flight(actor, n=5, source="serpapi", token="TOK"):
    opts = [dict(o, id=i + 1, best=i == 0, booking_token=f"{token}{i}") for i, o in enumerate(flights._sample("DEL", "BOM", day(n)))]
    async with db.session_scope() as s:
        sn = ResultSnapshot(workspace_id=actor.workspace_id, conversation_id=actor.conversation_id, actor_id=actor.user_id,
                            spec={"origin": "DEL", "destination": "BOM", "date": day(n).isoformat(), "adults": 1}, rows=opts, totals={},
                            meta={"kind": "flights", "source": source, "note": None, "search_url": "https://www.google.com/travel/flights?q=x"})
        s.add(sn)
        await s.flush()
        return sn.id, opts


async def seed_hotel(actor, ci=5, co=8, source="serpapi", link="https://hotel.example/book"):
    rows = [{"id": 1, "name": "Taj Test", "type": "hotel", "stars": 5, "rating": 4.6, "reviews": 2000, "price_per_night_inr": 6000,
             "total_inr": 6000 * (co - ci), "image": None, "link": link, "amenities": ["Wi-Fi"], "nearby": [], "check_in_time": None},
            {"id": 2, "name": "Budget Inn", "type": "hotel", "stars": None, "rating": None, "reviews": None, "price_per_night_inr": 1500,
             "total_inr": 1500 * (co - ci), "image": None, "link": None, "amenities": [], "nearby": [], "check_in_time": None}]
    async with db.session_scope() as s:
        sn = ResultSnapshot(workspace_id=actor.workspace_id, conversation_id=actor.conversation_id, actor_id=actor.user_id,
                            spec={"city": "Mumbai", "check_in": day(ci).isoformat(), "check_out": day(co).isoformat(), "adults": 1}, rows=rows,
                            totals={}, meta={"kind": "hotels", "source": source, "note": None, "nights": co - ci,
                                             "search_url": "https://www.google.com/travel/hotels?q=mumbai"})
        s.add(sn)
        await s.flush()
        return sn.id, rows


async def new_trips():
    """Trips created by bookings (the seed has its own demo trip)."""
    return await one(Trip, Trip.purpose.like("Trip: %"))


async def set_notify(user_id, email):
    async with db.session_scope() as s:
        await s.execute(update(User).where(User.id == user_id).values(notify_email=email))


async def set_manager(user_id, manager_id):
    async with db.session_scope() as s:
        await s.execute(update(User).where(User.id == user_id).values(reports_to_id=manager_id))


async def book_trip(actor, **extra):
    return await propose_and_confirm(actor, "book_trip", extra)


# ------------------------------------------------------------------ book_flight / book_trip: self

async def test_book_flight_only_pending_payment_with_payment_link(seeded, monkeypatch):
    calls = fake_checkout(monkeypatch)
    a = await make_actor(seeded, "arjun")
    sid, opts = await seed_flight(a)
    _, out = await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": 2})
    assert out.status == "executed"
    assert calls == [("DEL", "BOM", day(5), "TOK1", 1)]  # the chosen option's token reaches checkout_link
    (b,) = await one(FlightBooking)
    assert re.fullmatch(r"PUR-\d{3}[A-Z]", b.ref) and b.status == "pending_payment" and b.user_id == a.user_id
    assert b.price_paise == opts[1]["price_inr"] * 100 and b.receipt_id == out.receipt.id and b.details["pay"] == {"via": "IndiGo", "exact": True}
    assert await one(HotelBooking) == []
    pays = [e for e in out.receipt.effects if e.get("type") == "payment_link"]
    assert len(pays) == 1 and pays[0]["what"] == "flight" and pays[0]["method"] == "POST" and pays[0]["url"].startswith("https://www.google.com/")
    assert pays[0]["post_data"] == "x=1" and pays[0]["exact"] is True and "IndiGo" in pays[0]["label"]
    assert {"type": "booking", "ref": b.ref} in out.receipt.effects
    assert not any(e.get("type") == "flight_booking" for e in out.receipt.effects)


async def test_book_trip_flight_and_hotel_records_trip_and_payment_links(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    a = await make_actor(seeded, "arjun")
    fsid, fopts = await seed_flight(a, n=5)
    hsid, hrows = await seed_hotel(a, ci=5, co=8)
    _, out = await book_trip(a, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1)
    assert out.status == "executed"
    (fb,), (hb,) = await one(FlightBooking), await one(HotelBooking)
    assert re.fullmatch(r"PUR-\d{3}[A-Z]", fb.ref) and re.fullmatch(r"HTL-\d{3}[A-Z]", hb.ref)
    assert fb.status == "pending_payment" and hb.status == "pending_payment"
    assert fb.user_id == hb.user_id == a.user_id
    assert (hb.hotel, hb.city, hb.nights, hb.total_paise) == ("Taj Test", "Mumbai", 3, 18000 * 100)
    assert hb.check_in == day(5) and hb.check_out == day(8) and hb.pay_url == "https://hotel.example/book"
    (trip,) = await new_trips()
    assert fb.trip_id == hb.trip_id == trip.id and trip.employee_party_id == a.party_id
    assert trip.start_date == day(5) and trip.end_date == day(8) and trip.city == "Mumbai"  # flight date .. check-out
    assert fb.ref in trip.purpose and hb.ref in trip.purpose
    pays = [e for e in out.receipt.effects if e.get("type") == "payment_link"]
    assert [p["what"] for p in pays] == ["flight", "hotel"]
    hp = pays[1]
    assert hp["method"] == "GET" and hp["url"] == "https://hotel.example/book" and hp["exact"] is True and "Taj Test" in hp["label"]
    total = fopts[0]["price_inr"] + 18000
    assert f"{total:,}" in out.receipt.summary or str(total) in out.receipt.summary.replace(",", "")


async def test_book_hotel_only_and_hotel_without_link_uses_search_url(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(a, ci=4, co=6)
    _, out = await book_trip(a, hotel_search_id=hsid, hotel_option_id=2)
    assert out.status == "executed"
    assert await one(FlightBooking) == []
    (hb,) = await one(HotelBooking)
    assert hb.pay_url == "https://www.google.com/travel/hotels?q=mumbai"
    (p,) = [e for e in out.receipt.effects if e.get("type") == "payment_link"]
    assert p["what"] == "hotel" and p["exact"] is False and p["url"] == hb.pay_url
    (trip,) = await new_trips()
    assert (trip.start_date, trip.end_date) == (day(4), day(6)) and hb.trip_id == trip.id


async def test_book_flight_fallback_checkout_is_get_and_not_exact(seeded, monkeypatch):
    fake_checkout(monkeypatch, method="GET", url="https://www.google.com/travel/flights?q=fallback", via="Google Flights", exact=False)
    a = await make_actor(seeded, "arjun")
    sid, _ = await seed_flight(a)
    _, out = await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": 1})
    (p,) = [e for e in out.receipt.effects if e.get("type") == "payment_link"]
    assert p["method"] == "GET" and p["exact"] is False and p["post_data"] is None
    (m,) = [m for m in await one(Message, Message.kind == "trip") if m.channel == "inbox"]
    assert "https://www.google.com/travel/flights?q=fallback" in m.body


async def test_post_checkout_email_body_uses_search_url_not_post_endpoint(seeded, monkeypatch):
    fake_checkout(monkeypatch, method="POST", url="https://www.google.com/travel/clk/POSTONLY")
    a = await make_actor(seeded, "arjun")
    sid, _ = await seed_flight(a)
    await propose_and_confirm(a, "book_flight", {"search_id": sid, "option_id": 1})
    (m,) = [m for m in await one(Message, Message.kind == "trip") if m.channel == "inbox"]
    assert "POSTONLY" not in m.body and "https://www.google.com/travel/flights?q=x" in m.body and "Reference: PUR-" in m.body


async def test_confirm_tool_shows_payment_card(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    a = await make_actor(seeded, "arjun")
    fsid, _ = await seed_flight(a)
    hsid, _ = await seed_hotel(a)
    out, ctx = await call(travel.propose_trip_booking, a, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1)
    assert out["ok"] is True and ctx.ui[-1]["card"] == "proposal"
    pid = ctx.ui[-1]["proposal_id"]
    async with db.session_scope() as s:
        await proposals.mark_presented(s, pid)
    async with db.session_scope() as s:
        await confirmation.record_turn(s, a, "yes, go ahead", source="text")
    out, ctx = await call(proposal_tools.confirm_pending_proposal, a)
    assert out["ok"] is True and out["status"] == "executed", out
    cards = {c["card"]: c for c in ctx.ui}
    assert {"receipt", "payment"} <= set(cards)
    pay = cards["payment"]
    assert pay["receipt"] == out["receipt"] and [i["what"] for i in pay["items"]] == ["flight", "hotel"]
    assert all(i["type"] == "payment_link" for i in pay["items"])


async def test_plan_lines_self_booking(seeded, monkeypatch):
    a = await make_actor(seeded, "arjun")
    fsid, fopts = await seed_flight(a, source="sample")
    hsid, _ = await seed_hotel(a)
    async with db.session_scope() as s:
        plan = await booking.BookTrip().plan(s, a, {"flight_search_id": fsid, "flight_option_id": 1, "hotel_search_id": hsid, "hotel_option_id": 1})
    assert plan.title == "Book trip" and any("(estimated fare)" in l for l in plan.lines)
    assert any("Trip total" in l for l in plan.lines)
    assert not any(l.startswith("Traveller:") for l in plan.lines)
    assert any("Purser takes no payment" in l for l in plan.lines) and any("hotel's website" in l for l in plan.lines)
    assert "Taj Test" in plan.speak and "?" in plan.speak


async def test_neither_flight_nor_hotel_is_validation(seeded):
    a = await make_actor(seeded, "arjun")
    out, ctx = await call(travel.propose_trip_booking, a)
    assert out["ok"] is False and out["code"] == VALIDATION and ctx.ui == []
    out, _ = await call(travel.propose_trip_booking, a, flight_search_id="x", hotel_option_id=1)  # ids without their pair
    assert out["code"] == VALIDATION


async def test_trip_other_users_search_is_not_found(seeded, monkeypatch):
    priya, arjun = await make_actor(seeded), await make_actor(seeded, "arjun")
    fsid, _ = await seed_flight(priya)
    hsid, _ = await seed_hotel(priya)
    out, _ = await call(travel.propose_trip_booking, arjun, flight_search_id=fsid, flight_option_id=1)
    assert out["ok"] is False and out["code"] == NOT_FOUND
    out, _ = await call(travel.propose_trip_booking, arjun, hotel_search_id=hsid, hotel_option_id=1)
    assert out["code"] == NOT_FOUND
    # a flights snapshot passed as a hotel search (wrong kind) is also not found
    afsid, _ = await seed_flight(arjun)
    out, _ = await call(travel.propose_trip_booking, arjun, hotel_search_id=afsid, hotel_option_id=1)
    assert out["code"] == NOT_FOUND


async def test_hotel_option_out_of_range_is_validation(seeded):
    a = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(a)
    out, _ = await call(travel.propose_trip_booking, a, hotel_search_id=hsid, hotel_option_id=9)
    assert out["ok"] is False and out["code"] == VALIDATION and "1 to 2" in out["message"]


async def test_ceo_cannot_propose_trip(seeded):
    priya = await make_actor(seeded)
    hsid, _ = await seed_hotel(priya)
    out, _ = await call(travel.propose_trip_booking, replace(priya, role="ceo"), hotel_search_id=hsid, hotel_option_id=1)
    assert out["ok"] is False and out["code"] == FORBIDDEN


async def test_trip_confirm_is_idempotent(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    a = await make_actor(seeded, "arjun")
    fsid, _ = await seed_flight(a)
    hsid, _ = await seed_hotel(a)
    p, out = await book_trip(a, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1)
    async with db.session_scope() as s:
        again = await proposals.confirm(s, a, p.id, via="button")
    assert again.status == "replayed"
    assert len(await one(FlightBooking)) == 1 and len(await one(HotelBooking)) == 1 and len(await new_trips()) == 1


async def test_list_my_flights_shows_pending_payment(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    a = await make_actor(seeded, "arjun")
    fsid, _ = await seed_flight(a)
    hsid, _ = await seed_hotel(a)
    await book_trip(a, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1)
    out, _ = await call(travel.list_my_flights, a)
    assert out["ok"] and {b["kind"] for b in out["bookings"]} == {"flight", "hotel"} and {b["status"] for b in out["bookings"]} == {"pending_payment"}


# ------------------------------------------------------------------ on-behalf booking

async def test_employee_cannot_book_for_non_report(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    arjun = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(arjun)
    out, _ = await call(travel.propose_trip_booking, arjun, hotel_search_id=hsid, hotel_option_id=1, for_user_id=seeded["neha_id"])
    assert out["ok"] is False and out["code"] == FORBIDDEN and "manager" in out["message"]
    assert await one(HotelBooking) == []


async def test_book_for_self_via_own_id_is_allowed_for_employee(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    arjun = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(arjun)
    out, _ = await call(travel.propose_trip_booking, arjun, hotel_search_id=hsid, hotel_option_id=1, for_user_id=arjun.user_id)
    assert out["ok"] is True


@pytest.mark.parametrize("role", ["admin", "hr_admin", "finance_approver"])
async def test_privileged_roles_can_book_for_others(seeded, monkeypatch, role):
    fake_checkout(monkeypatch)
    actor = replace(await make_actor(seeded, "arjun"), role=role)  # role comes from the Actor, not the DB row
    fsid, _ = await seed_flight(actor)
    hsid, _ = await seed_hotel(actor)
    _, out = await book_trip(actor, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1, for_user_id=seeded["neha_id"])
    assert out.status == "executed"
    (fb,), (hb,) = await one(FlightBooking), await one(HotelBooking)
    assert fb.user_id == hb.user_id == seeded["neha_id"]


async def test_manager_can_book_for_report_and_party_is_travellers(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    await set_manager(seeded["neha_id"], seeded["arjun_id"])  # Arjun (an employee) now manages Neha
    arjun = await make_actor(seeded, "arjun")
    fsid, _ = await seed_flight(arjun)
    hsid, _ = await seed_hotel(arjun, ci=5, co=7)
    _, out = await book_trip(arjun, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1, for_user_id=seeded["neha_id"])
    assert out.status == "executed"
    (fb,), (hb,), (trip,) = await one(FlightBooking), await one(HotelBooking), await new_trips()
    assert fb.user_id == hb.user_id == seeded["neha_id"]
    async with db.session_scope() as s:
        neha_party = (await s.get(User, seeded["neha_id"])).party_id
    assert trip.employee_party_id == neha_party and trip.employee_party_id != arjun.party_id
    assert fb.trip_id == trip.id == hb.trip_id


async def test_on_behalf_plan_first_line_names_traveller_and_booker(seeded, monkeypatch):
    priya = await make_actor(seeded)
    hsid, _ = await seed_hotel(priya)
    async with db.session_scope() as s:
        plan = await booking.BookTrip().plan(s, priya, {"hotel_search_id": hsid, "hotel_option_id": 1, "for_user_id": seeded["arjun_id"]})
    assert plan.lines[0] == f"Traveller: Arjun Mehta (booked by {priya.display_name})" and "for Arjun Mehta" in plan.speak


async def test_on_behalf_inbox_to_traveller_and_booker_and_email_to_notify_address(seeded, monkeypatch, mail):
    fake_checkout(monkeypatch)
    mail.enable("arjun.mail@example.test")
    await set_notify(seeded["arjun_id"], "arjun.mail@example.test")
    priya = await make_actor(seeded)
    fsid, _ = await seed_flight(priya)
    hsid, _ = await seed_hotel(priya)
    _, out = await book_trip(priya, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1, for_user_id=seeded["arjun_id"])
    assert out.status == "executed"
    msgs = await one(Message, Message.kind == "trip")
    inbox = sorted(m.recipient_user_id for m in msgs if m.channel == "inbox")
    assert inbox == sorted([seeded["arjun_id"], priya.user_id])
    (em,) = [m for m in msgs if m.channel == "email"]
    assert em.email_to == "arjun.mail@example.test" and em.status == "queued" and em.recipient_user_id is None
    assert "has booked this trip for you" in em.body and em.body.startswith("Hi Arjun,")
    assert await one(GoogleOp) == []


async def test_self_booking_inbox_is_single_copy(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    arjun = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(arjun)
    await book_trip(arjun, hotel_search_id=hsid, hotel_option_id=1)
    msgs = [m for m in await one(Message, Message.kind == "trip") if m.channel == "inbox"]
    assert [m.recipient_user_id for m in msgs] == [arjun.user_id]


# ------------------------------------------------------------------ email routing

async def test_explicit_email_to_wins_over_notify_email(seeded, monkeypatch, mail):
    fake_checkout(monkeypatch)
    mail.enable("*")
    await set_notify(seeded["arjun_id"], "on-file@example.test")
    arjun = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(arjun)
    await book_trip(arjun, hotel_search_id=hsid, hotel_option_id=1, email_to="  Boss@Example.TEST ")
    (em,) = [m for m in await one(Message, Message.kind == "trip") if m.channel == "email"]
    assert em.email_to == "boss@example.test" and em.status == "queued"


@pytest.mark.parametrize("bad", ["not-an-email", "a@b", "two words@x.com", "@x.com"])
async def test_bad_email_to_is_validation(seeded, bad):
    arjun = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(arjun)
    out, _ = await call(travel.propose_trip_booking, arjun, hotel_search_id=hsid, hotel_option_id=1, email_to=bad)
    assert out["ok"] is False and out["code"] == VALIDATION and "email" in out["message"].lower()


async def test_no_email_anywhere_only_inbox(seeded, monkeypatch):
    fake_checkout(monkeypatch)
    await set_notify(seeded["arjun_id"], None)
    arjun = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(arjun)
    async with db.session_scope() as s:
        plan = await booking.BookTrip().plan(s, arjun, {"hotel_search_id": hsid, "hotel_option_id": 1})
    assert any("no email address on file" in l for l in plan.lines)
    _, out = await book_trip(arjun, hotel_search_id=hsid, hotel_option_id=1)
    assert out.status == "executed"
    assert [m.channel for m in await one(Message, Message.kind == "trip")] == ["inbox"]
    assert "in your Purser inbox" in out.receipt.summary


async def test_email_skipped_when_email_not_configured_or_not_allowlisted(seeded, monkeypatch, mail):
    fake_checkout(monkeypatch)
    await set_notify(seeded["arjun_id"], "arjun.mail@example.test")
    arjun = await make_actor(seeded, "arjun")
    hsid, _ = await seed_hotel(arjun)
    await book_trip(arjun, hotel_search_id=hsid, hotel_option_id=1)  # mail fixture: email not configured
    (em,) = [m for m in await one(Message, Message.kind == "trip") if m.channel == "email"]
    assert em.status == "skipped" and em.status_detail == "email_not_configured"
    mail.enable("someone-else@example.test")
    hsid2, _ = await seed_hotel(arjun)
    await book_trip(arjun, hotel_search_id=hsid2, hotel_option_id=1)
    ems = [m for m in await one(Message, Message.kind == "trip") if m.channel == "email"]
    assert ems[-1].status == "skipped" and ems[-1].status_detail == "not_on_allowlist"


# ------------------------------------------------------------------ Google-linked actor

async def test_google_linked_self_booking_sends_from_gmail_and_creates_events(seeded, monkeypatch, mail):
    pin(monkeypatch, **FAKE_GOOGLE)
    fake_checkout(monkeypatch)
    a = linked(await make_actor(seeded))
    fsid, _ = await seed_flight(a)
    hsid, _ = await seed_hotel(a)
    async with db.session_scope() as s:
        plan = await booking.BookTrip().plan(s, a, {"flight_search_id": fsid, "flight_option_id": 1, "hotel_search_id": hsid, "hotel_option_id": 1})
    assert any(LINKED in l and "Gmail" in l for l in plan.lines) and any("Calendar holds" in l for l in plan.lines)
    _, out = await book_trip(a, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1)
    assert out.status == "executed"
    ops = await one(GoogleOp)
    assert [o.kind for o in ops] == ["send_email", "create_event", "create_event"]
    send = ops[0]
    assert send.payload["sender"] == LINKED and send.payload["to"] == [LINKED] and send.payload["cc"] == []
    assert "Trip approved" in send.payload["subject"] and "payment" in send.payload["subject"]
    assert all(o.status == "queued" and o.ref == f"G{o.id}" and o.user_id == a.user_id for o in ops)
    assert "✈" in ops[1].payload["title"] and "🏨" in ops[2].payload["title"] and ops[1].payload["start"] < ops[1].payload["end"]
    assert not [m for m in await one(Message, Message.kind == "trip") if m.channel == "email"]  # Gmail path, no SMTP message


async def test_google_linked_on_behalf_cc_booker_and_no_events(seeded, monkeypatch, mail):
    pin(monkeypatch, **FAKE_GOOGLE)
    fake_checkout(monkeypatch)
    await set_notify(seeded["arjun_id"], "arjun.mail@example.test")
    a = linked(await make_actor(seeded))
    fsid, _ = await seed_flight(a)
    hsid, _ = await seed_hotel(a)
    _, out = await book_trip(a, flight_search_id=fsid, flight_option_id=1, hotel_search_id=hsid, hotel_option_id=1, for_user_id=seeded["arjun_id"])
    assert out.status == "executed"
    ops = await one(GoogleOp)
    assert [o.kind for o in ops] == ["send_email"]  # no calendar events on someone else's behalf
    p = ops[0].payload
    assert p["sender"] == LINKED and p["to"] == ["arjun.mail@example.test"] and p["cc"] == [LINKED]
    assert "has booked this trip for you" in p["body"]


async def test_google_linked_on_behalf_to_own_address_has_no_self_cc(seeded, monkeypatch):
    pin(monkeypatch, **FAKE_GOOGLE)
    fake_checkout(monkeypatch)
    a = linked(await make_actor(seeded))
    hsid, _ = await seed_hotel(a)
    _, out = await book_trip(a, hotel_search_id=hsid, hotel_option_id=1, for_user_id=seeded["arjun_id"], email_to=LINKED.upper())
    assert out.status == "executed"
    (send,) = await one(GoogleOp)
    assert send.payload["to"] == [LINKED] and send.payload["cc"] == []


async def test_google_linked_booking_with_no_email_resolved_skips_send(seeded, monkeypatch):
    pin(monkeypatch, **FAKE_GOOGLE)
    fake_checkout(monkeypatch)
    await set_notify(seeded["arjun_id"], None)
    a = linked(await make_actor(seeded))
    hsid, _ = await seed_hotel(a)
    _, out = await book_trip(a, hotel_search_id=hsid, hotel_option_id=1, for_user_id=seeded["arjun_id"])
    assert out.status == "executed" and await one(GoogleOp) == []


async def test_non_linked_actor_never_creates_google_ops(seeded, monkeypatch):
    pin(monkeypatch, **FAKE_GOOGLE)  # Google configured, but arjun's email is not the linked one
    fake_checkout(monkeypatch)
    a = await make_actor(seeded, "arjun")
    fsid, _ = await seed_flight(a)
    await propose_and_confirm(a, "book_flight", {"search_id": fsid, "option_id": 1})
    assert await one(GoogleOp) == []
