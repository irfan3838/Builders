"""Flight search: SerpAPI Google Flights (real fares) with a 30-minute cache; on failure a clearly labelled sample list.

Results are normalised to options with stable ids (1..n) and stored by the caller as a snapshot, so the agent picks an
option by id and never states a price or time that the search did not return.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import date, datetime, timedelta

import httpx

from app.config import get_settings

log = logging.getLogger("purser.flights")
URL = "https://serpapi.com/search.json"
CACHE_S = 1800
_cache: dict[tuple, tuple[float, dict]] = {}


class FlightSearchError(Exception):
    pass


def _hhmm(t: str | None) -> str:
    return (t or "")[-5:]


def _norm_option(o: dict) -> dict | None:
    legs = o.get("flights") or []
    if not legs or o.get("price") is None:
        return None
    first, last = legs[0], legs[-1]
    airlines = list(dict.fromkeys(leg.get("airline", "") for leg in legs if leg.get("airline")))
    return {
        "airline": " + ".join(airlines) or "Unknown airline",
        "logo": o.get("airline_logo") or first.get("airline_logo"),
        "flight_no": ", ".join(leg.get("flight_number", "") for leg in legs if leg.get("flight_number")),
        "depart": first.get("departure_airport", {}).get("time"), "arrive": last.get("arrival_airport", {}).get("time"),
        "depart_time": _hhmm(first.get("departure_airport", {}).get("time")), "arrive_time": _hhmm(last.get("arrival_airport", {}).get("time")),
        "from": first.get("departure_airport", {}).get("id"), "to": last.get("arrival_airport", {}).get("id"),
        "duration_min": int(o.get("total_duration") or sum(int(leg.get("duration") or 0) for leg in legs)),
        "stops": len(legs) - 1, "layovers": [lay.get("id") or lay.get("name") for lay in o.get("layovers") or []],
        "price_inr": int(o["price"]), "cabin": first.get("travel_class", "Economy"),
        "overnight": any(leg.get("overnight") for leg in legs),
        "booking_token": o.get("booking_token"),  # server-side only: turned into the airline's checkout link on approval
    }


def _sample(origin: str, dest: str, day: date) -> list[dict]:
    """Deterministic SAMPLE fares when live search is unavailable. Always labelled 'sample' to the user."""
    seed = int(hashlib.sha256(f"{origin}{dest}{day}".encode()).hexdigest(), 16)
    carriers = [("IndiGo", "6E"), ("Air India", "AI"), ("Akasa Air", "QP"), ("Air India Express", "IX"), ("SpiceJet", "SG")]
    out = []
    for i in range(6):
        name, code = carriers[(seed >> (i * 3)) % len(carriers)]
        dep_h = 6 + (i * 3 + seed % 3) % 16
        dur = 95 + ((seed >> (i * 5)) % 60) + (75 if i == 4 else 0)
        dep = datetime.combine(day, datetime.min.time()) + timedelta(hours=dep_h, minutes=(seed >> i) % 4 * 15)
        arr = dep + timedelta(minutes=dur)
        out.append({"airline": name, "logo": None, "flight_no": f"{code} {1000 + (seed >> (i * 7)) % 8999}",
                    "depart": dep.strftime("%Y-%m-%d %H:%M"), "arrive": arr.strftime("%Y-%m-%d %H:%M"),
                    "depart_time": dep.strftime("%H:%M"), "arrive_time": arr.strftime("%H:%M"), "from": origin, "to": dest,
                    "duration_min": dur, "stops": 1 if i == 4 else 0, "layovers": ["HYD"] if i == 4 else [],
                    "price_inr": 3800 + (seed >> (i * 4)) % 5200, "cabin": "Economy", "overnight": False})
    return out


async def search(origin: str, dest: str, day: date, *, adults: int = 1) -> dict:
    """Returns {source: serpapi|sample, options: [...], note}. Options are sorted best-first (Google's order)."""
    key = (origin, dest, day.isoformat(), adults)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    st = get_settings()
    note = None
    if st.flights_enabled:
        params = {"engine": "google_flights", "departure_id": origin, "arrival_id": dest, "outbound_date": day.isoformat(),
                  "type": "2", "currency": "INR", "gl": "in", "hl": "en", "adults": str(adults), "api_key": st.serpapi_api_key}
        try:
            async with httpx.AsyncClient(timeout=12) as c:
                r = await c.get(URL, params=params)
            body = r.json()
            if r.status_code >= 400 or body.get("error"):
                raise FlightSearchError(str(body.get("error") or r.status_code)[:200])
            opts = []
            for best, group in ((True, body.get("best_flights") or []), (False, body.get("other_flights") or [])):
                for x in group:
                    o = _norm_option(x)
                    if o:
                        opts.append({**o, "best": best})
            if opts:
                out = {"source": "serpapi", "options": opts[:15], "note": None,
                       "search_url": (body.get("search_metadata") or {}).get("google_flights_url")}
                _cache[key] = (time.time(), out)
                return out
            note = "No flights found on that date by the live search."
        except (httpx.HTTPError, FlightSearchError, ValueError) as e:
            log.warning("serpapi failed %s-%s %s: %s", origin, dest, day, str(e)[:200])
            note = "Estimated fares: live prices are unavailable right now. The airline site shows the final price."
    else:
        note = "Estimated fares: live prices are unavailable right now. The airline site shows the final price."
    out = {"source": "sample", "options": _sample(origin, dest, day), "note": note, "search_url": google_flights_url(origin, dest, day)}
    return out


def google_flights_url(origin: str, dest: str, day: date) -> str:
    from urllib.parse import quote
    return f"https://www.google.com/travel/flights?hl=en&gl=in&curr=INR&q={quote(f'one way flights from {origin} to {dest} on {day.isoformat()}')}"


async def checkout_link(origin: str, dest: str, day: date, token: str | None, adults: int = 1) -> dict:
    """Where the traveller pays for THIS flight: the airline's own checkout via Google Flights' booking redirect
    (a POST, done by the browser), else a pre-filled Google Flights search. Never raises."""
    fallback = {"method": "GET", "url": google_flights_url(origin, dest, day), "via": "Google Flights", "exact": False}
    st = get_settings()
    if not (token and st.flights_enabled):
        return fallback
    params = {"engine": "google_flights", "departure_id": origin, "arrival_id": dest, "outbound_date": day.isoformat(), "type": "2",
              "currency": "INR", "gl": "in", "hl": "en", "adults": str(adults), "booking_token": token, "api_key": st.serpapi_api_key}
    try:
        async with httpx.AsyncClient(timeout=12) as c:
            body = (await c.get(URL, params=params)).json()
        opts = [b.get("together") or {} for b in body.get("booking_options") or []]
        opts = [o for o in opts if (o.get("booking_request") or {}).get("url", "").startswith("https://www.google.com/")]
        if not opts:
            return fallback
        best = next((o for o in opts if o.get("airline")), opts[0])  # prefer booking directly with the airline
        req = best["booking_request"]
        return {"method": "POST" if req.get("post_data") else "GET", "url": req["url"], "post_data": req.get("post_data"),
                "via": best.get("book_with") or "the airline", "price_inr": best.get("price"), "exact": True}
    except (httpx.HTTPError, ValueError, KeyError) as e:
        log.warning("checkout link failed %s-%s: %s", origin, dest, str(e)[:200])
        return fallback
