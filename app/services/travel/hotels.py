"""Hotel search: SerpAPI Google Hotels (real rates, the hotel's own website for payment), 30-minute cache; on failure a
labelled sample list that links to a Google Hotels search."""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import date
from urllib.parse import quote

import httpx

from app.config import get_settings

log = logging.getLogger("purser.hotels")
URL = "https://serpapi.com/search.json"
CACHE_S = 1800
_cache: dict[tuple, tuple[float, dict]] = {}


def google_hotels_url(city: str, check_in: date, check_out: date) -> str:
    return f"https://www.google.com/travel/hotels?hl=en&gl=in&curr=INR&q={quote(f'hotels in {city} {check_in.isoformat()} to {check_out.isoformat()}')}"


def _safe_link(u: str | None) -> str | None:
    return u if u and u.startswith(("https://", "http://")) else None


def _norm(p: dict, nights: int) -> dict | None:
    rate = (p.get("rate_per_night") or {}).get("extracted_lowest")
    if rate is None:
        return None
    total = (p.get("total_rate") or {}).get("extracted_lowest") or rate * nights
    imgs = p.get("images") or []
    return {"name": p.get("name", "Hotel"), "type": p.get("type", "hotel"), "stars": p.get("extracted_hotel_class"),
            "rating": p.get("overall_rating"), "reviews": p.get("reviews"), "price_per_night_inr": int(rate), "total_inr": int(total),
            "image": imgs[0].get("thumbnail") if imgs else None, "link": _safe_link(p.get("link")),
            "amenities": (p.get("amenities") or [])[:5],
            "nearby": [n.get("name") for n in (p.get("nearby_places") or [])[:2] if n.get("name")],
            "check_in_time": p.get("check_in_time")}


def _sample(city: str, nights: int) -> list[dict]:
    seed = int(hashlib.sha256(city.encode()).hexdigest(), 16)
    names = ["Residency", "Grand", "Sea View Suites", "Business Hotel", "Comfort Inn", "Heritage Stay"]
    out = []
    for i, n in enumerate(names):
        rate = 2400 + (seed >> (i * 5)) % 7600
        out.append({"name": f"{city} {n}", "type": "hotel", "stars": 3 + i % 3, "rating": round(3.6 + ((seed >> i) % 13) / 10, 1),
                    "reviews": 200 + (seed >> (i * 3)) % 3000, "price_per_night_inr": rate, "total_inr": rate * nights, "image": None,
                    "link": None, "amenities": ["Free Wi-Fi", "Air conditioning", "Breakfast"][: 1 + i % 3], "nearby": [], "check_in_time": "2:00 PM"})
    return out


async def search(city: str, check_in: date, check_out: date, *, adults: int = 1) -> dict:
    nights = max(1, (check_out - check_in).days)
    key = (city.lower(), check_in.isoformat(), check_out.isoformat(), adults)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_S:
        return hit[1]
    st = get_settings()
    note = "Estimated rates: live hotel prices are unavailable right now. The hotel site shows the final price."
    if st.flights_enabled:
        params = {"engine": "google_hotels", "q": f"hotels in {city}", "check_in_date": check_in.isoformat(),
                  "check_out_date": check_out.isoformat(), "adults": str(adults), "currency": "INR", "gl": "in", "hl": "en",
                  "api_key": st.serpapi_api_key}
        try:
            async with httpx.AsyncClient(timeout=12) as c:
                body = (await c.get(URL, params=params)).json()
            if body.get("error"):
                raise ValueError(str(body["error"])[:200])
            opts = [o for o in (_norm(p, nights) for p in body.get("properties") or []) if o][:12]
            if opts:
                out = {"source": "serpapi", "options": opts, "note": None, "nights": nights,
                       "search_url": (body.get("search_metadata") or {}).get("google_hotels_url") or google_hotels_url(city, check_in, check_out)}
                _cache[key] = (time.time(), out)
                return out
            note = "No hotels found for those dates by the live search."
        except (httpx.HTTPError, ValueError) as e:
            log.warning("hotel search failed %s: %s", city, str(e)[:200])
            note = "Estimated rates: live hotel prices are unavailable right now. The hotel site shows the final price."
    return {"source": "sample", "options": _sample(city, nights), "note": note, "nights": nights,
            "search_url": google_hotels_url(city, check_in, check_out)}
