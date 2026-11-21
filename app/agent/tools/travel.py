"""Travel tools: where the user is, live flight search, and a (simulated) booking through propose -> confirm."""

from __future__ import annotations

from datetime import date

from agents import RunContextWrapper, function_tool

from app import db
from app.agent.context import PurserContext, safe_tool
from app.agent.tools.clarify import bump
from app.agent.tools.proposals import _propose
from app.errors import VALIDATION, DomainError
from app.models import ResultSnapshot, User
from app.services.records import today_ist
from app.services.travel import airports, booking, flights, hotels

Ctx = RunContextWrapper[PurserContext]


async def _here(actor) -> dict | None:
    async with db.session_scope() as s:
        u = await s.get(User, actor.user_id)
    if u is None or u.last_lat is None or u.last_lon is None:
        return None
    return airports.nearest(u.last_lat, u.last_lon)


@function_tool
@safe_tool
async def get_my_location(ctx: Ctx) -> dict:
    """The user's current city and nearest airport, from the location their browser shared. Use it as the flight origin
    when they do not name one, and say it back ("flying from Chennai, right?")."""
    near = await _here(ctx.context.actor)
    if near is None:
        return {"ok": False, "code": "NO_LOCATION", "message": "Location is not shared. Ask which city they fly from (ask_choice with a few likely cities)."}
    return {"ok": True, "nearest_airport": near}


@function_tool
@safe_tool
async def search_flights(ctx: Ctx, destination: str, depart_date: str, origin: str | None = None, adults: int = 1) -> dict:
    """Search one-way flights and show them as a list (airline, times, duration, stops, price), best first.
    destination/origin: a city or IATA code ('Mumbai', 'BOM'). origin defaults to the user's current location.
    depart_date: YYYY-MM-DD. If the user gave a vague date ('next week'), first ask which day with ask_choice
    (topic='flight', kind='date', values YYYY-MM-DD). Speak the count, the cheapest and the fastest; then ask which to book."""
    a = ctx.context.actor
    dest = airports.resolve(destination)
    if dest is None:
        raise DomainError(VALIDATION, f"I don't know an airport for '{destination}'. Ask the user for the city.")
    if origin:
        org = airports.resolve(origin)
        if org is None:
            raise DomainError(VALIDATION, f"I don't know an airport for '{origin}'.")
        how = "named by the user"
    else:
        org = await _here(a)
        if org is None:
            return {"ok": False, "code": "NO_LOCATION", "message": "No origin and no shared location. Ask where they fly from."}
        how = "the user's current location"
    if org["iata"] == dest["iata"]:
        raise DomainError(VALIDATION, f"Origin and destination are both {dest['city']}.")
    try:
        day = date.fromisoformat(depart_date)
    except ValueError:
        raise DomainError(VALIDATION, "depart_date must be YYYY-MM-DD; resolve the user's words to a date first.") from None
    if day < today_ist():
        raise DomainError(VALIDATION, "That date is in the past.")
    adults = max(1, min(int(adults), 6))
    res = await flights.search(org["iata"], dest["iata"], day, adults=adults)
    opts = [{"id": i + 1, **o} for i, o in enumerate(res["options"])]
    async with db.session_scope() as s:
        snap = ResultSnapshot(workspace_id=a.workspace_id, conversation_id=a.conversation_id, actor_id=a.user_id,
                              spec={"origin": org["iata"], "destination": dest["iata"], "date": day.isoformat(), "adults": adults},
                              rows=opts, totals={}, meta={"kind": "flights", "source": res["source"], "note": res["note"],
                                                         "search_url": res.get("search_url")})
        s.add(snap)
        await s.flush()
        sid = snap.id
    await bump(a, "flight", reset=True)
    public = [{k: v for k, v in o.items() if k != "booking_token"} for o in opts]
    ctx.context.show({"card": "flight_options", "search_id": sid, "origin": org, "destination": dest, "date": day.isoformat(),
                      "source": res["source"], "note": res["note"], "options": public})
    cheapest = min(opts, key=lambda o: o["price_inr"]) if opts else None
    fastest = min(opts, key=lambda o: o["duration_min"]) if opts else None
    brief = lambda o: {k: o[k] for k in ("id", "airline", "flight_no", "depart_time", "arrive_time", "duration_min", "stops", "price_inr")}  # noqa: E731
    return {"ok": True, "search_id": sid, "from": org, "origin_from": how, "to": dest, "date": day.isoformat(), "source": res["source"],
            "note": res["note"], "count": len(opts), "cheapest": brief(cheapest) if cheapest else None,
            "fastest": brief(fastest) if fastest else None, "options": [brief(o) for o in opts[:8]],
            "say": "If source is 'sample', say these are estimated fares because live prices are unavailable right now. Prices are in rupees."}


