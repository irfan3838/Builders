"""Flight-only and whole-trip (flight + hotel) bookings.

Purser approves and records the trip, then hands the traveller to the real payment pages: the airline's own checkout
for the exact flight (Google Flights booking redirect) and the hotel's own website. Purser never takes or confirms
payment, so bookings stay 'pending_payment' and every message says payment is finished on those sites."""

from __future__ import annotations

import re
import secrets
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import get_settings
from app.errors import FORBIDDEN, NOT_FOUND, VALIDATION, DomainError
from app.models import FlightBooking, GoogleOp, HotelBooking, ResultSnapshot, Trip, User
from app.money import format_inr
from app.services import audit, messaging, people
from app.services.actions import Execution, Plan
from app.services.travel import airports, flights

PAY_NOTE = "Purser approves and records it; you complete payment on the airline / hotel website (Purser takes no payment)."


async def _snap(s, actor, search_id: str, kind: str) -> ResultSnapshot:
    snap = await s.get(ResultSnapshot, search_id)
    if snap is None or snap.actor_id != actor.user_id or (snap.meta or {}).get("kind") != kind:
        raise DomainError(NOT_FOUND, f"That {kind[:-1]} search was not found. Search again.")
    return snap


async def option(s, actor, search_id: str, option_id: int, kind: str = "flights") -> tuple[ResultSnapshot, dict]:
    snap = await _snap(s, actor, search_id, kind)
    for o in snap.rows:
        if int(o["id"]) == int(option_id):
            return snap, o
    raise DomainError(VALIDATION, f"Option {option_id} is not in that search (1 to {len(snap.rows)}).")


def _city(code: str) -> str:
    a = airports.BY_CODE.get(code)
    return a[1] if a else code


def flight_lines(snap, o) -> list[str]:
    hrs, mins = divmod(o["duration_min"], 60)
    stops = "non-stop" if o["stops"] == 0 else f"{o['stops']} stop{'s' if o['stops'] > 1 else ''} via {', '.join(o['layovers'])}"
    return [f"✈ {o['airline']} {o['flight_no']}",
            f"{_city(o['from'])} ({o['from']}) {o['depart']} → {_city(o['to'])} ({o['to']}) {o['arrive']}",
            f"{hrs}h {mins}m · {stops} · {o['cabin']}",
            f"Fare: {format_inr(o['price_inr'] * 100)} for {snap.spec.get('adults', 1)} adult(s)"
            + (" (estimated fare)" if snap.meta.get("source") == "sample" else " (live Google Flights fare)")]


def hotel_lines(snap, h) -> list[str]:
    stars = f"{h['stars']}-star · " if h.get("stars") else ""
    rating = f"rated {h['rating']} ({h['reviews']:,} reviews) · " if h.get("rating") and h.get("reviews") else ""
    return [f"🏨 {h['name']}", f"{snap.spec['city']}: {snap.spec['check_in']} → {snap.spec['check_out']} ({snap.meta['nights']} night(s))",
            f"{stars}{rating}{format_inr(h['price_per_night_inr'] * 100)}/night",
            f"Stay total: {format_inr(h['total_inr'] * 100)}" + (" (estimated rate)" if snap.meta.get("source") == "sample" else " (live Google Hotels rate)")]


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def _traveller(s, actor, args) -> User:
    """Who travels. Admin, HR, finance or the person's manager may book for someone else (a travel desk)."""
    me = await s.get(User, actor.user_id)
    uid = args.get("for_user_id")
    if not uid or int(uid) == actor.user_id:
        return me
    t = await people.user(s, actor, int(uid))
    if not (actor.is_hr or actor.is_approver or t.reports_to_id == actor.user_id):
        raise DomainError(FORBIDDEN, f"Only admin, HR, finance or {t.display_name}'s manager can book travel for them.")
    return t


def _send_to(actor, traveller: User, args) -> str | None:
    """Where the itinerary email goes: an address the user gave, else the traveller's address on file."""
    explicit = (args.get("email_to") or "").strip().lower()
    if explicit:
        if not EMAIL_RE.match(explicit):
            raise DomainError(VALIDATION, f"'{explicit}' is not a valid email address. Spell it out again.")
        return explicit
    if traveller.id == actor.user_id and actor.uses_google:
        return actor.email
    return traveller.notify_email


async def _inputs(s, actor, args) -> tuple:
    f = h = fs = hs = None
    if args.get("flight_search_id") and args.get("flight_option_id"):
        fs, f = await option(s, actor, args["flight_search_id"], args["flight_option_id"], "flights")
    if args.get("hotel_search_id") and args.get("hotel_option_id"):
        hs, h = await option(s, actor, args["hotel_search_id"], args["hotel_option_id"], "hotels")
    if not f and not h:
        raise DomainError(VALIDATION, "Pick a flight, a hotel, or both.")
    return fs, f, hs, h