@function_tool
@safe_tool
async def propose_flight_booking(ctx: Ctx, search_id: str, option_id: int, for_user_id: int | None = None,
                                 email_to: str | None = None) -> dict:
    """Propose booking one option from search_flights ('book the cheapest', 'the 9:25 Air India', 'option 3').
    After the user approves, Purser records it, emails the itinerary and shows a Pay button that opens the airline's own
    checkout for that exact flight (payment happens there). For flight + hotel together use propose_trip_booking."""
    return await _propose(ctx, "book_flight", {"search_id": search_id, "option_id": option_id, "for_user_id": for_user_id,
                                               "email_to": email_to})


@function_tool
@safe_tool
async def search_hotels(ctx: Ctx, city: str, check_in: str, check_out: str, adults: int = 1) -> dict:
    """Search hotels for a stay (live Google Hotels rates): name, stars, rating, price per night, stay total, amenities.
    check_in / check_out: YYYY-MM-DD (for a trip, check_in = the flight date). Speak the count, the best-rated and the
    cheapest; then ask which to book."""
    a = ctx.context.actor
    try:
        ci, co = date.fromisoformat(check_in), date.fromisoformat(check_out)
    except ValueError:
        raise DomainError(VALIDATION, "Dates must be YYYY-MM-DD; resolve the user's words first.") from None
    if ci < today_ist() or co <= ci:
        raise DomainError(VALIDATION, "Check-in must be today or later and check-out after check-in.")
    if (co - ci).days > 30:
        raise DomainError(VALIDATION, "Stays longer than 30 nights are not supported.")
    place = airports.resolve(city)
    name = place["city"].split(" (")[0] if place else city.strip().title()
    adults = max(1, min(int(adults), 6))
    res = await hotels.search(name, ci, co, adults=adults)
    opts = [{"id": i + 1, **o} for i, o in enumerate(res["options"])]
    async with db.session_scope() as s:
        snap = ResultSnapshot(workspace_id=a.workspace_id, conversation_id=a.conversation_id, actor_id=a.user_id,
                              spec={"city": name, "check_in": ci.isoformat(), "check_out": co.isoformat(), "adults": adults},
                              rows=opts, totals={}, meta={"kind": "hotels", "source": res["source"], "note": res["note"],
                                                         "nights": res["nights"], "search_url": res["search_url"]})
        s.add(snap)
        await s.flush()
        sid = snap.id
    ctx.context.show({"card": "hotel_options", "search_id": sid, "city": name, "check_in": ci.isoformat(), "check_out": co.isoformat(),
                      "nights": res["nights"], "source": res["source"], "note": res["note"], "options": opts})
    brief = lambda o: {k: o.get(k) for k in ("id", "name", "stars", "rating", "price_per_night_inr", "total_inr")}  # noqa: E731
    best = max(opts, key=lambda o: (o.get("rating") or 0, -(o["price_per_night_inr"]))) if opts else None
    cheap = min(opts, key=lambda o: o["price_per_night_inr"]) if opts else None
    return {"ok": True, "search_id": sid, "city": name, "nights": res["nights"], "source": res["source"], "note": res["note"],
            "count": len(opts), "best_rated": brief(best) if best else None, "cheapest": brief(cheap) if cheap else None,
            "options": [brief(o) for o in opts[:8]]}


@function_tool
@safe_tool
async def propose_trip_booking(ctx: Ctx, flight_search_id: str | None = None, flight_option_id: int | None = None,
                               hotel_search_id: str | None = None, hotel_option_id: int | None = None,
                               for_user_id: int | None = None, email_to: str | None = None) -> dict:
    """Propose booking a whole trip: one flight option and/or one hotel option from the searches. The preview shows both
    and the trip total. After the user approves, Purser records the trip, emails the itinerary and shows payment
    buttons that open the airline's checkout and the hotel's website (payment happens there, not in Purser).
    Booking for a colleague (admin, HR, finance or their manager): for_user_id from find_people; the itinerary goes to their
    inbox and is emailed to email_to (an address the user said; spell it back) or the address on file."""
    return await _propose(ctx, "book_trip", {"flight_search_id": flight_search_id, "flight_option_id": flight_option_id,
                                             "hotel_search_id": hotel_search_id, "hotel_option_id": hotel_option_id,
                                             "for_user_id": for_user_id, "email_to": email_to})


@function_tool
@safe_tool
async def list_my_flights(ctx: Ctx) -> dict:
    """The user's approved flights and hotel stays, newest first, with payment status."""
    async with db.session_scope() as s:
        return {"ok": True, "bookings": await booking.my_bookings(s, ctx.context.actor)}


TOOLS = [get_my_location, search_flights, search_hotels, propose_flight_booking, propose_trip_booking, list_my_flights]