async def _plan(s, actor, args) -> Plan:
    fs, f, hs, h = await _inputs(s, actor, args)
    lines: list[str] = []
    total = 0
    if f:
        lines += flight_lines(fs, f)
        total += f["price_inr"]
    if h:
        lines += hotel_lines(hs, h)
        total += h["total_inr"]
    if f and h:
        lines.append(f"Trip total: {format_inr(total * 100)}")
    who = await _traveller(s, actor, args)
    to = _send_to(actor, who, args)
    if who.id != actor.user_id:
        lines.insert(0, f"Traveller: {who.display_name} (booked by {actor.display_name})")
    lines.append(f"Itinerary emailed to {to}" + (f" from your Gmail ({actor.email})." if actor.uses_google else ".") if to
                 else f"Itinerary in {'their' if who.id != actor.user_id else 'your'} Purser inbox (no email address on file; say one to email it).")
    if actor.uses_google and who.id == actor.user_id:
        lines.append("Calendar holds added to your Google Calendar.")
    lines.append("After you approve, payment pages open: "
                 + " and ".join(x for x in ((f"{f['airline']} checkout" if f else ""), ("the hotel's website" if h else "")) if x) + ".")
    lines.append(PAY_NOTE)
    what = " and ".join(x for x in ((f"{f['airline']} {f['flight_no']} at {f['depart_time']}" if f else ""), (h["name"] if h else "")) if x)
    for_whom = f" for {who.display_name}" if who.id != actor.user_id else ""
    return Plan("Book trip" if f and h else "Book flight" if f else "Book hotel", lines,
                f"Approve {what}{for_whom} for {format_inr(total * 100)}?", [])


async def _execute(s, actor, args, receipt_id) -> Execution:
    fs, f, hs, h = await _inputs(s, actor, args)
    who = await _traveller(s, actor, args)
    to = _send_to(actor, who, args)
    for_other = who.id != actor.user_id
    tz = ZoneInfo(get_settings().calendar_timezone)
    pays: list[dict] = []
    refs: list[str] = []
    body: list[str] = []
    ops: list[tuple[str, dict]] = []
    total = 0
    start = end = None
    city = None
    if f:
        dep = datetime.strptime(f["depart"], "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        arr = datetime.strptime(f["arrive"], "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        link = await flights.checkout_link(f["from"], f["to"], dep.date(), f.get("booking_token"), fs.spec.get("adults", 1))
        b = FlightBooking(workspace_id=actor.workspace_id, user_id=who.id, ref="pending", origin=f["from"], destination=f["to"],
                          depart_at=f["depart"], arrive_at=f["arrive"], airline=f["airline"], flight_no=f["flight_no"],
                          price_paise=f["price_inr"] * 100, source=fs.meta.get("source", "serpapi"), status="pending_payment",
                          details={**{k: f[k] for k in ("duration_min", "stops", "layovers", "cabin")}, "pay": {k: link.get(k) for k in ("via", "exact")}},
                          receipt_id=receipt_id)
        s.add(b)
        await s.flush()
        b.ref = f"PUR-{b.id:03d}{secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
        refs.append(b.ref)
        total += f["price_inr"]
        start, end, city = dep.date(), dep.date(), _city(f["to"])
        pays.append({"type": "payment_link", "what": "flight", "label": f"Pay {link['via']} · {format_inr(f['price_inr'] * 100)}",
                     "detail": f"{f['airline']} {f['flight_no']} {f['from']}→{f['to']} {f['depart']}", **{k: link.get(k) for k in ("method", "url", "post_data", "exact")}})
        mail_url = link["url"] if link["method"] == "GET" else (fs.meta.get("search_url") or flights.google_flights_url(f["from"], f["to"], dep.date()))
        body += flight_lines(fs, f) + [f"Reference: {b.ref}", f"Pay at {link['via']}: {mail_url}", ""]
        ops.append(("create_event", {"title": f"✈ {f['airline']} {f['flight_no']} {f['from']}→{f['to']}", "start": dep.isoformat(),
                                     "end": arr.isoformat(), "tz": str(tz), "description": f"{b.ref}. Payment on the airline site."}))
        flight_row = b
    if h:
        ci, co = date.fromisoformat(hs.spec["check_in"]), date.fromisoformat(hs.spec["check_out"])
        url = h.get("link") or hs.meta.get("search_url")
        hb = HotelBooking(workspace_id=actor.workspace_id, user_id=who.id, ref="pending", hotel=h["name"], city=hs.spec["city"],
                          check_in=ci, check_out=co, nights=hs.meta["nights"], total_paise=h["total_inr"] * 100,
                          source=hs.meta.get("source", "serpapi"), status="pending_payment", pay_url=url,
                          details={k: h.get(k) for k in ("stars", "rating", "price_per_night_inr", "amenities")}, receipt_id=receipt_id)
        s.add(hb)
        await s.flush()
        hb.ref = f"HTL-{hb.id:03d}{secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
        refs.append(hb.ref)
        total += h["total_inr"]
        start, end, city = min(start or ci, ci), max(end or co, co), hs.spec["city"]
        pays.append({"type": "payment_link", "what": "hotel", "label": f"Pay {h['name']} · {format_inr(h['total_inr'] * 100)}",
                     "detail": f"{ci:%d %b} → {co:%d %b}, {hs.meta['nights']} night(s)", "method": "GET", "url": url,
                     "post_data": None, "exact": bool(h.get("link"))})
        body += hotel_lines(hs, h) + [f"Reference: {hb.ref}", f"Pay on the hotel website: {url}", ""]
        ops.append(("create_event", {"title": f"🏨 {h['name']} check-in", "start": datetime.combine(ci, datetime.min.time(), tz).replace(hour=14).isoformat(),
                                     "end": datetime.combine(ci, datetime.min.time(), tz).replace(hour=15).isoformat(), "tz": str(tz),
                                     "description": f"{hb.ref}. Check-out {co:%d %b}."}))
        hotel_row = hb
    trip_id = None
    if who.party_id and start:
        t = Trip(workspace_id=actor.workspace_id, employee_party_id=who.party_id, city=city, start_date=start, end_date=end,
                 purpose="Trip: " + ", ".join(refs))
        s.add(t)
        await s.flush()
        trip_id = t.id
    if f:
        flight_row.trip_id = trip_id
    if h:
        hotel_row.trip_id = trip_id
    subject = f"Trip approved: {city}, {start:%a %d %b} ({', '.join(refs)}) — complete payment"
    intro = (f"{actor.display_name} has booked this trip for you in Purser." if for_other else "Your trip is approved in Purser.")
    text = "\n".join([f"Hi {who.display_name.split()[0]},", "", intro, "", *body,
                      f"Total: {format_inr(total * 100)}", "", PAY_NOTE, "", "— Purser"])
    me = await s.get(User, actor.user_id)
    queue: list[tuple[str, dict]] = []
    if to and actor.uses_google:  # sent from the booker's own Gmail
        queue.append(("send_email", {"sender": actor.email, "to": [to], "cc": [actor.email] if for_other and to != actor.email else [],
                                     "subject": subject, "body": text}))
    if actor.uses_google and not for_other:
        queue += ops  # calendar holds only in the booker's own calendar
    for kind, payload in queue:
        op = GoogleOp(workspace_id=actor.workspace_id, user_id=actor.user_id, ref="pending", kind=kind, payload=payload,
                      status="queued", receipt_id=receipt_id)
        s.add(op)
        await s.flush()
        op.ref = f"G{op.id}"
    inbox = [who] + ([me] if for_other else [])
    await messaging.compose(s, actor, inbox, kind="trip", subject=subject, body=text, channels=["inbox"], receipt_id=receipt_id)
    if to and not actor.uses_google:
        await messaging.compose(s, actor, [], kind="trip", subject=subject, body=text, channels=["email"], receipt_id=receipt_id,
                                external_emails=[to])
    await audit.record(s, actor, "trip.approved", record_type="trip", record_id=trip_id, record_ref=", ".join(refs),
                       after={"refs": refs, "total_paise": total * 100, "payment": "on provider websites", "traveller": who.id},
                       receipt_id=receipt_id)
    return Execution(f"Trip approved{' for ' + who.display_name if for_other else ''} ({', '.join(refs)}), total {format_inr(total * 100)}. Payment pages are ready: "
                     + " and ".join(p["label"].split(" · ")[0] for p in pays) + ". Itinerary "
                     + (f"emailed to {to}." if to else "in your Purser inbox."), [*pays, *({"type": "booking", "ref": r} for r in refs)])


def _flight_args(args: dict) -> dict:
    return {"flight_search_id": args["search_id"], "flight_option_id": args["option_id"],
            "for_user_id": args.get("for_user_id"), "email_to": args.get("email_to")}


class BookFlight:
    kind = "book_flight"

    async def plan(self, s, actor, args):
        return await _plan(s, actor, _flight_args(args))

    async def execute(self, s, actor, args, receipt_id):
        return await _execute(s, actor, _flight_args(args), receipt_id)


class BookTrip:
    kind = "book_trip"

    async def plan(self, s, actor, args):
        return await _plan(s, actor, args)

    async def execute(self, s, actor, args, receipt_id):
        return await _execute(s, actor, args, receipt_id)


TRAVEL_ACTIONS = (BookFlight(), BookTrip())


async def my_bookings(s, actor, limit: int = 5) -> list[dict]:
    fl = (await s.execute(select(FlightBooking).where(FlightBooking.workspace_id == actor.workspace_id,
                                                      FlightBooking.user_id == actor.user_id)
                          .order_by(FlightBooking.id.desc()).limit(limit))).scalars().all()
    ht = (await s.execute(select(HotelBooking).where(HotelBooking.workspace_id == actor.workspace_id,
                                                     HotelBooking.user_id == actor.user_id)
                          .order_by(HotelBooking.id.desc()).limit(limit))).scalars().all()
    return ([{"ref": b.ref, "kind": "flight", "what": f"{b.airline} {b.flight_no} {b.origin}→{b.destination}", "when": b.depart_at,
              "price": format_inr(b.price_paise), "status": b.status} for b in fl]
            + [{"ref": b.ref, "kind": "hotel", "what": f"{b.hotel}, {b.city}", "when": f"{b.check_in} → {b.check_out}",
                "price": format_inr(b.total_paise), "status": b.status} for b in ht])
